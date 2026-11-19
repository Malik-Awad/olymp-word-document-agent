import json
import os
import re
from typing import Iterable

from .models import EditOperation


def fallback_plan(instruction: str) -> list[EditOperation]:
    text = instruction.strip()

    replace = re.match(
        r"(?is)^(?:please\s+)?replace\s+(?:the\s+text\s+)?[\"'](.+?)[\"']\s+(?:with|by)\s+[\"'](.+?)[\"']\s*[.!]?$",
        text,
    )
    if replace:
        return [EditOperation("replace", replace.group(1), replace.group(2))]

    remove = re.match(
        r"(?is)^(?:please\s+)?(?:remove|delete)\s+(?:the\s+text\s+)?[\"'](.+?)[\"']\s*[.!]?$",
        text,
    )
    if remove:
        return [EditOperation("remove", remove.group(1))]

    insert = re.match(
        r"(?is)^(?:please\s+)?(?:insert|add)\s+[\"'](.+?)[\"']\s+(before|after)\s+[\"'](.+?)[\"']\s*[.!]?$",
        text,
    )
    if insert:
        return [EditOperation("insert", insert.group(3), insert.group(1), insert.group(2))]

    append = re.match(
        r"(?is)^(?:please\s+)?(?:append|add)\s+(?:at\s+the\s+end\s+)?[\"'](.+?)[\"']\s*[.!]?$",
        text,
    )
    if append:
        return [EditOperation("insert", "", append.group(1), "end")]

    raise ValueError(
        "Instruction could not be planned safely. Use: replace 'old' with 'new', "
        "remove 'text', insert 'text' before|after 'anchor', or append 'text'."
    )


def claude_plan(instruction: str, model: str | None = None) -> list[EditOperation]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:
        raise RuntimeError("Install the project dependencies, including langchain-anthropic") from exc

    llm = ChatAnthropic(
        model=model or "claude-sonnet-4-5-20250929",
        temperature=0,
        max_tokens=800,
    )
    system = (
        "You convert document editing instructions into a JSON array of precise operations. "
        "Return only valid JSON, with no markdown. Allowed actions: replace, remove, insert. "
        "For replace: {\"action\":\"replace\",\"target\":\"exact text\",\"replacement\":\"new text\"}. "
        "For remove: {\"action\":\"remove\",\"target\":\"exact text\"}. "
        "For insert: {\"action\":\"insert\",\"target\":\"exact anchor text\",\"replacement\":\"text to insert\",\"position\":\"before|after|end\"}. "
        "Use position=end and target=\"\" only to append. Never include prose or shell/code operations."
    )
    response = llm.invoke([("system", system), ("user", instruction)])
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Claude plan must be a JSON array")
    return [_operation_from_data(item) for item in data]


def _operation_from_data(item: object) -> EditOperation:
    if not isinstance(item, dict):
        raise ValueError("Each Claude operation must be an object")
    action = item.get("action")
    target = item.get("target", "")
    replacement = item.get("replacement", "")
    position = item.get("position", "after")
    if action not in {"replace", "remove", "insert"}:
        raise ValueError(f"Unsupported edit action: {action}")
    if not isinstance(target, str) or not isinstance(replacement, str):
        raise ValueError("Operation target and replacement must be strings")
    if action == "remove":
        replacement = ""
    if action == "insert":
        if position not in {"before", "after", "end"}:
            raise ValueError("Insert position must be before, after, or end")
    else:
        position = "after"
    if action != "insert" and not target:
        raise ValueError("Replace/remove operations require a target")
    if action == "replace" and not replacement:
        raise ValueError("Replacement text is required")
    if action == "insert" and (not replacement or (position != "end" and not target)):
        raise ValueError("Insert requires replacement text and an anchor unless appending")
    return EditOperation(action, target, replacement, position)
