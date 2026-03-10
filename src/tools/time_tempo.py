"""Time signature and tempo tools for MuseScore MCP."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import MuseScoreClient


def setup_time_tempo_tools(mcp: FastMCP, client: MuseScoreClient) -> None:
    """Setup time signature and tempo tools."""

    @mcp.tool()
    async def set_time_signature(numerator: int = 4, denominator: int = 4):
        """Set the time signature.

        Args:
            numerator: Top number of time signature (beats per measure)
            denominator: Bottom number of time signature (note value that gets the beat)
        """
        if numerator < 1:
            return {"error": "Numerator must be >= 1"}
        if denominator < 1:
            return {"error": "Denominator must be >= 1"}
        return await client.send_command("setTimeSignature", {
            "numerator": numerator,
            "denominator": denominator
        })

    @mcp.tool()
    async def set_tempo(bpm: float, text: str | None = None):
        """Set the tempo in beats per minute.

        Args:
            bpm: Tempo in beats per minute (must be > 0)
            text: Custom tempo text (e.g. "Allegro"). If not provided, defaults to "♩ = {bpm}".

        Returns:
            success: Whether the tempo was set
            message: Confirmation with BPM value
        """
        if bpm <= 0:
            return {"error": "BPM must be greater than 0"}
        params: dict[str, Any] = {"bpm": bpm}
        if text is not None:
            params["text"] = text
        return await client.send_command("setTempo", params)
