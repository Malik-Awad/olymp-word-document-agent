from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class EditOperation:
    action: Literal["replace", "remove", "insert"]
    target: str
    replacement: str = ""
    position: Literal["before", "after", "end"] = "after"

