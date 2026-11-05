# Claim Audit Layer — Integration Spec (v1.0)

**Status:** Proposed — ready for OpenCode integration
**Date:** 2026-09-14
**Origin:** Drafted after the Genesis 6:2 audit (laqach/nashim overreach). Michael directed a new safeguard layer so the harness stops stretching past what the text licenses.
**Scope:** 4K Bible Translation Harness — all analysis runs (OT Hebrew and NT Greek)

---

## 1. Purpose

The harness's four-layer model already governs *where* claims may live (`evidence_status`, field placement) and *who* may be said to have done what (layer attribution). What it does not yet govern is whether a claim about meaning is **licensed by the construction** — whether the text actually bears the weight the prose puts on it.

The Genesis 6:2 run exposed this gap: every claim was well-formed, correctly placed, and unlicensed by the Hebrew. This spec adds a **claim-audit layer**: rules the analyst follows at generation time, and the reviewer enforces at review time.

## 2. The specimen failure (Genesis 6:2)

What `runs/Genesis_6-1-10/Genesis_6-2.md` asserted:

- *"they took for themselves women (literally 'women', not 'wives' — the Hebrew does not use the marriage verb here)"*
- *"לָקַח … not the covenantal marriage verb חָתַן"*
- *"ASV's 'took them wives' imports a marital framework the Hebrew does not assert"*

What the Hebrew supports:

