"""validators.py — Quality gates for a VerseAnalysis.

Runs automated checks before a verse is marked `done`. Returns a list of
issues (empty list = passed). Language-aware: OT verses use Hebrew purity
checks and H#### Strong's; NT verses use Greek purity and G#### Strong's.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from dataclasses import dataclass

from .schema import VerseAnalysis
from .text_purity import verify_greek
from .hebrew_text import verify_hebrew
from .retrieve import fetch_verse

SCRIPT_DIR = Path(__file__).resolve().parent.parent
STRONGS_DIR = SCRIPT_DIR / "strongs-data"


@dataclass
class ValidationIssue:
    severity: str   # "error" | "warning"
    field: str
    message: str

    def to_dict(self) -> dict:
        return {"severity": self.severity, "field": self.field, "message": self.message}


# Unicode / Strong's patterns
GREEK_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
HEBREW_RE = re.compile(r"[\u0590-\u05ff\ufb1d-\ufb4f]")
STRONGS_GREEK_RE = re.compile(r"\bG\d{1,5}\b")
STRONGS_HEBREW_RE = re.compile(r"\bH\d{1,5}\b")
PARSING_RE = re.compile(r"\b[A-Z]{1,4}-[A-Z0-9]{1,4}(?:-[A-Z0-9]{1,4})+\b")


def validate(analysis: VerseAnalysis, bundle_strongs_numbers: set[str] | None = None,
               bundle_cross_refs: list[dict] | None = None,
               spoken_jesus_material: bool = False,
               bundle_source_text: str | None = None) -> list[ValidationIssue]:
    """Run all validators. Returns list of issues (empty = passed).

    Language-aware: detects OT vs NT from analysis.testament and applies the
    appropriate purity check (Hebrew vs Greek), Strong's format (H vs G),
    and baseline text (ASV vs WEB).

    bundle_source_text: the bundle's authoritative source text (hebrew_text
    for OT, greek_text for NT). When provided, a byte-exact compare runs so
    combining-mark drift / corruption is caught at ingest (fix-spec
    2026-09-15 #3) instead of at the reviewer's byte-exact check 1.
    """
    issues: list[ValidationIssue] = []
    is_ot = analysis.testament == "OT"

    # Detect OT cross-refs for the Aramaic-gap check (NT only)
    has_ot_refs = False
    if bundle_cross_refs:
        has_ot_refs = any(r.get("testament") == "OT" for r in bundle_cross_refs)

    # 1. Source text purity (language-aware)
    if is_ot:
        purity = verify_hebrew(analysis.hebrew_text)
        if not purity.is_hebrew:
            issues.append(ValidationIssue(
                "error", "hebrew_text",
                f"Hebrew text not pure: {purity.reason}",
            ))
    else:
        purity = verify_greek(analysis.greek_text)
        if not purity.is_greek:
            issues.append(ValidationIssue(
                "error", "greek_text",
                f"Greek text not pure: {purity.message}",
            ))

    # 2. Baseline text non-empty (language-aware)
    baseline_text = analysis.asv_text if is_ot else analysis.web_text
    baseline_label = "ASV" if is_ot else "WEB"
    baseline_field = "asv_text" if is_ot else "web_text"
    if not baseline_text or len(baseline_text.strip()) < 5:
        issues.append(ValidationIssue("error", baseline_field, f"{baseline_label} text missing or too short"))

    # 3. Diff phrases must appear in baseline (language-aware)
    baseline_lower = baseline_text.lower()
    for i, d in enumerate(analysis.diffs):
        phrase = d.baseline_phrase.strip().strip('"').strip("'").lower()
        if not phrase:
            issues.append(ValidationIssue("error", f"diffs[{i}].baseline_phrase", "empty phrase"))
        elif phrase not in baseline_lower:
            words = phrase.split()
            if len(words) >= 2:
                head = " ".join(words[:2])
                if head not in baseline_lower:
                    issues.append(ValidationIssue(
                        "warning", f"diffs[{i}].baseline_phrase",
                        f'phrase "{d.baseline_phrase}" not found in {baseline_label} text',
                    ))
            else:
                issues.append(ValidationIssue(
                    "warning", f"diffs[{i}].baseline_phrase",
                    f'phrase "{d.baseline_phrase}" not found in {baseline_label} text',
                ))

    # 4. Strong's numbers exist in bundle (if provided) — language-aware
    if bundle_strongs_numbers is not None:
        for i, kw in enumerate(analysis.key_words):
            if kw.strongs and kw.strongs.upper() not in bundle_strongs_numbers:
                num = kw.strongs.upper().lstrip("GH")
                prefix = "H" if is_ot else "G"
                if f"{prefix}{num}" not in bundle_strongs_numbers and num not in bundle_strongs_numbers:
                    issues.append(ValidationIssue(
                        "warning", f"key_words[{i}].strongs",
                        f"Strong's {kw.strongs} not in bundle concordance",
                    ))

    # 5. Style guide: no source-language script / Strong's / parsing in expanded translation
    source_re = HEBREW_RE if is_ot else GREEK_RE
    strongs_re = STRONGS_HEBREW_RE if is_ot else STRONGS_GREEK_RE
    source_name = "Hebrew" if is_ot else "Greek"
    if source_re.search(analysis.expanded_translation):
        issues.append(ValidationIssue(
            "error", "expanded_translation",
            f"Contains {source_name} Unicode characters (style guide: English only)",
        ))
    if strongs_re.search(analysis.expanded_translation):
        issues.append(ValidationIssue(
            "error", "expanded_translation",
            f"Contains Strong's numbers (style guide: English only)",
        ))
    if PARSING_RE.search(analysis.expanded_translation):
        issues.append(ValidationIssue(
            "warning", "expanded_translation",
            "May contain parsing codes (style guide: English only)",
        ))

    # 6. Required fields
    if not analysis.expanded_translation.strip():
        issues.append(ValidationIssue("error", "expanded_translation", "empty"))
    if not analysis.key_words:
        issues.append(ValidationIssue("warning", "key_words", "no key words analyzed"))

    # 7. Cross-references appear in bundle index (warning — index not exhaustive)
    if bundle_cross_refs is not None:
        bundle_refs = set()
        for r in bundle_cross_refs:
            bundle_refs.add(f"{r.get('book_name','')} {r.get('chapter')}:{r.get('verse')}")
            bundle_refs.add(f"{r.get('book_abbr','')} {r.get('chapter')}:{r.get('verse')}")
        for i, cited in enumerate(analysis.cross_references):
            cited_clean = re.sub(r"\s*\(votes:\s*\d+\)\s*$", "", cited).strip()
            matched = any(cited_clean.lower() in b.lower() or b.lower() in cited_clean.lower()
                         for b in bundle_refs)
            if not matched and cited_clean:
                issues.append(ValidationIssue(
                    "warning", f"cross_references[{i}]",
                    f'"{cited}" not in bundle cross-ref index (may be unverified)',
                ))

    # 8. Aramaic-gap acknowledgment (NT spoken-Jesus material with OT cross-refs only)
    if not is_ot and spoken_jesus_material and has_ot_refs:
        if not analysis.aramaic_gap_acknowledged:
            issues.append(ValidationIssue(
                "error", "aramaic_gap_acknowledged",
                "spoken-Jesus material with OT cross-refs must acknowledge the Aramaic gap",
            ))
        ctx_text = " ".join(analysis.context_notes).lower()
        if "aramaic" not in ctx_text and "earliest extant" not in ctx_text:
            issues.append(ValidationIssue(
                "warning", "context_notes",
                "Aramaic gap flagged but not explained in context_notes",
            ))

    # 9. Jesus-attribution check (NT spoken-Jesus material only — never for OT)
    JESUS_VERBS = re.compile(
        r"\b(jesus|he|him)\s+(softens?|reframes?|drains?|chooses?|intends?|shifts?|adapts?)\b",
        re.IGNORECASE,
    )
    if not is_ot and spoken_jesus_material:
        for i, ins in enumerate(analysis.insights):
            if JESUS_VERBS.search(ins.description) or JESUS_VERBS.search(ins.title):
                issues.append(ValidationIssue(
                    "error", f"insights[{i}]",
                    "attributes Greek word choice to Jesus (forbidden — Jesus taught in Aramaic)",
                ))
        for i, d in enumerate(analysis.diffs):
            if JESUS_VERBS.search(d.what_lost) or JESUS_VERBS.search(d.why_matters):
                issues.append(ValidationIssue(
                    "error", f"diffs[{i}]",
                    "attributes Greek word choice to Jesus (forbidden — Jesus taught in Aramaic)",
                ))

    # 10. Evidence-status sanity
    for i, d in enumerate(analysis.diffs):
        if d.gap_type and not d.evidence_status:
            issues.append(ValidationIssue(
                "warning", f"diffs[{i}].evidence_status",
                "gap_type set but evidence_status missing",
            ))
        if d.evidence_status and d.evidence_status not in ("textual", "inferential", "speculative"):
            issues.append(ValidationIssue(
                "warning", f"diffs[{i}].evidence_status",
                f"invalid evidence_status: {d.evidence_status}",
            ))

    # 11. Claim-audit heuristics (spec §7) — warnings only, reviewer confirms
    issues.extend(claim_audit_issues(analysis))

    # 12. Byte-exact source-text compare vs bundle (fix-spec 2026-09-15 #3).
    # Mirrors the reviewer's byte-exact check 1 so drift is caught at ingest.
    # Call normalize_source_text() first: NFC-equivalent combining-mark drift
    # is repaired to the bundle's exact bytes and passes this check.
    if bundle_source_text:
        analyst_text = analysis.hebrew_text if is_ot else analysis.greek_text
        source_field = "hebrew_text" if is_ot else "greek_text"
        if analyst_text and analyst_text != bundle_source_text:
            issues.append(ValidationIssue(
                "error", source_field,
                "source text does not byte-match the bundle (reviewer check 1 "
                "compares byte-exact) — combining-mark drift or a dropped char; "
                "copy the text verbatim from the bundle",
            ))

    return issues


def normalize_source_text(analysis: VerseAnalysis, bundle_source_text: str | None) -> str | None:
    """Repair combining-mark drift in the analyst's source text (in place).

    If the analyst's source text differs from the bundle only by combining-mark
    order (NFC-equivalent, e.g. dagesh/qamats swapped) — but is not byte-equal —
    rewrite it to the bundle's exact bytes. The bundle is the reviewer's
    byte-exact ground truth and is itself not always NFC, so NFC output must
    NOT be used as the repaired form (fix-spec 2026-09-15 #3; 12:17/12:19).

    Returns a note describing the repair, or None when no repair was made.
    """
    if not bundle_source_text:
        return None
    is_ot = analysis.testament == "OT"
    analyst_text = analysis.hebrew_text if is_ot else analysis.greek_text
    if not analyst_text or analyst_text == bundle_source_text:
        return None
    import unicodedata
    if unicodedata.normalize("NFC", analyst_text) \
            != unicodedata.normalize("NFC", bundle_source_text):
        return None
    if is_ot:
        analysis.hebrew_text = bundle_source_text
    else:
        analysis.greek_text = bundle_source_text
    return (f"{'hebrew_text' if is_ot else 'greek_text'} combining-mark drift "
            f"normalized to bundle bytes (NFC-equivalent)")


# ── Claim-audit ingest-time heuristics (claim-audit-spec §7) ──────────────────
# Full semantic licensing is a reviewer judgment. These mechanical checks emit
# `warning` (never `error`) for the reviewer to confirm.

CELL_HEDGE_RE = re.compile(
    r"\b(context decides?|may|might|possibly|perhaps|either|or|can also|tends? to|sometimes|often)\b",
    re.IGNORECASE,
)
PROSE_HEDGE_RE = re.compile(
    r"\b(may|might|possibly|perhaps|as if|as though|though|although|invites?|recalls?|resonates?|can|could|appears?|seems?|suggests?)\b",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(r"\b(not|never|rather than|instead of|no longer)\b", re.IGNORECASE)
ABSOLUTE_RE = re.compile(r"\b(means|always|only|must be|is the standard)\b", re.IGNORECASE)
MEANING_CLAIM_RE = re.compile(
    r"\b(means|signifies|is the idiom|the idiom|rather than|instead of)\b",
    re.IGNORECASE,
)
CONTRAST_RE = re.compile(r"\b(not|never|rather than|instead of)\b", re.IGNORECASE)
CERTAINTY_RE = re.compile(
    r"\b(signals?|frames?|deliberately|narrator'?s?\s+(?:choice|choosing)|imports?|inverts?|inversion)\b",
    re.IGNORECASE,
)
_SCRIPTURE_CITATION_RE = re.compile(
    r"\b(?:[123]\s?)?(?:Gen(?:esis)?|Ex(?:o(?:d(?:us)?)?)?|Lev(?:iticus)?|Num(?:bers)?|Deut(?:eronomy)?|"
    r"Josh(?:ua)?|Judg(?:es)?|Ruth|Sam(?:uel)?|K(?:in)?gs|Chr(?:on(?:icles)?)?|Ezra|Neh(?:emiah)?|Est(?:her)?|"
    r"Job|Ps(?:alm|alms)?|Prov(?:erbs)?|Eccl(?:esiastes)?|Song|Isa(?:iah)?|Jer(?:emiah)?|Lam(?:entations)?|"
    r"Ezek(?:iel)?|Dan(?:iel)?|Hos(?:ea)?|Joel|Amos|Obad(?:iah)?|Jon(?:ah)?|Mic(?:ah)?|Nah(?:um)?|Hab(?:akkuk)?|"
    r"Zeph(?:aniah)?|Hag(?:gai)?|Zech(?:ariah)?|Mal(?:achi)?|Matt(?:hew)?|Mark|Luke|John|Acts|Rom(?:ans)?|"
    r"Cor(?:inthians)?|Gal(?:atians)?|Eph(?:esians)?|Phil(?:ippians)?|Col(?:ossians)?|Thess(?:alonians)?|"
    r"Tim(?:othy)?|Tit(?:us)?|Philem|Heb(?:rews)?|Jam?es|Pet(?:er)?|Jude|Rev(?:elation)?)\.?\s*"
    r"\d{1,3}(?:\s*[:\u2013-]\s*\d{1,3})?",
    re.IGNORECASE,
)

# Configurable keyterm → root map (claim-audit-spec §7, CA-6).
# Hebrew roots are consonantal (pointing stripped before matching); Greek roots
# are diacritic-stripped prefixes. A keyterm claimed in prose while its root is
# absent from the verse's source text → warning.
CLAIM_KEYTERMS: dict[str, dict[str, tuple[str, ...]]] = {
    "covenant": {"hebrew": ("ברית",), "greek": ("διαθηκ",)},
    "hesed": {"hebrew": ("חסד",)},
    "torah": {"hebrew": ("תורה", "תורת")},
    "grace": {"greek": ("χαρι",)},
    "gospel": {"greek": ("ευαγγελ",)},
}

_GLOSS_STOPWORDS = {"the", "and", "with", "from", "that", "this", "same", "one",
                    "for", "not", "any", "some", "widest", "sense", "very",
                    "also", "used", "which", "who", "whom", "whose"}
_IRREGULAR_PLURAL = {"women": "woman", "wives": "wife", "men": "man",
                     "children": "child", "feet": "foot", "teeth": "tooth"}


def _strip_source(text: str) -> str:
    """Strip Hebrew pointing and Greek diacritics for root-presence matching."""
    import unicodedata
    out = re.sub(r"[\u0591-\u05C7]", "", text)
    decomposed = unicodedata.normalize("NFD", out)
    return "".join(ch for ch in decomposed if not ("\u0300" <= ch <= "\u036f")).casefold()


def _stem(w: str) -> str:
    w = w.lower().strip(".,;:!?\"'()\u2019'")
    if w in _IRREGULAR_PLURAL:
        return _IRREGULAR_PLURAL[w]
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and len(w) > 3:
        return w[:-1]
    return w


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+|\n+", text or "") if s.strip()]


def _mention_stems(kw) -> set[str]:
    """Stems a prose sentence may use to refer to this key word: transliteration
    tokens, the source-script surface form, and the first gloss head(s)."""
    stems: set[str] = set()
    for tok in re.findall(r"[A-Za-z\u2019'-]{3,}", kw.transliteration or ""):
        stems.add(_stem(tok))
    if kw.word and (re.search(r"[\u0590-\u05ff]", kw.word) or re.search(r"[\u0370-\u03ff]", kw.word)):
        stems.add(kw.word)
    first_piece = re.split(r"[/,;(]", kw.lexical_range or "")[0]
    for tok in re.findall(r"[A-Za-z\u2019'-]{3,}", first_piece)[:2]:
        if tok.lower() not in _GLOSS_STOPWORDS:
            stems.add(_stem(tok))
    return stems


def claim_audit_issues(analysis: VerseAnalysis) -> list[ValidationIssue]:
    """Machine-checkable claim-audit subset (spec §7). All warnings."""
    issues: list[ValidationIssue] = []
    is_ot = analysis.testament == "OT"

    # Prose units: diffs + insights (claims), sentence views for CA-3/CA-4/CA-6
    prose_units: list[tuple[str, str]] = []
    for i, d in enumerate(analysis.diffs):
        prose_units.append((f"diffs[{i}].what_lost", d.what_lost or ""))
        prose_units.append((f"diffs[{i}].why_matters", d.why_matters or ""))
    for i, ins in enumerate(analysis.insights):
        prose_units.append((f"insights[{i}].description", ins.description or ""))
    expanded_sents = [("expanded_translation", s) for s in _sentences(analysis.expanded_translation)]

    # CA-6 root-presence: keyterm claimed while its root is absent from source text
    source_text = analysis.hebrew_text if is_ot else analysis.greek_text
    if source_text:
        stripped = _strip_source(source_text)
        for term, roots_by_lang in CLAIM_KEYTERMS.items():
            roots = roots_by_lang.get("hebrew" if is_ot else "greek")
            if not roots or any(r in stripped for r in roots):
                continue
            term_re = re.compile(rf"\b{term}s?\b", re.IGNORECASE)
            for label, text in prose_units + expanded_sents:
                for s in _sentences(text):
                    if term_re.search(s) and not PROSE_HEDGE_RE.search(s):
                        issues.append(ValidationIssue(
                            "warning", label,
                            f"[CA-6] keyterm '{term}' asserted unhedged but its root is absent "
                            f"from this verse's source text — relocate to insights/further_study "
                            f"with an evidence_status tag",
                        ))
                        break

    # CA-1/CA-2 citation-presence: meaning/contrast claim without a citation in
    # the same unit — a diff's what_lost + why_matters count as one bullet.
    ca12_units: list[tuple[str, str]] = []
    for i, d in enumerate(analysis.diffs):
        ca12_units.append((f"diffs[{i}]", f"{d.what_lost or ''} {d.why_matters or ''}"))
    for i, ins in enumerate(analysis.insights):
        ca12_units.append((f"insights[{i}]", ins.description or ""))
    for label, text in ca12_units:
        if (MEANING_CLAIM_RE.search(text) or CONTRAST_RE.search(text)) \
                and not _SCRIPTURE_CITATION_RE.search(text):
            issues.append(ValidationIssue(
                "warning", label,
                "[CA-1/CA-2] meaning/contrast claim without a scripture citation in the same "
                "unit — cite a parallel construction or restate positively",
            ))

    # CA-4 certainty lexicon: strong-intent verb without adjacent citation or hedge
    for label, text in prose_units + expanded_sents:
        for s in _sentences(text):
            if CERTAINTY_RE.search(s) and not _SCRIPTURE_CITATION_RE.search(s) \
                    and not PROSE_HEDGE_RE.search(s):
                snippet = (s[:80] + "…") if len(s) > 80 else s
                issues.append(ValidationIssue(
                    "warning", label,
                    f"[CA-4] strong-intent verb without adjacent citation or hedge: \"{snippet}\" "
                    f"— cite a parallel or hedge ('as if', 'invites', 'may recall')",
                ))
                break

    # CA-3 table-prose consistency: prose asserts what a hedged table cell hedges
    for kw in analysis.key_words:
        cell = f"{kw.lexical_range} {kw.nuance}"
        if not CELL_HEDGE_RE.search(cell):
            continue
        stems = _mention_stems(kw)
        if not stems:
            continue
        for label, text in prose_units + expanded_sents:
            for s in _sentences(text):
                sent_stems = {_stem(t) for t in re.findall(r"[A-Za-z\u2019'-]{3,}", s)}
                script_hit = bool(kw.word) and kw.word in s
                if not (script_hit or (sent_stems & stems)):
                    continue
                if (NEGATION_RE.search(s) or ABSOLUTE_RE.search(s)) and not PROSE_HEDGE_RE.search(s):
                    issues.append(ValidationIssue(
                        "warning", label,
                        f"[CA-3] prose asserts unhedged one-side meaning of "
                        f"'{kw.transliteration or kw.word}' while the word table hedges — "
                        f"carry the hedge into the prose",
                    ))
                    break

    return issues


def passes(issues: list[ValidationIssue]) -> bool:
    return not any(i.severity == "error" for i in issues)


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(i.severity == "error" for i in issues)
