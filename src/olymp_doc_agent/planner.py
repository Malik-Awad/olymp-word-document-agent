import re

from .models import EditOperation


def plan_instruction(instruction: str) -> list[EditOperation]:
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
