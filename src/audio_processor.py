"""Audio conversion and preprocessing"""
import subprocess
from pathlib import Path
from typing import Tuple
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from .config import Config
from .logger import get_logger


class AudioProcessor:
    """Handles audio file conversion and preprocessing"""

    def __init__(self):
        self.sample_rate = Config.AUDIO_SAMPLE_RATE
        self.logger = get_logger("audio")
        # Try to find FFmpeg - first in PATH, then in local install
        self.ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable - try PATH first, then local install"""
        import shutil

        # Try to find in PATH
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            self.logger.debug("FFmpeg discovered in PATH: %s", ffmpeg_in_path)
            return "ffmpeg"

        # Try local installation
        local_ffmpeg = Config.PROJECT_ROOT / "ffmpeg" / "bin" / "ffmpeg.exe"
        if local_ffmpeg.exists():
            self.logger.debug("FFmpeg discovered in local bundle: %s", local_ffmpeg)
            return str(local_ffmpeg)

        # Default to "ffmpeg" and let it fail with helpful error
        self.logger.warning("FFmpeg not found; relying on system PATH resolution")
        return "ffmpeg"

    def convert_to_wav(self, input_path: Path, output_path: Path = None) -> Path:
        """
        Convert M4A (or any format) to WAV at optimal settings for Whisper.

        Args:
            input_path: Path to input audio file
            output_path: Optional output path (auto-generated if None)

        Returns:
            Path to converted WAV file

        Design rationale:
        - 16kHz mono: Whisper's training data format
        - WAV format: Lossless, widely compatible
        - FFmpeg: Fast, reliable, handles all formats
        """
        if output_path is None:
            output_path = Config.TEMP_DIR / f"{input_path.stem}_converted.wav"

        self.logger.info("Converting %s -> %s (sample_rate=%s)", input_path, output_path, self.sample_rate)

        # Use FFmpeg for conversion
        # -ar: sample rate, -ac: channels (1=mono), -y: overwrite
        command = [
            self.ffmpeg_path,
            "-i", str(input_path),
            "-ar", str(self.sample_rate),
            "-ac", "1",  # Convert to mono
            "-y",  # Overwrite without asking
            str(output_path)
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )
            self.logger.debug("FFmpeg conversion command succeeded: %s", " ".join(command))
            return output_path
        except subprocess.CalledProcessError as e:
            self.logger.error("FFmpeg conversion failed: %s", e.stderr.strip())
            raise RuntimeError(f"FFmpeg conversion failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg: "
                "https://ffmpeg.org/download.html"
            )

    def load_audio(self, path: Path) -> Tuple[np.ndarray, int]:
        """
        Load audio file into numpy array.

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        audio, sr = sf.read(str(path))
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32, copy=False)
        return audio, sr

    def get_duration(self, path: Path) -> float:
        """
        Get audio duration in seconds.

        Args:
            path: Path to audio file

        Returns:
            Duration in seconds
        """
        audio = AudioSegment.from_file(str(path))
        return len(audio) / 1000.0  # pydub uses milliseconds

    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio to prevent clipping and improve consistency.

        Design rationale:
        - Single-room mic = inconsistent volume levels
        - Normalization helps with VAD accuracy
        - Peak normalization preserves dynamics
        """
        if audio.max() > 0:
            return (audio / np.abs(audio).max()).astype(np.float32, copy=False)
        return audio.astype(np.float32, copy=False)

    def save_audio(self, audio: np.ndarray, path: Path, sample_rate: int = None):
        """Save audio array to file"""
        if sample_rate is None:
            sample_rate = self.sample_rate

        sf.write(str(path), audio, sample_rate)
