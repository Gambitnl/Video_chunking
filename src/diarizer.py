"""Speaker diarization using PyAnnote.audio"""
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import torch
import numpy as np
from .config import Config
from .transcriber import TranscriptionSegment


@dataclass
class SpeakerSegment:
    """A segment attributed to a specific speaker"""
    speaker_id: str  # e.g., "SPEAKER_00"
    start_time: float
    end_time: float
    confidence: Optional[float] = None


class SpeakerDiarizer:
    """
    Speaker diarization using PyAnnote.audio.

    Purpose:
    - Identify "who spoke when" in the audio
    - Assign speaker labels to transcription segments
    - Learn speaker identities over multiple sessions

    Challenge for this project:
    - 4 speakers (3 players + 1 DM)
    - Single room mic = overlapping speech
    - Same person voices multiple characters

    PyAnnote.audio is state-of-the-art for this task.
    """

    def __init__(self, num_speakers: int = 4):
        """
        Args:
            num_speakers: Expected number of speakers (helps accuracy)
        """
        self.num_speakers = num_speakers
        self.pipeline = None
        self._init_pipeline()

    def _init_pipeline(self):
        """
        Initialize PyAnnote pipeline.

        Note: Requires HuggingFace token for some models.
        Uses public models when possible.
        """
        try:
            from pyannote.audio import Pipeline

            # Try to load the pipeline
            # You may need to accept terms at: https://huggingface.co/pyannote/speaker-diarization
            # Then create a token at: https://huggingface.co/settings/tokens
            # And set it in environment: HF_TOKEN=your_token

            model_name = "pyannote/speaker-diarization-3.1"

            # Check for HuggingFace token
            import os
            hf_token = os.getenv("HF_TOKEN")

            if hf_token:
                self.pipeline = Pipeline.from_pretrained(
                    model_name,
                    use_auth_token=hf_token
                )
            else:
                # Try without token (may fail for some models)
                self.pipeline = Pipeline.from_pretrained(model_name)

            # Move to GPU if available
            if torch.cuda.is_available():
                self.pipeline = self.pipeline.to(torch.device("cuda"))

        except Exception as e:
            print(f"Warning: Could not initialize PyAnnote pipeline: {e}")
            print("Speaker diarization will be limited.")
            print("\nTo use full diarization:")
            print("1. Visit: https://huggingface.co/pyannote/speaker-diarization")
            print("2. Accept the terms")
            print("3. Create token: https://huggingface.co/settings/tokens")
            print("4. Set HF_TOKEN in your .env file")
            self.pipeline = None

    def diarize(self, audio_path: Path) -> List[SpeakerSegment]:
        """
        Perform speaker diarization on audio file.

        Args:
            audio_path: Path to WAV file

        Returns:
            List of SpeakerSegment objects
        """
        if self.pipeline is None:
            # Fallback: create dummy single-speaker segments
            return self._create_fallback_diarization(audio_path)

        # Run diarization
        diarization = self.pipeline(
            str(audio_path),
            num_speakers=self.num_speakers
        )

        # Convert to our format
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(SpeakerSegment(
                speaker_id=speaker,
                start_time=turn.start,
                end_time=turn.end
            ))

        return segments

    def _create_fallback_diarization(self, audio_path: Path) -> List[SpeakerSegment]:
        """
        Fallback when PyAnnote is not available.
        Creates a single speaker for the entire audio.
        """
        from pydub import AudioSegment

        audio = AudioSegment.from_file(str(audio_path))
        duration = len(audio) / 1000.0

        return [SpeakerSegment(
            speaker_id="SPEAKER_00",
            start_time=0.0,
            end_time=duration
        )]

    def assign_speakers_to_transcription(
        self,
        transcription_segments: List[TranscriptionSegment],
        speaker_segments: List[SpeakerSegment]
    ) -> List[Dict]:
        """
        Assign speaker labels to transcription segments.

        Strategy:
        - For each transcription segment, find overlapping speaker segment
        - Use the speaker with maximum overlap
        - Return enriched segments with speaker info

        Args:
            transcription_segments: Transcribed text segments
            speaker_segments: Speaker diarization results

        Returns:
            List of dicts with {text, start, end, speaker, ...}
        """
        enriched_segments = []

        for trans_seg in transcription_segments:
            # Find speaker with maximum overlap
            best_speaker = None
            max_overlap = 0.0

            for speaker_seg in speaker_segments:
                overlap = self._calculate_overlap(
                    trans_seg.start_time,
                    trans_seg.end_time,
                    speaker_seg.start_time,
                    speaker_seg.end_time
                )

                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = speaker_seg.speaker_id

            enriched_segments.append({
                'text': trans_seg.text,
                'start_time': trans_seg.start_time,
                'end_time': trans_seg.end_time,
                'speaker': best_speaker or "UNKNOWN",
                'confidence': trans_seg.confidence,
                'words': trans_seg.words
            })

        return enriched_segments

    def _calculate_overlap(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float
    ) -> float:
        """Calculate overlap duration between two time segments"""
        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)

        if overlap_end <= overlap_start:
            return 0.0

        return overlap_end - overlap_start


class SpeakerProfileManager:
    """
    Manages speaker profiles across multiple sessions.

    Purpose:
    - Learn which SPEAKER_XX corresponds to which actual person
    - Persist mappings across sessions
    - Allow manual labeling that improves over time

    Future enhancement:
    - Compare voice embeddings across sessions
    - Automatically map SPEAKER_00 in session 2 to same person in session 1
    """

    def __init__(self, profile_file: Path = None):
        self.profile_file = profile_file or (Config.MODELS_DIR / "speaker_profiles.json")
        self.profiles = self._load_profiles()

    def _load_profiles(self) -> Dict:
        """Load existing speaker profiles"""
        import json

        if self.profile_file.exists():
            with open(self.profile_file, 'r') as f:
                return json.load(f)
        return {}

    def save_profiles(self):
        """Save speaker profiles to disk"""
        import json

        self.profile_file.parent.mkdir(exist_ok=True)
        with open(self.profile_file, 'w') as f:
            json.dump(self.profiles, f, indent=2)

    def map_speaker(
        self,
        session_id: str,
        speaker_id: str,
        person_name: str
    ):
        """
        Map a speaker ID to an actual person.

        Args:
            session_id: Unique session identifier
            speaker_id: PyAnnote speaker ID (e.g., "SPEAKER_00")
            person_name: Actual person name (e.g., "Player1", "DM")
        """
        if session_id not in self.profiles:
            self.profiles[session_id] = {}

        self.profiles[session_id][speaker_id] = person_name
        self.save_profiles()

    def get_person_name(
        self,
        session_id: str,
        speaker_id: str
    ) -> Optional[str]:
        """Get person name for a speaker ID in a session"""
        return self.profiles.get(session_id, {}).get(speaker_id)
