"""Speaker diarization using PyAnnote.audio"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass
import os
import sys
import torch
import numpy as np
import threading
import warnings
import shutil
from .config import Config
from .transcriber import TranscriptionSegment
from .logger import get_logger
from .preflight import PreflightIssue
from .retry import retry_with_backoff

warnings.filterwarnings(
    "ignore",
    message=r"TensorFloat-32 \(TF32\) has been disabled.*",
    category=UserWarning,
    module="pyannote.audio.utils.reproducibility",
)
warnings.filterwarnings(
    "ignore",
    message=r"std\(\): degrees of freedom is <= 0.*",
    category=UserWarning,
    module="pyannote.audio.models.blocks.pooling",
)

try:
    import torchaudio  # type: ignore
except Exception:
    torchaudio = None  # type: ignore
else:
    def _silence_deprecated_backend_calls() -> None:
        """Mask deprecated torchaudio backend helpers that spam warnings on torch>=2.5."""
        try:
            def _noop_set_backend(*args, **kwargs):  # type: ignore[return-type]
                return None

            def _noop_get_backend(*args, **kwargs):  # type: ignore[return-type]
                return "soundfile"

            backend = getattr(torchaudio, "_backend", None)
            if backend is not None:
                if hasattr(backend, "set_audio_backend"):
                    backend.set_audio_backend = _noop_set_backend  # type: ignore[attr-defined]
                if hasattr(backend, "get_audio_backend"):
                    backend.get_audio_backend = _noop_get_backend  # type: ignore[attr-defined]

            if hasattr(torchaudio, "set_audio_backend"):
                torchaudio.set_audio_backend = _noop_set_backend  # type: ignore[attr-defined]
            if hasattr(torchaudio, "get_audio_backend"):
                torchaudio.get_audio_backend = _noop_get_backend  # type: ignore[attr-defined]
        except Exception as exc:
            get_logger("diarizer").debug("Failed to silence torchaudio backend calls: %s", exc)

    _silence_deprecated_backend_calls()

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


def _upgrade_lightning_checkpoint(checkpoint_path: Path, logger) -> None:
    """Run Lightning's checkpoint migration on cached weights to avoid upgrade spam."""
    try:
        checkpoint_file = Path(checkpoint_path)
        if not checkpoint_file.exists():
            return
        from pytorch_lightning.utilities.migration import migrate_checkpoint, pl_legacy_patch  # type: ignore

        backup_path = checkpoint_file.with_suffix(checkpoint_file.suffix + ".bak")
        if not backup_path.exists():
            shutil.copy2(checkpoint_file, backup_path)

        with pl_legacy_patch():
            state = torch.load(checkpoint_file, map_location=torch.device("cpu"))
            migrate_checkpoint(state)
        torch.save(state, checkpoint_file)
    except Exception as exc:  # pragma: no cover - best-effort helper
        logger.debug("Skipping Lightning checkpoint upgrade for %s: %s", checkpoint_path, exc)


@dataclass
class SpeakerSegment:
    """A segment attributed to a specific speaker"""
    speaker_id: str  # e.g., "SPEAKER_00"
    start_time: float
    end_time: float
    confidence: Optional[float] = None


class BaseDiarizer:
    """Abstract base class for diarization backends."""
    def diarize(self, audio_path: Path) -> Tuple[List[SpeakerSegment], Dict[str, np.ndarray]]:
        raise NotImplementedError

    def assign_speakers_to_transcription(
        self,
        transcription_segments: List[TranscriptionSegment],
        speaker_segments: List[SpeakerSegment]
    ) -> List[Dict]:
        """Assign speaker labels based on timing overlap."""
        enriched_segments = []
        for trans_seg in transcription_segments:
            best_speaker, max_overlap = "UNKNOWN", 0.0
            for speaker_seg in speaker_segments:
                overlap = max(0, min(trans_seg.end_time, speaker_seg.end_time) - max(trans_seg.start_time, speaker_seg.start_time))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = speaker_seg.speaker_id
            enriched_segments.append({
                'text': trans_seg.text, 'start_time': trans_seg.start_time, 'end_time': trans_seg.end_time,
                'speaker': best_speaker, 'confidence': trans_seg.confidence, 'words': trans_seg.words
            })
        return enriched_segments

    def preflight_check(self) -> List:
        return []


import requests
import time

