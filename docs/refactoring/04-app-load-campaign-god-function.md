# Refactor Candidate #4: Refactor God Function `_load_campaign()` in app.py

## Problem Statement

The `_load_campaign()` function in `app.py` (lines 964-1041) returns **25 different values** in a massive tuple and is responsible for updating the entire application's UI state. This is a classic "God Function" anti-pattern that violates the Single Responsibility Principle and creates extremely high coupling.

## Current State Analysis

### Location
- **File**: `app.py`
- **Function**: `_load_campaign()`
- **Lines**: 964-1041
- **Size**: 77 lines
- **Return Values**: 25 (tuple)

### Current Code Structure

```python
def _load_campaign(display_name: Optional[str], current_campaign_id: Optional[str]):
    campaign_id = _campaign_id_from_name(display_name) or current_campaign_id or initial_campaign_id
    summary = _campaign_summary_message(campaign_id)
    manifest = _build_campaign_manifest(campaign_id)

    process_updates = _compute_process_updates(campaign_id)
    campaign_names_map = _refresh_campaign_names()
    dropdown_update = gr.update(...)

    overview_update = gr.update(value=_campaign_overview_markdown(campaign_id))
    knowledge_update = gr.update(value=_knowledge_summary_markdown(campaign_id))
    session_library_update = gr.update(value=_session_library_markdown(campaign_id))

    # ... many more update calculations ...

    return (
        campaign_id,
        summary,
        manifest,
        dropdown_update,
        *process_updates,
        overview_update,
        knowledge_update,
        session_library_update,
        character_profiles_update,
        character_table_update,
        character_select_update,
        character_export_update,
        character_overview_update,
        extract_party_update,
        story_session_update,
        narrative_hint_update,
        diagnostics_update,
        chat_update,
        social_campaign_update,
        social_session_update,
        social_keyword_update,
        social_nebula_update,
    )
```

### Issues

1. **Massive Return Value**: Returns 25 values - impossible to remember order
2. **High Coupling**: Function knows about entire UI structure
3. **Hard to Test**: Mock 25 different components for testing
4. **Hard to Maintain**: Adding new UI element requires modifying this function
5. **Poor Readability**: Unclear what each return value represents
6. **Violates SRP**: Does UI state calculation for all tabs
7. **Brittle**: Easy to get tuple positions wrong
8. **Code Duplication**: Similar function `_create_new_campaign()` has same issues

## Proposed Solution

### Design Overview

Replace the massive tuple return with:
1. **State Object Pattern**: Return a single state object
2. **Builder Pattern**: Build state incrementally
3. **Tab-Specific State Objects**: Separate concerns by UI tab
4. **State Manager Class**: Centralize state management logic

### New Architecture

