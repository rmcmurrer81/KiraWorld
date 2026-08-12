#!/usr/bin/env python3
"""Static append-only v2 binding for Qwen 3.5 resident-media acceptance.

This module deliberately does not import or execute either historical harness.
It reads their exact bytes once, verifies pinned SHA-256 values, parses the
current harness as inert Python syntax, and revalidates the four exact library
sources.  It cannot run a model, decode or play media, use a speaker, or create
an experience/memory record.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
EXACT_MODEL = "qwen3.5:9b"
EXACT_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
HISTORICAL_MEDIA_HARNESS_SHA256 = (
    "d7b527397c8c630dfda01834191b8839c4fc4300c372c6517e5926cb03267773"
)
CURRENT_MEDIA_HARNESS_SHA256 = (
    "f56927167a92eadf88f2ea9b61ef5a6ece9d8e96bc53f3d696331188e2279e23"
)
EXPECTED_MEDIA_QUESTIONS_SHA256 = (
    "3da59a2279f70b573887661c26c492603eb2a15fda3763406a0a09dbd3c3b4e2"
)
EXPECTED_BEHAVIOR_QUESTIONS_SHA256 = (
    "75244e80adc2c3ec541bd56c5c2e8bee16858f5e81360b14fce8768201f468d3"
)

BINDINGS: Mapping[str, Mapping[str, Any]] = {
    "historical_readiness": {
        "path": "RecoverySprint/continuation_20260808/qwen35_non_body_media_static_readiness/attempt_01/READINESS_CONFIG.json",
        "sha256": "ef6cbce3c8aabc63b9e2a087bfb4a6a42bc41351ae7236d7d8ffaaed23222632",
        "bytes": 6501,
    },
    "historical_overlay": {
        "path": "tools/run_qwen35_non_body_media_acceptance.py",
        "sha256": "7dda527c20810c0a2a924c75be8dcfcad0ba44db2b63415c21ed65007a0c7238",
        "bytes": 36845,
    },
    "current_media_harness": {
        "path": "tools/run_resident_media_experience_live_acceptance.py",
        "sha256": CURRENT_MEDIA_HARNESS_SHA256,
        "bytes": 74054,
    },
    "current_routes_checkpoint": {
        "path": "System/Docs/QWEN35_REMAINING_CURRENT_PERSON_ROUTES_STATIC_CHECKPOINT_20260809.md",
        "sha256": "cc9204b30eb447e047769da06a3f217d2584fef1bb4472acdbf880717e5038a6",
        "bytes": 9455,
    },
    "historical_extended_profile": {
        "path": "RecoverySprint/continuation_20260803/kira_turing_psych_non_body_extended_profile/attempt_01/TURING_PSYCH_NON_BODY_EXTENDED_CONFIG.json",
        "sha256": "f9b2713191890e4c605187162dd628950aaf9001858a1eb8124b96928f7b534f",
        "bytes": 7238,
    },
}

CONFIG_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260809"
    / "qwen35_non_body_media_static_readiness_v2"
    / "attempt_01"
    / "READINESS_CONFIG_V2.json"
)


class Qwen35MediaV2Error(RuntimeError):
    """A sealed static binding or truth boundary failed."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _project_file(relative: str) -> Path:
    path = ROOT / relative
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise Qwen35MediaV2Error(f"project binding escaped root: {relative}") from exc
    if path.is_symlink() or not resolved.is_file():
        raise Qwen35MediaV2Error(f"project binding is not a regular exact file: {relative}")
    return resolved


def _read_exact(binding: Mapping[str, Any], label: str) -> bytes:
    path = _project_file(str(binding.get("path") or ""))
    data = path.read_bytes()
    if len(data) != binding.get("bytes"):
        raise Qwen35MediaV2Error(f"{label} byte length changed")
    if _sha256(data) != binding.get("sha256"):
        raise Qwen35MediaV2Error(f"{label} SHA-256 changed")
    return data


