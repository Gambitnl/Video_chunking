
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

    @patch('subprocess.run')
    def test_convert_to_wav_accepts_named_string(self, mock_run, processor):
        mock_run.return_value = MagicMock(check=True)

        class DummyNamedString(str):
            pass

        dummy = DummyNamedString("/in/test_clip.m4a")
        dummy.name = "/in/test_clip.m4a"

        result_path = processor.convert_to_wav(dummy)

        expected_output = Path("/tmp/temp_dir/test_clip_converted.wav")
        expected_input = Path("/in/test_clip.m4a")
        assert result_path == expected_output

        command = mock_run.call_args[0][0]
        assert str(expected_input) in command
        assert str(expected_output) in command

    @patch('src.audio_processor.sf.read')
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

    @patch('src.audio_processor.sf.write')
    def test_save_audio(self, mock_sf_write, processor):
        audio = np.zeros(100)
        path = Path("/out/test.wav")
        processor.save_audio(audio, path)
        mock_sf_write.assert_called_once_with(str(path), audio, 16000)

    @patch('src.audio_processor.sf.SoundFile')
    def test_load_audio_segment(self, mock_soundfile, processor):
        mock_file_instance = MagicMock()
        mock_soundfile.return_value.__enter__.return_value = mock_file_instance
        mock_file_instance.samplerate = 16000
        mock_file_instance.read.return_value = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        path = Path("/in/test.wav")
        start_time = 1.0
        end_time = 1.2

        audio_data, sr = processor.load_audio_segment(path, start_time, end_time)

        assert sr == 16000
        assert np.array_equal(audio_data, np.array([0.1, 0.2, 0.3], dtype=np.float32))
        mock_soundfile.assert_called_once_with(str(path), 'r')
        mock_file_instance.seek.assert_called_once_with(int(start_time * sr))
        mock_file_instance.read.assert_called_once_with(frames=int((end_time - start_time) * sr), dtype='float32')
