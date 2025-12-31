"""
Tests for Clarification Budget System.

These tests verify:
- Budget enforcement (max 3 clarifications)
- No duplicate questions
- Proceed with defaults when budget exhausted
- Deterministic ask/assume decisions
"""

import pytest

from forgebreaker.models.clarification import (
    DEFAULT_MAX_CLARIFICATIONS,
    ClarificationDecision,
    ClarificationPolicy,
    ClarificationType,
)
from forgebreaker.models.intent import (
    Archetype,
    Constraint,
    DeckIntent,
    Format,
)
from forgebreaker.services.clarification import (
    create_policy,
    evaluate_clarification,
    get_next_clarification,
    record_clarification,
    resolve_intent_with_policy,
    should_ask_clarification,
)


class TestClarificationPolicy:
    """Tests for ClarificationPolicy model."""

    def test_default_max_questions(self) -> None:
        """Default max is 3 questions."""
        policy = ClarificationPolicy()
        assert policy.max_questions == 3
        assert policy.max_questions == DEFAULT_MAX_CLARIFICATIONS

    def test_starts_empty(self) -> None:
        """Policy starts with no asked questions."""
        policy = ClarificationPolicy()
        assert len(policy.asked_questions) == 0
        assert policy.can_ask() is True

    def test_remaining_budget(self) -> None:
        """Remaining budget decreases as questions are asked."""
        policy = ClarificationPolicy()
        assert policy.remaining_budget() == 3

        policy.record_question(ClarificationType.FORMAT)
        assert policy.remaining_budget() == 2

        policy.record_question(ClarificationType.COLORS)
        assert policy.remaining_budget() == 1

        policy.record_question(ClarificationType.ARCHETYPE)
        assert policy.remaining_budget() == 0

    def test_has_asked(self) -> None:
        """has_asked correctly tracks asked questions."""
        policy = ClarificationPolicy()
        assert policy.has_asked(ClarificationType.FORMAT) is False

        policy.record_question(ClarificationType.FORMAT)
        assert policy.has_asked(ClarificationType.FORMAT) is True
        assert policy.has_asked(ClarificationType.COLORS) is False

    def test_is_exhausted(self) -> None:
        """is_exhausted returns True when budget is 0."""
        policy = ClarificationPolicy()
        assert policy.is_exhausted() is False

        policy.record_question(ClarificationType.FORMAT)
        policy.record_question(ClarificationType.COLORS)
        assert policy.is_exhausted() is False

        policy.record_question(ClarificationType.ARCHETYPE)
        assert policy.is_exhausted() is True

    def test_record_question_raises_when_exhausted(self) -> None:
        """Cannot record question when budget exhausted."""
        policy = ClarificationPolicy()
        policy.record_question(ClarificationType.FORMAT)
        policy.record_question(ClarificationType.COLORS)
        policy.record_question(ClarificationType.ARCHETYPE)

        with pytest.raises(ValueError, match="exhausted"):
            policy.record_question(ClarificationType.CONSTRAINTS)

    def test_record_question_raises_on_duplicate(self) -> None:
        """Cannot ask same question twice."""
        policy = ClarificationPolicy()
        policy.record_question(ClarificationType.FORMAT)

        with pytest.raises(ValueError, match="Already asked"):
            policy.record_question(ClarificationType.FORMAT)


class TestBudgetEnforcement:
    """Tests for clarification budget enforcement."""

    def test_ask_three_then_fourth_blocked(self) -> None:
        """After 3 clarifications, 4th is blocked."""
        policy = ClarificationPolicy()
        intent = DeckIntent(confidence=0.1)  # Empty intent needs clarification

        # First 3 should be allowed
        assert should_ask_clarification(ClarificationType.FORMAT, intent, policy)
        policy.record_question(ClarificationType.FORMAT)

        assert should_ask_clarification(ClarificationType.COLORS, intent, policy)
        policy.record_question(ClarificationType.COLORS)

        assert should_ask_clarification(ClarificationType.ARCHETYPE, intent, policy)
        policy.record_question(ClarificationType.ARCHETYPE)

        # 4th should be blocked (budget exhausted)
        assert not should_ask_clarification(ClarificationType.TRIBE_OR_THEME, intent, policy)
        assert not should_ask_clarification(ClarificationType.CONSTRAINTS, intent, policy)

    def test_custom_max_questions(self) -> None:
        """Custom max_questions is respected."""
        policy = ClarificationPolicy(max_questions=1)
        intent = DeckIntent(confidence=0.1)

        assert should_ask_clarification(ClarificationType.FORMAT, intent, policy)
        policy.record_question(ClarificationType.FORMAT)

        # Budget of 1 is now exhausted
        assert not should_ask_clarification(ClarificationType.COLORS, intent, policy)


