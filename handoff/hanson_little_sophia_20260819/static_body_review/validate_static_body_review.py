#!/usr/bin/env python3
"""Read-only exact-identity validator for the curated static body review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


EXPECTED = {
    "MIND_BODY_STATIC_READINESS_BASELINE_20260818.json": (
        14775,
        "689a8d0edc0385f9d83b691b28d32eaee159f54ec47490cba525f000a2125470",
    ),
    "BODY_FACE_STATION_INTAKE_WORKSHEETS_20260818.json": (
        26572,
        "556acabd3a32dcc3cd26c6fe18767a0524095a0410878d5733b43d15f9237b16",
    ),
    "BODY_FACE_STATION_FUTURE_EVIDENCE_ORDER_20260818.json": (
        47970,
        "6392052b662231854bef15073ded3b922412895c9e02832797a5d4f531a96163",
    ),
    "INTENDED_BODY_NEUTRAL_CANDIDATE_ACQUISITION_BOUNDARY_V5.json": (
        38048,
        "fdd3384758b665c7c082bf59674b74006a4e5056653d93caff7c8de1038e5e99",
    ),
    "INTENDED_BODY_V5_AUDIT_DECISION.json": (
        1527,
        "ad8256e6ca68c2c105ede7b21290ef25b610434e02a0bc52542fc64349bfcada",
    ),
    "FACIAL_BLINK_LIPSYNC_EXACT_RIG_CONTROL_MAPPING_ACQUISITION_BOUNDARY_V4.json": (
        81987,
        "1b2da41b8a73ae6d121697aca8c49219074bddc3f623c436063360d211c8cc67",
    ),
    "FACIAL_V4_AUDIT_DECISION.json": (
        1533,
        "314fcd4a891f84af63965fdba3b125cb7d274483b0b3703735285599b4eedf09",
    ),
}


class ValidationError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value: str) -> Any:
    raise ValidationError(f"nonfinite JSON value: {value}")


def validate(root: Path) -> list[str]:
    issues: list[str] = []
    resolved = root.resolve(strict=True)
    for name, (expected_bytes, expected_sha) in EXPECTED.items():
        path = resolved / name
        if not path.is_file() or path.is_symlink():
            issues.append(f"missing or non-regular artifact: {name}")
            continue
        raw = path.read_bytes()
        observed_sha = hashlib.sha256(raw).hexdigest()
        if len(raw) != expected_bytes:
            issues.append(
                f"byte mismatch {name}: expected {expected_bytes}, observed {len(raw)}"
            )
        if observed_sha != expected_sha:
            issues.append(
                f"sha256 mismatch {name}: expected {expected_sha}, observed {observed_sha}"
            )
        try:
            text = raw.decode("utf-8-sig")
            json.loads(text, object_pairs_hook=_pairs, parse_constant=_nonfinite)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
            issues.append(f"strict JSON failure {name}: {exc}")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args(argv)
    issues = validate(args.root)
    if issues:
        print("STATIC_BODY_REVIEW FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("STATIC_BODY_REVIEW PASS_STATIC_DATA_ONLY_NO_GO")
    print(f"artifacts: {len(EXPECTED)}")
    print("materialized_body: false")
    print("robot_or_blender_authority: false")
    print("root_go: null")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
