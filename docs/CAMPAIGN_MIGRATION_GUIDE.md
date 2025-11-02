# Campaign Migration Guide

## Overview

This guide helps you migrate existing session data, character profiles, and narratives to use the new campaign system. If you've been using the D&D Session Processor before campaigns were introduced, follow this guide to organize your data by campaign.

---

## Why Migrate?

The campaign system provides:
- **Organization**: Group sessions, profiles, and narratives by campaign
- **Filtering**: View only data relevant to the active campaign in the UI
- **Isolation**: Keep different campaigns separate (no data leakage)
- **Knowledge**: Campaign-specific knowledge bases that don't mix adventures

---

## Before You Begin

### Prerequisites

1. **Backup your data** (recommended):
   ```bash
   # Create a backup of your entire output directory
   cp -r output output_backup_$(date +%Y%m%d)

   # Or on Windows
   xcopy output output_backup_%date:~-4,4%%date:~-7,2%%date:~-10,2% /E /I
   ```

2. **Verify you have campaigns defined**:
   - Check `models/campaigns.json` exists
   - Ensure the campaign you want to use is listed

3. **Identify your campaign ID**:
   ```bash
   python cli.py config
   ```
   Look for campaigns in the output, or check `models/campaigns.json` directly.

---

## Migration Workflow

### Step 1: Preview Changes (Dry Run)

Always start with a dry run to see what will change:

```bash
# Preview session migration
python cli.py campaigns migrate-sessions broken_seekers --dry-run

# Preview profile migration
python cli.py campaigns migrate-profiles broken_seekers --dry-run

# Preview narrative migration
python cli.py campaigns migrate-narratives broken_seekers --dry-run
```

### Step 2: Migrate Sessions

Add `campaign_id` metadata to your session output files:

```bash
# Migrate ALL sessions
python cli.py campaigns migrate-sessions broken_seekers

# Migrate only specific sessions (by pattern)
python cli.py campaigns migrate-sessions broken_seekers --filter "Session_*"

# Save a report
python cli.py campaigns migrate-sessions broken_seekers --output migration_report.md
```

**What this does:**
- Adds `campaign_id`, `campaign_name`, and `party_id` to `*_data.json` metadata
- Skips sessions that already have `campaign_id` assigned
- Does NOT modify actual transcript content

### Step 3: Migrate Character Profiles

Assign campaign ownership to character profiles:

```bash
# Migrate ALL profiles without campaign_id
python cli.py campaigns migrate-profiles broken_seekers

# Migrate specific characters only
python cli.py campaigns migrate-profiles broken_seekers --characters "Sha'ek,Pipira,Fan'nar"

# Save a report
python cli.py campaigns migrate-profiles broken_seekers --output profiles_migration.md
```

