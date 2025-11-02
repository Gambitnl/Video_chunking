# Session Cleanup & Validation Guide

## Overview

The Session Manager provides tools to audit and clean up your processed session data, helping you maintain a clean workspace and free up disk space.

## Quick Start

### Audit Your Sessions

To see what cleanup opportunities exist:

```bash
python cli.py sessions audit
```

This will show you:
- Total sessions and storage used
- Empty session directories
- Incomplete sessions (missing required files)
- Stale checkpoints (>7 days old)
- Potential space savings

**Save a Report:**
```bash
python cli.py sessions audit --output audit_report.md
```

### Clean Up Sessions

By default, cleanup removes:
- ✅ Empty session directories
- ✅ Stale checkpoints (>7 days old)
- ❌ Incomplete sessions (preserved by default)

**Dry Run (Preview Only):**
```bash
python cli.py sessions cleanup --dry-run
```
Shows what would be deleted without actually deleting anything.

**Interactive Cleanup:**
```bash
python cli.py sessions cleanup
```
Prompts you before deleting each category of items.

**Force Cleanup (No Prompts):**
```bash
python cli.py sessions cleanup --force
```
Deletes without prompting. Use with caution!

**Include Incomplete Sessions:**
```bash
python cli.py sessions cleanup --incomplete --force
```

## Cleanup Options

| Option | Default | Description |
|--------|---------|-------------|
| `--empty` / `--no-empty` | Yes | Delete empty session directories |
| `--incomplete` / `--no-incomplete` | No | Delete incomplete sessions |
| `--stale-checkpoints` / `--no-stale-checkpoints` | Yes | Delete checkpoints >7 days old |
| `--dry-run` | - | Preview deletions without actually deleting |
| `--force` | - | Skip confirmation prompts |
| `--output FILE` | - | Save cleanup report to markdown file |

## Examples

### Example 1: Safe Cleanup

Remove only empty directories and stale checkpoints, with confirmation:

```bash
python cli.py sessions cleanup
```

Output:
```
Running cleanup...

Found 6 empty sessions (0.00 MB):
  - 20251024_222513_test_5min_quick (0.00 MB)
  - 20251024_222505_test_5min (0.00 MB)
  ...

Delete empty sessions? [y/N]: y
Deleted 6 sessions

Found 6 stale checkpoints (0.00 MB):
  - test_5min
  - test_session
  ...

Delete stale checkpoints? [y/N]: y
Deleted 6 checkpoints

Cleanup Summary:
  Empty sessions deleted: 6
  Incomplete sessions deleted: 0
  Stale checkpoints deleted: 6
  Total space freed: 0.15 MB
```

### Example 2: Aggressive Cleanup

Remove everything including incomplete sessions:

```bash
python cli.py sessions cleanup --incomplete --force --dry-run
```

First run with `--dry-run` to preview, then remove `--dry-run` to execute.

### Example 3: Custom Cleanup

Keep stale checkpoints but remove empty sessions:

```bash
python cli.py sessions cleanup --no-stale-checkpoints --force
```

### Example 4: Audit Before Cleanup

Generate an audit report, review it, then clean up:

```bash
# 1. Audit and save report
python cli.py sessions audit --output my_audit.md

# 2. Review the markdown report
cat my_audit.md

# 3. Run cleanup based on findings
python cli.py sessions cleanup --dry-run

# 4. Execute cleanup if satisfied
python cli.py sessions cleanup --force
```

## Understanding Session States

### Valid Sessions
Complete sessions with all required files:
- `transcripts/transcript.json`
- `transcripts/diarized_transcript.json`
- `transcripts/classified_transcript.json`

### Empty Sessions
Session directories with <1KB of content. Usually from failed processing starts.

### Incomplete Sessions
Sessions missing one or more required files. May indicate:
- Processing was interrupted
- Processing failed partway through
- Intentional partial processing (e.g., skipped classification)

**Recommendation:** Review incomplete sessions before deleting to ensure you're not removing intentionally partial runs.

### Stale Checkpoints
Checkpoint directories older than 7 days. These are used for resuming interrupted processing but can be safely deleted after processing completes.

## Safety Features

1. **Dry-run mode**: Preview deletions before committing
2. **Interactive prompts**: Confirm each category before deletion
3. **Skipped sessions tracking**: See what was preserved
4. **Error reporting**: Any deletion failures are logged
5. **Markdown reports**: Document what was cleaned

## Advanced Usage

### Programmatic Access

```python
from src.session_manager import SessionManager

manager = SessionManager()

# Audit sessions
report = manager.audit_sessions()
print(f"Found {len(report.empty_sessions)} empty sessions")
print(f"Potential cleanup: {report.potential_cleanup_mb:.2f} MB")

# Cleanup with custom settings
cleanup_report = manager.cleanup(
    delete_empty=True,
    delete_incomplete=False,
    delete_stale_checkpoints=True,
    dry_run=False,
    interactive=False
)

print(f"Freed {cleanup_report.total_freed_mb:.2f} MB")
```

### Custom Checkpoint Age Threshold

```python
from src.session_manager import SessionManager

# Use 14-day threshold instead of default 7 days
manager = SessionManager(checkpoint_age_threshold_days=14)
```

## Troubleshooting

### "No sessions found"

Make sure you're running from the project root directory. The tool looks for sessions in `output/`.

### "Permission denied" errors

Ensure no processes are using the session files (e.g., audio players, text editors).

### Incomplete sessions keep appearing

If processing frequently fails partway through, investigate:
1. Check logs for error messages
2. Verify adequate disk space
3. Ensure Ollama/Whisper services are running
4. Review checkpoint system

## Best Practices

1. **Weekly audits**: Run `sessions audit` weekly to monitor growth
2. **Monthly cleanup**: Clean empty sessions and stale checkpoints monthly
3. **Review before deleting incomplete**: Some incomplete sessions may be intentional
4. **Save audit reports**: Keep reports for tracking storage trends
5. **Use dry-run first**: Always preview with `--dry-run` before force cleanup

## Related Commands

- `python cli.py config` - View current configuration
- `python cli.py check-setup` - Verify dependencies
- `python app.py` - Launch web UI for session processing
