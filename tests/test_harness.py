"""Tests for the harness package."""
import json
import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_text_purity_clean_greek():
    from harness.text_purity import verify_greek
    r = verify_greek("ὑμεῖς δὲ μὴ κληθῆτε Ῥαββί·")
    assert r.is_greek, r.message
    assert not r.latin_letters


def test_text_purity_detects_bleed():
    from harness.text_purity import verify_greek
    r = verify_greek("πantes δὴ ὑmeis ἀdelfoί")
    assert not r.is_greek
    assert len(r.latin_letters) > 0


def test_text_purity_empty():
    from harness.text_purity import verify_greek
    r = verify_greek("")
    assert not r.is_greek


def test_repair_basic():
    from harness.text_purity import repair_greek, verify_greek
    fixed, applied = repair_greek("ἀdelfoί")
    assert verify_greek(fixed).is_greek, f"got {fixed!r}"
    assert fixed == "ἀδελφοί"


def test_repair_multipass():
    from harness.text_purity import repair_greek, verify_greek
    # θusiaσterion needs ~7 passes
    fixed, applied = repair_greek("θúsiaσterion")
    assert verify_greek(fixed).is_greek, f"got {fixed!r}"


def test_repair_no_greek_untouched():
    from harness.text_purity import repair_greek
    fixed, applied = repair_greek("hello world")
    assert applied == []
    assert fixed == "hello world"


def test_repair_skips_strongs_refs():
    from harness.text_purity import repair_greek
    # Strong's number references should not be "repaired"
    fixed, applied = repair_greek("Μακάριοι g3107")
    assert applied == []
    assert "g3107" in fixed


def test_greek_text_cleaner_paired_angle():
    """⸂ apparatus ⸂ chosen ⸃ → keep chosen (real SBLGNT format)."""
    from harness.greek_text import clean_sblgnt
    text = "πάντα 23:3 ⸂ ἐὰν RP WH NA ¦ ἂν TR TNT2 ⸂ἐὰν⸃ εἴπωσιν"
    out = clean_sblgnt(text)
    assert out == "πάντα ἐὰν εἴπωσιν", out


def test_greek_text_cleaner_paired_tortoise():
    """⸋ apparatus ⸋ chosen ⸌ → keep chosen."""
    from harness.greek_text import clean_sblgnt
    text = "Ῥαββί, 23:7 ⸋ Ῥαββί RP TR ¦ – TNT2 WH NA SBL ⸋ῥαββί·⸌"
    out = clean_sblgnt(text)
    assert out == "Ῥαββί, ῥαββί·", out


def test_greek_text_cleaner_paired_nail():
    """⸉ apparatus ⸉ chosen ⸊ → keep chosen."""
    from harness.greek_text import clean_sblgnt
    text = "⸉ τηρεῖτε RP TR ¦ ποιήσατε TNT2 WH ⸉τηρεῖτε·⸊ κατὰ"
    out = clean_sblgnt(text)
    assert out == "τηρεῖτε· κατὰ", out


def test_greek_text_cleaner_unit_number():
    """Apparatus unit number after 2nd OPEN is stripped from chosen."""
    from harness.greek_text import clean_sblgnt
    text = "⸂2 τῷ RP TR ¦ αὐτοὶ TNT2 WH ⸂2τῷ δὲ⸃ δακτύλῳ"
    out = clean_sblgnt(text)
    assert out == "τῷ δὲ δακτύλῳ", out


def test_greek_text_cleaner_unpaired_insertion():
    """⸆ apparatus ⸆ → remove (insertion-point, no chosen reading)."""
    from harness.greek_text import clean_sblgnt
    text = "Οὐαὶ ⸆ – RP f 35 TR ¦ δὲ TNT2 WH NA NIV SBL ⸆ ὑμῖν"
    out = clean_sblgnt(text)
    assert "RP" not in out
    assert "TNT2" not in out
    assert "ὑμῖν" in out
    assert "Οὐαὶ" in out


def test_greek_text_cleaner_multiple_blocks():
    """Multiple apparatus blocks of different types in one verse."""
    from harness.greek_text import clean_sblgnt
    text = ("ὑμεῖς 23:8 ⸂ καθηγητής RP TR ¦ διδάσκαλος TNT2 WH ⸂καθηγητής,⸃ "
            "23:8 ⸋ ὁ χριστός RP TR ¦ – TNT2 WH ⸋ὁ χριστός·⸌ πάντες")
    out = clean_sblgnt(text)
    assert out == "ὑμεῖς καθηγητής, ὁ χριστός· πάντες", out


def test_greek_text_cleaner_matthew_23_3():
    """Full Matthew 23:3 with three apparatus blocks."""
    from harness.greek_text import clean_sblgnt
    text = ("πάντα οὖν ὅσα 23:3 ⸂ ἐὰν RP f 35 WH NA NIV SBL  ¦ ἂν TR TNT2 ⸂ἐὰν⸃ "
            "εἴπωσιν ὑμῖν 23:3 ⸋ τηρεῖν RP f 35 TR  ¦ – TNT2 WH NA NIV SBL ⸋τηρεῖν,⸌ "
            "23:3 ⸉ τηρεῖτε καὶ ποιεῖτε RP f 35 TR  ¦ ποιήσατε καὶ τηρεῖτε TNT2 WH NA NIV SBL "
            "⸉τηρεῖτε καὶ ποιεῖτε·⸊ κατὰ δὲ τὰ ἔργα αὐτῶν μὴ ποιεῖτε, "
            "λέγουσιν γὰρ καὶ οὐ ποιοῦσιν.")
    out = clean_sblgnt(text)
    expected = ("πάντα οὖν ὅσα ἐὰν εἴπωσιν ὑμῖν τηρεῖν, "
                "τηρεῖτε καὶ ποιεῖτε· κατὰ δὲ τὰ ἔργα αὐτῶν "
                "μὴ ποιεῖτε, λέγουσιν γὰρ καὶ οὐ ποιοῦσιν.")
    assert out == expected, out


def test_book_index_loads():
    from harness.retrieve import canonical_books, load_book_index
    idx = load_book_index()
    assert "ot_books" in idx
    assert "nt_books" in idx
    assert len(idx["ot_books"]) == 39
    assert len(idx["nt_books"]) == 27
    books = canonical_books()
    assert len(books) == 66
    assert "Matthew" in books
    assert "Revelation" in books
    assert "Genesis" in books
    assert "Malachi" in books


def test_resolve_book_aliases():
    from harness.retrieve import resolve_book
    assert resolve_book("Matthew") == "Matthew"
    assert resolve_book("matt") == "Matthew"
    assert resolve_book("mt") == "Matthew"
    assert resolve_book("1cor") == "1Corinthians"
    assert resolve_book("rev") == "Revelation"


def test_fetch_verse_matthew_23_8():
    from harness.retrieve import fetch_verse
    b = fetch_verse("Matthew", 23, 8)
    assert b.book == "Matthew"
    assert b.chapter == 23
    assert b.verse == 8
    assert b.greek_text
    assert b.greek_pure, f"greek not pure: {b.greek_purity}"
    assert b.web_text
    assert b.strongs_count > 0


def test_fetch_verse_rev_1_1():
    from harness.retrieve import fetch_verse
    b = fetch_verse("Revelation", 1, 1)
    assert b.greek_pure, f"greek not pure: {b.greek_purity}"
    assert "Ἀποκάλυψις" in b.greek_text


def test_chapter_verse_count():
    from harness.retrieve import chapter_verse_count, book_chapter_count
    assert chapter_verse_count("Matthew", 23) == 39
    assert book_chapter_count("Matthew") == 28


def test_verse_bundle_json():
    from harness.retrieve import fetch_verse
    b = fetch_verse("John", 1, 1)
    j = b.to_json()
    d = json.loads(j)
    assert d["book"] == "John"
    assert d["chapter"] == 1
    assert d["greek_text"]


def test_schema_roundtrip():
    from harness.schema import VerseAnalysis, DiffEntry, KeyWord, Insight
    a = VerseAnalysis(
        book="Matthew", chapter=23, verse=8, reference="Matthew 23:8",
        greek_text="ὑμεῖς", web_text="But you", greek_pure=True,
        expanded_translation="But you",
        diffs=[DiffEntry("But you", "x", "y")],
        insights=[Insight("t", "d")],
        key_words=[KeyWord("ὑμεῖς", "hymeis", "G4771", "PPro-N2P", "you", "subject")],
    )
    d = a.to_dict()
    a2 = VerseAnalysis.from_dict(d)
    assert a2.book == "Matthew"
    assert len(a2.diffs) == 1
    assert a2.diffs[0].baseline_phrase == "But you"


