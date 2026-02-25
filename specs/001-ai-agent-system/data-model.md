# Data Model: AI Agent System

**Feature**: 001-ai-agent-system
**Date**: 2026-01-13
**Purpose**: Formalize entity structures from specification

## Entity 1: Feature Specification

**Purpose**: Captures user requirements, scenarios, functional requirements, and success criteria in business terms

**Fields**:
- `feature_name`: string - Short descriptive name (e.g., "AI Agent System")
- `branch`: string - Git branch name (format: `###-slug`)
- `created_date`: date (ISO 8601: YYYY-MM-DD)
- `status`: enum ["Draft", "In Review", "Approved", "Implemented"]
- `input_description`: string - Original user feature description (natural language)
- `user_stories`: array of UserStory objects
  - `title`: string
  - `priority`: enum ["P1", "P2", "P3", "P4", "P5"]
  - `description`: string
  - `why_this_priority`: string
  - `independent_test`: string
  - `acceptance_scenarios`: array of Scenario objects
    - `given`: string (initial state)
    - `when`: string (action)
    - `then`: string (expected outcome)
- `functional_requirements`: array of FunctionalRequirement objects
  - `id`: string (format: "FR-###")
  - `description`: string (MUST/SHOULD/MAY statement)
- `success_criteria`: array of SuccessCriterion objects
  - `id`: string (format: "SC-###")
  - `description`: string (measurable outcome)
- `assumptions`: array of strings
- `dependencies`: object with `internal` and `external` arrays

**File Format**: Markdown with YAML front-matter

**Validation Rules**:
- All mandatory sections present (User Scenarios, Requirements, Success Criteria)
- No [NEEDS CLARIFICATION] markers remain
- Success criteria are measurable (contain metrics)
- No implementation details (languages, frameworks, APIs)

**State Transitions**:
1. **Draft** → **In Review**: Quality validation passed (checklist complete)
2. **In Review** → **Approved**: Human operator approval
3. **Approved** → **Implemented**: All tasks from task list completed
4. **Implemented** → **Draft**: Specification amended (reopens for review)

**Relationships**:
- Has one Implementation Plan (1:1)
- Has one or more Quality Checklists (1:N)
- Generates one Task List via plan (1:1)

---

## Entity 2: Implementation Plan

**Purpose**: Details technical architecture, project structure, technology choices, and complexity justifications

**Fields**:
- `feature_name`: string
- `branch`: string
- `date`: date (ISO 8601)
- `spec_link`: path (relative link to spec.md)
- `summary`: string (extracted from spec)
- `technical_context`: object
  - `language_version`: string
  - `primary_dependencies`: array of strings
  - `storage`: string
  - `testing`: string
  - `target_platform`: string
  - `project_type`: string
  - `performance_goals`: string
  - `constraints`: string
  - `scale_scope`: string
- `constitution_check`: object
  - `pre_research_validation`: array of PrincipleCheck objects
    - `principle`: string (e.g., "Principle I")
    - `status`: enum ["PASS", "FAIL", "RISK"]
    - `notes`: string
  - `gates_summary`: object
    - `blocking_violations`: array of strings
    - `risks_requiring_attention`: array of strings
- `project_structure`: object
  - `documentation`: string (directory tree)
  - `source_code`: string (directory tree)
  - `structure_decision`: string (rationale)
- `complexity_tracking`: array of ComplexityEntry objects
  - `risk`: string
  - `impact`: string
  - `mitigation_strategy`: string
  - `complexity_added`: string
- `phases`: array of Phase objects
  - `phase_number`: integer
  - `name`: string
  - `output`: string
  - `prerequisites`: array of strings
  - `tasks`: array of strings

**File Format**: Markdown with YAML front-matter

**Validation Rules**:
- No NEEDS CLARIFICATION in Technical Context
- Constitution check passed or violations justified
- Project structure has concrete paths (no "Option A/B/C" labels)
- research.md exists and complete

**State Transitions**:
1. **Draft** → **Research Complete**: Phase 0 complete (research.md generated)
2. **Research Complete** → **Design Complete**: Phase 1 complete (data-model.md, contracts/, quickstart.md generated)
3. **Design Complete** → **Ready for Tasks**: Constitution recheck passed
4. **Ready for Tasks** → **Draft**: Plan amended (reopens for research)

