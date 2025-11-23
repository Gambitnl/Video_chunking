"""Tests for campaign migration utilities."""
import pytest
import json
from pathlib import Path
from datetime import datetime

from src.campaign_migration import CampaignMigration, MigrationReport
from src.party_config import CampaignManager, Campaign, CampaignSettings


@pytest.fixture
def temp_campaign(tmp_path):
    """Create a temporary campaign for testing."""
    campaigns_file = tmp_path / "campaigns.json"
    campaigns_file.parent.mkdir(exist_ok=True, parents=True)

    campaign_data = {
        "test_campaign": {
            "name": "Test Campaign",
            "party_id": "test_party",
            "settings": {
                "num_speakers": 4,
                "skip_diarization": False,
                "skip_classification": False,
                "skip_snippets": True,
                "skip_knowledge": False,
                "session_id_prefix": "Session_",
                "auto_number_sessions": False
            },
            "description": "Test campaign for migration",
            "notes": None
        }
    }

    campaigns_file.write_text(json.dumps(campaign_data, indent=2), encoding='utf-8')

    return campaigns_file.parent


@pytest.fixture
def temp_session_with_metadata(tmp_path):
    """Create a temporary session with metadata file."""
    session_dir = tmp_path / "20251101_120000_test_session"
    session_dir.mkdir(parents=True)

    metadata = {
        "metadata": {
            "session_id": "test_session",
            "input_file": "/path/to/audio.m4a",
            "character_names": ["Alice", "Bob"],
            "player_names": ["Player1", "Player2"],
            "statistics": {
                "total_duration_seconds": 300.0
            }
        },
        "segments": []
    }

    data_file = session_dir / "test_session_data.json"
    data_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    return session_dir


@pytest.fixture
def migration_with_temp_config(tmp_path, monkeypatch):
    """Create migration instance with temporary config."""
    from src import config

    # Mock the Config paths
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', tmp_path / "output")
    monkeypatch.setattr(config.Config, 'MODELS_DIR', tmp_path / "models")

    # Ensure directories exist
    (tmp_path / "output").mkdir(exist_ok=True)
    (tmp_path / "models").mkdir(exist_ok=True)

    return CampaignMigration()


