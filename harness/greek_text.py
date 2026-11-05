"""greek_text.py — Robust cleaning of SBLGNT verse text.

The Solid Rock Greek NT (grc-srgnt) embeds a textual apparatus inline in the
verse JSON using Supplemental Punctuation brackets (U+2E00–U+2E0F).

Apparatus format (discovered by codepoint analysis of Matthew 23, Matthew 1,
Luke 15, and other chapters):

  PAIRED:   OPEN apparatus OPEN CHOSEN CLOSE
            where CLOSE = chr(ord(OPEN) + 1)
            The chosen reading sits between the 2nd OPEN and CLOSE.
            e.g. ⸂ variants ¦ variants ⸂chosen⸃  →  chosen

  NESTED:   Apparatus may nest — the CHOSEN of an outer block contains
            inner apparatus blocks. Resolved innermost-first iteratively.
            e.g. ⸂ outer-app ⸂chosen-with-⸂2inner⸂2inner-chosen⸃rest⸃
              → ⸂ outer-app ⸂chosen-with-inner-chosen rest⸃ → final chosen

  PREFIX:   apparatus OPEN CHOSEN CLOSE
            The apparatus precedes the verse text; only one OPEN.
            e.g. RP TR ¦ – TNT2 ⸋chosen⸌  →  chosen

  UNPAIRED: OPEN apparatus OPEN
            An insertion-point apparatus with no close bracket.
            e.g. ⸆ variants ¦ variants ⸆  →  (nothing)

  ORPHAN:   OPEN apparatus OPEN  (close expected but absent)
            Treated as unpaired — remove, keep what follows.

Known open brackets and their closes:
  ⸂ (U+2E02) → ⸃ (U+2E03)   angle
  ⸄ (U+2E04) → ⸅ (U+2E05)   white curly (potential)
  ⸆ (U+2E06) → (none)         insertion point (unpaired)
  ⸈ (U+2E08) → ⸉ (U+2E09)   (potential)
  ⸉ (U+2E09) → ⸊ (U+2E0A)   nail → tortoise
  ⸋ (U+2E0B) → ⸌ (U+2E0C)   tortoise → dental

Unit numbers may follow an OPEN bracket (e.g. ⸂2 apparatus ⸂2 chosen⸃).
Unit digits are IMMEDIATELY adjacent to the bracket (no whitespace) — a digit
after bracket+space is always the start of the next inline verse reference
(e.g. "⸆ 17:26") and must be preserved for VERSE_REF_RE.
Inline verse references like "23:3" appear between apparatus blocks.
Source sigla (RP, TR, NA, WH, SBL, TNT2, NIV, f35, etc.) follow readings.
¦ (U+00A6) separates alternative readings; – (U+2013) marks omission.
"""

from __future__ import annotations

import re

VERSE_REF_RE = re.compile(r"\s*\d+:\d+\s*")
BRACKET_RANGE = re.compile(r"[\u2e00-\u2e0f]")
NO_BRACKET = r"[^\u2e00-\u2e0f]*"  # any chars except editorial brackets

KNOWN_OPENS: dict[str, str | None] = {
    "\u2e02": "\u2e03",
    "\u2e04": "\u2e05",
    "\u2e06": None,
    "\u2e08": "\u2e09",
    "\u2e09": "\u2e0a",
    "\u2e0b": "\u2e0c",
}


def clean_sblgnt(text: str) -> str:
    if not text:
        return text

    # 1. Iteratively resolve innermost PAIRED apparatus (handles nesting)
    changed = True
    while changed:
        changed = False
        for open_ch, close_ch in KNOWN_OPENS.items():
            if close_ch is None or open_ch not in text or close_ch not in text:
                continue
            # Innermost: OPEN [no-brackets] OPEN [no-brackets] CLOSE → keep chosen
            pattern = (
                re.escape(open_ch)
                + NO_BRACKET
                + re.escape(open_ch)
                + r"\s*\d*"
                + r"(" + NO_BRACKET + r")"
                + re.escape(close_ch)
            )
            new = re.sub(pattern, r"\1", text, flags=re.DOTALL)
            if new != text:
                text = new
                changed = True

    # 2. Resolve PREFIX apparatus (single OPEN + CLOSE, apparatus before OPEN)
    for open_ch, close_ch in KNOWN_OPENS.items():
        if close_ch is None or close_ch not in text:
            continue
        count = text.count(open_ch)
        if count == 1:
            pattern = (
                r".*?" + re.escape(open_ch) + r"\s*\d*" + r"(" + NO_BRACKET + r")" + re.escape(close_ch)
            )
            text = re.sub(pattern, r"\1", text, flags=re.DOTALL)

    # 3. Resolve UNPAIRED (⸆) and ORPHAN (open without close): OPEN ... OPEN → remove
    for open_ch, close_ch in KNOWN_OPENS.items():
        if open_ch not in text:
            continue
        count = text.count(open_ch)
        if count >= 2 and (close_ch is None or close_ch not in text):
            # \d* consumes a unit digit immediately after the 2nd open (⸆2 … ⸆2)
            pattern = re.escape(open_ch) + NO_BRACKET + re.escape(open_ch) + r"\d*"
            text = re.sub(pattern, " ", text, flags=re.DOTALL)

    # 4. Strip remaining brackets, verse refs, whitespace
    # \d* after a bracket is an apparatus unit digit (⸆2) — digits following
    # bracket+whitespace are verse refs and are handled by VERSE_REF_RE below.
    text = re.sub(r"[\u2e00-\u2e0f]\d*", " ", text)
    text = VERSE_REF_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
