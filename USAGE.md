# Usage Guide

Detailed guide on using the D&D Session Transcription system.

## Quick Examples

### Web UI (Easiest)

```bash
# Start the web interface
python app.py

# Open browser to: http://127.0.0.1:7860
```

Then:
1. Upload your M4A file
2. Enter session info
3. Click "Process Session"
4. Download results when done

### CLI (Full Control)

```bash
# Basic processing
python cli.py process recording.m4a

# With party configuration (easiest for recurring campaigns)
python cli.py process recording.m4a \
  --party default \
  --session-id "Campaign1_Session05"

# With manual options
python cli.py process recording.m4a \
  --session-id "Campaign1_Session05" \
  --characters "Thorin Ironforge,Elara Moonwhisper,Zyx the Trickster" \
  --players "Alice,Bob,Charlie,DM Dave" \
  --num-speakers 4 \
  --output-dir ./my_transcripts
```

## Understanding the Output

After processing, you'll get 4 files:

### 1. Full Transcript (`*_full.txt`)

Complete transcript with all content labeled:

```
================================================================================
D&D SESSION TRANSCRIPT - FULL VERSION
================================================================================

[00:15:23] SPEAKER_00 (IC): Je betreedt een donkere grot. De muren druipen van het vocht.
[00:15:45] SPEAKER_01 as Thorin (IC): Ik steek mijn fakkel aan en kijk om me heen.
[00:16:02] SPEAKER_02 (OOC): Haha, alweer een grot! Hoeveel grotten zijn dit nu al?
[00:16:15] SPEAKER_00 (OOC): Geen idee, ik ben de tel kwijt.
[00:16:30] SPEAKER_00 (IC): Je ziet in het licht van de fakkel oude runen op de muur.
```

**Use this for**: Complete session record, finding when something was discussed

### 2. IC-Only Transcript (`*_ic_only.txt`)

Game narrative only, no meta-discussion:

```
================================================================================
D&D SESSION TRANSCRIPT - IN-CHARACTER ONLY
================================================================================

[00:15:23] DM: Je betreedt een donkere grot. De muren druipen van het vocht.
[00:15:45] Thorin: Ik steek mijn fakkel aan en kijk om me heen.
[00:16:30] DM: Je ziet in het licht van de fakkel oude runen op de muur.
```

**Use this for**: Session notes, campaign journal, sharing story highlights

### 3. OOC-Only Transcript (`*_ooc_only.txt`)

Meta-discussion, jokes, and banter:

```
================================================================================
D&D SESSION TRANSCRIPT - OUT-OF-CHARACTER ONLY
================================================================================

[00:16:02] Bob: Haha, alweer een grot! Hoeveel grotten zijn dit nu al?
[00:16:15] DM Dave: Geen idee, ik ben de tel kwijt.
```

**Use this for**: Remembering funny moments, tracking rules discussions

### 4. JSON Data (`*_data.json`)

Complete structured data for further processing:

```json
{
  "metadata": {
    "session_id": "Campaign1_Session05",
    "character_names": ["Thorin", "Elara", "Zyx"],
    "statistics": {
      "total_duration_formatted": "04:15:32",
      "ic_percentage": 67.5,
      "character_appearances": {
        "Thorin": 145,
        "Elara": 132,
        "Zyx": 98
      }
    }
  },
  "segments": [
    {
      "start_time": 923.45,
      "end_time": 928.12,
      "text": "Je betreedt een donkere grot.",
      "speaker_id": "SPEAKER_00",
      "speaker_name": "DM Dave",
      "classification": "IC",
      "classification_confidence": 0.98,
      "character": null
    }
  ]
}
```

**Use this for**: Custom analysis, building other tools, statistics

### 5. Session Notebook (Coming Soon)

Transform your IC-only transcript into different narrative perspectives:

**Character POV**: Experience the session from a specific character's perspective
```
I entered the dark cave, my torch flickering in the damp air. The walls dripped
with moisture. As I raised my torch higher, ancient runes became visible on the stone.

My companion Elara spoke up: "These runes look Dwarven..."
```

**Third-Person Narrator**: Read the session as a fantasy novel
```
Thorin entered the dark cave, his torch flickering in the damp air. The walls
dripped with moisture. As he raised his torch higher, ancient runes became
visible on the stone.

Elara examined the markings carefully. "These runes look Dwarven," she observed.
```

_Note: This feature will use the LLM to transform the IC-only transcript into readable narrative formats. The original transcripts remain unchanged._

## Using Party Configurations

Party configurations make it easy to reuse character and player information across multiple sessions.

### View Available Parties

