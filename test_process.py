"""Test script to process audio file through the pipeline"""
from pathlib import Path
from src.pipeline import DDSessionProcessor
import time

# File to process
audio_file = Path(r"C:\Users\Gambit\Documents\Audacity\Sep 19 5m.m4a")

print(f"Processing: {audio_file}")
print(f"File exists: {audio_file.exists()}")
print(f"File size: {audio_file.stat().st_size / (1024*1024):.2f} MB")
print("="*80)

# Create processor with default party
processor = DDSessionProcessor(
    session_id="test_sep19_5m",
    num_speakers=4,
    party_id="default"
)

print("\nStarting processing...")
print("Using GPU acceleration for Whisper transcription")
start_time = time.perf_counter()

# Process with all skip options enabled (fastest)
result = processor.process(
    input_file=audio_file,
    skip_diarization=True,
    skip_classification=True,
    skip_snippets=True
)

end_time = time.perf_counter()
elapsed = end_time - start_time

print("="*80)
print(f"✅ Processing complete in {elapsed:.1f} seconds ({elapsed/60:.2f} minutes)")
print("="*80)

# Show results
print("\n📊 Statistics:")
stats = result['statistics']
print(f"  - Total Duration: {stats['total_duration_formatted']}")
print(f"  - Total Segments: {stats['total_segments']}")

print("\n📁 Output Files:")
for key, path in result['output_files'].items():
    print(f"  - {key}: {path}")

print("\n📝 First 500 characters of transcript:")
full_text = result['output_files']['full'].read_text(encoding='utf-8')
print(full_text[:500])
print("...")
