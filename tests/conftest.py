"""
Shared pytest fixtures and test helpers.

This file contains common fixtures used across multiple test files.
"""
import pytest
import json
import wave
import numpy as np
from pathlib import Path
from typing import List, Tuple


# ============================================================================
# Audio File Fixtures
# ============================================================================

@pytest.fixture
def sample_audio_path(tmp_path):
    """
    Create a small test audio file (5 seconds, silent).

    Returns:
        Path to test WAV file (16kHz, mono, 16-bit)
    """
    return create_test_audio(tmp_path, duration=5)


@pytest.fixture
def sample_audio_with_speech(tmp_path):
    """
    Create test audio with speech/silence pattern.

    Pattern:
        0-2s: speech
        2-3s: silence
        3-5s: speech

    Returns:
        Path to test WAV file
    """
    speech_segments = [(0, 2), (3, 5)]
    return create_test_audio_with_pattern(tmp_path, speech_segments, duration=5)


# ============================================================================
# Transcription Fixtures
# ============================================================================

@pytest.fixture
def sample_segments():
    """
    Return sample transcription segments for testing.

    Returns:
        List of mock transcription segments with timestamps and text
    """
    return [
        {
            'start_time': 0.0,
            'end_time': 2.5,
            'text': 'Hello world',
            'speaker': 'SPEAKER_00'
        },
        {
            'start_time': 3.0,
            'end_time': 5.0,
            'text': 'This is a test',
            'speaker': 'SPEAKER_01'
        },
        {
            'start_time': 5.5,
            'end_time': 8.0,
            'text': 'Another segment here',
            'speaker': 'SPEAKER_00'
        }
    ]


@pytest.fixture
def sample_segments_with_classification():
    """
    Return sample transcription segments with IC/OOC classification.

    Returns:
        List of segments with classification metadata
    """
    return [
        {
            'start_time': 0.0,
            'end_time': 2.5,
            'text': 'I draw my sword',
            'speaker': 'Player1',
            'classification': {
                'label': 'IC',
                'confidence': 0.9,
                'reasoning': 'Character action',
                'character': 'Aragorn'
            }
        },
        {
            'start_time': 3.0,
            'end_time': 5.0,
            'text': 'Should we order pizza?',
            'speaker': 'Player2',
            'classification': {
                'label': 'OOC',
                'confidence': 0.95,
                'reasoning': 'Real-world discussion',
                'character': None
            }
        }
    ]


# ============================================================================
# Mock LLM Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_response():
    """
    Mock LLM API response function.

    Returns:
        Function that returns mock LLM text based on prompt
    """
    def _mock_llm(prompt: str) -> str:
        """Return mock response based on prompt keywords."""
        if "character" in prompt.lower():
            return json.dumps({
                'name': 'Test Character',
                'race': 'Human',
                'class': 'Fighter'
            })
        elif "classify" in prompt.lower():
            return "Classificatie: IC\nVertrouwen: 0.9\nPersonage: Test"
        else:
            return "Mock LLM response"

    return _mock_llm


@pytest.fixture
def mock_ollama_available(monkeypatch):
    """
    Mock Ollama as available and responsive.

    Use this fixture to simulate Ollama running locally.
    """
    def mock_get(*args, **kwargs):
        """Mock successful Ollama connection."""
        class MockResponse:
            status_code = 200
            def json(self):
                return {"status": "ok"}

        return MockResponse()

    monkeypatch.setattr('requests.get', mock_get)


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def mock_party_config(tmp_path):
    """
    Create a mock party configuration file.

    Returns:
        Path to party config JSON file
    """
    party_data = {
        'party_name': 'Test Party',
        'dm_name': 'Test DM',
        'characters': [
            {'name': 'Aragorn', 'player': 'Alice'},
            {'name': 'Legolas', 'player': 'Bob'}
        ]
    }

    config_dir = tmp_path / "parties"
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / "default.json"
    config_file.write_text(json.dumps(party_data, indent=2))

    return config_file


