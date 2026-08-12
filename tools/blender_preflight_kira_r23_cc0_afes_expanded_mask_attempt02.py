#!/usr/bin/env python3
"""Attempt 02 wrapper retaining metrics from the exact R23 preflight failure.

The exact sealed Attempt 01 worker and config perform all inspection, chart,
projection, mask, and gate logic unchanged.  This wrapper only traces their
exception frames so already-computed metrics survive in append-only evidence.
It does not author geometry, save a Blend, render, export, or create a
candidate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping

import bpy


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import blender_preflight_kira_r23_cc0_afes_expanded_mask as base  # noqa: E402
from tools.kira_r23_attempt02_failure_retention import (  # noqa: E402
    retain_preflight_failure_metrics,
)


DEFAULT_OVERLAY = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask_attempt02_preparation/"
    "KIRA_R23_ATTEMPT02_FAILURE_RETENTION_OVERLAY.json"
)
ALLOWED_OUTPUT = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_expanded_mask/preflight_attempt_02"
)


class Attempt02RetentionError(RuntimeError):
    pass


def arguments() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay", default=DEFAULT_OVERLAY.as_posix())
    return parser.parse_args(raw)


def project_path(raw: str | Path) -> Path:
    value = Path(str(raw))
    if value.is_absolute() or ".." in value.parts:
        raise Attempt02RetentionError(f"unsafe project-relative path: {raw}")
    resolved = (ROOT / value).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Attempt02RetentionError(f"path escaped project: {raw}") from exc
    return resolved


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_binding(name: str, binding: Mapping[str, Any]) -> dict[str, Any]:
    path = project_path(str(binding["path"]))
    if not path.is_file():
        raise Attempt02RetentionError(f"missing {name}: {relative(path)}")
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise Attempt02RetentionError(
            f"{name} binding mismatch: size={size}, sha256={digest}"
        )
    return {"path": relative(path), "bytes": size, "sha256": digest}


def run_exact_preflight_with_failure_capture(
    config: Mapping[str, Any], config_path: Path
) -> dict[str, Any]:
    """Run base.preflight unchanged and attach captured metrics on failure."""

    captured: dict[str, dict[str, Any]] = {
        "preflight": {},
        "expanded": {},
    }
    preflight_code = base.preflight.__code__
    expanded_code = base.expanded_mask_record.__code__

    def local_trace(frame, event, _arg):
        if event == "exception":
            if frame.f_code is preflight_code:
                captured["preflight"] = dict(frame.f_locals)
            elif frame.f_code is expanded_code:
                captured["expanded"] = dict(frame.f_locals)
        return local_trace

    def global_trace(frame, _event, _arg):
        if frame.f_code is preflight_code or frame.f_code is expanded_code:
            return local_trace
        return None

    previous_trace = sys.gettrace()
    sys.settrace(global_trace)
    try:
        return base.preflight(config, config_path)
    except Exception as exc:
        retained = retain_preflight_failure_metrics(
            captured["preflight"], captured["expanded"]
        )
        setattr(exc, "r23_attempt02_retained_metrics", retained)
        raise
    finally:
        sys.settrace(previous_trace)


def output_directory(overlay: Mapping[str, Any]) -> Path:
    directory = project_path(str(overlay["output"]["directory"]))
    if directory != project_path(ALLOWED_OUTPUT):
        raise Attempt02RetentionError("Attempt 02 output path is not exact")
    if directory.exists():
        raise FileExistsError(
            f"append-only Attempt 02 output already exists: {relative(directory)}"
        )
    return directory


def main() -> int:
    args = arguments()
    overlay_path = project_path(args.overlay)
    overlay = read_json(overlay_path)
    if overlay.get("schema") != (
        "kira.avatar.r23_cc0_afes_preflight_attempt02_"
        "failure_retention_overlay.v1"
    ):
        raise Attempt02RetentionError("wrong Attempt 02 overlay schema")
    if overlay.get("attempt_id") != "attempt_02":
        raise Attempt02RetentionError("wrong Attempt 02 identifier")

    verified_bindings = {
        name: verify_binding(name, overlay[name])
        for name in (
            "base_worker",
            "base_config",
            "source_blend",
            "qualified_cc0_foundation",
            "preserved_attempt_01",
        )
    }
    if Path(base.__file__).resolve() != project_path(overlay["base_worker"]["path"]):
        raise Attempt02RetentionError("imported base worker path is not exact")

    base_config_path = project_path(overlay["base_config"]["path"])
    config = read_json(base_config_path)
    if config.get("schema") != "kira.avatar.r23_cc0_afes_expanded_mask_preflight.v1":
        raise Attempt02RetentionError("wrong sealed base config schema")

    directory = output_directory(overlay)
    directory.mkdir(parents=True, exist_ok=False)
    try:
        report = run_exact_preflight_with_failure_capture(config, base_config_path)
        report["attempt_02_failure_retention"] = {
            "attempt_id": "attempt_02",
            "overlay": {
                "path": relative(overlay_path),
                "sha256": sha256_file(overlay_path),
            },
            "wrapper": {
                "path": relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
            },
            "verified_bindings": verified_bindings,
            "base_preflight_executed_unchanged": True,
            "selection_or_gate_logic_changed": False,
        }
        filename = str(overlay["output"]["pass_file"])
        result = 0
    except Exception as exc:
        retained = getattr(exc, "r23_attempt02_retained_metrics", {})
        expanded = retained.get("expanded_r19_mask_failure", {})
        retention = expanded.get("retention", {})
        expected_rings = [int(value) for value in overlay["required_complete_ring_attempts"]]
        complete = (
            retention.get("recorded_exterior_rings") == expected_rings
            and retention.get("complete_attempts_array") is True
        )
        source_path = project_path(overlay["source_blend"]["path"])
        body = bpy.data.objects.get(config["r19_contract"]["body_object"])
        body_state_after = (
            base.mesh_full_state_sha256(body)
            if body is not None and body.type == "MESH"
            else None
        )
        report = {
            "schema_version": 1,
            "artifact_kind": (
                "KIRA_R23_CC0_AFES_EXPANDED_MASK_READ_ONLY_PREFLIGHT_"
                "ATTEMPT02_FAILURE_WITH_RETAINED_METRICS"
            ),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PREFLIGHT_NO_GO_NO_CANDIDATE",
            "attempt_id": "attempt_02",
            "overlay": {
                "path": relative(overlay_path),
                "sha256": sha256_file(overlay_path),
            },
            "wrapper": {
                "path": relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
            },
            "base_config": verified_bindings["base_config"],
            "base_worker": verified_bindings["base_worker"],
            "preserved_attempt_01": verified_bindings["preserved_attempt_01"],
            "verified_attempt02_bindings": verified_bindings,
            "only_change": overlay["only_change"],
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "retained_pre_failure_metrics": retained,
            "retention_gate": {
                "expected_exterior_rings": expected_rings,
                "complete_attempts_array_present": complete,
                "recorded_attempt_count": retention.get("attempt_count"),
                "recorded_exterior_rings": retention.get(
                    "recorded_exterior_rings"
                ),
            },
            "integrity": {
                "source_blend_sha256_after": sha256_file(source_path),
                "source_blend_sha256_expected": overlay["source_blend"]["sha256"],
                "source_blend_exact": (
                    sha256_file(source_path) == overlay["source_blend"]["sha256"]
                ),
                "r19_body_state_after": body_state_after,
                "r19_body_state_matches_preflight_start": (
                    body_state_after
                    == retained.get("pre_failure_integrity", {}).get(
                        "r19_body_state_before"
                    )
                ),
            },
            "operations": {
                "mesh_mutation_performed": False,
                "candidate_created": False,
                "blend_written": False,
                "render_performed": False,
                "export_performed": False,
                "runtime_mutation_performed": False,
                "reference_only_asset_loaded": False,
            },
        }
        filename = str(overlay["output"]["failure_file"])
        result = 2

    evidence_path = directory / filename
    if evidence_path.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {relative(evidence_path)}")
    evidence_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "evidence": relative(evidence_path),
                "sha256": sha256_file(evidence_path),
                "retention_complete": report.get("retention_gate", {}).get(
                    "complete_attempts_array_present"
                ),
                "candidate_created": False,
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())

