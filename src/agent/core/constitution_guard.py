"""
Constitution compliance enforcement for SpecKit Agent System.

This module loads and validates compliance with the project constitution,
ensuring all workflows respect constitutional principles.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


class ConstitutionError(Exception):
    """Raised when a constitution violation is detected."""
    pass


class ConstitutionGuard:
    """
    Enforces constitution compliance for all agent operations.

    Loads constitution from .specify/memory/constitution.md and provides
    validation functions to check operations against constitutional principles.
    """

    def __init__(self, constitution_path: Optional[Path] = None):
        """
        Initialize the constitution guard.

        Args:
            constitution_path: Path to constitution.md. If None, uses default location.
        """
        if constitution_path is None:
            constitution_path = Path.cwd() / ".specify" / "memory" / "constitution.md"

        self.constitution_path = Path(constitution_path)
        self.constitution_content: Optional[str] = None
        self.version: Optional[str] = None
        self.status: Optional[str] = None
        self.principles: Dict[str, Dict[str, any]] = {}

        if self.constitution_path.exists():
            self._load_constitution()

    def _load_constitution(self) -> None:
        """Load and parse the constitution file."""
        self.constitution_content = self.constitution_path.read_text(encoding="utf-8")

        # Extract version and status from footer
        version_match = re.search(r'\*\*Version\*\*:\s*(\S+)', self.constitution_content)
        status_match = re.search(r'\*\*Status\*\*:\s*(\S+)', self.constitution_content)

        self.version = version_match.group(1) if version_match else None
        self.status = status_match.group(1) if status_match else None

        # Parse principles
        self._parse_principles()

    def _parse_principles(self) -> None:
        """Parse constitution principles from the content."""
        if not self.constitution_content:
            return

        # Extract principle sections (### I. through ### X.)
        principle_pattern = r'###\s+([IVX]+)\.\s+(.+?)\n\n(.+?)(?=\n###|\Z)'
        matches = re.finditer(principle_pattern, self.constitution_content, re.DOTALL)

        for match in matches:
            number = match.group(1)
            name = match.group(2).strip()
            content = match.group(3).strip()

            # Extract rules
            rules = []
            rules_section = re.search(r'\*\*Rules?\*\*:(.+?)(?=\*\*|\Z)', content, re.DOTALL)
            if rules_section:
                rules_text = rules_section.group(1)
                # Extract bullet points
                rules = [
                    line.strip().lstrip('-').strip()
                    for line in rules_text.split('\n')
                    if line.strip().startswith('-')
                ]

            # Extract rationale
            rationale = None
            rationale_section = re.search(r'\*\*Rationale\*\*:\s*(.+?)(?=\n\n|\Z)', content, re.DOTALL)
            if rationale_section:
                rationale = rationale_section.group(1).strip()

            self.principles[number] = {
                "name": name,
                "content": content,
                "rules": rules,
                "rationale": rationale,
                "is_non_negotiable": "(NON-NEGOTIABLE)" in name
            }

    def is_active(self) -> bool:
        """Check if the constitution is active."""
        return self.status == "ACTIVE"

    def get_version(self) -> Optional[str]:
        """Get the constitution version."""
        return self.version

    def get_principle(self, identifier: str) -> Optional[Dict]:
        """
        Get a specific principle by Roman numeral identifier.

        Args:
            identifier: Roman numeral (I, II, III, etc.)

        Returns:
            Dictionary containing principle details, or None if not found.
        """
        return self.principles.get(identifier)

    def check_compliance(
        self,
        operation: str,
        context: Optional[Dict] = None
    ) -> Tuple[bool, List[str]]:
        """
        Check if an operation complies with constitutional principles.

        Args:
            operation: The operation being performed (e.g., "ask_question", "generate_spec")
            context: Additional context for validation (e.g., question_count, workflow_step)

        Returns:
            Tuple of (is_compliant, list_of_violations)
        """
        if not self.is_active():
            return False, ["Constitution is not active"]

        violations = []
        context = context or {}

        # Check Principle IV: One Question at a Time
        if operation == "ask_question":
            question_count = context.get("question_count", 1)
            if question_count > 1:
                violations.append(
                    "Violation of Principle IV (One Question at a Time): "
                    f"Attempted to ask {question_count} questions, but only 1 is allowed"
                )

        # Check Principle V: Mandatory Development Flow
        if operation == "workflow_step":
            expected_step = context.get("expected_step")
            actual_step = context.get("actual_step")
            if expected_step and actual_step and expected_step != actual_step:
                violations.append(
                    "Violation of Principle V (Mandatory Development Flow): "
                    f"Expected step '{expected_step}', but got '{actual_step}'"
                )

        # Check Principle VI: No-Vibe Coding
        if operation == "generate_code":
            has_rationale = context.get("has_rationale", False)
            if not has_rationale:
                violations.append(
                    "Violation of Principle VI (No-Vibe Coding): "
                    "Code generation without documented rationale"
                )

        # Check Communication Authority
        if operation == "send_message":
            has_approval = context.get("has_approval", False)
            if not has_approval:
                violations.append(
                    "Violation of Communication Authority: "
                    "Attempted to send message without explicit human approval"
                )

        # Check Principle I: Human Never Writes
        if operation == "request_manual_work":
            violations.append(
                "Violation of Principle I (Human Never Writes): "
                "AI requested manual work from human"
            )

        return len(violations) == 0, violations

    def enforce_compliance(
        self,
        operation: str,
        context: Optional[Dict] = None
    ) -> None:
        """
        Enforce compliance by raising an exception if violations are detected.

        Args:
            operation: The operation being performed
            context: Additional context for validation

        Raises:
            ConstitutionError: If compliance check fails
        """
        is_compliant, violations = self.check_compliance(operation, context)

        if not is_compliant:
            violation_text = "\n".join(f"  - {v}" for v in violations)
            raise ConstitutionError(
                f"Constitution compliance check failed:\n{violation_text}\n\n"
                "System must halt and revert to last valid state per Principle X."
            )

    def get_mandatory_flow_steps(self) -> List[str]:
        """Get the list of mandatory development flow steps."""
        return [
            "intent_clarification",
            "problem_definition",
            "vision_statement",
            "functional_requirements",
            "non_functional_requirements",
            "constraints_assumptions",
            "architecture_design",
            "task_decomposition",
            "implementation",
            "validation_testing",
            "iteration_improvement"
        ]

    def validate_workflow_order(
        self,
        completed_steps: List[str],
        next_step: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that workflow steps are executed in the correct order.

        Args:
            completed_steps: List of steps already completed
            next_step: The next step to be executed

        Returns:
            Tuple of (is_valid, error_message)
        """
        mandatory_steps = self.get_mandatory_flow_steps()

        # Find the expected next step
        expected_index = len(completed_steps)

        if expected_index >= len(mandatory_steps):
            return False, "All mandatory steps have been completed"

        expected_step = mandatory_steps[expected_index]

        if next_step != expected_step:
            return False, (
                f"Invalid workflow order. Expected '{expected_step}' "
                f"but got '{next_step}'. "
                f"Completed steps: {completed_steps}"
            )

        return True, None


def load_constitution(constitution_path: Optional[Path] = None) -> ConstitutionGuard:
    """
    Load the constitution and return a guard instance.

    Args:
        constitution_path: Optional path to constitution file

    Returns:
        ConstitutionGuard instance
    """
    return ConstitutionGuard(constitution_path)


def check_compliance(
    operation: str,
    context: Optional[Dict] = None,
    constitution_path: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """
    Convenience function to check compliance without creating a guard instance.

    Args:
        operation: The operation being performed
        context: Additional context for validation
        constitution_path: Optional path to constitution file

    Returns:
        Tuple of (is_compliant, list_of_violations)
    """
    guard = ConstitutionGuard(constitution_path)
    return guard.check_compliance(operation, context)
