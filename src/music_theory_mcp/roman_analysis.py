"""Label chords with Roman numerals in a key.

music21's romanNumeralFromChord mislabels common cases: with preferSecondaryDominants=True it
calls the tonic of C major "V/IV", and without it E7 in A minor becomes "V75#3". So triads and
seventh chords are labeled here from music21's own analysis (root, triad quality, seventh,
inversion); other chords fall back to music21.
"""

from music21 import chord, key, roman

_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII"]
_TRIAD_FIGURES = ["", "6", "64"]
_SEVENTH_FIGURES = ["7", "65", "43", "42"]
_SEVENTHS = {9: "d7", 10: "m7", 11: "M7"}  # semitones above the root

# (triad quality, seventh above the root) combinations this module labels itself
_SUPPORTED = {
    ("major", None), ("major", "M7"), ("major", "m7"),
    ("minor", None), ("minor", "m7"),
    ("diminished", None), ("diminished", "m7"), ("diminished", "d7"),
    ("augmented", None), ("augmented", "M7"),
}


def _diatonic_names(k: key.Key) -> set[str]:
    """Note names belonging to the key; minor also allows the raised 6th and 7th."""
    names = {p.name for p in k.pitches}
    if k.mode == "minor":
        names |= {k.pitches[5].transpose("A1").name, k.pitches[6].transpose("A1").name}
    return names


def _numeral(degree: int, accidental: str, triad: str, seventh: str | None, inversion: int) -> str:
    numeral = _NUMERALS[degree - 1]
    if triad in ("minor", "diminished"):
        numeral = numeral.lower()
    if triad == "diminished":
        quality = "ø" if seventh == "m7" else "o"
    elif triad == "augmented":
        quality = "+"
    else:
        quality = ""
    figures = _SEVENTH_FIGURES if seventh else _TRIAD_FIGURES
    return accidental + numeral + quality + figures[inversion]


def _tonicized_numeral(k: key.Key, target_root) -> str | None:
    """Numeral for the key-area a secondary chord points to, or None if it can't be tonicized."""
    scale_names = [p.name for p in k.pitches[:7]]
    if target_root.name not in scale_names:
        return None
    degree = scale_names.index(target_root.name) + 1
    if k.mode == "minor" and degree == 5:
        return "V"
    triad = chord.Chord([scale_names[(degree - 1 + step) % 7] for step in (0, 2, 4)]).quality
    if triad == "diminished":
        return None
    return _NUMERALS[degree - 1] if triad == "major" else _NUMERALS[degree - 1].lower()


def roman_label(c: chord.Chord, k: key.Key) -> str:
    """Roman numeral for a chord in a key, e.g. "V7", "ii65", "V7/V", "viio7/vi", "bVI", "iv"."""
    seventh = _SEVENTHS.get(c.semitonesFromChordStep(7)) if c.isSeventh() else None
    if not (c.isTriad() or c.isSeventh()) or (c.quality, seventh) not in _SUPPORTED:
        return roman.romanNumeralFromChord(c, k).figure
    triad, inversion = c.quality, c.inversion()
    degree, accidental = k.getScaleDegreeAndAccidentalFromPitch(c.root())

    if all(p.name in _diatonic_names(k) for p in c.pitches):
        return _numeral(degree, "", triad, seventh, inversion)

    # Secondary dominants and leading-tone chords
    if triad == "major" and seventh in (None, "m7"):
        function, target_root = 5, c.root().transpose("P4")
    elif triad == "diminished":
        function, target_root = 7, c.root().transpose("m2")
    else:
        function = target_root = None
    if function:
        if target_root.name == k.tonic.name:  # e.g. viio7 borrowed from minor in a major key
            return _numeral(function, "", triad, seventh, inversion)
        target = _tonicized_numeral(k, target_root)
        if target:
            return _numeral(function, "", triad, seventh, inversion) + "/" + target

    alteration = accidental.modifier.replace("-", "b") if accidental else ""
    return _numeral(degree, alteration, triad, seventh, inversion)
