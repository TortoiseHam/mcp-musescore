"""Static registry of MuseScore element types for discovery."""

from typing import Any

ELEMENT_CATEGORIES = {
    "cursor_attached": {
        "description": "Elements added at the cursor position via cursor.add(). "
                       "Use add_cursor_element() to create these.",
        "elements": [
            "DYNAMIC", "STAFF_TEXT", "SYSTEM_TEXT", "REHEARSAL_MARK",
            "FERMATA", "ARTICULATION", "HARMONY", "FINGERING",
            "TEMPO_TEXT", "INSTRUMENT_CHANGE", "KEYSIG", "BAR_LINE",
        ],
    },
    "cmd_shortcut": {
        "description": "Elements added via MuseScore's built-in commands. "
                       "Use dedicated tools: add_slur(), add_tie(), add_hairpin().",
        "elements": ["SLUR", "TIE", "HAIRPIN", "VOLTA"],
    },
}

ELEMENT_INFO: dict[str, dict[str, Any]] = {
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
        "description": "Articulation marking. Set subtype to choose which articulation. "
                       "Supported subtypes: staccato, marcato, tenuto, trill, turn.",
        "category": "cursor_attached",
        "common_properties": {
            "subtype": "string — one of: staccato, marcato, tenuto, trill, turn",
        },
        "example": {"subtype": "staccato"},
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
    "TEMPO_TEXT": {
        "description": "Tempo marking. Prefer set_tempo() for standard tempo changes; "
                       "use this for custom tempo text without BPM effect.",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — display text",
            "tempo": "float — tempo in beats per second (BPM / 60)",
        },
        "example": {"text": "Andante", "tempo": 1.33},
    },
    "INSTRUMENT_CHANGE": {
        "description": "Instrument change marking at a point in the score",
        "category": "cursor_attached",
        "common_properties": {
            "text": "string — instrument change label",
        },
        "example": {"text": "Mute"},
    },
    "KEYSIG": {
        "description": "Key signature. Set the key using the 'key' property "
                       "(negative = flats, 0 = C major, positive = sharps).",
        "category": "cursor_attached",
        "common_properties": {
            "key": "int — number of sharps (positive) or flats (negative). "
                   "E.g. -3 = Eb major, 0 = C major, 2 = D major",
        },
        "example": {"key": -3},
    },
    "BAR_LINE": {
        "description": "Bar line. Set subtype for different styles: "
                       "normal, double, start-repeat, end-repeat, end-start-repeat, end.",
        "category": "cursor_attached",
        "common_properties": {
            "subtypeName": "string — bar line type name",
        },
        "example": {},
    },
    "SLUR": {
        "description": "Slur connecting notes across a measure range. "
                       "Use add_slur(start_measure, end_measure).",
        "category": "cmd_shortcut",
        "common_properties": {
            "start_measure": "int — first measure (1-based)",
            "end_measure": "int — last measure (1-based)",
        },
        "example": {"start_measure": 1, "end_measure": 4},
    },
    "TIE": {
        "description": "Tie connecting two notes of the same pitch. "
                       "Select the note and call add_tie().",
        "category": "cmd_shortcut",
        "common_properties": {},
        "example": {},
    },
    "HAIRPIN": {
        "description": "Crescendo or diminuendo hairpin spanning a measure range. "
                       "Use add_hairpin(start_measure, end_measure, hairpin_type).",
        "category": "cmd_shortcut",
        "common_properties": {
            "hairpin_type": "string — 'crescendo' or 'diminuendo'",
            "start_measure": "int — first measure (1-based)",
            "end_measure": "int — last measure (1-based)",
        },
        "example": {"start_measure": 4, "end_measure": 5, "hairpin_type": "crescendo"},
    },
    "VOLTA": {
        "description": "Volta bracket (repeat ending). "
                       "Use add_volta(text, endings, start_measure, end_measure).",
        "category": "cmd_shortcut",
        "common_properties": {
            "text": "string — display text, e.g. '1.', '2.'",
            "endings": "list[int] — ending numbers, e.g. [1], [2]",
            "start_measure": "int — first measure (1-based)",
            "end_measure": "int — last measure (1-based)",
        },
        "example": {"text": "1.", "endings": [1], "start_measure": 1, "end_measure": 4},
    },
}


def get_element_categories() -> dict[str, Any]:
    """Return all categories with their element lists."""
    return ELEMENT_CATEGORIES


def get_all_element_types() -> list[str]:
    """Return all element type names across all categories."""
    types: list[str] = []
    for cat in ELEMENT_CATEGORIES.values():
        types.extend(cat["elements"])
    return types


def get_element_info(element_type: str) -> dict[str, Any]:
    """Return info about a specific element type."""
    return ELEMENT_INFO.get(element_type, {})
