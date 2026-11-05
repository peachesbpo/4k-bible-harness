"""orchestrator.py — Helpers for the opencode main agent.

The harness CLI is pure Python (no LLM calls). The opencode main agent drives
the loop:
  1. `harness next <run_id>`       → get next pending verse's bundle + prompt
  2. spawn a Task subagent with that prompt (fresh context, no kv-cache bloat)
  3. `harness ingest <run_id>`     ← pipe subagent's JSON response to stdin
  4. repeat

This module provides the helpers that the CLI calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .retrieve import fetch_verse, VerseBundle
from .schema import VerseAnalysis, normalize_review
from .prompts import analyst_prompt, reviewer_prompt, corrector_prompt
from .state import Manifest, init_manifest, update_verse_status, run_dir
from .writer import write_verse, load_verse_analysis
from .validators import validate, has_errors, normalize_source_text
from .summary import write_summary


def _parse_passage(passage: str) -> tuple[str, int, int, int]:
    """Parse 'Matthew 23:8-12' → ('Matthew', 23, 8, 12). Also 'Matthew 23:8' or 'Matthew 23'."""
    import re
    m = re.match(r"^\s*([A-Za-z1-3]+\s*[A-Za-z]+)\s+(\d+)(?::(\d+)(?:-(\d+))?)?\s*$", passage)
    if not m:
        raise ValueError(f"Invalid passage: {passage!r}")
    book = m.group(1).strip()
    chapter = int(m.group(2))
    v_start = int(m.group(3)) if m.group(3) else None
    v_end = int(m.group(4)) if m.group(4) else v_start
    return book, chapter, v_start, v_end


def plan_passage(passage: str) -> tuple[str, Path]:
    """Create a run for a passage. Returns (run_id, manifest_path)."""
    from .state import run_id_for
    book, chapter, v_start, v_end = _parse_passage(passage)
    if v_start is None:
        # Full chapter
        from .retrieve import chapter_verse_count
        v_start = 1
        v_end = chapter_verse_count(book, chapter)
    verses = [(chapter, v) for v in range(v_start, v_end + 1)]
    run_id = run_id_for(book, chapter, v_start, v_end)
    manifest, path = init_manifest(run_id, book, verses,
                                    chapter_start=chapter, chapter_end=chapter,
                                    verse_start=v_start, verse_end=v_end)
    return run_id, path


def plan_book(book: str) -> tuple[str, Path]:
    """Create a verse-by-verse run for an entire book."""
    from .retrieve import book_chapter_count, chapter_verse_count, resolve_book
    from .state import whole_book_run_id
    canonical = resolve_book(book)
    run_id = whole_book_run_id(canonical)
    verses: list[tuple[int, int]] = []
    n_chapters = book_chapter_count(canonical)
    for ch in range(1, n_chapters + 1):
        n_v = chapter_verse_count(canonical, ch)
        for v in range(1, n_v + 1):
            verses.append((ch, v))
    manifest, path = init_manifest(run_id, canonical, verses, whole_book=True,
                                   chapter_start=1, chapter_end=n_chapters)
    return run_id, path


def next_pending_verse(run_id: str) -> dict | None:
    """Return the next pending verse's dispatch payload, or None if run is complete.

    Returns: {"book", "chapter", "verse", "bundle": {...}, "prompt": "..."}
    """
    rd = run_dir(run_id)
    mp = rd / "manifest.json"
    if not mp.exists():
        return None
    m = Manifest.load(mp)
    for key, v in m.verses.items():
        if v["status"] in ("pending", "failed"):
            ch, v_num = v["chapter"], v["verse"]
            bundle = fetch_verse(v["book"], ch, v_num, include_etymology=True)
            passage_ref = run_id.replace("_", " ")
            prompt = analyst_prompt(bundle, passage_ref=passage_ref)
            return {
                "book": v["book"], "chapter": ch, "verse": v_num,
                "bundle": bundle.to_prompt_dict(), "prompt": prompt,
            }
    return None


def ingest_analysis(run_id: str, analysis_json: str, force: bool = False) -> dict:
    """Ingest a subagent's VerseAnalysis JSON. Validates and updates manifest."""
    rd = run_dir(run_id)
    mp = rd / "manifest.json"
    if not mp.exists():
        return {"error": f"Run not found: {run_id}"}
    try:
        data = json.loads(analysis_json)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    try:
        analysis = VerseAnalysis.from_dict(data)
    except TypeError as e:
        return {"error": f"Schema mismatch: {e}"}

    # Validate
    bundle = fetch_verse(analysis.book, analysis.chapter, analysis.verse, include_etymology=True)
    # Combining-mark drift repair (fix-spec 2026-09-15 #3): NFC-equivalent
    # dagesh/qamats-order drift is rewritten to the bundle's exact bytes here,
    # so it is caught/repaired at ingest instead of failing the reviewer's
    # byte-exact check 1 (12:17, 12:19).
    bundle_source_text = bundle.hebrew_text if bundle.testament == "OT" else bundle.greek_text
    drift_note = normalize_source_text(analysis, bundle_source_text)
    # Build strongs number set (language-aware: H#### for OT, G#### for NT)
    if bundle.testament == "OT":
        strongs_numbers = {w.strongs.upper() for w in bundle.hebrew_words if w.strongs}
        strongs_numbers |= {w.strongs.upper().lstrip("H") for w in bundle.hebrew_words if w.strongs}
    else:
        strongs_numbers = {w.get("number", "").upper() for w in bundle.strongs}
        strongs_numbers |= {w.get("number", "").upper().lstrip("G") for w in bundle.strongs}
    issues = validate(analysis,
                      bundle_strongs_numbers=strongs_numbers,
                      bundle_cross_refs=bundle.cross_refs,
                      spoken_jesus_material=bundle.spoken_jesus_material,
                      bundle_source_text=bundle_source_text)
    validators_ok = not has_errors(issues)

    # Write
    md_path, json_path = write_verse(analysis, run_id, force=force)

    # Update manifest (language-aware purity field)
    purity_ok = bundle.hebrew_pure if bundle.testament == "OT" else analysis.greek_pure
    new_status = "analyzed" if validators_ok else "analyzed"  # analyzed either way; review is next
    update_verse_status(mp, analysis.chapter, analysis.verse, new_status,
                         analysis_path=md_path.name, sidecar_path=json_path.name,
                         purity_ok=purity_ok, validators_ok=validators_ok)
    return {
        "verse": f"{analysis.book} {analysis.chapter}:{analysis.verse}",
        "status": new_status,
        "validators_ok": validators_ok,
        "issues": [i.to_dict() for i in issues],
        "md_path": str(md_path),
        "json_path": str(json_path),
        **({"source_normalized": drift_note} if drift_note else {}),
    }


