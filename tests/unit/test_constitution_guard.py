"""
Unit tests for constitution guard module.

Tests constitution loading, principle validation, and compliance checking.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.agent.core.constitution_guard import (
    ConstitutionGuard,
    load_constitution,
    check_compliance,
    ConstitutionError
)


class TestConstitutionGuard:
    """Test ConstitutionGuard class."""

    def test_init_with_default_path(self, temp_dir):
        """Test initialization with default constitution path."""
        guard = ConstitutionGuard(repo_root=temp_dir)
        expected_path = temp_dir / ".specify" / "memory" / "constitution.md"
        assert guard.constitution_path == expected_path

    def test_init_with_custom_path(self, temp_dir):
        """Test initialization with custom constitution path."""
        custom_path = temp_dir / "custom" / "constitution.md"
        guard = ConstitutionGuard(
            repo_root=temp_dir,
            constitution_path=custom_path
        )
        assert guard.constitution_path == custom_path

    def test_load_constitution_file_not_found(self, temp_dir):
        """Test that missing constitution file raises error."""
        guard = ConstitutionGuard(repo_root=temp_dir)
        with pytest.raises(ConstitutionError) as exc_info:
            guard.load()
        assert "not found" in str(exc_info.value).lower()

    def test_load_valid_constitution(self, temp_dir, sample_constitution):
        """Test loading a valid constitution file."""
        # Create constitution file
        const_dir = temp_dir / ".specify" / "memory"
        const_dir.mkdir(parents=True)
        const_path = const_dir / "constitution.md"

        const_content = """---
version: 1.0.0
status: ACTIVE
---

# Project Constitution

## Principles

### Principle 1: One Question at a Time
Agent asks one clarification question per iteration.
"""
        const_path.write_text(const_content)

        guard = ConstitutionGuard(repo_root=temp_dir)
        result = guard.load()

        assert result is not None
        assert guard.is_loaded

    def test_get_principles(self, temp_dir):
        """Test extracting principles from constitution."""
        const_dir = temp_dir / ".specify" / "memory"
        const_dir.mkdir(parents=True)
        const_path = const_dir / "constitution.md"

        const_content = """---
version: 1.0.0
status: ACTIVE
---

# Project Constitution

## Principles

### Principle 1: One Question at a Time
Agent asks one clarification question per iteration.

### Principle 2: Atomic Operations
All file operations are atomic.
"""
        const_path.write_text(const_content)

        guard = ConstitutionGuard(repo_root=temp_dir)
        guard.load()
        principles = guard.get_principles()

        assert len(principles) >= 2

    def test_check_compliance_loaded(self, temp_dir):
        """Test compliance check when constitution is loaded."""
        const_dir = temp_dir / ".specify" / "memory"
        const_dir.mkdir(parents=True)
        const_path = const_dir / "constitution.md"

        const_content = """---
version: 1.0.0
status: ACTIVE
---

# Project Constitution

## Principles

### Principle 1: Test Principle
Test description.
"""
        const_path.write_text(const_content)

        guard = ConstitutionGuard(repo_root=temp_dir)
        guard.load()

        # Should not raise if constitution is loaded
        result = guard.check_compliance()
        assert result is True

    def test_check_compliance_not_loaded(self, temp_dir):
        """Test compliance check when constitution not loaded."""
        guard = ConstitutionGuard(repo_root=temp_dir)

        with pytest.raises(ConstitutionError):
            guard.check_compliance()


class TestConstitutionValidation:
    """Test constitution content validation."""

    def test_validate_version_format(self, temp_dir):
        """Test that version follows semver format."""
        const_dir = temp_dir / ".specify" / "memory"
        const_dir.mkdir(parents=True)
        const_path = const_dir / "constitution.md"

        const_content = """---
version: 1.0.0
status: ACTIVE
---

# Constitution
"""
        const_path.write_text(const_content)

        guard = ConstitutionGuard(repo_root=temp_dir)
        guard.load()

        # Version should be accessible
        assert guard.version is not None

    def test_validate_status_active(self, temp_dir):
        """Test that status is ACTIVE."""
        const_dir = temp_dir / ".specify" / "memory"
        const_dir.mkdir(parents=True)
        const_path = const_dir / "constitution.md"

        const_content = """---
version: 1.0.0
status: ACTIVE
---

# Constitution
"""
        const_path.write_text(const_content)

        guard = ConstitutionGuard(repo_root=temp_dir)
        guard.load()

        assert guard.status == "ACTIVE"


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_load_constitution_function(self, temp_dir):
        """Test load_constitution convenience function."""
        const_dir = temp_dir / ".specify" / "memory"
        const_dir.mkdir(parents=True)
        const_path = const_dir / "constitution.md"

        const_content = """---
version: 1.0.0
status: ACTIVE
---

# Constitution
"""
        const_path.write_text(const_content)

        with patch('src.agent.core.constitution_guard.Path') as mock_path:
            mock_path.cwd.return_value = temp_dir
            result = load_constitution(repo_root=temp_dir)
            assert result is not None

    def test_check_compliance_function(self, temp_dir):
        """Test check_compliance convenience function."""
        const_dir = temp_dir / ".specify" / "memory"
        const_dir.mkdir(parents=True)
        const_path = const_dir / "constitution.md"

        const_content = """---
version: 1.0.0
status: ACTIVE
---

# Constitution
"""
        const_path.write_text(const_content)

        result = check_compliance(repo_root=temp_dir)
        assert result is True


class TestConstitutionError:
    """Test ConstitutionError exception."""

    def test_error_message(self):
        """Test ConstitutionError message."""
        error = ConstitutionError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inheritance(self):
        """Test that ConstitutionError inherits from Exception."""
        error = ConstitutionError("Test")
        assert isinstance(error, Exception)
