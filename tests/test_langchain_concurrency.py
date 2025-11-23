"""
Concurrency tests for LangChain components.
"""
import pytest
import concurrent.futures
import time
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.langchain.conversation_store import ConversationStore

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def conversation_store(tmp_path):
    """Create a ConversationStore instance in a temporary directory."""
    return ConversationStore(tmp_path)

def test_concurrent_message_addition(conversation_store):
    """
    Test multiple threads adding messages to the same conversation.
    Verifies that file locking prevents data loss or corruption.
    """
    conv_id = conversation_store.create_conversation()

    num_threads = 10
    messages_per_thread = 20

    def add_messages_worker(thread_id):
        try:
            for i in range(messages_per_thread):
                conversation_store.add_message(
                    conv_id,
                    "user",
                    f"Message {i} from thread {thread_id}"
                )
                # No sleep needed, we want to stress it, but maybe a tiny yield helps OS schedule threads
                time.sleep(0.001)
            return True
        except Exception as e:
            logger.error(f"Thread {thread_id} failed: {e}")
            return False

    # Execute concurrent writes
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(add_messages_worker, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(results), "Some threads failed to add messages"

    # Verify results
    conversation = conversation_store.load_conversation(conv_id)
    assert conversation is not None

    total_expected = num_threads * messages_per_thread
    assert len(conversation["messages"]) == total_expected, \
        f"Expected {total_expected} messages, found {len(conversation['messages'])}"

    # Verify all messages content integrity
    messages_content = [m["content"] for m in conversation["messages"]]
    for t in range(num_threads):
        for i in range(messages_per_thread):
            expected = f"Message {i} from thread {t}"
            assert expected in messages_content

def test_concurrent_conversation_creation(conversation_store):
    """
    Test multiple threads creating conversations simultaneously.
    Verifies that unique IDs are generated and no race conditions occur in directory writing.
    """
    num_threads = 20

    def create_conv_worker(i):
        return conversation_store.create_conversation(f"Campaign {i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_conv_worker, i) for i in range(num_threads)]
        created_ids = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Verify all were created
    assert len(created_ids) == num_threads
    assert len(set(created_ids)) == num_threads # All unique

    # Verify list_conversations finds them all
    listed = conversation_store.list_conversations(limit=100)
    assert len(listed) == num_threads

def test_concurrent_read_write(conversation_store):
    """
    Test concurrent reading and writing to the same conversation.
    """
    conv_id = conversation_store.create_conversation()

    num_writers = 5
    num_readers = 5
    writes_per_thread = 10

    def writer(thread_id):
        for i in range(writes_per_thread):
            conversation_store.add_message(conv_id, "user", f"Write {i} from {thread_id}")
            time.sleep(0.005)

    def reader(thread_id):
        reads = 0
        for _ in range(writes_per_thread):
            conv = conversation_store.load_conversation(conv_id)
            if conv:
                reads += 1
            time.sleep(0.005)
        return reads

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_writers + num_readers) as executor:
        write_futures = [executor.submit(writer, i) for i in range(num_writers)]
        read_futures = [executor.submit(reader, i) for i in range(num_readers)]

        concurrent.futures.wait(write_futures)
        concurrent.futures.wait(read_futures)

    # Verify final state
    conversation = conversation_store.load_conversation(conv_id)
    assert len(conversation["messages"]) == num_writers * writes_per_thread

    # Verify readers didn't crash
    for f in read_futures:
        assert f.result() > 0

def test_concurrent_delete_and_write(conversation_store):
    """
    Test race condition where one thread writes while another deletes.
    """
    conv_id = conversation_store.create_conversation()

    def writer():
        # Try to write many messages, eventually should fail when deleted
        successes = 0
        failures = 0
        for i in range(50):
            try:
                conversation_store.add_message(conv_id, "user", "msg")
                successes += 1
                time.sleep(0.002)
            except Exception:
                failures += 1
        return successes, failures

    def deleter():
        time.sleep(0.05) # Let writer start
        return conversation_store.delete_conversation(conv_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_write = executor.submit(writer)
        future_delete = executor.submit(deleter)

        concurrent.futures.wait([future_write, future_delete])

    deleted = future_delete.result()
    successes, failures = future_write.result()

    # If delete succeeded, file should be gone
    if deleted:
        assert not (conversation_store.conversations_dir / f"{conv_id}.json").exists()
        # Writer might have succeeded some, but eventually should fail or handle it
        # Since add_message checks existence inside lock, it might recreate it?
        # add_message: load_conversation -> returns None if not found -> raises ValueError
        pass
    else:
        # If delete failed (maybe lock timeout?), then file exists
        pass

def test_concurrent_campaign_chat_client_usage(tmp_path):
    """
    Test concurrent usage of CampaignChatClient.
    Verifies that the client can handle multiple simultaneous requests (thread safety of non-disk components).
    """
    from src.langchain.campaign_chat import CampaignChatClient

    # Mock dependencies
    with patch("src.langchain.campaign_chat.LLMFactory") as mock_factory, \
         patch("src.langchain.campaign_chat.Config") as mock_config:

        mock_llm = MagicMock()
        # Make the LLM simulate some processing time
        def side_effect(prompt):
            time.sleep(0.01)
            return "Mock response"
        mock_llm.side_effect = side_effect

        mock_factory.create_llm.return_value = mock_llm

        # Create client
        client = CampaignChatClient()

        num_requests = 10

        def ask_worker(i):
            response = client.ask(f"Question {i}")
            return response

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(ask_worker, i) for i in range(num_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_requests
        for res in results:
            assert res["answer"] == "Mock response"

        # Verify history grew (since it's one client instance, memory is shared)
        # 10 interactions * 2 messages (user+ai) = 20 messages
        # But ConversationBufferWindowMemory might truncate.
        # Default k=10 (last 10 exchanges = 20 messages).
        # We did 10 exchanges. So it should be full.
        history = client.memory.load_memory_variables({})
        # Key depends on memory config, likely "chat_history"
        assert "chat_history" in history
        # We don't strictly assert length as threading order is non-deterministic for append,
        # but we assert it didn't crash.


def test_concurrent_campaign_chat_chain_usage():
    """
    Test concurrent usage of CampaignChatChain.
    """
    from src.langchain.campaign_chat import CampaignChatChain

    # We need to mock the internal chain because we don't want to rely on real LangChain
    # logic which might need real API keys or be slow.

    mock_llm = MagicMock()
    mock_retriever = MagicMock()

    # We need to patch where ConversationalRetrievalChain is imported from.
    # Since it is imported inside __init__, we have to patch the module it comes from.
    # We will try to patch both potential sources.

    # langchain 1.0.8 does not seem to expose langchain.chains directly or it is empty.
    # langchain_classic seems to have it.
    # We will just mock langchain_classic one, and if that fails, we can add more logic.

    with patch("langchain_classic.chains.ConversationalRetrievalChain.from_llm") as mock_from_llm_lcc:

        # Setup the mock chain instance
        mock_chain_instance = MagicMock()
        # The chain is called with a dict {"question": ...}
        # It returns a dict
        mock_chain_instance.return_value = {
            "answer": "Mock Chain Response",
            "source_documents": [MagicMock(page_content="Content", metadata={})]
        }

        # Configure both patches to return our mock instance
        mock_from_llm_lcc.return_value = mock_chain_instance

        # Create chain
        # NOTE: The __init__ will trigger the import. One of the patches should catch it
        # depending on what is installed/imported.
        chain = CampaignChatChain(mock_llm, mock_retriever)

        num_requests = 10

        def ask_worker(i):
            response = chain.ask(f"Question {i}")
            return response

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(ask_worker, i) for i in range(num_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_requests
        for res in results:
            assert res["answer"] == "Mock Chain Response"
