"""Character profiling and overview generation from campaign logs and transcripts"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime


@dataclass
class CharacterAction:
    """Represents a significant action taken by a character"""
    session: str
    timestamp: Optional[str] = None
    description: str = ""
    type: str = "general"  # combat, social, exploration, magic, etc.


@dataclass
class CharacterItem:
    """Items owned or received by the character"""
    name: str
    description: Optional[str] = None
    session_acquired: Optional[str] = None
    category: str = "misc"  # weapon, armor, magical, consumable, quest, misc


@dataclass
class CharacterRelationship:
    """Relationships with other characters, NPCs, or factions"""
    name: str
    relationship_type: str  # ally, enemy, neutral, mentor, student, etc.
    description: Optional[str] = None
    first_met: Optional[str] = None


@dataclass
class CharacterDevelopment:
    """Character growth and development notes"""
    session: str
    note: str
    category: str = "general"  # personality, backstory, goal, fear, trait


@dataclass
class CharacterQuote:
    """Memorable quotes from the character"""
    session: str
    quote: str
    context: Optional[str] = None


@dataclass
class CharacterProfile:
    """Complete character profile with all tracked information"""
    # Basic Information
    name: str
    player: str
    race: str
    class_name: str
    level: int = 1

    # Core Description
    description: str = ""
    personality: str = ""
    backstory: str = ""

    # Appearance
    appearance: str = ""

    # Aliases and alternative names
    aliases: List[str] = field(default_factory=list)

    # Campaign Information
    campaign: str = ""
    first_session: Optional[str] = None
    last_updated: Optional[str] = None

    # Tracked Data
    notable_actions: List[CharacterAction] = field(default_factory=list)
    inventory: List[CharacterItem] = field(default_factory=list)
    relationships: List[CharacterRelationship] = field(default_factory=list)
    development_notes: List[CharacterDevelopment] = field(default_factory=list)
    memorable_quotes: List[CharacterQuote] = field(default_factory=list)

    # Statistics
    sessions_appeared: List[str] = field(default_factory=list)
    total_sessions: int = 0

    # Goals and Motivations
    current_goals: List[str] = field(default_factory=list)
    completed_goals: List[str] = field(default_factory=list)

    # Notes
    dm_notes: str = ""
    player_notes: str = ""


class CharacterProfileManager:
    """Manages character profiles for a campaign"""

    def __init__(self, profiles_file: Path = None):
        from .config import Config
        self.profiles_file = profiles_file or (Config.MODELS_DIR / "character_profiles.json")
        self.profiles: Dict[str, CharacterProfile] = self._load_profiles()

    def _load_profiles(self) -> Dict[str, CharacterProfile]:
        """Load character profiles from JSON file"""
        if not self.profiles_file.exists():
            return {}

        try:
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            profiles = {}
            for char_id, profile_data in data.items():
                # Convert nested dataclasses
                profile_data['notable_actions'] = [
                    CharacterAction(**action) for action in profile_data.get('notable_actions', [])
                ]
                profile_data['inventory'] = [
                    CharacterItem(**item) for item in profile_data.get('inventory', [])
                ]
                profile_data['relationships'] = [
                    CharacterRelationship(**rel) for rel in profile_data.get('relationships', [])
                ]
                profile_data['development_notes'] = [
                    CharacterDevelopment(**dev) for dev in profile_data.get('development_notes', [])
                ]
                profile_data['memorable_quotes'] = [
                    CharacterQuote(**quote) for quote in profile_data.get('memorable_quotes', [])
                ]

                profiles[char_id] = CharacterProfile(**profile_data)

            return profiles
        except Exception as e:
            print(f"Warning: Could not load character profiles: {e}")
            return {}

    def save_profiles(self):
        """Save all character profiles to JSON file"""
        self.profiles_file.parent.mkdir(exist_ok=True, parents=True)

        data = {}
        for char_id, profile in self.profiles.items():
            data[char_id] = asdict(profile)

        with open(self.profiles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_profile(self, character_name: str) -> Optional[CharacterProfile]:
        """Get a character profile by name"""
        return self.profiles.get(character_name)

    def add_profile(self, character_name: str, profile: CharacterProfile):
        """Add or update a character profile"""
        profile.last_updated = datetime.now().isoformat()
        self.profiles[character_name] = profile
        self.save_profiles()

    def list_characters(self) -> List[str]:
        """List all character names"""
        return list(self.profiles.keys())

    def export_profile(self, character_name: str, export_path: Path):
        """Export a single character profile to JSON"""
        profile = self.get_profile(character_name)
        if not profile:
            raise ValueError(f"Character '{character_name}' not found")

        data = {character_name: asdict(profile)}
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_profile(self, import_path: Path, character_name: Optional[str] = None):
        """Import a character profile from JSON"""
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for file_char_name, profile_data in data.items():
            new_char_name = character_name or file_char_name

            # Convert nested structures
            profile_data['notable_actions'] = [
                CharacterAction(**action) for action in profile_data.get('notable_actions', [])
            ]
            profile_data['inventory'] = [
                CharacterItem(**item) for item in profile_data.get('inventory', [])
            ]
            profile_data['relationships'] = [
                CharacterRelationship(**rel) for rel in profile_data.get('relationships', [])
            ]
            profile_data['development_notes'] = [
                CharacterDevelopment(**dev) for item in profile_data.get('development_notes', [])
            ]
            profile_data['memorable_quotes'] = [
                CharacterQuote(**quote) for quote in profile_data.get('memorable_quotes', [])
            ]

            profile = CharacterProfile(**profile_data)
            self.add_profile(new_char_name, profile)
            return new_char_name

    def generate_character_overview(self, character_name: str, format: str = "markdown") -> str:
        """Generate a readable character overview"""
        profile = self.get_profile(character_name)
        if not profile:
            return f"Character '{character_name}' not found."

        if format == "markdown":
            return self._generate_markdown_overview(profile)
        elif format == "text":
            return self._generate_text_overview(profile)
        else:
            return str(asdict(profile))

    def _generate_markdown_overview(self, profile: CharacterProfile) -> str:
        """Generate markdown format character overview"""
        md = f"# {profile.name}\n\n"

        # Basic Info
        md += "## Basic Information\n\n"
        md += f"- **Player**: {profile.player}\n"
        md += f"- **Race**: {profile.race}\n"
        md += f"- **Class**: {profile.class_name} (Level {profile.level})\n"
        md += f"- **Campaign**: {profile.campaign}\n"

        if profile.aliases:
            md += f"- **Also known as**: {', '.join(profile.aliases)}\n"

        md += f"\n**Sessions Played**: {profile.total_sessions}\n\n"

        # Description
        if profile.description:
            md += "## Description\n\n"
            md += profile.description + "\n\n"

        if profile.appearance:
            md += "### Appearance\n\n"
            md += profile.appearance + "\n\n"

        if profile.personality:
            md += "### Personality\n\n"
            md += profile.personality + "\n\n"

        if profile.backstory:
            md += "### Backstory\n\n"
            md += profile.backstory + "\n\n"

        # Goals
        if profile.current_goals:
            md += "## Current Goals\n\n"
            for goal in profile.current_goals:
                md += f"- {goal}\n"
            md += "\n"

        # Notable Actions
        if profile.notable_actions:
            md += "## Notable Actions\n\n"
            for action in profile.notable_actions[-10:]:  # Last 10
                md += f"### {action.session}\n"
                md += f"*{action.type.title()}*: {action.description}\n\n"

        # Inventory
        if profile.inventory:
            md += "## Inventory\n\n"
            by_category = {}
            for item in profile.inventory:
                by_category.setdefault(item.category, []).append(item)

            for category, items in sorted(by_category.items()):
                md += f"### {category.title()}\n\n"
                for item in items:
                    md += f"- **{item.name}**"
                    if item.description:
                        md += f": {item.description}"
                    md += "\n"
                md += "\n"

        # Relationships
        if profile.relationships:
            md += "## Relationships\n\n"
            for rel in profile.relationships:
                md += f"- **{rel.name}** ({rel.relationship_type})"
                if rel.description:
                    md += f": {rel.description}"
                md += "\n"
            md += "\n"

        # Memorable Quotes
        if profile.memorable_quotes:
            md += "## Memorable Quotes\n\n"
            for quote in profile.memorable_quotes[-5:]:  # Last 5
                md += f"> \"{quote.quote}\"\n"
                if quote.context:
                    md += f">\n*— {quote.context}*\n"
                md += f"\n*Session: {quote.session}*\n\n"

        # Development
        if profile.development_notes:
            md += "## Character Development\n\n"
            for dev in profile.development_notes:
                md += f"**{dev.session}** ({dev.category}): {dev.note}\n\n"

        # Notes
        if profile.dm_notes:
            md += "## DM Notes\n\n"
            md += profile.dm_notes + "\n\n"

        if profile.player_notes:
            md += "## Player Notes\n\n"
            md += profile.player_notes + "\n\n"

        return md

    def _generate_text_overview(self, profile: CharacterProfile) -> str:
        """Generate plain text format character overview"""
        text = f"{'=' * 80}\n"
        text += f"{profile.name}\n"
        text += f"{'=' * 80}\n\n"

        text += f"{profile.race} {profile.class_name} (Level {profile.level})\n"
        text += f"Played by: {profile.player}\n"
        text += f"Campaign: {profile.campaign}\n"
        text += f"Sessions: {profile.total_sessions}\n\n"

        if profile.description:
            text += f"{profile.description}\n\n"

        # Add more sections as needed...

        return text
