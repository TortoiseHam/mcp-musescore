"""Sequence processing tools for MuseScore MCP."""

from mcp.server.fastmcp import FastMCP

from ..client import MuseScoreClient
from ..types import ActionSequence


def setup_sequence_tools(mcp: FastMCP, client: MuseScoreClient) -> None:
    """Setup sequence processing tools."""

    @mcp.tool()
    async def processSequence(sequence: ActionSequence):
        """Process a sequence of commands."""
        return await client.send_command("processSequence", {"sequence": sequence})
