# CLM-05: Tab-Level Campaign Filtering Implementation

**Status**: PARTIAL IMPLEMENTATION - Backend Complete, UI Integration Pending
**Author**: Claude Code
**Date**: 2025-11-02
**Related**: CAMPAIGN_LIFECYCLE_IMPLEMENTATION.md, IMPLEMENTATION_PLANS_PART2.md:929-933

---

## Overview

This document tracks the implementation of **CLM-05: Tab-Level Filtering & Legacy Cleanup** - ensuring that when a user selects a campaign, all tabs show only data for that campaign.

### Success Criteria

- [x] **Backend filtering implemented** for core services (StoryNotebookManager)
- [x] **Comprehensive test coverage** for filtering logic
- [ ] **UI integration** - campaign selectors added to all relevant tabs
- [ ] **Character profile filtering** integrated into UI
- [ ] **LLM Chat tab** uses campaign-filtered profiles
- [ ] **Social Insights tab** filters by campaign
- [x] **Documentation** for backend implementation

---

## Completed Work (2025-11-02)

### 1. Story Notebook Manager Campaign Filtering

**Files Modified**: [`src/story_notebook.py`](../src/story_notebook.py)

#### Changes to `list_sessions()` Method

Added campaign filtering with graceful degradation for legacy sessions:

```python
def list_sessions(
    self,
    limit: Optional[int] = 25,
    campaign_id: Optional[str] = None,
    include_unassigned: bool = True,
) -> List[str]:
    """Return recent session IDs based on available *_data.json outputs.

    Args:
        limit: Maximum number of sessions to return (None for unlimited)
        campaign_id: Filter sessions by campaign_id. None returns all sessions.
        include_unassigned: If campaign_id is specified, whether to include
                           sessions without campaign_id metadata (legacy sessions)

    Returns:
        List of session IDs matching the filter criteria, sorted by modification time
    """
```

**Key Features**:
- **Backward Compatible**: Works with both new (with campaign_id) and legacy (without campaign_id) sessions
- **Graceful Degradation**: `include_unassigned=True` by default means legacy sessions appear in campaign views
- **Flexible Filtering**: Can strictly filter (`include_unassigned=False`) or be permissive

**Design Decisions**:

1. **Why `include_unassigned=True` by default?**
   - Users shouldn't lose access to existing sessions when they create their first campaign
   - Provides a smooth migration path - users can gradually assign sessions to campaigns
   - Follows the "Allow campaign_id: null in metadata" principle from CLM-01

2. **Why read metadata inside the loop?**
   - Avoids loading all session files into memory at once
   - Allows lazy evaluation for better performance with large session libraries
   - Handles corrupted files gracefully (skips them rather than crashing)

#### Changes to `build_session_info()` Method

Enhanced session info display to show campaign assignment:

```python
# Show campaign info if available
campaign_id = metadata.get("campaign_id")
campaign_name = metadata.get("campaign_name")
if campaign_id and campaign_name:
    details.append(f"- **Campaign**: {campaign_name} (`{campaign_id}`)")
elif campaign_id:
    details.append(f"- **Campaign ID**: `{campaign_id}`")
else:
    details.append(f"- **Campaign**: *Unassigned* (use migration tools to assign)")
```

**User Benefits**:
- Immediately see which campaign a session belongs to
- Clear indication when a session is unassigned (legacy)
- Helpful reminder about migration tools

---

### 2. Comprehensive Test Suite

**Files Created**: [`tests/test_story_notebook_campaign_filtering.py`](../tests/test_story_notebook_campaign_filtering.py)

Created 10 comprehensive tests covering all filtering scenarios:

