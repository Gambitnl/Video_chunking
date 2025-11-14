# Master Plan

> **Last Updated**: 2025-11-11
> **Purpose**: Single source of truth for all open work items, sprint planning, and project status. This document supersedes `docs/OUTSTANDING_TASKS.md`, `docs/BUG_HUNT_TODO.md`, and `docs/BUG_SUMMARY.md`.

---

## Sprint Goals (Week of 2025-11-11)

### Primary Objective: Stabilize and Polish the User Experience

1.  **Address Critical UI Bugs**: Resolve the most impactful UI issues to improve usability and stability.
2.  **Enhance the LangChain Experience**: Implement key UX improvements for the Campaign Chat feature.
3.  **Improve Test Coverage**: Begin to address the most critical gaps in the LangChain test suite.

---

## Active Sprint Board

### To Do

-   [ ] **BUG-20251103-027**: Global - No conflict detection for concurrent operations
-   [ ] **BUG-20251103-018**: Campaign Dashboard - Narratives include other campaigns
-   [ ] **P2.1-UX: Campaign Chat UI Improvements** (1-2 days)
-   [ ] **BUG-20251102-01**: CampaignChatClient.ask - Add integration tests for full RAG pipeline

### In Progress

-   `[~]` **BUG-20251102-32**: General - Add performance tests for LangChain components (In Progress)

### Done

-   [x] **BUG-20251103-006**: Process Session - No client-side validation
-   [x] **BUG-20251103-019**: Live Session - Non-functional placeholder tab
-   [x] **BUG-20251103-022**: Social Insights - WordCloud dependency not handled gracefully
-   [x] **BUG-20251103-017**: Campaign Dashboard - Sessions not filtered by campaign
-   [x] **BUG-20251103-008**: Process Session - Real-time progress indicator (Completed 2025-11-14)
-   [x] **BUG-20251103-021**: Social Insights - Loading indicators during analysis (Completed 2025-11-14)
-   [x] **BUG-20251103-011**: Campaign Tab - Interactive features with live switching (Completed 2025-11-14)
-   [x] **BUG-20251103-025**: Settings & Tools - Interactive configuration editing (Completed 2025-11-14)
-   [x] **BUG-20251102-18**: HybridSearcher - Integration tests with real instances (Completed 2025-11-14)
-   [x] **BUG-20251102-22**: CampaignRetriever - Integration tests with real files (Completed 2025-11-14)

---

## Backlog

### High Priority

-   [ ] **P2-ANALYTICS: Session Analytics & Search** (3-4 days)
-   [ ] **BUG-20251102-08**: CampaignChatChain.ask - Add integration tests for full chain
-   [ ] **BUG-20251102-26**: CampaignVectorStore.add_transcript_segments - Test with large batches
-   [ ] **BUG-20251102-33**: General - Add concurrency tests for clients
-   [ ] **BUG-20251102-35**: General - Add tests for error paths and edge cases

### Medium Priority

-   [ ] **P4-INFRA-001**: Comprehensive Test Suite (3-5 days)
-   [ ] **BUG-20251103-002**: Main Dashboard - Campaign state not persisted across refreshes
-   [ ] **BUG-20251103-004**: Campaign Launcher - Dropdown not refreshed on external changes
-   [ ] **BUG-20251103-007**: Process Session - Results section doesn't auto-scroll
-   [ ] **BUG-20251103-009**: Process Session - Audio path resolution inconsistent
-   [ ] **BUG-20251103-013**: Campaign Dashboard - No error recovery for corrupted files
-   [x] **BUG-20251103-021**: Social Insights - No loading indicator during analysis
-   [ ] **BUG-20251103-025**: Settings & Tools - Static markdown only, no interactive controls
-   [ ] **BUG-20251103-026**: Global - Campaign context update triggers excessive re-renders
-   [ ] **BUG-20251103-028**: Global - Error messages expose internal file paths/stack traces
-   [ ] **BUG-20251103-029**: Data - Session library doesn't verify campaign_id before display
-   [ ] All remaining Medium Priority LangChain Test Gaps (42 bugs)

### Low Priority

-   [ ] **P3-FEATURE-001**: Real-time Processing (5-7 days)
-   [ ] **P3-FEATURE-002**: Multi-language Support (2-3 days)
-   [ ] **P3-FEATURE-003**: Custom Speaker Labels (2 days)
-   [ ] **P4-INFRA-002**: CI/CD Pipeline (2-3 days)
-   [ ] **P4-INFRA-003**: Performance Profiling (2 days)
-   [ ] **P4-DOCS-001**: API Documentation (2-3 days)
-   [ ] All remaining Low Priority UI Bugs (11 bugs)
-   [ ] All remaining Low Priority LangChain Test Gaps (8 bugs)

---

## Completed Work

### Recent Concurrent Development Sprint (2025-11-14)

**Orchestration Summary**: 15 independent tasks executed concurrently across 3 batches with zero merge conflicts.

**Batch 1 - Refactoring & Core Infrastructure (6 tasks):**
- ✅ Consolidated TranscriptFormatter duplicate methods (Refactor #5)
- ✅ Extracted SpeakerDiarizer complex methods (Refactor #6)
- ✅ Created CampaignArtifactCounter module (Refactor #8)
- ✅ Implemented OpenAI Whisper transcriber backend
- ✅ Completed HybridChunker test suite (16 tests, P0-2)
- ✅ Added HybridSearcher integration tests (14 tests)

**Batch 2 - Testing & UI Enhancements (6 tasks):**
- ✅ Added CampaignRetriever integration tests (20 tests)
- ✅ Added SemanticRetriever integration tests (9 tests)
- ✅ Implemented real-time progress indicator (Process Session tab)
- ✅ Added loading indicators (Social Insights tab)
- ✅ Created OllamaClientFactory (Refactor #9, 27 tests)
- ✅ Converted Campaign Tab to interactive UI

**Batch 3 - Configuration & Test Coverage (3 tasks):**
- ✅ Implemented interactive Settings & Tools configuration editor
- ✅ Created story_generator.py test suite (39 tests)
- ✅ Created party_config.py test suite (74 tests, 99% coverage)

**Key Metrics:**
- 15 feature branches completed
- 220+ tests added
- ~5,000 lines of production code
- 99% coverage achieved for party_config.py
- Zero file conflicts maintained across all parallel work

For detailed history, see `git log` and `docs/archive` directory.
