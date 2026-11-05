#!/usr/bin/env python3
"""download_data.py — fetch the six public datasets used by the 4K Bible Harness.

Datasets land in data/ and are linked into the repo root paths the harness
reads (bible-api-data/, bible-api-esv/, bible-api-web/, strongs-data/,
cross-refs/, strongs-greek-dictionary.js, lsj-greek-lexicon.json).

Sources (real, public):
  Greek NT (grc-srgnt) + ASV (en-asv)   github.com/wldeh/bible-api (sparse checkout)
  World English Bible (NT)              github.com/TehShrike/world-english-bible
  Strong's interlinear concordance      github.com/tahmmee/interlinear_bibledata
  Strong's Greek dictionary (JSON)      github.com/openscriptures/strongs
  LSJ Greek lexicon                     github.com/perseids-project/lsj-js
  Cross-references (CC-BY)              openbible.info

bible-db.sqlite (Hebrew OT text/morphology + BDB lexicon + semantic
categories, custom-built from public-domain sources) has no single stable
public URL and is NOT downloaded. Place it at the repo root (or data/) or
pass --db PATH to link it. Without it, the Greek NT pipeline works fully and
OT Hebrew analysis degrades gracefully.

Usage:
  python scripts/download_data.py              # everything not already present
  python scripts/download_data.py --only web,lsj
  python scripts/download_data.py --list
  python scripts/download_data.py --db /path/to/bible-db.sqlite

Idempotent: existing datasets are skipped. Prints a summary at the end.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

WLDEH_REPO = "https://github.com/wldeh/bible-api"
WLDEH_VERSIONS = {"greek-nt": "grc-srgnt", "asv": "en-asv"}
WEB_BASE = "https://raw.githubusercontent.com/TehShrike/world-english-bible/master/json"
STRONGS_TAR_URL = "https://github.com/tahmmee/interlinear_bibledata/raw/master/interlinear/bible.tar.gz"
STRONGS_GREEK_JS_URL = "https://raw.githubusercontent.com/openscriptures/strongs/master/greek/strongs-greek-dictionary.js"
LSJ_URL = "https://raw.githubusercontent.com/perseids-project/lsj-js/master/vendor/lsj.json"
XREF_ZIP_URL = "https://a.openbible.info/data/cross-references.zip"

WEB_NT_BOOKS = [
    "matthew", "mark", "luke", "john", "acts",
    "romans", "1corinthians", "2corinthians", "galatians", "ephesians",
    "philippians", "colossians", "1thessalonians", "2thessalonians",
    "1timothy", "2timothy", "titus", "philemon", "hebrews", "james",
    "1peter", "2peter", "1john", "2john", "3john", "jude", "revelation",
]

ROOT_LINKS = [
    "bible-api-data", "bible-api-esv", "bible-api-web", "strongs-data",
    "cross-refs", "strongs-greek-dictionary.js", "lsj-greek-lexicon.json",
]


def report(msg: str) -> None:
    print(msg, flush=True)


def fetch_to_file(url: str, dest: Path, label: str) -> None:
    report(f"  downloading {label} ...")
    report(f"    {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "4k-bible-harness/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        total = resp.getheader("Content-Length")
        total = int(total) if total else None
        done = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                pct = min(100, done * 100 // total)
                print(f"\r    {done / 1e6:7.1f} / {total / 1e6:.1f} MB ({pct}%)", end="", flush=True)
    print()
    tmp.replace(dest)


def dir_nonempty(p: Path) -> bool:
    return p.is_dir() and any(p.iterdir())


# ── Greek NT + ASV (wldeh/bible-api sparse checkout) ─────────────────────────

def fetch_wldeh(names: list[str], done: dict[str, bool]) -> bool:
    wanted = [n for n in names if not done[n]]
    if not wanted:
        return True
    if shutil.which("git") is None:
        report("  SKIP: git not found; install git or clone manually:")
        report(f"    git clone --filter=blob:none --no-checkout --depth 1 {WLDEH_REPO}")
        return False
    versions = {WLDEH_VERSIONS[n] for n in wanted}
    sub = f"bibles/{' bibles/'.join(sorted(versions))}"
    work = DATA_DIR / "_wldeh-clone"
    if not dir_nonempty(work):
        report(f"  sparse-checkout of {', '.join(sorted(versions))} from wldeh/bible-api (~500 MB transient, ~180 MB blobs)")
        report(f"    git clone {WLDEH_REPO}")
        work.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(
            ["git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1", WLDEH_REPO, str(work)],
            capture_output=True, text=True)
        if r.returncode != 0:
            report("  FAILED: " + (r.stderr or r.stdout).strip().splitlines()[-1])
            shutil.rmtree(work, ignore_errors=True)
            return False
    else:
        report("  reusing existing partial clone in data/_wldeh-clone")
    subprocess.run(["git", "-C", str(work), "sparse-checkout", "set", "--no-cone", sub],
                   capture_output=True, text=True)
    r = subprocess.run(["git", "-C", str(work), "checkout"], capture_output=True, text=True)
    if r.returncode != 0:
        report("  FAILED: " + (r.stderr or r.stdout).strip().splitlines()[-1])
        return False
    ok = True
    for n in wanted:
        ver = WLDEH_VERSIONS[n]
        src = work / "bibles" / ver
        dst = DATA_DIR / ("bible-api-data" if n == "greek-nt" else "bible-api-esv") / "bibles" / ver
        if not dir_nonempty(src):
            report(f"  FAILED: {ver} not found in checkout")
            ok = False
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        n_books = len(list((dst / "books").glob("*"))) if (dst / "books").is_dir() else 0
        report(f"  {n}: {ver} → {dst.relative_to(REPO_ROOT)} ({n_books} books)")
        done[n] = True
    shutil.rmtree(work, ignore_errors=True)
    return ok


# ── World English Bible (TehShrike JSON → per-verse wldeh layout) ────────────

def fetch_web(done: dict[str, bool]) -> bool:
    if done["web"]:
        return True
    out_root = DATA_DIR / "bible-api-web" / "bibles" / "en-web" / "books"
    out_root.mkdir(parents=True, exist_ok=True)
    total = 0
    for book in WEB_NT_BOOKS:
        url = f"{WEB_BASE}/{book}.json"
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    url, headers={"User-Agent": "4k-bible-harness/1.0"}), timeout=120) as r:
                data = json.loads(r.read())
        except Exception as e:
            report(f"  FAILED fetching {book}: {e}")
            return False
        verses: dict[tuple[int, int], list[str]] = {}
        for obj in data:
            if obj.get("type") not in ("paragraph text", "line text"):
                continue
            ch, v = obj.get("chapterNumber"), obj.get("verseNumber")
            if ch is None or v is None:
                continue
            verses.setdefault((ch, v), []).append(obj.get("value", ""))
        count = 0
        for (ch, v), parts in verses.items():
            text = " ".join("".join(parts).split())
            vdir = out_root / book / "chapters" / str(ch) / "verses"
            vdir.mkdir(parents=True, exist_ok=True)
            (vdir / f"{v}.json").write_text(
                json.dumps({"verse": str(v), "text": text}, ensure_ascii=False),
                encoding="utf-8")
            count += 1
        total += count
    report(f"  web: {total} verse files (27 NT books) → {out_root.relative_to(REPO_ROOT)}")
    done["web"] = True
    return True


# ── Strong's concordance (tahmmee/interlinear_bibledata) ─────────────────────

def fetch_strongs_concordance(done: dict[str, bool]) -> bool:
    if done["strongs-concordance"]:
        return True
    out = DATA_DIR / "strongs-data"
    tmp = DATA_DIR / "bible.tar.gz"
    try:
        fetch_to_file(STRONGS_TAR_URL, tmp, "Strong's interlinear bible.tar.gz")
        out.mkdir(parents=True, exist_ok=True)
        try:
            with tarfile.open(tmp) as tf:
                tf.extractall(out, filter="data")
        except TypeError:
            with tarfile.open(tmp) as tf:
                tf.extractall(out)
    finally:
        tmp.unlink(missing_ok=True)
    n = len(list(out.glob("*.json")))
    if n == 0:
        report("  FAILED: no book JSONs extracted")
        return False
    report(f"  strongs-concordance: {n} book JSONs → {out.relative_to(REPO_ROOT)}")
    done["strongs-concordance"] = True
    return True


# ── Strong's Greek dictionary (Open Scriptures) ──────────────────────────────

def fetch_strongs_greek_dict(done: dict[str, bool]) -> bool:
    if done["strongs-greek-dict"]:
        return True
    dest = DATA_DIR / "strongs-greek-dictionary.js"
    fetch_to_file(STRONGS_GREEK_JS_URL, dest, "Strong's Greek dictionary")
    report(f"  strongs-greek-dict: → {dest.relative_to(REPO_ROOT)}")
    done["strongs-greek-dict"] = True
    return True


# ── LSJ lexicon (perseids-project/lsj-js) ────────────────────────────────────

def fetch_lsj(done: dict[str, bool]) -> bool:
    if done["lsj"]:
        return True
    dest = DATA_DIR / "lsj-greek-lexicon.json"
    fetch_to_file(LSJ_URL, dest, "LSJ Greek lexicon (~70 MB)")
    report(f"  lsj: → {dest.relative_to(REPO_ROOT)}")
    done["lsj"] = True
    return True


# ── Cross-references (openbible.info, CC-BY) ─────────────────────────────────

def fetch_cross_refs(done: dict[str, bool]) -> bool:
    if done["cross-refs"]:
        return True
    out = DATA_DIR / "cross-refs"
    out.mkdir(parents=True, exist_ok=True)
    tmp = DATA_DIR / "cross-references.zip"
    try:
        fetch_to_file(XREF_ZIP_URL, tmp, "cross-references.zip")
        with zipfile.ZipFile(tmp) as zf:
            zf.extract("cross_references.txt", out)
    finally:
        tmp.unlink(missing_ok=True)
    if not (out / "cross_references.txt").exists():
        report("  FAILED: cross_references.txt not in zip")
        return False
    report(f"  cross-refs: → {(out / 'cross_references.txt').relative_to(REPO_ROOT)}")
    done["cross-refs"] = True
    return True


# ── bible-db.sqlite (manual step) ────────────────────────────────────────────

def check_bible_db(db_arg: str | None) -> str:
    root = REPO_ROOT / "bible-db.sqlite"
    data = DATA_DIR / "bible-db.sqlite"
    if root.exists() or data.exists():
        if data.exists() and not root.exists():
            make_link(root, data)
            report("  bible-db.sqlite: found in data/, linked at repo root")
        else:
            report("  bible-db.sqlite: present")
        return "ok"
    if db_arg:
        src = Path(db_arg).expanduser().resolve()
        if not src.is_file():
            report(f"  bible-db.sqlite: --db path not found: {src}")
            return "manual"
        shutil.copy2(src, data)
        make_link(root, data)
        report(f"  bible-db.sqlite: copied from {src}, linked at repo root")
        return "ok"
    report("  bible-db.sqlite: MISSING — manual step (see README).")
    report("    Custom-built from public-domain sources (WLC Hebrew + BDB + semantic")
    report("    categories); no single stable public URL. Place it at the repo root or")
    report("    data/, or re-run with --db /path/to/bible-db.sqlite. The Greek NT")
    report("    pipeline works without it; OT Hebrew analysis degrades gracefully.")
    return "manual"


# ── root links + summary ─────────────────────────────────────────────────────

def make_link(root_path: Path, target: Path) -> bool:
    if root_path.exists() or root_path.is_symlink():
        return True
    try:
        root_path.symlink_to(Path("data") / target.relative_to(DATA_DIR))
        return True
    except OSError as e:
        report(f"  NOTE: could not symlink {root_path.name} → data/: {e}")
        report("        copy or move it there manually; the harness reads repo-root paths.")
        return False


def make_root_links() -> None:
    for name in ROOT_LINKS:
        target = DATA_DIR / name
        if dir_nonempty(target) or (target.is_file() and target.stat().st_size > 0):
            make_link(REPO_ROOT / name, target)


DATASETS = [
    ("greek-nt", "Greek NT (grc-srgnt, 27 books)", ["greek-nt"]),
    ("asv", "American Standard Version 1901 (en-asv, full Bible)", ["asv"]),
    ("web", "World English Bible (NT, en-web)", ["web"]),
    ("strongs-concordance", "Strong's interlinear concordance (66 books)", ["strongs-concordance"]),
    ("strongs-greek-dict", "Strong's Greek dictionary (Open Scriptures)", ["strongs-greek-dict"]),
    ("lsj", "LSJ Greek lexicon (~70 MB)", ["lsj"]),
    ("cross-refs", "Cross-references (openbible.info, CC-BY)", ["cross-refs"]),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch the 4K Bible Harness datasets into data/.")
    ap.add_argument("--only", default="", help="comma-separated subset: " + ",".join(n for n, _, _ in DATASETS))
    ap.add_argument("--list", action="store_true", help="list datasets and exit")
    ap.add_argument("--db", default=None, metavar="PATH", help="link/copy an existing bible-db.sqlite")
    args = ap.parse_args()

    if args.list:
        for name, desc, _ in DATASETS:
            print(f"{name:22s} {desc}")
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    selected = {s.strip() for s in args.only.split(",") if s.strip()}
    unknown = selected - {n for n, _, _ in DATASETS}
    if unknown:
        ap.error(f"unknown dataset(s): {', '.join(sorted(unknown))}")

    done = {}
    for name, _, wldeh_keys in DATASETS:
        target = DATA_DIR / ("bible-api-data/bibles/grc-srgnt" if name == "greek-nt"
                             else "bible-api-esv/bibles/en-asv" if name == "asv"
                             else "bible-api-web/bibles/en-web" if name == "web"
                             else "strongs-data" if name == "strongs-concordance"
                             else "strongs-greek-dictionary.js" if name == "strongs-greek-dict"
                             else "lsj-greek-lexicon.json" if name == "lsj"
                             else "cross-refs/cross_references.txt")
        already = (dir_nonempty(target) if not target.suffix
                   else target.is_file() and target.stat().st_size > 0)
        for k in wldeh_keys:
            done[k] = already
        if already:
            report(f"[skip] {name} (already present)")
        elif selected and name not in selected:
            report(f"[skip] {name} (not selected)")

    results = {}
    for name, desc, keys in DATASETS:
        if done[keys[0]] or (selected and name not in selected):
            results[name] = "skipped" if done[keys[0]] else "not selected"
            continue
        report(f"[fetch] {name} — {desc}")
        if name in ("greek-nt", "asv"):
            ok = fetch_wldeh(keys, done)
        else:
            ok = {"web": fetch_web,
                  "strongs-concordance": fetch_strongs_concordance,
                  "strongs-greek-dict": fetch_strongs_greek_dict,
                  "lsj": fetch_lsj,
                  "cross-refs": fetch_cross_refs}[name](done)
        results[name] = "ok" if ok else "FAILED"

    db_status = check_bible_db(args.db)
    make_root_links()

    report("")
    report("=" * 62)
    report("SUMMARY")
    report("=" * 62)
    for name, _, _ in DATASETS:
        report(f"  {name:22s} {results[name]}")
    report(f"  {'bible-db.sqlite':22s} {db_status}")
    n_ok = sum(1 for v in results.values() if v == "ok")
    report("")
    report(f"{n_ok} dataset(s) fetched this run; existing ones skipped (idempotent).")
    report("Datasets live in data/ and are linked at the repo-root paths the harness reads.")
    if db_status == "manual":
        report("bible-db.sqlite still needs the manual step described above.")
    return 0 if all(v in ("ok", "skipped", "not selected") for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
