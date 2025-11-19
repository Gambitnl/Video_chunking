# Autonomous Task Execution Workflow v4.0
**Optimized for Claude Code on the Web | Last Updated: 2025-11-19**

Pick any task at will and complete it following the repository's Operator Workflow.

---

## Core Principles

1. **[PARALLEL]** Leverage parallel tool usage - Claude Code excels at concurrent operations
2. **[STANDARDS]** Read repository standards first - CLAUDE.md and AGENTS.md are your contract
3. **[VISIBLE]** TodoWrite for visibility - User sees your progress in real-time
4. **[VERIFY]** Verify before implementing - Always get user approval for task selection
5. **[REVIEW]** Self-review rigorously - Catch issues before reviewers do

---

## Pre-Implementation (5-10 min)

### Environment Check (PARALLEL - Single Message)

Use parallel tool calls to check environment:

```
Read: AGENTS.md, CLAUDE.md (in one message)
Bash: which pip && which pytest && python --version
Bash: git branch --show-current
```

### Find Available Tasks (PARALLEL)

```
Glob: **/OUTSTANDING_TASKS.md
Glob: ROADMAP.md
Glob: **/BUG_*.md
Glob: IMPLEMENTATION_PLAN*.md
Read: [all files found above in single message]
```

**Priority order:**
1. P0 (Critical) > P1 (High Impact) > P2 (Important) > P3 (Future) > P4 (Infrastructure)
2. Within same priority: HIGH bugs > MEDIUM bugs > LOW bugs
3. Prefer [LOW] conflict risk tasks when working autonomously

### Verify Task Status

**CRITICAL:** Before proposing a task, check if already complete:
- Search for `[x]` markers in OUTSTANDING_TASKS.md
- Check git history: `git log --oneline --grep="TASK-ID" -n 5`
- If task shows `[x]` but incomplete, verify implementation exists

---

## Task Selection & User Verification (MANDATORY)

**Present analysis BEFORE starting work:**

```
========================================
[!] PROPOSED TASK: BUG-20251119-102
========================================

Priority: **[P2]** Important | Effort: **30-45 min** | Risk: [LOW]

Title: SessionAnalyzer.calculate_character_stats - Fix missing duration field

Why this task:
1. [RECENT] Newly logged 2025-11-19, no one working on it
2. [ISOLATED] Low conflict risk - analytics module rarely modified
3. [IMPACT] Breaks character statistics display (zero speaking durations)

FILES TO MODIFY:
  • `src/analytics/session_analyzer.py:373-394`
  • `tests/test_analytics_session_analyzer.py`

FILES TO CREATE: None

Implementation approach:
  Step 1: Read `session_analyzer.py:373-394` to understand current logic
  Step 2: Replace `segment.duration` with calculated `end_time - start_time`
  Step 3: Add regression test validating duration calculation
  Step 4: Run `pytest -k test_analytics_session_analyzer -v`

Alternative tasks considered:
  • BUG-20251102-13 (LangChain JSON) - [LOCKED] by GPT-5.1-Codex
  • BUG-20251103-002 (Campaign state) - [MED] conflict risk (app.py core)
  • BUG-20251107-01 (num_speakers) - [HIGH] complexity (1-2 hours)

Approve? (yes/no/suggest alternative)
```

**Skip verification only if:**
- User said "proceed autonomously" AND
- You completed 1+ approved tasks this session AND
- Continuing similar priority/complexity work

---

## Task Locking (Immediate)

### 1. Lock in OUTSTANDING_TASKS.md

```
Read: docs/archive/OUTSTANDING_TASKS.md (find exact line)
Edit: Change [ ] to [~] with agent name + UTC timestamp
Bash: git add docs/archive/OUTSTANDING_TASKS.md && git commit -m "Lock task: TASK-ID"
```

### 2. Create TodoWrite tracker

```json
[
  {"content": "Lock TASK-ID in OUTSTANDING_TASKS.md", "status": "in_progress", "activeForm": "Locking TASK-ID"},
  {"content": "Read implementation plan/bug details", "status": "pending", "activeForm": "Reading plan"},
  {"content": "Read current implementation files", "status": "pending", "activeForm": "Reading files"},
  {"content": "Implement fix/feature", "status": "pending", "activeForm": "Implementing"},
  {"content": "Self-review checklist", "status": "pending", "activeForm": "Self-reviewing"},
  {"content": "Run syntax validation", "status": "pending", "activeForm": "Validating syntax"},
  {"content": "Update OUTSTANDING_TASKS.md completion", "status": "pending", "activeForm": "Updating tasks"},
  {"content": "Commit and push changes", "status": "pending", "activeForm": "Committing"}
]
```