def test_validators_pass_good_analysis():
    from harness.schema import VerseAnalysis, DiffEntry, KeyWord
    from harness.validators import validate, has_errors
    a = VerseAnalysis(
        book="Matthew", chapter=23, verse=8, reference="Matthew 23:8",
        greek_text="ὑμεῖς δὲ μὴ κληθῆτε Ῥαββί·",
        web_text="But be not ye called Rabbi",
        greek_pure=True,
        expanded_translation="But you shall not be called Rabbi",
        diffs=[DiffEntry("Rabbi", "title means my great one", "Jesus forbids")],
        insights=[],
        key_words=[KeyWord("κληθῆτε", "klēthēte", "G2564", "V-ASP-2P", "to call", "prohibitive")],
    )
    issues = validate(a, bundle_strongs_numbers={"G2564", "G4771"})
    errors = [i for i in issues if i.severity == "error"]
    assert not errors, [i.message for i in errors]


def test_validators_catch_greek_in_expanded():
    from harness.schema import VerseAnalysis, DiffEntry, KeyWord
    from harness.validators import validate, has_errors
    a = VerseAnalysis(
        book="Matthew", chapter=23, verse=8, reference="Matthew 23:8",
        greek_text="ὑμεῖς", web_text="But you", greek_pure=True,
        expanded_translation="But ὑμεῖς shall not be called",  # Greek bleed
        diffs=[], insights=[], key_words=[],
    )
    issues = validate(a)
    assert has_errors(issues)


def test_validators_catch_fabricated_diff():
    from harness.schema import VerseAnalysis, DiffEntry
    from harness.validators import validate
    a = VerseAnalysis(
        book="Matthew", chapter=23, verse=8, reference="Matthew 23:8",
        greek_text="ὑμεῖς", web_text="But be not ye called Rabbi",
        greek_pure=True,
        expanded_translation="But you shall not be called",
        diffs=[DiffEntry("pharaoh", "x", "y")],  # "pharaoh" not in WEB
        insights=[], key_words=[],
    )
    issues = validate(a)
    warnings = [i for i in issues if "not found in WEB" in i.message]
    assert warnings


def test_state_manifest_roundtrip(tmp_path):
    from harness.state import init_manifest, update_verse_status, Manifest
    m, path = init_manifest("test_run", "Matthew", [(23, 8), (23, 9)])
    assert m.run_id == "test_run"
    assert len(m.verses) == 2
    m = update_verse_status(path, 23, 8, "analyzed")
    m2 = Manifest.load(path)
    assert m2.verses["23:8"]["status"] == "analyzed"
    assert m2.verses["23:9"]["status"] == "pending"


def test_cache_roundtrip(tmp_path):
    from harness import cache
    # Create a fake source file
    src = tmp_path / "src.json"
    src.write_text('{"text": "hello"}')
    cache.put_cached_verse("test", "Book", 1, 1, src, {"text": "hello"})
    data, hit = cache.get_cached_verse("test", "Book", 1, 1, src)
    assert hit
    assert data["text"] == "hello"
    # Modify source with different-sized content → miss (size is part of the key)
    src.write_text('{"text": "different world"}')
    data, hit = cache.get_cached_verse("test", "Book", 1, 1, src)
    assert not hit
    cache.clear("test")


def test_writer_renders_verse():
    from harness.schema import VerseAnalysis, DiffEntry, KeyWord, Insight
    from harness.writer import _fallback_render
    a = VerseAnalysis(
        book="Matthew", chapter=23, verse=8, reference="Matthew 23:8",
        greek_text="ὑμεῖς", web_text="But you", greek_pure=True,
        expanded_translation="But you shall not be called",
        diffs=[DiffEntry("Rabbi", "title", "why")],
        insights=[Insight("Prohibitive", "desc")],
        key_words=[KeyWord("ὑμεῖς", "hymeis", "G4771", "PPro-N2P", "you", "subject")],
    )
    md = _fallback_render(a, "Matthew 23:8-12")
    assert "Matthew 23:8" in md
    assert "ὑμεῖς" in md
    assert "Rabbi" in md


def test_cross_refs_populated_matthew_5_5():
    from harness.retrieve import fetch_verse
    b = fetch_verse("Matthew", 5, 5)
    assert b.cross_refs, "cross_refs should be populated"
    # Psalm 37:11 is the top cross-ref (105 votes) for Matthew 5:5
    top = b.cross_refs[0]
    assert top["book_name"] in ("Psalm", "Psalms")
    assert top["chapter"] == 37
    assert top["verse"] == 11
    assert top["votes"] >= 100
    # Hebrew word analysis attached
    assert top.get("hebrew_words")
    assert len(top["hebrew_words"]) > 0
    # First Hebrew word should have Strong's data
    hw = top["hebrew_words"][0]
    assert hw.get("strong")
    assert hw.get("strongs_data")


def test_cross_refs_can_be_disabled():
    from harness.retrieve import fetch_verse
    b = fetch_verse("Matthew", 5, 5, include_cross_refs=False)
    assert b.cross_refs == [] or b.cross_refs is None


def test_validator_flags_unverified_cross_ref():
    from harness.schema import VerseAnalysis
    from harness.validators import validate
    a = VerseAnalysis(
        book="Matthew", chapter=5, verse=5, reference="Matthew 5:5",
        greek_text="ὑμεῖς", web_text="But you", greek_pure=True,
        expanded_translation="But you",
        diffs=[], insights=[], key_words=[],
        cross_references=["Habakkuk 9:99 (votes: 5)"],  # not in index
    )
    bundle_refs = [{"book_name": "Psalm", "book_abbr": "Ps",
                    "chapter": 37, "verse": 11, "votes": 105}]
    issues = validate(a, bundle_cross_refs=bundle_refs)
    warnings = [i for i in issues if "not in bundle cross-ref index" in i.message]
    assert warnings


def test_validator_accepts_known_cross_ref():
    from harness.schema import VerseAnalysis
    from harness.validators import validate
    a = VerseAnalysis(
        book="Matthew", chapter=5, verse=5, reference="Matthew 5:5",
        greek_text="ὑμεῖς", web_text="But you", greek_pure=True,
        expanded_translation="But you",
        diffs=[], insights=[], key_words=[],
        cross_references=["Psalm 37:11 (votes: 105)"],
    )
    bundle_refs = [{"book_name": "Psalm", "book_abbr": "Ps",
                    "chapter": 37, "verse": 11, "votes": 105}]
    issues = validate(a, bundle_cross_refs=bundle_refs)
    warnings = [i for i in issues if "not in bundle cross-ref index" in i.message]
    assert not warnings


def test_cross_references_james_typo_fixed():
    """Regression: cross_references.py had 'Jas': 'Jasus' typo."""
    from cross_references import BOOK_DISPLAY_NAMES
    assert BOOK_DISPLAY_NAMES["Jas"] == "James"


def test_diff_entry_layer_gap_fields():
    from harness.schema import DiffEntry
    d = DiffEntry("inherit", "x", "y",
                  hebrew_root="yârash (H3423)",
                  greek_choice="klēronomeō (G2816)",
                  web_rendering="inherit",
                  gap_type="hebrew_to_greek",
                  evidence_status="textual")
    assert d.hebrew_root == "yârash (H3423)"
    assert d.gap_type == "hebrew_to_greek"


def test_aramaic_gap_validator_passes_epistles():
    """Epistles (spoken_jesus_material=False) don't need aramaic_gap_acknowledged."""
    from harness.schema import VerseAnalysis
    from harness.validators import validate, has_errors
    a = VerseAnalysis(
        book="Romans", chapter=1, verse=1, reference="Romans 1:1",
        greek_text="Παῦλος", web_text="Paul", greek_pure=True,
        expanded_translation="Paul", diffs=[], insights=[], key_words=[],
        aramaic_gap_acknowledged=False,
    )
    issues = validate(a, spoken_jesus_material=False)
    gap_issues = [i for i in issues if "aramaic" in i.field]
    assert not gap_issues


def test_aramaic_gap_validator_flags_spoken_jesus():
    """Spoken-Jesus material with OT refs MUST acknowledge the Aramaic gap."""
    from harness.schema import VerseAnalysis
    from harness.validators import validate
    a = VerseAnalysis(
        book="Matthew", chapter=5, verse=5, reference="Matthew 5:5",
        greek_text="Μακάριοι", web_text="Blessed", greek_pure=True,
        expanded_translation="Happy", diffs=[], insights=[], key_words=[],
        aramaic_gap_acknowledged=False,
    )
    bundle_refs = [{"book_name": "Psalm", "testament": "OT", "chapter": 37, "verse": 11}]
    issues = validate(a, bundle_cross_refs=bundle_refs, spoken_jesus_material=True)
    gap_issues = [i for i in issues if "aramaic" in i.field]
    assert gap_issues
    assert any(i.severity == "error" for i in gap_issues)


