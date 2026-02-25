#!/usr/bin/env python3
"""
MCP Email Server — Personal AI Employee

A minimal Model Context Protocol (MCP) stdio server that sends emails
via the Gmail API. Replaces SMTP with OAuth2-authenticated Gmail sending.

Protocol: JSON-RPC 2.0 over stdin/stdout (newline-delimited)

Tools exposed:
    send_email(to, subject, body) → {status: "success"}
                                  | {status: "error", message: "..."}

Register in ~/.config/claude-code/mcp.json:
    {
      "mcpServers": {
        "email": {
          "command": "python",
          "args": ["/abs/path/to/mcp_servers/email/server.py"]
        }
      }
    }

Standalone test:
    python mcp_servers/email/server.py --test to@example.com "Subject" "Body"
"""

import sys
import json
import base64
import argparse
from email.mime.text import MIMEText
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CREDENTIALS_FILE = REPO_ROOT / "credintials.json.json"
TOKEN_FILE = REPO_ROOT / "token.json"
# Use gmail.send scope (minimal) — gmail.modify already obtained for the watcher,
# so the existing token.json covers this.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# ---------------------------------------------------------------------------
# Gmail auth (shared logic with gmail_watcher.py)
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
                raise FileNotFoundError(
                    f"Credentials file not found: {CREDENTIALS_FILE}\n"
                    "Download OAuth2 credentials from Google Cloud Console."
                )

            class _WslBrowser(webbrowser.BaseBrowser):
                def open(self, url, new=0, autoraise=True):
                    print(f"Auth URL: {url}", file=sys.stderr, flush=True)
                    subprocess.Popen(
                        ["cmd.exe", "/c", "start", "", url.replace("&", "^&")]
                    )
                    return True

            webbrowser.register("wsl-windows", _WslBrowser, preferred=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            print("Complete Google sign-in in your browser...", file=sys.stderr, flush=True)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"Token saved: {TOKEN_FILE}", file=sys.stderr, flush=True)

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Gmail send
# ---------------------------------------------------------------------------

def send_gmail(to: str, subject: str, body: str) -> dict:
    """
    Send an email via Gmail API.

    Returns {"status": "success"} or {"status": "error", "message": "..."}.
    """
    try:
        service = _get_gmail_service()

        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()

        return {"status": "success"}

    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# MCP JSON-RPC 2.0 stdio server
# ---------------------------------------------------------------------------

TOOL_DEFINITION = {
    "name": "send_email",
    "description": (
        "Send an email via Gmail API. "
        "Requires OAuth2 token to be present (run gmail_watcher.py once to authenticate)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "to":      {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body":    {"type": "string", "description": "Plain-text email body"},
        },
        "required": ["to", "subject", "body"],
    },
}

SERVER_INFO = {"name": "email", "version": "0.1.0"}
PROTOCOL_VERSION = "2024-11-05"


def _send_response(response: dict) -> None:
    """Write a JSON-RPC response to stdout (newline-delimited)."""
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def _error_response(req_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def _handle_request(request: dict) -> None:
    """Dispatch a single JSON-RPC request."""
    req_id = request.get("id")
    method = request.get("method", "")

    # Notifications (no id) — acknowledge silently
    if req_id is None:
        return

    if method == "initialize":
        _send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        })

    elif method == "tools/list":
        _send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": [TOOL_DEFINITION]},
        })

    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name != "send_email":
            _send_response(_error_response(req_id, -32601, f"Unknown tool: {tool_name}"))
            return

        to      = arguments.get("to", "")
        subject = arguments.get("subject", "")
        body    = arguments.get("body", "")

        if not to or not subject:
            _send_response(_error_response(req_id, -32602, "'to' and 'subject' are required"))
            return

        result = send_gmail(to, subject, body)
        _send_response({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps(result)}
                ],
                "isError": result["status"] != "success",
            },
        })

    else:
        _send_response(_error_response(req_id, -32601, f"Method not found: {method}"))


def run_server() -> None:
    """Read newline-delimited JSON-RPC messages from stdin and dispatch them."""
    print(f"MCP Email Server starting (PID {__import__('os').getpid()})",
          file=sys.stderr, flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            _send_response(_error_response(None, -32700, f"Parse error: {exc}"))
            continue
        try:
            _handle_request(request)
        except Exception as exc:
            req_id = request.get("id")
            _send_response(_error_response(req_id, -32603, f"Internal error: {exc}"))


# ---------------------------------------------------------------------------
# Standalone test mode
# ---------------------------------------------------------------------------

def _standalone_test(to: str, subject: str, body: str) -> None:
    """Send a test email directly (bypasses MCP protocol)."""
    print(f"Sending test email to {to}...", flush=True)
    result = send_gmail(to, subject, body)
    print(f"Result: {result}", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="MCP Email Server")
    parser.add_argument("--test", nargs=3, metavar=("TO", "SUBJECT", "BODY"),
                        help="Send a test email directly without MCP protocol")
    args = parser.parse_args()

    if args.test:
        _standalone_test(*args.test)
    else:
        run_server()


if __name__ == "__main__":
    main()
