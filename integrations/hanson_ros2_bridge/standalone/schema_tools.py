from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


RFC3339_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _is_rfc3339_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if RFC3339_DATE_TIME.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def strict_format_checker() -> FormatChecker:
    """Return a checker whose RFC 3339 validation has no optional dependency."""

    checker = FormatChecker()
    checker.checks("date-time")(_is_rfc3339_date_time)
    return checker


def schema_validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=strict_format_checker())
