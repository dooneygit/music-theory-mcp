import pytest
from fastmcp.exceptions import ToolError

from music_theory_mcp.server import (
    analyze_progression,
    check_voice_leading,
    chord_from_symbol,
    detect_key,
    diatonic_chords,
    identify_chord,
    interval_between,
    key_info,
    note_info,
    roman_numeral_to_chord,
    scale_degree,
    scale_notes,
    transpose_chords,
    transpose_notes,
)


def test_note_info():
    assert note_info("Bb4") == {
        "note": "Bb4",
        "name": "Bb",
        "octave": 4,
        "midi": 70,
        "frequency_hz": 466.16,
        "pitch_class": 10,
        "enharmonics": ["Cbb5", "A#4"],
    }


def test_note_info_defaults_to_octave_4():
    result = note_info("A")
    assert (result["note"], result["midi"], result["frequency_hz"]) == ("A4", 69, 440.0)


def test_note_info_crosses_octave_for_enharmonics():
    assert note_info("B#3")["midi"] == 60


def test_note_info_bad_input():
    with pytest.raises(ToolError, match="Invalid note"):
        note_info("H2")


def test_interval_between():
    assert interval_between("C4", "Ab4") == {
        "from": "C4",
        "to": "Ab4",
        "name": "m6",
        "full_name": "Minor Sixth",
        "direction": "ascending",
        "semitones": 8,
        "simple_name": "m6",
        "is_compound": False,
        "is_consonant": True,
        "inversion": "M3",
    }


@pytest.mark.parametrize(
    "note1, note2, name",
    [("C", "F#", "A4"), ("C", "Gb", "d5"), ("Bb3", "D#4", "A3"), ("E", "Bb", "d5"), ("C4", "C4", "P1")],
)
def test_interval_between_spelling(note1, note2, name):
    assert interval_between(note1, note2)["name"] == name


def test_interval_between_descending_and_compound():
    down = interval_between("G", "C")
    assert (down["name"], down["direction"], down["semitones"]) == ("P5", "descending", -7)
    ninth = interval_between("C4", "D5")
    assert (ninth["name"], ninth["simple_name"], ninth["is_compound"], ninth["inversion"]) == ("M9", "M2", True, "m7")


def test_interval_between_bad_input():
    with pytest.raises(ToolError, match="Invalid note"):
        interval_between("C", "Q")


def test_transpose_notes():
    assert transpose_notes(["C4", "E4", "G4"], "m3") == {"interval": "m3", "notes": ["Eb4", "G4", "Bb4"]}


@pytest.mark.parametrize(
    "notes, step, expected",
    [
        (["C#"], "M3", ["E#"]),
        (["F#", "C#"], "-P5", ["B", "F#"]),
        (["Bb3"], "M9", ["C5"]),
        (["Bb"], 2, ["C"]),
        (["E4"], "-2", ["D4"]),
    ],
)
def test_transpose_notes_spelling(notes, step, expected):
    assert transpose_notes(notes, step)["notes"] == expected


def test_transpose_notes_bad_input():
    with pytest.raises(ToolError, match="Invalid interval"):
        transpose_notes(["C"], "P3")
    with pytest.raises(ToolError, match="Invalid note"):
        transpose_notes(["C", "Z"], "M2")


def test_chord_from_symbol():
    assert chord_from_symbol("F#m7b5") == {
        "symbol": "F#m7b5",
        "notes": ["F#", "A", "C", "E"],
        "root": "F#",
        "bass": "F#",
        "kind": "half-diminished-seventh",
        "chord_tones": [
            {"note": "F#", "interval": "P1"},
            {"note": "A", "interval": "m3"},
            {"note": "C", "interval": "d5"},
            {"note": "E", "interval": "m7"},
        ],
    }


