"""Transcription tips and workflow advice for MuseScore MCP."""


TRANSCRIPTION_TIPS = """
# PDF-to-MuseScore Transcription Guide

When transcribing a PDF score into MuseScore via this MCP server, follow a phased approach. Trying to do everything in a single pass leads to mistakes and makes it harder to catch errors. Work through the score multiple times, each pass focusing on a different layer.

For long or complex scores, the key principle is: **keep your working context small and verifiable.** Never try to hold the entire score in your head at once. Work in short sections, verify often, and build up incrementally.

## Phase 0: Reconnaissance

Before touching MuseScore, study the PDF and build a mental map of the piece. This phase prevents the most common catastrophic errors (wrong measure count, missed repeats, misidentified structure).

1. **Count measures carefully** — Go through the PDF and count total measures, grouped by system (line) and page. Write down: "Page 1: systems of 4, 4, 4 measures = 12. Page 2: 4, 4, 4, 3 = 15..." Off-by-one measure errors cascade through the entire transcription and are extremely painful to fix later.
2. **Map the form** — Identify the large-scale structure: intro, verse, chorus, bridge, coda, etc. Note which sections repeat and which are unique. A typical pop song might have only 30-40 measures of unique material despite being 80+ measures long.
3. **Identify repeated/copied sections** — Flag sections that are identical or near-identical to earlier ones. You'll transcribe these once and duplicate, potentially cutting your work in half or more.
4. **Note hazards** — Flag anything tricky: key changes, meter changes, cue notes, ossia staves, complex tuplet nesting, divisi passages, cross-staff notation. Knowing where the hard parts are lets you plan around them.
5. **Catalog the elements** — Make a quick inventory: How many instruments? Any transposing instruments? Lyrics? Multiple verses? What dynamics and articulations are used? This determines which phases you'll need.

## Phase 1: Score Setup

With your map in hand, set up the skeleton:

1. **Instruments & staves** — Add all instruments/staves in the correct order using `add_instrument`. Match the PDF's layout top to bottom.
2. **Time signature** — Set the initial time signature with `set_time_signature`. If it changes mid-piece, you'll handle that in Phase 2.
3. **Measures** — Use `append_measure` to create the exact number of measures from your Phase 0 count. Getting this right now saves enormous headaches later.

## Phase 2: Structure & Road Map

Walk through the PDF and mark up the structural elements that define the road map of the piece. This pass is about getting the form right before filling in content:

1. **Key signatures** — Note where key changes occur and set them at the correct measures.
2. **Time signature changes** — If the meter changes mid-piece, place those now.
3. **Tempo markings** — Set tempo at the beginning and at any tempo changes.
4. **Rehearsal marks** — If the score has rehearsal letters/numbers, place them.
5. **Repeat barlines & endings** — Mark repeat signs, first/second endings (voltas), D.C., D.S., coda, and segno markings. Getting these right early prevents measure-numbering confusion later.
6. **Double barlines and final barlines** — Place section breaks and the final barline.

## Phase 3: Notes & Rhythms

Now fill in the actual musical content. **Work in short sections (8-16 measures) across all staves, not one staff through the entire piece.** This keeps your working context small, makes verification possible, and lets you check that the vertical harmony between parts makes sense.

### Section-by-section workflow:

For each section (e.g., measures 1-8, then 9-16, etc.):

1. **Enter notes for all staves in this section** — Use `go_to_measure` to navigate. For each measure, add notes and rests in order using `add_note` and `add_rest`. Complete all staves for this section before moving on.
2. **Tuplets** — Use `add_tuplet` when you encounter triplets or other irregular groupings.
3. **Ties** — When a note is tied across a barline or within a measure, handle ties as you write the notes.
4. **Use `processSequence` for efficiency, but keep batches small** — Batch 1-2 measures at a time. Larger batches are faster but if there's an error, you have to undo the entire batch and redo it. The sweet spot is batching enough to be efficient but small enough that mistakes are cheap to fix.
5. **Verification gate** — After completing each section, STOP and verify against the PDF before moving to the next section. Use `get_score` and `get_cursor_info` to confirm measure contents, note pitches, and rhythms. Do not proceed until the section is correct. Errors that accumulate over 50+ measures become nearly impossible to untangle.

### Exploiting repetition:

After transcribing unique sections, duplicate material for repeated sections rather than re-transcribing from scratch. If measures 33-48 are identical to measures 1-16, copy rather than re-enter. This is faster and eliminates a source of inconsistency.

## Phase 4: Articulations, Dynamics & Expression

With all the notes in place, add the expressive layer. Again, work section by section:

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

1. **Compare against the PDF section by section** — Go through the score and compare with the original. Check note pitches, rhythms, dynamics, and text.
2. **Spot-check harmonic checkpoints** — At cadences and key structural moments, verify the full vertical chord across all staves matches the PDF. This catches wrong notes that might sound plausible in isolation.
3. **Playback check** — If possible, listen to the playback to catch wrong notes or rhythm errors that are hard to spot visually.
4. **Fix measure count** — Use `insert_measure` or `delete_selection` if you ended up with too few or too many measures.

## General Tips

- **Save frequently** — MuseScore can be unpredictable. Use undo (`undo`) liberally if something goes wrong.
- **Octave awareness** — MIDI pitches: Middle C = 60. Each octave is 12 semitones. Double-check that notes are in the right octave — off-by-an-octave errors are the most common transcription mistake.
- **Read ahead in the PDF** — Before transcribing a section, scan it for repeats, key changes, or meter changes that affect how you set up the measures.
- **Enharmonic spellings** — MuseScore may spell a note differently than the PDF (e.g., F# vs Gb). Note these for later correction.
- **Transposing instruments** — If the PDF shows a transposing part (e.g., Bb Clarinet, F Horn), decide whether to enter concert pitch or written pitch based on how MuseScore is configured.
- **When in doubt, use `get_score`** — This returns the current state of the score and helps you orient yourself if you lose track of where you are.
- **Don't fight momentum** — If a particular passage is proving difficult, mark it and move on. Come back to hard spots after the easy sections are done. Getting 90% of the score entered correctly is better than getting stuck on measure 12.
- **Treat the PDF page layout as a reference grid** — Know which measures are on which page and system. When you need to re-check something, you can go straight to the right spot in the PDF instead of scanning through the whole document.
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
