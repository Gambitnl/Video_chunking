"""Test the Gradio UI by simulating user interaction"""
from pathlib import Path
import sys
import io

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import gradio as gr
from gradio_client import Client
import time

def test_ui_processing():
    """Simulate a user processing a file through the Gradio UI"""

    print("="*70)
    print("GRADIO UI TEST - Simulating User Interaction")
    print("="*70)

    # Connect to the running Gradio server
    print("\n1. Connecting to Gradio server at http://127.0.0.1:7860...")
    try:
        client = Client("http://127.0.0.1:7860")
        print("   [OK] Connected to Gradio UI")
    except Exception as e:
        print(f"   [ERROR] Could not connect: {e}")
        return False

    # Prepare the sample file
    sample_file = Path(r"C:\Users\Gambit\Documents\Audacity\Sep 19 5m.m4a")

    print(f"\n2. Checking sample file: {sample_file}")
    if not sample_file.exists():
        print(f"   [ERROR] File not found")
        return False
    print(f"   [OK] File found ({sample_file.stat().st_size / (1024*1024):.2f} MB)")

    # Test with quick mode first (skip all optional processing)
    print("\n3. Configuring processing settings (QUICK MODE):")
    print("   - Session ID: test_ui_5min")
    print("   - Party: default")
    print("   - Number of Speakers: 4")
    print("   - Skip Diarization: YES (faster)")
    print("   - Skip Classification: YES (faster)")
    print("   - Skip Snippets: YES (faster)")

    print("\n4. Submitting file for processing...")
    print("   This will transcribe the audio without extra processing (fastest)")

    try:
        # Call the Gradio endpoint
        # The function signature from app.py is:
        # process_session(audio_file, session_id, party_selection, character_names,
        #                 player_names, num_speakers, skip_diarization,
        #                 skip_classification, skip_snippets)

        # Note: Gradio file input needs proper file handling AND a list
        from gradio_client import handle_file

        result = client.predict(
            audio_file=[handle_file(str(sample_file))],  # Must be a LIST of file handles!
            session_id="test_ui_5min",
            party_selection="default",
            character_names="",
            player_names="",
            num_speakers=4,
            skip_diarization=True,   # Skip for speed
            skip_classification=True, # Skip for speed
            skip_snippets=True,       # Skip for speed
            api_name="/process_session"
        )

        print("\n5. Processing completed!")
        print("="*70)

        # Result is a tuple: (status, full_text, ic_text, ooc_text, stats)
        status, full_text, ic_text, ooc_text, stats = result

        print("\nSTATUS:")
        print(status)

        print("\nTRANSCRIPT PREVIEW (first 500 characters):")
        print("-"*70)
        print(full_text[:500] if full_text else "(empty)")
        if len(full_text) > 500:
            print("...")
        print("-"*70)

        print(f"\nFull transcript length: {len(full_text)} characters")

        if ic_text:
            print(f"IC transcript length: {len(ic_text)} characters")
        if ooc_text:
            print(f"OOC transcript length: {len(ooc_text)} characters")

        if stats:
            print("\nSTATISTICS:")
            print(stats[:500] if len(stats) > 500 else stats)

        print("\n" + "="*70)
        print("OK! File processed through UI successfully!")
        print("="*70)

        return True

    except Exception as e:
        print(f"\n[ERROR] Processing error: {e}")
        print("\nFull error details:")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys

    print("\nNote: This script expects the Gradio app to be running at http://127.0.0.1:7860")
    print("      If not running, start it with: python app.py\n")

    success = test_ui_processing()
    sys.exit(0 if success else 1)
