# 4K Bible Harness

A local-first Bible study harness that reads the original languages of Scripture — Greek New Testament, Hebrew OT, Strong's numbers, classical lexicons — and produces expanded English translations ("the director's cut") alongside standard translations, with a diff layer that shows exactly what the standard translation flattens. Analysis is subagent-driven: a planner retrieves verified source text locally, per-verse subagents analyze, a reviewer validates, and a corrector applies fixes — every claim checked against the actual sources on disk.

## Why local

Everything runs on your machine against data files you control:

- **Privacy** — nothing about what you study leaves your machine.
- **No meter** — no API keys, no usage meters, no rate limits; the sources are on disk and reading them is free.
- **Total control** — you choose the model, the prompts, the validators, and the outputs. Swap models, edit the claim-audit rules, fork the validators. The harness never phones home.

## Install

```bash
pip install -e .          # or: pip install -r requirements.txt
python scripts/download_data.py   # fetches datasets into data/ (~250 MB)
```

Then link or place the local Bible database, `bible-db.sqlite`, at the repo root. This file is a custom build (Westminster Leningrad Codex Hebrew text + morphology, BDB-class Hebrew lexicon, Strong's Greek entries, semantic categories) assembled from public-domain sources with no single stable public URL, so it is not auto-downloaded. Without it, the Greek NT pipeline works fully; OT Hebrew analysis degrades gracefully (the harness reports it is unavailable).

## Fetching the data

`scripts/download_data.py` downloads the six public datasets into `data/` and links them where the harness expects them. It is idempotent — re-running skips anything already present — and prints a summary at the end. Greek NT: `wldeh/bible-api` (`grc-srgnt`) via sparse checkout, upstream eBible.org. ASV: `en-asv`, same API. WEB: `TehShrike/world-english-bible` JSON, assembled per-verse. Strong's concordance + Greek dictionary: `tahmmee/interlinear_bibledata` + Open Scriptures. LSJ: `perseids-project/lsj-js`. Cross-references: openbible.info.

## Run it

```bash
# Fetch a passage with its Greek text, English, and Strong's numbers
python fetch_verse.py Matthew 23:13 --greek --esv --strongs

# One-shot passage analysis (legacy CLI)
python analyze_passage.py --passage "Matthew 23:25"

# The hardened, subagent-driven pipeline
harness plan "Matthew 23:8-12"
harness next Matthew_23-8-12          # get next verse + analysis prompt
echo "$JSON" | harness ingest Matthew_23-8-12
harness next-review Matthew_23-8-12   # review loop
harness mark-done Matthew_23-8-12 && harness render Matthew_23-8-12
```

Sample output (from `passages/Matthew_23-25/SUMMARY.md`):

> **25** Woe unto you (an exclamation of pain and anger — not just "alas" but the cry of grief itself), scribes (and "scribes" means secretaries, registrars, subordinate officials...) and Pharisees (and "Pharisees" means separatists — those who have made themselves exclusively religious, a sect apart), hypocrites (and "hypocrites" literally means stage-players — actors under an assumed character, performing a role rather than living a truth)!

Each run produces a directory with per-verse `.md` analyses plus a `SUMMARY` in markdown, styled HTML, and PDF — results-first: diff analysis, expanded translation, baseline translation, theological insights, notes for further study.

## Honest by design

This harness is an aid for reading, not an oracle. What comes out the other end is highly dependent on the model quality. Models with more world knowledge are preferred — the harness lays the sources on the table, but the reading is only as good as the reader. The output is not presented as 100% accurate: the reviewer and claim-audit layers exist precisely to catch overreach, and they ship in this repo (`prompts/`, including the claim-audit spec) so you can tighten them further. The suite of 100 automated tests guards the validators, retrieval, purity checks, and run state (97 pass without the optional `bible-db.sqlite`; all 100 with it in place).

## Credits

- **Cross-references** — from [OpenBible.info](https://www.openbible.info/labs/cross-references/), licensed under a [Creative Commons Attribution License (CC-BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- **LSJ Greek Lexicon** — courtesy of the [Perseus Digital Library](https://www.perseus.tufts.edu/) (Liddell-Scott-Jones, via the `perseids-project/lsj-js` distribution).
- **Greek New Testament (grc-srgnt)** — courtesy credit to [eBible.org](https://ebible.org/) / Solid Rock Publications: *Solid Rock Greek New Testament, Scholar's Edition* — translation by Robinson and Pierpont, contributors Joey McCollum and Stephen Brown (public domain, per eBible.org metadata).
- **Strong's Concordance & Greek dictionary** — public domain (James Strong, 1890; Open Scriptures JSON distribution).
- **English translations (ASV 1901, World English Bible, KJV)** — public domain.
- **Hebrew text & lexicon (BDB)** — public domain sources.

**Designed by Michael Howard · Built by Peaches**
