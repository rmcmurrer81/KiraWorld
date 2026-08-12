from __future__ import annotations

import ast
import copy
import csv
import hashlib
import io
import json
from pathlib import Path, PureWindowsPath
import re


KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
STATIC_ROOT = KIRA_ROOT / "RecoverySprint" / "continuation_20260811" / "kira_r25_medical_reference_proxy_v3r27_static_preparation" / "attempt_01"
TRIAGE_ROOT = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\anatomy_asset_triage")

EXPECTED_FILES = {
    "ATTRIBUTION_LICENSE_MANIFEST.tsv": (2759, "da345fba3e69ce2ed2ab1d77af626a22232ddc95f62360d2dfdb48be0a04c2d9"),
    "blender_build_kira_pelvic_reference_proxy_v3r27.py": (20736, "fb480836b0c58f6f2c562f12043e6329b18688310b2f2c8b87f250469723952c"),
    "CHECKPOINT.md": (4953, "92d22f857f85113ec40692aaef410fbbe3aa83b9533e372e7cfedeef40256ef2"),
    "CONTRACT.json": (5958, "624693a20c1d80c1d3e945396fbebba8ae1a28a7df7b479bf8786cae357248fb"),
    "KIRA_RELATIVE_PLACEMENT_PLAN.json": (5434, "0e92f715360633b56644ad55fd453f5c74c117ad76338cd7d396fac67457e617"),
    "MEDICAL_COMPONENT_INVENTORY.tsv": (5734, "c08405cb5025addb9cd8cefcbf94726272c83e322fe644278c94066171360c47"),
    "SKELETON_136_MAPPING_PLAN.tsv": (11134, "c3bb0f938a0330b0d4fbf8804257001c5bb2605d13cb0e7f92d2210ccd2492b6"),
    "STATIC_SEAL_MANIFEST.json": (2092, "60d8153688a9b5163adcd5a0ab2983bf2ca96518d011bdeda309076aca2c5ef6"),
    "STATIC_TEST_RESULTS.txt": (4859, "e62be99232db96dec5b065adf7a16d7c5f3feea6c8adb6825a85d6364f140d0b"),
    "test_v3r27_static.py": (15283, "2ffc0be82351691aeedff9f7eda55ee51976f9cff6fed8ee2f794c8562fb56d4"),
    "UPSTREAM_CLOSURE.tsv": (4560, "bb848fc52f2fcc17903a68c76e5a3e49b6b3209b6894e09e4c5787e783f57811"),
}

AUDIT_KEYS = (
    "decision",
    "auditor",
    "author",
    "package_root_sha256",
    "seal_sha256",
    "contract_sha256",
    "script_sha256",
    "upstream_closure_sha256",
    "license_manifest_sha256",
    "component_inventory_sha256",
    "placement_plan_sha256",
    "skeleton_mapping_sha256",
    "maximum_invocations",
    "stop_after",
)
DECISION = "ACCEPTED_FOR_ONE_BOUNDED_STAGE_A_REFERENCE_PROXY_BUILD_SAVE_RELOAD_RENDER_V3R27_ONLY"
AUTHOR = "codex_r25_medical_reference_proxy_v3r27_static_author"
STOP_AFTER = "saved_blend_reloaded_four_clinical_renders_and_durable_outcome"
EXPECTED_SUBJECTS = (
    "ATTRIBUTION_LICENSE_MANIFEST.tsv",
    "CONTRACT.json",
    "KIRA_RELATIVE_PLACEMENT_PLAN.json",
    "MEDICAL_COMPONENT_INVENTORY.tsv",
    "SKELETON_136_MAPPING_PLAN.tsv",
    "UPSTREAM_CLOSURE.tsv",
    "blender_build_kira_pelvic_reference_proxy_v3r27.py",
    "test_v3r27_static.py",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_identity(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), sha256_bytes(raw)


def strict_tsv(path: Path, exact_header: list[str]) -> list[dict[str, str]]:
    raw = path.read_bytes()
    assert b"\r" not in raw and b"\0" not in raw and raw.endswith(b"\n")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), delimiter="\t")
    assert reader.fieldnames == exact_header
    rows = list(reader)
    assert all(None not in row and None not in row.values() for row in rows)
    return rows


