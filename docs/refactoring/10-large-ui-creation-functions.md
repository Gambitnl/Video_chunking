# Refactor Candidate #10: Refactor Large UI Creation Functions

## Problem Statement

The UI creation functions in `src/ui/` are extremely large, with `create_process_session_tab_modern()` at 808 lines being a prime example. These monolithic functions make the UI code difficult to maintain, test, and modify. Adding or changing UI elements requires navigating through hundreds of lines of code.

## Current State Analysis

### Locations

Multiple UI creation functions are excessively large:

1. **`create_process_session_tab_modern()`** - `src/ui/process_session_tab_modern.py`
   - **Lines**: 808 (entire file)
   - Creates complete Process Session tab

2. **`create_campaign_tab_modern()`** - `src/ui/campaign_tab_modern.py`
   - Large UI creation function

3. **`create_characters_tab_modern()`** - `src/ui/characters_tab_modern.py`
   - Complex character management UI

4. **`create_settings_tools_tab_modern()`** - `src/ui/settings_tools_tab_modern.py`
   - Settings and tools UI

### Current Code Structure

```python
def create_process_session_tab_modern(
    demo,
    refresh_campaign_names,
    process_session_fn,
    preflight_fn,
    campaign_manager,
    active_campaign_state,
    campaign_badge_text,
    initial_campaign_name
):
    """
    Create the Process Session tab UI.

    This function is 808 lines long and creates:
    - Campaign badge
    - Audio upload
    - Session configuration
    - Party selection
    - Processing options (checkboxes)
    - Backend selection dropdowns
    - Action buttons
    - Status display
    - Results display (full, IC, OOC)
    - Statistics display
    - Snippet export display
    - Event handlers for all components

    All event handlers are defined inline, making the function extremely long.
    """
    # Lines 1-100: Component creation
    with gr.Tab("📝 Process Session"):
        campaign_badge = gr.Markdown(campaign_badge_text)
        audio_input = gr.Audio(...)
        session_id_input = gr.Textbox(...)
        # ... many more components

    # Lines 101-300: More components
    with gr.Accordion("Advanced Options"):
        # ... many advanced options

    # Lines 301-500: Event handler definitions
    def _on_process_click(...):
        # 50+ line handler

    def _on_preflight_click(...):
        # 30+ line handler

    # Lines 501-808: More handlers and wiring
    process_btn.click(fn=_on_process_click, inputs=[...], outputs=[...])
    # ... many more click handlers

    return available_parties, process_tab_refs
```

### Issues

1. **Monolithic Design**: Single function does everything
2. **Poor Testability**: Cannot test individual components
3. **Hard to Modify**: Changes require navigating 800+ lines
4. **Event Handler Clutter**: Inline handlers make code hard to read
5. **Component Discovery**: Hard to find specific UI elements
6. **Reusability**: Cannot reuse individual components
7. **Code Organization**: No clear structure
8. **Documentation**: Hard to document such a large function

## Proposed Solution

### Design Overview

Break down large UI functions into:
1. **Component Factory Classes**: Create individual UI components
2. **Event Handler Classes**: Separate event handling logic
3. **Builder Pattern**: Build complex UIs step-by-step
4. **Composition**: Compose larger UIs from smaller components

### New Architecture

