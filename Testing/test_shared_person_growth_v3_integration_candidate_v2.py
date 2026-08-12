from __future__ import annotations

import copy
import hashlib
import hmac
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from Core import shared_person_growth_v3_integration_candidate_v1 as v1
from Core import shared_person_growth_v3_integration_candidate_v2 as v2
from Testing.test_shared_person_growth_v3_integration_candidate_v1 import (
    SharedGrowthV3IntegrationCandidateTests as V1Fixture,
)


ROOT = Path(__file__).resolve().parents[1]


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def decode(value: bytes) -> dict[str, Any]:
    result = json.loads(value)
    assert type(result) is dict
    assert canonical(result) == value
    return result


def copy_inventory_closure(clone_root: Path) -> dict[str, Any]:
    inventory = json.loads(v1.INVENTORY_PATH.read_text(encoding="utf-8"))
    paths = {
        v1.INVENTORY_PATH.relative_to(ROOT).as_posix(),
        *(
            inventory["growth_v3_binding"][key]
            for key in (
                "policy_path",
                "core_path",
                "creator_path",
                "fresh_audit_checkpoint_path",
            )
        ),
        *(item["path"] for item in inventory["discovery_sources"]),
        *(
            item["path"]
            for item in inventory["maturity_sources"]
            if item["path"] is not None
        ),
        *(item["source_path"] for item in inventory["routes"]),
    }
    for relative in sorted(paths):
        source = ROOT / relative
        target = clone_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return inventory


