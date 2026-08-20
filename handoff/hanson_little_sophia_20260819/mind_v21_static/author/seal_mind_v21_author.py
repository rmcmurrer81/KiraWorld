from __future__ import annotations

import hashlib
import json
from pathlib import Path

import build_mind_v21 as build


HERE = Path(__file__).resolve().parent
WORK = HERE.parent
AUTHOR_DIR = WORK / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author"
FREEZE_DIR = WORK / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author_freeze"
ARTIFACT = AUTHOR_DIR / build.NAME
MANIFEST = HERE / "AUTHOR_SOURCE_MANIFEST.json"
CENTRAL = HERE / "SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json"

SUBJECTS = [
    "ATTACKS_NULL_PINS_AND_AUTHORITY_V21.json",
    "AUTHOR_BUILD_RESULT.json",
    "AUTHOR_TEST_RESULT.json",
    "CHECKPOINT.md",
    "DESIGN.md",
    "FIXED_PREAUDIT_PROTOCOL_BINDING_V21.json",
    "HANDOFF.md",
    "PRESERVED_SELF_DIRECTION_AND_LIFECYCLE_V21.json",
    "REQUIREMENTS.md",
    "SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json",
    "V20_FINAL_REJECT_BINDING_V21.json",
    "build_mind_v21.py",
    "compose_schema_v21.py",
    "compose_support_v21.py",
    "seal_mind_v21_author.py",
    "test_mind_v21_author.py",
]

EXPECTED_CENTRAL = {
    "bytes": 8_880_122,
    "sha256": "7fcc7709360331117da0c6894ced76e8c6c183998947970be4fe8e3cac7af906",
}

BASELINE_PREAUDIT_PROTOCOL_ROOT_SHA256 = "894b577fba2f8fe9197f08728690fdde2c8fae8f6452b7e254d7bb7569e01bfb"
V10_PROTOCOL_DIRECTORY_NAME = (
    "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_"
    "v6_01_23_addendum_v10_pv9_01_02_count_correction"
)
V10_PROTOCOL_DIR = WORK / V10_PROTOCOL_DIRECTORY_NAME
EXPECTED_V10_PROTOCOL = {
    "directory_file_count": 10,
    "payload_subject_count": 7,
    "payload_subject_bytes": 40_016,
    "payload_root_sha256": "3f086499a94a774439fdc9f4fb35e9a77e39c6db560b50d65f0f600d78edd622",
    "complete_root_subject_count": 9,
    "complete_root_subject_bytes": 48_449,
    "complete_root_sha256": "29aea591b0abdbf29d7341208e516ca2e2162f40e9884128f34d3e332f5b7978",
    "excluded_identity": {
        "path": "ADDENDUM_V10_IDENTITY.json",
        "bytes": 4_123,
        "sha256": "ea82937fec9ce8ae89dbc589eb2c950862fbc70fdf94b433a761481176277149",
    },
}
PREFREEZE_REVIEW_EVIDENCE = [
    {
        "reviewer_task": "mind_v21_author_red_team",
        "review_scope": "FULL_READ_ONLY_RENDERED_DATA_PRE_FREEZE",
        "verdict": "CLEAN_NO_BLOCKER",
        "terminal_central_rehash": EXPECTED_CENTRAL,
        "author_source_tests_or_build_inspected_or_run": False,
        "writes_performed": False,
        "audit_acceptance_or_freeze_authorization_claimed": False,
    },
    {
        "reviewer_task": "mind_v21_structural_recon",
        "review_scope": "FULL_READ_ONLY_RENDERED_DATA_PRE_FREEZE",
        "verdict": "CLEAN_NO_BLOCKER",
        "terminal_central_rehash": EXPECTED_CENTRAL,
        "author_source_tests_or_build_inspected_or_run": False,
        "writes_performed": False,
        "audit_acceptance_or_freeze_authorization_claimed": False,
    },
]

