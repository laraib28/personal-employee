# Implementation Plan: AI Agent System

**Branch**: `001-ai-agent-system` | **Date**: 2026-01-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-agent-system/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build an AI agent system that executes governed workflows (specification, planning, task generation, constitution management, ADR creation) with strict constitution compliance enforcement and communication drafting capabilities. The system accepts natural language input via CLI commands, generates structured documentation artifacts, validates quality through checklists, logs all operations in PHRs, and enforces one-question-at-a-time clarification policy.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: anthropic (Claude API SDK), Jinja2 (template engine), PyYAML (YAML parser), pathlib (file I/O), GitPython (git integration)
**Storage**: File system (markdown files, YAML front-matter, directory structure per SpecKit Plus conventions) - no database required
**Testing**: pytest with pytest-cov for coverage, pytest-mock for mocking
**Target Platform**: CLI (Linux/macOS/Windows WSL), integrates with existing SpecKit Plus template system
**Project Type**: Single CLI application with modular command handlers
**Performance Goals**: Specification generation <5 minutes, constitution compliance check <1 second overhead per workflow step, PHR creation non-blocking
**Constraints**: Must integrate with existing `.specify/` structure, must not modify SpecKit Plus core templates without explicit approval, must preserve manual edits in agent context files between automated markers
**Scale/Scope**: Handles 5 workflow commands (/sp.specify, /sp.plan, /sp.tasks, /sp.constitution, /sp.adr), generates 8 entity types (spec, plan, tasks, constitution, ADR, PHR, communication draft, quality checklist), supports unlimited features per repository

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Constitution Validation

**Principle I (Human Never Writes, AI Always Generates)**:
- ✅ PASS: Agent generates all documentation artifacts automatically
- ✅ PASS: Human provides only intent (command invocation + feature description)
- ✅ PASS: No manual editing of generated files required

**Principle II (Role Clarity)**:
- ✅ PASS: Agent acts as System Architect, Product Planner, Technical Writer
- ✅ PASS: Human role limited to command invocation and clarification responses
- ✅ PASS: Clear separation maintained

**Principle III (Tool Authority & MCP Compliance)**:
- ✅ PASS: File system is read-only knowledge base for templates
- ✅ PASS: Generated documents are finalized (no drafts in Obsidian/system record)
- ✅ PASS: Missing context triggers halt and question (no assumptions)

**Principle IV (One Question at a Time)**:
- ✅ PASS: Maximum 3 questions total, asked sequentially
- ✅ PASS: Execution pauses until answer received
- ✅ PASS: No question bundling

**Principle V (Mandatory Development Flow)**:
- ✅ PASS: Workflow enforces 11-step order (spec → plan → tasks → implement → validate)
- ✅ PASS: No step skipping allowed
- ⚠️ RISK: Current implementation is manual (human invokes each command) - needs workflow state tracking

**Principle VI (No-Vibe Coding)**:
- ✅ PASS: All decisions documented in plans, ADRs, or assumptions sections
- ✅ PASS: No exploratory/temporary code
- ✅ PASS: Every line has documented purpose

**Principle VII (Documentation Law)**:
- ✅ PASS: All outputs structured (YAML front-matter + markdown sections)
- ✅ PASS: Assumptions explicitly declared
- ✅ PASS: Each document answers: what/why/how/boundaries

**Principle VIII (Output Standards)**:
- ✅ PASS: Clean, copy-paste ready markdown
- ✅ PASS: No explanatory fluff in generated files
- ✅ PASS: Directly usable

**Principle IX (Error & Failure Handling)**:
- ✅ PASS: Comprehensive error documentation required
- ✅ PASS: No silent fixes (all logged in PHRs)
- ⚠️ RISK: Error recovery strategy needs explicit design

**Principle X (Termination & Reset Rule)**:
- ✅ PASS: Halt on violations (compliance check gates)
- ⚠️ RISK: State revert mechanism needs explicit design (git reset? undo stack?)

**Communication Authority**:
- ✅ PASS: Email/WhatsApp drafts only (no sending)
- ✅ PASS: Explicit approval gate required
- ✅ PASS: All messages logged

### Gates Summary

**BLOCKING VIOLATIONS**: None

