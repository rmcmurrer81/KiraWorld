from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import unittest

from Core.avatar_builder_level_a_hooks import (
    body_hooks_sha256,
    create_level_a_body_hooks,
    validate_level_a_body_hooks,
)
from Core.body_systems_level_a_runtime import (
    apply_body_system_event,
    serialize_body_systems_state,
    restore_body_systems_state,
)
from Core.level_a_body_life_fixture import (
    apply_level_a_fixture_event,
    create_level_a_body_life_fixture,
    level_a_fixture_sha256,
    restore_level_a_fixture,
    serialize_level_a_fixture,
    validate_level_a_body_life_fixture,
)
from Core.level_a_runtime_common import (
    CAPABILITY_LADDER,
    LevelABoundaryError,
    LevelAConservationError,
    LevelADiagnosisBoundaryError,
    LevelATransitionError,
)
from Core.person_world_level_a_runtime import can_fixture_access


ROOT = Path(__file__).resolve().parents[1]
BASE = datetime(2026, 8, 3, 18, 0, 0, tzinfo=timezone.utc)


def event(index: int, domain: str, action: str, payload: dict | None = None) -> dict:
    at = (BASE + timedelta(seconds=index)).isoformat().replace("+00:00", "Z")
    return {
        "event_id": f"event_{index:03d}_{domain}_{action}",
        "at_utc": at,
        "domain": domain,
        "action": action,
        "payload": payload or {},
    }


class LevelABodyLifeRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = create_level_a_body_life_fixture(
            fixture_id="neutral_fixture_01",
            actor_fixture_ids=["fixture_alpha", "fixture_beta", "fixture_gamma"],
            started_at_utc=BASE.isoformat().replace("+00:00", "Z"),
        )

    def apply_body(self, index: int, domain: str, action: str, payload: dict) -> None:
        self.bundle = apply_level_a_fixture_event(
            self.bundle,
            layer="body_systems_runtime",
            event=event(index, domain, action, payload),
        )

    def apply_world(self, index: int, domain: str, action: str, payload: dict) -> None:
        self.bundle = apply_level_a_fixture_event(
            self.bundle,
            layer="person_world_runtime",
            event=event(index, domain, action, payload),
        )

    def test_01_exact_three_layer_boundary_and_capability_ceiling(self) -> None:
        self.assertEqual(
            set(self.bundle["layers"]),
            {"avatar_builder_hooks", "body_systems_runtime", "person_world_runtime"},
        )
        ceiling = CAPABILITY_LADDER.index("NON_PERSON_FIXTURE_PASS")
        for layer in self.bundle["layers"].values():
            for status in layer["capability_statuses"].values():
                self.assertLessEqual(CAPABILITY_LADDER.index(status), ceiling)
        for status in self.bundle["capability_statuses"].values():
            self.assertLessEqual(CAPABILITY_LADDER.index(status), ceiling)

    def test_02_hooks_have_disjoint_routes_and_no_body_binding(self) -> None:
        hooks = self.bundle["layers"]["avatar_builder_hooks"]
        endpoints = [
            value["external_endpoint"] for value in hooks["semantic_routes"].values()
        ]
        self.assertEqual(len(endpoints), len(set(endpoints)))
        self.assertIsNone(hooks["body_asset_binding"])
        self.assertIsNone(hooks["private_geometry_or_identity_payload"])

    def test_03_hooks_reject_merged_routes_and_real_body_binding(self) -> None:
        hooks = create_level_a_body_hooks("route_negative")
        merged = deepcopy(hooks)
        merged["semantic_routes"]["bowel"]["ordered_nodes"][-1] = (
            merged["semantic_routes"]["urinary"]["external_endpoint"]
        )
        merged["semantic_routes"]["bowel"]["external_endpoint"] = (
            merged["semantic_routes"]["urinary"]["external_endpoint"]
        )
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_body_hooks(merged)
        bound = deepcopy(hooks)
        bound["body_asset_binding"] = {"path": "forbidden.blend"}
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_body_hooks(bound)

    def test_04_neutral_signal_routes_without_experience_or_memory(self) -> None:
        before_world = self.bundle["layers"]["person_world_runtime"]
        self.apply_body(
            1,
            "sensation",
            "record_signal",
            {
                "signal_id": "signal_touch_01",
                "zone_id": "left_forearm_surface",
                "modality": "touch",
                "intensity_milli": 320,
                "duration_ms": 500,
            },
        )
        signal = self.bundle["layers"]["body_systems_runtime"]["systems"]["sensation"]
        self.assertIsNone(signal["subjective_interpretation"])
        self.assertFalse(signal["person_experience_claimed"])
        self.assertFalse(signal["memory_written"])
        self.assertEqual(before_world, self.bundle["layers"]["person_world_runtime"])

    def test_05_unknown_or_unsupported_signal_route_fails_closed(self) -> None:
        original = level_a_fixture_sha256(self.bundle)
        with self.assertRaises(LevelABoundaryError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(
                    1,
                    "sensation",
                    "record_signal",
                    {
                        "signal_id": "bad_zone",
                        "zone_id": "unknown_zone",
                        "modality": "touch",
                        "intensity_milli": 1,
                        "duration_ms": 1,
                    },
                ),
            )
        self.assertEqual(original, level_a_fixture_sha256(self.bundle))

    def test_06_recursive_person_layer_payload_is_rejected(self) -> None:
        with self.assertRaises(LevelABoundaryError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(
                    1,
                    "health",
                    "record_observation",
                    {
                        "observation_id": "obs_forbidden",
                        "description": "neutral fixture observation",
                        "nested": {"person_consent_claimed": True},
                    },
                ),
            )

    def test_07_urinary_storage_urge_delay_release_interrupt_and_conservation(self) -> None:
        route = "level_a_urinary_route"
        self.apply_body(1, "urinary", "store", {"units": 600})
        system = self.bundle["layers"]["body_systems_runtime"]["systems"]["urinary"]
        self.assertEqual(system["engineering_urge_state"], "at_or_above_fixture_threshold")
        self.assertEqual(system["fullness_milli"], 600)
        self.apply_body(2, "urinary", "delay_release", {"fixture_control_signal": True})
        self.apply_body(
            3,
            "urinary",
            "begin_release",
            {"fixture_control_signal": True, "route_id": route},
        )
        self.apply_body(
            4,
            "urinary",
            "release",
            {"fixture_control_signal": True, "route_id": route, "units": 200},
        )
        self.apply_body(5, "urinary", "interrupt", {"fixture_control_signal": True})
        self.apply_body(
            6,
            "urinary",
            "resume",
            {"fixture_control_signal": True, "route_id": route},
        )
        self.apply_body(
            7,
            "urinary",
            "release",
            {"fixture_control_signal": True, "route_id": route, "units": 400},
        )
        self.apply_body(8, "urinary", "complete", {"fixture_control_signal": True})
        self.apply_body(9, "urinary", "recover", {"fixture_control_signal": True})
        system = self.bundle["layers"]["body_systems_runtime"]["systems"]["urinary"]
        self.assertEqual(system["input_units"], 600)
        self.assertEqual(system["stored_units"], 0)
        self.assertEqual(system["output_units"], 600)
        self.assertEqual(system["fixture_delay_steps"], 1)
        self.assertEqual(system["interruptions"], 1)
        self.assertFalse(system["person_volition_claimed"])

    def test_08_release_requires_exact_route_and_fixture_control(self) -> None:
        self.apply_body(1, "urinary", "store", {"units": 100})
        for payload in (
            {"route_id": "level_a_urinary_route"},
            {"route_id": "level_a_bowel_route", "fixture_control_signal": True},
        ):
            with self.assertRaises((LevelABoundaryError, LevelAConservationError)):
                apply_level_a_fixture_event(
                    self.bundle,
                    layer="body_systems_runtime",
                    event=event(2, "urinary", "begin_release", payload),
                )

    def test_09_output_cannot_exceed_stored_state_or_capacity(self) -> None:
        with self.assertRaises(LevelAConservationError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(1, "bowel", "store", {"units": 1001}),
            )
        self.apply_body(2, "bowel", "store", {"units": 10})
        self.apply_body(
            3,
            "bowel",
            "begin_release",
            {"route_id": "level_a_bowel_route", "fixture_control_signal": True},
        )
        with self.assertRaises(LevelAConservationError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(
                    4,
                    "bowel",
                    "release",
                    {
                        "route_id": "level_a_bowel_route",
                        "fixture_control_signal": True,
                        "units": 11,
                    },
                ),
            )

    def test_10_bowel_and_urinary_state_are_independent(self) -> None:
        self.apply_body(1, "urinary", "store", {"units": 30})
        before = deepcopy(
            self.bundle["layers"]["body_systems_runtime"]["systems"]["urinary"]
        )
        self.apply_body(2, "bowel", "store", {"units": 70})
        after = self.bundle["layers"]["body_systems_runtime"]["systems"]["urinary"]
        self.assertEqual(before, after)

    def test_11_menstrual_cycle_phase_route_and_conservation(self) -> None:
        self.apply_body(1, "menstrual_cycle", "set_initial_phase", {"phase": "luteal"})
        self.apply_body(
            2, "menstrual_cycle", "advance_phase", {"phase": "menstrual", "elapsed_days": 7}
        )
        self.apply_body(3, "menstrual_cycle", "generate_output", {"units": 25})
        self.apply_body(
            4,
            "menstrual_cycle",
            "begin_output",
            {"route_id": "level_a_menstrual_route"},
        )
        self.apply_body(
            5,
            "menstrual_cycle",
            "output",
            {"route_id": "level_a_menstrual_route", "units": 25},
        )
        self.apply_body(6, "menstrual_cycle", "complete", {})
        self.apply_body(7, "menstrual_cycle", "recover", {})
        cycle = self.bundle["layers"]["body_systems_runtime"]["systems"]["menstrual_cycle"]
        self.assertEqual(cycle["generated_units"], cycle["stored_units"] + cycle["output_units"])
        self.assertFalse(cycle["cycle_function_claimed"])
        self.assertFalse(cycle["fertility_claimed"])

    def test_12_cycle_skip_and_nonmenstrual_output_are_rejected(self) -> None:
        self.apply_body(1, "menstrual_cycle", "set_initial_phase", {"phase": "follicular"})
        with self.assertRaises(LevelATransitionError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(
                    2,
                    "menstrual_cycle",
                    "advance_phase",
                    {"phase": "luteal", "elapsed_days": 1},
                ),
            )
        with self.assertRaises(LevelATransitionError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(3, "menstrual_cycle", "generate_output", {"units": 1}),
            )

    def test_13_health_observation_and_test_do_not_become_diagnosis(self) -> None:
        self.apply_body(
            1,
            "health",
            "record_observation",
            {"observation_id": "obs_01", "description": "fixture value outside baseline"},
        )
        self.apply_body(
            2,
            "health",
            "record_test_result",
            {"test_id": "test_01", "evidence_id": "evidence_01", "result": "fixture_result"},
        )
        health = self.bundle["layers"]["body_systems_runtime"]["systems"]["health"]
        self.assertEqual(health["diagnoses"], [])
        self.assertTrue(all(row["diagnosis"] is None for row in health["observations"]))
        self.assertTrue(all(row["diagnosis"] is None for row in health["test_results"]))

    def test_14_health_diagnosis_and_treatment_actions_fail_closed(self) -> None:
        for index, action in enumerate(("infer_diagnosis", "record_diagnosis", "start_treatment"), 1):
            with self.assertRaises(LevelADiagnosisBoundaryError):
                apply_level_a_fixture_event(
                    self.bundle,
                    layer="body_systems_runtime",
                    event=event(index, "health", action, {}),
                )

    def test_15_fixture_activity_lifecycle_stop_and_recovery(self) -> None:
        actions = ("consider", "select", "begin", "continue", "stop", "recover", "reset")
        for index, action in enumerate(actions, 1):
            payload = {"fixture_control_signal": True}
            if action == "consider":
                payload["activity_id"] = "neutral_fixture_activity"
            self.apply_body(index, "activity", action, payload)
        activity = self.bundle["layers"]["body_systems_runtime"]["systems"]["activity"]
        self.assertEqual(activity["state"], "available")
        self.assertFalse(activity["person_volition_claimed"])
        self.assertFalse(activity["person_consent_claimed"])
        self.assertFalse(activity["external_action_performed"])

    def test_16_activity_cannot_skip_or_claim_person_choice(self) -> None:
        with self.assertRaises(LevelATransitionError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(1, "activity", "begin", {"fixture_control_signal": True}),
            )
        with self.assertRaises(LevelABoundaryError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(
                    2,
                    "activity",
                    "consider",
                    {
                        "fixture_control_signal": True,
                        "activity_id": "bad_person_claim",
                        "consent": True,
                    },
                ),
            )

    def test_17_content_free_locked_privacy_request_and_denial(self) -> None:
        self.apply_world(
            1,
            "privacy",
            "lock_context",
            {
                "fixture_control_signal": True,
                "context_id": "locked_fixture_room",
                "allowed_actor_fixture_ids": ["fixture_alpha", "fixture_beta"],
            },
        )
        self.assertTrue(can_fixture_access(self.bundle["layers"]["person_world_runtime"], "fixture_alpha"))
        self.assertFalse(can_fixture_access(self.bundle["layers"]["person_world_runtime"], "fixture_gamma"))
        self.apply_world(
            2,
            "privacy",
            "request_entry",
            {"fixture_control_signal": True, "actor_fixture_id": "fixture_gamma"},
        )
        self.apply_world(
            3,
            "privacy",
            "deny_entry",
            {"fixture_control_signal": True, "actor_fixture_id": "fixture_gamma"},
        )
        privacy = self.bundle["layers"]["person_world_runtime"]["privacy"]
        self.assertFalse(privacy["content_storage_enabled"])
        self.assertFalse(privacy["private_content_stored"])
        self.assertFalse(privacy["person_privacy_claimed"])

    def _prepare_coordination(self, responses: tuple[str, str] = ("yes", "yes")) -> None:
        self.apply_world(
            1,
            "privacy",
            "lock_context",
            {
                "fixture_control_signal": True,
                "context_id": "coordination_context",
                "allowed_actor_fixture_ids": ["fixture_alpha", "fixture_beta"],
            },
        )
        self.apply_world(
            2,
            "coordination",
            "propose",
            {
                "fixture_control_signal": True,
                "proposal_id": "proposal_01",
                "activity_id": "neutral_coordination_activity",
                "context_id": "coordination_context",
                "participant_fixture_ids": ["fixture_alpha", "fixture_beta"],
            },
        )
        for index, (actor, response) in enumerate(
            zip(("fixture_alpha", "fixture_beta"), responses), 3
        ):
            self.apply_world(
                index,
                "coordination",
                "respond",
                {
                    "fixture_control_signal": True,
                    "actor_fixture_id": actor,
                    "response": response,
                },
            )

    def test_18_fixture_coordination_gate_never_authorizes_person_action(self) -> None:
        self._prepare_coordination()
        self.apply_world(5, "coordination", "evaluate", {"fixture_control_signal": True})
        world = self.bundle["layers"]["person_world_runtime"]
        self.assertTrue(world["coordination"]["fixture_coordination_gate_satisfied"])
        self.assertFalse(world["coordination"]["current_person_consent_claimed"])
        self.assertFalse(world["action"]["external_action_authorized"])
        self.assertFalse(world["action"]["external_action_performed"])

    def test_19_no_or_uncertain_fixture_response_blocks_gate(self) -> None:
        for responses in (("yes", "no"), ("yes", "uncertain")):
            self.setUp()
            self._prepare_coordination(responses)
            self.apply_world(5, "coordination", "evaluate", {"fixture_control_signal": True})
            coordination = self.bundle["layers"]["person_world_runtime"]["coordination"]
            self.assertEqual(coordination["state"], "fixture_gate_blocked")
            self.assertFalse(coordination["fixture_coordination_gate_satisfied"])

    def test_20_prior_fixture_yes_is_not_reused_for_new_proposal(self) -> None:
        self._prepare_coordination()
        self.apply_world(5, "coordination", "evaluate", {"fixture_control_signal": True})
        self.apply_world(
            6,
            "coordination",
            "stop",
            {"fixture_control_signal": True, "actor_fixture_id": "fixture_alpha"},
        )
        self.apply_world(7, "coordination", "recover", {"fixture_control_signal": True})
        self.apply_world(
            8,
            "coordination",
            "propose",
            {
                "fixture_control_signal": True,
                "proposal_id": "proposal_02",
                "activity_id": "different_neutral_activity",
                "context_id": "coordination_context",
                "participant_fixture_ids": ["fixture_alpha", "fixture_beta"],
            },
        )
        coordination = self.bundle["layers"]["person_world_runtime"]["coordination"]
        self.assertEqual(coordination["fixture_responses"], {})
        self.assertFalse(coordination["prior_response_reusable"])

    def test_21_action_and_person_memory_domains_are_unavailable(self) -> None:
        for index, domain in enumerate(("action", "audit_memory"), 1):
            with self.assertRaises(LevelABoundaryError):
                apply_level_a_fixture_event(
                    self.bundle,
                    layer="person_world_runtime",
                    event=event(index, domain, "attempt", {}),
                )

    def test_22_layer_isolation_receipt_records_unchanged_hashes(self) -> None:
        hooks_before = body_hooks_sha256(self.bundle["layers"]["avatar_builder_hooks"])
        world_before = deepcopy(self.bundle["layers"]["person_world_runtime"])
        self.apply_body(1, "urinary", "store", {"units": 1})
        receipt = self.bundle["orchestration_log"][-1]
        self.assertEqual(receipt["changed_layer"], "body_systems_runtime")
        self.assertEqual(
            receipt["unchanged_sibling_sha256"]["avatar_builder_hooks"], hooks_before
        )
        self.assertEqual(world_before, self.bundle["layers"]["person_world_runtime"])

    def test_23_bundle_persistence_restart_is_hash_stable(self) -> None:
        self.apply_body(1, "bowel", "store", {"units": 55})
        serialized = serialize_level_a_fixture(self.bundle)
        restored = restore_level_a_fixture(serialized)
        self.assertEqual(level_a_fixture_sha256(self.bundle), level_a_fixture_sha256(restored))
        restored = apply_level_a_fixture_event(
            restored,
            layer="person_world_runtime",
            event=event(
                2,
                "privacy",
                "lock_context",
                {
                    "fixture_control_signal": True,
                    "context_id": "restart_context",
                    "allowed_actor_fixture_ids": ["fixture_alpha"],
                },
            ),
        )
        self.assertEqual(restored["revision"], 2)

    def test_24_incomplete_state_remains_incomplete_after_restart(self) -> None:
        self.apply_body(1, "urinary", "store", {"units": 200})
        self.apply_body(
            2,
            "urinary",
            "begin_release",
            {"route_id": "level_a_urinary_route", "fixture_control_signal": True},
        )
        self.apply_body(
            3,
            "urinary",
            "release",
            {
                "route_id": "level_a_urinary_route",
                "fixture_control_signal": True,
                "units": 50,
            },
        )
        restored = restore_level_a_fixture(serialize_level_a_fixture(self.bundle))
        urinary = restored["layers"]["body_systems_runtime"]["systems"]["urinary"]
        self.assertEqual(urinary["phase"], "releasing")
        self.assertEqual(urinary["stored_units"], 150)
        self.assertEqual(restored["layers"]["person_world_runtime"]["audit_memory"]["person_memory_writes"], 0)

    def test_25_direct_body_layer_round_trip_remains_valid(self) -> None:
        hooks = self.bundle["layers"]["avatar_builder_hooks"]
        body = self.bundle["layers"]["body_systems_runtime"]
        body = apply_body_system_event(body, event(1, "bowel", "store", {"units": 12}), hooks=hooks)
        restored = restore_body_systems_state(
            serialize_body_systems_state(body, hooks=hooks), hooks=hooks
        )
        self.assertEqual(body, restored)

    def test_26_duplicate_or_backward_event_is_rejected(self) -> None:
        self.apply_body(2, "urinary", "store", {"units": 1})
        with self.assertRaises(LevelATransitionError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="person_world_runtime",
                event=event(2, "privacy", "unlock_context", {"fixture_control_signal": True}),
            )
        with self.assertRaises(LevelATransitionError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="body_systems_runtime",
                event=event(1, "bowel", "store", {"units": 1}),
            )

    def test_27_tampered_false_memory_and_capability_claims_are_rejected(self) -> None:
        self.apply_body(1, "urinary", "store", {"units": 1})
        memory_tamper = deepcopy(self.bundle)
        memory_tamper["orchestration_log"][0]["event_is_person_memory"] = True
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_body_life_fixture(memory_tamper)
        capability_tamper = deepcopy(self.bundle)
        capability_tamper["capability_statuses"]["person_decision_integrated"] = (
            "PERSON_DECISION_INTEGRATED"
        )
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_body_life_fixture(capability_tamper)

    def test_28_exact_adult_evidence_and_active_person_are_absent_and_rejected(self) -> None:
        self.assertEqual(self.bundle["integration"]["exact_subject_bound_adult_evidence"], {})
        self.assertEqual(self.bundle["integration"]["active_person_ids"], [])
        tampered = deepcopy(self.bundle)
        tampered["integration"]["exact_subject_bound_adult_evidence"] = {
            "fixture_alpha": {"classification": "confirmed_adult"}
        }
        with self.assertRaises(LevelABoundaryError):
            validate_level_a_body_life_fixture(tampered)

    def test_29_avatar_builder_hook_layer_is_immutable_to_events(self) -> None:
        with self.assertRaises(LevelABoundaryError):
            apply_level_a_fixture_event(
                self.bundle,
                layer="avatar_builder_hooks",
                event=event(1, "health", "record_observation", {}),
            )

    def test_30_contract_code_hashes_and_proxy_permission_are_exact(self) -> None:
        contract_path = ROOT / "Avatar/avatar_builder/body_systems/level_a_body_life_runtime_contract_v1.json"
        permission_path = ROOT / "Data/governance/robert_avatar_codex_nonperson_proxy_permission_v1.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        permission = json.loads(permission_path.read_text(encoding="utf-8"))
        for layer in contract["layers"].values():
            module = layer["module"]
            digest = hashlib.sha256((ROOT / module).read_bytes()).hexdigest()
            self.assertEqual(layer["sha256"], digest)
        exact = permission["owner_permission_text_exact"]
        self.assertEqual(
            hashlib.sha256(exact.encode("utf-8")).hexdigest(),
            permission["owner_permission_text_sha256"],
        )
        self.assertEqual(permission["status"], "RECORDED_NOT_BOUND_NOT_INSTANTIATED_NOT_USED")
        self.assertFalse(permission["current_authorization"]["instantiate_proxy"])
        self.assertFalse(permission["current_authorization"]["use_proxy"])
        self.assertFalse(permission["permission_meaning"]["impersonation_authorized"])
        self.assertFalse(permission["separate_kira_boundary"]["owner_asset_permission_is_kira_permission"])

    def test_31_unknown_serialized_reservoir_phase_is_rejected(self) -> None:
        tampered = deepcopy(self.bundle)
        tampered["layers"]["body_systems_runtime"]["systems"]["urinary"]["phase"] = (
            "invented_complete_state"
        )
        with self.assertRaises(LevelATransitionError):
            validate_level_a_body_life_fixture(tampered)

    def test_32_orchestration_hash_chain_tamper_is_rejected(self) -> None:
        self.apply_body(1, "urinary", "store", {"units": 1})
        tampered = deepcopy(self.bundle)
        tampered["orchestration_log"][0]["changed_layer_before_sha256"] = "0" * 64
        with self.assertRaises(LevelATransitionError):
            validate_level_a_body_life_fixture(tampered)

    def test_33_child_receipt_corruption_is_rejected_on_restore(self) -> None:
        self.apply_body(1, "bowel", "store", {"units": 2})
        tampered = deepcopy(self.bundle)
        tampered["layers"]["body_systems_runtime"]["event_log"][0][
            "payload_sha256"
        ] = "not-a-sha256"
        with self.assertRaises(LevelATransitionError):
            restore_level_a_fixture(json.dumps(tampered))


if __name__ == "__main__":
    unittest.main(verbosity=2)