@pytest.fixture
def mock_knowledge_base(tmp_path):
    """
    Create a mock campaign knowledge base.

    Returns:
        Path to knowledge base JSON file
    """
    kb_data = {
        'campaign_name': 'Test Campaign',
        'quests': [
            {'name': 'Destroy the Ring', 'status': 'active'}
        ],
        'npcs': [
            {'name': 'Gandalf', 'description': 'A wise wizard'}
        ],
        'locations': [
            {'name': 'The Shire', 'description': 'Peaceful homeland of hobbits'}
        ]
    }

    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir(exist_ok=True)

    kb_file = kb_dir / "test_campaign_knowledge.json"
    kb_file.write_text(json.dumps(kb_data, indent=2))

    return kb_file


# ============================================================================
# Helper Functions (Available to all tests)
# ============================================================================

def create_test_audio(
    output_dir: Path,
    duration: int,
    sample_rate: int = 16000,
    filename: str = "test.wav"
) -> Path:
    """
    Create a silent test WAV file.

    Args:
        output_dir: Directory to save the file
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        filename: Output filename

    Returns:
        Path to created WAV file
    """
    # Create silent audio (zeros)
    audio_data = np.zeros(duration * sample_rate, dtype=np.int16)

    wav_path = output_dir / filename
    with wave.open(str(wav_path), 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)   # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    return wav_path


def create_test_audio_with_pattern(
    output_dir: Path,
    speech_segments: List[Tuple[float, float]],
    duration: int,
    sample_rate: int = 16000,
    filename: str = "test_speech.wav"
) -> Path:
    """
    Create test audio with specific speech/silence patterns.

    Args:
        output_dir: Directory to save the file
        speech_segments: List of (start_time, end_time) tuples in seconds
        duration: Total duration in seconds
        sample_rate: Sample rate in Hz
        filename: Output filename

    Returns:
        Path to created WAV file

    Example:
        >>> create_test_audio_with_pattern(
        ...     tmp_path,
        ...     speech_segments=[(0, 2), (5, 7)],
        ...     duration=10
        ... )
        # Creates: speech 0-2s, silence 2-5s, speech 5-7s, silence 7-10s
    """
    # Start with silence
    audio_data = np.zeros(duration * sample_rate, dtype=np.int16)

    # Add "speech" (low-amplitude noise) to specified segments
    for start, end in speech_segments:
        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)

        # Use noise to simulate speech
        segment_length = end_sample - start_sample
        audio_data[start_sample:end_sample] = np.random.randint(
            -1000, 1000, size=segment_length, dtype=np.int16
        )

    wav_path = output_dir / filename
    with wave.open(str(wav_path), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    return wav_path


def create_mock_transcription(
    num_segments: int = 5,
    duration_per_segment: float = 2.0,
    include_speakers: bool = True,
    include_classification: bool = False
) -> List[dict]:
    """
    Create mock transcription data for testing.

    Args:
        num_segments: Number of segments to create
        duration_per_segment: Duration of each segment in seconds
        include_speakers: Include speaker labels
        include_classification: Include IC/OOC classification

    Returns:
        List of mock transcription segments
    """
    segments = []

    for i in range(num_segments):
        start_time = i * duration_per_segment
        end_time = start_time + duration_per_segment

        segment = {
            'start_time': start_time,
            'end_time': end_time,
            'text': f'Test segment {i+1}'
        }

        if include_speakers:
            segment['speaker'] = f'SPEAKER_{i % 4:02d}'

        if include_classification:
            is_ic = i % 2 == 0
            segment['classification'] = {
                'label': 'IC' if is_ic else 'OOC',
                'confidence': 0.8 + (i * 0.02),
                'reasoning': 'Mock classification',
                'character': f'Character{i}' if is_ic else None
            }

        segments.append(segment)

    return segments
