# Implementation Handoff: UI & Pipeline Wiring Complete

> **Date**: 2025-11-17
> **Completed By**: Claude (Sonnet 4.5)
> **Status**: UI and pipeline infrastructure ready for classifier integration
> **Related**: IC_OOC_CLASSIFICATION_ANALYSIS.md (Topics 1, 5, 6, 7)

---

## Executive Summary

All UI controls, pipeline wiring, and intermediate output infrastructure have been implemented to support the IC/OOC classification enhancements approved in the multi-agent review. The system is now ready for Codex and Gemini to integrate the classifier-side changes (prompts, enums, and downstream consumers).

**What's Complete**: ✅
- Enhanced speaker manager UI with role assignment and character mapping
- Process session advanced options (audit mode, scene generation)
- Intermediate output persistence (audit logs, scene bundles)
- Scene builder helper module
- Comprehensive UI documentation

**What's Pending**: ⏳
- Classifier prompt template updates
- Classification result structure changes
- Downstream consumer updates (knowledge base, character profiles)

---

## 1. Files Modified

### 1.1 UI Components

#### `src/ui/speaker_manager_tab.py` (completely rewritten)
**Changes**:
- Enhanced speaker mapping table with 5 columns (Speaker ID, Player Name, Role, Character Name, Confidence)
- Party configuration integration for auto-filling character mappings
- DM/Player/NPC role assignment controls
- DM NPC mode tracking (time ranges for when DM voices specific NPCs)
- Clear session and bulk operations

**New Functionality**:
- `load_speakers()` - Loads speaker profiles with enhanced metadata
- `load_party_mappings()` - Auto-fills character names from party config
- `save_mappings()` - Persists role and character assignments to speaker profiles
- `set_npc_mode()` - Tracks DM NPC voicing time ranges
- `clear_session()` - Removes speaker profiles for a session

**Speaker Profile Structure** (enhanced):
```json
{
  "SPEAKER_00": {
    "name": "Alice",
    "role": "PLAYER",
    "character_name": "Sha'ek Mindfa'ek",
    "confidence": 0.95,
    "embedding": [...],
    "sessions": [...]
  },
  "SPEAKER_17": {
    "name": "Jules",
    "role": "DM_NARRATOR",
    "character_name": "DM",
    "confidence": 0.98,
    "npc_modes": [
      {"npc_name": "Captain", "start_time": "05:30", "end_time": "08:45"}
    ]
  }
}
```

#### `src/ui/process_session_tab.py` (extended)
**Changes**:
- Added "Advanced Processing Options" accordion with 4 new controls
- Updated process button input wiring to include new parameters
- Updated component_refs to expose new inputs

**New UI Controls**:
1. `enable_audit_mode_input` (Checkbox) - Enable detailed audit logging
2. `redact_prompts_input` (Checkbox) - Redact dialogue text from audit logs
3. `generate_scenes_input` (Checkbox, default=True) - Generate scene bundles
4. `scene_summary_mode_input` (Dropdown) - Summary generation mode (template/llm/none)

**Updated Signature** (process_session_handler now receives):
```python
process_session_handler(
    audio_input,
    session_id_input,
    party_selection_input,
    character_names_input,
    player_names_input,
    num_speakers_input,
    skip_diarization_input,
    skip_classification_input,
    skip_snippets_input,
    skip_knowledge_input,
    enable_audit_mode_input,      # NEW
    redact_prompts_input,          # NEW
    generate_scenes_input,         # NEW
    scene_summary_mode_input,      # NEW
)
```

### 1.2 Infrastructure Modules

#### `src/intermediate_output.py` (extended)
**New Methods**:

1. **Audit Logging** (Topic 6):
   - `save_audit_log(segment_index, prompt_data, response_data, model_info, redact)` - Append NDJSON audit entry
   - `get_audit_log_path()` - Returns path to `stage_6_prompts.ndjson`
   - `update_classification_metadata(metadata)` - Merge metadata into `stage_6_classification.json`

2. **Scene Bundles** (Topic 7):
   - `save_scene_bundles(scenes, statistics)` - Save to `stage_6_scenes.json`
   - `load_scene_bundles()` - Load scene bundles and metadata

**Audit Log Format** (NDJSON):
```json
{"segment_index": 0, "timestamp": "2025-11-17T14:30:00", "prompt_hash": "abc123...", "response_hash": "def456...", "model": "qwen2.5:7b", "options": {...}, "prompt_preview": "Vorige: ...", "response_preview": "Classificatie: IC..."}
```

