from pathlib import Path

from docx import Document

from .editor import apply_operation, count_matches
from .planner import plan_instruction
from .verification import package_media, structural_signature, verify_input_output


class EditAgent:
    def run(self, input_path: str, instruction: str, output_path: str) -> dict:
        source = Path(input_path)
        destination = Path(output_path)
        if not source.is_file():
            raise FileNotFoundError(input_path)
        if source.suffix.lower() != ".docx":
            raise ValueError("Input must be a .docx file")
        destination.parent.mkdir(parents=True, exist_ok=True)

        def plan(state: dict) -> dict:
            try:
                operations = plan_instruction(state["instruction"])
                state["operations"] = operations
            except Exception as exc:
                state["error"] = str(exc)
            return state

        def validate(state: dict) -> dict:
            if state["error"]:
                return state
            operations = state["operations"] or []
            if not operations:
                state["error"] = "The instruction produced no edit operations"
                return state
            document = Document(state["input_path"])
            for operation in operations:
                if operation.action == "replace" and not operation.replacement:
                    state["error"] = "Replace operation has no replacement text"
                    return state
                if operation.action in {"replace", "remove"}:
                    count = count_matches(document, operation.target)
                    if count == 0:
                        state["error"] = f'Target text was not found: "{operation.target}"'
                        return state
                    if count > 1:
                        state["error"] = (
                            f'Target text is ambiguous ({count} matches): "{operation.target}". '
                            "Please include more surrounding context."
                        )
                        return state
                if operation.action == "insert" and operation.position != "end":
                    count = count_matches(document, operation.target)
                    if count == 0:
                        state["error"] = f'Insert anchor was not found: "{operation.target}"'
                        return state
                    if count > 1:
                        state["error"] = (
                            f'Insert anchor is ambiguous ({count} matches): "{operation.target}". '
                            "Please include more surrounding context."
                        )
                        return state
            state["matches"] = sum(
                count_matches(document, op.target)
                for op in operations
                if op.action != "insert" or op.position != "end"
            )
            return state

        def edit(state: dict) -> dict:
            if state["error"]:
                return state
            document = Document(state["input_path"])
            before_signature = structural_signature(document)
            before_media = package_media(document)
            for operation in state["operations"]:
                apply_operation(document, operation)
            after_signature = structural_signature(document)
            after_media = package_media(document)
            if before_signature != after_signature:
                state["error"] = "Edit changed document structure"
                return state
            if before_media != after_media:
                state["error"] = "Edit changed embedded media"
                return state
            document.save(state["output_path"])
            state["media_count"] = len(after_media)
            return state

        def verify(state: dict) -> dict:
            if state["error"]:
                return state
            try:
                verify_input_output(state["input_path"], state["output_path"])
                document = Document(state["output_path"])
                signature = structural_signature(document)
                state["table_count"] = signature[0]
                state["image_count"] = signature[1]
                state["header_count"] = signature[2]
                state["footer_count"] = signature[3]
            except Exception as exc:
                state["error"] = str(exc)
            return state

        initial = {
            "input_path": str(source),
            "output_path": str(destination),
            "instruction": instruction,
            "operations": None,
            "matches": 0,
            "error": None,
        }
        try:
            from langgraph.graph import END, StateGraph

            builder = StateGraph(dict)
            builder.add_node("plan", plan)
            builder.add_node("validate", validate)
            builder.add_node("edit", edit)
            builder.add_node("verify", verify)
            builder.set_entry_point("plan")
            builder.add_edge("plan", "validate")
            builder.add_edge("validate", "edit")
            builder.add_edge("edit", "verify")
            builder.add_edge("verify", END)
            graph = builder.compile()
            return graph.invoke(initial)
        except ImportError:
            state = plan(initial)
            state = validate(state)
            state = edit(state)
            return verify(state)
