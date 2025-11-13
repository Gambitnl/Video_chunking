# Process Session Tab - Manual Testing Checklist

## Overview

This checklist ensures comprehensive manual testing of the Process Session tab after Refactor #10 (Agents I, J, K). Use this to verify that all functionality works correctly in a real browser environment.

**Testing Environment**: Real Gradio app running in browser

**Estimated Time**: 45-60 minutes for complete checklist

---

## Pre-Testing Setup

### Environment Setup

- [ ] Application launches without errors (`python app.py`)
- [ ] Process Session tab loads and renders
- [ ] No console errors in browser DevTools
- [ ] All CSS styles load correctly

### Test Data Preparation

- [ ] Have test audio files ready:
  - [ ] Valid `.wav` file
  - [ ] Valid `.mp3` file
  - [ ] Valid `.m4a` file
  - [ ] Invalid file type (e.g., `.txt`)
- [ ] Have at least one party configuration available
- [ ] Have a campaign created (optional, for campaign testing)

---

## Section 1: Upload Section

### File Upload Component

- [ ] **Upload valid .wav file**
  - [ ] File uploads successfully
  - [ ] File name displays correctly
  - [ ] No error messages shown

- [ ] **Upload valid .mp3 file**
  - [ ] File uploads successfully
  - [ ] File name displays correctly

- [ ] **Upload valid .m4a file**
  - [ ] File uploads successfully
  - [ ] File name displays correctly

- [ ] **Upload valid .flac file** (if available)
  - [ ] File uploads successfully
  - [ ] File name displays correctly

- [ ] **Upload invalid file type**
  - [ ] File rejected OR error shown after validation
  - [ ] Clear error message displayed

### File History Warning

- [ ] **Upload new file (never processed)**
  - [ ] No warning displayed
  - [ ] File warning component hidden

- [ ] **Upload previously processed file**
  - [ ] Warning message appears
  - [ ] Warning shows when file was processed
  - [ ] Warning shows session ID from previous processing
  - [ ] Warning is styled prominently (yellow/orange)

- [ ] **Change to different file**
  - [ ] Warning clears if new file not processed
  - [ ] Warning updates if new file was processed

---

## Section 2: Party Selection

### Party Dropdown

- [ ] **Dropdown populates correctly**
  - [ ] "Manual Entry" appears first
  - [ ] All configured parties appear
  - [ ] Dropdown is searchable/filterable

- [ ] **Select "Manual Entry"**
  - [ ] Character display section hidden OR shows instructions
  - [ ] Character names input becomes required
  - [ ] Player names input becomes required

- [ ] **Select a configured party**
  - [ ] Party character list appears
  - [ ] All characters displayed correctly
  - [ ] Character names prefilled in hidden input (if applicable)
  - [ ] Player names prefilled in hidden input (if applicable)

- [ ] **Switch between parties**
  - [ ] Character list updates immediately
  - [ ] No delays or glitches
  - [ ] Previous selection clears properly

### Party Character Display

- [ ] **Character list formatting**
  - [ ] Characters listed clearly
  - [ ] Readable font and spacing
  - [ ] Scrollable if many characters

---

## Section 3: Session Configuration

### Session ID Input

- [ ] **Enter valid session ID**
  - [ ] Accepts alphanumeric, hyphens, underscores
  - [ ] No validation errors

- [ ] **Enter invalid session ID**
  - [ ] Validation error on processing
  - [ ] Clear error message about allowed characters

- [ ] **Leave session ID empty**
  - [ ] Validation error on processing
  - [ ] Clear error message

### Speaker Count Slider

- [ ] **Adjust slider**
  - [ ] Slider moves smoothly
  - [ ] Value updates in real-time
  - [ ] Range is 2-10 speakers
  - [ ] Default value is correct (4 or campaign default)

### Language Dropdown

- [ ] **Dropdown populates**
  - [ ] Languages listed (English, Spanish, etc.)
  - [ ] Default is "English"

- [ ] **Select different language**
  - [ ] Selection updates correctly
  - [ ] No errors

### Manual Entry Inputs (When Manual Entry Selected)