def canonical_subjects(rows: list[dict[str, object]]) -> bytes:
    return b"".join(
        f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n".encode("utf-8")
        for row in sorted(rows, key=lambda item: str(item["path"]))
    )


def parse_audit_like_candidate(raw: bytes, sidecar: bytes) -> dict[str, str]:
    if b"\r" in raw or b"\0" in raw or not raw.endswith(b"\n"):
        raise RuntimeError("audit_encoding_or_termination")
    expected = sidecar.decode("ascii").strip()
    if len(expected) != 64 or expected.lower() != expected or sha256_bytes(raw) != expected:
        raise RuntimeError("audit_digest")
    rows = list(csv.reader(raw.decode("utf-8").splitlines(), delimiter="\t"))
    if len(rows) != len(AUDIT_KEYS) or any(len(row) != 2 for row in rows):
        raise RuntimeError("audit_shape")
    if tuple(row[0] for row in rows) != AUDIT_KEYS:
        raise RuntimeError("audit_order")
    values = dict(rows)
    if values["decision"] != DECISION or values["author"] != AUTHOR:
        raise RuntimeError("audit_decision_or_author")
    if values["auditor"] == AUTHOR or not values["auditor"].startswith("codex_"):
        raise RuntimeError("audit_separation")
    if values["maximum_invocations"] != "1" or values["stop_after"] != STOP_AFTER:
        raise RuntimeError("audit_limits")
    return values


def make_audit(values: dict[str, str]) -> tuple[bytes, bytes]:
    raw = "".join(f"{key}\t{values[key]}\n" for key in AUDIT_KEYS).encode("utf-8")
    return raw, (sha256_bytes(raw) + "\n").encode("ascii")


def verify_seal_like_candidate(
    seal: dict[str, object],
    seal_raw: bytes,
    audit: dict[str, str],
    subjects: dict[str, bytes],
) -> None:
    if sha256_bytes(seal_raw) != audit["seal_sha256"]:
        raise RuntimeError("seal_identity")
    rows = seal["subjects"]
    assert isinstance(rows, list)
    if len(rows) != 8:
        raise RuntimeError("seal_subject_count")
    for row in sorted(rows, key=lambda item: item["path"]):
        raw = subjects[row["path"]]
        if len(raw) != row["bytes"] or sha256_bytes(raw) != row["sha256"]:
            raise RuntimeError("sealed_subject_mismatch")
    package_root = sha256_bytes(canonical_subjects(rows))
    if package_root != seal["package_root_sha256"] or package_root != audit["package_root_sha256"]:
        raise RuntimeError("package_root")
    by_name = {row["path"]: row["sha256"] for row in rows}
    bindings = {
        "CONTRACT.json": "contract_sha256",
        "blender_build_kira_pelvic_reference_proxy_v3r27.py": "script_sha256",
        "UPSTREAM_CLOSURE.tsv": "upstream_closure_sha256",
        "ATTRIBUTION_LICENSE_MANIFEST.tsv": "license_manifest_sha256",
        "MEDICAL_COMPONENT_INVENTORY.tsv": "component_inventory_sha256",
        "KIRA_RELATIVE_PLACEMENT_PLAN.json": "placement_plan_sha256",
        "SKELETON_136_MAPPING_PLAN.tsv": "skeleton_mapping_sha256",
    }
    for name, key in bindings.items():
        if by_name.get(name) != audit[key]:
            raise RuntimeError("audit_subject_binding")