@pytest.mark.parametrize(
    "symbol, notes",
    [
        ("Bbmaj7", ["Bb", "D", "F", "A"]),
        ("Ebdim7", ["Eb", "Gb", "Bbb", "Dbb"]),
        ("C7(b9)", ["C", "E", "G", "Bb", "Db"]),
        ("Bb7b9#11", ["Bb", "D", "F", "Ab", "Cb", "E"]),
        ("C6/9", ["C", "E", "G", "A", "D"]),
        ("Dsus4", ["D", "G", "A"]),
    ],
)
def test_chord_from_symbol_notes(symbol, notes):
    assert chord_from_symbol(symbol)["notes"] == notes


def test_chord_from_symbol_slash_bass():
    result = chord_from_symbol("D7/F#")
    assert (result["notes"], result["root"], result["bass"]) == (["F#", "A", "C", "D"], "D", "F#")
    assert result["chord_tones"][0] == {"note": "F#", "interval": "M3"}
    assert chord_from_symbol("C/D")["chord_tones"][0] == {"note": "D", "interval": "M2"}


def test_chord_from_symbol_extension_intervals():
    tones = chord_from_symbol("C7#9")["chord_tones"]
    assert tones[-1] == {"note": "D#", "interval": "A9"}


def test_chord_from_symbol_bad_input():
    with pytest.raises(ToolError, match="Unrecognized chord symbol"):
        chord_from_symbol("Cblah")


def test_identify_chord():
    assert identify_chord(["E", "G", "C"]) == {
        "notes": ["E4", "G4", "C5"],
        "symbol": "C/E",
        "name": "major triad",
        "root": "C",
        "bass": "E",
        "inversion": "first inversion",
        "forte_class": "3-11B",
        "prime_form": [0, 3, 7],
    }


@pytest.mark.parametrize(
    "notes, symbol, name, inversion",
    [
        (["B3", "D4", "F4", "A4"], "Bø7", "half-diminished seventh chord", "root position"),
        (["F#", "A#", "C#", "E"], "F#7", "dominant seventh chord", "root position"),
        (["G3", "C4", "E4"], "C/G", "major triad", "second inversion"),
        (["Bb2", "C4", "E4", "G4"], "C7/Bb", "dominant seventh chord", "third inversion"),
        (["C4", "E4", "G#4"], "C+", "augmented triad", "root position"),
    ],
)
def test_identify_chord_cases(notes, symbol, name, inversion):
    result = identify_chord(notes)
    assert (result["symbol"], result["name"], result["inversion"]) == (symbol, name, inversion)


def test_identify_chord_non_tertian():
    result = identify_chord(["C4", "C#4", "D4"])
    assert (result["symbol"], result["inversion"], result["forte_class"]) == (None, None, "3-1")


def test_identify_chord_bad_input():
    with pytest.raises(ToolError, match="octaves for all notes or for none"):
        identify_chord(["C4", "E", "G"])
    with pytest.raises(ToolError, match="at least one note"):
        identify_chord([])


def test_transpose_chords():
    assert transpose_chords(["C", "Am", "F", "G7"], "M2") == {"interval": "M2", "chords": ["D", "Bm", "G", "A7"]}


@pytest.mark.parametrize(
    "chords, step, expected",
    [
        (["Bbmaj7", "Eb7", "D7/F#"], "-m3", ["Gmaj7", "C7", "B7/D#"]),
        (["F#m7b5", "B7b9", "Em"], "P4", ["Bm7b5", "E7b9", "Am"]),
        (["Bb7b9#11"], "M2", ["C7b9#11"]),
        (["C"], "A4", ["F#"]),
        (["C"], "d5", ["Gb"]),
        (["Db/Ab"], 1, ["D/A"]),
    ],
)
def test_transpose_chords_cases(chords, step, expected):
    assert transpose_chords(chords, step)["chords"] == expected


def test_transpose_chords_bad_input():
    with pytest.raises(ToolError, match="Unrecognized chord symbol"):
        transpose_chords(["C", "Gfoo"], "M2")


def test_scale_notes():
    assert scale_notes("F#") == {
        "tonic": "F#",
        "scale": "major",
        "direction": "ascending",
        "notes": ["F#", "G#", "A#", "B", "C#", "D#", "E#", "F#"],
    }


