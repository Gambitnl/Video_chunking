"""Create a Colab classification job from existing Stage 5 output"""
import json
import time
import uuid
from pathlib import Path

# Paths
stage5_file = Path("output/20251115_184757_test_s6_nov15_1847pm/intermediates/stage_5_diarization.json")
prompt_file = Path("src/prompts/classifier_prompt_nl.txt")

# Load stage 5 output
print(f"Loading segments from {stage5_file}...")
with open(stage5_file, 'r', encoding='utf-8') as f:
    stage5_data = json.load(f)

segments = stage5_data['segments']
print(f"Found {len(segments)} segments")

# Load prompt template
with open(prompt_file, 'r', encoding='utf-8') as f:
    prompt_template = f.read()

# Character and player names (from Team OP config)
character_names = ["Brinn", "Cassandra", "Nyx", "Theron"]
player_names = ["Gambit", "Seraph", "Luna", "Phoenix"]

# Generate unique job ID
job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:8]}"

# Create job data
job_data = {
    "job_id": job_id,
    "segments": segments,
    "character_names": character_names,
    "player_names": player_names,
    "prompt_template": prompt_template,
}

# Write job file to current directory (user can move it manually)
output_file = Path(f"{job_id}.json")
print(f"\nCreating job file: {output_file}")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(job_data, f, indent=2, ensure_ascii=False)

print(f"✓ Job file created successfully!")
print(f"\nNext steps:")
print(f"1. Move this file to your Google Drive folder:")
print(f"   Google Drive/VideoChunking/classification_pending/{job_id}.json")
print(f"2. Start your Colab notebook (colab_classification_worker.ipynb)")
print(f"3. The Colab worker will process it and write results to:")
print(f"   Google Drive/VideoChunking/classification_complete/{job_id}_result.json")
print(f"\nJob ID: {job_id}")
print(f"Segments to classify: {len(segments)}")
