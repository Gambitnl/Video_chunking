"""Quick test script for the 5-minute sample file"""
import pytest
from pathlib import Path
from src.pipeline import DDSessionProcessor
from src.config import Config
from src.logger import get_log_file_path

@pytest.mark.slow
def test_sample_file():
    """Test the 5-minute sample file with minimal processing"""

    # Sample file location
    sample_file = Path(r"C:\Users\Gambit\Documents\Audacity\Sep 19 5m.m4a")

    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        return

    print(f"✓ Found sample file: {sample_file}")
    print(f"  Size: {sample_file.stat().st_size / (1024*1024):.2f} MB")

    # Create processor with minimal config
    print("\n🔧 Creating processor...")
    processor = DDSessionProcessor(
        session_id="test_5min",
        num_speakers=4  # Default guess
    )

    print("\n🚀 Starting processing...")
    print("   This will:")
    print("   1. Extract audio (if needed)")
    print("   2. Transcribe using Whisper")
    print("   3. Identify speakers (diarization)")
    print("   4. Classify IC/OOC content")
    print("   5. Export results\n")

    try:
        result = processor.process(
            input_file=sample_file,
            skip_diarization=False,  # Try with diarization
            skip_classification=False,  # Try with classification
            skip_snippets=True  # Skip snippets for speed
        )

        print("\n✅ SUCCESS! Processing completed!")
        print(f"\n📊 Statistics:")
        stats = result['statistics']
        print(f"   - Total Duration: {stats['total_duration_formatted']}")
        print(f"   - IC Duration: {stats['ic_duration_formatted']} ({stats['ic_percentage']:.1f}%)")
        print(f"   - Total Segments: {stats['total_segments']}")
        print(f"   - IC Segments: {stats['ic_segments']}")
        print(f"   - OOC Segments: {stats['ooc_segments']}")

        print(f"\n📁 Output files:")
        output_files = result['output_files']
        for key, path in output_files.items():
            print(f"   - {key}: {path}")

        print(f"\n📝 Log file: {get_log_file_path()}")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        print(f"\n📝 Check log for details: {get_log_file_path()}")
        import traceback
        traceback.print_exc()

@pytest.mark.slow
def test_sample_quick():
    """Quick test with all optional processing skipped"""

    sample_file = Path(r"C:\Users\Gambit\Documents\Audacity\Sep 19 5m.m4a")

    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        return

    print(f"✓ Found sample file: {sample_file}")
    print(f"  Size: {sample_file.stat().st_size / (1024*1024):.2f} MB")

    print("\n🔧 Creating processor (QUICK MODE - transcription only)...")
    processor = DDSessionProcessor(
        session_id="test_5min_quick",
        num_speakers=4
    )

    print("\n🚀 Starting quick processing (transcription only)...")

    try:
        result = processor.process(
            input_file=sample_file,
            skip_diarization=True,  # Skip for speed
            skip_classification=True,  # Skip for speed
            skip_snippets=True  # Skip for speed
        )

        print("\n✅ SUCCESS! Quick processing completed!")
        print(f"\n📁 Output files:")
        output_files = result['output_files']
        for key, path in output_files.items():
            if path.exists():
                print(f"   - {key}: {path}")

        # Show a preview of the transcript
        full_transcript_path = output_files['full']
        if full_transcript_path.exists():
            print(f"\n📄 Transcript preview (first 500 chars):")
            print("-" * 60)
            transcript = full_transcript_path.read_text(encoding='utf-8')
            print(transcript[:500])
            if len(transcript) > 500:
                print("...")
            print("-" * 60)

        print(f"\n📝 Log file: {get_log_file_path()}")

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        print(f"\n📝 Check log for details: {get_log_file_path()}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        print("=" * 70)
        print("QUICK TEST MODE - Transcription Only (Fastest)")
        print("=" * 70)
        test_sample_quick()
    else:
        print("=" * 70)
        print("FULL TEST MODE - All Features")
        print("=" * 70)
        print("\nTip: Run 'python test_sample.py quick' for faster transcription-only test")
        print("=" * 70)
        test_sample_file()
