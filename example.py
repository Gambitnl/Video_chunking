"""
Example script demonstrating how to use the D&D Session Processor programmatically.

This shows how to integrate the processing pipeline into your own Python code.
"""

from pathlib import Path
from src.pipeline import DDSessionProcessor
from src.config import Config


def example_basic_processing():
    """
    Example 1: Basic processing with minimal configuration
    """
    print("=" * 80)
    print("Example 1: Basic Processing")
    print("=" * 80)

    # Create processor
    processor = DDSessionProcessor(
        session_id="example_session_1",
        num_speakers=4
    )

    # Process audio file
    # (Replace with your actual audio file path)
    input_file = Path("path/to/your/session.m4a")

    if not input_file.exists():
        print(f"⚠ File not found: {input_file}")
        print("   Please update the path in this example script.")
        return

    result = processor.process(
        input_file=input_file,
        output_dir=Config.OUTPUT_DIR
    )

    print(f"\n✓ Processing complete!")
    print(f"  Output files: {result['output_files']}")
    print(f"  Statistics: {result['statistics']}")


def example_with_character_info():
    """
    Example 2: Processing with character and player information
    """
    print("\n" + "=" * 80)
    print("Example 2: Processing with Character Information")
    print("=" * 80)

    # Define your campaign details
    character_names = [
        "Thorin Ironforge",
        "Elara Moonwhisper",
        "Zyx the Trickster"
    ]

    player_names = [
        "Alice",
        "Bob",
        "Charlie",
        "DM Dave"
    ]

    # Create processor with campaign info
    processor = DDSessionProcessor(
        session_id="campaign1_session05",
        character_names=character_names,
        player_names=player_names,
        num_speakers=4
    )

    # Process
    input_file = Path("path/to/your/session.m4a")

    if not input_file.exists():
        print(f"⚠ File not found: {input_file}")
        return

    result = processor.process(
        input_file=input_file,
        output_dir=Path("./my_campaign_transcripts")
    )

    # Access results
    stats = result['statistics']
    print(f"\nSession Statistics:")
    print(f"  Duration: {stats['total_duration_formatted']}")
    print(f"  IC Content: {stats['ic_percentage']:.1f}%")
    print(f"  Character Appearances:")
    for char, count in stats['character_appearances'].items():
        print(f"    - {char}: {count} times")


def example_fast_processing():
    """
    Example 3: Fast processing (skip optional stages)
    """
    print("\n" + "=" * 80)
    print("Example 3: Fast Processing (Skip Optional Stages)")
    print("=" * 80)

    processor = DDSessionProcessor(
        session_id="quick_test",
        num_speakers=4
    )

    input_file = Path("path/to/your/session.m4a")

    if not input_file.exists():
        print(f"⚠ File not found: {input_file}")
        return

    # Skip diarization and classification for speed
    result = processor.process(
        input_file=input_file,
        skip_diarization=True,  # 2-3x faster
        skip_classification=True  # 2-3x faster
    )

    print(f"\n✓ Fast processing complete!")
    print(f"  (No speaker labels or IC/OOC separation)")


def example_speaker_mapping():
    """
    Example 4: Managing speaker profiles
    """
    print("\n" + "=" * 80)
    print("Example 4: Speaker Profile Management")
    print("=" * 80)

    processor = DDSessionProcessor(
        session_id="session_with_mapping",
        num_speakers=4
    )

    # After processing, map speaker IDs to real names
    processor.update_speaker_mapping("SPEAKER_00", "DM Dave")
    processor.update_speaker_mapping("SPEAKER_01", "Alice")
    processor.update_speaker_mapping("SPEAKER_02", "Bob")
    processor.update_speaker_mapping("SPEAKER_03", "Charlie")

    print("\n✓ Speaker mappings saved!")
    print("  These will be used in future sessions automatically.")


def example_reading_json_output():
    """
    Example 5: Reading and processing JSON output
    """
    print("\n" + "=" * 80)
    print("Example 5: Reading JSON Output")
    print("=" * 80)

    import json

    # Path to a previously generated JSON file
    json_file = Config.OUTPUT_DIR / "example_session_1_data.json"

    if not json_file.exists():
        print(f"⚠ JSON file not found: {json_file}")
        print("   Process a session first to generate output.")
        return

    # Load JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Access metadata
    metadata = data['metadata']
    print(f"\nSession: {metadata['session_id']}")
    print(f"Characters: {', '.join(metadata.get('character_names', []))}")

    # Access segments
    segments = data['segments']
    print(f"\nTotal segments: {len(segments)}")

    # Filter for IC content
    ic_segments = [s for s in segments if s['classification'] == 'IC']
    print(f"IC segments: {len(ic_segments)}")

    # Find all mentions of a character
    character_name = "Thorin"
    mentions = [
        s for s in segments
        if character_name.lower() in s['text'].lower()
    ]
    print(f"\nSegments mentioning '{character_name}': {len(mentions)}")

    # Show first few
    print(f"\nFirst 3 mentions:")
    for seg in mentions[:3]:
        print(f"  [{seg['start_time']:.1f}s] {seg['text'][:60]}...")


def example_custom_output():
    """
    Example 6: Creating custom output format
    """
    print("\n" + "=" * 80)
    print("Example 6: Custom Output Format")
    print("=" * 80)

    import json
    from datetime import timedelta

    json_file = Config.OUTPUT_DIR / "example_session_1_data.json"

    if not json_file.exists():
        print(f"⚠ JSON file not found: {json_file}")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create a custom format: Character dialogue only, formatted for story
    output = []
    output.append("# Campaign Story - IC Dialogue Only\n")

    current_speaker = None
    for segment in data['segments']:
        if segment['classification'] != 'IC':
            continue

        speaker = segment.get('speaker_name') or segment.get('character') or 'Unknown'
        text = segment['text']

        # Group consecutive dialogue from same speaker
        if speaker != current_speaker:
            output.append(f"\n**{speaker}**: {text}")
            current_speaker = speaker
        else:
            output.append(f" {text}")

    # Save custom format
    custom_file = Config.OUTPUT_DIR / "custom_story_format.md"
    custom_file.write_text('\n'.join(output), encoding='utf-8')

    print(f"✓ Custom format saved to: {custom_file}")


if __name__ == "__main__":
    print("""
    D&D Session Processor - Examples

    This script demonstrates various ways to use the processor.

    NOTE: Update the file paths in each example before running!
    """)

    # Run examples
    # Uncomment the ones you want to try:

    # example_basic_processing()
    # example_with_character_info()
    # example_fast_processing()
    # example_speaker_mapping()
    # example_reading_json_output()
    # example_custom_output()

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)
