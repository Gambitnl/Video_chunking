# MCP Servers for VideoChunking

This document describes how to start and configure recommended MCP servers for the project. The repo ships a sample MCP config at `.claude/mcp_config.json` for local development.

## Context7 (Context7 / Upstash)

Context7 provides up-to-date library documentation for prompts and LLM context. We provide a helper config and script to run a local Context7 MCP server.

### Quick start (PowerShell)

1. Ensure Node.js and `npx` are installed.
2. (Optional) Obtain a Context7 API key at https://context7.com/dashboard and set it as an environment variable:

```powershell
$env:CONTEXT7_API_KEY = 'YOUR_API_KEY'
```

3. Start the server using the included helper script:

```powershell
.\	ools\start_context7_mcp.ps1 -ApiKey $env:CONTEXT7_API_KEY
```

The script will run `npx -y @upstash/context7-mcp --transport http --port 3000` by default.

### MCP config

A sample MCP configuration is included at `.claude/mcp_config.json`:

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

### Notes
- Running without an API key is supported but may be rate-limited.
- For more advanced configuration see upstream docs: https://github.com/mcp/upstash/context7

## Next steps
- Optionally add other MCP servers (ffmpeg, filesystem, sqlite) to `.claude/mcp_config.json` as needed.
- Add tests that mock MCP responses for unit tests and run integration tests against local MCP servers.
