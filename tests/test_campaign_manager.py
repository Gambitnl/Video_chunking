from pathlib import Path
import json

from src.party_config import CampaignManager, CampaignSettings, Campaign


def test_create_blank_campaign_generates_unique_profile(tmp_path):
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)

    campaign_id, campaign = manager.create_blank_campaign()

    assert campaign_id in manager.campaigns
    assert campaign.name.startswith("New Campaign")
    assert campaign.party_id == ""
    assert campaign.settings == CampaignSettings()

    # Persisted to disk
    stored = json.loads(config_path.read_text(encoding="utf-8"))
    assert campaign_id in stored
    assert stored[campaign_id]["name"] == campaign.name

    # Second call yields a different id and name
    second_id, second_campaign = manager.create_blank_campaign()
    assert second_id != campaign_id
    assert second_campaign.name != campaign.name


def test_rename_campaign_success(tmp_path):
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)
    cid, _ = manager.create_blank_campaign(name="Original Name")

    success = manager.rename_campaign(cid, "New Name")

    assert success is True
    assert manager.get_campaign(cid).name == "New Name"

    # Persisted
    stored = json.loads(config_path.read_text(encoding="utf-8"))
    assert stored[cid]["name"] == "New Name"


def test_rename_campaign_fail_empty(tmp_path):
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)
    cid, _ = manager.create_blank_campaign(name="Original")

    success = manager.rename_campaign(cid, "")
    assert success is False
    assert manager.get_campaign(cid).name == "Original"


def test_rename_campaign_fail_duplicate(tmp_path):
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)
    cid1, _ = manager.create_blank_campaign(name="Campaign 1")
    cid2, _ = manager.create_blank_campaign(name="Campaign 2")

    # Try to rename 1 to 2
    success = manager.rename_campaign(cid1, "Campaign 2")
    assert success is False
    assert manager.get_campaign(cid1).name == "Campaign 1"

    # Case insensitive check
    success = manager.rename_campaign(cid1, "campaign 2")
    assert success is False


def test_rename_campaign_fail_not_found(tmp_path):
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)

    success = manager.rename_campaign("non_existent", "New Name")
    assert success is False


def test_delete_campaign_success(tmp_path):
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)
    cid, _ = manager.create_blank_campaign()

    assert cid in manager.campaigns

    success = manager.delete_campaign(cid)
    assert success is True
    assert cid not in manager.campaigns

    # Persisted
    stored = json.loads(config_path.read_text(encoding="utf-8"))
    assert cid not in stored


def test_delete_campaign_fail_not_found(tmp_path):
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)

    success = manager.delete_campaign("non_existent")
    assert success is False


def test_campaign_switching(tmp_path):
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)

    cid1, c1 = manager.create_blank_campaign(name="Campaign One")
    cid2, c2 = manager.create_blank_campaign(name="Campaign Two")

    # Simulate switching
    current_campaign_id = cid1
    campaign = manager.get_campaign(current_campaign_id)
    assert campaign.name == "Campaign One"

    current_campaign_id = cid2
    campaign = manager.get_campaign(current_campaign_id)
    assert campaign.name == "Campaign Two"

    # Reload manager to ensure persistence
    manager2 = CampaignManager(config_file=config_path)
    assert manager2.get_campaign(cid1).name == "Campaign One"
    assert manager2.get_campaign(cid2).name == "Campaign Two"


def test_load_campaigns_empty_file(tmp_path):
    config_path = tmp_path / "campaigns.json"
    config_path.touch()  # Create empty file

    manager = CampaignManager(config_file=config_path)
    assert manager.campaigns == {}


def test_load_campaigns_corrupt_json(tmp_path):
    config_path = tmp_path / "campaigns.json"
    config_path.write_text("{invalid_json", encoding="utf-8")

    manager = CampaignManager(config_file=config_path)
    assert manager.campaigns == {}


def test_load_campaigns_partial_corruption(tmp_path):
    """Test that valid campaigns are loaded even if some are corrupt/incomplete."""
    config_path = tmp_path / "campaigns.json"
    data = {
        "valid_camp": {
            "name": "Valid Campaign",
            "party_id": "p1",
            "settings": {}
        },
        "invalid_camp": {
            "name": "Invalid Campaign"
            # Missing party_id and settings
        }
    }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)

    manager = CampaignManager(config_file=config_path)

    # Should load valid_camp
    assert "valid_camp" in manager.campaigns
    assert manager.get_campaign("valid_camp").name == "Valid Campaign"

    # Should skip invalid_camp
    assert "invalid_camp" not in manager.campaigns


def test_campaign_settings_defaults():
    """Verify default settings are suitable for UI."""
    settings = CampaignSettings()
    assert settings.num_speakers == 4
    assert settings.skip_diarization is False
    assert settings.skip_classification is False
    assert settings.skip_snippets is True
    assert settings.skip_knowledge is False
    assert settings.session_id_prefix == "Session_"
    assert settings.auto_number_sessions is False


def test_campaign_persistence_integrity(tmp_path):
    """Verify full round-trip persistence of campaign data."""
    config_path = tmp_path / "campaigns.json"
    manager = CampaignManager(config_file=config_path)

    settings = CampaignSettings(
        num_speakers=2,
        skip_diarization=True,
        skip_classification=True,
        skip_snippets=False,
        skip_knowledge=True,
        session_id_prefix="Ep_",
        auto_number_sessions=True
    )
    campaign = Campaign(
        name="Test Campaign",
        party_id="party_1",
        settings=settings,
        description="Desc",
        notes="Notes"
    )

    manager.add_campaign("c1", campaign)

    # Reload
    manager2 = CampaignManager(config_file=config_path)
    loaded = manager2.get_campaign("c1")

    assert loaded.name == "Test Campaign"
    assert loaded.party_id == "party_1"
    assert loaded.settings.num_speakers == 2
    assert loaded.settings.skip_diarization is True
    assert loaded.settings.skip_classification is True
    assert loaded.settings.skip_snippets is False
    assert loaded.settings.skip_knowledge is True
    assert loaded.settings.session_id_prefix == "Ep_"
    assert loaded.settings.auto_number_sessions is True
    assert loaded.description == "Desc"
    assert loaded.notes == "Notes"
