import pytest
from fastmcp.exceptions import ToolError

from music_theory_mcp.notation import (
    display,
    display_key,
    parse_chord_symbol,
    parse_interval,
    parse_key,
    parse_pitch,
    parse_roman,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("C", "C"),
        ("Bb4", "B-4"),
        ("bb4", "B-4"),
        ("f#3", "F#3"),
        ("Ebb", "E--"),
        ("Cx", "C##"),
        ("B-4", "B-4"),
        ("E♭5", "E-5"),
        (" G# ", "G#"),
    ],
)
def test_parse_pitch(text, expected):
    assert parse_pitch(text).nameWithOctave == expected


@pytest.mark.parametrize("text", ["H", "", "C#b", "Cbbb", "Bb4x", "do"])
def test_parse_pitch_rejects_bad_input(text):
    with pytest.raises(ToolError, match="Invalid note"):
        parse_pitch(text)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("F#m7b5", ["F#", "A", "C", "E"]),
        ("Bbmaj7", ["B-", "D", "F", "A"]),
        ("Bb7b9#11", ["B-", "D", "F", "A-", "C-", "E"]),
        ("Ebdim7", ["E-", "G-", "B--", "D--"]),
        ("C7(b9)", ["C", "E", "G", "B-", "D-"]),
        ("C6/9", ["C", "E", "G", "A", "D"]),
        ("Cm(maj7)", ["C", "E-", "G", "B"]),
        ("CΔ", ["C", "E", "G", "B"]),
        ("Cmaj9", ["C", "E", "G", "B", "D"]),
        ("Cø", ["C", "E-", "G-", "B-"]),
        ("C°7", ["C", "E-", "G-", "B--"]),
        ("A/C#", ["C#", "E", "A"]),
        ("Bb/D", ["D", "F", "B-"]),
    ],
)
def test_parse_chord_symbol(text, expected):
    assert [p.name for p in parse_chord_symbol(text).pitches] == expected


@pytest.mark.parametrize("text", ["am7", "Cxyz", "", "C9sus4", "7"])
def test_parse_chord_symbol_rejects_bad_input(text):
    with pytest.raises(ToolError):
        parse_chord_symbol(text)


@pytest.mark.parametrize(
    "text, tonic, mode",
    [
        ("C", "C", "major"),
        ("a", "A", "minor"),
        ("Bb", "B-", "major"),
        ("bb", "B-", "minor"),
        ("Bb major", "B-", "major"),
        ("F#m", "F#", "minor"),
        ("F# minor", "F#", "minor"),
        ("c# Minor", "C#", "minor"),
        ("D dorian", "D", "dorian"),
        ("EbM", "E-", "major"),
    ],
)
def test_parse_key(text, tonic, mode):
    k = parse_key(text)
    assert (k.tonic.name, k.mode) == (tonic, mode)


@pytest.mark.parametrize("text", ["H major", "C blues", "", "C#b"])
def test_parse_key_rejects_bad_input(text):
    with pytest.raises(ToolError):
        parse_key(text)


@pytest.mark.parametrize(
    "value, name, semitones",
    [
        ("M3", "M3", 4),
        ("-P5", "P5", -7),
        ("+m7", "m7", 10),
        ("maj3", "M3", 4),
        ("aug4", "A4", 6),
        ("dim5", "d5", 6),
        ("M9", "M9", 14),
        (7, "P5", 7),
        ("-2", "M2", -2),
    ],
)
def test_parse_interval(value, name, semitones):
    i = parse_interval(value)
    assert (i.name, i.semitones) == (name, semitones)


@pytest.mark.parametrize("value", ["P3", "M5", "x3", "third", ""])
def test_parse_interval_rejects_bad_input(value):
    with pytest.raises(ToolError, match="Invalid interval"):
        parse_interval(value)


@pytest.mark.parametrize("figure", ["V7", "ii65", "viio7", "iiø7", "V7/V", "bVI", "It+6", "Ger65", "N6", "Cad64"])
def test_parse_roman_accepts(figure):
    assert parse_roman(figure, parse_key("C")).pitches


@pytest.mark.parametrize("figure", ["VIIIx", "IIII", "X", "V7/", "hello"])
def test_parse_roman_rejects(figure):
    with pytest.raises(ToolError, match="Invalid Roman numeral"):
        parse_roman(figure, parse_key("C"))


def test_display():
    assert display("B-4") == "Bb4"
    assert display("E--") == "Ebb"
    assert display("B-7/E-") == "Bb7/Eb"
    assert display_key(parse_key("f#")) == "F# minor"
