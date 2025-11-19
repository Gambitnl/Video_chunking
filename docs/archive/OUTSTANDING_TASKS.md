# Outstanding Tasks - Master Checklist



> **Last Updated**: 2025-11-06

> **Purpose**: Single source of truth for all open work items

> **Sources**: ROADMAP.md, BUG_HUNT_TODO.md, BUG_SUMMARY.md, IMPLEMENTATION_PLANS_*.md



---



## ⚠️ Task Locking Protocol (Multi-Agent Coordination)



**CRITICAL**: When starting work on ANY task, you MUST lock it immediately to prevent duplicate work.



### Locking Workflow



1. **Before starting**: Change `[ ]` to `[~]` with agent name + timestamp

2. **Commit immediately**: `git add docs/OUTSTANDING_TASKS.md && git commit -m "Lock task: Task-ID"`

3. **After completion**: Update `[~]` to `[x]` with completion date



### Status Meanings



- `[ ]` = Available (no one working on this)

- `[~]` = Locked (another agent is working - DO NOT START)

- `[x]` = Complete (verified implementation exists)



### Abandoned Tasks



If you find a `[~]` task with timestamp >24 hours old:

1. Check git history for recent commits on that task

2. If no activity, ask user for permission to take over

3. Update with your agent name and new timestamp



---



## Quick Stats



- **P0**: ✅ ALL COMPLETE (9/9 done)

- **P1**: ✅ ALL COMPLETE (6/6 done)

- **P2**: 🟡 Core complete, 2 polish items remain

- **P3**: ⏸️ Deferred (0/3 started)

- **P4**: ⏸️ Deferred (0/4 started)

- **Bugs**: 🔴 85 open (58 LangChain test gaps + 27 UI issues)



**Legend**:

- `[ ]` Not Started (available for work)

- `[~]` In Progress (locked by agent - includes agent name + start timestamp)

- `[x]` Completed (includes completion date)

- ✅ Complete | 🟡 In Progress | 🔴 High Priority | ⏸️ Paused



**Task Locking Format**:

```

[~] Task-ID: Description (Agent: Name, Started: YYYY-MM-DD HH:MM UTC) → source:line

[x] Task-ID: Description (Agent: Name, Completed: YYYY-MM-DD) → source:line

```



---



## P0 (Critical / Immediate)



✅ **ALL COMPLETE** (2025-10-26)



- [x] P0-BUG-001: Stale Clip Cleanup → ROADMAP.md:68-72

- [x] P0-BUG-002: Unsafe Type Casting → ROADMAP.md:73-79

- [x] P0-BUG-003: Checkpoint System → ROADMAP.md:80-84

- [x] P0-BUG-004: Improve Resumable Checkpoints → ROADMAP.md:87-91

- [x] P0-BUG-005: Surface Chunking Failures → ROADMAP.md:92-98

- [x] P0-BUG-006: Refine Snippet Placeholder Output → ROADMAP.md:99-105

- [x] P0-REFACTOR-001: Extract Campaign Dashboard → ROADMAP.md:118-124

- [x] P0-REFACTOR-002: Extract Story Generation → ROADMAP.md:126-132

- [x] P0-REFACTOR-003: Split app.py into UI Modules → ROADMAP.md:134-139



---



## P1 (High Impact)



✅ **ALL COMPLETE** (6/6 done as of 2025-11-02)



- [x] P1-FEATURE-001: Automatic Character Profile Extraction (2025-10-31) → IMPLEMENTATION_PLANS_PART2.md:29

- [x] P1-FEATURE-002: Streaming Snippet Export (2025-11-01) → IMPLEMENTATION_PLANS_PART2.md:138

- [x] P1-FEATURE-003: Batch Processing (2025-10-24) → ROADMAP.md:218-228

- [x] P1-FEATURE-004: Gradio UI Modernization (2025-11-01) → docs/UI_MODERNIZATION_PROPOSAL.md

- [x] P1-FEATURE-005: Campaign Lifecycle Manager (2025-11-02) → IMPLEMENTATION_PLANS_PART2.md:452

