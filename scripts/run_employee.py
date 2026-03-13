#!/usr/bin/env python3
"""
AI Employee — Platinum-tier entry point with RUN_MODE dispatch and Watchdog.

RUN_MODE (set in .env or environment):
    local  (default)
        Runs the AI Employee only.
        Handles human approval, final email sending, vault management.

    cloud
        Runs both the Gmail Watcher AND the AI Employee in parallel,
        each supervised by a Watchdog that restarts on crash.
        Intended for always-on server/cloud deployment.

Domain separation:
    Cloud responsibilities : Gmail ingestion, AI analysis, briefing generation
    Local responsibilities : Human approval gate, email sending, financial actions

Usage:
    python scripts/run_employee.py
    python scripts/run_employee.py --mode cloud
    python scripts/run_employee.py --interval 10 --vault /path/to/vault
    python scripts/run_employee.py --mode cloud --restart-delay 10
"""

import argparse
import os
import sys
from pathlib import Path

# Repo root is one level above scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "watchers"))


# ---------------------------------------------------------------------------
# .env loader (no external dependency)
# ---------------------------------------------------------------------------

def _load_env(repo_root: Path) -> None:
    """Read key=value pairs from .env into os.environ (does not overwrite)."""
    env_file = repo_root / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _load_env(REPO_ROOT)

    parser = argparse.ArgumentParser(
        description="AI Employee — Platinum tier runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["cloud", "local"],
        default=os.environ.get("RUN_MODE", "local"),
        help="Run mode: 'local' (approval + sending) or 'cloud' (Gmail + AI). "
             "Defaults to RUN_MODE env var or 'local'.",
    )
    parser.add_argument(
        "--interval", type=float, default=5.0,
        help="AI Employee poll interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--vault", type=str, default=None,
        help="Path to Obsidian vault (default: obsidian_vault/ in repo root)",
    )
    parser.add_argument(
        "--restart-delay", type=float,
        default=float(os.environ.get("WATCHDOG_RESTART_DELAY", "5")),
        help="Seconds between watchdog crash-restart (default: 5)",
    )
    parser.add_argument(
        "--max-restarts", type=int,
        default=int(os.environ.get("WATCHDOG_MAX_RESTARTS", "10")),
        help="Watchdog gives up after this many consecutive crashes (default: 10)",
    )
    args = parser.parse_args()

    vault_path = Path(args.vault) if args.vault else REPO_ROOT / "obsidian_vault"
    logs_path = vault_path / "Logs"

    from ai_employee import AIEmployee
    from watchdog import run_watched

    print(f"[RUNNER] RUN_MODE = {args.mode.upper()}", flush=True)
    print(f"[RUNNER] Vault    = {vault_path}", flush=True)

    # ------------------------------------------------------------------
    # Build AI Employee
    # ------------------------------------------------------------------
    employee = AIEmployee(repo_root=REPO_ROOT, poll_interval=args.interval)
    if args.vault:
        employee.vault_path = vault_path
        employee.needs_action_path = vault_path / "Needs_Action"
        employee.pending_approval_path = vault_path / "Pending_Approval"
        employee.approved_path = vault_path / "Approved"
        employee.done_path = vault_path / "Done"
        employee.logs_path = logs_path
        employee.plans_path = vault_path / "Plans"
        employee._setup_directories()

    employee.health.set_service_status("ai_employee", "starting")

    if args.mode == "cloud":
        # ---------------------------------------------------------------
        # CLOUD mode: Gmail Watcher + AI Employee, both under watchdog
        # ---------------------------------------------------------------
        print("[RUNNER] Starting in CLOUD mode (Gmail Watcher + AI Employee)", flush=True)

        try:
            from gmail_watcher import GmailWatcher
        except ImportError as exc:
            print(f"[RUNNER] ERROR: Cannot import GmailWatcher — {exc}", flush=True)
            print("[RUNNER] Install: google-auth-oauthlib google-api-python-client", flush=True)
            sys.exit(1)

        watcher = GmailWatcher(vault_path=vault_path)
        employee.health.set_service_status("gmail_watcher", "starting")

        # Run gmail_watcher in a supervised thread
        watcher_thread = run_watched(
            target=watcher.run,
            name="gmail_watcher",
            logs_path=logs_path,
            restart_delay=args.restart_delay,
            max_restarts=args.max_restarts,
        )
        employee.health.set_service_status("gmail_watcher", "running")
        print("[RUNNER] Gmail Watcher started (supervised)", flush=True)

        # Run ai_employee in a second supervised thread
        print("[RUNNER] Starting AI Employee (supervised)...", flush=True)
        employee_thread = run_watched(
            target=employee.run,
            name="ai_employee",
            logs_path=logs_path,
            restart_delay=args.restart_delay,
            max_restarts=args.max_restarts,
        )

        # Block main thread until both workers die (or Ctrl-C)
        try:
            watcher_thread.join()
            employee_thread.join()
        except KeyboardInterrupt:
            print("\n[RUNNER] Shutting down (Ctrl-C).", flush=True)

    else:
        # ---------------------------------------------------------------
        # LOCAL mode: AI Employee only, under watchdog
        # ---------------------------------------------------------------
        print("[RUNNER] Starting in LOCAL mode (AI Employee only)", flush=True)
        print("[RUNNER] Handles: approval gate, email sending, vault management", flush=True)

        employee_thread = run_watched(
            target=employee.run,
            name="ai_employee",
            logs_path=logs_path,
            restart_delay=args.restart_delay,
            max_restarts=args.max_restarts,
        )

        try:
            employee_thread.join()
        except KeyboardInterrupt:
            print("\n[RUNNER] Shutting down (Ctrl-C).", flush=True)


if __name__ == "__main__":
    main()
