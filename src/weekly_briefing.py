#!/usr/bin/env python3
"""
Weekly CEO Briefing Generator — Personal AI Employee

Reads the Obsidian vault and produces a structured Monday briefing:
  obsidian_vault/Briefings/YYYY-MM-DD_Monday_Briefing.md

Sections generated:
  1. Executive Summary
  2. Completed Tasks (last 7 days)
  3. Revenue Summary  (from Logs/ JSON, finance-related entries)
  4. Bottlenecks      (failed / rejected tasks)
  5. Suggested Actions

Usage:
    python src/weekly_briefing.py
    python src/weekly_briefing.py --days 14 --vault /custom/vault
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from retry import with_retry, write_vault_log

sys.stdout.reconfigure(line_buffering=True)

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT_PATH = REPO_ROOT / "obsidian_vault"

FINANCE_KEYWORDS = {"payment", "invoice", "bill", "receipt", "revenue",
                    "finance", "salary", "refund", "expense", "cost", "fee"}


# ---------------------------------------------------------------------------
# YAML front-matter parser (no external dependency)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict:
    """
    Extract YAML front-matter from a markdown file without PyYAML.

    Returns a flat dict of key: value strings.
    """
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta


def _parse_date(value: str) -> Optional[datetime]:
    """Parse ISO-ish date strings found in vault front-matter."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Data readers
# ---------------------------------------------------------------------------

def read_done_tasks(done_path: Path, since: datetime) -> dict:
    """
    Scan Done/ folder for task report files completed within the window.

    Returns:
        {
          "completed":  [list of task dicts],
          "failed":     [list of task dicts],
          "total_seen": int,
        }
    """
    completed = []
    failed = []
    total_seen = 0

    for md_file in sorted(done_path.glob("*.md")):
        if md_file.name.startswith("_"):
            continue  # skip _original_* archives

        total_seen += 1
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        meta = _parse_frontmatter(text)
        processed_at = _parse_date(meta.get("processed_at", ""))

        if processed_at and processed_at < since:
            continue  # outside window

        task = {
            "title":        meta.get("title", md_file.stem),
            "status":       meta.get("status", "unknown").lower(),
            "priority":     meta.get("priority", "MEDIUM"),
            "processed_at": meta.get("processed_at", ""),
            "task_id":      meta.get("task_id", md_file.stem),
            "file":         md_file.name,
        }

        if task["status"] in ("completed", "done"):
            completed.append(task)
        elif task["status"] in ("failed", "error"):
            failed.append(task)

    return {
        "completed":  completed,
        "failed":     failed,
        "total_seen": total_seen,
    }