---

## File Impact Analysis

### Use Parallel Reads

```
Read: file1.py, file2.py, file3.py (in one message)
Grep: "pattern" -n -C 3 --output_mode=content
Bash: git log -n 5 --oneline -- [file]
```

### TodoWrite Checkpoint

Update after analysis:
```
- Analyzing file impact (in_progress)
- File1: [changes needed, LOC estimate, risk level]
- File2: [changes needed, LOC estimate, risk level]
```

### Red Flags (coordinate with user before proceeding)

- **[!]** Touching >5 files -> consider breaking into subtasks
- **[!]** Shared files (app.py, config.py) -> extra care, check for locks
- **[!]** File modified by others in last 7 days -> coordinate
- **[!!!]** High conflict risk -> verify no parallel work

---

## Implementation

### Code Quality Standards (from CLAUDE.md)

- **[ASCII]** ASCII-only - No Unicode characters (-> not →, [x] not ✓)
- **[TYPES]** Type hints - All function signatures
- **[DOCS]** Docstrings - All public functions/classes
- **[SIZE]** Functions <50 lines - Extract helpers if needed
- **[WHY]** Comments explain WHY - Not what

### Pattern

1. **Read before Edit** (CRITICAL - Edit tool requires it)
2. **Make changes incrementally** - One logical change at a time
3. **Update TodoWrite** - Mark completed immediately, not batched
4. **Validate syntax** - `python -m py_compile [file]` after each edit

### Testing (non-negotiable)

- Write tests ALONGSIDE code (not after)
- Target: >85% coverage for modified code
- Run: `python -m py_compile [file]` (syntax check minimum)
- If pytest available: `pytest -k test_name -v`

### Commit Frequently

```bash
# Conventional commits format
git add [files] && git commit -m "feat: description"
git add [files] && git commit -m "fix: description"
git add [files] && git commit -m "test: description"
```

---

## Self-Review Checklist (MANDATORY)

Run BEFORE final commit:

### [!] Critical (Must-check)

- [ ] **Read before Edit** - Edit tool requirement
- [ ] **ASCII-only** - No Unicode characters anywhere
- [ ] **Type hints** - All function signatures
- [ ] **Docstrings** - All public functions
- [ ] **Edge cases** - Especially UI components (Gradio)
- [ ] **Cleanup** - No commented code, no `print()` statements
- [ ] **Logging** - Use `logger`, not `print()`
- [ ] **Boundary conditions** - None, empty, whitespace, zero, negative
- [ ] **No hardcoded values** - Use Config or constants
- [ ] **Scope** - No scope creep
- [ ] **Syntax** - `python -m py_compile [file]` passes

### Quality

- [ ] **DRY** - No code duplication
- [ ] **Breaking changes** - Check all call sites
- [ ] **Comments** - Explain WHY, not what
- [ ] **Naming** - No single letters except i, j in loops
- [ ] **Security** - No SQL injection, XSS, command injection, path traversal

### Repository Standards

- [ ] **Operator Workflow** - Read plan -> implement -> document -> test
- [ ] **CLAUDE.md** - ASCII-only, coding style, patterns
- [ ] **AGENTS.md** - Project structure, naming conventions

---

## Code Review Response

When bot reviewers (gemini-code-assist, chatgpt-codex) comment:

### Acknowledge All Feedback

- **[HIGH/CRITICAL]** -> Fix immediately
- **[MEDIUM]** -> Fix if <30 min effort
- **[LOW]** -> Document for follow-up or fix if trivial

### Process

1. Read files before editing (Edit tool requirement)
2. Apply suggested changes
3. Commit with review acknowledgment:

```bash
git commit -m "fix: Address code review feedback for [feature]

[Category] Improvements:
- [Change 1]
- [Change 2]

Addresses:
- [reviewer-bot]: [issue description] ([priority])

Co-authored-by: [reviewer-bot]"
```

4. Push immediately after review fixes

---

## Completion Checklist

Task complete when:

- [ ] User approved task selection
- [ ] Task properly locked
- [ ] Feature/fix works as specified
- [ ] Self-review checklist 100% complete
- [ ] Tests prove correctness
- [ ] Documentation updated
- [ ] Code review feedback addressed
- [ ] OUTSTANDING_TASKS.md reflects completion
- [ ] You can confidently hand it to another developer

---

## Git Push Protocol

```bash
# Always use -u flag for first push to branch
git push -u origin <branch-name>

# If push fails with network error, retry with exponential backoff:
# Attempt 1: immediate
# Attempt 2: wait 2s
# Attempt 3: wait 4s
# Attempt 4: wait 8s
# Attempt 5: wait 16s (final)
```

