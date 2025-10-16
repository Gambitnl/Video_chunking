"""Character profiling and overview generation from campaign logs and transcripts"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path
import json
import shutil
from datetime import datetime
import logging


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

    def __init__(self, profiles_file: Path = None, max_backups: int = 5):
        from .config import Config

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Set up paths
        self.profiles_file = profiles_file or (Config.MODELS_DIR / "character_profiles.json")
        self.backup_dir = self.profiles_file.parent / "character_backups"
        self.max_backups = max_backups

        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True, parents=True)

        # Load profiles
        self.profiles: Dict[str, CharacterProfile] = self._load_profiles()

        self.logger.info(f"CharacterProfileManager initialized with {len(self.profiles)} profiles")

    def _load_profiles(self) -> Dict[str, CharacterProfile]:
        """Load character profiles from JSON file"""
        if not self.profiles_file.exists():
            self.logger.info(f"No existing profiles file found at {self.profiles_file}")
            return {}

        try:
            self.logger.debug(f"Loading profiles from {self.profiles_file}")
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

            self.logger.info(f"Loaded {len(profiles)} character profiles")
            return profiles
        except Exception as e:
            self.logger.error(f"Failed to load character profiles: {e}", exc_info=True)
            return {}

    def _create_backup(self):
        """Create a backup of the current profiles file"""
        if not self.profiles_file.exists():
            return

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"character_profiles_{timestamp}.json"

            shutil.copy2(self.profiles_file, backup_file)
            self.logger.debug(f"Created backup: {backup_file.name}")

            # Clean up old backups
            self._cleanup_old_backups()

        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")

    def _cleanup_old_backups(self):
        """Remove old backups, keeping only the most recent max_backups files"""
        try:
            backups = sorted(self.backup_dir.glob("character_profiles_*.json"), reverse=True)

            if len(backups) > self.max_backups:
                for old_backup in backups[self.max_backups:]:
                    old_backup.unlink()
                    self.logger.debug(f"Removed old backup: {old_backup.name}")

        except Exception as e:
            self.logger.warning(f"Failed to cleanup old backups: {e}")

    def save_profiles(self):
        """Save all character profiles to JSON file with automatic backup"""
        try:
            self.profiles_file.parent.mkdir(exist_ok=True, parents=True)

            # Create backup before saving
            self._create_backup()

            data = {}
            for char_id, profile in self.profiles.items():
                data[char_id] = asdict(profile)

            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved {len(data)} character profiles to {self.profiles_file.name}")

        except Exception as e:
            self.logger.error(f"Failed to save character profiles: {e}", exc_info=True)
            raise

    def get_profile(self, character_name: str) -> Optional[CharacterProfile]:
        """Get a character profile by name"""
        return self.profiles.get(character_name)

    def add_profile(self, character_name: str, profile: CharacterProfile):
        """Add or update a character profile"""
        is_new = character_name not in self.profiles
        profile.last_updated = datetime.now().isoformat()
        self.profiles[character_name] = profile

        self.logger.info(f"{'Added new' if is_new else 'Updated'} character profile: {character_name}")
        self.save_profiles()

    def list_characters(self) -> List[str]:
        """List all character names"""
        return list(self.profiles.keys())

    def export_profile(self, character_name: str, export_path: Path):
        """Export a single character profile to JSON"""
        profile = self.get_profile(character_name)
        if not profile:
            self.logger.error(f"Cannot export - character '{character_name}' not found")
            raise ValueError(f"Character '{character_name}' not found")

        try:
            data = {character_name: asdict(profile)}
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Exported character '{character_name}' to {export_path}")

        except Exception as e:
            self.logger.error(f"Failed to export character '{character_name}': {e}", exc_info=True)
            raise

    def import_profile(self, import_path: Path, character_name: Optional[str] = None):
        """Import a character profile from JSON"""
        try:
            self.logger.info(f"Importing character profile from {import_path}")

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
                    CharacterDevelopment(**dev) for dev in profile_data.get('development_notes', [])
                ]
                profile_data['memorable_quotes'] = [
                    CharacterQuote(**quote) for quote in profile_data.get('memorable_quotes', [])
                ]

                profile = CharacterProfile(**profile_data)
                self.add_profile(new_char_name, profile)

                self.logger.info(f"Successfully imported character '{new_char_name}'")
                return new_char_name

        except Exception as e:
            self.logger.error(f"Failed to import character profile: {e}", exc_info=True)
            raise

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

        # Quick Stats Bar
        md += "---\n\n"
        md += f"**{profile.race}** | **{profile.class_name} Lv.{profile.level}** | "
        md += f"**{profile.total_sessions} Sessions** | "
        md += f"**{len(profile.notable_actions)} Actions** | "
        md += f"**{len(profile.inventory)} Items**\n\n"
        md += "---\n\n"

        # Basic Info
        md += "## 📋 Basic Information\n\n"
        md += f"- **Player**: {profile.player}\n"
        md += f"- **Campaign**: {profile.campaign}\n"

        if profile.aliases:
            md += f"- **Also known as**: {', '.join(profile.aliases)}\n"

        if profile.first_session:
            md += f"- **First Appearance**: {profile.first_session}\n"

        md += "\n"

        # Description
        if profile.description:
            md += "## 📖 Description\n\n"
            md += profile.description + "\n\n"

        if profile.appearance:
            md += "### 👤 Appearance\n\n"
            md += profile.appearance + "\n\n"

        if profile.personality:
            md += "### 🎭 Personality\n\n"
            md += profile.personality + "\n\n"

        if profile.backstory:
            md += "### 📜 Backstory\n\n"
            md += profile.backstory + "\n\n"

        # Goals
        if profile.current_goals or profile.completed_goals:
            md += "## 🎯 Goals & Progress\n\n"

            if profile.current_goals:
                md += "### Current Objectives\n\n"
                for goal in profile.current_goals:
                    md += f"- 🔲 {goal}\n"
                md += "\n"

            if profile.completed_goals:
                md += "### Completed Goals\n\n"
                for goal in profile.completed_goals:
                    md += f"- ✅ {goal}\n"
                md += "\n"

        # Notable Actions
        if profile.notable_actions:
            md += "## ⚔️ Notable Actions\n\n"

            # Group by action type for summary
            action_types = {}
            for action in profile.notable_actions:
                action_types[action.type] = action_types.get(action.type, 0) + 1

            # Show action type breakdown
            if len(action_types) > 1:
                md += "_Action Summary:_ "
                md += " | ".join([f"{t.title()}: {c}" for t, c in sorted(action_types.items())])
                md += "\n\n"

            # Action type emoji mapping
            action_icons = {
                'combat': '⚔️',
                'social': '💬',
                'exploration': '🔍',
                'magic': '✨',
                'divine': '🙏',
                'general': '📌'
            }

            # Display recent actions (last 15)
            recent_actions = profile.notable_actions[-15:] if len(profile.notable_actions) > 15 else profile.notable_actions
            for action in recent_actions:
                icon = action_icons.get(action.type, '•')
                md += f"**{action.session}** {icon} _{action.type.title()}_\n"
                md += f"  {action.description}\n\n"

        # Inventory
        if profile.inventory:
            md += "## 🎒 Inventory\n\n"
            md += f"_Carrying {len(profile.inventory)} items_\n\n"

            # Category icon mapping
            category_icons = {
                'weapon': '⚔️',
                'armor': '🛡️',
                'magical': '✨',
                'consumable': '🧪',
                'quest': '📜',
                'equipment': '🔧',
                'misc': '📦'
            }

            by_category = {}
            for item in profile.inventory:
                by_category.setdefault(item.category, []).append(item)

            for category, items in sorted(by_category.items()):
                icon = category_icons.get(category, '•')
                md += f"### {icon} {category.title()}\n\n"
                for item in items:
                    md += f"- **{item.name}**"
                    if item.description:
                        md += f": {item.description}"
                    if item.session_acquired:
                        md += f" _(acquired: {item.session_acquired})_"
                    md += "\n"
                md += "\n"

        # Relationships
        if profile.relationships:
            md += "## 🤝 Relationships\n\n"

            # Relationship type icons
            rel_icons = {
                'ally': '🤝',
                'enemy': '⚔️',
                'neutral': '🤷',
                'mentor': '👨‍🏫',
                'student': '👨‍🎓',
                'friend': '❤️',
                'rival': '⚡',
                'family': '👨‍👩‍👦',
                'deity': '🙏',
                'bonded spirit': '👻',
                'companion': '🐾',
                'employer': '💼',
                'master': '👑',
                'rescued by': '🆘'
            }

            for rel in profile.relationships:
                icon = rel_icons.get(rel.relationship_type.lower(), '•')
                md += f"**{icon} {rel.name}** _{rel.relationship_type}_\n"
                if rel.description:
                    md += f"  {rel.description}\n"
                if rel.first_met:
                    md += f"  _First met: {rel.first_met}_\n"
                md += "\n"

        # Memorable Quotes
        if profile.memorable_quotes:
            md += "## 💬 Memorable Quotes\n\n"
            for quote in profile.memorable_quotes[-5:]:  # Last 5
                md += f"> \"{quote.quote}\"\n\n"
                if quote.context:
                    md += f"_Context: {quote.context}_\n"
                md += f"_— {quote.session}_\n\n"

        # Development
        if profile.development_notes:
            md += "## 📈 Character Development\n\n"

            # Development category icons
            dev_icons = {
                'personality': '🎭',
                'backstory': '📜',
                'goal': '🎯',
                'fear': '😰',
                'trait': '✨',
                'divine connection': '🙏',
                'general': '📌'
            }

            for dev in profile.development_notes:
                icon = dev_icons.get(dev.category.lower(), '•')
                md += f"**{dev.session}** {icon} _{dev.category.title()}_\n"
                md += f"  {dev.note}\n\n"

        # Notes
        if profile.dm_notes:
            md += "## 📝 DM Notes\n\n"
            md += profile.dm_notes + "\n\n"

        if profile.player_notes:
            md += "## ✍️ Player Notes\n\n"
            md += profile.player_notes + "\n\n"

        # Footer with update info
        if profile.last_updated:
            md += "---\n\n"
            md += f"_Last updated: {profile.last_updated}_\n"

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

    # Helper methods for filtering and analytics
    def get_actions_by_type(self, character_name: str, action_type: str) -> List[CharacterAction]:
        """Get all actions of a specific type for a character"""
        profile = self.get_profile(character_name)
        if not profile:
            return []
        return [a for a in profile.notable_actions if a.type == action_type]

    def get_actions_by_session(self, character_name: str, session: str) -> List[CharacterAction]:
        """Get all actions from a specific session"""
        profile = self.get_profile(character_name)
        if not profile:
            return []
        return [a for a in profile.notable_actions if a.session == session]

    def get_character_statistics(self, character_name: str) -> Dict:
        """Get comprehensive statistics for a character"""
        profile = self.get_profile(character_name)
        if not profile:
            return {}

        # Count actions by type
        action_counts = {}
        for action in profile.notable_actions:
            action_counts[action.type] = action_counts.get(action.type, 0) + 1

        # Count inventory by category
        inventory_counts = {}
        for item in profile.inventory:
            inventory_counts[item.category] = inventory_counts.get(item.category, 0) + 1

        # Count relationships by type
        relationship_counts = {}
        for rel in profile.relationships:
            relationship_counts[rel.relationship_type] = relationship_counts.get(rel.relationship_type, 0) + 1

        return {
            'name': profile.name,
            'level': profile.level,
            'total_sessions': profile.total_sessions,
            'total_actions': len(profile.notable_actions),
            'actions_by_type': action_counts,
            'total_items': len(profile.inventory),
            'items_by_category': inventory_counts,
            'total_relationships': len(profile.relationships),
            'relationships_by_type': relationship_counts,
            'total_quotes': len(profile.memorable_quotes),
            'total_developments': len(profile.development_notes),
            'current_goals': len(profile.current_goals),
            'completed_goals': len(profile.completed_goals)
        }

    def search_profiles(self, query: str) -> List[str]:
        """Search character profiles for a text query (case-insensitive)"""
        query = query.lower()
        matches = []

        for char_name, profile in self.profiles.items():
            # Search in various fields
            searchable_text = (
                f"{profile.name} {profile.description} {profile.personality} "
                f"{profile.backstory} {profile.appearance} {' '.join(profile.aliases)}"
            ).lower()

            # Also search in actions and relationships
            for action in profile.notable_actions:
                searchable_text += f" {action.description}".lower()

            for rel in profile.relationships:
                searchable_text += f" {rel.name} {rel.description or ''}".lower()

            if query in searchable_text:
                matches.append(char_name)

        return matches