| Test | Purpose |
|------|---------|
| `test_list_sessions_no_filter` | Verify no filtering returns all sessions |
| `test_list_sessions_filter_by_campaign` | Verify campaign filtering works (includes unassigned) |
| `test_list_sessions_include_unassigned` | Verify `include_unassigned=True` behavior |
| `test_list_sessions_exclude_unassigned` | Verify `include_unassigned=False` behavior |
| `test_list_sessions_with_limit` | Verify limit works with filtering |
| `test_list_sessions_nonexistent_campaign` | Verify filtering for non-existent campaigns |
| `test_build_session_info_with_campaign` | Verify campaign info display |
| `test_build_session_info_without_campaign` | Verify unassigned session display |
| `test_list_sessions_empty_directory` | Verify graceful handling of empty dirs |
| `test_list_sessions_corrupted_metadata` | Verify handling of corrupted session files |

**Test Results**: ✅ **All 10 tests passing** (0.33s execution time)

```bash
============================= test session starts =============================
tests/test_story_notebook_campaign_filtering.py::test_list_sessions_no_filter PASSED
tests/test_story_notebook_campaign_filtering.py::test_list_sessions_filter_by_campaign PASSED
tests/test_story_notebook_campaign_filtering.py::test_list_sessions_include_unassigned PASSED
tests/test_story_notebook_campaign_filtering.py::test_list_sessions_exclude_unassigned PASSED
tests/test_story_notebook_campaign_filtering.py::test_list_sessions_with_limit PASSED
tests/test_story_notebook_campaign_filtering.py::test_list_sessions_nonexistent_campaign PASSED
tests/test_story_notebook_campaign_filtering.py::test_build_session_info_with_campaign PASSED
tests/test_story_notebook_campaign_filtering.py::test_build_session_info_without_campaign PASSED
tests/test_story_notebook_campaign_filtering.py::test_list_sessions_empty_directory PASSED
tests/test_story_notebook_campaign_filtering.py::test_list_sessions_corrupted_metadata PASSED
============================= 10 passed in 0.33s =========================
```

---

## Remaining Work

### 3. Story Notebook Tab ✅ Complete

**Files Modified**: [`src/ui/story_notebook_tab.py`](../src/ui/story_notebook_tab.py)
**Test Coverage**: [`tests/test_story_notebook_tab_campaign_filtering.py`](../tests/test_story_notebook_tab_campaign_filtering.py)
**Status**: Implementation complete, 3 tests passing

#### Changes Implemented

1. **Function Signature Update**:
   - Added `refresh_campaign_names: Callable[[], Dict[str, str]]` parameter
   - Allows tab to access campaign list dynamically

2. **Campaign Selector UI**:
   ```python
   campaign_selector = gr.Dropdown(
       choices=["All Campaigns"] + list(campaign_names.values()),
       value="All Campaigns",
       label="Filter by Campaign",
       info="Show only sessions from the selected campaign (includes unassigned sessions)"
   )
   ```

3. **story_refresh_sessions_ui() Enhancement**:
   - Accepts `campaign_name: str` parameter
   - Maps campaign name to campaign_id using refresh_campaign_names()
   - Filters sessions using `story_manager.list_sessions(campaign_id=campaign_id)`
   - Handles "All Campaigns" case (shows all sessions)

4. **story_select_session_ui() Enhancement**:
   - Accepts `campaign_name: str` parameter
   - Maps campaign name to campaign_id
   - Filters sessions by selected campaign

5. **Event Handlers**:
   - `campaign_selector.change()` → refreshes session list automatically
   - `refresh_story_btn.click()` → respects selected campaign
   - `story_session_dropdown.change()` → uses campaign-filtered session list

#### Implementation Notes

**Campaign Filtering Behavior**:
- "All Campaigns" option shows all sessions (campaign_id=None)
- Campaign-specific filtering includes unassigned sessions by default (graceful degradation)
- Uses StoryNotebookManager.list_sessions(campaign_id=...) for backend filtering

**Backward Compatibility**:
- Requires refresh_campaign_names parameter (breaking change to function signature)
- Internal logic fully backward compatible with unassigned sessions
- No changes required to existing story generation functions

**Test Coverage**:
- Signature validation (ensures refresh_campaign_names callback is accepted)
- Component creation verification (campaign selector exists)
- Empty campaigns handling (graceful degradation)

