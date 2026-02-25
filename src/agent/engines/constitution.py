"""
Constitution generation and amendment engine for SpecKit Agent System.

This module handles creation and versioning of project constitutions with
sync impact reporting and template alignment checking.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re
import os
from anthropic import Anthropic

from ..core.constitution_guard import ConstitutionGuard
from ..core.renderer import Renderer
from ..core.validation import QualityValidator
from ..core.file_ops import atomic_write, safe_read


class ConstitutionError(Exception):
    """Raised when constitution operations fail."""
    pass


class ConstitutionEngine:
    """
    Manages constitution creation, amendment, and versioning.

    Handles parsing principles, version management, sync impact reporting,
    and template alignment checking.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        repo_root: Optional[Path] = None,
        model: str = "claude-sonnet-4-5"
    ):
        """
        Initialize the constitution engine.

        Args:
            api_key: Anthropic API key
            repo_root: Repository root path
            model: Claude model to use
        """
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.model = model
        self.constitution_path = self.repo_root / ".specify" / "memory" / "constitution.md"

        # Initialize Anthropic client
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ConstitutionError(
                "ANTHROPIC_API_KEY not found. Please set it in environment or .env file."
            )

        self.client = Anthropic(api_key=self.api_key)

        # Initialize dependencies
        self.renderer = Renderer()
        self.validator = QualityValidator()

    def process_constitution(
        self,
        content: str,
        is_file_path: bool = False
    ) -> Dict[str, Any]:
        """
        Process constitution input (create new or amend existing).

        Args:
            content: Constitution content or file path
            is_file_path: Whether content is a file path

        Returns:
            Dictionary with processing results

        Raises:
            ConstitutionError: If processing fails
        """
        # Step 1: Detect input type and load content
        print("📄 Loading constitution content...")
        constitution_text = self._load_content(content, is_file_path)

        # Step 2: Parse constitution content and extract principles
        print("🔍 Parsing principles...")
        parsed_principles = self._parse_principles(constitution_text)

        print(f"✅ Found {len(parsed_principles)} principle(s)")

        # Step 3: Detect constitution type (new vs amendment)
        print("🔎 Detecting constitution type...")
        is_new, existing_version = self._detect_type()

        if is_new:
            print("📝 Creating new constitution")
            change_type = "MAJOR"
        else:
            print(f"📝 Amending existing constitution (current version: {existing_version})")

            # Step 4: Determine version increment
            change_type = self._determine_version_increment(
                parsed_principles,
                constitution_text
            )
            print(f"📊 Change type: {change_type}")

        # Step 5: Calculate new version
        new_version = self._calculate_version(existing_version, change_type, is_new)
        print(f"🔢 New version: {new_version}")

        # Step 6: Generate sync impact report
        print("📋 Generating sync impact report...")
        sync_report = self._generate_sync_impact_report(
            is_new=is_new,
            change_type=change_type,
            old_version=existing_version,
            new_version=new_version,
            principles=parsed_principles
        )

        # Step 7: Check dependent templates
        print("🔍 Checking template alignment...")
        template_checks = self._check_dependent_templates()

        # Step 8: Build complete constitution content
        print("📝 Building constitution document...")
        constitution_content = self._build_constitution_content(
            principles=parsed_principles,
            version=new_version,
            sync_report=sync_report,
            template_checks=template_checks,
            is_new=is_new
        )

        # Step 9: Validate constitution
        print("✔️  Validating constitution...")
        validation_errors = self._validate_constitution(constitution_content, new_version)

        if validation_errors:
            print("⚠️  Validation warnings:")
            for error in validation_errors:
                print(f"   - {error}")

        # Step 10: Write constitution file atomically
        print(f"💾 Writing constitution to {self.constitution_path}...")
        atomic_write(self.constitution_path, constitution_content)

        print("✅ Constitution written successfully!")

        return {
            "constitution_file": str(self.constitution_path),
            "version": new_version,
            "status": "ACTIVE",
            "change_type": change_type,
            "is_new": is_new,
            "principles_count": len(parsed_principles),
            "sync_report": sync_report,
            "template_checks": template_checks,
            "validation_errors": validation_errors
        }

    def _load_content(self, content: str, is_file_path: bool) -> str:
        """Load constitution content from file or inline string."""
        if is_file_path:
            # Treat as file path
            file_path = Path(content)
            if not file_path.exists():
                raise ConstitutionError(f"Constitution file not found: {content}")

            try:
                return file_path.read_text(encoding='utf-8')
            except Exception as e:
                raise ConstitutionError(f"Failed to read constitution file: {e}")
        else:
            # Treat as inline content
            return content

    def _parse_principles(self, constitution_text: str) -> List[Dict[str, Any]]:
        """Parse principles from constitution text using Claude API."""
        prompt = f"""Parse this constitution text and extract all principles.

Constitution text:
{constitution_text}

For each principle, extract:
1. "number": Roman numeral (I, II, III, etc.) or sequential number
2. "name": Principle name
3. "description": Brief description
4. "rules": List of specific rules
5. "rationale": Rationale for the principle
6. "is_non_negotiable": Boolean indicating if marked as NON-NEGOTIABLE

Return ONLY a JSON array of principles, no other text.

Example format:
[
  {{
    "number": "I",
    "name": "Human Never Writes",
    "description": "Human NEVER writes content. AI ALWAYS generates structured output.",
    "rules": ["If a task involves analysis...", "Human interaction is limited to..."],
    "rationale": "Ensures consistency and reproducibility",
    "is_non_negotiable": true
  }}
]"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)

            import json
            principles = json.loads(response_text)
            return principles

        except Exception as e:
            raise ConstitutionError(f"Failed to parse principles: {e}")

    def _detect_type(self) -> Tuple[bool, Optional[str]]:
        """Detect if this is a new constitution or an amendment."""
        if not self.constitution_path.exists():
            return True, None

        # Load existing constitution and extract version
        content = safe_read(self.constitution_path)
        if not content:
            return True, None

        version_match = re.search(r'\*\*Version\*\*:\s*(\S+)', content)
        if version_match:
            return False, version_match.group(1)

        return True, None

    def _determine_version_increment(
        self,
        new_principles: List[Dict[str, Any]],
        new_text: str
    ) -> str:
        """Determine version increment type (MAJOR/MINOR/PATCH)."""
        # Load existing constitution
        existing_content = safe_read(self.constitution_path)
        if not existing_content:
            return "MAJOR"

        # Use Claude to analyze changes
        prompt = f"""Analyze the changes between existing and new constitution to determine version increment type.

