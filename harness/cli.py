"""cli.py — harness command-line interface.

Usage:
    harness plan "Matthew 23:8-12"            # create a passage run
    harness book Matthew                       # create a whole-book verse-by-verse run
    harness next <run_id>                      # emit next pending verse's prompt + bundle
    harness ingest <run_id>                    # read VerseAnalysis JSON from stdin, write + validate
    harness next-review <run_id>               # emit next verse to review
    harness ingest-review <run_id>             # read reviewer JSON from stdin
    harness next-correction <run_id>           # emit next verse to correct
    harness finalize <run_id>                  # read corrected JSON from stdin, mark done
    harness mark-done <run_id>                # mark all reviewed verses as done
    harness render <run_id>                    # build SUMMARY.md/.html/.pdf
    harness status [run_id]                    # show run status (all runs if no id)
    harness cache clear [version]              # clear cache
    harness cache stats                        # cache size
    harness repair passages/                   # scan legacy passages for issues
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import orchestrator as orch
from . import cache


def _read_stdin() -> str:
    return sys.stdin.read()


def _emit(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="4K Bible Translation Harness — subagent-driven verse analysis",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Create a passage run")
    p_plan.add_argument("passage", help="e.g. 'Matthew 23:8-12' or 'Matthew 23'")

    p_book = sub.add_parser("book", help="Create a whole-book verse-by-verse run")
    p_book.add_argument("book", help="e.g. Matthew")

    p_next = sub.add_parser("next", help="Emit next pending verse's prompt + bundle")
    p_next.add_argument("run_id")

    p_ingest = sub.add_parser("ingest", help="Read VerseAnalysis JSON from stdin")
    p_ingest.add_argument("run_id")
    p_ingest.add_argument("--force", action="store_true", help="Overwrite existing")

    p_nextrev = sub.add_parser("next-review", help="Emit next verse to review")
    p_nextrev.add_argument("run_id")

    p_ingestrev = sub.add_parser("ingest-review", help="Read reviewer JSON from stdin")
    p_ingestrev.add_argument("run_id")

    p_nextcorr = sub.add_parser("next-correction", help="Emit next verse to correct")
    p_nextcorr.add_argument("run_id")

    p_finalize = sub.add_parser("finalize", help="Read corrected JSON from stdin, apply")
    p_finalize.add_argument("run_id")
    p_finalize.add_argument("--force", action="store_true")

    p_markdone = sub.add_parser("mark-done", help="Mark all reviewed verses as done")
    p_markdone.add_argument("run_id")

    p_render = sub.add_parser("render", help="Build SUMMARY.md/.html/.pdf")
    p_render.add_argument("run_id")
    p_render.add_argument("--passage-ref", default=None)
    p_render.add_argument("--no-html", action="store_true")
    p_render.add_argument("--no-pdf", action="store_true")

    p_status = sub.add_parser("status", help="Show run status")
    p_status.add_argument("run_id", nargs="?", default=None)

    p_cache = sub.add_parser("cache", help="Cache operations")
    p_cache_sub = p_cache.add_subparsers(dest="cache_cmd", required=True)
    p_cache_clear = p_cache_sub.add_parser("clear", help="Clear cache")
    p_cache_clear.add_argument("version", nargs="?", default=None)
    p_cache_sub.add_parser("stats", help="Show cache stats")

    p_repair = sub.add_parser("repair", help="Scan legacy passages for issues")
    p_repair.add_argument("dir", help="Directory to scan")
    p_repair.add_argument("--apply", action="store_true", help="Apply repairs (default: dry-run)")

    p_books = sub.add_parser("books", help="List canonical books")
    p_books.add_argument("--search", default=None)

    p_fetch = sub.add_parser("fetch", help="Fetch a verse bundle (debug)")
    p_fetch.add_argument("book")
    p_fetch.add_argument("chapter", type=int)
    p_fetch.add_argument("verse", type=int)

    args = parser.parse_args(argv)

    if args.cmd == "plan":
        run_id, path = orch.plan_passage(args.passage)
        _emit({"run_id": run_id, "manifest": str(path)})
        return 0

    if args.cmd == "book":
        run_id, path = orch.plan_book(args.book)
        _emit({"run_id": run_id, "manifest": str(path)})
        return 0

    if args.cmd == "next":
        payload = orch.next_pending_verse(args.run_id)
        if payload is None:
            _emit({"done": True, "message": "no pending verses"})
        else:
            _emit(payload)
        return 0

    if args.cmd == "ingest":
        text = _read_stdin()
        result = orch.ingest_analysis(args.run_id, text, force=args.force)
        _emit(result)
        return 0 if "error" not in result else 1

    if args.cmd == "next-review":
        payload = orch.next_review_verse(args.run_id)
        if payload is None:
            _emit({"done": True, "message": "no verses to review"})
        else:
            _emit(payload)
        return 0

    if args.cmd == "ingest-review":
        text = _read_stdin()
        result = orch.ingest_review(args.run_id, text)
        _emit(result)
        return 0 if "error" not in result else 1

    if args.cmd == "next-correction":
        payload = orch.next_correction_verse(args.run_id)
        if payload is None:
            _emit({"done": True, "message": "no verses to correct"})
        else:
            _emit(payload)
        return 0

    if args.cmd == "finalize":
        text = _read_stdin()
        result = orch.ingest_analysis(args.run_id, text, force=args.force)
        if "error" not in result:
            # Mark done
            data = json.loads(text)
            orch.finalize_verse(args.run_id, data["book"], data["chapter"], data["verse"])
        _emit(result)
        return 0 if "error" not in result else 1

    if args.cmd == "mark-done":
        _emit(orch.mark_done(args.run_id))
        return 0

    if args.cmd == "render":
        paths = orch.render_run(
            args.run_id, args.passage_ref,
            html=not args.no_html, pdf=not args.no_pdf,
        )
        _emit(paths)
        return 0

    if args.cmd == "status":
        if args.run_id:
            _emit(orch.run_status(args.run_id))
        else:
            _emit(orch.list_runs())
        return 0

    if args.cmd == "cache":
        if args.cache_cmd == "clear":
            n = cache.clear(args.version)
            _emit({"cleared": n})
        elif args.cache_cmd == "stats":
            _emit(cache.stats())
        return 0

    if args.cmd == "repair":
        from .repair import scan_directory, apply_repairs
        issues = scan_directory(args.dir)
        if args.apply:
            applied = apply_repairs(issues)
            _emit({"issues": len(issues), "applied": applied})
        else:
            _emit({"issues": len(issues), "items": [i.to_dict() for i in issues]})
        return 0

    if args.cmd == "books":
        from .retrieve import canonical_books
        books = canonical_books()
        if args.search:
            books = [b for b in books if args.search.lower() in b.lower()]
        _emit({"books": books})
        return 0

    if args.cmd == "fetch":
        from .retrieve import fetch_verse
        b = fetch_verse(args.book, args.chapter, args.verse)
        _emit(b.to_prompt_dict())
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