**Scene Bundle Format** (JSON):
```json
{
  "metadata": {"session_id": "test", "generated_at": "...", "total_scenes": 15},
  "scenes": [
    {
      "scene_index": 0,
      "start_time": 5.2,
      "end_time": 125.8,
      "duration": 120.6,
      "dominant_type": "CHARACTER",
      "speaker_list": ["SPEAKER_00", "SPEAKER_03"],
      "segment_count": 24,
      "classification_distribution": {"CHARACTER": 20, "OOC": 4},
      "confidence_span": {"min": 0.87, "max": 0.98},
      "summary": "Alice, Bob - 24 segments of in-character roleplay (2m 0s)"
    }
  ],
  "statistics": {...}
}
```

#### `src/scene_builder.py` (NEW MODULE)
**Purpose**: Build narrative scenes from classified segments.

**Classes**:
1. `SceneState` (dataclass) - Tracks state of a scene being built
   - Accumulates segments, speakers, classification counts
   - Calculates scene metadata (duration, confidence span)
   - Generates template-based summaries

2. `SceneBuilder` - Main scene building class
   - `build_scenes(segments, classifications, summary_mode)` - Build scene bundles
   - `calculate_statistics(scenes)` - Calculate aggregate scene statistics

**Scene Break Heuristics**:
- IC <-> OOC classification changes (configurable)
- Time gaps >75 seconds (configurable)
- Speaker roster changes (optional, not used by default)

**Summary Modes**:
- `template` - Fast template-based (e.g., "Alice, Bob - 15 segments of in-character roleplay (3m 20s)")
- `llm` - LLM-generated (placeholder for future implementation)
- `none` - No summaries

---

## 2. Files Created

### 2.1 Documentation

#### `docs/UI_ENHANCEMENTS_GUIDE.md` (NEW)
**Contents**:
- Complete guide to all new UI controls
- Workflow examples for common use cases
- Technical notes on file formats and metadata
- Troubleshooting guide
- Future enhancements roadmap

**Sections**:
1. Speaker Manager Tab Enhancements
2. Process Session Tab Enhancements
3. Workflow Examples (3 detailed scenarios)
4. Technical Notes (file locations, versioning, heuristics)
5. Troubleshooting (common issues and solutions)
6. Future Enhancements (planned features)

---

## 3. Integration Points for Codex/Gemini

### 3.1 Classifier Integration (Codex)

**What Needs to Be Done**:

1. **Update Classifier to Receive Speaker Context** (Topic 1):
   - Modify `src/classifier.py` to accept `speaker_map` parameter
   - Update prompt building to include speaker assignments
   - Format as: `Alice (SPEAKER_00) - plays Sha'ek Mindfa'ek`

2. **Update Prompt Templates** (Topics 1, 2, 3):
   - Extend `src/prompts/classifier_prompt_nl.txt` with:
     - Speaker context section
     - Temporal metadata preamble
     - Extended context window examples
   - Add "Unknown Speaker" handling
   - Add DM narrator vs. NPC hints

3. **Update Classification Result Structure** (Topic 5):
   - Add `classification_type` field to `ClassificationResult`
   - Extend enum to support: `CHARACTER`, `DM_NARRATION`, `NPC_DIALOGUE`, `OOC_OTHER`
   - Maintain backward compatibility with existing `classification` field (IC/OOC/MIXED)

4. **Integrate Audit Logging** (Topic 6):
   - Call `intermediate_output_manager.save_audit_log()` after each classification
   - Pass prompt_data, response_data, model_info, redact flag
   - Update metadata with generation_stats

**Example Integration Point** (pseudo-code):
```python
# In src/pipeline.py or classifier wrapper
from src.intermediate_output import IntermediateOutputManager

intermediate_mgr = IntermediateOutputManager(session_output_dir)

# Build speaker map from speaker profiles + party config
speaker_map = self._build_speaker_map(session_id)

# Pass to classifier
for i, segment in enumerate(segments):
    # Classify with speaker context
    result = classifier.classify_segment(
        segment=segment,
        prev_segment=segments[i-1] if i > 0 else None,
        next_segment=segments[i+1] if i < len(segments)-1 else None,
        speaker_map=speaker_map,
        enable_audit=enable_audit_mode,
    )

    # Save audit log if enabled
    if enable_audit_mode:
        intermediate_mgr.save_audit_log(
            segment_index=i,
            prompt_data=result.prompt_data,
            response_data=result.response_data,
            model_info=result.model_info,
            redact=redact_prompts,
        )
```

