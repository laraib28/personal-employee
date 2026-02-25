"""
Specification generation engine for SpecKit Agent System.

This module generates feature specifications from natural language descriptions
using the Claude API, with clarification handling and quality validation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import subprocess
import json
import re
import os
from anthropic import Anthropic

from ..core.constitution_guard import ConstitutionGuard
from ..core.clarification import ClarificationManager
from ..core.renderer import Renderer
from ..core.validation import QualityValidator, ValidationResult
from ..core.file_ops import atomic_write, create_validator, validate_no_placeholders


class SpecificationError(Exception):
    """Raised when specification generation fails."""
    pass


class SpecificationEngine:
    """
    Generates feature specifications from natural language descriptions.

    Uses Claude API to parse descriptions, extract requirements, and generate
    structured specifications with constitutional compliance and quality validation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        repo_root: Optional[Path] = None,
        model: str = "claude-sonnet-4-5"
    ):
        """
        Initialize the specification engine.

        Args:
            api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)
            repo_root: Repository root path
            model: Claude model to use
        """
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.model = model

        # Initialize Anthropic client
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise SpecificationError(
                "ANTHROPIC_API_KEY not found. Please set it in environment or .env file."
            )

        self.client = Anthropic(api_key=self.api_key)

        # Initialize dependencies
        self.constitution_guard = ConstitutionGuard()
        self.clarification_manager = ClarificationManager(self.constitution_guard)
        self.renderer = Renderer()
        self.validator = QualityValidator()

        # Script path
        self.create_feature_script = (
            self.repo_root / ".specify" / "scripts" / "bash" / "create-new-feature.sh"
        )

    def generate_specification(
        self,
        feature_description: str,
        short_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete feature specification from description.

        Args:
            feature_description: Natural language feature description
            short_name: Optional short name for the feature

        Returns:
            Dictionary with specification results including paths and validation

        Raises:
            SpecificationError: If generation fails
        """
        # Step 1: Parse feature description and extract key concepts
        print("📝 Analyzing feature description...")
        parsed_data = self._parse_feature_description(feature_description)

        # Step 2: Generate short name and slug if not provided
        if not short_name:
            short_name = parsed_data.get("short_name")

        print(f"📌 Feature name: {short_name}")

        # Step 3: Identify ambiguous requirements
        print("🔍 Checking for ambiguities...")
        ambiguities = self._identify_ambiguities(parsed_data)

        # Step 4: Ask clarification questions one at a time (max 3)
        clarifications = {}
        if ambiguities:
            print(f"❓ Found {len(ambiguities)} area(s) needing clarification")
            clarifications = self._ask_clarifications(ambiguities[:3])  # Max 3
            print("✅ Clarifications received")

        # Step 5: Update spec content with clarification answers
        if clarifications:
            parsed_data = self._integrate_clarifications(parsed_data, clarifications)

        # Step 6: Call create-new-feature.sh to initialize branch and spec file
        print(f"🌿 Creating feature branch and directory structure...")
        feature_info = self._create_feature_structure(feature_description, short_name)

        branch_name = feature_info["BRANCH_NAME"]
        spec_file = Path(feature_info["SPEC_FILE"])

        print(f"✅ Branch created: {branch_name}")

        # Step 7: Fill spec template with extracted data
        print("📄 Generating specification document...")
        spec_content = self._generate_spec_content(
            feature_description=feature_description,
            branch_name=branch_name,
            parsed_data=parsed_data
        )

        # Step 8: Validate generated spec
        print("✔️  Validating specification quality...")
        is_valid, validation_results = self.validator.validate_document(
            spec_content,
            "specification"
        )

        if not is_valid:
            print("⚠️  Warning: Specification has validation issues")
            for result in validation_results:
                if not result.passed:
                    print(f"   - {result.message}")

        # Step 9: Write spec.md atomically
        print(f"💾 Writing specification to {spec_file}...")
        atomic_write(
            spec_file,
            spec_content,
            validator=create_validator(validate_no_placeholders)
        )

        print("✅ Specification generated successfully!")

        return {
            "branch_name": branch_name,
            "spec_file": str(spec_file),
            "feature_num": feature_info["FEATURE_NUM"],
            "short_name": short_name,
            "validation_passed": is_valid,
            "validation_results": validation_results,
            "clarifications": clarifications,
            "parsed_data": parsed_data
        }

    def _parse_feature_description(self, description: str) -> Dict[str, Any]:
        """Parse feature description and extract key concepts using Claude API."""
        prompt = f"""Analyze this feature description and extract structured information:

"{description}"

Extract and return a JSON object with:
1. "short_name": A 2-4 word concise name for the feature (e.g., "user-authentication", "payment-integration")
2. "feature_type": The type of feature (e.g., "new feature", "enhancement", "bug fix", "refactoring")
3. "user_stories": List of 2-5 user stories, each with:
   - "title": Brief title
   - "description": Plain language description
   - "priority": P1 (critical), P2 (important), P3 (nice-to-have)
   - "why_priority": Rationale for priority
   - "independent_test": How it can be tested independently
   - "scenarios": List of Given-When-Then acceptance scenarios
4. "functional_requirements": List of 5-10 functional requirements (FR-001, FR-002, etc.)
5. "key_entities": List of main data entities involved (if applicable)
6. "success_criteria": List of 3-5 measurable success criteria (SC-001, SC-002, etc.)
7. "edge_cases": List of 2-5 edge cases to consider

Return ONLY valid JSON, no other text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)

            parsed_data = json.loads(response_text)
            return parsed_data

        except json.JSONDecodeError as e:
            raise SpecificationError(f"Failed to parse Claude response as JSON: {e}")
        except Exception as e:
            raise SpecificationError(f"Failed to parse feature description: {e}")

    def _identify_ambiguities(self, parsed_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Identify ambiguous or unclear requirements that need clarification."""
        ambiguities = []

        # Check for missing or vague information
        user_stories = parsed_data.get("user_stories", [])
        functional_requirements = parsed_data.get("functional_requirements", [])

        # Check if technical context is needed
        if len(functional_requirements) > 0:
            # Ask about technology preferences
            ambiguities.append({
                "id": "tech_stack",
                "question": "What technology stack or programming language should be used for this feature? (e.g., Python, Node.js, React, etc.)",
                "context": {"reason": "Technical implementation approach not specified"}
            })

        # Check if data storage is needed
        key_entities = parsed_data.get("key_entities", [])
        if len(key_entities) > 0:
            ambiguities.append({
                "id": "data_storage",
                "question": "What type of data storage should be used? (e.g., SQL database, NoSQL, file system, in-memory)",
                "context": {"reason": "Data persistence strategy not specified"}
            })

        # Check for authentication/authorization requirements
        has_auth = any(
            "auth" in req.lower() or "login" in req.lower() or "user" in req.lower()
            for req in functional_requirements
        )
        if has_auth:
            ambiguities.append({
                "id": "auth_method",
                "question": "What authentication method should be used? (e.g., JWT tokens, sessions, OAuth, basic auth)",
                "context": {"reason": "Authentication method not specified"}
            })

        return ambiguities

    def _ask_clarifications(
        self,
        ambiguities: List[Dict[str, str]]
    ) -> Dict[str, str]:
        """Ask clarification questions one at a time."""
        clarifications = {}

        for ambiguity in ambiguities:
            try:
                answer = self.clarification_manager.ask_question(
                    question=ambiguity["question"],
                    question_id=ambiguity["id"],
                    context=ambiguity.get("context")
                )
                clarifications[ambiguity["id"]] = answer

            except Exception as e:
                # Log error but continue with other clarifications
                print(f"⚠️  Warning: Failed to get clarification for {ambiguity['id']}: {e}")
                clarifications[ambiguity["id"]] = "Not specified"

        return clarifications

    def _integrate_clarifications(
        self,
        parsed_data: Dict[str, Any],
        clarifications: Dict[str, str]
    ) -> Dict[str, Any]:
        """Integrate clarification answers into parsed data."""
        # Store clarifications in metadata
        if "metadata" not in parsed_data:
            parsed_data["metadata"] = {}

        parsed_data["metadata"]["clarifications"] = clarifications

        # Update specific fields based on clarifications
        if "tech_stack" in clarifications:
            parsed_data["metadata"]["technology"] = clarifications["tech_stack"]

        if "data_storage" in clarifications:
            parsed_data["metadata"]["storage"] = clarifications["data_storage"]

        if "auth_method" in clarifications:
            parsed_data["metadata"]["authentication"] = clarifications["auth_method"]

        return parsed_data

    def _create_feature_structure(
        self,
        description: str,
        short_name: Optional[str]
    ) -> Dict[str, str]:
        """Call create-new-feature.sh script to initialize branch and spec file."""
        if not self.create_feature_script.exists():
            raise SpecificationError(
                f"create-new-feature.sh script not found at {self.create_feature_script}"
            )

        # Build command
        cmd = [str(self.create_feature_script), "--json"]

        if short_name:
            cmd.extend(["--short-name", short_name])

        cmd.append(description)

        # Execute script
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root
            )

            # Parse JSON output
            feature_info = json.loads(result.stdout.strip())
            return feature_info

        except subprocess.CalledProcessError as e:
            raise SpecificationError(f"Failed to create feature structure: {e.stderr}")
        except json.JSONDecodeError as e:
            raise SpecificationError(f"Failed to parse create-new-feature.sh output: {e}")

    def _generate_spec_content(
        self,
        feature_description: str,
        branch_name: str,
        parsed_data: Dict[str, Any]
    ) -> str:
        """Generate specification content from parsed data."""
        from datetime import datetime

        # Build spec content manually (template has placeholders we need to fill)
        lines = []
        lines.append(f"# Feature Specification: {parsed_data.get('short_name', 'Feature')}")
        lines.append("")
        lines.append(f"**Feature Branch**: `{branch_name}`")
        lines.append(f"**Created**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"**Status**: Draft")
        lines.append(f"**Input**: User description: \"{feature_description}\"")
        lines.append("")

        # Add metadata section if clarifications exist
        metadata = parsed_data.get("metadata", {})
        if metadata.get("clarifications"):
            lines.append("## Technical Context")
            lines.append("")
            for key, value in metadata.items():
                if key != "clarifications":
                    lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            lines.append("")

        # User Stories section
        lines.append("## User Scenarios & Testing")
        lines.append("")

        user_stories = parsed_data.get("user_stories", [])
        for i, story in enumerate(user_stories, 1):
            lines.append(f"### User Story {i} - {story.get('title', 'Story')} (Priority: {story.get('priority', 'P3')})")
            lines.append("")
            lines.append(story.get("description", ""))
            lines.append("")
            lines.append(f"**Why this priority**: {story.get('why_priority', 'Value delivery')}")
            lines.append("")
            lines.append(f"**Independent Test**: {story.get('independent_test', 'Can be tested independently')}")
            lines.append("")
            lines.append("**Acceptance Scenarios**:")
            lines.append("")

            scenarios = story.get("scenarios", [])
            for j, scenario in enumerate(scenarios, 1):
                lines.append(f"{j}. **Given** {scenario.get('given', '[state]')}, **When** {scenario.get('when', '[action]')}, **Then** {scenario.get('then', '[outcome]')}")

            lines.append("")
            lines.append("---")
            lines.append("")

        # Edge Cases
        lines.append("### Edge Cases")
        lines.append("")
        edge_cases = parsed_data.get("edge_cases", [])
        for edge_case in edge_cases:
            lines.append(f"- {edge_case}")
        lines.append("")

        # Requirements section
        lines.append("## Requirements")
        lines.append("")
        lines.append("### Functional Requirements")
        lines.append("")

        functional_requirements = parsed_data.get("functional_requirements", [])
        for i, req in enumerate(functional_requirements, 1):
            lines.append(f"- **FR-{i:03d}**: {req}")

        lines.append("")

        # Key Entities (if applicable)
        key_entities = parsed_data.get("key_entities", [])
        if key_entities:
            lines.append("### Key Entities")
            lines.append("")
            for entity in key_entities:
                if isinstance(entity, dict):
                    name = entity.get("name", "Entity")
                    description = entity.get("description", "")
                    lines.append(f"- **{name}**: {description}")
                else:
                    lines.append(f"- **{entity}**: Data entity")
            lines.append("")

        # Success Criteria
        lines.append("## Success Criteria")
        lines.append("")
        lines.append("### Measurable Outcomes")
        lines.append("")

        success_criteria = parsed_data.get("success_criteria", [])
        for i, criterion in enumerate(success_criteria, 1):
            lines.append(f"- **SC-{i:03d}**: {criterion}")

        lines.append("")

        return "\n".join(lines)


def generate_specification(
    feature_description: str,
    short_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate a specification.

    Args:
        feature_description: Feature description
        short_name: Optional short name
        api_key: Optional API key

    Returns:
        Specification generation results
    """
    engine = SpecificationEngine(api_key=api_key)
    return engine.generate_specification(feature_description, short_name)