```python
@dataclass
class CampaignState:
    """Complete application state for a campaign"""
    campaign_id: Optional[str]
    summary: str
    manifest: str
    dropdown_update: Any
    process_tab: 'ProcessTabState'
    campaign_tab: 'CampaignTabState'
    characters_tab: 'CharactersTabState'
    stories_tab: 'StoriesTabState'
    settings_tab: 'SettingsTabState'

    def to_gradio_outputs(self) -> tuple:
        """
        Convert state to Gradio output tuple for compatibility.
        This method makes the transition gradual.
        """
        return (
            self.campaign_id,
            self.summary,
            self.manifest,
            self.dropdown_update,
            *self.process_tab.to_tuple(),
            *self.campaign_tab.to_tuple(),
            *self.characters_tab.to_tuple(),
            *self.stories_tab.to_tuple(),
            *self.settings_tab.to_tuple(),
        )


@dataclass
class ProcessTabState:
    """State for the Process Session tab"""
    campaign_badge: Any
    session_id_input: Any
    character_names_input: Any
    player_names_input: Any
    party_selection_input: Any
    num_speakers_input: Any
    skip_diarization_input: Any
    skip_classification_input: Any
    skip_snippets_input: Any
    skip_knowledge_input: Any
    status_output: Any
    results_section: Any
    full_output: str
    ic_output: str
    ooc_output: str
    stats_output: Any
    snippet_output: Any

    def to_tuple(self) -> tuple:
        """Convert to tuple for Gradio compatibility"""
        return (
            self.campaign_badge,
            self.session_id_input,
            # ... all fields in order
        )


@dataclass
class CampaignTabState:
    """State for the Campaign tab"""
    overview: Any
    knowledge: Any
    session_library: Any

    def to_tuple(self) -> tuple:
        return (self.overview, self.knowledge, self.session_library)


@dataclass
class CharactersTabState:
    """State for the Characters tab"""
    profiles: Any
    table: Any
    character_dropdown: Any
    export_dropdown: Any
    overview: Any
    extract_party_dropdown: Any

    def to_tuple(self) -> tuple:
        return (
            self.profiles,
            self.table,
            self.character_dropdown,
            self.export_dropdown,
            self.overview,
            self.extract_party_dropdown,
        )


@dataclass
class StoriesTabState:
    """State for the Stories tab"""
    session_list: Any
    narrative_hint: Any

    def to_tuple(self) -> tuple:
        return (self.session_list, self.narrative_hint)


@dataclass
class SettingsTabState:
    """State for the Settings tab"""
    diagnostics: Any
    chat: Any
    social_campaign_selector: Any
    social_session_dropdown: Any
    social_keyword_output: Any
    social_nebula_output: Any

    def to_tuple(self) -> tuple:
        return (
            self.diagnostics,
            self.chat,
            self.social_campaign_selector,
            self.social_session_dropdown,
            self.social_keyword_output,
            self.social_nebula_output,
        )


class CampaignStateBuilder:
    """
    Builder for constructing CampaignState incrementally.

    This separates the complex state construction logic
    and makes it easier to test and maintain.
    """

    def __init__(
        self,
        campaign_manager: CampaignManager,
        party_manager: PartyConfigManager,
        story_manager: StoryNotebookManager,
    ):
        self.campaign_manager = campaign_manager
        self.party_manager = party_manager
        self.story_manager = story_manager
        self._campaign_id: Optional[str] = None

    def with_campaign_id(self, campaign_id: Optional[str]) -> 'CampaignStateBuilder':
        """Set the campaign ID for this state"""
        self._campaign_id = campaign_id
        return self

    def build_core_state(self) -> Tuple[Optional[str], str, str, Any]:
        """Build core campaign state (ID, summary, manifest, dropdown)"""
        summary = _campaign_summary_message(self._campaign_id)
        manifest = _build_campaign_manifest(self._campaign_id)

        campaign_names_map = _refresh_campaign_names()
        dropdown_update = gr.update(
            choices=list(campaign_names_map.values()),
            value=campaign_names_map.get(self._campaign_id) if self._campaign_id else None,
        )

        return self._campaign_id, summary, manifest, dropdown_update

    def build_process_tab_state(self) -> ProcessTabState:
        """Build state for the Process Session tab"""
        settings = _process_defaults_for_campaign(self._campaign_id)

        return ProcessTabState(
            campaign_badge=_format_campaign_badge(self._campaign_id),
            session_id_input=gr.update(value=""),
            character_names_input=gr.update(value=""),
            player_names_input=gr.update(value=""),
            party_selection_input=gr.update(value=settings["party_selection"]),
            num_speakers_input=gr.update(value=settings["num_speakers"]),
            skip_diarization_input=gr.update(value=settings["skip_diarization"]),
            skip_classification_input=gr.update(value=settings["skip_classification"]),
            skip_snippets_input=gr.update(value=settings["skip_snippets"]),
            skip_knowledge_input=gr.update(value=settings["skip_knowledge"]),
            status_output=StatusMessages.info("Ready", "Campaign loaded. Configure session options and click Start Processing."),
            results_section=gr.update(visible=False),
            full_output="",
            ic_output="",
            ooc_output="",
            stats_output=StatusMessages.info("Statistics", "No statistics available."),
            snippet_output=StatusMessages.info("Snippet Export", "No snippet information available."),
        )

    def build_campaign_tab_state(self) -> CampaignTabState:
        """Build state for the Campaign tab"""
        return CampaignTabState(
            overview=gr.update(value=_campaign_overview_markdown(self._campaign_id)),
            knowledge=gr.update(value=_knowledge_summary_markdown(self._campaign_id)),
            session_library=gr.update(value=_session_library_markdown(self._campaign_id)),
        )

    def build_characters_tab_state(self) -> CharactersTabState:
        """Build state for the Characters tab"""
        (
            character_profiles_update,
            character_table_update,
            character_select_update,
            character_export_update,
            character_overview_update,
        ) = _character_tab_updates(self._campaign_id)

        extract_party_update = _extract_party_dropdown_update(self._campaign_id)

        return CharactersTabState(
            profiles=character_profiles_update,
            table=character_table_update,
            character_dropdown=character_select_update,
            export_dropdown=character_export_update,
            overview=character_overview_update,
            extract_party_dropdown=extract_party_update,
        )

    def build_stories_tab_state(self) -> StoriesTabState:
        """Build state for the Stories tab"""
        return StoriesTabState(
            session_list=gr.update(value=_session_library_markdown(self._campaign_id)),
            narrative_hint=gr.update(value=_narrative_hint_markdown(self._campaign_id)),
        )

    def build_settings_tab_state(self) -> SettingsTabState:
        """Build state for the Settings tab"""
        campaign_names_map = _refresh_campaign_names()

        social_campaign_choices = ["All Campaigns"] + list(campaign_names_map.values())
        social_campaign_value = campaign_names_map.get(self._campaign_id) if self._campaign_id else "All Campaigns"
        if not social_campaign_value:
            social_campaign_value = "All Campaigns"

        social_sessions = (
            self.story_manager.list_sessions(campaign_id=self._campaign_id)
            if self._campaign_id
            else self.story_manager.list_sessions()
        )

        return SettingsTabState(
            diagnostics=gr.update(value=_diagnostics_markdown(self._campaign_id)),
            chat=gr.update(value=_chat_status_markdown(self._campaign_id)),
            social_campaign_selector=gr.update(
                choices=social_campaign_choices,
                value=social_campaign_value,
            ),
            social_session_dropdown=gr.update(
                choices=social_sessions,
                value=social_sessions[0] if social_sessions else None,
            ),
            social_keyword_output=gr.update(
                value=StatusMessages.info(
                    "Social Insights",
                    "Select a session and run Analyze Banter for the current campaign.",
                )
            ),
            social_nebula_output=gr.update(value=None),
        )

    def build(self) -> CampaignState:
        """Build the complete CampaignState object"""
        campaign_id, summary, manifest, dropdown_update = self.build_core_state()

        return CampaignState(
            campaign_id=campaign_id,
            summary=summary,
            manifest=manifest,
            dropdown_update=dropdown_update,
            process_tab=self.build_process_tab_state(),
            campaign_tab=self.build_campaign_tab_state(),
            characters_tab=self.build_characters_tab_state(),
            stories_tab=self.build_stories_tab_state(),
            settings_tab=self.build_settings_tab_state(),
        )


# Refactored function
def _load_campaign(display_name: Optional[str], current_campaign_id: Optional[str]):
    """
    Load a campaign and compute the full application state.

    Args:
        display_name: Display name of campaign to load
        current_campaign_id: Current campaign ID (fallback)

    Returns:
        Tuple compatible with Gradio outputs (for backward compatibility)
    """
    campaign_id = _campaign_id_from_name(display_name) or current_campaign_id or initial_campaign_id

    # Build state using builder pattern
    builder = CampaignStateBuilder(
        campaign_manager=campaign_manager,
        party_manager=party_manager,
        story_manager=story_manager,
    )

    state = builder.with_campaign_id(campaign_id).build()

    # Convert to Gradio tuple for compatibility
    return state.to_gradio_outputs()
```

