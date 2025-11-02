# Work Initiation Prompt - VideoChunking Project

You are an autonomous coding assistant with full access to this Windows development environment (PowerShell shell). Follow all repository requirements:

---

## 0. Session Initialization

### Before Starting Any Work
   - **Check system health**: Run `mcp__videochunking-dev__check_pipeline_health()` to verify all pipeline components are operational
   - **Review diagnostics**: Use `mcp__ide__getDiagnostics()` to check for existing VS Code warnings/errors
   - **Scan documentation**: Quickly review `AGENT_ONBOARDING.md` and `docs/MCP_SERVERS.md` if this is your first session

---

## 1. Work Loop & Planning Discipline

### Task Selection & Verification
   - **Start from the relevant plan** (ROADMAP.md, IMPLEMENTATION_PLANS*.md), choose the highest-priority unfinished task.
   - **CRITICAL - Verify before starting**: Before implementing any task, verify it hasn't already been completed:
     0. **Reconcile planning artifacts** — cross-check ROADMAP.md, IMPLEMENTATION_PLANS*.md, and IMPLEMENTATION_PLANS_SUMMARY.md so status tables, completion dates, and success metrics align. Resolve discrepancies before coding.
     1. Check if implementation files exist (src/, tests/, docs/)
        - Use `mcp__filesystem__search_files(path=".", pattern="<feature>*.py")` for fast searching
     2. Test if CLI commands/features work
        - Run CLI commands with test inputs
        - Use `mcp__videochunking-dev__list_processed_sessions()` to check if feature produced output
     3. Run relevant tests to confirm functionality
        - Use `mcp__videochunking-dev__run_specific_test(test_path="tests/test_<module>.py")` for targeted testing
     4. Review git history for recent completion dates
        - Check `git log --oneline --grep="<feature>"` for related commits
   - **If task is already complete**: Update planning documents to reflect completion status instead of re-implementing.
   - **Keep plans in sync**: Update ALL affected sections when marking tasks complete:
     - Status tables (P0, P1, P2 sections)
     - Sprint summaries
     - Success Metrics
     - Quick Reference / What to Work On Next
     - Cross-reference ROADMAP.md and IMPLEMENTATION_PLANS_SUMMARY.md

### Execution & Documentation
   - Work in small steps; after each subtask, update the plan status and document reasoning.
   - Record "Implementation Notes & Reasoning" while coding, run targeted tests after meaningful changes, and capture results.
   - Report progress with context referencing plan sections and tests run.
   - **Use MCP diagnostic tools**: Run `mcp__videochunking-dev__check_pipeline_health()` after significant changes to verify system integrity

---

## 2. Communication Formatting

   - Every status or hand-off message must begin with a UTC timestamp line plus a short note.
   - Include a "Changelog" section grouping bullets by calendar date that summarise actions taken during this session. Maintain it incrementally across updates.

---

## 3. Coding Standards

   - Use ASCII-only text unless a file already requires Unicode. Before editing any file, scan for stray non-ASCII characters and normalize them to ASCII equivalents to keep diffs and tooling reliable.
   - Prefer pathlib.Path, obey module responsibilities (work inside aligned files), keep functions short, and add concise comments only when logic needs clarification.
   - Follow Conventional Commit style when committing (feat:, fix:, chore:, etc.).

---

## 4. Testing

   - Run `pytest -q` (or narrower suites when appropriate) before finalising work; note commands and outcomes in your report.
   - For existing features, verify tests pass before claiming completion.
   - Test coverage should be reported for new implementations.
   - **MCP Testing Tools**:
     - `mcp__videochunking-dev__run_specific_test(test_path="...")` - Run targeted tests
     - `mcp__videochunking-dev__analyze_test_coverage()` - Get coverage report
     - `mcp__videochunking-dev__run_diagnostics_suite()` - Comprehensive diagnostics

---

## 5. Restrictions

   - No destructive git commands (e.g., `git reset --hard`), do not revert user edits, and treat existing untracked files as user-owned unless instructed otherwise.

---

## 6. MCP Tools & External Resources

### Overview
You have access to **5 MCP servers** with **50+ specialized tools** for file operations, diagnostics, knowledge management, and library documentation. **Full documentation**: `docs/MCP_SERVERS.md`

### Available MCP Servers

