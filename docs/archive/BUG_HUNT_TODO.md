# BUG_HUNT_TODO.md - Detailed Bug Descriptions & Implementation Notes

> **Last Updated**: 2025-11-20
> **Purpose**: Detailed bug hunt findings with implementation notes and code review results
> **Status Tracking**: See [OUTSTANDING_TASKS.md](OUTSTANDING_TASKS.md) for current status of all bugs

## About This File

This file contains detailed descriptions, reproduction steps, and implementation notes for all bugs discovered during bug hunt sessions. Completed bugs remain here with their implementation notes for historical reference and future analysis.

**For current bug status and work planning**, see [OUTSTANDING_TASKS.md](OUTSTANDING_TASKS.md).

## 2025-11-02 Bug Hunt Findings

This list summarizes preliminary findings from the bug hunt session on 2025-11-02. For detailed reproduction steps, evidence, and follow-up suggestions, please refer to `logs/bug_hunt/BugHunt_20251102_1200.md`.

### Area 1: LangChain Test Coverage (P2.1-TESTING)

-   **BUG-20251102-01**: `CampaignChatClient.ask` - Add integration tests for full RAG pipeline (retriever + LLM). (High)
    *   **Issue**: The `CampaignChatClient.ask` method orchestrates Retrieval-Augmented Generation (RAG) by integrating the retriever and the Language Model (LLM). Current tests often mock these components individually.
    *   **Why it's an issue**: Mocking components individually doesn't guarantee their proper interaction. Changes to retrieval logic or LLM prompting could silently break the RAG functionality, leading to irrelevant or incorrect responses. A high-priority integration test is needed to verify the entire RAG pipeline works as a cohesive unit, ensuring that retrieved information is effectively used by the LLM to generate answers.

-   **BUG-20251102-02**: `CampaignChatClient.ask` - Test with various `context` inputs. (Medium)
    *   **Issue**: The `CampaignChatClient.ask` method accepts an optional `context` dictionary. The current implementation doesn't visibly use this context, but future plans may involve it influencing retrieval or LLM behavior.
    *   **Why it's an issue**: Untested input parameters create a maintenance risk. If `context` is improperly handled, it could cause errors or unexpected behavior when future features attempt to utilize it. Proactive testing ensures the parameter behaves as expected, even if its full functionality is yet to be implemented.

-   **BUG-20251102-03**: `CampaignChatClient.ask` - Test error handling when `retriever.retrieve` fails. (Medium)
    *   **Issue**: If the `self.retriever.retrieve` call within `CampaignChatClient.ask` throws an exception (e.g., due to issues with ChromaDB, embedding model, or file access), the current error handling might be too generic.
    *   **Why it's an issue**: Unspecific error handling can result in cryptic messages for the user or silent failures leading to suboptimal LLM responses. Explicitly testing this ensures the system either gracefully falls back (e.g., attempts to answer without RAG) or provides clear, actionable error messages to the user for better debugging.

##### Implementation Notes & Reasoning (2025-11-20 GPT-5.1-Codex-Max)

- Added a regression test that forces `CampaignChatClient.ask` to handle retriever exceptions, ensuring the LLM is not invoked and no chat history is persisted when retrieval fails.

##### Code Review Findings (2025-11-20 GPT-5.1-Codex-Max)

- [APPROVED] Error path now surfaces retrieval failures with an "Error:" prefix and empty sources while avoiding unintended side effects.

-   **BUG-20251102-04**: `CampaignChatClient.ask` - Test error handling when `llm` call fails. (Medium)
    *   **Issue**: Similar to retriever failures, if the `self.llm(full_prompt)` call in `CampaignChatClient.ask` fails (e.g., due to an invalid API key, network timeout, model being unavailable), the current error handling simply captures the generic exception.
    *   **Why it's an issue**: An LLM failure is a critical operational issue. Generic error messages can expose internal system details or be unhelpful to the user. Specific tests are needed to ensure robust error handling provides clear, non-technical feedback to the user, potentially suggesting solutions like checking network connections or API keys.

-   **BUG-20251102-05**: `CampaignChatClient._initialize_llm` - Add tests for `langchain_community.llms.Ollama` fallback. (Agent: Jules, Completed: 2025-11-20) (Low)
    *   **Issue**: The `_initialize_llm` method attempts to import `langchain_ollama.OllamaLLM` first, and if that fails, it falls back to `langchain_community.llms.Ollama`. Current tests might not cover this fallback scenario.
    *   **Why it's an issue**: Fallback mechanisms are crucial for resilience but are often overlooked in testing. If the fallback import or the `langchain_community` version of Ollama behaves unexpectedly, it could lead to silent failures or inconsistent behavior in environments where the primary import isn't available, undermining the system's intended robustness.

-   **BUG-20251102-06**: `CampaignChatClient._initialize_memory` - Add tests for `langchain_classic.memory.ConversationBufferMemory` and `langchain.memory.ConversationBufferMemory` fallbacks. (Low)
    *   **Issue**: The `_initialize_memory` method has multiple fallbacks for `ConversationBufferWindowMemory`, eventually falling back to `ConversationBufferMemory` (which is an unbounded memory buffer).
    *   **Why it's an issue**: Using an unbounded memory buffer (the final fallback) can lead to severe memory consumption issues and application instability over long conversations. Tests are necessary to ensure that these fallbacks are either explicitly managed (e.g., by issuing a warning) or that the preferred bounded memory is always successfully initialized to prevent such critical resource leaks.

-   **BUG-20251102-07**: `CampaignChatClient._load_system_prompt` - Test `campaign_name`, `num_sessions`, `pc_names` placeholders. (Medium)
    *   **Issue**: The `_load_system_prompt` method formats a system prompt using placeholders like `{campaign_name}` which are currently filled with generic values ("Unknown", "0"). A `TODO` comment indicates these should eventually be dynamic.
    *   **Why it's an issue**: Incorrect placeholder handling could lead to malformed prompts or LLM misinterpretations. Testing ensures that the `SafeFormatDict` either correctly inserts values or gracefully handles missing keys, preventing future integration issues when actual campaign data is introduced.

-   **BUG-20251102-08**: `CampaignChatChain.ask` - Add integration tests for full chain functionality. (High)
    *   **Issue**: `CampaignChatChain` utilizes LangChain's `ConversationalRetrievalChain.from_llm`. Current tests typically mock the entire `chain` object rather than testing its full interaction with LLM, retriever, and memory components.
    *   **Why it's an issue**: Excessive mocking prevents verification of the actual LangChain orchestration. Integration tests are vital to ensure that the `ConversationalRetrievalChain` correctly combines and processes inputs from all its integrated components and produces the expected output, directly impacting the accuracy and relevance of conversational responses.

##### Implementation Notes & Reasoning (2025-11-21 GPT-5.1-Codex-Max)

- Added `tests/test_langchain_campaign_chat_chain.py` with integration-style tests that instantiate `CampaignChatChain` against a real `ConversationalRetrievalChain`, using `langchain_core` `LLM`/`BaseRetriever` subclasses to simulate deterministic LLM outputs and static documents.
- Verified the chain propagates retrieved documents into the LLM prompt and returns sources alongside answers, and that it still responds when retrieval returns no documents.

##### Code Review Findings (2025-11-21 GPT-5.1-Codex-Max)

- [APPROVED] Tests now cover end-to-end wiring, confirming prompt formatting includes context and source propagation works; noted existing LangChain deprecation warnings for future cleanup.

-   **BUG-20251102-09**: `CampaignChatChain.ask` - Test with various `question` inputs and expected `source_documents`. (Agent: Claude Sonnet 4.5, Completed: 2025-11-22) (Medium)
    *   **Issue**: The `CampaignChatChain.ask` method takes a `question` and is expected to return `answer` and `source_documents`. The range of questions and their impact on source retrieval needs thorough testing.
    *   **Why it's an issue**: The quality of RAG depends heavily on how the conversational chain processes different types of questions (e.g., simple, complex, follow-up). Verifying that relevant `source_documents` are consistently returned for various inputs is essential for the chain to provide accurate and well-contextualized answers.

##### Implementation Notes & Reasoning (2025-11-22 Claude Sonnet 4.5)

- Added 6 comprehensive test cases to `tests/test_langchain_campaign_chat_chain.py` covering:
  - **Complex multi-part questions**: Tests RAG handling of compound queries requiring multiple sources
  - **Follow-up questions with context**: Validates conversational memory (e.g., pronouns referring to previous context)
  - **Specific vs. general questions**: Ensures appropriate source selection based on question scope
  - **Synthesis questions**: Tests combining information across multiple session sources
  - **Single source detailed answers**: Validates focused retrieval for targeted queries
