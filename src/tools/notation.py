"""Notation tools for human-readable score readback and bulk note entry."""

import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import MuseScoreClient
from ..pitch import (
    midi_to_note_name,
    ticks_to_duration_str,
    parse_pitch,
    concert_to_written,
)

# Duration string to {numerator, denominator} mapping
_DURATION_DENOM = {
    "1": 1, "2": 2, "4": 4, "8": 8, "16": 16, "32": 32, "64": 64, "128": 128,
}

_NOTATION_TOKEN_RE = re.compile(
    r"^"
    r"(?P<rest>r)"                          # rest prefix
    r"|(?P<multirest>R\*(\d+))"             # multi-measure rest R*N
    r"|(?P<pitch>[A-Ga-g][#b]{0,2}-?\d)"    # pitch like Eb5, F#4, C-1
    r""
)

_DURATION_RE = re.compile(r"/(\d+)(\.{0,3})")


def _parse_duration(dur_str: str) -> dict[str, int]:
    """Parse a duration string like '/4', '/4.', '/2..' into {numerator, denominator}."""
    m = _DURATION_RE.match(dur_str)
    if not m:
        raise ValueError(f"Invalid duration: '{dur_str}'")
    base_denom = int(m.group(1))
    dots = len(m.group(2))
    if dots == 0:
        return {"numerator": 1, "denominator": base_denom}
    # Dotted: num = 2^(dots+1) - 1, denom = base_denom * 2^dots
    num = (1 << (dots + 1)) - 1
    denom = base_denom * (1 << dots)
    return {"numerator": num, "denominator": denom}


def parse_notation_string(notation: str) -> list[dict[str, Any]]:
    """Parse a notation string into a sequence of actions.

    Format:
        r/4 Eb5/4 F5/4 G5/4 | Ab5/1 | R*7
    - Notes: Eb5/4 (pitch/duration)
    - Dotted: Eb5/4. (dotted quarter)
    - Rests: r/4 (quarter rest)
    - Ties: Eb5/4~ (tie to next)
    - Multi-measure rest: R*3 (3 whole-measure rests)
    - Barlines: | (ignored separator)

    Returns:
        List of action dicts suitable for processSequence.
    """
    tokens = notation.split()
    actions: list[dict[str, Any]] = []

    for token in tokens:
        if token == "|":
            continue

        # Multi-measure rest: R*N
        if token.startswith("R*"):
            try:
                count = int(token[2:])
            except ValueError:
                raise ValueError(f"Invalid multi-measure rest: '{token}'")
            for _ in range(count):
                actions.append({
                    "action": "addRest",
                    "params": {
                        "duration": {"numerator": 1, "denominator": 1},
                        "advanceCursorAfterAction": True,
                    },
                })
            continue

        # Rest: r/D[.]
        if token.startswith("r/"):
            dur_part = token[1:]  # "/4" or "/4."
            duration = _parse_duration(dur_part)
            actions.append({
                "action": "addRest",
                "params": {
                    "duration": duration,
                    "advanceCursorAfterAction": True,
                },
            })
            continue

        # Note: Pitch/D[.][~]
        # Find the / separator
        slash_idx = token.find("/")
        if slash_idx == -1:
            raise ValueError(f"Invalid notation token (missing duration): '{token}'")

        pitch_str = token[:slash_idx]
        rest = token[slash_idx:]  # e.g. "/4.~"

        # Check for tie
        has_tie = rest.endswith("~")
        if has_tie:
            rest = rest[:-1]

        duration = _parse_duration(rest)
        midi = parse_pitch(pitch_str)

        actions.append({
            "action": "addNote",
            "params": {
                "pitch": midi,
                "duration": duration,
                "advanceCursorAfterAction": True,
            },
        })

        if has_tie:
            actions.append({
                "action": "addTie",
                "params": {},
            })

    return actions


