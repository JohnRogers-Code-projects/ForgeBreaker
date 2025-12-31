"""
Tests for Deck Intent Inference.

These tests verify the deterministic intent parsing from user text.
"""

import pytest

from forgebreaker.models.intent import (
    Archetype,
    Constraint,
    DeckIntent,
    Format,
)
from forgebreaker.services.intent_inference import (
    apply_intent_defaults,
    infer_deck_intent,
)


class TestDeckIntentModel:
    """Tests for the DeckIntent dataclass."""

    def test_default_values(self) -> None:
        """DeckIntent has correct defaults."""
        intent = DeckIntent()
        assert intent.format is None
        assert intent.colors is None
        assert intent.archetype is None
        assert intent.tribe is None
        assert intent.theme is None
        assert intent.constraints == frozenset()
        assert intent.confidence == 0.0

    def test_confidence_validation(self) -> None:
        """Confidence must be in [0.0, 1.0]."""
        with pytest.raises(ValueError):
            DeckIntent(confidence=-0.1)
        with pytest.raises(ValueError):
            DeckIntent(confidence=1.1)

    def test_immutable(self) -> None:
        """DeckIntent is frozen."""
        intent = DeckIntent(confidence=0.5)
        with pytest.raises(AttributeError):
            intent.confidence = 0.8  # type: ignore


class TestInferDeckIntent:
    """Tests for infer_deck_intent function."""

    def test_empty_request(self) -> None:
        """'build me a deck' produces minimal intent."""
        intent = infer_deck_intent("build me a deck")

        assert intent.format is None
        assert intent.colors is None
        assert intent.archetype is None
        assert intent.tribe is None
        assert intent.theme is None
        assert intent.constraints == frozenset()
        assert intent.confidence < 0.5

    def test_red_green_dragon_deck(self) -> None:
        """'red green dragon deck' extracts colors and tribe."""
        intent = infer_deck_intent("red green dragon deck")

        assert intent.colors == frozenset({"R", "G"})
        assert intent.tribe == "Dragon"
        assert intent.confidence > 0.1  # Higher than base case

    def test_standard_gruul_midrange(self) -> None:
        """'standard gruul midrange' extracts format, colors, archetype."""
        intent = infer_deck_intent("standard gruul midrange")

        assert intent.format == Format.STANDARD
        assert intent.colors == frozenset({"R", "G"})
        assert intent.archetype == Archetype.MIDRANGE

    def test_format_extraction(self) -> None:
        """Various formats are correctly extracted."""
        assert infer_deck_intent("historic deck").format == Format.HISTORIC
        assert infer_deck_intent("explorer aggro").format == Format.EXPLORER
        assert infer_deck_intent("pioneer control").format == Format.PIONEER
        assert infer_deck_intent("modern burn").format == Format.MODERN

    def test_color_extraction_individual(self) -> None:
        """Individual color words are extracted."""
        intent = infer_deck_intent("white blue deck")
        assert intent.colors == frozenset({"W", "U"})

        intent = infer_deck_intent("black red aggro")
        assert intent.colors == frozenset({"B", "R"})

    def test_color_extraction_guilds(self) -> None:
        """Guild names are correctly mapped to colors."""
        assert infer_deck_intent("azorius control").colors == frozenset({"W", "U"})
        assert infer_deck_intent("dimir rogues").colors == frozenset({"U", "B"})
        assert infer_deck_intent("rakdos midrange").colors == frozenset({"B", "R"})
        assert infer_deck_intent("selesnya tokens").colors == frozenset({"G", "W"})
        assert infer_deck_intent("izzet spells").colors == frozenset({"U", "R"})

    def test_color_extraction_clans(self) -> None:
        """Clan/shard names are correctly mapped to colors."""
        assert infer_deck_intent("jund midrange").colors == frozenset({"B", "R", "G"})
        assert infer_deck_intent("esper control").colors == frozenset({"W", "U", "B"})
        assert infer_deck_intent("temur ramp").colors == frozenset({"G", "U", "R"})

    def test_color_extraction_mono(self) -> None:
        """Mono-color specifications work."""
        assert infer_deck_intent("mono-red aggro").colors == frozenset({"R"})
        assert infer_deck_intent("monoblue tempo").colors == frozenset({"U"})

    def test_archetype_extraction(self) -> None:
        """Archetypes are correctly extracted."""
        assert infer_deck_intent("red aggro").archetype == Archetype.AGGRO
        assert infer_deck_intent("blue control").archetype == Archetype.CONTROL
        assert infer_deck_intent("golgari midrange").archetype == Archetype.MIDRANGE
        assert infer_deck_intent("storm combo").archetype == Archetype.COMBO
        assert infer_deck_intent("simic ramp").archetype == Archetype.RAMP

    def test_tribe_extraction(self) -> None:
        """Creature types are correctly extracted."""
        assert infer_deck_intent("goblin deck").tribe == "Goblin"
        assert infer_deck_intent("elf tribal").tribe == "Elf"
        assert infer_deck_intent("vampire aggro").tribe == "Vampire"
        assert infer_deck_intent("zombie horde").tribe == "Zombie"
        assert infer_deck_intent("dragon tribal").tribe == "Dragon"

    def test_theme_extraction(self) -> None:
        """Non-tribal themes are correctly extracted."""
        assert infer_deck_intent("sacrifice deck").theme == "sacrifice"
        assert infer_deck_intent("graveyard matters").theme == "graveyard"
        assert infer_deck_intent("artifact deck").theme == "artifacts"
        assert infer_deck_intent("token swarm").theme == "tokens"
        assert infer_deck_intent("lifegain deck").theme == "lifegain"

    def test_constraint_extraction(self) -> None:
        """Constraints are correctly extracted."""
        intent = infer_deck_intent("budget red deck")
        assert Constraint.BUDGET in intent.constraints

        intent = infer_deck_intent("competitive standard")
        assert Constraint.COMPETITIVE in intent.constraints

        intent = infer_deck_intent("casual fun deck")
        assert Constraint.CASUAL in intent.constraints

    def test_multiple_constraints(self) -> None:
        """Multiple constraints can be extracted."""
        intent = infer_deck_intent("budget casual goblins")
        assert Constraint.BUDGET in intent.constraints
        assert Constraint.CASUAL in intent.constraints

    def test_complex_request(self) -> None:
        """Complex requests extract multiple fields."""
        intent = infer_deck_intent("build me a competitive standard gruul midrange dragon deck")

        assert intent.format == Format.STANDARD
        assert intent.colors == frozenset({"R", "G"})
        assert intent.archetype == Archetype.MIDRANGE
        assert intent.tribe == "Dragon"
        assert Constraint.COMPETITIVE in intent.constraints