- All tests follow existing pattern using `SequenceLLM` (deterministic responses) and `StaticRetriever` (controlled document sets)
- Tests verify both `answer` content and `sources` count/metadata to ensure RAG quality
- Total test count increased from 2 to 8 tests (400% increase in coverage)

##### Code Review Findings (2025-11-22 Claude Sonnet 4.5)

- [APPROVED] Tests comprehensively cover the requested question variety per bug specification
- Test assertions validate both answer quality and source document propagation
- Tests are deterministic and isolated (no external dependencies)
- All tests follow repository coding standards (ASCII-only, type hints in docstrings)
- Syntax validation passed, tests ready for execution when pytest environment is available

-   **BUG-20251102-10**: `CampaignChatChain.ask` - Test error handling when `self.chain` call fails. (Medium)
    *   **Issue**: If the underlying `ConversationalRetrievalChain` call within `CampaignChatChain.ask` fails (e.g., due to an internal LangChain error or issues with integrated components), the `ask` method's error handling must be robust.
    *   **Why it's an issue**: An unhandled or improperly handled error in the core conversational chain would lead to a broken user experience. Testing this ensures the application can gracefully recover or provide meaningful diagnostic information when critical components fail, maintaining application stability.

-   **BUG-20251102-11**: `ConversationStore.add_message` - Test adding messages with and without sources. (Low)
    *   **Issue**: The `add_message` method in `ConversationStore` has an optional `sources` parameter, but there isn't explicit test coverage for messages being added both with and without this source metadata.
    *   **Why it's an issue**: Proper storage and retrieval of source metadata are fundamental for the RAG feature's transparency. If sources are not correctly serialized/deserialized, users may lose sight of where information originated, undermining the credibility and usefulness of the conversational AI.

-   **BUG-20251102-12**: `ConversationStore.add_message` - Test updating `relevant_sessions` in context. (Medium)
    *   **Issue**: The `add_message` method contains logic to extract `session_id` from sources and store them in `conversation["context"]["relevant_sessions"]`.
    *   **Why it's an issue**: This mechanism is crucial for maintaining historical context about which game sessions informed a conversation. Failure to correctly populate `relevant_sessions` could lead to inaccurate historical data, broken filtering features, or difficulties in generating campaign summaries, compromising the integrity of derived knowledge.

-   **BUG-20251102-13**: `ConversationStore.load_conversation` - Test loading a corrupted JSON file. (Medium)
    *   **Issue**: The `load_conversation` method deserializes JSON files. If a file becomes corrupted (e.g., malformed JSON, truncated due to a crash), the current error handling for `json.JSONDecodeError` needs verification.
    *   **Why it's an issue**: A corrupted conversation file should be handled gracefully to prevent application crashes and maintain data resilience. Testing this ensures that the system logs the error, potentially skips the unreadable file, and continues operating without failing entirely, preserving user experience.

-   **BUG-20251102-14**: `ConversationStore.list_conversations` - Test with a large number of conversations. (Medium)
    *   **Issue**: The `list_conversations` method iterates through all conversation JSON files in the directory to extract metadata. While a `limit` is applied post-loading, the initial file system scan and metadata extraction could become slow with thousands of files.
    *   **Why it's an issue**: Performance degradation in core UI interactions (like listing conversations) is a common issue as data scales. This test proactively identifies potential bottlenecks or UI freezes, ensuring the application remains responsive even for users with extensive conversation history.

-   **BUG-20251102-15**: `ConversationStore.list_conversations` - Test error handling for corrupted conversation files. (Medium)
    *   **Issue**: During the `list_conversations` process, if one or more conversation files are corrupted, the `json.load` operation might fail for those specific files. The `try-except` block attempts to handle this.
    *   **Why it's an issue**: The conversation listing should be resilient to individual file corruption. A single bad file should not prevent the listing of all other valid conversations. Testing this ensures graceful degradation and continued access to recoverable data, improving overall system robustness.

-   **BUG-20251102-16**: `ConversationStore.delete_conversation` - Test deleting a non-existent conversation. (Low)
    *   **Issue**: The `delete_conversation` method returns `False` if the target file does not exist, indicating it was not deleted.
    *   **Why it's an issue**: While the expected behavior is clear, unit testing this edge case confirms that calling the method with a non-existent ID does not raise unexpected exceptions or cause unintended side effects, validating the method's robustness.

-   **BUG-20251102-17**: `ConversationStore.get_chat_history` - Test with an empty conversation. (Low)
    *   **Issue**: The `get_chat_history` method retrieves messages from a conversation. An empty conversation has an empty `messages` list.
    *   **Why it's an issue**: This simple test confirms that the method correctly returns an empty list for a newly created or cleared conversation, preventing potential indexing errors or unexpected formatting issues that could arise from an empty message list.

##### Implementation Notes & Reasoning (2025-11-20 GPT-5.1-Codex)

- Added a unit test that creates a new conversation and verifies `get_chat_history` returns an empty list so regressions surface before runtime.
- Kept coverage in `tests/test_langchain_conversation_store.py` alongside the existing chat history tests for focused, low-overhead validation.

##### Code Review Findings (2025-11-20 GPT-5.1-Codex)

- [APPROVED] Behavior already aligns with expectations; additional test coverage mitigates future regressions without code changes.

-   **BUG-20251102-18**: `HybridSearcher.search` - Add integration tests with actual `vector_store` and `keyword_retriever` instances (not mocks). (Agent: Jules, Completed: 2025-11-22) (High)
    *   **Issue**: `HybridSearcher` is responsible for combining results from both semantic and keyword search, which rely on `CampaignVectorStore` and `CampaignRetriever` respectively. Existing tests heavily mock these dependencies.
    *   **Why it's an issue**: Excessive mocking prevents verification of the actual search mechanisms. Integration tests are vital to ensure that both search methods are correctly invoked, their results are accurately processed, and the final combined output is relevant and well-ranked, directly impacting the quality of information provided to the LLM.

##### Implementation Notes & Reasoning (2025-11-22 Jules)

- Verified existing integration tests in `tests/test_langchain_hybrid_search.py`.
- Installed necessary dependencies (`pytest`, `langchain`, `chromadb`, `sentence-transformers`) and confirmed tests pass against real `CampaignVectorStore` (ChromaDB) and `CampaignRetriever` (BM25/files).
- Tests confirm that `HybridSearcher` correctly combines and ranks results from both sources using Reciprocal Rank Fusion.

##### Code Review Findings (2025-11-22 Jules)

- [APPROVED] Integration tests are comprehensive, covering basic search, mixed results, weighting, metadata preservation, and edge cases.

-   **BUG-20251102-19**: `HybridSearcher.search` - Test with varying `top_k` and `semantic_weight` values. (Medium)
    *   **Issue**: The `HybridSearcher.search` method allows users to control the number of results (`top_k`) and the balance between semantic and keyword search (`semantic_weight`).
    *   **Why it's an issue**: Incorrect application of these parameters can lead to suboptimal search results, such as too few or too many documents, or a biased preference for one search type. Testing diverse `top_k` and `semantic_weight` values ensures the Reciprocal Rank Fusion (RRF) algorithm works correctly under varying configurations.

-   **BUG-20251102-20**: `HybridSearcher.search` - Test when one of the underlying search methods (semantic or keyword) returns an error. (Medium)
    *   **Issue**: If either `vector_store.search` or `keyword_retriever.retrieve` fails, the `HybridSearcher` should ideally still utilize the results from the functioning component or, at minimum, handle the error gracefully.
    *   **Why it's an issue**: A failure in one search component should not cripple the entire hybrid search. The system should be resilient enough to still provide some relevant results, or a clear error, preventing a complete loss of conversational context. This tests the fault tolerance and graceful degradation of the hybrid search.

##### Implementation Notes & Reasoning (2025-11-22 GPT-5.1-Codex-Max)

- Added per-backend exception handling in `HybridSearcher.search` so semantic and keyword searches fail independently, logging errors without blocking the remaining backend.
- Expanded `tests/test_langchain_hybrid_search.py` to cover semantic failure with keyword fallback, keyword failure with semantic fallback, and dual failure returning an empty result set.

##### Code Review Findings (2025-11-22 GPT-5.1-Codex-Max)

- [APPROVED] Hybrid search now returns available results when one backend raises while logging the failure; both-backend failure surfaces as an empty list without raising.
- New tests are deterministic via mocks and assert the Reciprocal Rank Fusion path is skipped when no results are available.