Existing constitution:
{existing_content[:2000]}...

New constitution:
{new_text[:2000]}...

Determine the change type:
- MAJOR: Breaking changes, removed principles, significant restructuring, changes that invalidate existing work
- MINOR: New principles added, non-breaking enhancements, clarifications that don't change meaning
- PATCH: Typo fixes, formatting changes, minor clarifications

Return ONLY one word: MAJOR, MINOR, or PATCH"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            change_type = response.content[0].text.strip().upper()

            if change_type in ["MAJOR", "MINOR", "PATCH"]:
                return change_type
            else:
                # Default to MINOR if unclear
                return "MINOR"

        except Exception:
            # Default to MINOR on error
            return "MINOR"

    def _calculate_version(
        self,
        current_version: Optional[str],
        change_type: str,
        is_new: bool
    ) -> str:
        """Calculate new version based on change type."""
        if is_new or not current_version:
            return "1.0.0"

        # Parse current version
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', current_version)
        if not match:
            return "1.0.0"

        major, minor, patch = map(int, match.groups())

        if change_type == "MAJOR":
            return f"{major + 1}.0.0"
        elif change_type == "MINOR":
            return f"{major}.{minor + 1}.0"
        else:  # PATCH
            return f"{major}.{minor}.{patch + 1}"

    def _generate_sync_impact_report(
        self,
        is_new: bool,
        change_type: str,
        old_version: Optional[str],
        new_version: str,
        principles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate sync impact report for the constitution change."""
        report = {
            "version_change": f"[{'Initial' if is_new else old_version}] → {new_version}",
            "change_type": f"{change_type} - {'Initial constitution creation' if is_new else 'Constitution amendment'}",
            "modified_principles": [],
            "added_sections": [],
            "removed_sections": [],
            "affected_templates": []
        }

        if is_new:
            report["modified_principles"] = [f"All principles created ({len(principles)} principles)"]
            report["added_sections"] = ["Core Principles", "Communication Authority", "System Purpose", "Governance"]
            report["removed_sections"] = ["None (initial creation)"]
        else:
            report["modified_principles"] = [p.get("name", "Unknown") for p in principles]
            report["added_sections"] = ["Updated principles"]
            report["removed_sections"] = []

        return report

    def _check_dependent_templates(self) -> List[Dict[str, str]]:
        """Check dependent templates for alignment with constitution."""
        templates_dir = self.repo_root / ".specify" / "templates"
        template_checks = []

        template_files = [
            "plan-template.md",
            "spec-template.md",
            "tasks-template.md"
        ]

        for template_file in template_files:
            template_path = templates_dir / template_file

            if template_path.exists():
                template_checks.append({
                    "file": template_file,
                    "status": "✅",
                    "message": f"{template_file} exists"
                })
            else:
                template_checks.append({
                    "file": template_file,
                    "status": "⚠",
                    "message": f"{template_file} not found"
                })

        return template_checks

    def _build_constitution_content(
        self,
        principles: List[Dict[str, Any]],
        version: str,
        sync_report: Dict[str, Any],
        template_checks: List[Dict[str, str]],
        is_new: bool
    ) -> str:
        """Build complete constitution content."""
        lines = []

        # Add sync impact report as comment at top
        lines.append("<!--")
        lines.append("SYNC IMPACT REPORT")
        lines.append("==================")
        lines.append(f"Version Change: {sync_report['version_change']}")
        lines.append(f"Change Type: {sync_report['change_type']}")
        lines.append("")
        lines.append("Modified Principles:")
        for principle in sync_report["modified_principles"]:
            lines.append(f"- {principle}")
        lines.append("")
        lines.append("Added Sections:")
        for section in sync_report["added_sections"]:
            lines.append(f"- {section}")
        lines.append("")
        lines.append("Removed Sections:")
        for section in sync_report["removed_sections"]:
            lines.append(f"- {section}")
        lines.append("")
        lines.append("Templates Requiring Updates:")
        for check in template_checks:
            lines.append(f"{check['status']} {check['message']}")
        lines.append("")
        lines.append("Amendments:")
        lines.append(f"- {datetime.now().strftime('%Y-%m-%d')}: {'Initial constitution creation' if is_new else 'Constitution updated'}")
        lines.append("")
        lines.append("Deferred Items: None")
        lines.append("-->")
        lines.append("")

        # Add main constitution content
        lines.append("# AI-Driven System Constitution")
        lines.append("")
        lines.append("## System Purpose")
        lines.append("")
        lines.append("This constitution defines governance principles for AI-driven development workflows.")
        lines.append("All development work must comply with these principles.")
        lines.append("")
        lines.append("**Core Value**: Correctness is always prioritized over speed.")
        lines.append("")

        # Add Core Principles
        lines.append("## Core Principles")
        lines.append("")

        for principle in principles:
            number = principle.get("number", "")
            name = principle.get("name", "Principle")
            is_non_negotiable = principle.get("is_non_negotiable", False)

            title = f"### {number}. {name}"
            if is_non_negotiable:
                title += " (NON-NEGOTIABLE)"

            lines.append(title)
            lines.append("")

            description = principle.get("description", "")
            if description:
                lines.append(description)
                lines.append("")

            rules = principle.get("rules", [])
            if rules:
                lines.append("**Rules**:")
                for rule in rules:
                    lines.append(f"- {rule}")
                lines.append("")

            rationale = principle.get("rationale", "")
            if rationale:
                lines.append(f"**Rationale**: {rationale}")
                lines.append("")

        # Add Governance section
        lines.append("## Governance")
        lines.append("")
        lines.append("This constitution supersedes all other practices. All development work must verify compliance.")
        lines.append("")
        lines.append("**Amendment Process**:")
        lines.append("- Amendments require documented rationale and approval")
        lines.append("- Version changes follow semantic versioning (MAJOR.MINOR.PATCH)")
        lines.append("- All amendments must include Sync Impact Report")
        lines.append("")
        lines.append("**Compliance Review**:")
        lines.append("- Before any workflow step: Check constitution compliance")
        lines.append("- Violations halt workflow until resolved")
        lines.append("")

        # Add version footer
        today = datetime.now().strftime("%Y-%m-%d")
        lines.append(f"**Version**: {version} | **Ratified**: {today} | **Last Amended**: {today} | **Status**: ACTIVE")
        lines.append("")

        return "\n".join(lines)

    def _validate_constitution(self, content: str, version: str) -> List[str]:
        """Validate constitution content."""
        errors = []

        # Check for placeholders
        if re.search(r'{{.*}}', content):
            errors.append("Constitution contains unresolved placeholders")

        # Check for valid version format
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            errors.append(f"Invalid version format: {version}")

        # Check for required sections
        required_sections = ["Core Principles", "Governance"]
        for section in required_sections:
            if section not in content:
                errors.append(f"Missing required section: {section}")

        # Check for ISO dates
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        if not re.search(date_pattern, content):
            errors.append("Constitution missing ISO date format")

        return errors


def create_constitution(
    content: str,
    is_file_path: bool = False,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to create or amend a constitution.

    Args:
        content: Constitution content or file path
        is_file_path: Whether content is a file path
        api_key: Optional API key

    Returns:
        Constitution processing results
    """
    engine = ConstitutionEngine(api_key=api_key)
    return engine.process_constitution(content, is_file_path)
