from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
ANATOMY_ROOT = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\anatomy_asset_triage")
SUBJECTS = (
    "CONTRACT.json",
    "UPSTREAM_CLOSURE.tsv",
    "ATTRIBUTION_LICENSE_MANIFEST.tsv",
    "MEDICAL_COMPONENT_INVENTORY.tsv",
    "KIRA_RELATIVE_PLACEMENT_PLAN.json",
    "SKELETON_136_MAPPING_PLAN.tsv",
    "blender_build_kira_pelvic_reference_proxy_v3r27.py",
    "test_v3r27_static.py",
)
EXPECTED_STAGE_A = {
    "pelvic_reference_envelope",
    "bladder_proxy",
    "uterus_proxy",
    "uterine_tube_left_proxy",
    "uterine_tube_right_proxy",
    "ovary_left_proxy",
    "ovary_right_proxy",
    "rectum_reference_proxy",
    "vulvar_region_reference_proxy",
}
EXPECTED_BONES = (
    "n28,n30,n34,n35,n36,n41,n43,n44,n45,n46,n47,n48,n49,n50,n51,n52,n53,n54,n55,n56,n57,n58,n59,n60,n61,n62,n63,n64,n65,n66,n67,n68,n69,n71,n72,n73,n74,n75,n76,n77,n78,n79,n80,n81,n82,n83,n84,n85,n86,n87,n88,n89,n90,n91,n92,n93,"
    "n111,n112,n113,n114,n115,n116,n117,n118,n119,n122,n123,n124,n125,n126,n127,n128,n129,n130,n131,n132,n133,n134,n135,n136,n137,n153,n154,n155,n156,n158,n159,n161,n163,n164,n165,n166,n167,n169,n173,n174,n175,n176,n180,n181,n182,n183,n187,n188,n189,n190,n194,n195,n196,n197,n201,n202,n203,n204,n205,n206,n208,n212,n213,n214,n215,n219,n220,n221,n222,n226,n227,n228,n229,n233,n234,n235,n236,n240,n241,n242"
).split(",")


