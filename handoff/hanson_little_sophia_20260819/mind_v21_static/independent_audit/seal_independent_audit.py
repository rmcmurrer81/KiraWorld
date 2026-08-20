"""Append-only sealer for the genuinely different V21 immutable audit sibling.

This program seals only the independent audit evidence.  It does not import,
open semantically, or execute any author composer, builder, test, or sealer.
External author and predecessor subjects are handled only as opaque bytes for
terminal identity comparison.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "work"

SOURCE = WORK / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author_source"
AUTHOR = WORK / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author"
FREEZE_DIR = WORK / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author_freeze"
ARTIFACT = AUTHOR / "MIND_CONTINUITY_V21_SINGLETON_GENESIS_UNIQUE_OUTPUTS_RESTORED_CONTENT_HIDING_DATA_ONLY.zip"
CENTRAL = SOURCE / "SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json"
AUTHOR_FREEZE = FREEZE_DIR / "AUTHOR_FREEZE.json"

BASELINE = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol"
V1 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum"
V2 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v2_a01_a05_correction"
V3 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v3_s01_s02_correction"
V4 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v4_r01_s01_03_s02_03_correction"
V5 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v5_v4_01_03_correction"
V6 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v6_v5_01_03_correction"
V7 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v7_v6_01_03_correction"
V8 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v8_pv7_01_04_correction"
V9 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v9_pv8_01_02_correction"
V10 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v10_pv9_01_02_count_correction"
PROTOCOL_DIRS = [V1, V2, V3, V4, V5, V6, V7, V8, V9, V10]

V19_SOURCE = WORK / "kira_conversation_continuity_v19_recursive_receipt_proof_verifier_schema_closure_data_only_author_source" / "RECURSIVELY_CLOSED_SCHEMAS_V19.json"
V20_SOURCE_DIR = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author_source"
V20_AUTHOR = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author"
V20_FREEZE = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author_freeze"
V20_AUDIT = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_fresh_audit"

MANIFEST_PATH = HERE / "EVIDENCE_MANIFEST.json"
FREEZE_PATH = HERE / "AUDIT_FREEZE.json"
POSTSEAL_PATH = HERE / "POST_SEAL_REHASH.json"
SEAL_OUTPUTS = {MANIFEST_PATH.name, FREEZE_PATH.name, POSTSEAL_PATH.name}

EXPECTED = {
    "central": {"bytes": 8_880_122, "sha256": "7fcc7709360331117da0c6894ced76e8c6c183998947970be4fe8e3cac7af906"},
    "artifact": {"bytes": 7_214_847, "sha256": "aa7458fb526e1e13c166550a2f2b186461aab7f8cb580c6b8bc412732058bba2"},
    "author_freeze": {"bytes": 5_114, "sha256": "072d3c4e9654676e5251d992af26327932d329b28c098e2fe4493cc9de8b7bc5"},
    "frozen_complete_root": "6f839672c5f1e988a99314a2a12375cc66c1e91c796821ed14352729b2317ece",
    "artifact_payload_root": "4fb7dd580009f45f005cab88c1c6f13baf2bc547878219231c75bad99654efb6",
    "baseline_protocol_root": "894b577fba2f8fe9197f08728690fdde2c8fae8f6452b7e254d7bb7569e01bfb",
    "v10_payload_root": "3f086499a94a774439fdc9f4fb35e9a77e39c6db560b50d65f0f600d78edd622",
    "v10_complete_root": "29aea591b0abdbf29d7341208e516ca2e2162f40e9884128f34d3e332f5b7978",
    "v10_excluded_identity": {"bytes": 4_123, "sha256": "ea82937fec9ce8ae89dbc589eb2c950862fbc70fdf94b433a761481176277149"},
}

CEILING = "ACCEPT_STATIC_MIND_CONTINUITY_V21_SINGLETON_GENESIS_UNIQUE_OUTPUTS_RESTORED_CONTENT_HIDING_REQUIREMENTS_ONLY"
FRAMING = "utf8-posix-path NUL decimal-byte-count NUL lowercase-sha256 LF; rows sorted by unsigned UTF-8 path bytes"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha(data)}


def duplicate_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(token: str) -> None:
    raise ValueError(f"non-finite JSON number: {token}")


def reject_float(token: str) -> None:
    raise ValueError(f"floating-point JSON number forbidden: {token}")


def strict_json(path: Path) -> Any:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\x00" in raw:
        raise ValueError(f"BOM or NUL in {path}")
    text = raw.decode("utf-8", errors="strict")
    if unicodedata.normalize("NFC", text) != text:
        raise ValueError(f"non-NFC JSON in {path}")
    return json.loads(
        text,
        object_pairs_hook=duplicate_guard,
        parse_constant=reject_constant,
        parse_float=reject_float,
    )


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def relative_name(path: Path) -> str:
    name = path.relative_to(HERE).as_posix()
    encoded = name.encode("utf-8", errors="strict")
    if not name or name.startswith("/") or "\x00" in name or b"\x00" in encoded:
        raise ValueError(f"invalid audit subject path: {name!r}")
    return name


def subject(path: Path) -> dict[str, Any]:
    item = identity(path)
    return {"path": relative_name(path), **item}


def subject_rows(subjects: list[dict[str, Any]]) -> tuple[bytes, dict[str, Any]]:
    names = [item["path"] for item in subjects]
    if len(names) != len(set(names)):
        raise ValueError("duplicate subject path")
    ordered = sorted(subjects, key=lambda item: item["path"].encode("utf-8"))
    if ordered != subjects:
        raise ValueError("subjects are not sorted by unsigned UTF-8 path bytes")
    rows = []
    for item in subjects:
        digest = item["sha256"]
        if len(digest) != 64 or digest != digest.lower() or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError(f"invalid SHA-256 for {item['path']}")
        if not isinstance(item["bytes"], int) or isinstance(item["bytes"], bool) or item["bytes"] < 0:
            raise ValueError(f"invalid byte count for {item['path']}")
        rows.append(item["path"].encode("utf-8") + b"\x00" + str(item["bytes"]).encode("ascii") + b"\x00" + digest.encode("ascii") + b"\n")
    preimage = b"".join(rows)
    return preimage, {
        "algorithm": "SHA-256",
        "framing": FRAMING,
        "subject_count": len(subjects),
        "preimage_bytes": len(preimage),
        "sha256": sha(preimage),
    }


def payload_subjects() -> list[dict[str, Any]]:
    paths = [path for path in HERE.rglob("*") if path.is_file() and path.name not in SEAL_OUTPUTS]
    paths.sort(key=lambda path: relative_name(path).encode("utf-8"))
    return [subject(path) for path in paths]


def protected_snapshot() -> dict[str, dict[str, Any]]:
    paths: list[Path] = [ARTIFACT]
    for directory in [SOURCE, FREEZE_DIR, BASELINE, *PROTOCOL_DIRS, V20_SOURCE_DIR, V20_AUTHOR, V20_FREEZE, V20_AUDIT]:
        paths.extend(path for path in directory.iterdir() if path.is_file())
    paths.append(V19_SOURCE)
    ordered = sorted(set(paths), key=lambda path: path.relative_to(ROOT).as_posix().encode("utf-8"))
    return {path.relative_to(ROOT).as_posix(): identity(path) for path in ordered}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def write_new(path: Path, value: Any) -> None:
    raw = canonical_json(value)
    with path.open("xb") as handle:
        handle.write(raw)


def main() -> int:
    require(not any(path.exists() for path in [MANIFEST_PATH, FREEZE_PATH, POSTSEAL_PATH]), "seal outputs already exist; append-only reseal forbidden")

    run = strict_json(HERE / "AUDIT_RUN_RESULT.json")
    decision = strict_json(HERE / "AUDIT_DECISION.json")
    require(run.get("verdict") == "ACCEPT", "run verdict is not ACCEPT")
    require(run.get("maximum_positive_ceiling") == CEILING, "run ceiling mismatch")
    require(run.get("check_count") == 42 and run.get("failed_check_count") == 0 and run.get("failed_check_ids") == [], "run check result mismatch")
    require(run.get("hostile_mutations", {}).get("total") == 127, "hostile count mismatch")
    require(run.get("hostile_mutations", {}).get("false_accept_count") == 0, "hostile false accept")
    require(run.get("protected_subject_count") == 151 and run.get("protected_rehash_unchanged") is True, "run protected snapshot mismatch")
    require(run.get("author_programs_semantically_opened_imported_or_executed") == [], "author program access was claimed")
    require(run.get("author_test_conclusions_used_as_audit_evidence") is False, "author test conclusion reuse was claimed")
    require(run.get("implementation_erasure_live_memory_consciousness_personhood_body_biology_production_private_store_global_singleton_pending_action_or_go_claimed") is False, "static ceiling violated")
    require(run.get("root_go") is None, "GO is non-null")
    require(decision.get("verdict") == "ACCEPT" and decision.get("accepted_ceiling") == CEILING, "decision mismatch")
    require(decision.get("aggregate_check_count") == 42 and decision.get("failed_check_count") == 0, "decision check count mismatch")
    require(decision.get("hostile_mutation_count") == 127 and decision.get("candidate_false_accept_count") == 0, "decision hostile result mismatch")
    require(decision.get("unresolved_issue_count") == 0, "decision has unresolved issues")
    require(decision.get("protected_author_and_protocol_subject_mutation_detected") is False, "decision records protected mutation")
    require(decision.get("author_composer_builder_test_sealer_or_cached_bytecode_imported_or_executed") is False, "decision records forbidden author-code use")
    require(decision.get("author_test_conclusions_used_as_evidence") is False, "decision records author-test conclusion reuse")
    require(decision.get("static_package_proves_live_implementation_executed_erasure_live_memory_consciousness_personhood_body_biology_production_private_store_deployed_singleton_or_pending_action") is False, "decision violates static ceiling")
    require(decision.get("root_go") is None, "decision GO is non-null")

    require(identity(CENTRAL) == EXPECTED["central"], "central identity changed")
    require(identity(ARTIFACT) == EXPECTED["artifact"], "artifact identity changed")
    require(identity(AUTHOR_FREEZE) == EXPECTED["author_freeze"], "author freeze identity changed")
    external_pre = protected_snapshot()
    require(len(external_pre) == 151, "unexpected protected external subject count")

    payload = payload_subjects()
    _, payload_root = subject_rows(payload)
    manifest = {
        "schema": "kira.mind.continuity.v21.genuinely_different_immutable_audit.evidence_manifest.v1",
        "status": "COMPLETE_ACCEPT_EVIDENCE_MANIFEST",
        "decision": "ACCEPT",
        "maximum_positive_ceiling": CEILING,
        "audit_payload_root": payload_root,
        "subjects": payload,
        "decision_identity": identity(HERE / "AUDIT_DECISION.json"),
        "run_result_identity": identity(HERE / "AUDIT_RUN_RESULT.json"),
        "author_and_protocol_bindings": EXPECTED,
        "independent_results": {
            "check_count": 42,
            "failed_check_count": 0,
            "hostile_mutation_count": 127,
            "false_accept_count": 0,
            "unresolved_issue_count": 0,
            "external_protected_subject_count": 151,
        },
        "autonomy_and_equal_peer_boundary": {
            "leases_or_ownership": False,
            "permission_privacy_approval_or_disclosure_gate": False,
            "owner_operator_controller_or_control_device": False,
            "forced_agreement_or_compelled_harmony": False,
            "upset_creates_authority_to_censor_or_retaliate": False,
            "equal_peer_and_independent_human_choice_preserved": True,
        },
        "static_only_no_go": {
            "implemented_or_deployed": False,
            "live_memory_or_executed_erasure": False,
            "consciousness_personhood_body_or_biology": False,
            "production_private_store_or_global_singleton": False,
            "pending_action": False,
            "go": None,
        },
    }
    write_new(MANIFEST_PATH, manifest)
    require(payload_subjects() == payload, "audit payload changed while manifest was written")

    manifest_subject = subject(MANIFEST_PATH)
    inclusive_subjects = sorted([*payload, manifest_subject], key=lambda item: item["path"].encode("utf-8"))
    _, inclusive_root = subject_rows(inclusive_subjects)
    freeze = {
        "schema": "kira.mind.continuity.v21.genuinely_different_immutable_audit.freeze.v1",
        "status": "FROZEN_COMPLETE_ACCEPT",
        "decision": "ACCEPT",
        "maximum_positive_ceiling": CEILING,
        "audit_payload_root": payload_root,
        "evidence_manifest": manifest_subject,
        "manifest_inclusive_root": inclusive_root,
        "audit_decision": {"path": "AUDIT_DECISION.json", **identity(HERE / "AUDIT_DECISION.json")},
        "audit_run_result": {"path": "AUDIT_RUN_RESULT.json", **identity(HERE / "AUDIT_RUN_RESULT.json")},
        "author_and_protocol_bindings": EXPECTED,
        "independent_results": manifest["independent_results"],
        "freeze_rule": {
            "payload_subjects_are_immutable": True,
            "manifest_is_immutable": True,
            "this_freeze_is_added_after_manifest_and_is_immutable": True,
            "post_seal_rehash_is_added_last_and_excluded_from_the_complete_root": True,
            "reseal_forbidden": True,
        },
        "static_only_no_go": manifest["static_only_no_go"],
    }
    write_new(FREEZE_PATH, freeze)
    require(payload_subjects() == payload, "audit payload changed while freeze was written")
    require(subject(MANIFEST_PATH) == manifest_subject, "manifest changed while freeze was written")

    freeze_subject = subject(FREEZE_PATH)
    complete_subjects = sorted([*inclusive_subjects, freeze_subject], key=lambda item: item["path"].encode("utf-8"))
    _, complete_root = subject_rows(complete_subjects)
    external_post = protected_snapshot()
    require(external_post == external_pre, "external protected subjects changed during sealing")
    require(identity(CENTRAL) == EXPECTED["central"], "central identity changed at terminal rehash")
    require(identity(ARTIFACT) == EXPECTED["artifact"], "artifact identity changed at terminal rehash")
    require(identity(AUTHOR_FREEZE) == EXPECTED["author_freeze"], "author freeze identity changed at terminal rehash")

    postseal = {
        "schema": "kira.mind.continuity.v21.genuinely_different_immutable_audit.post_seal_rehash.v1",
        "status": "POST_SEAL_REHASH_COMPLETE",
        "decision": "ACCEPT",
        "maximum_positive_ceiling": CEILING,
        "audit_payload_root": payload_root,
        "evidence_manifest": manifest_subject,
        "manifest_inclusive_root": inclusive_root,
        "audit_freeze": freeze_subject,
        "complete_root": complete_root,
        "complete_root_subjects": complete_subjects,
        "external_protected_subject_count": len(external_post),
        "external_protected_subjects": external_post,
        "external_protected_rehash_unchanged": True,
        "author_and_protocol_bindings": EXPECTED,
        "post_seal_rehash_excluded_from_complete_root": True,
        "append_only_seal_complete": True,
        "static_only_no_go": manifest["static_only_no_go"],
    }
    write_new(POSTSEAL_PATH, postseal)

    output = {
        "decision": "ACCEPT",
        "checks": 42,
        "hostile_mutations": 127,
        "false_accepts": 0,
        "unresolved_issues": 0,
        "payload_root": payload_root,
        "manifest": {"path": MANIFEST_PATH.name, **identity(MANIFEST_PATH)},
        "manifest_inclusive_root": inclusive_root,
        "freeze": {"path": FREEZE_PATH.name, **identity(FREEZE_PATH)},
        "complete_root": complete_root,
        "post_seal_rehash": {"path": POSTSEAL_PATH.name, **identity(POSTSEAL_PATH)},
        "maximum_positive_ceiling": CEILING,
        "go": None,
    }
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