def test_migrate_session_metadata_dry_run(tmp_path, temp_campaign, monkeypatch):
    """Test session metadata migration in dry-run mode."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create session with metadata
    session_dir = output_dir / "20251101_120000_test_session"
    session_dir.mkdir()

    metadata = {
        "metadata": {
            "session_id": "test_session",
            "character_names": [],
            "player_names": []
        },
        "segments": []
    }

    data_file = session_dir / "test_session_data.json"
    data_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_session_metadata(
        campaign_id="test_campaign",
        dry_run=True
    )

    # Verify report
    assert report.sessions_migrated == 1
    assert report.sessions_skipped == 0
    assert len(report.errors) == 0

    # Verify file not modified (dry-run)
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert "campaign_id" not in data["metadata"]


def test_migrate_session_metadata_actual(tmp_path, temp_campaign, monkeypatch):
    """Test actual session metadata migration."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create session with metadata
    session_dir = output_dir / "20251101_120000_test_session"
    session_dir.mkdir()

    metadata = {
        "metadata": {
            "session_id": "test_session",
            "character_names": [],
            "player_names": []
        },
        "segments": []
    }

    data_file = session_dir / "test_session_data.json"
    data_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_session_metadata(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Verify report
    assert report.sessions_migrated == 1
    assert report.sessions_skipped == 0

    # Verify file was modified
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert data["metadata"]["campaign_id"] == "test_campaign"
    assert data["metadata"]["campaign_name"] == "Test Campaign"
    assert data["metadata"]["party_id"] == "test_party"


def test_migrate_session_metadata_skip_existing(tmp_path, temp_campaign, monkeypatch):
    """Test migration skips sessions that already have campaign_id."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create session with metadata that already has campaign_id
    session_dir = output_dir / "20251101_120000_test_session"
    session_dir.mkdir()

    metadata = {
        "metadata": {
            "session_id": "test_session",
            "campaign_id": "existing_campaign",
            "character_names": [],
            "player_names": []
        },
        "segments": []
    }

    data_file = session_dir / "test_session_data.json"
    data_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_session_metadata(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Verify skipped
    assert report.sessions_migrated == 0
    assert report.sessions_skipped == 1

    # Verify file not modified
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert data["metadata"]["campaign_id"] == "existing_campaign"  # Unchanged


def test_migrate_session_metadata_with_filter(tmp_path, temp_campaign, monkeypatch):
    """Test session migration with glob filter."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create multiple sessions
    for i, name in enumerate(["Session_01", "test_session", "Session_02"]):
        session_dir = output_dir / f"2025110{i}_120000_{name}"
        session_dir.mkdir()

        metadata = {
            "metadata": {"session_id": name},
            "segments": []
        }

        data_file = session_dir / f"{name}_data.json"
        data_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')

    # Run migration with filter
    migration = CampaignMigration()
    report = migration.migrate_session_metadata(
        campaign_id="test_campaign",
        dry_run=False,
        session_filter="*Session_*"
    )

    # Should only migrate sessions matching "Session_*" pattern
    assert report.sessions_migrated == 2  # Session_01 and Session_02
    assert report.sessions_skipped == 0


def test_migrate_character_profiles(tmp_path, temp_campaign, monkeypatch):
    """Test character profile migration."""
    from src import config
    from src.character_profile import CharacterProfileManager, CharacterProfile

    # Setup
    profiles_dir = temp_campaign / "character_profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create a profile without campaign_id
    profile_data = {
        "name": "Test Character",
        "player": "Test Player",
        "race": "Human",
        "class_name": "Fighter",
        "level": 1,
        "campaign_name": "Old Campaign Name",
        "campaign_id": None,  # No campaign assigned yet
        "aliases": [],
        "notable_actions": [],
        "inventory": [],
        "relationships": [],
        "development_notes": [],
        "memorable_quotes": [],
        "sessions_appeared": [],
        "current_goals": [],
        "completed_goals": []
    }

    profile_file = profiles_dir / "Test_Character.json"
    profile_file.write_text(json.dumps(profile_data, indent=2), encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_character_profiles(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Verify
    assert report.profiles_migrated == 1
    assert report.profiles_skipped == 0

    # Load and verify profile was updated
    updated_data = json.loads(profile_file.read_text(encoding='utf-8'))
    assert updated_data["campaign_id"] == "test_campaign"


def test_migrate_character_profiles_skip_assigned(tmp_path, temp_campaign, monkeypatch):
    """Test migration skips profiles already assigned to a campaign."""
    from src import config

    # Setup
    profiles_dir = temp_campaign / "character_profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create profile already assigned to different campaign
    profile_data = {
        "name": "Test Character",
        "player": "Test Player",
        "race": "Human",
        "class_name": "Fighter",
        "level": 1,
        "campaign_id": "other_campaign",  # Already assigned
        "aliases": [],
        "notable_actions": [],
        "inventory": [],
        "relationships": [],
        "development_notes": [],
        "memorable_quotes": [],
        "sessions_appeared": [],
        "current_goals": [],
        "completed_goals": []
    }

    profile_file = profiles_dir / "Test_Character.json"
    profile_file.write_text(json.dumps(profile_data, indent=2), encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_character_profiles(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Should skip
    assert report.profiles_migrated == 0
    assert report.profiles_skipped == 1


def test_migrate_narrative_frontmatter(tmp_path, temp_campaign, monkeypatch):
    """Test adding YAML frontmatter to narratives."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create narrative file without frontmatter
    session_dir = output_dir / "20251101_120000_Session_01"
    narratives_dir = session_dir / "narratives"
    narratives_dir.mkdir(parents=True)

    narrative_file = narratives_dir / "session_01_narrative.md"
    narrative_content = "# Session 1\n\nThis is the story of session 1."
    narrative_file.write_text(narrative_content, encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_narrative_frontmatter(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Verify
    assert report.narratives_migrated == 1
    assert report.narratives_skipped == 0

    # Check frontmatter was added
    updated_content = narrative_file.read_text(encoding='utf-8')
    assert updated_content.startswith("---\n")
    assert "campaign_id: test_campaign" in updated_content
    assert "campaign_name: Test Campaign" in updated_content
    assert narrative_content in updated_content


def test_migrate_narrative_skip_with_frontmatter(tmp_path, temp_campaign, monkeypatch):
    """Test migration skips narratives that already have frontmatter."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create narrative with existing frontmatter
    session_dir = output_dir / "20251101_120000_Session_01"
    narratives_dir = session_dir / "narratives"
    narratives_dir.mkdir(parents=True)

    narrative_file = narratives_dir / "session_01_narrative.md"
    narrative_content = "---\nalready_has: frontmatter\n---\n\n# Session 1"
    narrative_file.write_text(narrative_content, encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_narrative_frontmatter(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Should skip
    assert report.narratives_migrated == 0
    assert report.narratives_skipped == 1

    # Content should be unchanged
    assert narrative_file.read_text(encoding='utf-8') == narrative_content


def test_generate_migration_report_markdown():
    """Test markdown report generation."""
    migration = CampaignMigration()

    sessions_report = MigrationReport(
        sessions_migrated=5,
        sessions_skipped=2,
        errors=["Error 1"]
    )

    profiles_report = MigrationReport(
        profiles_migrated=3,
        profiles_skipped=1
    )

    markdown = migration.generate_migration_report_markdown(
        sessions_report=sessions_report,
        profiles_report=profiles_report
    )

    assert "# Campaign Migration Report" in markdown
    assert "## Session Metadata" in markdown
    assert "Migrated**: 5" in markdown
    assert "Skipped**: 2" in markdown
    assert "## Character Profiles" in markdown
    assert "Migrated**: 3" in markdown
    assert "Error 1" in markdown


def test_migrate_with_empty_json(tmp_path, temp_campaign, monkeypatch):
    """Test migration handles empty JSON files gracefully."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create session with empty data file
    session_dir = output_dir / "20251101_120000_Empty"
    session_dir.mkdir()
    data_file = session_dir / "Empty_data.json"
    data_file.write_text("{}", encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_session_metadata(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Should report 0 migrated, 0 skipped, and likely an error or just handled
    # Since metadata is empty, key lookup might fail if not careful
    # The code does `data.get('metadata', {})` so it should be fine.

    assert report.sessions_migrated == 1

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert "metadata" in data
    assert data["metadata"]["campaign_id"] == "test_campaign"


def test_migrate_with_corrupted_json(tmp_path, temp_campaign, monkeypatch):
    """Test migration handles corrupted JSON files."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Create session with corrupted data file
    session_dir = output_dir / "20251101_120000_Corrupt"
    session_dir.mkdir()
    data_file = session_dir / "Corrupt_data.json"
    data_file.write_text("{ this is not valid json }", encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_session_metadata(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Should report error
    assert report.sessions_migrated == 0
    assert len(report.errors) == 1
    assert "Corrupt_data.json" in report.errors[0]


def test_migrate_partial_success(tmp_path, temp_campaign, monkeypatch):
    """Test migration continues after encountering an error."""
    from src import config

    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(config.Config, 'OUTPUT_DIR', output_dir)
    monkeypatch.setattr(config.Config, 'MODELS_DIR', temp_campaign)

    # Session 1: Good
    s1 = output_dir / "20251101_120000_Good"
    s1.mkdir()
    (s1 / "Good_data.json").write_text(json.dumps({"metadata": {"session_id": "good"}}), encoding='utf-8')

    # Session 2: Corrupt
    s2 = output_dir / "20251102_120000_Bad"
    s2.mkdir()
    (s2 / "Bad_data.json").write_text("invalid json", encoding='utf-8')

    # Session 3: Good
    s3 = output_dir / "20251103_120000_Good2"
    s3.mkdir()
    (s3 / "Good2_data.json").write_text(json.dumps({"metadata": {"session_id": "good2"}}), encoding='utf-8')

    # Run migration
    migration = CampaignMigration()
    report = migration.migrate_session_metadata(
        campaign_id="test_campaign",
        dry_run=False
    )

    # Verify results
    assert report.sessions_migrated == 2
    assert len(report.errors) == 1

    # Verify s1 and s3 were updated
    with open(s1 / "Good_data.json", 'r') as f:
        assert json.load(f)["metadata"]["campaign_id"] == "test_campaign"

    with open(s3 / "Good2_data.json", 'r') as f:
        assert json.load(f)["metadata"]["campaign_id"] == "test_campaign"