**RISKS REQUIRING DESIGN ATTENTION** (3):
1. Workflow state tracking - how to enforce step order automatically?
2. Error recovery strategy - what state to revert to on failure?
3. State revert mechanism - git operations vs in-memory undo?

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-agent-system/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
│   ├── cli-commands.yaml        # Command interface contracts
│   ├── file-formats.yaml        # Document format contracts
│   └── validation-rules.yaml    # Quality gate contracts
├── checklists/
│   └── requirements.md  # Specification quality checklist (completed)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── agent/
│   ├── __init__.py
│   ├── cli.py           # Command-line interface entry point
│   ├── commands/        # Command handlers
│   │   ├── __init__.py
│   │   ├── specify.py   # /sp.specify implementation
│   │   ├── plan.py      # /sp.plan implementation
│   │   ├── tasks.py     # /sp.tasks implementation
│   │   ├── constitution.py  # /sp.constitution implementation
│   │   └── adr.py       # /sp.adr implementation
│   ├── core/
│   │   ├── __init__.py
│   │   ├── constitution_guard.py  # Compliance checker
│   │   ├── workflow_orchestrator.py  # Step enforcement
│   │   ├── clarification.py  # One-question-at-a-time handler
│   │   └── phr_manager.py  # PHR creation
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── specification.py  # Spec generation logic
│   │   ├── planning.py       # Plan generation logic
│   │   ├── task_gen.py       # Task generation logic
│   │   └── validation.py     # Quality checklist validation
│   ├── templates/
│   │   ├── __init__.py
│   │   └── renderer.py  # Jinja2 template engine wrapper
│   └── utils/
│       ├── __init__.py
│       ├── file_ops.py  # File I/O helpers (pathlib)
│       └── git_ops.py   # Git integration (GitPython)
│
tests/
├── __init__.py
├── conftest.py          # Pytest configuration and fixtures
├── contract/
│   ├── __init__.py
│   ├── test_cli_interface.py
│   └── test_file_formats.py
├── integration/
│   ├── __init__.py
│   ├── test_specify_workflow.py
│   ├── test_plan_workflow.py
│   └── test_constitution_enforcement.py
└── unit/
    ├── __init__.py
    ├── test_constitution_guard.py
    ├── test_clarification.py
    └── test_phr_manager.py

