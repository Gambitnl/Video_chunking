# Session Notebook Guide

**Status**: ✅ Implemented

Transform your D&D session transcripts into readable narrative formats from different perspectives.

## Overview

The Session Notebook feature takes your IC-only transcript and rewrites it as:
- **Third-Person Narrator**: Traditional fantasy novel style with objective narration
- **Character POV**: First-person narrative from a specific character's perspective

## How to Use (Web UI)

### Accessing Story Notebooks

1. **Open the Web UI**: Run `python app.py` and navigate to the "Story Notebooks" tab
2. **Select a Session**: Choose a processed session from the dropdown at the top
   - Click "Refresh Sessions" if you don't see your session listed
3. **Adjust Creativity Slider**: Control the narrative style
   - **0.1-0.4**: Faithful retelling, stays close to transcript
   - **0.5**: Balanced (recommended)
   - **0.6-1.0**: More dramatic flair and narrative embellishment

### Generate Narrator Summary

Click **"Generate Narrator Summary"** to create an omniscient third-person overview of the entire session. This perspective:
- Describes events objectively from a DM/narrator viewpoint
- Includes all party members' actions
- Provides scene-setting and atmosphere
- Saves to `output/<session>/narratives/<session>_narrator.md`

### Generate Character Narratives

1. **Select a Character**: Choose which PC's perspective to write from
2. **Click "Generate Character Narrative"**: Creates a first-person recap from that character's eyes
   - Filters events to what that character experienced
   - Uses first-person voice ("I entered the cave...")
   - Reflects character personality and observations
   - Saves to `output/<session>/narratives/<session>_<character>.md`

### Tips

- **Generate narrator first** to get a complete overview
- **Generate all character narratives** to see how different PCs experienced the same events
- **Lower creativity (0.3-0.5)** for accurate session recaps
- **Higher creativity (0.6-0.8)** for dramatic storytelling and campaign chronicles

## Example Output Formats

### 1. Character First-Person POV (Implemented)

Experience the session through a specific character's eyes.

**Input** (IC-only transcript):
```
[00:15:23] DM: Je betreedt een donkere grot. De muren druipen van het vocht.
[00:15:45] Thorin: Ik steek mijn fakkel aan en kijk om me heen.
[00:16:30] DM: Je ziet oude runen op de muur.
[00:17:15] Elara: Die runen zijn Dwergs. Thorin, kun jij ze lezen?
```

