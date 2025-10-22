"""Simple comprehensive system test (Windows-compatible)"""
import sys
from pathlib import Path

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print('='*70)

def print_test(name, passed, details=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status} {name:30} {details}")
    return passed

def test_imports():
    """Test that all required modules can be imported"""
    print_header("1. TESTING IMPORTS")
    results = []

    # PyTorch
    try:
        import torch
        gpu = "GPU" if torch.cuda.is_available() else "CPU"
        results.append(print_test("PyTorch", True, f"v{torch.__version__} ({gpu})"))
    except Exception as e:
        results.append(print_test("PyTorch", False, str(e)[:40]))

    # faster-whisper
    try:
        import faster_whisper
        results.append(print_test("faster-whisper", True))
    except Exception as e:
        results.append(print_test("faster-whisper", False, str(e)[:40]))

    # pyannote
    try:
        import pyannote.audio
        results.append(print_test("pyannote.audio", True))
    except Exception as e:
        results.append(print_test("pyannote.audio", False, str(e)[:40]))

    # Gradio
    try:
        import gradio
        results.append(print_test("Gradio", True, f"v{gradio.__version__}"))
    except Exception as e:
        results.append(print_test("Gradio", False, str(e)[:40]))

    # pydub
    try:
        import pydub
        results.append(print_test("pydub", True))
    except Exception as e:
        results.append(print_test("pydub", False, str(e)[:40]))

    # Project modules
    try:
        from src.pipeline import DDSessionProcessor
        results.append(print_test("src.pipeline", True))
    except Exception as e:
        results.append(print_test("src.pipeline", False, str(e)[:40]))

    try:
        from src.transcriber import Transcriber
        results.append(print_test("src.transcriber", True))
    except Exception as e:
        results.append(print_test("src.transcriber", False, str(e)[:40]))

    try:
        from src.diarizer import SpeakerDiarizer
        results.append(print_test("src.diarizer", True))
    except Exception as e:
        results.append(print_test("src.diarizer", False, str(e)[:40]))

    try:
        from src.classifier import ICOOCClassifier
        results.append(print_test("src.classifier", True))
    except Exception as e:
        results.append(print_test("src.classifier", False, str(e)[:40]))

    return all(results)