**Relationships**:
- Belongs to one Feature Specification (N:1)
- Has one Research document (1:1)
- Has one Data Model document (1:1)
- Has one Contracts directory (1:1)
- Has one Quickstart guide (1:1)
- Generates one Task List (1:1)

---

## Entity 3: Task List

**Purpose**: Dependency-ordered, parallelizable breakdown of implementation work organized by user story

**Fields**:
- `feature_name`: string
- `branch`: string
- `date`: date (ISO 8601)
- `spec_link`: path
- `plan_link`: path
- `tasks_by_story`: array of TaskGroup objects
  - `user_story`: string (reference to spec.md user story title)
  - `priority`: enum ["P1", "P2", "P3", "P4", "P5"]
  - `tasks`: array of Task objects
    - `id`: string (format: "T###")
    - `description`: string
    - `file_paths`: array of strings (exact paths, not placeholders)
    - `dependencies`: array of task IDs
    - `parallel`: boolean (marked [P] if true)
    - `estimated_complexity`: enum ["XS", "S", "M", "L", "XL"]
- `dependency_graph`: object (adjacency list representation)
- `parallel_markers`: array of task IDs that can execute in parallel
- `estimated_total_complexity`: string

**File Format**: Markdown with YAML front-matter

**Validation Rules**:
- Tasks grouped by user story (each story has task section)
- Dependencies acyclic (no circular references)
- At least 30% of tasks marked [P] for parallel execution
- Tasks reference exact file paths (not "TBD" or placeholders)

**State Transitions**:
1. **Draft** → **In Progress**: First task started
2. **In Progress** → **Completed**: All tasks completed
3. **Completed** → **Draft**: Task list amended (reopens)

**Relationships**:
- Belongs to one Feature Specification (N:1)
- Belongs to one Implementation Plan (N:1)
- Has many Tasks (1:N)

---

## Entity 4: Constitution

**Purpose**: Governance document defining development principles, role boundaries, tool authority, workflow rules

**Fields**:
- `version`: string (semver: MAJOR.MINOR.PATCH)
- `ratified_date`: date (ISO 8601)
- `last_amended_date`: date (ISO 8601)
- `status`: enum ["Draft", "Active", "Superseded"]
- `principles`: array of Principle objects
  - `number`: integer (Roman numeral in display)
  - `name`: string
  - `description`: string
  - `rules`: array of strings
  - `rationale`: string
  - `non_negotiable`: boolean
- `governance_rules`: object
  - `amendment_process`: string
  - `complexity_justification`: string
  - `compliance_review`: string
- `sync_impact_report`: object (embedded as HTML comment)
  - `version_change`: string (old → new)
  - `change_type`: string
  - `modified_principles`: array of strings
  - `added_sections`: array of strings
  - `removed_sections`: array of strings
  - `templates_requiring_updates`: array of TemplateStatus objects
    - `path`: string
    - `status`: enum ["✅ updated", "⚠ pending"]
  - `follow_up_todos`: array of strings
  - `amendments`: array of Amendment objects
    - `date`: date (ISO 8601)
    - `description`: string
  - `deferred_items`: array of strings

**File Format**: Markdown with inline metadata (footer line)

**Validation Rules**:
- No {{PLACEHOLDER}} or [PLACEHOLDER] tokens remain
- Version follows semver format
- Dates in ISO 8601 format (YYYY-MM-DD)
- Sync impact report present for all amendments (except initial v1.0.0)

**State Transitions**:
1. **Draft** → **Active**: Ratified (ratification date set)
2. **Active** → **Superseded**: New constitution version activated
3. **Superseded** → N/A (terminal state)

**Relationships**:
- Validates all Feature Specifications (1:N)
- Validates all Implementation Plans (1:N)
- Validates all Task Lists (1:N)
- Referenced by all PHRs (1:N)

---

## Entity 5: Architecture Decision Record (ADR)

**Purpose**: Captures significant architectural decision, alternatives considered, consequences, and rationale

