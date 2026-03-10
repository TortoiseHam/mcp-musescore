# Generic Elements, Discovery, Export & Voice Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add generic element creation (dynamics, text, articulations, etc.), slur/tie/hairpin tools, element discovery/introspection, PDF export, and voice switching to the MCP server.

**Architecture:** Three layers of new functionality: (1) a static Python registry of MuseScore element types grouped by attachment pattern, with a QML `describeElement` command for runtime property discovery; (2) generic `add_cursor_element` tool for `newElement()` + `cursor.add()` elements, plus dedicated `add_slur`/`add_tie`/`add_hairpin` tools that use MuseScore's `cmd()` API since spanners/ties can't be created via `newElement`; (3) `export_pdf` using `writeScore()` and `set_voice` using `cursor.track`.

**Tech Stack:** Python 3 (FastMCP), QML (MuseScore 3.0 plugin API), WebSocket

---

## Task 1: Element Registry

**Files:**
- Create: `src/registry.py`

**Step 1: Create the registry module**

```python
"""Static registry of MuseScore element types for discovery."""

from typing import Dict, List, Any

ELEMENT_CATEGORIES = {
    "cursor_attached": {
        "description": "Elements added at the cursor position via cursor.add(). "
                       "Use add_cursor_element() to create these.",
        "elements": [
            "DYNAMIC", "STAFF_TEXT", "SYSTEM_TEXT", "REHEARSAL_MARK",
            "FERMATA", "ARTICULATION", "HARMONY", "FINGERING",
            "TEMPO_TEXT", "INSTRUMENT_CHANGE",
        ],
    },
    "cmd_shortcut": {
        "description": "Elements added via MuseScore's built-in commands. "
                       "Use dedicated tools: add_slur(), add_tie(), add_hairpin().",
        "elements": ["SLUR", "TIE", "HAIRPIN"],
    },
}

ELEMENT_INFO: Dict[str, Dict[str, Any]] = {
    "DYNAMIC": {
        "description": "Dynamic marking (pp, p, mp, mf, f, ff, etc.)",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — dynamic text, e.g. 'ff', 'pp', 'sfz'",
            "velocity": "int 1-127 — MIDI velocity value",
            "dynamicRange": "int — 0=Staff, 1=Part, 2=System",
        },
        "example": {"text": "mf", "velocity": 80},
    },
    "STAFF_TEXT": {
        "description": "Text attached to a staff (e.g. 'pizz.', 'arco')",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — the text content",
        },
        "example": {"text": "pizz."},
    },
    "SYSTEM_TEXT": {
        "description": "Text attached to the system (appears above all staves)",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — the text content",
        },
        "example": {"text": "Allegro con brio"},
    },
    "REHEARSAL_MARK": {
        "description": "Rehearsal mark (e.g. A, B, C or numbered)",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — the rehearsal mark text",
        },
        "example": {"text": "A"},
    },
    "FERMATA": {
        "description": "Fermata (pause/hold) marking",
        "category": "cursor_attached",
        "common_properties": {
            "timeStretch": "float — how much to stretch the note (default 1.0)",
        },
        "example": {"timeStretch": 2.0},
    },
    "ARTICULATION": {
        "description": "Articulation marking (staccato, accent, tenuto, etc.). "
                       "Set subtype to choose which articulation.",
        "category": "cursor_attached",
        "common_properties": {
            "subtype": "string — articulation symbol name",
        },
        "example": {},
    },
    "HARMONY": {
        "description": "Chord symbol (e.g. Cmaj7, Dm, G7)",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — chord symbol text",
        },
        "example": {"text": "Cmaj7"},
    },
    "FINGERING": {
        "description": "Fingering annotation on a note",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — fingering text (e.g. '1', '2', '3')",
        },
        "example": {"text": "1"},
    },
    "INSTRUMENT_CHANGE": {
        "description": "Instrument change marking at a point in the score",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — instrument change label",
        },
        "example": {"text": "Mute"},
    },
    "SLUR": {
        "description": "Slur connecting notes. Select start note, call add_slur(), "
                       "then navigate to end note. Works on current selection.",
        "category": "cmd_shortcut",
        "common_properties": {},
        "example": {},
    },
    "TIE": {
        "description": "Tie connecting two notes of the same pitch. "
                       "Select the note and call add_tie().",
        "category": "cmd_shortcut",
        "common_properties": {},
        "example": {},
    },
    "HAIRPIN": {
        "description": "Crescendo or diminuendo hairpin. "
                       "Use add_hairpin(hairpin_type). Works on current selection.",
        "category": "cmd_shortcut",
        "common_properties": {
            "hairpin_type": "string — 'crescendo' or 'diminuendo'",
        },
        "example": {},
    },
}


def get_element_categories() -> Dict[str, Any]:
    """Return all categories with their element lists."""
    return ELEMENT_CATEGORIES


def get_elements_in_category(category: str) -> List[str]:
    """Return element type names in a category."""
    cat = ELEMENT_CATEGORIES.get(category)
    if not cat:
        return []
    return cat["elements"]


def get_element_info(element_type: str) -> Dict[str, Any]:
    """Return info about a specific element type."""
    return ELEMENT_INFO.get(element_type, {})
```

