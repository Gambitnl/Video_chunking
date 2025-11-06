"""Speaker diarization using PyAnnote.audio"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import os
import sys
import torch
import numpy as np
import threading
from .config import Config
from .transcriber import TranscriptionSegment
from .logger import get_logger
from .preflight import PreflightIssue

try:
    import torchaudio  # type: ignore
except Exception:
    torchaudio = None  # type: ignore

if torchaudio is not None:
    try:
        if not hasattr(torchaudio, "list_audio_backends"):
            from torchaudio.utils import list_audio_backends as _list_audio_backends  # type: ignore

            def _list_backends_wrapper():  # type: ignore[return-type]
                try:
                    return _list_audio_backends()
                except Exception:
                    return []

            torchaudio.list_audio_backends = _list_backends_wrapper  # type: ignore[attr-defined]
    except Exception:
        pass

try:
    import speechbrain.inference as _sb_inference  # type: ignore
    sys.modules.setdefault("speechbrain.pretrained", _sb_inference)
    from speechbrain.utils import torch_audio_backend as _sb_backend  # type: ignore

    def _noop_check_backend():  # type: ignore[return-type]
        """SpeechBrain backend check overridden to avoid deprecated torchaudio APIs."""
        return None

    _sb_backend.check_torchaudio_backend = _noop_check_backend  # type: ignore[attr-defined]
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
_ffmpeg_candidates = [
    REPO_ROOT / "ffmpeg" / "bin",
]
shared_root = REPO_ROOT / "ffmpeg_shared"
if shared_root.exists():
    for candidate in shared_root.rglob("bin"):
        _ffmpeg_candidates.append(candidate)
for candidate in _ffmpeg_candidates:
    if candidate.exists():
        path_str = str(candidate)
        if path_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{path_str}{os.pathsep}{os.environ.get('PATH', '')}"


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

    This class uses a lazy-loading, thread-safe pattern to initialize the pipeline
    only when it is first needed.
    """

    def __init__(self):
        """Initialize the diarizer with lazy model loading."""
        self.pipeline = None
        self.embedding_model = None
        self.model_load_lock = threading.Lock()
        self.logger = get_logger("diarizer")

    def _load_pipeline_if_needed(self):
        """Load the PyAnnote pipeline on first use, in a thread-safe manner."""
        with self.model_load_lock:
            if self.pipeline is not None:
                return

            try:
                from pyannote.audio import Pipeline, Model, Inference
                from huggingface_hub import hf_hub_download

                diarization_model_name = Config.PYANNOTE_DIARIZATION_MODEL
                embedding_model_name = Config.PYANNOTE_EMBEDDING_MODEL

                self.logger.info(
                    "Initializing PyAnnote pipeline (model=%s, embedding=%s)...",
                    diarization_model_name,
                    embedding_model_name
                )
                self.logger.info("This is a one-time download and may take a moment.")

                token = Config.HF_TOKEN
                if not token:
                    self.logger.warning(
                        "HF_TOKEN is not set. Access to %s may be denied.",
                        diarization_model_name
                    )
                else:
                    # Ensure Hugging Face tooling sees the token even if downstream
                    # libraries ignore explicit kwargs.
                    os.environ.setdefault("HF_TOKEN", token)
                    os.environ["HF_HUB_TOKEN"] = token
                    os.environ["HUGGINGFACEHUB_API_TOKEN"] = token
                    os.environ["HUGGING_FACE_HUB_TOKEN"] = token

                    # Proactively download community assets required by downstream
                    # diarization components so we fail fast if access is missing.
                    try:
                        if diarization_model_name == "pyannote/speaker-diarization-community-1":
                            hf_hub_download(
                                repo_id=diarization_model_name,
                                filename="plda/xvec_transform.npz",
                                token=token,
                            )
                        hf_hub_download(
                            repo_id=embedding_model_name,
                            filename="pytorch_model.bin",
                            token=token,
                        )
                    except Exception as exc:
                        raise RuntimeError(
                            f"Unable to download required Hugging Face asset: {exc}"
                        ) from exc

                def _load_component(factory, model_name: str):
                    if not token:
                        return factory(model_name)
                    try:
                        return factory(model_name, token=token)
                    except TypeError:
                        pass
                    try:
                        return factory(model_name, use_auth_token=token)
                    except TypeError:
                        self.logger.warning(
                            "%s does not accept token parameters; relying on environment.",
                            factory.__qualname__
                        )
                        return factory(model_name)

                self.pipeline = _load_component(Pipeline.from_pretrained, diarization_model_name)

                # Load embedding model for speaker identification
                embedding_model = _load_component(Model.from_pretrained, embedding_model_name)
                self.embedding_model = Inference(embedding_model, window="whole")

                preferred_device = Config.get_inference_device()
                if preferred_device == "cuda":
                    device = torch.device("cuda")
                    self.pipeline = self.pipeline.to(device)
                    if hasattr(self.embedding_model, 'to'):
                        self.embedding_model = self.embedding_model.to(device)
                    self.logger.info("PyAnnote pipeline moved to CUDA.")
                else:
                    self.logger.info("PyAnnote pipeline running on CPU.")

                self.logger.info("PyAnnote pipeline initialized successfully.")

            except Exception as e:
                self.logger.warning("Could not initialize PyAnnote pipeline: %s", e)
                self.logger.warning("Speaker diarization will be limited.")
                self.logger.info("To use full diarization:")
                self.logger.info("1. Visit: https://huggingface.co/pyannote/speaker-diarization")
                self.logger.info("2. Accept the terms")
                self.logger.info("3. Create token: https://huggingface.co/settings/tokens")
                self.logger.info("4. Set HF_TOKEN in your .env file")
                self.pipeline = None # Ensure it's None on failure

    def diarize(self, audio_path: Path) -> Tuple[List[SpeakerSegment], Dict[str, np.ndarray]]:
        """
        Perform speaker diarization on audio file.

        Args:
            audio_path: Path to WAV file

        Returns:
            A tuple containing:
            - A list of SpeakerSegment objects.
            - A dictionary mapping speaker IDs to their embeddings.
        """
        self._load_pipeline_if_needed()

        if self.pipeline is None:
            # Fallback: create dummy single-speaker segments
            segments = self._create_fallback_diarization(audio_path)
            return segments, {}

        # Run diarization
        diarization_input = str(audio_path)
        try:
            import torchaudio  # type: ignore
            waveform, sample_rate = torchaudio.load(str(audio_path))
            diarization_input = {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
        except Exception as exc:
            self.logger.debug(
                "Falling back to on-disk audio loading for diarization: %s",
                exc
            )

        diarization = self.pipeline(diarization_input)

        # Convert to our format
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(SpeakerSegment(
                speaker_id=speaker,
                start_time=turn.start,
                end_time=turn.end
            ))

        # Extract speaker embeddings using the loaded model
        speaker_embeddings = {}
        if self.embedding_model is not None:
            for speaker_id in diarization.labels():
                # Get all segments for this speaker
                speaker_segments = diarization.label_timeline(speaker_id)
                # Extract the audio for this speaker
                from pydub import AudioSegment
                audio = AudioSegment.from_wav(str(audio_path))
                speaker_audio = AudioSegment.empty()
                for segment in speaker_segments:
                    speaker_audio += audio[segment.start * 1000:segment.end * 1000]

                # Get the embedding for this speaker
                if len(speaker_audio) > 0:
                    # Convert to numpy array
                    samples = np.array(speaker_audio.get_array_of_samples()).astype(np.float32) / 32768.0
                    samples_tensor = torch.from_numpy(samples).unsqueeze(0)
                    embedding = self.embedding_model({"waveform": samples_tensor, "sample_rate": audio.frame_rate})
                    speaker_embeddings[speaker_id] = embedding.squeeze().numpy()

        return segments, speaker_embeddings

    def preflight_check(self):
        issues = []
        token = Config.HF_TOKEN

        if not token:
            issues.append(
                PreflightIssue(
                    component="diarizer",
                    message="HF_TOKEN not set; diarization will fall back to single-speaker output.",
                    severity="warning",
                )
            )
            return issues

        try:
            from huggingface_hub import HfApi  # type: ignore
            try:
                from huggingface_hub import HfHubHTTPError  # type: ignore
            except ImportError:
                HfHubHTTPError = Exception  # type: ignore
        except Exception as exc:
            issues.append(
                PreflightIssue(
                    component="diarizer",
                    message=f"huggingface_hub not available: {exc}",
                    severity="error",
                )
            )
            return issues

        api = HfApi()
        required_repos = [
            Config.PYANNOTE_DIARIZATION_MODEL,
            "pyannote/segmentation-3.0",
            Config.PYANNOTE_EMBEDDING_MODEL,
        ]

        for repo in dict.fromkeys(required_repos):
            try:
                api.model_info(repo, token=token)
            except HfHubHTTPError as err:
                response = getattr(err, "response", None)
                status = getattr(response, "status_code", "unknown status")
                issues.append(
                    PreflightIssue(
                        component="diarizer",
                        message=(
                            f"Access to {repo} denied ({status}). "
                            "Visit the model page and accept the terms."
                        ),
                        severity="error",
                    )
                )
            except Exception as exc:  # pragma: no cover - unexpected network failures
                issues.append(
                    PreflightIssue(
                        component="diarizer",
                        message=f"Failed to verify {repo}: {exc}",
                        severity="error",
                    )
                )
        return issues

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

        if speaker_id not in self.profiles[session_id]:
            self.profiles[session_id][speaker_id] = {}

        self.profiles[session_id][speaker_id]["name"] = person_name
        self.save_profiles()

    def get_person_name(
        self,
        session_id: str,
        speaker_id: str
    ) -> Optional[str]:
        """Get person name for a speaker ID in a session"""
        return self.profiles.get(session_id, {}).get(speaker_id, {}).get("name")

    def save_speaker_embeddings(
        self,
        session_id: str,
        speaker_embeddings: Dict[str, np.ndarray]
    ):
        """
        Save speaker embeddings for a session.

        Args:
            session_id: Unique session identifier
            speaker_embeddings: A dictionary mapping speaker IDs to their embeddings.
        """
        if session_id not in self.profiles:
            self.profiles[session_id] = {}

        for speaker_id, embedding in speaker_embeddings.items():
            if speaker_id not in self.profiles[session_id]:
                self.profiles[session_id][speaker_id] = {}
            self.profiles[session_id][speaker_id]["embedding"] = embedding.tolist()
        self.save_profiles()
