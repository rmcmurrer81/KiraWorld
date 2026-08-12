"""Verify World Builder requests stay approval-first with preview artifacts."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import create_world_notebook_request as generator  # noqa: E402


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run() -> int:
    original_world_root = generator.DEFAULT_WORLD_ROOT
    original_index_path = generator.DEFAULT_INDEX_PATH
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="kira_world_builder_preview_") as temp:
        temp_root = Path(temp)
        generator.DEFAULT_WORLD_ROOT = temp_root / "worlds"
        generator.DEFAULT_INDEX_PATH = temp_root / "notebook_world_index.json"
        try:
            seed = generator.infer_seed("Test Coffee Shop", city="Home World", category="fictional_or_original_place")
            paths = generator.create_files(
                seed,
                requested_by="robert",
                trigger="approval preview smoke test",
                visibility="private_only",
                autonomy="request_mode",
                status="draft",
            )

            required = [
                "request",
                "blueprint_preview",
                "blueprint_map",
                "approval_gate",
                "tardis_review_stage",
            ]
            for key in required:
                if key not in paths or not paths[key].exists():
                    failures.append(f"missing {key}")

            request = read_json(paths["request"])
            approval = read_json(paths["approval_gate"])
            blueprint = read_json(paths["blueprint_preview"])
            tardis = read_json(paths["tardis_review_stage"])
            blueprint_text = paths["blueprint_map"].read_text(encoding="utf-8")

            if request.get("approval_workflow", {}).get("auto_place_in_existing_world") is not False:
                failures.append("request approval workflow allows auto placement")
            if approval.get("world_builder_may_commit_to_world") is not False:
                failures.append("approval gate allows commit")
            if approval.get("requires_robert_approval") is not True:
                failures.append("approval gate does not require Robert approval")
            if blueprint.get("approval_policy", {}).get("status") != "draft_not_placed":
                failures.append("blueprint preview is not draft_not_placed")
            if "TARDIS" not in tardis.get("stage_name", ""):
                failures.append("TARDIS review stage missing")
            if "Do not place" not in blueprint_text:
                failures.append("blueprint map missing do-not-place warning")

            report = {
                "schema_version": 1,
                "status": "passed" if not failures else "failed",
                "failures": failures,
                "checked_files": {key: str(path) for key, path in paths.items()},
            }
        finally:
            generator.DEFAULT_WORLD_ROOT = original_world_root
            generator.DEFAULT_INDEX_PATH = original_index_path

    out = ROOT / "Data" / "world_builds" / "tests" / "world_builder_approval_preview_20260713.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": not failures, "report": str(out.relative_to(ROOT)), "failures": failures}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(run())
