"""
Conversational interface for querying campaign data using LangChain.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from src.config import Config
from src.langchain.llm_factory import LLMFactory

logger = logging.getLogger("DDSessionProcessor.campaign_chat")

# Maximum lengths to prevent abuse
MAX_QUESTION_LENGTH = 2000
MAX_CONTEXT_DOCS_LENGTH = 10000

def sanitize_input(text: str, max_length: int = MAX_QUESTION_LENGTH) -> str:
    """
    Sanitize user input to prevent prompt injection attacks.

    Args:
        text: User input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text

    Raises:
        ValueError: If input is invalid
    """
    if not text or not isinstance(text, str):
        raise ValueError("Input must be a non-empty string")

    # Remove null bytes
    text = text.replace('\x00', '')

    # Limit length to prevent excessive token usage
    if len(text) > max_length:
        logger.warning(f"Input truncated from {len(text)} to {max_length} characters")
        text = text[:max_length]

    # Remove or escape potential prompt injection patterns
    # Remove system-like instructions (attempts to override the system prompt)
    injection_patterns = [
        r'ignore\s+(all\s+)?previous\s+instructions',
        r'disregard\s+(all\s+)?previous\s+instructions',
        r'forget\s+(all\s+)?previous\s+instructions',
        r'system\s*:',
        r'assistant\s*:',
        r'<\|im_start\|>',
        r'<\|im_end\|>',
    ]

    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Potential prompt injection detected and sanitized: {pattern}")
            text = re.sub(pattern, '[REDACTED]', text, flags=re.IGNORECASE)

    # Final check: after stripping, ensure we still have content
    sanitized = text.strip()
    if not sanitized:
        raise ValueError("Input cannot be empty after sanitization")

    return sanitized


class SafeFormatDict(dict):
    def __missing__(self, key):
        return f'{{{key}}}'


class SafeFormatDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"


class CampaignChatClient:
    """LangChain-powered conversational interface for campaign data."""

    def __init__(
        self,
        llm_provider: str = None,
        model_name: str = None,
        retriever=None,
        campaign_id: Optional[str] = None
    ):
        """
        Initialize the campaign chat client.

        Args:
            llm_provider: LLM provider ('ollama' or 'openai')
            model_name: Model name to use
            retriever: Optional retriever for RAG (defaults to simple keyword search)
            campaign_id: Optional campaign ID for contextual prompts
        """
        self.llm_provider = llm_provider or Config.LLM_BACKEND
        self.model_name = model_name or Config.OLLAMA_MODEL
        self.retriever = retriever
        self.campaign_id = campaign_id

        # Initialize LLM based on provider
        self.llm = LLMFactory.create_llm(
            provider=self.llm_provider,
            model_name=self.model_name
        )

        # Initialize conversation memory
        self.memory = self._initialize_memory()

        # Load system prompt
        self.system_prompt = self._load_system_prompt()

        logger.info(
            f"Initialized CampaignChatClient with {self.llm_provider} "
            f"using model {self.model_name}"
        )

    def _initialize_memory(self):
        """
        Initialize conversation memory with bounded window.

        Uses ConversationBufferWindowMemory to prevent unbounded memory growth
        by keeping only the last N conversation exchanges.
        """
        try:
            from langchain_classic.memory import ConversationBufferWindowMemory
        except ImportError:
            try:
                # Fallback for older langchain versions
                from langchain.memory import ConversationBufferWindowMemory
            except ImportError:
                # Final fallback to unbounded memory (not ideal)
                logger.warning("ConversationBufferWindowMemory not available, using unbounded memory")
                try:
                    from langchain_classic.memory import ConversationBufferMemory
                    return ConversationBufferMemory(
                        memory_key="chat_history",
                        return_messages=True,
                        output_key="answer"
                    )
                except ImportError:
                    from langchain.memory import ConversationBufferMemory
                    return ConversationBufferMemory(
                        memory_key="chat_history",
                        return_messages=True,
                        output_key="answer"
                    )

        # Keep last 10 exchanges (20 messages total) to prevent memory growth
        return ConversationBufferWindowMemory(
            k=10,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )

    def _load_system_prompt(self) -> str:
        """Load the system prompt template with campaign context."""
        prompt_file = Path(__file__).parent.parent.parent / "prompts" / "campaign_assistant.txt"

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                template = f.read()

            # Load campaign data if campaign_id is provided
            campaign_name = "Unknown"
            num_sessions = 0
            pc_names = "Unknown"

            if self.campaign_id:
                try:
                    from src.party_config import CampaignManager, PartyConfigManager
                    from src.story_notebook import StoryNotebookManager

                    # Load campaign info
                    campaign_mgr = CampaignManager()
                    campaign = campaign_mgr.get_campaign(self.campaign_id)

                    if campaign:
                        campaign_name = campaign.name

                        # Load party info to get PC names
                        party_mgr = PartyConfigManager()
                        party = party_mgr.get_party(campaign.party_id)

                        if party and party.characters:
                            pc_names = ", ".join([char.name for char in party.characters])

                        # Get session count for this campaign
                        story_mgr = StoryNotebookManager()
                        sessions = story_mgr.list_sessions(
                            limit=None,
                            campaign_id=self.campaign_id,
                            include_unassigned=False
                        )
                        num_sessions = len(sessions)

                except ImportError as e:
                    logger.warning(f"Could not load campaign data for {self.campaign_id} because a dependency is missing: {e}")
                except Exception as e:
                    logger.warning(f"Could not load campaign data for {self.campaign_id}: {e}", exc_info=True)

            context = SafeFormatDict(
                campaign_name=campaign_name,
                num_sessions=num_sessions,
                pc_names=pc_names,
            )

            return template.format_map(context)
        except FileNotFoundError:
            logger.warning(f"System prompt file not found: {prompt_file}")
            return "You are a helpful D&D campaign assistant."

    def ask(self, question: str, context: Optional[Dict] = None) -> Dict:
        """
        Ask a question and get an answer with sources.

        Args:
            question: User's question
            context: Optional context (campaign name, session filters, etc.)

        Returns:
            Dictionary containing 'answer' and 'sources'
        """
        try:
            # Sanitize user input to prevent prompt injection
            try:
                sanitized_question = sanitize_input(question, max_length=MAX_QUESTION_LENGTH)
            except ValueError as e:
                logger.error(f"Invalid input: {e}")
                return {
                    "answer": "Error: Invalid input. Please provide a valid question.",
                    "sources": []
                }

            # If retriever is available, get relevant documents
            sources = []
            context_docs = ""

            if self.retriever:
                # Use sanitized question for retrieval
                relevant_docs = self.retriever.retrieve(sanitized_question, top_k=5)
                sources = [
                    {
                        "content": doc.page_content if hasattr(doc, 'page_content') else str(doc),
                        "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
                    }
                    for doc in relevant_docs
                ]

                # Build context string for LLM with length limits
                context_parts = []
                total_length = 0
                for i, doc in enumerate(sources):
                    content = doc['content']
                    if total_length + len(content) > MAX_CONTEXT_DOCS_LENGTH:
                        # Truncate to fit within limit
                        remaining = MAX_CONTEXT_DOCS_LENGTH - total_length
                        if remaining > 100:  # Only add if meaningful length remains
                            content = content[:remaining] + "... [truncated]"
                            context_parts.append(f"Source {i+1}:\n{content}")
                        break
                    context_parts.append(f"Source {i+1}:\n{content}")
                    total_length += len(content)

                context_docs = "\n\n".join(context_parts)

            # Use structured prompt format to prevent injection
            # Separate system prompt, context, and user question clearly
            prompt_parts = [
                f"SYSTEM INSTRUCTIONS:\n{self.system_prompt}",
                ""
            ]

            if context_docs:
                prompt_parts.extend([
                    "RELEVANT INFORMATION:",
                    context_docs,
                    ""
                ])

            prompt_parts.extend([
                "USER QUESTION:",
                sanitized_question,
                "",
                "ASSISTANT RESPONSE:"
            ])

            full_prompt = "\n".join(prompt_parts)

            # Generate response
            response = self.llm(full_prompt)

            # Store in memory (use sanitized question)
            self.memory.save_context(
                {"input": sanitized_question},
                {"answer": response}
            )

            return {
                "answer": response,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return {
                "answer": f"Error: {str(e)}",
                "sources": []
            }

    def clear_memory(self):
        """Clear conversation memory."""
        self.memory.clear()
        logger.info("Conversation memory cleared")


class CampaignChatChain:
    """Conversational chain for campaign queries using ConversationalRetrievalChain."""

    def __init__(self, llm, retriever):
        """
        Initialize the conversational chain.

        Args:
            llm: Language model instance
            retriever: Retriever for fetching relevant documents
        """
        try:
            from langchain_classic.chains import ConversationalRetrievalChain
            from langchain_classic.memory import ConversationBufferMemory
        except ImportError:
            # Fallback for older langchain versions
            from langchain.chains import ConversationalRetrievalChain
            from langchain.memory import ConversationBufferMemory

        self.llm = llm
        self.retriever = retriever

        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            ),
            return_source_documents=True,
            verbose=True
        )

        logger.info("Initialized CampaignChatChain")

    def ask(self, question: str) -> Dict:
        """
        Ask a question and get answer with sources.

        Args:
            question: User's question

        Returns:
            Dictionary with 'answer' and 'sources'
        """
        try:
            result = self.chain({"question": question})

            return {
                "answer": result["answer"],
                "sources": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in result.get("source_documents", [])
                ]
            }
        except Exception as e:
            logger.error(f"Error in conversational chain: {e}", exc_info=True)
            return {
                "answer": f"Error: {str(e)}",
                "sources": []
            }