requirements.txt         # Python dependencies
pyproject.toml          # Project configuration (PEP 518)
setup.py                # Package installation script
README.md               # Project overview
```

**Structure Decision**: Python 3.11+ single CLI application with modular command handlers. Uses standard Python package structure with separate modules for commands, core infrastructure, engines (generation logic), template rendering, and utilities.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

### Risks Requiring Mitigation (Not Violations)

| Risk | Impact | Mitigation Strategy | Complexity Added |
|------|--------|---------------------|------------------|
| Workflow state tracking not enforced automatically | Manual step invocation allows skipping (violates Principle V) | Add workflow state file tracking last completed step; each command validates prerequisites before executing | Workflow state file + validation logic (~100 LOC) |
| Error recovery strategy undefined | Failed command leaves partial artifacts without clear recovery path (impacts Principle IX) | Atomic operation pattern: write to temp files, validate, then move to final location; on error, clean temp files | Transaction pattern for file writes (~50 LOC) |
| State revert mechanism unclear | Principle X requires revert on violations but method not specified | Use git stash/reset for document revert; maintain undo stack for non-git operations; document both approaches in quickstart | Git integration for revert (~80 LOC) |

**Total Complexity Added**: ~230 LOC for constitutional compliance infrastructure

**Justification**: Required to satisfy Principles V, IX, X. Alternative of manual recovery increases human burden and violates Principle I (AI always generates). Complexity is necessary and unavoidable.

## Phase 0: Research (OUTPUT: research.md)

### Research Tasks

1. **Language/Platform Selection**
   - Research question: Which language/platform provides best integration with existing SpecKit Plus bash scripts?
   - Options: Python (rich ecosystem, Claude SDK), TypeScript (Node.js, cross-platform), Bash (native integration)
   - Decision criteria: Ease of template rendering, file I/O performance, testing infrastructure, maintainability

2. **Template Engine Selection** (blocked by task 1)
   - Research question: Which template engine for markdown + YAML front-matter rendering?
   - Options vary by language choice
   - Decision criteria: YAML front-matter support, markdown preservation, variable interpolation

3. **Workflow State Tracking Pattern**
   - Research question: How to persist workflow state (last completed step) for prerequisite validation?
   - Options: File-based (.specify/state.yaml), Git branches (encode state in branch name), In-memory (session-based)
   - Decision criteria: Persistence across sessions, simplicity, git-friendliness

4. **Atomic File Operation Pattern**
   - Research question: How to implement atomic writes (temp → validate → move) for error recovery?
   - Options: OS-level atomic rename, transactional file API, custom rollback logic
   - Decision criteria: Cross-platform compatibility, error safety, performance

5. **Quality Validation Integration**
   - Research question: How to automate checklist validation (currently manual markdown file)?
   - Options: Rule engine, AST parsing of generated markdown, LLM-based validation
   - Decision criteria: Accuracy, speed (<1 second per SC-009), maintainability

### Research Output Format

For each task above, document in `research.md`:
- **Decision**: [what was chosen]
- **Rationale**: [why chosen over alternatives]
- **Alternatives Considered**: [what else evaluated, why rejected]
- **Implementation Notes**: [specific libraries/patterns/gotchas]

## Phase 1: Design & Contracts (OUTPUT: data-model.md, contracts/, quickstart.md)

### Prerequisites

- ✅ `research.md` complete (all NEEDS CLARIFICATION resolved)
- ✅ Language/platform selected
- ✅ Template engine selected
- ✅ Workflow state tracking pattern chosen
- ✅ Atomic file operation pattern chosen

### Data Model (data-model.md)

Extract entities from spec.md Key Entities section and formalize:

1. **Feature Specification**
   - Fields: feature_name, branch, created_date, status, input_description, user_stories[], functional_requirements[], success_criteria[], assumptions[], dependencies[]
   - File format: Markdown with YAML front-matter
   - Validation: All mandatory sections present, no [NEEDS CLARIFICATION] markers remain, success criteria measurable
   - State transitions: Draft → In Review → Approved → Implemented

2. **Implementation Plan**
   - Fields: feature_name, branch, spec_link, summary, technical_context{}, constitution_check{}, project_structure, complexity_tracking[], phases[]
   - File format: Markdown with YAML front-matter
   - Validation: All NEEDS CLARIFICATION resolved, constitution check passed, structure decision documented
   - State transitions: Draft → Research Complete → Design Complete → Ready for Tasks

3. **Task List**
   - Fields: feature_name, tasks_by_story[], dependency_graph{}, parallel_markers[], estimated_complexity
   - File format: Markdown with YAML front-matter
   - Validation: All tasks have file paths, dependencies acyclic, at least 30% parallelizable
   - State transitions: Draft → In Progress → Completed

4. **Constitution**
   - Fields: version, ratified_date, last_amended_date, status, principles[], governance_rules, sync_impact_report
   - File format: Markdown with YAML front-matter (or inline metadata)
   - Validation: No unresolved placeholders, version follows semver, amendments documented
   - State transitions: Draft → Active → Superseded

5. **Architecture Decision Record (ADR)**
   - Fields: id, title, date, status, context, decision, alternatives[], consequences, significance_test{}
   - File format: Markdown with YAML front-matter
   - Validation: Meets 3-part significance test (impact + alternatives + scope)
   - State transitions: Proposed → Accepted → Superseded → Deprecated

6. **Prompt History Record (PHR)**
   - Fields: id, title, stage, date, surface, model, feature, branch, user, command, labels[], links{}, files[], tests[], prompt_text (verbatim), response_text, outcome{}, evaluation{}
   - File format: Markdown with YAML front-matter
   - Validation: All placeholders filled, prompt_text not truncated, routed correctly by stage
   - State transitions: None (immutable log entry)

7. **Communication Draft**
   - Fields: draft_id, type (email|whatsapp), purpose, recipient, subject, body, approval_status, approval_timestamp, sent_timestamp
   - File format: Markdown or JSON (TBD in research)
   - Validation: Clearly marked as DRAFT, approval_status must be 'pending' initially, sent_timestamp null until approved
   - State transitions: Draft → Pending Approval → Approved → Sent (external system) OR Rejected

8. **Quality Checklist**
   - Fields: feature_name, checklist_type, created_date, items[], validation_results[], notes
   - File format: Markdown with checkboxes
   - Validation: All items have pass/fail status, failing items documented with rationale
   - State transitions: Created → In Progress → Complete

### API Contracts (contracts/)

**File: cli-commands.yaml**
```yaml
commands:
  - name: /sp.specify
    description: Generate feature specification from natural language description
    inputs:
      - feature_description: string (natural language)
    outputs:
      - spec_file: path (specs/{number}-{slug}/spec.md)
      - checklist_file: path (specs/{number}-{slug}/checklists/requirements.md)
      - phr_file: path (history/prompts/{feature-name}/{id}-{slug}.spec.prompt.md)
    preconditions:
      - constitution_active: boolean
      - valid_git_repo: boolean
    postconditions:
      - spec_exists: boolean
      - quality_validation_passed: boolean
      - phr_created: boolean
    errors:
      - missing_constitution: "Constitution file not found at .specify/memory/constitution.md"
      - invalid_feature_description: "Feature description is empty or invalid"
      - quality_validation_failed: "Specification failed quality checklist"

  - name: /sp.plan
    description: Generate implementation plan from feature specification
    inputs:
      - none (reads from current feature branch spec.md)
    outputs:
      - plan_file: path (specs/{feature}/plan.md)
      - research_file: path (specs/{feature}/research.md)
      - data_model_file: path (specs/{feature}/data-model.md)
      - contracts_dir: path (specs/{feature}/contracts/)
      - quickstart_file: path (specs/{feature}/quickstart.md)
      - phr_file: path (history/prompts/{feature}/{id}-{slug}.plan.prompt.md)
    preconditions:
      - spec_exists: boolean
      - spec_quality_passed: boolean
      - constitution_check_passed: boolean
    postconditions:
      - plan_complete: boolean
      - no_needs_clarification: boolean
      - constitution_recheck_passed: boolean
      - phr_created: boolean
    errors:
      - spec_not_found: "Feature specification not found"
      - constitution_violation: "Plan violates constitution principle {principle_id}"
      - unresolved_clarifications: "Technical context has unresolved NEEDS CLARIFICATION markers"

  - name: /sp.tasks
    description: Generate task list from implementation plan
    inputs:
      - none (reads from current feature branch spec.md + plan.md)
    outputs:
      - tasks_file: path (specs/{feature}/tasks.md)
      - phr_file: path (history/prompts/{feature}/{id}-{slug}.tasks.prompt.md)
    preconditions:
      - spec_exists: boolean
      - plan_exists: boolean
      - plan_research_complete: boolean
      - plan_design_complete: boolean
    postconditions:
      - tasks_grouped_by_story: boolean
      - dependencies_acyclic: boolean
      - parallel_markers_added: boolean
      - phr_created: boolean
    errors:
      - plan_not_complete: "Plan has incomplete phases"
      - circular_dependency: "Task dependency cycle detected: {cycle}"

  - name: /sp.constitution
    description: Create or update project constitution
    inputs:
      - constitution_content: string (principles and governance rules) or file_path
    outputs:
      - constitution_file: path (.specify/memory/constitution.md)
      - sync_impact_report: embedded in constitution file
      - phr_file: path (history/prompts/constitution/{id}-{slug}.constitution.prompt.md)
    preconditions:
      - none (can create from scratch)
    postconditions:
      - constitution_active: boolean
      - version_incremented: boolean
      - no_unresolved_placeholders: boolean
      - phr_created: boolean
    errors:
      - invalid_version: "Version does not follow semver"
      - unresolved_placeholders: "Constitution contains unresolved {placeholder}"

  - name: /sp.adr
    description: Document architectural decision record
    inputs:
      - decision_title: string
      - decision_context: string (optional, inferred from recent work)
    outputs:
      - adr_file: path (history/adr/{number}-{slug}.md)
      - phr_file: path (history/prompts/{feature}/{id}-{slug}.misc.prompt.md)
    preconditions:
      - significance_test_passed: boolean (impact + alternatives + scope)
    postconditions:
      - adr_created: boolean
      - alternatives_documented: boolean
      - phr_created: boolean
    errors:
      - significance_test_failed: "Decision does not meet significance criteria"
      - missing_context: "Cannot infer decision context from workspace"