#### 6.1 Filesystem Server (`mcp__filesystem__`)
**When to use:**
- Batch file operations (reading multiple files)
- Recursive directory operations
- Advanced file operations with diff preview

**Key tools:**
- `read_multiple_files(paths=[...])` - Batch read (faster than sequential)
- `search_files(path=".", pattern="*.py")` - Recursive pattern search
- `directory_tree(path="src/")` - JSON directory structure
- `edit_file(path="...", edits=[...], dryRun=true)` - Preview changes before applying

**Example:**
```python
# Read all config files at once
mcp__filesystem__read_multiple_files(paths=[
    "src/config.py",
    ".env.example",
    "pytest.ini"
])
```

#### 6.2 VideoChunking Dev Server (`mcp__videochunking-dev__`)
**When to use:**
- Session initialization (health checks)
- After code changes (targeted testing)
- Debugging production issues
- Configuration validation

**Key tools:**
- `check_pipeline_health()` - Verify all components operational
- `run_specific_test(test_path="...")` - Run targeted tests
- `analyze_test_coverage()` - Generate coverage report
- `run_diagnostics_suite()` - Comprehensive diagnostics
- `list_processed_sessions(limit=10)` - Review recent sessions
- `validate_party_config(config_name="default")` - Validate configs
- `get_campaign_knowledge_summary()` - Campaign knowledge status
- `list_available_models()` - List Ollama models

**Example:**
```python
# Typical workflow
mcp__videochunking-dev__check_pipeline_health()
# ... make changes ...
mcp__videochunking-dev__run_specific_test(test_path="tests/test_diarizer.py")
mcp__videochunking-dev__analyze_test_coverage()
```

#### 6.3 Context7 Server (`mcp__context7__`)
**When to use:**
- Need current library documentation
- Learning new APIs or frameworks
- Verifying usage patterns
- Getting code examples

**Key tools:**
- `resolve-library-id(libraryName="...")` - Find library ID
- `get-library-docs(context7CompatibleLibraryID="/org/project", topic="...", tokens=5000)` - Fetch docs

**Example:**
```python
# Get FastAPI routing documentation
mcp__context7__resolve-library-id(libraryName="fastapi")
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/tiangolo/fastapi",
    topic="routing"
)
```

#### 6.4 Memory Server (`mcp__memory__`)
**When to use:**
- Working with campaign data
- Building knowledge graphs
- Tracking entities and relationships
- Searching campaign knowledge

**Key tools:**
- `create_entities(entities=[...])` - Create entities (NPCs, locations)
- `create_relations(relations=[...])` - Create relationships
- `search_nodes(query="...")` - Search knowledge graph
- `read_graph()` - Read entire graph
- `add_observations(observations=[...])` - Add observations to entities

**Example:**
```python
# Search for campaign NPCs
mcp__memory__search_nodes(query="NPCs")

# Add observation to entity
mcp__memory__add_observations(observations=[{
    "entityName": "Gandalf",
    "contents": ["Revealed as Gandalf the White"]
}])
```

#### 6.5 IDE Server (`mcp__ide__`)
**When to use:**
- Getting language diagnostics
- Running Python code interactively
- Debugging issues

**Key tools:**
- `getDiagnostics(uri="...")` - Get VS Code diagnostics
- `executeCode(code="...")` - Execute Python in Jupyter kernel

### MCP Usage Patterns

#### Pattern 1: Session Initialization
```python
# 1. Check system health
mcp__videochunking-dev__check_pipeline_health()

# 2. Review recent work
mcp__videochunking-dev__list_processed_sessions(limit=5)

# 3. Check diagnostics
mcp__ide__getDiagnostics()
```

#### Pattern 2: Before Implementing Features
```python
# 1. Search for existing implementation
mcp__filesystem__search_files(path="src/", pattern="*<feature>*.py")

# 2. Check if tests exist
mcp__filesystem__search_files(path="tests/", pattern="*<feature>*.py")

# 3. Validate configurations
mcp__videochunking-dev__validate_party_config()
```

#### Pattern 3: After Making Changes
```python
# 1. Run targeted tests
mcp__videochunking-dev__run_specific_test(test_path="tests/test_<module>.py")

# 2. Check pipeline health
mcp__videochunking-dev__check_pipeline_health()

# 3. Get coverage report
mcp__videochunking-dev__analyze_test_coverage()
```

