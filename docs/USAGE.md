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

## Campaign Launcher (Web UI)

- Start the Gradio app with `python app.py`.
- Use the **Campaign Launcher** heading at the top of the UI to load an existing campaign or create a new one.
- The launcher shows a manifest summarising party linkage, knowledge files, processed sessions, and outstanding gaps.
- Once loaded, every tab (Process Session, Campaign, Characters, Stories, Settings) updates automatically to reflect the active campaign context.

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

After processing, each session is saved in its own **timestamped folder**:

```
output/
  └── YYYYMMDD_HHMMSS_session_id/
      ├── session_id_full.txt
      ├── session_id_ic_only.txt
      ├── session_id_ooc_only.txt
      ├── session_id_data.json
      ├── session_id_full.srt
      ├── session_id_ic_only.srt
      └── session_id_ooc_only.srt
```

**Example**: Processing a session with ID "session1" on October 19, 2025 at 7:47 PM creates:
```
output/20251019_194750_session1/
```

This keeps each session organized and prevents files from different sessions getting mixed together.

### Output Files

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

### 5. Session Narratives (`narratives/`)

Transform your IC-only transcript into readable story formats using the **Story Notebooks** tab in the Web UI.

**Narrator Summary** (`*_narrator.md`): Third-person omniscient overview
```
The party ventured into the dark cave, their footsteps echoing off damp stone walls.
Thorin raised his torch high, illuminating ancient Dwarven runes carved deep into
the rock face.

"These markings are old," Elara observed, tracing the symbols with her fingers.
"Very old..."
```

**Character Perspective** (`*_{character}.md`): First-person narrative from a PC's viewpoint
```
I entered the cave cautiously, my torch casting flickering shadows on the wet walls.
The air was thick and cold. As I held my light higher, I noticed strange symbols
carved into the stone.

Elara stepped closer to examine them. "These runes are Dwarven," she said.
```

**How to Generate**: See the "Creating Session Narratives" section below.

_Note: This feature uses your local LLM to transform the IC-only transcript into readable narrative formats. The original transcripts remain unchanged._

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

You can skip any of the three optional processing stages to save time:

#### Skip Speaker Diarization (`--skip-diarization`)
Skip identifying who is speaking. **~30% time saved**, but all speakers labeled as 'UNKNOWN'.

**Pros**: Faster, no HuggingFace token needed
**Cons**: Can't tell who said what
**When to use**: Quick transcription, single speaker, or when you don't care who's talking

```bash
python cli.py process session.m4a --skip-diarization
```

#### Skip IC/OOC Classification (`--skip-classification`)
Skip separating in-character dialogue from out-of-character banter. **~20% time saved**, but no IC/OOC filtering (all content labeled as IC).

**Pros**: Faster, no LLM needed
**Cons**: Can't filter out OOC banter
**When to use**: Sessions with minimal OOC content, or when you want everything

```bash
python cli.py process session.m4a --skip-classification
```

#### Skip Audio Snippets (`--skip-snippets`)
Skip exporting individual WAV files for each dialogue segment. **~10% time saved**, saves disk space.

**Pros**: Faster, much less disk space used
**Cons**: No individual audio clips per segment
**When to use**: You only need transcripts, not audio segments

```bash
python cli.py process session.m4a --skip-snippets
```

#### Skip Everything (Maximum Speed)
```bash
# Skip all optional processing for 2-3x speed
python cli.py process session.m4a \
  --skip-diarization \
  --skip-classification \
  --skip-snippets
```

You'll still get transcription with timestamps, just without speaker labels, IC/OOC filtering, or audio segments.

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
5. Skip audio snippets (`--skip-snippets`)
6. Process shorter sessions

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

## LLM Chat

The Web UI includes a powerful "LLM Chat" tab that allows you to interact directly with the locally configured language model (e.g., Ollama). You can use this for general queries or to role-play as one of your campaign characters.

### Features

- **Direct LLM Access**: Chat directly with the model.
- **Character Role-Playing**: Select a character from the dropdown to have the LLM adopt their personality, description, and backstory.
- **Session-Based History**: The chat remembers your conversation within the current session.
- **Clear Chat**: A button to easily reset the conversation.

### How to Use

1.  Navigate to the **LLM Chat** tab in the web UI.
2.  To have a general conversation, simply type your message in the "Your Message" box and press Enter.
3.  To chat as a character:
    - Select a character from the **Chat as Character** dropdown menu.
    - The chat history will automatically clear.
    - Type your message. The LLM will now respond from the perspective of the selected character.
4.  Click the **Clear Chat** button at any time to start a new conversation.

**Note on Chat History**: The chat history is stored in-memory for the duration of your browser session. If you close or refresh the application, the chat history will be lost. It is not saved to a file.

## Campaign Dashboard

The **Campaign Dashboard** tab provides a comprehensive health check of all components tied to your selected campaign.

### Features

- **Campaign Health Percentage**: 0-100% with color-coded indicator (🟢🟡🟠🔴)
- **Visual Status Indicators**: ✅ (configured), ⚠️ (needs attention), ❌ (missing)
- **Component Tracking**: 6 key areas monitored
- **Actionable Next Steps**: Specific recommendations for missing components

### Components Monitored

1. **Party Configuration**: `models/parties/{campaign}_party.json`
2. **Processing Settings**: Campaign-specific settings in party config
3. **Knowledge Base**: `models/knowledge/{campaign}_knowledge.json`
4. **Character Profiles**: `models/character_profiles/{campaign}_*.json`
5. **Processed Sessions**: `output/{campaign}_Session_*/`
6. **Session Narratives**: `output/{campaign}_Session_*/narratives/`