@pytest.mark.parametrize(
    "tonic, scale_type, direction, notes",
    [
        ("Bb", "harmonic minor", "ascending", ["Bb", "C", "Db", "Eb", "F", "Gb", "A", "Bb"]),
        ("A", "melodic minor", "ascending", ["A", "B", "C", "D", "E", "F#", "G#", "A"]),
        ("A", "melodic minor", "descending", ["A", "G", "F", "E", "D", "C", "B", "A"]),
        ("D", "dorian", "ascending", ["D", "E", "F", "G", "A", "B", "C", "D"]),
        ("Eb", "lydian", "ascending", ["Eb", "F", "G", "A", "Bb", "C", "D", "Eb"]),
        ("C", "whole tone", "ascending", ["C", "D", "E", "F#", "G#", "A#", "C"]),
        ("C", "octatonic half-whole", "ascending", ["C", "Db", "Eb", "Fb", "Gb", "G", "A", "Bb", "C"]),
    ],
)
def test_scale_notes_types(tonic, scale_type, direction, notes):
    assert scale_notes(tonic, scale_type, direction)["notes"] == notes


def test_scale_notes_chromatic_has_13_notes():
    assert len(scale_notes("C", "chromatic")["notes"]) == 13


def test_scale_notes_bad_input():
    with pytest.raises(ToolError, match="Invalid note"):
        scale_notes("X", "major")


def test_key_info():
    assert key_info("Eb") == {
        "key": "Eb major",
        "signature": {"sharps": 0, "flats": 3, "accidentals": ["Bb", "Eb", "Ab"]},
        "scale": ["Eb", "F", "G", "Ab", "Bb", "C", "D", "Eb"],
        "relative": "C minor",
        "parallel": "Eb minor",
    }


def test_key_info_minor():
    result = key_info("c#")
    assert result["key"] == "C# minor"
    assert result["signature"] == {"sharps": 4, "flats": 0, "accidentals": ["F#", "C#", "G#", "D#"]}
    assert (result["relative"], result["parallel"]) == ("E major", "C# major")


def test_key_info_mode():
    result = key_info("D dorian")
    assert (result["key"], result["signature"]["accidentals"], result["relative"]) == ("D dorian", [], "C major")


def test_key_info_seven_sharps():
    assert key_info("C# major")["signature"]["sharps"] == 7


def test_key_info_bad_input():
    with pytest.raises(ToolError, match="Invalid key"):
        key_info("C bebop")


def test_scale_degree():
    assert scale_degree("F", "D major") == {
        "note": "F",
        "key": "D major",
        "degree": 3,
        "alteration": "b",
        "label": "b3",
        "degree_name": "mediant",
        "in_key": False,
    }


@pytest.mark.parametrize(
    "note, key, label, degree_name, in_key",
    [
        ("F#", "D", "3", "mediant", True),
        ("G#", "a minor", "#7", "leading tone", False),
        ("G", "a minor", "7", "subtonic", True),
        ("B", "C", "7", "leading tone", True),
        ("Bb", "C", "b7", "subtonic", False),
        ("Db", "C", "b2", "supertonic", False),
        ("E#", "C#", "3", "mediant", True),
        ("Ebb", "C", "bb3", "mediant", False),
        ("Eb4", "Eb", "1", "tonic", True),
    ],
)
def test_scale_degree_cases(note, key, label, degree_name, in_key):
    result = scale_degree(note, key)
    assert (result["label"], result["degree_name"], result["in_key"]) == (label, degree_name, in_key)


def test_scale_degree_bad_input():
    with pytest.raises(ToolError, match="Invalid key"):
        scale_degree("C", "Q major")


def test_roman_numeral_to_chord():
    assert roman_numeral_to_chord("V65/V", "C") == {
        "numeral": "V65/V",
        "key": "C major",
        "notes": ["F#", "A", "C", "D"],
        "root": "D",
        "bass": "F#",
        "inversion": "first inversion",
        "name": "dominant seventh chord",
        "symbol": "D7/F#",
        "tonicized_key": "G major",
    }


