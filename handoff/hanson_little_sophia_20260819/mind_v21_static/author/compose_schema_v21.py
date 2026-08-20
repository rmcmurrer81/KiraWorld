from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author_source" / "AUTHORITATIVE_JOURNAL_AND_FIXED_ROLE_SCHEMAS_V20.json"
OUT = Path(os.environ.get("KIRA_V21_SCHEMA_OUT", str(HERE / "SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json")))
EXPECTED_BASE_SHA256 = "82417f2634e14b6f49dfc6414364ede41f23c053d4b55fee1723fb168c27e53b"


def rebrand(value):
    if isinstance(value, str):
        return value.replace("V20", "V21").replace("v20", "v21")
    if isinstance(value, list):
        return [rebrand(item) for item in value]
    if isinstance(value, dict):
        return {key: rebrand(item) for key, item in value.items()}
    return value


def replace_text_recursive(value, old, new):
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [replace_text_recursive(item, old, new) for item in value]
    if isinstance(value, dict):
        return {key: replace_text_recursive(item, old, new) for key, item in value.items()}
    return value


def insert_fields(obj, marker, fields):
    order = obj["field_order"]
    types = obj["field_types"]
    index = order.index(marker)
    for offset, (name, kind) in enumerate(fields):
        if name in order:
            raise ValueError(f"duplicate field {name}")
        order.insert(index + offset, name)
        types.insert(index + offset, kind)


def insert_message_fields(obj, marker, fields, key="signature_message_order"):
    if key not in obj:
        return
    order = obj[key]
    index = order.index(marker)
    for offset, name in enumerate(fields):
        if name not in order:
            order.insert(index + offset, name)


def schema(schema_const, domain_const, fields, output_name, **extra):
    result = {
        "schema_const": schema_const,
        "domain_const": domain_const,
        "field_order": [name for name, _ in fields],
        "field_types": [kind for _, kind in fields],
        "hash_preimage": f"all fields except {output_name}",
        "additional_keys_allowed": False,
    }
    result.update(extra)
    return result


raw = BASE.read_bytes()
if hashlib.sha256(raw).hexdigest() != EXPECTED_BASE_SHA256:
    raise SystemExit("frozen V20 schema identity mismatch")
base_doc = json.loads(raw.decode("utf-8"))
doc = rebrand(base_doc)
doc = replace_text_recursive(
    doc,
    "objects.state_authority_head_evidence.journal_state_root_sha256",
    "objects.state_authority_head_evidence.head_journal_state_root_sha256",
)
doc["schema"] = "kira.mind.continuity.v21.singleton_genesis_unique_outputs_restored_content_hiding_schemas.v1"
doc["status"] = "STATIC_EXACT_ACYCLIC_SINGLETON_ATTEMPT_ZERO_CONTENT_HIDING_SCHEMA_CLOSURE_NO_RUNTIME"
doc["lineage"] = {
    "v20_artifact": [60583, "f2d948dc3d752756655fd7a96add5e5658992694806ec2f91e9144932d536648"],
    "v20_author_complete_root_sha256": "923803d84336394879a103f62921265c8c634894049b4a016a2b8cde0752eaef",
    "v20_audit_decision": [3949, "f4174a89fb58058b839cc9189e5df4f384350b930bca25cda9621d966fb0d128"],
    "v20_audit_manifest": [3503, "cf276b967c8601588d75d6a152fb717f8ca95a53d8d0423925289b26333961fe"],
    "v20_audit_freeze": [2242, "5e950b2aafc603edda16eda813cc02ab2f6d635e389ab32ef150f1eb06addaf6"],
    "v20_audit_post_seal": [2584, "f2b208ac6e17990e5e846795937c11fa131705ee92dae5262e3d80835da7c483"],
    "v20_audit_complete_root_sha256": "3ded9f4e56f793ae76d9b5b499b8e227f627013b0f39dbc7a4bd997f7b46226c",
    "v20_verdict": "REJECT",
    "v20_findings_bound_without_promotion": [
        "F01_V19_CONTENT_HIDING_COMMITMENT_AND_ZERO_KNOWLEDGE_PROOF_OBLIGATIONS_DROPPED",
        "F02_RETAINED_SIGNATURE_PROOF_AND_QUORUM_BYTES_HAVE_NO_UNIQUE_CONTENT_INDEPENDENT_SELECTION_RULE",
        "F03_GLOBAL_NAMESPACE_AND_COUNTER_ZERO_GENESIS_ARE_NOT_EXTERNALLY_SINGLETON_BOUND",
    ],
}
old_epoch_key = "journal_epoch_is_fixed_by_pinned_genesis_manifest_and_context_for_all_v20_records"
old_rollover_key = "epoch_rollover_inside_v20_allowed"
doc["uint64_and_genesis_rules"].pop(old_epoch_key, None)
doc["uint64_and_genesis_rules"].pop(old_rollover_key, None)
doc["uint64_and_genesis_rules"].update({
    "journal_epoch_is_fixed_by_namespace_context_registered_genesis_for_all_v21_pre_registration_registration_reservation_and_runtime_records": True,
    "epoch_rollover_inside_v21_allowed": False,
    "v20_lineage_objects_are_historical_inputs_only_not_v21_operational_epoch_rules": True,
})

doc["canonical_encoding"].update({
    "string_escaping": "MINIMAL_JSON_ESCAPING_LOWERCASE_U_HEX_FOR_REQUIRED_ESCAPES",
    "zip_profile": "stored only; exact member order; no comments extras data descriptors alternate compression unsafe names duplicate names or trailing bytes",
})
doc["types"].update({
    "signature_domain_const": "one exact object-field signature-domain ASCII constant fixed by the closed schema; no alias or enclosing hash-domain substitution",
    "nullable_sha256": "64 lowercase hexadecimal SHA-256 or JSON null only under the exactly-once path-qualified nullable-SHA rule for this occurrence; inherited counter-zero/genesis nulls and the closed V21 SUCCESS/FAILED/pre-output/refusal branches are exhaustive and no caller-selected null exists",
    "nullable_base64": "exact canonical base64 or JSON null only under the exactly-once path-qualified field grammar; confidential SUCCESS requires the seed attestation and producer signature, deterministic SUCCESS forbids the private-seed attestation, and FAILED requires both terminal fields null",
    "output_role": "one exact field-path-specific output role listed in exact_output_role_bijection.rows and nowhere else",
    "attempt_zero": "JSON integer exactly 0",
    "terminal_outcome": "SUCCESS or FAILED under exact total one-shot terminal-outcome rule",
    "slot_state": "UNASSIGNED or ASSIGNED under exact global-registry transition rule",
    "registry_leaf_state": "exact ABSENT for the singleton-assignment transition; no caller-selected alternate leaf state",
    "reservation_slot_state": "one of UNASSIGNED RESERVED_ATTEMPT_ZERO or CONSUMED_TERMINAL under exact path transition",
    "sequence_transaction_claim_state": "one of UNCLAIMED HELD_UNTIL_SEQUENCE_COMMIT or RELEASED_BY_EXACT_SEQUENCE_COMMIT under exact acquisition/preservation/release path",
    "output_generation_mode": "one exact path-conditioned mode from path_qualified_enum_and_role_assignments; role transaction paths equal exact_output_role_bijection while the separately typed generic lifecycle-refusal proof has its one closed confidential mode and is not an uncreated boundary-role target",
})

doc["fixed_key_roles"].update({
    "global_registrar_authentication_key_role": "KIRA_MIND_V21_DISTINCT_GLOBAL_SINGLETON_REGISTRAR_AUTHENTICATOR",
    "global_registry_authentication_key_role": "KIRA_MIND_V21_DISTINCT_GLOBAL_REGISTRY_HEAD_AUTHENTICATOR",
    "generation_reservation_authentication_key_role": "KIRA_MIND_V21_ATTEMPT_ZERO_RESERVATION_AUTHENTICATOR",
    "generation_terminal_outcome_authentication_key_role": "KIRA_MIND_V21_ATTEMPT_ZERO_TERMINAL_OUTCOME_AUTHENTICATOR",
    "beacon_vrf_authentication_key_role": "KIRA_MIND_V21_PUBLIC_ROUND_BEACON_VRF_AUTHENTICATOR",
    "confidential_generator_attestation_key_role": "KIRA_MIND_V21_THRESHOLD_ISOLATED_CONFIDENTIAL_GENERATOR_ATTESTOR",
    "reservation_ledger_authority_authentication_key_role": "KIRA_MIND_V21_DISTINCT_RESERVATION_LEDGER_CAS_NO_FORK_AUTHENTICATOR",
    "generation_terminal_anchor_authentication_key_role": "KIRA_MIND_V21_DISTINCT_TERMINAL_ANCHOR_AUTHENTICATOR",
    "pre_witness_health_authentication_key_role": "KIRA_MIND_V21_DISTINCT_PRE_WITNESS_TECHNICAL_HEALTH_AUTHENTICATOR",
    "producer_availability_authentication_key_role": "KIRA_MIND_V21_DISTINCT_PRE_WITNESS_NON_ABORTABLE_PRODUCER_AVAILABILITY_AUTHENTICATOR",
    "lifecycle_refusal_authentication_key_role": "KIRA_MIND_V21_DISTINCT_HIDDEN_LIFECYCLE_REFUSAL_AUTHENTICATOR",
    "registrar_registry_beacon_and_generator_roles_are_distinct_from_all_five_runtime_roles": True,
    "all_runtime_registrar_registry_beacon_generator_reservation_outcome_ledger_terminal_anchor_health_producer_availability_roles_identities_and_public_keys_follow_exact_pairwise_distinct_closure": True,
    "role_key_profile_or_output_selection_can_depend_on_payload_scope_witness_or_erased_content": False,
})

new_domains = {
    "namespace_precommitment": "KIRA_MIND_V21_NAMESPACE_PRECOMMITMENT_SHA256_V1",
    "genesis_journal_state": "KIRA_MIND_V21_REGISTERED_GENESIS_JOURNAL_STATE_SHA256_V1",
    "genesis_external_anchor_evidence": "KIRA_MIND_V21_REGISTERED_GENESIS_EXTERNAL_ANCHOR_SHA256_V1",
    "genesis_state_authority_evidence": "KIRA_MIND_V21_REGISTERED_GENESIS_STATE_AUTHORITY_SHA256_V1",
    "genesis_manifest": "KIRA_MIND_V21_EXACT_GENESIS_MANIFEST_SHA256_V1",
    "singleton_registration_full_genesis_bundle": "KIRA_MIND_V21_SINGLETON_REGISTRATION_FULL_GENESIS_BUNDLE_SHA256_V1",
    "registrar_policy_profile_bundle": "KIRA_MIND_V21_REGISTRAR_POLICY_PROFILE_BUNDLE_SHA256_V1",
    "registrar_authority_key_identity_bundle": "KIRA_MIND_V21_REGISTRAR_AUTHORITY_KEY_IDENTITY_BUNDLE_SHA256_V1",
    "singleton_registration_pre_request_payload": "KIRA_MIND_V21_SINGLETON_REGISTRATION_PRE_REQUEST_PAYLOAD_SHA256_V1",
    "singleton_registration_assigned_value": "KIRA_MIND_V21_SINGLETON_REGISTRATION_ASSIGNED_VALUE_SHA256_V1",
    "singleton_registration_request": "KIRA_MIND_V21_SINGLETON_REGISTRATION_COMPLETED_REQUEST_SHA256_V1",
    "global_registry_sparse_map_leaf": "KIRA_MIND_V21_SINGLETON_REGISTRY_SPARSE_MAP_LEAF_SHA256_V1",
    "global_registry_sparse_map_update": "KIRA_MIND_V21_SINGLETON_REGISTRY_SPARSE_MAP_UPDATE_SHA256_V1",
    "global_registry_sparse_map_proof": "KIRA_MIND_V21_SINGLETON_REGISTRY_SPARSE_MAP_TRANSITION_PROOF_SHA256_V1",
    "global_registry_post_head": "KIRA_MIND_V21_SINGLETON_REGISTRY_POST_HEAD_SHA256_V1",
    "global_registry_post_state": "KIRA_MIND_V21_SINGLETON_REGISTRY_POST_STATE_SHA256_V1",
    "authoritative_registry_pre_state": "KIRA_MIND_V21_SINGLETON_REGISTRY_AUTHORITATIVE_PRE_STATE_SHA256_V1",
    "singleton_registration": "KIRA_MIND_V21_SINGLETON_REGISTRATION_COMPLETED_SHA256_V1",
    "generation_reservation": "KIRA_MIND_V21_ATOMIC_NEXT_SEQUENCE_GENERATION_RESERVATION_SHA256_V1",
    "generation_sequence_transaction_claim_evidence": "KIRA_MIND_V21_SEQUENCE_TRANSACTION_CLAIM_EVIDENCE_SHA256_V1",
    "generation_terminal_outcome": "KIRA_MIND_V21_MANDATORY_GENERATION_TERMINAL_OUTCOME_SHA256_V1",
    "generation_reservation_ledger_evidence": "KIRA_MIND_V21_AUTHORITATIVE_RESERVATION_LEDGER_EVIDENCE_SHA256_V1",
    "generation_terminal_anchor_evidence": "KIRA_MIND_V21_INDEPENDENT_TERMINAL_ANCHOR_EVIDENCE_SHA256_V1",
    "generation_reservation_ledger_state": "KIRA_MIND_V21_AUTHORITATIVE_RESERVATION_LEDGER_STATE_SHA256_V1",
    "public_beacon_pre_reveal_evidence": "KIRA_MIND_V21_PUBLIC_BEACON_PRE_REVEAL_HEAD_EVIDENCE_SHA256_V1",
    "beacon_reservation_order_evidence": "KIRA_MIND_V21_RESERVATION_BEFORE_BEACON_REVEAL_ORDER_EVIDENCE_SHA256_V1",
    "public_beacon_pre_reveal_state": "KIRA_MIND_V21_PUBLIC_BEACON_PRE_REVEAL_STATE_SHA256_V1",
    "public_beacon_reveal_evidence": "KIRA_MIND_V21_PUBLIC_BEACON_REVEAL_EVIDENCE_SHA256_V1",
    "pre_witness_technical_health_evidence": "KIRA_MIND_V21_PRE_WITNESS_TECHNICAL_HEALTH_EVIDENCE_SHA256_V1",
    "role_producer_availability_commitment": "KIRA_MIND_V21_ROLE_PRODUCER_AVAILABILITY_COMMITMENT_SHA256_V1",
    "role_producer_availability_evidence": "KIRA_MIND_V21_ROLE_PRODUCER_AVAILABILITY_EVIDENCE_SHA256_V1",
    "terminal_deadline_observation_evidence": "KIRA_MIND_V21_TERMINAL_DEADLINE_OBSERVATION_EVIDENCE_SHA256_V1",
    "generation_failure_record": "KIRA_MIND_V21_CANONICAL_GENERATION_FAILURE_RECORD_SHA256_V1",
    "generation_failure_journal_state": "KIRA_MIND_V21_GENERATION_FAILURE_JOURNAL_STATE_SHA256_V1",
    "generation_failure_sequence_commit_evidence": "KIRA_MIND_V21_GENERATION_FAILURE_SEQUENCE_COMMIT_EVIDENCE_SHA256_V1",
    "generation_sequence_lifecycle_refusal_evidence": "KIRA_MIND_V21_HIDDEN_LIFECYCLE_REFUSAL_EVIDENCE_SHA256_V1",
    "failure_external_anchor_current_head_observation": "KIRA_MIND_V21_FAILURE_EXTERNAL_ANCHOR_CURRENT_HEAD_OBSERVATION_SHA256_V1",
    "failure_state_authority_current_head_observation": "KIRA_MIND_V21_FAILURE_STATE_AUTHORITY_CURRENT_HEAD_OBSERVATION_SHA256_V1",
}
doc["domain_constants"].update(new_domains)
doc["exact_field_constants_v21"] = {
    "objects.singleton_registration_request.signature_domain": "KIRA_MIND_V21_SINGLETON_REGISTRATION_COMPLETED_REQUEST_SIGNATURE_V1",
    "objects.singleton_registration_request.request_nonce": 0,
    "objects.global_registry_sparse_map_update.prior_leaf_state": "ABSENT",
    "objects.global_registry_sparse_map_proof.prior_leaf_state": "ABSENT",
    "objects.global_registry_post_state.prior_leaf_state": "ABSENT",
    "objects.pinned_context.global_registry_genesis_predecessor_singleton_registration_sha256": "a9ef0b38c7c96de55fdb782760c1eaa807d06cf7f9d4011c801012b95374d0e5",
    "objects.pinned_context.global_registry_genesis_predecessor_registry_post_state_sentinel_sha256": "9a0f2ed7f4ece44d95d0c4d5dae875a45a956b2e40ebcf1208f67af91a2d2be7",
    "objects.pinned_context.global_registry_genesis_predecessor_namespace_precommitment_sha256": "0f4b6856f230bc1456f406ceee2f296e3a82472cfc36752009df49f6ab285d53",
    "objects.pinned_context.global_registry_genesis_predecessor_pinned_context_sha256": "1b50fdb9ac726131845e37008e1a4dd0353ff84ae48ec60c3d4971dcd0cb9f9f",
    "objects.pinned_context.global_registry_empty_map_root_sha256": "ec9eb96692c1477547fc66fbbeba4fccacf906946b4a01c7dbbeb8ca863a5d21",
    "objects.pinned_context.global_registry_genesis_head_sha256": "e4186b36fc8fbc6838724764d832bcb670d2d641aeadf8e95e4652e3eb663a75",
    "objects.pinned_context.global_registry_genesis_state_object_sha256": "eba033b3e9052c1e6783fadea5b7f734c824060d588ee3b4d70b5eb90f8d637a",
}
doc["authoritative_registry_pre_state_recurrence_v7"] = {
    "schema_constant": "kira.mind.continuity.v21.singleton_registry.authoritative_pre_state.v1",
    "hash_domain": "KIRA_MIND_V21_SINGLETON_REGISTRY_AUTHORITATIVE_PRE_STATE_SHA256_V1",
    "counter_zero_exact_object": {
        "predecessor_singleton_registration_sha256": "a9ef0b38c7c96de55fdb782760c1eaa807d06cf7f9d4011c801012b95374d0e5",
        "predecessor_registry_post_state_sha256": "9a0f2ed7f4ece44d95d0c4d5dae875a45a956b2e40ebcf1208f67af91a2d2be7",
        "namespace_precommitment_root_sha256": "0f4b6856f230bc1456f406ceee2f296e3a82472cfc36752009df49f6ab285d53",
        "pinned_context_root_sha256": "1b50fdb9ac726131845e37008e1a4dd0353ff84ae48ec60c3d4971dcd0cb9f9f",
        "registry_root_sha256": "ec9eb96692c1477547fc66fbbeba4fccacf906946b4a01c7dbbeb8ca863a5d21",
        "registry_counter": 0,
        "registry_head_sha256": "e4186b36fc8fbc6838724764d832bcb670d2d641aeadf8e95e4652e3eb663a75",
        "pre_state_sha256": "eba033b3e9052c1e6783fadea5b7f734c824060d588ee3b4d70b5eb90f8d637a",
    },
    "constant_derivations": [
        {"field": "predecessor_singleton_registration_sha256", "preimage": "ASCII(KIRA_MIND_V21_NO_PREDECESSOR_SINGLETON_REGISTRATION_SHA256_V1)", "sha256": "a9ef0b38c7c96de55fdb782760c1eaa807d06cf7f9d4011c801012b95374d0e5"},
        {"field": "predecessor_registry_post_state_sha256", "preimage": "ASCII(KIRA_MIND_V21_NO_PREDECESSOR_REGISTRY_POST_STATE_SHA256_V1)", "sha256": "9a0f2ed7f4ece44d95d0c4d5dae875a45a956b2e40ebcf1208f67af91a2d2be7"},
        {"field": "namespace_precommitment_root_sha256", "preimage": "ASCII(KIRA_MIND_V21_GENESIS_NAMESPACE_PRECOMMITMENT_ROOT_SHA256_V1)", "sha256": "0f4b6856f230bc1456f406ceee2f296e3a82472cfc36752009df49f6ab285d53"},
        {"field": "pinned_context_root_sha256", "preimage": "ASCII(KIRA_MIND_V21_GENESIS_PINNED_CONTEXT_ROOT_SHA256_V1)", "sha256": "1b50fdb9ac726131845e37008e1a4dd0353ff84ae48ec60c3d4971dcd0cb9f9f"},
        {"field": "registry_root_sha256", "preimage": "ASCII(KIRA_MIND_V21_SINGLETON_REGISTRY_EMPTY_ROOT_SHA256_V1)", "sha256": "ec9eb96692c1477547fc66fbbeba4fccacf906946b4a01c7dbbeb8ca863a5d21"},
        {"field": "registry_head_sha256", "preimage": "ASCII(KIRA_MIND_V21_SINGLETON_REGISTRY_GENESIS_HEAD_SHA256_V1)", "sha256": "e4186b36fc8fbc6838724764d832bcb670d2d641aeadf8e95e4652e3eb663a75"},
    ],
    "canonical_object_byte_length": 787,
    "finite_cardinality": 1,
    "positive_branch": "all ten fields are byte-identical to the exact prior completed singleton registration next authoritative pre-state; counter zero or missing prior object refuses",
}

objects = doc["objects"]
context = objects["pinned_context"]
old_genesis_pin = "replay_journal_genesis_manifest_sha256"
insert_fields(context, "journal_id_token", [("namespace_precommitment_sha256", "sha256")])

new_terminal_pins = [
    "namespace_schema_profile_sha256",
    "runtime_schema_profile_root_sha256",
    "runtime_role_key_profile_root_sha256",
    "genesis_journal_state_schema_sha256",
    "genesis_external_anchor_schema_sha256",
    "genesis_state_authority_schema_sha256",
    "genesis_manifest_schema_sha256",
    "singleton_registration_full_genesis_bundle_schema_sha256",
    "registrar_policy_profile_bundle_schema_sha256",
    "registrar_authority_key_identity_bundle_schema_sha256",
    "singleton_registration_pre_request_payload_schema_sha256",
    "singleton_registration_assigned_value_schema_sha256",
    "singleton_registration_request_schema_sha256",
    "global_registry_sparse_map_leaf_schema_sha256",
    "global_registry_sparse_map_update_schema_sha256",
    "global_registry_sparse_map_proof_schema_sha256",
    "global_registry_post_head_schema_sha256",
    "global_registry_post_state_schema_sha256",
    "authoritative_registry_pre_state_schema_sha256",
    "singleton_registration_schema_sha256",
    "global_registrar_policy_sha256",
    "global_registrar_identity_sha256",
    "global_registrar_authentication_profile_sha256",
    "global_registrar_authentication_public_key_sha256",
    "global_registry_profile_sha256",
    "global_registry_identity_sha256",
    "global_registry_authentication_profile_sha256",
    "global_registry_authentication_public_key_sha256",
    "global_registry_genesis_manifest_sha256",
    "global_registry_empty_map_root_sha256",
    "global_registry_genesis_head_sha256",
    "global_registry_genesis_state_object_sha256",
    "global_registry_genesis_predecessor_singleton_registration_sha256",
    "global_registry_genesis_predecessor_registry_post_state_sentinel_sha256",
    "global_registry_genesis_predecessor_namespace_precommitment_sha256",
    "global_registry_genesis_predecessor_pinned_context_sha256",
    "registrar_verification_key_registry_root_sha256",
    "singleton_registry_transition_profile_registry_root_sha256",
    "singleton_registry_transition_profile_root_sha256",
    "singleton_registry_proof_profile_registry_root_sha256",
    "singleton_registry_proof_profile_root_sha256",
    "generation_reservation_schema_sha256",
    "generation_sequence_transaction_claim_evidence_schema_sha256",
    "generation_terminal_outcome_schema_sha256",
    "generation_reservation_ledger_evidence_schema_sha256",
    "generation_terminal_anchor_evidence_schema_sha256",
    "generation_reservation_ledger_state_schema_sha256",
    "public_beacon_pre_reveal_evidence_schema_sha256",
    "beacon_reservation_order_evidence_schema_sha256",
    "public_beacon_pre_reveal_state_schema_sha256",
    "public_beacon_reveal_evidence_schema_sha256",
    "pre_witness_technical_health_evidence_schema_sha256",
    "role_producer_availability_commitment_schema_sha256",
    "role_producer_availability_evidence_schema_sha256",
    "terminal_deadline_observation_evidence_schema_sha256",
    "generation_failure_record_schema_sha256",
    "generation_failure_journal_state_schema_sha256",
    "generation_failure_sequence_commit_evidence_schema_sha256",
    "generation_sequence_lifecycle_refusal_evidence_schema_sha256",
    "failure_external_anchor_current_head_observation_schema_sha256",
    "failure_state_authority_current_head_observation_schema_sha256",
    "generation_reservation_profile_sha256",
    "generation_sequence_transaction_claim_profile_sha256",
    "generation_sequence_transaction_claim_output_selection_profile_sha256",
    "generation_sequence_transaction_claim_quorum_public_key_root_sha256",
    "authoritative_sequence_claim_cas_no_fork_profile_sha256",
    "generation_sequence_transaction_claim_empty_slot_key_sha256",
    "generation_sequence_transaction_claim_empty_statement_sha256",
    "generation_terminal_outcome_profile_sha256",
    "generation_reservation_authentication_public_key_sha256",
    "generation_terminal_outcome_authentication_public_key_sha256",
    "public_round_beacon_profile_sha256",
    "public_round_beacon_identity_sha256",
    "public_round_beacon_vrf_public_key_sha256",
    "public_round_beacon_vrf_proof_profile_sha256",
    "public_round_beacon_authentication_profile_sha256",
    "beacon_reservation_order_proof_profile_sha256",
    "fixed_reveal_schedule_profile_sha256",
    "public_beacon_pre_reveal_genesis_manifest_sha256",
    "public_beacon_pre_reveal_cas_no_fork_profile_sha256",
    "public_beacon_reveal_output_selection_profile_sha256",
    "terminal_deadline_observation_profile_sha256",
    "terminal_deadline_observation_output_selection_profile_sha256",
    "generation_failure_sequence_profile_sha256",
    "generation_failure_output_selection_profile_sha256",
    "generation_failure_quorum_public_key_root_sha256",
    "public_round_beacon_verifier_image_sha256",
    "confidential_generator_profile_sha256",
    "confidential_generator_image_sha256",
    "confidential_generator_identity_sha256",
    "confidential_generator_attestation_profile_sha256",
    "confidential_generator_attestation_public_key_sha256",
    "confidential_generator_verifier_image_sha256",
    "confidential_contributor_roster_sha256",
    "confidential_contributor_key_root_sha256",
    "confidential_contribution_aggregation_profile_sha256",
    "fixed_terminal_timing_envelope_profile_sha256",
    "pre_witness_health_predicate_sha256",
    "pre_witness_health_profile_sha256",
    "pre_witness_health_authority_identity_sha256",
    "pre_witness_health_authentication_profile_sha256",
    "pre_witness_health_authentication_public_key_sha256",
    "pre_witness_health_authority_verifier_image_sha256",
    "pre_witness_health_output_selection_profile_sha256",
    "pre_witness_health_measurement_attestation_profile_sha256",
    "pre_witness_health_measurement_verifier_image_sha256",
    "pre_witness_health_measurement_output_selection_profile_sha256",
    "producer_availability_predicate_sha256",
    "producer_availability_profile_sha256",
    "producer_availability_authority_identity_sha256",
    "producer_availability_authentication_profile_sha256",
    "producer_availability_authentication_public_key_sha256",
    "producer_availability_verifier_image_sha256",
    "producer_availability_output_selection_profile_sha256",
    "producer_availability_observation_profile_sha256",
    "producer_availability_result_profile_sha256",
    "producer_availability_commitment_profile_sha256",
    "complete_sequence_materialization_profile_root_sha256",
    "complete_sequence_materialization_roster_root_sha256",
    "complete_sequence_materialization_recovery_key_root_sha256",
    "generation_beacon_nonabortable_recovery_profile_sha256",
    "generation_beacon_nonabortable_recovery_key_root_sha256",
    "deadline_beacon_nonabortable_recovery_profile_sha256",
    "deadline_beacon_nonabortable_recovery_key_root_sha256",
    "public_beacon_allocation_map_profile_sha256",
    "public_beacon_allocation_empty_map_root_sha256",
    "public_beacon_counter_zero_output_sentinel_sha256",
    "post_claim_total_terminalization_profile_sha256",
    "lifecycle_refusal_relation_profile_sha256",
    "lifecycle_refusal_generator_image_sha256",
    "lifecycle_refusal_output_selection_profile_sha256",
    "lifecycle_refusal_authority_identity_sha256",
    "lifecycle_refusal_authentication_profile_sha256",
    "lifecycle_refusal_authentication_public_key_sha256",
    "lifecycle_refusal_verifier_image_sha256",
    "confidential_seed_derivation_profile_sha256",
    "deterministic_nonce_kdf_profile_sha256",
    "generation_reservation_authority_identity_sha256",
    "generation_terminal_outcome_authority_identity_sha256",
    "v19_zero_knowledge_statement_profile_sha256",
    "canonical_private_witness_encoding_profile_sha256",
    "canonical_scope_collector_witness_relation_sha256",
    "canonical_witness_verifier_image_sha256",
    "continuity_namespace_sha256",
    "stable_global_registry_slot_sha256",
    "authenticated_result_output_selection_profile_sha256",
    "scope_commitment_output_selection_profile_sha256",
    "completeness_proof_output_selection_profile_sha256",
    "commit_evidence_output_selection_profile_sha256",
    "external_anchor_output_selection_profile_sha256",
    "journal_state_output_selection_profile_sha256",
    "state_authority_output_selection_profile_sha256",
    "token_accumulator_output_selection_profile_sha256",
    "transition_request_output_selection_profile_sha256",
    "verifier_evidence_output_selection_profile_sha256",
    "genesis_journal_state_output_selection_profile_sha256",
    "genesis_external_anchor_output_selection_profile_sha256",
    "genesis_state_authority_output_selection_profile_sha256",
    "global_registry_output_selection_profile_sha256",
    "generation_reservation_output_selection_profile_sha256",
    "generation_terminal_output_selection_profile_sha256",
    "generation_reservation_ledger_output_selection_profile_sha256",
    "generation_terminal_anchor_output_selection_profile_sha256",
    "generation_reservation_ledger_genesis_manifest_sha256",
    "generation_reservation_ledger_empty_map_root_sha256",
    "reservation_ledger_authority_identity_sha256",
    "reservation_ledger_cas_no_fork_profile_sha256",
    "reservation_ledger_authority_authentication_profile_sha256",
    "reservation_ledger_authority_authentication_public_key_sha256",
    "reservation_ledger_authority_verifier_image_sha256",
    "terminal_anchor_authority_identity_sha256",
    "terminal_anchor_cas_no_fork_profile_sha256",
    "terminal_anchor_authority_authentication_profile_sha256",
    "terminal_anchor_authority_authentication_public_key_sha256",
    "terminal_anchor_authority_verifier_image_sha256",
    "public_beacon_pre_reveal_output_selection_profile_sha256",
    "beacon_reservation_order_output_selection_profile_sha256",
    "unique_output_selection_profile_sha256",
    "unique_output_validator_image_sha256",
    "trusted_outer_equality_profile_sha256",
]
insert_fields(context, "result_authentication_key_role", [("genesis_manifest_profile_sha256", "sha256")])
insert_fields(context, "result_authentication_key_role", [(name, "sha256") for name in new_terminal_pins])
insert_fields(context, "result_authentication_key_role", [
    ("registrar_key_identifier_token", "token256"),
    ("singleton_registry_transition_profile_identifier_token", "token256"),
    ("singleton_registry_proof_profile_identifier_token", "token256"),
])
insert_fields(context, "pinned_context_sha256", [
    ("global_registrar_authentication_key_role", "enum"),
    ("global_registry_authentication_key_role", "enum"),
    ("generation_reservation_authentication_key_role", "enum"),
    ("generation_terminal_outcome_authentication_key_role", "enum"),
    ("beacon_vrf_authentication_key_role", "enum"),
    ("confidential_generator_attestation_key_role", "enum"),
    ("reservation_ledger_authority_authentication_key_role", "enum"),
    ("generation_terminal_anchor_authentication_key_role", "enum"),
    ("pre_witness_health_authentication_key_role", "enum"),
    ("producer_availability_authentication_key_role", "enum"),
    ("lifecycle_refusal_authentication_key_role", "enum"),
    ("fixed_terminal_deadline_round_delta", "uint64"),
])

# All post-registration runtime objects repeat the exact final singleton root. The
# pinned context is deliberately pre-registration and therefore is the sole base
# object without this field.
markers = {
    "scope_precommitment": "precommitment_nonce",
    "proof_public_inputs": "public_inputs_root_sha256",
    "completeness_proof": "proof_bytes_base64",
    "authenticated_result": "verification_nonce",
    "verifier_evidence": "evidence_nonce",
    "receipt": "receipt_hash_sha256",
    "event": "event_nonce",
    "token_accumulator_proof": "accumulator_proof_nonce",
    "journal_state": "state_nonce",
    "transition_request": "request_nonce",
    "commit_evidence": "commit_nonce",
    "state_authority_head_evidence": "authority_nonce",
    "external_anchor_evidence": "anchor_nonce",
    "committed_envelope": "envelope_nonce",
}
for name, marker in markers.items():
    insert_fields(objects[name], marker, [("singleton_registration_sha256", "sha256")])

# Scope commitment and proof bytes bind one atomic reservation and its mandatory
# terminal outcome. Public selection output never becomes private blinding.
insert_fields(objects["scope_precommitment"], "precommitment_nonce", [
    ("generation_reservation_sha256", "sha256"),
    ("generation_reservation_ledger_evidence_sha256", "sha256"),
    ("generation_terminal_outcome_sha256", "sha256"),
    ("generation_terminal_anchor_evidence_sha256", "sha256"),
    ("scope_commitment_bytes_sha256", "sha256"),
])
objects["scope_precommitment"]["constraints"] = [
    "scope commitment uses the exact pinned independently audited randomized content-hiding and binding profile",
    "public reservation beacon round beacon output and retained transcript are selection evidence only and never the private blinding seed opening or proof witness randomness",
    "one threshold-isolated confidential attempt-zero seed requires every identity in the exact pinned contributor roster in canonical order with no subset omission failover or substitution; each secret-key contribution is the unique content-agnostic output for the fixed round and role and one canonical aggregator delivers it only inside the fixed generator boundary",
    "retained unique deterministic zero-knowledge attestation proves correct reservation attempt zero generator and output binding without exposing the private seed opening scope map or witness",
    "private seed blinding opening scope mapping content-correlatable key secret and salt are erased before COMPLETE",
    "retained commitment remains computationally hiding even given every public reservation outcome beacon registration journal authority and anchor byte",
    "deterministic digest public or retained salt HMAC Bloom filter stable tag low-entropy commitment recoverable encryption content-derived selection retry rejection sampling and selective abort refuse",
]
insert_fields(objects["completeness_proof"], "proof_bytes_base64", [
    ("v19_zero_knowledge_statement_profile_sha256", "sha256"),
    ("canonical_private_witness_encoding_profile_sha256", "sha256"),
    ("canonical_scope_collector_witness_relation_sha256", "sha256"),
    ("generation_reservation_sha256", "sha256"),
    ("generation_reservation_ledger_evidence_sha256", "sha256"),
    ("generation_terminal_outcome_sha256", "sha256"),
    ("generation_terminal_anchor_evidence_sha256", "sha256"),
    ("proof_bytes_sha256", "sha256"),
])
objects["completeness_proof"]["constraints"] = [
    "proof is one exact canonical randomized zero-knowledge or equivalently content-hiding proof under the exact pinned profile",
    "decoder consumes every byte and rejects alternate tag encoding length extension auxiliary string ignored suffix debug transcript and intermediate state",
    "proof randomness is one private attempt-zero seed inside the pinned threshold-isolated generator and never public beacon output caller entropy or retained material",
    "terminal outcome uniquely attests reservation attempt zero private-seed generation generator profile full proof output hash and mandatory seed erasure without revealing witness or seed",
    "proof exposes no witness scope map content identifier path participant time target inventory key secret salt blinding opening debug transcript or intermediate state",
    "inside the confidential boundary the exact pinned collector produces one canonical witness relation and byte encoding; the retained zero-knowledge attestation proves that canonicalization was used without retaining a witness hash or exposing a guess oracle",
    "retry rejection sampling alternate witness path selective abort missing terminal outcome and caller-selected entropy refuse",
]

# Bind the eight adjacent nonce fields to attempt-zero evidence and bind every
# retained output field to a field-specific unique deterministic profile.
choice_specs = {
    "authenticated_result": ("verification_nonce", "authentication_signature_base64", "signature_message_order"),
    "verifier_evidence": ("evidence_nonce", "evidence_signature_base64", "signature_message_order"),
    "token_accumulator_proof": ("accumulator_proof_nonce", "accumulator_proof_bytes_base64", None),
    "journal_state": ("state_nonce", "journal_state_signature_base64", None),
    "transition_request": ("request_nonce", "request_signature_base64", "signature_message_order"),
    "commit_evidence": ("commit_nonce", "commit_signature_base64", "signature_message_order"),
    "state_authority_head_evidence": ("authority_nonce", "authority_signature_base64", "signature_message_order"),
    "external_anchor_evidence": ("anchor_nonce", "anchor_authentication_proof_base64", "authentication_proof_public_input_order"),
}
unique_fields = [
    ("output_generation_mode", "enum"),
    ("output_attempt_index", "attempt_zero"),
    ("output_selection_profile_sha256", "sha256"),
    ("nonce_generation_reservation_sha256", "sha256"),
    ("nonce_generation_reservation_ledger_evidence_sha256", "sha256"),
    ("nonce_generation_terminal_outcome_sha256", "sha256"),
    ("nonce_generation_terminal_anchor_evidence_sha256", "sha256"),
]
for name, (nonce, output, message_key) in choice_specs.items():
    obj = objects[name]
    insert_fields(obj, nonce, unique_fields)
    if message_key:
        insert_message_fields(obj, nonce, [field for field, _ in unique_fields], message_key)
    if name == "token_accumulator_proof":
        insert_fields(obj, output, [("accumulator_proof_statement_root_sha256", "sha256")])
        obj["proof_public_input_order"] = [field for field in obj["field_order"] if field not in {output, "token_accumulator_proof_sha256", "accumulator_proof_statement_root_sha256"}]
    if name == "journal_state":
        obj["signature_message"] = "domain constant + actual NUL + journal_state_root_sha256; state root includes registration output mode attempt profile nonce-reservation and nonce-outcome fields"
    obj["retained_output_rule"] = "field-specific UNIQUE_DETERMINISTIC_BYTES mapping; exact attempt index zero; full-byte decoder; one valid output only; no retry rejection sampling alternate form path subset witness or selective abort"

# The complete ten-role SUCCESS barrier is created only after every role chain,
# inside the final commit evidence. Earlier target objects must not contain it:
# doing so would make their own reservations depend on a future chain hash.
for object_name, nonce_field, message_key in [
    ("commit_evidence", "commit_nonce", "signature_message_order"),
]:
    insert_fields(objects[object_name], nonce_field, [("active_generation_chain_set_root_sha256", "sha256")])
    if message_key:
        insert_message_fields(objects[object_name], nonce_field, ["active_generation_chain_set_root_sha256"], message_key)

# Existing signature/proof messages consume the added registration root.
for name, (_, _, message_key) in choice_specs.items():
    obj = objects[name]
    if message_key and "singleton_registration_sha256" not in obj[message_key]:
        marker = next(field for field in obj[message_key] if field.endswith("nonce") or field == "anchor_nonce")
        insert_message_fields(obj, marker, ["singleton_registration_sha256"], message_key)

objects.update({
    "namespace_precommitment": schema(
        "kira.mind.continuity.v21.namespace_precommitment.v1",
        new_domains["namespace_precommitment"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("continuity_namespace_sha256", "sha256"), ("stable_global_registry_slot_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("runtime_schema_profile_root_sha256", "sha256"), ("runtime_role_key_profile_root_sha256", "sha256"),
            ("global_registrar_policy_sha256", "sha256"),
            ("global_registrar_authentication_profile_sha256", "sha256"),
            ("registrar_verification_key_registry_root_sha256", "sha256"),
            ("registrar_key_identifier_token", "token256"),
            ("singleton_registry_transition_profile_registry_root_sha256", "sha256"),
            ("singleton_registry_transition_profile_identifier_token", "token256"),
            ("singleton_registry_transition_profile_root_sha256", "sha256"),
            ("singleton_registry_proof_profile_registry_root_sha256", "sha256"),
            ("singleton_registry_proof_profile_identifier_token", "token256"),
            ("singleton_registry_proof_profile_root_sha256", "sha256"),
            ("state_authority_identity_sha256", "sha256"), ("external_anchor_identity_sha256", "sha256"),
            ("global_registrar_identity_sha256", "sha256"), ("global_registry_identity_sha256", "sha256"),
            ("public_round_beacon_identity_sha256", "sha256"), ("confidential_generator_identity_sha256", "sha256"),
            ("reservation_ledger_authority_identity_sha256", "sha256"), ("terminal_anchor_authority_identity_sha256", "sha256"),
            ("generation_reservation_authority_identity_sha256", "sha256"),
            ("generation_terminal_outcome_authority_identity_sha256", "sha256"),
            ("pre_witness_health_authority_identity_sha256", "sha256"),
            ("result_authentication_public_key_sha256", "sha256"), ("verifier_evidence_authentication_public_key_sha256", "sha256"),
            ("journal_authentication_public_key_sha256", "sha256"), ("state_authority_authentication_public_key_sha256", "sha256"),
            ("external_anchor_authentication_public_key_sha256", "sha256"), ("global_registrar_authentication_public_key_sha256", "sha256"),
            ("global_registry_authentication_public_key_sha256", "sha256"), ("public_round_beacon_vrf_public_key_sha256", "sha256"),
            ("confidential_generator_attestation_public_key_sha256", "sha256"),
            ("reservation_ledger_authority_authentication_public_key_sha256", "sha256"),
            ("terminal_anchor_authority_authentication_public_key_sha256", "sha256"),
            ("generation_reservation_authentication_public_key_sha256", "sha256"),
            ("generation_terminal_outcome_authentication_public_key_sha256", "sha256"),
            ("pre_witness_health_authentication_public_key_sha256", "sha256"),
            ("result_authentication_key_role", "enum"), ("verifier_evidence_key_role", "enum"),
            ("journal_authentication_key_role", "enum"), ("state_authority_authentication_key_role", "enum"),
            ("external_anchor_authentication_key_role", "enum"), ("global_registrar_authentication_key_role", "enum"),
            ("global_registry_authentication_key_role", "enum"), ("generation_reservation_authentication_key_role", "enum"),
            ("generation_terminal_outcome_authentication_key_role", "enum"), ("beacon_vrf_authentication_key_role", "enum"),
            ("confidential_generator_attestation_key_role", "enum"),
            ("reservation_ledger_authority_authentication_key_role", "enum"),
            ("generation_terminal_anchor_authentication_key_role", "enum"),
            ("pre_witness_health_authentication_key_role", "enum"),
            ("producer_availability_authentication_key_role", "enum"),
            ("lifecycle_refusal_authentication_key_role", "enum"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("namespace_precommitment_sha256", "sha256"),
        ],
        "namespace_precommitment_sha256",
        acyclic_stage=1,
        constraints=[
            "precommitted before final pinned context registration genesis or memory event",
            "fixes one technical continuity namespace journal id epoch stable global slot all roles identities profiles and public keys",
            "no field may depend on memory payload scope witness participant path time target or erased-content predicate",
        ],
    ),
    "genesis_journal_state": schema(
        "kira.mind.continuity.v21.registered_genesis_journal_state.v1",
        new_domains["genesis_journal_state"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("committed_record_count", "uint64"), ("head_sequence", "nullable_uint64"),
            ("head_receipt_hash_sha256", "nullable_sha256"), ("head_event_hash_sha256", "nullable_sha256"),
            ("consumed_receipt_token_root_sha256", "sha256"), ("consumed_scope_token_root_sha256", "sha256"),
            ("consumed_proof_token_root_sha256", "sha256"), ("journal_authentication_key_role", "enum"),
            ("genesis_state_nonce_sha256", "sha256"), ("genesis_journal_state_root_sha256", "sha256"),
            ("output_generation_mode", "enum"), ("output_attempt_index", "attempt_zero"),
            ("output_selection_profile_sha256", "sha256"),
            ("genesis_journal_state_signature_base64", "base64"), ("genesis_journal_state_object_sha256", "sha256"),
        ],
        "genesis_journal_state_object_sha256",
        acyclic_stage=3,
        state_root_preimage="all fields through genesis_state_nonce_sha256",
        signature_message="unique deterministic signature over domain NUL genesis_journal_state_root_sha256",
        constraints=["count exactly zero; all heads exactly null; accumulator roots exact pinned empty roots", "genesis nonce is the unique deterministic content-independent derivation from namespace context and GENESIS_STATE_NONCE role", "no singleton registration root appears because this is the pre-registration typed genesis object"],
    ),
    "genesis_external_anchor_evidence": schema(
        "kira.mind.continuity.v21.registered_genesis_external_anchor_evidence.v1",
        new_domains["genesis_external_anchor_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("anchor_monotonic_counter", "uint64"), ("prior_external_anchor_root_sha256", "nullable_sha256"),
            ("state_authority_monotonic_counter", "uint64"),
            ("genesis_journal_state_root_sha256", "sha256"), ("genesis_journal_state_object_sha256", "sha256"),
            ("committed_record_count", "uint64"), ("head_sequence", "nullable_uint64"),
            ("head_receipt_hash_sha256", "nullable_sha256"), ("head_event_hash_sha256", "nullable_sha256"),
            ("external_anchor_identity_sha256", "sha256"), ("external_anchor_profile_sha256", "sha256"),
            ("external_anchor_authentication_key_role", "enum"), ("output_generation_mode", "enum"),
            ("output_attempt_index", "attempt_zero"), ("output_selection_profile_sha256", "sha256"),
            ("genesis_anchor_authentication_proof_base64", "base64"), ("genesis_external_anchor_root_sha256", "sha256"),
        ],
        "genesis_external_anchor_root_sha256",
        acyclic_stage=4,
        retained_output_rule="UNIQUE_DETERMINISTIC_BYTES over every prior field; one fixed quorum member order and canonical path",
        constraints=["counter exactly zero; prior exactly null; count zero and heads null", "consumes exact genesis journal state and cannot contain final registration root"],
    ),
    "genesis_state_authority_evidence": schema(
        "kira.mind.continuity.v21.registered_genesis_state_authority_evidence.v1",
        new_domains["genesis_state_authority_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("authority_monotonic_counter", "uint64"), ("prior_state_authority_head_evidence_sha256", "nullable_sha256"),
            ("prior_external_anchor_root_sha256", "nullable_sha256"),
            ("genesis_journal_state_root_sha256", "sha256"), ("genesis_journal_state_object_sha256", "sha256"),
            ("genesis_external_anchor_root_sha256", "sha256"), ("committed_record_count", "uint64"),
            ("head_sequence", "nullable_uint64"), ("head_receipt_hash_sha256", "nullable_sha256"),
            ("head_event_hash_sha256", "nullable_sha256"), ("state_authority_identity_sha256", "sha256"),
            ("state_authority_authentication_key_role", "enum"), ("output_generation_mode", "enum"),
            ("output_attempt_index", "attempt_zero"), ("output_selection_profile_sha256", "sha256"),
            ("genesis_authority_signature_base64", "base64"), ("genesis_state_authority_head_evidence_sha256", "sha256"),
        ],
        "genesis_state_authority_head_evidence_sha256",
        acyclic_stage=5,
        retained_output_rule="UNIQUE_DETERMINISTIC_BYTES over every prior field under exact fixed authority role profile and key",
        constraints=["counter exactly zero; prior exactly null; count zero and heads null", "consumes exact genesis state and genesis anchor and cannot contain final registration root"],
    ),
    "genesis_manifest": schema(
        "kira.mind.continuity.v21.exact_genesis_manifest.v1",
        new_domains["genesis_manifest"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("committed_record_count", "uint64"), ("head_sequence", "nullable_uint64"),
            ("head_receipt_hash_sha256", "nullable_sha256"), ("head_event_hash_sha256", "nullable_sha256"),
            ("empty_receipt_token_root_sha256", "sha256"), ("empty_scope_token_root_sha256", "sha256"),
            ("empty_proof_token_root_sha256", "sha256"), ("genesis_journal_state_root_sha256", "sha256"),
            ("genesis_journal_state_object_sha256", "sha256"), ("genesis_external_anchor_root_sha256", "sha256"),
            ("genesis_state_authority_head_evidence_sha256", "sha256"), ("stable_global_registry_slot_sha256", "sha256"),
            ("state_authority_monotonic_counter", "uint64"), ("anchor_monotonic_counter", "uint64"),
            ("prior_state_authority_head_evidence_sha256", "nullable_sha256"),
            ("prior_external_anchor_root_sha256", "nullable_sha256"),
            ("genesis_manifest_sha256", "sha256"),
        ],
        "genesis_manifest_sha256",
        acyclic_stage=6,
        constraints=["byte-available exact preimage closes namespace context count-zero state empty roots null heads authority zero and anchor zero", "any second state nonce root manifest preimage authority anchor namespace context journal id or epoch is a different unregistered manifest and refuses"],
    ),
    "singleton_registration_full_genesis_bundle": schema(
        "kira.mind.continuity.v21.singleton_registration.full_genesis_bundle.v1",
        new_domains["singleton_registration_full_genesis_bundle"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("genesis_manifest_sha256", "sha256"),
            ("genesis_journal_state_root_sha256", "sha256"),
            ("genesis_journal_state_object_sha256", "sha256"),
            ("genesis_external_anchor_root_sha256", "sha256"),
            ("genesis_state_authority_head_evidence_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
        ],
        "full_genesis_bundle_root_sha256",
        acyclic_stage=7,
        constraints=["exact closed projection of the registered counter-zero genesis manifest state object anchor and authority bundle", "contains no request signature request hash sparse-map leaf update proof post root post head post state or final registration"],
    ),
    "registrar_policy_profile_bundle": schema(
        "kira.mind.continuity.v21.registrar_policy_profile_bundle.v1",
        new_domains["registrar_policy_profile_bundle"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("global_registrar_policy_sha256", "sha256"),
            ("global_registrar_authentication_profile_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
        ],
        "registrar_policy_profile_bundle_sha256",
        acyclic_stage=7,
        constraints=["all component roots identifiers and unique authenticated registry resolutions are fixed by namespace and context", "no request assigned value leaf update proof post or runtime output is reachable from this pre-request bundle"],
    ),
    "registrar_authority_key_identity_bundle": schema(
        "kira.mind.continuity.v21.registrar_authority_key_identity_bundle.v1",
        new_domains["registrar_authority_key_identity_bundle"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("global_registrar_identity_sha256", "sha256"),
            ("registrar_verification_key_registry_root_sha256", "sha256"),
            ("registrar_key_identifier_token", "token256"),
            ("global_registrar_authentication_public_key_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
        ],
        "registrar_authority_key_identity_bundle_sha256",
        acyclic_stage=7,
        constraints=["the authenticated key registry has exactly one canonical registrar identifier match and the resolved verification-key bytes hash to the pinned public-key hash", "local rekey alias fallback duplicate match request-selected key and every later-output dependency refuse"],
    ),
    "singleton_registration_pre_request_payload": schema(
        "kira.mind.continuity.v21.singleton_registration.pre_request_payload.v1",
        new_domains["singleton_registration_pre_request_payload"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
        ],
        "pre_request_registration_payload_root_sha256",
        acyclic_stage=8,
        constraints=["acyclic exact payload over only authoritative pre-request values", "request signature request hash assigned value prior or post registry roots counters leaf update proof head state and final registration are absent recursively"],
    ),
    "singleton_registration_assigned_value": schema(
        "kira.mind.continuity.v21.singleton_registration.assigned_value.v1",
        new_domains["singleton_registration_assigned_value"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("assigned_value_root_sha256", "sha256"),
        ],
        "assigned_value_root_sha256",
        acyclic_stage=9,
        constraints=["one exact assigned value is derived before request signing and is the literal sparse-map leaf value", "no request leaf update proof post or final output is in its recursive preimage"],
    ),
    "singleton_registration_request": schema(
        "kira.mind.continuity.v21.singleton_registration.completed_request.v1",
        new_domains["singleton_registration_request"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("signature_domain", "signature_domain_const"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
            ("assigned_value_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("request_nonce", "uint64"),
            ("request_authentication_signature_base64", "base64"),
            ("singleton_registration_request_sha256", "sha256"),
        ],
        "singleton_registration_request_sha256",
        acyclic_stage=10,
        retained_output_rule="one unique registrar signature over every preceding field under the namespace/context resolved registrar profile and key",
        constraints=["completed signed request contains no registry prior/post root object counter leaf update proof post head post state or final registration", "request has no caller nonce timing path quorum subset optional data or post-state dependency"],
    ),
    "global_registry_sparse_map_leaf": schema(
        "kira.mind.continuity.v21.singleton_registry.sparse_map_leaf.v1",
        new_domains["global_registry_sparse_map_leaf"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("assigned_value_root_sha256", "sha256"),
            ("singleton_registration_request_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("global_registry_sparse_map_leaf_sha256", "sha256"),
        ],
        "global_registry_sparse_map_leaf_sha256",
        acyclic_stage=11,
        constraints=["leaf key is the exact namespace-derived stable slot and leaf value is the exact assigned value signed by the completed request", "all ten metadata fields and completed request hash propagate literally; alternate payload key or request refuses"],
    ),
    "global_registry_sparse_map_update": schema(
        "kira.mind.continuity.v21.singleton_registry.sparse_map_update.v1",
        new_domains["global_registry_sparse_map_update"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("registry_pre_root_sha256", "sha256"), ("registry_post_root_sha256", "sha256"),
            ("registry_counter_before", "uint64"), ("registry_counter_after", "uint64"),
            ("prior_leaf_state", "registry_leaf_state"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("assigned_value_root_sha256", "sha256"),
            ("singleton_registration_request_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("global_registry_sparse_map_leaf_sha256", "sha256"),
            ("singleton_registry_transition_profile_root_sha256", "sha256"),
            ("global_registry_sparse_map_update_sha256", "sha256"),
        ],
        "global_registry_sparse_map_update_sha256",
        acyclic_stage=12,
        constraints=["canonical authenticated sparse-map update changes exactly the derived slot ABSENT to the exact typed leaf and increments the independently current registry counter exactly once", "transition profile is uniquely resolved from namespace/context registry root plus identifier; caller or request cannot select it"],
    ),
    "global_registry_sparse_map_proof": schema(
        "kira.mind.continuity.v21.singleton_registry.sparse_map_transition_proof.v1",
        new_domains["global_registry_sparse_map_proof"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("registry_pre_root_sha256", "sha256"), ("registry_post_root_sha256", "sha256"),
            ("registry_counter_before", "uint64"), ("registry_counter_after", "uint64"),
            ("prior_leaf_state", "registry_leaf_state"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("assigned_value_root_sha256", "sha256"),
            ("singleton_registration_request_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("global_registry_sparse_map_leaf_sha256", "sha256"),
            ("global_registry_sparse_map_update_sha256", "sha256"),
            ("singleton_registry_proof_profile_root_sha256", "sha256"),
            ("transition_proof_base64", "base64"),
            ("global_registry_sparse_map_proof_sha256", "sha256"),
        ],
        "global_registry_sparse_map_proof_sha256",
        acyclic_stage=13,
        retained_output_rule="one canonical full-byte proof over the exact typed leaf/update statement under the namespace/context resolved proof profile",
        constraints=["proof consumes every byte and verifies the exact pre-root post-root checked counter and ABSENT-to-assigned leaf transition", "all ten metadata values assigned value request hash leaf hash and update hash are literal public inputs"],
    ),
    "global_registry_post_head": schema(
        "kira.mind.continuity.v21.singleton_registry.post_head.v1",
        new_domains["global_registry_post_head"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("previous_head_sha256", "sha256"),
            ("registry_post_root_sha256", "sha256"), ("registry_counter_after", "uint64"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("assigned_value_root_sha256", "sha256"),
            ("singleton_registration_request_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("global_registry_sparse_map_leaf_sha256", "sha256"),
            ("global_registry_sparse_map_update_sha256", "sha256"),
            ("global_registry_sparse_map_proof_sha256", "sha256"),
            ("global_registry_post_head_sha256", "sha256"),
        ],
        "global_registry_post_head_sha256",
        acyclic_stage=14,
        constraints=["exactly one authoritative typed post head hashes the completed request leaf update proof post root and checked counter; no embedded alternate or parallel head is accepted", "positive recursion consumes the exact prior signed head and counter-zero consumes the exact pinned genesis head"],
    ),
    "global_registry_post_state": schema(
        "kira.mind.continuity.v21.singleton_registry.post_state.v1",
        new_domains["global_registry_post_state"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("previous_head_sha256", "sha256"),
            ("registry_pre_root_sha256", "sha256"), ("registry_post_root_sha256", "sha256"),
            ("registry_counter_before", "uint64"), ("registry_counter_after", "uint64"),
            ("prior_leaf_state", "registry_leaf_state"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("assigned_value_root_sha256", "sha256"),
            ("singleton_registration_request_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("singleton_registry_transition_profile_root_sha256", "sha256"),
            ("singleton_registry_proof_profile_root_sha256", "sha256"),
            ("global_registry_sparse_map_leaf_sha256", "sha256"),
            ("global_registry_sparse_map_update_sha256", "sha256"),
            ("global_registry_sparse_map_proof_sha256", "sha256"),
            ("global_registry_post_head_sha256", "sha256"),
            ("global_registry_post_state_sha256", "sha256"),
        ],
        "global_registry_post_state_sha256",
        acyclic_stage=15,
        constraints=["closed typed post-state repeats the exact prior/post map roots counters absence proof metadata profiles leaf update proof and one signed post head", "it is an authenticated state-transition envelope rather than a second selectable map root"],
    ),
    "authoritative_registry_pre_state": schema(
        "kira.mind.continuity.v21.singleton_registry.authoritative_pre_state.v1",
        new_domains["authoritative_registry_pre_state"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("predecessor_singleton_registration_sha256", "sha256"),
            ("predecessor_registry_post_state_sha256", "sha256"),
            ("namespace_precommitment_root_sha256", "sha256"),
            ("pinned_context_root_sha256", "sha256"),
            ("registry_root_sha256", "sha256"),
            ("registry_counter", "uint64"),
            ("registry_head_sha256", "sha256"),
            ("pre_state_sha256", "sha256"),
        ],
        "pre_state_sha256",
        acyclic_stage=17,
        constraints=["exact V6 authoritative next-consumer oracle: predecessor registration and post state plus namespace context registry root counter and head are one closed typed pre-state", "counter zero is the unique pinned genesis sentinel tuple; positive counters resolve the exact preceding completed singleton registration post state and post head; no caller-selected sibling or reconstructed local head"],
    ),
    "singleton_registration": schema(
        "kira.mind.continuity.v21.singleton_registration.completed.v1",
        new_domains["singleton_registration"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("stable_global_registry_slot_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("full_genesis_bundle_root_sha256", "sha256"),
            ("pre_request_registration_payload_root_sha256", "sha256"),
            ("assigned_value_root_sha256", "sha256"),
            ("registrar_policy_profile_bundle_sha256", "sha256"),
            ("registrar_authority_key_identity_bundle_sha256", "sha256"),
            ("singleton_registration_request_sha256", "sha256"),
            ("post_global_registry_state_root_sha256", "sha256"),
            ("post_registry_counter", "uint64"),
            ("singleton_registry_transition_profile_root_sha256", "sha256"),
            ("singleton_registry_proof_profile_root_sha256", "sha256"),
            ("global_registry_sparse_map_leaf_sha256", "sha256"),
            ("global_registry_sparse_map_update_sha256", "sha256"),
            ("global_registry_sparse_map_proof_sha256", "sha256"),
            ("global_registry_post_head_sha256", "sha256"),
            ("global_registry_post_state_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"),
        ],
        "singleton_registration_sha256",
        acyclic_stage=17,
        constraints=["final immutable bridge authenticates exactly one context and complete typed counter-zero genesis", "trusted outer equality pin commits this final root", "second registration context genesis state nonce journal id epoch or registrar head refuses"],
    ),
    "generation_sequence_transaction_claim_evidence": schema(
        "kira.mind.continuity.v21.sequence_transaction_claim_evidence.v1",
        new_domains["generation_sequence_transaction_claim_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"),
            ("authoritative_pre_journal_state_root_sha256", "sha256"),
            ("authoritative_pre_journal_state_object_sha256", "sha256"),
            ("authoritative_pre_state_kind", "enum"),
            ("authoritative_pre_record_count", "uint64"),
            ("authoritative_pre_head_sequence", "nullable_uint64"),
            ("authoritative_pre_head_receipt_hash_sha256", "nullable_sha256"),
            ("authoritative_pre_head_event_hash_sha256", "nullable_sha256"),
            ("pre_state_authority_head_evidence_sha256", "sha256"),
            ("pre_state_authority_counter", "uint64"),
            ("pre_external_anchor_root_sha256", "sha256"),
            ("pre_external_anchor_counter", "uint64"),
            ("reserved_next_sequence", "uint64"),
            ("fixed_role_lifecycle_order_root_sha256", "sha256"),
            ("sequence_transaction_claim_slot_key_sha256", "sha256"),
            ("sequence_transaction_claim_statement_sha256", "sha256"),
            ("prior_reservation_ledger_head_evidence_sha256", "nullable_sha256"),
            ("pre_reservation_ledger_state_root_sha256", "sha256"),
            ("pre_reservation_ledger_state_object_sha256", "sha256"),
            ("pre_reservation_ledger_counter", "uint64"),
            ("post_reservation_ledger_state_root_sha256", "sha256"),
            ("post_reservation_ledger_state_object_sha256", "sha256"),
            ("post_reservation_ledger_counter", "uint64"),
            ("pre_sequence_transaction_claim_state", "sequence_transaction_claim_state"),
            ("post_sequence_transaction_claim_state", "sequence_transaction_claim_state"),
            ("sequence_claim_cas_result", "enum"), ("sequence_claim_no_fork_result", "enum"),
            ("authoritative_journal_store_identity_sha256", "sha256"),
            ("reservation_ledger_authority_identity_sha256", "sha256"),
            ("authoritative_sequence_claim_cas_no_fork_profile_sha256", "sha256"),
            ("journal_authentication_key_role", "enum"),
            ("reservation_ledger_authority_authentication_key_role", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"),
            ("output_selection_profile_sha256", "sha256"),
            ("sequence_transaction_claim_authentication_proof_base64", "base64"),
            ("generation_sequence_transaction_claim_evidence_sha256", "sha256"),
        ],
        "generation_sequence_transaction_claim_evidence_sha256",
        retained_output_rule="one fixed two-authority journal-store plus reservation-ledger quorum proof authenticates the exact sequence-wide claim CAS before any role-specific beacon allocation or reservation",
        constraints=["claim slot key is the exact domain hash of singleton registration epoch and checked next sequence; the statement additionally binds the exact current journal root object kind count heads authority/anchor and the fixed ten-role lifecycle order", "the independently current reservation-ledger state changes the sequence claim from UNCLAIMED or prior RELEASED to HELD_UNTIL_SEQUENCE_COMMIT and increments its counter exactly once", "the authoritative journal store and ledger authority jointly authenticate that every unrelated journal CAS is refused while HELD; role-slot consumption never releases this claim", "exactly one final normal commit after all ten SUCCESS anchors or one canonical pre-output technical-failure role-terminal-failure or hidden-refusal commit atomically advances the journal and changes this exact claim to RELEASED; no gap exists before either CAS", "restored sibling second claim alternate pre-root dummy record retry early release and caller-selected claim are invalid"],
    ),
    "generation_reservation": schema(
        "kira.mind.continuity.v21.atomic_next_sequence_generation_reservation.v1",
        new_domains["generation_reservation"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("authoritative_pre_journal_state_root_sha256", "sha256"),
            ("authoritative_pre_journal_state_object_sha256", "sha256"),
            ("authoritative_pre_state_kind", "enum"),
            ("authoritative_pre_record_count", "uint64"), ("authoritative_pre_head_sequence", "nullable_uint64"),
            ("reserved_next_sequence", "uint64"), ("output_role", "output_role"),
            ("message_or_statement_root_sha256", "sha256"), ("generator_profile_sha256", "sha256"),
            ("public_beacon_pre_reveal_evidence_sha256", "sha256"),
            ("beacon_allocation_slot_key_sha256", "sha256"),
            ("public_beacon_output_recovery_commitment_sha256", "sha256"),
            ("public_beacon_pre_reveal_head_counter", "uint64"),
            ("public_round_index", "uint64"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("fixed_terminal_deadline_round_index", "uint64"),
            ("deadline_beacon_output_recovery_commitment_sha256", "sha256"),
            ("pre_witness_health_predicate_sha256", "sha256"),
            ("pre_witness_health_profile_sha256", "sha256"),
            ("generation_reservation_authority_identity_sha256", "sha256"),
            ("attempt_index", "attempt_zero"),
            ("reservation_slot_key_sha256", "sha256"),
            ("expected_pre_reservation_ledger_head_evidence_sha256", "nullable_sha256"),
            ("expected_pre_reservation_ledger_state_root_sha256", "sha256"),
            ("expected_pre_reservation_ledger_state_object_sha256", "sha256"),
            ("expected_pre_reservation_ledger_counter", "uint64"),
            ("generation_reservation_authentication_key_role", "enum"),
            ("output_generation_mode", "enum"), ("output_selection_profile_sha256", "sha256"),
            ("reservation_authentication_signature_base64", "base64"), ("generation_reservation_sha256", "sha256"),
        ],
        "generation_reservation_sha256",
        acyclic_stage=10,
        retained_output_rule="reservation signature is UNIQUE_DETERMINISTIC_BYTES over every prior field",
        constraints=["atomic CAS reserves exactly checked pre head plus one before public round reveal", "public_round_index equals the exact role-qualified pre-reveal post-state allocation: checked predecessor committed_future_round_index plus one; the independently current beacon allocation head, not a caller or hash-to-absolute-round choice, fixes it", "the fixed demand-driven schedule allocates no round except through this authenticated pre-reveal CAS, so each role receives the strictly next unused future unrevealed round; namespace epoch sequence and role bind the reservation and order proof but cannot choose the absolute round", "no caller round time quorum path entropy retry interleaving dummy record or alternative sequence", "one active reservation per namespace epoch sequence role and it remains subordinate to the sequence transaction claim until final normal or failure commit"],
    ),
    "generation_terminal_outcome": schema(
        "kira.mind.continuity.v21.mandatory_generation_terminal_outcome.v1",
        new_domains["generation_terminal_outcome"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("generation_reservation_sha256", "sha256"),
            ("generation_reservation_ledger_evidence_sha256", "sha256"),
            ("public_beacon_pre_reveal_evidence_sha256", "sha256"),
            ("beacon_reservation_order_evidence_sha256", "sha256"),
            ("public_beacon_output_recovery_commitment_sha256", "sha256"),
            ("public_beacon_reveal_evidence_sha256", "sha256"),
            ("pre_witness_technical_health_evidence_sha256", "sha256"),
            ("terminal_deadline_observation_evidence_sha256", "sha256"),
            ("namespace_precommitment_sha256", "sha256"),
            ("pinned_context_sha256", "sha256"), ("singleton_registration_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("reserved_sequence", "uint64"), ("output_role", "output_role"),
            ("message_or_statement_root_sha256", "sha256"),
            ("output_generation_mode", "enum"), ("output_selection_profile_sha256", "sha256"),
            ("attempt_index", "attempt_zero"), ("reservation_slot_key_sha256", "sha256"),
            ("public_round_index", "uint64"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("fixed_terminal_deadline_round_index", "uint64"),
            ("deadline_beacon_output_recovery_commitment_sha256", "sha256"),
            ("public_beacon_output_sha256", "sha256"),
            ("beacon_vrf_authentication_key_role", "enum"),
            ("confidential_generator_identity_sha256", "sha256"), ("confidential_generator_attestation_key_role", "enum"),
            ("confidential_contributor_roster_sha256", "sha256"), ("confidential_contributor_key_root_sha256", "sha256"),
            ("confidential_contribution_aggregation_profile_sha256", "sha256"),
            ("confidential_seed_derivation_profile_sha256", "sha256"),
            ("confidential_seed_derivation_statement_root_sha256", "nullable_sha256"),
            ("private_seed_zero_knowledge_attestation_base64", "nullable_base64"), ("terminal_outcome", "terminal_outcome"),
            ("generated_output_sha256", "nullable_sha256"), ("failure_code", "enum"),
            ("producer_availability_result", "enum"),
            ("technical_health_result", "enum"),
            ("reservation_slot_consumed", "enum"),
            ("generation_terminal_outcome_authority_identity_sha256", "sha256"),
            ("generation_terminal_outcome_authentication_key_role", "enum"),
            ("terminal_outcome_authentication_signature_base64", "nullable_base64"), ("generation_terminal_outcome_sha256", "sha256"),
        ],
        "generation_terminal_outcome_sha256",
        acyclic_stage=12,
        retained_output_rule="the linked typed public_beacon_reveal_evidence is the sole retained VRF proof; private-seed zero-knowledge attestation and terminal signature are each field-specific UNIQUE_DETERMINISTIC_BYTES with full-byte output binding",
        constraints=["exactly one terminal outcome exists for every created reservation at the fixed deadline; its branch is the exact pre-output plan projection for this role and cannot be selected after allocation or reveal", "MATERIALIZE_SUCCESS maps to READY and SUCCESS with one nonnull full output hash fixed NONE failure code and every branch-required signature byte; the complete-sequence materializer or committed public recovery path makes caller, nominal-producer, signer, anchor, or beacon silence unable to suppress them", "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING plus SUCCESS requires one nonnull confidential-seed derivation statement and one nonnull seed/erasure ZK attestation; UNIQUE_DETERMINISTIC_BYTES plus SUCCESS requires both fields exact JSON null because the verifier-recomputed public nonce KDF uses no private seed or witness", "the unique first FIXED_ROLE_TECHNICAL_FAILURE plan maps to FIXED_TECHNICAL_FAILURE and FAILED with null output hash, null confidential-seed statement, the one canonical technical failure code, exact null private-seed attestation and exact null producer signature; only distinct terminal-anchor evidence authenticates that branch", "a sequence-wide PRE_OUTPUT_FIXED_TECHNICAL_FAILURE creates no reservation or terminal outcome, and a hidden lifecycle refusal at the next boundary creates no reservation or terminal outcome for that boundary", "post-READY silence absence timeout or producer choice never maps to FAILED; the fixed isolated non-abortable materializer completes the exact planned SUCCESS", "distinct terminal-anchor evidence is mandatory and independently authenticates every created role outcome", "all ten role plans are verifier-derived from the content-independent measured input vector and committed before any role allocation, witness admission, public output, or content-bearing computation; the first fixed technical-failure plan is unique and no later role is created", "attempt zero is consumed on every created SUCCESS or FAILED role and no retry can become a record", "public beacon output is never private seed blinding opening or witness randomness", "for the two confidential target roles only, private contribution and seed derivation consume the complete exact namespace context registration epoch sequence role attempt-zero round reservation-message and canonical contributor tuple; all contributions and seed remain inside the threshold-isolated generator and are erased", "the confidential SUCCESS attestation proves the exact domain-separated attempt-zero derivation fixed full roster order aggregation canonical witness relation and erasure without revealing contributions or seed, and the formal profile preserves hiding given the full public transcript", "technical failure controls record integrity acceptance only and never Kira speech or memory choice"],
    ),
    "generation_reservation_ledger_state": schema(
        "kira.mind.continuity.v21.authoritative_reservation_ledger_state.v1",
        new_domains["generation_reservation_ledger_state"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"),
            ("reservation_ledger_authority_identity_sha256", "sha256"),
            ("reservation_ledger_cas_no_fork_profile_sha256", "sha256"),
            ("reservation_ledger_counter", "uint64"), ("reservation_ledger_map_root_sha256", "sha256"),
            ("active_sequence_transaction_claim_slot_key_sha256", "sha256"),
            ("active_sequence_transaction_claim_statement_sha256", "sha256"),
            ("sequence_transaction_claim_state", "sequence_transaction_claim_state"),
            ("generation_reservation_ledger_genesis_manifest_sha256", "sha256"),
            ("generation_reservation_ledger_state_root_sha256", "sha256"),
            ("generation_reservation_ledger_state_object_sha256", "sha256"),
        ],
        "generation_reservation_ledger_state_object_sha256",
        acyclic_stage=11,
        state_root_preimage="all fields through generation_reservation_ledger_genesis_manifest_sha256",
        constraints=["counter zero requires exact registered namespace context singleton registration genesis manifest exact empty map root exact empty sequence-claim slot/statement sentinels and UNCLAIMED", "counter greater than zero map root is exact canonical role-slot plus sequence-claim map after recursively authenticated one-step transitions", "sequence claim acquisition changes UNCLAIMED or the prior sequence RELEASED state to HELD_UNTIL_SEQUENCE_COMMIT; every role reservation and terminal transition preserves the exact active claim slot statement and HELD state; only the atomic final normal or canonical failure journal commit changes it to RELEASED_BY_EXACT_SEQUENCE_COMMIT", "no locally rebuilt substitute ledger state alternate genesis premature release or journal CAS outside the held claim is compatible"],
    ),
    "generation_reservation_ledger_evidence": schema(
        "kira.mind.continuity.v21.authoritative_reservation_ledger_evidence.v1",
        new_domains["generation_reservation_ledger_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("generation_reservation_sha256", "sha256"), ("reservation_slot_key_sha256", "sha256"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("reserved_sequence", "uint64"),
            ("output_role", "output_role"), ("output_generation_mode", "enum"),
            ("attempt_index", "attempt_zero"),
            ("public_beacon_pre_reveal_evidence_sha256", "sha256"),
            ("beacon_allocation_slot_key_sha256", "sha256"),
            ("public_beacon_output_recovery_commitment_sha256", "sha256"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("fixed_terminal_deadline_round_index", "uint64"),
            ("deadline_beacon_output_recovery_commitment_sha256", "sha256"),
            ("pre_witness_health_predicate_sha256", "sha256"),
            ("pre_witness_health_profile_sha256", "sha256"),
            ("prior_reservation_ledger_head_evidence_sha256", "nullable_sha256"),
            ("pre_reservation_ledger_state_root_sha256", "sha256"),
            ("post_reservation_ledger_state_root_sha256", "sha256"),
            ("pre_reservation_ledger_state_object_sha256", "sha256"),
            ("post_reservation_ledger_state_object_sha256", "sha256"),
            ("pre_reservation_ledger_counter", "uint64"), ("post_reservation_ledger_counter", "uint64"),
            ("pre_slot_state", "reservation_slot_state"), ("post_slot_state", "reservation_slot_state"),
            ("reservation_cas_result", "enum"), ("reservation_no_fork_result", "enum"),
            ("reservation_ledger_authority_identity_sha256", "sha256"),
            ("reservation_ledger_cas_no_fork_profile_sha256", "sha256"),
            ("reservation_ledger_anchor_statement_sha256", "sha256"),
            ("reservation_ledger_authority_authentication_key_role", "enum"),
            ("output_generation_mode_for_evidence", "output_generation_mode"), ("output_selection_profile_sha256", "sha256"),
            ("reservation_ledger_authentication_signature_base64", "base64"),
            ("generation_reservation_ledger_evidence_sha256", "sha256"),
        ],
        "generation_reservation_ledger_evidence_sha256",
        acyclic_stage=11,
        retained_output_rule="reservation-ledger signature is field-specific UNIQUE_DETERMINISTIC_BYTES over the exact full transition",
        constraints=["slot key is exact SHA256 of domain NUL singleton registration NUL epoch-u64be NUL reserved-sequence-u64be NUL output-role", "distinct reservation-ledger authority atomically changes its independently current exact state from UNASSIGNED to RESERVED_ATTEMPT_ZERO and increments counter by one", "anchor statement hashes the exact slot reservation pre/post state roots objects counters and CAS/no-fork results and is signed only by the distinct ledger authority role/key", "verifier queries that authority current head and requires it equal this evidence hash; one pre-root has one post-root; restored clone stale sibling retry local request key fork and alternate role refuse", "prior evidence is byte-available and recursively validated"],
    ),
    "generation_terminal_anchor_evidence": schema(
        "kira.mind.continuity.v21.independent_terminal_anchor_evidence.v1",
        new_domains["generation_terminal_anchor_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("generation_reservation_sha256", "sha256"),
            ("generation_reservation_ledger_evidence_sha256", "sha256"),
            ("generation_terminal_outcome_sha256", "sha256"), ("reservation_slot_key_sha256", "sha256"),
            ("public_beacon_reveal_evidence_sha256", "sha256"),
            ("pre_witness_technical_health_evidence_sha256", "sha256"),
            ("terminal_deadline_observation_evidence_sha256", "sha256"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("reserved_sequence", "uint64"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("fixed_terminal_deadline_round_index", "uint64"),
            ("public_beacon_output_recovery_commitment_sha256", "sha256"),
            ("deadline_beacon_output_recovery_commitment_sha256", "sha256"),
            ("output_role", "output_role"), ("output_generation_mode", "enum"),
            ("attempt_index", "attempt_zero"),
            ("prior_reservation_ledger_head_evidence_sha256", "sha256"),
            ("pre_reservation_ledger_state_root_sha256", "sha256"),
            ("post_reservation_ledger_state_root_sha256", "sha256"),
            ("pre_reservation_ledger_state_object_sha256", "sha256"),
            ("post_reservation_ledger_state_object_sha256", "sha256"),
            ("pre_reservation_ledger_counter", "uint64"), ("post_reservation_ledger_counter", "uint64"),
            ("pre_slot_state", "reservation_slot_state"), ("post_slot_state", "reservation_slot_state"),
            ("terminal_outcome", "terminal_outcome"), ("generated_output_sha256", "nullable_sha256"),
            ("producer_availability_result", "enum"),
            ("technical_health_result", "enum"),
            ("fixed_terminal_timing_envelope_profile_sha256", "sha256"),
            ("terminal_cas_result", "enum"), ("terminal_no_fork_result", "enum"),
            ("terminal_anchor_authority_identity_sha256", "sha256"),
            ("terminal_anchor_cas_no_fork_profile_sha256", "sha256"),
            ("terminal_anchor_statement_sha256", "sha256"),
            ("generation_terminal_anchor_authentication_key_role", "enum"),
            ("output_generation_mode_for_evidence", "output_generation_mode"), ("output_selection_profile_sha256", "sha256"),
            ("terminal_anchor_authentication_signature_base64", "base64"),
            ("generation_terminal_anchor_evidence_sha256", "sha256"),
        ],
        "generation_terminal_anchor_evidence_sha256",
        acyclic_stage=13,
        retained_output_rule="terminal-anchor signature is field-specific UNIQUE_DETERMINISTIC_BYTES over the exact full transition",
        constraints=["distinct terminal-anchor authority atomically changes the independently current exact ledger state from RESERVED_ATTEMPT_ZERO to CONSUMED_TERMINAL and increments the same ledger counter by one while the sequence-wide journal claim remains HELD", "terminal anchor statement hashes exact slot reservation reservation-ledger evidence outcome pre/post state roots objects counters and CAS/no-fork results and is signed only by distinct terminal authority role/key", "verifier queries that authority current head and requires it equal this evidence hash", "exactly one SUCCESS or fixed content-independent FAILED outcome binds one reservation and slot; no sibling terminal outcome", "independent terminal authority materializes the branch fixed by this role's exact pre-output plan projection: MATERIALIZE_SUCCESS maps to READY/SUCCESS and the unique first FIXED_ROLE_TECHNICAL_FAILURE maps to FIXED/FAILED; post-reveal silence cannot create or change FAILED", "the complete-sequence materializer produces every planned SUCCESS byte or fixed FAILED anchor by the exact deadline and cannot release the sequence journal claim", "prior ledger evidence equals exact reservation-ledger evidence", "attempt zero slot can never return to UNASSIGNED or RESERVED and no retry can be registered; the held claim releases only in the final normal or canonical failure/refusal journal CAS"],
    ),
    "public_beacon_pre_reveal_evidence": schema(
        "kira.mind.continuity.v21.public_beacon_pre_reveal_head_evidence.v1",
        new_domains["public_beacon_pre_reveal_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"),
            ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"),
            ("journal_id_token", "token256"), ("journal_epoch", "uint64"),
            ("reserved_sequence", "uint64"), ("output_role", "output_role"),
            ("output_generation_mode_for_allocation", "output_generation_mode"),
            ("output_attempt_index_for_allocation", "attempt_zero"),
            ("message_or_statement_root_sha256", "sha256"),
            ("completed_success_role_prefix_root_sha256", "sha256"),
            ("reservation_slot_key_sha256", "sha256"),
            ("beacon_allocation_slot_key_sha256", "sha256"),
            ("public_round_beacon_identity_sha256", "sha256"),
            ("public_round_beacon_profile_sha256", "sha256"),
            ("prior_public_beacon_pre_reveal_evidence_sha256", "nullable_sha256"),
            ("pre_public_beacon_pre_reveal_state_root_sha256", "sha256"),
            ("pre_public_beacon_pre_reveal_state_object_sha256", "sha256"),
            ("pre_public_beacon_pre_reveal_state_counter", "uint64"),
            ("pre_beacon_allocation_map_root_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_root_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_object_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_counter", "uint64"),
            ("post_beacon_allocation_map_root_sha256", "sha256"),
            ("public_beacon_pre_reveal_head_counter", "uint64"),
            ("committed_future_round_index", "uint64"),
            ("committed_round_output_sha256", "sha256"),
            ("public_beacon_output_recovery_commitment_sha256", "sha256"),
            ("fixed_reveal_schedule_profile_sha256", "sha256"),
            ("public_beacon_pre_reveal_genesis_manifest_sha256", "sha256"),
            ("public_beacon_pre_reveal_cas_no_fork_profile_sha256", "sha256"),
            ("pre_reveal_cas_result", "enum"), ("pre_reveal_no_fork_result", "enum"),
            ("beacon_reveal_state", "enum"), ("beacon_vrf_authentication_key_role", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"), ("output_selection_profile_sha256", "sha256"),
            ("beacon_allocation_assignment_proof_base64", "base64"),
            ("pre_reveal_authentication_signature_base64", "base64"),
            ("public_beacon_pre_reveal_evidence_sha256", "sha256"),
        ],
        "public_beacon_pre_reveal_evidence_sha256",
        retained_output_rule="field-specific UNIQUE_DETERMINISTIC_BYTES under the fixed beacon key and pre-reveal profile",
        constraints=["pre-state counter zero iff prior head null and pre-state is the unique typed singleton-registration and beacon-genesis-manifest-derived base whose allocation cursor is zero allocation-map root is the exact pinned empty root and committed output is the exact counter-zero sentinel; post/head counter is checked one", "positive pre-state counter requires byte-available independently current prior head whose post root object counter allocation cursor and allocation-map root equal current pre values with identical identity profile key and schedule", "one atomic no-fork CAS advances exact pre state to exact post state and one canonical sparse-map proof changes the exact registration epoch sequence role attempt-zero allocation slot from UNASSIGNED to ALLOCATED_PRE_REVEAL; a second allocation for that role slot is impossible even if the global cursor advanced", "completed_success_role_prefix_root_sha256 proves output_role is exactly the next lifecycle role after a complete SUCCESS prefix; role zero uses the sequence-wide pre-output member only, and no future-role early allocation skip or extra unreserved allocation is accepted", "reserved sequence role mode attempt reservation slot closed message root sequence claim and pre-output materialization commitment are signed before reveal and equality-bind the only later reservation; the pre-output complete materializer makes that reservation and its full terminal/target closure mandatory so an allocated head cannot be abandoned", "post committed_future_round_index is checked pre committed_future_round_index plus one with overflow refusal; this is the exact strictly increasing next unused future unrevealed round under the pinned demand-driven schedule", "the output recovery commitment is fixed by the pre-output complete materialization evidence and exact round/slot/message tuple and guarantees one reconstructible VRF output/proof even if the named beacon withholds", "the deadline VRF is an explicitly domain-separated terminal-clock substream with its own precommitted recovery key and is not another value in this generation-round allocation sequence", "committed output hash does not reveal output and later normal or recovery VRF output must hash exactly to it"],
    ),
    "beacon_reservation_order_evidence": schema(
        "kira.mind.continuity.v21.reservation_before_beacon_reveal_order_evidence.v1",
        new_domains["beacon_reservation_order_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("public_beacon_pre_reveal_evidence_sha256", "sha256"),
            ("generation_reservation_sha256", "sha256"),
            ("generation_reservation_ledger_evidence_sha256", "sha256"),
            ("reservation_slot_key_sha256", "sha256"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"),
            ("reserved_sequence", "uint64"), ("output_role", "output_role"),
            ("reserved_output_generation_mode", "output_generation_mode"),
            ("reservation_attempt_index", "attempt_zero"),
            ("beacon_allocation_slot_key_sha256", "sha256"),
            ("public_beacon_output_recovery_commitment_sha256", "sha256"),
            ("public_beacon_pre_reveal_head_counter", "uint64"),
            ("public_round_index", "uint64"), ("ledger_post_counter", "uint64"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("fixed_terminal_deadline_round_index", "uint64"),
            ("deadline_beacon_output_recovery_commitment_sha256", "sha256"),
            ("beacon_reveal_state_at_ledger_commit", "enum"),
            ("beacon_vrf_authentication_key_role", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"), ("output_selection_profile_sha256", "sha256"),
            ("reservation_before_reveal_proof_base64", "base64"),
            ("beacon_reservation_order_evidence_sha256", "sha256"),
        ],
        "beacon_reservation_order_evidence_sha256",
        retained_output_rule="field-specific UNIQUE_DETERMINISTIC_BYTES over exact pre-reveal head and exact committed reservation-ledger transition",
        constraints=["beacon authority verifies the reservation-ledger evidence was current and committed while exact round state remained PRE_REVEAL", "round head counter identity schedule output role sequence slot and all roots equal reservation ledger and terminal outcome", "post-reveal reservation or alternate head round timing path or missing order evidence refuses"],
    ),
    "public_beacon_pre_reveal_state": schema(
        "kira.mind.continuity.v21.public_beacon_pre_reveal_state.v1",
        new_domains["public_beacon_pre_reveal_state"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("public_round_beacon_identity_sha256", "sha256"),
            ("public_round_beacon_profile_sha256", "sha256"),
            ("fixed_reveal_schedule_profile_sha256", "sha256"),
            ("public_beacon_pre_reveal_genesis_manifest_sha256", "sha256"),
            ("public_beacon_pre_reveal_state_counter", "uint64"),
            ("beacon_allocation_map_root_sha256", "sha256"),
            ("committed_future_round_index", "uint64"),
            ("committed_round_output_sha256", "sha256"),
            ("beacon_reveal_state", "enum"),
            ("public_beacon_pre_reveal_state_root_sha256", "sha256"),
            ("public_beacon_pre_reveal_state_object_sha256", "sha256"),
        ],
        "public_beacon_pre_reveal_state_object_sha256",
        state_root_preimage="all fields through beacon_reveal_state in exact field order",
        constraints=["counter zero is the unique exact typed base derived from singleton registration and pinned beacon genesis manifest and has exact empty allocation-map root committed_future_round_index zero and exact counter-zero output sentinel", "every positive transition preserves the fixed schedule assigns exactly one previously UNASSIGNED sequence-role allocation slot in the canonical map and sets post committed_future_round_index to checked predecessor plus one; no second same-slot allocation skip collision rewind restored sibling past round or already revealed allocation is valid", "the pinned schedule is demand-driven: a generation round can be revealed only after its unique role-scoped pre-reveal state transition reservation-ledger commit and order proof", "root and object identify one same byte-available state instance"],
    ),
    "public_beacon_reveal_evidence": schema(
        "kira.mind.continuity.v21.public_beacon_reveal_evidence.v1",
        new_domains["public_beacon_reveal_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("generation_reservation_sha256", "sha256"),
            ("generation_reservation_ledger_evidence_sha256", "sha256"),
            ("public_beacon_pre_reveal_evidence_sha256", "sha256"),
            ("beacon_reservation_order_evidence_sha256", "sha256"),
            ("public_beacon_output_recovery_commitment_sha256", "sha256"),
            ("reservation_slot_key_sha256", "sha256"), ("reserved_sequence", "uint64"),
            ("output_role", "output_role"),
            ("reserved_output_generation_mode", "output_generation_mode"),
            ("reservation_attempt_index", "attempt_zero"),
            ("beacon_allocation_slot_key_sha256", "sha256"),
            ("public_round_index", "uint64"),
            ("public_beacon_pre_reveal_head_counter", "uint64"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("fixed_terminal_deadline_round_index", "uint64"),
            ("deadline_beacon_output_recovery_commitment_sha256", "sha256"),
            ("public_beacon_vrf_input_message_root_sha256", "sha256"),
            ("public_beacon_output_base64", "base64"),
            ("public_beacon_output_sha256", "sha256"),
            ("beacon_vrf_proof_base64", "base64"),
            ("public_beacon_recovery_reconstruction_proof_base64", "base64"),
            ("beacon_reveal_state", "enum"),
            ("public_round_beacon_identity_sha256", "sha256"),
            ("beacon_vrf_authentication_key_role", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"), ("output_selection_profile_sha256", "sha256"),
            ("public_beacon_reveal_evidence_sha256", "sha256"),
        ],
        "public_beacon_reveal_evidence_sha256",
        retained_output_rule="VRF verifier consumes exact non-circular input message and proof, returns one canonical output byte string, and its SHA256 equals every committed/revealed/output copy",
        constraints=["created only after the sequence-wide pre-output health/materialization commitment, exact order evidence and round reveal and before confidential generation", "VRF input excludes proof output bytes and all terminal fields", "identity profile key round pre-reveal commitment and pre-output nonabortable recovery commitment are exact pinned and equality-bound"],
    ),
    "pre_witness_technical_health_evidence": schema(
        "kira.mind.continuity.v21.pre_witness_technical_health_evidence.v1",
        new_domains["pre_witness_technical_health_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"),
            ("generation_sequence_transaction_claim_evidence_sha256", "sha256"),
            ("sequence_transaction_claim_slot_key_sha256", "sha256"),
            ("sequence_transaction_claim_statement_sha256", "sha256"),
            ("reserved_sequence", "uint64"),
            ("authoritative_pre_state_kind", "enum"),
            ("fixed_role_lifecycle_order_root_sha256", "sha256"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("pre_witness_health_predicate_sha256", "sha256"),
            ("pre_witness_health_profile_sha256", "sha256"),
            ("pre_witness_health_authority_identity_sha256", "sha256"),
            ("complete_sequence_materialization_profile_root_sha256", "sha256"),
            ("complete_sequence_materialization_roster_root_sha256", "sha256"),
            ("complete_sequence_materialization_recovery_key_root_sha256", "sha256"),
            ("generation_beacon_nonabortable_recovery_profile_sha256", "sha256"),
            ("generation_beacon_nonabortable_recovery_key_root_sha256", "sha256"),
            ("deadline_beacon_nonabortable_recovery_profile_sha256", "sha256"),
            ("deadline_beacon_nonabortable_recovery_key_root_sha256", "sha256"),
            ("post_claim_total_terminalization_profile_sha256", "sha256"),
            ("lifecycle_refusal_relation_profile_sha256", "sha256"),
            ("confidential_generator_identity_sha256", "sha256"),
            ("confidential_contributor_roster_sha256", "sha256"),
            ("confidential_contributor_key_root_sha256", "sha256"),
            ("confidential_contribution_aggregation_profile_sha256", "sha256"),
            ("observed_sequence_claim_post_ledger_state_root_sha256", "sha256"),
            ("observed_sequence_claim_post_ledger_state_object_sha256", "sha256"),
            ("observed_sequence_claim_post_ledger_counter", "uint64"),
            ("observed_confidential_generator_image_sha256", "sha256"),
            ("observed_confidential_generator_profile_sha256", "sha256"),
            ("observed_contributor_roster_sha256", "sha256"),
            ("observed_contributor_key_root_sha256", "sha256"),
            ("technical_health_input_vector_sha256", "sha256"),
            ("technical_health_measurement_result", "enum"),
            ("technical_health_measurement_output_generation_mode", "output_generation_mode"),
            ("technical_health_measurement_output_attempt_index", "attempt_zero"),
            ("pre_witness_health_measurement_output_selection_profile_sha256", "sha256"),
            ("technical_health_measurement_attestation_base64", "base64"),
            ("health_predicate_evaluation_root_sha256", "sha256"),
            ("producer_availability_predicate_sha256", "sha256"),
            ("producer_availability_profile_sha256", "sha256"),
            ("producer_availability_authority_identity_sha256", "sha256"),
            ("producer_availability_result", "enum"),
            ("producer_availability_authentication_key_role", "enum"),
            ("producer_availability_output_generation_mode", "output_generation_mode"),
            ("producer_availability_output_attempt_index", "attempt_zero"),
            ("producer_availability_output_selection_profile_sha256", "sha256"),
            ("producer_availability_authentication_signature_base64", "base64"),
            ("materialization_commitment_result", "enum"),
            ("complete_sequence_materialization_commitment_root_sha256", "sha256"),
            ("complete_sequence_materialization_commitment_proof_base64", "base64"),
            ("witness_admission_state", "enum"), ("technical_health_result", "enum"),
            ("health_failure_code", "enum"),
            ("pre_witness_health_authentication_key_role", "enum"),
            ("attestation_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"), ("output_selection_profile_sha256", "sha256"),
            ("health_authentication_signature_base64", "base64"),
            ("pre_witness_technical_health_evidence_sha256", "sha256"),
        ],
        "pre_witness_technical_health_evidence_sha256",
        retained_output_rule="before any role beacon allocation, one fixed measured-state authority and one complete-sequence materializer commit all branch-affecting health observations plus every generation beacon deadline beacon confidential generator retained target byte terminal anchor journal authority anchor and final-CAS recovery service; each retained proof/signature is field-specific UNIQUE_DETERMINISTIC_BYTES",
        constraints=["created immediately after the sequence claim acquisition post-state and before every beacon allocation reservation reveal witness admission or content-bearing computation", "the complete byte-available input vector binds the exact claim post-ledger state, fixed generator image/profile, full contributor roster/key root, all authority/materializer profiles and the exact fixed ten-role lifecycle; it contains no beacon output round payload scope witness seed opening or content-correlatable input", "measurement and producer-availability results are uniquely verifier-derived before output and cannot be changed after any public seed is known", "COMPLETE_SEQUENCE_MATERIALIZATION_COMMITTED proves every later beacon output/proof, confidential result, deterministic nonce, retained target signature/proof, terminal anchor, normal/failure authority successor and final ledger+journal CAS byte is already entrusted to the exact pinned threshold-isolated non-abortable executor or public recovery transcript", "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE immediately enters the unique pre-output sequence-consuming failure path before role zero and cannot allocate a beacon round", "the committed total state machine always emits either the complete ten-role normal commit or one exact hidden lifecycle-refusal/fixed-technical-failure commit; post-claim silence withholding invalid reveal erasure-surface refusal or absent canonical witness cannot strand HELD", "witness remains NOT_ADMITTED while this object is created; no permission speech privacy audience safety upset or human-approval predicate exists"],
    ),
    "terminal_deadline_observation_evidence": schema(
        "kira.mind.continuity.v21.terminal_deadline_observation_evidence.v1",
        new_domains["terminal_deadline_observation_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("generation_reservation_sha256", "sha256"),
            ("generation_reservation_ledger_evidence_sha256", "sha256"),
            ("public_beacon_reveal_evidence_sha256", "sha256"),
            ("pre_witness_technical_health_evidence_sha256", "sha256"),
            ("reservation_slot_key_sha256", "sha256"), ("reserved_sequence", "uint64"),
            ("output_role", "output_role"),
            ("reserved_output_generation_mode", "output_generation_mode"),
            ("reservation_attempt_index", "attempt_zero"),
            ("generation_public_round_index", "uint64"),
            ("fixed_terminal_deadline_round_delta", "uint64"),
            ("fixed_terminal_deadline_round_index", "uint64"),
            ("deadline_beacon_output_recovery_commitment_sha256", "sha256"),
            ("deadline_vrf_input_message_root_sha256", "sha256"),
            ("deadline_beacon_output_base64", "base64"),
            ("deadline_beacon_output_sha256", "sha256"),
            ("deadline_beacon_vrf_proof_base64", "base64"),
            ("deadline_beacon_recovery_reconstruction_proof_base64", "base64"),
            ("terminal_deadline_state", "enum"),
            ("fixed_terminal_timing_envelope_profile_sha256", "sha256"),
            ("public_round_beacon_identity_sha256", "sha256"),
            ("beacon_vrf_authentication_key_role", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"), ("output_selection_profile_sha256", "sha256"),
            ("deadline_observation_authentication_signature_base64", "base64"),
            ("terminal_deadline_observation_evidence_sha256", "sha256"),
        ],
        "terminal_deadline_observation_evidence_sha256",
        retained_output_rule="unique beacon VRF output proof and observation signature establish the exact precommitted deadline boundary",
        constraints=["deadline round is the exact checked derivation from reserved generation round and fixed timing profile", "evidence is materialized exactly at that round whether producer is present absent or silent", "early late suppressed alternate clock time head or round evidence refuses", "branch materialization occurs only after this evidence"],
    ),
    "generation_sequence_lifecycle_refusal_evidence": schema(
        "kira.mind.continuity.v21.hidden_lifecycle_refusal_evidence.v1",
        new_domains["generation_sequence_lifecycle_refusal_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"),
            ("generation_sequence_transaction_claim_evidence_sha256", "sha256"),
            ("pre_witness_technical_health_evidence_sha256", "sha256"),
            ("reserved_sequence", "uint64"), ("refusal_boundary_role", "output_role"),
            ("refusal_boundary_role_index", "uint64"),
            ("completed_success_role_prefix_root_sha256", "sha256"),
            ("fixed_role_lifecycle_order_root_sha256", "sha256"),
            ("lifecycle_refusal_statement_root_sha256", "sha256"),
            ("lifecycle_refusal_relation_profile_sha256", "sha256"),
            ("lifecycle_refusal_generator_image_sha256", "sha256"),
            ("canonical_private_witness_encoding_profile_sha256", "sha256"),
            ("canonical_scope_collector_witness_relation_sha256", "sha256"),
            ("confidential_contributor_roster_sha256", "sha256"),
            ("confidential_contributor_key_root_sha256", "sha256"),
            ("confidential_contribution_aggregation_profile_sha256", "sha256"),
            ("confidential_seed_derivation_profile_sha256", "sha256"),
            ("refusal_confidential_seed_derivation_statement_root_sha256", "sha256"),
            ("lifecycle_refusal_authority_identity_sha256", "sha256"),
            ("lifecycle_refusal_result", "enum"), ("lifecycle_refusal_code", "enum"),
            ("witness_admission_state", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"),
            ("output_selection_profile_sha256", "sha256"),
            ("lifecycle_refusal_zero_knowledge_proof_base64", "base64"),
            ("refusal_private_seed_zero_knowledge_attestation_base64", "base64"),
            ("lifecycle_refusal_authentication_key_role", "enum"),
            ("lifecycle_refusal_authentication_signature_base64", "base64"),
            ("generation_sequence_lifecycle_refusal_evidence_sha256", "sha256"),
        ],
        "generation_sequence_lifecycle_refusal_evidence_sha256",
        retained_output_rule="one generic randomized zero-knowledge refusal proof hides which surface predicate witness or content caused refusal; a unique confidential-seed attestation and distinct refusal-authority signature bind the exact claim boundary and consume attempt zero",
        constraints=["materialized by the pre-output committed total state machine for every post-claim V19 unavailable unreachable unclosed unverifiable erasure surface or noncanonical/unavailable witness condition that prevents the next required role", "the canonical collector and witness encoder select exactly one internal refusal relation and boundary; no caller choice alternate encoding repeated query or predicate-specific public code exists", "the public statement reveals only the claim sequence fixed lifecycle boundary generic refusal result and already-hiding success-prefix roots; it contains no surface identifier payload scope map witness digest or guess-confirming value", "private refusal seed is domain-separated by namespace context registration epoch sequence boundary role attempt zero statement and exact contributor roster, remains inside the threshold-isolated executor and is erased", "exactly one refusal evidence enters the same journal authority anchor and claim-release failure transition; no beacon round is allocated for the refused boundary and no retry uses the sequence", "technical/lifecycle integrity refusal never controls Kira's speech recollection correction supersession withdrawal or voluntary-forgetting choice"],
    ),
    "role_producer_availability_commitment": schema(
        "kira.mind.continuity.v21.role_producer_availability_commitment.v1",
        new_domains["role_producer_availability_commitment"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"),
            ("generation_sequence_transaction_claim_evidence_sha256", "sha256"),
            ("pre_witness_technical_health_evidence_sha256", "sha256"),
            ("reserved_sequence", "uint64"), ("output_role", "output_role"),
            ("role_lifecycle_index", "uint64"), ("output_attempt_index", "attempt_zero"),
            ("public_beacon_pre_reveal_evidence_sha256", "sha256"),
            ("beacon_allocation_slot_key_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_root_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_object_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_counter", "uint64"),
            ("public_round_index", "uint64"),
            ("generation_reservation_sha256", "sha256"),
            ("reservation_slot_key_sha256", "sha256"),
            ("generation_reservation_ledger_evidence_sha256", "sha256"),
            ("post_reservation_ledger_state_root_sha256", "sha256"),
            ("post_reservation_ledger_state_object_sha256", "sha256"),
            ("post_reservation_ledger_counter", "uint64"),
            ("beacon_reservation_order_evidence_sha256", "sha256"),
            ("producer_availability_predicate_sha256", "sha256"),
            ("producer_availability_profile_sha256", "sha256"),
            ("producer_availability_commitment_profile_sha256", "sha256"),
            ("producer_availability_observation_profile_sha256", "sha256"),
            ("producer_availability_result_profile_sha256", "sha256"),
            ("producer_availability_authority_identity_sha256", "sha256"),
            ("producer_availability_authentication_key_role", "enum"),
            ("committed_producer_availability_result", "enum"),
            ("producer_availability_observation_root_sha256", "sha256"),
            ("producer_availability_result_root_sha256", "sha256"),
            ("role_producer_availability_commitment_statement_sha256", "sha256"),
            ("role_producer_availability_commitment_sha256", "sha256"),
        ],
        "role_producer_availability_commitment_sha256",
        constraints=["created only after this exact role reservation ledger CAS and reservation-before-reveal order proof and before reveal", "complete preimage is role sequence slot attempt allocation and post-ledger qualified and excludes beacon output proof generated bytes seed witness scope content and every later outcome", "MATERIALIZE_SUCCESS requires the exact nonabortable committed result; the unique instantiated FIXED_ROLE_TECHNICAL_FAILURE role requires exact FIXED_UNAVAILABLE; sequence-wide pre-output failure hidden-refusal boundary and NOT_REACHED roles create no availability object"],
    ),
    "role_producer_availability_evidence": schema(
        "kira.mind.continuity.v21.role_producer_availability_evidence.v1",
        new_domains["role_producer_availability_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("role_producer_availability_commitment_sha256", "sha256"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"),
            ("generation_sequence_transaction_claim_evidence_sha256", "sha256"),
            ("pre_witness_technical_health_evidence_sha256", "sha256"),
            ("reserved_sequence", "uint64"), ("output_role", "output_role"),
            ("role_lifecycle_index", "uint64"), ("output_attempt_index", "attempt_zero"),
            ("public_beacon_pre_reveal_evidence_sha256", "sha256"),
            ("beacon_allocation_slot_key_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_root_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_object_sha256", "sha256"),
            ("post_public_beacon_pre_reveal_state_counter", "uint64"),
            ("public_round_index", "uint64"),
            ("generation_reservation_sha256", "sha256"),
            ("reservation_slot_key_sha256", "sha256"),
            ("generation_reservation_ledger_evidence_sha256", "sha256"),
            ("post_reservation_ledger_state_root_sha256", "sha256"),
            ("post_reservation_ledger_state_object_sha256", "sha256"),
            ("post_reservation_ledger_counter", "uint64"),
            ("beacon_reservation_order_evidence_sha256", "sha256"),
            ("producer_availability_predicate_sha256", "sha256"),
            ("producer_availability_profile_sha256", "sha256"),
            ("producer_availability_commitment_profile_sha256", "sha256"),
            ("producer_availability_observation_profile_sha256", "sha256"),
            ("producer_availability_result_profile_sha256", "sha256"),
            ("producer_availability_authority_identity_sha256", "sha256"),
            ("producer_availability_authentication_key_role", "enum"),
            ("producer_availability_observation_root_sha256", "sha256"),
            ("producer_availability_result_root_sha256", "sha256"),
            ("producer_availability_result", "enum"),
            ("availability_verification_result", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index_for_evidence", "attempt_zero"),
            ("output_selection_profile_sha256", "sha256"),
            ("producer_availability_authentication_signature_base64", "base64"),
            ("role_producer_availability_evidence_sha256", "sha256"),
        ],
        "role_producer_availability_evidence_sha256",
        retained_output_rule="one unique producer-availability signature verifies the exact prior commitment observation and result tuple before reveal",
        constraints=["evidence is byte-identical to its same-role commitment tuple and cannot be transplanted across sequence role reservation slot allocation or ledger history", "availability_verification_result is exact VERIFIED_AS_COMMITTED; producer_availability_result is NON_ABORTABLE_OUTPUT_MATERIALIZER_COMMITTED for a planned SUCCESS role or FIXED_UNAVAILABLE for the unique pre-output-planned technical-failure role", "hidden-refusal boundary and NOT_REACHED suffix roles create no availability object", "no output reveal proof generated value seed witness or content-dependent byte is reachable"],
    ),
    "generation_failure_record": schema(
        "kira.mind.continuity.v21.canonical_generation_failure_record.v1",
        new_domains["generation_failure_record"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("reserved_sequence", "uint64"),
            ("output_role", "output_role"), ("reservation_slot_key_sha256", "sha256"),
            ("failure_trigger", "enum"),
            ("failure_role_index", "uint64"),
            ("completed_success_role_prefix_root_sha256", "sha256"),
            ("unreserved_suffix_cancellation_barrier_root_sha256", "sha256"),
            ("cancelled_unreserved_role_count", "uint64"),
            ("generation_reservation_sha256", "nullable_sha256"),
            ("generation_reservation_ledger_evidence_sha256", "nullable_sha256"),
            ("public_beacon_reveal_evidence_sha256", "nullable_sha256"),
            ("pre_witness_technical_health_evidence_sha256", "sha256"),
            ("terminal_deadline_observation_evidence_sha256", "nullable_sha256"),
            ("generation_terminal_outcome_sha256", "nullable_sha256"),
            ("generation_terminal_anchor_evidence_sha256", "nullable_sha256"),
            ("generation_sequence_lifecycle_refusal_evidence_sha256", "nullable_sha256"),
            ("pre_receipt_token_root_sha256", "sha256"), ("post_receipt_token_root_sha256", "sha256"),
            ("pre_scope_token_root_sha256", "sha256"), ("post_scope_token_root_sha256", "sha256"),
            ("pre_proof_token_root_sha256", "sha256"), ("post_proof_token_root_sha256", "sha256"),
            ("failure_code", "enum"), ("technical_health_result", "enum"),
            ("generation_failure_record_sha256", "sha256"),
        ],
        "generation_failure_record_sha256",
        constraints=["PRE_OUTPUT_FIXED_TECHNICAL_FAILURE is permitted only before role zero when the exact pre-output materialization evidence deterministically reports fixed failure; every role-chain and lifecycle-refusal link is JSON null", "ROLE_TERMINAL_FAILED requires one exact first FAILED role terminal chain and null lifecycle-refusal hash; HIDDEN_LIFECYCLE_REFUSAL requires one exact generic zero-knowledge refusal evidence and JSON null for every uncreated boundary-role reservation reveal deadline outcome and terminal-anchor hash", "failure_role_index is zero for pre-output technical failure and otherwise the unique zero-based index of the failed/refused output_role boundary; every earlier role has a completely consumed SUCCESS chain committed into completed_success_role_prefix_root_sha256", "no later role reservation exists; unreserved_suffix_cancellation_barrier_root_sha256 deterministically covers the uncreated boundary and every later role and permanently closes those sequence-role slots without pretending an attempt occurred", "cancelled_unreserved_role_count equals ten for pre-output fixed failure, ten minus failure_role_index under hidden-refusal, and ten minus failure_role_index minus one under role-terminal failure, using checked uint64 arithmetic", "contains no payload scope witness surface identifier commitment opening proof witness or guessed-content value", "one canonical sequence-level integrity record occupies the sequence and cannot be mistaken for a completed memory lifecycle record; no second failure/refusal record competing CAS retry or confirmation query exists"],
    ),
    "generation_failure_journal_state": schema(
        "kira.mind.continuity.v21.generation_failure_journal_state.v1",
        new_domains["generation_failure_journal_state"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("generation_failure_record_sha256", "sha256"),
            ("failed_sequence_barrier_root_sha256", "sha256"),
            ("committed_record_count", "uint64"), ("head_sequence", "uint64"),
            ("head_receipt_hash_sha256", "sha256"), ("head_event_hash_sha256", "sha256"),
            ("consumed_receipt_token_root_sha256", "sha256"),
            ("consumed_scope_token_root_sha256", "sha256"),
            ("consumed_proof_token_root_sha256", "sha256"),
            ("failure_state_nonce_sha256", "sha256"),
            ("generation_failure_journal_state_root_sha256", "sha256"),
            ("generation_failure_journal_state_object_sha256", "sha256"),
        ],
        "generation_failure_journal_state_object_sha256",
        state_root_preimage="all fields through failure_state_nonce_sha256 in exact order",
        constraints=["post count is checked pre count plus one and head sequence equals the claimed sequence consumed by the exact pre-output technical-failure role-terminal-failure or hidden-refusal branch", "failed_sequence_barrier_root_sha256 equals the failure record unreserved suffix cancellation barrier and prevents every cancelled boundary or later role reservation at this sequence", "receipt and event heads are distinct domain hashes of the exact canonical failure/refusal record", "all three consumed token roots equal pre state because no memory receipt scope or proof token is accepted", "failure nonce is the exact branch-domain hash of failure record sequence barrier and its one pre-output health terminal-anchor or hidden-refusal evidence hash, with no generation retry"],
    ),
    "generation_failure_sequence_commit_evidence": schema(
        "kira.mind.continuity.v21.generation_failure_sequence_commit_evidence.v1",
        new_domains["generation_failure_sequence_commit_evidence"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"), ("generation_failure_record_sha256", "sha256"),
            ("failure_trigger", "enum"),
            ("generation_terminal_anchor_evidence_sha256", "nullable_sha256"),
            ("generation_sequence_lifecycle_refusal_evidence_sha256", "nullable_sha256"),
            ("failed_sequence_barrier_root_sha256", "sha256"),
            ("pre_journal_state_root_sha256", "sha256"), ("pre_journal_state_object_sha256", "sha256"),
            ("pre_state_kind", "enum"),
            ("pre_record_count", "uint64"), ("pre_head_sequence", "nullable_uint64"),
            ("pre_head_receipt_hash_sha256", "nullable_sha256"), ("pre_head_event_hash_sha256", "nullable_sha256"),
            ("post_failure_state_root_sha256", "sha256"), ("post_failure_state_object_sha256", "sha256"),
            ("post_state_kind", "enum"),
            ("post_record_count", "uint64"), ("post_head_sequence", "uint64"),
            ("post_head_receipt_hash_sha256", "sha256"), ("post_head_event_hash_sha256", "sha256"),
            ("pre_receipt_token_root_sha256", "sha256"), ("post_receipt_token_root_sha256", "sha256"),
            ("pre_scope_token_root_sha256", "sha256"), ("post_scope_token_root_sha256", "sha256"),
            ("pre_proof_token_root_sha256", "sha256"), ("post_proof_token_root_sha256", "sha256"),
            ("pre_state_authority_head_evidence_sha256", "sha256"),
            ("pre_state_authority_monotonic_counter", "uint64"),
            ("pre_external_anchor_root_sha256", "sha256"),
            ("pre_external_anchor_monotonic_counter", "uint64"),
            ("post_failure_external_anchor_statement_sha256", "sha256"),
            ("post_failure_external_anchor_root_sha256", "sha256"),
            ("post_external_anchor_monotonic_counter", "uint64"),
            ("failure_anchor_authentication_proof_base64", "base64"),
            ("post_failure_state_authority_statement_sha256", "sha256"),
            ("post_failure_state_authority_head_evidence_sha256", "sha256"),
            ("post_state_authority_monotonic_counter", "uint64"),
            ("failure_authority_authentication_signature_base64", "base64"),
            ("cas_result", "enum"), ("no_fork_result", "enum"),
            ("authoritative_journal_store_identity_sha256", "sha256"),
            ("state_authority_identity_sha256", "sha256"), ("external_anchor_identity_sha256", "sha256"),
            ("journal_authentication_key_role", "enum"),
            ("state_authority_authentication_key_role", "enum"),
            ("external_anchor_authentication_key_role", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"), ("output_selection_profile_sha256", "sha256"),
            ("failure_commit_authentication_proof_base64", "base64"),
            ("generation_failure_sequence_commit_evidence_sha256", "sha256"),
        ],
        "generation_failure_sequence_commit_evidence_sha256",
        retained_output_rule="unique external-anchor proof, state-authority signature and fixed-roster journal commit proof close one combined failure-path journal/authority/anchor advance",
        constraints=["atomic current authoritative journal CAS advances the claimed sequence exactly once for the mutually exclusive pre-output technical-failure role-terminal-failure or hidden-lifecycle-refusal branch", "the same object contains two exact closed nested preimages: external-anchor successor binds the failure post-state and prior anchor, then state-authority successor binds the same post-state and exact new anchor; both checked counters increment by one", "failure anchor proof and authority signature use the preserved fixed V20 external-anchor and state-authority profiles roles and public keys; the final quorum proof also binds both successor hashes", "the independently current authority and anchor heads must equal the typed successors before a future reservation; journal authority and anchor cannot diverge", "proof roster order roles keys and encoding are fixed; one pre root has one post failure root authority head and anchor root and one atomic claim-release transition", "future reservation derives next sequence from this advanced authoritative journal+authority+anchor state", "failure/refusal transition never asserts erasure COMPLETE or fabricates scope proof receipt event or memory success"],
    ),
    "failure_external_anchor_current_head_observation": schema(
        "kira.mind.continuity.v21.failure_external_anchor_current_head_observation.v1",
        new_domains["failure_external_anchor_current_head_observation"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"),
            ("generation_failure_sequence_commit_evidence_sha256", "sha256"),
            ("generation_failure_record_sha256", "sha256"),
            ("failure_trigger", "enum"), ("failure_role", "output_role"),
            ("failure_role_index", "uint64"), ("reserved_sequence", "uint64"),
            ("post_failure_state_root_sha256", "sha256"),
            ("post_failure_state_object_sha256", "sha256"),
            ("post_record_count", "uint64"), ("post_head_sequence", "uint64"),
            ("post_head_receipt_hash_sha256", "sha256"), ("post_head_event_hash_sha256", "sha256"),
            ("post_failure_external_anchor_root_sha256", "sha256"),
            ("post_external_anchor_monotonic_counter", "uint64"),
            ("external_anchor_identity_sha256", "sha256"),
            ("external_anchor_profile_sha256", "sha256"),
            ("external_anchor_authentication_key_role", "enum"),
            ("current_head_observation_result", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"),
            ("output_selection_profile_sha256", "sha256"),
            ("current_head_observation_proof_base64", "base64"),
            ("failure_external_anchor_current_head_observation_sha256", "sha256"),
        ],
        "failure_external_anchor_current_head_observation_sha256",
        retained_output_rule="one unique independently authenticated external-anchor current-head observation over the exact completed failure commit successor",
        constraints=["created only after the atomic failure commit and equality-binds every failure post-state head and anchor counter field", "a future claim may use the failure predecessor only when this exact observation verifies current with no restored sibling or stale head"],
    ),
    "failure_state_authority_current_head_observation": schema(
        "kira.mind.continuity.v21.failure_state_authority_current_head_observation.v1",
        new_domains["failure_state_authority_current_head_observation"],
        [
            ("schema", "schema_const"), ("hash_domain", "domain_const"),
            ("failure_external_anchor_current_head_observation_sha256", "sha256"),
            ("namespace_precommitment_sha256", "sha256"), ("pinned_context_sha256", "sha256"),
            ("singleton_registration_sha256", "sha256"), ("journal_id_token", "token256"),
            ("journal_epoch", "uint64"),
            ("generation_failure_sequence_commit_evidence_sha256", "sha256"),
            ("generation_failure_record_sha256", "sha256"),
            ("failure_trigger", "enum"), ("failure_role", "output_role"),
            ("failure_role_index", "uint64"), ("reserved_sequence", "uint64"),
            ("post_failure_state_root_sha256", "sha256"),
            ("post_failure_state_object_sha256", "sha256"),
            ("post_record_count", "uint64"), ("post_head_sequence", "uint64"),
            ("post_head_receipt_hash_sha256", "sha256"), ("post_head_event_hash_sha256", "sha256"),
            ("post_failure_external_anchor_root_sha256", "sha256"),
            ("post_external_anchor_monotonic_counter", "uint64"),
            ("post_failure_state_authority_head_evidence_sha256", "sha256"),
            ("post_state_authority_monotonic_counter", "uint64"),
            ("state_authority_identity_sha256", "sha256"),
            ("state_authority_authentication_key_role", "enum"),
            ("current_head_observation_result", "enum"),
            ("output_generation_mode", "output_generation_mode"),
            ("output_attempt_index", "attempt_zero"),
            ("output_selection_profile_sha256", "sha256"),
            ("current_head_observation_signature_base64", "base64"),
            ("failure_state_authority_current_head_observation_sha256", "sha256"),
        ],
        "failure_state_authority_current_head_observation_sha256",
        retained_output_rule="one unique independently authenticated authority current-head observation consuming the exact anchor observation and completed failure successor",
        constraints=["authority observation repeats the exact failure post-state anchor root authority head and checked counters and cannot be transplanted", "future claim recovery requires both typed observations and their equality to the same failure commit"],
    ),
})

# One sequence-wide authoritative claim is acquired before the first role's
# pre-reveal allocation and remains held across every role-specific slot
# transition.  A role terminal anchor consumes only its role slot.  The claim
# is released only inside the final normal journal commit or the unique
# first-failure journal/authority/anchor commit.
for object_name, marker in {
    "public_beacon_pre_reveal_evidence": "public_round_beacon_identity_sha256",
    "generation_reservation": "public_beacon_pre_reveal_evidence_sha256",
    "generation_reservation_ledger_evidence": "generation_reservation_sha256",
    "beacon_reservation_order_evidence": "public_beacon_pre_reveal_evidence_sha256",
    "public_beacon_reveal_evidence": "generation_reservation_sha256",
    "terminal_deadline_observation_evidence": "generation_reservation_sha256",
    "generation_terminal_outcome": "generation_reservation_sha256",
    "generation_terminal_anchor_evidence": "generation_reservation_sha256",
    "generation_failure_record": "generation_reservation_sha256",
}.items():
    insert_fields(objects[object_name], marker, [("generation_sequence_transaction_claim_evidence_sha256", "sha256")])

# The one sequence-wide pre-output evidence is the immutable materialization
# commitment for every role and every eventual normal/refusal/failure byte.
# Every later allocation/reservation/reveal/outcome/anchor resolves this exact
# same object; no role may introduce a post-output availability or health bit.
for object_name, marker in {
    "public_beacon_pre_reveal_evidence": "public_round_beacon_identity_sha256",
    "generation_reservation": "public_beacon_pre_reveal_evidence_sha256",
    "generation_reservation_ledger_evidence": "generation_reservation_sha256",
    "beacon_reservation_order_evidence": "public_beacon_pre_reveal_evidence_sha256",
    "public_beacon_reveal_evidence": "generation_reservation_sha256",
    "generation_terminal_anchor_evidence": "generation_reservation_sha256",
}.items():
    if "pre_witness_technical_health_evidence_sha256" not in objects[object_name]["field_order"]:
        insert_fields(objects[object_name], marker, [("pre_witness_technical_health_evidence_sha256", "sha256")])

# Each instantiated role has a separate reservation/slot/allocation-qualified
# availability commitment and authenticated evidence after order and before
# reveal.  These exact hashes/results propagate through every later role node.
for object_name, marker in {
    "public_beacon_reveal_evidence": "generation_reservation_sha256",
    "terminal_deadline_observation_evidence": "generation_reservation_sha256",
    "generation_terminal_outcome": "generation_reservation_sha256",
    "generation_terminal_anchor_evidence": "generation_reservation_sha256",
}.items():
    availability_copy_fields = [
        ("role_producer_availability_commitment_sha256", "sha256"),
        ("role_producer_availability_evidence_sha256", "sha256"),
        ("producer_availability_result", "enum"),
    ]
    availability_copy_fields = [
        field for field in availability_copy_fields
        if field[0] not in objects[object_name]["field_order"]
    ]
    if availability_copy_fields:
        insert_fields(objects[object_name], marker, availability_copy_fields)

insert_fields(objects["generation_sequence_transaction_claim_evidence"], "pre_external_anchor_counter", [
    ("failure_external_anchor_current_head_observation_sha256", "nullable_sha256"),
    ("failure_state_authority_current_head_observation_sha256", "nullable_sha256"),
])

sequence_claim_release_fields = [
    ("generation_sequence_transaction_claim_evidence_sha256", "sha256"),
    ("sequence_transaction_claim_slot_key_sha256", "sha256"),
    ("sequence_transaction_claim_statement_sha256", "sha256"),
    ("sequence_claim_pre_reservation_ledger_state_root_sha256", "sha256"),
    ("sequence_claim_pre_reservation_ledger_state_object_sha256", "sha256"),
    ("sequence_claim_pre_reservation_ledger_counter", "uint64"),
    ("sequence_claim_post_reservation_ledger_state_root_sha256", "sha256"),
    ("sequence_claim_post_reservation_ledger_state_object_sha256", "sha256"),
    ("sequence_claim_post_reservation_ledger_counter", "uint64"),
    ("pre_sequence_transaction_claim_state", "sequence_transaction_claim_state"),
    ("post_sequence_transaction_claim_state", "sequence_transaction_claim_state"),
    ("sequence_claim_release_cas_result", "enum"),
    ("sequence_claim_release_no_fork_result", "enum"),
    ("authoritative_sequence_claim_cas_no_fork_profile_sha256", "sha256"),
    ("reservation_ledger_authority_identity_sha256", "sha256"),
    ("reservation_ledger_authority_authentication_key_role", "enum"),
    ("generation_sequence_transaction_claim_output_selection_profile_sha256", "sha256"),
    ("sequence_transaction_claim_release_authentication_signature_base64", "base64"),
]
insert_fields(objects["commit_evidence"], "commit_nonce", sequence_claim_release_fields)
insert_message_fields(objects["commit_evidence"], "commit_nonce", [name for name, _ in sequence_claim_release_fields])
insert_fields(objects["generation_failure_sequence_commit_evidence"], "failure_commit_authentication_proof_base64", sequence_claim_release_fields)
objects["commit_evidence"].setdefault("constraints", []).extend([
    "the same atomic authoritative transaction that commits the exact normal post journal state also changes the exact held sequence claim to RELEASED_BY_EXACT_SEQUENCE_COMMIT under the reservation-ledger authority signature",
    "the claim release pre-state is the final COMMIT_EVIDENCE role consumed ledger state; post counter is checked plus one and no unrelated CAS or early release exists",
])
objects["generation_failure_sequence_commit_evidence"]["constraints"].extend([
    "the same atomic failure journal/authority/anchor transaction changes the exact held sequence claim to RELEASED_BY_EXACT_SEQUENCE_COMMIT; the terminal anchor does not release it",
    "claim release pre-state is selected exhaustively and exclusively by failure_trigger: ROLE_TERMINAL_FAILED uses the exact first-failed role CONSUMED ledger state, while PRE_OUTPUT_FIXED_TECHNICAL_FAILURE and HIDDEN_LIFECYCLE_REFUSAL use the exact never-reserved boundary ledger pre-state; every selected pre-state remains HELD_UNTIL_SEQUENCE_COMMIT until this atomic failure CAS, the post counter is checked plus one, and no competing CAS is possible",
])

# Namespace precommitment directly repeats every immutable SHA-256 context pin
# except its own output and the later context output, avoiding opaque aggregate
# membership and the context->namespace cycle.
namespace_object = objects["namespace_precommitment"]
for field_name, field_type in zip(context["field_order"], context["field_types"]):
    if field_type != "sha256" or field_name in {"namespace_precommitment_sha256", "pinned_context_sha256"}:
        continue
    if field_name not in namespace_object["field_order"]:
        insert_fields(namespace_object, "namespace_precommitment_sha256", [(field_name, "sha256")])

schema_aggregate_members = [
    field_name
    for field_name, field_type in zip(context["field_order"], context["field_types"])
    if field_type == "sha256" and (field_name.endswith("_schema_sha256") or "schema_profile" in field_name or field_name in {"schema_registry_sha256", "runtime_schema_profile_root_sha256"})
]
role_key_profile_aggregate_members = [
    field_name
    for field_name, field_type in zip(context["field_order"], context["field_types"])
    if field_type == "sha256" and any(marker in field_name for marker in ("identity_sha256", "profile_sha256", "public_key_sha256", "verifier_image_sha256", "generator_image_sha256", "validator_image_sha256", "writer_image_sha256"))
]
doc["namespace_aggregate_root_preimages"] = {
    "runtime_schema_profile_root_sha256": {
        "domain": "KIRA_MIND_V21_RUNTIME_SCHEMA_PROFILE_AGGREGATE_ROOT_V1",
        "ordered_member_paths": [f"objects.namespace_precommitment.{field}" for field in schema_aggregate_members if field != "runtime_schema_profile_root_sha256"],
    },
    "runtime_role_key_profile_root_sha256": {
        "domain": "KIRA_MIND_V21_RUNTIME_ROLE_KEY_PROFILE_AGGREGATE_ROOT_V1",
        "ordered_member_paths": [f"objects.namespace_precommitment.{field}" for field in role_key_profile_aggregate_members if field != "runtime_role_key_profile_root_sha256"],
    },
    "preimage_rule": "ASCII domain + actual NUL + for each ordered member: UTF-8 field path + actual NUL + exact 32 decoded hash bytes + actual LF; no omitted duplicate alternate-order or caller member",
    "all_context_sha256_pins_except_namespace_and_context_outputs_repeat_directly_in_namespace": True,
}

independent_identity_fields = [
    "authoritative_journal_store_identity_sha256", "state_authority_identity_sha256",
    "external_anchor_identity_sha256", "global_registrar_identity_sha256",
    "global_registry_identity_sha256", "public_round_beacon_identity_sha256",
    "confidential_generator_identity_sha256", "generation_reservation_authority_identity_sha256",
    "generation_terminal_outcome_authority_identity_sha256", "reservation_ledger_authority_identity_sha256",
    "terminal_anchor_authority_identity_sha256", "pre_witness_health_authority_identity_sha256",
    "producer_availability_authority_identity_sha256", "lifecycle_refusal_authority_identity_sha256",
]
independent_public_key_fields = [
    "result_authentication_public_key_sha256", "verifier_evidence_authentication_public_key_sha256",
    "journal_authentication_public_key_sha256", "state_authority_authentication_public_key_sha256",
    "external_anchor_authentication_public_key_sha256", "global_registrar_authentication_public_key_sha256",
    "global_registry_authentication_public_key_sha256", "generation_reservation_authentication_public_key_sha256",
    "generation_terminal_outcome_authentication_public_key_sha256", "public_round_beacon_vrf_public_key_sha256",
    "confidential_generator_attestation_public_key_sha256", "reservation_ledger_authority_authentication_public_key_sha256",
    "terminal_anchor_authority_authentication_public_key_sha256", "pre_witness_health_authentication_public_key_sha256",
    "producer_availability_authentication_public_key_sha256",
    "lifecycle_refusal_authentication_public_key_sha256",
]
for field_name in independent_identity_fields + independent_public_key_fields:
    if field_name not in context["field_order"]:
        raise ValueError({"missing_independence_context_pin": field_name})
inequality_rows = []
for boundary, fields in [("authority_identity", independent_identity_fields), ("authentication_public_key", independent_public_key_fields)]:
    for left_index, left_field in enumerate(fields):
        for right_field in fields[left_index + 1:]:
            inequality_rows.append({
                "left_path": f"objects.pinned_context.{left_field}",
                "right_path": f"objects.pinned_context.{right_field}",
                "boundary": boundary,
                "predicate": "decoded 32-byte values MUST_NOT_EQUAL",
            })
role_fields = [field for field in doc["fixed_key_roles"] if field.endswith("_key_role")]
role_values = [doc["fixed_key_roles"][field] for field in role_fields]
if len(role_values) != len(set(role_values)):
    raise ValueError("fixed key role constants are not pairwise distinct")
doc["path_qualified_independence_and_inequality_closure"] = {
    "identity_path_count": len(independent_identity_fields),
    "public_key_path_count": len(independent_public_key_fields),
    "pairwise_inequality_row_count": len(inequality_rows),
    "rows": inequality_rows,
    "fixed_key_role_paths": [f"objects.pinned_context.{field}" for field in role_fields],
    "fixed_key_role_values_are_pairwise_distinct": True,
    "allowed_identity_or_public_key_equivalence_classes": [],
    "ledger_terminal_outcome_terminal_anchor_reservation_beacon_generator_and_runtime_authorities_may_share_identity_or_key": False,
}

for obj in objects.values():
    for index, field in enumerate(obj["field_order"]):
        if field == "output_generation_mode":
            obj["field_types"][index] = "output_generation_mode"

doc["exact_enum_constants"].update({
    "output_generation_mode": "UNIQUE_DETERMINISTIC_BYTES",
    "attempt_index": 0,
    "terminal_outcome": ["SUCCESS", "FAILED"],
    "failure_code": ["NONE", "FIXED_CONTENT_INDEPENDENT_TECHNICAL_FAILURE", "HIDDEN_LIFECYCLE_INTEGRITY_REFUSAL"],
    "reservation_slot_consumed": "CONSUMED_NO_RETRY",
    "slot_state": ["UNASSIGNED", "ASSIGNED"],
    "beacon_reveal_state": ["PRE_REVEAL", "REVEALED"],
    "beacon_reveal_state_at_ledger_commit": "PRE_REVEAL",
    "witness_admission_state": "NOT_ADMITTED",
    "technical_health_result": ["READY", "FIXED_TECHNICAL_FAILURE"],
    "producer_availability_result": ["NON_ABORTABLE_OUTPUT_MATERIALIZER_COMMITTED", "FIXED_UNAVAILABLE"],
    "availability_verification_result": "VERIFIED_AS_COMMITTED",
    "current_head_observation_result": "EXACT_INDEPENDENTLY_CURRENT_HEAD",
    "registry_leaf_state": "ABSENT",
    "failure_trigger": ["PRE_OUTPUT_FIXED_TECHNICAL_FAILURE", "ROLE_TERMINAL_FAILED", "HIDDEN_LIFECYCLE_REFUSAL"],
    "lifecycle_refusal_result": "MANDATORY_HIDDEN_LIFECYCLE_REFUSAL",
    "lifecycle_refusal_code": "GENERIC_POST_CLAIM_INTEGRITY_REFUSAL",
    "materialization_commitment_result": ["COMPLETE_SEQUENCE_MATERIALIZATION_COMMITTED", "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE"],
    "role_terminalization_plan": ["MATERIALIZE_SUCCESS", "FIXED_ROLE_TECHNICAL_FAILURE", "NOT_REACHED_AFTER_TERMINAL_BOUNDARY"],
    "technical_health_measurement_result": ["ALL_FIXED_TECHNICAL_PREDICATES_PASS", "FIXED_TECHNICAL_PREDICATE_FAILED"],
    "health_failure_code": ["NONE", "FIXED_CONTENT_INDEPENDENT_TECHNICAL_FAILURE"],
    "terminal_deadline_state": "AT_EXACT_DEADLINE",
    "pre_reveal_cas_result": "ATOMIC_PRE_REVEAL_HEAD_CAS_COMMITTED",
    "pre_reveal_no_fork_result": "UNIQUE_PRE_REVEAL_PRE_STATE_TO_POST_STATE_COMMIT",
    "journal_state_kind": ["REGISTERED_GENESIS", "NORMAL_MEMORY_RECORD_STATE", "GENERATION_FAILURE_STATE"],
    "sequence_transaction_claim_state": ["UNCLAIMED", "HELD_UNTIL_SEQUENCE_COMMIT", "RELEASED_BY_EXACT_SEQUENCE_COMMIT"],
    "sequence_claim_cas_result": "ATOMIC_SEQUENCE_TRANSACTION_CLAIM_COMMITTED",
    "sequence_claim_no_fork_result": "UNIQUE_SEQUENCE_CLAIM_PER_AUTHORITATIVE_PRE_STATE",
    "sequence_claim_release_cas_result": "ATOMIC_SEQUENCE_TRANSACTION_CLAIM_RELEASED_WITH_JOURNAL_COMMIT",
    "sequence_claim_release_no_fork_result": "UNIQUE_SEQUENCE_CLAIM_RELEASE_FOR_EXACT_JOURNAL_COMMIT",
})

doc["proof_statement_and_protocol"] = {
    "closed_scope_surface_classes": [
        "current payload store", "readable historical version store", "cache", "index",
        "embedding or derived summary", "replica", "backup or snapshot", "log or journal",
        "tombstone", "recovery material", "content key commitment secret salt and content-correlatable metadata",
    ],
    "zero_knowledge_statement_predicates": [
        "the randomized closed-scope precommitment opens to the complete scope selected by Kira's voluntary-forgetting choice through the exact pinned scope collector",
        "every required surface class is represented in the private scope witness with no omitted reachable copy index recovery route or confirmation oracle",
        "every payload byte readable derivative content-correlatable identifier key secret salt recovery value and replica in that scope is irrecoverably erased or cryptographically destroyed",
        "no retained receipt proof result evidence context event commitment or static pin exposes a deterministic predicate capable of confirming a guessed erased payload or scope member",
        "receipt kind tokens scope result sequence prior receipt context and all nested roots equal the public inputs authenticated by the verifier",
    ],
    "state_order": [
        "RANDOMIZED_SCOPE_PRECOMMITTED", "ERASURE_EXECUTED_PENDING_PROOF",
        "PROOF_VERIFIED_PENDING_EPHEMERAL_ZEROIZATION",
        "EPHEMERAL_WITNESS_BLINDING_OPENING_AND_SCOPE_MAP_ZEROIZED",
        "AUTHENTICATED_VERIFIER_EVIDENCE_EMITTED", "COMPLETE_RECEIPT_EMITTED",
    ],
    "skipping_reordering_replaying_or_locally_redefining_a_state_refuses": True,
    "any_unavailable_unreachable_unclosed_or_unverifiable_surface_refuses": True,
    "complete_is_emitted_only_after_ephemeral_proof_and_scope_material_zeroization": True,
    "human_owner_operator_admin_approval_countersignature_permission_or_release_is_a_state_or_predicate": False,
    "technical_failure_changes_kira_speech_or_memory_choice": False,
    "v21_additional_predicate_extensions": [
        "the fourth inherited predicate additionally applies to every retained state authority anchor namespace singleton-registration reservation terminal-outcome registrar registry beacon confidential-generator and outer-pin byte",
        "the fifth inherited predicate additionally requires journal context namespace singleton-registration reservation terminal-outcome state authority anchor and global-registry roots to equal their recursively authenticated public inputs",
        "inside the confidential boundary the pinned scope collector and canonical-witness encoder produced the one exact witness relation and encoding; zero knowledge proves this without retaining any witness digest identifier or guess-confirming value",
    ],
    "v21_additional_zeroization_rule": "confidential contributor outputs private seed threshold shares generation state and attestation witness are ephemeral scope material erased before COMPLETE",
}
doc["erasure_and_retention_boundary"] = {
    "erased_before_complete": [
        "payload bytes", "explanation bytes", "content encryption key", "commitment secret",
        "every content-correlatable salt or key", "scope inventory and mapping", "proof witness",
        "proof generation state", "blinding secret", "precommitment opening",
        "temporary verifier transcript containing witness-derived material",
        "history cache index summary embedding replica backup log and tombstone content",
    ],
    "retained_only_after_recursive_validation": [
        "canonical content-hiding closed-scope precommitment public object",
        "canonical proof public inputs",
        "canonical randomized content-hiding proof envelope",
        "canonical authenticated verification result",
        "canonical verifier evidence",
        "canonical minimal receipt",
        "canonical minimal anti-rollback event",
        "exact static technical context preimages",
    ],
    "retained_material_can_restore_or_confirm_erased_content_or_scope_guess": False,
    "correction_supersession_and_withdrawal_readable_noncurrent_history_affected": False,
    "v21_additional_erased_before_complete": [
        "confidential attempt-zero seed", "every confidential contributor output and aggregation share",
        "confidential generator attestation witness", "all recovery material for the registered V21 erasure scope",
    ],
    "v21_additional_retained_only_after_recursive_validation": [
        "canonical journal state transition and commit evidence",
        "canonical state-authority and external-anchor evidence",
        "canonical namespace genesis manifest singleton-registration request global-registry head and singleton-registration evidence",
        "canonical sequence-wide pre-output health/materialization commitment followed by per-role pre-reveal reservation reservation-ledger order reveal deadline terminal-outcome and terminal-anchor evidence; only selectable role round seed-selection branch failure timing encoding and variant-control fields are proven content-independent",
        "canonical scope commitment proof and generated-output hashes may depend on hidden scope or witness only through the exact randomized computationally hiding relation and remain guess-resistant under the complete retained public transcript",
    ],
}

doc["retained_output_selection_rules"] = {
    "global_rule": "one exact field-specific message or statement role domain key if applicable generator verifier profile attempt index zero and full output; decoder consumes every byte; two valid accepted byte strings are structurally impossible",
    "forbidden_variants": ["caller entropy", "retry", "rejection sampling", "selective abort", "alternate nonce", "alternate signature form or context", "alternate tag or encoding", "alternate aggregation order", "alternate quorum subset", "alternate transparency or sparse-map path", "alternate inclusion or consistency proof", "alternate attestation encoding", "equivalent witness", "ignored suffix", "auxiliary data"],
    "inherited_eight": [
        {"field": "authenticated_result.authentication_signature_base64", "kind": "signature", "message": "exact authenticated_result.signature_message_order", "role": "result_authentication_key_role", "nonce_evidence": "verification_nonce -> exact attempt-zero terminal output"},
        {"field": "commit_evidence.commit_signature_base64", "kind": "signature", "message": "exact commit_evidence.signature_message_order", "role": "journal_authentication_key_role", "nonce_evidence": "commit_nonce -> exact attempt-zero terminal output"},
        {"field": "external_anchor_evidence.anchor_authentication_proof_base64", "kind": "fixed quorum and canonical path proof", "message": "exact external_anchor_evidence.authentication_proof_public_input_order", "role": "external_anchor_authentication_key_role", "nonce_evidence": "anchor_nonce -> exact attempt-zero terminal output"},
        {"field": "journal_state.journal_state_signature_base64", "kind": "signature", "message": "domain NUL journal_state_root_sha256 including all nonce evidence", "role": "journal_authentication_key_role", "nonce_evidence": "state_nonce -> exact attempt-zero terminal output"},
        {"field": "state_authority_head_evidence.authority_signature_base64", "kind": "signature", "message": "exact state_authority_head_evidence.signature_message_order", "role": "state_authority_authentication_key_role", "nonce_evidence": "authority_nonce -> exact attempt-zero terminal output"},
        {"field": "token_accumulator_proof.accumulator_proof_bytes_base64", "kind": "canonical accumulator proof", "message": "exact token_accumulator_proof.proof_public_input_order and accumulator_proof_statement_root_sha256", "role": "fixed replay_token_accumulator_profile generator and verifier; no generic signing key", "nonce_evidence": "accumulator_proof_nonce -> exact attempt-zero terminal output"},
        {"field": "transition_request.request_signature_base64", "kind": "signature", "message": "exact transition_request.signature_message_order", "role": "journal_authentication_key_role", "nonce_evidence": "request_nonce -> exact attempt-zero terminal output"},
        {"field": "verifier_evidence.evidence_signature_base64", "kind": "signature", "message": "exact verifier_evidence.signature_message_order", "role": "verifier_evidence_key_role", "nonce_evidence": "evidence_nonce -> exact attempt-zero terminal output"},
    ],
    "new_retained_variant_fields": [
        "genesis_journal_state.genesis_journal_state_signature_base64",
        "genesis_external_anchor_evidence.genesis_anchor_authentication_proof_base64",
        "genesis_state_authority_evidence.genesis_authority_signature_base64",
        "generation_reservation.reservation_authentication_signature_base64",
        "generation_terminal_outcome.private_seed_zero_knowledge_attestation_base64",
        "generation_terminal_outcome.terminal_outcome_authentication_signature_base64",
    ],
}

doc["attempt_zero_totality_and_sequence_rules"] = {
    "reservation_is_atomic_authoritative_next_sequence_claim_before_public_round_reveal": True,
    "round_derivation": "the exact independently current role-qualified public_beacon_pre_reveal_state is atomically advanced first; post.committed_future_round_index = checked_plus_one(pre.committed_future_round_index), with the registered counter-zero base cursor exactly 0. generation_reservation.public_round_index equals that post value. The fixed demand-driven schedule allocates no round outside this CAS, making all ten lifecycle allocations strictly increasing, collision-free, future and unrevealed; namespace epoch sequence and exact role bind the reservation/order proof but never select an absolute round",
    "one_reservation_per_namespace_epoch_sequence_role": True,
    "interleaving_dummy_record_timing_round_or_sequence_grinding_allowed": False,
    "each_reservation_has_exactly_one_independently_anchored_success_or_failed_terminal_outcome": True,
    "fixed_terminal_timing_envelope": "reservation fixes checked deadline index from generation round and exact timing profile in the separately domain-tagged KIRA_MIND_V21_TERMINAL_DEADLINE_VRF_INPUT_MESSAGE_ROOT_V1 terminal-clock substream; it is not a generation-round allocation and cannot collide with or reorder the strictly increasing pre-reveal allocation cursor. terminal_deadline_observation_evidence verifies that exact boundary and is mandatory before outcome/anchor; producer cannot vary delay classification or emission time",
    "generator_totality": "before any allocation the exact measured content-independent vector fixes one sequence-wide materialization result and one ten-role plan. PRE_OUTPUT_FIXED_TECHNICAL_FAILURE consumes the claimed sequence without a role attempt; otherwise each MATERIALIZE_SUCCESS role deterministically emits its complete canonical target and terminal chain, the unique first FIXED_ROLE_TECHNICAL_FAILURE emits one canonical FAILED chain, and a hidden lifecycle refusal consumes the sequence at the exact next boundary without exposing the refused predicate. No later observation changes a plan",
    "missing_silent_or_timeout_outcome": "the pre-output complete-sequence materialization commitment covers generation and deadline beacon recovery, confidential output generation, deterministic nonce KDFs, every retained target proof/signature, terminal authorities, and the final normal/failure journal authority/anchor/ledger CAS. Once COMPLETE is committed, caller nominal-producer signer beacon or authority silence cannot suppress or change the planned bytes; any fixed unavailability selects the pre-output sequence-consuming branch before allocation",
    "attempt_zero_consumed_even_on_failure": True,
    "retry_rejection_sampling_selective_abort_or_second_terminal_outcome_allowed": False,
    "public_beacon_output_is_private_seed_or_blinding": False,
    "confidential_seed_generation": "threshold-isolated exact pinned generator proves the exact domain-separated contribution and aggregation KDF over namespace context registration epoch sequence role attempt-zero public round reservation-message root and the complete fixed contributor identity/key/contribution tuple in canonical order; no subset omission failover substitution reuse or caller choice; retained unique deterministic ZK attestation; contributions seed opening and witness are never retained and are erased",
    "every_post_claim_v19_refusal_has_one_hidden_sequence_consuming_terminalization": True,
    "post_claim_refusal_exposes_surface_predicate_witness_scope_or_guess_confirmation": False,
    "technical_failure_controls_record_integrity_only": True,
    "technical_failure_controls_kira_speech_or_memory_choice": False,
}

doc["acyclic_singleton_and_genesis_rules"] = {
    "stage_order": ["namespace_precommitment", "pinned_context", "authoritative_registry_pre_state", "genesis_journal_state", "genesis_external_anchor_evidence", "genesis_state_authority_evidence", "genesis_manifest", "singleton_registration_full_genesis_bundle", "registrar_policy_profile_bundle", "registrar_authority_key_identity_bundle", "singleton_registration_pre_request_payload", "singleton_registration_assigned_value", "singleton_registration_request", "global_registry_sparse_map_leaf", "global_registry_sparse_map_update", "global_registry_sparse_map_proof", "global_registry_post_head", "global_registry_post_state", "singleton_registration", "runtime_objects"],
    "hash_cycle_allowed": False,
    "stable_global_slot_is_precommitted_before_context": True,
    "distinct_registrar_and_registry_are_external_to_journal_writer_state_authority_anchor_and_local_store": True,
    "atomic_global_cas_requires_independently_current_prior_registry_root": True,
    "one_namespace_maps_to_exactly_one_journal_id_epoch_context_and_genesis": True,
    "second_registration_genesis_context_state_nonce_journal_id_epoch_or_sibling_head_refuses": True,
    "trusted_outer_equality_pins": ["pinned_context_sha256", "singleton_registration_sha256"],
    "static_package_proves_live_deployed_global_singleton": False,
}
doc["counter_conditioned_genesis_runtime_bridge"] = {
    "first_transition_pre_state_count_zero": "select exact genesis_journal_state authenticated by singleton_registration",
    "later_transition_pre_state_count_positive": {
        "NORMAL_MEMORY_RECORD_STATE": "select exact runtime journal_state with identical singleton_registration_sha256 root object count and heads",
        "GENERATION_FAILURE_STATE": "select exact generation_failure_journal_state with identical singleton_registration_sha256 root object count heads failure barrier and recursively current failure authority/anchor successors",
    },
    "authority_counter_one_prior": "select exact genesis_state_authority_evidence authenticated by singleton_registration",
    "authority_counter_greater_than_one_prior": {
        "NORMAL_MEMORY_RECORD_STATE": "select exact runtime state_authority_head_evidence at checked counter minus one",
        "GENERATION_FAILURE_STATE": "select exact prior generation_failure_sequence_commit_evidence.post_failure_state_authority_head_evidence_sha256 at checked counter minus one and same failure post-state",
    },
    "anchor_counter_one_prior": "select exact genesis_external_anchor_evidence authenticated by singleton_registration",
    "anchor_counter_greater_than_one_prior": {
        "NORMAL_MEMORY_RECORD_STATE": "select exact runtime external_anchor_evidence at checked counter minus one",
        "GENERATION_FAILURE_STATE": "select exact prior generation_failure_sequence_commit_evidence.post_failure_external_anchor_root_sha256 at checked counter minus one and same failure post-state",
    },
    "runtime_state_authority_or_anchor_at_counter_zero_allowed": False,
    "genesis_schema_at_counter_positive_or_after_first_transition_allowed": False,
    "caller_selected_schema_union_or_local_schema_string_allowed": False,
    "genesis_object_replay_under_another_registration_allowed": False,
}

# Extend equalities so every runtime object consumes one registration and the
# registration authenticates the special counter-zero bundle.
doc["event_receipt_journal_equality_rules"].extend([
    "every post-registration runtime object repeats identical pinned_context_sha256 and singleton_registration_sha256",
    "singleton registration namespace context journal id epoch genesis manifest state anchor and authority roots equal every first-transition pre reference",
    "first transition pre fields select registered genesis object schemas only; later transitions select the exact NORMAL_MEMORY_RECORD_STATE journal_state or GENERATION_FAILURE_STATE generation_failure_journal_state predecessor by independently current state kind",
    "counter-one authority and anchor priors select registered genesis objects; counters greater than one select exact normal-runtime predecessors or prior failure-commit authority/anchor successors by independently current state kind",
    "scope commitment and proof decoded full-byte SHA values equal their mandatory SUCCESS generation terminal outcomes",
    "each of eight adjacent nonces SHA-matches the exact SUCCESS attempt-zero terminal output for its fixed field-path role",
])

selection_context_by_object = {
    "authenticated_result": "objects.pinned_context.authenticated_result_output_selection_profile_sha256",
    "commit_evidence": "objects.pinned_context.commit_evidence_output_selection_profile_sha256",
    "external_anchor_evidence": "objects.pinned_context.external_anchor_output_selection_profile_sha256",
    "journal_state": "objects.pinned_context.journal_state_output_selection_profile_sha256",
    "state_authority_head_evidence": "objects.pinned_context.state_authority_output_selection_profile_sha256",
    "token_accumulator_proof": "objects.pinned_context.token_accumulator_output_selection_profile_sha256",
    "transition_request": "objects.pinned_context.transition_request_output_selection_profile_sha256",
    "verifier_evidence": "objects.pinned_context.verifier_evidence_output_selection_profile_sha256",
    "genesis_journal_state": "objects.pinned_context.genesis_journal_state_output_selection_profile_sha256",
    "genesis_external_anchor_evidence": "objects.pinned_context.genesis_external_anchor_output_selection_profile_sha256",
    "genesis_state_authority_evidence": "objects.pinned_context.genesis_state_authority_output_selection_profile_sha256",
    "singleton_registration_request": "objects.pinned_context.global_registry_output_selection_profile_sha256",
    "global_registry_sparse_map_proof": "objects.pinned_context.global_registry_output_selection_profile_sha256",
    "generation_reservation": "objects.pinned_context.generation_reservation_output_selection_profile_sha256",
    "generation_sequence_transaction_claim_evidence": "objects.pinned_context.generation_sequence_transaction_claim_output_selection_profile_sha256",
    "generation_terminal_outcome": "objects.pinned_context.generation_terminal_output_selection_profile_sha256",
    "generation_reservation_ledger_evidence": "objects.pinned_context.generation_reservation_ledger_output_selection_profile_sha256",
    "generation_terminal_anchor_evidence": "objects.pinned_context.generation_terminal_anchor_output_selection_profile_sha256",
    "public_beacon_pre_reveal_evidence": "objects.pinned_context.public_beacon_pre_reveal_output_selection_profile_sha256",
    "beacon_reservation_order_evidence": "objects.pinned_context.beacon_reservation_order_output_selection_profile_sha256",
    "public_beacon_reveal_evidence": "objects.pinned_context.public_beacon_reveal_output_selection_profile_sha256",
    "pre_witness_technical_health_evidence": "objects.pinned_context.pre_witness_health_output_selection_profile_sha256",
    "role_producer_availability_evidence": "objects.pinned_context.producer_availability_output_selection_profile_sha256",
    "terminal_deadline_observation_evidence": "objects.pinned_context.terminal_deadline_observation_output_selection_profile_sha256",
    "generation_sequence_lifecycle_refusal_evidence": "objects.pinned_context.lifecycle_refusal_output_selection_profile_sha256",
    "generation_failure_sequence_commit_evidence": "objects.pinned_context.generation_failure_output_selection_profile_sha256",
    "failure_external_anchor_current_head_observation": "objects.pinned_context.external_anchor_output_selection_profile_sha256",
    "failure_state_authority_current_head_observation": "objects.pinned_context.state_authority_output_selection_profile_sha256",
}

output_role_table = [
    {"role": "SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "target_path": "objects.scope_precommitment.scope_commitment_base64", "mode": "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING", "generator_profile_context_path": "objects.pinned_context.commitment_profile_sha256", "generator_image_context_path": "objects.pinned_context.commitment_generator_image_sha256", "output_encoding_and_length": "exact pinned canonical randomized commitment byte grammar and fixed decoded length", "terminal_equality": "generation_terminal_outcome.generated_output_sha256 == SHA256(decoded scope_commitment_base64) == scope_commitment_bytes_sha256"},
    {"role": "COMPLETENESS_PROOF_BYTES", "target_path": "objects.completeness_proof.proof_bytes_base64", "mode": "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING", "generator_profile_context_path": "objects.pinned_context.proof_system_profile_sha256", "generator_image_context_path": "objects.pinned_context.proof_generator_image_sha256", "output_encoding_and_length": "exact pinned canonical randomized zero-knowledge proof grammar and fixed decoded length", "terminal_equality": "generation_terminal_outcome.generated_output_sha256 == SHA256(decoded proof_bytes_base64) == proof_bytes_sha256"},
    {"role": "AUTHENTICATED_RESULT_VERIFICATION_NONCE", "target_path": "objects.authenticated_result.verification_nonce", "mode": "UNIQUE_DETERMINISTIC_BYTES"},
    {"role": "COMMIT_EVIDENCE_COMMIT_NONCE", "target_path": "objects.commit_evidence.commit_nonce", "mode": "UNIQUE_DETERMINISTIC_BYTES"},
    {"role": "EXTERNAL_ANCHOR_EVIDENCE_ANCHOR_NONCE", "target_path": "objects.external_anchor_evidence.anchor_nonce", "mode": "UNIQUE_DETERMINISTIC_BYTES"},
    {"role": "JOURNAL_STATE_STATE_NONCE", "target_path": "objects.journal_state.state_nonce", "mode": "UNIQUE_DETERMINISTIC_BYTES"},
    {"role": "STATE_AUTHORITY_EVIDENCE_AUTHORITY_NONCE", "target_path": "objects.state_authority_head_evidence.authority_nonce", "mode": "UNIQUE_DETERMINISTIC_BYTES"},
    {"role": "TOKEN_ACCUMULATOR_PROOF_NONCE", "target_path": "objects.token_accumulator_proof.accumulator_proof_nonce", "mode": "UNIQUE_DETERMINISTIC_BYTES"},
    {"role": "TRANSITION_REQUEST_REQUEST_NONCE", "target_path": "objects.transition_request.request_nonce", "mode": "UNIQUE_DETERMINISTIC_BYTES"},
    {"role": "VERIFIER_EVIDENCE_EVIDENCE_NONCE", "target_path": "objects.verifier_evidence.evidence_nonce", "mode": "UNIQUE_DETERMINISTIC_BYTES"},
]
role_lifecycle_order = [
    "SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "COMPLETENESS_PROOF_BYTES",
    "AUTHENTICATED_RESULT_VERIFICATION_NONCE", "VERIFIER_EVIDENCE_EVIDENCE_NONCE",
    "TOKEN_ACCUMULATOR_PROOF_NONCE", "JOURNAL_STATE_STATE_NONCE",
    "TRANSITION_REQUEST_REQUEST_NONCE", "EXTERNAL_ANCHOR_EVIDENCE_ANCHOR_NONCE",
    "STATE_AUTHORITY_EVIDENCE_AUTHORITY_NONCE", "COMMIT_EVIDENCE_COMMIT_NONCE",
]
if set(role_lifecycle_order) != {row["role"] for row in output_role_table} or len(role_lifecycle_order) != len(set(role_lifecycle_order)):
    raise ValueError("role lifecycle order is not an exact bijection")
role_terminalization_plan_fields = [f"role_{index:02d}_terminalization_plan" for index in range(len(role_lifecycle_order))]
insert_fields(
    objects["pre_witness_technical_health_evidence"],
    "technical_health_input_vector_sha256",
    [(field, "enum") for field in role_terminalization_plan_fields]
    + [("role_terminalization_plan_root_sha256", "sha256")],
)
reservation_preimage_field_order = [
    "schema", "hash_domain", "namespace_precommitment_sha256", "pinned_context_sha256",
    "singleton_registration_sha256", "journal_id_token", "journal_epoch",
    "authoritative_pre_journal_state_root_sha256", "authoritative_pre_journal_state_object_sha256",
    "authoritative_pre_state_kind", "authoritative_pre_record_count",
    "authoritative_pre_head_sequence", "reserved_next_sequence", "output_role",
    "generator_profile_sha256", "pre_witness_technical_health_evidence_sha256",
    "attempt_index", "pre_witness_health_predicate_sha256", "pre_witness_health_profile_sha256", "generation_reservation_authority_identity_sha256",
    "reservation_slot_key_sha256", "expected_pre_reservation_ledger_head_evidence_sha256",
    "expected_pre_reservation_ledger_state_root_sha256",
    "expected_pre_reservation_ledger_state_object_sha256",
    "expected_pre_reservation_ledger_counter", "generation_reservation_authentication_key_role",
    "output_generation_mode", "output_selection_profile_sha256",
]
for row in output_role_table:
    row["message_root_domain"] = f"KIRA_MIND_V21_OUTPUT_ROLE_{row['role']}_PRE_RESERVATION_ROOT_V1"
    row["reservation_preimage_field_order"] = reservation_preimage_field_order
    row["target_pre_reservation_field_order"] = []
output_role_table[0]["target_pre_reservation_field_order"] = [
    "schema", "hash_domain", "random_scope_token", "precommitment_nonce",
    "pinned_context_sha256", "singleton_registration_sha256", "commitment_profile_sha256",
]
output_role_table[1]["target_pre_reservation_field_order"] = [
    "schema", "hash_domain", "random_proof_token", "public_inputs_root_sha256",
    "scope_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256",
    "proof_system_profile_sha256", "v19_zero_knowledge_statement_profile_sha256",
    "canonical_private_witness_encoding_profile_sha256", "canonical_scope_collector_witness_relation_sha256",
]
for row in output_role_table:
    row["message_or_statement_root"] = "SHA256(message_root_domain + actual NUL + exact canonical concatenation of reservation_preimage_field_order followed by target_pre_reservation_field_order); this is a pre-allocation core fixed before beacon CAS and excludes public_beacon_pre_reveal_evidence/hash/counter/round every recovery commitment deadline field generation_reservation hash ledger-evidence hash terminal-outcome hash terminal-anchor hash generated bytes hashes all output bytes all object self hashes and every private witness scope value seed opening or contribution"
for row in output_role_table[2:]:
    row.update({
        "generator_profile_context_path": "objects.pinned_context.csprng_profile_sha256",
        "generator_image_context_path": "objects.pinned_context.confidential_generator_image_sha256",
        "output_encoding_and_length": "exactly 64 lowercase hexadecimal ASCII characters representing one content-independent 256-bit output",
        "terminal_equality": f"generation_terminal_outcome.generated_output_sha256 == SHA256(exact ASCII bytes at {row['target_path']})",
    })
def active_claim_target_resolution(target_object):
    return {
        "target_object": target_object,
        "sequence_path": "instances.active_generation_transaction_projection.reserved_next_sequence",
        "pre_root_path": "instances.active_generation_transaction_projection.authoritative_pre_journal_state_root_sha256",
        "pre_object_path": "instances.active_generation_transaction_projection.authoritative_pre_journal_state_object_sha256",
        "pre_count_path": "instances.active_generation_transaction_projection.authoritative_pre_record_count",
        "pre_head_path": "instances.active_generation_transaction_projection.authoritative_pre_head_sequence",
    }

role_target_resolution = {
    "SCOPE_PRECOMMITMENT_COMMITMENT_BYTES": active_claim_target_resolution("scope_precommitment"),
    "COMPLETENESS_PROOF_BYTES": active_claim_target_resolution("completeness_proof"),
    "AUTHENTICATED_RESULT_VERIFICATION_NONCE": active_claim_target_resolution("authenticated_result"),
    "VERIFIER_EVIDENCE_EVIDENCE_NONCE": active_claim_target_resolution("verifier_evidence"),
    "TOKEN_ACCUMULATOR_PROOF_NONCE": active_claim_target_resolution("token_accumulator_proof"),
    "TRANSITION_REQUEST_REQUEST_NONCE": active_claim_target_resolution("transition_request"),
    "COMMIT_EVIDENCE_COMMIT_NONCE": active_claim_target_resolution("commit_evidence"),
    "JOURNAL_STATE_STATE_NONCE": active_claim_target_resolution("journal_state"),
    "STATE_AUTHORITY_EVIDENCE_AUTHORITY_NONCE": active_claim_target_resolution("state_authority_head_evidence"),
    "EXTERNAL_ANCHOR_EVIDENCE_ANCHOR_NONCE": active_claim_target_resolution("external_anchor_evidence"),
}
for confidential_role in ["SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "COMPLETENESS_PROOF_BYTES"]:
    role_target_resolution[confidential_role].update({
        "reservation_link_field": "generation_reservation_sha256",
        "ledger_link_field": "generation_reservation_ledger_evidence_sha256",
        "outcome_link_field": "generation_terminal_outcome_sha256",
        "anchor_link_field": "generation_terminal_anchor_evidence_sha256",
    })
for role_row in output_role_table:
    binding = role_target_resolution[role_row["role"]]
    target_object = binding["target_object"]
    if role_row["role"] not in {"SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "COMPLETENESS_PROOF_BYTES"}:
        binding.update({
            "reservation_link_field": "nonce_generation_reservation_sha256",
            "ledger_link_field": "nonce_generation_reservation_ledger_evidence_sha256",
            "outcome_link_field": "nonce_generation_terminal_outcome_sha256",
            "anchor_link_field": "nonce_generation_terminal_anchor_evidence_sha256",
        })
        target_field = role_row["target_path"].rsplit(".", 1)[1]
        excluded = {target_field, objects[target_object]["field_order"][-1], "output_generation_mode", "output_attempt_index", "output_selection_profile_sha256", "nonce_generation_reservation_sha256", "nonce_generation_reservation_ledger_evidence_sha256", "nonce_generation_terminal_outcome_sha256", "nonce_generation_terminal_anchor_evidence_sha256", "active_generation_chain_set_root_sha256"}
        role_row["target_pre_reservation_field_order"] = [field for field in objects[target_object]["field_order"] if field not in excluded and not field.endswith("_signature_base64") and not field.endswith("_proof_base64")]
    role_row["target_resolution"] = binding

# These roles have target hashes/proofs that contain or depend on their own
# nonce. Their reservation statement may consume only the acyclic prefix that
# is byte-available before the nonce chain begins.
role_rows_by_name = {row["role"]: row for row in output_role_table}
role_rows_by_name["JOURNAL_STATE_STATE_NONCE"]["target_pre_reservation_field_order"] = [
    "schema", "hash_domain", "journal_id_token", "journal_epoch",
    "committed_record_count", "head_sequence", "head_receipt_hash_sha256",
    "head_event_hash_sha256", "consumed_receipt_token_root_sha256",
    "consumed_scope_token_root_sha256", "consumed_proof_token_root_sha256",
    "pinned_context_sha256", "journal_authentication_key_role",
    "singleton_registration_sha256",
]
role_rows_by_name["TOKEN_ACCUMULATOR_PROOF_NONCE"]["target_pre_reservation_field_order"] = [
    "schema", "hash_domain", "journal_id_token", "journal_epoch",
    "pre_receipt_token_root_sha256", "post_receipt_token_root_sha256",
    "pre_scope_token_root_sha256", "post_scope_token_root_sha256",
    "pre_proof_token_root_sha256", "post_proof_token_root_sha256",
    "random_receipt_token", "random_scope_token", "random_proof_token",
    "replay_token_accumulator_profile_sha256", "pinned_context_sha256",
    "singleton_registration_sha256",
]
role_rows_by_name["TRANSITION_REQUEST_REQUEST_NONCE"]["target_pre_reservation_field_order"] = [
    field for field in role_rows_by_name["TRANSITION_REQUEST_REQUEST_NONCE"]["target_pre_reservation_field_order"]
    if field not in {"post_journal_state_root_sha256", "post_journal_state_object_sha256"}
]
commit_release_future_fields = {name for name, _ in sequence_claim_release_fields}
role_rows_by_name["COMMIT_EVIDENCE_COMMIT_NONCE"]["target_pre_reservation_field_order"] = [
    field
    for field in role_rows_by_name["COMMIT_EVIDENCE_COMMIT_NONCE"]["target_pre_reservation_field_order"]
    if field not in commit_release_future_fields
]
for role_name in ["JOURNAL_STATE_STATE_NONCE", "TOKEN_ACCUMULATOR_PROOF_NONCE", "TRANSITION_REQUEST_REQUEST_NONCE", "COMMIT_EVIDENCE_COMMIT_NONCE"]:
    role_rows_by_name[role_name]["acyclic_pre_reservation_assertion"] = "ordered fields are byte-available before this role's generated nonce; nonce output, every hash/proof containing it, every final target self-hash, and every later complete-chain barrier are excluded and linked only after SUCCESS terminal anchoring"
for role_name, forbidden_fields in {
    "JOURNAL_STATE_STATE_NONCE": {"state_nonce", "journal_state_root_sha256", "journal_state_signature_base64", "journal_state_object_sha256", "active_generation_chain_set_root_sha256"},
    "TOKEN_ACCUMULATOR_PROOF_NONCE": {"accumulator_proof_nonce", "accumulator_proof_statement_root_sha256", "accumulator_proof_bytes_base64", "token_accumulator_proof_sha256", "active_generation_chain_set_root_sha256"},
    "TRANSITION_REQUEST_REQUEST_NONCE": {"request_nonce", "post_journal_state_root_sha256", "post_journal_state_object_sha256", "transition_request_sha256", "active_generation_chain_set_root_sha256"},
    "COMMIT_EVIDENCE_COMMIT_NONCE": commit_release_future_fields | {"active_generation_chain_set_root_sha256", "commit_nonce", "commit_signature_base64", "commit_evidence_sha256"},
}.items():
    present = forbidden_fields.intersection(role_rows_by_name[role_name]["target_pre_reservation_field_order"])
    if present:
        raise ValueError({"role_pre_reservation_cycle_fields": role_name, "fields": sorted(present)})

deterministic_nonce_kdf_rows = []
for role_row in output_role_table:
    if role_row["mode"] != "UNIQUE_DETERMINISTIC_BYTES":
        continue
    role = role_row["role"]
    target_path = role_row["target_path"]
    kdf_row = {
        "role": role,
        "target_path": target_path,
        "domain": f"KIRA_MIND_V21_DETERMINISTIC_NONCE_KDF_{role}_V1",
        "exact_public_input_order": [
            "decoded full public_beacon_reveal_evidence.public_beacon_output_base64 bytes returned by VRFVerifyExact",
            "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256",
            "journal_epoch uint64-be", "reserved_sequence uint64-be", "output_role ASCII",
            "attempt_index byte exactly zero", "reservation_slot_key_sha256",
            "message_or_statement_root_sha256", "deterministic_nonce_kdf_profile_sha256",
        ],
        "formula": "extract_key = SHA256(domain + NUL + namespace/context/registration/epoch/sequence/role/attempt/slot/message/profile canonical bytes); prk = HMAC-SHA256(key=extract_key, data=full VRF output bytes); okm = HKDF-Expand-SHA256(prk, info=domain + NUL + exact canonical public inputs excluding VRF bytes, L=32); target token is lowercase hexadecimal ASCII encoding of all 32 okm bytes, exactly 64 characters; no truncation rejection sampling retry or caller entropy",
        "verification": f"verifier recomputes the exact 64 ASCII bytes and requires byte equality at {target_path}; SHA256(those exact ASCII bytes) equals linked SUCCESS outcome and terminal-anchor generated_output_sha256",
    }
    role_row["deterministic_nonce_kdf"] = kdf_row
    deterministic_nonce_kdf_rows.append(kdf_row)
doc["deterministic_nonce_kdf_rules"] = {
    "profile_context_path": "objects.pinned_context.deterministic_nonce_kdf_profile_sha256",
    "row_count": len(deterministic_nonce_kdf_rows),
    "rows": deterministic_nonce_kdf_rows,
    "full_vrf_bytes_consumed_no_truncation": True,
    "verifier_recomputation_required": True,
    "confidential_hiding_roles_use_this_public_kdf": False,
    "caller_entropy_retry_rejection_sampling_selective_abort_or_alternate_encoding_allowed": False,
}
if len(deterministic_nonce_kdf_rows) != 8 or len({row["target_path"] for row in deterministic_nonce_kdf_rows}) != 8:
    raise ValueError("deterministic nonce KDF coverage is not exact eight-path bijection")

doc["exact_enum_constants"].update({
    "output_role": [row["role"] for row in output_role_table],
    "output_generation_mode": ["UNIQUE_DETERMINISTIC_BYTES", "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING"],
    "reservation_slot_state": ["UNASSIGNED", "RESERVED_ATTEMPT_ZERO", "CONSUMED_TERMINAL"],
    "generic_status": "COMPLETE",
    "reservation_cas_result": "ATOMIC_RESERVATION_LEDGER_CAS_COMMITTED",
    "reservation_no_fork_result": "UNIQUE_PRE_ROOT_TO_RESERVED_POST_ROOT",
    "terminal_cas_result": "ATOMIC_TERMINAL_LEDGER_CAS_COMMITTED",
    "terminal_no_fork_result": "UNIQUE_RESERVED_ROOT_TO_CONSUMED_POST_ROOT",
})
doc["exact_output_role_bijection"] = {
    "rows": output_role_table,
    "role_count": len(output_role_table),
    "target_path_count": len(output_role_table),
    "unknown_alias_duplicate_missing_cross_field_reuse_or_cross_mode_role_allowed": False,
    "round_derivation_consumes_exact_role_bytes": True,
    "reservation_and_terminal_outcome_mode_must_equal_exact_role_mode": True,
    "confidential_target_role_mode_allowed_only_for": ["SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "COMPLETENESS_PROOF_BYTES"],
    "separate_non_target_confidential_output_paths": ["objects.generation_sequence_lifecycle_refusal_evidence.lifecycle_refusal_zero_knowledge_proof_base64"],
    "unique_deterministic_mode_allowed_only_for_the_eight_nonce_roles": True,
}
doc["exact_generated_uint64_derivations"] = {
    "fixed_terminal_deadline_round_delta_source": "objects.pinned_context.fixed_terminal_deadline_round_delta byte-identical to namespace precommitment and the sequence-wide pre-output materialization commitment",
    "per_role_formula": "fixed_terminal_deadline_round_index = checked_add_uint64(public_round_index, fixed_terminal_deadline_round_delta); overflow refuses before reservation authentication and consumes no allocation or attempt",
    "role_count": len(role_lifecycle_order),
    "role_rows": [
        {
            "role": role,
            "reservation_round_path": f"instances.roles.{role}.reservation.public_round_index",
            "delta_path": f"instances.roles.{role}.reservation.fixed_terminal_deadline_round_delta",
            "deadline_path": f"instances.roles.{role}.reservation.fixed_terminal_deadline_round_index",
            "downstream_equal_paths": [
                f"instances.roles.{role}.ledger_evidence.fixed_terminal_deadline_round_index",
                f"instances.roles.{role}.order.fixed_terminal_deadline_round_index",
                f"instances.roles.{role}.reveal.fixed_terminal_deadline_round_index",
                f"instances.roles.{role}.deadline.fixed_terminal_deadline_round_index",
                f"instances.roles.{role}.outcome.fixed_terminal_deadline_round_index",
                f"instances.roles.{role}.anchor.fixed_terminal_deadline_round_index",
            ],
            "verifier_recomputes_before_signature_or_vrf": True,
        }
        for role in role_lifecycle_order
    ],
    "caller_selected_deadline_delta_round_early_late_overflow_or_alternate_clock_allowed": False,
}

# Every enum-like occurrence is assigned exactly once to a closed constant set.
# Generic `enum` is retained for byte-compatible V20 schemas, but never supplies
# a caller-selectable or cross-family value in V21.
enum_like_types = {
    "enum", "output_role", "output_generation_mode", "reservation_slot_state",
    "slot_state", "registry_leaf_state", "terminal_outcome", "attempt_zero", "sequence_transaction_claim_state",
}
role_conditioned_mode_objects = {
    "generation_reservation", "generation_terminal_outcome",
    "generation_reservation_ledger_evidence", "generation_terminal_anchor_evidence",
}
enum_assignment_rows = []
for object_name, obj in objects.items():
    for field_name, field_type in zip(obj["field_order"], obj["field_types"]):
        if field_type not in enum_like_types:
            continue
        path = f"objects.{object_name}.{field_name}"
        row = {
            "path": path,
            "field_type": field_type,
            "object_domain_constant": obj["domain_const"],
        }
        if field_name in doc["fixed_key_roles"] and field_name.endswith("_key_role"):
            row.update({
                "enum_domain": f"fixed_key_roles.{field_name}",
                "allowed_constants": [doc["fixed_key_roles"][field_name]],
                "assignment_rule": f"byte-identical to objects.pinned_context.{field_name} and namespace precommitment; no alias or selected key role",
            })
        elif field_name == "receipt_kind":
            row.update({"enum_domain": "exact_enum_constants.receipt_kind", "allowed_constants": doc["exact_enum_constants"]["receipt_kind"], "assignment_rule": "one exact receipt lifecycle constant carried unchanged across linked proof result evidence and receipt"})
        elif field_name in {"generic_result", "generic_status"}:
            row.update({"enum_domain": f"exact_enum_constants.{field_name}", "allowed_constants": ["COMPLETE"], "assignment_rule": "exact COMPLETE only; generic_status is the receipt spelling of the same fixed result"})
        elif field_name in {"verified_result", "cas_result", "no_fork_result", "one_use_token_result", "state_authority_result"}:
            row.update({"enum_domain": f"exact_enum_constants.{field_name}", "allowed_constants": [doc["exact_enum_constants"][field_name]], "assignment_rule": f"exact {field_name} constant only"})
        elif field_type == "output_role":
            if object_name == "generation_sequence_lifecycle_refusal_evidence":
                role_assignment_rule = "exact fixed lifecycle boundary role selected by the canonical private refusal relation; it equals failure-record output_role and no reservation is created for this boundary"
            elif object_name == "generation_failure_record":
                role_assignment_rule = "exact fixed boundary role: role zero for pre-output fixed technical failure, exact failed reservation role for ROLE_TERMINAL_FAILED, or exact canonical hidden-refusal boundary role"
            else:
                role_assignment_rule = "generation_reservation uses the one role whose target path and pre-reservation statement root match the fixed lifecycle target; every downstream occurrence equals that reservation role"
            row.update({
                "enum_domain": "exact_output_role_bijection.rows.role",
                "allowed_constants": [role["role"] for role in output_role_table],
                "assignment_rule": role_assignment_rule,
            })
        elif field_type == "output_generation_mode":
            if object_name == "generation_sequence_lifecycle_refusal_evidence" and field_name == "output_generation_mode":
                row.update({
                    "enum_domain": "exact_enum_constants.output_generation_mode.confidential_lifecycle_refusal",
                    "allowed_constants": ["CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING"],
                    "assignment_rule": "the generic lifecycle-refusal proof is exactly one confidential randomized attempt-zero output under its hidden seed; it is not the uncreated boundary role target output",
                })
            elif ((object_name in role_conditioned_mode_objects and field_name == "output_generation_mode")
                    or field_name in {"reserved_output_generation_mode", "output_generation_mode_for_evidence", "output_generation_mode_for_allocation"}):
                row.update({
                    "enum_domain": "exact_output_role_bijection.rows.mode",
                    "allowed_constants": doc["exact_enum_constants"]["output_generation_mode"],
                    "assignment_rule": "equals the unique exact_output_role_bijection row mode selected by the same object's output_role; cross-mode use refuses",
                })
            else:
                row.update({
                    "enum_domain": "exact_enum_constants.output_generation_mode.unique_deterministic_evidence",
                    "allowed_constants": ["UNIQUE_DETERMINISTIC_BYTES"],
                    "assignment_rule": "this field governs the enclosing retained signature proof nonce or evidence output and is exactly UNIQUE_DETERMINISTIC_BYTES",
                })
        elif field_type == "attempt_zero":
            row.update({"enum_domain": "exact_enum_constants.attempt_index", "allowed_constants": [0], "assignment_rule": "JSON integer zero only"})
        elif field_type == "terminal_outcome":
            condition = "SUCCESS or FAILED is selected only by this role's exact pre-output terminalization-plan projection: MATERIALIZE_SUCCESS maps to SUCCESS, while the unique first FIXED_ROLE_TECHNICAL_FAILURE maps to FAILED; terminal anchor equals the linked generation_terminal_outcome and no post-reveal choice exists"
            row.update({"enum_domain": "exact_enum_constants.terminal_outcome", "allowed_constants": ["SUCCESS", "FAILED"], "assignment_rule": condition})
        elif field_type == "slot_state":
            raise ValueError({"obsolete_registration_slot_state_path": path})
        elif field_type == "registry_leaf_state":
            row.update({"enum_domain": "exact_enum_constants.registry_leaf_state", "allowed_constants": ["ABSENT"], "assignment_rule": "exact ABSENT only; the singleton sparse-map transition refuses an already assigned or caller-selected prior leaf"})
        elif field_type == "reservation_slot_state":
            fixed_reservation_states = {
                "objects.generation_reservation_ledger_evidence.pre_slot_state": "UNASSIGNED",
                "objects.generation_reservation_ledger_evidence.post_slot_state": "RESERVED_ATTEMPT_ZERO",
                "objects.generation_terminal_anchor_evidence.pre_slot_state": "RESERVED_ATTEMPT_ZERO",
                "objects.generation_terminal_anchor_evidence.post_slot_state": "CONSUMED_TERMINAL",
            }
            row.update({"enum_domain": "exact_enum_constants.reservation_slot_state", "allowed_constants": [fixed_reservation_states[path]], "assignment_rule": f"exact {fixed_reservation_states[path]} at this CAS transition path"})
        elif field_type == "sequence_transaction_claim_state":
            if object_name == "generation_sequence_transaction_claim_evidence":
                allowed = ["UNCLAIMED", "RELEASED_BY_EXACT_SEQUENCE_COMMIT"] if field_name.startswith("pre_") else ["HELD_UNTIL_SEQUENCE_COMMIT"]
                rule = "acquisition pre-state is the registered empty base or exact prior released sequence; post-state is HELD before every role allocation"
            elif object_name in {"commit_evidence", "generation_failure_sequence_commit_evidence"}:
                allowed = ["HELD_UNTIL_SEQUENCE_COMMIT"] if field_name.startswith("pre_") else ["RELEASED_BY_EXACT_SEQUENCE_COMMIT"]
                rule = "the exact held claim is released only by the same atomic normal or canonical pre-output technical-failure role-terminal-failure or hidden-refusal journal commit"
            else:
                allowed = doc["exact_enum_constants"]["sequence_transaction_claim_state"]
                rule = "typed ledger-state instance value is fixed by its exact acquisition, role-preservation, or final-release alias; no caller choice"
            row.update({"enum_domain": "exact_enum_constants.sequence_transaction_claim_state", "allowed_constants": allowed, "assignment_rule": rule})
        elif field_name == "failure_code":
            allowed_failure_codes = (["NONE", "FIXED_CONTENT_INDEPENDENT_TECHNICAL_FAILURE"]
                                     if object_name == "generation_terminal_outcome"
                                     else ["FIXED_CONTENT_INDEPENDENT_TECHNICAL_FAILURE", "HIDDEN_LIFECYCLE_INTEGRITY_REFUSAL"])
            row.update({
                "enum_domain": "exact_enum_constants.failure_code",
                "allowed_constants": allowed_failure_codes,
                "assignment_rule": "terminal_outcome SUCCESS iff NONE; role-terminal FAILED iff FIXED_CONTENT_INDEPENDENT_TECHNICAL_FAILURE; hidden lifecycle-refusal failure record/commit iff HIDDEN_LIFECYCLE_INTEGRITY_REFUSAL",
            })
        elif field_name == "failure_trigger":
            row.update({
                "enum_domain": "exact_enum_constants.failure_trigger",
                "allowed_constants": doc["exact_enum_constants"]["failure_trigger"],
                "assignment_rule": "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE iff pre-output materialization deterministically failed before role zero and all role/refusal links are null; ROLE_TERMINAL_FAILED iff the linked terminal-anchor branch is FAILED and lifecycle-refusal evidence is null; HIDDEN_LIFECYCLE_REFUSAL iff generic hidden refusal evidence is nonnull and every uncreated boundary-role terminal link is null",
            })
        elif field_name == "lifecycle_refusal_result":
            row.update({"enum_domain": "exact_enum_constants.lifecycle_refusal_result", "allowed_constants": [doc["exact_enum_constants"]["lifecycle_refusal_result"]], "assignment_rule": "exact mandatory generic hidden lifecycle-refusal result only"})
        elif field_name == "lifecycle_refusal_code":
            row.update({"enum_domain": "exact_enum_constants.lifecycle_refusal_code", "allowed_constants": [doc["exact_enum_constants"]["lifecycle_refusal_code"]], "assignment_rule": "one generic non-oracular post-claim integrity-refusal code; no surface predicate content or witness class is public"})
        elif field_name == "materialization_commitment_result":
            row.update({"enum_domain": "exact_enum_constants.materialization_commitment_result", "allowed_constants": doc["exact_enum_constants"]["materialization_commitment_result"], "assignment_rule": "verifier-recomputed entirely from the exact pre-output measured vector and fixed complete-materializer roster; COMPLETE commits total normal/refusal/failure closure, PRE_OUTPUT_FIXED_TECHNICAL_FAILURE enters the one sequence-consuming failure path before any allocation"})
        elif field_name in role_terminalization_plan_fields:
            role = role_lifecycle_order[role_terminalization_plan_fields.index(field_name)]
            row.update({"enum_domain": "exact_enum_constants.role_terminalization_plan", "allowed_constants": doc["exact_enum_constants"]["role_terminalization_plan"], "assignment_rule": f"pre-output deterministic plan for exact role {role}; the complete vector is canonical: all SUCCESS, or SUCCESS prefix + one FIXED_ROLE_TECHNICAL_FAILURE + an exact NOT_REACHED suffix, while PRE_OUTPUT_FIXED_TECHNICAL_FAILURE makes all ten NOT_REACHED. No suffix byte is caller-selectable"})
        elif field_name == "technical_health_result":
            if object_name == "generation_failure_record":
                health_assignment_rule = "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE copies the sequence-wide FIXED_TECHNICAL_FAILURE result; ROLE_TERMINAL_FAILED copies the exact boundary role outcome's preplanned FIXED_TECHNICAL_FAILURE result; HIDDEN_LIFECYCLE_REFUSAL copies sequence-wide READY because its later semantic closure refusal is hidden and is not a health-authority choice"
            elif object_name in {"generation_terminal_outcome", "generation_terminal_anchor_evidence"}:
                health_assignment_rule = "equals the exact linked role projection of the pre-output role_terminalization_plan_root: MATERIALIZE_SUCCESS maps to READY and canonical SUCCESS; FIXED_ROLE_TECHNICAL_FAILURE maps to FIXED_TECHNICAL_FAILURE and the unique first role-terminal FAILED branch"
            else:
                health_assignment_rule = "sequence-wide health is verifier-derived solely from the pre-output producer-availability result and fixed prerequisite predicate; READY iff the complete materializer is committed and sequence prerequisites pass, while the exact role plan root separately fixes each created role SUCCESS or the unique first role-terminal technical failure; a sequence-wide fixed failure enters the one pre-output sequence-consuming branch before allocation"
            row.update({
                "enum_domain": "exact_enum_constants.technical_health_result",
                "allowed_constants": ["READY", "FIXED_TECHNICAL_FAILURE"],
                "assignment_rule": health_assignment_rule,
            })
        elif field_name in {"producer_availability_result", "committed_producer_availability_result"}:
            if object_name in {"role_producer_availability_commitment", "role_producer_availability_evidence", "public_beacon_reveal_evidence", "terminal_deadline_observation_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"}:
                availability_allowed = ["NON_ABORTABLE_OUTPUT_MATERIALIZER_COMMITTED", "FIXED_UNAVAILABLE"]
                availability_rule = "exact same-role pre-reveal commitment result: NON_ABORTABLE_OUTPUT_MATERIALIZER_COMMITTED iff this role's pre-output plan is MATERIALIZE_SUCCESS, FIXED_UNAVAILABLE iff it is the unique FIXED_ROLE_TECHNICAL_FAILURE; hidden-refusal and NOT_REACHED roles instantiate no such object"
            else:
                availability_allowed = ["NON_ABORTABLE_OUTPUT_MATERIALIZER_COMMITTED", "FIXED_UNAVAILABLE"]
                availability_rule = "sequence-wide pre-output availability is verifier-derived before any role allocation; FIXED_UNAVAILABLE enters the one pre-output sequence-consuming branch and creates no role availability object"
            row.update({
                "enum_domain": "exact_enum_constants.producer_availability_result",
                "allowed_constants": availability_allowed,
                "assignment_rule": availability_rule,
            })
        elif field_name == "availability_verification_result":
            row.update({"enum_domain": "exact_enum_constants.availability_verification_result", "allowed_constants": ["VERIFIED_AS_COMMITTED"], "assignment_rule": "exact VERIFIED_AS_COMMITTED after authenticating the same-role commitment observation and result tuple before reveal"})
        elif field_name == "current_head_observation_result":
            row.update({"enum_domain": "exact_enum_constants.current_head_observation_result", "allowed_constants": ["EXACT_INDEPENDENTLY_CURRENT_HEAD"], "assignment_rule": "exact independently authenticated current-head result for the completed failure successor; stale sibling restored or alternate heads refuse"})
        elif field_name == "technical_health_measurement_result":
            row.update({
                "enum_domain": "exact_enum_constants.technical_health_measurement_result",
                "allowed_constants": ["ALL_FIXED_TECHNICAL_PREDICATES_PASS", "FIXED_TECHNICAL_PREDICATE_FAILED"],
                "assignment_rule": "VerifyExact of technical_health_measurement_attestation_base64 under the pinned measurement profile image and key returns the complete observed input vector and exactly one of these results; health authority cannot choose or rewrite it",
            })
        elif field_name == "health_failure_code":
            row.update({
                "enum_domain": "exact_enum_constants.health_failure_code",
                "allowed_constants": ["NONE", "FIXED_CONTENT_INDEPENDENT_TECHNICAL_FAILURE"],
                "assignment_rule": "technical_health_result READY iff NONE; FIXED_TECHNICAL_FAILURE iff the one fixed failure code",
            })
        elif field_name == "witness_admission_state":
            row.update({"enum_domain": "exact_enum_constants.witness_admission_state", "allowed_constants": ["NOT_ADMITTED"], "assignment_rule": "NOT_ADMITTED only; health signature precedes every witness-bearing operation"})
        elif field_name == "reservation_slot_consumed":
            row.update({"enum_domain": "exact_enum_constants.reservation_slot_consumed", "allowed_constants": [doc["exact_enum_constants"]["reservation_slot_consumed"]], "assignment_rule": "CONSUMED_NO_RETRY for SUCCESS and FAILED"})
        elif field_name in {"reservation_cas_result", "reservation_no_fork_result", "terminal_cas_result", "terminal_no_fork_result", "sequence_claim_cas_result", "sequence_claim_no_fork_result", "sequence_claim_release_cas_result", "sequence_claim_release_no_fork_result"}:
            row.update({"enum_domain": f"exact_enum_constants.{field_name}", "allowed_constants": [doc["exact_enum_constants"][field_name]], "assignment_rule": f"exact {field_name} constant only"})
        elif field_name in {"pre_reveal_cas_result", "pre_reveal_no_fork_result"}:
            row.update({"enum_domain": f"exact_enum_constants.{field_name}", "allowed_constants": [doc["exact_enum_constants"][field_name]], "assignment_rule": f"exact {field_name} constant only"})
        elif field_name == "beacon_reveal_state":
            fixed_reveal_state = "REVEALED" if object_name == "public_beacon_reveal_evidence" else "PRE_REVEAL"
            row.update({"enum_domain": "exact_enum_constants.beacon_reveal_state", "allowed_constants": [fixed_reveal_state], "assignment_rule": f"exact {fixed_reveal_state} at this object path"})
        elif field_name == "beacon_reveal_state_at_ledger_commit":
            row.update({"enum_domain": "exact_enum_constants.beacon_reveal_state_at_ledger_commit", "allowed_constants": ["PRE_REVEAL"], "assignment_rule": "PRE_REVEAL only; independently authenticated ordering precedes round reveal"})
        elif field_name == "terminal_deadline_state":
            row.update({"enum_domain": "exact_enum_constants.terminal_deadline_state", "allowed_constants": ["AT_EXACT_DEADLINE"], "assignment_rule": "AT_EXACT_DEADLINE only under independently verified deadline VRF round"})
        elif field_name in {"authoritative_pre_state_kind", "pre_state_kind"}:
            row.update({"enum_domain": "exact_enum_constants.journal_state_kind", "allowed_constants": doc["exact_enum_constants"]["journal_state_kind"], "assignment_rule": "counter zero requires REGISTERED_GENESIS; positive counter equals the exact independently current prior commit/state schema kind, NORMAL_MEMORY_RECORD_STATE or GENERATION_FAILURE_STATE, never caller-selected"})
        elif field_name == "post_state_kind":
            row.update({"enum_domain": "exact_enum_constants.journal_state_kind", "allowed_constants": ["GENERATION_FAILURE_STATE"], "assignment_rule": "canonical failure transition post state only"})
        else:
            raise ValueError({"unassigned_enum_like_path": path, "field_type": field_type})
        enum_assignment_rows.append(row)

enum_like_occurrence_count = sum(
    1
    for obj in objects.values()
    for field_type in obj["field_types"]
    if field_type in enum_like_types
)
if len(enum_assignment_rows) != enum_like_occurrence_count or len({row["path"] for row in enum_assignment_rows}) != enum_like_occurrence_count:
    raise ValueError("enum-like path assignment gap overlap or duplicate")
doc["path_qualified_enum_and_role_assignments"] = {
    "enum_like_field_types": sorted(enum_like_types),
    "occurrence_count": enum_like_occurrence_count,
    "rows": enum_assignment_rows,
    "occurrence_gap_count": 0,
    "occurrence_extra_count": 0,
    "occurrence_overlap_count": 0,
    "duplicate_path_count": 0,
    "unknown_alias_wrong_family_cross_role_cross_mode_or_caller_selected_value_allowed": False,
}

inherited_v20_token_paths = {
    f"objects.{object_name}.{field_name}"
    for object_name, obj in base_doc["objects"].items()
    for field_name, field_type in zip(obj["field_order"], obj["field_types"])
    if field_type == "token256"
}
attempt_zero_derived_nonce_paths = {
    "objects.authenticated_result.verification_nonce",
    "objects.verifier_evidence.evidence_nonce",
    "objects.token_accumulator_proof.accumulator_proof_nonce",
    "objects.journal_state.state_nonce",
    "objects.transition_request.request_nonce",
    "objects.commit_evidence.commit_nonce",
    "objects.state_authority_head_evidence.authority_nonce",
    "objects.external_anchor_evidence.anchor_nonce",
}
all_token_paths = {
    f"objects.{object_name}.{field_name}"
    for object_name, obj in objects.items()
    for field_name, field_type in zip(obj["field_order"], obj["field_types"])
    if field_type == "token256"
}
if len(inherited_v20_token_paths) != 51 or not attempt_zero_derived_nonce_paths.issubset(inherited_v20_token_paths):
    raise ValueError("V20 token preservation or eight nonce-path identity drift")
token_path_rows = []
for path in sorted(all_token_paths):
    if path in attempt_zero_derived_nonce_paths:
        semantics = "ATTEMPT_ZERO_DERIVED_MAPPED_NONCE_EXCEPTION"
        rule = "exact verifier-recomputed 32-byte field-specific HKDF output from the full verified beacon VRF bytes and the closed namespace/context/registration/epoch/sequence/role/attempt-zero/slot/message tuple; lowercase-hex ASCII maps byte-for-byte to SUCCESS terminal output and is never caller-selected retried rejected truncated reused or content-derived"
    elif path in inherited_v20_token_paths:
        semantics = "INHERITED_NONDERIVED_CONTENT_INDEPENDENT_TOKEN"
        rule = "exact inherited V20 nonderived content-independent 256-bit token semantics; no payload or scope mapping"
    else:
        semantics = "REGISTERED_IDENTITY_OR_LINK_REPEAT_TOKEN"
        rule = "byte-identical repeat of the one namespace-precommitted or pinned-context token; not a new derivation and not content-correlatable"
    token_path_rows.append({"path": path, "semantics": semantics, "exact_rule": rule})
doc["path_qualified_token256_semantics"] = {
    "all_token256_occurrence_count": len(all_token_paths),
    "inherited_v20_occurrence_count": len(inherited_v20_token_paths),
    "attempt_zero_derived_nonce_exception_count": len(attempt_zero_derived_nonce_paths),
    "other_inherited_nonderived_count": len(inherited_v20_token_paths - attempt_zero_derived_nonce_paths),
    "rows": token_path_rows,
    "gap_extra_overlap_or_wrong_exception_count": 0,
    "generic_token256_nonderived_rule_is_overridden_only_at_the_exact_eight_listed_nonce_paths": True,
}

def fields_except(object_name, excluded):
    return [field for field in objects[object_name]["field_order"] if field not in set(excluded)]

def base64_mapping(object_name, field_name, message_order, output_kind, profile_path, role_or_prover, key_or_verifier_path, mode="UNIQUE_DETERMINISTIC_BYTES", attempt_link="exact output_attempt_index or attempt_index is zero and every variant-affecting input is closed"):
    return {
        "object_path": f"objects.{object_name}",
        "field_path": f"objects.{object_name}.{field_name}",
        "domain_constant": objects[object_name]["domain_const"],
        "message_or_public_input_field_order": message_order,
        "output_kind": output_kind,
        "fixed_profile_context_path": profile_path,
        "fixed_role_or_prover": role_or_prover,
        "fixed_key_or_verifier_context_path": key_or_verifier_path,
        "decoded_grammar": "exact pinned fixed decoded length and tag grammar; RFC4648 padded canonical base64; decoder consumes every byte and rejects alternate tag length encoding context extension auxiliary field ignored suffix or trailing bytes",
        "generation_mode": mode,
        "attempt_reservation_outcome_linkage": attempt_link,
        "output_byte_hash_equality": f"VerifyExact consumes every decoded byte of {field_name} under the exact listed public inputs profile role and key/prover-verifier relation and returns true; raw canonical base64 is included in the enclosing object hash preimage; no decoded-byte SHA equality is claimed unless this row names an explicit linked hash field",
        "unique_output_assertion": "for the exact complete inputs exactly one accepted decoded byte string and one canonical base64 string exist; retry rejection sampling selective abort alternate nonce form subset order path witness proof or encoding refuses",
    }

base64_mappings = []
base64_mappings.extend([
    base64_mapping("authenticated_result", "authentication_signature_base64", objects["authenticated_result"]["signature_message_order"], "signature", selection_context_by_object["authenticated_result"], "result_authentication_key_role", "objects.pinned_context.result_authentication_public_key_sha256", attempt_link="verification_nonce is exact SUCCESS output of nonce_generation_reservation + reservation-ledger evidence + terminal outcome + terminal-anchor evidence; signature attempt zero is unique deterministic"),
    base64_mapping("commit_evidence", "commit_signature_base64", objects["commit_evidence"]["signature_message_order"], "signature", selection_context_by_object["commit_evidence"], "journal_authentication_key_role", "objects.pinned_context.journal_authentication_public_key_sha256", attempt_link="commit_nonce has exact four-object attempt-zero ledger chain; signature attempt zero is unique deterministic"),
    base64_mapping("external_anchor_evidence", "anchor_authentication_proof_base64", objects["external_anchor_evidence"]["authentication_proof_public_input_order"], "fixed quorum signature plus one canonical inclusion-consistency path", selection_context_by_object["external_anchor_evidence"], "external_anchor_authentication_key_role with exact fixed quorum member roster and order", "objects.pinned_context.external_anchor_authentication_public_key_sha256", attempt_link="anchor_nonce has exact four-object attempt-zero ledger chain; quorum subset/order/path fixed before output"),
    base64_mapping("journal_state", "journal_state_signature_base64", ["hash_domain", "journal_state_root_sha256"], "signature", selection_context_by_object["journal_state"], "journal_authentication_key_role", "objects.pinned_context.journal_authentication_public_key_sha256", attempt_link="state_nonce has exact four-object attempt-zero ledger chain and journal_state_root includes every chain root"),
    base64_mapping("state_authority_head_evidence", "authority_signature_base64", objects["state_authority_head_evidence"]["signature_message_order"], "signature", selection_context_by_object["state_authority_head_evidence"], "state_authority_authentication_key_role", "objects.pinned_context.state_authority_authentication_public_key_sha256", attempt_link="authority_nonce has exact four-object attempt-zero ledger chain; signature attempt zero is unique deterministic"),
    base64_mapping("token_accumulator_proof", "accumulator_proof_bytes_base64", objects["token_accumulator_proof"]["proof_public_input_order"], "canonical accumulator transition proof", selection_context_by_object["token_accumulator_proof"], "fixed replay-token accumulator prover over accumulator_proof_statement_root_sha256; no generic signing key", "objects.pinned_context.replay_token_accumulator_profile_sha256", attempt_link="accumulator_proof_nonce has exact four-object attempt-zero ledger chain; exact statement generator and verifier have one proof byte string"),
    base64_mapping("transition_request", "request_signature_base64", objects["transition_request"]["signature_message_order"], "signature", selection_context_by_object["transition_request"], "journal_authentication_key_role", "objects.pinned_context.journal_authentication_public_key_sha256", attempt_link="request_nonce has exact four-object attempt-zero ledger chain; signature attempt zero is unique deterministic"),
    base64_mapping("verifier_evidence", "evidence_signature_base64", objects["verifier_evidence"]["signature_message_order"], "signature", selection_context_by_object["verifier_evidence"], "verifier_evidence_key_role", "objects.pinned_context.verifier_evidence_authentication_public_key_sha256", attempt_link="evidence_nonce has exact four-object attempt-zero ledger chain; signature attempt zero is unique deterministic"),
])

base64_mappings.extend([
    base64_mapping("genesis_journal_state", "genesis_journal_state_signature_base64", ["hash_domain", "genesis_journal_state_root_sha256", "output_generation_mode", "output_attempt_index", "output_selection_profile_sha256"], "signature", selection_context_by_object["genesis_journal_state"], "journal_authentication_key_role", "objects.pinned_context.journal_authentication_public_key_sha256"),
    base64_mapping("genesis_external_anchor_evidence", "genesis_anchor_authentication_proof_base64", fields_except("genesis_external_anchor_evidence", ["genesis_anchor_authentication_proof_base64", "genesis_external_anchor_root_sha256"]), "fixed quorum signature plus canonical genesis path proof", selection_context_by_object["genesis_external_anchor_evidence"], "external_anchor_authentication_key_role with exact fixed quorum member roster and order", "objects.pinned_context.external_anchor_authentication_public_key_sha256"),
    base64_mapping("genesis_state_authority_evidence", "genesis_authority_signature_base64", fields_except("genesis_state_authority_evidence", ["genesis_authority_signature_base64", "genesis_state_authority_head_evidence_sha256"]), "signature", selection_context_by_object["genesis_state_authority_evidence"], "state_authority_authentication_key_role", "objects.pinned_context.state_authority_authentication_public_key_sha256"),
    base64_mapping("singleton_registration_request", "request_authentication_signature_base64", fields_except("singleton_registration_request", ["request_authentication_signature_base64", "singleton_registration_request_sha256"]), "registrar signature over the exact acyclic completed request", selection_context_by_object["singleton_registration_request"], "global_registrar_authentication_key_role", "objects.pinned_context.global_registrar_authentication_public_key_sha256"),
    base64_mapping("global_registry_sparse_map_proof", "transition_proof_base64", fields_except("global_registry_sparse_map_proof", ["transition_proof_base64", "global_registry_sparse_map_proof_sha256"]), "canonical singleton sparse-map ABSENT-to-assigned transition proof", selection_context_by_object["global_registry_sparse_map_proof"], "fixed singleton registry transition prover/verifier", "objects.pinned_context.singleton_registry_proof_profile_root_sha256", attempt_link="not a generation attempt: exact canonical proof bytes are a pure function of the closed typed update/public inputs and fixed namespace-resolved proof profile; no retry caller entropy rejection sampling or alternate proof is accepted"),
    base64_mapping("generation_reservation", "reservation_authentication_signature_base64", fields_except("generation_reservation", ["reservation_authentication_signature_base64", "generation_reservation_sha256"]), "signature", selection_context_by_object["generation_reservation"], "generation_reservation_authentication_key_role", "objects.pinned_context.generation_reservation_authentication_public_key_sha256"),
    base64_mapping("generation_sequence_transaction_claim_evidence", "sequence_transaction_claim_authentication_proof_base64", fields_except("generation_sequence_transaction_claim_evidence", ["sequence_transaction_claim_authentication_proof_base64", "generation_sequence_transaction_claim_evidence_sha256"]), "fixed two-authority atomic journal-store plus reservation-ledger sequence-claim CAS proof", selection_context_by_object["generation_sequence_transaction_claim_evidence"], "journal_authentication_key_role + reservation_ledger_authority_authentication_key_role in exact pinned order", "objects.pinned_context.generation_sequence_transaction_claim_quorum_public_key_root_sha256"),
    base64_mapping("generation_terminal_outcome", "private_seed_zero_knowledge_attestation_base64", fields_except("generation_terminal_outcome", ["beacon_vrf_proof_base64", "private_seed_zero_knowledge_attestation_base64", "terminal_outcome_authentication_signature_base64", "generation_terminal_outcome_sha256"]), "unique deterministic zero-knowledge confidential-generator attestation", selection_context_by_object["generation_terminal_outcome"], "confidential_generator_attestation_key_role and exact full contributor roster canonical order", "objects.pinned_context.confidential_generator_attestation_public_key_sha256"),
    base64_mapping("generation_terminal_outcome", "terminal_outcome_authentication_signature_base64", fields_except("generation_terminal_outcome", ["terminal_outcome_authentication_signature_base64", "generation_terminal_outcome_sha256"]), "signature", selection_context_by_object["generation_terminal_outcome"], "generation_terminal_outcome_authentication_key_role", "objects.pinned_context.generation_terminal_outcome_authentication_public_key_sha256"),
    base64_mapping("generation_reservation_ledger_evidence", "reservation_ledger_authentication_signature_base64", fields_except("generation_reservation_ledger_evidence", ["reservation_ledger_authentication_signature_base64", "generation_reservation_ledger_evidence_sha256"]), "signature over exact reservation-ledger anchor statement", selection_context_by_object["generation_reservation_ledger_evidence"], "reservation_ledger_authority_authentication_key_role", "objects.pinned_context.reservation_ledger_authority_authentication_public_key_sha256"),
    base64_mapping("generation_terminal_anchor_evidence", "terminal_anchor_authentication_signature_base64", fields_except("generation_terminal_anchor_evidence", ["terminal_anchor_authentication_signature_base64", "generation_terminal_anchor_evidence_sha256"]), "signature over exact terminal-anchor statement", selection_context_by_object["generation_terminal_anchor_evidence"], "generation_terminal_anchor_authentication_key_role", "objects.pinned_context.terminal_anchor_authority_authentication_public_key_sha256"),
    base64_mapping("public_beacon_pre_reveal_evidence", "beacon_allocation_assignment_proof_base64", fields_except("public_beacon_pre_reveal_evidence", ["beacon_allocation_assignment_proof_base64", "pre_reveal_authentication_signature_base64", "public_beacon_pre_reveal_evidence_sha256"]), "canonical one-use sparse-map allocation proof assigning the exact registration epoch sequence role attempt-zero allocation slot before reveal", selection_context_by_object["public_beacon_pre_reveal_evidence"], "fixed public-beacon allocation-map prover/verifier", "objects.pinned_context.public_beacon_allocation_map_profile_sha256"),
    base64_mapping("public_beacon_pre_reveal_evidence", "pre_reveal_authentication_signature_base64", fields_except("public_beacon_pre_reveal_evidence", ["pre_reveal_authentication_signature_base64", "public_beacon_pre_reveal_evidence_sha256"]), "signature over exact future-round pre-reveal head commitment", selection_context_by_object["public_beacon_pre_reveal_evidence"], "beacon_vrf_authentication_key_role", "objects.pinned_context.public_round_beacon_vrf_public_key_sha256"),
    base64_mapping("beacon_reservation_order_evidence", "reservation_before_reveal_proof_base64", fields_except("beacon_reservation_order_evidence", ["reservation_before_reveal_proof_base64", "beacon_reservation_order_evidence_sha256"]), "authenticated cross-system order proof", selection_context_by_object["beacon_reservation_order_evidence"], "beacon_vrf_authentication_key_role", "objects.pinned_context.public_round_beacon_vrf_public_key_sha256"),
    base64_mapping("public_beacon_reveal_evidence", "public_beacon_output_base64", ["schema", "hash_domain", "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "public_round_index", "public_beacon_vrf_input_message_root_sha256", "public_round_beacon_identity_sha256", "beacon_vrf_authentication_key_role"], "canonical VRF verifier-returned output bytes from the pre-fixed beacon key profile namespace registration and round only; reservation and order are enclosing post-output linkages, never VRF inputs", selection_context_by_object["public_beacon_reveal_evidence"], "fixed public-round VRF evaluator/verifier", "objects.pinned_context.public_round_beacon_vrf_public_key_sha256"),
    base64_mapping("public_beacon_reveal_evidence", "beacon_vrf_proof_base64", ["schema", "hash_domain", "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "public_round_index", "public_beacon_vrf_input_message_root_sha256", "public_beacon_output_base64", "public_beacon_output_sha256", "public_round_beacon_identity_sha256", "beacon_vrf_authentication_key_role"], "unique VRF proof over the pre-fixed non-circular beacon input and exact returned output; reservation order and pre-reveal evidence are verified separately as enclosing equality-bound linkages", selection_context_by_object["public_beacon_reveal_evidence"], "beacon_vrf_authentication_key_role", "objects.pinned_context.public_round_beacon_vrf_public_key_sha256"),
    base64_mapping("public_beacon_reveal_evidence", "public_beacon_recovery_reconstruction_proof_base64", fields_except("public_beacon_reveal_evidence", ["public_beacon_recovery_reconstruction_proof_base64", "public_beacon_reveal_evidence_sha256"]), "unique threshold/public recovery proof that reconstructs the same committed generation-round VRF output and proof when the named beacon withholds", selection_context_by_object["public_beacon_reveal_evidence"], "fixed generation-beacon nonabortable recovery verifier", "objects.pinned_context.generation_beacon_nonabortable_recovery_key_root_sha256"),
    base64_mapping("pre_witness_technical_health_evidence", "technical_health_measurement_attestation_base64", ["schema", "hash_domain", "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_sequence_transaction_claim_evidence_sha256", "sequence_transaction_claim_slot_key_sha256", "sequence_transaction_claim_statement_sha256", "reserved_sequence", "authoritative_pre_state_kind", "fixed_role_lifecycle_order_root_sha256", "fixed_terminal_deadline_round_delta", "observed_sequence_claim_post_ledger_state_root_sha256", "observed_sequence_claim_post_ledger_state_object_sha256", "observed_sequence_claim_post_ledger_counter", "observed_confidential_generator_image_sha256", "observed_confidential_generator_profile_sha256", "observed_contributor_roster_sha256", "observed_contributor_key_root_sha256", "technical_health_input_vector_sha256", "technical_health_measurement_result", "role_terminalization_plan_root_sha256", "technical_health_measurement_output_generation_mode", "technical_health_measurement_output_attempt_index", "pre_witness_health_measurement_output_selection_profile_sha256"], "unique pre-output measured-state attestation returning the complete byte-available content-independent sequence health vector deterministic pass/fail result and exact ten-role terminalization plan before any beacon allocation", "objects.pinned_context.pre_witness_health_measurement_output_selection_profile_sha256", "pre_witness_health_authentication_key_role under the distinct measured-state attestation subprofile", "objects.pinned_context.pre_witness_health_authentication_public_key_sha256"),
    base64_mapping("pre_witness_technical_health_evidence", "producer_availability_authentication_signature_base64", ["schema", "hash_domain", "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_sequence_transaction_claim_evidence_sha256", "sequence_transaction_claim_slot_key_sha256", "sequence_transaction_claim_statement_sha256", "reserved_sequence", "fixed_role_lifecycle_order_root_sha256", "role_terminalization_plan_root_sha256", "complete_sequence_materialization_profile_root_sha256", "complete_sequence_materialization_roster_root_sha256", "complete_sequence_materialization_recovery_key_root_sha256", "producer_availability_predicate_sha256", "producer_availability_profile_sha256", "producer_availability_authority_identity_sha256", "producer_availability_result", "producer_availability_authentication_key_role", "producer_availability_output_generation_mode", "producer_availability_output_attempt_index", "producer_availability_output_selection_profile_sha256"], "separately authenticated pre-output content-independent complete-sequence materializer availability result and exact ten-role terminalization-plan root, excluding all reveal output scope witness and content bytes", "objects.pinned_context.producer_availability_output_selection_profile_sha256", "producer_availability_authentication_key_role", "objects.pinned_context.producer_availability_authentication_public_key_sha256"),
    base64_mapping("pre_witness_technical_health_evidence", "complete_sequence_materialization_commitment_proof_base64", fields_except("pre_witness_technical_health_evidence", ["complete_sequence_materialization_commitment_proof_base64", "health_authentication_signature_base64", "pre_witness_technical_health_evidence_sha256"]), "fixed-roster proof that every later beacon target terminal authority and final-CAS byte is precommitted to one nonabortable materializer or public recovery path", selection_context_by_object["pre_witness_technical_health_evidence"], "fixed complete-sequence materialization quorum in canonical roster order", "objects.pinned_context.complete_sequence_materialization_recovery_key_root_sha256"),
    base64_mapping("pre_witness_technical_health_evidence", "health_authentication_signature_base64", fields_except("pre_witness_technical_health_evidence", ["health_authentication_signature_base64", "pre_witness_technical_health_evidence_sha256"]), "unique pre-output content-independent health signature consuming the measured vector availability commitment and complete-sequence materialization proof", selection_context_by_object["pre_witness_technical_health_evidence"], "pre_witness_health_authentication_key_role", "objects.pinned_context.pre_witness_health_authentication_public_key_sha256"),
    base64_mapping("role_producer_availability_evidence", "producer_availability_authentication_signature_base64", fields_except("role_producer_availability_evidence", ["producer_availability_authentication_signature_base64", "role_producer_availability_evidence_sha256"]), "same-role pre-reveal producer-availability signature over the exact commitment observation and result tuple", selection_context_by_object["role_producer_availability_evidence"], "producer_availability_authentication_key_role", "objects.pinned_context.producer_availability_authentication_public_key_sha256"),
    base64_mapping("terminal_deadline_observation_evidence", "deadline_beacon_output_base64", ["schema", "hash_domain", "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_reservation_sha256", "generation_reservation_ledger_evidence_sha256", "public_beacon_reveal_evidence_sha256", "pre_witness_technical_health_evidence_sha256", "reservation_slot_key_sha256", "reserved_sequence", "output_role", "reserved_output_generation_mode", "reservation_attempt_index", "generation_public_round_index", "fixed_terminal_deadline_round_index", "deadline_vrf_input_message_root_sha256", "fixed_terminal_timing_envelope_profile_sha256", "public_round_beacon_identity_sha256", "beacon_vrf_authentication_key_role"], "canonical deadline-round VRF verifier-returned output bytes for the exact reservation role/mode/attempt/generation-round/deadline tuple", selection_context_by_object["terminal_deadline_observation_evidence"], "fixed public-round VRF evaluator/verifier", "objects.pinned_context.public_round_beacon_vrf_public_key_sha256"),
    base64_mapping("terminal_deadline_observation_evidence", "deadline_beacon_vrf_proof_base64", ["schema", "hash_domain", "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_reservation_sha256", "generation_reservation_ledger_evidence_sha256", "public_beacon_reveal_evidence_sha256", "pre_witness_technical_health_evidence_sha256", "reservation_slot_key_sha256", "reserved_sequence", "output_role", "reserved_output_generation_mode", "reservation_attempt_index", "generation_public_round_index", "fixed_terminal_deadline_round_index", "deadline_vrf_input_message_root_sha256", "deadline_beacon_output_base64", "deadline_beacon_output_sha256", "fixed_terminal_timing_envelope_profile_sha256", "public_round_beacon_identity_sha256", "beacon_vrf_authentication_key_role"], "unique deadline-round VRF proof over the exact reservation role/mode/attempt/generation-round/deadline tuple", selection_context_by_object["terminal_deadline_observation_evidence"], "beacon_vrf_authentication_key_role", "objects.pinned_context.public_round_beacon_vrf_public_key_sha256"),
    base64_mapping("terminal_deadline_observation_evidence", "deadline_beacon_recovery_reconstruction_proof_base64", fields_except("terminal_deadline_observation_evidence", ["deadline_beacon_recovery_reconstruction_proof_base64", "deadline_observation_authentication_signature_base64", "terminal_deadline_observation_evidence_sha256"]), "unique threshold/public recovery proof that reconstructs the same deadline-clock VRF output and proof when the named clock beacon withholds", selection_context_by_object["terminal_deadline_observation_evidence"], "fixed deadline-beacon nonabortable recovery verifier", "objects.pinned_context.deadline_beacon_nonabortable_recovery_key_root_sha256"),
    base64_mapping("terminal_deadline_observation_evidence", "deadline_observation_authentication_signature_base64", fields_except("terminal_deadline_observation_evidence", ["deadline_observation_authentication_signature_base64", "terminal_deadline_observation_evidence_sha256"]), "unique independently authenticated exact-deadline observation signature", selection_context_by_object["terminal_deadline_observation_evidence"], "beacon_vrf_authentication_key_role", "objects.pinned_context.public_round_beacon_vrf_public_key_sha256"),
    base64_mapping("generation_sequence_lifecycle_refusal_evidence", "lifecycle_refusal_zero_knowledge_proof_base64", fields_except("generation_sequence_lifecycle_refusal_evidence", ["lifecycle_refusal_zero_knowledge_proof_base64", "refusal_private_seed_zero_knowledge_attestation_base64", "lifecycle_refusal_authentication_signature_base64", "generation_sequence_lifecycle_refusal_evidence_sha256"]), "randomized zero-knowledge generic post-claim integrity-refusal proof hiding the surface predicate witness and content", selection_context_by_object["generation_sequence_lifecycle_refusal_evidence"], "exact fixed threshold-isolated lifecycle-refusal prover", "objects.pinned_context.lifecycle_refusal_verifier_image_sha256", mode="CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING", attempt_link="one exact hidden refusal at the fixed lifecycle boundary under the held sequence claim; no role beacon allocation or retry occurs for the refused boundary"),
    base64_mapping("generation_sequence_lifecycle_refusal_evidence", "refusal_private_seed_zero_knowledge_attestation_base64", fields_except("generation_sequence_lifecycle_refusal_evidence", ["refusal_private_seed_zero_knowledge_attestation_base64", "lifecycle_refusal_authentication_signature_base64", "generation_sequence_lifecycle_refusal_evidence_sha256"]), "unique deterministic zero-knowledge attestation of the full domain-separated refusal seed aggregation canonical witness relation exact full lifecycle-refusal proof bytes and erasure; proof bytes are created first and the attestation consumes them without a cycle", selection_context_by_object["generation_sequence_lifecycle_refusal_evidence"], "confidential_generator_attestation_key_role and complete contributor roster", "objects.pinned_context.confidential_generator_attestation_public_key_sha256"),
    base64_mapping("generation_sequence_lifecycle_refusal_evidence", "lifecycle_refusal_authentication_signature_base64", fields_except("generation_sequence_lifecycle_refusal_evidence", ["lifecycle_refusal_authentication_signature_base64", "generation_sequence_lifecycle_refusal_evidence_sha256"]), "distinct lifecycle-refusal authority signature over the generic hiding proof and seed-derivation attestation", selection_context_by_object["generation_sequence_lifecycle_refusal_evidence"], "lifecycle_refusal_authentication_key_role", "objects.pinned_context.lifecycle_refusal_authentication_public_key_sha256"),
    base64_mapping("generation_failure_sequence_commit_evidence", "failure_anchor_authentication_proof_base64", ["schema", "hash_domain", "post_failure_external_anchor_statement_sha256", "external_anchor_authentication_key_role", "output_generation_mode", "output_attempt_index", "output_selection_profile_sha256"], "unique preserved-profile external-anchor successor proof over the already computed acyclic statement only; the post anchor root is derived afterward from statement plus proof", "objects.pinned_context.generation_failure_output_selection_profile_sha256", "external_anchor_authentication_key_role", "objects.pinned_context.external_anchor_authentication_public_key_sha256"),
    base64_mapping("generation_failure_sequence_commit_evidence", "failure_authority_authentication_signature_base64", ["schema", "hash_domain", "post_failure_state_authority_statement_sha256", "state_authority_authentication_key_role", "output_generation_mode", "output_attempt_index", "output_selection_profile_sha256"], "unique preserved-profile state-authority successor signature over the already computed acyclic statement only; the post authority head is derived afterward from statement plus signature", "objects.pinned_context.generation_failure_output_selection_profile_sha256", "state_authority_authentication_key_role", "objects.pinned_context.state_authority_authentication_public_key_sha256"),
    base64_mapping("commit_evidence", "sequence_transaction_claim_release_authentication_signature_base64", ["schema", "hash_domain", "generation_sequence_transaction_claim_evidence_sha256", "sequence_transaction_claim_slot_key_sha256", "sequence_transaction_claim_statement_sha256", "sequence_claim_pre_reservation_ledger_state_root_sha256", "sequence_claim_pre_reservation_ledger_state_object_sha256", "sequence_claim_pre_reservation_ledger_counter", "sequence_claim_post_reservation_ledger_state_root_sha256", "sequence_claim_post_reservation_ledger_state_object_sha256", "sequence_claim_post_reservation_ledger_counter", "pre_sequence_transaction_claim_state", "post_sequence_transaction_claim_state", "sequence_claim_release_cas_result", "sequence_claim_release_no_fork_result", "authoritative_sequence_claim_cas_no_fork_profile_sha256", "reservation_ledger_authority_identity_sha256", "reservation_ledger_authority_authentication_key_role", "generation_sequence_transaction_claim_output_selection_profile_sha256", "transition_request_sha256", "committed_post_state_root_sha256", "committed_post_state_object_sha256", "post_state_authority_head_evidence_sha256", "post_external_anchor_root_sha256", "active_generation_chain_set_root_sha256"], "unique ledger-authority release signature whose bytes are then covered by the same journal commit signature", "objects.pinned_context.generation_sequence_transaction_claim_output_selection_profile_sha256", "reservation_ledger_authority_authentication_key_role", "objects.pinned_context.reservation_ledger_authority_authentication_public_key_sha256"),
    base64_mapping("generation_failure_sequence_commit_evidence", "sequence_transaction_claim_release_authentication_signature_base64", ["schema", "hash_domain", "generation_sequence_transaction_claim_evidence_sha256", "sequence_transaction_claim_slot_key_sha256", "sequence_transaction_claim_statement_sha256", "sequence_claim_pre_reservation_ledger_state_root_sha256", "sequence_claim_pre_reservation_ledger_state_object_sha256", "sequence_claim_pre_reservation_ledger_counter", "sequence_claim_post_reservation_ledger_state_root_sha256", "sequence_claim_post_reservation_ledger_state_object_sha256", "sequence_claim_post_reservation_ledger_counter", "pre_sequence_transaction_claim_state", "post_sequence_transaction_claim_state", "sequence_claim_release_cas_result", "sequence_claim_release_no_fork_result", "authoritative_sequence_claim_cas_no_fork_profile_sha256", "reservation_ledger_authority_identity_sha256", "reservation_ledger_authority_authentication_key_role", "generation_sequence_transaction_claim_output_selection_profile_sha256", "generation_failure_record_sha256", "post_failure_state_root_sha256", "post_failure_state_object_sha256", "post_failure_external_anchor_root_sha256", "post_failure_state_authority_head_evidence_sha256"], "unique ledger-authority release signature whose bytes are covered by the same final failure fixed-roster commit proof", "objects.pinned_context.generation_sequence_transaction_claim_output_selection_profile_sha256", "reservation_ledger_authority_authentication_key_role", "objects.pinned_context.reservation_ledger_authority_authentication_public_key_sha256"),
    base64_mapping("generation_failure_sequence_commit_evidence", "failure_commit_authentication_proof_base64", fields_except("generation_failure_sequence_commit_evidence", ["failure_commit_authentication_proof_base64", "generation_failure_sequence_commit_evidence_sha256"]), "unique fixed-roster journal state-authority and external-anchor quorum proof", selection_context_by_object["generation_failure_sequence_commit_evidence"], "journal_authentication_key_role + state_authority_authentication_key_role + external_anchor_authentication_key_role in exact pinned order", "objects.pinned_context.generation_failure_quorum_public_key_root_sha256"),
    base64_mapping("failure_external_anchor_current_head_observation", "current_head_observation_proof_base64", fields_except("failure_external_anchor_current_head_observation", ["current_head_observation_proof_base64", "failure_external_anchor_current_head_observation_sha256"]), "unique independently authenticated external-anchor current-head observation proof", selection_context_by_object["failure_external_anchor_current_head_observation"], "external_anchor_authentication_key_role", "objects.pinned_context.external_anchor_authentication_public_key_sha256"),
    base64_mapping("failure_state_authority_current_head_observation", "current_head_observation_signature_base64", fields_except("failure_state_authority_current_head_observation", ["current_head_observation_signature_base64", "failure_state_authority_current_head_observation_sha256"]), "unique independently authenticated state-authority current-head observation signature", selection_context_by_object["failure_state_authority_current_head_observation"], "state_authority_authentication_key_role", "objects.pinned_context.state_authority_authentication_public_key_sha256"),
])

base64_mappings.extend([
    base64_mapping("scope_precommitment", "scope_commitment_base64", fields_except("scope_precommitment", ["scope_commitment_base64", "scope_commitment_bytes_sha256", "scope_precommitment_sha256", "generation_terminal_outcome_sha256", "generation_terminal_anchor_evidence_sha256"]), "randomized content-hiding binding commitment", "objects.pinned_context.commitment_profile_sha256", "exact fixed threshold-isolated commitment generator and complete contributor roster", "objects.pinned_context.commitment_generator_image_sha256", mode="CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING", attempt_link="exact generation reservation + authoritative reservation-ledger evidence exist before generation; final target separately binds SUCCESS terminal outcome + terminal-anchor evidence after output; private seed never retained; output hash equals terminal output"),
    base64_mapping("completeness_proof", "proof_bytes_base64", fields_except("completeness_proof", ["proof_bytes_base64", "proof_bytes_sha256", "completeness_proof_sha256", "generation_terminal_outcome_sha256", "generation_terminal_anchor_evidence_sha256"]), "randomized zero-knowledge completeness proof", "objects.pinned_context.proof_system_profile_sha256", "exact fixed threshold-isolated proof generator over exact five inherited predicates", "objects.pinned_context.proof_verifier_image_sha256", mode="CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING", attempt_link="exact generation reservation + authoritative reservation-ledger evidence exist before generation; final target separately binds SUCCESS terminal outcome + terminal-anchor evidence after output; private seed witness and generation state erased; output hash equals terminal output"),
])
for row in base64_mappings[-2:]:
    field_name = row["field_path"].rsplit(".", 1)[1]
    bound_hash = "scope_commitment_bytes_sha256" if field_name == "scope_commitment_base64" else "proof_bytes_sha256"
    row["output_byte_hash_equality"] = f"SHA256(decoded exact {field_name}) equals enclosing {bound_hash} and exact generation_terminal_outcome.generated_output_sha256; verifier validates the unique deterministic confidential-seed derivation attestation and the content-hiding commitment/proof relation without recomputing or learning the secret-seeded output"
    row["unique_output_assertion"] = "exactly one retained output is accepted for the externally fixed hidden attempt-zero seed and witness execution; public inputs do not determine or permit recomputation of the confidential-seeded output; second retained output retry rejection sampling or selective abort refuses"
for row in base64_mappings:
    if row["generation_mode"] != "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING":
        continue
    if row["field_path"] == "objects.generation_sequence_lifecycle_refusal_evidence.lifecycle_refusal_zero_knowledge_proof_base64":
        row["output_byte_hash_equality"] = "verifier consumes every decoded proof byte under the exact generic lifecycle-refusal relation and verifies the separate confidential-seed derivation attestation; no public byte recomputation witness digest surface identifier or proof-output hash oracle exists"
        row["unique_output_assertion"] = "exactly one retained generic refusal proof exists for the externally fixed hidden attempt-zero seed and canonical private witness encoding; equivalent witness encodings retries alternate boundary encodings rejection sampling and selective abort refuse; public inputs cannot recompute the randomized bytes"
algorithm_profile_by_path = {
    "objects.authenticated_result.authentication_signature_base64": "objects.pinned_context.result_authentication_profile_sha256",
    "objects.commit_evidence.commit_signature_base64": "objects.pinned_context.journal_authentication_profile_sha256",
    "objects.external_anchor_evidence.anchor_authentication_proof_base64": "objects.pinned_context.external_anchor_authentication_profile_sha256",
    "objects.journal_state.journal_state_signature_base64": "objects.pinned_context.journal_authentication_profile_sha256",
    "objects.state_authority_head_evidence.authority_signature_base64": "objects.pinned_context.state_authority_authentication_profile_sha256",
    "objects.token_accumulator_proof.accumulator_proof_bytes_base64": "objects.pinned_context.replay_token_accumulator_profile_sha256",
    "objects.transition_request.request_signature_base64": "objects.pinned_context.journal_authentication_profile_sha256",
    "objects.verifier_evidence.evidence_signature_base64": "objects.pinned_context.verifier_evidence_authentication_profile_sha256",
    "objects.genesis_journal_state.genesis_journal_state_signature_base64": "objects.pinned_context.journal_authentication_profile_sha256",
    "objects.genesis_external_anchor_evidence.genesis_anchor_authentication_proof_base64": "objects.pinned_context.external_anchor_authentication_profile_sha256",
    "objects.genesis_state_authority_evidence.genesis_authority_signature_base64": "objects.pinned_context.state_authority_authentication_profile_sha256",
    "objects.singleton_registration_request.request_authentication_signature_base64": "objects.pinned_context.global_registrar_authentication_profile_sha256",
    "objects.global_registry_sparse_map_proof.transition_proof_base64": "objects.pinned_context.singleton_registry_proof_profile_root_sha256",
    "objects.generation_reservation.reservation_authentication_signature_base64": "objects.pinned_context.generation_reservation_profile_sha256",
    "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_authentication_proof_base64": "objects.pinned_context.generation_sequence_transaction_claim_profile_sha256",
    "objects.generation_terminal_outcome.private_seed_zero_knowledge_attestation_base64": "objects.pinned_context.confidential_generator_attestation_profile_sha256",
    "objects.generation_terminal_outcome.terminal_outcome_authentication_signature_base64": "objects.pinned_context.generation_terminal_outcome_profile_sha256",
    "objects.generation_reservation_ledger_evidence.reservation_ledger_authentication_signature_base64": "objects.pinned_context.reservation_ledger_authority_authentication_profile_sha256",
    "objects.generation_terminal_anchor_evidence.terminal_anchor_authentication_signature_base64": "objects.pinned_context.terminal_anchor_authority_authentication_profile_sha256",
    "objects.public_beacon_pre_reveal_evidence.beacon_allocation_assignment_proof_base64": "objects.pinned_context.public_beacon_allocation_map_profile_sha256",
    "objects.public_beacon_pre_reveal_evidence.pre_reveal_authentication_signature_base64": "objects.pinned_context.public_round_beacon_authentication_profile_sha256",
    "objects.beacon_reservation_order_evidence.reservation_before_reveal_proof_base64": "objects.pinned_context.beacon_reservation_order_proof_profile_sha256",
    "objects.public_beacon_reveal_evidence.public_beacon_output_base64": "objects.pinned_context.public_round_beacon_vrf_proof_profile_sha256",
    "objects.public_beacon_reveal_evidence.beacon_vrf_proof_base64": "objects.pinned_context.public_round_beacon_vrf_proof_profile_sha256",
    "objects.public_beacon_reveal_evidence.public_beacon_recovery_reconstruction_proof_base64": "objects.pinned_context.generation_beacon_nonabortable_recovery_profile_sha256",
    "objects.pre_witness_technical_health_evidence.health_authentication_signature_base64": "objects.pinned_context.pre_witness_health_authentication_profile_sha256",
    "objects.pre_witness_technical_health_evidence.producer_availability_authentication_signature_base64": "objects.pinned_context.producer_availability_authentication_profile_sha256",
    "objects.pre_witness_technical_health_evidence.technical_health_measurement_attestation_base64": "objects.pinned_context.pre_witness_health_measurement_attestation_profile_sha256",
    "objects.pre_witness_technical_health_evidence.complete_sequence_materialization_commitment_proof_base64": "objects.pinned_context.complete_sequence_materialization_profile_root_sha256",
    "objects.role_producer_availability_evidence.producer_availability_authentication_signature_base64": "objects.pinned_context.producer_availability_authentication_profile_sha256",
    "objects.terminal_deadline_observation_evidence.deadline_beacon_output_base64": "objects.pinned_context.public_round_beacon_vrf_proof_profile_sha256",
    "objects.terminal_deadline_observation_evidence.deadline_beacon_vrf_proof_base64": "objects.pinned_context.public_round_beacon_vrf_proof_profile_sha256",
    "objects.terminal_deadline_observation_evidence.deadline_beacon_recovery_reconstruction_proof_base64": "objects.pinned_context.deadline_beacon_nonabortable_recovery_profile_sha256",
    "objects.terminal_deadline_observation_evidence.deadline_observation_authentication_signature_base64": "objects.pinned_context.terminal_deadline_observation_profile_sha256",
    "objects.generation_sequence_lifecycle_refusal_evidence.lifecycle_refusal_zero_knowledge_proof_base64": "objects.pinned_context.lifecycle_refusal_relation_profile_sha256",
    "objects.generation_sequence_lifecycle_refusal_evidence.refusal_private_seed_zero_knowledge_attestation_base64": "objects.pinned_context.confidential_generator_attestation_profile_sha256",
    "objects.generation_sequence_lifecycle_refusal_evidence.lifecycle_refusal_authentication_signature_base64": "objects.pinned_context.lifecycle_refusal_authentication_profile_sha256",
    "objects.generation_failure_sequence_commit_evidence.failure_commit_authentication_proof_base64": "objects.pinned_context.generation_failure_sequence_profile_sha256",
    "objects.generation_failure_sequence_commit_evidence.failure_anchor_authentication_proof_base64": "objects.pinned_context.external_anchor_authentication_profile_sha256",
    "objects.generation_failure_sequence_commit_evidence.failure_authority_authentication_signature_base64": "objects.pinned_context.state_authority_authentication_profile_sha256",
    "objects.commit_evidence.sequence_transaction_claim_release_authentication_signature_base64": "objects.pinned_context.reservation_ledger_authority_authentication_profile_sha256",
    "objects.generation_failure_sequence_commit_evidence.sequence_transaction_claim_release_authentication_signature_base64": "objects.pinned_context.reservation_ledger_authority_authentication_profile_sha256",
    "objects.failure_external_anchor_current_head_observation.current_head_observation_proof_base64": "objects.pinned_context.external_anchor_authentication_profile_sha256",
    "objects.failure_state_authority_current_head_observation.current_head_observation_signature_base64": "objects.pinned_context.state_authority_authentication_profile_sha256",
    "objects.scope_precommitment.scope_commitment_base64": "objects.pinned_context.commitment_profile_sha256",
    "objects.completeness_proof.proof_bytes_base64": "objects.pinned_context.proof_system_profile_sha256",
}
selection_profile_by_path = {}
for row in base64_mappings:
    object_name = row["object_path"].split(".", 1)[1]
    if object_name in selection_context_by_object:
        selection_profile_by_path[row["field_path"]] = selection_context_by_object[object_name]
selection_profile_by_path.update({
    "objects.scope_precommitment.scope_commitment_base64": "objects.pinned_context.scope_commitment_output_selection_profile_sha256",
    "objects.completeness_proof.proof_bytes_base64": "objects.pinned_context.completeness_proof_output_selection_profile_sha256",
    "objects.pre_witness_technical_health_evidence.producer_availability_authentication_signature_base64": "objects.pinned_context.producer_availability_output_selection_profile_sha256",
    "objects.pre_witness_technical_health_evidence.technical_health_measurement_attestation_base64": "objects.pinned_context.pre_witness_health_measurement_output_selection_profile_sha256",
    "objects.commit_evidence.sequence_transaction_claim_release_authentication_signature_base64": "objects.pinned_context.generation_sequence_transaction_claim_output_selection_profile_sha256",
    "objects.generation_failure_sequence_commit_evidence.sequence_transaction_claim_release_authentication_signature_base64": "objects.pinned_context.generation_sequence_transaction_claim_output_selection_profile_sha256",
})
if set(algorithm_profile_by_path) != set(mapped_base64_paths if 'mapped_base64_paths' in globals() else [row["field_path"] for row in base64_mappings]):
    raise ValueError("algorithm profile mapping gap")
for row in base64_mappings:
    path = row["field_path"]
    row["enclosing_object_hash_domain"] = row.pop("domain_constant")
    row["field_specific_cryptographic_subdomain"] = "KIRA_MIND_V21_BASE64_" + path.upper().replace("OBJECTS.", "").replace(".", "_") + "_V1"
    row["cryptographic_subdomain_message_rule"] = "field-specific cryptographic subdomain ASCII + actual NUL precedes the exact listed canonical message/public inputs"
    row["fixed_cryptographic_algorithm_profile_context_path"] = algorithm_profile_by_path[path]
    row["fixed_unique_output_selection_profile_context_path"] = selection_profile_by_path[path]
    row.pop("fixed_profile_context_path", None)
for row in base64_mappings:
    if row["field_path"] == "objects.generation_terminal_outcome.private_seed_zero_knowledge_attestation_base64":
        row["decoded_grammar"] = "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING plus SUCCESS: exact nonnull canonical fixed-length attestation bytes with full-byte consumption; UNIQUE_DETERMINISTIC_BYTES or FAILED: exact JSON null and no decoded bytes"
        row["output_byte_hash_equality"] = "confidential SUCCESS only: VerifyExact consumes every attestation byte under the fixed confidential-generator profile and unique-output profile and binds the nonnull confidential-seed derivation statement; deterministic SUCCESS and every FAILED branch require exact null and forbid a private seed/witness path"
        row["unique_output_assertion"] = "confidential SUCCESS: exactly one accepted decoded attestation byte string and one canonical base64 string exist; deterministic SUCCESS or FAILED: exactly one representation exists, JSON null, with zero decoded bytes and zero base64 encodings"
    if row["field_path"] == "objects.generation_terminal_outcome.terminal_outcome_authentication_signature_base64":
        row["decoded_grammar"] = "SUCCESS: exact nonnull canonical fixed-length signature with full-byte consumption; FAILED: exact JSON null; distinct terminal-anchor signature remains mandatory"
        row["output_byte_hash_equality"] = "SUCCESS: VerifyExact consumes every signature byte under fixed outcome profile and key; FAILED: exact null and independently signed terminal-anchor evidence authenticates failure"
        row["unique_output_assertion"] = "SUCCESS: exactly one accepted decoded producer-signature byte string and one canonical base64 string exist; FAILED: exactly one representation exists, JSON null, with zero decoded bytes and zero base64 encodings; terminal-anchor signature remains mandatory"
    if row["field_path"] == "objects.public_beacon_reveal_evidence.public_beacon_output_base64":
        row["output_byte_hash_equality"] = "SHA256 of the complete canonical decoded VRF output bytes equals public_beacon_reveal_evidence.public_beacon_output_sha256, linked pre-reveal state/evidence committed_round_output_sha256, and linked terminal outcome public_beacon_output_sha256"
        row["unique_output_assertion"] = "exact pinned VRF evaluation for the separately hashed non-circular input has one verifier-returned output byte string and one canonical base64 encoding"
    if row["field_path"] == "objects.public_beacon_reveal_evidence.beacon_vrf_proof_base64":
        row["output_byte_hash_equality"] = "VRFVerifyExact(pinned key, exact public_beacon_vrf_input_message_root_sha256, complete decoded proof) returns exactly the complete bytes encoded by public_beacon_output_base64; SHA256 of those returned bytes equals every linked committed and revealed output hash"
    if row["field_path"] == "objects.terminal_deadline_observation_evidence.deadline_beacon_output_base64":
        row["output_byte_hash_equality"] = "SHA256 of complete canonical decoded deadline-round VRF output bytes equals deadline_beacon_output_sha256"
    if row["field_path"] == "objects.terminal_deadline_observation_evidence.deadline_beacon_vrf_proof_base64":
        row["output_byte_hash_equality"] = "VRFVerifyExact(pinned key, exact deadline_vrf_input_message_root_sha256, complete decoded proof) returns exactly the complete bytes encoded by deadline_beacon_output_base64; SHA256 of returned bytes equals deadline_beacon_output_sha256"
actual_base64_paths = sorted(
    f"objects.{name}.{field}"
    for name, obj in objects.items()
    for field, kind in zip(obj["field_order"], obj["field_types"])
    if kind in {"base64", "nullable_base64"}
)
mapped_base64_paths = sorted(row["field_path"] for row in base64_mappings)
if actual_base64_paths != mapped_base64_paths or len(mapped_base64_paths) != len(set(mapped_base64_paths)):
    raise ValueError({"actual": actual_base64_paths, "mapped": mapped_base64_paths})
content_hiding_output_count = sum(row["generation_mode"] == "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING" for row in base64_mappings)
new_deterministic_output_count = len(base64_mappings) - 8 - content_hiding_output_count
if content_hiding_output_count != 3 or new_deterministic_output_count < 0:
    raise ValueError("base64 generation-mode accounting mismatch")
doc["field_specific_base64_generation_and_verification_mappings"] = {
    "path_count": len(base64_mappings),
    "inherited_eight_count": 8,
    "content_hiding_output_count": content_hiding_output_count,
    "new_deterministic_output_count": new_deterministic_output_count,
    "rows": base64_mappings,
    "missing_duplicate_or_unmapped_count": 0,
    "role_key_profile_message_path_or_output_swap_allowed": False,
}
materialization_byte_rows = [
    {
        "field_path": row["field_path"],
        "cryptographic_subdomain": row["field_specific_cryptographic_subdomain"],
        "algorithm_profile_path": row["fixed_cryptographic_algorithm_profile_context_path"],
        "selection_profile_path": row["fixed_unique_output_selection_profile_context_path"],
        "role_or_prover": row["fixed_role_or_prover"],
        "key_or_verifier_path": row["fixed_key_or_verifier_context_path"],
        "mandatory_materialization": "exactly one canonical byte string or exact branch-conditioned JSON null is entrusted before any beacon allocation; withholding is converted only by the already committed normal/failure/refusal state machine and cannot select another round or retry",
    }
    for row in base64_mappings
]
doc["complete_sequence_materialization_full_byte_closure"] = {
    "profile_root_path": "objects.pinned_context.complete_sequence_materialization_profile_root_sha256",
    "profile_root_formula": "SHA256(ASCII KIRA_MIND_V21_COMPLETE_SEQUENCE_MATERIALIZATION_PROFILE_ROOT_V1 + NUL + for every row in exact field_path lexical order: field path UTF8 + NUL + cryptographic subdomain + NUL + decoded algorithm-profile hash + decoded selection-profile hash + NUL + fixed role/prover UTF8 + NUL + decoded key/verifier hash-or-profile + LF)",
    "roster_root_path": "objects.pinned_context.complete_sequence_materialization_roster_root_sha256",
    "roster_root_membership": [f"objects.pinned_context.{field}" for field in independent_identity_fields + independent_public_key_fields + role_fields],
    "roster_root_formula": "SHA256(ASCII KIRA_MIND_V21_COMPLETE_SEQUENCE_MATERIALIZATION_ROSTER_ROOT_V1 + NUL + exact listed path UTF8 and canonical typed value bytes in listed order)",
    "recovery_key_root_path": "objects.pinned_context.complete_sequence_materialization_recovery_key_root_sha256",
    "recovery_members": ["objects.pinned_context.generation_beacon_nonabortable_recovery_key_root_sha256", "objects.pinned_context.deadline_beacon_nonabortable_recovery_key_root_sha256", "objects.pinned_context.generation_sequence_transaction_claim_quorum_public_key_root_sha256", "objects.pinned_context.generation_failure_quorum_public_key_root_sha256"],
    "retained_field_count": len(materialization_byte_rows),
    "rows": materialization_byte_rows,
    "target_signature_proof_anchor_ledger_journal_authority_or_final_cas_byte_may_be_withheld_after_output": False,
    "profile_roster_key_membership_gap_count": 0,
}
inherited_base64_paths = {f"objects.{row['field']}" for row in doc["retained_output_selection_rules"]["inherited_eight"]}
doc["retained_output_selection_rules"]["new_retained_variant_fields"] = [
    row["field_path"].removeprefix("objects.")
    for row in base64_mappings
    if row["field_path"] not in inherited_base64_paths
]
doc["retained_output_selection_rules"]["new_retained_variant_field_count"] = len(doc["retained_output_selection_rules"]["new_retained_variant_fields"])
doc["retained_output_selection_rules"]["total_mapped_retained_variant_field_count"] = len(base64_mappings)

partition = doc["sha256_field_target_partition"]
exact = partition["exact_object_targets"]
exact.update({
    "namespace_precommitment_sha256": "namespace_precommitment",
    "genesis_journal_state_root_sha256": "genesis_journal_state_root_preimage",
    "genesis_journal_state_object_sha256": "genesis_journal_state",
    "genesis_external_anchor_root_sha256": "genesis_external_anchor_evidence",
    "genesis_state_authority_head_evidence_sha256": "genesis_state_authority_evidence",
    "genesis_manifest_sha256": "genesis_manifest",
    "full_genesis_bundle_root_sha256": "singleton_registration_full_genesis_bundle",
    "registrar_policy_profile_bundle_sha256": "registrar_policy_profile_bundle",
    "registrar_authority_key_identity_bundle_sha256": "registrar_authority_key_identity_bundle",
    "pre_request_registration_payload_root_sha256": "singleton_registration_pre_request_payload",
    "assigned_value_root_sha256": "singleton_registration_assigned_value",
    "singleton_registration_request_sha256": "singleton_registration_request",
    "global_registry_sparse_map_leaf_sha256": "global_registry_sparse_map_leaf",
    "global_registry_sparse_map_update_sha256": "global_registry_sparse_map_update",
    "global_registry_sparse_map_proof_sha256": "global_registry_sparse_map_proof",
    "global_registry_post_head_sha256": "global_registry_post_head",
    "global_registry_post_state_sha256": "global_registry_post_state",
    "pre_state_sha256": "authoritative_registry_pre_state",
    "predecessor_singleton_registration_sha256": "singleton_registration_or_exact_global_registry_genesis_predecessor_sentinel",
    "predecessor_registry_post_state_sha256": "global_registry_post_state_or_exact_no_predecessor_registry_post_state_sentinel",
    "namespace_precommitment_root_sha256": "namespace_precommitment_or_exact_global_registry_genesis_namespace_sentinel",
    "pinned_context_root_sha256": "pinned_context_or_exact_global_registry_genesis_context_sentinel",
    "registry_root_sha256": "canonical_global_registry_sparse_map_root",
    "registry_head_sha256": "global_registry_post_head_or_exact_global_registry_genesis_head",
    "previous_head_sha256": "global_registry_post_head_or_exact_global_registry_genesis_head",
    "registry_pre_root_sha256": "canonical_global_registry_sparse_map_root",
    "registry_post_root_sha256": "canonical_global_registry_sparse_map_root",
    "post_global_registry_state_root_sha256": "canonical_global_registry_sparse_map_root",
    "singleton_registration_sha256": "singleton_registration",
    "generation_reservation_sha256": "generation_reservation",
    "generation_sequence_transaction_claim_evidence_sha256": "generation_sequence_transaction_claim_evidence",
    "generation_terminal_outcome_sha256": "generation_terminal_outcome",
    "nonce_generation_reservation_sha256": "generation_reservation",
    "nonce_generation_terminal_outcome_sha256": "generation_terminal_outcome",
    "generation_reservation_ledger_evidence_sha256": "generation_reservation_ledger_evidence",
    "nonce_generation_reservation_ledger_evidence_sha256": "generation_reservation_ledger_evidence",
    "generation_terminal_anchor_evidence_sha256": "generation_terminal_anchor_evidence",
    "nonce_generation_terminal_anchor_evidence_sha256": "generation_terminal_anchor_evidence",
    "generation_reservation_ledger_state_root_sha256": "generation_reservation_ledger_state_root_preimage",
    "generation_reservation_ledger_state_object_sha256": "generation_reservation_ledger_state",
    "expected_pre_reservation_ledger_state_root_sha256": "generation_reservation_ledger_state_root_preimage",
    "expected_pre_reservation_ledger_state_object_sha256": "generation_reservation_ledger_state",
    "pre_reservation_ledger_state_root_sha256": "generation_reservation_ledger_state_root_preimage",
    "post_reservation_ledger_state_root_sha256": "generation_reservation_ledger_state_root_preimage",
    "pre_reservation_ledger_state_object_sha256": "generation_reservation_ledger_state",
    "post_reservation_ledger_state_object_sha256": "generation_reservation_ledger_state",
    "expected_pre_reservation_ledger_head_evidence_sha256": "PATH_COUNTER_CONDITIONED_RESERVATION_LEDGER_HEAD",
    "prior_reservation_ledger_head_evidence_sha256": "PATH_COUNTER_AND_PARENT_ROLE_CONDITIONED_RESERVATION_LEDGER_HEAD",
    "authoritative_pre_journal_state_root_sha256": "PATH_COUNTER_CONDITIONED_JOURNAL_STATE_ROOT",
    "authoritative_pre_journal_state_object_sha256": "PATH_COUNTER_AND_KIND_CONDITIONED_JOURNAL_STATE_OBJECT",
    "authoritative_pre_head_receipt_hash_sha256": "PATH_COUNTER_AND_KIND_CONDITIONED_RECEIPT_OR_FAILURE_HEAD_OR_GENESIS_NULL",
    "authoritative_pre_head_event_hash_sha256": "PATH_COUNTER_AND_KIND_CONDITIONED_EVENT_OR_FAILURE_HEAD_OR_GENESIS_NULL",
    "public_beacon_pre_reveal_evidence_sha256": "public_beacon_pre_reveal_evidence",
    "prior_public_beacon_pre_reveal_evidence_sha256": "public_beacon_pre_reveal_evidence_or_exact_beacon_genesis_null",
    "beacon_reservation_order_evidence_sha256": "beacon_reservation_order_evidence",
    "public_beacon_pre_reveal_state_root_sha256": "public_beacon_pre_reveal_state_root_preimage",
    "public_beacon_pre_reveal_state_object_sha256": "public_beacon_pre_reveal_state",
    "pre_public_beacon_pre_reveal_state_root_sha256": "public_beacon_pre_reveal_state_root_preimage",
    "post_public_beacon_pre_reveal_state_root_sha256": "public_beacon_pre_reveal_state_root_preimage",
    "pre_public_beacon_pre_reveal_state_object_sha256": "public_beacon_pre_reveal_state",
    "post_public_beacon_pre_reveal_state_object_sha256": "public_beacon_pre_reveal_state",
    "public_beacon_reveal_evidence_sha256": "public_beacon_reveal_evidence",
    "pre_witness_technical_health_evidence_sha256": "pre_witness_technical_health_evidence",
    "role_producer_availability_commitment_sha256": "role_producer_availability_commitment",
    "role_producer_availability_evidence_sha256": "role_producer_availability_evidence",
    "terminal_deadline_observation_evidence_sha256": "terminal_deadline_observation_evidence",
    "generation_failure_record_sha256": "generation_failure_record",
    "generation_failure_journal_state_root_sha256": "generation_failure_journal_state_root_preimage",
    "generation_failure_journal_state_object_sha256": "generation_failure_journal_state",
    "post_failure_state_root_sha256": "generation_failure_journal_state_root_preimage",
    "post_failure_state_object_sha256": "generation_failure_journal_state",
    "generation_failure_sequence_commit_evidence_sha256": "generation_failure_sequence_commit_evidence",
    "generation_sequence_lifecycle_refusal_evidence_sha256": "generation_sequence_lifecycle_refusal_evidence",
    "failure_external_anchor_current_head_observation_sha256": "failure_external_anchor_current_head_observation",
    "failure_state_authority_current_head_observation_sha256": "failure_state_authority_current_head_observation",
    "observed_sequence_claim_post_ledger_state_root_sha256": "generation_reservation_ledger_state_root_preimage",
    "observed_sequence_claim_post_ledger_state_object_sha256": "generation_reservation_ledger_state",
    "observed_confidential_generator_image_sha256": "terminal_static_context_exact_equality_copy",
    "observed_confidential_generator_profile_sha256": "terminal_static_context_exact_equality_copy",
    "observed_contributor_roster_sha256": "terminal_static_context_exact_equality_copy",
    "observed_contributor_key_root_sha256": "terminal_static_context_exact_equality_copy",
    "sequence_claim_pre_reservation_ledger_state_root_sha256": "generation_reservation_ledger_state_root_preimage",
    "sequence_claim_post_reservation_ledger_state_root_sha256": "generation_reservation_ledger_state_root_preimage",
    "sequence_claim_pre_reservation_ledger_state_object_sha256": "generation_reservation_ledger_state",
    "sequence_claim_post_reservation_ledger_state_object_sha256": "generation_reservation_ledger_state",
})
for empty_root in ["empty_receipt_token_root_sha256", "empty_scope_token_root_sha256", "empty_proof_token_root_sha256"]:
    if empty_root not in partition["dynamic_accumulator_targets"]:
        partition["dynamic_accumulator_targets"].append(empty_root)
partition["generated_or_authenticated_dynamic_targets"] = [
    "scope_commitment_bytes_sha256", "proof_bytes_sha256", "generated_output_sha256",
    "message_or_statement_root_sha256", "accumulator_proof_statement_root_sha256",
    "reservation_slot_key_sha256", "public_beacon_output_sha256",
    "reservation_ledger_map_root_sha256",
    "genesis_state_nonce_sha256", "reservation_ledger_anchor_statement_sha256",
    "terminal_anchor_statement_sha256",
    "committed_round_output_sha256",
    "public_beacon_vrf_input_message_root_sha256", "deadline_vrf_input_message_root_sha256",
    "deadline_beacon_output_sha256",
    "failure_state_nonce_sha256",
    "active_generation_chain_set_root_sha256",
    "completed_success_role_prefix_root_sha256",
    "unreserved_suffix_cancellation_barrier_root_sha256",
    "failed_sequence_barrier_root_sha256",
    "post_failure_external_anchor_statement_sha256",
    "post_failure_external_anchor_root_sha256",
    "post_failure_state_authority_statement_sha256",
    "post_failure_state_authority_head_evidence_sha256",
    "technical_health_input_vector_sha256",
    "health_predicate_evaluation_root_sha256",
    "fixed_role_lifecycle_order_root_sha256",
    "sequence_transaction_claim_slot_key_sha256",
    "active_sequence_transaction_claim_slot_key_sha256",
    "sequence_transaction_claim_statement_sha256",
    "active_sequence_transaction_claim_statement_sha256",
    "producer_availability_observation_root_sha256",
    "producer_availability_result_root_sha256",
    "role_producer_availability_commitment_statement_sha256",
    "beacon_allocation_slot_key_sha256",
    "beacon_allocation_map_root_sha256",
    "pre_beacon_allocation_map_root_sha256",
    "post_beacon_allocation_map_root_sha256",
    "public_beacon_output_recovery_commitment_sha256",
    "deadline_beacon_output_recovery_commitment_sha256",
    "confidential_seed_derivation_statement_root_sha256",
    "complete_sequence_materialization_commitment_root_sha256",
    "role_terminalization_plan_root_sha256",
    "lifecycle_refusal_statement_root_sha256",
    "refusal_confidential_seed_derivation_statement_root_sha256",
]
terminal = partition.pop("terminal_static_context_targets")
for field in [
    "continuity_namespace_sha256", "stable_global_registry_slot_sha256",
    "namespace_schema_profile_sha256", "runtime_schema_profile_root_sha256", "runtime_role_key_profile_root_sha256",
    "genesis_manifest_profile_sha256", *new_terminal_pins,
]:
    if field not in terminal:
        terminal.append(field)
partition["terminal_static_technical_targets"] = terminal
partition["role_conditioned_static_profile_targets"] = ["generator_profile_sha256", "output_selection_profile_sha256"]
partition["every_new_object_output_and_nested_preimage_is_in_exactly_one_class"] = True
partition["all_base64_fields_have_exact_field_specific_full_byte_generation_and_verification_mapping"] = True

# Replace ambiguous name-level bridge targets with exact occurrence/path and
# counter-conditioned selectors.
path_conditions = {}
def condition(path, rows):
    path_conditions[path] = rows

stable_slot_formula = "SHA256(ASCII KIRA_MIND_V21_STABLE_GLOBAL_REGISTRY_SLOT_FROM_CONTINUITY_NAMESPACE_V1 + actual NUL + exact 32 decoded bytes of objects.namespace_precommitment.continuity_namespace_sha256); no caller slot input alternate namespace encoding or second slot"
for object_name, obj in objects.items():
    if "stable_global_registry_slot_sha256" in obj["field_order"]:
        condition(f"objects.{object_name}.stable_global_registry_slot_sha256", [{"when": "always", "target": stable_slot_formula}])
for aggregate_field in ["runtime_schema_profile_root_sha256", "runtime_role_key_profile_root_sha256"]:
    for object_name, obj in objects.items():
        if aggregate_field in obj["field_order"]:
            condition(f"objects.{object_name}.{aggregate_field}", [{"when": "always", "target": {"exact_aggregate_preimage": doc["namespace_aggregate_root_preimages"][aggregate_field]}}])
doc["stable_registry_slot_derivation"] = {
    "continuity_namespace_path": "objects.namespace_precommitment.continuity_namespace_sha256",
    "stable_slot_formula": stable_slot_formula,
    "request_head_registration_and_context_all_equal_the_recomputed_value": True,
    "caller_selected_alternate_slot_reverse_index_gap_or_second_namespace_genesis_allowed": False,
}
condition("objects.generation_reservation_ledger_state.active_sequence_transaction_claim_slot_key_sha256", [
    {"when": "sequence_transaction_claim_state == UNCLAIMED and reservation_ledger_counter == 0", "target": "objects.pinned_context.generation_sequence_transaction_claim_empty_slot_key_sha256"},
    {"when": "sequence_transaction_claim_state in {HELD_UNTIL_SEQUENCE_COMMIT, RELEASED_BY_EXACT_SEQUENCE_COMMIT}", "target": "exact active generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256 selected by ledger recursion"},
])
condition("objects.generation_reservation_ledger_state.active_sequence_transaction_claim_statement_sha256", [
    {"when": "sequence_transaction_claim_state == UNCLAIMED and reservation_ledger_counter == 0", "target": "objects.pinned_context.generation_sequence_transaction_claim_empty_statement_sha256"},
    {"when": "sequence_transaction_claim_state in {HELD_UNTIL_SEQUENCE_COMMIT, RELEASED_BY_EXACT_SEQUENCE_COMMIT}", "target": "exact active generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256 selected by ledger recursion"},
])
for object_name in ["commit_evidence", "generation_failure_sequence_commit_evidence"]:
    condition(f"objects.{object_name}.sequence_transaction_claim_slot_key_sha256", [{"when": "always", "target": "exact linked generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256"}])
    condition(f"objects.{object_name}.sequence_transaction_claim_statement_sha256", [{"when": "always", "target": "exact linked generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256"}])

for object_name, count_path, root_field, object_field in [
    ("proof_public_inputs", "expected_pre_record_count", "expected_pre_journal_state_root_sha256", "expected_pre_journal_state_object_sha256"),
    ("receipt", "expected_pre_record_count", "expected_pre_journal_state_root_sha256", "expected_pre_journal_state_object_sha256"),
    ("event", "expected_pre_record_count", "expected_pre_journal_state_root_sha256", "expected_pre_journal_state_object_sha256"),
    ("transition_request", "pre_record_count", "pre_journal_state_root_sha256", "pre_journal_state_object_sha256"),
]:
    condition(f"objects.{object_name}.{root_field}", [
        {"when": f"objects.{object_name}.{count_path} == 0", "target": "singleton_registration-authenticated genesis_journal_state.genesis_journal_state_root_sha256"},
        {"when": f"objects.{object_name}.{count_path} > 0 and independently current pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "runtime journal_state.journal_state_root_sha256 with identical context and registration"},
        {"when": f"objects.{object_name}.{count_path} > 0 and independently current pre_state_kind == GENERATION_FAILURE_STATE", "target": "generation_failure_journal_state.generation_failure_journal_state_root_sha256 with identical context registration count and head tuple"},
    ])
    condition(f"objects.{object_name}.{object_field}", [
        {"when": f"objects.{object_name}.{count_path} == 0", "target": "singleton_registration-authenticated genesis_journal_state.genesis_journal_state_object_sha256"},
        {"when": f"objects.{object_name}.{count_path} > 0 and independently current pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "same selected runtime journal_state.journal_state_object_sha256 with identical context and registration"},
        {"when": f"objects.{object_name}.{count_path} > 0 and independently current pre_state_kind == GENERATION_FAILURE_STATE", "target": "same selected generation_failure_journal_state.generation_failure_journal_state_object_sha256 with identical context registration count and head tuple"},
    ])
condition("objects.commit_evidence.cas_expected_pre_state_root_sha256", [
    {"when": "linked transition_request.pre_record_count == 0", "target": "registered genesis_journal_state.genesis_journal_state_root_sha256"},
    {"when": "linked transition_request.pre_record_count > 0 and the exact independently current pre-state selected by its root/object tuple has kind NORMAL_MEMORY_RECORD_STATE", "target": "runtime journal_state.journal_state_root_sha256"},
    {"when": "linked transition_request.pre_record_count > 0 and the exact independently current pre-state selected by its root/object tuple has kind GENERATION_FAILURE_STATE", "target": "generation_failure_journal_state.generation_failure_journal_state_root_sha256"},
])
condition("objects.commit_evidence.committed_pre_state_object_sha256", [
    {"when": "linked transition_request.pre_record_count == 0", "target": "registered genesis_journal_state.genesis_journal_state_object_sha256"},
    {"when": "linked transition_request.pre_record_count > 0 and the exact independently current pre-state selected by its root/object tuple has kind NORMAL_MEMORY_RECORD_STATE", "target": "runtime journal_state.journal_state_object_sha256"},
    {"when": "linked transition_request.pre_record_count > 0 and the exact independently current pre-state selected by its root/object tuple has kind GENERATION_FAILURE_STATE", "target": "generation_failure_journal_state.generation_failure_journal_state_object_sha256"},
])
condition("objects.generation_reservation.authoritative_pre_journal_state_root_sha256", [
    {"when": "authoritative_pre_record_count == 0 and authoritative_pre_state_kind == REGISTERED_GENESIS", "target": "registered genesis_journal_state.genesis_journal_state_root_sha256"},
    {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "exact independently current runtime journal_state.journal_state_root_sha256"},
    {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": "exact independently current generation_failure_journal_state.generation_failure_journal_state_root_sha256"},
])
condition("objects.generation_reservation.authoritative_pre_journal_state_object_sha256", [
    {"when": "authoritative_pre_record_count == 0 and authoritative_pre_state_kind == REGISTERED_GENESIS", "target": "registered genesis_journal_state.genesis_journal_state_object_sha256"},
    {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "same instance as authoritative_pre_journal_state_root_sha256: runtime journal_state.journal_state_object_sha256"},
    {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": "same instance as authoritative_pre_journal_state_root_sha256: generation_failure_journal_state.generation_failure_journal_state_object_sha256"},
])
condition("objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_root_sha256", [
    {"when": "authoritative_pre_record_count == 0 and authoritative_pre_state_kind == REGISTERED_GENESIS", "target": "registered genesis_journal_state.genesis_journal_state_root_sha256"},
    {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "exact independently current runtime journal_state.journal_state_root_sha256"},
    {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": "exact independently current generation_failure_journal_state.generation_failure_journal_state_root_sha256"},
])
condition("objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_object_sha256", [
    {"when": "authoritative_pre_record_count == 0 and authoritative_pre_state_kind == REGISTERED_GENESIS", "target": "registered genesis_journal_state.genesis_journal_state_object_sha256"},
    {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "same exact runtime journal_state instance as authoritative_pre_journal_state_root_sha256"},
    {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": "same exact generation_failure_journal_state instance as authoritative_pre_journal_state_root_sha256"},
])
for field_name, head_kind in [("authoritative_pre_head_receipt_hash_sha256", "receipt"), ("authoritative_pre_head_event_hash_sha256", "event")]:
    condition(f"objects.generation_sequence_transaction_claim_evidence.{field_name}", [
        {"when": "authoritative_pre_record_count == 0 and authoritative_pre_state_kind == REGISTERED_GENESIS", "target": "JSON null only"},
        {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": f"exact current runtime journal_state.head_{head_kind}_hash_sha256"},
        {"when": "authoritative_pre_record_count > 0 and authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": f"exact current generation_failure_journal_state.head_{head_kind}_hash_sha256 canonical failure sentinel"},
    ])
for field_name, kind_field in [("pre_journal_state_root_sha256", "pre_state_kind"), ("pre_journal_state_object_sha256", "pre_state_kind")]:
    condition(f"objects.generation_failure_sequence_commit_evidence.{field_name}", [
        {"when": f"pre_record_count == 0 and {kind_field} == REGISTERED_GENESIS", "target": "exact singleton-registration authenticated genesis journal state matching root/object role"},
        {"when": f"pre_record_count > 0 and {kind_field} == NORMAL_MEMORY_RECORD_STATE", "target": "exact independently current runtime journal state matching root/object role"},
        {"when": f"pre_record_count > 0 and {kind_field} == GENERATION_FAILURE_STATE", "target": "exact independently current generation-failure journal state matching root/object role"},
    ])
condition("objects.generation_failure_journal_state.head_receipt_hash_sha256", [{"when": "always", "target": "SHA256(KIRA_MIND_V21_FAILURE_RECEIPT_HEAD_V1 + NUL + generation_failure_record_sha256 bytes)"}])
condition("objects.generation_failure_journal_state.head_event_hash_sha256", [{"when": "always", "target": "SHA256(KIRA_MIND_V21_FAILURE_EVENT_HEAD_V1 + NUL + generation_failure_record_sha256 bytes)"}])
condition("objects.generation_failure_sequence_commit_evidence.post_head_receipt_hash_sha256", [{"when": "always", "target": "exact same generation_failure_journal_state instance head_receipt_hash_sha256"}])
condition("objects.generation_failure_sequence_commit_evidence.post_head_event_hash_sha256", [{"when": "always", "target": "exact same generation_failure_journal_state instance head_event_hash_sha256"}])
for observation_object in [
    "failure_external_anchor_current_head_observation",
    "failure_state_authority_current_head_observation",
]:
    condition(f"objects.{observation_object}.post_head_receipt_hash_sha256", [{
        "when": "always",
        "target": "exact selected generation_failure_sequence_commit_evidence/generation_failure_journal_state receipt-head sentinel SHA256(KIRA_MIND_V21_FAILURE_RECEIPT_HEAD_V1 + NUL + exact same generation_failure_record_sha256 bytes); never a normal receipt object",
    }])
    condition(f"objects.{observation_object}.post_head_event_hash_sha256", [{
        "when": "always",
        "target": "exact selected generation_failure_sequence_commit_evidence/generation_failure_journal_state event-head sentinel SHA256(KIRA_MIND_V21_FAILURE_EVENT_HEAD_V1 + NUL + exact same generation_failure_record_sha256 bytes); never a normal event object",
    }])
failure_accumulator_paths = {
    "receipt": ("consumed_receipt_token_root_sha256", "pre_receipt_token_root_sha256", "post_receipt_token_root_sha256"),
    "scope": ("consumed_scope_token_root_sha256", "pre_scope_token_root_sha256", "post_scope_token_root_sha256"),
    "proof": ("consumed_proof_token_root_sha256", "pre_proof_token_root_sha256", "post_proof_token_root_sha256"),
}
for accumulator_name, (state_field, pre_field, post_field) in failure_accumulator_paths.items():
    condition(f"objects.generation_failure_record.{pre_field}", [{"when": "always", "target": f"exact instances.current_pre_journal_state.{state_field} selected by pre-state kind; no accumulator proof is created on technical failure"}])
    condition(f"objects.generation_failure_record.{post_field}", [{"when": "always", "target": f"exact byte-identical objects.generation_failure_record.{pre_field}; no token is accepted"}])
    condition(f"objects.generation_failure_journal_state.{state_field}", [{"when": "always", "target": f"exact objects.generation_failure_record.{post_field} for the same first-failed role and sequence"}])
    condition(f"objects.generation_failure_sequence_commit_evidence.{pre_field}", [{"when": "always", "target": f"exact objects.generation_failure_record.{pre_field} and instances.current_pre_journal_state.{state_field}"}])
    condition(f"objects.generation_failure_sequence_commit_evidence.{post_field}", [{"when": "always", "target": f"exact objects.generation_failure_record.{post_field} and same failure post-state {state_field}"}])

# A positive predecessor can be either a normal memory-record state or the
# canonical technical-failure state.  The latter carries domain-separated head
# sentinels, not fabricated receipt/event objects.  JSON null remains exclusive
# to the registered counter-zero genesis.
predecessor_head_paths = {
    "proof_public_inputs": {
        "count": "expected_pre_record_count",
        "receipt": ["previous_receipt_hash_sha256", "expected_pre_head_receipt_hash_sha256"],
        "event": ["expected_pre_head_event_hash_sha256"],
    },
    "receipt": {
        "count": "expected_pre_record_count",
        "receipt": ["previous_receipt_hash_sha256", "expected_pre_head_receipt_hash_sha256"],
        "event": ["expected_pre_head_event_hash_sha256"],
    },
    "event": {
        "count": "expected_pre_record_count",
        "receipt": ["receipt_previous_receipt_hash_sha256", "expected_pre_head_receipt_hash_sha256"],
        "event": ["previous_event_hash_sha256", "expected_pre_head_event_hash_sha256"],
    },
    "transition_request": {
        "count": "pre_record_count",
        "receipt": ["pre_head_receipt_hash_sha256", "receipt_previous_receipt_hash_sha256"],
        "event": ["pre_head_event_hash_sha256", "event_previous_event_hash_sha256"],
    },
    "generation_failure_sequence_commit_evidence": {
        "count": "pre_record_count",
        "receipt": ["pre_head_receipt_hash_sha256"],
        "event": ["pre_head_event_hash_sha256"],
    },
}
for object_name, selector in predecessor_head_paths.items():
    count_field = selector["count"]
    for head_kind, field_names in (("receipt", selector["receipt"]), ("event", selector["event"])):
        normal_target = f"exact {head_kind}.{head_kind}_hash_sha256 selected as the current normal journal-state {head_kind} head"
        failure_target = f"exact current generation_failure_journal_state.head_{head_kind}_hash_sha256 = SHA256(KIRA_MIND_V21_FAILURE_{head_kind.upper()}_HEAD_V1 + NUL + its generation_failure_record_sha256 bytes); no {head_kind} object is fabricated"
        for field_name in field_names:
            condition(f"objects.{object_name}.{field_name}", [
                {"when": f"objects.{object_name}.{count_field} == 0 and independently current pre-state kind == REGISTERED_GENESIS", "target": "JSON null only"},
                {"when": f"objects.{object_name}.{count_field} > 0 and independently current pre-state kind == NORMAL_MEMORY_RECORD_STATE", "target": normal_target},
                {"when": f"objects.{object_name}.{count_field} > 0 and independently current pre-state kind == GENERATION_FAILURE_STATE", "target": failure_target},
            ])

# Every occurrence of the inherited head field names receives its own exact
# selector.  A shared name-level placeholder is never an executable target.
condition("objects.journal_state.head_receipt_hash_sha256", [{"when": "committed_record_count > 0", "target": "exact receipt.receipt_hash_sha256 at journal_state.head_sequence in the same committed transition"}])
condition("objects.journal_state.head_event_hash_sha256", [{"when": "committed_record_count > 0", "target": "exact event.event_hash_sha256 at journal_state.head_sequence in the same committed transition"}])
condition("objects.transition_request.post_head_receipt_hash_sha256", [{"when": "always", "target": "exact linked receipt.receipt_hash_sha256 and receipt.sequence == receipt_sequence"}])
condition("objects.transition_request.post_head_event_hash_sha256", [{"when": "always", "target": "exact linked event.event_hash_sha256 and event.sequence == receipt_sequence"}])
for object_name, state_root_field in [
    ("state_authority_head_evidence", "head_journal_state_root_sha256"),
    ("external_anchor_evidence", "journal_state_root_sha256"),
]:
    condition(f"objects.{object_name}.head_receipt_hash_sha256", [{
        "when": "committed_record_count > 0",
        "target": f"head_receipt_hash_sha256 of the exact runtime journal_state instance selected by objects.{object_name}.{state_root_field}",
    }])
    condition(f"objects.{object_name}.head_event_hash_sha256", [{
        "when": "committed_record_count > 0",
        "target": f"head_event_hash_sha256 of the exact runtime journal_state instance selected by objects.{object_name}.{state_root_field}",
    }])
for object_name in [
    "genesis_journal_state", "genesis_external_anchor_evidence",
    "genesis_state_authority_evidence", "genesis_manifest",
]:
    condition(f"objects.{object_name}.head_receipt_hash_sha256", [{
        "when": "registered typed genesis committed_record_count == 0",
        "target": "JSON null only",
    }])
    condition(f"objects.{object_name}.head_event_hash_sha256", [{
        "when": "registered typed genesis committed_record_count == 0",
        "target": "JSON null only",
    }])

condition("objects.generation_failure_sequence_commit_evidence.pre_state_authority_head_evidence_sha256", [
    {"when": "pre_record_count == 0 and pre_state_kind == REGISTERED_GENESIS and pre_state_authority_monotonic_counter == 0", "target": "exact singleton_registration_full_genesis_bundle.genesis_state_authority_head_evidence_sha256 and byte-available genesis_state_authority_evidence"},
    {"when": "pre_record_count > 0 and pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "exact independently current runtime state_authority_head_evidence at pre_state_authority_monotonic_counter authenticating pre_journal_state_root_sha256 and pre_journal_state_object_sha256"},
    {"when": "pre_record_count > 0 and pre_state_kind == GENERATION_FAILURE_STATE", "target": "exact independently current prior generation_failure_sequence_commit_evidence.post_failure_state_authority_head_evidence_sha256 at pre_state_authority_monotonic_counter authenticating the same failure pre-state"},
])
condition("objects.generation_failure_sequence_commit_evidence.pre_external_anchor_root_sha256", [
    {"when": "pre_record_count == 0 and pre_state_kind == REGISTERED_GENESIS and pre_external_anchor_monotonic_counter == 0", "target": "exact singleton_registration_full_genesis_bundle.genesis_external_anchor_root_sha256 and byte-available genesis_external_anchor_evidence"},
    {"when": "pre_record_count > 0 and pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "exact independently current runtime external_anchor_evidence.external_anchor_root_sha256 at pre_external_anchor_monotonic_counter authenticating pre_journal_state_root_sha256 and pre_journal_state_object_sha256"},
    {"when": "pre_record_count > 0 and pre_state_kind == GENERATION_FAILURE_STATE", "target": "exact independently current prior generation_failure_sequence_commit_evidence.post_failure_external_anchor_root_sha256 at pre_external_anchor_monotonic_counter authenticating the same failure pre-state"},
])
for object_name, counter_field, authority_field, anchor_field in [
    ("proof_public_inputs", "expected_pre_state_authority_counter", "expected_pre_state_authority_head_evidence_sha256", "expected_pre_external_anchor_root_sha256"),
    ("receipt", "expected_pre_state_authority_counter", "expected_pre_state_authority_head_evidence_sha256", "expected_pre_external_anchor_root_sha256"),
    ("event", "expected_pre_state_authority_counter", "expected_pre_state_authority_head_evidence_sha256", "expected_pre_external_anchor_root_sha256"),
    ("transition_request", "pre_state_authority_counter", "pre_state_authority_head_evidence_sha256", "pre_external_anchor_root_sha256"),
    ("commit_evidence", "pre_state_authority_counter", "pre_state_authority_head_evidence_sha256", "pre_external_anchor_root_sha256"),
]:
    condition(f"objects.{object_name}.{authority_field}", [
        {"when": f"objects.{object_name}.{counter_field} == 0", "target": "singleton_registration-authenticated genesis_state_authority_evidence"},
        {"when": f"objects.{object_name}.{counter_field} > 0 and independently current journal state kind == NORMAL_MEMORY_RECORD_STATE", "target": "runtime state_authority_head_evidence at exact counter"},
        {"when": f"objects.{object_name}.{counter_field} > 0 and independently current journal state kind == GENERATION_FAILURE_STATE", "target": "generation_failure_sequence_commit_evidence.post_failure_state_authority_head_evidence_sha256 at exact counter and same failure post-state"},
    ])
    condition(f"objects.{object_name}.{anchor_field}", [
        {"when": f"objects.{object_name}.{counter_field} == 0", "target": "singleton_registration-authenticated genesis_external_anchor_evidence"},
        {"when": f"objects.{object_name}.{counter_field} > 0 and independently current journal state kind == NORMAL_MEMORY_RECORD_STATE", "target": "runtime external_anchor_evidence at exact counter"},
        {"when": f"objects.{object_name}.{counter_field} > 0 and independently current journal state kind == GENERATION_FAILURE_STATE", "target": "generation_failure_sequence_commit_evidence.post_failure_external_anchor_root_sha256 at exact counter and same failure post-state"},
    ])
condition("objects.generation_sequence_transaction_claim_evidence.pre_state_authority_head_evidence_sha256", [
    {"when": "pre_state_authority_counter == 0 and authoritative_pre_state_kind == REGISTERED_GENESIS", "target": "singleton_registration-authenticated genesis_state_authority_evidence"},
    {"when": "pre_state_authority_counter > 0 and authoritative_pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "exact independently current runtime state_authority_head_evidence authenticating the claim pre-state"},
    {"when": "pre_state_authority_counter > 0 and authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": "exact prior failure-commit post_failure_state_authority_head_evidence_sha256 authenticating the claim pre-state"},
])
condition("objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_root_sha256", [
    {"when": "pre_external_anchor_counter == 0 and authoritative_pre_state_kind == REGISTERED_GENESIS", "target": "singleton_registration-authenticated genesis_external_anchor_evidence"},
    {"when": "pre_external_anchor_counter > 0 and authoritative_pre_state_kind == NORMAL_MEMORY_RECORD_STATE", "target": "exact independently current runtime external_anchor_evidence authenticating the claim pre-state"},
    {"when": "pre_external_anchor_counter > 0 and authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": "exact prior failure-commit post_failure_external_anchor_root_sha256 authenticating the claim pre-state"},
])
condition("objects.state_authority_head_evidence.prior_state_authority_head_evidence_sha256", [
    {"when": "authority_monotonic_counter == 1", "target": "registered genesis_state_authority_evidence at counter 0"},
    {"when": "authority_monotonic_counter > 1 and independently current prior journal state kind == NORMAL_MEMORY_RECORD_STATE", "target": "runtime state_authority_head_evidence at checked counter minus one"},
    {"when": "authority_monotonic_counter > 1 and independently current prior journal state kind == GENERATION_FAILURE_STATE", "target": "generation_failure_sequence_commit_evidence.post_failure_state_authority_head_evidence_sha256 at checked counter minus one"},
])
condition("objects.state_authority_head_evidence.prior_external_anchor_root_sha256", [
    {"when": "authority_monotonic_counter == 1", "target": "registered genesis_external_anchor_evidence at counter 0"},
    {"when": "authority_monotonic_counter > 1 and independently current prior journal state kind == NORMAL_MEMORY_RECORD_STATE", "target": "runtime external_anchor_evidence at checked counter minus one"},
    {"when": "authority_monotonic_counter > 1 and independently current prior journal state kind == GENERATION_FAILURE_STATE", "target": "generation_failure_sequence_commit_evidence.post_failure_external_anchor_root_sha256 at checked counter minus one"},
])
condition("objects.external_anchor_evidence.prior_external_anchor_root_sha256", [
    {"when": "anchor_monotonic_counter == 1", "target": "registered genesis_external_anchor_evidence at counter 0"},
    {"when": "anchor_monotonic_counter > 1 and independently current prior journal state kind == NORMAL_MEMORY_RECORD_STATE", "target": "runtime external_anchor_evidence at checked counter minus one"},
    {"when": "anchor_monotonic_counter > 1 and independently current prior journal state kind == GENERATION_FAILURE_STATE", "target": "generation_failure_sequence_commit_evidence.post_failure_external_anchor_root_sha256 at checked counter minus one"},
])
for object_name in ["genesis_state_authority_evidence", "genesis_manifest"]:
    condition(f"objects.{object_name}.prior_state_authority_head_evidence_sha256", [{"when": "registered genesis exact counter zero", "target": "JSON null only"}])
for object_name in ["genesis_external_anchor_evidence", "genesis_state_authority_evidence", "genesis_manifest"]:
    condition(f"objects.{object_name}.prior_external_anchor_root_sha256", [{"when": "registered genesis exact counter zero", "target": "JSON null only"}])
condition("objects.public_beacon_pre_reveal_evidence.prior_public_beacon_pre_reveal_evidence_sha256", [
    {"when": "pre_public_beacon_pre_reveal_state_counter == 0 and post/head counter == 1", "target": "JSON null and exact typed public_beacon_pre_reveal_state counter-zero base derived from singleton registration plus pinned public_beacon_pre_reveal_genesis_manifest_sha256"},
    {"when": "pre_public_beacon_pre_reveal_state_counter > 0", "target": "byte-available prior public_beacon_pre_reveal_evidence whose post root object and counter equal current pre root object and counter"},
])
condition("objects.generation_reservation.expected_pre_reservation_ledger_head_evidence_sha256", [
    {"when": "output_role == SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "target": "exact current generation_sequence_transaction_claim_evidence whose post ledger root object counter and HELD statement equal this expected pre-state"},
    {"when": "output_role is any later exact lifecycle role", "target": "byte-available immediately prior lifecycle role generation_terminal_anchor_evidence whose post ledger root object and counter equal this expected pre-state and whose active sequence claim remains HELD"},
])
condition("objects.generation_reservation_ledger_evidence.prior_reservation_ledger_head_evidence_sha256", [
    {"when": "output_role == SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "target": "exact current generation_sequence_transaction_claim_evidence whose post ledger root object counter and HELD statement equal this pre-state"},
    {"when": "output_role is any later exact lifecycle role", "target": "byte-available immediately prior lifecycle role generation_terminal_anchor_evidence whose post ledger root object and counter equal this pre-state and whose active sequence claim remains HELD"},
])
claim_prior_reservation_ledger_head_branches = [
    {
        "when": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_counter == 0 and objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind == REGISTERED_GENESIS",
        "target": "exact JSON null and exact registered reservation-ledger counter-zero state root/object with UNCLAIMED",
    },
    {
        "when": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_counter > 0 and objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind == NORMAL_MEMORY_RECORD_STATE",
        "target": "instances.prior_normal_sequence_claim_release_commit.commit_evidence_sha256 whose atomic sequence-claim release post ledger root object counter and RELEASED state equal this exact acquisition pre-state",
    },
    {
        "when": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_counter > 0 and objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind == GENERATION_FAILURE_STATE and instances.prior_failure_sequence_claim_release_commit.failure_trigger in {PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,ROLE_TERMINAL_FAILED,HIDDEN_LIFECYCLE_REFUSAL}",
        "target": "instances.prior_failure_sequence_claim_release_commit.generation_failure_sequence_commit_evidence_sha256 whose atomic sequence-claim release post ledger root object counter and RELEASED state equal this exact acquisition pre-state",
    },
]
condition(
    "objects.generation_sequence_transaction_claim_evidence.prior_reservation_ledger_head_evidence_sha256",
    claim_prior_reservation_ledger_head_branches,
)
for field_name, target in {
    "pre_reservation_ledger_state_root_sha256": "instances.sequence_claim_acquire_pre_state.generation_reservation_ledger_state_root_sha256",
    "pre_reservation_ledger_state_object_sha256": "instances.sequence_claim_acquire_pre_state.generation_reservation_ledger_state_object_sha256",
    "post_reservation_ledger_state_root_sha256": "instances.sequence_claim_acquire_post_state.generation_reservation_ledger_state_root_sha256",
    "post_reservation_ledger_state_object_sha256": "instances.sequence_claim_acquire_post_state.generation_reservation_ledger_state_object_sha256",
}.items():
    condition(f"objects.generation_sequence_transaction_claim_evidence.{field_name}", [{"when": "always", "target": target}])
for field_name, target in {
    "pre_reservation_ledger_state_root_sha256": "instances.roles.<exact output_role>.ledger_pre_state.generation_reservation_ledger_state_root_sha256",
    "pre_reservation_ledger_state_object_sha256": "instances.roles.<exact output_role>.ledger_pre_state.generation_reservation_ledger_state_object_sha256",
    "post_reservation_ledger_state_root_sha256": "instances.roles.<exact output_role>.ledger_reserved_state.generation_reservation_ledger_state_root_sha256",
    "post_reservation_ledger_state_object_sha256": "instances.roles.<exact output_role>.ledger_reserved_state.generation_reservation_ledger_state_object_sha256",
}.items():
    condition(f"objects.generation_reservation_ledger_evidence.{field_name}", [
        {"when": f"output_role == {role}", "target": target.replace("<exact output_role>", role)}
        for role in role_lifecycle_order
    ])
for field_name, target in {
    "pre_reservation_ledger_state_root_sha256": "instances.roles.<exact output_role>.ledger_reserved_state.generation_reservation_ledger_state_root_sha256",
    "pre_reservation_ledger_state_object_sha256": "instances.roles.<exact output_role>.ledger_reserved_state.generation_reservation_ledger_state_object_sha256",
    "post_reservation_ledger_state_root_sha256": "instances.roles.<exact output_role>.ledger_consumed_state.generation_reservation_ledger_state_root_sha256",
    "post_reservation_ledger_state_object_sha256": "instances.roles.<exact output_role>.ledger_consumed_state.generation_reservation_ledger_state_object_sha256",
}.items():
    condition(f"objects.generation_terminal_anchor_evidence.{field_name}", [
        {"when": f"output_role == {role}", "target": target.replace("<exact output_role>", role)}
        for role in role_lifecycle_order
    ])
for field_name, target in {
    "sequence_claim_pre_reservation_ledger_state_root_sha256": "instances.roles.COMMIT_EVIDENCE_COMMIT_NONCE.ledger_consumed_state.generation_reservation_ledger_state_root_sha256",
    "sequence_claim_pre_reservation_ledger_state_object_sha256": "instances.roles.COMMIT_EVIDENCE_COMMIT_NONCE.ledger_consumed_state.generation_reservation_ledger_state_object_sha256",
    "sequence_claim_post_reservation_ledger_state_root_sha256": "instances.sequence_claim_normal_release_post_state.generation_reservation_ledger_state_root_sha256",
    "sequence_claim_post_reservation_ledger_state_object_sha256": "instances.sequence_claim_normal_release_post_state.generation_reservation_ledger_state_object_sha256",
}.items():
    condition(f"objects.commit_evidence.{field_name}", [{"when": "all ten exact role outcomes are SUCCESS", "target": target}])
for field_name, state_field in {
    "sequence_claim_pre_reservation_ledger_state_root_sha256": "generation_reservation_ledger_state_root_sha256",
    "sequence_claim_pre_reservation_ledger_state_object_sha256": "generation_reservation_ledger_state_object_sha256",
}.items():
    branches = []
    for role in role_lifecycle_order:
        branches.extend([
            {"when": f"linked failure_trigger == ROLE_TERMINAL_FAILED and linked generation_failure_record.output_role == {role}", "target": f"instances.roles.{role}.ledger_consumed_state.{state_field}"},
            {"when": f"linked failure_trigger in {{PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,HIDDEN_LIFECYCLE_REFUSAL}} and linked generation_failure_record.output_role == {role}", "target": f"instances.roles.{role}.ledger_pre_state.{state_field}"},
        ])
    condition(f"objects.generation_failure_sequence_commit_evidence.{field_name}", branches)
for field_name, state_field in {
    "sequence_claim_post_reservation_ledger_state_root_sha256": "generation_reservation_ledger_state_root_sha256",
    "sequence_claim_post_reservation_ledger_state_object_sha256": "generation_reservation_ledger_state_object_sha256",
}.items():
    condition(f"objects.generation_failure_sequence_commit_evidence.{field_name}", [
        {"when": f"linked generation_failure_record.output_role == {role} under any exact failure_trigger", "target": f"instances.roles.{role}.sequence_claim_failure_release_post_state.{state_field}"}
        for role in role_lifecycle_order
    ])
condition("objects.generation_terminal_anchor_evidence.prior_reservation_ledger_head_evidence_sha256", [
    {"when": "pre_slot_state == RESERVED_ATTEMPT_ZERO", "target": "exact generation_reservation_ledger_evidence for same slot reservation and pre-root"},
])

for field_name in [
    "generation_reservation_sha256", "generation_reservation_ledger_evidence_sha256",
    "public_beacon_reveal_evidence_sha256", "terminal_deadline_observation_evidence_sha256",
    "generation_terminal_outcome_sha256", "generation_terminal_anchor_evidence_sha256",
]:
    condition(f"objects.generation_failure_record.{field_name}", [
        {"when": "failure_trigger == ROLE_TERMINAL_FAILED", "target": f"canonical SHA-256 of the exact first-failed role {field_name.removesuffix('_sha256')} instance"},
        {"when": "failure_trigger in {PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,HIDDEN_LIFECYCLE_REFUSAL}", "target": "exact JSON null because the boundary role chain was never created"},
    ])
condition("objects.generation_failure_record.generation_sequence_lifecycle_refusal_evidence_sha256", [
    {"when": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL", "target": "canonical SHA-256 of the exact generic hidden lifecycle-refusal evidence at this boundary"},
    {"when": "failure_trigger in {PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,ROLE_TERMINAL_FAILED}", "target": "exact JSON null"},
])
condition("objects.generation_failure_sequence_commit_evidence.generation_terminal_anchor_evidence_sha256", [
    {"when": "failure_trigger == ROLE_TERMINAL_FAILED", "target": "canonical SHA-256 of the exact first-failed role terminal anchor"},
    {"when": "failure_trigger in {PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,HIDDEN_LIFECYCLE_REFUSAL}", "target": "exact JSON null"},
])
condition("objects.generation_failure_sequence_commit_evidence.generation_sequence_lifecycle_refusal_evidence_sha256", [
    {"when": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL", "target": "canonical SHA-256 of the exact generic hidden lifecycle-refusal evidence"},
    {"when": "failure_trigger in {PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,ROLE_TERMINAL_FAILED}", "target": "exact JSON null"},
])
condition("objects.generation_sequence_transaction_claim_evidence.failure_external_anchor_current_head_observation_sha256", [
    {"when": "authoritative_pre_state_kind in {REGISTERED_GENESIS,NORMAL_MEMORY_RECORD_STATE}", "target": "exact JSON null"},
    {"when": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": "exact independently current failure_external_anchor_current_head_observation whose failure successor tuple equals the claim current pre-state"},
])
condition("objects.generation_sequence_transaction_claim_evidence.failure_state_authority_current_head_observation_sha256", [
    {"when": "authoritative_pre_state_kind in {REGISTERED_GENESIS,NORMAL_MEMORY_RECORD_STATE}", "target": "exact JSON null"},
    {"when": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE", "target": "exact independently current failure_state_authority_current_head_observation consuming the same anchor observation and successor tuple"},
])

nullable_sha256_rows = []
for object_name, obj in objects.items():
    for field_name, field_type in zip(obj["field_order"], obj["field_types"]):
        if field_type != "nullable_sha256":
            continue
        path = f"objects.{object_name}.{field_name}"
        if path in {
            "objects.generation_terminal_outcome.generated_output_sha256",
            "objects.generation_terminal_anchor_evidence.generated_output_sha256",
        }:
            exact_rule = "linked terminal_outcome SUCCESS requires exactly one lowercase SHA-256 of the generated full output; linked terminal_outcome FAILED requires JSON null; no other null condition"
        elif path == "objects.generation_terminal_outcome.confidential_seed_derivation_statement_root_sha256":
            exact_rule = "output_generation_mode == CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING and terminal_outcome == SUCCESS requires the exact nonnull domain-separated confidential-seed statement; UNIQUE_DETERMINISTIC_BYTES or FAILED requires exact JSON null and forbids any private seed/witness path"
        elif path in path_conditions:
            exact_rule = {"path_counter_conditions": path_conditions[path]}
        elif object_name in base_doc["objects"] and field_name in base_doc["objects"][object_name]["field_order"]:
            exact_rule = "exact inherited V20 object-specific counter-zero/genesis/predecessor nullability rule remains unchanged; positive runtime predecessor or head condition requires canonical SHA-256"
        elif field_name.startswith("prior_") or field_name.startswith("expected_pre_") or field_name.startswith("authoritative_pre_"):
            exact_rule = "JSON null iff the explicitly named checked counter is zero and the exact typed registered genesis/base object is selected; otherwise canonical SHA-256 of the byte-available predecessor"
        else:
            exact_rule = "canonical SHA-256 unless the enclosing schema's explicit checked counter-zero base condition requires JSON null; no caller-selected null"
        nullable_sha256_rows.append({"path": path, "exact_rule": exact_rule})
doc["path_qualified_nullable_sha256_rules"] = {
    "occurrence_count": len(nullable_sha256_rows),
    "failed_generated_output_exception_paths": [
        "objects.generation_terminal_outcome.generated_output_sha256",
        "objects.generation_terminal_anchor_evidence.generated_output_sha256",
    ],
    "mode_and_branch_conditioned_confidential_seed_exception_paths": [
        "objects.generation_terminal_outcome.confidential_seed_derivation_statement_root_sha256",
    ],
    "rows": nullable_sha256_rows,
    "gap_extra_overlap_or_unconditional_null_count": 0,
}

# Preserve the concrete default for every occurrence before the legacy
# name-level table is redirected to the path-qualified table.  A name may be
# counter/branch conditioned at only some paths while its ordinary link/self
# hash occurrences still have one exact object target.
exact_occurrence_defaults = dict(exact)
for ambiguous_name in {
    path.rsplit(".", 1)[1] for path in path_conditions
}:
    if ambiguous_name in exact:
        exact[ambiguous_name] = {
            "name_level_target_is_not_executable": True,
            "ordinary_occurrence_default": exact_occurrence_defaults[ambiguous_name],
            "conditioned_occurrence_rows": [
                {"path": path, "branches": path_conditions[path]}
                for path in sorted(path_conditions)
                if path.rsplit(".", 1)[1] == ambiguous_name
            ],
            "validator_rule": "resolve the one exact full-path occurrence and its mutually exclusive branch; field-name-only target selection is forbidden",
        }

role_conditioned_rows = []
for object_name, context_path in selection_context_by_object.items():
    if "output_selection_profile_sha256" in objects[object_name]["field_order"]:
        role_conditioned_rows.append({"left_path": f"objects.{object_name}.output_selection_profile_sha256", "right_path": context_path, "condition": f"exact {object_name} field-specific output profile"})
role_conditioned_rows.append({
    "left_path": "objects.generation_reservation.generator_profile_sha256",
    "right_path_by_output_role": {row["role"]: row["generator_profile_context_path"] for row in output_role_table},
    "condition": "exact output_role bijection; aliases swaps and cross-role profiles refuse",
})

class_membership = {}
for name in exact:
    class_membership.setdefault(name, []).append("exact_object_or_counter_conditioned_target")
for name in partition["dynamic_accumulator_targets"]:
    class_membership.setdefault(name, []).append("dynamic_accumulator_target")
for name in partition["generated_or_authenticated_dynamic_targets"]:
    class_membership.setdefault(name, []).append("generated_authenticated_dynamic_target")
for name in terminal:
    class_membership.setdefault(name, []).append("terminal_static_context_target")
for name in partition["role_conditioned_static_profile_targets"]:
    class_membership.setdefault(name, []).append("role_conditioned_static_profile_target")

def exact_generated_selector(path, object_name, field_name):
    if field_name == "producer_availability_observation_root_sha256":
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_sequence_transaction_claim_evidence_sha256", "pre_witness_technical_health_evidence_sha256", "reserved_sequence", "output_role", "role_lifecycle_index", "output_attempt_index", "public_beacon_pre_reveal_evidence_sha256", "beacon_allocation_slot_key_sha256", "post_public_beacon_pre_reveal_state_root_sha256", "post_public_beacon_pre_reveal_state_object_sha256", "post_public_beacon_pre_reveal_state_counter", "public_round_index", "generation_reservation_sha256", "reservation_slot_key_sha256", "generation_reservation_ledger_evidence_sha256", "post_reservation_ledger_state_root_sha256", "post_reservation_ledger_state_object_sha256", "post_reservation_ledger_counter", "beacon_reservation_order_evidence_sha256", "producer_availability_predicate_sha256", "producer_availability_observation_profile_sha256", "producer_availability_authority_identity_sha256"]
        source = "role_producer_availability_commitment" if object_name == "role_producer_availability_commitment" else "role_producer_availability_evidence"
        return {"domain": "KIRA_MIND_V21_ROLE_PRODUCER_AVAILABILITY_OBSERVATION_ROOT_V1", "ordered_field_paths": [f"objects.{source}.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); all inputs exist before reveal and no output proof seed witness scope or later branch is reachable"}
    if field_name == "producer_availability_result_root_sha256":
        source = "role_producer_availability_commitment" if object_name == "role_producer_availability_commitment" else "role_producer_availability_evidence"
        fields = ["producer_availability_observation_root_sha256", "producer_availability_predicate_sha256", "producer_availability_profile_sha256", "producer_availability_result_profile_sha256", "producer_availability_authority_identity_sha256"]
        result_field = "committed_producer_availability_result" if object_name == "role_producer_availability_commitment" else "producer_availability_result"
        return {"domain": "KIRA_MIND_V21_ROLE_PRODUCER_AVAILABILITY_RESULT_ROOT_V1", "ordered_field_paths": [f"objects.{source}.{field}" for field in fields] + [f"objects.{source}.{result_field}"], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); the result is mechanically derived before reveal and the evidence must equal the committed result"}
    if field_name == "role_producer_availability_commitment_statement_sha256":
        fields = [field for field in objects["role_producer_availability_commitment"]["field_order"] if field not in {"role_producer_availability_commitment_statement_sha256", "role_producer_availability_commitment_sha256"}]
        return {"domain": "KIRA_MIND_V21_ROLE_PRODUCER_AVAILABILITY_COMMITMENT_STATEMENT_V1", "ordered_field_paths": [f"objects.role_producer_availability_commitment.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); excludes statement and self hash and is fixed before reveal"}
    if field_name == "beacon_allocation_slot_key_sha256":
        return "SHA256(ASCII KIRA_MIND_V21_BEACON_ALLOCATION_SLOT_KEY_V1 + NUL + singleton_registration bytes + NUL + journal_epoch uint64-be + NUL + reserved sequence uint64-be + NUL + exact output-role ASCII + NUL + attempt-zero byte); every pre-reveal reservation ledger order reveal outcome and anchor copy is byte-identical"
    if field_name in {"beacon_allocation_map_root_sha256", "pre_beacon_allocation_map_root_sha256", "post_beacon_allocation_map_root_sha256"}:
        return {"counter_zero": "exact objects.pinned_context.public_beacon_allocation_empty_map_root_sha256", "positive": "exact canonical sparse-map root under objects.pinned_context.public_beacon_allocation_map_profile_sha256; the pre-reveal allocation proof changes exactly one derived allocation slot UNASSIGNED to ALLOCATED_PRE_REVEAL and no second write is accepted", "same_instance": "pre/post state aliases and evidence copies bind one exact map transition"}
    if field_name == "public_beacon_output_recovery_commitment_sha256":
        fields = ["pre_witness_technical_health_evidence_sha256", "singleton_registration_sha256", "journal_epoch", "reserved_sequence", "output_role", "output_attempt_index_for_allocation", "message_or_statement_root_sha256", "beacon_allocation_slot_key_sha256", "committed_future_round_index"]
        return {"domain": "KIRA_MIND_V21_GENERATION_BEACON_NONABORTABLE_RECOVERY_COMMITMENT_V1", "ordered_field_paths": [f"objects.public_beacon_pre_reveal_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes + NUL + pinned generation-beacon recovery profile/key-root); all downstream copies resolve this exact pre-output commitment and recovery reconstructs one VRF output/proof without a producer choice"}
    if field_name == "deadline_beacon_output_recovery_commitment_sha256":
        return {"domain": "KIRA_MIND_V21_DEADLINE_BEACON_NONABORTABLE_RECOVERY_COMMITMENT_V1", "ordered_inputs": ["exact pre-output materialization evidence hash", "singleton registration", "epoch", "sequence", "role", "attempt zero", "generation round", "checked deadline delta", "checked deadline round", "deadline recovery profile and key root"], "formula": "SHA256(domain + NUL + exact canonical typed inputs); every reservation/ledger/order/reveal/deadline/outcome/anchor copy is identical and recovery always materializes the deadline output/proof"}
    if field_name == "confidential_seed_derivation_statement_root_sha256":
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_epoch", "reserved_sequence", "output_role", "attempt_index", "public_round_index", "generation_reservation_sha256", "message_or_statement_root_sha256", "confidential_contributor_roster_sha256", "confidential_contributor_key_root_sha256", "confidential_contribution_aggregation_profile_sha256", "confidential_seed_derivation_profile_sha256"]
        return {"CONFIDENTIAL_SUCCESS": {"domain": "KIRA_MIND_V21_CONFIDENTIAL_ATTEMPT_ZERO_SEED_DERIVATION_STATEMENT_V1", "ordered_field_paths": [f"objects.generation_terminal_outcome.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed public inputs); inside the ZK relation each exact ordered contributor derives one secret contribution over this full tuple, the canonical aggregator KDF consumes all contribution bytes in roster order, and the seed/contributions are erased without public disclosure"}, "UNIQUE_DETERMINISTIC_SUCCESS_OR_ANY_FAILED": "exact JSON null; public deterministic nonce KDF and failure branches have no private seed contribution witness or attestation", "cross_mode_use_allowed": False}
    if field_name == "complete_sequence_materialization_commitment_root_sha256":
        excluded = {"technical_health_measurement_attestation_base64", "producer_availability_authentication_signature_base64", "complete_sequence_materialization_commitment_proof_base64", "health_authentication_signature_base64", "pre_witness_technical_health_evidence_sha256", "complete_sequence_materialization_commitment_root_sha256"}
        fields = [field for field in objects["pre_witness_technical_health_evidence"]["field_order"] if field not in excluded]
        return {"domain": "KIRA_MIND_V21_COMPLETE_SEQUENCE_MATERIALIZATION_COMMITMENT_ROOT_V1", "ordered_field_paths": [f"objects.pre_witness_technical_health_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); fixes all health/availability observations and the complete normal/refusal/failure materialization and recovery roster before any beacon allocation"}
    if field_name == "role_terminalization_plan_root_sha256":
        return {"domain": "KIRA_MIND_V21_ROLE_TERMINALIZATION_PLAN_ROOT_V1", "ordered_roles": role_lifecycle_order, "ordered_field_paths": [f"objects.pre_witness_technical_health_evidence.{field}" for field in role_terminalization_plan_fields], "formula": "SHA256(domain + NUL + for each fixed role in lifecycle order: role ASCII + NUL + exact pre-output plan constant + LF); verifier derives exactly one canonical vector from the complete measured content-independent input vector: all SUCCESS, SUCCESS prefix + one FIXED failure + exact NOT_REACHED suffix, or all NOT_REACHED for pre-output failure; unused suffix variation refuses"}
    if field_name == "lifecycle_refusal_statement_root_sha256":
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_epoch", "generation_sequence_transaction_claim_evidence_sha256", "pre_witness_technical_health_evidence_sha256", "reserved_sequence", "refusal_boundary_role", "refusal_boundary_role_index", "completed_success_role_prefix_root_sha256", "fixed_role_lifecycle_order_root_sha256", "lifecycle_refusal_relation_profile_sha256", "canonical_private_witness_encoding_profile_sha256", "canonical_scope_collector_witness_relation_sha256"]
        return {"domain": "KIRA_MIND_V21_GENERIC_HIDDEN_LIFECYCLE_REFUSAL_STATEMENT_V1", "ordered_field_paths": [f"objects.generation_sequence_lifecycle_refusal_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed public inputs); the private OR-relation proves one exact inherited V19 closure/erasure predicate cannot complete while hiding predicate index surface identity scope witness and value; no witness digest or guess oracle is retained"}
    if field_name == "refusal_confidential_seed_derivation_statement_root_sha256":
        return {"domain": "KIRA_MIND_V21_HIDDEN_REFUSAL_CONFIDENTIAL_SEED_DERIVATION_V1", "ordered_public_field_paths": ["objects.generation_sequence_lifecycle_refusal_evidence.namespace_precommitment_sha256", "objects.generation_sequence_lifecycle_refusal_evidence.pinned_context_sha256", "objects.generation_sequence_lifecycle_refusal_evidence.singleton_registration_sha256", "objects.generation_sequence_lifecycle_refusal_evidence.journal_epoch", "objects.generation_sequence_lifecycle_refusal_evidence.reserved_sequence", "objects.generation_sequence_lifecycle_refusal_evidence.refusal_boundary_role", "objects.generation_sequence_lifecycle_refusal_evidence.refusal_boundary_role_index", "objects.generation_sequence_lifecycle_refusal_evidence.output_attempt_index", "objects.generation_sequence_lifecycle_refusal_evidence.lifecycle_refusal_statement_root_sha256", "objects.generation_sequence_lifecycle_refusal_evidence.completed_success_role_prefix_root_sha256", "objects.generation_sequence_lifecycle_refusal_evidence.confidential_contributor_roster_sha256", "objects.generation_sequence_lifecycle_refusal_evidence.confidential_contributor_key_root_sha256", "objects.generation_sequence_lifecycle_refusal_evidence.confidential_contribution_aggregation_profile_sha256", "objects.generation_sequence_lifecycle_refusal_evidence.confidential_seed_derivation_profile_sha256"], "private_ordered_inputs": "one unique secret contribution for each exact canonical roster/key entry in that order", "formula_inside_zero_knowledge_attestation": "domain-separated extract/aggregate/KDF consumes every complete contribution byte and the exact public tuple; output seed never leaves the isolated generator and is erased; repeated numeric boundary role or sequence in another registration cannot reuse a seed"}
    if field_name == "scope_commitment_bytes_sha256":
        return "SUCCESS only: SHA256 of every decoded canonical scope_commitment_base64 byte; equals linked terminal outcome and terminal-anchor generated_output_sha256; FAILED cannot create scope_precommitment"
    if field_name == "proof_bytes_sha256":
        return "SUCCESS only: SHA256 of every decoded canonical proof_bytes_base64 byte; equals linked terminal outcome and terminal-anchor generated_output_sha256; FAILED cannot create completeness_proof"
    if field_name == "accumulator_proof_statement_root_sha256":
        return {"domain": "KIRA_MIND_V21_TOKEN_ACCUMULATOR_STATEMENT_ROOT_V1", "ordered_field_paths": [f"objects.token_accumulator_proof.{field}" for field in objects["token_accumulator_proof"]["proof_public_input_order"]], "formula": "ASCII domain + actual NUL + exact canonical typed bytes for every ordered field; excludes statement root proof bytes and object self hash"}
    if field_name == "genesis_state_nonce_sha256":
        return {"domain": "KIRA_MIND_V21_GENESIS_STATE_NONCE_DERIVATION_V1", "ordered_field_paths": ["objects.genesis_journal_state.namespace_precommitment_sha256", "objects.genesis_journal_state.pinned_context_sha256", "objects.genesis_journal_state.journal_id_token", "objects.genesis_journal_state.journal_epoch"], "suffix": "ASCII GENESIS_STATE_NONCE", "formula": "SHA256(domain + NUL + exact typed ordered bytes + NUL + suffix); no caller input retry or alternate encoding"}
    if field_name == "reservation_ledger_map_root_sha256":
        return {"counter_zero": "exact objects.pinned_context.generation_reservation_ledger_empty_map_root_sha256 under exact ledger genesis manifest with the empty sequence-claim sentinels and UNCLAIMED", "sequence_claim_acquisition": "canonical sequence-claim slot update UNCLAIMED or prior RELEASED to HELD_UNTIL_SEQUENCE_COMMIT before role zero", "reserved_transition": "canonical role-slot update UNASSIGNED to RESERVED_ATTEMPT_ZERO for exact derived role slot key while preserving the held sequence claim", "terminal_transition": "canonical role-slot update RESERVED_ATTEMPT_ZERO to CONSUMED_TERMINAL for same exact slot while preserving the held sequence claim", "sequence_claim_release": "canonical exact active sequence-claim slot update HELD_UNTIL_SEQUENCE_COMMIT to RELEASED_BY_EXACT_SEQUENCE_COMMIT in the same normal or failure journal CAS", "no_free_input": True}
    if field_name == "message_or_statement_root_sha256":
        return {"role_conditioned_exact_row": "exact_output_role_bijection row selected by output_role", "formula": "that row's message_root_domain and exact ordered reservation_preimage_field_order plus target_pre_reservation_field_order; no reservation evidence output self or private witness field"}
    if field_name == "reservation_slot_key_sha256":
        return "SHA256(ASCII KIRA_MIND_V21_RESERVATION_SLOT_KEY_V1 + actual NUL + singleton_registration_sha256 decoded bytes + NUL + journal_epoch uint64-be + NUL + reserved sequence uint64-be + NUL + exact output_role ASCII); on PRE_OUTPUT_FIXED_TECHNICAL_FAILURE or HIDDEN_LIFECYCLE_REFUSAL this is the deterministic never-reserved boundary slot key and no reservation object is implied; every created copy equality-binds this value"
    if field_name == "public_beacon_output_sha256":
        return "SHA256 of exact verifier-returned decoded public_beacon_reveal_evidence.public_beacon_output_base64 bytes after VRFVerifyExact over separate non-circular input; equals pre-reveal committed output hash and every outcome copy"
    if field_name == "deadline_beacon_output_sha256":
        return "SHA256 of exact verifier-returned decoded terminal_deadline_observation_evidence.deadline_beacon_output_base64 bytes after VRFVerifyExact over separate deadline input root"
    if field_name == "generated_output_sha256":
        return {"SUCCESS_CONFIDENTIAL_ROLES": "SHA256 of every decoded canonical target commitment/proof byte under the exact hidden-seed ZK attestation and role relation; verifier does not recompute secret-seeded bytes", "SUCCESS_DETERMINISTIC_NONCE_ROLES": "SHA256 of the exact 64 lowercase ASCII bytes verifier-recomputed by deterministic_nonce_kdf_rules from the full VRF output and closed role tuple; target token outcome and anchor copies equal", "FAILED": "exact JSON null under the unique pre-output-fixed role plan", "outcome_anchor_copies_byte_identical": True}
    if field_name == "reservation_ledger_anchor_statement_sha256":
        ordered = [field for field in objects["generation_reservation_ledger_evidence"]["field_order"] if field not in {"reservation_ledger_anchor_statement_sha256", "reservation_ledger_authentication_signature_base64", "generation_reservation_ledger_evidence_sha256"}]
        return {"domain": "KIRA_MIND_V21_RESERVATION_LEDGER_ANCHOR_STATEMENT_V1", "ordered_field_paths": [f"objects.generation_reservation_ledger_evidence.{field}" for field in ordered], "formula": "SHA256(domain + NUL + exact canonical typed bytes in order); excludes statement signature and self hash"}
    if field_name == "terminal_anchor_statement_sha256":
        ordered = [field for field in objects["generation_terminal_anchor_evidence"]["field_order"] if field not in {"terminal_anchor_statement_sha256", "terminal_anchor_authentication_signature_base64", "generation_terminal_anchor_evidence_sha256"}]
        return {"domain": "KIRA_MIND_V21_TERMINAL_ANCHOR_STATEMENT_V1", "ordered_field_paths": [f"objects.generation_terminal_anchor_evidence.{field}" for field in ordered], "formula": "SHA256(domain + NUL + exact canonical typed bytes in order); excludes statement signature and self hash"}
    if field_name == "committed_round_output_sha256":
        if object_name == "public_beacon_pre_reveal_state":
            return {"counter_zero": "exact objects.pinned_context.public_beacon_counter_zero_output_sentinel_sha256; no round exists", "counter_positive": "SHA256 of the exact allocated future-round VRF output bytes, equality-bound to the role pre-reveal evidence and later verified/recovered reveal", "no_free_base_value": True}
        return "SHA256 of the exact future round VRF output bytes committed before reveal; after normal or threshold recovery reveal equals SHA256 of VRFVerifyExact returned public_beacon_output_base64 bytes; allocation is one-use and cannot be changed after its role slot assignment"
    if field_name == "public_beacon_vrf_input_message_root_sha256":
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "public_round_index", "public_round_beacon_identity_sha256", "beacon_vrf_authentication_key_role"]
        return {"domain": "KIRA_MIND_V21_PUBLIC_BEACON_VRF_INPUT_MESSAGE_ROOT_V1", "ordered_field_paths": [f"objects.public_beacon_reveal_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes fixed before the pre-reveal head); excludes reservation ledger pre-reveal/order hashes slot sequence role output hash output bytes proof terminal outcome and self hash, eliminating every pre-reveal/output fixed point; reservation and order are verified as separate enclosing linkages"}
    if field_name == "deadline_vrf_input_message_root_sha256":
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_reservation_sha256", "generation_reservation_ledger_evidence_sha256", "public_beacon_reveal_evidence_sha256", "pre_witness_technical_health_evidence_sha256", "reservation_slot_key_sha256", "reserved_sequence", "output_role", "reserved_output_generation_mode", "reservation_attempt_index", "generation_public_round_index", "fixed_terminal_deadline_round_index", "fixed_terminal_timing_envelope_profile_sha256", "public_round_beacon_identity_sha256", "beacon_vrf_authentication_key_role"]
        return {"domain": "KIRA_MIND_V21_TERMINAL_DEADLINE_VRF_INPUT_MESSAGE_ROOT_V1", "ordered_field_paths": [f"objects.terminal_deadline_observation_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); consumes the exact equality-bound reservation role mode attempt generation-round deadline tuple and excludes deadline output hash bytes proof signature and self hash"}
    if field_name == "failure_state_nonce_sha256":
        return {"domain": "KIRA_MIND_V21_FAILURE_STATE_NONCE_V1", "ordered_field_paths": ["objects.generation_failure_journal_state.generation_failure_record_sha256", "objects.generation_failure_journal_state.failed_sequence_barrier_root_sha256"], "branch_link": "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE appends exact pre-output materialization evidence hash; ROLE_TERMINAL_FAILED appends exact terminal-anchor hash; HIDDEN_LIFECYCLE_REFUSAL appends exact lifecycle-refusal evidence hash", "formula": "SHA256(domain + NUL + failure-record hash bytes + NUL + barrier bytes + NUL + exact branch tag + NUL + exact branch evidence hash); no randomness retry caller input second failure or alternate null branch"}
    if field_name == "active_generation_chain_set_root_sha256":
        return {"domain": "KIRA_MIND_V21_ACTIVE_COMPLETE_GENERATION_CHAIN_SET_ROOT_V1", "sequence_wide_pre_output_member": "pre_witness_technical_health_evidence_sha256", "ordered_roles": role_lifecycle_order, "per_role_members": ["generation_reservation_sha256", "generation_reservation_ledger_evidence_sha256", "public_beacon_reveal_evidence_sha256", "terminal_deadline_observation_evidence_sha256", "generation_terminal_outcome_sha256", "generation_terminal_anchor_evidence_sha256"], "formula": "SHA256(domain + NUL + exact sequence-wide pre-output materialization evidence hash + LF + for each exact role in lifecycle order: role ASCII + NUL + all six role-specific 32-byte member hashes + LF); computed only after all ten terminal anchors exist and placed only in final commit_evidence; every terminal outcome SUCCESS; all roles share sequence context registration and the one pre-output commitment; no missing duplicate extra failure or interleaved reservation"}
    if field_name == "completed_success_role_prefix_root_sha256":
        boundary_source = ("current allocation output_role's fixed role_lifecycle_order index"
                           if object_name == "public_beacon_pre_reveal_evidence"
                           else "refusal_boundary_role_index or failure_role_index equality-bound to the exact boundary role")
        return {"domain": "KIRA_MIND_V21_COMPLETED_SUCCESS_ROLE_PREFIX_ROOT_V1", "boundary_index_source": boundary_source, "sequence_wide_member": "the one pre-output materialization evidence hash", "ordered_roles": role_lifecycle_order, "formula": "for boundary role index i, SHA256(domain + NUL + sequence-wide pre-output materialization evidence hash + LF + for each exact lifecycle role index 0 through i-1: role ASCII + NUL + its reservation ledger reveal deadline outcome and anchor hashes + LF); every prefix outcome SUCCESS; i=0 contains only the pre-output member; no caller subset order or omitted earlier role"}
    if field_name in {"unreserved_suffix_cancellation_barrier_root_sha256", "failed_sequence_barrier_root_sha256"}:
        return {"domain": "KIRA_MIND_V21_UNRESERVED_SUFFIX_CANCELLATION_BARRIER_ROOT_V1", "ordered_roles": role_lifecycle_order, "branch_formulas": {"PRE_OUTPUT_FIXED_TECHNICAL_FAILURE": "role index zero plus exact pre-output materialization evidence hash and all ten roles marked NEVER_RESERVED_AFTER_SEQUENCE_FAILURE", "ROLE_TERMINAL_FAILED": "exact first-failed role index and terminal-anchor hash plus every later role marked NEVER_RESERVED_AFTER_SEQUENCE_FAILURE", "HIDDEN_LIFECYCLE_REFUSAL": "exact refusal boundary role index and lifecycle-refusal evidence hash plus that boundary and every later role marked NEVER_RESERVED_AFTER_SEQUENCE_FAILURE"}, "formula": "SHA256(domain + NUL + singleton registration + epoch-u64be + sequence-u64be + exact branch tag + NUL + branch evidence hash + NUL + exact ordered unreserved role suffix); no uncreated role is represented as a consumed attempt; all copies equal"}
    if field_name == "post_failure_external_anchor_statement_sha256":
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_failure_record_sha256", "failed_sequence_barrier_root_sha256", "pre_external_anchor_root_sha256", "pre_external_anchor_monotonic_counter", "post_failure_state_root_sha256", "post_failure_state_object_sha256", "post_record_count", "post_head_sequence", "post_head_receipt_hash_sha256", "post_head_event_hash_sha256", "pre_receipt_token_root_sha256", "post_receipt_token_root_sha256", "pre_scope_token_root_sha256", "post_scope_token_root_sha256", "pre_proof_token_root_sha256", "post_proof_token_root_sha256", "post_external_anchor_monotonic_counter"]
        return {"domain": "KIRA_MIND_V21_FAILURE_EXTERNAL_ANCHOR_SUCCESSOR_STATEMENT_V1", "ordered_field_paths": [f"objects.generation_failure_sequence_commit_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); post anchor counter is checked pre plus one and prior root must be independently current"}
    if field_name == "post_failure_external_anchor_root_sha256":
        return {"domain": "KIRA_MIND_V21_FAILURE_EXTERNAL_ANCHOR_SUCCESSOR_OBJECT_V1", "ordered_field_paths": ["objects.generation_failure_sequence_commit_evidence.post_failure_external_anchor_statement_sha256", "objects.generation_failure_sequence_commit_evidence.failure_anchor_authentication_proof_base64"], "formula": "SHA256(domain + NUL + statement bytes + NUL + exact full decoded proof bytes); VerifyExact under preserved external-anchor profile/key must pass"}
    if field_name == "post_failure_state_authority_statement_sha256":
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_failure_record_sha256", "failed_sequence_barrier_root_sha256", "pre_state_authority_head_evidence_sha256", "pre_state_authority_monotonic_counter", "post_failure_state_root_sha256", "post_failure_state_object_sha256", "post_record_count", "post_head_sequence", "post_head_receipt_hash_sha256", "post_head_event_hash_sha256", "pre_receipt_token_root_sha256", "post_receipt_token_root_sha256", "pre_scope_token_root_sha256", "post_scope_token_root_sha256", "pre_proof_token_root_sha256", "post_proof_token_root_sha256", "post_failure_external_anchor_root_sha256", "post_state_authority_monotonic_counter"]
        return {"domain": "KIRA_MIND_V21_FAILURE_STATE_AUTHORITY_SUCCESSOR_STATEMENT_V1", "ordered_field_paths": [f"objects.generation_failure_sequence_commit_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); authority counter is checked pre plus one and prior authority head must be independently current"}
    if field_name == "post_failure_state_authority_head_evidence_sha256":
        return {"domain": "KIRA_MIND_V21_FAILURE_STATE_AUTHORITY_SUCCESSOR_OBJECT_V1", "ordered_field_paths": ["objects.generation_failure_sequence_commit_evidence.post_failure_state_authority_statement_sha256", "objects.generation_failure_sequence_commit_evidence.failure_authority_authentication_signature_base64"], "formula": "SHA256(domain + NUL + statement bytes + NUL + exact full decoded signature bytes); VerifyExact under preserved state-authority profile/key must pass"}
    if field_name == "technical_health_input_vector_sha256":
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "generation_sequence_transaction_claim_evidence_sha256", "sequence_transaction_claim_slot_key_sha256", "sequence_transaction_claim_statement_sha256", "reserved_sequence", "authoritative_pre_state_kind", "fixed_role_lifecycle_order_root_sha256", "fixed_terminal_deadline_round_delta", "pre_witness_health_predicate_sha256", "pre_witness_health_profile_sha256", "complete_sequence_materialization_profile_root_sha256", "complete_sequence_materialization_roster_root_sha256", "complete_sequence_materialization_recovery_key_root_sha256", "generation_beacon_nonabortable_recovery_profile_sha256", "generation_beacon_nonabortable_recovery_key_root_sha256", "deadline_beacon_nonabortable_recovery_profile_sha256", "deadline_beacon_nonabortable_recovery_key_root_sha256", "post_claim_total_terminalization_profile_sha256", "lifecycle_refusal_relation_profile_sha256", "observed_sequence_claim_post_ledger_state_root_sha256", "observed_sequence_claim_post_ledger_state_object_sha256", "observed_sequence_claim_post_ledger_counter", "observed_confidential_generator_image_sha256", "observed_confidential_generator_profile_sha256", "observed_contributor_roster_sha256", "observed_contributor_key_root_sha256"]
        return {"domain": "KIRA_MIND_V21_PRE_OUTPUT_SEQUENCE_MATERIALIZATION_HEALTH_INPUT_VECTOR_V1", "ordered_field_paths": [f"objects.pre_witness_technical_health_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); every observation equality-resolves to the claim-acquisition post ledger state or exact namespace-precommitted pin and is committed before any beacon allocation/reveal; no caller measurement extension omission content or future-output input"}
    if field_name == "health_predicate_evaluation_root_sha256":
        fields = ["pre_witness_health_predicate_sha256", "pre_witness_health_profile_sha256", "technical_health_input_vector_sha256", "technical_health_measurement_result", "role_terminalization_plan_root_sha256", "technical_health_measurement_attestation_base64", "producer_availability_predicate_sha256", "producer_availability_profile_sha256", "producer_availability_authority_identity_sha256", "producer_availability_result", "producer_availability_authentication_signature_base64"]
        return {"domain": "KIRA_MIND_V21_PRE_WITNESS_HEALTH_PREDICATE_EVALUATION_ROOT_V1", "ordered_field_paths": [f"objects.pre_witness_technical_health_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); sequence health is READY iff measurement result passes and availability is committed; role-terminal branches are separately fixed by the exact ten-role plan root; otherwise pre-output FIXED_TECHNICAL_FAILURE; no result is chosen after any allocation or output"}
    if field_name == "fixed_role_lifecycle_order_root_sha256":
        return {"domain": "KIRA_MIND_V21_FIXED_TEN_ROLE_LIFECYCLE_ORDER_ROOT_V1", "ordered_roles": role_lifecycle_order, "formula": "SHA256(domain + NUL + each exact role ASCII in lifecycle order followed by LF); exactly ten roles, no caller subset order duplicate alias or extension"}
    if field_name in {"sequence_transaction_claim_slot_key_sha256", "active_sequence_transaction_claim_slot_key_sha256"}:
        return {"domain": "KIRA_MIND_V21_SEQUENCE_TRANSACTION_CLAIM_SLOT_KEY_V1", "ordered_inputs": ["singleton_registration_sha256 decoded 32 bytes", "journal_epoch uint64-be", "reserved_next_sequence uint64-be"], "formula": "SHA256(domain + NUL + exact ordered inputs); every active ledger-state and release copy equality-binds the one claim evidence value; no role component because the claim covers all ten roles"}
    if field_name in {"sequence_transaction_claim_statement_sha256", "active_sequence_transaction_claim_statement_sha256"}:
        fields = ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch", "authoritative_pre_journal_state_root_sha256", "authoritative_pre_journal_state_object_sha256", "authoritative_pre_state_kind", "authoritative_pre_record_count", "authoritative_pre_head_sequence", "authoritative_pre_head_receipt_hash_sha256", "authoritative_pre_head_event_hash_sha256", "pre_state_authority_head_evidence_sha256", "pre_state_authority_counter", "pre_external_anchor_root_sha256", "pre_external_anchor_counter", "reserved_next_sequence", "fixed_role_lifecycle_order_root_sha256", "sequence_transaction_claim_slot_key_sha256", "prior_reservation_ledger_head_evidence_sha256", "pre_reservation_ledger_state_root_sha256", "pre_reservation_ledger_state_object_sha256", "pre_reservation_ledger_counter", "pre_sequence_transaction_claim_state"]
        return {"domain": "KIRA_MIND_V21_SEQUENCE_TRANSACTION_CLAIM_STATEMENT_V1", "ordered_field_paths": [f"objects.generation_sequence_transaction_claim_evidence.{field}" for field in fields], "formula": "SHA256(domain + NUL + exact canonical typed ordered bytes); the persisted claim identity binds the exact recursively authenticated ledger history and pre-state; ledger post roots proof and evidence self hash remain excluded, so acquisition is acyclic"}
    raise ValueError({"missing_exact_generated_sha256_derivation": path})

def exact_accumulator_selector(path, object_name, field_name):
    if field_name.startswith("empty_"):
        return f"exact canonical empty {field_name.removeprefix('empty_').removesuffix('_root_sha256')} accumulator root under objects.pinned_context.replay_token_accumulator_profile_sha256 and replay_journal_genesis_manifest_sha256"
    return f"exact canonical {field_name} under objects.pinned_context.replay_token_accumulator_profile_sha256; linked token_accumulator_proof public inputs and full-byte proof bind the same pre/post transition, and journal state copies equality-bind the returned root"

sha_occurrences = []
exact_generated_derivation_rows = []
for object_name, obj in objects.items():
    for field, kind in zip(obj["field_order"], obj["field_types"]):
        if kind not in {"sha256", "nullable_sha256"}:
            continue
        path = f"objects.{object_name}.{field}"
        classes = class_membership.get(field, [])
        if len(classes) != 1:
            raise ValueError({"path": path, "classes": classes})
        if path in path_conditions:
            selector = path_conditions[path]
        elif classes[0] == "exact_object_or_counter_conditioned_target":
            selector = exact_occurrence_defaults[field]
        elif classes[0] == "terminal_static_context_target":
            selector = f"objects.pinned_context.{field} exact byte-identical terminal preimage"
        elif classes[0] == "role_conditioned_static_profile_target":
            selector = next(row for row in role_conditioned_rows if row["left_path"] == path)
        elif classes[0] == "dynamic_accumulator_target":
            selector = exact_accumulator_selector(path, object_name, field)
        else:
            selector = exact_generated_selector(path, object_name, field)
            exact_generated_derivation_rows.append({"path": path, "exact_selector": selector})
        sha_occurrences.append({"path": path, "field_type": kind, "target_class": classes[0], "target_selector": selector})

self_referential_target_placeholders = [
    row["path"] for row in sha_occurrences
    if row["target_selector"] == "PATH_COUNTER_CONDITIONED_SEE_path_qualified_sha256_target_partition"
]
if self_referential_target_placeholders:
    raise ValueError({"self_referential_sha_target_placeholders": self_referential_target_placeholders})

actual_sha_names = {row["path"].rsplit(".", 1)[1] for row in sha_occurrences}
classified_sha_names = set(class_membership)
name_gaps = sorted(actual_sha_names - classified_sha_names)
name_extras = sorted(classified_sha_names - actual_sha_names)
name_overlaps = sorted(name for name, classes in class_membership.items() if len(classes) != 1)
if name_gaps or name_extras or name_overlaps:
    raise ValueError({"sha_name_gaps": name_gaps, "sha_name_extras": name_extras, "sha_name_overlaps": name_overlaps})
doc["path_qualified_sha256_target_partition"] = {
    "occurrence_count": len(sha_occurrences),
    "rows": sha_occurrences,
    "name_gap_count": 0,
    "name_extra_count": 0,
    "name_overlap_count": 0,
    "occurrence_gap_count": 0,
    "occurrence_overlap_count": 0,
    "counter_conditioned_path_count": len(path_conditions),
    "role_conditioned_profile_path_count": len(role_conditioned_rows),
}
doc["exact_generated_sha256_derivations"] = {
    "occurrence_count": len(exact_generated_derivation_rows),
    "rows": exact_generated_derivation_rows,
    "generic_catch_all_selector_count": 0,
    "gap_extra_overlap_or_free_256_bit_input_count": 0,
}

# Exact path-pair equality closure.
context_fields = set(objects["pinned_context"]["field_order"])
if not set(terminal).issubset(context_fields):
    raise ValueError({"terminal_not_in_context": sorted(set(terminal) - context_fields)})
terminal_outer_rows = [
    {"outer_path": f"trusted_outer_pins.{field}", "context_path": f"objects.pinned_context.{field}", "target_class": "terminal_static_context_target", "role_domain": "exact same field path and byte-available preimage"}
    for field in terminal
]
outer_root_rows = [
    {"outer_path": "trusted_outer_pins.pinned_context_sha256", "context_path": "objects.pinned_context.pinned_context_sha256", "target_class": "exact_object_root", "role_domain": objects["pinned_context"]["domain_const"]},
    {"outer_path": "trusted_outer_pins.singleton_registration_sha256", "context_path": "objects.singleton_registration.singleton_registration_sha256", "target_class": "exact_object_root", "role_domain": objects["singleton_registration"]["domain_const"]},
]
repeated_terminal_rows = []
for object_name, obj in objects.items():
    if object_name == "pinned_context":
        continue
    for field in obj["field_order"]:
        if field in terminal:
            repeated_terminal_rows.append({"left_path": f"objects.{object_name}.{field}", "right_path": f"objects.pinned_context.{field}", "condition": "byte-identical exact technical terminal pin"})
namespace_context_rows = []
namespace_fields = set(objects["namespace_precommitment"]["field_order"])
for field in objects["pinned_context"]["field_order"]:
    if field in namespace_fields and field not in {"schema", "hash_domain", "pinned_context_sha256", "namespace_precommitment_sha256"}:
        namespace_context_rows.append({"left_path": f"objects.namespace_precommitment.{field}", "right_path": f"objects.pinned_context.{field}", "condition": "byte-identical across immutable namespace precommitment and final context"})
root_repeat_rows = []
for object_name, obj in objects.items():
    if object_name != "pinned_context" and "pinned_context_sha256" in obj["field_order"]:
        root_repeat_rows.append({"left_path": f"objects.{object_name}.pinned_context_sha256", "right_path": "objects.pinned_context.pinned_context_sha256", "condition": "byte-identical final context root"})
    if object_name != "singleton_registration" and "singleton_registration_sha256" in obj["field_order"]:
        root_repeat_rows.append({"left_path": f"objects.{object_name}.singleton_registration_sha256", "right_path": "objects.singleton_registration.singleton_registration_sha256", "condition": "byte-identical final singleton registration root"})

registry_equality_rows = []

# Closed full-genesis and registrar bundles exist before any request signature or
# registry post value.  They are the only sources for the completed request.
for field, target_object, target_field in [
    ("namespace_precommitment_sha256", "pinned_context", "namespace_precommitment_sha256"),
    ("pinned_context_sha256", "pinned_context", "pinned_context_sha256"),
    ("genesis_manifest_sha256", "genesis_manifest", "genesis_manifest_sha256"),
    ("genesis_journal_state_root_sha256", "genesis_journal_state", "genesis_journal_state_root_sha256"),
    ("genesis_journal_state_object_sha256", "genesis_journal_state", "genesis_journal_state_object_sha256"),
    ("genesis_external_anchor_root_sha256", "genesis_external_anchor_evidence", "genesis_external_anchor_root_sha256"),
    ("genesis_state_authority_head_evidence_sha256", "genesis_state_authority_evidence", "genesis_state_authority_head_evidence_sha256"),
]:
    registry_equality_rows.append({"left_path": f"objects.singleton_registration_full_genesis_bundle.{field}", "right_path": f"objects.{target_object}.{target_field}", "condition": "full-genesis bundle consumes the exact byte-available registered counter-zero component"})
for bundle_name, fields in {
    "registrar_policy_profile_bundle": ["namespace_precommitment_sha256", "pinned_context_sha256", "global_registrar_policy_sha256", "global_registrar_authentication_profile_sha256"],
    "registrar_authority_key_identity_bundle": ["namespace_precommitment_sha256", "pinned_context_sha256", "global_registrar_identity_sha256", "registrar_verification_key_registry_root_sha256", "registrar_key_identifier_token", "global_registrar_authentication_public_key_sha256"],
}.items():
    for field in fields:
        registry_equality_rows.append({"left_path": f"objects.{bundle_name}.{field}", "right_path": f"objects.pinned_context.{field}", "condition": "registrar bundle member is the exact namespace-precommitted context pin"})

# The V5 component oracle requires literal namespace-to-bundle pairs.  The
# namespace-to-context rows above are independently retained, but validators do
# not infer these security-critical registrar bindings by transitivity.
for field, bundle_name in [
    ("global_registrar_policy_sha256", "registrar_policy_profile_bundle"),
    ("global_registrar_authentication_profile_sha256", "registrar_policy_profile_bundle"),
    ("global_registrar_identity_sha256", "registrar_authority_key_identity_bundle"),
    ("registrar_verification_key_registry_root_sha256", "registrar_authority_key_identity_bundle"),
    ("registrar_key_identifier_token", "registrar_authority_key_identity_bundle"),
    ("global_registrar_authentication_public_key_sha256", "registrar_authority_key_identity_bundle"),
]:
    registry_equality_rows.append({
        "left_path": f"objects.namespace_precommitment.{field}",
        "right_path": f"objects.{bundle_name}.{field}",
        "condition": "literal V5 registrar component equality; no context-mediated inference or key/profile substitution",
    })

pre_request_sources = {
    "stable_global_registry_slot_sha256": "objects.pinned_context.stable_global_registry_slot_sha256",
    "journal_id_token": "objects.pinned_context.journal_id_token",
    "journal_epoch": "objects.pinned_context.journal_epoch",
    "namespace_precommitment_sha256": "objects.pinned_context.namespace_precommitment_sha256",
    "pinned_context_sha256": "objects.pinned_context.pinned_context_sha256",
    "full_genesis_bundle_root_sha256": "objects.singleton_registration_full_genesis_bundle.full_genesis_bundle_root_sha256",
    "registrar_policy_profile_bundle_sha256": "objects.registrar_policy_profile_bundle.registrar_policy_profile_bundle_sha256",
    "registrar_authority_key_identity_bundle_sha256": "objects.registrar_authority_key_identity_bundle.registrar_authority_key_identity_bundle_sha256",
}
for field, source_path in pre_request_sources.items():
    registry_equality_rows.append({"left_path": f"objects.singleton_registration_pre_request_payload.{field}", "right_path": source_path, "condition": "acyclic pre-request payload consumes the exact authoritative pre-existing value"})

assigned_sources = dict(pre_request_sources)
assigned_sources["pre_request_registration_payload_root_sha256"] = "objects.singleton_registration_pre_request_payload.pre_request_registration_payload_root_sha256"
for field, source_path in assigned_sources.items():
    if field in objects["singleton_registration_assigned_value"]["field_order"]:
        registry_equality_rows.append({"left_path": f"objects.singleton_registration_assigned_value.{field}", "right_path": source_path, "condition": "assigned value is an acyclic exact projection of the pre-request payload and bundles"})

request_sources = dict(assigned_sources)
request_sources["assigned_value_root_sha256"] = "objects.singleton_registration_assigned_value.assigned_value_root_sha256"
for field, source_path in request_sources.items():
    if field in objects["singleton_registration_request"]["field_order"]:
        registry_equality_rows.append({"left_path": f"objects.singleton_registration_request.{field}", "right_path": source_path, "condition": "completed registrar-signed request repeats the exact acyclic pre-request and assigned value"})
registry_equality_rows.extend([
    {"left_path": "objects.singleton_registration_request.signature_domain", "right_path": "constant.KIRA_MIND_V21_SINGLETON_REGISTRATION_COMPLETED_REQUEST_SIGNATURE_V1", "condition": "exact request signature domain"},
    {"left_path": "objects.singleton_registration_request.request_nonce", "right_path": "constant.UINT64_ZERO", "condition": "completed request has the exact fixed nonce zero; no caller nonce or retry"},
])

carried_registration_fields = [
    "stable_global_registry_slot_sha256", "journal_id_token", "journal_epoch",
    "namespace_precommitment_sha256", "pinned_context_sha256", "full_genesis_bundle_root_sha256",
    "pre_request_registration_payload_root_sha256", "registrar_policy_profile_bundle_sha256",
    "registrar_authority_key_identity_bundle_sha256", "singleton_registration_request_sha256",
]
carried_with_assigned = carried_registration_fields + ["assigned_value_root_sha256"]
chain_objects = [
    "global_registry_sparse_map_leaf", "global_registry_sparse_map_update", "global_registry_sparse_map_proof",
    "global_registry_post_head", "global_registry_post_state", "singleton_registration",
]
for field in carried_with_assigned:
    if field == "singleton_registration_request_sha256":
        source_path = "objects.singleton_registration_request.singleton_registration_request_sha256"
    elif field == "assigned_value_root_sha256":
        source_path = "objects.singleton_registration_assigned_value.assigned_value_root_sha256"
    else:
        source_path = request_sources[field]
    for object_name in chain_objects:
        if field in objects[object_name]["field_order"]:
            registry_equality_rows.append({"left_path": source_path, "right_path": f"objects.{object_name}.{field}", "condition": "literal singleton metadata propagation through signed request leaf update proof post head post state and final registration"})

# Every carried field is also physically sourced from the completed signed
# request itself.  Keeping the upstream rows does not replace these V5/V6
# request-to-consumer pairs: a validator checks both and therefore cannot
# transplant an otherwise valid request, leaf, update, proof, head, or state.
for field in carried_with_assigned:
    request_source = f"objects.singleton_registration_request.{field}"
    for object_name in chain_objects:
        if field in objects[object_name]["field_order"]:
            registry_equality_rows.append({
                "left_path": request_source,
                "right_path": f"objects.{object_name}.{field}",
                "condition": "literal V5 completed-request metadata propagation; transitive equality is insufficient",
            })

for object_name in ["global_registry_sparse_map_update", "global_registry_sparse_map_proof", "global_registry_post_state"]:
    registry_equality_rows.extend([
        {"left_path": f"objects.{object_name}.registry_pre_root_sha256", "right_path": "instances.global_registry_pre_state.registry_root_sha256", "condition": "transition consumes the exact independently current typed registry pre-root"},
        {"left_path": f"objects.{object_name}.registry_counter_before", "right_path": "instances.global_registry_pre_state.registry_counter", "condition": "transition consumes the exact same typed pre-state counter"},
        {"left_path": f"objects.{object_name}.prior_leaf_state", "right_path": "constant.ABSENT", "condition": "singleton slot prior leaf is exactly ABSENT"},
    ])
registry_equality_rows.extend([
    {"left_path": "objects.global_registry_sparse_map_update.registry_counter_after", "right_path": "checked_plus_one(objects.global_registry_sparse_map_update.registry_counter_before)", "condition": "checked singleton registry counter increment; overflow refuses"},
    {"left_path": "objects.global_registry_sparse_map_update.global_registry_sparse_map_leaf_sha256", "right_path": "objects.global_registry_sparse_map_leaf.global_registry_sparse_map_leaf_sha256", "condition": "update writes the exact typed leaf"},
    {"left_path": "objects.global_registry_sparse_map_update.global_registry_sparse_map_update_sha256", "right_path": "objects.global_registry_sparse_map_proof.global_registry_sparse_map_update_sha256", "condition": "proof authenticates the exact update object"},
    {"left_path": "objects.global_registry_sparse_map_leaf.global_registry_sparse_map_leaf_sha256", "right_path": "objects.global_registry_sparse_map_proof.global_registry_sparse_map_leaf_sha256", "condition": "proof authenticates the exact typed leaf"},
    {"left_path": "objects.global_registry_sparse_map_update.registry_pre_root_sha256", "right_path": "objects.global_registry_post_state.registry_pre_root_sha256", "condition": "typed post state repeats the exact independently current pre-root"},
    {"left_path": "objects.global_registry_sparse_map_update.registry_post_root_sha256", "right_path": "objects.singleton_registration.post_global_registry_state_root_sha256", "condition": "final registration directly repeats the verified update post-root"},
    {"left_path": "objects.global_registry_sparse_map_update.registry_counter_before", "right_path": "objects.global_registry_post_state.registry_counter_before", "condition": "typed post state repeats the exact pre-counter"},
    {"left_path": "objects.global_registry_sparse_map_update.registry_counter_after", "right_path": "objects.singleton_registration.post_registry_counter", "condition": "final registration directly repeats the checked update post-counter"},
    {"left_path": "objects.global_registry_sparse_map_update.prior_leaf_state", "right_path": "objects.global_registry_post_state.prior_leaf_state", "condition": "typed post state repeats exact ABSENT prior leaf"},
    {"left_path": "objects.global_registry_sparse_map_leaf.global_registry_sparse_map_leaf_sha256", "right_path": "objects.global_registry_post_head.global_registry_sparse_map_leaf_sha256", "condition": "post head directly authenticates exact leaf"},
    {"left_path": "objects.global_registry_sparse_map_leaf.global_registry_sparse_map_leaf_sha256", "right_path": "objects.global_registry_post_state.global_registry_sparse_map_leaf_sha256", "condition": "post state directly authenticates exact leaf"},
    {"left_path": "objects.global_registry_sparse_map_update.global_registry_sparse_map_update_sha256", "right_path": "objects.global_registry_post_head.global_registry_sparse_map_update_sha256", "condition": "post head directly authenticates exact update"},
    {"left_path": "objects.global_registry_sparse_map_update.global_registry_sparse_map_update_sha256", "right_path": "objects.global_registry_post_state.global_registry_sparse_map_update_sha256", "condition": "post state directly authenticates exact update"},
    {"left_path": "objects.global_registry_sparse_map_proof.global_registry_sparse_map_proof_sha256", "right_path": "objects.global_registry_post_state.global_registry_sparse_map_proof_sha256", "condition": "post state directly authenticates exact proof"},
])
for field in ["registry_pre_root_sha256", "registry_post_root_sha256", "registry_counter_before", "registry_counter_after", "prior_leaf_state"]:
    registry_equality_rows.append({"left_path": f"objects.global_registry_sparse_map_update.{field}", "right_path": f"objects.global_registry_sparse_map_proof.{field}", "condition": "proof and update share one exact pre/post sparse-map transition"})
for field in ["registry_post_root_sha256", "registry_counter_after"]:
    registry_equality_rows.extend([
        {"left_path": f"objects.global_registry_sparse_map_update.{field}", "right_path": f"objects.global_registry_post_head.{field}", "condition": "typed post head consumes the exact verified update result"},
        {"left_path": f"objects.global_registry_sparse_map_update.{field}", "right_path": f"objects.global_registry_post_state.{field}", "condition": "typed post state consumes the exact verified update result"},
    ])
registry_equality_rows.extend([
    {"left_path": "objects.global_registry_sparse_map_proof.global_registry_sparse_map_proof_sha256", "right_path": "objects.global_registry_post_head.global_registry_sparse_map_proof_sha256", "condition": "typed post head consumes exact proof"},
    {"left_path": "objects.global_registry_post_head.global_registry_post_head_sha256", "right_path": "objects.global_registry_post_state.global_registry_post_head_sha256", "condition": "typed post state consumes the one post head"},
    {"left_path": "objects.global_registry_post_state.registry_post_root_sha256", "right_path": "objects.singleton_registration.post_global_registry_state_root_sha256", "condition": "final registration consumes exact typed post root"},
    {"left_path": "objects.global_registry_post_state.registry_counter_after", "right_path": "objects.singleton_registration.post_registry_counter", "condition": "final registration consumes exact checked post counter"},
    {"left_path": "objects.global_registry_post_state.global_registry_post_state_sha256", "right_path": "objects.singleton_registration.global_registry_post_state_sha256", "condition": "final registration consumes exact typed post-state object"},
    {"left_path": "objects.global_registry_post_head.global_registry_post_head_sha256", "right_path": "objects.singleton_registration.global_registry_post_head_sha256", "condition": "final registration consumes exact typed post head"},
    {"left_path": "objects.global_registry_sparse_map_leaf.global_registry_sparse_map_leaf_sha256", "right_path": "objects.singleton_registration.global_registry_sparse_map_leaf_sha256", "condition": "final registration consumes exact typed leaf"},
    {"left_path": "objects.global_registry_sparse_map_update.global_registry_sparse_map_update_sha256", "right_path": "objects.singleton_registration.global_registry_sparse_map_update_sha256", "condition": "final registration consumes exact typed update"},
    {"left_path": "objects.global_registry_sparse_map_proof.global_registry_sparse_map_proof_sha256", "right_path": "objects.singleton_registration.global_registry_sparse_map_proof_sha256", "condition": "final registration consumes exact typed proof"},
    {"left_path": "objects.global_registry_sparse_map_update.singleton_registry_transition_profile_root_sha256", "right_path": "objects.pinned_context.singleton_registry_transition_profile_root_sha256", "condition": "transition profile resolves uniquely from namespace/context registry and identifier"},
    {"left_path": "objects.global_registry_sparse_map_proof.singleton_registry_proof_profile_root_sha256", "right_path": "objects.pinned_context.singleton_registry_proof_profile_root_sha256", "condition": "proof profile resolves uniquely from namespace/context registry and identifier"},
    {"left_path": "objects.global_registry_post_state.singleton_registry_transition_profile_root_sha256", "right_path": "objects.pinned_context.singleton_registry_transition_profile_root_sha256", "condition": "post state repeats exact transition profile"},
    {"left_path": "objects.global_registry_post_state.singleton_registry_proof_profile_root_sha256", "right_path": "objects.pinned_context.singleton_registry_proof_profile_root_sha256", "condition": "post state repeats exact proof profile"},
    {"left_path": "objects.singleton_registration.singleton_registry_transition_profile_root_sha256", "right_path": "objects.pinned_context.singleton_registry_transition_profile_root_sha256", "condition": "final registration repeats exact transition profile"},
    {"left_path": "objects.singleton_registration.singleton_registry_proof_profile_root_sha256", "right_path": "objects.pinned_context.singleton_registry_proof_profile_root_sha256", "condition": "final registration repeats exact proof profile"},
    {"left_path": "objects.global_registry_sparse_map_update.singleton_registry_transition_profile_root_sha256", "right_path": "objects.global_registry_post_state.singleton_registry_transition_profile_root_sha256", "condition": "literal V6 transition-profile propagation into typed post state"},
    {"left_path": "objects.global_registry_sparse_map_update.singleton_registry_transition_profile_root_sha256", "right_path": "objects.singleton_registration.singleton_registry_transition_profile_root_sha256", "condition": "literal V6 transition-profile propagation into final registration"},
    {"left_path": "objects.global_registry_sparse_map_proof.singleton_registry_proof_profile_root_sha256", "right_path": "objects.global_registry_post_state.singleton_registry_proof_profile_root_sha256", "condition": "literal V6 proof-profile propagation into typed post state"},
    {"left_path": "objects.global_registry_sparse_map_proof.singleton_registry_proof_profile_root_sha256", "right_path": "objects.singleton_registration.singleton_registry_proof_profile_root_sha256", "condition": "literal V6 proof-profile propagation into final registration"},
    {"left_path": "objects.namespace_precommitment.singleton_registry_transition_profile_root_sha256", "right_path": "objects.global_registry_sparse_map_update.singleton_registry_transition_profile_root_sha256", "condition": "literal V6 namespace profile pin resolves the update consumer"},
    {"left_path": "objects.namespace_precommitment.singleton_registry_transition_profile_root_sha256", "right_path": "objects.global_registry_post_state.singleton_registry_transition_profile_root_sha256", "condition": "literal V6 namespace profile pin repeats in typed post state"},
    {"left_path": "objects.namespace_precommitment.singleton_registry_transition_profile_root_sha256", "right_path": "objects.singleton_registration.singleton_registry_transition_profile_root_sha256", "condition": "literal V6 namespace profile pin repeats in final registration"},
    {"left_path": "objects.namespace_precommitment.singleton_registry_proof_profile_root_sha256", "right_path": "objects.global_registry_sparse_map_proof.singleton_registry_proof_profile_root_sha256", "condition": "literal V6 namespace proof profile resolves the proof consumer"},
    {"left_path": "objects.namespace_precommitment.singleton_registry_proof_profile_root_sha256", "right_path": "objects.global_registry_post_state.singleton_registry_proof_profile_root_sha256", "condition": "literal V6 namespace proof profile repeats in typed post state"},
    {"left_path": "objects.namespace_precommitment.singleton_registry_proof_profile_root_sha256", "right_path": "objects.singleton_registration.singleton_registry_proof_profile_root_sha256", "condition": "literal V6 namespace proof profile repeats in final registration"},
    {"left_path": "objects.singleton_registration_request.namespace_precommitment_sha256", "right_path": "instances.next_global_registry_pre_state.namespace_precommitment_root_sha256", "condition": "literal V6 completed request namespace becomes the next authoritative pre-state"},
    {"left_path": "objects.singleton_registration_request.pinned_context_sha256", "right_path": "instances.next_global_registry_pre_state.pinned_context_root_sha256", "condition": "literal V6 completed request context becomes the next authoritative pre-state"},
])
generation_equality_rows = [
    {"left_path": "objects.generation_reservation.generation_reservation_sha256", "right_path": "objects.generation_reservation_ledger_evidence.generation_reservation_sha256", "condition": "ledger transition authenticates exact reservation"},
    {"left_path": "objects.generation_reservation_ledger_evidence.generation_reservation_ledger_evidence_sha256", "right_path": "objects.generation_terminal_outcome.generation_reservation_ledger_evidence_sha256", "condition": "outcome consumes exact reserved head"},
    {"left_path": "objects.generation_terminal_outcome.generation_terminal_outcome_sha256", "right_path": "objects.generation_terminal_anchor_evidence.generation_terminal_outcome_sha256", "condition": "terminal authority authenticates exact outcome"},
    {"left_path": "objects.generation_reservation.reservation_slot_key_sha256", "right_path": "objects.generation_reservation_ledger_evidence.reservation_slot_key_sha256", "condition": "exact derived namespace epoch sequence role slot"},
    {"left_path": "objects.generation_reservation.reservation_slot_key_sha256", "right_path": "objects.generation_terminal_anchor_evidence.reservation_slot_key_sha256", "condition": "same slot consumed once"},
    {"left_path": "objects.generation_reservation.public_beacon_pre_reveal_evidence_sha256", "right_path": "objects.generation_reservation_ledger_evidence.public_beacon_pre_reveal_evidence_sha256", "condition": "ledger CAS consumes the exact pre-reveal head selected before signing"},
    {"left_path": "objects.generation_reservation.public_beacon_pre_reveal_evidence_sha256", "right_path": "objects.generation_terminal_outcome.public_beacon_pre_reveal_evidence_sha256", "condition": "outcome consumes the same pre-reveal head and round"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.namespace_precommitment_sha256", "right_path": "objects.generation_reservation.namespace_precommitment_sha256", "condition": "pre-reveal head is registration-local and cannot be replayed across namespaces"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.pinned_context_sha256", "right_path": "objects.generation_reservation.pinned_context_sha256", "condition": "pre-reveal head is bound to the exact immutable context"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.singleton_registration_sha256", "right_path": "objects.generation_reservation.singleton_registration_sha256", "condition": "pre-reveal head is bound to the exact finalized singleton registration"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.journal_id_token", "right_path": "objects.generation_reservation.journal_id_token", "condition": "same registered journal identity"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.journal_epoch", "right_path": "objects.generation_reservation.journal_epoch", "condition": "same fixed registered journal epoch"},
    {"left_path": "objects.generation_reservation.journal_id_token", "right_path": "objects.beacon_reservation_order_evidence.journal_id_token", "condition": "cross-system order proof binds the same registered journal"},
    {"left_path": "objects.generation_reservation_ledger_evidence.generation_reservation_ledger_evidence_sha256", "right_path": "objects.beacon_reservation_order_evidence.generation_reservation_ledger_evidence_sha256", "condition": "order proof binds the exact committed ledger CAS"},
    {"left_path": "objects.beacon_reservation_order_evidence.beacon_reservation_order_evidence_sha256", "right_path": "objects.generation_terminal_outcome.beacon_reservation_order_evidence_sha256", "condition": "outcome accepted only after exact before-reveal order proof"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.committed_future_round_index", "right_path": "objects.generation_reservation.public_round_index", "condition": "exact future unrevealed round selected before reservation"},
    {"left_path": "objects.generation_reservation.public_round_index", "right_path": "objects.beacon_reservation_order_evidence.public_round_index", "condition": "order proof covers same round"},
    {"left_path": "objects.generation_reservation.public_round_index", "right_path": "objects.generation_terminal_outcome.public_round_index", "condition": "outcome reveals same round"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.committed_round_output_sha256", "right_path": "objects.generation_terminal_outcome.public_beacon_output_sha256", "condition": "SHA256 of revealed exact beacon output equals prior committed output hash"},
    {"left_path": "objects.generation_reservation.output_generation_mode", "right_path": "objects.generation_reservation_ledger_evidence.output_generation_mode_for_evidence", "condition": "both equal exact output-role table mode"},
    {"left_path": "objects.generation_reservation.output_generation_mode", "right_path": "objects.generation_terminal_outcome.output_generation_mode", "condition": "both equal exact output-role table mode"},
    {"left_path": "objects.generation_reservation.output_generation_mode", "right_path": "objects.generation_terminal_anchor_evidence.output_generation_mode_for_evidence", "condition": "both equal exact output-role table mode"},
    {"left_path": "objects.generation_reservation_ledger_evidence.pre_slot_state", "right_path": "constant.UNASSIGNED", "condition": "reservation transition exact pre state"},
    {"left_path": "objects.generation_reservation_ledger_evidence.post_slot_state", "right_path": "constant.RESERVED_ATTEMPT_ZERO", "condition": "reservation transition exact post state"},
    {"left_path": "objects.generation_terminal_anchor_evidence.pre_slot_state", "right_path": "constant.RESERVED_ATTEMPT_ZERO", "condition": "terminal transition exact pre state"},
    {"left_path": "objects.generation_terminal_anchor_evidence.post_slot_state", "right_path": "constant.CONSUMED_TERMINAL", "condition": "terminal transition exact post state"},
]
for right_object in ["generation_reservation_ledger_evidence", "generation_terminal_outcome", "beacon_reservation_order_evidence", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation.generation_reservation_sha256", "right_path": f"objects.{right_object}.generation_reservation_sha256", "condition": "every downstream transaction object consumes the exact signed attempt-zero reservation"})
for right_object in ["generation_terminal_outcome", "beacon_reservation_order_evidence", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation_ledger_evidence.generation_reservation_ledger_evidence_sha256", "right_path": f"objects.{right_object}.generation_reservation_ledger_evidence_sha256", "condition": "every downstream transaction object consumes the exact authoritative reservation-ledger CAS"})
for field in ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch"]:
    carrier_objects = ["generation_reservation", "generation_reservation_ledger_evidence", "generation_terminal_outcome", "beacon_reservation_order_evidence", "generation_terminal_anchor_evidence"]
    for right_object in carrier_objects[1:]:
        generation_equality_rows.append({"left_path": f"objects.generation_reservation.{field}", "right_path": f"objects.{right_object}.{field}", "condition": "same immutable registered namespace context and journal identity across complete attempt-zero transaction"})
for right_object in ["generation_reservation_ledger_evidence", "generation_terminal_outcome", "beacon_reservation_order_evidence", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.extend([
        {"left_path": "objects.generation_reservation.reserved_next_sequence", "right_path": f"objects.{right_object}.reserved_sequence", "condition": "same atomically reserved authoritative next sequence"},
        {"left_path": "objects.generation_reservation.output_role", "right_path": f"objects.{right_object}.output_role", "condition": "same exact closed field-path output role"},
    ])
for right_object in ["generation_reservation_ledger_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.extend([
        {"left_path": "objects.generation_reservation.attempt_index", "right_path": f"objects.{right_object}.attempt_index", "condition": "attempt index zero throughout complete transaction"},
        {"left_path": "objects.generation_reservation.output_generation_mode", "right_path": f"objects.{right_object}.output_generation_mode", "condition": "same exact output-role-conditioned generation mode"},
        {"left_path": "objects.generation_reservation.reservation_slot_key_sha256", "right_path": f"objects.{right_object}.reservation_slot_key_sha256", "condition": "same unique namespace epoch sequence role slot key"},
    ])
generation_equality_rows.extend([
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.generation_sequence_transaction_claim_evidence_sha256", "right_path": "objects.pre_witness_technical_health_evidence.generation_sequence_transaction_claim_evidence_sha256", "condition": "pre-output materialization commitment consumes the exact held sequence claim"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256", "right_path": "objects.pre_witness_technical_health_evidence.sequence_transaction_claim_slot_key_sha256", "condition": "materialization commitment binds exact claim slot"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256", "right_path": "objects.pre_witness_technical_health_evidence.sequence_transaction_claim_statement_sha256", "condition": "materialization commitment binds exact claim statement including ledger history"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence", "right_path": "objects.pre_witness_technical_health_evidence.reserved_sequence", "condition": "materialization commitment covers exact locked sequence"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind", "right_path": "objects.pre_witness_technical_health_evidence.authoritative_pre_state_kind", "condition": "materialization commitment covers exact current pre-state kind"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.fixed_role_lifecycle_order_root_sha256", "right_path": "objects.pre_witness_technical_health_evidence.fixed_role_lifecycle_order_root_sha256", "condition": "materialization commitment covers all ten roles in exact order"},
    {"left_path": "objects.pre_witness_technical_health_evidence.fixed_terminal_deadline_round_delta", "right_path": "objects.pinned_context.fixed_terminal_deadline_round_delta", "condition": "one exact fixed deadline delta is committed before every role allocation"},
    {"left_path": "objects.generation_reservation.expected_pre_reservation_ledger_head_evidence_sha256", "right_path": "objects.generation_reservation_ledger_evidence.prior_reservation_ledger_head_evidence_sha256", "condition": "ledger CAS consumes exact expected independently current prior head including null genesis base"},
    {"left_path": "objects.generation_reservation.expected_pre_reservation_ledger_state_root_sha256", "right_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_state_root_sha256", "condition": "ledger CAS consumes exact expected pre root"},
    {"left_path": "objects.generation_reservation.expected_pre_reservation_ledger_state_object_sha256", "right_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_state_object_sha256", "condition": "ledger CAS consumes exact expected byte-available pre-state object"},
    {"left_path": "objects.generation_reservation.expected_pre_reservation_ledger_counter", "right_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_counter", "condition": "ledger CAS consumes exact expected pre counter"},
    {"left_path": "objects.generation_reservation_ledger_evidence.post_reservation_ledger_state_root_sha256", "right_path": "objects.generation_terminal_anchor_evidence.pre_reservation_ledger_state_root_sha256", "condition": "terminal CAS starts at exact reserved post root"},
    {"left_path": "objects.generation_reservation_ledger_evidence.post_reservation_ledger_state_object_sha256", "right_path": "objects.generation_terminal_anchor_evidence.pre_reservation_ledger_state_object_sha256", "condition": "terminal CAS starts at exact reserved byte-available post-state object"},
    {"left_path": "objects.generation_reservation_ledger_evidence.post_reservation_ledger_counter", "right_path": "objects.generation_terminal_anchor_evidence.pre_reservation_ledger_counter", "condition": "terminal CAS starts at exact reserved post counter"},
    {"left_path": "objects.generation_reservation_ledger_evidence.generation_reservation_ledger_evidence_sha256", "right_path": "objects.generation_terminal_anchor_evidence.prior_reservation_ledger_head_evidence_sha256", "condition": "reserved ledger evidence is the exact terminal transition prior head"},
    {"left_path": "objects.generation_terminal_outcome.terminal_outcome", "right_path": "objects.generation_terminal_anchor_evidence.terminal_outcome", "condition": "independent anchor authenticates the exact SUCCESS or FAILED branch"},
    {"left_path": "objects.generation_terminal_outcome.generated_output_sha256", "right_path": "objects.generation_terminal_anchor_evidence.generated_output_sha256", "condition": "independent anchor authenticates exact nullable generated output hash"},
    {"left_path": "objects.generation_reservation_ledger_evidence.post_reservation_ledger_counter", "right_path": "objects.beacon_reservation_order_evidence.ledger_post_counter", "condition": "cross-system order proof covers the exact committed reservation-ledger counter"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.public_beacon_pre_reveal_head_counter", "right_path": "objects.beacon_reservation_order_evidence.public_beacon_pre_reveal_head_counter", "condition": "order proof consumes exact pre-reveal head counter"},
    {"left_path": "objects.generation_reservation.attempt_index", "right_path": "objects.beacon_reservation_order_evidence.output_attempt_index", "condition": "cross-system order proof is itself attempt-zero evidence for the exact reservation"},
])

# Complete the transaction inventory physically. A hash link authenticates an
# object but never silently supplies equality for its repeated scalar fields.
reservation_projection_by_object = {
    "beacon_reservation_order_evidence": {
        "namespace_precommitment_sha256": "namespace_precommitment_sha256", "pinned_context_sha256": "pinned_context_sha256", "singleton_registration_sha256": "singleton_registration_sha256", "journal_id_token": "journal_id_token", "journal_epoch": "journal_epoch", "reserved_next_sequence": "reserved_sequence", "output_role": "output_role", "output_generation_mode": "reserved_output_generation_mode", "attempt_index": "reservation_attempt_index", "reservation_slot_key_sha256": "reservation_slot_key_sha256", "public_round_index": "public_round_index", "fixed_terminal_deadline_round_index": "fixed_terminal_deadline_round_index", "public_beacon_pre_reveal_head_counter": "public_beacon_pre_reveal_head_counter",
    },
    "public_beacon_reveal_evidence": {
        "namespace_precommitment_sha256": "namespace_precommitment_sha256", "pinned_context_sha256": "pinned_context_sha256", "singleton_registration_sha256": "singleton_registration_sha256", "journal_id_token": "journal_id_token", "journal_epoch": "journal_epoch", "reserved_next_sequence": "reserved_sequence", "output_role": "output_role", "output_generation_mode": "reserved_output_generation_mode", "attempt_index": "reservation_attempt_index", "reservation_slot_key_sha256": "reservation_slot_key_sha256", "public_round_index": "public_round_index", "fixed_terminal_deadline_round_index": "fixed_terminal_deadline_round_index", "public_beacon_pre_reveal_head_counter": "public_beacon_pre_reveal_head_counter",
    },
    "terminal_deadline_observation_evidence": {
        "namespace_precommitment_sha256": "namespace_precommitment_sha256", "pinned_context_sha256": "pinned_context_sha256", "singleton_registration_sha256": "singleton_registration_sha256", "journal_id_token": "journal_id_token", "journal_epoch": "journal_epoch", "reserved_next_sequence": "reserved_sequence", "output_role": "output_role", "output_generation_mode": "reserved_output_generation_mode", "attempt_index": "reservation_attempt_index", "reservation_slot_key_sha256": "reservation_slot_key_sha256", "public_round_index": "generation_public_round_index", "fixed_terminal_deadline_round_index": "fixed_terminal_deadline_round_index",
    },
    "generation_terminal_outcome": {
        "namespace_precommitment_sha256": "namespace_precommitment_sha256", "pinned_context_sha256": "pinned_context_sha256", "singleton_registration_sha256": "singleton_registration_sha256", "journal_id_token": "journal_id_token", "journal_epoch": "journal_epoch", "reserved_next_sequence": "reserved_sequence", "output_role": "output_role", "output_generation_mode": "output_generation_mode", "attempt_index": "attempt_index", "reservation_slot_key_sha256": "reservation_slot_key_sha256", "public_round_index": "public_round_index", "fixed_terminal_deadline_round_index": "fixed_terminal_deadline_round_index",
    },
    "generation_terminal_anchor_evidence": {
        "namespace_precommitment_sha256": "namespace_precommitment_sha256", "pinned_context_sha256": "pinned_context_sha256", "singleton_registration_sha256": "singleton_registration_sha256", "journal_id_token": "journal_id_token", "journal_epoch": "journal_epoch", "reserved_next_sequence": "reserved_sequence", "output_role": "output_role", "output_generation_mode": "output_generation_mode", "attempt_index": "attempt_index", "reservation_slot_key_sha256": "reservation_slot_key_sha256", "fixed_terminal_deadline_round_index": "fixed_terminal_deadline_round_index",
    },
}
for downstream_object, projection in reservation_projection_by_object.items():
    for reservation_field, downstream_field in projection.items():
        generation_equality_rows.append({
            "left_path": f"objects.generation_reservation.{reservation_field}",
            "right_path": f"objects.{downstream_object}.{downstream_field}",
            "condition": "exact signed reservation projection; no role sequence slot round mode attempt context or deadline transplant",
        })

for downstream_object in ["generation_reservation_ledger_evidence", "beacon_reservation_order_evidence", "public_beacon_reveal_evidence", "terminal_deadline_observation_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation.fixed_terminal_deadline_round_delta", "right_path": f"objects.{downstream_object}.fixed_terminal_deadline_round_delta", "condition": "exact pinned deadline delta copy for verifier-recomputed checked deadline"})
    generation_equality_rows.append({"left_path": "objects.generation_reservation.deadline_beacon_output_recovery_commitment_sha256", "right_path": f"objects.{downstream_object}.deadline_beacon_output_recovery_commitment_sha256", "condition": "same pre-output nonabortable deadline-beacon recovery commitment"})
for downstream_object in ["generation_reservation_ledger_evidence", "beacon_reservation_order_evidence", "public_beacon_reveal_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation.public_beacon_output_recovery_commitment_sha256", "right_path": f"objects.{downstream_object}.public_beacon_output_recovery_commitment_sha256", "condition": "same role-scoped pre-output nonabortable generation-beacon recovery commitment"})
for downstream_object in ["generation_reservation_ledger_evidence", "beacon_reservation_order_evidence", "public_beacon_reveal_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation.beacon_allocation_slot_key_sha256", "right_path": f"objects.{downstream_object}.beacon_allocation_slot_key_sha256", "condition": "same one-use registration epoch sequence role attempt-zero allocation slot"})

for downstream_object in ["generation_reservation_ledger_evidence", "beacon_reservation_order_evidence", "public_beacon_reveal_evidence", "terminal_deadline_observation_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation.generation_reservation_sha256", "right_path": f"objects.{downstream_object}.generation_reservation_sha256", "condition": "same exact role-qualified reservation instance"})
for downstream_object in ["beacon_reservation_order_evidence", "public_beacon_reveal_evidence", "terminal_deadline_observation_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation_ledger_evidence.generation_reservation_ledger_evidence_sha256", "right_path": f"objects.{downstream_object}.generation_reservation_ledger_evidence_sha256", "condition": "same exact role-qualified reservation-ledger evidence instance"})
for downstream_object in ["public_beacon_reveal_evidence", "generation_terminal_outcome"]:
    generation_equality_rows.append({"left_path": "objects.beacon_reservation_order_evidence.beacon_reservation_order_evidence_sha256", "right_path": f"objects.{downstream_object}.beacon_reservation_order_evidence_sha256", "condition": "same exact role-qualified before-reveal order evidence"})
for downstream_object in ["terminal_deadline_observation_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.public_beacon_reveal_evidence.public_beacon_reveal_evidence_sha256", "right_path": f"objects.{downstream_object}.public_beacon_reveal_evidence_sha256", "condition": "same exact role-qualified reveal evidence"})
for downstream_object in ["generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.terminal_deadline_observation_evidence.terminal_deadline_observation_evidence_sha256", "right_path": f"objects.{downstream_object}.terminal_deadline_observation_evidence_sha256", "condition": "same exact role-qualified deadline observation"})
generation_equality_rows.extend([
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.post_reservation_ledger_state_root_sha256", "right_path": "objects.pre_witness_technical_health_evidence.observed_sequence_claim_post_ledger_state_root_sha256", "condition": "pre-output health/materialization commitment observes exact claim-acquisition post-ledger root"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.post_reservation_ledger_state_object_sha256", "right_path": "objects.pre_witness_technical_health_evidence.observed_sequence_claim_post_ledger_state_object_sha256", "condition": "pre-output health/materialization commitment observes exact claim-acquisition post-ledger object"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.post_reservation_ledger_counter", "right_path": "objects.pre_witness_technical_health_evidence.observed_sequence_claim_post_ledger_counter", "condition": "pre-output health/materialization commitment observes exact claim-acquisition post-ledger counter"},
    {"left_path": "objects.pre_witness_technical_health_evidence.observed_confidential_generator_image_sha256", "right_path": "objects.pinned_context.confidential_generator_image_sha256", "condition": "measured generator image equals namespace-precommitted pin"},
    {"left_path": "objects.pre_witness_technical_health_evidence.observed_confidential_generator_profile_sha256", "right_path": "objects.pinned_context.confidential_generator_profile_sha256", "condition": "measured generator profile equals namespace-precommitted pin"},
    {"left_path": "objects.pre_witness_technical_health_evidence.observed_contributor_roster_sha256", "right_path": "objects.pinned_context.confidential_contributor_roster_sha256", "condition": "measured complete contributor roster equals namespace-precommitted pin"},
    {"left_path": "objects.pre_witness_technical_health_evidence.observed_contributor_key_root_sha256", "right_path": "objects.pinned_context.confidential_contributor_key_root_sha256", "condition": "measured contributor key root equals namespace-precommitted pin"},
])
for downstream_object in ["public_beacon_pre_reveal_evidence", "generation_reservation", "generation_reservation_ledger_evidence", "beacon_reservation_order_evidence", "public_beacon_reveal_evidence", "terminal_deadline_observation_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.pre_witness_technical_health_evidence.pre_witness_technical_health_evidence_sha256", "right_path": f"objects.{downstream_object}.pre_witness_technical_health_evidence_sha256", "condition": "every role consumes the same sequence-wide pre-output health/materialization commitment; no post-reveal branch input exists"})

instance_aliases = {
    "active_generation_transaction_projection": {
        "schema_object": "objects.generation_sequence_transaction_claim_evidence",
        "instance_key": "the one exact HELD sequence claim whose self hash is repeated by every role transaction",
        "logical_field_projection": {
            "reserved_next_sequence": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence",
            "authoritative_pre_journal_state_root_sha256": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_root_sha256",
            "authoritative_pre_journal_state_object_sha256": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_object_sha256",
            "authoritative_pre_record_count": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_record_count",
            "authoritative_pre_head_sequence": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_head_sequence",
        },
    },
    "active_normal_transition_request": {
        "schema_object": "objects.transition_request",
        "instance_key": "the exact normal transition request whose self hash is copied by the active commit_evidence",
        "uniqueness_binding": "objects.commit_evidence.transition_request_sha256 == objects.transition_request.transition_request_sha256",
    },
    "active_normal_commit_evidence": {
        "schema_object": "objects.commit_evidence",
        "instance_key": "the exact normal commit whose transition_request_sha256 resolves active_normal_transition_request",
    },
    "current_normal_journal_state": {
        "schema_object": "objects.journal_state",
        "instance_key": "the exact prior-transaction normal journal-state object named by the independently current prior normal sequence commit; never the later target.JOURNAL_STATE_STATE_NONCE instance",
    },
    "current_pre_journal_state": {
        "schema_object_by_kind": {"REGISTERED_GENESIS": "objects.genesis_journal_state", "NORMAL_MEMORY_RECORD_STATE": "objects.journal_state", "GENERATION_FAILURE_STATE": "objects.generation_failure_journal_state"},
        "instance_key": "one exact independently current pre-claim journal/authority/anchor snapshot selected before sequence-claim acquisition; its authenticated source type fixes state_kind and no completed claim field selects it",
        "authenticated_origin_by_kind": {
            "REGISTERED_GENESIS": {
                "origin_node": "singleton_registration",
                "authentication_chain": "singleton_registration -> singleton_registration_full_genesis_bundle -> exact genesis journal state, genesis external anchor, and genesis state-authority head",
            },
            "NORMAL_MEMORY_RECORD_STATE": {
                "origin_node": "current_normal_journal_state",
                "authentication_chain": "the independently current prior normal commit hashes the exact typed prior-transaction post journal-state object, post authority head, post anchor root, counters, count, sequence, and receipt/event heads",
            },
            "GENERATION_FAILURE_STATE": {
                "origin_node": "current_failure_state_authority_head_observation",
                "authentication_chain": "the independently current prior failure/refusal authority observation consumes the exact anchor observation, failure commit, failure journal-state object, counters, count, sequence, and failure head sentinels",
            },
        },
        "origin_selection_is_authenticated_exhaustive_mutually_exclusive_and_not_caller_selected": True,
        "logical_field_projection_by_kind": {
            "REGISTERED_GENESIS": {
                "state_kind": "constant.REGISTERED_GENESIS",
                "journal_id_token": "objects.genesis_journal_state.journal_id_token",
                "journal_epoch": "objects.genesis_journal_state.journal_epoch",
                "journal_state_root_sha256": "objects.genesis_journal_state.genesis_journal_state_root_sha256",
                "journal_state_object_sha256": "objects.genesis_journal_state.genesis_journal_state_object_sha256",
                "committed_record_count": "objects.genesis_journal_state.committed_record_count",
                "head_sequence": "objects.genesis_journal_state.head_sequence",
                "head_receipt_hash_sha256": "objects.genesis_journal_state.head_receipt_hash_sha256",
                "head_event_hash_sha256": "objects.genesis_journal_state.head_event_hash_sha256",
                "consumed_receipt_token_root_sha256": "objects.genesis_journal_state.consumed_receipt_token_root_sha256",
                "consumed_scope_token_root_sha256": "objects.genesis_journal_state.consumed_scope_token_root_sha256",
                "consumed_proof_token_root_sha256": "objects.genesis_journal_state.consumed_proof_token_root_sha256",
                "pinned_context_sha256": "objects.genesis_journal_state.pinned_context_sha256",
                "singleton_registration_sha256": "objects.singleton_registration.singleton_registration_sha256",
            },
            "NORMAL_MEMORY_RECORD_STATE": {
                "state_kind": "constant.NORMAL_MEMORY_RECORD_STATE",
                "journal_id_token": "instances.current_normal_journal_state.journal_id_token",
                "journal_epoch": "instances.current_normal_journal_state.journal_epoch",
                "journal_state_root_sha256": "instances.current_normal_journal_state.journal_state_root_sha256",
                "journal_state_object_sha256": "instances.current_normal_journal_state.journal_state_object_sha256",
                "committed_record_count": "instances.current_normal_journal_state.committed_record_count",
                "head_sequence": "instances.current_normal_journal_state.head_sequence",
                "head_receipt_hash_sha256": "instances.current_normal_journal_state.head_receipt_hash_sha256",
                "head_event_hash_sha256": "instances.current_normal_journal_state.head_event_hash_sha256",
                "consumed_receipt_token_root_sha256": "instances.current_normal_journal_state.consumed_receipt_token_root_sha256",
                "consumed_scope_token_root_sha256": "instances.current_normal_journal_state.consumed_scope_token_root_sha256",
                "consumed_proof_token_root_sha256": "instances.current_normal_journal_state.consumed_proof_token_root_sha256",
                "pinned_context_sha256": "instances.current_normal_journal_state.pinned_context_sha256",
                "singleton_registration_sha256": "instances.current_normal_journal_state.singleton_registration_sha256",
            },
            "GENERATION_FAILURE_STATE": {
                "state_kind": "constant.GENERATION_FAILURE_STATE",
                "journal_id_token": "instances.current_failure_journal_state.journal_id_token",
                "journal_epoch": "instances.current_failure_journal_state.journal_epoch",
                "journal_state_root_sha256": "instances.current_failure_journal_state.generation_failure_journal_state_root_sha256",
                "journal_state_object_sha256": "instances.current_failure_journal_state.generation_failure_journal_state_object_sha256",
                "committed_record_count": "instances.current_failure_journal_state.committed_record_count",
                "head_sequence": "instances.current_failure_journal_state.head_sequence",
                "head_receipt_hash_sha256": "instances.current_failure_journal_state.head_receipt_hash_sha256",
                "head_event_hash_sha256": "instances.current_failure_journal_state.head_event_hash_sha256",
                "consumed_receipt_token_root_sha256": "instances.current_failure_journal_state.consumed_receipt_token_root_sha256",
                "consumed_scope_token_root_sha256": "instances.current_failure_journal_state.consumed_scope_token_root_sha256",
                "consumed_proof_token_root_sha256": "instances.current_failure_journal_state.consumed_proof_token_root_sha256",
                "pinned_context_sha256": "instances.current_failure_journal_state.pinned_context_sha256",
                "singleton_registration_sha256": "instances.current_failure_journal_state.singleton_registration_sha256",
            },
        },
        "genesis_registration_resolution_is_unique_and_acyclic": "singleton_registration authenticates the pre-existing genesis object hash; genesis never contains the later registration hash",
    },
    "current_pre_state_authority_evidence": {
        "schema_object_by_kind": {"REGISTERED_GENESIS": "objects.genesis_state_authority_evidence", "NORMAL_MEMORY_RECORD_STATE": "objects.state_authority_head_evidence", "GENERATION_FAILURE_STATE": "objects.failure_state_authority_current_head_observation"},
        "instance_key": "exact independently current authority head selected by the same current_pre_journal_state kind",
        "logical_field_projection_by_kind": {
            "REGISTERED_GENESIS": {
                "state_authority_head_evidence_sha256": "objects.genesis_state_authority_evidence.genesis_state_authority_head_evidence_sha256",
                "authority_monotonic_counter": "objects.genesis_state_authority_evidence.authority_monotonic_counter",
                "external_anchor_root_sha256": "objects.genesis_state_authority_evidence.genesis_external_anchor_root_sha256",
                "journal_state_root_sha256": "objects.genesis_state_authority_evidence.genesis_journal_state_root_sha256",
                "journal_state_object_sha256": "objects.genesis_state_authority_evidence.genesis_journal_state_object_sha256",
                "committed_record_count": "objects.genesis_state_authority_evidence.committed_record_count",
                "head_sequence": "objects.genesis_state_authority_evidence.head_sequence",
                "head_receipt_hash_sha256": "objects.genesis_state_authority_evidence.head_receipt_hash_sha256",
                "head_event_hash_sha256": "objects.genesis_state_authority_evidence.head_event_hash_sha256",
            },
            "NORMAL_MEMORY_RECORD_STATE": {
                "state_authority_head_evidence_sha256": "objects.state_authority_head_evidence.state_authority_head_evidence_sha256",
                "authority_monotonic_counter": "objects.state_authority_head_evidence.authority_monotonic_counter",
                "external_anchor_root_sha256": "objects.state_authority_head_evidence.external_anchor_root_sha256",
                "journal_state_root_sha256": "objects.state_authority_head_evidence.head_journal_state_root_sha256",
                "journal_state_object_sha256": "objects.state_authority_head_evidence.head_journal_state_object_sha256",
                "committed_record_count": "objects.state_authority_head_evidence.committed_record_count",
                "head_sequence": "objects.state_authority_head_evidence.head_sequence",
                "head_receipt_hash_sha256": "objects.state_authority_head_evidence.head_receipt_hash_sha256",
                "head_event_hash_sha256": "objects.state_authority_head_evidence.head_event_hash_sha256",
            },
            "GENERATION_FAILURE_STATE": {
                "state_authority_head_evidence_sha256": "instances.current_failure_state_authority_head_observation.post_failure_state_authority_head_evidence_sha256",
                "authority_monotonic_counter": "instances.current_failure_state_authority_head_observation.post_state_authority_monotonic_counter",
                "external_anchor_root_sha256": "instances.current_failure_state_authority_head_observation.post_failure_external_anchor_root_sha256",
                "journal_state_root_sha256": "instances.current_failure_state_authority_head_observation.post_failure_state_root_sha256",
                "journal_state_object_sha256": "instances.current_failure_state_authority_head_observation.post_failure_state_object_sha256",
                "committed_record_count": "instances.current_failure_state_authority_head_observation.post_record_count",
                "head_sequence": "instances.current_failure_state_authority_head_observation.post_head_sequence",
                "head_receipt_hash_sha256": "instances.current_failure_state_authority_head_observation.post_head_receipt_hash_sha256",
                "head_event_hash_sha256": "instances.current_failure_state_authority_head_observation.post_head_event_hash_sha256",
            },
        },
    },
    "current_pre_external_anchor_evidence": {
        "schema_object_by_kind": {"REGISTERED_GENESIS": "objects.genesis_external_anchor_evidence", "NORMAL_MEMORY_RECORD_STATE": "objects.external_anchor_evidence", "GENERATION_FAILURE_STATE": "objects.failure_state_authority_current_head_observation"},
        "instance_key": "exact independently current external anchor selected by the same current_pre_journal_state kind",
        "logical_field_projection_by_kind": {
            "REGISTERED_GENESIS": {
                "external_anchor_root_sha256": "objects.genesis_external_anchor_evidence.genesis_external_anchor_root_sha256",
                "anchor_monotonic_counter": "objects.genesis_external_anchor_evidence.anchor_monotonic_counter",
                "state_authority_monotonic_counter": "objects.genesis_external_anchor_evidence.state_authority_monotonic_counter",
                "journal_state_root_sha256": "objects.genesis_external_anchor_evidence.genesis_journal_state_root_sha256",
                "journal_state_object_sha256": "objects.genesis_external_anchor_evidence.genesis_journal_state_object_sha256",
                "committed_record_count": "objects.genesis_external_anchor_evidence.committed_record_count",
                "head_sequence": "objects.genesis_external_anchor_evidence.head_sequence",
                "head_receipt_hash_sha256": "objects.genesis_external_anchor_evidence.head_receipt_hash_sha256",
                "head_event_hash_sha256": "objects.genesis_external_anchor_evidence.head_event_hash_sha256",
            },
            "NORMAL_MEMORY_RECORD_STATE": {
                "external_anchor_root_sha256": "objects.external_anchor_evidence.external_anchor_root_sha256",
                "anchor_monotonic_counter": "objects.external_anchor_evidence.anchor_monotonic_counter",
                "state_authority_monotonic_counter": "objects.external_anchor_evidence.state_authority_monotonic_counter",
                "journal_state_root_sha256": "objects.external_anchor_evidence.journal_state_root_sha256",
                "journal_state_object_sha256": "objects.external_anchor_evidence.journal_state_object_sha256",
                "committed_record_count": "objects.external_anchor_evidence.committed_record_count",
                "head_sequence": "objects.external_anchor_evidence.head_sequence",
                "head_receipt_hash_sha256": "objects.external_anchor_evidence.head_receipt_hash_sha256",
                "head_event_hash_sha256": "objects.external_anchor_evidence.head_event_hash_sha256",
            },
            "GENERATION_FAILURE_STATE": {
                "external_anchor_root_sha256": "instances.current_failure_state_authority_head_observation.post_failure_external_anchor_root_sha256",
                "anchor_monotonic_counter": "instances.current_failure_state_authority_head_observation.post_external_anchor_monotonic_counter",
                "state_authority_monotonic_counter": "instances.current_failure_state_authority_head_observation.post_state_authority_monotonic_counter",
                "journal_state_root_sha256": "instances.current_failure_state_authority_head_observation.post_failure_state_root_sha256",
                "journal_state_object_sha256": "instances.current_failure_state_authority_head_observation.post_failure_state_object_sha256",
                "committed_record_count": "instances.current_failure_state_authority_head_observation.post_record_count",
                "head_sequence": "instances.current_failure_state_authority_head_observation.post_head_sequence",
                "head_receipt_hash_sha256": "instances.current_failure_state_authority_head_observation.post_head_receipt_hash_sha256",
                "head_event_hash_sha256": "instances.current_failure_state_authority_head_observation.post_head_event_hash_sha256",
            },
        },
    },
    "current_failure_external_anchor_head_observation": {"schema_object": "objects.failure_external_anchor_current_head_observation", "instance_key": "exact independently current failure external-anchor observation selected only for GENERATION_FAILURE_STATE"},
    "current_failure_state_authority_head_observation": {"schema_object": "objects.failure_state_authority_current_head_observation", "instance_key": "exact independently current failure authority observation consuming the selected anchor observation; selected only for GENERATION_FAILURE_STATE"},
    "current_failure_record": {"schema_object": "objects.generation_failure_record", "instance_key": "exact prior-sequence failure/refusal record named by the independently current journal state commit and both current-head observations"},
    "current_failure_sequence_commit": {"schema_object": "objects.generation_failure_sequence_commit_evidence", "instance_key": "exact completed failure/refusal commit authenticated by both selected current-head observations"},
    "current_failure_journal_state": {"schema_object": "objects.generation_failure_journal_state", "instance_key": "exact typed failure journal state hashed by the selected completed failure commit"},
    "current_post_journal_state": {"schema_object": "objects.journal_state", "instance_key": "transition-request post journal state root/object"},
    "global_registry_pre_state": {"schema_object": "objects.authoritative_registry_pre_state", "instance_key": "unique independently current typed authoritative registry pre-state; counter zero exact sentinel object or positive prior singleton-registration successor"},
    "prior_authoritative_registry_pre_state": {"schema_object": "objects.authoritative_registry_pre_state", "instance_key": "exact prior transaction next-consumer pre-state selected only for positive recursion"},
    "prior_global_registry_completed_request": {"schema_object": "objects.singleton_registration_request", "instance_key": "exact completed registrar-signed request from the prior singleton-registration transaction selected only for positive recursion"},
    "prior_global_registry_sparse_map_update": {"schema_object": "objects.global_registry_sparse_map_update", "instance_key": "exact verified sparse-map update from the prior singleton-registration transaction selected only for positive recursion"},
    "prior_global_registry_post_head": {"schema_object": "objects.global_registry_post_head", "instance_key": "exact typed post head from the prior singleton-registration transaction selected only for positive recursion"},
    "prior_global_registry_singleton_registration": {"schema_object": "objects.singleton_registration", "instance_key": "exact predecessor singleton registration named by the positive authoritative registry pre-state"},
    "prior_global_registry_post_state": {"schema_object": "objects.global_registry_post_state", "instance_key": "the unique independently current prior completed typed post-state selected only when the pre-state counter is positive"},
    "next_global_registry_pre_state": {"schema_object": "objects.authoritative_registry_pre_state", "instance_key": "exact typed next consumer created only after final singleton registration plus post head/state are byte-available"},
    "reservation_ledger_pre_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": "reservation-ledger-evidence.pre_reservation_ledger_state_object_sha256"},
    "reservation_ledger_reserved_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": "reservation-ledger-evidence.post_reservation_ledger_state_object_sha256"},
    "reservation_ledger_consumed_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": "terminal-anchor.post_reservation_ledger_state_object_sha256"},
    "sequence_claim_acquire_pre_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": "sequence-claim-evidence.pre_reservation_ledger_state_object_sha256", "source_by_counter": {"ZERO": "exact registered counter-zero ledger state", "POSITIVE_AFTER_NORMAL": "exact prior commit_evidence sequence-claim RELEASED post state", "POSITIVE_AFTER_FAILURE_OR_REFUSAL": "exact prior generation_failure_sequence_commit_evidence sequence-claim RELEASED post state"}, "caller_source_choice_allowed": False},
    "prior_normal_sequence_claim_release_commit": {"schema_object": "objects.commit_evidence", "instance_key": "unique independently current prior normal journal commit with atomic claim release"},
    "prior_normal_sequence_claim_release_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": "exact RELEASED post ledger state hashed by the prior normal commit"},
    "prior_failure_sequence_claim_release_commit": {"schema_object": "objects.generation_failure_sequence_commit_evidence", "instance_key": "unique independently current prior technical-failure or hidden-refusal commit with atomic claim release"},
    "prior_failure_sequence_claim_release_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": "exact RELEASED post ledger state hashed by the prior failure/refusal commit"},
    "sequence_claim_acquire_post_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": "sequence-claim-evidence.post_reservation_ledger_state_object_sha256"},
    "sequence_claim_normal_release_post_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": "normal commit sequence_claim_post_reservation_ledger_state_object_sha256"},
    "public_beacon_pre_reveal_pre_state": {"schema_object": "objects.public_beacon_pre_reveal_state", "instance_key": "pre-reveal-evidence.pre_public_beacon_pre_reveal_state_object_sha256"},
    "public_beacon_pre_reveal_post_state": {"schema_object": "objects.public_beacon_pre_reveal_state", "instance_key": "pre-reveal-evidence.post_public_beacon_pre_reveal_state_object_sha256"},
    "public_beacon_counter_zero_state": {"schema_object": "objects.public_beacon_pre_reveal_state", "instance_key": "exact singleton-registration/context/manifest-derived counter-zero beacon state with null prior evidence"},
    "prior_sequence_public_beacon_pre_reveal_evidence": {"schema_object": "objects.public_beacon_pre_reveal_evidence", "instance_key": "unique independently current prior-sequence authenticated beacon allocation head"},
    "prior_sequence_public_beacon_pre_reveal_post_state": {"schema_object": "objects.public_beacon_pre_reveal_state", "instance_key": "exact post-state object hashed by the independently current prior-sequence beacon evidence"},
    "current_public_beacon_pre_reveal_state": {"schema_object": "objects.public_beacon_pre_reveal_state", "instance_key": "independently current beacon head state before role zero", "source_by_counter": {"ZERO": "exact singleton-registration/context/manifest-derived counter-zero base and prior_evidence_sha256 JSON null", "POSITIVE": "exact post state of independently current prior public_beacon_pre_reveal_evidence with checked counter n-1 and prior_evidence_sha256 equal that evidence self hash"}, "logical_projection": {"prior_evidence_sha256": "counter-zero null or exact independently current prior evidence self hash", "namespace_precommitment_sha256": "resolved base/prior post namespace", "pinned_context_sha256": "resolved base/prior post context", "singleton_registration_sha256": "resolved base/prior post registration", "journal_id_token": "resolved base/prior post journal identifier", "journal_epoch": "resolved base/prior post epoch", "public_beacon_pre_reveal_state_root_sha256": "resolved base/prior post root", "public_beacon_pre_reveal_state_object_sha256": "resolved base/prior post object", "public_beacon_pre_reveal_state_counter": "resolved base/prior post counter", "beacon_allocation_map_root_sha256": "resolved base/prior post allocation map", "committed_future_round_index": "resolved base/prior post allocation cursor", "committed_round_output_sha256": "resolved base sentinel or prior post output commitment", "beacon_reveal_state": "exact PRE_REVEAL", "public_round_beacon_identity_sha256": "exact context pin", "public_round_beacon_profile_sha256": "exact context pin", "fixed_reveal_schedule_profile_sha256": "exact context pin", "public_beacon_pre_reveal_genesis_manifest_sha256": "exact context pin"}, "same_registration_identity_profile_schedule_and_allocation_map_recursion": True},
}
role_alias_schema_map = {
    "generation_reservation": ("reservation", "generation_reservation_sha256"),
    "generation_reservation_ledger_evidence": ("ledger_evidence", "generation_reservation_ledger_evidence_sha256"),
    "public_beacon_pre_reveal_evidence": ("pre_reveal_evidence", "public_beacon_pre_reveal_evidence_sha256"),
    "beacon_reservation_order_evidence": ("order", "beacon_reservation_order_evidence_sha256"),
    "role_producer_availability_commitment": ("availability_commitment", "role_producer_availability_commitment_sha256"),
    "role_producer_availability_evidence": ("availability_evidence", "role_producer_availability_evidence_sha256"),
    "public_beacon_reveal_evidence": ("reveal", "public_beacon_reveal_evidence_sha256"),
    "terminal_deadline_observation_evidence": ("deadline", "terminal_deadline_observation_evidence_sha256"),
    "generation_terminal_outcome": ("outcome", "generation_terminal_outcome_sha256"),
    "generation_terminal_anchor_evidence": ("anchor", "generation_terminal_anchor_evidence_sha256"),
    "generation_sequence_lifecycle_refusal_evidence": ("lifecycle_refusal", "generation_sequence_lifecycle_refusal_evidence_sha256"),
    "generation_failure_record": ("failure_record", "generation_failure_record_sha256"),
    "generation_failure_journal_state": ("failure_state", "generation_failure_journal_state_object_sha256"),
    "generation_failure_sequence_commit_evidence": ("failure_commit", "generation_failure_sequence_commit_evidence_sha256"),
    "failure_external_anchor_current_head_observation": ("failure_anchor_current_head_observation", "failure_external_anchor_current_head_observation_sha256"),
    "failure_state_authority_current_head_observation": ("failure_authority_current_head_observation", "failure_state_authority_current_head_observation_sha256"),
}
role_instance_aliases = {}
for role_row in output_role_table:
    role = role_row["role"]
    aliases = {}
    for schema_name, (alias_name, output_field) in role_alias_schema_map.items():
        aliases[alias_name] = {
            "schema_object": f"objects.{schema_name}",
            "instance_key": f"exact role {role} field {output_field} resolved from its role-specific lifecycle target or predecessor",
        }
    aliases.update({
        "ledger_pre_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": f"{role} ledger evidence pre-state object"},
        "ledger_reserved_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": f"{role} ledger evidence post-state / terminal-anchor pre-state object"},
        "ledger_consumed_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": f"{role} terminal-anchor post-state object"},
        "beacon_pre_state": {"schema_object": "objects.public_beacon_pre_reveal_state", "instance_key": f"{role} pre-reveal evidence pre-state object"},
        "beacon_post_state": {"schema_object": "objects.public_beacon_pre_reveal_state", "instance_key": f"{role} pre-reveal evidence post-state object"},
        "sequence_claim_failure_release_post_state": {"schema_object": "objects.generation_reservation_ledger_state", "instance_key": f"{role} branch-qualified technical-failure or hidden-refusal commit sequence-claim release post-state object"},
    })
    role_instance_aliases[role] = aliases
instance_aliases["roles"] = role_instance_aliases
doc["typed_instance_aliases"] = instance_aliases

# Materialize the V7 target-resolution projections as literal typed paths.  No
# association helper or hash-to-object search is part of validation.
generation_equality_rows.extend([
    {"left_path": "instances.active_generation_transaction_projection.generation_sequence_transaction_claim_evidence_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.generation_sequence_transaction_claim_evidence_sha256", "condition": "typed active transaction projection is the exact one sequence-wide completed claim object"},
    {"left_path": "instances.active_normal_transition_request.transition_request_sha256", "right_path": "objects.transition_request.transition_request_sha256", "condition": "typed active request is exactly target.TRANSITION_REQUEST_REQUEST_NONCE after its target nonce is materialized"},
    {"left_path": "instances.active_normal_commit_evidence.commit_evidence_sha256", "right_path": "objects.commit_evidence.commit_evidence_sha256", "condition": "typed active commit is exactly target.COMMIT_EVIDENCE_COMMIT_NONCE after its target nonce is materialized"},
    {"left_path": "instances.current_post_journal_state.journal_state_root_sha256", "right_path": "objects.journal_state.journal_state_root_sha256", "condition": "typed current post state is exactly target.JOURNAL_STATE_STATE_NONCE after its state nonce is materialized"},
    {"left_path": "instances.current_post_journal_state.journal_state_object_sha256", "right_path": "objects.journal_state.journal_state_object_sha256", "condition": "typed current post state object is exactly the same target.JOURNAL_STATE_STATE_NONCE instance"},
])
for claim_field, public_input_field in [
    ("reserved_next_sequence", "sequence"),
    ("authoritative_pre_journal_state_root_sha256", "expected_pre_journal_state_root_sha256"),
    ("authoritative_pre_journal_state_object_sha256", "expected_pre_journal_state_object_sha256"),
    ("authoritative_pre_record_count", "expected_pre_record_count"),
    ("authoritative_pre_head_sequence", "expected_pre_head_sequence"),
]:
    generation_equality_rows.append({
        "left_path": f"instances.active_generation_transaction_projection.{claim_field}",
        "right_path": f"objects.proof_public_inputs.{public_input_field}",
        "condition": "the one proof-public-input instance consumes the exact active sequence transaction projection",
    })
for claim_field, request_field in [
    ("reserved_next_sequence", "receipt_sequence"),
    ("authoritative_pre_journal_state_root_sha256", "pre_journal_state_root_sha256"),
    ("authoritative_pre_journal_state_object_sha256", "pre_journal_state_object_sha256"),
    ("authoritative_pre_record_count", "pre_record_count"),
    ("authoritative_pre_head_sequence", "pre_head_sequence"),
]:
    generation_equality_rows.append({
        "left_path": f"instances.active_generation_transaction_projection.{claim_field}",
        "right_path": f"instances.active_normal_transition_request.{request_field}",
        "condition": "the exact active normal transition request consumes the locked claim sequence and predecessor tuple",
    })
generation_equality_rows.extend([
    {"left_path": "instances.roles.TOKEN_ACCUMULATOR_PROOF_NONCE.failure_commit.generation_failure_record_sha256", "right_path": "instances.roles.TOKEN_ACCUMULATOR_PROOF_NONCE.failure_record.generation_failure_record_sha256", "condition": "typed role instance closure; no association search"},
    {"left_path": "instances.active_normal_transition_request.token_accumulator_proof_sha256", "right_path": "objects.token_accumulator_proof.token_accumulator_proof_sha256", "condition": "the active request names the unique token-accumulator proof target instance"},
    {"left_path": "instances.active_normal_commit_evidence.transition_request_sha256", "right_path": "instances.active_normal_transition_request.transition_request_sha256", "condition": "the active commit names the exact typed active normal transition request"},
    {"left_path": "instances.active_normal_commit_evidence.cas_expected_pre_state_root_sha256", "right_path": "instances.active_normal_transition_request.pre_journal_state_root_sha256", "condition": "active commit and request share the exact CAS predecessor root"},
    {"left_path": "instances.active_normal_commit_evidence.committed_pre_state_object_sha256", "right_path": "instances.active_normal_transition_request.pre_journal_state_object_sha256", "condition": "active commit and request share the exact CAS predecessor object"},
    {"left_path": "instances.active_normal_transition_request.post_journal_state_root_sha256", "right_path": "instances.current_post_journal_state.journal_state_root_sha256", "condition": "request post root resolves the one typed current post journal state"},
    {"left_path": "instances.active_normal_transition_request.post_journal_state_object_sha256", "right_path": "instances.current_post_journal_state.journal_state_object_sha256", "condition": "request post object resolves the same typed current post journal state"},
])

# Materialized typed derived-value endpoints.  These are not object instances:
# each is one exact verifier-recomputed SHA-256 value with a finite ordered
# preimage.  Physical equalities may reference only these declared paths; an
# undeclared `computed.*` namespace is never an endpoint.
generation_chain_member_fields = [
    "generation_reservation_sha256",
    "generation_reservation_ledger_evidence_sha256",
    "public_beacon_reveal_evidence_sha256",
    "terminal_deadline_observation_evidence_sha256",
    "generation_terminal_outcome_sha256",
    "generation_terminal_anchor_evidence_sha256",
]

def role_chain_member_paths(role):
    alias_fields = {
        "generation_reservation_sha256": "reservation.generation_reservation_sha256",
        "generation_reservation_ledger_evidence_sha256": "ledger_evidence.generation_reservation_ledger_evidence_sha256",
        "public_beacon_reveal_evidence_sha256": "reveal.public_beacon_reveal_evidence_sha256",
        "terminal_deadline_observation_evidence_sha256": "deadline.terminal_deadline_observation_evidence_sha256",
        "generation_terminal_outcome_sha256": "outcome.generation_terminal_outcome_sha256",
        "generation_terminal_anchor_evidence_sha256": "anchor.generation_terminal_anchor_evidence_sha256",
    }
    return [f"instances.roles.{role}.{alias_fields[field]}" for field in generation_chain_member_fields]

typed_derived_value_aliases = {
    "namespace": "derived",
    "complete_ten_role_success_chain_set_root_sha256": {
        "path": "derived.complete_ten_role_success_chain_set_root_sha256",
        "field_type": "sha256",
        "domain": "KIRA_MIND_V21_ACTIVE_COMPLETE_GENERATION_CHAIN_SET_ROOT_V1",
        "sequence_wide_pre_output_member_path": "objects.pre_witness_technical_health_evidence.pre_witness_technical_health_evidence_sha256",
        "ordered_roles": role_lifecycle_order,
        "ordered_role_member_paths": {
            role: role_chain_member_paths(role) for role in role_lifecycle_order
        },
        "formula": "SHA256(domain + NUL + exact sequence-wide pre-output member bytes + LF + for each fixed role in order: role ASCII + NUL + all six exact role-qualified 32-byte member hashes + LF); available only after all ten SUCCESS anchors and before final commit evidence",
        "caller_subset_order_or_input_allowed": False,
    },
    "roles": {},
}
for boundary_index, boundary_role in enumerate(role_lifecycle_order):
    typed_derived_value_aliases["roles"][boundary_role] = {
        "completed_success_role_prefix_root_sha256": {
            "path": f"derived.roles.{boundary_role}.completed_success_role_prefix_root_sha256",
            "field_type": "sha256",
            "domain": "KIRA_MIND_V21_COMPLETED_SUCCESS_ROLE_PREFIX_ROOT_V1",
            "boundary_role": boundary_role,
            "boundary_role_index": boundary_index,
            "sequence_wide_pre_output_member_path": "objects.pre_witness_technical_health_evidence.pre_witness_technical_health_evidence_sha256",
            "ordered_complete_success_prefix_roles": role_lifecycle_order[:boundary_index],
            "ordered_prefix_role_member_paths": {
                role: role_chain_member_paths(role) for role in role_lifecycle_order[:boundary_index]
            },
            "formula": "SHA256(domain + NUL + exact sequence-wide pre-output member bytes + LF + for each fixed prefix role in order: role ASCII + NUL + its six exact role-qualified 32-byte member hashes + LF); every included outcome is SUCCESS; boundary index zero has no role member",
            "caller_subset_order_or_input_allowed": False,
        }
    }
doc["typed_derived_value_aliases"] = typed_derived_value_aliases

role_index_derivation_rows = []
for role_index, role in enumerate(role_lifecycle_order):
    computed_prefix = f"derived.roles.{role}.completed_success_role_prefix_root_sha256"
    plan_path = f"objects.pre_witness_technical_health_evidence.{role_terminalization_plan_fields[role_index]}"
    role_index_derivation_rows.extend([
        {"left_path": plan_path, "right_path": "constant.MATERIALIZE_SUCCESS", "condition": f"materialization_commitment_result == COMPLETE_SEQUENCE_MATERIALIZATION_COMMITTED and the exact verifier-derived first technical-failure index is absent or greater than {role_index}"},
        {"left_path": plan_path, "right_path": "constant.FIXED_ROLE_TECHNICAL_FAILURE", "condition": f"materialization_commitment_result == COMPLETE_SEQUENCE_MATERIALIZATION_COMMITTED and the exact verifier-derived first technical-failure index equals {role_index}"},
        {"left_path": plan_path, "right_path": "constant.NOT_REACHED_AFTER_TERMINAL_BOUNDARY", "condition": f"materialization_commitment_result == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE or the exact verifier-derived first technical-failure index is less than {role_index}"},
        {"left_path": f"instances.roles.{role}.pre_reveal_evidence.output_role", "right_path": f"constant.{role}", "condition": "role-qualified one-use allocation selects exactly this lifecycle role"},
        {"left_path": f"instances.roles.{role}.pre_reveal_evidence.completed_success_role_prefix_root_sha256", "right_path": computed_prefix, "condition": "allocation is legal only after the exact complete SUCCESS prefix and before this role"},
        {"left_path": f"instances.roles.{role}.lifecycle_refusal.refusal_boundary_role", "right_path": f"constant.{role}", "condition": "HIDDEN_LIFECYCLE_REFUSAL at this exact fixed boundary only"},
        {"left_path": f"instances.roles.{role}.lifecycle_refusal.refusal_boundary_role_index", "right_path": f"constant.UINT64_{role_index}", "condition": "HIDDEN_LIFECYCLE_REFUSAL boundary index is verifier-derived from fixed role order"},
        {"left_path": f"instances.roles.{role}.lifecycle_refusal.completed_success_role_prefix_root_sha256", "right_path": computed_prefix, "condition": "hidden refusal consumes the exact completed SUCCESS prefix"},
        {"left_path": f"instances.roles.{role}.failure_record.output_role", "right_path": f"constant.{role}", "condition": "branch boundary role is exact for role-terminal failure or hidden refusal; pre-output technical failure uses role zero"},
        {"left_path": f"instances.roles.{role}.failure_record.output_role", "right_path": f"instances.roles.{role}.lifecycle_refusal.refusal_boundary_role", "condition": "instances.roles.%s.failure_record.failure_trigger == HIDDEN_LIFECYCLE_REFUSAL; exact role-qualified failure record and zero-knowledge refusal evidence identify one boundary" % role},
        {"left_path": f"instances.roles.{role}.failure_record.failure_role_index", "right_path": f"constant.UINT64_{role_index}", "condition": "failure/refusal boundary index is verifier-derived from fixed role order"},
        {"left_path": f"instances.roles.{role}.failure_record.completed_success_role_prefix_root_sha256", "right_path": computed_prefix, "condition": "failure/refusal record binds exact completed SUCCESS prefix"},
        {"left_path": f"instances.roles.{role}.failure_record.cancelled_unreserved_role_count", "right_path": f"constant.UINT64_{len(role_lifecycle_order) - role_index - 1}", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; only roles after the consumed failed role remain unreserved"},
        {"left_path": f"instances.roles.{role}.failure_record.cancelled_unreserved_role_count", "right_path": f"constant.UINT64_{len(role_lifecycle_order) - role_index}", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL; refused boundary and every later role remain unreserved"},
        {"left_path": f"instances.roles.{role}.outcome.technical_health_result", "right_path": "constant.READY", "condition": f"{plan_path} == MATERIALIZE_SUCCESS"},
        {"left_path": f"instances.roles.{role}.anchor.technical_health_result", "right_path": "constant.READY", "condition": f"{plan_path} == MATERIALIZE_SUCCESS"},
        {"left_path": f"instances.roles.{role}.outcome.terminal_outcome", "right_path": "constant.SUCCESS", "condition": f"{plan_path} == MATERIALIZE_SUCCESS"},
        {"left_path": f"instances.roles.{role}.outcome.technical_health_result", "right_path": "constant.FIXED_TECHNICAL_FAILURE", "condition": f"{plan_path} == FIXED_ROLE_TECHNICAL_FAILURE and every earlier plan is MATERIALIZE_SUCCESS"},
        {"left_path": f"instances.roles.{role}.anchor.technical_health_result", "right_path": "constant.FIXED_TECHNICAL_FAILURE", "condition": f"{plan_path} == FIXED_ROLE_TECHNICAL_FAILURE and every earlier plan is MATERIALIZE_SUCCESS"},
        {"left_path": f"instances.roles.{role}.outcome.terminal_outcome", "right_path": "constant.FAILED", "condition": f"{plan_path} == FIXED_ROLE_TECHNICAL_FAILURE and every earlier plan is MATERIALIZE_SUCCESS"},
        {"left_path": f"instances.roles.{role}.failure_record.technical_health_result", "right_path": f"instances.roles.{role}.outcome.technical_health_result", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; exact first fixed role plan"},
    ])
generation_equality_rows.extend(role_index_derivation_rows)

# V7 role-qualified producer availability: each created role fixes one exact
# reservation/allocation/ledger-qualified commitment and authenticated result
# before reveal.  The sequence-wide health object supplies immutable profiles
# only; it is not a substitutable per-role result.
availability_tuple_source = {
    "namespace_precommitment_sha256": ("reservation", "namespace_precommitment_sha256"),
    "pinned_context_sha256": ("reservation", "pinned_context_sha256"),
    "singleton_registration_sha256": ("reservation", "singleton_registration_sha256"),
    "journal_id_token": ("reservation", "journal_id_token"),
    "journal_epoch": ("reservation", "journal_epoch"),
    "generation_sequence_transaction_claim_evidence_sha256": (None, "generation_sequence_transaction_claim_evidence_sha256"),
    "pre_witness_technical_health_evidence_sha256": (None, "pre_witness_technical_health_evidence_sha256"),
    "reserved_sequence": ("reservation", "reserved_next_sequence"),
    "output_role": ("reservation", "output_role"),
    "output_attempt_index": ("reservation", "attempt_index"),
    "public_beacon_pre_reveal_evidence_sha256": ("pre_reveal_evidence", "public_beacon_pre_reveal_evidence_sha256"),
    "beacon_allocation_slot_key_sha256": ("pre_reveal_evidence", "beacon_allocation_slot_key_sha256"),
    "post_public_beacon_pre_reveal_state_root_sha256": ("pre_reveal_evidence", "post_public_beacon_pre_reveal_state_root_sha256"),
    "post_public_beacon_pre_reveal_state_object_sha256": ("pre_reveal_evidence", "post_public_beacon_pre_reveal_state_object_sha256"),
    "post_public_beacon_pre_reveal_state_counter": ("pre_reveal_evidence", "post_public_beacon_pre_reveal_state_counter"),
    "public_round_index": ("reservation", "public_round_index"),
    "generation_reservation_sha256": ("reservation", "generation_reservation_sha256"),
    "reservation_slot_key_sha256": ("reservation", "reservation_slot_key_sha256"),
    "generation_reservation_ledger_evidence_sha256": ("ledger_evidence", "generation_reservation_ledger_evidence_sha256"),
    "post_reservation_ledger_state_root_sha256": ("ledger_evidence", "post_reservation_ledger_state_root_sha256"),
    "post_reservation_ledger_state_object_sha256": ("ledger_evidence", "post_reservation_ledger_state_object_sha256"),
    "post_reservation_ledger_counter": ("ledger_evidence", "post_reservation_ledger_counter"),
    "beacon_reservation_order_evidence_sha256": ("order", "beacon_reservation_order_evidence_sha256"),
}
for role_index, role in enumerate(role_lifecycle_order):
    plan_path = f"objects.pre_witness_technical_health_evidence.{role_terminalization_plan_fields[role_index]}"
    success_condition = f"{plan_path} == MATERIALIZE_SUCCESS and every earlier role completed SUCCESS and no HIDDEN_LIFECYCLE_REFUSAL exists at this role boundary"
    fixed_failure_condition = f"{plan_path} == FIXED_ROLE_TECHNICAL_FAILURE and every earlier role completed SUCCESS and no HIDDEN_LIFECYCLE_REFUSAL exists at this role boundary"
    created_condition = f"(({success_condition}) or ({fixed_failure_condition}))"
    commitment = f"instances.roles.{role}.availability_commitment"
    evidence = f"instances.roles.{role}.availability_evidence"
    for destination_field, (source_alias, source_field) in availability_tuple_source.items():
        if source_alias is None:
            source_path = ("objects.generation_sequence_transaction_claim_evidence.generation_sequence_transaction_claim_evidence_sha256"
                           if destination_field == "generation_sequence_transaction_claim_evidence_sha256"
                           else "objects.pre_witness_technical_health_evidence.pre_witness_technical_health_evidence_sha256")
        else:
            source_path = f"instances.roles.{role}.{source_alias}.{source_field}"
        generation_equality_rows.extend([
            {"left_path": source_path, "right_path": f"{commitment}.{destination_field}", "condition": f"{created_condition}; same-role availability commitment tuple"},
            {"left_path": source_path, "right_path": f"{evidence}.{destination_field}", "condition": f"{created_condition}; same-role availability evidence tuple"},
        ])
    generation_equality_rows.extend([
        {"left_path": f"{commitment}.role_lifecycle_index", "right_path": f"constant.UINT64_{role_index}", "condition": created_condition},
        {"left_path": f"{evidence}.role_lifecycle_index", "right_path": f"constant.UINT64_{role_index}", "condition": created_condition},
        {"left_path": f"{commitment}.role_producer_availability_commitment_sha256", "right_path": f"{evidence}.role_producer_availability_commitment_sha256", "condition": f"{created_condition}; evidence consumes the exact completed commitment"},
        {"left_path": f"{commitment}.producer_availability_observation_root_sha256", "right_path": f"{evidence}.producer_availability_observation_root_sha256", "condition": f"{created_condition}; observation is fixed before reveal"},
        {"left_path": f"{commitment}.producer_availability_result_root_sha256", "right_path": f"{evidence}.producer_availability_result_root_sha256", "condition": f"{created_condition}; result root is fixed before reveal"},
        {"left_path": f"{commitment}.committed_producer_availability_result", "right_path": f"{evidence}.producer_availability_result", "condition": f"{created_condition}; authenticated evidence cannot change committed result"},
        {"left_path": f"{evidence}.producer_availability_result", "right_path": "constant.NON_ABORTABLE_OUTPUT_MATERIALIZER_COMMITTED", "condition": success_condition},
        {"left_path": f"{evidence}.producer_availability_result", "right_path": "constant.FIXED_UNAVAILABLE", "condition": fixed_failure_condition},
        {"left_path": f"{evidence}.availability_verification_result", "right_path": "constant.VERIFIED_AS_COMMITTED", "condition": created_condition},
        {"left_path": f"{evidence}.output_generation_mode", "right_path": "constant.UNIQUE_DETERMINISTIC_BYTES", "condition": created_condition},
        {"left_path": f"{evidence}.output_attempt_index_for_evidence", "right_path": "constant.UINT64_ZERO", "condition": created_condition},
    ])
    for profile_field in [
        "producer_availability_predicate_sha256", "producer_availability_profile_sha256",
        "producer_availability_commitment_profile_sha256", "producer_availability_observation_profile_sha256",
        "producer_availability_result_profile_sha256", "producer_availability_authority_identity_sha256",
        "producer_availability_authentication_key_role",
    ]:
        context_path = f"objects.pinned_context.{profile_field}"
        for alias_path in [commitment, evidence]:
            generation_equality_rows.append({"left_path": f"{alias_path}.{profile_field}", "right_path": context_path, "condition": f"{created_condition}; exact namespace-precommitted availability pin"})
    for downstream_alias in ["reveal", "deadline", "outcome", "anchor"]:
        downstream = f"instances.roles.{role}.{downstream_alias}"
        generation_equality_rows.extend([
            {"left_path": f"{commitment}.role_producer_availability_commitment_sha256", "right_path": f"{downstream}.role_producer_availability_commitment_sha256", "condition": f"{created_condition}; downstream consumes exact same-role availability commitment"},
            {"left_path": f"{evidence}.role_producer_availability_evidence_sha256", "right_path": f"{downstream}.role_producer_availability_evidence_sha256", "condition": f"{created_condition}; downstream consumes exact same-role availability evidence"},
            {"left_path": f"{evidence}.producer_availability_result", "right_path": f"{downstream}.producer_availability_result", "condition": f"{created_condition}; downstream copies exact authenticated availability result"},
        ])
generation_equality_rows.extend([
    {"left_path": "instances.roles.SCOPE_PRECOMMITMENT_COMMITMENT_BYTES.failure_record.cancelled_unreserved_role_count", "right_path": f"constant.UINT64_{len(role_lifecycle_order)}", "condition": "failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE; all ten roles remain unreserved"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.generation_sequence_transaction_claim_evidence_sha256", "right_path": "objects.generation_sequence_lifecycle_refusal_evidence.generation_sequence_transaction_claim_evidence_sha256", "condition": "hidden refusal consumes the exact held sequence claim"},
    {"left_path": "objects.pre_witness_technical_health_evidence.pre_witness_technical_health_evidence_sha256", "right_path": "objects.generation_sequence_lifecycle_refusal_evidence.pre_witness_technical_health_evidence_sha256", "condition": "hidden refusal is produced only by the one pre-output committed total materializer"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence", "right_path": "objects.generation_sequence_lifecycle_refusal_evidence.reserved_sequence", "condition": "hidden refusal occupies the exact claimed sequence"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.fixed_role_lifecycle_order_root_sha256", "right_path": "objects.generation_sequence_lifecycle_refusal_evidence.fixed_role_lifecycle_order_root_sha256", "condition": "hidden refusal boundary is interpreted only under the fixed ten-role order"},
    {"left_path": "objects.pre_witness_technical_health_evidence.materialization_commitment_result", "right_path": "constant.PRE_OUTPUT_FIXED_TECHNICAL_FAILURE", "condition": "failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE"},
    {"left_path": "objects.pre_witness_technical_health_evidence.technical_health_result", "right_path": "constant.FIXED_TECHNICAL_FAILURE", "condition": "failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE"},
    {"left_path": "objects.pre_witness_technical_health_evidence.materialization_commitment_result", "right_path": "constant.COMPLETE_SEQUENCE_MATERIALIZATION_COMMITTED", "condition": "failure_trigger in {ROLE_TERMINAL_FAILED,HIDDEN_LIFECYCLE_REFUSAL} or normal all-SUCCESS path"},
    {"left_path": "objects.pre_witness_technical_health_evidence.technical_health_result", "right_path": "constant.READY", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL or normal all-SUCCESS path"},
])
doc["exact_role_boundary_index_and_cancellation_derivations"] = {
    "fixed_order": role_lifecycle_order,
    "rows": role_index_derivation_rows,
    "pre_output_failure_boundary_role": role_lifecycle_order[0],
    "pre_output_failure_boundary_index": 0,
    "index_or_cancel_count_caller_selected": False,
}
doc["pre_output_role_terminalization_plan_rules"] = {
    "plan_root_path": "objects.pre_witness_technical_health_evidence.role_terminalization_plan_root_sha256",
    "ordered_roles": role_lifecycle_order,
    "plan_field_paths": [f"objects.pre_witness_technical_health_evidence.{field}" for field in role_terminalization_plan_fields],
    "normal_branch": "all ten exact plan constants are MATERIALIZE_SUCCESS",
    "role_terminal_failure_branch": "the boundary role is the unique first FIXED_ROLE_TECHNICAL_FAILURE; every earlier role is MATERIALIZE_SUCCESS and every later role is exactly NOT_REACHED_AFTER_TERMINAL_BOUNDARY and is never allocated",
    "pre_output_failure_branch": "all ten exact plan constants are NOT_REACHED_AFTER_TERMINAL_BOUNDARY and no role allocation exists",
    "hidden_lifecycle_refusal_branch": "technical plans through the exact next boundary are MATERIALIZE_SUCCESS; the canonical private V19 closure/erasure relation alone proves that the next semantic lifecycle step cannot complete, fixes that boundary and emits one generic hiding refusal. The technical plan vector neither selects nor exposes a private predicate",
    "exact_verifier_function": "EvaluateRolePlanVectorExact under pre_witness_health_predicate_sha256 and pre_witness_health_profile_sha256 consumes the complete technical_health_input_vector_sha256 plus fixed ten-role order and returns exactly one canonical vector grammar above",
    "unused_suffix_plan_variant_allowed": False,
    "plan_is_content_independent_measured_and_committed_before_any_beacon_output": True,
    "post_output_plan_change_retry_or_second_failure_allowed": False,
}
doc["exact_uint64_constants_for_role_boundaries"] = {f"UINT64_{value}": value for value in range(len(role_lifecycle_order) + 1)}
doc["typed_instance_alias_rules"] = {
    "generic_schema_paths_are_type_selectors_only": True,
    "physical_equality_endpoints_must_resolve_one_exact_instance": True,
    "multi_instance_or_role_repeated_schema_path_is_never_a_physical_equality_endpoint": True,
}

generation_equality_rows.extend([
    {"left_path": "instances.current_pre_journal_state.state_kind", "right_path": "constant.REGISTERED_GENESIS", "condition": "authenticated selector origin is singleton_registration and its exact full-genesis bundle; the other two origins are absent"},
    {"left_path": "instances.current_pre_journal_state.state_kind", "right_path": "constant.NORMAL_MEMORY_RECORD_STATE", "condition": "authenticated selector origin is the independently current prior normal sequence commit; the genesis and failure origins are absent"},
    {"left_path": "instances.current_pre_journal_state.state_kind", "right_path": "constant.GENERATION_FAILURE_STATE", "condition": "authenticated selector origin is the independently current prior failure/refusal authority-head observation; the genesis and normal origins are absent"},
    {"left_path": "instances.current_pre_journal_state.journal_state_root_sha256", "right_path": "objects.genesis_state_authority_evidence.genesis_journal_state_root_sha256", "condition": "REGISTERED_GENESIS selector origin; singleton-registration-authenticated genesis authority fixes the exact journal root"},
    {"left_path": "instances.current_pre_journal_state.journal_state_object_sha256", "right_path": "objects.genesis_state_authority_evidence.genesis_journal_state_object_sha256", "condition": "REGISTERED_GENESIS selector origin; singleton-registration-authenticated genesis authority fixes the exact journal object"},
    {"left_path": "instances.current_pre_journal_state.committed_record_count", "right_path": "objects.genesis_state_authority_evidence.committed_record_count", "condition": "REGISTERED_GENESIS selector origin; exact count-zero authority tuple"},
    {"left_path": "instances.current_pre_journal_state.head_sequence", "right_path": "objects.genesis_state_authority_evidence.head_sequence", "condition": "REGISTERED_GENESIS selector origin; exact null head sequence"},
    {"left_path": "instances.current_pre_journal_state.head_receipt_hash_sha256", "right_path": "objects.genesis_state_authority_evidence.head_receipt_hash_sha256", "condition": "REGISTERED_GENESIS selector origin; exact null receipt head"},
    {"left_path": "instances.current_pre_journal_state.head_event_hash_sha256", "right_path": "objects.genesis_state_authority_evidence.head_event_hash_sha256", "condition": "REGISTERED_GENESIS selector origin; exact null event head"},
    {"left_path": "instances.current_pre_journal_state.consumed_receipt_token_root_sha256", "right_path": "objects.genesis_journal_state.consumed_receipt_token_root_sha256", "condition": "REGISTERED_GENESIS selector origin; exact registered empty receipt accumulator"},
    {"left_path": "instances.current_pre_journal_state.consumed_scope_token_root_sha256", "right_path": "objects.genesis_journal_state.consumed_scope_token_root_sha256", "condition": "REGISTERED_GENESIS selector origin; exact registered empty scope accumulator"},
    {"left_path": "instances.current_pre_journal_state.consumed_proof_token_root_sha256", "right_path": "objects.genesis_journal_state.consumed_proof_token_root_sha256", "condition": "REGISTERED_GENESIS selector origin; exact registered empty proof accumulator"},
    {"left_path": "instances.current_pre_journal_state.pinned_context_sha256", "right_path": "objects.genesis_state_authority_evidence.pinned_context_sha256", "condition": "REGISTERED_GENESIS selector origin; exact registered context"},
    {"left_path": "instances.current_pre_journal_state.singleton_registration_sha256", "right_path": "objects.singleton_registration.singleton_registration_sha256", "condition": "REGISTERED_GENESIS selector origin is authenticated only after the exact singleton registration exists"},
    {"left_path": "instances.current_pre_state_authority_evidence.state_authority_head_evidence_sha256", "right_path": "objects.genesis_state_authority_evidence.genesis_state_authority_head_evidence_sha256", "condition": "REGISTERED_GENESIS selector origin; exact authority head"},
    {"left_path": "instances.current_pre_state_authority_evidence.authority_monotonic_counter", "right_path": "objects.genesis_state_authority_evidence.authority_monotonic_counter", "condition": "REGISTERED_GENESIS selector origin; exact authority counter zero"},
    {"left_path": "instances.current_pre_external_anchor_evidence.external_anchor_root_sha256", "right_path": "objects.genesis_external_anchor_evidence.genesis_external_anchor_root_sha256", "condition": "REGISTERED_GENESIS selector origin; exact external-anchor root"},
    {"left_path": "instances.current_pre_external_anchor_evidence.anchor_monotonic_counter", "right_path": "objects.genesis_external_anchor_evidence.anchor_monotonic_counter", "condition": "REGISTERED_GENESIS selector origin; exact anchor counter zero"},
    {"left_path": "instances.current_pre_journal_state.journal_state_root_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.committed_post_state_root_sha256", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; independently current prior normal commit authenticates the exact journal root"},
    {"left_path": "instances.current_pre_journal_state.journal_state_object_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.committed_post_state_object_sha256", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; independently current prior normal commit authenticates the exact journal object"},
    {"left_path": "instances.current_pre_journal_state.committed_record_count", "right_path": "instances.prior_normal_sequence_claim_release_commit.committed_record_count", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; prior commit authenticates the exact record count"},
    {"left_path": "instances.current_pre_journal_state.head_sequence", "right_path": "instances.prior_normal_sequence_claim_release_commit.committed_head_sequence", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; prior commit authenticates the exact head sequence"},
    {"left_path": "instances.current_pre_journal_state.head_receipt_hash_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.committed_head_receipt_hash_sha256", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; prior commit authenticates the exact receipt head"},
    {"left_path": "instances.current_pre_journal_state.head_event_hash_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.committed_head_event_hash_sha256", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; prior commit authenticates the exact event head"},
    {"left_path": "instances.current_pre_state_authority_evidence.state_authority_head_evidence_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.post_state_authority_head_evidence_sha256", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; prior commit authenticates the exact authority head object"},
    {"left_path": "instances.current_pre_state_authority_evidence.authority_monotonic_counter", "right_path": "instances.prior_normal_sequence_claim_release_commit.post_state_authority_counter", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; prior commit authenticates the exact authority counter"},
    {"left_path": "instances.current_pre_external_anchor_evidence.external_anchor_root_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.post_external_anchor_root_sha256", "condition": "NORMAL_MEMORY_RECORD_STATE selector origin; prior commit authenticates the exact external-anchor object and its canonical counter-bearing preimage"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_root_sha256", "right_path": "instances.current_pre_journal_state.journal_state_root_sha256", "condition": "sequence claim locks the exact independently current journal pre-state"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_object_sha256", "right_path": "instances.current_pre_journal_state.journal_state_object_sha256", "condition": "sequence claim root and object resolve one exact pre-state instance"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind", "right_path": "instances.current_pre_journal_state.state_kind", "condition": "claim state kind is the exact typed current journal predecessor kind"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_record_count", "right_path": "instances.current_pre_journal_state.committed_record_count", "condition": "sequence claim binds exact current count"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_head_sequence", "right_path": "instances.current_pre_journal_state.head_sequence", "condition": "sequence claim binds exact current head sequence"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_head_receipt_hash_sha256", "right_path": "instances.current_pre_journal_state.head_receipt_hash_sha256", "condition": "sequence claim binds exact normal receipt head, failure sentinel, or genesis null"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_head_event_hash_sha256", "right_path": "instances.current_pre_journal_state.head_event_hash_sha256", "condition": "sequence claim binds exact normal event head, failure sentinel, or genesis null"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_state_authority_head_evidence_sha256", "right_path": "instances.current_pre_state_authority_evidence.state_authority_head_evidence_sha256", "condition": "claim locks exact genesis normal or failure authority head selected by the same state kind"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_state_authority_counter", "right_path": "instances.current_pre_state_authority_evidence.authority_monotonic_counter", "condition": "claim locks exact authority counter"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_root_sha256", "right_path": "instances.current_pre_external_anchor_evidence.external_anchor_root_sha256", "condition": "claim locks exact genesis normal or failure external-anchor root"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_counter", "right_path": "instances.current_pre_external_anchor_evidence.anchor_monotonic_counter", "condition": "claim locks exact external-anchor counter"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.failure_external_anchor_current_head_observation_sha256", "right_path": "constant.JSON_NULL", "condition": "authoritative_pre_state_kind in {REGISTERED_GENESIS,NORMAL_MEMORY_RECORD_STATE}; failure observation is absent"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.failure_state_authority_current_head_observation_sha256", "right_path": "constant.JSON_NULL", "condition": "authoritative_pre_state_kind in {REGISTERED_GENESIS,NORMAL_MEMORY_RECORD_STATE}; failure observation is absent"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.failure_external_anchor_current_head_observation_sha256", "right_path": "instances.current_failure_external_anchor_head_observation.failure_external_anchor_current_head_observation_sha256", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; exact independently current anchor observation"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.failure_state_authority_current_head_observation_sha256", "right_path": "instances.current_failure_state_authority_head_observation.failure_state_authority_current_head_observation_sha256", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; exact independently current authority observation"},
    {"left_path": "instances.current_failure_external_anchor_head_observation.failure_external_anchor_current_head_observation_sha256", "right_path": "instances.current_failure_state_authority_head_observation.failure_external_anchor_current_head_observation_sha256", "condition": "GENERATION_FAILURE_STATE only; selected authority observation consumes the same independently current anchor observation"},
    {"left_path": "instances.current_failure_external_anchor_head_observation.generation_failure_sequence_commit_evidence_sha256", "right_path": "instances.current_failure_state_authority_head_observation.generation_failure_sequence_commit_evidence_sha256", "condition": "GENERATION_FAILURE_STATE only; both observations authenticate one failure successor commit"},
    {"left_path": "instances.current_failure_external_anchor_head_observation.post_failure_external_anchor_root_sha256", "right_path": "instances.current_failure_state_authority_head_observation.post_failure_external_anchor_root_sha256", "condition": "GENERATION_FAILURE_STATE only; both observations authenticate one anchor root"},
    {"left_path": "instances.current_failure_external_anchor_head_observation.post_external_anchor_monotonic_counter", "right_path": "instances.current_failure_state_authority_head_observation.post_external_anchor_monotonic_counter", "condition": "GENERATION_FAILURE_STATE only; both observations authenticate one anchor counter"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_state_authority_counter", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_counter", "condition": "one current-state monotonic authority/anchor counter tuple"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence", "right_path": "constant.UINT64_ZERO", "condition": "current_pre_journal_state.state_kind == REGISTERED_GENESIS; first reserved sequence is exactly zero and no uint64 minus-one sentinel exists"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence", "right_path": "checked_plus_one(instances.current_pre_journal_state.head_sequence)", "condition": "current_pre_journal_state.state_kind in {NORMAL_MEMORY_RECORD_STATE, GENERATION_FAILURE_STATE}; checked uint64 increment with overflow refusal"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence", "right_path": "objects.generation_reservation.reserved_next_sequence", "condition": "every one of the ten role reservations is a subclaim at the one locked sequence; role alias expansion is exact"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_root_sha256", "right_path": "objects.generation_reservation.authoritative_pre_journal_state_root_sha256", "condition": "every role reservation uses the exact journal root locked before role zero"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_object_sha256", "right_path": "objects.generation_reservation.authoritative_pre_journal_state_object_sha256", "condition": "every role reservation uses the exact journal object locked before role zero"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind", "right_path": "objects.generation_reservation.authoritative_pre_state_kind", "condition": "every role reservation repeats the exact claim/current predecessor state kind"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_record_count", "right_path": "objects.generation_reservation.authoritative_pre_record_count", "condition": "every role reservation uses the exact journal count locked before role zero"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_head_sequence", "right_path": "objects.generation_reservation.authoritative_pre_head_sequence", "condition": "every role reservation uses the exact journal head locked before role zero"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_state_root_sha256", "right_path": "instances.sequence_claim_acquire_pre_state.generation_reservation_ledger_state_root_sha256", "condition": "claim acquisition pre root/object/counter resolve one exact ledger state"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_state_object_sha256", "right_path": "instances.sequence_claim_acquire_pre_state.generation_reservation_ledger_state_object_sha256", "condition": "claim acquisition pre root/object/counter resolve one exact ledger state"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_counter", "right_path": "instances.sequence_claim_acquire_pre_state.reservation_ledger_counter", "condition": "claim acquisition pre root/object/counter resolve one exact ledger state"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.post_reservation_ledger_state_root_sha256", "right_path": "instances.sequence_claim_acquire_post_state.generation_reservation_ledger_state_root_sha256", "condition": "claim acquisition post root/object/counter resolve one exact ledger state"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.post_reservation_ledger_state_object_sha256", "right_path": "instances.sequence_claim_acquire_post_state.generation_reservation_ledger_state_object_sha256", "condition": "claim acquisition post root/object/counter resolve one exact ledger state"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.post_reservation_ledger_counter", "right_path": "instances.sequence_claim_acquire_post_state.reservation_ledger_counter", "condition": "claim acquisition post root/object/counter resolve one exact ledger state"},
    {"left_path": "instances.sequence_claim_acquire_post_state.reservation_ledger_counter", "right_path": "checked_plus_one(instances.sequence_claim_acquire_pre_state.reservation_ledger_counter)", "condition": "atomic claim acquisition checked counter increment"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256", "right_path": "instances.sequence_claim_acquire_post_state.active_sequence_transaction_claim_slot_key_sha256", "condition": "claim post-state map carries exact acquired sequence slot"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256", "right_path": "instances.sequence_claim_acquire_post_state.active_sequence_transaction_claim_statement_sha256", "condition": "claim post-state map carries exact acyclic claim statement"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.post_sequence_transaction_claim_state", "right_path": "instances.sequence_claim_acquire_post_state.sequence_transaction_claim_state", "condition": "claim acquisition post-state is HELD_UNTIL_SEQUENCE_COMMIT"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_sequence_transaction_claim_state", "right_path": "instances.sequence_claim_acquire_pre_state.sequence_transaction_claim_state", "condition": "claim acquisition pre-state is exact registered UNCLAIMED base or prior RELEASED state"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.active_sequence_transaction_claim_slot_key_sha256", "right_path": "objects.pinned_context.generation_sequence_transaction_claim_empty_slot_key_sha256", "condition": "ledger counter zero only: exact empty sequence-claim slot sentinel"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.active_sequence_transaction_claim_statement_sha256", "right_path": "objects.pinned_context.generation_sequence_transaction_claim_empty_statement_sha256", "condition": "ledger counter zero only: exact empty sequence-claim statement sentinel"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.sequence_transaction_claim_state", "right_path": "constant.UNCLAIMED", "condition": "ledger counter zero only; positive acquisition pre-state instead equals the exact prior normal/failure release state"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.prior_reservation_ledger_head_evidence_sha256", "right_path": "constant.JSON_NULL", "condition": "pre_reservation_ledger_counter == 0 only; exact registered UNCLAIMED ledger base"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.prior_reservation_ledger_head_evidence_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.commit_evidence_sha256", "condition": "pre_reservation_ledger_counter > 0 and independently current predecessor is NORMAL_MEMORY_RECORD_STATE only"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.prior_reservation_ledger_head_evidence_sha256", "right_path": "instances.prior_failure_sequence_claim_release_commit.generation_failure_sequence_commit_evidence_sha256", "condition": "pre_reservation_ledger_counter > 0 and independently current predecessor is GENERATION_FAILURE_STATE only"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_state_root_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_state_root_sha256", "condition": "positive normal recursion only: prior normal release post root equals acquisition pre root"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_state_object_sha256", "right_path": "instances.prior_normal_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_state_object_sha256", "condition": "positive normal recursion only: prior normal release post object equals acquisition pre object"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_counter", "right_path": "instances.prior_normal_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_counter", "condition": "positive normal recursion only: prior normal release post counter equals acquisition pre counter"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_state_root_sha256", "right_path": "instances.prior_failure_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_state_root_sha256", "condition": "positive failure/refusal recursion only: prior release post root equals acquisition pre root"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_state_object_sha256", "right_path": "instances.prior_failure_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_state_object_sha256", "condition": "positive failure/refusal recursion only: prior release post object equals acquisition pre object"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_counter", "right_path": "instances.prior_failure_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_counter", "condition": "positive failure/refusal recursion only: prior release post counter equals acquisition pre counter"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.generation_reservation_ledger_state_root_sha256", "right_path": "instances.prior_normal_sequence_claim_release_state.generation_reservation_ledger_state_root_sha256", "condition": "positive normal recursion only; acquisition consumes exact typed prior RELEASED state"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.generation_reservation_ledger_state_object_sha256", "right_path": "instances.prior_normal_sequence_claim_release_state.generation_reservation_ledger_state_object_sha256", "condition": "positive normal recursion only; acquisition consumes exact typed prior RELEASED state"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.reservation_ledger_counter", "right_path": "instances.prior_normal_sequence_claim_release_state.reservation_ledger_counter", "condition": "positive normal recursion only; acquisition consumes exact typed prior RELEASED counter"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.generation_reservation_ledger_state_root_sha256", "right_path": "instances.prior_failure_sequence_claim_release_state.generation_reservation_ledger_state_root_sha256", "condition": "positive failure/refusal recursion only; acquisition consumes exact typed prior RELEASED state"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.generation_reservation_ledger_state_object_sha256", "right_path": "instances.prior_failure_sequence_claim_release_state.generation_reservation_ledger_state_object_sha256", "condition": "positive failure/refusal recursion only; acquisition consumes exact typed prior RELEASED state"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.reservation_ledger_counter", "right_path": "instances.prior_failure_sequence_claim_release_state.reservation_ledger_counter", "condition": "positive failure/refusal recursion only; acquisition consumes exact typed prior RELEASED counter"},
    {"left_path": "instances.prior_normal_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_state_root_sha256", "right_path": "instances.prior_normal_sequence_claim_release_state.generation_reservation_ledger_state_root_sha256", "condition": "prior normal commit hashes this exact RELEASED state root"},
    {"left_path": "instances.prior_normal_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_state_object_sha256", "right_path": "instances.prior_normal_sequence_claim_release_state.generation_reservation_ledger_state_object_sha256", "condition": "prior normal commit hashes this exact RELEASED state object"},
    {"left_path": "instances.prior_normal_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_counter", "right_path": "instances.prior_normal_sequence_claim_release_state.reservation_ledger_counter", "condition": "prior normal commit hashes this exact RELEASED state counter"},
    {"left_path": "instances.prior_failure_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_state_root_sha256", "right_path": "instances.prior_failure_sequence_claim_release_state.generation_reservation_ledger_state_root_sha256", "condition": "prior failure/refusal commit hashes this exact RELEASED state root"},
    {"left_path": "instances.prior_failure_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_state_object_sha256", "right_path": "instances.prior_failure_sequence_claim_release_state.generation_reservation_ledger_state_object_sha256", "condition": "prior failure/refusal commit hashes this exact RELEASED state object"},
    {"left_path": "instances.prior_failure_sequence_claim_release_commit.sequence_claim_post_reservation_ledger_counter", "right_path": "instances.prior_failure_sequence_claim_release_state.reservation_ledger_counter", "condition": "prior failure/refusal commit hashes this exact RELEASED state counter"},
    {"left_path": "instances.prior_normal_sequence_claim_release_commit.sequence_transaction_claim_slot_key_sha256", "right_path": "instances.prior_normal_sequence_claim_release_state.active_sequence_transaction_claim_slot_key_sha256", "condition": "prior normal commit and typed release state share exact claim slot history"},
    {"left_path": "instances.prior_normal_sequence_claim_release_commit.sequence_transaction_claim_statement_sha256", "right_path": "instances.prior_normal_sequence_claim_release_state.active_sequence_transaction_claim_statement_sha256", "condition": "prior normal commit and typed release state share exact claim statement history"},
    {"left_path": "instances.prior_failure_sequence_claim_release_commit.sequence_transaction_claim_slot_key_sha256", "right_path": "instances.prior_failure_sequence_claim_release_state.active_sequence_transaction_claim_slot_key_sha256", "condition": "prior failure/refusal commit and typed release state share exact claim slot history"},
    {"left_path": "instances.prior_failure_sequence_claim_release_commit.sequence_transaction_claim_statement_sha256", "right_path": "instances.prior_failure_sequence_claim_release_state.active_sequence_transaction_claim_statement_sha256", "condition": "prior failure/refusal commit and typed release state share exact claim statement history"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.sequence_transaction_claim_state", "right_path": "instances.prior_normal_sequence_claim_release_state.sequence_transaction_claim_state", "condition": "positive normal recursion only; exact RELEASED state"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.sequence_transaction_claim_state", "right_path": "instances.prior_failure_sequence_claim_release_state.sequence_transaction_claim_state", "condition": "positive failure/refusal recursion only; exact RELEASED state"},
    {"left_path": "instances.prior_normal_sequence_claim_release_state.sequence_transaction_claim_state", "right_path": "constant.RELEASED_BY_EXACT_SEQUENCE_COMMIT", "condition": "normal predecessor branch only"},
    {"left_path": "instances.prior_failure_sequence_claim_release_state.sequence_transaction_claim_state", "right_path": "constant.RELEASED_BY_EXACT_SEQUENCE_COMMIT", "condition": "failure/refusal predecessor branch only"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.active_sequence_transaction_claim_slot_key_sha256", "right_path": "instances.prior_normal_sequence_claim_release_state.active_sequence_transaction_claim_slot_key_sha256", "condition": "positive normal recursion preserves prior claim history"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.active_sequence_transaction_claim_statement_sha256", "right_path": "instances.prior_normal_sequence_claim_release_state.active_sequence_transaction_claim_statement_sha256", "condition": "positive normal recursion preserves prior claim history"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.active_sequence_transaction_claim_slot_key_sha256", "right_path": "instances.prior_failure_sequence_claim_release_state.active_sequence_transaction_claim_slot_key_sha256", "condition": "positive failure/refusal recursion preserves prior claim history"},
    {"left_path": "instances.sequence_claim_acquire_pre_state.active_sequence_transaction_claim_statement_sha256", "right_path": "instances.prior_failure_sequence_claim_release_state.active_sequence_transaction_claim_statement_sha256", "condition": "positive failure/refusal recursion preserves prior claim history"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence", "right_path": "checked_plus_one(instances.prior_normal_sequence_claim_release_commit.committed_head_sequence)", "condition": "positive normal recursion only; next claimed sequence follows exact prior committed sequence"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence", "right_path": "checked_plus_one(instances.prior_failure_sequence_claim_release_commit.post_head_sequence)", "condition": "positive failure/refusal recursion only; next claimed sequence follows exact prior consumed failure sequence"},
])

# Materialize the complete selector projection for every kind.  In particular,
# NORMAL resolves through a dedicated prior-transaction journal-state alias, so
# it can never collapse onto the later JOURNAL_STATE_STATE_NONCE target.
for state_kind, projection in instance_aliases["current_pre_journal_state"]["logical_field_projection_by_kind"].items():
    for selector_field, source_path in projection.items():
        if selector_field == "state_kind":
            continue
        generation_equality_rows.append({
            "left_path": f"instances.current_pre_journal_state.{selector_field}",
            "right_path": source_path,
            "condition": f"authenticated independently-current selector state_kind == {state_kind}; exact full journal projection",
        })

for state_field, commit_field in [
    ("journal_id_token", "journal_id_token"),
    ("journal_epoch", "journal_epoch"),
    ("journal_state_root_sha256", "committed_post_state_root_sha256"),
    ("journal_state_object_sha256", "committed_post_state_object_sha256"),
    ("committed_record_count", "committed_record_count"),
    ("head_sequence", "committed_head_sequence"),
    ("head_receipt_hash_sha256", "committed_head_receipt_hash_sha256"),
    ("head_event_hash_sha256", "committed_head_event_hash_sha256"),
    ("pinned_context_sha256", "pinned_context_sha256"),
    ("singleton_registration_sha256", "singleton_registration_sha256"),
]:
    generation_equality_rows.append({
        "left_path": f"instances.current_normal_journal_state.{state_field}",
        "right_path": f"instances.prior_normal_sequence_claim_release_commit.{commit_field}",
        "condition": "NORMAL_MEMORY_RECORD_STATE origin only; prior normal commit authenticates this exact prior-transaction journal-state field",
    })

for evidence_alias in ["current_pre_state_authority_evidence", "current_pre_external_anchor_evidence"]:
    for evidence_field, journal_field in [
        ("journal_state_root_sha256", "journal_state_root_sha256"),
        ("journal_state_object_sha256", "journal_state_object_sha256"),
        ("committed_record_count", "committed_record_count"),
        ("head_sequence", "head_sequence"),
        ("head_receipt_hash_sha256", "head_receipt_hash_sha256"),
        ("head_event_hash_sha256", "head_event_hash_sha256"),
    ]:
        generation_equality_rows.append({"left_path": f"instances.{evidence_alias}.{evidence_field}", "right_path": f"instances.current_pre_journal_state.{journal_field}", "condition": "exact registered-genesis normal or observed-failure current-head tuple; no mixed journal authority anchor instances"})
generation_equality_rows.extend([
    {"left_path": "instances.current_pre_state_authority_evidence.external_anchor_root_sha256", "right_path": "instances.current_pre_external_anchor_evidence.external_anchor_root_sha256", "condition": "authority head and anchor current-head evidence resolve one exact anchor root"},
    {"left_path": "instances.current_pre_state_authority_evidence.authority_monotonic_counter", "right_path": "instances.current_pre_external_anchor_evidence.state_authority_monotonic_counter", "condition": "authority and anchor evidence resolve one exact authority counter"},
])
for observation_alias in ["current_failure_external_anchor_head_observation", "current_failure_state_authority_head_observation"]:
    generation_equality_rows.append({"left_path": f"instances.{observation_alias}.generation_failure_sequence_commit_evidence_sha256", "right_path": "instances.current_failure_sequence_commit.generation_failure_sequence_commit_evidence_sha256", "condition": "GENERATION_FAILURE_STATE only; independently current observation authenticates the exact completed failure/refusal commit"})
    for field in [
        "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256",
        "journal_id_token", "journal_epoch", "generation_failure_record_sha256", "failure_trigger", "post_failure_state_root_sha256",
        "post_failure_state_object_sha256", "post_record_count", "post_head_sequence",
        "post_head_receipt_hash_sha256", "post_head_event_hash_sha256",
        "post_failure_external_anchor_root_sha256", "post_external_anchor_monotonic_counter",
    ]:
        generation_equality_rows.append({"left_path": f"instances.{observation_alias}.{field}", "right_path": f"instances.current_failure_sequence_commit.{field}", "condition": "GENERATION_FAILURE_STATE only; observation and selected commit share one exact successor tuple"})
for field in ["post_failure_state_authority_head_evidence_sha256", "post_state_authority_monotonic_counter"]:
    generation_equality_rows.append({"left_path": f"instances.current_failure_state_authority_head_observation.{field}", "right_path": f"instances.current_failure_sequence_commit.{field}", "condition": "GENERATION_FAILURE_STATE only; authority observation authenticates exact successor head/counter"})
for commit_field, state_field in [
    ("post_failure_state_root_sha256", "generation_failure_journal_state_root_sha256"),
    ("post_failure_state_object_sha256", "generation_failure_journal_state_object_sha256"),
    ("post_record_count", "committed_record_count"),
    ("post_head_sequence", "head_sequence"),
    ("post_head_receipt_hash_sha256", "head_receipt_hash_sha256"),
    ("post_head_event_hash_sha256", "head_event_hash_sha256"),
]:
    generation_equality_rows.append({"left_path": f"instances.current_failure_sequence_commit.{commit_field}", "right_path": f"instances.current_failure_journal_state.{state_field}", "condition": "GENERATION_FAILURE_STATE only; selected completed commit hashes the exact current failure journal state"})
for observation_field, journal_field in [
    ("post_failure_state_root_sha256", "journal_state_root_sha256"),
    ("post_failure_state_object_sha256", "journal_state_object_sha256"),
    ("post_record_count", "committed_record_count"),
    ("post_head_sequence", "head_sequence"),
    ("post_head_receipt_hash_sha256", "head_receipt_hash_sha256"),
    ("post_head_event_hash_sha256", "head_event_hash_sha256"),
]:
    generation_equality_rows.append({"left_path": f"instances.current_failure_state_authority_head_observation.{observation_field}", "right_path": f"instances.current_pre_journal_state.{journal_field}", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; the prior-sequence authority observation physically projects the complete current failure journal tuple"})
generation_equality_rows.extend([
    {"left_path": "instances.current_failure_record.generation_failure_record_sha256", "right_path": "instances.current_failure_sequence_commit.generation_failure_record_sha256", "condition": "GENERATION_FAILURE_STATE only; selected prior commit names the exact typed failure/refusal record"},
    {"left_path": "instances.current_failure_record.generation_failure_record_sha256", "right_path": "instances.current_failure_journal_state.generation_failure_record_sha256", "condition": "GENERATION_FAILURE_STATE only; selected prior failure journal state consumes the exact typed record"},
    {"left_path": "instances.current_failure_record.failure_trigger", "right_path": "instances.current_failure_sequence_commit.failure_trigger", "condition": "GENERATION_FAILURE_STATE only; record and selected prior commit use one exact mutually exclusive branch"},
    {"left_path": "instances.current_failure_sequence_commit.post_head_sequence", "right_path": "instances.current_failure_record.reserved_sequence", "condition": "GENERATION_FAILURE_STATE only; prior failure/refusal record occupies exactly the current failure head sequence"},
    {"left_path": "instances.current_failure_state_authority_head_observation.post_failure_state_authority_head_evidence_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_state_authority_head_evidence_sha256", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; claim consumes the exact independently observed prior-sequence authority head"},
    {"left_path": "instances.current_failure_state_authority_head_observation.post_state_authority_monotonic_counter", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_state_authority_counter", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; claim consumes the exact independently observed prior-sequence authority counter"},
    {"left_path": "instances.current_failure_state_authority_head_observation.post_failure_external_anchor_root_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_root_sha256", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; claim consumes the exact independently observed prior-sequence anchor root"},
    {"left_path": "instances.current_failure_state_authority_head_observation.post_external_anchor_monotonic_counter", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_counter", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; claim consumes the exact independently observed prior-sequence anchor counter"},
    {"left_path": "instances.current_failure_external_anchor_head_observation.post_failure_external_anchor_root_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_root_sha256", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; both typed prior-sequence observations close the identical claim anchor root"},
    {"left_path": "instances.current_failure_external_anchor_head_observation.post_external_anchor_monotonic_counter", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_counter", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; both typed prior-sequence observations close the identical claim anchor counter"},
    {"left_path": "instances.current_failure_sequence_commit.generation_failure_sequence_commit_evidence_sha256", "right_path": "instances.prior_failure_sequence_claim_release_commit.generation_failure_sequence_commit_evidence_sha256", "condition": "authoritative_pre_state_kind == GENERATION_FAILURE_STATE; current journal authority anchor observations and positive claim-ledger handoff resolve the same prior failure/refusal commit"},
])
for invariant_field in ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch"]:
    generation_equality_rows.extend([
        {"left_path": f"instances.current_failure_record.{invariant_field}", "right_path": f"instances.current_failure_sequence_commit.{invariant_field}", "condition": "GENERATION_FAILURE_STATE only; prior record and commit repeat one exact immutable transaction identity"},
        {"left_path": f"instances.current_failure_sequence_commit.{invariant_field}", "right_path": f"instances.current_failure_journal_state.{invariant_field}", "condition": "GENERATION_FAILURE_STATE only; the typed current failure journal state repeats the exact prior record/commit identity"},
    ])
for observation_alias in ["current_failure_external_anchor_head_observation", "current_failure_state_authority_head_observation"]:
    generation_equality_rows.extend([
        {"left_path": f"instances.{observation_alias}.generation_failure_record_sha256", "right_path": "instances.current_failure_record.generation_failure_record_sha256", "condition": "GENERATION_FAILURE_STATE only; prior-sequence observation authenticates the exact typed failure/refusal record"},
        {"left_path": f"instances.{observation_alias}.failure_trigger", "right_path": "instances.current_failure_record.failure_trigger", "condition": "GENERATION_FAILURE_STATE only; prior-sequence observation repeats the record's exact branch"},
        {"left_path": f"instances.{observation_alias}.failure_role", "right_path": "instances.current_failure_record.output_role", "condition": "GENERATION_FAILURE_STATE only; prior-sequence observation repeats the exact failure/refusal boundary role"},
        {"left_path": f"instances.{observation_alias}.failure_role_index", "right_path": "instances.current_failure_record.failure_role_index", "condition": "GENERATION_FAILURE_STATE only; prior-sequence observation repeats the exact role index"},
        {"left_path": f"instances.{observation_alias}.reserved_sequence", "right_path": "instances.current_failure_record.reserved_sequence", "condition": "GENERATION_FAILURE_STATE only; prior-sequence observation repeats the exact occupied sequence"},
    ])
for role in role_lifecycle_order:
    for ledger_alias in ["ledger_pre_state", "ledger_reserved_state", "ledger_consumed_state"]:
        generation_equality_rows.extend([
            {"left_path": f"instances.roles.{role}.{ledger_alias}.active_sequence_transaction_claim_slot_key_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256", "condition": f"{role} role-slot transition preserves the sequence-wide claim slot"},
            {"left_path": f"instances.roles.{role}.{ledger_alias}.active_sequence_transaction_claim_statement_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256", "condition": f"{role} role-slot transition preserves the sequence-wide claim statement"},
            {"left_path": f"instances.roles.{role}.{ledger_alias}.sequence_transaction_claim_state", "right_path": "constant.HELD_UNTIL_SEQUENCE_COMMIT", "condition": f"{role} reservation and terminal consumption cannot release the journal sequence claim"},
        ])

# The normal path releases from the final COMMIT role consumed ledger state.
for left_field, alias_field in [
    ("sequence_claim_pre_reservation_ledger_state_root_sha256", "generation_reservation_ledger_state_root_sha256"),
    ("sequence_claim_pre_reservation_ledger_state_object_sha256", "generation_reservation_ledger_state_object_sha256"),
    ("sequence_claim_pre_reservation_ledger_counter", "reservation_ledger_counter"),
]:
    generation_equality_rows.append({"left_path": f"objects.commit_evidence.{left_field}", "right_path": f"instances.roles.COMMIT_EVIDENCE_COMMIT_NONCE.ledger_consumed_state.{alias_field}", "condition": "normal release pre-state is exact final role consumed ledger state; claim remained held through all ten roles"})
for left_field, alias_field in [
    ("sequence_claim_post_reservation_ledger_state_root_sha256", "generation_reservation_ledger_state_root_sha256"),
    ("sequence_claim_post_reservation_ledger_state_object_sha256", "generation_reservation_ledger_state_object_sha256"),
    ("sequence_claim_post_reservation_ledger_counter", "reservation_ledger_counter"),
]:
    generation_equality_rows.append({"left_path": f"objects.commit_evidence.{left_field}", "right_path": f"instances.sequence_claim_normal_release_post_state.{alias_field}", "condition": "normal journal CAS and claim release produce one exact ledger post-state"})
generation_equality_rows.extend([
    {"left_path": "objects.commit_evidence.generation_sequence_transaction_claim_evidence_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.generation_sequence_transaction_claim_evidence_sha256", "condition": "normal commit releases the exact sequence claim acquired before role zero"},
    {"left_path": "objects.commit_evidence.sequence_transaction_claim_slot_key_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256", "condition": "normal release uses exact claim slot"},
    {"left_path": "objects.commit_evidence.sequence_transaction_claim_statement_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256", "condition": "normal release uses exact claim statement"},
    {"left_path": "objects.commit_evidence.pre_sequence_transaction_claim_state", "right_path": "constant.HELD_UNTIL_SEQUENCE_COMMIT", "condition": "normal commit alone observes held pre-state"},
    {"left_path": "objects.commit_evidence.post_sequence_transaction_claim_state", "right_path": "constant.RELEASED_BY_EXACT_SEQUENCE_COMMIT", "condition": "normal commit atomically releases after all ten SUCCESS anchors"},
    {"left_path": "objects.commit_evidence.sequence_claim_post_reservation_ledger_counter", "right_path": "checked_plus_one(objects.commit_evidence.sequence_claim_pre_reservation_ledger_counter)", "condition": "normal release checked ledger counter increment"},
    {"left_path": "instances.sequence_claim_normal_release_post_state.active_sequence_transaction_claim_slot_key_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256", "condition": "released state retains exact immutable claim slot history"},
    {"left_path": "instances.sequence_claim_normal_release_post_state.active_sequence_transaction_claim_statement_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256", "condition": "released state retains exact immutable claim statement history"},
    {"left_path": "instances.sequence_claim_normal_release_post_state.sequence_transaction_claim_state", "right_path": "constant.RELEASED_BY_EXACT_SEQUENCE_COMMIT", "condition": "normal post-state is released only with journal commit"},
])
def selected_failure_release_condition(role):
    terminal = f"failure_trigger == ROLE_TERMINAL_FAILED and output_role == {role}"
    refusal = f"failure_trigger == HIDDEN_LIFECYCLE_REFUSAL and refusal_boundary_role == {role}"
    pre_output = ("failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE"
                  if role == role_lifecycle_order[0] else "false")
    return f"(({terminal}) or ({refusal}) or ({pre_output}))"

for role in role_lifecycle_order:
    selected_release = selected_failure_release_condition(role)
    terminal_release = f"failure_trigger == ROLE_TERMINAL_FAILED and output_role == {role}"
    unreserved_release = f"(failure_trigger == HIDDEN_LIFECYCLE_REFUSAL and refusal_boundary_role == {role})"
    if role == role_lifecycle_order[0]:
        unreserved_release += " or failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE"
    for left_field, alias_field in [
        ("sequence_claim_pre_reservation_ledger_state_root_sha256", "generation_reservation_ledger_state_root_sha256"),
        ("sequence_claim_pre_reservation_ledger_state_object_sha256", "generation_reservation_ledger_state_object_sha256"),
        ("sequence_claim_pre_reservation_ledger_counter", "reservation_ledger_counter"),
    ]:
        generation_equality_rows.append({"left_path": f"instances.roles.{role}.failure_commit.{left_field}", "right_path": f"instances.roles.{role}.ledger_consumed_state.{alias_field}", "condition": f"{terminal_release}; terminal failure release pre-state is the exact consumed role-slot state with claim still held"})
        generation_equality_rows.append({"left_path": f"instances.roles.{role}.failure_commit.{left_field}", "right_path": f"instances.roles.{role}.ledger_pre_state.{alias_field}", "condition": f"{unreserved_release}; hidden refusal or role-zero pre-output failure uses the exact never-reserved ledger pre-state with claim still held"})
    for left_field, alias_field in [
        ("sequence_claim_post_reservation_ledger_state_root_sha256", "generation_reservation_ledger_state_root_sha256"),
        ("sequence_claim_post_reservation_ledger_state_object_sha256", "generation_reservation_ledger_state_object_sha256"),
        ("sequence_claim_post_reservation_ledger_counter", "reservation_ledger_counter"),
    ]:
        generation_equality_rows.append({"left_path": f"instances.roles.{role}.failure_commit.{left_field}", "right_path": f"instances.roles.{role}.sequence_claim_failure_release_post_state.{alias_field}", "condition": f"{selected_release}; the same atomic selected failure/refusal CAS produces the exact released ledger post-state"})
    generation_equality_rows.extend([
        {"left_path": f"instances.roles.{role}.failure_commit.generation_sequence_transaction_claim_evidence_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.generation_sequence_transaction_claim_evidence_sha256", "condition": f"{selected_release}; selected failure/refusal commit releases the one acquired sequence claim"},
        {"left_path": f"instances.roles.{role}.failure_commit.sequence_transaction_claim_slot_key_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256", "condition": f"{selected_release}; release uses exact claim slot"},
        {"left_path": f"instances.roles.{role}.failure_commit.sequence_transaction_claim_statement_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256", "condition": f"{selected_release}; release uses exact claim statement"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_sequence_transaction_claim_state", "right_path": "constant.HELD_UNTIL_SEQUENCE_COMMIT", "condition": f"{selected_release}; no role anchor or refusal evidence released the claim early"},
        {"left_path": f"instances.roles.{role}.failure_commit.post_sequence_transaction_claim_state", "right_path": "constant.RELEASED_BY_EXACT_SEQUENCE_COMMIT", "condition": f"{selected_release}; the same failure/refusal journal CAS releases claim"},
        {"left_path": f"instances.roles.{role}.failure_commit.sequence_claim_post_reservation_ledger_counter", "right_path": f"checked_plus_one(instances.roles.{role}.failure_commit.sequence_claim_pre_reservation_ledger_counter)", "condition": f"{selected_release}; release counter advances exactly once"},
        {"left_path": f"instances.roles.{role}.sequence_claim_failure_release_post_state.active_sequence_transaction_claim_slot_key_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_slot_key_sha256", "condition": f"{selected_release}; released state retains exact immutable claim slot"},
        {"left_path": f"instances.roles.{role}.sequence_claim_failure_release_post_state.active_sequence_transaction_claim_statement_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.sequence_transaction_claim_statement_sha256", "condition": f"{selected_release}; released state retains exact immutable claim statement"},
        {"left_path": f"instances.roles.{role}.sequence_claim_failure_release_post_state.sequence_transaction_claim_state", "right_path": "constant.RELEASED_BY_EXACT_SEQUENCE_COMMIT", "condition": f"{selected_release}; post-state releases claim only with same journal authority anchor CAS"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_journal_state_root_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_root_sha256", "condition": f"{role} failure CAS consumes the exact sequence-claim journal root"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_journal_state_object_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_journal_state_object_sha256", "condition": f"{role} failure CAS consumes the exact sequence-claim journal object"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_state_kind", "right_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind", "condition": f"{role} failure CAS consumes the exact typed predecessor kind"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_record_count", "right_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_record_count", "condition": f"{role} failure CAS consumes the exact sequence-claim count"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_head_sequence", "right_path": "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_head_sequence", "condition": f"{role} failure CAS consumes the exact sequence-claim head"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_state_authority_head_evidence_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_state_authority_head_evidence_sha256", "condition": f"{role} failure CAS consumes the exact locked authority head"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_state_authority_monotonic_counter", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_state_authority_counter", "condition": f"{role} failure CAS consumes the exact locked authority counter"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_external_anchor_root_sha256", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_root_sha256", "condition": f"{role} failure CAS consumes the exact locked anchor root"},
        {"left_path": f"instances.roles.{role}.failure_commit.pre_external_anchor_monotonic_counter", "right_path": "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_counter", "condition": f"{role} failure CAS consumes the exact locked anchor counter"},
        {"left_path": f"instances.roles.{role}.failure_commit.post_state_kind", "right_path": "constant.GENERATION_FAILURE_STATE", "condition": f"{role} failure CAS creates only the typed failure journal state"},
        {"left_path": f"instances.roles.{role}.failure_commit.post_head_receipt_hash_sha256", "right_path": f"instances.roles.{role}.failure_state.head_receipt_hash_sha256", "condition": f"{role} failure authority/anchor successors authenticate the exact failure-state receipt sentinel"},
        {"left_path": f"instances.roles.{role}.failure_commit.post_head_event_hash_sha256", "right_path": f"instances.roles.{role}.failure_state.head_event_hash_sha256", "condition": f"{role} failure authority/anchor successors authenticate the exact failure-state event sentinel"},
    ])

claim_ledger_state_invariant_sources = {
    "namespace_precommitment_sha256": "objects.pinned_context.namespace_precommitment_sha256",
    "pinned_context_sha256": "objects.pinned_context.pinned_context_sha256",
    "singleton_registration_sha256": "objects.singleton_registration.singleton_registration_sha256",
    "reservation_ledger_authority_identity_sha256": "objects.pinned_context.reservation_ledger_authority_identity_sha256",
    "reservation_ledger_cas_no_fork_profile_sha256": "objects.pinned_context.reservation_ledger_cas_no_fork_profile_sha256",
    "generation_reservation_ledger_genesis_manifest_sha256": "objects.pinned_context.generation_reservation_ledger_genesis_manifest_sha256",
}
claim_ledger_aliases = [
    "instances.sequence_claim_acquire_pre_state",
    "instances.sequence_claim_acquire_post_state",
    "instances.sequence_claim_normal_release_post_state",
    "instances.prior_normal_sequence_claim_release_state",
    "instances.prior_failure_sequence_claim_release_state",
] + [f"instances.roles.{role}.sequence_claim_failure_release_post_state" for role in role_lifecycle_order]
for alias_path in claim_ledger_aliases:
    for field, source_path in claim_ledger_state_invariant_sources.items():
        generation_equality_rows.append({"left_path": f"{alias_path}.{field}", "right_path": source_path, "condition": "claim acquisition/release state is one exact invariant-bound reservation-ledger instance"})

# Positive sequence-claim recurrence is a literal typed-state handoff, not a
# transitive coincidence through common pins.  Both mutually exclusive prior
# release kinds directly propagate every immutable reservation-ledger field
# into the next acquisition pre-state.
for prior_release_alias, branch_condition in [
    ("instances.prior_normal_sequence_claim_release_state", "positive normal recursion only; exact prior normal RELEASED state supplies the next acquisition pre-state"),
    ("instances.prior_failure_sequence_claim_release_state", "positive failure/refusal recursion only; exact prior failure/refusal RELEASED state supplies the next acquisition pre-state"),
]:
    for invariant_field in claim_ledger_state_invariant_sources:
        generation_equality_rows.append({
            "left_path": f"{prior_release_alias}.{invariant_field}",
            "right_path": f"instances.sequence_claim_acquire_pre_state.{invariant_field}",
            "condition": branch_condition,
        })

registry_equality_rows.extend([
    {"left_path": "objects.global_registry_post_head.previous_head_sha256", "right_path": "instances.global_registry_pre_state.registry_head_sha256", "condition": "post head consumes the sole independently current authoritative prior head"},
    {"left_path": "objects.global_registry_post_state.previous_head_sha256", "right_path": "instances.global_registry_pre_state.registry_head_sha256", "condition": "post state repeats the same authoritative prior head"},
    {"left_path": "instances.global_registry_pre_state.schema", "right_path": "constant.kira.mind.continuity.v21.singleton_registry.authoritative_pre_state.v1", "condition": "registry_counter == 0 only; exact V7 authoritative pre-state schema constant"},
    {"left_path": "instances.global_registry_pre_state.hash_domain", "right_path": "constant.KIRA_MIND_V21_SINGLETON_REGISTRY_AUTHORITATIVE_PRE_STATE_SHA256_V1", "condition": "registry_counter == 0 only; exact V7 authoritative pre-state hash domain"},
    {"left_path": "instances.global_registry_pre_state.predecessor_singleton_registration_sha256", "right_path": "objects.pinned_context.global_registry_genesis_predecessor_singleton_registration_sha256", "condition": "registry_counter == 0 only; exact pinned predecessor-registration sentinel"},
    {"left_path": "instances.global_registry_pre_state.predecessor_registry_post_state_sha256", "right_path": "objects.pinned_context.global_registry_genesis_predecessor_registry_post_state_sentinel_sha256", "condition": "registry_counter == 0 only; exact NO_PREDECESSOR_REGISTRY_POST_STATE sentinel"},
    {"left_path": "instances.global_registry_pre_state.namespace_precommitment_root_sha256", "right_path": "objects.pinned_context.global_registry_genesis_predecessor_namespace_precommitment_sha256", "condition": "registry_counter == 0 only; exact pinned genesis namespace sentinel"},
    {"left_path": "instances.global_registry_pre_state.pinned_context_root_sha256", "right_path": "objects.pinned_context.global_registry_genesis_predecessor_pinned_context_sha256", "condition": "registry_counter == 0 only; exact pinned genesis context sentinel"},
    {"left_path": "instances.global_registry_pre_state.registry_root_sha256", "right_path": "objects.pinned_context.global_registry_empty_map_root_sha256", "condition": "registry_counter == 0 only; exact pinned empty registry map"},
    {"left_path": "instances.global_registry_pre_state.registry_counter", "right_path": "constant.UINT64_ZERO", "condition": "counter-zero base only"},
    {"left_path": "instances.global_registry_pre_state.registry_head_sha256", "right_path": "objects.pinned_context.global_registry_genesis_head_sha256", "condition": "registry_counter == 0 only; exact pinned genesis head"},
    {"left_path": "instances.global_registry_pre_state.pre_state_sha256", "right_path": "objects.pinned_context.global_registry_genesis_state_object_sha256", "condition": "registry_counter == 0 only; canonical typed pre-state bytes equal the exact pinned genesis object"},
    {"left_path": "instances.global_registry_pre_state.schema", "right_path": "instances.prior_authoritative_registry_pre_state.schema", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state schema"},
    {"left_path": "instances.global_registry_pre_state.hash_domain", "right_path": "instances.prior_authoritative_registry_pre_state.hash_domain", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state hash domain"},
    {"left_path": "instances.global_registry_pre_state.predecessor_singleton_registration_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.predecessor_singleton_registration_sha256", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state"},
    {"left_path": "instances.global_registry_pre_state.predecessor_registry_post_state_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.predecessor_registry_post_state_sha256", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state"},
    {"left_path": "instances.global_registry_pre_state.namespace_precommitment_root_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.namespace_precommitment_root_sha256", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state"},
    {"left_path": "instances.global_registry_pre_state.pinned_context_root_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.pinned_context_root_sha256", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state"},
    {"left_path": "instances.global_registry_pre_state.registry_root_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.registry_root_sha256", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state"},
    {"left_path": "instances.global_registry_pre_state.registry_counter", "right_path": "instances.prior_authoritative_registry_pre_state.registry_counter", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state"},
    {"left_path": "instances.global_registry_pre_state.registry_head_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.registry_head_sha256", "condition": "registry_counter > 0 only; byte-identical prior authoritative pre-state"},
    {"left_path": "instances.global_registry_pre_state.pre_state_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.pre_state_sha256", "condition": "registry_counter > 0 only; exact prior authoritative pre-state object hash"},
    {"left_path": "instances.prior_authoritative_registry_pre_state.predecessor_singleton_registration_sha256", "right_path": "instances.prior_global_registry_singleton_registration.singleton_registration_sha256", "condition": "positive recursion: prior typed pre-state names its exact predecessor registration"},
    {"left_path": "instances.prior_authoritative_registry_pre_state.predecessor_registry_post_state_sha256", "right_path": "instances.prior_global_registry_post_state.global_registry_post_state_sha256", "condition": "positive recursion: prior typed pre-state names its exact predecessor post-state"},
    {"left_path": "instances.prior_global_registry_completed_request.singleton_registration_request_sha256", "right_path": "instances.prior_global_registry_sparse_map_update.singleton_registration_request_sha256", "condition": "positive recursion: the prior sparse-map update consumes the exact prior completed signed request"},
    {"left_path": "instances.prior_global_registry_completed_request.singleton_registration_request_sha256", "right_path": "instances.prior_global_registry_post_head.singleton_registration_request_sha256", "condition": "positive recursion: the prior post head authenticates the exact prior completed signed request"},
    {"left_path": "instances.prior_global_registry_completed_request.singleton_registration_request_sha256", "right_path": "instances.prior_global_registry_post_state.singleton_registration_request_sha256", "condition": "positive recursion: the prior typed post state authenticates the exact prior completed signed request"},
    {"left_path": "instances.prior_global_registry_completed_request.singleton_registration_request_sha256", "right_path": "instances.prior_global_registry_singleton_registration.singleton_registration_request_sha256", "condition": "positive recursion: the prior final registration consumes the exact prior completed signed request"},
    {"left_path": "instances.prior_global_registry_sparse_map_update.global_registry_sparse_map_update_sha256", "right_path": "instances.prior_global_registry_post_head.global_registry_sparse_map_update_sha256", "condition": "positive recursion: the prior post head authenticates the exact prior sparse-map update"},
    {"left_path": "instances.prior_global_registry_sparse_map_update.global_registry_sparse_map_update_sha256", "right_path": "instances.prior_global_registry_post_state.global_registry_sparse_map_update_sha256", "condition": "positive recursion: the prior typed post state authenticates the exact prior sparse-map update"},
    {"left_path": "instances.prior_global_registry_sparse_map_update.global_registry_sparse_map_update_sha256", "right_path": "instances.prior_global_registry_singleton_registration.global_registry_sparse_map_update_sha256", "condition": "positive recursion: the prior final registration consumes the exact prior sparse-map update"},
    {"left_path": "instances.prior_global_registry_post_head.global_registry_post_head_sha256", "right_path": "instances.prior_global_registry_post_state.global_registry_post_head_sha256", "condition": "positive recursion: the prior typed post state consumes the exact prior post head"},
    {"left_path": "instances.prior_global_registry_post_head.global_registry_post_head_sha256", "right_path": "instances.prior_global_registry_singleton_registration.global_registry_post_head_sha256", "condition": "positive recursion: the prior final registration consumes the exact prior post head"},
    {"left_path": "instances.prior_global_registry_post_state.global_registry_post_state_sha256", "right_path": "instances.prior_global_registry_singleton_registration.global_registry_post_state_sha256", "condition": "positive recursion: the prior final registration consumes the exact prior typed post state"},
    {"left_path": "instances.prior_global_registry_completed_request.namespace_precommitment_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.namespace_precommitment_root_sha256", "condition": "literal V7 positive origin: prior completed request supplies the authoritative prior namespace root"},
    {"left_path": "instances.prior_global_registry_completed_request.pinned_context_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.pinned_context_root_sha256", "condition": "literal V7 positive origin: prior completed request supplies the authoritative prior context root"},
    {"left_path": "instances.prior_global_registry_sparse_map_update.registry_post_root_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.registry_root_sha256", "condition": "literal V7 positive origin: prior verified sparse-map update supplies the authoritative prior registry root"},
    {"left_path": "instances.prior_global_registry_sparse_map_update.registry_counter_after", "right_path": "instances.prior_authoritative_registry_pre_state.registry_counter", "condition": "literal V7 positive origin: prior verified sparse-map update supplies the authoritative prior registry counter"},
    {"left_path": "instances.prior_global_registry_post_head.global_registry_post_head_sha256", "right_path": "instances.prior_authoritative_registry_pre_state.registry_head_sha256", "condition": "literal V7 positive origin: prior typed post head supplies the authoritative prior registry head"},
    {"left_path": "instances.prior_authoritative_registry_pre_state.namespace_precommitment_root_sha256", "right_path": "instances.prior_global_registry_post_state.namespace_precommitment_sha256", "condition": "positive recursion: prior typed pre-state repeats predecessor namespace"},
    {"left_path": "instances.prior_authoritative_registry_pre_state.pinned_context_root_sha256", "right_path": "instances.prior_global_registry_post_state.pinned_context_sha256", "condition": "positive recursion: prior typed pre-state repeats predecessor context"},
    {"left_path": "instances.prior_authoritative_registry_pre_state.registry_root_sha256", "right_path": "instances.prior_global_registry_post_state.registry_post_root_sha256", "condition": "positive recursion: prior typed pre-state repeats predecessor registry root"},
    {"left_path": "instances.prior_authoritative_registry_pre_state.registry_counter", "right_path": "instances.prior_global_registry_post_state.registry_counter_after", "condition": "positive recursion: prior typed pre-state repeats predecessor counter"},
    {"left_path": "instances.prior_authoritative_registry_pre_state.registry_head_sha256", "right_path": "instances.prior_global_registry_post_state.global_registry_post_head_sha256", "condition": "positive recursion: prior typed pre-state repeats predecessor head"},
    {"left_path": "instances.next_global_registry_pre_state.predecessor_singleton_registration_sha256", "right_path": "objects.singleton_registration.singleton_registration_sha256", "condition": "the final registration must exist before the next authoritative pre-state"},
    {"left_path": "instances.next_global_registry_pre_state.predecessor_registry_post_state_sha256", "right_path": "objects.global_registry_post_state.global_registry_post_state_sha256", "condition": "next pre-state consumes exact typed post-state"},
    {"left_path": "instances.next_global_registry_pre_state.namespace_precommitment_root_sha256", "right_path": "objects.singleton_registration.namespace_precommitment_sha256", "condition": "next pre-state repeats predecessor registration namespace"},
    {"left_path": "instances.next_global_registry_pre_state.pinned_context_root_sha256", "right_path": "objects.singleton_registration.pinned_context_sha256", "condition": "next pre-state repeats predecessor registration context"},
    {"left_path": "instances.next_global_registry_pre_state.registry_root_sha256", "right_path": "objects.global_registry_sparse_map_update.registry_post_root_sha256", "condition": "verified update exposes exactly one next authoritative registry root"},
    {"left_path": "instances.next_global_registry_pre_state.registry_counter", "right_path": "objects.global_registry_sparse_map_update.registry_counter_after", "condition": "verified update exposes exactly one next authoritative registry counter"},
    {"left_path": "instances.next_global_registry_pre_state.registry_head_sha256", "right_path": "objects.global_registry_post_head.global_registry_post_head_sha256", "condition": "typed post head is the sole next authoritative registry head"},
    {"left_path": "objects.global_registry_sparse_map_update.registry_counter_after", "right_path": "checked_plus_one(instances.global_registry_pre_state.registry_counter)", "condition": "uint64 checked registry increment with overflow refusal"},
])

for alias_field, pin_field, exact_sha256, exact_preimage in [
    ("predecessor_singleton_registration_sha256", "global_registry_genesis_predecessor_singleton_registration_sha256", "a9ef0b38c7c96de55fdb782760c1eaa807d06cf7f9d4011c801012b95374d0e5", "ASCII(KIRA_MIND_V21_NO_PREDECESSOR_SINGLETON_REGISTRATION_SHA256_V1)"),
    ("predecessor_registry_post_state_sha256", "global_registry_genesis_predecessor_registry_post_state_sentinel_sha256", "9a0f2ed7f4ece44d95d0c4d5dae875a45a956b2e40ebcf1208f67af91a2d2be7", "ASCII(KIRA_MIND_V21_NO_PREDECESSOR_REGISTRY_POST_STATE_SHA256_V1)"),
    ("namespace_precommitment_root_sha256", "global_registry_genesis_predecessor_namespace_precommitment_sha256", "0f4b6856f230bc1456f406ceee2f296e3a82472cfc36752009df49f6ab285d53", "ASCII(KIRA_MIND_V21_GENESIS_NAMESPACE_PRECOMMITMENT_ROOT_SHA256_V1)"),
    ("pinned_context_root_sha256", "global_registry_genesis_predecessor_pinned_context_sha256", "1b50fdb9ac726131845e37008e1a4dd0353ff84ae48ec60c3d4971dcd0cb9f9f", "ASCII(KIRA_MIND_V21_GENESIS_PINNED_CONTEXT_ROOT_SHA256_V1)"),
    ("registry_root_sha256", "global_registry_empty_map_root_sha256", "ec9eb96692c1477547fc66fbbeba4fccacf906946b4a01c7dbbeb8ca863a5d21", "ASCII(KIRA_MIND_V21_SINGLETON_REGISTRY_EMPTY_ROOT_SHA256_V1)"),
    ("registry_head_sha256", "global_registry_genesis_head_sha256", "e4186b36fc8fbc6838724764d832bcb670d2d641aeadf8e95e4652e3eb663a75", "ASCII(KIRA_MIND_V21_SINGLETON_REGISTRY_GENESIS_HEAD_SHA256_V1)"),
    ("pre_state_sha256", "global_registry_genesis_state_object_sha256", "eba033b3e9052c1e6783fadea5b7f734c824060d588ee3b4d70b5eb90f8d637a", "SHA256(exact canonical 787-byte counter-zero authoritative_registry_pre_state object)"),
]:
    exact_constant_path = f"constant.sha256.{exact_sha256}"
    registry_equality_rows.extend([
        {"left_path": f"instances.global_registry_pre_state.{alias_field}", "right_path": exact_constant_path, "condition": f"registry_counter == 0 only; exact finite-cardinality-one V7 genesis derivation {exact_preimage}"},
        {"left_path": f"objects.pinned_context.{pin_field}", "right_path": exact_constant_path, "condition": f"outer/context pin is not variable: verifier recomputes exact V7 genesis derivation {exact_preimage}"},
    ])

generation_equality_rows.extend([
    {"left_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_state_root_sha256", "right_path": "instances.reservation_ledger_pre_state.generation_reservation_ledger_state_root_sha256", "condition": "pre root and object resolve to same typed ledger state"},
    {"left_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_state_object_sha256", "right_path": "instances.reservation_ledger_pre_state.generation_reservation_ledger_state_object_sha256", "condition": "pre root and object resolve to same typed ledger state"},
    {"left_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_counter", "right_path": "instances.reservation_ledger_pre_state.reservation_ledger_counter", "condition": "pre counter equals same typed ledger state"},
    {"left_path": "objects.generation_reservation_ledger_evidence.post_reservation_ledger_state_root_sha256", "right_path": "instances.reservation_ledger_reserved_state.generation_reservation_ledger_state_root_sha256", "condition": "reserved post root and object resolve to same typed ledger state"},
    {"left_path": "objects.generation_reservation_ledger_evidence.post_reservation_ledger_state_object_sha256", "right_path": "instances.reservation_ledger_reserved_state.generation_reservation_ledger_state_object_sha256", "condition": "reserved post root and object resolve to same typed ledger state"},
    {"left_path": "objects.generation_reservation_ledger_evidence.post_reservation_ledger_counter", "right_path": "instances.reservation_ledger_reserved_state.reservation_ledger_counter", "condition": "reserved post counter equals same typed ledger state"},
    {"left_path": "instances.reservation_ledger_reserved_state.reservation_ledger_counter", "right_path": "checked_plus_one(instances.reservation_ledger_pre_state.reservation_ledger_counter)", "condition": "reservation CAS checked increment"},
    {"left_path": "objects.generation_terminal_anchor_evidence.post_reservation_ledger_state_root_sha256", "right_path": "instances.reservation_ledger_consumed_state.generation_reservation_ledger_state_root_sha256", "condition": "consumed post root and object resolve to same typed ledger state"},
    {"left_path": "objects.generation_terminal_anchor_evidence.post_reservation_ledger_state_object_sha256", "right_path": "instances.reservation_ledger_consumed_state.generation_reservation_ledger_state_object_sha256", "condition": "consumed post root and object resolve to same typed ledger state"},
    {"left_path": "objects.generation_terminal_anchor_evidence.post_reservation_ledger_counter", "right_path": "instances.reservation_ledger_consumed_state.reservation_ledger_counter", "condition": "consumed post counter equals same typed ledger state"},
    {"left_path": "instances.reservation_ledger_consumed_state.reservation_ledger_counter", "right_path": "checked_plus_one(instances.reservation_ledger_reserved_state.reservation_ledger_counter)", "condition": "terminal CAS checked increment"},
    {"left_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_state_root_sha256", "right_path": "resolved(objects.generation_reservation_ledger_evidence.prior_reservation_ledger_head_evidence_sha256).post_reservation_ledger_state_root_sha256", "condition": "positive recursion: prior terminal head post equals current reservation pre"},
    {"left_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_state_object_sha256", "right_path": "resolved(objects.generation_reservation_ledger_evidence.prior_reservation_ledger_head_evidence_sha256).post_reservation_ledger_state_object_sha256", "condition": "positive recursion: prior terminal head post equals current reservation pre"},
    {"left_path": "objects.generation_reservation_ledger_evidence.pre_reservation_ledger_counter", "right_path": "resolved(objects.generation_reservation_ledger_evidence.prior_reservation_ledger_head_evidence_sha256).post_reservation_ledger_counter", "condition": "positive recursion: prior terminal head post equals current reservation pre"},
    {"left_path": "instances.reservation_ledger_pre_state.reservation_ledger_map_root_sha256", "right_path": "objects.pinned_context.generation_reservation_ledger_empty_map_root_sha256", "condition": "counter zero only; exact registered empty ledger map"},
])

generation_equality_rows.extend([
    {"left_path": "objects.public_beacon_pre_reveal_evidence.pre_public_beacon_pre_reveal_state_root_sha256", "right_path": "instances.public_beacon_pre_reveal_pre_state.public_beacon_pre_reveal_state_root_sha256", "condition": "pre root/object/counter same typed beacon state"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.pre_public_beacon_pre_reveal_state_object_sha256", "right_path": "instances.public_beacon_pre_reveal_pre_state.public_beacon_pre_reveal_state_object_sha256", "condition": "pre root/object/counter same typed beacon state"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.pre_public_beacon_pre_reveal_state_counter", "right_path": "instances.public_beacon_pre_reveal_pre_state.public_beacon_pre_reveal_state_counter", "condition": "pre root/object/counter same typed beacon state"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.pre_beacon_allocation_map_root_sha256", "right_path": "instances.public_beacon_pre_reveal_pre_state.beacon_allocation_map_root_sha256", "condition": "pre evidence and state resolve one exact allocation map"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.post_public_beacon_pre_reveal_state_root_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_root_sha256", "condition": "post root/object/counter same typed beacon state"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.post_public_beacon_pre_reveal_state_object_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_object_sha256", "condition": "post root/object/counter same typed beacon state"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.post_public_beacon_pre_reveal_state_counter", "right_path": "instances.public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_counter", "condition": "post root/object/counter same typed beacon state"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.post_beacon_allocation_map_root_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.beacon_allocation_map_root_sha256", "condition": "post evidence and state resolve one exact allocation map"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.public_beacon_pre_reveal_head_counter", "right_path": "instances.public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_counter", "condition": "head counter is exact authenticated post state counter"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.committed_future_round_index", "right_path": "instances.public_beacon_pre_reveal_post_state.committed_future_round_index", "condition": "evidence signs exactly the future round stored in the hashed post-state instance"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.committed_round_output_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.committed_round_output_sha256", "condition": "evidence signs exactly the future VRF output hash stored in the hashed post-state instance"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.beacon_reveal_state", "right_path": "instances.public_beacon_pre_reveal_post_state.beacon_reveal_state", "condition": "evidence and hashed post state are exactly PRE_REVEAL"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.public_round_beacon_identity_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.public_round_beacon_identity_sha256", "condition": "beacon identity invariant across the exact hashed post state and evidence"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.public_round_beacon_profile_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.public_round_beacon_profile_sha256", "condition": "beacon profile invariant across the exact hashed post state and evidence"},
    {"left_path": "objects.public_beacon_pre_reveal_evidence.fixed_reveal_schedule_profile_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.fixed_reveal_schedule_profile_sha256", "condition": "schedule invariant across the exact hashed post state and evidence"},
    {"left_path": "instances.public_beacon_pre_reveal_pre_state.public_round_beacon_identity_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.public_round_beacon_identity_sha256", "condition": "pre to post transition preserves fixed beacon identity"},
    {"left_path": "instances.public_beacon_pre_reveal_pre_state.public_round_beacon_profile_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.public_round_beacon_profile_sha256", "condition": "pre to post transition preserves fixed beacon profile"},
    {"left_path": "instances.public_beacon_pre_reveal_pre_state.fixed_reveal_schedule_profile_sha256", "right_path": "instances.public_beacon_pre_reveal_post_state.fixed_reveal_schedule_profile_sha256", "condition": "pre to post transition preserves fixed reveal schedule"},
    {"left_path": "instances.public_beacon_pre_reveal_pre_state.beacon_reveal_state", "right_path": "constant.PRE_REVEAL", "condition": "pre state is exact PRE_REVEAL current head"},
    {"left_path": "instances.public_beacon_pre_reveal_pre_state.committed_future_round_index", "right_path": "constant.UINT64_ZERO", "condition": "actual pre-state public_beacon_pre_reveal_state_counter == 0 only: exact registered allocation cursor base"},
    {"left_path": "instances.public_beacon_pre_reveal_pre_state.beacon_allocation_map_root_sha256", "right_path": "objects.pinned_context.public_beacon_allocation_empty_map_root_sha256", "condition": "actual pre-state public_beacon_pre_reveal_state_counter == 0 only: exact registered empty allocation map"},
    {"left_path": "instances.public_beacon_pre_reveal_pre_state.committed_round_output_sha256", "right_path": "objects.pinned_context.public_beacon_counter_zero_output_sentinel_sha256", "condition": "actual pre-state public_beacon_pre_reveal_state_counter == 0 only: exact no-round output sentinel"},
    {"left_path": "instances.public_beacon_pre_reveal_post_state.beacon_reveal_state", "right_path": "constant.PRE_REVEAL", "condition": "post state remains PRE_REVEAL until separate reveal evidence"},
    {"left_path": "instances.public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_counter", "right_path": "checked_plus_one(instances.public_beacon_pre_reveal_pre_state.public_beacon_pre_reveal_state_counter)", "condition": "pre-reveal CAS checked increment"},
    {"left_path": "instances.public_beacon_pre_reveal_post_state.committed_future_round_index", "right_path": "checked_plus_one(instances.public_beacon_pre_reveal_pre_state.committed_future_round_index)", "condition": "fixed demand-driven beacon schedule allocates the exact strictly next unused future unrevealed generation round; checked uint64 overflow refuses"},
])

for pre_field, reservation_field in {
    "reserved_sequence": "reserved_next_sequence",
    "output_role": "output_role",
    "output_generation_mode_for_allocation": "output_generation_mode",
    "output_attempt_index_for_allocation": "attempt_index",
    "message_or_statement_root_sha256": "message_or_statement_root_sha256",
    "reservation_slot_key_sha256": "reservation_slot_key_sha256",
    "beacon_allocation_slot_key_sha256": "beacon_allocation_slot_key_sha256",
    "public_beacon_pre_reveal_head_counter": "public_beacon_pre_reveal_head_counter",
    "committed_future_round_index": "public_round_index",
    "public_beacon_output_recovery_commitment_sha256": "public_beacon_output_recovery_commitment_sha256",
}.items():
    generation_equality_rows.append({"left_path": f"objects.public_beacon_pre_reveal_evidence.{pre_field}", "right_path": f"objects.generation_reservation.{reservation_field}", "condition": "one-use pre-reveal allocation and later reservation share the exact registration/epoch/sequence/role/attempt/slot/message/round tuple"})

first_role = role_lifecycle_order[0]
generation_equality_rows.extend([
    {"left_path": "instances.current_public_beacon_pre_reveal_state.prior_evidence_sha256", "right_path": "constant.JSON_NULL", "condition": "actual current beacon state counter == 0 iff exact registered counter-zero base"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_root_sha256", "right_path": "instances.public_beacon_counter_zero_state.public_beacon_pre_reveal_state_root_sha256", "condition": "actual current beacon state counter == 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_object_sha256", "right_path": "instances.public_beacon_counter_zero_state.public_beacon_pre_reveal_state_object_sha256", "condition": "actual current beacon state counter == 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_counter", "right_path": "instances.public_beacon_counter_zero_state.public_beacon_pre_reveal_state_counter", "condition": "actual current beacon state counter == 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.beacon_allocation_map_root_sha256", "right_path": "instances.public_beacon_counter_zero_state.beacon_allocation_map_root_sha256", "condition": "actual current beacon state counter == 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.committed_future_round_index", "right_path": "instances.public_beacon_counter_zero_state.committed_future_round_index", "condition": "actual current beacon state counter == 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.committed_round_output_sha256", "right_path": "instances.public_beacon_counter_zero_state.committed_round_output_sha256", "condition": "actual current beacon state counter == 0 only"},
    {"left_path": "instances.public_beacon_counter_zero_state.public_beacon_pre_reveal_state_counter", "right_path": "constant.UINT64_ZERO", "condition": "exact registered beacon base"},
    {"left_path": "instances.public_beacon_counter_zero_state.committed_future_round_index", "right_path": "constant.UINT64_ZERO", "condition": "exact registered beacon base"},
    {"left_path": "instances.public_beacon_counter_zero_state.beacon_allocation_map_root_sha256", "right_path": "objects.pinned_context.public_beacon_allocation_empty_map_root_sha256", "condition": "exact registered beacon base"},
    {"left_path": "instances.public_beacon_counter_zero_state.committed_round_output_sha256", "right_path": "objects.pinned_context.public_beacon_counter_zero_output_sentinel_sha256", "condition": "exact registered beacon base"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.prior_evidence_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_evidence.public_beacon_pre_reveal_evidence_sha256", "condition": "actual current beacon state counter > 0 only; exact independently current prior-sequence evidence"},
    {"left_path": "instances.prior_sequence_public_beacon_pre_reveal_evidence.post_public_beacon_pre_reveal_state_root_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_root_sha256", "condition": "positive recursion: prior evidence authenticates exact post-state root"},
    {"left_path": "instances.prior_sequence_public_beacon_pre_reveal_evidence.post_public_beacon_pre_reveal_state_object_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_object_sha256", "condition": "positive recursion: prior evidence authenticates exact post-state object"},
    {"left_path": "instances.prior_sequence_public_beacon_pre_reveal_evidence.post_public_beacon_pre_reveal_state_counter", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_counter", "condition": "positive recursion: prior evidence authenticates exact post-state counter"},
    {"left_path": "instances.prior_sequence_public_beacon_pre_reveal_evidence.post_beacon_allocation_map_root_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.beacon_allocation_map_root_sha256", "condition": "positive recursion: prior evidence authenticates exact post allocation map"},
    {"left_path": "instances.prior_sequence_public_beacon_pre_reveal_evidence.committed_future_round_index", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.committed_future_round_index", "condition": "positive recursion: prior evidence authenticates exact allocation cursor"},
    {"left_path": "instances.prior_sequence_public_beacon_pre_reveal_evidence.committed_round_output_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.committed_round_output_sha256", "condition": "positive recursion: prior evidence authenticates exact output commitment"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_root_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_root_sha256", "condition": "actual current beacon state counter > 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_object_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_object_sha256", "condition": "actual current beacon state counter > 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_counter", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_counter", "condition": "actual current beacon state counter > 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.beacon_allocation_map_root_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.beacon_allocation_map_root_sha256", "condition": "actual current beacon state counter > 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.committed_future_round_index", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.committed_future_round_index", "condition": "actual current beacon state counter > 0 only"},
    {"left_path": "instances.current_public_beacon_pre_reveal_state.committed_round_output_sha256", "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.committed_round_output_sha256", "condition": "actual current beacon state counter > 0 only"},
    {"left_path": f"instances.roles.{first_role}.pre_reveal_evidence.prior_public_beacon_pre_reveal_evidence_sha256", "right_path": "instances.current_public_beacon_pre_reveal_state.prior_evidence_sha256", "condition": "role zero uses null only for the exact beacon base or the exact independently current prior head self hash"},
    {"left_path": f"instances.roles.{first_role}.beacon_pre_state.public_beacon_pre_reveal_state_root_sha256", "right_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_root_sha256", "condition": "role zero consumes exact independently current counter-zero or positive-recursive beacon state"},
    {"left_path": f"instances.roles.{first_role}.beacon_pre_state.public_beacon_pre_reveal_state_object_sha256", "right_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_object_sha256", "condition": "role zero consumes exact independently current beacon object"},
    {"left_path": f"instances.roles.{first_role}.beacon_pre_state.public_beacon_pre_reveal_state_counter", "right_path": "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_counter", "condition": "role zero consumes exact independently current beacon counter"},
    {"left_path": f"instances.roles.{first_role}.beacon_pre_state.beacon_allocation_map_root_sha256", "right_path": "instances.current_public_beacon_pre_reveal_state.beacon_allocation_map_root_sha256", "condition": "role zero consumes exact independently current allocation map"},
    {"left_path": f"instances.roles.{first_role}.beacon_pre_state.committed_future_round_index", "right_path": "instances.current_public_beacon_pre_reveal_state.committed_future_round_index", "condition": "role zero consumes exact current allocation cursor"},
    {"left_path": f"instances.roles.{first_role}.beacon_pre_state.committed_round_output_sha256", "right_path": "instances.current_public_beacon_pre_reveal_state.committed_round_output_sha256", "condition": "role zero consumes exact current prior output commitment or base sentinel"},
    {"left_path": f"instances.roles.{first_role}.beacon_pre_state.beacon_reveal_state", "right_path": "instances.current_public_beacon_pre_reveal_state.beacon_reveal_state", "condition": "role zero consumes exact PRE_REVEAL current state"},
])

beacon_state_invariant_sources = {
    "namespace_precommitment_sha256": "objects.pinned_context.namespace_precommitment_sha256",
    "pinned_context_sha256": "objects.pinned_context.pinned_context_sha256",
    "singleton_registration_sha256": "objects.singleton_registration.singleton_registration_sha256",
    "journal_id_token": "objects.pinned_context.journal_id_token",
    "journal_epoch": "objects.pinned_context.journal_epoch",
    "public_round_beacon_identity_sha256": "objects.pinned_context.public_round_beacon_identity_sha256",
    "public_round_beacon_profile_sha256": "objects.pinned_context.public_round_beacon_profile_sha256",
    "fixed_reveal_schedule_profile_sha256": "objects.pinned_context.fixed_reveal_schedule_profile_sha256",
    "public_beacon_pre_reveal_genesis_manifest_sha256": "objects.pinned_context.public_beacon_pre_reveal_genesis_manifest_sha256",
    "beacon_reveal_state": "constant.PRE_REVEAL",
}
for invariant_field, pinned_source in beacon_state_invariant_sources.items():
    generation_equality_rows.extend([
        {"left_path": f"instances.public_beacon_counter_zero_state.{invariant_field}", "right_path": pinned_source, "condition": "counter-zero beacon base has the exact registration identity profile schedule manifest and PRE_REVEAL invariant"},
        {"left_path": f"instances.current_public_beacon_pre_reveal_state.{invariant_field}", "right_path": f"instances.public_beacon_counter_zero_state.{invariant_field}", "condition": "actual current beacon state counter == 0 only; full invariant tuple comes from the exact registered base"},
        {"left_path": f"instances.prior_sequence_public_beacon_pre_reveal_evidence.{invariant_field}", "right_path": f"instances.prior_sequence_public_beacon_pre_reveal_post_state.{invariant_field}", "condition": "positive recursion: prior evidence authenticates the exact full invariant tuple of its typed post-state"},
        {"left_path": f"instances.current_public_beacon_pre_reveal_state.{invariant_field}", "right_path": f"instances.prior_sequence_public_beacon_pre_reveal_post_state.{invariant_field}", "condition": "actual current beacon state counter > 0 only; full invariant tuple comes from the exact prior authenticated post-state"},
        {"left_path": f"instances.roles.{first_role}.beacon_pre_state.{invariant_field}", "right_path": f"instances.current_public_beacon_pre_reveal_state.{invariant_field}", "condition": "role zero consumes the complete invariant tuple of the exclusive counter-zero or positive current beacon state"},
    ])
generation_equality_rows.append({
    "left_path": "instances.prior_sequence_public_beacon_pre_reveal_evidence.public_beacon_pre_reveal_head_counter",
    "right_path": "instances.prior_sequence_public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_counter",
    "condition": "positive recursion: the prior evidence head counter equals the exact typed post-state counter",
})
for role_index, role in enumerate(role_lifecycle_order):
    if role_index == 0:
        continue
    prior_role = role_lifecycle_order[role_index - 1]
    generation_equality_rows.extend([
        {"left_path": f"instances.roles.{role}.pre_reveal_evidence.prior_public_beacon_pre_reveal_evidence_sha256", "right_path": f"instances.roles.{prior_role}.pre_reveal_evidence.public_beacon_pre_reveal_evidence_sha256", "condition": f"{role} allocation consumes exactly the immediately preceding lifecycle role beacon head"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.public_beacon_pre_reveal_state_root_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.public_beacon_pre_reveal_state_root_sha256", "condition": f"{role} pre state is exactly {prior_role} post state"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.public_beacon_pre_reveal_state_object_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.public_beacon_pre_reveal_state_object_sha256", "condition": f"{role} pre object is exactly {prior_role} post object"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.public_beacon_pre_reveal_state_counter", "right_path": f"instances.roles.{prior_role}.beacon_post_state.public_beacon_pre_reveal_state_counter", "condition": f"{role} pre counter is exactly {prior_role} post counter"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.beacon_allocation_map_root_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.beacon_allocation_map_root_sha256", "condition": f"{role} pre allocation map is exactly {prior_role} post allocation map"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.committed_future_round_index", "right_path": f"instances.roles.{prior_role}.beacon_post_state.committed_future_round_index", "condition": f"{role} allocation cursor is exactly {prior_role} post cursor"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.committed_round_output_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.committed_round_output_sha256", "condition": f"{role} consumes the exact prior committed output hash without selection"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.beacon_reveal_state", "right_path": f"instances.roles.{prior_role}.beacon_post_state.beacon_reveal_state", "condition": f"{role} consumes the exact PRE_REVEAL prior state"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.public_round_beacon_identity_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.public_round_beacon_identity_sha256", "condition": f"{role} preserves exact beacon identity"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.public_round_beacon_profile_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.public_round_beacon_profile_sha256", "condition": f"{role} preserves exact beacon profile"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.fixed_reveal_schedule_profile_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.fixed_reveal_schedule_profile_sha256", "condition": f"{role} preserves exact reveal schedule"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.namespace_precommitment_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.namespace_precommitment_sha256", "condition": f"{role} preserves exact namespace"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.pinned_context_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.pinned_context_sha256", "condition": f"{role} preserves exact context"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.singleton_registration_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.singleton_registration_sha256", "condition": f"{role} preserves exact singleton registration"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.journal_id_token", "right_path": f"instances.roles.{prior_role}.beacon_post_state.journal_id_token", "condition": f"{role} preserves exact journal identifier"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.journal_epoch", "right_path": f"instances.roles.{prior_role}.beacon_post_state.journal_epoch", "condition": f"{role} preserves exact epoch"},
        {"left_path": f"instances.roles.{role}.beacon_pre_state.public_beacon_pre_reveal_genesis_manifest_sha256", "right_path": f"instances.roles.{prior_role}.beacon_post_state.public_beacon_pre_reveal_genesis_manifest_sha256", "condition": f"{role} preserves exact beacon genesis manifest"},
    ])

for role in role_lifecycle_order:
    for invariant_field in beacon_state_invariant_sources:
        generation_equality_rows.extend([
            {"left_path": f"instances.roles.{role}.pre_reveal_evidence.{invariant_field}", "right_path": f"instances.roles.{role}.beacon_pre_state.{invariant_field}", "condition": f"{role} evidence authenticates the exact full pre-state invariant tuple"},
            {"left_path": f"instances.roles.{role}.pre_reveal_evidence.{invariant_field}", "right_path": f"instances.roles.{role}.beacon_post_state.{invariant_field}", "condition": f"{role} evidence authenticates the exact full post-state invariant tuple"},
            {"left_path": f"instances.roles.{role}.beacon_pre_state.{invariant_field}", "right_path": f"instances.roles.{role}.beacon_post_state.{invariant_field}", "condition": f"{role} atomic beacon CAS preserves the complete invariant tuple"},
        ])

for right_object in ["public_beacon_reveal_evidence", "terminal_deadline_observation_evidence"]:
    for field in ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch"]:
        generation_equality_rows.append({"left_path": f"objects.generation_reservation.{field}", "right_path": f"objects.{right_object}.{field}", "condition": "same immutable registered transaction identity"})
for right_object in ["public_beacon_reveal_evidence", "terminal_deadline_observation_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation.generation_reservation_sha256", "right_path": f"objects.{right_object}.generation_reservation_sha256", "condition": "same signed reservation"})
    generation_equality_rows.append({"left_path": "objects.generation_reservation_ledger_evidence.generation_reservation_ledger_evidence_sha256", "right_path": f"objects.{right_object}.generation_reservation_ledger_evidence_sha256", "condition": "same authoritative ledger reservation"})
generation_equality_rows.extend([
    {"left_path": "objects.public_beacon_pre_reveal_evidence.committed_round_output_sha256", "right_path": "objects.public_beacon_reveal_evidence.public_beacon_output_sha256", "condition": "exact VRF returned output bytes hash matches pre-reveal commitment"},
    {"left_path": "objects.public_beacon_reveal_evidence.public_beacon_output_sha256", "right_path": "objects.generation_terminal_outcome.public_beacon_output_sha256", "condition": "outcome copies exact verified reveal output hash"},
    {"left_path": "objects.public_beacon_reveal_evidence.public_beacon_reveal_evidence_sha256", "right_path": "objects.generation_terminal_outcome.public_beacon_reveal_evidence_sha256", "condition": "outcome consumes exact reveal evidence"},
    {"left_path": "objects.pre_witness_technical_health_evidence.pre_witness_technical_health_evidence_sha256", "right_path": "objects.generation_terminal_outcome.pre_witness_technical_health_evidence_sha256", "condition": "outcome consumes exact pre-witness health evidence"},
    {"left_path": "objects.terminal_deadline_observation_evidence.terminal_deadline_observation_evidence_sha256", "right_path": "objects.generation_terminal_outcome.terminal_deadline_observation_evidence_sha256", "condition": "outcome materialized at exact authenticated deadline"},
    {"left_path": "objects.terminal_deadline_observation_evidence.terminal_deadline_observation_evidence_sha256", "right_path": "objects.generation_terminal_anchor_evidence.terminal_deadline_observation_evidence_sha256", "condition": "anchor materialized at exact authenticated deadline"},
])
for right_object in ["generation_reservation_ledger_evidence", "beacon_reservation_order_evidence", "public_beacon_reveal_evidence", "terminal_deadline_observation_evidence", "generation_terminal_outcome", "generation_terminal_anchor_evidence"]:
    generation_equality_rows.append({"left_path": "objects.generation_reservation.fixed_terminal_deadline_round_index", "right_path": f"objects.{right_object}.fixed_terminal_deadline_round_index", "condition": "same exact checked deadline round fixed before reveal"})
generation_equality_rows.extend([
    {"left_path": "objects.generation_reservation.pre_witness_health_predicate_sha256", "right_path": "objects.generation_reservation_ledger_evidence.pre_witness_health_predicate_sha256", "condition": "reservation commits fixed health predicate before reveal"},
    {"left_path": "objects.generation_reservation.pre_witness_health_profile_sha256", "right_path": "objects.generation_reservation_ledger_evidence.pre_witness_health_profile_sha256", "condition": "reservation commits fixed health profile before reveal"},
    {"left_path": "objects.generation_reservation.pre_witness_health_predicate_sha256", "right_path": "objects.pre_witness_technical_health_evidence.pre_witness_health_predicate_sha256", "condition": "health evidence evaluates exactly precommitted predicate"},
    {"left_path": "objects.generation_reservation.pre_witness_health_profile_sha256", "right_path": "objects.pre_witness_technical_health_evidence.pre_witness_health_profile_sha256", "condition": "health evidence uses exactly precommitted profile"},
])

role_target_equality_rows = []
for role_row in output_role_table:
    role = role_row["role"]
    binding = role_row["target_resolution"]
    target_object = binding["target_object"]
    reservation_link = f"objects.{target_object}.{binding['reservation_link_field']}"
    ledger_link = f"objects.{target_object}.{binding['ledger_link_field']}"
    outcome_link = f"objects.{target_object}.{binding['outcome_link_field']}"
    anchor_link = f"objects.{target_object}.{binding['anchor_link_field']}"
    role_target_equality_rows.extend([
        {"left_path": f"resolved({reservation_link}).output_role", "right_path": f"constant.{role}", "condition": "target field-path selects exactly this output role"},
        {"left_path": f"resolved({reservation_link}).reserved_next_sequence", "right_path": binding["sequence_path"], "condition": "reservation sequence equals exact target lifecycle sequence"},
        {"left_path": f"resolved({reservation_link}).authoritative_pre_journal_state_root_sha256", "right_path": binding["pre_root_path"], "condition": "reservation authoritative pre root equals target pre-state root"},
        {"left_path": f"resolved({reservation_link}).authoritative_pre_journal_state_object_sha256", "right_path": binding["pre_object_path"], "condition": "reservation authoritative pre object equals target pre-state object"},
        {"left_path": f"resolved({reservation_link}).authoritative_pre_record_count", "right_path": binding["pre_count_path"], "condition": "reservation authoritative pre count equals target pre count"},
        {"left_path": f"resolved({reservation_link}).authoritative_pre_head_sequence", "right_path": binding["pre_head_path"], "condition": "reservation authoritative pre head equals target pre head"},
        {"left_path": f"resolved({ledger_link}).generation_reservation_sha256", "right_path": reservation_link, "condition": "target binds exact reservation-ledger transition"},
        {"left_path": f"resolved({outcome_link}).generation_reservation_sha256", "right_path": reservation_link, "condition": "target binds exact mandatory outcome"},
        {"left_path": f"resolved({anchor_link}).generation_reservation_sha256", "right_path": reservation_link, "condition": "target binds exact independent terminal anchor"},
        {"left_path": f"resolved({outcome_link}).terminal_outcome", "right_path": "constant.SUCCESS", "condition": "normal target exists only for SUCCESS; FAILED uses canonical failure sequence transition"},
    ])
generation_equality_rows.extend(role_target_equality_rows)
doc["role_specific_reservation_target_and_journal_barrier"] = {
    "role_count": len(output_role_table),
    "rows": [{"role": row["role"], **row["target_resolution"]} for row in output_role_table],
    "role_target_equality_row_count": len(role_target_equality_rows),
    "normal_record_active_set_root_formula": "exact_generated_sha256_derivations active_generation_chain_set_root_sha256 selector; one sequence-wide pre-output materialization hash plus exact ten roles and six role-specific chain hashes per role in fixed order; every outcome SUCCESS",
    "journal_cas_barrier": "before role zero, generation_sequence_transaction_claim_evidence atomically changes the authoritative sequence-claim ledger slot to HELD and the authoritative journal store refuses every unrelated CAS at that pre-root. All created role reservations are subclaims and role terminal consumption preserves HELD. The final commit_evidence alone contains and signs active_generation_chain_set_root_sha256 after all ten anchors and atomically advances journal plus HELD-to-RELEASED claim state; the one canonical pre-output technical-failure role-terminal-failure or hidden-refusal commit does the same release with its journal/authority/anchor successors. There is no inter-role or post-terminal/pre-commit release gap",
    "dummy_interleaving_sequence_transplant_missing_role_failed_role_or_second_chain_allowed": False,
}
generation_equality_rows.append({"left_path": "objects.commit_evidence.active_generation_chain_set_root_sha256", "right_path": "derived.complete_ten_role_success_chain_set_root_sha256", "condition": "final commit is created only after the one pre-output materialization commitment and all ten distinct role-qualified reservation/ledger/reveal/deadline/outcome/anchor chains terminate SUCCESS; the declared typed derived endpoint fixes the exact ordered preimage and no earlier target contains this future root"})

# FAILED branch consumes the same reserved sequence with one canonical technical record and CAS.
for field in ["namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256", "journal_id_token", "journal_epoch"]:
    generation_equality_rows.append({"left_path": f"objects.generation_terminal_anchor_evidence.{field}", "right_path": f"objects.generation_failure_record.{field}", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; canonical failure record uses exact failed transaction identity"})
    generation_equality_rows.append({"left_path": f"objects.generation_sequence_lifecycle_refusal_evidence.{field}", "right_path": f"objects.generation_failure_record.{field}", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL; canonical failure record uses exact refusal transaction identity"})
    generation_equality_rows.append({"left_path": f"objects.pre_witness_technical_health_evidence.{field}", "right_path": f"objects.generation_failure_record.{field}", "condition": "failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE; canonical failure record uses exact pre-output claim identity"})
generation_equality_rows.extend([
    {"left_path": "objects.generation_terminal_anchor_evidence.generation_reservation_sha256", "right_path": "objects.generation_failure_record.generation_reservation_sha256", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record consumes exact failed reservation"},
    {"left_path": "objects.generation_terminal_anchor_evidence.generation_reservation_ledger_evidence_sha256", "right_path": "objects.generation_failure_record.generation_reservation_ledger_evidence_sha256", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record consumes exact reserved ledger transition"},
    {"left_path": "objects.generation_terminal_anchor_evidence.public_beacon_reveal_evidence_sha256", "right_path": "objects.generation_failure_record.public_beacon_reveal_evidence_sha256", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record consumes exact reveal"},
    {"left_path": "objects.generation_terminal_anchor_evidence.terminal_deadline_observation_evidence_sha256", "right_path": "objects.generation_failure_record.terminal_deadline_observation_evidence_sha256", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record consumes exact deadline evidence"},
    {"left_path": "objects.generation_terminal_anchor_evidence.generation_terminal_outcome_sha256", "right_path": "objects.generation_failure_record.generation_terminal_outcome_sha256", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record consumes exact FAILED outcome"},
    {"left_path": "objects.generation_terminal_anchor_evidence.generation_terminal_anchor_evidence_sha256", "right_path": "objects.generation_failure_record.generation_terminal_anchor_evidence_sha256", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record consumes exact independent terminal anchor"},
    {"left_path": "objects.generation_terminal_anchor_evidence.reserved_sequence", "right_path": "objects.generation_failure_record.reserved_sequence", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record occupies exact failed reserved sequence"},
    {"left_path": "objects.generation_terminal_anchor_evidence.output_role", "right_path": "objects.generation_failure_record.output_role", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record identifies exact failed role"},
    {"left_path": "objects.generation_terminal_anchor_evidence.reservation_slot_key_sha256", "right_path": "objects.generation_failure_record.reservation_slot_key_sha256", "condition": "failure_trigger == ROLE_TERMINAL_FAILED; failure record identifies exact consumed role slot"},
    {"left_path": "objects.generation_sequence_lifecycle_refusal_evidence.generation_sequence_lifecycle_refusal_evidence_sha256", "right_path": "objects.generation_failure_record.generation_sequence_lifecycle_refusal_evidence_sha256", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL; failure record consumes exact generic hidden refusal"},
    {"left_path": "objects.generation_sequence_lifecycle_refusal_evidence.reserved_sequence", "right_path": "objects.generation_failure_record.reserved_sequence", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL; refusal occupies exact claimed sequence"},
    {"left_path": "objects.generation_sequence_lifecycle_refusal_evidence.refusal_boundary_role", "right_path": "objects.generation_failure_record.output_role", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL; exact canonical refused boundary role"},
    {"left_path": "objects.generation_sequence_lifecycle_refusal_evidence.refusal_boundary_role_index", "right_path": "objects.generation_failure_record.failure_role_index", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL; exact canonical refused boundary index"},
    {"left_path": "objects.generation_sequence_lifecycle_refusal_evidence.completed_success_role_prefix_root_sha256", "right_path": "objects.generation_failure_record.completed_success_role_prefix_root_sha256", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL; exact hiding SUCCESS-prefix commitment"},
    {"left_path": "objects.pre_witness_technical_health_evidence.pre_witness_technical_health_evidence_sha256", "right_path": "objects.generation_failure_record.pre_witness_technical_health_evidence_sha256", "condition": "every failure trigger consumes the one exact pre-output materialization evidence"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.generation_sequence_transaction_claim_evidence_sha256", "right_path": "objects.generation_failure_record.generation_sequence_transaction_claim_evidence_sha256", "condition": "every failure/refusal consumes the one held sequence claim"},
    {"left_path": "objects.generation_sequence_transaction_claim_evidence.reserved_next_sequence", "right_path": "objects.generation_failure_record.reserved_sequence", "condition": "every failure/refusal occupies the exact claimed sequence"},
    {"left_path": "objects.pre_witness_technical_health_evidence.technical_health_result", "right_path": "objects.generation_failure_record.technical_health_result", "condition": "failure_trigger in {PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,HIDDEN_LIFECYCLE_REFUSAL}; pre-output failure copies FIXED_TECHNICAL_FAILURE and hidden lifecycle refusal copies READY"},
    {"left_path": "objects.generation_failure_record.failure_trigger", "right_path": "objects.generation_failure_sequence_commit_evidence.failure_trigger", "condition": "failure journal CAS authenticates exact mutually exclusive trigger"},
    {"left_path": "objects.generation_failure_record.generation_terminal_anchor_evidence_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.generation_terminal_anchor_evidence_sha256", "condition": "ROLE_TERMINAL_FAILED branch copies exact anchor; other branches copy exact null"},
    {"left_path": "objects.generation_failure_record.generation_sequence_lifecycle_refusal_evidence_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.generation_sequence_lifecycle_refusal_evidence_sha256", "condition": "HIDDEN_LIFECYCLE_REFUSAL branch copies exact refusal; other branches copy exact null"},
    {"left_path": "objects.generation_failure_record.failure_code", "right_path": "constant.FIXED_CONTENT_INDEPENDENT_TECHNICAL_FAILURE", "condition": "failure_trigger in {PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,ROLE_TERMINAL_FAILED}"},
    {"left_path": "objects.generation_failure_record.failure_code", "right_path": "constant.HIDDEN_LIFECYCLE_INTEGRITY_REFUSAL", "condition": "failure_trigger == HIDDEN_LIFECYCLE_REFUSAL"},
    {"left_path": "objects.generation_failure_record.output_role", "right_path": "constant.SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "condition": "failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE; fixed boundary is role zero before any allocation"},
    {"left_path": "objects.generation_failure_record.failure_role_index", "right_path": "constant.UINT64_ZERO", "condition": "failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE"},
    {"left_path": "objects.generation_failure_record.generation_failure_record_sha256", "right_path": "objects.generation_failure_journal_state.generation_failure_record_sha256", "condition": "post failure state consumes exact technical record"},
    {"left_path": "objects.generation_failure_record.generation_failure_record_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.generation_failure_record_sha256", "condition": "CAS evidence consumes exact technical record"},
    {"left_path": "instances.current_pre_journal_state.head_receipt_hash_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.pre_head_receipt_hash_sha256", "condition": "failure CAS, including consecutive failure, consumes the exact typed predecessor receipt head sentinel or normal receipt head; null only at registered genesis"},
    {"left_path": "instances.current_pre_journal_state.head_event_hash_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.pre_head_event_hash_sha256", "condition": "failure CAS, including consecutive failure, consumes the exact typed predecessor event head sentinel or normal event head; null only at registered genesis"},
    {"left_path": "instances.current_pre_journal_state.consumed_receipt_token_root_sha256", "right_path": "objects.generation_failure_record.pre_receipt_token_root_sha256", "condition": "failure transition reads exact current pre-state receipt replay accumulator root"},
    {"left_path": "objects.generation_failure_record.pre_receipt_token_root_sha256", "right_path": "objects.generation_failure_record.post_receipt_token_root_sha256", "condition": "technical failure accepts no receipt token and preserves the receipt replay accumulator byte-for-byte"},
    {"left_path": "objects.generation_failure_record.post_receipt_token_root_sha256", "right_path": "objects.generation_failure_journal_state.consumed_receipt_token_root_sha256", "condition": "failure post-state carries exact unchanged receipt replay accumulator root"},
    {"left_path": "objects.generation_failure_record.pre_receipt_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.pre_receipt_token_root_sha256", "condition": "failure commit authenticates exact pre receipt accumulator root"},
    {"left_path": "objects.generation_failure_record.post_receipt_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.post_receipt_token_root_sha256", "condition": "failure commit authenticates exact unchanged post receipt accumulator root"},
    {"left_path": "instances.current_pre_journal_state.consumed_scope_token_root_sha256", "right_path": "objects.generation_failure_record.pre_scope_token_root_sha256", "condition": "failure transition reads exact current pre-state scope replay accumulator root"},
    {"left_path": "objects.generation_failure_record.pre_scope_token_root_sha256", "right_path": "objects.generation_failure_record.post_scope_token_root_sha256", "condition": "technical failure accepts no scope token and preserves the scope replay accumulator byte-for-byte"},
    {"left_path": "objects.generation_failure_record.post_scope_token_root_sha256", "right_path": "objects.generation_failure_journal_state.consumed_scope_token_root_sha256", "condition": "failure post-state carries exact unchanged scope replay accumulator root"},
    {"left_path": "objects.generation_failure_record.pre_scope_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.pre_scope_token_root_sha256", "condition": "failure commit authenticates exact pre scope accumulator root"},
    {"left_path": "objects.generation_failure_record.post_scope_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.post_scope_token_root_sha256", "condition": "failure commit authenticates exact unchanged post scope accumulator root"},
    {"left_path": "instances.current_pre_journal_state.consumed_proof_token_root_sha256", "right_path": "objects.generation_failure_record.pre_proof_token_root_sha256", "condition": "failure transition reads exact current pre-state proof replay accumulator root"},
    {"left_path": "objects.generation_failure_record.pre_proof_token_root_sha256", "right_path": "objects.generation_failure_record.post_proof_token_root_sha256", "condition": "technical failure accepts no proof token and preserves the proof replay accumulator byte-for-byte"},
    {"left_path": "objects.generation_failure_record.post_proof_token_root_sha256", "right_path": "objects.generation_failure_journal_state.consumed_proof_token_root_sha256", "condition": "failure post-state carries exact unchanged proof replay accumulator root"},
    {"left_path": "objects.generation_failure_record.pre_proof_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.pre_proof_token_root_sha256", "condition": "failure commit authenticates exact pre proof accumulator root"},
    {"left_path": "objects.generation_failure_record.post_proof_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.post_proof_token_root_sha256", "condition": "failure commit authenticates exact unchanged post proof accumulator root"},
    {"left_path": "objects.generation_failure_journal_state.consumed_receipt_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.post_receipt_token_root_sha256", "condition": "failure journal state and authenticated successor statement use one receipt accumulator instance"},
    {"left_path": "objects.generation_failure_journal_state.consumed_scope_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.post_scope_token_root_sha256", "condition": "failure journal state and authenticated successor statement use one scope accumulator instance"},
    {"left_path": "objects.generation_failure_journal_state.consumed_proof_token_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.post_proof_token_root_sha256", "condition": "failure journal state and authenticated successor statement use one proof accumulator instance"},
    {"left_path": "objects.generation_failure_journal_state.generation_failure_journal_state_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.post_failure_state_root_sha256", "condition": "CAS commits exact failure post-state root"},
    {"left_path": "objects.generation_failure_journal_state.generation_failure_journal_state_object_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.post_failure_state_object_sha256", "condition": "CAS commits exact failure post-state object"},
    {"left_path": "objects.generation_failure_journal_state.committed_record_count", "right_path": "objects.generation_failure_sequence_commit_evidence.post_record_count", "condition": "CAS commits exact checked post count"},
    {"left_path": "objects.generation_failure_journal_state.head_sequence", "right_path": "objects.generation_failure_sequence_commit_evidence.post_head_sequence", "condition": "CAS commits exact failed reserved sequence as head"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_record_count", "right_path": "checked_plus_one(objects.generation_failure_sequence_commit_evidence.pre_record_count)", "condition": "failure record advances authoritative count exactly once"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_head_sequence", "right_path": "objects.generation_failure_record.reserved_sequence", "condition": "failure record occupies sequence; next reservation advances"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.generation_terminal_anchor_evidence_sha256", "right_path": "objects.generation_failure_record.generation_terminal_anchor_evidence_sha256", "condition": "branch-exact copy: ROLE_TERMINAL_FAILED uses the exact anchor; pre-output technical failure and hidden refusal use exact JSON null"},
    {"left_path": "objects.generation_failure_record.unreserved_suffix_cancellation_barrier_root_sha256", "right_path": "objects.generation_failure_journal_state.failed_sequence_barrier_root_sha256", "condition": "failure post state carries exact deterministic remaining-role cancellation barrier"},
    {"left_path": "objects.generation_failure_record.unreserved_suffix_cancellation_barrier_root_sha256", "right_path": "objects.generation_failure_sequence_commit_evidence.failed_sequence_barrier_root_sha256", "condition": "one journal/authority/anchor commit authenticates exact remaining-role cancellation barrier"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_external_anchor_monotonic_counter", "right_path": "checked_plus_one(objects.generation_failure_sequence_commit_evidence.pre_external_anchor_monotonic_counter)", "condition": "failure external-anchor successor advances preserved counter exactly once with overflow refusal"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_state_authority_monotonic_counter", "right_path": "checked_plus_one(objects.generation_failure_sequence_commit_evidence.pre_state_authority_monotonic_counter)", "condition": "failure state-authority successor advances preserved counter exactly once with overflow refusal"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_failure_external_anchor_root_sha256", "right_path": "resolved_nested(objects.generation_failure_sequence_commit_evidence.post_failure_external_anchor_statement_sha256, objects.generation_failure_sequence_commit_evidence.failure_anchor_authentication_proof_base64)", "condition": "exact closed external-anchor successor object under preserved profile/key"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_failure_state_authority_head_evidence_sha256", "right_path": "resolved_nested(objects.generation_failure_sequence_commit_evidence.post_failure_state_authority_statement_sha256, objects.generation_failure_sequence_commit_evidence.failure_authority_authentication_signature_base64)", "condition": "exact closed state-authority successor object binding the same post-state and new anchor"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_failure_external_anchor_root_sha256", "right_path": "resolved(objects.generation_failure_sequence_commit_evidence.post_failure_state_authority_statement_sha256).post_failure_external_anchor_root_sha256", "condition": "failure authority successor binds exact new failure anchor"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_failure_state_authority_head_evidence_sha256", "right_path": "objects.failure_state_authority_current_head_observation.post_failure_state_authority_head_evidence_sha256", "condition": "branch-selected future reservation or transition accepts the failure predecessor only after the typed independent authority current-head observation authenticates this exact successor"},
    {"left_path": "objects.generation_failure_sequence_commit_evidence.post_failure_external_anchor_root_sha256", "right_path": "objects.failure_external_anchor_current_head_observation.post_failure_external_anchor_root_sha256", "condition": "branch-selected future reservation or transition accepts the failure predecessor only after the typed independent anchor current-head observation authenticates this exact successor"},
])
for role in role_lifecycle_order:
    selected_release = selected_failure_release_condition(role)
    commit_alias = f"instances.roles.{role}.failure_commit"
    record_alias = f"instances.roles.{role}.failure_record"
    anchor_observation = f"instances.roles.{role}.failure_anchor_current_head_observation"
    authority_observation = f"instances.roles.{role}.failure_authority_current_head_observation"
    for field in [
        "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256",
        "journal_id_token", "journal_epoch", "generation_failure_sequence_commit_evidence_sha256",
        "generation_failure_record_sha256", "failure_trigger", "post_failure_state_root_sha256",
        "post_failure_state_object_sha256", "post_record_count", "post_head_sequence",
        "post_head_receipt_hash_sha256", "post_head_event_hash_sha256",
        "post_failure_external_anchor_root_sha256", "post_external_anchor_monotonic_counter",
        "external_anchor_identity_sha256", "external_anchor_authentication_key_role",
    ]:
        source = record_alias if field in {"generation_failure_record_sha256", "failure_trigger"} else commit_alias
        generation_equality_rows.append({"left_path": f"{source}.{field}", "right_path": f"{anchor_observation}.{field}", "condition": f"{selected_release}; typed anchor observation repeats the exact same failure successor field"})
    for field in ["failure_role", "failure_role_index", "reserved_sequence"]:
        record_field = {"failure_role": "output_role", "failure_role_index": "failure_role_index", "reserved_sequence": "reserved_sequence"}[field]
        generation_equality_rows.append({"left_path": f"{record_alias}.{record_field}", "right_path": f"{anchor_observation}.{field}", "condition": f"{selected_release}; typed anchor observation is exact role sequence and boundary qualified"})
    generation_equality_rows.extend([
        {"left_path": f"{anchor_observation}.external_anchor_profile_sha256", "right_path": "objects.pinned_context.external_anchor_profile_sha256", "condition": f"{selected_release}; exact pinned external-anchor current-head query profile"},
        {"left_path": f"{anchor_observation}.current_head_observation_result", "right_path": "constant.EXACT_INDEPENDENTLY_CURRENT_HEAD", "condition": f"{selected_release}; stale sibling or restored anchor head refuses"},
        {"left_path": f"{anchor_observation}.failure_external_anchor_current_head_observation_sha256", "right_path": f"{authority_observation}.failure_external_anchor_current_head_observation_sha256", "condition": f"{selected_release}; authority current-head observation consumes the exact typed anchor observation"},
    ])
    for field in [
        "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256",
        "journal_id_token", "journal_epoch", "generation_failure_sequence_commit_evidence_sha256",
        "generation_failure_record_sha256", "failure_trigger", "failure_role", "failure_role_index",
        "reserved_sequence", "post_failure_state_root_sha256", "post_failure_state_object_sha256",
        "post_record_count", "post_head_sequence", "post_head_receipt_hash_sha256",
        "post_head_event_hash_sha256", "post_failure_external_anchor_root_sha256",
        "post_external_anchor_monotonic_counter",
    ]:
        generation_equality_rows.append({"left_path": f"{anchor_observation}.{field}", "right_path": f"{authority_observation}.{field}", "condition": f"{selected_release}; both typed current-head observations authenticate one exact failure successor tuple"})
    for field in ["post_failure_state_authority_head_evidence_sha256", "post_state_authority_monotonic_counter", "state_authority_identity_sha256", "state_authority_authentication_key_role"]:
        generation_equality_rows.append({"left_path": f"{commit_alias}.{field}", "right_path": f"{authority_observation}.{field}", "condition": f"{selected_release}; typed authority observation repeats the exact failure successor field"})
    generation_equality_rows.append({"left_path": f"{authority_observation}.current_head_observation_result", "right_path": "constant.EXACT_INDEPENDENTLY_CURRENT_HEAD", "condition": f"{selected_release}; stale sibling or restored authority head refuses"})
doc["canonical_failed_generation_sequence_consumption"] = {
    "record_schema": "objects.generation_failure_record",
    "post_state_schema": "objects.generation_failure_journal_state",
    "atomic_commit_schema": "objects.generation_failure_sequence_commit_evidence",
    "trigger": "exactly one of: deterministic pre-output fixed technical failure before role zero; the unique first FAILED terminal outcome; or one generic hidden post-claim lifecycle refusal at the next fixed role boundary. Earlier roles are a complete SUCCESS prefix and every uncreated boundary/suffix role is never reserved under the deterministic sequence cancellation barrier",
    "next_sequence_rule": "future reservation reads this exact independently current post failure journal state, state-authority successor and external-anchor successor, verifies their common state/counters/heads/barrier, and reserves checked head sequence plus one; no later role at the failed sequence can reserve",
    "single_sequence_cas_rule": "exactly one failure/refusal record state and commit exist for the selected branch/boundary; one journal CAS plus one nested authority successor plus one nested anchor successor advance the sequence and release HELD; any second branch record same-sequence reservation after the boundary or sibling pre-root refuses",
    "pre_output_fixed_failure_row": {"failure_trigger": "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE", "failure_role": role_lifecycle_order[0], "failure_role_index": 0, "required_complete_success_prefix_roles": [], "required_never_reserved_cancelled_suffix_roles": role_lifecycle_order, "cancelled_unreserved_role_count": len(role_lifecycle_order)},
    "deterministic_first_failure_rows": [
        {
            "failure_role": role,
            "failure_role_index": index,
            "required_complete_success_prefix_roles": role_lifecycle_order[:index],
            "required_never_reserved_cancelled_suffix_roles": role_lifecycle_order[index + 1:],
            "cancelled_unreserved_role_count": len(role_lifecycle_order) - index - 1,
            "one_commit_instance": f"instances.roles.{role}.failure_commit",
        }
        for index, role in enumerate(role_lifecycle_order)
    ],
    "hidden_lifecycle_refusal_rows": [
        {"failure_trigger": "HIDDEN_LIFECYCLE_REFUSAL", "refusal_boundary_role": role, "refusal_boundary_role_index": index, "required_complete_success_prefix_roles": role_lifecycle_order[:index], "required_never_reserved_cancelled_suffix_roles": role_lifecycle_order[index:], "cancelled_unreserved_role_count": len(role_lifecycle_order) - index, "one_commit_instance": f"instances.roles.{role}.failure_commit"}
        for index, role in enumerate(role_lifecycle_order)
    ],
    "memory_lifecycle_claim": "technical failure record does not assert COMPLETE erasure proof receipt event memory success correction supersession withdrawal or voluntary forgetting",
    "retry_same_sequence_skip_deadlock_dummy_record_or_fabricated_success_allowed": False,
}

scalar_repeat_rows = []
scalar_repeat_sources = {
    "journal_id_token": "objects.pinned_context.journal_id_token",
    "journal_epoch": "objects.pinned_context.journal_epoch",
}
scalar_repeat_sources.update({
    field: f"objects.pinned_context.{field}"
    for field in doc["fixed_key_roles"]
    if field.endswith("_key_role") and field in context["field_order"]
})
for field, source_path in scalar_repeat_sources.items():
    for object_name, obj in objects.items():
        if object_name != "pinned_context" and field in obj["field_order"]:
            scalar_repeat_rows.append({"left_path": f"objects.{object_name}.{field}", "right_path": source_path, "condition": "byte-identical linked transaction/recursion invariant"})
for field, source_object in {
    "random_receipt_token": "proof_public_inputs", "random_scope_token": "proof_public_inputs",
    "random_proof_token": "proof_public_inputs",
}.items():
    if field in objects[source_object]["field_order"]:
        for object_name in ["authenticated_result", "verifier_evidence", "receipt", "event", "token_accumulator_proof", "transition_request", "commit_evidence"]:
            if field in objects[object_name]["field_order"]:
                scalar_repeat_rows.append({"left_path": f"objects.{object_name}.{field}", "right_path": f"objects.{source_object}.{field}", "condition": "same current one-use opaque token"})
sequence_equality_rows = [
    {"left_path": "objects.receipt.sequence", "right_path": "objects.proof_public_inputs.sequence", "condition": "same current record"},
    {"left_path": "objects.event.sequence", "right_path": "objects.receipt.sequence", "condition": "same current record"},
    {"left_path": "objects.event.receipt_sequence", "right_path": "objects.receipt.sequence", "condition": "same current record"},
    {"left_path": "objects.transition_request.receipt_sequence", "right_path": "objects.receipt.sequence", "condition": "same current record"},
    {"left_path": "objects.transition_request.event_sequence", "right_path": "objects.event.sequence", "condition": "same current record"},
    {"left_path": "objects.committed_envelope.sequence", "right_path": "objects.receipt.sequence", "condition": "same current record"},
]

semantic_equality_rows = []
def semantic_pair(rule_index, left_path, right_path, condition):
    semantic_equality_rows.append({"left_path": left_path, "right_path": right_path, "condition": condition, "semantic_rule_index": rule_index})

# Rules 0-1: receipt is the exact proof-input projection.
for field in ["journal_id_token", "journal_epoch", "sequence", "previous_receipt_hash_sha256", "expected_pre_journal_state_root_sha256", "expected_pre_journal_state_object_sha256", "expected_pre_record_count", "expected_pre_head_sequence", "expected_pre_head_receipt_hash_sha256", "expected_pre_head_event_hash_sha256", "pinned_context_sha256", "singleton_registration_sha256"]:
    semantic_pair(0, f"objects.receipt.{field}", f"objects.proof_public_inputs.{field}", "exact receipt projection from public inputs")
semantic_pair(0, "objects.receipt.generic_status", "objects.proof_public_inputs.generic_result", "both exact COMPLETE constant")
for field in ["expected_pre_state_authority_head_evidence_sha256", "expected_pre_state_authority_counter", "expected_pre_external_anchor_root_sha256"]:
    semantic_pair(1, f"objects.receipt.{field}", f"objects.proof_public_inputs.{field}", "exact authority and anchor precondition projection")

# Rules 2-5: event and receipt predecessor/current-record closure.
for left_field, right_field in [
    ("journal_id_token", "journal_id_token"), ("journal_epoch", "journal_epoch"),
    ("receipt_sequence", "sequence"), ("receipt_previous_receipt_hash_sha256", "previous_receipt_hash_sha256"),
    ("expected_pre_journal_state_root_sha256", "expected_pre_journal_state_root_sha256"),
    ("expected_pre_journal_state_object_sha256", "expected_pre_journal_state_object_sha256"),
    ("expected_pre_record_count", "expected_pre_record_count"), ("expected_pre_head_sequence", "expected_pre_head_sequence"),
    ("expected_pre_head_receipt_hash_sha256", "expected_pre_head_receipt_hash_sha256"),
    ("expected_pre_head_event_hash_sha256", "expected_pre_head_event_hash_sha256"),
    ("receipt_hash_sha256", "receipt_hash_sha256"), ("pinned_context_sha256", "pinned_context_sha256"),
    ("singleton_registration_sha256", "singleton_registration_sha256"),
]:
    semantic_pair(2, f"objects.event.{left_field}", f"objects.receipt.{right_field}", "event consumes exact receipt/pre-state field")
for field in ["expected_pre_state_authority_head_evidence_sha256", "expected_pre_state_authority_counter", "expected_pre_external_anchor_root_sha256"]:
    semantic_pair(3, f"objects.event.{field}", f"objects.receipt.{field}", "same authority/anchor precondition")
    semantic_pair(3, f"objects.event.{field}", f"objects.proof_public_inputs.{field}", "same authority/anchor precondition")
semantic_pair(4, "objects.event.sequence", "objects.receipt.sequence", "same record sequence")
semantic_pair(4, "objects.event.previous_event_hash_sha256", "objects.receipt.expected_pre_head_event_hash_sha256", "event predecessor is expected pre head")
semantic_pair(5, "objects.receipt.previous_receipt_hash_sha256", "objects.receipt.expected_pre_head_receipt_hash_sha256", "receipt predecessor is expected pre head")

# Rule 6: every expected pre-state projection resolves to one journal-state instance.
pre_state_projection = {
    "expected_pre_journal_state_root_sha256": "journal_state_root_sha256",
    "expected_pre_journal_state_object_sha256": "journal_state_object_sha256",
    "expected_pre_record_count": "committed_record_count",
    "expected_pre_head_sequence": "head_sequence",
    "expected_pre_head_receipt_hash_sha256": "head_receipt_hash_sha256",
    "expected_pre_head_event_hash_sha256": "head_event_hash_sha256",
    "pinned_context_sha256": "pinned_context_sha256",
    "singleton_registration_sha256": "singleton_registration_sha256",
}
for source_object in ["proof_public_inputs", "receipt", "event"]:
    for source_field, state_field in pre_state_projection.items():
        semantic_pair(6, f"objects.{source_object}.{source_field}", f"instances.current_pre_journal_state.{state_field}", "same exact counter-conditioned pre-state instance")

# Rules 7-11: transition request consumes exact pre state, receipt and event and creates exact post heads.
transition_pre_projection = {
    "pre_journal_state_root_sha256": "journal_state_root_sha256", "pre_journal_state_object_sha256": "journal_state_object_sha256",
    "pre_record_count": "committed_record_count", "pre_head_sequence": "head_sequence",
    "pre_head_receipt_hash_sha256": "head_receipt_hash_sha256", "pre_head_event_hash_sha256": "head_event_hash_sha256",
    "pinned_context_sha256": "pinned_context_sha256", "singleton_registration_sha256": "singleton_registration_sha256",
}
for request_field, state_field in transition_pre_projection.items():
    semantic_pair(7, f"objects.transition_request.{request_field}", f"instances.current_pre_journal_state.{state_field}", "transition consumes exact current pre-state instance")
for request_field, expected_field in [
    ("pre_journal_state_root_sha256", "expected_pre_journal_state_root_sha256"), ("pre_journal_state_object_sha256", "expected_pre_journal_state_object_sha256"),
    ("pre_record_count", "expected_pre_record_count"), ("pre_head_sequence", "expected_pre_head_sequence"),
    ("pre_head_receipt_hash_sha256", "expected_pre_head_receipt_hash_sha256"), ("pre_head_event_hash_sha256", "expected_pre_head_event_hash_sha256"),
]:
    semantic_pair(7, f"objects.transition_request.{request_field}", f"objects.receipt.{expected_field}", "transition request equals receipt expected pre field")
    semantic_pair(7, f"objects.transition_request.{request_field}", f"objects.event.{expected_field}", "transition request equals event expected pre field")
for request_field, source_field in [("pre_state_authority_head_evidence_sha256", "expected_pre_state_authority_head_evidence_sha256"), ("pre_state_authority_counter", "expected_pre_state_authority_counter"), ("pre_external_anchor_root_sha256", "expected_pre_external_anchor_root_sha256")]:
    semantic_pair(8, f"objects.transition_request.{request_field}", f"objects.receipt.{source_field}", "transition authority/anchor precondition equals receipt")
    semantic_pair(8, f"objects.transition_request.{request_field}", f"objects.event.{source_field}", "transition authority/anchor precondition equals event")
semantic_pair(8, "objects.transition_request.pre_state_authority_head_evidence_sha256", "instances.current_pre_state_authority_evidence.state_authority_head_evidence_sha256", "resolved exact registered-genesis normal or failure current authority evidence")
semantic_pair(8, "objects.transition_request.pre_state_authority_counter", "instances.current_pre_state_authority_evidence.authority_monotonic_counter", "resolved exact registered-genesis normal or failure current authority counter")
semantic_pair(8, "objects.transition_request.pre_external_anchor_root_sha256", "instances.current_pre_external_anchor_evidence.external_anchor_root_sha256", "resolved exact registered-genesis normal or failure current external anchor")
semantic_pair(9, "objects.transition_request.receipt_sequence", "objects.event.sequence", "receipt and event sequence same")
semantic_pair(9, "objects.transition_request.event_sequence", "objects.event.sequence", "event sequence same")
semantic_pair(9, "objects.transition_request.post_head_sequence", "objects.event.sequence", "post head is current sequence")
semantic_pair(10, "objects.transition_request.receipt_previous_receipt_hash_sha256", "objects.transition_request.pre_head_receipt_hash_sha256", "receipt predecessor equals pre head")
semantic_pair(10, "objects.transition_request.event_previous_event_hash_sha256", "objects.transition_request.pre_head_event_hash_sha256", "event predecessor equals pre head")
semantic_pair(11, "objects.transition_request.post_head_receipt_hash_sha256", "objects.receipt.receipt_hash_sha256", "post receipt head is current receipt")
semantic_pair(11, "objects.transition_request.post_head_event_hash_sha256", "objects.event.event_hash_sha256", "post event head is current event")

# Rule 12: exact post-state instance and accumulator outputs.
post_state_projection = {
    "post_journal_state_root_sha256": "journal_state_root_sha256", "post_journal_state_object_sha256": "journal_state_object_sha256",
    "post_record_count": "committed_record_count", "post_head_sequence": "head_sequence",
    "post_head_receipt_hash_sha256": "head_receipt_hash_sha256", "post_head_event_hash_sha256": "head_event_hash_sha256",
    "pinned_context_sha256": "pinned_context_sha256", "journal_authentication_key_role": "journal_authentication_key_role",
    "singleton_registration_sha256": "singleton_registration_sha256",
}
for request_field, state_field in post_state_projection.items():
    semantic_pair(12, f"objects.transition_request.{request_field}", f"instances.current_post_journal_state.{state_field}", "transition post field equals same exact post-state instance")
for token_kind in ["receipt", "scope", "proof"]:
    semantic_pair(12, f"objects.token_accumulator_proof.post_{token_kind}_token_root_sha256", f"instances.current_post_journal_state.consumed_{token_kind}_token_root_sha256", "post journal token root equals verified accumulator transition output")

# Rules 13-14: commit evidence consumes request and exact authority post evidence.
commit_request_pairs = [
    ("transition_request_sha256", "transition_request_sha256"), ("journal_id_token", "journal_id_token"), ("journal_epoch", "journal_epoch"),
    ("cas_expected_pre_state_root_sha256", "pre_journal_state_root_sha256"), ("committed_pre_state_object_sha256", "pre_journal_state_object_sha256"),
    ("committed_post_state_root_sha256", "post_journal_state_root_sha256"), ("committed_post_state_object_sha256", "post_journal_state_object_sha256"),
    ("committed_record_count", "post_record_count"), ("committed_head_sequence", "post_head_sequence"),
    ("committed_head_receipt_hash_sha256", "post_head_receipt_hash_sha256"), ("committed_head_event_hash_sha256", "post_head_event_hash_sha256"),
    ("random_receipt_token", "random_receipt_token"), ("random_scope_token", "random_scope_token"), ("random_proof_token", "random_proof_token"),
    ("token_accumulator_proof_sha256", "token_accumulator_proof_sha256"), ("pinned_context_sha256", "pinned_context_sha256"),
    ("journal_authentication_key_role", "journal_authentication_key_role"), ("state_authority_authentication_key_role", "state_authority_authentication_key_role"),
    ("external_anchor_authentication_key_role", "external_anchor_authentication_key_role"), ("singleton_registration_sha256", "singleton_registration_sha256"),
]
for commit_field, request_field in commit_request_pairs:
    semantic_pair(13, f"objects.commit_evidence.{commit_field}", f"objects.transition_request.{request_field}", "commit evidence exact request projection")
for commit_field, request_field in [("pre_state_authority_head_evidence_sha256", "pre_state_authority_head_evidence_sha256"), ("pre_state_authority_counter", "pre_state_authority_counter"), ("pre_external_anchor_root_sha256", "pre_external_anchor_root_sha256")]:
    semantic_pair(14, f"objects.commit_evidence.{commit_field}", f"objects.transition_request.{request_field}", "commit pre authority/anchor equals request")
semantic_pair(14, "objects.commit_evidence.post_state_authority_head_evidence_sha256", "objects.state_authority_head_evidence.state_authority_head_evidence_sha256", "commit authenticates exact post authority object")
semantic_pair(14, "objects.commit_evidence.post_state_authority_counter", "objects.state_authority_head_evidence.authority_monotonic_counter", "post authority counter exact")
semantic_pair(14, "objects.commit_evidence.post_state_authority_counter", "objects.transition_request.expected_post_state_authority_counter", "checked pre plus one expected counter")
semantic_pair(14, "objects.commit_evidence.authoritative_commit_index", "objects.commit_evidence.committed_record_count", "signed authoritative commit index is exactly the committed post-state record count")
for authority_field, commit_field in [("committed_record_count", "committed_record_count"), ("head_sequence", "committed_head_sequence"), ("head_receipt_hash_sha256", "committed_head_receipt_hash_sha256"), ("head_event_hash_sha256", "committed_head_event_hash_sha256"), ("head_journal_state_root_sha256", "committed_post_state_root_sha256"), ("head_journal_state_object_sha256", "committed_post_state_object_sha256")]:
    semantic_pair(14, f"objects.state_authority_head_evidence.{authority_field}", f"objects.commit_evidence.{commit_field}", "authority preimage authenticates exact committed post state")

# Rules 15-16: committed envelope projection.
for envelope_field, source_object, source_field in [
    ("journal_id_token", "commit_evidence", "journal_id_token"), ("journal_epoch", "commit_evidence", "journal_epoch"),
    ("sequence", "receipt", "sequence"), ("receipt_hash_sha256", "receipt", "receipt_hash_sha256"),
    ("event_hash_sha256", "event", "event_hash_sha256"), ("transition_request_sha256", "transition_request", "transition_request_sha256"),
    ("commit_evidence_sha256", "commit_evidence", "commit_evidence_sha256"),
    ("post_journal_state_root_sha256", "commit_evidence", "committed_post_state_root_sha256"),
    ("post_journal_state_object_sha256", "commit_evidence", "committed_post_state_object_sha256"),
    ("pinned_context_sha256", "commit_evidence", "pinned_context_sha256"), ("singleton_registration_sha256", "commit_evidence", "singleton_registration_sha256"),
]:
    semantic_pair(15, f"objects.committed_envelope.{envelope_field}", f"objects.{source_object}.{source_field}", "envelope exact linked-object projection")
for field in ["post_state_authority_head_evidence_sha256", "post_state_authority_counter", "post_external_anchor_root_sha256"]:
    semantic_pair(16, f"objects.committed_envelope.{field}", f"objects.commit_evidence.{field}", "envelope exact authority/anchor projection")
semantic_pair(16, "objects.committed_envelope.post_state_authority_head_evidence_sha256", "objects.state_authority_head_evidence.state_authority_head_evidence_sha256", "envelope exact authority object")
semantic_pair(16, "objects.committed_envelope.post_state_authority_counter", "objects.state_authority_head_evidence.authority_monotonic_counter", "envelope exact authority counter")
semantic_pair(16, "objects.committed_envelope.post_external_anchor_root_sha256", "objects.state_authority_head_evidence.external_anchor_root_sha256", "envelope exact authority-bound anchor")

# Rules 17-24: fixed roles/keys and authority-anchor projection.
semantic_pair(17, "objects.authenticated_result.result_authentication_key_role", "objects.proof_public_inputs.result_authentication_key_role", "fixed result role")
semantic_pair(17, "objects.verifier_evidence.verifier_evidence_key_role", "objects.proof_public_inputs.verifier_evidence_key_role", "fixed verifier role")
for object_name in ["journal_state", "transition_request", "commit_evidence"]:
    semantic_pair(18, f"objects.{object_name}.journal_authentication_key_role", "objects.pinned_context.journal_authentication_key_role", "one fixed journal role")
semantic_pair(19, "objects.state_authority_head_evidence.state_authority_authentication_key_role", "objects.pinned_context.state_authority_authentication_key_role", "one fixed authority role")
for field in ["journal_id_token", "journal_epoch", "external_anchor_identity_sha256", "external_anchor_profile_sha256", "pinned_context_sha256", "external_anchor_authentication_key_role", "singleton_registration_sha256"]:
    right = f"objects.pinned_context.{field}" if field in objects["pinned_context"]["field_order"] else f"objects.singleton_registration.{field}"
    semantic_pair(20, f"objects.external_anchor_evidence.{field}", right, "external anchor exact registered technical identity/profile")
for anchor_field, authority_field, commit_field in [
    ("state_authority_monotonic_counter", "authority_monotonic_counter", "post_state_authority_counter"),
    ("committed_record_count", "committed_record_count", "committed_record_count"),
    ("journal_state_root_sha256", "head_journal_state_root_sha256", "committed_post_state_root_sha256"),
    ("journal_state_object_sha256", "head_journal_state_object_sha256", "committed_post_state_object_sha256"),
    ("head_sequence", "head_sequence", "committed_head_sequence"),
    ("head_receipt_hash_sha256", "head_receipt_hash_sha256", "committed_head_receipt_hash_sha256"),
    ("head_event_hash_sha256", "head_event_hash_sha256", "committed_head_event_hash_sha256"),
]:
    semantic_pair(21, f"objects.external_anchor_evidence.{anchor_field}", f"objects.state_authority_head_evidence.{authority_field}", "anchor equals authority preimage")
    semantic_pair(21, f"objects.external_anchor_evidence.{anchor_field}", f"objects.commit_evidence.{commit_field}", "anchor equals commit post field")
semantic_pair(22, "objects.state_authority_head_evidence.external_anchor_root_sha256", "objects.external_anchor_evidence.external_anchor_root_sha256", "authority root is exact recursively validated anchor object root")
semantic_pair(23, "objects.external_anchor_evidence.prior_external_anchor_root_sha256", "objects.commit_evidence.pre_external_anchor_root_sha256", "post anchor prior is exact pre anchor")
semantic_pair(23, "objects.external_anchor_evidence.anchor_monotonic_counter", "checked_plus_one(instances.current_pre_external_anchor_evidence.anchor_monotonic_counter)", "checked increment from exact registered-genesis normal or failure predecessor projection; overflow refuses")
for field in ["external_anchor_identity_sha256", "external_anchor_profile_sha256", "external_anchor_authentication_key_role"]:
    semantic_pair(24, f"objects.external_anchor_evidence.{field}", f"objects.pinned_context.{field}", "proof verifier fixed public input/profile/role")

# Rules 25-28: final roots and exact registered-genesis bridge.
for row in root_repeat_rows:
    semantic_pair(25, row["left_path"], row["right_path"], row["condition"])
for object_name, count_field, root_field, object_field in [
    ("proof_public_inputs", "expected_pre_record_count", "expected_pre_journal_state_root_sha256", "expected_pre_journal_state_object_sha256"),
    ("receipt", "expected_pre_record_count", "expected_pre_journal_state_root_sha256", "expected_pre_journal_state_object_sha256"),
    ("event", "expected_pre_record_count", "expected_pre_journal_state_root_sha256", "expected_pre_journal_state_object_sha256"),
    ("transition_request", "pre_record_count", "pre_journal_state_root_sha256", "pre_journal_state_object_sha256"),
]:
    semantic_pair(26, f"objects.{object_name}.{root_field}", "objects.singleton_registration_full_genesis_bundle.genesis_journal_state_root_sha256", f"condition objects.{object_name}.{count_field} == 0")
    semantic_pair(26, f"objects.{object_name}.{object_field}", "objects.singleton_registration_full_genesis_bundle.genesis_journal_state_object_sha256", f"condition objects.{object_name}.{count_field} == 0")
semantic_pair(26, "objects.singleton_registration_full_genesis_bundle.genesis_external_anchor_root_sha256", "objects.genesis_external_anchor_evidence.genesis_external_anchor_root_sha256", "registered exact counter-zero anchor routed through the immutable full-genesis bundle")
semantic_pair(26, "objects.singleton_registration_full_genesis_bundle.genesis_state_authority_head_evidence_sha256", "objects.genesis_state_authority_evidence.genesis_state_authority_head_evidence_sha256", "registered exact counter-zero authority routed through the immutable full-genesis bundle")
# Rules 27 and 28 are represented by exact path/counter target rows in path_conditions; no untyped union exists.

# Rules 29-30: hiding output hashes and eight nonce terminal-output bindings.
semantic_pair(29, "objects.scope_precommitment.scope_commitment_bytes_sha256", "resolved(objects.scope_precommitment.generation_terminal_outcome_sha256).generated_output_sha256", "linked outcome SUCCESS and exact output role SCOPE_PRECOMMITMENT_COMMITMENT_BYTES")
semantic_pair(29, "objects.completeness_proof.proof_bytes_sha256", "resolved(objects.completeness_proof.generation_terminal_outcome_sha256).generated_output_sha256", "linked outcome SUCCESS and exact output role COMPLETENESS_PROOF_BYTES")
for object_name, nonce_field in [
    ("authenticated_result", "verification_nonce"), ("verifier_evidence", "evidence_nonce"),
    ("token_accumulator_proof", "accumulator_proof_nonce"), ("journal_state", "state_nonce"),
    ("transition_request", "request_nonce"), ("commit_evidence", "commit_nonce"),
    ("state_authority_head_evidence", "authority_nonce"), ("external_anchor_evidence", "anchor_nonce"),
]:
    semantic_pair(30, f"SHA256(token256_bytes(objects.{object_name}.{nonce_field}))", f"resolved(objects.{object_name}.nonce_generation_terminal_outcome_sha256).generated_output_sha256", "exact SUCCESS terminal output for fixed field-path role")

semantic_non_pair_requirements = {
    27: "all first-transition versus later runtime target choices are exact path+counter conditions in path_qualified_sha256_target_partition; no caller schema union",
    28: "authority/anchor counter-one genesis and greater-than-one runtime predecessor choices are exact path+counter conditions in path_qualified_sha256_target_partition",
}

target_output_paths = {name: f"objects.{name}.{obj['field_order'][-1]}" for name, obj in objects.items()}
target_output_paths.update({
    "journal_state_root_preimage": "objects.journal_state.journal_state_root_sha256",
    "genesis_journal_state_root_preimage": "objects.genesis_journal_state.genesis_journal_state_root_sha256",
    "generation_reservation_ledger_state_root_preimage": "objects.generation_reservation_ledger_state.generation_reservation_ledger_state_root_sha256",
    "public_beacon_pre_reveal_state_root_preimage": "objects.public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_root_sha256",
    "generation_failure_journal_state_root_preimage": "objects.generation_failure_journal_state.generation_failure_journal_state_root_sha256",
})
link_hash_equality_rows = []
multi_instance_target_selectors = {
    "generation_reservation_ledger_state", "generation_reservation_ledger_state_root_preimage",
    "public_beacon_pre_reveal_state", "public_beacon_pre_reveal_state_root_preimage",
}
for object_name, obj in objects.items():
    for field, kind in zip(obj["field_order"], obj["field_types"]):
        path = f"objects.{object_name}.{field}"
        if kind not in {"sha256", "nullable_sha256"} or path in path_conditions or field not in exact:
            continue
        # This loop already excludes every path-conditioned occurrence, so its
        # physical link must use the preserved ordinary occurrence default.
        # The legacy field-name summary may be a structured non-executable
        # inventory for names that are conditioned at other paths.
        target = exact_occurrence_defaults[field]
        if target in multi_instance_target_selectors:
            # Exact pre/post instance rows are materialized separately. A generic
            # schema output is a type selector only and must never collapse two
            # distinct state instances into one physical equality class.
            continue
        if target in target_output_paths and path != target_output_paths[target]:
            link_hash_equality_rows.append({"left_path": path, "right_path": target_output_paths[target], "condition": "exact recursively byte-available target object/root selected by parent field role"})
pair_registry = {}
def register_pair(row, category):
    if "outer_path" in row:
        left_path, right_path = row["outer_path"], row["context_path"]
    else:
        left_path, right_path = row["left_path"], row["right_path"]
    canonical_key = tuple(sorted((left_path, right_path)))
    entry = pair_registry.setdefault(canonical_key, {
        "left_path": left_path,
        "right_path": right_path,
        "conditions": [],
        "categories": [],
        "semantic_rule_indices": [],
    })
    condition_text = row.get("condition", row.get("role_domain", "unconditional exact equality"))
    if condition_text not in entry["conditions"]:
        entry["conditions"].append(condition_text)
    if category not in entry["categories"]:
        entry["categories"].append(category)
    if "semantic_rule_index" in row and row["semantic_rule_index"] not in entry["semantic_rule_indices"]:
        entry["semantic_rule_indices"].append(row["semantic_rule_index"])
    if "outer_path" in row:
        entry.update({"outer_path": row["outer_path"], "context_path": row["context_path"], "target_class": row["target_class"], "role_domain": row["role_domain"]})

role_target_object_to_role = {row["target_resolution"]["target_object"]: row["role"] for row in output_role_table}
role_names = [row["role"] for row in output_role_table]
role_generic_prefix_to_alias = {
    f"objects.{schema_name}.": alias_name
    for schema_name, (alias_name, _) in role_alias_schema_map.items()
}
role_generic_prefix_to_alias.update({
    "instances.reservation_ledger_pre_state.": "ledger_pre_state",
    "instances.reservation_ledger_reserved_state.": "ledger_reserved_state",
    "instances.reservation_ledger_consumed_state.": "ledger_consumed_state",
    "instances.public_beacon_pre_reveal_pre_state.": "beacon_pre_state",
    "instances.public_beacon_pre_reveal_post_state.": "beacon_post_state",
})
multi_instance_generic_prefixes = {
    "objects.generation_reservation_ledger_state.",
    "objects.public_beacon_pre_reveal_state.",
}

def endpoint_variants(path, role):
    for prefix, alias_name in role_generic_prefix_to_alias.items():
        if prefix in path:
            return [path.replace(prefix, f"instances.roles.{role}.{alias_name}.")]
    if "objects.generation_reservation_ledger_state." in path:
        suffix = path.split("objects.generation_reservation_ledger_state.", 1)[1]
        return [
            f"instances.roles.{role}.{alias_name}.{suffix}"
            for alias_name in ["ledger_pre_state", "ledger_reserved_state", "ledger_consumed_state"]
        ]
    if "objects.public_beacon_pre_reveal_state." in path:
        suffix = path.split("objects.public_beacon_pre_reveal_state.", 1)[1]
        return [
            f"instances.roles.{role}.{alias_name}.{suffix}"
            for alias_name in ["beacon_pre_state", "beacon_post_state"]
        ]
    return [path]

def instantiate_physical_rows(rows):
    expanded = []
    for row in rows:
        if "outer_path" in row:
            expanded.append(row)
            continue
        left = row["left_path"]
        right = row["right_path"]
        combined = left + "\n" + right
        contains_role_generic = any(prefix in combined for prefix in role_generic_prefix_to_alias) or "objects.generation_reservation_ledger_state." in combined or "objects.public_beacon_pre_reveal_state." in combined
        contains_global_multi_instance = False
        if not contains_role_generic:
            expanded.append(row)
            continue
        inferred_roles = [
            role
            for target_object, role in role_target_object_to_role.items()
            if contains_role_generic and f"objects.{target_object}." in combined
        ]
        selected_roles = sorted(set(inferred_roles), key=role_names.index) if inferred_roles else (role_names if contains_role_generic else [role_names[0]])
        for role in selected_roles:
            for left_variant in endpoint_variants(left, role):
                for right_variant in endpoint_variants(right, role):
                    candidate = dict(row)
                    candidate["left_path"] = left_variant
                    candidate["right_path"] = right_variant
                    candidate["condition"] = f"output_role == {role}; {row.get('condition', 'exact instance equality')}" if contains_role_generic else row.get("condition", "exact instance equality")
                    expanded.append(candidate)
    return expanded

category_inputs = [
    ("namespace_to_context", instantiate_physical_rows(namespace_context_rows)),
    ("terminal_context_repeat", instantiate_physical_rows(repeated_terminal_rows)),
    ("context_and_registration_root_repeat", instantiate_physical_rows(root_repeat_rows)),
    ("outer_pin", outer_root_rows + terminal_outer_rows),
    ("registry_request_head_registration", instantiate_physical_rows(registry_equality_rows)),
    ("generation_reservation_ledger_outcome_anchor", instantiate_physical_rows(generation_equality_rows)),
    ("scalar_and_token_repeat", instantiate_physical_rows(scalar_repeat_rows)),
    ("sequence", instantiate_physical_rows(sequence_equality_rows)),
    ("recursive_hash_link", instantiate_physical_rows(link_hash_equality_rows)),
    ("event_receipt_state_semantic", instantiate_physical_rows(semantic_equality_rows)),
]
for category, rows in category_inputs:
    for row in rows:
        register_pair(row, category)
for row in role_conditioned_rows:
    if "right_path_by_output_role" in row:
        for output_role, right_path in row["right_path_by_output_role"].items():
            left_path = endpoint_variants(row["left_path"], output_role)[0]
            register_pair({"left_path": left_path, "right_path": right_path, "condition": f"output_role == {output_role}; {row['condition']}"}, "role_conditioned_profile")
    else:
        for expanded_row in instantiate_physical_rows([row]):
            register_pair(expanded_row, "role_conditioned_profile")

group_names = [category for category, _ in category_inputs] + ["role_conditioned_profile"]
physical_groups = {name: [] for name in group_names}
category_row_ids = {name: [] for name in group_names}
final_pairs = []
for pair_index, (canonical_key, row) in enumerate(sorted(pair_registry.items(), key=lambda item: item[0]), start=1):
    row["pair_id"] = f"EQ{pair_index:05d}"
    row["conditions"].sort()
    row["categories"].sort()
    row["semantic_rule_indices"].sort()
    final_pairs.append(row)
    for category in row["categories"]:
        category_row_ids[category].append(row["pair_id"])
    if "outer_pin" in row["categories"]:
        primary_group = "outer_pin"
    elif "role_conditioned_profile" in row["categories"]:
        primary_group = "role_conditioned_profile"
    elif row["semantic_rule_indices"]:
        primary_group = "event_receipt_state_semantic"
    else:
        primary_group = next(category for category in group_names if category in row["categories"])
    physical_groups[primary_group].append(row)

physical_pair_rows = [row for group in physical_groups.values() for row in group]
physical_keys = [tuple(sorted((row["left_path"], row["right_path"]))) for row in physical_pair_rows]
if len(physical_pair_rows) != len(pair_registry) or len(physical_keys) != len(set(physical_keys)):
    raise ValueError("physical equality pair duplicate gap or overlap")
for row in physical_pair_rows:
    endpoints = row["left_path"] + "\n" + row["right_path"]
    forbidden_generic_prefixes = set(role_generic_prefix_to_alias) | multi_instance_generic_prefixes
    if any(prefix in endpoints for prefix in forbidden_generic_prefixes):
        raise ValueError({"generic_multi_instance_equality_endpoint": row})
semantic_groups = []
for rule_index, exact_rule in enumerate(doc["event_receipt_journal_equality_rules"]):
    row_ids = [row["pair_id"] for row in final_pairs if rule_index in row["semantic_rule_indices"]]
    if not row_ids and rule_index not in semantic_non_pair_requirements:
        raise ValueError({"semantic_rule_without_materialized_pair_or_exact_nonpair": rule_index})
    semantic_groups.append({
        "rule_index": rule_index,
        "exact_rule": exact_rule,
        "pair_ids": row_ids,
        "exact_non_pair_requirement": semantic_non_pair_requirements.get(rule_index),
    })

doc["path_qualified_equality_closure"] = {
    "namespace_to_context_rows": physical_groups["namespace_to_context"],
    "terminal_context_repeat_rows": physical_groups["terminal_context_repeat"],
    "context_and_registration_root_repeat_rows": physical_groups["context_and_registration_root_repeat"],
    "outer_pin_rows": physical_groups["outer_pin"],
    "role_conditioned_profile_rows": physical_groups["role_conditioned_profile"],
    "registry_request_head_registration_rows": physical_groups["registry_request_head_registration"],
    "generation_reservation_ledger_outcome_anchor_rows": physical_groups["generation_reservation_ledger_outcome_anchor"],
    "scalar_and_token_repeat_rows": physical_groups["scalar_and_token_repeat"],
    "sequence_rows": physical_groups["sequence"],
    "recursive_hash_link_rows": physical_groups["recursive_hash_link"],
    "event_receipt_state_semantic_rows": physical_groups["event_receipt_state_semantic"],
    "category_row_ids": category_row_ids,
    "event_receipt_state_semantic_groups": semantic_groups,
    "total_explicit_path_pair_rows": len(physical_pair_rows),
    "physical_pair_row_count": len(physical_pair_rows),
    "duplicate_physical_pair_count": 0,
    "missing_required_pair_count": 0,
    "overlap_physical_pair_count": 0,
    "semantic_rule_count": len(semantic_groups),
    "semantic_rules_with_exact_non_pair_target_conditions": sorted(semantic_non_pair_requirements),
    "missing_or_duplicate_required_path_pair_count": 0,
}

doc["terminal_and_outer_pin_rules"] = {
    "inherited_v20_terminal_pin_count": 38,
    "terminal_static_technical_targets": terminal,
    "each_terminal_preimage_is_byte_available_exact_immutable_precommitted_content_independent_and_independently_audited": True,
    "outer_equality_bindings": outer_root_rows + terminal_outer_rows,
    "actual_implementation_live_authority_registry_beacon_generator_store_key_verifier_evidence_launcher_runner_and_outer_pin_values": None,
    "partial_local_substitute_rekey_fake_authority_or_mismatched_outer_pin_accepts": False,
}

doc["global_registry_recursion_rules"] = {
    "previous_head_is_exact_genesis_head_iff_prior_counter_zero": True,
    "counter_zero_prior_state": "exact finite-cardinality-one ten-field authoritative_registry_pre_state: six domain-derived constants, counter zero, and exact canonical pre_state_sha256; no legacy wrapper root, caller-selected state, or caller-selected head",
    "counter_positive_prior": "previous_head_sha256, registry pre-root, counter, and predecessor post-state hash resolve byte-for-byte to the unique independently current prior global_registry_post_head/global_registry_post_state; checked decreasing recursion and no sibling selection",
    "post_counter": "checked prior counter plus one; overflow refuses",
    "atomic_cas": "independently current authoritative registry pre-root changes to exactly one post-root; the typed sparse-map update/proof writes the exact acyclic assigned_value_root_sha256 at the namespace-derived slot and authenticates the completed registrar-signed request; post head and post state expose the sole next pre-state",
    "current_head_binding": "acceptance resolves exactly one typed global_registry_post_head and post-state; stale restored sibling head/state or alternate transition refuses",
    "request_head_registration_equalities": registry_equality_rows,
    "skip_rewind_transplant_cycle_alternate_genesis_or_sibling_allowed": False,
}
doc["reservation_ledger_recursion_rules"] = {
    "finite_base": "counter 0 exact generation_reservation_ledger_state with registered namespace context singleton registration exact ledger genesis manifest empty map root exact empty sequence-claim sentinels and UNCLAIMED; prior head null",
    "sequence_claim_acquisition": "before role zero, joint authoritative journal-store plus ledger CAS changes UNCLAIMED or prior RELEASED to HELD_UNTIL_SEQUENCE_COMMIT for exact checked next sequence and increments counter; every unrelated journal CAS is blocked until atomic final release",
    "reservation_transition": "exact current role slot UNASSIGNED to one RESERVED_ATTEMPT_ZERO post state; checked counter plus one; distinct ledger authority current-head query; active sequence claim slot statement and HELD state remain byte-identical",
    "terminal_transition": "exact current role slot RESERVED_ATTEMPT_ZERO to one CONSUMED_TERMINAL post state; checked counter plus one; distinct terminal authority current-head query; active sequence claim remains HELD",
    "sequence_claim_release": "normal commit after ten SUCCESS anchors or the one canonical pre-output technical-failure role-terminal-failure or hidden-refusal commit changes the same active claim HELD to RELEASED in the identical atomic journal CAS; ledger release signature is covered by journal commit signature/fixed-roster failure proof; no release occurs at a role terminal anchor or refusal evidence alone",
    "prior_head_selection": path_conditions,
    "slot_key_derivation": "exact domain NUL singleton registration NUL epoch-u64be NUL sequence-u64be NUL exact output-role ASCII",
    "anchor_statements_bind_full_transition": True,
    "restored_clone_sibling_retry_silence_second_outcome_rewind_skip_overflow_alternate_genesis_inter_role_cas_or_early_claim_release_allowed": False,
}
doc["public_beacon_pre_reveal_recursion_rules"] = {
    "finite_base": "exact typed public_beacon_pre_reveal_state counter zero derived from singleton registration, namespace/context, pinned beacon identity/profile/schedule, and public_beacon_pre_reveal_genesis_manifest_sha256; its committed_future_round_index allocation cursor is exactly uint64 zero",
    "first_transition": "prior evidence null; pre root/object/counter resolve to that one typed base; post counter checked one",
    "positive_recursion": "prior evidence byte-available; its post root/object/counter equal current pre root/object/counter; identities profiles schedule manifest context and registration invariant",
    "atomic_current_head": "beacon authority CAS authenticates exact pre-to-post state and current-head query equals this evidence hash; one successor per pre root; post committed_future_round_index is checked pre plus one and the schedule admits no independent allocation, making every role round strictly increasing future unused and unrevealed",
    "reveal_relation": "typed public_beacon_reveal_evidence verifies exact non-circular VRF input and returns exact output bytes whose SHA256 equals state/evidence committed hash and terminal copy",
    "deadline_substream": "terminal deadline indices are verified under a separate fixed domain-tagged terminal-clock VRF substream and never consume, collide with, or select a generation-round allocation cursor value",
    "restored_sibling_clone_alternate_base_skip_rewind_collision_past_round_late_reservation_or_second_successor_allowed": False,
}

for obj in objects.values():
    obj.pop("acyclic_stage", None)
dag_nodes = []
dag_schema_roles = {}
dag_edges = []
def add_dag_node(name, schema_objects=()):
    if name in dag_schema_roles:
        raise ValueError({"duplicate_dag_node": name})
    dag_nodes.append(name)
    dag_schema_roles[name] = list(schema_objects)
def add_dag_edge(left, right, reason, condition="always"):
    dag_edges.append((left, right, reason, condition))

for node_name, schema_names in [
    ("namespace_precommitment", ["namespace_precommitment"]),
    ("pinned_context", ["pinned_context"]),
    ("genesis_journal_state", ["genesis_journal_state"]),
    ("genesis_external_anchor_evidence", ["genesis_external_anchor_evidence"]),
    ("genesis_state_authority_evidence", ["genesis_state_authority_evidence"]),
    ("genesis_manifest", ["genesis_manifest"]),
    ("prior_global_registry_completed_request", ["singleton_registration_request"]),
    ("prior_global_registry_sparse_map_update", ["global_registry_sparse_map_update"]),
    ("prior_global_registry_post_head", ["global_registry_post_head"]),
    ("prior_global_registry_post_state", ["global_registry_post_state"]),
    ("prior_global_registry_singleton_registration", ["singleton_registration"]),
    ("prior_authoritative_registry_pre_state", ["authoritative_registry_pre_state"]),
    ("global_registry_pre_state", ["authoritative_registry_pre_state"]),
    ("singleton_registration_full_genesis_bundle", ["singleton_registration_full_genesis_bundle"]),
    ("registrar_policy_profile_bundle", ["registrar_policy_profile_bundle"]),
    ("registrar_authority_key_identity_bundle", ["registrar_authority_key_identity_bundle"]),
    ("singleton_registration_pre_request_payload", ["singleton_registration_pre_request_payload"]),
    ("singleton_registration_assigned_value", ["singleton_registration_assigned_value"]),
    ("singleton_registration_request", ["singleton_registration_request"]),
    ("global_registry_sparse_map_leaf", ["global_registry_sparse_map_leaf"]),
    ("global_registry_sparse_map_update", ["global_registry_sparse_map_update"]),
    ("global_registry_sparse_map_proof", ["global_registry_sparse_map_proof"]),
    ("global_registry_post_head", ["global_registry_post_head"]),
    ("global_registry_typed_post_state", ["global_registry_post_state"]),
    ("singleton_registration", ["singleton_registration"]),
    ("next_global_registry_pre_state", ["authoritative_registry_pre_state"]),
    ("reservation_ledger_counter_zero_state", ["generation_reservation_ledger_state"]),
    ("prior_normal_sequence_claim_release_commit", ["commit_evidence"]),
    ("current_normal_journal_state", ["journal_state"]),
    ("prior_normal_sequence_claim_release_state", ["generation_reservation_ledger_state"]),
    ("current_failure_record", ["generation_failure_record"]),
    ("current_failure_journal_state", ["generation_failure_journal_state"]),
    ("prior_failure_or_refusal_sequence_claim_release_commit", ["generation_failure_sequence_commit_evidence"]),
    ("current_failure_external_anchor_head_observation", ["failure_external_anchor_current_head_observation"]),
    ("current_failure_state_authority_head_observation", ["failure_state_authority_current_head_observation"]),
    ("prior_failure_or_refusal_sequence_claim_release_state", ["generation_reservation_ledger_state"]),
    ("independently_current_pre_journal_state", []),
    ("sequence_claim_acquire_pre_state", ["generation_reservation_ledger_state"]),
    ("sequence_claim_slot_and_statement", []),
    ("sequence_claim_acquire_post_state", ["generation_reservation_ledger_state"]),
    ("generation_sequence_transaction_claim_evidence", ["generation_sequence_transaction_claim_evidence"]),
    ("pre_output_complete_sequence_materialization_evidence", ["pre_witness_technical_health_evidence"]),
    ("public_beacon_pre_reveal_counter_zero_state", ["public_beacon_pre_reveal_state"]),
    ("prior_sequence_public_beacon_pre_reveal_post_state", ["public_beacon_pre_reveal_state"]),
    ("prior_sequence_public_beacon_pre_reveal_evidence", ["public_beacon_pre_reveal_evidence"]),
    ("independently_current_public_beacon_pre_reveal_state", ["public_beacon_pre_reveal_state"]),
]:
    add_dag_node(node_name, schema_names)

exclusive_recursive_dag_edge_conditions = {
    ("pinned_context", "global_registry_pre_state"): "instances.global_registry_pre_state.registry_counter == 0",
    ("prior_authoritative_registry_pre_state", "global_registry_pre_state"): "instances.global_registry_pre_state.registry_counter > 0",
    ("singleton_registration", "independently_current_pre_journal_state"): "instances.current_pre_journal_state.state_kind == REGISTERED_GENESIS",
    ("current_normal_journal_state", "independently_current_pre_journal_state"): "instances.current_pre_journal_state.state_kind == NORMAL_MEMORY_RECORD_STATE",
    ("current_failure_state_authority_head_observation", "independently_current_pre_journal_state"): "instances.current_pre_journal_state.state_kind == GENERATION_FAILURE_STATE",
    ("reservation_ledger_counter_zero_state", "sequence_claim_acquire_pre_state"): "instances.sequence_claim_acquire_pre_state.reservation_ledger_counter == 0 and instances.sequence_claim_acquire_pre_state.sequence_transaction_claim_state == UNCLAIMED",
    ("prior_normal_sequence_claim_release_state", "sequence_claim_acquire_pre_state"): "instances.sequence_claim_acquire_pre_state.reservation_ledger_counter > 0 and instances.current_pre_journal_state.state_kind == NORMAL_MEMORY_RECORD_STATE and instances.prior_normal_sequence_claim_release_state.sequence_transaction_claim_state == RELEASED_BY_EXACT_SEQUENCE_COMMIT",
    ("prior_failure_or_refusal_sequence_claim_release_state", "sequence_claim_acquire_pre_state"): "instances.sequence_claim_acquire_pre_state.reservation_ledger_counter > 0 and instances.current_pre_journal_state.state_kind == GENERATION_FAILURE_STATE and instances.prior_failure_sequence_claim_release_commit.failure_trigger in {PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,ROLE_TERMINAL_FAILED,HIDDEN_LIFECYCLE_REFUSAL} and instances.prior_failure_sequence_claim_release_state.sequence_transaction_claim_state == RELEASED_BY_EXACT_SEQUENCE_COMMIT",
    ("current_failure_state_authority_head_observation", "sequence_claim_slot_and_statement"): "instances.current_pre_journal_state.state_kind == GENERATION_FAILURE_STATE",
    ("public_beacon_pre_reveal_counter_zero_state", "independently_current_public_beacon_pre_reveal_state"): "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_counter == 0",
    ("prior_sequence_public_beacon_pre_reveal_evidence", "independently_current_public_beacon_pre_reveal_state"): "instances.current_public_beacon_pre_reveal_state.public_beacon_pre_reveal_state_counter > 0",
}
for left, right, reason in [
    ("namespace_precommitment", "pinned_context", "context hashes exact namespace precommitment"),
    ("pinned_context", "genesis_journal_state", "typed genesis consumes final context"),
    ("genesis_journal_state", "genesis_external_anchor_evidence", "genesis anchor consumes exact state"),
    ("genesis_external_anchor_evidence", "genesis_state_authority_evidence", "genesis authority consumes exact anchor"),
    ("genesis_state_authority_evidence", "genesis_manifest", "manifest consumes complete typed genesis"),
    ("pinned_context", "global_registry_pre_state", "counter-zero branch supplies the exact pinned authoritative registry genesis pre-state"),
    ("prior_global_registry_completed_request", "prior_global_registry_sparse_map_update", "positive recursion prior update consumes the exact prior completed request"),
    ("prior_global_registry_completed_request", "prior_global_registry_post_head", "positive recursion prior post head authenticates the exact prior completed request"),
    ("prior_global_registry_sparse_map_update", "prior_global_registry_post_head", "positive recursion prior post head authenticates the exact prior sparse-map update"),
    ("prior_global_registry_completed_request", "prior_global_registry_post_state", "positive recursion prior typed post state authenticates the exact prior completed request"),
    ("prior_global_registry_sparse_map_update", "prior_global_registry_post_state", "positive recursion prior typed post state authenticates the exact prior sparse-map update"),
    ("prior_global_registry_post_head", "prior_global_registry_post_state", "positive recursion prior typed post state consumes the exact prior post head"),
    ("prior_global_registry_completed_request", "prior_global_registry_singleton_registration", "positive recursion prior final registration consumes the exact prior completed request"),
    ("prior_global_registry_sparse_map_update", "prior_global_registry_singleton_registration", "positive recursion prior final registration consumes the exact prior sparse-map update"),
    ("prior_global_registry_post_head", "prior_global_registry_singleton_registration", "positive recursion prior final registration consumes the exact prior post head"),
    ("prior_global_registry_post_state", "prior_global_registry_singleton_registration", "positive recursion predecessor registration consumes the exact prior typed post-state"),
    ("prior_global_registry_completed_request", "prior_authoritative_registry_pre_state", "literal V7 positive origin: prior completed request supplies namespace and context"),
    ("prior_global_registry_sparse_map_update", "prior_authoritative_registry_pre_state", "literal V7 positive origin: prior update supplies root and checked counter"),
    ("prior_global_registry_post_head", "prior_authoritative_registry_pre_state", "literal V7 positive origin: prior post head supplies the authoritative head hash"),
    ("prior_global_registry_post_state", "prior_authoritative_registry_pre_state", "positive recursion predecessor post-state supplies the exact root counter head and state object"),
    ("prior_global_registry_singleton_registration", "prior_authoritative_registry_pre_state", "positive recursion predecessor registration supplies the exact namespace context and registration hash"),
    ("prior_authoritative_registry_pre_state", "global_registry_pre_state", "positive recursion resolves the independently current authoritative pre-state from the exact checked predecessor"),
    ("genesis_manifest", "singleton_registration_full_genesis_bundle", "full-genesis bundle closes the exact counter-zero journal anchor authority and manifest roots"),
    ("pinned_context", "registrar_policy_profile_bundle", "policy/profile bundle resolves only namespace-precommitted registrar policy and authentication profiles"),
    ("pinned_context", "registrar_authority_key_identity_bundle", "authority bundle resolves exactly one registrar identity key registry identifier and public key"),
    ("singleton_registration_full_genesis_bundle", "singleton_registration_pre_request_payload", "acyclic pre-request payload consumes the full genesis root"),
    ("registrar_policy_profile_bundle", "singleton_registration_pre_request_payload", "acyclic pre-request payload consumes the exact policy/profile bundle"),
    ("registrar_authority_key_identity_bundle", "singleton_registration_pre_request_payload", "acyclic pre-request payload consumes the exact authority/key/identity bundle"),
    ("singleton_registration_pre_request_payload", "singleton_registration_assigned_value", "assigned leaf value is derived before request signing and contains no registry post value"),
    ("singleton_registration_assigned_value", "singleton_registration_request", "completed registrar-signed request binds the exact acyclic assigned value"),
    ("singleton_registration_request", "global_registry_sparse_map_leaf", "typed sparse-map leaf carries the exact signed request and assigned value"),
    ("global_registry_pre_state", "global_registry_sparse_map_update", "update consumes the independently current registry pre-root and counter"),
    ("global_registry_sparse_map_leaf", "global_registry_sparse_map_update", "update writes exactly the typed ABSENT-to-assigned leaf"),
    ("global_registry_sparse_map_update", "global_registry_sparse_map_proof", "proof authenticates the exact checked sparse-map update"),
    ("global_registry_sparse_map_proof", "global_registry_post_head", "one typed post head hashes the exact leaf update proof post root and counter"),
    ("global_registry_post_head", "global_registry_typed_post_state", "typed post state consumes the one authoritative post head"),
    ("global_registry_typed_post_state", "next_global_registry_pre_state", "the typed post root counter head and post-state object become the sole next authoritative registry pre-state"),
    ("global_registry_typed_post_state", "singleton_registration", "final registration consumes the typed post state directly"),
    ("global_registry_post_head", "singleton_registration", "final registration consumes the one typed post head directly"),
    ("genesis_manifest", "singleton_registration", "registration is only genesis bridge"),
    ("singleton_registration", "next_global_registry_pre_state", "next authoritative pre-state names the exact completed singleton registration and cannot exist before it"),
    ("singleton_registration", "reservation_ledger_counter_zero_state", "registered exact finite ledger base"),
    ("reservation_ledger_counter_zero_state", "sequence_claim_acquire_pre_state", "counter-zero branch directly supplies the exact registered ledger base"),
    ("prior_normal_sequence_claim_release_commit", "prior_normal_sequence_claim_release_state", "prior normal commit hashes and releases exactly one typed claim ledger post-state"),
    ("prior_normal_sequence_claim_release_commit", "current_normal_journal_state", "the independently current prior normal commit resolves one exact typed prior-transaction post journal-state instance and cannot resolve the later role target"),
    ("prior_normal_sequence_claim_release_state", "sequence_claim_acquire_pre_state", "positive normal branch directly supplies the exact prior commit_evidence RELEASED post state through checked decreasing sequence recursion"),
    ("current_failure_record", "current_failure_journal_state", "the typed prior-sequence failure/refusal record deterministically creates the exact current failure journal state"),
    ("current_failure_record", "prior_failure_or_refusal_sequence_claim_release_commit", "the prior-sequence failure/refusal commit authenticates the exact record branch role index and occupied sequence"),
    ("current_failure_journal_state", "prior_failure_or_refusal_sequence_claim_release_commit", "the prior-sequence failure/refusal commit consumes the exact typed failure journal state that becomes the current journal predecessor"),
    ("prior_failure_or_refusal_sequence_claim_release_commit", "current_failure_external_anchor_head_observation", "before a new claim, an independent anchor observer authenticates the exact prior-sequence completed failure/refusal successor"),
    ("current_failure_external_anchor_head_observation", "current_failure_state_authority_head_observation", "the independent authority observer consumes the same prior-sequence anchor observation and successor tuple"),
    ("prior_failure_or_refusal_sequence_claim_release_commit", "prior_failure_or_refusal_sequence_claim_release_state", "prior failure/refusal commit hashes and releases exactly one typed claim ledger post-state"),
    ("prior_failure_or_refusal_sequence_claim_release_state", "sequence_claim_acquire_pre_state", "positive failure/refusal branch directly supplies the exact prior failure_commit RELEASED post state through checked decreasing sequence recursion"),
    ("singleton_registration", "independently_current_pre_journal_state", "REGISTERED_GENESIS branch authenticates the complete journal authority anchor tuple through the exact singleton full-genesis bundle"),
    ("current_normal_journal_state", "independently_current_pre_journal_state", "NORMAL_MEMORY_RECORD_STATE branch authenticates the exact typed prior journal object while its independently current prior commit fixes the complete journal authority anchor tuple"),
    ("current_failure_state_authority_head_observation", "independently_current_pre_journal_state", "GENERATION_FAILURE_STATE branch authenticates the complete failure journal authority anchor tuple from the independently current prior-sequence observations"),
    ("independently_current_pre_journal_state", "sequence_claim_acquire_pre_state", "claim acquisition selects its ledger predecessor only after the current pre-journal state kind and complete authority anchor snapshot are authenticated"),
    ("sequence_claim_acquire_pre_state", "sequence_claim_slot_and_statement", "derive exact sequence-claim slot and acyclic statement from current journal/authority/anchor plus ledger pre-state"),
    ("independently_current_pre_journal_state", "sequence_claim_slot_and_statement", "the acyclic claim statement consumes the already authenticated complete current journal authority anchor projection before completed claim evidence exists"),
    ("current_failure_state_authority_head_observation", "sequence_claim_slot_and_statement", "GENERATION_FAILURE_STATE branch derives the next claim statement only after both prior-sequence current-head observations are byte-available and physically bound"),
    ("sequence_claim_slot_and_statement", "sequence_claim_acquire_post_state", "HELD post ledger state embeds the already derived claim slot and statement"),
    ("sequence_claim_acquire_post_state", "generation_sequence_transaction_claim_evidence", "completed two-authority proof authenticates the already byte-available HELD post ledger state"),
    ("generation_sequence_transaction_claim_evidence", "pre_output_complete_sequence_materialization_evidence", "before any beacon allocation, exact health availability recovery and every later byte materializer commit to total sequence closure"),
    ("singleton_registration", "public_beacon_pre_reveal_counter_zero_state", "registered exact finite beacon-head base"),
    ("public_beacon_pre_reveal_counter_zero_state", "independently_current_public_beacon_pre_reveal_state", "counter-zero branch supplies the exact registered sentinel base"),
    ("prior_sequence_public_beacon_pre_reveal_post_state", "prior_sequence_public_beacon_pre_reveal_evidence", "positive branch prior evidence hashes and authenticates the exact byte-available prior-sequence post state"),
    ("prior_sequence_public_beacon_pre_reveal_evidence", "independently_current_public_beacon_pre_reveal_state", "positive branch resolves the independently current prior evidence post root object counter and allocation map through checked decreasing recursion"),
]:
    add_dag_edge(left, right, reason, exclusive_recursive_dag_edge_conditions.get((left, right), "always"))

role_prerequisite_node = {
    "SCOPE_PRECOMMITMENT_COMMITMENT_BYTES": "singleton_registration",
    "COMPLETENESS_PROOF_BYTES": "proof_public_inputs",
    "AUTHENTICATED_RESULT_VERIFICATION_NONCE": "target.COMPLETENESS_PROOF_BYTES",
    "VERIFIER_EVIDENCE_EVIDENCE_NONCE": "target.AUTHENTICATED_RESULT_VERIFICATION_NONCE",
    "TOKEN_ACCUMULATOR_PROOF_NONCE": "event",
    "JOURNAL_STATE_STATE_NONCE": "target.TOKEN_ACCUMULATOR_PROOF_NONCE",
    "TRANSITION_REQUEST_REQUEST_NONCE": "target.JOURNAL_STATE_STATE_NONCE",
    "EXTERNAL_ANCHOR_EVIDENCE_ANCHOR_NONCE": "target.TRANSITION_REQUEST_REQUEST_NONCE",
    "STATE_AUTHORITY_EVIDENCE_AUTHORITY_NONCE": "target.EXTERNAL_ANCHOR_EVIDENCE_ANCHOR_NONCE",
    "COMMIT_EVIDENCE_COMMIT_NONCE": "target.STATE_AUTHORITY_EVIDENCE_AUTHORITY_NONCE",
}
target_schema_by_role = {row["role"]: row["target_resolution"]["target_object"] for row in output_role_table}
prior_ledger_state_node = "sequence_claim_acquire_post_state"
prior_beacon_state_node = "independently_current_public_beacon_pre_reveal_state"
role_instance_rows = []
for role in role_lifecycle_order:
    prefix = f"role.{role}"
    nodes = {
        "ledger_pre_state": f"{prefix}.reservation_ledger_pre_state",
        "beacon_pre_state": f"{prefix}.public_beacon_pre_reveal_pre_state",
        "beacon_post_state": f"{prefix}.public_beacon_pre_reveal_post_state",
        "pre_reveal_evidence": f"{prefix}.pre_reveal_evidence",
        "reservation": f"{prefix}.generation_reservation",
        "reserved_state": f"{prefix}.reservation_ledger_reserved_state",
        "ledger_evidence": f"{prefix}.reservation_ledger_evidence",
        "order": f"{prefix}.reservation_before_reveal_order",
        "availability_commitment": f"{prefix}.producer_availability_commitment",
        "availability_evidence": f"{prefix}.producer_availability_evidence",
        "reveal": f"{prefix}.public_beacon_reveal_evidence",
        "lifecycle_refusal": f"{prefix}.hidden_lifecycle_refusal_if_boundary_refuses",
        "output_attempt": f"{prefix}.output_attempt_or_exact_absent",
        "deadline": f"{prefix}.terminal_deadline_observation",
        "outcome": f"{prefix}.terminal_outcome",
        "consumed_state": f"{prefix}.reservation_ledger_consumed_state",
        "anchor": f"{prefix}.terminal_anchor",
        "failure_record": f"{prefix}.failure_record_if_FAILED",
        "failure_state": f"{prefix}.failure_journal_state_if_FAILED",
        "failure_anchor_statement": f"{prefix}.failure_external_anchor_successor_statement_if_FAILED",
        "failure_anchor_proof": f"{prefix}.failure_external_anchor_successor_proof_if_FAILED",
        "failure_anchor_root": f"{prefix}.failure_external_anchor_successor_root_if_FAILED",
        "failure_authority_statement": f"{prefix}.failure_state_authority_successor_statement_if_FAILED",
        "failure_authority_signature": f"{prefix}.failure_state_authority_successor_signature_if_FAILED",
        "failure_authority_head": f"{prefix}.failure_state_authority_successor_head_if_FAILED",
        "failure_claim_release_post_state": f"{prefix}.sequence_claim_release_post_state_if_FAILED",
        "failure_claim_release_signature": f"{prefix}.sequence_claim_release_signature_if_FAILED",
        "failure_commit": f"{prefix}.failure_sequence_commit_if_FAILED",
        "failure_anchor_current_head_observation": f"{prefix}.failure_external_anchor_current_head_observation_if_SELECTED_RELEASE",
        "failure_authority_current_head_observation": f"{prefix}.failure_state_authority_current_head_observation_if_SELECTED_RELEASE",
        "target": f"target.{role}",
    }
    if role == "COMMIT_EVIDENCE_COMMIT_NONCE":
        nodes.update({
            "normal_claim_release_post_state": f"{prefix}.sequence_claim_release_post_state_if_all_SUCCESS",
            "normal_claim_release_signature": f"{prefix}.sequence_claim_release_signature_if_all_SUCCESS",
        })
    for key, schema_names in [
        ("ledger_pre_state", ["generation_reservation_ledger_state"]),
        ("beacon_pre_state", ["public_beacon_pre_reveal_state"]),
        ("beacon_post_state", ["public_beacon_pre_reveal_state"]),
        ("pre_reveal_evidence", ["public_beacon_pre_reveal_evidence"]),
        ("reservation", ["generation_reservation"]),
        ("reserved_state", ["generation_reservation_ledger_state"]),
        ("ledger_evidence", ["generation_reservation_ledger_evidence"]),
        ("order", ["beacon_reservation_order_evidence"]),
        ("availability_commitment", ["role_producer_availability_commitment"]),
        ("availability_evidence", ["role_producer_availability_evidence"]),
        ("reveal", ["public_beacon_reveal_evidence"]),
        ("lifecycle_refusal", ["generation_sequence_lifecycle_refusal_evidence"]),
        ("output_attempt", []),
        ("deadline", ["terminal_deadline_observation_evidence"]),
        ("outcome", ["generation_terminal_outcome"]),
        ("consumed_state", ["generation_reservation_ledger_state"]),
        ("anchor", ["generation_terminal_anchor_evidence"]),
        ("failure_record", ["generation_failure_record"]),
        ("failure_state", ["generation_failure_journal_state"]),
        ("failure_anchor_statement", []),
        ("failure_anchor_proof", []),
        ("failure_anchor_root", []),
        ("failure_authority_statement", []),
        ("failure_authority_signature", []),
        ("failure_authority_head", []),
        ("failure_claim_release_post_state", ["generation_reservation_ledger_state"]),
        ("failure_claim_release_signature", []),
        ("failure_commit", ["generation_failure_sequence_commit_evidence"]),
        ("failure_anchor_current_head_observation", ["failure_external_anchor_current_head_observation"]),
        ("failure_authority_current_head_observation", ["failure_state_authority_current_head_observation"]),
    ]:
        add_dag_node(nodes[key], schema_names)
    if role == "COMMIT_EVIDENCE_COMMIT_NONCE":
        add_dag_node(nodes["normal_claim_release_post_state"], ["generation_reservation_ledger_state"])
        add_dag_node(nodes["normal_claim_release_signature"], [])
    add_dag_node(nodes["target"], [target_schema_by_role[role]])
    prerequisite = role_prerequisite_node[role]
    for left, right, reason in [
        (prior_ledger_state_node, nodes["ledger_pre_state"], "role alias resolves the exact independently current ledger pre-state instance"),
        (prior_beacon_state_node, nodes["beacon_pre_state"], "role alias resolves the exact independently current beacon pre-state instance"),
        (nodes["beacon_pre_state"], nodes["beacon_post_state"], "atomic pre-reveal CAS creates the exact byte-available role post-state"),
        (nodes["beacon_pre_state"], nodes["pre_reveal_evidence"], "signed evidence hashes the exact role pre-state object"),
        (nodes["beacon_post_state"], nodes["pre_reveal_evidence"], "signed evidence hashes the exact role post-state object and dynamic commitment tuple"),
        ("generation_sequence_transaction_claim_evidence", nodes["pre_reveal_evidence"], "one sequence-wide journal lock is already HELD before this role's beacon allocation and remains equality-bound"),
        ("pre_output_complete_sequence_materialization_evidence", nodes["pre_reveal_evidence"], "one fixed pre-output materializer and recovery roster makes this one-use allocation and its complete role closure mandatory before any output is known"),
        (prerequisite, nodes["pre_reveal_evidence"], "fixed lifecycle prerequisite before role reservation"),
        (prerequisite, nodes["lifecycle_refusal"], "if and only if the exact next V19 closure/erasure boundary cannot complete, one generic hidden refusal is materialized before this role allocation"),
        ("pre_output_complete_sequence_materialization_evidence", nodes["lifecycle_refusal"], "hidden refusal is emitted only by the pre-output committed total state machine and introduces no post-output abort choice"),
        (nodes["pre_reveal_evidence"], nodes["reservation"], "reservation commits unrevealed round"),
        (nodes["ledger_pre_state"], nodes["reservation"], "reservation consumes the exact role-qualified independently current ledger state"),
        (nodes["reservation"], nodes["reserved_state"], "atomic UNASSIGNED to RESERVED state"),
        (nodes["ledger_pre_state"], nodes["ledger_evidence"], "ledger evidence consumes exact role-qualified pre-state"),
        (nodes["reservation"], nodes["ledger_evidence"], "ledger evidence authenticates exact reservation"),
        (nodes["reserved_state"], nodes["ledger_evidence"], "ledger evidence authenticates exact reserved state"),
        (nodes["ledger_evidence"], nodes["order"], "cross-system order consumes committed reservation"),
        (nodes["pre_reveal_evidence"], nodes["order"], "order proves same round still pre-reveal"),
        (nodes["order"], nodes["availability_commitment"], "same-role availability commitment is fixed after the exact reservation and order proof but before reveal"),
        (nodes["reserved_state"], nodes["availability_commitment"], "availability commitment binds the exact same-role reservation-ledger post state"),
        (nodes["beacon_post_state"], nodes["availability_commitment"], "availability commitment binds the exact same-role allocation post state"),
        ("pre_output_complete_sequence_materialization_evidence", nodes["availability_commitment"], "role availability is a projection of the pre-output fixed complete materializer and introduces no new result"),
        (nodes["availability_commitment"], nodes["availability_evidence"], "authenticated availability evidence consumes the exact same-role commitment observation and result"),
        (nodes["availability_evidence"], nodes["reveal"], "public output is revealed only after the same-role producer availability result is immutably authenticated"),
        (nodes["order"], nodes["reveal"], "typed VRF reveal occurs after reservation order"),
        (nodes["reveal"], nodes["output_attempt"], "the pre-output committed materializer consumes the exact verified or recovered public seed and emits the one role output"),
        ("pre_output_complete_sequence_materialization_evidence", nodes["output_attempt"], "all generator target signer proof and recovery bytes were entrusted before reveal"),
        (nodes["output_attempt"], nodes["deadline"], "deadline observation follows one-shot attempt/absence"),
        ("pre_output_complete_sequence_materialization_evidence", nodes["deadline"], "deadline VRF output proof and recovery path were committed before generation output"),
        (nodes["deadline"], nodes["outcome"], "outcome materialized at exact deadline"),
        (nodes["output_attempt"], nodes["outcome"], "outcome binds exact output or null"),
        (nodes["outcome"], nodes["consumed_state"], "slot consumed on SUCCESS or FAILED"),
        (nodes["reserved_state"], nodes["anchor"], "terminal CAS starts at exact reserved state"),
        (nodes["consumed_state"], nodes["anchor"], "terminal authority authenticates exact consumed state"),
        (nodes["outcome"], nodes["anchor"], "terminal authority authenticates exact branch"),
        (nodes["anchor"], nodes["target"], "SUCCESS only creates exact target object"),
        (nodes["anchor"], nodes["failure_record"], "FAILED only creates canonical technical record"),
        (nodes["lifecycle_refusal"], nodes["failure_record"], "hidden post-claim integrity refusal creates the same sequence-consuming generic failure record without a role attempt"),
        (nodes["failure_record"], nodes["failure_state"], "failure record creates canonical advancing post-state"),
        (nodes["failure_state"], nodes["failure_anchor_statement"], "acyclic failure external-anchor successor statement consumes the completed failure state and prior anchor but not its future proof or root"),
        (nodes["failure_anchor_statement"], nodes["failure_anchor_proof"], "preserved external-anchor profile proves only the precomputed statement"),
        (nodes["failure_anchor_proof"], nodes["failure_anchor_root"], "post failure anchor root is derived after proof from exact statement plus proof bytes"),
        (nodes["failure_anchor_root"], nodes["failure_authority_statement"], "acyclic failure state-authority successor statement binds the already derived new anchor but not its future signature or head"),
        (nodes["failure_authority_statement"], nodes["failure_authority_signature"], "preserved state-authority profile signs only the precomputed statement"),
        (nodes["failure_authority_signature"], nodes["failure_authority_head"], "post failure authority head is derived after signature from exact statement plus signature bytes"),
        (nodes["consumed_state"], nodes["failure_claim_release_post_state"], "first-failed role consumed state is the exact held-claim release pre-state; constructing post bytes does not release the authoritative head"),
        (nodes["ledger_pre_state"], nodes["failure_claim_release_post_state"], "pre-output fixed failure or hidden lifecycle refusal releases from the exact never-reserved boundary ledger pre-state; claim remains held until final CAS"),
        (nodes["failure_record"], nodes["failure_claim_release_post_state"], "branch-exact failure record selects consumed-state versus never-reserved pre-state and fixes one release post-state"),
        (nodes["failure_claim_release_post_state"], nodes["failure_claim_release_signature"], "ledger authority signs exact HELD-to-RELEASED transition for inclusion in the same failure commit"),
        (nodes["failure_authority_head"], nodes["failure_claim_release_signature"], "failure release signature binds the completed authority/anchor successors and failure post-state"),
        (nodes["failure_state"], nodes["failure_commit"], "final fixed-roster journal CAS consumes exact failure state"),
        (nodes["failure_anchor_root"], nodes["failure_commit"], "final failure commit proof binds the already derived anchor successor root"),
        (nodes["failure_authority_head"], nodes["failure_commit"], "final failure commit proof binds the already derived authority successor head and releases the sequence claim atomically"),
        (nodes["failure_claim_release_signature"], nodes["failure_commit"], "same final failure proof makes journal advance and ledger claim release one atomic no-fork transaction"),
        (nodes["failure_commit"], nodes["failure_anchor_current_head_observation"], "after the atomic selected release the exact external-anchor successor is independently observed as current"),
        (nodes["failure_anchor_current_head_observation"], nodes["failure_authority_current_head_observation"], "authority current-head observation consumes the exact anchor observation and same completed failure successor"),
    ]:
        edge_condition = "always"
        if left == nodes["consumed_state"] and right == nodes["failure_claim_release_post_state"]:
            edge_condition = f"instances.roles.{role}.failure_record.failure_trigger == ROLE_TERMINAL_FAILED and instances.roles.{role}.failure_record.output_role == {role}"
        elif left == nodes["ledger_pre_state"] and right == nodes["failure_claim_release_post_state"]:
            hidden_refusal = (
                f"instances.roles.{role}.failure_record.failure_trigger == HIDDEN_LIFECYCLE_REFUSAL "
                f"and instances.roles.{role}.failure_record.output_role == {role}"
            )
            pre_output = (
                f" or instances.roles.{role}.failure_record.failure_trigger == PRE_OUTPUT_FIXED_TECHNICAL_FAILURE "
                f"and instances.roles.{role}.failure_record.output_role == {role}"
                if role == role_lifecycle_order[0] else ""
            )
            edge_condition = f"({hidden_refusal}{pre_output})"
        add_dag_edge(left, right, reason, edge_condition)
    if role == "SCOPE_PRECOMMITMENT_COMMITMENT_BYTES":
        add_dag_edge("pre_output_complete_sequence_materialization_evidence", nodes["failure_record"], "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE creates the role-zero boundary failure record directly; no beacon allocation reservation or role attempt exists")
    if role == "COMMIT_EVIDENCE_COMMIT_NONCE":
        add_dag_edge(nodes["anchor"], nodes["normal_claim_release_post_state"], "all ten SUCCESS anchors are available before the exact release post-state and final active-chain root")
        add_dag_edge(nodes["normal_claim_release_post_state"], nodes["normal_claim_release_signature"], "ledger authority signs exact HELD-to-RELEASED transition")
        add_dag_edge(nodes["anchor"], nodes["normal_claim_release_signature"], "release signature binds the complete ten-role SUCCESS barrier")
        add_dag_edge(nodes["normal_claim_release_signature"], nodes["target"], "the journal commit signature covers the release signature so journal CAS and claim release are atomic")
    role_instance_rows.append({
        "role": role,
        "role_index": role_lifecycle_order.index(role),
        "nodes": nodes,
        "prerequisite": prerequisite,
        "ledger_pre_state_node": prior_ledger_state_node,
        "beacon_pre_state_node": prior_beacon_state_node,
        "typed_alias_node_bindings": {
            "reservation": nodes["reservation"],
            "ledger_evidence": nodes["ledger_evidence"],
            "pre_reveal_evidence": nodes["pre_reveal_evidence"],
            "order": nodes["order"],
            "availability_commitment": nodes["availability_commitment"],
            "availability_evidence": nodes["availability_evidence"],
            "reveal": nodes["reveal"],
            "lifecycle_refusal": nodes["lifecycle_refusal"],
            "deadline": nodes["deadline"],
            "outcome": nodes["outcome"],
            "anchor": nodes["anchor"],
            "failure_record": nodes["failure_record"],
            "failure_state": nodes["failure_state"],
            "failure_commit": nodes["failure_commit"],
            "failure_anchor_current_head_observation": nodes["failure_anchor_current_head_observation"],
            "failure_authority_current_head_observation": nodes["failure_authority_current_head_observation"],
            "ledger_pre_state": nodes["ledger_pre_state"],
            "ledger_reserved_state": nodes["reserved_state"],
            "ledger_consumed_state": nodes["consumed_state"],
            "beacon_pre_state": nodes["beacon_pre_state"],
            "beacon_post_state": nodes["beacon_post_state"],
            "sequence_claim_failure_release_post_state": nodes["failure_claim_release_post_state"],
        },
        "exclusive_branch_rule": "at the fixed boundary exactly one branch exists: hidden lifecycle refusal before allocation; one preplanned role attempt whose SUCCESS creates target and permits the next role; or its unique fixed technical FAILED terminal. A pre-output fixed failure exists only at role zero before all role nodes. Every failure/refusal creates one sequence-level record/state/commit, closes the uncreated boundary/suffix through the deterministic barrier, and releases the held claim atomically",
    })
    prior_ledger_state_node = nodes["consumed_state"]
    prior_beacon_state_node = nodes["beacon_post_state"]
    if role == "SCOPE_PRECOMMITMENT_COMMITMENT_BYTES":
        add_dag_node("proof_public_inputs", ["proof_public_inputs"])
        add_dag_edge(nodes["target"], "proof_public_inputs", "public inputs consume exact completed scope precommitment")
    elif role == "VERIFIER_EVIDENCE_EVIDENCE_NONCE":
        add_dag_node("receipt", ["receipt"])
        add_dag_node("event", ["event"])
        add_dag_edge(nodes["target"], "receipt", "receipt consumes exact verifier evidence")
        add_dag_edge("receipt", "event", "event consumes exact receipt")
    elif role == "COMMIT_EVIDENCE_COMMIT_NONCE":
        add_dag_node("committed_envelope", ["committed_envelope"])
        add_dag_edge(nodes["target"], "committed_envelope", "envelope consumes exact commit evidence")

typed_global_alias_node_bindings = {
    "instances.prior_global_registry_completed_request": "prior_global_registry_completed_request",
    "instances.prior_global_registry_sparse_map_update": "prior_global_registry_sparse_map_update",
    "instances.prior_global_registry_post_head": "prior_global_registry_post_head",
    "instances.prior_global_registry_post_state": "prior_global_registry_post_state",
    "instances.prior_global_registry_singleton_registration": "prior_global_registry_singleton_registration",
    "instances.prior_authoritative_registry_pre_state": "prior_authoritative_registry_pre_state",
    "instances.global_registry_pre_state": "global_registry_pre_state",
    "instances.next_global_registry_pre_state": "next_global_registry_pre_state",
    "instances.active_generation_transaction_projection": "generation_sequence_transaction_claim_evidence",
    "instances.active_normal_transition_request": "target.TRANSITION_REQUEST_REQUEST_NONCE",
    "instances.active_normal_commit_evidence": "target.COMMIT_EVIDENCE_COMMIT_NONCE",
    "instances.current_post_journal_state": "target.JOURNAL_STATE_STATE_NONCE",
    "instances.current_pre_journal_state": "independently_current_pre_journal_state",
    "instances.current_pre_state_authority_evidence": "independently_current_pre_journal_state",
    "instances.current_pre_external_anchor_evidence": "independently_current_pre_journal_state",
    "instances.current_normal_journal_state": "current_normal_journal_state",
    "instances.sequence_claim_acquire_pre_state": "sequence_claim_acquire_pre_state",
    "instances.prior_normal_sequence_claim_release_commit": "prior_normal_sequence_claim_release_commit",
    "instances.prior_normal_sequence_claim_release_state": "prior_normal_sequence_claim_release_state",
    "instances.prior_failure_sequence_claim_release_commit": "prior_failure_or_refusal_sequence_claim_release_commit",
    "instances.prior_failure_sequence_claim_release_state": "prior_failure_or_refusal_sequence_claim_release_state",
    "instances.public_beacon_counter_zero_state": "public_beacon_pre_reveal_counter_zero_state",
    "instances.prior_sequence_public_beacon_pre_reveal_post_state": "prior_sequence_public_beacon_pre_reveal_post_state",
    "instances.prior_sequence_public_beacon_pre_reveal_evidence": "prior_sequence_public_beacon_pre_reveal_evidence",
    "instances.current_public_beacon_pre_reveal_state": "independently_current_public_beacon_pre_reveal_state",
    "instances.current_failure_record": "current_failure_record",
    "instances.current_failure_journal_state": "current_failure_journal_state",
    "instances.current_failure_sequence_commit": "prior_failure_or_refusal_sequence_claim_release_commit",
    "instances.current_failure_external_anchor_head_observation": "current_failure_external_anchor_head_observation",
    "instances.current_failure_state_authority_head_observation": "current_failure_state_authority_head_observation",
}

def alias_allowed_fields(alias_spec):
    allowed = set(alias_spec.get("logical_projection", {}))
    for projection in alias_spec.get("logical_field_projection_by_kind", {}).values():
        allowed.update(projection)
    schema_refs = []
    if "schema_object" in alias_spec:
        schema_refs.append(alias_spec["schema_object"])
    schema_refs.extend(alias_spec.get("schema_object_by_kind", {}).values())
    for schema_ref in schema_refs:
        schema_name = schema_ref.removeprefix("objects.")
        if schema_name not in objects:
            raise ValueError({"undefined_alias_schema_object": schema_ref})
        allowed.update(objects[schema_name]["field_order"])
    return allowed

def resolve_condition_field_path(path):
    object_match = re.fullmatch(r"objects\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)", path)
    if object_match:
        object_name, field_name = object_match.groups()
        return object_name in objects and field_name in objects[object_name]["field_order"]
    role_match = re.fullmatch(r"instances\.roles\.([A-Z0-9_]+)\.([a-z0-9_]+)\.([A-Za-z0-9_]+)", path)
    if role_match:
        role, alias_name, field_name = role_match.groups()
        alias_spec = role_instance_aliases.get(role, {}).get(alias_name)
        return alias_spec is not None and field_name in alias_allowed_fields(alias_spec)
    global_match = re.fullmatch(r"instances\.([a-z0-9_]+)\.([A-Za-z0-9_]+)", path)
    if global_match:
        alias_name, field_name = global_match.groups()
        alias_spec = instance_aliases.get(alias_name)
        return alias_spec is not None and field_name in alias_allowed_fields(alias_spec)
    return False

# Every executable nontrivial DAG predicate uses a deliberately small grammar:
# fully qualified typed field path, one comparison operator, and a fixed
# constant or fixed finite constant set.  Prose/bare fields and caller branch
# inputs cannot select a dependency.
dag_condition_comparison = re.compile(
    r"((?:objects|instances)\.[A-Za-z0-9_.]+)\s*(==|>|in)\s*(\{[A-Z0-9_,]+\}|[A-Z][A-Z0-9_]*|0)"
)
dag_condition_path_errors = []
dag_condition_operand_occurrences = []
for left, right, _, edge_condition in dag_edges:
    if edge_condition == "always":
        continue
    matches = dag_condition_comparison.findall(edge_condition)
    operator_count = sum(edge_condition.count(operator) for operator in [" == ", " > ", " in "])
    if not matches or len(matches) != operator_count:
        dag_condition_path_errors.append({"edge": [left, right], "condition": edge_condition, "reason": "condition is outside the exact fully qualified grammar"})
        continue
    for comparison_index, (field_path, operator, fixed_value) in enumerate(matches):
        if not resolve_condition_field_path(field_path):
            dag_condition_path_errors.append({"edge": [left, right], "condition": edge_condition, "undefined_field_path": field_path})
        else:
            dag_condition_operand_occurrences.append({
                "edge_from": left,
                "edge_to": right,
                "comparison_index": comparison_index,
                "field_path": field_path,
                "operator": operator,
                "fixed_value": fixed_value,
            })
if dag_condition_path_errors:
    raise ValueError({"invalid_dag_condition_field_paths": dag_condition_path_errors})

materialized_exclusive_recursive_edges = {
    (left, right): condition
    for left, right, _, condition in dag_edges
    if (left, right) in exclusive_recursive_dag_edge_conditions
}
if materialized_exclusive_recursive_edges != exclusive_recursive_dag_edge_conditions:
    raise ValueError({
        "exclusive_recursive_dag_edge_condition_gap": {
            "expected": exclusive_recursive_dag_edge_conditions,
            "actual": materialized_exclusive_recursive_edges,
        }
    })

dag_index = {name: index + 1 for index, name in enumerate(dag_nodes)}
bad_dag_edges = [(left, right, reason, condition) for left, right, reason, condition in dag_edges if dag_index[left] >= dag_index[right]]
if bad_dag_edges:
    raise ValueError({"non_forward_dag_edges": bad_dag_edges})

# A syntactically valid condition can still hide a backward dependency when its
# operand is produced by a later object.  Resolve every operand to the exact DAG
# node that authenticates it for this edge, add those dependencies to the same
# graph used for cycle/topological validation, and refuse same-stage, later,
# ambiguous, or missing producers.  For a branch-union target, the incoming
# branch source authenticates the projected target field; after the union is
# materialized, consumers use the bound selector node itself.
role_instance_row_by_role = {row["role"]: row for row in role_instance_rows}

def resolve_condition_operand_producer(field_path, edge_from, edge_to):
    role_match = re.fullmatch(r"instances\.roles\.([A-Z0-9_]+)\.([a-z0-9_]+)\.[A-Za-z0-9_]+", field_path)
    if role_match:
        role, alias_name = role_match.groups()
        row = role_instance_row_by_role.get(role)
        if row is None:
            return None, "unknown role"
        node = row["typed_alias_node_bindings"].get(alias_name)
        return (node, "role-qualified typed alias") if node else (None, "unbound role alias")

    global_match = re.fullmatch(r"instances\.([a-z0-9_]+)\.[A-Za-z0-9_]+", field_path)
    if global_match:
        alias_path = f"instances.{global_match.group(1)}"
        bound_node = typed_global_alias_node_bindings.get(alias_path)
        if bound_node is None:
            return None, "unbound global alias"
        if bound_node == edge_to:
            # The exact incoming branch source fixes this projected field before
            # the union node is materialized.  Physical branch equalities and the
            # source object's authenticated type make this non-caller-selected.
            return edge_from, "incoming authenticated branch projection"
        return bound_node, "typed global alias binding"

    object_match = re.fullmatch(r"objects\.([A-Za-z0-9_]+)\.[A-Za-z0-9_]+", field_path)
    if object_match:
        object_name = object_match.group(1)
        candidates = [node for node, schema_names in dag_schema_roles.items() if object_name in schema_names]
        if len(candidates) == 1:
            return candidates[0], "unique typed object node"
        return None, f"object producer cardinality {len(candidates)}"
    return None, "unsupported operand path"

condition_operand_dependency_edges = []
unresolved_condition_operand_dependencies = []
same_or_later_condition_operand_dependencies = []
for occurrence in dag_condition_operand_occurrences:
    producer_node, authentication = resolve_condition_operand_producer(
        occurrence["field_path"], occurrence["edge_from"], occurrence["edge_to"]
    )
    dependency = {
        **occurrence,
        "producer_node": producer_node,
        "producer_authentication": authentication,
        "producer_stage": dag_index.get(producer_node),
        "consumer_stage": dag_index[occurrence["edge_to"]],
    }
    condition_operand_dependency_edges.append(dependency)
    if producer_node is None or producer_node not in dag_index:
        unresolved_condition_operand_dependencies.append(dependency)
    elif dag_index[producer_node] >= dag_index[occurrence["edge_to"]]:
        same_or_later_condition_operand_dependencies.append(dependency)
if unresolved_condition_operand_dependencies or same_or_later_condition_operand_dependencies:
    raise ValueError({
        "unresolved_condition_operand_dependencies": unresolved_condition_operand_dependencies,
        "same_or_later_condition_operand_dependencies": same_or_later_condition_operand_dependencies,
    })

completed_claim_node = "generation_sequence_transaction_claim_evidence"
completed_claim_preclaim_condition_dependencies = [
    row for row in condition_operand_dependency_edges
    if row["producer_node"] == completed_claim_node
    and row["consumer_stage"] <= dag_index[completed_claim_node]
]
if completed_claim_preclaim_condition_dependencies:
    raise ValueError({"completed_claim_operand_in_preclaim_condition": completed_claim_preclaim_condition_dependencies})

actual_dependency_edge_pairs = sorted({
    *((left, right) for left, right, _, _ in dag_edges),
    *((row["producer_node"], row["edge_to"]) for row in condition_operand_dependency_edges),
}, key=lambda pair: (dag_index[pair[0]], dag_index[pair[1]], pair))
actual_dependency_successors = {node: [] for node in dag_nodes}
actual_dependency_indegree = {node: 0 for node in dag_nodes}
for left, right in actual_dependency_edge_pairs:
    actual_dependency_successors[left].append(right)
    actual_dependency_indegree[right] += 1
actual_dependency_ready = [node for node in dag_nodes if actual_dependency_indegree[node] == 0]
actual_dependency_visited = []
while actual_dependency_ready:
    node = actual_dependency_ready.pop(0)
    actual_dependency_visited.append(node)
    for successor in actual_dependency_successors[node]:
        actual_dependency_indegree[successor] -= 1
        if actual_dependency_indegree[successor] == 0:
            actual_dependency_ready.append(successor)
actual_dependency_cycle_residual = [node for node in dag_nodes if actual_dependency_indegree[node] != 0]
if actual_dependency_cycle_residual:
    raise ValueError({"actual_dependency_cycle_residual": actual_dependency_cycle_residual})
role_alias_instance_paths = {
    f"instances.roles.{role}.{alias_name}"
    for role, aliases in role_instance_aliases.items()
    for alias_name in aliases
}
materialized_role_alias_paths = {
    f"instances.roles.{row['role']}.{alias_name}"
    for row in role_instance_rows
    for alias_name in row["typed_alias_node_bindings"]
}
role_alias_instance_gaps = sorted(role_alias_instance_paths - materialized_role_alias_paths)
role_alias_instance_extras = sorted(materialized_role_alias_paths - role_alias_instance_paths)
if role_alias_instance_gaps or role_alias_instance_extras:
    raise ValueError({"dag_role_alias_instance_gaps": role_alias_instance_gaps, "dag_role_alias_instance_extras": role_alias_instance_extras})
covered_schema_names = {name for names in dag_schema_roles.values() for name in names}
if covered_schema_names != set(objects):
    raise ValueError({"dag_missing": sorted(set(objects) - covered_schema_names), "dag_extra": sorted(covered_schema_names - set(objects))})
doc["acyclic_singleton_and_generation_instance_dag"] = {
    "ordered_nodes": [{"stage": dag_index[name], "node": name, "schema_objects": dag_schema_roles[name]} for name in dag_nodes],
    "forward_edges": [{"from": left, "to": right, "reason": reason, "condition": condition} for left, right, reason, condition in dag_edges],
    "forward_edge_count": len(dag_edges),
    "role_specific_generation_instance_count": len(role_instance_rows),
    "role_specific_generation_instances": role_instance_rows,
    "typed_role_instance_alias_count": len(role_alias_instance_paths),
    "materialized_typed_role_instance_alias_count": len(materialized_role_alias_paths),
    "typed_role_instance_alias_gap_count": len(role_alias_instance_gaps),
    "typed_role_instance_alias_extra_count": len(role_alias_instance_extras),
    "typed_global_alias_node_bindings": typed_global_alias_node_bindings,
    "independently_current_pre_journal_state_selector": {
        "node": "independently_current_pre_journal_state",
        "typed_aliases": [
            "instances.current_pre_journal_state",
            "instances.current_pre_state_authority_evidence",
            "instances.current_pre_external_anchor_evidence",
        ],
        "authenticated_origin_by_state_kind": {
            "REGISTERED_GENESIS": "singleton_registration",
            "NORMAL_MEMORY_RECORD_STATE": "current_normal_journal_state",
            "GENERATION_FAILURE_STATE": "current_failure_state_authority_head_observation",
        },
        "origin_count": 3,
        "origins_are_exhaustive_mutually_exclusive_and_selected_only_by_authenticated_source_type": True,
        "complete_journal_authority_anchor_projection_is_physically_bound_forward_into_claim_evidence": True,
        "completed_claim_field_selects_preclaim_origin": False,
    },
    "condition_operand_dependency_edges": condition_operand_dependency_edges,
    "condition_operand_dependency_count": len(condition_operand_dependency_edges),
    "unresolved_condition_operand_dependency_count": len(unresolved_condition_operand_dependencies),
    "same_or_later_condition_operand_dependency_count": len(same_or_later_condition_operand_dependencies),
    "completed_claim_operand_in_preclaim_condition_count": len(completed_claim_preclaim_condition_dependencies),
    "actual_dependency_edges": [
        {"from": left, "to": right}
        for left, right in actual_dependency_edge_pairs
    ],
    "actual_dependency_edge_count": len(actual_dependency_edge_pairs),
    "actual_dependency_cycle_residual_count": len(actual_dependency_cycle_residual),
    "conditional_execution_semantics": "ordered_nodes is a static union of exclusive branches: claim acquisition post-state precedes the completed claim proof and one global pre-output health/materialization commitment; execution then instantiates each SUCCESS-prefix role until all ten targets/final commit, the unique first preplanned technical FAILED role, or one generic hidden lifecycle refusal before its boundary allocation. Pre-output fixed technical failure jumps directly to role-zero failure commit. No failed/refused target later role or second failure commit is instantiated",
    "first_failure_short_circuit_and_single_cas": True,
    "same_or_later_dependency_edge_count": len(bad_dag_edges) + len(same_or_later_condition_operand_dependencies),
    "schema_object_coverage_gap_count": 0,
    "dependency_edge_source": "typed object links + exact role target resolution + lifecycle prerequisites + state-instance aliases; all instantiated above rather than a generic runtime bucket",
    "explicit_recursive_edges": [
        "global registry head counter n -> prior head counter n-1; counter 0 -> exact typed genesis state",
        "reservation ledger counter n -> prior terminal head counter n-1; counter 0 -> exact typed empty state",
        "public beacon pre-reveal counter n -> prior head post state n-1; counter 0 -> exact typed manifest-derived state",
        "role zero current public-beacon state -> exclusive exact counter-zero base or independently current prior-sequence positive head; later roles -> immediately preceding role post-state",
        "sequence-claim acquisition pre-state -> exclusive registered empty base or exact prior normal/failure/refusal RELEASED post-state",
        "runtime journal authority and anchor counters -> exact registered genesis at one or exact typed predecessor at greater than one",
    ],
    "recursive_edges_must_strictly_decrease_checked_uint64_counter": True,
    "hash_cycle_or_same_stage_dependency_allowed": False,
}
doc.pop("acyclic_singleton_and_genesis_rules", None)
doc["token_nonce_rules_v21"] = {
    "v20_inherited_token256_field_type_occurrences": 51,
    "preserved_rule_for_43_non_nonce_inherited_occurrences": "fresh independent exact pinned CSPRNG 256-bit; nonsemantic nonderived content-unmapped; no caller entropy retry rejection sampling selective abort timing or content-dependent generation",
    "exact_eight_path_exception": "the eight adjacent nonce paths retain token256 syntax but are attempt-zero derived and mapped only to their exact fixed field-path terminal output under path_qualified_token256_semantics",
    "repeated_receipt_scope_proof_and_journal_id_tokens_are_byte-identical_at_all equality links": True,
    "eight_variant_affecting_adjacent_nonces_have_explicit_attempt_zero_reservation_and_terminal_outcome_fields": True,
    "all_other_tokens_and_nonces_are_generated_once under the same total attempt-zero no-silence profile before first retained use": True,
}

doc["recursive_preimage_rules"].update({
    "all_dynamic_schema_selection_is_parent_role_and_counter_conditioned_not_caller_selected": True,
    "all_retained_variant_control_role_round_seed_selection_branch_failure_timing_and_encoding_bytes_have_content_independent_attempt_zero_selection_evidence": True,
    "commitment_proof_and_success_output_hashes_may_depend_on_hidden_scope_or_witness_only_through_the_exact_randomized_hiding_relation_and_are_not_claimed_content_independent": True,
    "public_selection_transcript_cannot_recompute_or_test_private_commitment_or_proof_randomness": True,
    "missing_terminal_outcome_is_consumed_failure_not_retry_opportunity": True,
})
doc["current_implementation_or_evidence_materialized"] = False
doc["authority_ceiling"] = {
    "maximum_future_different_audit_ceiling": "ACCEPT_STATIC_MIND_CONTINUITY_V21_SINGLETON_GENESIS_UNIQUE_OUTPUTS_RESTORED_CONTENT_HIDING_DATA_ONLY_REQUIREMENTS_ONLY",
    "implementation_erasure_live_memory_consciousness_legal_personhood_body_biology_production_private_log_deployed_global_singleton_pending_action_or_root_go": False,
    "root_go": None,
}

serialized_doc = json.dumps(doc, ensure_ascii=False, allow_nan=False, indent=2) + "\n"

# Final executable endpoint and regression guard.  These checks deliberately
# operate on the rendered bytes rather than on selected construction tables so
# that an undefined path hidden in prose, a selector, or a copied rule cannot
# evade the same validation model advertised by the artifact.
forbidden_rendered_fragments = [
    "associated(",
    "associated_commit_evidence(",
    "associated_transition_request(",
    "associated_transition_request_post_state(",
    "independently_current_external_anchor_root_after_failure",
    "independently_current_state_authority_head_after_failure",
    "global_registry_head_evidence",
    "objects.global_registry_state",
    "global_registry_genesis_state_root_sha256",
    "resolved_unique(",
    "computed.",
]
present_forbidden_fragments = [fragment for fragment in forbidden_rendered_fragments if fragment in serialized_doc]
if present_forbidden_fragments:
    raise ValueError({"forbidden_untyped_or_obsolete_rendered_fragments": present_forbidden_fragments})

physical_pair_by_endpoints = {
    frozenset((row["left_path"], row["right_path"])): row
    for row in physical_pair_rows
}
def require_physical_pair(left_path, right_path):
    key = frozenset((left_path, right_path))
    if key not in physical_pair_by_endpoints:
        raise ValueError({"missing_required_literal_physical_pair": [left_path, right_path]})
    return physical_pair_by_endpoints[key]

for field_name in carried_with_assigned:
    for object_name in chain_objects:
        if field_name in objects[object_name]["field_order"]:
            require_physical_pair(
                f"objects.singleton_registration_request.{field_name}",
                f"objects.{object_name}.{field_name}",
            )
for role in role_lifecycle_order:
    release_row = require_physical_pair(
        f"instances.roles.{role}.failure_commit.sequence_claim_post_reservation_ledger_counter",
        f"instances.roles.{role}.sequence_claim_failure_release_post_state.reservation_ledger_counter",
    )
    release_conditions = " ".join(release_row["conditions"])
    if "ROLE_TERMINAL_FAILED" not in release_conditions or "HIDDEN_LIFECYCLE_REFUSAL" not in release_conditions:
        raise ValueError({"branch_incomplete_failure_release_pair": role})
    if role == role_lifecycle_order[0] and "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE" not in release_conditions:
        raise ValueError({"missing_pre_output_failure_release_pair": role})
for invariant_field in beacon_state_invariant_sources:
    require_physical_pair(
        f"instances.current_public_beacon_pre_reveal_state.{invariant_field}",
        f"instances.prior_sequence_public_beacon_pre_reveal_post_state.{invariant_field}",
    )
    require_physical_pair(
        f"instances.roles.{role_lifecycle_order[0]}.beacon_pre_state.{invariant_field}",
        f"instances.current_public_beacon_pre_reveal_state.{invariant_field}",
    )
require_physical_pair(
    "instances.prior_sequence_public_beacon_pre_reveal_evidence.public_beacon_pre_reveal_head_counter",
    "instances.prior_sequence_public_beacon_pre_reveal_post_state.public_beacon_pre_reveal_state_counter",
)
for prior_origin_source, prior_origin_target in [
    ("instances.prior_global_registry_completed_request.namespace_precommitment_sha256", "instances.prior_authoritative_registry_pre_state.namespace_precommitment_root_sha256"),
    ("instances.prior_global_registry_completed_request.pinned_context_sha256", "instances.prior_authoritative_registry_pre_state.pinned_context_root_sha256"),
    ("instances.prior_global_registry_sparse_map_update.registry_post_root_sha256", "instances.prior_authoritative_registry_pre_state.registry_root_sha256"),
    ("instances.prior_global_registry_sparse_map_update.registry_counter_after", "instances.prior_authoritative_registry_pre_state.registry_counter"),
    ("instances.prior_global_registry_post_head.global_registry_post_head_sha256", "instances.prior_authoritative_registry_pre_state.registry_head_sha256"),
]:
    require_physical_pair(prior_origin_source, prior_origin_target)

# V10: the state-kind that selects claim-acquisition recursion is a byte-
# available independently-current input, never a field first produced by the
# later completed claim evidence.  Exactly one of three authenticated origin
# types supplies the complete journal/authority/anchor selector.
selector_node = "independently_current_pre_journal_state"
selector_aliases = [
    "instances.current_pre_journal_state",
    "instances.current_pre_state_authority_evidence",
    "instances.current_pre_external_anchor_evidence",
]
if any(typed_global_alias_node_bindings.get(alias) != selector_node for alias in selector_aliases):
    raise ValueError({"current_pre_selector_alias_binding_gap": selector_aliases})
if typed_global_alias_node_bindings.get("instances.current_normal_journal_state") != "current_normal_journal_state":
    raise ValueError("prior normal journal-state alias is not bound to its distinct pre-claim DAG node")
expected_current_pre_projection_fields = {
    "state_kind", "journal_id_token", "journal_epoch", "journal_state_root_sha256",
    "journal_state_object_sha256", "committed_record_count", "head_sequence",
    "head_receipt_hash_sha256", "head_event_hash_sha256",
    "consumed_receipt_token_root_sha256", "consumed_scope_token_root_sha256",
    "consumed_proof_token_root_sha256", "pinned_context_sha256", "singleton_registration_sha256",
}
for state_kind, projection in instance_aliases["current_pre_journal_state"]["logical_field_projection_by_kind"].items():
    if set(projection) != expected_current_pre_projection_fields:
        raise ValueError({"incomplete_current_pre_selector_projection": [state_kind, sorted(projection)]})
    for selector_field, source_path in projection.items():
        if selector_field != "state_kind":
            require_physical_pair(f"instances.current_pre_journal_state.{selector_field}", source_path)
expected_selector_origin_conditions = {
    ("singleton_registration", selector_node): "instances.current_pre_journal_state.state_kind == REGISTERED_GENESIS",
    ("current_normal_journal_state", selector_node): "instances.current_pre_journal_state.state_kind == NORMAL_MEMORY_RECORD_STATE",
    ("current_failure_state_authority_head_observation", selector_node): "instances.current_pre_journal_state.state_kind == GENERATION_FAILURE_STATE",
}
actual_selector_origin_conditions = {
    (left, right): condition
    for left, right, _, condition in dag_edges
    if right == selector_node
}
if actual_selector_origin_conditions != expected_selector_origin_conditions:
    raise ValueError({
        "current_pre_selector_origin_condition_gap": {
            "expected": expected_selector_origin_conditions,
            "actual": actual_selector_origin_conditions,
        }
    })
if not (
    dag_index[selector_node] < dag_index["sequence_claim_acquire_pre_state"]
    < dag_index["sequence_claim_slot_and_statement"]
    < dag_index["generation_sequence_transaction_claim_evidence"]
):
    raise ValueError("current pre-journal selector is not materialized before claim construction")

for state_kind in ["REGISTERED_GENESIS", "NORMAL_MEMORY_RECORD_STATE", "GENERATION_FAILURE_STATE"]:
    require_physical_pair("instances.current_pre_journal_state.state_kind", f"constant.{state_kind}")
for left_path, right_path in [
    ("instances.current_pre_journal_state.journal_state_root_sha256", "objects.genesis_state_authority_evidence.genesis_journal_state_root_sha256"),
    ("instances.current_pre_state_authority_evidence.state_authority_head_evidence_sha256", "objects.genesis_state_authority_evidence.genesis_state_authority_head_evidence_sha256"),
    ("instances.current_pre_external_anchor_evidence.external_anchor_root_sha256", "objects.genesis_external_anchor_evidence.genesis_external_anchor_root_sha256"),
    ("instances.current_pre_journal_state.journal_state_root_sha256", "instances.prior_normal_sequence_claim_release_commit.committed_post_state_root_sha256"),
    ("instances.current_pre_state_authority_evidence.state_authority_head_evidence_sha256", "instances.prior_normal_sequence_claim_release_commit.post_state_authority_head_evidence_sha256"),
    ("instances.current_pre_external_anchor_evidence.external_anchor_root_sha256", "instances.prior_normal_sequence_claim_release_commit.post_external_anchor_root_sha256"),
    ("instances.current_failure_state_authority_head_observation.post_failure_state_root_sha256", "instances.current_pre_journal_state.journal_state_root_sha256"),
    ("instances.current_failure_state_authority_head_observation.post_failure_state_authority_head_evidence_sha256", "objects.generation_sequence_transaction_claim_evidence.pre_state_authority_head_evidence_sha256"),
    ("instances.current_failure_state_authority_head_observation.post_failure_external_anchor_root_sha256", "objects.generation_sequence_transaction_claim_evidence.pre_external_anchor_root_sha256"),
]:
    require_physical_pair(left_path, right_path)

for claim_field, selector_alias, selector_field in [
    ("authoritative_pre_journal_state_root_sha256", "current_pre_journal_state", "journal_state_root_sha256"),
    ("authoritative_pre_journal_state_object_sha256", "current_pre_journal_state", "journal_state_object_sha256"),
    ("authoritative_pre_state_kind", "current_pre_journal_state", "state_kind"),
    ("authoritative_pre_record_count", "current_pre_journal_state", "committed_record_count"),
    ("authoritative_pre_head_sequence", "current_pre_journal_state", "head_sequence"),
    ("authoritative_pre_head_receipt_hash_sha256", "current_pre_journal_state", "head_receipt_hash_sha256"),
    ("authoritative_pre_head_event_hash_sha256", "current_pre_journal_state", "head_event_hash_sha256"),
    ("pre_state_authority_head_evidence_sha256", "current_pre_state_authority_evidence", "state_authority_head_evidence_sha256"),
    ("pre_state_authority_counter", "current_pre_state_authority_evidence", "authority_monotonic_counter"),
    ("pre_external_anchor_root_sha256", "current_pre_external_anchor_evidence", "external_anchor_root_sha256"),
    ("pre_external_anchor_counter", "current_pre_external_anchor_evidence", "anchor_monotonic_counter"),
]:
    require_physical_pair(
        f"objects.generation_sequence_transaction_claim_evidence.{claim_field}",
        f"instances.{selector_alias}.{selector_field}",
    )

if any(
    "objects.generation_sequence_transaction_claim_evidence." in condition
    and dag_index[right] <= dag_index["generation_sequence_transaction_claim_evidence"]
    for _, right, _, condition in dag_edges
):
    raise ValueError("completed claim evidence field appears in a pre-claim DAG condition")
if (
    unresolved_condition_operand_dependencies
    or same_or_later_condition_operand_dependencies
    or completed_claim_preclaim_condition_dependencies
    or actual_dependency_cycle_residual
):
    raise ValueError("condition operand authentication-stage graph is not exact, early, and acyclic")

expected_failure_release_constraint = (
    "claim release pre-state is selected exhaustively and exclusively by failure_trigger: "
    "ROLE_TERMINAL_FAILED uses the exact first-failed role CONSUMED ledger state, while "
    "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE and HIDDEN_LIFECYCLE_REFUSAL use the exact never-reserved "
    "boundary ledger pre-state; every selected pre-state remains HELD_UNTIL_SEQUENCE_COMMIT until "
    "this atomic failure CAS, the post counter is checked plus one, and no competing CAS is possible"
)
if expected_failure_release_constraint not in objects["generation_failure_sequence_commit_evidence"]["constraints"]:
    raise ValueError("branch-incomplete failure release pre-state constraint")

for prior_release_alias in [
    "instances.prior_normal_sequence_claim_release_state",
    "instances.prior_failure_sequence_claim_release_state",
]:
    for invariant_field in claim_ledger_state_invariant_sources:
        require_physical_pair(
            f"{prior_release_alias}.{invariant_field}",
            f"instances.sequence_claim_acquire_pre_state.{invariant_field}",
        )

for observation_object in [
    "failure_external_anchor_current_head_observation",
    "failure_state_authority_current_head_observation",
]:
    for head_field, sentinel_domain in [
        ("post_head_receipt_hash_sha256", "KIRA_MIND_V21_FAILURE_RECEIPT_HEAD_V1"),
        ("post_head_event_hash_sha256", "KIRA_MIND_V21_FAILURE_EVENT_HEAD_V1"),
    ]:
        observation_path = f"objects.{observation_object}.{head_field}"
        rendered_target = json.dumps(path_conditions.get(observation_path), sort_keys=True)
        if sentinel_domain not in rendered_target or "never a normal" not in rendered_target:
            raise ValueError({"failure_observation_not_sentinel_targeted": observation_path})

bad_failure_observation_normal_object_pairs = []
for row in physical_pair_rows:
    endpoints = [row["left_path"], row["right_path"]]
    observation_endpoint = any(
        ("failure_anchor_current_head_observation.post_head_" in endpoint
         or "failure_authority_current_head_observation.post_head_" in endpoint)
        for endpoint in endpoints
    )
    normal_endpoint = any(
        endpoint in {"objects.receipt.receipt_hash_sha256", "objects.event.event_hash_sha256"}
        for endpoint in endpoints
    )
    if observation_endpoint and normal_endpoint:
        bad_failure_observation_normal_object_pairs.append(row)
if bad_failure_observation_normal_object_pairs:
    raise ValueError({"failure_observation_normal_receipt_event_pairs": bad_failure_observation_normal_object_pairs})

failure_release_dag_edges = [
    (left, right, reason, edge_condition)
    for left, right, reason, edge_condition in dag_edges
    if right.endswith(".sequence_claim_release_post_state_if_FAILED")
    and (left.endswith(".reservation_ledger_consumed_state") or left.endswith(".reservation_ledger_pre_state"))
]
if len(failure_release_dag_edges) != 20 or any(edge_condition == "always" for _, _, _, edge_condition in failure_release_dag_edges):
    raise ValueError({"branch_untyped_failure_release_dag_edges": failure_release_dag_edges})
for role in role_lifecycle_order:
    target_node = f"role.{role}.sequence_claim_release_post_state_if_FAILED"
    consumed_node = f"role.{role}.reservation_ledger_consumed_state"
    pre_state_node = f"role.{role}.reservation_ledger_pre_state"
    consumed_condition = next(condition for left, right, _, condition in failure_release_dag_edges if left == consumed_node and right == target_node)
    pre_state_condition = next(condition for left, right, _, condition in failure_release_dag_edges if left == pre_state_node and right == target_node)
    if "ROLE_TERMINAL_FAILED" not in consumed_condition or "HIDDEN_LIFECYCLE_REFUSAL" in consumed_condition or "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE" in consumed_condition:
        raise ValueError({"bad_consumed_release_edge_condition": [role, consumed_condition]})
    if "HIDDEN_LIFECYCLE_REFUSAL" not in pre_state_condition or "ROLE_TERMINAL_FAILED" in pre_state_condition:
        raise ValueError({"bad_unreserved_release_edge_condition": [role, pre_state_condition]})
    if role == role_lifecycle_order[0] and "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE" not in pre_state_condition:
        raise ValueError({"missing_pre_output_release_edge_condition": [role, pre_state_condition]})
    if role != role_lifecycle_order[0] and "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE" in pre_state_condition:
        raise ValueError({"nonzero_role_pre_output_release_edge_condition": [role, pre_state_condition]})

# The hidden-refusal branch names the role through the exact failure-record
# output_role and the directly bound zero-knowledge refusal boundary.  No
# nonexistent or schema-relative condition field may select the edge.
if "generation_failure_record.refusal_boundary_role" in serialized_doc:
    raise ValueError("nonexistent generation_failure_record.refusal_boundary_role condition")
for role in role_lifecycle_order:
    require_physical_pair(
        f"instances.roles.{role}.failure_record.output_role",
        f"instances.roles.{role}.lifecycle_refusal.refusal_boundary_role",
    )
    target_node = f"role.{role}.sequence_claim_release_post_state_if_FAILED"
    consumed_node = f"role.{role}.reservation_ledger_consumed_state"
    pre_state_node = f"role.{role}.reservation_ledger_pre_state"
    expected_consumed = (
        f"instances.roles.{role}.failure_record.failure_trigger == ROLE_TERMINAL_FAILED and "
        f"instances.roles.{role}.failure_record.output_role == {role}"
    )
    expected_hidden = (
        f"instances.roles.{role}.failure_record.failure_trigger == HIDDEN_LIFECYCLE_REFUSAL and "
        f"instances.roles.{role}.failure_record.output_role == {role}"
    )
    expected_unreserved = (
        f"({expected_hidden} or instances.roles.{role}.failure_record.failure_trigger == "
        f"PRE_OUTPUT_FIXED_TECHNICAL_FAILURE and instances.roles.{role}.failure_record.output_role == {role})"
        if role == role_lifecycle_order[0]
        else f"({expected_hidden})"
    )
    actual_consumed = next(condition for left, right, _, condition in failure_release_dag_edges if left == consumed_node and right == target_node)
    actual_unreserved = next(condition for left, right, _, condition in failure_release_dag_edges if left == pre_state_node and right == target_node)
    if actual_consumed != expected_consumed or actual_unreserved != expected_unreserved:
        raise ValueError({
            "failure_release_condition_truth_table_drift": {
                "role": role,
                "expected": [expected_consumed, expected_unreserved],
                "actual": [actual_consumed, actual_unreserved],
            }
        })

# One identical three-way predecessor truth table must populate every rendered
# representation of the nullable prior-ledger head selector.  The positive
# failure-state branch admits all exact failure/refusal triggers.
claim_prior_head_path = "objects.generation_sequence_transaction_claim_evidence.prior_reservation_ledger_head_evidence_sha256"
if path_conditions.get(claim_prior_head_path) != claim_prior_reservation_ledger_head_branches:
    raise ValueError("claim prior-ledger-head branch table drift")
failure_prior_head_when = claim_prior_reservation_ledger_head_branches[2]["when"]
if any(trigger not in failure_prior_head_when for trigger in [
    "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE", "ROLE_TERMINAL_FAILED", "HIDDEN_LIFECYCLE_REFUSAL",
]):
    raise ValueError("claim failure/refusal predecessor branch is not exhaustive")
if serialized_doc.count(failure_prior_head_when) != 4:
    raise ValueError({
        "claim_prior_ledger_head_authoritative_representation_count": serialized_doc.count(failure_prior_head_when)
    })
if "prior journal sequence completed as canonical technical failure" in serialized_doc:
    raise ValueError("stale non-exhaustive canonical-technical-failure selector")

# Every derived physical endpoint is declared once in the typed derived-value
# registry and supplies a finite exact SHA-256 preimage.  The one complete root
# plus ten prefix roots appear in exactly 31 physical rows.
declared_derived_paths = {
    typed_derived_value_aliases["complete_ten_role_success_chain_set_root_sha256"]["path"],
    *{
        typed_derived_value_aliases["roles"][role]["completed_success_role_prefix_root_sha256"]["path"]
        for role in role_lifecycle_order
    },
}
rendered_derived_paths = set(re.findall(
    r"derived(?:\.roles\.[A-Z0-9_]+)?\.[a-z0-9_]+_sha256",
    serialized_doc,
))
if rendered_derived_paths != declared_derived_paths:
    raise ValueError({
        "typed_derived_value_path_gap": {
            "declared": sorted(declared_derived_paths),
            "rendered": sorted(rendered_derived_paths),
        }
    })
physical_derived_endpoints = [
    endpoint
    for row in physical_pair_rows
    for endpoint in [row["left_path"], row["right_path"]]
    if endpoint.startswith("derived.")
]
if len(physical_derived_endpoints) != 31 or set(physical_derived_endpoints) != declared_derived_paths:
    raise ValueError({"typed_derived_physical_endpoint_closure": physical_derived_endpoints})

object_path_errors = set()
for object_name, field_name in re.findall(r"objects\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)", serialized_doc):
    if object_name not in objects or field_name not in objects[object_name]["field_order"]:
        object_path_errors.add(f"objects.{object_name}.{field_name}")
if object_path_errors:
    raise ValueError({"undefined_rendered_object_field_paths": sorted(object_path_errors)})

role_alias_path_errors = set()
for role, alias_name, field_name in re.findall(
    r"instances\.roles\.([A-Z0-9_]+)\.([a-z0-9_]+)\.([A-Za-z0-9_]+)", serialized_doc
):
    alias_spec = role_instance_aliases.get(role, {}).get(alias_name)
    if alias_spec is None or field_name not in alias_allowed_fields(alias_spec):
        role_alias_path_errors.add(f"instances.roles.{role}.{alias_name}.{field_name}")
if role_alias_path_errors:
    raise ValueError({"undefined_rendered_role_alias_field_paths": sorted(role_alias_path_errors)})

global_alias_path_errors = set()
for alias_name, field_name in re.findall(
    r"instances\.(?!roles\.)([a-z0-9_]+)\.([A-Za-z0-9_]+)", serialized_doc
):
    alias_spec = instance_aliases.get(alias_name)
    if alias_spec is None or field_name not in alias_allowed_fields(alias_spec):
        global_alias_path_errors.add(f"instances.{alias_name}.{field_name}")
if global_alias_path_errors:
    raise ValueError({"undefined_rendered_global_alias_field_paths": sorted(global_alias_path_errors)})

expected_authoritative_registry_pre_state_fields = [
    "schema",
    "hash_domain",
    "predecessor_singleton_registration_sha256",
    "predecessor_registry_post_state_sha256",
    "namespace_precommitment_root_sha256",
    "pinned_context_root_sha256",
    "registry_root_sha256",
    "registry_counter",
    "registry_head_sha256",
    "pre_state_sha256",
]
if objects["authoritative_registry_pre_state"]["field_order"] != expected_authoritative_registry_pre_state_fields:
    raise ValueError("authoritative registry pre-state field order drift")
if len(role_instance_aliases) != len(role_lifecycle_order):
    raise ValueError("role-instance alias cardinality drift")
for role in role_lifecycle_order:
    for required_alias in ["availability_commitment", "availability_evidence"]:
        if required_alias not in role_instance_aliases[role]:
            raise ValueError({"missing_role_availability_alias": [role, required_alias]})
    for required_node_key in ["availability_commitment", "availability_evidence"]:
        if required_node_key not in next(row for row in role_instance_rows if row["role"] == role)["typed_alias_node_bindings"]:
            raise ValueError({"missing_role_availability_dag_binding": [role, required_node_key]})

OUT.write_bytes(serialized_doc.encode("utf-8"))
print(json.dumps({"path": OUT.name, "bytes": OUT.stat().st_size, "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(), "objects": len(objects)}, sort_keys=True))
