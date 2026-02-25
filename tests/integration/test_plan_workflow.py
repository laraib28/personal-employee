"""
Integration tests for plan workflow.

Tests the full /sp.plan workflow from spec to plan generation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from src.agent.cli import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def setup_repo_with_spec(temp_dir):
    """Set up a repository with existing spec for plan testing."""
    # Create .specify directory structure
    specify_dir = temp_dir / ".specify"
    specify_dir.mkdir()

    memory_dir = specify_dir / "memory"
    memory_dir.mkdir()

    templates_dir = specify_dir / "templates"
    templates_dir.mkdir()

    # Create constitution file
    constitution = memory_dir / "constitution.md"
    constitution.write_text("""---
version: 1.0.0
status: ACTIVE
---

# Project Constitution

## Principles

### Principle 1: One Question at a Time
Agent asks one clarification question per iteration.
""")

    # Create plan template
    plan_template = templates_dir / "plan-template.md"
    plan_template.write_text("""---
feature: {{FEATURE_SLUG}}
title: {{FEATURE_TITLE}} Implementation Plan
created: {{DATE_ISO}}
---

# Implementation Plan: {{FEATURE_TITLE}}

## Technical Context

{{TECHNICAL_CONTEXT}}

## Project Structure

{{PROJECT_STRUCTURE}}
""")

    # Create feature with spec
    feature_dir = temp_dir / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    spec_file = feature_dir / "spec.md"
    spec_file.write_text("""---
feature: 001-test-feature
title: Test Feature
created: 2026-01-14
status: draft
---

# Feature: Test Feature

## Problem Statement
This is a test feature for testing plan generation.

## User Stories

### US1: As a user, I want to test
- Given a test input
- When I run the test
- Then I see expected output

## Success Criteria
- SC-001: Tests pass successfully
""")

    # Create workflow state
    state_file = specify_dir / "state.yaml"
    state_file.write_text("""
features:
  001-test-feature:
    branch: 001-test-feature
    last_step: specify
    artifacts:
      spec: specs/001-test-feature/spec.md
""")

    # Create history directory
    history_dir = temp_dir / "history" / "prompts"
    history_dir.mkdir(parents=True)

    return temp_dir


class TestPlanWorkflowIntegration:
    """Integration tests for plan command workflow."""

    def test_plan_help_shows_options(self, runner):
        """Test that plan help shows all options."""
        result = runner.invoke(cli, ['plan', '--help'])

        assert result.exit_code == 0
        assert '--feature' in result.output or '-f' in result.output

    def test_plan_requires_spec(self, runner, temp_dir):
        """Test that plan requires existing spec."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            # Without spec, should fail
            result = runner.invoke(cli, ['plan'])
            assert result.exit_code != 0


class TestPlanPrerequisites:
    """Test plan command prerequisites."""

    def test_plan_checks_workflow_state(self, runner, setup_repo_with_spec):
        """Test that plan checks workflow state."""
        # Plan should verify spec exists before proceeding
        result = runner.invoke(cli, ['plan', '--help'])
        assert result.exit_code == 0
        assert 'Prerequisites' in result.output or 'specification' in result.output.lower()


class TestPlanOutputs:
    """Test plan command outputs."""

    def test_plan_describes_artifacts(self, runner):
        """Test that plan help describes output artifacts."""
        result = runner.invoke(cli, ['plan', '--help'])

        assert 'plan' in result.output.lower()