def test_aramaic_gap_validator_passes_when_acknowledged():
    from harness.schema import VerseAnalysis
    from harness.validators import validate
    a = VerseAnalysis(
        book="Matthew", chapter=5, verse=5, reference="Matthew 5:5",
        greek_text="Μακάριοι", web_text="Blessed", greek_pure=True,
        expanded_translation="Happy", diffs=[], insights=[], key_words=[],
        aramaic_gap_acknowledged=True,
        context_notes=["Jesus taught in Aramaic; the Greek is the earliest extant text."],
    )
    bundle_refs = [{"book_name": "Psalm", "testament": "OT", "chapter": 37, "verse": 11}]
    issues = validate(a, bundle_cross_refs=bundle_refs, spoken_jesus_material=True)
    gap_errors = [i for i in issues if "aramaic" in i.field and i.severity == "error"]
    assert not gap_errors


def test_jesus_attribution_validator():
    """Catches 'Jesus softens' in spoken material."""
    from harness.schema import VerseAnalysis, Insight
    from harness.validators import validate
    a = VerseAnalysis(
        book="Matthew", chapter=5, verse=5, reference="Matthew 5:5",
        greek_text="x", web_text="y", greek_pure=True,
        expanded_translation="z",
        diffs=[], key_words=[],
        insights=[Insight("test", "Jesus softens the conquest promise")],
        aramaic_gap_acknowledged=True,
        context_notes=["Aramaic gap noted"],
    )
    issues = validate(a, spoken_jesus_material=True)
    attribution_issues = [i for i in issues if "attributes Greek word choice to Jesus" in i.message]
    assert attribution_issues


def test_spoken_jesus_material_book_index():
    """Matthew = True, Romans = False."""
    from harness.retrieve import fetch_verse
    assert fetch_verse("Matthew", 1, 1).spoken_jesus_material is True
    assert fetch_verse("Romans", 1, 1).spoken_jesus_material is False
    assert fetch_verse("Acts", 1, 1).spoken_jesus_material is True
    assert fetch_verse("Revelation", 1, 1).spoken_jesus_material is False


# ── Hebrew / OT tests ──────────────────────────────────────────────────────────


def test_hebrew_purity_clean():
    from harness.hebrew_text import verify_hebrew
    r = verify_hebrew("בְּרֵאשִׁית בָּרָא אֱלֹהִים")
    assert r.is_hebrew, r.reason
    assert not r.offending_chars


def test_hebrew_purity_with_cantillation():
    from harness.hebrew_text import verify_hebrew
    # Genesis 1:1 with trope marks (U+0591–U+05AF) + vowel points
    r = verify_hebrew("בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים")
    assert r.is_hebrew, r.reason


def test_hebrew_purity_detects_latin_bleed():
    from harness.hebrew_text import verify_hebrew
    r = verify_hebrew("בְּre'shit בָּרָא")
    assert not r.is_hebrew
    assert len(r.offending_chars) > 0
    # Latin letters flagged
    flagged_chars = {ch for _, ch, _ in r.offending_chars}
    assert "r" in flagged_chars and "e" in flagged_chars


def test_hebrew_purity_detects_greek_bleed():
    from harness.hebrew_text import verify_hebrew
    r = verify_hebrew("βρα בָּרָא")
    assert not r.is_hebrew
    flagged = {ch for _, ch, _ in r.offending_chars}
    assert "β" in flagged


def test_hebrew_purity_empty():
    from harness.hebrew_text import verify_hebrew
    r = verify_hebrew("")
    assert not r.is_hebrew
    assert "no hebrew text" in r.reason


def test_hebrew_purity_maqef_allowed():
    from harness.hebrew_text import verify_hebrew
    # Maqef (U+05BE) is inside the Hebrew block — should pass
    r = verify_hebrew("בְּרֵאשִׁית־בָּרָא")
    assert r.is_hebrew, r.reason


def test_decode_morph_noun():
    from harness.hebrew_text import decode_morph
    assert decode_morph("HNcmpa") == "Noun common masculine plural absolute"
    assert decode_morph("HNcfsa") == "Noun common feminine singular absolute"
    assert decode_morph("HNcbsa") == "Noun common dual(both) singular absolute"


def test_decode_morph_verb():
    from harness.hebrew_text import decode_morph
    assert decode_morph("HVqp3ms") == "Verb Qal perfect 3rd masculine singular"
    assert decode_morph("HVqp3fs") == "Verb Qal perfect 3rd feminine singular"
    assert decode_morph("HVqc") == "Verb Qal infinitive construct"


def test_decode_morph_compound():
    from harness.hebrew_text import decode_morph
    assert decode_morph("HR/Ncfsa") == "Preposition / Noun common feminine singular absolute"
    assert decode_morph("HTd/Ncmpa") == "Particle (definite article) / Noun common masculine plural absolute"
    assert decode_morph("HC/To") == "Conjunction / Particle (object marker)"


def test_decode_morph_particle():
    from harness.hebrew_text import decode_morph
    assert decode_morph("HTo") == "Particle (object marker)"
    assert decode_morph("HTd") == "Particle (definite article)"


def test_fetch_verse_genesis_1_1():
    from harness.retrieve import fetch_verse
    b = fetch_verse("Genesis", 1, 1)
    assert b.book == "Genesis"
    assert b.testament == "OT"
    assert b.original_language == "hebrew"
    assert b.hebrew_text and "בְּרֵאשִׁ" in b.hebrew_text  # consonantal skeleton of bereshit
    assert b.hebrew_pure, f"hebrew not pure: {b.hebrew_purity}"
    assert b.asv_text and "In the beginning" in b.asv_text
    assert b.spoken_jesus_material is False
    # Genesis 1:1 has 7 Hebrew words
    assert len(b.hebrew_words) == 7
    w0 = b.hebrew_words[0]
    assert w0.strongs == "H7225"
    assert "feminine" in w0.morph_readable
    assert w0.lemma  # BDB lemma populated
    assert w0.strongs_def  # BDB definition populated
    # OT verse should not populate NT fields
    assert b.greek_text is None
    assert b.web_text is None


def test_fetch_verse_genesis_aliases():
    from harness.retrieve import fetch_verse, resolve_book
    assert resolve_book("gen") == "Genesis"
    assert resolve_book("Ge") == "Genesis"
    assert resolve_book("gn") == "Genesis"
    b = fetch_verse("gen", 1, 1)
    assert b.book == "Genesis"


def test_ot_chapter_verse_count():
    from harness.retrieve import chapter_verse_count, book_chapter_count
    # Genesis 1 has 31 verses; Genesis has 50 chapters
    assert chapter_verse_count("Genesis", 1) == 31
    assert book_chapter_count("Genesis") == 50


def test_ot_verse_bundle_json():
    from harness.retrieve import fetch_verse
    import json
    b = fetch_verse("Genesis", 1, 1)
    j = b.to_json()
    d = json.loads(j)
    assert d["testament"] == "OT"
    assert d["original_language"] == "hebrew"
    assert d["hebrew_text"]
    assert d["asv_text"]
    assert d["hebrew_words"]
    assert d["hebrew_words"][0]["strongs"].startswith("H")


def test_nt_regression_matthew_still_works():
    """NT retrieval must still work after OT additions (regression guard)."""
    from harness.retrieve import fetch_verse
    b = fetch_verse("Matthew", 23, 8)
    assert b.testament == "NT"
    assert b.original_language == "greek"
    assert b.greek_text and b.greek_pure
    assert b.web_text
    assert b.strongs_count > 0
    # NT verse should not populate OT fields
    assert b.hebrew_text is None
    assert b.asv_text is None
    assert b.hebrew_words == []


