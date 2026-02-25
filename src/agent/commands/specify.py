"""
Specify command handler for SpecKit Agent System.

This module provides the CLI command handler for the 'specify' command,
which generates feature specifications from natural language descriptions.
"""

from pathlib import Path
from typing import Optional
import sys

from ..engines.specification import SpecificationEngine, SpecificationError
from ..core.phr_manager import PHRManager
from ..core.workflow_orchestrator import WorkflowOrchestrator
from ..core.file_ops import atomic_write


def execute_specify(
    feature_description: str,
    short_name: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> dict:
    """
    Execute the specify command workflow.

    Args:
        feature_description: Natural language feature description
        short_name: Optional short name for the feature
        api_key: Optional Anthropic API key
        verbose: Enable verbose output

    Returns:
        Dictionary with execution results

    Raises:
        SpecificationError: If specification generation fails
    """
    repo_root = Path.cwd()

    if verbose:
        print(f"Repository root: {repo_root}")
        print(f"Feature description: {feature_description}")
        if short_name:
            print(f"Short name: {short_name}")

    print("\n" + "=" * 70)
    print("GENERATING FEATURE SPECIFICATION")
    print("=" * 70 + "\n")

    # Initialize components
    spec_engine = SpecificationEngine(api_key=api_key, repo_root=repo_root)
    phr_manager = PHRManager(repo_root=repo_root)
    orchestrator = WorkflowOrchestrator()

    # Generate specification
    try:
        result = spec_engine.generate_specification(
            feature_description=feature_description,
            short_name=short_name
        )

    except SpecificationError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        raise

    # Create quality checklist
    checklist_path = _create_quality_checklist(
        result=result,
        repo_root=repo_root
    )

    if checklist_path:
        print(f"📋 Quality checklist: {checklist_path}")
        result["checklist_file"] = str(checklist_path)

    # Create PHR
    print("\n📝 Creating Prompt History Record...")
    try:
        phr_info = phr_manager.create_phr(
            title=f"Specify {result['short_name']}",
            stage="spec",
            prompt=feature_description,
            response=f"Generated specification for feature: {result['branch_name']}",
            feature=result["branch_name"],
            command="/sp.specify",
            files_created=[result["spec_file"]],
            files_modified=[],
            tests_run=[],
            labels=["specification", "feature-generation"],
            metadata={
                "model": spec_engine.model,
                "validation_passed": result["validation_passed"],
                "clarifications_count": len(result.get("clarifications", {})),
                "outcome_impact": f"Created feature specification for {result['short_name']}",
                "next_prompts": "Run /sp.plan to generate implementation plan",
                "reflection": "Specification generated successfully" if result["validation_passed"] else "Specification has validation warnings"
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
            step="specify",
            feature=result["branch_name"],
            artifacts={
                "spec": result["spec_file"],
                "checklist": str(checklist_path) if checklist_path else None
            },
            metadata={
                "short_name": result["short_name"],
                "validation_passed": result["validation_passed"]
            }
        )
        print("✅ Workflow state updated")

    except Exception as e:
        print(f"⚠️  Warning: Failed to update workflow state: {e}", file=sys.stderr)

    # Display results summary
    print("\n" + "=" * 70)
    print("SPECIFICATION GENERATED SUCCESSFULLY")
    print("=" * 70)
    print(f"\n📁 Feature: {result['branch_name']}")
    print(f"📄 Specification: {result['spec_file']}")
    print(f"✔️  Validation: {'PASSED' if result['validation_passed'] else 'WARNINGS'}")

    if not result["validation_passed"]:
        print("\n⚠️  Validation Warnings:")
        for vr in result["validation_results"]:
            if not vr.passed:
                print(f"   - {vr.message}")

    if result.get("clarifications"):
        print(f"\n💬 Clarifications received: {len(result['clarifications'])}")

    print("\n📋 Next Steps:")
    print("   1. Review the generated specification")
    print("   2. Run 'speckit-agent plan' to generate implementation plan")
    print("   3. Run 'speckit-agent tasks' to break down into tasks")

    print("\n" + "=" * 70 + "\n")

    return result


def _create_quality_checklist(
    result: dict,
    repo_root: Path
) -> Optional[Path]:
    """
    Create a quality checklist file with validation results.

    Args:
        result: Specification generation result
        repo_root: Repository root path

    Returns:
        Path to checklist file, or None if creation fails
    """
    branch_name = result["branch_name"]
    checklist_dir = repo_root / "specs" / branch_name / "checklists"

    try:
        # Create checklists directory
        checklist_dir.mkdir(parents=True, exist_ok=True)

        checklist_path = checklist_dir / "requirements.md"

        # Build checklist content
        lines = []
        lines.append("# Requirements Quality Checklist")
        lines.append("")
        lines.append(f"**Feature**: {result['short_name']}")
        lines.append(f"**Generated**: {Path(result['spec_file']).name}")
        lines.append(f"**Validation Status**: {'✅ PASSED' if result['validation_passed'] else '⚠️  WARNINGS'}")
        lines.append("")

        lines.append("## Validation Results")
        lines.append("")

        validation_results = result.get("validation_results", [])
        passed_count = sum(1 for vr in validation_results if vr.passed)
        total_count = len(validation_results)

        lines.append(f"**Overall**: {passed_count}/{total_count} checks passed")
        lines.append("")

        # Group by rule
        rules_map = {}
        for vr in validation_results:
            rule = vr.rule or "general"
            if rule not in rules_map:
                rules_map[rule] = []
            rules_map[rule].append(vr)

        for rule, results in rules_map.items():
            lines.append(f"### {rule.replace('_', ' ').title()}")
            lines.append("")

            for vr in results:
                status = "✅" if vr.passed else "❌"
                lines.append(f"- [{status}] {vr.message}")

            lines.append("")

        # Clarifications section
        clarifications = result.get("clarifications", {})
        if clarifications:
            lines.append("## Clarifications Provided")
            lines.append("")

            for key, value in clarifications.items():
                clean_key = key.replace("_", " ").title()
                lines.append(f"- **{clean_key}**: {value}")

            lines.append("")

        # Action items
        lines.append("## Action Items")
        lines.append("")

        if result["validation_passed"]:
            lines.append("- [x] Specification validation passed")
            lines.append("- [ ] Review specification content")
            lines.append("- [ ] Generate implementation plan (`speckit-agent plan`)")
        else:
            lines.append("- [x] Specification generated with warnings")
            lines.append("- [ ] Review and address validation warnings")
            lines.append("- [ ] Update specification as needed")
            lines.append("- [ ] Generate implementation plan when ready")

        lines.append("")

        content = "\n".join(lines)

        # Write checklist
        atomic_write(checklist_path, content)

        return checklist_path

    except Exception as e:
        print(f"⚠️  Warning: Failed to create quality checklist: {e}", file=sys.stderr)
        return None