**Step 2: Verify import works**

Run: `uv run python -c "from src.registry import get_element_info; print(get_element_info('DYNAMIC'))"`
Expected: Prints the DYNAMIC dict

**Step 3: Commit**

```bash
git add src/registry.py
git commit -m "feat: add static element type registry for discovery"
```

---

## Task 2: Discovery Tools (list_elements, describe_element)

**Files:**
- Create: `src/tools/elements.py`
- Modify: `src/tools/__init__.py`
- Modify: `server.py`

**Step 1: Create elements.py with discovery tools**

```python
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
```

**Step 2: Wire into `src/tools/__init__.py`**

Add to imports and `__all__`:

```python
from .elements import setup_element_tools
```

```python
__all__ = [
    ...,
    "setup_element_tools",
]
```

**Step 3: Wire into `server.py`**

Add import and call:

```python
from src.tools import (
    ...,
    setup_element_tools,
)
...
setup_element_tools(mcp, client)
```

**Step 4: Verify server starts**

Run: `timeout 3 uv run python server.py 2>&1; true`
Expected: "MuseScore MCP Server is running"

**Step 5: Commit**

```bash
git add src/tools/elements.py src/tools/__init__.py server.py
git commit -m "feat: add list_elements and describe_element discovery tools"
```

---

## Task 3: QML describeElement Command

**Files:**
- Modify: `musescore-mcp-websocket.qml`

**Step 1: Add describeElement to processCommand switch**

In the `processCommand` switch statement, add alongside the core operations:

```javascript
case "describeElement":         return describeElement(command.params);
```

**Step 2: Add describeElement function**

Add in the "CORE OPERATIONS" section:

```javascript
function describeElement(params) {
    if (!params || !params.elementType) {
        return { error: "elementType is required" };
    }

    var elementType = Element[params.elementType];
    if (elementType === undefined) {
        return { error: "Unknown element type: " + params.elementType };
    }

    try {
        var elem = newElement(elementType);
        var properties = {};

        Object.keys(elem).forEach(function(key) {
            var val = elem[key];
            if (val !== undefined && typeof val !== "function") {
                try {
                    properties[key] = String(val);
                } catch (e) {
                    properties[key] = "(unreadable)";
                }
            }
        });

        return {
            elementType: params.elementType,
            properties: properties
        };
    } catch (e) {
        return { error: e.toString() };
    }
}
```

**Step 3: Commit**

```bash
git add musescore-mcp-websocket.qml
git commit -m "feat: add describeElement QML command for runtime introspection"
```

---

## Task 4: Generic add_cursor_element Tool

**Files:**
- Modify: `src/tools/elements.py`
- Modify: `musescore-mcp-websocket.qml`
- Modify: `src/types/action_types.py`

**Step 1: Add add_cursor_element to elements.py**

Append inside `setup_element_tools`:

```python
    @mcp.tool()
    async def add_cursor_element(element_type: str, properties: Optional[dict] = None):
        """Add an element at the current cursor position.

        Use list_elements() to see available types, and describe_element() to see
        properties for a specific type.

        This works for cursor-attached elements: DYNAMIC, STAFF_TEXT, SYSTEM_TEXT,
        REHEARSAL_MARK, FERMATA, ARTICULATION, HARMONY, FINGERING, INSTRUMENT_CHANGE.

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
```

**Step 2: Add addCursorElement to QML processCommand switch**

```javascript
case "addCursorElement":        return addCursorElement(command.params);
```

**Step 3: Add addCursorElement QML function**

Add in the "NOTE & MUSIC OPERATIONS" section:

```javascript
function addCursorElement(params) {
    if (!params || !params.elementType) {
        return { error: "elementType is required" };
    }

    var elementType = Element[params.elementType];
    if (elementType === undefined) {
        return { error: "Unknown element type: " + params.elementType };
    }

    return executeWithUndo(function() {
        syncStateToSelection();

        var cursor = createCursor();
        var elem = newElement(elementType);

        if (params.properties) {
            var keys = Object.keys(params.properties);
            for (var i = 0; i < keys.length; i++) {
                elem[keys[i]] = params.properties[keys[i]];
            }
        }

        cursor.add(elem);

        return {
            success: true,
            message: params.elementType + " added",
            currentSelection: selectionState
        };
    });
}
```