---

### 4. Character Profile Tab Integration

**File**: [`src/ui/character_profiles_tab.py`](../src/ui/character_profiles_tab.py)

**What Needs to Be Done**:
1. Add campaign selector dropdown
2. Use existing `CharacterProfileManager.get_profiles_by_campaign()` method
3. Update profile list to show only campaign-specific profiles
4. Add UI indicator for profiles without campaign assignment

**Complexity**: Low - backend method already exists

**Estimated Effort**: 1 hour

---

### 5. LLM Chat Tab Integration

**File**: [`src/ui/llm_chat_tab.py`](../src/ui/llm_chat_tab.py)

**What Needs to Be Done**:
1. Accept campaign_id parameter (from parent context)
2. Filter character dropdown using `get_profiles_by_campaign(campaign_id)`
3. Show message if no characters exist for selected campaign

**Complexity**: Low - straightforward filter application

**Estimated Effort**: 30 minutes

---

### 6. Social Insights Tab Enhancement

**File**: [`src/ui/social_insights_tab.py`](../src/ui/social_insights_tab.py)

**Current State**: Uses manual session_id input

**What Needs to Be Done**:
1. Add campaign selector dropdown
2. Add session dropdown (filtered by campaign using `StoryNotebookManager.list_sessions()`)
3. Replace manual session_id input with dropdown selection
4. Optionally create `SocialInsightsManager` class for better organization

**Complexity**: Medium - requires refactoring from text input to dropdown

**Estimated Effort**: 1-2 hours

---

## UI Integration Progress (2025-11-02)

### Character Profiles Tab ✅ Complete (Legacy Tab)

**Files Modified**: [`src/ui/character_profiles_tab.py`](../src/ui/character_profiles_tab.py)
**Test Coverage**: [`tests/test_character_profiles_tab_campaign_filtering.py`](../tests/test_character_profiles_tab_campaign_filtering.py)
**Status**: Implementation complete, 2 tests passing

---

### LLM Chat Tab ✅ Complete

**Files Modified**: [`src/ui/llm_chat_tab.py`](../src/ui/llm_chat_tab.py)
**Test Coverage**: [`tests/test_llm_chat_tab_campaign_filtering.py`](../tests/test_llm_chat_tab_campaign_filtering.py)
**Status**: Implementation complete, 3 tests passing

#### Changes Implemented

1. **Function Signature Update**:
   - Added `campaign_id: Optional[str] = None` parameter
   - Allows tab to filter characters by campaign

2. **Character Loading Refactor**:
   - Replaced direct JSON file loading with CharacterProfileManager
   - Uses `get_profiles_by_campaign(campaign_id)` when campaign is specified
   - Falls back to all characters when no campaign specified (backward compatible)

3. **Empty State Handling**:
   ```python
   if campaign_id and len(character_profiles) == 0:
       gr.Markdown(StatusMessages.info(
           "No Characters in Campaign",
           "This campaign has no character profiles yet."
       ))
   ```

4. **Profile Data Conversion**:
   - Converts CharacterProfile objects to dict format for chat function
   - Extracts description, personality, and backstory fields
   - Maintains compatibility with existing chat_with_llm() function

#### Implementation Notes

**Backward Compatibility**:
- Default `campaign_id=None` shows all characters (existing behavior)
- Tab works seamlessly whether campaign filtering is used or not

**Character Profile Integration**:
- Now uses centralized CharacterProfileManager instead of direct file access
- Benefits from campaign-aware filtering built into the manager
- More maintainable and consistent with rest of codebase

**Test Coverage**:
- Campaign ID parameter acceptance validated
- Backward compatibility without campaign_id tested
- Component creation verified

---

#### Changes Implemented (Character Profiles Tab)

1. **Function Signature Update**:
   - Added `refresh_campaign_names: Callable[[], Dict[str, str]]` parameter
   - Allows tab to access campaign list dynamically

