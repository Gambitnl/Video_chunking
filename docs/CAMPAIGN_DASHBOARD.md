# Campaign Dashboard

**Status**: ✅ Implemented

Get a comprehensive health check of your campaign configuration with visual status indicators.

## Overview

The Campaign Dashboard provides a centralized view of all components tied to your selected campaign profile. It shows what's properly configured (✅), what needs attention (⚠️), and what's missing (❌) at a glance.

## How to Use

### Accessing the Dashboard

1. **Open the Web UI**: Run `python app.py`
2. **Select a Campaign**: Choose your campaign from the dropdown on the "Process Session" tab
3. **Go to "Campaign Dashboard" tab**: Click the tab to view your campaign's health status
4. **Click "Refresh Campaign Info"**: Update the dashboard with the latest configuration

### What the Dashboard Shows

The dashboard displays the overall **Campaign Health** as a percentage with a color-coded indicator:

- 🟢 **90-100%**: Excellent - Everything is properly configured
- 🟡 **70-89%**: Good - Most components are set up
- 🟠 **50-69%**: Needs Attention - Several components missing
- 🔴 **0-49%**: Critical - Major configuration needed

## Components Tracked

The dashboard monitors 6 key campaign components:

### 1. Party Configuration ✅/❌

**What it checks**: Whether a party configuration file exists for the campaign

**Location**: `models/parties/{campaign}_party.json`

**Why it matters**: The party config defines:
- Player characters (names, classes, races)
- Campaign settings (language, OOC markers)
- Knowledge extraction settings

**How to fix**: Go to "Party Config" tab and create/edit your party configuration

---

### 2. Processing Settings ✅/⚠️/❌

**What it checks**: Campaign-specific settings in the party config

**Checks for**:
- ✅ All settings configured (language, IC threshold, skip knowledge)
- ⚠️ Using default settings (not customized)
- ❌ No settings found

**Why it matters**: Processing settings control:
- Transcription language
- IC/OOC classification threshold
- Whether knowledge extraction runs automatically

**How to fix**: Edit your party config in the "Party Config" tab and adjust `campaign_settings`

---

### 3. Knowledge Base ✅/⚠️/❌

**What it checks**: Campaign knowledge extraction and storage

**Checks for**:
- ✅ Knowledge base exists with entities (quests, NPCs, locations, etc.)
- ⚠️ Knowledge base file exists but is empty
- ❌ No knowledge base found

**Location**: `models/knowledge/{campaign}_knowledge.json`

**Why it matters**: The knowledge base tracks:
- Quests (active, completed, failed)
- NPCs and their relationships
- Plot hooks and mysteries
- Locations visited
- Important items and artifacts

**How to fix**:
- Process a session with knowledge extraction enabled
- Import session notes in the "Import Session Notes" tab
- Manually create the knowledge base file

---

### 4. Character Profiles ✅/⚠️/❌

**What it checks**: Individual character profile files

**Checks for**:
- ✅ All characters in party config have profile files
- ⚠️ Some characters have profiles, some don't
- ❌ No character profiles found

**Location**: `models/character_profiles/{campaign}_{character}.json`

**Why it matters**: Character profiles contain:
- Character background and personality
- Relationships with other PCs and NPCs
- Character development over time
- Used for generating character-specific narratives

**How to fix**:
- Create profiles in the "Character Profiles" tab
- Process sessions to automatically build character context
- Manually create JSON files in the character_profiles directory

---

### 5. Processed Sessions ✅/⚠️/❌

**What it checks**: Successfully processed session outputs

**Checks for**:
- ✅ Multiple sessions processed (3+)
- ⚠️ Few sessions processed (1-2)
- ❌ No sessions processed yet

**Location**: `output/{campaign}_Session_*/`

**Why it matters**: Processed sessions include:
- Speaker diarization
- IC/OOC classification
- Formatted transcripts
- Generated narratives

**How to fix**: Process sessions in the "Process Session" tab

---

### 6. Session Narratives ✅/⚠️/❌

**What it checks**: Generated story notebooks (narrator + character POV)

**Checks for**:
- ✅ Multiple narrative files found
- ⚠️ Few narrative files found
- ❌ No narratives generated

**Location**: `output/{campaign}_Session_*/narratives/`

**Why it matters**: Narratives provide:
- Readable story format of sessions
- Third-person narrator summaries
- First-person character perspectives

**How to fix**: Generate narratives in the "Story Notebooks" tab

---

## Dashboard Output Format

### Example: Healthy Campaign (🟢 90%)