```bash
# List all configured parties
python cli.py list-parties

# Show details of a specific party
python cli.py show-party default
```

### Using Party Config in Processing

**Web UI**: Simply select your party from the "Party Configuration" dropdown instead of manually entering character/player names.

**CLI**:
```bash
# Process with party config
python cli.py process recording.m4a --party default --session-id "session1"
```

### Creating Custom Parties

Party configurations are stored in `models/parties.json`. The default party "The Broken Seekers" includes:
- **Sha'ek Mindfa'ek** (Cleric) - played by Player1
- **Pipira Shimmerlock** (Wizard) - played by Player2
- **Fan'nar Khe'Lek** (Ranger) - played by Player3
- **Furnax** (Frost Hellhound companion)

To create your own party configuration, edit `models/parties.json` following the same structure, or use the Python API:

```python
from src.party_config import PartyConfigManager, Party, Character

manager = PartyConfigManager()

# Create a new party
my_party = Party(
    party_name="The Dragon Slayers",
    dm_name="DM Mike",
    campaign="Lost Mines",
    characters=[
        Character(
            name="Gandor the Brave",
            player="Sarah",
            race="Human",
            class_name="Fighter",
            aliases=["Gandor"]
        ),
        # Add more characters...
    ]
)

# Save it
manager.add_party("dragon_slayers", my_party)
```

### Benefits of Party Configs

1. **Consistency**: Same character/player names across all sessions
2. **Less typing**: No need to manually enter names each time
3. **Better classification**: Character descriptions and aliases help the IC/OOC classifier
4. **Character context**: Rich descriptions improve LLM understanding

## Workflow: First Session

### Step 1: Process with Default Settings

```bash
python cli.py process session1.m4a --session-id "session1"
```

This creates output with speaker IDs like `SPEAKER_00`, `SPEAKER_01`, etc.

### Step 2: Identify Speakers

Open the full transcript and figure out who is who:

- `SPEAKER_00` = Sounds like the DM (lots of narration)
- `SPEAKER_01` = Mentions "Thorin" often (probably Alice)
- `SPEAKER_02` = Different voice (probably Bob)
- `SPEAKER_03` = Another distinct voice (probably Charlie)

### Step 3: Map Speakers

```bash
# Map each speaker ID to a real person
python cli.py map-speaker session1 SPEAKER_00 "DM Dave"
python cli.py map-speaker session1 SPEAKER_01 "Alice"
python cli.py map-speaker session1 SPEAKER_02 "Bob"
python cli.py map-speaker session1 SPEAKER_03 "Charlie"
```

### Step 4: Verify Mappings

```bash
python cli.py show-speakers session1
```

### Step 5: Reprocess with Names

```bash
python cli.py process session1.m4a \
  --session-id "session1" \
  --characters "Thorin,Elara,Zyx" \
  --players "Alice,Bob,Charlie,DM Dave"
```

Now the output will use the names you specified!

## Advanced Usage

### Processing Long Sessions

For very long sessions (6+ hours):

1. **Split the audio first** (optional):
   ```bash
   # Use Audacity or ffmpeg to split into 2-hour chunks
   ffmpeg -i long_session.m4a -t 7200 -c copy part1.m4a
   ffmpeg -i long_session.m4a -ss 7200 -t 7200 -c copy part2.m4a
   ```

2. **Process each part**:
   ```bash
   python cli.py process part1.m4a --session-id "session1_part1"
   python cli.py process part2.m4a --session-id "session1_part2"
   ```

3. **Combine manually** or use the JSON outputs

### Faster Processing (Skip Optional Steps)

```bash
# Skip both diarization and classification for 2-3x speed
python cli.py process session.m4a \
  --skip-diarization \
  --skip-classification
```

You'll still get transcription, just without:
- Speaker labels (everyone will be "UNKNOWN")
- IC/OOC separation (everything will be marked IC)

### Using Groq API for Speed

If you have a Groq API key (free tier available):

1. **Add to `.env`**:
   ```
   GROQ_API_KEY=your_key_here
   WHISPER_BACKEND=groq
   ```

2. **Process as normal**:
   ```bash
   python cli.py process session.m4a
   ```

This can reduce transcription time from hours to minutes!

### Batch Processing

Process multiple sessions:

```bash
# Create a simple batch script (Windows)
for %%f in (*.m4a) do (
  python cli.py process "%%f" --session-id "%%~nf"
)

# Or bash script (Linux/Mac)
for file in *.m4a; do
  python cli.py process "$file" --session-id "${file%.m4a}"
done
```

## Tips & Best Practices

### Improving Transcription Accuracy