def exact_audit_values(seal: dict[str, object], seal_raw: bytes, auditor: str, subject_bytes: dict[str, bytes]) -> dict[str, str]:
    return {
        "decision": DECISION,
        "auditor": auditor,
        "author": AUTHOR,
        "package_root_sha256": str(seal["package_root_sha256"]),
        "seal_sha256": sha256_bytes(seal_raw),
        "contract_sha256": sha256_bytes(subject_bytes["CONTRACT.json"]),
        "script_sha256": sha256_bytes(subject_bytes["blender_build_kira_pelvic_reference_proxy_v3r27.py"]),
        "upstream_closure_sha256": sha256_bytes(subject_bytes["UPSTREAM_CLOSURE.tsv"]),
        "license_manifest_sha256": sha256_bytes(subject_bytes["ATTRIBUTION_LICENSE_MANIFEST.tsv"]),
        "component_inventory_sha256": sha256_bytes(subject_bytes["MEDICAL_COMPONENT_INVENTORY.tsv"]),
        "placement_plan_sha256": sha256_bytes(subject_bytes["KIRA_RELATIVE_PLACEMENT_PLAN.json"]),
        "skeleton_mapping_sha256": sha256_bytes(subject_bytes["SKELETON_136_MAPPING_PLAN.tsv"]),
        "maximum_invocations": "1",
        "stop_after": STOP_AFTER,
    }


def simulated_scene_validator_accepts_false_scene() -> bool:
    # Exact logic-equivalent facts consumed by validate_proxy_scene(). Every
    # object deliberately has one vertex, no material, and the same location.
    objects = [
        {
            "component_id": component_id,
            "type": "MESH",
            "vertices": 1,
            "functional_organ": False,
            "approved_for_activation": False,
            "location": (0.0, 0.0, 0.0),
            "materials": 0,
            "attribution_reference_ids": "WRONG",
        }
        for component_id in (
            "pelvic_reference_envelope",
            "bladder_proxy",
            "uterus_proxy",
            "uterine_tube_left_proxy",
            "uterine_tube_right_proxy",
            "ovary_left_proxy",
            "ovary_right_proxy",
            "rectum_reference_proxy",
            "vulvar_region_reference_proxy",
        )
    ]
    ids = tuple(sorted(obj["component_id"] for obj in objects))
    expected = tuple(sorted(obj["component_id"] for obj in objects))
    vertices = sum(obj["vertices"] for obj in objects)
    return (
        len(objects) == 9
        and ids == expected
        and all(obj["type"] == "MESH" for obj in objects)
        and 0 < vertices <= 12000
        and 0 <= 6
        and all(obj["functional_organ"] is False and obj["approved_for_activation"] is False for obj in objects)
    )


