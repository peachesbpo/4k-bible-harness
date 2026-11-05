"""prompts.py — Versioned subagent prompts.

Prompts live in prompts/*.md. Each prompt is a function that takes a VerseBundle
(or VerseAnalysis for reviewer) and returns the subagent prompt string.

Prompt files use {{#if NT}}...{{/if}} and {{#if OT}}...{{/if}} conditional
blocks that are resolved based on the bundle's `testament` field. This keeps
each role in a single templated file (avoids drift between parallel NT/OT
prompt versions).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from textwrap import dedent

from .retrieve import VerseBundle
from .schema import VerseAnalysis

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Matches {{#if NT}}...{{/if}} or {{#if OT}}...{{/if}} (non-greedy, multiline)
_CONDITIONAL_RE = re.compile(
    r"\{\{#if\s+(NT|OT)\}\}(.*?)\{\{/if\}\}",
    re.DOTALL,
)


def _load(name: str) -> str:
    p = PROMPTS_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"Prompt not found: {p}")
    return p.read_text("utf-8")


def _resolve_conditionals(text: str, testament: str) -> str:
    """Strip {{#if NT}}/{{#if OT}} blocks that don't match the testament,
    keep the inner content of the block that does match."""
    keep = testament  # "NT" or "OT"

    def _replace(match: re.Match) -> str:
        tag = match.group(1)
        inner = match.group(2)
        return inner if tag == keep else ""

    resolved = _CONDITIONAL_RE.sub(_replace, text)
    # Clean up any blank lines left by stripped blocks (collapse 3+ newlines to 2)
    resolved = re.sub(r"\n{3,}", "\n\n", resolved)
    return resolved


def analyst_prompt(bundle: VerseBundle, passage_ref: str | None = None) -> str:
    """Build the analyst subagent prompt for one verse."""
    template = _load("analyst.md")
    template = _resolve_conditionals(template, bundle.testament)
    bundle_json = bundle.to_json()
    return template.replace("{{VERSE_BUNDLE_JSON}}", bundle_json).replace(
        "{{PASSAGE_REF}}", passage_ref or bundle.book
    )


def reviewer_prompt(analysis: VerseAnalysis, bundle: VerseBundle) -> str:
    """Build the reviewer subagent prompt."""
    template = _load("reviewer.md")
    template = _resolve_conditionals(template, bundle.testament)
    return (
        template
        .replace("{{VERSE_ANALYSIS_JSON}}", json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2))
        .replace("{{VERSE_BUNDLE_JSON}}", bundle.to_json())
    )


def corrector_prompt(analysis: VerseAnalysis, review_notes: str) -> str:
    """Build the corrector subagent prompt.

    The corrector prompt doesn't have a VerseBundle directly; we infer the
    testament from the analysis (OT analyses have hebrew_text populated, NT
    have greek_text populated). Falls back to NT if neither is present.
    """
    testament = "NT"
    if hasattr(analysis, "hebrew_text") and analysis.hebrew_text:
        testament = "OT"
    elif hasattr(analysis, "greek_text") and not analysis.greek_text:
        testament = "OT"
    template = _load("corrector.md")
    template = _resolve_conditionals(template, testament)
    return (
        template
        .replace("{{VERSE_ANALYSIS_JSON}}", json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2))
        .replace("{{REVIEW_NOTES}}", review_notes)
    )


def analysis_schema_hint() -> str:
    """A short hint describing the JSON schema the analyst must return."""
    return dedent(
        """
        Return ONLY a JSON object with this shape (no prose, no markdown fences):
        {
          "book": "Matthew",
          "chapter": 23,
          "verse": 8,
          "reference": "Matthew 23:8",
          "greek_text": "<the verified Greek text, copied exactly from the bundle>",
          "web_text": "<the WEB text, copied exactly from the bundle>",
          "greek_pure": true,
          "expanded_translation": "<clean English with parenthetical nuance notes>",
          "diffs": [
            {"baseline_phrase": "<phrase from WEB>", "what_lost": "...", "why_matters": "..."}
          ],
          "insights": [
            {"title": "...", "description": "..."}
          ],
          "key_words": [
            {"word": "<Greek>", "transliteration": "...", "strongs": "G1234",
             "parsing": "...", "lexical_range": "...", "nuance": "..."}
          ],
          "grammar_notes": "...",
          "syntax_notes": "...",
          "prep_notes": "...",
          "context_notes": ["..."],
          "cross_references": ["..."],
          "further_study": ["..."]
        }
        """
    ).strip()
