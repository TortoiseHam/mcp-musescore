"""Cursor and navigation tools for MuseScore MCP."""

from ..client import MuseScoreClient


def setup_navigation_tools(mcp, client: MuseScoreClient):
    """Setup cursor and navigation tools."""

    @mcp.tool()
    async def get_cursor_info(verbose: bool = True):
        """Get information about the current cursor position.

        Args:
            verbose: If True (default), includes full score summary in currentScore.
                If False, currentScore will be null (faster for just getting selection info).

        Returns:
            currentSelection: Current selection state with fields:
                - startStaff: Starting staff index (0-based)
                - endStaff: Ending staff index (0-based, exclusive)
                - startTick: Starting tick position
                - elements: List of elements in selection, each with:
                    - name: Element type ("Note", "Chord", "Rest")
                    - baseDuration: Duration name (e.g. "QUARTER", "HALF")
                    - durationTicks: Duration in ticks
                    - pitchMidi/pitchName: For notes only
                    - accidental/tieBack/tieForward: For notes only
                    - tuplet: Tuplet info if in a tuplet
                - totalDuration: Sum of element durations in ticks
            currentScore: Full score summary (see get_score) or null if verbose=False
        """
        return await client.send_command("getCursorInfo", {"verbose": str(verbose).lower()})

    @mcp.tool()
    async def go_to_measure(measure: int):
        """Navigate to a specific measure."""
        if measure < 1:
            return {"error": "Measure must be >= 1"}
        return await client.send_command("goToMeasure", {"measure": measure})

    @mcp.tool()
    async def go_to_final_measure():
        """Navigate to the final measure of the score."""
        return await client.send_command("goToFinalMeasure")

    @mcp.tool()
    async def go_to_beginning_of_score():
        """Navigate to the beginning of the score."""
        return await client.send_command("goToBeginningOfScore")

    @mcp.tool()
    async def next_element(num_elements: int = 1):
        """Move cursor forward by one or more elements.

        Args:
            num_elements: Number of elements to advance (default 1, must be >= 1)

        Returns:
            currentSelection with the element at the new position, including:
                - name, baseDuration, durationTicks
                - pitchMidi, pitchName, accidental, tieBack, tieForward (for notes)
                - tuplet info (if in a tuplet)
        """
        if num_elements < 1:
            return {"error": "num_elements must be >= 1"}
        return await client.send_command("nextElement", {"numElements": num_elements})

    @mcp.tool()
    async def prev_element(num_elements: int = 1):
        """Move cursor backward by one or more elements.

        Args:
            num_elements: Number of elements to go back (default 1, must be >= 1)

        Returns:
            currentSelection with the element at the new position, including:
                - name, baseDuration, durationTicks
                - pitchMidi, pitchName, accidental, tieBack, tieForward (for notes)
                - tuplet info (if in a tuplet)
        """
        if num_elements < 1:
            return {"error": "num_elements must be >= 1"}
        return await client.send_command("prevElement", {"numElements": num_elements})

    @mcp.tool()
    async def next_staff():
        """Move cursor to the next staff."""
        return await client.send_command("nextStaff")

    @mcp.tool()
    async def prev_staff():
        """Move cursor to the previous staff."""
        return await client.send_command("prevStaff")

    @mcp.tool()
    async def select_current_measure():
        """Select the current measure."""
        return await client.send_command("selectCurrentMeasure")

    @mcp.tool()
    async def select_custom_range(start_tick: int, end_tick: int, start_staff: int, end_staff: int):
        """Select a custom range in the score by tick position and staff.

        Args:
            start_tick: Starting tick position
            end_tick: Ending tick position
            start_staff: Starting staff index (0-based)
            end_staff: Ending staff index (0-based)
        """
        if start_staff < 0:
            return {"error": "start_staff must be >= 0"}
        if end_staff < 0:
            return {"error": "end_staff must be >= 0"}
        return await client.send_command("selectCustomRange", {
            "startTick": start_tick,
            "endTick": end_tick,
            "startStaff": start_staff,
            "endStaff": end_staff
        })

    @mcp.tool()
    async def set_voice(voice: int):
        """Switch the cursor to a different voice (for polyphonic writing).

        Args:
            voice: Voice number 0-3 (MuseScore supports 4 voices per staff)

        Returns:
            currentSelection: Updated selection state in the new voice.
        """
        if voice < 0 or voice > 3:
            return {"error": "Voice must be 0-3"}
        return await client.send_command("setVoice", {"voice": voice})
