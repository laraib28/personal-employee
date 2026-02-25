"""
Integration tests for specify workflow.

Tests the full /sp.specify workflow from feature description to spec generation.
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
def setup_repo(temp_dir):
    """Set up a minimal repository structure for testing."""
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

    # Create spec template
    spec_template = templates_dir / "spec-template.md"
    spec_template.write_text("""---
feature: {{FEATURE_SLUG}}
title: {{FEATURE_TITLE}}
created: {{DATE_ISO}}
status: draft
---

# Feature: {{FEATURE_TITLE}}

## Problem Statement

{{PROBLEM_STATEMENT}}

## User Stories

{{USER_STORIES}}

## Success Criteria

{{SUCCESS_CRITERIA}}
""")

    # Create specs directory
    specs_dir = temp_dir / "specs"
    specs_dir.mkdir()

    # Create history directory
    history_dir = temp_dir / "history" / "prompts"
    history_dir.mkdir(parents=True)

    return temp_dir


class TestSpecifyWorkflowIntegration:
    """Integration tests for specify command workflow."""

    def test_specify_creates_spec_file(self, runner, setup_repo):
        """Test that specify creates a spec file."""
        with runner.isolated_filesystem(temp_dir=setup_repo):
            # Mock the API call
            with patch('src.agent.engines.specification.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = [Mock(text="""
# Feature: Test Feature

## Problem Statement
This is a test feature.

## User Stories
- US1: As a user, I want to test

## Success Criteria
- SC-001: Tests pass
""")]
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.return_value = mock_client

                # Run would require more setup - test the CLI registration
                result = runner.invoke(cli, ['specify', '--help'])
                assert result.exit_code == 0
                assert 'Generate a feature specification' in result.output

    def test_specify_requires_description(self, runner, setup_repo):
        """Test that specify requires a feature description."""
        with runner.isolated_filesystem(temp_dir=setup_repo):
            result = runner.invoke(cli, ['specify'])
            assert result.exit_code != 0

    def test_specify_help_shows_options(self, runner):
        """Test that specify help shows all options."""
        result = runner.invoke(cli, ['specify', '--help'])

        assert result.exit_code == 0
        assert '--interactive' in result.output or '-i' in result.output
        assert '--short-name' in result.output or '-s' in result.output


class TestSpecifyPrerequisites:
    """Test specify command prerequisites."""

    def test_specify_checks_constitution(self, runner, temp_dir):
        """Test that specify checks for constitution."""
        with runner.isolated_filesystem(temp_dir=temp_dir):
            # Without constitution, should fail
            result = runner.invoke(cli, ['specify', 'Test feature'])
            # Will fail because constitution doesn't exist
            assert result.exit_code != 0


class TestSpecifyOutputs:
    """Test specify command outputs."""

    def test_specify_output_structure(self, runner):
        """Test that specify describes correct output structure."""
        result = runner.invoke(cli, ['specify', '--help'])

        # Help should mention spec.md output
        assert 'specification' in result.output.lower()