class TestDeterminism:
    """Tests that intent inference is deterministic."""

    def test_same_input_same_output(self) -> None:
        """Same input always produces same output."""
        text = "standard gruul midrange dragon deck"

        intent1 = infer_deck_intent(text)
        intent2 = infer_deck_intent(text)
        intent3 = infer_deck_intent(text)

        assert intent1 == intent2 == intent3

    def test_determinism_across_variations(self) -> None:
        """Various inputs produce consistent outputs."""
        test_cases = [
            "build me a deck",
            "red green dragons",
            "mono red aggro",
            "esper control standard",
            "budget goblins",
        ]

        for text in test_cases:
            results = [infer_deck_intent(text) for _ in range(5)]
            assert all(r == results[0] for r in results), f"Non-deterministic: {text}"


class TestApplyIntentDefaults:
    """Tests for apply_intent_defaults function."""

    def test_defaults_applied_to_empty_intent(self) -> None:
        """Empty intent gets format and archetype defaults."""
        intent = DeckIntent(confidence=0.1)
        defaulted = apply_intent_defaults(intent)

        assert defaulted.format == Format.STANDARD
        assert defaulted.archetype == Archetype.MIDRANGE

    def test_defaults_do_not_override(self) -> None:
        """Existing values are not overridden."""
        intent = DeckIntent(
            format=Format.HISTORIC,
            archetype=Archetype.AGGRO,
            confidence=0.5,
        )
        defaulted = apply_intent_defaults(intent)

        assert defaulted.format == Format.HISTORIC
        assert defaulted.archetype == Archetype.AGGRO

    def test_partial_defaults(self) -> None:
        """Only missing fields get defaults."""
        intent = DeckIntent(
            format=Format.EXPLORER,
            archetype=None,
            confidence=0.3,
        )
        defaulted = apply_intent_defaults(intent)

        assert defaulted.format == Format.EXPLORER  # Preserved
        assert defaulted.archetype == Archetype.MIDRANGE  # Defaulted

    def test_confidence_increases_with_defaults(self) -> None:
        """Confidence increases when defaults are applied."""
        intent = DeckIntent(confidence=0.2)
        defaulted = apply_intent_defaults(intent)

        assert defaulted.confidence > intent.confidence

    def test_confidence_capped_at_one(self) -> None:
        """Confidence does not exceed 1.0."""
        intent = DeckIntent(confidence=0.95)
        defaulted = apply_intent_defaults(intent)

        assert defaulted.confidence <= 1.0

    def test_other_fields_preserved(self) -> None:
        """Non-defaulted fields are preserved."""
        intent = DeckIntent(
            colors=frozenset({"R", "G"}),
            tribe="Dragon",
            theme="tokens",
            constraints=frozenset({Constraint.BUDGET}),
            confidence=0.4,
        )
        defaulted = apply_intent_defaults(intent)

        assert defaulted.colors == frozenset({"R", "G"})
        assert defaulted.tribe == "Dragon"
        assert defaulted.theme == "tokens"
        assert defaulted.constraints == frozenset({Constraint.BUDGET})


