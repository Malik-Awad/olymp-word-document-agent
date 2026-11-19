from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches

from olymp_doc_agent.editor import (
    apply_operation,
    count_matches,
    iter_paragraphs,
    paragraph_plain_text,
)
from olymp_doc_agent.models import EditOperation
from olymp_doc_agent.planner import _operation_from_data, plan_instruction


def test_replace_preserves_run_formatting():
    document = Document()
    paragraph = document.add_paragraph()
    bold = paragraph.add_run("Review ")
    bold.bold = True
    italic = paragraph.add_run("weekly")
    italic.italic = True
    paragraph.add_run(" notes.")

    count = apply_operation(document, EditOperation("replace", "weekly", "biweekly"))

    assert count == 1
    assert paragraph_plain_text(paragraph) == "Review biweekly notes."
    assert paragraph.runs[0].bold is True
    assert paragraph.runs[1].italic is True


def test_remove_across_runs_preserves_formatting_of_unaffected_runs():
    document = Document()
    paragraph = document.add_paragraph()
    left = paragraph.add_run("Remove ")
    left.bold = True
    middle = paragraph.add_run("DRAFT ")
    middle.italic = True
    right = paragraph.add_run("only.")

    apply_operation(document, EditOperation("remove", "DRAFT"))

    assert paragraph_plain_text(paragraph) == "Remove  only."
    assert paragraph.runs[0].bold is True
    assert paragraph.runs[1].italic is True
    assert paragraph.runs[1].text == " "
    assert paragraph.runs[2].text == "only."


def test_insert_before_and_after():
    document = Document()
    paragraph = document.add_paragraph("Patient plan: continue")

    apply_operation(document, EditOperation("insert", "continue", "to ", "before"))
    apply_operation(document, EditOperation("insert", "continue", " treatment", "after"))

    assert paragraph_plain_text(paragraph) == "Patient plan: to continue treatment"


def test_edit_in_table_cell():
    document = Document()
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Status: draft"

    apply_operation(document, EditOperation("replace", "draft", "approved"))

    assert table.cell(0, 0).text == "Status: approved"


def test_edit_in_header():
    document = Document()
    section = document.sections[0]
    section.header.paragraphs[0].text = "Olymp confidential"

    apply_operation(document, EditOperation("remove", "confidential"))

    assert section.header.paragraphs[0].text == "Olymp "


def test_append():
    document = Document()
    document.add_paragraph("First paragraph.")

    apply_operation(document, EditOperation("insert", "", "Second paragraph.", "end"))

    assert document.paragraphs[-1].text == "First paragraph.Second paragraph."


def test_duplicate_target_is_detected():
    document = Document()
    document.add_paragraph("Plan weekly.")
    document.add_paragraph("Review weekly.")

    assert count_matches(document, "weekly") == 2


def test_planner_examples():
    assert plan_instruction("Replace 'weekly' with 'monthly'")[0].replacement == "monthly"
    assert plan_instruction("Remove 'Draft only.'")[0].action == "remove"
    inserted = plan_instruction("Insert 'urgent ' before 'review'")
    assert inserted[0].position == "before"
    assert plan_instruction("Append 'Thank you.'")[0].position == "end"


def test_model_operation_validation():
    operation = _operation_from_data(
        {
            "action": "replace",
            "target": "weekly check-in",
            "replacement": "monthly check-in",
        }
    )
    assert operation == EditOperation(
        "replace",
        "weekly check-in",
        "monthly check-in",
    )


def test_model_operation_rejects_empty_target():
    import pytest

    with pytest.raises(ValueError, match="require a target"):
        _operation_from_data({"action": "remove", "target": ""})


def test_model_operation_rejects_invalid_insert_position():
    import pytest

    with pytest.raises(ValueError, match="position"):
        _operation_from_data(
            {
                "action": "insert",
                "target": "review",
                "replacement": "urgent",
                "position": "inside",
            }
        )

