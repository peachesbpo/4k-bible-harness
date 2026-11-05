"""summary.py — Aggregate per-verse analyses into a SUMMARY.md/.html/.pdf.

Reads all {Book}_{Ch}-{V}.json sidecars in a run directory and produces:
  - SUMMARY.md  — results-first overview
  - SUMMARY.html — styled dark-theme HTML (optional, needs markdown)
  - SUMMARY.pdf  — print-ready (optional, needs weasyprint)
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import VerseAnalysis
from .state import run_dir
from .writer import load_verse_analysis

try:
    import markdown as _md
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

try:
    from weasyprint import HTML as _WeasyHTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False


def _load_analyses(rd: Path) -> list[VerseAnalysis]:
    analyses = []
    for jp in sorted(rd.glob("*.json")):
        if jp.name == "manifest.json" or jp.name.startswith("SUMMARY"):
            continue
        try:
            analyses.append(load_verse_analysis(jp))
        except Exception:
            pass
    return analyses


def _load_review_audits(rd: Path) -> list[dict]:
    """Load claim-audit tallies from *.review.json files in the run dir.

    Review files are not verse analyses; they carry reviewer corrections and
    (per claim-audit spec §6.3) summary.claim_audit {total, licensed,
    downgraded, cut}. Legacy review files without the tally are tallied from
    their rule-citing corrections.
    """
    from .schema import ReviewCorrection, derive_claim_audit

    audits = []
    for rp in sorted(rd.glob("*.review.json")):
        try:
            d = json.loads(rp.read_text(encoding="utf-8"))
        except Exception:
            continue
        s = d.get("summary")
        ca = s.get("claim_audit") if isinstance(s, dict) else None
        if not isinstance(ca, dict):
            corrections = [ReviewCorrection.from_dict(c) for c in d.get("corrections", [])
                           if isinstance(c, dict)]
            ca = derive_claim_audit(corrections)
        audits.append({"verse_file": rp.name, **{k: ca.get(k, 0) for k in
                       ("total", "licensed", "downgraded", "cut")}})
    return audits


def _render_claim_audit(audits: list[dict]) -> list[str]:
    lines = ["", "---", "", "## 🔍 Claim Audit", ""]
    if not audits:
        lines += ["No claim-audit findings recorded for this run.", ""]
        return lines
    lines += ["Per-verse claim-audit verdicts from the review pass "
              "(rules CA-1..CA-7, see `prompts/claim-audit-spec.md`):", ""]
    lines += ["| Verse file | Total | Licensed | Downgraded | Cut |",
              "|------------|-------|----------|------------|-----|"]
    totals = {"total": 0, "licensed": 0, "downgraded": 0, "cut": 0}
    for a in audits:
        lines.append(f"| {a['verse_file']} | {a['total']} | {a['licensed']} | "
                     f"{a['downgraded']} | {a['cut']} |")
        for k in totals:
            totals[k] += a.get(k, 0)
    lines += ["", f"**Totals**: {totals['total']} findings — "
              f"{totals['licensed']} licensed, {totals['downgraded']} downgraded, "
              f"{totals['cut']} cut.", ""]
    return lines


def render_summary_md(analyses: list[VerseAnalysis], passage_ref: str,
                      claim_audits: list[dict] | None = None) -> str:
    """Render a results-first SUMMARY.md from verse analyses."""
    if not analyses:
        return f"# {passage_ref} — 4K Translation Analysis\n\nNo verse analyses found.\n"

    # Detect testament from the first analysis (all verses in a run share it)
    is_ot = analyses[0].testament == "OT"
    baseline_label = "ASV" if is_ot else "WEB"

    all_diffs = []
    all_insights = []
    for a in analyses:
        for d in a.diffs:
            all_diffs.append((a.reference, d))
        for i in a.insights:
            all_insights.append((a.reference, i))

    lines = [
        f"# {passage_ref} — 4K Translation Analysis",
        "",
        f"**Verses**: {len(analyses)}  ",
        f"**Total nuance gaps**: {len(all_diffs)}  ",
        f"**Total insights**: {len(all_insights)}  ",
        f"**Original Language**: {'Hebrew (WLC)' if is_ot else 'Greek (SBLGNT)'}  ",
        f"**Analyst**: Peaches (4K Bible Translation Harness)",
        "",
        "---",
        "",
        "## 📊 Diff Analysis: What Got Lost?",
        "",
        f"| # | Verse | Standard ({baseline_label}) | What's Lost | Why It Matters |",
        "|---|-------|----------------|-------------|----------------|",
    ]
    for i, (ref, d) in enumerate(all_diffs, 1):
        lines.append(
            f"| {i} | {ref} | \"{d.baseline_phrase}\" | {d.what_lost} | {d.why_matters} |"
        )
    lines += ["", "---", "", "## ✨ Expanded Translation (4K)", ""]
    for a in analyses:
        lines += [f"### {a.reference}", "", a.expanded_translation, ""]
    lines += [f"---", "", f"## 📖 Baseline Translation ({baseline_label})", ""]
    for a in analyses:
        baseline_text = a.asv_text if is_ot else a.web_text
        lines += [f"**{a.reference}**: {baseline_text}", ""]
    lines += ["---", "", "## 📂 Individual Verse Analyses", ""]
    for a in analyses:
        stem = f"{a.book}_{a.chapter}-{a.verse}.md"
        lines.append(f"- [{a.reference}]({stem})")
    lines += ["", "---", "", "## 💡 Theological Insights Recovered", ""]
    for ref, ins in all_insights:
        lines.append(f"- **{ref}** — {ins.title}: {ins.description}")
    lines += _render_claim_audit(claim_audits or [])
    lines += ["", "---", "", "## 📝 Notes for Further Study", ""]
    seen = set()
    for a in analyses:
        for f in a.further_study:
            if f not in seen:
                lines.append(f"- {f}")
                seen.add(f)
    lines += ["", "---", "",
              "**Analysis completed by**: Peaches (4K Bible Translation Harness)  ",
              "**Review status**: Draft - Ready for Review", ""]
    return "\n".join(lines)


def write_summary(run_id: str, passage_ref: str,
                  generate_html: bool = True, generate_pdf: bool = True) -> dict:
    """Write SUMMARY.md (+ optional .html, .pdf) for a run. Returns paths."""
    rd = run_dir(run_id)
    analyses = _load_analyses(rd)
    claim_audits = _load_review_audits(rd)
    md = render_summary_md(analyses, passage_ref, claim_audits=claim_audits)
    md_path = rd / "SUMMARY.md"
    md_path.write_text(md, encoding="utf-8")
    paths = {"md": str(md_path)}

    if generate_html and HAS_MARKDOWN:
        html_body = _md.markdown(md, extensions=["tables", "fenced_code", "toc", "nl2br"])
        from .theme import DARK_CSS
        html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{passage_ref} — 4K Translation Analysis</title>
<style>{DARK_CSS}</style></head><body>
{html_body}
</body></html>"""
        html_path = rd / "SUMMARY.html"
        html_path.write_text(html, encoding="utf-8")
        paths["html"] = str(html_path)
        if generate_pdf and HAS_WEASYPRINT:
            pdf_path = rd / "SUMMARY.pdf"
            _WeasyHTML(string=html).write_pdf(str(pdf_path))
            paths["pdf"] = str(pdf_path)
    return paths