2. **Campaign Selector UI**:
   ```python
   campaign_selector = gr.Dropdown(
       choices=["All Campaigns"] + list(campaign_names.values()),
       value="All Campaigns",
       label="Filter by Campaign",
       info="Show only characters from the selected campaign"
   )
   ```

3. **load_character_list() Enhancement**:
   - Accepts `campaign_name: str` parameter
   - Maps campaign name to campaign_id using refresh_campaign_names()
   - Filters characters using `manager.list_characters(campaign_id=campaign_id)`
   - Handles "All Campaigns" case (shows all characters)

4. **Event Handlers**:
   - `campaign_selector.change()` → refreshes character list automatically
   - `char_refresh_btn.click()` → respects selected campaign
   - `char_table.select()` → uses campaign-filtered character list

#### Implementation Notes

**Why Legacy Tab?**
The modern UI (`characters_tab_modern.py`) currently contains placeholder HTML. The legacy `character_profiles_tab.py` has full functionality and is ready to be integrated into the modern UI when the placeholders are replaced with real components.

**Graceful Degradation**:
- "All Campaigns" option shows all characters (campaign_id=None)
- Works seamlessly with unassigned characters (campaign_id=None)
- No breaking changes to existing functionality

**Test Coverage**:
- Signature validation (ensures refresh_campaign_names callback is accepted)
- Component creation verification (campaign selector exists)
- Integration-ready for when modern UI calls this tab

---

## Integration Strategy

### Recommended Implementation Order

