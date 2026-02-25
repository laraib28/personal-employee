# Quickstart Guide: AI Agent System

**Feature**: 001-ai-agent-system
**Date**: 2026-01-13
**Purpose**: Developer guide for implementing and using the AI agent system

## Prerequisites

### System Requirements
- **Python**: 3.11 or higher
- **OS**: Linux, macOS, or Windows WSL
- **Git**: 2.30 or higher
- **Text Editor**: VS Code, Vim, or any editor with Python support

### Python Dependencies
See `requirements.txt` for complete list:
- `anthropic>=0.40.0` - Claude API SDK
- `Jinja2>=3.1.0` - Template rendering
- `PyYAML>=6.0` - YAML parsing
- `GitPython>=3.1.0` - Git integration
- `click>=8.0` - CLI framework
- `pytest>=7.0` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `markdown-it-py` - Markdown AST parsing (for validation)

## Installation

### 1. Clone Repository

```bash
cd /path/to/your/workspace
git clone <repository-url>
cd <repository-name>
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows WSL: source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Keys

Create `.env` file in repository root:

```bash
# Claude API Key (required for agent operations)
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Configure model (defaults to claude-sonnet-4-5)
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

**Never commit `.env` to git!** (Already in `.gitignore`)

### 5. Verify Installation

```bash
python -m agent.cli --help
```

Expected output:
```text
Usage: agent.cli [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  constitution  Create or update project constitution
  specify       Generate feature specification
  plan          Generate implementation plan
  tasks         Generate task list
  adr           Document architectural decision
```

## Running Commands

### `/sp.specify` - Generate Feature Specification

**Usage**:
```bash
python -m agent.cli specify "Your feature description here"
```

**Example**:
```bash
python -m agent.cli specify "Add user authentication with OAuth2"
```

**What it does**:
1. Runs constitution compliance check
2. Creates feature branch (`001-feature-name`)
3. Generates `specs/001-feature-name/spec.md`
4. Creates quality checklist `specs/001-feature-name/checklists/requirements.md`
5. Asks up to 3 clarification questions (one at a time)
6. Validates specification against quality gates
7. Creates PHR in `history/prompts/001-feature-name/0001-*.spec.prompt.md`

**Output**:
- Feature branch created
- Specification file path
- Checklist validation results
- PHR ID

### `/sp.plan` - Generate Implementation Plan

**Usage**:
```bash
# Must be on feature branch
git checkout 001-feature-name
python -m agent.cli plan
```

**What it does**:
1. Runs constitution compliance check
2. Reads existing `spec.md`
3. Asks clarification questions for technical context (e.g., language choice)
4. Generates Phase 0 artifacts:
   - `research.md` (research decisions)
5. Generates Phase 1 artifacts:
   - `plan.md` (implementation plan)
   - `data-model.md` (entity structures)
   - `contracts/` (API contracts, validation rules)
   - `quickstart.md` (this file)
6. Updates agent context (`CLAUDE.md` or equivalent)
7. Re-evaluates constitution compliance
8. Creates PHR in `history/prompts/001-feature-name/0002-*.plan.prompt.md`

**Output**:
- Plan file path
- Research, data-model, contracts, quickstart paths
- Constitution recheck results
- PHR ID

### `/sp.tasks` - Generate Task List

**Usage**:
```bash
# Must be on feature branch with complete plan
git checkout 001-feature-name
python -m agent.cli tasks
```

**What it does**:
1. Runs constitution compliance check
2. Reads existing `spec.md` and `plan.md`
3. Generates `tasks.md` with:
   - Tasks grouped by user story
   - Dependency ordering
   - Parallel execution markers `[P]`
   - Exact file paths
4. Validates task list (acyclic dependencies, 30%+ parallel)
5. Creates PHR in `history/prompts/001-feature-name/0003-*.tasks.prompt.md`

**Output**:
- Task file path
- Task count, parallel percentage
- PHR ID

### `/sp.constitution` - Create/Update Constitution

**Usage**:
```bash
# From repository root
python -m agent.cli constitution constitution.tsx
```

