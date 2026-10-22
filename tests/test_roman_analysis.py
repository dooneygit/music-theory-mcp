import pytest
from music21 import chord

from music_theory_mcp.notation import parse_chord_symbol, parse_key
from music_theory_mcp.roman_analysis import roman_label


@pytest.mark.parametrize(
    "symbol, key, expected",
    [
        ("C", "C", "I"),
        ("Dm", "C", "ii"),
        ("G7", "C", "V7"),
        ("Bm7b5", "C", "viiø7"),
        ("Fmaj7", "C", "IV7"),
        ("C/E", "C", "I6"),
        ("G/D", "C", "V64"),
        ("D7/F#", "C", "V65/V"),
        ("D7", "C", "V7/V"),
        ("E7", "C", "V7/vi"),
        ("C7", "C", "V7/IV"),
        ("A7", "C", "V7/ii"),
        ("F#dim7", "C", "viio7/V"),
        ("Bdim7", "C", "viio7"),
        ("Fm", "C", "iv"),
        ("Ab", "C", "bVI"),
        ("Bb", "C", "bVII"),
        ("Caug", "C", "I+"),
        ("Am", "a", "i"),
        ("E7", "a", "V7"),
        ("E", "a", "V"),
        ("G#dim7", "a", "viio7"),
        ("F", "a", "VI"),
        ("C", "a", "III"),
        ("B7", "a", "V7/V"),
        ("A7", "a", "V7/iv"),
        ("Bb/D", "a", "bII6"),
        ("Bm7b5", "a", "iiø7"),
    ],
)
def test_roman_label(symbol, key, expected):
    c = chord.Chord(parse_chord_symbol(symbol).pitches)
    assert roman_label(c, parse_key(key)) == expected


def test_roman_label_falls_back_to_music21_for_other_chords():
    c = chord.Chord(parse_chord_symbol("Csus4").pitches)
    assert roman_label(c, parse_key("C"))