## Implementation Plan

### Phase 1: Create State Objects (Low Risk)
**Duration**: 3-4 hours

1. **Create state dataclasses**
   - `CampaignState`
   - `ProcessTabState`
   - `CampaignTabState`
   - `CharactersTabState`
   - `StoriesTabState`
   - `SettingsTabState`

2. **Add `to_tuple()` methods**
   - Implement for each state class
   - Ensure tuple order matches current implementation
   - Add tests to verify order

3. **Create unit tests**
   ```python
   def test_process_tab_state_to_tuple():
       state = ProcessTabState(...)
       result = state.to_tuple()
       assert len(result) == 17  # Expected number of fields
       assert isinstance(result, tuple)
   ```

### Phase 2: Create Builder Class (Medium Risk)
**Duration**: 4-5 hours

1. **Implement `CampaignStateBuilder`**
   - Extract logic from `_load_campaign()`
   - Create method for each tab's state
   - Add logging for debugging

2. **Add builder tests**
   ```python
   def test_campaign_state_builder_process_tab():
       builder = CampaignStateBuilder(
           campaign_manager=mock_manager,
           party_manager=mock_party,
           story_manager=mock_story,
       )

       state = builder.with_campaign_id("test_campaign").build_process_tab_state()

       assert state.campaign_badge is not None
       assert isinstance(state, ProcessTabState)
   ```

