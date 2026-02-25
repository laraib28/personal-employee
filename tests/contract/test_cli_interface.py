"""
Contract tests for CLI interface.

Tests that all CLI commands are registered, have proper help text,
and follow the expected interface contracts.
"""

import pytest
from click.testing import CliRunner

from src.agent.cli import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCLICommands:
    """Test that all required CLI commands exist and are accessible."""

    def test_cli_help(self, runner):
        """Test that main CLI help is accessible."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'SpecKit Agent System' in result.output

    def test_cli_version(self, runner):
        """Test version command."""
        result = runner.invoke(cli, ['version'])
        assert result.exit_code == 0
        assert 'SpecKit Agent System' in result.output

    def test_specify_command_exists(self, runner):
        """Test that specify command is registered."""
        result = runner.invoke(cli, ['specify', '--help'])
        assert result.exit_code == 0
        assert 'Generate a feature specification' in result.output

    def test_constitution_command_exists(self, runner):
        """Test that constitution command is registered."""
        result = runner.invoke(cli, ['constitution', '--help'])
        assert result.exit_code == 0
        assert 'Create or update the project constitution' in result.output

    def test_plan_command_exists(self, runner):
        """Test that plan command is registered."""
        result = runner.invoke(cli, ['plan', '--help'])
        assert result.exit_code == 0
        assert 'Generate implementation plan' in result.output

    def test_tasks_command_exists(self, runner):
        """Test that tasks command is registered."""
        result = runner.invoke(cli, ['tasks', '--help'])
        assert result.exit_code == 0
        assert 'Generate task list' in result.output

    def test_adr_command_exists(self, runner):
        """Test that adr command is registered."""
        result = runner.invoke(cli, ['adr', '--help'])
        assert result.exit_code == 0
        assert 'Document an architectural decision' in result.output

    def test_draft_command_exists(self, runner):
        """Test that draft command is registered."""
        result = runner.invoke(cli, ['draft', '--help'])
        assert result.exit_code == 0
        assert 'Create a communication draft' in result.output

    def test_status_command_exists(self, runner):
        """Test that status command is registered."""
        result = runner.invoke(cli, ['status', '--help'])
        assert result.exit_code == 0


class TestSpecifyCommandInterface:
    """Test specify command interface contract."""

    def test_specify_requires_description_or_interactive(self, runner):
        """Test that specify requires feature description."""
        result = runner.invoke(cli, ['specify'])
        assert result.exit_code != 0
        assert 'FEATURE_DESCRIPTION is required' in result.output or 'Error' in result.output

    def test_specify_accepts_short_name_option(self, runner):
        """Test that specify accepts --short-name option."""
        result = runner.invoke(cli, ['specify', '--help'])
        assert '--short-name' in result.output or '-s' in result.output


class TestConstitutionCommandInterface:
    """Test constitution command interface contract."""

    def test_constitution_requires_input(self, runner):
        """Test that constitution requires content input."""
        result = runner.invoke(cli, ['constitution'])
        assert result.exit_code != 0
        assert 'Must provide constitution content' in result.output or 'Error' in result.output

    def test_constitution_accepts_file_option(self, runner):
        """Test that constitution accepts --file option."""
        result = runner.invoke(cli, ['constitution', '--help'])
        assert '--file' in result.output or '-f' in result.output


class TestADRCommandInterface:
    """Test ADR command interface contract."""

    def test_adr_requires_decision_title(self, runner):
        """Test that adr requires decision title argument."""
        result = runner.invoke(cli, ['adr'])
        assert result.exit_code != 0
        # Click will show "Missing argument" error

    def test_adr_accepts_context_option(self, runner):
        """Test that adr accepts --context option."""
        result = runner.invoke(cli, ['adr', '--help'])
        assert '--context' in result.output or '-c' in result.output

    def test_adr_accepts_feature_option(self, runner):
        """Test that adr accepts --feature option."""
        result = runner.invoke(cli, ['adr', '--help'])
        assert '--feature' in result.output or '-f' in result.output


class TestDraftCommandInterface:
    """Test draft command interface contract."""

    def test_draft_requires_purpose(self, runner):
        """Test that draft requires purpose argument."""
        result = runner.invoke(cli, ['draft', '--type', 'email'])
        assert result.exit_code != 0
        # Click will show "Missing argument" error

    def test_draft_requires_type(self, runner):
        """Test that draft requires --type option."""
        result = runner.invoke(cli, ['draft', 'Test message'])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or '--type' in result.output

    def test_draft_type_choices(self, runner):
        """Test that draft type is restricted to email/whatsapp."""
        result = runner.invoke(cli, ['draft', '--help'])
        assert 'email' in result.output
        assert 'whatsapp' in result.output

    def test_draft_accepts_recipient_option(self, runner):
        """Test that draft accepts --recipient option."""
        result = runner.invoke(cli, ['draft', '--help'])
        assert '--recipient' in result.output or '-r' in result.output

    def test_draft_accepts_tone_option(self, runner):
        """Test that draft accepts --tone option."""
        result = runner.invoke(cli, ['draft', '--help'])
        assert '--tone' in result.output
        assert 'professional' in result.output
        assert 'friendly' in result.output


class TestCLIGlobalOptions:
    """Test global CLI options."""

    def test_verbose_option(self, runner):
        """Test that --verbose option is available."""
        result = runner.invoke(cli, ['--help'])
        assert '--verbose' in result.output or '-v' in result.output

    def test_debug_option(self, runner):
        """Test that --debug option is available."""
        result = runner.invoke(cli, ['--help'])
        assert '--debug' in result.output

    def test_version_option(self, runner):
        """Test that --version option is available."""
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
