#!/usr/bin/env python3
"""
AI Employee - Autonomous Task Processing Agent

The AI Employee is the core orchestrator that monitors, processes, and executes
tasks autonomously while maintaining human oversight through the Obsidian vault.

Purpose:
    Act as a personal AI assistant that monitors for work, processes tasks,
    and takes action while keeping humans informed through structured logs.

Responsibilities:
    1. MONITOR: Watch Obsidian vault for pending tasks (Needs_Action/)
    2. PROCESS: Analyze and prioritize incoming tasks
    3. EXECUTE: Perform actions (code changes, file ops, API calls)
    4. REPORT: Log results back to Obsidian vault (Done/, Logs/)
    5. LEARN: Track patterns and improve over time (via PHRs)

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                      AI EMPLOYEE                             │
    ├─────────────────────────────────────────────────────────────┤
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
    │  │ Monitor │→ │ Process │→ │ Execute │→ │ Report  │        │
    │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
    │       ↑                                       │              │
    │       └───────────── Loop ───────────────────┘              │
    ├─────────────────────────────────────────────────────────────┤
    │  Integrations:                                               │
    │  - File Watcher (detect changes)                            │
    │  - Obsidian Vault (task queue & reports)                    │
    │  - Claude API (AI reasoning)                                │
    │  - Git (version control)                                    │
    │  - Health Monitor (Platinum)                                │
    │  - Vault Sync (Platinum)                                    │
    └─────────────────────────────────────────────────────────────┘
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from retry import with_retry, mask_secrets
from health_monitor import HealthMonitor
from vault_sync import VaultSync

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


def parse_datetime(value: any) -> Optional[datetime]:
    """
    Safely parse a datetime from YAML metadata.

    Handles:
    - None → returns None (caller decides fallback)
    - datetime → returns as-is (PyYAML auto-converted)
    - str → parses via fromisoformat()
    - other → raises TypeError with clear message

    Args:
        value: The value to parse (None, datetime, or ISO string)

    Returns:
        Parsed datetime object, or None if value was None
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace(" ", "T"))
        except ValueError as e:
            raise ValueError(f"Invalid ISO datetime string: {value!r}") from e

    raise TypeError(
        f"Expected None, datetime, or str; got {type(value).__name__}: {value!r}"
    )


MCP_EMAIL_SERVER = Path(__file__).resolve().parent.parent / "mcp_servers" / "email" / "server.py"