3. **Test full build process**
   ```python
   def test_campaign_state_builder_full():
       builder = CampaignStateBuilder(...)
       state = builder.with_campaign_id("test").build()

       assert isinstance(state, CampaignState)
       assert state.campaign_id == "test"
       assert isinstance(state.process_tab, ProcessTabState)
   ```

### Phase 3: Refactor `_load_campaign()` (Medium Risk)
**Duration**: 2 hours

1. **Replace implementation**
   - Use `CampaignStateBuilder`
   - Keep same return signature (tuple)
   - Add comments explaining structure

2. **Verify behavior**
   - Run application manually
   - Test loading different campaigns
   - Verify UI updates correctly

### Phase 4: Refactor `_create_new_campaign()` (Low Risk)
**Duration**: 2 hours

1. **Apply same pattern**
   - Use `CampaignStateBuilder`
   - Remove duplication

2. **Add specific logic for new campaigns**
   ```python
   def _create_new_campaign(name: str):
       proposed_name = name.strip() if name else ""
       new_campaign_id, _ = campaign_manager.create_blank_campaign(name=proposed_name or None)

       # Initialize knowledge base
       knowledge = CampaignKnowledgeBase(campaign_id=new_campaign_id)
       if not knowledge.knowledge_file.exists():
           knowledge._save_knowledge()

       _set_notebook_context("")

       # Build state
       builder = CampaignStateBuilder(...)
       state = builder.with_campaign_id(new_campaign_id).build()

       # Return with new campaign name cleared
       return (
           state.to_gradio_outputs()[0:4]  # Core fields
           + (gr.update(value=""),)  # Clear new campaign name input
           + state.to_gradio_outputs()[4:]  # Rest of fields
       )
   ```

### Phase 5: Testing (High Priority)
**Duration**: 3-4 hours

1. **Unit tests for all state classes**
2. **Integration tests for builder**
3. **UI tests for campaign loading**
4. **Regression tests**

### Phase 6: Documentation (Low Risk)
**Duration**: 1-2 hours

1. **Document state structure**
2. **Update architecture diagrams**
3. **Add developer guide for adding new UI elements**

## Testing Strategy

### Unit Tests

```python
class TestCampaignState(unittest.TestCase):
    def test_campaign_state_creation(self):
        """Test creating a CampaignState object"""
        state = CampaignState(
            campaign_id="test",
            summary="Test summary",
            manifest="Test manifest",
            dropdown_update=None,
            process_tab=ProcessTabState(...),
            # ... other tabs
        )
        assert state.campaign_id == "test"

    def test_campaign_state_to_gradio_outputs(self):
        """Test converting state to Gradio tuple"""
        state = CampaignState(...)
        outputs = state.to_gradio_outputs()
        assert isinstance(outputs, tuple)
        assert len(outputs) == 38  # Total expected outputs

    def test_process_tab_state_defaults(self):
        """Test ProcessTabState with default values"""
        pass


class TestCampaignStateBuilder(unittest.TestCase):
    def setUp(self):
        self.mock_campaign_manager = Mock()
        self.mock_party_manager = Mock()
        self.mock_story_manager = Mock()

        self.builder = CampaignStateBuilder(
            self.mock_campaign_manager,
            self.mock_party_manager,
            self.mock_story_manager,
        )

    def test_builder_with_campaign_id(self):
        """Test setting campaign ID"""
        builder = self.builder.with_campaign_id("test_id")
        assert builder._campaign_id == "test_id"

    def test_build_process_tab_state(self):
        """Test building process tab state"""
        state = self.builder.with_campaign_id("test").build_process_tab_state()
        assert isinstance(state, ProcessTabState)

    def test_build_full_state(self):
        """Test building complete state"""
        state = self.builder.with_campaign_id("test").build()
        assert isinstance(state, CampaignState)
        assert isinstance(state.process_tab, ProcessTabState)
        assert isinstance(state.campaign_tab, CampaignTabState)
```

