from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = SCRIPT_DIR / "runs"
STATUS_FILE = RUNS_DIR / "BACKFILL-STATUS.md"

EXCLUDE_RUNS = {"test_run", "progress.json"}

BOOK_ORDER_CACHE: dict[str, int] | None = None


def _book_order() -> dict[str, int]:
    global BOOK_ORDER_CACHE
    if BOOK_ORDER_CACHE is not None:
        return BOOK_ORDER_CACHE
    idx_path = SCRIPT_DIR / "harness" / "book_index.json"
    order: dict[str, int] = {}
    try:
        idx = json.loads(idx_path.read_text("utf-8"))
        books = idx.get("ot_books", {})
        books.update(idx.get("nt_books", {}))
        canon = [
            "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
            "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
            "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
            "Psalms", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon",
            "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea",
            "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
            "Zephaniah", "Haggai", "Zechariah", "Malachi",
            "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
            "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
            "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
            "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
            "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
        ]
        for i, b in enumerate(canon):
            order[b] = i
        for name in books:
            if name not in order:
                order[name] = 1000
    except Exception:
        order = {"Genesis": 0, "Matthew": 1}
    BOOK_ORDER_CACHE = order
    return order


def _recheck_index() -> set[str]:
    keys: set[str] = set()
    if not STATUS_FILE.exists():
        return keys
    in_section = False
    for line in STATUS_FILE.read_text("utf-8").splitlines():
        if line.startswith("## Rechecked index"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            m = re.match(r"^- `([^`]+)`\s+\|\s+`([^`]+)`", line)
            if m:
                keys.add(f"{m.group(1)}|{m.group(2)}")
    return keys


def _review_sidecar(rd: Path, run_id: str, v: dict) -> Path:
    stem = f"{v['book']}_{v['chapter']}-{v['verse']}"
    return rd / f"{stem}.review.json"


def _review_sidecar_candidates(rd: Path, run_id: str, v: dict) -> list[Path]:
    stem = f"{v['book']}_{v['chapter']}-{v['verse']}"
    return [rd / f"{stem}.review.valid.json", _review_sidecar(rd, run_id, v)]


def is_ca_rechecked(rd: Path, run_id: str, v: dict) -> bool:
    # Both sidecar namings carry claim-audit evidence:
    #   .review.valid.json — valid verdict (nightly/backfill record path)
    #   .review.json       — flagged verdict (corrections pending/recorded)
    for rp in _review_sidecar_candidates(rd, run_id, v):
        if not rp.exists():
            continue
        try:
            data = json.loads(rp.read_text("utf-8"))
        except Exception:
            continue
        s = data.get("summary")
        if isinstance(s, dict) and "claim_audit" in s:
            return True
    return False


def _run_tier(run_id: str) -> int:
    # PRIORITY ORDER (Michael, 2026-10-02):
    #   0: Genesis 12 runs (closest-to-present Genesis work)
    #   1: all old Matthew runs (23-28 + 5:39)
    #   2: canonical remainder (Genesis 1-11 circle-back etc.)
    if run_id.startswith("Genesis_12"):
        return 0
    if run_id.startswith("Matthew_"):
        return 1
    return 2


def run_sort_key(m: dict):
    order = _book_order()
    return (
        _run_tier(m.get("run_id", "")),
        order.get(m.get("book", ""), 1000),
        m.get("chapter_start") or 0,
        m.get("verse_start") or 0,
        m.get("run_id", ""),
    )


def scan() -> dict:
    index = _recheck_index()
    runs = []
    for d in sorted(RUNS_DIR.iterdir()):
        if d.name in EXCLUDE_RUNS or not d.is_dir():
            continue
        mp = d / "manifest.json"
        if not mp.exists():
            continue
        m = json.loads(mp.read_text("utf-8"))
        runs.append(m)
    runs.sort(key=run_sort_key)

    total_done = 0
    already = 0
    backlog: list[dict] = []
    stuck: list[dict] = []
    anomalies: list[dict] = []
    deferred_runs: dict[str, list[str]] = {}

    for m in runs:
        run_id = m["run_id"]
        rd = RUNS_DIR / run_id
        blocked = False
        for key, v in m.get("verses", {}).items():
            st = v.get("status")
            if st in ("reviewing", "correcting"):
                stuck.append({"run_id": run_id, "ref": f"{v['book']} {v['chapter']}:{v['verse']}", "status": st})
                blocked = True
        for key, v in m.get("verses", {}).items():
            if v.get("status") != "done":
                continue
            total_done += 1
            ref_key = f"{run_id}|{v['book']} {v['chapter']}:{v['verse']}"
            sidecar = rd / (v.get("sidecar_path") or f"{v['book']}_{v['chapter']}-{v['verse']}.json")
            if not sidecar.exists():
                anomalies.append({"run_id": run_id, "ref": f"{v['book']} {v['chapter']}:{v['verse']}",
                                  "problem": "missing analysis sidecar"})
                continue
            ca = is_ca_rechecked(rd, run_id, v) or ref_key in index
            if ca:
                already += 1
                continue
            backlog.append({
                "run_id": run_id,
                "book": v["book"], "chapter": v["chapter"], "verse": v["verse"],
                "ref": f"{v['book']} {v['chapter']}:{v['verse']}",
                "sidecar": str(sidecar),
                "review_sidecar": any(rp.exists() for rp in _review_sidecar_candidates(rd, run_id, v)),
                "run_blocked_by_stuck": blocked,
            })
    return {
        "runs": len(runs),
        "total_done": total_done,
        "already_ca_rechecked": already,
        "backlog_remaining": len(backlog),
        "stuck_mid_loop": stuck,
        "anomalies": anomalies,
        "backlog": backlog,
    }


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    result = scan()
    eligible = [b for b in result["backlog"] if not b["run_blocked_by_stuck"]]
    deferred = [b for b in result["backlog"] if b["run_blocked_by_stuck"]]
    result["next_batch"] = eligible[:limit]
    result["deferred_by_stuck_runs"] = len(deferred)
    for k in ("backlog",):
        result.pop(k)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