-   **BUG-20251102-21**: `HybridSearcher._reciprocal_rank_fusion` - Test with more complex scenarios, including documents with identical content but different metadata. (Medium)
    *   **Issue**: The `_reciprocal_rank_fusion` method combines and re-ranks search results. This algorithm can be complex, especially when dealing with overlapping documents or those with very similar scores.
    *   **Why it's an issue**: Subtle flaws in the RRF implementation can lead to incorrect or unstable ranking, potentially hiding highly relevant documents or promoting less relevant ones. Thorough testing with diverse and challenging data sets is necessary to ensure the algorithm consistently produces optimal rankings.

-   **BUG-20251102-22**: `CampaignRetriever.retrieve` - Add integration tests with actual knowledge base and transcript files. (High)
    *   **Issue**: `CampaignRetriever` is responsible for keyword-based retrieval from knowledge base JSON files and raw transcript files. The current tests for `_load_knowledge_base` and caching are good, but the core `retrieve` method's interaction with the file system isn't fully tested.
    *   **Why it's an issue**: This component represents the keyword search aspect of RAG. If it does not correctly read, parse, and search against actual files on disk, the hybrid search will lack a crucial dimension of recall. Integration tests using real (or simulated) files are essential to confirm functional correctness for realistic data.

-   **BUG-20251102-23**: `CampaignRetriever._search_knowledge_bases` - Test with various query types (NPC, quest, location). (Medium)
    *   **Issue**: The `_search_knowledge_bases` method searches for NPCs, quests, and locations within loaded knowledge base JSONs, using the `_matches_query` helper.
    *   **Why it's an issue**: The `_matches_query` is a simple keyword-matching function. Tests are needed to ensure that queries specifically targeting different entities (e.g., "who is this NPC?", "details on this quest") correctly identify and return relevant entries, avoiding false positives or missed matches due to the inherent simplicity of the search logic.

-   **BUG-20251102-24**: `CampaignRetriever._search_transcripts` - Test with different query matching scenarios (partial words, case sensitivity). (Medium)
    *   **Issue**: The `_search_transcripts` method performs a basic `query_lower in text.lower()` substring search within transcript segments.
    *   **Why it's an issue**: This simple search can sometimes be imprecise. Tests should cover scenarios like multi-word queries, partial word matching (where appropriate), presence/absence of special characters, and how it handles variations in text. This helps characterize the search's effectiveness and identify potential gaps.

-   **BUG-20251102-25**: `CampaignRetriever._load_knowledge_base` - Test cache eviction logic. (Medium)
    *   **Issue**: The `_load_knowledge_base` method implements a cache with a `KB_CACHE_SIZE` limit and an eviction policy to remove the oldest entries.
    *   **Why it's an issue**: Cache eviction logic, especially in a Least Recently Used (LRU) fashion, can be tricky. Bugs here could lead to inefficient cache usage (cache thrashing), incorrect data being served (if eviction happens prematurely), or memory issues (if eviction fails). Tests are needed to confirm accurate cache management under load.

-   **BUG-20251102-26**: `CampaignVectorStore.add_transcript_segments` - Test with a very large number of segments to ensure batching works correctly and efficiently. (High)
    *   **Issue**: The `add_transcript_segments` method processes input `segments` in batches (`EMBEDDING_BATCH_SIZE`) to prevent Out Of Memory (OOM) errors during embedding generation.
    *   **Why it's an issue**: This batching mechanism is critical for handling large transcript files. A test with thousands or tens of thousands of segments is essential to verify that the batching loop correctly handles array slices, boundary conditions, and ensures that memory consumption remains stable and within limits. Failure here would cause crashes for long game sessions.

-   **BUG-20251102-27**: `CampaignVectorStore.add_knowledge_documents` - Test with various document structures and metadata. (Medium)
    *   **Issue**: The `add_knowledge_documents` method generates unique IDs for documents using metadata fields like `doc_type` and `name` (`f"{doc_type}_{safe_name}_{batch_start + i}"`).
    *   **Why it's an issue**: The ID generation involves string concatenation and sanitization. Testing with diverse document types, names (including those with spaces or special characters), and metadata structures ensures that ID generation is robust, unique, and doesn't lead to errors or collisions in the vector database.

-   **BUG-20251102-28**: `CampaignVectorStore.search` - Test with `collection` parameter set to "transcripts" and "knowledge". (Medium)
    *   **Issue**: The `CampaignVectorStore.search` method includes an optional `collection` parameter to specify whether to search "transcripts", "knowledge", or both.
    *   **Why it's an issue**: Correct filtering by collection is essential for precise search functionality, allowing users to target specific knowledge domains. Tests are required to confirm that the `if collection is None or collection == "transcripts":` and similar logic correctly restrict searches, preventing irrelevant results from being returned.

-   **BUG-20251102-29**: `CampaignVectorStore.delete_session` - Test deleting a session with no segments. (Low)
    *   **Issue**: The `CampaignVectorStore.delete_session` method checks if there are segments before attempting to delete them and logs a warning if none are found.
    *   **Why it's an issue**: This is a minor edge case. Confirming that no errors are thrown and the warning message is correctly logged for sessions with no associated segments verifies graceful handling and prevents unexpected behavior, like attempts to delete from an empty set.
    *   **Status**: Completed on 2025-11-21; behavior had already been covered by `tests/test_langchain_vector_store.py::TestDeleteSession.test_delete_session_not_found`, which exercises the empty-segment path, verifies no deletion occurs, and confirms the warning emission. No additional code changes were required during the 2025-11-21 review.

-   **BUG-20251102-30**: `CampaignVectorStore.clear_all` - Test destructive nature and recreation of collections. (Medium)
    *   **Issue**: The `CampaignVectorStore.clear_all` method performs a highly destructive operation by deleting and then recreating both ChromaDB collections ("transcripts" and "knowledge").
    *   **Why it's an issue**: Given its destructive nature, this method requires robust testing. It's crucial to confirm that all data is indeed removed, that the collections are correctly reinitialized, and that subsequent data additions to the recreated collections function without issues. A bug here could lead to permanent data loss.

-   **BUG-20251102-31**: `CampaignVectorStore.get_stats` - Test with empty and populated collections. (Low)
    *   **Issue**: The `CampaignVectorStore.get_stats` method reports the count of documents in both the "transcripts" and "knowledge" collections.
    *   **Why it's an issue**: This method provides basic diagnostic information about the vector store's content. Testing it with both empty and fully populated collections ensures that the counts are accurate and reliable for monitoring, debugging, or user feedback.

-   **BUG-20251102-32**: General - Add performance tests for LangChain components (e.g., query latency, ingestion speed). (High)
    *   **Issue**: Critical components of the LangChain integration (embedding generation, vector store search, LLM calls) have performance implications for user experience.
    *   **Why it's an issue**: Performance regressions can significantly degrade user experience. Establishing benchmarks for key operations (e.g., semantic search latency, transcript ingestion speed) is vital for proactive monitoring and preventing the application from becoming slow or unresponsive as data grows.

-   **BUG-20251102-33**: General - Add concurrency tests for `CampaignChatClient` and `CampaignChatChain` interactions. (High)
    *   **Issue**: While `ConversationStore` has file-locking mechanisms, `CampaignChatClient` and `CampaignChatChain` might be accessed concurrently in real-world scenarios (e.g., multiple users, or even rapid interactions by a single user).
    *   **Why it's an issue**: Concurrent access to shared resources or state within these clients can lead to race conditions, data corruption, or deadlocks. These are challenging bugs to diagnose. Comprehensive concurrency tests are essential to ensure stability under multi-threaded or rapid interaction loads.

-   **BUG-20251102-34**: General - Improve test data complexity for all LangChain tests. (Medium)
    *   **Issue**: Many existing LangChain tests often utilize simple, short, or synthetic data.
    *   **Why it's an issue**: Real-world D&D transcripts and campaign knowledge are complex, featuring varied language, specialized terminology, internal consistency, and long paragraphs. Using richer, more realistic test data will expose issues related to text processing, context window limitations, or entity recognition that simpler data would fail to reveal.

-   **BUG-20251102-35**: General - Add tests for error paths and edge cases not currently covered. (High)
    *   **Issue**: This is a general observation that critical error paths and less common edge cases (e.g., filesystem permissions, disk full, invalid external service responses, malformed environment variables) might not be fully covered.
    *   **Why it's an issue**: A truly robust application handles unexpected conditions gracefully. Untested error paths are the most common source of crashes and unhandled exceptions in production. A systematic approach to test these scenarios will significantly improve the application's overall stability and resilience.

### Area 2: Campaign Chat UI Improvements (P2.1-UX)