```

**File: file-formats.yaml**
```yaml
formats:
  markdown_with_frontmatter:
    description: Standard format for all generated documents
    structure:
      - front_matter: YAML delimited by --- markers
      - body: Markdown with headings, lists, code blocks
    validation:
      - yaml_parseable: true
      - no_unresolved_placeholders: true
      - headings_hierarchical: true
    examples:
      - spec.md
      - plan.md
      - tasks.md
      - constitution.md
      - adr/{number}-{slug}.md
      - phr/{id}-{slug}.{stage}.prompt.md

  checklist_markdown:
    description: Quality validation checklists
    structure:
      - front_matter: YAML with metadata
      - body: Markdown headings + checkbox lists
    validation:
      - all_items_have_status: true (checked or unchecked)
      - notes_section_present: true
    examples:
      - checklists/requirements.md

  contracts_yaml:
    description: API and validation contracts
    structure:
      - pure YAML (no markdown)
    validation:
      - yaml_valid: true
      - all_fields_documented: true
    examples:
      - contracts/cli-commands.yaml
      - contracts/file-formats.yaml
      - contracts/validation-rules.yaml
```

**File: validation-rules.yaml**
```yaml
quality_gates:
  specification:
    - rule: no_implementation_details
      check: Content does not mention languages, frameworks, databases, APIs
      error: "Specification contains implementation detail: {detail}"

    - rule: testable_requirements
      check: Each functional requirement can be objectively tested
      error: "Requirement {id} is not testable: {requirement}"

    - rule: measurable_success_criteria
      check: Success criteria have numeric metrics or objective measures
      error: "Success criterion {id} lacks measurement: {criterion}"

    - rule: technology_agnostic
      check: Success criteria describe outcomes, not implementation
      error: "Success criterion {id} is technology-specific: {criterion}"

    - rule: no_clarification_markers
      check: No [NEEDS CLARIFICATION] markers remain
      error: "Unresolved clarification at {location}: {marker}"

  plan:
    - rule: technical_context_complete
      check: No NEEDS CLARIFICATION in Technical Context section
      error: "Technical context incomplete: {field}"

    - rule: constitution_check_passed
      check: All constitution principles verified, violations justified
      error: "Constitution violation in {principle}: {violation}"

    - rule: structure_decision_documented
      check: Project Structure has concrete paths, no Option labels
      error: "Project structure contains undecided options"

    - rule: research_complete
      check: research.md exists and all questions answered
      error: "Research incomplete for: {research_task}"

  tasks:
    - rule: grouped_by_user_story
      check: Tasks organized under user story headings
      error: "Task {id} not grouped under user story"

    - rule: dependencies_acyclic
      check: Task dependency graph has no cycles
      error: "Circular dependency detected: {cycle}"

    - rule: parallel_markers
      check: At least 30% of tasks marked [P] for parallel execution
      error: "Insufficient parallelization: {percentage}% marked parallel"

    - rule: file_paths_explicit
      check: Tasks reference exact file paths, not placeholders
      error: "Task {id} has vague file reference: {reference}"

  constitution:
    - rule: no_placeholders
      check: No {{PLACEHOLDER}} or [PLACEHOLDER] tokens remain
      error: "Unresolved placeholder: {placeholder}"

    - rule: version_valid
      check: Version follows semver (MAJOR.MINOR.PATCH)
      error: "Invalid version format: {version}"

    - rule: dates_iso_format
      check: Dates in YYYY-MM-DD format
      error: "Invalid date format: {date}"

    - rule: sync_impact_report
      check: Sync impact report present for all amendments
      error: "Missing sync impact report for version {version}"

  phr:
    - rule: prompt_text_complete
      check: PROMPT_TEXT not truncated, captures full user input
      error: "PHR {id} has truncated prompt text"

    - rule: all_placeholders_filled
      check: No {{PLACEHOLDER}} tokens remain in YAML or body
      error: "PHR {id} has unfilled placeholder: {placeholder}"

    - rule: routing_correct
      check: File path matches stage routing rules
      error: "PHR {id} routed incorrectly: {actual_path} should be {expected_path}"
