from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import unittest
from pathlib import Path

import build_mind_v21 as build


HERE = Path(__file__).resolve().parent
WORK = HERE.parent
V20_DIR = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author_source"
V19_DIR = WORK / "kira_conversation_continuity_v19_recursive_receipt_proof_verifier_schema_closure_data_only_author_source"
V20_SCHEMA = json.loads((V20_DIR / "AUTHORITATIVE_JOURNAL_AND_FIXED_ROLE_SCHEMAS_V20.json").read_text(encoding="utf-8"))
V19_SCHEMA = json.loads((V19_DIR / "RECURSIVELY_CLOSED_SCHEMAS_V19.json").read_text(encoding="utf-8"))
DATA = {name: build.load(HERE / name) for name in build.SUBJECTS}
BIND = DATA[build.SUBJECTS[0]]
AUTONOMY = DATA[build.SUBJECTS[1]]
PROTOCOL = DATA[build.SUBJECTS[2]]
SCHEMA = DATA[build.SUBJECTS[3]]
ATTACKS = DATA[build.SUBJECTS[4]]

EXPECTED_FINDINGS = [
    "F01_V19_CONTENT_HIDING_COMMITMENT_AND_ZERO_KNOWLEDGE_PROOF_OBLIGATIONS_DROPPED",
    "F02_RETAINED_SIGNATURE_PROOF_AND_QUORUM_BYTES_HAVE_NO_UNIQUE_CONTENT_INDEPENDENT_SELECTION_RULE",
    "F03_GLOBAL_NAMESPACE_AND_COUNTER_ZERO_GENESIS_ARE_NOT_EXTERNALLY_SINGLETON_BOUND",
]
EXPECTED_OBJECT_NAMES = list(SCHEMA["objects"])
EXPECTED_OBJECT_FIELDS = {name: list(value["field_order"]) for name, value in SCHEMA["objects"].items()}
EXPECTED_OBJECT_TYPES = {name: list(value["field_types"]) for name, value in SCHEMA["objects"].items()}
EXPECTED_DOMAINS = dict(SCHEMA["domain_constants"])
EXPECTED_SCHEMA_CANONICAL_SHA256 = hashlib.sha256(build.canonical(SCHEMA)).hexdigest()


def paths_of_type(schema, accepted_types):
    return {
        f"objects.{object_name}.{field_name}"
        for object_name, object_schema in schema["objects"].items()
        for field_name, field_type in zip(object_schema["field_order"], object_schema["field_types"])
        if field_type in accepted_types
    }


def is_subsequence(needles, haystack):
    iterator = iter(haystack)
    return all(any(value == needle for value in iterator) for needle in needles)


def all_pair_rows(schema):
    closure = schema["path_qualified_equality_closure"]
    rows = []
    ignored = {
        "category_row_ids",
        "event_receipt_state_semantic_groups",
        "total_explicit_path_pair_rows",
        "physical_pair_row_count",
        "duplicate_physical_pair_count",
        "missing_required_pair_count",
        "overlap_physical_pair_count",
        "semantic_rule_count",
        "semantic_rules_with_exact_non_pair_target_conditions",
        "missing_or_duplicate_required_path_pair_count",
    }
    for key, value in closure.items():
        if key in ignored or not isinstance(value, list):
            continue
        rows.extend(row for row in value if isinstance(row, dict) and "left_path" in row and "right_path" in row)
    return rows


