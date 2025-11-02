from pathlib import Path
import json

from src.party_config import CampaignManager, CampaignSettings


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