```

### Quickstart (quickstart.md)

Generate quickstart guide for developers implementing the agent system:

**Content Requirements**:
1. Prerequisites (language/platform setup, dependencies)
2. Installation (clone, install deps, configure)
3. Running commands (examples of /sp.specify, /sp.plan, etc.)
4. Directory structure walkthrough
5. Testing strategy (how to run contract/integration/unit tests)
6. Troubleshooting common issues
7. Contributing guidelines (how to add new commands)

### Agent Context Update

Run `.specify/scripts/bash/update-agent-context.sh claude` to add new technology decisions from `research.md` to `CLAUDE.md` (between preservation markers).

## Phase 2: Task Generation (OUTPUT: NONE - handled by /sp.tasks command)

This phase is NOT executed by `/sp.plan`. After Phase 1 completes, human operator runs `/sp.tasks` to generate task list.

## Post-Design Constitution Recheck

After Phase 1 design complete, re-evaluate Constitution Check:

**Gates to Re-Validate**:
1. Principle V (Mandatory Development Flow) - verify workflow state tracking design satisfies step enforcement
2. Principle IX (Error & Failure Handling) - verify atomic file operation pattern provides error recovery
3. Principle X (Termination & Reset Rule) - verify state revert mechanism (git-based or undo stack) is specified

**Expected Outcome**: All 3 risks from initial check resolved by research + design decisions.

## Post-Design Constitution Recheck

**Gate**: Re-validate constitution compliance after Phase 1 design complete.

### Risk 1: Workflow State Tracking

**Initial Status**: ⚠️ RISK - Manual step invocation allows skipping (violates Principle V)

**Resolution**: ✅ RESOLVED in research.md Research Task 3
- **Decision**: File-based state tracking (`.specify/state.yaml`)
- **Implementation**: Each command validates prerequisites before executing by checking `last_step` field in state file
- **Enforcement**: `/sp.plan` requires `last_step == "specify"`, `/sp.tasks` requires `last_step == "plan"`
- **State Schema**: Documented in research.md with feature-level granularity
- **Compliance**: Satisfies Principle V (Mandatory Development Flow) - step order enforced programmatically

**Post-Design Status**: ✅ PASS

### Risk 2: Error Recovery Strategy

**Initial Status**: ⚠️ RISK - Failed command leaves partial artifacts without clear recovery path (impacts Principle IX)

**Resolution**: ✅ RESOLVED in research.md Research Task 4
- **Decision**: Atomic file operation pattern (temp file + validate + atomic rename)
- **Implementation**: All file writes use temp file → validation → `os.replace()` pattern
- **Error Handling**: On failure, temp file deleted automatically, original preserved
- **Validation**: Quality gates run before atomic rename (YAML parsing, placeholder detection, structure checks)
- **Compliance**: Satisfies Principle IX (Error & Failure Handling) - comprehensive error documentation, no partial writes

**Post-Design Status**: ✅ PASS

### Risk 3: State Revert Mechanism

**Initial Status**: ⚠️ RISK - Principle X requires revert on violations but method not specified (git reset? undo stack?)

**Resolution**: ✅ RESOLVED in research.md Research Task 4 + data-model.md Entity 8 (Quality Checklist)
- **Decision**: Atomic file operations eliminate need for explicit revert (failed writes leave original intact)
- **Git Integration**: GitPython available for manual revert operations if needed (e.g., `git stash`, `git reset`)
- **State File**: `.specify/state.yaml` tracks last successful step, enables rollback to known good state
- **Validation Gates**: Constitution compliance check runs BEFORE file writes, prevents violations from being persisted
- **Compliance**: Satisfies Principle X (Termination & Reset Rule) - halt on violations, state preserved, clear recovery path

**Post-Design Status**: ✅ PASS

### Constitution Check Summary

**All 3 Risks Resolved**: ✅ PASS

- **Principle V (Mandatory Development Flow)**: State tracking enforces step order
- **Principle IX (Error & Failure Handling)**: Atomic file operations provide error recovery
- **Principle X (Termination & Reset Rule)**: Pre-write validation + atomic operations prevent bad state

**Design Complete**: Ready for Phase 2 (Task Generation via `/sp.tasks` command)

## Next Steps

1. Human operator reviews this plan for approval
2. If approved, `/sp.tasks` command generates task list organized by user story
3. Implementation begins following task dependency order
4. PHR created automatically upon plan completion

## Open Questions for Human Operator

**NONE** - all technical context will be resolved in Phase 0 research before proceeding to design.

If research phase identifies additional clarifications needed, those will be surfaced one at a time following Constitution Principle IV.
