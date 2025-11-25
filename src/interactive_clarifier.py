
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

# Set up a logger for this module
_logger = logging.getLogger(__name__)


@dataclass(order=True)
class ClarificationRequest:
    """A request for clarification from the user."""
    priority: int
    question: str
    item_id: str = field(compare=False)
    context: Dict[str, Any] = field(compare=False, default_factory=dict)
    response: Optional[Union[str, bool]] = field(compare=False, default=None)
    timestamp: float = field(compare=False, default_factory=time.time)
    event: threading.Event = field(
        compare=False, default_factory=threading.Event)


class InteractiveClarifier:
    """
    Manages interactive clarification requests during pipeline processing.

    This class is thread-safe.
    """

    def __init__(self, timeout: int = 30, max_questions: int = 10):
        self.requests: Dict[str, ClarificationRequest] = {}
        self.lock = threading.Lock()
        self.timeout = timeout
        self.max_questions = max_questions

    def ask_question(self, question: str, priority: int, item_id: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Asks a question and blocks until a response is received or it times out.

        Args:
            question: The question to ask the user.
            priority: The priority of the question (lower number is higher priority).
            item_id: A unique identifier for the item being clarified.
            context: Additional context for the question.

        Returns:
            The user's response, or None if the request times out.
        """
        request = None
        with self.lock:
            if len(self.requests) >= self.max_questions:
                _logger.warning(
                    "Question limit (%s) reached. Skipping new question: %s",
                    self.max_questions, question
                )
                return None

            request = ClarificationRequest(
                priority=priority, question=question, item_id=item_id, context=context or {})
            self.requests[item_id] = request

        try:
            # Wait for the event to be set, with a timeout
            event_was_set = request.event.wait(timeout=self.timeout)
            if event_was_set:
                return request.response
            else:
                # Handle timeout explicitly
                _logger.warning("Question timed out for item_id: %s", item_id)
                return None
        finally:
            # CRITICAL: Ensure the request is always removed to prevent memory leaks
            with self.lock:
                self.requests.pop(item_id, None)

    def submit_response(self, item_id: str, response: Any):
        """
        Submits a response from the user for a pending question.

        Args:
            item_id: The unique identifier of the item.
            response: The user's response.
        """
        with self.lock:
            if item_id in self.requests:
                request = self.requests[item_id]
                request.response = response
                request.event.set()
            else:
                _logger.warning(
                    "Received a response for an unknown or timed-out item_id: %s", item_id)

    def get_sorted_questions(self) -> List[ClarificationRequest]:
        """
        Returns a list of all pending clarification requests, sorted by priority.

        This is intended for the UI to display questions to the user.
        """
        with self.lock:
            # Return a sorted copy to avoid race conditions during iteration
            return sorted(list(self.requests.values()))
