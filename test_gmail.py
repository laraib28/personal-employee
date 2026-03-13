#!/usr/bin/env python3
"""
Gmail API connectivity test.

Authenticates via OAuth2 (InstalledAppFlow) using the project credentials file,
then fetches the latest 5 messages from the inbox and prints the count.

Usage:
    python test_gmail.py
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path

CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    """Authenticate and return an authorised Gmail API service object."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    # Load existing token if available
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh or re-authenticate if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            # WSL2: register a custom browser that opens via Windows cmd.exe.
            # Patching webbrowser.open alone is insufficient because the module
            # iterates an internal _tryorder registry. We inject our own browser.
            class _WslBrowser(webbrowser.BaseBrowser):
                def open(self, url, new=0, autoraise=True):
                    print(f"\nAuth URL: {url}\n", flush=True)
                    subprocess.Popen(
                        ["cmd.exe", "/c", "start", "", url.replace("&", "^&")]
                    )
                    return True

            webbrowser.register("wsl-windows", _WslBrowser, preferred=True)

            print("Opening Google sign-in in your Windows browser...", flush=True)
            print("Please complete the sign-in, then return here.", flush=True)
            creds = flow.run_local_server(port=0)

        # Save token for next run
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"Token saved to: {TOKEN_FILE}")

    service = build("gmail", "v1", credentials=creds)
    return service


def main():
    # Verify credentials file exists
    if not CREDENTIALS_FILE.exists():
        print(
            "Download OAuth credentials from Google Cloud Console "
            "and place credentials.json in the project root."
        )
        sys.exit(1)

    print(f"Using credentials: {CREDENTIALS_FILE.name}", flush=True)
    print("Connecting to Gmail API...", flush=True)

    try:
        service = get_gmail_service()

        # Fetch latest 5 messages from inbox
        result = service.users().messages().list(
            userId="me",
            labelIds=["INBOX"],
            maxResults=5
        ).execute()

        messages = result.get("messages", [])
        print(f"Messages Found: {len(messages)}")

        # Print subject of each message
        if messages:
            print("\nLatest messages:")
            for i, msg in enumerate(messages, 1):
                msg_detail = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From"]
                ).execute()

                headers = {
                    h["name"]: h["value"]
                    for h in msg_detail.get("payload", {}).get("headers", [])
                }
                subject = headers.get("Subject", "(no subject)")
                sender = headers.get("From", "(unknown)")
                print(f"  {i}. From: {sender}")
                print(f"     Subject: {subject}")

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