```python
# src/ui/components/audio_upload.py
from dataclasses import dataclass
from typing import Any
import gradio as gr


@dataclass
class AudioUploadComponent:
    """Audio upload component with validation"""
    audio_input: Any
    file_info: Any

    @classmethod
    def create(cls, label: str = "Upload Audio File") -> 'AudioUploadComponent':
        """
        Create audio upload component.

        Returns:
            AudioUploadComponent with Gradio elements
        """
        with gr.Group():
            audio_input = gr.Audio(
                label=label,
                type="filepath",
                elem_classes=["audio-upload"]
            )
            file_info = gr.Markdown(
                value="No file uploaded",
                elem_classes=["file-info"]
            )

        return cls(audio_input=audio_input, file_info=file_info)

    def on_upload(self, audio_file) -> str:
        """Handle audio file upload"""
        if audio_file is None:
            return "No file uploaded"

        from pathlib import Path
        file_path = Path(audio_file) if isinstance(audio_file, str) else Path(audio_file.name)

        file_size = file_path.stat().st_size / (1024 * 1024)  # MB
        return f"📁 **{file_path.name}** ({file_size:.1f} MB)"

    def wire_events(self):
        """Wire up event handlers"""
        self.audio_input.change(
            fn=self.on_upload,
            inputs=[self.audio_input],
            outputs=[self.file_info]
        )


# src/ui/components/session_config.py
@dataclass
class SessionConfigComponent:
    """Session configuration inputs"""
    session_id: Any
    party_selection: Any
    character_names: Any
    player_names: Any
    num_speakers: Any

    @classmethod
    def create(
        cls,
        available_parties: list,
        default_party: str = "Manual Entry"
    ) -> 'SessionConfigComponent':
        """Create session configuration component"""
        with gr.Group():
            gr.Markdown("### Session Configuration")

            session_id = gr.Textbox(
                label="Session ID",
                placeholder="e.g., session_01",
                info="Unique identifier for this session"
            )

            party_selection = gr.Dropdown(
                label="Party Configuration",
                choices=available_parties,
                value=default_party,
                info="Select a party profile or use manual entry"
            )

            with gr.Row():
                character_names = gr.Textbox(
                    label="Character Names",
                    placeholder="e.g., Gandalf, Frodo, Aragorn",
                    info="Comma-separated list"
                )
                player_names = gr.Textbox(
                    label="Player Names",
                    placeholder="e.g., Alice, Bob, Charlie",
                    info="Comma-separated list"
                )

            num_speakers = gr.Number(
                label="Number of Speakers",
                value=4,
                minimum=1,
                maximum=10,
                precision=0
            )

        return cls(
            session_id=session_id,
            party_selection=party_selection,
            character_names=character_names,
            player_names=player_names,
            num_speakers=num_speakers
        )


# src/ui/components/processing_options.py
@dataclass
class ProcessingOptionsComponent:
    """Processing option checkboxes"""
    skip_diarization: Any
    skip_classification: Any
    skip_snippets: Any
    skip_knowledge: Any

    @classmethod
    def create(cls, defaults: dict = None) -> 'ProcessingOptionsComponent':
        """Create processing options component"""
        defaults = defaults or {}

        with gr.Group():
            gr.Markdown("### Processing Options")

            skip_diarization = gr.Checkbox(
                label="Skip Diarization",
                value=defaults.get("skip_diarization", False),
                info="Skip speaker identification"
            )

            skip_classification = gr.Checkbox(
                label="Skip IC/OOC Classification",
                value=defaults.get("skip_classification", False),
                info="Skip in-character/out-of-character detection"
            )

            skip_snippets = gr.Checkbox(
                label="Skip Audio Snippets",
                value=defaults.get("skip_snippets", True),
                info="Skip exporting individual audio segments"
            )

            skip_knowledge = gr.Checkbox(
                label="Skip Knowledge Extraction",
                value=defaults.get("skip_knowledge", False),
                info="Skip extracting campaign knowledge"
            )

        return cls(
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
            skip_snippets=skip_snippets,
            skip_knowledge=skip_knowledge
        )


# src/ui/handlers/process_session_handler.py
class ProcessSessionHandler:
    """Event handlers for process session tab"""

    def __init__(
        self,
        process_session_fn,
        preflight_fn,
        campaign_manager,
    ):
        self.process_session_fn = process_session_fn
        self.preflight_fn = preflight_fn
        self.campaign_manager = campaign_manager
        self.logger = get_logger("ui.process_handler")

    def handle_process_click(
        self,
        audio_file,
        session_id,
        party_selection,
        character_names,
        player_names,
        num_speakers,
        language,
        skip_diarization,
        skip_classification,
        skip_snippets,
        skip_knowledge,
        transcription_backend,
        diarization_backend,
        classification_backend,
        campaign_id,
    ):
        """
        Handle process button click.

        Returns:
            Tuple of UI updates
        """
        try:
            # Validate inputs
            if not audio_file:
                return self._error_response("Please upload an audio file")

            if not session_id:
                return self._error_response("Please provide a session ID")

            # Call process function
            self.logger.info("Starting session processing for %s", session_id)

            result = self.process_session_fn(
                audio_file=audio_file,
                session_id=session_id,
                party_selection=party_selection,
                character_names=character_names,
                player_names=player_names,
                num_speakers=num_speakers,
                language=language,
                skip_diarization=skip_diarization,
                skip_classification=skip_classification,
                skip_snippets=skip_snippets,
                skip_knowledge=skip_knowledge,
                transcription_backend=transcription_backend,
                diarization_backend=diarization_backend,
                classification_backend=classification_backend,
                campaign_id=campaign_id,
            )

            return self._success_response(result)

        except Exception as exc:
            self.logger.exception("Error processing session")
            return self._error_response(str(exc))

    def handle_preflight_click(
        self,
        party_selection,
        character_names,
        player_names,
        num_speakers,
        language,
        skip_diarization,
        skip_classification,
        transcription_backend,
        diarization_backend,
        classification_backend,
        campaign_id,
    ):
        """Handle preflight check button click"""
        try:
            result = self.preflight_fn(
                party_selection=party_selection,
                character_names=character_names,
                player_names=player_names,
                num_speakers=num_speakers,
                language=language,
                skip_diarization=skip_diarization,
                skip_classification=skip_classification,
                transcription_backend=transcription_backend,
                diarization_backend=diarization_backend,
                classification_backend=classification_backend,
                campaign_id=campaign_id,
            )

            return result

        except Exception as exc:
            self.logger.exception("Error running preflight checks")
            return StatusMessages.error("Preflight Error", str(exc))

    def _error_response(self, message: str):
        """Build error response tuple"""
        return (
            gr.update(visible=True),  # Show error
            StatusMessages.error("Processing Error", message),
            "",  # Clear outputs
            "",
            "",
            StatusMessages.info("Statistics", "No statistics"),
            StatusMessages.info("Snippets", "No snippets"),
        )

    def _success_response(self, result: dict):
        """Build success response tuple"""
        return (
            gr.update(visible=True),  # Show results
            StatusMessages.success("Processing Complete", result.get("message", "")),
            result.get("full", ""),
            result.get("ic", ""),
            result.get("ooc", ""),
            self._format_statistics(result.get("stats", {})),
            self._format_snippets(result.get("snippet", {})),
        )

    def _format_statistics(self, stats: dict) -> str:
        """Format statistics for display"""
        if not stats:
            return StatusMessages.info("Statistics", "No statistics available")

        lines = [
            "### Statistics",
            f"- Duration: {stats.get('total_duration_formatted', 'N/A')}",
            f"- Segments: {stats.get('total_segments', 0)}",
            f"- IC Segments: {stats.get('ic_segments', 0)}",
            f"- OOC Segments: {stats.get('ooc_segments', 0)}",
        ]
        return "\n".join(lines)

    def _format_snippets(self, snippet: dict) -> str:
        """Format snippet info for display"""
        if not snippet.get("segments_dir"):
            return StatusMessages.info("Snippets", "No snippets exported")

        return StatusMessages.success(
            "Snippet Export",
            f"Exported to: {snippet['segments_dir']}"
        )


# src/ui/builders/process_session_tab_builder.py
class ProcessSessionTabBuilder:
    """Builder for Process Session tab"""

    def __init__(
        self,
        demo,
        refresh_campaign_names,
        process_session_fn,
        preflight_fn,
        campaign_manager,
        active_campaign_state,
        campaign_badge_text,
        initial_campaign_name
    ):
        self.demo = demo
        self.refresh_campaign_names = refresh_campaign_names
        self.process_session_fn = process_session_fn
        self.preflight_fn = preflight_fn
        self.campaign_manager = campaign_manager
        self.active_campaign_state = active_campaign_state
        self.campaign_badge_text = campaign_badge_text
        self.initial_campaign_name = initial_campaign_name

        # Component references
        self.components = {}
        self.handler = None

    def build(self) -> tuple:
        """Build the complete Process Session tab"""
        with gr.Tab("📝 Process Session"):
            # Campaign badge
            self.components['campaign_badge'] = gr.Markdown(
                self.campaign_badge_text
            )

            # Audio upload
            self.components['audio'] = AudioUploadComponent.create()
            self.components['audio'].wire_events()

            # Session configuration
            available_parties = self.campaign_manager.get_available_parties()
            self.components['session_config'] = SessionConfigComponent.create(
                available_parties=available_parties
            )

            # Processing options
            self.components['options'] = ProcessingOptionsComponent.create()

            # Backend selection
            self.components['backends'] = BackendSelectionComponent.create()

            # Action buttons
            self.components['actions'] = ActionButtonsComponent.create()

            # Results display
            self.components['results'] = ResultsDisplayComponent.create()

        # Create handler
        self.handler = ProcessSessionHandler(
            self.process_session_fn,
            self.preflight_fn,
            self.campaign_manager,
        )

        # Wire up events
        self._wire_events()

        # Build reference dict
        refs = self._build_references()

        return available_parties, refs

    def _wire_events(self):
        """Wire up all event handlers"""
        # Process button
        self.components['actions'].process_btn.click(
            fn=self.handler.handle_process_click,
            inputs=self._get_process_inputs(),
            outputs=self._get_process_outputs(),
        )

        # Preflight button
        self.components['actions'].preflight_btn.click(
            fn=self.handler.handle_preflight_click,
            inputs=self._get_preflight_inputs(),
            outputs=[self.components['results'].status_output],
        )

    def _get_process_inputs(self) -> list:
        """Get list of inputs for process handler"""
        return [
            self.components['audio'].audio_input,
            self.components['session_config'].session_id,
            self.components['session_config'].party_selection,
            # ... all other inputs
        ]

    def _get_process_outputs(self) -> list:
        """Get list of outputs for process handler"""
        return [
            self.components['results'].results_section,
            self.components['results'].status_output,
            # ... all other outputs
        ]

    def _build_references(self) -> dict:
        """Build reference dict for external access"""
        return {
            'campaign_badge': self.components['campaign_badge'],
            'session_id_input': self.components['session_config'].session_id,
            # ... all other references
        }


# Simplified main function
def create_process_session_tab_modern(
    demo,
    refresh_campaign_names,
    process_session_fn,
    preflight_fn,
    campaign_manager,
    active_campaign_state,
    campaign_badge_text,
    initial_campaign_name
):
    """
    Create the Process Session tab UI.

    Now much shorter - delegates to builder.
    """
    builder = ProcessSessionTabBuilder(
        demo=demo,
        refresh_campaign_names=refresh_campaign_names,
        process_session_fn=process_session_fn,
        preflight_fn=preflight_fn,
        campaign_manager=campaign_manager,
        active_campaign_state=active_campaign_state,
        campaign_badge_text=campaign_badge_text,
        initial_campaign_name=initial_campaign_name,
    )

    return builder.build()
```

