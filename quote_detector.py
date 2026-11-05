#!/usr/bin/env python3
"""
quote_detector.py — Detect when an NT verse is a quote or allusion to an OT passage.

When Jesus quotes the Old Testament, the Greek NT text is already a TRANSLATION.
The Hebrew original is the true source text. This module detects such quotes by:
  1. Finding high-vote OT cross-references (openbible.info dataset)
  2. Computing lexical overlap between the NT verse and each OT candidate
  3. Flagging probable quotes where overlap exceeds a threshold
  4. Returning the Hebrew source text with word-level Strong's analysis

Usage:
    from quote_detector import QuoteDetector
    detector = QuoteDetector()
    result = detector.detect("Matthew", 5, 5)
    # Returns: { is_quote, confidence, source_ref, hebrew_text, hebrew_words, ... }

    # CLI:
    python3 quote_detector.py Matthew 5:5
    python3 quote_detector.py Matthew 23:27 --verbose
"""

import re
import sys
import json
import sqlite3
import math
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).parent
BIBLE_DB_PATH = SCRIPT_DIR / "bible-db.sqlite"

# Import cross-reference index
from cross_references import CrossReferenceIndex, XREF_BOOK_TO_DB, BOOK_DISPLAY_NAMES

# ── Stopwords ──────────────────────────────────────────────────

# Common English stopwords — filtered out before overlap comparison.
# We keep pronouns like "they", "you", "shall" because they can be meaningful in quotes.
STOPWORDS = frozenset({
    'a', 'an', 'the', 'and', 'or', 'but', 'of', 'in', 'on', 'at', 'to', 'for',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'by', 'with', 'from',
    'as', 'into', 'through', 'unto', 'upon', 'out', 'up', 'down', 'over',
    'that', 'this', 'these', 'those', 'which', 'who', 'whom', 'whose',
    'do', 'does', 'did', 'done', 'have', 'has', 'had', 'having',
    'not', 'no', 'nor', 'neither', 'either', 'both', 'all', 'also',
    'so', 'than', 'then', 'there', 'here', 'where', 'when', 'why', 'how',
    'it', 'its', 'if', 'whether', 'because', 'since', 'though', 'although',
    'may', 'might', 'can', 'could', 'would', 'should', 'must',
    'i', 'we', 'us', 'our', 'ours', 'my', 'mine', 'me',
    'am', 'pm',
})

# Words that are meaningful even if common — keep these even though they're frequent
MEANINGFUL_COMMON = frozenset({
    'shall', 'will', 'they', 'you', 'he', 'she', 'we',
    'blessed', 'woe', 'inherit', 'earth', 'land', 'lord', 'god',
    'son', 'man', 'men', 'people', 'nation', 'king', 'kingdom',
    'sin', 'sinful', 'righteous', 'wicked', 'holy', 'unclean',
    'blood', 'bone', 'bones', 'dead', 'death', 'life', 'live',
    'heart', 'soul', 'spirit', 'flesh', 'body',
    'fire', 'water', 'bread', 'wine', 'cup',
    'house', 'temple', 'altar', 'grave', 'sepulchre', 'tomb',
    'gentle', 'meek', 'mild', 'humble', 'poor', 'rich',
})


def _tokenize(text):
    """Tokenize English text into content words (lowercase, no punctuation)."""
    # Lowercase and split on non-alpha
    words = re.findall(r"[a-z']+", text.lower())
    # Filter: keep if not a stopword OR if it's a meaningful common word
    return [w for w in words if w not in STOPWORDS or w in MEANINGFUL_COMMON]


def _jaccard_similarity(set_a, set_b):
    """Jaccard similarity: |A ∩ B| / |A ∪ B|"""
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _overlap_recall(nt_words, ot_words):
    """
    Directional overlap: what fraction of NT content words appear in the OT verse?
    High recall = most of the NT verse is found in the OT = likely a quote.
    """
    if not nt_words:
        return 0.0
    nt_set = set(nt_words)
    ot_set = set(ot_words)
    shared = nt_set & ot_set
    return len(shared) / len(nt_set)


