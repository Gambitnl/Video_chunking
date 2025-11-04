# Claude Code Skills - Setup Complete! ✅

All skills have been successfully configured for the VideoChunking project.

## What Was Done

### ✅ 1. Fixed Existing Skills (3 skills)

Upgraded old-format skills to the new Claude Code Skills standard:

- **video-chunk** → `.claude/skills/video-chunk/SKILL.md`
  - Processes D&D session videos through complete pipeline
  - Trigger: "process", "chunk", "transcribe", "analyze" + video file

- **test-pipeline** → `.claude/skills/test-pipeline/SKILL.md`
  - Runs pytest test suite with coverage analysis
  - Trigger: "run tests", "check coverage", "validate pipeline"

- **debug-ffmpeg** → `.claude/skills/debug-ffmpeg/SKILL.md`
  - Troubleshoots FFmpeg and video processing issues
  - Trigger: "ffmpeg error", "audio extraction problem", "codec issue"

**Changes Made:**
- Renamed from `.md` to `/SKILL.md` in subdirectories
- Updated frontmatter: `skill_name` → `name`
- Enhanced descriptions with trigger phrases
- Added detailed usage examples and troubleshooting

### ✅ 2. Marketplace Skills Guide

Created comprehensive guide: `.claude/MARKETPLACE_SKILLS_GUIDE.md`

**To Install Marketplace Skills (in your Claude Code session):**
```
/plugin marketplace add anthropics/skills
/plugin install example-skills@anthropic-agent-skills
```

**Recommended Skills for This Project:**
- **mcp-builder**: Extend your custom MCP server
- **webapp-testing**: Test your Gradio UI with Playwright
- **artifacts-builder**: Create demo/docs artifacts
- **skill-creator**: Learn to build better custom skills

### ✅ 3. New Custom Skills (4 skills)

Created project-specific skills for D&D session processing:

#### **campaign-analyzer** (`.claude/skills/campaign-analyzer/SKILL.md`)
Analyze campaign knowledge from processed sessions.

**Capabilities:**
- Extract NPCs, locations, quests, items, factions
- Summarize campaign state and active quests
- Search for specific entities across sessions
- Track relationships and story arcs
- Analyze trends and frequently mentioned entities

**Triggers:**
- "What NPCs have we encountered?"
- "Show me all locations"
- "Tell me about Lord Blackthorn"
- "What happened in the last 5 sessions?"

#### **session-processor** (`.claude/skills/session-processor/SKILL.md`)
Orchestrate complete end-to-end session processing workflow.

**Capabilities:**
- Pre-flight health checks
- Audio extraction (FFmpeg)
- Transcription (Whisper)
- Speaker diarization (PyAnnote)
- IC/OOC classification (Ollama)
- Knowledge extraction
- Output generation and validation

**Triggers:**
- "Process this session video: path/to/video.mp4"
- "Run the pipeline on session_12.mkv"
- "Transcribe and analyze episode5.mp4"
- "Process all videos in recordings/ folder"

**Processing Time:** ~30 minutes for 2-hour video

#### **diagnostics-runner** (`.claude/skills/diagnostics-runner/SKILL.md`)
Comprehensive system health checks and diagnostics.

**Capabilities:**
- Dependency verification (all Python packages)
- System health (FFmpeg, Ollama, PyAnnote)
- Test suite execution with coverage
- Configuration validation (party configs, settings)
- Git status review
- Data integrity checks
- Performance benchmarks
- Cleanup recommendations

**Triggers:**
- "Run diagnostics"
- "Check system health"
- "Is everything working?"
- "Run full diagnostics before release"

**Diagnostic Levels:**
- Quick: 30 seconds
- Standard: 2 minutes
- Comprehensive: 5-10 minutes

#### **party-validator** (`.claude/skills/party-validator/SKILL.md`)
Validate and manage D&D party configuration files.

