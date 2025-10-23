# Agent Onboarding Guide

> **START HERE**: New to this repository? Read this file first.
> **Created**: 2025-10-22
> **Purpose**: Single entry point for AI agents and human contributors

---

## [TARGET] You Are Here

**Repository**: D&D Session Processor (VideoChunking)
**Purpose**: Automated transcription, speaker diarization, and campaign management for tabletop RPG sessions
**Stack**: Python 3.10+, Gradio (UI), faster-whisper (transcription), PyAnnote (diarization), Ollama (LLM)
**Current State**: Production-ready core pipeline, active feature development

**Total onboarding time**: ~45-60 minutes for full context

---

## [ROCKET] Onboarding Path

### Stage 1: Essential Context (5 minutes)

**Read these files first** to understand what this project does and how we work:

#### 1.1: Project Overview
**File**: [`docs/PROJECT_SUMMARY.md`](./docs/PROJECT_SUMMARY.md)
- **What to learn**: What this project does, key features, technology stack
- **Why read this**: You need to understand the problem space before touching code
- **Key sections**: "Core Features", "Architecture Overview"

#### 1.2: Working Methodology
**File**: [`AGENTS.md`](./AGENTS.md)
- **What to learn**: Repository guidelines, coding style, testing standards, **Operator Workflow**
- **Why read this**: This defines HOW we work - required for all contributors
- **Key sections**:
  - "Operator Workflow" (lines 53-62) - **CRITICAL**: The plan -> implement -> document -> test loop
  - "AI Agent Workflows" - Critical Reviewer methodology
  - "Character Encoding: ASCII-Only" - Keep files cp1252-compatible

#### 1.3: Quick Reference
**File**: [`docs/QUICKREF.md`](./docs/QUICKREF.md)
- **What to learn**: Common commands, directory structure, configuration
- **Why read this**: Practical reference for day-to-day work

[DONE] **Stage 1 Complete**: You now understand WHAT this project does and HOW we work

---

### Stage 2: Development Standards (15 minutes)

#### 2.1: Critical Review Workflow
**File**: [`docs/CRITICAL_REVIEW_WORKFLOW.md`](./docs/CRITICAL_REVIEW_WORKFLOW.md)
- **What to learn**: How to implement features with documented reasoning and get critical review
- **Why read this**: **REQUIRED** workflow for all implementations
- **Key sections**: "Phase 1: Implementation", "Real-World Examples"

#### 2.2: Critical Reviewer Agent
**File**: [`.claude/agents/critical-reviewer.md`](./.claude/agents/critical-reviewer.md)
- **What to learn**: The skeptical review methodology, checklists, philosophy
- **Why read this**: Understand the "assume issues exist" mindset
- **Key sections**: "Review Process", "Critical Review Checklist"

[DONE] **Stage 2 Complete**: You now understand our quality standards and review process

---

### Stage 3: What to Build (20 minutes)

#### 3.1: Consolidated Roadmap
**File**: [`ROADMAP.md`](./ROADMAP.md)
- **What to learn**: All planned features (P0-P4), priorities, effort estimates
- **Why read this**: See the big picture and current priorities
- **Key sections**: "P0: Critical / Immediate", "Quick Reference Guide"

#### 3.2: Implementation Plans (if they exist)
- Look for `IMPLEMENTATION_PLANS.md` and related files
- These contain detailed subtasks, code examples, templates
- Read the plan for any feature before implementing it

[DONE] **Stage 3 Complete**: You know what needs to be built

---

## [LOOP] The Operator Workflow Loop

**CRITICAL**: This is how ALL work is done in this repository.

```
1. START FROM THE PLAN
   |
   v Read ROADMAP.md or implementation plans before coding

2. WORK IN SMALL STEPS
   |
   v Implement one subtask at a time
   v Update plan immediately (checkboxes, notes)

3. DOCUMENT REASONING
   |
   v Add "Implementation Notes & Reasoning" as you go
   v Explain WHY, not just WHAT

4. VALIDATE CONTINUOUSLY
   |
   v Run tests after each change (pytest -q)
   v Note gaps or failures

5. REPORT WITH CONTEXT
   |
   v Reference plan sections you advanced
   v List tests executed

6. REQUEST CRITICAL REVIEW
   |
   v "Is there truly no issues with [feature]?"
   v Address findings and iterate

7. MERGE AFTER APPROVAL
   |
   v Update documentation
   └-> Loop back to step 1 for next task
```

---

## [LIST] Quick Start Checklist

### First 5 Minutes
- [ ] Read `docs/PROJECT_SUMMARY.md`
- [ ] Read `AGENTS.md` (focus on "Operator Workflow")
- [ ] Read `docs/QUICKREF.md`

