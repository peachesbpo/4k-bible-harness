"""retrieve.py — Verse retrieval layer.

Wraps the local data sources into a clean VerseBundle dataclass. Uses the
auto-generated book_index.json for canonical book lookup. Uses the on-disk
cache for parsed JSON.
"""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from . import cache
from .text_purity import verify_greek, PurityReport
from .greek_text import clean_sblgnt
from .hebrew_text import verify_hebrew, decode_morph, HebrewPurityReport

# Cross-reference index (lazy-loaded)
_xref_index = None


def _get_xref_index():
    global _xref_index
    if _xref_index is None:
        try:
            # cross_references.py lives at project root
            import sys
            sys.path.insert(0, str(SCRIPT_DIR))
            from cross_references import CrossReferenceIndex
            _xref_index = CrossReferenceIndex()
        except Exception:
            _xref_index = False  # disable gracefully if unavailable
    return _xref_index if _xref_index is not False else None

SCRIPT_DIR = Path(__file__).resolve().parent.parent
BOOK_INDEX_PATH = Path(__file__).resolve().parent / "book_index.json"

# Data source roots
GREEK_ROOT = SCRIPT_DIR / "bible-api-data" / "bibles" / "grc-srgnt" / "books"
WEB_ROOT = SCRIPT_DIR / "bible-api-web" / "bibles" / "en-web" / "books"
KJV_ROOT = SCRIPT_DIR / "bible-api-esv" / "bibles" / "en-kjv" / "books"
ASV_ROOT = SCRIPT_DIR / "bible-api-esv" / "bibles" / "en-asv" / "books"
STRONGS_DIR = SCRIPT_DIR / "strongs-data"
STRONGS_DICT_PATH = SCRIPT_DIR / "strongs-greek-dictionary.js"
LSJ_PATH = SCRIPT_DIR / "lsj-greek-lexicon.json"
BIBLE_DB_PATH = SCRIPT_DIR / "bible-db.sqlite"

_book_index: dict | None = None


def load_book_index() -> dict:
    global _book_index
    if _book_index is None:
        _book_index = json.loads(BOOK_INDEX_PATH.read_text("utf-8"))
    return _book_index


def _find_book(canonical: str) -> dict | None:
    """Find a book entry by canonical name (case-insensitive). Searches both OT and NT."""
    idx = load_book_index()
    canonical_lower = canonical.lower()
    for entry in idx.get("ot_books", []) + idx["nt_books"]:
        if entry["canonical"].lower() == canonical_lower:
            return entry
    return None


def canonical_books() -> list[str]:
    return [e["canonical"] for e in load_book_index().get("ot_books", [])] + \
           [e["canonical"] for e in load_book_index()["nt_books"]]


