"""Sequence processing tools for MuseScore MCP."""

from mcp.server.fastmcp import FastMCP

from ..client import MuseScoreClient
from ..pitch import parse_pitch
from ..types import ActionSequence


def setup_sequence_tools(mcp: FastMCP, client: MuseScoreClient) -> None:
    """Setup sequence processing tools."""

    @mcp.tool()
    async def processSequence(sequence: ActionSequence):
        """Process a sequence of commands."""
        # Preprocess: convert string pitches to MIDI integers for addNote actions
        for item in sequence:
            if item.get("action") == "addNote" and "params" in item:
                params = item["params"]
                if "pitch" in params and isinstance(params["pitch"], str):
                    try:
                        params["pitch"] = parse_pitch(params["pitch"])
                    except (ValueError, TypeError) as e:
                        return {"error": f"Invalid pitch in sequence: {e}"}
        return await client.send_command("processSequence", {"sequence": sequence})