### Next 15 Minutes
- [ ] Read `docs/CRITICAL_REVIEW_WORKFLOW.md`
- [ ] Read `.claude/agents/critical-reviewer.md`

### Next 20 Minutes
- [ ] Read `ROADMAP.md`
- [ ] Choose a feature to work on (start with P0)

### Before You Code
- [ ] Read the specific implementation plan for your chosen feature
- [ ] Understand the subtasks and success criteria

---

## [FOLDER] Reference: Where to Find Things

### Documentation
- **Index**: `docs/README.md` - Complete documentation index
- **All docs**: `docs/` directory

### Code
- **Main pipeline**: `src/pipeline.py`
- **UI**: `app.py` - Gradio web interface
- **CLI**: `cli.py` - Command-line interface
- **Core modules**: `src/` - chunker, transcriber, diarizer, etc.
- **Tests**: `tests/`

### Planning & Roadmap
- **Roadmap**: `ROADMAP.md` - All features (P0-P4)
- **Implementation Plans**: `IMPLEMENTATION_PLANS*.md` (if they exist)

### Workflows & Standards
- **Repository guidelines**: `AGENTS.md` - Coding style, testing, **Operator Workflow**
- **Critical Review**: `docs/CRITICAL_REVIEW_WORKFLOW.md`
- **Review Agent**: `.claude/agents/critical-reviewer.md`

---

## [KEY] Key Concepts

### 1. The Processing Pipeline
```
Audio Input (M4A/MP3/WAV)
  |
  v Audio Conversion (FFmpeg -> 16kHz WAV)
  |
  v Chunking (VAD-based smart chunking)
  |
  v Transcription (faster-whisper)
  |
  v Overlap Merging
  |
  v Speaker Diarization (PyAnnote)
  |
  v IC/OOC Classification (Ollama LLM)
  |
  v Output Generation
```

### 2. Critical Reviewer Methodology
- **Skeptical by default**: Assume issues exist until proven otherwise
- **Socratic questioning**: Challenge assumptions
- **Documented reasoning**: Every decision needs a "why"
- **Learning feedback loop**: Quality compounds over time

### 3. Implementation Requirements
**All features MUST include**:
1. **Implementation Notes & Reasoning** - Design decisions, alternatives, trade-offs
2. **Code Review Findings** - Issues identified, recommendations, merge verdict
3. **Tests** - Unit tests for new code
4. **Documentation** - Update relevant docs

### 4. Priority System
- **P0**: Critical/Immediate (bugs, crashes, refactoring blockers)
- **P1**: High Impact (features that unlock major value)
- **P2**: Important Enhancements
- **P3**: Future Enhancements
- **P4**: Infrastructure & Quality

---

## [WARNING] Common Pitfalls

### [FAIL] Don't Do This
1. **Coding without reading the plan** -> You'll miss requirements
2. **Leaving documentation until the end** -> Context is lost
3. **Not keeping the plan in sync** -> Plan becomes stale
4. **Skipping tests** -> Bugs slip through
5. **Not requesting critical review** -> Issues ship to production

### [DONE] Do This Instead
1. **Start from the plan** -> Read before writing code
2. **Document as you go** -> Update plan after each subtask
3. **Keep plan synchronized** -> Plan is single source of truth
4. **Write tests continuously** -> Test as you go
5. **Request skeptical review** -> "Is there truly no issues?"

---

## [CHECK] Success Indicators

You're successfully onboarded when you can:

1. [x] Explain what this project does
2. [x] Navigate the codebase and find relevant modules
3. [x] Follow the Operator Workflow loop
4. [x] Read an implementation plan and understand subtasks
5. [x] Implement a feature with proper documentation
6. [x] Request and respond to critical review

---

## [BOOK] Reading Order Summary

```
Essential Context (5 min):
  1. docs/PROJECT_SUMMARY.md
  2. AGENTS.md (focus: Operator Workflow, ASCII-only)
  3. docs/QUICKREF.md

Development Standards (15 min):
  4. docs/CRITICAL_REVIEW_WORKFLOW.md
  5. .claude/agents/critical-reviewer.md

What to Build (20 min):
  6. ROADMAP.md
  7. IMPLEMENTATION_PLANS*.md (if they exist)
```

---

## [LIGHT] Philosophy

> "Quality emerges from dialogue, not perfection on first try. Every implementation deserves skeptical analysis, and every decision deserves a documented 'why'."

**Core principles**:
- **Plans are living documents** - Keep them in sync
- **Reasoning is required** - Document the "why"
- **Skepticism is professionalism** - "Revisions requested" is normal
- **Feedback loops create quality** - Review -> Document -> Learn -> Improve

---

**Welcome to the team!** [ROCKET]

**Next step**: Choose your first task from `ROADMAP.md` and read its implementation plan.
