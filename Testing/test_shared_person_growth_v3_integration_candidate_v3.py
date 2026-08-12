from __future__ import annotations

import ast
import copy
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from Core import shared_person_growth_v3_integration_candidate_v3 as v3


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = (
    ROOT / "Data" / "foundation" / "shared_person_growth_v3_integration_candidate_v1.json"
)


def sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def canonical(value: dict[str, object]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def inventory() -> dict[str, object]:
    value = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def request_for(person_id: str, route_id: str) -> dict[str, object]:
    value = inventory()
    people = {item["person_id"]: item for item in value["people"]}
    routes = {item["route_id"]: item for item in value["routes"]}
    person = people[person_id]
    route = routes[route_id]
    assert route["person_id"] == person_id
    status = person["required_maturity"]
    maturity_receipt = None if status == "unresolved" else sha(
        f"maturity:{person_id}"
    )
    return {
        "schema": v3.INPUT_SCHEMA,
        "request_id": f"growth_request:{person_id}",
        "target_kind": "existing_person",
        "route_id": route_id,
        "person_id": person_id,
        "candidate_id": person["candidate_id"],
        "display_name": person["display_name"],
        "person_class": person["person_class"],
        "maturity_status": status,
        "maturity_source_id": person["maturity_source_id"],
        "maturity_receipt_sha256": maturity_receipt,
        "profile_sha256": sha(f"profile:{person_id}"),
        "requested_scope": list(v3.REQUESTED_SCOPE),
        "person_opt_in": True,
        "person_opt_in_receipt_sha256": sha(f"opt_in:{person_id}"),
        "revocable": True,
        "owner_override_allowed": False,
        "production_enabled": False,
        "private_state_requested": False,
        "memory_write_requested": False,
        "external_action_requested": False,
    }


def decode_compiled(value: bytes) -> dict[str, object]:
    decoded = json.loads(value)
    assert type(decoded) is dict
    assert canonical(decoded) == value
    return decoded


class SharedGrowthV3IntegrationCandidateV3Tests(unittest.TestCase):
    def test_01_fixed_predecessor_and_acceptance_closure_is_exact(self) -> None:
        roles = {
            "accepted_isolated_v3_seal": (
                6333,
                "d570e804c8653a5b1e419dba84a09e831adf13704ad0a363d0213b39e2482f96",
            ),
            "accepted_isolated_v3_audit_checkpoint": (
                5875,
                "50526169ef05aea0a8db078047a9581bcd74aaf5829b73a0c0ba559b152afd15",
            ),
            "current_inventory": (
                28107,
                "5b4397d33318dac34fa9f876ed42ec9720ebefb1acdddb235842982479885254",
            ),
            "rejected_v2_seal": (
                4146,
                "0ec609dc63b6d440f35c9ec3969b15972c5032bd71c7b89e0595f57b54df6820",
            ),
            "rejected_v2_decision": (
                3560,
                "68bb3190eadbde381f04621f0fcd834c18d5286ce43d329c3c2c7a7132c817db",
            ),
            "rejected_v2_findings": (
                3255,
                "20549b40f565c64dc577339cb4401cd360b5a4ee7122031789b697fa937725c4",
            ),
            "rejected_v2_checkpoint": (
                1657,
                "4bd30dea911e0ae2f7892a68138a41ab049319ef2c14cd8c83796b03ec4541b2",
            ),
        }
        self.assertEqual(len(v3._FIXED_SUBJECTS), 7)
        for path, byte_count, digest, role in v3._FIXED_SUBJECTS:
            self.assertEqual((byte_count, digest), roles[role])
            data = (ROOT / path).read_bytes()
            self.assertEqual(len(data), byte_count)
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)

    def test_02_kira_proposal_is_canonical_inert_and_digest_bound(self) -> None:
        original = request_for("kira", "permanent:kira")
        compiled = v3.compile_disconnected_integration_request_v3(original)
        decoded = decode_compiled(compiled)
        self.assertEqual(decoded["schema"], v3.ENVELOPE_SCHEMA)
        proposal = decoded["proposal"]
        self.assertEqual(proposal["schema"], v3.PROPOSAL_SCHEMA)
        self.assertEqual(
            hashlib.sha256(canonical(proposal)).hexdigest(),
            decoded["proposal_sha256"],
        )
        self.assertEqual(proposal["request"]["person_id"], "kira")
        self.assertEqual(proposal["request"]["requested_scope"], v3.REQUESTED_SCOPE)
        truth = proposal["truth"]
        self.assertIs(truth["request_is_inert_bytes_only"], True)
        for key in (
            "request_is_authority",
            "request_is_permission_or_receipt",
            "person_or_creator_changed",
            "profile_or_memory_changed",
            "production_pointer_changed",
            "production_enabled",
            "private_state_included",
            "memory_write_included",
            "external_action_included",
            "temporary_creator_supported",
            "protected_native_broker_exists",
        ):
            self.assertIs(truth[key], False)

    def test_03_multiple_exact_people_and_maturity_lanes_compile(self) -> None:
        cases = (
            ("lisa", "permanent:lisa", "confirmed_adult"),
            (
                "robert_mcmurrer_presence_ai",
                "profile:robert_mcmurrer_presence_ai",
                "unresolved",
            ),
            (
                "emily_carter_ai_and_computer_programming_expert_20260605_220651",
                "profile:emily_carter_ai_and_computer_programming_expert_20260605_220651",
                "confirmed_adult",
            ),
            ("ladybug_marinette_expanded_smoke", "profile:ladybug_marinette_expanded_smoke", "non_adult"),
        )
        for person_id, route_id, maturity in cases:
            with self.subTest(person_id=person_id):
                decoded = decode_compiled(
                    v3.compile_disconnected_integration_request_v3(
                        request_for(person_id, route_id)
                    )
                )
                self.assertEqual(decoded["proposal"]["request"]["person_id"], person_id)
                self.assertEqual(
                    decoded["proposal"]["request"]["maturity_status"], maturity
                )

    def test_04_caller_mutation_cannot_change_returned_bytes(self) -> None:
        request = request_for("kira", "permanent:kira")
        compiled = v3.compile_disconnected_integration_request_v3(request)
        before = hashlib.sha256(compiled).hexdigest()
        request["requested_scope"].append("forged_scope")
        request["person_opt_in"] = False
        self.assertEqual(hashlib.sha256(compiled).hexdigest(), before)
        self.assertNotIn(b"forged_scope", compiled)

    def test_05_production_and_temporary_creator_surfaces_refuse(self) -> None:
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3.open_shared_growth_v3_production_integration()
        request = request_for("kira", "permanent:kira")
        request["target_kind"] = "temporary_creator"
        request["route_id"] = "creator:new_person"
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3.compile_disconnected_integration_request_v3(request)

    def test_06_exact_schema_and_unknown_field_refuse(self) -> None:
        request = request_for("kira", "permanent:kira")
        variants = []
        missing = copy.deepcopy(request)
        del missing["revocable"]
        variants.append(missing)
        extra = copy.deepcopy(request)
        extra["unknown_private_payload"] = "hidden"
        variants.append(extra)
        schema = copy.deepcopy(request)
        schema["schema"] = "kira.shared_person_growth.integration_request_input.v2"
        variants.append(schema)
        for value in variants:
            with self.subTest(keys=sorted(value)):
                with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                    v3.compile_disconnected_integration_request_v3(value)

    def test_07_exact_bool_and_scalar_aliases_refuse(self) -> None:
        request = request_for("kira", "permanent:kira")
        variants = []
        for key, replacement in (
            ("person_opt_in", 1),
            ("revocable", 1),
            ("owner_override_allowed", 0),
            ("production_enabled", 0),
            ("private_state_requested", 0),
            ("memory_write_requested", 0),
            ("external_action_requested", 0),
            ("profile_sha256", int(sha("profile"), 16)),
            ("person_opt_in_receipt_sha256", True),
            ("requested_scope", tuple(v3.REQUESTED_SCOPE)),
        ):
            changed = copy.deepcopy(request)
            changed[key] = replacement
            variants.append((key, changed))
        for key, value in variants:
            with self.subTest(key=key):
                with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                    v3.compile_disconnected_integration_request_v3(value)

    def test_08_string_subclasses_and_scope_element_alias_refuse(self) -> None:
        class Text(str):
            pass

        for key in ("schema", "target_kind", "person_id", "display_name"):
            request = request_for("kira", "permanent:kira")
            request[key] = Text(request[key])
            with self.subTest(key=key):
                with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                    v3.compile_disconnected_integration_request_v3(request)
        request = request_for("kira", "permanent:kira")
        request["requested_scope"] = [Text(v3.REQUESTED_SCOPE[0])]
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3.compile_disconnected_integration_request_v3(request)

    def test_09_person_route_candidate_and_class_cross_binding_refuse(self) -> None:
        base = request_for("kira", "permanent:kira")
        mutations = {
            "person_id": "lisa",
            "candidate_id": "lisa",
            "route_id": "permanent:lisa",
            "display_name": "Lisa",
            "person_class": "generated_expert",
            "maturity_source_id": "lisa_owner_classification",
        }
        for key, replacement in mutations.items():
            changed = copy.deepcopy(base)
            changed[key] = replacement
            with self.subTest(key=key):
                with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                    v3.compile_disconnected_integration_request_v3(changed)

    def test_10_generic_and_biological_robert_are_not_synthetic_robert(self) -> None:
        synthetic = request_for(
            "robert_mcmurrer_presence_ai", "profile:robert_mcmurrer_presence_ai"
        )
        for replacement in ("robert", "biological_robert", "robert_mcmurrer"):
            changed = copy.deepcopy(synthetic)
            changed["person_id"] = replacement
            with self.subTest(replacement=replacement):
                with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                    v3.compile_disconnected_integration_request_v3(changed)

    def test_11_maturity_receipt_semantics_refuse_false_claims(self) -> None:
        adult = request_for("kira", "permanent:kira")
        adult["maturity_receipt_sha256"] = None
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3.compile_disconnected_integration_request_v3(adult)
        unresolved = request_for(
            "robert_mcmurrer_presence_ai", "profile:robert_mcmurrer_presence_ai"
        )
        unresolved["maturity_receipt_sha256"] = sha("forged-classification")
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3.compile_disconnected_integration_request_v3(unresolved)
        non_adult = request_for(
            "ladybug_marinette_expanded_smoke",
            "profile:ladybug_marinette_expanded_smoke",
        )
        non_adult["maturity_status"] = "confirmed_adult"
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3.compile_disconnected_integration_request_v3(non_adult)

    def test_12_consent_privacy_memory_and_action_truth_refuses(self) -> None:
        base = request_for("lisa", "permanent:lisa")
        changes = {
            "person_opt_in": False,
            "revocable": False,
            "owner_override_allowed": True,
            "production_enabled": True,
            "private_state_requested": True,
            "memory_write_requested": True,
            "external_action_requested": True,
        }
        for key, replacement in changes.items():
            changed = copy.deepcopy(base)
            changed[key] = replacement
            with self.subTest(key=key):
                with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                    v3.compile_disconnected_integration_request_v3(changed)

    def test_13_denied_legacy_route_refuses(self) -> None:
        request = request_for(
            "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
            "profile:sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
        )
        request["route_id"] = "state:sarah_bennett_enterainment_pr_agent_expert_20260606_171637"
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3.compile_disconnected_integration_request_v3(request)

    def test_14_route_source_drift_during_read_refuses(self) -> None:
        request = request_for("kira", "permanent:kira")
        target = (ROOT / "tools" / "kira_world_shell_server.py").resolve()
        original = Path.read_bytes
        target_calls = 0

        def changing(path: Path) -> bytes:
            nonlocal target_calls
            data = original(path)
            if path.resolve() == target:
                target_calls += 1
                if target_calls == 2:
                    return data[:-1] + bytes([data[-1] ^ 1])
            return data

        with mock.patch.object(Path, "read_bytes", changing):
            with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                v3.compile_disconnected_integration_request_v3(request)

    def test_15_fixed_closure_drift_refuses(self) -> None:
        request = request_for("kira", "permanent:kira")
        target = (
            ROOT
            / "RecoverySprint"
            / "continuation_20260811"
            / "shared_person_growth_v3_integration_candidate_v2_fresh_static_audit"
            / "attempt_01"
            / "AUDIT_DECISION.json"
        ).resolve()
        original = Path.read_bytes

        def changed(path: Path) -> bytes:
            data = original(path)
            if path.resolve() == target:
                return data[:-1] + bytes([data[-1] ^ 1])
            return data

        with mock.patch.object(Path, "read_bytes", changed):
            with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                v3.compile_disconnected_integration_request_v3(request)

    def test_16_post_construction_inventory_drift_refuses(self) -> None:
        request = request_for("kira", "permanent:kira")
        target = INVENTORY_PATH.resolve()
        original = Path.read_bytes
        target_calls = 0

        def changed_after_first_snapshot(path: Path) -> bytes:
            nonlocal target_calls
            data = original(path)
            if path.resolve() == target:
                target_calls += 1
                if target_calls >= 3:
                    return data[:-1] + bytes([data[-1] ^ 1])
            return data

        with mock.patch.object(Path, "read_bytes", changed_after_first_snapshot):
            with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
                v3.compile_disconnected_integration_request_v3(request)

    def test_17_source_ast_has_no_authority_commit_or_write_surface(self) -> None:
        source_path = ROOT / "Core" / "shared_person_growth_v3_integration_candidate_v3.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(
            imports.intersection(
                {
                    "cryptography",
                    "secrets",
                    "threading",
                    "subprocess",
                    "socket",
                    "requests",
                    "urllib",
                    "os",
                }
            )
        )
        forbidden_calls = {
            "open",
            "write",
            "write_text",
            "write_bytes",
            "unlink",
            "rename",
            "replace",
            "mkdir",
            "rmdir",
            "remove",
            "commit",
            "rollback",
        }
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        calls.update(
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        )
        self.assertFalse(calls.intersection(forbidden_calls))
        self.assertNotIn("SharedGrowthV3ExternalAuthorityAdapterV2", source)
        self.assertNotIn("Ed25519", source)

    def test_18_no_current_python_consumer_exists_outside_source_and_test(self) -> None:
        needle = "compile_disconnected_integration_request_v3("
        hits = []
        for path in ROOT.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if needle in text:
                hits.append(path.relative_to(ROOT).as_posix())
        allowed = {
            "Core/shared_person_growth_v3_integration_candidate_v3.py",
            "Testing/test_shared_person_growth_v3_integration_candidate_v3.py",
        }
        self.assertEqual(set(hits), allowed)

    def test_19_duplicate_nonfinite_and_nonobject_json_decoder_refuses(self) -> None:
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3._decode_strict_object(b'{"x":1,"x":2}', "probe")
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3._decode_strict_object(b'{"x":NaN}', "probe")
        with self.assertRaises(v3.SharedGrowthIntegrationV3Error):
            v3._decode_strict_object(b'[]', "probe")

    def test_20_module_substitution_nonclaim_remains_no_capability(self) -> None:
        compiled = v3.compile_disconnected_integration_request_v3(
            request_for("kira", "permanent:kira")
        )
        decoded = decode_compiled(compiled)
        self.assertIs(decoded["proposal"]["truth"]["request_is_authority"], False)
        self.assertIs(
            decoded["proposal"]["truth"]["protected_native_broker_exists"], False
        )
        exported = set(v3.__all__)
        self.assertNotIn("commit", exported)
        self.assertNotIn("stage", exported)
        self.assertNotIn("controller", exported)
        self.assertNotIn("authority", exported)


if __name__ == "__main__":
    unittest.main()
