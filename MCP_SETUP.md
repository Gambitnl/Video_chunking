# MCP Server Setup Guide

This document describes the Model Context Protocol (MCP) servers configured for the VideoChunking project.

## What is MCP?

The Model Context Protocol (MCP) is an open standard that allows AI assistants like Claude Code to interact with external tools, systems, and data sources in a standardized way. MCP servers expose tools that can be invoked during conversations to enhance capabilities.

## Installed MCP Servers

### 1. Filesystem Server
**Purpose**: Secure file operations within the project directory

**Available Tools**:
- Read, write, and search files
- List directory contents
- Navigate project structure

**Configuration**:
```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "F:\\Repos\\VideoChunking"]
}
```

### 2. Git Server
**Purpose**: Enhanced git operations and repository analysis

**Available Tools**:
- Advanced git queries
- Commit history exploration
- Branch management
- Repository statistics

**Configuration**:
```json
"git": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "F:\\Repos\\VideoChunking"]
}
```

### 3. Memory Server
**Purpose**: Persistent knowledge graph for campaign data

**Available Tools**:
- Store and retrieve entities
- Create relationships between entities
- Query knowledge graph
- Perfect for tracking NPCs, locations, quests

**Configuration**:
```json
"memory": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-memory"]
}
```

### 4. Fetch Server
**Purpose**: Web content fetching and documentation access

**Available Tools**:
- Fetch web pages
- Access API documentation
- Research capabilities

**Configuration**:
```json
"fetch": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-fetch"]
}
```

### 5. Custom VideoChunking Dev Server
**Purpose**: Project-specific development tools

**Available Tools**:

#### `analyze_test_coverage`
Run pytest with coverage analysis for the entire project.

**Example**: "Analyze test coverage for the project"

#### `run_specific_test`
Run a specific pytest test by path.

**Example**: "Run test tests/test_diarization.py::test_speaker_embedding"

**Parameters**:
- `test_path`: Path to test file or specific test

#### `list_processed_sessions`
List recently processed D&D sessions from the output directory.

**Example**: "List the last 5 processed sessions"

**Parameters**:
- `limit` (optional): Maximum number of sessions to return (default: 10)

#### `check_pipeline_health`
Check the health status of all pipeline components (FFmpeg, Ollama, PyAnnote, dependencies).

**Example**: "Check pipeline health"

#### `validate_party_config`
Validate party configuration files.

**Example**: "Validate party config default" or "Validate all party configs"

**Parameters**:
- `config_name` (optional): Specific config to validate (e.g., "default")

#### `get_campaign_knowledge_summary`
Get a summary of extracted campaign knowledge (NPCs, locations, quests, etc.).

**Example**: "Show campaign knowledge summary"

#### `run_diagnostics_suite`
Run comprehensive diagnostics (tests, dependencies, git status).

**Example**: "Run full diagnostics"

#### `list_available_models`
List available Ollama models for IC/OOC classification.

**Example**: "What Ollama models are available?"

**Configuration**:
```json
"videochunking-dev": {
  "command": "python",
  "args": ["F:\\Repos\\VideoChunking\\mcp_server.py"]
}
```

## How to Use MCP Tools

Once the servers are running (after restarting Claude Code), you can use them naturally in conversation:

### Examples:

1. **Test Coverage**:
   - "Analyze test coverage for the project"
   - "Run the test suite with coverage"

2. **Session Management**:
   - "List the last 10 processed sessions"
   - "Show me recently processed D&D sessions"

3. **Health Checks**:
   - "Check pipeline health"
   - "Are all dependencies installed?"

4. **Party Configuration**:
   - "Validate the default party config"
   - "Check all party configuration files"

5. **Campaign Knowledge**:
   - "Show campaign knowledge summary"
   - "How many NPCs have we tracked?"

6. **Diagnostics**:
   - "Run full diagnostics"
   - "What's the project status?"

7. **Git Operations** (via git server):
   - "Show recent commits"
   - "What files have changed?"

8. **Memory Operations** (via memory server):
   - "Store NPC: Lord Blackthorn, evil wizard from Session 3"
   - "What NPCs do we know about?"

## Activating MCP Servers

**To activate the MCP servers**, you need to **restart Claude Code**:

1. Exit the current Claude Code session
2. Restart Claude Code CLI
3. The MCP servers will auto-load from `.claude/mcp_config.json`

On first run, npx will download the required packages (using the `-y` flag for auto-confirmation).

## Verifying MCP Servers

After restarting, Claude Code will have access to tools with the `mcp__` prefix:

- `mcp__filesystem__*`
- `mcp__git__*`
- `mcp__memory__*`
- `mcp__fetch__*`
- `mcp__videochunking-dev__*`

You can test by asking: "What MCP tools are available?" or "Check pipeline health"

## Troubleshooting

### Server Not Loading
- Verify `.claude/mcp_config.json` has valid JSON syntax
- Check that Node.js and npm are installed: `node --version`
- Ensure Python is available: `python --version`
- Check Claude Code logs for error messages

### FastMCP Not Found
If the custom server fails:
```bash
pip install fastmcp
```

### NPX Package Download Issues
On first run, npx downloads packages. If this fails:
```bash
# Manually install packages
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-git
npm install -g @modelcontextprotocol/server-memory
npm install -g @modelcontextprotocol/server-fetch
```

Then update `.claude/mcp_config.json` to use direct commands instead of npx.

## Configuration File Location

`.claude/mcp_config.json` - Contains all MCP server configurations

## Security Notes

- **Filesystem server**: Restricted to `F:\Repos\VideoChunking` directory only
- **Git server**: Repository-scoped operations only
- **Memory server**: Local knowledge graph storage
- **Custom server**: Read-only operations for most tools (except test runs)

## Future Enhancements

Potential additional tools for the custom MCP server:
- Session processing progress tracking
- Campaign timeline generation
- Character relationship graph visualization
- Audio quality analysis
- Transcription accuracy metrics

## Additional Resources

- [Official MCP Documentation](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Server Repository](https://github.com/modelcontextprotocol/servers)
