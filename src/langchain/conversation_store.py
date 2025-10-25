"""
Conversation persistence and management.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("DDSessionProcessor.conversation_store")


class ConversationStore:
    """Save and load conversation history."""

    def __init__(self, conversations_dir: Path):
        """
        Initialize the conversation store.

        Args:
            conversations_dir: Directory to store conversation JSON files
        """
        self.conversations_dir = Path(conversations_dir)
        self.conversations_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized ConversationStore at {self.conversations_dir}")

    def create_conversation(self, campaign: str = None) -> str:
        """
        Create a new conversation.

        Args:
            campaign: Optional campaign name

        Returns:
            Conversation ID
        """
        conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()

        conversation = {
            "conversation_id": conversation_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": [],
            "context": {
                "campaign": campaign or "Unknown",
                "relevant_sessions": []
            }
        }

        self._save_conversation(conversation_id, conversation)
        logger.info(f"Created new conversation: {conversation_id}")

        return conversation_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: List[Dict] = None
    ) -> Dict:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content
            sources: Optional list of source documents (for assistant messages)

        Returns:
            The message dict that was added
        """
        conversation = self.load_conversation(conversation_id)

        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")

        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()

        message = {
            "id": message_id,
            "role": role,
            "content": content,
            "timestamp": timestamp
        }

        if sources:
            message["sources"] = sources

            # Update relevant sessions
            for source in sources:
                session_id = source.get("metadata", {}).get("session_id")
                if session_id and session_id not in conversation["context"]["relevant_sessions"]:
                    conversation["context"]["relevant_sessions"].append(session_id)

        conversation["messages"].append(message)
        conversation["updated_at"] = timestamp

        self._save_conversation(conversation_id, conversation)
        logger.debug(f"Added {role} message to conversation {conversation_id}")

        return message

    def load_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Load a conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation dict or None if not found
        """
        conversation_file = self.conversations_dir / f"{conversation_id}.json"

        if not conversation_file.exists():
            logger.warning(f"Conversation file not found: {conversation_file}")
            return None

        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading conversation {conversation_id}: {e}")
            return None

    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """
        List all conversations, sorted by most recent.

        Args:
            limit: Maximum number of conversations to return

        Returns:
            List of conversation metadata dicts
        """
        conversations = []

        for conv_file in self.conversations_dir.glob("conv_*.json"):
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    conv = json.load(f)

                # Extract metadata
                conversations.append({
                    "conversation_id": conv["conversation_id"],
                    "created_at": conv["created_at"],
                    "updated_at": conv["updated_at"],
                    "message_count": len(conv.get("messages", [])),
                    "campaign": conv.get("context", {}).get("campaign", "Unknown")
                })
            except (json.JSONDecodeError, KeyError, IOError) as e:
                logger.warning(f"Error loading conversation file {conv_file}: {e}")
                continue

        # Sort by updated_at descending
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)

        return conversations[:limit]

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        conversation_file = self.conversations_dir / f"{conversation_id}.json"

        if not conversation_file.exists():
            logger.warning(f"Cannot delete, conversation not found: {conversation_id}")
            return False

        try:
            conversation_file.unlink()
            logger.info(f"Deleted conversation: {conversation_id}")
            return True
        except IOError as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            return False

    def _save_conversation(self, conversation_id: str, conversation: Dict):
        """Save conversation to disk."""
        conversation_file = self.conversations_dir / f"{conversation_id}.json"

        try:
            with open(conversation_file, "w", encoding="utf-8") as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Error saving conversation {conversation_id}: {e}")
            raise

    def get_chat_history(self, conversation_id: str) -> List[Dict]:
        """
        Get chat history in Gradio chatbot format.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of messages in format expected by Gradio Chatbot
        """
        conversation = self.load_conversation(conversation_id)

        if conversation is None:
            return []

        # Convert to Gradio format (list of dicts with 'role' and 'content')
        return [
            {
                "role": msg["role"],
                "content": msg["content"]
            }
            for msg in conversation.get("messages", [])
        ]
