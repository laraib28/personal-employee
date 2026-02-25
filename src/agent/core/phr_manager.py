"""
Prompt History Record (PHR) management for SpecKit Agent System.

This module creates PHR files by calling the existing create-phr.sh script
and filling in template placeholders with actual values.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess
import json
import os
import re


class PHRError(Exception):
    """Raised when PHR creation or management fails."""
    pass


class PHRManager:
    """
    Manages creation and manipulation of Prompt History Records (PHRs).

    PHRs are stored in history/prompts/ with routing based on context:
    - constitution → history/prompts/constitution/
    - feature stages → history/prompts/<feature-name>/
    - general → history/prompts/general/
    """

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize the PHR manager.

        Args:
            repo_root: Repository root path. If None, uses current directory.
        """
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.script_path = self.repo_root / ".specify" / "scripts" / "bash" / "create-phr.sh"

        if not self.script_path.exists():
            raise PHRError(f"create-phr.sh script not found at {self.script_path}")

    def create_phr(
        self,
        title: str,
        stage: str,
        prompt: str,
        response: str,
        feature: Optional[str] = None,
        command: Optional[str] = None,
        files_created: Optional[List[str]] = None,
        files_modified: Optional[List[str]] = None,
        tests_run: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Create a new Prompt History Record.

        Args:
            title: PHR title (used for filename)
            stage: Workflow stage (constitution, spec, plan, tasks, etc.)
            prompt: The full user prompt text
            response: Key assistant response text
            feature: Feature identifier (e.g., "001-ai-agent-system")
            command: Command that was executed (e.g., "/sp.specify")
            files_created: List of files created
            files_modified: List of files modified
            tests_run: List of tests executed
            labels: List of topic labels
            metadata: Additional metadata

        Returns:
            Dictionary with PHR information (id, path, context, stage)

        Raises:
            PHRError: If PHR creation fails
        """
        # Build command arguments
        cmd = [
            str(self.script_path),
            "--title", title,
            "--stage", stage,
            "--json"
        ]

        if feature:
            cmd.extend(["--feature", feature])

        # Execute create-phr.sh script
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root
            )

            # Parse JSON output
            phr_info = json.loads(result.stdout.strip())

        except subprocess.CalledProcessError as e:
            raise PHRError(f"Failed to create PHR: {e.stderr}")
        except json.JSONDecodeError as e:
            raise PHRError(f"Failed to parse PHR creation output: {e}")

        # Fill in template placeholders
        phr_path = Path(phr_info["path"])
        self._fill_template(
            phr_path=phr_path,
            phr_id=phr_info["id"],
            title=title,
            stage=stage,
            prompt=prompt,
            response=response,
            feature=feature or "none",
            command=command,
            files_created=files_created or [],
            files_modified=files_modified or [],
            tests_run=tests_run or [],
            labels=labels or [],
            metadata=metadata or {}
        )

        return phr_info

    def _fill_template(
        self,
        phr_path: Path,
        phr_id: str,
        title: str,
        stage: str,
        prompt: str,
        response: str,
        feature: str,
        command: Optional[str],
        files_created: List[str],
        files_modified: List[str],
        tests_run: List[str],
        labels: List[str],
        metadata: Dict[str, Any]
    ) -> None:
        """
        Fill in template placeholders in the PHR file.

        Args:
            phr_path: Path to the PHR file
            phr_id: PHR identifier
            title: PHR title
            stage: Workflow stage
            prompt: User prompt text
            response: Assistant response text
            feature: Feature identifier
            command: Command executed
            files_created: List of created files
            files_modified: List of modified files
            tests_run: List of tests executed
            labels: Topic labels
            metadata: Additional metadata
        """
        # Read template
        content = phr_path.read_text(encoding='utf-8')

        # Get git information
        branch = self._get_git_branch()
        user = self._get_git_user()

        # Prepare files YAML
        all_files = []
        if files_created:
            all_files.extend([f"  - {f} (created)" for f in files_created])
        if files_modified:
            all_files.extend([f"  - {f} (modified)" for f in files_modified])
        files_yaml = "\n".join(all_files) if all_files else "  []"

        # Prepare tests YAML
        tests_yaml = "\n".join([f"  - {t}" for t in tests_run]) if tests_run else "  []"

        # Prepare labels
        labels_str = ", ".join([f'"{label}"' for label in labels]) if labels else ""

        # Get model name from metadata or use default
        model = metadata.get("model", "claude-sonnet-4-5")

        # Prepare outcome summaries
        files_count = len(files_created) + len(files_modified)
        files_summary = f"{files_count} file(s) changed"
        tests_summary = f"{len(tests_run)} test(s) run" if tests_run else "No tests run"
        outcome_impact = metadata.get("outcome_impact", "Workflow step completed")
        next_prompts = metadata.get("next_prompts", "Continue to next workflow step")
        reflection = metadata.get("reflection", "Execution successful")

        # Fill in all placeholders
        replacements = {
            "{{ID}}": phr_id,
            "{{TITLE}}": title,
            "{{STAGE}}": stage,
            "{{DATE_ISO}}": datetime.now().strftime("%Y-%m-%d"),
            "{{SURFACE}}": "agent",
            "{{MODEL}}": model,
            "{{FEATURE}}": feature,
            "{{BRANCH}}": branch,
            "{{USER}}": user,
            "{{COMMAND}}": command or f"/sp.{stage}",
            "{{LABELS}}": labels_str,
            "{{LINKS_SPEC}}": metadata.get("spec_link", "null"),
            "{{LINKS_TICKET}}": metadata.get("ticket_link", "null"),
            "{{LINKS_ADR}}": metadata.get("adr_link", "null"),
            "{{LINKS_PR}}": metadata.get("pr_link", "null"),
            "{{FILES_YAML}}": files_yaml,
            "{{TESTS_YAML}}": tests_yaml,
            "{{PROMPT_TEXT}}": self._escape_yaml_text(prompt),
            "{{RESPONSE_TEXT}}": self._escape_yaml_text(response),
            "{{OUTCOME_IMPACT}}": outcome_impact,
            "{{TESTS_SUMMARY}}": tests_summary,
            "{{FILES_SUMMARY}}": files_summary,
            "{{NEXT_PROMPTS}}": next_prompts,
            "{{REFLECTION_NOTE}}": reflection,
            "{{FAILURE_MODES}}": metadata.get("failure_modes", "None observed"),
            "{{GRADER_RESULTS}}": metadata.get("grader_results", "N/A"),
            "{{PROMPT_VARIANT_ID}}": metadata.get("prompt_variant", "default"),
            "{{NEXT_EXPERIMENT}}": metadata.get("next_experiment", "N/A")
        }

        # Apply all replacements
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, str(value))

        # Check for any remaining placeholders
        remaining_placeholders = re.findall(r'{{[A-Z_]+}}', content)
        if remaining_placeholders:
            raise PHRError(
                f"Failed to fill all placeholders in PHR. Remaining: {remaining_placeholders}"
            )

        # Write filled content back
        phr_path.write_text(content, encoding='utf-8')

    def _get_git_branch(self) -> str:
        """Get current git branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def _get_git_user(self) -> str:
        """Get git user name."""
        try:
            result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return os.environ.get("USER", "unknown")

    def _escape_yaml_text(self, text: str) -> str:
        """
        Escape text for YAML content sections.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for YAML
        """
        # For multiline text in markdown sections, just ensure proper indentation
        # and handle any special characters
        if not text:
            return "N/A"

        # Remove leading/trailing whitespace
        text = text.strip()

        # For very long text, truncate with indicator
        max_length = 5000
        if len(text) > max_length:
            text = text[:max_length] + "\n\n[... truncated for length ...]"

        return text

    def get_phr_path(
        self,
        phr_id: str,
        stage: str,
        feature: Optional[str] = None
    ) -> Optional[Path]:
        """
        Get the path to a specific PHR.

        Args:
            phr_id: PHR identifier (e.g., "0001")
            stage: Workflow stage
            feature: Feature identifier for feature-specific PHRs

        Returns:
            Path to PHR file, or None if not found
        """
        # Determine directory based on stage
        if stage == "constitution":
            phr_dir = self.repo_root / "history" / "prompts" / "constitution"
        elif feature:
            phr_dir = self.repo_root / "history" / "prompts" / feature
        else:
            phr_dir = self.repo_root / "history" / "prompts" / "general"

        if not phr_dir.exists():
            return None

        # Find PHR file matching ID and stage
        pattern = f"{phr_id}-*.{stage}.prompt.md"
        matching_files = list(phr_dir.glob(pattern))

        return matching_files[0] if matching_files else None


def create_phr(
    title: str,
    stage: str,
    prompt: str,
    response: str,
    feature: Optional[str] = None,
    **kwargs
) -> Dict[str, str]:
    """
    Convenience function to create a PHR without instantiating a manager.

    Args:
        title: PHR title
        stage: Workflow stage
        prompt: User prompt text
        response: Assistant response text
        feature: Feature identifier
        **kwargs: Additional arguments passed to PHRManager.create_phr

    Returns:
        Dictionary with PHR information
    """
    manager = PHRManager()
    return manager.create_phr(
        title=title,
        stage=stage,
        prompt=prompt,
        response=response,
        feature=feature,
        **kwargs
    )
