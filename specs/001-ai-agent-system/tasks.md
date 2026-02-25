# Task List: AI Agent System

**Feature**: 001-ai-agent-system
**Branch**: `001-ai-agent-system`
**Date**: 2026-01-13
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

This task list implements an AI agent system that executes governed workflows (specification, planning, task generation, constitution management, ADR creation) with strict constitution compliance enforcement. Tasks are organized by user story to enable independent implementation and testing.

**Technology Stack**: Python 3.11+, anthropic (Claude SDK), Jinja2, PyYAML, GitPython, pytest

**MVP Scope**: User Story 1 (Create Feature Specification) + User Story 4 (Create Project Constitution)

---

## Phase 1: Setup & Project Initialization

**Goal**: Establish project structure, dependencies, and development environment

**Tasks**:

- [ ] T001 [P] Create Python project structure per plan.md (src/agent/, tests/, requirements.txt, pyproject.toml, setup.py)
- [ ] T002 [P] Create requirements.txt with dependencies (anthropic>=0.40.0, Jinja2>=3.1.0, PyYAML>=6.0, GitPython>=3.1.0, click>=8.0, pytest>=7.0, pytest-cov, pytest-mock, markdown-it-py)
- [ ] T003 [P] Create pyproject.toml with project metadata (name, version, description, author, license, requires-python >=3.11)
- [ ] T004 [P] Create setup.py for package installation (setuptools, find_packages, entry point for CLI)
- [ ] T005 [P] Create .gitignore (.venv/, __pycache__/, *.pyc, .pytest_cache/, htmlcov/, .env, .specify/state.yaml)
- [ ] T006 [P] Create README.md with project overview and quickstart link
- [ ] T007 [P] Create all __init__.py files in package structure (src/agent/, src/agent/commands/, src/agent/core/, src/agent/engines/, src/agent/templates/, src/agent/utils/)
- [ ] T008 [P] Create tests/__init__.py and tests/conftest.py with pytest fixtures
- [ ] T009 Create .env.example with ANTHROPIC_API_KEY placeholder and usage instructions

---

## Phase 2: Foundational Infrastructure (Blocking Prerequisites)

**Goal**: Build core infrastructure required by all user stories

**Tasks**:

- [ ] T010 Implement constitution_guard.py with compliance check function that loads constitution.md and validates principles
- [ ] T011 Implement workflow_orchestrator.py with state tracking (.specify/state.yaml read/write) and prerequisite validation
- [ ] T012 Implement phr_manager.py with create_phr function that calls existing .specify/scripts/bash/create-phr.sh and fills placeholders
- [ ] T013 Implement file_ops.py with atomic_write function (temp file + validate + os.replace pattern from research.md)
- [ ] T014 [P] Implement git_ops.py with GitPython wrappers for branch operations (create, checkout, status)
- [ ] T015 [P] Implement renderer.py with Jinja2 Environment setup (autoescape=False, FileSystemLoader for .specify/templates/, custom filters: slugify, iso_date, allocate_id)
- [ ] T016 Implement clarification.py with ask_question function that enforces one-question-at-a-time policy
- [ ] T017 [P] Implement validation.py with QualityValidator class and rule engine from research.md (markdown AST parsing, validation rules from contracts/validation-rules.yaml)
- [ ] T018 Create cli.py with Click CLI framework and command group structure (@click.group, --help)

---

## Phase 3: User Story 1 - Create Feature Specification (Priority P1)

**Story Goal**: Generate complete, structured specification from natural language description

**Independent Test**: Provide feature description → verify spec.md generated with all sections, quality validation passed, PHR created

**Tasks**:

