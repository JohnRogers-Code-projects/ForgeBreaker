"""
Intent Inference — Deterministic Parsing of User Deck Requests.

This module provides deterministic intent inference from raw user text.
It uses regex and keyword matching only — no LLM calls, no card DB lookups.

IMPORTANT: This is scaffolding only. Intent is inferred but not yet
used to alter execution paths.
"""

import re

from forgebreaker.models.intent import (
    ALL_COLORS,
    Archetype,
    Constraint,
    DeckIntent,
    Format,
)

# =============================================================================
# FORMAT PATTERNS
# =============================================================================

_FORMAT_PATTERNS: dict[Format, re.Pattern[str]] = {
    Format.STANDARD: re.compile(r"\bstandard\b", re.IGNORECASE),
    Format.HISTORIC: re.compile(r"\bhistoric\b", re.IGNORECASE),
    Format.EXPLORER: re.compile(r"\bexplorer\b", re.IGNORECASE),
    Format.PIONEER: re.compile(r"\bpioneer\b", re.IGNORECASE),
    Format.MODERN: re.compile(r"\bmodern\b", re.IGNORECASE),
    Format.LEGACY: re.compile(r"\blegacy\b", re.IGNORECASE),
    Format.VINTAGE: re.compile(r"\bvintage\b", re.IGNORECASE),
    Format.BRAWL: re.compile(r"\bbrawl\b", re.IGNORECASE),
    Format.TIMELESS: re.compile(r"\btimeless\b", re.IGNORECASE),
}

# =============================================================================
# COLOR PATTERNS
# =============================================================================

# Color words map to color codes
_COLOR_WORDS: dict[str, str] = {
    "white": "W",
    "blue": "U",
    "black": "B",
    "red": "R",
    "green": "G",
    # Mana symbols
    "w": "W",
    "u": "U",
    "b": "B",
    "r": "R",
    "g": "G",
}

# Guild/clan names map to color pairs
_COLOR_PAIRS: dict[str, frozenset[str]] = {
    # Ravnica guilds
    "azorius": frozenset({"W", "U"}),
    "dimir": frozenset({"U", "B"}),
    "rakdos": frozenset({"B", "R"}),
    "gruul": frozenset({"R", "G"}),
    "selesnya": frozenset({"G", "W"}),
    "orzhov": frozenset({"W", "B"}),
    "izzet": frozenset({"U", "R"}),
    "golgari": frozenset({"B", "G"}),
    "boros": frozenset({"R", "W"}),
    "simic": frozenset({"G", "U"}),
    # Tarkir clans (wedges)
    "abzan": frozenset({"W", "B", "G"}),
    "jeskai": frozenset({"U", "R", "W"}),
    "sultai": frozenset({"B", "G", "U"}),
    "mardu": frozenset({"R", "W", "B"}),
    "temur": frozenset({"G", "U", "R"}),
    # Alara shards
    "bant": frozenset({"G", "W", "U"}),
    "esper": frozenset({"W", "U", "B"}),
    "grixis": frozenset({"U", "B", "R"}),
    "jund": frozenset({"B", "R", "G"}),
    "naya": frozenset({"R", "G", "W"}),
    # Mono-color
    "mono-white": frozenset({"W"}),
    "mono-blue": frozenset({"U"}),
    "mono-black": frozenset({"B"}),
    "mono-red": frozenset({"R"}),
    "mono-green": frozenset({"G"}),
    "monowhite": frozenset({"W"}),
    "monoblue": frozenset({"U"}),
    "monoblack": frozenset({"B"}),
    "monored": frozenset({"R"}),
    "monogreen": frozenset({"G"}),
}

# =============================================================================
# ARCHETYPE PATTERNS
# =============================================================================

_ARCHETYPE_PATTERNS: dict[Archetype, re.Pattern[str]] = {
    Archetype.AGGRO: re.compile(r"\b(aggro|aggressive|fast|beatdown)\b", re.IGNORECASE),
    Archetype.MIDRANGE: re.compile(r"\b(midrange|mid-range|value)\b", re.IGNORECASE),
    Archetype.CONTROL: re.compile(r"\b(control|controlling)\b", re.IGNORECASE),
    Archetype.COMBO: re.compile(r"\b(combo|combination|otk)\b", re.IGNORECASE),
    Archetype.TEMPO: re.compile(r"\b(tempo)\b", re.IGNORECASE),
    Archetype.RAMP: re.compile(r"\b(ramp|ramping|big.?mana)\b", re.IGNORECASE),
}

# =============================================================================
# TRIBE PATTERNS
# =============================================================================