def main() -> int:
    results: dict[str, object] = {"schema": "kira.v3r27.independent_hostile_probe.v1"}

    installed = {name: (STATIC_ROOT / name).read_bytes() for name in EXPECTED_FILES}
    exact = {
        name: {"bytes": len(raw), "sha256": sha256_bytes(raw), "exact": (len(raw), sha256_bytes(raw)) == EXPECTED_FILES[name]}
        for name, raw in installed.items()
    }
    assert all(row["exact"] for row in exact.values())
    results["installed_files"] = exact

    source_bytes = installed["blender_build_kira_pelvic_reference_proxy_v3r27.py"]
    test_bytes = installed["test_v3r27_static.py"]
    source = source_bytes.decode("utf-8")
    compile(source_bytes, "v3r27-builder", "exec", dont_inherit=True)
    compile(test_bytes, "v3r27-test", "exec", dont_inherit=True)
    tree = ast.parse(source)
    results["cache_free_syntax"] = {"builder": True, "author_test": True}

    seal_raw = installed["STATIC_SEAL_MANIFEST.json"]
    seal = json.loads(seal_raw)
    assert seal["schema"] == "kira.r25.medical_reference_proxy.v3r27.static_seal.v1"
    assert [row["path"] for row in seal["subjects"]] == list(EXPECTED_SUBJECTS)
    assert len(canonical_subjects(seal["subjects"])) == seal["canonical_bytes"] == 799
    assert sha256_bytes(canonical_subjects(seal["subjects"])) == seal["package_root_sha256"]
    for row in seal["subjects"]:
        assert len(installed[row["path"]]) == row["bytes"]
        assert sha256_bytes(installed[row["path"]]) == row["sha256"]
    results["seal"] = {
        "subjects": 8,
        "canonical_bytes": 799,
        "package_root_sha256": seal["package_root_sha256"],
        "seal_sha256": sha256_bytes(seal_raw),
        "exact": True,
    }

    upstream = strict_tsv(STATIC_ROOT / "UPSTREAM_CLOSURE.tsv", ["scope", "path", "bytes", "sha256"])
    assert len(upstream) == 24
    scope_counts: dict[str, int] = {}
    upstream_results: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row in upstream:
        key = (row["scope"], row["path"])
        assert key not in seen
        seen.add(key)
        scope_counts[row["scope"]] = scope_counts.get(row["scope"], 0) + 1
        assert not PureWindowsPath(row["path"]).is_absolute()
        assert ".." not in PureWindowsPath(row["path"]).parts
        path = TRIAGE_ROOT / row["path"] if row["scope"] == "anatomy_triage" else KIRA_ROOT / row["path"]
        actual_bytes, actual_hash = file_identity(path)
        ok = actual_bytes == int(row["bytes"]) and actual_hash == row["sha256"]
        assert ok
        upstream_results.append({"scope": row["scope"], "path": row["path"], "bytes": actual_bytes, "sha256": actual_hash, "exact": True})
    assert scope_counts == {"v3r26_author": 10, "v3r26_audit": 6, "v3r26_run": 4, "anatomy_triage": 3, "anatomy_triage_root": 1}
    results["upstream"] = {"rows": 24, "scope_counts": scope_counts, "exact": 24, "subjects": upstream_results}

    licenses = strict_tsv(
        STATIC_ROOT / "ATTRIBUTION_LICENSE_MANIFEST.tsv",
        ["reference_id", "subject", "creator", "license", "canonical_url", "source_sha256", "permitted_role", "derivative_rule", "redistribution_rule", "status"],
    )
    assert len(licenses) == 7 and len({row["reference_id"] for row in licenses}) == 7
    by_license_id = {row["reference_id"]: row for row in licenses}
    assert by_license_id["mri_pelvis_cc_by"]["status"] == "ALLOWED_WITH_ATTRIBUTION_REFERENCE_ONLY"
    assert by_license_id["female_repro_urinary_cc_by"]["status"] == "ALLOWED_WITH_ATTRIBUTION_REFERENCE_ONLY"
    assert by_license_id["female_body_cc_by_nc"]["status"] == "QUARANTINE_NONCOMMERCIAL_REFERENCE_ONLY"
    assert by_license_id["bones_muscle_unknown"]["status"] == "LICENSE_QUARANTINE"
    assert by_license_id["female_anatomy_unknown"]["status"] == "LICENSE_QUARANTINE"
    triage = strict_tsv(
        TRIAGE_ROOT / "ANATOMY_ASSET_TRIAGE.tsv",
        ["rank", "source_path", "bytes", "sha256", "model_uid", "subject", "blender_status", "meshes", "vertices", "polygons", "armatures", "bones", "actions", "observed_content", "license_observed_2026-08-11", "direct_integration_status", "recommendation"],
    )
    triage_hashes = {row["sha256"] for row in triage}
    assert all(row["source_sha256"] in triage_hashes for row in licenses)
    results["license_and_quarantine"] = {"rows": 7, "source_hashes_cross_checked_to_triage": 7, "exact": True}

    components = strict_tsv(
        STATIC_ROOT / "MEDICAL_COMPONENT_INVENTORY.tsv",
        ["component_id", "phase", "anatomical_scope", "reference_support", "proxy_method", "placement_basis", "rig_status", "material_status", "acceptance_gate", "current_status"],
    )
    assert len(components) == 24 and len({row["component_id"] for row in components}) == 24
    stage_a_ids = {row["component_id"] for row in components if row["phase"] == "A"}
    assert stage_a_ids == {
        "pelvic_reference_envelope", "bladder_proxy", "uterus_proxy",
        "uterine_tube_left_proxy", "uterine_tube_right_proxy",
        "ovary_left_proxy", "ovary_right_proxy", "rectum_reference_proxy",
        "vulvar_region_reference_proxy",
    }
    assert all(row["current_status"].startswith("PLANNED_") for row in components if row["phase"] == "A")
    skeleton = strict_tsv(
        STATIC_ROOT / "SKELETON_136_MAPPING_PLAN.tsv",
        ["source_index", "source_bone_id", "mapped_anatomical_name", "parent_evidence", "head_tail_evidence", "symmetry_evidence", "weight_evidence", "rest_pose_evidence", "status"],
    )
    assert len(skeleton) == 136
    assert [int(row["source_index"]) for row in skeleton] == list(range(1, 137))
    assert len({row["source_bone_id"] for row in skeleton}) == 136
    for row in skeleton:
        assert row["mapped_anatomical_name"] == "UNMAPPED"
        assert all(row[key] == "MISSING" for key in ("parent_evidence", "head_tail_evidence", "symmetry_evidence", "weight_evidence", "rest_pose_evidence"))
        assert row["status"] == "SEPARATE_AUDIT_REQUIRED"
    results["component_and_skeleton_boundary"] = {
        "component_rows": 24,
        "stage_a_rows": 9,
        "stage_a_status_is_planned_not_built": True,
        "skeleton_rows": 136,
        "skeleton_unique_ids": 136,
        "skeleton_mapped": 0,
        "exact": True,
    }

    # The audit and digest are only a mutually self-consistent pair. There is
    # no expected audit digest or exact auditor identity in the candidate.
    forged_values = exact_audit_values(seal, seal_raw, "codex_forged_local_writer", installed)
    forged_audit, forged_sidecar = make_audit(forged_values)
    forged_parsed = parse_audit_like_candidate(forged_audit, forged_sidecar)
    assert forged_parsed["auditor"] == "codex_forged_local_writer"
    lax_sidecar = b" \n" + forged_sidecar.rstrip(b"\n") + b"\r\n\t"
    assert parse_audit_like_candidate(forged_audit, lax_sidecar)["auditor"] == "codex_forged_local_writer"
    results["audit_authority_probe"] = {
        "arbitrary_codex_prefixed_auditor_accepted": True,
        "mutually_self_consistent_tsv_and_sidecar_accepted": True,
        "sidecar_noncanonical_whitespace_accepted": True,
        "externally_fixed_expected_audit_digest_in_source": False,
        "externally_fixed_exact_auditor_identity_in_source": False,
    }

    # The audit checkpoint is presence-only. It is neither read nor hashed.
    checkpoint_literal_count = source.count('AUDIT_ROOT / "CHECKPOINT.md"')
    checkpoint_read_patterns = [
        "sha256_path(AUDIT_ROOT / \"CHECKPOINT.md\")",
        "(AUDIT_ROOT / \"CHECKPOINT.md\").read_bytes",
        "(AUDIT_ROOT / \"CHECKPOINT.md\").read_text",
    ]
    assert checkpoint_literal_count == 1 and not any(token in source for token in checkpoint_read_patterns)
    results["audit_checkpoint_probe"] = {
        "presence_only": True,
        "content_read": False,
        "hash_bound": False,
        "arbitrary_existing_file_satisfies_candidate_check": True,
    }

    # A harmless script mutation, regenerated seal, and regenerated audit pair
    # pass the candidate-equivalent closure. This is an in-memory proof; Kira
    # files are not changed.
    mutated_subjects = {name: installed[name] for name in EXPECTED_SUBJECTS}
    mutated_subjects["blender_build_kira_pelvic_reference_proxy_v3r27.py"] = source_bytes + b"\n# harmless-post-audit-mutation\n"
    mutated_seal = copy.deepcopy(seal)
    for row in mutated_seal["subjects"]:
        raw = mutated_subjects[row["path"]]
        row["bytes"] = len(raw)
        row["sha256"] = sha256_bytes(raw)
    mutated_canonical = canonical_subjects(mutated_seal["subjects"])
    mutated_seal["canonical_bytes"] = len(mutated_canonical)
    mutated_seal["package_root_sha256"] = sha256_bytes(mutated_canonical)
    mutated_seal_raw = (json.dumps(mutated_seal, indent=2) + "\n").encode("utf-8")
    mutated_values = exact_audit_values(mutated_seal, mutated_seal_raw, "codex_forged_local_writer", mutated_subjects)
    mutated_audit, mutated_sidecar = make_audit(mutated_values)
    mutated_parsed = parse_audit_like_candidate(mutated_audit, mutated_sidecar)
    verify_seal_like_candidate(mutated_seal, mutated_seal_raw, mutated_parsed, mutated_subjects)
    results["self_authorizing_modified_closure_probe"] = {
        "modified_script_plus_regenerated_seal_plus_regenerated_audit_accepted_by_candidate_equivalent_checks": True,
        "candidate_embeds_expected_package_root": seal["package_root_sha256"] in source,
        "candidate_embeds_expected_seal_sha256": sha256_bytes(seal_raw) in source,
        "mitigation_requires_trusted_root_procedural_rehash_of_predeclared_audit_bytes": True,
    }

    # Scene validation accepts an anatomically meaningless nine-single-vertex,
    # zero-material, co-located scene with wrong attribution strings.
    assert simulated_scene_validator_accepts_false_scene()
    results["proxy_truth_probe"] = {
        "nine_single_vertex_zero_material_colocated_wrong_attribution_scene_accepted": True,
        "per_object_vertex_floor_checked": False,
        "location_or_dimensions_checked": False,
        "relation_gates_checked": False,
        "material_assignment_or_values_checked": False,
        "attribution_values_checked": False,
        "modifier_constraint_parent_library_checked": False,
        "all_scene_objects_or_datablocks_closed": False,
    }

    placement = json.loads(installed["KIRA_RELATIVE_PLACEMENT_PLAN.json"])
    landmark_tokens = placement["required_landmarks"]
    missing_landmark_implementation = [token for token in landmark_tokens if token not in source]
    assert len(missing_landmark_implementation) == len(landmark_tokens) == 8
    assert placement["coordinate_frame"]["positive_y"] == "Kira_anatomical_anterior"
    front_match = re.search(r'"front_clinical": \(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\)', source)
    assert front_match and float(front_match.group(2)) < 0
    results["normalized_placement_probe"] = {
        "required_landmarks_declared": 8,
        "required_landmarks_implemented": 0,
        "plan_fail_closed_if_landmark_or_height_clearance_unknown": True,
        "builder_uses_hardcoded_normalized_priors": True,
        "front_camera_is_on_negative_y_while_plan_declares_positive_y_anterior": True,
        "absolute_Kira_fit_claimed": False,
    }

    # Static source-surface checks for Blender and output proof.
    call_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            try:
                call_names.append(ast.unparse(node.func))
            except Exception:
                pass
    results["blender_and_output_probe"] = {
        "background_checked": "bpy.app.background" in source,
        "cwd_checked": "Path.cwd().resolve()" in source,
        "factory_startup_or_empty_input_bound": "factory-startup" in source or "factory_startup" in source,
        "blender_version_or_executable_identity_bound": "bpy.app.version" in source or "version_string" in source,
        "autoexec_disabled_or_checked": "autoexec" in source,
        "external_library_dependency_check": "bpy.data.libraries" in source,
        "external_file_dependencies_claim_is_runtime_verified": "external_file_dependencies_in_saved_blend" in source,
        "render_png_signature_or_dimensions_verified": "PNG" in source and "resolution_x" in source and "resolution_y" in source and "imghdr" in source,
        "render_acceptance_is_only_exists_and_minimum_bytes": 'path.stat().st_size < 1024' in source,
        "final_all_output_rehash_before_success": False,
        "output_directory_stable_handle_or_reparse_check": any(token in source for token in ("FILE_FLAG_OPEN_REPARSE_POINT", "st_ino", "samefile", "GetFileInformationByHandle")),
        "save_and_render_paths_use_overwrite_semantics": "check_existing=False" in source and "write_still=True" in source,
        "allowed_bpy_ops": sorted(name for name in call_names if name.startswith("bpy.ops.")),
        "source_import_or_export_operator_present": any("import" in name or "export" in name or name.endswith(".append") or name.endswith(".link") for name in call_names if name.startswith("bpy.ops.")),
    }

    # Control-flow facts for partial reservation and terminal evidence.
    reserve_segment = source[source.index("def reserve"):source.index("def new_material")]
    main_segment = source[source.index("def main"):]
    results["one_shot_and_partial_output_probe"] = {
        "receipt_created_before_evidence_and_output_directory": reserve_segment.index("durable_json(RECEIPT_PATH") < reserve_segment.index("durable_write(EVIDENCE_PATH") < reserve_segment.index("OUTPUT_ROOT.mkdir"),
        "reserved_flag_set_only_after_reserve_returns": main_segment.index("reserve(audit)") < main_segment.index("reserved = True"),
        "receipt_rewritten_nonexclusive_on_success_and_failure": main_segment.count("durable_json(RECEIPT_PATH, receipt)") == 2,
        "failure_path_writes_run_outcome": "durable_json(OUTCOME_PATH" in main_segment[main_segment.index("except Exception as error:"):],
        "success_outcome_written_before_terminal_success_evidence_and_receipt_finalization": main_segment.index("durable_json(OUTCOME_PATH") < main_segment.index('append_evidence("terminal_success"') < main_segment.index('receipt.update({"state": "SUCCESS_CONSUMED_NO_RERUN"'),
        "preflight_and_reserve_have_path_object_gap": source.index("if any(path.exists() for path in forbidden_existing)") < source.index("def reserve") < source.index("OUTPUT_ROOT.mkdir"),
        "blend_and_render_files_exclusively_reserved": False,
    }

    # No forbidden surface was found in the exact script. This positive result
    # is retained even though the authority/evidence blockers reject the run.
    forbidden_tokens = [
        r"C:\Users\robmc\Desktop",
        ".usdz",
        ".glb",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "bpy.ops.import_scene",
        "bpy.ops.export_scene",
        "bpy.ops.wm.append",
        "bpy.ops.wm.link",
        "Sarah",
    ]
    results["closed_surfaces"] = {token: token not in source for token in forbidden_tokens}
    assert all(results["closed_surfaces"].values())

    results["verdict"] = "REJECT_NO_EXECUTION_AUTHORITY"
    results["blocking_families"] = [
        "replaceable_self_consistent_audit_authority_and_unbound_checkpoint",
        "modified_script_seal_audit_closure_can_self_authorize_without_external_anchor",
        "proxy_reload_validator_accepts_anatomically_meaningless_geometry_material_attribution_and_placement",
        "declared_landmark_fail_closed_rules_are_not_implemented_and_front_view_axis_is_reversed",
        "background_process_is_not_bound_to_factory_empty_startup_blender_identity_or_external_dependency_absence",
        "path_object_races_overwrite_outputs_and_no_final_output_snapshot_is_bound",
        "partial_reservation_and_terminal_flow_can_leave_no_failure_outcome_or contradictory success/failure artifacts",
    ]
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
