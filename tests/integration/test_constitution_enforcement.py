"""
Integration tests for constitution enforcement.

Tests that constitution compliance is checked at workflow steps.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from click.testing import CliRunner

from src.agent.cli import cli
from src.agent.core.constitution_guard import ConstitutionGuard, ConstitutionError


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def repo_with_constitution(temp_dir):
    """Set up a repository with a valid constitution."""
    # Create .specify directory structure
    specify_dir = temp_dir / ".specify"
    specify_dir.mkdir()

    memory_dir = specify_dir / "memory"
    memory_dir.mkdir()

    # Create constitution file
    constitution = memory_dir / "constitution.md"
    constitution.write_text("""---
version: 1.0.0
status: ACTIVE
created: 2026-01-14
---

# Project Constitution

## Principles

### Principle 1: One Question at a Time
Agent asks one clarification question per iteration.

**Rules:**
- Max 1 question per agent turn
- Wait for user response before next question

**Rationale:**
Prevents information overload and ensures focused clarification.

### Principle 2: Atomic Operations
All file operations are atomic.

**Rules:**
- Use temp file + validate + rename pattern
- Never leave partial writes

**Rationale:**
Prevents data corruption and ensures consistency.

### Principle 3: Constitution Compliance
All workflows must check constitution compliance.

**Rules:**
- Check compliance before proceeding
- Halt immediately on violations

**Rationale:**
Ensures governance is enforced consistently.
""")

    return temp_dir


@pytest.fixture
def repo_without_constitution(temp_dir):
    """Set up a repository without constitution."""
    specify_dir = temp_dir / ".specify"
    specify_dir.mkdir()

    memory_dir = specify_dir / "memory"
    memory_dir.mkdir()

    # No constitution file created
    return temp_dir


class TestConstitutionLoading:
    """Test constitution loading in workflows."""

    def test_load_valid_constitution(self, repo_with_constitution):
        """Test loading a valid constitution file."""
        guard = ConstitutionGuard(repo_root=repo_with_constitution)
        guard.load()

        assert guard.is_loaded
        assert guard.version == "1.0.0"
        assert guard.status == "ACTIVE"

    def test_load_missing_constitution_raises(self, repo_without_constitution):
        """Test that missing constitution raises error."""
        guard = ConstitutionGuard(repo_root=repo_without_constitution)

        with pytest.raises(ConstitutionError) as exc_info:
            guard.load()

        assert "not found" in str(exc_info.value).lower()

    def test_get_principles_after_load(self, repo_with_constitution):
        """Test getting principles after loading."""
        guard = ConstitutionGuard(repo_root=repo_with_constitution)
        guard.load()

        principles = guard.get_principles()
        assert len(principles) >= 3


class TestConstitutionCompliance:
    """Test constitution compliance checking."""

    def test_compliance_check_passes_with_valid_constitution(self, repo_with_constitution):
        """Test that compliance check passes with valid constitution."""
        guard = ConstitutionGuard(repo_root=repo_with_constitution)
        guard.load()

        result = guard.check_compliance()
        assert result is True

    def test_compliance_check_fails_without_load(self, repo_with_constitution):
        """Test that compliance check fails if constitution not loaded."""
        guard = ConstitutionGuard(repo_root=repo_with_constitution)

        with pytest.raises(ConstitutionError):
            guard.check_compliance()


class TestWorkflowConstitutionEnforcement:
    """Test constitution enforcement in workflows."""

    def test_specify_requires_constitution(self, runner, repo_without_constitution):
        """Test that specify command requires constitution."""
        with runner.isolated_filesystem(temp_dir=repo_without_constitution):
            result = runner.invoke(cli, ['specify', 'Test feature'])
            # Should fail due to missing constitution
            assert result.exit_code != 0

    def test_plan_requires_constitution(self, runner, repo_without_constitution):
        """Test that plan command requires constitution."""
        with runner.isolated_filesystem(temp_dir=repo_without_constitution):
            result = runner.invoke(cli, ['plan'])
            # Should fail due to missing constitution
            assert result.exit_code != 0


class TestConstitutionVersioning:
    """Test constitution versioning."""

    def test_version_parsing(self, repo_with_constitution):
        """Test that version is parsed correctly."""
        guard = ConstitutionGuard(repo_root=repo_with_constitution)
        guard.load()

        assert guard.version == "1.0.0"

    def test_version_semver_format(self, repo_with_constitution):
        """Test that version follows semver format."""
        guard = ConstitutionGuard(repo_root=repo_with_constitution)
        guard.load()

        # Should be X.Y.Z format
        parts = guard.version.split('.')
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestConstitutionStatus:
    """Test constitution status handling."""

    def test_active_status_allows_operations(self, repo_with_constitution):
        """Test that ACTIVE status allows operations."""
        guard = ConstitutionGuard(repo_root=repo_with_constitution)
        guard.load()

        assert guard.status == "ACTIVE"
        assert guard.check_compliance() is True

    def test_inactive_status_detected(self, temp_dir):
        """Test that inactive constitution is detected."""
        # Create inactive constitution
        specify_dir = temp_dir / ".specify"
        specify_dir.mkdir()
        memory_dir = specify_dir / "memory"
        memory_dir.mkdir()

        constitution = memory_dir / "constitution.md"
        constitution.write_text("""---
version: 1.0.0
status: INACTIVE
---

# Project Constitution
""")

        guard = ConstitutionGuard(repo_root=temp_dir)
        guard.load()

        assert guard.status == "INACTIVE"
