import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import api
import classifier
import rag
from rag import ask_manual, clean_answer, load_manual, read_pages, search

client = TestClient(api.app)


def test_manual_pages_are_read_with_page_numbers():
    pages = read_pages(rag.MANUAL_FILE)
    assert [number for number, _ in pages] == list(range(1, 11))
    assert "Security and your account" in pages[6][1]
    assert "CloudDesk User Manual - version" not in pages[6][1]


def test_load_manual_saves_small_chunks_with_page_metadata():
    count = load_manual()
    stored = rag.get_collection().get(include=["documents", "metadatas"])

    assert count == len(stored["ids"]) > 10
    assert all(len(text) <= 512 for text in stored["documents"])
    assert {metadata["page"] for metadata in stored["metadatas"]} == set(range(1, 11))


def test_search_returns_top_3_with_pages():
    chunks = search("How long is the password reset link valid?")
    assert len(chunks) == 3
    assert chunks[0]["page"] == 7


def fake_model(monkeypatch, reply):
    prompts = []

    def fake_ask(prompt, temperature=0):
        prompts.append(prompt)
        return reply

    monkeypatch.setattr(rag, "ask", fake_ask)
    return prompts


def test_answer_uses_only_the_cited_page(monkeypatch):
    prompts = fake_model(monkeypatch, "The reset link is valid for 1 hour. [Page 7]")

    result = ask_manual("How long is the password reset link valid?")

    assert result["answer"] == "The reset link is valid for 1 hour."
    assert result["sources"] == [{"page": 7}]
    assert "[Page 7]" in prompts[0]
    assert "If the context does not contain the answer, reply with exactly: I don't know." in prompts[0]


@pytest.mark.parametrize("reply", ["I don't know.", "I don’t know", "i don't know. [Page 2]", ""])
def test_unanswerable_returns_i_dont_know_without_sources(monkeypatch, reply):
    fake_model(monkeypatch, reply)
    result = ask_manual("Who is the CEO of CloudDesk?")
    assert result["answer"] == "I don't know."
    assert result["sources"] == []


@pytest.mark.parametrize("space", ["\u202f", "\u00a0"])
def test_clean_answer_fixes_special_spaces(space):
    assert clean_answer(f"Monday to Saturday, 9{space}am to 7{space}pm.  ") == "Monday to Saturday, 9 am to 7 pm."
    assert clean_answer("Full\u2011time employees") == "Full-time employees"


def test_answer_with_a_special_space_is_cleaned(monkeypatch):
    fake_model(monkeypatch, "Support is open from 9\u202fam to 7\u202fpm. [Page 10]")

    result = ask_manual("When is the support team available?")

    assert result["answer"] == "Support is open from 9 am to 7 pm."
    assert "9 am" in result["answer"]


def test_post_ask(monkeypatch):
    fake_model(monkeypatch, "Passwords reset links last 1 hour. [Page 7]")

    response = client.post("/ask", json={"question": "How long is the password reset link valid?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "Passwords reset links last 1 hour.", "sources": [{"page": 7}]}


def test_post_ask_rejects_an_empty_question():
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_post_ask_model_error_gives_503(monkeypatch):
    def broken(prompt, temperature=0):
        raise RuntimeError("rate limit")

    monkeypatch.setattr(rag, "ask", broken)
    response = client.post("/ask", json={"question": "How long is the trial?"})
    assert response.status_code == 503


def test_post_classify_uses_the_best_prompt(monkeypatch):
    prompts = []

    def fake_ask(prompt, temperature=0):
        prompts.append(prompt)
        return "Billing"

    monkeypatch.setattr(classifier, "ask", fake_ask)

    response = client.post("/classify", json={"ticket": "I was charged twice."})

    assert response.json() == {"category": "Billing", "prompt_version": "v2"}
    assert "## Constraints" in prompts[0]


def test_post_classify_bad_model_answer_gives_502(monkeypatch):
    monkeypatch.setattr(classifier, "ask", lambda prompt, temperature=0: "Sales")
    assert client.post("/classify", json={"ticket": "Hello"}).status_code == 502


def tool_call(name, arguments):
    return SimpleNamespace(id="c1", function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))


def fake_chat(monkeypatch, *replies):
    seen = []

    def chat(messages, tools):
        seen.append(messages)
        return replies[len(seen) - 1]

    import assistant
    monkeypatch.setattr(assistant, "chat_with_tools", chat)
    monkeypatch.setattr(api, "answer_question", lambda message: assistant.answer_question(message, chat=chat))
    return seen


def test_post_chat_model_chooses_the_manual(monkeypatch):
    fake_chat(
        monkeypatch,
        SimpleNamespace(content=None, tool_calls=[tool_call("search_manual", {"question": "password reset link"})]),
        SimpleNamespace(content="The reset link is valid for 1 hour.", tool_calls=None),
    )

    response = client.post("/chat", json={"message": "How long is the password reset link valid?"})

    body = response.json()
    assert body["tools_used"] == ["search_manual(password reset link)"]
    assert body["answer"] == "The reset link is valid for 1 hour."
    assert {"page": 7} in body["sources"]


def test_post_chat_model_chooses_a_tool(monkeypatch):
    fake_chat(
        monkeypatch,
        SimpleNamespace(content=None, tool_calls=[tool_call("get_customer", {"customer_id": 2})]),
        SimpleNamespace(content="Customer 2 is on the Premium plan.", tool_calls=None),
    )

    body = client.post("/chat", json={"message": "Which plan is customer 2 on?"}).json()

    assert body == {"answer": "Customer 2 is on the Premium plan.", "tools_used": ["get_customer(2)"], "sources": []}


def test_post_chat_i_dont_know_has_no_sources(monkeypatch):
    fake_chat(
        monkeypatch,
        SimpleNamespace(content=None, tool_calls=[tool_call("search_manual", {"question": "CEO"})]),
        SimpleNamespace(content="I don't know", tool_calls=None),
    )

    body = client.post("/chat", json={"message": "Who is the CEO?"}).json()

    assert body["answer"] == "I don't know."
    assert body["sources"] == []
