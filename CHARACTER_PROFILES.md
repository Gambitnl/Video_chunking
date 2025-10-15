# Character Profiles Guide

Automatic character profiling and overview generation from campaign logs and session transcripts.

## Overview

The Character Profile system allows you to:
- **Track character development** across multiple sessions
- **Document notable actions, inventory, and relationships**
- **Generate beautiful character overviews** in markdown or text format
- **Export/import character data** for sharing or backup
- **Create comprehensive campaign records** with rich character details

## Features

### Character Data Tracked

- **Basic Information**: Name, player, race, class, level
- **Description**: Appearance, personality, backstory
- **Notable Actions**: Significant events by session
- **Inventory**: Items organized by category (weapons, armor, magical, consumable, etc.)
- **Relationships**: NPCs, allies, enemies, mentors, companions
- **Character Development**: Growth notes and personality changes
- **Memorable Quotes**: Favorite moments with context
- **Goals**: Current objectives and completed achievements
- **Statistics**: Sessions played, participation tracking

### Output Formats

- **Markdown**: Beautiful formatted overviews perfect for wikis or notes
- **Text**: Plain text for simple viewing
- **JSON**: Complete data export for programmatic access

## Quick Start

### View Character Profiles

```bash
# List all characters
python cli.py list-characters

# View detailed character overview
python cli.py show-character "Sha'ek Mindfa'ek"

# Save overview to file
python cli.py show-character "Pipira Shimmerlock" --output pip_overview.md
```

###Export/Import

```bash
# Export a character
python cli.py export-character "Sha'ek Mindfa'ek" shaek.json

# Import a character
python cli.py import-character shaek.json

# Import with custom name
python cli.py import-character shaek.json --character-name "Sha'ek v2"
```

## Creating Character Profiles

### Method 1: Python API

```python
from src.character_profile import (
    CharacterProfile, CharacterProfileManager,
    CharacterAction, CharacterItem, CharacterRelationship
)

# Create manager
manager = CharacterProfileManager()

# Create character profile
character = CharacterProfile(
    name="Gandor the Brave",
    player="Sarah",
    race="Human",
    class_name="Fighter",
    level=5,
    description="A brave warrior from the northern kingdoms",
    personality="Bold, protective, values honor above all",
    appearance="Tall, scarred face, wears plate armor",
    aliases=["Gandor", "The Brave One"],
    campaign="Lost Mines of Phandelver",
    notable_actions=[
        CharacterAction(
            session="Session 1",
            description="Defended the village from goblin raid",
            type="combat"
        )
    ],
    inventory=[
        CharacterItem(
            name="Longsword +1",
            description="Enchanted blade found in ancient ruins",
            category="weapon",
            session_acquired="Session 3"
        )
    ],
    relationships=[
        CharacterRelationship(
            name="Sildar Hallwinter",
            relationship_type="ally",
            description="Town guard captain",
            first_met="Session 1"
        )
    ],
    current_goals=[
        "Find the missing supplies",
        "Protect the town from the Redbrands"
    ],
    sessions_appeared=["Session 1", "Session 2", "Session 3"],
    total_sessions=3
)

# Save the profile
manager.add_profile("Gandor the Brave", character)
```

### Method 2: Manual JSON Editing

Edit `models/character_profiles.json` directly:

```json
{
  "Gandor the Brave": {
    "name": "Gandor the Brave",
    "player": "Sarah",
    "race": "Human",
    "class_name": "Fighter",
    "level": 5,
    "description": "A brave warrior from the northern kingdoms",
    "notable_actions": [
      {
        "session": "Session 1",
        "description": "Defended the village",
        "type": "combat"
      }
    ],
    ...
  }
}
```

## Example Output

### Character Overview (Markdown)

```markdown
# Sha'ek Mindfa'ek

## Basic Information

- **Player**: Player1
- **Race**: Adar (from Adar)
- **Class**: Cleric of Ioun (Level 3)
- **Campaign**: Gaia Adventures - Culdor Academy
- **Also known as**: Sha'ek, The Broken, The Defect

**Sessions Played**: 3

## Description

The Broken - A hardened veteran cleric with glowing green eyes...

### Appearance

Wears heavy chain mail with visible wear and damage from combat...

## Notable Actions

### Session 2
*Divine*: Prayed to Pelor and received visions from Ioun...

## Inventory

### Armor
- **Chain Mail Armor**: Heavy chain mail with battle damage
- **Shield with Ioun's Emblem**: Well-maintained shield

### Consumable
- **Healing Potion**: Given by Professor Artex

## Relationships

- **Golos** (bonded spirit): Quori spirit connected through the Smelting ritual
- **Ioun** (deity): Goddess of knowledge, cleric devotee
```

## CLI Commands Reference

### List Characters

```bash
python cli.py list-characters
```

Shows a table with all characters: name, player, race/class, level, and session count.

### Show Character

```bash
python cli.py show-character <name> [--format markdown|text] [--output FILE]
```

Generate detailed character overview.

**Examples**:
```bash
# Display in terminal (markdown formatted)
python cli.py show-character "Sha'ek Mindfa'ek"

# Save to file
python cli.py show-character "Pipira Shimmerlock" --output pip.md

# Plain text format
python cli.py show-character "Fan'nar Khe'Lek" --format text
```

### Export Character

```bash
python cli.py export-character <name> <output_file>
```

Export character profile to JSON file for sharing or backup.

