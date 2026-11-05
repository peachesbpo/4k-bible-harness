#!/usr/bin/env python3
"""
fetch_verse.py — Fetch Bible verse text from local data sources (no internet required).

Reads from local datasets:
  - Greek NT: bible-api-data/bibles/grc-srgnt/ (Solid Rock Greek NT, Scholar's Edition)
  - ESV English: bible-api-esv/bibles/en-asv/ (American Standard Version of 1901)
  - Strong's: strongs-data/ (interlinear_bibledata with word-level Strong's numbers)
  - Strong's Greek Dictionary: strongs-greek-dictionary.js (lemma, definitions, derivation)
  - LSJ Lexicon: lsj-greek-lexicon.json (Liddell-Scott-Jones classical Greek dictionary)
  - Bible DB: bible-db.sqlite (semantic categories, morphology)

Usage:
    python3 fetch_verse.py Matthew 23:13           # Fetch both Greek + ESV
    python3 fetch_verse.py Matthew 23:13-18        # Fetch a range
    python3 fetch_verse.py Matthew 23:13 --greek   # Greek only
    python3 fetch_verse.py Matthew 23:13 --esv     # ESV only
    python3 fetch_verse.py Matthew 23:13 --kjv     # KJV (if available locally)
    python3 fetch_verse.py Matthew 23:13 --strongs # Include Strong's concordance
    python3 fetch_verse.py Matthew 23:13 --etymology  # Strong's + all dictionaries
    python3 fetch_verse.py Matthew chapter 23      # Full chapter

Output: JSON to stdout
"""

import json
import sys
import os
import re
import argparse
import sqlite3
import unicodedata
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent

# Local data source paths
DATA_SOURCES = {
    "greek": {
        "path": SCRIPT_DIR / "bible-api-data" / "bibles" / "grc-srgnt",
        "description": "Solid Rock Greek New Testament, Scholar's Edition",
    },
    "esv": {
        "path": SCRIPT_DIR / "bible-api-esv" / "bibles" / "en-asv",
        "description": "American Standard Version of 1901",
    },
    "kjv": {
        "path": SCRIPT_DIR / "bible-api-esv" / "bibles" / "en-kjv",
        "description": "King James Version (if available locally)",
    },
}

STRONGS_PATH = SCRIPT_DIR / "strongs-data"

# Etymology data sources
STRONGS_DICT_PATH = SCRIPT_DIR / "strongs-greek-dictionary.js"
LSJ_PATH = SCRIPT_DIR / "lsj-greek-lexicon.json"
BIBLE_DB_PATH = SCRIPT_DIR / "bible-db.sqlite"

# Book name mappings (English → Greek script names in the repo)
# Greek-script repos use actual Greek Unicode characters
BOOK_NAMES = {
    "matthew":    {"en": "matthew",    "grc": "\u03bc\u03b1\u03c4\u03b8\u03b1\u03b9\u03bf\u03bd"},  # ματθαιον
    "mark":       {"en": "mark",       "grc": "\u03bc\u03b1\u03c1\u03ba\u03bf\u03bd"},              # μαρκον
    "luke":       {"en": "luke",       "grc": "\u03bb\u03bf\u03c5\u03ba\u03b1\u03bd"},              # λoukan
    "john":       {"en": "john",       "grc": "\u03b9\u03c9\u03b1\u03bd\u03bd\u03b7\u03bd"},          # iωavvev
    "romans":     {"en": "romans",     "grc": "\u03c1\u03c9\u03bc\u03b1\u03b9\u03bf\u03c5\u03c2"},  # rωμaioς
    "1cor":       {"en": "1cor",       "grc": "\u03ba\u03bf\u03c1\u03b9\u03bd\u03b8\u03b9\u03bf\u03c5\u03c2\u03b1"},
    "2cor":       {"en": "2cor",       "grc": "\u03ba\u03bf\u03c1\u03b9\u03bd\u03b8\u03b9\u03bf\u03c5\u03c2\u03b2"},
    # Add more as needed
}

# Strong's book name mappings (English → strongs-data filenames)
STRONGS_BOOK_NAMES = {
    "matthew": "matthew.json",
    "mark": "mark.json",
    "luke": "luke.json",
    "john": "john.json",
    "romans": "romans.json",
    "1cor": "i_corinthians.json",
    "2cor": "ii_corinthians.json",
    # Add more as needed
}

