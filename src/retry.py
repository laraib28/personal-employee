#!/usr/bin/env python3
"""
Retry decorator and shared vault audit-log writer.

Used by gmail_watcher, ai_employee, and weekly_briefing.

Exports:
    with_retry(max_attempts, backoff, log_fn)  — decorator
    write_vault_log(logs_path, entry)          — append JSON to Logs/
"""

import functools
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Shared vault log writer
# ---------------------------------------------------------------------------

def write_vault_log(logs_path, entry: dict) -> None:
    """
    Append a structured JSON audit entry to <logs_path>/YYYY-MM-DD.json.

    Creates the log file and parent directory if they do not exist.
    Maintains a valid JSON array at all times.

    Required event types used across the project:
        email_read, email_sent, weekly_briefing_generated,
        error, retry_attempt
    """
    logs_path = Path(logs_path)
    logs_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_path / f"{today}.json"

    entry = dict(entry)  # shallow copy — do not mutate caller's dict
    entry["logged_at"] = datetime.now().isoformat()

    entries = []
    if log_file.exists():
        try:
            entries = json.loads(log_file.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = []
        except (json.JSONDecodeError, ValueError):
            entries = []

    entries.append(entry)
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
        attempt 3 fails → raise            (default 4s would follow, but we raise)

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
