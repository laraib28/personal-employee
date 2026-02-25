"""
Constitution command handler for SpecKit Agent System.

This module provides the CLI command handler for the 'constitution' command,
which creates or amends project constitutions with versioning and sync reporting.
"""

from pathlib import Path
from typing import Optional
import sys

from ..engines.constitution import ConstitutionEngine, ConstitutionError
from ..core.phr_manager import PHRManager
from ..core.workflow_orchestrator import WorkflowOrchestrator


def execute_constitution(
    content: str,
    is_file_path: bool = False,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> dict:
    """
    Execute the constitution command workflow.

    Args:
        content: Constitution content or file path
        is_file_path: Whether content is a file path
        api_key: Optional Anthropic API key
        verbose: Enable verbose output

    Returns:
        Dictionary with execution results

    Raises:
        ConstitutionError: If constitution processing fails
    """
    repo_root = Path.cwd()

    if verbose:
        print(f"Repository root: {repo_root}")
        if is_file_path:
            print(f"Constitution file: {content}")
        else:
            print(f"Constitution content length: {len(content)} characters")

    print("\n" + "=" * 70)
    print("PROCESSING PROJECT CONSTITUTION")
    print("=" * 70 + "\n")

    # Initialize components
    constitution_engine = ConstitutionEngine(api_key=api_key, repo_root=repo_root)
    phr_manager = PHRManager(repo_root=repo_root)
    orchestrator = WorkflowOrchestrator()

    # Process constitution
    try:
        result = constitution_engine.process_constitution(
            content=content,
            is_file_path=is_file_path
        )

    except ConstitutionError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        raise

    # Create PHR
    print("\n📝 Creating Prompt History Record...")
    try:
        # Prepare prompt text
        if is_file_path:
            prompt_text = f"Create/update constitution from file: {content}"
        else:
            prompt_text = f"Create/update constitution from inline content:\n{content[:500]}"
            if len(content) > 500:
                prompt_text += "..."

        # Prepare response text
        response_text = f"""Constitution {'created' if result['is_new'] else 'amended'} successfully.
Version: {result['version']}
Change type: {result['change_type']}
Principles: {result['principles_count']}
Status: {result['status']}"""

        phr_info = phr_manager.create_phr(
            title=f"Constitution v{result['version']}",
            stage="constitution",
            prompt=prompt_text,
            response=response_text,
            feature=None,  # Constitution is global, not feature-specific
            command="/sp.constitution",
            files_created=[result["constitution_file"]] if result['is_new'] else [],
            files_modified=[] if result['is_new'] else [result["constitution_file"]],
            tests_run=[],
            labels=["constitution", "governance", result['change_type'].lower()],
            metadata={
                "model": constitution_engine.model,
                "version": result["version"],
                "change_type": result["change_type"],
                "is_new": result["is_new"],
                "principles_count": result["principles_count"],
                "outcome_impact": f"Constitution v{result['version']} {'created' if result['is_new'] else 'updated'}",
                "next_prompts": "Constitution is now active and will govern all workflows",
                "reflection": "Constitution processing completed successfully" if not result['validation_errors'] else "Constitution has validation warnings"
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

    # Update workflow state (constitution is a global state change)
    print("🔄 Updating workflow state...")
    try:
        orchestrator.update_state(
            step="constitution",
            feature=None,  # Constitution is not feature-specific
            artifacts={
                "constitution": result["constitution_file"]
            },
            metadata={
                "version": result["version"],
                "change_type": result["change_type"],
                "is_new": result["is_new"],
                "principles_count": result["principles_count"]
            }
        )
        print("✅ Workflow state updated")

    except Exception as e:
        print(f"⚠️  Warning: Failed to update workflow state: {e}", file=sys.stderr)

    # Display results summary
    print("\n" + "=" * 70)
    print("CONSTITUTION PROCESSED SUCCESSFULLY")
    print("=" * 70)
    print(f"\n📁 File: {result['constitution_file']}")
    print(f"🔢 Version: {result['version']}")
    print(f"📊 Change Type: {result['change_type']}")
    print(f"✅ Status: {result['status']}")
    print(f"📋 Principles: {result['principles_count']}")

    if result['validation_errors']:
        print("\n⚠️  Validation Warnings:")
        for error in result['validation_errors']:
            print(f"   - {error}")

    # Display sync impact report
    print("\n📋 Sync Impact Report:")
    sync_report = result['sync_report']
    print(f"   Version Change: {sync_report['version_change']}")
    print(f"   Change Type: {sync_report['change_type']}")
    print(f"   Modified Principles: {len(sync_report['modified_principles'])}")

    # Display template checks
    print("\n🔍 Template Alignment:")
    for check in result['template_checks']:
        print(f"   {check['status']} {check['message']}")

    print("\n📋 Next Steps:")
    if result['is_new']:
        print("   1. Review the constitution to ensure it captures all governance rules")
        print("   2. All future workflows will now enforce constitutional compliance")
        print("   3. Run 'speckit-agent specify' to create feature specifications")
    else:
        print("   1. Review the updated constitution and sync impact report")
        print("   2. Update any affected templates or workflows as needed")
        print("   3. All workflows will use the new constitution version")

    print("\n" + "=" * 70 + "\n")

    return result
