"""
Clarification Policy — Interaction Budget for User Requests.

This module defines the clarification budget system that limits
how many follow-up questions can be asked per request.

INVARIANT: Max 3 clarifications per request.
INVARIANT: No duplicate clarification types.
INVARIANT: When budget exhausted, proceed with defaults.
"""

from dataclasses import dataclass, field
from enum import Enum


class ClarificationType(str, Enum):
    """Types of clarifications that can be requested."""

    FORMAT = "format"
    COLORS = "colors"
    ARCHETYPE = "archetype"
    TRIBE_OR_THEME = "tribe_or_theme"
    CONSTRAINTS = "constraints"


# Default maximum clarifications per request
DEFAULT_MAX_CLARIFICATIONS = 3


@dataclass
class ClarificationPolicy:
    """
    Tracks clarification budget for a single request.

    Attributes:
        max_questions: Maximum clarifications allowed (default: 3)
        asked_questions: Set of clarification types already asked

    INVARIANT: len(asked_questions) <= max_questions
    """

    max_questions: int = DEFAULT_MAX_CLARIFICATIONS
    asked_questions: set[ClarificationType] = field(default_factory=set)

    def can_ask(self) -> bool:
        """Return True if budget allows more questions."""
        return len(self.asked_questions) < self.max_questions

    def remaining_budget(self) -> int:
        """Return number of questions remaining."""
        return max(0, self.max_questions - len(self.asked_questions))

    def has_asked(self, clarification_type: ClarificationType) -> bool:
        """Return True if this clarification type was already asked."""
        return clarification_type in self.asked_questions

    def record_question(self, clarification_type: ClarificationType) -> None:
        """
        Record that a clarification was asked.

        Raises:
            ValueError: If budget exhausted or type already asked
        """
        if not self.can_ask():
            raise ValueError("Clarification budget exhausted")
        if self.has_asked(clarification_type):
            raise ValueError(f"Already asked {clarification_type.value}")
        self.asked_questions.add(clarification_type)

    def is_exhausted(self) -> bool:
        """Return True if no more clarifications can be asked."""
        return not self.can_ask()


@dataclass(frozen=True)
class ClarificationRequest:
    """
    A request to clarify a specific aspect of user intent.

    Attributes:
        clarification_type: What aspect needs clarification
        question_key: Identifier for the question (for deduplication)
        options: Available choices (if applicable)
    """

    clarification_type: ClarificationType
    question_key: str
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClarificationDecision:
    """
    The result of evaluating whether to ask a clarification.

    Attributes:
        should_ask: Whether to ask the clarification
        reason: Why this decision was made
        clarification: The clarification to ask (if should_ask is True)
    """

    should_ask: bool
    reason: str
    clarification: ClarificationRequest | None = None