**Step 4: Add TypedDicts to action_types.py**

```python
class AddCursorElementParams(TypedDict):
    elementType: str
    properties: NotRequired[Dict[str, Any]]


class AddCursorElementAction(TypedDict):
    action: Literal["addCursorElement"]
    params: AddCursorElementParams
```

Add `AddCursorElementAction` to the `ActionSequence` union.

**Step 5: Add to `__init__.py` exports**

Add `"AddCursorElementAction"` to `__all__` in `src/types/__init__.py`.

**Step 6: Add "addCursorElement" to processSequence validCommands**

In QML `processSequence`, add `"addCursorElement"` to the `validCommands` array.

**Step 7: Verify**

Run: `timeout 3 uv run python server.py 2>&1; true`
Expected: Server starts cleanly

**Step 8: Commit**

```bash
git add src/tools/elements.py musescore-mcp-websocket.qml src/types/action_types.py src/types/__init__.py
git commit -m "feat: add generic add_cursor_element tool for dynamics, text, etc."
```

---

## Task 5: Slur, Tie, and Hairpin Tools

**Files:**
- Modify: `src/tools/elements.py`
- Modify: `musescore-mcp-websocket.qml`
- Modify: `src/types/action_types.py`
- Modify: `src/types/__init__.py`

These use MuseScore's `cmd()` because `newElement()` doesn't work reliably for spanners/ties.

**Step 1: Add tools to elements.py**

Append inside `setup_element_tools`:

```python
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
```

**Step 2: Add QML commands to processCommand switch**

```javascript
case "addSlur":                 return addSlur();
case "addTie":                  return addTie();
case "addHairpin":              return addHairpin(command.params);
```

**Step 3: Add QML functions**

Add in the "NOTE & MUSIC OPERATIONS" section:

```javascript
function addSlur() {
    return executeWithUndo(function() {
        cmd("add-slur");
        syncStateToSelection();
        return {
            success: true,
            message: "Slur added",
            currentSelection: selectionState
        };
    });
}

function addTie() {
    return executeWithUndo(function() {
        cmd("tie");
        syncStateToSelection();
        return {
            success: true,
            message: "Tie added",
            currentSelection: selectionState
        };
    });
}

function addHairpin(params) {
    return executeWithUndo(function() {
        if (params && params.hairpinType === "diminuendo") {
            cmd("add-hairpin-reverse");
        } else {
            cmd("add-hairpin");
        }
        syncStateToSelection();
        return {
            success: true,
            message: (params && params.hairpinType || "crescendo") + " hairpin added",
            currentSelection: selectionState
        };
    });
}
```

**Step 4: Add TypedDicts to action_types.py**

```python
class AddSlurAction(TypedDict):
    action: Literal["addSlur"]
    params: Dict[str, Any]


class AddTieAction(TypedDict):
    action: Literal["addTie"]
    params: Dict[str, Any]


class AddHairpinParams(TypedDict):
    hairpinType: str


class AddHairpinAction(TypedDict):
    action: Literal["addHairpin"]
    params: AddHairpinParams
```

Add all three to the `ActionSequence` union.

**Step 5: Add to `__init__.py` exports**

Add `"AddSlurAction"`, `"AddTieAction"`, `"AddHairpinAction"` to `__all__`.

**Step 6: Add to processSequence validCommands in QML**

Add `"addSlur"`, `"addTie"`, `"addHairpin"` to the `validCommands` array.

**Step 7: Verify**

Run: `timeout 3 uv run python server.py 2>&1; true`
Expected: Server starts cleanly

**Step 8: Commit**

```bash
git add src/tools/elements.py musescore-mcp-websocket.qml src/types/action_types.py src/types/__init__.py
git commit -m "feat: add slur, tie, and hairpin tools using cmd() API"
```

---

## Task 6: PDF Export

**Files:**
- Modify: `src/tools/connection.py`
- Modify: `musescore-mcp-websocket.qml`
- Modify: `src/types/action_types.py`
- Modify: `src/types/__init__.py`

**Step 1: Add export_pdf to connection.py**

Append inside `setup_connection_tools`:

```python
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
```

**Step 2: Add QML command to processCommand switch**

```javascript
case "exportPdf":               return exportPdf(command.params);
```

**Step 3: Add QML exportPdf function**

Add in the "CORE OPERATIONS" section:

```javascript
function exportPdf(params) {
    if (!curScore) return { error: "No score open" };

    var outputPath = params && params.outputPath || "/tmp/musescore-mcp/export.pdf";

    try {
        var success = writeScore(curScore, outputPath, "pdf");
        if (success) {
            return { success: true, path: outputPath, message: "Score exported to PDF" };
        } else {
            return { success: false, error: "writeScore returned false — check path and permissions" };
        }
    } catch (e) {
        return { error: e.toString() };
    }
}
```