## Implementation Plan

### Phase 1: Create Component Classes (Low Risk)
**Duration**: 6-8 hours

1. **Create base component class**
   ```python
   # src/ui/components/base.py
   class BaseUIComponent:
       """Base class for UI components"""
       def create(cls) -> 'BaseUIComponent':
           raise NotImplementedError

       def wire_events(self):
           """Wire up event handlers (optional)"""
           pass
   ```

2. **Create individual component classes**
   - `AudioUploadComponent`
   - `SessionConfigComponent`
   - `ProcessingOptionsComponent`
   - `BackendSelectionComponent`
   - `ActionButtonsComponent`
   - `ResultsDisplayComponent`

3. **Add unit tests for each component**

### Phase 2: Create Handler Classes (Medium Risk)
**Duration**: 4-5 hours

1. **Create handler classes**
   - `ProcessSessionHandler`
   - `PreflightCheckHandler`
   - `ResultsDisplayHandler`

2. **Extract event handling logic**
   - Move from inline functions
   - Add error handling
   - Add logging

3. **Add tests for handlers**

### Phase 3: Create Builder Class (Medium Risk)
**Duration**: 4-5 hours

1. **Create `ProcessSessionTabBuilder`**
   - Implement `build()` method
   - Implement `_wire_events()`
   - Implement `_build_references()`

