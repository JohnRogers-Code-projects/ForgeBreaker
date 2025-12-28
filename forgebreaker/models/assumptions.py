"""
Deck assumption models.

Assumptions are PLAYER BELIEFS about what a deck needs to function.
They are hypotheses, not facts. They may be wrong.

The system surfaces characteristics of a decklist to help players
articulate and examine their own beliefs. It does not claim these
beliefs are correct or that the deck will perform as expected.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AssumptionCategory(str, Enum):
    """Categories of deck assumptions."""

    MANA_CURVE = "mana_curve"
    DRAW_CONSISTENCY = "draw_consistency"
    KEY_CARDS = "key_cards"
    INTERACTION_TIMING = "interaction_timing"


class AssumptionHealth(str, Enum):
    """
    How a belief compares to conventional baselines.

    This is NOT a prediction of performance. It indicates whether
    the deck's characteristics match common patterns for the archetype.
    Deviating from convention may be intentional and correct.
    """

    HEALTHY = "healthy"  # Matches conventional baseline
    WARNING = "warning"  # Differs from convention
    CRITICAL = "critical"  # Differs significantly from convention


@dataclass
class DeckAssumption:
    """
    A single belief about what a deck needs to function.

    This represents a hypothesis the player holds (or should consider)
    about how the deck operates. It is not a prediction or guarantee.

    Attributes:
        name: Human-readable name for this belief
        category: Type of assumption
        description: What this belief is about
        observed_value: What the decklist shows (a fact about the list)
        typical_range: What convention suggests for this archetype (not truth)
        health: How this compares to convention (not quality)
        explanation: Why a player might care about this
        adjustable: Whether this can be stress-tested
    """

    name: str
    category: AssumptionCategory
    description: str
    observed_value: Any  # Renamed from current_value - this is observable fact
    typical_range: tuple[float, float]  # Renamed from expected_range - convention, not truth
    health: AssumptionHealth
    explanation: str
    adjustable: bool = True

    def is_within_typical(self) -> bool:
        """Check if observed value is within typical range for the archetype."""
        if isinstance(self.observed_value, int | float):
            return self.typical_range[0] <= self.observed_value <= self.typical_range[1]
        return True


@dataclass
class DeckAssumptionSet:
    """
    A collection of beliefs about what a deck needs to function.

    These are hypotheses for the player to examine, not system predictions.
    The fragility score indicates how much the deck deviates from convention,
    NOT how likely it is to fail.

    Attributes:
        deck_name: Name of the deck
        archetype: Archetype used for baseline comparison
        assumptions: List of individual beliefs to examine
        overall_fragility: How much the deck deviates from convention (0-1)
        fragility_explanation: What the deviation means (not a prediction)
    """

    deck_name: str
    archetype: str
    assumptions: list[DeckAssumption] = field(default_factory=list)
    overall_fragility: float = 0.0
    fragility_explanation: str = ""

    def get_by_category(self, category: AssumptionCategory) -> list[DeckAssumption]:
        """Get all assumptions in a category."""
        return [a for a in self.assumptions if a.category == category]

    def get_warnings(self) -> list[DeckAssumption]:
        """Get assumptions that differ from convention."""
        return [
            a
            for a in self.assumptions
            if a.health in (AssumptionHealth.WARNING, AssumptionHealth.CRITICAL)
        ]

    def get_critical(self) -> list[DeckAssumption]:
        """Get assumptions that differ significantly from convention."""
        return [a for a in self.assumptions if a.health == AssumptionHealth.CRITICAL]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "deck_name": self.deck_name,
            "archetype": self.archetype,
            "assumptions": [
                {
                    "name": a.name,
                    "category": a.category.value,
                    "description": a.description,
                    "observed_value": a.observed_value,
                    "typical_range": list(a.typical_range),
                    "health": a.health.value,
                    "explanation": a.explanation,
                    "adjustable": a.adjustable,
                }
                for a in self.assumptions
            ],
            "overall_fragility": self.overall_fragility,
            "fragility_explanation": self.fragility_explanation,
        }