def setup_notation_tools(mcp: FastMCP, client: MuseScoreClient) -> None:
    """Setup notation readback and bulk entry tools."""

    @mcp.tool()
    async def get_score_text(
        start_measure: int = 1,
        end_measure: int | None = None,
        staves: list[int] | None = None,
        prefer_flats: bool = True,
        written_pitch: bool = False,
    ) -> str:
        """Get a human-readable text representation of the score.

        Returns notation like:
            m1  staff0: r/4  Eb5/4  F5/4  G5/4
            m2  staff0: Ab5/1

        Args:
            start_measure: First measure to include (1-based)
            end_measure: Last measure to include (defaults to all)
            staves: List of staff indices to include (defaults to all)
            prefer_flats: Use flats (Eb) vs sharps (D#) for note names
            written_pitch: If True, show written pitch for transposing instruments
                instead of concert pitch

        Returns:
            Multi-line text representation of the score
        """
        params: dict[str, Any] = {"startMeasure": start_measure}
        if end_measure is not None:
            params["endMeasure"] = end_measure
        if staves is not None:
            params["staves"] = staves

        result = await client.send_command("getScore", params)

        if "error" in result:
            return f"Error: {result['error']}"

        analysis = result.get("result", result).get("analysis", result.get("result", result))

        # Build transposition map if needed
        transpose_map: dict[int, int] = {}
        if written_pitch and "staves" in analysis:
            for staff_info in analysis["staves"]:
                staff_name = staff_info.get("name", "")
                if staff_name.startswith("staff"):
                    try:
                        idx = int(staff_name[5:])
                    except ValueError:
                        continue
                    transpose_map[idx] = staff_info.get("transposeChromatic", 0)

        lines = []
        for measure_data in analysis.get("measures", []):
            measure_num = measure_data.get("measure", "?")
            elements_by_staff = measure_data.get("elements", {})

            for staff_key, elements in sorted(elements_by_staff.items()):
                staff_idx = int(staff_key.replace("staff", "")) if staff_key.startswith("staff") else 0
                chromatic = transpose_map.get(staff_idx, 0)

                parts = []
                for el in elements:
                    name = el.get("name", "")
                    base_dur = el.get("baseDuration", "QUARTER")
                    dots = el.get("dotted", 0)
                    dur_ticks = el.get("durationTicks", 0)
                    dur_str = ticks_to_duration_str(base_dur, dots, dur_ticks)
                    tie_str = "~" if el.get("tieForward") else ""

                    if name == "Rest":
                        parts.append(f"r{dur_str}")
                    elif name == "Note":
                        midi = el.get("pitchMidi", 0)
                        if written_pitch and chromatic:
                            midi = concert_to_written(midi, chromatic)
                        note_name = midi_to_note_name(midi, prefer_flats=prefer_flats)
                        parts.append(f"{note_name}{dur_str}{tie_str}")
                    elif name == "Chord":
                        notes = el.get("notes", [])
                        if len(notes) == 1:
                            midi = notes[0].get("pitchMidi", 0)
                            if written_pitch and chromatic:
                                midi = concert_to_written(midi, chromatic)
                            note_name = midi_to_note_name(midi, prefer_flats=prefer_flats)
                            parts.append(f"{note_name}{dur_str}{tie_str}")
                        else:
                            chord_notes = []
                            for n in notes:
                                midi = n.get("pitchMidi", 0)
                                if written_pitch and chromatic:
                                    midi = concert_to_written(midi, chromatic)
                                chord_notes.append(midi_to_note_name(midi, prefer_flats=prefer_flats))
                            chord_str = " ".join(chord_notes)
                            parts.append(f"<{chord_str}>{dur_str}{tie_str}")

                if parts:
                    lines.append(f"m{measure_num}  {staff_key}: {'  '.join(parts)}")

        return "\n".join(lines) if lines else "(empty)"

    @mcp.tool()
    async def add_notes_from_string(
        notation: str,
        staff: int | None = None,
        measure: int | None = None,
        written_pitch: bool = False,
    ):
        """Add notes to the score from a compact notation string.

        Notation format:
            r/4 Eb5/4 F5/4 G5/4 | Ab5/1 | R*7

        - Notes: Eb5/4 (pitch/duration), F#4/8 (eighth note)
        - Dotted: Eb5/4. (dotted quarter), C5/2.. (double-dotted half)
        - Rests: r/4 (quarter rest), r/1 (whole rest)
        - Ties: Eb5/4~ (tie to next note of same pitch)
        - Multi-measure rest: R*3 (3 measures of whole rests)
        - Barlines: | (optional separator, ignored by parser)

        Common durations: /1=whole, /2=half, /4=quarter, /8=eighth, /16=sixteenth

        Args:
            notation: The notation string to parse and enter
            staff: Staff index to navigate to before entering (0-based)
            measure: Measure number to navigate to before entering (1-based)
            written_pitch: If True, treat pitches as written pitch for transposing
                instruments and convert to concert pitch before entry

        Returns:
            Result from processSequence with all entered notes
        """
        try:
            actions = parse_notation_string(notation)
        except ValueError as e:
            return {"error": str(e)}

        if not actions:
            return {"error": "No notes or rests found in notation string"}

        # Prepend navigation if staff/measure specified
        nav_actions: list[dict[str, Any]] = []
        if measure is not None:
            nav_actions.append({
                "action": "goToMeasure",
                "params": {"measure": measure},
            })
        if staff is not None:
            # Navigate to the correct staff by going to measure on that staff
            # We use goToMeasure which puts us on staff 0, then nextStaff to reach target
            for _ in range(staff):
                nav_actions.append({
                    "action": "nextStaff",
                    "params": {},
                })

        # Handle written pitch transposition
        if written_pitch and staff is not None:
            # Query score for transposition info
            score_result = await client.send_command("getScore", {"startMeasure": 1, "endMeasure": 1})
            chromatic = 0
            analysis = score_result.get("result", score_result).get("analysis", score_result.get("result", score_result))
            if "staves" in analysis:
                for staff_info in analysis["staves"]:
                    staff_name = staff_info.get("name", "")
                    if staff_name == f"staff{staff}":
                        chromatic = staff_info.get("transposeChromatic", 0)
                        break
            if chromatic:
                from ..pitch import written_to_concert
                for action in actions:
                    if action.get("action") == "addNote" and "pitch" in action.get("params", {}):
                        action["params"]["pitch"] = written_to_concert(
                            action["params"]["pitch"], chromatic
                        )

        sequence = nav_actions + actions
        return await client.send_command("processSequence", {"sequence": sequence})