class StaticExternalGrowthAuthorityV2:
    """Test-only authority; deliberately not retained by the V2 adapter."""

    def __init__(self, fixture: V1Fixture) -> None:
        self.fixture = fixture
        self._signing_key = Ed25519PrivateKey.generate()
        self.public_key_raw = self._signing_key.public_key().public_bytes_raw()
        self.authority_binding = {
            "schema": "kira.shared_person_growth.external_authority_binding.v2",
            "authority_instance_id": "static_external_growth_authority_v2",
            "authority_epoch_sha256": hashlib.sha256(
                b"static-external-growth-authority-v2-epoch"
            ).hexdigest(),
            "authority_verification_key_sha256": sha_bytes(self.public_key_raw),
            "controller_id": fixture.controller.controller_id,
            "controller_identity_sha256": fixture.controller.controller_identity_sha256,
            "protected_external_callback_required": True,
            "callback_retained_by_adapter": False,
            "python_adapter_is_trust_root": False,
            "production_enabled": False,
        }
        self._secret = hashlib.sha256(b"test-only-growth-v2-external-secret").digest()
        self._counter = 0
        self._envelopes: dict[str, dict[str, Any]] = {}
        self._stage_tickets: dict[str, dict[str, Any]] = {}
        self._commit_receipts: dict[str, dict[str, Any]] = {}
        self._consumed_envelopes: set[str] = set()
        self._consumed_stage_tickets: set[str] = set()
        self._consumed_commit_receipts: set[str] = set()
        self._rolled_back_commits: set[str] = set()
        self.call_count = 0
        self.actions: list[str] = []
        self.raise_after_commit_effect_once = False
        self.mutate_after_action: dict[str, Callable[[], None]] = {}

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}:{self._counter:08d}"

    def _response(
        self, core: dict[str, Any], *, request_bytes: bytes
    ) -> bytes:
        result = copy.deepcopy(core)
        result["request_sha256"] = sha_bytes(request_bytes)
        result["response_sha256"] = v2._sha_mapping(result)
        result["authority_signature_hex"] = self._signing_key.sign(
            v2._SIGNED_RESPONSE_DOMAIN + canonical(
                {
                    key: value
                    for key, value in result.items()
                    if key not in {"response_sha256", "authority_signature_hex"}
                }
            )
        ).hex()
        return canonical(result)

    def _ticket(
        self,
        *,
        schema: str,
        kind: str,
        attachment_sha256: str,
        inventory_sha256: str,
        prior_sha256: str | None,
        source_gate_sha256: str,
        output_sha256: str | None,
    ) -> dict[str, Any]:
        core = {
            "schema": schema,
            "ticket_kind": kind,
            "ticket_id": self._next_id(f"external_{kind.lower()}") ,
            "authority_binding_sha256": v2._sha_mapping(self.authority_binding),
            "inventory_sha256": inventory_sha256,
            "attachment_sha256": attachment_sha256,
            "prior_ticket_sha256": prior_sha256,
            "source_gate_snapshot_sha256": source_gate_sha256,
            "output_sha256": output_sha256,
            "single_use": True,
            "static_only": True,
            "production_enabled": False,
        }
        core["opaque_authority_authenticator_sha256"] = hmac.new(
            self._secret, canonical(core), hashlib.sha256
        ).hexdigest()
        result = dict(core)
        result["ticket_sha256"] = v2._sha_mapping(result)
        return result

    def _envelope_attachment(self, request: dict[str, Any]) -> dict[str, Any]:
        legacy = self.fixture.adapter
        if request["payload_kind"] == "EXISTING_PERSON_V3_PROFILE":
            handle = legacy.issue_existing_person_migration(
                identity=legacy.identity,
                secret=self.fixture.integration_secret,
                operation_id=self._next_id("legacy_issue"),
                route_id=request["route_id"],
                profile=request["payload"],
            )
        elif request["payload_kind"] == "TEMPORARY_CREATOR_V3_BUNDLE":
            handle = legacy.issue_creator_migration(
                identity=legacy.identity,
                secret=self.fixture.integration_secret,
                operation_id=self._next_id("legacy_creator_issue"),
                creator_bundle=request["payload"],
            )
        else:
            raise RuntimeError("unsupported payload kind")
        receipts = getattr(
            legacy, "_SharedGrowthV3IntegrationAdapter__receipts"
        )
        return copy.deepcopy(receipts[handle]["attachment"])

    def __call__(self, request_bytes: bytes) -> bytes:
        self.call_count += 1
        request = decode(request_bytes)
        action = request.get("action")
        self.actions.append(str(action))
        if request.get("static_only") is not True or request.get("production_enabled") is not False:
            raise RuntimeError("non-static authority request")
        if action == "ISSUE_STATIC_MIGRATION_ENVELOPE":
            attachment = self._envelope_attachment(request)
            envelope_core = {
                "schema": "kira.shared_person_growth.migration_envelope.v2",
                "envelope_id": self._next_id("external_envelope"),
                "operation_id": request["operation_id"],
                "route_id": request["route_id"],
                "inventory_sha256": request["inventory_sha256"],
                "authority_binding": copy.deepcopy(self.authority_binding),
                "issue_source_gate_snapshot": copy.deepcopy(
                    request["source_gate_snapshot"]
                ),
                "attachment": attachment,
                "attachment_sha256": attachment["attachment_sha256"],
                "single_use": True,
                "static_only": True,
                "production_enabled": False,
            }
            envelope_core["opaque_authority_authenticator_sha256"] = hmac.new(
                self._secret, canonical(envelope_core), hashlib.sha256
            ).hexdigest()
            envelope = dict(envelope_core)
            envelope["envelope_sha256"] = v2._sha_mapping(envelope)
            self._envelopes[envelope["envelope_sha256"]] = copy.deepcopy(envelope)
            response = self._response(
                {
                    "schema": "kira.shared_person_growth.external_issue_response.v2",
                    "authority_binding": copy.deepcopy(self.authority_binding),
                    "envelope": envelope,
                    "static_only": True,
                    "production_enabled": False,
                },
                request_bytes=request_bytes,
            )
        elif action == "AUTHORIZE_STATIC_STAGE":
            envelope = request["envelope"]
            digest = envelope["envelope_sha256"]
            if self._envelopes.get(digest) != envelope or digest in self._consumed_envelopes:
                raise RuntimeError("migration envelope missing, changed, or replayed")
            self._consumed_envelopes.add(digest)
            ticket = self._ticket(
                schema="kira.shared_person_growth.stage_ticket.v2",
                kind="STAGE",
                attachment_sha256=envelope["attachment_sha256"],
                inventory_sha256=envelope["inventory_sha256"],
                prior_sha256=digest,
                source_gate_sha256=request["stage_source_gate_snapshot"][
                    "snapshot_sha256"
                ],
                output_sha256=None,
            )
            self._stage_tickets[ticket["ticket_sha256"]] = copy.deepcopy(ticket)
            response = self._response(
                {
                    "schema": "kira.shared_person_growth.external_stage_response.v2",
                    "authority_binding": copy.deepcopy(self.authority_binding),
                    "stage_ticket": ticket,
                    "static_only": True,
                    "production_enabled": False,
                },
                request_bytes=request_bytes,
            )
        elif action == "COMMIT_STATIC_STAGE":
            ticket = request["stage_ticket"]
            digest = ticket["ticket_sha256"]
            if self._stage_tickets.get(digest) != ticket or digest in self._consumed_stage_tickets:
                raise RuntimeError("stage ticket missing, changed, or replayed")
            self._consumed_stage_tickets.add(digest)
            receipt = self._ticket(
                schema="kira.shared_person_growth.commit_receipt.v2",
                kind="COMMIT",
                attachment_sha256=request["attachment_sha256"],
                inventory_sha256=ticket["inventory_sha256"],
                prior_sha256=digest,
                source_gate_sha256=request["commit_source_gate_snapshot"][
                    "snapshot_sha256"
                ],
                output_sha256=request["output_sha256"],
            )
            self._commit_receipts[receipt["ticket_sha256"]] = copy.deepcopy(receipt)
            if self.raise_after_commit_effect_once:
                self.raise_after_commit_effect_once = False
                raise RuntimeError("test-only lost commit response after durable effect")
            response = self._response(
                {
                    "schema": "kira.shared_person_growth.external_commit_response.v2",
                    "authority_binding": copy.deepcopy(self.authority_binding),
                    "commit_receipt": receipt,
                    "static_only": True,
                    "production_enabled": False,
                },
                request_bytes=request_bytes,
            )
        elif action == "QUERY_STATIC_COMMIT_STATUS":
            stage_ticket_sha256 = request["stage_ticket"]["ticket_sha256"]
            matches = [
                copy.deepcopy(receipt)
                for receipt in self._commit_receipts.values()
                if (
                    receipt["prior_ticket_sha256"] == stage_ticket_sha256
                    and receipt["attachment_sha256"]
                    == request["attachment_sha256"]
                    and receipt["output_sha256"] == request["output_sha256"]
                    and receipt["source_gate_snapshot_sha256"]
                    == request["commit_source_gate_snapshot"]["snapshot_sha256"]
                )
            ]
            if len(matches) > 1:
                raise RuntimeError("ambiguous test authority commit state")
            response = self._response(
                {
                    "schema": (
                        "kira.shared_person_growth."
                        "external_commit_status_response.v2"
                    ),
                    "authority_binding": copy.deepcopy(self.authority_binding),
                    "commit_state": "COMMITTED" if matches else "NOT_COMMITTED",
                    "commit_receipt": matches[0] if matches else None,
                    "static_only": True,
                    "production_enabled": False,
                },
                request_bytes=request_bytes,
            )
        elif action == "FINALIZE_STATIC_READBACK":
            receipt = request["commit_receipt"]
            digest = receipt["ticket_sha256"]
            if self._commit_receipts.get(digest) != receipt or digest in self._consumed_commit_receipts:
                raise RuntimeError("commit receipt missing, changed, or replayed")
            self._consumed_commit_receipts.add(digest)
            final = self._ticket(
                schema="kira.shared_person_growth.final_readback_receipt.v2",
                kind="FINAL_READBACK",
                attachment_sha256=request["attachment_sha256"],
                inventory_sha256=receipt["inventory_sha256"],
                prior_sha256=digest,
                source_gate_sha256=request["readback_source_gate_snapshot"][
                    "snapshot_sha256"
                ],
                output_sha256=request["output_sha256"],
            )
            response = self._response(
                {
                    "schema": "kira.shared_person_growth.external_readback_response.v2",
                    "authority_binding": copy.deepcopy(self.authority_binding),
                    "final_receipt": final,
                    "static_only": True,
                    "production_enabled": False,
                },
                request_bytes=request_bytes,
            )
        elif action == "ROLLBACK_FAILED_STATIC_STAGE":
            receipt = request["commit_receipt"]
            digest = receipt["ticket_sha256"]
            if self._commit_receipts.get(digest) != receipt:
                raise RuntimeError("rollback commit receipt missing or changed")
            self._rolled_back_commits.add(digest)
            response = self._response(
                {
                    "schema": "kira.shared_person_growth.external_rollback_response.v2",
                    "authority_binding": copy.deepcopy(self.authority_binding),
                    "rollback_confirmed": True,
                    "output_absent": request["output_absent"],
                    "production_pointer_changed": False,
                    "static_only": True,
                    "production_enabled": False,
                },
                request_bytes=request_bytes,
            )
        else:
            raise RuntimeError("unknown external authority action")
        hook = self.mutate_after_action.get(action)
        if hook is not None:
            hook()
        return response


