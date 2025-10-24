
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import numpy as np
import subprocess

# Mock the config before other imports
@pytest.fixture(autouse=True)
def mock_config():
    with patch('src.audio_processor.Config') as MockConfig:
        MockConfig.AUDIO_SAMPLE_RATE = 16000
        MockConfig.PROJECT_ROOT = Path("/fake/project")
        MockConfig.TEMP_DIR = Path("/tmp/temp_dir")
        yield MockConfig

from src.audio_processor import AudioProcessor

@pytest.fixture
def processor():
    """Provides an AudioProcessor instance with mocked ffmpeg path."""
    with patch.object(AudioProcessor, '_find_ffmpeg', return_value='ffmpeg'):
        yield AudioProcessor()

class TestAudioProcessor:

    @patch('shutil.which', return_value='/usr/bin/ffmpeg')
    def test_find_ffmpeg_in_path(self, mock_which):
        processor = AudioProcessor()
        assert processor.ffmpeg_path == 'ffmpeg'

    @patch('shutil.which', return_value=None)
    @patch('pathlib.Path.exists', return_value=True)
    def test_find_ffmpeg_in_local_bundle(self, mock_exists, mock_which, mock_config):
        processor = AudioProcessor()
        expected_path = str(mock_config.PROJECT_ROOT / "ffmpeg" / "bin" / "ffmpeg.exe")
        assert processor.ffmpeg_path == expected_path

    @patch('shutil.which', return_value=None)
    @patch('pathlib.Path.exists', return_value=False)
    def test_find_ffmpeg_fallback(self, mock_exists, mock_which):
        processor = AudioProcessor()
        assert processor.ffmpeg_path == 'ffmpeg'

    @patch('subprocess.run')
    def test_convert_to_wav_success(self, mock_run, processor):
        mock_run.return_value = MagicMock(check=True)
        input_path = Path("/in/test.m4a")
        output_path = Path("/out/test.wav")
        
        result_path = processor.convert_to_wav(input_path, output_path)

        assert result_path == output_path
        mock_run.assert_called_once()
        # Check that the command includes the correct arguments
        command = mock_run.call_args[0][0]
        assert str(input_path) in command
        assert str(output_path) in command
        assert "-ar" in command
        assert "16000" in command
        assert "-ac" in command
        assert "1" in command

    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cmd', stderr='Error'))
    def test_convert_to_wav_failure(self, mock_run, processor):
        with pytest.raises(RuntimeError, match="FFmpeg conversion failed: Error"):
            processor.convert_to_wav(Path("in.m4a"), Path("out.wav"))

    @patch('soundfile.read')
    def test_load_audio(self, mock_sf_read, processor):
        mock_sf_read.return_value = (np.array([0, 1], dtype=np.int16), 16000)
        audio, sr = processor.load_audio(Path("test.wav"))
        assert sr == 16000
        assert audio.dtype == np.float32

    @patch('pydub.AudioSegment.from_file')
    def test_get_duration(self, mock_from_file, processor):
        mock_segment = MagicMock()
        mock_segment.__len__.return_value = 2500 # 2.5 seconds in ms
        mock_from_file.return_value = mock_segment
        duration = processor.get_duration(Path("test.wav"))
        assert duration == 2.5

    def test_normalize_audio(self, processor):
        audio = np.array([-0.5, 0.0, 0.5, 1.0], dtype=np.float32)
        normalized = processor.normalize_audio(audio)
        assert np.abs(normalized).max() == pytest.approx(1.0)

    def test_normalize_silent_audio(self, processor):
        audio = np.zeros(100, dtype=np.float32)
        normalized = processor.normalize_audio(audio)
        assert np.all(normalized == 0)

    @patch('soundfile.write')
    def test_save_audio(self, mock_sf_write, processor):
        audio = np.zeros(100)
        path = Path("/out/test.wav")
        processor.save_audio(audio, path)
        mock_sf_write.assert_called_once_with(str(path), audio, 16000)
