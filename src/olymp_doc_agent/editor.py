from typing import Iterator

from docx.document import Document as DocumentType
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from lxml import etree

from .models import EditOperation

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def iter_paragraphs(document: DocumentType) -> Iterator[Paragraph]:
    for paragraph in document.paragraphs:
        yield paragraph
    for table in document.tables:
        yield from iter_table_paragraphs(table)
    for section in document.sections:
        yield from section.header.paragraphs
        for table in section.header.tables:
            yield from iter_table_paragraphs(table)
        yield from section.footer.paragraphs
        for table in section.footer.tables:
            yield from iter_table_paragraphs(table)


def iter_table_paragraphs(table: Table) -> Iterator[Paragraph]:
    for row in table.rows:
        for cell in row.cells:
            yield from iter_cell_paragraphs(cell)


def iter_cell_paragraphs(cell: _Cell) -> Iterator[Paragraph]:
    for paragraph in cell.paragraphs:
        yield paragraph
    for table in cell.tables:
        yield from iter_table_paragraphs(table)


def _run_text(run) -> str:
    parts = []
    for child in run._r:
        tag = child.tag
        if tag == f"{{{W_NS}}}t":
            parts.append(child.text or "")
        elif tag == f"{{{W_NS}}}tab":
            parts.append("\t")
        elif tag == f"{{{W_NS}}}br":
            parts.append("\n")
    return "".join(parts)


def _set_run_text(run, text: str) -> None:
    for child in list(run._r):
        if child.tag in {
            f"{{{W_NS}}}t",
            f"{{{W_NS}}}tab",
            f"{{{W_NS}}}br",
        }:
            run._r.remove(child)
    if text:
        node = etree.Element(f"{{{W_NS}}}t")
        if text.startswith(" ") or text.endswith(" "):
            node.set(f"{{{W_NS}}}space", "preserve")
        node.text = text
        run._r.append(node)


def paragraph_plain_text(paragraph: Paragraph) -> str:
    return "".join(_run_text(run) for run in paragraph.runs)


def _apply_span(paragraph: Paragraph, start: int, end: int, replacement: str) -> None:
    runs = paragraph.runs
    if not runs:
        return

    boundaries = []
    cursor = 0
    for index, run in enumerate(runs):
        length = len(_run_text(run))
        boundaries.append((cursor, cursor + length, index))
        cursor += length

    start_run = None
    end_run = None
    start_local = 0
    end_local = 0
    for begin, finish, index in boundaries:
        if begin <= start < finish:
            start_run = index
            start_local = start - begin
        if begin < end <= finish:
            end_run = index
            end_local = end - begin
    if start_run is None:
        for begin, finish, index in boundaries:
            if finish == start:
                start_run, start_local = index, finish - begin
                break
    if end_run is None:
        for begin, finish, index in boundaries:
            if finish == end:
                end_run, end_local = index, end - begin
                break
    if start_run is None or end_run is None:
        return

    start_text = _run_text(runs[start_run])
    end_text = _run_text(runs[end_run])
    if start_run == end_run:
        _set_run_text(runs[start_run], start_text[:start_local] + replacement + start_text[end_local:])
        return

    _set_run_text(runs[start_run], start_text[:start_local] + replacement)
    _set_run_text(runs[end_run], end_text[end_local:])
    for index in range(start_run + 1, end_run):
        _set_run_text(runs[index], "")


def count_matches(document: DocumentType, target: str) -> int:
    if not target:
        return 0
    return sum(paragraph_plain_text(p).count(target) for p in iter_paragraphs(document))


def apply_operation(document: DocumentType, operation: EditOperation) -> int:
    matched = 0

    if operation.action == "insert" and operation.position == "end":
        if document.paragraphs:
            paragraph = document.paragraphs[-1]
            run = paragraph.add_run(operation.replacement)
            matched = 1
        else:
            document.add_paragraph(operation.replacement)
            matched = 1
        return matched

    for paragraph in iter_paragraphs(document):
        text = paragraph_plain_text(paragraph)
        target = operation.target
        if not target:
            continue

        for match_start in reversed(list(_all_match_starts(text, target))):
            match_end = match_start + len(target)
            if operation.action == "replace":
                _apply_span(paragraph, match_start, match_end, operation.replacement)
            elif operation.action == "remove":
                _apply_span(paragraph, match_start, match_end, "")
            elif operation.action == "insert":
                anchor_end = match_end if operation.position == "after" else match_start
                _apply_span(paragraph, anchor_end, anchor_end, operation.replacement)
            matched += 1
    return matched


def _all_match_starts(text: str, target: str) -> Iterator[int]:
    start = 0
    while True:
        index = text.find(target, start)
        if index < 0:
            return
        yield index
        start = index + len(target)
