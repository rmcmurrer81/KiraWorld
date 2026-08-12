"""Seal one append-only private Kira R18 package and external checkpoint.

This standard-library finalizer does not open Blender, alter the candidate,
activate or assign Kira, export a runtime model, or touch R17.  It verifies the
Blend/render/evidence hashes, writes one package manifest, and writes the build
checkpoint outside both the R17 and R18 candidate directories.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.prepare_kira_r18_bounded_bald_authoring import validate_sources


PRIVATE_PARENT = ROOT / "Avatar/private_owner_review"
PREFIX = "kira_profiled_adult_candidate_r18_bald_targeted_"
CHECKPOINT_PARENT = (
    ROOT / "RecoverySprint/continuation_20260802/kira_r18_bounded_bald_authoring"
)
OWNER_VISUAL_FINDINGS = (
    "The protected central external surface remains conspicuously layered/plate-like despite being structurally connected and zero-intersection at rest.",
    "The 55-degree and 80-degree knee states show strong dark/pinched shading and rounded collapse; the 80-degree audits also report posed self-intersection pairs.",
    "Hands, feet, and nail plates remain simplified and flat-looking.",
    "Seat contact is materially improved, but the feet remain unsupported/floating and the eating-ready arms/hands remain rigid or overlapping.",
    "The lying-contact images are static pose foundations, not accepted natural motion.",
    "A horizontal band remains visible across the rear scalp.",
    "The face and eyes remain generic/mannequin-like rather than a demonstrated Kira identity match.",
    "Brows are improved from R17 but remain sparse and stroke-like.",
    "The protected side render does not provide a useful diagnostic view of the central external surface.",
)


class KiraR18PackageFinalizeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--checkpoint-dir", required=True)
    return parser.parse_args()


def _safe_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    candidate = (ROOT / Path(args.candidate_dir)).resolve(strict=True)
    checkpoint = (ROOT / Path(args.checkpoint_dir)).resolve()
    if candidate.parent != PRIVATE_PARENT.resolve() or not candidate.name.startswith(PREFIX):
        raise KiraR18PackageFinalizeError("candidate is not an R18 private-review child")
    if checkpoint.parent != CHECKPOINT_PARENT.resolve():
        raise KiraR18PackageFinalizeError("checkpoint must be a direct child of the R18 evidence root")
    if checkpoint.exists():
        raise KiraR18PackageFinalizeError("append-only checkpoint already exists")
    if (candidate / "PACKAGE_MANIFEST.json").exists():
        raise KiraR18PackageFinalizeError("append-only package manifest already exists")
    return candidate, checkpoint


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    candidate, checkpoint = _safe_paths(args)
    source_validation = validate_sources(ROOT)
    evidence_path = candidate / "BUILD_EVIDENCE.json"
    if not evidence_path.is_file():
        raise KiraR18PackageFinalizeError("BUILD_EVIDENCE.json missing")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    if evidence.get("candidate_id") != candidate.name:
        raise KiraR18PackageFinalizeError("candidate/evidence identity mismatch")
    if evidence.get("status") != "INACTIVE_PRIVATE_COMPLETE_BODY_AWAITING_OWNER_VISUAL_DECISION":
        raise KiraR18PackageFinalizeError("candidate is not a complete inactive delivery")
    safety = evidence.get("safety") or {}
    required_safety = {
        "inactive": True,
        "private_owner_review_only": True,
        "assigned": False,
        "activated": False,
        "clothing_created": False,
        "scalp_hair_created_or_loaded": False,
        "published": False,
        "uploaded": False,
        "runtime_exported": False,
        "live_kira_state_unchanged": True,
    }
    failures = [
        key for key, expected in required_safety.items() if safety.get(key) is not expected
    ]
    if failures:
        raise KiraR18PackageFinalizeError("safety evidence failed: " + ", ".join(failures))

    blend_record = (evidence.get("outputs") or {}).get("blend") or {}
    blend_path = candidate / str(blend_record.get("path") or "")
    if not blend_path.is_file() or sha256(blend_path) != blend_record.get("sha256"):
        raise KiraR18PackageFinalizeError("candidate Blend hash mismatch")
    if ((evidence.get("outputs") or {}).get("private_glb") or {}).get("exported") is not False:
        raise KiraR18PackageFinalizeError("runtime/private GLB export is not permitted")

    render_rows = evidence.get("render_inventory") or []
    if len(render_rows) < 30:
        raise KiraR18PackageFinalizeError(f"full review render inventory is incomplete: {len(render_rows)}")
    labels: set[str] = set()
    for record in render_rows:
        label = str(record.get("label") or "")
        path = candidate / str(record.get("path") or "")
        if not label or label in labels:
            raise KiraR18PackageFinalizeError(f"duplicate or missing render label: {label!r}")
        labels.add(label)
        if not path.is_file() or sha256(path) != record.get("sha256"):
            raise KiraR18PackageFinalizeError(f"render hash mismatch: {label}")
    required_labels = {
        "front",
        "rear",
        "left_profile",
        "right_profile",
        "left_three_quarter",
        "right_three_quarter",
        "face_close",
        "eyes_close",
        "left_hand_nails_close",
        "right_hand_nails_close",
        "left_foot_nails_close",
        "right_foot_nails_close",
        "protected_adult_relationship_front",
        "protected_adult_relationship_side",
        "protected_adult_relationship_three_quarter",
        "neutral_standing",
        "crown_top_scalp",
        "rear_scalp_hairline",
        "left_knee_flexion",
        "right_knee_flexion",
        "bilateral_knee_flexion",
        "seated_front_three_quarter",
        "seated_side_contact",
        "brows_close",
        "diagnostic_medical_external_view",
        "left_knee_bend_80deg",
        "right_knee_bend_80deg",
        "bilateral_knee_bend_80deg",
        "toilet_seated_diagnostic_contact",
    }
    missing = required_labels.difference(labels)
    if missing:
        raise KiraR18PackageFinalizeError("required review labels missing: " + ", ".join(sorted(missing)))

    pose_audits = (
        ((evidence.get("movement_and_contact") or {}).get("pose_intersection_audits"))
        or {}
    )
    posed_intersection_counts = {
        name: int(record.get("nonadjacent_intersection_pair_count") or 0)
        for name, record in sorted(pose_audits.items())
        if isinstance(record, dict)
        and "nonadjacent_intersection_pair_count" in record
    }

    files = sorted(
        (path for path in candidate.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(candidate).as_posix().casefold(),
    )
    file_records = [_file_record(path, candidate) for path in files]
    manifest = {
        "schema_version": 1,
        "artifact_type": "kira_r18_private_owner_review_package_manifest",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "candidate_id": candidate.name,
        "status": "SEALED_PRIVATE_INACTIVE_AWAITING_OWNER_VISUAL_DECISION_WITH_DISCLOSED_DEFECTS",
        "file_count_excluding_manifest": len(file_records),
        "files": file_records,
        "build_evidence_sha256": sha256(evidence_path),
        "blend_sha256": sha256(blend_path),
        "review_label_count": len(labels),
        "owner_visual_approval_claimed": False,
        "owner_visual_findings": list(OWNER_VISUAL_FINDINGS),
        "posed_nonadjacent_intersection_pair_counts": posed_intersection_counts,
        "source_r17_validation": source_validation,
        "safety": required_safety,
        "rollback": (
            "Quarantine or remove only this R18 directory if rejected. The exact R17 "
            "package and live Kira runtime/selection remain unchanged."
        ),
    }
    manifest_path = candidate / "PACKAGE_MANIFEST.json"
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")

    checkpoint.mkdir(parents=False, exist_ok=False)
    audit = {
        "schema_version": 1,
        "artifact_type": "kira_r18_private_package_finalization_audit",
        "candidate_dir": candidate.relative_to(ROOT).as_posix(),
        "candidate_manifest": {
            "path": manifest_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(manifest_path),
        },
        "build_evidence_sha256": sha256(evidence_path),
        "blend_sha256": sha256(blend_path),
        "source_r17_validation": source_validation,
        "private_inactive_unassigned": True,
        "runtime_exported": False,
        "owner_visual_approval_claimed": False,
        "owner_visual_findings": list(OWNER_VISUAL_FINDINGS),
        "posed_nonadjacent_intersection_pair_counts": posed_intersection_counts,
    }
    audit_path = checkpoint / "PACKAGE_AUDIT.json"
    with audit_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(audit, stream, indent=2, sort_keys=True)
        stream.write("\n")
    checkpoint_path = checkpoint / "CHECKPOINT.md"
    findings_text = "\n".join(f"- {finding}" for finding in OWNER_VISUAL_FINDINGS)
    pose_counts_text = "\n".join(
        f"- `{name}`: {count} nonadjacent intersection pairs"
        for name, count in posed_intersection_counts.items()
    )
    checkpoint_text = f"""# Kira R18 private bald-body checkpoint