def next_review_verse(run_id: str) -> dict | None:
    """Return the next verse needing review (status=analyzed)."""
    rd = run_dir(run_id)
    mp = rd / "manifest.json"
    if not mp.exists():
        return None
    m = Manifest.load(mp)
    for key, v in m.verses.items():
        if v["status"] == "analyzed":
            ch, v_num = v["chapter"], v["verse"]
            sidecar = rd / v.get("sidecar_path", "")
            if not sidecar.exists():
                continue
            analysis = load_verse_analysis(sidecar)
            bundle = fetch_verse(v["book"], ch, v_num, include_etymology=True)
            prompt = reviewer_prompt(analysis, bundle)
            m = update_verse_status(mp, ch, v_num, "reviewing")
            m.dispatched_review_verse = m.verse_key(ch, v_num)
            m.save(mp)
            return {
                "book": v["book"], "chapter": ch, "verse": v_num,
                "analysis": analysis.to_dict(),
                "bundle": bundle.to_prompt_dict(),
                "prompt": prompt,
            }
    return None


def ingest_review(run_id: str, review_json: str) -> dict:
    """Ingest a reviewer's verdict. If invalid, mark for correction; else mark reviewed.

    Review JSON is normalized per the claim-audit layer (spec §6.3): corrections
    gain optional rule/claim/verdict fields; the persisted review.json carries
    summary.claim_audit {total, licensed, downgraded, cut}.
    """
    rd = run_dir(run_id)
    mp = rd / "manifest.json"
    try:
        data = json.loads(review_json)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    result = normalize_review(data)
    # Target the verse whose dispatch next_review_verse returned (fix-spec
    # 2026-09-15 #1) — not the first verse in reviewing status. Positional
    # targeting misfiled verdicts whenever an earlier verse was stuck in
    # reviewing with a corrections sidecar awaiting the correction cycle
    # (v.18→v.17 on 8/9; 8:5→8:4; 12:18 consumed on 9/14).
    m = Manifest.load(mp)
    target = None
    dispatched = m.dispatched_review_verse
    if dispatched and dispatched in m.verses \
            and m.verses[dispatched]["status"] == "reviewing":
        target = m.verses[dispatched]
    if target is None:
        # Legacy fallback (pre-dispatch-field manifests): first reviewing verse
        for key, v in m.verses.items():
            if v["status"] == "reviewing":
                target = v
                break
    if not target:
        return {"error": "no verse in reviewing state"}
    ch, v_num = target["chapter"], target["verse"]
    # Verdict consumed — clear the dispatch record regardless of outcome
    m.dispatched_review_verse = None
    m.save(mp)
    valid = result.valid
    corrections = [c.to_dict() for c in result.corrections]
    # Normalization note: claim-audit findings must carry rule AND claim
    incomplete_ca = [i for i, c in enumerate(result.corrections)
                     if c.rule and not c.claim]
    if valid or not corrections:
        # Persist the verdict as a sidecar too (fix-spec 2026-09-15 #2): mirrors
        # the .review.json shape so history/audit survives. Suffix .valid.json
        # keeps it out of the *.review.json glob — next_correction_verse and
        # the SUMMARY claim-audit loader must not see approved verdicts as
        # pending corrections.
        review_path = rd / f"{target['book']}_{ch}-{v_num}.review.valid.json"
        review_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        update_verse_status(mp, ch, v_num, "reviewed")
        return {"verse": f"{target['book']} {ch}:{v_num}", "valid": True, "status": "reviewed",
                "review_path": str(review_path),
                "claim_audit": result.summary["claim_audit"]}
    # Need correction — store normalized corrections and mark
    corrections_path = rd / f"{target['book']}_{ch}-{v_num}.review.json"
    corrections_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    update_verse_status(mp, ch, v_num, "reviewing", last_error=f"{len(corrections)} corrections")
    out = {
        "verse": f"{target['book']} {ch}:{v_num}",
        "valid": False,
        "corrections": corrections,
        "corrections_path": str(corrections_path),
        "claim_audit": result.summary["claim_audit"],
        "status": "needs_correction",
    }
    if incomplete_ca:
        out["normalization_notes"] = [
            f"corrections[{i}] cites {result.corrections[i].rule} but is missing 'claim' "
            f"(spec §6.2: rule-citing findings must quote the offending claim)"
            for i in incomplete_ca
        ]
    return out