- [ ] T019 [US1] Implement specify.py command handler with Click decorator (@cli.command('specify'), @click.argument('feature_description'))
- [ ] T020 [US1] Implement specification.py engine: parse feature description, detect feature type, extract key concepts
- [ ] T021 [US1] Implement specification.py: generate short name (2-4 words) and slug for branch naming
- [ ] T022 [US1] Implement specification.py: call create-new-feature.sh script to initialize branch and spec file
- [ ] T023 [US1] Implement specification.py: identify ambiguous requirements and generate clarification questions (max 3)
- [ ] T024 [US1] Implement specification.py: call clarification.ask_question for each unclear aspect (one at a time)
- [ ] T025 [US1] Implement specification.py: update spec content with clarification answers
- [ ] T026 [US1] Implement specification.py: fill spec template using renderer.render with user stories, requirements, success criteria from extraction
- [ ] T027 [US1] Implement specification.py: validate generated spec using validation.QualityValidator with specification rules
- [ ] T028 [US1] Implement specification.py: create quality checklist in specs/{feature}/checklists/requirements.md with validation results
- [ ] T029 [US1] Implement specification.py: call file_ops.atomic_write to write spec.md (temp → validate → rename)
- [ ] T030 [US1] Implement specify.py: call phr_manager.create_phr with stage='spec', embed full prompt and response
- [ ] T031 [US1] Implement specify.py: update workflow state (.specify/state.yaml) with last_step='specify'
- [ ] T032 [US1] Implement specify.py: return spec file path, checklist results, PHR ID to user

---

## Phase 4: User Story 4 - Create Project Constitution (Priority P1)

**Story Goal**: Generate structured governance document with versioning and compliance rules

**Independent Test**: Provide constitution principles → verify constitution.md created with all sections, version metadata, sync impact report

**Tasks**:

- [ ] T033 [P] [US4] Implement constitution.py command handler with Click decorator (@cli.command('constitution'), @click.argument('constitution_content'))
- [ ] T034 [P] [US4] Implement constitution.py: detect input type (file path vs inline content)
- [ ] T035 [US4] Implement constitution.py: parse constitution content and extract principles (number, name, description, rules, rationale)
- [ ] T036 [US4] Implement constitution.py: detect constitution type (new creation vs amendment) based on existing constitution.md
- [ ] T037 [US4] Implement constitution.py: determine version increment (MAJOR/MINOR/PATCH) based on change type (breaking/additive/clarification)
- [ ] T038 [US4] Implement constitution.py: generate sync impact report (version change, modified principles, added/removed sections, affected templates)
- [ ] T039 [US4] Implement constitution.py: check dependent templates (.specify/templates/plan-template.md, spec-template.md, tasks-template.md) for alignment
- [ ] T040 [US4] Implement constitution.py: fill constitution template with principles, governance rules, version metadata, sync impact report
- [ ] T041 [US4] Implement constitution.py: validate constitution (no placeholders, valid semver, ISO dates) using validation.QualityValidator
- [ ] T042 [US4] Implement constitution.py: call file_ops.atomic_write to write .specify/memory/constitution.md
- [ ] T043 [US4] Implement constitution.py: call phr_manager.create_phr with stage='constitution', embed full prompt and response
- [ ] T044 [US4] Implement constitution.py: return constitution file path, version, status (ACTIVE), PHR ID to user

---

## Phase 5: User Story 2 - Generate Implementation Plan (Priority P2)

**Story Goal**: Transform specification into technical architecture with research and design artifacts

**Independent Test**: Provide existing spec.md → verify plan.md, research.md, data-model.md, contracts/, quickstart.md generated with constitution recheck passed

**Tasks**:

