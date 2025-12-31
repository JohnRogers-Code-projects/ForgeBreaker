"""
Deck Query - semantic representation of deck building requests.

INVARIANT: Queries express preferences, NOT exclusions.
A "Goblin deck" query prefers Goblin-related cards but does not
hard-exclude non-Goblins.

This model is the foundation for scored candidate pools (PR5).
"""

from dataclasses import dataclass, field
from enum import Enum


class QuerySignalType(str, Enum):
    """Types of signals that can be expressed in a query."""

    # Creature type preference (e.g., "Goblin", "Dragon", "Elf")
    TRIBE = "tribe"

    # Mechanical theme (e.g., "sacrifice", "graveyard", "tokens")
    THEME = "theme"

    # Color preference (e.g., "red", "blue-black")
    COLOR = "color"

    # Archetype preference (e.g., "aggro", "control", "combo")
    ARCHETYPE = "archetype"

    # Format requirement (e.g., "standard", "historic")
    FORMAT = "format"

    # Keyword ability (e.g., "flying", "trample", "haste")
    KEYWORD = "keyword"

    # Card type preference (e.g., "creature", "instant", "enchantment")
    CARD_TYPE = "card_type"


class SignalStrength(str, Enum):
    """
    How strongly a signal should influence scoring.

    REQUIRED: Hard requirement (equivalent to filter)
    STRONG: Major influence on scoring
    MODERATE: Moderate influence on scoring
    WEAK: Minor influence on scoring
    """

    REQUIRED = "required"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass(frozen=True, slots=True)
class QuerySignal:
    """
    A single signal in a deck query.

    Signals express preferences, not exclusions. A card that doesn't
    match a signal is scored lower, not excluded.

    Exception: REQUIRED strength signals ARE exclusionary for safety
    (e.g., format legality is non-negotiable).
    """

    signal_type: QuerySignalType
    value: str
    strength: SignalStrength = SignalStrength.STRONG

    def is_required(self) -> bool:
        """Check if this signal is a hard requirement."""
        return self.strength == SignalStrength.REQUIRED