def _phrase_overlap(nt_text, ot_text):
    """
    Check for shared consecutive word sequences (2+ content words).
    Returns: list of shared phrases.
    """
    nt_tokens = re.findall(r"[a-z']+", nt_text.lower())
    ot_tokens = re.findall(r"[a-z']+", ot_text.lower())

    # Build 2-grams and 3-grams from OT
    ot_bigrams = set()
    for i in range(len(ot_tokens) - 1):
        ot_bigrams.add((ot_tokens[i], ot_tokens[i+1]))

    ot_trigrams = set()
    for i in range(len(ot_tokens) - 2):
        ot_trigrams.add((ot_tokens[i], ot_tokens[i+1], ot_tokens[i+2]))

    # Check NT against OT
    shared_phrases = []
    for i in range(len(nt_tokens) - 1):
        bg = (nt_tokens[i], nt_tokens[i+1])
        if bg in ot_bigrams:
            # Only count if at least one word is a content word
            if any(w not in STOPWORDS for w in bg):
                shared_phrases.append(' '.join(bg))

    for i in range(len(nt_tokens) - 2):
        tg = (nt_tokens[i], nt_tokens[i+1], nt_tokens[i+2])
        if tg in ot_trigrams:
            shared_phrases.append(' '.join(tg))

    return shared_phrases


