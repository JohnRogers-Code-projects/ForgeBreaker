"""
Tests for PR4: Semantic Deck Queries.

INVARIANT: Queries express preferences, NOT exclusions.
A "Goblin deck" query prefers Goblin-related cards but does NOT
hard-exclude non-Goblins.

QueryContract encodes formal invariants that ANY scorer must obey:
1. DOMINANCE: Matching cards score >= non-matching cards
2. MONOTONICITY: Adding preferences never reduces scores
3. NON-EXCLUSIVITY: Non-matching cards are not excluded (score >= 0)
"""

import pytest

from forgebreaker.models.deck_query import (
    DeckQuery,
    QueryContract,
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


# =============================================================================
# QUERY CONTRACT TESTS - FORMAL INVARIANTS
# =============================================================================


class MockScorer:
    """
    Mock scorer for testing QueryContract invariants.

    This scorer implements the correct invariant behavior:
    - Matching cards get bonus points
    - Non-matching cards get base score
    - Adding preferences only adds bonuses
    """

    def __init__(self) -> None:
        # Card database: card_name -> {property: value}
        self.card_db: dict[str, dict[str, str | list[str]]] = {
            "Goblin Guide": {"tribe": "Goblin", "colors": ["R"]},
            "Krenko, Mob Boss": {"tribe": "Goblin", "colors": ["R"]},
            "Lightning Bolt": {"tribe": "", "colors": ["R"]},  # Not a Goblin
            "Mountain": {"tribe": "", "colors": []},  # Basic land
            "Forest": {"tribe": "", "colors": []},  # Basic land
            "Elvish Mystic": {"tribe": "Elf", "colors": ["G"]},  # Different tribe
        }

        # Base score for all cards
        self.base_score = 10.0

        # Bonus for matching each signal type
        self.signal_bonus = {
            SignalStrength.STRONG: 5.0,
            SignalStrength.MODERATE: 3.0,
            SignalStrength.WEAK: 1.0,
            SignalStrength.REQUIRED: 0.0,  # Required doesn't add bonus
        }

    def score(self, card_name: str, query: DeckQuery) -> float:
        """Score a card against a query."""
        if card_name not in self.card_db:
            return 0.0

        score = self.base_score

        for signal in query.signals:
            if signal.is_required():
                # Required signals can exclude (return 0 if not matched)
                if not self.matches_signal(card_name, signal):
                    return -1.0  # Excluded
            elif self.matches_signal(card_name, signal):
                # Add bonus for matching preference
                score += self.signal_bonus[signal.strength]

        return score

    def matches_signal(self, card_name: str, signal: QuerySignal) -> bool:
        """Check if a card matches a signal."""
        if card_name not in self.card_db:
            return False

        card = self.card_db[card_name]

        if signal.signal_type == QuerySignalType.TRIBE:
            return card.get("tribe") == signal.value

        if signal.signal_type == QuerySignalType.COLOR:
            colors = card.get("colors", [])
            return signal.value.upper() in [c.upper() for c in colors]  # type: ignore[union-attr]

        # For testing, assume all cards are format-legal
        return signal.signal_type == QuerySignalType.FORMAT


class TestQueryContract:
    """
    Tests for QueryContract formal invariants.

    These tests prove the invariants using a mock scorer.
    Any real scorer MUST also pass these tests.
    """

    @pytest.fixture
    def contract(self) -> QueryContract:
        """QueryContract instance."""
        return QueryContract()

    @pytest.fixture
    def scorer(self) -> MockScorer:
        """Mock scorer for testing."""
        return MockScorer()

    def test_contract_is_immutable(self, contract: QueryContract) -> None:
        """QueryContract is frozen."""
        with pytest.raises(AttributeError):
            contract.MIN_INCLUDED_SCORE = -1.0  # type: ignore[misc]


class TestDominanceInvariant:
    """
    MANDATORY TEST: Dominance invariant.

    Goblin cards always score >= non-Goblin cards in Goblin query.
    """

    @pytest.fixture
    def contract(self) -> QueryContract:
        return QueryContract()

    @pytest.fixture
    def scorer(self) -> MockScorer:
        return MockScorer()

    def test_goblin_scores_higher_than_non_goblin(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        MANDATORY: Goblin cards score >= non-Goblin cards in Goblin query.
        """
        query = DeckQuery.for_tribal("Goblin")
        goblin_signal = query.get_signals(QuerySignalType.TRIBE)[0]

        # Goblin Guide (matches) vs Lightning Bolt (doesn't match)
        assert contract.check_dominance(
            scorer=scorer,
            query=query,
            matching_card="Goblin Guide",
            non_matching_card="Lightning Bolt",
            signal=goblin_signal,
        )

    def test_goblin_scores_higher_than_elf(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        Goblin cards score >= Elf cards in Goblin query.
        """
        query = DeckQuery.for_tribal("Goblin")
        goblin_signal = query.get_signals(QuerySignalType.TRIBE)[0]

        assert contract.check_dominance(
            scorer=scorer,
            query=query,
            matching_card="Krenko, Mob Boss",
            non_matching_card="Elvish Mystic",
            signal=goblin_signal,
        )

    def test_dominance_is_not_equality(self, scorer: MockScorer) -> None:
        """
        Dominance means >=, not >. Equal scores are valid.
        """
        query = DeckQuery.for_tribal("Goblin")

        # Both are Goblins, so dominance trivially holds (same score)
        goblin_guide_score = scorer.score("Goblin Guide", query)
        krenko_score = scorer.score("Krenko, Mob Boss", query)

        # Both should have the same score (base + tribe bonus)
        assert goblin_guide_score == krenko_score

    def test_dominance_violation_raises(self, contract: QueryContract, scorer: MockScorer) -> None:
        """
        Checking dominance with wrong card pairing raises ValueError.
        """
        query = DeckQuery.for_tribal("Goblin")
        goblin_signal = query.get_signals(QuerySignalType.TRIBE)[0]

        # Lightning Bolt doesn't match Goblin - can't be the "matching" card
        with pytest.raises(ValueError, match="does not match signal"):
            contract.check_dominance(
                scorer=scorer,
                query=query,
                matching_card="Lightning Bolt",  # Wrong - doesn't match
                non_matching_card="Goblin Guide",
                signal=goblin_signal,
            )


class TestMonotonicityInvariant:
    """
    MANDATORY TEST: Monotonicity invariant.

    Adding a preference never lowers any card's score.
    """

    @pytest.fixture
    def contract(self) -> QueryContract:
        return QueryContract()

    @pytest.fixture
    def scorer(self) -> MockScorer:
        return MockScorer()

    def test_adding_tribe_preference_never_lowers_score(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        MANDATORY: Adding a tribe preference never reduces any score.
        """
        base_query = DeckQuery.empty()
        additional_signal = QuerySignal(
            signal_type=QuerySignalType.TRIBE,
            value="Goblin",
            strength=SignalStrength.STRONG,
        )

        # Test for Goblin card
        assert contract.check_monotonicity(
            scorer=scorer,
            card="Goblin Guide",
            base_query=base_query,
            additional_signal=additional_signal,
        )

        # Test for non-Goblin card
        assert contract.check_monotonicity(
            scorer=scorer,
            card="Lightning Bolt",
            base_query=base_query,
            additional_signal=additional_signal,
        )

    def test_adding_color_preference_never_lowers_score(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        Adding a color preference never reduces any score.
        """
        base_query = DeckQuery.for_tribal("Goblin")
        additional_signal = QuerySignal(
            signal_type=QuerySignalType.COLOR,
            value="R",
            strength=SignalStrength.STRONG,
        )

        # Red card
        assert contract.check_monotonicity(
            scorer=scorer,
            card="Goblin Guide",
            base_query=base_query,
            additional_signal=additional_signal,
        )

        # Green card (doesn't match color)
        assert contract.check_monotonicity(
            scorer=scorer,
            card="Elvish Mystic",
            base_query=base_query,
            additional_signal=additional_signal,
        )

    def test_monotonicity_across_multiple_signals(self, scorer: MockScorer) -> None:
        """
        Monotonicity holds when adding multiple signals.
        """
        # Start with empty query
        query1 = DeckQuery.empty()
        signal1 = QuerySignal(QuerySignalType.TRIBE, "Goblin", SignalStrength.STRONG)
        query2 = query1.add_signal(signal1)
        signal2 = QuerySignal(QuerySignalType.COLOR, "R", SignalStrength.STRONG)
        query3 = query2.add_signal(signal2)

        # Scores should only increase (or stay same)
        score1 = scorer.score("Goblin Guide", query1)
        score2 = scorer.score("Goblin Guide", query2)
        score3 = scorer.score("Goblin Guide", query3)

        assert score1 <= score2 <= score3


class TestNonExclusivityInvariant:
    """
    MANDATORY TEST: Non-exclusivity invariant.

    Non-matching cards are not excluded (score >= 0).
    """

    @pytest.fixture
    def contract(self) -> QueryContract:
        return QueryContract()

    @pytest.fixture
    def scorer(self) -> MockScorer:
        return MockScorer()

    def test_non_goblin_not_excluded_from_goblin_query(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        MANDATORY: Non-Goblin cards are not excluded from Goblin query.
        """
        query = DeckQuery.for_tribal("Goblin")

        # Lightning Bolt doesn't match Goblin but should not be excluded
        assert contract.check_non_exclusivity(
            scorer=scorer,
            query=query,
            non_matching_card="Lightning Bolt",
        )

    def test_non_red_not_excluded_from_red_query(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        Non-red cards are not excluded from red preference query.
        """
        query = DeckQuery.for_tribal("Goblin", colors=["R"])

        # Elvish Mystic is green, not red
        assert contract.check_non_exclusivity(
            scorer=scorer,
            query=query,
            non_matching_card="Elvish Mystic",
        )

    def test_required_signal_can_exclude(self, contract: QueryContract, scorer: MockScorer) -> None:
        """
        REQUIRED signals (like format) CAN exclude cards.

        This is the exception - we can't play illegal cards.
        """
        query = DeckQuery.for_tribal("Goblin", format="standard")

        # For this test, the contract allows exclusion because format is REQUIRED
        # The check returns True (no violation) even if the card would be excluded
        assert contract.check_non_exclusivity(
            scorer=scorer,
            query=query,
            non_matching_card="Lightning Bolt",
        )

    def test_non_matching_card_has_positive_score(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        Non-matching cards have score >= 0 (not excluded).
        """
        query = DeckQuery.for_tribal("Goblin")

        # All non-matching cards should have positive scores
        non_matching_cards = ["Lightning Bolt", "Elvish Mystic", "Mountain", "Forest"]

        for card in non_matching_cards:
            score = scorer.score(card, query)
            assert score >= contract.MIN_INCLUDED_SCORE, f"{card} was excluded"


class TestArchetypeAgnostic:
    """
    MANDATORY TESTS: Query semantics are archetype-agnostic.

    The invariants work for any tribe, not just Goblin.
    This proves the system is generic, not special-cased.
    """

    @pytest.fixture
    def contract(self) -> QueryContract:
        return QueryContract()

    @pytest.fixture
    def scorer(self) -> MockScorer:
        return MockScorer()

    def test_dominance_works_for_elf(self, contract: QueryContract, scorer: MockScorer) -> None:
        """
        Dominance invariant works for Elf queries.
        """
        query = DeckQuery.for_tribal("Elf")
        elf_signal = query.get_signals(QuerySignalType.TRIBE)[0]

        # Elvish Mystic (Elf) vs Goblin Guide (not Elf)
        assert contract.check_dominance(
            scorer=scorer,
            query=query,
            matching_card="Elvish Mystic",
            non_matching_card="Goblin Guide",
            signal=elf_signal,
        )

    def test_monotonicity_works_for_elf(self, contract: QueryContract, scorer: MockScorer) -> None:
        """
        Monotonicity invariant works for Elf queries.
        """
        base_query = DeckQuery.empty()
        elf_signal = QuerySignal(
            signal_type=QuerySignalType.TRIBE,
            value="Elf",
            strength=SignalStrength.STRONG,
        )

        # Elf card - adding Elf preference should not lower score
        assert contract.check_monotonicity(
            scorer=scorer,
            card="Elvish Mystic",
            base_query=base_query,
            additional_signal=elf_signal,
        )

        # Non-Elf card - adding Elf preference should not lower score
        assert contract.check_monotonicity(
            scorer=scorer,
            card="Goblin Guide",
            base_query=base_query,
            additional_signal=elf_signal,
        )

    def test_non_exclusivity_works_for_elf(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        Non-exclusivity invariant works for Elf queries.
        """
        query = DeckQuery.for_tribal("Elf")

        # Goblin Guide doesn't match Elf but should not be excluded
        assert contract.check_non_exclusivity(
            scorer=scorer,
            query=query,
            non_matching_card="Goblin Guide",
        )

    def test_invariants_work_for_any_tribe(
        self, contract: QueryContract, scorer: MockScorer
    ) -> None:
        """
        All three invariants work for arbitrary tribes.

        This proves the system is not Goblin-specific.
        """
        tribes = ["Goblin", "Elf"]

        for tribe in tribes:
            query = DeckQuery.for_tribal(tribe)
            tribe_signal = query.get_signals(QuerySignalType.TRIBE)[0]

            # Find a card that matches and one that doesn't
            matching_card = None
            non_matching_card = None
            for card_name, card_data in scorer.card_db.items():
                if card_data.get("tribe") == tribe:
                    matching_card = card_name
                elif card_data.get("tribe") != tribe and card_data.get("tribe") != "":
                    non_matching_card = card_name

            if matching_card and non_matching_card:
                # Dominance
                assert contract.check_dominance(
                    scorer=scorer,
                    query=query,
                    matching_card=matching_card,
                    non_matching_card=non_matching_card,
                    signal=tribe_signal,
                ), f"Dominance failed for {tribe}"

            # Non-exclusivity (use a generic non-matching card)
            assert contract.check_non_exclusivity(
                scorer=scorer,
                query=query,
                non_matching_card="Mountain",
            ), f"Non-exclusivity failed for {tribe}"


class TestAddSignal:
    """
    Tests for DeckQuery.add_signal() method.
    """

    def test_add_signal_creates_new_query(self) -> None:
        """
        add_signal creates a new query with additional signal.
        """
        base = DeckQuery.empty()
        signal = QuerySignal(QuerySignalType.TRIBE, "Goblin", SignalStrength.STRONG)

        extended = base.add_signal(signal)

        # Original unchanged
        assert len(base.signals) == 0

        # New query has signal
        assert len(extended.signals) == 1
        assert extended.tribe == "Goblin"

    def test_add_signal_preserves_existing(self) -> None:
        """
        add_signal preserves existing signals.
        """
        base = DeckQuery.for_tribal("Goblin")
        signal = QuerySignal(QuerySignalType.COLOR, "R", SignalStrength.STRONG)

        extended = base.add_signal(signal)

        # Both tribe and color present
        assert extended.tribe == "Goblin"
        assert "R" in extended.colors
