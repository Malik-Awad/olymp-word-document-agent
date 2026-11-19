import sys
from types import ModuleType

from docx import Document
from docx.shared import Inches
from PIL import Image

import olymp_doc_agent.agent as agent_module
from olymp_doc_agent.agent import EditAgent
from olymp_doc_agent.models import EditOperation
from olymp_doc_agent.verification import verify_input_output


def test_ai_agent_runs_langgraph_plan_and_edit_nodes(tmp_path, monkeypatch):
    input_path = tmp_path / "input.docx"
    output_path = tmp_path / "output.docx"
    document = Document()
    document.add_paragraph("The client has a weekly check-in.")
    document.save(input_path)

    class FakeStateGraph:
        def __init__(self, _state_schema):
            self.nodes = {}
            self.edges = {}

        def add_node(self, name, function):
            self.nodes[name] = function

        def set_entry_point(self, name):
            self.entry = name

        def add_edge(self, start, end):
            self.edges[start] = end

        def compile(self):
            graph = self

            class CompiledGraph:
                def invoke(self, state):
                    node = graph.entry
                    while node != "END":
                        state = graph.nodes[node](state)
                        node = graph.edges[node]
                    return state

            return CompiledGraph()

    langgraph = ModuleType("langgraph")
    langgraph.__path__ = []
    graph_module = ModuleType("langgraph.graph")
    graph_module.END = "END"
    graph_module.StateGraph = FakeStateGraph
    monkeypatch.setitem(sys.modules, "langgraph", langgraph)
    monkeypatch.setitem(sys.modules, "langgraph.graph", graph_module)
    monkeypatch.setattr(
        agent_module,
        "plan_with_model",
        lambda instruction, doc: [
            EditOperation("replace", "weekly check-in", "monthly check-in")
        ],
    )

    result = EditAgent().run(
        str(input_path),
        "Change the check-in frequency to monthly",
        str(output_path),
    )

    assert result["error"] is None
    assert Document(output_path).paragraphs[0].text == (
        "The client has a monthly check-in."
    )


def test_agent_replaces_text_and_preserves_table(tmp_path):
    input_path = tmp_path / "input.docx"
    output_path = tmp_path / "output.docx"
    document = Document()
    document.add_heading("Care Plan", 1)
    document.add_paragraph("Review weekly.")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Status"
    table.cell(0, 1).text = "Draft"
    document.save(input_path)

    result = EditAgent(offline=True).run(
        str(input_path),
        "Replace 'weekly' with 'biweekly'",
        str(output_path),
    )

    assert result["error"] is None
    edited = Document(output_path)
    assert "Review biweekly." in [p.text for p in edited.paragraphs]
    assert edited.tables[0].cell(0, 0).text == "Status"
    assert edited.tables[0].cell(0, 1).text == "Draft"
    verify_input_output(str(input_path), str(output_path))


def test_agent_rejects_ambiguous_target(tmp_path):
    input_path = tmp_path / "input.docx"
    output_path = tmp_path / "output.docx"
    document = Document()
    document.add_paragraph("Draft.")
    document.add_paragraph("Draft.")
    document.save(input_path)

    result = EditAgent(offline=True).run(
        str(input_path),
        "Remove 'Draft'",
        str(output_path),
    )

    assert "ambiguous" in result["error"]
    assert not output_path.exists()


def test_agent_preserves_image(tmp_path):
    input_path = tmp_path / "input.docx"
    output_path = tmp_path / "output.docx"
    image_path = tmp_path / "small.png"
    Image.new("RGB", (20, 20), "red").save(image_path)

    document = Document()
    document.add_paragraph("A small image follows:")
    document.add_picture(str(image_path), width=Inches(0.5))
    document.save(input_path)

    result = EditAgent(offline=True).run(
        str(input_path),
        "Replace 'small image' with 'diagram'",
        str(output_path),
    )

    assert result["error"] is None
    edited = Document(output_path)
    inline_shapes = edited.inline_shapes
    assert len(inline_shapes) == 1
