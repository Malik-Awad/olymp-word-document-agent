# OLYMP Word Document Editor

This project implements a LangGraph-based agent that makes limited, auditable changes to existing `.docx` files. The runtime is provider-neutral and has no model API dependency: natural-language instructions are converted by a local planner into typed edit operations.

## Setup

Requires Python 3.11+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
doc-agent sample\clinical_note.docx "Replace 'weekly' with 'biweekly'" sample\clinical_note_edited.docx
```

Or run as a module:

```powershell
python -m olymp_doc_agent.cli sample\clinical_note.docx "Remove 'Draft only.'" sample\clinical_note_edited.docx
```

## Supported instructions

- Replace text: `Replace 'old text' with 'new text'`
- Remove text: `Remove 'old text'`
- Insert after text: `Insert 'new text' after 'anchor text'`
- Insert before text: `Insert 'new text' before 'anchor text'`
- Append text to a document: `Append 'text'`

The planner is restricted to these action types. The agent validates every plan before editing and refuses ambiguous or unsupported instructions instead of guessing.

## Architecture

The LangGraph workflow is:

1. `plan`: the local parser converts the instruction into typed edit operations.
2. `validate`: operations are checked for a supported action, required fields, and a unique target.
3. `edit`: directly manipulates WordprocessingML text nodes with `python-docx`.
4. `verify`: checks the target and document integrity invariants, saves to a new file, and compares key package properties.

The runtime does not expose shell access or general code execution. All document changes are made only by the typed Python editing tools.

## Preservation approach

- The implementation copies the input package before editing conceptually and writes a new output; it never performs in-place edits.
- Edits are scoped to paragraphs and table cells in the document body, headers, and footers.
- Existing run properties (bold, italic, size, color, fonts, character styles) are retained by changing text nodes rather than recreating runs.
- Images and other drawing XML are left intact.
- Tables, section properties, hyperlinks, comments, and document metadata are preserved by the source package unless an edit itself requires text outside a run.
- Verification ensures package entries are not removed, permits expected Word metadata/header/footer entries, and compares media, table, image, header, and footer counts.

## Testing

```powershell
python -m pytest -q
```

The tests cover replacement, removal, insertion, formatted text, tables, images, headers, ambiguity, and package integrity.

The sample document demonstrates replacement of `weekly` with `monthly`; the original table and header remain unchanged. Run:

```powershell
python -m olymp_doc_agent.cli sample\clinical_note.docx "Replace 'weekly' with 'monthly'" sample\clinical_note_edited.docx
```

## Known limitations

- Text in drawing text boxes, text in embedded objects, and tracked revisions is not edited.
- Text split across paragraphs cannot be matched in a single operation.
- Comments, SmartArt, and tracked changes may be retained but are not treated as editable content.
- Natural-language support is limited to the documented quoted instruction formats.
- Saving through `python-docx` can normalize some package internals even though it preserves normal Word document content and formatting.

*** Add File: src/olymp_doc_agent/__init__.py
"""AI-assisted, structure-preserving Word document editing."""

from .agent import EditAgent

__all__ = ["EditAgent"]

