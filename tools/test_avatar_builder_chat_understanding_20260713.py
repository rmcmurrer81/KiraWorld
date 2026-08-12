"""Exercise Avatar Builder chat understanding for Robert's correction requests."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Core.avatar_builder_ai as builder_ai  # noqa: E402


TESTS = [
    {
        "candidate_id": "kira",
        "message": "Give Kira realistic brown eyes and place them inside her eye sockets.",
        "required_intents": {"eye_color:brown"},
        "required_fields": {"requested_eye_color": "brown"},
    },
    {
        "candidate_id": "kira",
        "message": "Give Kira eyes.",
        "required_intents": {"eyes"},
        "required_fields": {},
    },
    {
        "candidate_id": "kira",
        "message": "Kira is an adult and update the body to fit that adult body policy.",
        "required_intents": {"maturity:adult", "body_shape"},
        "required_fields": {"maturity_override": "adult"},
        "required_truthy_fields": {"confirmed_adult_classification_evidence"},
    },
    {
        "candidate_id": "spider_gwen_spider_gwen_20260606_013325",
        "message": "The eyes are too flat; make them round instead of flattened and seat them back in the sockets.",
        "required_intents": {"eyes"},
        "required_fields": {},
    },
    {
        "candidate_id": "spider_gwen_spider_gwen_20260606_013325",
        "message": "Gwen's body and head shape are off; update the adult body and head fit with warmer skin tone and stop the barbie doll treatment.",
        "required_intents": {"body_shape", "head_shape_or_size", "skin_tone", "anatomy_policy", "adult_body_fit"},
        "required_fields": {
            "adult_body_fit_status": "failed_requires_landmark_lattice_sculpt_fit",
        },
    },
    {
        "candidate_id": "spider_gwen_spider_gwen_20260606_013325",
        "message": "Gwen is 5 feet and 10 inches tall, so scale the adult female base before body fitting.",
        "required_intents": {"measurement:height", "body_shape", "adult_body_fit"},
        "required_fields": {"target_height_m": 1.778},
    },
    {
        "candidate_id": "spider_gwen_spider_gwen_20260606_013325",
        "message": "Research online for better Blender adult body anatomy fitting and eye socket modeling solutions.",
        "required_intents": {"online_learning", "body_shape", "eyes", "anatomy_policy"},
        "required_fields": {},
    },
]


CANONICAL_WRITE_TARGETS = (
    ROOT / "Avatar" / "avatar_builder" / "builder_memory.json",
    ROOT / "Avatar" / "avatar_builder" / "body_training" / "body_fit_plans" / "kira_adult_body_fit_plan.json",
    ROOT / "Avatar" / "avatar_builder" / "eye_training" / "kira_eye_rebuild_plan.json",
    ROOT / "Avatar" / "avatar_builder" / "eye_training" / "spider_gwen_spider_gwen_20260606_013325_eye_rebuild_plan.json",
    ROOT / "Avatar" / "avatar_builder" / "body_training" / "body_fit_plans" / "spider_gwen_spider_gwen_20260606_013325_adult_body_fit_plan.json",
    ROOT / "Avatar" / "avatar_builder" / "tests" / "avatar_builder_chat_understanding_20260713.json",
    ROOT / "Avatar" / "temp_ai" / "kira" / "avatar_builder_adjustments.json",
    ROOT / "Avatar" / "temp_ai" / "spider_gwen_spider_gwen_20260606_013325" / "avatar_builder_adjustments.json",
)


def file_hashes(paths: tuple[Path, ...]) -> dict[str, str | None]:
    return {
        path.relative_to(ROOT).as_posix(): (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        )
        for path in paths
    }


def run() -> int:
    canonical_before = file_hashes(CANONICAL_WRITE_TARGETS)
    results = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="avatar_builder_chat_understanding_") as temp_dir:
        isolated_root = Path(temp_dir)
        isolated_builder = isolated_root / "Avatar" / "avatar_builder"
        with (
            patch.object(builder_ai, "PROJECT_ROOT", isolated_root),
            patch.object(builder_ai, "AVATAR_TEMP_DIR", isolated_root / "Avatar" / "temp_ai"),
            patch.object(builder_ai, "AVATAR_STATE_DIR", isolated_root / "Avatar" / "state" / "temp_ai"),
            patch.object(builder_ai, "BUILDER_ROOT", isolated_builder),
            patch.object(builder_ai, "GLOBAL_MEMORY_PATH", isolated_builder / "builder_memory.json"),
            patch.object(builder_ai, "HAIR_TRAINING_ROOT", isolated_builder / "hair_training"),
            patch.object(builder_ai, "BODY_TRAINING_ROOT", isolated_builder / "body_training"),
            patch.object(builder_ai, "model_path_for_candidate", return_value=None),
        ):
            for test in TESTS:
                output = builder_ai.avatar_builder_chat(test["candidate_id"], test["message"], None)
                adjustments = builder_ai.load_adjustments(test["candidate_id"])
                intents = set(adjustments.get("last_understood_intents") or [])
                missing = sorted(set(test["required_intents"]) - intents)
                bad_fields = []
                for key, expected in test["required_fields"].items():
                    if adjustments.get(key) != expected:
                        bad_fields.append({"field": key, "expected": expected, "actual": adjustments.get(key)})
                for key in test.get("required_truthy_fields", set()):
                    if not adjustments.get(key):
                        bad_fields.append({"field": key, "expected": "truthy", "actual": adjustments.get(key)})
                result = {
                    "candidate_id": test["candidate_id"],
                    "message": test["message"],
                    "reply": output.get("reply", ""),
                    "understood_intents": sorted(intents),
                    "missing_required_intents": missing,
                    "bad_fields": bad_fields,
                    "ok": not missing and not bad_fields,
                }
                results.append(result)
                if not result["ok"]:
                    failures.append(result)

    canonical_after = file_hashes(CANONICAL_WRITE_TARGETS)
    if canonical_after != canonical_before:
        failures.append({
            "error": "isolated_test_mutated_canonical_avatar_builder_files",
            "before": canonical_before,
            "after": canonical_after,
        })

    report = {
        "schema_version": 1,
        "created_at": builder_ai.now_iso(),
        "status": "passed" if not failures else "failed",
        "results": results,
        "canonical_files_unchanged": canonical_after == canonical_before,
    }
    print(json.dumps({"ok": not failures, "report": "in_memory_only", "failures": failures, "summary": report}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(run())
