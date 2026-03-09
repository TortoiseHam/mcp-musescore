import QtQuick 2.9
import MuseScore 3.0

MuseScore {
    id: root
    menuPath: "Plugins.MuseScore API Server"
    description: "Exposes MuseScore API via WebSocket (Clean Version)"
    version: "2.0"
    
    property var clientConnections: []
    property bool serverRunning: false
    property var selectionState: ({
        startStaff: 0,
        endStaff: 1,
        startTick: 0,
        elements: []
    })

    // ========================================
    // WEBSOCKET & MESSAGE PROCESSING
    // ========================================

    function processMessage(message, clientId) {
        console.log("Received message: " + message);
        try {
            var command = JSON.parse(message);
            var result = processCommand(command);
            api.websocketserver.send(clientId, JSON.stringify({
                status: "success",
                result: result
            }));
        } catch (e) {
            console.log("Error processing command: " + e.toString());
            api.websocketserver.send(clientId, JSON.stringify({
                status: "error",
                message: e.toString()
            }));
        }
    }

    function processCommand(command) {
        console.log("Processing command: " + command.action);
        
        switch(command.action) {
            // Core operations
            case "getScore":                return getScore(command.params);
            case "syncStateToSelection":    return syncStateToSelection();
            case "ping":                    return "pong";
            case "undo":                    return undo();
            case "describeElement":         return describeElement(command.params);
            case "exportPdf":               return exportPdf(command.params);
            case "goToBeginningOfScore":    return goToBeginningOfScore();
            case "processSequence":         return processSequence(command.params);

            // Navigation
            case "getCursorInfo":           return getCursorInfo(command.params);
            case "goToMeasure":             return goToMeasure(command.params);
            case "goToFinalMeasure":        return goToFinalMeasure(command.params);
            case "nextElement":             return nextElement(command.params);
            case "prevElement":             return prevElement(command.params);
            case "nextStaff":               return nextStaff(command.params);
            case "prevStaff":               return prevStaff(command.params);
            case "setVoice":                return setVoice(command.params);

            // Selection
            case "selectCurrentMeasure":    return selectCurrentMeasure(command.params);
            case "selectCustomRange":       return selectCustomRange(command.params);

            // Notes & Music
            case "addNote":                 return addNote(command.params);
            case "addRest":                 return addRest(command.params);
            case "addTuplet":               return addTuplet(command.params);
            case "addLyrics":               return addLyrics(command.params);
            case "addCursorElement":        return addCursorElement(command.params);
            case "addSlur":                 return addSlur();
            case "addTie":                  return addTie();
            case "addHairpin":              return addHairpin(command.params);

            // Measures
            case "appendMeasure":           return appendMeasure(command.params);
            case "insertMeasure":           return insertMeasure(command.params);
            case "deleteSelection":         return deleteSelection(command.params);

            // Staff & Instruments
            case "addInstrument":           return addInstrument(command.params);
            case "setStaffMute":            return setStaffMute(command.params);
            case "setInstrumentSound":      return setInstrumentSound(command.params);
            case "setTimeSignature":        return setTimeSignature(command.params);
            case "setTempo":                return setTempo(command.params);

            default:
                throw new Error("Unknown command: " + command.action);
        }
    }

    // ========================================
    // UTILITY FUNCTIONS
    // ========================================

    function validateParams(params, required) {
        var missing = [];
        for (var i = 0; i < required.length; i++) {
            if (params[required[i]] === undefined) {
                missing.push(required[i]);
            }
        }
        return missing.length > 0 ? { error: "Missing required parameters: " + missing.join(", ") } : { valid: true };
    }

    function executeWithUndo(operation) {
        if (!curScore) return { error: "No score open" };
        
        curScore.startCmd();
        try {
            var result = operation();
            curScore.endCmd();
            return result;
        } catch (e) {
            curScore.endCmd(true);
            return { error: e.toString() };
        }
    }

    function getNoteName(note) {
        const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        return noteNames[note % 12];
    }

    function getDurationName(duration) {
        const durationNames = ["LONG","BREVE","WHOLE","HALF","QUARTER","EIGHTH","16TH","32ND","64TH","128TH","256TH","512TH","1024TH","ZERO","MEASURE","INVALID"];
        return durationNames[duration] || "UNKNOWN";
    }

    // ========================================
    // CURSOR MANAGEMENT
    // ========================================

    function createCursor(params) {
        if (!curScore) throw new Error("No score open");
        
        if (!params || Object.keys(params).length === 0) {
            params = selectionState;
        }
        
        var cursor = curScore.newCursor();
        cursor.inputStateMode = Cursor.INPUT_STATE_SYNC_WITH_SCORE;
        
        // Set track
        if (params.startStaff !== undefined) cursor.staffIdx = params.startStaff;
        if (params.voice !== undefined) cursor.voice = params.voice;
        
        // Position cursor
        if (params.rewindMode !== undefined) {
            cursor.rewind(params.rewindMode);
        } else if (params.startTick !== undefined) {
            try {
                cursor.rewindToTick(params.startTick);
            } catch (e) {
                console.log("rewindToTick failed, using manual navigation");
                cursor.rewind(0);
                while (cursor.tick < params.startTick && cursor.next()) {}
            }
        } else if (params.measure !== undefined) {
            cursor.rewind(0);
            for (var i = 0; i < params.measure && cursor.nextMeasure(); i++) {}
        } else {
            cursor.rewind(0);
        }
        
        // Set duration
        if (params.duration) {
            cursor.setDuration(params.duration.numerator || 1, params.duration.denominator || 4);
        }
        
        return cursor;
    }

    function initCursorState() {
        if (!curScore) return "No score open";
        
        return executeWithUndo(function() {
            var cursor = curScore.newCursor();
            cursor.rewind(0);

            var startTick = cursor.tick;
            cursor.next();
            var endTick = cursor.tick;
            var element = cursor.element;

            selectionState = {
                startStaff: cursor.staffIdx,
                endStaff: cursor.staffIdx + 1,
                startTick: startTick,
                elements: element ? [processElement(element)] : []
            };
            
            curScore.selection.clear();
            curScore.selection.selectRange(startTick, endTick, 0, 0);
            
            return "Initialized at " + [startTick, endTick, 0, 0].join(',');
        });
    }

    // ========================================
    // ELEMENT PROCESSING
    // ========================================

    function processElement(element) {
        if (!element) return null;
        
        var base = {
            name: element.name,
            subtype: element.subtype,
            subtypeName: element.subtypeName,
            baseDuration: getDurationName(element.durationType ? element.durationType.type : 0),
            dotted: element.durationType ? element.durationType.dots : 0,
            durationTicks: element.actualDuration ? element.actualDuration.ticks : 0,
            tuplet: element.tuplet ? {   
                durationNumerator: element.tuplet.duration.numerator,
                durationDenominator: element.tuplet.duration.denominator,
            } : null
        };

        switch (element.name) {
            case "Note":
                return Object.assign(base, {
                    pitchMidi: element.pitch,
                    pitchName: getNoteName(element.pitch),
                    noteType: element.noteType,
                    accidental: element.accidental,
                    tieBack: element.tieBack,
                    tieForward: element.tieForward
                });
            
            case "Chord":
                return Object.assign(base, {
                    noteType: element.noteType,
                    notes: Object.keys(element.notes || {}).map(function(k) {
                        return {
                            pitchMidi: element.notes[k].pitch, 
                            pitchName: getNoteName(element.notes[k].pitch)
                        };
                    })
                });
                
            case "Rest":
                return base;
                
            default:
                return { name: element.name, properties: Object.keys(element) };
        }
    }

    // ========================================
    // CORE OPERATIONS
    // ========================================

    function undo() {
        cmd("undo");
        return { success: true, message: "Undo successful" };
    }

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

    function goToBeginningOfScore() {
        var response = initCursorState();
        return { 
            success: true, 
            message: response, 
            currentSelection: selectionState,
            currentScore: getScoreSummary()
        };
    }

    function processSequence(params) {
        if (!curScore) return { error: "No score open" };
        if (!params.sequence) return { error: "No sequence specified" };

        var validCommands = [
            "getScore", "addNote", "addRest", "addTuplet", "appendMeasure", "deleteSelection",
            "getCursorInfo", "goToMeasure", "nextElement", "prevElement", "nextStaff", "prevStaff",
            "selectCurrentMeasure", "insertMeasure", "goToFinalMeasure",
            "goToBeginningOfScore", "setTimeSignature", "addLyrics", "addInstrument",    
            "setStaffMute", "setInstrumentSound", "setTempo",
            "addCursorElement", "addSlur", "addTie", "addHairpin",
            "setVoice", "selectCustomRange", "syncStateToSelection"
        ];

        try {
            var results = [];
            for (var i = 0; i < params.sequence.length; i++) {
                var command = params.sequence[i];
                if (!validCommands.includes(command.action)) {
                    throw new Error("Invalid command: " + command.action);
                }
                var result = processCommand(command);
                results.push({action: command.action, result: result});
            }
            return { success: true, results: results, message: "Sequence processed", currentSelection: selectionState };
        } catch (e) {
            return { error: e.toString() };
        }
    }

    // ========================================
    // NAVIGATION FUNCTIONS
    // ========================================

    function syncStateToSelection() {
        if (!curScore) return { error: "No score open" };

        try {
            var selection = curScore.selection;
            var startSegment = selection.startSegment;
            var endSegment = selection.endSegment;

            if (startSegment && endSegment) {
                var cursor = createCursor({
                    startTick: startSegment.tick,
                    startStaff: selection.startStaff    
                });

                var elements = [];
                while (cursor.tick < endSegment.tick && cursor.element) {
                    elements.push(processElement(cursor.element));
                    if (!cursor.next()) break;
                }

                selectionState = {
                    startStaff: selection.startStaff,
                    endStaff: selection.endStaff,
                    startTick: startSegment.tick,
                    elements: elements,
                    totalDuration: elements.reduce(function(a, b) { return a + (b.durationTicks || 0); }, 0)
                };

                return { success: true, currentSelection: selectionState };
            } else {
                return { success: false, error: "No valid selection found" };
            }
        } catch (e) {
            return { success: false, error: e.toString() };
        }
    }

    function getCursorInfo(params) {
        if (!curScore) return { error: "No score open" };
        
        syncStateToSelection();
        return { 
            success: true, 
            currentSelection: selectionState, 
            currentScore: params && params.verbose !== "false" ? getScoreSummary() : null
        };
    }

    function goToMeasure(params) {
        var validation = validateParams(params, ["measure"]);
        if (!validation.valid) return validation;

        return executeWithUndo(function() {
            var score = getScoreSummary();
            var measure = score.measures[params.measure - 1];
            var startTick = measure.startTick;
            
            var cursor = createCursor({ startTick: startTick, startStaff: selectionState.startStaff });
            var element = processElement(cursor.element);
            var staffIdx = selectionState.startStaff;
            
            curScore.selection.clear();
            curScore.selection.selectRange(startTick, startTick + element.durationTicks, staffIdx, staffIdx + 1);
            
            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };
            
            return { success: true, currentSelection: selectionState };
        });
    }

    function nextElement(params) {
        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: selectionState.startStaff 
            });

            var numElements = params && params.numElements || 1;
            var success = true;
            for (var i = 0; i < numElements && success; i++) {
                success = cursor.next();
            }
            
            if (success) {
                var element = processElement(cursor.element);
                var startTick = cursor.tick;
                var staffIdx = cursor.staffIdx;
                
                // Check if we need to append a measure
                if (startTick + element.durationTicks >= curScore.lastSegment.tick) {
                    cmd("append-measure");
                }

                curScore.selection.clear();
                curScore.selection.selectRange(startTick, startTick + element.durationTicks, staffIdx, staffIdx + 1);

                selectionState = {
                    startStaff: staffIdx,
                    endStaff: staffIdx + 1,
                    startTick: startTick,
                    elements: [element],
                    totalDuration: element.durationTicks
                };
                
                return { success: true, currentSelection: selectionState };
            } else {
                return { success: false, message: "End of score reached" };
            }
        });
    }

    function prevElement(params) {
        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: selectionState.startStaff 
            });

            var endTick = cursor.tick;
            var numElements = params && params.numElements || 1;
            var success = true;
            
            for (var i = 0; i < numElements && success; i++) {
                success = cursor.prev();
            }

            if (success) {
                var element = processElement(cursor.element);
                var startTick = cursor.tick;
                var staffIdx = cursor.staffIdx;
                
                curScore.selection.clear();
                curScore.selection.selectRange(startTick, endTick, staffIdx, staffIdx + 1);

                selectionState = {
                    startStaff: staffIdx,
                    endStaff: staffIdx + 1,
                    startTick: startTick,
                    elements: [element],
                    totalDuration: endTick - startTick
                };
                
                return { success: true, currentSelection: selectionState };
            } else {
                return { success: false, message: "Beginning of score reached" };
            }
        });
    }

    function nextStaff(params) {
        return executeWithUndo(function() {
            syncStateToSelection();

            if (selectionState.endStaff >= curScore.nstaves) {
                return { success: false, message: "Already at last staff" };
            }

            var newStaff = selectionState.endStaff;
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: newStaff 
            });

            var element = processElement(cursor.element);
            
            curScore.selection.clear();
            curScore.selection.selectRange(
                selectionState.startTick, 
                selectionState.startTick + element.durationTicks, 
                newStaff, 
                newStaff + 1
            );

            selectionState = {
                startStaff: newStaff,
                endStaff: newStaff + 1,
                startTick: selectionState.startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { success: true, currentSelection: selectionState };
        });
    }

    function prevStaff(params) {
        return executeWithUndo(function() {
            syncStateToSelection();

            if (selectionState.startStaff <= 0) {
                return { success: false, message: "Already at first staff" };
            }

            var newStaff = selectionState.startStaff - 1;
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: newStaff 
            });

            var element = processElement(cursor.element);
            
            curScore.selection.clear();
            curScore.selection.selectRange(
                selectionState.startTick, 
                selectionState.startTick + element.durationTicks, 
                newStaff, 
                newStaff + 1
            );

            selectionState = {
                startStaff: newStaff,
                endStaff: newStaff + 1,
                startTick: selectionState.startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { success: true, currentSelection: selectionState };
        });
    }

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

    function goToFinalMeasure(params) {
        return executeWithUndo(function() {
            var cursor = createCursor({ startTick: 0 });
            var count = 0;
            var startTick = 0;

            while (cursor.nextMeasure()) {
                startTick = cursor.tick;
                count++;
            }

            if (count === 0) {
                return { success: false, message: "Already at the last measure" };
            }

            cursor.rewindToTick(startTick);
            cursor.next();
            var endTick = cursor.tick;
            var staffIdx = cursor.staffIdx;
            
            curScore.selection.clear();
            curScore.selection.selectRange(startTick, endTick, staffIdx, staffIdx + 1);
            
            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [processElement(cursor.element)],
                totalDuration: endTick - startTick
            };

            return { success: true, currentSelection: selectionState };
        });
    }

    // ========================================
    // SELECTION FUNCTIONS
    // ========================================

    function selectCurrentMeasure() {
        return executeWithUndo(function() {
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: selectionState.startStaff 
            });

            var currTick = cursor.tick;
            var currStaff = cursor.staffIdx;
            var scoreSummary = getScoreSummary();

            var measureIdx = scoreSummary.measures.filter(function(measure) { 
                return measure.startTick <= currTick; 
            }).length - 1;
            
            var measure = scoreSummary.measures[measureIdx];
            var measureElements = measure.elements[`staff${currStaff}`];
            var totalDuration = measureElements.reduce(function(a, b) { 
                return a + (b.durationTicks || 0); 
            }, 0);
            var measureEndTick = measure.startTick + totalDuration;

            curScore.selection.clear();
            curScore.selection.selectRange(measure.startTick, measureEndTick, currStaff, currStaff + 1);

            selectionState = {
                startStaff: currStaff,
                endStaff: currStaff + 1,
                startTick: measure.startTick,
                elements: measureElements,
                totalDuration: totalDuration
            };

            return { 
                success: true, 
                message: `Selected measure ${measureIdx + 1}`, 
                currentSelection: selectionState
            };
        });
    }

    function selectCustomRange(params) {
        var validation = validateParams(params, ["startTick", "endTick", "startStaff", "endStaff"]);
        if (!validation.valid) return validation;

        return executeWithUndo(function() {
            var cursor = createCursor({ 
                startTick: params.startTick, 
                startStaff: params.startStaff 
            });

            var element = processElement(cursor.element);
            
            curScore.selection.clear();
            curScore.selection.selectRange(params.startTick, params.endTick, params.startStaff, params.endStaff);

            selectionState = {
                startStaff: params.startStaff,
                endStaff: params.endStaff,
                startTick: params.startTick,
                elements: [element],
                totalDuration: params.endTick - params.startTick
            };

            return { success: true, message: "Selection updated", currentSelection: selectionState };
        });
    }

    // ========================================
    // NOTE & MUSIC OPERATIONS
    // ========================================

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
            syncStateToSelection();

            return {
                success: true,
                message: params.elementType + " added",
                currentSelection: selectionState
            };
        });
    }

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

    function addNote(params) {
        var validation = validateParams(params, ["pitch", "duration", "advanceCursorAfterAction"]);
        if (!validation.valid) return validation;

        if (!params.duration.numerator || !params.duration.denominator) {
            return { error: "Duration must be specified as { numerator: int, denominator: int }" };
        }

        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor();
            cursor.setDuration(params.duration.numerator, params.duration.denominator);
            
            // Check if current position has a rest
            var hasRest = selectionState.elements.some(function(element) { 
                return element.name === "Rest"; 
            });

            cursor.addNote(params.pitch, !hasRest);
            cursor.rewindToTick(selectionState.startTick);

            if (params.advanceCursorAfterAction) {
                cursor.next();
            }

            var element = processElement(cursor.element);
            var startTick = cursor.tick;
            var staffIdx = cursor.staffIdx;

            curScore.selection.clear();
            curScore.selection.selectRange(startTick, startTick + element.durationTicks, staffIdx, staffIdx + 1);
            
            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { 
                success: true, 
                message: "Note added with pitch " + params.pitch,
                currentSelection: selectionState
            };
        });
    }

    function addRest(params) {
        var validation = validateParams(params, ["duration", "advanceCursorAfterAction"]);
        if (!validation.valid) return validation;

        if (!params.duration.numerator || !params.duration.denominator) {
            return { error: "Duration must be specified as { numerator: int, denominator: int }" };
        }

        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor();
            cursor.setDuration(params.duration.numerator, params.duration.denominator);
            cursor.addRest();
            cursor.rewindToTick(selectionState.startTick);

            if (params.advanceCursorAfterAction) {
                cursor.next();
            }

            var element = processElement(cursor.element);
            var startTick = cursor.tick;
            var staffIdx = cursor.staffIdx;

            curScore.selection.clear();
            curScore.selection.selectRange(startTick, startTick + element.durationTicks, staffIdx, staffIdx + 1);

            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { success: true, message: "Rest added", currentSelection: selectionState };
        });
    }

    function addTuplet(params) {
        var validation = validateParams(params, ["ratio", "duration", "advanceCursorAfterAction"]);
        if (!validation.valid) return validation;

        if (!params.ratio.numerator || !params.ratio.denominator || 
            !params.duration.numerator || !params.duration.denominator) {
            return { error: "Ratio and duration must be specified as { numerator: int, denominator: int }" };
        }
        
        return executeWithUndo(function() {
            var cursor = createCursor();
            cursor.setDuration(params.duration.numerator, params.duration.denominator);
            
            var ratio = fraction(params.ratio.numerator, params.ratio.denominator);
            var duration = fraction(params.duration.numerator, params.duration.denominator);
            
            cursor.addTuplet(ratio, duration);
            cursor.next();

            if (params.advanceCursorAfterAction) {
                cursor.next();
            }

            var element = processElement(cursor.element);
            var startTick = cursor.tick;
            var staffIdx = cursor.staffIdx;

            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: startTick,
                elements: [element],
                totalDuration: element.durationTicks
            };

            return { 
                success: true, 
                message: "Tuplet " + params.ratio.numerator + ":" + params.ratio.denominator + " added",
                currentSelection: selectionState
            };
        });
    }

    function addLyrics(params) {
        if (!params.lyrics || !Array.isArray(params.lyrics) || params.lyrics.length === 0) {
            return { error: "Lyrics must be specified as an array of strings" };
        }
        
        return executeWithUndo(function() {
            syncStateToSelection();
            
            var cursor = createCursor({ 
                startTick: selectionState.startTick, 
                startStaff: selectionState.startStaff 
            });
            
            var lyricsArray = params.lyrics.slice();
            var verse = params.verse || 0;
            var addedCount = 0;
            var skippedCount = 0;
            
            while (cursor.element && lyricsArray.length > 0) {
                var element = cursor.element;
                
                if (element.type === Element.CHORD || element.name === "Chord") {
                    var lyr = newElement(Element.LYRICS);
                    lyr.text = lyricsArray.shift();
                    lyr.verse = verse;
                    
                    cursor.add(lyr);
                    addedCount++;
                } else if (element.type === Element.REST || element.name === "Rest") {
                    skippedCount++;
                }
                
                if (!cursor.next()) break;
            }
            
            var finalElement = processElement(cursor.element) || selectionState.elements[0];
            var finalTick = cursor.tick;
            var staffIdx = cursor.staffIdx;
            
            selectionState = {
                startStaff: staffIdx,
                endStaff: staffIdx + 1,
                startTick: finalTick,
                elements: [finalElement],
                totalDuration: finalElement.durationTicks || selectionState.totalDuration
            };
            
            curScore.selection.clear();
            curScore.selection.selectRange(finalTick, finalTick + (finalElement.durationTicks || 0), staffIdx, staffIdx + 1);
            
            var message = `Added ${addedCount} lyrics`;
            if (skippedCount > 0) message += `, skipped ${skippedCount} rests`;
            if (lyricsArray.length > 0) message += `, ${lyricsArray.length} lyrics remaining`;
            
            return { 
                success: true, 
                message: message,
                addedCount: addedCount,
                skippedCount: skippedCount,
                remainingLyrics: lyricsArray,
                currentSelection: selectionState
            };
        });
    }

    // ========================================
    // MEASURE OPERATIONS
    // ========================================

    function appendMeasure(params) {
        return executeWithUndo(function() {
            var count = params && params.count || 1;
            
            for (var i = 0; i < count; i++) {
                cmd("append-measure");
            }
            
            return { 
                success: true, 
                message: count + " measure(s) appended",
                currentSelection: selectionState
            };
        });
    }

    function insertMeasure(params) {
        return executeWithUndo(function() {
            cmd("insert-measure");
            syncStateToSelection();
            
            return { 
                success: true, 
                message: "Measure inserted",
                currentSelection: selectionState
            };
        });
    }

    function deleteSelection(params) {
        return executeWithUndo(function() {
            if (params && params.measure) {
                createCursor({ measure: params.measure });
            }
            
            cmd("delete");
            
            return { 
                success: true, 
                message: "Selection deleted",
                currentSelection: selectionState
            };
        });
    }

    // ========================================
    // STAFF & INSTRUMENT OPERATIONS
    // ========================================

    function addInstrument(params) {
        var validation = validateParams(params, ["instrumentId"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            curScore.appendPart(params.instrumentId);
            return { success: true, message: "Instrument " + params.instrumentId + " added" };
        });
    }

    function setStaffMute(params) {
        var validation = validateParams(params, ["staff"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            var staff = curScore.staves && curScore.staves[params.staff] || 
                       (typeof curScore.staff === "function" ? curScore.staff(params.staff) : null);
            
            if (staff) {
                staff.invisible = Boolean(params.mute);
                return { success: true, message: "Staff " + (params.mute ? "muted" : "unmuted") };
            } else {
                return { error: "Staff not found" };
            }
        });
    }

    function setInstrumentSound(params) {
        var validation = validateParams(params, ["staff", "instrumentId"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            cmd("instruments");
            return { success: true, message: "Instrument dialog opened, manual selection required" };
        });
    }

    function setTimeSignature(params) {
        var validation = validateParams(params, ["numerator", "denominator"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            var cursor = createCursor();
            var currTick = cursor.tick;
            var currStaff = cursor.staffIdx;

            var ts = newElement(Element.TIMESIG);
            ts.timesig = fraction(params.numerator, params.denominator);
            cursor.add(ts);

            return { 
                success: true, 
                message: "Time signature set to " + params.numerator + "/" + params.denominator
            };
        });
    }

    function setTempo(params) {
        var validation = validateParams(params, ["bpm"]);
        if (!validation.valid) return validation;
        
        return executeWithUndo(function() {
            var cursor = createCursor();
            
            var tempo = newElement(Element.TEMPO_TEXT);
            tempo.tempo = params.bpm / 60.0;
            tempo.text = params.text || ("♩ = " + params.bpm);
            
            cursor.add(tempo);
            
            return { success: true, message: "Tempo set to " + params.bpm + " BPM" };
        });
    }

    // ========================================
    // SCORE ANALYSIS
    // ========================================

    function getScore(params) {
        if (!curScore) return { error: "No score open" };

        try {
            return { success: true, analysis: getScoreSummary(params) };
        } catch (e) {
            return { error: e.toString() };
        }
    }

    function getScoreSummary(params) {
        if (!curScore) return { error: "No score open" };

        return executeWithUndo(function() {
            var tempState = selectionState;

            // Parse filter params (only when called from getScore with explicit params)
            var startMeasure = params && params.startMeasure ? params.startMeasure : 1;
            var endMeasure = params && params.endMeasure ? params.endMeasure : curScore.nmeasures;
            var filterStaves = params && params.staves ? params.staves : null;

            var score = {
                numMeasures: curScore.nmeasures,
                measures: [],
                staves: []
            };

            // Analyze staves
            for (var i = 0; i < curScore.nstaves; i++) {
                if (filterStaves && filterStaves.indexOf(i) === -1) continue;

                var staff = curScore.staves && curScore.staves[i] ||
                           (typeof curScore.staff === "function" ? curScore.staff(i) : null);

                score.staves.push({
                    name: `staff${i}`,
                    shortName: staff ? staff.shortName : "",
                    visible: staff ? !staff.invisible : true
                });
            }

            // Walk all measure boundaries for correct tick mapping
            var cursor = createCursor({startTick: 0});
            var measureBoundaries = [];
            var allMeasures = [];

            for (var i = 0; i < curScore.nmeasures; i++) {
                measureBoundaries.push(cursor.tick);

                // Only include measures in the requested range
                if (i + 1 >= startMeasure && i + 1 <= endMeasure) {
                    var measure = {
                        measure: i + 1,
                        startTick: cursor.tick,
                        numElements: 0,
                        elements: {}
                    };

                    for (var j = 0; j < curScore.nstaves; j++) {
                        if (filterStaves && filterStaves.indexOf(j) === -1) continue;
                        measure.elements[`staff${j}`] = [];
                    }

                    allMeasures.push({index: i, measure: measure});
                    score.measures.push(measure);
                }

                cursor.nextMeasure();
            }

            // Process elements for each staff
            for (var k = 0; k < curScore.nstaves; k++) {
                if (filterStaves && filterStaves.indexOf(k) === -1) continue;

                cursor.rewind(0);
                cursor.staffIdx = k;

                while (cursor.element) {
                    var measureIdx = measureBoundaries.filter(function(tick) {
                        return tick <= cursor.tick;
                    }).length - 1;

                    // Only process if this measure is in the requested range
                    if (measureIdx + 1 >= startMeasure && measureIdx + 1 <= endMeasure) {
                        // Find the corresponding measure in our filtered list
                        var filteredIdx = -1;
                        for (var m = 0; m < allMeasures.length; m++) {
                            if (allMeasures[m].index === measureIdx) {
                                filteredIdx = m;
                                break;
                            }
                        }

                        if (filteredIdx >= 0) {
                            score.measures[filteredIdx].numElements++;

                            var processedElement = processElement(cursor.element);
                            if (processedElement) {
                                processedElement.startTick = cursor.tick;
                                score.measures[filteredIdx].elements[`staff${k}`].push(processedElement);
                            }
                        }
                    }

                    if (!cursor.next()) break;
                }
            }

            // Restore state
            selectionState = tempState;
            return score;
        });
    }

    // ========================================
    // INITIALIZATION
    // ========================================

    onRun: {
        if (serverRunning) {
            console.log("MuseScore API Server is already running on port 8765");
            return;
        }

        console.log("Starting MuseScore API Server on port 8765");

        api.websocketserver.listen(8765, function(clientId) {
            console.log("Client connected with ID: " + clientId);
            clientConnections.push(clientId);

            api.websocketserver.onMessage(clientId, function(message) {
                processMessage(message, clientId);
            });
        });

        serverRunning = true;

        if (curScore) {
            initCursorState();
        }
    }
}