#!/usr/bin/env python3
"""
Retry decorator and shared vault audit-log writer.

Used by gmail_watcher, ai_employee, weekly_briefing, and vault_sync.

Exports:
    with_retry(max_attempts, backoff, log_fn)  — decorator
    write_vault_log(logs_path, entry)          — append JSON to Logs/
    mask_secrets(data)                         — redact sensitive values
"""

import functools
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Security: secret masking
# ---------------------------------------------------------------------------

# Key-name substrings that indicate a value should be redacted
_SECRET_KEY_PATTERNS = frozenset({
    "api_key", "apikey", "token", "password", "passwd", "secret",
    "auth", "credential", "private_key", "access_key", "refresh_token",
})

# Value prefixes that look like live API tokens regardless of key name
_SECRET_VALUE_PREFIXES = ("sk-", "AIza", "ya29.", "xoxb-", "ghp_")

# Compiled regex: catch anything that looks like a long base64/hex secret
_SECRET_VALUE_RE = re.compile(r"^[A-Za-z0-9+/=_\-]{40,}$")


def mask_secrets(data: dict) -> dict:
    """
    Return a shallow copy of *data* with sensitive values replaced by '***'.

    Rules (applied in order):
    1. If the key (lowercase) contains any token in _SECRET_KEY_PATTERNS → mask.
    2. If the string value starts with a known secret prefix → mask.
    3. If the string value is 40+ chars of base64/hex characters → mask.

    Non-string values and short strings are left untouched.
    Nested dicts are NOT recursed — call mask_secrets on sub-dicts explicitly
    if needed.

    Examples:
        mask_secrets({"api_key": "sk-abc123..."})  → {"api_key": "***"}
        mask_secrets({"to": "user@example.com"})   → {"to": "user@example.com"}
    """
    masked: dict = {}
    for k, v in data.items():
        k_lower = k.lower()

        # Rule 1: key name contains a secret pattern
        if any(pat in k_lower for pat in _SECRET_KEY_PATTERNS):
            masked[k] = "***"
            continue

        # Rules 2 & 3: inspect string values
        if isinstance(v, str):
            if v.startswith(_SECRET_VALUE_PREFIXES):
                masked[k] = "***"
                continue
            if _SECRET_VALUE_RE.match(v):
                masked[k] = "***"
                continue

        masked[k] = v

    return masked


# ---------------------------------------------------------------------------
# Shared vault log writer
# ---------------------------------------------------------------------------

def write_vault_log(logs_path, entry: dict) -> None:
    """
    Append a structured JSON audit entry to <logs_path>/YYYY-MM-DD.json.

    Creates the log file and parent directory if they do not exist.
    Maintains a valid JSON array at all times.

    Secrets in *entry* are automatically masked before writing.

    Required event types used across the project:
        email_received, email_processed, email_read, email_sent,
        approval_requested, approval_granted,
        retry_attempt, system_error, health_heartbeat,
        weekly_briefing_generated, vault_file_added, vault_file_moved,
        vault_file_removed, error
    """
    logs_path = Path(logs_path)
    logs_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_path / f"{today}.json"

    safe_entry = mask_secrets(dict(entry))   # redact before persisting
    safe_entry["logged_at"] = datetime.now().isoformat()

    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = []
        except (json.JSONDecodeError, ValueError):
            entries = []

    entries.append(safe_entry)
    log_file.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def with_retry(
    max_attempts: int = 3,
    backoff: tuple = (1, 2, 4),
    log_fn: Optional[Callable] = None,
) -> Callable:
    """
    Decorator: retry a function up to max_attempts times with backoff.

    Backoff pattern (seconds between attempts):
        attempt 1 fails → wait backoff[0]  (default 1s)
        attempt 2 fails → wait backoff[1]  (default 2s)
        attempt 3 fails → raise

    If log_fn is provided it is called on every retry attempt with a dict:
        {
          "event":         "retry_attempt",
          "function":      "<name>",
          "attempt":       <n>,
          "max_attempts":  <N>,
          "error":         "<message>",
          "delay_seconds": <d>,
        }

    Logging failures are silently swallowed so they never break the retry.

    Usage — as decorator:
        @with_retry(max_attempts=3, log_fn=self._write_audit_log)
        def call_api():
            ...

    Usage — inline:
        result = with_retry(max_attempts=3)(some_fn)()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc

                    if attempt < max_attempts:
                        delay = (
                            backoff[attempt - 1]
                            if attempt - 1 < len(backoff)
                            else backoff[-1]
                        )
                        print(
                            f"[RETRY] {func.__name__} attempt {attempt}/{max_attempts} "
                            f"failed: {exc}. Retrying in {delay}s...",
                            flush=True,
                        )
                        if log_fn:
                            try:
                                log_fn({
                                    "event":         "retry_attempt",
                                    "function":      func.__name__,
                                    "attempt":       attempt,
                                    "max_attempts":  max_attempts,
                                    "error":         str(exc),
                                    "delay_seconds": delay,
                                })
                            except Exception:
                                pass  # never let logging break the retry
                        time.sleep(delay)
                    else:
                        print(
                            f"[RETRY] {func.__name__} failed after "
                            f"{max_attempts} attempts: {exc}",
                            flush=True,
                        )

            raise last_exc  # re-raise after all attempts exhausted

        return wrapper
    return decorator