Or provide content inline:
```bash
python -m agent.cli constitution --inline "
Principle I: Human Never Writes
...
"
```

**What it does**:
1. Reads constitution content (file or inline)
2. Fills constitution template
3. Validates (no placeholders, valid semver, ISO dates)
4. Generates sync impact report
5. Writes to `.specify/memory/constitution.md`
6. Creates PHR in `history/prompts/constitution/0001-*.constitution.prompt.md`

**Output**:
- Constitution file path
- Version (MAJOR.MINOR.PATCH)
- Status (ACTIVE)
- PHR ID

### `/sp.adr` - Document Architectural Decision

**Usage**:
```bash
# From feature branch or repository root
python -m agent.cli adr "Use PostgreSQL for data storage"
```

**What it does**:
1. Tests decision significance (impact + alternatives + scope)
2. Prompts for context (if not inferable from workspace)
3. Generates ADR with:
   - Decision statement
   - Alternatives considered
   - Consequences (positive/negative)
   - Status (Proposed → Accepted)
4. Writes to `history/adr/0001-use-postgresql.md`
5. Creates PHR in `history/prompts/{feature}/0004-*.misc.prompt.md`

**Output**:
- ADR file path
- ADR ID
- PHR ID

## Directory Structure Walkthrough

```text
.
├── .specify/                       # SpecKit Plus templates and scripts
│   ├── memory/
│   │   └── constitution.md         # Active constitution
│   ├── state.yaml                  # Workflow state tracking
│   ├── templates/                  # Jinja2 templates (read-only)
│   │   ├── spec-template.md
│   │   ├── plan-template.md
│   │   ├── tasks-template.md
│   │   └── phr-template.prompt.md
│   └── scripts/bash/               # Existing bash scripts
│       ├── create-phr.sh           # PHR creation (reused by agent)
│       ├── setup-plan.sh           # Plan initialization
│       └── update-agent-context.sh # Agent context updater
│
├── src/agent/                      # AI agent source code
│   ├── cli.py                      # Click CLI entry point
│   ├── commands/                   # Command handlers
│   │   ├── specify.py              # /sp.specify logic
│   │   ├── plan.py                 # /sp.plan logic
│   │   ├── tasks.py                # /sp.tasks logic
│   │   ├── constitution.py         # /sp.constitution logic
│   │   └── adr.py                  # /sp.adr logic
│   ├── core/                       # Core infrastructure
│   │   ├── constitution_guard.py   # Compliance checker
│   │   ├── workflow_orchestrator.py # Step enforcement
│   │   ├── clarification.py        # One-question-at-a-time
│   │   └── phr_manager.py          # PHR creation
│   ├── engines/                    # Generation logic
│   │   ├── specification.py        # Spec generation
│   │   ├── planning.py             # Plan generation
│   │   ├── task_gen.py             # Task generation
│   │   └── validation.py           # Quality validation
│   ├── templates/
│   │   └── renderer.py             # Jinja2 wrapper
│   └── utils/
│       ├── file_ops.py             # Atomic file writes
│       └── git_ops.py              # GitPython operations
│
├── tests/                          # Pytest test suite
│   ├── conftest.py                 # Shared fixtures
│   ├── contract/                   # Contract tests (CLI interface)
│   ├── integration/                # Integration tests (workflows)
│   └── unit/                       # Unit tests (components)
│
├── specs/                          # Feature specifications
│   └── 001-feature-name/
│       ├── spec.md
│       ├── plan.md
│       ├── tasks.md
│       ├── research.md
│       ├── data-model.md
│       ├── quickstart.md
│       ├── contracts/
│       └── checklists/
│
├── history/                        # Immutable logs
│   ├── adr/                        # Architecture Decision Records
│   └── prompts/                    # Prompt History Records
│       ├── constitution/
│       ├── {feature-name}/
│       └── general/
│
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Project configuration
├── setup.py                        # Package installation
└── README.md                       # Project overview
```

## Testing Strategy

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=agent --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Specific Test Types

**Contract Tests** (CLI interface validation):
```bash
pytest tests/contract/
```

