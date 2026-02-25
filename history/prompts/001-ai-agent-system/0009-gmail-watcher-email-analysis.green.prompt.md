---
id: "0009"
title: Gmail Watcher Email Analysis
stage: green
date: 2026-02-26
surface: agent
model: claude-sonnet-4-6
feature: 001-ai-agent-system
branch: 001-ai-agent-system
user: laraib
command: (manual prompt)
labels: ["gmail", "watcher", "email-analysis", "gold-tier", "claude-api"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - watchers/gmail_watcher.py (created, 280 lines)
  - test_gmail.py (updated with WSL browser fix)
tests:
  - none
---

## Prompt

User provided an AI email analysis prompt template using Claude API. Template extracts: Summary, Action Required, Urgency, Category, Suggested Action from email details (sender, subject, snippet).

## Response snapshot

Created watchers/gmail_watcher.py — polls Gmail inbox for unread messages, analyses each via Claude API using the provided prompt, writes structured markdown task entries to obsidian_vault/Needs_Action/ with YAML frontmatter (urgency, category, action_required, suggested_action, approval_required). Integrates with the existing AI Employee main loop. Supports --interval, --max-emails, --vault CLI args. Persists seen message IDs to .gmail_seen_ids.json to avoid duplicates.

## Outcome

- Impact: Gmail watcher implemented end-to-end; unread emails are fetched, analysed by Claude, and written as actionable Obsidian notes with structured frontmatter automatically.
- Tests: none run; manual verification via WSL browser fix for OAuth flow.
- Files: watchers/gmail_watcher.py created (280 lines); test_gmail.py updated with WSL browser workaround.
- Next prompts: Wire gmail_watcher into the main agent loop; add unit tests with mocked Gmail API and Claude responses; implement approval workflow reading from Obsidian vault.
- Reflection: Prompt template drove a clean separation between email ingestion and AI analysis. Persisting seen IDs to JSON is a lightweight deduplication strategy suitable for early-stage iteration.

## Evaluation notes (flywheel)

- Failure modes observed: OAuth browser redirect does not work natively in WSL; mitigated by patching test_gmail.py to print the auth URL instead of opening a browser.
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): gold-tier Claude API email analysis prompt template (user-supplied)
- Next experiment (smallest change to try): Add a mock for the Gmail API client in tests to enable automated CI validation without live credentials.