class HuggingFaceApiDiarizer(BaseDiarizer):
    """Diarization using the Hugging Face Inference API."""

    def __init__(self):
        self.logger = get_logger("diarizer.huggingface")
        self.api_token = Config.HUGGING_FACE_API_KEY
        self.api_url = f"https://api-inference.huggingface.co/models/{Config.PYANNOTE_DIARIZATION_MODEL}"
        if not self.api_token:
            self.logger.warning(
                "HF_TOKEN is not set. Hugging Face diarizer will be unavailable."
            )

    @retry_with_backoff()
    def _make_api_call(self, data, headers):
        response = requests.post(self.api_url, headers=headers, data=data, timeout=120)
        if response.status_code == 503:
            self.logger.warning("Model is loading on Hugging Face, retrying in 30s...")
            time.sleep(30)
            response = requests.post(self.api_url, headers=headers, data=data, timeout=120)
        response.raise_for_status()
        return response.json()

    def diarize(self, audio_path: Path) -> Tuple[List[SpeakerSegment], Dict[str, np.ndarray]]:
        """Perform speaker diarization using the Hugging Face API."""
        if not self.api_token:
            raise ValueError("HF_TOKEN is not set. Cannot use Hugging Face API.")

        self.logger.info("Offloading diarization to Hugging Face API for %s", audio_path.name)
        headers = {"Authorization": f"Bearer {self.api_token}"}

        with open(audio_path, "rb") as f:
            data = f.read()

        try:
            result = self._make_api_call(data, headers)

        except requests.exceptions.RequestException as e:
            err_body = getattr(e, "response", None)
            err_text = getattr(err_body, "text", "(no response body)")
            self.logger.error("Error calling Hugging Face API: %s. Body: %s", e, err_text)
            return [], {}

        if not isinstance(result, list):
            self.logger.error("Unexpected response format from Hugging Face API: %s", result)
            return [], {}

        segments = []
        for segment_data in result:
            speaker = segment_data.get("label")
            start = segment_data.get("start_time")
            end = segment_data.get("end_time")

            if speaker is None or start is None or end is None:
                self.logger.warning("Skipping invalid segment from API: %s", segment_data)
                continue

            segments.append(SpeakerSegment(
                speaker_id=str(speaker),
                start_time=float(start),
                end_time=float(end),
            ))

        self.logger.info("Received %d speaker segments from Hugging Face API.", len(segments))
        return segments, {}

    def preflight_check(self):
        """Check if the Hugging Face API is configured."""
        issues = []
        if not self.api_token:
            issues.append(
                PreflightIssue(
                    component="diarizer",
                    message="HF_TOKEN not set; Hugging Face diarization backend is unavailable.",
                    severity="warning",
                )
            )
        return issues