class QuoteDetector:
    """Detects when an NT verse quotes or closely alludes to an OT passage."""

    def __init__(self, bible_db_path=None):
        self.xref = CrossReferenceIndex()
        self.bible_db_path = Path(bible_db_path) if bible_db_path else BIBLE_DB_PATH
        self._db = None

    def _get_db(self):
        if self._db is not None:
            return self._db
        if not self.bible_db_path.exists():
            return None
        self._db = sqlite3.connect(str(self.bible_db_path))
        self._db.row_factory = sqlite3.Row
        return self._db

    def _get_kjv_text(self, book_id, chapter, verse):
        """Get KJV text for any book/chapter/verse from bible-db."""
        conn = self._get_db()
        if not conn:
            return None
        cursor = conn.execute(
            'SELECT text FROM verses WHERE book=? AND chapter=? AND verse=? AND source=?',
            (book_id, chapter, verse, 'kjv')
        )
        row = cursor.fetchone()
        return row['text'] if row else None

    def _get_hebrew_text(self, book_id, chapter, verse):
        """Get Hebrew (WLC) text from bible-db."""
        conn = self._get_db()
        if not conn:
            return None
        cursor = conn.execute(
            'SELECT text FROM verses WHERE book=? AND chapter=? AND verse=? AND source=?',
            (book_id, chapter, verse, 'wlc')
        )
        row = cursor.fetchone()
        return row['text'] if row else None

    def _get_hebrew_words(self, book_id, chapter, verse):
        """Get word-level Hebrew analysis with Strong's numbers."""
        conn = self._get_db()
        if not conn:
            return []

        cursor = conn.execute('''
            SELECT w.id, w.w, w.surface, w.morph, ws.strong
            FROM words w
            LEFT JOIN word_strong ws ON ws.word_id = w.id
            WHERE w.book=? AND w.chapter=? AND w.verse=? AND w.source='wlc'
            ORDER BY w.w
        ''', (book_id, chapter, verse))

        words = []
        for row in cursor.fetchall():
            d = dict(row)
            word_entry = {
                'position': d['w'],
                'surface': d['surface'],
                'morph': d['morph'],
                'strong': d['strong'],
            }

            # Enrich with Strong's definition
            if d['strong']:
                strong_id = d['strong']
                cursor2 = conn.execute(
                    'SELECT lemma, translit, pron, derivation, strongs_def, kjv_def FROM strongs WHERE strong=?',
                    (strong_id,)
                )
                srow = cursor2.fetchone()
                if srow:
                    sd = dict(srow)
                    word_entry['strongs_data'] = {
                        'lemma': sd['lemma'],
                        'translit': sd['translit'],
                        'derivation': sd['derivation'],
                        'strongs_def': sd['strongs_def'],
                        'kjv_def': sd['kjv_def'],
                    }

                # Semantic categories
                cursor3 = conn.execute(
                    'SELECT category, is_primary FROM strong_category WHERE strong=?',
                    (strong_id,)
                )
                cats = [{'category': r['category'], 'is_primary': bool(r['is_primary'])}
                        for r in cursor3.fetchall()]
                if cats:
                    word_entry['categories'] = cats

            words.append(word_entry)

        return words

    def detect(self, book, chapter, verse, threshold=0.4, min_votes=5, verbose=False):
        """
        Detect if an NT verse is a quote/allusion to an OT passage.

        Args:
            book: Book name (e.g., "Matthew")
            chapter: Chapter number
            verse: Verse number
            threshold: Minimum overlap recall to flag as a quote (default 0.4)
            min_votes: Minimum cross-reference votes to consider (default 5)
            verbose: Include detailed scoring in output

        Returns:
            dict: {
                'query': {'book', 'chapter', 'verse'},
                'is_ot_quote': bool,
                'confidence': float,  # 0.0-1.0
                'source': {  # best OT match, or null
                    'book_id', 'book_name', 'chapter', 'verse',
                    'votes', 'kjv_text', 'hebrew_text', 'hebrew_words',
                    'overlap_recall', 'jaccard', 'shared_terms', 'shared_phrases',
                },
                'candidates': [...],  # all OT candidates scored (if verbose)
            }
        """
        # Get cross-references
        xref_result = self.xref.lookup(book, chapter, verse, include_hebrew=False, min_votes=1)
        refs = xref_result.get('cross_references', [])

        # Get NT verse KJV text
        # First, find the book_id for the NT verse
        book_abbr = self.xref._book_to_xref_key(book)
        nt_book_id = XREF_BOOK_TO_DB.get(book_abbr)
        nt_kjv = self._get_kjv_text(nt_book_id, chapter, verse) if nt_book_id else None

        if not nt_kjv:
            return {
                'query': {'book': book, 'chapter': chapter, 'verse': verse},
                'is_ot_quote': False,
                'confidence': 0.0,
                'source': None,
                'candidates': [],
                'note': 'Could not retrieve NT verse text for comparison',
            }

        nt_words = _tokenize(nt_kjv)
        nt_word_set = set(nt_words)

        candidates = []
        best_match = None
        best_score = 0.0

        for ref in refs:
            if ref['votes'] < min_votes:
                continue
            if ref['testament'] != 'OT':
                continue

            # Get OT verse KJV text
            ot_kjv = ref.get('kjv_text') or self._get_kjv_text(
                ref['db_book_id'], ref['chapter'], ref['verse']
            )
            if not ot_kjv:
                continue

            ot_words = _tokenize(ot_kjv)
            ot_word_set = set(ot_words)

            # Compute metrics
        recall = _overlap_recall(nt_words, ot_words)
            jaccard = _jaccard_similarity(nt_word_set, ot_word_set)
            shared_terms = sorted(nt_word_set & ot_word_set)
            shared_phrases = _phrase_overlap(nt_kjv, ot_kjv)

            # Composite score: recall is primary (how much of NT is in OT)
            # Boost for shared phrases (consecutive word matches = stronger signal)
            phrase_boost = min(len(shared_phrases) * 0.1, 0.3)
            # Boost for high vote count (community consensus)
            vote_boost = min(math.log10(ref['votes'] + 1) * 0.05, 0.15)
            # Composite: recall + phrase_boost + vote_boost
            composite = recall + phrase_boost + vote_boost

            candidate = {
                'book_id': ref['db_book_id'],
                'book_name': ref['book_name'],
                'book_abbr': ref['book_abbr'],
                'chapter': ref['chapter'],
                'verse': ref['verse'],
                'votes': ref['votes'],
                'kjv_text': ot_kjv,
                'overlap_recall': round(recall, 3),
                'jaccard': round(jaccard, 3),
                'composite_score': round(composite, 3),
                'shared_terms': shared_terms,
                'shared_phrases': shared_phrases,
            }

            if composite >= threshold:
                candidate['is_quote_candidate'] = True

            candidates.append(candidate)

            if composite > best_score:
                best_score = composite
                best_match = candidate

        # Sort candidates by composite score
        candidates.sort(key=lambda c: c['composite_score'], reverse=True)

        # Determine if best match is a quote
        is_quote = best_match is not None and best_match['composite_score'] >= threshold

        # If it's a quote, fetch Hebrew text and words
        source = None
        if is_quote and best_match:
            hebrew_text = self._get_hebrew_text(
                best_match['book_id'], best_match['chapter'], best_match['verse']
            )
            hebrew_words = self._get_hebrew_words(
                best_match['book_id'], best_match['chapter'], best_match['verse']
            )

            source = {
                'book_id': best_match['book_id'],
                'book_name': best_match['book_name'],
                'book_abbr': best_match['book_abbr'],
                'chapter': best_match['chapter'],
                'verse': best_match['verse'],
                'votes': best_match['votes'],
                'kjv_text': best_match['kjv_text'],
                'hebrew_text': hebrew_text,
                'hebrew_words': hebrew_words,
                'overlap_recall': best_match['overlap_recall'],
                'jaccard': best_match['jaccard'],
                'composite_score': best_match['composite_score'],
                'shared_terms': best_match['shared_terms'],
                'shared_phrases': best_match['shared_phrases'],
            }

        result = {
            'query': {'book': book, 'chapter': chapter, 'verse': verse},
            'nt_kjv_text': nt_kjv,
            'is_ot_quote': is_quote,
            'confidence': round(best_score, 3) if best_match else 0.0,
            'threshold': threshold,
            'source': source,
        }

        if verbose:
            result['candidates'] = candidates

        return result

    def format_result(self, result, verbose=False):
        """Format detection result as readable markdown."""
        lines = []
        q = result['query']
        lines.append(f"## 🔍 OT Quote Detection: {q['book']} {q['chapter']}:{q['verse']}")
        lines.append("")

        if result['is_ot_quote'] and result['source']:
            s = result['source']
            lines.append(f"**✅ QUOTE DETECTED** — {s['book_name']} {s['chapter']}:{s['verse']} (confidence: {result['confidence']})")
            lines.append("")
            lines.append(f"**NT verse (KJV)**: {result.get('nt_kjv_text', 'N/A')}")
            lines.append(f"**OT source (KJV)**: {s['kjv_text']}")
            if s.get('hebrew_text'):
                lines.append(f"**Hebrew (WLC)**: {s['hebrew_text']}")
            lines.append("")
            lines.append(f"**Overlap recall**: {s['overlap_recall']} | **Jaccard**: {s['jaccard']} | **Composite**: {s['composite_score']}")
            lines.append(f"**Shared terms**: {', '.join(s['shared_terms'])}")
            if s['shared_phrases']:
                lines.append(f"**Shared phrases**: {', '.join(s['shared_phrases'])}")
            lines.append("")

            # Hebrew word analysis
            if s.get('hebrew_words'):
                lines.append("### Hebrew Word Analysis")
                lines.append("")
                lines.append("| Word | Strong's | Transliteration | Definition | Categories |")
                lines.append("|------|----------|-----------------|------------|------------|")
                for w in s['hebrew_words']:
                    strong_id = w.get('strong', '')
                    sd = w.get('strongs_data', {})
                    translit = sd.get('translit', '')
                    definition = sd.get('strongs_def', '').strip() or sd.get('kjv_def', '').strip()
                    if len(definition) > 100:
                        definition = definition[:97] + '...'
                    cats = ', '.join(
                        c['category'] for c in w.get('categories', [])
                        if c.get('is_primary')
                    )
                    surface = w.get('surface', '')
                    lines.append(f"| {surface} | {strong_id} | {translit} | {definition} | {cats} |")
                lines.append("")

                # Derivation chains
                lines.append("### Derivation Chains")
                for w in s['hebrew_words']:
                    sd = w.get('strongs_data', {})
                    derivation = sd.get('derivation', '').strip()
                    strongs_def = sd.get('strongs_def', '').strip()
                    if derivation and len(derivation) > 10:
                        strong_id = w.get('strong', '')
                        lines.append(f"- **{strong_id}** ({sd.get('translit', '')}): {strongs_def}")
                        lines.append(f"  - *Derivation*: {derivation}")
        else:
            lines.append("**❌ No OT quote detected** — verse appears to be original Greek composition.")
            lines.append(f"Best match score: {result['confidence']} (threshold: {result['threshold']})")

        if verbose and result.get('candidates'):
            lines.append("")
            lines.append("### All Candidates")
            lines.append("")
            lines.append("| OT Verse | Votes | Recall | Jaccard | Composite | Shared Terms |")
            lines.append("|----------|-------|--------|----------|-----------|--------------|")
            for c in result['candidates'][:10]:
                shared = ', '.join(c['shared_terms'][:5])
                flag = " ✸" if c.get('is_quote_candidate') else ""
                lines.append(f"| {c['book_name']} {c['chapter']}:{c['verse']}{flag} | {c['votes']} | {c['overlap_recall']} | {c['jaccard']} | {c['composite_score']} | {shared} |")

        return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Detect if an NT verse quotes an OT passage")
    parser.add_argument("book", help="Book name (e.g., Matthew)")
    parser.add_argument("passage", help="Passage (e.g., 5:5)")
    parser.add_argument("--threshold", type=float, default=0.4,
                        help="Minimum composite score to flag as quote (default 0.4)")
    parser.add_argument("--min-votes", type=int, default=5,
                        help="Minimum cross-ref votes (default 5)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show all candidates with scores")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON")

    args = parser.parse_args()

    if ":" in args.passage:
        ch, v = args.passage.split(":")
        chapter, verse = int(ch), int(v)
    else:
        print("Passage must be in format chapter:verse (e.g., 5:5)")
        sys.exit(1)

    detector = QuoteDetector()
    result = detector.detect(args.book, chapter, verse,
                             threshold=args.threshold,
                             min_votes=args.min_votes,
                             verbose=args.verbose)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(detector.format_result(result, verbose=args.verbose))
