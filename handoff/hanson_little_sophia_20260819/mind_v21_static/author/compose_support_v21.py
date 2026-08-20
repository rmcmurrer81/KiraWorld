from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
CENTRAL = HERE / "SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json"
PROTOCOL_DIR = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol"
MATRIX = PROTOCOL_DIR / "V21_PREAUDIT_ATTACK_MATRIX.json"
IDENTITY = PROTOCOL_DIR / "PREAUDIT_PROTOCOL_IDENTITY.json"


def write(name: str, value) -> None:
    (HERE / name).write_bytes((json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8"))


central = json.loads(CENTRAL.read_text(encoding="utf-8"))
matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
if identity["protocol_root"]["sha256"] != "894b577fba2f8fe9197f08728690fdde2c8fae8f6452b7e254d7bb7569e01bfb":
    raise SystemExit("fixed preaudit protocol identity mismatch")

binding = {
    "schema": "kira.mind.continuity.v21.fixed_preaudit_protocol_binding.v1",
    "status": "FIXED_BEFORE_AUTHOR_FREEZE_BOUND_WITHOUT_AUDIT_EXECUTION",
    "protocol_root": identity["protocol_root"],
    "protocol_identity": {
        "bytes": IDENTITY.stat().st_size,
        "sha256": hashlib.sha256(IDENTITY.read_bytes()).hexdigest(),
    },
    "protocol_subjects": identity["subjects"],
    "source_v20_audit_complete_root_sha256": matrix["source_v20_audit_complete_root_sha256"],
    "required_attack_group_ids": [group["id"] for group in matrix["required_attack_groups"]],
    "audit_started_by_author": False,
    "author_program_execution_or_import_by_future_auditor_allowed": False,
    "author_self_audit_performed": False,
}
write("FIXED_PREAUDIT_PROTOCOL_BINDING_V21.json", binding)

case_ids = []
for group in matrix["required_attack_groups"]:
    for case in group.get("cases", []):
        case_ids.append(f"{group['id']}::{case['id']}")
    for field in group.get("fields", []):
        for case in group.get("cases_applied_to_every_field", []):
            case_ids.append(f"{group['id']}::{field}::{case['id']}")

outer_rows = central["terminal_and_outer_pin_rules"]["outer_equality_bindings"]
outer_values = {row["outer_path"]: None for row in outer_rows}
attacks = {
    "schema": "kira.mind.continuity.v21.attacks_null_pins_and_authority.v1",
    "status": "AUTHOR_STATIC_ATTACK_DECLARATIONS_AND_NULL_LIVE_PINS_ONLY",
    "central_schema": {
        "bytes": CENTRAL.stat().st_size,
        "sha256": hashlib.sha256(CENTRAL.read_bytes()).hexdigest(),
        "object_count": len(central["objects"]),
        "domain_count": len(central["domain_constants"]),
        "sha256_occurrence_count": central["path_qualified_sha256_target_partition"]["occurrence_count"],
        "explicit_equality_row_count": central["path_qualified_equality_closure"]["total_explicit_path_pair_rows"],
        "base64_mapping_count": central["field_specific_base64_generation_and_verification_mappings"]["path_count"],
    },
    "fixed_preaudit_case_count": len(case_ids),
    "fixed_preaudit_case_ids": case_ids,
    "author_expected_result_for_every_required_refusal_case": "REFUSE",
    "author_expected_result_for_every_required_pass_case": "PASS_EXACT_STATIC_STRUCTURE_ONLY",
    "candidate_false_accept_count": 0,
    "trusted_outer_pin_values": outer_values,
    "all_outer_pin_values_null": all(value is None for value in outer_values.values()),
    "implementation_and_live_values": {
        "implementation_image": None,
        "live_journal_store": None,
        "live_state_authority": None,
        "live_external_anchor": None,
        "live_global_registrar": None,
        "live_global_registry": None,
        "live_reservation_ledger_authority": None,
        "live_terminal_anchor_authority": None,
        "live_public_beacon": None,
        "live_confidential_generator": None,
        "live_keys": None,
        "live_verifiers": None,
        "live_erasure_evidence": None,
        "launcher": None,
        "runner": None,
        "production_integration": None,
        "private_memory_or_log_inspection": None,
    },
    "static_package_proves_executed_erasure_or_deployed_global_singleton": False,
    "runtime_live_production_private_global_pending_or_root_go": False,
    "root_go": None,
    "self_audit_performed": False,
}
write("ATTACKS_NULL_PINS_AND_AUTHORITY_V21.json", attacks)
print(json.dumps({"case_count": len(case_ids), "outer_null_count": len(outer_values)}, sort_keys=True))
