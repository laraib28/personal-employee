"""
Quality validation engine for SpecKit Agent System.

This module provides markdown document validation against quality rules
defined in contracts/validation-rules.yaml.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import re
import yaml
from markdown_it import MarkdownIt


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, passed: bool, message: str = "", rule: Optional[str] = None):
        self.passed = passed
        self.message = message
        self.rule = rule

    def __bool__(self) -> bool:
        return self.passed

    def __repr__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        rule_text = f" [{self.rule}]" if self.rule else ""
        return f"{status}{rule_text}: {self.message}"


class QualityValidator:
    """
    Validates documents against quality rules.

    Parses markdown documents and validates them against rules defined
    in validation-rules.yaml, checking for required sections, forbidden
    patterns, and structural requirements.
    """

    def __init__(self, rules_file: Optional[Path] = None):
        """
        Initialize the quality validator.

        Args:
            rules_file: Path to validation-rules.yaml. If None, uses default location.
        """
        if rules_file is None:
            rules_file = Path.cwd() / "specs" / "001-ai-agent-system" / "contracts" / "validation-rules.yaml"

        self.rules_file = Path(rules_file)
        self.rules: Dict[str, Any] = {}
        self.md_parser = MarkdownIt()

        # Load rules if file exists
        if self.rules_file.exists():
            self._load_rules()
        else:
            # Use default rules if file doesn't exist
            self._load_default_rules()

    def _load_rules(self) -> None:
        """Load validation rules from YAML file."""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                self.rules = yaml.safe_load(f) or {}
        except Exception as e:
            raise ValidationError(f"Failed to load validation rules: {e}")

    def _load_default_rules(self) -> None:
        """Load default validation rules."""
        self.rules = {
            "specification": {
                "required_sections": [
                    "Problem Statement",
                    "User Stories",
                    "Success Criteria"
                ],
                "forbidden_patterns": [
                    r"{{.*}}",
                    r"\[.*PLACEHOLDER.*\]",
                    r"TODO:",
                    r"FIXME:",
                    r"TBD"
                ]
            },
            "plan": {
                "required_sections": [
                    "Technical Context",
                    "Project Structure"
                ],
                "forbidden_patterns": [
                    r"NEEDS CLARIFICATION",
                    r"{{.*}}",
                    r"TBD"
                ]
            },
            "tasks": {
                "required_sections": [
                    "Phase",
                    "Dependencies"
                ],
                "forbidden_patterns": [
                    r"{{.*}}",
                    r"TBD"
                ]
            },
            "constitution": {
                "required_sections": [
                    "Core Principles",
                    "Governance"
                ],
                "forbidden_patterns": [
                    r"{{.*}}",
                    r"TBD"
                ]
            }
        }

    def validate_document(
        self,
        content: str,
        document_type: str
    ) -> Tuple[bool, List[ValidationResult]]:
        """
        Validate a document against quality rules.

        Args:
            content: Document content
            document_type: Type of document (specification, plan, tasks, constitution)

        Returns:
            Tuple of (all_passed, list_of_validation_results)
        """
        results = []

        # Get rules for this document type
        doc_rules = self.rules.get(document_type, {})

        if not doc_rules:
            results.append(ValidationResult(
                passed=False,
                message=f"No validation rules found for document type: {document_type}"
            ))
            return False, results

        # Check required sections
        if "required_sections" in doc_rules:
            section_results = self._check_required_sections(
                content,
                doc_rules["required_sections"]
            )
            results.extend(section_results)

        # Check forbidden patterns
        if "forbidden_patterns" in doc_rules:
            pattern_results = self._check_forbidden_patterns(
                content,
                doc_rules["forbidden_patterns"]
            )
            results.extend(pattern_results)

        # Check for YAML frontmatter
        frontmatter_result = self._check_frontmatter(content)
        results.append(frontmatter_result)

        # Check markdown structure
        structure_result = self._check_markdown_structure(content)
        results.append(structure_result)

        # Determine overall pass/fail
        all_passed = all(r.passed for r in results)

        return all_passed, results

    def _check_required_sections(
        self,
        content: str,
        required_sections: List[str]
    ) -> List[ValidationResult]:
        """Check that all required sections are present."""
        results = []

        # Extract headings from content
        headings = self._extract_headings(content)

        for required_section in required_sections:
            # Check if section exists (case-insensitive partial match)
            found = any(
                required_section.lower() in heading.lower()
                for heading in headings
            )

            if found:
                results.append(ValidationResult(
                    passed=True,
                    message=f"Required section found: {required_section}",
                    rule="required_sections"
                ))
            else:
                results.append(ValidationResult(
                    passed=False,
                    message=f"Missing required section: {required_section}",
                    rule="required_sections"
                ))

        return results

    def _check_forbidden_patterns(
        self,
        content: str,
        forbidden_patterns: List[str]
    ) -> List[ValidationResult]:
        """Check that no forbidden patterns are present."""
        results = []

        for pattern in forbidden_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)

            if matches:
                # Show first few matches
                sample = ", ".join(matches[:3])
                if len(matches) > 3:
                    sample += f"... ({len(matches) - 3} more)"

                results.append(ValidationResult(
                    passed=False,
                    message=f"Forbidden pattern found: {pattern} (examples: {sample})",
                    rule="forbidden_patterns"
                ))
            else:
                results.append(ValidationResult(
                    passed=True,
                    message=f"No forbidden pattern: {pattern}",
                    rule="forbidden_patterns"
                ))

        return results

    def _check_frontmatter(self, content: str) -> ValidationResult:
        """Check that document has valid YAML frontmatter."""
        if not content.strip():
            return ValidationResult(
                passed=False,
                message="Document is empty",
                rule="frontmatter"
            )

        if not content.startswith('---\n'):
            return ValidationResult(
                passed=False,
                message="Missing YAML frontmatter (should start with ---)",
                rule="frontmatter"
            )

        # Find closing delimiter
        parts = content.split('---\n', 2)
        if len(parts) < 3:
            return ValidationResult(
                passed=False,
                message="Incomplete YAML frontmatter (missing closing ---)",
                rule="frontmatter"
            )

        # Try to parse frontmatter
        frontmatter = parts[1]
        try:
            yaml.safe_load(frontmatter)
            return ValidationResult(
                passed=True,
                message="Valid YAML frontmatter",
                rule="frontmatter"
            )
        except yaml.YAMLError as e:
            return ValidationResult(
                passed=False,
                message=f"Invalid YAML frontmatter: {e}",
                rule="frontmatter"
            )

    def _check_markdown_structure(self, content: str) -> ValidationResult:
        """Check that document has valid markdown structure."""
        # Should have at least one heading
        if not re.search(r'^#+\s+.+$', content, re.MULTILINE):
            return ValidationResult(
                passed=False,
                message="Document has no headings",
                rule="markdown_structure"
            )

        # Should have some content beyond headings
        non_heading_lines = [
            line for line in content.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]

        if len(non_heading_lines) < 5:
            return ValidationResult(
                passed=False,
                message="Document has insufficient content",
                rule="markdown_structure"
            )

        return ValidationResult(
            passed=True,
            message="Valid markdown structure",
            rule="markdown_structure"
        )

    def _extract_headings(self, content: str) -> List[str]:
        """Extract all headings from markdown content."""
        headings = []

        # Parse markdown
        tokens = self.md_parser.parse(content)

        # Extract heading tokens
        for token in tokens:
            if token.type == 'heading_open':
                # Get the next token which contains the text
                idx = tokens.index(token)
                if idx + 1 < len(tokens):
                    text_token = tokens[idx + 1]
                    if text_token.type == 'inline' and text_token.content:
                        headings.append(text_token.content)

        # Fallback: regex extraction if parser doesn't work well
        if not headings:
            heading_pattern = r'^#+\s+(.+)$'
            headings = re.findall(heading_pattern, content, re.MULTILINE)

        return headings

    def generate_report(
        self,
        results: List[ValidationResult],
        verbose: bool = False
    ) -> str:
        """
        Generate a human-readable validation report.

        Args:
            results: List of validation results
            verbose: If True, include passing checks; if False, only failures

        Returns:
            Formatted report string
        """
        if not results:
            return "No validation checks performed"

        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]

        lines = []
        lines.append("=" * 70)
        lines.append("VALIDATION REPORT")
        lines.append("=" * 70)
        lines.append(f"Total checks: {len(results)}")
        lines.append(f"Passed: {len(passed)}")
        lines.append(f"Failed: {len(failed)}")
        lines.append("")

        if failed:
            lines.append("FAILURES:")
            lines.append("-" * 70)
            for result in failed:
                lines.append(f"  {result}")
            lines.append("")

        if verbose and passed:
            lines.append("PASSED:")
            lines.append("-" * 70)
            for result in passed:
                lines.append(f"  {result}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


def validate_document(
    content: str,
    document_type: str,
    rules_file: Optional[Path] = None
) -> Tuple[bool, List[ValidationResult]]:
    """
    Convenience function to validate a document.

    Args:
        content: Document content
        document_type: Document type
        rules_file: Optional path to rules file

    Returns:
        Tuple of (all_passed, validation_results)
    """
    validator = QualityValidator(rules_file)
    return validator.validate_document(content, document_type)