def test_writer_renders_ot_verse():
    """Writer should render Hebrew/ASV for OT verses, not Greek/WEB."""
    from harness.schema import VerseAnalysis, DiffEntry, KeyWord, Insight
    from harness.writer import _fallback_render
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        greek_text="", web_text="", greek_pure=False,
        hebrew_text="בְּרֵאשִׁית בָּרָא אֱלֹהִים",
        asv_text="In the beginning God created the heavens and the earth.",
        hebrew_pure=True,
        original_language="hebrew", testament="OT",
        expanded_translation="In the beginning (the marked start of an ordered sequence) God created the heavens and the earth.",
        diffs=[DiffEntry("In the beginning", "loses the construct-chain nuance", "why",
                         hebrew_root="rêʼshîyth (H7225)", asv_rendering="In the beginning",
                         gap_type="hebrew_to_asv", evidence_status="textual")],
        insights=[Insight("Divine-exclusive creation", "בָּרָא (H1254) used only of God")],
        key_words=[KeyWord("בָּרָא", "bârâʼ", "H1254", lexical_range="to create",
                          nuance="divine-exclusive", morphology="Verb Qal perfect 3rd masculine singular",
                          stem="Qal")],
    )
    md = _fallback_render(a, "Genesis 1:1-5")
    assert "Genesis 1:1" in md
    assert "Hebrew" in md
    assert "WLC" in md
    assert "ASV" in md
    assert "בְּרֵאשִׁית" in md
    assert "In the beginning God created" in md
    assert "Morphology" in md  # OT key word table has Morphology column
    assert "Stem" in md
    assert "Qal" in md
    # Should NOT say "Greek" or "WEB" or "SBLGNT"
    assert "Greek" not in md
    assert "WEB" not in md
    assert "SBLGNT" not in md


def test_summary_renders_ot_passage():
    """Summary should label ASV/Hebrew for OT runs, not WEB/Greek."""
    from harness.schema import VerseAnalysis
    from harness.summary import render_summary_md
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning",
        hebrew_pure=True, original_language="hebrew", testament="OT",
        expanded_translation="In the beginning (marked start)",
        insights=[],
    )
    md = render_summary_md([a], "Genesis 1:1-5")
    assert "Hebrew (WLC)" in md
    assert "ASV" in md
    assert "WEB" not in md
    assert "Greek" not in md


def test_schema_ot_roundtrip():
    """VerseAnalysis OT fields survive to_dict/from_dict roundtrip."""
    from harness.schema import VerseAnalysis, DiffEntry, KeyWord
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning",
        hebrew_pure=True, original_language="hebrew", testament="OT",
        expanded_translation="In the beginning",
        diffs=[DiffEntry("In the beginning", "x", "y", hebrew_root="H7225",
                         asv_rendering="In the beginning", gap_type="hebrew_to_asv")],
        key_words=[KeyWord("בְּרֵאשִׁית", "rêʼshîyth", "H7225",
                          morphology="Noun common feminine singular absolute", stem=None)],
    )
    d = a.to_dict()
    a2 = VerseAnalysis.from_dict(d)
    assert a2.testament == "OT"
    assert a2.hebrew_text == "בְּרֵאשִׁית"
    assert a2.asv_text == "In the beginning"
    assert a2.key_words[0].morphology == "Noun common feminine singular absolute"
    assert a2.diffs[0].asv_rendering == "In the beginning"
    assert a2.diffs[0].gap_type == "hebrew_to_asv"


# ── OT validator tests ─────────────────────────────────────────────────────────


def test_validator_ot_passes_good_analysis():
    """A clean OT analysis should pass validators without errors."""
    from harness.schema import VerseAnalysis, DiffEntry, KeyWord
    from harness.validators import validate, has_errors
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית בָּרָא אֱלֹהִים",
        asv_text="In the beginning God created the heavens and the earth.",
        hebrew_pure=True, original_language="hebrew", testament="OT",
        expanded_translation="In the beginning (the marked start) God created the heavens and the earth.",
        diffs=[DiffEntry("In the beginning", "loses construct-chain nuance", "why",
                         hebrew_root="rêʼshîyth (H7225)", asv_rendering="In the beginning",
                         gap_type="hebrew_to_asv", evidence_status="textual")],
        insights=[],
        key_words=[KeyWord("בָּרָא", "bârâʼ", "H1254", lexical_range="to create",
                          nuance="divine-exclusive", morphology="Verb Qal perfect 3rd masculine singular",
                          stem="Qal")],
    )
    issues = validate(a, bundle_strongs_numbers={"H7225", "H1254"})
    errors = [i for i in issues if i.severity == "error"]
    assert not errors, [i.message for i in errors]


def test_validator_ot_catches_hebrew_in_expanded():
    """Hebrew Unicode in expanded_translation should fail for OT."""
    from harness.schema import VerseAnalysis
    from harness.validators import validate, has_errors
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning God created",
        hebrew_pure=True, testament="OT",
        expanded_translation="In the בְּרֵאשִׁית God created",  # Hebrew bleed
        diffs=[], insights=[], key_words=[],
    )
    issues = validate(a)
    assert has_errors(issues)
    assert any("Hebrew" in i.message for i in issues)


def test_validator_ot_catches_h_strongs_in_expanded():
    """H#### Strong's numbers in expanded_translation should fail for OT."""
    from harness.schema import VerseAnalysis
    from harness.validators import validate, has_errors
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning God created",
        hebrew_pure=True, testament="OT",
        expanded_translation="In the beginning (H7225) God created",  # Strong's bleed
        diffs=[], insights=[], key_words=[],
    )
    issues = validate(a)
    assert has_errors(issues)


def test_validator_ot_skips_aramaic_gap():
    """OT verses should NOT trigger the Aramaic-gap check even with NT cross-refs."""
    from harness.schema import VerseAnalysis
    from harness.validators import validate
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning",
        hebrew_pure=True, testament="OT",
        expanded_translation="In the beginning",
        diffs=[], insights=[], key_words=[],
        aramaic_gap_acknowledged=False,  # OT should not require this
    )
    # Even with NT cross-refs present, OT should not flag Aramaic gap
    bundle_refs = [{"book_name": "John", "testament": "NT", "chapter": 1, "verse": 1}]
    issues = validate(a, bundle_cross_refs=bundle_refs, spoken_jesus_material=False)
    gap_issues = [i for i in issues if "aramaic" in i.field.lower()]
    assert not gap_issues


def test_validator_ot_skips_jesus_attribution():
    """OT verses should NOT trigger the Jesus-attribution check."""
    from harness.schema import VerseAnalysis, Insight
    from harness.validators import validate
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning",
        hebrew_pure=True, testament="OT",
        expanded_translation="In the beginning",
        diffs=[], key_words=[],
        insights=[Insight("test", "Jesus softens the creation narrative")],  # would flag in NT
    )
    issues = validate(a, spoken_jesus_material=False)
    attribution_issues = [i for i in issues if "attributes" in i.message]
    assert not attribution_issues


def test_validator_ot_diff_phrase_in_asv():
    """OT diff phrases must appear in ASV text (not WEB)."""
    from harness.schema import VerseAnalysis, DiffEntry
    from harness.validators import validate
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning God created the heavens",
        hebrew_pure=True, testament="OT",
        expanded_translation="In the beginning God created",
        diffs=[DiffEntry("pharaoh", "x", "y")],  # "pharaoh" not in ASV text
        insights=[], key_words=[],
    )
    issues = validate(a)
    warnings = [i for i in issues if "not found in ASV" in i.message]
    assert warnings


# ── Claim-audit layer tests (claim-audit-spec.md) ──────────────────────────────


def _ca_ot_analysis(hebrew_text: str, insights=None, diffs=None, key_words=None,
                    expanded: str = "they took for themselves wives from all that they chose"):
    from harness.schema import VerseAnalysis
    return VerseAnalysis(
        book="Genesis", chapter=6, verse=2, reference="Genesis 6:2",
        hebrew_text=hebrew_text,
        asv_text="that the sons of God saw the daughters of men that they were fair; and they took them wives of all that they chose.",
        hebrew_pure=True, original_language="hebrew", testament="OT",
        expanded_translation=expanded,
        diffs=diffs or [], insights=insights or [], key_words=key_words or [],
    )


def test_claim_audit_root_presence_flags_covenant():
    from harness.schema import Insight
    from harness.validators import claim_audit_issues
    a = _ca_ot_analysis(
        "וַיִּקְחוּ לָהֶם נָשִׁים",  # no ברית in this verse text
        insights=[Insight("Covenant framing", "The act prefigures the covenant with Noah.")],
    )
    issues = claim_audit_issues(a)
    ca6 = [i for i in issues if "[CA-6]" in i.message and "covenant" in i.message]
    assert ca6
    assert all(i.severity == "warning" for i in ca6)
    assert ca6[0].field == "insights[0].description"


def test_claim_audit_root_presence_passes_when_root_present():
    from harness.schema import Insight
    from harness.validators import claim_audit_issues
    a = _ca_ot_analysis(
        "וַהֲקִמֹתִי אֶת בְּרִיתִי",  # ברית present
        insights=[Insight("Covenant framing", "The covenant word anchors the passage.")],
    )
    issues = claim_audit_issues(a)
    assert not any("[CA-6]" in i.message for i in issues)


