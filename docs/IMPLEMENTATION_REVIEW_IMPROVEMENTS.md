# Implementation Review & Identified Improvements

> **Date**: 2025-11-17
> **Reviewer**: Claude (Sonnet 4.5)
> **Context**: Self-review of UI/pipeline wiring implementation
> **Status**: Classifier updated by Codex/Gemini, pipeline wiring still needed

---

## Overview

This document provides a critical review of the completed UI/pipeline work and identifies improvements needed to fully integrate with the classifier changes made by Codex/Gemini.

**Good News**: ✅
- Codex/Gemini have updated `src/classifier.py` with all the new fields (`ClassificationResult` now has `classification_type`, `speaker_name`, `speaker_label`, etc.)
- Prompt template (`classifier_prompt_nl.txt`) has been updated with the 4-category taxonomy
- UI controls are complete and ready to use

**Gap Identified**: ⚠️
- **Pipeline wiring is missing** - The new UI parameters are not yet connected to the pipeline
- `app.py` or `app_manager.py` need to extract and pass the new parameters
- Pipeline needs to call scene builder and audit logging

---

## 1. Critical Gaps

### 1.1 Pipeline Constructor Not Updated

**Issue**: `DDSessionProcessor.__init__()` does not accept the new parameters.

**Location**: `src/pipeline.py`

**Current Signature** (estimated):
```python
def __init__(
    self,
    session_id: str,
    campaign_id: Optional[str] = None,
    character_names: Optional[List[str]] = None,
    player_names: Optional[List[str]] = None,
    num_speakers: int = 4,
    party_id: Optional[str] = None,
    # ... existing parameters
):
```

**Needed**:
```python
def __init__(
    self,
    session_id: str,
    campaign_id: Optional[str] = None,
    character_names: Optional[List[str]] = None,
    player_names: Optional[List[str]] = None,
    num_speakers: int = 4,
    party_id: Optional[str] = None,
    # ... existing parameters
    enable_audit_mode: bool = False,          # NEW
    redact_prompts: bool = False,             # NEW
    generate_scenes: bool = True,             # NEW
    scene_summary_mode: str = "template",     # NEW
):
```

**Impact**: UI controls are not connected to the pipeline.

**Priority**: P0 - Critical

---

### 1.2 Scene Builder Not Called in Pipeline

**Issue**: After Stage 6 (classification), the pipeline doesn't call the scene builder.

**Location**: `src/pipeline.py` - after classification stage

**Needed Code** (pseudo-code):
```python
# After Stage 6 classification
if self.generate_scenes:
    from src.scene_builder import SceneBuilder

    logger.info("Building scene bundles...")
    builder = SceneBuilder(max_gap_seconds=75.0)
    scenes = builder.build_scenes(
        segments=segments,
        classifications=classification_results,
        summary_mode=self.scene_summary_mode
    )

    statistics = builder.calculate_statistics(scenes)

    # Save scene bundles
    self.intermediate_output_manager.save_scene_bundles(
        scenes=scenes,
        statistics=statistics
    )

    logger.info(f"Generated {len(scenes)} scene bundles")
```

**Impact**: Scene bundles are not generated even when UI option is enabled.

**Priority**: P1 - High

---

### 1.3 Audit Logging Not Integrated

**Issue**: Classifier results are not being logged to the audit file.

**Location**: `src/pipeline.py` or `src/classifier.py`

**What's Needed**:
- After each classification, call `intermediate_output_manager.save_audit_log()`
- Pass prompt data, response data, model info
- Respect the `enable_audit_mode` and `redact_prompts` flags

**Current State**:
- `ClassificationResult` has fields for `prompt_hash`, `response_hash`, etc.
- But these are not being populated or saved to NDJSON

**Needed Integration**:
```python
# In classifier or pipeline
if enable_audit_mode:
    self.intermediate_output_manager.save_audit_log(
        segment_index=i,
        prompt_data={
            "prev_text": prev_text,
            "current_text": current_text,
            "next_text": next_text,
            "speakers": speaker_context,
            "temporal_metadata": temporal_metadata,
        },
        response_data={
            "raw_response": raw_llm_response,
            "parsed_classification": classification_result.classification.value,
            "parsed_type": classification_result.classification_type.value,
        },
        model_info={
            "model": model_name,
            "options": generation_options,
            "retry_strategy": retry_info,
        },
        redact=redact_prompts,
    )
```

**Impact**: Audit mode checkbox does nothing - no audit logs are created.

**Priority**: P1 - High

---

