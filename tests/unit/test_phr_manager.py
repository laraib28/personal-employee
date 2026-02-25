"""
Unit tests for PHR (Prompt History Record) manager module.

Tests PHR creation, placeholder filling, and routing to correct directories.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.agent.core.phr_manager import (
    PHRManager,
    create_phr,
    PHRError
)


class TestPHRManager:
    """Test PHRManager class."""

    def test_init_with_default_paths(self, temp_dir):
        """Test initialization with default paths."""
        manager = PHRManager(repo_root=temp_dir)
        assert manager.repo_root == temp_dir
        assert manager.prompts_dir == temp_dir / "history" / "prompts"

    def test_init_creates_prompts_directory(self, temp_dir):
        """Test that prompts directory is created if needed."""
        manager = PHRManager(repo_root=temp_dir)
        manager._ensure_directories("general")
        assert (temp_dir / "history" / "prompts" / "general").exists()


class TestPHRRouting:
    """Test PHR routing to correct directories."""

    def test_route_constitution_stage(self, temp_dir):
        """Test that constitution stage routes to constitution dir."""
        manager = PHRManager(repo_root=temp_dir)
        path = manager._get_phr_directory("constitution", None)
        assert "constitution" in str(path)

    def test_route_feature_stage(self, temp_dir):
        """Test that feature stages route to feature dir."""
        manager = PHRManager(repo_root=temp_dir)
        path = manager._get_phr_directory("spec", "001-test-feature")
        assert "001-test-feature" in str(path)

    def test_route_general_stage(self, temp_dir):
        """Test that general stage routes to general dir."""
        manager = PHRManager(repo_root=temp_dir)
        path = manager._get_phr_directory("general", None)
        assert "general" in str(path)

    def test_route_misc_with_feature(self, temp_dir):
        """Test that misc stage with feature routes to feature dir."""
        manager = PHRManager(repo_root=temp_dir)
        path = manager._get_phr_directory("misc", "001-test-feature")
        assert "001-test-feature" in str(path)

    def test_route_misc_without_feature(self, temp_dir):
        """Test that misc stage without feature routes to general dir."""
        manager = PHRManager(repo_root=temp_dir)
        path = manager._get_phr_directory("misc", None)
        assert "general" in str(path)


class TestPHRIDAllocation:
    """Test PHR ID allocation."""

    def test_allocate_first_id(self, temp_dir):
        """Test allocating first ID returns 0001."""
        manager = PHRManager(repo_root=temp_dir)
        phr_id = manager._allocate_id("general", None)
        assert phr_id == "0001"

    def test_allocate_increments_id(self, temp_dir):
        """Test that IDs increment correctly."""
        manager = PHRManager(repo_root=temp_dir)

        # Create directory and first file
        phr_dir = temp_dir / "history" / "prompts" / "general"
        phr_dir.mkdir(parents=True)

        # Create existing PHR file
        existing = phr_dir / "0001-existing.general.prompt.md"
        existing.write_text("existing")

        phr_id = manager._allocate_id("general", None)
        assert phr_id == "0002"

    def test_allocate_handles_gaps(self, temp_dir):
        """Test that allocation handles ID gaps correctly."""
        manager = PHRManager(repo_root=temp_dir)

        phr_dir = temp_dir / "history" / "prompts" / "general"
        phr_dir.mkdir(parents=True)

        # Create files with gap (0001, 0003)
        (phr_dir / "0001-first.general.prompt.md").write_text("first")
        (phr_dir / "0003-third.general.prompt.md").write_text("third")

        phr_id = manager._allocate_id("general", None)
        # Should return next after highest (0004)
        assert phr_id == "0004"


class TestPHRCreation:
    """Test PHR creation."""

    def test_create_phr_returns_info(self, temp_dir, sample_phr_data):
        """Test that create_phr returns PHR info."""
        manager = PHRManager(repo_root=temp_dir)

        result = manager.create_phr(
            title=sample_phr_data['title'],
            stage=sample_phr_data['stage'],
            prompt=sample_phr_data['prompt'],
            response=sample_phr_data['response'],
            feature=sample_phr_data['feature'],
            command=sample_phr_data['command']
        )

        assert 'id' in result
        assert 'path' in result
        assert 'stage' in result

    def test_create_phr_creates_file(self, temp_dir, sample_phr_data):
        """Test that create_phr creates the PHR file."""
        manager = PHRManager(repo_root=temp_dir)

        result = manager.create_phr(
            title=sample_phr_data['title'],
            stage=sample_phr_data['stage'],
            prompt=sample_phr_data['prompt'],
            response=sample_phr_data['response'],
            feature=sample_phr_data['feature'],
            command=sample_phr_data['command']
        )

        phr_path = Path(result['path'])
        assert phr_path.exists()

    def test_create_phr_fills_placeholders(self, temp_dir, sample_phr_data):
        """Test that PHR has no unresolved placeholders."""
        manager = PHRManager(repo_root=temp_dir)

        result = manager.create_phr(
            title=sample_phr_data['title'],
            stage=sample_phr_data['stage'],
            prompt=sample_phr_data['prompt'],
            response=sample_phr_data['response'],
            feature=sample_phr_data['feature'],
            command=sample_phr_data['command']
        )

        phr_path = Path(result['path'])
        content = phr_path.read_text()

        # Should not have placeholder patterns
        assert '{{' not in content
        assert '}}' not in content

    def test_create_phr_includes_prompt_text(self, temp_dir, sample_phr_data):
        """Test that PHR includes the prompt text."""
        manager = PHRManager(repo_root=temp_dir)

        result = manager.create_phr(
            title=sample_phr_data['title'],
            stage=sample_phr_data['stage'],
            prompt=sample_phr_data['prompt'],
            response=sample_phr_data['response'],
            feature=sample_phr_data['feature'],
            command=sample_phr_data['command']
        )

        phr_path = Path(result['path'])
        content = phr_path.read_text()

        assert sample_phr_data['prompt'] in content

    def test_create_phr_includes_response_text(self, temp_dir, sample_phr_data):
        """Test that PHR includes the response text."""
        manager = PHRManager(repo_root=temp_dir)

        result = manager.create_phr(
            title=sample_phr_data['title'],
            stage=sample_phr_data['stage'],
            prompt=sample_phr_data['prompt'],
            response=sample_phr_data['response'],
            feature=sample_phr_data['feature'],
            command=sample_phr_data['command']
        )

        phr_path = Path(result['path'])
        content = phr_path.read_text()

        assert sample_phr_data['response'] in content


class TestPHRValidStages:
    """Test PHR stage validation."""

    @pytest.mark.parametrize("stage", [
        "constitution", "spec", "plan", "tasks",
        "red", "green", "refactor", "explainer", "misc", "general"
    ])
    def test_valid_stages_accepted(self, temp_dir, stage):
        """Test that all valid stages are accepted."""
        manager = PHRManager(repo_root=temp_dir)

        # Should not raise
        result = manager.create_phr(
            title=f"Test {stage}",
            stage=stage,
            prompt="Test prompt",
            response="Test response"
        )

        assert result['stage'] == stage

    def test_invalid_stage_raises_error(self, temp_dir):
        """Test that invalid stage raises error."""
        manager = PHRManager(repo_root=temp_dir)

        with pytest.raises((PHRError, ValueError)):
            manager.create_phr(
                title="Test Invalid",
                stage="invalid_stage",
                prompt="Test",
                response="Test"
            )


class TestConvenienceFunction:
    """Test create_phr convenience function."""

    def test_create_phr_function(self, temp_dir):
        """Test create_phr module-level function."""
        result = create_phr(
            title="Test PHR",
            stage="general",
            prompt="Test prompt",
            response="Test response",
            repo_root=temp_dir
        )

        assert 'id' in result
        assert 'path' in result


class TestPHRError:
    """Test PHRError exception."""

    def test_error_message(self):
        """Test PHRError message."""
        error = PHRError("Test PHR error")
        assert str(error) == "Test PHR error"

    def test_error_inheritance(self):
        """Test that PHRError inherits from Exception."""
        error = PHRError("Test")
        assert isinstance(error, Exception)
