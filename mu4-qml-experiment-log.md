# MuseScore 4 QML API Experiment Log

Tracking what works and doesn't work in MU4's QML plugin API for element addition.

## Test Score
- 4 staves, measures 4-6 have notes on staff 0
- m4: r/4 Db5/4 F5/4 Ab5/4
- m5: Ab5/1
- m6: G5/4 F5/4 Eb5/4 Db5/4

## Approaches Tested

### `cursor.add(elem)` — via addCursorElement
MU4's `Cursor::add()` has dedicated handling only for: KEYSIG, TIMESIG, CLEF, ARTICULATION (on chords), LYRICS, FINGERING, SYMBOL, NOTE, ARPEGGIO, TREMOLO, ORNAMENT, LAYOUT_BREAK, AMBITUS, MEASURE_NUMBER, SPACER, JUMP, MARKER, HBOX, STAFFTYPE_CHANGE. Everything else falls to a generic default.

| Element | Result | Notes |
|---------|--------|-------|
| DYNAMIC | WORKS | {"text": "p", "velocity": 49} — renders correctly |
| STAFF_TEXT | WORKS | {"text": "dolce"} — renders correctly |
| SYSTEM_TEXT | WORKS | {"text": "rit."} — renders correctly |
| REHEARSAL_MARK | WORKS | {"text": "A"} — renders correctly |
| FINGERING | WORKS | {"text": "3"} — renders correctly |
| TEMPO_TEXT | WORKS | {"text": "Andante", "tempo": 1.33} — renders correctly |
| INSTRUMENT_CHANGE | WORKS | {"text": "Mute"} — renders correctly |
| ARTICULATION | FIXED | cursor.add() doesn't work (subtype read-only). FIX: route through cmd("add-{subtype}") in addCursorElement. Works for: staccato, marcato, tenuto, trill, turn. NOT working: accent, sforzando. |
| HARMONY | CRASHES app | {"text": "Dbmaj7"} — crashes MuseScore |
| BAR_LINE | CRASHES app | subtypeName is read-only (errors before cursor.add); plain add reaches cursor.add() which crashes. newElement(Element.BAR_LINE) itself is fine. |
| FERMATA | Reports success, nothing renders | cursor.add() falls to generic default |

### `cmd()` — via addCmdElement
| Command | Result | Notes |
|---------|--------|-------|
| cmd("tie") | WORKS | On note with same pitch following |
| cmd("flip") | WORKS | Flips stem direction |
| cmd("add-staccato") | WORKS | Adds staccato dot |
| cmd("add-marcato") | WORKS | Adds marcato ^ |
| cmd("add-tenuto") | WORKS | Adds tenuto — |
| cmd("add-trill") | WORKS | Adds trill (ornament) |
| cmd("add-turn") | WORKS | Adds turn (ornament) |
| cmd("chord-text") | WORKS (partial) | Opens chord symbol edit mode — need to type text then escape. Loses cursor. |
| cmd("escape") | WORKS | Exits edit mode |
| cmd("add-sforzando") | No-op | Reports success, nothing renders |
| cmd("add-double-barline") | No-op | Reports success, nothing renders |
| cmd("reset-barline") | No-op | Reports success, nothing renders |
| cmd("add-accent") | No-op | Reports success, nothing renders |
| cmd("add-fermata") | No-op | Reports success, nothing renders |
| cmd("toggle-marcato") | No-op | Reports success, nothing renders |
| cmd("toggle-fermata") | No-op | Reports success, nothing renders |

### Spanner cmds with `selectRange()` only — FAILS
| Command | Result | Notes |
|---------|--------|-------|
| cmd("add-hairpin") | No-op | selectRange() sets segment range but NOT m_el. Guard fails silently. |
| cmd("add-hairpin-reverse") | No-op | Same root cause |
| cmd("add-slur") | No-op | Same root cause |
| cmd("volta") | No-op | Same root cause |

### Spanner cmds with `selectNoteElements()` — WORKS!
Uses getScoreSummary() for reliable tick positions + selectRange() to move UI cursor +
selection.select() on individual elements to populate m_el. Beat-level precision via tick math.

**CRITICAL GOTCHAS discovered during development:**
1. `selection.select()` corrupts cursor navigation state — cursor.nextMeasure() stops working after select(). FIX: collect tick positions FIRST (via getScoreSummary), THEN select elements using fresh cursors at known ticks.
2. UI cursor position matters — selection.select() may silently fail if the UI cursor isn't in the target area. FIX: call selectRange() first to move UI state, THEN select individual elements.
3. Don't nest startCmd/endCmd — getScoreSummary uses executeWithUndo internally. Don't wrap selectNoteElements in another startCmd/endCmd.

| Command | Result | Notes |
|---------|--------|-------|
| cmd("add-hairpin") | WORKS | Crescendo with beat-level precision confirmed |
| cmd("add-hairpin-reverse") | WORKS | Diminuendo with beat-level precision confirmed |
| cmd("add-slur") | WORKS | Must start on a note, not a rest. start_beat must land on a note. |
| cmd("volta") | No-op | Tried: selectRange only, selectNoteElements, no selection. All no-op. |
| cmd("add-volta") | No-op | Alternative command name — also no-op |
| cmd("volta-bracket") | No-op | Alternative command name — also no-op |

