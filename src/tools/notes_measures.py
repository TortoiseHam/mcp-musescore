"""Notes and measures tools for MuseScore MCP."""

from mcp.server.fastmcp import FastMCP

from ..client import MuseScoreClient


def _validate_duration(duration: dict[str, int]) -> str | None:
    """Validate a duration dict has required keys and valid values."""
    if "numerator" not in duration or "denominator" not in duration:
        return "Duration must contain 'numerator' and 'denominator' keys"
    if duration["numerator"] < 1:
        return "Duration numerator must be >= 1"
    if duration["denominator"] < 1:
        return "Duration denominator must be >= 1"
    return None


def setup_notes_measures_tools(mcp: FastMCP, client: MuseScoreClient) -> None:
    """Setup notes and measures tools."""

    @mcp.tool()
    async def add_note(pitch: int = 64, duration: dict[str, int] | None = None, advance_cursor_after_action: bool = True):
        """Add a note at the current cursor position with the specified pitch and duration.

        Args:
            pitch: MIDI pitch value (0-127, where 60 is middle C)
            duration: Duration as {"numerator": int, "denominator": int} (e.g., {"numerator": 1, "denominator": 4} for quarter note)
            advance_cursor_after_action: Whether to move cursor to next position after adding note

        Returns:
            currentSelection: Updated selection state at the new cursor position with:
                - startStaff, endStaff, startTick
                - elements: The element at cursor after the operation
                - totalDuration: Duration in ticks
        """
        if duration is None:
            duration = {"numerator": 1, "denominator": 4}
        if not 0 <= pitch <= 127:
            return {"error": "Pitch must be between 0 and 127"}
        err = _validate_duration(duration)
        if err:
            return {"error": err}
        return await client.send_command("addNote", {
            "pitch": pitch,
            "duration": duration,
            "advanceCursorAfterAction": advance_cursor_after_action
        })

    @mcp.tool()
    async def add_rest(duration: dict[str, int] | None = None, advance_cursor_after_action: bool = True):
        """Add a rest at the current cursor position.

        Args:
            duration: Duration as {"numerator": int, "denominator": int} (e.g., {"numerator": 1, "denominator": 4} for quarter rest)
            advance_cursor_after_action: Whether to move cursor to next position after adding rest

        Returns:
            currentSelection: Updated selection state at the new cursor position with:
                - startStaff, endStaff, startTick
                - elements: The element at cursor after the operation
                - totalDuration: Duration in ticks
        """
        if duration is None:
            duration = {"numerator": 1, "denominator": 4}
        err = _validate_duration(duration)
        if err:
            return {"error": err}
        return await client.send_command("addRest", {
            "duration": duration,
            "advanceCursorAfterAction": advance_cursor_after_action
        })

    @mcp.tool()
    async def add_tuplet(duration: dict[str, int] | None = None, ratio: dict[str, int] | None = None, advance_cursor_after_action: bool = True):
        """Add a tuplet at the current cursor position.

        Args:
            duration: Base duration as {"numerator": int, "denominator": int}
            ratio: Tuplet ratio as {"numerator": int, "denominator": int} (e.g., {"numerator": 3, "denominator": 2} for triplet)
            advance_cursor_after_action: Whether to move cursor to next position after adding tuplet
        """
        if duration is None:
            duration = {"numerator": 1, "denominator": 4}
        if ratio is None:
            ratio = {"numerator": 3, "denominator": 2}
        err = _validate_duration(duration)
        if err:
            return {"error": err}
        err = _validate_duration(ratio)
        if err:
            return {"error": f"Invalid ratio: {err}"}
        return await client.send_command("addTuplet", {
            "duration": duration,
            "ratio": ratio,
            "advanceCursorAfterAction": advance_cursor_after_action
        })

    @mcp.tool()
    async def add_lyrics(lyrics: list[str], verse: int = 0):
        """Add lyrics to consecutive notes starting from the current cursor position.

        Args:
            lyrics: List of lyric syllables to add (e.g., ["Hel", "lo", "world"])
            verse: Verse number (0-based, default is 0 for first verse)
        """
        return await client.send_command("addLyrics", {
            "lyrics": lyrics,
            "verse": verse
        })

    @mcp.tool()
    async def insert_measure():
        """Insert a measure at the current position."""
        return await client.send_command("insertMeasure")

    @mcp.tool()
    async def append_measure(count: int = 1):
        """Append measures to the end of the score."""
        if count < 1:
            return {"error": "Count must be >= 1"}
        return await client.send_command("appendMeasure", {"count": count})

    @mcp.tool()
    async def delete_selection(measure: int | None = None):
        """Delete the current selection or specified measure."""
        if measure is not None and measure < 1:
            return {"error": "Measure must be >= 1"}
        params: dict[str, int] = {}
        if measure is not None:
            params["measure"] = measure
        return await client.send_command("deleteSelection", params)

    @mcp.tool()
    async def undo():
        """Undo the last action."""
        return await client.send_command("undo")
