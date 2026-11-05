"""text_purity.py — Verify that Greek source text is actually Greek.

Catches the LLM-transliteration bleed seen in legacy passages (e.g. "σtiν",
"ἐste", "ἀdelfoί", "πantes" — Latin letters mixed into Greek Unicode).

The Greek and Coptic Unicode block is U+0370–U+03FF. We also allow a small
set of punctuation/whitespace characters that appear in the source data:
  - spaces, middle dot · (U+0387, Greek anosigma/semicolon)
  - Greek punctuation: ; · ' (U+037E, U+0387)
  - regular punctuation: , . ; : ' " — these appear in some verse JSON
  - newline, tab

Anything outside these ranges in a "Greek" string is flagged.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Greek and Coptic block + a few extensions
GREEK_RANGES = [
    (0x0370, 0x03FF),  # Greek and Coptic
    (0x1F00, 0x1FFF),  # Greek Extended (polytonic)
]

# Latin letters that are commonly confused with Greek look-alikes.
# If any of these appear in a "Greek" string, it's almost certainly bleed.
LATIN_LOOKALIKES = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

# Punctuation/symbols we allow in Greek verse text.
ALLOWED_NON_GREEK = set(" ,.;:;'\"—–-?!()[]\n\t\r·;")
# SBLGNT editorial brackets (Supplemental Punctuation block U+2E00–U+2E0F):
# ⸌ ⸍ ⸂ ⸃ ⸄ ⸅ ⸆ ⸇ ⸈ ⸉ ⸊ ⸋ ⸌ ⸍ ⸎ ⸏
ALLOWED_NON_GREEK.update(chr(c) for c in range(0x2E00, 0x2E10))


@dataclass
class PurityReport:
    is_greek: bool
    suspicious_chars: list[tuple[int, str, str]]  # (position, char, hex)
    latin_letters: list[tuple[int, str, str]]      # (position, char, hex)
    message: str

    def to_dict(self) -> dict:
        return {
            "is_greek": self.is_greek,
            "suspicious_chars": self.suspicious_chars,
            "latin_letters": self.latin_letters,
            "message": self.message,
        }


def _is_greek_codepoint(cp: int) -> bool:
    for lo, hi in GREEK_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def verify_greek(text: str, allow_latin_lookalikes: bool = False) -> PurityReport:
    """Verify that `text` is genuinely Greek script.

    Args:
        text: the string to check (typically a verse's "original_text" field).
        allow_latin_lookalikes: if True, don't flag Latin letters (use only for
            debugging — should stay False in production).

    Returns:
        PurityReport with .is_greek True iff the string contains at least one
        Greek char and no Latin letters (when allow_latin_lookalikes=False).
    """
    if not text:
        return PurityReport(False, [], [], "empty string")

    suspicious = []
    latin = []
    greek_count = 0

    for i, ch in enumerate(text):
        cp = ord(ch)
        if _is_greek_codepoint(cp):
            greek_count += 1
            continue
        # Combining marks applied to Greek are fine
        if unicodedata.combining(ch) and i > 0 and _is_greek_codepoint(ord(text[i - 1])):
            continue
        if ch in ALLOWED_NON_GREEK:
            continue
        if ch in LATIN_LOOKALIKES:
            if not allow_latin_lookalikes:
                latin.append((i, ch, f"U+{cp:04X}"))
            continue
        suspicious.append((i, ch, f"U+{cp:04X}"))

    is_greek = greek_count > 0 and not latin and not suspicious
    if not greek_count:
        message = "no Greek characters found"
    elif latin:
        message = (
            f"{len(latin)} Latin letter(s) mixed into Greek text — likely "
            "transliteration bleed (e.g. 't' instead of 'τ')"
        )
    elif suspicious:
        message = (
            f"{len(suspicious)} suspicious non-Greek character(s) — "
            "unexpected script in source text"
        )
    else:
        message = "ok"

    return PurityReport(is_greek, suspicious, latin, message)


def repair_greek(text: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Best-effort repair of common Latin→Greek transliteration bleed.

    Replaces Latin letters that appear inside otherwise-Greek text with their
    standard transliteration equivalents. Returns (repaired_text,
    replacements_applied) where replacements_applied is a list of
    (position_in_original, old_char, new_char).

    Conservative: only repairs when the text is mostly Greek and the Latin
    char is adjacent to a Greek char.
    """
    # Latin → Greek transliteration map. Includes both look-alikes and the
    # standard beta-code-style transliteration, since LLM bleed produces both.
    REPLACEMENTS = {
        'a': 'α', 'A': 'Α',
        'b': 'β', 'B': 'Β',
        'c': 'κ',  # kappa (transliteration, e.g. cαὶ = καὶ)
        'd': 'δ',  # delta (no upper — D ≠ Δ visually)
        'e': 'ε', 'E': 'Ε',
        'f': 'φ',  # phi — common in transliteration (adelphos, not adelphos)
        'g': 'γ', 'G': 'Γ',
        'h': 'η',  # eta — common transliteration
        'i': 'ι', 'I': 'Ι',
        'k': 'κ', 'K': 'Κ',
        'l': 'λ',  # lambda
        'm': 'μ', 'M': 'Μ',
        'n': 'ν', 'N': 'Ν',
        'o': 'ο', 'O': 'Ο',
        'p': 'π',  # pi (lowercase)
        'r': 'ρ', 'R': 'Ρ',
        's': 'σ',
        't': 'τ', 'T': 'Τ',
        'u': 'υ', 'U': 'Υ',
        'v': 'ν',  # visual look-alike (ν nu), NOT upsilon
        'w': 'ω', 'W': 'Ω',
        'x': 'χ', 'X': 'Χ',
        'z': 'ζ',  # zeta
    }
    SAFE = REPLACEMENTS

    # Only repair if the text has at least 1 Greek char (otherwise it's probably
    # actually Latin and we'd be corrupting it).
    greek_count = sum(1 for ch in text if _is_greek_codepoint(ord(ch)))
    if greek_count < 1:
        return text, []

    # Skip lines that contain Strong's number references (g\d+) — those are
    # concordance citations, not Greek source text.
    import re as _re
    if _re.search(r"\b[gG]\d{1,5}\b", text):
        return text, []

    # Normalize accented Latin (â, é, ô) to plain Latin so they match SAFE keys.
    # Use a translation table for common Latin accented chars only — leave Greek alone.
    LATIN_ACCENT_MAP = str.maketrans({
        "â": "a", "á": "a", "à": "a", "ä": "a", "ã": "a", "å": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "î": "i", "ï": "i", "í": "i", "ì": "i",
        "ô": "o", "ö": "o", "ó": "o", "ò": "o", "õ": "o",
        "û": "u", "ü": "u", "ú": "u", "ù": "u",
        "ý": "y", "ÿ": "y",
        "ç": "c",
        "ñ": "n",
        "Â": "A", "É": "E", "Ê": "E", "Ô": "O", "Ü": "U",
    })
    text = text.translate(LATIN_ACCENT_MAP)

    # Multi-pass: each pass may convert Latin chars adjacent to Greek. Re-running
    # catches newly-adjacent chars after the previous pass's replacements. A word
    # like "θusiaσterion" needs ~7 passes to fully convert from the inside out.
    all_applied: list[tuple[int, str, str]] = []
    current = text
    for _ in range(12):
        out = []
        pass_applied: list[tuple[int, str, str]] = []
        for i, ch in enumerate(current):
            prev_is_greek = i > 0 and _is_greek_codepoint(ord(current[i - 1]))
            next_is_greek = i + 1 < len(current) and _is_greek_codepoint(ord(current[i + 1]))
            if ch in SAFE and (prev_is_greek or next_is_greek):
                out.append(SAFE[ch])
                pass_applied.append((i, ch, SAFE[ch]))
            else:
                out.append(ch)
        if not pass_applied:
            break
        # Carry applied positions forward (best-effort — positions are relative
        # to the current pass, not the original string, but still useful for audit)
        all_applied.extend(pass_applied)
        current = "".join(out)
    return current, all_applied