# Strong's book number prefix (BB in BBCCCVVV — 2-digit book, 3-digit chapter, 3-digit verse = 8 chars)
STRONGS_BOOK_NUMBERS = {
    "matthew": "40",
    "mark": "41",
    "luke": "42",
    "john": "43",
    "romans": "45",
    # Add more as needed
}


# ── Etymology Data Sources ────────────────────────────────────

# Lazy-loaded caches
_strongs_dict_cache = None
_lsj_cache = None
_lsj_index_cache = None
_bible_db_cache = None


def _normalize_greek(s):
    """Normalize Greek text for matching: NFC, final sigma → sigma, lowercase, strip diacritics."""
    s = unicodedata.normalize('NFC', s)
    s = s.replace('ς', 'σ')  # final sigma → regular sigma
    s = s.lower()
    # Strip combining marks (diacritics)
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))
    return s


def _load_strongs_dict():
    """Load the Strong's Greek dictionary (JS file with JSON payload)."""
    global _strongs_dict_cache
    if _strongs_dict_cache is not None:
        return _strongs_dict_cache
    if not STRONGS_DICT_PATH.exists():
        return None
    content = STRONGS_DICT_PATH.read_text('utf-8')
    start = content.index('{')
    end = content.rindex('}') + 1
    _strongs_dict_cache = json.loads(content[start:end])
    return _strongs_dict_cache


def _load_lsj():
    """Load the LSJ (Liddell-Scott-Jones) Greek-English lexicon."""
    global _lsj_cache, _lsj_index_cache
    if _lsj_cache is not None:
        return _lsj_cache, _lsj_index_cache
    if not LSJ_PATH.exists():
        return None, None
    with open(LSJ_PATH, 'r') as f:
        _lsj_cache = json.load(f)
    # Build normalized index for matching
    _lsj_index_cache = {}
    for key in _lsj_cache:
        norm = _normalize_greek(key)
        if norm not in _lsj_index_cache:
            _lsj_index_cache[norm] = key
        # Also index g (Greek) fields
        for g in _lsj_cache[key].get('g', []):
            gn = _normalize_greek(g)
            if gn not in _lsj_index_cache:
                _lsj_index_cache[gn] = key
    return _lsj_cache, _lsj_index_cache


def _get_bible_db():
    """Get a SQLite connection to bible-db.sqlite."""
    global _bible_db_cache
    if _bible_db_cache is not None:
        return _bible_db_cache
    if not BIBLE_DB_PATH.exists():
        return None
    _bible_db_cache = sqlite3.connect(str(BIBLE_DB_PATH))
    _bible_db_cache.row_factory = sqlite3.Row
    return _bible_db_cache


def _strip_html(text):
    """Strip HTML tags from LSJ definitions."""
    return re.sub(r'<[^>]+>', '', text).strip()


def _follow_lsj_crossref(definition, lsj_data, depth=0):
    """
    If an LSJ entry is a cross-reference (e.g., 'πρᾱΰς, v. πρᾶος.'),
    follow the reference to the main entry.
    """
    if depth > 3:  # Prevent infinite loops
        return None
    # Match patterns like 'X, v. Y.' or 'X, cf. Y.' or 'See Y.'
    match = re.match(r'^[^,]+,\s*(?:v\.|cf\.|see\s)\s*([^.,]+)[.]', definition, re.IGNORECASE)
    if not match:
        return None
    ref_key = match.group(1).strip()
    if ref_key in lsj_data:
        ref_def = _strip_html(lsj_data[ref_key].get('d', ''))
        # If the referenced entry is also a cross-ref, follow it
        deeper = _follow_lsj_crossref(ref_def, lsj_data, depth + 1)
        if deeper:
            return deeper
        return ref_key
    return None


def lookup_strongs_entry(strong_id):
    """
    Look up a Strong's number in the Greek dictionary.
    Returns: dict with lemma, strongs_def, kjv_def, derivation, translit
    """
    d = _load_strongs_dict()
    if not d:
        return None
    return d.get(strong_id)


