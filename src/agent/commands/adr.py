"""
ADR command handler for SpecKit Agent System.

This module provides the CLI command handler for the 'adr' command,
which creates Architecture Decision Records for significant decisions.
"""

from pathlib import Path
from typing import Optional
import sys

from ..engines.adr import ADREngine, ADRError
from ..core.phr_manager import PHRManager
from ..core.workflow_orchestrator import WorkflowOrchestrator

# Re-export ADRError for CLI usage
__all__ = ['execute_adr', 'ADRError']


def execute_adr(
    decision_title: str,
    decision_context: Optional[str] = None,
    feature: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> dict:
    """
    Execute the ADR command workflow.

    Args:
        decision_title: Title of the architectural decision
        decision_context: Optional decision context
        feature: Feature name (if None, uses current branch)
        api_key: Optional Anthropic API key (unused - ADR doesn't use AI)
        verbose: Enable verbose output

    Returns:
        Dictionary with execution results

    Raises:
        ADRError: If ADR creation fails
    """
    repo_root = Path.cwd()

    if verbose:
        print(f"Repository root: {repo_root}")
        if feature:
            print(f"Feature: {feature}")
        print(f"Decision: {decision_title}")

    # Initialize components
    adr_engine = ADREngine(repo_root=repo_root)
    phr_manager = PHRManager(repo_root=repo_root)
    orchestrator = WorkflowOrchestrator()

    # Create ADR
    try:
        result = adr_engine.create_adr(
            decision_title=decision_title,
            decision_context=decision_context,
            feature=feature
        )

    except ADRError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        raise

    # Create PHR
    print("\n📝 Creating Prompt History Record...")
    try:
        # Prepare response text
        sig_test_summary = "\n".join([
            f"  - {key.title()}: {data['reason']}"
            for key, data in result["significance_test"].items()
        ])

        response_text = f"""Architecture Decision Record created successfully.

ADR ID: {result['adr_id']}
Title: {result['title']}
Feature: {result.get('feature', 'N/A')}

Significance Test (all passed):
{sig_test_summary}

Alternatives documented: {result['alternatives_count']}
Path: {result['adr_path']}"""

        phr_info = phr_manager.create_phr(
            title=f"ADR {result['adr_id']}: {result['title']}",
            stage="misc",
            prompt=f"Document architectural decision: {decision_title}",
            response=response_text,
            feature=result.get("feature"),
            command="/sp.adr",
            files_created=[result["adr_path"]],
            files_modified=[],
            tests_run=[],
            labels=["adr", "architecture", "decision"],
            metadata={
                "adr_id": result["adr_id"],
                "adr_slug": result["slug"],
                "alternatives_count": result["alternatives_count"],
                "significance_test_passed": True,
                "outcome_impact": f"Documented architectural decision: {result['title']}",
                "next_prompts": "Review ADR and mark as Accepted when implemented",
                "reflection": "ADR successfully created with significance testing"
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
            step="adr",
            feature=result.get("feature"),
            artifacts={
                "adr": result["adr_path"]
            },
            metadata={
                "adr_id": result["adr_id"],
                "adr_title": result["title"],
                "significance_passed": True
            }
        )
        print("✅ Workflow state updated")

    except Exception as e:
        print(f"⚠️  Warning: Failed to update workflow state: {e}", file=sys.stderr)

    # Display results summary
    print("\n" + "=" * 70)
    print("ARCHITECTURE DECISION RECORD CREATED")
    print("=" * 70)
    print(f"\n📋 ADR ID: {result['adr_id']}")
    print(f"📄 Title: {result['title']}")
    print(f"📁 Path: {result['adr_path']}")

    if result.get("feature"):
        print(f"🔗 Feature: {result['feature']}")

    print(f"\n✅ Significance Test: PASSED")
    for key, data in result["significance_test"].items():
        print(f"   - {key.title()}: {data['reason']}")

    print(f"\n📊 Metrics:")
    print(f"   Alternatives documented: {result['alternatives_count']}")

    if result.get("validation_errors"):
        print("\n⚠️  ADR Validation Warnings:")
        for error in result["validation_errors"]:
            print(f"   - {error}")

    print("\n📋 Next Steps:")
    print("   1. Review the generated ADR")
    print("   2. Update status to 'Accepted' when decision is implemented")
    print("   3. Link to related specifications and PRs")
    print("   4. Reference this ADR in relevant documentation")

    print("\n" + "=" * 70 + "\n")

    return result
