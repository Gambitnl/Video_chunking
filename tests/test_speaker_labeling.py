
import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from src.diarizer import SpeakerProfileManager

@pytest.fixture
def speaker_profile_manager(tmp_path):
    profile_file = tmp_path / "speaker_profiles.json"
    return SpeakerProfileManager(profile_file=profile_file)

def test_save_speaker_embeddings(speaker_profile_manager):
    session_id = "test_session"
    speaker_embeddings = {"SPEAKER_00": np.array([1.0, 2.0, 3.0])}
    speaker_profile_manager.save_speaker_embeddings(session_id, speaker_embeddings)

    profiles = speaker_profile_manager._load_profiles()
    assert session_id in profiles
    assert "SPEAKER_00" in profiles[session_id]
    assert "embedding" in profiles[session_id]["SPEAKER_00"]
    assert profiles[session_id]["SPEAKER_00"]["embedding"] == [1.0, 2.0, 3.0]

def test_map_speaker(speaker_profile_manager):
    session_id = "test_session"
    speaker_id = "SPEAKER_00"
    person_name = "Test Person"
    speaker_profile_manager.map_speaker(session_id, speaker_id, person_name)

    profiles = speaker_profile_manager._load_profiles()
    assert session_id in profiles
    assert speaker_id in profiles[session_id]
    assert "name" in profiles[session_id][speaker_id]
    assert profiles[session_id][speaker_id]["name"] == person_name

def test_get_person_name(speaker_profile_manager):
    session_id = "test_session"
    speaker_id = "SPEAKER_00"
    person_name = "Test Person"
    speaker_profile_manager.map_speaker(session_id, speaker_id, person_name)

    retrieved_name = speaker_profile_manager.get_person_name(session_id, speaker_id)
    assert retrieved_name == person_name