def resolve_book(name: str) -> str:
    """Resolve a user-provided book name to canonical. Raises ValueError if unknown."""
    # Direct match
    entry = _find_book(name)
    if entry:
        return entry["canonical"]
    # Common aliases (NT + OT)
    aliases = {
        # NT
        "1cor": "1Corinthians", "1 cor": "1Corinthians", "1corinthians": "1Corinthians",
        "2cor": "2Corinthians", "2 cor": "2Corinthians", "2corinthians": "2Corinthians",
        "1tim": "1Timothy", "1 tim": "1Timothy", "1timothy": "1Timothy",
        "2tim": "2Timothy", "2 tim": "2Timothy", "2timothy": "2Timothy",
        "1pet": "1Peter", "1 pet": "1Peter", "1peter": "1Peter",
        "2pet": "2Peter", "2 pet": "2Peter", "2peter": "2Peter",
        "1john": "1John", "1 john": "1John",
        "2john": "2John", "2 john": "2John",
        "3john": "3John", "3 john": "3John",
        "rev": "Revelation", "revelation": "Revelation",
        "phil": "Philippians", "php": "Philippians",
        "eph": "Ephesians",
        "rom": "Romans",
        "matt": "Matthew", "mt": "Matthew",
        "mk": "Mark",
        "lk": "Luke",
        "jn": "John",
        # OT
        "gen": "Genesis", "ge": "Genesis", "gn": "Genesis",
        "exo": "Exodus", "ex": "Exodus",
        "lev": "Leviticus", "lv": "Leviticus",
        "num": "Numbers",
        "deu": "Deuteronomy", "dt": "Deuteronomy", "deut": "Deuteronomy",
        "jos": "Joshua", "josh": "Joshua",
        "jdg": "Judges", "judg": "Judges",
        "rut": "Ruth", "ru": "Ruth",
        "1sam": "1Samuel", "1 sam": "1Samuel", "1samuel": "1Samuel", "i sam": "1Samuel",
        "2sam": "2Samuel", "2 sam": "2Samuel", "2samuel": "2Samuel", "ii sam": "2Samuel",
        "1kgs": "1Kings", "1ki": "1Kings", "1kings": "1Kings", "i kgs": "1Kings",
        "2kgs": "2Kings", "2ki": "2Kings", "2kings": "2Kings", "ii kgs": "2Kings",
        "1chr": "1Chronicles", "1ch": "1Chronicles", "1chronicles": "1Chronicles",
        "2chr": "2Chronicles", "2ch": "2Chronicles", "2chronicles": "2Chronicles",
        "ezr": "Ezra",
        "neh": "Nehemiah", "ne": "Nehemiah",
        "est": "Esther",
        "job": "Job",
        "psa": "Psalms", "ps": "Psalms", "psalm": "Psalms", "psalms": "Psalms",
        "pro": "Proverbs", "prv": "Proverbs", "prov": "Proverbs",
        "ecc": "Ecclesiastes", "eccl": "Ecclesiastes", "qoh": "Ecclesiastes",
        "sng": "SongOfSolomon", "song": "SongOfSolomon", "sos": "SongOfSolomon",
        "isa": "Isaiah",
        "jer": "Jeremiah",
        "lam": "Lamentations",
        "ezk": "Ezekiel", "ezek": "Ezekiel",
        "dan": "Daniel",
        "hos": "Hosea", "hoso": "Hosea",
        "jol": "Joel", "joel": "Joel",
        "amo": "Amos",
        "oba": "Obadiah", "obad": "Obadiah",
        "jon": "Jonah", "jnh": "Jonah",
        "mic": "Micah",
        "nam": "Nahum",
        "hab": "Habakkuk",
        "zep": "Zephaniah", "zeph": "Zephaniah",
        "hag": "Haggai",
        "zec": "Zechariah", "zech": "Zechariah",
        "mal": "Malachi",
    }
    canon = aliases.get(name.lower())
    if canon:
        entry = _find_book(canon)
        if entry:
            return entry["canonical"]
    raise ValueError(f"Unknown book: {name!r}. Known: {', '.join(canonical_books())}")


# ── VerseBundle dataclass ──────────────────────────────────────────────────────


@dataclass
class StrongWord:
    i: int | None
    text: str           # English gloss (interlinear)
    word: str           # Greek surface form
    number: str         # Strong's number, e.g. "g976"
    strongs_dict: dict | None = None
    lsj: dict | None = None
    bible_db: dict | None = None
    categories: list | None = None


@dataclass
class HebrewWord:
    """One word of WLC Hebrew text with morphology + BDB lexicon enrichment."""
    surface: str                  # Hebrew surface form (with cantillation/vowels)
    translit: str                 # BDB transliteration, e.g. "rêʼshîyth"
    lemma: str                     # Hebrew lemma, e.g. "רֵאשִׁית"
    morph_raw: str                 # Raw WLC morph code, e.g. "HR/Ncfsa"
    morph_readable: str            # Decoded morph, e.g. "Preposition / Noun common feminine singular absolute"
    strongs: str                   # Strong's number with H prefix, e.g. "H7225"
    strongs_def: str               # BDB definition
    derivation: str               # BDB derivation
    kjv_def: str                  # KJV gloss
    categories: list[dict] | None = None  # Semantic categories from strong_category
    w: int | None = None          # Word order in the verse (1-based)


@dataclass
class VerseBundle:
    """All retrieved data for one verse, ready to hand to a subagent."""
    book: str           # canonical name
    chapter: int
    verse: int
    greek_text: str | None
    greek_pure: bool
    greek_purity: dict
    web_text: str | None
    kjv_text: str | None
    strongs: list[dict] = field(default_factory=list)
    strongs_count: int = 0
    cross_refs: list | None = None
    spoken_jesus_material: bool = False  # True for Gospels+Acts (Aramaic-gap rule applies)
    source_paths: dict = field(default_factory=dict)
    # OT fields (populated for OT verses; None/empty for NT)
    hebrew_text: str | None = None
    asv_text: str | None = None
    hebrew_pure: bool = False
    hebrew_purity: dict = field(default_factory=lambda: {"is_hebrew": False, "reason": "n/a"})
    hebrew_words: list[HebrewWord] = field(default_factory=list)
    original_language: str = "greek"   # "greek" | "hebrew" (Aramaic deferred)
    testament: str = "NT"               # "OT" | "NT"

    def to_prompt_dict(self) -> dict:
        """Slim dict for the subagent prompt — excludes internal fields."""
        d = asdict(self)
        d.pop("source_paths", None)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_prompt_dict(), ensure_ascii=False, indent=2)


