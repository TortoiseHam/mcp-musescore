"""Pitch utility functions for note name parsing and MIDI conversion."""

import re

_NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

_FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_PITCH_RE = re.compile(r"^([A-Ga-g])(#{1,2}|b{1,2})?(-?\d)$")


def parse_pitch(pitch: int | str) -> int:
    """Parse a pitch value (MIDI int or note name string) to a MIDI number.

    Args:
        pitch: MIDI number (0-127) or note name like "C4", "Eb5", "F#4", "Bb3"

    Returns:
        MIDI pitch number (0-127)

    Examples:
        >>> parse_pitch(60)
        60
        >>> parse_pitch("C4")
        60
        >>> parse_pitch("Eb5")
        75
        >>> parse_pitch("F#4")
        66
        >>> parse_pitch("Bb3")
        58
    """
    if isinstance(pitch, int):
        if not 0 <= pitch <= 127:
            raise ValueError(f"MIDI pitch must be 0-127, got {pitch}")
        return pitch

    if not isinstance(pitch, str):  # type: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"Pitch must be int or str, got {type(pitch).__name__}")

    m = _PITCH_RE.match(pitch)
    if not m:
        raise ValueError(
            f"Invalid pitch string: '{pitch}'. "
            "Expected format: note letter + optional accidental + octave, e.g. 'C4', 'Eb5', 'F#4'"
        )

    letter, accidental, octave_str = m.groups()
    base = _NOTE_BASE[letter.upper()]
    acc = 0
    if accidental:
        acc = accidental.count("#") - accidental.count("b")
    midi = (int(octave_str) + 1) * 12 + base + acc

    if not 0 <= midi <= 127:
        raise ValueError(f"Pitch '{pitch}' resolves to MIDI {midi}, which is outside 0-127")

    return midi


def midi_to_note_name(midi: int, prefer_flats: bool = True) -> str:
    """Convert a MIDI pitch number to a human-readable note name.

    Args:
        midi: MIDI pitch number (0-127)
        prefer_flats: If True, use flats (Eb); if False, use sharps (D#)

    Returns:
        Note name string like "Eb5", "C4", "F#4"
    """
    if not 0 <= midi <= 127:
        raise ValueError(f"MIDI pitch must be 0-127, got {midi}")

    octave = midi // 12 - 1
    semitone = midi % 12
    table = _FLAT_NAMES if prefer_flats else _SHARP_NAMES
    return f"{table[semitone]}{octave}"


_DURATION_MAP = {
    "WHOLE": 1,
    "HALF": 2,
    "QUARTER": 4,
    "EIGHTH": 8,
    "16TH": 16,
    "32ND": 32,
    "64TH": 64,
    "128TH": 128,
    "BREVE": 0.5,
    "LONG": 0.25,
}


def ticks_to_duration_str(base_duration: str, dots: int, ticks: int = 0) -> str:
    """Convert a MuseScore duration enum + dot count to a readable string.

    Falls back to tick-based calculation if base_duration is unreliable (e.g. "LONG").

    Args:
        base_duration: Duration name like "QUARTER", "EIGHTH", "HALF"
        dots: Number of dots (0, 1, 2)
        ticks: Duration in ticks (480 = quarter note). Used as fallback.

    Returns:
        Duration string like "/4", "/4.", "/4.."
    """
    # If baseDuration is unreliable, calculate from ticks
    if base_duration == "LONG" and ticks > 0:
        return _ticks_to_duration(ticks)

    denom = _DURATION_MAP.get(base_duration)
    if denom is None:
        if ticks > 0:
            return _ticks_to_duration(ticks)
        return f"/{base_duration}"
    if isinstance(denom, float):
        return f"/{denom}{'.' * dots}"
    return f"/{denom}{'.' * dots}"


# Ticks per duration at 480 ticks/quarter
_TICKS_TABLE = [
    (1920 * 4, "/0.25"),    # long
    (1920 * 2, "/0.5"),     # breve
    (1920, "/1"),            # whole
    (960, "/2"),             # half
    (480, "/4"),             # quarter
    (240, "/8"),             # eighth
    (120, "/16"),            # 16th
    (60, "/32"),             # 32nd
    (30, "/64"),             # 64th
]


def _ticks_to_duration(ticks: int) -> str:
    """Convert tick count to a duration string, handling dotted values."""
    # Check for exact matches first (undotted)
    for t, s in _TICKS_TABLE:
        if ticks == t:
            return s

    # Check for dotted values: dotted = base * 1.5, double-dotted = base * 1.75
    for t, s in _TICKS_TABLE:
        if ticks == t + t // 2:  # dotted
            return s + "."
        if ticks == t + t // 2 + t // 4:  # double-dotted
            return s + ".."

    # Fallback: show as tick count
    return f"/{ticks}t"


def written_to_concert(midi: int, chromatic_transpose: int) -> int:
    """Convert written pitch to concert pitch.

    For transposing instruments, the written pitch differs from concert pitch.
    E.g., Bb Clarinet: chromatic_transpose = -2 (written C sounds as Bb).
    Concert = written + chromatic_transpose.

    Args:
        midi: Written MIDI pitch
        chromatic_transpose: Chromatic transposition interval (negative = sounds lower)

    Returns:
        Concert pitch MIDI number
    """
    return midi + chromatic_transpose


def concert_to_written(midi: int, chromatic_transpose: int) -> int:
    """Convert concert pitch to written pitch.

    Args:
        midi: Concert MIDI pitch
        chromatic_transpose: Chromatic transposition interval

    Returns:
        Written pitch MIDI number
    """
    return midi - chromatic_transpose