**Capabilities:**
- Validate party config structure and data
- Create new party configurations
- Update existing configs (add players/characters)
- Compare multiple configs
- Preview speaker mappings
- Troubleshoot speaker assignment issues

**Triggers:**
- "Validate the default party configuration"
- "Create new party config for oneshot"
- "Add player David to main party"
- "Why is speaker mapping wrong?"

**Validates:**
- Required fields (party_name, dm, players)
- JSON syntax correctness
- No duplicate player names
- Character assignments
- Voice characteristics for mapping

## Skills Overview

You now have **7 total skills** installed:

| Skill | Type | Purpose |
|-------|------|---------|
| video-chunk | Processing | Process session videos end-to-end |
| test-pipeline | Testing | Run pytest suite with coverage |
| debug-ffmpeg | Debugging | Troubleshoot FFmpeg issues |
| campaign-analyzer | Analysis | Analyze campaign knowledge |
| session-processor | Orchestration | Automated session workflow |
| diagnostics-runner | Health | System diagnostics & checks |
| party-validator | Configuration | Validate party configs |

## How Skills Work

### Automatic Activation

Skills are **model-invoked** - Claude automatically uses them based on your request. You don't need to explicitly call them.

**Example:**
```
User: "Process the video at recordings/session_12.mp4"

Claude automatically:
1. Recognizes this matches session-processor skill
2. Activates the skill
3. Follows the skill's instructions
4. Runs health checks, processes video, validates outputs
5. Reports results
```

### Composability

Multiple skills work together automatically:

```
User: "Run diagnostics, then process session_13.mp4 if everything looks good"

Claude uses:
1. diagnostics-runner skill → checks system health
2. session-processor skill → processes video (if health check passes)
3. campaign-analyzer skill → shows extracted knowledge
```

## Verifying Installation

### Check Skills Are Loaded

After restarting Claude Code, skills should auto-load. Verify by:

1. **Look for skill directories:**
   ```bash
   ls .claude/skills/
   ```
   Should show: campaign-analyzer, debug-ffmpeg, diagnostics-runner,
                party-validator, session-processor, test-pipeline, video-chunk

2. **Test a skill:**
   ```
   "Check if the system is ready to process"
   ```
   → Should activate diagnostics-runner skill

3. **Check logs:**
   Claude Code debug logs will show skills being loaded on startup

### Common Issues

**Skills not activating:**
- Restart Claude Code to reload skills
- Check SKILL.md files have proper YAML frontmatter
- Verify `name` field matches directory name
- Ensure descriptions include trigger phrases

**YAML frontmatter errors:**
```yaml
---
name: skill-name           # ✅ Correct
description: What it does  # ✅ Must include
---
```

```yaml
---
skill_name: skill-name     # ❌ Wrong field name
---
```

## Using Skills

### Direct Usage

Just describe what you want naturally:

```
"Process this D&D session video at recordings/ep5.mp4"
→ Uses: session-processor

"What NPCs have we encountered?"
→ Uses: campaign-analyzer

"Run the test suite"
→ Uses: test-pipeline

"Check if FFmpeg is working"
→ Uses: debug-ffmpeg

"Validate party configuration"
→ Uses: party-validator

"Is everything ready to process?"
→ Uses: diagnostics-runner
```

### Combined Workflows

```
"I'm about to process several sessions. First check system health,
 then validate the party config, then process sessions 10-15."

Claude will:
1. Use diagnostics-runner → system health check
2. Use party-validator → verify party config
3. Use session-processor → process each session
4. Use campaign-analyzer → show extracted knowledge
```

## Integration with MCP Tools

Skills leverage your custom MCP tools from `mcp_server.py`:

| Skill | MCP Tools Used |
|-------|----------------|
| session-processor | check_pipeline_health, validate_party_config, list_available_models |
| diagnostics-runner | check_pipeline_health, run_diagnostics_suite, analyze_test_coverage, validate_party_config, list_processed_sessions |
| party-validator | validate_party_config |
| campaign-analyzer | get_campaign_knowledge_summary, list_processed_sessions |
| test-pipeline | analyze_test_coverage, run_specific_test |
| debug-ffmpeg | check_pipeline_health |

