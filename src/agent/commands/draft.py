"""
Draft command handler for SpecKit Agent System.

This module provides the CLI command handler for the 'draft' command,
which creates communication drafts (email/WhatsApp) for human approval.
"""

from pathlib import Path
from typing import Optional
import sys

from ..engines.communication import CommunicationEngine, CommunicationError
from ..core.phr_manager import PHRManager
from ..core.workflow_orchestrator import WorkflowOrchestrator

# Re-export CommunicationError for CLI usage
__all__ = ['execute_draft', 'CommunicationError']


def execute_draft(
    message_type: str,
    purpose: str,
    recipient: Optional[str] = None,
    context: Optional[str] = None,
    tone: str = "professional",
    feature: Optional[str] = None,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> dict:
    """
    Execute the draft command workflow.

    Args:
        message_type: Type of message ('email' or 'whatsapp')
        purpose: Purpose/intent of the message
        recipient: Optional recipient name
        context: Optional additional context
        tone: Message tone (professional, friendly, formal, casual)
        feature: Feature name for PHR routing (if None, uses 'general')
        api_key: Optional Anthropic API key
        verbose: Enable verbose output

    Returns:
        Dictionary with execution results

    Raises:
        CommunicationError: If draft creation fails
    """
    repo_root = Path.cwd()

    if verbose:
        print(f"Repository root: {repo_root}")
        print(f"Message type: {message_type}")
        print(f"Purpose: {purpose}")
        if recipient:
            print(f"Recipient: {recipient}")

    # Initialize components
    comm_engine = CommunicationEngine(repo_root=repo_root, api_key=api_key)
    phr_manager = PHRManager(repo_root=repo_root)
    orchestrator = WorkflowOrchestrator()

    # Create draft
    try:
        result = comm_engine.create_draft(
            message_type=message_type,
            purpose=purpose,
            recipient=recipient,
            context=context,
            tone=tone
        )

    except CommunicationError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        raise

    # Create PHR
    print("\n📝 Creating Prompt History Record...")
    try:
        response_text = f"""Communication draft created successfully.

Draft ID: {result['draft_id']}
Type: {result['message_type']}
Path: {result['draft_path']}
Status: {result['approval_status']}

Purpose: {purpose}
Recipient: {result.get('recipient', 'Not specified')}

IMPORTANT: This draft requires explicit human approval before sending.
Review the draft at: {result['draft_path']}"""

        phr_info = phr_manager.create_phr(
            title=f"Draft {result['message_type'].title()}: {purpose[:40]}",
            stage="misc",
            prompt=f"Create {message_type} draft: {purpose}",
            response=response_text,
            feature=feature,
            command="/sp.draft",
            files_created=[result["draft_path"]],
            files_modified=[],
            tests_run=[],
            labels=["communication", "draft", result["message_type"]],
            metadata={
                "draft_id": result["draft_id"],
                "message_type": result["message_type"],
                "approval_status": result["approval_status"],
                "recipient": result.get("recipient"),
                "outcome_impact": f"Created {result['message_type']} draft for human review",
                "next_prompts": "Review and approve/reject the draft",
                "reflection": "Draft created with approval gate enforced"
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
            step="draft",
            feature=feature,
            artifacts={
                "draft": result["draft_path"]
            },
            metadata={
                "draft_id": result["draft_id"],
                "message_type": result["message_type"],
                "approval_status": result["approval_status"]
            }
        )
        print("✅ Workflow state updated")

    except Exception as e:
        print(f"⚠️  Warning: Failed to update workflow state: {e}", file=sys.stderr)

    # Display results summary
    print("\n" + "=" * 70)
    print("COMMUNICATION DRAFT CREATED")
    print("=" * 70)
    print(f"\n📧 Type: {result['message_type'].upper()}")
    print(f"🆔 Draft ID: {result['draft_id']}")
    print(f"📁 Path: {result['draft_path']}")
    print(f"📋 Status: {result['approval_status'].upper()}")

    if result.get("subject"):
        print(f"\n📌 Subject: {result['subject']}")

    print(f"\n📝 Body Preview:")
    print("-" * 40)
    print(result.get("body_preview", ""))
    print("-" * 40)

    print("\n⚠️  APPROVAL REQUIRED")
    print("=" * 70)
    print(result["approval_message"])
    print("=" * 70)

    print("\n📋 Next Steps:")
    print("   1. Open the draft file and review the content")
    print("   2. Verify recipient, subject, and message are correct")
    print("   3. Update approval_status in the file's front-matter:")
    print("      - 'approved' to send")
    print("      - 'rejected' to discard")
    print("      - 'modified' if changes were made")
    print("   4. Only send messages that have been explicitly approved")

    print("\n" + "=" * 70 + "\n")

    return result
