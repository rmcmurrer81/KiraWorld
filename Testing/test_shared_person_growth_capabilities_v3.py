from __future__ import annotations

import copy
import hashlib
import json
import pickle
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import Core.shared_person_growth_capabilities_v3 as core
import tools.create_temporary_ai_growth_profile_v3 as creator


ROOT = Path(__file__).resolve().parents[1]
SECRET_A = bytes(range(1, 33))
SECRET_B = bytes(range(33, 65))

PROTECTED_PREDECESSORS = {
    "Data/foundation/shared_person_growth_capabilities_v1.json": (
        3030,
        "76cf318bef763acdfd06f417af90449aa72875267f60d1a62217f81ec61f1a4f",
    ),
    "Core/shared_person_growth_capabilities_v1.py": (
        29508,
        "2bda38a21409c46f6a2626925d7917dd1c778c58572cf04633828438777e9806",
    ),
    "tools/create_temporary_ai_growth_profile_v1.py": (
        8950,
        "ef307c784d6a80cd98530bc2d8cadef7bab736b23f268a6408c211e7dd766869",
    ),
    "TemporaryAI/config/shared_person_growth_capability_template_v1.json": (
        1404,
        "9146baabec5e433ae0e89f211c6944b182a6a6e9cf840073cdad548008116686",
    ),
    "Testing/test_shared_person_growth_capabilities_v1.py": (
        13815,
        "4476c5ed263e902cba97ac1e124e3b5972a46d463868db95112ecc7523bf2a11",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_static_implementation/attempt_01/CHECKPOINT.md": (
        3215,
        "35a4c28ec0263df842f1a9f302763cc63d7a29b12018771c4114318226196725",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_fresh_static_audit/attempt_01/INDEPENDENT_HOSTILE_PROBES.py": (
        11362,
        "13461f26a87b596444ec0b5279961bd9d16e4b3b60b996af13b08f94e341d3bd",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_fresh_static_audit/attempt_01/STATIC_AUDIT_RESULT.json": (
        7609,
        "4f0384e0af76710999443be906f81ac0d04898314676eed8aeb01f294b5843f5",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_fresh_static_audit/attempt_01/AUDIT_DECISION.json": (
        1008,
        "b6dd63618483298e144477218649764f996ba89aa2df6b9be94de0be6c75b298",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v1_fresh_static_audit/attempt_01/CHECKPOINT.md": (
        6182,
        "ebadc6bdc21247b2a75eb9798a6dfb4f9988477adddae3827080b42a191f0e04",
    ),
    "Data/foundation/shared_person_growth_capabilities_v2.json": (
        4252,
        "a37c0a238cb49746acfb897144c40b3c031fc6f2201bbd1c6f46b25b49d21a74",
    ),
    "Core/shared_person_growth_capabilities_v2.py": (
        74221,
        "182b3c408b440e66c93bc6c439e8466cb628a77537b0e3db9b28cf86e427efd9",
    ),
    "tools/create_temporary_ai_growth_profile_v2.py": (
        12074,
        "d253141728e6a3ad1f9be346954d3f1e01ac5d067c279cc2cdfbcc8b967ef3cf",
    ),
    "TemporaryAI/config/shared_person_growth_capability_template_v2.json": (
        1738,
        "71d3b74f345895c440c35be82d5afbf19144c8ca56e420aaefdb4d14f839e7d7",
    ),
    "Testing/test_shared_person_growth_capabilities_v2.py": (
        30924,
        "027b838bcbcbcdfe9dbf707e905800ac43ce1cf1eb11d2a623b33237476d0682",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v2_static_repair/attempt_01/SEALED_MANIFEST.json": (
        2596,
        "5b79aff6622efa1d82164e4327bf36b51b02aab3d6667d75c72c968c3489fbd2",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v2_static_repair/attempt_01/AUTHOR_STATIC_TEST_RESULT.json": (
        2392,
        "639ddb98fec9cb6721bcfb325e9234a735bb14b5944d7c4e244ca49e34d7144d",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v2_static_repair/attempt_01/CHECKPOINT.md": (
        9006,
        "7e8b2b39c5cd56231018eae831c23a32b343a6dad4301d54d75224963f98488c",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v2_fresh_static_audit/attempt_01/INDEPENDENT_HOSTILE_PROBES.py": (
        26019,
        "694caa6fe672c1a2facfd278a268f84459ed6b8fe039080a383dab63c4efe061",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v2_fresh_static_audit/attempt_01/HOSTILE_PROBE_RESULT.json": (
        2408,
        "09e3fc9e50b6637ae45b1281bd9ceb1bf430025b51c7931e0e7482b163b739c1",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v2_fresh_static_audit/attempt_01/STATIC_AUDIT_RESULT.json": (
        14354,
        "a7bc34bedf30b609e344e196de7c2b3247088d5fe4c40121aee01fcd7d75bc42",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v2_fresh_static_audit/attempt_01/AUDIT_DECISION.json": (
        2142,
        "db446488b70cdccab26502d32b66dfa47e8f6f3cafe22f3f8b551c1869c389f9",
    ),
    "RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v2_fresh_static_audit/attempt_01/CHECKPOINT.md": (
        8702,
        "c5d14bb2f3415ad8568fc98faf63c30b908d50fab6c63dbc173770c05b1cc785",
    ),
}