def test_claim_audit_certainty_lexicon_flags():
    from harness.schema import Insight
    from harness.validators import claim_audit_issues
    a = _ca_ot_analysis(
        "וַיִּקְחוּ לָהֶם נָשִׁים",
        insights=[Insight("Framing", "The narrator's choice of the taking-verb frames the act as appropriation.")],
    )
    issues = claim_audit_issues(a)
    assert any("[CA-4]" in i.message for i in issues)


def test_claim_audit_certainty_hedged_passes():
    from harness.schema import Insight
    from harness.validators import claim_audit_issues
    a = _ca_ot_analysis(
        "וַיִּקְחוּ לָהֶם נָשִׁים",
        insights=[Insight("Framing", "The taking-verb frames the act as if it were appropriation.")],
    )
    issues = claim_audit_issues(a)
    assert not any("[CA-4]" in i.message for i in issues)


def test_claim_audit_citation_presence_flags():
    from harness.schema import DiffEntry
    from harness.validators import claim_audit_issues
    a = _ca_ot_analysis(
        "וַיִּקְחוּ לָהֶם נָשִׁים",
        diffs=[DiffEntry("took them wives", "The verb means seize rather than give in marriage.",
                         "The act reads as appropriation.")],
    )
    issues = claim_audit_issues(a)
    assert any("[CA-1/CA-2]" in i.message for i in issues)


def test_claim_audit_citation_present_passes():
    from harness.schema import DiffEntry
    from harness.validators import claim_audit_issues
    a = _ca_ot_analysis(
        "וַיִּקְחוּ לָהֶם נָשִׁים",
        diffs=[DiffEntry("took them wives",
                         "The marriage idiom lāqaḥ nāšîm carries the meaning (Gen 4:19; 11:29).",
                         "The idiom is the standard marriage construction.")],
    )
    issues = claim_audit_issues(a)
    assert not any("[CA-1/CA-2]" in i.message for i in issues)


def test_claim_audit_hedge_contradiction_flags():
    """CA-3: table hedges ('context decides') but prose asserts one side unhedged."""
    from harness.schema import Insight, KeyWord
    from harness.validators import claim_audit_issues
    kw = KeyWord("נָשִׁ֔ים", "ishshah", "H802",
                 lexical_range="woman / wife (the same lexeme covers both; context decides)",
                 nuance="spans both senses")
    a = _ca_ot_analysis(
        "וַיִּקְחוּ לָהֶם נָשִׁים",
        key_words=[kw],
        insights=[Insight("Women, not wives",
                          "Hebrew says 'women' — the marital reading 'wives' is supplied by translators, not forced by the noun.")],
    )
    issues = claim_audit_issues(a)
    ca3 = [i for i in issues if "[CA-3]" in i.message]
    assert ca3
    assert all(i.severity == "warning" for i in ca3)


def test_claim_audit_clean_analysis_no_warnings():
    from harness.schema import VerseAnalysis, DiffEntry, KeyWord
    from harness.validators import claim_audit_issues
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית בָּרָא אֱלֹהִים",
        asv_text="In the beginning God created the heavens and the earth.",
        hebrew_pure=True, original_language="hebrew", testament="OT",
        expanded_translation="In the beginning (the marked start) God created the heavens and the earth.",
        diffs=[DiffEntry("In the beginning", "loses construct-chain nuance", "why",
                         hebrew_root="rêʼshîyth (H7225)", asv_rendering="In the beginning",
                         gap_type="hebrew_to_asv", evidence_status="textual")],
        insights=[],
        key_words=[KeyWord("בָּרָא", "bara", "H1254", lexical_range="to create",
                           nuance="divine-exclusive", morphology="Verb Qal perfect 3rd masculine singular",
                           stem="Qal")],
    )
    issues = claim_audit_issues(a)
    assert not issues, [i.message for i in issues]


def test_claim_audit_heuristics_never_error():
    """§7 heuristics emit warning (never error), even on a maximally bad analysis."""
    from harness.schema import Insight
    from harness.validators import claim_audit_issues, has_errors
    a = _ca_ot_analysis(
        "וַיִּקְחוּ לָהֶם נָשִׁים",
        insights=[Insight("Covenant framing", "The narrator deliberately frames a covenant; the act means seizure.")],
    )
    issues = claim_audit_issues(a)
    assert issues
    assert not has_errors(issues)


def test_claim_audit_wired_into_validate():
    """validate() runs the claim-audit heuristics (ingest-time pass-through)."""
    from harness.schema import Insight
    from harness.validators import validate, has_errors
    a = _ca_ot_analysis(
        "וַיִּקְחוּ לָהֶם נָשִׁים",
        insights=[Insight("Covenant framing", "The act prefigures the covenant with Noah.")],
    )
    issues = validate(a)
    assert any("[CA-6]" in i.message for i in issues)
    assert not has_errors(issues)


# ── Review normalization tests (schema.py, spec §6.3) ──────────────────────────


def test_review_normalization_legacy_string_summary():
    from harness.schema import normalize_review
    r = normalize_review({"valid": True, "corrections": [], "summary": "all clean"})
    assert r.summary["text"] == "all clean"
    assert r.summary["claim_audit"] == {"total": 0, "licensed": 0, "downgraded": 0, "cut": 0}


def test_review_normalization_derives_claim_audit():
    from harness.schema import normalize_review
    r = normalize_review({
        "valid": False,
        "corrections": [
            {"severity": "error", "field": "diffs", "index": 3, "issue": "i", "fix": "f",
             "rule": "CA-2", "claim": "not the covenantal marriage verb", "verdict": "cut"},
            {"severity": "warning", "field": "insights", "index": 2, "issue": "i", "fix": "f",
             "rule": "CA-4", "claim": "frames the act"},
            {"severity": "warning", "field": "diffs", "index": 0,
             "issue": "phrase not verbatim", "fix": "f"},
        ],
        "summary": "three findings",
    })
    ca = r.summary["claim_audit"]
    assert ca == {"total": 2, "licensed": 0, "downgraded": 1, "cut": 1}
    assert r.summary["text"] == "three findings"
    d = r.to_dict()
    assert d["summary"]["claim_audit"]["total"] == 2
    assert d["corrections"][0]["rule"] == "CA-2"
    assert d["corrections"][1]["verdict"] is None
    # structural correction carries no rule
    assert d["corrections"][2]["rule"] is None


def test_review_normalization_prefers_reviewer_tally():
    from harness.schema import normalize_review
    r = normalize_review({
        "valid": False,
        "corrections": [{"severity": "error", "field": "diffs", "index": 0,
                         "issue": "i", "fix": "f", "rule": "CA-1",
                         "claim": "x means y", "verdict": "downgraded"}],
        "claim_audit": {"downgraded": 2, "cut": 1},
        "summary": {"text": "audited", "claim_audit": {"total": 12, "licensed": 9}},
    })
    ca = r.summary["claim_audit"]
    assert ca["total"] == 12 and ca["licensed"] == 9
    assert ca["downgraded"] == 2 and ca["cut"] == 1


def test_review_correction_field_validation():
    from harness.schema import ReviewCorrection
    c = ReviewCorrection.from_dict({"severity": "banana", "field": "diffs", "index": "3",
                                    "issue": "i", "rule": "CA-9", "verdict": "maybe"})
    assert c.severity == "warning"
    assert c.index is None
    assert c.rule is None
    assert c.verdict is None


# ── SUMMARY claim-audit rendering tests (spec §9.5) ────────────────────────────


def test_summary_renders_claim_audit_counts():
    from harness.schema import VerseAnalysis
    from harness.summary import render_summary_md
    a = VerseAnalysis(
        book="Genesis", chapter=6, verse=2, reference="Genesis 6:2",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning",
        hebrew_pure=True, original_language="hebrew", testament="OT",
        expanded_translation="In the beginning", insights=[],
    )
    audits = [{"verse_file": "Genesis_6-2.review.json",
               "total": 4, "licensed": 1, "downgraded": 2, "cut": 1}]
    md = render_summary_md([a], "Genesis 6:1-10", claim_audits=audits)
    assert "## 🔍 Claim Audit" in md
    assert "Genesis_6-2.review.json" in md
    assert "2 downgraded" in md and "1 cut" in md
    # must not break the OT render contract
    assert "WEB" not in md
    assert "Greek" not in md


