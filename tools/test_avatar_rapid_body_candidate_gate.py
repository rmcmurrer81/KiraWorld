#!/usr/bin/env python3
"""Focused tests for inactive rapid-body workspace and roster safety."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_rapid_body_candidate import (  # noqa: E402
    REQUIRED_RENDER_LABELS,
    REQUIRED_DEFORMATION_POSE_LABELS,
    REQUIRED_VISUAL_REVIEW_CHECKS,
    VISUAL_CHECK_RELEVANT_RENDER_LABELS,
    VISUAL_CHECK_REQUIRED_RENDER_LABELS,
    build_workspace_record,
    evaluate_candidate_package,
    private_roster_entry,
    roster_with_entry,
)
from Core.avatar_rapid_body_request import (  # noqa: E402
    RapidBodyRequestError,
    validate_rapid_body_request,
)


REPORT_DIR = (
    PROJECT_ROOT
    / "Avatar/avatar_builder/proofs/"
    "rapid_body_candidate_gate_20260730"
)
REPORT_PATH = REPORT_DIR / "TEST_REPORT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_minimal_rigged_glb(path: Path, marker: str) -> None:
    joint_names = [
        "Hips",
        "Spine",
        "Neck",
        "Head",
        "LeftArm",
        "LeftForeArm",
        "LeftHand",
        "RightArm",
        "RightForeArm",
        "RightHand",
        "LeftUpLeg",
        "LeftLeg",
        "LeftFoot",
        "RightUpLeg",
        "RightLeg",
        "RightFoot",
    ]
    nodes = [{"name": "Body", "mesh": 0, "skin": 0}]
    nodes.extend({"name": name} for name in joint_names)
    document = {
        "asset": {"version": "2.0", "generator": f"test:{marker}"},
        "accessors": [
            {"componentType": 5126, "count": 3, "type": "VEC3"},
            {"componentType": 5123, "count": 3, "type": "VEC4"},
            {"componentType": 5126, "count": 3, "type": "VEC4"},
            {"componentType": 5123, "count": 3, "type": "SCALAR"},
        ],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": 0,
                            "JOINTS_0": 1,
                            "WEIGHTS_0": 2,
                        },
                        "indices": 3,
                        "mode": 4,
                    }
                ]
            }
        ],
        "nodes": nodes,
        "skins": [{"joints": list(range(1, len(nodes)))}],
        "animations": [{"name": "bounded_pose_evidence"}],
        "materials": [{"name": marker}],
    }
    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    declared = 12 + 8 + len(encoded)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, declared)
        + struct.pack("<II", len(encoded), 0x4E4F534A)
        + encoded
    )


def make_fixture(root: Path) -> dict[str, Path | dict]:
    source = (
        root
        / "Avatar/avatar_builder/asset_library/base_body_reference/"
        "generic_adult_female_cage.glb"
    )
    candidate_root = (
        root
        / "Avatar/private_owner_review/"
        "kira_temporary_functional_body_20260730/run_a"
    )
    candidate = candidate_root / "kira_temporary.glb"
    write_minimal_rigged_glb(source, "source")
    write_minimal_rigged_glb(candidate, "candidate")

    authority = (
        root
        / "Avatar/avatar_builder/multiview_authoring/base_catalog/"
        "authority.json"
    )
    write_json(
        authority,
        {
            "schema_version": 1,
            "entries": [
                {
                    "base_id": "generic_adult_female_cage",
                    "path": source.relative_to(root).as_posix(),
                    "sha256": sha256(source),
                    "topology_lane": "confirmed_adult_topology",
                    "allowed_use": "cage_fit_source_new_surface_required",
                    "copy_as_candidate_body_allowed": False,
                    "maturity_authority": {
                        "adult_only": True,
                        "allowed_for_non_adult": False,
                    },
                    "structural_audit": {"valid_glb": True},
                    "stable_working_rig_proven": False,
                    "anatomical_completeness_proven": False,
                    "known_boundary_loops": 3,
                }
            ],
        },
    )

    runtime_root = root / "Data/runtime"
    live_body = root / "Avatar/models/temp_ai/kira/avatar.glb"
    selection = root / "Avatar/state/body_selections/kira.json"
    shell = runtime_root / "kira_world_shell_state.json"
    for path, content in (
        (live_body, b"unchanged live body"),
        (selection, b'{"selection":"unchanged"}\n'),
        (shell, b'{"world":"unchanged"}\n'),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    request = (
        root
        / "Avatar/avatar_builder/rapid_body_pipeline/requests/"
        "kira_temporary.json"
    )
    request_payload = {
        "schema_version": 1,
        "display_owner": {
            "stable_id": "kira",
            "display_name": "Kira Hart",
        },
        "body_purpose": "TEMPORARY_FUNCTIONAL_BODY",
        "adult_status": "adult",
        "body_class": "adult_female",
        "parameters": {
            "height_m": 1.651,
            "build_preset": "natural_athletic",
            "muscularity": 0.18,
            "body_mass": 0.0,
            "shoulder_width": 0.0,
            "chest_torso": 0.0,
            "waist_abdomen": -0.04,
            "hips_pelvis": 0.02,
            "arms": 0.0,
            "legs": 0.02,
            "hands": 0.0,
            "feet": 0.0,
            "neck": 0.0,
            "face_landmarks": "bounded_generic_adult_female",
            "skin_direction": "light_natural_regional_variation",
            "iris_color": "natural_brown",
            "hair": {
                "color": "black",
                "texture": "straight",
                "review_style": "simple_removable_shoulders_clear",
            },
        },
        "foundation_requirements": {
            "selection": "AUTO_SELECT_ENROLLED_CLEAN_ADULT_FEMALE",
            "selected_source_path": "",
            "continuous_topology": True,
            "integrated_adult_anatomy": True,
            "movement_ready_rig": True,
            "deformation_regions": True,
            "future_clothing_compatible": True,
            "future_hair_compatible": True,
        },
        "reference_inputs": [
            {
                "subject_id": "generic_non_identifiable",
                "type": "owner_text_specification",
            }
        ],
        "privacy": {
            "robert_private_data_allowed": False,
            "identifiable_person_likeness_allowed": False,
            "copy_existing_person_body_allowed": False,
            "private_local_review_only": True,
        },
        "output": {
            "private_candidate_root": (
                "Avatar/private_owner_review/"
                "kira_temporary_functional_body_20260730"
            ),
            "candidate_state": "PRIVATE_INSPECTION_CANDIDATE",
            "runtime_assignment_allowed": False,
            "owner_approved": False,
            "kira_permanent_selection_claimed": False,
        },
        "runtime_nonmutation_baseline": {
            "live_body": {
                "path": live_body.relative_to(root).as_posix(),
                "bytes": live_body.stat().st_size,
                "sha256": sha256(live_body),
            },
            "body_selection": {
                "path": selection.relative_to(root).as_posix(),
                "bytes": selection.stat().st_size,
                "sha256": sha256(selection),
            },
            "world_shell_state": {
                "path": shell.relative_to(root).as_posix(),
                "bytes": shell.stat().st_size,
                "sha256": sha256(shell),
            },
        },
    }
    write_json(request, request_payload)

    render_records: dict[str, dict] = {}
    for label in REQUIRED_RENDER_LABELS:
        render = candidate_root / "renders" / f"{label}.png"
        render.parent.mkdir(parents=True, exist_ok=True)
        render.write_bytes(b"\x89PNG\r\n\x1a\n" + label.encode("ascii"))
        render_records[label] = {
            "path": render.relative_to(root).as_posix(),
            "sha256": sha256(render),
            "size_bytes": render.stat().st_size,
        }

    evidence = candidate_root / "blender_build_evidence.json"
    evidence_payload = {
        "schema_version": 1,
        "candidate_id": "kira_temporary_functional_body_20260730",
        "status": "PRIVATE_INSPECTION_CANDIDATE_AWAITING_OWNER_REVIEW",
        "request": {
            "path": request.relative_to(root).as_posix(),
            "sha256": sha256(request),
            "parameters": request_payload["parameters"],
        },
        "source": {
            "path": source.relative_to(root).as_posix(),
            "sha256": sha256(source),
        },
        "surface_authoring": {
            "body_topology_after": {
                "surface_island_count": 1,
                "non_manifold_edge_count": 0,
                "degenerate_face_count": 0,
                "boundary_loop_count": 3,
            },
            "request_parametric_key": {
                "moved_vertex_count": 120,
                "maximum_world_displacement_m": 0.012,
                "integrated_external_adult_form": {
                    "authored_on_primary_body_surface": True,
                    "separate_or_floating_anatomy_mesh_created": False,
                    "all_named_regions_received_surface_displacement": True,
                    "visual_owner_review_required": True,
                    "functional_soft_tissue_behavior_proven": False,
                    "body_class": "adult_female",
                    "wrong_body_class_helper_or_surface_excluded": True,
                    "requested_body_class_visually_reviewed": True,
                },
            },
        },
        "renders": render_records,
        "artifacts": {
            "candidate_glb": {
                "path": candidate.relative_to(root).as_posix(),
                "sha256": sha256(candidate),
                "size_bytes": candidate.stat().st_size,
            }
        },
        "gates": {
            **{name: True for name in (
                "new_transformed_surface_not_unmodified_copy",
                "one_connected_primary_body_surface",
                "zero_primary_body_nonmanifold_edges",
                "known_boundary_cycles_reported",
                "integrated_external_adult_form_engineering_gate",
                "adult_surface_matches_requested_body_class",
                "movement_ready_structural_and_bounded_pose_gate",
                "brown_review_eyes_present",
                "straight_black_removable_review_hair_present",
                "ordinary_finger_and_toe_nail_review_components_present",
                "future_clothing_structural_compatibility",
                "future_hair_structural_compatibility",
            )},
            "owner_approved": False,
            "runtime_assignment_allowed": False,
            "public_export_allowed": False,
        },
        "privacy": {
            "private_local_review_only": True,
            "robert_private_data_allowed": False,
            "robert_private_data_read_or_used_by_worker": False,
            "identifiable_person_likeness_used": False,
            "copy_existing_person_body_used": False,
            "runtime_files_read_or_written_by_worker": False,
        },
    }
    write_json(evidence, evidence_payload)
    topology_audit = candidate_root / "independent_topology_audit.json"
    topology_payload = {
        "schema_version": 1,
        "audit_mode": "independent_blender_rapid_body_topology_v1",
        "producer": "tools/blender_audit_rapid_body_candidate.py",
        "candidate_sha256": sha256(candidate),
        "input_modified": False,
        "primary_marker_count": 1,
        "primary_body": {
            "present": True,
            "surface_island_count": 1,
            "boundary_loop_count": 3,
            "reviewed_intentional_boundary_loop_count": 3,
            "boundary_component_support": {
                "method": (
                    "exact_import_boundary_vertices_to_supported_component_"
                    "vertex_kdtree"
                ),
                "boundary_loop_count": 3,
                "supported_boundary_loop_count": 3,
                "unsupported_boundary_loop_count": 0,
                "coverage_complete": True,
            },
            "open_boundary_chain_count": 0,
            "non_manifold_edge_count": 0,
            "degenerate_face_count": 0,
            "unweighted_vertex_count": 0,
            "weight_sum_out_of_tolerance_count": 0,
        },
        "self_intersection": {
            "complete_bvh_overlap_scan": True,
            "adjacency_method": (
                "raw_index_or_positional_weld_key_shared_vertex"
            ),
            "positional_weld_tolerance_m": 0.000001,
            "coincident_duplicate_triangle_pair_count": 0,
            "nonadjacent_intersecting_source_face_pair_count": 0,
        },
        "topology_intersection_gate_passed": True,
        "owner_approved": False,
        "runtime_assignment_allowed": False,
    }
    write_json(topology_audit, topology_payload)
    deformation_audit = (
        candidate_root / "independent_deformation_audit.json"
    )
    deformation_payload = {
        "schema_version": 1,
        "audit_mode": "independent_blender_rapid_body_deformation_v1",
        "producer": "tools/blender_audit_rapid_body_candidate.py",
        "candidate_sha256": sha256(candidate),
        "input_modified": False,
        "skeleton_profile": {
            "joint_count": 16,
            "runtime_compatibility_claimed": False,
            "future_adapter_or_eligibility_proof_required": True,
        },
        "missing_pose_labels": [],
        "failed_pose_labels": [],
        "required_pose_labels": list(REQUIRED_DEFORMATION_POSE_LABELS),
        "pose_records": {
            label: {
                "bounded_structural_deformation_passed": True,
                **(
                    {
                        "anatomical_knee_direction_passed": True,
                        "anatomical_knee_direction": {
                            "passed": True,
                            "side": (
                                "right"
                                if label == "knee_flexion_right"
                                else "left"
                            ),
                            "anatomical_forward_axis": "-Y",
                            "upper_leg_bone": (
                                "upperleg02.R"
                                if label == "knee_flexion_right"
                                else "upperleg02.L"
                            ),
                            "lower_leg_bone": (
                                "lowerleg01.R"
                                if label == "knee_flexion_right"
                                else "lowerleg01.L"
                            ),
                            "ankle_bone": (
                                "lowerleg02.R"
                                if label == "knee_flexion_right"
                                else "lowerleg02.L"
                            ),
                            "measured_from_exact_imported_skeleton": True,
                            "posterior_ankle_displacement_m": 0.22,
                            "flexion_degrees": 68.0,
                        },
                    }
                    if label
                    in {"knee_flexion", "knee_flexion_right"}
                    else {}
                ),
            }
            for label in REQUIRED_DEFORMATION_POSE_LABELS
        },
        "restoration": {
            "restored_within_1e_6_m": True,
        },
        "bounded_pose_deformation_gate_passed": True,
        "owner_approved": False,
        "runtime_assignment_allowed": False,
    }
    write_json(deformation_audit, deformation_payload)
    visual_review = {
        "schema_version": 1,
        "status": "PASSED_FOR_PRIVATE_INSPECTION",
        "candidate_sha256": sha256(candidate),
        "reviewed_at": "2026-07-30T04:00:00Z",
        "reviewed_by": "independent_visual_inspector",
        "owner_approval_claimed": False,
        "check_results": {
            name: {
                "passed": True,
                "evidence_render_labels": [
                    *sorted(
                        VISUAL_CHECK_REQUIRED_RENDER_LABELS.get(name, set())
                    ),
                    *(
                        []
                        if VISUAL_CHECK_REQUIRED_RENDER_LABELS.get(name)
                        else [
                            sorted(
                                VISUAL_CHECK_RELEVANT_RENDER_LABELS[name]
                            )[0]
                        ]
                    ),
                ],
            }
            for name in REQUIRED_VISUAL_REVIEW_CHECKS
        },
    }
    return {
        "source": source,
        "candidate": candidate,
        "request": request,
        "request_payload": request_payload,
        "evidence": evidence,
        "evidence_payload": evidence_payload,
        "topology_audit": topology_audit,
        "topology_payload": topology_payload,
        "deformation_audit": deformation_audit,
        "deformation_payload": deformation_payload,
        "visual_review": visual_review,
        "selection": selection,
    }


def convert_fixture_to_licensed_derivative(
    root: Path,
    fixture: dict[str, Path | dict],
) -> Path:
    """Write the second supported build-evidence family over the same artifact."""

    source = fixture["source"]
    request = fixture["request"]
    candidate = fixture["candidate"]
    evidence = fixture["evidence"]
    request_payload = fixture["request_payload"]
    old_evidence = fixture["evidence_payload"]
    assert isinstance(source, Path)
    assert isinstance(request, Path)
    assert isinstance(candidate, Path)
    assert isinstance(evidence, Path)
    assert isinstance(request_payload, dict)
    assert isinstance(old_evidence, dict)

    authority = source.with_suffix(".authority.json")
    write_json(
        authority,
        {
            "schema_version": 1,
            "authority_id": "test_cc_by_derivative_source",
            "local_asset": {
                "path": source.relative_to(root).as_posix(),
                "bytes": source.stat().st_size,
                "sha256": sha256(source),
                "copy_policy": (
                    "exact_byte_copy_of_reviewed_source; "
                    "do_not_replace_in_place"
                ),
            },
            "source": {
                "title": "Adult Female Test Foundation",
                "author": "Test Author",
                "source_url": "https://example.invalid/foundation",
                "license": "CC BY 4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "attribution_required_on_derivatives": True,
            },
            "reviewed_structure": {
                "mesh_count": 1,
                "joint_count": 16,
                "adult_external_anatomy_component_present": True,
            },
            "allowed_use": {
                "lane": "adult_female_avatar_derivative",
                "may_export_private_derivative_candidate": True,
                "may_activate_or_replace_runtime_without_separate_approval": (
                    False
                ),
            },
            "forbidden_use": {
                "minor_or_age_ambiguous_lane": True,
                "robert_private_reference_input": True,
                "claim_source_is_kira_likeness": True,
                "claim_complete_topology_from_filename_or_metadata_alone": True,
                "runtime_assignment_without_owner_approval": True,
                "public_distribution_without_required_attribution_and_review": (
                    True
                ),
            },
        },
    )
    topology = old_evidence["surface_authoring"]["body_topology_after"]
    render_bindings = old_evidence["renders"]
    derivative = {
        "schema_version": 1,
        "candidate_id": "kira_temporary_functional_body_20260730",
        "status": (
            "PRIVATE_INSPECTION_CANDIDATE_AWAITING_INDEPENDENT_AUDIT_"
            "AND_OWNER_REVIEW"
        ),
        "sources": {
            "staged_foundation": {
                "path": source.relative_to(root).as_posix(),
                "sha256": sha256(source),
                "size_bytes": source.stat().st_size,
            },
            "authority": {
                "path": authority.relative_to(root).as_posix(),
                "sha256": sha256(authority),
                "size_bytes": authority.stat().st_size,
            },
            "request": {
                "path": request.relative_to(root).as_posix(),
                "sha256": sha256(request),
                "size_bytes": request.stat().st_size,
            },
        },
        "privacy": {
            "private_local_review_only": True,
            "robert_private_photos_used": False,
            "robert_measurements_used": False,
            "robert_morphs_or_surface_used": False,
            "identifiable_person_likeness_used": False,
            "runtime_files_read_or_written_by_worker": False,
        },
        "request_parameters": request_payload["parameters"],
        "parameter_morph": {
            "changed_vertices": 120,
            "maximum_vertex_delta_m": 0.012,
        },
        "topology_author_audit": {
            "connected_components": topology["surface_island_count"],
            "boundary_closed_cycle_count": topology["boundary_loop_count"],
            "boundary_parts": [
                {"closed_cycle": True}
                for _ in range(topology["boundary_loop_count"])
            ],
            "overused_edge_count": topology["non_manifold_edge_count"],
            "degenerate_face_count_under_1e_12_m2": topology[
                "degenerate_face_count"
            ],
        },
        "adult_surface_authoring": {
            "authored_on_primary_body_surface": True,
            "separate_or_floating_adult_surface_present": False,
            "adult_surface_interface_weld_or_bridge_evidence": True,
            "owner_visual_review_required": True,
            "dynamic_soft_tissue_behavior_proven": False,
            "adult_surface_body_class": "adult_female",
            "wrong_body_class_helper_or_surface_excluded": True,
            "requested_body_class_visually_reviewed": True,
        },
        "render_bindings": render_bindings,
        "candidate": {
            "path": candidate.relative_to(root).as_posix(),
            "sha256": sha256(candidate),
            "size_bytes": candidate.stat().st_size,
            "owner_approved": False,
            "runtime_assignment_allowed": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        },
        "gates": {
            "author_topology_gate": True,
            "author_weight_gate": True,
            "author_bounded_deformation_gate": True,
            "author_combined_gate": True,
        },
    }
    write_json(evidence, derivative)
    fixture["evidence_payload"] = derivative
    return authority


def run() -> dict:
    rows: list[dict[str, object]] = []

    def record(name: str, passed: bool, detail: object) -> None:
        rows.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            raise AssertionError(f"{name}: {detail}")

    with tempfile.TemporaryDirectory(prefix="kira_rapid_body_gate_") as tmp:
        root = Path(tmp)
        fixture = make_fixture(root)
        request = fixture["request"]
        evidence = fixture["evidence"]
        visual = fixture["visual_review"]
        topology_audit = fixture["topology_audit"]
        topology_payload = fixture["topology_payload"]
        deformation_audit = fixture["deformation_audit"]
        deformation_payload = fixture["deformation_payload"]
        assert isinstance(request, Path)
        assert isinstance(evidence, Path)
        assert isinstance(visual, dict)
        assert isinstance(topology_audit, Path)
        assert isinstance(topology_payload, dict)
        assert isinstance(deformation_audit, Path)
        assert isinstance(deformation_payload, dict)

        workspace = build_workspace_record(root, request)
        record(
            "workspace_exposes_all_bounded_owner_controls",
            set(workspace["owner_controls"]) == {
                "height",
                "build",
                "torso_waist_hips",
                "arms_legs",
                "hands_feet",
                "neck",
                "face",
                "skin",
                "eyes",
                "hair",
                "anatomy",
            },
            workspace["owner_controls"],
        )
        record(
            "workspace_runtime_truth_is_no_body_and_unassigned",
            workspace["runtime_assignment"]["allowed"] is False
            and workspace["runtime_assignment"]["performed"] is False
            and workspace["runtime_assignment"]["runtime_profile_truth"]
            == "NO_BODY_UNCHANGED",
            workspace["runtime_assignment"],
        )
        record(
            "private_candidate_accepts_proven_non79_skeleton_profile",
            workspace["skeleton_policy"][
                "fixed_runtime_joint_count_required_at_this_phase"
            ]
            is False
            and workspace["skeleton_policy"][
                "future_runtime_adapter_or_eligibility_proof_required"
            ]
            is True,
            workspace["skeleton_policy"],
        )

        valid = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "valid_exact_private_candidate_is_admitted",
            valid["private_inspection_roster_admission_allowed"] is True
            and valid["runtime_assignment_allowed"] is False,
            valid["failures"],
        )
        record(
            "source_is_not_promoted_as_complete_body",
            valid["source_authority"][
                "source_anatomical_completeness_proven"
            ]
            is False
            and valid["source_authority"][
                "source_stable_working_rig_proven"
            ]
            is False
            and valid["source_authority"]["copy_as_candidate_body_allowed"]
            is False,
            valid["source_authority"],
        )
        record(
            "candidate_skeleton_is_recorded_without_runtime_claim",
            valid["skeleton_profile"]["joint_count"] == 16
            and valid["skeleton_profile"][
                "current_runtime_compatibility_claimed"
            ]
            is False,
            valid["skeleton_profile"],
        )

        wrong_body_class_payload = deepcopy(fixture["evidence_payload"])
        assert isinstance(wrong_body_class_payload, dict)
        wrong_body_class_payload["surface_authoring"][
            "request_parametric_key"
        ]["integrated_external_adult_form"]["body_class"] = "adult_male"
        wrong_body_class = evidence.parent / "wrong_body_class.json"
        write_json(wrong_body_class, wrong_body_class_payload)
        wrong_body_class_result = evaluate_candidate_package(
            root,
            request,
            wrong_body_class,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "wrong_body_class_helper_or_surface_blocks_candidate",
            "adult_surface_requested_body_class_mismatch"
            in wrong_body_class_result["failures"],
            wrong_body_class_result["failures"],
        )

        audit_path = (
            root
            / "Avatar/private_owner_review/"
            "kira_temporary_functional_body_20260730/run_a/"
            "candidate_audit.json"
        )
        write_json(audit_path, valid)
        entry = private_roster_entry(root, audit_path)
        record(
            "private_roster_entry_is_visible_but_never_selectable",
            entry["private_inspection_visible"] is True
            and entry["runtime_selectable"] is False
            and entry["runtime_assignment_allowed"] is False
            and entry["owner_approved"] is False,
            entry,
        )
        roster = {
            "schema_version": 1,
            "entries": [],
            "runtime_bridge": {
                "implemented": False,
                "assignment_allowed": False,
            },
        }
        updated = roster_with_entry(roster, entry)
        record(
            "roster_append_preserves_unselectable_state",
            len(updated["entries"]) == 1
            and updated["entries"][0]["runtime_selectable"] is False,
            updated["entries"],
        )

        pending = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
        )
        record(
            "missing_independent_visual_review_blocks_admission",
            pending["private_inspection_roster_admission_allowed"] is False
            and "independent_visual_review_pending" in pending["failures"],
            pending["failures"],
        )

        rejected_visual = deepcopy(visual)
        rejected_visual["status"] = "REJECTED_PRIVATE_ENGINEERING_EVIDENCE"
        rejected = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=rejected_visual,
        )
        record(
            "independent_visual_rejection_overrides_numerical_passes",
            rejected["private_inspection_roster_admission_allowed"] is False
            and "independent_visual_review_not_passed"
            in rejected["failures"],
            rejected["failures"],
        )

        false_visual_pass = deepcopy(visual)
        false_visual_pass["check_results"][
            "knees_no_reverse_or_hyperextension"
        ]["passed"] = False
        false_visual_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=false_visual_pass,
        )
        record(
            "visual_pass_label_cannot_override_failed_required_check",
            (
                "independent_visual_check_not_passed:"
                "knees_no_reverse_or_hyperextension"
            )
            in false_visual_result["failures"],
            false_visual_result["failures"],
        )

        unbound_visual = deepcopy(visual)
        unbound_visual["check_results"][
            "eyes_no_hard_bands_or_uv_material_artifacts"
        ]["evidence_render_labels"] = ["unbound_eye_preview"]
        unbound_visual_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=unbound_visual,
        )
        record(
            "visual_check_requires_exact_bound_render_evidence",
            (
                "independent_visual_check_evidence_unbound:"
                "eyes_no_hard_bands_or_uv_material_artifacts"
            )
            in unbound_visual_result["failures"],
            unbound_visual_result["failures"],
        )

        irrelevant_visual = deepcopy(visual)
        irrelevant_visual["check_results"][
            "scalp_no_nonhair_black_patch_or_cap_artifact"
        ]["evidence_render_labels"] = ["neutral_front"]
        irrelevant_visual_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=irrelevant_visual,
        )
        record(
            "visual_check_requires_relevant_render_angle",
            (
                "independent_visual_check_evidence_irrelevant:"
                "scalp_no_nonhair_black_patch_or_cap_artifact"
            )
            in irrelevant_visual_result["failures"],
            irrelevant_visual_result["failures"],
        )

        one_sided_knee_visual = deepcopy(visual)
        one_sided_knee_visual["check_results"][
            "knees_no_reverse_or_hyperextension"
        ]["evidence_render_labels"] = ["pose_knee_flexion"]
        one_sided_knee_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=one_sided_knee_visual,
        )
        record(
            "both_knees_require_dedicated_visual_evidence",
            (
                "independent_visual_check_evidence_incomplete:"
                "knees_no_reverse_or_hyperextension"
            )
            in one_sided_knee_result["failures"],
            one_sided_knee_result["failures"],
        )

        crown_only_visual = deepcopy(visual)
        crown_only_visual["check_results"][
            "scalp_no_nonhair_black_patch_or_cap_artifact"
        ]["evidence_render_labels"] = ["crown_top_close"]
        crown_only_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=crown_only_visual,
        )
        record(
            "crown_and_rear_hairline_evidence_are_both_required",
            (
                "independent_visual_check_evidence_incomplete:"
                "scalp_no_nonhair_black_patch_or_cap_artifact"
            )
            in crown_only_result["failures"],
            crown_only_result["failures"],
        )

        missing_independent = evaluate_candidate_package(
            root,
            request,
            evidence,
            visual_review=visual,
        )
        record(
            "build_booleans_cannot_replace_independent_geometry_and_pose_audits",
            "independent_topology_intersection_audit_missing"
            in missing_independent["failures"]
            and "independent_bounded_deformation_audit_missing"
            in missing_independent["failures"],
            missing_independent["failures"],
        )

        intersecting_payload = deepcopy(topology_payload)
        intersecting_payload["self_intersection"][
            "nonadjacent_intersecting_source_face_pair_count"
        ] = 2
        intersecting_payload["topology_intersection_gate_passed"] = False
        intersecting_path = (
            topology_audit.parent / "intersecting_topology_audit.json"
        )
        write_json(intersecting_path, intersecting_payload)
        intersecting_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=intersecting_payload,
            topology_audit_path=intersecting_path,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "independent_self_intersection_failure_blocks_admission",
            "independent_primary_body_self_intersections"
            in intersecting_result["failures"]
            and "independent_topology_intersection_gate_failed"
            in intersecting_result["failures"],
            intersecting_result["failures"],
        )

        unsupported_boundary_payload = deepcopy(topology_payload)
        unsupported_boundary_payload["primary_body"][
            "boundary_component_support"
        ]["coverage_complete"] = False
        unsupported_boundary_payload["primary_body"][
            "boundary_component_support"
        ]["supported_boundary_loop_count"] = 2
        unsupported_boundary_payload["primary_body"][
            "boundary_component_support"
        ]["unsupported_boundary_loop_count"] = 1
        unsupported_boundary_payload[
            "topology_intersection_gate_passed"
        ] = False
        unsupported_boundary_path = (
            topology_audit.parent / "unsupported_boundary_audit.json"
        )
        write_json(unsupported_boundary_path, unsupported_boundary_payload)
        unsupported_boundary_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=unsupported_boundary_payload,
            topology_audit_path=unsupported_boundary_path,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "manual_boundary_count_cannot_replace_component_contact_proof",
            "independent_boundary_component_support_incomplete"
            in unsupported_boundary_result["failures"]
            and "independent_unsupported_boundary_component_present"
            in unsupported_boundary_result["failures"],
            unsupported_boundary_result["failures"],
        )

        wrong_deformation_payload = deepcopy(deformation_payload)
        wrong_deformation_payload["candidate_sha256"] = "0" * 64
        wrong_deformation_path = (
            deformation_audit.parent / "wrong_hash_deformation_audit.json"
        )
        write_json(wrong_deformation_path, wrong_deformation_payload)
        wrong_deformation_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=wrong_deformation_payload,
            deformation_audit_path=wrong_deformation_path,
            visual_review=visual,
        )
        record(
            "deformation_audit_must_bind_exact_candidate_hash",
            "independent_deformation_candidate_sha256_mismatch"
            in wrong_deformation_result["failures"],
            wrong_deformation_result["failures"],
        )

        incomplete_pose_policy = deepcopy(deformation_payload)
        incomplete_pose_policy["required_pose_labels"] = [
            label
            for label in REQUIRED_DEFORMATION_POSE_LABELS
            if label != "knee_flexion"
        ]
        incomplete_pose_policy_path = (
            deformation_audit.parent / "incomplete_pose_policy.json"
        )
        write_json(incomplete_pose_policy_path, incomplete_pose_policy)
        incomplete_pose_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=incomplete_pose_policy,
            deformation_audit_path=incomplete_pose_policy_path,
            visual_review=visual,
        )
        record(
            "dedicated_knee_flexion_pose_is_required",
            "independent_required_pose_policy_mismatch"
            in incomplete_pose_result["failures"],
            incomplete_pose_result["failures"],
        )

        missing_right_knee_policy = deepcopy(deformation_payload)
        missing_right_knee_policy["required_pose_labels"] = [
            label
            for label in REQUIRED_DEFORMATION_POSE_LABELS
            if label != "knee_flexion_right"
        ]
        missing_right_knee_policy_path = (
            deformation_audit.parent / "missing_right_knee_policy.json"
        )
        write_json(
            missing_right_knee_policy_path,
            missing_right_knee_policy,
        )
        missing_right_knee_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=missing_right_knee_policy,
            deformation_audit_path=missing_right_knee_policy_path,
            visual_review=visual,
        )
        record(
            "right_knee_flexion_pose_is_independently_required",
            "independent_required_pose_policy_mismatch"
            in missing_right_knee_result["failures"],
            missing_right_knee_result["failures"],
        )

        wrong_knee_direction = deepcopy(deformation_payload)
        wrong_knee_record = wrong_knee_direction["pose_records"][
            "knee_flexion_right"
        ]
        wrong_knee_record["anatomical_knee_direction_passed"] = False
        wrong_knee_record["anatomical_knee_direction"]["passed"] = False
        wrong_knee_record["anatomical_knee_direction"][
            "posterior_ankle_displacement_m"
        ] = -0.22
        wrong_knee_path = (
            deformation_audit.parent / "wrong_knee_direction.json"
        )
        write_json(wrong_knee_path, wrong_knee_direction)
        wrong_knee_result = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=wrong_knee_direction,
            deformation_audit_path=wrong_knee_path,
            visual_review=visual,
        )
        record(
            "encoded_knee_pose_must_bend_in_anatomical_direction",
            (
                "independent_anatomical_knee_direction_failed:"
                "knee_flexion_right"
            )
            in wrong_knee_result["failures"]
            and (
                "independent_anatomical_knee_measurement_invalid:"
                "knee_flexion_right"
            )
            in wrong_knee_result["failures"],
            wrong_knee_result["failures"],
        )

        evidence_payload = fixture["evidence_payload"]
        assert isinstance(evidence_payload, dict)
        contaminated_payload = deepcopy(evidence_payload)
        contaminated_payload["source"]["prohibited_reference"] = (
            "C:/Users/example/Desktop/reference/identity_photo.png"
        )
        contaminated = evidence.parent / "contaminated.json"
        write_json(contaminated, contaminated_payload)
        contaminated_result = evaluate_candidate_package(
            root,
            request,
            contaminated,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "private_identity_reference_path_blocks_candidate",
            any(
                failure.startswith("prohibited_private_identity_source:")
                for failure in contaminated_result["failures"]
            ),
            contaminated_result["failures"],
        )

        selection = fixture["selection"]
        assert isinstance(selection, Path)
        selection.write_bytes(b'{"selection":"changed"}\n')
        runtime_changed = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "changed_runtime_sentinel_blocks_candidate",
            "runtime_sentinel_changed:body_selection"
            in runtime_changed["failures"],
            runtime_changed["failures"],
        )
        selection.write_bytes(b'{"selection":"unchanged"}\n')

        bad_parameters = deepcopy(fixture["request_payload"])
        assert isinstance(bad_parameters, dict)
        bad_parameters["parameters"]["hands"] = 3.0
        try:
            validate_rapid_body_request(bad_parameters)
        except RapidBodyRequestError:
            bounded_rejected = True
        else:
            bounded_rejected = False
        record(
            "out_of_range_owner_control_is_rejected",
            bounded_rejected,
            bad_parameters["parameters"]["hands"],
        )

        unknown = deepcopy(fixture["request_payload"])
        assert isinstance(unknown, dict)
        unknown["parameters"]["hidden_person_delta"] = 0.1
        try:
            validate_rapid_body_request(unknown)
        except RapidBodyRequestError:
            unknown_rejected = True
        else:
            unknown_rejected = False
        record(
            "unknown_hidden_parameter_is_rejected",
            unknown_rejected,
            "hidden_person_delta",
        )

        runtime_gate_payload = deepcopy(evidence_payload)
        runtime_gate_payload["gates"]["runtime_assignment_allowed"] = True
        runtime_gate = evidence.parent / "runtime_gate.json"
        write_json(runtime_gate, runtime_gate_payload)
        runtime_gate_result = evaluate_candidate_package(
            root,
            request,
            runtime_gate,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "build_claiming_runtime_assignment_is_blocked",
            "build_gate_false_required:runtime_assignment_allowed"
            in runtime_gate_result["failures"],
            runtime_gate_result["failures"],
        )

    with tempfile.TemporaryDirectory(
        prefix="kira_licensed_derivative_gate_"
    ) as tmp:
        root = Path(tmp)
        fixture = make_fixture(root)
        convert_fixture_to_licensed_derivative(root, fixture)
        request = fixture["request"]
        evidence = fixture["evidence"]
        topology_audit = fixture["topology_audit"]
        topology_payload = fixture["topology_payload"]
        deformation_audit = fixture["deformation_audit"]
        deformation_payload = fixture["deformation_payload"]
        visual = fixture["visual_review"]
        assert isinstance(request, Path)
        assert isinstance(evidence, Path)
        assert isinstance(topology_audit, Path)
        assert isinstance(topology_payload, dict)
        assert isinstance(deformation_audit, Path)
        assert isinstance(deformation_payload, dict)
        assert isinstance(visual, dict)

        derivative_valid = evaluate_candidate_package(
            root,
            request,
            evidence,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "licensed_derivative_evidence_family_requires_same_independent_gate",
            derivative_valid["private_inspection_roster_admission_allowed"]
            is True
            and derivative_valid["evidence_family"]
            == "licensed_derivative_foundation_v1"
            and derivative_valid["source_authority"]["provenance"][
                "attribution_required"
            ]
            is True,
            derivative_valid["failures"],
        )

        derivative_payload = fixture["evidence_payload"]
        assert isinstance(derivative_payload, dict)
        leaked = deepcopy(derivative_payload)
        leaked["privacy"]["robert_private_photos_used"] = True
        leaked_path = evidence.parent / "derivative_private_leak.json"
        write_json(leaked_path, leaked)
        leaked_result = evaluate_candidate_package(
            root,
            request,
            leaked_path,
            topology_audit=topology_payload,
            topology_audit_path=topology_audit,
            deformation_audit=deformation_payload,
            deformation_audit_path=deformation_audit,
            visual_review=visual,
        )
        record(
            "licensed_derivative_blocks_robert_private_reference_use",
            "build_privacy_false_required:robert_private_photos_used"
            in leaked_result["failures"],
            leaked_result["failures"],
        )

    report = {
        "schema_version": 1,
        "suite": "avatar_builder_rapid_body_candidate_gate",
        "status": "PASSED",
        "tests_passed": sum(1 for row in rows if row["passed"]),
        "tests_failed": sum(1 for row in rows if not row["passed"]),
        "tests": rows,
        "runtime_mutation_performed": False,
        "runtime_assignment_allowed": False,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_PATH, report)
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
