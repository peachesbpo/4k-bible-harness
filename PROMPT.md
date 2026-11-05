# 4K Bible Translation Harness — Agent Operating Contract

## Hermeneutic posture (v0.3)

The harness operates on a **four-layer** model. Each layer is authoritative for itself alone, not for the layer above or below it.

| Layer | Language | Agent | Authoritative for |
|-------|----------|-------|-------------------|
| Source concept | Hebrew (OT) | Psalmist / prophet | what the source promise carried |
| Jesus's teaching | Aramaic (not extant) | Jesus | unknown — we do not have these words |
| Gospel rendering | Greek | Matthew / the Gospel writer | what the written text says |
| English | WEB | modern translators | nothing — it is the translation we are diffing against |

**Rules the harness enforces:**

- **Never attribute the Greek word choice to Jesus.** Jesus taught in Aramaic; the Greek Gospel is the earliest extant text, written by his followers. The harness uses "Matthew renders," "the Greek does not carry," "the Gospel drops." It does NOT use "Jesus softens," "Jesus reframes," "Jesus chooses."
- **For spoken-Jesus material** (Matthew, Mark, Luke, John, Acts) **with OT cross-references**: the analyst names the Aramaic gap explicitly. Claims describe the Greek text, not Jesus's spoken words.
- **For epistles** (Romans→Jude, Revelation): the Greek IS the original. The Aramaic-gap rule does not apply.
- **Each OT-echo diff carries layer-gap fields**: `hebrew_root`, `greek_choice`, `web_rendering`, `gap_type`, `evidence_status`. Speculative claims (about Jesus's intent, Aramaic wording) are flagged `evidence_status: "speculative"` and belong in `further_study`, not `diffs` or `insights`.
- **Claim audit (CA-1..CA-7)**: every claim about meaning must be licensed by the construction — meaning claims cite a parallel with the same construction, "X, not Y" contrasts are demonstrated with citations, table hedges carry into prose, intent claims are hedged or tagged, and theological keyterms absent from the verse's source text stay out of diffs. Unlicensed claims in translation-defining fields block finalize. Canonical rule sheet: `prompts/claim-audit-spec.md`.

## Quick start

This file is the canonical instruction any opencode agent (or human) should
follow to drive the harness. The harness CLI is pure Python — the agent is the
orchestrator that spawns fresh Task subagents per verse (no kv-cache bloat).

## Quick start

```bash
# 1. Plan a passage run (creates runs/<run_id>/manifest.json)
harness plan "Matthew 23:8-12"

# 2. Loop: fetch next pending verse, spawn analyst subagent, ingest result
harness next <run_id>        # emits {book, chapter, verse, bundle, prompt}
#   ... pipe `prompt` to a fresh Task subagent ...
#   ... subagent returns VerseAnalysis JSON ...
echo "$JSON" | harness ingest <run_id>

# 3. Review loop
harness next-review <run_id>  # emits {analysis, bundle, prompt}
#   ... spawn reviewer subagent with prompt ...
#   ... reviewer returns {valid, corrections, summary} ...
echo "$JSON" | harness ingest-review <run_id>

# 4. Correction loop (only for verses that failed review)
harness next-correction <run_id>
#   ... spawn corrector subagent ...
echo "$JSON" | harness finalize <run_id>

# 5. Mark reviewed verses as done, render SUMMARY
harness mark-done <run_id>
harness render <run_id>
```

## Whole-book iterative mode

```bash
harness book Matthew          # creates runs/Matthew_verse_by_verse/
# Then run the same next → ingest loop verse by verse. The manifest tracks
# per-verse status; resume any time. Checkpoint is per-verse, so a crash
# loses at most one verse of work.
```

## Status

```bash
harness status                # list all runs
harness status <run_id>      # one run's verse-state counts
```

## Subagent dispatch pattern (opencode Task tool)

For each verse:

1. `harness next <run_id>` → get `prompt` and `bundle` for the next pending verse.
2. Spawn a **fresh** Task subagent (no `task_id` resume) with:
   - `subagent_type: "general"`
   - `prompt: <the prompt from step 1>`
   - Instruct: "Return ONLY the JSON object. No prose, no markdown fences."
3. Parse the subagent's response as JSON. If it wrapped in fences, strip them.
4. `echo "$JSON" | harness ingest <run_id>` → writes files, runs validators, updates manifest.
5. If `validators_ok` is false, the verse is still `analyzed` but flagged; the review pass will catch issues.

Spawn **one subagent per verse**. Do not batch — that defeats the kv-cache isolation.

## Subagent contract

The analyst subagent receives the full prompt in `prompts/analyst.md` with the
VerseBundle JSON inlined. It must return a single JSON object matching
`harness/schema.py::VerseAnalysis`. The ingest command validates:

- Greek text purity (no Latin letters in Greek source)
- WEB phrase appears in diffs (no fabrication)
- Strong's numbers match the concordance
- Style guide (no Greek/Strong's/parsing in expanded translation)

Validation issues are recorded in the manifest but do not block ingest — the
review pass handles corrections.

## Repairs

```bash
harness repair passages/            # dry-run scan
harness repair passages/ --apply    # fix Greek-text bleed in legacy files
```

## Cache

```bash
harness cache stats
harness cache clear [version]      # version: greek|web|kjv, or all
```

## Files

- `harness/book_index.json` — auto-generated NT book mappings (run `scripts/build_book_index.py` to rebuild)
- `runs/<run_id>/manifest.json` — per-verse status tracker
- `runs/<run_id>/<Book>_<ch>-<v>.md` — human-readable verse analysis
- `runs/<run_id>/<Book>_<ch>-<v>.json` — structured sidecar
- `runs/<run_id>/SUMMARY.md` — aggregated passage summary
- `.cache/<version>/<book>/<ch>/<v>.json` — parsed verse cache (mtime-keyed)
- `prompts/{analyst,reviewer,corrector}.md` — subagent prompts
