from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from Core.shared_person_growth_capabilities_v3 import (
    GrowthAuthorityError,
    GrowthCapabilityError,
    GrowthReplayError,
    ProtectedGrowthController,
    build_fresh_capability_profile,
)
from Core.shared_person_growth_v3_integration_candidate_v1 import (
    INVENTORY_PATH,
    GrowthIntegrationAuthorityError,
    GrowthIntegrationError,
    GrowthIntegrationRecoveryRequired,
    SharedGrowthV3IntegrationAdapter,
    current_route_coverage_inventory,
    inventory_sha256,
    load_integration_inventory,
    validate_public_attachment,
)
from tools.create_temporary_ai_growth_profile_v3 import build_fresh_creator_bundle


ROOT = Path(__file__).resolve().parents[1]
V3_PROTECTED = {
    "Data/foundation/shared_person_growth_capabilities_v3.json":
        "1a74c9dc778cd38aec3eb2d5533439de5cd5884e2ed73cbe591f50a3403e3756",
    "Core/shared_person_growth_capabilities_v3.py":
        "8250c657486981ba5ce41892da373adc7df49c462865dc8be75af80f542eb3a2",
    "tools/create_temporary_ai_growth_profile_v3.py":
        "f7d3cbaf2b06be938377480e6c7906c296f3236ce115da5afbfa3edd89f0d53e",
    "TemporaryAI/config/shared_person_growth_capability_template_v3.json":
        "09d273ef0af98ac138da568d2d4192e1521a5999e24f7c4302e7fe78a939be2d",
    "Testing/test_shared_person_growth_capabilities_v3.py":
        "37a8a27179083b9b3a90f98a69910edb75f4a9fda68e3d383953d22ae86180ca",
    "RecoverySprint/continuation_20260811/shared_person_growth_capabilities_v3_fresh_static_audit/attempt_01/CHECKPOINT.md":
        "50526169ef05aea0a8db078047a9581bcd74aaf5829b73a0c0ba559b152afd15",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SharedGrowthV3IntegrationCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temp.name)
        self.controller_secret = bytes(range(1, 33))
        self.integration_secret = bytes(range(33, 65))
        self.controller = ProtectedGrowthController(
            controller_id="growth_integration_test_controller",
            authority_secret=self.controller_secret,
            ledger_root=self.temp_root / "growth_ledger",
        )
        self.adapter = SharedGrowthV3IntegrationAdapter(
            authority_controller=self.controller,
            authority_identity=self.controller.identity,
            integration_secret=self.integration_secret,
            ledger_root=self.temp_root / "integration_ledger",
            staging_root=self.temp_root / "staging",
        )
        self.inventory = load_integration_inventory()
        self.counter = 0

    def tearDown(self) -> None:
        self.temp.cleanup()

    def next_id(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}:{self.counter:04d}"

    def person(self, person_id: str) -> dict:
        return next(item for item in self.inventory["people"] if item["person_id"] == person_id)

    def route(self, route_id: str) -> dict:
        return next(item for item in self.inventory["routes"] if item["route_id"] == route_id)

    def build_profile(
        self,
        person_id: str,
        *,
        profile_id: str | None = None,
        maturity: str | None = None,
    ) -> dict:
        item = self.person(person_id)
        status = item["required_maturity"] if maturity is None else maturity
        profile_id = profile_id or self.next_id("growth_profile")
        roots = self.controller.issue_fresh_profile_roots(
            authority_identity=self.controller.identity,
            authority_secret=self.controller_secret,
            operation_id=self.next_id("roots"),
            person_id=person_id,
            candidate_id=item["candidate_id"],
            profile_id=profile_id,
        )
        maturity_handle = None
        if status != "unresolved":
            source = next(
                entry
                for entry in self.inventory["maturity_sources"]
                if entry["source_id"] == item["maturity_source_id"]
            )
            self.assertIsNotNone(source["path"])
            revision = self.next_id("classification")
            evidence = self.controller.issue_evidence_receipt(
                authority_identity=self.controller.identity,
                authority_secret=self.controller_secret,
                operation_id=self.next_id("evidence"),
                person_id=person_id,
                candidate_id=item["candidate_id"],
                profile_id=profile_id,
                purpose="maturity_classification_source",
                source_kind="classification_receipt",
                source_content=(ROOT / source["path"]).read_bytes(),
                source_revision=self.next_id("source_revision"),
                event_binding_id=revision,
            )
            maturity_handle = self.controller.issue_maturity_classification(
                authority_identity=self.controller.identity,
                authority_secret=self.controller_secret,
                operation_id=self.next_id("maturity"),
                person_id=person_id,
                candidate_id=item["candidate_id"],
                profile_id=profile_id,
                status=status,
                source_evidence=evidence,
                classification_revision=revision,
            )
        return build_fresh_capability_profile(
            person_id=person_id,
            candidate_id=item["candidate_id"],
            profile_id=profile_id,
            authority_controller=self.controller,
            authority_identity=self.controller.identity,
            fresh_root_authority=roots,
            maturity_authority=maturity_handle,
        )

    def build_creator_bundle(
        self,
        candidate_id: str = "new_temporary_person_001",
        person_id: str = "person_new_temporary_001",
        profile_id: str = "growth_new_temporary_001",
        maturity: str = "unresolved",
    ) -> dict:
        maturity_handle = None
        if maturity != "unresolved":
            revision = self.next_id("creator_classification")
            evidence = self.controller.issue_evidence_receipt(
                authority_identity=self.controller.identity,
                authority_secret=self.controller_secret,
                operation_id=self.next_id("creator_evidence"),
                person_id=person_id,
                candidate_id=candidate_id,
                profile_id=profile_id,
                purpose="maturity_classification_source",
                source_kind="classification_receipt",
                source_content=b"exact protected owner classification for this new candidate",
                source_revision=self.next_id("creator_source_revision"),
                event_binding_id=revision,
            )
            maturity_handle = self.controller.issue_maturity_classification(
                authority_identity=self.controller.identity,
                authority_secret=self.controller_secret,
                operation_id=self.next_id("creator_maturity"),
                person_id=person_id,
                candidate_id=candidate_id,
                profile_id=profile_id,
                status=maturity,
                source_evidence=evidence,
                classification_revision=revision,
            )
        return build_fresh_creator_bundle(
            candidate_id=candidate_id,
            display_name="New Temporary Person",
            authority_controller=self.controller,
            authority_identity=self.controller.identity,
            authority_secret=self.controller_secret,
            maturity_authority=maturity_handle,
            person_id=person_id,
            profile_id=profile_id,
            fresh_roots_operation_id=self.next_id("creator_roots"),
        )

    def issue_existing(self, route_id: str, profile: dict):
        return self.adapter.issue_existing_person_migration(
            identity=self.adapter.identity,
            secret=self.integration_secret,
            operation_id=self.next_id("integration_issue"),
            route_id=route_id,
            profile=profile,
        )

    def stage(self, receipt):
        return self.adapter.stage_receipt(
            identity=self.adapter.identity,
            secret=self.integration_secret,
            receipt=receipt,
            operation_id=self.next_id("integration_stage"),
        )

    def test_01_v3_and_acceptance_bytes_are_preserved(self) -> None:
        for relative, expected in V3_PROTECTED.items():
            self.assertEqual(expected, sha(ROOT / relative), relative)

    def test_02_complete_current_route_coverage_and_denied_alias(self) -> None:
        coverage = current_route_coverage_inventory()
        self.assertEqual(24, coverage["person_count"])
        self.assertEqual(36, coverage["route_count"])
        self.assertEqual(35, coverage["applicable_route_count"])
        self.assertEqual(1, coverage["denied_alias_route_count"])
        self.assertEqual(23, coverage["temporary_profile_route_count"])
        self.assertEqual(11, coverage["temporary_state_route_count"])
        self.assertEqual([], coverage["omitted_person_ids"])
        self.assertEqual([], coverage["omitted_route_paths"])
        self.assertEqual([], coverage["cross_bound_route_ids"])
        denied = [r for r in self.inventory["routes"] if r["disposition"] != "applicable"]
        self.assertEqual("sarah_bennett_enterainment_pr_agent_expert_20260606_171637", denied[0]["candidate_id"])
        self.assertIsNone(denied[0]["person_id"])

    def test_03_every_person_has_an_exact_non_cross_bound_route(self) -> None:
        people = {p["person_id"]: p for p in self.inventory["people"]}
        covered: set[str] = set()
        for route in self.inventory["routes"]:
            if route["disposition"] != "applicable":
                continue
            person = people[route["person_id"]]
            self.assertEqual(person["candidate_id"], route["candidate_id"])
            covered.add(route["person_id"])
        self.assertEqual(set(people), covered)
        self.assertNotIn("biological_robert", people)
        self.assertEqual(
            "synthetic_robert_distinct_from_biological_robert",
            people["robert_mcmurrer_presence_ai"]["person_class"],
        )

    def test_04_inventory_unknown_field_and_source_hash_drift_fail_closed(self) -> None:
        value = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        value["unknown"] = True
        path = self.temp_root / "unknown.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(GrowthIntegrationError):
            load_integration_inventory(path, verify_current_routes=False)
        value.pop("unknown")
        value["routes"][0]["source_sha256"] = "1" * 64
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(GrowthIntegrationError):
            load_integration_inventory(path, verify_current_routes=False)

    def test_05_denied_sarah_alias_cannot_issue_a_receipt(self) -> None:
        profile = self.build_profile(
            "sarah_bennett_entertainment_pr_agent_expert_20260606_171637"
        )
        with self.assertRaises(GrowthIntegrationAuthorityError):
            self.issue_existing(
                "state:sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
                profile,
            )

    def test_06_existing_kira_projection_is_public_only_default_off(self) -> None:
        profile = self.build_profile("kira", profile_id="growth_kira_integration_001")
        receipt = self.issue_existing("permanent:kira", profile)
        output = self.stage(receipt)
        attachment = json.loads(output.read_text(encoding="utf-8"))
        observed_keys: set[str] = set()

        def collect_keys(node):
            if isinstance(node, dict):
                observed_keys.update(node)
                for child in node.values():
                    collect_keys(child)
            elif isinstance(node, list):
                for child in node:
                    collect_keys(child)

        collect_keys(attachment)
        for forbidden in ("private_state_roots", "growth_profile", "private_records", "authority_secret"):
            self.assertNotIn(forbidden, observed_keys)
        self.assertTrue(attachment["integration_truth"]["default_off"])
        self.assertFalse(attachment["integration_truth"]["person_activated"])
        self.assertEqual([], attachment["public_capability_projection"]["live_enabled_capability_ids"])
        self.assertEqual("DESIGN_ONLY", attachment["public_capability_projection"]["bounded_initiative_stage"])
        self.assertFalse(attachment["public_capability_projection"]["bounded_initiative_live_enabled"])

    def test_07_receipt_is_one_use_and_operation_ids_cannot_replay(self) -> None:
        profile = self.build_profile("beth_smith_ordinary_temp_20260716")
        receipt = self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile)
        self.stage(receipt)
        with self.assertRaises(GrowthReplayError):
            self.stage(receipt)
        replay_operation = "integration_issue:replay"
        self.adapter.issue_existing_person_migration(
            identity=self.adapter.identity,
            secret=self.integration_secret,
            operation_id=replay_operation,
            route_id="profile:beth_smith_ordinary_temp_20260716",
            profile=self.build_profile(
                "beth_smith_ordinary_temp_20260716", profile_id="growth_beth_replay_a"
            ),
        )
        with self.assertRaises(GrowthReplayError):
            self.adapter.issue_existing_person_migration(
                identity=self.adapter.identity,
                secret=self.integration_secret,
                operation_id=replay_operation,
                route_id="profile:beth_smith_ordinary_temp_20260716",
                profile=self.build_profile(
                    "beth_smith_ordinary_temp_20260716", profile_id="growth_beth_replay_b"
                ),
            )

    def test_08_cross_person_route_and_profile_are_rejected(self) -> None:
        profile = self.build_profile("kira")
        with self.assertRaises(GrowthIntegrationAuthorityError):
            self.issue_existing("permanent:lisa", profile)

    def test_09_maturity_mismatch_rejected_and_nonadult_stays_doll_safe(self) -> None:
        unresolved_kira = self.build_profile(
            "kira", profile_id="growth_kira_wrong_maturity", maturity="unresolved"
        )
        with self.assertRaises(GrowthIntegrationAuthorityError):
            self.issue_existing("permanent:kira", unresolved_kira)
        marinette = self.build_profile(
            "ladybug_marinette_expanded_smoke",
            profile_id="growth_marinette_nonadult",
        )
        receipt = self.issue_existing("profile:ladybug_marinette_expanded_smoke", marinette)
        attachment = json.loads(self.stage(receipt).read_text(encoding="utf-8"))
        maturity = attachment["maturity_projection"]
        self.assertEqual("non_adult", maturity["status"])
        self.assertFalse(maturity["full_adult_curriculum_eligible"])
        self.assertEqual("doll_safe_non_anatomical", maturity["default_body_lane"])
        self.assertFalse(maturity["adult_anatomy_added"])
        self.assertFalse(maturity["consent_granted"])

    def test_10_confirmed_adult_is_eligibility_only_not_delivery_or_consent(self) -> None:
        kira = self.build_profile("kira")
        receipt = self.issue_existing("profile:kira", kira)
        attachment = json.loads(self.stage(receipt).read_text(encoding="utf-8"))
        maturity = attachment["maturity_projection"]
        self.assertTrue(maturity["full_adult_curriculum_eligible"])
        self.assertFalse(maturity["full_adult_curriculum_delivered"])
        self.assertFalse(maturity["adult_anatomy_added"])
        self.assertFalse(maturity["consent_granted"])

    def test_11_unknown_attachment_private_field_and_bool_int_fail_closed(self) -> None:
        profile = self.build_profile("beth_smith_ordinary_temp_20260716")
        receipt = self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile)
        stored = self.adapter._SharedGrowthV3IntegrationAdapter__receipts[receipt]
        attachment = copy.deepcopy(stored["attachment"])
        attachment["private_state_roots"] = {"leak": "Data/person_private/leak"}
        with self.assertRaises(GrowthIntegrationError):
            validate_public_attachment(
                attachment,
                inventory=self.inventory,
                inventory_digest=inventory_sha256(),
                authority_controller=self.controller,
            )
        attachment = copy.deepcopy(stored["attachment"])
        attachment["integration_truth"]["default_off"] = 1
        unsigned = copy.deepcopy(attachment)
        unsigned.pop("attachment_sha256")
        attachment["attachment_sha256"] = hashlib.sha256(
            json.dumps(unsigned, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self.assertRaises(GrowthIntegrationError):
            validate_public_attachment(
                attachment,
                inventory=self.inventory,
                inventory_digest=inventory_sha256(),
                authority_controller=self.controller,
            )

    def test_12_creator_unresolved_round_trip_has_same_safe_defaults(self) -> None:
        bundle = self.build_creator_bundle()
        receipt = self.adapter.issue_creator_migration(
            identity=self.adapter.identity,
            secret=self.integration_secret,
            operation_id=self.next_id("creator_integration_issue"),
            creator_bundle=bundle,
        )
        attachment = json.loads(self.stage(receipt).read_text(encoding="utf-8"))
        self.assertTrue(attachment["route_binding"]["creator_new_person_route"])
        self.assertEqual("unresolved", attachment["maturity_projection"]["status"])
        self.assertEqual("no_protected_source", attachment["maturity_projection"]["maturity_source_id"])
        self.assertEqual("doll_safe_non_anatomical", attachment["maturity_projection"]["default_body_lane"])
        self.assertNotIn("growth_profile", attachment)

    def test_13_creator_classified_requires_and_preserves_exact_v3_receipt(self) -> None:
        bundle = self.build_creator_bundle(
            candidate_id="new_confirmed_adult_001",
            person_id="person_new_confirmed_adult_001",
            profile_id="growth_new_confirmed_adult_001",
            maturity="confirmed_adult",
        )
        receipt = self.adapter.issue_creator_migration(
            identity=self.adapter.identity,
            secret=self.integration_secret,
            operation_id=self.next_id("classified_creator_issue"),
            creator_bundle=bundle,
        )
        attachment = json.loads(self.stage(receipt).read_text(encoding="utf-8"))
        self.assertEqual("confirmed_adult", attachment["maturity_projection"]["status"])
        self.assertEqual(
            "creator_protected_v3_receipt",
            attachment["maturity_projection"]["maturity_source_id"],
        )
        self.assertRegex(
            attachment["maturity_projection"]["classification_receipt_sha256"],
            r"^[0-9a-f]{64}$",
        )

    def test_14_creator_existing_and_denied_alias_collisions_are_rejected(self) -> None:
        existing = self.build_creator_bundle(
            candidate_id="kira",
            person_id="person_creator_collision_kira",
            profile_id="growth_creator_collision_kira",
        )
        with self.assertRaises(GrowthIntegrationAuthorityError):
            self.adapter.issue_creator_migration(
                identity=self.adapter.identity,
                secret=self.integration_secret,
                operation_id=self.next_id("creator_collision"),
                creator_bundle=existing,
            )
        alias = self.build_creator_bundle(
            candidate_id="sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
            person_id="person_creator_collision_sarah_alias",
            profile_id="growth_creator_collision_sarah_alias",
        )
        with self.assertRaises(GrowthIntegrationAuthorityError):
            self.adapter.issue_creator_migration(
                identity=self.adapter.identity,
                secret=self.integration_secret,
                operation_id=self.next_id("creator_alias_collision"),
                creator_bundle=alias,
            )

    def test_15_cross_controller_creator_and_cross_adapter_identity_fail(self) -> None:
        bundle = self.build_creator_bundle()
        other_controller = ProtectedGrowthController(
            controller_id="other_growth_controller",
            authority_secret=bytes(range(65, 97)),
            ledger_root=self.temp_root / "other_growth_ledger",
        )
        other_adapter = SharedGrowthV3IntegrationAdapter(
            authority_controller=other_controller,
            authority_identity=other_controller.identity,
            integration_secret=bytes(range(97, 129)),
            ledger_root=self.temp_root / "other_integration_ledger",
            staging_root=self.temp_root / "other_staging",
        )
        with self.assertRaises((GrowthAuthorityError, GrowthCapabilityError)):
            other_adapter.issue_creator_migration(
                identity=other_adapter.identity,
                secret=bytes(range(97, 129)),
                operation_id="other_creator_issue:001",
                creator_bundle=bundle,
            )
        profile = self.build_profile("beth_smith_ordinary_temp_20260716")
        with self.assertRaises(GrowthIntegrationAuthorityError):
            self.adapter.issue_existing_person_migration(
                identity=other_adapter.identity,
                secret=self.integration_secret,
                operation_id="cross_adapter_identity:001",
                route_id="profile:beth_smith_ordinary_temp_20260716",
                profile=profile,
            )

    def test_16_precommit_failure_rolls_back_only_new_output_and_can_retry(self) -> None:
        profile = self.build_profile(
            "beth_smith_ordinary_temp_20260716",
            profile_id="growth_beth_precommit_rollback",
        )
        receipt = self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile)
        ledger = self.adapter._SharedGrowthV3IntegrationAdapter__ledger
        original_append = ledger.append

        def fail_commit(*, operation_id, kind, binding):
            if kind == "migration_commit_and_receipt_consume":
                raise GrowthIntegrationError("injected commit refusal")
            return original_append(operation_id=operation_id, kind=kind, binding=binding)

        ledger.append = fail_commit
        with self.assertRaises(GrowthIntegrationError):
            self.stage(receipt)
        expected = self.temp_root / "staging" / "growth_beth_precommit_rollback.shared_growth_integration_v1.json"
        self.assertFalse(expected.exists())
        ledger.append = original_append
        output = self.stage(receipt)
        self.assertTrue(output.is_file())

    def test_17_explicit_postcommit_rollback_is_exact_and_not_replayable(self) -> None:
        profile = self.build_profile("beth_smith_ordinary_temp_20260716")
        output = self.stage(
            self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile)
        )
        result = self.adapter.rollback_staged_attachment(
            identity=self.adapter.identity,
            secret=self.integration_secret,
            output=output,
            operation_id=self.next_id("postcommit_rollback"),
        )
        self.assertTrue(result["output_absent"])
        self.assertFalse(result["production_pointer_changed"])
        self.assertFalse(output.exists())
        with self.assertRaises(FileNotFoundError):
            self.adapter.rollback_staged_attachment(
                identity=self.adapter.identity,
                secret=self.integration_secret,
                output=output,
                operation_id=self.next_id("postcommit_rollback_replay"),
            )

    def test_18_upgrade_rollback_preserves_prior_staged_revision(self) -> None:
        first = self.build_profile(
            "beth_smith_ordinary_temp_20260716", profile_id="growth_beth_upgrade_v1"
        )
        first_output = self.stage(
            self.issue_existing("profile:beth_smith_ordinary_temp_20260716", first)
        )
        first_bytes = first_output.read_bytes()
        second = self.build_profile(
            "beth_smith_ordinary_temp_20260716", profile_id="growth_beth_upgrade_v2"
        )
        second_output = self.stage(
            self.issue_existing("profile:beth_smith_ordinary_temp_20260716", second)
        )
        self.adapter.rollback_staged_attachment(
            identity=self.adapter.identity,
            secret=self.integration_secret,
            output=second_output,
            operation_id=self.next_id("upgrade_rollback"),
        )
        self.assertTrue(first_output.exists())
        self.assertEqual(first_bytes, first_output.read_bytes())
        self.assertFalse(second_output.exists())

    def test_19_existing_output_is_never_overwritten_or_deleted(self) -> None:
        profile = self.build_profile(
            "beth_smith_ordinary_temp_20260716",
            profile_id="growth_beth_existing_output",
        )
        receipt = self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile)
        output = self.temp_root / "staging" / "growth_beth_existing_output.shared_growth_integration_v1.json"
        original = b"preexisting owner bytes"
        output.write_bytes(original)
        with self.assertRaises(FileExistsError):
            self.stage(receipt)
        self.assertEqual(original, output.read_bytes())

    def test_20_unknown_ledger_file_and_truncated_tail_fail_closed(self) -> None:
        bad_root = self.temp_root / "bad_ledger"
        bad_root.mkdir()
        (bad_root / "notes.txt").write_text("not a ledger record", encoding="utf-8")
        with self.assertRaises(GrowthIntegrationRecoveryRequired):
            SharedGrowthV3IntegrationAdapter(
                authority_controller=self.controller,
                authority_identity=self.controller.identity,
                integration_secret=self.integration_secret,
                ledger_root=bad_root,
                staging_root=self.temp_root / "bad_staging",
            )
        bad_root = self.temp_root / "truncated_ledger"
        bad_root.mkdir()
        (bad_root / "00000001.json").write_bytes(b"{")
        with self.assertRaises(GrowthIntegrationRecoveryRequired):
            SharedGrowthV3IntegrationAdapter(
                authority_controller=self.controller,
                authority_identity=self.controller.identity,
                integration_secret=self.integration_secret,
                ledger_root=bad_root,
                staging_root=self.temp_root / "truncated_staging",
            )

    def test_21_public_ledger_snapshot_has_no_secret_or_private_payload(self) -> None:
        profile = self.build_profile("beth_smith_ordinary_temp_20260716")
        self.stage(self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile))
        snapshot = self.adapter.ledger_public_snapshot()
        self.assertGreaterEqual(snapshot["record_count"], 2)
        self.assertFalse(snapshot["authority_secret_exposed"])
        self.assertFalse(snapshot["private_payload_exposed"])
        self.assertFalse(snapshot["production_pointer_changed"])

    def test_22_exact_shell_and_production_runtime_bytes_remain_unchanged(self) -> None:
        self.assertEqual(
            "72e4fc403e00a2c4e7ac84e7a87a3c925fc9ce475a8afc90e17ac9e0b6b19fb4",
            sha(ROOT / "tools/kira_world_shell_server.py"),
        )
        self.assertEqual(
            "4fa0449b6f91b7df6f207e86d324e893ee244bce9d8d065a3d14bdc8a197f2ae",
            sha(ROOT / "config/model_runtime.json"),
        )
        self.assertFalse(
            any(
                (ROOT / "TemporaryAI" / "candidates").glob(
                    "*/shared_person_growth_v3_integration_candidate_v1.json"
                )
            )
        )

    def test_23_receipt_body_tamper_fails_before_output_creation(self) -> None:
        profile = self.build_profile(
            "beth_smith_ordinary_temp_20260716",
            profile_id="growth_beth_receipt_tamper",
        )
        receipt = self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile)
        stored = self.adapter._SharedGrowthV3IntegrationAdapter__receipts[receipt]
        stored["body"]["route_id"] = "profile:edgar_cayce_edgar_cayce_20260608_200254"
        with self.assertRaises(GrowthIntegrationAuthorityError):
            self.stage(receipt)
        self.assertFalse(
            (
                self.temp_root
                / "staging"
                / "growth_beth_receipt_tamper.shared_growth_integration_v1.json"
            ).exists()
        )

    def test_24_rehashed_capability_invention_is_rejected(self) -> None:
        profile = self.build_profile("beth_smith_ordinary_temp_20260716")
        receipt = self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile)
        attachment = copy.deepcopy(
            self.adapter._SharedGrowthV3IntegrationAdapter__receipts[receipt]["attachment"]
        )
        attachment["public_capability_projection"]["design_only_capability_ids"].append(
            "invented_private_capability"
        )
        attachment["public_capability_projection"]["design_only_capability_ids"].sort()
        unsigned = copy.deepcopy(attachment)
        unsigned.pop("attachment_sha256")
        attachment["attachment_sha256"] = hashlib.sha256(
            json.dumps(
                unsigned,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        with self.assertRaises(GrowthIntegrationError):
            validate_public_attachment(
                attachment,
                inventory=self.inventory,
                inventory_digest=inventory_sha256(),
                authority_controller=self.controller,
            )

    def test_25_ledger_bytes_require_adapter_secret_authentication(self) -> None:
        profile = self.build_profile("beth_smith_ordinary_temp_20260716")
        self.stage(self.issue_existing("profile:beth_smith_ordinary_temp_20260716", profile))
        record_path = self.temp_root / "integration_ledger" / "00000001.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["binding"]["route_id"] = "profile:edgar_cayce_edgar_cayce_20260608_200254"
        record["binding_sha256"] = hashlib.sha256(
            json.dumps(
                record["binding"],
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        unsigned = copy.deepcopy(record)
        unsigned.pop("record_sha256")
        record["record_sha256"] = hashlib.sha256(
            json.dumps(
                unsigned,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        record_path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(GrowthIntegrationRecoveryRequired):
            SharedGrowthV3IntegrationAdapter(
                authority_controller=self.controller,
                authority_identity=self.controller.identity,
                integration_secret=self.integration_secret,
                ledger_root=self.temp_root / "integration_ledger",
                staging_root=self.temp_root / "tampered_ledger_staging",
            )


if __name__ == "__main__":
    unittest.main()
