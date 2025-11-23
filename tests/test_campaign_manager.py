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
