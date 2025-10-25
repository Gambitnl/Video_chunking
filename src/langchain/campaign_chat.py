"""
Conversational interface for querying campaign data using LangChain.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from src.config import Config

logger = logging.getLogger("DDSessionProcessor.campaign_chat")


class CampaignChatClient:
    """LangChain-powered conversational interface for campaign data."""

    def __init__(
        self,
        llm_provider: str = None,
        model_name: str = None,
        retriever=None
    ):
        """
        Initialize the campaign chat client.

        Args:
            llm_provider: LLM provider ('ollama' or 'openai')
            model_name: Model name to use
            retriever: Optional retriever for RAG (defaults to simple keyword search)
        """
        self.llm_provider = llm_provider or Config.LLM_BACKEND
        self.model_name = model_name or Config.OLLAMA_MODEL
        self.retriever = retriever

        # Initialize LLM based on provider
        self.llm = self._initialize_llm()

        # Initialize conversation memory
        self.memory = self._initialize_memory()

        # Load system prompt
        self.system_prompt = self._load_system_prompt()

        logger.info(
            f"Initialized CampaignChatClient with {self.llm_provider} "
            f"using model {self.model_name}"
        )

    def _initialize_llm(self):
        """Initialize the LLM based on provider configuration."""
        try:
            if self.llm_provider == "ollama":
                from langchain_community.llms import Ollama
                return Ollama(
                    model=self.model_name,
                    base_url=Config.OLLAMA_BASE_URL
                )
            elif self.llm_provider == "openai":
                from langchain_community.llms import OpenAI
                return OpenAI(
                    model=self.model_name,
                    openai_api_key=Config.OPENAI_API_KEY
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
        except ImportError as e:
            logger.error(f"Failed to import LangChain dependencies: {e}")
            raise RuntimeError(
                "LangChain dependencies not installed. "
                "Run: pip install langchain langchain-community"
            ) from e

    def _initialize_memory(self):
        """Initialize conversation memory."""
        from langchain.memory import ConversationBufferMemory

        return ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )

    def _load_system_prompt(self) -> str:
        """Load the system prompt template."""
        prompt_file = Path(__file__).parent.parent.parent / "prompts" / "campaign_assistant.txt"

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                template = f.read()

            # TODO: Replace placeholders with actual campaign data
            return template.format(
                campaign_name="Unknown",
                num_sessions=0,
                pc_names="Unknown"
            )
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
            # If retriever is available, get relevant documents
            sources = []
            context_docs = ""

            if self.retriever:
                relevant_docs = self.retriever.retrieve(question, top_k=5)
                sources = [
                    {
                        "content": doc.page_content if hasattr(doc, 'page_content') else str(doc),
                        "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
                    }
                    for doc in relevant_docs
                ]

                # Build context string for LLM
                context_docs = "\n\n".join([
                    f"Source {i+1}:\n{doc['content']}"
                    for i, doc in enumerate(sources)
                ])

            # Build full prompt with system message, context, and question
            full_prompt = f"{self.system_prompt}\n\n"

            if context_docs:
                full_prompt += f"Relevant Information:\n{context_docs}\n\n"

            full_prompt += f"Question: {question}\n\nAnswer:"

            # Generate response
            response = self.llm(full_prompt)

            # Store in memory
            self.memory.save_context(
                {"input": question},
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
