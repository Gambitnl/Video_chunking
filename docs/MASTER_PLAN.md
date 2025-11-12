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
-   [ ] **BUG-20251103-008**: Process Session - No progress indicator during processing
-   [ ] **P2.1-UX: Campaign Chat UI Improvements** (1-2 days)
-   [ ] **BUG-20251102-01**: CampaignChatClient.ask - Add integration tests for full RAG pipeline

### In Progress

-   `[~]` **Consolidate planning documents into this MASTER_PLAN.md** (Agent: Jules, Started: 2025-11-11 13:18 UTC)

### Done

-   [x] **BUG-20251103-006**: Process Session - No client-side validation
-   [x] **BUG-20251103-019**: Live Session - Non-functional placeholder tab
-   [x] **BUG-20251103-022**: Social Insights - WordCloud dependency not handled gracefully
-   [x] **BUG-20251103-017**: Campaign Dashboard - Sessions not filtered by campaign

---

## Backlog

### High Priority

-   [ ] **P2-ANALYTICS: Session Analytics & Search** (3-4 days)
-   [ ] **BUG-20251102-08**: CampaignChatChain.ask - Add integration tests for full chain
-   [ ] **BUG-20251102-18**: HybridSearcher.search - Integration tests with real instances
-   [ ] **BUG-20251102-22**: CampaignRetriever.retrieve - Integration tests with real files
-   [ ] **BUG-20251102-26**: CampaignVectorStore.add_transcript_segments - Test with large batches
-   [ ] **BUG-20251102-32**: General - Add performance tests for LangChain components
-   [ ] **BUG-20251102-33**: General - Add concurrency tests for clients
-   [ ] **BUG-20251102-35**: General - Add tests for error paths and edge cases

### Medium Priority

-   [ ] **P4-INFRA-001**: Comprehensive Test Suite (3-5 days)
-   [ ] **BUG-20251103-002**: Main Dashboard - Campaign state not persisted across refreshes
-   [ ] **BUG-20251103-004**: Campaign Launcher - Dropdown not refreshed on external changes
-   [ ] **BUG-20251103-007**: Process Session - Results section doesn't auto-scroll
-   [ ] **BUG-20251103-009**: Process Session - Audio path resolution inconsistent
-   [ ] **BUG-20251103-011**: Campaign Tab - Static content, no interactive features
-   [ ] **BUG-20251103-013**: Campaign Dashboard - No error recovery for corrupted files
-   [ ] **BUG-20251103-021**: Social Insights - No loading indicator during analysis
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

For a detailed history of completed work, please refer to the `git log` and the `docs/archive` directory, which contains the now-superseded planning documents.
