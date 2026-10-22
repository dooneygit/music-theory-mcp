"""FastMCP server exposing music theory tools computed with music21."""

from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from music21 import chord, harmony, interval, pitch, scale
from music21 import key as m21key
from music21.scale.intervalNetwork import Direction

from music_theory_mcp.notation import (
    display,
    display_key,
    parse_chord_symbol,
    parse_interval,
    parse_key,
    parse_pitch,
    parse_roman,
    split_chord_symbol,
)
from music_theory_mcp.roman_analysis import roman_label

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
    return {
        "notes": [display(p.nameWithOctave) for p in c.pitches],
        "symbol": _chord_symbol(c),
        "name": c.commonName,
        "root": display(c.root().name),
        "bass": display(c.bass().name),
        "inversion": _inversion_name(c),
        "forte_class": c.forteClass,
        "prime_form": c.primeForm,
    }


@mcp.tool
def transpose_chords(chords: list[str], interval: str | int) -> dict:
    """Transpose chord symbols by an interval, keeping each chord's quality and slash bass.

    interval is a quality plus a number ("M2", "P4", "m3"), with a leading "-" for downward ("-M2").
    A semitone count (5, -3) also works, but then music21 chooses the spelling, so prefer a named
    interval. To move from one key to another, use the interval between the tonics
    (C major to Eb major is "m3").

    Examples: transpose_chords(["C", "Am", "F", "G7"], "M2"), transpose_chords(["Bbmaj7", "Eb7", "D7/F#"], "-m3"),
    transpose_chords(["F#m7b5", "B7b9", "Em"], "P4")
    """
    step = parse_interval(interval)
    transposed = []
    for symbol in chords:
        parse_chord_symbol(symbol)  # reject invalid symbols before rebuilding them
        root, quality, bass = split_chord_symbol(symbol)
        new_symbol = display(parse_pitch(root).transpose(step).name) + quality
        if bass:
            new_symbol += "/" + display(parse_pitch(bass).transpose(step).name)
        transposed.append(new_symbol)
    return {"interval": step.directedName, "chords": transposed}


_SCALES = {
    "major": scale.MajorScale,
    "natural minor": scale.MinorScale,
    "harmonic minor": scale.HarmonicMinorScale,
    "melodic minor": scale.MelodicMinorScale,
    "dorian": scale.DorianScale,
    "phrygian": scale.PhrygianScale,
    "lydian": scale.LydianScale,
    "mixolydian": scale.MixolydianScale,
    "locrian": scale.LocrianScale,
    "whole tone": scale.WholeToneScale,
    "chromatic": scale.ChromaticScale,
    "octatonic whole-half": scale.OctatonicScale,
    "octatonic half-whole": lambda tonic: scale.OctatonicScale(tonic, mode=1),
}

ScaleType = Literal[
    "major", "natural minor", "harmonic minor", "melodic minor", "dorian", "phrygian", "lydian",
    "mixolydian", "locrian", "whole tone", "chromatic", "octatonic whole-half", "octatonic half-whole",
]


@mcp.tool
def scale_notes(
    tonic: str, scale_type: ScaleType = "major", direction: Literal["ascending", "descending"] = "ascending"
) -> dict:
    """List the notes of a scale over one octave, tonic to tonic, correctly spelled.

    Melodic minor differs by direction: ascending raises 6 and 7, descending is natural minor.
    Ionian = major and aeolian = natural minor. Symmetric scales (whole tone, chromatic,
    octatonic) have no single correct spelling, so music21's spelling is used.

    Examples: scale_notes("F#", "major"), scale_notes("Bb", "harmonic minor"),
    scale_notes("A", "melodic minor", "descending"), scale_notes("D", "dorian")
    """
    tonic_pitch = parse_pitch(tonic)
    tonic_pitch.octave = 4
    sc = _SCALES[scale_type](tonic_pitch)
    pitches = sc.getPitches(
        tonic_pitch,
        tonic_pitch.transpose("P8"),
        direction=Direction.ASCENDING if direction == "ascending" else Direction.DESCENDING,
    )
    notes = [display(p.name) for p in pitches]
    # music21 sometimes respells the octave in symmetric scales (B# for C)
    notes[-1 if direction == "ascending" else 0] = display(tonic_pitch.name)
    return {"tonic": display(tonic_pitch.name), "scale": scale_type, "direction": direction, "notes": notes}


