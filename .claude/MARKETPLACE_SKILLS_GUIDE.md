# Anthropic Marketplace Skills Installation Guide

This guide explains how to install and use skills from the official Anthropic skills marketplace.

## Quick Start

### 1. Add the Marketplace

In Claude Code, run:
```
/plugin marketplace add anthropics/skills
```

### 2. Browse Available Skills

View available plugins:
```
/plugin
```

### 3. Install Skill Collections

Install useful skill bundles:
```
/plugin install example-skills@anthropic-agent-skills
```

## Available Skills

### Creative & Design Skills

**algorithmic-art**
- Generates art using p5.js
- Includes randomization and particle systems
- Creates interactive visual compositions

**canvas-design**
- Creates visual art in PNG and PDF formats
- Professional design capabilities
- Export-ready outputs

**slack-gif-creator**
- Produces optimized animated GIFs
- Sized for Slack integration
- Fast rendering

### Development & Technical Skills

**artifacts-builder**
- Constructs complex HTML artifacts
- Uses React and Tailwind CSS
- Interactive components

**mcp-builder**
- Guidance for creating MCP servers
- Integrates external APIs
- Best practices and examples

**webapp-testing**
- Tests web applications using Playwright
- UI verification and validation
- Automated test generation

### Enterprise & Communication Skills

**brand-guidelines**
- Applies Anthropic's official branding
- Consistent styling across artifacts
- Logo and color palette usage

**internal-comms**
- Helps write organizational communications
- Professional tone and structure
- Templates for common messages

**theme-factory**
- Styles artifacts with professional themes
- Multiple theme options
- Consistent design language

### Meta Skills

**skill-creator**
- Educational resource for developing new skills
- Best practices and patterns
- Example structures

**template-skill**
- Basic starting template for custom skills
- Boilerplate structure
- Ready to customize

### Document Skills (Source-Available, Premium)

**document-skills**
- Word (.docx): Tracked changes, styles, tables
- PDF (.pdf): Forms, annotations, merging
- PowerPoint (.pptx): Slides, layouts, animations
- Excel (.xlsx): Formulas, charts, pivot tables

Install with:
```
/plugin install document-skills@anthropic-agent-skills
```

## Recommended Skills for VideoChunking Project

### High Priority

1. **mcp-builder**: Helpful for extending your custom MCP server (`mcp_server.py`)
2. **webapp-testing**: Test your Gradio UI (`app.py`)

### Medium Priority

3. **artifacts-builder**: Create demo/documentation artifacts
4. **skill-creator**: Learn to build better custom skills

### Optional

5. **slack-gif-creator**: Create session highlight clips for sharing
6. **canvas-design**: Generate campaign maps or visual assets

## Managing Installed Skills

### List Installed Plugins
```
/plugin list
```

### Enable/Disable Plugins
```
/plugin enable <plugin-name>
/plugin disable <plugin-name>
```

### Uninstall Plugins
```
/plugin uninstall <plugin-name>
```

### Update Plugins
```
/plugin update <plugin-name>
```

## Verification

After installation, skills become available automatically. Claude will activate them when relevant to your task.

To verify installation:
1. Check `/help` for new slash commands from plugins
2. Try invoking a skill naturally: "Create a test webapp using Playwright"
3. Check `.claude/plugins/` directory for installed files

## Troubleshooting

### Skills Not Activating

**Issue**: Claude doesn't use installed skills
**Solutions**:
- Restart Claude Code to reload plugins
- Verify installation: `/plugin list`
- Use specific trigger phrases from skill descriptions
- Check skill is enabled: `/plugin enable <name>`

### Installation Fails

**Issue**: Plugin installation errors
**Solutions**:
- Check internet connection (downloads from GitHub)
- Verify marketplace is added correctly
- Try installing with fully qualified name: `skill-name@marketplace-name`
- Check Claude Code version is up to date

### Conflicting Skills

**Issue**: Multiple skills respond to same request
**Solutions**:
- Use more specific language
- Temporarily disable conflicting skills
- Explicitly mention skill name in request

## Additional Resources

- [Official Skills Documentation](https://docs.claude.com/en/docs/claude-code/skills)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Creating Custom Skills Guide](https://docs.claude.com/en/docs/claude-code/skills#creating-skills)
- [Plugin System Documentation](https://docs.claude.com/en/docs/claude-code/plugins)

## Next Steps

After installing marketplace skills:
1. Review what each skill does
2. Test them with simple requests
3. Combine multiple skills for complex workflows
4. Create custom skills for project-specific needs

## Integration with VideoChunking Project

Marketplace skills can complement your custom skills:
- Use **mcp-builder** skill when extending `mcp_server.py`
- Use **webapp-testing** skill to test your Gradio UI
- Use **skill-creator** skill when building new project skills
- Your custom skills (video-chunk, test-pipeline, debug-ffmpeg) work alongside marketplace skills
