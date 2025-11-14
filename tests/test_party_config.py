"""Comprehensive test suite for party_config.py

Tests cover:
- Configuration loading and saving
- Validation (duplicate names, default party protection)
- Player-character mappings
- Error recovery (corrupted JSON, missing files)
- Import/export functionality
- Campaign management
"""

import json
import pytest
from pathlib import Path
from dataclasses import asdict

from src.party_config import (
    Character,
    Party,
    PartyConfigManager,
    Campaign,
    CampaignSettings,
    CampaignManager,
)


# ============================================================================
# Character Dataclass Tests
# ============================================================================


class TestCharacterDataclass:
    """Test Character dataclass functionality"""

    def test_character_basic_creation(self):
        """Test creating a basic character"""
        char = Character(
            name="Aragorn",
            player="Alice",
            race="Human",
            class_name="Ranger"
        )
        assert char.name == "Aragorn"
        assert char.player == "Alice"
        assert char.race == "Human"
        assert char.class_name == "Ranger"
        assert char.description is None
        assert char.aliases is None

    def test_character_with_all_fields(self):
        """Test creating character with all optional fields"""
        char = Character(
            name="Legolas",
            player="Bob",
            race="Elf",
            class_name="Ranger",
            description="Keen-eyed archer from Mirkwood",
            aliases=["Greenleaf", "Elf-friend"]
        )
        assert char.description == "Keen-eyed archer from Mirkwood"
        assert char.aliases == ["Greenleaf", "Elf-friend"]

    def test_character_serialization(self):
        """Test converting character to dict"""
        char = Character(
            name="Gimli",
            player="Charlie",
            race="Dwarf",
            class_name="Fighter",
            aliases=["Son of Gloin"]
        )
        char_dict = asdict(char)
        assert char_dict['name'] == "Gimli"
        assert char_dict['player'] == "Charlie"
        assert char_dict['aliases'] == ["Son of Gloin"]


# ============================================================================
# Party Dataclass Tests
# ============================================================================


class TestPartyDataclass:
    """Test Party dataclass functionality"""

    def test_party_basic_creation(self):
        """Test creating a basic party"""
        characters = [
            Character("Frodo", "Player1", "Hobbit", "Rogue"),
            Character("Sam", "Player2", "Hobbit", "Fighter")
        ]
        party = Party(
            party_name="Fellowship",
            dm_name="DM Dave",
            characters=characters
        )
        assert party.party_name == "Fellowship"
        assert party.dm_name == "DM Dave"
        assert len(party.characters) == 2
        assert party.campaign is None
        assert party.notes is None

    def test_party_with_optional_fields(self):
        """Test creating party with campaign and notes"""
        characters = [Character("Test", "Player1", "Human", "Wizard")]
        party = Party(
            party_name="Test Party",
            dm_name="DM",
            characters=characters,
            campaign="Lost Mine of Phandelver",
            notes="Starting adventure"
        )
        assert party.campaign == "Lost Mine of Phandelver"
        assert party.notes == "Starting adventure"

    def test_party_serialization(self):
        """Test converting party to dict"""
        characters = [Character("Test", "Player1", "Human", "Wizard")]
        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=characters
        )
        party_dict = asdict(party)
        assert party_dict['party_name'] == "Test"
        assert party_dict['dm_name'] == "DM"
        assert isinstance(party_dict['characters'], list)


# ============================================================================
# PartyConfigManager Initialization Tests
# ============================================================================