- **lāqaḥ + nāšîm is the standard marriage idiom** for a man taking a wife: Gen 4:19 (וַיִּקַּח־לוֹ … נָשִׁים — the closest structural match to 6:2's וַיִּקְחוּ לָהֶם נָשִׁים), Gen 11:29, Gen 12:19 ("I took her for myself as a wife"), and Deut 7:3 itself uses lāqaḥ for the forbidden marriage-taking ("his daughter you shall not take for your son").
- ḥātan is **not** the standard "man marries" verb; it means *give in marriage / intermarry* and is rare. The contrast drawn in the file is false — there is no standard alternative verb that the narrator avoided.
- The same file's word table says of nāšîm: *"woman / wife (the same lexeme covers both; context decides)"* — and the prose then overrides the hedge.

Four failure classes (these define what the layer must catch):

- **F1 — Lexeme-as-meaning:** the word's full lexical range is treated as the operative meaning. ("laqach means take in the widest sense — seize" → "the act reads as appropriation.")
- **F2 — Unbacked contrast:** "X, not Y" without showing Y is available/expected in comparable constructions. ("not the covenantal marriage verb ḥātan.")
- **F3 — Table-prose override:** prose asserts what the word table hedges. (table: "context decides" / prose: "not 'wives.'")
- **F4 — Certainty inflation:** intent/rhetoric asserted without parallel evidence. ("ASV's 'took them wives' imports a marital framework.")

## 3. Design principles

1. **Generation-side first.** The cheapest place to fix overstatement is the analyst prompt. Reviewer enforcement is the backstop, not the primary defense.
2. **Interpretation is welcome; licensing is mandatory.** This layer does not filter theology. It relabels and relocates unlicensed claims per the existing `evidence_status` discipline.
3. **Ride the existing correction loop.** No new pipeline stage. Claim-audit findings are review.json corrections with a `rule` field; validators gain a machine-checkable subset.
4. **The word table is the anchor of record.** Morphology, stem, and lexical-range facts are always allowed. What needs licensing is the *step from range to meaning*.

## 4. Rule set

Verdict vocabulary (used by analyst self-audit and reviewer findings):

- **licensed** — claim stands; required parallel/citation present.
- **downgraded** — claim restated with calibrated wording and/or hedge; or relocated with a tag.
- **cut** — removed from diffs/expanded translation. Cut content is *moved, not deleted* — to `further_study` with `evidence_status: inferential` or `speculative` if it retains study value.

### CA-1 — Collocation licensing (kills F1)

A claim about what a word or construction **means in this verse** must cite **≥1 parallel passage where the same construction** (verb+object pair, idiom, stem+argument structure) **carries the claimed meaning**. Lexical-range entries may never be the sole support for a prose conclusion.

- Check: does the claim's support reduce to the Strong's/BDB range line?
- Example pass: "took wives — the marriage idiom lāqaḥ nāšîm (Gen 4:19; 11:29; 12:19)."
- Example fail: "laqach means seize → the act is seizure" (no parallel where lāqaḥ nāšîm means forcible seizure; the idiom elsewhere is marriage).

### CA-2 — Contrast citation (kills F2)

Every "X, not Y" / "Y rather than X" claim must demonstrate **Y is actually available and expected** in comparable constructions, with ≥1 citation. If Y is not the standard alternative, the contrast is cut and the claim restated positively.

- Example fail: "not the covenantal marriage verb ḥātan" — ḥātan is not the man-marries verb; the standard idiom *is* laqach nashim, so there is no contrast.
- Example pass: a root-contrast claim with verses showing both roots used in comparable constructions.

### CA-3 — Table-prose consistency (kills F3)

Prose may never assert what the word table hedges. The analyst must carry the hedge into the prose; the reviewer flags contradictions.

- Machine-checkable subset (see §7): extract hedge markers from the Nuance column ("context decides", "may", "possibly", "either", "or") and flag prose sentences in the same file that assert one side unhedged.
- Specimen fix: "women/wives — ʾiššâ spans both; here the conjugal context (v.4 'came in to…') makes 'wives' the natural English, though only the takers' side is given verbs of agency."

### CA-4 — Certainty calibration (kills F4)

Strong-intent/rhetorical verbs — "signals," "frames," "deliberately," "the narrator's choice," "imports," "inverts" (as claims about an author's or translator's act) — require either (a) a cited parallel, or (b) explicit hedging ("as if," "invites the reader to hear," "may recall"). Otherwise the verb is downgraded to "resonates with / recalls / invites."

- Claims about a *human author's or translator's intent* are by default `inferential` (this is already reviewer practice; make it explicit for insights, not just diffs).

### CA-5 — Contested-reading map

When a reading material to the translation choice is disputed (in scholarship or tradition), the file must state: (a) what the Hebrew/Greek **usage across the canon** favors; (b) which **communities later preferred alternatives**, and roughly when/why; (c) whether the language itself adjudicates.

- Calibration template: `Genesis_6-4.md`'s sons-of-God treatment (canonical usage in Job 1:6; 2:1; 38:7; Ps 82; 89:6-7; Deut 32:8 Qumran+LXX; pre-Christian Jewish sources on the divine side; Augustine's later Sethite shift; "the Hebrew morphology does not adjudicate"). Treat 6-4 as the passing example.

### CA-6 — Concept-import detector

A theological keyterm whose **Hebrew/Greek root is absent from the verse text** (e.g., "covenant" in Gen 6:1-4, where בְּרִית first appears in v.18) may not appear as a claim about what the text says — not in diffs, not unhedged in the expanded translation. It belongs in insights/further_study with `evidence_status: inferential` or `speculative`.

- Machine-checkable subset: keyterm-in-claim vs root-presence-in-bundle-text; reviewer confirms.

### CA-7 — Layer attribution (existing rule, extended to OT runs)

PROMPT.md's attribution rules were written for spoken-Jesus material; extend the audit to OT runs: claims describe **the text and its writers**, never speakers or communities beyond the extant words ("the Torah's narrator," not "Moses felt"). Nothing new to generate — the reviewer re-checks it here.

## 5. Severity and placement policy

The bar scales with how close the claim sits to the translation itself:

| Field | Bar | Unlicensed claim |
|-------|-----|------------------|
| 4K expanded translation, diffs | translation-defining | **error** (blocks finalize) |
| theological insights | interpretive | **warning** unless tagged (`evidence_status`) |
| further_study | tagged reflection | pass (must carry tag) |

Severity semantics reuse the existing review loop: `error` corrections must be resolved before finalize; `warning`s are reported in SUMMARY.

## 6. Pipeline integration (recommended)

