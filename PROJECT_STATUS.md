# 4K Bible Translation Harness - Project Status

**Created**: 2026-06-20  
**Last Updated**: 2026-08-06  
**Status**: ✅ **HARDENED (v0.4)** — OT (Hebrew/WLC) support added, two-layer hermeneutic for OT, language-aware validators/prompts/writer, 62 tests passing  
**Test Passage**: Matthew 5:3-12 (The Beatitudes), Genesis 1:1 (smoke test)

---

## 🎯 What We Built

A structured workflow and toolset for recovering original language nuances from biblical texts and producing "4K" expanded translations that show what gets lost in standard English versions. All data sources are local — no internet required.

---

## 📦 Local Data Sources

All six datasets are stored locally in the project folder:

| Source | Path | Description | Size |
|--------|------|-------------|------|
| **Greek NT** | `bible-api-data/bibles/grc-srgnt/` | Solid Rock Greek NT, Scholar's Edition — 27 books, 8,223 verse files | 37 MB |
| **WEB English** | `bible-api-web/bibles/en-web/` | World English Bible (public domain) — 66 books, 7,958 verse (NT only) files | ~8 MB |
| **Strong's** | `strongs-data/` | Interlinear Bible with word-level Strong's numbers — 66 book files | 39 MB |
| **Strong's Greek Dict** | `strongs-greek-dictionary.js` | Strong's Greek dictionary — 5,523 entries with lemma, strongs_def, kjv_def, derivation | 1.2 MB |
| **LSJ Lexicon** ⭐ | `lsj-greek-lexicon.json` | Liddell-Scott-Jones classical Greek-English lexicon — 119,553 entries, independent of Bible translation | 70 MB |
| **Bible DB** | `bible-db.sqlite` | Semantic categories (18 domains), morphology, Hebrew+Greek dictionaries — 14,197 Strong's entries | 132 MB |

**Origin repos (already downloaded, no internet needed):**
- Greek NT + ESV: `wldeh/bible-api` (sparse-checked, .git removed)
- Strong's: `tahmmee/interlinear_bibledata` (bible.tar.gz extracted)

---

## 📁 Project Structure

```
bible-translation-harness/
├── README.md                   # Project overview + data source docs
├── PROJECT_STATUS.md           # This file
├── template.md                 # Results-first output template (v2)
├── fetch_verse.py              # Fetch Greek/ESV/Strong's from local data
├── analyze_passage.py          # Main analysis script (MD + HTML + PDF output)
├── convert_to_pdf.py           # Standalone MD→HTML→PDF converter
├── config.json                 # Configuration (local paths, output options, format)
├── bible-api-data/             # Greek NT (local, grc-srgnt)
├── bible-api-web/              # WEB English (local, en-asv)
├── strongs-data/               # Strong's concordance (local)
└── passages/                   # Individual passage analyses
```

---

## ✅ Output Format: Granular Per-Verse + Summary (v3 — June 23)

Each passage produces a **directory** with a SUMMARY file and individual verse files.

### SUMMARY.md / .html / .pdf — Results-first overview:
1. **📊 Diff Analysis** — What the standard translation loses (table + flattened concepts)
2. **✨ Expanded Translation (4K)** — Clean, casual-readable English with parenthetical nuance notes
3. **📖 Baseline Translation** — Standard ESV for reference
4. **📂 Individual Verse Analyses** — Links to per-verse files
5. **💡 Theological Insights** — Deeper "why it matters" findings
6. **📝 Notes for Further Study** — Open questions and research directions