- [x] P1-MAINTENANCE-001: Session Cleanup & Validation (2025-11-01) → IMPLEMENTATION_PLANS_PART2.md:704



---



## P2 (Important Enhancements)



🟡 **Core Complete, Polish Remaining** (2/4 done)



### Completed

- [x] P2-LANGCHAIN-001: Conversational Campaign Interface (2025-10-25) → IMPLEMENTATION_PLANS_PART3.md:31

- [x] P2-LANGCHAIN-002: Semantic Search with RAG (2025-10-25) → IMPLEMENTATION_PLANS_PART3.md:286

- [x] P2.1-SECURITY: All critical security fixes (2025-10-25) → docs/LANGCHAIN_SECURITY_FIXES.md

- [x] P2.1-TESTING: LangChain test coverage expansion (2025-11-06) → ROADMAP.md:340-352

  - **Achievement**: 49% → 87% coverage (+38pp) - 70 new tests added



### Remaining

- [ ] **P2.1-UX: Campaign Chat UI Improvements** (1-2 days) → ROADMAP.md:364-370

  - Missing loading indicators during LLM calls

  - Raw exceptions shown to users

  - No conversation management (delete/rename)

  - Sources only shown for last message

  - See BUG_HUNT_TODO.md:150-198 for detailed list (12 UX bugs)



- [ ] **P2-ANALYTICS: Session Analytics & Search** (3-4 days) → ROADMAP.md:379-420

  - Session analytics dashboard

  - Character analytics & filtering

  - Session search functionality

  - Complete OOC topic analysis (in progress)



---



## P3 (Future Enhancements)



⏸️ **Deferred** - Focus on P2 polish first



- [ ] P3-FEATURE-001: Real-time Processing → IMPLEMENTATION_PLANS_PART4.md:33 (audio ingestion scaffolding exists)

- [ ] P3-FEATURE-002: Multi-language Support → IMPLEMENTATION_PLANS_PART4.md:160

- [ ] P3-FEATURE-003: Custom Speaker Labels → IMPLEMENTATION_PLANS_PART4.md:256



---



## P4 (Infrastructure & Quality)



⏸️ **Deferred** - Incremental alongside features



- [ ] P4-INFRA-001: Comprehensive Test Suite → IMPLEMENTATION_PLANS_PART4.md:270

- [ ] P4-INFRA-002: CI/CD Pipeline → IMPLEMENTATION_PLANS_PART4.md:340

- [ ] P4-INFRA-003: Performance Profiling → IMPLEMENTATION_PLANS_PART4.md:411

- [ ] P4-DOCS-001: API Documentation → IMPLEMENTATION_PLANS_PART4.md:477



---



## Bugs - LangChain Test Gaps



🔴 **58 Test Coverage Gaps** (from 2025-11-02 bug hunt)



