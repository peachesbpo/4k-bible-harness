"""schema.py — VerseAnalysis dataclass.

The structured intermediate that flows between subagents and the writer.
A subagent returns this as JSON; the writer renders it to markdown using
template_verse.md via Jinja2.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class DiffEntry:
    """One nuance gap: a phrase in the English baseline that loses something.

    Layer-gap fields (optional) make explicit which layers the diff spans.
    - NT (OT-echo verses): hebrew_root + greek_choice + web_rendering
    - OT: hebrew_root + asv_rendering (no Greek layer)
    Each layer is authoritative for itself, not for the layer above or below it.
    """
    baseline_phrase: str        # the English baseline phrase (must appear in the baseline text)
    what_lost: str             # what nuance is lost
    why_matters: str           # why it matters theologically
    # Layer-gap (optional; populated for OT-echo verses and OT diffs)
    hebrew_root: str | None = None        # e.g. "yârash (H3423) — seize, dispossess"
    greek_choice: str | None = None       # NT only: e.g. "klēronomeō (G2816) — receive as heir"
    web_rendering: str | None = None      # NT only: e.g. "inherit"
    asv_rendering: str | None = None      # OT only: e.g. "inherit"
    gap_type: str | None = None           # "hebrew_to_greek"|"greek_to_web"|"hebrew_to_web"|"hebrew_to_asv"
    evidence_status: str | None = None     # "textual" | "inferential" | "speculative"


@dataclass
class KeyWord:
    """One key word from the source text.

    NT uses `parsing` (e.g. "V-ASP-2P"). OT uses `morphology` (decoded WLC,
    e.g. "Noun common feminine singular absolute") + `stem` (Qal/Hiphil/etc.).
    Both share word/transliteration/strongs/lexical_range/nuance.
    """
    word: str                  # surface form (Greek or Hebrew)
    transliteration: str
    strongs: str               # e.g. "G2564" (NT) or "H7225" (OT)
    parsing: str = ""          # NT: e.g. "V-ASP-2P"
    lexical_range: str = ""    # gloss range
    nuance: str = ""           # what this word contributes here
    # OT-only fields (defaults allow NT construction without these)
    morphology: str = ""      # OT: decoded WLC morph, e.g. "Noun common feminine singular absolute"
    stem: str | None = None   # OT: verbal stem (Qal/Hiphil/etc.); None for non-verbs


@dataclass
class Insight:
    title: str
    description: str
    # Claim-audit tagging (spec §5): interpretive claims default inferential;
    # reviewer/corrector set this when a hedge or tag is required (CA-4/CA-5).
    evidence_status: str | None = None


@dataclass
class VerseAnalysis:
    """The full structured analysis for one verse.

    Testament-aware: NT verses populate greek_text/web_text/greek_pure;
    OT verses populate hebrew_text/asv_text/hebrew_pure. The defaults allow
    from_dict to work for both — an OT analyst JSON that omits greek_text
    will fall back to the empty-string default.
    """
    # Identity
    book: str
    chapter: int
    verse: int
    reference: str            # "Matthew 23:8" or "Genesis 1:1"

    # Source (verified) — NT
    greek_text: str = ""
    web_text: str = ""
    greek_pure: bool = False

    # Source (verified) — OT
    hebrew_text: str = ""
    asv_text: str = ""
    hebrew_pure: bool = False
    original_language: str = "greek"   # "greek" | "hebrew"
    testament: str = "NT"               # "OT" | "NT"

    # Outputs
    expanded_translation: str = ""    # clean English, parenthetical notes
    diffs: list[DiffEntry] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)
    key_words: list[KeyWord] = field(default_factory=list)

    # Supporting
    grammar_notes: str = ""
    syntax_notes: str = ""
    prep_notes: str = ""
    context_notes: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    further_study: list[str] = field(default_factory=list)

    # Provenance
    analyst: str = "Peaches (4K Bible Translation Harness)"
    review_status: str = "Draft - Ready for Review"

    # Hermeneutic (v0.3): the analyst confirms it named the Aramaic gap
    # for spoken-Jesus material with OT echoes. Reviewer flags False.
    # OT verses: always False (the Aramaic-gap rule is NT-only).
    aramaic_gap_acknowledged: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "VerseAnalysis":
        d = normalize_legacy_analysis(dict(d))
        d["diffs"] = [DiffEntry(**x) if isinstance(x, dict) else x for x in d.get("diffs", [])]
        d["insights"] = [Insight(**x) if isinstance(x, dict) else x for x in d.get("insights", [])]
        d["key_words"] = [KeyWord(**x) if isinstance(x, dict) else x for x in d.get("key_words", [])]
        # Filter out keys that aren't dataclass fields (be tolerant of extra fields)
        import dataclasses
        valid_keys = {f.name for f in dataclasses.fields(cls)}
        d = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**d)


# ── Legacy sidecar normalization (read-time only, disk sidecars never rewritten) ─
# July-2026-era sidecars predate the ESV→WEB baseline switch: they carry
# `esv_text`, per-diff `esv_rendering`, and `*_to_esv` gap_type values. Every
# analysis read path (next-review / next-correction sidecar loads, stdin
# ingest) routes through from_dict, which maps legacy names to the current
# schema in memory. The on-disk sidecar is left untouched.

_LEGACY_BASELINE = {"NT": "web", "OT": "asv"}


def _legacy_testament(d: dict) -> str:
    """Best-effort testament detection for legacy dicts (explicit fields first)."""
    t = d.get("testament")
    if t in ("NT", "OT"):
        return t
    lang = d.get("original_language")
    if lang == "hebrew":
        return "OT"
    if lang == "greek":
        return "NT"
    if d.get("hebrew_text") or d.get("asv_text"):
        return "OT"
    return "NT"


def _normalize_legacy_diff(x: dict, base: str) -> dict:
    x = dict(x)
    if "esv_rendering" in x:
        x[f"{base}_rendering"] = x.pop("esv_rendering")
    gt = x.get("gap_type")
    if gt == "greek_to_esv":
        x["gap_type"] = "greek_to_web"
    elif gt == "hebrew_to_esv":
        x["gap_type"] = f"hebrew_to_{base}"
    return x


def normalize_legacy_analysis(d: dict) -> dict:
    """Map ESV-era field names to the current schema. Returns a (shallow) copy.

    Legacy markers: top-level `esv_text`, per-diff `esv_rendering`, and
    `*_to_esv` gap_type values. NT maps to web_*, OT to asv_*. Dicts without
    legacy markers are returned as-is (copy), untouched.
    """
    diffs = d.get("diffs") or []
    has_legacy = "esv_text" in d or any(
        isinstance(x, dict) and "esv_rendering" in x for x in diffs
    )
    if not has_legacy:
        return d
    d = dict(d)
    testament = _legacy_testament(d)
    base = _LEGACY_BASELINE[testament]
    # Legacy dicts predate the testament/original_language fields; stamp the
    # detected values so downstream rendering (md/summary) treats OT as OT.
    d["testament"] = testament
    d["original_language"] = "hebrew" if testament == "OT" else "greek"
    if "esv_text" in d:
        d[f"{base}_text"] = d.pop("esv_text")
    d["diffs"] = [
        _normalize_legacy_diff(x, base) if isinstance(x, dict) else x
        for x in diffs
    ]
    return d


# ── Review-side schema (claim-audit layer, spec §6.3) ─────────────────────────

VALID_CA_RULES = ("CA-1", "CA-2", "CA-3", "CA-4", "CA-5", "CA-6", "CA-7")
VALID_VERDICTS = ("licensed", "downgraded", "cut")
VALID_SEVERITIES = ("error", "warning")


@dataclass
class ReviewCorrection:
    """One reviewer correction.

    Claim-audit findings (check 14) additionally carry `rule` ("CA-1".."CA-7"),
    `claim` (the exact quoted offending text), and `verdict`
    ("licensed" | "downgraded" | "cut"). Structural corrections leave these None.
    """
    severity: str                       # "error" | "warning"
    field: str
    index: int | None
    issue: str
    fix: str = ""
    rule: str | None = None
    claim: str | None = None
    verdict: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "ReviewCorrection":
        d = dict(d)
        idx = d.get("index")
        if not isinstance(idx, int):
            idx = None
        rule = d.get("rule")
        if rule not in VALID_CA_RULES:
            rule = None
        verdict = d.get("verdict")
        if verdict not in VALID_VERDICTS:
            verdict = None
        severity = d.get("severity")
        if severity not in VALID_SEVERITIES:
            severity = "warning"
        return cls(
            severity=severity,
            field=str(d.get("field", "")),
            index=idx,
            issue=str(d.get("issue", "")),
            fix=str(d.get("fix", "")),
            rule=rule,
            claim=d.get("claim") if isinstance(d.get("claim"), str) else None,
            verdict=verdict,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReviewResult:
    """Normalized reviewer output.

    `summary` is always an object: {"text": str, "claim_audit": {total, licensed, downgraded, cut}}.
    Legacy string summaries are wrapped; a missing claim-audit tally is derived
    from the rule-citing corrections.
    """
    valid: bool
    corrections: list[ReviewCorrection]
    summary: dict

    @classmethod
    def from_dict(cls, d: dict) -> "ReviewResult":
        corrections = [ReviewCorrection.from_dict(c) for c in d.get("corrections", []) if isinstance(c, dict)]
        raw_summary = d.get("summary", "")
        reviewer_audit: dict | None = None
        if isinstance(raw_summary, dict):
            text = str(raw_summary.get("text") or raw_summary.get("summary") or "")
            ca = raw_summary.get("claim_audit")
            reviewer_audit = ca if isinstance(ca, dict) else None
        else:
            text = str(raw_summary)
        derived = derive_claim_audit(corrections)
        claim_audit = {
            "total": (reviewer_audit or {}).get("total", derived["total"]),
            "licensed": (reviewer_audit or {}).get("licensed", derived["licensed"]),
            "downgraded": (reviewer_audit or {}).get("downgraded", derived["downgraded"]),
            "cut": (reviewer_audit or {}).get("cut", derived["cut"]),
        }
        # Reviewer-supplied top-level tally (new-style output) also honored
        top_audit = d.get("claim_audit")
        if isinstance(top_audit, dict):
            for k in ("total", "licensed", "downgraded", "cut"):
                if k in top_audit:
                    claim_audit[k] = top_audit[k]
        return cls(valid=bool(d.get("valid", False)), corrections=corrections,
                   summary={"text": text, "claim_audit": claim_audit})

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "corrections": [c.to_dict() for c in self.corrections],
            "summary": {"text": self.summary.get("text", ""),
                        "claim_audit": dict(self.summary.get("claim_audit", {}))},
        }


def derive_claim_audit(corrections: list[ReviewCorrection]) -> dict:
    """Tally claim-audit verdicts from rule-citing corrections.

    A rule-citing correction with no explicit verdict counts as "downgraded"
    (a correction implies the claim changed). "licensed" claims produce no
    correction, so the derived licensed count is 0 unless stated by the reviewer.
    """
    rule_citing = [c for c in corrections if c.rule]
    licensed = sum(1 for c in rule_citing if c.verdict == "licensed")
    cut = sum(1 for c in rule_citing if c.verdict == "cut")
    downgraded = len(rule_citing) - licensed - cut
    return {"total": len(rule_citing), "licensed": licensed, "downgraded": downgraded, "cut": cut}


def normalize_review(data: dict) -> "ReviewResult":
    """Coerce a raw reviewer JSON dict into a ReviewResult (spec §6.3)."""
    return ReviewResult.from_dict(data)
