# Party Configuration Guide

The D&D Session Processor supports **Party Configurations** - pre-configured character and player information that can be reused across multiple sessions.

## Benefits

1. **Faster Setup**: No need to manually enter character/player names for each session
2. **Consistency**: Same names and spellings across all sessions
3. **Better Classification**: Rich character descriptions help the IC/OOC classifier understand context
4. **Character Aliases**: Supports multiple names/nicknames for better recognition

## Default Party: "The Broken Seekers"

The system includes a default party configuration based on the Gaia Adventures campaign:

### Characters

1. **Sha'ek Mindfa'ek** (The Broken)
   - **Player**: Player1
   - **Race**: Adar (from Adar)
   - **Class**: Cleric of Ioun
   - **Aliases**: Sha'ek, The Broken, The Defect
   - **Description**: A hardened veteran cleric with glowing green eyes. Survived the Smelting ritual, connected to Quori spirit Golos. Wears heavy chain mail, carries a large bag and shield with Ioun's emblem.

2. **Pipira Shimmerlock** (Pip)
   - **Player**: Player2
   - **Race**: Gnome
   - **Class**: Wizard
   - **Aliases**: Pip, Pipira
   - **Description**: An ambitious gnome student wizard. Perceptive, eager to learn, fond of experiments and tinkering with mechanical objects.

