"""Convert natural music notation (e.g. "Bb", "F#m7b5") to music21 objects and back.

music21 writes flats as "-" ("B-"), so "Bb" must be converted before parsing.
Worse, some inputs are silently misread rather than rejected (music21 reads
"Bb7b9#11" as a B chord), so everything goes through these helpers. Invalid
input raises ToolError with a message the calling LLM can act on.
"""

import re

from fastmcp.exceptions import ToolError
from music21 import harmony, interval, key, pitch, roman

_UNICODE_ACCIDENTALS = {"♭": "b", "♯": "#", "𝄪": "x", "𝄫": "bb", "♮": ""}

_PITCH_RE = re.compile(r"^([A-Ga-g])([#bx\-]*)(\d+)?$")
_CHORD_RE = re.compile(r"^([A-G])([#b]{0,2})(.*?)(?:/([A-G][#b]{0,2}))?$")
_KEY_RE = re.compile(r"^([A-Ga-g])([#bx\-]*)\s*(.*)$")
_INTERVAL_RE = re.compile(r"^([+-]?)(P|M|m|A+|d+)(\d+)$")

_MODES = {
    "": None,  # decided by the case of the tonic letter
    "m": "minor", "min": "minor", "minor": "minor",
    "M": "major", "maj": "major", "major": "major",
    "ionian": "ionian", "dorian": "dorian", "phrygian": "phrygian",
    "lydian": "lydian", "mixolydian": "mixolydian", "aeolian": "aeolian",
    "locrian": "locrian",
}

# Common chord-quality spellings music21 doesn't accept, mapped to ones it does.
# Applied in order, after parentheses and commas are stripped.
_QUALITY_ALIASES = [
    (r"^(m|min)(maj|M|Δ)7", "mM7"),
    (r"^Δ$", "maj7"),
    (r"^Δ", "maj"),
    (r"^maj(9|11|13)", r"M\1"),
    (r"^(m?)6/?9$", r"\g<1>6add9"),
    (r"^ø$", "ø7"),
    (r"^m7(b|-)5", "ø7"),  # music21 would call m7b5 an altered minor seventh
    (r"°", "o"),
]

_ROMAN_DEGREE = r"[b#\-]*(?:VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)"
_ROMAN_FIGURE = r"(?:[o°ø+]|/o)?(?:[#b\-]?\d+)*"
_ROMAN_RE = re.compile(
    rf"^(?:(?:It|Ger|Fr|Sw)\+?\d*|N\d*|Cad64"
    rf"|{_ROMAN_DEGREE}{_ROMAN_FIGURE}(?:/{_ROMAN_DEGREE}{_ROMAN_FIGURE})*)$"
)


def _clean(text: str) -> str:
    text = text.strip()
    for symbol, ascii_symbol in _UNICODE_ACCIDENTALS.items():
        text = text.replace(symbol, ascii_symbol)
    return text


def _m21_accidental(accidental: str) -> str:
    """Convert a natural accidental string ("b", "bb", "#", "x") to music21's ("-", "--", "#", "##")."""
    if set(accidental) <= {"b", "-"}:
        return "-" * len(accidental)
    if set(accidental) <= {"#", "x"}:
        return accidental.replace("x", "##")
    raise ValueError(accidental)


def parse_pitch(text: str) -> pitch.Pitch:
    """Parse "C", "Bb4", "f#3", "Ebb", "Cx", "B-4" (music21 style) into a Pitch."""
    match = _PITCH_RE.match(_clean(text))
    if not match:
        raise ToolError(
            f"Invalid note {text!r}. Use a letter A-G, optional accidentals "
            "(# or b, x for double sharp), and an optional octave, e.g. 'C', 'Bb4', 'F#3'."
        )
    letter, accidental, octave = match.groups()
    try:
        name = letter.upper() + _m21_accidental(accidental) + (octave or "")
    except ValueError:
        raise ToolError(f"Invalid note {text!r}: cannot mix sharps and flats.") from None
    if len(name.rstrip("0123456789")) > 3:
        raise ToolError(f"Invalid note {text!r}: too many accidentals.")
    return pitch.Pitch(name)


def split_chord_symbol(text: str) -> tuple[str, str, str | None]:
    """Split "Bbm7/F" into root "Bb", quality "m7" and bass "F" (None without a slash bass)."""
    match = _CHORD_RE.match(_clean(text))
    if not match:
        raise ToolError(
            f"Invalid chord symbol {text!r}. It must start with an uppercase root A-G, "
            "e.g. 'C', 'Bbmaj7', 'F#m7b5', 'D7/F#'."
        )
    root, root_accidental, quality, bass = match.groups()
    return root + root_accidental, quality, bass