**Step 4: Add TypedDict to action_types.py**

```python
class ExportPdfParams(TypedDict, total=False):
    outputPath: str


class ExportPdfAction(TypedDict):
    action: Literal["exportPdf"]
    params: ExportPdfParams
```

Add `ExportPdfAction` to `ActionSequence` union. Add to `__init__.py` exports.

**Step 5: Verify**

Run: `timeout 3 uv run python server.py 2>&1; true`
Expected: Server starts cleanly

**Step 6: Commit**

```bash
git add src/tools/connection.py musescore-mcp-websocket.qml src/types/action_types.py src/types/__init__.py
git commit -m "feat: add export_pdf tool using writeScore API"
```

---

## Task 7: Voice Switching

**Files:**
- Modify: `src/tools/navigation.py`
- Modify: `musescore-mcp-websocket.qml`
- Modify: `src/types/action_types.py`
- Modify: `src/types/__init__.py`

**Step 1: Add set_voice to navigation.py**

Append inside `setup_navigation_tools`:

```python
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
```

**Step 2: Add QML command to processCommand switch**

```javascript
case "setVoice":                return setVoice(command.params);
```

**Step 3: Add QML setVoice function**

Add in the "NAVIGATION FUNCTIONS" section:

```javascript
function setVoice(params) {
    var validation = validateParams(params, ["voice"]);
    if (!validation.valid) return validation;

    var voice = params.voice;
    if (voice < 0 || voice > 3) {
        return { error: "Voice must be 0-3" };
    }

    return executeWithUndo(function() {
        syncStateToSelection();

        var staffIdx = selectionState.startStaff;
        var cursor = createCursor({
            startTick: selectionState.startTick,
            startStaff: staffIdx
        });

        cursor.track = staffIdx * 4 + voice;
        cursor.rewindToTick(selectionState.startTick);

        var element = processElement(cursor.element);
        var startTick = cursor.tick;

        curScore.selection.clear();
        curScore.selection.selectRange(
            startTick,
            startTick + (element ? element.durationTicks : 0),
            staffIdx,
            staffIdx + 1
        );

        selectionState = {
            startStaff: staffIdx,
            endStaff: staffIdx + 1,
            startTick: startTick,
            voice: voice,
            elements: element ? [element] : [],
            totalDuration: element ? element.durationTicks : 0
        };

        return {
            success: true,
            message: "Voice set to " + voice,
            currentSelection: selectionState
        };
    });
}
```

**Step 4: Add TypedDict to action_types.py**

```python
class SetVoiceParams(TypedDict):
    voice: int


class SetVoiceAction(TypedDict):
    action: Literal["setVoice"]
    params: SetVoiceParams
```

Add `SetVoiceAction` to `ActionSequence` union. Add to `__init__.py` exports.

**Step 5: Add "setVoice" to processSequence validCommands in QML**

Add `"setVoice"` to the `validCommands` array.

**Step 6: Verify**

Run: `timeout 3 uv run python server.py 2>&1; true`
Expected: Server starts cleanly

**Step 7: Commit**

```bash
git add src/tools/navigation.py musescore-mcp-websocket.qml src/types/action_types.py src/types/__init__.py
git commit -m "feat: add set_voice tool for polyphonic writing"
```

---

## Verification (with MuseScore running)

After all tasks, verify end-to-end:

1. `list_elements()` → returns both categories with all element types
2. `list_elements(category="cursor_attached")` → returns 10 cursor-attached elements
3. `describe_element(element_type="DYNAMIC")` → returns static info with common_properties
4. `describe_element(element_type="DYNAMIC", runtime_properties=True)` → includes QML property dump
5. `add_cursor_element(element_type="DYNAMIC", properties={"text": "ff", "velocity": 96})` → dynamic appears in score
6. `add_cursor_element(element_type="STAFF_TEXT", properties={"text": "pizz."})` → text appears
7. `add_tie()` (with note selected) → tie added
8. `add_slur()` → slur started from selection
9. `add_hairpin(hairpin_type="crescendo")` → crescendo hairpin on selection
10. `add_hairpin(hairpin_type="diminuendo")` → diminuendo hairpin
11. `export_pdf()` → file at /tmp/musescore-mcp/export.pdf
12. `export_pdf(output_path="/tmp/test.pdf")` → file at /tmp/test.pdf
13. `set_voice(voice=1)` → cursor switches to voice 2
14. `set_voice(voice=0)` → back to voice 1
15. `processSequence` with `addCursorElement`, `addSlur`, `addTie`, `setVoice` in sequence → all work