# Common creature types that indicate tribal decks
_TRIBE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bdragon(s)?\b", re.IGNORECASE), "Dragon"),
    (re.compile(r"\bgoblin(s)?\b", re.IGNORECASE), "Goblin"),
    (re.compile(r"\belf\b|\belves\b", re.IGNORECASE), "Elf"),
    (re.compile(r"\bvampire(s)?\b", re.IGNORECASE), "Vampire"),
    (re.compile(r"\bzombie(s)?\b", re.IGNORECASE), "Zombie"),
    (re.compile(r"\bmerfolk\b", re.IGNORECASE), "Merfolk"),
    (re.compile(r"\bangel(s)?\b", re.IGNORECASE), "Angel"),
    (re.compile(r"\bdemon(s)?\b", re.IGNORECASE), "Demon"),
    (re.compile(r"\bwarrior(s)?\b", re.IGNORECASE), "Warrior"),
    (re.compile(r"\bknight(s)?\b", re.IGNORECASE), "Knight"),
    (re.compile(r"\bwizard(s)?\b", re.IGNORECASE), "Wizard"),
    (re.compile(r"\bshaman(s)?\b", re.IGNORECASE), "Shaman"),
    (re.compile(r"\bdinosaur(s)?\b", re.IGNORECASE), "Dinosaur"),
    (re.compile(r"\bpirate(s)?\b", re.IGNORECASE), "Pirate"),
    (re.compile(r"\bspirit(s)?\b", re.IGNORECASE), "Spirit"),
    (re.compile(r"\bcat(s)?\b", re.IGNORECASE), "Cat"),
    (re.compile(r"\bdog(s)?\b", re.IGNORECASE), "Dog"),
    (re.compile(r"\brat(s)?\b", re.IGNORECASE), "Rat"),
    (re.compile(r"\bsliver(s)?\b", re.IGNORECASE), "Sliver"),
    (re.compile(r"\bhuman(s)?\b", re.IGNORECASE), "Human"),
    (re.compile(r"\bsoldier(s)?\b", re.IGNORECASE), "Soldier"),
    (re.compile(r"\bshrine(s)?\b", re.IGNORECASE), "Shrine"),
]

# =============================================================================
# THEME PATTERNS (non-tribal)
# =============================================================================

_THEME_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsacrifice\b|\bsac\b", re.IGNORECASE), "sacrifice"),
    (re.compile(r"\bgraveyard\b|\breanimator\b", re.IGNORECASE), "graveyard"),
    (re.compile(r"\bartifact(s)?\b", re.IGNORECASE), "artifacts"),
    (re.compile(r"\benchantment(s)?\b|\benchantress\b", re.IGNORECASE), "enchantments"),
    (re.compile(r"\btoken(s)?\b", re.IGNORECASE), "tokens"),
    (re.compile(r"\blifegain\b|\blife.?gain\b", re.IGNORECASE), "lifegain"),
    (re.compile(r"\bmill\b|\bmilling\b", re.IGNORECASE), "mill"),
    (re.compile(r"\bburn\b", re.IGNORECASE), "burn"),
    (re.compile(r"\bdiscard\b", re.IGNORECASE), "discard"),
    (re.compile(r"\bcounters?\b|\b\+1/\+1\b", re.IGNORECASE), "counters"),
    (re.compile(r"\bflicker\b|\bblink\b", re.IGNORECASE), "blink"),
    (re.compile(r"\blandfall\b", re.IGNORECASE), "landfall"),
    (
        re.compile(r"\bspellslinger\b|\binstants?\s*(and|&)?\s*sorceries?\b", re.IGNORECASE),
        "spellslinger",
    ),
]

# =============================================================================
# CONSTRAINT PATTERNS
# =============================================================================

_CONSTRAINT_PATTERNS: dict[Constraint, re.Pattern[str]] = {
    Constraint.BUDGET: re.compile(r"\b(budget|cheap|affordable|low.?cost)\b", re.IGNORECASE),
    Constraint.COMPETITIVE: re.compile(r"\b(competitive|comp|ranked|tournament)\b", re.IGNORECASE),
    Constraint.CASUAL: re.compile(r"\b(casual|fun|jank|janky)\b", re.IGNORECASE),
    Constraint.SINGLETON: re.compile(r"\b(singleton|highlander)\b", re.IGNORECASE),
}


# =============================================================================
# INFERENCE FUNCTIONS
# =============================================================================


def _extract_format(text: str) -> Format | None:
    """Extract format from text. Returns None if no format found."""
    for format_enum, pattern in _FORMAT_PATTERNS.items():
        if pattern.search(text):
            return format_enum
    return None


