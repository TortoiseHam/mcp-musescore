"""Connection and utility tools for MuseScore MCP."""

from typing import List, Optional
from ..client import MuseScoreClient


def setup_connection_tools(mcp, client: MuseScoreClient):
    """Setup connection and utility tools."""

    @mcp.tool()
    async def connect_to_musescore():
        """Connect to the MuseScore WebSocket API."""
        result = await client.connect()
        return {"success": result}

    @mcp.tool()
    async def ping_musescore():
        """Ping the MuseScore WebSocket API to check connection."""
        return await client.send_command("ping")

    @mcp.tool()
    async def get_score(start_measure: Optional[int] = None, end_measure: Optional[int] = None, staves: Optional[List[int]] = None):
        """Get information about the current score, optionally filtered.

        Args:
            start_measure: First measure to include (1-based, default all)
            end_measure: Last measure to include (1-based, must be >= start_measure)
            staves: List of staff indices to include (0-based, default all)

        Returns:
            analysis: Score summary object with:
                - numMeasures: Total number of measures in the score
                - measures: List of measure objects, each with:
                    - measure: Measure number (1-based)
                    - startTick: Tick position of measure start
                    - numElements: Count of elements in this measure
                    - elements: Dict keyed by "staff0", "staff1", etc., each a list of elements
                - staves: List of staff objects with name, shortName, visible
        """
        if start_measure is not None and start_measure < 1:
            return {"error": "start_measure must be >= 1"}
        if end_measure is not None:
            if end_measure < 1:
                return {"error": "end_measure must be >= 1"}
            if start_measure is not None and end_measure < start_measure:
                return {"error": "end_measure must be >= start_measure"}
        if staves is not None:
            for s in staves:
                if s < 0:
                    return {"error": "Staff indices must be >= 0"}
        params = {}
        if start_measure is not None:
            params["startMeasure"] = start_measure
        if end_measure is not None:
            params["endMeasure"] = end_measure
        if staves is not None:
            params["staves"] = staves
        return await client.send_command("getScore", params)

    @mcp.tool()
    async def sync_state_to_selection():
        """Sync the plugin's internal state to the current selection in MuseScore."""
        return await client.send_command("syncStateToSelection")

    @mcp.tool()
    async def export_pdf(output_path: str = "/tmp/musescore-mcp/export.pdf"):
        """Export the current score to a PDF file.

        Args:
            output_path: File path for the exported PDF. Parent directory will be
                created if it doesn't exist. Defaults to /tmp/musescore-mcp/export.pdf.

        Returns:
            success: Whether the export succeeded
            path: The absolute path to the exported PDF file
        """
        import os
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return await client.send_command("exportPdf", {"outputPath": output_path})
