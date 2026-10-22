"""FastMCP server exposing music theory tools computed with music21."""

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from music21 import chord, harmony, interval, pitch

from music_theory_mcp.notation import display, parse_chord_symbol, parse_interval, parse_pitch

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


@mcp.tool
def chord_from_symbol(symbol: str) -> dict:
    """Spell out a lead-sheet chord symbol: its notes, root, bass and each tone's interval above the root.

    Supports triads, sixths, sevenths, extensions (9, 11, 13), alterations (b5, #5, b9, #9, #11, b13),
    add/sus chords and slash basses. Notes are listed bottom to top in close position.

    Examples: chord_from_symbol("F#m7b5"), chord_from_symbol("Bbmaj7"), chord_from_symbol("C7(b9)"),
    chord_from_symbol("D7/F#"), chord_from_symbol("Ebdim7"), chord_from_symbol("C6/9")
    """
    cs = parse_chord_symbol(symbol)
    root = cs.root()
    tones = []
    for p in cs.pitches:
        above = p
        while above.ps < root.ps:  # a slash bass can sit below the root
            above = above.transpose("P8")
        tones.append({"note": display(p.name), "interval": interval.Interval(root, above).name})
    return {
        "symbol": symbol,
        "notes": [display(p.name) for p in cs.pitches],
        "root": display(root.name),
        "bass": display(cs.bass().name),
        "kind": cs.chordKind,
        "chord_tones": tones,
    }


_INVERSION_NAMES = ["root position", "first inversion", "second inversion", "third inversion"]


def _voiced_pitches(notes: list[str]) -> list[pitch.Pitch]:
    """Parse notes listed bottom to top. If none has an octave, stack each one above the last."""
    pitches = [parse_pitch(n) for n in notes]
    if all(p.octave is None for p in pitches):
        previous = None
        for p in pitches:
            p.octave = 4
            while previous is not None and p.ps <= previous.ps:
                p.octave += 1
            previous = p
    elif any(p.octave is None for p in pitches):
        raise ToolError("Give octaves for all notes or for none of them.")
    return pitches


@mcp.tool
def identify_chord(notes: list[str]) -> dict:
    """Identify a chord from its notes: chord symbol, name, root, bass and inversion.

    List notes bottom to top. Without octaves they are stacked upward in the order given,
    so ["E", "G", "C"] is a first-inversion C major triad (C/E). With octaves, the lowest note is the bass.
    Inversion is only reported for triads and seventh chords. Forte class and prime form are
    included for post-tonal analysis.

    Examples: identify_chord(["E", "G", "C"]), identify_chord(["B3", "D4", "F4", "A4"]),
    identify_chord(["F#", "A#", "C#", "E"]), identify_chord(["C4", "E4", "G#4"])
    """
    if not notes:
        raise ToolError("Give at least one note.")
    c = chord.Chord(_voiced_pitches(notes))
    symbol = harmony.chordSymbolFigureFromChord(c)
    inversion = c.inversion() if c.isTriad() or c.isSeventh() else None
    return {
        "notes": [display(p.nameWithOctave) for p in c.pitches],
        "symbol": None if symbol == "Chord Symbol Cannot Be Identified" else display(symbol),
        "name": c.commonName,
        "root": display(c.root().name),
        "bass": display(c.bass().name),
        "inversion": None if inversion is None else _INVERSION_NAMES[inversion],
        "forte_class": c.forteClass,
        "prime_form": c.primeForm,
    }
