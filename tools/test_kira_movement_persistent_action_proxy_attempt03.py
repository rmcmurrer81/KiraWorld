#!/usr/bin/env python3
"""Focused no-Blender test of Attempt 03's exact proxy mapping behavior."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
WORKER = ROOT / "Tools/blender_author_kira_r21_action_only_movement_attempt03.py"


class DummyAction:
    def __init__(self) -> None:
        self.name = "DUMMY_ACTION"
        self.frame_range = (1.0, 30.0)
        self._values = {"private_owner_review_only": True, "pose_id": "dummy"}

    def keys(self) -> list[str]:
        return list(self._values)

    def __getitem__(self, key: str) -> Any:
        return self._values[key]


def load_exact_proxy_class() -> type:
    tree = ast.parse(WORKER.read_text(encoding="utf-8"), filename=str(WORKER))
    future = next(
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "__future__"
    )
    proxy = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "PersistentActionProxy"
    )
    module = ast.Module(body=[future, proxy], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, Any] = {"Any": Any}
    exec(compile(module, str(WORKER), "exec"), namespace)
    return namespace["PersistentActionProxy"]


def main() -> int:
    proxy_type = load_exact_proxy_class()
    raw = DummyAction()
    proxy = proxy_type(raw)
    assert proxy.name == "DUMMY_ACTION"
    assert proxy.frame_range == (1.0, 30.0)
    assert sorted(proxy.keys()) == ["pose_id", "private_owner_review_only"]
    assert proxy["private_owner_review_only"] is True
    assert proxy["pose_id"] == "dummy"
    assert proxy.raw is raw
    print("PERSISTENT_ACTION_PROXY_ATTEMPT03_MAPPING_TEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