**Example**:
```bash
python cli.py export-character "Sha'ek Mindfa'ek" shaek_backup.json
```

### Import Character

```bash
python cli.py import-character <input_file> [--character-name NAME]
```

Import character profile from JSON file.

**Examples**:
```bash
# Import with original name
python cli.py import-character shaek_backup.json

# Import with custom name
python cli.py import-character shaek_backup.json --character-name "Sha'ek (Backup)"
```

## Data Structure

### CharacterProfile Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Character's full name |
| `player` | string | Player name |
| `race` | string | Character race |
| `class_name` | string | Character class |
| `level` | int | Current level |
| `description` | string | General description |
| `personality` | string | Personality traits |
| `backstory` | string | Character background |
| `appearance` | string | Physical description |
| `aliases` | list | Alternative names/nicknames |
| `campaign` | string | Campaign name |
| `notable_actions` | list | List of CharacterAction objects |
| `inventory` | list | List of CharacterItem objects |
| `relationships` | list | List of CharacterRelationship objects |
| `development_notes` | list | List of CharacterDevelopment objects |
| `memorable_quotes` | list | List of CharacterQuote objects |
| `current_goals` | list | Active objectives |
| `completed_goals` | list | Achieved objectives |
| `sessions_appeared` | list | Session IDs |
| `total_sessions` | int | Number of sessions |
| `dm_notes` | string | DM-only notes |
| `player_notes` | string | Player notes |

### CharacterAction

```python
@dataclass
class CharacterAction:
    session: str            # Session identifier
    timestamp: Optional[str]  # Optional timestamp
    description: str        # What happened
    type: str              # combat, social, exploration, magic, etc.
```

### CharacterItem

```python
@dataclass
class CharacterItem:
    name: str                    # Item name
    description: Optional[str]   # Item description
    session_acquired: Optional[str]  # When obtained
    category: str               # weapon, armor, magical, consumable, quest, misc
```

### CharacterRelationship

```python
@dataclass
class CharacterRelationship:
    name: str                    # NPC/Character name
    relationship_type: str       # ally, enemy, neutral, mentor, etc.
    description: Optional[str]   # Details about the relationship
    first_met: Optional[str]    # When they first met
```

## Use Cases

### Campaign Journal

Generate beautiful character overviews for your campaign wiki or shared notes:

```bash
# Export all characters
for char in $(python cli.py list-characters | tail -n +3 | awk '{print $2}'); do
    python cli.py show-character "$char" --output "wiki/$char.md"
done
```

### Session Prep

Review character information before a session:

```bash
python cli.py show-character "Sha'ek Mindfa'ek"
```

### Backup and Sharing

Share character profiles with other DMs or players:

```bash
# Export party
python cli.py export-character "Sha'ek Mindfa'ek" shaek.json
python cli.py export-character "Pipira Shimmerlock" pip.json

# Send files to other DM
# They can import:
python cli.py import-character shaek.json
```

### Character Growth Tracking

Document character development over time by updating the profile after each session:

```python
from src.character_profile import CharacterProfileManager, CharacterDevelopment

manager = CharacterProfileManager()
profile = manager.get_profile("Gandor the Brave")

# Add development note
profile.development_notes.append(
    CharacterDevelopment(
        session="Session 5",
        note="Learned to trust magic users after Pip saved his life",
        category="personality"
    )
)

# Update level
profile.level = 6

# Save changes
manager.add_profile("Gandor the Brave", profile)
```

## Integration with Party Config

Character profiles complement the party configuration system:

- **Party Config**: Defines who is in the party for session processing
- **Character Profiles**: Tracks detailed character history and development

You can create character profiles from your party configuration:

```python
from src.party_config import PartyConfigManager
from src.character_profile import CharacterProfile, CharacterProfileManager

party_mgr = PartyConfigManager()
char_mgr = CharacterProfileManager()

party = party_mgr.get_party("default")

for character in party.characters:
    # Create basic profile from party character
    profile = CharacterProfile(
        name=character.name,
        player=character.player,
        race=character.race,
        class_name=character.class_name,
        description=character.description or "",
        aliases=character.aliases or [],
        campaign=party.campaign
    )

    char_mgr.add_profile(character.name, profile)
```

## Storage Location

Character profiles are stored in: `models/character_profiles.json`

This file is NOT tracked in git (it's in .gitignore) to keep your character data private.

## Tips for Best Results

1. **Update regularly**: Add notes after each session while events are fresh
2. **Be specific**: Detailed descriptions help create better overviews
3. **Track relationships**: NPCs and relationships add depth to character stories
4. **Include quotes**: Memorable moments make characters come alive
5. **Document growth**: Note how characters change over time
6. **Use categories**: Proper categorization makes overviews more organized

## Future Enhancements

Planned features:
- **Automatic extraction** from session transcripts
- **Character comparison** tools
- **Timeline visualization** of character actions
- **Relationship graphs** showing party dynamics
- **Character arc analysis** using AI
- **Integration with session notebooks** for personalized stories

## Example: Complete Character Profile

See the included example characters from the Culdor Campaign:
- Sha'ek Mindfa'ek (The Broken)
- Pipira Shimmerlock (Pip)
- Fan'nar Khe'Lek (Pas'Ta)
- Furnax (Frost Hellhound)

View them with:
```bash
python cli.py list-characters
python cli.py show-character "Sha'ek Mindfa'ek"
```

---

**Create rich, detailed character profiles that bring your D&D campaign to life!**