@pytest.mark.parametrize(
    "numeral, key, notes, name",
    [
        ("viio7", "a minor", ["G#", "B", "D", "F"], "diminished seventh chord"),
        ("V7", "a minor", ["E", "G#", "B", "D"], "dominant seventh chord"),
        ("bVI", "C", ["Ab", "C", "Eb"], "major triad"),
        ("VI", "c", ["Ab", "C", "Eb"], "major triad"),
        ("ii42", "Eb", ["Eb", "F", "Ab", "C"], "minor seventh chord"),
        ("iiø7", "C", ["D", "F", "Ab", "C"], "half-diminished seventh chord"),
        ("It+6", "a", ["F", "A", "D#"], "Italian augmented sixth chord"),
        ("Ger65", "C", ["Ab", "C", "Eb", "F#"], "German augmented sixth chord"),
        ("N6", "a", ["D", "F", "Bb"], "major triad"),
        ("Cad64", "C", ["G", "C", "E"], "major triad"),
    ],
)
def test_roman_numeral_to_chord_cases(numeral, key, notes, name):
    result = roman_numeral_to_chord(numeral, key)
    assert (result["notes"], result["name"]) == (notes, name)


def test_roman_numeral_to_chord_inversions():
    assert roman_numeral_to_chord("I64", "G")["inversion"] == "second inversion"
    assert roman_numeral_to_chord("V42", "G")["inversion"] == "third inversion"
    assert roman_numeral_to_chord("I", "G")["tonicized_key"] is None


def test_roman_numeral_to_chord_bad_input():
    with pytest.raises(ToolError, match="Invalid Roman numeral"):
        roman_numeral_to_chord("VIIIx", "C")


def test_diatonic_chords():
    result = diatonic_chords("C")
    assert (result["key"], result["scale"]) == ("C major", "major")
    assert result["chords"][0] == {
        "degree": 1,
        "numeral": "I",
        "symbol": "C",
        "notes": ["C", "E", "G"],
        "name": "major triad",
    }
    assert [c["numeral"] for c in result["chords"]] == ["I", "ii", "iii", "IV", "V", "vi", "viio"]


def test_diatonic_chords_sevenths():
    result = diatonic_chords("Bb", sevenths=True)
    assert [c["symbol"] for c in result["chords"]] == ["Bbmaj7", "Cm7", "Dm7", "Ebmaj7", "F7", "Gm7", "Aø7"]
    assert result["chords"][6]["numeral"] == "viiø7"


@pytest.mark.parametrize(
    "key, variant, numerals",
    [
        ("e minor", "harmonic", ["i", "iio", "III+", "iv", "V", "VI", "viio"]),
        ("a", "natural", ["i", "iio", "III", "iv", "v", "VI", "VII"]),
        ("a", "melodic", ["i", "ii", "III+", "IV", "V", "vio", "viio"]),
        ("D dorian", "harmonic", ["i", "ii", "III", "IV", "v", "vio", "VII"]),
    ],
)
def test_diatonic_chords_scales(key, variant, numerals):
    assert [c["numeral"] for c in diatonic_chords(key, minor_variant=variant)["chords"]] == numerals


def test_diatonic_chords_harmonic_minor_sevenths():
    chords = diatonic_chords("a", sevenths=True)["chords"]
    assert (chords[4]["numeral"], chords[4]["notes"]) == ("V7", ["E", "G#", "B", "D"])
    assert (chords[6]["numeral"], chords[6]["symbol"]) == ("viio7", "G#o7")


def test_analyze_progression():
    assert analyze_progression(["C", "Am", "Dm7", "G7", "C"], "C") == {
        "key": "C major",
        "chords": [
            {"chord": "C", "numeral": "I", "notes": ["C", "E", "G"]},
            {"chord": "Am", "numeral": "vi", "notes": ["A", "C", "E"]},
            {"chord": "Dm7", "numeral": "ii7", "notes": ["D", "F", "A", "C"]},
            {"chord": "G7", "numeral": "V7", "notes": ["G", "B", "D", "F"]},
            {"chord": "C", "numeral": "I", "notes": ["C", "E", "G"]},
        ],
    }