class TestConfidenceScoring:
    """Tests for confidence calculation."""

    def test_empty_request_low_confidence(self) -> None:
        """Empty requests have low confidence."""
        intent = infer_deck_intent("build me a deck")
        assert intent.confidence < 0.5

    def test_specific_request_higher_confidence(self) -> None:
        """More specific requests have higher confidence."""
        vague = infer_deck_intent("build me a deck")
        specific = infer_deck_intent("standard gruul midrange dragon deck")

        assert specific.confidence > vague.confidence

    def test_tribal_boosts_confidence(self) -> None:
        """Tribal requests get confidence boost."""
        non_tribal = infer_deck_intent("red green deck")
        tribal = infer_deck_intent("red green dragon deck")

        assert tribal.confidence > non_tribal.confidence


class TestSnapshotCases:
    """Snapshot tests for common phrases."""

    @pytest.mark.parametrize(
        "text,expected_format,expected_colors,expected_archetype,expected_tribe",
        [
            ("build me a deck", None, None, None, None),
            ("red deck", None, frozenset({"R"}), None, None),
            ("mono red aggro", None, frozenset({"R"}), Archetype.AGGRO, None),
            ("standard control", Format.STANDARD, None, Archetype.CONTROL, None),
            ("gruul", None, frozenset({"R", "G"}), None, None),
            ("jund midrange", None, frozenset({"B", "R", "G"}), Archetype.MIDRANGE, None),
            ("dragon tribal", None, None, None, "Dragon"),
            ("red green dragons", None, frozenset({"R", "G"}), None, "Dragon"),
            (
                "historic goblins",
                Format.HISTORIC,
                None,
                None,
                "Goblin",
            ),
            (
                "standard esper control",
                Format.STANDARD,
                frozenset({"W", "U", "B"}),
                Archetype.CONTROL,
                None,
            ),
        ],
    )
    def test_snapshot(
        self,
        text: str,
        expected_format: Format | None,
        expected_colors: frozenset[str] | None,
        expected_archetype: Archetype | None,
        expected_tribe: str | None,
    ) -> None:
        """Verify intent inference for common phrases."""
        intent = infer_deck_intent(text)

        assert intent.format == expected_format, f"format mismatch for '{text}'"
        assert intent.colors == expected_colors, f"colors mismatch for '{text}'"
        assert intent.archetype == expected_archetype, f"archetype mismatch for '{text}'"
        assert intent.tribe == expected_tribe, f"tribe mismatch for '{text}'"