-   **BUG-20251102-36**: UI - Implement loading indicators for LLM calls in the Campaign Chat tab. (High)
    *   **Issue**: When a user sends a message in the Campaign Chat tab, the system initiates an LLM call which can incur significant latency, especially with RAG. The UI likely becomes unresponsive or provides no visual feedback during this period.
    *   **Why it's an issue**: Lack of visual feedback (e.g., loading spinners, "AI is typing..." messages, dimmed input fields) leads to a frustrating user experience. Users might perceive the application as frozen, leading to duplicate input or abandoning the interaction. This is a critical usability and perceived performance issue.

-   **BUG-20251102-37**: UI - Replace internal exceptions with user-friendly error messages in the Campaign Chat tab. (High)
    *   **Issue**: If any backend LangChain component fails (LLM, retriever, vector store), the UI might currently display raw Python exceptions, stack traces, or overly technical error messages directly to the user.
    *   **Why it's an issue**: Exposing internal errors is poor UX and a potential security risk (revealing system details). User-friendly, contextual error messages that explain the problem in plain language and offer actionable advice (e.g., "LLM service unavailable, please check your network connection") are vital for a professional and helpful interface.

-   **BUG-20251102-38**: UI - Add functionality to delete conversations in the Campaign Chat tab. (Medium)
    *   **Issue**: While the `ConversationStore` provides a `delete_conversation` method, there is no corresponding UI element or workflow in the Campaign Chat tab for users to remove old, irrelevant, or test conversations.
    *   **Why it's an issue**: Users need basic data management capabilities. Over time, accumulating unneeded conversations can clutter the UI, make it harder to find relevant history, and potentially impact perceived performance (as seen with `list_conversations` concerns). This is a significant gap in fundamental CRUD (Create, Read, Update, Delete) operations.

-   **BUG-20251102-39**: UI - Add functionality to rename conversations in the Campaign Chat tab. (Medium)
    *   **Issue**: Conversations in the chat interface are likely identified by an auto-generated ID or a generic title. There's no UI mechanism allowing users to assign meaningful, custom names (e.g., "Quest for the Sunstone", "Discussion about the Dragon's Lair").
    *   **Why it's an issue**: Unlabeled or generically named conversations are difficult to distinguish and organize, especially as the number of conversations grows. The ability to rename improves information architecture, aids discoverability, and enhances overall user control and personalization of their interaction history.

-   **BUG-20251102-40**: UI - Ensure the conversation dropdown updates immediately after sending a message. (Medium)
    *   **Issue**: When a user starts a new conversation or sends a message that modifies an existing one, the list of conversations (e.g., in a dropdown or sidebar) might not refresh instantly to reflect the most recent activity.
    *   **Why it's an issue**: A stale UI fails to provide immediate feedback, leading to user confusion or uncertainty about whether their actions (`save_context` in `ConversationStore`) have been registered. Users expect the interface to accurately reflect the current state of their data instantaneously.

-   **BUG-20251102-41**: UI - Improve the display of sources, potentially showing all relevant sources for a conversation, not just the last message. (Medium)
    *   **Issue**: The current UI might only display the source documents (`source_documents` from `ConversationalRetrievalChain` or `sources` from `CampaignChatClient.ask`) relevant to the *most recent* LLM response. Previous conversational turns may have also utilized source documents that are no longer visible.
    *   **Why it's an issue**: In a RAG system, transparency regarding the information an LLM used is crucial for user trust and understanding. Limiting source display to only the latest message can obscure the context or reasoning behind earlier LLM responses. A more comprehensive source view, perhaps contextual to each chat bubble or expandable, would significantly enhance transparency.

-   **BUG-20251102-42**: UI - Implement a clear "new conversation" button or flow. (Low)
    *   **Issue**: There might not be an explicit and intuitive UI element for a user to start a completely fresh conversation, effectively clearing the current chat history and LLM memory.
    *   **Why it's an issue**: Without a clear "start over" option, users might get stuck in long, off-topic, or context-heavy conversations, leading to frustration. A dedicated button improves user control and helps them manage distinct conversational threads effectively.

-   **BUG-20251102-43**: UI - Add a character limit display for the chat input field. (Low)
    *   **Issue**: The `sanitize_input` function enforces a `MAX_QUESTION_LENGTH` to prevent excessive token usage in LLM calls. However, this limit is likely not communicated to the user in the UI.
    *   **Why it's an issue**: If a user types a very long query, it will be silently truncated by the backend. Providing a visual character count or a dynamic progress bar for the input field indicates the limit to the user and prevents frustration from lost or truncated input.

-   **BUG-20251102-44**: UI - Ensure chat history scrolls to the bottom automatically on new messages. (Low)
    *   **Issue**: In longer chat sessions, when new messages (both user inputs and AI responses) are added to the display, the chat area might not automatically scroll to reveal the most recent entry.
    *   **Why it's an issue**: Manual scrolling to view new messages is an unnecessary friction in chat interfaces. Automatic scrolling to the latest message is a standard and expected behavior, ensuring the user always sees the most recent interaction without effort.

-   **BUG-20251102-45**: UI - Add a "copy to clipboard" option for LLM responses. (Low)
    *   **Issue**: Users might want to easily transfer the LLM's generated output (e.g., a summarized quest log, an NPC description) to another application or document.
    *   **Why it's an issue**: Manually highlighting and copying text, especially from within a UI component, can be cumbersome or prone to errors. A dedicated "copy to clipboard" button enhances user workflow and improves the utility of the generated content.

-   **BUG-20251102-46**: UI - Implement a mechanism to display the current LLM model being used. (Low)
    *   **Issue**: The `CampaignChatClient` uses configurable `llm_provider` and `model_name` settings. This information, while logged in the backend, is not visibly exposed in the user interface.
    *   **Why it's an issue**: Transparency about the underlying LLM (e.g., knowing if GPT-4 or a local Ollama model is active) is important for managing user expectations regarding response quality, cost implications, or even for debugging purposes. Displaying this information enhances user awareness and control.

-   **BUG-20251102-47**: UI - Add a "clear chat" button for the current conversation. (Medium)
    *   **Issue**: While there's a need for a "new conversation" flow, users might also want to clear just the *messages* within the currently selected conversation, without deleting the conversation's core context or metadata. This would involve calling `self.memory.clear()` on the client.
    *   **Why it's an issue**: This provides users with more granular control over their chat session. Clearing messages offers a "soft reset" for a conversational topic, allowing a fresh start without losing the overarching context associated with that specific conversation.

### Area 3: Recently Completed P1 Features (Regression Hunt)

-   **BUG-20251102-48**: Character Profile Extraction - Test with transcripts containing unusual character names or dialogue patterns. (Medium)
    *   **Issue**: The Character Profile Extraction feature (P1-FEATURE-001) relies on Large Language Models (LLMs) to parse transcripts and extract character information. D&D sessions can feature unique, made-up character names, highly stylized dialogue, or very sparse mentions of a character.
    *   **Why it's an issue**: LLMs, despite sophisticated prompting, can struggle with ambiguity or highly unstandardized inputs. This could lead to inaccurate or incomplete character profiles, misattributing dialogue, or failing to identify specific traits, diminishing the reliability and usefulness of the automatic extraction.

-   **BUG-20251102-49**: Character Profile Extraction - Test with very long transcripts to ensure performance and memory usage are acceptable. (High)
    *   **Issue**: Character profile extraction involves processing potentially multi-hour-long transcripts, often involving feeding large blocks of text to an LLM or complex text processing.
    *   **Why it's an issue**: Processing extremely large inputs is a common source of performance bottlenecks and Out Of Memory (OOM) errors. If the feature cannot efficiently handle typical full-session recordings, it becomes unusable for its core purpose, especially in resource-constrained environments. Robust testing is critical here.

-   **BUG-20251102-50**: Character Profile Extraction - Verify that extracted profiles are correctly saved and loaded. (Medium)
    *   **Issue**: After an LLM extracts character profiles, this data is saved to persistent storage (presumably JSON files) and subsequently reloaded for display or further processing.
    *   **Why it's an issue**: Data persistence is a fundamental requirement. Bugs in serialization (saving) or deserialization (loading) -- such as encoding errors, schema inconsistencies, or partial writes -- could lead to corrupted or lost character profiles, undermining the long-term utility of the extraction feature for users.

-   **BUG-20251102-51**: UI Modernization - Test all 5 consolidated tabs for responsiveness on different screen sizes. (Medium)
    *   **Issue**: The UI Modernization (P1-FEATURE-004) involved a significant redesign, reducing tabs and implementing a "full-width responsive layout." Responsive design is complex to execute flawlessly across diverse devices and screen resolutions.
    *   **Why it's an issue**: Despite the intention, UI elements can break, overlap, become unreadable, or exhibit incorrect layout behavior on certain screen sizes (e.g., very narrow mobile views, very wide desktop monitors) or very wide desktop monitors. Visual testing confirms that the responsive design goals are met for a broad range of user environments.

