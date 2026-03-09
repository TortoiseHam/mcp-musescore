"""Element discovery and generic element tools for MuseScore MCP."""

from typing import Optional
from ..client import MuseScoreClient
from ..registry import get_element_categories, get_elements_in_category, get_element_info


def setup_element_tools(mcp, client: MuseScoreClient):
    """Setup generic element and discovery tools."""

    @mcp.tool()
    async def list_elements(category: Optional[str] = None):
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
            all_types = []
            for cat in get_element_categories().values():
                all_types.extend(cat["elements"])
            return {"error": f"Unknown element type: {element_type}. Available: {all_types}"}

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
    async def add_cursor_element(element_type: str, properties: Optional[dict] = None):
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
            all_types = []
            for cat in get_element_categories().values():
                all_types.extend(cat["elements"])
            return {"error": f"Unknown element type: {element_type}. Available: {all_types}"}
        if info.get("category") != "cursor_attached":
            return {"error": f"{element_type} is not cursor-attached. "
                    f"Category: {info.get('category')}. See its description for the right tool."}
        params = {"elementType": element_type}
        if properties:
            params["properties"] = properties
        return await client.send_command("addCursorElement", params)

    @mcp.tool()
    async def add_slur():
        """Add a slur starting from the current selection.

        The slur begins at the currently selected note. After calling this,
        use next_element() to extend the slur, then call any note/navigation
        tool to finalize it.

        Returns:
            currentSelection: Updated selection state.
        """
        return await client.send_command("addSlur")

    @mcp.tool()
    async def add_tie():
        """Add a tie from the currently selected note to the next note of the same pitch.

        The note must be selected before calling this.

        Returns:
            currentSelection: Updated selection state.
        """
        return await client.send_command("addTie")

    @mcp.tool()
    async def add_hairpin(hairpin_type: str = "crescendo"):
        """Add a crescendo or diminuendo hairpin at the current selection.

        Select a range first (e.g. via select_current_measure or select_custom_range),
        then call this to add the hairpin across that range.

        Args:
            hairpin_type: "crescendo" or "diminuendo"

        Returns:
            currentSelection: Updated selection state.
        """
        if hairpin_type not in ("crescendo", "diminuendo"):
            return {"error": "hairpin_type must be 'crescendo' or 'diminuendo'"}
        return await client.send_command("addHairpin", {"hairpinType": hairpin_type})
