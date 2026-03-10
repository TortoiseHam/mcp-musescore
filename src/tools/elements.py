"""Element discovery and generic element tools for MuseScore MCP."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import MuseScoreClient
from ..registry import get_element_categories, get_element_info, get_all_element_types


def setup_element_tools(mcp: FastMCP, client: MuseScoreClient) -> None:
    """Setup generic element and discovery tools."""

    @mcp.tool()
    async def list_elements(category: str | None = None):
        """List available MuseScore element types, optionally filtered by category.

        Args:
            category: Filter by category — "cursor_attached" or "cmd_shortcut".
                If not provided, returns all categories with their elements.

        Returns:
            categories: Dict of category name to element list and description,
                or a single category's elements if filtered.
        """
        if category:
            cats = get_element_categories()
            if category not in cats:
                return {"error": f"Unknown category: {category}. Valid: {list(cats.keys())}"}
            cat = cats[category]
            elements = []
            for name in cat["elements"]:
                info = get_element_info(name)
                elements.append({
                    "type": name,
                    "description": info.get("description", ""),
                })
            return {"category": category, "description": cat["description"], "elements": elements}
        return {"categories": get_element_categories()}

    @mcp.tool()
    async def describe_element(element_type: str, runtime_properties: bool = False):
        """Get detailed information about a MuseScore element type.

        Args:
            element_type: Element type name (e.g. "DYNAMIC", "STAFF_TEXT")
            runtime_properties: If True, also queries MuseScore for all non-undefined
                properties on a temp element of this type (slower, requires connection).

        Returns:
            Static info (description, category, common_properties, example) and
            optionally runtime_properties from MuseScore.
        """
        info = get_element_info(element_type)
        if not info:
            return {"error": f"Unknown element type: {element_type}. Available: {get_all_element_types()}"}

        result = dict(info)
        result["type"] = element_type

        if runtime_properties:
            qml_result = await client.send_command("describeElement", {"elementType": element_type})
            if "result" in qml_result:
                result["runtime_properties"] = qml_result["result"]
            elif "error" not in qml_result:
                result["runtime_properties"] = qml_result

        return result

    @mcp.tool()
    async def add_cursor_element(element_type: str, properties: dict[str, Any] | None = None):
        """Add an element at the current cursor position.

        Use list_elements() to see available types, and describe_element() to see
        properties for a specific type.

        This works for cursor-attached elements: DYNAMIC, STAFF_TEXT, SYSTEM_TEXT,
        REHEARSAL_MARK, FERMATA, ARTICULATION, HARMONY, FINGERING, INSTRUMENT_CHANGE,
        KEYSIG, BAR_LINE.

        Args:
            element_type: Element type name (e.g. "DYNAMIC", "STAFF_TEXT")
            properties: Dict of property name to value to set on the element
                (e.g. {"text": "ff", "velocity": 96} for a dynamic)

        Returns:
            currentSelection: Updated selection state after adding the element.
        """
        info = get_element_info(element_type)
        if not info:
            return {"error": f"Unknown element type: {element_type}. Available: {get_all_element_types()}"}
        if info.get("category") != "cursor_attached":
            return {"error": f"{element_type} is not cursor-attached. "
                    f"Category: {info.get('category')}. See its description for the right tool."}
        params: dict[str, Any] = {"elementType": element_type}
        if properties:
            params["properties"] = properties
        return await client.send_command("addCursorElement", params)

    @mcp.tool()
    async def add_volta(text: str, endings: list[int], start_measure: int, end_measure: int):
        """Add a volta bracket (repeat ending) spanning a measure range.

        Args:
            text: Display text for the volta (e.g. "1.", "2.", "1.-3.")
            endings: List of ending numbers this volta covers (e.g. [1], [2], [1, 2, 3])
            start_measure: First measure of the volta (1-based)
            end_measure: Last measure of the volta (1-based)

        Returns:
            Result with volta placement status
        """
        if start_measure < 1 or end_measure < 1:
            return {"error": "Measures must be >= 1"}
        if end_measure < start_measure:
            return {"error": "end_measure must be >= start_measure"}
        return await client.send_command("addVolta", {
            "text": text,
            "endings": endings,
            "startMeasure": start_measure,
            "endMeasure": end_measure,
        })

    @mcp.tool()
    async def add_slur(start_measure: int, end_measure: int,
                       start_beat: float = 1, end_beat: float | None = None):
        """Add a slur spanning a beat range.

        IMPORTANT: The slur must start on a note, not a rest. If start_beat
        falls on a rest, the slur will not be created. Adjust start_beat to
        the first note in the passage.

        Args:
            start_measure: First measure (1-based)
            end_measure: Last measure (1-based)
            start_beat: Beat within start measure (1-based, default 1).
                Must land on a note, not a rest. Supports fractional beats:
                1.5 = "and" of 1, 2.25 = first sixteenth after beat 2, etc.
            end_beat: Beat within end measure (1-based, default end of measure).
                Supports fractional beats.

        Returns:
            currentSelection: Updated selection state.
        """
        if start_measure < 1 or end_measure < 1:
            return {"error": "Measures must be >= 1"}
        if end_measure < start_measure:
            return {"error": "end_measure must be >= start_measure"}
        params: dict = {
            "startMeasure": start_measure,
            "endMeasure": end_measure,
            "startBeat": start_beat,
        }
        if end_beat is not None:
            params["endBeat"] = end_beat
        return await client.send_command("addSlur", params)

    @mcp.tool()
    async def add_tie():
        """Add a tie from the currently selected note to the next note of the same pitch.

        The note must be selected before calling this.

        Returns:
            currentSelection: Updated selection state.
        """
        return await client.send_command("addTie")

    @mcp.tool()
    async def add_hairpin(start_measure: int, end_measure: int,
                          hairpin_type: str = "crescendo",
                          start_beat: float = 1, end_beat: float | None = None):
        """Add a crescendo or diminuendo hairpin spanning a beat range.

        Args:
            start_measure: First measure (1-based)
            end_measure: Last measure (1-based)
            hairpin_type: "crescendo" or "diminuendo"
            start_beat: Beat within start measure (1-based, default 1).
                Supports fractional beats: 1.5 = "and" of 1, 2.25 = first
                sixteenth after beat 2, etc.
            end_beat: Beat within end measure (1-based, default end of measure).
                Supports fractional beats.

        Returns:
            currentSelection: Updated selection state.
        """
        if hairpin_type not in ("crescendo", "diminuendo"):
            return {"error": "hairpin_type must be 'crescendo' or 'diminuendo'"}
        if start_measure < 1 or end_measure < 1:
            return {"error": "Measures must be >= 1"}
        if end_measure < start_measure:
            return {"error": "end_measure must be >= start_measure"}
        params: dict = {
            "hairpinType": hairpin_type,
            "startMeasure": start_measure,
            "endMeasure": end_measure,
            "startBeat": start_beat,
        }
        if end_beat is not None:
            params["endBeat"] = end_beat
        return await client.send_command("addHairpin", params)

    @mcp.tool()
    async def test_cmd(cmd_name: str):
        """Test an arbitrary MuseScore cmd() call. For experimentation only.

        Args:
            cmd_name: The command name to pass to cmd() (e.g. "toggle-marcato")
        """
        if cmd_name == "testBarline":
            return await client.send_command("testBarline", {})
        return await client.send_command("testCmd", {"cmd": cmd_name})