class SpeakerDiarizer(BaseDiarizer):
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
        self.embedding_device = "cpu"
        self._cuda_embedding_failed = False

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
                        embedding_checkpoint = hf_hub_download(
                            repo_id=embedding_model_name,
                            filename="pytorch_model.bin",
                            token=token,
                        )
                        _upgrade_lightning_checkpoint(Path(embedding_checkpoint), self.logger)
                    except Exception as exc:
                        raise RuntimeError(
                            f"Unable to download required Hugging Face asset: {exc}"
                        ) from exc

                def _load_component(factory: Callable, model_name: str, **factory_kwargs):
                    if not token:
                        return factory(model_name, **factory_kwargs)
                    try:
                        return factory(model_name, token=token, **factory_kwargs)
                    except TypeError:
                        pass
                    try:
                        return factory(model_name, use_auth_token=token, **factory_kwargs)
                    except TypeError:
                        self.logger.warning(
                            "%s does not accept token parameters; relying on environment.",
                            factory.__qualname__
                        )
                        return factory(model_name, **factory_kwargs)

                self.pipeline = _load_component(Pipeline.from_pretrained, diarization_model_name)

                # Load embedding model for speaker identification
                embedding_model = _load_component(
                    Model.from_pretrained,
                    embedding_model_name,
                    strict=False
                )
                self.embedding_model = Inference(embedding_model, window="whole")

                preferred_device = Config.get_inference_device()
                use_cuda = preferred_device == "cuda" and torch.cuda.is_available()
                if use_cuda:
                    device = torch.device("cuda")
                    self.pipeline = self.pipeline.to(device)
                    if hasattr(self.embedding_model, 'to'):
                        self.embedding_model = self.embedding_model.to(device)
                    self.embedding_device = "cuda"
                    self.logger.info("PyAnnote pipeline moved to CUDA.")
                else:
                    self.logger.info("PyAnnote pipeline running on CPU.")
                    if hasattr(self.embedding_model, 'to'):
                        self.embedding_model = self.embedding_model.to(torch.device("cpu"))
                    self.embedding_device = "cpu"

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

    def _load_audio_for_diarization(self, audio_path: Path):
        """
        Load audio file for diarization, preferring in-memory loading.

        Attempts to load audio using torchaudio for in-memory processing.
        Falls back to file path if in-memory loading fails.

        Args:
            audio_path: Path to audio file

        Returns:
            Either a dict with 'waveform' and 'sample_rate' keys (in-memory),
            or a string path (fallback for file-based loading)
        """
        diarization_input = str(audio_path)
        try:
            import torchaudio  # type: ignore
            waveform, sample_rate = torchaudio.load(str(audio_path))
            diarization_input = {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
            self.logger.debug("Loaded audio in-memory for diarization")
        except Exception as exc:
            self.logger.debug(
                "Falling back to on-disk audio loading for diarization: %s",
                exc
            )

        return diarization_input

    def _perform_diarization(self, diarization_input) -> Tuple[Any, List[SpeakerSegment]]:
        """
        Execute diarization pipeline and convert results to segments.

        Args:
            diarization_input: Either a dict with audio data or a file path string

        Returns:
            A tuple of (diarization_result, segments_list) where:
            - diarization_result: Raw result from pyannote pipeline (needed for embeddings)
            - segments_list: List of SpeakerSegment objects
        """
        self.logger.debug("Running diarization pipeline...")
        diarization = self.pipeline(diarization_input)

        # Convert to our format
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(SpeakerSegment(
                speaker_id=speaker,
                start_time=turn.start,
                end_time=turn.end
            ))

        self.logger.info(
            "Diarization complete: %d segments, %d speakers",
            len(segments),
            len(set(seg.speaker_id for seg in segments))
        )

        return diarization, segments

    def _extract_speaker_embeddings(
        self,
        audio_path: Path,
        diarization
    ) -> Dict[str, np.ndarray]:
        """
        Extract speaker embeddings for each diarized speaker.

        Uses the embedding model to extract voice embeddings for each speaker
        identified in the diarization result. Embeddings are averaged across
        all segments for each speaker.

        Args:
            audio_path: Path to audio file
            diarization: Raw diarization result from pyannote pipeline

        Returns:
            Dictionary mapping speaker IDs to their embedding arrays
        """
        speaker_embeddings: Dict[str, np.ndarray] = {}

        if self.embedding_model is None:
            self.logger.debug("No embedding model available, skipping embedding extraction")
            return speaker_embeddings

        # Import pydub for audio segment extraction
        try:
            from pydub import AudioSegment
        except Exception as exc:
            self.logger.warning(
                "Unable to import pydub for embedding extraction: %s",
                exc
            )
            return speaker_embeddings

        # Load audio file
        try:
            audio = AudioSegment.from_wav(str(audio_path))
        except Exception as exc:
            self.logger.warning(
                "Unable to load %s for speaker embeddings: %s",
                audio_path,
                exc
            )
            return speaker_embeddings

        # Extract embeddings for each speaker
        for speaker_id in diarization.labels():
            try:
                speaker_segments = diarization.label_timeline(speaker_id)
                speaker_audio = AudioSegment.empty()

                # Concatenate all segments for this speaker
                for segment in speaker_segments:
                    speaker_audio += audio[segment.start * 1000:segment.end * 1000]

                if len(speaker_audio) <= 0:
                    self.logger.debug("Skipping %s: no audio data", speaker_id)
                    continue

                # Convert to numpy array and normalize
                samples = np.array(
                    speaker_audio.get_array_of_samples(),
                    dtype=np.float32
                ) / 32768.0

                # Prepare tensor and run inference
                samples_tensor = self._prepare_waveform_tensor(samples)
                embedding = self._run_embedding_inference(samples_tensor, audio.frame_rate)
                speaker_embeddings[speaker_id] = self._embedding_to_numpy(embedding)

                self.logger.debug("Extracted embedding for %s", speaker_id)

            except Exception as exc:
                self.logger.warning(
                    "Failed to extract embedding for %s: %s",
                    speaker_id,
                    exc
                )

        self.logger.info("Extracted embeddings for %d speakers", len(speaker_embeddings))
        return speaker_embeddings

    def diarize(self, audio_path: Path) -> Tuple[List[SpeakerSegment], Dict[str, np.ndarray]]:
        """
        Perform speaker diarization on audio file.

        This method orchestrates the complete diarization pipeline:
        1. Load and initialize the diarization pipeline
        2. Load audio file for processing
        3. Execute speaker diarization
        4. Extract speaker embeddings

        Args:
            audio_path: Path to WAV file

        Returns:
            A tuple containing:
            - A list of SpeakerSegment objects
            - A dictionary mapping speaker IDs to their embeddings
        """
        self._load_pipeline_if_needed()

        if self.pipeline is None:
            # Fallback: create dummy single-speaker segments
            segments = self._create_fallback_diarization(audio_path)
            return segments, {}

        # Step 1: Load audio for diarization
        diarization_input = self._load_audio_for_diarization(audio_path)

        # Step 2: Perform diarization
        diarization, segments = self._perform_diarization(diarization_input)

        # Step 3: Extract speaker embeddings
        speaker_embeddings = self._extract_speaker_embeddings(audio_path, diarization)

        return segments, speaker_embeddings

    def _prepare_waveform_tensor(self, samples: np.ndarray) -> torch.Tensor:
        tensor = torch.from_numpy(samples).unsqueeze(0)
        if self.embedding_device == "cuda" and torch.cuda.is_available():
            return tensor.to("cuda")
        return tensor

    def _run_embedding_inference(self, waveform: torch.Tensor, sample_rate: int):
        if self.embedding_model is None:
            raise RuntimeError("Embedding model is not initialized.")

        payload = {
            "waveform": waveform,
            "sample_rate": sample_rate
        }

        try:
            with torch.inference_mode():
                return self.embedding_model(payload)
        except RuntimeError as exc:
            message = str(exc).lower()
            if "cuda error" in message and self.embedding_device == "cuda":
                if not self._cuda_embedding_failed:
                    self.logger.warning(
                        "CUDA embedding failed (%s). Switching embeddings to CPU for the remainder of the session.",
                        exc
                    )
                    self._cuda_embedding_failed = True
                self._move_embedding_model_to_cpu()
                cpu_payload = {
                    "waveform": waveform.to("cpu"),
                    "sample_rate": sample_rate
                }
                with torch.inference_mode():
                    return self.embedding_model(cpu_payload)
            raise

    def _move_embedding_model_to_cpu(self) -> None:
        if self.embedding_model is None:
            return
        if hasattr(self.embedding_model, "to"):
            self.embedding_model = self.embedding_model.to(torch.device("cpu"))
        self.embedding_device = "cpu"

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

    def _embedding_to_numpy(self, embedding: Any) -> np.ndarray:
        """
        Normalize PyAnnote embedding outputs to numpy arrays.

        PyAnnote 3.x may return tensors, numpy arrays, or SlidingWindowFeature objects.
        """
        if embedding is None:
            raise ValueError("Embedding output is None")

        if torch is not None and isinstance(embedding, torch.Tensor):
            return embedding.detach().cpu().float().squeeze().numpy()

        if isinstance(embedding, np.ndarray):
            return np.asarray(embedding, dtype=np.float32).squeeze()

        data_attr = getattr(embedding, "data", None)
        if data_attr is not None:
            return self._embedding_to_numpy(data_attr)

        numpy_method = getattr(embedding, "numpy", None)
        if callable(numpy_method):
            return np.asarray(numpy_method(), dtype=np.float32).squeeze()

        try:
            return np.asarray(embedding, dtype=np.float32).squeeze()
        except Exception as exc:
            raise TypeError(
                f"Unsupported embedding type: {type(embedding)}"
            ) from exc


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

class DiarizerFactory:
    """Factory to create the appropriate diarizer based on config."""

    @staticmethod
    def create(backend: str = None):
        """
        Create a diarizer instance.

        Args:
            backend (str): 'local' or 'huggingface'. Defaults to config.

        Returns:
            An instance of a diarizer class.
        """
        backend = backend or Config.DIARIZATION_BACKEND
        if backend == "hf_api":
            return HuggingFaceApiDiarizer()
        elif backend in ("pyannote", "local"):
            return SpeakerDiarizer()
        else:
            raise ValueError(f"Unknown diarizer backend: {backend}")