### 3.2 Scene Builder Integration (Pipeline)

**What Needs to Be Done**:

1. **Wire Scene Builder into Pipeline** (after Stage 6):
   ```python
   # In src/pipeline.py after classification
   if generate_scenes:
       from src.scene_builder import SceneBuilder

       builder = SceneBuilder(max_gap_seconds=75.0)
       scenes = builder.build_scenes(
           segments=segments,
           classifications=classifications,
           summary_mode=scene_summary_mode
       )

       statistics = builder.calculate_statistics(scenes)

       intermediate_output_manager.save_scene_bundles(
           scenes=scenes,
           statistics=statistics
       )
   ```

2. **Update Pipeline Constructor** to accept new parameters:
   ```python
   def __init__(
       self,
       ...,
       enable_audit_mode: bool = False,
       redact_prompts: bool = False,
       generate_scenes: bool = True,
       scene_summary_mode: str = "template",
   ):
   ```

3. **Pass Parameters from UI to Pipeline**:
   - Update `app.py` or `app_manager.py` to extract new inputs
   - Pass to `DDSessionProcessor` constructor

### 3.3 Downstream Consumer Updates (Gemini)

**What Needs to Be Done**:

1. **Update Knowledge Base** (`src/knowledge_base.py`):
   - Load scene bundles if available
   - Extract knowledge from scenes instead of individual segments
   - Use `dominant_type` to filter for IC-relevant scenes

2. **Update Character Profile Extractor** (`src/character_profile_extractor.py`):
   - Use `classification_type` field to distinguish CHARACTER vs. DM_NARRATION
   - Filter for CHARACTER-specific segments
   - Use speaker_name from classification results

3. **Update Story Notebook** (`src/story_notebook.py`):
   - Load scene bundles for narrative structure
   - Use scene summaries as story section headers
   - Group segments by scene for coherent story flow

**Example Integration** (pseudo-code):
```python
# In src/knowledge_base.py
from src.intermediate_output import IntermediateOutputManager

intermediate_mgr = IntermediateOutputManager(session_output_dir)

# Try to load scene bundles
try:
    scenes, metadata = intermediate_mgr.load_scene_bundles()
    ic_scenes = [s for s in scenes if s["dominant_type"] in ["CHARACTER", "DM_NARRATION", "NPC_DIALOGUE"]]

    # Extract knowledge from IC scenes
    for scene in ic_scenes:
        # Process scene...
except FileNotFoundError:
    # Fall back to per-segment processing
    segments, classifications = intermediate_mgr.load_classification()
    # Process segments...
```

---

## 4. Testing Recommendations

### 4.1 UI Testing

**Speaker Manager Tab**:
1. Load speakers for a processed session
2. Verify speaker IDs match diarization output
3. Load party mappings and verify auto-fill
4. Save mappings and verify persistence
5. Test DM NPC mode tracking

**Process Session Tab**:
1. Process a session with audit mode enabled
2. Verify `stage_6_prompts.ndjson` is created
3. Process with redact mode and verify no dialogue text in audit log
4. Verify scene bundles are generated by default
5. Test scene summary mode options

### 4.2 Integration Testing

**After Classifier Integration**:
1. Process a test session with speaker mappings
2. Verify character attribution improves from ~10% to 80%+
3. Check classification results for `classification_type` field
4. Verify audit log contains correct prompt hashes
5. Verify scene bundles have correct boundaries

**After Downstream Integration**:
1. Run knowledge extraction on scene-bundled session
2. Verify NPC extraction improves (should find NPCs from DM_NARRATION/NPC_DIALOGUE)
3. Verify character profiles use CHARACTER-specific segments
4. Verify story notebook uses scene structure

### 4.3 Regression Testing

**Backward Compatibility**:
1. Process a session without advanced options (verify old behavior works)
2. Load classification results without `classification_type` (verify graceful fallback)
3. Process without scene bundles (verify downstream still works)

---

## 5. Known Limitations

### 5.1 DM NPC Mode Not Fully Integrated

**Status**: UI and speaker profiles support DM NPC mode tracking, but classifier integration is pending.

**Current Behavior**: NPC mode metadata is saved to speaker profiles but not yet used by the classifier.

**Expected After Integration**: Classifier will receive NPC hints and attribute DM dialogue to specific NPCs during those time ranges.

