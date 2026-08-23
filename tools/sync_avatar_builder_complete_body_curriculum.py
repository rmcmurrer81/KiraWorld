#!/usr/bin/env python3
"""Persist the current bound complete-body curriculum into Avatar Builder memory."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_builder_ai import teach_complete_body_curriculum  # noqa: E402


def main() -> int:
    result = teach_complete_body_curriculum()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