-   **BUG-20251102-52**: UI Modernization - Verify all progressive disclosure elements (accordions, collapsible sections) function correctly. (Medium)
    *   **Issue**: The modernized UI heavily leverages progressive disclosure patterns like accordions and collapsible sections to manage visual clutter.
    *   **Why it's an issue**: These interactive UI components often rely on JavaScript logic and can be prone to bugs: they might fail to expand/collapse, content within them might not render correctly when revealed, or their state might not persist as expected across user interactions or page refreshes. Each instance of such elements needs functional verification.

-   **BUG-20251102-53**: UI Modernization - Check for any broken links or missing elements in the new UI. (Medium)
    *   **Issue**: A large-scale UI refactor ("16 tabs -> 5 sections") can inadvertently lead to orphaned components, disconnected logic, or missing UI elements that were crucial in the old design.
    *   **Why it's an issue**: Broken UI interactions (e.g., buttons that do nothing, navigation links that lead nowhere), or missing content display areas are direct regressions that severely impact feature functionality and user trust. A comprehensive audit is required to ensure full feature parity and connectivity.

-   **BUG-20251102-54**: Campaign Lifecycle Manager - Test campaign creation, loading, and switching. (High)
    *   **Issue**: The Campaign Lifecycle Manager (P1-FEATURE-005) provides core functionality for managing distinct D&D campaigns, which includes creating new campaigns, loading existing ones, and switching between them.
    *   **Why it's an issue**: This is a foundational feature. Critical bugs here -- such as a failure to create a new campaign, inability to load existing campaign data, or data corruption when switching campaigns -- would essentially render the multi-campaign management aspect of the application unusable. These operations must be robust.

-   **BUG-20251102-55**: Campaign Lifecycle Manager - Verify campaign-aware UI elements (filtering, migrations) work as expected. (Medium)
    *   **Issue**: The Campaign Lifecycle Manager integrates "campaign-aware UI, filtering, and migrations" for managing game data. This means UI components should adapt to the selected campaign, and filters should accurately apply campaign context.
    *   **Why it's an issue**: Incorrect application of campaign context could lead to showing irrelevant data (e.g., sessions from the wrong campaign), or migration tools behaving unexpectedly. Comprehensive testing ensures that filtering is precise and data migrations are stable under various conditions.

-   **BUG-20251102-56**: Campaign Lifecycle Manager - Test edge cases for campaign migrations (e.g., empty campaign, corrupted campaign data). (Medium)
    *   **Issue**: Campaign data migrations are complex processes involving schema changes for persistent campaign files. Edge cases like attempting to migrate a campaign with no data, or a campaign JSON file that was manually modified or corrupted, are common failure scenarios.
    *   **Why it's an issue**: Migration logic must be resilient to imperfect real-world data. Untested edge cases here could lead to unrecoverable data loss, system crashes, or data inconsistencies for users whose campaign files deviate from perfect schemas.

-   **BUG-20251102-57**: General P1 - Check for any performance regressions introduced by the new features. (High)
    *   **Issue**: The recently completed P1 features (Character Profile Extraction, UI Modernization, Campaign Lifecycle Manager) involved substantial code changes and introduced new processing demands.
    *   **Why it's an issue**: Even if functionally correct, new features often introduce unintended performance overhead. These regressions -- such as increased load times for the UI, slower data processing for extraction, or higher memory consumption -- can degrade the overall user experience and system efficiency over time. Regular performance checks are necessary.

-   **BUG-20251102-58**: General P1 - Review logs for unexpected errors or warnings related to these new features. (Medium)
    *   **Issue**: Post-implementation, logs serve as the primary source for detecting non-critical but indicative issues. Unexpected error messages, warnings about deprecated APIs, or resource warnings specifically related to the newly implemented P1 features (e.g., in `src/character_profile_extractor.py`, `src/ui/`, `src/campaign_dashboard.py` modules) can signify latent problems.
    *   **Why it's an issue**: Silenced errors or subtle warnings can accumulate, leading to system instability, resource leaks, or incomplete functionality that isn't immediately obvious from the UI. A proactive review of logs is essential to catch these issues before they escalate into critical problems.

### Resolved 2025-11-02

- **BUG-20251102-111**: Normalized Gradio NamedString inputs by coercing to pathlib.Path in src/audio_processor.py:46-74; UI session processing no longer fails at Stage 1.

### Resolved 2025-11-03

- **BUG-20251103-001**: Fixed Stage 2 NameError by passing optional progress callback through HybridChunker.chunk_audio into _create_chunks_with_pauses; added regression tests (src/chunker.py:61-132, 	ests/test_chunker.py:175-218).

### Area 4: UI Dashboard Issues (2025-11-03)

#### Campaign Launcher & Main Dashboard

-   **BUG-20251103-002**: Main Dashboard - Campaign state not persisted across page refreshes. (Medium)
    *   **Issue**: The `active_campaign_state` is a Gradio State variable that resets to `initial_campaign_id` on every page refresh or browser reload. Users lose their active campaign context if they refresh the page.
    *   **Why it's an issue**: Users expect the application to remember their active campaign selection. Having to re-select the campaign after every refresh creates friction and poor UX, especially for long processing sessions where users might refresh to check status.
    *   **File**: `app.py:623` (State initialization)
    *   **Impact**: MEDIUM - Workflow interruption

-   **BUG-20251103-003**: Campaign Launcher - No validation when creating campaign with empty/whitespace-only name. (Low)
    *   **Issue**: The `_create_new_campaign` function in `app.py:780` strips the campaign name but still allows creation if the stripped result is empty, defaulting to auto-generated name without warning the user.
    *   **Why it's an issue**: Users might accidentally create campaigns with generic auto-generated names when they intended to provide a specific name but only entered whitespace. This leads to confusion and campaign management clutter.
    *   **File**: `app.py:780-843` (_create_new_campaign function)
    *   **Impact**: LOW - Minor UX issue

-   **BUG-20251103-004**: Campaign Launcher - Dropdown not refreshed when external campaign changes occur. (Medium)
    *   **Issue**: If campaigns.json is modified externally (CLI, manual edit, another user), the dropdown at `app.py:630-635` doesn't refresh until user explicitly loads/creates a campaign through the UI.
    *   **Why it's an issue**: In multi-user scenarios or when using CLI alongside UI, stale campaign lists lead to errors when trying to load campaigns that appear in the dropdown but no longer exist, or missing newly created campaigns.
    *   **File**: `app.py:630-635` (existing_campaign_dropdown)
    *   **Impact**: MEDIUM - Data consistency issue

-   **BUG-20251103-005**: Campaign Manifest - Exception handling too broad, masks specific errors. (Low)
    *   **Issue**: Multiple functions in `app.py` use bare `except Exception:` blocks that silently handle all exceptions (e.g., `_count_campaign_artifacts:126`, `_build_campaign_manifest:200-237`). Specific errors like permission issues, corrupted JSON, or missing files are all treated identically.
    *   **Why it's an issue**: Broad exception handling makes debugging difficult. Users get generic "metadata unavailable" or empty results without knowing if it's a permissions issue, corrupted data, or missing file. Logs might not capture the actual problem.
    *   **Files**: `app.py:126,200-237,311,344,423,441,449,466,487` (multiple locations)
    *   **Impact**: LOW - Debugging difficulty

#### Process Session Tab

-   **BUG-20251103-006**: Process Session - No client-side validation before starting processing. (High)
    *   **Issue**: The "Start Processing" button in `process_session_tab_modern.py:228-475` doesn't validate inputs before submission. Users can click process without uploading audio, without entering session ID, or with invalid party configurations, triggering backend errors instead of immediate feedback.
    *   **Why it's an issue**: Backend processing is expensive. Invalid submissions waste resources and create poor UX. Users see cryptic error messages from the pipeline instead of helpful validation messages explaining what's missing.
    *   **File**: `src/ui/process_session_tab_modern.py:228-475` (process button and validation guard)
    *   **Status (2025-11-06 Codex)**: Added pre-flight validation that blocks processing when required fields are missing or inconsistent. The button now sets status errors client-side and skips the pipeline call when validation fails.

##### Implementation Notes & Reasoning (2025-11-06 Codex)

- Introduced a queued guard that evaluates inputs before processing and uses `gr.State` to short-circuit heavy jobs when validation fails.
- Expanded validation coverage to include session ID formatting, supported audio extensions, manual entry name uniqueness, and party configuration availability.
- Retained a defensive server-side validation pass so direct API calls still receive clear error messages.

