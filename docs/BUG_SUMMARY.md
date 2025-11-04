# Bug Summary - Quick Reference

> **Generated**: 2025-11-03
> **Source**: [BUG_HUNT_TODO.md](BUG_HUNT_TODO.md) - Area 4: UI Dashboard Issues (lines 253-446)
> **Total Issues**: 29 bugs
>
> **Note**: This is a quick-reference summary. For full issue descriptions with "Why it's an issue" explanations and detailed context, see [BUG_HUNT_TODO.md - Area 4](BUG_HUNT_TODO.md#area-4-ui-dashboard-issues-2025-11-03)

---

## High Priority (6 issues)

**Reference**: [BUG_HUNT_TODO.md:283-287, 295-299, 367-371, 387-391, 421-425](BUG_HUNT_TODO.md#process-session-tab)

| ID | Title | File | Line | Details |
|----|-------|------|------|---------|
| BUG-20251103-006 | Process Session - No client-side validation | src/ui/process_session_tab_modern.py | 205-210 | [View](BUG_HUNT_TODO.md#L283) |
| BUG-20251103-008 | Process Session - No progress indicator | app.py | 509-601 | [View](BUG_HUNT_TODO.md#L295) |
| BUG-20251103-019 | Live Session - Non-functional placeholder | src/ui/live_session_tab.py | 92-163 | [View](BUG_HUNT_TODO.md#L367) |
| BUG-20251103-022 | Social Insights - WordCloud dependency not handled | src/ui/social_insights_tab.py | 20 | [View](BUG_HUNT_TODO.md#L387) |
| BUG-20251103-027 | Global - No conflict detection for concurrent ops | Multiple files | - | [View](BUG_HUNT_TODO.md#L421) |

---

## Medium Priority (13 issues)

**Reference**: [BUG_HUNT_TODO.md - Various sections](BUG_HUNT_TODO.md#area-4-ui-dashboard-issues-2025-11-03)

| ID | Title | File | Line | Details |
|----|-------|------|------|---------|
| BUG-20251103-002 | Main Dashboard - Campaign state not persisted | app.py | 623 | [View](BUG_HUNT_TODO.md#L257) |
| BUG-20251103-004 | Campaign Launcher - Dropdown not refreshed | app.py | 630-635 | [View](BUG_HUNT_TODO.md#L269) |
| BUG-20251103-007 | Process Session - Results don't auto-scroll | src/ui/process_session_tab_modern.py | 219-226 | [View](BUG_HUNT_TODO.md#L289) |
| BUG-20251103-009 | Process Session - Audio path resolution inconsistent | app.py | 499-507 | [View](BUG_HUNT_TODO.md#L301) |
| BUG-20251103-011 | Campaign Tab - Static content only | src/ui/campaign_tab_modern.py | 9-46 | [View](BUG_HUNT_TODO.md#L315) |
| BUG-20251103-013 | Campaign Dashboard - No error recovery | app.py | 300-335 | [View](BUG_HUNT_TODO.md#L327) |
| BUG-20251103-017 | Campaign Dashboard - Sessions not filtered by campaign | src/campaign_dashboard.py | 119-136 | [View](BUG_HUNT_TODO.md#L353) |
| BUG-20251103-018 | Campaign Dashboard - Narratives include other campaigns | src/campaign_dashboard.py | 146-148 | [View](BUG_HUNT_TODO.md#L359) |
| BUG-20251103-021 | Social Insights - No loading indicator | src/ui/social_insights_tab.py | 16-64 | [View](BUG_HUNT_TODO.md#L381) |
| BUG-20251103-025 | Settings & Tools - Static markdown only | src/ui/settings_tools_tab_modern.py | 29-41 | [View](BUG_HUNT_TODO.md#L407) |
| BUG-20251103-026 | Global - Excessive re-renders on campaign change | app.py | 681-778 | [View](BUG_HUNT_TODO.md#L415) |
| BUG-20251103-028 | Global - Error messages expose internal details | Multiple files | - | [View](BUG_HUNT_TODO.md#L427) |
| BUG-20251103-029 | Data - Session library doesn't verify campaign_id | app.py | 397-426 | [View](BUG_HUNT_TODO.md#L435) |

---

## Low Priority (10 issues)

**Reference**: [BUG_HUNT_TODO.md - Various sections](BUG_HUNT_TODO.md#area-4-ui-dashboard-issues-2025-11-03)

| ID | Title | File | Line | Details |
|----|-------|------|------|---------|
| BUG-20251103-003 | Campaign Launcher - No validation for empty names | app.py | 780-843 | [View](BUG_HUNT_TODO.md#L263) |
| BUG-20251103-005 | Campaign Manifest - Exception handling too broad | app.py | Multiple | [View](BUG_HUNT_TODO.md#L275) |
| BUG-20251103-010 | Process Session - Name parsing edge cases | app.py | 542-543 | [View](BUG_HUNT_TODO.md#L307) |
| BUG-20251103-012 | Campaign Dashboard - Knowledge base truncated | app.py | 337-366 | [View](BUG_HUNT_TODO.md#L321) |
| BUG-20251103-014 | Campaign Dashboard - Text truncation cuts words | src/campaign_dashboard.py | 101 | [View](BUG_HUNT_TODO.md#L335) |
| BUG-20251103-015 | Campaign Dashboard - Health percentage edge case | src/campaign_dashboard.py | 196 | [View](BUG_HUNT_TODO.md#L341) |
| BUG-20251103-016 | Campaign Dashboard - Managers instantiated multiple times | src/campaign_dashboard.py | 20-22 | [View](BUG_HUNT_TODO.md#L347) |
| BUG-20251103-020 | Live Session - Stop button enabled incorrectly | src/ui/live_session_tab.py | 111-115 | [View](BUG_HUNT_TODO.md#L373) |
| BUG-20251103-023 | Social Insights - Temp file cleanup not guaranteed | src/ui/social_insights_tab.py | 49-50 | [View](BUG_HUNT_TODO.md#L393) |
| BUG-20251103-024 | Social Insights - Stale nebula after campaign filter | src/ui/social_insights_tab.py | 130-134 | [View](BUG_HUNT_TODO.md#L399) |
| BUG-20251103-030 | Data - Profile filtering logic flaw with None | Multiple files | - | [View](BUG_HUNT_TODO.md#L441) |

---

## By Category

### Campaign Launcher & Main Dashboard (4 bugs)
- BUG-20251103-002 (Medium), BUG-20251103-003 (Low), BUG-20251103-004 (Medium), BUG-20251103-005 (Low)

### Process Session Tab (5 bugs)
- BUG-20251103-006 (High), BUG-20251103-007 (Medium), BUG-20251103-008 (High), BUG-20251103-009 (Medium), BUG-20251103-010 (Low)

### Campaign Tab (3 bugs)
- BUG-20251103-011 (Medium), BUG-20251103-012 (Low), BUG-20251103-013 (Medium)

### Campaign Dashboard Module (5 bugs)
- BUG-20251103-014 (Low), BUG-20251103-015 (Low), BUG-20251103-016 (Low), BUG-20251103-017 (Medium), BUG-20251103-018 (Medium)

### Live Session Tab (2 bugs)
- BUG-20251103-019 (High), BUG-20251103-020 (Low)

### Social Insights Tab (4 bugs)
- BUG-20251103-021 (Medium), BUG-20251103-022 (High), BUG-20251103-023 (Low), BUG-20251103-024 (Low)

### Settings & Tools Tab (1 bug)
- BUG-20251103-025 (Medium)

### Cross-Tab Coordination (3 bugs)
- BUG-20251103-026 (Medium), BUG-20251103-027 (High), BUG-20251103-028 (Medium)

### Data Consistency (2 bugs)
- BUG-20251103-029 (Medium), BUG-20251103-030 (Low)

---

## Recommended Fix Order

### Week 1 (Critical UX Issues)
1. BUG-20251103-006 - Add client-side validation
2. BUG-20251103-019 - Hide/mark Live Session as "Coming Soon"
3. BUG-20251103-022 - Better WordCloud dependency error

### Week 2 (Data Integrity & Performance)
4. BUG-20251103-027 - Add concurrent operation locking
5. BUG-20251103-008 - Implement progress indicators
6. BUG-20251103-017 - Fix campaign filtering in dashboard
7. BUG-20251103-018 - Fix narrative filtering

### Week 3 (UX Improvements)
8. BUG-20251103-007 - Auto-scroll to results
9. BUG-20251103-021 - Add loading indicators
10. BUG-20251103-002 - Persist campaign state

### Month 2 (Polish & Optimization)
11. BUG-20251103-026 - Optimize re-render cascade
12. BUG-20251103-028 - User-friendly error messages
13. Remaining Low priority issues

---

**For detailed descriptions, see**: [BUG_HUNT_TODO.md](BUG_HUNT_TODO.md#area-4-ui-dashboard-issues-2025-11-03)
