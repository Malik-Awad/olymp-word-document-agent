import sys
from types import ModuleType, SimpleNamespace

import pytest
from docx import Document

from olymp_doc_agent.models import EditOperation
from olymp_doc_agent.planner import plan_with_model


def test_model_planner_uses_document_context_and_parses_plan(monkeypatch):
    seen = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            seen["config"] = kwargs

        def invoke(self, messages):
            seen["messages"] = messages
            return SimpleNamespace(
                content=(
                    '{"operations":[{"action":"replace","target":"weekly check-in",'
                    '"replacement":"monthly check-in"}],"clarification":null}'
                )
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setitem(
        sys.modules,
        "langchain_openai",
        ModuleType("langchain_openai"),
    )
    sys.modules["langchain_openai"].ChatOpenAI = FakeChatOpenAI

    document = Document()
    document.add_paragraph("The client has a weekly check-in.")
    operations = plan_with_model("Change the check-in to monthly", document)

    assert operations == [
        EditOperation("replace", "weekly check-in", "monthly check-in")
    ]
    assert seen["config"] == {
        "model": "test-model",
        "temperature": 0,
        "base_url": "https://example.invalid/v1",
    }
    assert "weekly check-in" in seen["messages"][1][1]


def test_model_planner_fails_clearly_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is not set"):
        plan_with_model("Make a change", Document())


def test_model_planner_returns_clarification_instead_of_guessing(monkeypatch):
    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(
                content=(
                    '{"operations":[],"clarification":"Which appointment should change?"}'
                )
            )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(
        sys.modules,
        "langchain_openai",
        ModuleType("langchain_openai"),
    )
    sys.modules["langchain_openai"].ChatOpenAI = FakeChatOpenAI

    with pytest.raises(ValueError, match="Which appointment should change"):
        plan_with_model("Change the appointment", Document())

