# Research: AI Agent System

**Feature**: 001-ai-agent-system
**Date**: 2026-01-13
**Purpose**: Resolve technical unknowns for implementation plan

## Research Task 1: Language/Platform Selection

**Decision**: Python 3.11+

**Rationale**:
- **Claude API Integration**: Official `anthropic` Python SDK provides robust API access with streaming, error handling, and token counting
- **Template Engine Maturity**: Jinja2 is battle-tested for complex markdown + YAML generation with custom filters and macros
- **File I/O Simplicity**: `pathlib` provides clean, cross-platform file operations; no OS-specific quirks
- **Git Integration**: GitPython library enables programmatic git operations (stash, reset, commit) without shell commands
- **Testing Infrastructure**: pytest ecosystem is comprehensive (coverage, mocking, fixtures, parametrization)
- **Ecosystem Richness**: PyPI has mature packages for YAML parsing, markdown processing, CLI argument parsing
- **Maintainability**: Python's readability and type hints (via `typing` module) aid long-term maintenance

**Alternatives Considered**:
- **TypeScript/Node.js 20+**: Rejected - Claude SDK less mature than Python version; Node.js file I/O more callback-heavy; testing ecosystem fragmented (Jest vs Vitest vs Mocha)
- **Bash scripts**: Rejected - Complex logic (constitution validation, checklist parsing, workflow orchestration) becomes unmaintainable in bash; no native YAML/markdown parsing; testing with bats is limited

**Implementation Notes**:
- Use `anthropic>=0.40.0` for Claude API 4.5 support
- Use `Jinja2>=3.1.0` for template rendering with auto-escaping disabled (markdown passthrough)
- Use `PyYAML>=6.0` for front-matter parsing (use `safe_load` to prevent code execution)
- Use `GitPython>=3.1.0` for git operations (avoid shell injection vulnerabilities)
- Use `click>=8.0` for CLI argument parsing (better than argparse for command groups)
- Python 3.11+ required for `tomllib` (builtin TOML support for `pyproject.toml`)

---

## Research Task 2: Template Engine Selection

**Decision**: Jinja2 with custom markdown filters

**Rationale**:
- **YAML Front-Matter Support**: Can render both YAML and markdown in single pass using block structure
- **Variable Interpolation**: Supports complex expressions (`{{ variable }}`, `{% for %}`, `{% if %}`)
- **Markdown Preservation**: With `autoescape=False`, preserves markdown syntax without HTML escaping
- **Custom Filters**: Can add filters for slug generation, date formatting, ID allocation
- **Template Inheritance**: Enables base templates for common document structure (front-matter + body pattern)
- **Whitespace Control**: `-` syntax (`{{- variable -}}`) enables clean output without extra newlines

**Alternatives Considered**:
- **String Templates (stdlib)**: Rejected - Too simple, no control flow (if/for), manual concatenation error-prone
- **f-strings**: Rejected - Requires code changes for template modifications, no template inheritance
- **Mako**: Rejected - More powerful than needed, security concerns (executes Python code in templates)
- **Mustache**: Rejected - Logic-less philosophy conflicts with need for loops and conditionals

**Implementation Notes**:
- Disable autoescape: `Environment(autoescape=False)` to preserve markdown
- Add custom filters:
  - `slugify(text)`: Convert "Feature Name" → "feature-name" for filenames
  - `iso_date()`: Current date in YYYY-MM-DD format
  - `allocate_id(feature_name, stage)`: Find next available PHR/ADR ID
