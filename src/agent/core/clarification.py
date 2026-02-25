"""
User clarification system for SpecKit Agent System.

This module provides functions to ask clarification questions from the user
while enforcing the one-question-at-a-time constitutional principle.
"""

from typing import Optional, List, Dict, Any
from .constitution_guard import ConstitutionGuard, ConstitutionError


class ClarificationError(Exception):
    """Raised when clarification handling fails."""
    pass


class ClarificationManager:
    """
    Manages user clarification requests with constitutional compliance.

    Enforces Principle IV: One Question at a Time by ensuring only one
    question is asked per interaction and tracking question state.
    """

    def __init__(self, constitution_guard: Optional[ConstitutionGuard] = None):
        """
        Initialize the clarification manager.

        Args:
            constitution_guard: Constitution guard instance for compliance checking
        """
        self.constitution_guard = constitution_guard or ConstitutionGuard()
        self.pending_questions: List[str] = []
        self.answers: Dict[str, str] = {}
        self.current_question: Optional[str] = None

    def ask_question(
        self,
        question: str,
        question_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Ask a single clarification question from the user.

        Enforces one-question-at-a-time policy per Constitution Principle IV.

        Args:
            question: The question to ask
            question_id: Optional identifier for tracking this question
            context: Optional context about why this question is being asked

        Returns:
            User's answer to the question

        Raises:
            ConstitutionError: If trying to ask multiple questions at once
            ClarificationError: If question handling fails
        """
        # Enforce constitution compliance: only one question at a time
        self.constitution_guard.enforce_compliance(
            operation="ask_question",
            context={"question_count": 1}
        )

        # Set current question
        self.current_question = question_id or question

        # Display question to user
        print("\n" + "=" * 70)
        print("CLARIFICATION NEEDED")
        print("=" * 70)
        print(f"\n{question}\n")

        if context:
            print("Context:")
            for key, value in context.items():
                print(f"  {key}: {value}")
            print()

        # Get user input
        print("Your answer:")
        answer = input("> ").strip()

        if not answer:
            raise ClarificationError("Empty answer provided. Please provide a response.")

        # Store answer
        if question_id:
            self.answers[question_id] = answer

        # Clear current question
        self.current_question = None

        print("=" * 70)
        print()

        return answer

    def ask_multiple_sequential(
        self,
        questions: List[Dict[str, Any]],
        stop_on_empty: bool = False
    ) -> Dict[str, str]:
        """
        Ask multiple questions sequentially (one at a time).

        This method respects the one-question-at-a-time principle by asking
        questions in sequence, waiting for each answer before proceeding.

        Args:
            questions: List of question dicts with keys: 'id', 'question', 'context' (optional)
            stop_on_empty: If True, stop asking if user provides empty answer

        Returns:
            Dictionary mapping question IDs to answers

        Raises:
            ConstitutionError: If constitutional violations occur
            ClarificationError: If question handling fails
        """
        answers = {}

        for q_dict in questions:
            question_id = q_dict.get("id")
            question = q_dict.get("question")
            context = q_dict.get("context")

            if not question:
                continue

            try:
                answer = self.ask_question(
                    question=question,
                    question_id=question_id,
                    context=context
                )

                if question_id:
                    answers[question_id] = answer

                # Stop if empty answer and stop_on_empty is True
                if stop_on_empty and not answer:
                    break

            except ClarificationError as e:
                if stop_on_empty:
                    break
                raise

        return answers

    def queue_question(self, question: str, question_id: Optional[str] = None) -> None:
        """
        Queue a question for later asking.

        Questions are queued but asked one at a time when process_queue is called.

        Args:
            question: Question to queue
            question_id: Optional identifier for this question
        """
        self.pending_questions.append({
            "id": question_id or f"q_{len(self.pending_questions) + 1}",
            "question": question
        })

    def process_queue(self, max_questions: Optional[int] = None) -> Dict[str, str]:
        """
        Process queued questions one at a time.

        Args:
            max_questions: Maximum number of questions to process (default: all)

        Returns:
            Dictionary mapping question IDs to answers
        """
        if not self.pending_questions:
            return {}

        # Limit number of questions if specified
        questions_to_ask = self.pending_questions[:max_questions] if max_questions else self.pending_questions

        # Ask questions sequentially
        answers = self.ask_multiple_sequential(questions_to_ask)

        # Remove asked questions from queue
        self.pending_questions = self.pending_questions[len(questions_to_ask):]

        return answers

    def has_pending_questions(self) -> bool:
        """Check if there are pending questions in the queue."""
        return len(self.pending_questions) > 0

    def clear_queue(self) -> None:
        """Clear all pending questions."""
        self.pending_questions = []

    def get_answer(self, question_id: str) -> Optional[str]:
        """
        Get a previously provided answer.

        Args:
            question_id: Question identifier

        Returns:
            Answer if found, None otherwise
        """
        return self.answers.get(question_id)

    def has_answer(self, question_id: str) -> bool:
        """
        Check if an answer has been provided for a question.

        Args:
            question_id: Question identifier

        Returns:
            True if answer exists
        """
        return question_id in self.answers


def ask_question(
    question: str,
    question_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function to ask a single clarification question.

    Args:
        question: Question to ask
        question_id: Optional question identifier
        context: Optional context information

    Returns:
        User's answer
    """
    manager = ClarificationManager()
    return manager.ask_question(question, question_id, context)


def ask_yes_no(
    question: str,
    default: Optional[bool] = None
) -> bool:
    """
    Ask a yes/no question.

    Args:
        question: Question to ask
        default: Default answer if user presses enter (None, True, or False)

    Returns:
        True for yes, False for no
    """
    # Format question with default indicator
    if default is True:
        prompt = f"{question} [Y/n]"
    elif default is False:
        prompt = f"{question} [y/N]"
    else:
        prompt = f"{question} [y/n]"

    manager = ClarificationManager()

    while True:
        answer = manager.ask_question(prompt)

        # Handle empty answer with default
        if not answer and default is not None:
            return default

        # Parse yes/no
        answer_lower = answer.lower()
        if answer_lower in ('y', 'yes', 'true', '1'):
            return True
        elif answer_lower in ('n', 'no', 'false', '0'):
            return False
        else:
            print("Please answer 'yes' or 'no' (or 'y'/'n')")


def ask_choice(
    question: str,
    choices: List[str],
    default: Optional[int] = None
) -> str:
    """
    Ask user to choose from a list of options.

    Args:
        question: Question to ask
        choices: List of choice options
        default: Default choice index (0-based) if user presses enter

    Returns:
        Selected choice string
    """
    # Build question with choices
    prompt_lines = [question, ""]
    for i, choice in enumerate(choices, 1):
        default_marker = " (default)" if default is not None and i == default + 1 else ""
        prompt_lines.append(f"  {i}. {choice}{default_marker}")

    prompt_lines.append("")
    prompt_lines.append("Enter choice number:")

    full_prompt = "\n".join(prompt_lines)

    manager = ClarificationManager()

    while True:
        answer = manager.ask_question(full_prompt)

        # Handle empty answer with default
        if not answer and default is not None:
            return choices[default]

        # Parse choice number
        try:
            choice_num = int(answer)
            if 1 <= choice_num <= len(choices):
                return choices[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("Please enter a valid number")
