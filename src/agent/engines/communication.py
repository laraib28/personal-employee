"""
Communication draft engine for SpecKit Agent System.

This module generates email and WhatsApp message drafts for human review.
All drafts require explicit human approval before any sending occurs.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum
import uuid
import os

from ..core.renderer import iso_date
from ..core.file_ops import atomic_write


class CommunicationError(Exception):
    """Raised when communication draft operations fail."""
    pass


class MessageType(Enum):
    """Supported message types."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class ApprovalStatus(Enum):
    """Draft approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class CommunicationEngine:
    """
    Generates communication drafts for human review and approval.

    All drafts are clearly marked as requiring approval.
    No messages are ever sent without explicit human consent.
    """

    def __init__(self, repo_root: Optional[Path] = None, api_key: Optional[str] = None):
        """
        Initialize the communication engine.

        Args:
            repo_root: Repository root path
            api_key: Anthropic API key for message generation
        """
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.drafts_dir = self.repo_root / "drafts"
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def create_draft(
        self,
        message_type: str,
        purpose: str,
        recipient: Optional[str] = None,
        context: Optional[str] = None,
        tone: str = "professional"
    ) -> Dict[str, Any]:
        """
        Create a communication draft.

        Args:
            message_type: Type of message ('email' or 'whatsapp')
            purpose: Purpose/intent of the message
            recipient: Optional recipient name/description
            context: Optional additional context
            tone: Message tone (professional, friendly, formal, casual)

        Returns:
            Dictionary with draft creation results

        Raises:
            CommunicationError: If draft creation fails
        """
        print("\n" + "=" * 70)
        print("CREATING COMMUNICATION DRAFT")
        print("=" * 70 + "\n")

        # Step 1: Detect and validate message type
        print("1. Detecting message type...")
        msg_type = self._detect_message_type(message_type)
        print(f"   Type: {msg_type.value}")

        # Step 2: Generate draft ID
        print("\n2. Generating draft ID...")
        draft_id = self._generate_draft_id()
        print(f"   ID: {draft_id}")

        # Step 3: Generate subject (email only)
        subject = None
        if msg_type == MessageType.EMAIL:
            print("\n3. Generating email subject...")
            subject = self._generate_subject(purpose, recipient)
            print(f"   Subject: {subject}")

        # Step 4: Generate message body
        print("\n4. Generating message body...")
        body = self._generate_body(
            msg_type=msg_type,
            purpose=purpose,
            recipient=recipient,
            context=context,
            tone=tone
        )
        print(f"   Body length: {len(body)} characters")

        # Step 5: Create draft with approval status
        print("\n5. Creating draft document...")
        draft_content = self._create_draft_document(
            draft_id=draft_id,
            msg_type=msg_type,
            subject=subject,
            body=body,
            purpose=purpose,
            recipient=recipient,
            tone=tone
        )

        # Step 6: Write draft file
        print("\n6. Writing draft file...")
        draft_path = self._write_draft(draft_id, msg_type, draft_content)
        print(f"   Path: {draft_path}")

        # Step 7: Log draft creation
        print("\n7. Logging draft creation...")
        self._log_draft_creation(draft_id, msg_type, purpose)

        print("\n" + "=" * 70)
        print("DRAFT CREATED SUCCESSFULLY")
        print("=" * 70)

        return {
            "draft_id": draft_id,
            "draft_path": str(draft_path),
            "message_type": msg_type.value,
            "subject": subject,
            "body_preview": body[:200] + "..." if len(body) > 200 else body,
            "approval_status": ApprovalStatus.PENDING.value,
            "recipient": recipient,
            "purpose": purpose,
            "approval_required": True,
            "approval_message": (
                "This draft requires explicit human approval before sending. "
                "Review the draft, then mark as approved/rejected/modified."
            )
        }

    def _detect_message_type(self, message_type: str) -> MessageType:
        """Detect and validate message type."""
        type_lower = message_type.lower().strip()

        # Map various inputs to message types
        email_variants = ["email", "e-mail", "mail", "em"]
        whatsapp_variants = ["whatsapp", "wa", "whats app", "wapp"]

        if type_lower in email_variants:
            return MessageType.EMAIL
        elif type_lower in whatsapp_variants:
            return MessageType.WHATSAPP
        else:
            raise CommunicationError(
                f"Unknown message type: '{message_type}'. "
                f"Supported types: email, whatsapp"
            )

    def _generate_draft_id(self) -> str:
        """Generate unique draft ID using UUID."""
        # Use timestamp prefix for sortability + UUID suffix for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_suffix = str(uuid.uuid4())[:8]
        return f"{timestamp}-{unique_suffix}"

    def _generate_subject(self, purpose: str, recipient: Optional[str]) -> str:
        """Generate email subject from purpose."""
        # If API available, use Claude to generate subject
        if self.api_key:
            try:
                return self._generate_subject_with_llm(purpose, recipient)
            except Exception as e:
                print(f"   Warning: LLM subject generation failed: {e}")
                # Fall back to simple extraction

        # Simple subject extraction from purpose
        # Take first sentence or first 60 chars
        subject = purpose.split('.')[0].strip()
        if len(subject) > 60:
            subject = subject[:57] + "..."
        return subject

    def _generate_subject_with_llm(self, purpose: str, recipient: Optional[str]) -> str:
        """Generate subject using Claude API."""
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)

        prompt = f"""Generate a concise, professional email subject line for the following purpose:

Purpose: {purpose}
{"Recipient: " + recipient if recipient else ""}

Requirements:
- Maximum 60 characters
- Clear and descriptive
- Professional tone
- No quotes around the subject

