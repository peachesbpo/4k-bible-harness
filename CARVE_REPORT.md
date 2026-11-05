# CARVE_REPORT.md — 4K Bible Harness public-repo carve

**Date:** 2026-11-05 · **Source (READ-ONLY, untouched):** `/home/mspea/.openclaw/workspace/Projects/bible-translation-harness`
**Destination:** `/home/mspea/repos/4k-bible-harness` (fresh `git init -b main`, no remote, nothing pushed)

---

## 1. Files copied — 122 tracked files

Allowlist copy only; nothing outside the manifest was taken. Tree summary:

| Area | Files | Notes |
|---|---|---|
| `passages/` | 81 | 10 passage dirs + embedded `test-runs/`; `passages/Archive/` EXCLUDED |
| `harness/` | 17 | full pipeline package incl. `book_index.json`; `__pycache__` excluded |
| `prompts/` | 4 | analyst, reviewer, corrector, claim-audit-spec (included per decision C) |
| `tests/` | 2 | `test_harness.py` + `__init__.py` |
| `scripts/` | 2 | `backfill_select.py` (copied from working repo's `scripts/` — its real location) + new `download_data.py` |
| root tools | 5 | `analyze_passage.py`, `fetch_verse.py`, `cross_references.py`, `quote_detector.py`, `convert_to_pdf.py` |
| root docs/config | 10 | README, PROJECT_STATUS, PROMPT, template.md, template_v2.md, template_verse.md, pyproject.toml, requirements.txt, config.json, .gitignore |
| new files | 6 | LICENSE (MIT), CARVE_REPORT.md, public README (rewrite), plus 3 later docs/data commits |

`config.json` verified secret-free before copy (paths + options only, no keys/tokens).

## 2. Files excluded & why

| Excluded | Why |
|---|---|
| `bible-db.sqlite`, `bible-api-data/`, `bible-api-esv/`, `bible-api-web/`, `cross-refs/`, `strongs-data/`, `strongs-greek-dictionary.js`, `lsj-greek-lexicon.json` | Datasets ship via `scripts/download_data.py` instead (locked decision D); `bible-db.sqlite` has no stable public URL → documented manual step |
| `passages/Archive/` | Per manifest |
| `create_gmail_draft.py`, `create_gmail_draft_callie.py`, `draft-email-to-callie-edwards.md`, `draft-email-to-mike-epps.md` | Not in allowlist; fundamentally personal |
| `etymology-source-research.md`, `table-gifts.md`, `night9-prompt-*.md`, `FIX-SPEC-*.md`, `opencode-task-*.md` | Not in allowlist; internal working notes |
| `runs/`, `logs/`, `.cache/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info`, `fix4/` | Generated state; not in allowlist |
| `scripts/` others (nightly_run.sh, nightly_prompt.md, backfill_step.py, build_*.py, adhoc_run.sh, build_web_data.py) | Not in allowlist (internal ops); `build_web_data.py`'s proven logic lives on inside `download_data.py` |

Deliberate config tweaks (logged, "trivial only"):
- `pyproject.toml`: distribution name `bible-translation-harness` → `4k-bible-harness` (public identity per decision E; package `harness` and `harness` console script unchanged).
- `.gitignore`: extended to the standard list (runs/, logs/, .pytest_cache/, data/, dataset names, *.sqlite).

## 3. Scrubs (applied to copies only; source untouched)

| File | Before | After |
|---|---|---|
| `scripts/backfill_select.py:98` | `# PRIORITY ORDER (Michael, 2026-10-02):` | `# PRIORITY ORDER (per directive, 2026-10-02):` |
| `prompts/claim-audit-spec.md:5` | `**Origin:** Drafted after the Genesis 6:2 audit (laqach/nashim overreach). Michael directed a new safeguard layer so the harness stops stretching past what the text licenses.` | `**Origin:** Drafted after the Genesis 6:2 audit exposed an overreach gap.` (F1–F4 engineering content untouched) |
| `PROJECT_STATUS.md:238` | `**Project Lead**: Michael Howard` | `**Project Lead**: the harness designer (credits in README)` |
| `PROJECT_STATUS.md:248` | `Parked-draft integrity (bible-journey-harness, Michael's standing instruction):` | `Parked-draft integrity (bible-journey-harness, standing directive):` |
| `passages/Matthew_5-3-12/Matthew_5-5.md:87` | `(Michael Howard review, 2026-06-24)` | `(human review, 2026-06-24)` |
| `passages/Matthew_5-3-12/test-runs/v2-test-01-2026-06-25/Matthew_5-5.md:117` | `corrected after Michael Howard review` | `corrected after human review` |
| `passages/Matthew_5-3-12/test-runs/v2-test-02-2026-06-25/Matthew_5-5.md:182` | `corrected after Michael Howard review` | `corrected after human review` |
| `passages/Matthew_23-13-36/Matthew_23-25.md:67` | `Michael is calling out these groups by name` | `Jesus is calling out these groups by name` (speaker-name contamination; the speaker in Matt 23 is Jesus) |
| `passages/Matthew_23-13-36/Matthew_23-26.md:40` | `Michael isn't promising that cleaning the inside…` | `Jesus isn't promising…` (same) |
| `passages/Matthew_23-13-36/Matthew_23-28.md:27` | `Michael is saying: you appear righteous TO MEN` | `Jesus is saying: …` (same) |
| `passages/Matthew_23-13-36/Matthew_23-28.md:38` | `Michael is making a precise grammatical distinction` | `Jesus is making…` (same) |
| `passages/Matthew_23-13-36/Matthew_23-28.md:72` | `Michael consistently treats hypocrisy and lawlessness as a paired corruption` | `the analysis consistently treats…` |
| `harness/hebrew_text.py:14` | `The full codebook is in /tmp/opencode/genesis-prep/01-wlc-morph-codebook.md; the tables…` | `The full codebook is the WLC/CCAT morphology codebook (see the WLC distribution docs); the tables…` (absolute temp path → generic) |
| old `README.md:324` | `Michael Howard` footer | resolved wholesale: file replaced by public README (`docs:` commit) |

"Michaelius" note: zero hits in the dest tree; lexicon-derived allowed instances were never an issue here. "Peaches" analyst credits in passage files are the sanctioned author entity (decision A) and were kept.

## 4. Final grep-clean proof

Command (dest repo root):

```
grep -rn -i -E "\b(michael|spea|mspea|peachbpo|callie|epps)\b|michaelius|/home/mspea" . --exclude-dir=.git
```

Output (entire tracked tree, after the README rewrite landed):

```
(no output — zero matches)
```

Method note: the brief's raw `spea` token matches the English words speak/speaker/speaking (~dozens of false positives in verse-analysis prose, e.g. "to speak vilely against"); word-boundary matching was used for the proof, and the raw broad pattern was also run and manually reviewed — its only non-speak* hit ever was the README footer above, removed by the public rewrite.

## 5. Pytest result

```
$ python3 -m pytest tests/ -q
100 passed in 2.19s
```

- The suite is 100 tests, not the ~62 the task brief expected (it grew in the working repo since that count was captured); README states the true number.
- Without `bible-db.sqlite` present: `97 passed, 3 failed` — the 3 failures (`test_fetch_verse_genesis_1_1`, `test_ot_verse_bundle_json`, `test_cross_refs_populated_matthew_5_5`) all require bible-db.sqlite (WLC Hebrew text/word data for OT-source analysis) — the documented manual-step dataset, not a code defect.
- With bible-db.sqlite linked locally via `python scripts/download_data.py --db <path>` (file lives in gitignored `data/`, never committed): `100 passed`.
- No fabricated passes; no test files modified.

## 6. Download-script sources (all real, verified HTTP 200; byte sizes match working-repo files)

| Dataset | URL | Format/notes |
|---|---|---|
| Greek NT `grc-srgnt` | `git clone --filter=blob:none --no-checkout --depth 1 https://github.com/wldeh/bible-api` + sparse checkout of `bibles/grc-srgnt` | same per-verse JSON layout the harness reads; upstream origin eBible.org (Solid Rock GNT) |
| ASV `en-asv` | same wldeh clone, `bibles/en-asv` | full Bible, 66 books |
| WEB (NT) | `https://raw.githubusercontent.com/TehShrike/world-english-bible/master/json/<book>.json` | assembled into wldeh per-verse layout (logic reused from working repo's `scripts/build_web_data.py`); NT-only like the working repo |
| Strong's concordance | `https://github.com/tahmmee/interlinear_bibledata/raw/master/interlinear/bible.tar.gz` | 66 book JSONs, word-level Strong's numbers |
| Strong's Greek dictionary | `https://raw.githubusercontent.com/openscriptures/strongs/master/greek/strongs-greek-dictionary.js` | 1,200,839 bytes — byte-identical to working repo file |
| LSJ lexicon | `https://raw.githubusercontent.com/perseids-project/lsj-js/master/vendor/lsj.json` | 69,668,462 bytes — byte-identical to working repo file |
| Cross-references | `https://a.openbible.info/data/cross-references.zip` | CC-BY; extracts `cross_references.txt` |
| `bible-db.sqlite` | none (manual step) | custom build (WLC + BDB + semantic categories + sqlite-vec) with no stable public URL; `--db PATH` links/copies one; harness degrades gracefully without it |

The script is stdlib-only, idempotent (skips existing, `[skip]` lines in output), writes datasets into `data/`, symlinks them at the repo-root paths `harness/retrieve.py` expects, and prints a SUMMARY table. End-to-end tested: all seven datasets fetched successfully; `fetch_verse.py Matthew 23:13 --greek` and `cross_references.py Matthew 5:5` read correctly through the links.

## 7. Commits (logical order; default global git config left as-is, repo-local identity set to the public author line)

```
e5917ed data: ignore repo-root dataset symlinks (slash-less patterns match symlinked datasets)
e4ff0ac docs: correct test-count claim to measured reality (100 tests; 97 without bible-db.sqlite)
6ebc568 data: download script
5cb5709 license: MIT
32a132c docs: public README + credits
53d8002 scrub: remove personal references
98e0cd4 carve: copy engine+docs from working repo
```

## 8. Open questions

1. **bible-db.sqlite distribution** — no public build script exists in the working repo for it; if it should ever be publicly shippable, a builder script (from OSHB/WLC + BDB public-domain sources) would close the manual step.
2. **WEB scope** — download mirrors the working repo (NT only, 27 books); OT English comes from ASV. If WEB-OT is ever wanted, extend the book list in `download_data.py`.
3. **Suite count** — brief expected ~62 tests; actual is 100 (README/report state reality; PROJECT_STATUS.md's historical "62" line was left as a dated status snapshot).
4. **Launch-day concerns** — decision F explicitly out of scope here.
