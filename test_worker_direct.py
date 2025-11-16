"""Test the worker detection logic directly"""
from pathlib import Path

pending_dir = Path(r"G:\My Drive\VideoChunking\classification_pending")
complete_dir = Path(r"G:\My Drive\VideoChunking\classification_complete")

print(f"Pending dir exists: {pending_dir.exists()}")
print(f"Pending dir: {pending_dir}")

job_files = list(pending_dir.glob("job_*.json"))
print(f"\nFound {len(job_files)} job files:")
for f in job_files:
    print(f"  - {f.name} ({f.stat().st_size} bytes)")

# Test if we can read one
if job_files:
    import json
    test_file = job_files[0]
    print(f"\nTrying to read: {test_file.name}")
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  ✓ Successfully loaded")
        print(f"  Job ID: {data.get('job_id')}")
        print(f"  Segments: {len(data.get('segments', []))}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