class TestPartyConfigManagerInit:
    """Test PartyConfigManager initialization"""

    def test_init_creates_default_party_when_no_file(self, tmp_path):
        """Test initialization creates default party when config doesn't exist"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        # Should have default party
        assert "default" in manager.parties
        default_party = manager.parties["default"]
        assert default_party.party_name == "The Broken Seekers"
        assert default_party.dm_name == "DM"
        assert len(default_party.characters) == 4

        # Should create config file
        assert config_file.exists()

    def test_init_loads_existing_parties(self, tmp_path):
        """Test initialization loads existing parties from file"""
        config_file = tmp_path / "parties.json"

        # Create existing config
        existing_data = {
            "custom_party": {
                "party_name": "Custom Party",
                "dm_name": "Custom DM",
                "characters": [
                    {
                        "name": "TestChar",
                        "player": "TestPlayer",
                        "race": "Human",
                        "class_name": "Fighter",
                        "description": None,
                        "aliases": None
                    }
                ],
                "campaign": "Test Campaign",
                "notes": None
            }
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f)

        manager = PartyConfigManager(config_file=config_file)

        # Should load custom party
        assert "custom_party" in manager.parties
        custom = manager.parties["custom_party"]
        assert custom.party_name == "Custom Party"
        assert custom.dm_name == "Custom DM"
        assert len(custom.characters) == 1
        assert custom.characters[0].name == "TestChar"

        # Should also ensure default party exists
        assert "default" in manager.parties

    def test_init_with_custom_path(self, tmp_path):
        """Test initialization with custom config file path"""
        custom_path = tmp_path / "custom" / "config.json"
        manager = PartyConfigManager(config_file=custom_path)

        # Should create parent directories
        assert custom_path.parent.exists()
        assert custom_path.exists()
        assert "default" in manager.parties

    def test_init_handles_corrupted_json(self, tmp_path):
        """Test initialization gracefully handles corrupted JSON"""
        config_file = tmp_path / "parties.json"

        # Write invalid JSON
        with open(config_file, 'w') as f:
            f.write("{invalid json content")

        # Should not crash, should create default party
        manager = PartyConfigManager(config_file=config_file)
        assert "default" in manager.parties
        assert len(manager.parties) >= 1


# ============================================================================
# PartyConfigManager CRUD Tests
# ============================================================================


class TestPartyConfigManagerCRUD:
    """Test Party CRUD operations"""

    def test_add_party_basic(self, tmp_path):
        """Test adding a new party"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        new_party = Party(
            party_name="New Party",
            dm_name="New DM",
            characters=[
                Character("Hero1", "Player1", "Human", "Fighter"),
                Character("Hero2", "Player2", "Elf", "Wizard")
            ]
        )

        manager.add_party("new_party", new_party)

        # Should be in memory
        assert "new_party" in manager.parties
        assert manager.parties["new_party"].party_name == "New Party"

        # Should be persisted to file
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert "new_party" in data

    def test_add_party_overwrites_existing(self, tmp_path):
        """Test adding party with existing ID overwrites it"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party1 = Party(
            party_name="Party v1",
            dm_name="DM",
            characters=[Character("Test", "Player1", "Human", "Fighter")]
        )
        party2 = Party(
            party_name="Party v2",
            dm_name="DM",
            characters=[Character("Test", "Player1", "Human", "Fighter")]
        )

        manager.add_party("test_party", party1)
        assert manager.parties["test_party"].party_name == "Party v1"

        manager.add_party("test_party", party2)
        assert manager.parties["test_party"].party_name == "Party v2"

    def test_get_party_existing(self, tmp_path):
        """Test getting an existing party"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        # Get default party
        default = manager.get_party("default")
        assert default is not None
        assert default.party_name == "The Broken Seekers"

    def test_get_party_nonexistent(self, tmp_path):
        """Test getting non-existent party returns None"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        result = manager.get_party("nonexistent")
        assert result is None

    def test_list_parties(self, tmp_path):
        """Test listing all party IDs"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party1 = Party("Party1", "DM", [Character("C1", "P1", "Human", "Fighter")])
        party2 = Party("Party2", "DM", [Character("C2", "P2", "Elf", "Wizard")])

        manager.add_party("party1", party1)
        manager.add_party("party2", party2)

        party_list = manager.list_parties()
        assert "default" in party_list
        assert "party1" in party_list
        assert "party2" in party_list
        assert len(party_list) >= 3

    def test_delete_party_success(self, tmp_path):
        """Test deleting a non-default party"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party("Test", "DM", [Character("C", "P", "Human", "Fighter")])
        manager.add_party("deletable", party)
        assert "deletable" in manager.parties

        manager.delete_party("deletable")
        assert "deletable" not in manager.parties

        # Should be removed from file
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert "deletable" not in data

    def test_delete_default_party_raises_error(self, tmp_path):
        """Test deleting default party raises ValueError"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        with pytest.raises(ValueError, match="Cannot delete default party"):
            manager.delete_party("default")

        # Default party should still exist
        assert "default" in manager.parties

    def test_delete_nonexistent_party_silent(self, tmp_path):
        """Test deleting non-existent party doesn't error"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        # Should not raise error
        manager.delete_party("nonexistent")


# ============================================================================
# Validation Tests
# ============================================================================


class TestPartyConfigValidation:
    """Test party configuration validation"""

    def test_add_party_duplicate_character_names_raises_error(self, tmp_path):
        """Test adding party with duplicate character names raises ValueError"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Duplicate Test",
            dm_name="DM",
            characters=[
                Character("Aragorn", "Player1", "Human", "Fighter"),
                Character("Aragorn", "Player2", "Elf", "Wizard")  # Duplicate name
            ]
        )

        with pytest.raises(ValueError, match="Duplicate character names not allowed"):
            manager.add_party("dup_test", party)

    def test_add_party_duplicate_player_names_raises_error(self, tmp_path):
        """Test adding party with duplicate player names raises ValueError"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Duplicate Player Test",
            dm_name="DM",
            characters=[
                Character("Char1", "Alice", "Human", "Fighter"),
                Character("Char2", "Alice", "Elf", "Wizard")  # Duplicate player
            ]
        )

        with pytest.raises(ValueError, match="Duplicate player names not allowed"):
            manager.add_party("dup_player_test", party)

    def test_add_party_allows_multiple_companions(self, tmp_path):
        """Test that multiple Companion/NPC/Beast characters are allowed"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Companion Test",
            dm_name="DM",
            characters=[
                Character("Hero", "Player1", "Human", "Fighter"),
                Character("Pet1", "Companion", "Wolf", "Beast"),
                Character("Pet2", "Companion", "Raven", "Beast"),
                Character("Hireling", "NPC", "Human", "Commoner")
            ]
        )

        # Should not raise error
        manager.add_party("companion_test", party)
        assert "companion_test" in manager.parties

    def test_validation_with_mixed_case_companion(self, tmp_path):
        """Test validation handles mixed-case companion/npc/beast"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Mixed Case Test",
            dm_name="DM",
            characters=[
                Character("Hero", "Player1", "Human", "Fighter"),
                Character("Pet1", "COMPANION", "Wolf", "Beast"),
                Character("Pet2", "Npc", "Human", "Commoner"),
                Character("Pet3", "BeAsT", "Owl", "Beast")
            ]
        )

        # Should not raise error (case-insensitive check)
        manager.add_party("mixed_case_test", party)
        assert "mixed_case_test" in manager.parties


# ============================================================================
# Character/Player Mapping Tests
# ============================================================================


class TestCharacterPlayerMappings:
    """Test character and player name extraction"""

    def test_get_character_names(self, tmp_path):
        """Test extracting character names from party"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        default_names = manager.get_character_names("default")
        assert "Sha'ek Mindfa'ek" in default_names
        assert "Pipira Shimmerlock" in default_names
        assert "Fan'nar Khe'Lek" in default_names
        assert "Furnax" in default_names

    def test_get_character_names_nonexistent_party(self, tmp_path):
        """Test getting character names from non-existent party returns empty list"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        names = manager.get_character_names("nonexistent")
        assert names == []

    def test_get_player_names(self, tmp_path):
        """Test extracting player names from party"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="Game Master",
            characters=[
                Character("Char1", "Alice", "Human", "Fighter"),
                Character("Char2", "Bob", "Elf", "Wizard"),
                Character("Pet", "Companion", "Wolf", "Beast")
            ]
        )
        manager.add_party("test", party)

        player_names = manager.get_player_names("test")
        assert "Alice" in player_names
        assert "Bob" in player_names
        assert "Game Master" in player_names  # DM included
        assert "Companion" not in player_names  # Companion excluded

    def test_get_player_names_sorted(self, tmp_path):
        """Test player names are returned sorted"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="Zoe",
            characters=[
                Character("C1", "Charlie", "Human", "Fighter"),
                Character("C2", "Alice", "Elf", "Wizard"),
                Character("C3", "Bob", "Dwarf", "Cleric")
            ]
        )
        manager.add_party("test", party)

        player_names = manager.get_player_names("test")
        # Should be sorted
        assert player_names == sorted(player_names)

    def test_get_player_names_excludes_npc_beast(self, tmp_path):
        """Test player names exclude NPC and Beast"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[
                Character("Hero", "Alice", "Human", "Fighter"),
                Character("Shopkeeper", "NPC", "Human", "Commoner"),
                Character("Mount", "Beast", "Horse", "Beast")
            ]
        )
        manager.add_party("test", party)

        player_names = manager.get_player_names("test")
        assert "Alice" in player_names
        assert "DM" in player_names
        assert "NPC" not in player_names
        assert "Beast" not in player_names

    def test_get_all_names_with_aliases(self, tmp_path):
        """Test getting all names including aliases"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[
                Character("Aragorn", "Player1", "Human", "Ranger",
                         aliases=["Strider", "Elessar"]),
                Character("Gandalf", "Player2", "Wizard", "Wizard",
                         aliases=["Mithrandir", "The Grey"])
            ]
        )
        manager.add_party("test", party)

        all_names = manager.get_all_names("test")
        assert "Aragorn" in all_names
        assert "Strider" in all_names["Aragorn"]
        assert "Elessar" in all_names["Aragorn"]
        assert "Gandalf" in all_names
        assert "Mithrandir" in all_names["Gandalf"]

    def test_get_all_names_without_aliases(self, tmp_path):
        """Test getting names for character without aliases"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[
                Character("Simple", "Player1", "Human", "Fighter")
            ]
        )
        manager.add_party("test", party)

        all_names = manager.get_all_names("test")
        assert "Simple" in all_names
        assert all_names["Simple"] == ["Simple"]