**Branch naming:** Must start with `claude/` and end with session ID (enforced by git hooks)

---

## Tool Usage Best Practices

### Parallel Tool Calls (Maximize Performance)

**DO THIS** (single message):
```
Read: file1.py
Read: file2.py
Read: file3.py
Grep: "pattern"
```

**NOT THIS** (multiple messages):
```
Read: file1.py
[wait for response]
Read: file2.py
[wait for response]
```

### Sequential Tool Calls (Dependencies)

Use `&&` for dependent commands:
```bash
git add . && git commit -m "msg" && git push
```

### Task Tool (Complex Multi-Step)

Use `Task(Explore)` for:
- "Where are errors handled?" (codebase exploration)
- "How does authentication work?" (architectural questions)
- "Find all instances of X pattern" (comprehensive search)

**Don't use Task for:**
- Reading specific file paths (use Read)
- Searching for specific class (use Glob)
- Searching within 2-3 known files (use Grep)

### TodoWrite (Progress Visibility)

- Create at task start
- Update after EACH subtask (not batched)
- Mark complete immediately when done
- One task `in_progress` at a time

---

## When Stuck

### Escalation Ladder

1. **Grep** for similar patterns in codebase (precedent)
2. **Read** docs/ for guidance (QUICKREF.md, SETUP.md)
3. **Read** test files for usage examples (tests/test_*.py)
4. **Bash**: `git log --oneline -- [file] -n 10` (see recent changes)
5. **Ask** user specific questions (not "how do I...")

### Don't

- Spin for >15 min without asking
- Ask vague questions ("how does this work?")
- Guess at implementation - verify with user

---

## Quick Reference

### Repository Standards

- **CLAUDE.md** - Coding style, patterns, critical requirements
- **AGENTS.md** - Project structure, Operator Workflow
- **ROADMAP.md** - Current priorities and features

### Task Sources

- **docs/archive/OUTSTANDING_TASKS.md** - Master checklist (primary source)
- **docs/archive/BUG_SUMMARY.md** - Quick bug reference
- **docs/archive/BUG_HUNT_TODO.md** - Detailed bug descriptions
- **IMPLEMENTATION_PLAN*.md** - Feature implementation plans

### Common Commands

```bash
# Syntax check
python -m py_compile [file]

# Run tests
pytest -k test_name -v
pytest tests/test_file.py

# Git operations
git log --oneline --grep="TASK-ID" -n 5
git log -n 5 --oneline -- [file]
git add . && git commit -m "fix: description"
git push -u origin <branch>
```

---

## Visual Formatting Guide

### Task Proposal Template

```
========================================
[!] PROPOSED TASK: TASK-ID
========================================

Priority: **[P0/P1/P2/P3/P4]** | Effort: **X min/hours** | Risk: [LOW/MED/HIGH]

Title: Brief description

Why this task:
1. [REASON 1]
2. [REASON 2]
3. [REASON 3]

FILES TO MODIFY:
  • `path/to/file.py:line-range`
  • `path/to/test.py`

FILES TO CREATE: None | List paths

Implementation approach:
  Step 1: [what you'll do]
  Step 2: [what you'll do]
  Step 3: [what you'll do]

Alternative tasks considered:
  • TASK-ID - [why not chosen]
  • TASK-ID - [why not chosen]

Approve? (yes/no/suggest alternative)
```

### File Path Formatting

Always use backticks for file paths:
- Modify `src/analytics/session_analyzer.py:373-394`
- Test `tests/test_analytics_session_analyzer.py:142-150`
- Create `docs/NEW_FEATURE.md`

### Priority Indicators

- **[P0]** Critical/Immediate - Bugs, crashes
- **[P1]** High Impact - Major features
- **[P2]** Important - Significant improvements
- **[P3]** Future - Nice-to-have
- **[P4]** Infrastructure - Technical debt

### Risk Indicators

- **[LOW]** - Isolated change, well-tested module
- **[MED]** - Touches shared code, requires coordination
- **[HIGH]** - Cross-cutting change, high complexity
- **[!!!]** - Critical system component, requires expert review

---

**Version:** 4.0
**Optimized for:** Claude Code on the Web (Sonnet 4.5)
**Last Updated:** 2025-11-19

**Key Changes from v3.0:**
1. Visual formatting with separators and bold markers
2. Concrete tool call examples (not just descriptions)
3. File path backtick formatting throughout
4. Expanded error handling and "When Stuck" section
5. TodoWrite JSON examples
6. Code review response protocol
7. Quick reference section for common operations
