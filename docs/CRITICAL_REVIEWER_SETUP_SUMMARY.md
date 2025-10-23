# Critical Reviewer Setup Summary

> **Created**: 2025-10-22  
> **Purpose**: Document the assets and workflow required for the Critical Reviewer methodology

---

## Components Installed

1. **Agent Definition**  
   - File: `.claude/agents/critical-reviewer.md`  
   - Describes mindset, checklists, and questioning patterns for skeptical reviews.

2. **Workflow Guide**  
   - File: `docs/CRITICAL_REVIEW_WORKFLOW.md`  
   - Step-by-step process for implementers and reviewers, including templates.

3. **Onboarding Entry Point**  
   - File: `AGENT_ONBOARDING.md` (root)  
   - Structured reading path for new contributors; highlights the reviewer workflow.

4. **ASCII-Only Policy**  
   - File: `AGENTS.md` (see “Character Encoding: ASCII-Only”)  
   - Prevents cp1252 issues on Windows and keeps automation reliable.

---

## Implementation Plan Requirements

The top section of every `IMPLEMENTATION_PLANS*.md` file now defines two mandatory sections for each task:

- **Implementation Notes & Reasoning** – captures decisions, alternatives, and trade-offs.  
- **Code Review Findings** – records reviewer verdicts, severity, and follow-up actions.

This ensures every feature records both the implementer’s intent and the reviewer’s feedback.

---

## Operator Workflow Loop

Documented in `AGENTS.md`, this loop applies to all contributors:

1. Read the relevant implementation plan or roadmap item.  
2. Implement subtasks and update the plan immediately after each milestone.  
3. Capture reasoning in “Implementation Notes & Reasoning.”  
4. Run targeted tests and record the commands used.  
5. Respond to reviews and report progress referencing the plan.

Keeping plans in sync is required before requesting a critical review.

---

## Critical Review Checklist (Quick Reference)

Reviewers must address the following (see agent file for full details):

- **Design quality** – API consistency, error handling, edge cases.  
- **Implementation consistency** – naming, logging, parity with similar code.  
- **Testing rigor** – happy path and failure path coverage.  
- **Maintenance impact** – future proofing and documentation clarity.

The reviewer records findings in the plan and issues one of three verdicts: Approved, Issues Found, or Revisions Requested.

---

## Next Steps for Contributors

1. **Before coding** – read the relevant implementation plan and confirm open subtasks.  
2. **While coding** – update the plan as you complete work; avoid “document later.”  
3. **Before review** – ensure Implementation Notes and test evidence are present.  
4. **Request review** – ask the Critical Reviewer agent (or a human reviewer) to challenge the work.  
5. **After review** – address findings, update the plan, and re-run tests.

By combining the workflow guide, onboarding path, and ASCII-safe docs, the repository now enforces a repeatable quality bar and retains institutional memory for future contributors.