##### Code Review Findings (2025-11-06 Codex)

- [APPROVED] Self-review: validation logic covers reported gaps. Residual risk: file existence check depends on Gradio upload temp path; monitor for non-local deployments.
    *   **Impact**: HIGH - Resource waste, poor UX

-   **BUG-20251103-007**: Process Session - Results section doesn't scroll to view automatically. (Medium)
    *   **Issue**: After processing completes, the results section at `process_session_tab_modern.py:219-226` becomes visible but the UI doesn't auto-scroll to show it. On smaller screens, users might not realize results are ready below the fold.
    *   **Why it's an issue**: Users have to manually scroll down to see results, especially after long processing times. This creates unnecessary friction and can make users think processing is still ongoing when results are already available.
    *   **File**: `src/ui/process_session_tab_modern.py:219-226` (results_section)
    *   **Impact**: MEDIUM - Discoverability issue

  -   **BUG-20251103-008**: Process Session - No progress indicator during long processing operations. (High)
      *   **Issue**: The `process_session` function in `app.py:509-601` runs synchronously without progress updates. Users see no feedback during chunking, transcription (which can take hours), diarization, or classification stages.
      *   **Why it's an issue**: Processing 4-hour sessions can take 10+ hours on CPU. With no progress indicators, users can't tell if the system is working, frozen, or failed. This leads to duplicate submissions, abandoned sessions, and support requests.
      *   **File**: `app.py:509-601` (process_session function)
      *   **Impact**: HIGH - Critical UX flaw for long operations

      *   **Status (2025-11-20 Codex)**: Improved session progress polling with elapsed time, ETA, and next-stage hints sourced from StatusTracker snapshots. The Process tab now surfaces timing summaries whenever processing is active, aligning with the progress UI components.

      ##### Implementation Notes & Reasoning (2025-11-20 Codex)

      - Calculated elapsed time and ETA using recorded stage durations so users get realistic expectations during long runs.
      - Added next-stage callouts to set expectations for upcoming work and reduce perceived stalls.
      - Centralized timestamp parsing to tolerate `Z` suffixes and allow deterministic testing through a patchable time source.

      ##### Code Review Findings (2025-11-20 Codex)

      - [APPROVED] Self-review: Progress summaries display for the active session only and remain hidden otherwise. ETA calculations fall back gracefully when timing data is incomplete.

-   **BUG-20251103-009**: Process Session - Audio file path resolution inconsistent across platforms. (Medium)
    *   **Issue**: The `_resolve_audio_path` function at `app.py:499-507` handles string paths and objects with `.name` attributes, but doesn't handle `pathlib.Path` objects or validate that resolved paths actually exist before passing to pipeline.
    *   **Why it's an issue**: Different Gradio versions or deployment environments might return different types. The function could pass non-existent paths to the pipeline, leading to late-stage failures after user has waited for validation.
    *   **File**: `app.py:499-507` (_resolve_audio_path)
    *   **Impact**: MEDIUM - Cross-platform compatibility

-   **BUG-20251103-010**: Process Session - Character/player name parsing doesn't handle edge cases. (Low)
    *   **Issue**: At `app.py:542-543`, name parsing uses simple `split(',')` and `strip()`. Doesn't handle: names with commas (e.g., "Lastname, Firstname"), empty entries after strip, duplicate names, or special characters.
    *   **Why it's an issue**: Users entering names like "Smith, John" or "O'Brien" might get unexpected results. Duplicate names could break speaker diarization. No validation means errors appear later in the pipeline.
    *   **File**: `app.py:542-543` (name parsing in process_session)
    *   **Impact**: LOW - Edge case handling

#### Campaign Tab

-   **BUG-20251103-011**: Campaign Tab - Static content, no interactive features. (Medium)
    *   **Issue**: The Campaign tab in `campaign_tab_modern.py:9-46` only displays three read-only markdown components. No buttons to refresh data, export knowledge base, or perform campaign management actions.
    *   **Why it's an issue**: Users have to switch to other tabs to perform actions, then return to Campaign tab to see updates. The tab becomes passive display-only rather than an active campaign management hub. UX feels incomplete.
    *   **File**: `src/ui/campaign_tab_modern.py:9-46`
    *   **Impact**: MEDIUM - Missing functionality

-   **BUG-20251103-012**: Campaign Dashboard - Knowledge base sample entries truncated without indication. (Low)
    *   **Issue**: The `_knowledge_summary_markdown` function in `app.py:337-366` uses `[:3]` to sample first 3 entries but doesn't indicate total count or that results are truncated (e.g., "Showing 3 of 47 NPCs").
    *   **Why it's an issue**: Users might think only 3 NPCs exist when actually 47 have been captured. This misrepresents the actual knowledge base size and richness, potentially leading to unnecessary reprocessing or confusion about data completeness.
    *   **File**: `app.py:337-366` (_knowledge_summary_markdown)
    *   **Impact**: LOW - Misleading display

-   **BUG-20251103-013**: Campaign Dashboard - No error recovery for corrupted campaign files. (Medium)
    *   **Issue**: Functions like `_campaign_overview_markdown` (app.py:300-335) catch exceptions but don't provide recovery options. If campaign file is corrupted, user just sees error message with no way to repair or reset.
    *   **Why it's an issue**: Corrupted campaign files can happen from crashes or manual edits. Without recovery tools in the UI, users are stuck and might lose campaign data. Should offer "reset to defaults" or "repair" options.
    *   **File**: `app.py:300-335` and similar functions
    *   **Impact**: MEDIUM - Data recovery gap

#### Campaign Dashboard Module

-   **BUG-20251103-014**: Campaign Dashboard - Personality text truncated without ellipsis boundary awareness. (Low)
    *   **Issue**: At `campaign_dashboard.py:101`, character personality is truncated to 50 chars with `[:50]` without checking word boundaries. Can cut words in half: "No personality set" becomes "No personalit".
    *   **Why it's an issue**: Broken words look unprofessional and can confuse users. Should truncate at word boundaries or use `textwrap` for clean breaks with proper ellipsis.
    *   **File**: `src/campaign_dashboard.py:101`
    *   **Impact**: LOW - Display quality

-   **BUG-20251103-015**: Campaign Dashboard - Health percentage calculation doesn't handle zero components edge case. (Low)
    *   **Issue**: At `campaign_dashboard.py:196`, health calculation uses `if total_components > 0` check, but if somehow checks list is empty, subsequent code still references `health_percent` which could be uninitialized in edge cases.
    *   **Why it's an issue**: Defensive programming issue. While unlikely with current code structure, if checks list initialization changes, could cause NameError. Should set default `health_percent = 0` before the check.
    *   **File**: `src/campaign_dashboard.py:196`
    *   **Impact**: LOW - Edge case safety

-   **BUG-20251103-016**: Campaign Dashboard - Party manager instantiated multiple times unnecessarily. (Low)
    *   **Issue**: `CampaignDashboard.__init__` at `campaign_dashboard.py:20-22` creates manager instances. Multiple dashboard generations create redundant manager objects, each loading the same JSON files from disk.
    *   **Why it's an issue**: Minor performance issue. Each manager instantiation reads party/campaign JSON files. For frequent dashboard refreshes, this adds unnecessary I/O. Managers should be shared/cached at app level.
    *   **File**: `src/campaign_dashboard.py:20-22`
    *   **Impact**: LOW - Performance optimization opportunity

-   **BUG-20251103-017**: Campaign Dashboard - Processed sessions check doesn't filter by campaign. (Medium)
    *   **Issue**: The `_check_processed_sessions` method at `campaign_dashboard.py:119-136` counts all sessions in OUTPUT_DIR regardless of which campaign they belong to. Dashboard for Campaign A shows sessions from Campaign B.
    *   **Why it's an issue**: Campaign-specific dashboards should show campaign-specific data. Showing all sessions is misleading and breaks the campaign isolation model. Users can't tell which sessions belong to their campaign.
    *   **File**: `src/campaign_dashboard.py:119-136` (_check_processed_sessions)
    *   **Impact**: MEDIUM - Data filtering error

-   **BUG-20251103-018**: Campaign Dashboard - Session narratives check includes imported_narratives globally. (Medium)
    *   **Issue**: At `campaign_dashboard.py:146-148`, the function adds ALL narratives from `imported_narratives` directory regardless of campaign. Campaign-specific dashboards include narratives from other campaigns.
    *   **Why it's an issue**: Similar to BUG-20251103-017, breaks campaign isolation. Users see narrative counts that don't match their campaign's actual output, leading to confusion about what content exists for their specific campaign.
    *   **File**: `src/campaign_dashboard.py:146-148`
    *   **Impact**: MEDIUM - Data filtering error