### How to Use

1. **Select a campaign** on the "Process Session" tab
2. **Go to "Campaign Dashboard" tab**
3. **Click "Refresh Campaign Info"** to update the dashboard
4. **Review status indicators** to see what's configured
5. **Follow "Next Steps"** to fix missing components

### Health Indicators

- 🟢 **90-100%**: Excellent - Everything configured
- 🟡 **70-89%**: Good - Most components ready
- 🟠 **50-69%**: Needs Attention - Several missing
- 🔴 **0-49%**: Critical - Major setup needed

See **[CAMPAIGN_DASHBOARD.md](CAMPAIGN_DASHBOARD.md)** for complete documentation.

## Campaign Library (Knowledge Base)

The **Campaign Library** tab displays all campaign knowledge automatically extracted from your sessions.

### What Gets Tracked

- 🎯 **Quests**: Active, completed, and failed missions
- 👥 **NPCs**: Characters met, their roles, and relationships
- 🔓 **Plot Hooks**: Unresolved mysteries and foreshadowing
- 📍 **Locations**: Places visited and their descriptions
- ⚡ **Items**: Important artifacts and equipment

### How It Works

1. **Automatic Extraction**: After processing each session, the LLM analyzes the IC-only transcript
2. **Entity Identification**: Quests, NPCs, locations, items, and plot hooks are detected
3. **Knowledge Merging**: New information merges with existing campaign knowledge
4. **Smart Updates**: Existing entities are updated, new ones are added

### Accessing the Knowledge Base

**Web UI**:
1. Go to **"Campaign Library"** tab
2. Select your campaign from the dropdown
3. Click **"Load Knowledge Base"**
4. Browse entities by category or search across all

**File Location**: `models/knowledge/{campaign}_knowledge.json`

### Disabling Knowledge Extraction

If you don't want automatic knowledge extraction:

**Web UI**: Uncheck "Skip Campaign Knowledge Extraction" checkbox when processing

**CLI**: Add `--skip-knowledge` flag (not yet implemented)

See **[CAMPAIGN_KNOWLEDGE_BASE.md](CAMPAIGN_KNOWLEDGE_BASE.md)** for complete documentation.

## Import Session Notes (Backfilling)

The **Import Session Notes** tab allows you to import written notes from early sessions (before you started recording).

### Use Case

Don't have recordings of sessions 1-5? Import your written notes to:
- Extract campaign knowledge (quests, NPCs, locations, etc.)
- Generate narrative summaries
- Create a complete session timeline
- Build character profiles from early sessions

### How to Import

1. **Go to "Import Session Notes" tab**
2. **Enter Session ID**: e.g., "Session_01", "Session_02"
3. **Select Campaign**: Choose from dropdown
4. **Provide Notes**: Paste text or upload `.txt`/`.md` file
5. **Enable Options**:
   - ✅ **Extract Knowledge**: Add entities to knowledge base
   - ✅ **Generate Narrative**: Create story summary
6. **Click "Import Session Notes"**

### Example Notes Format

```markdown
Session 1 - The Adventure Begins

The party met at the Broken Compass tavern in Neverwinter. Guard Captain
Thorne approached them with a quest: find Marcus, a merchant who disappeared
on the Waterdeep Road three days ago.

NPCs Met:
- Guard Captain Thorne (stern but fair, quest giver)
- Innkeeper Mara (friendly, provided rumors)

Locations:
- The Broken Compass (tavern in Neverwinter)
- Waterdeep Road (where Marcus vanished)

Quests Started:
- Find Marcus the Missing Merchant (active)

The party set out at dawn, following the road north...
```

### Generated Files

- **Knowledge Base**: Updated with extracted entities
- **Narrative** (if enabled): `output/imported_narratives/{session_id}_narrator.md`

See **[CAMPAIGN_KNOWLEDGE_BASE.md](CAMPAIGN_KNOWLEDGE_BASE.md)** for complete documentation.

## Monitoring & Diagnostics
- Open the Gradio UI and switch to the **Diagnostics** tab to list pytest suites (`Discover Tests`) and run individual nodes or the entire suite without leaving the browser.
- Keep `app_manager.py` running: the manager now surfaces every option the session was launched with, tracks stage start/end timestamps, and refreshes automatically so you can watch progress in real time.
- Use the **Recent Events** list in the manager to confirm which stage completed last and what will run next (helpful when processing multi-hour sessions).
## Creating Session Narratives
1. Paste your shared Google Doc URL into the **Document Viewer** tab and click *Fetch* to populate the campaign notebook context.
2. Switch to **Story Notebooks**, pick a processed session, and adjust the creativity slider to control how closely the prose mirrors the transcript.
3. Generate the narrator overview, then choose individual characters to produce first-person recaps; each result is saved to `output/<session>/narratives/` for easy revisiting.
- The manager now differentiates between "idle" and "active" states: if the processor isn't listening on port 7860 you'll see an idle summary with the most recent session ID, and detailed stage progress appears only once a session is running.

## MCP Agent Workflows (Planned)
- LangChain agent orchestrates pipeline tools for context-aware processing.
- LlamaIndex stores transcripts & knowledge, powering retrieval/Q&A.
- Backend selection (OpenAI/Ollama) configurable via `.env`.
- CLI/Gradio extensions will expose agent-driven commands.