1. **Audio Quality**:
   - Place recorder as close to center of group as possible
   - Minimize background noise
   - Use better microphone if possible

2. **Specify Language**:
   - The system already uses Dutch (`nl`)
   - This significantly improves accuracy

3. **Character Names**:
   - Provide character names to help classification
   - Use full names if they're distinctive

### Improving Speaker Diarization

1. **Consistent Setup**:
   - Use same recording device and position each session
   - Helps system learn speaker profiles over time

2. **Num Speakers**:
   - Set `--num-speakers` accurately
   - Too many = false splits
   - Too few = speakers merged together

3. **Manual Correction**:
   - First session: identify speakers manually
   - Map them using `map-speaker`
   - Future sessions will be more accurate

### Improving IC/OOC Classification

1. **Provide Context**:
   - List character names: helps identify IC speech
   - List player names: helps identify OOC references

2. **Review and Learn**:
   - Check the classification results
   - Note patterns the LLM might miss
   - Future versions can learn from corrections

3. **Confidence Scores**:
   - Check `classification_confidence` in JSON
   - Low confidence (<0.6) = might be wrong
   - Manually verify low-confidence segments

## Understanding Statistics

The system generates useful stats:

```
Session Statistics:
  Total Duration: 04:15:32
  IC Duration: 02:52:15 (67.5%)
  Total Segments: 1,247
  IC Segments: 842
  OOC Segments: 405

  Character Appearances:
    - Thorin: 145
    - Elara: 132
    - Zyx: 98
```

**Insights**:
- **IC Percentage**: How much was actual gameplay vs banter
- **Character Appearances**: Who talked the most (useful for spotlight balance)
- **OOC Segments**: Lots of OOC might indicate confusion or off-topic discussion

## Troubleshooting Results

### "Speaker diarization seems wrong"

**Problem**: SPEAKER_00 is sometimes Alice, sometimes Bob

**Solutions**:
1. Check if voices are similar (hard to distinguish)
2. Increase `--num-speakers` if people are being merged
3. Decrease `--num-speakers` if one person is split
4. Accept some errors (no system is perfect)

### "IC/OOC classification is backwards"

**Problem**: Obvious IC content marked as OOC

**Possible causes**:
1. Segment is ambiguous (truly could be either)
2. LLM misunderstood context
3. Need better few-shot examples

**Solutions**:
1. Check confidence score (might be low)
2. Use the full transcript (has both)
3. Manually filter the JSON if needed

### "Characters not detected"

**Problem**: `character: null` even for obvious IC speech

**Causes**:
1. Character names not provided
2. Characters never mentioned by name
3. DM narration (no character)

**Solutions**:
- Always provide `--characters` list
- In JSON, use speaker + classification instead

### "Processing too slow"

**Solutions** (in order of impact):
1. Use Groq API (`WHISPER_BACKEND=groq`)
2. Get a GPU for local processing
3. Skip diarization (`--skip-diarization`)
4. Skip classification (`--skip-classification`)
5. Process shorter sessions

## Example: Full Workflow

Here's a complete example from start to finish:

```bash
# 1. Initial processing
python cli.py process "Campaign1_Session05.m4a" \
  --session-id "C1S05" \
  --characters "Thorin,Elara,Zyx" \
  --players "Alice,Bob,Charlie,DM" \
  --num-speakers 4

# 2. Check output
cat output/C1S05_full.txt | head -50

# 3. Identify speakers from output
#    SPEAKER_00 = DM (lots of narration)
#    SPEAKER_01 = Alice (mentions Thorin)
#    SPEAKER_02 = Bob (mentions Elara)
#    SPEAKER_03 = Charlie (mentions Zyx)

# 4. Map speakers
python cli.py map-speaker C1S05 SPEAKER_00 "DM"
python cli.py map-speaker C1S05 SPEAKER_01 "Alice"
python cli.py map-speaker C1S05 SPEAKER_02 "Bob"
python cli.py map-speaker C1S05 SPEAKER_03 "Charlie"

# 5. Verify
python cli.py show-speakers C1S05

# 6. Reprocess with correct names (or just use the files as-is)
#    Speaker mappings are now saved for future sessions!

# 7. Review results
#    - IC-only for session notes
#    - Full transcript for complete record
#    - JSON for statistics
```

## Next Steps

- Try processing a short test session first (10-15 minutes)
- Review outputs and verify quality
- Adjust settings in `.env` if needed
- Process full sessions once satisfied
- Build a library of transcribed sessions!

## Questions?

- Check [SETUP.md](SETUP.md) for installation issues
- Check [README.md](README.md) for project overview
- Review the Help tab in the web UI
