#!/usr/bin/env python3
"""Run R19 radial-patch attempt 03 under the corrected bounded gate.

The inherited BlackProject base has 330 supported boundary edges in 23 loops.
Attempt 03 does not seal or relabel them.  It requires their exact loop-size
multiset to match the sealed R9b evidence while separately requiring zero new
patch/seam boundaries, exactly 34 seam merges, one connected component, and
zero patch-related exact penetrations.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import blender_build_kira_r19_blackproject_radial_patch_probe_attempt_02 as bounded_worker  # noqa: E402


OUTPUT_REL = Path(
    "RecoverySprint/continuation_20260802/"
    "r19_blackproject_radial_patch/attempt_03"
)
R9B_EVIDENCE_REL = Path(
    "Avatar/private_owner_review/kira_temporary_functional_body_20260730/"
    "kira_tfb_blackproject_r9b_20260730_072700/BUILD_EVIDENCE.json"
)
R9B_EVIDENCE_SHA256 = "79741bb5dfec080c523ae57c875fa95ca8ff91c77342406ffb11ce8506137d42"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def boundary_multiset(topology: dict[str, object]) -> list[int]:
    return sorted(
        int(record["vertex_count"])
        for record in topology.get("boundary_parts", [])
    )


def finalize_attempt_03() -> None:
    output_dir = PROJECT_ROOT / OUTPUT_REL
    evidence_path = output_dir / "BUILD_EVIDENCE.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    r9b_path = PROJECT_ROOT / R9B_EVIDENCE_REL
    if sha256_file(r9b_path) != R9B_EVIDENCE_SHA256:
        raise ValueError("sealed R9b topology baseline hash mismatch")
    r9b = json.loads(r9b_path.read_text(encoding="utf-8"))
    expected_multiset = boundary_multiset(r9b["topology_author_audit"])
    observed_multiset = boundary_multiset(evidence["primary_surface_topology"])
    join = evidence["primary_surface_join"]
    localized = evidence["intersection_localization"]
    gates = {
        "exactly_34_seam_merges": int(join["boundary_vertices_merged"]) == 34,
        "one_connected_primary_component": int(
            evidence["primary_surface_topology"]["connected_components"]
        )
        == 1,
        "zero_new_patch_or_seam_boundary_edges": int(
            join["post_weld_topology_hard_gate"]["new_patch_boundary_edge_count"]
        )
        == 0,
        "zero_patch_related_exact_intersections": int(
            localized["new_patch_related_genuine_pair_count"]
        )
        == 0,
        "inherited_boundary_edge_count_matches_r9b": int(
            evidence["primary_surface_topology"]["boundary_edge_count"]
        )
        == int(r9b["topology_author_audit"]["boundary_edge_count"])
        == 330,
        "inherited_boundary_loop_count_matches_r9b": len(observed_multiset)
        == len(expected_multiset)
        == 23,
        "inherited_boundary_loop_size_multiset_matches_r9b": observed_multiset
        == expected_multiset,
        "new_patch_prejoin_exact_intersections_zero": int(
            evidence["patch_exact_nonadjacent_intersection_audit"][
                "exact_genuine_penetration_pair_count"
            ]
        )
        == 0,
        "source_interior_geometry_reused_zero": (
            int(evidence["radial_patch_authoring"]["source_interior_vertices_reused"])
            == 0
            and int(evidence["radial_patch_authoring"]["source_interior_faces_reused"])
            == 0
        ),
    }
    if not all(gates.values()):
        failures = sorted(name for name, passed in gates.items() if not passed)
        raise ValueError(f"attempt-03 bounded gates failed: {failures}")

    attempt_02_path = Path(bounded_worker.__file__).resolve()
    base_path = Path(bounded_worker.attempt_01_worker.__file__).resolve()
    this_path = Path(__file__).resolve()
    evidence["attempt"] = "attempt_03"
    evidence["status"] = (
        "PRIVATE_INACTIVE_PATCH_STRUCTURAL_GATES_PASSED_"
        "INHERITED_FOUNDATION_BOUNDARIES_UNRESOLVED_REQUIRES_VISUAL_REVIEW"
    )
    evidence["attempt_03_corrected_bounded_gate"] = {
        **gates,
        "expected_inherited_boundary_edge_count": 330,
        "observed_inherited_boundary_edge_count": evidence[
            "primary_surface_topology"
        ]["boundary_edge_count"],
        "expected_inherited_boundary_loop_count": 23,
        "observed_inherited_boundary_loop_count": len(observed_multiset),
        "expected_inherited_boundary_loop_size_multiset": expected_multiset,
        "observed_inherited_boundary_loop_size_multiset": observed_multiset,
        "baseline": {
            "path": str(R9B_EVIDENCE_REL).replace("\\", "/"),
            "sha256": R9B_EVIDENCE_SHA256,
        },
        "unresolved_foundation_property": (
            "BlackProject retains 330 supported boundary edges in 23 loops "
            "outside the replaced adult aperture; this bounded task does not "
            "seal fingers, toes, or face openings"
        ),
    }
    evidence["worker"] = {
        "path": str(this_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "sha256": sha256_file(this_path),
        "dependencies": [
            {
                "path": str(attempt_02_path.relative_to(PROJECT_ROOT)).replace(
                    "\\", "/"
                ),
                "sha256": sha256_file(attempt_02_path),
            },
            {
                "path": str(base_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(base_path),
            },
        ],
    }
    evidence["gates"].update(gates)
    evidence["gates"]["closed_primary_surface"] = False
    evidence["gates"]["global_foundation_boundary_property_resolved"] = False
    evidence["gates"]["visual_review"] = "PENDING"
    evidence["gates"]["owner_approval"] = "PENDING"
    evidence["gates"]["runtime_eligibility"] = False
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    report_path = output_dir / "REPORT.md"
    report_path.write_text(
        "\n".join(
            [
                "# R19 BlackProject radial patch probe — attempt 03",
                "",
                f"Status: `{evidence['status']}`",
                "",
                "- Attempts 01 and 02 remain append-only evidence.",
                "- The exact 34-vertex seam is preserved and exactly 34 seam vertices merged.",
                "- The new patch reuses `0` rejected source-interior vertices and `0` faces.",
                "- Its center uses 17 distributed vertices, 32 quads, and two terminal triangles; there is no central poke/fan.",
                "- New patch exact intersections are zero both before and after joining.",
                "- The joined primary body is one connected component and the patch adds zero boundary edges.",
                "- The inherited BlackProject base still has 330 boundary edges in 23 loops outside this patch.",
                f"- Inherited loop-size multiset: `{observed_multiset}`; it exactly matches sealed R9b evidence.",
                "- Unrelated finger, toe, and face openings were not sealed.",
                "- Structural passage does not imply visual acceptance, owner approval, or runtime eligibility.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = output_dir / "PACKAGE_MANIFEST.json"
    entries = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and path != manifest_path:
            entries.append(
                {
                    "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "append_only_attempt": "attempt_03",
                "files_excluding_this_manifest": entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    output_dir = PROJECT_ROOT / OUTPUT_REL
    if output_dir.exists():
        raise FileExistsError("append-only attempt_03 already exists")
    bounded_worker.OUTPUT_REL = OUTPUT_REL
    result = bounded_worker.main()
    finalize_attempt_03()
    print(
        json.dumps(
            {
                "ok": True,
                "attempt": "attempt_03",
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