@pytest.mark.parametrize(
    "chords, key, numerals",
    [
        (["Am", "B7", "E7", "Am"], "a minor", ["i", "V7/V", "V7", "i"]),
        (["Bbmaj7", "Gm7", "C7", "F"], "F", ["IV7", "ii7", "V7", "I"]),
        (["C", "C7", "F", "Fm", "C/G", "G7", "C"], "C", ["I", "V7/IV", "IV", "iv", "I64", "V7", "I"]),
        (["Eb", "Ab", "Bb7", "Eb"], "Eb", ["I", "IV", "V7", "I"]),
        (["Cm", "Db/F", "G7", "Cm"], "c", ["i", "bII6", "V7", "i"]),
    ],
)
def test_analyze_progression_cases(chords, key, numerals):
    assert [c["numeral"] for c in analyze_progression(chords, key)["chords"]] == numerals


def test_analyze_progression_bad_input():
    with pytest.raises(ToolError, match="Invalid key"):
        analyze_progression(["C"], "C blues")
    with pytest.raises(ToolError, match="Unrecognized chord symbol"):
        analyze_progression(["C", "Gzz"], "C")


def test_detect_key():
    result = detect_key(["C", "D", "E", "F", "G", "A", "B", "C"])
    assert result["key"] == "C major"
    assert 0 < result["confidence"] <= 1
    assert len(result["alternatives"]) == 4
    assert all(alt["confidence"] <= result["confidence"] for alt in result["alternatives"])


@pytest.mark.parametrize(
    "notes, key",
    [
        (["A", "C", "E", "G#", "B", "D", "F", "E", "A"], "A minor"),
        ("C C G G A A G F F E E D D C".split(), "C major"),
        ("G B D G F# E D C B A G".split(), "G major"),
        ("E G B E D# E F# G A B".split(), "E minor"),
        ("Bb D F Bb A G F Eb D C Bb".split(), "Bb major"),
    ],
)
def test_detect_key_cases(notes, key):
    assert detect_key(notes)["key"] == key


def test_detect_key_bad_input():
    with pytest.raises(ToolError, match="at least one note"):
        detect_key([])


def test_check_voice_leading_parallel_fifths():
    assert check_voice_leading(["G4", "A4"], ["C4", "D4"]) == {
        "issue_count": 1,
        "transitions": [
            {
                "from": ["G4", "C4"],
                "to": ["A4", "D4"],
                "intervals": ["P5", "P5"],
                "motion": "parallel",
                "issues": ["parallel fifths"],
            }
        ],
    }


def test_check_voice_leading_clean_cadence():
    result = check_voice_leading(["E5", "D5", "C5"], ["C3", "B2", "C3"])
    assert result["issue_count"] == 0
    assert [t["motion"] for t in result["transitions"]] == ["parallel", "contrary"]


@pytest.mark.parametrize(
    "upper, lower, issue",
    [
        (["C5", "D5"], ["C4", "D4"], "parallel octaves"),
        (["G4", "D5"], ["C4", "G3"], "fifths by contrary motion"),
        (["E4", "C5"], ["A3", "C4"], "hidden (direct) octave"),
        (["E5", "D5"], ["C3", "G2"], "hidden (direct) fifth"),
        (["C4", "D4"], ["E4", "F4"], "voice crossing"),
        (["E4", "G4"], ["C4", "F4"], "voice overlap"),
    ],
)
def test_check_voice_leading_issues(upper, lower, issue):
    assert issue in check_voice_leading(upper, lower)["transitions"][0]["issues"]


def test_check_voice_leading_bad_input():
    with pytest.raises(ToolError, match="same number of notes"):
        check_voice_leading(["C5", "D5"], ["C4"])
    with pytest.raises(ToolError, match="needs an octave"):
        check_voice_leading(["C5", "D"], ["C4", "B3"])
