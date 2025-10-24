# Start Context7 MCP server (Windows PowerShell helper)
# Requires Node.js and npx available in PATH.

param(
  [string]$ApiKey = $env:CONTEXT7_API_KEY
)

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
  Write-Error "npx is not available in PATH. Install Node.js (which includes npx) and try again."
  exit 1
}

if (-not $ApiKey) {
  Write-Host "No CONTEXT7_API_KEY provided; running without API key (rate limits may apply)."
}

$env:CONTEXT7_API_KEY = $ApiKey

Write-Host "Starting Context7 MCP server via npx @upstash/context7-mcp..."

# Use Start-Process so logs appear in a new console; remove -NoNewWindow to open separate window
Start-Process npx -ArgumentList("-y", "@upstash/context7-mcp@latest", "--transport", "http", "--port", "3000") -NoNewWindow -Wait
