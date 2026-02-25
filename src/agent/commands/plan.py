"""
Plan command handler for SpecKit Agent System.

This module provides the CLI command handler for the 'plan' command,
which generates implementation plans from specifications.
"""

from pathlib import Path
from typing import Optional
import sys

from ..engines.planning import PlanningEngine, PlanningError
from ..core.phr_manager import PHRManager
from ..core.workflow_orchestrator import WorkflowOrchestrator


def execute_plan(
    feature: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> dict:
    """
    Execute the plan command workflow.

    Args:
        feature: Feature name (if None, uses current branch)
        api_key: Optional Anthropic API key
        verbose: Enable verbose output

    Returns:
        Dictionary with execution results

    Raises:
        PlanningError: If plan generation fails
    """
    repo_root = Path.cwd()

    if verbose:
        print(f"Repository root: {repo_root}")
        if feature:
            print(f"Feature: {feature}")

    print("\n" + "=" * 70)
    print("GENERATING IMPLEMENTATION PLAN")
    print("=" * 70 + "\n")

    # Initialize components
    planning_engine = PlanningEngine(api_key=api_key, repo_root=repo_root)
    phr_manager = PHRManager(repo_root=repo_root)
    orchestrator = WorkflowOrchestrator()

    # Validate prerequisites
    print("✔️  Validating prerequisites...")
    try:
        orchestrator.enforce_prerequisites("plan", feature)
        print("✅ Prerequisites validated")
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        print("\nPlease ensure you have:")
        print("  1. Created a feature specification (run 'speckit-agent specify')")
        print("  2. Are on the correct feature branch")
        sys.exit(1)

    # Generate plan
    try:
        result = planning_engine.generate_plan(feature=feature)

    except PlanningError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        raise

    # Create PHR
    print("\n📝 Creating Prompt History Record...")
    try:
        # Prepare response text
        artifacts_list = "\\n".join([
            f"  - {name}: {path}"
            for name, path in result["artifacts"].items()
        ])

        response_text = f"""Implementation plan generated successfully.
Branch: {result['branch_name']}
Technical Context: {result['tech_context'].get('language', 'Not specified')}

Artifacts created:
{artifacts_list}

Constitution recheck: {'Passed' if result['constitution_recheck']['passed'] else 'Warnings'}"""

        phr_info = phr_manager.create_phr(
            title=f"Plan {result['branch_name']}",
            stage="plan",
            prompt=f"Generate implementation plan for {result['branch_name']}",
            response=response_text,
            feature=result["branch_name"],
            command="/sp.plan",
            files_created=[
                result["plan_file"],
                result["artifacts"]["research"],
                result["artifacts"]["data_model"],
                result["artifacts"]["cli_commands"],
                result["artifacts"]["file_formats"],
                result["artifacts"]["validation_rules"],
                result["artifacts"]["quickstart"]
            ],
            files_modified=[],
            tests_run=[],
            labels=["plan", "architecture", "design"],
            metadata={
                "model": planning_engine.model,
                "tech_stack": result["tech_context"].get("language", "Not specified"),
                "artifacts_count": len(result["artifacts"]),
                "clarifications_count": len(result.get("clarifications", {})),
                "constitution_recheck": result["constitution_recheck"]["passed"],
                "outcome_impact": f"Created implementation plan for {result['branch_name']}",
                "next_prompts": "Run /sp.tasks to generate task breakdown",
                "reflection": "Plan generation completed successfully" if result["constitution_recheck"]["passed"] else "Plan has constitution warnings"
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
            step="plan",
            feature=result["branch_name"],
            artifacts={
                "plan": result["plan_file"],
                **result["artifacts"]
            },
            metadata={
                "tech_stack": result["tech_context"].get("language", "Not specified"),
                "constitution_recheck": result["constitution_recheck"]["passed"]
            }
        )
        print("✅ Workflow state updated")

    except Exception as e:
        print(f"⚠️  Warning: Failed to update workflow state: {e}", file=sys.stderr)

    # Display results summary
    print("\n" + "=" * 70)
    print("IMPLEMENTATION PLAN GENERATED SUCCESSFULLY")
    print("=" * 70)
    print(f"\n📁 Feature: {result['branch_name']}")
    print(f"📄 Plan: {result['plan_file']}")

    print("\n📋 Artifacts Created:")
    for name, path in result["artifacts"].items():
        clean_name = name.replace("_", " ").title()
        print(f"   - {clean_name}: {path}")

    print(f"\n🔧 Technical Context:")
    print(f"   Language: {result['tech_context'].get('language', 'Not specified')}")
    print(f"   Storage: {result['tech_context'].get('storage', 'N/A')}")
    print(f"   Testing: {result['tech_context'].get('testing', 'Not specified')}")

    if result.get("clarifications"):
        print(f"\n💬 Clarifications received: {len(result['clarifications'])}")

    recheck = result["constitution_recheck"]
    print(f"\n✔️  Constitution Recheck: {'✅ PASSED' if recheck['passed'] else '⚠️  WARNINGS'}")
    if not recheck["passed"]:
        print("\n⚠️  Constitution Warnings:")
        for violation in recheck["violations"]:
            print(f"   - {violation}")

    if result.get("validation_errors"):
        print("\n⚠️  Plan Validation Warnings:")
        for error in result["validation_errors"]:
            print(f"   - {error}")

    print("\n📋 Next Steps:")
    print("   1. Review the generated plan and artifacts")
    print("   2. Run 'speckit-agent tasks' to generate task breakdown")
    print("   3. Begin implementation according to the plan")

    print("\n" + "=" * 70 + "\n")

    return result
