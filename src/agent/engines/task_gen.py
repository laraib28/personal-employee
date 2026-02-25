"""
Task generation engine for SpecKit Agent System.

This module generates dependency-ordered, parallelizable task lists from
implementation plans, organized by user story with exact file paths.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
import re
import yaml
from anthropic import Anthropic
import os

from ..core.renderer import Renderer
from ..core.validation import QualityValidator
from ..core.file_ops import safe_read


class TaskGenerationError(Exception):
    """Raised when task generation fails."""
    pass


class TaskGenerationEngine:
    """
    Generates structured, dependency-ordered task lists.

    Creates tasks organized by user story with parallelization markers,
    dependency graphs, and exact file paths.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        repo_root: Optional[Path] = None,
        model: str = "claude-sonnet-4-5"
    ):
        """
        Initialize the task generation engine.

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
            raise TaskGenerationError(
                "ANTHROPIC_API_KEY not found. Please set it in environment or .env file."
            )

        self.client = Anthropic(api_key=self.api_key)

        # Initialize dependencies
        self.renderer = Renderer()
        self.validator = QualityValidator()

    def generate_tasks(
        self,
        feature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate task list from specification and plan.

        Args:
            feature: Feature name (if None, uses current branch)

        Returns:
            Dictionary with task generation results

        Raises:
            TaskGenerationError: If generation fails
        """
        # Determine feature directory
        if not feature:
            # Try to get from git branch or environment
            from ..core.git_ops import get_current_branch
            try:
                feature = get_current_branch()
            except Exception:
                feature = os.environ.get("SPECIFY_FEATURE")

        if not feature:
            raise TaskGenerationError(
                "Could not determine feature. Please specify --feature or ensure you're on a feature branch."
            )

        feature_dir = self.repo_root / "specs" / feature

        if not feature_dir.exists():
            raise TaskGenerationError(f"Feature directory not found: {feature_dir}")

        # Load artifacts
        print("📖 Loading planning artifacts...")
        spec_file = feature_dir / "spec.md"
        plan_file = feature_dir / "plan.md"
        datamodel_file = feature_dir / "data-model.md"
        contracts_dir = feature_dir / "contracts"

        spec_content = safe_read(spec_file)
        plan_content = safe_read(plan_file)
        datamodel_content = safe_read(datamodel_file)

        if not spec_content or not plan_content:
            raise TaskGenerationError(
                f"Specification or plan not found in {feature_dir}. "
                "Please run 'speckit-agent specify' and 'speckit-agent plan' first."
            )

        # Parse artifacts
        print("🔍 Parsing user stories and requirements...")
        spec_data = self._parse_spec(spec_content)

        print("🔍 Extracting technical stack...")
        plan_data = self._parse_plan(plan_content)

        print("🔍 Loading data model...")
        entities = self._parse_datamodel(datamodel_content) if datamodel_content else []

        print("🔍 Loading contracts...")
        contracts = self._load_contracts(contracts_dir)

        # Generate tasks
        print("📝 Generating setup tasks...")
        setup_tasks = self._generate_setup_tasks(plan_data)

        print("📝 Generating foundational tasks...")
        foundational_tasks = self._generate_foundational_tasks(plan_data)

        print("📝 Generating user story tasks...")
        story_tasks = self._generate_story_tasks(
            spec_data,
            plan_data,
            entities,
            contracts
        )

        # Combine all tasks
        all_tasks = setup_tasks + foundational_tasks + story_tasks

        # Assign sequential IDs
        print("🔢 Assigning task IDs...")
        all_tasks = self._assign_task_ids(all_tasks)

        # Mark parallelizable tasks
        print("⚡ Identifying parallelizable tasks...")
        all_tasks = self._mark_parallelizable(all_tasks)

        # Build dependency graph
        print("📊 Building dependency graph...")
        dep_graph = self._build_dependency_graph(all_tasks)

        # Detect circular dependencies
        print("🔍 Checking for circular dependencies...")
        has_cycles = self._detect_cycles(dep_graph)
        if has_cycles:
            raise TaskGenerationError("Circular dependencies detected in task graph!")

        # Calculate parallel percentage
        print("📊 Calculating parallelization metrics...")
        parallel_pct = self._calculate_parallel_percentage(all_tasks)

        if parallel_pct < 30:
            print(f"⚠️  Warning: Parallel percentage ({parallel_pct:.1f}%) is below 30% target")

        # Generate tasks content
        print("📄 Generating tasks.md...")
        tasks_content = self._generate_tasks_content(
            feature=feature,
            spec_data=spec_data,
            plan_data=plan_data,
            all_tasks=all_tasks,
            dep_graph=dep_graph,
            parallel_pct=parallel_pct
        )

        # Validate tasks
        print("✔️  Validating task list...")
        validation_errors = self._validate_tasks(tasks_content, all_tasks)

        if validation_errors:
            print("⚠️  Task validation warnings:")
            for error in validation_errors:
                print(f"   - {error}")

        print("✅ Task generation complete!")

        return {
            "feature": feature,
            "feature_dir": str(feature_dir),
            "tasks_content": tasks_content,
            "task_count": len(all_tasks),
            "parallel_count": sum(1 for t in all_tasks if t.get("parallelizable")),
            "parallel_percentage": parallel_pct,
            "dependency_graph": dep_graph,
            "validation_errors": validation_errors,
            "user_story_count": len(spec_data["user_stories"])
        }

    def _parse_spec(self, spec_content: str) -> Dict[str, Any]:
        """Parse specification and extract user stories."""
        data = {
            "user_stories": [],
            "functional_requirements": [],
            "success_criteria": []
        }

        # Extract user stories with priorities
        story_pattern = r'### User Story (\d+) - (.+?) \(Priority: (P\d+)\)'
        for match in re.finditer(story_pattern, spec_content):
            data["user_stories"].append({
                "number": int(match.group(1)),
                "title": match.group(2),
                "priority": match.group(3)
            })

        # Extract functional requirements
        fr_pattern = r'\*\*FR-(\d+)\*\*: (.+)'
        for match in re.finditer(fr_pattern, spec_content):
            data["functional_requirements"].append({
                "id": match.group(1),
                "description": match.group(2)
            })

        # Extract success criteria
        sc_pattern = r'\*\*SC-(\d+)\*\*: (.+)'
        for match in re.finditer(sc_pattern, spec_content):
            data["success_criteria"].append({
                "id": match.group(1),
                "description": match.group(2)
            })

        return data

    def _parse_plan(self, plan_content: str) -> Dict[str, Any]:
        """Parse plan and extract technical context."""
        data = {
            "language": None,
            "dependencies": [],
            "storage": None,
            "testing": None,
            "project_structure": {}
        }

        # Extract technical context
        tech_patterns = {
            "language": r'\*\*Language/Version\*\*:\s*(.+)',
            "dependencies": r'\*\*Primary Dependencies\*\*:\s*(.+)',
            "storage": r'\*\*Storage\*\*:\s*(.+)',
            "testing": r'\*\*Testing\*\*:\s*(.+)'
        }

        for key, pattern in tech_patterns.items():
            match = re.search(pattern, plan_content)
            if match:
                value = match.group(1).strip()
                if value not in ["Not specified", "N/A", "NEEDS CLARIFICATION"]:
                    if key == "dependencies":
                        data[key] = [d.strip() for d in value.split(",")]
                    else:
                        data[key] = value

        # Extract project structure from code block
        structure_match = re.search(r'### Source Code.*?```text\n(.+?)\n```', plan_content, re.DOTALL)
        if structure_match:
            data["project_structure"]["source"] = structure_match.group(1)

        return data

    def _parse_datamodel(self, datamodel_content: str) -> List[Dict[str, Any]]:
        """Parse data model and extract entities."""
        entities = []

        # Find entity sections
        entity_pattern = r'### (.+?)\n\n(.+?)(?=\n###|\Z)'
        for match in re.finditer(entity_pattern, datamodel_content, re.DOTALL):
            entities.append({
                "name": match.group(1).strip(),
                "description": match.group(2).strip()
            })

        return entities

    def _load_contracts(self, contracts_dir: Path) -> Dict[str, Any]:
        """Load contract specifications."""
        contracts = {
            "commands": [],
            "formats": {},
            "validation_rules": {}
        }

        # Load CLI commands
        cli_commands_file = contracts_dir / "cli-commands.yaml"
        if cli_commands_file.exists():
            try:
                with open(cli_commands_file, 'r') as f:
                    data = yaml.safe_load(f)
                    contracts["commands"] = data.get("commands", [])
            except Exception:
                pass

        return contracts

    def _generate_setup_tasks(self, plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate Phase 1 setup tasks."""
        tasks = []

        language = plan_data.get("language", "")

        # Project structure task
        tasks.append({
            "description": "Create project directory structure",
            "phase": "setup",
            "files": ["src/", "tests/"],
            "parallelizable": False,
            "dependencies": []
        })

        # Dependencies file
        if "python" in language.lower():
            tasks.append({
                "description": "Create requirements.txt with dependencies",
                "phase": "setup",
                "files": ["requirements.txt"],
                "parallelizable": True,
                "dependencies": []
            })
        elif "node" in language.lower() or "javascript" in language.lower():
            tasks.append({
                "description": "Create package.json with dependencies",
                "phase": "setup",
                "files": ["package.json"],
                "parallelizable": True,
                "dependencies": []
            })

        # Configuration files
        tasks.append({
            "description": "Create configuration files",
            "phase": "setup",
            "files": [".gitignore", "README.md"],
            "parallelizable": True,
            "dependencies": []
        })

        return tasks

    def _generate_foundational_tasks(self, plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate Phase 2 foundational infrastructure tasks."""
        tasks = []

        # Core modules
        core_modules = [
            "config",
            "utils",
            "exceptions",
            "validators"
        ]

        for module in core_modules:
            tasks.append({
                "description": f"Implement {module} module",
                "phase": "foundation",
                "files": [f"src/{module}.py"],
                "parallelizable": True,
                "dependencies": []
            })

        return tasks

    def _generate_story_tasks(
        self,
        spec_data: Dict[str, Any],
        plan_data: Dict[str, Any],
        entities: List[Dict[str, Any]],
        contracts: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate tasks for each user story."""
        tasks = []

        # Sort user stories by priority
        user_stories = sorted(
            spec_data["user_stories"],
            key=lambda s: s["priority"]
        )

        for story in user_stories:
            story_num = story["number"]
            story_title = story["title"]

            # Phase prefix for this story
            phase_name = f"user_story_{story_num}"

            # Models/entities tasks
            story_entities = [e for e in entities if str(story_num) in e.get("description", "")]
            for entity in story_entities:
                tasks.append({
                    "description": f"[US{story_num}] Implement {entity['name']} model",
                    "phase": phase_name,
                    "user_story": story_num,
                    "files": [f"src/models/{entity['name'].lower()}.py"],
                    "parallelizable": True,
                    "dependencies": []
                })

            # Services tasks
            tasks.append({
                "description": f"[US{story_num}] Implement {story_title} service",
                "phase": phase_name,
                "user_story": story_num,
                "files": [f"src/services/{story_title.lower().replace(' ', '_')}_service.py"],
                "parallelizable": False,
                "dependencies": [t["description"] for t in tasks if t.get("user_story") == story_num and "model" in t["description"].lower()]
            })

            # API/CLI endpoint tasks
            tasks.append({
                "description": f"[US{story_num}] Implement {story_title} endpoint",
                "phase": phase_name,
                "user_story": story_num,
                "files": [f"src/api/{story_title.lower().replace(' ', '_')}_endpoint.py"],
                "parallelizable": False,
                "dependencies": [t["description"] for t in tasks if t.get("user_story") == story_num and "service" in t["description"].lower()]
            })

            # Integration tests
            tasks.append({
                "description": f"[US{story_num}] Write integration tests for {story_title}",
                "phase": phase_name,
                "user_story": story_num,
                "files": [f"tests/integration/test_{story_title.lower().replace(' ', '_')}.py"],
                "parallelizable": True,
                "dependencies": [t["description"] for t in tasks if t.get("user_story") == story_num and "endpoint" in t["description"].lower()]
            })

        return tasks

    def _assign_task_ids(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assign sequential task IDs."""
        for i, task in enumerate(tasks, 1):
            task["id"] = f"T{i:03d}"
        return tasks

    def _mark_parallelizable(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mark tasks that can be executed in parallel."""
        # Tasks are already marked during generation
        # This is a validation/refinement pass

        for task in tasks:
            # Tasks with no dependencies and different files can be parallel
            if not task.get("dependencies") and len(task.get("files", [])) > 0:
                task["parallelizable"] = True

        return tasks

    def _build_dependency_graph(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build task dependency graph."""
        graph = {}

        for task in tasks:
            task_id = task["id"]
            dependencies = []

            # Convert dependency descriptions to task IDs
            for dep_desc in task.get("dependencies", []):
                for other_task in tasks:
                    if other_task["description"] == dep_desc:
                        dependencies.append(other_task["id"])

            graph[task_id] = dependencies

        return graph

    def _detect_cycles(self, graph: Dict[str, List[str]]) -> bool:
        """Detect circular dependencies using DFS."""
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    return True

        return False

    def _calculate_parallel_percentage(self, tasks: List[Dict[str, Any]]) -> float:
        """Calculate percentage of parallelizable tasks."""
        if not tasks:
            return 0.0

        parallelizable_count = sum(1 for t in tasks if t.get("parallelizable"))
        return (parallelizable_count / len(tasks)) * 100

    def _generate_tasks_content(
        self,
        feature: str,
        spec_data: Dict[str, Any],
        plan_data: Dict[str, Any],
        all_tasks: List[Dict[str, Any]],
        dep_graph: Dict[str, List[str]],
        parallel_pct: float
    ) -> str:
        """Generate tasks.md content."""
        lines = []

        lines.append(f"# Task List: {feature}")
        lines.append("")
        lines.append(f"**Feature**: {feature}")
        lines.append(f"**Branch**: `{feature}`")
        lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append(f"**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)")
        lines.append("")

        lines.append("## Overview")
        lines.append("")
        lines.append(f"This task list breaks down the implementation into {len(all_tasks)} tasks ")
        lines.append(f"organized by phase. {parallel_pct:.1f}% of tasks can be executed in parallel.")
        lines.append("")
        lines.append(f"**Technology Stack**: {plan_data.get('language', 'Not specified')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Group tasks by phase
        phases = {}
        for task in all_tasks:
            phase = task.get("phase", "other")
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(task)

        # Generate phase sections
        phase_order = ["setup", "foundation"] + [p for p in phases.keys() if p not in ["setup", "foundation"]]

        for phase in phase_order:
            if phase not in phases:
                continue

            phase_tasks = phases[phase]
            phase_title = phase.replace("_", " ").title()

            lines.append(f"## Phase: {phase_title}")
            lines.append("")

            # Add independent test criteria for user story phases
            if phase.startswith("user_story_"):
                story_num = phase.split("_")[-1]
                story = next((s for s in spec_data["user_stories"] if s["number"] == int(story_num)), None)
                if story:
                    lines.append(f"**User Story {story_num}**: {story['title']}")
                    lines.append(f"**Priority**: {story['priority']}")
                    lines.append("")
                    lines.append("**Independent Test**: Verify user story implementation is complete and functional")
                    lines.append("")

            lines.append("**Tasks**:")
            lines.append("")

            for task in phase_tasks:
                parallel_marker = "[P] " if task.get("parallelizable") else ""
                us_marker = f"[US{task['user_story']}] " if task.get("user_story") else ""
                checkbox = "[ ]"

                lines.append(f"- {checkbox} {task['id']} {parallel_marker}{us_marker}{task['description']}")

            lines.append("")
            lines.append("---")
            lines.append("")

        # Dependency graph section
        lines.append("## Dependencies & Execution Order")
        lines.append("")
        lines.append("### Dependency Graph")
        lines.append("")
        lines.append("```text")
        for task_id, dependencies in sorted(dep_graph.items()):
            if dependencies:
                deps_str = ", ".join(dependencies)
                lines.append(f"{task_id} → depends on: {deps_str}")
        lines.append("```")
        lines.append("")

        # Parallelization metrics
        lines.append("### Parallelization Metrics")
        lines.append("")
        lines.append(f"- **Total Tasks**: {len(all_tasks)}")
        lines.append(f"- **Parallelizable Tasks**: {sum(1 for t in all_tasks if t.get('parallelizable'))}")
        lines.append(f"- **Parallel Percentage**: {parallel_pct:.1f}%")
        lines.append("")

        if parallel_pct >= 30:
            lines.append(f"✅ Meets >=30% parallelization target")
        else:
            lines.append(f"⚠️  Below 30% parallelization target")

        lines.append("")

        return "\n".join(lines)

    def _validate_tasks(
        self,
        tasks_content: str,
        all_tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """Validate task list."""
        errors = []

        # Check for TBD or placeholders in file paths
        for task in all_tasks:
            for file_path in task.get("files", []):
                if "TBD" in file_path or "PLACEHOLDER" in file_path:
                    errors.append(f"Task {task['id']} has placeholder file path: {file_path}")

        # Check for required sections
        required_sections = ["Overview", "Dependencies & Execution Order"]
        for section in required_sections:
            if section not in tasks_content:
                errors.append(f"Missing required section: {section}")

        return errors


def generate_tasks(
    feature: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate tasks.

    Args:
        feature: Feature name
        api_key: Optional API key

    Returns:
        Task generation results
    """
    engine = TaskGenerationEngine(api_key=api_key)
    return engine.generate_tasks(feature)
