"""
Pytest configuration and shared fixtures for SpecKit Agent System tests.

This module provides common test fixtures used across unit, integration,
and contract tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def sample_constitution() -> Dict[str, Any]:
    """Provide sample constitution data for testing."""
    return {
        "version": "1.0.0",
        "status": "ACTIVE",
        "created": "2026-01-14",
        "principles": [
            {
                "number": 1,
                "name": "One Question at a Time",
                "description": "Agent asks one clarification question per iteration",
                "rules": ["Max 1 question per agent turn", "Wait for user response"],
                "rationale": "Prevents information overload and ensures focused clarification"
            },
            {
                "number": 2,
                "name": "Atomic Operations",
                "description": "All file operations are atomic",
                "rules": ["Use temp file + validate + rename pattern"],
                "rationale": "Prevents partial writes and data corruption"
            }
        ]
    }


@pytest.fixture
def sample_spec_content() -> str:
    """Provide sample feature specification content for testing."""
    return """---
feature: 001-test-feature
title: Test Feature
created: 2026-01-14
status: draft
---

# Feature: Test Feature

## Problem Statement

This is a test feature for validating the agent system.

## User Stories

### US1: As a user, I want to test the system
- Given a test scenario
- When I run the test
- Then I see the expected results

## Success Criteria

- SC-001: Tests pass successfully
"""


@pytest.fixture
def sample_plan_content() -> str:
    """Provide sample implementation plan content for testing."""
    return """---
feature: 001-test-feature
title: Test Feature Implementation Plan
created: 2026-01-14
---

# Implementation Plan: Test Feature

## Technical Context

- Language: Python 3.11+
- Framework: pytest

## Project Structure

```
src/
  test_module.py
tests/
  test_test_module.py
```
"""


@pytest.fixture
def sample_tasks_content() -> str:
    """Provide sample task list content for testing."""
    return """---
feature: 001-test-feature
title: Test Feature Task List
created: 2026-01-14
---

# Task List: Test Feature

## Phase 1: Setup

- [ ] T001 Create project structure
- [ ] T002 Write initial tests

## Phase 2: Implementation

- [ ] T003 Implement feature logic
- [ ] T004 Validate implementation
"""


@pytest.fixture
def sample_phr_data() -> Dict[str, Any]:
    """Provide sample PHR (Prompt History Record) data for testing."""
    return {
        "id": 1,
        "title": "Test Feature Specification",
        "stage": "spec",
        "feature": "001-test-feature",
        "date": "2026-01-14",
        "surface": "agent",
        "model": "claude-sonnet-4-5",
        "branch": "001-test-feature",
        "user": "test-user",
        "command": "/sp.specify",
        "labels": ["specification", "test"],
        "prompt": "Create a test feature specification",
        "response": "Generated specification for test feature",
        "files_created": ["specs/001-test-feature/spec.md"],
        "tests_run": []
    }


@pytest.fixture
def mock_anthropic_client(mocker):
    """Mock Anthropic API client for testing."""
    mock_client = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.content = [mocker.Mock(text="Mocked Claude response")]
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_git_repo(mocker, temp_dir):
    """Mock Git repository for testing."""
    mock_repo = mocker.Mock()
    mock_repo.working_dir = str(temp_dir)
    mock_repo.active_branch.name = "001-test-feature"
    return mock_repo


@pytest.fixture
def sample_workflow_state() -> Dict[str, Any]:
    """Provide sample workflow state for testing."""
    return {
        "last_step": "specify",
        "feature": "001-test-feature",
        "branch": "001-test-feature",
        "timestamp": datetime.now().isoformat(),
        "artifacts": {
            "spec": "specs/001-test-feature/spec.md",
            "plan": None,
            "tasks": None
        }
    }


@pytest.fixture
def sample_validation_rules() -> Dict[str, Any]:
    """Provide sample validation rules for testing."""
    return {
        "specification": {
            "required_sections": [
                "Problem Statement",
                "User Stories",
                "Success Criteria"
            ],
            "forbidden_patterns": [
                "TODO",
                "FIXME",
                "{{.*}}",
                "\\[.*PLACEHOLDER.*\\]"
            ]
        },
        "plan": {
            "required_sections": [
                "Technical Context",
                "Project Structure"
            ],
            "forbidden_patterns": [
                "NEEDS CLARIFICATION",
                "TBD"
            ]
        }
    }
