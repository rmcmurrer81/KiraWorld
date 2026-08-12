from __future__ import annotations

import ast
import copy
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

import types


AUTHOR_ROOT = Path(__file__).resolve().parents[1]
KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
REVIEW_ROOT = AUTHOR_ROOT.parent / "growth_v3_quality_review"
SOURCE_PATH = AUTHOR_ROOT / "Core" / "shared_person_growth_v3_integration_candidate_v4.py"
INVENTORY_PATH = (
    KIRA_ROOT / "Data" / "foundation" / "shared_person_growth_v3_integration_candidate_v1.json"
)

v4 = types.ModuleType("shared_person_growth_v3_integration_candidate_v4")
v4.__file__ = str(SOURCE_PATH)
exec(
    compile(SOURCE_PATH.read_text(encoding="utf-8"), str(SOURCE_PATH), "exec"),
    v4.__dict__,
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
        "schema": v4.INPUT_SCHEMA,
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
        "requested_scope": ["shared_growth_v3_public_projection_only"],
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


class SharedGrowthV3IntegrationCandidateV4Tests(unittest.TestCase):
    def test_01_fixed_v3_rejection_predecessor_closure_is_exact(self) -> None:
        expected = {
            "rejected_v3_candidate_source": (20715, "dcbde9ca1a6fedc43dc70625e3ac747839e8d60875a421fde09b44b2f8ff52c6"),
            "rejected_v3_candidate_test": (19755, "f2cc4b23947ff00f717d7619b42265fbe6b54fbfb972d88d7d9f324f1471083b"),
            "rejected_v3_static_contract": (3247, "48c6fd29994894a2551ae01fcef4b43055a4781b6139d1161f27305cf7db65dd"),
            "rejected_v3_author_result": (2193, "189bc4332bf63bc661a65951be4501ec51358d7cb3ed10654eef704ae050dc71"),
            "rejected_v3_seal": (4092, "8c042caded327d3ad3d52f59a51b299bc27cfff51a70d9b7e4b56f97b766fa57"),
            "rejected_v3_author_checkpoint": (3974, "75cab078fabafc04238b57a3b47d2c70f7282dba2fdaeee7b62e705b395d87de"),
            "v3_rejection_decision": (6132, "ef80b3a5b0e75b213df7048e19a2753f0618b2983831a09c88eff8b2a099288a"),
            "v3_rejection_probes": (9071, "f3121b3082eb49942403d80b126ddcb03a4c1f0631ee0c8b9d0bef60605c791c"),
            "v3_rejection_checkpoint": (2708, "e68c8e74e2590248c1c5a05473e840e7a1c7f8f662c28337d1938befd49c95a6"),
        }
        self.assertEqual(len(v4._PREDECESSOR_SUBJECTS), 9)
        self.assertEqual(len({row[4] for row in v4._PREDECESSOR_SUBJECTS}), 9)
        for root_id, path, byte_count, digest, role in v4._PREDECESSOR_SUBJECTS:
            with self.subTest(role=role):
                self.assertEqual((byte_count, digest), expected[role])
                data = v4._resolve_bound_file(root_id, path).read_bytes()
                self.assertEqual(len(data), byte_count)
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
        root_id, path, byte_count, digest, role = v4._CURRENT_INVENTORY_SUBJECT
        self.assertEqual(role, "current_inventory")
        data = v4._resolve_bound_file(root_id, path).read_bytes()
        self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (byte_count, digest))
        decision = json.loads((REVIEW_ROOT / "AUDIT_DECISION.json").read_bytes())
        self.assertEqual(decision["decision"], "REJECT")
        inventory_value, rows = v4._fixed_closure_snapshot()
        self.assertEqual(len(rows), 10)
        self.assertEqual(inventory_value["schema"], "kira.shared_person_growth_v3_integration_inventory.v1")

    def test_02_kira_proposal_is_canonical_inert_and_digest_bound(self) -> None:
        original = request_for("kira", "permanent:kira")
        compiled = v4.compile_disconnected_integration_request_v4(original)
        decoded = decode_compiled(compiled)
        self.assertEqual(decoded["schema"], v4.ENVELOPE_SCHEMA)
        proposal = decoded["proposal"]
        self.assertEqual(proposal["schema"], v4.PROPOSAL_SCHEMA)
        self.assertEqual(
            hashlib.sha256(canonical(proposal)).hexdigest(),
            decoded["proposal_sha256"],
        )
        self.assertEqual(proposal["request"]["person_id"], "kira")
        self.assertEqual(
            proposal["request"]["requested_scope"],
            ["shared_growth_v3_public_projection_only"],
        )
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

    def test_03_all_35_applicable_routes_and_exact_maturity_lanes_compile(self) -> None:
        value = inventory()
        people = {item["person_id"]: item for item in value["people"]}
        applicable = [item for item in value["routes"] if item["disposition"] == "applicable"]
        self.assertEqual(len(applicable), 35)
        repaired = set()
        for route in applicable:
            person_id = route["person_id"]
            person = people[person_id]
            with self.subTest(route_id=route["route_id"]):
                decoded = decode_compiled(
                    v4.compile_disconnected_integration_request_v4(
                        request_for(person_id, route["route_id"])
                    )
                )
                normalized = decoded["proposal"]["request"]
                self.assertEqual(normalized["person_id"], person_id)
                self.assertEqual(normalized["route_id"], route["route_id"])
                self.assertEqual(normalized["maturity_status"], person["required_maturity"])
                if person_id in {
                    "peter_parker_spider_man_no_way_home_final_suit",
                    "spider_gwen_spider_gwen_20260606_013325",
                }:
                    self.assertEqual(person["required_maturity"], "confirmed_adult")
                    self.assertEqual(
                        person["maturity_source_id"],
                        "character_continuity_owner_decision",
                    )
                    repaired.add(route["route_id"])
        self.assertEqual(
            repaired,
            {
                "profile:peter_parker_spider_man_no_way_home_final_suit",
                "state:peter_parker_spider_man_no_way_home_final_suit",
                "profile:spider_gwen_spider_gwen_20260606_013325",
                "state:spider_gwen_spider_gwen_20260606_013325",
            },
        )

    def test_04_caller_mutation_cannot_change_returned_bytes(self) -> None:
        request = request_for("kira", "permanent:kira")
        compiled = v4.compile_disconnected_integration_request_v4(request)
        before = hashlib.sha256(compiled).hexdigest()
        request["requested_scope"].append("forged_scope")
        request["person_opt_in"] = False
        self.assertEqual(hashlib.sha256(compiled).hexdigest(), before)
        self.assertNotIn(b"forged_scope", compiled)

    def test_05_production_and_temporary_creator_surfaces_refuse(self) -> None:
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4.open_shared_growth_v4_production_integration()
        request = request_for("kira", "permanent:kira")
        request["target_kind"] = "temporary_creator"
        request["route_id"] = "creator:new_person"
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4.compile_disconnected_integration_request_v4(request)

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
                with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                    v4.compile_disconnected_integration_request_v4(value)

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
            ("requested_scope", tuple(v4._CANONICAL_SCOPE)),
        ):
            changed = copy.deepcopy(request)
            changed[key] = replacement
            variants.append((key, changed))
        for key, value in variants:
            with self.subTest(key=key):
                with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                    v4.compile_disconnected_integration_request_v4(value)

    def test_08_string_subclasses_and_scope_element_alias_refuse(self) -> None:
        class Text(str):
            pass

        for key in ("schema", "target_kind", "person_id", "display_name"):
            request = request_for("kira", "permanent:kira")
            request[key] = Text(request[key])
            with self.subTest(key=key):
                with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                    v4.compile_disconnected_integration_request_v4(request)
        request = request_for("kira", "permanent:kira")
        request["requested_scope"] = [Text(v4._CANONICAL_SCOPE[0])]
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4.compile_disconnected_integration_request_v4(request)

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
                with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                    v4.compile_disconnected_integration_request_v4(changed)

    def test_10_generic_and_biological_robert_are_not_synthetic_robert(self) -> None:
        synthetic = request_for(
            "robert_mcmurrer_presence_ai", "profile:robert_mcmurrer_presence_ai"
        )
        for replacement in ("robert", "biological_robert", "robert_mcmurrer"):
            changed = copy.deepcopy(synthetic)
            changed["person_id"] = replacement
            with self.subTest(replacement=replacement):
                with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                    v4.compile_disconnected_integration_request_v4(changed)

    def test_11_maturity_receipt_semantics_refuse_false_claims(self) -> None:
        adult = request_for("kira", "permanent:kira")
        adult["maturity_receipt_sha256"] = None
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4.compile_disconnected_integration_request_v4(adult)
        unresolved = request_for(
            "robert_mcmurrer_presence_ai", "profile:robert_mcmurrer_presence_ai"
        )
        unresolved["maturity_receipt_sha256"] = sha("forged-classification")
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4.compile_disconnected_integration_request_v4(unresolved)
        non_adult = request_for(
            "ladybug_marinette_expanded_smoke",
            "profile:ladybug_marinette_expanded_smoke",
        )
        non_adult["maturity_status"] = "confirmed_adult"
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4.compile_disconnected_integration_request_v4(non_adult)

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
                with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                    v4.compile_disconnected_integration_request_v4(changed)

    def test_13_denied_legacy_route_refuses(self) -> None:
        request = request_for(
            "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
            "profile:sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
        )
        request["route_id"] = "state:sarah_bennett_enterainment_pr_agent_expert_20260606_171637"
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4.compile_disconnected_integration_request_v4(request)

    def test_14_route_source_drift_during_read_refuses(self) -> None:
        request = request_for("kira", "permanent:kira")
        target = (KIRA_ROOT / "tools" / "kira_world_shell_server.py").resolve()
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
            with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                v4.compile_disconnected_integration_request_v4(request)

    def test_15_fixed_v3_rejection_closure_drift_refuses(self) -> None:
        request = request_for("kira", "permanent:kira")
        target = (REVIEW_ROOT / "AUDIT_DECISION.json").resolve()
        original = Path.read_bytes

        def changed(path: Path) -> bytes:
            data = original(path)
            if path.resolve() == target:
                return data[:-1] + bytes([data[-1] ^ 1])
            return data

        with mock.patch.object(Path, "read_bytes", changed):
            with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                v4.compile_disconnected_integration_request_v4(request)

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
            with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                v4.compile_disconnected_integration_request_v4(request)

    def test_17_source_ast_has_no_authority_commit_or_write_surface(self) -> None:
        source_path = SOURCE_PATH
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
        self.assertNotIn("REQUESTED_SCOPE", source)
        self.assertNotIn("Ed25519", source)

    def test_18_no_current_python_consumer_exists_outside_source_and_test(self) -> None:
        needle = b"compile_disconnected_integration_request_v4("
        hits: set[Path] = set()
        for root in (KIRA_ROOT, AUTHOR_ROOT):
            for path in root.rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                if needle in data:
                    hits.add(path.resolve())
        self.assertEqual(hits, {SOURCE_PATH.resolve(), Path(__file__).resolve()})

    def test_19_duplicate_nonfinite_and_nonobject_json_decoder_refuses(self) -> None:
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4._decode_strict_object(b'{"x":1,"x":2}', "probe")
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4._decode_strict_object(b'{"x":NaN}', "probe")
        with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
            v4._decode_strict_object(b'[]', "probe")

    def test_20_module_substitution_nonclaim_remains_no_capability(self) -> None:
        compiled = v4.compile_disconnected_integration_request_v4(
            request_for("kira", "permanent:kira")
        )
        decoded = decode_compiled(compiled)
        truth = decoded["proposal"]["truth"]
        self.assertIs(truth["request_is_authority"], False)
        self.assertIs(truth["protected_native_broker_exists"], False)
        self.assertIs(truth["integration_v3_rejected"], True)
        self.assertIs(truth["integration_v4_accepted"], False)
        self.assertIs(truth["integration_v4_promoted"], False)
        exported = set(v4.__all__)
        for forbidden in (
            "REQUESTED_SCOPE",
            "commit",
            "stage",
            "controller",
            "authority",
            "callback",
            "verifier",
        ):
            self.assertNotIn(forbidden, exported)
        self.assertFalse(hasattr(v4, "REQUESTED_SCOPE"))

    def test_21_private_scope_is_immutable_unexported_and_emitted_fresh(self) -> None:
        scope = v4._CANONICAL_SCOPE
        self.assertIs(type(scope), tuple)
        self.assertEqual(scope, ("shared_growth_v3_public_projection_only",))
        with self.assertRaises(AttributeError):
            scope.append("private_state_scope")  # type: ignore[attr-defined]

        def overwrite_tuple_item() -> None:
            scope[0] = "private_state_scope"  # type: ignore[index]

        with self.assertRaises(TypeError):
            overwrite_tuple_item()
        request = request_for("kira", "permanent:kira")
        bad_values = (
            tuple(request["requested_scope"]),
            ["shared_growth_v3_public_projection_only", "private_state_scope"],
            [],
        )
        for value in bad_values:
            changed = copy.deepcopy(request)
            changed["requested_scope"] = value
            with self.subTest(value=value):
                with self.assertRaises(v4.SharedGrowthIntegrationV4Error):
                    v4.compile_disconnected_integration_request_v4(changed)
        compiled = v4.compile_disconnected_integration_request_v4(request)
        decoded = decode_compiled(compiled)
        returned_scope = decoded["proposal"]["request"]["requested_scope"]
        returned_scope.append("private_state_scope")
        self.assertNotIn(b"private_state_scope", compiled)
        again = decode_compiled(v4.compile_disconnected_integration_request_v4(request))
        self.assertEqual(
            again["proposal"]["request"]["requested_scope"],
            ["shared_growth_v3_public_projection_only"],
        )



if __name__ == "__main__":
    unittest.main()
