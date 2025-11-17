"""
Conversation persistence and management.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import filelock

logger = logging.getLogger("DDSessionProcessor.conversation_store")

# Valid conversation ID pattern: conv_[8 hex chars]
CONVERSATION_ID_PATTERN = re.compile(r'^conv_[0-9a-f]{8}$')

# Conversation schema for validation
CONVERSATION_SCHEMA = {
    "required_keys": ["conversation_id", "created_at", "updated_at", "messages", "context"],
    "message_keys": ["id", "role", "content", "timestamp"],
    "context_keys": ["campaign", "relevant_sessions"]
}


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

        # Create locks directory for file locking
        self.locks_dir = self.conversations_dir / ".locks"
        self.locks_dir.mkdir(exist_ok=True)

        logger.info(f"Initialized ConversationStore at {self.conversations_dir}")

    def _validate_conversation_id(self, conversation_id: str) -> bool:
        """
        Validate conversation ID format to prevent path traversal.

        Args:
            conversation_id: Conversation ID to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If conversation ID is invalid
        """
        if not conversation_id:
            raise ValueError("Conversation ID cannot be empty")

        if not CONVERSATION_ID_PATTERN.match(conversation_id):
            raise ValueError(
                f"Invalid conversation ID format: {conversation_id}. "
                f"Must match pattern: conv_[8 hex chars]"
            )

        # Additional check: ensure the ID doesn't contain path separators
        if '/' in conversation_id or '\\' in conversation_id or '..' in conversation_id:
            raise ValueError(f"Conversation ID contains invalid characters: {conversation_id}")

        return True

    def _validate_conversation_data(self, conversation: Dict) -> bool:
        """
        Validate conversation data structure.

        Args:
            conversation: Conversation dict to validate

        Returns:
            True if valid

        Raises:
            ValueError: If conversation data is invalid
        """
        # Check required top-level keys
        for key in CONVERSATION_SCHEMA["required_keys"]:
            if key not in conversation:
                raise ValueError(f"Missing required key in conversation: {key}")

        # Validate messages structure
        if not isinstance(conversation["messages"], list):
            raise ValueError("Messages must be a list")

        for i, msg in enumerate(conversation["messages"]):
            if not isinstance(msg, dict):
                raise ValueError(f"Message {i} is not a dict")

            for key in CONVERSATION_SCHEMA["message_keys"]:
                if key not in msg:
                    raise ValueError(f"Message {i} missing required key: {key}")

            # Validate role
            if msg["role"] not in ["user", "assistant", "system"]:
                raise ValueError(f"Invalid role in message {i}: {msg['role']}")

        # Validate context structure
        if not isinstance(conversation["context"], dict):
            raise ValueError("Context must be a dict")

        for key in CONVERSATION_SCHEMA["context_keys"]:
            if key not in conversation["context"]:
                raise ValueError(f"Missing required key in context: {key}")

        return True

    def _get_lock_path(self, conversation_id: str) -> Path:
        """Get the lock file path for a conversation."""
        return self.locks_dir / f"{conversation_id}.lock"

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
        # Validate conversation ID to prevent path traversal
        self._validate_conversation_id(conversation_id)

        # Validate role
        if role not in ["user", "assistant", "system"]:
            raise ValueError(f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'")

        # Use file locking to prevent race conditions
        lock_path = self._get_lock_path(conversation_id)
        lock = filelock.FileLock(lock_path, timeout=10)

        try:
            with lock:
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
        except filelock.Timeout:
            logger.error(f"Timeout acquiring lock for conversation {conversation_id}")
            raise RuntimeError(f"Could not acquire lock for conversation {conversation_id}")

    def load_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Load a conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation dict or None if not found
        """
        # Validate conversation ID to prevent path traversal
        try:
            self._validate_conversation_id(conversation_id)
        except ValueError as e:
            logger.error(f"Invalid conversation ID: {e}")
            return None

        conversation_file = self.conversations_dir / f"{conversation_id}.json"

        # Additional security check: ensure the resolved path is within conversations_dir
        try:
            conversation_file = conversation_file.resolve()
            if not str(conversation_file).startswith(str(self.conversations_dir.resolve())):
                logger.error(f"Path traversal attempt detected: {conversation_id}")
                return None
        except Exception as e:
            logger.error(f"Error resolving path for conversation {conversation_id}: {e}")
            return None

        if not conversation_file.exists():
            logger.warning(f"Conversation file not found: {conversation_file}")
            return None

        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                conversation = json.load(f)

            # Validate loaded data
            self._validate_conversation_data(conversation)

            return conversation
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading conversation {conversation_id}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid conversation data in {conversation_id}: {e}")
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

    def rename_conversation(self, conversation_id: str, new_campaign_name: str) -> bool:
        """
        Rename a conversation by updating its campaign name.

        Args:
            conversation_id: Conversation ID
            new_campaign_name: New campaign name

        Returns:
            True if renamed successfully, False otherwise
        """
        # Validate conversation ID to prevent path traversal
        try:
            self._validate_conversation_id(conversation_id)
        except ValueError as e:
            logger.error(f"Invalid conversation ID for rename: {e}")
            return False

        # Validate new name
        if not new_campaign_name or not new_campaign_name.strip():
            logger.error("Campaign name cannot be empty")
            return False

        # Sanitize campaign name (limit length, remove problematic characters)
        new_campaign_name = new_campaign_name.strip()[:100]

        # Use file locking to prevent race conditions
        lock_path = self._get_lock_path(conversation_id)
        lock = filelock.FileLock(lock_path, timeout=10)

        try:
            with lock:
                conversation = self.load_conversation(conversation_id)
                if not conversation:
                    logger.warning(f"Cannot rename, conversation not found: {conversation_id}")
                    return False

                # Update campaign name
                conversation["context"]["campaign"] = new_campaign_name
                conversation["updated_at"] = datetime.now().isoformat()

                self._save_conversation(conversation_id, conversation)
                logger.info(f"Renamed conversation {conversation_id} to '{new_campaign_name}'")

            return True
        except filelock.Timeout:
            logger.error(f"Timeout acquiring lock for rename: {conversation_id}")
            return False
        except Exception as e:
            logger.error(f"Error renaming conversation {conversation_id}: {e}")
            return False

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        # Validate conversation ID to prevent path traversal
        try:
            self._validate_conversation_id(conversation_id)
        except ValueError as e:
            logger.error(f"Invalid conversation ID for deletion: {e}")
            return False

        conversation_file = self.conversations_dir / f"{conversation_id}.json"

        # Security check: ensure the resolved path is within conversations_dir
        try:
            conversation_file = conversation_file.resolve()
            if not str(conversation_file).startswith(str(self.conversations_dir.resolve())):
                logger.error(f"Path traversal attempt detected in delete: {conversation_id}")
                return False
        except Exception as e:
            logger.error(f"Error resolving path for deletion {conversation_id}: {e}")
            return False

        if not conversation_file.exists():
            logger.warning(f"Cannot delete, conversation not found: {conversation_id}")
            return False

        # Use file locking to prevent race conditions during deletion
        lock_path = self._get_lock_path(conversation_id)
        lock = filelock.FileLock(lock_path, timeout=10)

        try:
            with lock:
                conversation_file.unlink()
                logger.info(f"Deleted conversation: {conversation_id}")

            # Clean up lock file AFTER releasing the lock
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except (OSError, IOError) as e:
                # Log but don't fail if we can't delete the lock file
                logger.debug(f"Could not delete lock file for {conversation_id}: {e}")

            return True
        except filelock.Timeout:
            logger.error(f"Timeout acquiring lock for deletion: {conversation_id}")
            return False
        except IOError as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            return False

    def _save_conversation(self, conversation_id: str, conversation: Dict):
        """
        Save conversation to disk.

        Note: This method should only be called from within a file lock context.
        """
        # Validate conversation ID (this is called from locked contexts, but double-check)
        self._validate_conversation_id(conversation_id)

        # Validate conversation data before saving
        self._validate_conversation_data(conversation)

        conversation_file = self.conversations_dir / f"{conversation_id}.json"

        # Security check: ensure the resolved path is within conversations_dir
        try:
            conversation_file = conversation_file.resolve()
            if not str(conversation_file).startswith(str(self.conversations_dir.resolve())):
                raise ValueError(f"Path traversal attempt detected in save: {conversation_id}")
        except Exception as e:
            logger.error(f"Error resolving path for save {conversation_id}: {e}")
            raise

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
        # Validate conversation ID
        try:
            self._validate_conversation_id(conversation_id)
        except ValueError as e:
            logger.error(f"Invalid conversation ID in get_chat_history: {e}")
            return []

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