**Integration Tests** (end-to-end workflows):
```bash
pytest tests/integration/
```

**Unit Tests** (component tests):
```bash
pytest tests/unit/
```

### Run Specific Test File

```bash
pytest tests/unit/test_constitution_guard.py
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Failed Tests Only

```bash
pytest --lf
```

## Troubleshooting Common Issues

### Issue: `ModuleNotFoundError: No module named 'agent'`

**Solution**: Activate virtual environment and install package in editable mode:
```bash
source .venv/bin/activate
pip install -e .
```

### Issue: `anthropic.APIError: Invalid API key`

**Solution**: Check `.env` file has valid `ANTHROPIC_API_KEY`:
```bash
cat .env | grep ANTHROPIC_API_KEY
```

Get API key from: https://console.anthropic.com/settings/keys

### Issue: `ConstitutionViolation: Specification not found`

**Solution**: Run `/sp.specify` before `/sp.plan`:
```bash
python -m agent.cli specify "Your feature"
python -m agent.cli plan
```

### Issue: `ValueError: Template not found`

**Solution**: Ensure `.specify/templates/` directory exists with template files. If missing, copy from SpecKit Plus installation:
```bash
cp -r /path/to/speckit-plus/.specify/templates/ .specify/
```

### Issue: `GitCommandError: branch already exists`

**Solution**: Feature number conflict. Check existing branches:
```bash
git branch | grep -E '^[* ]*[0-9]+-'
```

Delete stale branch or increment feature number manually.

### Issue: Tests failing with `FileNotFoundError`

**Solution**: Run tests from repository root (where `tests/` directory is):
```bash
cd /path/to/repository/root
pytest
```

### Issue: Quality validation fails with "implementation details"

**Solution**: Specification contains technology-specific terms (Python, React, PostgreSQL). Remove implementation details, focus on business requirements:
- ❌ "System uses PostgreSQL database"
- ✅ "System persists user data"

### Issue: `YAML parse error` in generated file

**Solution**: Generated file has malformed YAML front-matter. Check for:
- Unescaped special characters (`:`, `#`, `|`)
- Missing quotes around strings with special chars
- Indentation errors

Use YAML linter:
```bash
python -c "import yaml; yaml.safe_load(open('file.md').read().split('---')[1])"
```

## Contributing Guidelines

### Adding New Commands

1. Create command handler in `src/agent/commands/new_command.py`
2. Implement command logic using existing patterns
3. Register command in `src/agent/cli.py`:
   ```python
   @cli.command()
   def new_command():
       """Command description"""
       from agent.commands.new_command import execute
       execute()
   ```
4. Add contract to `contracts/cli-commands.yaml`
5. Add validation rules to `contracts/validation-rules.yaml`
6. Write tests in `tests/contract/test_new_command.py`
7. Update this quickstart guide

### Code Style

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Docstrings for all public functions (Google style)
- Max line length: 100 characters
- Run `black` formatter before committing:
  ```bash
  pip install black
  black src/ tests/
  ```

### Testing Requirements

- All new code requires tests
- Minimum 80% code coverage
- Contract tests for CLI interface changes
- Integration tests for workflow changes
- Unit tests for component logic

### Pull Request Process

1. Create feature branch from `master`
2. Implement changes with tests
3. Run full test suite: `pytest`
4. Run linter: `black src/ tests/`
5. Update documentation (README, quickstart, contracts)
6. Create pull request with:
   - Clear description
   - Test results
   - Breaking changes (if any)
7. Wait for review and CI checks

## Additional Resources

- **Constitution**: `.specify/memory/constitution.md` - governance principles
- **API Contracts**: `specs/001-ai-agent-system/contracts/` - command interfaces
- **Data Model**: `specs/001-ai-agent-system/data-model.md` - entity structures
- **Anthropic API Docs**: https://docs.anthropic.com/claude/reference/
- **SpecKit Plus**: https://github.com/speckit/speckit-plus (template system)

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review existing GitHub issues
3. Create new issue with:
   - Error message (full traceback)
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, Python version)