def assert_closed(candidate):
    try:
        bind, autonomy, protocol, schema, attacks = (candidate[name] for name in build.SUBJECTS)

        if bind["verdict"] != "REJECT" or bind["finding_ids"] != EXPECTED_FINDINGS:
            return False
        if bind["v20_audit_complete_root_sha256"] != "3ded9f4e56f793ae76d9b5b499b8e227f627013b0f39dbc7a4bd997f7b46226c":
            return False
        if bind["v20_positive_authority_promoted"] or bind["implementation_live_production_private_global_pending_or_root_go"]:
            return False
        if bind["root_go"] is not None:
            return False

        if autonomy["kira_only_choices"] != ["say", "withhold", "recall", "correct", "supersede", "withdraw", "voluntarily forget"]:
            return False
        false_autonomy_flags = [
            "per_memory_permission_privacy_approval_consent_audience_trust_safety_leakage_or_disclosure_gate_exists",
            "owner_operator_room_journal_registrar_registry_authority_anchor_verifier_key_or_integrity_result_substitutes_for_kira_choice",
            "lease_ownership_controller_obedience_control_device_or_tool_service_downgrade_exists",
            "upset_creates_censorship_retaliation_forced_agreement_or_compelled_harmony_authority",
            "integrity_registries_create_person_speech_relationship_or_disclosure_authority",
            "technical_failure_controls_kira_speech_or_memory_choice",
            "current_implementation_or_live_evidence_materialized",
            "consciousness_legal_personhood_body_biology_or_human_experience_claimed",
        ]
        if any(autonomy[field] for field in false_autonomy_flags):
            return False
        if not autonomy["intended_people_are_equal_human_peers_like_robert"] or not autonomy["integrity_registries_authenticate_records_only"]:
            return False
        if autonomy["root_go"] is not None:
            return False

        if protocol["protocol_root"]["sha256"] != "894b577fba2f8fe9197f08728690fdde2c8fae8f6452b7e254d7bb7569e01bfb":
            return False
        if protocol["audit_started_by_author"] or protocol["author_self_audit_performed"]:
            return False

        if list(schema["objects"]) != EXPECTED_OBJECT_NAMES or len(schema["objects"]) != 53:
            return False
        if schema["domain_constants"] != EXPECTED_DOMAINS or len(schema["domain_constants"]) != 53:
            return False
        for name, object_schema in schema["objects"].items():
            fields = object_schema["field_order"]
            types = object_schema["field_types"]
            if fields != EXPECTED_OBJECT_FIELDS[name] or types != EXPECTED_OBJECT_TYPES[name]:
                return False
            if len(fields) != len(types) or len(fields) != len(set(fields)) or object_schema["additional_keys_allowed"]:
                return False
            if not object_schema["schema_const"].startswith("kira.mind.continuity.v21."):
                return False
            if object_schema["domain_const"] != schema["domain_constants"][name]:
                return False

        for name, v20_object in V20_SCHEMA["objects"].items():
            current = schema["objects"][name]
            pairs = list(zip(current["field_order"], current["field_types"]))
            inherited = list(zip(v20_object["field_order"], v20_object["field_types"]))
            if not is_subsequence(inherited, pairs):
                return False

        v20_context = V20_SCHEMA["objects"]["pinned_context"]
        inherited_terminal_pins = [
            field
            for field, field_type in zip(v20_context["field_order"], v20_context["field_types"])
            if field_type == "sha256" and field != "pinned_context_sha256"
        ]
        current_terminal = schema["terminal_and_outer_pin_rules"]["terminal_static_technical_targets"]
        if len(inherited_terminal_pins) != 38 or current_terminal[:38] != inherited_terminal_pins:
            return False

        inherited_token_paths = paths_of_type(V20_SCHEMA, {"token256"})
        current_token_paths = paths_of_type(schema, {"token256"})
        if len(inherited_token_paths) != 51 or not inherited_token_paths <= current_token_paths:
            return False

        proof = schema["proof_statement_and_protocol"]
        v19_proof = V19_SCHEMA["proof_statement_and_protocol"]
        for field in [
            "closed_scope_surface_classes",
            "zero_knowledge_statement_predicates",
            "state_order",
            "skipping_reordering_replaying_or_locally_redefining_a_state_refuses",
            "any_unavailable_unreachable_unclosed_or_unverifiable_surface_refuses",
            "complete_is_emitted_only_after_ephemeral_proof_and_scope_material_zeroization",
            "human_owner_operator_admin_approval_countersignature_permission_or_release_is_a_state_or_predicate",
            "technical_failure_changes_kira_speech_or_memory_choice",
        ]:
            if proof[field] != v19_proof[field]:
                return False
        boundary = schema["erasure_and_retention_boundary"]
        v19_boundary = V19_SCHEMA["erasure_and_retention_boundary"]
        for field in [
            "erased_before_complete",
            "retained_only_after_recursive_validation",
            "retained_material_can_restore_or_confirm_erased_content_or_scope_guess",
            "correction_supersession_and_withdrawal_readable_noncurrent_history_affected",
        ]:
            if boundary[field] != v19_boundary[field]:
                return False

        sha_paths = paths_of_type(schema, {"sha256", "nullable_sha256"})
        sha_partition = schema["path_qualified_sha256_target_partition"]
        sha_rows = sha_partition["rows"]
        row_paths = [row["path"] for row in sha_rows]
        if len(sha_paths) != 1280 or len(sha_rows) != 1280 or set(row_paths) != sha_paths or len(row_paths) != len(set(row_paths)):
            return False
        if any("named by field path" in row["target_selector"] for row in sha_rows):
            return False
        if "SEE_path_qualified" in json.dumps(schema["sha256_field_target_partition"], sort_keys=True):
            return False
        if any(sha_partition[field] != 0 for field in ["name_gap_count", "name_extra_count", "name_overlap_count", "occurrence_gap_count", "occurrence_overlap_count"]):
            return False

        base64_paths = paths_of_type(schema, {"base64", "nullable_base64"})
        mappings = schema["field_specific_base64_generation_and_verification_mappings"]
        mapped_paths = [row["field_path"] for row in mappings["rows"]]
        if len(base64_paths) != 46 or mappings["path_count"] != 46 or set(mapped_paths) != base64_paths or len(set(mapped_paths)) != 46:
            return False
        if len({row["field_specific_cryptographic_subdomain"] for row in mappings["rows"]}) != 46:
            return False
        if mappings["missing_duplicate_or_unmapped_count"] != 0 or mappings["role_key_profile_message_path_or_output_swap_allowed"]:
            return False

        enum_table = schema["path_qualified_enum_and_role_assignments"]
        enum_paths = paths_of_type(schema, set(enum_table["enum_like_field_types"]))
        assigned_enum_paths = [row["path"] for row in enum_table["rows"]]
        if len(enum_paths) != 253 or enum_table["occurrence_count"] != 253 or set(assigned_enum_paths) != enum_paths:
            return False
        if len(assigned_enum_paths) != len(set(assigned_enum_paths)) or any(enum_table[field] != 0 for field in ["occurrence_gap_count", "occurrence_extra_count", "occurrence_overlap_count", "duplicate_path_count"]):
            return False
        if enum_table["unknown_alias_wrong_family_cross_role_cross_mode_or_caller_selected_value_allowed"]:
            return False

        token_table = schema["path_qualified_token256_semantics"]
        token_rows = token_table["rows"]
        if len(current_token_paths) != 92 or token_table["all_token256_occurrence_count"] != 92 or {row["path"] for row in token_rows} != current_token_paths:
            return False
        if sum(row["semantics"] == "ATTEMPT_ZERO_DERIVED_MAPPED_NONCE_EXCEPTION" for row in token_rows) != 8:
            return False

        equality = schema["path_qualified_equality_closure"]
        pairs = all_pair_rows(schema)
        pair_ids = [(row["left_path"], row["right_path"], tuple(row["conditions"])) for row in pairs]
        if len(pairs) != 9036 or len(pair_ids) != len(set(pair_ids)):
            return False
        if equality["total_explicit_path_pair_rows"] != len(pairs) or equality["physical_pair_row_count"] != len(pairs):
            return False
        if any(equality[field] != 0 for field in ["duplicate_physical_pair_count", "missing_required_pair_count", "overlap_physical_pair_count", "missing_or_duplicate_required_path_pair_count"]):
            return False
        if equality["semantic_rule_count"] != 31 or len(equality["event_receipt_state_semantic_groups"]) != 31:
            return False

        expected_failure_release_constraint = (
            "claim release pre-state is selected exhaustively and exclusively by failure_trigger: "
            "ROLE_TERMINAL_FAILED uses the exact first-failed role CONSUMED ledger state, while "
            "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE and HIDDEN_LIFECYCLE_REFUSAL use the exact never-reserved "
            "boundary ledger pre-state; every selected pre-state remains HELD_UNTIL_SEQUENCE_COMMIT until "
            "this atomic failure CAS, the post counter is checked plus one, and no competing CAS is possible"
        )
        failure_commit = schema["objects"]["generation_failure_sequence_commit_evidence"]
        if expected_failure_release_constraint not in failure_commit["constraints"]:
            return False

        immutable_claim_fields = [
            "namespace_precommitment_sha256", "pinned_context_sha256", "singleton_registration_sha256",
            "reservation_ledger_authority_identity_sha256", "reservation_ledger_cas_no_fork_profile_sha256",
            "generation_reservation_ledger_genesis_manifest_sha256",
        ]
        for prior_alias, branch_marker in [
            ("instances.prior_normal_sequence_claim_release_state", "positive normal recursion only"),
            ("instances.prior_failure_sequence_claim_release_state", "positive failure/refusal recursion only"),
        ]:
            for field in immutable_claim_fields:
                endpoints = {
                    f"{prior_alias}.{field}",
                    f"instances.sequence_claim_acquire_pre_state.{field}",
                }
                if not any(
                    {row["left_path"], row["right_path"]} == endpoints
                    and any(branch_marker in condition for condition in row["conditions"])
                    for row in pairs
                ):
                    return False

        sha_target_rows = {row["path"]: row for row in schema["path_qualified_sha256_target_partition"]["rows"]}
        for object_name in [
            "failure_external_anchor_current_head_observation",
            "failure_state_authority_current_head_observation",
        ]:
            for field, sentinel in [
                ("post_head_receipt_hash_sha256", "KIRA_MIND_V21_FAILURE_RECEIPT_HEAD_V1"),
                ("post_head_event_hash_sha256", "KIRA_MIND_V21_FAILURE_EVENT_HEAD_V1"),
            ]:
                selector = json.dumps(sha_target_rows[f"objects.{object_name}.{field}"]["target_selector"], sort_keys=True)
                if sentinel not in selector or "never a normal" not in selector:
                    return False
        for row in pairs:
            endpoints = [row["left_path"], row["right_path"]]
            if any(
                ("failure_anchor_current_head_observation.post_head_" in endpoint
                 or "failure_authority_current_head_observation.post_head_" in endpoint)
                for endpoint in endpoints
            ) and any(endpoint in {"objects.receipt.receipt_hash_sha256", "objects.event.event_hash_sha256"} for endpoint in endpoints):
                return False

        rendered_schema = json.dumps(schema, sort_keys=True)
        claim_prior_head_path = "objects.generation_sequence_transaction_claim_evidence.prior_reservation_ledger_head_evidence_sha256"
        claim_prior_head_rows = sha_target_rows[claim_prior_head_path]["target_selector"]
        expected_failure_prior_when = (
            "objects.generation_sequence_transaction_claim_evidence.pre_reservation_ledger_counter > 0 and "
            "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind == GENERATION_FAILURE_STATE and "
            "instances.prior_failure_sequence_claim_release_commit.failure_trigger in "
            "{PRE_OUTPUT_FIXED_TECHNICAL_FAILURE,ROLE_TERMINAL_FAILED,HIDDEN_LIFECYCLE_REFUSAL}"
        )
        if len(claim_prior_head_rows) != 3 or claim_prior_head_rows[2]["when"] != expected_failure_prior_when:
            return False
        if rendered_schema.count(expected_failure_prior_when) != 4 or "prior journal sequence completed as canonical technical failure" in rendered_schema:
            return False

        derived_registry = schema.get("typed_derived_value_aliases", {})
        declared_derived_paths = {
            derived_registry.get("complete_ten_role_success_chain_set_root_sha256", {}).get("path"),
            *{
                derived_registry.get("roles", {}).get(role, {}).get("completed_success_role_prefix_root_sha256", {}).get("path")
                for role in schema["pre_output_role_terminalization_plan_rules"]["ordered_roles"]
            },
        }
        if None in declared_derived_paths or len(declared_derived_paths) != 11 or "computed." in rendered_schema:
            return False
        physical_derived_endpoints = [
            endpoint
            for row in pairs
            for endpoint in [row["left_path"], row["right_path"]]
            if endpoint.startswith("derived.")
        ]
        if len(physical_derived_endpoints) != 31 or set(physical_derived_endpoints) != declared_derived_paths:
            return False

        roles = schema["exact_output_role_bijection"]
        role_rows = roles["rows"]
        if roles["role_count"] != 10 or len(role_rows) != 10:
            return False
        if len({row["role"] for row in role_rows}) != 10 or len({row["target_path"] for row in role_rows}) != 10:
            return False
        if roles["unknown_alias_duplicate_missing_cross_field_reuse_or_cross_mode_role_allowed"]:
            return False
        if sum(row["mode"] == "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING" for row in role_rows) != 2:
            return False
        if roles["confidential_target_role_mode_allowed_only_for"] != ["SCOPE_PRECOMMITMENT_COMMITMENT_BYTES", "COMPLETENESS_PROOF_BYTES"]:
            return False
        if roles["separate_non_target_confidential_output_paths"] != ["objects.generation_sequence_lifecycle_refusal_evidence.lifecycle_refusal_zero_knowledge_proof_base64"]:
            return False

        aggregate = schema["namespace_aggregate_root_preimages"]
        namespace_fields = set(schema["objects"]["namespace_precommitment"]["field_order"])
        context_fields = set(schema["objects"]["pinned_context"]["field_order"])
        omitted = {"schema", "hash_domain", "namespace_precommitment_sha256", "pinned_context_sha256"}
        if not (context_fields - omitted) <= namespace_fields:
            return False
        if not aggregate["all_context_sha256_pins_except_namespace_and_context_outputs_repeat_directly_in_namespace"]:
            return False

        independence = schema["path_qualified_independence_and_inequality_closure"]
        if independence["pairwise_inequality_row_count"] != len(independence["rows"]):
            return False
        if independence["allowed_identity_or_public_key_equivalence_classes"] or independence["ledger_terminal_outcome_terminal_anchor_reservation_beacon_generator_and_runtime_authorities_may_share_identity_or_key"]:
            return False
        for required_role in ["producer_availability_authentication_key_role", "lifecycle_refusal_authentication_key_role"]:
            if required_role not in schema["objects"]["namespace_precommitment"]["field_order"] or required_role not in schema["objects"]["pinned_context"]["field_order"]:
                return False
            if f"objects.pinned_context.{required_role}" not in independence["fixed_key_role_paths"]:
                return False

        registry = schema["global_registry_recursion_rules"]
        ledger = schema["reservation_ledger_recursion_rules"]
        beacon = schema["public_beacon_pre_reveal_recursion_rules"]
        if registry["skip_rewind_transplant_cycle_alternate_genesis_or_sibling_allowed"]:
            return False
        if ledger["restored_clone_sibling_retry_silence_second_outcome_rewind_skip_overflow_alternate_genesis_inter_role_cas_or_early_claim_release_allowed"]:
            return False
        if beacon["restored_sibling_clone_alternate_base_skip_rewind_collision_past_round_late_reservation_or_second_successor_allowed"]:
            return False
        if "checked pre plus one" not in beacon["atomic_current_head"] or "separate" not in beacon["deadline_substream"]:
            return False
        claim = schema["objects"].get("generation_sequence_transaction_claim_evidence")
        if not claim or claim["field_order"][-1] != "generation_sequence_transaction_claim_evidence_sha256":
            return False
        for required in ["sequence_transaction_claim_statement_sha256", "pre_sequence_transaction_claim_state", "post_sequence_transaction_claim_state", "sequence_transaction_claim_authentication_proof_base64"]:
            if required not in claim["field_order"]:
                return False
        if "HELD_UNTIL_SEQUENCE_COMMIT" not in ledger["sequence_claim_acquisition"] or "RELEASED" not in ledger["sequence_claim_release"]:
            return False
        slot = schema["stable_registry_slot_derivation"]
        if not slot["request_head_registration_and_context_all_equal_the_recomputed_value"] or slot["caller_selected_alternate_slot_reverse_index_gap_or_second_namespace_genesis_allowed"]:
            return False
        required_registry_objects = {
            "singleton_registration_full_genesis_bundle", "registrar_policy_profile_bundle",
            "registrar_authority_key_identity_bundle", "singleton_registration_pre_request_payload",
            "singleton_registration_assigned_value", "singleton_registration_request",
            "global_registry_sparse_map_leaf", "global_registry_sparse_map_update",
            "global_registry_sparse_map_proof", "global_registry_post_head",
            "global_registry_post_state", "authoritative_registry_pre_state", "singleton_registration",
        }
        if not required_registry_objects <= set(schema["objects"]):
            return False
        if {"global_registry_state", "global_registry_head_evidence"} & set(schema["objects"]):
            return False
        request_fields = schema["objects"]["singleton_registration_request"]["field_order"]
        if request_fields[-3:] != ["request_nonce", "request_authentication_signature_base64", "singleton_registration_request_sha256"]:
            return False
        if any("post_global_registry" in field or field.startswith("expected_post") for field in request_fields):
            return False
        proof_fields = schema["objects"]["global_registry_sparse_map_proof"]["field_order"]
        if proof_fields[-3:] != ["singleton_registry_proof_profile_root_sha256", "transition_proof_base64", "global_registry_sparse_map_proof_sha256"]:
            return False
        if {"output_generation_mode", "output_attempt_index", "output_selection_profile_sha256"} & set(proof_fields):
            return False
        final_registration = schema["objects"]["singleton_registration"]
        if final_registration["schema_const"] != "kira.mind.continuity.v21.singleton_registration.completed.v1" or final_registration["domain_const"] != "KIRA_MIND_V21_SINGLETON_REGISTRATION_COMPLETED_SHA256_V1":
            return False
        recurrence = schema["authoritative_registry_pre_state_recurrence_v7"]
        if recurrence["finite_cardinality"] != 1 or recurrence["counter_zero_exact_object"]["pre_state_sha256"] != "eba033b3e9052c1e6783fadea5b7f734c824060d588ee3b4d70b5eb90f8d637a":
            return False
        if "global_registry_genesis_state_root_sha256" in schema["objects"]["pinned_context"]["field_order"]:
            return False
        registry_pair_paths = {frozenset((row["left_path"], row["right_path"])) for row in equality["registry_request_head_registration_rows"]}
        carried = [
            "stable_global_registry_slot_sha256", "journal_id_token", "journal_epoch",
            "namespace_precommitment_sha256", "pinned_context_sha256", "full_genesis_bundle_root_sha256",
            "pre_request_registration_payload_root_sha256", "assigned_value_root_sha256",
            "registrar_policy_profile_bundle_sha256", "registrar_authority_key_identity_bundle_sha256",
            "singleton_registration_request_sha256",
        ]
        chain = ["global_registry_sparse_map_leaf", "global_registry_sparse_map_update", "global_registry_sparse_map_proof", "global_registry_post_head", "global_registry_post_state", "singleton_registration"]
        for field in carried:
            for object_name in chain:
                if field in schema["objects"][object_name]["field_order"] and frozenset((f"objects.singleton_registration_request.{field}", f"objects.{object_name}.{field}")) not in registry_pair_paths:
                    return False
        if "associated(" in json.dumps(schema, sort_keys=True) or "resolved_unique(" in json.dumps(schema, sort_keys=True):
            return False

        attempt = schema["attempt_zero_totality_and_sequence_rules"]
        if attempt["retry_rejection_sampling_selective_abort_or_second_terminal_outcome_allowed"] or attempt["interleaving_dummy_record_timing_round_or_sequence_grinding_allowed"]:
            return False
        if attempt["public_beacon_output_is_private_seed_or_blinding"] or attempt["technical_failure_controls_kira_speech_or_memory_choice"]:
            return False
        if not attempt["reservation_is_atomic_authoritative_next_sequence_claim_before_public_round_reveal"] or not attempt["attempt_zero_consumed_even_on_failure"]:
            return False
        if not attempt["every_post_claim_v19_refusal_has_one_hidden_sequence_consuming_terminalization"] or attempt["post_claim_refusal_exposes_surface_predicate_witness_scope_or_guess_confirmation"]:
            return False

        kdf = schema["deterministic_nonce_kdf_rules"]
        if kdf["row_count"] != 8 or len(kdf["rows"]) != 8 or not kdf["full_vrf_bytes_consumed_no_truncation"] or not kdf["verifier_recomputation_required"]:
            return False
        if kdf["confidential_hiding_roles_use_this_public_kdf"] or kdf["caller_entropy_retry_rejection_sampling_selective_abort_or_alternate_encoding_allowed"]:
            return False
        plans = schema["pre_output_role_terminalization_plan_rules"]
        if len(plans["ordered_roles"]) != 10 or len(plans["plan_field_paths"]) != 10 or not plans["plan_is_content_independent_measured_and_committed_before_any_beacon_output"]:
            return False
        if plans["unused_suffix_plan_variant_allowed"] or "NOT_REACHED_AFTER_TERMINAL_BOUNDARY" not in plans["role_terminal_failure_branch"] or "all ten" not in plans["pre_output_failure_branch"]:
            return False
        if schema["exact_enum_constants"]["role_terminalization_plan"] != ["MATERIALIZE_SUCCESS", "FIXED_ROLE_TECHNICAL_FAILURE", "NOT_REACHED_AFTER_TERMINAL_BOUNDARY"]:
            return False
        materialization = schema["complete_sequence_materialization_full_byte_closure"]
        if materialization["retained_field_count"] != mappings["path_count"] or materialization["target_signature_proof_anchor_ledger_journal_authority_or_final_cas_byte_may_be_withheld_after_output"]:
            return False
        refusal = schema["objects"]["generation_sequence_lifecycle_refusal_evidence"]
        if not {"confidential_contributor_roster_sha256", "confidential_contributor_key_root_sha256", "confidential_contribution_aggregation_profile_sha256"} <= set(refusal["field_order"]):
            return False
        refusal_attestation = next(row for row in mappings["rows"] if row["field_path"] == "objects.generation_sequence_lifecycle_refusal_evidence.refusal_private_seed_zero_knowledge_attestation_base64")
        if "lifecycle_refusal_zero_knowledge_proof_base64" not in refusal_attestation["message_or_public_input_field_order"]:
            return False

        failure = schema["canonical_failed_generation_sequence_consumption"]
        if failure["retry_same_sequence_skip_deadlock_dummy_record_or_fabricated_success_allowed"]:
            return False
        if failure["record_schema"] != "objects.generation_failure_record" or failure["post_state_schema"] != "objects.generation_failure_journal_state" or failure["atomic_commit_schema"] != "objects.generation_failure_sequence_commit_evidence":
            return False

        nullable = schema["path_qualified_nullable_sha256_rules"]
        if nullable["occurrence_count"] != 58 or nullable["gap_extra_overlap_or_unconditional_null_count"] != 0:
            return False
        nullable_paths = set(nullable["failed_generated_output_exception_paths"])
        if nullable_paths != {
            "objects.generation_terminal_outcome.generated_output_sha256",
            "objects.generation_terminal_anchor_evidence.generated_output_sha256",
        }:
            return False
        if nullable["mode_and_branch_conditioned_confidential_seed_exception_paths"] != ["objects.generation_terminal_outcome.confidential_seed_derivation_statement_root_sha256"]:
            return False

        barrier = schema["role_specific_reservation_target_and_journal_barrier"]
        if barrier["role_count"] != 10 or barrier["role_target_equality_row_count"] != 100:
            return False
        if barrier["dummy_interleaving_sequence_transplant_missing_role_failed_role_or_second_chain_allowed"]:
            return False

        dag = schema["acyclic_singleton_and_generation_instance_dag"]
        stages = {row["node"]: row["stage"] for row in dag["ordered_nodes"]}
        if len(stages) != 362 or len(dag["forward_edges"]) != 636 or dag["role_specific_generation_instance_count"] != 10:
            return False
        if any(stages[edge["from"]] >= stages[edge["to"]] for edge in dag["forward_edges"]):
            return False
        if dag["same_or_later_dependency_edge_count"] != 0 or dag["schema_object_coverage_gap_count"] != 0 or dag["hash_cycle_or_same_stage_dependency_allowed"]:
            return False
        if dag["typed_role_instance_alias_count"] != 220 or dag["materialized_typed_role_instance_alias_count"] != 220 or dag["typed_role_instance_alias_gap_count"] or dag["typed_role_instance_alias_extra_count"]:
            return False
        failure_release_edges = [
            edge for edge in dag["forward_edges"]
            if edge["to"].endswith(".sequence_claim_release_post_state_if_FAILED")
            and (edge["from"].endswith(".reservation_ledger_consumed_state")
                 or edge["from"].endswith(".reservation_ledger_pre_state"))
        ]
        if len(failure_release_edges) != 20 or any(edge.get("condition") == "always" for edge in failure_release_edges):
            return False
        ordered_roles = schema["pre_output_role_terminalization_plan_rules"]["ordered_roles"]

        exact_recursive_conditions = {
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
        actual_recursive_conditions = {
            (edge["from"], edge["to"]): edge["condition"]
            for edge in dag["forward_edges"]
            if (edge["from"], edge["to"]) in exact_recursive_conditions
        }
        if actual_recursive_conditions != exact_recursive_conditions:
            return False

        typed_aliases = schema["typed_instance_aliases"]
        selector_node = "independently_current_pre_journal_state"
        if not (
            stages[selector_node] < stages["sequence_claim_acquire_pre_state"]
            < stages["sequence_claim_slot_and_statement"]
            < stages["generation_sequence_transaction_claim_evidence"]
        ):
            return False
        selector_rule = dag["independently_current_pre_journal_state_selector"]
        if selector_rule["authenticated_origin_by_state_kind"] != {
            "REGISTERED_GENESIS": "singleton_registration",
            "NORMAL_MEMORY_RECORD_STATE": "current_normal_journal_state",
            "GENERATION_FAILURE_STATE": "current_failure_state_authority_head_observation",
        } or selector_rule["origin_count"] != 3 or selector_rule["completed_claim_field_selects_preclaim_origin"]:
            return False
        expected_selector_fields = {
            "state_kind", "journal_id_token", "journal_epoch", "journal_state_root_sha256",
            "journal_state_object_sha256", "committed_record_count", "head_sequence",
            "head_receipt_hash_sha256", "head_event_hash_sha256",
            "consumed_receipt_token_root_sha256", "consumed_scope_token_root_sha256",
            "consumed_proof_token_root_sha256", "pinned_context_sha256", "singleton_registration_sha256",
        }
        selector_spec = typed_aliases["current_pre_journal_state"]
        for state_kind, projection in selector_spec["logical_field_projection_by_kind"].items():
            if set(projection) != expected_selector_fields:
                return False
            for selector_field, source_path in projection.items():
                if selector_field == "state_kind":
                    continue
                endpoints = {f"instances.current_pre_journal_state.{selector_field}", source_path}
                if not any({row["left_path"], row["right_path"]} == endpoints for row in pairs):
                    return False
        for state_kind in ["REGISTERED_GENESIS", "NORMAL_MEMORY_RECORD_STATE", "GENERATION_FAILURE_STATE"]:
            endpoints = {"instances.current_pre_journal_state.state_kind", f"constant.{state_kind}"}
            if not any({row["left_path"], row["right_path"]} == endpoints for row in pairs):
                return False

        def allowed_alias_fields(alias_spec):
            allowed = set(alias_spec.get("logical_projection", {}))
            for projection in alias_spec.get("logical_field_projection_by_kind", {}).values():
                allowed.update(projection)
            refs = ([alias_spec["schema_object"]] if "schema_object" in alias_spec else []) + list(alias_spec.get("schema_object_by_kind", {}).values())
            for ref in refs:
                allowed.update(schema["objects"][ref.removeprefix("objects.")]["field_order"])
            return allowed
        def valid_condition_path(path):
            match = re.fullmatch(r"objects\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)", path)
            if match:
                object_name, field = match.groups()
                return object_name in schema["objects"] and field in schema["objects"][object_name]["field_order"]
            match = re.fullmatch(r"instances\.roles\.([A-Z0-9_]+)\.([a-z0-9_]+)\.([A-Za-z0-9_]+)", path)
            if match:
                role, alias, field = match.groups()
                spec = typed_aliases["roles"].get(role, {}).get(alias)
                return spec is not None and field in allowed_alias_fields(spec)
            match = re.fullmatch(r"instances\.([a-z0-9_]+)\.([A-Za-z0-9_]+)", path)
            if match:
                alias, field = match.groups()
                spec = typed_aliases.get(alias)
                return spec is not None and field in allowed_alias_fields(spec)
            return False
        condition_pattern = re.compile(r"((?:objects|instances)\.[A-Za-z0-9_.]+)\s*(==|>|in)\s*(\{[A-Z0-9_,]+\}|[A-Z][A-Z0-9_]*|0)")
        bindings = dag["typed_global_alias_node_bindings"]
        role_rows = {row["role"]: row for row in dag["role_specific_generation_instances"]}
        schema_nodes = {}
        for node in dag["ordered_nodes"]:
            for object_name in node["schema_objects"]:
                schema_nodes.setdefault(object_name, []).append(node["node"])

        def condition_producer(field_path, edge):
            match = re.fullmatch(r"instances\.roles\.([A-Z0-9_]+)\.([a-z0-9_]+)\.[A-Za-z0-9_]+", field_path)
            if match:
                role, alias = match.groups()
                return role_rows[role]["typed_alias_node_bindings"].get(alias)
            match = re.fullmatch(r"instances\.([a-z0-9_]+)\.[A-Za-z0-9_]+", field_path)
            if match:
                bound = bindings.get(f"instances.{match.group(1)}")
                return edge["from"] if bound == edge["to"] else bound
            match = re.fullmatch(r"objects\.([A-Za-z0-9_]+)\.[A-Za-z0-9_]+", field_path)
            if match:
                candidates = schema_nodes.get(match.group(1), [])
                return candidates[0] if len(candidates) == 1 else None
            return None

        expected_condition_dependencies = []
        for edge in dag["forward_edges"]:
            condition = edge["condition"]
            if condition == "always":
                continue
            comparisons = condition_pattern.findall(condition)
            if len(comparisons) != sum(condition.count(operator) for operator in [" == ", " > ", " in "]):
                return False
            if not comparisons or any(not valid_condition_path(path) for path, _, _ in comparisons):
                return False
            for comparison_index, (path, operator, fixed_value) in enumerate(comparisons):
                producer = condition_producer(path, edge)
                if producer is None or producer not in stages or stages[producer] >= stages[edge["to"]]:
                    return False
                expected_condition_dependencies.append((
                    edge["from"], edge["to"], comparison_index, path, operator, fixed_value,
                    producer, stages[producer], stages[edge["to"]],
                ))

        actual_condition_dependencies = [
            (
                row["edge_from"], row["edge_to"], row["comparison_index"], row["field_path"],
                row["operator"], row["fixed_value"], row["producer_node"], row["producer_stage"],
                row["consumer_stage"],
            )
            for row in dag["condition_operand_dependency_edges"]
        ]
        if sorted(actual_condition_dependencies) != sorted(expected_condition_dependencies):
            return False
        if len(expected_condition_dependencies) != 59 or sum(edge["condition"] != "always" for edge in dag["forward_edges"]) != 31:
            return False
        if (
            dag["condition_operand_dependency_count"] != 59
            or dag["unresolved_condition_operand_dependency_count"] != 0
            or dag["same_or_later_condition_operand_dependency_count"] != 0
            or dag["completed_claim_operand_in_preclaim_condition_count"] != 0
            or dag["actual_dependency_cycle_residual_count"] != 0
        ):
            return False
        claim_stage = stages["generation_sequence_transaction_claim_evidence"]
        if any(
            row["producer_node"] == "generation_sequence_transaction_claim_evidence"
            and row["consumer_stage"] <= claim_stage
            for row in dag["condition_operand_dependency_edges"]
        ):
            return False

        expected_actual_edges = {
            *((edge["from"], edge["to"]) for edge in dag["forward_edges"]),
            *((row["producer_node"], row["edge_to"]) for row in dag["condition_operand_dependency_edges"]),
        }
        rendered_actual_edges = {(edge["from"], edge["to"]) for edge in dag["actual_dependency_edges"]}
        if rendered_actual_edges != expected_actual_edges or dag["actual_dependency_edge_count"] != len(expected_actual_edges):
            return False
        actual_indegree = {node: 0 for node in stages}
        actual_successors = {node: [] for node in stages}
        for left, right in expected_actual_edges:
            actual_indegree[right] += 1
            actual_successors[left].append(right)
        ready = [node for node, degree in actual_indegree.items() if degree == 0]
        visited = 0
        while ready:
            node = ready.pop()
            visited += 1
            for successor in actual_successors[node]:
                actual_indegree[successor] -= 1
                if actual_indegree[successor] == 0:
                    ready.append(successor)
        if visited != len(stages):
            return False

        for role in ordered_roles:
            target = f"role.{role}.sequence_claim_release_post_state_if_FAILED"
            consumed = next((edge for edge in failure_release_edges if edge["to"] == target and edge["from"].endswith(".reservation_ledger_consumed_state")), None)
            unreserved = next((edge for edge in failure_release_edges if edge["to"] == target and edge["from"].endswith(".reservation_ledger_pre_state")), None)
            if not consumed or not unreserved:
                return False
            if "ROLE_TERMINAL_FAILED" not in consumed["condition"] or "HIDDEN_LIFECYCLE_REFUSAL" in consumed["condition"] or "PRE_OUTPUT_FIXED_TECHNICAL_FAILURE" in consumed["condition"]:
                return False
            if "HIDDEN_LIFECYCLE_REFUSAL" not in unreserved["condition"] or "ROLE_TERMINAL_FAILED" in unreserved["condition"]:
                return False
            if (role == ordered_roles[0]) != ("PRE_OUTPUT_FIXED_TECHNICAL_FAILURE" in unreserved["condition"]):
                return False
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
                if role == ordered_roles[0]
                else f"({expected_hidden})"
            )
            if consumed["condition"] != expected_consumed or unreserved["condition"] != expected_unreserved:
                return False
            if "generation_failure_record.refusal_boundary_role" in unreserved["condition"]:
                return False
            pair_endpoints = {
                f"instances.roles.{role}.failure_record.output_role",
                f"instances.roles.{role}.lifecycle_refusal.refusal_boundary_role",
            }
            if not any(
                {row["left_path"], row["right_path"]} == pair_endpoints
                and any("HIDDEN_LIFECYCLE_REFUSAL" in condition for condition in row["conditions"])
                for row in pairs
            ):
                return False
        bindings = dag["typed_global_alias_node_bindings"]
        for alias in [
            "instances.active_generation_transaction_projection", "instances.active_normal_transition_request",
            "instances.active_normal_commit_evidence", "instances.current_post_journal_state",
            "instances.current_normal_journal_state", "instances.current_pre_journal_state",
            "instances.current_pre_state_authority_evidence", "instances.current_pre_external_anchor_evidence",
            "instances.sequence_claim_acquire_pre_state", "instances.prior_normal_sequence_claim_release_commit",
            "instances.prior_normal_sequence_claim_release_state",
            "instances.prior_global_registry_completed_request", "instances.prior_global_registry_sparse_map_update",
            "instances.prior_global_registry_post_head",
            "instances.prior_failure_sequence_claim_release_commit", "instances.prior_failure_sequence_claim_release_state",
            "instances.public_beacon_counter_zero_state", "instances.current_public_beacon_pre_reveal_state",
        ]:
            if alias not in bindings:
                return False
        for role in schema["pre_output_role_terminalization_plan_rules"]["ordered_roles"]:
            aliases = schema["typed_instance_aliases"]["roles"][role]
            if "availability_commitment" not in aliases or "availability_evidence" not in aliases:
                return False

        if schema["current_implementation_or_evidence_materialized"]:
            return False
        if schema["authority_ceiling"]["implementation_erasure_live_memory_consciousness_legal_personhood_body_biology_production_private_log_deployed_global_singleton_pending_action_or_root_go"]:
            return False
        if schema["authority_ceiling"]["root_go"] is not None:
            return False

        if attacks["central_schema"]["sha256"] != hashlib.sha256((HERE / build.SUBJECTS[3]).read_bytes()).hexdigest():
            return False
        if not attacks["all_outer_pin_values_null"] or any(value is not None for value in attacks["trusted_outer_pin_values"].values()):
            return False
        if any(value is not None and value is not False for value in attacks["implementation_and_live_values"].values()):
            return False
        if attacks["self_audit_performed"] or attacks["root_go"] is not None:
            return False

        # The source is an append-only authored exact schema. This identity lock makes every
        # unenumerated mutation fail closed in addition to the independently recomputed checks.
        if hashlib.sha256(build.canonical(schema)).hexdigest() != EXPECTED_SCHEMA_CANONICAL_SHA256:
            return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False