# ============================================================================
# Character Description Tests
# ============================================================================


class TestCharacterDescriptions:
    """Test character description retrieval"""

    def test_get_character_description_by_name(self, tmp_path):
        """Test getting character description by exact name"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[
                Character(
                    "Aragorn",
                    "Player1",
                    "Human",
                    "Ranger",
                    description="Heir to the throne of Gondor"
                )
            ]
        )
        manager.add_party("test", party)

        desc = manager.get_character_description("Aragorn", "test")
        assert desc is not None
        assert "Aragorn" in desc
        assert "Ranger" in desc
        assert "Human" in desc
        assert "Player1" in desc
        assert "Heir to the throne of Gondor" in desc

    def test_get_character_description_by_alias(self, tmp_path):
        """Test getting character description by alias"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[
                Character(
                    "Aragorn",
                    "Player1",
                    "Human",
                    "Ranger",
                    description="Ranger from the North",
                    aliases=["Strider"]
                )
            ]
        )
        manager.add_party("test", party)

        desc = manager.get_character_description("Strider", "test")
        assert desc is not None
        assert "Aragorn" in desc
        assert "Strider" in desc

    def test_get_character_description_nonexistent(self, tmp_path):
        """Test getting description for non-existent character returns None"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        desc = manager.get_character_description("Nonexistent", "default")
        assert desc is None

    def test_get_character_description_includes_aliases(self, tmp_path):
        """Test character description includes aliases section"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[
                Character(
                    "Gandalf",
                    "Player1",
                    "Wizard",
                    "Wizard",
                    aliases=["Mithrandir", "The Grey", "Stormcrow"]
                )
            ]
        )
        manager.add_party("test", party)

        desc = manager.get_character_description("Gandalf", "test")
        assert "Also known as" in desc
        assert "Mithrandir" in desc
        assert "The Grey" in desc