**Note:** MCP tools won't be available until you reload them with `/mcp reload` or restart Claude Code after fixing the `.mcp.json` configuration.

## Next Steps

### 1. Restart Claude Code
For skills and MCP tools to load:
```bash
# In your other terminal, exit Claude Code
# Then restart: claude
```

### 2. Test Skills

Try these commands to verify skills work:

```
"Check system health"                    → diagnostics-runner
"Validate the default party config"      → party-validator
"What's in the campaign knowledge base?" → campaign-analyzer
"Run a quick test"                       → test-pipeline
```

### 3. Install Marketplace Skills (Optional)

In Claude Code:
```
/plugin marketplace add anthropics/skills
/plugin install example-skills@anthropic-agent-skills
```

### 4. Process a Session

Once everything is verified:
```
"Process the session video at recordings/session_12.mp4"
```

Skills will automatically:
- Check system health (diagnostics-runner)
- Validate party config (party-validator)
- Process the video (session-processor)
- Extract knowledge (campaign-analyzer)

## Customizing Skills

### Add More Skills

Create new skill directories:
```bash
mkdir .claude/skills/my-custom-skill
```

Create `SKILL.md`:
```yaml
---
name: my-custom-skill
description: What this skill does and when to use it (include trigger phrases)
---

# My Custom Skill

## What This Skill Does
...

## Usage
...
```

### Modify Existing Skills

Edit any `.claude/skills/*/SKILL.md` file:
- Update descriptions to change trigger matching
- Add more examples and usage patterns
- Include references to helper scripts
- Link to documentation

**After changes:** Restart Claude Code to reload

### Restrict Tool Access

Add `allowed-tools` to frontmatter:
```yaml
---
name: read-only-skill
description: Read files without modifying them
allowed-tools: Read, Grep, Glob
---
```

This restricts the skill to only those tools (security/safety).

## Documentation

### Skill Documentation Files

All skills have comprehensive `SKILL.md` files with:
- Purpose and capabilities
- Usage examples and triggers
- Command references
- Troubleshooting guides
- Integration with other skills
- Best practices

### Additional Guides

- `.claude/MARKETPLACE_SKILLS_GUIDE.md` - Installing marketplace skills
- `.claude/SKILLS_SETUP_COMPLETE.md` - This file
- [Official Docs](https://docs.claude.com/en/docs/claude-code/skills)

## Troubleshooting

### Skills Not Loading

**Check YAML syntax:**
```bash
# Each SKILL.md must start with:
---
name: skill-name
description: Description here
---
```

**Check skill directory structure:**
```
.claude/skills/
├── skill-name/
│   └── SKILL.md   # ← Must be named exactly "SKILL.md"
```

**Restart Claude Code:**
Skills are loaded at startup. Changes require restart.

### Conflicts Between Skills

If multiple skills match your request:
- Use more specific language
- Mention skill name explicitly
- Temporarily disable conflicting skills

### Performance Issues

Skills add processing overhead. For faster responses:
- Use focused, specific requests
- Disable unused skills
- Restart Claude Code periodically

## Resources

- [Claude Code Skills Docs](https://docs.claude.com/en/docs/claude-code/skills)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Creating Skills Guide](https://docs.claude.com/en/docs/claude-code/skills#creating-skills)
- [MCP Documentation](https://modelcontextprotocol.io/)

## Summary

✅ **7 skills configured and ready**
✅ **MCP configuration fixed** (`.mcp.json` in project root)
✅ **Marketplace installation guide created**
✅ **Comprehensive documentation provided**

**Next:** Restart Claude Code and start using your skills!

---

*Generated: 2024-11-03*
*Project: VideoChunking D&D Session Transcription System*
