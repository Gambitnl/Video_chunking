# UI Improvements Task Collection

This document consolidates the twenty UI improvements documented in `UI_IMPROVEMENTS.md` into a concise, ASCII-only checklist with priority and estimated effort. Use this as the source list when planning or tracking UI polish work.

## Current Status Check (2025-11-23)

The table below captures whether each improvement is still required based on the current Gradio UI implementation. "Still required" means no implementation is present or only minimal scaffolding exists; "Partially covered" means a narrow subset is present but gaps remain. Detailed remediation steps for every item now live in `UI_IMPROVEMENTS_SOLUTIONS.md` to guide implementation.

| # | Improvement | Priority | Effort | Status | Notes |
|---|-------------|----------|--------|--------|-------|
| 1 | Missing ARIA labels and accessibility attributes | High | Medium | Completed | ARIA helpers now propagate labels, described-by targets, and live regions across process, campaign, characters, and settings tabs (2025-11-23).
| 2 | No keyboard navigation support | High | High | Still required | There are no keyboard shortcut bindings or tabindex management utilities wired in any UI module.
| 3 | Missing focus indicators | Medium | Low | Still required | `src/ui/theme.py` defines focus styles only for text inputs, leaving buttons, accordions, and custom components without visible focus rings.
| 4 | Buttons do not show loading states | High | Low | Completed | Added `ButtonStates` helper and wired process/preflight buttons to show `[WORKING]` labels and disable concurrent actions while processing.
| 5 | No progress percentage display | Medium | Medium | Still required | Progress components are present but no percentage or ETA rendering is wired into the processing events.
| 6 | Missing success animations or confirmations | Low | Low | Still required | No success toasts, banners, or state transitions are emitted after processing completes.
| 7 | No dark mode support | Medium | Medium | Still required | Dark palette tokens exist in `src/ui/theme.py` but no toggle or conditional styling is applied in the app layout.
| 8 | Inconsistent button sizing | Low | Low | Still required | Button creation relies on ad-hoc size arguments without a central sizing policy or audit.
| 9 | Empty states lack visual appeal | Medium | Low | Still required | Upload, configuration, and results areas have plain Markdown placeholders with no guided empty-state layouts.
| 10 | No real-time input validation | High | Low | Partially covered | Session ID validation is wired via `validate_session_id_realtime`, but other fields (audio type, party selection, speaker counts) do not yet surface immediate validation feedback.
| 11 | File upload missing drag-and-drop cues | Medium | Low | Still required | The upload component uses the default Gradio file input without the custom drag-drop affordances defined in the theme.
| 12 | No character count on long text areas | Low | Low | Still required | Text areas and multi-line inputs do not display live character or word counts.
| 13 | Session search missing debouncing | Medium | Medium | Still required | No debounced search helpers or throttled handlers are present for session lookups.
| 14 | Table sorting not implemented | Medium | Medium | Still required | Data tables are rendered without sortable headers or column-level sort handlers.
| 15 | No autosave indicator for settings | Medium | Medium | Still required | Settings changes are not annotated with autosave status or last-saved timestamps in the UI.
| 16 | No confirmation dialogs for destructive actions | High | Medium | Still required | Destructive actions (cancel, reset, rerun) execute immediately with no confirmation prompts.
| 17 | Accordion state not persisted | Low | Low | Still required | Accordion open/closed state is not persisted across interactions or reloads.
| 18 | No breadcrumbs or progress persistence | Medium | Medium | Still required | The workflow stepper is static and non-clickable, with no persisted active step between refreshes.
| 19 | Missing copy functionality | Low | Low | Still required | Copy helpers exist but are not wired to outputs or identifiers anywhere in the UI modules.
| 20 | No tooltips despite CSS support | Medium | Medium | Still required | Complex fields rely on static `info` text; no hover tooltips or helper popovers are attached.

## Accessibility and Usability (Critical)
1. Missing ARIA labels and accessibility attributes (Priority: High, Effort: Medium) - add aria-label, role, aria-describedby, and aria-live coverage across all interactive elements in every tab.
2. No keyboard navigation support (Priority: High, Effort: High) - add keyboard shortcuts, tabindex ordering, skip links, and keyboard-triggerable primary actions.
3. Missing focus indicators (Priority: Medium, Effort: Low) - apply consistent focus rings and focus management to all interactive elements.

## Loading States and Feedback
4. Buttons do not show loading states (Priority: High, Effort: Low) - add spinners or busy text, disable during processing, and restore on completion.
5. No progress percentage display (Priority: Medium, Effort: Medium) - show quantitative progress and estimated time remaining.
6. Missing success animations or confirmations (Priority: Low, Effort: Low) - add noticeable completion feedback such as toasts or highlight effects.

## Visual Design and Consistency
7. No dark mode support (Priority: Medium, Effort: Medium) - expose a theme toggle and apply the dark palette defined in `theme.py`.
8. Inconsistent button sizing (Priority: Low, Effort: Low) - standardize button sizes by action type across tabs.
9. Empty states lack visual appeal (Priority: Medium, Effort: Low) - add richer empty-state layouts with calls to action.

## Form Validation and Input Feedback
10. No real-time input validation (Priority: High, Effort: Low) - validate inputs such as session IDs on change with clear pass or fail messaging.
11. File upload missing drag-and-drop cues (Priority: Medium, Effort: Low) - enhance drag-drop affordances and visual feedback for uploads.
12. No character count on long text areas (Priority: Low, Effort: Low) - display character, word, or item counts and warn near limits.

## Search and Discovery
13. Session search missing debouncing (Priority: Medium, Effort: Medium) - debounce search inputs to avoid excessive requests and jitter.
14. Table sorting not implemented (Priority: Medium, Effort: Medium) - add sortable columns for lists such as sessions and characters.
15. No autosave indicator for settings (Priority: Medium, Effort: Medium) - surface autosave status and last-saved timestamps.

## Navigation and Workflow
16. No confirmation dialogs for destructive actions (Priority: High, Effort: Medium) - require explicit confirmation before restarts or resets.
17. Accordion state not persisted (Priority: Low, Effort: Low) - remember accordion open or closed state between visits.
18. No breadcrumbs or progress persistence (Priority: Medium, Effort: Medium) - make the workflow stepper dynamic, clickable, and stateful.
19. Missing copy functionality (Priority: Low, Effort: Low) - wire up copy-to-clipboard buttons for common outputs and identifiers.

## Feature Gaps
20. No tooltips despite CSS support (Priority: Medium, Effort: Medium) - attach tooltips to complex fields using the existing styling hooks.