def test_summary_empty_claim_audit_section():
    from harness.schema import VerseAnalysis
    from harness.summary import render_summary_md
    a = VerseAnalysis(
        book="Genesis", chapter=6, verse=2, reference="Genesis 6:2",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning",
        hebrew_pure=True, original_language="hebrew", testament="OT",
        expanded_translation="In the beginning", insights=[],
    )
    md = render_summary_md([a], "Genesis 6:1-10")
    assert "## 🔍 Claim Audit" in md
    assert "No claim-audit findings recorded" in md


def test_load_review_audits_legacy_derivation(tmp_path):
    from harness.summary import _load_review_audits
    (tmp_path / "Genesis_6-2.review.json").write_text(json.dumps({
        "valid": False,
        "corrections": [
            {"severity": "error", "field": "diffs", "index": 3, "issue": "i", "fix": "f",
             "rule": "CA-2", "claim": "not the covenantal marriage verb", "verdict": "cut"},
            {"severity": "warning", "field": "insights", "index": 2, "issue": "i", "fix": "f",
             "rule": "CA-4", "claim": "frames", "verdict": "downgraded"},
        ],
        "summary": "two findings"},
    ), encoding="utf-8")
    audits = _load_review_audits(tmp_path)
    assert audits == [{"verse_file": "Genesis_6-2.review.json",
                       "total": 2, "licensed": 0, "downgraded": 1, "cut": 1}]


# ── Prompt integration smoke tests (claim-audit sections render) ───────────────


def test_analyst_prompt_contains_claim_audit_ot():
    from harness.retrieve import fetch_verse
    from harness.prompts import analyst_prompt
    b = fetch_verse("Genesis", 1, 1)
    p = analyst_prompt(b, passage_ref="Genesis 1:1-5")
    assert "Licensing Requirements (claim audit)" in p
    assert "CA-1" in p and "CA-2" in p and "CA-4" in p
    assert "Self-audit checklist" in p


def test_analyst_prompt_contains_claim_audit_nt():
    from harness.retrieve import fetch_verse
    from harness.prompts import analyst_prompt
    b = fetch_verse("Matthew", 23, 8)
    p = analyst_prompt(b)
    assert "Licensing Requirements (claim audit)" in p
    assert "CA-1" in p


def test_reviewer_prompt_contains_ca_rules():
    from harness.retrieve import fetch_verse
    from harness.prompts import reviewer_prompt
    from harness.schema import VerseAnalysis
    b = fetch_verse("Genesis", 1, 1)
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text=b.hebrew_text, asv_text=b.asv_text, hebrew_pure=True,
        original_language="hebrew", testament="OT",
    )
    p = reviewer_prompt(a, b)
    for rule in ("CA-1", "CA-2", "CA-3", "CA-4", "CA-5", "CA-6", "CA-7"):
        assert rule in p
    assert '"rule"' in p and '"claim"' in p and '"verdict"' in p
    assert "error** (blocks finalize)" in p


def test_corrector_prompt_contains_preserve_hedges():
    from harness.prompts import corrector_prompt
    from harness.schema import VerseAnalysis
    a = VerseAnalysis(
        book="Genesis", chapter=1, verse=1, reference="Genesis 1:1",
        hebrew_text="בְּרֵאשִׁית", asv_text="In the beginning",
        hebrew_pure=True, original_language="hebrew", testament="OT",
    )
    p = corrector_prompt(a, "- fix x")
    assert "Claim-audit fixes" in p
    assert "do not strengthen a downgraded claim" in p


def test_insight_evidence_status_roundtrip():
    """CA-4/CA-5 insight tagging survives the schema roundtrip."""
    from harness.schema import VerseAnalysis, Insight
    a = VerseAnalysis(
        book="Genesis", chapter=6, verse=2, reference="Genesis 6:2",
        hebrew_text="נָשִׁים", asv_text="wives", hebrew_pure=True,
        original_language="hebrew", testament="OT",
        expanded_translation="wives",
        insights=[Insight("t", "d", evidence_status="inferential")],
    )
    a2 = VerseAnalysis.from_dict(a.to_dict())
    assert a2.insights[0].evidence_status == "inferential"
    # legacy insights without the field still load
    a3 = VerseAnalysis.from_dict({"book": "Genesis", "chapter": 6, "verse": 2,
                                  "reference": "Genesis 6:2",
                                  "insights": [{"title": "t", "description": "d"}]})
    assert a3.insights[0].evidence_status is None


# ── Legacy sidecar normalization tests (ESV-era field names, read-time only) ───


def _legacy_nt_sidecar_dict():
    """Fixture modeled on runs/Matthew_5-5/Matthew_5-5.json (July 2026, ESV era):
    esv_text at top level, esv_rendering + *_to_esv in diffs, no
    testament/original_language fields."""
    return {
        "book": "Matthew", "chapter": 5, "verse": 5, "reference": "Matthew 5:5",
        "greek_text": "Μακάριοι οἱ πρᾳεῖς· ὅτι αὐτοὶ κληρονομήσουσιν τὴν γῆν.",
        "esv_text": "Blessed are the meek: for they shall inherit the earth.",
        "greek_pure": True,
        "expanded_translation": "Fortunate are the mild — for they themselves shall receive the land as their inheritance.",
        "diffs": [
            {"baseline_phrase": "meek", "what_lost": "weakness reading", "why_matters": "tempered strength",
             "hebrew_root": "ʻânâv (H6035)", "greek_choice": "praÿs (G4239)",
             "esv_rendering": "meek", "gap_type": "hebrew_to_esv", "evidence_status": "textual"},
            {"baseline_phrase": "earth", "what_lost": "land/earth range", "why_matters": "both live readings",
             "greek_choice": "gē (G1093)",
             "esv_rendering": "earth", "gap_type": "greek_to_esv", "evidence_status": "inferential"},
        ],
        "insights": [{"title": "t", "description": "d"}],
        "key_words": [{"word": "πρᾳεῖς", "transliteration": "praeis", "strongs": "G4239",
                       "parsing": "nom masc pl adjective", "lexical_range": "mild, gentle",
                       "nuance": "tempered strength"}],
        "context_notes": ["Third beatitude."],
        "cross_references": ["Psalm 37:11 (votes: 105)"],
        "further_study": [],
        "analyst": "Peaches (4K Bible Translation Harness)",
        "review_status": "Draft - Ready for Review",
        "aramaic_gap_acknowledged": True,
    }


def test_legacy_nt_sidecar_loads_and_maps():
    """The Matthew_5-5 field pattern loads via from_dict (previously TypeError)."""
    from harness.schema import VerseAnalysis
    legacy = _legacy_nt_sidecar_dict()
    a = VerseAnalysis.from_dict(legacy)  # must not raise
    assert a.reference == "Matthew 5:5"
    assert a.web_text == "Blessed are the meek: for they shall inherit the earth."
    assert a.testament == "NT"
    assert a.diffs[0].web_rendering == "meek"
    assert a.diffs[0].gap_type == "hebrew_to_web"
    assert a.diffs[1].web_rendering == "earth"
    assert a.diffs[1].gap_type == "greek_to_web"
    assert all(not hasattr(d, "esv_rendering") for d in a.diffs)


def test_legacy_normalization_ot_variant():
    """OT legacy sidecar maps esv_* → asv_* (hebrew_to_esv → hebrew_to_asv)."""
    from harness.schema import VerseAnalysis
    legacy = {
        "book": "Genesis", "chapter": 6, "verse": 2, "reference": "Genesis 6:2",
        "hebrew_text": "וַיִּקְחוּ לָהֶם נָשִׁים", "esv_text": "wives text",
        "hebrew_pure": True,
        "expanded_translation": "they took wives",
        "diffs": [{"baseline_phrase": "wives", "what_lost": "x", "why_matters": "y",
                   "hebrew_root": "lâqach (H3947)", "esv_rendering": "wives",
                   "gap_type": "hebrew_to_esv", "evidence_status": "textual"}],
    }
    a = VerseAnalysis.from_dict(legacy)
    assert a.testament == "OT"
    assert a.original_language == "hebrew"
    assert a.asv_text == "wives text"
    assert a.diffs[0].asv_rendering == "wives"
    assert a.diffs[0].gap_type == "hebrew_to_asv"


def test_legacy_testament_detection_without_explicit_fields():
    """No testament/original_language: hebrew_text presence implies OT, else NT."""
    from harness.schema import normalize_legacy_analysis
    nt = _legacy_nt_sidecar_dict()
    assert normalize_legacy_analysis(nt) is not nt  # copy, input unmutated
    ot = {"book": "Genesis", "chapter": 1, "verse": 1, "reference": "Genesis 1:1",
          "hebrew_text": "בְּרֵאשִׁית", "esv_text": "In the beginning", "diffs": []}
    assert normalize_legacy_analysis(ot)["asv_text"] == "In the beginning"


