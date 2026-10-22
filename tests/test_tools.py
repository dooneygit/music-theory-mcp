import pytest
from fastmcp.exceptions import ToolError

from music_theory_mcp.server import (
    chord_from_symbol,
    identify_chord,
    interval_between,
    note_info,
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
