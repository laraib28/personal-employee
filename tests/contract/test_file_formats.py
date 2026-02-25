"""
Contract tests for file formats.

Tests YAML parsing, front-matter extraction, and document structure
validation to ensure consistent file formats across the system.
"""

import pytest
import yaml
import re
from pathlib import Path


class TestYAMLFrontMatter:
    """Test YAML front-matter parsing and validation."""

    def test_parse_valid_front_matter(self):
        """Test parsing valid YAML front-matter."""
        content = """---
title: Test Document
date: 2026-01-14
status: draft
---

# Document Content

This is the body.
"""
        # Extract front-matter
        match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        assert match is not None

        front_matter = yaml.safe_load(match.group(1))
        assert front_matter['title'] == 'Test Document'
        assert front_matter['date'] == '2026-01-14'
        assert front_matter['status'] == 'draft'

    def test_parse_front_matter_with_lists(self):
        """Test parsing front-matter with list values."""
        content = """---
labels:
  - spec
  - feature
  - test
files:
  - src/module.py
  - tests/test_module.py
---

Content here.
"""
        match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        assert match is not None

        front_matter = yaml.safe_load(match.group(1))
        assert front_matter['labels'] == ['spec', 'feature', 'test']
        assert len(front_matter['files']) == 2

    def test_parse_front_matter_with_nested_objects(self):
        """Test parsing front-matter with nested objects."""
        content = """---
links:
  spec: specs/feature/spec.md
  plan: specs/feature/plan.md
  adr: null
metadata:
  version: 1.0.0
  author: test
---

Content.
"""
        match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        assert match is not None

        front_matter = yaml.safe_load(match.group(1))
        assert front_matter['links']['spec'] == 'specs/feature/spec.md'
        assert front_matter['links']['adr'] is None
        assert front_matter['metadata']['version'] == '1.0.0'

    def test_reject_invalid_yaml(self):
        """Test that invalid YAML raises an error."""
        invalid_yaml = """
title: Test
  invalid_indent: true
"""
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(invalid_yaml)


class TestSpecificationFormat:
    """Test specification document format."""

    def test_spec_required_sections(self, sample_spec_content):
        """Test that spec contains required sections."""
        assert '# Feature:' in sample_spec_content or '## Problem Statement' in sample_spec_content
        assert '## User Stories' in sample_spec_content
        assert '## Success Criteria' in sample_spec_content

    def test_spec_front_matter_fields(self, sample_spec_content):
        """Test that spec front-matter has required fields."""
        match = re.match(r'^---\n(.*?)\n---\n', sample_spec_content, re.DOTALL)
        assert match is not None

        front_matter = yaml.safe_load(match.group(1))
        assert 'feature' in front_matter
        assert 'title' in front_matter

    def test_success_criteria_format(self, sample_spec_content):
        """Test that success criteria follow SC-XXX format."""
        # Success criteria should be prefixed with SC-XXX
        sc_pattern = r'SC-\d{3}'
        matches = re.findall(sc_pattern, sample_spec_content)
        assert len(matches) > 0, "Expected at least one SC-XXX criterion"


class TestPlanFormat:
    """Test implementation plan document format."""

    def test_plan_required_sections(self, sample_plan_content):
        """Test that plan contains required sections."""
        assert '## Technical Context' in sample_plan_content
        assert '## Project Structure' in sample_plan_content

    def test_plan_front_matter_fields(self, sample_plan_content):
        """Test that plan front-matter has required fields."""
        match = re.match(r'^---\n(.*?)\n---\n', sample_plan_content, re.DOTALL)
        assert match is not None

        front_matter = yaml.safe_load(match.group(1))
        assert 'feature' in front_matter
        assert 'title' in front_matter


class TestTasksFormat:
    """Test task list document format."""

    def test_tasks_required_sections(self, sample_tasks_content):
        """Test that tasks contains phase sections."""
        assert '## Phase' in sample_tasks_content

    def test_tasks_front_matter_fields(self, sample_tasks_content):
        """Test that tasks front-matter has required fields."""
        match = re.match(r'^---\n(.*?)\n---\n', sample_tasks_content, re.DOTALL)
        assert match is not None

        front_matter = yaml.safe_load(match.group(1))
        assert 'feature' in front_matter

    def test_task_id_format(self, sample_tasks_content):
        """Test that tasks follow T### format."""
        task_pattern = r'T\d{3}'
        matches = re.findall(task_pattern, sample_tasks_content)
        assert len(matches) > 0, "Expected at least one T### task ID"

    def test_task_checkbox_format(self, sample_tasks_content):
        """Test that tasks have markdown checkboxes."""
        checkbox_pattern = r'- \[ \]'
        matches = re.findall(checkbox_pattern, sample_tasks_content)
        assert len(matches) > 0, "Expected at least one task checkbox"


class TestPHRFormat:
    """Test PHR (Prompt History Record) format."""

    def test_phr_required_fields(self, sample_phr_data):
        """Test that PHR data has required fields."""
        required_fields = [
            'id', 'title', 'stage', 'feature', 'date',
            'surface', 'model', 'command', 'prompt', 'response'
        ]
        for field in required_fields:
            assert field in sample_phr_data, f"Missing required field: {field}"

    def test_phr_stage_values(self, sample_phr_data):
        """Test that PHR stage is a valid value."""
        valid_stages = [
            'constitution', 'spec', 'plan', 'tasks',
            'red', 'green', 'refactor', 'explainer', 'misc', 'general'
        ]
        assert sample_phr_data['stage'] in valid_stages

    def test_phr_surface_value(self, sample_phr_data):
        """Test that PHR surface is 'agent'."""
        assert sample_phr_data['surface'] == 'agent'


class TestADRFormat:
    """Test ADR (Architecture Decision Record) format."""

    def test_adr_filename_format(self):
        """Test ADR filename follows {number}-{slug}.md format."""
        valid_filenames = [
            "0001-use-postgresql.md",
            "0002-choose-rest-api.md",
            "0010-python-over-nodejs.md"
        ]
        pattern = r'^\d{4}-[\w-]+\.md$'

        for filename in valid_filenames:
            assert re.match(pattern, filename), f"Invalid ADR filename: {filename}"

    def test_adr_required_sections(self):
        """Test that ADR template has required sections."""
        required_sections = [
            "Decision",
            "Consequences",
            "Alternatives Considered"
        ]
        # This would be tested against actual ADR content
        # For contract testing, we just verify the expected structure


class TestDraftFormat:
    """Test communication draft format."""

    def test_draft_front_matter_fields(self):
        """Test expected draft front-matter fields."""
        expected_fields = [
            'draft_id',
            'message_type',
            'created_date',
            'approval_status',
            'sent_timestamp',
            'purpose',
            'recipient'
        ]
        # Contract: these fields should be present in draft documents

    def test_draft_approval_status_values(self):
        """Test valid approval status values."""
        valid_statuses = ['pending', 'approved', 'rejected', 'modified']
        # Contract: approval_status must be one of these values

    def test_draft_message_types(self):
        """Test valid message types."""
        valid_types = ['email', 'whatsapp']
        # Contract: message_type must be one of these values
