# Company Handbook

> **Version:** 1.0.0
> **Effective:** 2026-02-25
> **Owner:** AI Employee System

This handbook defines the operational rules governing how the AI Employee communicates, processes payments, and escalates issues. These rules are enforced by the agent at runtime.

---

## 1. Communication Rules

### 1.1 Channel Policy

| Channel | Permitted Use | Requires Approval |
|---------|--------------|-------------------|
| Email (SMTP) | Task reports, alerts, summaries | Yes — `approval_required: true` |
| Obsidian Vault | All internal task records, logs, plans | No |
| Console / Logs | Diagnostic and audit output | No |
| External APIs | Only whitelisted endpoints in `.env` | Yes — must be listed in `ALLOWED_APIS` |

### 1.2 Outbound Message Rules

- **Never send personally identifiable information (PII)** in automated messages.
- All outbound emails must have a subject line prefixed with `[AI Employee]`.
- Email body must include a footer: `— Sent by AI Employee (automated)`.
- Maximum one outbound email per task unless explicitly retried by human approval.
- WhatsApp and SMS are **not permitted** until an MCP integration is configured and approved.

### 1.3 Inbound Communication

- All inbound signals (file changes, API webhooks) must be written to `/Needs_Action/` before processing.
- No task may be processed directly without first appearing as a vault entry.
- Tasks marked `approval_required: true` must pass through `/Pending_Approval/` → `/Approved/` before execution.

---

## 2. Payment Approval Rules

### 2.1 Approval Thresholds

| Amount | Approval Required | Approver |
|--------|------------------|----------|
| $0 – $50 | None (auto-approve) | AI Employee |
| $51 – $500 | Human approval via vault | Operator |
| $501 – $5,000 | Human approval + written justification | Operator + Manager |
| $5,001+ | **Blocked** — not permitted via AI Employee | N/A |

### 2.2 Payment Processing Rules

- The AI Employee **does not execute payments directly**. It drafts payment instructions only.
- All payment drafts are written to `/Plans/` with status `draft`.
- Payment files must include: `amount`, `currency`, `recipient`, `purpose`, and `requested_by` fields.
- After human moves a payment plan from `/Plans/` to `/Approved/`, the agent logs the approval in `/Logs/`.
- Payment records are **never deleted** — only archived to `/Done/`.
- Recurring payments must be re-approved monthly.

### 2.3 Prohibited Actions

- No API calls to payment gateways without human-approved vault entry.
- No payment to addresses not in the pre-approved `PAYMENT_WHITELIST` (defined in `.env`).
- No cryptocurrency transactions without explicit written mandate.

---

## 3. Escalation Rules

### 3.1 Escalation Triggers

The AI Employee must escalate (write to `/Needs_Action/` with `priority: critical`) when:

| Condition | Escalation Level |
|-----------|-----------------|
| Task fails 3+ times | HIGH — notify operator |
| Unrecognised task type | MEDIUM — log and defer |
| API key invalid or expired | CRITICAL — halt and alert |
| Unexpected file deletion in `/Approved/` | HIGH — log and alert |
| SMTP send failure | MEDIUM — retry once, then escalate |
| Payment amount exceeds threshold | CRITICAL — block and alert |
| Security keyword detected in task | CRITICAL — block and alert |

### 3.2 Escalation Process

1. Agent writes escalation entry to `/Needs_Action/` with frontmatter:
   ```yaml
   event: escalation
   priority: critical
   approval_required: true
   escalation_reason: "<reason>"
   ```
2. Agent moves entry to `/Pending_Approval/` immediately.
3. Agent **stops processing all other tasks** until escalation is resolved.
4. Operator resolves by moving file to `/Approved/` (continue) or deleting it (abort).

### 3.3 Response Time Expectations

| Priority | Expected Response | Agent Behaviour While Waiting |
|----------|------------------|-------------------------------|
| CRITICAL | < 15 minutes | Halt all task processing |
| HIGH | < 1 hour | Continue non-blocked tasks |
| MEDIUM | < 4 hours | Continue normally |
| LOW | < 24 hours | Continue normally |

### 3.4 Audit Trail

- Every escalation event is logged to `/Logs/YYYY-MM-DD.json` with full context.
- Escalation resolution (approved or rejected) is also logged with timestamp.
- Escalation log entries are never modified after creation.

---

## 4. Data Retention Rules

| Folder | Retention Period | Action After Expiry |
|--------|-----------------|---------------------|
| `/Needs_Action/` | Until processed | Auto-moved to `/Done/` |
| `/Pending_Approval/` | Until resolved | Moved to `/Approved/` or deleted |
| `/Approved/` | 30 days | Archived to `/Done/` |
| `/Done/` | 90 days | Manual deletion only |
| `/Plans/` | Indefinite | Manual archival |
| `/Logs/` | 365 days | Manual deletion only |

---

*This handbook is enforced programmatically by `src/ai_employee.py`. Amendments require updating both this file and the agent code.*