```markdown
# Campaign Dashboard: The Broken Seekers

**Campaign Health**: 🟢 90% (Excellent)

## ✅ All Good (5 components)
- Party Configuration
- Processing Settings
- Knowledge Base (23 quests, 47 NPCs, 15 locations, 12 items)
- Character Profiles (All 4 characters configured)
- Processed Sessions (8 sessions)

## ⚠️ Needs Attention (1 component)
- Session Narratives (Only 2 narratives found. Consider generating more in Story Notebooks tab)

## 📋 Next Steps
1. Generate more session narratives in Story Notebooks tab
```

### Example: New Campaign (🔴 33%)

```markdown
# Campaign Dashboard: New Campaign

**Campaign Health**: 🔴 33% (Needs major setup)

## ✅ All Good (2 components)
- Party Configuration
- Processing Settings (Language: nl, IC Threshold: 0.6)

## ❌ Missing (4 components)
- Knowledge Base: No knowledge base found. Process a session or import notes.
- Character Profiles: No character profiles found. Create in Character Profiles tab.
- Processed Sessions: No sessions processed yet. Process a session in Process Session tab.
- Session Narratives: No narratives generated yet.

## 📋 Next Steps
1. Process your first session in Process Session tab
2. Create character profiles in Character Profiles tab
3. Import early session notes if available
4. Generate narratives after processing sessions
```

## Use Cases

### For New Campaigns

**Goal**: Set up all components before processing first session

1. Check dashboard → See what's missing
2. Create party config → Define characters and settings
3. Create character profiles → Add background for each PC
4. Import early session notes → Backfill sessions 1-5 if not recorded
5. Process first recorded session → Generate full outputs
6. Check dashboard again → Verify everything is green

### For Existing Campaigns

**Goal**: Identify missing components and fill gaps

1. Check dashboard → See campaign health percentage
2. Review "Needs Attention" section → Identify specific issues
3. Follow "Next Steps" → Fix issues one by one
4. Re-check dashboard → Confirm improvements

### For Campaign Maintenance

**Goal**: Regular health checks

1. After processing each session → Check dashboard
2. Verify all components updated → Ensure knowledge base, profiles, and narratives are current
3. Monitor campaign health → Maintain 🟢 or 🟡 status

## Technical Details

### Data Sources

The dashboard reads from multiple locations:

```
models/
├── parties/{campaign}_party.json          # Party config
├── knowledge/{campaign}_knowledge.json    # Knowledge base
└── character_profiles/{campaign}_*.json   # Character profiles

output/
└── {campaign}_Session_*/
    ├── transcript_*.txt                   # Processed sessions
    └── narratives/*.md                    # Session narratives
```

### Health Calculation

```python
total_components = 6
health_percent = (components_good / total_components) * 100

if health_percent >= 90: indicator = "🟢 Excellent"
elif health_percent >= 70: indicator = "🟡 Good"
elif health_percent >= 50: indicator = "🟠 Needs Attention"
else: indicator = "🔴 Critical"
```

### Refresh Behavior

The dashboard does **not** auto-refresh. You must:
1. Click "Refresh Campaign Info" button to update
2. Or switch to another tab and back to refresh

This prevents unnecessary file system reads during normal use.

## Troubleshooting

### Dashboard Shows "No campaign selected"

**Cause**: You haven't selected a campaign on the "Process Session" tab

**Fix**: Go to "Process Session" tab → Select campaign from dropdown → Return to Dashboard

### Knowledge Base Shows as Missing But I Processed Sessions

**Cause**: Knowledge extraction was skipped during processing

**Fix**:
- Ensure "Skip Campaign Knowledge Extraction" checkbox is **unchecked** when processing
- Or import session notes with "Extract Knowledge" enabled

### Character Profiles Show Partial

**Cause**: Some characters in party config don't have profile files

**Fix**: The dashboard lists which characters are missing profiles. Create them in "Character Profiles" tab.

### Processed Sessions Count Seems Low

**Cause**: Dashboard only counts sessions matching the campaign name prefix

**Fix**: Ensure your session IDs follow the pattern `{campaign}_Session_01`, `{campaign}_Session_02`, etc.

## Future Enhancements

Planned improvements to the dashboard:

- ⏳ **Timeline View**: Chronological list of all processed sessions
- ⏳ **Quick Actions**: Direct buttons to fix issues (e.g., "Create Character Profile")
- ⏳ **Storage Usage**: Disk space used by campaign files
- ⏳ **Session Calendar**: Visual calendar of processed sessions
- ⏳ **Export Report**: Download campaign health report as PDF/Markdown

---

**Built to give you confidence in your campaign setup!**


## Developer Notes

- Core dashboard logic lives in `src/campaign_dashboard.py`.
- The Gradio UI wrapper is defined in `src/ui/campaign_dashboard_tab.py`.
- Tests covering the dashboard live in `tests/test_campaign_dashboard.py`.

