"""End-to-end checks through the MCP protocol using an in-memory client."""

import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from music_theory_mcp.server import mcp

EXPECTED_TOOLS = {
    "note_info",
    "interval_between",
    "transpose_notes",
    "chord_from_symbol",
    "identify_chord",
    "transpose_chords",
    "scale_notes",
    "key_info",
    "scale_degree",
    "roman_numeral_to_chord",
    "diatonic_chords",
    "analyze_progression",
    "detect_key",
    "check_voice_leading",
}


async def _list_tools():
    async with Client(mcp) as client:
        return await client.list_tools()


async def _call(name: str, arguments: dict):
    async with Client(mcp) as client:
        return await client.call_tool(name, arguments)


def test_all_tools_registered_with_docs():
    tools = asyncio.run(_list_tools())
    assert {t.name for t in tools} == EXPECTED_TOOLS
    assert all("Examples:" in t.description for t in tools)


def test_call_returns_structured_result():
    result = asyncio.run(_call("chord_from_symbol", {"symbol": "Bbmaj7"}))
    assert result.data["notes"] == ["Bb", "D", "F", "A"]


def test_semitone_interval_accepted_over_protocol():
    result = asyncio.run(_call("transpose_notes", {"notes": ["C4"], "interval": 7}))
    assert result.data["notes"] == ["G4"]


def test_bad_input_returns_readable_error():
    with pytest.raises(ToolError, match="Invalid note 'H'"):
        asyncio.run(_call("note_info", {"note": "H"}))


def test_schema_rejects_unknown_scale_type():
    with pytest.raises(ToolError):
        asyncio.run(_call("scale_notes", {"tonic": "C", "scale_type": "bebop"}))
