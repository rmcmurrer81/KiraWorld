from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StrictJSONError(ValueError):
    """JSON was syntactically valid-looking but unsafe or ambiguous."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise StrictJSONError(f"non-finite JSON number is forbidden: {value}")


def loads_strict(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_object_without_duplicates,
        parse_constant=_reject_nonfinite,
    )


def load_path_strict(path: Path) -> Any:
    return loads_strict(path.read_text(encoding="utf-8"))
