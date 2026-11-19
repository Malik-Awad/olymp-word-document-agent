import hashlib
from zipfile import ZipFile

from docx.document import Document as DocumentType

from .editor import iter_paragraphs, paragraph_plain_text


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_media(document: DocumentType) -> list[str]:
    package = document.part.package
    media = []
    for part in package.parts:
        if str(part.partname).startswith("/word/media/"):
            media.append(hashlib.sha256(part.blob).hexdigest())
    return sorted(media)


def structural_signature(document: DocumentType) -> tuple[int, int, int, int]:
    table_count = len(document.tables)
    image_count = sum(
        1
        for paragraph in iter_paragraphs(document)
        for run in paragraph.runs
        if run._r.xpath(".//wp:docPr")
    )
    header_count = sum(len(section.header.paragraphs) for section in document.sections)
    footer_count = sum(len(section.footer.paragraphs) for section in document.sections)
    return table_count, image_count, header_count, footer_count


def verify_input_output(input_path: str, output_path: str) -> None:
    with ZipFile(input_path) as source, ZipFile(output_path) as result:
        source_entries = set(source.namelist())
        result_entries = set(result.namelist())
        added = result_entries - source_entries
        removed = source_entries - result_entries
        if removed:
            raise RuntimeError(f"Document package lost entries: {sorted(removed)}")
        unexpected_added = added - {
            name
            for name in added
            if name.startswith("docProps/")
            or name.startswith("word/header")
            or name.startswith("word/footer")
            or name.startswith("word/_rels/header")
            or name.startswith("word/_rels/footer")
        }
        if unexpected_added:
            raise RuntimeError(f"Unexpected package entries: {sorted(unexpected_added)}")