1. **Character Profile Tab** (easiest, builds confidence)
2. **LLM Chat Tab** (depends on #1)
3. **Story Notebook Tab** (most complex, save for last)
4. **Social Insights Tab** (optional refactoring, can be done separately)

### Global Campaign Selector Consideration

**Alternative Approach**: Instead of adding campaign selectors to each tab individually, consider:
- Single top-level campaign selector in app.py
- Store selected campaign in `gr.State` accessible to all tabs
- All tabs read from this global campaign state
- Benefits: Consistency, less code duplication, single source of truth
- Challenges: Requires refactoring existing tab signatures

**Recommendation**: Implement per-tab selectors first (as planned), then optionally refactor to global selector in a future iteration.

---

## Testing Strategy

### Backend Testing ✅ Complete

- [x] Unit tests for `list_sessions()` filtering
- [x] Edge case testing (empty dirs, corrupted files, legacy sessions)
- [x] Test coverage for `include_unassigned` parameter
- [x] Session info display testing

### UI Testing (Pending)

- [ ] Integration test: Select campaign, verify tabs update
- [ ] Manual test: Create new campaign, process session, verify appears in campaign view
- [ ] Manual test: Legacy sessions appear with "Unassigned" indicator
- [ ] Manual test: Switch campaigns, verify session list updates correctly
- [ ] Manual test: Character profiles filter by campaign
- [ ] Manual test: LLM Chat uses campaign-filtered characters

---

## Documentation Updates

- [x] This implementation document created
- [x] Inline code documentation (docstrings) updated
- [ ] Update [`docs/USAGE.md`](USAGE.md) with campaign filtering workflow
- [ ] Update [`docs/QUICK REF.md`](QUICKREF.md) with campaign selector usage
- [ ] Update [`README.md`](../README.md) with campaign features overview

---

## Design Patterns & Best Practices

### Pattern: Graceful Degradation

```python
# Good: Allows mixed old/new data
sessions = manager.list_sessions(campaign_id="my_campaign", include_unassigned=True)

# Strict: Only shows explicitly assigned sessions
sessions = manager.list_sessions(campaign_id="my_campaign", include_unassigned=False)
```

**Why This Works**:
- Users don't lose access to legacy data
- Provides clear path for incremental migration
- Supports both power users (who want strict filtering) and casual users (who want everything)

### Pattern: Informative UI Feedback

```python
if campaign_id and campaign_name:
    details.append(f"- **Campaign**: {campaign_name} (`{campaign_id}`)")
elif campaign_id:
    details.append(f"- **Campaign ID**: `{campaign_id}`")
else:
    details.append(f"- **Campaign**: *Unassigned* (use migration tools to assign)")
```

**Why This Works**:
- Users immediately see campaign assignment status
- Provides actionable hint (migration tools) for unassigned sessions
- Handles partial data gracefully (campaign_id without campaign_name)

---

## Known Limitations

1. **No automatic UI refresh on campaign selection** - Users must click "Refresh" after selecting a campaign
   - **Future Enhancement**: Add reactive updates using Gradio's event system

2. **Character profiles use `get_profiles_by_campaign()` but UI doesn't expose it yet** - Backend ready, UI pending
   - **Impact**: Medium - users can't filter character profiles by campaign in UI

3. **No global campaign context** - Each tab manages campaign selection independently
   - **Impact**: Low - Works fine, but could be more elegant with global state

4. **Social Insights tab still uses manual session_id input** - No campaign integration
   - **Impact**: Low - Tab is rarely used, can be enhanced later

---

## Performance Considerations

### Current Implementation

- **List Sessions**: O(n) where n = number of session files
  - Reads metadata for each file when filtering by campaign
  - Lazy evaluation prevents loading all sessions into memory

- **Memory Usage**: Minimal - only stores session IDs in memory, not full data

### Optimization Opportunities (Future)

1. **Session Metadata Cache**: Cache campaign_id mappings to avoid repeated file reads
2. **Index File**: Create `sessions_index.json` mapping campaign_id → session_ids
3. **Parallel Processing**: Use multiprocessing to read session metadata in parallel

**Current Performance**: Acceptable for typical usage (<1000 sessions)

---

## Migration Path for Users

### Scenario 1: New User (No Legacy Data)

1. Create campaign using Campaign Dashboard
2. Process sessions with campaign selected
3. All sessions automatically assigned to campaign
4. **Result**: Clean, organized data from day one

### Scenario 2: Existing User (Has Legacy Data)

1. Create campaign using Campaign Dashboard
2. Run migration tools to assign existing sessions:
   ```bash
   python cli.py campaigns migrate-sessions my_campaign --dry-run
   python cli.py campaigns migrate-sessions my_campaign
   ```
3. Process new sessions with campaign selected
4. **Result**: Legacy and new data both assigned to campaign

### Scenario 3: Multiple Campaigns

1. Create multiple campaigns
2. Assign sessions to appropriate campaigns using migration tools with `--filter`:
   ```bash
   python cli.py campaigns migrate-sessions campaign_1 --filter "Season_1_*"
   python cli.py campaigns migrate-sessions campaign_2 --filter "Season_2_*"
   ```
3. Unassigned sessions appear in all campaign views (with `include_unassigned=True`)
4. **Result**: Organized by campaign, with shared pool of unassigned sessions

---

## Conclusion

**Status Summary**:
- ✅ **Backend Implementation**: Complete and tested
- ✅ **Test Coverage**: 18 tests, all passing (10 backend + 8 UI)
- ✅ **Documentation**: Implementation documented
- ✅ **Character Profiles Tab**: Complete (legacy tab ready for modern UI)
- ✅ **LLM Chat Tab**: Complete (campaign-aware character filtering)
- ✅ **Story Notebook Tab**: Complete (campaign-aware session filtering)
- ⏳ **UI Integration**: 1 tab remaining (Social Insights - optional)

**Completed Work (2025-11-02)**:
1. ✅ Character Profile tab - Campaign filtering implemented and tested (2 tests)
2. ✅ LLM Chat tab - Campaign-aware character loading and filtering (3 tests)
3. ✅ Story Notebook tab - Campaign-aware session filtering (3 tests)

**Next Steps**:
1. Update Social Insights tab (optional enhancement)
2. Integrate legacy character_profiles_tab into modern UI when placeholders are replaced

**Estimated Remaining Effort**: 1-2 hours for Social Insights tab (optional)

---

*Last Updated: 2025-11-02*
