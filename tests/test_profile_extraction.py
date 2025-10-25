import pytest

from src.character_profile import (
    PROFILE_UPDATE_CATEGORIES,
    ProfileUpdate,
    ProfileUpdateBatch,
)
from src.profile_extractor import ProfileExtractor


def make_update_payload(**overrides):
    payload = {
        "character": "Aria",
        "category": "notable_actions",
        "content": "Aria unleashes a radiant smite",
        "type": "combat",
        "timestamp": "00:12:34",
        "confidence": 0.9,
        "context": "The paladin finishes the duel",
        "tags": ["combat", "smite"],
        "metadata": {"damage": 32},
    }
    payload.update(overrides)
    return payload


def test_profile_update_from_dict_valid():
    payload = make_update_payload()
    update = ProfileUpdate.from_dict(payload)
    assert update.character == payload["character"]
    assert update.category == payload["category"]
    assert update.to_dict()["tags"] == payload["tags"]


def test_profile_update_from_dict_missing_fields():
    with pytest.raises(ValueError):
        ProfileUpdate.from_dict({"character": "Aria"})


@pytest.mark.parametrize("category", PROFILE_UPDATE_CATEGORIES)
def test_profile_update_all_categories(category):
    payload = make_update_payload(category=category)
    update = ProfileUpdate.from_dict(payload)
    assert update.category == category


def test_profile_update_batch_roundtrip():
    batch_payload = {
        "session_id": "session_001",
        "campaign_id": "camp_alpha",
        "generated_at": "2025-10-25T12:00:00Z",
        "source": {"unit": "test"},
        "updates": [make_update_payload()],
    }
    batch = ProfileUpdateBatch.from_dict(batch_payload)
    assert batch.session_id == "session_001"
    assert len(batch.updates) == 1
    assert batch.to_dict()["campaign_id"] == "camp_alpha"


def test_profile_extractor_returns_empty_batch_when_no_segments():
    extractor = ProfileExtractor(config=None, llm_client=None)
    batch = extractor.extract_profile_updates(
        session_id="session_002",
        transcript_segments=[],
        campaign_id="camp_alpha",
    )
    assert batch.session_id == "session_002"
    assert batch.campaign_id == "camp_alpha"
    assert batch.updates == []


def test_profile_extractor_normalizes_segments():
    extractor = ProfileExtractor(config=None, llm_client=None)
    raw_segments = [
        {"text": "Hello", "speaker": "A", "start": 0.0, "end": 1.0, "confidence": 0.8},
        {"text": "", "speaker": "B"},
        "not a dict",
    ]
    normalized = list(extractor._normalize_segments(raw_segments))
    assert len(normalized) == 1
    assert normalized[0]["text"] == "Hello"
    assert normalized[0]["speaker"] == "A"