def next_correction_verse(run_id: str) -> dict | None:
    """Return the next verse needing correction (has a .review.json sidecar)."""
    rd = run_dir(run_id)
    mp = rd / "manifest.json"
    if not mp.exists():
        return None
    m = Manifest.load(mp)
    for key, v in m.verses.items():
        ch, v_num = v["chapter"], v["verse"]
        review_path = rd / f"{v['book']}_{ch}-{v_num}.review.json"
        if review_path.exists() and v["status"] != "done":
            sidecar = rd / v.get("sidecar_path", "")
            if not sidecar.exists():
                continue
            analysis = load_verse_analysis(sidecar)
            review_notes = review_path.read_text("utf-8")
            prompt = corrector_prompt(analysis, review_notes)
            update_verse_status(mp, ch, v_num, "correcting")
            return {
                "book": v["book"], "chapter": ch, "verse": v_num,
                "analysis": analysis.to_dict(),
                "review_notes": review_notes,
                "prompt": prompt,
            }
    return None


def finalize_verse(run_id: str, book: str, ch: int, v: int,
                  corrected_json: str | None = None, force: bool = False) -> dict:
    """Apply a corrected analysis (or mark an already-reviewed verse as done)."""
    rd = run_dir(run_id)
    mp = rd / "manifest.json"
    if corrected_json:
        return ingest_analysis(run_id, corrected_json, force=force)
    # No correction — just mark done
    update_verse_status(mp, ch, v, "done")
    return {"verse": f"{book} {ch}:{v}", "status": "done"}


def mark_done(run_id: str) -> dict:
    """Mark all reviewed verses as done. Returns count."""
    rd = run_dir(run_id)
    mp = rd / "manifest.json"
    m = Manifest.load(mp)
    count = 0
    for key, v in m.verses.items():
        if v["status"] == "reviewed":
            update_verse_status(mp, v["chapter"], v["verse"], "done")
            count += 1
    return {"marked_done": count}


def render_run(run_id: str, passage_ref: str | None = None, html: bool = True, pdf: bool = True) -> dict:
    """Render the SUMMARY for a run."""
    if passage_ref is None:
        passage_ref = run_id.replace("_", " ")
    return write_summary(run_id, passage_ref, generate_html=html, generate_pdf=pdf)


def run_status(run_id: str) -> dict:
    rd = run_dir(run_id)
    mp = rd / "manifest.json"
    if not mp.exists():
        return {"error": f"run not found: {run_id}"}
    m = Manifest.load(mp)
    return m.summary()


def list_runs() -> list[dict]:
    from .state import RUNS_DIR
    if not RUNS_DIR.exists():
        return []
    out = []
    for d in sorted(RUNS_DIR.iterdir()):
        mp = d / "manifest.json"
        if mp.exists():
            m = Manifest.load(mp)
            out.append(m.summary())
    return out