### 5.2 LLM Scene Summaries Not Implemented

**Status**: Scene builder has `llm` summary mode option, but implementation is placeholder.

**Current Behavior**: Selecting `llm` mode returns `"[LLM summary not yet implemented - placeholder]"`.

**Expected After Implementation**: Will call LLM to generate rich, context-aware scene summaries.

### 5.3 No UI Controls for Scene Break Tuning

**Status**: Scene break heuristics (time gap, classification change detection) are hardcoded in `SceneBuilder` class.

**Current Workaround**: Modify `src/scene_builder.py` constructor parameters.

**Expected After UI Update**: Expose threshold controls in Process Session advanced options.

---

## 6. File Structure Summary

```
src/
+-- ui/
    +-- speaker_manager_tab.py (MODIFIED - enhanced controls)
    +-- process_session_tab.py (MODIFIED - advanced options)
+-- intermediate_output.py (MODIFIED - audit & scene methods)
+-- scene_builder.py (NEW - scene bundling logic)
+-- pipeline.py (PENDING - needs Codex/Gemini wiring)
+-- classifier.py (PENDING - needs Codex updates)
+-- prompts/
    +-- classifier_prompt_nl.txt (PENDING - needs Codex updates)
+-- knowledge_base.py (PENDING - needs Gemini scene integration)
+-- character_profile_extractor.py (PENDING - needs Gemini updates)
+-- story_notebook.py (PENDING - needs Gemini updates)

docs/
+-- UI_ENHANCEMENTS_GUIDE.md (NEW - user documentation)
+-- IMPLEMENTATION_HANDOFF_UI_PIPELINE.md (NEW - this file)
+-- IC_OOC_CLASSIFICATION_ANALYSIS.md (REFERENCE - multi-agent consensus)

output/<session>/intermediates/
+-- stage_6_classification.json (EXISTING - will be extended with metadata)
+-- stage_6_prompts.ndjson (NEW - audit log, created if enabled)
+-- stage_6_scenes.json (NEW - scene bundles, created if enabled)

models/
+-- speaker_profiles.json (EXISTING - extended with role & character_name fields)
```

---

## 7. Next Steps

### For Codex (Classifier & Pipeline)

1. **Update `src/classifier.py`**:
   - Add `speaker_map` parameter to classification methods
   - Extend `ClassificationResult` with `speaker_name`, `classification_type`, `unknown_speaker` fields
   - Implement prompt building with speaker context

2. **Update `src/prompts/classifier_prompt_nl.txt`**:
   - Add speaker context section
   - Add temporal metadata preamble
   - Update examples to show speaker labels

3. **Wire Pipeline Parameters**:
   - Extract new UI inputs in `app.py` or `app_manager.py`
   - Pass to `DDSessionProcessor` constructor
   - Call `scene_builder` after classification
   - Call `save_audit_log` if enabled

4. **Update Tests**:
   - Add test for speaker map building
   - Add test for audit log creation
   - Add test for scene bundle generation

### For Gemini (Downstream Consumers)

1. **Update `src/knowledge_base.py`**:
   - Load scene bundles if available
   - Use `classification_type` to filter segments
   - Extract NPC information from DM_NARRATION/NPC_DIALOGUE

2. **Update `src/character_profile_extractor.py`**:
   - Filter for CHARACTER-specific segments
   - Use speaker_name from classification results

3. **Update `src/story_notebook.py`**:
   - Use scene bundles for narrative structure
   - Include scene summaries as section headers

4. **Update Tests**:
   - Add test for scene-based knowledge extraction
   - Add test for CHARACTER-filtered profile extraction

---

## 8. Success Metrics

**After Full Integration**:

- ✅ Character attribution accuracy: ~10% → 80%+ (measured by % of IC segments with concrete character names)
- ✅ Audit log creation: 100% of segments logged when enabled
- ✅ Scene bundle generation: 100% of sessions produce scene files when enabled
- ✅ NPC extraction: >5 NPCs extracted per 3-hour session (vs. 0 currently)
- ✅ Story quality: Coherent narrative structure with proper character attributions

---

## 9. Contact & Questions

**Completed Work (UI/Pipeline Infrastructure)**: Claude (Sonnet 4.5)
- Speaker manager enhancements
- Process session advanced options
- Intermediate output persistence
- Scene builder module
- Documentation

