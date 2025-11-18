import pytest

from src.classifier import (
    Classification,
    ClassificationResult,
    ClassificationType,
    OllamaClassifier,
    SpeakerInfo,
)
from src.classifier import OllamaClientFactory


class _DummyClient:
    def list(self):
        return []

    def generate(self, *args, **kwargs):
        raise RuntimeError("Should not be called in prompt formatting tests")


@pytest.fixture(autouse=True)
def _mock_ollama_client(monkeypatch):
    monkeypatch.setattr(
        OllamaClientFactory,
        "create_client",
        lambda self, **kwargs: _DummyClient(),
    )


def _build_classifier():
    return OllamaClassifier(model="dummy", base_url="http://dummy")


def test_build_prompt_includes_metadata_and_speakers():
    classifier = _build_classifier()

    speaker_map = {
        "SPEAKER_00": {"name": "Alice", "character": "Sha'ek Mindfa'ek", "role": "PLAYER"},
        "SPEAKER_01": {"name": "Jules", "role": "DM_NARRATOR"},
    }
    segments = [
        {"text": "Intro", "start_time": 0.0, "end_time": 2.0, "speaker": "SPEAKER_01"},
        {"text": "I cast fireball", "start_time": 5.0, "end_time": 8.0, "speaker": "SPEAKER_00"},
        {"text": "The room erupts", "start_time": 9.0, "end_time": 11.0, "speaker": "SPEAKER_01"},
    ]
    speaker_overview = classifier._format_speaker_overview(speaker_map)
    context = classifier._gather_context_segments(segments, 1)
    metadata = classifier._build_temporal_metadata(1, segments[1], segments, [], 12.0)
    speaker_info = classifier._resolve_speaker_info("SPEAKER_00", speaker_map)

    prompt = classifier._build_prompt_with_context(
        character_names=["Sha'ek Mindfa'ek"],
        player_names=["Alice"],
        speaker_overview=speaker_overview,
        metadata=metadata,
        context_segments=context,
        speaker_info=speaker_info,
        speaker_map=speaker_map,
    )

    assert "Sha'ek Mindfa'ek" in prompt
    assert "Sprekerkaart" in prompt
    assert "Turn-rate" in prompt
    assert "SPEAKER_00" in prompt  # Labels still referenced


@pytest.mark.parametrize(
    "classification,role,expected",
    [
        (Classification.IN_CHARACTER, "PLAYER", ClassificationType.CHARACTER),
        (Classification.IN_CHARACTER, "DM_NARRATOR", ClassificationType.DM_NARRATION),
        (Classification.IN_CHARACTER, "DM_NPC", ClassificationType.NPC_DIALOGUE),
        (Classification.OUT_OF_CHARACTER, "PLAYER", ClassificationType.OOC_OTHER),
    ],
)
def test_infer_classification_type_fallback(classification, role, expected):
    classifier = _build_classifier()
    result = ClassificationResult(
        segment_index=0,
        classification=classification,
        confidence=0.9,
        reasoning="",
    )
    speaker_info = SpeakerInfo(label="SPEAKER_00", role=role)

    classifier._infer_classification_type(result, speaker_info)

    assert result.classification_type == expected
