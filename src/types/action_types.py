"""TypedDict definitions for MuseScore MCP action sequences."""

from typing import Dict, Any, List, Literal, Optional
from typing_extensions import TypedDict, NotRequired


class GetScoreParams(TypedDict, total=False):
    startMeasure: int
    endMeasure: int
    staves: List[int]


class GetScoreAction(TypedDict):
    action: Literal["getScore"]
    params: GetScoreParams


class AddNoteParams(TypedDict):
    pitch: int
    duration: Dict[Literal["numerator", "denominator"], int]
    advanceCursorAfterAction: bool


class AddNoteAction(TypedDict):
    action: Literal["addNote"]
    params: AddNoteParams


class AddRestParams(TypedDict):
    duration: Dict[Literal["numerator", "denominator"], int]
    advanceCursorAfterAction: bool


class AddRestAction(TypedDict):
    action: Literal["addRest"]
    params: AddRestParams


class AddTupletParams(TypedDict):
    duration: Dict[Literal["numerator", "denominator"], int]
    ratio: Dict[Literal["numerator", "denominator"], int]
    advanceCursorAfterAction: bool


class AddTupletAction(TypedDict):
    action: Literal["addTuplet"]
    params: AddTupletParams


class AddLyricsParams(TypedDict):
    lyrics: List[str]
    verse: int


class AddLyricsAction(TypedDict):
    action: Literal["addLyrics"]
    params: AddLyricsParams


class AddInstrumentParams(TypedDict):
    instrumentId: str


class AddInstrumentAction(TypedDict):
    action: Literal["addInstrument"]
    params: AddInstrumentParams


class SetStaffMuteParams(TypedDict):
    staff: int
    mute: bool


class SetStaffMuteAction(TypedDict):
    action: Literal["setStaffMute"]
    params: SetStaffMuteParams


class SetInstrumentSoundParams(TypedDict):
    staff: int
    instrumentId: str


class SetInstrumentSoundAction(TypedDict):
    action: Literal["setInstrumentSound"]
    params: SetInstrumentSoundParams


class AppendMeasureAction(TypedDict):
    action: Literal["appendMeasure"]
    params: Dict[str, Any]


class DeleteSelectionAction(TypedDict):
    action: Literal["deleteSelection"]
    params: Dict[str, Any]


class GetCursorInfoParams(TypedDict, total=False):
    verbose: str


class GetCursorInfoAction(TypedDict):
    action: Literal["getCursorInfo"]
    params: GetCursorInfoParams


class GoToMeasureParams(TypedDict):
    measure: int


class GoToMeasureAction(TypedDict):
    action: Literal["goToMeasure"]
    params: GoToMeasureParams


class NextElementParams(TypedDict, total=False):
    numElements: int


class NextElementAction(TypedDict):
    action: Literal["nextElement"]
    params: NextElementParams


class PrevElementParams(TypedDict, total=False):
    numElements: int


class PrevElementAction(TypedDict):
    action: Literal["prevElement"]
    params: PrevElementParams


class SelectCurrentMeasureAction(TypedDict):
    action: Literal["selectCurrentMeasure"]
    params: Dict[str, Any]


class InsertMeasureAction(TypedDict):
    action: Literal["insertMeasure"]
    params: Dict[str, Any]


class GoToFinalMeasureAction(TypedDict):
    action: Literal["goToFinalMeasure"]
    params: Dict[str, Any]


class GoToBeginningOfScoreAction(TypedDict):
    action: Literal["goToBeginningOfScore"]
    params: Dict[str, Any]


class SetTimeSignatureParams(TypedDict):
    numerator: int
    denominator: int


class SetTimeSignatureAction(TypedDict):
    action: Literal["setTimeSignature"]
    params: SetTimeSignatureParams


class UndoAction(TypedDict):
    action: Literal["undo"]
    params: Dict[str, Any]


class NextStaffAction(TypedDict):
    action: Literal["nextStaff"]
    params: Dict[str, Any]


class PrevStaffAction(TypedDict):
    action: Literal["prevStaff"]
    params: Dict[str, Any]


class SetTempoParams(TypedDict):
    bpm: float
    text: NotRequired[str]


class SetTempoAction(TypedDict):
    action: Literal["setTempo"]
    params: SetTempoParams


class SelectCustomRangeParams(TypedDict):
    startTick: int
    endTick: int
    startStaff: int
    endStaff: int


class SelectCustomRangeAction(TypedDict):
    action: Literal["selectCustomRange"]
    params: SelectCustomRangeParams


class SyncStateToSelectionAction(TypedDict):
    action: Literal["syncStateToSelection"]
    params: Dict[str, Any]


class AddCursorElementParams(TypedDict):
    elementType: str
    properties: NotRequired[Dict[str, Any]]


class AddCursorElementAction(TypedDict):
    action: Literal["addCursorElement"]
    params: AddCursorElementParams


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


ActionSequence = List[
    GetScoreAction | AddNoteAction | AddRestAction | AddTupletAction |
    AddLyricsAction | AddInstrumentAction | SetStaffMuteAction |
    SetInstrumentSoundAction | AppendMeasureAction | DeleteSelectionAction |
    GetCursorInfoAction | GoToMeasureAction | NextElementAction |
    PrevElementAction | SelectCurrentMeasureAction | InsertMeasureAction |
    GoToFinalMeasureAction | GoToBeginningOfScoreAction | SetTimeSignatureAction |
    UndoAction | NextStaffAction | PrevStaffAction | SetTempoAction |
    SelectCustomRangeAction | SyncStateToSelectionAction |
    AddCursorElementAction | AddSlurAction | AddTieAction | AddHairpinAction
]
