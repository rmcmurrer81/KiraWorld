#!/usr/bin/env python3
"""Minimal append-only bootstrap for Kira R20 author Attempt 05.

The sealed Attempt 04 Blender worker, config, mutation gates, save path logic,
pose tests, and fresh-process verifier stay byte-for-byte unchanged.  This
bootstrap verifies those authorities, binds only the pure Attempt 05
``build_positions`` function in the current process, and reroutes the already
validated author output from historical ``attempt_04`` to new ``attempt_05``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from typing import Any, Mapping


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_author_kira_r20_pelvis_only as sealed_worker  # noqa: E402
from Core import kira_r20_attempt05_patchwide_quality_repair as repair  # noqa: E402


WORKER_ID = "KIRA_R20_PELVIS_ONLY_AUTHORING_WORKER_ATTEMPT05_BOUNDED_METRIC_V1"
SEALED_AUTHOR_OUTPUT_REL = (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04"
)
ATTEMPT05_AUTHOR_OUTPUT_REL = (
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_05"
)

SEALED_FILE_HASHES = {
    "Core/kira_r20_curvilinear_pelvic_patch.py": (
        "fe5b9f8b68dd7acd9b6eaaaf26d12d65fe0e3e263548e8979bcb26c0e58f640d"
    ),
    "tools/blender_author_kira_r20_pelvis_only.py": (
        "2b18b3050777f0fe6e414a882e2faa83cc80249ca52d86037a4cfacc78d9329a"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json": (
        "5ab9d60a948d7cac4e08e71a0f9c3927af9f33004ef23f888cc60f21b2e9e7cc"
    ),
    "Testing/test_kira_r20_pelvis_only_authoring.py": (
        "8e12b0573db0715ea339a163d705aa856142e3fbeee9f02e05e96fb3145bc71a"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04/AUTHORING_SUMMARY.json": (
        "66607972ca0678355b87b425678c952cc2b82fdd193894be7bb2666e5186c7af"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04/AUTHOR_FAILURE.json": (
        "e0840aef480144a72221646ef4b67fcda1da5404429e4df46957239a6237f07e"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04/"
    "r20_candidate_a_balanced_organic/FAILURE_EVIDENCE.json": (
        "468b4a8366ce78231b24fada48771a14ca4e96bc8324aec26b2ccbadddcc2299"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04/"
    "r20_candidate_b_soft_natural/FAILURE_EVIDENCE.json": (
        "a60b8b0ad47cbb87d453a34c845850d5e650b23005913c641cbc6cf1dd31fd28"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01/"
    "QUALITY_DIAGNOSTIC_EVIDENCE.json": (
        "3d44a5ac098e647a33e77740663ff88fa983f78d79ccf67e5f74866a29092950"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01/CHECKPOINT.md": (
        "9de4862ddff56ceabba8922152a2223708af088cd29f1285ff0e291cea26a1e4"
    ),
    "RecoverySprint/continuation_20260802/"
    "kira_r20_pelvis_only_authoring/attempt_04_quality_diagnostic_01/"
    "PACKAGE_MANIFEST.json": (
        "b583473840385c52887dec11fd5043bb8bc7074cc0e1fef398707f1b69ec0aca"
    ),
}

EXPECTED_ATTEMPT04_RELATIVE_FILE_SET = {
    "AUTHORING_SUMMARY.json",
    "AUTHOR_FAILURE.json",
    "r20_candidate_a_balanced_organic/FAILURE_EVIDENCE.json",
    "r20_candidate_b_soft_natural/FAILURE_EVIDENCE.json",
}

_ORIGINAL_VALIDATE_CONFIG = sealed_worker.validate_config
_ORIGINAL_BUILD_POSITIONS = sealed_worker.patch_contract.build_positions
_ORIGINAL_WORKER_ID = sealed_worker.WORKER_ID


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_authorities() -> None:
    for relative, expected in SEALED_FILE_HASHES.items():
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"Attempt 05 authority is missing: {relative}")
        actual = _sha256_file(path)
        if actual != expected:
            raise RuntimeError(
                f"Attempt 05 authority hash drifted: {relative}: {actual} != {expected}"
            )
    attempt04 = PROJECT_ROOT / SEALED_AUTHOR_OUTPUT_REL
    actual_set = {
        path.relative_to(attempt04).as_posix()
        for path in attempt04.rglob("*")
        if path.is_file()
    }
    if actual_set != EXPECTED_ATTEMPT04_RELATIVE_FILE_SET:
        raise RuntimeError(
            "Attempt 04 append-only evidence file set drifted: "
            f"{sorted(actual_set)}"
        )


def _attempt05_validate_config(config_path: Path, args: Any) -> tuple[dict[str, Any], dict[str, Path]]:
    if args.mode == "preflight":
        raise RuntimeError(
            "Attempt 05 reuses the passed hash-bound Attempt 04 preflight; a new preflight is forbidden"
        )
    _verify_authorities()
    config, original_paths = _ORIGINAL_VALIDATE_CONFIG(config_path, args)
    if sealed_worker.project_relative(original_paths["author_output"]) != SEALED_AUTHOR_OUTPUT_REL:
        raise RuntimeError("sealed worker did not validate the exact historical Attempt 04 output")
    target = (PROJECT_ROOT / ATTEMPT05_AUTHOR_OUTPUT_REL).resolve()
    try:
        target.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError("Attempt 05 output escapes the project root") from exc
    if args.mode == "author" and target.exists():
        raise RuntimeError(f"refusing to overwrite append-only Attempt 05 output: {target}")
    if args.mode == "verify-render" and not target.is_dir():
        raise RuntimeError("Attempt 05 author output does not exist for fresh-process verification")
    paths = dict(original_paths)
    paths["author_output"] = target
    return config, paths


def main() -> int:
    if _ORIGINAL_BUILD_POSITIONS is not repair._SEALED_BUILD_POSITIONS:
        raise RuntimeError("Attempt 05 did not capture the exact sealed build_positions callable")
    if sealed_worker.patch_contract.build_positions is not _ORIGINAL_BUILD_POSITIONS:
        raise RuntimeError("sealed build_positions was already changed before Attempt 05 bootstrap")
    sealed_worker.validate_config = _attempt05_validate_config
    sealed_worker.patch_contract.build_positions = repair.build_positions
    sealed_worker.WORKER_ID = WORKER_ID
    try:
        return sealed_worker.main()
    finally:
        sealed_worker.validate_config = _ORIGINAL_VALIDATE_CONFIG
        sealed_worker.patch_contract.build_positions = _ORIGINAL_BUILD_POSITIONS
        sealed_worker.WORKER_ID = _ORIGINAL_WORKER_ID


if __name__ == "__main__":
    raise SystemExit(main())

