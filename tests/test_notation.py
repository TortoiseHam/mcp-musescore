"""Tests for notation string parser."""

import pytest

from src.tools.notation import parse_notation_string, _parse_duration


class TestParseDuration:
    """Tests for _parse_duration()."""

    def test_basic(self):
        assert _parse_duration("/4") == {"numerator": 1, "denominator": 4}
        assert _parse_duration("/2") == {"numerator": 1, "denominator": 2}
        assert _parse_duration("/1") == {"numerator": 1, "denominator": 1}
        assert _parse_duration("/8") == {"numerator": 1, "denominator": 8}
        assert _parse_duration("/16") == {"numerator": 1, "denominator": 16}

    def test_dotted(self):
        # Dotted quarter = 3/8
        assert _parse_duration("/4.") == {"numerator": 3, "denominator": 8}
        # Double-dotted half = 7/8
        assert _parse_duration("/2..") == {"numerator": 7, "denominator": 8}
        # Dotted half = 3/4
        assert _parse_duration("/2.") == {"numerator": 3, "denominator": 4}
        # Dotted eighth = 3/16
        assert _parse_duration("/8.") == {"numerator": 3, "denominator": 16}

    def test_invalid(self):
        with pytest.raises(ValueError):
            _parse_duration("4")  # missing /
        with pytest.raises(ValueError):
            _parse_duration("")


class TestParseNotationString:
    """Tests for parse_notation_string()."""

    def test_simple_notes(self):
        actions = parse_notation_string("C4/4 D4/4 E4/4 F4/4")
        assert len(actions) == 4
        assert all(a["action"] == "addNote" for a in actions)
        assert actions[0]["params"]["pitch"] == 60
        assert actions[1]["params"]["pitch"] == 62
        assert actions[2]["params"]["pitch"] == 64
        assert actions[3]["params"]["pitch"] == 65

    def test_rest(self):
        actions = parse_notation_string("r/4")
        assert len(actions) == 1
        assert actions[0]["action"] == "addRest"
        assert actions[0]["params"]["duration"] == {"numerator": 1, "denominator": 4}

    def test_multi_measure_rest(self):
        actions = parse_notation_string("R*3")
        assert len(actions) == 3
        assert all(a["action"] == "addRest" for a in actions)
        assert all(a["params"]["duration"] == {"numerator": 1, "denominator": 1} for a in actions)

    def test_tie(self):
        actions = parse_notation_string("Eb5/4~ Eb5/4")
        assert len(actions) == 3
        assert actions[0]["action"] == "addNote"
        assert actions[0]["params"]["pitch"] == 75
        assert actions[1]["action"] == "addTie"
        assert actions[2]["action"] == "addNote"

    def test_barline_separator(self):
        actions = parse_notation_string("C4/4 | D4/4")
        assert len(actions) == 2
        assert actions[0]["params"]["pitch"] == 60
        assert actions[1]["params"]["pitch"] == 62

    def test_dotted_note(self):
        actions = parse_notation_string("C4/4.")
        assert len(actions) == 1
        assert actions[0]["params"]["duration"] == {"numerator": 3, "denominator": 8}

    def test_mixed(self):
        actions = parse_notation_string("r/4 Eb5/4 F5/4 G5/4 | Ab5/1")
        assert len(actions) == 5
        assert actions[0]["action"] == "addRest"
        assert actions[1]["action"] == "addNote"
        assert actions[1]["params"]["pitch"] == 75  # Eb5
        assert actions[4]["params"]["duration"] == {"numerator": 1, "denominator": 1}

    def test_invalid_token(self):
        with pytest.raises(ValueError):
            parse_notation_string("X")  # no duration

    def test_empty_string(self):
        actions = parse_notation_string("")
        assert actions == []