- Template directory: `.specify/templates/` (read existing templates, don't modify)
- Use `FileSystemLoader` with absolute paths to avoid path resolution issues
- Handle missing variables gracefully: `Environment(undefined=StrictUndefined)` to catch typos

---

## Research Task 3: Workflow State Tracking Pattern

**Decision**: File-based state tracking (`.specify/state.yaml`)

**Rationale**:
- **Persistence**: Survives across terminal sessions (vs in-memory)
- **Simplicity**: Single YAML file easier than multiple git branch markers
- **Git-Friendly**: Text file, diff-able, mergeable (vs binary database)
- **Atomic Updates**: YAML write is atomic at OS level (write temp → rename)
- **Human-Readable**: Developers can inspect state manually if needed
- **Multi-Feature Support**: Can track state for multiple features in parallel

**Alternatives Considered**:
- **Git Branch Encoding**: Rejected - Branch names like `001-feature-name@step=plan` are ugly, break tooling assumptions
- **In-Memory (Session-Based)**: Rejected - Loses state on exit, can't enforce prerequisites across sessions
- **SQLite Database**: Rejected - Overkill for simple state tracking, adds dependency, not diff-able

**Implementation Notes**:
- State file location: `.specify/state.yaml` (git-ignored)
- State schema:
  ```yaml
  features:
    001-ai-agent-system:
      branch: 001-ai-agent-system
      last_step: plan  # Values: specify, plan, tasks, red, green, refactor
      last_updated: 2026-01-13T10:30:00Z
      artifacts:
        spec: specs/001-ai-agent-system/spec.md
        plan: specs/001-ai-agent-system/plan.md
        tasks: null  # Not yet generated
  ```
- Prerequisite validation logic:
  - `/sp.specify`: No prerequisites (creates state entry)
  - `/sp.plan`: Requires `last_step == "specify"`
  - `/sp.tasks`: Requires `last_step == "plan"`
- Update state atomically:
  1. Read current state
  2. Modify in-memory
  3. Write to `.specify/state.yaml.tmp`
  4. Rename `.specify/state.yaml.tmp` → `.specify/state.yaml` (atomic)
- Handle missing state file gracefully (treat as empty state)

---

## Research Task 4: Atomic File Operation Pattern

**Decision**: Temp file + validate + atomic rename pattern

**Rationale**:
- **Error Safety**: Failed write doesn't corrupt existing file
- **Validation Before Commit**: Can validate generated content before making it "official"
- **Cross-Platform**: OS-level rename is atomic on Linux/macOS/Windows (POSIX guarantee)
- **No Rollback Needed**: If validation fails, just delete temp file (no undo stack)
- **Performance**: Single rename syscall is fast
- **Simplicity**: No transaction log or complex rollback logic

**Alternatives Considered**:
- **Direct Write with Try/Catch**: Rejected - Partial writes corrupt file if error occurs mid-write
- **Transactional File API**: Rejected - Python has no builtin transactional file system
- **Custom Rollback Logic**: Rejected - Complex, requires tracking all file modifications, error-prone

**Implementation Notes**:
- Pattern for all file writes:
  ```python
  import tempfile
  import os
  from pathlib import Path

  def atomic_write(target_path: Path, content: str):
      # 1. Write to temp file in same directory (ensures same filesystem for atomic rename)
      temp_fd, temp_path = tempfile.mkstemp(
          dir=target_path.parent,
          prefix=f".{target_path.name}.",
          suffix=".tmp"
      )
      try:
          with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
              f.write(content)
          # 2. Validate (optional - e.g., YAML parseable, no placeholders)
          validate_content(Path(temp_path))
          # 3. Atomic rename (overwrites target if exists)
          os.replace(temp_path, target_path)  # replace() is atomic
      except Exception:
          # 4. Clean up temp file on any error
          Path(temp_path).unlink(missing_ok=True)
          raise
  ```
- Use `os.replace()` not `os.rename()` (replace works even if target exists on Windows)
- Temp file in same directory as target ensures same filesystem (cross-filesystem moves aren't atomic)
- Validation can include: YAML parsing, placeholder detection, required section checks

---

## Research Task 5: Quality Validation Integration

**Decision**: Rule engine with markdown AST parsing

**Rationale**:
- **Accuracy**: AST parsing detects actual structure (e.g., "no implementation details" checks for code fences with language tags)
- **Speed**: Fast enough for real-time validation (<1 second requirement) - no LLM call needed
- **Deterministic**: Same input always produces same result (vs LLM variability)
- **Offline**: Works without API calls (no latency, no cost, no rate limits)
- **Extensible**: Easy to add new rules by adding functions to rule registry

**Alternatives Considered**:
- **LLM-Based Validation**: Rejected - Too slow (>1 second), costs API tokens, non-deterministic results
- **Regex-Only Validation**: Rejected - Can't handle structural checks (e.g., "success criteria measurable"), misses context
- **Manual Checklist**: Rejected - Requirement SC-002 mandates automated validation (100% pass rate)

**Implementation Notes**:
- Use `markdown-it-py` for AST parsing (Python port of markdown-it.js)
- Rule engine structure:
  ```python
  from dataclasses import dataclass
  from typing import Callable, List

  @dataclass
  class ValidationRule:
      rule_id: str
      description: str
      check: Callable[[str], bool]  # Takes markdown content, returns pass/fail
      error_template: str

  class QualityValidator:
      def __init__(self):
          self.rules: dict[str, List[ValidationRule]] = {
              'specification': [...],
              'plan': [...],
              'tasks': [...]
          }

      def validate(self, document_type: str, content: str) -> List[str]:
          """Returns list of error messages (empty if all pass)"""
          errors = []
          for rule in self.rules[document_type]:
              if not rule.check(content):
                  errors.append(rule.error_template.format(...))
          return errors
  ```
- Example rule implementations:
  - `no_implementation_details`: Parse AST, detect code fences with language tags (python, typescript, rust, etc.), flag as violation
  - `testable_requirements`: Parse AST, find "FR-XXX" lines, check for modal verbs (MUST), concrete actions
  - `measurable_success_criteria`: Parse AST, find "SC-XXX" lines, check for numeric patterns (percentages, counts, time units)
  - `no_clarification_markers`: Simple regex search for `[NEEDS CLARIFICATION` pattern
- Load rules from `contracts/validation-rules.yaml` (defined in plan)
- Validation runs automatically after document generation, before atomic rename

---

## Summary

All research tasks complete. Key decisions:

1. **Language**: Python 3.11+ (Claude SDK, Jinja2, pytest)
2. **Templates**: Jinja2 with custom markdown filters
3. **State**: File-based `.specify/state.yaml` for workflow tracking
4. **Atomicity**: Temp file + validate + rename pattern
5. **Validation**: Rule engine with markdown AST parsing

These decisions resolve all NEEDS CLARIFICATION markers from plan.md Technical Context. Ready to proceed to Phase 1 (Design & Contracts).
