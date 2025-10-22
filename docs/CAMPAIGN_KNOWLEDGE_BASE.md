# Campaign Knowledge Base

## Overview

The Campaign Knowledge Base automatically extracts and tracks campaign information across sessions, creating a living library of your D&D campaign.

## What It Tracks

### 1. **Quests**
- Active, completed, and failed quests
- Quest descriptions and objectives
- Related NPCs and locations
- Session where first mentioned

### 2. **NPCs (Non-Player Characters)**
- Character names and descriptions
- Roles (quest giver, merchant, enemy, ally, etc.)
- Current location
- Relationships with party members
- All sessions where they appeared

### 3. **Plot Hooks**
- Mysteries and unresolved elements
- Foreshadowing and hints
- Related quests and NPCs
- Resolution status

### 4. **Locations**
- Places visited or mentioned
- Descriptions and notable features
- NPCs present at each location
- All sessions where visited

### 5. **Items & Artifacts**
- Important items (not common equipment)
- Properties and significance
- Current owner
- Current location

## How It Works

### Automatic Extraction

After each session is processed:

1. **LLM Analysis**: The IC-only transcript is analyzed by your local LLM (Ollama)
2. **Entity Extraction**: Quests, NPCs, locations, items, and plot hooks are identified
3. **Knowledge Merging**: New information is merged with existing campaign knowledge
4. **Smart Updates**: Existing entities are updated, new ones are added

### Knowledge Base Storage

- Stored in `models/knowledge/{campaign}_knowledge.json`
- Persistent across sessions
- Automatically accumulates over time
- Can be edited manually if needed

## Using the Knowledge Base

### Web UI Tab: "Campaign Library"

View all your campaign knowledge in organized categories:

- **Active Quests**: Current objectives and missions
- **NPCs**: All encountered characters with descriptions
- **Plot Hooks**: Unresolved mysteries and hints
- **Locations**: All visited places
- **Items**: Important artifacts and equipment
- **Search**: Find specific information across all categories

### Editing Knowledge

The knowledge base is stored as JSON in `models/knowledge/`. You can:

- Manually edit to correct extraction errors
- Add notes and additional context
- Mark plot hooks as resolved
- Update quest statuses

## Configuration

Knowledge extraction is automatically enabled when processing sessions. To disable:

**Web UI**: Uncheck "Skip Campaign Knowledge Extraction" checkbox in Process Session tab

**Python API**:
```python
processor.process(
    input_file=audio_file,
    skip_knowledge=True  # Disable knowledge extraction
)
```

## Importing Session Notes (Backfilling Early Sessions)

Don't have recordings of your first few sessions? No problem! You can import written session notes and extract campaign knowledge from them.

### How to Import Session Notes

1. **Open the Web UI** (`python app.py`)
2. **Go to "Import Session Notes" tab**
3. **For each session**:
   - Enter Session ID (e.g., "Session_01", "Session_02")
   - Select your campaign
   - Paste your written notes or upload a .txt/.md file
   - Check "Extract Knowledge" to add entities to the knowledge base
   - Optionally check "Generate Narrative" to create a summary
   - Click "Import Session Notes"

### What Gets Extracted

The same LLM that processes audio transcripts will analyze your written notes and extract:
- 🎯 Quests mentioned in your notes
- 👥 NPCs you wrote about
- 🔓 Plot hooks and mysteries
- 📍 Locations visited
- ⚡ Important items found

### Example Session Notes Format

```markdown
Session 1 - The Adventure Begins

The party met at the Broken Compass tavern in Neverwinter. Guard Captain
Thorne approached them with a quest: find Marcus, a merchant who disappeared
on the Waterdeep Road three days ago.

NPCs Met:
- Guard Captain Thorne (stern but fair, quest giver)
- Innkeeper Mara (friendly, provided rumors)

Locations:
- The Broken Compass (tavern in Neverwinter)
- Waterdeep Road (where Marcus vanished)

Quests Started:
- Find Marcus the Missing Merchant (active)

The party set out at dawn, following the road north...
```

### Benefits of Importing Notes

✅ **Consistent Format**: Notes are processed the same as recorded sessions
✅ **Complete Timeline**: Fill in sessions 1-5 before you started recording
✅ **Cumulative Knowledge**: Imported entities merge with future recorded sessions
✅ **Searchable**: Search across all sessions (imported + recorded) in Campaign Library

### Generated Files

Imported session notes create:
- `models/knowledge/{campaign}_knowledge.json` - Updated with extracted entities
- `output/imported_narratives/{session_id}_narrator.md` - Optional narrative summary (if enabled)

## Example Knowledge Entry

### Quest
```json
{
  "title": "Rescue the Missing Merchant",
  "description": "Find Marcus who disappeared on the road to Waterdeep",
  "status": "active",
  "first_mentioned": "Session_01",
  "last_updated": "Session_03",
  "related_npcs": ["Marcus", "Guard Captain Thorne"],
  "related_locations": ["Waterdeep Road", "Dark Forest"]
}
```

### NPC
```json
{
  "name": "Guard Captain Thorne",
  "description": "Stern human captain of the city watch",
  "role": "quest_giver",
  "location": "Neverwinter",
  "relationships": {
    "Sha'ek": "Respectful, gave quest",
    "Pipira": "Suspicious of magic use"
  },
  "appearances": ["Session_01", "Session_05"]
}
```

## Benefits

- **Campaign Continuity**: Never forget important NPCs or plot threads
- **Session Prep**: DMs can review what was established in previous sessions
- **Player Reference**: Quick lookup of quest details and NPC names
- **Campaign Wiki**: Automatically builds a comprehensive campaign reference
- **Long Campaigns**: Essential for campaigns spanning many sessions

## Future Enhancements

- Relationship graphs (visualize NPC connections)
- Timeline view (chronological campaign events)
- Faction tracking
- Character development over time
- Export to PDF/Markdown for sharing

---

**Built to preserve your campaign memories!** 📚✨
