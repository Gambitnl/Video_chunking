# Implementation Plan: Session Analytics Dashboard

> **Task ID**: P2-ANALYTICS-001
> **Priority**: P2 (Important Enhancement)
> **Estimated Effort**: 2-3 days
> **Owner**: Claude (Sonnet 4.5)
> **Date Started**: 2025-11-17
> **Status**: In Progress

---

## Table of Contents
1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Architecture](#architecture)
4. [Implementation Steps](#implementation-steps)
5. [Testing Strategy](#testing-strategy)
6. [Success Criteria](#success-criteria)

---

## Overview

### Problem Statement
Users currently have no way to:
- Compare multiple sessions side-by-side
- Track character participation across sessions
- Analyze speaking time distribution
- Understand IC/OOC balance over time
- Visualize campaign progression

### Solution
Create a comprehensive Session Analytics Dashboard that provides:
1. **Session Comparison View** - Side-by-side comparison of 2+ sessions
2. **Character Participation Tracking** - Speaking time and message counts per character
3. **Speaking Time Distribution** - Who spoke how much and when
4. **IC/OOC Analysis** - Ratio of in-character to out-of-character content
5. **Timeline Visualization** - Campaign progression over sessions

### Impact
- **User Value**: HIGH - Enables DMs to understand group dynamics
- **Complexity**: MEDIUM - Data extraction + visualization
- **Dependencies**: Requires processed session JSON files

---

## Requirements

### Functional Requirements

**FR-1: Session Selection**
- User can select 1-5 sessions from dropdown
- Display shows basic session metadata (date, duration, participants)
- Validation prevents selecting non-existent sessions

**FR-2: Comparison View**
- Side-by-side display of selected sessions
- Metrics: Total duration, speaker count, IC/OOC ratio, message count
- Highlight differences between sessions (e.g., "Session 2 had 30% more IC content")

**FR-3: Character Participation**
- Bar chart showing speaking time per character across sessions
- Table showing message counts, word counts, average message length
- Filter by character to see participation trends

**FR-4: Speaking Time Distribution**
- Pie chart or bar chart showing time distribution among speakers
- Option to filter IC-only or OOC-only
- Detect imbalances (e.g., "Player X spoke 5x more than Player Y")

**FR-5: IC/OOC Timeline**
- Line chart showing IC/OOC ratio over time (session-by-session)
- Identify sessions with unusual ratios (too much OOC, etc.)
- Calculate campaign-wide averages

**FR-6: Export Analytics**
- Export analytics data to JSON, CSV, Markdown
- Include charts as images (optional, future enhancement)
- Generate printable report

### Non-Functional Requirements

**NFR-1: Performance**
- Analytics calculation should complete in <5 seconds for 10 sessions
- UI should remain responsive during calculations
- Cache analytics results to avoid recalculation

**NFR-2: Usability**
- Clear labels and tooltips
- Color-coded visualizations
- Graceful handling of missing/incomplete data

**NFR-3: Maintainability**
- Modular design (separate analytics engine from UI)
- Comprehensive unit tests (>85% coverage)
- Clear documentation with examples

---

## Architecture

### Component Overview

```
SessionAnalyticsDashboard
    |
    +-> SessionAnalyzer (core logic)
    |   +-> SessionMetricsExtractor
    |   +-> ComparisonEngine
    |   +-> TimelineGenerator
    |
    +-> AnalyticsDataModels (data classes)
    |   +-> SessionMetrics
    |   +-> CharacterStats
    |   +-> ComparisonResult
    |   +-> TimelineData
    |
    +-> AnalyticsVisualizer (charts/graphs)
    |   +-> ChartGenerator (matplotlib or plotly)
    |   +-> TableFormatter
    |
    +-> AnalyticsUI (Gradio tab)
        +-> Session selector
        +-> Comparison view
        +-> Charts display
        +-> Export functionality
```

### Data Flow

```
1. User selects sessions
   |
   v
2. SessionAnalyzer loads session JSON files
   |
   v
3. Extract metrics (duration, speakers, IC/OOC ratio, etc.)
   |
   v
4. Calculate comparisons and statistics
   |
   v
5. Generate visualizations
   |
   v
6. Display in Gradio UI
```

### File Structure

**New Files**:
```
src/analytics/
    __init__.py                    # Package init
    session_analyzer.py            # Core analytics engine (300-400 lines)
    data_models.py                 # Data classes for analytics (150-200 lines)
    visualizer.py                  # Chart generation (200-300 lines)
    exporter.py                    # Export functionality (100-150 lines)

src/ui/
    analytics_tab.py               # Gradio UI tab (400-500 lines)

tests/
    test_session_analyzer.py       # Unit tests for analyzer (20+ tests)
    test_analytics_data_models.py  # Tests for data models (10+ tests)
    test_analytics_visualizer.py   # Tests for visualizer (10+ tests)
    test_analytics_exporter.py     # Tests for exporter (10+ tests)
```

**Modified Files**:
```
app.py                             # Add analytics tab import
ROADMAP.md                         # Update status
docs/USAGE.md                      # Document analytics features
```

---

## Implementation Steps

### Phase 1: Core Analytics Engine (Day 1, ~6 hours)

#### Step 1.1: Create Data Models
**File**: `src/analytics/data_models.py`
**Time**: 1 hour

**Tasks**:
- [ ] Create `SessionMetrics` dataclass
  - session_id, duration, speaker_count, message_count
  - ic_message_count, ooc_message_count, ic_duration, ooc_duration
  - character_stats (dict of character -> CharacterStats)
  - timestamp (session date/time)
- [ ] Create `CharacterStats` dataclass
  - character_name, message_count, word_count, speaking_duration
  - ic_messages, ooc_messages
  - avg_message_length, first_appearance, last_appearance
- [ ] Create `ComparisonResult` dataclass
  - sessions (list of SessionMetrics)
  - differences (dict of metric -> values)
  - insights (list of auto-generated insights)
- [ ] Create `TimelineData` dataclass
  - sessions (chronologically ordered)
  - ic_ooc_ratios (list of tuples)
  - character_participation_over_time (dict)

**Implementation Notes**:
- Use Python dataclasses with type hints
- Add validation in `__post_init__`
- Include helper methods (e.g., `SessionMetrics.ic_percentage()`)
- Add docstrings for all classes and methods

#### Step 1.2: Implement SessionAnalyzer
**File**: `src/analytics/session_analyzer.py`
**Time**: 3 hours

**Tasks**:
- [ ] Create `SessionAnalyzer` class with methods:
  - `load_session(session_id: str) -> Optional[SessionMetrics]`
  - `load_multiple_sessions(session_ids: List[str]) -> List[SessionMetrics]`
  - `extract_metrics(session_data: dict) -> SessionMetrics`
  - `calculate_character_stats(segments: List[dict]) -> Dict[str, CharacterStats]`
  - `compare_sessions(sessions: List[SessionMetrics]) -> ComparisonResult`
  - `generate_timeline(sessions: List[SessionMetrics]) -> TimelineData`
  - `generate_insights(comparison: ComparisonResult) -> List[str]`
- [ ] Implement session JSON loading
  - Search output/ directory for session data JSON
  - Parse session metadata and segments
  - Handle missing/malformed data gracefully
- [ ] Implement metrics extraction
  - Calculate total duration from segments
  - Count IC vs OOC messages
  - Sum speaking durations per character
  - Calculate word counts and averages
- [ ] Implement comparison logic
  - Compute differences (absolute and percentage)
  - Identify outliers (e.g., unusually long/short sessions)
  - Generate auto-insights (e.g., "Session 2 had 40% more IC content")
- [ ] Implement timeline generation
  - Sort sessions chronologically
  - Extract IC/OOC ratio per session
  - Track character participation over time
  - Handle gaps in session dates

**Implementation Notes**:
- Use pathlib.Path for file operations
- Cache loaded session data (LRU cache with 30 min TTL)
- Log all operations with src.logger
- Raise clear exceptions for missing data
- Follow existing code patterns from src/formatter.py

#### Step 1.3: Write Unit Tests for Core Engine
**File**: `tests/test_session_analyzer.py`
**Time**: 2 hours

**Tasks**:
- [ ] Test session loading (valid, invalid, missing files)
- [ ] Test metrics extraction (sample session data)
- [ ] Test character stats calculation
- [ ] Test session comparison (2 sessions, 5 sessions)
- [ ] Test timeline generation
- [ ] Test insight generation
- [ ] Test caching behavior
- [ ] Test error handling (malformed JSON, missing fields)

**Implementation Notes**:
- Create fixture session JSON files (tests/fixtures/sessions/)
- Mock file I/O where appropriate
- Use pytest markers (@pytest.mark.fast)
- Aim for >85% branch coverage

### Phase 2: Visualization & Export (Day 2 Morning, ~4 hours)

#### Step 2.1: Implement Visualizer
**File**: `src/analytics/visualizer.py`
**Time**: 2 hours

**Tasks**:
- [ ] Create `AnalyticsVisualizer` class with methods:
  - `generate_comparison_table(comparison: ComparisonResult) -> str` (Markdown)
  - `generate_character_chart(stats: Dict[str, CharacterStats]) -> str` (Markdown bar chart)
  - `generate_ic_ooc_chart(timeline: TimelineData) -> str` (Markdown chart)
  - `generate_speaking_distribution(session: SessionMetrics) -> str` (Markdown)
- [ ] Implement text-based visualizations
  - Use ASCII bar charts for character participation
  - Use emoji/symbols for visual interest
  - Create formatted tables with borders
  - Generate summary statistics
- [ ] (Optional) Add Plotly integration
  - Generate interactive HTML charts
  - Export as standalone HTML files
  - Embed in Gradio UI (gr.HTML)

**Implementation Notes**:
- Start with simple Markdown tables/charts (ASCII art)
- Plotly integration is optional enhancement
- Use StatusIndicators for visual consistency
- Keep charts readable and accessible
- Add option to toggle between text/graphical charts

#### Step 2.2: Implement Exporter
**File**: `src/analytics/exporter.py`
**Time**: 1 hour

**Tasks**:
- [ ] Create `AnalyticsExporter` class with methods:
  - `export_to_json(data: Any, output_path: Path)`
  - `export_to_csv(comparison: ComparisonResult, output_path: Path)`
  - `export_to_markdown(comparison: ComparisonResult, output_path: Path)`
  - `export_full_report(comparison: ComparisonResult, output_dir: Path)`
- [ ] Implement JSON export
  - Serialize dataclasses to JSON
  - Include metadata (export timestamp, version)
- [ ] Implement CSV export
  - Flatten comparison data to rows
  - Include headers and formatting
- [ ] Implement Markdown export
  - Generate formatted report with sections
  - Include charts and tables
  - Add executive summary at top

**Implementation Notes**:
- Follow export patterns from src/search_exporter.py
- Add timestamps to exported filenames
- Validate output paths before writing
- Log all export operations

#### Step 2.3: Write Tests for Visualization & Export
**Files**: `tests/test_analytics_visualizer.py`, `tests/test_analytics_exporter.py`
**Time**: 1 hour

**Tasks**:
- [ ] Test chart generation (Markdown format)
- [ ] Test table formatting
- [ ] Test JSON export (serialization)
- [ ] Test CSV export (format validation)
- [ ] Test Markdown export (structure)
- [ ] Test error handling (invalid paths, permissions)

### Phase 3: UI Integration (Day 2 Afternoon, ~4 hours)

#### Step 3.1: Create Analytics Tab
**File**: `src/ui/analytics_tab.py`
**Time**: 3 hours

**Tasks**:
- [ ] Create `create_analytics_tab(project_root: Path)` function
- [ ] Implement UI components:
  - Multi-select dropdown for session selection (limit 5)
  - "Refresh Sessions" button
  - Comparison metrics display (gr.Markdown)
  - Character participation chart display
  - IC/OOC timeline chart display
  - Export buttons (JSON, CSV, Markdown)
  - Status indicator for operations
- [ ] Implement event handlers:
  - `load_available_sessions() -> List[str]`
  - `analyze_sessions(selected_sessions: List[str]) -> str` (Markdown output)
  - `export_analytics(format: str, data: Any) -> str` (status message)
- [ ] Add help text and examples
- [ ] Implement error handling and user feedback

**Implementation Notes**:
- Follow modern UI patterns from src/ui/search_tab.py
- Use StatusMessages for consistent feedback
- Add tooltips and placeholders
- Make sure UI is responsive (use gr.Row/Column)
- Add collapsible sections using gr.Accordion

**UI Layout**:
```
[Analytics Dashboard Tab]

  ### Session Analytics Dashboard

  [Help text with examples]

  ---- Session Selection ----
  [Multi-select dropdown] [Refresh] [Analyze]

  ---- Comparison View ----
  [Metrics table - Markdown]

  ---- Character Participation ----
  [Chart - Markdown or Plotly]

  ---- IC/OOC Timeline ----
  [Chart - Markdown or Plotly]

  ---- Insights ----
  [Auto-generated insights - Markdown]

  ---- Export ----
  [Export JSON] [Export CSV] [Export Markdown Report]

  [Status indicator]
```

#### Step 3.2: Integrate into app.py
**File**: `app.py`
**Time**: 30 minutes

**Tasks**:
- [ ] Import `create_analytics_tab` from src.ui.analytics_tab
- [ ] Add analytics tab to Gradio interface
- [ ] Position after "Campaign" tab, before "Characters" tab
- [ ] Test that tab loads correctly

**Implementation Notes**:
- Follow existing tab integration patterns
- Add error handling for import failures
- Update tab order in interface creation

#### Step 3.3: Manual UI Testing
**Time**: 30 minutes

**Tasks**:
- [ ] Start Gradio app: `python app.py`
- [ ] Navigate to Analytics tab
- [ ] Select 2-3 sessions
- [ ] Click "Analyze" and verify metrics display
- [ ] Test export functionality
- [ ] Test error cases (no sessions, invalid selection)
- [ ] Verify responsive layout on different screen sizes

### Phase 4: Documentation & Testing (Day 3, ~4 hours)

#### Step 4.1: Update Documentation
**Files**: `ROADMAP.md`, `docs/USAGE.md`, `docs/QUICKREF.md`
**Time**: 1 hour

**Tasks**:
- [ ] Update ROADMAP.md
  - Mark "Session Analytics Dashboard" as [DONE]
  - Add completion date and actual effort
  - Move to "Archived / Completed Work" section
- [ ] Update docs/USAGE.md
  - Add "Session Analytics" section
  - Document how to access and use the dashboard
  - Include screenshots or examples
- [ ] Update docs/QUICKREF.md
  - Add analytics quick reference commands
  - Document export formats

**Implementation Notes**:
- Use ASCII-only characters
- Follow existing documentation style
- Include practical examples
- Add troubleshooting tips

#### Step 4.2: Integration Testing
**File**: `tests/integration/test_analytics_integration.py`
**Time**: 1.5 hours

**Tasks**:
- [ ] Create end-to-end test
  - Load real session data from fixtures
  - Run full analytics pipeline
  - Verify all metrics calculated correctly
  - Test export functionality
  - Validate output files
- [ ] Test edge cases
  - Single session analysis
  - 5+ sessions
  - Sessions with missing data
  - Empty sessions

**Implementation Notes**:
- Use real session fixtures from tests/fixtures/
- Mark as @pytest.mark.integration
- May be slower than unit tests (acceptable)

#### Step 4.3: Final Test Suite Run
**Time**: 30 minutes

**Tasks**:
- [ ] Run full test suite: `pytest -q`
- [ ] Run analytics tests: `pytest tests/test_analytics* -v`
- [ ] Check test coverage: `pytest --cov=src/analytics --cov-report=html`
- [ ] Verify >85% coverage for all new modules
- [ ] Fix any failing tests

#### Step 4.4: Code Review & Cleanup
**Time**: 1 hour

**Tasks**:
- [ ] Review all new code for:
  - Type hints on all functions
  - Docstrings on all public functions/classes
  - Proper error handling
  - Logging statements
  - ASCII-only characters
  - Code style consistency
- [ ] Remove debug print statements
- [ ] Clean up unused imports
- [ ] Format code consistently
- [ ] Add/update code comments

### Phase 5: Critical Review & Improvements (Day 3 Afternoon, ~2 hours)

#### Step 5.1: Self-Review
**Time**: 1 hour

**Tasks**:
- [ ] Review implementation against requirements
- [ ] Test all user workflows manually
- [ ] Check for security issues (input validation, path traversal)
- [ ] Check for performance issues (caching, efficiency)
- [ ] Verify error messages are user-friendly
- [ ] Test with edge cases (0 sessions, 100 sessions, corrupt data)

#### Step 5.2: Identify Improvements
**Time**: 1 hour

**Tasks**:
- [ ] Find at least 3 improvements
- [ ] Categorize by: Security, Performance, UX, Code Quality
- [ ] Document each improvement:
  - What could be better?
  - Why it matters
  - How to implement (or why deferred)
- [ ] Implement quick wins (<30 min each)
- [ ] Document longer-term improvements for future tasks

**Expected Improvements** (examples):
1. **Performance**: Add batch processing for 10+ sessions
2. **UX**: Add date range filter for session selection
3. **Feature**: Add export to PDF with embedded charts
4. **Code Quality**: Extract chart generation to separate helper class
5. **Security**: Validate session IDs against path traversal
6. **Performance**: Implement incremental analytics (don't recalculate all)

---

## Testing Strategy

### Unit Tests
**Coverage Target**: >85% branch coverage

**Test Files**:
- `test_session_analyzer.py` (20+ tests)
  - Session loading (valid, invalid, missing)
  - Metrics extraction
  - Character stats calculation
  - Session comparison
  - Timeline generation
  - Insight generation
  - Error handling
- `test_analytics_data_models.py` (10+ tests)
  - Dataclass creation and validation
  - Helper methods (e.g., ic_percentage())
  - Edge cases (zero duration, no characters)
- `test_analytics_visualizer.py` (10+ tests)
  - Chart generation (Markdown format)
  - Table formatting
  - Edge cases (no data, single character)
- `test_analytics_exporter.py` (10+ tests)
  - JSON export
  - CSV export
  - Markdown export
  - File permissions and paths

### Integration Tests
**Test File**: `tests/integration/test_analytics_integration.py`

**Scenarios**:
- End-to-end analytics generation
- Export workflow (analyze -> export -> validate file)
- Error recovery (corrupt data, missing files)

### Manual Testing
**Scenarios**:
- UI navigation and usability
- Visual appearance of charts
- Export file validation
- Performance with large datasets
- Error messages clarity

---

## Success Criteria

### Functionality
- [ ] Users can select 1-5 sessions and view comparison metrics
- [ ] Character participation is calculated and displayed correctly
- [ ] IC/OOC timeline shows correct ratios
- [ ] Insights are auto-generated and meaningful
- [ ] Export to JSON, CSV, Markdown works correctly

### Quality
- [ ] >85% test coverage for all new modules
- [ ] All tests pass (unit + integration)
- [ ] No security vulnerabilities (input validation)
- [ ] Error messages are user-friendly (no stack traces)
- [ ] Code follows repository style guidelines

### Performance
- [ ] Analytics calculation completes in <5s for 10 sessions
- [ ] UI remains responsive during calculations
- [ ] Results are cached to avoid recalculation

### Documentation
- [ ] ROADMAP.md updated with completion status
- [ ] docs/USAGE.md documents analytics features
- [ ] Code comments explain complex logic
- [ ] Docstrings on all public functions

### User Experience
- [ ] UI is intuitive and easy to navigate
- [ ] Charts are readable and informative
- [ ] Export files are well-formatted
- [ ] Status indicators show operation progress

---

## Risk Assessment

### Risks

**R1: Session Data Format Inconsistency**
- **Impact**: HIGH
- **Probability**: MEDIUM
- **Mitigation**: Add schema validation, handle missing fields gracefully

**R2: Performance with Large Datasets**
- **Impact**: MEDIUM
- **Probability**: MEDIUM
- **Mitigation**: Implement caching, limit session selection to 5

**R3: Chart Visualization Complexity**
- **Impact**: LOW
- **Probability**: LOW
- **Mitigation**: Start with simple Markdown charts, add Plotly later

**R4: UI Integration Issues**
- **Impact**: MEDIUM
- **Probability**: LOW
- **Mitigation**: Follow existing tab patterns, test early

---

## Implementation Notes & Reasoning

*(This section will be updated during implementation)*

### Design Decisions
- **Why Markdown charts instead of Plotly initially?**
  - Lower complexity, faster implementation
  - ASCII charts work everywhere (no JS dependencies)
  - Can add Plotly later as enhancement

- **Why limit session selection to 5?**
  - Prevents performance issues
  - Comparison becomes less useful with too many sessions
  - Can be increased later if needed

- **Why separate analytics engine from UI?**
  - Enables CLI usage in future
  - Easier to test
  - Can be used by other components (e.g., campaign dashboard)

### Alternatives Considered
- **Plotly vs Matplotlib**: Chose text-based initially for simplicity
- **Real-time vs Cached**: Chose cached analytics with refresh button
- **Single vs Multi-file architecture**: Chose multi-file for maintainability

### Trade-offs
- **Simplicity vs Features**: Prioritized core features, deferred advanced charts
- **Performance vs Accuracy**: Used caching to balance both
- **Flexibility vs Complexity**: Fixed schema for now, can extend later

---

## Post-Implementation Review

### What Went Well
1. **Modular Architecture**: Separating data models, analyzer, visualizer, and exporter made the code easy to test and maintain
2. **Comprehensive Type Hints**: Using dataclasses with full type annotations caught bugs early and improved IDE support
3. **LRU Caching**: Caching session loads significantly improved performance when analyzing the same sessions multiple times
4. **Clear Data Flow**: The pipeline from loading -> extracting -> comparing -> visualizing was intuitive and easy to follow
5. **Markdown Visualizations**: Starting with simple Markdown charts instead of complex plotting libraries kept implementation fast
6. **Test-Driven Design**: Writing tests alongside implementation helped catch edge cases (e.g., zero messages, empty sessions)

### What Could Be Improved
1. **Limited Chart Types**: Only text-based ASCII charts - no interactive visualizations yet
2. **No Persistent State**: Analytics results are not saved - need to recalculate each time
3. **Limited Session Selection**: 5-session limit is arbitrary - could be smarter (e.g., based on memory)
4. **No Progress Indicators**: Long-running analysis operations don't show progress
5. **Character Name Mapping**: No handling of speaker ID -> character name inconsistencies across sessions

### Lessons Learned
1. **Start Simple**: Text-based visualizations were sufficient for v1 - don't over-engineer
2. **Cache Aggressively**: LRU cache on session loading eliminated most performance concerns
3. **Validate Early**: Dataclass `__post_init__` validation caught many bugs during development
4. **Markdown is Powerful**: Gradio's Markdown rendering makes simple charts look professional
5. **Testing Fixtures**: Creating comprehensive test fixtures upfront made testing much faster

### Future Enhancements
1. **Interactive Charts**: Add Plotly/Chart.js integration for interactive visualizations
2. **Persistent Analytics**: Save analytics results to database for historical tracking
3. **Advanced Insights**: Use ML to detect patterns (e.g., "combat sessions are getting shorter")
4. **Character Consistency**: Smart matching of speaker IDs to character names across sessions
5. **Export to PDF**: Generate printable PDF reports with embedded charts
6. **Comparative Metrics**: Compare current campaign to other campaigns (if multiple exist)
7. **Real-Time Analytics**: Update analytics as sessions are processed

---

## Changelog

- **2025-11-17 08:00**: Created implementation plan
- **2025-11-17 09:00**: Implemented data models (CharacterStats, SessionMetrics, ComparisonResult, TimelineData)
- **2025-11-17 10:00**: Implemented SessionAnalyzer core engine (load, extract, compare, insights)
- **2025-11-17 11:00**: Implemented Visualizer (Markdown charts and tables)
- **2025-11-17 11:30**: Implemented Exporter (JSON, CSV, Markdown)
- **2025-11-17 12:00**: Created Gradio UI tab with event handlers
- **2025-11-17 12:30**: Integrated analytics tab into app.py
- **2025-11-17 13:00**: Wrote comprehensive unit tests (50+ tests)
- **2025-11-17 13:30**: Updated documentation and ROADMAP.md
- **2025-11-17 14:00**: **IMPLEMENTATION COMPLETE**
