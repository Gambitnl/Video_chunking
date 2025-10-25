"""Character profiling and overview generation from campaign logs and transcripts"""
from dataclasses import dataclass, field, asdict
from typing import Any, List, Dict, Optional
from pathlib import Path
import json
import shutil
from datetime import datetime
import logging
from .formatter import sanitize_filename

PROFILE_UPDATE_CATEGORIES = [
    "notable_actions",
    "memorable_quotes",
    "development_notes",
    "relationships",
    "inventory_changes",
    "goal_progress",
    "character_background",
]


@dataclass
class ProfileUpdate:
    """A suggested update to a character profile."""
    character: str
    category: str
    content: str
    type: Optional[str] = None
    timestamp: Optional[str] = None
    session_id: Optional[str] = None
    confidence: Optional[float] = None
    context: Optional[str] = None
    quote: Optional[str] = None
    segment_start: Optional[float] = None
    segment_end: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.category not in PROFILE_UPDATE_CATEGORIES:
            raise ValueError(
                f"Unsupported profile update category '{self.category}'. "
                f"Known categories: {', '.join(PROFILE_UPDATE_CATEGORIES)}"
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.timestamp and len(self.timestamp.split(":")) not in (2, 3):
            raise ValueError("timestamp must be in MM:SS or HH:MM:SS format")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ProfileUpdate":
        character = payload.get("character")
        category = payload.get("category")
        content = payload.get("content")
        if not all([character, category, content]):
            raise ValueError("character, category, and content are required fields")
        instance = cls(
            character=character,
            category=category,
            content=content,
            type=payload.get("type"),
            timestamp=payload.get("timestamp"),
            session_id=payload.get("session_id"),
            confidence=payload.get("confidence"),
            context=payload.get("context"),
            quote=payload.get("quote"),
            segment_start=payload.get("segment_start"),
            segment_end=payload.get("segment_end"),
            tags=list(payload.get("tags", [])),
            relationships=list(payload.get("relationships", [])),
            metadata=dict(payload.get("metadata", {})),
        )
        return instance


@dataclass
class ProfileUpdateBatch:
    """Container for suggested updates generated from a session transcript."""
    session_id: str
    campaign_id: Optional[str] = None
    generated_at: Optional[str] = None
    source: Optional[Dict[str, Any]] = None
    updates: List[ProfileUpdate] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "campaign_id": self.campaign_id,
            "generated_at": self.generated_at,
            "source": self.source or {},
            "updates": [update.to_dict() for update in self.updates],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ProfileUpdateBatch":
        session_id = payload.get("session_id")
        if not session_id:
            raise ValueError("session_id is required for ProfileUpdateBatch")
        updates_payload = payload.get("updates", [])
        updates = [ProfileUpdate.from_dict(item) for item in updates_payload]
        return cls(
            session_id=session_id,
            campaign_id=payload.get("campaign_id"),
            generated_at=payload.get("generated_at"),
            source=dict(payload.get("source", {})),
            updates=updates,
        )



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
    """Manages character profiles for a campaign, with each profile stored as a separate JSON file."""

    def __init__(self, profiles_dir: Path = None, max_backups: int = 5):
        from .config import Config
        from .formatter import sanitize_filename

        self.logger = logging.getLogger(__name__)
        self.sanitize_filename = sanitize_filename

        # Set up paths
        self.profiles_dir = profiles_dir or (Config.MODELS_DIR / "character_profiles")
        self.backup_dir = Config.MODELS_DIR / "character_backups"
        self.max_backups = max_backups

        # Ensure directories exist
        self.profiles_dir.mkdir(exist_ok=True, parents=True)
        self.backup_dir.mkdir(exist_ok=True, parents=True)

        # Handle one-time migration from old single-file format
        self._migrate_old_profiles()

        # Load all profiles from individual files
        self.profiles: Dict[str, CharacterProfile] = self._load_profiles()

        self.logger.info(f"CharacterProfileManager initialized with {len(self.profiles)} profiles.")

    def _migrate_old_profiles(self):
        """Migrate profiles from the old single-file storage to the new individual file structure."""
        from .config import Config
        old_profiles_file = Config.MODELS_DIR / "character_profiles.json"
        migrated_marker = Config.MODELS_DIR / "character_profiles.json.migrated"

        if old_profiles_file.exists() and not migrated_marker.exists():
            self.logger.warning(f"Old profile file '{old_profiles_file}' found. Migrating to individual files...")
            try:
                with open(old_profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for char_name, profile_data in data.items():
                    profile = self._parse_profile_data(profile_data)
                    self._save_single_profile(profile)
                    self.logger.info(f"Migrated character '{char_name}' to its own file.")

                # Rename old file to prevent re-migration
                old_profiles_file.rename(migrated_marker)
                self.logger.warning(f"Migration complete. Old file renamed to '{migrated_marker.name}'.")

            except Exception as e:
                self.logger.error(f"Failed during migration from old profile file: {e}", exc_info=True)

    def _parse_profile_data(self, profile_data: dict) -> CharacterProfile:
        """Parse a dictionary into a CharacterProfile object, handling nested dataclasses."""
        profile_data['notable_actions'] = [CharacterAction(**action) for action in profile_data.get('notable_actions', [])]
        profile_data['inventory'] = [CharacterItem(**item) for item in profile_data.get('inventory', [])]
        profile_data['relationships'] = [CharacterRelationship(**rel) for rel in profile_data.get('relationships', [])]
        profile_data['development_notes'] = [CharacterDevelopment(**dev) for dev in profile_data.get('development_notes', [])]
        profile_data['memorable_quotes'] = [CharacterQuote(**quote) for quote in profile_data.get('memorable_quotes', [])]
        return CharacterProfile(**profile_data)

    def _load_profiles(self) -> Dict[str, CharacterProfile]:
        """Load all character profiles from individual JSON files in the profiles directory."""
        profiles = {}
        self.logger.debug(f"Loading profiles from directory: {self.profiles_dir}")
        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                profile = self._parse_profile_data(profile_data)
                
                if profile.name:
                    profiles[profile.name] = profile
                else:
                    self.logger.warning(f"Profile file '{profile_file.name}' is missing a 'name' field. Skipping.")

            except Exception as e:
                self.logger.error(f"Failed to load character profile from '{profile_file.name}': {e}", exc_info=True)
        
        self.logger.info(f"Loaded {len(profiles)} character profiles from individual files.")
        return profiles

    def _create_backup(self, profile_path: Path):
        """Create a backup of a single profile file."""
        if not profile_path.exists():
            return

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{profile_path.stem}_{timestamp}.json"
            shutil.copy2(profile_path, backup_file)
            self.logger.debug(f"Created backup for '{profile_path.name}' at '{backup_file.name}'")
            self._cleanup_old_backups(profile_path.stem)
        except Exception as e:
            self.logger.warning(f"Failed to create backup for '{profile_path.name}': {e}")

    def _cleanup_old_backups(self, profile_stem: str):
        """Remove old backups for a specific character, keeping the most recent ones."""
        try:
            backups = sorted(self.backup_dir.glob(f"{profile_stem}_*.json"), reverse=True)
            if len(backups) > self.max_backups:
                for old_backup in backups[self.max_backups:]:
                    old_backup.unlink()
                    self.logger.debug(f"Removed old backup: {old_backup.name}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old backups for '{profile_stem}': {e}")

    def _save_single_profile(self, profile: CharacterProfile):
        """Save a single character profile to its own JSON file."""
        if not profile or not profile.name:
            self.logger.error("Attempted to save a profile with no name.")
            return

        try:
            profile.last_updated = datetime.now().isoformat()
            filename = f"{self.sanitize_filename(profile.name)}.json"
            profile_path = self.profiles_dir / filename

            self._create_backup(profile_path)

            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(profile), f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved profile for '{profile.name}' to '{profile_path.name}'")

        except Exception as e:
            self.logger.error(f"Failed to save profile for '{profile.name}': {e}", exc_info=True)
            raise

    def get_profile(self, character_name: str) -> Optional[CharacterProfile]:
        """Get a character profile by name from the in-memory dictionary."""
        return self.profiles.get(character_name)

    def add_profile(self, character_name: str, profile: CharacterProfile):
        """Add or update a character profile in memory and save it to its file."""
        is_new = character_name not in self.profiles
        self.profiles[character_name] = profile
        self._save_single_profile(profile)
        self.logger.info(f"{'Added new' if is_new else 'Updated'} character profile: {character_name}")

    def list_characters(self) -> List[str]:
        """List all character names from the in-memory profiles."""
        return sorted(list(self.profiles.keys()))

    def export_profile(self, character_name: str, export_path: Path):
        """Export a single character profile to a JSON file at the specified path."""
        profile = self.get_profile(character_name)
        if not profile:
            self.logger.error(f"Cannot export - character '{character_name}' not found")
            raise ValueError(f"Character '{character_name}' not found")

        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(profile), f, indent=2, ensure_ascii=False)
            self.logger.info(f"Exported character '{character_name}' to {export_path}")
        except Exception as e:
            self.logger.error(f"Failed to export character '{character_name}': {e}", exc_info=True)
            raise

    def import_profile(self, import_path: Path):
        """Import a character profile from a JSON file and save it."""
        try:
            self.logger.info(f"Importing character profile from {import_path}")
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both old and new export formats
            if list(data.keys()) == [next(iter(data))]: # Old format: {"char_name": {...}}
                char_name = next(iter(data))
                profile_data = data[char_name]
            else: # New format: {...}
                profile_data = data
                char_name = profile_data.get("name")

            if not char_name:
                raise ValueError("Imported JSON does not contain a character name.")

            profile = self._parse_profile_data(profile_data)
            self.add_profile(char_name, profile)
            self.logger.info(f"Successfully imported and saved character '{char_name}'")
            return char_name

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
        md += "## [NOTE] Basic Information\n\n"
        md += f"- **Player**: {profile.player}\n"
        md += f"- **Campaign**: {profile.campaign}\n"

        if profile.aliases:
            md += f"- **Also known as**: {', '.join(profile.aliases)}\n"

        if profile.first_session:
            md += f"- **First Appearance**: {profile.first_session}\n"

        md += "\n"

        # Description
        if profile.description:
            md += "## [BOOK] Description\n\n"
            md += profile.description + "\n\n"

        if profile.appearance:
            md += "### [PERSON] Appearance\n\n"
            md += profile.appearance + "\n\n"

        if profile.personality:
            md += "### [THEATER] Personality\n\n"
            md += profile.personality + "\n\n"

        if profile.backstory:
            md += "### [SCROLL] Backstory\n\n"
            md += profile.backstory + "\n\n"

        # Goals
        if profile.current_goals or profile.completed_goals:
            md += "## [TARGET] Goals & Progress\n\n"

            if profile.current_goals:
                md += "### Current Objectives\n\n"
                for goal in profile.current_goals:
                    md += f"- [ ] {goal}\n"
                md += "\n"

            if profile.completed_goals:
                md += "### Completed Goals\n\n"
                for goal in profile.completed_goals:
                    md += f"- [DONE] {goal}\n"
                md += "\n"

        # Notable Actions
        if profile.notable_actions:
            md += "## [COMBAT] Notable Actions\n\n"

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
                'combat': '[COMBAT]',
                'social': '[CHAT]',
                'exploration': '[EXPLORE]',
                'magic': '[MAGIC]',
                'divine': '[DIVINE]',
                'general': '[GENERAL]'
            }

            # Display recent actions (last 15)
            recent_actions = profile.notable_actions[-15:] if len(profile.notable_actions) > 15 else profile.notable_actions
            for action in recent_actions:
                icon = action_icons.get(action.type, '-')
                md += f"**{action.session}** {icon} _{action.type.title()}_\n"
                md += f"  {action.description}\n\n"

        # Inventory
        if profile.inventory:
            md += "## [BAG] Inventory\n\n"
            md += f"_Carrying {len(profile.inventory)} items_\n\n"

            # Category icon mapping
            from .ui.constants import StatusIndicators
            category_icons = {
                'weapon': StatusIndicators.WEAPON,
                'armor': StatusIndicators.ARMOR,
                'magical': StatusIndicators.MAGICAL,
                'consumable': StatusIndicators.CONSUMABLE,
                'quest': StatusIndicators.QUEST_ITEM,
                'equipment': StatusIndicators.EQUIPMENT,
                'misc': StatusIndicators.MISC
            }

            by_category = {}
            for item in profile.inventory:
                by_category.setdefault(item.category, []).append(item)

            for category, items in sorted(by_category.items()):
                icon = category_icons.get(category, '-')
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
            md += "## [HANDSHAKE] Relationships\n\n"

            # Relationship type icons
            rel_icons = {
                'ally': StatusIndicators.ALLY,
                'enemy': StatusIndicators.ENEMY,
                'neutral': StatusIndicators.NEUTRAL,
                'mentor': StatusIndicators.MENTOR,
                'student': StatusIndicators.STUDENT,
                'friend': StatusIndicators.FRIEND,
                'rival': StatusIndicators.RIVAL,
                'family': StatusIndicators.FAMILY,
                'deity': StatusIndicators.DEITY,
                'bonded spirit': StatusIndicators.SPIRIT,
                'companion': StatusIndicators.COMPANION,
                'employer': StatusIndicators.EMPLOYER,
                'master': StatusIndicators.MASTER,
                'rescued by': StatusIndicators.RESCUED
            }

            for rel in profile.relationships:
                icon = rel_icons.get(rel.relationship_type.lower(), '-')
                md += f"**{icon} {rel.name}** _{rel.relationship_type}_\n"
                if rel.description:
                    md += f"  {rel.description}\n"
                if rel.first_met:
                    md += f"  _First met: {rel.first_met}_\n"
                md += "\n"

        # Memorable Quotes
        if profile.memorable_quotes:
            md += "## [CHAT] Memorable Quotes\n\n"
            for quote in profile.memorable_quotes[-5:]:  # Last 5
                md += f"> \"{quote.quote}\"\n\n"
                if quote.context:
                    md += f"_Context: {quote.context}_\n"
                md += f"_- {quote.session}_\n\n"

        # Development
        if profile.development_notes:
            md += "## [UP] Character Development\n\n"

            # Development category icons
            from .ui.constants import StatusIndicators
            dev_icons = {
                'personality': StatusIndicators.PERSONALITY,
                'backstory': StatusIndicators.BACKSTORY,
                'goal': StatusIndicators.QUEST_ACTIVE,  # Reuse quest active icon
                'fear': StatusIndicators.FEAR,
                'trait': StatusIndicators.TRAIT,
                'divine connection': StatusIndicators.DIVINE,
                'general': StatusIndicators.GENERAL
            }

            for dev in profile.development_notes:
                icon = dev_icons.get(dev.category.lower(), '-')
                md += f"**{dev.session}** {icon} _{dev.category.title()}_\n"
                md += f"  {dev.note}\n\n"

        # Notes
        if profile.dm_notes:
            md += "## [NOTE] DM Notes\n\n"
            md += profile.dm_notes + "\n\n"

        if profile.player_notes:
            md += "## [WRITE] Player Notes\n\n"
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

    def merge_updates(self, character_name: str, updates: Dict[str, List['ProfileUpdate']]) -> Optional[CharacterProfile]:
        """Merge suggested updates into a character profile."""
        profile = self.get_profile(character_name)
        if not profile:
            self.logger.error(f"Cannot merge updates - character '{character_name}' not found")
            return None

        for category, moments in updates.items():
            for moment in moments:
                session_value = moment.session_id or moment.timestamp or "unknown_session"
                moment_type = moment.type or "general"
                if category == "notable_actions":
                    profile.notable_actions.append(CharacterAction(
                        session=session_value,
                        description=moment.content,
                        type=moment_type
                    ))
                elif category == "memorable_quotes":
                    profile.memorable_quotes.append(CharacterQuote(
                        session=session_value,
                        quote=moment.content,
                        context=moment.context
                    ))
                elif category == "development_notes":
                    profile.development_notes.append(CharacterDevelopment(
                        session=session_value,
                        note=moment.content,
                        category=moment_type
                    ))
                elif category == "relationships":
                    if moment.relationships:
                        for relation in moment.relationships:
                            profile.relationships.append(CharacterRelationship(
                                name=relation.get("character", moment.content),
                                relationship_type=relation.get("type", moment_type),
                                description=relation.get("description"),
                                first_met=session_value
                            ))
                    else:
                        profile.relationships.append(CharacterRelationship(
                            name=moment.content,
                            relationship_type=moment_type,
                            first_met=session_value
                        ))
                elif category == "inventory_changes":
                    profile.inventory.append(CharacterItem(
                        name=moment.metadata.get("item_name", moment.content) if moment.metadata else moment.content,
                        description=moment.context,
                        session_acquired=session_value,
                        category=moment_type
                    ))
                else:
                    self.logger.debug("Unhandled profile update category '%s' for '%s'", category, character_name)
        
        self.add_profile(character_name, profile)
        return profile