def send_via_mcp_email(to: str, subject: str, body: str) -> str:
    """
    Send an email by calling the MCP Email Server subprocess.

    Spawns mcp_servers/email/server.py, performs the JSON-RPC handshake,
    calls the send_email tool, and returns a success message.

    Raises RuntimeError on failure so callers can handle it uniformly.
    """
    if not MCP_EMAIL_SERVER.exists():
        raise RuntimeError(f"MCP email server not found: {MCP_EMAIL_SERVER}")

    proc = subprocess.Popen(
        [sys.executable, str(MCP_EMAIL_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    def _rpc(payload: dict) -> dict:
        """Write one JSON-RPC message and read one response line."""
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout unexpectedly")
        return json.loads(line)

    try:
        # 1. initialize handshake
        _rpc({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ai_employee", "version": "0.1.0"},
            },
        })
        # 2. initialized notification (no response expected)
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        # 3. call send_email tool
        response = _rpc({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {
                "name": "send_email",
                "arguments": {"to": to, "subject": subject, "body": body},
            },
        })

    finally:
        proc.stdin.close()
        proc.wait(timeout=10)

    # Parse result
    if "error" in response:
        raise RuntimeError(f"MCP error: {response['error'].get('message', response['error'])}")

    result_json = response.get("result", {})
    content = result_json.get("content", [{}])
    result = json.loads(content[0].get("text", "{}")) if content else {}

    if result.get("status") != "success":
        raise RuntimeError(f"Email send failed: {result.get('message', 'unknown error')}")

    return f"Email sent to {to} via Gmail API (subject: {subject})"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class TaskStatus(Enum):
    """Task lifecycle status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


@dataclass
class Task:
    """Represents a task for the AI Employee to process."""
    id: str
    title: str
    description: str
    source_file: Path
    created_at: datetime
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    metadata: dict = field(default_factory=dict)
    result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source_file": str(self.source_file),
            "created_at": self.created_at.isoformat(),
            "priority": self.priority.name,
            "status": self.status.value,
            "metadata": self.metadata,
            "result": self.result,
            "error": self.error,
        }


class AIEmployee:
    """
    Autonomous AI Employee that processes tasks from Obsidian vault.

    The AI Employee continuously monitors for new tasks, processes them
    using Claude API, and reports results back to the vault.

    Platinum-tier additions:
    - HealthMonitor: heartbeat + service status written to health_status.json
    - VaultSync: file-change detection logged per cycle
    - Security: secrets masked before any audit-log write
    - Enhanced Dashboard: live health, uptime, email counters
    - New event types: email_received, email_processed, approval_requested,
                       approval_granted, health_heartbeat
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        api_key: Optional[str] = None,
        poll_interval: float = 5.0,
    ):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.vault_path = self.repo_root / "obsidian_vault"
        self.needs_action_path = self.vault_path / "Needs_Action"
        self.pending_approval_path = self.vault_path / "Pending_Approval"
        self.approved_path = self.vault_path / "Approved"
        self.done_path = self.vault_path / "Done"
        self.logs_path = self.vault_path / "Logs"
        self.plans_path = self.vault_path / "Plans"
        self.poll_interval = poll_interval
        self.approval_poll_interval = 3.0

        # API setup
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                print("Warning: anthropic package not installed")

        # Task queue
        self.task_queue: list[Task] = []
        self.processed_files: set[str] = set()
        self.processed_approved: set[str] = set()  # tracks approved email drafts sent

        # Handlers for different task types
        self.handlers: dict[str, Callable] = {
            "file_change": self._handle_file_change,
            "code_review": self._handle_code_review,
            "documentation": self._handle_documentation,
            "test": self._handle_test,
            "send_email": self._handle_send_email,
            "general": self._handle_general,
        }

        # Ensure directories exist
        self._setup_directories()

        # Platinum: Health monitor
        self.health = HealthMonitor(self.logs_path)
        self.health.set_service_status("ai_employee", "starting")

        # Platinum: Vault sync tracker
        self.vault_sync = VaultSync(
            vault_path=self.vault_path,
            log_fn=self._write_audit_log,
        )

    def _setup_directories(self) -> None:
        """Create required vault directories."""
        for path in [self.needs_action_path, self.pending_approval_path,
                     self.approved_path, self.done_path, self.logs_path, self.plans_path]:
            path.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        """Get current timestamp string."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log a message with timestamp."""
        print(f"[{self._timestamp()}] [{level}] {message}")

    def _write_audit_log(self, entry: dict) -> None:
        """
        Append a structured JSON audit entry to /Logs/YYYY-MM-DD.json.

        Secrets are automatically masked by retry.write_vault_log before
        anything is persisted to disk.
        """
        from retry import write_vault_log
        write_vault_log(self.logs_path, entry)

    def _regenerate_dashboard(self) -> None:
        """
        Regenerate Dashboard.md with a live summary of the vault state.

        Platinum additions: health status, uptime, email counter,
        last heartbeat, service statuses.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

        needs_action_files = sorted(
            f for f in self.needs_action_path.glob("*.md") if not f.name.startswith("_")
        )
        pending_files = sorted(self.pending_approval_path.glob("*.md"))
        done_today = sorted(
            f for f in self.done_path.glob("*.md")
            if f.stat().st_mtime >= today_start
        ) if self.done_path.exists() else []

        def file_list(files: list) -> str:
            if not files:
                return "*(empty)*\n"
            return "".join(f"- `{f.name}`\n" for f in files)

        ai_status = "Enabled" if self.client else "Disabled (no API key)"
        log_file = self.logs_path / f"{datetime.now().strftime('%Y-%m-%d')}.json"

        # Platinum: pull health data
        health = self.health.to_dict()
        uptime = health.get("uptime", "00:00:00")
        emails_today = health.get("emails_processed_today", 0)
        error_count = health.get("error_count", 0)
        last_heartbeat = health.get("heartbeat") or "—"
        last_email = health.get("last_email") or "—"

        # Service rows for health table
        services = health.get("services", {})
        service_rows = "\n".join(
            f"| {svc} | {status} |"
            for svc, status in sorted(services.items())
        ) or "| — | — |"

        content = f"""# AI Employee Dashboard

> **Last Updated:** {now_str}
> **Cycle Interval:** {int(self.poll_interval)}s

---

## Needs Action ({len(needs_action_files)} items)

{file_list(needs_action_files)}
---

## Pending Approval ({len(pending_files)} items)

{file_list(pending_files)}
---

## Completed Today ({len(done_today)} items)

{file_list(done_today)}
---

## System Health

| Component | Status |
|-----------|--------|
| Agent Loop | Running |
| AI (Claude) | {ai_status} |
| Vault Path | `{self.vault_path}` |
| Log File | `{log_file.name}` |
| Uptime | {uptime} |
| Errors | {error_count} |

---

## Email Activity

| Metric | Value |
|--------|-------|
| Processed Today | {emails_today} |
| Last Email | {last_email[:60] if last_email != "—" else "—"} |
| Last Heartbeat | {last_heartbeat[:19] if last_heartbeat != "—" else "—"} |

---

## Service Status

| Service | Status |
|---------|--------|
{service_rows}

---

*Auto-generated by AI Employee — updates every {int(self.poll_interval)}s*
"""
        dashboard_path = self.vault_path / "Dashboard.md"
        dashboard_path.write_text(content, encoding="utf-8")

    # =========================================================================
    # MONITOR: Watch for new tasks
    # =========================================================================

    def scan_for_tasks(self) -> list[Task]:
        """Scan Needs_Action folder for new tasks."""
        new_tasks = []

        if not self.needs_action_path.exists():
            return new_tasks

        for file_path in self.needs_action_path.glob("*.md"):
            # Skip action plan and already processed
            if file_path.name.startswith("_"):
                continue
            if str(file_path) in self.processed_files:
                continue

            task = self._parse_task_file(file_path)
            if task:
                new_tasks.append(task)
                self.processed_files.add(str(file_path))
                # Platinum: log email_received for email-sourced tasks
                if task.metadata.get("source") == "gmail":
                    self._write_audit_log({
                        "event":   "email_received",
                        "task_id": task.id,
                        "subject": task.metadata.get("subject", ""),
                        "from":    task.metadata.get("from", ""),
                    })

        return new_tasks

    def _parse_task_file(self, file_path: Path) -> Optional[Task]:
        """Parse a task file from Obsidian vault."""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract front matter
            metadata = {}
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    import yaml
                    metadata = yaml.safe_load(parts[1]) or {}
                    content = parts[2].strip()

            # Determine task type and priority
            event = metadata.get("event", "general")
            priority = self._determine_priority(event, metadata)

            task = Task(
                id=file_path.stem,
                title=f"{event.upper()}: {metadata.get('file', file_path.name)}",
                description=content,
                source_file=file_path,
                created_at=parse_datetime(metadata.get("timestamp")) or datetime.now(),
                priority=priority,
                metadata=metadata,
            )
            return task

        except Exception as e:
            self._log(f"Error parsing {file_path}: {e}", "ERROR")
            self.health.increment_error()
            return None

    def _determine_priority(self, event: str, metadata: dict) -> TaskPriority:
        """Determine task priority based on event type."""
        priority_map = {
            "created": TaskPriority.MEDIUM,
            "modified": TaskPriority.LOW,
            "deleted": TaskPriority.HIGH,
            "error": TaskPriority.CRITICAL,
            "security": TaskPriority.CRITICAL,
            "test_failure": TaskPriority.HIGH,
        }
        return priority_map.get(event, TaskPriority.MEDIUM)

    # =========================================================================
    # APPROVAL: Human-in-the-loop gate
    # =========================================================================

    def _requires_approval(self, task: Task) -> bool:
        """Check if task frontmatter has approval_required: true."""
        return bool(task.metadata.get("approval_required", False))

    def _wait_for_approval(self, task: Task) -> bool:
        """
        Move task to Pending_Approval/ and block until it appears in Approved/.

        The human moves the file from Pending_Approval/ to Approved/ to grant
        approval. This method polls Approved/ every 3 seconds.

        Returns True if approved, False if the file was deleted (rejected).
        """
        filename = task.source_file.name
        pending_path = self.pending_approval_path / filename
        approved_path = self.approved_path / filename

        # Move from Needs_Action to Pending_Approval
        task.source_file.rename(pending_path)
        task.source_file = pending_path
        task.status = TaskStatus.BLOCKED

        self._log(f"APPROVAL REQUIRED: {task.title}")
        self._log(f"  Waiting for: {filename}")
        self._log(f"  Move to approve: {self.approved_path}/")
        self._log(f"  Delete to reject: remove from {self.pending_approval_path}/")

        # Platinum: log approval_requested
        self._write_audit_log({
            "event":    "approval_requested",
            "task_id":  task.id,
            "title":    task.title,
            "filename": filename,
        })

        # Block until approved or rejected
        while True:
            # Check if file appeared in Approved/
            if approved_path.exists():
                self._log(f"APPROVED: {task.title}", "SUCCESS")
                task.source_file = approved_path
                # Platinum: log approval_granted
                self._write_audit_log({
                    "event":   "approval_granted",
                    "task_id": task.id,
                    "title":   task.title,
                })
                return True

            # Check if file was deleted from Pending_Approval (rejection)
            if not pending_path.exists():
                self._log(f"REJECTED: {task.title} (file removed)", "WARN")
                self._write_audit_log({
                    "event":   "task_rejected",
                    "task_id": task.id,
                    "title":   task.title,
                })
                return False

            time.sleep(self.approval_poll_interval)

    # =========================================================================
    # PROCESS: Analyze and prioritize tasks
    # =========================================================================

    def process_task(self, task: Task) -> Task:
        """Process a single task."""
        self._log(f"Processing: {task.title}")
        task.status = TaskStatus.IN_PROGRESS

        try:
            # Determine handler
            event = task.metadata.get("event", "general")
            handler = self.handlers.get(event, self.handlers["general"])

            # Execute handler
            result = handler(task)

            task.result = result
            task.status = TaskStatus.COMPLETED
            self._log(f"Completed: {task.title}", "SUCCESS")

            # Platinum: log email_processed for email tasks
            if task.metadata.get("source") == "gmail":
                self.health.set_last_email(task.metadata.get("subject", task.title))
                self._write_audit_log({
                    "event":   "email_processed",
                    "task_id": task.id,
                    "subject": task.metadata.get("subject", ""),
                    "status":  "completed",
                })

        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            self._log(f"Failed: {task.title} - {e}", "ERROR")
            self.health.increment_error()
            self._write_audit_log({
                "event":    "task_failed",
                "task_id":  task.id,
                "title":    task.title,
                "error":    str(e),
                "priority": task.priority.name,
            })

        return task

    # =========================================================================
    # EXECUTE: Task handlers
    # =========================================================================

    def _handle_file_change(self, task: Task) -> str:
        """Handle file change events."""
        file_path = task.metadata.get("file", "unknown")
        event = task.metadata.get("event", "unknown")

        if not self.client:
            return f"Logged {event} event for {file_path} (AI analysis disabled)"

        # Get AI analysis
        analysis = self._get_ai_analysis(task)
        return analysis

    def _handle_code_review(self, task: Task) -> str:
        """Handle code review requests."""
        if not self.client:
            return "Code review queued (AI disabled)"

        return self._get_ai_analysis(task, focus="code_review")

    def _handle_documentation(self, task: Task) -> str:
        """Handle documentation tasks."""
        return "Documentation task processed"

    def _handle_test(self, task: Task) -> str:
        """Handle test-related tasks."""
        return "Test task processed"

    def _handle_general(self, task: Task) -> str:
        """Handle general tasks."""
        if not self.client:
            return "Task acknowledged (AI disabled)"

        return self._get_ai_analysis(task)

    def _handle_send_email(self, task: Task) -> str:
        """Handle send_email events. Requires 'to' and 'subject' in frontmatter."""
        to = task.metadata.get("to")
        subject = task.metadata.get("subject")

        if not to or not subject:
            return "EMAIL FAILED: 'to' and 'subject' required in frontmatter"

        body = task.description or "(no body)"

        @with_retry(max_attempts=3, backoff=(1, 2, 4), log_fn=self._write_audit_log)
        def _send():
            return send_via_mcp_email(to=to, subject=subject, body=body)

        try:
            result = _send()
            self._log(f"Email sent: {to} — {subject}", "SUCCESS")
            self._write_audit_log({
                "event":   "email_sent",
                "to":      to,
                "subject": subject,
                "task_id": task.id,
            })
            return result
        except Exception as e:
            self._log(f"Email failed: {e}", "ERROR")
            self.health.increment_error()
            self._write_audit_log({
                "event":   "system_error",
                "context": "send_email",
                "to":      to,
                "subject": subject,
                "error":   str(e),
            })
            return f"EMAIL FAILED: {e}"

    def _load_prompt_template(self) -> str:
        """Load the task processor prompt template."""
        template_path = self.repo_root / "src" / "prompts" / "task_processor.prompt.md"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        # Fallback to simple prompt if template not found
        return """You are an AI Employee. Analyze this task and respond with:
1. Task answer
2. Action block: [ACTION: NONE], [ACTION: EMAIL], or [ACTION: WHATSAPP]

Task content:
{{TASK_BODY}}"""

    def _get_ai_analysis(self, task: Task, focus: str = "general") -> str:
        """Get AI analysis for a task using the prompt template."""
        if not self.client:
            return "AI analysis unavailable"

        try:
            # Build task body for template
            task_body = f"""---
title: {task.title}
priority: {task.priority.name}
created: {task.created_at.isoformat()}
event: {task.metadata.get('event', 'general')}
file: {task.metadata.get('file', 'N/A')}
---

{task.description}
"""
            # Load and populate template
            template = self._load_prompt_template()
            prompt = template.replace("{{TASK_BODY}}", task_body)

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()

        except Exception as e:
            self.health.increment_error()
            return f"AI analysis error: {e}"

    # =========================================================================
    # APPROVED EMAIL SENDER: Human-approved email drafts
    # =========================================================================

    def _process_approved_emails(self) -> None:
        """
        Scan Approved/ for email-draft files identified by a 'to:' frontmatter field.

        Regular task-approval files (moved there by _wait_for_approval) do not
        contain 'to:', so they are ignored by this method and handled by the
        normal process_task / report_task flow.

        On success:  log email_sent event, move file to Done/.
        On failure:  log system_error event, leave file in Approved/ for retry.
        """
        if not self.approved_path.exists():
            return

        for md_file in sorted(self.approved_path.glob("*.md")):
            file_key = str(md_file)
            if file_key in self.processed_approved:
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                metadata = {}
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        import yaml
                        metadata = yaml.safe_load(parts[1]) or {}

                to = metadata.get("to") or metadata.get("To")
                if not to:
                    continue  # not an email draft — skip

                subject = str(
                    metadata.get("subject") or metadata.get("Subject") or "(no subject)"
                )
                # Body is the content after the front-matter block
                body_text = (
                    content.split("---", 2)[-1].strip()
                    if content.count("---") >= 2
                    else content
                )

                # Mark as processed before attempting send to prevent
                # duplicate sends on subsequent cycles if the file survives
                self.processed_approved.add(file_key)

                @with_retry(max_attempts=3, backoff=(1, 2, 4), log_fn=self._write_audit_log)
                def _send_approved(to=to, subject=subject, body=body_text):
                    return send_via_mcp_email(to=to, subject=subject, body=body)

                try:
                    _send_approved()
                    self._log(f"Approved email sent to {to}: {subject}", "SUCCESS")
                    self._write_audit_log({
                        "event":       "email_sent",
                        "to":          to,
                        "subject":     subject,
                        "source_file": str(md_file),
                    })
                    dest = self.done_path / (
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        f"_email_sent_{md_file.name}"
                    )
                    md_file.rename(dest)
                    self._log(f"Moved to Done: {dest.name}")

                except Exception as e:
                    self._log(f"Approved email failed for {to}: {e}", "ERROR")
                    self.health.increment_error()
                    self._write_audit_log({
                        "event":       "system_error",
                        "context":     "approved_email_send",
                        "to":          to,
                        "subject":     subject,
                        "error":       str(e),
                        "source_file": str(md_file),
                    })
                    # Leave file in Approved/ for retry on next cycle
                    self.processed_approved.discard(file_key)

            except Exception as e:
                self._log(f"Error reading approved file {md_file.name}: {e}", "ERROR")
                self.health.increment_error()

    # =========================================================================
    # REPORT: Log results to Obsidian
    # =========================================================================

    def report_task(self, task: Task) -> Path:
        """Write task result to Done folder and emit a structured JSON audit log entry."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{task.status.value}_{task.id}.md"
        report_path = self.done_path / filename

        content = f"""---
task_id: {task.id}
title: {task.title}
status: {task.status.value}
priority: {task.priority.name}
processed_at: {self._timestamp()}
original_file: {task.source_file}
---

# Task Report: {task.title}

## Status: {task.status.value.upper()}

## Original Task
- **Created**: {task.created_at}
- **Source**: `{task.source_file}`
- **Priority**: {task.priority.name}

## Result

{task.result or "No result"}

"""
        if task.error:
            content += f"""## Error

```
{task.error}
```
"""

        report_path.write_text(content, encoding="utf-8")
        self._log(f"Report saved: {report_path}")

        # Move original task file to Done
        if task.source_file.exists():
            archive_path = self.done_path / f"_original_{task.source_file.name}"
            task.source_file.rename(archive_path)

        # Write structured audit log entry
        self._write_audit_log({
            "event":       "task_completed",
            "task_id":     task.id,
            "title":       task.title,
            "status":      task.status.value,
            "priority":    task.priority.name,
            "created_at":  task.created_at.isoformat(),
            "result":      task.result,
            "error":       task.error,
            "report_file": str(report_path),
            "source_file": str(task.source_file),
        })

        return report_path

    # =========================================================================
    # MAIN LOOP
    # =========================================================================

    def run_once(self) -> list[Task]:
        """Run one iteration of task processing."""
        # Platinum: vault sync check (detect file movements)
        self.vault_sync.check()

        # Scan for new tasks
        new_tasks = self.scan_for_tasks()

        if new_tasks:
            self._log(f"Found {len(new_tasks)} new task(s)")

            # Sort by priority
            new_tasks.sort(key=lambda t: t.priority.value)

            # Process each task
            for task in new_tasks:
                # Human-in-the-loop gate
                if self._requires_approval(task):
                    approved = self._wait_for_approval(task)
                    if not approved:
                        self._log(f"Skipped (rejected): {task.title}")
                        continue

                self.process_task(task)
                self.report_task(task)

        # Process any human-approved email drafts
        self._process_approved_emails()

        # Platinum: health heartbeat
        self.health.set_service_status("ai_employee", "running")
        self.health.heartbeat()
        self._write_audit_log({"event": "health_heartbeat",
                                "uptime": self.health.to_dict()["uptime"]})

        # Regenerate dashboard on every cycle
        self._regenerate_dashboard()

        return new_tasks

    def run(self) -> None:
        """Run the AI Employee continuously."""
        self._log("=" * 60)
        self._log("AI EMPLOYEE STARTING")
        self._log("=" * 60)
        self._log(f"Vault: {self.vault_path}")
        self._log(f"AI: {'Enabled' if self.client else 'Disabled'}")
        self._log(f"Poll interval: {self.poll_interval}s")
        self._log("=" * 60)
        self._log("Monitoring for tasks... (Ctrl+C to stop)\n")

        self.health.set_service_status("ai_employee", "running")
        self._write_audit_log({"event": "agent_started",
                                "vault": str(self.vault_path),
                                "ai_enabled": self.client is not None,
                                "poll_interval": self.poll_interval})

        try:
            while True:
                self.run_once()
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            self.health.set_service_status("ai_employee", "stopped")
            self.health.heartbeat()
            self._write_audit_log({"event": "agent_stopped"})
            self._log("\nAI Employee stopped.")

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_status(self) -> dict:
        """Get current AI Employee status."""
        return {
            "vault_path": str(self.vault_path),
            "ai_enabled": self.client is not None,
            "pending_tasks": len(list(self.needs_action_path.glob("*.md"))),
            "pending_approval": len(list(self.pending_approval_path.glob("*.md"))),
            "processed_count": len(self.processed_files),
            "poll_interval": self.poll_interval,
            "health": self.health.to_dict(),
        }


def main() -> None:
    """Main entry point."""
    repo_root = Path(__file__).parent.parent
    employee = AIEmployee(repo_root=repo_root)
    employee.run()


if __name__ == "__main__":
    main()