class TestNoDuplicateQuestions:
    """Tests that same clarification type is never asked twice."""

    def test_same_type_not_asked_twice(self) -> None:
        """Same clarification type returns False on second attempt."""
        policy = ClarificationPolicy()
        intent = DeckIntent(confidence=0.1)

        # First time: should ask
        assert should_ask_clarification(ClarificationType.FORMAT, intent, policy)
        policy.record_question(ClarificationType.FORMAT)

        # Second time: should not ask (already asked)
        assert not should_ask_clarification(ClarificationType.FORMAT, intent, policy)

    def test_different_types_can_be_asked(self) -> None:
        """Different clarification types can each be asked once."""
        policy = ClarificationPolicy()
        intent = DeckIntent(confidence=0.1)

        policy.record_question(ClarificationType.FORMAT)

        # Different types should still be askable
        assert should_ask_clarification(ClarificationType.COLORS, intent, policy)
        assert should_ask_clarification(ClarificationType.ARCHETYPE, intent, policy)


class TestProceedAfterBudgetExhausted:
    """Tests that defaults are applied when budget is exhausted."""

    def test_exhausted_budget_applies_defaults(self) -> None:
        """When budget exhausted, resolve_intent applies defaults."""
        policy = ClarificationPolicy()
        policy.record_question(ClarificationType.FORMAT)
        policy.record_question(ClarificationType.COLORS)
        policy.record_question(ClarificationType.ARCHETYPE)

        # Intent missing format and archetype
        intent = DeckIntent(confidence=0.2)

        resolved, should_clarify = resolve_intent_with_policy(intent, policy)

        # Should not clarify (budget exhausted)
        assert should_clarify is False
        # Defaults should be applied
        assert resolved.format == Format.STANDARD
        assert resolved.archetype == Archetype.MIDRANGE

    def test_missing_info_plus_exhausted_equals_defaults(self) -> None:
        """Missing info + exhausted budget → defaults applied."""
        policy = ClarificationPolicy(max_questions=0)  # Already exhausted

        intent = DeckIntent(
            colors=frozenset({"R", "G"}),
            tribe="Dragon",
            confidence=0.3,
        )

        resolved, should_clarify = resolve_intent_with_policy(intent, policy)

        assert should_clarify is False
        assert resolved.format == Format.STANDARD
        assert resolved.archetype == Archetype.MIDRANGE
        # Original fields preserved
        assert resolved.colors == frozenset({"R", "G"})
        assert resolved.tribe == "Dragon"


class TestDeterminism:
    """Tests that same intent + policy → same decision."""

    def test_same_input_same_output(self) -> None:
        """Identical inputs produce identical decisions."""
        intent = DeckIntent(
            colors=frozenset({"R"}),
            confidence=0.3,
        )

        for _ in range(5):
            policy = ClarificationPolicy()
            result = should_ask_clarification(ClarificationType.FORMAT, intent, policy)
            assert result is True  # FORMAT is missing

        for _ in range(5):
            policy = ClarificationPolicy()
            result = should_ask_clarification(ClarificationType.COLORS, intent, policy)
            assert result is False  # COLORS is present

    def test_deterministic_next_clarification(self) -> None:
        """get_next_clarification is deterministic."""
        intent = DeckIntent(confidence=0.1)

        decisions = []
        for _ in range(5):
            policy = ClarificationPolicy()
            decision = get_next_clarification(intent, policy)
            decisions.append(decision)

        # All decisions should be identical
        assert all(
            d.clarification.clarification_type == decisions[0].clarification.clarification_type
            for d in decisions
        )

    def test_deterministic_resolve(self) -> None:
        """resolve_intent_with_policy is deterministic."""
        intent = DeckIntent(
            format=Format.STANDARD,
            colors=frozenset({"U", "W"}),
            archetype=Archetype.CONTROL,
            confidence=0.6,
        )

        results = []
        for _ in range(5):
            policy = ClarificationPolicy()
            resolved, should_clarify = resolve_intent_with_policy(intent, policy)
            results.append((resolved, should_clarify))

        # All results should be identical
        assert all(r == results[0] for r in results)


class TestRegressionValidIntent:
    """Tests that valid/complete intents don't trigger clarifications."""

    def test_complete_intent_no_clarification(self) -> None:
        """Intent with all fields doesn't need clarification."""
        policy = ClarificationPolicy()
        intent = DeckIntent(
            format=Format.STANDARD,
            colors=frozenset({"R", "G"}),
            archetype=Archetype.MIDRANGE,
            tribe="Dragon",
            constraints=frozenset({Constraint.COMPETITIVE}),
            confidence=0.8,
        )

        # No clarification type should be asked
        for ctype in ClarificationType:
            assert not should_ask_clarification(ctype, intent, policy)

    def test_complete_intent_resolves_unchanged(self) -> None:
        """Complete intent resolves without clarification needed."""
        policy = ClarificationPolicy()
        intent = DeckIntent(
            format=Format.HISTORIC,
            colors=frozenset({"B", "G"}),
            archetype=Archetype.MIDRANGE,
            tribe="Elf",
            confidence=0.7,
        )

        resolved, should_clarify = resolve_intent_with_policy(intent, policy)

        # Should not need clarification
        assert should_clarify is False
        # Intent should be essentially unchanged (defaults don't override)
        assert resolved.format == Format.HISTORIC
        assert resolved.archetype == Archetype.MIDRANGE

    def test_partial_intent_may_clarify(self) -> None:
        """Partial intent with budget may request clarification."""
        policy = ClarificationPolicy()
        intent = DeckIntent(
            colors=frozenset({"R"}),
            confidence=0.2,
        )

        resolved, should_clarify = resolve_intent_with_policy(intent, policy)

        # Missing format, archetype — should clarify
        assert should_clarify is True