class SharedGrowthV3IntegrationV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = V1Fixture(methodName="test_01_v3_and_acceptance_bytes_are_preserved")
        self.fixture.setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temp.name)
        self.authority = StaticExternalGrowthAuthorityV2(self.fixture)
        self.adapter = v2.SharedGrowthV3ExternalAuthorityAdapterV2(
            staging_root=self.temp_root / "staging",
            authority_public_key_raw=self.authority.public_key_raw,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()
        self.fixture.tearDown()

    def test_01_rejected_v1_and_audit_and_accepted_v3_are_preserved(self) -> None:
        expected = {
            "Core/shared_person_growth_v3_integration_candidate_v1.py": (
                66891,
                "91eef4a3c19edfbda59ca8d1c7e46df54d77648a8d0140eadbee5672353db63c",
            ),
            "Testing/test_shared_person_growth_v3_integration_candidate_v1.py": (
                32344,
                "fddf0658abc322d4ff5590441647ccf2ad18efc305f4f8a78fceb27467d5bd8a",
            ),
            "Data/foundation/shared_person_growth_v3_integration_candidate_v1.json": (
                28107,
                "5b4397d33318dac34fa9f876ed42ec9720ebefb1acdddb235842982479885254",
            ),
            "RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_static_preparation/attempt_01/SEALED_MANIFEST.json": (
                3406,
                "1103ed9c29be3c27a6089ea4682dde93c2db248b4bbf2fa7f5637db60f1d337f",
            ),
            "RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_fresh_static_audit/attempt_01/CHECKPOINT.md": (
                4134,
                "c4ee1dcf86e8703ddd16345a4e31abe9672468a3f0a8b8b6ac31bc44163ad24f",
            ),
            "Core/shared_person_growth_capabilities_v3.py": (
                111964,
                "8250c657486981ba5ce41892da373adc7df49c462865dc8be75af80f542eb3a2",
            ),
        }
        for relative, (size, digest) in expected.items():
            path = ROOT / relative
            self.assertEqual(path.stat().st_size, size, relative)
            self.assertEqual(file_sha(path), digest, relative)

    def test_02_public_adapter_retains_no_authority_identity_secret_or_callback(self) -> None:
        state = self.adapter.public_state()
        self.assertFalse(state["authority_callback_retained"])
        self.assertFalse(state["authority_secret_retained"])
        self.assertFalse(state["controller_retained"])
        self.assertFalse(state["controller_identity_retained"])
        self.assertFalse(state["adapter_identity_capability_present"])
        values = [getattr(self.adapter, slot) for slot in self.adapter.__slots__]
        self.assertNotIn(self.authority, values)
        self.assertNotIn(self.fixture.controller, values)
        self.assertNotIn(self.fixture.controller.identity, values)
        self.assertNotIn(self.fixture.integration_secret, values)
        self.assertFalse(hasattr(self.adapter, "identity"))
        self.assertFalse(
            any("secret" in slot or "controller" in slot for slot in self.adapter.__slots__)
        )
        self.assertEqual(
            {
                "_authority_public_key",
                "_authority_verification_key_sha256",
            },
            {slot for slot in self.adapter.__slots__ if "authority" in slot},
        )
        self.assertNotIn(self.authority._signing_key, values)
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_no_callback"
        )
        with self.assertRaisesRegex(v2.GrowthIntegrationV2AuthorityError, "callback"):
            self.adapter.issue_existing_person_migration(
                authority_callback=None,  # type: ignore[arg-type]
                operation_id="v2:no_callback",
                route_id="permanent:kira",
                profile=profile,
            )

    def test_03_production_opener_always_refuses_even_with_callback(self) -> None:
        for kwargs in ({}, {"authority_callback": self.authority}, {"adapter": self.adapter}):
            with self.subTest(kwargs=tuple(kwargs)):
                with self.assertRaisesRegex(
                    v2.GrowthIntegrationV2AuthorityError, "production.*disconnected"
                ):
                    v2.open_production_shared_growth_v3_integration_v2(**kwargs)

    def test_04_existing_kira_issue_stage_and_final_readback(self) -> None:
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_kira_positive"
        )
        envelope = self.adapter.issue_existing_person_migration(
            authority_callback=self.authority,
            operation_id="v2:kira_issue",
            route_id="permanent:kira",
            profile=profile,
        )
        output = self.adapter.stage_receipt(
            authority_callback=self.authority,
            receipt_envelope=envelope,
            operation_id="v2:kira_stage",
        )
        self.assertTrue(output.is_file())
        attachment = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual("kira", attachment["profile_binding"]["person_id"])
        self.assertEqual("DEFAULT_OFF_STAGED_NOT_PROMOTED", attachment["status"])
        self.assertFalse(attachment["integration_truth"]["production_pointer_changed"])
        self.assertEqual([], attachment["public_capability_projection"]["live_enabled_capability_ids"])
        self.assertNotIn("private_state_roots", attachment)
        self.assertNotIn("private_memory", attachment)
        self.assertNotIn("private_emotion", attachment)
        self.assertFalse(
            attachment["integration_truth"]["profile_or_creator_bundle_copied"]
        )

    def _clone_adapter(self) -> tuple[Path, v2.SharedGrowthV3ExternalAuthorityAdapterV2]:
        clone_root = self.temp_root / "clone_project"
        copy_inventory_closure(clone_root)
        adapter = v2.SharedGrowthV3ExternalAuthorityAdapterV2(
            staging_root=self.temp_root / "clone_staging",
            authority_public_key_raw=self.authority.public_key_raw,
            inventory_path=clone_root / v1.INVENTORY_PATH.relative_to(ROOT),
            project_root=clone_root,
        )
        return clone_root, adapter

    def test_05_post_construction_source_drift_refuses_before_issue_callback(self) -> None:
        clone_root, adapter = self._clone_adapter()
        source = clone_root / "tools/kira_world_shell_server.py"
        source.write_bytes(source.read_bytes() + b"\n# post construction drift\n")
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_post_construction"
        )
        before_calls = self.authority.call_count
        with self.assertRaises(v1.GrowthIntegrationError):
            adapter.issue_existing_person_migration(
                authority_callback=self.authority,
                operation_id="v2:post_construction",
                route_id="permanent:kira",
                profile=profile,
            )
        self.assertEqual(before_calls, self.authority.call_count)

    def test_06_source_drift_after_issue_refuses_stage(self) -> None:
        clone_root, adapter = self._clone_adapter()
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_after_issue"
        )
        envelope = adapter.issue_existing_person_migration(
            authority_callback=self.authority,
            operation_id="v2:before_drift",
            route_id="permanent:kira",
            profile=profile,
        )
        source = clone_root / "tools/kira_world_shell_server.py"
        source.write_bytes(source.read_bytes() + b"\n# drift before stage\n")
        with self.assertRaises(v1.GrowthIntegrationError):
            adapter.stage_receipt(
                authority_callback=self.authority,
                receipt_envelope=envelope,
                operation_id="v2:stage_after_drift",
            )
        self.assertEqual([], list((self.temp_root / "clone_staging").glob("*.json")))

    def test_07_issue_callback_source_mutation_is_detected(self) -> None:
        clone_root, adapter = self._clone_adapter()
        source = clone_root / "tools/kira_world_shell_server.py"
        self.authority.mutate_after_action["ISSUE_STATIC_MIGRATION_ENVELOPE"] = (
            lambda: source.write_bytes(source.read_bytes() + b"\n# issue callback drift\n")
        )
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_issue_callback_drift"
        )
        with self.assertRaises(v1.GrowthIntegrationError):
            adapter.issue_existing_person_migration(
                authority_callback=self.authority,
                operation_id="v2:issue_callback_drift",
                route_id="permanent:kira",
                profile=profile,
            )

    def test_08_stage_callback_source_mutation_is_detected_before_write(self) -> None:
        clone_root, adapter = self._clone_adapter()
        source = clone_root / "tools/kira_world_shell_server.py"
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_stage_callback_drift"
        )
        envelope = adapter.issue_existing_person_migration(
            authority_callback=self.authority,
            operation_id="v2:stage_drift_issue",
            route_id="permanent:kira",
            profile=profile,
        )
        self.authority.mutate_after_action["AUTHORIZE_STATIC_STAGE"] = (
            lambda: source.write_bytes(source.read_bytes() + b"\n# stage callback drift\n")
        )
        with self.assertRaises(v1.GrowthIntegrationError):
            adapter.stage_receipt(
                authority_callback=self.authority,
                receipt_envelope=envelope,
                operation_id="v2:stage_callback_drift",
            )
        self.assertEqual([], list((self.temp_root / "clone_staging").glob("*.json")))

    def test_09_commit_callback_source_mutation_rolls_back_output(self) -> None:
        clone_root, adapter = self._clone_adapter()
        source = clone_root / "tools/kira_world_shell_server.py"
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_commit_callback_drift"
        )
        envelope = adapter.issue_existing_person_migration(
            authority_callback=self.authority,
            operation_id="v2:commit_drift_issue",
            route_id="permanent:kira",
            profile=profile,
        )
        self.authority.mutate_after_action["COMMIT_STATIC_STAGE"] = (
            lambda: source.write_bytes(source.read_bytes() + b"\n# commit callback drift\n")
        )
        with self.assertRaises(v1.GrowthIntegrationError):
            adapter.stage_receipt(
                authority_callback=self.authority,
                receipt_envelope=envelope,
                operation_id="v2:commit_callback_drift",
            )
        self.assertEqual([], list((self.temp_root / "clone_staging").glob("*.json")))
        self.assertEqual(1, len(self.authority._rolled_back_commits))

    def test_10_readback_callback_source_mutation_rolls_back_output(self) -> None:
        clone_root, adapter = self._clone_adapter()
        source = clone_root / "tools/kira_world_shell_server.py"
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_readback_callback_drift"
        )
        envelope = adapter.issue_existing_person_migration(
            authority_callback=self.authority,
            operation_id="v2:readback_drift_issue",
            route_id="permanent:kira",
            profile=profile,
        )
        self.authority.mutate_after_action["FINALIZE_STATIC_READBACK"] = (
            lambda: source.write_bytes(source.read_bytes() + b"\n# readback callback drift\n")
        )
        with self.assertRaises(v1.GrowthIntegrationError):
            adapter.stage_receipt(
                authority_callback=self.authority,
                receipt_envelope=envelope,
                operation_id="v2:readback_callback_drift",
            )
        self.assertEqual([], list((self.temp_root / "clone_staging").glob("*.json")))
        self.assertEqual(1, len(self.authority._rolled_back_commits))

    def test_11_external_envelope_is_one_use_across_stage_attempts(self) -> None:
        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_replay"
        )
        envelope = self.adapter.issue_existing_person_migration(
            authority_callback=self.authority,
            operation_id="v2:replay_issue",
            route_id="permanent:kira",
            profile=profile,
        )
        output = self.adapter.stage_receipt(
            authority_callback=self.authority,
            receipt_envelope=envelope,
            operation_id="v2:replay_first",
        )
        self.assertTrue(output.is_file())
        with self.assertRaisesRegex(v2.GrowthIntegrationV2AuthorityError, "callback failed"):
            self.adapter.stage_receipt(
                authority_callback=self.authority,
                receipt_envelope=envelope,
                operation_id="v2:replay_second",
            )

    def test_12_creator_round_trip_remains_public_unresolved_and_default_off(self) -> None:
        bundle = self.fixture.build_creator_bundle(
            candidate_id="new_temporary_person_v2",
            person_id="person_new_temporary_v2",
            profile_id="growth_new_temporary_v2",
        )
        envelope = self.adapter.issue_creator_migration(
            authority_callback=self.authority,
            operation_id="v2:creator_issue",
            creator_bundle=bundle,
        )
        output = self.adapter.stage_receipt(
            authority_callback=self.authority,
            receipt_envelope=envelope,
            operation_id="v2:creator_stage",
        )
        text = output.read_text(encoding="utf-8")
        attachment = json.loads(text)
        self.assertEqual("unresolved", attachment["maturity_projection"]["status"])
        self.assertEqual("doll_safe_non_anatomical", attachment["maturity_projection"]["default_body_lane"])
        self.assertNotIn("private_state_roots", attachment)
        self.assertNotIn("private_memory", attachment)
        self.assertNotIn("private_emotion", attachment)
        self.assertFalse(
            attachment["integration_truth"]["profile_or_creator_bundle_copied"]
        )
        self.assertFalse(attachment["integration_truth"]["person_activated"])

    def test_13_hostile_substitute_callback_cannot_mint_authority(self) -> None:
        rogue_signing_key = Ed25519PrivateKey.generate()

        def rogue_callback(request_bytes: bytes) -> bytes:
            response = decode(self.authority(request_bytes))
            unsigned = {
                key: value
                for key, value in response.items()
                if key not in {"response_sha256", "authority_signature_hex"}
            }
            response["authority_signature_hex"] = rogue_signing_key.sign(
                v2._SIGNED_RESPONSE_DOMAIN + canonical(unsigned)
            ).hex()
            return canonical(response)

        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_rogue_callback"
        )
        with self.assertRaisesRegex(
            v2.GrowthIntegrationV2AuthorityError, "signature failed"
        ):
            self.adapter.issue_existing_person_migration(
                authority_callback=rogue_callback,
                operation_id="v2:rogue_callback",
                route_id="permanent:kira",
                profile=profile,
            )
        self.assertEqual([], list((self.temp_root / "staging").glob("*.json")))

    def test_14_signed_response_replay_fails_fresh_request_challenge(self) -> None:
        captured: list[bytes] = []

        def capture_callback(request_bytes: bytes) -> bytes:
            response = self.authority(request_bytes)
            captured.append(response)
            return response

        profile = self.fixture.build_profile(
            "kira", profile_id="growth_profile:v2_signed_replay"
        )
        self.adapter.issue_existing_person_migration(
            authority_callback=capture_callback,
            operation_id="v2:capture_signed_response",
            route_id="permanent:kira",
            profile=profile,
        )
        self.assertEqual(1, len(captured))

        def replay_callback(_request_bytes: bytes) -> bytes:
            return captured[0]

        with self.assertRaisesRegex(
            v2.GrowthIntegrationV2AuthorityError, "request cross-binding"
        ):
            self.adapter.issue_existing_person_migration(
                authority_callback=replay_callback,
                operation_id="v2:replay_signed_response",
                route_id="permanent:kira",
                profile=profile,
            )

    def test_15_static_summary_is_truthful(self) -> None:
        summary = v2.static_contract_summary()
        self.assertEqual("STATIC_SUCCESSOR_PENDING_DIFFERENT_FRESH_AUDIT", summary["status"])
        self.assertFalse(summary["adapter_retains_authority_or_secret"])
        self.assertTrue(summary["adapter_retains_public_verifier_only"])
        self.assertTrue(summary["ed25519_signed_response_required"])
        self.assertTrue(
            summary["fresh_per_call_challenge_and_request_binding_required"]
        )
        self.assertTrue(summary["route_source_rehashed_at_issue"])
        self.assertTrue(summary["route_source_rehashed_at_stage"])
        self.assertTrue(summary["route_source_rehashed_at_final_commit"])
        self.assertTrue(summary["route_source_rehashed_at_final_readback"])
        self.assertTrue(summary["production_opener_disconnected"])
        self.assertFalse(summary["production_pointer_changed"])
        self.assertFalse(summary["live_enabled"])


if __name__ == "__main__":
    unittest.main()