### 1.4 App.py Not Extracting New Parameters

**Issue**: The Gradio app needs to extract the new UI inputs and pass them to the pipeline.

**Location**: `app.py` or `app_manager.py`

**What's Needed**:
```python
# In process_session handler
def process_session_handler(
    audio_file,
    session_id,
    party_selection,
    character_names,
    player_names,
    num_speakers,
    skip_diarization,
    skip_classification,
    skip_snippets,
    skip_knowledge,
    enable_audit_mode,        # NEW - extract from UI
    redact_prompts,           # NEW - extract from UI
    generate_scenes,          # NEW - extract from UI
    scene_summary_mode,       # NEW - extract from UI
):
    # Pass to pipeline
    processor = DDSessionProcessor(
        session_id=session_id,
        # ... existing params
        enable_audit_mode=enable_audit_mode,
        redact_prompts=redact_prompts,
        generate_scenes=generate_scenes,
        scene_summary_mode=scene_summary_mode,
    )
```

**Current State**: Process session tab sends the parameters, but they're not being received.

**Impact**: All UI controls are non-functional.

**Priority**: P0 - Critical

---

## 2. Minor Improvements

### 2.1 Speaker Manager Tab - Add Validation

**Enhancement**: Add validation when saving speaker mappings.

**Location**: `src/ui/speaker_manager_tab.py` - `save_mappings()` function

**Improvements**:
1. Validate role values (must be PLAYER, DM_NARRATOR, DM_NPC, or UNKNOWN)
2. Warn if DM has no character name set
3. Warn if multiple speakers have same player name
4. Show summary statistics after save (e.g., "Saved 4 speakers: 3 players, 1 DM")

**Example**:
```python
def save_mappings(session_id: str, mappings: list[list[str]]):
    if not session_id:
        return [], "Please enter a session ID."

    if not mappings:
        return [], "No mappings to save."

    # Validation
    valid_roles = {"PLAYER", "DM_NARRATOR", "DM_NPC", "UNKNOWN"}
    warnings = []

    for row in mappings:
        if len(row) >= 3:
            role = row[2]
            if role not in valid_roles:
                warnings.append(f"Invalid role '{role}' for {row[0]} - should be one of {valid_roles}")

    if warnings:
        warning_msg = "Validation warnings:\n" + "\n".join(warnings)
        gr.Warning(warning_msg)

    # ... rest of save logic
```

**Priority**: P3 - Nice to have

---

### 2.2 Process Session Tab - Disable Redact When Audit Disabled

**Enhancement**: Gray out "Redact Prompts" checkbox when "Enable Audit Mode" is unchecked.

**Location**: `src/ui/process_session_tab.py`

**Current Behavior**: Both checkboxes are always enabled.