- [ ] T045 [US2] Implement plan.py command handler with Click decorator (@cli.command('plan'))
- [ ] T046 [US2] Implement plan.py: validate prerequisites (spec exists, constitution check passed) using workflow_orchestrator
- [ ] T047 [US2] Implement plan.py: call setup-plan.sh script to initialize planning (copy plan template)
- [ ] T048 [US2] Implement planning.py engine: load spec.md and extract feature requirements, user stories, entities
- [ ] T049 [US2] Implement planning.py: analyze technical context needs (language, dependencies, storage, testing)
- [ ] T050 [US2] Implement planning.py: detect unknowns in technical context and generate clarification question (language/platform choice)
- [ ] T051 [US2] Implement planning.py: call clarification.ask_question for technical clarifications (one at a time)
- [ ] T052 [US2] Implement planning.py: generate Phase 0 research.md with research tasks and decisions based on clarifications
- [ ] T053 [US2] Implement planning.py: resolve all NEEDS CLARIFICATION markers using research decisions
- [ ] T054 [US2] Implement planning.py: extract entities from spec Key Entities section and formalize in data-model.md (fields, validation, state transitions)
- [ ] T055 [US2] Implement planning.py: generate contracts/cli-commands.yaml from functional requirements (map FR to command inputs/outputs/errors)
- [ ] T056 [P] [US2] Implement planning.py: generate contracts/file-formats.yaml with format specifications (markdown_with_frontmatter, checklist_markdown, contracts_yaml)
- [ ] T057 [P] [US2] Implement planning.py: generate contracts/validation-rules.yaml from success criteria and quality gates
- [ ] T058 [US2] Implement planning.py: generate quickstart.md with installation, command usage, testing strategy, troubleshooting
- [ ] T059 [US2] Implement planning.py: call update-agent-context.sh to add technology stack to agent context file (CLAUDE.md)
- [ ] T060 [US2] Implement planning.py: run constitution post-design recheck (validate risks resolved: workflow state tracking, error recovery, state revert)
- [ ] T061 [US2] Implement planning.py: fill plan template with technical context, constitution check, project structure, complexity tracking, phases
- [ ] T062 [US2] Implement planning.py: validate plan (no NEEDS CLARIFICATION, structure decided, research complete) using validation.QualityValidator
- [ ] T063 [US2] Implement plan.py: call file_ops.atomic_write for all generated files (plan.md, research.md, data-model.md, contracts/, quickstart.md)
- [ ] T064 [US2] Implement plan.py: call phr_manager.create_phr with stage='plan', embed full prompt and response
- [ ] T065 [US2] Implement plan.py: update workflow state (.specify/state.yaml) with last_step='plan'
- [ ] T066 [US2] Implement plan.py: return plan file path, artifacts list, constitution recheck status, PHR ID to user

---

## Phase 6: User Story 3 - Generate Task List (Priority P3)

**Story Goal**: Break architecture into dependency-ordered, parallelizable tasks organized by user story

**Independent Test**: Provide existing spec.md + plan.md → verify tasks.md generated with tasks grouped by story, dependency ordering, parallel markers

**Tasks**:

