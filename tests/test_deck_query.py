"""
Tests for PR4: Semantic Deck Queries.

INVARIANT: Queries express preferences, NOT exclusions.
A "Goblin deck" query prefers Goblin-related cards but does NOT
hard-exclude non-Goblins.
"""

import pytest

from forgebreaker.models.deck_query import (
    DeckQuery,
    QuerySignal,
    QuerySignalType,
    SignalStrength,
    is_archetype_query,
    is_theme_query,
    is_tribal_query,
)

# =============================================================================
# CORE INVARIANT TESTS: PREFERENCES NOT EXCLUSIONS
# =============================================================================


class TestQuerySemantics:
    """
    Tests proving queries express preferences, not exclusions.
    """

    def test_tribal_query_is_preference(self) -> None:
        """
        Tribal query expresses a preference, not an exclusion.

        The tribe signal has STRONG strength (not REQUIRED),
        meaning it influences scoring but doesn't filter.
        """
        query = DeckQuery.for_tribal("Goblin")

        tribe_signals = query.get_signals(QuerySignalType.TRIBE)
        assert len(tribe_signals) == 1

        tribe_signal = tribe_signals[0]
        assert tribe_signal.value == "Goblin"
        # STRONG, not REQUIRED - this is the key invariant
        assert tribe_signal.strength == SignalStrength.STRONG
        assert not tribe_signal.is_required()

    def test_theme_query_is_preference(self) -> None:
        """
        Theme query expresses a preference, not an exclusion.
        """
        query = DeckQuery.for_theme("sacrifice")

        theme_signals = query.get_signals(QuerySignalType.THEME)
        assert len(theme_signals) == 1

        theme_signal = theme_signals[0]
        assert theme_signal.value == "sacrifice"
        assert theme_signal.strength == SignalStrength.STRONG
        assert not theme_signal.is_required()

    def test_format_is_required(self) -> None:
        """
        Format legality IS required (non-negotiable).

        This is the exception - we can't play illegal cards.
        """
        query = DeckQuery.for_tribal("Goblin", format="standard")

        format_signals = query.get_signals(QuerySignalType.FORMAT)
        assert len(format_signals) == 1

        format_signal = format_signals[0]
        assert format_signal.value == "standard"
        assert format_signal.strength == SignalStrength.REQUIRED
        assert format_signal.is_required()

    def test_get_required_vs_preference_signals(self) -> None:
        """
        Can separate required signals from preference signals.
        """
        query = DeckQuery.for_tribal("Goblin", format="standard", colors=["R"])

        required = query.get_required_signals()
        preferences = query.get_preference_signals()

        # Format is required
        assert len(required) == 1
        assert required[0].signal_type == QuerySignalType.FORMAT

        # Tribe and color are preferences
        assert len(preferences) == 2
        preference_types = {s.signal_type for s in preferences}
        assert QuerySignalType.TRIBE in preference_types
        assert QuerySignalType.COLOR in preference_types


class TestGoblinDeckQuery:
    """
    Tests specifically for Goblin deck queries.

    REQUIREMENT: Goblin deck query includes Goblin-synergy cards.
    """

    def test_goblin_query_has_tribe_signal(self) -> None:
        """
        Goblin deck query has a tribe signal for "Goblin".
        """
        query = DeckQuery.for_tribal("Goblin")

        assert query.tribe == "Goblin"
        assert is_tribal_query(query)

    def test_goblin_query_not_hardcoded(self) -> None:
        """
        Goblin is not special-cased - any tribe works the same way.
        """
        goblin_query = DeckQuery.for_tribal("Goblin")
        dragon_query = DeckQuery.for_tribal("Dragon")
        elf_query = DeckQuery.for_tribal("Elf")

        # All tribal queries have the same structure
        for query, tribe in [
            (goblin_query, "Goblin"),
            (dragon_query, "Dragon"),
            (elf_query, "Elf"),
        ]:
            assert query.tribe == tribe
            assert is_tribal_query(query)
            # Tribe is a preference, not a requirement
            tribe_signal = query.get_signals(QuerySignalType.TRIBE)[0]
            assert not tribe_signal.is_required()

    def test_goblin_with_format_and_colors(self) -> None:
        """
        Goblin query can include format and color constraints.
        """
        query = DeckQuery.for_tribal(
            "Goblin",
            format="standard",
            colors=["R"],
            archetype="aggro",
        )

        assert query.tribe == "Goblin"
        assert query.format == "standard"
        assert "R" in query.colors
        assert query.archetype == "aggro"


class TestNonCreatureArchetypes:
    """
    Tests for non-creature archetype queries.

    REQUIREMENT: Non-creature archetypes are representable.
    """

    def test_burn_theme_query(self) -> None:
        """
        Burn theme is representable as a theme query.
        """
        query = DeckQuery.for_theme("burn", format="standard", colors=["R"])

        assert query.theme == "burn"
        assert is_theme_query(query)
        assert not is_tribal_query(query)  # Not a tribal deck

    def test_mill_theme_query(self) -> None:
        """
        Mill theme is representable.
        """
        query = DeckQuery.for_theme("mill", format="historic", colors=["U", "B"])

        assert query.theme == "mill"
        assert query.colors == frozenset(["U", "B"])

    def test_tokens_theme_query(self) -> None:
        """
        Tokens theme is representable.
        """
        query = DeckQuery.for_theme("tokens", format="standard")

        assert query.theme == "tokens"

    def test_control_archetype_query(self) -> None:
        """
        Control archetype is representable.
        """
        query = DeckQuery.for_archetype("control", format="standard", colors=["U", "W"])

        assert query.archetype == "control"
        assert is_archetype_query(query)
        assert not is_tribal_query(query)

    def test_combo_archetype_query(self) -> None:
        """
        Combo archetype is representable.
        """
        query = DeckQuery.for_archetype("combo", format="historic")

        assert query.archetype == "combo"


