#!/usr/bin/env python3
"""
Gmail Watcher — Personal AI Employee

Polls Gmail inbox for new messages, analyses each one using Claude API,
and writes structured task entries to /Needs_Action/ in the Obsidian vault.

The AI Employee main loop then picks up those entries and processes them.

Usage:
    python watchers/gmail_watcher.py
    python watchers/gmail_watcher.py --interval 60 --max-emails 10

Environment:
    ANTHROPIC_API_KEY   — Claude API key (required for analysis)
    GMAIL_POLL_INTERVAL — Override default poll interval in seconds
"""

import os
import sys
import time
import json

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from datetime import datetime
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# Allow importing shared utilities from src/
sys.path.insert(0, str(REPO_ROOT / "src"))
from retry import with_retry, write_vault_log  # noqa: E402

CREDENTIALS_FILE = REPO_ROOT / "credentials.json"
TOKEN_FILE = REPO_ROOT / "token.json"
VAULT_PATH = REPO_ROOT / "obsidian_vault"
SEEN_IDS_FILE = REPO_ROOT / ".gmail_seen_ids.json"
# gmail.modify is required to mark messages as read (removes UNREAD label)
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
DEFAULT_POLL_INTERVAL = 60  # seconds


# ---------------------------------------------------------------------------
# Gmail auth
# ---------------------------------------------------------------------------

def _get_gmail_service():
    """Return an authorised Gmail API service, refreshing token if needed."""
    import webbrowser
    import subprocess

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(
                    "Download OAuth credentials from Google Cloud Console "
                    "and place credentials.json in the project root.",
                    flush=True,
                )
                raise FileNotFoundError(
                    f"credentials.json not found at: {CREDENTIALS_FILE}"
                )

            class _WslBrowser(webbrowser.BaseBrowser):
                def open(self, url, new=0, autoraise=True):
                    print(f"Opening browser for Google sign-in...", flush=True)
                    print(f"Auth URL: {url}", flush=True)
                    subprocess.Popen(
                        ["cmd.exe", "/c", "start", "", url.replace("&", "^&")]
                    )
                    return True

            webbrowser.register("wsl-windows", _WslBrowser, preferred=True)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            print("Complete Google sign-in in your browser...", flush=True)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"Token saved: {TOKEN_FILE}", flush=True)

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Email fetching
# ---------------------------------------------------------------------------

def _get_header(headers: list[dict], name: str) -> str:
    """Extract a header value by name (case-insensitive)."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def fetch_new_emails(service, seen_ids: set, max_results: int = 5) -> list[dict]:
    """
    Fetch new unread inbox messages not yet seen by the watcher.

    Returns a list of dicts with: id, sender, subject, snippet, date.
    """
    result = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=max_results,
    ).execute()

    messages = result.get("messages", [])
    new_emails = []

    for msg in messages:
        msg_id = msg["id"]
        if msg_id in seen_ids:
            continue

        detail = service.users().messages().get(
            userId="me",
            id=msg_id,
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        headers = detail.get("payload", {}).get("headers", [])
        new_emails.append({
            "id": msg_id,
            "sender": _get_header(headers, "From"),
            "subject": _get_header(headers, "Subject"),
            "snippet": detail.get("snippet", ""),
            "date": _get_header(headers, "Date"),
        })

    return new_emails


# ---------------------------------------------------------------------------
# AI analysis
# ---------------------------------------------------------------------------

def analyse_email(email: dict, client) -> str:
    """
    Send the email to Claude for structured analysis.

    Returns the raw analysis text in the defined format.
    Prints the prompt and raw response to stdout for debugging.
    """
    sender = email["sender"]
    subject = email["subject"]
    snippet = email["snippet"]

    prompt = f"""You are an intelligent AI email assistant.

Analyze the email below and respond ONLY using this exact format.
Use plain text — no markdown, no bold, no asterisks, no extra lines.

Summary:
2-3 concise lines explaining what the email is about.

Action Required:
Yes or No

Urgency:
Low or Medium or High

Category:
Work or Social or Marketing or Finance or Personal or Spam or Other

Suggested Action:
Reply or Ignore or Mark as Read or Follow-up or Archive

Email Details:
From: {sender}
Subject: {subject}
Content: {snippet}