def test_legacy_normalization_does_not_mutate_input():
    from harness.schema import VerseAnalysis, normalize_legacy_analysis
    legacy = _legacy_nt_sidecar_dict()
    normalized = normalize_legacy_analysis(legacy)
    assert "esv_text" in legacy and "web_text" not in legacy
    assert legacy["diffs"][0]["esv_rendering"] == "meek"
    assert normalized["web_text"] == legacy["esv_text"]
    assert "esv_text" not in normalized
    # from_dict path likewise leaves the caller's dict untouched
    VerseAnalysis.from_dict(legacy)
    assert "esv_text" in legacy


def test_load_verse_analysis_legacy_sidecar_readonly(tmp_path):
    """load_verse_analysis accepts a legacy sidecar and never rewrites the file."""
    from harness.writer import load_verse_analysis
    p = tmp_path / "Matthew_5-5.json"
    raw = json.dumps(_legacy_nt_sidecar_dict(), ensure_ascii=False)
    p.write_text(raw, encoding="utf-8")
    a = load_verse_analysis(p)
    assert a.web_text.startswith("Blessed are the meek")
    assert p.read_text(encoding="utf-8") == raw  # disk sidecar byte-identical


def test_current_schema_dict_passes_through_unmapped():
    """Modern (WEB-era) dicts contain no esv_* keys and are untouched."""
    from harness.schema import VerseAnalysis
    a = VerseAnalysis(
        book="Matthew", chapter=23, verse=8, reference="Matthew 23:8",
        greek_text="ὑμεῖς", web_text="But you", greek_pure=True,
        expanded_translation="But you",
        diffs=[{"baseline_phrase": "you", "what_lost": "x", "why_matters": "y",
                "web_rendering": "you", "gap_type": "greek_to_web"}],
    )
    d = a.to_dict()
    a2 = VerseAnalysis.from_dict(d)
    assert a2.web_text == "But you"
    assert a2.diffs[0].web_rendering == "you"
    assert a2.diffs[0].gap_type == "greek_to_web"


def test_next_review_accepts_legacy_sidecar(tmp_path, monkeypatch):
    """End-to-end re-review path: next_review_verse loads a legacy sidecar,
    flips status to reviewing, and leaves the disk sidecar untouched."""
    import harness.state as state
    from harness.orchestrator import next_review_verse
    monkeypatch.setattr(state, "RUNS_DIR", tmp_path)
    run_id = "legacy_recheck_test"
    rd = tmp_path / run_id
    rd.mkdir()
    sidecar = rd / "Matthew_5-5.json"
    raw = json.dumps(_legacy_nt_sidecar_dict(), ensure_ascii=False)
    sidecar.write_text(raw, encoding="utf-8")
    manifest_path = rd / "manifest.json"
    manifest_path.write_text(json.dumps({
        "run_id": run_id, "book": "Matthew",
        "chapter_start": 5, "chapter_end": 5, "verse_start": 5, "verse_end": 5,
        "whole_book": False, "created_at": 0.0,
        "verses": {"5:5": {"book": "Matthew", "chapter": 5, "verse": 5,
                           "status": "analyzed", "attempts": 0, "last_error": None,
                           "analysis_path": "Matthew_5-5.md",
                           "sidecar_path": "Matthew_5-5.json",
                           "purity_ok": True, "validators_ok": True,
                           "updated_at": 0.0}},
    }, indent=2), encoding="utf-8")

    payload = next_review_verse(run_id)
    assert payload is not None
    assert payload["verse"] == 5
    assert "Blessed are the meek" in payload["analysis"]["web_text"]  # mapped in memory
    assert "CA-1" in payload["prompt"]  # current reviewer prompt with claim audit
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert m["verses"]["5:5"]["status"] == "reviewing"
    assert sidecar.read_text(encoding="utf-8") == raw  # disk sidecar byte-identical


# ── ingest_review dispatched-verse targeting tests (fix-spec 2026-09-15 #1) ────