**Fields**:
- `id`: integer (incrementing: 0001, 0002, ...)
- `title`: string (descriptive, slug for filename)
- `date`: date (ISO 8601)
- `status`: enum ["Proposed", "Accepted", "Superseded", "Deprecated"]
- `context`: string (background, problem statement)
- `decision`: string (what was decided)
- `alternatives`: array of Alternative objects
  - `name`: string
  - `description`: string
  - `rejected_reason`: string
- `consequences`: object
  - `positive`: array of strings
  - `negative`: array of strings
  - `risks`: array of strings
- `significance_test`: object
  - `impact`: boolean (long-term consequences?)
  - `alternatives`: boolean (multiple viable options?)
  - `scope`: boolean (cross-cutting influence?)

**File Format**: Markdown with YAML front-matter

**Validation Rules**:
- Meets 3-part significance test (all three must be true: impact, alternatives, scope)
- At least 2 alternatives documented
- Consequences (positive and negative) documented

**State Transitions**:
1. **Proposed** → **Accepted**: Decision approved and implemented
2. **Accepted** → **Superseded**: New ADR replaces this one
3. **Accepted** → **Deprecated**: Decision no longer relevant
4. **Proposed** → **Deprecated**: Decision rejected

**Relationships**:
- May relate to one Feature (N:1, optional)
- May supersede previous ADR (N:1, optional)
- Creates one PHR when generated (1:1)

---

## Entity 6: Prompt History Record (PHR)

**Purpose**: Immutable log entry capturing user prompt, AI response, stage, feature context, files modified, evaluation metadata

**Fields**:
- `id`: integer (incrementing per feature/stage: 0001, 0002, ...)
- `title`: string (3-7 words, slug for filename)
- `stage`: enum ["constitution", "spec", "plan", "tasks", "red", "green", "refactor", "explainer", "misc", "general"]
- `date`: date (ISO 8601)
- `surface`: enum ["agent", "human", "system"]
- `model`: string (e.g., "claude-sonnet-4-5-20250929")
- `feature`: string (feature name or "none" for constitution/general)
- `branch`: string (git branch)
- `user`: string (username or "system")
- `command`: string (e.g., "/sp.specify")
- `labels`: array of strings (topics, keywords)
- `links`: object
  - `spec`: path or null
  - `ticket`: URL or null
  - `adr`: path or null
  - `pr`: URL or null
- `files`: array of paths (created/modified files)
- `tests`: array of strings (tests run/added)
- `prompt_text`: string (full user input, verbatim, not truncated)
- `response_text`: string (concise summary of AI response)
- `outcome`: object
  - `impact`: string
  - `tests_summary`: string
  - `files_summary`: string
  - `next_prompts`: string
  - `reflection_note`: string
- `evaluation`: object
  - `failure_modes`: string
  - `grader_results`: string
  - `prompt_variant_id`: string or null
  - `next_experiment`: string

**File Format**: Markdown with YAML front-matter

**Validation Rules**:
- No {{PLACEHOLDER}} tokens remain in YAML or body
- prompt_text not truncated (full user input)
- Routed correctly by stage:
  - constitution → `history/prompts/constitution/`
  - spec/plan/tasks/red/green/refactor/explainer/misc → `history/prompts/{feature-name}/`
  - general → `history/prompts/general/`
- Filename matches pattern: `{id}-{slug}.{stage}.prompt.md`

**State Transitions**:
- None (immutable after creation)

**Relationships**:
- Belongs to one Feature (N:1, except constitution/general stages)
- Created by one Workflow Command (1:1)
- References Constitution version (N:1)

---

## Entity 7: Communication Draft

**Purpose**: Email or WhatsApp message generated by AI for human review, requiring explicit approval before sending

**Fields**:
- `draft_id`: string (UUID or timestamp-based)
- `type`: enum ["email", "whatsapp"]
- `purpose`: string (reason for message)
- `recipient`: string (email address or phone number)
- `subject`: string (for email only)
- `body`: string (message content)
- `approval_status`: enum ["pending", "approved", "rejected"]
- `approval_timestamp`: datetime (ISO 8601) or null
- `sent_timestamp`: datetime (ISO 8601) or null
- `created_by`: string (username or "agent")
- `approved_by`: string (username) or null

**File Format**: Markdown or JSON (TBD - pending research)

**Validation Rules**:
- Clearly marked as DRAFT in output
- approval_status must be 'pending' initially
- sent_timestamp must be null until approved
- Cannot transition to 'approved' without explicit human action

