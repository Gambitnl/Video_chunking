"""Party configuration management for D&D sessions"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from .config import Config
from .logger import get_logger
from .file_lock import get_file_lock


logger = get_logger(__name__)


@dataclass
class Character:
    """Represents a D&D character"""
    name: str
    player: str
    race: str
    class_name: str
    description: Optional[str] = None
    aliases: Optional[List[str]] = None  # Alternative names/nicknames


@dataclass
class Party:
    """Represents a D&D party configuration"""
    party_name: str
    dm_name: str
    characters: List[Character]
    campaign: Optional[str] = None
    notes: Optional[str] = None


class PartyConfigManager:
    """Manages party configurations for sessions"""

    def __init__(self, config_file: Path = None):
        self.config_file = config_file or (Config.MODELS_DIR / "parties.json")
        self.parties = self._load_parties()
        self._ensure_default_party()

    def _load_parties(self) -> Dict[str, Party]:
        """Load parties from JSON file"""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            parties = {}
            for party_id, party_data in data.items():
                characters = [
                    Character(**char_data)
                    for char_data in party_data['characters']
                ]
                party_data['characters'] = characters
                parties[party_id] = Party(**party_data)

            return parties
        except Exception as e:
            logger.warning(f"Could not load parties: {e}", exc_info=True)
            return {}

    def _ensure_default_party(self):
        """Ensure the default party configuration exists"""
        if "default" not in self.parties:
            self.parties["default"] = self._create_default_party()
            self.save_parties()

    def _create_default_party(self) -> Party:
        """Create the default party configuration"""
        return Party(
            party_name="The Broken Seekers",
            dm_name="DM",
            campaign="Gaia Adventures",
            characters=[
                Character(
                    name="Sha'ek Mindfa'ek",
                    player="Player1",
                    race="Adar (from Adar)",
                    class_name="Cleric of Ioun",
                    description="The Broken - A hardened veteran cleric with glowing green eyes. "
                                "Survived the Smelting ritual, connected to Quori spirit Golos. "
                                "Wears heavy chain mail, carries a large bag and shield with Ioun's emblem.",
                    aliases=["Sha'ek", "The Broken", "The Defect"]
                ),
                Character(
                    name="Pipira Shimmerlock",
                    player="Player2",
                    race="Gnome",
                    class_name="Wizard",
                    description="Pip - An ambitious gnome student wizard. Perceptive, eager to learn, "
                                "fond of experiments and tinkering with mechanical objects.",
                    aliases=["Pip", "Pipira"]
                ),
                Character(
                    name="Fan'nar Khe'Lek",
                    player="Player3",
                    race="Winter Eladrin",
                    class_name="Handyman/Ranger",
                    description="Pas'Ta - Snow-white skin, blond hair, wears fur clothing. "
                                "Works for Culdor Academy. Sharp-witted, mysterious, prefers working alone. "
                                "Uses archery and flail, carries a magical black leather Grimoire.",
                    aliases=["Pas'Ta", "Fan'nar"]
                ),
                Character(
                    name="Furnax",
                    player="Companion",
                    race="Frost Hellhound",
                    class_name="Beast Companion",
                    description="Pip's companion - Black with dark blue stripes, cold aura. "
                                "Unruly but well-trained, intelligent, rescued by the academy.",
                    aliases=["Furnax"]
                )
            ],
            notes="Party exploring Gaia. Suspicious of non-Gaian entities. "
                  "Connected to Culdor Academy. Characters have experienced magical chaos events."
        )

    def save_parties(self):
        """Save parties to JSON file with file locking to prevent concurrent write conflicts."""
        self.config_file.parent.mkdir(exist_ok=True, parents=True)

        # Use file lock to prevent race conditions
        lock = get_file_lock(self.config_file)
        with lock:
            # Convert to serializable format
            data = {}
            for party_id, party in self.parties.items():
                party_dict = asdict(party)
                data[party_id] = party_dict

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def get_party(self, party_id: str = "default") -> Optional[Party]:
        """Get a party by ID"""
        return self.parties.get(party_id)

    def list_parties(self) -> List[str]:
        """List all party IDs"""
        return list(self.parties.keys())

    def add_party(self, party_id: str, party: Party):
        """Add or update a party with validation"""
        # Validate no duplicate character names
        char_names = [c.name for c in party.characters]
        if len(char_names) != len(set(char_names)):
            duplicates = [name for name in char_names if char_names.count(name) > 1]
            raise ValueError(f"Duplicate character names not allowed: {', '.join(set(duplicates))}")

        # Validate no duplicate player names (except for Companion, NPC, Beast which can repeat)
        player_names = [c.player for c in party.characters
                       if c.player.lower() not in ["companion", "npc", "beast"]]
        if len(player_names) != len(set(player_names)):
            duplicates = [name for name in player_names if player_names.count(name) > 1]
            raise ValueError(f"Duplicate player names not allowed: {', '.join(set(duplicates))}")

        self.parties[party_id] = party
        self.save_parties()

    def delete_party(self, party_id: str):
        """Delete a party (cannot delete default)"""
        if party_id == "default":
            raise ValueError("Cannot delete default party")
        if party_id in self.parties:
            del self.parties[party_id]
            self.save_parties()

    def get_character_names(self, party_id: str = "default") -> List[str]:
        """Get all character names from a party"""
        party = self.get_party(party_id)
        if not party:
            return []
        return [char.name for char in party.characters]

    def get_player_names(self, party_id: str = "default") -> List[str]:
        """Get all unique player names from a party (excluding companions)"""
        party = self.get_party(party_id)
        if not party:
            return []

        players = set()
        for char in party.characters:
            if char.player.lower() not in ["companion", "npc", "beast"]:
                players.add(char.player)

        # Add DM
        players.add(party.dm_name)
        return sorted(list(players))

    def get_all_names(self, party_id: str = "default") -> Dict[str, List[str]]:
        """Get all names including aliases for better recognition"""
        party = self.get_party(party_id)
        if not party:
            return {}

        names = {}
        for char in party.characters:
            all_names = [char.name]
            if char.aliases:
                all_names.extend(char.aliases)
            names[char.name] = all_names

        return names

    def get_character_description(self, character_name: str, party_id: str = "default") -> Optional[str]:
        """Get character description for LLM context"""
        party = self.get_party(party_id)
        if not party:
            return None

        for char in party.characters:
            if char.name == character_name or (char.aliases and character_name in char.aliases):
                desc_parts = [
                    f"{char.name} ({char.class_name})",
                    f"Player: {char.player}",
                    f"Race: {char.race}"
                ]
                if char.description:
                    desc_parts.append(f"Description: {char.description}")
                if char.aliases:
                    desc_parts.append(f"Also known as: {', '.join(char.aliases)}")
                return ". ".join(desc_parts)

        return None

    def get_party_context_for_llm(self, party_id: str = "default") -> str:
        """Get formatted party information for LLM prompts"""
        party = self.get_party(party_id)
        if not party:
            return ""

        context = f"D&D Party: {party.party_name}\n"
        context += f"Campaign: {party.campaign or 'Unknown'}\n"
        context += f"DM: {party.dm_name}\n\n"
        context += "Characters:\n"

        for char in party.characters:
            context += f"- {char.name}"
            if char.aliases:
                context += f" (aka {', '.join(char.aliases)})"
            context += f": {char.race} {char.class_name}"
            if char.player != "Companion":
                context += f" (played by {char.player})"
            context += "\n"

        if party.notes:
            context += f"\nNotes: {party.notes}\n"

        return context

    def export_party(self, party_id: str, export_path: Path):
        """Export a single party to a JSON file"""
        party = self.get_party(party_id)
        if not party:
            raise ValueError(f"Party '{party_id}' not found")

        data = {party_id: asdict(party)}
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_party(self, import_path: Path, party_id: Optional[str] = None):
        """
        Import a party from a JSON file.
        If party_id is provided, use that ID; otherwise use the ID from the file.
        """
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle both single party and multiple parties format
        if isinstance(data, dict):
            for file_party_id, party_data in data.items():
                # Use provided party_id or the one from file
                new_party_id = party_id or file_party_id

                # Convert to Party object
                characters = [
                    Character(**char_data)
                    for char_data in party_data['characters']
                ]
                party_data['characters'] = characters
                new_party = Party(**party_data)

                # Add to parties
                self.add_party(new_party_id, new_party)
                return new_party_id

        raise ValueError("Invalid party file format")

    def export_all_parties(self, export_path: Path):
        """Export all parties to a JSON file"""
        data = {}
        for party_id, party in self.parties.items():
            data[party_id] = asdict(party)

        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


@dataclass
class CampaignSettings:
    """Processing settings for a campaign"""
    num_speakers: int = 4
    skip_diarization: bool = False
    skip_classification: bool = False
    skip_snippets: bool = True
    skip_knowledge: bool = False
    session_id_prefix: str = "Session_"
    auto_number_sessions: bool = False


@dataclass
class Campaign:
    """Represents a campaign profile with party and settings"""
    name: str
    party_id: str
    settings: CampaignSettings
    description: Optional[str] = None
    notes: Optional[str] = None


class CampaignManager:
    """Manages campaign profiles"""

    def __init__(self, config_file: Path = None):
        self.config_file = config_file or (Config.MODELS_DIR / "campaigns.json")
        self.campaigns = self._load_campaigns()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure the campaign config directory exists."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

    def _generate_campaign_id(self, base_id: str = "campaign") -> str:
        """Generate a unique campaign identifier."""
        counter = 1
        candidate = f"{base_id}_{counter:03d}"
        while candidate in self.campaigns:
            counter += 1
            candidate = f"{base_id}_{counter:03d}"
        return candidate

    def _generate_campaign_name(self, base_name: str = "New Campaign") -> str:
        """Generate a human readable campaign name."""
        existing = {campaign.name for campaign in self.campaigns.values()}
        if base_name not in existing:
            return base_name

        counter = 2
        candidate = f"{base_name} {counter}"
        while candidate in existing:
            counter += 1
            candidate = f"{base_name} {counter}"
        return candidate

    def _load_campaigns(self) -> Dict[str, Campaign]:
        """Load campaigns from JSON file"""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            campaigns = {}
            for campaign_id, campaign_data in data.items():
                settings_data = campaign_data.get('settings', {})
                settings = CampaignSettings(**settings_data)

                campaign = Campaign(
                    name=campaign_data['name'],
                    party_id=campaign_data['party_id'],
                    settings=settings,
                    description=campaign_data.get('description'),
                    notes=campaign_data.get('notes')
                )
                campaigns[campaign_id] = campaign

            return campaigns
        except Exception as e:
            logger.error(f"Error loading campaigns: {e}", exc_info=True)
            return {}

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get a campaign by ID"""
        return self.campaigns.get(campaign_id)

    def list_campaigns(self) -> List[str]:
        """List all campaign IDs"""
        return list(self.campaigns.keys())

    def get_campaign_names(self) -> Dict[str, str]:
        """Get mapping of campaign IDs to display names"""
        return {cid: campaign.name for cid, campaign in self.campaigns.items()}

    def add_campaign(self, campaign_id: str, campaign: Campaign):
        """Add or update a campaign"""
        self.campaigns[campaign_id] = campaign
        self._save_campaigns()

    def rename_campaign(self, campaign_id: str, new_name: str) -> bool:
        """Renames a campaign after validation."""
        new_name = new_name.strip()
        if not new_name:
            logger.error("Campaign rename failed: New name cannot be empty.")
            return False

        if campaign_id not in self.campaigns:
            logger.error(f"Campaign rename failed: ID '{campaign_id}' not found.")
            return False

        # Check if new name is already in use by another campaign
        for cid, camp in self.campaigns.items():
            if cid != campaign_id and camp.name.lower() == new_name.lower():
                logger.error(f"Campaign rename failed: Name '{new_name}' is already in use.")
                return False

        self.campaigns[campaign_id].name = new_name
        self._save_campaigns()
        logger.info(f"Renamed campaign '{campaign_id}' to '{new_name}'.")
        return True

    def delete_campaign(self, campaign_id: str) -> bool:
        """Deletes a campaign."""
        if campaign_id not in self.campaigns:
            logger.warning(f"Attempted to delete non-existent campaign '{campaign_id}'.")
            return False

        del self.campaigns[campaign_id]
        self._save_campaigns()
        logger.info(f"Deleted campaign '{campaign_id}'.")
        return True

    def create_blank_campaign(
        self,
        name: Optional[str] = None,
        base_id: str = "campaign",
    ) -> Tuple[str, Campaign]:
        """
        Create and persist a blank campaign profile.

        Args:
            name: Optional display name. When omitted a unique "New Campaign" name is generated.
            base_id: Base identifier slug used to generate the campaign ID.

        Returns:
            Tuple of (campaign_id, Campaign instance).
        """
        campaign_id = self._generate_campaign_id(base_id)
        campaign_name = name.strip() if name and name.strip() else self._generate_campaign_name()

        blank_campaign = Campaign(
            name=campaign_name,
            party_id="",
            settings=CampaignSettings(),
            description=None,
            notes=None,
        )
        self.add_campaign(campaign_id, blank_campaign)
        return campaign_id, blank_campaign

    def _save_campaigns(self):
        """Save campaigns to JSON file with file locking to prevent concurrent write conflicts."""
        # Use file lock to prevent race conditions
        lock = get_file_lock(self.config_file)
        with lock:
            data = {}
            for campaign_id, campaign in self.campaigns.items():
                campaign_dict = asdict(campaign)
                data[campaign_id] = campaign_dict

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
