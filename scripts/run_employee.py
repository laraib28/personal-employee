#!/usr/bin/env python3
"""
Standalone runner for the AI Employee continuous monitor.

Usage:
    python scripts/run_employee.py
    python scripts/run_employee.py --interval 10
    python scripts/run_employee.py --vault /path/to/vault
"""

import argparse
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from ai_employee import AIEmployee


def main():
    parser = argparse.ArgumentParser(description="AI Employee - Continuous Monitor")
    parser.add_argument(
        "--interval", type=float, default=5.0,
        help="Poll interval in seconds (default: 5)"
    )
    parser.add_argument(
        "--vault", type=str, default=None,
        help="Path to Obsidian vault (default: obsidian_vault/ in repo root)"
    )
    args = parser.parse_args()

    employee = AIEmployee(repo_root=repo_root, poll_interval=args.interval)

    if args.vault:
        vault = Path(args.vault)
        employee.vault_path = vault
        employee.needs_action_path = vault / "Needs_Action"
        employee.done_path = vault / "Done"
        employee.logs_path = vault / "Logs"
        employee.plans_path = vault / "Plans"
        employee._setup_directories()

    employee.run()


if __name__ == "__main__":
    main()
