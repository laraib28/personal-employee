"""
Architecture Decision Record (ADR) engine for SpecKit Agent System.

This module creates ADRs for architecturally significant decisions with
significance testing and validation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re

from ..core.renderer import slugify, iso_date
from ..core.clarification import ask_question, ask_yes_no
from ..core.file_ops import atomic_write


class ADRError(Exception):
    """Raised when ADR operations fail."""
    pass


class ADREngine:
    """
    Manages Architecture Decision Record creation.

    Tests significance, prompts for context/alternatives/consequences,
    and generates structured ADR documents.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize the ADR engine.

        Args:
            repo_root: Repository root path
        """
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.adr_dir = self.repo_root / "history" / "adr"
        self.template_path = self.repo_root / ".specify" / "templates" / "adr-template.md"

    def create_adr(
        self,
        decision_title: str,
        decision_context: Optional[str] = None,
        feature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an Architecture Decision Record.

        Args:
            decision_title: Title of the architectural decision
            decision_context: Optional decision context
            feature: Optional feature context

        Returns:
            Dictionary with ADR creation results

        Raises:
            ADRError: If ADR creation fails
        """
        print("\n" + "=" * 70)
        print("CREATING ARCHITECTURE DECISION RECORD")
        print("=" * 70 + "\n")

        # Step 1: Run significance test
        print("🔍 Running significance test...")
        is_significant, test_results = self._run_significance_test(
            decision_title,
            decision_context
        )

        if not is_significant:
            print("\n❌ Significance test failed")
            print("\nThis decision does not meet the significance criteria:")
            for key, result in test_results.items():
                status = "✅" if result["passed"] else "❌"
                print(f"  {status} {key.title()}: {result['reason']}")

            print("\n💡 Suggestion: Consider capturing this as a PHR note instead of an ADR.")
            print("   ADRs should be reserved for decisions that:")
            print("   - Have long-term architectural consequences")
            print("   - Involved evaluation of multiple viable alternatives")
            print("   - Affect cross-cutting concerns (not isolated details)")

            raise ADRError(
                "Decision does not meet significance criteria. "
                "Use PHR for non-architectural decisions."
            )

        print("✅ Significance test passed")
        for key, result in test_results.items():
            print(f"  ✅ {key.title()}: {result['reason']}")

        # Step 2: Prompt for decision context if not provided
        if not decision_context:
            print("\n📝 Decision context needed...")
            decision_context = ask_question(
                "Please provide the decision context (what problem does this solve?):",
                question_id="decision_context"
            )

        # Step 3: Prompt for alternatives (minimum 2 required)
        print("\n📝 Gathering alternatives considered...")
        alternatives = self._prompt_for_alternatives()

        if len(alternatives) < 2:
            raise ADRError(
                "At least 2 alternatives must be documented. "
                "This is required to show proper evaluation was performed."
            )

        # Step 4: Prompt for consequences
        print("\n📝 Documenting consequences...")
        consequences = self._prompt_for_consequences()

        # Step 5: Allocate ADR ID
        print("\n🔢 Allocating ADR ID...")
        adr_id = self._allocate_adr_id()
        print(f"✅ ADR ID: {adr_id}")

        # Step 6: Generate slug from title
        adr_slug = slugify(decision_title)
        print(f"✅ Slug: {adr_slug}")

        # Step 7: Fill ADR template
        print("\n📄 Generating ADR document...")
        adr_content = self._fill_adr_template(
            adr_id=adr_id,
            title=decision_title,
            context=decision_context,
            decision=f"We will {decision_title}",
            alternatives=alternatives,
            consequences=consequences,
            significance_test=test_results,
            feature=feature
        )

        # Step 8: Validate ADR
        print("✔️  Validating ADR...")
        validation_errors = self._validate_adr(adr_content, alternatives, consequences)

        if validation_errors:
            print("⚠️  ADR validation warnings:")
            for error in validation_errors:
                print(f"   - {error}")

        # Step 9: Write ADR file
        adr_filename = f"{adr_id}-{adr_slug}.md"
        adr_path = self.adr_dir / adr_filename

        print(f"\n💾 Writing ADR to {adr_path}...")
        self.adr_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(adr_path, adr_content)

        print("✅ ADR created successfully!")

        return {
            "adr_id": adr_id,
            "adr_path": str(adr_path),
            "adr_filename": adr_filename,
            "title": decision_title,
            "slug": adr_slug,
            "significance_test": test_results,
            "alternatives_count": len(alternatives),
            "validation_errors": validation_errors,
            "feature": feature
        }

    def _run_significance_test(
        self,
        decision_title: str,
        decision_context: Optional[str]
    ) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
        """
        Run the three-part significance test.

        Tests:
        1. Impact: Long-term consequences for architecture/platform/security?
        2. Alternatives: Multiple viable options considered with tradeoffs?
        3. Scope: Cross-cutting concern (not isolated detail)?

        Returns:
            Tuple of (is_significant, test_results)
        """
        results = {}

        # Test 1: Impact - check for architectural keywords
        impact_keywords = [
            "architecture", "platform", "security", "framework", "stack",
            "database", "api", "authentication", "deployment", "infrastructure",
            "system", "design", "pattern", "integration", "scalability"
        ]

        title_lower = decision_title.lower()
        context_lower = (decision_context or "").lower()
        combined_text = title_lower + " " + context_lower

        has_impact = any(keyword in combined_text for keyword in impact_keywords)

        results["impact"] = {
            "passed": has_impact,
            "reason": "Appears to have architectural impact" if has_impact else "Limited architectural impact detected"
        }

        # Test 2: Alternatives - ask user
        print("\n❓ Significance Test - Alternatives")
        has_alternatives = ask_yes_no(
            "Were multiple viable alternatives considered with tradeoffs evaluated?",
            default=True
        )

        results["alternatives"] = {
            "passed": has_alternatives,
            "reason": "Multiple alternatives evaluated" if has_alternatives else "No alternatives evaluation"
        }

        # Test 3: Scope - ask user
        print("\n❓ Significance Test - Scope")
        is_cross_cutting = ask_yes_no(
            "Is this a cross-cutting concern that affects multiple parts of the system?",
            default=True
        )

        results["scope"] = {
            "passed": is_cross_cutting,
            "reason": "Cross-cutting concern" if is_cross_cutting else "Isolated detail"
        }

        # All three must pass
        is_significant = all(r["passed"] for r in results.values())

        return is_significant, results

    def _prompt_for_alternatives(self) -> List[Dict[str, str]]:
        """Prompt for alternatives considered."""
        alternatives = []

        print("\nEnter alternatives that were considered (minimum 2 required).")
        print("For each alternative, provide:")
        print("  1. Name/description of the alternative")
        print("  2. Why it was rejected")
        print("")

        for i in range(1, 6):  # Max 5 alternatives
            print(f"\n--- Alternative {i} ---")

            has_more = True
            if i > 2:  # After first 2, ask if they want to add more
                has_more = ask_yes_no(
                    f"Add alternative {i}?",
                    default=False
                )

            if not has_more:
                break

            alt_name = ask_question(
                f"Alternative {i} name/description:",
                question_id=f"alt_{i}_name"
            )

            if not alt_name or alt_name.strip().lower() in ["skip", "done", "no"]:
                break

            alt_rejection = ask_question(
                f"Why was '{alt_name}' rejected?",
                question_id=f"alt_{i}_rejection"
            )

            alternatives.append({
                "name": alt_name,
                "rejection_reason": alt_rejection
            })

        return alternatives

    def _prompt_for_consequences(self) -> Dict[str, List[str]]:
        """Prompt for positive and negative consequences."""
        consequences = {
            "positive": [],
            "negative": []
        }

        # Positive consequences
        print("\n--- Positive Consequences ---")
        print("Enter positive consequences (benefits) of this decision.")
        print("Enter one per prompt. Type 'done' when finished.")
        print("")

        for i in range(1, 6):  # Max 5 positive
            consequence = ask_question(
                f"Positive consequence {i} (or 'done'):",
                question_id=f"positive_{i}"
            )

            if not consequence or consequence.strip().lower() == "done":
                break

            consequences["positive"].append(consequence)

        # Negative consequences
        print("\n--- Negative Consequences ---")
        print("Enter negative consequences (drawbacks, risks) of this decision.")
        print("Enter one per prompt. Type 'done' when finished.")
        print("")

        for i in range(1, 6):  # Max 5 negative
            consequence = ask_question(
                f"Negative consequence {i} (or 'done'):",
                question_id=f"negative_{i}"
            )

            if not consequence or consequence.strip().lower() == "done":
                break

            consequences["negative"].append(consequence)

        return consequences

    def _allocate_adr_id(self) -> str:
        """Allocate next ADR ID by scanning existing ADRs."""
        if not self.adr_dir.exists():
            return "0001"

        max_id = 0

        # Scan for existing ADR files
        for file_path in self.adr_dir.glob("*.md"):
            filename = file_path.name

            # Extract ID from filename (format: 0001-slug.md)
            match = re.match(r'^(\d+)-', filename)
            if match:
                file_id = int(match.group(1))
                max_id = max(max_id, file_id)

        # Return next ID
        next_id = max_id + 1
        return f"{next_id:04d}"

    def _fill_adr_template(
        self,
        adr_id: str,
        title: str,
        context: str,
        decision: str,
        alternatives: List[Dict[str, str]],
        consequences: Dict[str, List[str]],
        significance_test: Dict[str, Dict[str, Any]],
        feature: Optional[str]
    ) -> str:
        """Fill ADR template with provided data."""
        # Load template
        if not self.template_path.exists():
            # Use built-in template if file doesn't exist
            template_content = self._get_builtin_template()
        else:
            template_content = self.template_path.read_text(encoding='utf-8')

        # Format alternatives
        alternatives_text = ""
        for alt in alternatives:
            alternatives_text += f"**{alt['name']}**\n\n"
            alternatives_text += f"- Rejected because: {alt['rejection_reason']}\n\n"

        # Format positive consequences
        positive_text = "\n".join([f"- {c}" for c in consequences["positive"]])
        if not positive_text:
            positive_text = "- (None documented)"

        # Format negative consequences
        negative_text = "\n".join([f"- {c}" for c in consequences["negative"]])
        if not negative_text:
            negative_text = "- (None documented)"

        # Prepare replacements
        replacements = {
            "{{ID}}": adr_id,
            "{{TITLE}}": title,
            "{{DATE_ISO}}": iso_date(),
            "{{FEATURE_NAME}}": feature or "N/A",
            "{{CONTEXT}}": context,
            "{{DECISION}}": decision,
            "{{POSITIVE_CONSEQUENCES}}": positive_text,
            "{{NEGATIVE_CONSEQUENCES}}": negative_text,
            "{{ALTERNATIVES}}": alternatives_text.strip(),
            "{{SPEC_LINK}}": f"../specs/{feature}/spec.md" if feature else "N/A",
            "{{PLAN_LINK}}": f"../specs/{feature}/plan.md" if feature else "N/A",
            "{{RELATED_ADRS}}": "N/A",
            "{{EVAL_NOTES_LINK}}": "N/A"
        }

        # Apply replacements
        content = template_content
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        # Set status to Proposed
        content = re.sub(
            r'\*\*Status:\*\* Proposed \| Accepted \| Superseded \| Rejected',
            '**Status:** Proposed',
            content
        )

        return content

    def _get_builtin_template(self) -> str:
        """Get built-in ADR template if file doesn't exist."""
        return """# ADR-{{ID}}: {{TITLE}}

**Status:** Proposed | Accepted | Superseded | Rejected
**Date:** {{DATE_ISO}}
**Feature:** {{FEATURE_NAME}}
**Context:** {{CONTEXT}}

## Decision

{{DECISION}}

## Consequences

### Positive

{{POSITIVE_CONSEQUENCES}}

### Negative

{{NEGATIVE_CONSEQUENCES}}

## Alternatives Considered

{{ALTERNATIVES}}

## References

- Feature Spec: {{SPEC_LINK}}
- Implementation Plan: {{PLAN_LINK}}
- Related ADRs: {{RELATED_ADRS}}
"""

    def _validate_adr(
        self,
        adr_content: str,
        alternatives: List[Dict[str, str]],
        consequences: Dict[str, List[str]]
    ) -> List[str]:
        """Validate ADR content."""
        errors = []

        # Check that significance test passed (implicitly if we got here)
        # Check that alternatives are documented
        if len(alternatives) < 2:
            errors.append("Less than 2 alternatives documented")

        # Check that consequences are listed
        if not consequences["positive"] and not consequences["negative"]:
            errors.append("No consequences documented")

        # Check for remaining placeholders
        if "{{" in adr_content:
            errors.append("ADR contains unresolved placeholders")

        # Check for required sections
        required_sections = ["Decision", "Consequences", "Alternatives Considered"]
        for section in required_sections:
            if section not in adr_content:
                errors.append(f"Missing required section: {section}")

        return errors


def create_adr(
    decision_title: str,
    decision_context: Optional[str] = None,
    feature: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to create an ADR.

    Args:
        decision_title: Decision title
        decision_context: Optional decision context
        feature: Optional feature context

    Returns:
        ADR creation results
    """
    engine = ADREngine()
    return engine.create_adr(decision_title, decision_context, feature)