def _two_verse_reviewing_fixture(rd: Path) -> Path:
    """12:17-style fixture: verse 12:17 stuck in `reviewing` with a corrections
    sidecar awaiting the correction cycle; verse 12:18 analyzed and next in
    line for review dispatch."""
    manifest_path = rd / "manifest.json"
    manifest_path.write_text(json.dumps({
        "run_id": rd.name, "book": "Genesis",
        "chapter_start": 12, "chapter_end": 12, "verse_start": 11, "verse_end": 20,
        "whole_book": False, "created_at": 0.0,
        "verses": {
            "12:17": {"book": "Genesis", "chapter": 12, "verse": 17,
                      "status": "reviewing", "attempts": 0,
                      "last_error": "3 corrections",
                      "analysis_path": "Genesis_12-17.md",
                      "sidecar_path": "Genesis_12-17.json",
                      "purity_ok": True, "validators_ok": True,
                      "updated_at": 0.0},
            "12:18": {"book": "Genesis", "chapter": 12, "verse": 18,
                      "status": "analyzed", "attempts": 0, "last_error": None,
                      "analysis_path": "Genesis_12-18.md",
                      "sidecar_path": "Genesis_12-18.json",
                      "purity_ok": True, "validators_ok": True,
                      "updated_at": 0.0},
        },
    }, indent=2), encoding="utf-8")
    (rd / "Genesis_12-17.review.json").write_text(json.dumps({
        "valid": False,
        "corrections": [{"severity": "error", "field": "diffs", "index": 0,
                         "issue": "i", "fix": "f"}],
        "summary": "stuck correction cycle",
    }, ensure_ascii=False), encoding="utf-8")
    (rd / "Genesis_12-18.json").write_text(json.dumps({
        "book": "Genesis", "chapter": 12, "verse": 18,
        "reference": "Genesis 12:18",
        "hebrew_text": "וַיִּקְרָא פַרְעֹה",
        "asv_text": "And Pharaoh called Abram",
        "hebrew_pure": True, "original_language": "hebrew", "testament": "OT",
        "expanded_translation": "So Pharaoh called Abram",
        "diffs": [], "insights": [], "key_words": [],
    }, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def test_ingest_review_targets_dispatched_verse(tmp_path, monkeypatch):
    """Fix-spec 2026-09-15 #1: a verdict must land on the verse dispatched by
    next_review_verse — not on the first verse stuck in `reviewing` (the 9/14
    12:18 mis-target that consumed a valid verdict for the stuck 12:17)."""
    import harness.state as state
    from harness.orchestrator import ingest_review, next_review_verse
    monkeypatch.setattr(state, "RUNS_DIR", tmp_path)
    run_id = "dispatch_target_test"
    rd = tmp_path / run_id
    rd.mkdir()
    manifest_path = _two_verse_reviewing_fixture(rd)

    payload = next_review_verse(run_id)
    assert payload is not None
    assert payload["verse"] == 18  # dispatched the analyzed verse, not stuck 12:17
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert m["dispatched_review_verse"] == "12:18"

    verdict = json.dumps({"valid": True, "corrections": [],
                          "summary": {"text": "clean",
                                      "claim_audit": {"total": 0, "licensed": 0,
                                                      "downgraded": 0, "cut": 0}}})
    result = ingest_review(run_id, verdict)
    assert "error" not in result, result
    assert result["verse"] == "Genesis 12:18", result
    assert result["valid"] is True and result["status"] == "reviewed"

    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert m["verses"]["12:18"]["status"] == "reviewed"
    # the stuck verse is untouched — no false `reviewed`, verdict not consumed
    assert m["verses"]["12:17"]["status"] == "reviewing"
    # dispatch record cleared on ingest
    assert m["dispatched_review_verse"] is None


def test_ingest_review_corrections_target_dispatched_verse(tmp_path, monkeypatch):
    """Invalid verdict: corrections sidecar must be written for the dispatched
    verse (12:18), the stuck 12:17 sidecar left alone, and the dispatch record
    cleared."""
    import harness.state as state
    from harness.orchestrator import ingest_review, next_review_verse
    monkeypatch.setattr(state, "RUNS_DIR", tmp_path)
    run_id = "dispatch_corrections_test"
    rd = tmp_path / run_id
    rd.mkdir()
    manifest_path = _two_verse_reviewing_fixture(rd)

    payload = next_review_verse(run_id)
    assert payload is not None and payload["verse"] == 18

    verdict = json.dumps({"valid": False,
                          "corrections": [{"severity": "error", "field": "diffs",
                                           "index": 0, "issue": "i", "fix": "f"}],
                          "summary": "two findings"})
    result = ingest_review(run_id, verdict)
    assert "error" not in result, result
    assert result["verse"] == "Genesis 12:18"
    assert result["status"] == "needs_correction"
    assert result["corrections_path"].endswith("Genesis_12-18.review.json")

    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert m["verses"]["12:18"]["last_error"] == "1 corrections"
    assert (rd / "Genesis_12-18.review.json").exists()
    # stuck verse's sidecar untouched
    stuck = json.loads((rd / "Genesis_12-17.review.json").read_text(encoding="utf-8"))
    assert stuck["summary"] == "stuck correction cycle"
    assert m["dispatched_review_verse"] is None


def test_ingest_review_legacy_fallback_single_reviewing(tmp_path, monkeypatch):
    """Pre-dispatch-field manifest (no dispatched_review_verse): single
    reviewing verse still resolves via the legacy first-reviewing scan."""
    import harness.state as state
    from harness.orchestrator import ingest_review
    monkeypatch.setattr(state, "RUNS_DIR", tmp_path)
    run_id = "legacy_single_reviewing_test"
    rd = tmp_path / run_id
    rd.mkdir()
    manifest_path = rd / "manifest.json"
    manifest_path.write_text(json.dumps({
        "run_id": run_id, "book": "Genesis",
        "chapter_start": 12, "chapter_end": 12, "verse_start": 17, "verse_end": 17,
        "whole_book": False, "created_at": 0.0,
        "verses": {
            "12:17": {"book": "Genesis", "chapter": 12, "verse": 17,
                      "status": "reviewing", "attempts": 0, "last_error": None,
                      "analysis_path": "Genesis_12-17.md",
                      "sidecar_path": "Genesis_12-17.json",
                      "purity_ok": True, "validators_ok": True,
                      "updated_at": 0.0},
        },
    }, indent=2), encoding="utf-8")

    verdict = json.dumps({"valid": True, "corrections": [], "summary": "clean"})
    result = ingest_review(run_id, verdict)
    assert "error" not in result, result
    assert result["verse"] == "Genesis 12:17"
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert m["verses"]["12:17"]["status"] == "reviewed"


def test_valid_verdict_persists_review_sidecar(tmp_path, monkeypatch):
    """Fix-spec 2026-09-15 #2: valid verdicts persist as a review sidecar
    (mirrors .review.json shape) so history/audit survives."""
    import harness.state as state
    from harness.orchestrator import ingest_review
    monkeypatch.setattr(state, "RUNS_DIR", tmp_path)
    run_id = "valid_sidecar_test"
    rd = tmp_path / run_id
    rd.mkdir()
    manifest_path = rd / "manifest.json"
    manifest_path.write_text(json.dumps({
        "run_id": run_id, "book": "Genesis",
        "chapter_start": 12, "chapter_end": 12, "verse_start": 18, "verse_end": 18,
        "whole_book": False, "created_at": 0.0,
        "verses": {
            "12:18": {"book": "Genesis", "chapter": 12, "verse": 18,
                      "status": "reviewing", "attempts": 0, "last_error": None,
                      "analysis_path": "Genesis_12-18.md",
                      "sidecar_path": "Genesis_12-18.json",
                      "purity_ok": True, "validators_ok": True,
                      "updated_at": 0.0},
        },
    }, indent=2), encoding="utf-8")

    verdict = json.dumps({
        "valid": True,
        "corrections": [],
        "summary": {"text": "clean", "claim_audit": {"total": 2, "licensed": 2,
                                                     "downgraded": 0, "cut": 0}},
    })
    result = ingest_review(run_id, verdict)
    assert "error" not in result, result
    assert result["status"] == "reviewed"
    assert result["review_path"].endswith("Genesis_12-18.review.valid.json")

    sidecar = json.loads((rd / "Genesis_12-18.review.valid.json").read_text(encoding="utf-8"))
    assert sidecar["valid"] is True
    assert sidecar["corrections"] == []
    assert sidecar["summary"]["claim_audit"]["licensed"] == 2
    # must NOT be visible to the correction queue glob (valid != pending correction)
    assert not (rd / "Genesis_12-18.review.json").exists()
    from harness.summary import _load_review_audits
    assert _load_review_audits(rd) == []


# ── Hebrew combining-mark drift at ingest (fix-spec 2026-09-15 #3) ─────────────

# bundle: bet + qamats(U+05B8, ccc 18) + dagesh(U+05BC, ccc 21) — canonical order
_BUNDLE_MARKS = "\u05d1\u05b8\u05bc"
# analyst drift: dagesh written before qamats — NFC-equivalent, not byte-equal
_DRIFT_MARKS = "\u05d1\u05bc\u05b8"


def _ot_analysis_with_text(hebrew_text: str) -> "VerseAnalysis":
    from harness.schema import VerseAnalysis
    return VerseAnalysis(
        book="Genesis", chapter=12, verse=18, reference="Genesis 12:18",
        hebrew_text=hebrew_text, asv_text="And Pharaoh called Abram",
        hebrew_pure=True, original_language="hebrew", testament="OT",
        expanded_translation="So Pharaoh called Abram",
        diffs=[], insights=[], key_words=[],
    )


def test_normalize_source_text_repairs_mark_drift():
    """dagesh/qamats order drift (NFC-equivalent) is rewritten to the bundle's
    exact bytes — the reviewer's byte-exact ground truth is the bundle, which
    is itself not always NFC, so the repaired form must be the bundle text."""
    import unicodedata
    from harness.validators import normalize_source_text
    a = _ot_analysis_with_text(f"וַיִּקְרָא {_DRIFT_MARKS}רָא")
    bundle_text = f"וַיִּקְרָא {_BUNDLE_MARKS}רָא"
    assert a.hebrew_text != bundle_text
    assert unicodedata.normalize("NFC", a.hebrew_text) \
        == unicodedata.normalize("NFC", bundle_text)
    note = normalize_source_text(a, bundle_text)
    assert note and "hebrew_text" in note
    assert a.hebrew_text == bundle_text  # bundle bytes, not NFC output


def test_normalize_source_text_leaves_real_corruption():
    """A genuinely different text (dropped aleph) is NOT silently repaired."""
    from harness.validators import normalize_source_text
    a = _ot_analysis_with_text("בָּרָתִי")  # aleph dropped from בָּרָאתִי
    bundle_text = "בָּרָאתִי"
    assert normalize_source_text(a, bundle_text) is None
    assert a.hebrew_text == "בָּרָתִי"  # untouched — byte-compare will flag it


def test_normalize_source_text_noop_when_equal_or_empty():
    from harness.validators import normalize_source_text
    a = _ot_analysis_with_text("בָּרָאתִי")
    assert normalize_source_text(a, "בָּרָאתִי") is None  # already byte-equal
    a_empty = _ot_analysis_with_text("")
    assert normalize_source_text(a_empty, "בָּרָאתִי") is None
    assert normalize_source_text(a, None) is None  # no bundle text available


def test_validator_byte_exact_source_compare():
    """validate() with bundle_source_text flags byte-mismatch (review check 1
    mirror) and passes when byte-equal; drift repaired by normalize passes."""
    from harness.validators import normalize_source_text, validate, has_errors
    bundle_text = f"וַיִּקְרָא {_BUNDLE_MARKS}רָא"
    # byte-equal → no issue
    issues = validate(_ot_analysis_with_text(bundle_text),
                      bundle_source_text=bundle_text)
    assert not [i for i in issues if i.severity == "error"], \
        [i.message for i in issues if i.severity == "error"]
    # real corruption (dropped char) → error
    issues = validate(_ot_analysis_with_text("בָּרָתִי"),
                      bundle_source_text="בָּרָאתִי")
    exact = [i for i in issues if "byte-match" in i.message]
    assert exact and exact[0].severity == "error"
    assert exact[0].field == "hebrew_text"
    # combining-mark drift → error when unrepaired, clean after normalize
    drift = _ot_analysis_with_text(f"וַיִּקְרָא {_DRIFT_MARKS}רָא")
    issues = validate(drift, bundle_source_text=bundle_text)
    assert any("byte-match" in i.message for i in issues)
    normalize_source_text(drift, bundle_text)
    issues = validate(drift, bundle_source_text=bundle_text)
    assert not has_errors(issues), [i.message for i in issues if i.severity == "error"]


def test_validator_byte_exact_skipped_without_bundle_text():
    """No bundle_source_text → check skipped (backward-compatible signature)."""
    from harness.validators import validate, has_errors
    issues = validate(_ot_analysis_with_text("בָּרָתִי"))
    assert not has_errors(issues), [i.message for i in issues if i.severity == "error"]
