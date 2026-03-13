#!/usr/bin/env python3
"""
Health Monitor — Personal AI Employee (Platinum Tier)

Tracks system health and writes a live status file every heartbeat cycle.

Output:  obsidian_vault/Logs/health_status.json

Schema:
    {
      "heartbeat":              "<ISO timestamp>",
      "uptime":                 "HH:MM:SS",
      "uptime_seconds":         <float>,
      "error_count":            <int>,
      "emails_processed_today": <int>,
      "last_email":             "<subject or null>",
      "services":               {"<name>": "running|stopped|error", ...},
      "updated_at":             "<ISO timestamp>"
    }

Usage:
    from health_monitor import HealthMonitor

    hm = HealthMonitor(logs_path)
    hm.set_service_status("ai_employee", "running")
    hm.heartbeat()          # call each agent cycle
    hm.increment_error()    # call on any handled exception
    hm.set_last_email("Re: Invoice")
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class HealthMonitor:
    """
    Lightweight health tracker for the Personal AI Employee system.

    Thread-safe for reads; writes are serialised via single-process ownership.
    """

    def __init__(self, logs_path: Path) -> None:
        self.logs_path = Path(logs_path)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.status_file = self.logs_path / "health_status.json"

        self._start_time: float = time.monotonic()
        self._error_count: int = 0
        self._emails_today: int = 0
        self._last_email: Optional[str] = None
        self._last_heartbeat: Optional[str] = None
        self._services: dict[str, str] = {}

        # Write initial status immediately
        self._write()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def heartbeat(self) -> None:
        """Record a heartbeat timestamp and flush status to disk."""
        self._last_heartbeat = datetime.now().isoformat()
        self._write()

    def set_service_status(self, service: str, status: str) -> None:
        """
        Update the status of a named service.

        Suggested values: "running", "stopped", "error", "starting"
        """
        self._services[service] = status

    def increment_error(self) -> None:
        """Increment the cumulative error counter by 1."""
        self._error_count += 1

    def set_last_email(self, subject: str) -> None:
        """Record the subject of the most recently processed email."""
        self._last_email = subject
        self._emails_today += 1

    def get_uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    def to_dict(self) -> dict:
        """Return the current health status as a plain dict."""
        return {
            "heartbeat":              self._last_heartbeat,
            "uptime":                 self._format_uptime(),
            "uptime_seconds":         round(self.get_uptime_seconds(), 1),
            "error_count":            self._error_count,
            "emails_processed_today": self._emails_today,
            "last_email":             self._last_email,
            "services":               dict(self._services),
            "updated_at":             datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _format_uptime(self) -> str:
        secs = int(self.get_uptime_seconds())
        h, remainder = divmod(secs, 3600)
        m, s = divmod(remainder, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _write(self) -> None:
        """Atomically write status JSON to disk."""
        try:
            self.status_file.write_text(
                json.dumps(self.to_dict(), indent=2, default=str),
                encoding="utf-8",
            )
        except OSError:
            pass  # never crash the agent over a health-write failure