Respond with ONLY the subject line, nothing else."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    def _generate_body(
        self,
        msg_type: MessageType,
        purpose: str,
        recipient: Optional[str],
        context: Optional[str],
        tone: str
    ) -> str:
        """Generate message body."""
        # If API available, use Claude to generate body
        if self.api_key:
            try:
                return self._generate_body_with_llm(
                    msg_type, purpose, recipient, context, tone
                )
            except Exception as e:
                print(f"   Warning: LLM body generation failed: {e}")
                # Fall back to template

        # Simple template fallback
        return self._generate_body_template(msg_type, purpose, recipient, tone)

    def _generate_body_with_llm(
        self,
        msg_type: MessageType,
        purpose: str,
        recipient: Optional[str],
        context: Optional[str],
        tone: str
    ) -> str:
        """Generate message body using Claude API."""
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)

        type_guidance = {
            MessageType.EMAIL: "formal email with greeting, body paragraphs, and sign-off",
            MessageType.WHATSAPP: "concise WhatsApp message, friendly but professional, no formal greeting needed"
        }

        tone_guidance = {
            "professional": "Professional and businesslike",
            "friendly": "Warm and approachable while remaining professional",
            "formal": "Formal and respectful",
            "casual": "Casual and conversational"
        }

        prompt = f"""Generate a {type_guidance[msg_type]} for the following:

Purpose: {purpose}
{"Recipient: " + recipient if recipient else ""}
{"Context: " + context if context else ""}
Tone: {tone_guidance.get(tone, tone)}

Requirements:
- Be clear and concise
- Stay focused on the purpose
- Use appropriate formatting for {msg_type.value}
- Do not include [brackets] or placeholders
- Use realistic content based on the purpose

Generate ONLY the message content, no meta-commentary."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    def _generate_body_template(
        self,
        msg_type: MessageType,
        purpose: str,
        recipient: Optional[str],
        tone: str
    ) -> str:
        """Generate simple template body when LLM unavailable."""
        recipient_name = recipient or "Team"

        if msg_type == MessageType.EMAIL:
            return f"""Dear {recipient_name},

{purpose}

Please let me know if you have any questions or need additional information.

Best regards"""
        else:  # WhatsApp
            return f"""Hi {recipient_name},

{purpose}

Let me know if you need anything else."""

    def _create_draft_document(
        self,
        draft_id: str,
        msg_type: MessageType,
        subject: Optional[str],
        body: str,
        purpose: str,
        recipient: Optional[str],
        tone: str
    ) -> str:
        """Create draft document with YAML front-matter and markdown body."""
        current_date = iso_date()

        # Build YAML front-matter
        front_matter_lines = [
            "---",
            f"draft_id: {draft_id}",
            f"message_type: {msg_type.value}",
            f"created_date: {current_date}",
            f"approval_status: pending",
            f"sent_timestamp: null",
            f"purpose: \"{purpose}\"",
            f"recipient: \"{recipient or 'Not specified'}\"",
            f"tone: {tone}",
        ]

        if subject:
            front_matter_lines.append(f"subject: \"{subject}\"")

        front_matter_lines.append("---")
        front_matter = "\n".join(front_matter_lines)

        # Build document body with prominent DRAFT marker
        draft_marker = """
================================================================================
                              *** DRAFT ***
                    REQUIRES EXPLICIT HUMAN APPROVAL
                        DO NOT SEND WITHOUT APPROVAL
================================================================================
"""

        document = f"""{front_matter}

# Communication Draft

{draft_marker}

## Message Details

- **Type**: {msg_type.value.upper()}
- **Draft ID**: {draft_id}
- **Created**: {current_date}
- **Status**: PENDING APPROVAL
- **Recipient**: {recipient or 'Not specified'}
- **Purpose**: {purpose}

{"## Subject" + chr(10) + chr(10) + subject + chr(10) if subject else ""}
## Message Body

{body}

---

## Approval Instructions

To approve this draft:
1. Review the message content carefully
2. Verify recipient and purpose are correct
3. Update `approval_status` in front-matter to one of:
   - `approved` - Ready to send
   - `rejected` - Discard draft
   - `modified` - Needs changes (edit content first)
4. Only approved drafts should be sent through external channels

**WARNING**: This is a DRAFT. No message should be sent without explicit human approval.
"""

        return document

    def _write_draft(
        self,
        draft_id: str,
        msg_type: MessageType,
        content: str
    ) -> Path:
        """Write draft file using atomic write."""
        # Create directory structure: drafts/{type}/{draft-id}.md
        type_dir = self.drafts_dir / msg_type.value
        type_dir.mkdir(parents=True, exist_ok=True)

        draft_path = type_dir / f"{draft_id}.md"

        # Use atomic write for safety
        atomic_write(draft_path, content)

        return draft_path

    def _log_draft_creation(
        self,
        draft_id: str,
        msg_type: MessageType,
        purpose: str
    ) -> None:
        """Log draft creation to system records."""
        # Log to drafts/drafts.log
        log_path = self.drafts_dir / "drafts.log"

        log_entry = (
            f"{iso_date()} | {draft_id} | {msg_type.value} | "
            f"CREATED | {purpose[:50]}...\n"
        )

        # Append to log file (create if doesn't exist)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)


def create_draft(
    message_type: str,
    purpose: str,
    recipient: Optional[str] = None,
    context: Optional[str] = None,
    tone: str = "professional",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to create a communication draft.

    Args:
        message_type: Type of message ('email' or 'whatsapp')
        purpose: Purpose/intent of the message
        recipient: Optional recipient name
        context: Optional additional context
        tone: Message tone
        api_key: Optional Anthropic API key

    Returns:
        Draft creation results
    """
    engine = CommunicationEngine(api_key=api_key)
    return engine.create_draft(
        message_type=message_type,
        purpose=purpose,
        recipient=recipient,
        context=context,
        tone=tone
    )