- [ ] **Character Names Input**
  - [ ] Accepts comma-separated names
  - [ ] Placeholder text helpful
  - [ ] Trims whitespace correctly

- [ ] **Player Names Input**
  - [ ] Accepts comma-separated names
  - [ ] Placeholder text helpful
  - [ ] Trims whitespace correctly

- [ ] **Mismatched counts**
  - [ ] Validation error if character/player counts don't match num_speakers
  - [ ] Error message clear and helpful

### Backend Settings Accordion

- [ ] **Accordion expands/collapses**
  - [ ] Smooth animation
  - [ ] Icon changes (arrow or chevron)

- [ ] **Transcription Backend Dropdown**
  - [ ] Options listed (Whisper, Groq, etc.)
  - [ ] Default value sensible

- [ ] **Diarization Backend Dropdown**
  - [ ] Options listed (PyAnnote, etc.)
  - [ ] Default value sensible

- [ ] **Classification Backend Dropdown**
  - [ ] Options listed (Ollama, OpenAI, etc.)
  - [ ] Default value sensible

### Pipeline Stage Toggles

- [ ] **Skip Diarization Checkbox**
  - [ ] Toggles on/off
  - [ ] Default value correct

- [ ] **Skip Classification Checkbox**
  - [ ] Toggles on/off
  - [ ] Default value correct

- [ ] **Skip Snippets Checkbox**
  - [ ] Toggles on/off
  - [ ] Default value correct (usually True)

- [ ] **Skip Knowledge Checkbox**
  - [ ] Toggles on/off
  - [ ] Default value correct

---

## Section 4: Processing Controls

### Preflight Button

- [ ] **Click preflight with valid config**
  - [ ] Button triggers action
  - [ ] Status message appears
  - [ ] Success message if all checks pass
  - [ ] Results section stays hidden

- [ ] **Click preflight with invalid config**
  - [ ] Error message displays
  - [ ] Error details are clear
  - [ ] No processing occurs