@mcp.tool
def key_info(key: str) -> dict:
    """Get a key's signature, scale, relative key and parallel key.

    A bare tonic is major if uppercase and minor if lowercase ("a" = A minor), or name the mode:
    "Bb major", "F#m", "c# minor". Church modes also work ("D dorian"); their relative key is the
    major key with the same signature. Signature accidentals are listed in standard order.

    Examples: key_info("Eb"), key_info("F# minor"), key_info("c#"), key_info("D dorian")
    """
    k = parse_key(key)
    relative_mode = "minor" if k.mode == "major" else "major"
    return {
        "key": display_key(k),
        "signature": {
            "sharps": max(k.sharps, 0),
            "flats": max(-k.sharps, 0),
            "accidentals": [display(p.name) for p in k.alteredPitches],
        },
        "scale": [display(p.name) for p in k.pitches],
        "relative": display_key(m21key.KeySignature(k.sharps).asKey(relative_mode)),
        "parallel": display_key(m21key.Key(k.tonic.name, relative_mode)),
    }


_DEGREE_NAMES = ["tonic", "supertonic", "mediant", "subdominant", "dominant", "submediant"]


@mcp.tool
def scale_degree(note: str, key: str) -> dict:
    """Find which scale degree a note is in a key, including chromatic notes (F in D major is b3).

    Minor keys are measured against natural minor, so the leading tone of A minor (G#) is "#7".
    Degree 7 is named "leading tone" when a half step below the tonic and "subtonic" when a whole step.

    Examples: scale_degree("F#", "D"), scale_degree("F", "D major"), scale_degree("G#", "a minor"),
    scale_degree("Db", "C")
    """
    p = parse_pitch(note)
    k = parse_key(key)
    degree, accidental = k.getScaleDegreeAndAccidentalFromPitch(p)
    alteration = accidental.modifier.replace("-", "b") if accidental else ""
    if degree == 7:
        half_steps_below_tonic = (k.tonic.pitchClass - p.pitchClass) % 12
        degree_name = "leading tone" if half_steps_below_tonic == 1 else "subtonic"
    else:
        degree_name = _DEGREE_NAMES[degree - 1]
    return {
        "note": display(p.name),
        "key": display_key(k),
        "degree": degree,
        "alteration": alteration,
        "label": f"{alteration}{degree}",
        "degree_name": degree_name,
        "in_key": not alteration,
    }


def _inversion_name(c: chord.Chord) -> str | None:
    """Name the inversion of a triad or seventh chord; None for other chords."""
    return _INVERSION_NAMES[c.inversion()] if c.isTriad() or c.isSeventh() else None


def _chord_symbol(c: chord.Chord) -> str | None:
    symbol = harmony.chordSymbolFigureFromChord(c)
    return None if symbol == "Chord Symbol Cannot Be Identified" else display(symbol)