Rules:
- If the subject or content contains URGENT or urgent, set Urgency to High.
- If the subject or content mentions payment, invoice, bill, or receipt, set Category to Finance.
- If Urgency is High, set Action Required to Yes.
- Output only the five fields above. Nothing else."""

    print(f"\n[DEBUG] Prompt sent to Claude:\n{prompt}\n", flush=True)

    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    print(f"[DEBUG] Raw Claude response:\n{raw}\n", flush=True)

    return raw


def _parse_analysis(analysis: str, email: Optional[dict] = None) -> dict:
    """
    Parse the structured analysis text into a dict for YAML frontmatter.

    Keys: summary, action_required, urgency, category, suggested_action.

    Handles both inline values ("Urgency: High") and next-line values.
    Strips markdown bold markers (**) before matching.
    Applies hardcoded override rules using the original email if provided.
    """
    result = {
        "summary": "",
        "action_required": "No",
        "urgency": "Low",
        "category": "Other",
        "suggested_action": "Mark as Read",
    }

    field_map = {
        "Summary:": "summary",
        "Action Required:": "action_required",
        "Urgency:": "urgency",
        "Category:": "category",
        "Suggested Action:": "suggested_action",
    }

    lines = analysis.splitlines()
    current_field = None
    current_lines = []

    for line in lines:
        # Normalise: strip leading/trailing whitespace and markdown bold markers
        normalised = line.strip().replace("**", "").strip()

        matched = False
        for label, key in field_map.items():
            if normalised.startswith(label):
                # Save previous field before switching
                if current_field:
                    result[current_field] = " ".join(current_lines).strip()
                current_field = key
                # Value may be inline ("Urgency: High") or on the next line
                inline_value = normalised[len(label):].strip()
                current_lines = [inline_value] if inline_value else []
                matched = True
                break

        if not matched and current_field and normalised:
            current_lines.append(normalised)

    # Save the last field
    if current_field:
        result[current_field] = " ".join(current_lines).strip()

    print(f"[DEBUG] Parsed fields: {result}", flush=True)

    # ------------------------------------------------------------------
    # Hardcoded override rules — applied after parsing so Claude's output
    # can still influence non-overridden fields.
    # ------------------------------------------------------------------
    print(f"[DEBUG] Email object received: {email}", flush=True)
    print(f"[DEBUG] Subject value: {email.get('subject') if email else None}", flush=True)

    if email:
        subject_lower = email.get("subject", "").lower()
        snippet_lower = email.get("snippet", "").lower()

        print(f"[DEBUG] subject_lower: {subject_lower!r}", flush=True)
        print(f"[DEBUG] snippet_lower: {snippet_lower!r}", flush=True)

        if "urgent" in subject_lower:
            result["urgency"] = "High"
            print("[DEBUG] Override applied: urgency → High (URGENT detected)", flush=True)

        if any(keyword in snippet_lower for keyword in ["payment", "invoice", "bill", "receipt"]):
            result["category"] = "Finance"
            print("[DEBUG] Override applied: category → Finance (finance keyword detected)", flush=True)

        if result["urgency"] == "High":
            result["action_required"] = "Yes"
            print("[DEBUG] Override applied: action_required → Yes (urgency is High)", flush=True)

    return result


# ---------------------------------------------------------------------------
# Vault writer
# ---------------------------------------------------------------------------

def write_to_vault(email: dict, analysis: str, vault_path: Path) -> Path:
    """
    Write the email + AI analysis as a markdown task file to /Needs_Action/.

    Returns the path of the created file.
    """
    needs_action_dir = vault_path / "Needs_Action"
    needs_action_dir.mkdir(parents=True, exist_ok=True)

    parsed = _parse_analysis(analysis, email=email)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = "".join(
        c if c.isalnum() or c == "_" else "_"
        for c in email["subject"].lower().replace(" ", "_")
    )[:40]
    filename = f"{timestamp}_email_{slug}.md"

    # Map urgency to approval_required flag
    approval_required = parsed["urgency"] == "High"

    content = f"""---
timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
event: email
source: gmail
email_id: {email["id"]}
from: "{email["sender"]}"
subject: "{email["subject"]}"
date: "{email["date"]}"
urgency: {parsed["urgency"]}
category: {parsed["category"]}
action_required: {parsed["action_required"]}
suggested_action: {parsed["suggested_action"]}
approval_required: {str(approval_required).lower()}
---

# Email: {email["subject"]}

**From:** {email["sender"]}
**Date:** {email["date"]}

---

## AI Analysis

{analysis}

---

## Original Snippet

> {email["snippet"]}