**State Transitions**:
1. **Draft** → **Pending Approval**: Generated and awaiting review
2. **Pending Approval** → **Approved**: Human approves (logs approval)
3. **Pending Approval** → **Rejected**: Human rejects (logs rejection reason)
4. **Approved** → **Sent**: External system sends message (out of agent scope)

**Relationships**:
- May belong to one Feature (N:1, optional)
- Creates one PHR when generated (1:1)
- Logged in system records (1:1 with approval log entry)

---

## Entity 8: Quality Checklist

**Purpose**: Validation criteria for specifications ensuring completeness, testability, measurability, absence of implementation details

**Fields**:
- `feature_name`: string
- `checklist_type`: enum ["requirements", "design", "implementation", "testing"]
- `created_date`: date (ISO 8601)
- `feature_link`: path (link to spec.md or plan.md)
- `items`: array of ChecklistItem objects
  - `section`: string (e.g., "Content Quality", "Requirement Completeness")
  - `description`: string
  - `status`: enum ["pass", "fail", "pending"]
  - `notes`: string (optional, for fail cases)
- `validation_results`: object
  - `status`: enum ["PASSED", "FAILED", "IN PROGRESS"]
  - `passed_count`: integer
  - `failed_count`: integer
  - `total_count`: integer
- `notes`: string (overall notes, failing items documentation)

**File Format**: Markdown with checkboxes, YAML front-matter

**Validation Rules**:
- All items have status (checked = pass, unchecked = fail)
- Failing items must have notes explaining reason
- notes section present

**State Transitions**:
1. **Created** → **In Progress**: Validation started
2. **In Progress** → **Complete**: All items checked (pass or fail with notes)
3. **Complete** → **In Progress**: Checklist amended (revalidation)

**Relationships**:
- Belongs to one Feature Specification (N:1)
- Validates one artifact (spec.md, plan.md, etc.) (1:1)

---

## Cross-Entity Relationships Summary

```text
Constitution (1) ──validates──> (N) Feature Specifications
Feature Specification (1) ──has──> (1) Implementation Plan
Feature Specification (1) ──has──> (1) Task List
Feature Specification (1) ──has──> (N) Quality Checklists
Implementation Plan (1) ──has──> (1) Research Document
Implementation Plan (1) ──has──> (1) Data Model Document
Implementation Plan (1) ──has──> (1) Contracts Directory
Implementation Plan (1) ──has──> (1) Quickstart Guide
Feature (1) ──generates──> (N) PHRs
Feature (N) ──may reference──> (1) ADR
Workflow Command (1) ──creates──> (1) PHR
Communication Draft (1) ──creates──> (1) PHR
```

---

## Data Storage

All entities stored as markdown files with YAML front-matter on file system. No database required.

**Directory Structure**:
```text
.specify/
├── memory/
│   └── constitution.md              # Entity 4: Constitution
├── state.yaml                        # Workflow state tracking
└── templates/                        # Jinja2 templates (read-only)

specs/
└── {###-feature-name}/
    ├── spec.md                       # Entity 1: Feature Specification
    ├── plan.md                       # Entity 2: Implementation Plan
    ├── tasks.md                      # Entity 3: Task List
    ├── research.md                   # Research document (plan phase 0)
    ├── data-model.md                 # This file (plan phase 1)
    ├── quickstart.md                 # Quickstart guide (plan phase 1)
    ├── contracts/                    # API contracts (plan phase 1)
    │   ├── cli-commands.yaml
    │   ├── file-formats.yaml
    │   └── validation-rules.yaml
    └── checklists/
        └── requirements.md           # Entity 8: Quality Checklist

history/
├── adr/
│   └── {####-slug}.md                # Entity 5: ADR
└── prompts/
    ├── constitution/
    │   └── {####-slug}.constitution.prompt.md  # Entity 6: PHR
    ├── {feature-name}/
    │   └── {####-slug}.{stage}.prompt.md       # Entity 6: PHR
    └── general/
        └── {####-slug}.general.prompt.md       # Entity 6: PHR

drafts/                               # Entity 7: Communication Drafts
├── email/
│   └── {draft-id}.md
└── whatsapp/
    └── {draft-id}.md
```