**What this does:**
- Sets `campaign_id` field for profiles
- Preserves existing `campaign_name` text
- Skips profiles already assigned to ANY campaign (won't override)

### Step 4: Migrate Narratives

Add YAML frontmatter to existing narrative markdown files:

```bash
# Add frontmatter to ALL narratives
python cli.py campaigns migrate-narratives broken_seekers

# Save a report
python cli.py campaigns migrate-narratives broken_seekers --output narratives_migration.md
```

**What this does:**
- Prepends YAML frontmatter with `campaign_id`, `campaign_name`, and `session_id`
- Skips files that already have frontmatter (start with `---`)
- Preserves all existing content

---

## Example Output

### Before Migration

**Session metadata** (`output/20251101_120000_Session_01/Session_01_data.json`):
```json
{
  "metadata": {
    "session_id": "Session_01",
    "character_names": ["Sha'ek", "Pipira"],
    "player_names": ["Player1", "Player2"]
  }
}
```

**Character profile** (`models/character_profiles/Shaek_Mindfaek.json`):
```json
{
  "name": "Sha'ek Mindfa'ek",
  "campaign": "Gaia Adventures",
  "player": "Player1"
}
```

**Narrative** (`output/.../narratives/session_01.md`):
```markdown
# Session 1 - The Storm's Aftermath

The party met Professor Artex...
```

### After Migration

**Session metadata**:
```json
{
  "metadata": {
    "session_id": "Session_01",
    "campaign_id": "broken_seekers",      ← NEW
    "campaign_name": "The Broken Seekers", ← NEW
    "party_id": "default",                 ← NEW
    "character_names": ["Sha'ek", "Pipira"],
    "player_names": ["Player1", "Player2"]
  }
}
```

**Character profile**:
```json
{
  "name": "Sha'ek Mindfa'ek",
  "campaign_id": "broken_seekers",   ← NEW
  "campaign_name": "Gaia Adventures", ← RENAMED from "campaign"
  "player": "Player1"
}
```

**Narrative**:
```markdown
---
campaign_id: broken_seekers
campaign_name: The Broken Seekers
session_id: Session_01
migrated_at: 2025-11-01T15:30:00
---

# Session 1 - The Storm's Aftermath

The party met Professor Artex...
```

---

## Advanced Usage

### Migrate Multiple Campaigns

If you have data from different campaigns mixed together, you'll need to manually separate them:

```bash
# Migrate first campaign
python cli.py campaigns migrate-sessions campaign_alpha --filter "Alpha_*"
python cli.py campaigns migrate-profiles campaign_alpha --characters "Alice,Bob"

# Migrate second campaign
python cli.py campaigns migrate-sessions campaign_beta --filter "Beta_*"
python cli.py campaigns migrate-profiles campaign_beta --characters "Charlie,Dave"
```

### Undo a Migration

If you made a mistake, you can manually edit the JSON files:

**For sessions**: Remove the `campaign_id`, `campaign_name`, and `party_id` fields from metadata

**For profiles**: Set `campaign_id` to `null` or remove it entirely

**For narratives**: Delete the frontmatter block (everything between the `---` markers)

Or restore from your backup:
```bash
cp -r output_backup_20251101/* output/
```

### Check Migration Status

View what's been migrated:

```bash
# Count sessions with campaign_id
find output -name "*_data.json" -exec grep -l "campaign_id" {} \; | wc -l

# Count profiles with campaign_id
grep -r "campaign_id" models/character_profiles/ | grep -v "null" | wc -l

# Count narratives with frontmatter
find output -name "*.md" -path "*/narratives/*" -exec head -1 {} \; | grep -c "^---$"
```

---

## Troubleshooting

### "Campaign 'xyz' not found"

**Problem**: The campaign ID doesn't exist in `models/campaigns.json`

**Solution**: Create the campaign first, or use an existing campaign ID

### "Profile 'Character Name' already assigned to campaign 'abc'"

**Problem**: Character profile already has a `campaign_id` set

**Solution**: This is intentional protection against accidental overrides. If you want to reassign:
1. Edit the profile JSON file manually
2. Set `campaign_id` to `null`
3. Run migration again

### No sessions found

**Problem**: No `*_data.json` files in output directory

**Solution**: Ensure you're running from the project root and your sessions actually exist

### Dry run shows 0 migrations

**Possible causes**:
1. All data is already migrated (has `campaign_id`)
2. Your filter pattern doesn't match any files
3. Campaign ID is invalid

**Solution**: Check the dry-run output for "skipped" messages

---

## Best Practices

1. **Always dry-run first**: Use `--dry-run` to preview changes
2. **Migrate in order**: Sessions → Profiles → Narratives
3. **Save reports**: Use `--output report.md` to document what changed
4. **Test incrementally**: Migrate a few sessions first, verify in UI, then migrate all
5. **One campaign at a time**: Don't try to migrate multiple campaigns simultaneously
6. **Backup first**: Always create a backup before mass migrations

---

## Migration Checklist

- [ ] Backup `output/` and `models/` directories
- [ ] Verify campaign exists in `models/campaigns.json`
- [ ] Run dry-run for sessions (`--dry-run`)
- [ ] Migrate sessions (`migrate-sessions`)
- [ ] Run dry-run for profiles (`--dry-run`)
- [ ] Migrate character profiles (`migrate-profiles`)
- [ ] Run dry-run for narratives (`--dry-run`)
- [ ] Migrate narratives (`migrate-narratives`)
- [ ] Test in UI: verify sessions/profiles filter correctly
- [ ] Save migration reports for documentation
- [ ] Delete backup after confirming everything works

---

## FAQ

**Q: Will migration change my actual transcript text?**
A: No. Migrations only add metadata to JSON files and frontmatter to markdown files. Your actual transcript content is never modified.

**Q: What if I don't want to migrate some sessions?**
A: Use the `--filter` option to select specific sessions, or simply skip them. Sessions without `campaign_id` will work fine (shown as "uncategorized" in UI).

**Q: Can I migrate the same data to multiple campaigns?**
A: No. Each session/profile can only belong to one campaign. If you need data in multiple campaigns, you'll need to duplicate the files manually.

**Q: What happens to new sessions I process?**
A: New sessions automatically include `campaign_id` if you select a campaign in the UI or pass `--campaign` flag to CLI.

**Q: Is migration reversible?**
A: Technically yes (manually edit files or restore backup), but it's easier to just get it right the first time using dry-run.

---

## Related Documentation

- [Campaign Lifecycle Implementation](CAMPAIGN_LIFECYCLE_IMPLEMENTATION.md) - Technical details
- [Session Cleanup Guide](SESSION_CLEANUP_GUIDE.md) - Manage old sessions
- [Usage Guide](USAGE.md) - General application usage

---

*Last Updated: 2025-11-01*