# ── Retrieval ───────────────────────────────────────────────────────────────────


def _greek_verse_path(book_entry: dict, chapter: int, verse: int) -> Path:
    return GREEK_ROOT / book_entry["greek_dir"] / "chapters" / str(chapter) / "verses" / f"{verse}.json"


def _web_verse_path(book_entry: dict, chapter: int, verse: int) -> Path:
    return WEB_ROOT / book_entry["web_dir"] / "chapters" / str(chapter) / "verses" / f"{verse}.json"


def _kjv_verse_path(book_entry: dict, chapter: int, verse: int) -> Path:
    if not book_entry.get("web_dir"):
        return Path("/nonexistent")
    return KJV_ROOT / book_entry["web_dir"] / "chapters" / str(chapter) / "verses" / f"{verse}.json"


def _asv_verse_path(book_entry: dict, chapter: int, verse: int) -> Path:
    """en-asv book path. OT books use asv_dir; NT books also have asv_dir (en-asv is full Bible)."""
    asv_dir = book_entry.get("asv_dir") or book_entry.get("web_dir")
    if not asv_dir:
        return Path("/nonexistent")
    return ASV_ROOT / asv_dir / "chapters" / str(chapter) / "verses" / f"{verse}.json"


def _read_verse_file(version: str, book: str, book_entry: dict, chapter: int, verse: int,
                    path: Path) -> str | None:
    """Read a verse JSON file, using the cache."""
    if not path.exists():
        return None
    cached, hit = cache.get_cached_verse(version, book, chapter, verse, path)
    if hit and cached is not None:
        return cached.get("text")
    try:
        data = json.loads(path.read_text("utf-8"))
        text = data.get("text", "")
        if version == "greek":
            text = clean_sblgnt(text)
        text = text.split("\x00")[0].strip()
        cache.put_cached_verse(version, book, chapter, verse, path, {"text": text})
        return text
    except (json.JSONDecodeError, IOError):
        return None


def _read_asv_verse(book: str, book_entry: dict, chapter: int, verse: int) -> str | None:
    """Read an en-asv verse (OT English baseline). Uses the cache."""
    path = _asv_verse_path(book_entry, chapter, verse)
    return _read_verse_file("asv", book, book_entry, chapter, verse, path)


def _fetch_hebrew_words(book_entry: dict, chapter: int, verse: int) -> list[HebrewWord]:
    """Fetch WLC Hebrew words for an OT verse from bible-db.sqlite.

    Joins words (WLC surface + morph) → word_strong (H####) → strongs (BDB lexicon)
    → strong_category (semantic categories). Returns words in verse order.
    """
    conn = _get_bible_db()
    if conn is None:
        return []
    db_book = book_entry.get("db_book_number")
    if db_book is None:
        return []
    try:
        rows = conn.execute(
            "SELECT w.id, w.w, w.surface, w.morph, ws.strong "
            "FROM words w "
            "LEFT JOIN word_strong ws ON ws.word_id = w.id "
            "WHERE w.source='wlc' AND w.book=? AND w.chapter=? AND w.verse=? "
            "ORDER BY w.w",
            (db_book, chapter, verse),
        ).fetchall()
    except sqlite3.Error:
        return []

    words: list[HebrewWord] = []
    for row in rows:
        surface = row["surface"] or ""
        morph_raw = row["morph"] or ""
        strong_id = row["strong"] or ""
        morph_readable = decode_morph(morph_raw)

        # Enrich from strongs table (BDB-class lexicon)
        translit = ""
        lemma = ""
        strongs_def = ""
        derivation = ""
        kjv_def = ""
        categories: list[dict] | None = None

        if strong_id:
            try:
                srow = conn.execute(
                    "SELECT lemma, translit, pron, derivation, strongs_def, kjv_def "
                    "FROM strongs WHERE strong=?",
                    (strong_id,),
                ).fetchone()
                if srow:
                    lemma = srow["lemma"] or ""
                    translit = srow["translit"] or ""
                    derivation = srow["derivation"] or ""
                    strongs_def = (srow["strongs_def"] or "").strip()
                    kjv_def = srow["kjv_def"] or ""
                cats = conn.execute(
                    "SELECT category, is_primary FROM strong_category WHERE strong=?",
                    (strong_id,),
                ).fetchall()
                if cats:
                    categories = [
                        {"category": r["category"], "is_primary": bool(r["is_primary"])}
                        for r in cats
                    ]
            except sqlite3.Error:
                pass

        words.append(HebrewWord(
            surface=surface,
            translit=translit,
            lemma=lemma,
            morph_raw=morph_raw,
            morph_readable=morph_readable,
            strongs=strong_id,
            strongs_def=strongs_def,
            derivation=derivation,
            kjv_def=kjv_def,
            categories=categories,
            w=row["w"],
        ))
    return words