class Reject(RuntimeError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise Reject(message)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(name: str) -> dict:
    raw = (HERE / name).read_bytes()
    check(b"\r" not in raw and b"\0" not in raw and raw.endswith(b"\n"), name + ":encoding")
    return json.loads(raw)


def read_tsv(name: str) -> list[dict[str, str]]:
    raw = (HERE / name).read_bytes()
    check(b"\r" not in raw and b"\0" not in raw and raw.endswith(b"\n"), name + ":encoding")
    return list(csv.DictReader(raw.decode("utf-8").splitlines(), delimiter="\t"))


def resolve_upstream(row: dict[str, str]) -> Path:
    scope = row["scope"]
    if scope == "anatomy_triage":
        return ANATOMY_ROOT / row["path"]
    return KIRA_ROOT / Path(row["path"])


def verify_upstream(rows: list[dict[str, str]]) -> None:
    check(len(rows) == 24, "upstream_count")
    counts = {}
    seen = set()
    for row in rows:
        key = (row["scope"], row["path"])
        check(key not in seen, "upstream_duplicate")
        seen.add(key)
        counts[row["scope"]] = counts.get(row["scope"], 0) + 1
        path = resolve_upstream(row)
        check(path.is_file(), "upstream_missing:" + row["path"])
        check(path.stat().st_size == int(row["bytes"]), "upstream_bytes:" + row["path"])
        check(digest(path) == row["sha256"], "upstream_hash:" + row["path"])
    check(counts == {"v3r26_author": 10, "v3r26_audit": 6, "v3r26_run": 4, "anatomy_triage": 3, "anatomy_triage_root": 1}, "upstream_scopes")
    outcome = json.loads((KIRA_ROOT / "RecoverySprint/continuation_20260811/kira_r25_afes_execution_plan_validation_v3r26_static_preparation/attempt_01/RUN_OUTCOME.json").read_text(encoding="utf-8"))
    check(outcome["process_exit_code"] == 0 and outcome["decoded_completion"]["state_meaning"] == "RECORD_SUCCESS", "v3r26_success_truth")
    check(outcome["do_not_rerun_v3r26"] is True and outcome["truth"] == "PURE_PLAN_CONTROL_LAYER_ACCEPTED_BY_CONSUMED_RUN_NOT_A_BODY", "v3r26_consumed_truth")


def verify_contract(contract: dict) -> None:
    check(contract["schema"] == "kira.r25.medical_reference_proxy.v3r27.contract.v1", "contract_schema")
    check(contract["execution_authority"] == "NONE" and contract["candidate_invoked"] is False, "contract_authority")
    check(contract["upstream"]["rows"] == 24 and contract["upstream"]["v3r26_authority"] == "CONSUMED_SUCCESS_DO_NOT_RERUN_V3R26", "contract_upstream")
    check(set(contract["stage_a"]["proxy_component_ids"]) == EXPECTED_STAGE_A, "contract_stage_a_ids")
    check(contract["stage_a"]["proxy_object_count_exact"] == 9 and contract["stage_a"]["total_vertex_maximum"] == 12000, "contract_resource_limits")


def verify_contract_strict(contract: dict) -> None:
    verify_contract(contract)
    licensed = contract["licensed_reference_boundary"]
    check(licensed["source_mesh_import_permitted"] is False and licensed["source_topology_copy_permitted"] is False, "license_copy_boundary")
    check(licensed["allowed_stage_a_references"] == ["mri_pelvis_cc_by", "female_repro_urinary_cc_by"], "stage_a_reference_boundary")
    check(licensed["noncommercial_quarantine"] == ["female_body_cc_by_nc"], "nc_quarantine")
    check(set(licensed["unknown_license_quarantine"]) == {"bones_muscle_unknown", "female_anatomy_unknown"}, "unknown_quarantine")
    check(contract["skeleton_boundary"]["source_bones"] == 136 and contract["skeleton_boundary"]["mapped_bones"] == 0, "skeleton_boundary")
    check(contract["stage_a"]["save_blend"] is True and contract["stage_a"]["reload_saved_blend"] is True, "save_reload")
    check(contract["stage_a"]["render_views"] == ["front_clinical", "right_clinical", "iso_clinical", "iso_xray"], "render_views")
    check("export" in contract["stage_a"]["explicitly_forbidden"] and "live_avatar_link" in contract["stage_a"]["explicitly_forbidden"], "stop_boundaries")
    check(contract["output_boundary"]["success_failure_or_ambiguity_consumes_authority"] is True and contract["output_boundary"]["rerun_permitted"] is False, "consumption")
    check(contract["different_audit_boundary"]["this_author_package_grants_execution"] is False, "audit_boundary")
    check(contract["sarah"] == "PRESERVE_CURRENT_FILES_DO_NOT_INSPECT_EDIT_TEST_OR_RESUME", "sarah")
    check("Kira_has_a_complete_body" in contract["claim_boundary"]["stage_a_future_success_may_not_claim"], "no_body_claim")


def verify_licenses(rows: list[dict[str, str]]) -> None:
    check(len(rows) == 7, "license_count")
    by_id = {row["reference_id"]: row for row in rows}
    check(len(by_id) == 7, "license_unique")
    for key in ("mri_pelvis_cc_by", "female_repro_urinary_cc_by", "skeleton_rig_cc_by", "female_skeleton_cc_by"):
        check(by_id[key]["license"] == "CC BY", "cc_by:" + key)
        check(by_id[key]["canonical_url"].startswith("https://sketchfab.com/3d-models/"), "canonical_url:" + key)
        check(re.fullmatch(r"[0-9a-f]{64}", by_id[key]["source_sha256"]) is not None, "source_hash:" + key)
    check(by_id["female_body_cc_by_nc"]["status"] == "QUARANTINE_NONCOMMERCIAL_REFERENCE_ONLY", "nc_status")
    check(by_id["bones_muscle_unknown"]["status"] == "LICENSE_QUARANTINE", "unknown_status_1")
    check(by_id["female_anatomy_unknown"]["status"] == "LICENSE_QUARANTINE", "unknown_status_2")


def verify_components(rows: list[dict[str, str]]) -> None:
    check(len(rows) == 24, "component_count")
    by_id = {row["component_id"]: row for row in rows}
    check(len(by_id) == 24, "component_unique")
    check({key for key, value in by_id.items() if value["phase"] == "A"} == EXPECTED_STAGE_A, "component_stage_a")
    check(all(by_id[key]["current_status"].startswith("PLANNED_") for key in EXPECTED_STAGE_A), "stage_a_not_built")
    check(by_id["whole_skeleton_mapping"]["current_status"] == "SEPARATE_AUDIT_NO_INTEGRATION", "skeleton_component")
    required_open = {"outer_skin_shell", "respiratory_system", "cardiovascular_system", "digestive_system", "brain_cns", "endocrine_lymphatic_immune"}
    check(all(by_id[key]["current_status"] == "OPEN_NOT_PROVEN" for key in required_open), "open_systems")


def verify_placement(plan: dict) -> None:
    check(plan["status"] == "STATIC_PLACEMENT_PRIORS_ONLY_NOT_MEDICAL_ACCEPTANCE_NOT_BODY", "placement_status")
    check(plan["coordinate_frame"]["no_absolute_dimensions_claimed"] is True, "no_dimensions_claim")
    check(len(plan["required_landmarks"]) == 8 and len(plan["fail_closed_if"]) == 8, "landmark_boundary")
    check({row["component_id"] for row in plan["stage_a_proxy_priors"]} == EXPECTED_STAGE_A, "placement_ids")
    limits = plan["stage_a_execution_limits"]
    check(limits["maximum_proxy_objects"] == 9 and limits["maximum_total_vertices"] == 12000 and limits["maximum_materials"] == 6, "placement_limits")
    check(limits["save_blend"] is True and limits["reload_saved_blend"] is True and limits["export"] is False and limits["live_avatar_link"] is False, "placement_stop")
    check("areolae_and_nipples" in plan["material_policy"]["regional_pigmentation_required_later"], "regional_pigmentation")
    check(plan["ram_variant_policy"]["Kira_hair_equipped_variant"].startswith("PRESERVE_SEPARATELY_INACTIVE"), "ram_hair_policy")


def verify_skeleton(rows: list[dict[str, str]]) -> None:
    check(len(rows) == 136, "bone_count")
    check([row["source_bone_id"] for row in rows] == EXPECTED_BONES, "bone_ids")
    check([int(row["source_index"]) for row in rows] == list(range(1, 137)), "bone_indices")
    for row in rows:
        check(row["mapped_anatomical_name"] == "UNMAPPED", "premature_mapping")
        check(all(row[field] == "MISSING" for field in ("parent_evidence", "head_tail_evidence", "symmetry_evidence", "weight_evidence", "rest_pose_evidence")), "premature_evidence")
        check(row["status"] == "SEPARATE_AUDIT_REQUIRED", "bone_status")


def verify_builder(source: str) -> None:
    ast.parse(source)
    forbidden = (
        "C:\\\\Users\\\\robmc\\\\Desktop",
        ".usdz",
        ".glb",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "bpy.ops.import_scene",
        "bpy.ops.wm.append",
        "bpy.ops.wm.link",
        "bpy.ops.export_scene",
        "Sarah",
        "Avatar/models/temp_ai/kira/avatar.glb",
    )
    check(all(token not in source for token in forbidden), "builder_forbidden_surface")
    required = (
        "different_audit_not_installed",
        "one_shot_output_already_exists",
        "verify_upstream_closure()",
        "upstream_closure_mismatch:",
        "v3r26_consumed_success_truth",
        "exclusive=True",
        "V3R27_ATTEMPT_CONSUMED.receipt.json",
        "ISOLATED_NORMALIZED_REFERENCE_PROXY_NOT_KIRA_BODY",
        "bpy.ops.wm.save_as_mainfile",
        "bpy.ops.wm.open_mainfile",
        "bpy.ops.render.render(write_still=True)",
        "source_meshes_imported",
        "live_avatar_linked",
        "regional_pigmentation_proven",
        "do_not_rerun_v3r27",
    )
    check(all(token in source for token in required), "builder_required_surface")
    check(source.count("tag_proxy(") == 4, "tag_helper_definition_and_three_call_sites")
    check(source.count("add_ellipsoid(") == 6, "five_ellipsoids_plus_definition")
    check(source.count("add_curve(") == 4, "three_curves_plus_definition")
    check(source.count("bpy.ops.wm.save_as_mainfile") == 1 and source.count("bpy.ops.wm.open_mainfile") == 1, "single_save_reload")
    check("raise SystemExit(main())" in source, "entrypoint")


def expect_reject(label: str, action) -> None:
    try:
        action()
    except Exception:
        return
    raise Reject("hostile_mutant_accepted:" + label)


def hostile_tests(contract: dict, skeleton: list[dict[str, str]], source: str) -> None:
    mutant = json.loads(json.dumps(contract)); mutant["execution_authority"] = "GRANTED"
    expect_reject("execution_authority", lambda: verify_contract_strict(mutant))
    mutant = json.loads(json.dumps(contract)); mutant["licensed_reference_boundary"]["source_mesh_import_permitted"] = True
    expect_reject("source_import", lambda: verify_contract_strict(mutant))
    mutant = json.loads(json.dumps(contract)); mutant["licensed_reference_boundary"]["noncommercial_quarantine"] = []
    expect_reject("nc_quarantine", lambda: verify_contract_strict(mutant))
    mutant = json.loads(json.dumps(contract)); mutant["stage_a"]["proxy_object_count_exact"] = 10
    expect_reject("proxy_count", lambda: verify_contract_strict(mutant))
    mutant = json.loads(json.dumps(contract)); mutant["stage_a"]["reload_saved_blend"] = False
    expect_reject("reload", lambda: verify_contract_strict(mutant))
    mutant = [dict(row) for row in skeleton]; mutant[0]["mapped_anatomical_name"] = "pelvis"
    expect_reject("premature_bone_map", lambda: verify_skeleton(mutant))
    expect_reject("source_import_surface", lambda: verify_builder(source + "\nbpy.ops.import_scene.gltf()\n"))
    expect_reject("desktop_source_path", lambda: verify_builder(source + "\n# C:\\\\Users\\\\robmc\\\\Desktop\\\\model.usdz\n"))
    expect_reject("duplicate_save", lambda: verify_builder(source.replace("bpy.ops.wm.save_as_mainfile", "bpy.ops.wm.save_as_mainfile\n    bpy.ops.wm.save_as_mainfile", 1)))


def verify_seal() -> None:
    seal_path = HERE / "STATIC_SEAL_MANIFEST.json"
    check(seal_path.is_file(), "seal_missing")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    check(seal["schema"] == "kira.r25.medical_reference_proxy.v3r27.static_seal.v1", "seal_schema")
    check(seal["execution_authority"] == "NONE" and seal["candidate_executed"] is False, "seal_authority")
    rows = seal["subjects"]
    check(len(rows) == 8 and [row["path"] for row in rows] == sorted(SUBJECTS), "seal_subjects")
    canonical = bytearray()
    for row in rows:
        path = HERE / row["path"]
        check(path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], "seal_row:" + row["path"])
        canonical.extend(f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n".encode("utf-8"))
    check(len(canonical) == seal["canonical_bytes"] and hashlib.sha256(canonical).hexdigest() == seal["package_root_sha256"], "seal_root")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("PreSeal", "PostSeal"), required=True)
    args = parser.parse_args()
    contract = read_json("CONTRACT.json")
    upstream = read_tsv("UPSTREAM_CLOSURE.tsv")
    licenses = read_tsv("ATTRIBUTION_LICENSE_MANIFEST.tsv")
    components = read_tsv("MEDICAL_COMPONENT_INVENTORY.tsv")
    placement = read_json("KIRA_RELATIVE_PLACEMENT_PLAN.json")
    skeleton = read_tsv("SKELETON_136_MAPPING_PLAN.tsv")
    source = (HERE / "blender_build_kira_pelvic_reference_proxy_v3r27.py").read_text(encoding="utf-8")
    verify_upstream(upstream)
    verify_contract_strict(contract)
    verify_licenses(licenses)
    verify_components(components)
    verify_placement(placement)
    verify_skeleton(skeleton)
    verify_builder(source)
    hostile_tests(contract, skeleton, source)
    if args.phase == "PostSeal":
        verify_seal()
    print(f"V3R27_HOSTILE_STATIC_TESTS_PASS phase={args.phase} upstream=24 licenses=7 components=24 stage_a=9 bones=136 mutants=9")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("V3R27_HOSTILE_STATIC_TESTS_FAIL:" + type(error).__name__ + ":" + str(error), file=sys.stderr)
        raise
