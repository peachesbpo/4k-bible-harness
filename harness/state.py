"""state.py — Run state and per-verse manifest.

Each run (passage or whole-book iterative) lives in runs/<run_id>/ with a
manifest.json tracking per-verse status. Statuses:

    pending → analyzing → analyzed → reviewing → reviewed → correcting → done

A verse is `done` when its .md + .json sidecar are written and validated.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = SCRIPT_DIR / "runs"

# Status values in order
STATUSES = ["pending", "analyzing", "analyzed", "reviewing", "reviewed", "correcting", "done", "failed"]


def run_id_for(book: str, chapter: int, verse_start: int | None, verse_end: int | None) -> str:
    """Build a run id like 'Matthew_23-8-12' or 'Matthew_23-8' or 'Matthew_ch23'."""
    b = book.replace(" ", "_")
    if verse_start is None and verse_end is None:
        return f"{b}_ch{chapter}"
    if verse_start == verse_end:
        return f"{b}_{chapter}-{verse_start}"
    end = verse_end if verse_end is not None else verse_start
    return f"{b}_{chapter}-{verse_start}-{end}"


def whole_book_run_id(book: str) -> str:
    return f"{book.replace(' ', '_')}_verse_by_verse"


def run_dir(run_id: str) -> Path:
    d = RUNS_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class VerseStatus:
    book: str
    chapter: int
    verse: int
    status: str = "pending"
    attempts: int = 0
    last_error: str | None = None
    analysis_path: str | None = None     # .md path (relative to run_dir)
    sidecar_path: str | None = None      # .json path
    purity_ok: bool | None = None
    validators_ok: bool | None = None
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Manifest:
    run_id: str
    book: str
    chapter_start: int | None = None
    chapter_end: int | None = None
    verse_start: int | None = None
    verse_end: int | None = None
    whole_book: bool = False
    created_at: float = field(default_factory=time.time)
    verses: dict[str, dict] = field(default_factory=dict)  # key = "ch:v"
    # Verse key ("ch:v") dispatched by the most recent next_review_verse call.
    # ingest_review targets THIS verse, not the first verse in reviewing status
    # (fix-spec 2026-09-15 #1: positional targeting misfiled verdicts when an
    # earlier verse was stuck in reviewing). Cleared when the verdict lands.
    dispatched_review_verse: str | None = None

    def verse_key(self, ch: int, v: int) -> str:
        return f"{ch}:{v}"

    def get(self, ch: int, v: int) -> VerseStatus | None:
        d = self.verses.get(self.verse_key(ch, v))
        return VerseStatus(**d) if d else None

    def set(self, vs: VerseStatus) -> None:
        vs.updated_at = time.time()
        self.verses[self.verse_key(vs.chapter, vs.verse)] = vs.to_dict()

    def set_status(self, ch: int, v: int, status: str, **extra) -> None:
        key = self.verse_key(ch, v)
        cur = self.verses.get(key, VerseStatus(self.book, ch, v).to_dict())
        cur.update(extra)
        cur["status"] = status
        cur["updated_at"] = time.time()
        self.verses[key] = cur

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for v in self.verses.values():
            counts[v["status"]] = counts.get(v["status"], 0) + 1
        return {
            "run_id": self.run_id,
            "book": self.book,
            "total_verses": len(self.verses),
            "counts": counts,
            "done": counts.get("done", 0),
            "pending": counts.get("pending", 0),
            "failed": counts.get("failed", 0),
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        d = json.loads(path.read_text("utf-8"))
        verses = d.pop("verses", {})
        m = cls(**d)
        m.verses = verses
        return m


def init_manifest(run_id: str, book: str, verses: list[tuple[int, int]],
                  whole_book: bool = False,
                  chapter_start: int | None = None, chapter_end: int | None = None,
                  verse_start: int | None = None, verse_end: int | None = None) -> tuple[Manifest, Path]:
    """Create or load a manifest for this run."""
    rd = run_dir(run_id)
    path = rd / "manifest.json"
    if path.exists():
        m = Manifest.load(path)
        # Backfill any missing verses
        for ch, v in verses:
            if m.verse_key(ch, v) not in m.verses:
                m.set(VerseStatus(book=book, chapter=ch, verse=v))
        m.save(path)
        return m, path
    m = Manifest(
        run_id=run_id, book=book, whole_book=whole_book,
        chapter_start=chapter_start, chapter_end=chapter_end,
        verse_start=verse_start, verse_end=verse_end,
    )
    for ch, v in verses:
        m.set(VerseStatus(book=book, chapter=ch, verse=v))
    m.save(path)
    return m, path


def update_verse_status(path: Path, ch: int, v: int, status: str, **extra) -> Manifest:
    """Update a single verse's status in-place on disk. Returns reloaded manifest."""
    m = Manifest.load(path)
    m.set_status(ch, v, status, **extra)
    m.save(path)
    return m