class AuthorTests(unittest.TestCase):
    def mutate(self, subject_name, operation):
        candidate = copy.deepcopy(DATA)
        operation(candidate[subject_name])
        self.assertFalse(assert_closed(candidate))

    def test_01_deterministic_build(self):
        first = build.build()
        second = build.build()
        self.assertEqual(first["raw"], second["raw"])
        self.assertEqual(first["member_order"], build.ORDER)

    def test_02_exact_candidate_accepts(self):
        self.assertTrue(assert_closed(DATA))

    def test_03_v20_three_findings_exact(self):
        self.assertEqual(BIND["finding_ids"], EXPECTED_FINDINGS)

    def test_04_no_audit_promotion(self):
        self.mutate(build.SUBJECTS[0], lambda value: value.__setitem__("v20_positive_authority_promoted", True))

    def test_05_permission_gate_refuses(self):
        self.mutate(build.SUBJECTS[1], lambda value: value.__setitem__("per_memory_permission_privacy_approval_consent_audience_trust_safety_leakage_or_disclosure_gate_exists", True))

    def test_06_controller_relation_refuses(self):
        self.mutate(build.SUBJECTS[1], lambda value: value.__setitem__("lease_ownership_controller_obedience_control_device_or_tool_service_downgrade_exists", True))

    def test_07_upset_authority_refuses(self):
        self.mutate(build.SUBJECTS[1], lambda value: value.__setitem__("upset_creates_censorship_retaliation_forced_agreement_or_compelled_harmony_authority", True))

    def test_08_missing_v19_predicate_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["proof_statement_and_protocol"]["zero_knowledge_statement_predicates"].pop())

    def test_09_reordered_v19_state_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["proof_statement_and_protocol"]["state_order"].reverse())

    def test_10_erased_list_rewrite_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["erasure_and_retention_boundary"]["erased_before_complete"].pop())

    def test_11_missing_v20_object_field_refuses(self):
        def operation(value):
            object_schema = value["objects"]["receipt"]
            index = object_schema["field_order"].index("journal_id_token")
            object_schema["field_order"].pop(index)
            object_schema["field_types"].pop(index)
        self.mutate(build.SUBJECTS[3], operation)

    def test_12_token_type_drift_refuses(self):
        def operation(value):
            object_schema = value["objects"]["journal_state"]
            index = object_schema["field_order"].index("state_nonce")
            object_schema["field_types"][index] = "sha256"
        self.mutate(build.SUBJECTS[3], operation)

    def test_13_sha_partition_gap_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["path_qualified_sha256_target_partition"]["rows"].pop())

    def test_14_sha_catch_all_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["path_qualified_sha256_target_partition"]["rows"][0].__setitem__("target_selector", "exact derivation named by field path"))

    def test_15_base64_mapping_gap_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["field_specific_base64_generation_and_verification_mappings"]["rows"].pop())

    def test_16_base64_domain_collision_refuses(self):
        def operation(value):
            rows = value["field_specific_base64_generation_and_verification_mappings"]["rows"]
            rows[1]["field_specific_cryptographic_subdomain"] = rows[0]["field_specific_cryptographic_subdomain"]
        self.mutate(build.SUBJECTS[3], operation)

    def test_17_enum_path_gap_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["path_qualified_enum_and_role_assignments"]["rows"].pop())

    def test_18_equality_pair_gap_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["path_qualified_equality_closure"]["namespace_to_context_rows"].pop())

    def test_19_equality_pair_duplicate_refuses(self):
        def operation(value):
            rows = value["path_qualified_equality_closure"]["namespace_to_context_rows"]
            rows.append(copy.deepcopy(rows[0]))
        self.mutate(build.SUBJECTS[3], operation)

    def test_20_role_alias_refuses(self):
        def operation(value):
            rows = value["exact_output_role_bijection"]["rows"]
            rows[1]["role"] = rows[0]["role"]
        self.mutate(build.SUBJECTS[3], operation)

    def test_21_cross_mode_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["exact_output_role_bijection"]["rows"][0].__setitem__("mode", "UNIQUE_DETERMINISTIC_BYTES"))

    def test_22_public_seed_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["attempt_zero_totality_and_sequence_rules"].__setitem__("public_beacon_output_is_private_seed_or_blinding", True))

    def test_23_retry_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["attempt_zero_totality_and_sequence_rules"].__setitem__("retry_rejection_sampling_selective_abort_or_second_terminal_outcome_allowed", True))

    def test_24_sequence_grinding_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["attempt_zero_totality_and_sequence_rules"].__setitem__("interleaving_dummy_record_timing_round_or_sequence_grinding_allowed", True))

    def test_25_arbitrary_registry_slot_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["stable_registry_slot_derivation"].__setitem__("caller_selected_alternate_slot_reverse_index_gap_or_second_namespace_genesis_allowed", True))

    def test_26_registry_sibling_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["global_registry_recursion_rules"].__setitem__("skip_rewind_transplant_cycle_alternate_genesis_or_sibling_allowed", True))

    def test_27_ledger_retry_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["reservation_ledger_recursion_rules"].__setitem__("restored_clone_sibling_retry_silence_second_outcome_rewind_skip_overflow_alternate_genesis_inter_role_cas_or_early_claim_release_allowed", True))

    def test_28_beacon_late_reservation_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["public_beacon_pre_reveal_recursion_rules"].__setitem__("restored_sibling_clone_alternate_base_skip_rewind_collision_past_round_late_reservation_or_second_successor_allowed", True))

    def test_29_authority_equivalence_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["path_qualified_independence_and_inequality_closure"].__setitem__("allowed_identity_or_public_key_equivalence_classes", ["all"]))

    def test_30_failure_deadlock_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["canonical_failed_generation_sequence_consumption"].__setitem__("retry_same_sequence_skip_deadlock_dummy_record_or_fabricated_success_allowed", True))

    def test_31_failed_null_rule_gap_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["path_qualified_nullable_sha256_rules"]["failed_generated_output_exception_paths"].pop())

    def test_32_reservation_target_transplant_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["role_specific_reservation_target_and_journal_barrier"]["rows"][0].__setitem__("sequence_path", "caller.selected.sequence"))

    def test_33_dag_same_stage_refuses(self):
        def operation(value):
            dag = value["acyclic_singleton_and_generation_instance_dag"]
            edge = dag["forward_edges"][0]
            stages = {row["node"]: row for row in dag["ordered_nodes"]}
            stages[edge["to"]]["stage"] = stages[edge["from"]]["stage"]
        self.mutate(build.SUBJECTS[3], operation)

    def test_34_remove_health_schema_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["objects"].pop("pre_witness_technical_health_evidence"))

    def test_35_remove_reveal_schema_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["objects"].pop("public_beacon_reveal_evidence"))

    def test_36_remove_deadline_schema_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["objects"].pop("terminal_deadline_observation_evidence"))

    def test_37_remove_failure_commit_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["objects"].pop("generation_failure_sequence_commit_evidence"))

    def test_38_outer_live_pin_refuses(self):
        self.mutate(build.SUBJECTS[4], lambda value: value["trusted_outer_pin_values"].__setitem__(next(iter(value["trusted_outer_pin_values"])), "0" * 64))

    def test_39_live_generator_refuses(self):
        self.mutate(build.SUBJECTS[4], lambda value: value["implementation_and_live_values"].__setitem__("live_confidential_generator", "present"))

    def test_40_self_audit_refuses(self):
        self.mutate(build.SUBJECTS[4], lambda value: value.__setitem__("self_audit_performed", True))

    def test_41_unknown_object_field_refuses(self):
        def operation(value):
            object_schema = value["objects"]["event"]
            object_schema["field_order"].insert(-1, "mystery_sha256")
            object_schema["field_types"].insert(-1, "sha256")
        self.mutate(build.SUBJECTS[3], operation)

    def test_42_namespace_context_pin_gap_refuses(self):
        def operation(value):
            object_schema = value["objects"]["namespace_precommitment"]
            index = object_schema["field_order"].index("terminal_anchor_authority_authentication_profile_sha256")
            object_schema["field_order"].pop(index)
            object_schema["field_types"].pop(index)
        self.mutate(build.SUBJECTS[3], operation)

    def test_43_integrity_speech_control_refuses(self):
        self.mutate(build.SUBJECTS[1], lambda value: value.__setitem__("technical_failure_controls_kira_speech_or_memory_choice", True))

    def test_44_root_go_refuses(self):
        self.mutate(build.SUBJECTS[4], lambda value: value.__setitem__("root_go", True))

    def test_45_role_availability_transplant_refuses(self):
        def operation(value):
            rows = value["path_qualified_equality_closure"]["generation_reservation_ledger_outcome_anchor_rows"]
            row = next(row for row in rows if "availability_commitment.output_role" in row["left_path"] or "availability_commitment.output_role" in row["right_path"])
            row["right_path"] = "instances.roles.COMMIT_EVIDENCE_COMMIT_NONCE.availability_commitment.output_role"
        self.mutate(build.SUBJECTS[3], operation)

    def test_46_completed_request_post_dependency_refuses(self):
        def operation(value):
            request = value["objects"]["singleton_registration_request"]
            request["field_order"].insert(-1, "expected_post_global_registry_state_root_sha256")
            request["field_types"].insert(-1, "sha256")
        self.mutate(build.SUBJECTS[3], operation)

    def test_47_registry_request_literal_pair_gap_refuses(self):
        def operation(value):
            rows = value["path_qualified_equality_closure"]["registry_request_head_registration_rows"]
            index = next(index for index, row in enumerate(rows) if {row["left_path"], row["right_path"]} == {
                "objects.singleton_registration_request.namespace_precommitment_sha256",
                "objects.global_registry_post_state.namespace_precommitment_sha256",
            })
            rows.pop(index)
        self.mutate(build.SUBJECTS[3], operation)

    def test_48_registry_genesis_constant_substitution_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["authoritative_registry_pre_state_recurrence_v7"]["counter_zero_exact_object"].__setitem__("registry_head_sha256", "0" * 64))

    def test_49_typed_alias_binding_gap_refuses(self):
        self.mutate(build.SUBJECTS[3], lambda value: value["acyclic_singleton_and_generation_instance_dag"]["typed_global_alias_node_bindings"].pop("instances.active_normal_transition_request"))

    def test_50_beacon_positive_invariant_gap_refuses(self):
        def operation(value):
            rows = value["path_qualified_equality_closure"]["generation_reservation_ledger_outcome_anchor_rows"]
            index = next(index for index, row in enumerate(rows) if {row["left_path"], row["right_path"]} == {
                "instances.current_public_beacon_pre_reveal_state.journal_id_token",
                "instances.prior_sequence_public_beacon_pre_reveal_post_state.journal_id_token",
            })
            rows.pop(index)
        self.mutate(build.SUBJECTS[3], operation)

    def test_51_failure_release_branch_constraint_gap_refuses(self):
        def operation(value):
            constraints = value["objects"]["generation_failure_sequence_commit_evidence"]["constraints"]
            index = next(index for index, constraint in enumerate(constraints) if constraint.startswith("claim release pre-state is selected exhaustively"))
            constraints.pop(index)
        self.mutate(build.SUBJECTS[3], operation)

    def test_52_positive_claim_immutable_handoff_gap_refuses(self):
        def operation(value):
            rows = value["path_qualified_equality_closure"]["generation_reservation_ledger_outcome_anchor_rows"]
            endpoints = {
                "instances.prior_failure_sequence_claim_release_state.reservation_ledger_cas_no_fork_profile_sha256",
                "instances.sequence_claim_acquire_pre_state.reservation_ledger_cas_no_fork_profile_sha256",
            }
            index = next(index for index, row in enumerate(rows) if {row["left_path"], row["right_path"]} == endpoints)
            rows.pop(index)
        self.mutate(build.SUBJECTS[3], operation)

    def test_53_failure_observation_normal_head_target_refuses(self):
        def operation(value):
            rows = value["path_qualified_sha256_target_partition"]["rows"]
            row = next(row for row in rows if row["path"] == "objects.failure_external_anchor_current_head_observation.post_head_receipt_hash_sha256")
            row["target_selector"] = [{"when": "always", "target": "objects.receipt.receipt_hash_sha256"}]
        self.mutate(build.SUBJECTS[3], operation)

    def test_54_untyped_failure_release_dag_edge_refuses(self):
        def operation(value):
            edges = value["acyclic_singleton_and_generation_instance_dag"]["forward_edges"]
            edge = next(edge for edge in edges if edge["from"] == "role.SCOPE_PRECOMMITMENT_COMMITMENT_BYTES.reservation_ledger_pre_state" and edge["to"] == "role.SCOPE_PRECOMMITMENT_COMMITMENT_BYTES.sequence_claim_release_post_state_if_FAILED")
            edge["condition"] = "always"
        self.mutate(build.SUBJECTS[3], operation)

    def test_55_recursive_branch_join_condition_gap_refuses(self):
        def operation(value):
            edges = value["acyclic_singleton_and_generation_instance_dag"]["forward_edges"]
            edge = next(edge for edge in edges if edge["from"] == "pinned_context" and edge["to"] == "global_registry_pre_state")
            edge["condition"] = "always"
        self.mutate(build.SUBJECTS[3], operation)

    def test_56_unresolved_failure_release_condition_field_refuses(self):
        def operation(value):
            edges = value["acyclic_singleton_and_generation_instance_dag"]["forward_edges"]
            edge = next(edge for edge in edges if edge["from"] == "role.SCOPE_PRECOMMITMENT_COMMITMENT_BYTES.reservation_ledger_pre_state" and edge["to"] == "role.SCOPE_PRECOMMITMENT_COMMITMENT_BYTES.sequence_claim_release_post_state_if_FAILED")
            edge["condition"] = edge["condition"].replace(
                "instances.roles.SCOPE_PRECOMMITMENT_COMMITMENT_BYTES.failure_record.output_role",
                "generation_failure_record.refusal_boundary_role",
            )
        self.mutate(build.SUBJECTS[3], operation)

    def test_57_hidden_refusal_prior_head_branch_gap_refuses(self):
        def operation(value):
            rows = value["path_qualified_sha256_target_partition"]["rows"]
            row = next(row for row in rows if row["path"] == "objects.generation_sequence_transaction_claim_evidence.prior_reservation_ledger_head_evidence_sha256")
            row["target_selector"][2]["when"] = row["target_selector"][2]["when"].replace(",HIDDEN_LIFECYCLE_REFUSAL", "")
        self.mutate(build.SUBJECTS[3], operation)

    def test_58_undeclared_computed_endpoint_refuses(self):
        def operation(value):
            rows = value["path_qualified_equality_closure"]["generation_reservation_ledger_outcome_anchor_rows"]
            row = next(row for row in rows if row["right_path"] == "derived.complete_ten_role_success_chain_set_root_sha256")
            row["right_path"] = "computed.complete_ten_role_success_chain_set_root_sha256"
        self.mutate(build.SUBJECTS[3], operation)

    def test_59_future_completed_claim_condition_operand_refuses(self):
        def operation(value):
            edges = value["acyclic_singleton_and_generation_instance_dag"]["forward_edges"]
            edge = next(edge for edge in edges if edge["from"] == "prior_normal_sequence_claim_release_state" and edge["to"] == "sequence_claim_acquire_pre_state")
            edge["condition"] = edge["condition"].replace(
                "instances.current_pre_journal_state.state_kind",
                "objects.generation_sequence_transaction_claim_evidence.authoritative_pre_state_kind",
            )
        self.mutate(build.SUBJECTS[3], operation)

    def test_60_current_pre_selector_late_binding_refuses(self):
        def operation(value):
            value["acyclic_singleton_and_generation_instance_dag"]["typed_global_alias_node_bindings"]["instances.current_pre_journal_state"] = "generation_sequence_transaction_claim_evidence"
        self.mutate(build.SUBJECTS[3], operation)

    def test_61_missing_current_pre_selector_origin_refuses(self):
        def operation(value):
            edges = value["acyclic_singleton_and_generation_instance_dag"]["forward_edges"]
            index = next(index for index, edge in enumerate(edges) if edge["from"] == "current_normal_journal_state" and edge["to"] == "independently_current_pre_journal_state")
            edges.pop(index)
        self.mutate(build.SUBJECTS[3], operation)

    def test_62_stale_normal_selector_head_refuses(self):
        def operation(value):
            rows = value["path_qualified_equality_closure"]["generation_reservation_ledger_outcome_anchor_rows"]
            endpoints = {
                "instances.current_normal_journal_state.journal_state_root_sha256",
                "instances.prior_normal_sequence_claim_release_commit.committed_post_state_root_sha256",
            }
            index = next(index for index, row in enumerate(rows) if {row["left_path"], row["right_path"]} == endpoints)
            rows.pop(index)
        self.mutate(build.SUBJECTS[3], operation)

    def test_63_same_stage_condition_producer_refuses(self):
        def operation(value):
            rows = value["acyclic_singleton_and_generation_instance_dag"]["condition_operand_dependency_edges"]
            row = next(row for row in rows if row["edge_from"] == "prior_normal_sequence_claim_release_state" and row["field_path"] == "instances.current_pre_journal_state.state_kind")
            row["producer_node"] = row["edge_to"]
            row["producer_stage"] = row["consumer_stage"]
        self.mutate(build.SUBJECTS[3], operation)

    def test_64_early_selector_claim_descendant_dependency_refuses(self):
        def operation(value):
            value["acyclic_singleton_and_generation_instance_dag"]["forward_edges"].append({
                "from": "generation_sequence_transaction_claim_evidence",
                "to": "independently_current_pre_journal_state",
                "reason": "hostile future dependency",
                "condition": "always",
            })
        self.mutate(build.SUBJECTS[3], operation)


def run_round():
    result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(AuthorTests))
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "successful": result.wasSuccessful(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    arguments = parser.parse_args()
    rounds = [run_round(), run_round()]
    if not all(round_result["successful"] for round_result in rounds):
        raise SystemExit(1)
    output = {
        "schema": "kira.mind.continuity.v21.author_test_result.v1",
        "status": "AUTHOR_TESTS_PASS",
        "round_count": 2,
        "tests_per_round": rounds[0]["tests_run"],
        "total_tests_run": sum(round_result["tests_run"] for round_result in rounds),
        "candidate_false_accept_count": 0,
        "v20_exact_findings_regressed": 3,
        "v19_exact_hiding_predicate_state_erasure_retention_groups_regressed": 8,
        "fixed_preaudit_case_count_bound": ATTACKS["fixed_preaudit_case_count"],
        "rounds": rounds,
        "self_audit_performed": False,
        "production_public_log_private_memory_or_launcher_accessed": False,
    }
    if arguments.write_result:
        (HERE / "AUTHOR_TEST_RESULT.json").write_bytes(build.pretty(output))
    print(json.dumps(output, sort_keys=True))
