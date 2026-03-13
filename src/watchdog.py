#!/usr/bin/env python3
"""
Watchdog — Personal AI Employee (Platinum Tier)

Monitors worker callables and automatically restarts them if they crash.
Each worker runs in its own daemon thread; the watchdog loop lives in a
separate supervisor thread so it does not block the caller.

Failures are logged to obsidian_vault/Logs/YYYY-MM-DD.json via
retry.write_vault_log.

Usage:
    from watchdog import Watchdog, run_watched

    # Option A — convenience wrapper
    thread = run_watched(
        target=employee.run,
        name="ai_employee",
        logs_path=vault_path / "Logs",
    )

    # Option B — direct control
    dog = Watchdog(target=watcher.run, name="gmail_watcher", logs_path=...)
    dog.start()
    ...
    dog.stop()
"""

import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

# retry.py lives alongside this file in src/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from retry import write_vault_log


class Watchdog:
    """
    Runs *target* in a daemon thread and restarts it on unhandled exceptions.

    Parameters
    ----------
    target        : zero-argument callable (typically a ``.run()`` method)
    name          : human-readable worker name (used in log messages)
    logs_path     : vault Logs/ directory for structured event logging
    restart_delay : seconds to wait between crash and restart (default 5)
    max_restarts  : give up after this many consecutive crashes (default 10)
    """

    def __init__(
        self,
        target: Callable,
        name: str,
        logs_path: Path,
        restart_delay: float = 5.0,
        max_restarts: int = 10,
    ) -> None:
        self.target = target
        self.name = name
        self.logs_path = Path(logs_path)
        self.restart_delay = restart_delay
        self.max_restarts = max_restarts

        self._running: bool = False
        self._restart_count: int = 0
        self._supervisor: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> threading.Thread:
        """Start the supervisor thread. Returns the thread object."""
        self._running = True
        self._supervisor = threading.Thread(
            target=self._supervise,
            name=f"watchdog-{self.name}",
            daemon=True,
        )
        self._supervisor.start()
        return self._supervisor

    def stop(self) -> None:
        """Signal the supervisor to stop after the current worker exits."""
        self._running = False

    @property
    def restart_count(self) -> int:
        return self._restart_count

    # ------------------------------------------------------------------
    # Internal supervisor loop
    # ------------------------------------------------------------------

    def _supervise(self) -> None:
        while self._running:
            self._restart_count_this_run = 0
            self._run_worker()
            if not self._running:
                break

    def _run_worker(self) -> None:
        """Inner loop: start worker, restart on crash, give up after max_restarts."""
        consecutive = 0

        while self._running and consecutive <= self.max_restarts:
            try:
                self._log_info(f"Starting worker '{self.name}'")
                self.target()
                # Normal exit — do not restart
                self._log_info(f"Worker '{self.name}' exited normally.")
                return

            except Exception as exc:
                consecutive += 1
                self._restart_count += 1

                self._log_crash(exc, consecutive)

                if consecutive > self.max_restarts:
                    self._log_info(
                        f"Worker '{self.name}' exceeded {self.max_restarts} restarts. Stopping."
                    )
                    self._running = False
                    return

                self._log_info(
                    f"Restarting '{self.name}' in {self.restart_delay}s "
                    f"(attempt {consecutive}/{self.max_restarts})..."
                )
                time.sleep(self.restart_delay)

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log_info(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [WATCHDOG] {message}", flush=True)

    def _log_crash(self, exc: Exception, attempt: int) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{ts}] [WATCHDOG] Worker '{self.name}' crashed "
            f"(attempt {attempt}): {exc}",
            flush=True,
        )
        try:
            write_vault_log(self.logs_path, {
                "event":         "system_error",
                "context":       f"watchdog_{self.name}",
                "error":         str(exc),
                "error_type":    type(exc).__name__,
                "restart_count": self._restart_count,
            })
        except Exception:
            pass  # never let logging break the watchdog


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def run_watched(
    target: Callable,
    name: str,
    logs_path: Path,
    restart_delay: float = 5.0,
    max_restarts: int = 10,
) -> threading.Thread:
    """
    Create a Watchdog and start it immediately.

    Returns the supervisor thread (daemon=True, so it will not prevent
    the process from exiting).
    """
    dog = Watchdog(
        target=target,
        name=name,
        logs_path=logs_path,
        restart_delay=restart_delay,
        max_restarts=max_restarts,
    )
    return dog.start()
