"""Campaign Knowledge Base - Extract and track campaign information across sessions"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
import ollama
from .config import Config
from .logger import get_logger
from .file_lock import get_file_lock


logger = get_logger(__name__)


@dataclass
class Quest:
    """Represents a quest or objective"""
    title: str
    description: str
    status: str  # "active", "completed", "failed", "unknown"
    first_mentioned: str  # session_id
    last_updated: str  # session_id
    related_npcs: List[str] = field(default_factory=list)
    related_locations: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class NPC:
    """Represents a non-player character"""
    name: str
    description: str
    first_mentioned: str  # session_id
    last_updated: str  # session_id
    role: Optional[str] = None  # "quest_giver", "merchant", "enemy", "ally", etc.
    location: Optional[str] = None
    relationships: Dict[str, str] = field(default_factory=dict)  # {character_name: relationship}
    appearances: List[str] = field(default_factory=list)  # session_ids
    notes: List[str] = field(default_factory=list)


@dataclass
class PlotHook:
    """Represents a plot hook or mystery"""
    summary: str
    details: str
    first_mentioned: str
    last_updated: str
    related_npcs: List[str] = field(default_factory=list)
    related_quests: List[str] = field(default_factory=list)
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class Location:
    """Represents a location in the campaign"""
    name: str
    description: str
    first_mentioned: str
    last_updated: str
    type: Optional[str] = None  # "city", "dungeon", "wilderness", etc.
    notable_features: List[str] = field(default_factory=list)
    npcs_present: List[str] = field(default_factory=list)
    visits: List[str] = field(default_factory=list)  # session_ids


@dataclass
class Item:
    """Represents an important item or artifact"""
    name: str
    description: str
    first_mentioned: str
    last_updated: str
    owner: Optional[str] = None
    location: Optional[str] = None
    properties: List[str] = field(default_factory=list)
    significance: Optional[str] = None


class KnowledgeExtractor:
    """Extract campaign knowledge from structured transcript segments using LLM"""

    def __init__(self):
        self.client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        self.model = Config.OLLAMA_MODEL

    def _build_rich_transcript(self, segments: List[Dict[str, Any]]) -> str:
        """
        Build a formatted transcript string from structured segments,
        including only narratively relevant classifications.
        """
        transcript_parts = []
        narrative_types = {"CHARACTER", "DM_NARRATION", "NPC_DIALOGUE"}

        for segment in segments:
            classification = segment.get("classification", "OOC")
            classification_type = segment.get("classification_type")

            is_narrative = False
            if classification_type:
                is_narrative = classification_type in narrative_types
            elif classification == "IC":
                is_narrative = True

            if is_narrative:
                actor = segment.get("character_name") or segment.get("speaker_name", "Unknown")
                text = segment.get("text", "")
                if actor and text:
                    transcript_parts.append(f"{actor}: {text}")
        
        return "\n".join(transcript_parts)

    def _merge_scene_results(self, all_results: List[Dict[str, List]]) -> Dict[str, List]:
        """
        Merge knowledge extracted from multiple scenes, performing a deep merge
        to enrich entities with new information found in later scenes.
        """
        merged: Dict[str, Dict[str, Any]] = {
            "quests": {}, "npcs": {}, "plot_hooks": {}, "locations": {}, "items": {}
        }

        for result in all_results:
            # --- Deep Merge Quests ---
            for new_quest in result.get("quests", []):
                key = new_quest.title.lower()
                if key in merged["quests"]:
                    existing = merged["quests"][key]
                    if new_quest.description and not existing.description:
                        existing.description = new_quest.description
                    if new_quest.status != "unknown":
                        existing.status = new_quest.status
                else:
                    merged["quests"][key] = new_quest

            # --- Deep Merge NPCs ---
            for new_npc in result.get("npcs", []):
                key = new_npc.name.lower()
                if key in merged["npcs"]:
                    existing = merged["npcs"][key]
                    if new_npc.description and not existing.description:
                        existing.description = new_npc.description
                    if new_npc.role and new_npc.role != "unknown":
                        existing.role = new_npc.role
                    if new_npc.location and not existing.location:
                        existing.location = new_npc.location
                else:
                    merged["npcs"][key] = new_npc

            # --- Simple Merge for Plot Hooks (avoiding resolved duplicates) ---
            for new_hook in result.get("plot_hooks", []):
                key = new_hook.summary.lower()
                if key not in merged["plot_hooks"]:
                    merged["plot_hooks"][key] = new_hook

            # --- Deep Merge Locations ---
            for new_loc in result.get("locations", []):
                key = new_loc.name.lower()
                if key in merged["locations"]:
                    existing = merged["locations"][key]
                    if new_loc.description and not existing.description:
                        existing.description = new_loc.description
                    if new_loc.type and new_loc.type != "unknown":
                        existing.type = new_loc.type
                else:
                    merged["locations"][key] = new_loc

            # --- Deep Merge Items ---
            for new_item in result.get("items", []):
                key = new_item.name.lower()
                if key in merged["items"]:
                    existing = merged["items"][key]
                    if new_item.description and not existing.description:
                        existing.description = new_item.description
                    if new_item.owner and not existing.owner:
                        existing.owner = new_item.owner
                    if new_item.location and not existing.location:
                        existing.location = new_item.location
                    if new_item.significance and not existing.significance:
                        existing.significance = new_item.significance
                else:
                    merged["items"][key] = new_item

        return {category: list(items.values()) for category, items in merged.items()}

    def _extract_knowledge_from_segments(
        self, segments: List[Dict[str, Any]], session_id: str, party_context: Optional[Dict] = None
    ) -> Dict[str, List]:
        """
        Run knowledge extraction on a specific list of segments.
        """
        party_info = ""
        if party_context:
            party_info = f"""
