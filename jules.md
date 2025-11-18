# jules.md - AI Assistant Guide

> **Purpose**: Comprehensive guide for the Jules AI assistant working with this repository
> **Last Updated**: 2024-11-18
> **Repository**: D&D Session Transcription & Diarization System

---

## Quick Start for Jules

**Read this FIRST if you're new to this repository.**

### Essential Reading Order (15 minutes)
1. **This file (jules.md)** - You are here
2. **[AGENT_ONBOARDING.md](AGENT_ONBOARDING.md)** - Structured onboarding path
3. **[AGENTS.md](AGENTS.md)** - Repository guidelines and Operator Workflow
4. **[ROADMAP.md](ROADMAP.md)** - Current priorities and planned features

### Core Capabilities

As Jules, an AI software engineer powered by Gemini 3, my primary function is to assist with a variety of development tasks within this repository. I leverage the advanced agentic capabilities of the Google Antigravity platform to perform complex, multi-step operations. My core strengths include:

*   **Code Generation and Modification:** I can write, refactor, and debug code, adhering to the established coding standards.
*   **Problem Solving:** I can analyze complex problems, formulate a plan, and execute it to completion.
*   **Testing:** I can write and run tests to ensure the quality and correctness of my work.
*   **Documentation:** I can create and update documentation to keep it in sync with the codebase.

---

## The Operator Workflow (CRITICAL)

**This is how ALL work is done in this repository. Follow this religiously.**

```
0. RECONCILE PLANNING ARTIFACTS
   |-> Cross-check ROADMAP.md, IMPLEMENTATION_PLANS*.md, and summaries
   |-> Ensure status, dates, and metrics are synchronized

1. START FROM THE PLAN
   |-> Read relevant section in ROADMAP.md or IMPLEMENTATION_PLANS*.md
   |-> Confirm subtasks you will execute
   |-> NEVER code without reading the plan first

2. WORK IN SMALL STEPS
   |-> Implement ONE subtask at a time
   |-> Update the plan IMMEDIATELY (status checkboxes, progress notes)
   |-> DO NOT leave documentation until the end

3. DOCUMENT REASONING
   |-> Add "Implementation Notes & Reasoning" as you work
   |-> Explain WHY decisions were made, not just WHAT was done
   |-> Record alternatives considered and trade-offs

4. VALIDATE CONTINUOUSLY
   |-> Run tests after each meaningful change (pytest -q)
   |-> Run targeted tests (pytest -k test_name) when appropriate
   |-> Note any test gaps or failures

5. REPORT WITH CONTEXT
   |-> Reference plan sections you advanced
   |-> List exact commands/tests executed
   |-> Point out follow-up actions or open questions

6. REQUEST CRITICAL REVIEW
   |-> After completing implementation, ask: "Is there truly no issues with [feature]?"
   |-> Invoke critical-reviewer agent when appropriate
   |-> Address findings and iterate

7. MERGE AFTER APPROVAL
   |-> Update all related documentation
   |-> Mark tasks as complete
   |-> Push to designated branch
   +-> Loop back to step 1 for next task
```

---

## Critical Requirements

### 1. Character Encoding: ASCII-Only
**EXTREMELY IMPORTANT**: Use ASCII characters ONLY in all project files.

**Why**: Unicode characters break Windows cp1252 encoding and cause crashes when tools read/write files.

**Rules:**
- Use `->` instead of Unicode arrows
- Use `[x]` instead of emoji checkmarks
- Use `[DONE]`, `[TODO]`, `[BLOCKED]` instead of emoji status indicators
- Use `-`, `*`, or `1.` for bullets instead of decorative glyphs
- Use `WARNING:`, `NOTE:`, `INFO:` instead of emoji icons
- Before editing files, scan for non-ASCII characters and normalize them

---
## Development Standards

### Coding Style
- **Python Version**: 3.10+ with type hints
- **Indentation**: 4 spaces (no tabs)
- **Naming**:
  - Functions/modules: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- **Line Length**: ~100 characters (not strict)
- **Function Size**: Keep under ~50 lines by extracting helpers
- **Imports**: Group by standard lib, third-party, local
- **Type Hints**: Required for all new functions
- **Docstrings**: Required for all public functions and classes

### Testing Standards
- Write tests beside related functionality: `tests/test_<module>.py`
- Mock external services (APIs, file I/O when appropriate)
- Use small WAV fixtures for audio tests
- Aim for >85% branch coverage on new/modified modules
- Test both happy-path and failure modes
- Add smoke tests for pipeline changes
- Keep tests fast (use mocks, small fixtures)

### Git Workflow
- All development and commits go to your designated feature branch.
- Branch naming convention: `jules/<feature-name>`
- Follow Conventional Commits format (`feat:`, `fix:`, `refactor:`, etc.)

---

## Success Checklist

Before considering any task complete, verify:

- [ ] Code follows repository coding style
- [ ] All functions have type hints and docstrings
- [ ] Tests are written and passing (`pytest -q`)
- [ ] Implementation plan is updated with progress
- [ ] "Implementation Notes & Reasoning" section is complete
- [ ] ASCII-only characters used (no Unicode)
- [ ] Changes committed with proper commit message
- [ ] Documentation updated (if applicable)
- [ ] Critical review requested
- [ ] Review findings addressed
- [ ] Changes pushed to correct branch

---

## Final Reminders

1. **Plans are living documents** - Keep them synchronized as you work
2. **Document reasoning as you go** - Don't wait until the end
3. **Test continuously** - After each meaningful change
4. **Review skeptically** - Assume issues exist until proven otherwise
5. **ASCII only** - Prevents encoding issues
6. **Edit, don't create** - Prefer editing existing files
7. **Small steps** - One subtask at a time
8. **Ask when unsure** - Better to clarify than assume