def test_ffmpeg():
    """Test FFmpeg installation"""
    print_header("2. TESTING FFMPEG")
    results = []

    import subprocess

    # Test system FFmpeg
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        version = result.stdout.split('\n')[0] if result.returncode == 0 else "Failed"
        results.append(print_test("System FFmpeg", result.returncode == 0, version[:50]))
    except FileNotFoundError:
        results.append(print_test("System FFmpeg", False, "Not in PATH"))
    except Exception as e:
        results.append(print_test("System FFmpeg", False, str(e)[:40]))

    # Test local FFmpeg
    local_ffmpeg = Path(r"f:/Repos/VideoChunking/ffmpeg/bin/ffmpeg.exe")
    if local_ffmpeg.exists():
        try:
            result = subprocess.run(
                [str(local_ffmpeg), '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            results.append(print_test("Local FFmpeg", result.returncode == 0, str(local_ffmpeg)))
        except Exception as e:
            results.append(print_test("Local FFmpeg", False, str(e)[:40]))
    else:
        results.append(print_test("Local FFmpeg", False, "Not found"))

    return any(results)

def test_ollama():
    """Test Ollama connection"""
    print_header("3. TESTING OLLAMA")
    results = []

    try:
        import ollama
        from src.config import Config

        client = ollama.Client(host=Config.OLLAMA_BASE_URL)

        try:
            models = client.list()
            results.append(print_test("Ollama Connection", True, Config.OLLAMA_BASE_URL))

            model_names = [m['name'] for m in models.get('models', [])]
            if model_names:
                results.append(print_test("Models Available", True, f"{len(model_names)} model(s)"))

                if any('gpt-oss' in m for m in model_names):
                    results.append(print_test("Recommended Model", True, "gpt-oss found"))
                else:
                    results.append(print_test("Recommended Model", False, f"Available: {', '.join(model_names[:2])}"))
            else:
                results.append(print_test("Models Available", False, "No models installed"))

        except Exception as e:
            results.append(print_test("Ollama Connection", False, str(e)[:50]))

    except Exception as e:
        results.append(print_test("Ollama Import", False, str(e)[:40]))

    return len(results) > 0 and results[0]

def test_sample_file():
    """Test sample file accessibility"""
    print_header("4. TESTING SAMPLE FILE")
    results = []

    sample_path = Path(r"C:\Users\Gambit\Documents\Audacity\Sep 19 5m.m4a")

    if sample_path.exists():
        size_mb = sample_path.stat().st_size / (1024 * 1024)
        results.append(print_test("File Exists", True, str(sample_path)))
        results.append(print_test("File Size", True, f"{size_mb:.2f} MB"))
        results.append(print_test("File Readable", sample_path.is_file(), ""))
    else:
        results.append(print_test("File Exists", False, str(sample_path)))

    return all(results)

def test_directories():
    """Test required directories"""
    print_header("5. TESTING DIRECTORIES")
    results = []

    from src.config import Config

    dirs_to_check = [
        ("Output Dir", Config.OUTPUT_DIR),
        ("Temp Dir", Config.TEMP_DIR),
        ("Logs Dir", Path("logs")),
    ]

    for name, path in dirs_to_check:
        path = Path(path)
        if path.exists():
            results.append(print_test(name, True, str(path)))
        else:
            try:
                path.mkdir(parents=True, exist_ok=True)
                results.append(print_test(name, True, f"Created: {path}"))
            except Exception as e:
                results.append(print_test(name, False, str(e)[:40]))

    return all(results)

def test_config():
    """Test configuration"""
    print_header("6. TESTING CONFIGURATION")
    results = []

    try:
        from src.config import Config

        results.append(print_test("Whisper Model", True, Config.WHISPER_MODEL))
        results.append(print_test("Whisper Backend", True, Config.WHISPER_BACKEND))
        results.append(print_test("LLM Backend", True, Config.LLM_BACKEND))
        results.append(print_test("Chunk Length", True, f"{Config.CHUNK_LENGTH_SECONDS}s"))
        results.append(print_test("Output Dir", True, str(Config.OUTPUT_DIR)))

    except Exception as e:
        results.append(print_test("Config Load", False, str(e)[:40]))

    return all(results)

def test_whisper():
    """Test Whisper model loading (optional, slow)"""
    print_header("7. TESTING WHISPER MODEL")
    results = []

    try:
        from src.config import Config
        from src.transcriber import Transcriber

        print(f"  Loading model: {Config.WHISPER_MODEL} (backend: {Config.WHISPER_BACKEND})")
        print("  This may take a moment on first run...")

        transcriber = Transcriber()
        results.append(print_test("Model Load", True, f"{Config.WHISPER_MODEL} ({Config.WHISPER_BACKEND})"))
        results.append(print_test("Transcriber Init", True, "Ready"))

    except Exception as e:
        results.append(print_test("Whisper Model", False, str(e)[:50]))

    return len(results) > 0 and all(results)

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" "*15 + "VIDEOCHUNKING SYSTEM TEST")
    print("="*70)
    print("\nVerifying all components before processing...\n")

    all_results = {}

    # Run tests
    all_results["Imports"] = test_imports()
    all_results["FFmpeg"] = test_ffmpeg()
    all_results["Ollama"] = test_ollama()
    all_results["Sample File"] = test_sample_file()
    all_results["Directories"] = test_directories()
    all_results["Configuration"] = test_config()

    # Whisper test is slow, make it optional
    if "--skip-whisper" not in sys.argv:
        all_results["Whisper Model"] = test_whisper()
    else:
        print("\n[Skipping Whisper model test - use without --skip-whisper to test]")

    # Summary
    print_header("SUMMARY")
    for name, passed in all_results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")

    # Critical components
    critical = ["Imports", "FFmpeg", "Sample File", "Directories"]
    critical_pass = all(all_results.get(comp, False) for comp in critical)

    print("\n" + "="*70)
    if critical_pass:
        print("  *** READY FOR TESTING! ***")
        print("\n  Next steps:")
        print("    python test_sample.py quick   - Quick transcription test (fastest)")
        print("    python test_sample.py         - Full processing test (all features)")
        print("    python app.py                 - Start web interface (http://127.0.0.1:7860)")
        print("\n  Note: Use --skip-whisper flag to skip Whisper model loading test")

        if not all_results.get("Ollama", False):
            print("\n  Note: Ollama not running - IC/OOC classification will be skipped")
            print("        Start with: ollama serve")
    else:
        print("  *** SOME CRITICAL COMPONENTS FAILED ***")
        print("\n  Fix the issues above before processing.")

    print("="*70 + "\n")

    return 0 if critical_pass else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