def _strict_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Qwen35MediaV2Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_from_exact(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    data = _read_exact(binding, label)
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Qwen35MediaV2Error(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise Qwen35MediaV2Error(f"{label} is not an object")
    return value


def _literal_assignment(source: bytes, name: str) -> Any:
    try:
        tree = ast.parse(source.decode("utf-8"), filename="<sealed_current_media_harness>")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise Qwen35MediaV2Error("current media harness is not valid inert UTF-8 syntax") from exc
    values: list[Any] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            try:
                values.append(ast.literal_eval(node.value))
            except (ValueError, TypeError) as exc:
                raise Qwen35MediaV2Error(f"{name} is not an inert literal") from exc
    if len(values) != 1:
        raise Qwen35MediaV2Error(f"{name} assignment count is not exactly one")
    return values[0]


def _validate_library_sources(readiness: Mapping[str, Any]) -> list[dict[str, Any]]:
    media = readiness.get("resident_media_14_plus_8")
    if not isinstance(media, Mapping):
        raise Qwen35MediaV2Error("historical readiness omitted resident-media contract")
    if media.get("media_questions_sha256") != EXPECTED_MEDIA_QUESTIONS_SHA256:
        raise Qwen35MediaV2Error("media question digest changed")
    if media.get("behavior_questions_sha256") != EXPECTED_BEHAVIOR_QUESTIONS_SHA256:
        raise Qwen35MediaV2Error("behavior question digest changed")
    sources = media.get("sources")
    if not isinstance(sources, list) or len(sources) != 4:
        raise Qwen35MediaV2Error("exact four-source plan is missing")
    expected_ids = {
        "illustrated_magazine_cover_page_001",
        "unfamiliar_merlion_race_car_crop_page_014",
        "power_rangers_commercial_interval_000_008",
        "highlander_new_york_new_york_interval_000_010",
    }
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for raw in sources:
        if not isinstance(raw, Mapping):
            raise Qwen35MediaV2Error("source entry is not an object")
        item = dict(raw)
        stimulus_id = str(item.get("stimulus_id") or "")
        if stimulus_id in seen or stimulus_id not in expected_ids:
            raise Qwen35MediaV2Error("source identifier is duplicate or unexpected")
        seen.add(stimulus_id)
        relative = str(item.get("path") or "")
        if not relative.startswith("Data/library/"):
            raise Qwen35MediaV2Error("media source is outside the resident library")
        path = _project_file(relative)
        source_bytes = path.read_bytes()
        actual = _sha256(source_bytes)
        if actual != item.get("source_sha256"):
            raise Qwen35MediaV2Error(f"media source changed: {stimulus_id}")
        result.append(
            {
                "stimulus_id": stimulus_id,
                "path": relative,
                "source_sha256": actual,
                "binding_sha256": item.get("binding_sha256"),
                "source_bytes": len(source_bytes),
            }
        )
    if seen != expected_ids:
        raise Qwen35MediaV2Error("source set is incomplete")
    return result


def validate_static_v2() -> dict[str, Any]:
    readiness = _json_from_exact(BINDINGS["historical_readiness"], "historical readiness")
    _read_exact(BINDINGS["historical_overlay"], "historical overlay")
    harness = _read_exact(BINDINGS["current_media_harness"], "current media harness")
    _read_exact(BINDINGS["current_routes_checkpoint"], "current routes checkpoint")
    profile = _json_from_exact(BINDINGS["historical_extended_profile"], "historical profile")
    if (
        readiness.get("historical_artifacts", {})
        .get("resident_media_harness", {})
        .get("sha256")
        != HISTORICAL_MEDIA_HARNESS_SHA256
    ):
        raise Qwen35MediaV2Error("historical harness provenance was not preserved")
    if _literal_assignment(harness, "EXACT_QWEN_MODEL") != EXACT_MODEL:
        raise Qwen35MediaV2Error("current harness model name changed")
    if _literal_assignment(harness, "EXACT_QWEN_DIGEST") != EXACT_DIGEST:
        raise Qwen35MediaV2Error("current harness model digest changed")
    if readiness.get("exact_model") != {"name": EXACT_MODEL, "digest": EXACT_DIGEST}:
        raise Qwen35MediaV2Error("historical overlay exact-model contract changed")
    turns = profile.get("exact_measured_turns")
    invitation = profile.get("exact_invitation")
    if not isinstance(turns, list) or len(turns) != 8 or not isinstance(invitation, Mapping):
        raise Qwen35MediaV2Error("historical voluntary profile shape changed")
    sources = _validate_library_sources(readiness)
    return {
        "schema": "kira.qwen35_non_body_media_static_readiness.v2",
        "status": "STATIC_V2_BINDINGS_PASS_PENDING_INDEPENDENT_AUDIT",
        "exact_model": {"name": EXACT_MODEL, "digest": EXACT_DIGEST},
        "historical_harness_provenance_sha256": HISTORICAL_MEDIA_HARNESS_SHA256,
        "current_harness_sha256": CURRENT_MEDIA_HARNESS_SHA256,
        "historical_and_current_harness_are_distinct": (
            HISTORICAL_MEDIA_HARNESS_SHA256 != CURRENT_MEDIA_HARNESS_SHA256
        ),
        "media_questions_sha256": EXPECTED_MEDIA_QUESTIONS_SHA256,
        "behavior_questions_sha256": EXPECTED_BEHAVIOR_QUESTIONS_SHA256,
        "voluntary_profile_turn_count": len(turns),
        "exact_sources": sources,
        "live_execution_authorized": False,
        "model_or_media_executed": False,
        "experience_or_memory_created": False,
        "owner_present_acceptance_required": True,
    }


def load_and_validate_config() -> dict[str, Any]:
    data = CONFIG_PATH.read_bytes()
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Qwen35MediaV2Error("v2 config is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise Qwen35MediaV2Error("v2 config is not an object")
    derived = validate_static_v2()
    expected = value.get("derived_contract")
    if expected != derived:
        raise Qwen35MediaV2Error("v2 config does not match current derived contract")
    if value.get("execution_allowed") is not False:
        raise Qwen35MediaV2Error("v2 config cannot authorize execution")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-live", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.execute_live:
        raise SystemExit("v2 is static preparation only; live media/model execution is not authorized")
    print(json.dumps(load_and_validate_config(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