class TestShouldAskClarification:
    """Tests for should_ask_clarification function."""

    def test_returns_false_if_already_asked(self) -> None:
        """Returns False if clarification type already asked."""
        policy = ClarificationPolicy()
        policy.record_question(ClarificationType.FORMAT)

        intent = DeckIntent(confidence=0.1)

        assert not should_ask_clarification(ClarificationType.FORMAT, intent, policy)

    def test_returns_false_if_budget_exhausted(self) -> None:
        """Returns False if budget is exhausted."""
        policy = ClarificationPolicy(max_questions=0)
        intent = DeckIntent(confidence=0.1)

        assert not should_ask_clarification(ClarificationType.FORMAT, intent, policy)

    def test_returns_false_if_intent_has_info(self) -> None:
        """Returns False if intent already has the information."""
        policy = ClarificationPolicy()
        intent = DeckIntent(
            format=Format.STANDARD,
            confidence=0.3,
        )

        assert not should_ask_clarification(ClarificationType.FORMAT, intent, policy)

    def test_returns_true_when_should_ask(self) -> None:
        """Returns True when all conditions met."""
        policy = ClarificationPolicy()
        intent = DeckIntent(confidence=0.1)

        assert should_ask_clarification(ClarificationType.FORMAT, intent, policy)


class TestEvaluateClarification:
    """Tests for evaluate_clarification function."""

    def test_returns_decision_with_reason(self) -> None:
        """Returns ClarificationDecision with reason."""
        policy = ClarificationPolicy()
        intent = DeckIntent(confidence=0.1)

        decision = evaluate_clarification(ClarificationType.FORMAT, intent, policy)

        assert isinstance(decision, ClarificationDecision)
        assert decision.should_ask is True
        assert decision.reason is not None
        assert decision.clarification is not None

    def test_decision_reason_for_already_asked(self) -> None:
        """Decision reason explains already asked."""
        policy = ClarificationPolicy()
        policy.record_question(ClarificationType.FORMAT)
        intent = DeckIntent(confidence=0.1)

        decision = evaluate_clarification(ClarificationType.FORMAT, intent, policy)

        assert decision.should_ask is False
        assert "Already asked" in decision.reason

    def test_decision_reason_for_exhausted(self) -> None:
        """Decision reason explains budget exhausted."""
        policy = ClarificationPolicy(max_questions=0)
        intent = DeckIntent(confidence=0.1)

        decision = evaluate_clarification(ClarificationType.FORMAT, intent, policy)

        assert decision.should_ask is False
        assert "exhausted" in decision.reason.lower()


class TestGetNextClarification:
    """Tests for get_next_clarification function."""

    def test_priority_order(self) -> None:
        """Clarifications are asked in priority order."""
        policy = ClarificationPolicy()
        intent = DeckIntent(confidence=0.1)

        # First should be FORMAT
        decision = get_next_clarification(intent, policy)
        assert decision is not None
        assert decision.clarification.clarification_type == ClarificationType.FORMAT

    def test_skips_already_present(self) -> None:
        """Skips clarification types already in intent."""
        policy = ClarificationPolicy()
        intent = DeckIntent(
            format=Format.STANDARD,  # Already has format
            confidence=0.2,
        )

        decision = get_next_clarification(intent, policy)
        assert decision is not None
        # Should skip FORMAT and ask COLORS
        assert decision.clarification.clarification_type == ClarificationType.COLORS

    def test_returns_none_when_complete(self) -> None:
        """Returns None when no clarification needed."""
        policy = ClarificationPolicy()
        intent = DeckIntent(
            format=Format.STANDARD,
            colors=frozenset({"R", "G"}),
            archetype=Archetype.MIDRANGE,
            tribe="Dragon",
            constraints=frozenset({Constraint.BUDGET}),
            confidence=0.8,
        )

        decision = get_next_clarification(intent, policy)
        assert decision is None


class TestCreatePolicy:
    """Tests for create_policy factory function."""

    def test_creates_fresh_policy(self) -> None:
        """Creates a new policy with full budget."""
        policy = create_policy()

        assert policy.max_questions == DEFAULT_MAX_CLARIFICATIONS
        assert len(policy.asked_questions) == 0
        assert policy.can_ask() is True


class TestRecordClarification:
    """Tests for record_clarification function."""

    def test_records_and_returns_policy(self) -> None:
        """Records clarification and returns policy for chaining."""
        policy = ClarificationPolicy()

        result = record_clarification(policy, ClarificationType.FORMAT)

        assert result is policy
        assert policy.has_asked(ClarificationType.FORMAT)