"""
    file_path = needs_action_dir / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


# ---------------------------------------------------------------------------
# Seen IDs persistence
# ---------------------------------------------------------------------------

def load_seen_ids() -> set:
    """Load previously seen Gmail message IDs from disk."""
    if SEEN_IDS_FILE.exists():
        try:
            return set(json.loads(SEEN_IDS_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValueError):
            return set()
    return set()


def save_seen_ids(seen_ids: set) -> None:
    """Persist seen Gmail message IDs to disk."""
    SEEN_IDS_FILE.write_text(
        json.dumps(list(seen_ids), indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Main watcher loop
# ---------------------------------------------------------------------------

class GmailWatcher:
    """Polls Gmail and writes AI-analysed email tasks to the Obsidian vault."""

    def __init__(
        self,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        max_emails: int = 5,
        vault_path: Path = VAULT_PATH,
    ):
        self.poll_interval = poll_interval
        self.max_emails = max_emails
        self.vault_path = vault_path
        self.logs_path = vault_path / "Logs"
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.seen_ids = load_seen_ids()

        # Gmail service
        print("Authenticating with Gmail...", flush=True)
        self.gmail = _get_gmail_service()
        print("Gmail connected.", flush=True)

        # Claude client
        api_key = os.environ.get("ANTHROPIC_API_KEY") or _load_api_key_from_env()
        self.client = None
        if api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
                print("Claude API connected.", flush=True)
            except ImportError:
                print("Warning: anthropic package not installed — analysis disabled", flush=True)
        else:
            print("Warning: ANTHROPIC_API_KEY not set — analysis disabled", flush=True)

    def poll(self) -> int:
        """
        Fetch new emails, analyse them, write to vault.
        Returns count of new emails processed.
        """
        try:
            emails = fetch_new_emails(self.gmail, self.seen_ids, self.max_emails)
        except Exception as e:
            print(f"[ERROR] Gmail fetch failed: {e}", flush=True)
            return 0

        if not emails:
            return 0

        print(f"[{_ts()}] Found {len(emails)} new email(s)", flush=True)
        processed = 0

        for email in emails:
            print(f"  Processing: {email['subject'][:60]}", flush=True)

            # AI analysis
            analysis = "(AI analysis disabled — no API key)"
            if self.client:
                try:
                    analysis = analyse_email(email, self.client)
                except Exception as e:
                    analysis = f"(Analysis error: {e})"

            # Write to vault
            vault_written = False
            try:
                path = write_to_vault(email, analysis, self.vault_path)
                print(f"  -> Written: {path.name}", flush=True)
                vault_written = True
            except Exception as e:
                print(f"  [ERROR] Failed to write vault entry: {e}", flush=True)
                write_vault_log(self.logs_path, {
                    "event": "error",
                    "context": "write_to_vault",
                    "subject": email.get("subject", ""),
                    "error": str(e),
                })

            # Mark as read in Gmail — only after vault write confirmed
            if vault_written:
                def _mark_read(email_id=email["id"]):
                    self.gmail.users().messages().modify(
                        userId="me",
                        id=email_id,
                        body={"removeLabelIds": ["UNREAD"]},
                    ).execute()

                try:
                    with_retry(
                        max_attempts=3,
                        backoff=(1, 2, 4),
                        log_fn=lambda e: write_vault_log(self.logs_path, e),
                    )(_mark_read)()
                    print(f"  [INFO] Marked as read: {email['subject']}", flush=True)
                    write_vault_log(self.logs_path, {
                        "event": "email_read",
                        "email_id": email["id"],
                        "subject": email.get("subject", ""),
                        "from": email.get("sender", ""),
                    })
                except Exception as e:
                    print(f"  [ERROR] Failed to mark as read: {e}", flush=True)
                    write_vault_log(self.logs_path, {
                        "event": "error",
                        "context": "mark_as_read",
                        "email_id": email["id"],
                        "subject": email.get("subject", ""),
                        "error": str(e),
                    })

            self.seen_ids.add(email["id"])
            processed += 1

        save_seen_ids(self.seen_ids)
        return processed

    def run(self) -> None:
        """Run the Gmail watcher continuously."""
        print("=" * 60, flush=True)
        print("GMAIL WATCHER — Personal AI Employee", flush=True)
        print("=" * 60, flush=True)
        print(f"Vault:    {self.vault_path}", flush=True)
        print(f"Interval: {self.poll_interval}s", flush=True)
        print(f"AI:       {'Enabled' if self.client else 'Disabled'}", flush=True)
        print("=" * 60, flush=True)
        print("Watching for new emails... (Ctrl+C to stop)\n", flush=True)

        try:
            while True:
                self.poll()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\nGmail watcher stopped.", flush=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_api_key_from_env() -> Optional[str]:
    """Fallback: read ANTHROPIC_API_KEY from .env file if not in environment."""
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Gmail Watcher — AI Employee")
    parser.add_argument(
        "--interval", type=float,
        default=float(os.environ.get("GMAIL_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)),
        help=f"Poll interval in seconds (default: {DEFAULT_POLL_INTERVAL})",
    )
    parser.add_argument(
        "--max-emails", type=int, default=5,
        help="Max emails to fetch per poll (default: 5)",
    )
    parser.add_argument(
        "--vault", type=str, default=None,
        help="Path to Obsidian vault (default: obsidian_vault/)",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault) if args.vault else VAULT_PATH

    watcher = GmailWatcher(
        poll_interval=args.interval,
        max_emails=args.max_emails,
        vault_path=vault_path,
    )
    watcher.run()


if __name__ == "__main__":
    main()