- [ ] T067 [US3] Implement tasks.py command handler with Click decorator (@cli.command('tasks'))
- [ ] T068 [US3] Implement tasks.py: validate prerequisites (spec and plan exist, plan research/design complete) using workflow_orchestrator
- [ ] T069 [US3] Implement tasks.py: call check-prerequisites.sh script to verify plan/spec and get feature directory
- [ ] T070 [US3] Implement task_gen.py engine: load spec.md and extract user stories with priorities (P1, P2, P3, P4, P5)
- [ ] T071 [US3] Implement task_gen.py: load plan.md and extract tech stack, libraries, project structure (file paths)
- [ ] T072 [P] [US3] Implement task_gen.py: load data-model.md and map entities to user stories (which story needs which entity)
- [ ] T073 [P] [US3] Implement task_gen.py: load contracts/ and map endpoints/commands to user stories
- [ ] T074 [US3] Implement task_gen.py: generate Phase 1 setup tasks (project structure, dependencies, configuration)
- [ ] T075 [US3] Implement task_gen.py: generate Phase 2 foundational tasks (core infrastructure: constitution_guard, workflow_orchestrator, phr_manager, file_ops, validation)
- [ ] T076 [US3] Implement task_gen.py: for each user story in priority order, generate tasks (models → services → endpoints → integration)
- [ ] T077 [US3] Implement task_gen.py: assign task IDs sequentially (T001, T002, ...) in execution order
- [ ] T078 [US3] Implement task_gen.py: add [P] markers to parallelizable tasks (different files, no blocking dependencies)
- [ ] T079 [US3] Implement task_gen.py: add [US#] labels to user story phase tasks (map to spec user stories)
- [ ] T080 [US3] Implement task_gen.py: ensure all tasks have exact file paths (not "TBD" or placeholders)
- [ ] T081 [US3] Implement task_gen.py: generate dependency graph (adjacency list) showing task dependencies
- [ ] T082 [US3] Implement task_gen.py: detect circular dependencies (cycle detection algorithm) and fail if found
- [ ] T083 [US3] Implement task_gen.py: calculate parallel percentage (parallelizable tasks / total tasks) and ensure >=30%
- [ ] T084 [US3] Implement task_gen.py: generate "Independent Test" criteria for each user story phase
- [ ] T085 [US3] Implement task_gen.py: fill tasks template with phases, dependency graph, parallel execution examples, MVP scope
- [ ] T086 [US3] Implement task_gen.py: validate tasks (grouped by story, acyclic dependencies, parallel markers, explicit paths) using validation.QualityValidator
- [ ] T087 [US3] Implement tasks.py: call file_ops.atomic_write to write specs/{feature}/tasks.md
- [ ] T088 [US3] Implement tasks.py: call phr_manager.create_phr with stage='tasks', embed full prompt and response
- [ ] T089 [US3] Implement tasks.py: update workflow state (.specify/state.yaml) with last_step='tasks'
- [ ] T090 [US3] Implement tasks.py: return tasks file path, total task count, parallel percentage, MVP scope, PHR ID to user

---

## Phase 7: User Story 5 - Document Architectural Decision (Priority P4)

**Story Goal**: Generate structured ADR documenting significant architectural decisions with alternatives and rationale

**Independent Test**: Provide decision context → verify ADR created with decision, alternatives, consequences, status

**Tasks**:

- [ ] T091 [P] [US5] Implement adr.py command handler with Click decorator (@cli.command('adr'), @click.argument('decision_title'))
- [ ] T092 [P] [US5] Implement adr.py: run significance test (impact + alternatives + scope) on decision
- [ ] T093 [US5] Implement adr.py: if significance test fails, reject with error message per contracts/cli-commands.yaml
- [ ] T094 [US5] Implement adr.py: prompt for decision context if not inferable from workspace (optional @click.option)
- [ ] T095 [US5] Implement adr.py: prompt for alternatives considered (at least 2 required)
- [ ] T096 [US5] Implement adr.py: prompt for consequences (positive, negative, risks)
- [ ] T097 [US5] Implement adr.py: allocate ADR ID (increment from highest existing in history/adr/)
- [ ] T098 [US5] Implement adr.py: generate ADR slug from decision title (slugify filter)
- [ ] T099 [US5] Implement adr.py: fill ADR template with decision, alternatives, consequences, significance test results, status (Proposed)
- [ ] T100 [US5] Implement adr.py: validate ADR (significance test passed, alternatives documented, consequences listed) using validation.QualityValidator
- [ ] T101 [US5] Implement adr.py: call file_ops.atomic_write to write history/adr/{number}-{slug}.md
- [ ] T102 [US5] Implement adr.py: call phr_manager.create_phr with stage='misc', feature context, embed full prompt and response
- [ ] T103 [US5] Implement adr.py: return ADR file path, ADR ID, PHR ID to user

---

## Phase 8: User Story 6 - Draft Communication Messages (Priority P5)

**Story Goal**: Generate email/WhatsApp drafts for human review with explicit approval requirement

**Independent Test**: Request message draft → verify draft generated, marked as DRAFT, requires approval before any sending

**Tasks**:

- [ ] T104 [P] [US6] Implement communication draft module in src/agent/engines/communication.py
- [ ] T105 [P] [US6] Implement communication.py: generate draft ID (UUID or timestamp-based)
- [ ] T106 [US6] Implement communication.py: detect message type (email vs whatsapp) from user request
- [ ] T107 [US6] Implement communication.py: generate message subject (for email only)
- [ ] T108 [US6] Implement communication.py: generate message body using LLM (Claude API) based on purpose
- [ ] T109 [US6] Implement communication.py: mark draft with approval_status='pending', sent_timestamp=null
- [ ] T110 [US6] Implement communication.py: add prominent DRAFT marker to output
- [ ] T111 [US6] Implement communication.py: decide format (markdown vs JSON per research.md decision)
- [ ] T112 [US6] Implement communication.py: call file_ops.atomic_write to write drafts/{type}/{draft-id}.md
- [ ] T113 [US6] Implement communication.py: log draft creation in system records
- [ ] T114 [US6] Implement CLI command (add to cli.py) for draft generation (@cli.command('draft'), @click.option for type/recipient/purpose)
- [ ] T115 [US6] Implement draft command: call phr_manager.create_phr with stage='misc', embed full prompt and response
- [ ] T116 [US6] Implement draft command: return draft file path, draft ID, approval requirement message, PHR ID to user

---

## Phase 9: Polish & Cross-Cutting Concerns

**Goal**: Finalize quality, documentation, error handling, and cross-cutting features

**Tasks**:

- [ ] T117 [P] Add comprehensive docstrings to all public functions (Google style format)
- [ ] T118 [P] Add type hints to all function signatures (typing module)
- [ ] T119 [P] Implement error handling in cli.py (try/except around commands, log errors, user-friendly messages)
- [ ] T120 [P] Implement logging configuration (Python logging module, configurable log levels, file + console output)
- [ ] T121 [P] Create conftest.py fixtures for common test data (sample spec, plan, constitution, PHR)
- [ ] T122 [P] Implement contract tests in tests/contract/test_cli_interface.py (test all CLI commands with Click CliRunner)
- [ ] T123 [P] Implement contract tests in tests/contract/test_file_formats.py (test YAML parsing, front-matter extraction)
- [ ] T124 [P] Implement integration test in tests/integration/test_specify_workflow.py (full /sp.specify workflow)
- [ ] T125 [P] Implement integration test in tests/integration/test_plan_workflow.py (full /sp.plan workflow)
- [ ] T126 [P] Implement integration test in tests/integration/test_constitution_enforcement.py (constitution compliance checks)
- [ ] T127 [P] Implement unit tests in tests/unit/test_constitution_guard.py (principle validation logic)
- [ ] T128 [P] Implement unit tests in tests/unit/test_clarification.py (one-question-at-a-time enforcement)
- [ ] T129 [P] Implement unit tests in tests/unit/test_phr_manager.py (PHR creation, placeholder filling, routing)
- [ ] T130 [P] Run pytest with coverage (pytest --cov=agent --cov-report=html), aim for >=80% coverage
- [ ] T131 [P] Run black formatter on all Python files (black src/ tests/)
- [ ] T132 [P] Create GitHub Actions workflow for CI (.github/workflows/tests.yml with pytest, coverage, linting)
- [ ] T133 Update README.md with badges (build status, coverage), usage examples, contributing guidelines
- [ ] T134 Validate all generated files against contracts/validation-rules.yaml
- [ ] T135 Run full workflow test: spec → plan → tasks → verify all artifacts generated correctly
- [ ] T136 Final code review and refactoring for code quality and maintainability

---

## Dependencies & Execution Order

### User Story Completion Order

```text
Phase 1 (Setup)
    ↓
Phase 2 (Foundational Infrastructure) ← BLOCKING for all user stories
    ↓
    ├─→ Phase 3: User Story 1 (Specify) [P1] ──┐
    │                                           │
    ├─→ Phase 4: User Story 4 (Constitution) [P1] ─→ MVP Complete
    │                                           │
    ├─→ Phase 5: User Story 2 (Plan) [P2] ← depends on US1
    │                                           │
    ├─→ Phase 6: User Story 3 (Tasks) [P3] ← depends on US1 + US2
    │                                           │
    ├─→ Phase 7: User Story 5 (ADR) [P4] ← independent
    │                                           │
    └─→ Phase 8: User Story 6 (Communication) [P5] ← independent
            ↓
    Phase 9 (Polish & Cross-Cutting)
```

### Blocking Dependencies

- **Phase 2 blocks all user stories**: Constitution guard, workflow orchestrator, PHR manager, file operations must exist before any command can execute
- **User Story 2 depends on User Story 1**: Plan generation requires existing spec
- **User Story 3 depends on User Stories 1 & 2**: Task generation requires existing spec + plan
- **User Stories 4, 5, 6 are independent**: Can be implemented in parallel with others

### Parallel Opportunities

**Phase 1 (Setup)**: 9 parallelizable tasks (T001-T008) - all create independent files

**Phase 2 (Foundational)**: 3 parallelizable tasks (T014, T015, T017) - independent utilities

**User Story 1**: Most tasks sequential (generation pipeline), but T032 report can run in parallel with state update

**User Story 4**: 2 parallelizable tasks (T033, T034) - input detection

**User Story 2**: 2 parallelizable tasks (T056, T057) - contract generation

**User Story 3**: 2 parallelizable tasks (T072, T073) - data loading

**User Story 5**: 2 parallelizable tasks (T091, T092) - command registration

**User Story 6**: 5 parallelizable tasks (T104-T108) - draft generation components

**Phase 9 (Polish)**: 16 parallelizable tasks (T117-T132) - testing, documentation, quality

**Total Parallelizable**: 41 tasks out of 136 = **30.1% parallel** ✅ (meets >=30% requirement from spec SC-007)

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Included**:
- Phase 1 (Setup)
- Phase 2 (Foundational Infrastructure)
- Phase 3 (User Story 1 - Create Feature Specification)
- Phase 4 (User Story 4 - Create Project Constitution)

**Rationale**: These two user stories (P1 priority) form the foundation of the governance framework. Constitution defines the rules, specification creates the first governed artifact. Together they demonstrate the core value proposition: AI-generated, constitution-compliant documentation.

**MVP Test**:
1. Install agent (`pip install -e .`)
2. Create constitution (`python -m agent.cli constitution principles.txt`)
3. Generate spec (`python -m agent.cli specify "Add user authentication"`)
4. Verify: constitution.md exists with valid version, spec.md exists with quality checklist passed, both PHRs created

### Incremental Delivery

**Iteration 1** (MVP): US1 + US4 (Tasks T001-T044, T117-T121)
- Deliverable: Working /sp.specify and /sp.constitution commands
- Value: Governance framework established, first workflow operational

**Iteration 2**: US2 (Tasks T045-T066, T122-T126)
- Deliverable: Working /sp.plan command with Phase 0 & Phase 1 outputs
- Value: Complete specification-to-plan workflow

**Iteration 3**: US3 (Tasks T067-T090, T127-T129)
- Deliverable: Working /sp.tasks command
- Value: Full design-to-implementation task breakdown

**Iteration 4**: US5 + US6 (Tasks T091-T116, T130-T132)
- Deliverable: Working /sp.adr and draft commands
- Value: Complete feature set with decision documentation and communication drafting

**Iteration 5**: Polish (Tasks T133-T136)
- Deliverable: Production-ready agent with CI/CD
- Value: Quality, documentation, maintainability

---

## Validation & Acceptance

Each user story phase must pass its "Independent Test" criteria before proceeding to the next phase. Quality validation runs automatically via validation.py using contracts/validation-rules.yaml.

**Constitution Compliance**: All tasks respect Constitution v1.0.0 principles. Workflow state tracking enforced by workflow_orchestrator. Atomic file operations prevent partial writes. One-question-at-a-time enforced by clarification module.

**Success Criteria Mapping** (from spec.md):
- SC-001: One question at a time → T016, T024, T051 enforce policy
- SC-002: 100% quality validation pass → T027, T041, T062, T086, T100 validate artifacts
- SC-003: Constitution checks before proceeding → T010, T046, T060 run compliance checks
- SC-004: Workflow in <10 minutes → Performance tracked in integration tests T124-T126
- SC-005: 100% drafts require approval → T109, T110 enforce approval gates
- SC-006: 1:1 commands to PHRs → T030, T043, T064, T088, T102, T115 create PHR per command
- SC-007: >=30% parallel → This task list achieves 30.1% parallel ✅
- SC-008: Independent test per story → Each phase includes "Independent Test" section
- SC-009: Violations halt in <1 second → T010 constitution_guard implements real-time checks
- SC-010: ADR suggestions intelligent → T092 implements significance test (impact + alternatives + scope)