Party Characters: {', '.join(party_context.get('character_names', []))}
Campaign: {party_context.get('campaign', 'Unknown')}
"""
        
        rich_transcript = self._build_rich_transcript(segments)
        if not rich_transcript:
            return {'quests': [], 'npcs': [], 'plot_hooks': [], 'locations': [], 'items': []}

        prompt = f"""You are analyzing a D&D session transcript to extract campaign knowledge.

{party_info}

**Your task**: Extract structured information about:
1. **Quests**: Objectives, missions, or goals mentioned
2. **NPCs**: Non-player characters (names, descriptions, roles)
3. **Plot Hooks**: Mysteries, hints, foreshadowing, or unresolved elements
4. **Locations**: Places visited or mentioned
5. **Items**: Important objects, artifacts, or equipment

**Transcript**:
{rich_transcript[:8000]}

**Instructions**:
- Be specific and extract only concrete information from the provided transcript.
- For NPCs: Include name, brief description, role if known.
- For Quests: Include clear objective and current status.
- For Plot Hooks: Identify mysteries or unresolved elements.
- For Locations: Note place names and brief descriptions.
- For Items: Only significant items (not common equipment).

**Output format** (JSON):
```json
{{
  "quests": [],
  "npcs": [],
  "plot_hooks": [],
  "locations": [],
  "items": []
}}
```

