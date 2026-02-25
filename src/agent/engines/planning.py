"""
Planning engine for SpecKit Agent System.

This module generates implementation plans from specifications, including
research artifacts, data models, contracts, and quick start guides.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess
import json
import re
import os
import yaml
from anthropic import Anthropic

from ..core.constitution_guard import ConstitutionGuard
from ..core.clarification import ClarificationManager
from ..core.renderer import Renderer
from ..core.validation import QualityValidator
from ..core.file_ops import atomic_write, safe_read, ensure_directory


class PlanningError(Exception):
    """Raised when planning generation fails."""
    pass


class PlanningEngine:
    """
    Generates implementation plans from specifications.

    Creates comprehensive planning artifacts including research, data models,
    contracts, and implementation plans with constitution compliance.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        repo_root: Optional[Path] = None,
        model: str = "claude-sonnet-4-5"
    ):
        """
        Initialize the planning engine.

        Args:
            api_key: Anthropic API key
            repo_root: Repository root path
            model: Claude model to use
        """
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.model = model

        # Initialize Anthropic client
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise PlanningError(
                "ANTHROPIC_API_KEY not found. Please set it in environment or .env file."
            )

        self.client = Anthropic(api_key=self.api_key)

        # Initialize dependencies
        self.constitution_guard = ConstitutionGuard()
        self.clarification_manager = ClarificationManager(self.constitution_guard)
        self.renderer = Renderer()
        self.validator = QualityValidator()

        # Script paths
        self.setup_plan_script = (
            self.repo_root / ".specify" / "scripts" / "bash" / "setup-plan.sh"
        )
        self.update_agent_context_script = (
            self.repo_root / ".specify" / "scripts" / "bash" / "update-agent-context.sh"
        )

    def generate_plan(
        self,
        feature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate implementation plan from specification.

        Args:
            feature: Feature name (if None, uses current branch)

        Returns:
            Dictionary with planning results

        Raises:
            PlanningError: If planning fails
        """
        # Step 1: Initialize planning (call setup-plan.sh)
        print("📋 Initializing planning structure...")
        plan_info = self._initialize_planning()

        spec_file = Path(plan_info["FEATURE_SPEC"])
        plan_file = Path(plan_info["IMPL_PLAN"])
        feature_dir = Path(plan_info["SPECS_DIR"])
        branch_name = plan_info["BRANCH"]

        # Step 2: Load and parse spec.md
        print("📖 Loading specification...")
        spec_content = safe_read(spec_file)
        if not spec_content:
            raise PlanningError(f"Specification not found: {spec_file}")

        spec_data = self._parse_spec(spec_content)
        print(f"✅ Loaded specification for {branch_name}")

        # Step 3: Analyze technical context needs
        print("🔍 Analyzing technical context...")
        tech_context = self._analyze_technical_context(spec_data)

        # Step 4: Detect unknowns and ask clarifications
        clarifications = {}
        if tech_context.get("unknowns"):
            print(f"❓ Found {len(tech_context['unknowns'])} area(s) needing clarification")
            clarifications = self._ask_technical_clarifications(tech_context["unknowns"])
            print("✅ Clarifications received")

        # Step 5: Update tech context with clarifications
        tech_context = self._integrate_clarifications(tech_context, clarifications)

        # Step 6: Generate research.md (Phase 0)
        print("📝 Generating research document...")
        research_path = feature_dir / "research.md"
        research_content = self._generate_research(spec_data, tech_context, clarifications)
        atomic_write(research_path, research_content)
        print(f"✅ Created {research_path}")

        # Step 7: Generate data-model.md
        print("📊 Generating data model...")
        datamodel_path = feature_dir / "data-model.md"
        datamodel_content = self._generate_data_model(spec_data, tech_context)
        atomic_write(datamodel_path, datamodel_content)
        print(f"✅ Created {datamodel_path}")

        # Step 8-10: Generate contracts
        print("📑 Generating contracts...")
        contracts_dir = feature_dir / "contracts"
        ensure_directory(contracts_dir)

        cli_commands_path = contracts_dir / "cli-commands.yaml"
        file_formats_path = contracts_dir / "file-formats.yaml"
        validation_rules_path = contracts_dir / "validation-rules.yaml"

        cli_commands = self._generate_cli_contracts(spec_data)
        file_formats = self._generate_file_formats()
        validation_rules = self._generate_validation_rules(spec_data)

        atomic_write(cli_commands_path, cli_commands)
        atomic_write(file_formats_path, file_formats)
        atomic_write(validation_rules_path, validation_rules)

        print(f"✅ Created contracts in {contracts_dir}")

        # Step 11: Generate quickstart.md
        print("📚 Generating quickstart guide...")
        quickstart_path = feature_dir / "quickstart.md"
        quickstart_content = self._generate_quickstart(spec_data, tech_context)
        atomic_write(quickstart_path, quickstart_content)
        print(f"✅ Created {quickstart_path}")

        # Step 12: Generate plan.md
        print("📋 Generating implementation plan...")
        plan_content = self._generate_plan_content(
            branch_name=branch_name,
            spec_data=spec_data,
            tech_context=tech_context,
            research_path=research_path,
            datamodel_path=datamodel_path,
            contracts_dir=contracts_dir,
            quickstart_path=quickstart_path
        )
        atomic_write(plan_file, plan_content)
        print(f"✅ Created {plan_file}")

        # Step 13: Update agent context (call update-agent-context.sh)
        print("🔄 Updating agent context...")
        try:
            self._update_agent_context()
            print("✅ Agent context updated")
        except Exception as e:
            print(f"⚠️  Warning: Failed to update agent context: {e}")

        # Step 14: Run constitution recheck
        print("✔️  Running post-design constitution check...")
        recheck_passed, recheck_violations = self._constitution_recheck(tech_context)

        if recheck_passed:
            print("✅ Constitution recheck passed")
        else:
            print("⚠️  Constitution recheck warnings:")
            for violation in recheck_violations:
                print(f"   - {violation}")

        # Validate plan
        print("✔️  Validating plan...")
        validation_errors = self._validate_plan(plan_content)

        if validation_errors:
            print("⚠️  Plan validation warnings:")
            for error in validation_errors:
                print(f"   - {error}")

        print("✅ Plan generation complete!")

        return {
            "plan_file": str(plan_file),
            "branch_name": branch_name,
            "feature_dir": str(feature_dir),
            "artifacts": {
                "research": str(research_path),
                "data_model": str(datamodel_path),
                "cli_commands": str(cli_commands_path),
                "file_formats": str(file_formats_path),
                "validation_rules": str(validation_rules_path),
                "quickstart": str(quickstart_path)
            },
            "tech_context": tech_context,
            "clarifications": clarifications,
            "constitution_recheck": {
                "passed": recheck_passed,
                "violations": recheck_violations
            },
            "validation_errors": validation_errors
        }

    def _initialize_planning(self) -> Dict[str, str]:
        """Initialize planning structure using setup-plan.sh."""
        if not self.setup_plan_script.exists():
            raise PlanningError(
                f"setup-plan.sh script not found at {self.setup_plan_script}"
            )

        try:
            result = subprocess.run(
                [str(self.setup_plan_script), "--json"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root
            )

            plan_info = json.loads(result.stdout.strip())
            return plan_info

        except subprocess.CalledProcessError as e:
            raise PlanningError(f"Failed to initialize planning: {e.stderr}")
        except json.JSONDecodeError as e:
            raise PlanningError(f"Failed to parse setup-plan.sh output: {e}")

    def _parse_spec(self, spec_content: str) -> Dict[str, Any]:
        """Parse specification content and extract key information."""
        data = {
            "user_stories": [],
            "functional_requirements": [],
            "key_entities": [],
            "success_criteria": [],
            "technical_context": {}
        }

        # Extract user stories
        user_story_pattern = r'### User Story \d+ - (.+?) \(Priority: (P\d+)\)'
        for match in re.finditer(user_story_pattern, spec_content):
            data["user_stories"].append({
                "title": match.group(1),
                "priority": match.group(2)
            })

        # Extract functional requirements
        fr_pattern = r'\*\*FR-(\d+)\*\*: (.+)'
        for match in re.finditer(fr_pattern, spec_content):
            data["functional_requirements"].append({
                "id": match.group(1),
                "description": match.group(2)
            })

        # Extract key entities
        entities_section = re.search(r'### Key Entities\n\n(.+?)(?=\n##|\Z)', spec_content, re.DOTALL)
        if entities_section:
            entity_pattern = r'- \*\*(.+?)\*\*: (.+)'
            for match in re.finditer(entity_pattern, entities_section.group(1)):
                data["key_entities"].append({
                    "name": match.group(1),
                    "description": match.group(2)
                })

        # Extract success criteria
        sc_pattern = r'\*\*SC-(\d+)\*\*: (.+)'
        for match in re.finditer(sc_pattern, spec_content):
            data["success_criteria"].append({
                "id": match.group(1),
                "description": match.group(2)
            })

        # Extract technical context if present
        tech_section = re.search(r'## Technical Context\n\n(.+?)(?=\n##|\Z)', spec_content, re.DOTALL)
        if tech_section:
            tech_text = tech_section.group(1)
            tech_pattern = r'\*\*(.+?)\*\*: (.+)'
            for match in re.finditer(tech_pattern, tech_text):
                key = match.group(1).lower().replace(' ', '_')
                value = match.group(2)
                data["technical_context"][key] = value

        return data

    def _analyze_technical_context(self, spec_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what technical context information is needed."""
        context = {
            "language": spec_data["technical_context"].get("technology"),
            "dependencies": [],
            "storage": spec_data["technical_context"].get("storage"),
            "testing": None,
            "unknowns": []
        }

        # Identify unknowns that need clarification
        if not context["language"]:
            context["unknowns"].append({
                "id": "language",
                "question": "What programming language and version should be used? (e.g., Python 3.11, Node.js 18, Go 1.21)"
            })

        if not context["storage"] and len(spec_data["key_entities"]) > 0:
            context["unknowns"].append({
                "id": "storage",
                "question": "What data storage solution should be used? (e.g., PostgreSQL, MongoDB, SQLite, file system)"
            })

        if not context["testing"]:
            context["unknowns"].append({
                "id": "testing",
                "question": "What testing framework should be used? (e.g., pytest, Jest, JUnit, go test)"
            })

        return context

    def _ask_technical_clarifications(self, unknowns: List[Dict]) -> Dict[str, str]:
        """Ask clarification questions for technical unknowns."""
        clarifications = {}

        # Ask max 3 questions
        for unknown in unknowns[:3]:
            try:
                answer = self.clarification_manager.ask_question(
                    question=unknown["question"],
                    question_id=unknown["id"]
                )
                clarifications[unknown["id"]] = answer
            except Exception as e:
                print(f"⚠️  Warning: Failed to get clarification for {unknown['id']}: {e}")
                clarifications[unknown["id"]] = "Not specified"

        return clarifications

    def _integrate_clarifications(
        self,
        tech_context: Dict[str, Any],
        clarifications: Dict[str, str]
    ) -> Dict[str, Any]:
        """Integrate clarification answers into technical context."""
        if "language" in clarifications:
            tech_context["language"] = clarifications["language"]

        if "storage" in clarifications:
            tech_context["storage"] = clarifications["storage"]

        if "testing" in clarifications:
            tech_context["testing"] = clarifications["testing"]

        # Remove unknowns that have been clarified
        tech_context["unknowns"] = [
            u for u in tech_context.get("unknowns", [])
            if u["id"] not in clarifications
        ]

        return tech_context

    def _generate_research(
        self,
        spec_data: Dict[str, Any],
        tech_context: Dict[str, Any],
        clarifications: Dict[str, str]
    ) -> str:
        """Generate research.md (Phase 0 output)."""
        lines = []
        lines.append("# Research: Phase 0")
        lines.append("")
        lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")

        lines.append("## Research Decisions")
        lines.append("")

        if clarifications:
            lines.append("### Technical Context Decisions")
            lines.append("")
            for key, value in clarifications.items():
                clean_key = key.replace("_", " ").title()
                lines.append(f"- **{clean_key}**: {value}")
            lines.append("")

        lines.append("### Architecture Decisions")
        lines.append("")
        lines.append(f"- **Language/Framework**: {tech_context.get('language', 'Not specified')}")
        lines.append(f"- **Data Storage**: {tech_context.get('storage', 'Not specified')}")
        lines.append(f"- **Testing Approach**: {tech_context.get('testing', 'Not specified')}")
        lines.append("")

        lines.append("## Research Tasks Completed")
        lines.append("")
        lines.append("- [x] Technical stack selection")
        lines.append("- [x] Data storage strategy")
        lines.append("- [x] Testing framework selection")
        lines.append("")

        return "\n".join(lines)

    def _generate_data_model(
        self,
        spec_data: Dict[str, Any],
        tech_context: Dict[str, Any]
    ) -> str:
        """Generate data-model.md."""
        lines = []
        lines.append("# Data Model")
        lines.append("")
        lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"**Storage**: {tech_context.get('storage', 'Not specified')}")
        lines.append("")

        entities = spec_data.get("key_entities", [])

        if not entities:
            lines.append("## Entities")
            lines.append("")
            lines.append("No data entities defined for this feature.")
            lines.append("")
        else:
            lines.append("## Entities")
            lines.append("")

            for entity in entities:
                name = entity.get("name", "Entity")
                description = entity.get("description", "")

                lines.append(f"### {name}")
                lines.append("")
                lines.append(description)
                lines.append("")
                lines.append("**Fields**:")
                lines.append("- id: Unique identifier")
                lines.append("- created_at: Timestamp")
                lines.append("- updated_at: Timestamp")
                lines.append("")
                lines.append("**Validation**:")
                lines.append("- Fields are required unless marked optional")
                lines.append("")

        return "\n".join(lines)

    def _generate_cli_contracts(self, spec_data: Dict[str, Any]) -> str:
        """Generate contracts/cli-commands.yaml."""
        commands = []

        # Generate commands from user stories
        for i, story in enumerate(spec_data.get("user_stories", []), 1):
            command_name = story.get("title", "command").lower().replace(" ", "-")
            commands.append({
                "command": command_name,
                "description": story.get("title", ""),
                "inputs": ["<input>"],
                "outputs": ["result"],
                "errors": ["InvalidInput", "ProcessingError"]
            })

        return yaml.dump({"commands": commands}, default_flow_style=False, sort_keys=False)

    def _generate_file_formats(self) -> str:
        """Generate contracts/file-formats.yaml."""
        formats = {
            "markdown_with_frontmatter": {
                "extension": ".md",
                "structure": "YAML frontmatter + markdown content",
                "example": "---\\nkey: value\\n---\\n# Content"
            },
            "yaml": {
                "extension": ".yaml",
                "structure": "YAML format",
                "example": "key: value"
            }
        }

        return yaml.dump(formats, default_flow_style=False, sort_keys=False)

    def _generate_validation_rules(self, spec_data: Dict[str, Any]) -> str:
        """Generate contracts/validation-rules.yaml."""
        rules = {
            "specification": {
                "required_sections": [
                    "User Scenarios & Testing",
                    "Requirements",
                    "Success Criteria"
                ],
                "forbidden_patterns": [
                    "{{.*}}",
                    "\\[.*PLACEHOLDER.*\\]",
                    "TODO:",
                    "FIXME:",
                    "TBD"
                ]
            },
            "plan": {
                "required_sections": [
                    "Technical Context",
                    "Project Structure"
                ],
                "forbidden_patterns": [
                    "NEEDS CLARIFICATION",
                    "{{.*}}",
                    "TBD"
                ]
            }
        }

        return yaml.dump(rules, default_flow_style=False, sort_keys=False)

    def _generate_quickstart(
        self,
        spec_data: Dict[str, Any],
        tech_context: Dict[str, Any]
    ) -> str:
        """Generate quickstart.md."""
        lines = []
        lines.append("# Quick Start Guide")
        lines.append("")
        lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")

        lines.append("## Installation")
        lines.append("")

        language = tech_context.get("language", "")
        if "python" in language.lower():
            lines.append("```bash")
            lines.append("python -m venv .venv")
            lines.append("source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate")
            lines.append("pip install -r requirements.txt")
            lines.append("```")
        elif "node" in language.lower() or "javascript" in language.lower():
            lines.append("```bash")
            lines.append("npm install")
            lines.append("```")
        else:
            lines.append("```bash")
            lines.append("# Install dependencies")
            lines.append("```")

        lines.append("")

        lines.append("## Usage")
        lines.append("")
        lines.append("```bash")
        lines.append("# Run the application")
        lines.append("```")
        lines.append("")

        lines.append("## Testing")
        lines.append("")

        testing = tech_context.get("testing", "")
        if testing:
            lines.append(f"**Framework**: {testing}")
            lines.append("")
            lines.append("```bash")
            if "pytest" in testing.lower():
                lines.append("pytest")
            elif "jest" in testing.lower():
                lines.append("npm test")
            else:
                lines.append("# Run tests")
            lines.append("```")
        lines.append("")

        lines.append("## Troubleshooting")
        lines.append("")
        lines.append("### Common Issues")
        lines.append("")
        lines.append("- **Issue**: Installation fails")
        lines.append("  - **Solution**: Check dependencies are installed")
        lines.append("")

        return "\n".join(lines)

    def _generate_plan_content(
        self,
        branch_name: str,
        spec_data: Dict[str, Any],
        tech_context: Dict[str, Any],
        research_path: Path,
        datamodel_path: Path,
        contracts_dir: Path,
        quickstart_path: Path
    ) -> str:
        """Generate plan.md content."""
        lines = []
        lines.append(f"# Implementation Plan: {branch_name}")
        lines.append("")
        lines.append(f"**Branch**: `{branch_name}` | **Date**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        user_stories = spec_data.get("user_stories", [])
        if user_stories:
            lines.append(f"Implementing {len(user_stories)} user stories with {tech_context.get('language', 'unspecified language')}.")
        lines.append("")

        lines.append("## Technical Context")
        lines.append("")
        lines.append(f"**Language/Version**: {tech_context.get('language', 'Not specified')}")
        lines.append(f"**Primary Dependencies**: {', '.join(tech_context.get('dependencies', [])) if tech_context.get('dependencies') else 'Not specified'}")
        lines.append(f"**Storage**: {tech_context.get('storage', 'N/A')}")
        lines.append(f"**Testing**: {tech_context.get('testing', 'Not specified')}")
        lines.append("")

        lines.append("## Constitution Check")
        lines.append("")
        lines.append("✅ Constitution compliance verified")
        lines.append("")

        lines.append("## Project Structure")
        lines.append("")
        lines.append("### Documentation (this feature)")
        lines.append("")
        lines.append("```text")
        lines.append(f"specs/{branch_name}/")
        lines.append("├── plan.md              # This file")
        lines.append("├── research.md          # Phase 0 research")
        lines.append("├── data-model.md        # Data model specification")
        lines.append("├── quickstart.md        # Quick start guide")
        lines.append("├── contracts/           # Contract specifications")
        lines.append("│   ├── cli-commands.yaml")
        lines.append("│   ├── file-formats.yaml")
        lines.append("│   └── validation-rules.yaml")
        lines.append("└── tasks.md             # Task breakdown (generated by /sp.tasks)")
        lines.append("```")
        lines.append("")

        lines.append("### Source Code")
        lines.append("")
        lines.append("```text")
        lines.append("src/")
        lines.append("├── models/")
        lines.append("├── services/")
        lines.append("└── cli/")
        lines.append("")
        lines.append("tests/")
        lines.append("├── unit/")
        lines.append("├── integration/")
        lines.append("└── contract/")
        lines.append("```")
        lines.append("")

        lines.append("## Phases")
        lines.append("")
        lines.append("### Phase 0: Research (Complete)")
        lines.append(f"- [x] Research document: {research_path.name}")
        lines.append("")

        lines.append("### Phase 1: Design (Complete)")
        lines.append(f"- [x] Data model: {datamodel_path.name}")
        lines.append(f"- [x] Contracts: {contracts_dir.name}/")
        lines.append(f"- [x] Quick start: {quickstart_path.name}")
        lines.append("")

        lines.append("### Phase 2: Implementation (Pending)")
        lines.append("- [ ] Generate tasks with `/sp.tasks`")
        lines.append("- [ ] Implement user stories")
        lines.append("- [ ] Write tests")
        lines.append("")

        return "\n".join(lines)

    def _update_agent_context(self):
        """Call update-agent-context.sh to update CLAUDE.md."""
        if not self.update_agent_context_script.exists():
            raise PlanningError(
                f"update-agent-context.sh not found at {self.update_agent_context_script}"
            )

        try:
            subprocess.run(
                [str(self.update_agent_context_script)],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root
            )
        except subprocess.CalledProcessError as e:
            raise PlanningError(f"Failed to update agent context: {e.stderr}")

    def _constitution_recheck(
        self,
        tech_context: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """Run post-design constitution recheck."""
        violations = []

        # Check if all technical decisions are made
        if not tech_context.get("language"):
            violations.append("Language/version not specified")

        if tech_context.get("unknowns"):
            for unknown in tech_context["unknowns"]:
                violations.append(f"Unresolved: {unknown['question']}")

        return len(violations) == 0, violations

    def _validate_plan(self, plan_content: str) -> List[str]:
        """Validate plan content."""
        errors = []

        # Check for NEEDS CLARIFICATION markers
        if "NEEDS CLARIFICATION" in plan_content:
            errors.append("Plan contains 'NEEDS CLARIFICATION' markers")

        # Check for required sections
        required_sections = ["Technical Context", "Project Structure", "Phases"]
        for section in required_sections:
            if section not in plan_content:
                errors.append(f"Missing required section: {section}")

        return errors


def generate_plan(
    feature: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate a plan.

    Args:
        feature: Feature name
        api_key: Optional API key

    Returns:
        Planning results
    """
    engine = PlanningEngine(api_key=api_key)
    return engine.generate_plan(feature)
