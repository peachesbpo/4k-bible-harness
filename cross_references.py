#!/usr/bin/env python3
"""
cross_references.py — Bible cross-reference lookup and Hebrew source analysis.

Uses the openbible.info cross-reference dataset (CC-BY, ~340k references)
to find verses related to a given Bible verse, then enriches OT source
verses with Hebrew word-level Strong's analysis from bible-db.sqlite.

Data source: https://www.openbible.info/labs/cross-references/
Downloaded: cross-refs/cross_references.txt (local, no internet required)

Usage:
    from cross_references import CrossReferenceIndex
    xref = CrossReferenceIndex()
    refs = xref.lookup("Matthew", 5, 5)
    # Returns list of cross-referenced verses, sorted by vote count,
    # with Hebrew word analysis for OT sources.
"""

import re
import sqlite3
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
XREF_PATH = SCRIPT_DIR / "cross-refs" / "cross_references.txt"
BIBLE_DB_PATH = SCRIPT_DIR / "bible-db.sqlite"

# Mapping from openbible.info book abbreviations to bible-db.sqlite book IDs.
# This is the key lookup table that connects cross-references to our Hebrew data.
XREF_BOOK_TO_DB = {
    # Old Testament (books 1-39)
    'Gen': 1, 'Exod': 2, 'Lev': 3, 'Num': 4, 'Deut': 5,
    'Josh': 6, 'Judg': 7, 'Ruth': 8,
    '1Sam': 9, '2Sam': 10, '1Kgs': 11, '2Kgs': 12,
    '1Chr': 13, '2Chr': 14,
    'Ezra': 15, 'Neh': 16, 'Esth': 17, 'Job': 18,
    'Ps': 19, 'Prov': 20, 'Eccl': 21, 'Song': 22,
    'Isa': 23, 'Jer': 24, 'Lam': 25,
    'Ezek': 26, 'Dan': 27, 'Hos': 28, 'Joel': 29,
    'Amos': 30, 'Obad': 31, 'Jonah': 32, 'Mic': 33,
    'Nah': 34, 'Hab': 35, 'Zeph': 36, 'Hag': 37,
    'Zech': 38, 'Mal': 39,
    # New Testament (books 40-66)
    'Matt': 40, 'Mark': 41, 'Luke': 42, 'John': 43,
    'Acts': 44, 'Rom': 45,
    '1Cor': 46, '2Cor': 47,
    'Gal': 48, 'Eph': 49, 'Phil': 50, 'Col': 51,
    '1Thess': 52, '2Thess': 53,
    '1Tim': 54, '2Tim': 55,
    'Titus': 56, 'Phlm': 57, 'Heb': 58, 'Jas': 59,
    '1Pet': 60, '2Pet': 61,
    '1John': 62, '2John': 63, '3John': 64,
    'Jude': 65, 'Rev': 66,
}

# Reverse mapping: bible-db book ID to openbible abbreviation
DB_BOOK_TO_XREF = {v: k for k, v in XREF_BOOK_TO_DB.items()}

# Book display names for human-readable output
BOOK_DISPLAY_NAMES = {
    'Gen': 'Genesis', 'Exod': 'Exodus', 'Lev': 'Leviticus', 'Num': 'Numbers',
    'Deut': 'Deuteronomy', 'Josh': 'Joshua', 'Judg': 'Judges', 'Ruth': 'Ruth',
    '1Sam': '1 Samuel', '2Sam': '2 Samuel', '1Kgs': '1 Kings', '2Kgs': '2 Kings',
    '1Chr': '1 Chronicles', '2Chr': '2 Chronicles',
    'Ezra': 'Ezra', 'Neh': 'Nehemiah', 'Esth': 'Esther', 'Job': 'Job',
    'Ps': 'Psalm', 'Prov': 'Proverbs', 'Eccl': 'Ecclesiastic', 'Song': 'Song',
    'Isa': 'Isaiah', 'Jer': 'Jeremiah', 'Lam': 'Lamentations',
    'Ezek': 'Ezekiel', 'Dan': 'Daniel', 'Hos': 'Hosea', 'Joel': 'Joel',
    'Amos': 'Amos', 'Obad': 'Obadiah', 'Jonah': 'Jonah', 'Mic': 'Micah',
    'Nah': 'Nahum', 'Hab': 'Habakkuk', 'Zeph': 'Zephaniah', 'Hag': 'Haggai',
    'Zech': 'Zechariah', 'Mal': 'Malachi',
    'Matt': 'Matthew', 'Mark': 'Mark', 'Luke': 'Luke', 'John': 'John',
    'Acts': 'Acts', 'Rom': 'Romans',
    '1Cor': '1 Corinthians', '2Cor': '2 Corinthians',
    'Gal': 'Galatians', 'Eph': 'Ephesians', 'Phil': 'Philippians', 'Col': 'Colossians',
    '1Thess': '1 Thessalonians', '2Thess': '2 Thessalonians',
    '1Tim': '1 Timothy', '2Tim': '2 Timothy',
    'Titus': 'Titus', 'Phlm': 'Philemon', 'Heb': 'Hebrews', 'Jas': 'James',
    '1Pet': '1 Peter', '2Pet': '2 Peter',
    '1John': '1 John', '2John': '2 John', '3John': '3 John',
    'Jude': 'Jude', 'Rev': 'Revelation',
}