@dataclass(frozen=True, slots=True)
class DeckQuery:
    """
    Semantic representation of a deck building request.

    INVARIANT: Queries express preferences, NOT exclusions.

    A DeckQuery captures the user's intent in terms of:
    - What they want (tribe, theme, archetype)
    - How strongly they want it (signal strength)
    - What's non-negotiable (format legality)

    Usage:
        query = DeckQuery.for_tribal("Goblin", format="standard")
        query = DeckQuery.for_theme("sacrifice", colors=["B", "R"])
        query = DeckQuery.for_archetype("aggro", tribe="Goblin")

    This model does NOT perform filtering - that's PR5's job.
    It only represents the semantic intent.
    """

    signals: tuple[QuerySignal, ...] = field(default_factory=tuple)

    # Convenience accessors for common signal types
    @property
    def tribe(self) -> str | None:
        """Get the tribe signal value, if any."""
        for signal in self.signals:
            if signal.signal_type == QuerySignalType.TRIBE:
                return signal.value
        return None

    @property
    def theme(self) -> str | None:
        """Get the theme signal value, if any."""
        for signal in self.signals:
            if signal.signal_type == QuerySignalType.THEME:
                return signal.value
        return None

    @property
    def colors(self) -> frozenset[str]:
        """Get all color signals as a frozenset."""
        colors = set()
        for signal in self.signals:
            if signal.signal_type == QuerySignalType.COLOR:
                colors.add(signal.value.upper())
        return frozenset(colors)

    @property
    def format(self) -> str | None:
        """Get the format signal value, if any."""
        for signal in self.signals:
            if signal.signal_type == QuerySignalType.FORMAT:
                return signal.value
        return None

    @property
    def archetype(self) -> str | None:
        """Get the archetype signal value, if any."""
        for signal in self.signals:
            if signal.signal_type == QuerySignalType.ARCHETYPE:
                return signal.value
        return None

    def has_signal(self, signal_type: QuerySignalType) -> bool:
        """Check if query has a signal of the given type."""
        return any(s.signal_type == signal_type for s in self.signals)

    def get_signals(self, signal_type: QuerySignalType) -> list[QuerySignal]:
        """Get all signals of a given type."""
        return [s for s in self.signals if s.signal_type == signal_type]

    def get_required_signals(self) -> list[QuerySignal]:
        """Get all required (non-negotiable) signals."""
        return [s for s in self.signals if s.is_required()]

    def get_preference_signals(self) -> list[QuerySignal]:
        """Get all preference (non-required) signals."""
        return [s for s in self.signals if not s.is_required()]

    # Factory methods for common query patterns

    @classmethod
    def for_tribal(
        cls,
        tribe: str,
        *,
        format: str | None = None,
        colors: list[str] | None = None,
        archetype: str | None = None,
    ) -> "DeckQuery":
        """
        Create a tribal deck query.

        Example: DeckQuery.for_tribal("Goblin", format="standard", colors=["R"])

        The tribe is a STRONG preference (not exclusionary).
        Goblin-synergy cards (e.g., "Goblin Bombardment") are included
        even if they're not Goblins themselves.
        """
        signals = [
            QuerySignal(
                signal_type=QuerySignalType.TRIBE,
                value=tribe,
                strength=SignalStrength.STRONG,
            )
        ]

        if format:
            signals.append(
                QuerySignal(
                    signal_type=QuerySignalType.FORMAT,
                    value=format,
                    strength=SignalStrength.REQUIRED,  # Format is non-negotiable
                )
            )

        if colors:
            for color in colors:
                signals.append(
                    QuerySignal(
                        signal_type=QuerySignalType.COLOR,
                        value=color.upper(),
                        strength=SignalStrength.STRONG,
                    )
                )

        if archetype:
            signals.append(
                QuerySignal(
                    signal_type=QuerySignalType.ARCHETYPE,
                    value=archetype,
                    strength=SignalStrength.MODERATE,
                )
            )

        return cls(signals=tuple(signals))

    @classmethod
    def for_theme(
        cls,
        theme: str,
        *,
        format: str | None = None,
        colors: list[str] | None = None,
        archetype: str | None = None,
    ) -> "DeckQuery":
        """
        Create a theme-based deck query.

        Example: DeckQuery.for_theme("sacrifice", format="historic", colors=["B", "R"])

        Works for non-creature archetypes like "burn", "mill", "tokens".
        """
        signals = [
            QuerySignal(
                signal_type=QuerySignalType.THEME,
                value=theme,
                strength=SignalStrength.STRONG,
            )
        ]

        if format:
            signals.append(
                QuerySignal(
                    signal_type=QuerySignalType.FORMAT,
                    value=format,
                    strength=SignalStrength.REQUIRED,
                )
            )

        if colors:
            for color in colors:
                signals.append(
                    QuerySignal(
                        signal_type=QuerySignalType.COLOR,
                        value=color.upper(),
                        strength=SignalStrength.STRONG,
                    )
                )

        if archetype:
            signals.append(
                QuerySignal(
                    signal_type=QuerySignalType.ARCHETYPE,
                    value=archetype,
                    strength=SignalStrength.MODERATE,
                )
            )

        return cls(signals=tuple(signals))

    @classmethod
    def for_archetype(
        cls,
        archetype: str,
        *,
        format: str | None = None,
        colors: list[str] | None = None,
        tribe: str | None = None,
    ) -> "DeckQuery":
        """
        Create an archetype-based deck query.

        Example: DeckQuery.for_archetype("aggro", format="standard", tribe="Goblin")
        """
        signals = [
            QuerySignal(
                signal_type=QuerySignalType.ARCHETYPE,
                value=archetype,
                strength=SignalStrength.STRONG,
            )
        ]

        if format:
            signals.append(
                QuerySignal(
                    signal_type=QuerySignalType.FORMAT,
                    value=format,
                    strength=SignalStrength.REQUIRED,
                )
            )

        if colors:
            for color in colors:
                signals.append(
                    QuerySignal(
                        signal_type=QuerySignalType.COLOR,
                        value=color.upper(),
                        strength=SignalStrength.STRONG,
                    )
                )

        if tribe:
            signals.append(
                QuerySignal(
                    signal_type=QuerySignalType.TRIBE,
                    value=tribe,
                    strength=SignalStrength.MODERATE,
                )
            )

        return cls(signals=tuple(signals))

    @classmethod
    def empty(cls) -> "DeckQuery":
        """Create an empty query (no preferences)."""
        return cls(signals=())


def is_tribal_query(query: DeckQuery) -> bool:
    """Check if query is primarily tribal."""
    return query.has_signal(QuerySignalType.TRIBE)


def is_theme_query(query: DeckQuery) -> bool:
    """Check if query is primarily theme-based."""
    return query.has_signal(QuerySignalType.THEME)


def is_archetype_query(query: DeckQuery) -> bool:
    """Check if query is primarily archetype-based."""
    return query.has_signal(QuerySignalType.ARCHETYPE)
