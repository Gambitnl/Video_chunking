import logging
import pytest
import json
from pathlib import Path
from src.langchain.conversation_store import ConversationStore

@pytest.fixture
def conversation_store(tmp_path):
    """Create a ConversationStore instance in a temporary directory."""
    return ConversationStore(tmp_path)

def test_conversation_store_init(tmp_path):
    store = ConversationStore(tmp_path)
    assert store.conversations_dir.exists()
    assert store.locks_dir.exists()

def test_validate_conversation_id_valid(conversation_store):
    assert conversation_store._validate_conversation_id("conv_12345678")

def test_validate_conversation_id_invalid(conversation_store):
    with pytest.raises(ValueError):
        conversation_store._validate_conversation_id("")
    with pytest.raises(ValueError):
        conversation_store._validate_conversation_id("invalid_id")
    with pytest.raises(ValueError):
        conversation_store._validate_conversation_id("conv_12345678/")

def test_validate_conversation_data_valid(conversation_store):
    valid_data = {
        "conversation_id": "conv_12345678",
        "created_at": "2025-11-02T12:00:00",
        "updated_at": "2025-11-02T12:00:00",
        "messages": [
            {
                "id": "msg_123",
                "role": "user",
                "content": "Hello",
                "timestamp": "2025-11-02T12:00:00"
            }
        ],
        "context": {
            "campaign": "Test Campaign",
            "relevant_sessions": []
        }
    }
    assert conversation_store._validate_conversation_data(valid_data)

def test_validate_conversation_data_invalid(conversation_store):
    invalid_data = {"conversation_id": "conv_12345678"}
    with pytest.raises(ValueError):
        conversation_store._validate_conversation_data(invalid_data)

def test_create_conversation(conversation_store):
    conversation_id = conversation_store.create_conversation("Test Campaign")
    assert conversation_id.startswith("conv_")
    conv_file = conversation_store.conversations_dir / f"{conversation_id}.json"
    assert conv_file.exists()
    with open(conv_file, "r") as f:
        data = json.load(f)
    assert data["conversation_id"] == conversation_id
    assert data["context"]["campaign"] == "Test Campaign"

def test_add_message(conversation_store):
    conversation_id = conversation_store.create_conversation()
    message = conversation_store.add_message(conversation_id, "user", "Hello")
    assert message["role"] == "user"
    assert message["content"] == "Hello"
    conversation = conversation_store.load_conversation(conversation_id)
    assert len(conversation["messages"]) == 1
    assert conversation["messages"][0]["content"] == "Hello"

def test_add_message_with_sources(conversation_store):
    conversation_id = conversation_store.create_conversation()
    sources = [{"metadata": {"session_id": "sess1"}}]
    conversation_store.add_message(conversation_id, "assistant", "Response", sources)
    conversation = conversation_store.load_conversation(conversation_id)
    assert "sess1" in conversation["context"]["relevant_sessions"]

def test_add_message_to_nonexistent_conversation(conversation_store):
    with pytest.raises(ValueError):
        conversation_store.add_message("conv_nonexistent", "user", "Hello")

def test_load_conversation(conversation_store):
    conversation_id = conversation_store.create_conversation()
    conversation = conversation_store.load_conversation(conversation_id)
    assert conversation["conversation_id"] == conversation_id

def test_load_nonexistent_conversation(conversation_store):
    conversation = conversation_store.load_conversation("conv_nonexistent")
    assert conversation is None

def test_list_conversations(conversation_store):
    conv1 = conversation_store.create_conversation()
    conv2 = conversation_store.create_conversation()
    conversations = conversation_store.list_conversations()
    assert len(conversations) == 2
    assert {c["conversation_id"] for c in conversations} == {conv1, conv2}

def test_delete_conversation(conversation_store):
    conversation_id = conversation_store.create_conversation()
    assert conversation_store.delete_conversation(conversation_id)
    assert not (conversation_store.conversations_dir / f"{conversation_id}.json").exists()

def test_delete_nonexistent_conversation(conversation_store):
    assert not conversation_store.delete_conversation("conv_nonexistent")

def test_get_chat_history(conversation_store):
    conversation_id = conversation_store.create_conversation()
    conversation_store.add_message(conversation_id, "user", "Hello")
    history = conversation_store.get_chat_history(conversation_id)
    assert history == [{"role": "user", "content": "Hello"}]

def test_get_chat_history_nonexistent(conversation_store):
    history = conversation_store.get_chat_history("conv_nonexistent")
    assert history == []

def test_rename_conversation(conversation_store):
    """Test renaming a conversation updates the campaign name."""
    conversation_id = conversation_store.create_conversation("Original Campaign")

    # Rename the conversation
    assert conversation_store.rename_conversation(conversation_id, "New Campaign Name")

    # Verify the campaign name was updated
    conversation = conversation_store.load_conversation(conversation_id)
    assert conversation["context"]["campaign"] == "New Campaign Name"

def test_rename_conversation_nonexistent(conversation_store):
    """Test renaming a nonexistent conversation returns False."""
    assert not conversation_store.rename_conversation("conv_nonexistent", "New Name")

def test_rename_conversation_empty_name(conversation_store):
    """Test renaming with empty name returns False."""
    conversation_id = conversation_store.create_conversation()
    assert not conversation_store.rename_conversation(conversation_id, "")
    assert not conversation_store.rename_conversation(conversation_id, "   ")

def test_rename_conversation_long_name(conversation_store):
    """Test renaming with a very long name truncates to 100 chars."""
    conversation_id = conversation_store.create_conversation()
    long_name = "A" * 200

    assert conversation_store.rename_conversation(conversation_id, long_name)

    conversation = conversation_store.load_conversation(conversation_id)
    assert len(conversation["context"]["campaign"]) == 100
    assert conversation["context"]["campaign"] == "A" * 100


@pytest.mark.parametrize(
    "corruption_content",
    [
        "not valid json",
        "{'key': 'value'",
        "",
    ],
)
def test_load_conversation_corrupted_file_quarantined(
    conversation_store, caplog, corruption_content
):
    """Corrupted JSON should be quarantined and return None without raising."""

    conversation_id = conversation_store.create_conversation()
    conversation_file = conversation_store.conversations_dir / f"{conversation_id}.json"
    conversation_file.write_text(corruption_content, encoding="utf-8")

    caplog.set_level(logging.ERROR)
    result = conversation_store.load_conversation(conversation_id)

    assert result is None
    assert not conversation_file.exists()

    quarantined_files = list(
        conversation_store.conversations_dir.glob(f"{conversation_id}.corrupted*")
    )
    assert len(quarantined_files) == 1
    assert "Error loading conversation" in caplog.text
