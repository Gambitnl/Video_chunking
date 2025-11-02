# MCP Servers for VideoChunking

This document describes the MCP (Model Context Protocol) servers configured for this project, what tools they provide, and when they should be used by AI agents.

---

## Overview

MCP servers provide specialized tools that extend AI agent capabilities beyond standard file operations. This project has **5 MCP servers** configured with **50+ specialized tools** for diagnostics, file operations, knowledge management, and library documentation.

**Quick Reference:**
- All MCP tools follow the naming pattern: `mcp__<server>__<tool_name>`
- Tools are automatically available in Claude Code sessions
- No manual server management required for configured servers

---

## Available MCP Servers

### 1. Filesystem Server (`mcp__filesystem__`)

**Purpose:** File system operations within allowed directories

**When to use:**
- Batch file operations (read multiple files)
- Recursive directory operations
- Advanced file operations (edit with diff preview)
- When you need file metadata or directory trees

**Key Tools:**

**File Operations:**
- `read_text_file` - Read text files (supports head/tail for large files)
- `read_media_file` - Read images/audio as base64
- `read_multiple_files` - Batch read multiple files (more efficient than sequential reads)
- `write_file` - Create or overwrite files
- `edit_file` - Line-based editing with diff preview

**Directory Operations:**
- `create_directory` - Create directory structures
- `list_directory` - List directory contents
- `list_directory_with_sizes` - List with file sizes (sortable)
- `directory_tree` - Recursive JSON tree view
- `move_file` - Move/rename files and directories

**Search & Info:**
- `search_files` - Recursive pattern search (e.g., `*.py`)
- `get_file_info` - File metadata (size, timestamps, permissions)
- `list_allowed_directories` - Show accessible paths

**Agent Usage Example:**
```python
# Batch read multiple config files
mcp__filesystem__read_multiple_files(paths=[
    "src/config.py",
    ".env.example",
    "pytest.ini"
])

# Search for test files
mcp__filesystem__search_files(path=".", pattern="test_*.py")

# Get directory structure
mcp__filesystem__directory_tree(path="src/")
```

---

### 2. VideoChunking Dev Server (`mcp__videochunking-dev__`)

**Purpose:** Project-specific diagnostics and pipeline management

**When to use:**
- Checking pipeline health
- Running specific tests
- Analyzing test coverage
- Validating configurations
- Reviewing processed sessions
- Debugging production issues

**Key Tools:**

**Diagnostics:**
- `check_pipeline_health` - Verify all pipeline components are operational
- `run_diagnostics_suite` - Comprehensive project diagnostics (tests, coverage, dependencies)
- `analyze_test_coverage` - Run pytest with coverage analysis

**Testing:**
- `run_specific_test` - Run specific test by path (e.g., `tests/test_pipeline.py::test_name`)

**Campaign Management:**
- `list_processed_sessions` - List recent D&D sessions with metadata
- `validate_party_config` - Validate party configuration files
- `get_campaign_knowledge_summary` - Get campaign knowledge base summary

**Models:**
- `list_available_models` - List installed Ollama models for IC/OOC classification

**Agent Usage Example:**
```python
# Before starting work - verify system health
mcp__videochunking-dev__check_pipeline_health()

# After making changes - run targeted tests
mcp__videochunking-dev__run_specific_test(test_path="tests/test_diarizer.py")

# Investigate sessions
mcp__videochunking-dev__list_processed_sessions(limit=5)

# Validate configurations
mcp__videochunking-dev__validate_party_config(config_name="default")
```

---

### 3. Context7 Server (`mcp__context7__`)

**Purpose:** Fetch up-to-date library documentation

**When to use:**
- Need current API documentation
- Learning new library features
- Verifying correct usage patterns
- Getting code examples for libraries

**Key Tools:**
- `resolve-library-id` - Find Context7-compatible library ID from package name
- `get-library-docs` - Fetch documentation for a specific library version

**Agent Usage Example:**
```python
# First, resolve the library ID
mcp__context7__resolve-library-id(libraryName="fastapi")
# Returns: "/tiangolo/fastapi"

# Then fetch documentation
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/tiangolo/fastapi",
    topic="routing",
    tokens=5000
)
```

**Setup:**

1. (Optional) Get API key at https://context7.com/dashboard
2. Set environment variable:
   ```powershell
   $env:CONTEXT7_API_KEY = 'YOUR_API_KEY'
   ```
3. Start server:
   ```powershell
   .\tools\start_context7_mcp.ps1 -ApiKey $env:CONTEXT7_API_KEY
   ```

**Notes:**
- Works without API key but may be rate-limited
- Supports versioned library queries (e.g., `/vercel/next.js/v14.3.0`)

---

### 4. Memory Server (`mcp__memory__`)

**Purpose:** Knowledge graph operations for campaign management

**When to use:**
- Tracking campaign entities (NPCs, locations, quests)
- Building relationships between entities
- Searching campaign knowledge
- Maintaining character profiles
- Documenting plot developments

**Key Tools:**

**Create:**
- `create_entities` - Create new entities (NPCs, locations, items)
- `create_relations` - Create relationships between entities
- `add_observations` - Add new observations to existing entities

**Read:**
- `read_graph` - Read entire knowledge graph
- `search_nodes` - Search for entities by query
- `open_nodes` - Open specific nodes by name