2. **Add tests**

### Phase 4: Refactor Main Function (Low Risk)
**Duration**: 2-3 hours

1. **Simplify `create_process_session_tab_modern()`**
   - Use builder
   - Reduce from 808 to ~30 lines

2. **Test integration**

### Phase 5: Repeat for Other UI Files (High Effort)
**Duration**: 15-20 hours

1. **Apply same pattern to**:
   - `create_campaign_tab_modern()`
   - `create_characters_tab_modern()`
   - `create_settings_tools_tab_modern()`
   - `create_stories_output_tab_modern()`

### Phase 6: Testing (High Priority)
**Duration**: 6-8 hours

1. **Unit tests for all components**
2. **Integration tests for builders**
3. **UI tests (manual or automated)**

### Phase 7: Documentation (Low Risk)
**Duration**: 3-4 hours

1. **Document component system**
2. **Add usage examples**
3. **Create developer guide**

## Testing Strategy

### Unit Tests

```python
class TestAudioUploadComponent(unittest.TestCase):
    """Test audio upload component"""

    def test_create(self):
        """Test component creation"""
        component = AudioUploadComponent.create()
        assert component.audio_input is not None
        assert component.file_info is not None

    def test_on_upload(self):
        """Test upload handler"""
        component = AudioUploadComponent.create()
        result = component.on_upload("/path/to/file.wav")
        assert "file.wav" in result


class TestProcessSessionHandler(unittest.TestCase):
    """Test process session handler"""

    def setUp(self):
        self.handler = ProcessSessionHandler(
            mock_process_fn,
            mock_preflight_fn,
            mock_campaign_manager,
        )

    def test_handle_process_click_success(self):
        """Test successful processing"""
        result = self.handler.handle_process_click(...)
        # Verify result structure

    def test_handle_process_click_error(self):
        """Test error handling"""
        # Test with invalid inputs
        # Verify error response
```