### Individual Verse Files — One complete self-contained packet per verse:
- 📖 Common English Translation (ESV for this verse)
- ✨ 4K Expanded Translation (clean English with parenthetical nuance notes)
- 📊 Diff Analysis (what this verse's standard translation loses)
- 💡 Theological Insights Recovered (verse-specific insights)
- 🔍 Detailed Linguistic Analysis (Greek text, Strong's concordance table, grammar, cross-references)

### 4K Translation Style Guide
- **English only** in the expanded translation — no Greek, no Strong's numbers, no parsing codes
- **Parenthetical notes** explain the nuance recovered in natural English
- **Readable for casuals** — no linguistics background required
- **Three formats for SUMMARY**: Markdown + HTML (dark theme) + PDF (WeasyPrint)
- **Verse files**: Markdown (part of repo structure, each self-contained)

---

## ✅ Pilot Results

| Passage | Nuance Gaps | Insights | Status |
|---------|-------------|----------|--------|
| Matthew 5:3-12 (Beatitudes) | 11 | 7 | ✅ Complete |
| Matthew 22:41-45 | 11 | 8 | ✅ Complete |
| Matthew 23:1-7 (Seven Woes: Critique) | 14 | 7 | ✅ Complete |
| Matthew 23:8-12 (Seven Woes: Commands) | 13 | 9 | ✅ Complete (v3 granular format) |
| Matthew 23:13 (Seven Woes: Shutting the Kingdom) | — | — | ✅ Complete (Strong's verified, verse numbering corrected) |
| Matthew 23:14 (Seven Woes: Devouring Widows' Houses) | — | — | ✅ Complete (Strong's verified, verse numbering corrected) |
| Matthew 23:23-24 (Seven Woes: Culminating Indictment + Camel Proverb) | 12 | 7 | ✅ Complete (v3 granular format, LSJ proverb verified) |
| Matthew 23:25 (Seven Woes: Cup and Platter — Outside/Inside) | 10 | 8 | ✅ Complete (v3 granular format, LSJ cites verse for γέmw ἐξ and paρoψis) |
| Matthew 23:26 (Seven Woes: The Reversal — Inside First) | 10 | 8 | ✅ Complete (v3 granular format, purpose clause + middle voice analysis) |
| Matthew 23:27-28 (Seven Woes: Whited Sepulchres) | 13 | 10 | ✅ Complete (v3 granular format, image-and-application pair, men...de concessive structure, LSJ cites for kekoniaμenoi/oraioi/hypokrisis) |

**Total**: 94 nuance gaps identified, 64 theological insights recovered across 8 passages + 2 corrected verse files with verified Strong's numbers.

---

## 🛠️ Current Capabilities

### ✅ Working
- Passage parsing (book, chapter, verse ranges)
- Baseline translation input (WEB/KJV configurable)
- **Local Greek NT** text from `bible-api-data/` (grc-srgnt)
- **Local WEB English** text from `bible-api-web/` (en-asv)
- **Local Strong's concordance** from `strongs-data/` (word-level Strong's numbers)
- **Strong's Greek dictionary** lookups (lemma, definitions, derivation)
- **LSJ classical Greek dictionary** lookups — breaks the Bible-translation feedback loop by providing original Greek meanings from classical literature (1843, revised 1940)
- **Bible-db semantic categories** — 18-domain categorization (e.g., emotion_mind>attitude_character)
- **`--etymology` flag** on fetch_verse.py — enriches Strong's data with all dictionary lookups in one call
- Key word analysis with verified Strong's numbers
- Grammatical observations (tense, voice, mood, syntax)
- Expanded translation generation (clean English, parenthetical notes)
- Diff analysis showing lost nuances (results-first table)
- Theological insights recovery
- **Multi-format output**: Markdown + HTML (dark theme) + PDF (WeasyPrint)
- **Results-first format**: Diffs lead, supporting detail follows
- **Casual-readable 4K translations**: English only, parenthetical nuance notes
- **Verse numbering discrepancy handling**: bible-api Greek vs ESV/KJV (Matthew 23:13-14 swapped)

### 🚧 Needs Development
- ~~**Hebrew Bible Support**: Currently Greek-only; needs Hebrew/Aramaic for OT~~ — **DONE (v0.4)**
- **Automated Cross-References**: Currently manual
- **Manuscript Variants**: Note differences between TR, NA28, UBS5
- **Batch Processing**: Analyze multiple passages in one run
- **Search/Index**: Search across all analyzed passages
- **Retroactive v3 conversion**: Older passages (5:3-12, 22:41-45, 23:1-7) need Strong's numbers added
- **Aramaic-range detection**: Daniel 2:4b–7:28, Ezra 4:8–6:18, 7:12–26, Jer 10:11 are Aramaic, not Hebrew. Deferred until those books are analyzed.


## 🎯 Next Steps (Priority Order)

### Phase 1: Enhancement
- [x] ~~Add Hebrew/Aramaic support for OT passages~~ — **DONE (v0.4, Hebrew only; Aramaic deferred)**
- [x] ~~Retroactively convert older passages to v3 format with Strong's numbers + etymology data~~
- [ ] Re-run Beatitudes via the hardened `harness` CLI with subagents
- [x] ~~Implement automated cross-reference fetching from local data~~ (already in `cross_references.py`)
- [ ] Add manuscript variant comparison
- [ ] Begin Genesis analysis (Genesis 1:1-5 pilot next, then 1:26-31, 3:1-7, 12:1-3, 22:1-19)

### Phase 2: Automation — ✅ DONE (v0.2)
- [x] ~~Batch processing for books/chapters~~ — `harness book Matthew --iterative`
- [x] ~~Search/index across all analyses~~ — structured `.json` sidecars per verse
- [ ] Web interface option (deferred — rich CLI shipped first per project decision)

---

## 🔧 v0.4 OT (Hebrew) Support (2026-08-06)

**What changed:**

- **OT book index** — `scripts/build_book_index.py` extended to scan 39 OT books (Genesis=01 … Malachi=39). `book_index.json` now carries `ot_books` alongside `nt_books`, with `testament`, `db_book_number`, and `asv_dir` fields per entry. All 39 OT Strong's prefixes verified.
- **Hebrew text module** (`harness/hebrew_text.py`) — `verify_hebrew()` purity checker (Hebrew Unicode block U+0590–U+05FF + presentation forms), mirrors `verify_greek()`. `decode_morph()` translates WLC/CCAT morphology codes to readable English (e.g., `HR/Ncfsa` → "Preposition / Noun common feminine singular absolute"). Full codebook verified against actual WLC data distribution.
- **Language-aware retrieval** (`harness/retrieve.py`) — `HebrewWord` dataclass (surface, translit, lemma, morph_raw, morph_readable, strongs, strongs_def, derivation, categories). `VerseBundle` extended with `hebrew_text`, `asv_text`, `hebrew_pure`, `hebrew_words`, `original_language`, `testament`. `fetch_verse()` branches on testament: OT queries `bible-db.sqlite` `words` table (WLC) + joins `word_strong` + enriches from `strongs` table (BDB). OT book aliases added to `resolve_book()`.
- **Templated prompts** — `prompts/{analyst,reviewer,corrector}.md` refactored to single templated files with `{{#if NT}}...{{/if}}` / `{{#if OT}}...{{/if}}` conditional blocks. `harness/prompts.py` resolves conditionals based on the bundle's testament. NT branch keeps the four-layer hermeneutic + Aramaic-gap rule; OT branch uses a two-layer Hebrew→English hermeneutic (no Aramaic gap, no Jesus-attribution check).
- **Testament-aware schema** (`harness/schema.py`) — `VerseAnalysis` fields made optional with defaults so `from_dict()` works for both NT and OT analyses. `KeyWord` gained `morphology` and `stem` fields (OT). `DiffEntry` gained `asv_rendering` field (OT).
- **Language-aware validators** (`harness/validators.py`) — Hebrew purity for OT, Greek for NT. Strong's format H#### vs G####. ASV-phrase-in-diff for OT, WEB for NT. Jesus-attribution and Aramaic-gap checks restricted to NT `spoken_jesus_material: true` (never fire for OT).
- **Testament-aware writer + summary** (`harness/writer.py`, `harness/summary.py`) — render "Hebrew (WLC)" and "ASV" for OT verses; "Greek (SBLGNT)" and "WEB" for NT. Key word table shows Morphology+Stem columns for OT, Parsing for NT.
- **Orchestrator fix** (`harness/orchestrator.py`) — `ingest_analysis()` builds the strongs-numbers set from `hebrew_words` (H####) for OT, from `strongs` array (G####) for NT. Purity field in manifest is `hebrew_pure` for OT, `greek_pure` for NT.
- **62 tests** passing (38 existing NT + 24 new Hebrew/OT: purity, morph decode, retrieval, aliases, chapter counts, bundle JSON, writer, summary, schema roundtrip, validators).
- **Smoke test**: Genesis 1:1 ran end-to-end (plan → next → ingest → render). SUMMARY.md/.html/.pdf produced with Hebrew text, WLC label, ASV baseline, decoded morphology, H#### Strong's, two-layer hermeneutic. No Greek/WEB/Aramaic-gap content in the OT output.

**What's deferred:**
- Aramaic-range detection (Daniel/Ezra/Jer) — Genesis has no Aramaic.
- WEB OT acquisition — en-asv (ASV 1901) is the OT English baseline for now.
- HALOT-class modern lexicon — BDB (in `bible-db.sqlite`) is adequate.

---

## 🔧 v0.3 Hermeneutic Hardening (2026-07-04)

**Problem identified**: v0.2 attributed the Greek word choice to Jesus ("Jesus softens the conquest promise") — a theological assertion, not a philological one. Jesus taught in Aramaic; the Greek Gospels are the earliest extant text, written by his followers. The harness cannot verify whether the Greek reflects Jesus's wording or the Gospel writer's rendering.

**What changed:**

- **Four-layer hermeneutic**: Source (Hebrew) → Aramaic (not extant) → Greek (Matthew) → English (ESV). Each layer authoritative for itself alone.
- **`spoken_jesus_material` flag** in `book_index.json` — True for Matthew–John + Acts, False for epistles. Drives which prompt rules apply.
- **`aramaic_gap_acknowledged`** field on `VerseAnalysis` — analyst must name the Aramaic gap for spoken-Jesus material with OT echoes.
- **Layer-gap fields on `DiffEntry`**: `hebrew_root`, `greek_choice`, `esv_rendering`, `gap_type`, `evidence_status` — make explicit which layers the diff spans.
- **Forbidden Jesus verbs**: "softens," "reframes," "drains," "chooses," "intends," "shifts," "adapts." The reviewer and validator both enforce.
- **Reviewer checks #11–13**: Jesus-attribution, Aramaic-gap acknowledgment, evidence-status sanity.
- **Validator checks**: aramaic-gap, Jesus-attribution (regex), evidence-status.
- **6 new tests** (33 total, all passing).
- **Re-ran Matthew 5:5** under v0.3: the *yârash* → *klēronomeō* gap is now framed as "Matthew's Greek does not carry the conquest-force" (textual) rather than "Jesus softened the conquest promise" (speculative). The Aramaic gap is named in context_notes.

---

## 🔧 v0.2 Hardening (2026-07-04)

**What changed:**

- **`harness/` Python package** with `harness` CLI command (installable via `pip install -e .`)
- **NT-complete book index** auto-generated from data dirs (27 books, all Strong's prefixes verified) — replaces the hand-typed 7-book table
- **Greek text purity verifier + repair** — catches the LLM-transliteration bleed seen in legacy passages (`σtiν`, `ἐste`, `ἀdelfoί`). Multi-pass repair with Latin→Greek transliteration map.
- **SBLGNT apparatus stripper** — robust cleaning of editorial brackets (⸂⸃⸆⸇⸋) and inline verse refs
- **On-disk cache** (`.cache/`) with mtime invalidation
- **VerseBundle dataclass** — clean retrieval layer wrapping all 6 data sources
- **VerseAnalysis schema** — structured intermediate (no more fragile regex template substitution)
- **Per-verse manifest** (`runs/<run_id>/manifest.json`) with status: `pending → analyzing → analyzed → reviewing → reviewed → done`
- **Subagent prompts** (`prompts/{analyst,reviewer,corrector}.md`) — fresh Task per verse, no kv-cache bloat
- **Quality gates** (`harness/validators.py`): greek purity, ESV-phrase-in-diff, Strong's existence, style guide
- **Legacy repair**: 18 Greek-text bleed issues found and fixed across `passages/Matthew_*`
- **22 tests** passing (`tests/test_harness.py`)
- **`PROMPT.md`** agent contract — any opencode session can drive the harness with one prompt

**How to drive it**: see `PROMPT.md`. Short version:
```bash
harness plan "Matthew 23:8-12"
harness next Matthew_23-8-12     # → prompt + bundle
# spawn Task subagent, get JSON back
echo "$JSON" | harness ingest Matthew_23-8-12
harness render Matthew_23-8-12
```

---

## 🎉 Success Criteria (Pilot)

✅ **Met**:
- Successfully parsed passage reference
- Retrieved baseline translation from local ESV data
- Analyzed original language text from local Greek NT data
- Identified key Greek words with verified Strong's numbers from local concordance
- Generated expanded translation with nuances (clean English)
- Created diff analysis showing lost meaning (results-first table)
- Produced formatted markdown output
- Recovered meaningful theological insights
- Generated HTML + PDF versions for distribution
- Established results-first format as standard
- **All data sources local — no internet/API calls required**

**The pilot proves the concept works!** Four passages analyzed with significant nuance recovery, plus 2 verse files corrected with verified Strong's numbers.

---

**Project Lead**: Michael Howard  
**Analyst**: Peaches (🍑)  
**Next Review**: After Hebrew support phase

## Run Log — 2026-09-13 (Action Loop audit)
- **Nightly chain 9/11 → 9/13 verified COMPLETE, all 10/10 verses per run:**
  - 9/11: Genesis 11:1-10 (runs/Genesis_11-1-10)
  - 9/12: Genesis 11:11-20 (runs/Genesis_11-11-20)
  - 9/13: Genesis 11:21-30 (runs/Genesis_11-21-30)
- **Progress cursor:** Genesis 11:30 / total_done 554 → tonight's 00:00Z run auto-computes **Genesis 11:31-40** (progress-driven; queue-label concern dissolved).
- **Parked-draft integrity (bible-journey-harness, Michael's standing instruction):** 03-02 (mtime 8/31), 03-13 (9/6), 03-14 (9/7), 03-15 (9/8) — ALL UNTOUCHED ✅. New draft 03-21 (Matthew 6:4) created 9/13 08:14 ET, status=pending approval in #bible-journey-approval.
