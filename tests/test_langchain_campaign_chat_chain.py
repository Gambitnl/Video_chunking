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


def test_campaign_chat_chain_complex_multipart_question():
    """Test chain handles complex multi-part questions with multiple sources."""

    documents = [
        Document(page_content="Elara is a high elf wizard from Silverymoon", metadata={"session": "s1", "speaker": "DM"}),
        Document(page_content="Thorin is a dwarf cleric who worships Moradin", metadata={"session": "s1", "speaker": "DM"}),
        Document(page_content="Elara and Thorin met at the Yawning Portal tavern", metadata={"session": "s2", "speaker": "DM"}),
    ]
    llm = SequenceLLM(["Elara is a high elf wizard and Thorin is a dwarf cleric. They met at the Yawning Portal."])
    retriever = StaticRetriever(documents)

    chain = CampaignChatChain(llm, retriever)

    result = chain.ask("Who are Elara and Thorin, and where did they meet?")

    assert result["answer"] == "Elara is a high elf wizard and Thorin is a dwarf cleric. They met at the Yawning Portal."
    assert len(result["sources"]) == 3, "Complex question should return multiple relevant sources"
    assert retriever.queries[0] == "Who are Elara and Thorin, and where did they meet?"


def test_campaign_chat_chain_followup_question_with_context():
    """Test chain handles follow-up questions that rely on conversational context."""

    documents = [
        Document(page_content="The Shadow Lord commands an army of undead", metadata={"id": "kb-1"}),
        Document(page_content="His fortress is located in the Shadowfell", metadata={"id": "kb-2"}),
    ]
    llm = SequenceLLM([
        "The Shadow Lord is the main antagonist",
        "Where is the Shadow Lord's fortress?", # Rephrased question step
        "His fortress is in the Shadowfell"
    ])
    retriever = StaticRetriever(documents)

    chain = CampaignChatChain(llm, retriever)

    # First question
    result1 = chain.ask("Who is the Shadow Lord?")
    assert result1["answer"] == "The Shadow Lord is the main antagonist"
    assert len(result1["sources"]) == 2

    # Follow-up question (uses "his" referring to Shadow Lord from context)
    result2 = chain.ask("Where is his fortress?")
    assert result2["answer"] == "His fortress is in the Shadowfell"
    assert len(result2["sources"]) == 2


def test_campaign_chat_chain_specific_vs_general_questions():
    """Test chain handles both specific and general questions appropriately."""

    documents = [
        Document(page_content="Waterdeep is the City of Splendors", metadata={"type": "location"}),
        Document(page_content="Baldur's Gate is a major trading port", metadata={"type": "location"}),
        Document(page_content="Neverwinter was rebuilt after the Spellplague", metadata={"type": "location"}),
    ]

    # Test specific question
    llm_specific = SequenceLLM(["Waterdeep is known as the City of Splendors"])
    retriever_specific = StaticRetriever([documents[0]])  # Only Waterdeep doc
    chain_specific = CampaignChatChain(llm_specific, retriever_specific)

    result_specific = chain_specific.ask("What is Waterdeep?")
    assert "Waterdeep" in result_specific["answer"]
    assert len(result_specific["sources"]) == 1, "Specific question should return focused sources"

    # Test general question
    llm_general = SequenceLLM(["The campaign features three major cities: Waterdeep, Baldur's Gate, and Neverwinter"])
    retriever_general = StaticRetriever(documents)  # All location docs
    chain_general = CampaignChatChain(llm_general, retriever_general)

    result_general = chain_general.ask("What cities are in the campaign?")
    assert "cities" in result_general["answer"].lower() or "waterdeep" in result_general["answer"].lower()
    assert len(result_general["sources"]) == 3, "General question should return multiple sources"


def test_campaign_chat_chain_question_requiring_synthesis():
    """Test chain handles questions requiring synthesis across multiple sources."""

    documents = [
        Document(page_content="Thorin lost his hammer in session 3", metadata={"session": "s3"}),
        Document(page_content="A mysterious merchant sold Thorin a new warhammer", metadata={"session": "s5"}),
        Document(page_content="The warhammer is named Dawnbringer and glows with holy light", metadata={"session": "s6"}),
    ]
    llm = SequenceLLM(["Thorin lost his original hammer but acquired Dawnbringer from a merchant"])
    retriever = StaticRetriever(documents)

    chain = CampaignChatChain(llm, retriever)

    result = chain.ask("What happened to Thorin's weapons?")

    assert "hammer" in result["answer"].lower()
    assert len(result["sources"]) == 3, "Synthesis question should pull from multiple related sources"
    assert result["sources"][0]["metadata"]["session"] == "s3"
    assert result["sources"][1]["metadata"]["session"] == "s5"


def test_campaign_chat_chain_single_source_detailed_answer():
    """Test chain with question that should return one highly relevant source."""

    documents = [
        Document(
            page_content="Lord Neverember rules Neverwinter with an iron fist. He seized power after the Spellplague and declared himself Lord Protector.",
            metadata={"type": "npc", "name": "Neverember"}
        ),
    ]
    llm = SequenceLLM(["Lord Neverember is the authoritarian ruler of Neverwinter"])
    retriever = StaticRetriever(documents)

    chain = CampaignChatChain(llm, retriever)

    result = chain.ask("Who is Lord Neverember?")

    assert "Neverember" in result["answer"]
    assert len(result["sources"]) == 1, "Single focused question should return single relevant source"
    assert result["sources"][0]["metadata"]["name"] == "Neverember"
    assert "Lord Neverember rules Neverwinter" in result["sources"][0]["content"]
