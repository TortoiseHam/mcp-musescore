"""Transcription tips and workflow advice for MuseScore MCP."""


TRANSCRIPTION_TIPS = """
# PDF-to-MuseScore Transcription Guide

When transcribing a PDF score into MuseScore via this MCP server, follow a phased approach. Trying to do everything in a single pass leads to mistakes and makes it harder to catch errors. Work through the score multiple times, each pass focusing on a different layer.

## Phase 1: Score Setup

Before writing any notes, set up the skeleton of the score:

1. **Instruments & staves** — Add all instruments/staves in the correct order using `add_instrument`. Match the PDF's layout top to bottom.
2. **Time signature** — Set the initial time signature with `set_time_signature`. If it changes mid-piece, you'll handle that in Phase 2.
3. **Measures** — Use `append_measure` to create roughly the right number of measures. You can always add or remove later.

## Phase 2: Structure & Road Map

Walk through the PDF and mark up the structural elements that define the road map of the piece. This pass is about getting the form right before filling in content:

1. **Key signatures** — Note where key changes occur and set them at the correct measures.
2. **Time signature changes** — If the meter changes mid-piece, place those now.
3. **Tempo markings** — Set tempo at the beginning and at any tempo changes.
4. **Rehearsal marks** — If the score has rehearsal letters/numbers, place them.
5. **Repeat barlines & endings** — Mark repeat signs, first/second endings (voltas), D.C., D.S., coda, and segno markings. Getting these right early prevents measure-numbering confusion later.
6. **Double barlines and final barlines** — Place section breaks and the final barline.

## Phase 3: Notes & Rhythms

Now fill in the actual musical content, one staff at a time:

1. **Work staff by staff** — Complete one instrument's part before moving to the next. This keeps your cursor position predictable.
2. **Work measure by measure** — Use `go_to_measure` to navigate. For each measure, add notes and rests in order using `add_note` and `add_rest`.
3. **Tuplets** — Use `add_tuplet` when you encounter triplets or other irregular groupings.
4. **Ties** — When a note is tied across a barline or within a measure, handle ties as you write the notes.
5. **Use `processSequence` for efficiency** — Batch multiple note/rest additions in a single call when you have a clear run of notes to enter. This is significantly faster than individual calls.
6. **Verify as you go** — Periodically use `get_cursor_info` and `get_score` to confirm you're in the right place. It's easier to fix a mistake in the current measure than to discover it 30 measures later.

## Phase 4: Articulations, Dynamics & Expression

With all the notes in place, add the expressive layer:

1. **Dynamics** — Place p, f, mf, crescendo/decrescendo markings.
2. **Articulations** — Staccato, accent, tenuto, fermata, etc.
3. **Slurs & phrase marks** — Draw slurs connecting the appropriate notes.
4. **Ornaments** — Trills, turns, mordents, grace notes.
5. **Text expressions** — "dolce", "con brio", "rit.", "a tempo", etc.

## Phase 5: Lyrics (if applicable)

If the score has vocal parts with lyrics:

1. **Enter lyrics verse by verse** — Use `add_lyrics` to attach words to notes. Do verse 1 for the entire piece, then verse 2, etc.
2. **Syllable alignment** — Pay attention to syllable breaks (hyphens) and melisma (underscores/extender lines) in the PDF.

## Phase 6: Review & Cleanup

1. **Compare against the PDF** — Go through the score section by section and compare with the original. Check note pitches, rhythms, dynamics, and text.
2. **Playback check** — If possible, listen to the playback to catch wrong notes or rhythm errors that are hard to spot visually.
3. **Fix measure count** — Use `insert_measure` or `delete_selection` if you ended up with too few or too many measures.

## General Tips

- **Save frequently** — MuseScore can be unpredictable. Use undo (`undo`) liberally if something goes wrong.
- **Octave awareness** — MIDI pitches: Middle C = 60. Each octave is 12 semitones. Double-check that notes are in the right octave — off-by-an-octave errors are the most common transcription mistake.
- **Read ahead in the PDF** — Before transcribing a section, scan it for repeats, key changes, or meter changes that affect how you set up the measures.
- **Enharmonic spellings** — MuseScore may spell a note differently than the PDF (e.g., F# vs Gb). Note these for later correction.
- **Transposing instruments** — If the PDF shows a transposing part (e.g., Bb Clarinet, F Horn), decide whether to enter concert pitch or written pitch based on how MuseScore is configured.
- **When in doubt, use `get_score`** — This returns the current state of the score and helps you orient yourself if you lose track of where you are.
""".strip()


def setup_tips_tools(mcp):
    """Setup transcription tips tools."""

    @mcp.tool()
    async def get_transcription_tips() -> str:
        """Get a comprehensive guide for transcribing PDF scores into MuseScore.

        Returns phased workflow advice for systematically converting a PDF score
        into a MuseScore file using this MCP server. The guide covers score setup,
        structural elements, note entry, dynamics/articulations, lyrics, and review.

        Call this at the start of any PDF transcription task to load the recommended
        workflow into context.
        """
        return TRANSCRIPTION_TIPS