**Source**: [BUG_HUNT_TODO.md:1-148](BUG_HUNT_TODO.md#area-1-langchain-test-coverage-p21-testing)



### High Priority Integration Tests (8 bugs)

- [ ] BUG-20251102-01: CampaignChatClient.ask - Add integration tests for full RAG pipeline → BUG_HUNT_TODO.md:9

- [ ] BUG-20251102-08: CampaignChatChain.ask - Add integration tests for full chain → BUG_HUNT_TODO.md:37

- [ ] BUG-20251102-18: HybridSearcher.search - Integration tests with real instances → BUG_HUNT_TODO.md:77

- [ ] BUG-20251102-22: CampaignRetriever.retrieve - Integration tests with real files → BUG_HUNT_TODO.md:93

- [ ] BUG-20251102-26: CampaignVectorStore.add_transcript_segments - Test with large batches → BUG_HUNT_TODO.md:109

- [ ] BUG-20251102-32: General - Add performance tests for LangChain components → BUG_HUNT_TODO.md:132

- [ ] BUG-20251102-33: General - Add concurrency tests for clients → BUG_HUNT_TODO.md:136

- [ ] BUG-20251102-35: General - Add tests for error paths and edge cases → BUG_HUNT_TODO.md:145



### Medium Priority Tests (42 bugs)

- [ ] BUG-20251102-02: CampaignChatClient.ask - Test various context inputs → BUG_HUNT_TODO.md:13

- [ ] BUG-20251102-03: CampaignChatClient.ask - Test retriever failure handling → BUG_HUNT_TODO.md:17

- [ ] BUG-20251102-04: CampaignChatClient.ask - Test LLM failure handling → BUG_HUNT_TODO.md:21

- [ ] BUG-20251102-07: _load_system_prompt - Test campaign placeholders → BUG_HUNT_TODO.md:33

- [ ] BUG-20251102-09: CampaignChatChain.ask - Test various questions/sources → BUG_HUNT_TODO.md:41

- [ ] BUG-20251102-10: CampaignChatChain.ask - Test chain failure handling → BUG_HUNT_TODO.md:45

- [ ] BUG-20251102-12: ConversationStore.add_message - Test updating relevant_sessions → BUG_HUNT_TODO.md:53

- [~] BUG-20251102-13: ConversationStore.load_conversation - Test corrupted JSON (Agent: GPT-5.1-Codex, Started: 2025-11-18 20:45 UTC) → BUG_HUNT_TODO.md:57

- [ ] BUG-20251102-14: ConversationStore.list_conversations - Test with large numbers → BUG_HUNT_TODO.md:61

- [ ] BUG-20251102-15: ConversationStore.list_conversations - Test corrupted files → BUG_HUNT_TODO.md:65

- [ ] BUG-20251102-19: HybridSearcher.search - Test varying top_k/semantic_weight → BUG_HUNT_TODO.md:81

- [ ] BUG-20251102-20: HybridSearcher.search - Test when one search method fails → BUG_HUNT_TODO.md:85

- [ ] BUG-20251102-21: HybridSearcher._reciprocal_rank_fusion - Test complex scenarios → BUG_HUNT_TODO.md:89

- [ ] BUG-20251102-23: CampaignRetriever._search_knowledge_bases - Test various query types → BUG_HUNT_TODO.md:97

- [ ] BUG-20251102-24: CampaignRetriever._search_transcripts - Test matching scenarios → BUG_HUNT_TODO.md:101

- [ ] BUG-20251102-25: CampaignRetriever._load_knowledge_base - Test cache eviction → BUG_HUNT_TODO.md:105

- [ ] BUG-20251102-27: CampaignVectorStore.add_knowledge_documents - Test various structures → BUG_HUNT_TODO.md:113

- [ ] BUG-20251102-28: CampaignVectorStore.search - Test collection parameter → BUG_HUNT_TODO.md:117

- [ ] BUG-20251102-30: CampaignVectorStore.clear_all - Test destructive operation → BUG_HUNT_TODO.md:125

- [ ] BUG-20251102-34: General - Improve test data complexity → BUG_HUNT_TODO.md:141

- [ ] BUG-20251102-48: Character Profile Extraction - Test unusual names/dialogue → BUG_HUNT_TODO.md:200

- [ ] BUG-20251102-49: Character Profile Extraction - Test long transcripts (HIGH) → BUG_HUNT_TODO.md:204

- [ ] BUG-20251102-50: Character Profile Extraction - Verify save/load → BUG_HUNT_TODO.md:208

- [ ] BUG-20251102-51: UI Modernization - Test responsiveness on different screens → BUG_HUNT_TODO.md:212

- [ ] BUG-20251102-52: UI Modernization - Verify progressive disclosure → BUG_HUNT_TODO.md:217

- [ ] BUG-20251102-53: UI Modernization - Check for broken links/elements → BUG_HUNT_TODO.md:221

- [ ] BUG-20251102-54: Campaign Lifecycle Manager - Test creation/loading/switching (HIGH) → BUG_HUNT_TODO.md:225

- [ ] BUG-20251102-55: Campaign Lifecycle Manager - Verify campaign-aware UI → BUG_HUNT_TODO.md:229

- [ ] BUG-20251102-56: Campaign Lifecycle Manager - Test migration edge cases → BUG_HUNT_TODO.md:233

- [ ] BUG-20251102-57: General P1 - Check for performance regressions (HIGH) → BUG_HUNT_TODO.md:237

- [ ] BUG-20251102-58: General P1 - Review logs for unexpected errors → BUG_HUNT_TODO.md:241



### Low Priority Tests (8 bugs)

- [ ] BUG-20251102-05: _initialize_llm - Test Ollama fallback → BUG_HUNT_TODO.md:25

- [ ] BUG-20251102-06: _initialize_memory - Test ConversationBufferMemory fallbacks → BUG_HUNT_TODO.md:29

- [ ] BUG-20251102-11: ConversationStore.add_message - Test with/without sources → BUG_HUNT_TODO.md:49

- [ ] BUG-20251102-16: ConversationStore.delete_conversation - Test non-existent → BUG_HUNT_TODO.md:69

- [ ] BUG-20251102-17: ConversationStore.get_chat_history - Test empty conversation → BUG_HUNT_TODO.md:73

- [ ] BUG-20251102-29: CampaignVectorStore.delete_session - Test session with no segments → BUG_HUNT_TODO.md:121

- [ ] BUG-20251102-31: CampaignVectorStore.get_stats - Test empty/populated collections → BUG_HUNT_TODO.md:129



---



## Bugs - UI Dashboard Issues



🔴 **30 UI Issues** (from 2025-11-03 bug hunt)



**Source**: [BUG_HUNT_TODO.md:253-446](BUG_HUNT_TODO.md#area-4-ui-dashboard-issues-2025-11-03) | **Quick Ref**: [BUG_SUMMARY.md](BUG_SUMMARY.md)

---

### 🤝 Multi-Session Coordination Guide

**For parallel work on same branch:**

1. **Pull latest** before choosing a task: `git pull origin <branch>`
2. **Check locked tasks** in this file (look for `[~]` status)
3. **Pick non-conflicting work** using conflict risk ratings:
   - ⚠️ LOW: Safe to work on anytime (isolated files)
   - ⚠️⚠️ MEDIUM: Check if another agent is working on same module
   - ⚠️⚠️⚠️ HIGH: Coordinate explicitly before starting
4. **Lock immediately** before starting work:
   ```markdown
   [~] BUG-ID: Description (Agent: YourName, Started: YYYY-MM-DD HH:MM UTC, Files: list) → source
   ```
5. **Commit & push lock** right away: `git add docs/OUTSTANDING_TASKS.md && git commit -m "Lock task: BUG-ID" && git push`
6. **Do the work**
7. **Update to complete** when done:
   ```markdown
   [x] BUG-ID: Description (Agent: YourName, Completed: YYYY-MM-DD) → source
   ```

**Conflict-free task selection examples:**
- Session 1: BUG-019 (live_session_tab.py) + Session 2: BUG-017 (campaign_dashboard.py) ✅ No conflict
- Session 1: BUG-008 (app.py:509-601) + Session 2: BUG-009 (app.py:499-507) ⚠️ Same file, adjacent lines - HIGH risk
- Session 1: BUG-007 (process_session_tab_modern.py) + Session 2: BUG-021 (social_insights_tab.py) ✅ No conflict

### High Priority (6 bugs)

- [x] BUG-20251103-006: Process Session - No client-side validation (Agent: Codex, Completed: 2025-11-06) → BUG_HUNT_TODO.md:283 | src/ui/process_session_tab_modern.py:228-475

- [ ] BUG-20251103-008: Process Session - No progress indicator during processing → BUG_HUNT_TODO.md:295 | app.py:509-601

- [x] BUG-20251103-019: Live Session - Non-functional placeholder tab (Agent: Claude, Completed: 2025-11-06) → BUG_HUNT_TODO.md:378 | src/ui/live_session_tab.py:92-163

- [x] BUG-20251103-022: Social Insights - WordCloud dependency not handled gracefully (Agent: Gemini, Completed: 2025-11-06) → BUG_HUNT_TODO.md:387 | src/ui/social_insights_tab.py:20

- [ ] BUG-20251103-027: Global - No conflict detection for concurrent operations → BUG_HUNT_TODO.md:421 | Multiple files



### Medium Priority (13 bugs)

- [x] BUG-20251103-002: Main Dashboard - Campaign state not persisted across refreshes (Agent: Codex GPT-5, Completed: 2025-11-19) → BUG_HUNT_TODO.md:257 | app.py:623
---



### High Priority (6 bugs)

#### Completed
- [x] BUG-20251103-006: Process Session - No client-side validation (Agent: Codex, Completed: 2025-11-06) → BUG_HUNT_TODO.md:283 | src/ui/process_session_tab_modern.py:228-475

- [x] BUG-20251103-022: Social Insights - WordCloud dependency not handled gracefully (Agent: Gemini, Completed: 2025-11-06) → BUG_HUNT_TODO.md:387 | src/ui/social_insights_tab.py:20

- [x] BUG-20251103-017: Campaign Dashboard - Sessions not filtered by campaign (Agent: Claude, Completed: 2025-11-06) → BUG_HUNT_TODO.md:353 | src/campaign_dashboard.py:119-136

#### Available - Core Logic (Medium Conflict Risk)
- [x] **BUG-20251103-008**: Process Session - No progress indicator during processing (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `app.py:916-1005` (added progress parameter and callback), `src/pipeline.py:1535-2181` (added progress_callback with 9 stage reports)
  - **Effort**: 2-4 hours (actual: ~2 hours)
  - **Conflict Risk**: ⚠️⚠️ MEDIUM (touches app.py core processing logic)
  - **Fix**: Added progress_callback to pipeline, integrated with Gradio Progress tracker, reports after each of 9 stages
  → BUG_HUNT_TODO.md:295

#### Available - Cross-Cutting (High Conflict Risk)
- [ ] **BUG-20251103-027**: Global - No conflict detection for concurrent operations
  - **Files**: Multiple (`app.py`, `campaign_dashboard.py`, all tab files, potentially new lock manager module)
  - **Effort**: 4-6 hours
  - **Conflict Risk**: ⚠️⚠️⚠️ HIGH (touches many files, architectural change)
  - **Fix**: Implement operation locking/coordination mechanism
  → BUG_HUNT_TODO.md:421



### Medium Priority (13 bugs)

#### Isolated UI Files (Low Conflict Risk)
- [x] **BUG-20251103-007**: Process Session - Results section doesn't auto-scroll (Agent: Claude, Completed: 2025-11-18)
  - **Files**: `src/ui/process_session_helpers.py:263-290`
  - **Effort**: 30 min (actual: 20 min) | **Conflict Risk**: ⚠️ LOW
  - **Fix**: Improved JavaScript auto-scroll with retry logic, increased timeout from 100ms to 300ms, added visibility checks
  → BUG_HUNT_TODO.md:289

- [x] **BUG-20251103-011**: Campaign Tab - Static content, no interactive features (Agent: Already Fixed, Completed: 2025-11-14 - commit bab3f2e)
  - **Files**: `src/ui/campaign_tab_modern.py:9-46`, `app.py:1546-1800`
  - **Effort**: 2-3 hours (actual: completed by Task12 PR #42)  | **Conflict Risk**: ⚠️ LOW
  - **Fix**: Added _refresh_campaign_tab, _handle_rename_campaign, _handle_delete_campaign functions with full event wiring
  → BUG_HUNT_TODO.md:315

- [x] **BUG-20251103-021**: Social Insights - No loading indicator during analysis (Agent: Already Fixed, Completed: 2025-11-14 - commit a2d6b42)
  - **Files**: `src/ui/social_insights_tab.py:34-243`
  - **Effort**: 1 hour (actual: completed by Task10 PR #40) | **Conflict Risk**: ⚠️ LOW
  - **Fix**: Added generator-based progress yielding with StatusMessages at 5 stages of analysis
  → BUG_HUNT_TODO.md:381

- [x] **BUG-20251103-025**: Settings & Tools - Static markdown only, no interactive controls (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `src/ui/settings_tools_tab_modern.py:40-87`, `src/ui/diagnostics_helpers.py`, `app.py:55-60,1721-1741`
  - **Effort**: 1 hour (actual) | **Conflict Risk**: ⚠️ LOW
  - **Fix**: Added interactive System Diagnostics (health check, export) and Conversation Management (list, clear all) sections with full UI integration
  → BUG_HUNT_TODO.md:407

#### Campaign Dashboard Module (Medium Conflict Risk)
- [x] **BUG-20251103-017**: Campaign Dashboard - Sessions not filtered by campaign (Agent: Claude, Completed: 2025-11-06)
  - **Files**: `src/campaign_dashboard.py:119-166`
  - **Effort**: 1-2 hours | **Conflict Risk**: ⚠️⚠️ MEDIUM
  → BUG_HUNT_TODO.md:353

- [x] **BUG-20251103-018**: Campaign Dashboard - Narratives include other campaigns (Agent: Claude, Completed: 2025-11-18 - Already fixed in commit 575b9a6)
  - **Files**: `src/campaign_dashboard.py:146-148`
  - **Effort**: 30-60 min | **Conflict Risk**: ⚠️⚠️ MEDIUM
  → BUG_HUNT_TODO.md:359

#### App.py Core Logic (Medium-High Conflict Risk)
- [ ] **BUG-20251103-002**: Main Dashboard - Campaign state not persisted across refreshes
  - **Files**: `app.py:623` (State initialization)
  - **Effort**: 1-2 hours | **Conflict Risk**: ⚠️⚠️ MEDIUM
  → BUG_HUNT_TODO.md:257

- [ ] **BUG-20251103-004**: Campaign Launcher - Dropdown not refreshed on external changes
  - **Files**: `app.py:630-635`
  - **Effort**: 1 hour | **Conflict Risk**: ⚠️⚠️ MEDIUM
  → BUG_HUNT_TODO.md:269

- [x] **BUG-20251103-009**: Process Session - Audio path resolution inconsistent (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `app.py:757-806`
  - **Effort**: 45 min (actual) | **Conflict Risk**: ⚠️⚠️ MEDIUM
  - **Fix**: Enhanced _resolve_audio_path to handle str, Path, dict, list, file-like objects with existence validation. Changed return type from str to Path to match pipeline.process() signature.
  → BUG_HUNT_TODO.md:301

- [ ] **BUG-20251103-013**: Campaign Dashboard - No error recovery for corrupted files
  - **Files**: `app.py:300-335`
  - **Effort**: 1-2 hours | **Conflict Risk**: ⚠️⚠️ MEDIUM
  → BUG_HUNT_TODO.md:327

- [ ] **BUG-20251103-026**: Global - Campaign context update triggers excessive re-renders
  - **Files**: `app.py:681-778` (_compute_process_updates, _load_campaign)
  - **Effort**: 3-4 hours | **Conflict Risk**: ⚠️⚠️⚠️ HIGH
  → BUG_HUNT_TODO.md:415

- [ ] **BUG-20251103-029**: Data - Session library doesn't verify campaign_id before display
  - **Files**: `app.py:397-426`
  - **Effort**: 1 hour | **Conflict Risk**: ⚠️⚠️ MEDIUM
  → BUG_HUNT_TODO.md:435

#### Cross-Cutting (High Conflict Risk)
- [ ] **BUG-20251103-028**: Global - Error messages expose internal file paths/stack traces
  - **Files**: Multiple files (error handling across app)
  - **Effort**: 2-3 hours | **Conflict Risk**: ⚠️⚠️⚠️ HIGH
  → BUG_HUNT_TODO.md:427



### Low Priority (8 bugs)

#### Quick Fixes (Isolated, Low Conflict)
- [x] **BUG-20251103-020**: Live Session - Stop button enabled before Start (Agent: Claude Sonnet 4.5, Completed: 2025-11-18 - Already fixed in commit 8d637f9)
  - **Files**: `src/ui/live_session_tab.py:121,127`
  - **Effort**: 15 min (verification only) | **Conflict Risk**: ⚠️ LOW
  - **Fix**: Both buttons now have `.interactive = False` set explicitly. Feature marked as "Coming Soon" with disabled UI.
  → BUG_HUNT_TODO.md:373

- [x] **BUG-20251103-023**: Social Insights - Temp file cleanup not guaranteed (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `src/ui/social_insights_tab.py:60-72`
  - **Effort**: 20 min (actual: 15 min) | **Conflict Risk**: ⚠️ LOW
  - **Fix**: Added cleanup logic at start of analyze_ooc_ui() to remove old *_nebula.png files from temp/ directory. Uses glob pattern matching with graceful error handling.
  → BUG_HUNT_TODO.md:393

- [x] **BUG-20251103-024**: Social Insights - Stale nebula after campaign filter change (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `src/ui/social_insights_tab.py:257-286, 375-386`
  - **Effort**: 30 min (actual: 20 min) | **Conflict Risk**: ⚠️ LOW
  - **Fix**: Modified refresh_sessions_ui to return 6 outputs (session dropdown + 5 cleared result components), added StatusMessages feedback when campaign changes
  → BUG_HUNT_TODO.md:410

#### Campaign Dashboard Polish
- [x] **BUG-20251103-014**: Campaign Dashboard - Personality text truncated mid-word (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `src/campaign_dashboard.py:101-112`
  - **Effort**: 20 min (actual: 15 min) | **Conflict Risk**: ⚠️⚠️ MEDIUM
  - **Fix**: Added word-boundary-aware truncation using rfind() to avoid mid-word cuts
  → BUG_HUNT_TODO.md:335

- [x] **BUG-20251103-015**: Campaign Dashboard - Health percentage edge case (Agent: Jules, Completed: 2025-11-18)
  - **Files**: `src/campaign_dashboard.py:196`
  - **Effort**: 15 min | **Conflict Risk**: ⚠️⚠️ MEDIUM
  → BUG_HUNT_TODO.md:341

- [x] **BUG-20251103-016**: Campaign Dashboard - Managers instantiated multiple times (Agent: Claude Sonnet 4.5, Completed: 2025-11-19)
  - **Files**: `src/campaign_dashboard.py:10-53`
  - **Effort**: 30 min (actual) | **Conflict Risk**: ⚠️⚠️ MEDIUM
  - **Fix**: Implemented lazy-loading singleton pattern for CampaignManager, PartyConfigManager, and CharacterProfileManager. Added _get_*_manager() functions to create instances once and reuse across all dashboard generations. Reduces JSON file I/O by ~3x during dashboard refreshes.
  → BUG_HUNT_TODO.md:347

#### App.py Edge Cases
- [x] **BUG-20251103-003**: Campaign Launcher - No validation for empty/whitespace names (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `app.py:1483-1520`
  - **Effort**: 30 min (actual: 25 min) | **Conflict Risk**: ⚠️⚠️ MEDIUM
  - **Fix**: Added validation in _create_new_campaign() to reject empty/whitespace-only names. Shows error message with guidance, keeps UI in current state. Matches validation pattern from _handle_rename_campaign().
  → BUG_HUNT_TODO.md:263

- [x] **BUG-20251103-010**: Process Session - Name parsing doesn't handle edge cases (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `app.py:860-880`
  - **Effort**: 30 min (actual: 20 min) | **Conflict Risk**: ⚠️⚠️ MEDIUM
  - **Fix**: Added duplicate removal with order preservation, comma validation warning
  → BUG_HUNT_TODO.md:307

- [x] **BUG-20251103-012**: Campaign Dashboard - Knowledge base sample truncated without indication (Agent: Claude Sonnet 4.5, Completed: 2025-11-18)
  - **Files**: `app.py:578-596`
  - **Effort**: 30 min (actual: 20 min) | **Conflict Risk**: ⚠️⚠️ MEDIUM
  - **Fix**: Added _format_sample helper to show count indicators (e.g., "showing 3 of 47")
  → BUG_HUNT_TODO.md:321

#### Cross-Cutting (Defer)
- [ ] **BUG-20251103-005**: Campaign Manifest - Exception handling too broad
  - **Files**: `app.py:Multiple` locations
  - **Effort**: 2-3 hours | **Conflict Risk**: ⚠️⚠️⚠️ HIGH
  → BUG_HUNT_TODO.md:275

- [ ] **BUG-20251103-030**: Data - Profile filtering logic flaw with None handling
  - **Files**: Multiple files
  - **Effort**: 1-2 hours | **Conflict Risk**: ⚠️⚠️ MEDIUM
  → BUG_HUNT_TODO.md:441



---

## Bugs - Analytics Module

🔍 **Session Analyzer Issues** (newly logged 2025-11-19)

- [x] BUG-20251119-101: SessionAnalyzer compare_sessions returned no insights when only one session was provided, leaving the Analytics tab without guidance and failing `tests/test_analytics_session_analyzer.py::test_compare_sessions_single`. Added a single-session summary insight plus a top-speaker highlight so comparisons always emit actionable text. → src/analytics/session_analyzer.py:452-476 | tests/test_analytics_session_analyzer.py:224-233

- [ ] BUG-20251119-102: SessionAnalyzer.calculate_character_stats relies on a non-existent `duration` field in transcript segments, so any caller receives zero speaking durations even though `start_time`/`end_time` are provided. Update the helper to compute duration from timestamps and add regression tests. → src/analytics/session_analyzer.py:373-394



---



## Resolved Bugs



### 2025-11-02

- [x] BUG-20251102-111: Gradio NamedString coercion in audio_processor.py → BUG_HUNT_TODO.md:247



### 2025-11-03

- [x] BUG-20251103-001: Stage 2 NameError in HybridChunker progress callback → BUG_HUNT_TODO.md:251



---



## Recommended Work Order



### Week 1: Critical UX Quick Wins

1. BUG-20251103-006 - Add client-side validation to Process Session

2. BUG-20251103-019 - Hide/disable Live Session tab (mark "Coming Soon")

3. BUG-20251103-022 - Better WordCloud dependency error handling



### Week 2: Data Integrity & Core Functionality

4. BUG-20251103-027 - Add concurrent operation locking/coordination

5. BUG-20251103-017 - Fix campaign filtering in dashboard sessions

6. BUG-20251103-018 - Fix campaign filtering in dashboard narratives

7. BUG-20251103-008 - Implement progress indicators for long operations



### Week 3: UX Polish

8. P2.1-UX Campaign Chat improvements (12 UX bugs from BUG_HUNT_TODO.md:150-198)

9. BUG-20251103-007 - Auto-scroll to results

10. BUG-20251103-021 - Add loading indicators to Social Insights



### Month 2: Testing & Analytics

11. High-priority LangChain integration tests (8 bugs: BUG-20251102-01, 08, 18, 22, 26, 32, 33, 35)

12. P2-ANALYTICS features (session analytics, search, character filtering)

13. Medium-priority UI fixes (remaining 13 medium bugs)



### Month 3+: Remaining Quality & P3/P4

14. Medium/Low priority LangChain tests (50 remaining test gaps)

15. Low priority UI bugs (11 bugs)

16. P3 features (if business priority shifts)

17. P4 infrastructure (CI/CD, profiling, API docs)



---



## Notes



- **Testing Strategy**: LangChain coverage improved from 49% → 87% (2025-11-06), but 58 test gaps remain for edge cases, integration scenarios, and performance benchmarks

- **UI State**: Modern UI launched 2025-11-01, but 30 bugs discovered in functionality, data filtering, and error handling

- **P2.1 Polish**: Core LangChain features work, but UX needs refinement (loading indicators, error messages, conversation management)

- **Campaign Isolation**: Multiple bugs (BUG-20251103-017, 018, 029) indicate campaign filtering not consistently applied across dashboard components



---



**For detailed context, see**:

- [ROADMAP.md](../ROADMAP.md) - Full feature roadmap with status

- [BUG_HUNT_TODO.md](BUG_HUNT_TODO.md) - Detailed bug descriptions with reproduction steps

- [BUG_SUMMARY.md](BUG_SUMMARY.md) - Quick reference for UI bugs

- [IMPLEMENTATION_PLANS_SUMMARY.md](../IMPLEMENTATION_PLANS_SUMMARY.md) - Sprint planning & effort estimates