@mcp.tool
def roman_numeral_to_chord(numeral: str, key: str) -> dict:
    """Spell the chord a Roman numeral stands for in a key, with its bass, inversion and chord symbol.

    Uppercase = major, lowercase = minor; "o" = diminished, "ø" (or "/o") = half-diminished,
    "+" = augmented. Figured-bass inversions: 6, 64 (triads); 7, 65, 43, 42 (sevenths).
    Secondary chords use "/" ("V7/V"). Also supports b/# prefixes ("bVI"), augmented sixths
    ("It+6", "Fr43", "Ger65"), Neapolitan ("N6") and cadential 6/4 ("Cad64"). In minor keys,
    V and viio use the raised leading tone. b/# alter the key's own scale degree: in C minor VI is
    already Ab major, so "bVI" is for borrowed chords in major. Notes are listed bottom to top.

    Examples: roman_numeral_to_chord("V65/V", "C"), roman_numeral_to_chord("viio7", "a minor"),
    roman_numeral_to_chord("bVI", "C"), roman_numeral_to_chord("Ger65", "C"), roman_numeral_to_chord("ii42", "Eb")
    """
    k = parse_key(key)
    rn = parse_roman(numeral, k)
    secondary_key = rn.secondaryRomanNumeralKey
    return {
        "numeral": numeral,
        "key": display_key(k),
        "notes": [display(p.name) for p in rn.pitches],
        "root": display(rn.root().name),
        "bass": display(rn.bass().name),
        "inversion": _inversion_name(rn),
        "name": rn.commonName,
        "symbol": _chord_symbol(chord.Chord(rn.pitches)),
        "tonicized_key": display_key(secondary_key) if secondary_key else None,
    }


_MODE_SCALES = {"ionian": "major", "aeolian": "natural minor"}


@mcp.tool
def diatonic_chords(
    key: str, sevenths: bool = False, minor_variant: Literal["natural", "harmonic", "melodic"] = "harmonic"
) -> dict:
    """List the chord built on each scale degree of a key, with Roman numeral, chord symbol and notes.

    Set sevenths=True for seventh chords instead of triads. For minor keys, minor_variant picks the
    scale the chords are built from: "harmonic" (default; raised 7th, giving V and viio as in
    common-practice harmony), "natural" or "melodic" (ascending). It is ignored for other keys.

    Examples: diatonic_chords("C"), diatonic_chords("Bb", sevenths=True), diatonic_chords("e minor"),
    diatonic_chords("a", minor_variant="natural"), diatonic_chords("D dorian")
    """
    k = parse_key(key)
    scale_type = f"{minor_variant} minor" if k.mode == "minor" else _MODE_SCALES.get(k.mode, k.mode)
    tonic = pitch.Pitch(k.tonic.name + "4")
    pitches = _SCALES[scale_type](tonic).getPitches(tonic, tonic.transpose("P15"), direction=Direction.ASCENDING)
    chords = []
    for degree in range(7):
        c = chord.Chord([pitches[degree + 2 * step] for step in range(4 if sevenths else 3)])
        chords.append({
            "degree": degree + 1,
            "numeral": roman_label(c, k),
            "symbol": _chord_symbol(c),
            "notes": [display(p.name) for p in c.pitches],
            "name": c.commonName,
        })
    return {"key": display_key(k), "scale": scale_type, "chords": chords}


@mcp.tool
def analyze_progression(chords: list[str], key: str) -> dict:
    """Label each chord symbol of a progression with its Roman numeral in a key.

    Recognizes secondary dominants and leading-tone chords (D7 in C is "V7/V", F#dim7 in C is
    "viio7/V"), borrowed and chromatic chords ("iv", "bVI", "bII6" in major), and inversions from
    slash basses (C/E is "I6"). Minor keys treat the raised 6th and 7th as diatonic, so E7 in
    A minor is "V7". Chords other than triads and sevenths get music21's label.

    Examples: analyze_progression(["C", "Am", "Dm7", "G7", "C"], "C"),
    analyze_progression(["Am", "D7/F#", "G", "E7", "Am"], "a minor"),
    analyze_progression(["Bbmaj7", "Gm7", "C7", "F"], "F")
    """
    k = parse_key(key)
    analysis = []
    for symbol in chords:
        c = chord.Chord(parse_chord_symbol(symbol).pitches)
        analysis.append({"chord": symbol, "numeral": roman_label(c, k), "notes": [display(p.name) for p in c.pitches]})
    return {"key": display_key(k), "chords": analysis}