# ============================================================================
# LLM Context Generation Tests
# ============================================================================


class TestLLMContextGeneration:
    """Test party context generation for LLM prompts"""

    def test_get_party_context_for_llm_basic(self, tmp_path):
        """Test generating basic party context for LLM"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="The Fellowship",
            dm_name="Tolkien",
            campaign="The Lord of the Rings",
            characters=[
                Character("Frodo", "Player1", "Hobbit", "Rogue"),
                Character("Sam", "Player2", "Hobbit", "Fighter")
            ]
        )
        manager.add_party("fellowship", party)

        context = manager.get_party_context_for_llm("fellowship")
        assert "The Fellowship" in context
        assert "Tolkien" in context
        assert "The Lord of the Rings" in context
        assert "Frodo" in context
        assert "Sam" in context
        assert "Hobbit" in context

    def test_get_party_context_includes_aliases(self, tmp_path):
        """Test LLM context includes character aliases"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[
                Character(
                    "Aragorn",
                    "Player1",
                    "Human",
                    "Ranger",
                    aliases=["Strider"]
                )
            ]
        )
        manager.add_party("test", party)

        context = manager.get_party_context_for_llm("test")
        assert "Aragorn" in context
        assert "aka" in context.lower() or "also known as" in context.lower()
        assert "Strider" in context

    def test_get_party_context_handles_companion(self, tmp_path):
        """Test LLM context handles Companion characters"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[
                Character("Hero", "Alice", "Human", "Fighter"),
                Character("Pet", "Companion", "Wolf", "Beast")
            ]
        )
        manager.add_party("test", party)

        context = manager.get_party_context_for_llm("test")
        assert "Hero" in context
        assert "Pet" in context
        # Companion should not show "(played by Companion)"
        assert "played by Alice" in context

    def test_get_party_context_includes_notes(self, tmp_path):
        """Test LLM context includes party notes"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Test",
            dm_name="DM",
            characters=[Character("Hero", "Player1", "Human", "Fighter")],
            notes="The party is investigating mysterious disappearances"
        )
        manager.add_party("test", party)

        context = manager.get_party_context_for_llm("test")
        assert "The party is investigating mysterious disappearances" in context

    def test_get_party_context_nonexistent_party(self, tmp_path):
        """Test getting context for non-existent party returns empty string"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        context = manager.get_party_context_for_llm("nonexistent")
        assert context == ""


# ============================================================================
# Import/Export Tests
# ============================================================================


class TestPartyImportExport:
    """Test party import and export functionality"""

    def test_export_party_basic(self, tmp_path):
        """Test exporting a party to JSON file"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Export Test",
            dm_name="DM",
            characters=[Character("Hero", "Player1", "Human", "Fighter")]
        )
        manager.add_party("export_test", party)

        export_path = tmp_path / "exported.json"
        manager.export_party("export_test", export_path)

        # File should exist
        assert export_path.exists()

        # Should contain correct data
        with open(export_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert "export_test" in data
        assert data["export_test"]["party_name"] == "Export Test"

    def test_export_nonexistent_party_raises_error(self, tmp_path):
        """Test exporting non-existent party raises ValueError"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        export_path = tmp_path / "exported.json"
        with pytest.raises(ValueError, match="Party 'nonexistent' not found"):
            manager.export_party("nonexistent", export_path)

    def test_import_party_basic(self, tmp_path):
        """Test importing a party from JSON file"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        # Create import file
        import_path = tmp_path / "import.json"
        import_data = {
            "imported_party": {
                "party_name": "Imported Party",
                "dm_name": "Imported DM",
                "characters": [
                    {
                        "name": "ImportChar",
                        "player": "ImportPlayer",
                        "race": "Elf",
                        "class_name": "Wizard",
                        "description": None,
                        "aliases": None
                    }
                ],
                "campaign": None,
                "notes": None
            }
        }

        with open(import_path, 'w', encoding='utf-8') as f:
            json.dump(import_data, f)

        # Import party
        party_id = manager.import_party(import_path)

        # Should be loaded
        assert party_id == "imported_party"
        assert "imported_party" in manager.parties
        imported = manager.parties["imported_party"]
        assert imported.party_name == "Imported Party"
        assert len(imported.characters) == 1

    def test_import_party_with_custom_id(self, tmp_path):
        """Test importing party with custom ID"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        # Create import file
        import_path = tmp_path / "import.json"
        import_data = {
            "original_id": {
                "party_name": "Test Party",
                "dm_name": "DM",
                "characters": [
                    {
                        "name": "Char",
                        "player": "Player",
                        "race": "Human",
                        "class_name": "Fighter",
                        "description": None,
                        "aliases": None
                    }
                ],
                "campaign": None,
                "notes": None
            }
        }

        with open(import_path, 'w', encoding='utf-8') as f:
            json.dump(import_data, f)

        # Import with custom ID
        party_id = manager.import_party(import_path, party_id="custom_id")

        # Should use custom ID
        assert party_id == "custom_id"
        assert "custom_id" in manager.parties
        assert "original_id" not in manager.parties

    def test_import_party_validates_on_add(self, tmp_path):
        """Test importing party triggers validation"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        # Create import file with duplicate character names
        import_path = tmp_path / "import.json"
        import_data = {
            "bad_party": {
                "party_name": "Bad Party",
                "dm_name": "DM",
                "characters": [
                    {
                        "name": "Duplicate",
                        "player": "Player1",
                        "race": "Human",
                        "class_name": "Fighter",
                        "description": None,
                        "aliases": None
                    },
                    {
                        "name": "Duplicate",  # Duplicate name
                        "player": "Player2",
                        "race": "Elf",
                        "class_name": "Wizard",
                        "description": None,
                        "aliases": None
                    }
                ],
                "campaign": None,
                "notes": None
            }
        }

        with open(import_path, 'w', encoding='utf-8') as f:
            json.dump(import_data, f)

        # Should raise validation error
        with pytest.raises(ValueError, match="Duplicate character names"):
            manager.import_party(import_path)

    def test_export_all_parties(self, tmp_path):
        """Test exporting all parties to single file"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party1 = Party("Party1", "DM1", [Character("C1", "P1", "Human", "Fighter")])
        party2 = Party("Party2", "DM2", [Character("C2", "P2", "Elf", "Wizard")])

        manager.add_party("party1", party1)
        manager.add_party("party2", party2)

        export_path = tmp_path / "all_parties.json"
        manager.export_all_parties(export_path)

        # Should contain all parties
        with open(export_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "default" in data
        assert "party1" in data
        assert "party2" in data

    def test_import_invalid_json_format_raises_error(self, tmp_path):
        """Test importing invalid JSON format raises ValueError"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        import_path = tmp_path / "invalid.json"
        with open(import_path, 'w') as f:
            f.write("[]")  # Array instead of object

        with pytest.raises(ValueError, match="Invalid party file format"):
            manager.import_party(import_path)


# ============================================================================
# Error Recovery Tests
# ============================================================================


class TestPartyConfigErrorRecovery:
    """Test error recovery in party configuration"""

    def test_load_with_missing_file_creates_default(self, tmp_path):
        """Test loading when file doesn't exist creates default party"""
        config_file = tmp_path / "nonexistent.json"
        manager = PartyConfigManager(config_file=config_file)

        # Should create default party and file
        assert "default" in manager.parties
        assert config_file.exists()

    def test_load_with_corrupted_json_recovers(self, tmp_path):
        """Test loading corrupted JSON recovers gracefully"""
        config_file = tmp_path / "corrupted.json"

        # Write invalid JSON
        with open(config_file, 'w') as f:
            f.write("{invalid: json, content")

        # Should not crash
        manager = PartyConfigManager(config_file=config_file)
        assert "default" in manager.parties

    def test_load_with_malformed_party_data_recovers(self, tmp_path):
        """Test loading with malformed party data recovers"""
        config_file = tmp_path / "malformed.json"

        # Create party data missing required fields
        malformed_data = {
            "bad_party": {
                "party_name": "Bad Party"
                # Missing dm_name and characters
            }
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(malformed_data, f)

        # Should recover and create default party
        manager = PartyConfigManager(config_file=config_file)
        assert "default" in manager.parties

    def test_save_creates_parent_directories(self, tmp_path):
        """Test saving creates parent directories if needed"""
        config_file = tmp_path / "deep" / "nested" / "path" / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party("Test", "DM", [Character("C", "P", "Human", "Fighter")])
        manager.add_party("test", party)

        # Parent directories should be created
        assert config_file.parent.exists()
        assert config_file.exists()

    def test_save_with_unicode_characters(self, tmp_path):
        """Test saving party with unicode characters in names"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        party = Party(
            party_name="Les Héros",
            dm_name="Jean-François",
            characters=[
                Character("Éliane", "María", "Elf", "Ranger"),
                Character("北斗", "李明", "Human", "Monk")
            ]
        )
        manager.add_party("unicode_test", party)

        # Should save and reload correctly
        manager2 = PartyConfigManager(config_file=config_file)
        loaded_party = manager2.get_party("unicode_test")
        assert loaded_party.party_name == "Les Héros"
        assert loaded_party.characters[0].name == "Éliane"
        assert loaded_party.characters[1].name == "北斗"


# ============================================================================
# CampaignSettings Tests
# ============================================================================


class TestCampaignSettings:
    """Test CampaignSettings dataclass"""

    def test_campaign_settings_defaults(self):
        """Test CampaignSettings default values"""
        settings = CampaignSettings()
        assert settings.num_speakers == 4
        assert settings.skip_diarization is False
        assert settings.skip_classification is False
        assert settings.skip_snippets is True
        assert settings.skip_knowledge is False
        assert settings.session_id_prefix == "Session_"
        assert settings.auto_number_sessions is False

    def test_campaign_settings_custom_values(self):
        """Test CampaignSettings with custom values"""
        settings = CampaignSettings(
            num_speakers=6,
            skip_diarization=True,
            skip_classification=True,
            session_id_prefix="Episode_"
        )
        assert settings.num_speakers == 6
        assert settings.skip_diarization is True
        assert settings.skip_classification is True
        assert settings.session_id_prefix == "Episode_"

    def test_campaign_settings_serialization(self):
        """Test CampaignSettings serialization to dict"""
        settings = CampaignSettings(num_speakers=5)
        settings_dict = asdict(settings)
        assert settings_dict['num_speakers'] == 5
        assert 'skip_diarization' in settings_dict


# ============================================================================
# Campaign Dataclass Tests
# ============================================================================


class TestCampaignDataclass:
    """Test Campaign dataclass"""

    def test_campaign_basic_creation(self):
        """Test creating basic campaign"""
        settings = CampaignSettings()
        campaign = Campaign(
            name="Lost Mine",
            party_id="party1",
            settings=settings
        )
        assert campaign.name == "Lost Mine"
        assert campaign.party_id == "party1"
        assert campaign.settings.num_speakers == 4
        assert campaign.description is None
        assert campaign.notes is None

    def test_campaign_with_optional_fields(self):
        """Test creating campaign with all fields"""
        settings = CampaignSettings(num_speakers=5)
        campaign = Campaign(
            name="Storm King's Thunder",
            party_id="party2",
            settings=settings,
            description="Giants are causing chaos",
            notes="Starting at level 5"
        )
        assert campaign.description == "Giants are causing chaos"
        assert campaign.notes == "Starting at level 5"


# ============================================================================
# CampaignManager Tests
# ============================================================================


class TestCampaignManager:
    """Test CampaignManager functionality"""

    def test_init_creates_storage_directory(self, tmp_path):
        """Test initialization creates storage directory"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        assert config_file.parent.exists()

    def test_init_loads_existing_campaigns(self, tmp_path):
        """Test initialization loads existing campaigns"""
        config_file = tmp_path / "campaigns.json"

        # Create existing campaign file
        existing_data = {
            "campaign_001": {
                "name": "Existing Campaign",
                "party_id": "party1",
                "settings": {
                    "num_speakers": 4,
                    "skip_diarization": False,
                    "skip_classification": False,
                    "skip_snippets": True,
                    "skip_knowledge": False,
                    "session_id_prefix": "Session_",
                    "auto_number_sessions": False
                },
                "description": "Test campaign",
                "notes": None
            }
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f)

        manager = CampaignManager(config_file=config_file)

        assert "campaign_001" in manager.campaigns
        campaign = manager.campaigns["campaign_001"]
        assert campaign.name == "Existing Campaign"
        assert campaign.party_id == "party1"

    def test_get_campaign_existing(self, tmp_path):
        """Test getting existing campaign"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        settings = CampaignSettings()
        campaign = Campaign("Test", "party1", settings)
        manager.add_campaign("test_campaign", campaign)

        result = manager.get_campaign("test_campaign")
        assert result is not None
        assert result.name == "Test"

    def test_get_campaign_nonexistent(self, tmp_path):
        """Test getting non-existent campaign returns None"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        result = manager.get_campaign("nonexistent")
        assert result is None

    def test_list_campaigns(self, tmp_path):
        """Test listing all campaign IDs"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        settings = CampaignSettings()
        manager.add_campaign("campaign1", Campaign("C1", "p1", settings))
        manager.add_campaign("campaign2", Campaign("C2", "p2", settings))

        campaign_list = manager.list_campaigns()
        assert "campaign1" in campaign_list
        assert "campaign2" in campaign_list

    def test_get_campaign_names(self, tmp_path):
        """Test getting campaign ID to name mapping"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        settings = CampaignSettings()
        manager.add_campaign("c1", Campaign("First Campaign", "p1", settings))
        manager.add_campaign("c2", Campaign("Second Campaign", "p2", settings))

        names = manager.get_campaign_names()
        assert names["c1"] == "First Campaign"
        assert names["c2"] == "Second Campaign"

    def test_add_campaign_saves_to_file(self, tmp_path):
        """Test adding campaign persists to file"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        settings = CampaignSettings(num_speakers=5)
        campaign = Campaign("Test Campaign", "party1", settings)
        manager.add_campaign("test", campaign)

        # Should be saved to file
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "test" in data
        assert data["test"]["name"] == "Test Campaign"
        assert data["test"]["settings"]["num_speakers"] == 5

    def test_create_blank_campaign_basic(self, tmp_path):
        """Test creating blank campaign with defaults"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        campaign_id, campaign = manager.create_blank_campaign()

        assert campaign_id.startswith("campaign_")
        assert campaign.name == "New Campaign"
        assert campaign.party_id == ""
        assert campaign.settings.num_speakers == 4
        assert campaign.description is None

        # Should be saved
        assert campaign_id in manager.campaigns

    def test_create_blank_campaign_with_name(self, tmp_path):
        """Test creating blank campaign with custom name"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        campaign_id, campaign = manager.create_blank_campaign(name="Custom Campaign")

        assert campaign.name == "Custom Campaign"

    def test_create_blank_campaign_unique_ids(self, tmp_path):
        """Test creating multiple blank campaigns generates unique IDs"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        id1, _ = manager.create_blank_campaign()
        id2, _ = manager.create_blank_campaign()
        id3, _ = manager.create_blank_campaign()

        assert id1 != id2 != id3
        assert all(cid.startswith("campaign_") for cid in [id1, id2, id3])

    def test_create_blank_campaign_unique_names(self, tmp_path):
        """Test creating multiple blank campaigns with same name generates unique names"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        id1, c1 = manager.create_blank_campaign()  # "New Campaign"
        id2, c2 = manager.create_blank_campaign()  # "New Campaign 2"
        id3, c3 = manager.create_blank_campaign()  # "New Campaign 3"

        assert c1.name == "New Campaign"
        assert c2.name == "New Campaign 2"
        assert c3.name == "New Campaign 3"

    def test_generate_campaign_id(self, tmp_path):
        """Test campaign ID generation"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        # First ID should be campaign_001
        id1 = manager._generate_campaign_id()
        assert id1 == "campaign_001"

        # Add it
        settings = CampaignSettings()
        manager.add_campaign(id1, Campaign("C1", "p1", settings))

        # Next should be campaign_002
        id2 = manager._generate_campaign_id()
        assert id2 == "campaign_002"

    def test_load_campaigns_handles_errors(self, tmp_path):
        """Test loading campaigns handles errors gracefully"""
        config_file = tmp_path / "campaigns.json"

        # Write invalid JSON
        with open(config_file, 'w') as f:
            f.write("{invalid json")

        # Should not crash
        manager = CampaignManager(config_file=config_file)
        assert manager.campaigns == {}

    def test_campaign_with_empty_party_id(self, tmp_path):
        """Test creating campaign with empty party_id is allowed"""
        config_file = tmp_path / "campaigns.json"
        manager = CampaignManager(config_file=config_file)

        settings = CampaignSettings()
        campaign = Campaign("Test", "", settings)  # Empty party_id
        manager.add_campaign("test", campaign)

        loaded = manager.get_campaign("test")
        assert loaded.party_id == ""


# ============================================================================
# Default Party Content Tests
# ============================================================================


class TestDefaultPartyContent:
    """Test default party structure and content"""

    def test_default_party_has_correct_name(self, tmp_path):
        """Test default party has correct name"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        default = manager.get_party("default")
        assert default.party_name == "The Broken Seekers"

    def test_default_party_has_all_characters(self, tmp_path):
        """Test default party has all expected characters"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        default = manager.get_party("default")
        assert len(default.characters) == 4

        char_names = [c.name for c in default.characters]
        assert "Sha'ek Mindfa'ek" in char_names
        assert "Pipira Shimmerlock" in char_names
        assert "Fan'nar Khe'Lek" in char_names
        assert "Furnax" in char_names

    def test_default_party_characters_have_aliases(self, tmp_path):
        """Test default party characters have aliases defined"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        default = manager.get_party("default")

        # Check specific character aliases
        shaek = next(c for c in default.characters if c.name == "Sha'ek Mindfa'ek")
        assert shaek.aliases is not None
        assert "Sha'ek" in shaek.aliases
        assert "The Broken" in shaek.aliases

    def test_default_party_has_campaign_info(self, tmp_path):
        """Test default party has campaign information"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        default = manager.get_party("default")
        assert default.campaign == "Gaia Adventures"
        assert default.notes is not None

    def test_default_party_furnax_is_companion(self, tmp_path):
        """Test Furnax is marked as Companion"""
        config_file = tmp_path / "parties.json"
        manager = PartyConfigManager(config_file=config_file)

        default = manager.get_party("default")
        furnax = next(c for c in default.characters if c.name == "Furnax")
        assert furnax.player == "Companion"
