import json

from src.profile_extractor import ProfileExtractor


class StubLLM:
    def __init__(self, content: dict | None):
        self._content = content
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self._content is None:
            return {"message": {"content": "invalid json"}}
        return {"message": {"content": json.dumps(self._content)}}


def test_extract_profile_updates_empty_when_llm_unavailable():
    extractor = ProfileExtractor(config=None, llm_client=None)
    batch = extractor.extract_profile_updates(
        session_id="session-1",
        transcript_segments=[],
        character_names=["Aria"],
    )
    assert batch.updates == []


def test_extract_profile_updates_with_stub_llm():
    llm = StubLLM(
        {
            "updates": [
                {
                    "character": "Aria",
                    "category": "notable_actions",
                    "content": "Aria unleashes a radiant smite",
                    "timestamp": "00:12:34",
                    "confidence": 0.9,
                    "context": "The paladin finishes the duel",
                    "type": "combat",
                }
            ]
        }
    )
    extractor = ProfileExtractor(config=None, llm_client=llm)

    segments = [
        {"text": "I unleash radiant justice!", "speaker": "Aria", "start": 12.0, "end": 14.0},
    ]

    batch = extractor.extract_profile_updates(
        session_id="session-1",
        transcript_segments=segments,
        character_names=["Aria"],
        campaign_context="Test Campaign",
    )

    assert len(batch.updates) == 1
    update = batch.updates[0]
    assert update.character == "Aria"
    assert update.category == "notable_actions"
    assert update.session_id == "session-1"
    assert update.content.startswith("Aria unleashes")
    assert llm.calls, "Expected LLM to be invoked"


def test_extract_profile_updates_handles_invalid_json():
    llm = StubLLM(None)
    extractor = ProfileExtractor(config=None, llm_client=llm)

    segments = [
        {"text": "For the Seekers!", "speaker": "Thorin", "start": 0.0, "end": 2.0},
    ]

    batch = extractor.extract_profile_updates(
        session_id="session-2",
        transcript_segments=segments,
        character_names=["Thorin"],
    )

    assert batch.updates == []