def read_log_events(logs_path: Path, since: datetime) -> dict:
    """
    Scan Logs/YYYY-MM-DD.json files within the window.

    Returns:
        {
          "all_events":     [list of event dicts],
          "finance_events": [list of finance-related event dicts],
          "agent_starts":   int,
          "task_failures":  int,
          "task_rejections": int,
        }
    """
    all_events = []
    finance_events = []
    agent_starts = 0
    task_failures = 0
    task_rejections = 0

    if not logs_path.exists():
        return {
            "all_events": [], "finance_events": [],
            "agent_starts": 0, "task_failures": 0, "task_rejections": 0,
        }

    for json_file in sorted(logs_path.glob("*.json")):
        # Quick date filter: filename is YYYY-MM-DD.json
        try:
            file_date = datetime.strptime(json_file.stem, "%Y-%m-%d")
            if file_date.date() < since.date():
                continue
        except ValueError:
            pass  # non-standard filename — read it anyway

        try:
            entries = json.loads(json_file.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                continue
        except (json.JSONDecodeError, OSError):
            continue

        for entry in entries:
            logged_at_str = entry.get("logged_at", "")
            logged_at = _parse_date(logged_at_str)
            if logged_at and logged_at < since:
                continue

            all_events.append(entry)

            event_type = entry.get("event", "")
            if event_type == "agent_started":
                agent_starts += 1
            elif event_type == "task_failed":
                task_failures += 1
            elif event_type == "task_rejected":
                task_rejections += 1

            # Finance detection: check all string values in the entry
            entry_text = json.dumps(entry).lower()
            if any(kw in entry_text for kw in FINANCE_KEYWORDS):
                finance_events.append(entry)

    return {
        "all_events":      all_events,
        "finance_events":  finance_events,
        "agent_starts":    agent_starts,
        "task_failures":   task_failures,
        "task_rejections": task_rejections,
    }


# ---------------------------------------------------------------------------
# Bottleneck detector
# ---------------------------------------------------------------------------

def detect_bottlenecks(done_data: dict, log_data: dict) -> list[str]:
    """
    Identify recurring problems from failed tasks and log error patterns.

    Returns a list of human-readable bottleneck strings.
    """
    bottlenecks = []

    if done_data["failed"]:
        bottlenecks.append(
            f"{len(done_data['failed'])} task(s) ended in FAILED status — "
            "review error logs for root cause."
        )

    if log_data["task_rejections"] > 0:
        bottlenecks.append(
            f"{log_data['task_rejections']} task(s) were rejected by human reviewer — "
            "approval criteria may need clarification."
        )

    if log_data["task_failures"] > 0:
        bottlenecks.append(
            f"{log_data['task_failures']} task failure event(s) logged — "
            "check Logs/ for detailed error context."
        )

    if log_data["agent_starts"] > 3:
        bottlenecks.append(
            f"Agent restarted {log_data['agent_starts']} time(s) this week — "
            "possible instability or manual restarts."
        )

    if not bottlenecks:
        bottlenecks.append("No critical bottlenecks detected this week.")

    return bottlenecks


# ---------------------------------------------------------------------------
# Suggested actions
# ---------------------------------------------------------------------------

def suggest_actions(done_data: dict, log_data: dict, bottlenecks: list[str]) -> list[str]:
    """Derive actionable suggestions from the week's data."""
    actions = []

    completed_count = len(done_data["completed"])
    if completed_count == 0:
        actions.append("No tasks completed — verify agent is running and watchers are active.")
    elif completed_count < 5:
        actions.append(
            f"Only {completed_count} task(s) completed — consider increasing watcher coverage "
            "(e.g., Gmail watcher, additional file watchers)."
        )
    else:
        actions.append(f"{completed_count} tasks completed — system operating normally.")

    if log_data["finance_events"]:
        actions.append(
            f"Review {len(log_data['finance_events'])} finance-related event(s) in Logs/ "
            "and reconcile with payment records."
        )

    if done_data["failed"]:
        actions.append(
            "Investigate failed tasks in Done/ — re-queue unresolved items to Needs_Action/."
        )

    if log_data["task_rejections"] > 0:
        actions.append(
            "Review rejected tasks in Approved/ and update approval rules in Company_Handbook.md."
        )

    if not actions:
        actions.append("No immediate actions required.")

    return actions


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def render_briefing(
    done_data: dict,
    log_data:  dict,
    bottlenecks: list[str],
    actions: list[str],
    period_start: datetime,
    period_end: datetime,
) -> str:
    """Render the full briefing as a markdown string."""

    now = datetime.now()
    completed = done_data["completed"]
    failed    = done_data["failed"]

    # ── Executive Summary ──────────────────────────────────────────────────
    total_events = len(log_data["all_events"])
    finance_count = len(log_data["finance_events"])
    health = "Healthy" if not failed and log_data["task_failures"] == 0 else "Needs Attention"

    summary_lines = [
        f"The AI Employee processed **{len(completed)} task(s)** "
        f"between {period_start.strftime('%b %d')} and {period_end.strftime('%b %d, %Y')}.",
        f"System health: **{health}**. "
        f"Total audit log events: **{total_events}**. "
        f"Finance-related events: **{finance_count}**.",
    ]
    if failed:
        summary_lines.append(
            f"⚠️ {len(failed)} task(s) failed this week and require review."
        )

    # ── Completed tasks table ──────────────────────────────────────────────
    if completed:
        task_rows = "\n".join(
            f"| {t['processed_at'][:16]} | {t['priority']} | {t['title'][:70]} |"
            for t in sorted(completed, key=lambda x: x["processed_at"], reverse=True)
        )
        completed_section = f"""| Processed At | Priority | Title |
|--------------|----------|-------|
{task_rows}"""
    else:
        completed_section = "_No tasks completed in this period._"

    # ── Failed tasks ───────────────────────────────────────────────────────
    if failed:
        failed_rows = "\n".join(
            f"- `{t['task_id']}` — {t['title'][:70]}"
            for t in failed
        )
    else:
        failed_rows = "_No failed tasks._"

    # ── Revenue / Finance ──────────────────────────────────────────────────
    if log_data["finance_events"]:
        finance_rows = "\n".join(
            f"- `{e.get('logged_at', 'N/A')[:16]}` "
            f"[{e.get('event', 'event')}] "
            f"{e.get('title', e.get('task_id', ''))}"
            for e in log_data["finance_events"][:10]
        )
        revenue_section = (
            f"**{finance_count} finance-related event(s)** detected in audit logs:\n\n"
            + finance_rows
        )
    else:
        revenue_section = (
            "_No revenue or finance events detected in logs this week._\n\n"
            "> Note: Finance events are detected by keywords: "
            + ", ".join(sorted(FINANCE_KEYWORDS)) + "."
        )

    # ── Bottlenecks ────────────────────────────────────────────────────────
    bottleneck_section = "\n".join(f"- {b}" for b in bottlenecks)

    # ── Suggested Actions ──────────────────────────────────────────────────
    actions_section = "\n".join(f"- [ ] {a}" for a in actions)

    # ── Assemble ───────────────────────────────────────────────────────────
    return f"""# Weekly CEO Briefing

**Generated:** {now.strftime("%Y-%m-%d %H:%M:%S")}
**Period:** {period_start.strftime("%Y-%m-%d")} → {period_end.strftime("%Y-%m-%d")}
**Vault:** `obsidian_vault/`

---

## 1. Executive Summary

{chr(10).join(summary_lines)}

---

## 2. Completed Tasks ({len(completed)} this week)

{completed_section}

### Failed Tasks ({len(failed)})

{failed_rows}

---

## 3. Revenue Summary

{revenue_section}

---

## 4. Bottlenecks

{bottleneck_section}

---

## 5. Suggested Actions

{actions_section}

---

_Briefing auto-generated by `src/weekly_briefing.py` — Personal AI Employee_
"""


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_briefing(
    vault_path: Path = VAULT_PATH,
    lookback_days: int = 7,
) -> Path:
    """
    Generate the weekly CEO briefing and write it to Briefings/.

    Returns the path of the created file.
    """
    now = datetime.now()
    period_end   = now
    period_start = now - timedelta(days=lookback_days)

    done_path     = vault_path / "Done"
    logs_path     = vault_path / "Logs"
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading Done/  from: {done_path}", flush=True)
    print(f"Reading Logs/  from: {logs_path}", flush=True)
    print(f"Period: {period_start.date()} → {period_end.date()}", flush=True)

    done_data = read_done_tasks(done_path, since=period_start)
    log_data  = read_log_events(logs_path, since=period_start)

    print(f"  Completed tasks found : {len(done_data['completed'])}", flush=True)
    print(f"  Failed tasks found    : {len(done_data['failed'])}", flush=True)
    print(f"  Audit log events      : {len(log_data['all_events'])}", flush=True)
    print(f"  Finance events        : {len(log_data['finance_events'])}", flush=True)

    bottlenecks = detect_bottlenecks(done_data, log_data)
    actions     = suggest_actions(done_data, log_data, bottlenecks)
    markdown    = render_briefing(done_data, log_data, bottlenecks, actions,
                                  period_start, period_end)

    filename    = f"{now.strftime('%Y-%m-%d')}_Monday_Briefing.md"
    output_path = briefings_dir / filename

    output_path.write_text(markdown, encoding="utf-8")
    print(f"\nBriefing written to: {output_path}", flush=True)

    # Structured audit log — Part 4 requirement
    write_vault_log(logs_path, {
        "event": "weekly_briefing_generated",
        "file": str(output_path),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "completed_tasks": len(done_data["completed"]),
        "failed_tasks": len(done_data["failed"]),
        "finance_events": len(log_data["finance_events"]),
        "lookback_days": lookback_days,
    })

    return output_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly CEO Briefing Generator")
    parser.add_argument(
        "--days", type=int, default=7,
        help="Lookback window in days (default: 7)"
    )
    parser.add_argument(
        "--vault", type=str, default=None,
        help="Path to Obsidian vault (default: obsidian_vault/)"
    )
    args = parser.parse_args()

    vault_path = Path(args.vault) if args.vault else VAULT_PATH

    @with_retry(
        max_attempts=3,
        backoff=(1, 2, 4),
        log_fn=lambda e: write_vault_log(vault_path / "Logs", e),
    )
    def _generate():
        return generate_briefing(vault_path=vault_path, lookback_days=args.days)

    path = _generate()
    print(f"Done. Open: {path}", flush=True)


if __name__ == "__main__":
    main()