def _extract_colors(text: str) -> frozenset[str] | None:
    """Extract colors from text. Returns None if no colors found."""
    colors: set[str] = set()
    text_lower = text.lower()

    # Check guild/clan names first (they're more specific)
    for name, color_set in _COLOR_PAIRS.items():
        if name in text_lower:
            colors.update(color_set)

    # Check individual color words
    for word, code in _COLOR_WORDS.items():
        # Use word boundary matching for color words
        if re.search(rf"\b{word}\b", text_lower):
            colors.add(code)

    # Validate colors
    colors = colors & ALL_COLORS

    return frozenset(colors) if colors else None


def _extract_archetype(text: str) -> Archetype | None:
    """Extract archetype from text. Returns None if no archetype found."""
    for archetype, pattern in _ARCHETYPE_PATTERNS.items():
        if pattern.search(text):
            return archetype
    return None


def _extract_tribe(text: str) -> str | None:
    """Extract creature type from text. Returns None if no tribe found."""
    for pattern, tribe_name in _TRIBE_PATTERNS:
        if pattern.search(text):
            return tribe_name
    return None


def _extract_theme(text: str) -> str | None:
    """Extract non-tribal theme from text. Returns None if no theme found."""
    for pattern, theme_name in _THEME_PATTERNS:
        if pattern.search(text):
            return theme_name
    return None


def _extract_constraints(text: str) -> frozenset[Constraint]:
    """Extract constraints from text. Returns empty set if none found."""
    constraints: set[Constraint] = set()
    for constraint, pattern in _CONSTRAINT_PATTERNS.items():
        if pattern.search(text):
            constraints.add(constraint)
    return frozenset(constraints)


def _calculate_confidence(intent: DeckIntent) -> float:
    """
    Calculate confidence score based on how much was inferred.

    More specific intents get higher confidence.
    """
    score = 0.1  # Base confidence for any request

    if intent.format is not None:
        score += 0.15
    if intent.colors is not None:
        score += 0.15
        # More colors = slightly more confidence (more specific)
        score += min(0.05, len(intent.colors) * 0.01)
    if intent.archetype is not None:
        score += 0.15
    if intent.tribe is not None:
        score += 0.2  # Tribal is very specific
    if intent.theme is not None:
        score += 0.15
    if intent.constraints:
        score += 0.05 * len(intent.constraints)

    return min(1.0, score)


def infer_deck_intent(user_text: str) -> DeckIntent:
    """
    Infer deck intent from raw user text.

    Uses regex and keyword matching only. Deterministic output —
    same input always produces same output.

    Args:
        user_text: Raw user request text

    Returns:
        DeckIntent with inferred fields and confidence score
    """
    format_val = _extract_format(user_text)
    colors = _extract_colors(user_text)
    archetype = _extract_archetype(user_text)
    tribe = _extract_tribe(user_text)
    theme = _extract_theme(user_text)
    constraints = _extract_constraints(user_text)

    # Create intent without confidence first
    intent = DeckIntent(
        format=format_val,
        colors=colors,
        archetype=archetype,
        tribe=tribe,
        theme=theme,
        constraints=constraints,
        confidence=0.0,  # Placeholder
    )

    # Calculate confidence based on what was inferred
    confidence = _calculate_confidence(intent)

    # Return with calculated confidence
    return DeckIntent(
        format=intent.format,
        colors=intent.colors,
        archetype=intent.archetype,
        tribe=intent.tribe,
        theme=intent.theme,
        constraints=intent.constraints,
        confidence=confidence,
    )


def apply_intent_defaults(intent: DeckIntent) -> DeckIntent:
    """
    Apply default values to an intent for unspecified fields.

    Defaults (authoritative):
    - format → Standard
    - archetype → Midrange

    Confidence is increased when defaults are applied, as the intent
    becomes more complete.

    Args:
        intent: The inferred intent (may have None fields)

    Returns:
        New DeckIntent with defaults applied
    """
    applied_defaults = 0

    # Apply format default
    new_format = intent.format
    if new_format is None:
        new_format = Format.STANDARD
        applied_defaults += 1

    # Apply archetype default
    new_archetype = intent.archetype
    if new_archetype is None:
        new_archetype = Archetype.MIDRANGE
        applied_defaults += 1

    # Increase confidence when defaults applied (intent is now more complete)
    # But cap the increase — defaults don't make us more certain about user intent
    confidence_boost = applied_defaults * 0.1
    new_confidence = min(1.0, intent.confidence + confidence_boost)

    return DeckIntent(
        format=new_format,
        colors=intent.colors,
        archetype=new_archetype,
        tribe=intent.tribe,
        theme=intent.theme,
        constraints=intent.constraints,
        confidence=new_confidence,
    )