def _parse_xref_verse(ref_str):
    """Parse a cross-reference verse string like 'Ps.37.11' or 'Rom.1.19-Rom.1.20'.
    
    Returns: list of (book_abbr, chapter, verse) tuples.
    For ranges, returns both endpoints.
    """
    results = []
    # Handle ranges: split on '-' but be careful not to split negative numbers
    parts = ref_str.split('-')
    for part in parts:
        m = re.match(r'(\d*[A-Za-z]+)\.(\d+)\.(\d+)', part)
        if m:
            book_abbr = m.group(1)
            chapter = int(m.group(2))
            verse = int(m.group(3))
            results.append((book_abbr, chapter, verse))
    return results


class CrossReferenceIndex:
    """Loads and queries the openbible.info cross-reference dataset."""

    def __init__(self, xref_path=None, bible_db_path=None):
        self.xref_path = Path(xref_path) if xref_path else XREF_PATH
        self.bible_db_path = Path(bible_db_path) if bible_db_path else BIBLE_DB_PATH
        self._xref_data = None
        self._bible_db = None

    def _load_xref(self):
        """Load the cross-references file into a dict."""
        if self._xref_data is not None:
            return self._xref_data

        if not self.xref_path.exists():
            self._xref_data = {}
            return self._xref_data

        self._xref_data = {}
        with open(self.xref_path, 'r') as f:
            next(f)  # skip header line
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 3:
                    continue
                from_verse = parts[0]
                to_verse = parts[1]
                try:
                    votes = int(parts[2])
                except ValueError:
                    continue

                if from_verse not in self._xref_data:
                    self._xref_data[from_verse] = []
                self._xref_data[from_verse].append({
                    'to': to_verse,
                    'votes': votes,
                })

        # Sort each entry by votes descending
        for key in self._xref_data:
            self._xref_data[key].sort(key=lambda x: x['votes'], reverse=True)

        return self._xref_data

    def _get_bible_db(self):
        """Get SQLite connection to bible-db.sqlite."""
        if self._bible_db is not None:
            return self._bible_db
        if not self.bible_db_path.exists():
            return None
        self._bible_db = sqlite3.connect(str(self.bible_db_path))
        self._bible_db.row_factory = sqlite3.Row
        return self._bible_db

    def _book_to_xref_key(self, book_name):
        """Convert a human-readable book name to openbible abbreviation."""
        # Map common names to xref abbreviations
        name_map = {
            'matthew': 'Matt', 'mark': 'Mark', 'luke': 'Luke', 'john': 'John',
            'romans': 'Rom', 'acts': 'Acts',
            '1cor': '1Cor', '2cor': '2Cor',
            'galatians': 'Gal', 'ephesians': 'Eph', 'philippians': 'Phil',
            'colossians': 'Col',
            '1thess': '1Thess', '2thess': '2Thess',
            '1timothy': '1Tim', '2timothy': '2Tim',
            'titus': 'Titus', 'philemon': 'Phlm', 'hebrews': 'Heb', 'jasus': 'Jas',
            '1peter': '1Pet', '2peter': '2Pet',
            '1john': '1John', '2john': '2John', '3john': '3John',
            'jude': 'Jude', 'revelation': 'Rev',
            'genesis': 'Gen', 'exodus': 'Exod', 'leviticus': 'Lev',
            'numbers': 'Num', 'deuteronomy': 'Deut',
            'joshua': 'Josh', 'judges': 'Judg', 'ruth': 'Ruth',
            '1samuel': '1Sam', '2samuel': '2Sam',
            '1kings': '1Kgs', '2kings': '2Kgs',
            '1chronicles': '1Chr', '2chronicles': '2Chr',
            'ezra': 'Ezra', 'nehemiah': 'Neh', 'esther': 'Esth', 'job': 'Job',
            'psalms': 'Ps', 'psalm': 'Ps', 'proverbs': 'Prov',
            'ecclesiastic': 'Eccl', 'song': 'Song',
            'isaiah': 'Isa', 'jeremiah': 'Jer', 'lamentations': 'Lam',
            'ezechiel': 'Ezek', 'daniel': 'Dan', 'hosea': 'Hos', 'joel': 'Joel',
            'amos': 'Amos', 'obadiah': 'Obad', 'jonah': 'Jonah', 'micah': 'Mic',
            'nahum': 'Nah', 'habakkuk': 'Hab', 'zephaniah': 'Zeph',
            'haggai': 'Hag', 'zechariah': 'Zech', 'malachi': 'Mal',
        }
        return name_map.get(book_name.lower(), book_name)

    def _xref_key(self, book_abbr, chapter, verse):
        """Build the openbible cross-reference key."""
        return f"{book_abbr}.{chapter}.{verse}"

    def lookup(self, book, chapter, verse, include_hebrew=True, min_votes=1):
        """Look up cross-references for a Bible verse.

        Args:
            book: Human-readable book name (e.g., "Matthew", "Psalm")
            chapter: Chapter number
            verse: Verse number
            include_hebrew: If True, enrich OT sources with Hebrew word analysis
            min_votes: Minimum vote count to include (default 1 = all)

        Returns:
            dict: {
                'query': {'book': ..., 'chapter': ..., 'verse': ...},
                'cross_references': [
                    {
                        'book_abbr': 'Ps',
                        'book_name': 'Psalm',
                        'chapter': 37,
                        'verse': 11,
                        'votes': 105,
                        'testament': 'OT',
                        'kjv_text': '...',
                        'esv_text': '...',
                        'hebrew_text': '...',
                        'hebrew_words': [...],  # word-level Strong's analysis
                    },
                    ...
                ]
            }
        """
        xref_data = self._load_xref()
        book_abbr = self._book_to_xref_key(book)
        key = self._xref_key(book_abbr, chapter, verse)

        raw_refs = xref_data.get(key, [])
        if not raw_refs:
            return {
                'query': {'book': book, 'chapter': chapter, 'verse': verse},
                'cross_references': []
            }

        results = []
        for ref in raw_refs:
            if ref['votes'] < min_votes:
                continue

            parsed = _parse_xref_verse(ref['to'])
            if not parsed:
                continue

            # Use the first parsed verse (ranges: just take first)
            to_book_abbr, to_ch, to_v = parsed[0]
            db_book_id = XREF_BOOK_TO_DB.get(to_book_abbr)
            if db_book_id is None:
                continue

            entry = {
                'book_abbr': to_book_abbr,
                'book_name': BOOK_DISPLAY_NAMES.get(to_book_abbr, to_book_abbr),
                'chapter': to_ch,
                'verse': to_v,
                'votes': ref['votes'],
                'db_book_id': db_book_id,
                'testament': 'OT' if db_book_id <= 39 else 'NT',
            }

            # Fetch verse text from bible-db
            conn = self._get_bible_db()
            if conn:
                # KJV text
                cursor = conn.execute(
                    'SELECT text FROM verses WHERE book=? AND chapter=? AND verse=? AND source=?',
                    (db_book_id, to_ch, to_v, 'kjv')
                )
                row = cursor.fetchone()
                entry['kjv_text'] = row['text'] if row else None

                # Hebrew (wlc) text
                cursor = conn.execute(
                    'SELECT text FROM verses WHERE book=? AND chapter=? AND verse=? AND source=?',
                    (db_book_id, to_ch, to_v, 'wlc')
                )
                row = cursor.fetchone()
                entry['hebrew_text'] = row['text'] if row else None

                # Hebrew word-level analysis with Strong's
                if include_hebrew and entry['testament'] == 'OT':
                    entry['hebrew_words'] = self._fetch_hebrew_words(db_book_id, to_ch, to_v)
                else:
                    entry['hebrew_words'] = []

            results.append(entry)

        return {
            'query': {'book': book, 'chapter': chapter, 'verse': verse},
            'cross_references': results
        }

    def _fetch_hebrew_words(self, db_book_id, chapter, verse):
        """Fetch Hebrew word-level analysis with Strong's numbers and definitions."""
        conn = self._get_bible_db()
        if not conn:
            return []

        cursor = conn.execute('''
            SELECT w.id, w.w, w.surface, w.morph, ws.strong
            FROM words w
            LEFT JOIN word_strong ws ON ws.word_id = w.id
            WHERE w.book=? AND w.chapter=? AND w.verse=? AND w.source='wlc'
            ORDER BY w.w
        ''', (db_book_id, chapter, verse))

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

    def format_cross_refs_markdown(self, xref_result, max_refs=15, min_votes=5):
        """Format cross-reference results as a markdown section.

        Args:
            xref_result: Output from lookup()
            max_refs: Maximum number of references to include
            min_votes: Minimum votes to include (filters noise)

        Returns: Markdown string
        """
        refs = xref_result['cross_references']
        if not refs:
            return ""

        # Filter by min_votes and limit
        refs = [r for r in refs if r['votes'] >= min_votes][:max_refs]

        if not refs:
            return ""

        q = xref_result['query']
        lines = []
        lines.append("## 📜 Cross-Reference Analysis (Psalm/OT Sources)")
        lines.append("")
        lines.append(f"**Source**: openbible.info cross-reference dataset (~340k references, CC-BY)")
        lines.append(f"**Query**: {q['book']} {q['chapter']}:{q['verse']}")
        lines.append(f"**References found**: {len(xref_result['cross_references'])} (showing top {len(refs)} with ≥{min_votes} votes)")
        lines.append("")

        # Separate OT and NT
        ot_refs = [r for r in refs if r['testament'] == 'OT']
        nt_refs = [r for r in refs if r['testament'] == 'NT']

        if ot_refs:
            lines.append("### Old Testament Sources (Hebrew word analysis)")
            lines.append("")
            for ref in ot_refs:
                lines.append(self._format_single_ref(ref))
                lines.append("")

        if nt_refs:
            lines.append("### New Testament Echoes")
            lines.append("")
            for ref in nt_refs:
                lines.append(self._format_single_ref(ref))
                lines.append("")

        return "\n".join(lines)

    def _format_single_ref(self, ref):
        """Format a single cross-reference as markdown."""
        lines = []
        header = f"#### {ref['book_name']} {ref['chapter']}:{ref['verse']} (votes: {ref['votes']})"
        lines.append(header)
        lines.append("")

        if ref.get('kjv_text'):
            lines.append(f"**KJV**: {ref['kjv_text']}")
        if ref.get('hebrew_text'):
            lines.append(f"**Hebrew**: {ref['hebrew_text']}")
        lines.append("")

        # Hebrew word analysis table
        if ref.get('hebrew_words'):
            lines.append("| Word | Strong's | Transliteration | Definition | Categories |")
            lines.append("|------|----------|-----------------|------------|------------|")
            for w in ref['hebrew_words']:
                strongs = w.get('strong', '')
                sd = w.get('strongs_data', {})
                translit = sd.get('translit', '')
                # Truncate definition for table readability
                definition = sd.get('strongs_def', '').strip()
                if len(definition) > 120:
                    definition = definition[:117] + '...'
                kjv_def = sd.get('kjv_def', '').strip()
                cats = ', '.join(
                    c['category'] for c in w.get('categories', [])
                    if c.get('is_primary')
                )

                # Use kjv_def if no strongs_def
                display_def = definition or kjv_def or ''
                surface = w.get('surface', '')
                lines.append(f"| {surface} | {strongs} | {translit} | {display_def} | {cats} |")

            lines.append("")

            # Derivation chains for key words
            for w in ref['hebrew_words']:
                sd = w.get('strongs_data', {})
                derivation = sd.get('derivation', '').strip()
                strongs_def = sd.get('strongs_def', '').strip()
                if derivation and len(derivation) > 10:
                    strongs = w.get('strong', '')
                    lines.append(f"- **{strongs}** ({sd.get('translit', '')}): {strongs_def}")
                    lines.append(f"  - *Derivation*: {derivation}")

        return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Look up Bible cross-references")
    parser.add_argument("book", help="Book name (e.g., Matthew, Psalm, Isaiah)")
    parser.add_argument("passage", help="Passage (e.g., 5:5)")
    parser.add_argument("--min-votes", type=int, default=5,
                        help="Minimum vote count (default 5)")
    parser.add_argument("--max-refs", type=int, default=15,
                        help="Maximum references to show (default 15)")
    parser.add_argument("--no-hebrew", action="store_true",
                        help="Skip Hebrew word analysis")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of markdown")

    args = parser.parse_args()

    # Parse passage
    if ":" in args.passage:
        ch, v = args.passage.split(":")
        chapter, verse = int(ch), int(v)
    else:
        print("Passage must be in format chapter:verse (e.g., 5:5)")
        sys.exit(1)

    xref = CrossReferenceIndex()
    result = xref.lookup(args.book, chapter, verse,
                          include_hebrew=not args.no_hebrew,
                          min_votes=1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        md = xref.format_cross_refs_markdown(result, max_refs=args.max_refs,
                                              min_votes=args.min_votes)
        if md:
            print(md)
        else:
            print(f"No cross-references found for {args.book} {chapter}:{verse}")
