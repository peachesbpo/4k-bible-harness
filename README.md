# 4K Bible Translation Harness

## Purpose
Recover the "director's cut" of Scripture by analyzing original language (Greek/Hebrew) nuances and producing expanded English translations that preserve meaning lost in standard translations. Supports both NT (Greek → WEB) and OT (Hebrew/WLC → ASV) passages.

## Data Sources (All Local — No API Calls Required)

All datasets are cloned/downloaded and stored locally in the project folder:

| Source | Path | Description | Size |
|--------|------|-------------|------|
| **Greek NT** | `bible-api-data/bibles/grc-srgnt/` | Solid Rock Greek New Testament, Scholar's Edition (grc-srgnt) — 27 books, 8,223 verse JSON files | 37 MB |
| **WEB English (NT)** | `bible-api-web/bibles/en-web/` | World English Bible (en-web, public domain) — NT only, 7,958 verse JSON files | ~8 MB |
| **ASV English (Full Bible)** | `bible-api-esv/bibles/en-asv/` | American Standard Version 1901 (en-asv, public domain) — full Bible, 66 books, 32,293 verse JSON files | 140 MB |
| **Strong's Concordance** | `strongs-data/` | Interlinear Bible with word-level Strong's numbers — 66 book JSON files, every word tagged | 39 MB |
| **Cross-References** | `cross-refs/cross_references.txt` | openbible.info cross-reference dataset — ~340k verse-to-verse links with vote counts (CC-BY) | 2 MB |
| **Bible DB (WLC + BDB)** | `bible-db.sqlite` | Westminster Leningrad Codex (Hebrew OT source text + morphology), BDB-class Hebrew lexicon (8,674 H#### entries), Strong's Greek dict (5,523 G#### entries), semantic categories (18 domains) | 132 MB |
| **LSJ Greek Lexicon** | `lsj-greek-lexicon.json` | Liddell-Scott-Jones classical Greek-English lexicon — 119,553 entries | 70 MB |

**Origin repos (for reference, already downloaded):**
- Greek NT + ESV: <https://github.com/wldeh/bible-api> (sparse-checked, .git removed)
- Strong's: <https://github.com/tahmmee/interlinear_bibledata> (bible.tar.gz extracted)
- Cross-References: <https://www.openbible.info/labs/cross-references/> (downloaded zip, extracted to txt)

### Local File Structure

```
bible-translation-harness/
├── bible-api-data/                    # Greek NT (local)
│   └── bibles/grc-srgnt/
│       ├── grc-srgnt.json             # Version metadata
│       └── books/
│           ├── ματθαιον/              # Matthew (Greek Unicode names)
│           │   └── chapters/23/verses/13.json
│           └── ... (27 books total)
├── bible-api-web/                     # WEB English (local)
│   └── bibles/en-asv/
│       ├── en-asv.json                # Version metadata
│       └── books/
│           ├── matthew/               # Matthew (Latin names)
│           │   └── chapters/23/verses/13.json
│           └── ... (66 books total)
├── strongs-data/                      # Strong's concordance (local)
│   ├── matthew.json                   # All Matthew verses with Strong's numbers
│   ├── mark.json
│   └── ... (66 book files total)
├── cross-refs/                        # Cross-reference data (local)
│   ├── cross_references.txt           # ~340k verse-to-verse links (openbible.info)
│   └── cross-references.zip           # Original download (archive)
```

### Reading Local Verse Files

```python
import json

# Greek NT verse
with open("bible-api-data/bibles/grc-srgnt/books/ματθαιον/chapters/23/verses/13.json") as f:
    greek = json.load(f)
    print(greek["text"])  # Greek verse text

# WEB English verse
with open("bible-api-web/bibles/en-web/books/matthew/chapters/23/verses/13.json") as f:
    esv = json.load(f)
    print(esv["text"])    # English ESV verse text

# Strong's concordance (all verses for a book in one file)
with open("strongs-data/matthew.json") as f:
    data = json.load(f)   # List of verse objects, each with "id" and "verse" (word array)
    # ID format: BCCCVVVV (book 3 digits, chapter 3 digits, verse 3 digits)
    # Matthew 23:13 = ID "40023013"
    for item in data:
        if item["id"] == "40023013":
            for word in item["verse"]:
                print(f"{word['word']} | {word['number']} | {word['text']}")
```

### Strong's Concordance ID Format

The Strong's data uses a `BBCCCVVV` ID scheme (8 digits):
- **BB** = Book number (2 digits): Matthew = 40, Mark = 41, Luke = 42, John = 43, etc.
- **CCC** = Chapter number (3 digits): 023 = chapter 23
- **VVV** = Verse number (3 digits): 013 = verse 13

Example: Matthew 23:13 = `40023013`

Each verse entry contains a `verse` array of word objects:
```json
{
  "i": 10,
  "text": "ye shut up",
  "word": "κλείετε",
  "number": "g2808"
}
```

## Output Structure: Granular Per-Verse + Summary

Each passage analysis produces a **directory** containing:

- **SUMMARY.md / .html / .pdf** — Results-first overview with:
  1. **📊 Diff Analysis** — What the standard translation loses (table + flattened concepts)
  2. **✨ Expanded Translation (4K)** — Clean, casual-readable English with parenthetical nuance notes
  3. **📖 Baseline Translation** — Standard ESV for reference
  4. **📂 Individual Verse Analyses** — Links to per-verse files
  5. **💡 Theological Insights** — Deeper "why it matters" findings
  6. **📝 Notes for Further Study** — Open questions and research directions

- **{Book}_{Chapter}:{Verse}.md** — One complete self-contained file per verse containing:
  - 📖 Common English Translation (ESV for this verse)
  - ✨ 4K Expanded Translation (clean English with parenthetical nuance notes)
  - 📊 Diff Analysis (what this verse's standard translation loses)
  - 💡 Theological Insights Recovered (verse-specific insights)
  - 🔍 Detailed Linguistic Analysis (Greek text, word table, grammar, context, cross-references)

### Directory Layout
```
passages/
├── Matthew_23-8-12/
│   ├── SUMMARY.md              # Common English + 4K Translation + Diffs
│   ├── SUMMARY.html            # Styled HTML (dark theme)
│   ├── SUMMARY.pdf             # Print/distribution ready
│   ├── Matthew_23-8.md         # Individual verse analysis
│   ├── Matthew_23-9.md
│   ├── Matthew_23-10.md
│   ├── Matthew_23-11.md
│   └── Matthew_23-12.md
```

### 4K Translation Style Guide
- **English only** in the expanded translation — no Greek, no Strong's numbers, no parsing codes
- **Parenthetical notes** explain the nuance recovered: "(literally means 'from the same womb' — blood-relations, kinsmen)"
- **Readable for casuals** — a person with no linguistics background should flow through it naturally
- **Tone/nuance in parentheses**, not in the main text — the main text reads as smooth English

### Summary Formats
The SUMMARY file is generated in three formats:
- **Markdown (.md)** — Source format, editable, links to verse files
- **HTML (.html)** — Styled, dark theme, responsive, web-ready
- **PDF (.pdf)** — Print/distribution ready (via WeasyPrint)

## Workflow (4-Phase Process)

### Phase 1: Source Retrieval (Main Agent)
Read verified source text from local data sources BEFORE spawning analysis subagents.
```bash
# Fetch Greek + ESV for a passage (reads from local files)
python3 fetch_verse.py Matthew 23:13-18
```
- Greek text from `bible-api-data/bibles/grc-srgnt/` (local)
- WEB from `bible-api-web/bibles/en-web/` (local)
- Strong's numbers from `strongs-data/` (local)
- Optional: KJV via `--kjv` flag
- **No internet connection required** — all data is local

### Phase 2: Analysis (Subagent)
Receives verified source text + ESV + Strong's numbers, produces per-verse analysis:
- Word-by-word analysis with Strong's numbers, parsing, lexical ranges
- Expanded 4K translation (clean English with parenthetical nuance notes)
- Diff analysis: what the ESV loses vs. the Greek original
- Theological insights recovered from original language

### Phase 3: Review (Review Subagent)
Validates each verse file for accuracy:
- **Greek text verification**: Compare against local source files
- **Diff validation**: Is each diff actually a diff? Does the ESV really lose this?
- **Strong's verification**: Cross-check Strong's numbers against local concordance
- **Flag hallucinations**: Greek text, fabricated diffs, overstated claims
- Output: List of corrections needed per verse

### Phase 4: Correction (Main Agent)
Applies review corrections to verse files.
- Remove false diffs (where ESV already captures the nuance)
- Fix Greek text errors
- Mark etymological commentary as commentary, not as translation loss
- Final output: Clean, verified verse files

### Strong's Reference
Strong's numbers are sourced locally from `strongs-data/` (interlinear_bibledata by tahmmee).
Each word in the concordance has a `number` field (e.g., `g932` for βasilεia = "kingdom").
No web lookups required.

## Project Structure
```
bible-translation-harness/
├── README.md                   # This file
├── PROMPT.md                   # Agent operating contract for the harness CLI
├── PROJECT_STATUS.md           # Project status and roadmap
├── pyproject.toml              # Packaging (install with `pip install -e .`)
├── requirements.txt            # Runtime deps (rich, jinja2; optional: markdown, weasyprint)
├── template.md                 # Summary template (results-first format)
├── template_verse.md           # Individual verse file template
├── template_v2.md              # V2 template (results-first, granular)
├── fetch_verse.py             # Fetch Greek/ESV/Strong's text from local data (legacy CLI)
├── cross_references.py         # Cross-reference lookup + Hebrew source analysis
├── analyze_passage.py          # Legacy analysis script (stub — use `harness` CLI instead)
├── convert_to_pdf.py          # Standalone MD→HTML→PDF converter
├── config.json                 # Data source paths, output options, format
├── harness/                    # Hardened harness package (v0.2)
│   ├── __init__.py
│   ├── book_index.json         # Auto-generated NT book mappings (27 books)
│   ├── cache.py                # On-disk JSON verse cache (mtime-keyed)
│   ├── greek_text.py           # SBLGNT apparatus stripper
│   ├── text_purity.py          # Greek-script verifier + bleed repair
│   ├── retrieve.py             # VerseBundle dataclass + retrieval layer
│   ├── schema.py               # VerseAnalysis dataclass (structured intermediate)
│   ├── state.py               # Run/verse manifest (per-verse checkpointing)
│   ├── writer.py               # VerseAnalysis → markdown + JSON sidecar
│   ├── summary.py              # Aggregate per-verse → SUMMARY.md/.html/.pdf
│   ├── prompts.py              # Subagent prompt builders
│   ├── validators.py           # Quality gates (greek purity, strongs, diff, style)
│   ├── repair.py               # Legacy passage scanner + bleed repair
│   ├── orchestrator.py        # Plan/next/ingest/review helpers
│   ├── cli.py                  # `harness` command entry point
│   └── theme.py               # CSS themes for HTML/PDF
├── prompts/                    # Subagent prompts
│   ├── analyst.md             # Analyst subagent (produces VerseAnalysis)
│   ├── reviewer.md            # Reviewer subagent (validates + flags corrections)
│   └── corrector.md           # Corrector subagent (applies corrections)
├── scripts/
│   └── build_book_index.py     # Regenerate harness/book_index.json from data dirs
├── tests/
│   └── test_harness.py         # 22 tests (purity, repair, retrieval, schema, validators, state)
├── runs/                       # One dir per run (manifest.json + per-verse .md/.json + SUMMARY.*)
├── bible-api-data/             # Greek NT (local, grc-srgnt)
├── bible-api-web/              # WEB English (local, en-asv)
├── strongs-data/               # Strong's concordance (local)
├── cross-refs/                 # Cross-reference data (local, openbible.info)
├── passages/                   # Legacy passage analyses (now bleed-repaired)
└── .cache/                    # Parsed verse cache (auto-generated, mtime-keyed)
```

## Usage

### Hardened Harness CLI (v0.2 — subagent-driven)

The `harness` command drives verse-by-verse analysis with **opencode Task subagents**
(fresh context per verse → no kv-cache bloat). The CLI is pure Python; the agent
orchestrates. See `PROMPT.md` for the full agent contract.

```bash
# Install (editable)
pip install -e .

# Plan a passage run
harness plan "Matthew 23:8-12"

# Per-verse loop (agent-driven): get next pending verse, spawn subagent, ingest
harness next Matthew_23-8-12            # → {book, chapter, verse, bundle, prompt}
#   ... spawn a Task subagent with the prompt, get JSON back ...
echo "$JSON" | harness ingest Matthew_23-8-12

# Review + correction loops
harness next-review Matthew_23-8-12
echo "$REVIEW_JSON" | harness ingest-review Matthew_23-8-12
harness next-correction Matthew_23-8-12
echo "$CORRECTED_JSON" | harness finalize Matthew_23-8-12

# Mark reviewed verses done, render SUMMARY.md/.html/.pdf
harness mark-done Matthew_23-8-12
harness render Matthew_23-8-12

# Whole-book iterative mode (verse-by-verse, per-verse checkpoint)
harness book Matthew
#   ... then same next/ingest loop ...

# Status / repairs / cache
harness status                           # list all runs
harness status Matthew_23-8-12          # one run
harness repair passages/ [--apply]       # scan/fix Greek-text bleed in legacy files
harness cache stats
harness cache clear [greek|esv|all]
```

### Legacy CLI (still works)

```bash
# Fetch verse text from local data sources
python3 fetch_verse.py Matthew 23:13           # Greek + ESV
python3 fetch_verse.py Matthew 23:13-18        # Range
python3 fetch_verse.py Matthew 23:13 --greek   # Greek only
python3 fetch_verse.py Matthew 23:13 --esv     # ESV only
python3 fetch_verse.py Matthew 23:13 --kjv     # KJV also
python3 fetch_verse.py Matthew 23:13 --etymology  # Strong's + LSJ + dictionaries
python3 fetch_verse.py Matthew chapter 23      # Full chapter

# Look up cross-references for a verse
python3 cross_references.py Matthew 5:5                  # Markdown output
python3 cross_references.py Matthew 5:5 --min-votes 20   # Only strong matches
python3 cross_references.py Matthew 5:5 --json           # Raw JSON
python3 cross_references.py Psalm 37:11 --no-hebrew      # Skip Hebrew analysis

# Convert existing markdown to HTML + PDF
python3 convert_to_pdf.py passages/Matthew_23-8-12.md
```

### Cross-Reference Analysis

The harness includes cross-reference data from [openbible.info](https://www.openbible.info/labs/cross-references/)
(~340k verse-to-verse links, CC-BY licensed). For any Bible verse, the `cross_references.py`
module:

1. **Finds all cross-referenced verses** — sorted by community vote count (relevance)
2. **Enriches OT sources with Hebrew word analysis** — Strong's numbers, definitions, derivation chains, semantic categories from bible-db.sqlite
3. **Separates OT sources from NT echoes** — Psalm/Isaiah/etc. sources get full Hebrew analysis; NT verses are listed for context
4. **Formats as markdown** — ready to drop into a verse analysis file

This is especially valuable for NT verses that quote or echo OT passages (e.g., Matthew 5:3-12
quotes Psalm 100/37 — the Hebrew source words carry nuance that Jesus's Greek may or may not
transfer, and the ESV may or may not capture from either).

## Completed Passages
- Matthew 5:3-12 (Beatitudes) — 11 gaps, 7 insights
- Matthew 22:41-45 — 11 gaps, 8 insights
- Matthew 23:1-7 (Seven Woes, critique) — 14 gaps, 7 insights
- Matthew 23:8-12 (Seven Woes, commands) — 13 gaps, 9 insights
- Matthew 23:13 (Seven Woes: shutting the kingdom) — Strong's verified, verse numbering corrected
- Matthew 23:14 (Seven Woes: devouring widows' houses) — Strong's verified, verse numbering corrected
- Matthew 23:23-24 (Seven Woes: culminating indictment + camel proverb) — 12 gaps, 7 insights, v3 granular format, LSJ proverb verified
- Matthew 23:27-28 (Seven Woes: whited sepulchres — image and application) — 13 gaps, 10 insights, v3 granular format, LSJ cites for kekoniaμenoi/oraioi/hypokrisis
- Matthew 23:29-32 (Seven Woes: building tombs and bearing measure) — 16 gaps, 10 insights, v3 granular format

## Project Lead
Michael Howard  
**Analyst**: Peaches (🍑)