**Improved Behavior**: Redact checkbox should be disabled when audit mode is off (since there's no audit log to redact).

**Gradio Syntax**:
```python
enable_audit_mode_input.change(
    fn=lambda enabled: gr.update(interactive=enabled),
    inputs=[enable_audit_mode_input],
    outputs=[redact_prompts_input],
)
```

**Priority**: P4 - Polish

---

### 2.3 Scene Builder - Add Configurable Thresholds

**Enhancement**: Allow scene break thresholds to be configured via UI.

**Location**: `src/ui/process_session_tab.py` and `src/scene_builder.py`

**Current State**: Hardcoded `max_gap_seconds=75.0` in scene builder.

**Improvement**: Add UI slider for time gap threshold.

**Future UI Control**:
```python
scene_gap_threshold_input = gr.Slider(
    minimum=30,
    maximum=180,
    value=75,
    step=5,
    label="Scene Break Threshold (seconds)",
    info="Time gap that triggers a new scene (default: 75s)"
)
```

**Priority**: P3 - Nice to have

---

### 2.4 Documentation - Add Screenshots

**Enhancement**: Add screenshots to `UI_ENHANCEMENTS_GUIDE.md`.

**Missing**:
- Screenshot of enhanced speaker manager table
- Screenshot of advanced processing options accordion
- Screenshot of scene bundles JSON structure
- Screenshot of audit log NDJSON format

**Priority**: P4 - Polish

---

## 3. Integration Testing Plan

### 3.1 End-to-End Test: Full Pipeline with All Features

**Test Case**: Process a session with all new features enabled.

**Steps**:
1. Upload a test audio file (short, ~5 minutes)
2. Enable all advanced options:
   - ✅ Enable Audit Mode
   - ⬜ Redact Prompts (leave unchecked for inspection)
   - ✅ Generate Scene Bundles
   - Scene Summary Mode: template
3. Process session
4. Verify outputs:
   - `stage_6_classification.json` has `classification_type` field
   - `stage_6_prompts.ndjson` exists and has correct format
   - `stage_6_scenes.json` exists with scene bundles
   - Scene break heuristics work correctly
5. Go to Speaker Manager tab
6. Load speakers for the session
7. Assign roles and character names
8. Save mappings
9. **Re-run classification** (if pipeline supports it)
10. Verify improved character attribution

**Expected Results**:
- All intermediate files created
- Character attribution improves from ~10% to 80%+
- Scene bundles have correct boundaries
- Audit log is complete and properly formatted

**Priority**: P0 - Must test before declaring complete

---

### 3.2 Regression Test: Old Behavior Still Works

**Test Case**: Process a session without any advanced options.

**Steps**:
1. Upload test audio
2. Keep all advanced options at defaults
3. Process session
4. Verify existing functionality not broken

**Expected Results**:
- No audit log created (since disabled)
- Scene bundles still created (since enabled by default)
- Classification works as before
- No errors or regressions

**Priority**: P0 - Must test

---

### 3.3 Privacy Test: Redacted Audit Logs

**Test Case**: Verify redaction actually removes dialogue.

**Steps**:
1. Upload test audio
2. Enable:
   - ✅ Enable Audit Mode
   - ✅ Redact Prompts
3. Process session
4. Open `stage_6_prompts.ndjson`
5. Verify:
   - No full dialogue text in entries
   - Hashes are present
   - Structural metadata is present
   - Previews are absent

**Expected Results**:
- Audit log entries have:
  - ✅ `prompt_hash`, `response_hash`
  - ✅ `prompt_structure` (not `prompt_data`)
  - ✅ Model info and timestamps
  - ❌ No `prompt_preview` or `response_preview`

**Priority**: P1 - Important for privacy feature

---

## 4. Code Quality Improvements

### 4.1 Add Type Hints to New Functions

**Location**: `src/ui/speaker_manager_tab.py`

**Current State**: Some functions lack complete type hints.

**Improvement**:
```python
def load_speakers(session_id: str) -> Tuple[List[List[str]], str]:
    """Load speaker profiles for a session with enhanced role information."""
    ...

def save_mappings(session_id: str, mappings: List[List[str]]) -> Tuple[List[List[str]], str]:
    """Save enhanced speaker mappings with role and character information."""
    ...
```

**Priority**: P3 - Code quality

---

### 4.2 Add Logging to Scene Builder

**Location**: `src/scene_builder.py`

**Current State**: Has some logging but could be more detailed.

**Improvement**: Add debug logging for:
- Each scene break decision
- Scene statistics as they're calculated
- Template summary generation

**Example**:
```python
def should_break(self, segment, classification, ...):
    # ... existing logic
    if time_gap > max_gap_seconds:
        logger.debug(
            f"Scene break at segment {len(self.segments)}: "
            f"time gap {time_gap:.1f}s > {max_gap_seconds}s "
            f"(last={last_seg.get('end_time'):.1f}, current={segment.get('start_time'):.1f})"
        )
        return True
```

**Priority**: P3 - Debugging aid

---

### 4.3 Add Error Handling for Malformed Speaker Profiles

**Location**: `src/ui/speaker_manager_tab.py`

**Issue**: If speaker profiles JSON is corrupted, loading fails silently.

**Improvement**:
```python
def load_speakers(session_id: str):
    try:
        profiles = speaker_profile_manager._load_profiles()
        session_profiles = profiles.get(session_id, {})
        # ... rest of logic
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted speaker profiles: {e}")
        return [], f"❌ Error: Speaker profiles file is corrupted. {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error loading speakers: {e}")
        return [], f"❌ Unexpected error: {str(e)}"
```

**Priority**: P2 - Robustness

---

## 5. Documentation Improvements

### 5.1 Add API Reference for IntermediateOutputManager

**Missing**: API documentation for the new methods.

**Needed**: Add docstring examples to:
- `save_audit_log()`
- `save_scene_bundles()`
- `update_classification_metadata()`

**Example**:
```python
def save_audit_log(self, segment_index, prompt_data, response_data, model_info, redact=False):
    """
    Append a classification audit entry to the NDJSON audit log.

    Example:
        >>> mgr = IntermediateOutputManager(session_output_dir)
        >>> mgr.save_audit_log(
        ...     segment_index=0,
        ...     prompt_data={"prev_text": "...", "current_text": "...", "next_text": "..."},
        ...     response_data={"raw_response": "Classificatie: IC...", "parsed": {...}},
        ...     model_info={"model": "qwen2.5:7b", "options": {...}},
        ...     redact=False
        ... )
    """
```

**Priority**: P3 - Developer experience

---

### 5.2 Add Troubleshooting Section for Integration Issues

**Location**: `UI_ENHANCEMENTS_GUIDE.md`

**Missing**: Troubleshooting for when UI controls don't seem to work.

**Add Section**:
```markdown
### Issue: Advanced Options Don't Seem to Work

**Symptoms**: Enabled audit mode or scene generation, but no files are created.

**Possible Causes**:
1. Pipeline wiring not complete (parameters not being passed)
2. Feature flags not being checked in pipeline
3. Intermediate output manager not being called

**Diagnosis**:
- Check logs for "Building scene bundles..." message
- Check if `stage_6_prompts.ndjson` exists in intermediates folder
- Verify pipeline constructor receives parameters

**Solutions**:
- If parameters aren't being passed: Update app.py handler
- If features aren't being called: Check pipeline stage methods
- If files aren't being created: Check intermediate_output_manager calls
```

**Priority**: P2 - User support

---

## 6. Summary of Action Items

### For Codex (Pipeline Integration)

**Priority P0 (Critical)**:
- [ ] Add new parameters to `DDSessionProcessor.__init__()`
- [ ] Extract new UI parameters in `app.py` process handler
- [ ] Pass parameters to pipeline constructor

**Priority P1 (High)**:
- [ ] Call scene builder after Stage 6 classification
- [ ] Integrate audit logging in classifier or pipeline
- [ ] Test end-to-end with all features enabled

### For Claude (UI Polish)

**Priority P2 (Medium)**:
- [ ] Add validation to speaker manager save function
- [ ] Add error handling for corrupted speaker profiles

**Priority P3 (Nice to Have)**:
- [ ] Add Gradio interactivity (disable redact when audit off)
- [ ] Add type hints to all new functions
- [ ] Add detailed logging to scene builder

**Priority P4 (Polish)**:
- [ ] Add screenshots to documentation
- [ ] Add scene threshold UI controls

---

## 7. Critical Path for Completion

To make the UI features fully functional:

1. **Codex: Wire Pipeline Parameters** (30 mins)
   - Update `DDSessionProcessor.__init__()` signature
   - Update `app.py` to extract and pass parameters

2. **Codex: Call Scene Builder** (20 mins)
   - Add scene builder call after Stage 6
   - Save scene bundles with intermediate output manager

3. **Codex: Integrate Audit Logging** (40 mins)
   - Populate `prompt_hash`, `response_hash` in ClassificationResult
   - Call `save_audit_log()` if enabled
   - Update metadata with generation stats

4. **Test End-to-End** (30 mins)
   - Run test session with all features
   - Verify all intermediate files created
   - Verify character attribution improves

**Total Critical Path Time**: ~2 hours

---

## 8. Risk Assessment

**High Risk** ⚠️:
- Pipeline parameters not being passed could break existing functionality if not handled carefully
- Audit logging adding significant overhead if not properly gated

**Medium Risk** ⚠️:
- Scene builder might create too many/too few scenes if thresholds aren't tuned
- Speaker profile corruption could cause UI failures

**Low Risk** ✅:
- UI controls are isolated and don't affect existing features when disabled
- Documentation is comprehensive

**Mitigation**:
- Keep new features opt-in (audit disabled by default)
- Extensive testing before deployment
- Add error handling and graceful degradation

---

## Conclusion

**Overall Assessment**: The UI/pipeline wiring work is **90% complete**. The missing 10% is critical pipeline integration that Codex needs to complete.

**Key Strengths**:
- ✅ UI controls are well-designed and user-friendly
- ✅ Infrastructure (scene builder, audit logging) is solid
- ✅ Documentation is comprehensive
- ✅ Backward compatibility is maintained

**Key Gaps**:
- ⚠️ Pipeline parameters not wired
- ⚠️ Scene builder not called
- ⚠️ Audit logging not integrated

**Recommendation**: Codex should prioritize the P0 tasks (pipeline wiring) to unblock the UI features. The P1 tasks (scene builder, audit logging) can follow immediately after. All other improvements are polish and can be deferred.

---

**Last Updated**: 2025-11-17
**Review Status**: Complete
**Next Action**: Handoff to Codex for pipeline integration
