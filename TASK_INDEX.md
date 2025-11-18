# Task Index - Markdown Files with Unresolved Tasks

> **Generated**: 2025-11-18
> **Purpose**: Quick reference for AI agents to find available work items
> **See also**: [CLAUDE.md](CLAUDE.md#available-tasks--work-items) for detailed descriptions

---

## Task Count Summary

**Total Files with Tasks:** 40+
**Total Active Tasks:** 1000+ (approximate)

---

## High-Priority Files (Start Here)

### Core Planning
| File | Tasks | Priority | Description |
|------|-------|----------|-------------|
| [ROADMAP.md](ROADMAP.md) | 11 | **P0-P4** | Main project roadmap |
| [docs/archive/OUTSTANDING_TASKS.md](docs/archive/OUTSTANDING_TASKS.md) | 83 | **P0-P4** | Comprehensive task backlog |

### Active Implementation Plans (P1-P2)
| File | Tasks | Priority | Description |
|------|-------|----------|-------------|
| [IMPLEMENTATION_PLAN_SESSION_ANALYTICS.md](IMPLEMENTATION_PLAN_SESSION_ANALYTICS.md) | 93 | **P2** | Session analytics dashboard |
| [IMPLEMENTATION_PLANS_INTERACTIVE_CLARIFICATION.md](IMPLEMENTATION_PLANS_INTERACTIVE_CLARIFICATION.md) | 48 | **P2** | Interactive clarification system |
| [IMPLEMENTATION_PLAN_LANGCHAIN_UX_POLISH.md](IMPLEMENTATION_PLAN_LANGCHAIN_UX_POLISH.md) | 36 | **P2** | Campaign Chat UX improvements |
| [IMPLEMENTATION_PLAN_SESSION_SEARCH.md](IMPLEMENTATION_PLAN_SESSION_SEARCH.md) | 30 | **P2** | Full-text search feature |
| [IMPLEMENTATION_PLAN_CHARACTER_ANALYTICS.md](IMPLEMENTATION_PLAN_CHARACTER_ANALYTICS.md) | 24 | **P2** | Character analytics & filtering |
| [IMPLEMENTATION_PLAN_OOC_TOPIC_ANALYSIS.md](IMPLEMENTATION_PLAN_OOC_TOPIC_ANALYSIS.md) | 17 | **P2** | OOC topic analysis |
| [IMPLEMENTATION_PLANS.md](IMPLEMENTATION_PLANS.md) | 15 | **P0-P1** | Core checkpoint/resume features |

### Workflow & Process
| File | Tasks | Priority | Description |
|------|-------|----------|-------------|
| [WORK_INITIATION_PROMPT.md](WORK_INITIATION_PROMPT.md) | 82 | - | Operator workflow guide |
| [CLAUDE.md](CLAUDE.md) | 12 | - | AI assistant guide |
| [AGENT_ONBOARDING.md](AGENT_ONBOARDING.md) | 11 | - | Agent onboarding path |

---

## Feature-Specific Plans

### UI/UX Improvements
| File | Tasks | Description |
|------|-------|-------------|
| [docs/UI_UX_IMPROVEMENT_PLAN.md](docs/UI_UX_IMPROVEMENT_PLAN.md) | 24 | Detailed UI/UX plan |
| [UX_QUICK_REFERENCE.md](UX_QUICK_REFERENCE.md) | 15 | UX best practices |
| [UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md) | 8 | UI enhancement proposals |
| [docs/UI_UX_NEXT_SESSION_GUIDE.md](docs/UI_UX_NEXT_SESSION_GUIDE.md) | 8 | Next session work items |
| [UX_IMPROVEMENTS.md](UX_IMPROVEMENTS.md) | 6 | UX improvement proposals |

### Campaign Management
| File | Tasks | Description |
|------|-------|-------------|
| [docs/CAMPAIGN_LIFECYCLE_IMPLEMENTATION.md](docs/CAMPAIGN_LIFECYCLE_IMPLEMENTATION.md) | 18 | Campaign lifecycle features |
| [docs/CLM-05_TAB_FILTERING_IMPLEMENTATION.md](docs/CLM-05_TAB_FILTERING_IMPLEMENTATION.md) | 13 | Tab filtering implementation |
| [docs/CAMPAIGN_MIGRATION_GUIDE.md](docs/CAMPAIGN_MIGRATION_GUIDE.md) | 11 | Data migration procedures |

### LangChain Integration
| File | Tasks | Description |
|------|-------|-------------|
| [docs/LANGCHAIN_FEATURES.md](docs/LANGCHAIN_FEATURES.md) | 6 | LangChain features & improvements |

---

## Implementation Guidance

### Documentation & Reviews
| File | Tasks | Description |
|------|-------|-------------|
| [docs/IMPLEMENTATION_REVIEW_IMPROVEMENTS.md](docs/IMPLEMENTATION_REVIEW_IMPROVEMENTS.md) | 13 | Review process improvements |
| [docs/CRITICAL_REVIEW_WORKFLOW.md](docs/CRITICAL_REVIEW_WORKFLOW.md) | 5 | Critical review methodology |

### Testing
| File | Tasks | Description |
|------|-------|-------------|
| [tests/ui/MANUAL_TESTING_CHECKLIST.md](tests/ui/MANUAL_TESTING_CHECKLIST.md) | 339 | Comprehensive UI testing checklist |
| [docs/TEST_PLANS.md](docs/TEST_PLANS.md) | 6 | Testing strategy & coverage goals |

---

## Infrastructure & Setup

### Configuration & Setup
| File | Tasks | Description |
|------|-------|-------------|
| [CLOUD_INFERENCE_OPTIONS.md](CLOUD_INFERENCE_OPTIONS.md) | 5 | Cloud backend options |
| [COLAB_SETUP.md](COLAB_SETUP.md) | 4 | Google Colab setup |

### Historical/Archive (Lower Priority)
| File | Tasks | Description |
|------|-------|-------------|
| [docs/DIARIZATION_CLASSIFICATION_HISTORY.md](docs/DIARIZATION_CLASSIFICATION_HISTORY.md) | 9 | Historical analysis |
| [docs/CLAUDE_SONNET_45_ANALYSIS.md](docs/CLAUDE_SONNET_45_ANALYSIS.md) | 8 | Historical review |
| [docs/archive/* (various)](docs/archive/) | 100+ | Archived plans & tasks |

---

## Recently Completed Plans

### Completed Implementation Plans (Reference Only)
- **[IMPLEMENTATION_PLAN_STREAMING_SNIPPET_EXPORT.md](IMPLEMENTATION_PLAN_STREAMING_SNIPPET_EXPORT.md)** (10 tasks) - **[DONE] 2025-11-18**
  - P1 feature: FFmpeg streaming export (90% memory reduction)
  - All phases complete, pushed to branch

---

## Quick Start Guide

### If You're Looking for Work:

1. **Check Priority:**
   ```
   P0 (Critical) > P1 (High) > P2 (Important) > P3 (Future) > P4 (Infrastructure)
   ```

2. **Start Here:**
   - Read [ROADMAP.md](ROADMAP.md) for current priorities
   - Check [docs/archive/OUTSTANDING_TASKS.md](docs/archive/OUTSTANDING_TASKS.md) for available tasks
   - Pick a task aligned with your expertise

3. **Before Starting:**
   - Lock task in OUTSTANDING_TASKS.md with `[~]` marker
   - Read the relevant IMPLEMENTATION_PLAN_*.md file
   - Follow the Operator Workflow in [CLAUDE.md](CLAUDE.md)

4. **During Work:**
   - Update task status as you progress
   - Document implementation notes
   - Run tests continuously

5. **After Completion:**
   - Mark tasks as `[x]` or `[DONE]`
   - Update ROADMAP.md
   - Request critical review
   - Push to designated branch

---

## Task Status Legend

- `[ ]` - Unresolved/Pending
- `[~]` - In Progress (locked by agent)
- `[x]` - Completed
- `[DONE]` - Completed (verbose form)
- `[PENDING]` - Pending/Blocked
- `[TODO]` - To Do (explicit marker)

---

## Notes

- **Archive Files**: Files in `docs/archive/` may contain outdated tasks. Always verify with ROADMAP.md.
- **Manual Testing**: The 339 tasks in `tests/ui/MANUAL_TESTING_CHECKLIST.md` are reference items, not all actionable.
- **Task Counts**: Approximate counts based on grep patterns for unchecked checkboxes and status markers.
- **Last Updated**: 2025-11-18 (auto-generated from repository scan)

---

**For detailed task descriptions and implementation guidance, see [CLAUDE.md](CLAUDE.md#available-tasks--work-items)**