No new stage. The audit folds into the existing loop:

1. `prompts/analyst.md` — add a **Licensing Requirements** section (CA-1, CA-2, CA-4 + a short self-audit checklist before returning VerseAnalysis JSON). Generation-side is the primary defense.
2. `prompts/reviewer.md` — add the full CA-1..CA-7 rule sheet and require: every finding citing a rule carries `rule: "CA-x"` and `claim: "<quoted text>"`.
3. `review.json` schema — extend corrections entries with optional `rule` (string) and `claim` (string); add `summary.claim_audit: {total, licensed, downgraded, cut}`. (`harness/schema.py`)
4. `harness/validators.py` — add the machine-checkable heuristics from §7 as ingest-time warnings (analyst-side and reviewer-side outputs both pass through ingest).
5. `prompts/corrector.md` — one line: fixes must preserve table hedges and calibrated wording; do not strengthen a downgraded claim while correcting something else.
6. `PROMPT.md` — add one bullet to "Rules the harness enforces" pointing at this file as the canonical rule sheet.

*Alternative:* if strict separation is preferred, a standalone audit pass (`harness next-audit` → `.audit.json`) inserted between ingest and next-review is acceptable — but it adds orchestrator plumbing for no review-quality gain; folding into the reviewer is cheaper and keeps one correction loop.

## 7. Machine-checkable validator heuristics (subset)

Full semantic licensing is a reviewer judgment. These are mechanical ingest-time checks that emit `warning` (never `error`) for the reviewer to confirm:

- **Hedge-extraction (CA-3):** regex hedge list over Nuance cells → contradiction scan against prose sections (fuzzy; reviewer confirms).
- **Citation-presence (CA-1/CA-2):** a meaning/contrast claim lacking a scripture citation in the same sentence or bullet → warning.
- **Certainty lexicon (CA-4):** strong-intent verb list without adjacent citation or hedge marker → warning.
- **Root-presence (CA-6):** configurable keyterm list (e.g., covenant/berit; hesed; torah) → if an English keyterm appears in a diff/insight claim but its root is absent from the verse's source text in the bundle → warning.

## 8. Worked calibration example (Genesis 6:2)

**Before (current diff #4 + insight #3):** as quoted in §2.

**After (CA-licensed):**

- Expanded translation: "…and they took for themselves wives (lāqaḥ nāšîm — the standard marriage idiom, as in Gen 4:19; 11:29; 12:19) from all that they chose (unrestricted selection — the takers' side is the only side given verbs; no consent, no giving side, no limit. The transgression is in the *execution*, not in a special verb)."
- Diff #4 rewritten: what ASV loses is not "marriage framework" but the *benefactive "for themselves"* plus the *unbounded "from all that they chose"* — the marriage-taking is textually real; its execution is what reads as appropriation.
- Insight rewritten under CA-2/CA-4: drop the ḥātan contrast (CA-2 fail); state the family-arrangement point with citations (Ex 22:16-17; Gen 34:12) as context-supported, tagged `inferential`.

## 9. Acceptance criteria

1. Re-running Genesis 6:2 through the updated pipeline produces claim-audit findings on the original diff #4 and insight #3 (CA-1/CA-2/CA-3/CA-4 as applicable), with minimal edits matching §8 in substance.
2. Re-running Genesis 6:4 passes CA-5 (contested-reading map intact).
3. Regression: existing structural corrections (e.g., verbatim `baseline_phrase` checks) still flow; severity behavior unchanged for non-CA findings.
4. No verse reaches "Ready for Review" with an error-severity CA violation unresolved.
5. `SUMMARY` rendering includes claim-audit counts without breaking existing render.

## 10. Non-goals

- **Not a doctrine filter.** Theological synthesis remains welcome — tagged and placed.
- **Not a parallel-passage auto-verifier.** Analyst/reviewer supply citations; validators check *presence*; the reviewer judges *relevance*.
- **No re-adjudication of legacy runs.** The layer applies at generation/review time. Existing files (like 6-2.md) can be patched separately if desired.