- [ ] **Click preflight without audio file**
  - [ ] Should work (preflight doesn't need audio)
  - [ ] Validates configuration only

### Process Button

- [ ] **Click process with valid inputs**
  - [ ] Button triggers processing
  - [ ] Status changes to "Processing..."
  - [ ] Button disables during processing (if applicable)
  - [ ] Event log clears

- [ ] **Click process with missing audio file**
  - [ ] Validation error displays
  - [ ] Error message: "No audio file uploaded"
  - [ ] Processing does not start

- [ ] **Click process with invalid session ID**
  - [ ] Validation error displays
  - [ ] Error message about session ID format
  - [ ] Processing does not start

- [ ] **Click process with Manual Entry but no character names**
  - [ ] Validation error displays
  - [ ] Error message about missing names
  - [ ] Processing does not start

- [ ] **Click process with mismatched speaker counts**
  - [ ] Validation error displays
  - [ ] Error message about count mismatch
  - [ ] Processing does not start

### Status Display

- [ ] **Status shows "Idle" initially**
  - [ ] Default status message visible
  - [ ] Styled appropriately

- [ ] **Status updates during processing**
  - [ ] Changes to "Processing..."
  - [ ] Shows progress messages (if any)

- [ ] **Status shows success after completion**
  - [ ] Green success message
  - [ ] Confirmation text

- [ ] **Status shows errors clearly**
  - [ ] Red error styling
  - [ ] Error details visible
  - [ ] Actionable guidance

---

## Section 5: Live Progress Updates

### Transcription Progress Bar

- [ ] **Progress bar hidden initially**
  - [ ] Not visible before processing

- [ ] **Progress bar appears during transcription**
  - [ ] Becomes visible
  - [ ] Updates periodically (every 2 seconds)
  - [ ] Shows percentage (0-100%)

- [ ] **Progress bar updates smoothly**
  - [ ] No jumps or glitches
  - [ ] Incremental updates

- [ ] **Progress reaches 100% on completion**
  - [ ] Bar fills completely
  - [ ] Accurate representation

### Stage Progress Display (Runtime Updates Accordion)

- [ ] **Accordion starts collapsed**
  - [ ] Hidden by default (clean UI)

- [ ] **Accordion expands on click**
  - [ ] Shows stage progress section
  - [ ] Shows event log section

- [ ] **Stage progress shows 8 stages**
  - [ ] All 8 pipeline stages listed:
    1. Audio Preparation
    2. Transcription
    3. Diarization
    4. Classification
    5. Snippet Generation
    6. Knowledge Extraction
    7. Export
    8. Cleanup

- [ ] **Stage status indicators update**
  - [ ] ⏸ Pending (before stage starts)
  - [ ] `[...]` Running (during stage)
  - [ ] `[DONE]` Completed (after stage)
  - [ ] `[ERROR]` Failed (if error)
  - [ ] ⏭ Skipped (if stage skipped)

- [ ] **Stage timing information accurate**
  - [ ] Start times shown
  - [ ] Durations shown for completed stages
  - [ ] Progress percentages (if applicable)

### Event Log

- [ ] **Event log starts empty**
  - [ ] No entries before processing

- [ ] **Event log clears on new session start**
  - [ ] Old events removed
  - [ ] Fresh start for new session

- [ ] **Events accumulate during processing**
  - [ ] New events append to bottom
  - [ ] Old events remain visible (scrollable)
  - [ ] No duplicates

- [ ] **Event entries formatted correctly**
  - [ ] Timestamps shown (HH:MM:SS)
  - [ ] Event type indicator (ℹ ✓ ⚠ ✗ ⚙)
  - [ ] Event message clear

- [ ] **Event log is scrollable**
  - [ ] Scroll bar appears if many events
  - [ ] Auto-scrolls to latest entry (optional)

- [ ] **Copy button works**
  - [ ] Copies all log entries to clipboard
  - [ ] Format is readable

---

## Section 6: Results Display

### Results Section Visibility

- [ ] **Results hidden initially**
  - [ ] Not visible before processing

- [ ] **Results appear after successful processing**
  - [ ] Section becomes visible
  - [ ] Smooth transition (if animated)

- [ ] **Page auto-scrolls to results**
  - [ ] Scrolls to results section
  - [ ] User doesn't have to manually scroll

### Full Transcript Output

- [ ] **Full transcript displays**
  - [ ] Text is readable
  - [ ] Proper formatting (line breaks, paragraphs)
  - [ ] Scrollable if long

- [ ] **Transcript content accurate**
  - [ ] Matches expected output
  - [ ] No truncation (unless very large)

### IC (In-Character) Transcript Output

- [ ] **IC transcript displays**
  - [ ] Only in-character dialogue shown
  - [ ] Proper formatting

### OOC (Out-of-Character) Transcript Output

- [ ] **OOC transcript displays**
  - [ ] Only out-of-character dialogue shown
  - [ ] Proper formatting

### Statistics Output

- [ ] **Statistics display**
  - [ ] Markdown formatted
  - [ ] Metrics shown:
    - [ ] Duration
    - [ ] Number of speakers
    - [ ] Number of turns
    - [ ] Other relevant stats

- [ ] **Statistics accurate**
  - [ ] Values match expected results

### Snippet Export Output

- [ ] **Snippet info displays (if snippets generated)**
  - [ ] Export location shown
  - [ ] Number of snippets shown
  - [ ] Format details shown

- [ ] **Snippet info shows "No snippets" if skipped**
  - [ ] Clear message
  - [ ] Not an error

---

## Section 7: Campaign Integration

### Campaign Badge

- [ ] **Badge displays when campaign active**
  - [ ] Shows campaign name
  - [ ] Styled prominently

- [ ] **Badge shows "Manual Setup" when no campaign**
  - [ ] Clear indicator
  - [ ] Not confusing

### Campaign Defaults Loading

- [ ] **Select campaign from Campaign tab**
  - [ ] Process Session tab updates
  - [ ] Party selection auto-filled (if campaign has party)
  - [ ] Speaker count auto-filled
  - [ ] Skip flags auto-filled

- [ ] **Switch to different campaign**
  - [ ] Defaults update to new campaign
  - [ ] Previous values overwritten

- [ ] **Switch to "Manual Setup"**
  - [ ] Defaults reset to hardcoded values
  - [ ] Campaign-specific settings cleared

---

## Section 8: Error Handling

### Validation Errors

- [ ] **Multiple validation errors shown together**
  - [ ] All errors listed (not just first one)
  - [ ] Bullet-point format
  - [ ] Clear and actionable

### Processing Errors

- [ ] **Processing fails gracefully**
  - [ ] Error message displays
  - [ ] UI doesn't crash
  - [ ] User can retry

- [ ] **Backend errors (e.g., Ollama down) handled**
  - [ ] Clear error message
  - [ ] Suggests resolution (e.g., "Start Ollama server")

### Network Errors

- [ ] **Server connection lost**
  - [ ] Gradio reconnects automatically
  - [ ] Progress updates resume after reconnect

---

## Section 9: Performance

### UI Responsiveness

- [ ] **Tab loads quickly**
  - [ ] < 2 seconds initial load
  - [ ] No long delays

- [ ] **UI remains responsive during processing**
  - [ ] Can interact with other tabs
  - [ ] Polling doesn't freeze UI
  - [ ] Smooth animations

### Polling Performance

- [ ] **Polling doesn't cause lag**
  - [ ] No stuttering or freezing
  - [ ] Progress updates feel smooth

- [ ] **CPU usage reasonable**
  - [ ] Browser doesn't slow down significantly
  - [ ] Fan noise doesn't spike (if laptop)

### Memory Usage

- [ ] **Large transcripts display without issues**
  - [ ] 10k+ line transcripts load
  - [ ] Scrolling is smooth
  - [ ] No browser crashes

- [ ] **Event log doesn't grow unbounded**
  - [ ] Limited to ~500 lines
  - [ ] Old entries removed (if limit enforced)

---

## Section 10: Regression Testing

### Existing Functionality

- [ ] **All features from before refactoring still work**
  - [ ] No missing functionality
  - [ ] No behavioral changes (unless documented)

### Cross-Tab Interactions

- [ ] **Campaign tab updates Process Session tab**
  - [ ] Selecting campaign updates defaults
  - [ ] Party selection syncs

- [ ] **Session results visible in other tabs (if applicable)**
  - [ ] Session appears in session list
  - [ ] Session data accessible

---

## Section 11: Edge Cases

### Unusual Inputs

- [ ] **Very long session ID (100+ chars)**
  - [ ] Handled gracefully (error or truncation)

- [ ] **Special characters in session ID**
  - [ ] Validation catches them
  - [ ] Error message clear

- [ ] **Very large audio file (1GB+)**
  - [ ] Upload works OR error shown
  - [ ] No browser crash

- [ ] **Many speakers (10)**
  - [ ] Slider allows 10
  - [ ] Processing handles it

### Rapid Interactions

- [ ] **Click process button multiple times quickly**
  - [ ] Only processes once
  - [ ] No duplicate sessions

- [ ] **Switch parties rapidly**
  - [ ] Character display updates correctly
  - [ ] No race conditions

- [ ] **Upload multiple files in succession**
  - [ ] Last upload is used
  - [ ] No confusion

---

## Section 12: Browser Compatibility (Optional)

### Chrome/Chromium

- [ ] All tests pass in Chrome
- [ ] No console errors
- [ ] Styling correct

### Firefox

- [ ] All tests pass in Firefox
- [ ] No console errors
- [ ] Styling correct

### Safari (if available)

- [ ] All tests pass in Safari
- [ ] No console errors
- [ ] Styling correct

---

## Post-Testing Summary

### Issues Found

| Issue | Severity | Description | Status |
|-------|----------|-------------|--------|
|       |          |             |        |
|       |          |             |        |

### Overall Assessment

- [ ] **All critical functionality works**
- [ ] **No major bugs found**
- [ ] **Performance is acceptable**
- [ ] **UI is polished and professional**
- [ ] **Ready for production** ✅

### Tester Notes

*(Add any additional observations, suggestions, or concerns)*

---

## Checklist Metadata

**Last Updated**: 2025-11-13
**Refactoring Version**: Refactor #10 (Agents I, J, K)
**Estimated Completion Time**: 45-60 minutes
**Tested By**: _________________
**Testing Date**: _________________
**App Version/Commit**: _________________