**Pending Work (Classifier/Downstream)**:
- Codex: Classifier prompts, result structures, pipeline wiring
- Gemini: Downstream consumer updates (knowledge base, profiles, notebooks)

**Questions/Issues**: Report in implementation planning documents or direct discussion

---

**Implementation Status**: ✅ UI & Pipeline Infrastructure Complete (2025-11-17 16:00 UTC)
**Next Phase**: Classifier & Downstream Integration
**Estimated Effort**: 4-6 hours for Codex, 2-3 hours for Gemini
**Priority**: P0/P1 (Critical for character attribution and story quality)

---

## 7. Pipeline Wiring Completion Update (2025-11-17 16:00 UTC)

### What Was Completed

✅ **app.py Updates**:
- Added 4 new parameters to `process_session()`: `enable_audit_mode`, `redact_prompts`, `generate_scenes`, `scene_summary_mode`
- Updated `_create_processor_for_context()` to pass new parameters to pipeline
- Updated audit event logging to include new parameters

✅ **UI Event Handler Updates** ([src/ui/process_session_events.py](src/ui/process_session_events.py)):
- Updated `process_session_handler()` to accept 4 new parameters
- Wired new inputs from UI components to processing function
- Parameters are now passed through the complete chain: UI -> Event Handler -> app.py -> Pipeline

✅ **Pipeline Constructor Updates** ([src/pipeline.py](src/pipeline.py)):
- Added 4 new parameters to `DDSessionProcessor.__init__()`
- Stored as instance variables: `self.enable_audit_mode`, `self.redact_prompts`, `self.generate_scenes`, `self.scene_summary_mode`
- Updated docstring with parameter descriptions

✅ **Scene Builder Integration** ([src/pipeline.py:1986-2003](src/pipeline.py#L1986-L2003)):
- Added scene builder call after classification stage
- Respects `self.generate_scenes` flag
- Builds scenes using `SceneBuilder` class with configurable heuristics
- Saves scene bundles to `stage_6_scenes.json` via `intermediate_output_manager.save_scene_bundles()`
- Generates statistics for scene metadata

### What Remains for Codex

⚠️ **Audit Logging Integration** (Estimated: 1-2 hours):

The audit logging infrastructure is complete, but the classifier needs to call it. Here's what Codex needs to do:

**Location**: [src/classifier.py](src/classifier.py) - Inside the `classify_segments()` method

**Required Changes**:
1. Accept `intermediate_output_manager` and `enable_audit_mode`, `redact_prompts` as parameters
2. After processing each segment, if `enable_audit_mode` is True, call:

```python
if enable_audit_mode:
    intermediate_output_manager.save_audit_log(
        segment_index=i,
        prompt_data={
            "prev_text": prev_text,
            "current_text": current_text,
            "next_text": next_text,
            "char_list": character_names,
            "player_list": player_names,
            "speakers": speaker_context,  # Speaker map info
        },
        response_data={
            "raw_response": raw_llm_response,
            "parsed_classification": result.classification.value,
            "parsed_type": result.classification_type.value,
            "parsed_confidence": result.confidence,
            "parsed_reasoning": result.reasoning,
        },
        model_info={
            "model": self.model_name,
            "options": generation_options,
            "retry_strategy": retry_count if retried else None,
        },
        redact=redact_prompts,
    )
```

**Where to Get These Values**:
- `prev_text`, `current_text`, `next_text` - Already being constructed for the prompt
- `raw_llm_response` - The raw text response from Ollama before parsing
- `generation_options` - The options dict passed to Ollama (temperature, etc.)
- `retry_count` - If retries were used, the retry number

**Integration Points**:
1. Update `ClassifierBase.classify_segments()` signature to accept `intermediate_output_manager`, `enable_audit_mode`, `redact_prompts`
2. Update `OllamaClassifier.classify_segments()` implementation to call `save_audit_log()` for each segment
3. Update pipeline's call to `self.classifier.classify_segments()` to pass these parameters (already passed via constructor, but may need to be exposed)

**Testing**:
- Enable audit mode in UI
- Process a short session
- Verify `output/<session>/intermediates/stage_6_prompts.ndjson` is created
- Verify each line is valid JSON with required fields
- Test with redact mode enabled - verify prompt/response text is excluded

---

**Last Updated**: 2025-11-17 16:00 UTC
**Document Version**: 1.1
**Pipeline Wiring**: ✅ Complete
**Audit Logging Integration**: ⚠️ Pending (Codex)
**Ready for Handoff**: Yes ✅