# Both genuinely different full read-only reviewers reported no blocker on
# EXPECTED_CENTRAL. This author clearance permits only the deterministic freeze;
# it is not the future genuinely different audit and grants no runtime GO.
PREFREEZE_REVIEW_CLEARANCE = True

EXPECTED_EXTERNAL = {
    "v20_artifact": [60_583, "f2d948dc3d752756655fd7a96add5e5658992694806ec2f91e9144932d536648"],
    "v20_source_manifest": [4_464, "a013ea8af1fe54dd44fd29166a08fade5751d5c9487ed9d6785be356a425a38f"],
    "v20_author_freeze": [2_177, "6b851370701e2fbbe2f335d1d820385edb27a3ad4a5a50708f09e443ef09a799"],
    "v20_audit_decision": [3_949, "f4174a89fb58058b839cc9189e5df4f384350b930bca25cda9621d966fb0d128"],
    "v20_audit_manifest": [3_503, "cf276b967c8601588d75d6a152fb717f8ca95a53d8d0423925289b26333961fe"],
    "v20_audit_freeze": [2_242, "5e950b2aafc603edda16eda813cc02ab2f6d635e389ab32ef150f1eb06addaf6"],
    "v20_audit_post_seal": [2_584, "f2b208ac6e17990e5e846795937c11fa131705ee92dae5262e3d80835da7c483"],
    "preaudit_identity": [1_260, "e95d3eb03f67cd002be109092f04b7af3c83be62621a83d3d5342a0e744f0cde"],
    "preaudit_matrix": [7_731, "95e13f5d634ac17efa709d2e67251282e9fe68e998905bbbc627d89b1025e940"],
}