def canonical_sha(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def resign_profile(value: dict) -> dict:
    unsigned = copy.deepcopy(value)
    unsigned.pop("profile_fingerprint_sha256", None)
    value["profile_fingerprint_sha256"] = canonical_sha(unsigned)
    return value


def resign_attachment(value: dict) -> dict:
    unsigned = copy.deepcopy(value)
    unsigned.pop("attachment_sha256", None)
    value["attachment_sha256"] = canonical_sha(unsigned)
    return value


def resign_bundle(value: dict) -> dict:
    unsigned = copy.deepcopy(value)
    unsigned.pop("bundle_sha256", None)
    value["bundle_sha256"] = canonical_sha(unsigned)
    return value


class Clock:
    def __init__(self) -> None:
        self.value = 10.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


class SharedPersonGrowthCapabilitiesV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.counter = 0

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def controller(
        self,
        suffix: str,
        *,
        secret: bytes = SECRET_A,
        controller_id: str | None = None,
    ) -> core.ProtectedGrowthController:
        self.counter += 1
        return core.ProtectedGrowthController(
            controller_id=controller_id or f"controller_{suffix}",
            authority_secret=secret,
            ledger_root=self.root / f"ledger_{self.counter}_{suffix}",
        )

    @staticmethod
    def binding(suffix: str) -> dict[str, str]:
        return {
            "person_id": f"person_{suffix}",
            "candidate_id": f"candidate_{suffix}",
            "profile_id": f"profile_{suffix}",
        }

    def profile(
        self,
        controller: core.ProtectedGrowthController,
        suffix: str,
        *,
        secret: bytes = SECRET_A,
        maturity: core.MaturityAuthorityHandle | None = None,
    ) -> dict:
        row = self.binding(suffix)
        roots = controller.issue_fresh_profile_roots(
            authority_identity=controller.identity,
            authority_secret=secret,
            operation_id=f"roots_{suffix}",
            **row,
        )
        return core.build_fresh_capability_profile(
            authority_controller=controller,
            authority_identity=controller.identity,
            fresh_root_authority=roots,
            maturity_authority=maturity,
            **row,
        )

    def classified_profile(
        self,
        controller: core.ProtectedGrowthController,
        suffix: str,
        *,
        status: str,
        secret: bytes = SECRET_A,
    ) -> dict:
        row = self.binding(suffix)
        revision = f"classification_{suffix}"
        source = controller.issue_evidence_receipt(
            authority_identity=controller.identity,
            authority_secret=secret,
            operation_id=f"classification_source_{suffix}",
            purpose="maturity_classification_source",
            source_kind="classification_receipt",
            source_content=f"authenticated classification content {suffix}".encode(),
            source_revision=f"source_revision_{suffix}",
            event_binding_id=revision,
            **row,
        )
        maturity = controller.issue_maturity_classification(
            authority_identity=controller.identity,
            authority_secret=secret,
            operation_id=f"classification_issue_{suffix}",
            status=status,
            source_evidence=source,
            classification_revision=revision,
            **row,
        )
        return self.profile(
            controller,
            suffix,
            secret=secret,
            maturity=maturity,
        )

    def session(
        self,
        controller: core.ProtectedGrowthController,
        profile: dict,
        suffix: str,
        *,
        secret: bytes = SECRET_A,
        max_events: int = 128,
    ) -> core.PersonGrowthSession:
        return controller.open_session(
            authority_identity=controller.identity,
            authority_secret=secret,
            profile=profile,
            activation_revision=f"activation_{suffix}",
            session_open_operation_id=f"session_open_{suffix}",
            clock=Clock(),
            max_events=max_events,
        )

    def evidence(
        self,
        controller: core.ProtectedGrowthController,
        session: core.PersonGrowthSession,
        suffix: str,
        *,
        purpose: str = "present_source",
        source_kind: str = "owner_statement",
        event_binding_id: str | None = None,
        content: bytes | bytearray = b"exact nonempty source content",
        secret: bytes = SECRET_A,
    ) -> core.EvidenceReceiptHandle:
        return controller.issue_evidence_receipt(
            authority_identity=controller.identity,
            authority_secret=secret,
            operation_id=f"evidence_issue_{suffix}",
            **self.binding(suffix.split("__", 1)[0]),
            purpose=purpose,
            source_kind=source_kind,
            source_content=content,  # type: ignore[arg-type]
            source_revision=f"source_revision_{suffix}",
            event_binding_id=event_binding_id or f"present_{suffix}",
            session=session,
            lease=session.lease,
        )

    @staticmethod
    def record_present(
        session: core.PersonGrowthSession,
        receipt: core.EvidenceReceiptHandle,
        event_id: str,
        *,
        source_kind: str = "owner_statement",
    ) -> dict:
        return session.record_present_fact(
            session.lease,
            present_event_id=event_id,
            factual_summary="One exact bounded present fact.",
            source_kind=source_kind,
            source_receipt=receipt,
            observed_at_utc="2026-08-11T00:00:00Z",
            expires_at_utc="2026-08-11T00:10:00Z",
        )

    def test_00_v1_v2_and_both_rejection_audits_are_exactly_preserved(self) -> None:
        for relative, (expected_bytes, expected_sha) in PROTECTED_PREDECESSORS.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, expected_bytes, relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_sha, relative)

    def test_01_policy_is_closed_typed_and_initiative_remains_design_only(self) -> None:
        policy = core.load_policy()
        self.assertEqual(
            policy["capabilities"]["bounded_initiative"],
            {
                "stage": "DESIGN_ONLY",
                "implemented_by_core": False,
                "live_enabled": False,
                "may_execute_external_action": False,
            },
        )
        self.assertFalse(hasattr(core.PersonGrowthSession, "propose_initiative"))
        mutations = []
        changed = copy.deepcopy(policy)
        changed["capabilities"]["present_source_grounding"]["implemented_by_core"] = 1
        mutations.append(changed)
        changed = copy.deepcopy(policy)
        changed["never_inherited_from_another_person"][0] = "different_identity_rule"
        mutations.append(changed)
        changed = copy.deepcopy(policy)
        changed["truth_separation"] = list(reversed(changed["truth_separation"]))
        mutations.append(changed)
        changed = copy.deepcopy(policy)
        changed["unknown_top_level_field"] = True
        mutations.append(changed)
        for index, changed in enumerate(mutations):
            path = self.root / f"closed_policy_{index}.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.subTest(index=index):
                with self.assertRaises(core.GrowthCapabilityError):
                    core.load_policy(path)
        duplicate = self.root / "duplicate_key_policy.json"
        duplicate.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
        with self.assertRaises(core.GrowthCapabilityError):
            core.load_policy(duplicate)

    def test_02_exact_controller_identity_blocks_copy_forgery_and_duplicate_labels(self) -> None:
        first = self.controller(
            "identity_a", secret=SECRET_A, controller_id="controller_duplicate_label"
        )
        second = self.controller(
            "identity_b", secret=SECRET_B, controller_id="controller_duplicate_label"
        )
        first_profile = self.profile(first, "identity_shared")
        second_profile = self.profile(second, "identity_shared", secret=SECRET_B)
        self.assertNotEqual(
            first.controller_identity_sha256, second.controller_identity_sha256
        )
        self.assertNotEqual(
            first_profile["authority_binding"]["controller_identity_sha256"],
            second_profile["authority_binding"]["controller_identity_sha256"],
        )
        with self.assertRaises(core.GrowthAuthorityError):
            core.validate_capability_profile(
                first_profile,
                authority_controller=second,
                authority_identity=second.identity,
            )
        with self.assertRaises(TypeError):
            copy.copy(first)
        with self.assertRaises(TypeError):
            copy.deepcopy(first)
        with self.assertRaises(TypeError):
            pickle.dumps(first)
        with self.assertRaises(TypeError):
            copy.copy(first.identity)
        with self.assertRaises(core.GrowthAuthorityError):
            first.issue_fresh_profile_roots(
                authority_identity=second.identity,
                authority_secret=SECRET_A,
                operation_id="cross_identity_roots",
                **self.binding("cross_identity"),
            )

    def test_03_secret_is_exact_structurally_strong_and_never_serialized(self) -> None:
        invalid = [
            bytearray(SECRET_A),
            SECRET_A[:31],
            SECRET_A + b"x",
            b"\x01" + b"\x00" * 31,
            b"A" * 32,
        ]
        for index, secret in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(core.GrowthAuthorityError):
                    self.controller(f"bad_secret_{index}", secret=secret)  # type: ignore[arg-type]
        controller = self.controller("secret_scan")
        self.profile(controller, "secret_scan")
        for path in (self.root / "ledger_6_secret_scan").glob("*.json"):
            raw = path.read_bytes()
            self.assertNotIn(SECRET_A, raw)
            self.assertNotIn(SECRET_A.hex().encode("ascii"), raw)

    def test_04_evidence_requires_content_session_event_binding_and_single_use_cas(self) -> None:
        controller = self.controller("evidence")
        profile = self.profile(controller, "evidence")
        session = self.session(controller, profile, "evidence")
        for content in (b"", bytearray(b"not exact bytes")):
            with self.assertRaises(core.GrowthCapabilityError):
                self.evidence(
                    controller,
                    session,
                    "evidence__invalid",
                    event_binding_id="present_invalid",
                    content=content,
                )
        content = b"Robert supplied exact source content for this event."
        receipt = self.evidence(
            controller,
            session,
            "evidence",
            event_binding_id="present_evidence",
            content=content,
        )
        before = session.public_snapshot(session.lease)
        with self.assertRaises(core.GrowthAuthorityError):
            self.record_present(session, receipt, "present_wrong_event")
        self.assertEqual(session.public_snapshot(session.lease), before)
        event = self.record_present(session, receipt, "present_evidence")
        self.assertEqual(event["source_content_sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(event["source_content_bytes"], len(content))
        self.assertNotIn(content.decode(), json.dumps(event))
        with self.assertRaises(core.GrowthReplayError):
            self.record_present(session, receipt, "present_evidence_replay")
        other_profile = self.profile(controller, "evidence_other")
        other = self.session(controller, other_profile, "evidence_other")
        with self.assertRaises(core.GrowthAuthorityError):
            controller.issue_evidence_receipt(
                authority_identity=controller.identity,
                authority_secret=SECRET_A,
                operation_id="cross_session_issue",
                **self.binding("evidence"),
                purpose="present_source",
                source_kind="owner_statement",
                source_content=b"cross-session content",
                source_revision="cross_session_revision",
                event_binding_id="present_cross_session",
                session=other,
                lease=other.lease,
            )

    def test_05_maturity_requires_authenticated_classification_content_and_kind(self) -> None:
        controller = self.controller("maturity")
        row = self.binding("maturity")
        with self.assertRaises(core.GrowthAuthorityError):
            controller.issue_evidence_receipt(
                authority_identity=controller.identity,
                authority_secret=SECRET_A,
                operation_id="wrong_kind_maturity_source",
                **row,
                purpose="maturity_classification_source",
                source_kind="owner_statement",
                source_content=b"not a classification receipt",
                source_revision="wrong_kind_revision",
                event_binding_id="classification_maturity",
            )
        source = controller.issue_evidence_receipt(
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            operation_id="valid_maturity_source",
            **row,
            purpose="maturity_classification_source",
            source_kind="classification_receipt",
            source_content=b"authenticated classification receipt bytes",
            source_revision="valid_maturity_source_revision",
            event_binding_id="classification_maturity",
        )
        with self.assertRaises(core.GrowthAuthorityError):
            controller.issue_maturity_classification(
                authority_identity=controller.identity,
                authority_secret=SECRET_A,
                operation_id="maturity_wrong_revision",
                **row,
                status="confirmed_adult",
                source_evidence=source,
                classification_revision="classification_other",
            )
        maturity = controller.issue_maturity_classification(
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            operation_id="maturity_valid_issue",
            **row,
            status="confirmed_adult",
            source_evidence=source,
            classification_revision="classification_maturity",
        )
        adult = self.profile(controller, "maturity", maturity=maturity)
        self.assertTrue(adult["maturity"]["full_adult_curriculum_eligible"])
        self.assertFalse(adult["maturity"]["full_adult_curriculum_delivered"])
        self.assertFalse(adult["maturity"]["adult_anatomy_added"])
        self.assertFalse(adult["maturity"]["consent_granted"])
        child = self.classified_profile(controller, "maturity_nonadult", status="non_adult")
        self.assertFalse(child["maturity"]["full_adult_curriculum_eligible"])

    def test_06_bool_int_substitution_is_rejected_everywhere(self) -> None:
        controller = self.controller("typed")
        original = self.profile(controller, "typed")
        mutations = []
        value = copy.deepcopy(original)
        value["capabilities"]["present_source_grounding"]["implemented_by_core"] = 1
        mutations.append(value)
        value = copy.deepcopy(original)
        value["inheritance"]["copied_private_records"] = False
        mutations.append(value)
        value = copy.deepcopy(original)
        value["maturity"]["consent_granted"] = 0
        mutations.append(value)
        value = copy.deepcopy(original)
        value["runtime"]["activated"] = 0
        mutations.append(value)
        for index, value in enumerate(mutations):
            resign_profile(value)
            with self.subTest(index=index):
                with self.assertRaises(core.GrowthCapabilityError):
                    core.validate_capability_profile(
                        value,
                        authority_controller=controller,
                        authority_identity=controller.identity,
                    )
        bundle = creator.build_fresh_creator_bundle(
            candidate_id="candidate_typed_bundle",
            display_name="Typed Bundle",
            authority_controller=controller,
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            person_id="person_typed_bundle",
            profile_id="profile_typed_bundle",
            fresh_roots_operation_id="roots_typed_bundle",
        )
        bundle["write_contract"]["private_person_data_copied"] = 0
        resign_bundle(bundle)
        with self.assertRaises(core.GrowthCapabilityError):
            creator.validate_creator_bundle(
                bundle,
                authority_controller=controller,
                authority_identity=controller.identity,
            )

    def test_07_creator_rejects_private_root_alias_detached_and_transitive_payload(self) -> None:
        controller = self.controller("creator_alias")
        source = creator.build_fresh_creator_bundle(
            candidate_id="candidate_creator_source",
            display_name="Source",
            authority_controller=controller,
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            person_id="person_creator_source",
            profile_id="profile_creator_source",
            fresh_roots_operation_id="roots_creator_source",
        )
        target = creator.build_fresh_creator_bundle(
            candidate_id="candidate_creator_target",
            display_name="Target",
            authority_controller=controller,
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            person_id="person_creator_target",
            profile_id="profile_creator_target",
            fresh_roots_operation_id="roots_creator_target",
        )
        source_roots = source["attachment"]["growth_profile"]["private_state_roots"]
        target_roots = target["attachment"]["growth_profile"]["private_state_roots"]
        self.assertTrue(set(source_roots.values()).isdisjoint(target_roots.values()))
        forged = copy.deepcopy(target)
        forged["attachment"]["growth_profile"]["private_state_roots"] = copy.deepcopy(
            source_roots
        )
        resign_profile(forged["attachment"]["growth_profile"])
        resign_attachment(forged["attachment"])
        resign_bundle(forged)
        with self.assertRaises(core.GrowthAuthorityError):
            creator.validate_creator_bundle(
                forged,
                authority_controller=controller,
                authority_identity=controller.identity,
            )
        with self.assertRaises(core.GrowthAuthorityError):
            creator.validate_creator_bundle(target)
        transitive = copy.deepcopy(target)
        transitive["attachment"]["creator_truth"]["transitive_private_payload"] = {
            "memory": "must never pass"
        }
        resign_attachment(transitive["attachment"])
        resign_bundle(transitive)
        with self.assertRaises(core.GrowthCapabilityError):
            creator.validate_creator_bundle(
                transitive,
                authority_controller=controller,
                authority_identity=controller.identity,
            )

    def test_08_creator_deletes_exact_new_output_on_any_postcreate_failure(self) -> None:
        controller = self.controller("creator_rollback")
        bundle = creator.build_fresh_creator_bundle(
            candidate_id="candidate_creator_rollback",
            display_name="Rollback",
            authority_controller=controller,
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            person_id="person_creator_rollback",
            profile_id="profile_creator_rollback",
            fresh_roots_operation_id="roots_creator_rollback",
        )
        candidate = self.root / "TemporaryAI/candidates/candidate_creator_rollback"
        candidate.mkdir(parents=True)
        output = candidate / "shared_person_growth_capabilities_v3.json"
        with mock.patch.object(
            creator,
            "validate_creator_bundle",
            side_effect=[bundle, core.GrowthCapabilityError("forced readback failure")],
        ):
            with self.assertRaises(core.GrowthCapabilityError):
                creator.write_bundle_exclusive(
                    bundle,
                    project_root=self.root,
                    authority_controller=controller,
                    authority_identity=controller.identity,
                )
        self.assertFalse(output.exists())
        output.write_text("preserve-existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            creator.write_bundle_exclusive(
                bundle,
                project_root=self.root,
                authority_controller=controller,
                authority_identity=controller.identity,
            )
        self.assertEqual(output.read_text(encoding="utf-8"), "preserve-existing")

    def test_09_event_commit_is_readback_verified_before_receipt_consumption(self) -> None:
        controller = self.controller("commit_order")
        profile = self.profile(controller, "commit_order")
        session = self.session(controller, profile, "commit_order", max_events=1)
        receipt = self.evidence(
            controller,
            session,
            "commit_order",
            event_binding_id="present_commit_order",
        )
        original = controller._consume_session_evidence
        observed: dict[str, int] = {}

        def wrapped(**kwargs):
            readback = controller._session_readback(
                session=session,
                lease=session.lease,
            )
            observed["revision_before_consume"] = readback["revision"]
            return original(**kwargs)

        with mock.patch.object(controller, "_consume_session_evidence", side_effect=wrapped):
            self.record_present(session, receipt, "present_commit_order")
        self.assertEqual(observed["revision_before_consume"], 1)
        second = self.evidence(
            controller,
            session,
            "commit_order__second",
            event_binding_id="present_commit_order_second",
        )
        with self.assertRaises(core.GrowthCapabilityError):
            self.record_present(session, second, "present_commit_order_second")
        still_available = controller._peek_session_evidence(
            session=session,
            lease=session.lease,
            handle=second,
            purpose="present_source",
            source_kind="owner_statement",
            event_binding_id="present_commit_order_second",
        )
        self.assertEqual(still_available["event_binding_id"], "present_commit_order_second")

    def test_10_receipt_consume_failure_creates_debt_and_no_accepted_event(self) -> None:
        controller = self.controller("consume_debt")
        profile = self.profile(controller, "consume_debt")
        session = self.session(controller, profile, "consume_debt")
        receipt = self.evidence(
            controller,
            session,
            "consume_debt",
            event_binding_id="present_consume_debt",
        )
        with mock.patch.object(
            controller,
            "_consume_session_evidence",
            side_effect=core.GrowthRecoveryDebtError("forced consume uncertainty"),
        ):
            with self.assertRaises(core.GrowthRecoveryDebtError):
                self.record_present(session, receipt, "present_consume_debt")
        self.assertEqual(session.private_records(session.lease), [])
        with self.assertRaises(core.GrowthRecoveryDebtError):
            session.public_snapshot(session.lease)
        debt = controller.protected_recovery_debt_snapshot(
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
        )
        self.assertFalse(debt["accepted_state_from_debt"])
        self.assertEqual(len(debt["sessions"]), 1)
        recovery = controller.recover_durable_state(
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            session=session,
            lease=session.lease,
        )
        self.assertEqual(
            recovery["session"]["action"],
            "commit_recovered_after_explicit_readback",
        )
        with self.assertRaises(core.GrowthLeaseError):
            session.private_records(session.lease)

    def test_11_post_replace_readback_uncertainty_has_durable_debt_not_accepted_state(self) -> None:
        path = self.root / "ledger_post_replace.json"
        ledger = core._DurableCASLedger("ledger:post_replace_probe", path)
        real = ledger._read_snapshot_path
        calls = {"count": 0}

        def fail_second(target: Path):
            calls["count"] += 1
            if calls["count"] == 2:
                raise core.GrowthCapabilityError("forced post-replace uncertainty")
            return real(target)

        with mock.patch.object(ledger, "_read_snapshot_path", side_effect=fail_second):
            with self.assertRaises(core.GrowthRecoveryDebtError):
                ledger.append_cas(
                    expected_revision=0,
                    operation_id="post_replace_operation",
                    kind="hostile_probe",
                    binding_sha256=hashlib.sha256(b"binding").hexdigest(),
                )
        self.assertEqual(ledger.revision, 0)
        self.assertTrue(ledger.has_recovery_debt)
        with self.assertRaises(core.GrowthRecoveryDebtError):
            ledger.readback_head()
        recovered = ledger.resolve_recovery_debt()
        self.assertEqual(recovered["action"], "commit_recovered_after_explicit_readback")
        self.assertEqual(ledger.revision, 1)

    def test_12_candidate_readback_failure_has_debt_and_no_commit(self) -> None:
        path = self.root / "ledger_candidate_failure.json"
        ledger = core._DurableCASLedger("ledger:candidate_failure_probe", path)
        with mock.patch.object(
            ledger,
            "_read_snapshot_path",
            side_effect=core.GrowthCapabilityError("forced candidate readback failure"),
        ):
            with self.assertRaises(core.GrowthRecoveryDebtError):
                ledger.append_cas(
                    expected_revision=0,
                    operation_id="candidate_failure_operation",
                    kind="hostile_probe",
                    binding_sha256=hashlib.sha256(b"binding").hexdigest(),
                )
        self.assertEqual(ledger.revision, 0)
        recovered = ledger.resolve_recovery_debt()
        self.assertEqual(recovered["action"], "candidate_not_committed")
        self.assertEqual(ledger.revision, 0)

    def test_13_emotion_replay_is_rejected_and_session_namespace_is_explicit(self) -> None:
        controller = self.controller("emotion")
        profile = self.profile(controller, "emotion")
        session = self.session(controller, profile, "emotion")
        receipt = self.evidence(
            controller, session, "emotion", event_binding_id="present_emotion"
        )
        self.record_present(session, receipt, "present_emotion")
        kwargs = {
            "emotion_event_id": "emotion_unique",
            "cause_present_event_ids": ("present_emotion",),
            "possible_interpretations": ("One bounded interpretation.",),
            "selected_appraisal": "One bounded appraisal.",
            "emotion_label": "curiosity",
            "intensity": 0.3,
            "confidence": 0.6,
            "unresolved": True,
        }
        event = session.record_causal_emotion(session.lease, **kwargs)
        self.assertEqual(event["session_binding_sha256"], session.session_binding_sha256)
        with self.assertRaises(core.GrowthReplayError):
            session.record_causal_emotion(session.lease, **kwargs)
        bad = dict(kwargs)
        bad["emotion_event_id"] = "emotion_bool_substitution"
        bad["unresolved"] = 1
        with self.assertRaises(core.GrowthCapabilityError):
            session.record_causal_emotion(session.lease, **bad)

    def test_14_learning_review_remains_separate_from_memory(self) -> None:
        controller = self.controller("learning")
        profile = self.profile(controller, "learning")
        session = self.session(controller, profile, "learning")
        receipt = self.evidence(
            controller, session, "learning", event_binding_id="present_learning"
        )
        self.record_present(session, receipt, "present_learning")
        proposal = session.propose_learning(
            session.lease,
            proposal_id="proposal_learning",
            proposed_claim="A bounded claim for separate review.",
            source_present_event_ids=("present_learning",),
            privacy_class="person_private",
            contradiction_state="not_checked",
        )
        self.assertEqual(proposal["proposal_state"], "PROPOSED_NOT_MEMORY")
        review_receipt = self.evidence(
            controller,
            session,
            "learning__review",
            purpose="learning_review",
            source_kind="correction_receipt",
            event_binding_id="review_learning",
        )
        review = session.review_learning_proposal(
            session.lease,
            review_event_id="review_learning",
            proposal_id="proposal_learning",
            decision="accept_for_separate_memory_review",
            review_authority_receipt=review_receipt,
            review_source_kind="correction_receipt",
        )
        self.assertFalse(review["memory_written_by_this_review"])
        self.assertTrue(review["separate_memory_writer_still_required"])
        self.assertTrue(all(not row["durable_memory_mutated"] for row in session.private_records(session.lease)))

    def test_15_deactivation_revokes_exact_lease_and_preserves_digest_only_truth(self) -> None:
        controller = self.controller("deactivate")
        profile = self.profile(controller, "deactivate")
        session = self.session(controller, profile, "deactivate")
        result = session.deactivate(
            session.lease,
            close_operation_id="session_close_deactivate",
        )
        self.assertEqual(result["purged_memory_only_event_count"], 0)
        self.assertFalse(result["durable_memory_deleted"])
        self.assertFalse(result["identity_changed"])
        with self.assertRaises(core.GrowthLeaseError):
            session.public_snapshot(session.lease)

    def test_16_creator_classified_and_unresolved_paths_need_exact_controller(self) -> None:
        controller = self.controller("creator_paths")
        unresolved = creator.build_fresh_creator_bundle(
            candidate_id="candidate_creator_unresolved",
            display_name="Unresolved",
            authority_controller=controller,
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            person_id="person_creator_unresolved",
            profile_id="profile_creator_unresolved",
            fresh_roots_operation_id="roots_creator_unresolved",
        )
        self.assertEqual(unresolved["maturity_authority"]["status"], "unresolved")
        self.assertTrue(
            unresolved["maturity_authority"][
                "protected_controller_connected_for_all_validation"
            ]
        )
        with self.assertRaises(core.GrowthAuthorityError):
            creator.validate_creator_bundle(unresolved)

        row = self.binding("creator_adult")
        revision = "classification_creator_adult"
        source = controller.issue_evidence_receipt(
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            operation_id="classification_source_creator_adult",
            **row,
            purpose="maturity_classification_source",
            source_kind="classification_receipt",
            source_content=b"authenticated adult classification content",
            source_revision="source_revision_creator_adult",
            event_binding_id=revision,
        )
        maturity = controller.issue_maturity_classification(
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            operation_id="classification_issue_creator_adult",
            **row,
            status="confirmed_adult",
            source_evidence=source,
            classification_revision=revision,
        )
        adult = creator.build_fresh_creator_bundle(
            candidate_id=row["candidate_id"],
            display_name="Adult",
            authority_controller=controller,
            authority_identity=controller.identity,
            authority_secret=SECRET_A,
            maturity_authority=maturity,
            person_id=row["person_id"],
            profile_id=row["profile_id"],
            fresh_roots_operation_id="roots_creator_adult",
        )
        maturity_truth = adult["attachment"]["growth_profile"]["maturity"]
        self.assertTrue(maturity_truth["full_adult_curriculum_eligible"])
        self.assertFalse(maturity_truth["adult_anatomy_added"])
        self.assertFalse(maturity_truth["consent_granted"])

    def test_17_template_is_static_closed_and_disallows_root_or_payload_copy(self) -> None:
        path = ROOT / "TemporaryAI/config/shared_person_growth_capability_template_v3.json"
        template = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(template["schema"], "kira.temporary_creator_shared_growth_template.v3")
        self.assertFalse(template["promotion_gate"]["current_shared_enablement_allowed"])
        self.assertIn("private_state_roots", template["never_copy"])
        self.assertIn("transitive_private_payload", template["never_copy"])
        self.assertTrue(
            template["creator_write_contract"][
                "exact_created_output_deleted_on_any_postcreate_failure"
            ]
        )


if __name__ == "__main__":
    unittest.main()
