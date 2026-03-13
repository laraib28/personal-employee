#!/usr/bin/env python3
"""
Vault Sync Preparation — Personal AI Employee (Platinum Tier)

Monitors vault folders for file additions and moves, and logs structured
sync events.  Does NOT perform real cloud sync — only prepares the event
log so a future sync layer can consume it.

Tracked folders (must already exist or will be created):
    Needs_Action, Pending_Approval, Approved, Done, Logs, Briefings

Sync events emitted:
    vault_file_added    — new file appeared in a folder
    vault_file_moved    — file disappeared from one folder, appeared in another
    vault_file_removed  — file disappeared without reappearing elsewhere

Usage:
    from vault_sync import VaultSync

    vs = VaultSync(vault_path, log_fn=write_vault_log_partial)
    # Call every agent cycle:
    events = vs.check()   # returns list of event dicts (may be empty)
"""

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


SYNC_FOLDERS = [
    "Needs_Action",
    "Pending_Approval",
    "Approved",
    "Done",
    "Logs",
    "Briefings",
]


class VaultSync:
    """
    Lightweight vault file-change detector.

    Takes a snapshot of each tracked folder on initialisation, then
    compares against that snapshot on every ``check()`` call.
    """

    def __init__(
        self,
        vault_path: Path,
        log_fn: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.log_fn = log_fn

        # Ensure folders exist
        for folder in SYNC_FOLDERS:
            (self.vault_path / folder).mkdir(parents=True, exist_ok=True)

        # Initial snapshot
        self._snapshots: dict[str, set[str]] = self._snapshot()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self) -> list[dict]:
        """
        Diff current vault state against the stored snapshot.

        Returns a list of event dicts (may be empty).  Events are also
        forwarded to log_fn if provided.
        """
        current = self._snapshot()
        events: list[dict] = []

        for folder in SYNC_FOLDERS:
            prev = self._snapshots.get(folder, set())
            now = current.get(folder, set())

            added = now - prev
            removed = prev - now

            for fname in sorted(added):
                event = {
                    "event":  "vault_file_added",
                    "folder": folder,
                    "file":   fname,
                    "ts":     datetime.now().isoformat(),
                }
                events.append(event)
                self._emit(event)

            for fname in sorted(removed):
                # Check whether the file simply moved to another folder
                moved_to = next(
                    (
                        f for f in SYNC_FOLDERS
                        if f != folder and fname in current.get(f, set())
                    ),
                    None,
                )
                event = {
                    "event":    "vault_file_moved" if moved_to else "vault_file_removed",
                    "folder":   folder,
                    "file":     fname,
                    "moved_to": moved_to,
                    "ts":       datetime.now().isoformat(),
                }
                events.append(event)
                self._emit(event)

        # Advance snapshot
        self._snapshots = current
        return events

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _snapshot(self) -> dict[str, set[str]]:
        snap: dict[str, set[str]] = {}
        for folder in SYNC_FOLDERS:
            path = self.vault_path / folder
            if path.exists():
                snap[folder] = {f.name for f in path.iterdir() if f.is_file()}
            else:
                snap[folder] = set()
        return snap

    def _emit(self, event: dict) -> None:
        if self.log_fn:
            try:
                self.log_fn(event)
            except Exception:
                pass  # never crash the agent over a sync-log failure