### Integration Tests

```python
@pytest.mark.integration
class TestProcessSessionTabBuilder(unittest.TestCase):
    """Test complete tab building"""

    def test_build_tab(self):
        """Test building complete tab"""
        builder = ProcessSessionTabBuilder(...)
        parties, refs = builder.build()

        # Verify all components created
        assert 'campaign_badge' in refs
        assert 'session_id_input' in refs
        # ... etc

    def test_event_wiring(self):
        """Test that events are wired correctly"""
        # Test clicking buttons triggers handlers
```

## Risks and Mitigation

### Risk 1: Breaking Existing UI
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Maintain same public API
- Extensive testing
- Gradual migration (one tab at a time)
- Feature flag for new UI

### Risk 2: Component Coupling
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Clear component interfaces
- Minimize dependencies
- Use dependency injection
- Document component contracts

### Risk 3: Event Wiring Errors
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Test all event handlers
- Clear event documentation
- Use consistent patterns
- Automated UI testing

## Expected Benefits

### Immediate Benefits
1. **Improved Maintainability**: Easier to modify individual components
2. **Better Testing**: Test components in isolation
3. **Code Clarity**: Clear component structure
4. **Reusability**: Components can be reused
5. **Developer Experience**: Easier to understand and modify

### Long-term Benefits
1. **Extensibility**: Easy to add new UI components
2. **Consistency**: Reusable components ensure consistent UI
3. **Documentation**: Self-documenting component structure
4. **Performance**: Potential for lazy loading
5. **Refactoring**: Easier to refactor individual components

### Metrics
- **Function Size**: Reduce from 808 to ~30 lines (96% reduction)
- **Cyclomatic Complexity**: Reduce from ~50 to ~5
- **Test Coverage**: Increase from ~30% to >80%
- **Reusable Components**: Create ~20 reusable components

## Success Criteria

1. ✅ All component classes created and tested
2. ✅ All handler classes created and tested
3. ✅ Builder pattern implemented
4. ✅ Main UI function reduced to <50 lines
5. ✅ All existing UI tests pass
6. ✅ New component tests added (>80% coverage)
7. ✅ UI behavior unchanged
8. ✅ Documentation updated
9. ✅ Developer guide created

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Component Classes | 6-8 hours | None |
| Phase 2: Handler Classes | 4-5 hours | Phase 1 |
| Phase 3: Builder Class | 4-5 hours | Phases 1-2 |
| Phase 4: Refactor Main Function | 2-3 hours | Phase 3 |
| Phase 5: Other UI Files | 15-20 hours | Phase 4 |
| Phase 6: Testing | 6-8 hours | Phase 5 |
| Phase 7: Documentation | 3-4 hours | Phase 6 |
| **Total** | **40-53 hours** | |

**Note**: This is the largest refactoring effort. Consider breaking into multiple iterations:
- **Iteration 1**: Process Session tab only (20-25 hours)
- **Iteration 2**: Campaign tab (10-12 hours)
- **Iteration 3**: Remaining tabs (10-15 hours)

## References

- Current implementation: `src/ui/process_session_tab_modern.py` (808 lines)
- Related files: All files in `src/ui/` directory
- Gradio documentation: https://www.gradio.app/docs
- Design patterns: Builder Pattern, Component Pattern
- UI architecture: Component-based design