**Output** (Thorin's POV):
```
I entered the dark cave, my torch flickering in the damp air. The walls dripped
with moisture, and the air felt heavy and stale. I lit my torch and looked around,
trying to get my bearings in this gloom.

As my eyes adjusted, I noticed ancient runes carved into the stone wall. They caught
the torchlight and seemed to shimmer slightly.

Elara stepped closer to examine them. "Those runes are Dwarven," she said. "Thorin,
can you read them?"
```

### 2. Third-Person Narrator (Implemented)

Read the session as a fantasy novel with objective narration.

**Input** (IC-only transcript):
```
[00:15:23] DM: Je betreedt een donkere grot. De muren druipen van het vocht.
[00:15:45] Thorin: Ik steek mijn fakkel aan en kijk om me heen.
[00:16:30] DM: Je ziet oude runen op de muur.
[00:17:15] Elara: Die runen zijn Dwergs. Thorin, kun jij ze lezen?
```

**Output** (Third-person narration):
```
The party entered the dark cave, their footsteps echoing off the damp stone walls.
Water dripped steadily from the ceiling, creating an eerie rhythm in the darkness.

Thorin lit his torch and held it aloft, casting flickering shadows across the rough
cavern walls. The warm light revealed ancient runes carved deep into the stone.

Elara moved closer to examine the markings, her elven eyes tracing the intricate
patterns. "Those runes are Dwarven," she announced. Turning to Thorin, she asked,
"Can you read them?"
```

### 3. Character Journal/Diary (Planned)

In-character journal entries for each player character. This format is not yet implemented but could be added in the future.

**Output** (Thorin's journal):
```
Day 47 of our journey

Today we discovered a cave system beneath the mountains. The entrance was hidden
behind a waterfall, just as the old map suggested. The air inside is damp and
cold - reminds me of the mines back home, though these tunnels feel older.
Much older.

Found some Dwarven runes on the walls. They're in an ancient dialect, but I
managed to make out something about a "guardian" and "the deep places." Elara
thinks we should investigate further. I'm not so sure - there's something about
this place that doesn't sit right with me.

Tomorrow we delve deeper.
```

## Future Enhancements

### Command Line Usage (Planned)

```bash
# Generate character POV notebook
python cli.py notebook session1.m4a \
  --perspective character \
  --character "Thorin" \
  --output session1_thorin_pov.txt

# Generate third-person narrator version
python cli.py notebook session1.m4a \
  --perspective narrator \
  --output session1_narrated.txt

# Generate all character journals
python cli.py notebook session1.m4a \
  --perspective journal \
  --output-dir session1_journals/
```

### Python API (Planned)

```python
from src.notebook import SessionNotebook

# Load processed session
notebook = SessionNotebook(session_id="session1")

# Generate character POV
thorin_pov = notebook.generate_character_pov(
    character="Thorin Ironforge",
    style="narrative"  # or "journal"
)

# Generate narrator version
narrator = notebook.generate_narrator_pov(
    style="fantasy"  # or "modern", "noir", etc.
)

# Save to file
notebook.save(thorin_pov, "output/session1_thorin_pov.txt")
```

## Technical Implementation (Planned)

The notebook generator will:

1. **Load IC-only transcript** - Only in-character dialogue and narration
2. **Identify speakers** - Map speakers to characters using party config
3. **Use LLM with context** - Transform text using gpt-oss or similar model
4. **Maintain continuity** - Keep track of narrative flow across chunks
5. **Preserve key events** - Ensure all important moments are included
6. **Add narrative flourish** - Enhance descriptions while staying true to events

### LLM Prompt Strategy

The system will use prompts like:

```
You are transforming a D&D session transcript into a first-person narrative
from the perspective of [CHARACTER NAME], a [RACE] [CLASS].

Original transcript segment:
[DM]: You enter a dark cave.
[Thorin]: I light my torch and look around.

Transform this into first-person narrative from Thorin's perspective,
maintaining the events but adding narrative depth and character voice.
Keep the same language (Dutch/English) as the original.
```

## Use Cases

### For Players
- **Character journals** - Create in-character session recaps
- **Personal perspective** - Experience the session through your character
- **Memory aid** - Easier to read than raw transcripts

### For DMs
- **Session summaries** - Create narrative summaries for players
- **Campaign chronicle** - Build a readable story of the campaign
- **Player engagement** - Share different character perspectives

### For Groups
- **Campaign book** - Compile sessions into a readable novel
- **Different viewpoints** - See how different characters experienced events
- **Shareable stories** - Create content to share with friends

## Configuration Options (Planned)

Customize the notebook generation in `.env`:

```bash
# Notebook settings
NOTEBOOK_MODEL=gpt-oss:20b        # LLM model for transformation
NOTEBOOK_STYLE=fantasy            # narrative style (fantasy, modern, etc.)
NOTEBOOK_LANGUAGE=nl              # Output language
NOTEBOOK_CHUNK_SIZE=500           # Words per processing chunk
NOTEBOOK_PRESERVE_DIALOGUE=true   # Keep original dialogue
```

## Limitations

### What It Won't Do
- **Invent events** - Only transforms what's in the transcript
- **Add new dialogue** - Dialogue remains as spoken
- **Change facts** - Events happen as they did in the session
- **Create perfect prose** - LLM limitations apply

### What to Expect
- **Narrative enhancement** - Better flow and readability
- **Perspective shift** - Events told from chosen viewpoint
- **Consistent voice** - Character personality maintained
- **Some repetition** - Especially in long sessions

## Examples by Perspective Type

### Same Scene, Different Perspectives

**Original transcript**:
```
[DM]: A dragon lands before you, scales gleaming red in the firelight.
[Thorin]: I ready my axe and stand my ground.
[Elara]: I begin casting Shield on Thorin.
[Zyx]: I try to hide behind a rock.
```

**Thorin's POV**:
```
The dragon descended from the sky, its massive red scales reflecting the
dancing flames around us. My heart pounded, but I planted my feet and
raised my axe. This was the moment we'd been training for.

Behind me, I heard Elara beginning an incantation - the familiar words
of a Shield spell. Good. I'd need it. From the corner of my eye, I saw
Zyx darting behind a boulder. Typical.
```

**Third-Person Narrator**:
```
The dragon's shadow fell over the party as the massive beast landed before
them. Its red scales gleamed like molten metal in the firelight, each one
the size of a shield.

Thorin, ever the warrior, immediately readied his battle-axe and stood firm.
His dwarven heritage showed in his unwavering stance - he would not yield.

Elara, recognizing the danger her companion faced, began weaving protective
magic around him. Her fingers traced arcane patterns in the air as she chanted
the Shield incantation.

Meanwhile, Zyx exhibited his usual tactical discretion, quickly positioning
himself behind a conveniently placed boulder.
```

**Zyx's POV**:
```
A DRAGON. An actual dragon just landed right in front of us. Red scales,
breathing fire, the whole deal. This was definitely not in the job description.

Thorin, because he's either brave or insane (probably both), immediately
went into his "I fight dragons before breakfast" stance. Elara started
casting some protection spell on him.

Me? I found a very nice rock to hide behind. Discretion, valor, you know
how it goes. Someone had to survive to tell this story.
```

## Development Status

1. ✅ Core transcription pipeline
2. ✅ Speaker diarization
3. ✅ IC/OOC classification
4. ✅ Party configuration system
5. ✅ Session notebook generation (Narrator + Character POV)
6. ⏳ Multi-session chronicle compilation
7. ⏳ Custom style templates
8. ⏳ Character journal format
9. ⏳ CLI and Python API

## Contributing Ideas

If you have ideas for narrative styles or perspective types, suggestions are welcome:

- Historical chronicle style?
- Bardic retelling?
- Tactical combat report?
- Character inner monologue?
- Multiple perspectives side-by-side?

---

## Current Implementation

The Story Notebooks feature is **fully implemented** in the Gradio Web UI:
- ✅ **Narrator Perspective**: Third-person omniscient overview of the entire session
- ✅ **Character Perspectives**: First-person narratives from each PC's point of view
- ✅ **Creativity Control**: Adjustable temperature slider for narrative style
- ✅ **Automatic Saving**: Narratives saved to `output/<session>/narratives/` as Markdown files

**Not Yet Implemented**:
- ⏳ CLI interface
- ⏳ Python API
- ⏳ Character journal/diary format
- ⏳ Custom style templates