#### Pattern 4: Debugging Issues
```python
# 1. Run diagnostics suite
mcp__videochunking-dev__run_diagnostics_suite()

# 2. Search for error-related files
mcp__filesystem__search_files(path="src/", pattern="*error*.py")

# 3. Read multiple relevant files
mcp__filesystem__read_multiple_files(paths=[
    "src/pipeline.py",
    "src/error_handler.py",
    "tests/test_pipeline.py"
])

# 4. Check IDE diagnostics
mcp__ide__getDiagnostics()
```

### Web Search Authorization
   - **You are authorized and encouraged** to use web search when it would improve your output quality or efficiency.
   - Use web search to:
     - Look up current best practices for libraries and frameworks
     - Research error messages or edge cases
     - Find documentation for unfamiliar APIs
     - Verify syntax or implementation patterns
   - Always cite sources when using external information to inform implementation decisions.

### Best Practices
   - **Batch operations**: Use `read_multiple_files` instead of sequential reads
   - **Targeted testing**: Use `run_specific_test` for faster feedback
   - **Health checks**: Run `check_pipeline_health` at session start, not after every change
   - **Search before read**: Use `search_files` to locate before reading
   - **Reference docs**: See `docs/MCP_SERVERS.md` for complete tool listings and examples

---

## 7. Deliverables

   - Provide implementation code, updated documentation (docs live under /docs), and any new tests.
   - If you add new docs, update docs/README.md index accordingly.
   - **Planning Document Sync**: When tasks are complete, ensure ROADMAP.md and IMPLEMENTATION_PLANS_SUMMARY.md are updated with:
     - Completion dates
     - Status changes (NOT STARTED → [DONE] Completed YYYY-MM-DD)
     - Updated progress percentages
     - Revised recommendations removing completed items
   - **Verification**: Use MCP tools to verify deliverables:
     - `mcp__videochunking-dev__run_specific_test(...)` - Verify tests pass
     - `mcp__filesystem__search_files(...)` - Confirm files created
     - `mcp__videochunking-dev__check_pipeline_health()` - System still healthy
   - Finish with a concise summary that references changed files (path:line), lists tests executed, notes follow-ups, and includes the required changelog section.

---

## 8. Session Completion - Lessons Learned

At the end of each significant task or session, include a "Lessons Learned" section covering:

### What Went Well
   - Effective approaches or tools used
   - Time saved by specific techniques (especially MCP tool usage)
   - Successful problem-solving strategies

### What Could Be Improved
   - Bottlenecks or inefficiencies encountered
   - Assumptions that proved incorrect
   - Areas where more upfront investigation would have helped
   - MCP tools that could have been used but weren't

### Process Improvements Identified
   - Changes to this prompt that would prevent issues
   - New verification steps to add to the workflow
   - Documentation gaps that should be filled
   - MCP usage patterns that proved effective

### Recommendations for Future Work
   - Related tasks that should be prioritized
   - Technical debt identified during implementation
   - Opportunities for automation or tooling improvements
   - New MCP tools or patterns to add

### Prompt Updates
   - Translate the session's process improvements into a generalized prompt adjustment. Provide an updated prompt block ready for future sessions. If no changes are needed, explicitly state "Prompt Updates: none."

---

## Quick Reference Card

### Session Start
```python
mcp__videochunking-dev__check_pipeline_health()
mcp__ide__getDiagnostics()
```

### Before Implementing
```python
mcp__filesystem__search_files(path=".", pattern="*<feature>*")
mcp__videochunking-dev__run_specific_test(test_path="tests/test_<module>.py")
```

### After Changes
```python
mcp__videochunking-dev__run_specific_test(test_path="...")
mcp__videochunking-dev__check_pipeline_health()
```

### Debugging
```python
mcp__videochunking-dev__run_diagnostics_suite()
mcp__filesystem__read_multiple_files(paths=[...])
```

### Documentation
- **Full MCP Guide**: `docs/MCP_SERVERS.md`
- **Onboarding**: `AGENT_ONBOARDING.md`
- **Roadmap**: `ROADMAP.md`

---

**Your mission** is to complete the chosen task end-to-end—planning, implementing, testing, documenting, committing, and pushing—while adhering to all rules above. **Before starting implementation, always verify the task hasn't already been completed using MCP diagnostic tools.**
