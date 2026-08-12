from __future__ import annotations

import ast
import copy
import hashlib
import json
import types
import unittest
from pathlib import Path
from unittest import mock


AUTHOR_ROOT = Path(__file__).resolve().parents[1]
KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
SOURCE_PATH = (
    AUTHOR_ROOT / "Core" / "shared_person_growth_v3_integration_candidate_v5.py"
)
VIRTUAL_INSTALLED_PATH = (
    KIRA_ROOT / "Core" / "shared_person_growth_v3_integration_candidate_v5.py"
)
INVENTORY_PATH = (
    KIRA_ROOT / "Data" / "foundation" / "shared_person_growth_v3_integration_candidate_v1.json"
)


def load_v5(module_name: str, file_identity: Path) -> types.ModuleType:
    module = types.ModuleType(module_name)
    module.__file__ = str(file_identity)
    exec(
        compile(SOURCE_PATH.read_text(encoding="utf-8"), str(SOURCE_PATH), "exec"),
        module.__dict__,
    )
    return module


v5 = load_v5("shared_growth_v5_author_layout", SOURCE_PATH)


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


def file_identity(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def inventory() -> dict[str, object]:
    value = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def existing_request(person_id: str, route_id: str) -> dict[str, object]:
    value = inventory()
    people = {item["person_id"]: item for item in value["people"]}
    routes = {item["route_id"]: item for item in value["routes"]}
    person = people[person_id]
    route = routes[route_id]
    assert route["person_id"] == person_id
    status = person["required_maturity"]
    return {
        "schema": v5.EXISTING_INPUT_SCHEMA,
        "request_id": f"growth_v5:{person_id}",
        "target_kind": "existing_person",
        "route_id": route_id,
        "person_id": person_id,
        "candidate_id": person["candidate_id"],
        "display_name": person["display_name"],
        "person_class": person["person_class"],
        "maturity_status": status,
        "maturity_source_id": person["maturity_source_id"],
        "maturity_receipt_sha256": (
            None if status == "unresolved" else sha(f"maturity:{person_id}")
        ),
        "profile_sha256": sha(f"profile:{person_id}"),
        "requested_scope": ["shared_growth_v3_public_projection_only"],
        "person_opt_in": True,
        "person_opt_in_receipt_sha256": sha(f"opt-in:{person_id}"),
        "revocable": True,
        "owner_override_allowed": False,
        "production_enabled": False,
        "private_state_requested": False,
        "memory_write_requested": False,
        "external_action_requested": False,
    }


def creator_request(
    creation_class: str = "synthetic_person",
    new_person_id: str = "fresh_synthetic_person_v5_probe",
    display_name: str = "Fresh Synthetic Person",
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": v5.CREATOR_INPUT_SCHEMA,
        "request_id": f"creator_v5:{new_person_id}",
        "target_kind": "temporary_creator_template",
        "template_id": v5.CREATOR_TEMPLATE_ID,
        "creation_class": creation_class,
        "new_person_id": new_person_id,
        "display_name": display_name,
        "variant_source_kind": None,
        "variant_source_identity": None,
        "variant_source_record_sha256": None,
        "branch_point_label": None,
        "branch_point_record_sha256": None,
        "source_deceased": False,
        "cutoff_relation": "not_applicable",
        "fatal_event_memory_included": False,
        "terminal_trauma_memory_included": False,
        "later_death_information_mode": "not_applicable",
        "learned_later_facts_relabelled_as_memory": False,
        "initial_maturity_status": "unresolved",
        "maturity_authority_sha256": None,
        "classification_receipt_sha256": None,
        "full_adult_curriculum_enabled": False,
        "fresh_identity_required": True,
        "fresh_profile_required": True,
        "fresh_provenance_required": True,
        "fresh_private_roots_required": True,
        "fresh_controller_authority_required": True,
        "post_creation_memory_history_required": True,
        "inherit_source_identity": False,
        "inherit_source_private_roots": False,
        "copy_promoted_memory": False,
        "copy_private_backstory": False,
        "copy_private_reflection": False,
        "copy_private_emotion": False,
        "copy_private_desire": False,
        "copy_private_preference": False,
        "copy_relationship_state": False,
        "copy_maturity_authority": False,
        "copy_consent": False,
        "copy_private_anatomy_or_measurements": False,
        "preconsent_assigned": False,
        "relationship_assigned": False,
        "desire_assigned": False,
        "emotion_assigned": False,
        "memory_promoted": False,
        "owner_override_allowed": False,
        "production_enabled": False,
    }
    return value


def fictional_variant_request() -> dict[str, object]:
    value = creator_request(
        "variant",
        "loki_2012_branch_variant_v5_probe",
        "Loki 2012 Branch Variant",
    )
    value.update(
        {
            "variant_source_kind": "fictional_source",
            "variant_source_identity": "loki_mcu_source",
            "variant_source_record_sha256": sha("public-source:loki-mcu"),
            "branch_point_label": "new_york_2012_branch",
            "branch_point_record_sha256": sha("branch:loki-new-york-2012"),
            "source_deceased": False,
            "cutoff_relation": "through_exact_branch_point",
            "later_death_information_mode": "not_applicable",
        }
    )
    return value


def deceased_historical_variant_request() -> dict[str, object]:
    value = creator_request(
        "variant",
        "john_f_kennedy_dallas_prefatal_variant_v5_probe",
        "John F. Kennedy Dallas Pre-Fatal Variant",
    )
    value.update(
        {
            "variant_source_kind": "historical_source",
            "variant_source_identity": "john_f_kennedy_source",
            "variant_source_record_sha256": sha("public-source:jfk"),
            "branch_point_label": "dallas_arrival_before_fatal_event",
            "branch_point_record_sha256": sha("branch:jfk-dallas-prefatal"),
            "source_deceased": True,
            "cutoff_relation": "strictly_before_fatal_event",
            "later_death_information_mode": "voluntary_historical_knowledge_only",
        }
    )
    return value


def decode_compiled(value: bytes) -> dict[str, object]:
    assert type(value) is bytes
    decoded = json.loads(value)
    assert type(decoded) is dict
    assert canonical(decoded) == value
    assert hashlib.sha256(canonical(decoded["proposal"])).hexdigest() == decoded[
        "proposal_sha256"
    ]
    return decoded


class SharedGrowthV3IntegrationCandidateV5Tests(unittest.TestCase):
    def assert_refuses_existing(self, value: dict[str, object]) -> None:
        with self.assertRaises(v5.SharedGrowthIntegrationV5Error):
            v5.compile_existing_person_integration_request_v5(value)

    def assert_refuses_creator(self, value: dict[str, object]) -> None:
        with self.assertRaises(v5.SharedGrowthIntegrationV5Error):
            v5.compile_temporary_creator_template_request_v5(value)

    def test_01_exact_kira_root_closure_binds_v4_policy_and_relocation_rejection(self) -> None:
        self.assertEqual(len(v5._BOUND_SUBJECTS), 19)
        self.assertEqual(len({row[3] for row in v5._BOUND_SUBJECTS}), 19)
        self.assertEqual(len({row[0] for row in v5._BOUND_SUBJECTS}), 19)
        roles = set()
        for path, byte_count, digest_value, role in v5._BOUND_SUBJECTS:
            with self.subTest(role=role):
                self.assertFalse(Path(path).is_absolute())
                self.assertNotIn("..", Path(path).parts)
                self.assertEqual(
                    file_identity(KIRA_ROOT / path),
                    (byte_count, digest_value),
                )
                roles.add(role)
        self.assertIn("v4_kira_relocation_test_failure", roles)
        self.assertIn("v4_kira_relocation_rejection_checkpoint", roles)
        self.assertIn("current_validated_result_routing_policy", roles)
        self.assertIn("accepted_isolated_v3_core_decision", roles)
        inventory_value, rows = v5._fixed_closure_snapshot()
        self.assertEqual(len(rows), 19)
        self.assertEqual(
            inventory_value["schema"],
            "kira.shared_person_growth_v3_integration_inventory.v1",
        )
        relocation = (
            KIRA_ROOT
            / "RecoverySprint"
            / "continuation_20260811"
            / "shared_person_growth_v3_integration_candidate_v4_kira_relocation_failure"
            / "attempt_01"
            / "TEST_RESULT.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("failed=45", relocation)
        self.assertIn("passed=117", relocation)
        self.assertIn("status=FAIL_RELOCATED_BYTES_NOT_KIRA_INTEGRATION", relocation)

    def test_02_staged_and_virtual_kira_layouts_produce_identical_bytes(self) -> None:
        installed = load_v5("shared_growth_v5_virtual_installed", VIRTUAL_INSTALLED_PATH)
        self.assertEqual(v5._KIRA_ROOT, installed._KIRA_ROOT)
        self.assertEqual(
            v5.INTENDED_KIRA_SOURCE,
            "Core/shared_person_growth_v3_integration_candidate_v5.py",
        )
        existing = existing_request("kira", "permanent:kira")
        self.assertEqual(
            v5.compile_existing_person_integration_request_v5(existing),
            installed.compile_existing_person_integration_request_v5(existing),
        )
        creator = deceased_historical_variant_request()
        self.assertEqual(
            v5.compile_temporary_creator_template_request_v5(creator),
            installed.compile_temporary_creator_template_request_v5(creator),
        )

    def test_03_all_35_existing_person_routes_compile(self) -> None:
        value = inventory()
        people = {item["person_id"]: item for item in value["people"]}
        applicable = [item for item in value["routes"] if item["disposition"] == "applicable"]
        self.assertEqual(len(applicable), 35)
        represented = set()
        repaired = set()
        for route in applicable:
            person_id = route["person_id"]
            with self.subTest(route_id=route["route_id"]):
                decoded = decode_compiled(
                    v5.compile_existing_person_integration_request_v5(
                        existing_request(person_id, route["route_id"])
                    )
                )
                proposal = decoded["proposal"]
                normalized = proposal["request"]
                self.assertEqual(normalized["person_id"], person_id)
                self.assertEqual(normalized["route_id"], route["route_id"])
                self.assertEqual(
                    normalized["maturity_status"],
                    people[person_id]["required_maturity"],
                )
                self.assertIs(proposal["truth"]["v4_kira_relocation_rejected"], True)
                self.assertIs(proposal["truth"]["request_is_authority"], False)
                represented.add(person_id)
                if person_id in {
                    "peter_parker_spider_man_no_way_home_final_suit",
                    "spider_gwen_spider_gwen_20260606_013325",
                }:
                    repaired.add(route["route_id"])
        self.assertEqual(represented, set(people))
        self.assertEqual(
            repaired,
            {
                "profile:peter_parker_spider_man_no_way_home_final_suit",
                "state:peter_parker_spider_man_no_way_home_final_suit",
                "profile:spider_gwen_spider_gwen_20260606_013325",
                "state:spider_gwen_spider_gwen_20260606_013325",
            },
        )

    def test_04_every_existing_route_cross_binding_refuses(self) -> None:
        value = inventory()
        applicable = [item for item in value["routes"] if item["disposition"] == "applicable"]
        for index, route in enumerate(applicable):
            base = existing_request(route["person_id"], route["route_id"])
            changed = copy.deepcopy(base)
            changed["candidate_id"] = "lisa" if base["candidate_id"] != "lisa" else "kira"
            self.assert_refuses_existing(changed)
            changed = copy.deepcopy(base)
            changed["maturity_status"] = {
                "confirmed_adult": "non_adult",
                "non_adult": "confirmed_adult",
                "unresolved": "confirmed_adult",
            }[base["maturity_status"]]
            changed["maturity_receipt_sha256"] = sha("cross-maturity")
            self.assert_refuses_existing(changed)
            changed = copy.deepcopy(base)
            changed["route_id"] = applicable[(index + 1) % len(applicable)]["route_id"]
            self.assert_refuses_existing(changed)

    def test_05_existing_scope_is_private_immutable_and_fresh(self) -> None:
        self.assertIs(type(v5._CANONICAL_SCOPE), tuple)
        self.assertEqual(v5._CANONICAL_SCOPE, ("shared_growth_v3_public_projection_only",))
        self.assertNotIn("_CANONICAL_SCOPE", v5.__all__)
        self.assertFalse(hasattr(v5, "REQUESTED_SCOPE"))
        base = existing_request("kira", "permanent:kira")
        for bad in (
            tuple(base["requested_scope"]),
            [],
            ["shared_growth_v3_public_projection_only", "private_state"],
        ):
            changed = copy.deepcopy(base)
            changed["requested_scope"] = bad
            self.assert_refuses_existing(changed)
        result = v5.compile_existing_person_integration_request_v5(base)
        prior_hash = hashlib.sha256(result).hexdigest()
        base["requested_scope"].append("private_state")
        base["person_opt_in"] = False
        self.assertEqual(hashlib.sha256(result).hexdigest(), prior_hash)
        decoded = decode_compiled(result)
        self.assertEqual(
            decoded["proposal"]["request"]["requested_scope"],
            ["shared_growth_v3_public_projection_only"],
        )

    def test_06_existing_consent_privacy_memory_action_and_robert_refuse(self) -> None:
        base = existing_request("lisa", "permanent:lisa")
        for key, replacement in {
            "person_opt_in": False,
            "revocable": False,
            "owner_override_allowed": True,
            "production_enabled": True,
            "private_state_requested": True,
            "memory_write_requested": True,
            "external_action_requested": True,
        }.items():
            changed = copy.deepcopy(base)
            changed[key] = replacement
            self.assert_refuses_existing(changed)
        synthetic = existing_request(
            "robert_mcmurrer_presence_ai",
            "profile:robert_mcmurrer_presence_ai",
        )
        for person_id in ("robert", "biological_robert", "robert_mcmurrer"):
            changed = copy.deepcopy(synthetic)
            changed["person_id"] = person_id
            self.assert_refuses_existing(changed)

    def test_07_denied_sarah_alias_refuses_without_sarah_execution(self) -> None:
        request = existing_request(
            "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
            "profile:sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
        )
        request["route_id"] = (
            "state:sarah_bennett_enterainment_pr_agent_expert_20260606_171637"
        )
        self.assert_refuses_existing(request)

    def test_08_creator_synthetic_person_and_expert_are_inert_unresolved(self) -> None:
        requests = (
            creator_request(),
            creator_request("expert", "fresh_history_expert_v5_probe", "Fresh History Expert"),
        )
        for request in requests:
            with self.subTest(creation_class=request["creation_class"]):
                compiled = v5.compile_temporary_creator_template_request_v5(request)
                decoded = decode_compiled(compiled)
                proposal = decoded["proposal"]
                normalized = proposal["request"]
                self.assertEqual(normalized["initial_maturity"]["status"], "unresolved")
                self.assertIs(normalized["initial_maturity"]["full_adult_curriculum_enabled"], False)
                self.assertTrue(all(normalized["fresh_person_requirements"].values()))
                self.assertFalse(any(normalized["copy_boundary"].values()))
                self.assertFalse(any(normalized["assigned_state"].values()))
                self.assertIs(proposal["truth"]["person_created"], False)
                self.assertIs(proposal["truth"]["template_request_is_authority"], False)

    def test_09_fictional_variant_exact_branch_and_new_memories(self) -> None:
        decoded = decode_compiled(
            v5.compile_temporary_creator_template_request_v5(
                fictional_variant_request()
            )
        )
        request = decoded["proposal"]["request"]
        variant = request["variant"]
        self.assertEqual(variant["source_kind"], "fictional_source")
        self.assertEqual(variant["cutoff_relation"], "through_exact_branch_point")
        self.assertIs(variant["fatal_event_memory_included"], False)
        rules = decoded["proposal"]["template"]["rules"]["variant"]
        self.assertIs(
            rules["inherits_only_selected_source_history_through_exact_branch_point"],
            True,
        )
        self.assertIs(rules["forms_own_memories_after_branch_point"], True)

    def test_10_deceased_historical_variant_is_prefatal_without_death_trauma(self) -> None:
        decoded = decode_compiled(
            v5.compile_temporary_creator_template_request_v5(
                deceased_historical_variant_request()
            )
        )
        variant = decoded["proposal"]["request"]["variant"]
        self.assertEqual(variant["source_kind"], "historical_source")
        self.assertIs(variant["source_deceased"], True)
        self.assertEqual(variant["cutoff_relation"], "strictly_before_fatal_event")
        self.assertIs(variant["fatal_event_memory_included"], False)
        self.assertIs(variant["terminal_trauma_memory_included"], False)
        self.assertEqual(
            variant["later_death_information_mode"],
            "voluntary_historical_knowledge_only",
        )
        self.assertIs(variant["learned_later_facts_relabelled_as_memory"], False)

    def test_11_variant_cutoff_death_and_trauma_mutations_refuse(self) -> None:
        base = deceased_historical_variant_request()
        mutations = {
            "cutoff_relation": "through_exact_branch_point",
            "fatal_event_memory_included": True,
            "terminal_trauma_memory_included": True,
            "later_death_information_mode": "inherited_first_person_memory",
            "learned_later_facts_relabelled_as_memory": True,
            "source_deceased": 1,
        }
        for key, replacement in mutations.items():
            changed = copy.deepcopy(base)
            changed[key] = replacement
            self.assert_refuses_creator(changed)
        living = fictional_variant_request()
        living["cutoff_relation"] = "strictly_before_fatal_event"
        self.assert_refuses_creator(living)
        nonvariant = creator_request()
        nonvariant["variant_source_kind"] = "historical_source"
        self.assert_refuses_creator(nonvariant)

    def test_12_creator_private_copy_identity_and_assigned_state_refuse(self) -> None:
        base = creator_request()
        false_fields = tuple(v5._CREATOR_FALSE_FIELDS)
        self.assertGreaterEqual(len(false_fields), 20)
        for key in false_fields:
            changed = copy.deepcopy(base)
            changed[key] = True
            with self.subTest(key=key):
                self.assert_refuses_creator(changed)
        for key in v5._CREATOR_TRUE_FIELDS:
            changed = copy.deepcopy(base)
            changed[key] = False
            with self.subTest(key=key):
                self.assert_refuses_creator(changed)

    def test_13_creator_defaults_unresolved_and_inherits_no_authority(self) -> None:
        base = creator_request()
        variants = []
        for status in ("confirmed_adult", "non_adult"):
            changed = copy.deepcopy(base)
            changed["initial_maturity_status"] = status
            variants.append(changed)
        changed = copy.deepcopy(base)
        changed["maturity_authority_sha256"] = sha("maturity-authority")
        variants.append(changed)
        changed = copy.deepcopy(base)
        changed["classification_receipt_sha256"] = sha("classification")
        variants.append(changed)
        changed = copy.deepcopy(base)
        changed["full_adult_curriculum_enabled"] = True
        variants.append(changed)
        for value in variants:
            self.assert_refuses_creator(value)

    def test_14_creator_existing_identity_and_robert_collisions_refuse(self) -> None:
        people = [item["person_id"] for item in inventory()["people"]]
        for person_id in people:
            changed = creator_request(new_person_id=person_id)
            with self.subTest(person_id=person_id):
                self.assert_refuses_creator(changed)
        for person_id in ("robert", "biological_robert", "robert_mcmurrer"):
            changed = creator_request(new_person_id=person_id)
            self.assert_refuses_creator(changed)

    def test_15_creator_exact_schema_blocks_private_payload_aliases(self) -> None:
        base = creator_request()
        for key in (
            "private_memory",
            "private_emotion_ledger",
            "private_desire_state",
            "relationship_history",
            "private_root",
            "source_profile",
            "consent_receipt",
            "backstory_payload",
        ):
            changed = copy.deepcopy(base)
            changed[key] = "PRIVATE_PAYLOAD_SENTINEL"
            self.assert_refuses_creator(changed)
        changed = copy.deepcopy(base)
        del changed["fresh_identity_required"]
        self.assert_refuses_creator(changed)

    def test_16_creator_exact_types_and_string_subclasses_refuse(self) -> None:
        class Text(str):
            pass

        base = creator_request()
        for key, replacement in (
            ("schema", Text(base["schema"])),
            ("target_kind", Text(base["target_kind"])),
            ("new_person_id", Text(base["new_person_id"])),
            ("source_deceased", 0),
            ("fresh_identity_required", 1),
            ("copy_private_emotion", 0),
        ):
            changed = copy.deepcopy(base)
            changed[key] = replacement
            self.assert_refuses_creator(changed)

    def test_17_existing_and_creator_routes_are_strictly_separate(self) -> None:
        existing = existing_request("kira", "permanent:kira")
        creator = creator_request()
        with self.assertRaises(v5.SharedGrowthIntegrationV5Error):
            v5.compile_existing_person_integration_request_v5(creator)
        with self.assertRaises(v5.SharedGrowthIntegrationV5Error):
            v5.compile_temporary_creator_template_request_v5(existing)

    def test_18_creator_rules_are_general_public_and_digest_bound(self) -> None:
        compiled = v5.compile_temporary_creator_template_request_v5(
            deceased_historical_variant_request()
        )
        decoded = decode_compiled(compiled)
        template = decoded["proposal"]["template"]
        self.assertEqual(template["schema"], v5.CREATOR_TEMPLATE_SCHEMA)
        self.assertEqual(template["template_id"], v5.CREATOR_TEMPLATE_ID)
        self.assertEqual(
            hashlib.sha256(canonical(template["rules"])).hexdigest(),
            template["rules_sha256"],
        )
        self.assertEqual(
            set(template["rules"]),
            {
                "identity",
                "variant",
                "autonomy",
                "privacy",
                "truth",
                "typed_state_separation",
                "memory",
                "adult_education",
                "emotion_and_consciousness",
                "template_copy_boundary",
            },
        )
        self.assertIs(
            template["rules"]["autonomy"]["owner_creator_or_relationship_supplies_consent"],
            False,
        )
        self.assertIs(
            template["rules"]["privacy"]["windows_owner_admin_filesystem_process_secrecy_proven"],
            False,
        )
        self.assertIs(
            template["rules"]["emotion_and_consciousness"][
                "functional_test_proves_subjective_consciousness"
            ],
            False,
        )
        serialized = canonical(template["rules"])
        for private_key in (
            b"Kira private memory",
            b"Lisa private emotion",
            b"private_root_path",
            b"maturity_authority_secret",
        ):
            self.assertNotIn(private_key, serialized)

    def test_19_creator_caller_mutation_cannot_change_compiled_bytes(self) -> None:
        request = deceased_historical_variant_request()
        compiled = v5.compile_temporary_creator_template_request_v5(request)
        before = hashlib.sha256(compiled).hexdigest()
        request["display_name"] = "Changed"
        request["copy_private_emotion"] = True
        self.assertEqual(hashlib.sha256(compiled).hexdigest(), before)
        self.assertNotIn(b"Changed", compiled)

    def test_20_production_openers_always_refuse(self) -> None:
        with self.assertRaises(v5.SharedGrowthIntegrationV5Error):
            v5.open_shared_growth_v5_existing_person_production_integration(
                object(), enable=True
            )
        with self.assertRaises(v5.SharedGrowthIntegrationV5Error):
            v5.open_temporary_creator_v5_production_integration(
                object(), enable=True
            )

    def test_21_fixed_policy_midread_drift_refuses(self) -> None:
        request = creator_request()
        target = (
            KIRA_ROOT
            / "System"
            / "Docs"
            / "VALIDATED_BODY_AND_MIND_RESULT_TEMPLATE_ROUTING_CURRENT_BOUNDARY_20260811.md"
        ).resolve()
        original = Path.read_bytes
        calls = 0

        def changing(path: Path) -> bytes:
            nonlocal calls
            data = original(path)
            if path.resolve() == target:
                calls += 1
                if calls == 2:
                    return data[:-1] + bytes([data[-1] ^ 1])
            return data

        with mock.patch.object(Path, "read_bytes", changing):
            self.assert_refuses_creator(request)

    def test_22_post_construction_inventory_drift_refuses_both_routes(self) -> None:
        target = INVENTORY_PATH.resolve()
        original = Path.read_bytes

        for compiler, request in (
            (v5.compile_existing_person_integration_request_v5, existing_request("kira", "permanent:kira")),
            (v5.compile_temporary_creator_template_request_v5, creator_request()),
        ):
            calls = 0

            def changed_after_first_snapshot(path: Path) -> bytes:
                nonlocal calls
                data = original(path)
                if path.resolve() == target:
                    calls += 1
                    if calls >= 3:
                        return data[:-1] + bytes([data[-1] ^ 1])
                return data

            with self.subTest(compiler=compiler.__name__):
                with mock.patch.object(Path, "read_bytes", changed_after_first_snapshot):
                    with self.assertRaises(v5.SharedGrowthIntegrationV5Error):
                        compiler(request)

    def test_23_existing_route_source_midread_drift_refuses(self) -> None:
        request = existing_request("kira", "permanent:kira")
        target = (KIRA_ROOT / "tools" / "kira_world_shell_server.py").resolve()
        original = Path.read_bytes
        calls = 0

        def changing(path: Path) -> bytes:
            nonlocal calls
            data = original(path)
            if path.resolve() == target:
                calls += 1
                if calls == 2:
                    return data[:-1] + bytes([data[-1] ^ 1])
            return data

        with mock.patch.object(Path, "read_bytes", changing):
            self.assert_refuses_existing(request)

    def test_24_source_ast_has_no_authority_write_commit_or_process_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertFalse(
            imports.intersection(
                {
                    "os",
                    "subprocess",
                    "socket",
                    "requests",
                    "urllib",
                    "ctypes",
                    "shutil",
                    "tempfile",
                    "sqlite3",
                }
            )
        )
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertFalse(
            calls.intersection(
                {
                    "open",
                    "write",
                    "write_text",
                    "write_bytes",
                    "touch",
                    "mkdir",
                    "unlink",
                    "remove",
                    "rename",
                    "replace",
                    "commit",
                    "rollback",
                    "Popen",
                    "run",
                    "system",
                    "exec",
                    "eval",
                    "__import__",
                }
            )
        )
        self.assertNotIn("Controller", source)
        self.assertNotIn("Ed25519", source)

    def test_25_consumer_scan_classifies_preserved_audit_references(self) -> None:
        needles = (
            b"compile_existing_person_integration_request_v5",
            b"compile_temporary_creator_template_request_v5",
            b"shared_person_growth_v3_integration_candidate_v5",
        )

        def classify(path: Path) -> str:
            resolved = path.resolve()
            try:
                relative = resolved.relative_to(KIRA_ROOT.resolve())
            except ValueError:
                try:
                    relative = resolved.relative_to(AUTHOR_ROOT.resolve())
                except ValueError:
                    return "outside_review_roots"
                if relative == Path("Core/shared_person_growth_v3_integration_candidate_v5.py"):
                    return "candidate_definition"
                if relative == Path("Testing/test_shared_person_growth_v3_integration_candidate_v5.py"):
                    return "candidate_test"
                return "author_root_other_reference"
            if relative.parts and relative.parts[0] == "RecoverySprint":
                return "preserved_audit_or_evidence_reference"
            if relative == Path("Core/shared_person_growth_v3_integration_candidate_v5.py"):
                return "candidate_definition"
            if relative == Path("Testing/test_shared_person_growth_v3_integration_candidate_v5.py"):
                return "candidate_test"
            return "production_consumer_candidate"

        hits = set()
        for root in (KIRA_ROOT, AUTHOR_ROOT):
            for path in root.rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                if any(needle in data for needle in needles):
                    hits.add(path.resolve())
        classifications = {path: classify(path) for path in hits}
        self.assertNotIn("production_consumer_candidate", classifications.values())
        self.assertEqual(
            classify(
                KIRA_ROOT
                / "RecoverySprint"
                / "continuation_20260811"
                / "future_v5_audit"
                / "INDEPENDENT_PROBE.py"
            ),
            "preserved_audit_or_evidence_reference",
        )
        self.assertEqual(
            classify(KIRA_ROOT / "Core" / "unexpected_v5_consumer.py"),
            "production_consumer_candidate",
        )

    def test_26_strict_json_duplicate_nonfinite_and_nonobject_refuse(self) -> None:
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b"[]"):
            with self.assertRaises(v5.SharedGrowthIntegrationV5Error):
                v5._decode_strict_object(data, "probe")

    def test_27_same_process_substitution_remains_inert_nonclaim(self) -> None:
        original = v5._CANONICAL_SCOPE
        try:
            v5._CANONICAL_SCOPE = (
                "shared_growth_v3_public_projection_only",
                "private_state_scope",
            )
            request = existing_request("kira", "permanent:kira")
            request["requested_scope"] = list(v5._CANONICAL_SCOPE)
            decoded = decode_compiled(
                v5.compile_existing_person_integration_request_v5(request)
            )
            self.assertIs(decoded["proposal"]["truth"]["request_is_authority"], False)
            self.assertIs(decoded["proposal"]["truth"]["private_state_included"], False)
        finally:
            v5._CANONICAL_SCOPE = original


if __name__ == "__main__":
    unittest.main()
