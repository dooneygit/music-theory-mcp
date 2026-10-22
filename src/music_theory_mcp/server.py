"""FastMCP server exposing music theory tools computed with music21."""

from fastmcp import FastMCP
from music21 import interval

from music_theory_mcp.notation import display, parse_interval, parse_pitch

mcp = FastMCP(
    "music-theory",
    instructions=(
        "Music theory calculator backed by music21. Use these tools instead of working out "
        "intervals, chord spellings, scales, keys or Roman numerals from memory. Inputs accept "
        "natural notation: notes like 'Bb4' or 'F#', chord symbols like 'F#m7b5', keys like "
        "'Eb major' or 'c# minor'."
    ),
)


@mcp.tool
def note_info(note: str) -> dict:
    """Get facts about one note: MIDI number, frequency, pitch class and enharmonic spellings.

    The octave defaults to 4 when omitted (middle C = C4 = MIDI 60; A4 = 440 Hz).

    Examples: note_info("Bb4"), note_info("F#"), note_info("Cb5"), note_info("E#3")
    """
    p = parse_pitch(note)
    if p.octave is None:
        p.octave = 4
    return {
        "note": display(p.nameWithOctave),
        "name": display(p.name),
        "octave": p.octave,
        "midi": p.midi,
        "frequency_hz": round(p.frequency, 2),
        "pitch_class": p.pitchClass,
        "enharmonics": [display(e.nameWithOctave) for e in p.getAllCommonEnharmonics()],
    }


_DIRECTIONS = {
    interval.Direction.ASCENDING: "ascending",
    interval.Direction.DESCENDING: "descending",
    interval.Direction.OBLIQUE: "unison",
}


@mcp.tool
def interval_between(note1: str, note2: str) -> dict:
    """Name the interval from note1 to note2 with correct spelling (C->F# is an augmented 4th, C->Gb a diminished 5th).

    Without octaves both notes are placed in octave 4, so ("G", "C") is a descending perfect 5th.
    Give octaves for an exact interval: ("G4", "C5") is an ascending perfect 4th.
    Consonance follows common-practice counterpoint, where the perfect 4th counts as dissonant.

    Examples: interval_between("C4", "Ab4"), interval_between("E", "Bb"), interval_between("C4", "D5")
    """
    start, end = parse_pitch(note1), parse_pitch(note2)
    i = interval.Interval(start, end)
    return {
        "from": display(start.nameWithOctave),
        "to": display(end.nameWithOctave),
        "name": i.name,
        "full_name": i.niceName,
        "direction": _DIRECTIONS[i.direction],
        "semitones": i.semitones,
        "simple_name": i.simpleName,
        "is_compound": i.generic.undirected > 8,
        "is_consonant": i.isConsonant(),
        "inversion": interval.Interval(i.simpleName).complement.name,
    }


@mcp.tool
def transpose_notes(notes: list[str], interval: str | int) -> dict:
    """Transpose notes by an interval, keeping correct enharmonic spelling (C# up a M3 is E#, not F).

    interval is a quality plus a number ("M3", "m7", "P5", "A4", "d5", "M9"), with a leading "-"
    for downward ("-P4"). A semitone count (7, -2) also works, but then music21 chooses the
    spelling, so prefer a named interval. Octaves are kept if given.

    Examples: transpose_notes(["C4", "E4", "G4"], "m3"), transpose_notes(["F#", "C#"], "-P5"),
    transpose_notes(["Bb"], 2)
    """
    step = parse_interval(interval)
    return {
        "interval": step.directedName,
        "notes": [display(parse_pitch(n).transpose(step).nameWithOctave) for n in notes],
    }
