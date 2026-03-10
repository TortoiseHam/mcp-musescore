"""Tests for pitch utility functions."""

import pytest

from src.pitch import (
    parse_pitch,
    midi_to_note_name,
    ticks_to_duration_str,
    written_to_concert,
    concert_to_written,
)


class TestParsePitch:
    """Tests for parse_pitch()."""

    def test_int_passthrough(self):
        assert parse_pitch(60) == 60
        assert parse_pitch(0) == 0
        assert parse_pitch(127) == 127

    def test_int_out_of_range(self):
        with pytest.raises(ValueError):
            parse_pitch(-1)
        with pytest.raises(ValueError):
            parse_pitch(128)

    def test_known_note_names(self):
        assert parse_pitch("C4") == 60
        assert parse_pitch("Eb5") == 75
        assert parse_pitch("F#4") == 66
        assert parse_pitch("Bb3") == 58
        assert parse_pitch("A4") == 69
        assert parse_pitch("C0") == 12
        assert parse_pitch("B0") == 23

    def test_case_insensitive(self):
        assert parse_pitch("c4") == 60
        assert parse_pitch("eb5") == 75
        assert parse_pitch("f#4") == 66

    def test_double_accidentals(self):
        assert parse_pitch("C##4") == 62  # Same as D4
        assert parse_pitch("Dbb4") == 60  # Same as C4

    def test_invalid_string(self):
        with pytest.raises(ValueError):
            parse_pitch("X4")
        with pytest.raises(ValueError):
            parse_pitch("C")
        with pytest.raises(ValueError):
            parse_pitch("4C")
        with pytest.raises(ValueError):
            parse_pitch("")

    def test_invalid_type(self):
        with pytest.raises(TypeError):
            parse_pitch(60.5)  # type: ignore

    def test_midi_out_of_range_from_string(self):
        with pytest.raises(ValueError):
            parse_pitch("G#9")  # Would be 128


class TestMidiToNoteName:
    """Tests for midi_to_note_name()."""

    def test_known_values_flats(self):
        assert midi_to_note_name(60) == "C4"
        assert midi_to_note_name(75) == "Eb5"
        assert midi_to_note_name(58) == "Bb3"
        assert midi_to_note_name(69) == "A4"

    def test_known_values_sharps(self):
        assert midi_to_note_name(66, prefer_flats=False) == "F#4"
        assert midi_to_note_name(75, prefer_flats=False) == "D#5"
        assert midi_to_note_name(58, prefer_flats=False) == "A#3"

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            midi_to_note_name(-1)
        with pytest.raises(ValueError):
            midi_to_note_name(128)

    def test_round_trip(self):
        """Every MIDI value should round-trip through note name and back."""
        for midi in range(128):
            name = midi_to_note_name(midi, prefer_flats=True)
            assert parse_pitch(name) == midi, f"Round-trip failed for MIDI {midi} -> {name}"

    def test_round_trip_sharps(self):
        """Round-trip with sharps."""
        for midi in range(128):
            name = midi_to_note_name(midi, prefer_flats=False)
            assert parse_pitch(name) == midi, f"Round-trip failed for MIDI {midi} -> {name}"


class TestTicksToDurationStr:
    """Tests for ticks_to_duration_str()."""

    def test_basic_durations(self):
        assert ticks_to_duration_str("QUARTER", 0) == "/4"
        assert ticks_to_duration_str("HALF", 0) == "/2"
        assert ticks_to_duration_str("WHOLE", 0) == "/1"
        assert ticks_to_duration_str("EIGHTH", 0) == "/8"
        assert ticks_to_duration_str("16TH", 0) == "/16"

    def test_dotted(self):
        assert ticks_to_duration_str("QUARTER", 1) == "/4."
        assert ticks_to_duration_str("HALF", 2) == "/2.."

    def test_unknown_duration(self):
        assert ticks_to_duration_str("UNKNOWN", 0) == "/UNKNOWN"


class TestTransposition:
    """Tests for written_to_concert and concert_to_written."""

    def test_bb_clarinet(self):
        # Bb clarinet: chromatic_transpose = -2
        # Written C4 (60) sounds as Bb3 (58)
        assert written_to_concert(60, -2) == 58
        assert concert_to_written(58, -2) == 60

    def test_no_transposition(self):
        assert written_to_concert(60, 0) == 60
        assert concert_to_written(60, 0) == 60

    def test_round_trip(self):
        for midi in range(12, 116):
            for transpose in [-7, -5, -2, 0, 2, 5, 7]:
                concert = written_to_concert(midi, transpose)
                assert concert_to_written(concert, transpose) == midi