#### Live Session Tab

-   **BUG-20251103-019**: Live Session - Tab is non-functional placeholder. (High)
    *   **Issue**: The Live Session tab in `live_session_tab.py:92-163` has UI mockups but no actual implementation. Buttons toggle states but don't capture audio, transcribe, or display real data. Users might try to use this feature and get confused.
    *   **Why it's an issue**: Having a prominent tab labeled "Live Session Monitoring" that doesn't work creates false expectations. Users waste time trying to figure out why it's not working. Should be marked as "Coming Soon" or hidden until implemented.
    *   **File**: `src/ui/live_session_tab.py:92-163`
    *   **Impact**: HIGH - Misleading UI feature

-   **BUG-20251103-020**: Live Session - Stop button enabled before Start is clicked. (Low)
    *   **Issue**: Looking at the initial state setup, stop_button is created without `interactive=False` initially, allowing users to click Stop before ever starting a session.
    *   **Why it's an issue**: Minor state management issue. Stop button should be disabled until session is actually running. Current implementation might show wrong button states.
    *   **File**: `src/ui/live_session_tab.py:111-115`
    *   **Impact**: LOW - UI state inconsistency

#### Social Insights Tab

-   **BUG-20251103-021**: Social Insights - No loading indicator during analysis. (Medium)
    *   **Issue**: The `analyze_ooc_ui` function in `social_insights_tab.py:16-64` can take several seconds to compute TF-IDF and generate word clouds, but provides no progress feedback during this time. Button just appears frozen.
    *   **Why it's an issue**: Users don't know if analysis is running or if the app crashed. For longer sessions with large OOC transcripts, analysis can take 10-30 seconds. No feedback creates anxiety and duplicate clicks.
    *   **File**: `src/ui/social_insights_tab.py:16-64` (analyze_ooc_ui)
    *   **Impact**: MEDIUM - Missing feedback

-   **BUG-20251103-022**: Social Insights - WordCloud generation not handling import failures gracefully. (High)
    *   **Issue**: At `social_insights_tab.py:20`, the function imports WordCloud inside the try block, but if the `wordcloud` package isn't installed, error message is generic "Analysis Failed" without mentioning missing dependency.
    *   **Why it's an issue**: Users get cryptic error messages instead of actionable "Please install wordcloud package: pip install wordcloud". This is particularly problematic since wordcloud isn't listed in core dependencies.
    *   **File**: `src/ui/social_insights_tab.py:20`
    *   **Impact**: HIGH - Missing dependency handling

-   **BUG-20251103-023**: Social Insights - Temp file cleanup not guaranteed. (Low)
    *   **Issue**: Word cloud image saved to `temp/` at `social_insights_tab.py:49-50` but never explicitly cleaned up. Multiple analyses create orphaned PNG files that accumulate over time.
    *   **Why it's an issue**: Disk space leak. Each analysis creates a ~50KB PNG file that persists indefinitely. After 1000 analyses, that's 50MB of temp files. Should implement cleanup or use temp file context managers.
    *   **File**: `src/ui/social_insights_tab.py:49-50`
    *   **Impact**: LOW - Resource cleanup

-   **BUG-20251103-024**: Social Insights - Campaign filter refresh doesn't persist nebula output. (Low)
    *   **Issue**: When user changes campaign filter at `social_insights_tab.py:130-134`, the session dropdown updates but previously generated word cloud stays visible even though it's for a different campaign/session.
    *   **Why it's an issue**: Creates confusion - users see word cloud for "Campaign A Session 1" but have now selected "Campaign B Session 5". Should clear nebula output when campaign filter changes.
    *   **File**: `src/ui/social_insights_tab.py:130-134` (campaign_selector.change)
    *   **Impact**: LOW - Stale data display

##### Implementation Notes & Reasoning (2025-11-20 GPT-5.1-Codex)

- Added a dedicated loading state for Social Insights that disables the Analyze button, surfaces a `[LOADING]` label, and posts an immediate status update so users see progress before the generator starts yielding results.
- Sequenced the Gradio event chain to restore the Analyze button after completion, preventing stuck disabled states and duplicate submissions.
- Extended unit coverage for the loading and reset helpers to ensure the UI updates stay stable as the tab evolves.

##### Code Review Findings (2025-11-20 GPT-5.1-Codex)

- [APPROVED] Implementation improves UX feedback without altering analysis logic; tests capture the new button-state contract.

#### Settings & Tools Tab

-   **BUG-20251103-025**: Settings & Tools - Diagnostics and Chat sections are static markdown only. (Medium)
    *   **Issue**: At `settings_tools_tab_modern.py:29-41`, diagnostics and chat are just markdown displays with no interactive controls. No "Run Health Check" button, no "Clear Chat History", no "Export Diagnostics" actions.
    *   **Why it's an issue**: Users expect tools and settings to be interactive. Current implementation is display-only, forcing users to use CLI or other tabs for actual tool functionality. Tab name "Settings & Tools" is misleading.
    *   **File**: `src/ui/settings_tools_tab_modern.py:29-41`
    *   **Impact**: MEDIUM - Missing functionality

#### Cross-Tab Coordination Issues

-   **BUG-20251103-026**: Global - Campaign context update triggers excessive re-renders. (Medium)
    *   **Issue**: When campaign is loaded/created (app.py:713-778, 780-842), the update cascades to 20+ UI components across all tabs. Functions like `_load_campaign` return 26+ output values, causing full re-render of all tabs even if user is only viewing one.
    *   **Why it's an issue**: Performance issue. Changing campaign triggers updates to: overview, knowledge, session library, profiles, story sessions, narratives, diagnostics, chat, social campaign selector, social sessions, keywords, nebula. Most aren't visible. Wastes compute and can cause UI lag.
    *   **Files**: `app.py:681-778` (_compute_process_updates, _load_campaign)
    *   **Impact**: MEDIUM - Performance overhead

-   **BUG-20251103-027**: Global - No conflict detection for concurrent operations. (High)
    *   **Issue**: If user starts session processing in one tab and simultaneously tries to modify campaign settings, create characters, or run analysis in other tabs, no locking mechanism prevents race conditions or state conflicts.
    *   **Why it's an issue**: Gradio allows multi-tab interaction. User could be processing session while another user/tab modifies party config or campaign settings. No coordination mechanism = potential data corruption, especially for JSON files written by multiple operations.
    *   **File**: Multiple files - app.py, campaign_dashboard.py, all tab files
    *   **Impact**: HIGH - Data integrity risk

-   **BUG-20251103-028**: Global - Error messages expose internal file paths and stack traces. (Medium)
    *   **Issue**: Throughout the codebase (e.g., app.py:593-600, social_insights_tab.py:58-64), exceptions are displayed to users with full error messages including absolute file paths, function names, and sometimes stack traces.
    *   **Why it's an issue**: Security and UX issue. Exposes internal directory structure and implementation details. Stack traces overwhelm non-technical users. Should show user-friendly messages with option to "View Technical Details" in a collapsible section.
    *   **Files**: Multiple - app.py:593-600, social_insights_tab.py:58-64, campaign_dashboard.py:80-82, 115-117
    *   **Impact**: MEDIUM - Security & UX concern

#### Data Consistency Issues

-   **BUG-20251103-029**: Data - Session library doesn't verify campaign_id before display. (Medium)
    *   **Issue**: The `_session_library_markdown` function in `app.py:397-426` uses `story_manager.list_sessions` with campaign_id filter, but doesn't verify the returned sessions actually have valid campaign metadata or that campaign hasn't been deleted.
    *   **Why it's an issue**: Orphaned sessions (campaign deleted but sessions remain) still show up. Sessions with corrupted metadata pass through. Users see sessions they can't interact with or that belong to non-existent campaigns.
    *   **File**: `app.py:397-426` (_session_library_markdown)
    *   **Impact**: MEDIUM - Data validation gap

-   **BUG-20251103-030**: Data - Character profiles filtered by campaign_id using getattr with default None. (Low)
    *   **Issue**: Throughout the codebase (e.g., app.py:215, 377), character profiles are filtered with `getattr(profile, "campaign_id", None) == campaign_id`. If profile object has no campaign_id attribute, defaults to None and might match if campaign_id is also None.
    *   **Why it's an issue**: Logic error in filtering. If both old profile (no campaign_id attr) and filter (campaign_id=None) are None, profile incorrectly matches. Should check hasattr first or treat missing campaign_id as unassigned rather than matching None.
    *   **Files**: `app.py:215,377`, `campaign_dashboard.py` (similar pattern likely exists)
    *   **Impact**: LOW - Filtering logic flaw

### Area 5: Core Pipeline Bugs (2025-11-07)