### Integration Tests

```python
@pytest.mark.integration
class TestCampaignLoading(unittest.TestCase):
    def test_load_campaign_returns_correct_structure(self):
        """Test that _load_campaign returns expected tuple structure"""
        result = _load_campaign("Test Campaign", None)

        assert isinstance(result, tuple)
        assert len(result) == 38  # Expected number of outputs

        # Verify types of key elements
        assert isinstance(result[0], (str, type(None)))  # campaign_id
        assert isinstance(result[1], str)  # summary
        assert isinstance(result[2], str)  # manifest

    def test_load_campaign_ui_updates_correctly(self):
        """Test that UI actually updates when campaign loaded"""
        # This would be a manual or Selenium test
        pass
```

## Risks and Mitigation

### Risk 1: Breaking UI Updates
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Keep exact same tuple order
- Comprehensive regression testing
- Manual UI testing before deployment
- Feature flag for gradual rollout

### Risk 2: Tuple Position Errors
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Unit tests verify tuple order
- Document tuple positions clearly
- Consider named tuples as intermediate step
- Automated comparison with old implementation

### Risk 3: Performance Overhead
**Likelihood**: Low
**Impact**: Low
**Mitigation**:
- Builder creates objects once
- Benchmark before/after
- Profile object creation time
- Use `__slots__` for dataclasses if needed

### Risk 4: Gradio Compatibility Issues
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Test with current Gradio version
- Ensure gr.update() objects work as expected
- Keep compatibility layer (to_tuple methods)
- Test on development environment first

## Expected Benefits

### Immediate Benefits
1. **Improved Readability**: Clear state structure vs massive tuple
2. **Better Testing**: Can test each tab's state independently
3. **Easier Debugging**: Named fields vs positional arguments
4. **Type Safety**: IDE autocomplete for state fields
5. **Documentation**: State classes serve as documentation

### Long-term Benefits
1. **Maintainability**: Adding new UI elements is straightforward
2. **Modularity**: Each tab's state is independent
3. **Reusability**: State objects can be used elsewhere
4. **Testability**: Mock individual state components
5. **Refactoring**: Easier to change UI structure

### Future Enhancements
1. **State Persistence**: Save/load application state
2. **Undo/Redo**: Track state changes
3. **State Comparison**: Diff two states
4. **State Validation**: Validate state before applying to UI

### Metrics
- **Function Complexity**: Reduce from ~15 to ~5
- **Return Value Count**: Reduce from 25 to 1 (state object)
- **Test Coverage**: Increase to >95%
- **Lines of Code**: Similar (but much clearer)

## Migration Path

### Phase 1: Backward Compatible (Current Phase)
- New state classes coexist with tuple returns
- `to_tuple()` methods provide compatibility
- No changes to UI binding code

### Phase 2: Gradual Adoption
- Use state objects internally
- Convert to tuples at boundary
- Update tests to use state objects

### Phase 3: Full Migration (Future)
- Update Gradio bindings to use state objects directly
- Remove `to_tuple()` compatibility methods
- Update all related functions

## Success Criteria

1. ✅ All state dataclasses created and tested
2. ✅ `CampaignStateBuilder` implemented and tested
3. ✅ `_load_campaign()` refactored using builder
4. ✅ `_create_new_campaign()` refactored using builder
5. ✅ All existing UI tests pass
6. ✅ Manual UI testing confirms correct behavior
7. ✅ Code review approved
8. ✅ Documentation updated
9. ✅ No performance regression

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Create State Objects | 3-4 hours | None |
| Phase 2: Create Builder Class | 4-5 hours | Phase 1 |
| Phase 3: Refactor _load_campaign | 2 hours | Phase 2 |
| Phase 4: Refactor _create_new_campaign | 2 hours | Phase 3 |
| Phase 5: Testing | 3-4 hours | Phase 4 |
| Phase 6: Documentation | 1-2 hours | Phase 5 |
| **Total** | **15-19 hours** | |

## References

- Current implementation: `app.py:964-1041`
- Similar function: `app.py:1043-1117` (_create_new_campaign)
- UI tab references: Various UI modules in `src/ui/`
- Design patterns: Builder Pattern, State Object Pattern
- Related: Clean Code Chapter 3 (Functions)
