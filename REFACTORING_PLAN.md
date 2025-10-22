Task Summary: Refactoring Candidates for D&D Session Processor

> **WARNING: DEPRECATED - 2025-10-22**
> This refactoring plan has been consolidated into **ROADMAP.md** under "P0: Code Refactoring".
> Please refer to ROADMAP.md for the current implementation order and priorities.
> This file is kept for historical reference only.

---

  Context

  The D&D Session Transcription system has grown significantly with new features:     
  - Campaign Dashboard (health check visualization)
  - Campaign Knowledge Base (automatic entity extraction)
  - Import Session Notes (backfilling early sessions)
  - Story Notebooks (narrative generation)

  The codebase now has 7,184 lines across all source files, with app.py containing    
   2,564 lines - indicating it has become a maintenance bottleneck.

  Completed Work

  1. ✅ Documentation Updated: All .md files updated for new features
  2. ✅ Bug Hunt Completed: Fixed 2 Unicode encoding bugs
    - app.py:2548 - Replaced emoji with ASCII text
    - src/chunker.py:82 - Replaced ≈ symbol with ~
  3. ✅ Syntax Validation: All files pass Python compilation

  Identified Refactoring Candidates

  Priority 1: HIGH - Extract Campaign Dashboard Logic

  File: app.py (lines 608-847, ~240 lines)
  Function: generate_campaign_dashboard()

  Problem:
  - Single massive function checking 6 components
  - Mixed concerns (data fetching, validation, markdown generation)
  - Hard to test and maintain

  Proposed Solution:
  # Create: src/campaign_dashboard.py
  class CampaignDashboard:
      def _check_party_config(self, campaign) -> ComponentStatus
      def _check_processing_settings(self, campaign) -> ComponentStatus
      def _check_knowledge_base(self, campaign_id) -> ComponentStatus
      def _check_character_profiles(self, party) -> ComponentStatus
      def _check_processed_sessions(self) -> ComponentStatus
      def _check_session_narratives(self) -> ComponentStatus
      def generate(self, campaign_name) -> str

  Benefits:
  - Testable components
  - Reusable logic outside Gradio
  - Cleaner separation of concerns

  ---
  Priority 2: HIGH - Split app.py into UI Modules

  File: app.py (2,564 lines total)

  Problem:
  - Monolithic file with all UI logic
  - 23+ nested function definitions
  - Hard to navigate and modify

  Proposed Structure:
  src/ui/
  ├── __init__.py
  ├── campaign_dashboard.py      # Dashboard tab (~240 lines)
  ├── import_notes.py             # Import session notes tab (~200 lines)
  ├── story_notebooks.py          # Story generation tab (~150 lines)
  ├── party_management.py         # Party config tab (~300 lines)
  ├── character_profiles.py       # Character profiles tab (~200 lines)
  ├── knowledge_library.py        # Campaign library tab (~150 lines)
  └── helpers.py                  # Common UI patterns/utilities

  Benefits:
  - Each module < 300 lines
  - Independent testing
  - Team collaboration easier
  - Faster IDE navigation

  ---
  Priority 3: MEDIUM - Extract Story Generation Logic

  File: app.py (lines ~300-338)
  Function: _generate_perspective_story()

  Problem:
  - Mixes LLM calling with log suppression
  - Embedded in UI code
  - Not reusable outside Gradio

  Proposed Solution:
  # Create: src/story_generator.py
  class StoryGenerator:
      @contextmanager
      def suppress_llm_logs(self):
          # Handle stdout/stderr suppression

      def generate_narrator_summary(self, ic_transcript, temperature=0.5) -> str      
      def generate_character_pov(self, ic_transcript, character, temperature=0.5)     
  -> str

  Benefits:
  - CLI can use story generation
  - Testable without Gradio
  - Cleaner log management

  ---
  Priority 4: MEDIUM - Create Status Indicator Constants

  Location: Scattered throughout app.py and dashboard code

  Problem:
  # Magic strings everywhere
  "✅", "❌", "⚠️", "🟢", "🟡", "🟠", "🔴"

  Proposed Solution:
  # Create: src/ui/constants.py
  class StatusIndicators:
      SUCCESS = "✅"
      ERROR = "❌"
      WARNING = "⚠️"
      HEALTH_EXCELLENT = "🟢"  # 90-100%
      HEALTH_GOOD = "🟡"        # 70-89%
      HEALTH_FAIR = "🟠"        # 50-69%
      HEALTH_POOR = "🔴"        # 0-49%

  Benefits:
  - Windows cp1252 compatibility in one place
  - Easy to swap ASCII fallbacks
  - Consistent styling

  ---
  Priority 5: LOW - Create MarkdownBuilder Helper

  Problem: String concatenation for markdown throughout dashboard

  Proposed Solution:
  # Create: src/ui/markdown_builder.py
  class MarkdownBuilder:
      def header(self, text, level=1)
      def status(self, is_good, component, details)
      def list_item(self, text)
      def code_block(self, text)
      def build() -> str

  Benefits:
  - Cleaner dashboard code
  - Consistent markdown formatting
  - Easier to modify output format

  ---
  Recommended Implementation Order

  1. Start with Priority 4 (constants) - Quick win, reduces risk
  2. Then Priority 1 (dashboard extraction) - High impact, moderate effort
  3. Then Priority 3 (story generator) - Enables CLI usage
  4. Then Priority 2 (UI split) - Large refactor, do last
  5. Skip Priority 5 for now - Nice to have, not critical

  Success Criteria

  - ✅ All existing tests still pass
  - ✅ UI functionality unchanged
  - ✅ app.py reduced to < 1000 lines
  - ✅ New modules have < 300 lines each
  - ✅ 100% backward compatibility

  Files to Modify

  - app.py - Extract logic, import from new modules
  - Create src/ui/ directory structure
  - Create src/campaign_dashboard.py
  - Create src/story_generator.py
  - Create src/ui/constants.py

  Testing Strategy

  1. Run existing tests after each extraction
  2. Manual UI testing in Gradio
  3. Verify all tabs still functional
  4. Check for import errors

  ---
  Handover Note: All bugs are fixed, documentation is complete. The refactoring is    
   optional but recommended for long-term maintainability. Start with small,
  low-risk changes (constants) and work up to larger refactors (UI split).
