"""cache.py — On-disk JSON cache for verse retrieval.

Caches the parsed JSON of individual verse files keyed by (version, book, chapter,
verse). Uses mtim of the source file to invalidate. Prevents re-reading + re-parsing
the 37MB Greek repo and 140MB WEB repo on every passage run.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = SCRIPT_DIR / ".cache"


def _cache_path(version: str, book: str, chapter: int, verse: int) -> Path:
    return CACHE_DIR / version / book / f"{chapter:03d}" / f"{verse:03d}.json"


def get_cached_verse(version: str, book: str, chapter: int, verse: int,
                    source_file: Path) -> tuple[dict | None, bool]:
    """Return (data, hit). `source_file` is the original JSON file path.

    Cache hit requires: cache file exists AND (mtime, size) match the source file.
    Using both mtime_ns and size guards against filesystems with coarse mtime
    resolution. Returns (data, True) on hit, (None, False) on miss.
    """
    cp = _cache_path(version, book, chapter, verse)
    if not source_file.exists():
        return None, False
    src_stat = source_file.stat()
    src_key = (src_stat.st_mtime_ns, src_stat.st_size)
    if not cp.exists():
        return None, False
    try:
        meta = json.loads(cp.read_text("utf-8"))
        if tuple(meta.get("src_key", ())) != src_key:
            return None, False
        return meta.get("data"), True
    except (json.JSONDecodeError, IOError):
        return None, False


def put_cached_verse(version: str, book: str, chapter: int, verse: int,
                    source_file: Path, data: Any) -> None:
    """Write `data` to the cache with the source file's (mtime, size) as the key."""
    cp = _cache_path(version, book, chapter, verse)
    cp.parent.mkdir(parents=True, exist_ok=True)
    if source_file.exists():
        st = source_file.stat()
        src_key = [st.st_mtime_ns, st.st_size]
    else:
        src_key = [0, 0]
    payload = {"src_key": src_key, "data": data}
    cp.write_text(json.dumps(payload, ensure_ascii=False))


def clear(version: str | None = None) -> int:
    """Clear the cache (all or one version). Returns number of files removed."""
    if not CACHE_DIR.exists():
        return 0
    removed = 0
    if version:
        target = CACHE_DIR / version
        if target.exists():
            for f in target.rglob("*"):
                if f.is_file():
                    f.unlink()
                    removed += 1
            # Remove empty dirs
            for d in sorted(target.rglob("*"), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
            if target.is_dir() and not any(target.iterdir()):
                target.rmdir()
    else:
        for f in CACHE_DIR.rglob("*"):
            if f.is_file():
                f.unlink()
                removed += 1
        for d in sorted(CACHE_DIR.rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
    return removed


def stats() -> dict:
    """Return cache statistics."""
    if not CACHE_DIR.exists():
        return {"files": 0, "bytes": 0}
    files = 0
    bytes_ = 0
    for f in CACHE_DIR.rglob("*"):
        if f.is_file():
            files += 1
            bytes_ += f.stat().st_size
    return {"files": files, "bytes": bytes_}
