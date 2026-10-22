# Music Theory MCP

An [FastMCP](https://gofastmcp.com) server to ground LLM music theory in deterministic symbolic computation via MIT's music21, addressing notoriously unreliable music theory from probabilistic LLM text generation.

Inputs accept natural notation (`Bb4`, `F#m7b5`, `Eb major`, `c# minor`); results come back as structured JSON in the same notation.

## Tools

| Tool | What it does |
|---|---|
| `note_info` | MIDI number, frequency, pitch class, enharmonics |
| `interval_between` | Correctly spelled interval between two notes |
| `transpose_notes` | Transpose notes, keeping correct spelling |
| `chord_from_symbol` | Spell a chord symbol (`F#m7b5`, `D7/F#`, `C6/9`) |
| `identify_chord` | Name a chord from its notes, with inversion |
| `transpose_chords` | Transpose a chord progression |
| `scale_notes` | Major, minor variants, modes, symmetric scales |
| `key_info` | Key signature, scale, relative and parallel keys |
| `scale_degree` | Scale degree of a note in a key (F in D major = b3) |
| `roman_numeral_to_chord` | Spell a Roman numeral in a key (`V65/V`, `Ger65`, `N6`) |
| `diatonic_chords` | Triads or sevenths on every degree of a key |
| `analyze_progression` | Roman numeral analysis, incl. secondary dominants |
| `detect_key` | Most likely key of a set of notes, with alternatives |
| `check_voice_leading` | Parallel/hidden fifths and octaves, crossing, overlap |

## Run

```sh
uv sync
uv run music-theory-mcp        # stdio transport
uv run pytest
```

To use it from an MCP client such as Claude Desktop:

```json
{
  "mcpServers": {
    "music-theory": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/music-theory-mcp", "music-theory-mcp"]
    }
  }
}
```
