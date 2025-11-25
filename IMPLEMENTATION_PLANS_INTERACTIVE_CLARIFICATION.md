# Implementation Plan: Interactive Clarification System

> **Feature ID**: P2-INTERACTIVE-CLARIFICATION
> **Status**: Phase 1 Complete, Phase 2-5 In Progress
> **Priority**: P2 (Important Enhancement)
> **Effort**: 5-7 days (2 days completed, 3-5 days remaining)
> **Owner**: Lane 1 Agent (Jules Bot)
> **Created**: 2025-11-18
> **Last Updated**: 2025-11-25
> **Phase 1 Completed**: 2025-11-25 (PR #139 - Merged)

---

## Executive Summary

Add real-time interactive clarification system to the pipeline that pauses processing when confidence is low and asks users for input through a chat-like interface in the Gradio UI. User responses improve immediate accuracy and train the system for future sessions.

**Problem**: Pipeline makes best-guess decisions when uncertain, leading to compounding errors.
**Solution**: Ask users to clarify ambiguous cases in real-time during processing.
**Impact**: 20-30% improvement in speaker identification accuracy, reduced post-processing corrections.

---

## Architecture Overview

### System Components

```
Pipeline Processing                UI Layer
+-------------------+             +------------------+
| SessionPipeline   |             | Gradio App       |
|                   |             |                  |
| 1. Audio Proc     |             | Process Tab      |
| 2. Chunking       |             | +-------------+  |
| 3. Transcription  |             | | Chat Widget |  |
| 4. Diarization    |<----------->| | Audio Play  |  |
|    -> Low conf?   |   Question  | | Quick Btns  |  |
|    -> Ask user    |   Queue     | +-------------+  |
| 5. Classification |             |                  |
| 6. Output         |             |                  |
+-------------------+             +------------------+
        |                                 ^
        v                                 |
+-------------------+             +------------------+
| InteractiveClarifier            | AppManager       |
|                   |             |                  |
| - Question Queue  |<----------->| - WebSocket/SSE  |
| - Context Storage |             | - Pause/Resume   |
| - Learning System |             | - State Sync     |
| - Timeout Handler |             |                  |
+-------------------+             +------------------+
```

### Data Flow

1. **Question Trigger**: Pipeline stage detects low confidence
2. **Context Capture**: Extract audio snippet, transcript text, timestamp
3. **Queue Question**: InteractiveClarifier queues question with context
4. **Pause Pipeline**: AppManager pauses background processing
5. **Notify UI**: WebSocket sends question to UI
6. **User Response**: UI collects response (or timeout)
7. **Apply Learning**: Update embeddings, party profiles, confidence scores
8. **Resume Pipeline**: Continue with corrected information

---

## Implementation Phases

### Phase 1: Core Infrastructure (2 days) ✅ COMPLETE

**Status**: ✅ Merged via PR #139 (2025-11-25)
**Branch**: `feature-interactive-clarification-phase1`
**Files Created**:
- `src/interactive_clarifier.py` (263 lines)
- `tests/test_interactive_clarifier.py` (comprehensive unit tests)

**Files Modified**:
- `src/config.py` (added IC configuration parameters)
- `.env.example` (added IC environment variables)

**Technical Notes**:
- Implemented thread-safe InteractiveClarifier class using `threading.Event`
- Priority queue system for managing multiple concurrent questions
- Configurable timeout handling with default fallbacks
- Question limit enforcement to prevent UI overload
- All unit tests passing (thread safety, priority ordering, timeout, response handling)

**Completed Tasks** (9/9):
- [x] IC-1.1.1: Create `src/interactive_clarifier.py` with InteractiveClarifier class
- [x] IC-1.1.2: Add configuration options to `src/config.py` for interactive clarification
- [x] IC-1.1.3: Add environment variables to `.env.example`
- [x] IC-1.1.4: Write unit tests in `tests/test_interactive_clarifier.py`
- [x] IC-1.1.5: Test thread safety with concurrent questions
- [x] IC-1.1.6: Test priority ordering
- [x] IC-1.1.7: Test timeout handling
- [x] IC-1.1.8: Test response submission/retrieval
- [x] IC-1.1.9: Test question limit enforcement

#### 1.1 Question Queue System ✅
**File**: `src/interactive_clarifier.py` (NEW - CREATED)

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import queue
import threading

class QuestionPriority(Enum):
    """Priority levels for clarification questions."""
    CRITICAL = 1    # Speaker count mismatch - must answer
    HIGH = 2        # Low confidence identification - should answer
    MEDIUM = 3      # Borderline classification - nice to answer
    LOW = 4         # Optional confirmation

class QuestionType(Enum):
    """Types of clarification questions."""
    SPEAKER_IDENTIFICATION = "speaker_id"
    CHARACTER_MAPPING = "char_map"
    IC_OOC_CLASSIFICATION = "ic_ooc"
    SPEAKER_COUNT = "speaker_count"

@dataclass
class ClarificationQuestion:
    """A single clarification question."""
    id: str
    question_type: QuestionType
    priority: QuestionPriority
    timestamp: float
    context: Dict[str, Any]
    question_text: str
    options: List[str]
    audio_snippet_path: Optional[Path] = None
    transcript_excerpt: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 60

@dataclass
class ClarificationResponse:
    """User response to a clarification question."""
    question_id: str
    answer: str
    confidence: float
    responded_at: datetime = field(default_factory=datetime.now)
    timeout: bool = False

class InteractiveClarifier:
    """
    Manages interactive clarification questions during pipeline processing.

    Features:
    - Priority-based question queue
    - Timeout handling with defaults
    - Context storage for learning
    - Thread-safe operations
    """

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.interactive_clarification_enabled
        self.confidence_threshold = config.clarification_confidence_threshold
        self.timeout_seconds = config.clarification_timeout_seconds
        self.max_questions = config.clarification_max_questions

        self._question_queue = queue.PriorityQueue()
        self._pending_questions: Dict[str, ClarificationQuestion] = {}
        self._responses: Dict[str, ClarificationResponse] = {}
        self._lock = threading.Lock()
        self._question_counter = 0

    def should_ask(self, confidence: float, question_type: QuestionType) -> bool:
        """
        Determine if a clarification question should be asked.

        Args:
            confidence: Confidence score (0.0-1.0)
            question_type: Type of question

        Returns:
            True if question should be asked
        """
        if not self.enabled:
            return False

        if len(self._pending_questions) >= self.max_questions:
            return False

        # Critical questions always asked
        if question_type == QuestionType.SPEAKER_COUNT:
            return True

        # Other questions based on confidence threshold
        return confidence < self.confidence_threshold

    def ask_question(
        self,
        question_type: QuestionType,
        priority: QuestionPriority,
        question_text: str,
        options: List[str],
        context: Dict[str, Any],
        audio_snippet_path: Optional[Path] = None,
        transcript_excerpt: Optional[str] = None
    ) -> str:
        """
        Queue a clarification question.

        Args:
            question_type: Type of question
            priority: Priority level
            question_text: Human-readable question
            options: Answer options for user
            context: Additional context for learning
            audio_snippet_path: Path to audio clip (if available)
            transcript_excerpt: Relevant transcript text

        Returns:
            Question ID for tracking response
        """
        with self._lock:
            self._question_counter += 1
            question_id = f"q_{self._question_counter:04d}"

        question = ClarificationQuestion(
            id=question_id,
            question_type=question_type,
            priority=priority,
            timestamp=context.get('timestamp', 0.0),
            context=context,
            question_text=question_text,
            options=options,
            audio_snippet_path=audio_snippet_path,
            transcript_excerpt=transcript_excerpt,
            timeout_seconds=self.timeout_seconds
        )

        # Add to queue (priority value, counter for stable sort)
        self._question_queue.put((priority.value, self._question_counter, question))

        with self._lock:
            self._pending_questions[question_id] = question

        return question_id

    def get_next_question(self, timeout: Optional[float] = None) -> Optional[ClarificationQuestion]:
        """
        Get next question from queue (blocks if empty).

        Args:
            timeout: Maximum time to wait for question (None = wait forever)

        Returns:
            Next question or None if timeout
        """
        try:
            _, _, question = self._question_queue.get(timeout=timeout)
            return question
        except queue.Empty:
            return None

    def has_pending_questions(self) -> bool:
        """Check if there are pending questions."""
        return not self._question_queue.empty()

    def submit_response(
        self,
        question_id: str,
        answer: str,
        confidence: float = 1.0
    ) -> None:
        """
        Submit user response to a question.

        Args:
            question_id: ID of question being answered
            answer: User's answer
            confidence: User's confidence in answer (0.0-1.0)
        """
        response = ClarificationResponse(
            question_id=question_id,
            answer=answer,
            confidence=confidence
        )

        with self._lock:
            self._responses[question_id] = response
            if question_id in self._pending_questions:
                del self._pending_questions[question_id]

    def get_response(
        self,
        question_id: str,
        wait: bool = True,
        timeout: Optional[float] = None
    ) -> Optional[ClarificationResponse]:
        """
        Get response for a question (optionally wait for it).

        Args:
            question_id: Question ID
            wait: Whether to wait for response
            timeout: Maximum wait time if wait=True

        Returns:
            Response or None if not available/timeout
        """
        if not wait:
            with self._lock:
                return self._responses.get(question_id)

        # Wait for response with timeout
        start_time = datetime.now()
        while True:
            with self._lock:
                if question_id in self._responses:
                    return self._responses[question_id]

            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= timeout:
                    # Timeout - create default response
                    question = self._pending_questions.get(question_id)
                    if question:
                        return self._create_timeout_response(question)
                    return None

            time.sleep(0.1)

    def _create_timeout_response(self, question: ClarificationQuestion) -> ClarificationResponse:
        """Create default response for timed-out question."""
        # Use first option (default) or context-based guess
        default_answer = question.options[0] if question.options else "skip"

        return ClarificationResponse(
            question_id=question.id,
            answer=default_answer,
            confidence=0.5,  # Low confidence for timeout
            timeout=True
        )

    def clear_responses(self) -> None:
        """Clear all stored responses (call after session complete)."""
        with self._lock:
            self._responses.clear()
            self._pending_questions.clear()
```

**Tasks**:
- [ ] Create `src/interactive_clarifier.py` with classes above
- [ ] Add configuration options to `src/config.py`
- [ ] Add to `.env.example`:
  ```bash
  INTERACTIVE_CLARIFICATION_ENABLED=true
  CLARIFICATION_CONFIDENCE_THRESHOLD=0.7
  CLARIFICATION_TIMEOUT_SECONDS=60
  CLARIFICATION_MAX_QUESTIONS=20
  ```
- [ ] Write unit tests in `tests/test_interactive_clarifier.py`

**Test Coverage**:
- Thread safety (concurrent questions)
- Priority ordering
- Timeout handling
- Response submission/retrieval
- Question limit enforcement

---

### Phase 2: Pipeline Integration (1.5 days)

#### 2.1 Diarization Integration
**File**: `src/diarizer.py` (MODIFY)

```python
def _assign_speakers_to_segments(
    self,
    segments: List[TranscriptSegment],
    clarifier: Optional[InteractiveClarifier] = None
) -> List[TranscriptSegment]:
    """
    Assign speaker labels to segments.

    Args:
        segments: Segments to label
        clarifier: Interactive clarifier for ambiguous cases

    Returns:
        Segments with speaker labels
    """
    for segment in segments:
        speaker_id, confidence = self._identify_speaker(segment)

        # Check if we should ask for clarification
        if clarifier and clarifier.should_ask(
            confidence,
            QuestionType.SPEAKER_IDENTIFICATION
        ):
            # Extract audio snippet for context
            snippet_path = self._extract_snippet(segment)

            # Ask user
            question_id = clarifier.ask_question(
                question_type=QuestionType.SPEAKER_IDENTIFICATION,
                priority=QuestionPriority.HIGH,
                question_text=f"Who is speaking at {segment.start:.1f}s?",
                options=self._get_speaker_options(),
                context={
                    'timestamp': segment.start,
                    'speaker_id': speaker_id,
                    'confidence': confidence,
                    'embedding': segment.embedding
                },
                audio_snippet_path=snippet_path,
                transcript_excerpt=segment.text[:200]
            )

            # Wait for response (with timeout)
            response = clarifier.get_response(
                question_id,
                wait=True,
                timeout=clarifier.timeout_seconds
            )

            if response and not response.timeout:
                # User provided clarification
                speaker_id = response.answer
                confidence = response.confidence

                # Learn from correction
                self._update_speaker_embedding(
                    speaker_id,
                    segment.embedding,
                    weight=response.confidence
                )

        segment.speaker = speaker_id
        segment.confidence = confidence

    return segments
```

#### 2.2 Character Mapping Integration
**File**: `src/party_config.py` (MODIFY)

```python
def map_speakers_to_characters(
    self,
    speakers: List[str],
    clarifier: Optional[InteractiveClarifier] = None
) -> Dict[str, str]:
    """
    Map speaker IDs to character names.

    Args:
        speakers: Detected speaker IDs
        clarifier: Interactive clarifier for ambiguous mappings

    Returns:
        Mapping of speaker_id -> character_name
    """
    mapping = {}

    # Check for count mismatch
    if len(speakers) != len(self.characters):
        if clarifier:
            question_id = clarifier.ask_question(
                question_type=QuestionType.SPEAKER_COUNT,
                priority=QuestionPriority.CRITICAL,
                question_text=(
                    f"I detected {len(speakers)} speakers but you specified "
                    f"{len(self.characters)} characters. How should I proceed?"
                ),
                options=[
                    "Add new character",
                    "Merge similar speakers",
                    "One character has multiple speakers",
                    "Reprocess with correct count"
                ],
                context={
                    'detected_speakers': speakers,
                    'expected_characters': self.characters
                }
            )

            response = clarifier.get_response(question_id, wait=True)
            # Handle response...

    # Auto-map with confidence checking
    for speaker_id in speakers:
        char_name, confidence = self._match_speaker_to_character(speaker_id)

        if clarifier and confidence < clarifier.confidence_threshold:
            # Ask for clarification
            question_id = clarifier.ask_question(
                question_type=QuestionType.CHARACTER_MAPPING,
                priority=QuestionPriority.HIGH,
                question_text=f"Which character is {speaker_id}?",
                options=self.characters + ["Unknown"],
                context={
                    'speaker_id': speaker_id,
                    'best_match': char_name,
                    'confidence': confidence
                }
            )

            response = clarifier.get_response(question_id, wait=True)
            if response:
                char_name = response.answer

                # Store learning
                self._store_speaker_mapping(speaker_id, char_name)

        mapping[speaker_id] = char_name

    return mapping
```

#### 2.3 Pipeline Modification
**File**: `src/pipeline.py` (MODIFY)

```python
class SessionPipeline:
    def __init__(self, config: Config, clarifier: Optional[InteractiveClarifier] = None):
        self.config = config
        self.clarifier = clarifier
        # ... existing init

    def run(self, input_file: Path, session_id: str) -> PipelineResult:
        """Run pipeline with optional interactive clarification."""

        # ... existing stages

        # Diarization with clarification
        if self.clarifier:
            self.clarifier.clear_responses()  # Fresh start

        result = self._run_stage_diarization(context, self.clarifier)

        # ... continue
```

**Tasks**:
- [ ] Add `clarifier` parameter to pipeline initialization
- [ ] Modify `_run_stage_diarization()` to accept clarifier
- [ ] Modify `_run_stage_classification()` for IC/OOC clarification
- [ ] Update speaker mapping logic in party config
- [ ] Add snippet extraction helper in snipper.py
- [ ] Write integration tests

---

### Phase 3: UI Integration (2 days)

#### 3.1 WebSocket Communication
**File**: `app_manager.py` (MODIFY)

```python
import asyncio
from typing import Optional, Callable

class AppManager:
    """Background process manager with WebSocket support."""

    def __init__(self):
        # ... existing init
        self._question_callback: Optional[Callable] = None
        self._websocket_clients = []

    def set_question_callback(self, callback: Callable) -> None:
        """Set callback for when questions are asked."""
        self._question_callback = callback

    async def _run_pipeline_async(
        self,
        input_file: Path,
        config: Config,
        clarifier: InteractiveClarifier
    ):
        """Run pipeline asynchronously with clarification support."""

        # Start background thread for question monitoring
        question_thread = threading.Thread(
            target=self._monitor_questions,
            args=(clarifier,),
            daemon=True
        )
        question_thread.start()

        # Run pipeline
        result = await asyncio.to_thread(
            self.pipeline.run,
            input_file,
            session_id,
            clarifier
        )

        return result

    def _monitor_questions(self, clarifier: InteractiveClarifier):
        """Monitor for new questions and notify UI."""
        while self.is_running:
            question = clarifier.get_next_question(timeout=1.0)
            if question:
                # Notify UI via callback
                if self._question_callback:
                    self._question_callback(question)
```

#### 3.2 Chat UI Component
**File**: `src/ui/clarification_chat.py` (NEW)

```python
import gradio as gr
from typing import List, Tuple, Optional
from pathlib import Path

class ClarificationChat:
    """
    Interactive chat component for clarification questions.

    Displays during processing to ask user for input on ambiguous cases.
    """

    def __init__(self, clarifier: InteractiveClarifier):
        self.clarifier = clarifier
        self.current_question: Optional[ClarificationQuestion] = None

    def create_ui(self) -> List[gr.components.Component]:
        """Create Gradio components for clarification chat."""

        with gr.Column(visible=False) as chat_container:
            gr.Markdown("### Clarification Needed")

            question_display = gr.Markdown("")

            # Audio playback (if available)
            audio_player = gr.Audio(
                label="Audio Context",
                visible=False,
                interactive=False
            )

            # Transcript excerpt
            transcript_display = gr.Textbox(
                label="Transcript",
                lines=3,
                interactive=False
            )

            # Answer buttons (dynamic)
            with gr.Row():
                answer_buttons = gr.Radio(
                    label="Your Answer",
                    choices=[]
                )

            with gr.Row():
                skip_btn = gr.Button("Skip", variant="secondary")
                submit_btn = gr.Button("Submit", variant="primary")

            # Status
            status_display = gr.Markdown("")

        return {
            'container': chat_container,
            'question': question_display,
            'audio': audio_player,
            'transcript': transcript_display,
            'buttons': answer_buttons,
            'skip': skip_btn,
            'submit': submit_btn,
            'status': status_display
        }

    def show_question(self, question: ClarificationQuestion) -> Tuple:
        """
        Display a clarification question in UI.

        Returns:
            Tuple of updated component states
        """
        self.current_question = question

        # Format question text with context
        question_md = f"""
**Question at {question.timestamp:.1f}s**

{question.question_text}

*Confidence: {question.context.get('confidence', 0):.1%}*
        """

        # Audio snippet (if available)
        audio_path = question.audio_snippet_path
        audio_visible = audio_path is not None

        # Transcript excerpt
        transcript = question.transcript_excerpt or ""

        return (
            gr.update(visible=True),  # container
            question_md,              # question
            gr.update(value=str(audio_path) if audio_path else None, visible=audio_visible),  # audio
            transcript,               # transcript
            gr.update(choices=question.options)  # buttons
        )

    def handle_submit(self, answer: str) -> str:
        """Handle user submitting answer."""
        if self.current_question and answer:
            self.clarifier.submit_response(
                question_id=self.current_question.id,
                answer=answer,
                confidence=1.0
            )
            return "Answer submitted! Continuing processing..."
        return "No answer selected"

    def handle_skip(self) -> str:
        """Handle user skipping question."""
        if self.current_question:
            # Submit default answer
            self.clarifier.submit_response(
                question_id=self.current_question.id,
                answer=self.current_question.options[0],
                confidence=0.5
            )
            return "Skipped - using default answer"
        return "No question to skip"
```

#### 3.3 Integration with Process Tab
**File**: `src/ui/process_session_tab_modern.py` (MODIFY)

```python
def create_process_session_tab(app_manager: AppManager) -> gr.Blocks:
    """Create Process Session tab with clarification support."""

    # Initialize clarifier
    clarifier = InteractiveClarifier(Config.from_env())
    chat_ui = ClarificationChat(clarifier)

    with gr.Blocks() as tab:
        # ... existing upload/config UI

        # Processing status
        with gr.Column(visible=False) as processing_container:
            progress = gr.Progress()
            status_display = gr.Markdown("")

            # Clarification chat (appears during processing)
            chat_components = chat_ui.create_ui()

        # ... existing result display

        # Event handlers
        def on_start_processing(file, config):
            # Set up question callback
            def question_handler(question):
                # Update UI with new question
                return chat_ui.show_question(question)

            app_manager.set_question_callback(question_handler)

            # Start processing with clarifier
            result = app_manager.process_session(
                input_file=file,
                config=config,
                clarifier=clarifier
            )

            return result

        process_btn.click(
            fn=on_start_processing,
            inputs=[upload_file, config_inputs],
            outputs=[status_display, chat_components['container'], ...]
        )

        chat_components['submit'].click(
            fn=chat_ui.handle_submit,
            inputs=[chat_components['buttons']],
            outputs=[chat_components['status']]
        )

        chat_components['skip'].click(
            fn=chat_ui.handle_skip,
            outputs=[chat_components['status']]
        )

    return tab
```

**Tasks**:
- [ ] Add WebSocket/SSE support to AppManager
- [ ] Create `src/ui/clarification_chat.py`
- [ ] Modify process session tab to include chat component
- [ ] Add real-time question routing
- [ ] Test UI responsiveness during processing
- [ ] Handle disconnection gracefully

---

### Phase 4: Learning System (1 day)

#### 4.1 Speaker Embedding Updates
**File**: `src/diarizer.py` (MODIFY)

```python
def _update_speaker_embedding(
    self,
    speaker_id: str,
    embedding: np.ndarray,
    weight: float = 1.0
) -> None:
    """
    Update speaker embedding based on user correction.

    Uses exponential moving average to incorporate new information.

    Args:
        speaker_id: Speaker to update
        embedding: Corrected embedding
        weight: Weight for new embedding (0.0-1.0)
    """
    if speaker_id not in self.speaker_embeddings:
        self.speaker_embeddings[speaker_id] = embedding
        return

    # Exponential moving average
    alpha = 0.3 * weight  # Learning rate adjusted by confidence
    current = self.speaker_embeddings[speaker_id]
    updated = alpha * embedding + (1 - alpha) * current

    # Normalize
    updated = updated / np.linalg.norm(updated)

    self.speaker_embeddings[speaker_id] = updated

    # Save to profile
    self._save_speaker_profile(speaker_id, updated)
```

#### 4.2 Party Profile Learning
**File**: `src/party_config.py` (MODIFY)

```python
@dataclass
class SpeakerMapping:
    """Learned mapping between speaker ID and character."""
    speaker_id: str
    character_name: str
    confidence: float
    session_id: str
    learned_at: datetime

class PartyConfig:
    """Party configuration with learning capability."""

    def __init__(self):
        # ... existing
        self.speaker_mappings: List[SpeakerMapping] = []

    def store_speaker_mapping(
        self,
        speaker_id: str,
        character_name: str,
        session_id: str,
        confidence: float = 1.0
    ) -> None:
        """
        Store learned speaker-to-character mapping.

        Future sessions can use this to improve initial mapping.
        """
        mapping = SpeakerMapping(
            speaker_id=speaker_id,
            character_name=character_name,
            confidence=confidence,
            session_id=session_id,
            learned_at=datetime.now()
        )

        self.speaker_mappings.append(mapping)
        self._save_to_disk()

    def get_likely_character(self, speaker_id: str) -> Tuple[str, float]:
        """
        Get most likely character for speaker based on history.

        Returns:
            (character_name, confidence)
        """
        # Find all mappings for this speaker
        matches = [m for m in self.speaker_mappings if m.speaker_id == speaker_id]

        if not matches:
            return ("Unknown", 0.0)

        # Use most recent high-confidence mapping
        matches.sort(key=lambda m: (m.confidence, m.learned_at), reverse=True)
        best = matches[0]

        return (best.character_name, best.confidence)
```

**Tasks**:
- [ ] Implement embedding update in diarizer
- [ ] Add speaker mapping storage to party config
- [ ] Create learning metrics tracking
- [ ] Add "learning effectiveness" report
- [ ] Test accuracy improvements over time

---

### Phase 5: Testing & Polish (1 day)

#### 5.1 Unit Tests
**File**: `tests/test_interactive_clarifier.py`

```python
import pytest
from src.interactive_clarifier import (
    InteractiveClarifier,
    QuestionType,
    QuestionPriority
)

def test_question_queue_ordering():
    """Test questions are prioritized correctly."""
    clarifier = InteractiveClarifier(config)

    # Add questions with different priorities
    q1 = clarifier.ask_question(
        QuestionType.SPEAKER_IDENTIFICATION,
        QuestionPriority.LOW,
        "Low priority",
        ["A", "B"],
        {}
    )

    q2 = clarifier.ask_question(
        QuestionType.SPEAKER_COUNT,
        QuestionPriority.CRITICAL,
        "Critical",
        ["A", "B"],
        {}
    )

    # Critical should come first
    first = clarifier.get_next_question()
    assert first.id == q2

def test_timeout_handling():
    """Test questions timeout with default answers."""
    clarifier = InteractiveClarifier(config)

    q_id = clarifier.ask_question(
        QuestionType.SPEAKER_IDENTIFICATION,
        QuestionPriority.HIGH,
        "Who is speaking?",
        ["Alice", "Bob"],
        {}
    )

    # Wait for timeout
    response = clarifier.get_response(q_id, wait=True, timeout=2.0)

    assert response is not None
    assert response.timeout is True
    assert response.answer == "Alice"  # First option

def test_concurrent_questions():
    """Test thread safety with concurrent questions."""
    # ... stress test with multiple threads
```

#### 5.2 Integration Tests
**File**: `tests/integration/test_interactive_pipeline.py`

```python
def test_pipeline_with_clarification(test_audio_file, mock_clarifier):
    """Test full pipeline with clarification enabled."""

    # Configure mock to answer questions automatically
    mock_clarifier.auto_respond = True

    pipeline = SessionPipeline(config, clarifier=mock_clarifier)
    result = pipeline.run(test_audio_file, "test_session")

    assert result.status == ProcessingStatus.COMPLETED
    assert mock_clarifier.questions_asked > 0
    assert all(q.id in mock_clarifier.responses for q in mock_clarifier.questions)
```

#### 5.3 UI Tests
**File**: `tests/integration/test_clarification_ui.py`

```python
def test_chat_ui_question_display(gradio_client):
    """Test chat UI displays questions correctly."""
    # ... test UI rendering

def test_chat_ui_answer_submission(gradio_client):
    """Test user can submit answers through UI."""
    # ... test interaction flow
```

**Tasks**:
- [ ] Write 20+ unit tests for InteractiveClarifier
- [ ] Write integration tests for pipeline
- [ ] Write UI interaction tests
- [ ] Load testing (many concurrent questions)
- [ ] Error handling tests
- [ ] Documentation and examples

---

## Configuration

### Environment Variables

Add to `.env.example`:

```bash
# Interactive Clarification System
INTERACTIVE_CLARIFICATION_ENABLED=true
CLARIFICATION_CONFIDENCE_THRESHOLD=0.7  # Ask if confidence below this
CLARIFICATION_TIMEOUT_SECONDS=60        # Auto-skip after timeout
CLARIFICATION_MAX_QUESTIONS=20          # Limit per session
```

### Config Class Updates

**File**: `src/config.py` (MODIFY)

```python
@dataclass
class Config:
    # ... existing fields

    # Interactive Clarification
    interactive_clarification_enabled: bool = True
    clarification_confidence_threshold: float = 0.7
    clarification_timeout_seconds: int = 60
    clarification_max_questions: int = 20

    @classmethod
    def from_env(cls) -> "Config":
        """Load config from environment variables."""
        return cls(
            # ... existing
            interactive_clarification_enabled=os.getenv(
                "INTERACTIVE_CLARIFICATION_ENABLED", "true"
            ).lower() == "true",
            clarification_confidence_threshold=float(
                os.getenv("CLARIFICATION_CONFIDENCE_THRESHOLD", "0.7")
            ),
            clarification_timeout_seconds=int(
                os.getenv("CLARIFICATION_TIMEOUT_SECONDS", "60")
            ),
            clarification_max_questions=int(
                os.getenv("CLARIFICATION_MAX_QUESTIONS", "20")
            )
        )
```

---

## Success Metrics

### Quantitative Goals

1. **Accuracy Improvement**
   - Speaker identification accuracy: 70% -> 90%+ (target)
   - Character mapping accuracy: 80% -> 95%+ (target)
   - IC/OOC classification accuracy: 85% -> 92%+ (target)

2. **User Experience**
   - Average questions per session: < 15
   - Average response time: < 30 seconds
   - Timeout rate: < 20% of questions
   - User satisfaction: > 4.0/5.0

3. **Learning Effectiveness**
   - Questions in session 1: ~20
   - Questions in session 5: ~5 (75% reduction)
   - Confidence scores trending upward over time

### Qualitative Goals

- Users feel in control of the process
- Errors caught early vs. post-processing corrections
- Natural, non-disruptive interaction flow
- Clear context for every question
- Graceful degradation when disabled

---

## Risk Mitigation

### Risk 1: UI Responsiveness
**Risk**: Background processing blocks UI updates
**Mitigation**:
- Use async/await for pipeline processing
- WebSocket for non-blocking communication
- Show processing status even when waiting for answer

### Risk 2: Timeout Handling
**Risk**: Users miss questions, defaults cause errors
**Mitigation**:
- Clear timeout countdown in UI
- Sensible defaults based on context
- Allow reviewing/correcting after session complete

### Risk 3: Over-questioning
**Risk**: Too many questions annoy users
**Mitigation**:
- Configurable threshold and max questions
- Priority system (only ask critical questions first)
- Learning reduces questions over time

### Risk 4: Audio Snippet Extraction
**Risk**: Snippet extraction adds latency
**Mitigation**:
- Pre-extract snippets during chunking stage
- Cache snippets in temp directory
- Make audio playback optional

### Risk 5: Network Disconnection
**Risk**: User disconnects during processing
**Mitigation**:
- Store questions in persistent queue
- Auto-resume with defaults if disconnected
- Allow reviewing questions post-processing

---

## Future Enhancements

After initial implementation, consider:

1. **Batch Review Mode** - Review all questions at end instead of during processing
2. **Voice Confirmation** - User speaks answer instead of clicking
3. **Smart Defaults** - ML model predicts best default based on context
4. **Question History** - Review past questions and change answers
5. **Multi-User Mode** - Different users can answer different question types
6. **Mobile Support** - Optimized UI for phone/tablet
7. **Keyboard Shortcuts** - Power users can answer quickly

---

## Implementation Notes & Reasoning

### Why Real-Time vs. Batch?

**Decision**: Real-time questions during processing
**Reasoning**:
- Immediate feedback loop improves accuracy
- Context is fresh in user's mind
- Can prevent cascade errors early
- More engaging user experience

**Trade-off**: Requires user presence during processing
**Mitigation**: Batch mode as future enhancement option

### Why WebSocket vs. Polling?

**Decision**: WebSocket for real-time communication
**Reasoning**:
- Lower latency for questions
- Bidirectional communication
- Better for long-running sessions

**Trade-off**: More complex implementation
**Mitigation**: Fallback to polling if WebSocket unavailable

### Why Priority Queue?

**Decision**: Priority-based question queue
**Reasoning**:
- Critical questions (speaker count) must be answered
- Less critical questions can be skipped
- Respects user's time and attention

### Why Learning System?

**Decision**: Store corrections for future improvement
**Reasoning**:
- Reduces questions in future sessions
- Improves confidence scores over time
- Creates personalized models per party

---

## Code Review Findings

*To be completed after implementation*

---

## Status Tracking

### Phase 1: Core Infrastructure
- [ ] Create InteractiveClarifier class
- [ ] Add configuration support
- [ ] Write unit tests
- [ ] Document API

### Phase 2: Pipeline Integration
- [ ] Modify diarizer for clarification
- [ ] Modify party config for mapping
- [ ] Update pipeline to pass clarifier
- [ ] Write integration tests

### Phase 3: UI Integration
- [ ] Add WebSocket support to AppManager
- [ ] Create ClarificationChat component
- [ ] Integrate with Process Session tab
- [ ] Test real-time communication

### Phase 4: Learning System
- [ ] Implement embedding updates
- [ ] Add speaker mapping storage
- [ ] Track learning metrics
- [ ] Validate accuracy improvements

### Phase 5: Testing & Polish
- [ ] Complete test coverage (>85%)
- [ ] Performance testing
- [ ] Error handling
- [ ] Documentation
- [ ] User guide

---

**Last Updated**: 2025-11-18
**Next Review**: After Phase 1 completion
