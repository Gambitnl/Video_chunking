"""Comprehensive system test to verify all components work"""
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def test_imports():
    """Test that all required modules can be imported"""
    console.print("\n[bold cyan]1. Testing Imports...[/bold cyan]")

    tests = []

    # Core dependencies
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        tests.append(("PyTorch", True, f"v{torch.__version__} (GPU: {gpu_available})"))
    except Exception as e:
        tests.append(("PyTorch", False, str(e)[:50]))

    try:
        import faster_whisper
        tests.append(("faster-whisper", True, "Installed"))
    except Exception as e:
        tests.append(("faster-whisper", False, str(e)[:50]))

    try:
        import pyannote.audio
        tests.append(("pyannote.audio", True, "Installed"))
    except Exception as e:
        tests.append(("pyannote.audio", False, str(e)[:50]))

    try:
        import gradio as gr
        tests.append(("Gradio", True, f"v{gr.__version__}"))
    except Exception as e:
        tests.append(("Gradio", False, str(e)[:50]))

    try:
        import pydub
        tests.append(("pydub", True, "Installed"))
    except Exception as e:
        tests.append(("pydub", False, str(e)[:50]))

    # Project modules
    try:
        from src.pipeline import DDSessionProcessor
        tests.append(("src.pipeline", True, "Loaded"))
    except Exception as e:
        tests.append(("src.pipeline", False, str(e)[:50]))

    try:
        from src.transcriber import Transcriber
        tests.append(("src.transcriber", True, "Loaded"))
    except Exception as e:
        tests.append(("src.transcriber", False, str(e)[:50]))

    try:
        from src.diarizer import SpeakerDiarizer
        tests.append(("src.diarizer", True, "Loaded"))
    except Exception as e:
        tests.append(("src.diarizer", False, str(e)[:50]))

    try:
        from src.classifier import ICOOCClassifier
        tests.append(("src.classifier", True, "Loaded"))
    except Exception as e:
        tests.append(("src.classifier", False, str(e)[:50]))

    # Display results
    table = Table(title="Import Tests")
    table.add_column("Module", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, success, details in tests:
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        table.add_row(name, status, details)

    console.print(table)

    all_ok = all(t[1] for t in tests)
    return all_ok, tests

def test_ffmpeg():
    """Test FFmpeg installation and accessibility"""
    console.print("\n[bold cyan]2. Testing FFmpeg...[/bold cyan]")

    import subprocess
    tests = []

    # Test system FFmpeg
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            tests.append(("System FFmpeg", True, version_line[:60]))
        else:
            tests.append(("System FFmpeg", False, "Non-zero exit code"))
    except FileNotFoundError:
        tests.append(("System FFmpeg", False, "Not found in PATH"))
    except Exception as e:
        tests.append(("System FFmpeg", False, str(e)[:50]))

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
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                tests.append(("Local FFmpeg", True, version_line[:60]))
            else:
                tests.append(("Local FFmpeg", False, "Non-zero exit code"))
        except Exception as e:
            tests.append(("Local FFmpeg", False, str(e)[:50]))
    else:
        tests.append(("Local FFmpeg", False, f"Not found at {local_ffmpeg}"))

    # Test Python FFmpeg access
    try:
        import subprocess
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        tests.append(("Python→FFmpeg", result.returncode == 0, "Accessible from Python"))
    except Exception as e:
        tests.append(("Python→FFmpeg", False, str(e)[:50]))

    # Display results
    table = Table(title="FFmpeg Tests")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, success, details in tests:
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        table.add_row(name, status, details)

    console.print(table)

    any_ok = any(t[1] for t in tests)
    return any_ok, tests

def test_ollama():
    """Test Ollama connection"""
    console.print("\n[bold cyan]3. Testing Ollama (LLM Backend)...[/bold cyan]")

    tests = []

    try:
        import ollama
        from src.config import Config

        client = ollama.Client(host=Config.OLLAMA_BASE_URL)

        # Test connection
        try:
            models = client.list()
            tests.append(("Ollama Connection", True, f"Connected to {Config.OLLAMA_BASE_URL}"))

            # Check for models
            model_names = [m['name'] for m in models.get('models', [])]
            if model_names:
                tests.append(("Ollama Models", True, f"Found {len(model_names)} model(s)"))

                # Check for recommended model
                if any('gpt-oss' in m for m in model_names):
                    tests.append(("Recommended Model", True, "gpt-oss found"))
                else:
                    tests.append(("Recommended Model", False, f"gpt-oss not found. Available: {', '.join(model_names[:3])}"))
            else:
                tests.append(("Ollama Models", False, "No models installed"))

        except Exception as e:
            tests.append(("Ollama Connection", False, str(e)[:60]))

    except Exception as e:
        tests.append(("Ollama", False, f"Import failed: {str(e)[:50]}"))

    # Display results
    table = Table(title="Ollama Tests")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, success, details in tests:
        status = "[green]✓[/green]" if success else "[yellow]⚠[/yellow]"
        table.add_row(name, status, details)

    console.print(table)

    return len(tests) > 0 and tests[0][1], tests

def test_sample_file():
    """Test that the sample file exists and is accessible"""
    console.print("\n[bold cyan]4. Testing Sample File...[/bold cyan]")

    sample_path = Path(r"C:\Users\Gambit\Documents\Audacity\Sep 19 5m.m4a")
    tests = []

    if sample_path.exists():
        size_mb = sample_path.stat().st_size / (1024 * 1024)
        tests.append(("File Exists", True, str(sample_path)))
        tests.append(("File Size", True, f"{size_mb:.2f} MB"))
        tests.append(("File Readable", sample_path.is_file(), "Regular file"))
    else:
        tests.append(("File Exists", False, f"Not found: {sample_path}"))

    # Display results
    table = Table(title="Sample File Tests")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, success, details in tests:
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        table.add_row(name, status, details)

    console.print(table)

    return len(tests) > 0 and all(t[1] for t in tests), tests

def test_directories():
    """Test that required directories exist"""
    console.print("\n[bold cyan]5. Testing Directories...[/bold cyan]")

    from src.config import Config

    tests = []
    required_dirs = [
        ("Output Dir", Config.OUTPUT_DIR),
        ("Temp Dir", Config.TEMP_DIR),
        ("Logs Dir", Path("logs")),
    ]

    for name, path in required_dirs:
        path = Path(path)
        if path.exists():
            tests.append((name, True, str(path)))
        else:
            try:
                path.mkdir(parents=True, exist_ok=True)
                tests.append((name, True, f"Created: {path}"))
            except Exception as e:
                tests.append((name, False, f"Cannot create: {str(e)[:40]}"))

    # Display results
    table = Table(title="Directory Tests")
    table.add_column("Directory", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, success, details in tests:
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        table.add_row(name, status, details)

    console.print(table)

    return all(t[1] for t in tests), tests

def test_whisper():
    """Test Whisper model loading"""
    console.print("\n[bold cyan]6. Testing Whisper Model...[/bold cyan]")

    tests = []

    try:
        from src.config import Config
        from src.transcriber import Transcriber

        console.print(f"   Loading model: {Config.WHISPER_MODEL} (backend: {Config.WHISPER_BACKEND})")
        console.print("   [dim]This may take a moment on first run...[/dim]")

        transcriber = Transcriber()
        tests.append(("Model Load", True, f"{Config.WHISPER_MODEL} ({Config.WHISPER_BACKEND})"))
        tests.append(("Transcriber Init", True, "Ready"))

    except Exception as e:
        tests.append(("Whisper Model", False, str(e)[:60]))

    # Display results
    table = Table(title="Whisper Model Tests")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, success, details in tests:
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        table.add_row(name, status, details)

    console.print(table)

    return len(tests) > 0 and all(t[1] for t in tests), tests

def main():
    """Run all tests"""
    console.print(Panel.fit(
        "[bold green]VideoChunking System Test Suite[/bold green]\n"
        "Verifying all components before processing",
        border_style="green"
    ))

    results = []

    # Run all tests
    results.append(("Imports", *test_imports()))
    results.append(("FFmpeg", *test_ffmpeg()))
    results.append(("Ollama", *test_ollama()))
    results.append(("Sample File", *test_sample_file()))
    results.append(("Directories", *test_directories()))

    # Whisper test is slow, make it optional
    if "--skip-whisper" not in sys.argv:
        results.append(("Whisper Model", *test_whisper()))
    else:
        console.print("\n[dim]Skipping Whisper model test (use without --skip-whisper to test)[/dim]")

    # Summary
    console.print("\n" + "="*70)
    console.print("[bold cyan]SUMMARY[/bold cyan]")
    console.print("="*70)

    table = Table(title="Overall Results")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, success, details in results:
        status = "[green]✓ PASS[/green]" if success else "[red]✗ FAIL[/red]"
        detail_count = f"{sum(1 for t in details if t[1])}/{len(details)} tests passed"
        table.add_row(name, status, detail_count)

    console.print(table)

    # Overall verdict
    all_critical_pass = all(r[1] for r in results if r[0] in ["Imports", "FFmpeg", "Sample File", "Directories"])
    ollama_pass = any(r[1] for r in results if r[0] == "Ollama")

    console.print("\n" + "="*70)
    if all_critical_pass:
        console.print("[bold green]✓ READY FOR TESTING![/bold green]")
        console.print("\nYou can now process your sample file:")
        console.print("  [cyan]python test_sample.py quick[/cyan]  - Quick transcription test")
        console.print("  [cyan]python test_sample.py[/cyan]        - Full processing test")

        if not ollama_pass:
            console.print("\n[yellow]⚠ Note: Ollama not available - IC/OOC classification will be skipped[/yellow]")
    else:
        console.print("[bold red]✗ SOME CRITICAL COMPONENTS FAILED[/bold red]")
        console.print("\nFix the issues above before processing.")

    console.print("="*70)

    return 0 if all_critical_pass else 1

if __name__ == "__main__":
    sys.exit(main())
