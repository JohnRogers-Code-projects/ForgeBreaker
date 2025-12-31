"""
Clarification Service — Deterministic Ask-vs-Assume Logic.

This module provides the decision logic for when to ask clarifying
questions versus when to proceed with defaults.

INVARIANT: Same intent + policy → same decision (deterministic)
INVARIANT: Budget exhausted → always proceed with defaults
INVARIANT: Already asked → never ask again
"""

from forgebreaker.models.clarification import (
    ClarificationDecision,
    ClarificationPolicy,
    ClarificationRequest,
    ClarificationType,
)
from forgebreaker.models.intent import (
    DeckIntent,
)
from forgebreaker.services.intent_inference import apply_intent_defaults


def _intent_has_format(intent: DeckIntent) -> bool:
    """Check if intent has format specified."""
    return intent.format is not None


def _intent_has_colors(intent: DeckIntent) -> bool:
    """Check if intent has colors specified."""
    return intent.colors is not None and len(intent.colors) > 0


def _intent_has_archetype(intent: DeckIntent) -> bool:
    """Check if intent has archetype specified."""
    return intent.archetype is not None


def _intent_has_tribe_or_theme(intent: DeckIntent) -> bool:
    """Check if intent has tribe or theme specified."""
    return intent.tribe is not None or intent.theme is not None


def _intent_has_constraints(intent: DeckIntent) -> bool:
    """Check if intent has constraints specified."""
    return len(intent.constraints) > 0


def _intent_needs_clarification(
    clarification_type: ClarificationType,
    intent: DeckIntent,
) -> bool:
    """
    Check if intent is missing information for this clarification type.

    Returns True if the intent lacks information that could be clarified.
    """
    match clarification_type:
        case ClarificationType.FORMAT:
            return not _intent_has_format(intent)
        case ClarificationType.COLORS:
            return not _intent_has_colors(intent)
        case ClarificationType.ARCHETYPE:
            return not _intent_has_archetype(intent)
        case ClarificationType.TRIBE_OR_THEME:
            return not _intent_has_tribe_or_theme(intent)
        case ClarificationType.CONSTRAINTS:
            # Constraints are optional add-ons — never need clarification
            return False
    return False


def should_ask_clarification(
    clarification_type: ClarificationType,
    intent: DeckIntent,
    policy: ClarificationPolicy,
) -> bool:
    """
    Determine if a clarification should be asked.

    Rules (authoritative, in order):
    1. If clarification_type already asked → False
    2. If budget exhausted → False
    3. If intent already has sufficient information → False
    4. Otherwise → True

    Args:
        clarification_type: The type of clarification to potentially ask
        intent: The current inferred intent
        policy: The clarification policy tracking budget

    Returns:
        True if clarification should be asked, False otherwise
    """
    # Rule 1: Already asked this type
    if policy.has_asked(clarification_type):
        return False

    # Rule 2: Budget exhausted
    if policy.is_exhausted():
        return False

    # Rule 3 & 4: Ask only if clarification is actually needed
    return _intent_needs_clarification(clarification_type, intent)


def evaluate_clarification(
    clarification_type: ClarificationType,
    intent: DeckIntent,
    policy: ClarificationPolicy,
) -> ClarificationDecision:
    """
    Evaluate whether to ask a clarification and return a decision object.

    This is a richer version of should_ask_clarification that includes
    the reason for the decision.

    Args:
        clarification_type: The type of clarification to potentially ask
        intent: The current inferred intent
        policy: The clarification policy tracking budget

    Returns:
        ClarificationDecision with should_ask, reason, and optional request
    """
    # Rule 1: Already asked
    if policy.has_asked(clarification_type):
        return ClarificationDecision(
            should_ask=False,
            reason=f"Already asked {clarification_type.value}",
        )

    # Rule 2: Budget exhausted
    if policy.is_exhausted():
        return ClarificationDecision(
            should_ask=False,
            reason="Clarification budget exhausted",
        )

    # Rule 3: Intent already has info
    if not _intent_needs_clarification(clarification_type, intent):
        return ClarificationDecision(
            should_ask=False,
            reason=f"Intent already has {clarification_type.value}",
        )

    # Rule 4: Should ask
    request = ClarificationRequest(
        clarification_type=clarification_type,
        question_key=f"ask_{clarification_type.value}",
    )
    return ClarificationDecision(
        should_ask=True,
        reason="Missing information, budget available",
        clarification=request,
    )


def get_next_clarification(
    intent: DeckIntent,
    policy: ClarificationPolicy,
) -> ClarificationDecision | None:
    """
    Get the next clarification to ask, if any.

    Evaluates clarification types in priority order and returns
    the first one that should be asked.

    Priority order:
    1. FORMAT (most impactful for card legality)
    2. COLORS (narrows card pool significantly)
    3. ARCHETYPE (affects deck structure)
    4. TRIBE_OR_THEME (specific build-around)
    5. CONSTRAINTS (optional preferences)

    Args:
        intent: The current inferred intent
        policy: The clarification policy tracking budget

    Returns:
        ClarificationDecision if a clarification should be asked, None otherwise
    """
    priority_order = [
        ClarificationType.FORMAT,
        ClarificationType.COLORS,
        ClarificationType.ARCHETYPE,
        ClarificationType.TRIBE_OR_THEME,
        ClarificationType.CONSTRAINTS,
    ]

    for clarification_type in priority_order:
        decision = evaluate_clarification(clarification_type, intent, policy)
        if decision.should_ask:
            return decision

    return None


def resolve_intent_with_policy(
    intent: DeckIntent,
    policy: ClarificationPolicy,
) -> tuple[DeckIntent, bool]:
    """
    Resolve an intent, applying defaults if no clarification should be asked.

    This is the single decision point for ask-vs-assume logic.

    Args:
        intent: The inferred intent (may have None fields)
        policy: The clarification policy tracking budget

    Returns:
        Tuple of (resolved_intent, should_clarify)
        - If should_clarify is True, intent is returned unchanged
        - If should_clarify is False, intent has defaults applied
    """
    next_clarification = get_next_clarification(intent, policy)

    if next_clarification is not None:
        # There's a clarification to ask
        return (intent, True)
    else:
        # No clarification needed or budget exhausted — apply defaults
        return (apply_intent_defaults(intent), False)


def create_policy() -> ClarificationPolicy:
    """
    Create a new clarification policy for a request.

    Each request gets a fresh policy with full budget.
    """
    return ClarificationPolicy()


def record_clarification(
    policy: ClarificationPolicy,
    clarification_type: ClarificationType,
) -> ClarificationPolicy:
    """
    Record that a clarification was asked and return updated policy.

    Note: This mutates the policy in place and returns it for chaining.

    Args:
        policy: The policy to update
        clarification_type: The type of clarification that was asked

    Returns:
        The same policy object (mutated)
    """
    policy.record_question(clarification_type)
    return policy