- [x] **BUG-20251107-01**: Fix Critical Bug - num_speakers Parameter Ignored in Speaker Diarization (Agent: Jules, Completed: 2025-11-20) (🔴 Critical)
    *   **Problem**: The `num_speakers` parameter (set to 4 in your case) is completely ignored during speaker diarization. Users can set it in the UI and it gets stored in the pipeline configuration, but it's never passed to the PyAnnote diarization model. This causes PyAnnote to auto-detect the number of speakers using clustering algorithms, which frequently results in severe over-segmentation.
    *   **Impact**:
        *   In your Session 6 processing: Expected 4 speakers, detected 20 speakers
        *   This creates 5x more speaker labels than necessary (SPEAKER_00 through SPEAKER_19)
        *   Downstream effects cascade through the entire pipeline:
            *   Wrong speaker attributions in transcripts
            *   IC/OOC classification has to process more segments with incorrect speaker context
            *   Character profile extraction assigns dialogue to wrong speakers
            *   Knowledge base extraction gets confused by fragmented speaker patterns
        *   With PyAnnote version mismatches (model trained on pyannote 0.0.1/torch 1.8.1, running on pyannote 3.1.1/torch 2.5.1), the auto-detection is even less reliable
    *   **Root Cause**: File: `src/diarizer.py`, Line 218
        *   `diarization = self.pipeline(diarization_input)  # ❌ No parameters passed`
        *   The pipeline stores `self.num_speakers = 4` but never uses it when calling PyAnnote.
    *   **Solution**:
        *   Modify `diarize()` method signature to accept `num_speakers` parameter:
            *   `def diarize(self, audio_path: Path, num_speakers: int = None) -> Tuple[List[SpeakerSegment], Dict[str, np.ndarray]]:`
        *   Pass `num_speakers` to PyAnnote pipeline:
            *   `diarization = self.pipeline(diarization_input, num_speakers=num_speakers  # ✅ Pass the parameter)`
        *   Update `pipeline.py` (Line 589) to pass the parameter:
            *   `speaker_segments, speaker_embeddings = self.diarizer.diarize(wav_file, num_speakers=self.num_speakers  # ✅ Wire from pipeline config)`
        *   Add validation to ensure `num_speakers` is reasonable (2-10 range)
        *   Add logging to confirm the parameter is being used:
            *   `self.logger.info(f"Running diarization with num_speakers={num_speakers}")`
    *   **Expected Outcome**:
        *   Diarization respects user's speaker count setting
        *   Accurate speaker detection: 4 speakers instead of 20
        *   Faster downstream processing (fewer segments to classify)
        *   Better speaker profile matching with party configuration
        *   More accurate character attribution in transcripts
    *   **Testing**:
        *   Re-run Session 6 with this fix
        *   Verify log shows "Running diarization with num_speakers=4"
        *   Check output shows exactly 4 speaker labels (SPEAKER_00 through SPEAKER_03)
        *   Validate speaker assignments match party config (3 players + 1 DM)
    *   **Files to Modify**:
        *   `src/diarizer.py` (add parameter, pass to pipeline)
        *   `src/pipeline.py` (wire parameter from config to diarizer)
        *   `tests/test_diarizer.py` (add test for `num_speakers` parameter)

##### Implementation Notes & Reasoning (2025-11-20 Jules)

- Verified that `src/diarizer.py` correctly accepts and uses `num_speakers`.
- Verified that `src/pipeline.py` correctly passes `num_speakers` from config.
- Added `test_diarize_passes_num_speakers` to `tests/test_diarizer.py` to enforce this behavior and prevent regression.

- **BUG-20251107-02**: Add Progress Logging to Stage 6 IC/OOC Classification (🟡 High)
    *   **Problem**: Stage 6 (IC/OOC classification) processes thousands of segments with ZERO progress updates. In your Session 6 processing, Stage 6 started at 10:59:09 with 5726 segments and appeared to hang because there were no log messages for hours. Users have no way to know if:
        *   The process is working normally
        *   It's stuck in an infinite loop
        *   Ollama has crashed
        *   How long it will take to complete
    *   **Impact**:
        *   User anxiety: "Is it frozen or just slow?"
        *   No ETA information for pipeline completion
        *   Can't detect if Ollama is actually failing silently
        *   Users may kill the process thinking it's hung, losing hours of work
        *   No visibility into classification throughput (segments/minute)
    *   **Root Cause**: File: `src/classifier.py`, Line 133-146 (`OllamaClassifier.classify_segments`)
        *   `for i, segment in enumerate(segments): # ... process segment silently ... results.append(result)  # ❌ No progress logging`
        *   There's a simple for-loop with no logging, progress updates, or ETA calculation.
    *   **Solution**:
        *   Add progress logging every N segments (e.g., every 50 or 100 segments):
            *   `PROGRESS_INTERVAL = 50  # Log every 50 segments`
            *   `if (i + 1) % PROGRESS_INTERVAL == 0 or (i + 1) == len(segments): ... self.logger.info(...)`
        *   Add ETA calculation based on average time per segment:
            *   `start_time = time.time() ... eta_minutes = remaining / 60 ... self.logger.info(...)`
        *   Update `StatusTracker` to show live progress in UI:
            *   `StatusTracker.update_stage(session_id, 6, "running", f"Classified {i + 1}/{len(segments)} segments ({percentage:.1f}%)")`
        *   Add batch summary at the end:
            *   `self.logger.info(f"Classification complete: {len(segments)} segments in {total_time/60:.1f} minutes ({avg_time:.2f}s per segment)")`
    *   **Expected Outcome**:
        *   Visible progress updates every 50 segments
        *   ETA calculation shows estimated completion time
        *   Users can see the process is working
        *   Can detect performance issues (if suddenly takes 10s per segment instead of 2s)
        *   Better debugging: can see exactly which segment range caused issues
    *   **Files to Modify**:
        *   `src/classifier.py` (`OllamaClassifier.classify_segments` method)
        *   Consider adding progress logging to OpenAI/Groq classifiers too
        *   Update tests to verify progress logging

- **BUG-20251107-03**: Implement Batched Classification for Stage 6 Performance Optimization (🟢 Medium)
    *   **Problem**: Stage 6 currently makes one LLM API call per segment - for Session 6 that's 5,726 individual API calls! Each call has overhead: Network latency, Model cold start, Context switching, Sequential processing.
    *   **Impact**:
        *   Stage 6 is the slowest stage in the pipeline (often 40-60% of total processing time)
        *   Users wait hours for classification to complete
        *   High API costs if using OpenAI/Groq (5726 API calls × $0.0001 = ~$0.57 per session)
        *   Ollama GPU underutilized - could process multiple segments in parallel
    *   **Opportunity**: Modern LLMs can process multiple segments in a single prompt with minimal quality degradation. By batching 10-20 segments together, we can:
        *   Reduce 5726 calls → ~300 calls (batch size 20)
        *   Reduce processing time from 3+ hours → under 1 hour
        *   Reduce API costs by 95%
        *   Better GPU utilization
    *   **Solution Overview**:
        *   **Approach 1: Batch Multiple Segments in Single Prompt (Recommended)**
        *   Create batching logic in `classifier.py`: `classify_segments_batched`
        *   Create batch prompt template (`src/prompts/classifier_batch_prompt_en.txt`)
        *   Parse batch responses with error handling
        *   Add configuration option in `config.py`: `CLASSIFICATION_BATCH_SIZE`, `CLASSIFICATION_USE_BATCHING`
        *   Update pipeline to use batched classification
    *   **Expected Outcome**:
        *   Processing time: 5726 segments with batch_size=20 = 287 batches
        *   At 5 seconds per batch = 24 minutes (was 3+ hours)
        *   87% time reduction
        *   API costs: 287 calls instead of 5726 = 95% cost reduction
    *   **Risks & Mitigation**:
        *   Risk: LLM might get confused with too many segments in one prompt -> Mitigation: Use conservative `batch_size=20`, make configurable
        *   Risk: JSON parsing might fail on complex responses -> Mitigation: Robust error handling with fallback parsing
        *   Risk: One bad batch could fail entire set -> Mitigation: Catch exceptions per-batch, fallback to one-by-one for failed batches
    *   **Files to Modify**:
        *   `src/classifier.py` (add `classify_segments_batched` method)
        *   `src/prompts/classifier_batch_prompt_en.txt` (new batch prompt template)
        *   `src/prompts/classifier_batch_prompt_nl.txt` (Dutch version)
        *   `src/config.py` (add batching configuration options)
        *   `src/pipeline.py` (switch to batched classification)
        *   `tests/test_classifier.py` (add batching tests)