def lookup_lsj(greek_lemma):
    """
    Look up a Greek lemma in the LSJ lexicon.
    Uses normalized matching to handle Unicode variant forms.
    Returns: dict with 'definition' (clean text), 'key' (matched LSJ key), 'is_crossref' (bool)
    """
    lsj_data, lsj_index = _load_lsj()
    if not lsj_data or not lsj_index:
        return None

    norm = _normalize_greek(greek_lemma)
    matched_key = lsj_index.get(norm)
    if not matched_key:
        return None

    entry = lsj_data[matched_key]
    raw_def = entry.get('d', '')
    clean_def = _strip_html(raw_def)

    # Check if this is a cross-reference
    ref_key = _follow_lsj_crossref(clean_def, lsj_data)
    if ref_key and ref_key != matched_key:
        ref_entry = lsj_data[ref_key]
        ref_def = _strip_html(ref_entry.get('d', ''))
        return {
            'key': ref_key,
            'definition': ref_def,
            'crossref_from': matched_key,
            'g': ref_entry.get('g', []),
            'l': ref_entry.get('l', []),
        }

    return {
        'key': matched_key,
        'definition': clean_def,
        'g': entry.get('g', []),
        'l': entry.get('l', []),
    }


def lookup_categories(strong_id):
    """
    Look up semantic categories for a Strong's number from bible-db.sqlite.
    Returns: list of {category, is_primary} dicts.
    """
    conn = _get_bible_db()
    if not conn:
        return []
    try:
        cursor = conn.execute(
            'SELECT category, is_primary FROM strong_category WHERE strong = ?',
            (strong_id,)
        )
        return [{'category': row['category'], 'is_primary': bool(row['is_primary'])}
                for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


def lookup_bible_db_strongs(strong_id):
    """
    Look up a Strong's number in bible-db.sqlite for full definition data.
    Returns: dict with lemma, translit, pron, derivation, strongs_def, kjv_def
    """
    conn = _get_bible_db()
    if not conn:
        return None
    try:
        cursor = conn.execute(
            'SELECT lemma, translit, pron, derivation, strongs_def, kjv_def FROM strongs WHERE strong = ?',
            (strong_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    except sqlite3.Error:
        pass
    return None


def enrich_strongs_word(word):
    """
    Enrich a Strong's concordance word entry with etymology data.

    Input: word dict from strongs-data (has 'strong', 'text', 'lemma', etc.)
    Output: same dict with added fields:
      - strongs_dict: {lemma, strongs_def, kjv_def, derivation} from Strong's Greek dict
      - lsj: {key, definition, g, l} from Liddell-Scott-Jones lexicon
      - categories: [{category, is_primary}] from bible-db semantic categories
      - bible_db: {lemma, translit, pron, derivation, strongs_def, kjv_def} from bible-db
    """
    # Strong's concordance uses 'number' field with lowercase 'g' prefix (e.g., 'g4239')
    strong_id = word.get('strong', '') or word.get('number', '')
    if not strong_id:
        return word

    # Ensure G prefix for dictionary lookups
    dict_id = strong_id.upper() if strong_id.upper().startswith('G') else f'G{strong_id}'

    # 1. Strong's Greek Dictionary
    sd_entry = lookup_strongs_entry(dict_id)
    if sd_entry:
        word['strongs_dict'] = {
            'lemma': sd_entry.get('lemma', ''),
            'strongs_def': sd_entry.get('strongs_def', '').strip(),
            'kjv_def': sd_entry.get('kjv_def', ''),
            'derivation': sd_entry.get('derivation', ''),
            'translit': sd_entry.get('translit', ''),
        }

    # 2. LSJ Classical Greek Dictionary
    lemma = sd_entry.get('lemma', '') if sd_entry else word.get('lemma', '')
    if lemma:
        lsj_entry = lookup_lsj(lemma)
        if lsj_entry:
            word['lsj'] = lsj_entry

    # 3. Bible DB semantic categories + full definition
    db_entry = lookup_bible_db_strongs(dict_id)
    if db_entry:
        word['bible_db'] = db_entry

    cats = lookup_categories(dict_id)
    if cats:
        word['categories'] = cats

    return word


# ── Local File Reading ────────────────────────────────────────

def _get_book_dir(version_key, book):
    """Get the directory path for a book in a given version."""
    source = DATA_SOURCES.get(version_key)
    if not source:
        return None
    
    base_path = source["path"] / "books"
    book_lower = book.lower()
    
    if not base_path.exists():
        return None
    
    # Try Latin name first (ESV)
    latin_dir = base_path / book_lower
    if latin_dir.exists():
        return latin_dir
    
    # Try Greek Unicode name
    if book_lower in BOOK_NAMES:
        grc_name = BOOK_NAMES[book_lower].get("grc", book_lower)
        grc_dir = base_path / grc_name
        if grc_dir.exists():
            return grc_dir
    
    # Try case-insensitive match
    for d in base_path.iterdir():
        if d.is_dir() and d.name.lower() == book_lower:
            return d
    
    return None


def fetch_verse_text(version_key, book, chapter, verse):
    """
    Fetch a single verse's text from local data files.
    
    Returns: (text, raw_json) or (None, None) if not found.
    """
    book_dir = _get_book_dir(version_key, book)
    if not book_dir:
        return None, None
    
    verse_file = book_dir / "chapters" / str(chapter) / "verses" / f"{verse}.json"
    if not verse_file.exists():
        return None, None
    
    try:
        raw = verse_file.read_text("utf-8")
        data = json.loads(raw)
        text = data.get("text", "")
        if version_key == "greek":
            from harness.greek_text import clean_sblgnt
            text = clean_sblgnt(text)
        text = text.split("\x00")[0].strip()
        return text, raw
    except (json.JSONDecodeError, KeyError, IOError):
        return None, None


def fetch_chapter(version_key, book, chapter):
    """Fetch all verses for a chapter from local data files."""
    book_dir = _get_book_dir(version_key, book)
    if not book_dir:
        return {}
    
    # Try chapter.json first (full chapter in one file)
    chapter_file = book_dir / "chapters" / f"{chapter}.json"
    if chapter_file.exists():
        try:
            raw = chapter_file.read_text("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict) and "data" in data:
                results = {}
                for item in data["data"]:
                    vnum = item.get("verse", "")
                    text = item.get("text", "")
                    if version_key == "greek":
                        from harness.greek_text import clean_sblgnt
                        text = clean_sblgnt(text)
                    text = text.split("\x00")[0].strip()
                    results[vnum] = text
                return results
            elif isinstance(data, dict):
                return data
        except (json.JSONDecodeError, IOError):
            pass
    
    # Fallback: read verse files individually
    verses_dir = book_dir / "chapters" / str(chapter) / "verses"
    if not verses_dir.exists():
        return {}
    
    results = {}
    for vf in sorted(verses_dir.glob("*.json")):
        try:
            raw = vf.read_text("utf-8")
            data = json.loads(raw)
            vnum = data.get("verse", vf.stem)
            text = data.get("text", "")
            if version_key == "greek":
                from harness.greek_text import clean_sblgnt
                text = clean_sblgnt(text)
            text = text.split("\x00")[0].strip()
            results[vnum] = text
        except (json.JSONDecodeError, IOError):
            pass
    
    return results


def fetch_strongs(book, chapter, verse):
    """
    Fetch Strong's concordance data for a specific verse from local data.
    
    Returns: list of word dicts, or None if not found.
    """
    book_lower = book.lower()
    strongs_file = STRONGS_BOOK_NAMES.get(book_lower)
    if not strongs_file:
        return None
    
    strongs_path = STRONGS_PATH / strongs_file
    if not strongs_path.exists():
        return None
    
    book_number = STRONGS_BOOK_NUMBERS.get(book_lower)
    if not book_number:
        return None
    
    # ID format: BBCCCVVV (2-digit book + 3-digit chapter + 3-digit verse = 8 chars)
    verse_id = f"{book_number}{chapter:03d}{verse:03d}"
    
    try:
        with open(strongs_path) as f:
            data = json.load(f)
        for item in data:
            if item.get("id") == verse_id:
                return item.get("verse", [])
    except (json.JSONDecodeError, IOError):
        pass
    
    return None


def fetch_strongs_chapter(book, chapter):
    """
    Fetch Strong's concordance data for an entire chapter.
    
    Returns: dict of {verse_num: [word_dicts]}
    """
    book_lower = book.lower()
    strongs_file = STRONGS_BOOK_NAMES.get(book_lower)
    if not strongs_file:
        return {}
    
    strongs_path = STRONGS_PATH / strongs_file
    if not strongs_path.exists():
        return {}
    
    book_number = STRONGS_BOOK_NUMBERS.get(book_lower)
    if not book_number:
        return {}
    
    # Match all verses in this chapter (BBCCC prefix = 5 chars)
    chapter_prefix = f"{book_number}{chapter:03d}"
    
    results = {}
    try:
        with open(strongs_path) as f:
            data = json.load(f)
        for item in data:
            item_id = item.get("id", "")
            if item_id.startswith(chapter_prefix) and len(item_id) == 8:
                vnum = str(int(item_id[5:]))  # Extract verse number (chars 5-7)
                results[vnum] = item.get("verse", [])
    except (json.JSONDecodeError, IOError):
        pass
    
    return results


# ── Public API ─────────────────────────────────────────────────

def fetch_passage(book, passage_str, versions=None, include_strongs=False, include_etymology=False):
    """
    Fetch one or more verses across specified Bible versions from local data.
    
    Args:
        book: "Matthew", "Mark", "Luke", "John", etc.
        passage_str: "23:13" or "23:13-18" or "23"
        versions: list of version keys ("greek", "esv", "kjv")
        include_strongs: if True, include Strong's concordance data
        include_etymology: if True, enrich Strong's data with all dictionary lookups
    
    Returns:
        dict: { "23:13": {"greek": "...", "esv": "...", "strongs": [...]}, ... }
    """
    if versions is None:
        versions = ["greek", "esv"]
    
    # Parse passage string
    if ":" in passage_str:
        chapter, verse_part = passage_str.split(":", 1)
        chapter = int(chapter)
        if "-" in verse_part:
            start, end = map(int, verse_part.split("-"))
            verses = list(range(start, end + 1))
        else:
            verses = [int(verse_part)]
    else:
        chapter = int(passage_str)
        verses = None  # Full chapter
    
    results = {}
    
    for vkey in versions:
        if vkey not in DATA_SOURCES:
            print(f"Unknown version: {vkey}", file=sys.stderr)
            continue
        
        source_path = DATA_SOURCES[vkey]["path"]
        if not source_path.exists():
            print(f"Local data not found for {vkey} at {source_path}", file=sys.stderr)
            continue
        
        if verses is None:
            # Full chapter
            chapter_data = fetch_chapter(vkey, book, chapter)
            for vnum, text in chapter_data.items():
                key = f"{chapter}:{vnum}"
                if key not in results:
                    results[key] = {}
                results[key][vkey] = text
        else:
            for verse in verses:
                text, _ = fetch_verse_text(vkey, book, chapter, verse)
                key = f"{chapter}:{verse}"
                if key not in results:
                    results[key] = {}
                results[key][vkey] = text
    
    # Add Strong's concordance if requested
    if include_strongs:
        if verses is None:
            strongs_data = fetch_strongs_chapter(book, chapter)
            for vnum, words in strongs_data.items():
                key = f"{chapter}:{vnum}"
                if key not in results:
                    results[key] = {}
                results[key]["strongs"] = words
        else:
            for verse in verses:
                words = fetch_strongs(book, chapter, verse)
                key = f"{chapter}:{verse}"
                if key not in results:
                    results[key] = {}
                results[key]["strongs"] = words
    
    # Enrich with etymology data if requested
    if include_etymology:
        for key in results:
            words = results[key].get("strongs", [])
            if words:
                results[key]["strongs"] = [enrich_strongs_word(w) for w in words]
    
    return results


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch Bible verse text from local data sources")
    parser.add_argument("book", help="Book name (e.g., Matthew, Mark, Luke, John)")
    parser.add_argument("passage", help="Passage (e.g., 23:13, 23:13-18, or 23 for full chapter)")
    parser.add_argument("--greek", action="store_true", help="Fetch Ancient Greek (grc-srgnt)")
    parser.add_argument("--esv", action="store_true", help="Fetch English Standard Version")
    parser.add_argument("--kjv", action="store_true", help="Fetch King James Version")
    parser.add_argument("--strongs", action="store_true", help="Include Strong's concordance data")
    parser.add_argument("--etymology", action="store_true", help="Enrich Strong's with LSJ + dictionary lookups")
    parser.add_argument("--all", action="store_true", help="Fetch all available versions")
    parser.add_argument("--raw", action="store_true", help="Include raw JSON in output")
    
    args = parser.parse_args()
    
    # Determine which versions to fetch
    versions = []
    if args.greek:
        versions.append("greek")
    if args.esv:
        versions.append("esv")
    if args.kjv:
        versions.append("kjv")
    if args.all:
        versions = list(DATA_SOURCES.keys())
    if not versions:
        versions = ["greek", "esv"]  # Default
    
    include_etymology = args.etymology
    if include_etymology:
        args.strongs = True  # Etymology requires Strong's data
    results = fetch_passage(args.book, args.passage, versions, include_strongs=args.strongs, include_etymology=include_etymology)
    
    if not results:
        print(json.dumps({"error": "No results found. Check that local data sources exist."}, indent=2))
        sys.exit(1)
    
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
