import pytest

from langchain_core.documents import Document
from langchain_core.language_models.llms import LLM
from langchain_core.retrievers import BaseRetriever

from src.langchain.campaign_chat import CampaignChatChain


class SequenceLLM(LLM):
    """Deterministic LLM that returns preset responses in order."""

    responses: list
    seen_prompts: list

    model_config = {"extra": "allow"}

    def __init__(self, responses):
        super().__init__(responses=list(responses), seen_prompts=[])

    @property
    def _llm_type(self) -> str:
        return "sequence-llm"

    @property
    def _identifying_params(self):
        return {"responses": tuple(self.responses)}

    def _call(self, prompt: str, stop=None):
        self.seen_prompts.append(prompt)
        if self.responses:
            return self.responses.pop(0)
        return "default response"


class StaticRetriever(BaseRetriever):
    """Simple retriever that returns a static list of documents."""

    documents: list
    queries: list

    model_config = {"extra": "allow"}

    def __init__(self, documents):
        super().__init__(documents=list(documents), queries=[])

    def _get_relevant_documents(self, query: str, *, run_manager=None):
        self.queries.append(query)
        return self.documents

    async def _aget_relevant_documents(self, query: str, *, run_manager=None):
        return self._get_relevant_documents(query, run_manager=run_manager)


def test_campaign_chat_chain_end_to_end_returns_sources():
    """Ensure CampaignChatChain returns LLM answer and propagates sources."""

    documents = [
        Document(page_content="Shadow Lord leads the cult", metadata={"id": "kb-1"}),
    ]
    llm = SequenceLLM(["Shadow Lord overthrown by heroes"])
    retriever = StaticRetriever(documents)

    chain = CampaignChatChain(llm, retriever)

    result = chain.ask("Who is the Shadow Lord?")

    assert result["answer"] == "Shadow Lord overthrown by heroes"
    assert result["sources"] == [
        {"content": "Shadow Lord leads the cult", "metadata": {"id": "kb-1"}},
    ]
    assert llm.seen_prompts[0].startswith("Use the following pieces of context"), "LLM should see formatted context prompt"
    assert retriever.queries, "Retriever should be invoked with the user question"


def test_campaign_chat_chain_handles_empty_retrieval():
    """Verify the chain still answers when no documents are retrieved."""

    llm = SequenceLLM(["No lore found for that topic"])
    retriever = StaticRetriever([])

    chain = CampaignChatChain(llm, retriever)

    result = chain.ask("What lore is available?")

    assert result["answer"] == "No lore found for that topic"
    assert result["sources"] == []
    assert retriever.queries == ["What lore is available?"], "Query should be recorded even without docs"
