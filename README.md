# OLYMP Word Document Editor

A Python and LangGraph agent that interprets editing requests with a chat model, then applies validated text operations to an existing Word document. The model plans edits; local Python tools perform them. The model never receives shell access or document-editing code execution.

## Requirements

- Python 3.11+
- An API key for an OpenAI-compatible chat-completions service

The default model is `gpt-4o-mini`. Configure the key through `OPENAI_API_KEY`; do not commit keys to this repository. An organization can use `OPENAI_BASE_URL` to point at its approved compatible endpoint and `OPENAI_MODEL` to select a model.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:OPENAI_API_KEY = "insert-company-key-here"
```

Set the key through your deployment secret manager for hosted use. Do not put a real key in source control or share it with sample documents.

## Run an AI edit

```powershell
doc-agent sample\clinical_note.docx "Change the check-in frequency to monthly" sample\clinical_note_edited.docx
```

Or:

```powershell
python -m olymp_doc_agent.cli sample\clinical_note.docx "Change the check-in frequency to monthly" sample\clinical_note_edited.docx
```

The LangGraph planning node sends the instruction and document text to the configured model. It receives a structured JSON edit plan. Local validation rejects missing or ambiguous targets; the local editor then changes only the relevant text and writes a new `.docx`.

## Offline mode

For testing the editing tools without an API key, use the limited quoted-command parser:

```powershell
python -m olymp_doc_agent.cli --offline sample\clinical_note.docx "Replace 'weekly' with 'monthly'" sample\clinical_note_edited.docx
```

Offline mode is deterministic and is **not** the AI functionality. It supports:

- `Replace 'old text' with 'new text'`
- `Remove 'text'`
- `Insert 'new text' before 'anchor'`
- `Insert 'new text' after 'anchor'`
- `Append 'text'`

## Architecture

The LangGraph workflow has four nodes:

1. **Plan** — sends the request and document text to the configured model, which returns typed operations or a clarification request.
2. **Validate** — checks operation types and fields, then requires each target or anchor to appear exactly once.
3. **Edit** — uses `python-docx` and WordprocessingML text nodes to make the changes locally.
4. **Verify** — checks package entries and document structure/media invariants, then reports output details.

The model is not given tools that can execute code or edit files. Instructions embedded in document text are treated as untrusted content, and model output is validated before use.

## Data handling

In AI mode, document text (up to 40,000 characters) and the editing request are sent to the configured model service. Use only documents and endpoints approved by the organization. The included sample is synthetic and contains no patient data. Offline mode does not contact a model service.

## Test before submitting

Run the automated tests:

```powershell
python -m pytest -q
```

They use a fake model response and do not require a key or make network requests. They cover model-plan parsing and validation, edit behavior, ambiguous targets, formatting, tables, headers, and images.

Then test the actual AI path using a company-approved key and the synthetic sample:

```powershell
python -m olymp_doc_agent.cli sample\clinical_note.docx "Change the check-in frequency to monthly" sample\clinical_note_ai_output.docx
```

Open the output in Word and confirm that the requested frequency changed while the heading, table, header, and other text remain intact. Also test a vague request and confirm the agent stops with a clarification/error instead of changing an uncertain target.

## Limitations

- Text in drawing text boxes, embedded objects, and tracked revisions is not edited.
- A target spanning multiple paragraphs is not supported.
- A target that occurs multiple times is rejected as ambiguous; provide more specific wording.
- `python-docx` may normalize some internal package details when saving.
- The model/API service and its behavior depend on the organization's selected endpoint and model.