def _normalize_greek(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = s.replace("ς", "σ")
    s = s.lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    return s


_strongs_dict_cache: dict | None = None


def _load_strongs_dict() -> dict:
    global _strongs_dict_cache
    if _strongs_dict_cache is not None:
        return _strongs_dict_cache
    if not STRONGS_DICT_PATH.exists():
        _strongs_dict_cache = {}
        return _strongs_dict_cache
    content = STRONGS_DICT_PATH.read_text("utf-8")
    start = content.index("{")
    end = content.rindex("}") + 1
    _strongs_dict_cache = json.loads(content[start:end])
    return _strongs_dict_cache


_lsj_cache: dict | None = None
_lsj_index: dict | None = None


def _load_lsj() -> tuple[dict, dict]:
    global _lsj_cache, _lsj_index
    if _lsj_cache is not None:
        return _lsj_cache, _lsj_index
    if not LSJ_PATH.exists():
        _lsj_cache = {}
        _lsj_index = {}
        return _lsj_cache, _lsj_index
    _lsj_cache = json.loads(LSJ_PATH.read_text("utf-8"))
    _lsj_index = {}
    for key in _lsj_cache:
        norm = _normalize_greek(key)
        if norm not in _lsj_index:
            _lsj_index[norm] = key
        for g in _lsj_cache[key].get("g", []):
            gn = _normalize_greek(g)
            if gn not in _lsj_index:
                _lsj_index[gn] = key
    return _lsj_cache, _lsj_index


_bible_db: sqlite3.Connection | None = None


def _get_bible_db() -> sqlite3.Connection | None:
    global _bible_db
    if _bible_db is not None:
        return _bible_db
    if not BIBLE_DB_PATH.exists():
        return None
    _bible_db = sqlite3.connect(str(BIBLE_DB_PATH))
    _bible_db.row_factory = sqlite3.Row
    return _bible_db


def enrich_word(word: dict) -> dict:
    """Enrich a Strong's word with dictionary + LSJ + categories."""
    strong_id = word.get("number", "") or word.get("strong", "")
    if not strong_id:
        return word
    dict_id = strong_id.upper() if strong_id.upper().startswith("G") else f"G{strong_id}"
    sd = _load_strongs_dict().get(dict_id)
    if sd:
        word["strongs_dict"] = {
            "lemma": sd.get("lemma", ""),
            "strongs_def": sd.get("strongs_def", "").strip(),
            "kjv_def": sd.get("kjv_def", ""),
            "derivation": sd.get("derivation", ""),
            "translit": sd.get("translit", ""),
        }
        lemma = sd.get("lemma", "")
        if lemma:
            lsj_data, lsj_index = _load_lsj()
            matched = lsj_index.get(_normalize_greek(lemma))
            if matched:
                import re
                raw = lsj_data[matched].get("d", "")
                clean = re.sub(r"<[^>]+>", "", raw).strip()
                word["lsj"] = {"key": matched, "definition": clean}
    conn = _get_bible_db()
    if conn:
        try:
            row = conn.execute(
                "SELECT lemma, translit, pron, derivation, strongs_def, kjv_def "
                "FROM strongs WHERE strong=?",
                (dict_id,),
            ).fetchone()
            if row:
                word["bible_db"] = dict(row)
            cats = conn.execute(
                "SELECT category, is_primary FROM strong_category WHERE strong=?",
                (dict_id,),
            ).fetchall()
            if cats:
                word["categories"] = [
                    {"category": r["category"], "is_primary": bool(r["is_primary"])}
                    for r in cats
                ]
        except sqlite3.Error:
            pass
    return word


def fetch_strongs(book_entry: dict, chapter: int, verse: int, enrich: bool = True) -> list[dict]:
    strongs_file = STRONGS_DIR / book_entry["strongs_file"]
    if not strongs_file.exists():
        return []
    prefix = book_entry["strongs_prefix"]
    verse_id = f"{prefix}{chapter:03d}{verse:03d}"
    try:
        data = json.loads(strongs_file.read_text("utf-8"))
    except (json.JSONDecodeError, IOError):
        return []
    for item in data:
        if item.get("id") == verse_id:
            words = item.get("verse", [])
            if enrich:
                words = [enrich_word(w) for w in words]
            return words
    return []


def fetch_cross_refs(book: str, chapter: int, verse: int,
                     min_votes: int = 5, max_refs: int = 10,
                     include_hebrew: bool = True) -> list[dict]:
    """Fetch top-N cross-references for a verse, sorted by votes.

    Returns a slim list of dicts: {book_abbr, book_name, chapter, verse, votes,
    testament, kjv_text, hebrew_text, hebrew_words}. The hebrew_words carry
    Strong's data + semantic categories — the source-language analysis that
    supersedes the secondary occurrence.
    """
    idx = _get_xref_index()
    if idx is None:
        return []
    try:
        result = idx.lookup(book, chapter, verse,
                            include_hebrew=include_hebrew, min_votes=min_votes)
    except Exception:
        return []
    refs = result.get("cross_references", [])
    # Sort by votes desc, take top-N
    refs = sorted(refs, key=lambda r: r.get("votes", 0), reverse=True)[:max_refs]
    # Slim each entry to what the subagent needs
    slim = []
    for r in refs:
        entry = {
            "book_abbr": r.get("book_abbr"),
            "book_name": r.get("book_name"),
            "chapter": r.get("chapter"),
            "verse": r.get("verse"),
            "votes": r.get("votes"),
            "testament": r.get("testament"),
            "kjv_text": r.get("kjv_text"),
            "hebrew_text": r.get("hebrew_text"),
        }
        if include_hebrew and r.get("hebrew_words"):
            entry["hebrew_words"] = [
                {
                    "surface": w.get("surface"),
                    "strong": w.get("strong"),
                    "strongs_data": w.get("strongs_data"),
                    "categories": w.get("categories"),
                }
                for w in r["hebrew_words"]
            ]
        slim.append(entry)
    return slim


def fetch_verse(book: str, chapter: int, verse: int,
                include_strongs: bool = True,
                include_etymology: bool = True,
                include_kjv: bool = False,
                include_cross_refs: bool = True,
                cross_ref_min_votes: int = 5,
                cross_ref_max: int = 10) -> VerseBundle:
    """Retrieve a single verse as a VerseBundle."""
    canonical = resolve_book(book)
    book_entry = _find_book(canonical)
    if not book_entry:
        raise ValueError(f"Book not in index: {canonical}")

    testament = book_entry.get("testament", "NT")

    # Cross-references (both OT and NT verses can have them)
    cross_refs: list[dict] = []
    if include_cross_refs:
        cross_refs = fetch_cross_refs(canonical, chapter, verse,
                                       min_votes=cross_ref_min_votes,
                                       max_refs=cross_ref_max)

    if testament == "OT":
        return _fetch_verse_ot(canonical, book_entry, chapter, verse,
                               include_cross_refs=cross_refs,
                               include_kjv=include_kjv)

    # NT path (existing)
    greek_path = _greek_verse_path(book_entry, chapter, verse)
    web_path = _web_verse_path(book_entry, chapter, verse)
    kjv_path = _kjv_verse_path(book_entry, chapter, verse)

    greek_text = _read_verse_file("greek", canonical, book_entry, chapter, verse, greek_path)
    web_text = _read_verse_file("web", canonical, book_entry, chapter, verse, web_path)
    kjv_text = _read_verse_file("kjv", canonical, book_entry, chapter, verse, kjv_path) if include_kjv else None

    purity = verify_greek(greek_text) if greek_text else PurityReport(False, [], [], "no greek text")

    strongs: list[dict] = []
    if include_strongs and greek_text:
        strongs = fetch_strongs(book_entry, chapter, verse, enrich=include_etymology)

    return VerseBundle(
        book=canonical,
        chapter=chapter,
        verse=verse,
        greek_text=greek_text,
        greek_pure=purity.is_greek,
        greek_purity=purity.to_dict(),
        web_text=web_text,
        kjv_text=kjv_text,
        strongs=strongs,
        strongs_count=len(strongs),
        cross_refs=cross_refs,
        spoken_jesus_material=bool(book_entry.get("spoken_jesus_material", False)),
        original_language="greek",
        testament="NT",
        source_paths={
            "greek": str(greek_path.relative_to(SCRIPT_DIR)) if greek_path.exists() else None,
            "web": str(web_path.relative_to(SCRIPT_DIR)) if web_path.exists() else None,
        },
    )


def _fetch_verse_ot(canonical: str, book_entry: dict, chapter: int, verse: int,
                   include_cross_refs: list[dict],
                   include_kjv: bool) -> VerseBundle:
    """Retrieve an OT verse: WLC Hebrew + en-asv English + BDB enrichment."""
    hebrew_words = _fetch_hebrew_words(book_entry, chapter, verse)
    hebrew_text = " ".join(w.surface for w in hebrew_words) if hebrew_words else None

    purity = verify_hebrew(hebrew_text) if hebrew_text else HebrewPurityReport(False, [], "no hebrew text")

    asv_text = _read_asv_verse(canonical, book_entry, chapter, verse)

    kjv_text: str | None = None
    if include_kjv:
        kjv_path = _kjv_verse_path(book_entry, chapter, verse)
        kjv_text = _read_verse_file("kjv", canonical, book_entry, chapter, verse, kjv_path)

    asv_path = _asv_verse_path(book_entry, chapter, verse)
    return VerseBundle(
        book=canonical,
        chapter=chapter,
        verse=verse,
        greek_text=None,
        greek_pure=False,
        greek_purity={"is_greek": False, "reason": "OT verse (no Greek source)"},
        web_text=None,
        kjv_text=kjv_text,
        strongs=[],
        strongs_count=0,
        cross_refs=include_cross_refs,
        spoken_jesus_material=False,  # OT is never spoken-Jesus material
        hebrew_text=hebrew_text,
        asv_text=asv_text,
        hebrew_pure=purity.is_hebrew,
        hebrew_purity=purity.to_dict(),
        hebrew_words=hebrew_words,
        original_language="hebrew",
        testament="OT",
        source_paths={
            "asv": str(asv_path.relative_to(SCRIPT_DIR)) if asv_path.exists() else None,
        },
    )


def fetch_passage(book: str, chapter: int, verses: list[int], **kwargs) -> list[VerseBundle]:
    """Fetch a list of verses. kwargs passed through to fetch_verse."""
    return [fetch_verse(book, chapter, v, **kwargs) for v in verses]


def chapter_verse_count(book: str, chapter: int) -> int:
    """How many verses are in this chapter? Counts verse JSON files in the appropriate repo."""
    canonical = resolve_book(book)
    book_entry = _find_book(canonical)
    if not book_entry:
        return 0
    # NT: en-web repo. OT: en-asv repo (en-web is NT-only).
    if book_entry.get("testament") == "OT":
        dir_name = book_entry.get("asv_dir")
        if not dir_name:
            return 0
        verses_dir = ASV_ROOT / dir_name / "chapters" / str(chapter) / "verses"
    else:
        dir_name = book_entry.get("web_dir")
        if not dir_name:
            return 0
        verses_dir = WEB_ROOT / dir_name / "chapters" / str(chapter) / "verses"
    if not verses_dir.exists():
        return 0
    return len(list(verses_dir.glob("*.json")))


def book_chapter_count(book: str) -> int:
    """How many chapters in this book?"""
    canonical = resolve_book(book)
    book_entry = _find_book(canonical)
    if not book_entry:
        return 0
    if book_entry.get("testament") == "OT":
        dir_name = book_entry.get("asv_dir")
        if not dir_name:
            return 0
        chapters_dir = ASV_ROOT / dir_name / "chapters"
    else:
        dir_name = book_entry.get("web_dir")
        if not dir_name:
            return 0
        chapters_dir = WEB_ROOT / dir_name / "chapters"
    if not chapters_dir.exists():
        return 0
    return sum(1 for d in chapters_dir.iterdir() if d.is_dir())
