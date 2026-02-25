# SpecKit Agent System

[![Tests](https://github.com/speckit/personal-employe/actions/workflows/tests.yml/badge.svg)](https://github.com/speckit/personal-employe/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI agent system that executes governed workflows for Spec-Driven Development with strict constitution compliance enforcement.

## Overview

SpecKit Agent System enables AI-driven software development workflows that are:
- **Constitution-Governed**: All actions comply with project governance principles
- **Workflow-Orchestrated**: Specification → Planning → Task Generation → Implementation
- **Quality-Validated**: Automatic validation against defined quality rules
- **Fully-Traced**: Every command generates a Prompt History Record (PHR)

## Features

| Command | Description | Status |
|---------|-------------|--------|
| `specify` | Generate feature specification from natural language | Implemented |
| `constitution` | Create or update project constitution | Implemented |
| `plan` | Generate implementation plan from specification | Implemented |
| `tasks` | Generate task list from plan | Implemented |
| `adr` | Document architectural decisions | Implemented |
| `draft` | Create communication drafts (email/WhatsApp) | Implemented |

## Quick Start

See [quickstart.md](./specs/001-ai-agent-system/quickstart.md) for detailed instructions.

### Installation

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Set up API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Usage Examples

```bash
# Show available commands
speckit-agent --help

# Create a project constitution
speckit-agent constitution --file principles.txt

# Generate a feature specification
speckit-agent specify "Add user authentication with JWT tokens"

# Generate implementation plan (requires existing spec)
speckit-agent plan

# Generate task list (requires existing plan)
speckit-agent tasks

# Document an architectural decision
speckit-agent adr "Use PostgreSQL for data storage"

# Create a communication draft
speckit-agent draft "Notify team about release" --type email --recipient "Team"

# Check workflow status
speckit-agent status
```

## Project Structure

```
personal-employe/
├── src/agent/              # Main package
│   ├── commands/           # CLI command handlers
│   ├── core/               # Core infrastructure
│   ├── engines/            # Workflow engines
│   ├── templates/          # Jinja2 templates
│   └── utils/              # Utilities
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── contract/          # Contract tests
├── .specify/              # SpecKit configuration
│   ├── memory/            # Constitution and state
│   ├── templates/         # Document templates
│   └── scripts/           # Helper scripts
├── specs/                 # Feature specifications
├── drafts/                # Communication drafts
└── history/               # PHRs and ADRs
    ├── prompts/           # Prompt History Records
    └── adr/               # Architecture Decision Records
```

## Technology Stack

- **Python 3.11+** - Core language
- **Claude API** (anthropic SDK) - AI generation
- **Jinja2** - Template engine
- **PyYAML** - YAML parsing
- **GitPython** - Git integration
- **Click** - CLI framework
- **pytest** - Testing

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/agent --cov-report=html

# Format code
black src/ tests/

# Type checking
mypy src/agent
```

## Key Concepts

### Constitution
The constitution (`.specify/memory/constitution.md`) defines governance principles that all workflows must follow. Compliance is checked before each operation.

### Prompt History Records (PHR)
Every command execution creates a PHR in `history/prompts/`, providing full traceability of agent interactions.

### Architecture Decision Records (ADR)
Significant architectural decisions are documented in `history/adr/` using the `/sp.adr` command with significance testing.

### Communication Drafts
All email and WhatsApp drafts require explicit human approval before sending. Drafts are stored in `drafts/{type}/` with `approval_status: pending`.

## Documentation

- [Specification](./specs/001-ai-agent-system/spec.md)
- [Implementation Plan](./specs/001-ai-agent-system/plan.md)
- [Task List](./specs/001-ai-agent-system/tasks.md)
- [Constitution](./.specify/memory/constitution.md)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Format code (`black src/ tests/`)
6. Commit your changes
7. Push to the branch
8. Open a Pull Request

## License

MIT
