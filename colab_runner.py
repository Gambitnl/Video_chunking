"""
This script is designed to be run in a Google Colab environment to offload
GPU-intensive tasks like audio transcription and speaker diarization.

To use this script in Google Colab:
1. Open a new Colab notebook.
2. Ensure the runtime is set to use a GPU (Runtime -> Change runtime type -> GPU).
3. Upload this script and 'requirements.txt' to your Colab session.
4. Create a folder for your audio files (e.g., 'audio_files').
5. Run the script in a cell: !python colab_runner.py audio_files
"""

import os
import sys
from pathlib import Path
import subprocess

class ColabRunner:
    """Handles the execution of the pipeline in a Colab environment."""

    def __init__(self, audio_dir):
        self.audio_dir = Path(audio_dir)

    def setup_environment(self):
        """Install dependencies and sets up the environment."""
        print("Setting up Colab environment...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            sys.exit(1)

    def download_models(self):
        """Download the necessary models for transcription and diarization."""
        print("Downloading models...")
        from src.config import Config
        from src.transcriber import TranscriberFactory
        from src.diarizer import SpeakerDiarizer

        # This will trigger the download of the models
        TranscriberFactory.create()
        SpeakerDiarizer()._load_pipeline_if_needed()
        print("Models downloaded.")

    def run_pipeline(self):
        """Run the full transcription and diarization pipeline."""
        print("Starting pipeline...")
        from src.pipeline import Pipeline
        from src.config import Config

        # Ensure output directories exist
        Config.ensure_directories()

        if not self.audio_dir.is_dir():
            print(f"Error: Audio directory not found at '{self.audio_dir}'")
            return

        for audio_file in self.audio_dir.glob("*.wav"):
            print(f"Processing {audio_file.name}...")
            pipeline = Pipeline(audio_file)
            pipeline.run()
            print(f"Finished processing {audio_file.name}.")
        print("Pipeline finished.")

def main():
    """Main function to run the transcription and diarization pipeline."""
    if len(sys.argv) < 2:
        print("Usage: python colab_runner.py <audio_directory>")
        sys.exit(1)

    audio_directory = sys.argv[1]

    # Add the project root to the Python path
    project_root = Path(__file__).parent
    sys.path.append(str(project_root))

    # Add src to python path
    sys.path.append(str(project_root / 'src'))


    runner = ColabRunner(audio_directory)
    runner.setup_environment()
    runner.download_models()
    runner.run_pipeline()

if __name__ == "__main__":
    main()
