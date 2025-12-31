"""
Deck Intent — Domain Object for User Request Representation.

This module defines the formal intent model that represents what a user
is asking for when requesting a deck. This is a pure data structure
with no behavior attached.

IMPORTANT: This is scaffolding only. Intent is parsed and stored but
not yet used to alter execution paths.
"""

from dataclasses import dataclass
from enum import Enum


class Format(str, Enum):
    """Supported MTG formats."""

    STANDARD = "standard"
    HISTORIC = "historic"
    EXPLORER = "explorer"
    PIONEER = "pioneer"
    MODERN = "modern"
    LEGACY = "legacy"
    VINTAGE = "vintage"
    BRAWL = "brawl"
    TIMELESS = "timeless"


class Archetype(str, Enum):
    """Common deck archetypes."""

    AGGRO = "aggro"
    MIDRANGE = "midrange"
    CONTROL = "control"
    COMBO = "combo"
    TEMPO = "tempo"
    RAMP = "ramp"


class Constraint(str, Enum):
    """Deck-building constraints."""

    BUDGET = "budget"
    COMPETITIVE = "competitive"
    CASUAL = "casual"
    SINGLETON = "singleton"


# Standard MTG color codes
COLOR_WHITE = "W"
COLOR_BLUE = "U"
COLOR_BLACK = "B"
COLOR_RED = "R"
COLOR_GREEN = "G"

ALL_COLORS = frozenset({COLOR_WHITE, COLOR_BLUE, COLOR_BLACK, COLOR_RED, COLOR_GREEN})


@dataclass(frozen=True)
class DeckIntent:
    """
    Represents the inferred intent from a user's deck request.

    All fields are optional except confidence. This allows partial
    inference where some aspects are clear and others are ambiguous.

    Attributes:
        format: The MTG format (Standard, Historic, etc.)
        colors: Set of color codes (W, U, B, R, G)
        archetype: Deck archetype (aggro, midrange, control, etc.)
        tribe: Creature type if tribal deck requested
        theme: Non-tribal theme (e.g., "sacrifice", "graveyard")
        constraints: Additional constraints (budget, competitive, etc.)
        confidence: Confidence score in [0.0, 1.0]
    """

    format: Format | None = None
    colors: frozenset[str] | None = None
    archetype: Archetype | None = None
    tribe: str | None = None
    theme: str | None = None
    constraints: frozenset[Constraint] = frozenset()
    confidence: float = 0.0

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")

    def with_defaults(
        self,
        format: Format | None = None,
        archetype: Archetype | None = None,
    ) -> "DeckIntent":
        """
        Return a new DeckIntent with defaults applied for None fields.

        Does not modify fields that already have values.
        """
        return DeckIntent(
            format=self.format if self.format is not None else format,
            colors=self.colors,
            archetype=self.archetype if self.archetype is not None else archetype,
            tribe=self.tribe,
            theme=self.theme,
            constraints=self.constraints,
            confidence=self.confidence,
        )