def parse_chord_symbol(text: str) -> harmony.ChordSymbol:
    """Parse a lead-sheet chord symbol like "F#m7b5", "Bbmaj7", "C7(b9)", "A/C#", "C6/9"."""
    root, quality, bass = split_chord_symbol(text)
    quality = re.sub(r"[(),\s]", "", quality)
    for pattern, replacement in _QUALITY_ALIASES:
        quality = re.sub(pattern, replacement, quality)
    figure = parse_pitch(root).name + quality
    if bass:
        figure += "/" + parse_pitch(bass).name
    try:
        symbol = harmony.ChordSymbol(figure)
    except Exception:
        raise ToolError(
            f"Unrecognized chord symbol {text!r}. Supported qualities include: "
            "'' (major), m, dim, aug/+, sus2, sus4, 5, 6, m6, 6/9, 7, maj7, m7, mM7, "
            "m7b5/ø7, dim7/o7, 7sus4, 9, maj9, m9, 11, m11, 13, maj13, m13, "
            "plus alterations like b5, #5, b9, #9, #11, b13 and add9."
        ) from None
    if symbol.root().name != parse_pitch(root).name or not symbol.pitches:
        raise ToolError(f"Could not interpret chord symbol {text!r}.")
    return symbol


def parse_key(text: str) -> key.Key:
    """Parse "C", "Bb major", "bb", "F#m", "C# minor", "D dorian" into a Key.

    A bare tonic is major if uppercase and minor if lowercase ("a" = A minor).
    """
    match = _KEY_RE.match(_clean(text))
    mode_word = match.group(3).strip() if match else ""
    if mode_word not in _MODES:
        mode_word = mode_word.lower()
    if not match or mode_word not in _MODES:
        raise ToolError(
            f"Invalid key {text!r}. Use a tonic plus optional mode, e.g. 'C', 'Bb major', "
            "'F#m', 'c# minor', 'D dorian'. A bare lowercase tonic means minor."
        )
    letter, accidental, _ = match.groups()
    tonic = parse_pitch(letter + accidental).name
    mode = _MODES[mode_word] or ("major" if letter.isupper() else "minor")
    return key.Key(tonic, mode)


def parse_interval(value: str | int) -> interval.Interval:
    """Parse "M3", "-P5", "m10", "A4", "d5", "maj3", "aug4" or a semitone count like 7 or -2."""
    if isinstance(value, int):
        return interval.Interval(value)
    text = value.strip()
    if re.fullmatch(r"[+-]?\d+", text):
        return interval.Interval(int(text))
    for word, symbol in (("perf", "P"), ("maj", "M"), ("min", "m"), ("aug", "A"), ("dim", "d")):
        text = re.sub(rf"(?i)^([+-]?){word}", rf"\g<1>{symbol}", text)
    match = _INTERVAL_RE.match(text)
    if match:
        sign, quality, number = match.groups()
        try:
            return interval.Interval(("-" if sign == "-" else "") + quality + number)
        except Exception:
            pass
    raise ToolError(
        f"Invalid interval {value!r}. Use quality + number, e.g. 'M3', 'm7', 'P5', "
        "'A4', 'd5', 'M9'; prefix '-' to go down ('-P4'); or a semitone count (7, -2). "
        "Unisons, 4ths, 5ths and octaves are perfect (P); 2nds, 3rds, 6ths and 7ths are major/minor."
    )


def parse_roman(figure: str, tonality: key.Key) -> roman.RomanNumeral:
    """Parse a Roman numeral like "V7", "ii65", "viio7", "V7/V", "bVI", "It+6", "N6", "Cad64"."""
    cleaned = figure.strip()
    if not _ROMAN_RE.match(cleaned):
        raise ToolError(
            f"Invalid Roman numeral {figure!r}. Use I-VII (uppercase major, lowercase minor), "
            "optional quality (o, ø, +), inversion figures (6, 64, 7, 65, 43, 42), "
            "secondary chords with '/', e.g. 'V7', 'ii65', 'viio7', 'V7/V', 'bVI', 'It+6', 'N6'."
        )
    return roman.RomanNumeral(cleaned, tonality)


def display(name: str) -> str:
    """Render a music21 pitch name or chord figure in natural notation ("B-4" -> "Bb4")."""
    return re.sub(r"(?<=[A-G])-+", lambda m: "b" * len(m.group()), name)


def display_key(tonality: key.Key) -> str:
    """Render a Key as e.g. "Bb major" or "F# minor"."""
    return f"{display(tonality.tonic.name)} {tonality.mode}"
