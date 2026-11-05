"""hebrew_text.py — Verify Hebrew source text purity + decode WLC morphology.

Mirrors greek_text.py / text_purity.py for OT verses. Two responsibilities:

1. `verify_hebrew(text)` — catch LLM-transliteration bleed (Latin/Greek/Arabic
   characters mixed into Hebrew Unicode). The Hebrew block is U+0590–U+05FF,
   plus the Hebrew presentation forms (U+FB1D–U+FB4F) used for precomposed
   letters with niqqud. Anything outside these ranges in a "Hebrew" string
   (except ASCII whitespace) is flagged.

2. `decode_morph(code)` — translate the Westminster Leningrad Codex (CCAT)
   morphology schema into readable English. e.g. "HR/Ncfsa" →
   "Preposition / Noun common feminine singular absolute". The full codebook
   is in /tmp/opencode/genesis-prep/01-wlc-morph-codebook.md; the tables
   here were verified against the actual distribution of morph codes in
   bible-db.sqlite (WLC source, ~300k word tokens).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


# ── Hebrew Unicode ranges ──────────────────────────────────────────────────────

HEBREW_RANGES = [
    (0x0590, 0x05FF),  # Hebrew block (letters, vowel points, cantillation, punctuation)
    (0xFB1D, 0xFB4F),  # Hebrew presentation forms (precomposed letters with niqqud)
]

# Whitespace allowed in Hebrew verse text. Everything else outside HEBREW_RANGES
# is bleed. (Hebrew punctuation — maqef U+05BE, sof pasuq U+05C3, paseq U+05C0,
# upper/lower marks U+05C4–U+05C5 — is inside U+0590–U+05FF, so allowed.)
ALLOWED_NON_HEBREW = set(" \t\n\r\u00a0")


@dataclass
class HebrewPurityReport:
    is_hebrew: bool
    offending_chars: list[tuple[int, str, str]]  # (position, char, hex)
    reason: str

    def to_dict(self) -> dict:
        return {
            "is_hebrew": self.is_hebrew,
            "offending_chars": self.offending_chars,
            "reason": self.reason,
        }


def _is_hebrew_codepoint(cp: int) -> bool:
    for lo, hi in HEBREW_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def verify_hebrew(text: str | None) -> HebrewPurityReport:
    """Verify that `text` is genuinely Hebrew script.

    Returns a HebrewPurityReport. .is_hebrew is True iff the string contains
    at least one Hebrew char and no characters outside the Hebrew ranges
    (except whitespace). Mirrors text_purity.verify_greek's API so retrieve.py
    can call it as a drop-in for OT verses.
    """
    if not text or not text.strip():
        return HebrewPurityReport(False, [], "no hebrew text")

    text = unicodedata.normalize("NFC", text)
    offending: list[tuple[int, str, str]] = []
    hebrew_count = 0

    for i, ch in enumerate(text):
        cp = ord(ch)
        if _is_hebrew_codepoint(cp):
            hebrew_count += 1
            continue
        # Combining marks applied to Hebrew are fine
        if unicodedata.combining(ch) and i > 0 and _is_hebrew_codepoint(ord(text[i - 1])):
            continue
        if ch in ALLOWED_NON_HEBREW:
            continue
        offending.append((i, ch, f"U+{cp:04X}"))

    if not hebrew_count:
        return HebrewPurityReport(False, offending, "no Hebrew characters found")
    if offending:
        return HebrewPurityReport(
            False, offending,
            f"{len(offending)} non-Hebrew character(s) — likely transliteration bleed",
        )
    return HebrewPurityReport(True, [], "ok")


# ── WLC morphology decoder ─────────────────────────────────────────────────────

POS_NAMES = {
    "N": "Noun",
    "R": "Preposition",
    "C": "Conjunction",
    "T": "Particle",
    "V": "Verb",
    "A": "Adjective",
    "P": "Pronoun",
    "D": "Adverb",
}

NOUN_TYPE = {"c": "common", "p": "proper", "g": "gentilic"}
GENDER = {"m": "masculine", "f": "feminine", "b": "dual(both)", "c": "common"}
NUMBER = {"s": "singular", "p": "plural", "d": "dual"}
STATE = {"a": "absolute", "c": "construct", "d": "determined"}

VERB_STEM = {
    "q": "Qal", "h": "Hiphil", "p": "Piel", "N": "Niphal",
    "t": "Hithpael", "P": "Pual", "H": "Hophal", "o": "Poal",
    "Q": "Poel", "r": "Hithpoel", "m": "Hithpalpel", "u": "Pilel",
    "v": "Hithpalel", "M": "Hithpoal", "l": "Pilpel", "a": "Palal",
    "K": "Hithpalpel var", "f": "Hithpael var", "O": "Poal var",
    "j": "Hophal var", "e": "Piel var", "i": "Niphal var",
    "k": "Pilpel var", "c": "Qal passive", "z": "Hithpalpel var",
    "s": "Sopal", "L": "Palal var", "D": "Devqal",
}

VERB_TENSE = {
    "p": "perfect", "i": "imperfect", "r": "participle active",
    "v": "imperative", "s": "participle passive", "j": "jussive",
    "c": "infinitive construct", "a": "infinitive absolute", "h": "cohortative",
}

PERSON = {"1": "1st", "2": "2nd", "3": "3rd"}

PARTICLE_SUB = {
    "d": "definite article", "o": "object marker", "n": "negative",
    "i": "interjection", "r": "interrogative", "m": "marker",
    "a": "assertive", "e": "exclamatory", "j": "particle",
}

PRONOUN_SUB = {
    "d": "demonstrative", "p": "personal", "i": "interrogative",
    "f": "relative", "x": "definite",
}

SUFFIX_PERSON = PERSON
SUFFIX_GENDER = GENDER
SUFFIX_NUMBER = NUMBER
SUFFIX_SPECIAL = {
    "d": "directional suffix", "h": "paragogic suffix", "n": "nun-energy suffix",
}


def _decode_noun(sub: str) -> str:
    """Decode HN<type><gender><number><state>. sub is the chars after 'HN'."""
    parts: list[str] = ["Noun"]
    if len(sub) >= 1 and sub[0] in NOUN_TYPE:
        parts.append(NOUN_TYPE[sub[0]])
    if len(sub) >= 2 and sub[1] in GENDER:
        parts.append(GENDER[sub[1]])
    if len(sub) >= 3 and sub[2] in NUMBER:
        parts.append(NUMBER[sub[2]])
    if len(sub) >= 4 and sub[3] in STATE:
        parts.append(STATE[sub[3]])
    return " ".join(parts)


def _decode_verb(sub: str) -> str:
    """Decode HV<stem><tense>[<person><gender><number>]. sub is after 'HV'."""
    parts: list[str] = ["Verb"]
    if len(sub) >= 1 and sub[0] in VERB_STEM:
        parts.append(VERB_STEM[sub[0]])
    if len(sub) >= 2 and sub[1] in VERB_TENSE:
        parts.append(VERB_TENSE[sub[1]])
    # Person/gender/number (positions 2-4)
    if len(sub) >= 3 and sub[2] in PERSON:
        parts.append(PERSON[sub[2]])
    if len(sub) >= 4 and sub[3] in GENDER:
        parts.append(GENDER[sub[3]])
    if len(sub) >= 5 and sub[4] in NUMBER:
        parts.append(NUMBER[sub[4]])
    return " ".join(parts)


def _decode_particle(sub: str) -> str:
    """Decode HT<sub>. sub is after 'HT'."""
    if not sub:
        return "Particle"
    code = sub[0]
    name = PARTICLE_SUB.get(code, f"particle ({code})")
    return f"Particle ({name})"


def _decode_pronoun(sub: str) -> str:
    """Decode HP<sub>. sub is after 'HP'."""
    parts: list[str] = ["Pronoun"]
    if not sub:
        return parts[0]
    code = sub[0]
    if code in PRONOUN_SUB:
        parts.append(PRONOUN_SUB[code])
    # personal pronouns carry person/gender/number (e.g. Pp3ms)
    if code == "p" and len(sub) >= 2:
        if len(sub) >= 2 and sub[1] in PERSON:
            parts.append(PERSON[sub[1]])
        if len(sub) >= 3 and sub[2] in GENDER:
            parts.append(GENDER[sub[2]])
        if len(sub) >= 4 and sub[3] in NUMBER:
            parts.append(NUMBER[sub[3]])
    # demonstrative (Pdx...) carries gender/number
    elif code == "d" and len(sub) >= 3:
        # Pdx<gender><number> e.g. Pdxcp, Pdxfs
        if len(sub) >= 3 and sub[2] in GENDER:
            parts.append(GENDER[sub[2]])
        if len(sub) >= 4 and sub[3] in NUMBER:
            parts.append(NUMBER[sub[3]])
    return " ".join(parts)


def _decode_adjective(sub: str) -> str:
    """Decode HA<gender><number><state>. sub is after 'HA'."""
    parts: list[str] = ["Adjective"]
    if len(sub) >= 1 and sub[0] in GENDER:
        parts.append(GENDER[sub[0]])
    if len(sub) >= 2 and sub[1] in NUMBER:
        parts.append(NUMBER[sub[1]])
    if len(sub) >= 3 and sub[2] in STATE:
        parts.append(STATE[sub[2]])
    return " ".join(parts)


def _decode_suffix(sub: str) -> str:
    """Decode /S<...> pronominal suffix."""
    # sub is "S..." (after the slash)
    if not sub.startswith("S"):
        return sub
    rest = sub[1:]
    if not rest:
        return "with pronominal suffix"
    # Special suffixes (Sd, Sh, Sn)
    if rest[0] in SUFFIX_SPECIAL:
        return f"with {SUFFIX_SPECIAL[rest[0]]}"
    # Standard Sp<person><gender><number>
    if rest[0] == "p" and len(rest) >= 4:
        parts: list[str] = ["with suffix"]
        if rest[1] in SUFFIX_PERSON:
            parts.append(SUFFIX_PERSON[rest[1]])
        if rest[2] in SUFFIX_GENDER:
            parts.append(SUFFIX_GENDER[rest[2]])
        if rest[3] in SUFFIX_NUMBER:
            parts.append(SUFFIX_NUMBER[rest[3]])
        return " ".join(parts)
    return f"with suffix ({rest})"


def _decode_segment(seg: str) -> str:
    """Decode one slash-separated segment of a morph code (no leading H)."""
    if not seg:
        return ""
    # Strip leading H (Hebrew marker) if present on the first segment
    if seg.startswith("H"):
        seg = seg[1:]
    if not seg:
        return ""
    pos = seg[0]
    sub = seg[1:]

    if pos == "N":
        return _decode_noun(sub)
    if pos == "V":
        return _decode_verb(sub)
    if pos == "T":
        return _decode_particle(sub)
    if pos == "P":
        return _decode_pronoun(sub)
    if pos == "A":
        return _decode_adjective(sub)
    if pos == "R":
        return "Preposition" + (f" (with directional-he)" if sub.startswith("d") else "")
    if pos == "C":
        return "Conjunction"
    if pos == "D":
        return "Adverb"
    return f"{POS_NAMES.get(pos, pos)} ({sub})"


def decode_morph(code: str | None) -> str:
    """Translate a WLC morph code into readable English.

    e.g. "HR/Ncfsa" → "Preposition / Noun common feminine singular absolute"
         "HVqp3ms"  → "Verb Qal perfect 3rd masculine singular"
         "HTo"       → "Particle (object marker)"
    """
    if not code:
        return ""
    # Split on / for compound morphs (e.g. "HR/Ncfsa" = prep + noun)
    segments = code.split("/")
    decoded = [_decode_segment(seg) for seg in segments]
    # Filter empty segments (from trailing slashes or bare H)
    decoded = [d for d in decoded if d]
    return " / ".join(decoded)