Status: **PRIVATE, INACTIVE, UNASSIGNED, AWAITING ROBERT VISUAL REVIEW**

- Candidate: `{candidate.relative_to(ROOT).as_posix()}`
- Candidate Blend SHA-256: `{sha256(blend_path)}`
- BUILD_EVIDENCE.json SHA-256: `{sha256(evidence_path)}`
- PACKAGE_MANIFEST.json SHA-256: `{sha256(manifest_path)}`
- PACKAGE_AUDIT.json SHA-256: `{sha256(audit_path)}`
- Frozen R17 package inventory SHA-256: `{source_validation['r17_package_inventory_sha256']}`

## Owner-review findings retained

{findings_text}

## Measured posed-intersection evidence

{pose_counts_text}

No activation, assignment, clothing, scalp-hair loading, runtime export,
publication, upload, internal-organ claim, bathroom-function claim, pregnancy
claim, Robert build, or owner visual approval occurred.

Rollback: quarantine or remove only the new R18 candidate directory and this
external checkpoint directory. The exact R17 package and live Kira state were
not changed.
"""
    with checkpoint_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(checkpoint_text)
    return {
        "candidate": candidate.relative_to(ROOT).as_posix(),
        "package_manifest": manifest_path.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(manifest_path),
        "package_audit": audit_path.relative_to(ROOT).as_posix(),
        "package_audit_sha256": sha256(audit_path),
        "checkpoint": checkpoint_path.relative_to(ROOT).as_posix(),
        "checkpoint_sha256": sha256(checkpoint_path),
    }


def main() -> int:
    result = finalize(_args())
    print("KIRA_R18_PACKAGE_FINALIZED=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