3. **Fan'nar Khe'Lek** (Pas'Ta)
   - **Player**: Player3
   - **Race**: Winter Eladrin
   - **Class**: Handyman/Ranger
   - **Aliases**: Pas'Ta, Fan'nar
   - **Description**: Snow-white skin, blond hair, wears fur clothing. Works for Culdor Academy. Sharp-witted, mysterious, prefers working alone. Uses archery and flail, carries a magical black leather Grimoire.

4. **Furnax**
   - **Player**: Companion
   - **Race**: Frost Hellhound
   - **Class**: Beast Companion
   - **Aliases**: Furnax
   - **Description**: Pip's companion - Black with dark blue stripes, cold aura. Unruly but well-trained, intelligent, rescued by the academy.

### Campaign Details

- **Campaign**: Gaia Adventures
- **DM**: DM
- **Notes**: Party exploring Gaia. Suspicious of non-Gaian entities. Connected to Culdor Academy. Characters have experienced magical chaos events.

## Using Party Configurations

### Web UI (Gradio)

1. Launch the web interface: `python app.py`
2. In the "Party Configuration" dropdown, select `default` (or your custom party)
3. The character and player name fields will be ignored when a party is selected
4. Click "Process Session" as usual

### Command Line

```bash
# List available parties
python cli.py list-parties

# Show party details
python cli.py show-party default

# Process with party config
python cli.py process recording.m4a --party default --session-id "session1"
```

### Python API

```python
from src.pipeline import DDSessionProcessor

# Create processor with party config
processor = DDSessionProcessor(
    session_id="my_session",
    party_id="default"  # Uses The Broken Seekers
)

# Process as usual
result = processor.process(input_file="session.m4a")
```

## Creating Custom Party Configurations

### Method 1: Edit JSON File

Party configurations are stored in `models/parties.json`. You can add new parties by editing this file:

```json
{
  "default": { ... },
  "my_party": {
    "party_name": "The Dragon Slayers",
    "dm_name": "DM Mike",
    "campaign": "Lost Mines of Phandelver",
    "characters": [
      {
        "name": "Gandor the Brave",
        "player": "Sarah",
        "race": "Human",
        "class_name": "Fighter",
        "description": "A brave warrior from the north",
        "aliases": ["Gandor", "The Brave One"]
      }
    ],
    "notes": "A group of adventurers exploring the Sword Coast"
  }
}
```

### Method 2: Python API

```python
from src.party_config import PartyConfigManager, Party, Character

# Create manager
manager = PartyConfigManager()

# Define your party
my_party = Party(
    party_name="The Dragon Slayers",
    dm_name="DM Mike",
    campaign="Lost Mines",
    characters=[
        Character(
            name="Gandor the Brave",
            player="Sarah",
            race="Human",
            class_name="Fighter",
            description="A brave warrior from the north",
            aliases=["Gandor", "The Brave One"]
        ),
        Character(
            name="Elara Moonwhisper",
            player="Tom",
            race="Elf",
            class_name="Wizard",
            description="A wise elven mage",
            aliases=["Elara"]
        )
    ],
    notes="A group of adventurers exploring the Sword Coast"
)

# Save it
manager.add_party("dragon_slayers", my_party)

# Use it
from src.pipeline import DDSessionProcessor
processor = DDSessionProcessor(
    session_id="session1",
    party_id="dragon_slayers"
)
```

## Character Field Descriptions

- **name**: Full character name (required)
- **player**: Player name or "DM", "Companion", "NPC" (required)
- **race**: Character race (required)
- **class_name**: Character class (required)
- **description**: Detailed description to help IC/OOC classification (optional)
- **aliases**: List of alternative names/nicknames the character might be called (optional)

## Tips for Best Results

1. **Include Aliases**: Add common nicknames and shortened names to help recognition
2. **Detailed Descriptions**: Rich descriptions help the LLM understand character context
3. **Mark Companions**: Use "Companion" as player name for pets/familiars
4. **Campaign Notes**: Add context notes to help classification understand campaign themes

## Managing Multiple Parties

If you run multiple campaigns, create separate party configurations:

```bash
# List all parties
python cli.py list-parties

# Switch between parties when processing
python cli.py process session.m4a --party campaign1
python cli.py process other.m4a --party campaign2
```

## Party Config vs Manual Entry

**Use Party Config when**:
- Running recurring campaign with same characters
- Want consistent naming across sessions
- Need detailed character context for better classification
- Have complex character names or many aliases

**Use Manual Entry when**:
- One-shot sessions with new characters
- Testing the system
- Characters change frequently
- Quick processing without setup

## Example Workflow

```bash
# First time: Set up your party
python cli.py show-party default  # View the default party

# Edit models/parties.json to customize with your actual character names

# Process sessions with your party
python cli.py process session1.m4a --party default --session-id s1
python cli.py process session2.m4a --party default --session-id s2
python cli.py process session3.m4a --party default --session-id s3

# All sessions will use consistent character information!
```

## Import/Export Party Configurations

You can save and share party configurations using import/export.

### Export a Party

```bash
# Export a single party
python cli.py export-party default my_party.json

# Export all parties (backup)
python cli.py export-all-parties backup.json
```

### Import a Party

```bash
# Import with original party ID
python cli.py import-party my_party.json

# Import with custom party ID
python cli.py import-party my_party.json --party-id campaign2
```

### Web UI Import/Export

In the Gradio web interface:

1. Launch the web UI: `python app.py`
2. Go to the **Party Management** tab (next to Speaker Management)
3. You can:
   - **Export Party**: Select a party from the dropdown and click "Export Party" to download as JSON
   - **Import Party**: Upload a party JSON file and optionally specify a custom party ID

**Note**: The Web UI shows import/export functionality but you need to refresh the page after importing a new party to see it in the party selection dropdown.

### Use Cases

- **Backup**: Export all parties before making changes
- **Sharing**: Share your party config with other DMs/players
- **Multiple Campaigns**: Import different party configs for different campaigns
- **Version Control**: Keep party configs in your own git repository

## Storage Location

Party configurations are stored in: `models/parties.json`

**Important**: This file is NOT tracked in git (it's in .gitignore) to keep your party data private. Use export/import to backup or share your configurations.

An example file is provided at: `models/parties.json.example`

## Validation

The system validates party configurations when loading:
- All required fields must be present
- Character names must be unique within a party
- At least one character must be defined

If validation fails, you'll see an error message indicating what needs to be fixed.

---

**Next Steps**: Edit `models/parties.json` to add your own party configuration, or modify the default to match your campaign!
