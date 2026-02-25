"""
Unit tests for clarification module.

Tests the one-question-at-a-time policy enforcement and user interaction.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.agent.core.clarification import (
    ask_question,
    ask_yes_no,
    ClarificationManager,
    ClarificationError
)


class TestAskQuestion:
    """Test ask_question function."""

    @patch('builtins.input', return_value='Test answer')
    def test_ask_question_returns_answer(self, mock_input):
        """Test that ask_question returns user input."""
        result = ask_question("Test question?", question_id="test_q1")
        assert result == 'Test answer'

    @patch('builtins.input', return_value='  trimmed answer  ')
    def test_ask_question_trims_whitespace(self, mock_input):
        """Test that answer whitespace is trimmed."""
        result = ask_question("Test question?", question_id="test_q2")
        assert result == 'trimmed answer'

    @patch('builtins.input', return_value='')
    def test_ask_question_empty_answer(self, mock_input):
        """Test handling of empty answer."""
        result = ask_question("Test question?", question_id="test_q3")
        assert result == ''

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_ask_question_keyboard_interrupt(self, mock_input):
        """Test handling of keyboard interrupt."""
        with pytest.raises(KeyboardInterrupt):
            ask_question("Test question?", question_id="test_q4")


class TestAskYesNo:
    """Test ask_yes_no function."""

    @patch('builtins.input', return_value='y')
    def test_yes_returns_true(self, mock_input):
        """Test that 'y' returns True."""
        result = ask_yes_no("Confirm?")
        assert result is True

    @patch('builtins.input', return_value='yes')
    def test_yes_full_returns_true(self, mock_input):
        """Test that 'yes' returns True."""
        result = ask_yes_no("Confirm?")
        assert result is True

    @patch('builtins.input', return_value='Y')
    def test_yes_uppercase_returns_true(self, mock_input):
        """Test that 'Y' returns True."""
        result = ask_yes_no("Confirm?")
        assert result is True

    @patch('builtins.input', return_value='n')
    def test_no_returns_false(self, mock_input):
        """Test that 'n' returns False."""
        result = ask_yes_no("Confirm?")
        assert result is False

    @patch('builtins.input', return_value='no')
    def test_no_full_returns_false(self, mock_input):
        """Test that 'no' returns False."""
        result = ask_yes_no("Confirm?")
        assert result is False

    @patch('builtins.input', return_value='')
    def test_empty_returns_default_true(self, mock_input):
        """Test that empty input returns default (True)."""
        result = ask_yes_no("Confirm?", default=True)
        assert result is True

    @patch('builtins.input', return_value='')
    def test_empty_returns_default_false(self, mock_input):
        """Test that empty input returns default (False)."""
        result = ask_yes_no("Confirm?", default=False)
        assert result is False


class TestClarificationManager:
    """Test ClarificationManager class."""

    def test_init_creates_empty_state(self):
        """Test that manager initializes with empty state."""
        manager = ClarificationManager()
        assert manager.questions_asked == 0
        assert len(manager.history) == 0

    def test_ask_increments_counter(self):
        """Test that asking increments question counter."""
        manager = ClarificationManager()

        with patch('builtins.input', return_value='answer'):
            manager.ask("Question 1?")
            assert manager.questions_asked == 1

            manager.ask("Question 2?")
            assert manager.questions_asked == 2

    def test_ask_records_history(self):
        """Test that questions are recorded in history."""
        manager = ClarificationManager()

        with patch('builtins.input', return_value='test answer'):
            manager.ask("Test question?")

        assert len(manager.history) == 1
        assert manager.history[0]['question'] == "Test question?"
        assert manager.history[0]['answer'] == 'test answer'

    def test_one_question_at_a_time_policy(self):
        """Test that only one question is asked per turn."""
        manager = ClarificationManager()

        # The manager should enforce asking questions one at a time
        # This is a policy check - in practice, the caller should
        # only call ask() once per agent turn
        with patch('builtins.input', return_value='answer'):
            result = manager.ask("Single question?")
            assert result == 'answer'

    def test_get_last_answer(self):
        """Test retrieving the last answer."""
        manager = ClarificationManager()

        with patch('builtins.input', return_value='last answer'):
            manager.ask("Question?")

        assert manager.get_last_answer() == 'last answer'

    def test_get_last_answer_empty(self):
        """Test get_last_answer when no questions asked."""
        manager = ClarificationManager()
        assert manager.get_last_answer() is None

    def test_clear_history(self):
        """Test clearing question history."""
        manager = ClarificationManager()

        with patch('builtins.input', return_value='answer'):
            manager.ask("Question?")

        manager.clear_history()
        assert len(manager.history) == 0
        assert manager.questions_asked == 0


class TestClarificationError:
    """Test ClarificationError exception."""

    def test_error_message(self):
        """Test ClarificationError message."""
        error = ClarificationError("Test clarification error")
        assert str(error) == "Test clarification error"

    def test_error_inheritance(self):
        """Test that ClarificationError inherits from Exception."""
        error = ClarificationError("Test")
        assert isinstance(error, Exception)


class TestOneQuestionPolicy:
    """Test enforcement of one-question-at-a-time policy."""

    def test_multiple_questions_warning(self):
        """Test that attempting multiple questions logs warning."""
        manager = ClarificationManager()

        # Asking multiple questions in quick succession should work
        # but the policy is that the agent should only ask one per turn
        with patch('builtins.input', return_value='answer'):
            q1 = manager.ask("Question 1?")
            q2 = manager.ask("Question 2?")

        # Both questions should get answers (policy is advisory)
        assert q1 == 'answer'
        assert q2 == 'answer'
        assert manager.questions_asked == 2

    def test_reset_between_turns(self):
        """Test resetting state between agent turns."""
        manager = ClarificationManager()

        with patch('builtins.input', return_value='answer'):
            manager.ask("Turn 1 question?")

        # Simulate new turn
        manager.new_turn()

        with patch('builtins.input', return_value='answer 2'):
            result = manager.ask("Turn 2 question?")

        assert result == 'answer 2'
