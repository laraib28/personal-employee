"""
Workflow state management and orchestration for SpecKit Agent System.

This module tracks workflow state in .specify/state.yaml and validates
that prerequisites are met before each workflow step.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import yaml


class WorkflowError(Exception):
    """Raised when workflow prerequisites are not met."""
    pass


class WorkflowOrchestrator:
    """
    Manages workflow state and validates workflow prerequisites.

    Tracks current workflow state in .specify/state.yaml and ensures
    that each step has required prerequisites before execution.
    """

    # Workflow step dependencies
    STEP_PREREQUISITES = {
        "specify": [],  # No prerequisites
        "constitution": [],  # No prerequisites
        "plan": ["specify"],  # Requires spec to exist
        "tasks": ["specify", "plan"],  # Requires both spec and plan
        "implement": ["specify", "plan", "tasks"],  # Requires all planning artifacts
    }

    def __init__(self, state_file_path: Optional[Path] = None):
        """
        Initialize the workflow orchestrator.

        Args:
            state_file_path: Path to state.yaml. If None, uses default location.
        """
        if state_file_path is None:
            state_file_path = Path.cwd() / ".specify" / "state.yaml"

        self.state_file_path = Path(state_file_path)
        self.state: Dict[str, Any] = {}

        # Create parent directory if it doesn't exist
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state if file exists
        if self.state_file_path.exists():
            self._load_state()
        else:
            self._initialize_state()

    def _load_state(self) -> None:
        """Load workflow state from file."""
        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                self.state = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise WorkflowError(f"Failed to load workflow state: {e}")

    def _save_state(self) -> None:
        """Save workflow state to file."""
        try:
            with open(self.state_file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.state, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise WorkflowError(f"Failed to save workflow state: {e}")

    def _initialize_state(self) -> None:
        """Initialize a new workflow state."""
        self.state = {
            "initialized": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "last_step": None,
            "features": {},
            "current_feature": None,
        }
        self._save_state()

    def update_state(
        self,
        step: str,
        feature: Optional[str] = None,
        artifacts: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update workflow state after completing a step.

        Args:
            step: The workflow step that was completed (e.g., "specify", "plan")
            feature: The feature being worked on
            artifacts: Dictionary of artifact paths created (e.g., {"spec": "path/to/spec.md"})
            metadata: Additional metadata to store
        """
        self.state["last_step"] = step
        self.state["last_updated"] = datetime.now().isoformat()

        if feature:
            self.state["current_feature"] = feature

            # Initialize feature tracking if needed
            if feature not in self.state["features"]:
                self.state["features"][feature] = {
                    "created": datetime.now().isoformat(),
                    "steps_completed": [],
                    "artifacts": {},
                    "metadata": {}
                }

            # Update feature tracking
            feature_state = self.state["features"][feature]

            if step not in feature_state["steps_completed"]:
                feature_state["steps_completed"].append(step)

            if artifacts:
                feature_state["artifacts"].update(artifacts)

            if metadata:
                feature_state["metadata"].update(metadata)

        self._save_state()

    def get_state(self) -> Dict[str, Any]:
        """Get the current workflow state."""
        return self.state.copy()

    def get_feature_state(self, feature: str) -> Optional[Dict[str, Any]]:
        """
        Get state for a specific feature.

        Args:
            feature: Feature identifier

        Returns:
            Feature state dictionary, or None if feature not found
        """
        return self.state.get("features", {}).get(feature)

    def has_completed_step(self, step: str, feature: Optional[str] = None) -> bool:
        """
        Check if a workflow step has been completed.

        Args:
            step: The workflow step to check
            feature: If provided, check for specific feature; otherwise check globally

        Returns:
            True if step has been completed
        """
        if feature:
            feature_state = self.get_feature_state(feature)
            if feature_state:
                return step in feature_state.get("steps_completed", [])
            return False
        else:
            # Check if any feature has completed this step
            return self.state.get("last_step") == step

    def validate_prerequisites(
        self,
        step: str,
        feature: Optional[str] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate that prerequisites are met for a workflow step.

        Args:
            step: The workflow step to validate
            feature: The feature being worked on

        Returns:
            Tuple of (is_valid, list_of_missing_prerequisites)
        """
        prerequisites = self.STEP_PREREQUISITES.get(step, [])
        missing = []

        for prereq in prerequisites:
            if feature:
                if not self.has_completed_step(prereq, feature):
                    missing.append(prereq)
            else:
                if not self.has_completed_step(prereq):
                    missing.append(prereq)

        return len(missing) == 0, missing

    def enforce_prerequisites(
        self,
        step: str,
        feature: Optional[str] = None
    ) -> None:
        """
        Enforce prerequisites by raising an exception if not met.

        Args:
            step: The workflow step to validate
            feature: The feature being worked on

        Raises:
            WorkflowError: If prerequisites are not met
        """
        is_valid, missing = self.validate_prerequisites(step, feature)

        if not is_valid:
            missing_text = ", ".join(missing)
            feature_text = f" for feature '{feature}'" if feature else ""
            raise WorkflowError(
                f"Cannot proceed with step '{step}'{feature_text}. "
                f"Missing prerequisites: {missing_text}. "
                f"Please complete these steps first."
            )

    def get_artifact_path(
        self,
        artifact_type: str,
        feature: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the path to a specific artifact.

        Args:
            artifact_type: Type of artifact (e.g., "spec", "plan", "tasks")
            feature: Feature identifier

        Returns:
            Path to artifact, or None if not found
        """
        if feature:
            feature_state = self.get_feature_state(feature)
            if feature_state:
                return feature_state.get("artifacts", {}).get(artifact_type)

        return None

    def artifact_exists(
        self,
        artifact_type: str,
        feature: Optional[str] = None
    ) -> bool:
        """
        Check if an artifact exists and is accessible.

        Args:
            artifact_type: Type of artifact (e.g., "spec", "plan", "tasks")
            feature: Feature identifier

        Returns:
            True if artifact exists and file is accessible
        """
        artifact_path = self.get_artifact_path(artifact_type, feature)

        if artifact_path:
            path = Path(artifact_path)
            return path.exists() and path.is_file()

        return False

    def reset_feature(self, feature: str) -> None:
        """
        Reset state for a specific feature.

        Args:
            feature: Feature identifier to reset
        """
        if feature in self.state.get("features", {}):
            del self.state["features"][feature]

            if self.state.get("current_feature") == feature:
                self.state["current_feature"] = None

            self._save_state()

    def clear_state(self) -> None:
        """Clear all workflow state and reinitialize."""
        self._initialize_state()


def get_orchestrator(state_file_path: Optional[Path] = None) -> WorkflowOrchestrator:
    """
    Get a workflow orchestrator instance.

    Args:
        state_file_path: Optional path to state file

    Returns:
        WorkflowOrchestrator instance
    """
    return WorkflowOrchestrator(state_file_path)
