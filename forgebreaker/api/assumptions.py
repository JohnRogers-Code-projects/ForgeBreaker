"""
Assumptions API endpoint.

Surfaces deck characteristics for players to examine their beliefs about
what the deck needs to function. These are hypotheses for inspection,
not system predictions or performance guarantees.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from forgebreaker.analysis.assumptions import surface_assumptions
from forgebreaker.db import get_meta_deck, meta_deck_to_model
from forgebreaker.db.database import get_session
from forgebreaker.services.card_database import get_card_database

router = APIRouter(prefix="/assumptions", tags=["assumptions"])


class AssumptionResponse(BaseModel):
    """
    A single belief about what a deck needs to function.

    observed_value is a fact about the decklist.
    typical_range reflects convention for the archetype (not a prescription).
    """

    name: str
    category: str
    description: str
    observed_value: Any  # What the decklist shows (fact)
    typical_range: list[float]  # Convention for archetype (not prescription)
    health: str
    explanation: str
    adjustable: bool


class AssumptionSetResponse(BaseModel):
    """
    A collection of beliefs about what a deck needs to function.

    These are hypotheses for players to examine, not system predictions.
    The fragility score indicates deviation from convention, not likelihood of failure.
    """

    deck_name: str
    archetype: str
    assumptions: list[AssumptionResponse] = Field(default_factory=list)
    overall_fragility: float = Field(ge=0.0, le=1.0)
    fragility_explanation: str


@router.get("/{user_id}/{format_name}/{deck_name}", response_model=AssumptionSetResponse)
async def get_deck_assumptions(
    user_id: str,  # noqa: ARG001  Required for route pattern
    format_name: str,
    deck_name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssumptionSetResponse:
    """
    Surface observable characteristics of a deck for player examination.

    Returns beliefs to examine about:
    - Mana curve (what the deck appears to need)
    - Draw consistency (how the deck finds cards)
    - Key card dependencies (what the deck relies on)
    - Interaction timing (when the deck needs to respond)

    The fragility score indicates deviation from convention, NOT prediction of failure.
    Deviating from convention may be intentional and correct.
    """
    # Get the deck
    db_deck = await get_meta_deck(session, deck_name, format_name)
    if db_deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deck '{deck_name}' not found in format '{format_name}'",
        )

    deck = meta_deck_to_model(db_deck)

    # Load card database for analysis
    try:
        card_db = get_card_database()
    except FileNotFoundError:
        # Provide analysis with empty card db (limited info)
        card_db = {}

    # Surface assumptions for player examination
    assumption_set = surface_assumptions(deck, card_db)

    # Build response
    return AssumptionSetResponse(
        deck_name=assumption_set.deck_name,
        archetype=assumption_set.archetype,
        assumptions=[
            AssumptionResponse(
                name=a.name,
                category=a.category.value,
                description=a.description,
                observed_value=a.observed_value,
                typical_range=list(a.typical_range),
                health=a.health.value,
                explanation=a.explanation,
                adjustable=a.adjustable,
            )
            for a in assumption_set.assumptions
        ],
        overall_fragility=assumption_set.overall_fragility,
        fragility_explanation=assumption_set.fragility_explanation,
    )
