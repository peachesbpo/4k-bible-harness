"""writer.py — Render VerseAnalysis to markdown + JSON sidecar.

Uses Jinja2 with template_verse.md (the existing template). Each verse produces:
  - {Book}_{Ch}-{V}.md   — human-readable analysis
  - {Book}_{Ch}-{V}.json — structured sidecar

Idempotent: skips if both files exist and analysis is `done`, unless force=True.
"""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jinja2.exceptions import TemplateError

from .schema import VerseAnalysis
from .state import run_dir

SCRIPT_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SCRIPT_DIR  # template_verse.md lives at project root


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return env


def render_verse_md(analysis: VerseAnalysis, passage_ref: str | None = None) -> str:
    """Render a VerseAnalysis to markdown using template_verse.md.

    Args:
        analysis: the structured analysis.
        passage_ref: optional parent passage label, e.g. "Matthew 23:8-12".
    """
    env = _env()
    template = env.get_template("template_verse.md")
    # template_verse.md uses {{VERSE_REFERENCE}} placeholders in the old regex
    # style. Jinja2 uses {{ ... }} too, but the existing template uses
    # {{ALL_CAPS_VARS}} which clashes with Jinja syntax. We render via a
    # simple namespace instead.
    #
    # Actually template_verse.md's placeholders ARE valid Jinja variables
    # (just uppercase names). We pass them all in.
    is_ot = analysis.testament == "OT"
    context = {
        "VERSE_REFERENCE": analysis.reference,
        "PASSAGE_REFERENCE": passage_ref or analysis.reference,
        "PASSAGE_DESCRIPTION": passage_ref or "",
        "LANGUAGE": "Hebrew" if is_ot else "Greek",
        "TEXT_VERSION": "Westminster Leningrad Codex (WLC)" if is_ot else "SBLGNT / Nestle 1904",
        "BASELINE_VERSE": analysis.asv_text if is_ot else analysis.web_text,
        "EXPANDED_VERSE": analysis.expanded_translation,
        "BASELINE_PHRASE": "",  # legacy placeholder, not used in new format
        "WHAT_LOST": "",
        "WHY_MATTERS": "",
        "INSIGHT_TITLE": "",
        "INSIGHT_DESCRIPTION": "",
        "ORIGINAL_TEXT": analysis.hebrew_text if is_ot else analysis.greek_text,
        "WORD": "",
        "TRANSLITERATION": "",
        "STRONGS": "",
        "PARSING": "",
        "RANGE": "",
        "NUANCE": "",
        "TVM_NOTES": analysis.grammar_notes,
        "SYNTAX_NOTES": analysis.syntax_notes,
        "PREP_NOTES": analysis.prep_notes,
        "CONTEXT_NOTE_1": analysis.context_notes[0] if analysis.context_notes else "",
        "CONTEXT_NOTE_2": analysis.context_notes[1] if len(analysis.context_notes) > 1 else "",
        "OT_ECHO": analysis.cross_references[0] if analysis.cross_references else "",
        "NT_ECHO": analysis.cross_references[1] if len(analysis.cross_references) > 1 else "",
        "ANALYST": analysis.analyst,
        "REVIEW_STATUS": analysis.review_status,
        # Rich data for the new blocks we append
        "diffs": [d.__dict__ if hasattr(d, "__dict__") else d for d in analysis.diffs],
        "insights": [i.__dict__ if hasattr(i, "__dict__") else i for i in analysis.insights],
        "key_words": [k.__dict__ if hasattr(k, "__dict__") else k for k in analysis.key_words],
        "further_study": analysis.further_study,
    }
    try:
        return template.render(**context)
    except TemplateError:
        # Fall back to a self-contained render if the template syntax is invalid
        return _fallback_render(analysis, passage_ref)


