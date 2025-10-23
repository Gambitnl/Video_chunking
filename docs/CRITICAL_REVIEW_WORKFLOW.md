# Critical Review Workflow

> **A Practical Guide to Rigorous Code Review**
> **Created**: 2025-10-22
> **Agent**: `.claude/agents/critical-reviewer.md`

---

## Overview

This document provides a step-by-step workflow for implementing and reviewing features using the **Critical Reviewer Agent** methodology. This process ensures high-quality code through skeptical analysis, documented reasoning, and iterative improvement.

---

## The Complete Workflow

### Phase 1: Implementation

**Implementer's Responsibilities**

1. **Read the Implementation Plan**
   - Review requirements in `IMPLEMENTATION_PLANS.md` (or PART2/3/4)
   - Understand subtasks, effort estimates, success criteria
   - Note any edge cases or special considerations

2. **Implement the Feature**
   - Follow the subtask breakdown
   - Write tests as you go (don't leave for end)
   - Use existing patterns and conventions
   - Handle error cases explicitly

3. **Log progress continuously**
   - Update the plan immediately after each completed subtask (status checkbox, timestamp, short note)
   - Capture design decisions in the "Implementation Notes & Reasoning" block while context is fresh
   - Record open questions or risks that reviewers should consider

4. **Self-Review**
   - Run all tests: `pytest -q`
   - Test edge cases manually
   - Check for code smells
   - Ensure logging is appropriate

5. **Document Implementation Notes** [REQUIRED]

   Add this section to the implementation plan:

   ```markdown
   ### Implementation Notes & Reasoning
   **Implementer**: [Your Name/Handle]
   **Date**: YYYY-MM-DD

   #### Design Decisions
   1. **[Decision Name]**
      - **Choice**: What was chosen
      - **Reasoning**: Why this approach over alternatives
      - **Alternatives Considered**: What else was evaluated
      - **Trade-offs**: What was gained/lost

   #### Open Questions
   - Any concerns for code review?
   - Areas needing feedback or validation?
   ```

6. **Mark Ready for Review**
   - Update implementation plan status
   - Commit code with clear message
   - Request review (human or AI agent)

---

### Phase 2: Critical Review

**Reviewer's Responsibilities** (Human or AI Agent)

#### Step 1: Invoke the Critical Reviewer Agent

**For AI Review**, use one of these patterns:

```bash
# Explicit invocation
/critical-reviewer P0-BUG-003

# Challenge pattern (triggers skeptical analysis)
"Is there truly no issues with the P0-BUG-003 implementation?"

# Direct request
"Critically review the checkpoint system implementation"
```

#### Step 2: Agent Performs Analysis

The agent will:

1. [x] **Read implementation plan requirements**
2. [x] **Examine actual implementation code**
3. [x] **Review test coverage**
4. [x] **Read implementer's reasoning**
5. [SEARCH] **Apply skeptical questioning**:
   - What edge cases weren't tested?
   - Are there consistency issues?
   - What happens with unexpected inputs?
   - Are there API design smells?
   - How could this fail in production?

#### Step 3: Test Edge Cases

The agent (or human reviewer) tests:

```python
# Boundary values
negative_values = -500
zero_values = 0
very_large_values = 999999999999
empty_strings = ""
whitespace_only = "   "
none_values = None

# Invalid inputs
malformed_data = "not-a-number"
float_like_strings = "10.5"

# Consistency checks
# Compare with similar functions
# Check API design patterns
# Validate error handling paths
```

#### Step 4: Document Findings

**Add this section to the implementation plan**:

```markdown
### Code Review Findings
**Reviewer**: [Name or "Claude Code (Critical Analysis)"]
**Date**: YYYY-MM-DD
**Status**: [WARNING] Issues Found / [DONE] Approved / [LOOP] Revisions Requested

#### Issues Identified

1. **[Issue Category]** - Severity: Critical/High/Medium/Low
   - **Problem**: Clear description with code example
   - **Impact**: What could go wrong
   - **Recommendation**: How to fix
   - **Status**: [ ] Unresolved / [x] Fixed / [DEFER] Deferred

#### Positive Findings
- [x] What was done well
- [x] Patterns worth replicating

#### Verdict
**Overall Assessment**: [Summary paragraph]

**Merge Recommendation**:
- [DONE] **Ready for Merge** (no issues or all fixed)
- [WARNING] **Issues Found** (needs discussion)
- [LOOP] **Revisions Requested** (must fix before merge)
```

---

### Phase 3: Dialogue & Iteration

1. **Review the Findings** - Implementer reads code review findings
2. **Prioritize Issues** - MUST FIX vs SHOULD FIX vs NICE TO HAVE
3. **Iterate on Fixes** - Address priority issues, update notes
4. **Update Status Tracking** - Mark issues as [x] Fixed or [DEFER] Deferred

---

### Phase 4: Final Approval & Merge

**Merge Checklist**

- [ ] All Critical/High severity issues resolved
- [ ] Tests passing: `pytest -q`
- [ ] Implementation Notes documented
- [ ] Code Review Findings documented
- [ ] Merge recommendation: [DONE] Ready for Merge

**Merge**:
```bash
git add .
git commit -m "feat: implement [feature] with critical review

- Addressed [X] review findings
- Added comprehensive test coverage

Reviewed-by: [Reviewer Name]"
git push
```

---

## Real-World Examples

### Example 1: Clean Implementation (P0-BUG-001)

**Implementation**: Stale Clip Cleanup

**Review Findings**:
- [x] No issues found
- [x] Exceeds spec (also cleans manifest)
- **Verdict**: [DONE] **Ready for Merge**

**Outcome**: Merged immediately

---

### Example 2: Issues Found (P0-BUG-002)

**Implementation**: Safe Type Casting

**Review Findings**:
- [CRITICAL] **Issue #2 (HIGH)**: Bool/Int inconsistency
- [WARNING] **Issue #1 (Medium)**: Private methods used publicly
- **Verdict**: [LOOP] **Revisions Requested**

**Iteration**:
1. Fixed Issue #2 (5 min)
2. Addressed Issue #1 (15 min)
3. Improved tests (30 min)

**Final Review**: [DONE] **Ready for Merge**

---

## Common Skeptical Questions

- "Is there truly no issues with this solution?"
- "What edge cases weren't tested?"
- "How does this compare to [similar function]?"
- "Could this reintroduce the bug it's fixing?"
- "Will this be easy to modify later?"

---

## Philosophy

> "The purpose of critical review is not to reject work, but to improve it through rigorous questioning and documented reasoning."

This workflow creates a **learning system** where quality emerges from iteration, not perfection on first try.

---

## See Also

- **Agent Definition**: `.claude/agents/critical-reviewer.md`
- **Templates**: `IMPLEMENTATION_PLANS.md` (Introduction section)
- **Repository Guidelines**: `AGENTS.md`