**Delete:**
- `delete_entities` - Delete entities and their relations
- `delete_observations` - Remove specific observations
- `delete_relations` - Delete relationships

**Agent Usage Example:**
```python
# Create campaign entities
mcp__memory__create_entities(entities=[
    {
        "name": "Thorin Oakenshield",
        "entityType": "Character",
        "observations": ["Dwarf warrior", "Seeking lost treasure"]
    }
])

# Create relationships
mcp__memory__create_relations(relations=[
    {
        "from": "Thorin Oakenshield",
        "to": "Lonely Mountain",
        "relationType": "seeks to reclaim"
    }
])

# Search campaign knowledge
mcp__memory__search_nodes(query="NPCs in Chapter 3")

# Read entire graph
mcp__memory__read_graph()
```

---

### 5. IDE Server (`mcp__ide__`)

**Purpose:** VS Code integration and Jupyter code execution

**When to use:**
- Getting language diagnostics from VS Code
- Running Python code in Jupyter notebooks
- Debugging code issues
- Interactive data exploration

**Key Tools:**
- `getDiagnostics` - Get language diagnostics (errors, warnings)
- `executeCode` - Execute Python code in Jupyter kernel

**Agent Usage Example:**
```python
# Get diagnostics for a file
mcp__ide__getDiagnostics(uri="file:///path/to/file.py")

# Execute Python code in Jupyter
mcp__ide__executeCode(code="import pandas as pd\ndf.head()")
```

---

## Agent Usage Scenarios

### Scenario 1: Starting a New Task
```python
# 1. Check system health
mcp__videochunking-dev__check_pipeline_health()

# 2. Get current VS Code diagnostics
mcp__ide__getDiagnostics()

# 3. Review recent sessions
mcp__videochunking-dev__list_processed_sessions(limit=5)
```

### Scenario 2: Debugging Pipeline Issues
```python
# 1. Run diagnostics
mcp__videochunking-dev__run_diagnostics_suite()

# 2. Check test coverage
mcp__videochunking-dev__analyze_test_coverage()

# 3. Search for error-related files
mcp__filesystem__search_files(path="src/", pattern="*error*.py")

# 4. Read relevant files
mcp__filesystem__read_multiple_files(paths=[
    "src/pipeline.py",
    "src/error_handler.py"
])
```

### Scenario 3: Learning a New Library
```python
# 1. Resolve library ID
mcp__context7__resolve-library-id(libraryName="gradio")

# 2. Get documentation
mcp__context7__get-library-docs(
    context7CompatibleLibraryID="/gradio-app/gradio",
    topic="components"
)
```

### Scenario 4: Campaign Knowledge Management
```python
# 1. Search existing entities
mcp__memory__search_nodes(query="locations")

# 2. Read full knowledge graph
mcp__memory__read_graph()

# 3. Add new observations
mcp__memory__add_observations(observations=[
    {
        "entityName": "Gandalf",
        "contents": ["Revealed identity as Gandalf the White"]
    }
])
```

---

## Best Practices for Agents

### When to Use MCP Tools vs. Standard Tools

**Use MCP Filesystem Tools When:**
- Reading multiple files at once (batch operations)
- Need directory tree structure
- Require file metadata
- Performing recursive searches

**Use Standard Tools When:**
- Single file read/write
- Simple grep/glob operations
- File already known from context

**Use VideoChunking-Dev Tools When:**
- Starting a session (health check)
- After code changes (run tests)
- Investigating issues (diagnostics)
- Before committing (coverage analysis)

**Use Memory Tools When:**
- Working with campaign data
- Building knowledge graphs
- Tracking entities and relationships
- Searching campaign knowledge

### Performance Tips

1. **Batch Operations:** Use `read_multiple_files` instead of sequential reads
2. **Targeted Tests:** Use `run_specific_test` for faster feedback
3. **Scoped Searches:** Use `search_files` with specific patterns instead of reading entire directories
4. **Health Checks:** Run `check_pipeline_health` at session start, not after every change

---

## Configuration

### Sample MCP Config

Located at `.claude/mcp_config.json`:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"],
      "env": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
      }
    }
  }
}
```

### Adding Additional Servers

1. Edit `.claude/mcp_config.json`
2. Add server configuration following the schema
3. Restart Claude Code session
4. Verify with `ListMcpResourcesTool`

---

## Troubleshooting

### Tools Not Available

1. Check `.mcp.json` or `.claude/mcp_config.json` exists
2. Verify server process is running
3. Restart Claude Code session
4. Check server logs

### Permission Errors (Filesystem)

- Use `list_allowed_directories` to see accessible paths
- Operations are restricted to allowed directories
- Configure allowed directories in server setup

### Context7 Rate Limiting

- Obtain API key from https://context7.com/dashboard
- Set `CONTEXT7_API_KEY` environment variable
- Restart server with API key

---

## Reference

**All MCP Tools:** 50+ tools across 5 servers
**Tool Naming Pattern:** `mcp__<server>__<tool_name>`
**Configuration File:** `.claude/mcp_config.json`
**Documentation:** This file

**Quick Links:**
- Context7 Setup: https://github.com/mcp/upstash/context7
- MCP Protocol: https://modelcontextprotocol.io/
- Project Diagnostics: Use `mcp__videochunking-dev__run_diagnostics_suite()`