Extract only what is explicitly mentioned. If nothing found, use empty array. Return ONLY the JSON.
"""
        try:
            response = self.client.chat(
                model=self.model, messages=[{'role': 'user', 'content': prompt}]
            )
            response_text = response['message']['content'].strip()

            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            elif '```' in response_text:
                start = response_text.find('```') + 3
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()

            extracted = json.loads(response_text)

            return {
                'quests': [Quest(title=q['title'], description=q['description'], status=q.get('status', 'unknown'), first_mentioned=session_id, last_updated=session_id) for q in extracted.get('quests', [])],
                'npcs': [NPC(name=n['name'], description=n['description'], role=n.get('role'), location=n.get('location'), first_mentioned=session_id, last_updated=session_id, appearances=[session_id]) for n in extracted.get('npcs', [])],
                'plot_hooks': [PlotHook(summary=p['summary'], details=p['details'], first_mentioned=session_id, last_updated=session_id) for p in extracted.get('plot_hooks', [])],
                'locations': [Location(name=l['name'], description=l['description'], type=l.get('type'), first_mentioned=session_id, last_updated=session_id, visits=[session_id]) for l in extracted.get('locations', [])],
                'items': [Item(name=i['name'], description=i['description'], owner=i.get('owner'), first_mentioned=session_id, last_updated=session_id) for i in extracted.get('items', [])]
            }
        except Exception as e:
            logger.error(f"Knowledge extraction error: {e}", exc_info=True)
            return {'quests': [], 'npcs': [], 'plot_hooks': [], 'locations': [], 'items': []}

    def extract_knowledge_from_session(
        self, session_path: Path, session_id: str, party_context: Optional[Dict] = None
    ) -> Dict[str, List]:
        """
        Extracts knowledge from a session, processing scene-by-scene if available.
        """
        classification_file = session_path / "intermediates" / "stage_6_classification.json"
        scenes_file = session_path / "intermediates" / "stage_6_scenes.json"

        if not classification_file.exists():
            logger.error(f"Classification file not found: {classification_file}")
            return {'quests': [], 'npcs': [], 'plot_hooks': [], 'locations': [], 'items': []}

        with open(classification_file, 'r', encoding='utf-8') as f:
            all_segments = json.load(f)
        
        segments_by_id = {seg['segment_index']: seg for seg in all_segments}

        if scenes_file.exists():
            logger.info("Scenes file found, processing scene-by-scene.")
            with open(scenes_file, 'r', encoding='utf-8') as f:
                scenes = json.load(f)
            
            all_results = []
            for i, scene in enumerate(scenes):
                logger.info(f"Extracting knowledge from scene {i+1}/{len(scenes)}...")
                scene_segments = [segments_by_id[seg_id] for seg_id in scene.get("segment_ids", []) if seg_id in segments_by_id]
                if scene_segments:
                    scene_result = self._extract_knowledge_from_segments(scene_segments, session_id, party_context)
                    all_results.append(scene_result)
            
            logger.info("Merging results from all scenes.")
            return self._merge_scene_results(all_results)
        else:
            logger.info("No scenes file found, processing all segments at once.")
            return self._extract_knowledge_from_segments(all_segments, session_id, party_context)


class CampaignKnowledgeBase:
    """Manage campaign knowledge across sessions"""

    def __init__(self, campaign_id: str = "default"):
        self.campaign_id = campaign_id
        self.knowledge_dir = Config.MODELS_DIR / "knowledge"
        self.knowledge_dir.mkdir(exist_ok=True)
        self.knowledge_file = self.knowledge_dir / f"{campaign_id}_knowledge.json"
        self.knowledge = self._load_knowledge()

    def _load_knowledge(self) -> Dict:
        """Load existing knowledge base"""
        if not self.knowledge_file.exists():
            return {
                'campaign_id': self.campaign_id,
                'last_updated': None,
                'sessions_processed': [],
                'quests': [],
                'npcs': [],
                'plot_hooks': [],
                'locations': [],
                'items': []
            }

        try:
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert dicts back to dataclasses
            data['quests'] = [Quest(**q) for q in data.get('quests', [])]
            data['npcs'] = [NPC(**n) for n in data.get('npcs', [])]
            data['plot_hooks'] = [PlotHook(**p) for p in data.get('plot_hooks', [])]
            data['locations'] = [Location(**l) for l in data.get('locations', [])]
            data['items'] = [Item(**i) for i in data.get('items', [])]

            return data
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}", exc_info=True)
            return self._load_knowledge.__wrapped__(self)

    def _save_knowledge(self):
        """Save knowledge base to disk with file locking to prevent concurrent write conflicts."""
        # Use file lock to prevent race conditions
        lock = get_file_lock(self.knowledge_file)
        with lock:
            # Convert dataclasses to dicts
            data = {
                'campaign_id': self.knowledge['campaign_id'],
                'last_updated': datetime.now().isoformat(),
                'sessions_processed': self.knowledge['sessions_processed'],
                'quests': [asdict(q) for q in self.knowledge['quests']],
                'npcs': [asdict(n) for n in self.knowledge['npcs']],
                'plot_hooks': [asdict(p) for p in self.knowledge['plot_hooks']],
                'locations': [asdict(l) for l in self.knowledge['locations']],
                'items': [asdict(i) for i in self.knowledge['items']]
            }

            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def merge_new_knowledge(self, new_knowledge: Dict, session_id: str):
        """Merge newly extracted knowledge into the knowledge base"""

        # Track this session
        if session_id not in self.knowledge['sessions_processed']:
            self.knowledge['sessions_processed'].append(session_id)

        # Merge quests (update existing or add new)
        for new_quest in new_knowledge.get('quests', []):
            existing = next((q for q in self.knowledge['quests'] if q.title.lower() == new_quest.title.lower()), None)
            if existing:
                # Update existing quest
                existing.description = new_quest.description
                existing.status = new_quest.status
                existing.last_updated = session_id
            else:
                self.knowledge['quests'].append(new_quest)

        # Merge NPCs (update existing or add new)
        for new_npc in new_knowledge.get('npcs', []):
            existing = next((n for n in self.knowledge['npcs'] if n.name.lower() == new_npc.name.lower()), None)
            if existing:
                # Update existing NPC
                existing.description = new_npc.description
                existing.last_updated = session_id
                if new_npc.role:
                    existing.role = new_npc.role
                if new_npc.location:
                    existing.location = new_npc.location
                if session_id not in existing.appearances:
                    existing.appearances.append(session_id)
            else:
                self.knowledge['npcs'].append(new_npc)

        # Merge plot hooks (always add new ones)
        for new_hook in new_knowledge.get('plot_hooks', []):
            # Check for similar hooks to avoid duplicates
            similar = next((p for p in self.knowledge['plot_hooks']
                          if p.summary.lower() == new_hook.summary.lower() and not p.resolved), None)
            if not similar:
                self.knowledge['plot_hooks'].append(new_hook)

        # Merge locations (update existing or add new)
        for new_loc in new_knowledge.get('locations', []):
            existing = next((l for l in self.knowledge['locations'] if l.name.lower() == new_loc.name.lower()), None)
            if existing:
                existing.description = new_loc.description
                existing.last_updated = session_id
                if session_id not in existing.visits:
                    existing.visits.append(session_id)
            else:
                self.knowledge['locations'].append(new_loc)

        # Merge items (update existing or add new)
        for new_item in new_knowledge.get('items', []):
            existing = next((i for i in self.knowledge['items'] if i.name.lower() == new_item.name.lower()), None)
            if existing:
                existing.description = new_item.description
                existing.last_updated = session_id
                if new_item.owner:
                    existing.owner = new_item.owner
                if new_item.location:
                    existing.location = new_item.location
            else:
                self.knowledge['items'].append(new_item)

        self._save_knowledge()

    def get_active_quests(self) -> List[Quest]:
        """Get all active quests"""
        return [q for q in self.knowledge['quests'] if q.status == 'active']

    def get_all_npcs(self) -> List[NPC]:
        """Get all NPCs"""
        return self.knowledge['npcs']

    def get_unresolved_plot_hooks(self) -> List[PlotHook]:
        """Get unresolved plot hooks"""
        return [p for p in self.knowledge['plot_hooks'] if not p.resolved]

    def get_all_locations(self) -> List[Location]:
        """Get all known locations"""
        return self.knowledge['locations']

    def search_knowledge(self, query: str) -> Dict:
        """Search across all knowledge"""
        query_lower = query.lower()
        results = {
            'quests': [q for q in self.knowledge['quests'] if query_lower in q.title.lower() or query_lower in q.description.lower()],
            'npcs': [n for n in self.knowledge['npcs'] if query_lower in n.name.lower() or query_lower in n.description.lower()],
            'plot_hooks': [p for p in self.knowledge['plot_hooks'] if query_lower in p.summary.lower() or query_lower in p.details.lower()],
            'locations': [l for l in self.knowledge['locations'] if query_lower in l.name.lower() or query_lower in l.description.lower()],
            'items': [i for i in self.knowledge['items'] if query_lower in i.name.lower() or query_lower in i.description.lower()]
        }
        return results