### `newElement()` — element creation
| Element | Result | Notes |
|---------|--------|-------|
| Element.HAIRPIN | Creation OK, property enumeration CRASHES | newElement() itself is safe; describeElement crash was from iterating Object.keys() |
| Element.BAR_LINE | Creation OK | cursor.add() after creation crashes though |

### `cursor.add()` with HAIRPIN spanner (obsolete approach)
| Approach | Result | Notes |
|---------|--------|-------|
| newElement + set tick/tick2/track (try/catch) + cursor.add() | No crash, no visible result | tick/tick2/track probably read-only. cursor.add() generic default doesn't handle spanners |

### `curScore.undoAddElement()` — doesn't exist in MU4
| Element | Result | Notes |
|---------|--------|-------|
| HAIRPIN | TypeError: not a function | undoAddElement is not available on MU4's Score object |

### Read-only properties on new elements in MU4
parent, track, subtype are all read-only. This blocks most "create element then configure it" approaches.

## Key Findings

### ROOT CAUSE: selectRange() vs selection.select()
- `curScore.selection.selectRange()` sets segment range BUT DOES NOT populate `m_el` (the individual element list)
- `curScore.selection.select(element, add)` DOES populate `m_el`
- `cmd("add-hairpin")` guard `noteOrRestSelected()` only checks `m_el`, not range — so it silently fails with selectRange()
- **FIX**: Use `selection.select(elem, true)` on individual note/rest elements to populate m_el before calling spanner cmd()

### selection.select() corrupts cursor state
- After calling `curScore.selection.select(elem, ...)`, cursor.nextMeasure() stops advancing
- FIX: Use two-phase approach — collect all tick positions first (via getScoreSummary or cursor walk), then create fresh cursors at each tick for element selection
- ALSO: selectRange() must be called first to move UI cursor to target area, otherwise selection.select() may not take effect

### cmd() behavior in MU4 plugins
- Working single-note cmds: tie, flip, add-staccato, add-marcato, add-tenuto, add-trill, add-turn, chord-text, escape
- NOT working cmds: add-accent, add-sforzando, add-fermata, toggle-marcato, toggle-fermata, add-double-barline, reset-barline
- Spanner cmds (add-hairpin, add-hairpin-reverse, add-slur, volta): WORK with selectNoteElements() approach
- `undoAddElement()` does not exist on MU4 Score object
- `parent`, `track`, `subtype` are read-only on new elements

### cursor.add() behavior
- Works for: DYNAMIC, STAFF_TEXT, SYSTEM_TEXT, REHEARSAL_MARK, FINGERING, TEMPO_TEXT, INSTRUMENT_CHANGE
- Doesn't render: FERMATA, ARTICULATION (subtype can't be set)
- Crashes: BAR_LINE, HARMONY

### Fixes implemented
- ARTICULATION: routed through cmd("add-{subtype}") in addCursorElement — works for staccato, marcato, tenuto, trill, turn
- HAIRPIN: selectNoteElements() + cmd("add-hairpin"/"add-hairpin-reverse") — WORKS with beat-level precision (float beats supported)
- SLUR: selectNoteElements() + cmd("add-slur") — WORKS. Must start on a note, not a rest.
- VOLTA: BROKEN. All cmd() approaches fail (volta, add-volta, volta-bracket) with any selection type. No working approach found.
- FERMATA: still broken, no working approach found

### QML gotchas
- `var` declarations at QML component level silently break the plugin. Use `property var` or declare inside functions.
- `selection.select()` corrupts cursor navigation — always collect positions before selecting.

## Current state of changes
### Files modified:
- `musescore-mcp-websocket.qml`: selectNoteElements() (two-phase with getScoreSummary + selectRange + select), addHairpin(), addSlur(), addVolta(), addCursorElement() ARTICULATION routing, addFermata(), testCmd dispatch
- `src/tools/elements.py`: add_hairpin() and add_slur() with start_beat/end_beat params, test_cmd() tool
- `src/types/action_types.py`: AddSlurParams and AddHairpinParams with beat fields
- `src/registry.py`: Updated ARTICULATION, HAIRPIN, SLUR descriptions

## Confirmed Broken (No Workaround)
- **BAR_LINE**: Cursor::add() crashes (no dedicated case, generic default crashes). QML Measure wrapper doesn't expose setEndBarLineType(). No working cmd() names found (tested: add-double-barline, reset-barline, double-barline, barline-double, add-barline-double). BarLineType enum exists in C++ (NORMAL=1, DOUBLE=2, START_REPEAT=4, END_REPEAT=8, END=0x20, etc.) but not accessible from QML.
- **VOLTA**: cmd("volta") is no-op with all selection approaches (selectRange, selectNoteElements). Also tried add-volta, volta-bracket — all no-ops.
- **HARMONY**: cursor.add() crashes MuseScore. cmd("chord-text") opens edit mode but can't programmatically type text.
- **FERMATA**: cursor.add() reports success but nothing renders. cmd("add-fermata") is no-op.

## Still To Test
- Alternative fermata approaches (check MU4 source for how fermata is added internally)
- Whether fermata can work via ARTICULATION path in Cursor::add()
