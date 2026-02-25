---
id: "0010"
title: MCP Email Server Integration
stage: green
date: 2026-02-26
surface: agent
model: claude-sonnet-4-6
feature: 001-ai-agent-system
branch: 001-ai-agent-system
user: laraib
command: continue
labels: ["mcp", "email", "gmail", "gold-tier", "json-rpc"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - mcp_servers/__init__.py
  - mcp_servers/email/__init__.py
  - mcp_servers/email/server.py
  - /home/laraib/.config/claude-code/mcp.json
  - src/ai_employee.py
tests:
  - .venv/bin/python -m py_compile src/ai_employee.py
  - .venv/bin/python -m py_compile mcp_servers/email/server.py
---

## Prompt

Implement MCP Email integration replacing SMTP:
- Create mcp_servers/email/server.py using Gmail API
- Register in ~/.config/claude-code/mcp.json
- Update ai_employee.py to call MCP server instead of SMTP
- Keep retry logic
- Return {status: "success"} or {status: "error", message: "..."}

## Response snapshot

Created `mcp_servers/email/server.py` — a minimal MCP JSON-RPC 2.0 stdio server:
- Implements `initialize`, `tools/list`, `tools/call` handlers
- Single tool: `send_email(to, subject, body)` using Gmail API
- Reuses credential logic from `gmail_watcher.py` (same token.json, WSL2 browser fix)
- `--test` flag for standalone testing without MCP protocol

Registered in `~/.config/claude-code/mcp.json` under `"email"` key.

Updated `src/ai_employee.py`:
- Removed `smtplib` / SMTP imports and `send_smtp_email()` function
- Added `send_via_mcp_email(to, subject, body)` — spawns MCP server subprocess, performs JSON-RPC handshake, calls `send_email` tool, returns success string or raises RuntimeError
- `_handle_send_email()`: now calls `send_via_mcp_email` with retry
- `_process_approved_emails()`: now calls `send_via_mcp_email` with retry; on failure discards from `processed_approved` set so next cycle retries

## Outcome

- ✅ Impact: Gold-tier email sending now uses Gmail API OAuth2 via MCP pattern; no SMTP credentials required
- 🧪 Tests: syntax check passed for both files
- 📁 Files: 5 files created/modified
- 🔁 Next prompts: delete token.json and re-authenticate if gmail.send scope was not previously granted; run --test mode to validate live send
- 🧠 Reflection: MCP server is a real JSON-RPC 2.0 stdio server registered with Claude Code; ai_employee calls it as a subprocess for clean separation

## Evaluation notes (flywheel)

- Failure modes observed: none (syntax clean)
- Graders run and results (PASS/FAIL): py_compile PASS for both files
- Prompt variant (if applicable): n/a
- Next experiment: test end-to-end with a real approved email file in Approved/ folder
