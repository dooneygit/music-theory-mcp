import pytest
from fastmcp.exceptions import ToolError

from music_theory_mcp.server import interval_between, note_info, transpose_notes


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