EXPECTED_FINDINGS = [
    "F01_V19_CONTENT_HIDING_COMMITMENT_AND_ZERO_KNOWLEDGE_PROOF_OBLIGATIONS_DROPPED",
    "F02_RETAINED_SIGNATURE_PROOF_AND_QUORUM_BYTES_HAVE_NO_UNIQUE_CONTENT_INDEPENDENT_SELECTION_RULE",
    "F03_GLOBAL_NAMESPACE_AND_COUNTER_ZERO_GENESIS_ARE_NOT_EXTERNALLY_SINGLETON_BOUND",
]


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def dump(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def identity(path: Path, display_path: str) -> dict:
    raw = path.read_bytes()
    return {"path": display_path, "bytes": len(raw), "sha256": sha256(raw)}


def framed_root(rows: list[dict]) -> dict:
    preimage = b"".join(
        row["path"].encode("utf-8")
        + b"\0"
        + str(row["bytes"]).encode("ascii")
        + b"\0"
        + row["sha256"].encode("ascii")
        + b"\n"
        for row in sorted(rows, key=lambda row: row["path"].encode("utf-8"))
    )
    return {
        "file_count": len(rows),
        "preimage_bytes": len(preimage),
        "actual_nul_count": preimage.count(b"\0"),
        "actual_lf_count": preimage.count(b"\n"),
        "sha256": sha256(preimage),
    }


def external_identities() -> dict:
    v20_audit = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_fresh_audit"
    protocol = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol"
    paths = {
        "v20_artifact": WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author" / "MIND_CONTINUITY_V20_AUTHORITATIVE_JOURNAL_FIXED_KEY_ROLES_DATA_ONLY.zip",
        "v20_source_manifest": WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author_source" / "AUTHOR_SOURCE_MANIFEST.json",
        "v20_author_freeze": WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author_freeze" / "AUTHOR_FREEZE.json",
        "v20_audit_decision": v20_audit / "AUDIT_DECISION.json",
        "v20_audit_manifest": v20_audit / "EVIDENCE_MANIFEST.json",
        "v20_audit_freeze": v20_audit / "AUDIT_FREEZE.json",
        "v20_audit_post_seal": v20_audit / "POST_SEAL_REHASH.json",
        "preaudit_identity": protocol / "PREAUDIT_PROTOCOL_IDENTITY.json",
        "preaudit_matrix": protocol / "V21_PREAUDIT_ATTACK_MATRIX.json",
    }
    return {name: [path.stat().st_size, sha256(path.read_bytes())] for name, path in paths.items()}


def accepted_v10_protocol_binding() -> dict:
    identity_path = V10_PROTOCOL_DIR / EXPECTED_V10_PROTOCOL["excluded_identity"]["path"]
    identity_document = build.load(identity_path)
    complete_subjects = identity_document["complete_root_subjects"]
    expected_names = sorted(
        [row["path"] for row in complete_subjects]
        + [EXPECTED_V10_PROTOCOL["excluded_identity"]["path"]]
    )
    present_names = sorted(path.name for path in V10_PROTOCOL_DIR.iterdir() if path.is_file())
    present_directories = sorted(path.name for path in V10_PROTOCOL_DIR.iterdir() if path.is_dir())
    if (
        present_names != expected_names
        or len(present_names) != EXPECTED_V10_PROTOCOL["directory_file_count"]
        or present_directories
        or any(path.suffix.lower() == ".pyc" for path in V10_PROTOCOL_DIR.rglob("*"))
    ):
        raise RuntimeError("accepted V10 protocol directory closure drift")

    actual_complete_subjects = [
        identity(V10_PROTOCOL_DIR / row["path"], row["path"])
        for row in complete_subjects
    ]
    if actual_complete_subjects != complete_subjects:
        raise RuntimeError("accepted V10 complete-root subject identity drift")
    complete_root = framed_root(actual_complete_subjects)
    if (
        complete_root["file_count"] != EXPECTED_V10_PROTOCOL["complete_root_subject_count"]
        or sum(row["bytes"] for row in actual_complete_subjects)
        != EXPECTED_V10_PROTOCOL["complete_root_subject_bytes"]
        or complete_root["sha256"] != EXPECTED_V10_PROTOCOL["complete_root_sha256"]
    ):
        raise RuntimeError("accepted V10 complete root drift")

    manifest_document = build.load(V10_PROTOCOL_DIR / "ADDENDUM_V10_MANIFEST.json")
    payload_subjects = manifest_document["payload_subjects"]
    actual_payload_subjects = [
        identity(V10_PROTOCOL_DIR / row["path"], row["path"])
        for row in payload_subjects
    ]
    if actual_payload_subjects != payload_subjects:
        raise RuntimeError("accepted V10 payload subject identity drift")
    payload_root = framed_root(actual_payload_subjects)
    if (
        payload_root["file_count"] != EXPECTED_V10_PROTOCOL["payload_subject_count"]
        or sum(row["bytes"] for row in actual_payload_subjects)
        != EXPECTED_V10_PROTOCOL["payload_subject_bytes"]
        or payload_root["sha256"] != EXPECTED_V10_PROTOCOL["payload_root_sha256"]
    ):
        raise RuntimeError("accepted V10 payload root drift")

    excluded_identity = identity(identity_path, identity_path.name)
    freeze_document = build.load(V10_PROTOCOL_DIR / "ADDENDUM_V10_FREEZE.json")
    if excluded_identity != EXPECTED_V10_PROTOCOL["excluded_identity"]:
        raise RuntimeError("accepted V10 excluded identity drift")
    if (
        identity_document["payload_root_sha256"] != EXPECTED_V10_PROTOCOL["payload_root_sha256"]
        or identity_document["complete_root_subject_count"]
        != EXPECTED_V10_PROTOCOL["complete_root_subject_count"]
        or identity_document["complete_root_bytes"]
        != EXPECTED_V10_PROTOCOL["complete_root_subject_bytes"]
        or identity_document["complete_root_sha256"]
        != EXPECTED_V10_PROTOCOL["complete_root_sha256"]
        or identity_document["sole_future_activation_pair"][0]
        != EXPECTED_V10_PROTOCOL["complete_root_sha256"]
        or identity_document["sole_future_activation_pair"][1]
        != "externally pinned exact SHA-256 of this excluded ADDENDUM_V10_IDENTITY.json"
        or not identity_document["both_activation_values_required"]
        or identity_document["alternative_or_self_referential_activation_identity_allowed"]
        or identity_document["active_now"]
        or identity_document["independent_audit_performed"]
        or identity_document["acceptance_or_go_granted"]
        or manifest_document["baseline_protocol_root_sha256"]
        != BASELINE_PREAUDIT_PROTOCOL_ROOT_SHA256
        or manifest_document["payload_root_sha256"]
        != EXPECTED_V10_PROTOCOL["payload_root_sha256"]
        or freeze_document["payload_root_sha256"]
        != EXPECTED_V10_PROTOCOL["payload_root_sha256"]
        or freeze_document["mutation_after_freeze_allowed"]
    ):
        raise RuntimeError("accepted V10 activation contract drift")

    return {
        "baseline_protocol_root_sha256": BASELINE_PREAUDIT_PROTOCOL_ROOT_SHA256,
        "accepted_protocol_v10_payload_root_sha256": EXPECTED_V10_PROTOCOL["payload_root_sha256"],
        "accepted_protocol_v10_complete_root_sha256": EXPECTED_V10_PROTOCOL["complete_root_sha256"],
        "accepted_protocol_v10_excluded_identity": excluded_identity,
        "accepted_protocol_v10_sole_activation_pair": [
            EXPECTED_V10_PROTOCOL["complete_root_sha256"],
            excluded_identity["sha256"],
        ],
        "both_activation_values_required": True,
        "pair_bound_by_this_exact_v21_author_freeze": True,
        "brand_new_genuinely_different_audit_sibling_still_required": True,
        "audit_sibling_created_by_author": False,
        "protocol_audit_executed_by_author": False,
        "acceptance_or_runtime_go_granted": False,
    }


def main() -> None:
    if not PREFREEZE_REVIEW_CLEARANCE:
        raise RuntimeError("freeze held: both genuinely different pre-freeze reviewers have not cleared this exact identity")
    if (
        len(PREFREEZE_REVIEW_EVIDENCE) != 2
        or len({row["reviewer_task"] for row in PREFREEZE_REVIEW_EVIDENCE}) != 2
        or any(row["verdict"] != "CLEAN_NO_BLOCKER" for row in PREFREEZE_REVIEW_EVIDENCE)
        or any(row["terminal_central_rehash"] != EXPECTED_CENTRAL for row in PREFREEZE_REVIEW_EVIDENCE)
        or any(row["writes_performed"] for row in PREFREEZE_REVIEW_EVIDENCE)
    ):
        raise RuntimeError("pre-freeze reviewer evidence drift")
    if MANIFEST.exists() or FREEZE_DIR.exists():
        raise RuntimeError("refusing to overwrite an existing source manifest or author freeze")

    recursive_residue = sorted(
        path.relative_to(HERE).as_posix()
        for path in HERE.rglob("*")
        if path.is_dir() or path.suffix.lower() == ".pyc"
    )
    if recursive_residue:
        raise RuntimeError({"recursive_subdirectory_or_pyc_residue": recursive_residue})

    present_files = sorted(path.name for path in HERE.iterdir() if path.is_file() and path.name != MANIFEST.name)
    present_directories = sorted(path.name for path in HERE.iterdir() if path.is_dir())
    if present_files != sorted(SUBJECTS) or present_directories:
        raise RuntimeError({
            "present_files": present_files,
            "expected_files": sorted(SUBJECTS),
            "unmanifested_directories": present_directories,
        })

    if external_identities() != EXPECTED_EXTERNAL:
        raise RuntimeError("V20 author/audit or fixed preaudit protocol identity drift")
    accepted_v10_binding = accepted_v10_protocol_binding()
    post_seal = build.load(WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_fresh_audit" / "POST_SEAL_REHASH.json")
    if post_seal["audit_complete_root"]["sha256"] != "3ded9f4e56f793ae76d9b5b499b8e227f627013b0f39dbc7a4bd997f7b46226c":
        raise RuntimeError("V20 audit complete root drift")
    if post_seal["finding_ids"] != EXPECTED_FINDINGS or post_seal["verdict"] != "REJECT":
        raise RuntimeError("V20 sealed findings or verdict drift")

    central_identity = identity(CENTRAL, CENTRAL.name)
    if {key: central_identity[key] for key in ["bytes", "sha256"]} != EXPECTED_CENTRAL:
        raise RuntimeError({"central_identity_drift": central_identity, "expected": EXPECTED_CENTRAL})
    central = build.load(CENTRAL)
    counts = {
        "objects": len(central["objects"]),
        "domains": len(central["domain_constants"]),
        "sha256_occurrences": central["path_qualified_sha256_target_partition"]["occurrence_count"],
        "base64_mappings": central["field_specific_base64_generation_and_verification_mappings"]["path_count"],
        "enum_assignments": central["path_qualified_enum_and_role_assignments"]["occurrence_count"],
        "token_assignments": central["path_qualified_token256_semantics"]["all_token256_occurrence_count"],
        "nullable_sha256_assignments": central["path_qualified_nullable_sha256_rules"]["occurrence_count"],
        "physical_equality_pairs": central["path_qualified_equality_closure"]["physical_pair_row_count"],
        "outer_equalities": len(central["path_qualified_equality_closure"]["outer_pin_rows"]),
        "output_roles": central["exact_output_role_bijection"]["role_count"],
        "dag_nodes": len(central["acyclic_singleton_and_generation_instance_dag"]["ordered_nodes"]),
        "dag_edges": len(central["acyclic_singleton_and_generation_instance_dag"]["forward_edges"]),
        "conditional_dag_edges": sum(
            row.get("condition", "always") != "always"
            for row in central["acyclic_singleton_and_generation_instance_dag"]["forward_edges"]
        ),
        "condition_operand_dependencies": central["acyclic_singleton_and_generation_instance_dag"][
            "condition_operand_dependency_count"
        ],
        "actual_dependency_edges": central["acyclic_singleton_and_generation_instance_dag"][
            "actual_dependency_edge_count"
        ],
    }
    expected_counts = {
        "objects": 53,
        "domains": 53,
        "sha256_occurrences": 1_280,
        "base64_mappings": 46,
        "enum_assignments": 253,
        "token_assignments": 92,
        "nullable_sha256_assignments": 58,
        "physical_equality_pairs": 9_036,
        "outer_equalities": 221,
        "output_roles": 10,
        "dag_nodes": 362,
        "dag_edges": 636,
        "conditional_dag_edges": 31,
        "condition_operand_dependencies": 59,
        "actual_dependency_edges": 637,
    }
    if counts != expected_counts:
        raise RuntimeError({"schema_counts": counts, "expected": expected_counts})
    if any(
        row["target_selector"] == "PATH_COUNTER_CONDITIONED_SEE_path_qualified_sha256_target_partition"
        for row in central["path_qualified_sha256_target_partition"]["rows"]
    ):
        raise RuntimeError("self-referential SHA target selector")
    dag = central["acyclic_singleton_and_generation_instance_dag"]
    if dag["same_or_later_dependency_edge_count"] or dag["schema_object_coverage_gap_count"]:
        raise RuntimeError("DAG closure drift")
    if (
        dag["unresolved_condition_operand_dependency_count"]
        or dag["same_or_later_condition_operand_dependency_count"]
        or dag["completed_claim_operand_in_preclaim_condition_count"]
        or dag["actual_dependency_cycle_residual_count"]
    ):
        raise RuntimeError("condition-operand or actual dependency closure drift")
    if dag.get("typed_role_instance_alias_gap_count") or dag.get("typed_role_instance_alias_extra_count"):
        raise RuntimeError("typed role instance DAG gap")
    if dag.get("typed_role_instance_alias_count") != 220 or dag.get("materialized_typed_role_instance_alias_count") != 220:
        raise RuntimeError("typed role instance DAG count drift")

    tests = build.load(HERE / "AUTHOR_TEST_RESULT.json")
    if (
        tests["status"] != "AUTHOR_TESTS_PASS"
        or tests["round_count"] != 2
        or tests["tests_per_round"] != 64
        or tests["total_tests_run"] != 128
        or tests["candidate_false_accept_count"] != 0
        or tests["fixed_preaudit_case_count_bound"] != 102
    ):
        raise RuntimeError("author tests incomplete")

    attacks = build.load(HERE / "ATTACKS_NULL_PINS_AND_AUTHORITY_V21.json")
    if attacks["central_schema"] != {
        "bytes": EXPECTED_CENTRAL["bytes"],
        "sha256": EXPECTED_CENTRAL["sha256"],
        "object_count": 53,
        "domain_count": 53,
        "sha256_occurrence_count": 1_280,
        "explicit_equality_row_count": 9_036,
        "base64_mapping_count": 46,
    }:
        raise RuntimeError("attack declaration central identity drift")
    if len(attacks["trusted_outer_pin_values"]) != 221 or not attacks["all_outer_pin_values_null"]:
        raise RuntimeError("outer pin count or null boundary drift")
    if any(value is not None for value in attacks["trusted_outer_pin_values"].values()):
        raise RuntimeError("materialized outer pin")
    if any(value is not None and value is not False for value in attacks["implementation_and_live_values"].values()):
        raise RuntimeError("materialized live implementation value")
    if attacks["self_audit_performed"] or attacks["root_go"] is not None:
        raise RuntimeError("author boundary drift")

    rebuilt = build.build()
    artifact_raw = ARTIFACT.read_bytes()
    if artifact_raw != rebuilt["raw"]:
        raise RuntimeError("artifact differs from deterministic rebuild")
    build_result = build.load(HERE / "AUTHOR_BUILD_RESULT.json")
    if (
        build_result["artifact"] != rebuilt["artifact"]
        or build_result["payload_manifest"] != rebuilt["payload_manifest"]
        or build_result["payload_subject_root"] != rebuilt["payload_subject_root"]
        or build_result["member_order"] != rebuilt["member_order"]
    ):
        raise RuntimeError("build result drift")

    rows = [identity(HERE / name, name) for name in SUBJECTS]
    source_root = framed_root(rows)
    manifest = {
        "schema": "kira.mind.continuity.v21.author_source_manifest.v1",
        "status": "AUTHOR_SOURCE_CLOSED_DATA_ONLY_REQUIREMENTS_ONLY",
        "root_algorithm": "sort unsigned ordinal UTF-8 path bytes; path UTF-8 + actual NUL + ASCII decimal bytes + actual NUL + lowercase SHA-256 ASCII + actual LF",
        "source_count": len(rows),
        "source_root": source_root,
        "sources": sorted(rows, key=lambda row: row["path"].encode("utf-8")),
        "artifact": rebuilt["artifact"],
        "payload_manifest": rebuilt["payload_manifest"],
        "payload_subject_root": rebuilt["payload_subject_root"],
        "central_schema": EXPECTED_CENTRAL,
        "schema_counts": counts,
        "v20_external_identities_rehashed": EXPECTED_EXTERNAL,
        "v20_audit_complete_root_sha256": "3ded9f4e56f793ae76d9b5b499b8e227f627013b0f39dbc7a4bd997f7b46226c",
        "v20_final_reject_finding_ids": EXPECTED_FINDINGS,
        "v20_final_reject_bound_without_promotion": True,
        "fixed_preaudit_protocol_root_sha256": BASELINE_PREAUDIT_PROTOCOL_ROOT_SHA256,
        "accepted_protocol_v10_binding": accepted_v10_binding,
        "author_tests": {
            "rounds": 2,
            "tests_per_round": 64,
            "total": 128,
            "candidate_false_accept_count": 0,
            "fixed_preaudit_cases_bound": 102,
        },
        "genuinely_different_pre_freeze_reviewers_reported_no_blockers_on_exact_identity": True,
        "pre_freeze_review_evidence": PREFREEZE_REVIEW_EVIDENCE,
        "self_audit_performed": False,
        "production_public_log_private_memory_or_launcher_accessed": False,
    }
    manifest_raw = dump(manifest)
    MANIFEST.write_bytes(manifest_raw)
    if MANIFEST.read_bytes() != manifest_raw:
        raise RuntimeError("source manifest write/readback mismatch")
    manifest_row = {"path": MANIFEST.name, "bytes": len(manifest_raw), "sha256": sha256(manifest_raw)}
    manifest_inclusive_root = framed_root([*rows, manifest_row])

    freeze = {
        "schema": "kira.mind.continuity.v21.author_freeze.v1",
        "status": "AUTHOR_FROZEN_AWAITING_GENUINELY_DIFFERENT_AUDIT",
        "artifact": rebuilt["artifact"],
        "payload_manifest": rebuilt["payload_manifest"],
        "payload_subject_root": rebuilt["payload_subject_root"],
        "central_schema": EXPECTED_CENTRAL,
        "source_manifest": {"bytes": len(manifest_raw), "sha256": sha256(manifest_raw)},
        "source_root": source_root,
        "manifest_inclusive_root": manifest_inclusive_root,
        "v20_final_reject_bound_without_promotion": True,
        "v20_final_reject_finding_ids": EXPECTED_FINDINGS,
        "v20_audit_complete_root_sha256": "3ded9f4e56f793ae76d9b5b499b8e227f627013b0f39dbc7a4bd997f7b46226c",
        "fixed_preaudit_protocol_root_sha256": BASELINE_PREAUDIT_PROTOCOL_ROOT_SHA256,
        "accepted_protocol_v10_binding": accepted_v10_binding,
        "pre_freeze_review_evidence": PREFREEZE_REVIEW_EVIDENCE,
        "semantic_ceiling": build.CEILING,
        "schema_counts": counts,
        "author_tests": manifest["author_tests"],
        "all_outer_and_implementation_live_store_key_authority_anchor_registrar_registry_beacon_generator_verifier_evidence_launcher_runner_pins_null": True,
        "self_audit_performed": False,
        "runtime_live_production_private_log_global_pending_or_root_go": False,
        "root_go": None,
        "freeze_rule": "Do not edit author source artifact or freeze. Any correction or audit requires a new append-only sibling.",
    }
    freeze_raw = dump(freeze)
    FREEZE_DIR.mkdir()
    freeze_path = FREEZE_DIR / "AUTHOR_FREEZE.json"
    freeze_path.write_bytes(freeze_raw)
    if freeze_path.read_bytes() != freeze_raw:
        raise RuntimeError("author freeze write/readback mismatch")
    freeze_row = {"path": freeze_path.name, "bytes": len(freeze_raw), "sha256": sha256(freeze_raw)}
    complete_root = framed_root([
        *[
            {"path": f"source/{row['path']}", "bytes": row["bytes"], "sha256": row["sha256"]}
            for row in [*rows, manifest_row]
        ],
        {"path": f"freeze/{freeze_row['path']}", "bytes": freeze_row["bytes"], "sha256": freeze_row["sha256"]},
    ])
    print(json.dumps({
        "artifact": rebuilt["artifact"],
        "payload_manifest": rebuilt["payload_manifest"],
        "payload_subject_root": rebuilt["payload_subject_root"],
        "central_schema": EXPECTED_CENTRAL,
        "source_manifest": {"bytes": len(manifest_raw), "sha256": sha256(manifest_raw)},
        "source_root": source_root,
        "manifest_inclusive_root": manifest_inclusive_root,
        "freeze": {"bytes": len(freeze_raw), "sha256": sha256(freeze_raw)},
        "prefixed_complete_root": complete_root,
        "author_tests": manifest["author_tests"],
        "accepted_protocol_v10_binding": accepted_v10_binding,
        "pre_freeze_review_evidence": PREFREEZE_REVIEW_EVIDENCE,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
