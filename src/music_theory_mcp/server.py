"""FastMCP server exposing music theory tools computed with music21."""

from fastmcp import FastMCP

from music_theory_mcp.notation import display, parse_pitch

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