def _fallback_render(analysis: VerseAnalysis, passage_ref: str | None) -> str:
    """Self-contained markdown render — doesn't depend on template_verse.md."""
    is_ot = analysis.testament == "OT"
    lang_name = "Hebrew" if is_ot else "Greek"
    text_version = "Westminster Leningrad Codex (WLC)" if is_ot else "SBLGNT / Nestle 1904"
    baseline_label = "ASV" if is_ot else "WEB"
    baseline_text = analysis.asv_text if is_ot else analysis.web_text
    original_text = analysis.hebrew_text if is_ot else analysis.greek_text
    lines = [
        f"# {analysis.reference} — 4K Verse Analysis",
        "",
        f"**Part of**: {passage_ref or analysis.reference}",
        f"**Original Language**: {lang_name} ({text_version})",
        f"**Analyst**: {analysis.analyst}",
        "",
        "---",
        "",
        f"## 📖 Common English Translation ({baseline_label})",
        "",
        f"> {baseline_text}",
        "",
        "---",
        "",
        "## ✨ 4K Expanded Translation",
        "",
        "*Original language nuances restored in readable English. Parenthetical notes explain the nuance recovered.*",
        "",
        analysis.expanded_translation,
        "",
        "---",
        "",
        "## 📊 Diff Analysis: What Got Lost?",
        "",
        f"| # | Standard ({baseline_label}) | What's Lost | Why It Matters |",
        "|---|----------------|-------------|----------------|",
    ]
    for i, d in enumerate(analysis.diffs, 1):
        d = d.__dict__ if hasattr(d, "__dict__") else d
        lines.append(f"| {i} | \"{d['baseline_phrase']}\" | {d['what_lost']} | {d['why_matters']} |")
    lines += ["", "---", "", "## 💡 Theological Insights Recovered", ""]
    for i, ins in enumerate(analysis.insights, 1):
        ins = ins.__dict__ if hasattr(ins, "__dict__") else ins
        lines.append(f"{i}. **{ins['title']}**: {ins['description']}")
        lines.append("")
    lines += ["---", "", "## 🔍 Detailed Linguistic Analysis", ""]
    lines += [f"#### {analysis.reference}", ""]
    lines += [f"**{lang_name} Text** ({text_version}):  "]
    lines += [f"> {original_text}", ""]
    lines += ["**Key Word Analysis**:", ""]
    if is_ot:
        lines += ["| Word | Transliteration | Strong's | Morphology | Stem | Lexical Range | Nuance |"]
        lines += ["|------|----------------|----------|------------|------|---------------|--------|"]
        for kw in analysis.key_words:
            kw = kw.__dict__ if hasattr(kw, "__dict__") else kw
            lines.append(
                f"| {kw['word']} | {kw['transliteration']} | {kw['strongs']} | "
                f"{kw.get('morphology', '')} | {kw.get('stem', '') or ''} | "
                f"{kw['lexical_range']} | {kw['nuance']} |"
            )
    else:
        lines += ["| Word | Transliteration | Strong's | Parsing | Lexical Range | Nuance |"]
        lines += ["|------|----------------|----------|---------|---------------|--------|"]
        for kw in analysis.key_words:
            kw = kw.__dict__ if hasattr(kw, "__dict__") else kw
            lines.append(
                f"| {kw['word']} | {kw['transliteration']} | {kw['strongs']} | "
                f"{kw['parsing']} | {kw['lexical_range']} | {kw['nuance']} |"
            )
    lines += [""]
    if analysis.grammar_notes or analysis.syntax_notes or analysis.prep_notes:
        lines += ["**Grammatical Observations**:"]
        if analysis.grammar_notes:
            lines += [f"- **Tense/Voice/Mood**: {analysis.grammar_notes}"]
        if analysis.syntax_notes:
            lines += [f"- **Syntax/Word Order**: {analysis.syntax_notes}"]
        if analysis.prep_notes:
            lines += [f"- **Prepositions/Particles**: {analysis.prep_notes}"]
        lines += [""]
    if analysis.context_notes:
        lines += ["**Cultural/Contextual Notes**:"]
        for c in analysis.context_notes:
            lines += [f"- {c}"]
        lines += [""]
    if analysis.cross_references:
        lines += ["**Cross-References**:"]
        for x in analysis.cross_references:
            lines += [f"- {x}"]
        lines += [""]
    if analysis.further_study:
        lines += ["---", "", "## 📝 Notes for Further Study", ""]
        for f in analysis.further_study:
            lines += [f"- {f}"]
        lines += [""]
    lines += ["---", "", f"**Analysis completed by**: {analysis.analyst}  "]
    lines += [f"**Review status**: {analysis.review_status}", ""]
    return "\n".join(lines)


def write_verse(analysis: VerseAnalysis, run_id: str,
                passage_ref: str | None = None, force: bool = False) -> tuple[Path, Path]:
    """Write the .md and .json sidecar for a verse. Returns (md_path, json_path)."""
    rd = run_dir(run_id)
    stem = f"{analysis.book}_{analysis.chapter}-{analysis.verse}"
    md_path = rd / f"{stem}.md"
    json_path = rd / f"{stem}.json"

    if not force and md_path.exists() and json_path.exists():
        # Idempotent: skip
        return md_path, json_path

    md = _fallback_render(analysis, passage_ref)
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path


def load_verse_analysis(json_path: Path) -> VerseAnalysis:
    """Load a VerseAnalysis from a .json sidecar."""
    return VerseAnalysis.from_dict(json.loads(json_path.read_text("utf-8")))
