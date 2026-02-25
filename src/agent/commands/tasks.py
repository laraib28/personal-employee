"""
Tasks command handler for SpecKit Agent System.

This module provides the CLI command handler for the 'tasks' command,
which generates dependency-ordered task lists from implementation plans.
"""

from pathlib import Path
from typing import Optional
import sys

from ..engines.task_gen import TaskGenerationEngine, TaskGenerationError
from ..core.phr_manager import PHRManager
from ..core.workflow_orchestrator import WorkflowOrchestrator
from ..core.file_ops import atomic_write


def execute_tasks(
    feature: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> dict:
    """
    Execute the tasks command workflow.

    Args:
        feature: Feature name (if None, uses current branch)
        api_key: Optional Anthropic API key
        verbose: Enable verbose output

    Returns:
        Dictionary with execution results

    Raises:
        TaskGenerationError: If task generation fails
    """
    repo_root = Path.cwd()

    if verbose:
        print(f"Repository root: {repo_root}")
        if feature:
            print(f"Feature: {feature}")

    print("\n" + "=" * 70)
    print("GENERATING TASK LIST")
    print("=" * 70 + "\n")

    # Initialize components
    task_engine = TaskGenerationEngine(api_key=api_key, repo_root=repo_root)
    phr_manager = PHRManager(repo_root=repo_root)
    orchestrator = WorkflowOrchestrator()

    # Validate prerequisites
    print("✔️  Validating prerequisites...")
    try:
        orchestrator.enforce_prerequisites("tasks", feature)
        print("✅ Prerequisites validated")
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        print("\nPlease ensure you have:")
        print("  1. Created a feature specification (run 'speckit-agent specify')")
        print("  2. Generated an implementation plan (run 'speckit-agent plan')")
        print("  3. Are on the correct feature branch")
        sys.exit(1)

    # Generate tasks
    try:
        result = task_engine.generate_tasks(feature=feature)

    except TaskGenerationError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        raise

    # Write tasks.md
    print("\n💾 Writing tasks.md...")
    tasks_file = Path(result["feature_dir"]) / "tasks.md"
    atomic_write(tasks_file, result["tasks_content"])
    print(f"✅ Created {tasks_file}")

    result["tasks_file"] = str(tasks_file)

    # Create PHR
    print("\n📝 Creating Prompt History Record...")
    try:
        response_text = f"""Task list generated successfully.
Feature: {result['feature']}
Total tasks: {result['task_count']}
Parallelizable: {result['parallel_count']} ({result['parallel_percentage']:.1f}%)
User stories: {result['user_story_count']}

Tasks organized by phase with dependency ordering and parallelization markers."""

        phr_info = phr_manager.create_phr(
            title=f"Tasks {result['feature']}",
            stage="tasks",
            prompt=f"Generate task breakdown for {result['feature']}",
            response=response_text,
            feature=result["feature"],
            command="/sp.tasks",
            files_created=[result["tasks_file"]],
            files_modified=[],
            tests_run=[],
            labels=["tasks", "breakdown", "dependencies"],
            metadata={
                "model": task_engine.model,
                "task_count": result["task_count"],
                "parallel_percentage": result["parallel_percentage"],
                "user_story_count": result["user_story_count"],
                "outcome_impact": f"Created task breakdown for {result['feature']}",
                "next_prompts": "Begin implementation following the task order",
                "reflection": "Task generation completed successfully"
            }
        )

        phr_id = phr_info["id"]
        phr_path = phr_info["path"]
        print(f"✅ PHR created: {phr_path} (ID: {phr_id})")

        result["phr_id"] = phr_id
        result["phr_path"] = phr_path

    except Exception as e:
        print(f"⚠️  Warning: Failed to create PHR: {e}", file=sys.stderr)
        result["phr_id"] = None
        result["phr_path"] = None

    # Update workflow state
    print("🔄 Updating workflow state...")
    try:
        orchestrator.update_state(
            step="tasks",
            feature=result["feature"],
            artifacts={
                "tasks": result["tasks_file"]
            },
            metadata={
                "task_count": result["task_count"],
                "parallel_percentage": result["parallel_percentage"]
            }
        )
        print("✅ Workflow state updated")

    except Exception as e:
        print(f"⚠️  Warning: Failed to update workflow state: {e}", file=sys.stderr)

    # Display results summary
    print("\n" + "=" * 70)
    print("TASK LIST GENERATED SUCCESSFULLY")
    print("=" * 70)
    print(f"\n📁 Feature: {result['feature']}")
    print(f"📄 Tasks: {result['tasks_file']}")

    print(f"\n📊 Metrics:")
    print(f"   Total tasks: {result['task_count']}")
    print(f"   Parallelizable: {result['parallel_count']} ({result['parallel_percentage']:.1f}%)")
    print(f"   User stories: {result['user_story_count']}")

    if result['parallel_percentage'] >= 30:
        print(f"\n   ✅ Meets >=30% parallelization target")
    else:
        print(f"\n   ⚠️  Below 30% parallelization target")

    if result.get("validation_errors"):
        print("\n⚠️  Task Validation Warnings:")
        for error in result["validation_errors"]:
            print(f"   - {error}")

    print("\n📋 Next Steps:")
    print("   1. Review the generated task list")
    print("   2. Begin implementation following the dependency order")
    print("   3. Use [P] markers to identify tasks that can run in parallel")
    print("   4. Track progress by checking off completed tasks")

    print("\n" + "=" * 70 + "\n")

    return result