class TestQueryFactoryMethods:
    """
    Tests for DeckQuery factory methods.
    """

    def test_for_tribal_basic(self) -> None:
        """
        for_tribal creates a basic tribal query.
        """
        query = DeckQuery.for_tribal("Dragon")

        assert query.tribe == "Dragon"
        assert query.format is None
        assert len(query.colors) == 0

    def test_for_tribal_full(self) -> None:
        """
        for_tribal with all options.
        """
        query = DeckQuery.for_tribal(
            "Vampire",
            format="standard",
            colors=["B", "R"],
            archetype="aggro",
        )

        assert query.tribe == "Vampire"
        assert query.format == "standard"
        assert query.colors == frozenset(["B", "R"])
        assert query.archetype == "aggro"

    def test_for_theme_basic(self) -> None:
        """
        for_theme creates a basic theme query.
        """
        query = DeckQuery.for_theme("sacrifice")

        assert query.theme == "sacrifice"
        assert query.tribe is None  # Not tribal

    def test_for_archetype_with_tribe(self) -> None:
        """
        for_archetype can include a tribe preference.
        """
        query = DeckQuery.for_archetype("aggro", format="standard", tribe="Goblin")

        assert query.archetype == "aggro"
        assert query.tribe == "Goblin"
        # Archetype is primary (STRONG), tribe is secondary (MODERATE)
        archetype_signal = query.get_signals(QuerySignalType.ARCHETYPE)[0]
        tribe_signal = query.get_signals(QuerySignalType.TRIBE)[0]
        assert archetype_signal.strength == SignalStrength.STRONG
        assert tribe_signal.strength == SignalStrength.MODERATE

    def test_empty_query(self) -> None:
        """
        Empty query has no signals.
        """
        query = DeckQuery.empty()

        assert len(query.signals) == 0
        assert query.tribe is None
        assert query.theme is None
        assert query.format is None


class TestSignalStrength:
    """
    Tests for signal strength semantics.
    """

    def test_required_strength_is_exclusionary(self) -> None:
        """
        REQUIRED strength signals are exclusionary.
        """
        signal = QuerySignal(
            signal_type=QuerySignalType.FORMAT,
            value="standard",
            strength=SignalStrength.REQUIRED,
        )

        assert signal.is_required()

    def test_strong_strength_is_preference(self) -> None:
        """
        STRONG strength signals are preferences (scoring only).
        """
        signal = QuerySignal(
            signal_type=QuerySignalType.TRIBE,
            value="Goblin",
            strength=SignalStrength.STRONG,
        )

        assert not signal.is_required()

    def test_moderate_strength_is_preference(self) -> None:
        """
        MODERATE strength signals are preferences.
        """
        signal = QuerySignal(
            signal_type=QuerySignalType.ARCHETYPE,
            value="aggro",
            strength=SignalStrength.MODERATE,
        )

        assert not signal.is_required()

    def test_weak_strength_is_preference(self) -> None:
        """
        WEAK strength signals are preferences.
        """
        signal = QuerySignal(
            signal_type=QuerySignalType.KEYWORD,
            value="haste",
            strength=SignalStrength.WEAK,
        )

        assert not signal.is_required()


class TestQueryHelperFunctions:
    """
    Tests for query classification helper functions.
    """

    def test_is_tribal_query(self) -> None:
        """
        is_tribal_query correctly identifies tribal queries.
        """
        tribal = DeckQuery.for_tribal("Goblin")
        theme = DeckQuery.for_theme("sacrifice")
        archetype = DeckQuery.for_archetype("aggro")

        assert is_tribal_query(tribal)
        assert not is_tribal_query(theme)
        assert not is_tribal_query(archetype)

    def test_is_theme_query(self) -> None:
        """
        is_theme_query correctly identifies theme queries.
        """
        tribal = DeckQuery.for_tribal("Goblin")
        theme = DeckQuery.for_theme("sacrifice")
        archetype = DeckQuery.for_archetype("aggro")

        assert not is_theme_query(tribal)
        assert is_theme_query(theme)
        assert not is_theme_query(archetype)

    def test_is_archetype_query(self) -> None:
        """
        is_archetype_query correctly identifies archetype queries.
        """
        tribal = DeckQuery.for_tribal("Goblin")
        theme = DeckQuery.for_theme("sacrifice")
        archetype = DeckQuery.for_archetype("aggro")

        assert not is_archetype_query(tribal)
        assert not is_archetype_query(theme)
        assert is_archetype_query(archetype)


class TestQueryImmutability:
    """
    Tests for query immutability.
    """

    def test_query_is_frozen(self) -> None:
        """
        DeckQuery is immutable (frozen dataclass).
        """
        query = DeckQuery.for_tribal("Goblin")

        with pytest.raises(AttributeError):
            query.signals = ()  # type: ignore[misc]

    def test_signal_is_frozen(self) -> None:
        """
        QuerySignal is immutable (frozen dataclass).
        """
        signal = QuerySignal(
            signal_type=QuerySignalType.TRIBE,
            value="Goblin",
            strength=SignalStrength.STRONG,
        )

        with pytest.raises(AttributeError):
            signal.value = "Dragon"  # type: ignore[misc]
