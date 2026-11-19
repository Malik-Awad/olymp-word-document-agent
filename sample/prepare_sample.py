from pathlib import Path

from docx import Document


def main() -> None:
    sample_dir = Path(__file__).resolve().parent
    document = Document()
    title = document.add_heading("Weekly Care Plan", 0)
    title.alignment = 1

    paragraph = document.add_paragraph()
    paragraph.add_run("Client: ").bold = True
    paragraph.add_run("Synthetic client")

    document.add_paragraph(
        "The client is scheduled for a weekly check-in. "
        "Review progress and confirm the next appointment."
    )
    document.add_paragraph("Draft only.")

    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Goal"
    table.cell(0, 1).text = "Status"
    table.cell(1, 0).text = "Complete sample documentation"
    table.cell(1, 1).text = "In progress"

    section = document.sections[0]
    section.header.paragraphs[0].text = "OLYMP - Synthetic sample"
    document.save(sample_dir / "clinical_note.docx")


if __name__ == "__main__":
    main()
