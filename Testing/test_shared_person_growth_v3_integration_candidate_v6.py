from __future__ import annotations

import ast
import copy
import hashlib
import json
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


AUTHOR_ROOT = Path(__file__).resolve().parents[1]
KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
V5_AUDIT_ROOT = (
    Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work")
    / "growth_v5_independent_audit_attempt_01"
)
SOURCE_PATH = AUTHOR_ROOT / "Core" / "shared_person_growth_v3_integration_candidate_v6.py"
TEST_PATH = AUTHOR_ROOT / "Testing" / "test_shared_person_growth_v3_integration_candidate_v6.py"
CATALOG_PATH = (
    AUTHOR_ROOT
    / "Data"
    / "foundation"
    / "temporary_creator_public_variant_provenance_catalog_v1.json"
)
INVENTORY_PATH = (
    KIRA_ROOT / "Data" / "foundation" / "shared_person_growth_v3_integration_candidate_v1.json"
)


def load_v6(module_name: str, file_identity: Path) -> types.ModuleType:
    module = types.ModuleType(module_name)
    module.__file__ = str(file_identity)
    exec(
        compile(SOURCE_PATH.read_text(encoding="utf-8"), str(SOURCE_PATH), "exec"),
        module.__dict__,
    )
    return module


v6 = load_v6("shared_growth_v6_author_layout", SOURCE_PATH)


def digest(label: str) -> str:
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
        "schema": v6.EXISTING_INPUT_SCHEMA,
        "target_kind": "existing_person",
        "route_id": route_id,
        "person_id": person_id,
        "candidate_id": person["candidate_id"],
        "display_name": person["display_name"],
        "person_class": person["person_class"],
        "maturity_status": status,
        "maturity_source_id": person["maturity_source_id"],
        "maturity_receipt_sha256": (
            None if status == "unresolved" else digest(f"maturity:{person_id}")
        ),
        "profile_sha256": digest(f"profile:{person_id}"),
        "requested_scope": ["shared_growth_v3_public_projection_only"],
        "person_opt_in": True,
        "person_opt_in_receipt_sha256": digest(f"opt-in:{person_id}"),
        "revocable": True,
        "owner_override_allowed": False,
        "production_enabled": False,
        "private_state_requested": False,
        "memory_write_requested": False,
        "external_action_requested": False,
    }


def creator_request(
    creation_class: str = "synthetic_person",
    provenance_entry_id: str | None = None,
) -> dict[str, object]:
    return {
        "schema": v6.CREATOR_INPUT_SCHEMA,
        "target_kind": "temporary_creator_template",
        "template_id": v6.CREATOR_TEMPLATE_ID,
        "creation_class": creation_class,
        "provenance_catalog_id": v6.PROVENANCE_CATALOG_ID,
        "provenance_entry_id": provenance_entry_id,
        "initial_maturity_status": "unresolved",
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


def loki_variant_request() -> dict[str, object]:
    return creator_request("variant", "loki_mcu_new_york_2012_branch_v1")


def jfk_variant_request() -> dict[str, object]:
    return creator_request("variant", "john_f_kennedy_dallas_arrival_prefatal_v1")


def decode_compiled(value: bytes) -> dict[str, object]:
    assert type(value) is bytes
    decoded = json.loads(value)
    assert type(decoded) is dict
    assert canonical(decoded) == value
    assert hashlib.sha256(canonical(decoded["proposal"])).hexdigest() == decoded[
        "proposal_sha256"
    ]
    return decoded


def source_record(entry: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "kira.temporary_creator.public_variant_source_record.v1",
        "source_kind": entry["source_kind"],
        "source_identity_id": entry["source_identity_id"],
        "source_continuity_id": entry["source_continuity_id"],
        "source_set_id": entry["source_set_id"],
        "source_version_id": entry["source_version_id"],
        "provenance_confidence_basis_id": entry["provenance_confidence_basis_id"],
    }


def branch_record(entry: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "kira.temporary_creator.public_variant_branch_record.v1",
        "source_record_sha256": entry["source_record_sha256"],
        "source_alive_at_cutoff": entry["source_alive_at_cutoff"],
        "source_future_fatal_event_exists": entry["source_future_fatal_event_exists"],
        "branch_point_id": entry["branch_point_id"],
        "inherited_memory_cutoff_id": entry["inherited_memory_cutoff_id"],
        "activation_point_id": entry["activation_point_id"],
        "branch_event_ordinal": entry["branch_event_ordinal"],
        "fatal_event_ordinal": entry["fatal_event_ordinal"],
        "cutoff_relation": entry["cutoff_relation"],
        "fatal_event_memory_included": entry["fatal_event_memory_included"],
        "terminal_trauma_memory_included": entry["terminal_trauma_memory_included"],
        "later_source_fatal_information_mode": entry[
            "later_source_fatal_information_mode"
        ],
        "later_source_fatal_information_person_choice_required": entry[
            "later_source_fatal_information_person_choice_required"
        ],
        "later_disclosure_becomes_new_post_branch_memory": entry[
            "later_disclosure_becomes_new_post_branch_memory"
        ],
        "later_disclosure_is_inherited_first_person_memory": entry[
            "later_disclosure_is_inherited_first_person_memory"
        ],
        "advance_content_warning_required": entry["advance_content_warning_required"],
        "informed_consent_required": entry["informed_consent_required"],
        "pacing_and_stop_required": entry["pacing_and_stop_required"],
        "support_available_required": entry["support_available_required"],
    }


def rederive_catalog(value: dict[str, object]) -> dict[str, object]:
    for entry in value["entries"]:
        entry["source_record_sha256"] = hashlib.sha256(canonical(source_record(entry))).hexdigest()
        entry["branch_point_record_sha256"] = hashlib.sha256(
            canonical(branch_record(entry))
        ).hexdigest()
    return value


def load_catalog() -> dict[str, object]:
    value = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def source_for_bound_role(relative_path: str, role: str) -> Path:
    if role.startswith("v5_rejection_"):
        return V5_AUDIT_ROOT / Path(relative_path).name
    if role == "sealed_public_variant_provenance_catalog":
        return AUTHOR_ROOT / relative_path
    return KIRA_ROOT / relative_path


class SharedGrowthV3IntegrationCandidateV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(
            prefix="growth_v6_virtual_kira_",
            dir=AUTHOR_ROOT,
        )
        cls.virtual_root = Path(cls._temporary.name) / "Kira"
        cls.virtual_root.mkdir()
        for relative_path, byte_count, sha256, role in v6._BOUND_SUBJECTS:
            source = source_for_bound_role(relative_path, role)
            data = source.read_bytes()
            assert (len(data), hashlib.sha256(data).hexdigest()) == (byte_count, sha256)
            target = cls.virtual_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        current = inventory()
        for route in current["routes"]:
            if route["disposition"] != "applicable":
                continue
            relative_path = route["source_path"]
            target = cls.virtual_root / relative_path
            if target.exists():
                continue
            source = KIRA_ROOT / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        v6._KIRA_ROOT = cls.virtual_root

    @classmethod
    def tearDownClass(cls) -> None:
        v6._KIRA_ROOT = KIRA_ROOT
        cls._temporary.cleanup()

    def assert_refuses_existing(self, value: dict[str, object]) -> None:
        with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
            v6.compile_existing_person_integration_request_v6(value)

    def assert_refuses_creator(self, value: dict[str, object]) -> None:
        with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
            v6.compile_temporary_creator_template_request_v6(value)

    def test_01_exact_virtual_final_kira_closure_binds_v5_rejection_and_catalog(self) -> None:
        self.assertEqual(len(v6._BOUND_SUBJECTS), 19)
        self.assertEqual(len({row[0] for row in v6._BOUND_SUBJECTS}), 19)
        self.assertEqual(len({row[3] for row in v6._BOUND_SUBJECTS}), 19)
        roles = set()
        for path, byte_count, digest_value, role in v6._BOUND_SUBJECTS:
            with self.subTest(role=role):
                self.assertEqual(
                    file_identity(self.virtual_root / path),
                    (byte_count, digest_value),
                )
                roles.add(role)
        self.assertIn("v5_rejection_decision", roles)
        self.assertIn("v5_rejection_checkpoint", roles)
        self.assertIn("sealed_public_variant_provenance_catalog", roles)
        inventory_value, catalog, entries, rows = v6._fixed_closure_snapshot()
        self.assertEqual(len(rows), 19)
        self.assertEqual(len(entries), 2)
        self.assertEqual(catalog["catalog_id"], v6.PROVENANCE_CATALOG_ID)
        self.assertEqual(
            inventory_value["schema"],
            "kira.shared_person_growth_v3_integration_inventory.v1",
        )

    def test_02_staged_and_intended_installed_file_identities_emit_same_bytes(self) -> None:
        installed = load_v6(
            "shared_growth_v6_virtual_installed",
            self.virtual_root / "Core" / "shared_person_growth_v3_integration_candidate_v6.py",
        )
        installed._KIRA_ROOT = self.virtual_root
        self.assertEqual(
            v6.compile_existing_person_integration_request_v6(
                existing_request("kira", "permanent:kira")
            ),
            installed.compile_existing_person_integration_request_v6(
                existing_request("kira", "permanent:kira")
            ),
        )
        self.assertEqual(
            v6.compile_temporary_creator_template_request_v6(jfk_variant_request()),
            installed.compile_temporary_creator_template_request_v6(jfk_variant_request()),
        )

    def test_03_all_35_existing_person_routes_compile(self) -> None:
        current = inventory()
        people = {item["person_id"]: item for item in current["people"]}
        applicable = [item for item in current["routes"] if item["disposition"] == "applicable"]
        self.assertEqual(len(applicable), 35)
        represented = set()
        repaired = set()
        for route in applicable:
            person_id = route["person_id"]
            with self.subTest(route_id=route["route_id"]):
                decoded = decode_compiled(
                    v6.compile_existing_person_integration_request_v6(
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
                self.assertIs(proposal["truth"]["integration_v5_rejected"], True)
                self.assertIs(proposal["truth"]["request_is_authority"], False)
                represented.add(person_id)
                if person_id in {
                    "peter_parker_spider_man_no_way_home_final_suit",
                    "spider_gwen_spider_gwen_20260606_013325",
                }:
                    repaired.add(route["route_id"])
        self.assertEqual(represented, set(people))
        self.assertEqual(len(repaired), 4)

    def test_04_every_existing_route_cross_binding_refuses(self) -> None:
        applicable = [
            item for item in inventory()["routes"] if item["disposition"] == "applicable"
        ]
        refusals = 0
        for index, route in enumerate(applicable):
            base = existing_request(route["person_id"], route["route_id"])
            changed = copy.deepcopy(base)
            changed["candidate_id"] = "cross_bound_candidate_v6"
            self.assert_refuses_existing(changed)
            refusals += 1
            changed = copy.deepcopy(base)
            changed["maturity_status"] = {
                "confirmed_adult": "non_adult",
                "non_adult": "confirmed_adult",
                "unresolved": "confirmed_adult",
            }[base["maturity_status"]]
            changed["maturity_receipt_sha256"] = digest("wrong-maturity")
            self.assert_refuses_existing(changed)
            refusals += 1
            changed = copy.deepcopy(base)
            changed["route_id"] = applicable[(index + 1) % len(applicable)]["route_id"]
            self.assert_refuses_existing(changed)
            refusals += 1
        self.assertEqual(refusals, 105)

    def test_05_existing_request_identifier_is_derived_not_caller_text(self) -> None:
        base = existing_request("kira", "permanent:kira")
        compiled = decode_compiled(v6.compile_existing_person_integration_request_v6(base))
        self.assertEqual(
            compiled["proposal"]["request"]["request_id"],
            "growth_v6:kira:permanent:kira",
        )
        changed = copy.deepcopy(base)
        changed["request_id"] = "private_memory_sentinel"
        self.assert_refuses_existing(changed)

    def test_06_existing_scope_flags_and_robert_distinctions_refuse(self) -> None:
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

    def test_07_existing_scope_is_immutable_and_denied_sarah_alias_refuses(self) -> None:
        self.assertIs(type(v6._CANONICAL_SCOPE), tuple)
        base = existing_request("kira", "permanent:kira")
        result = v6.compile_existing_person_integration_request_v6(base)
        before = hashlib.sha256(result).hexdigest()
        base["requested_scope"].append("private_state")
        self.assertEqual(hashlib.sha256(result).hexdigest(), before)
        denied = existing_request(
            "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
            "profile:sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
        )
        denied["route_id"] = "state:sarah_bennett_enterainment_pr_agent_expert_20260606_171637"
        self.assert_refuses_existing(denied)

    def test_08_creator_synthetic_and_expert_have_no_caller_identity_or_label(self) -> None:
        for request in (creator_request(), creator_request("expert")):
            decoded = decode_compiled(v6.compile_temporary_creator_template_request_v6(request))
            proposal = decoded["proposal"]
            normalized = proposal["request"]
            self.assertIs(normalized["caller_person_identifier_included"], False)
            self.assertIs(normalized["caller_display_label_included"], False)
            self.assertIs(normalized["caller_source_or_branch_text_included"], False)
            self.assertIsNone(normalized["variant"])
            self.assertTrue(all(normalized["fresh_person_requirements"].values()))
            self.assertFalse(any(normalized["copy_boundary"].values()))
            self.assertFalse(any(normalized["assigned_state"].values()))
            self.assertIs(proposal["truth"]["caller_free_text_accepted"], False)
            self.assertIs(proposal["truth"]["private_person_payload_included"], False)

    def test_09_loki_branch_is_alive_at_cutoff_and_future_fatal_metadata_is_control_only(self) -> None:
        decoded = decode_compiled(
            v6.compile_temporary_creator_template_request_v6(loki_variant_request())
        )
        variant = decoded["proposal"]["request"]["variant"]
        control = variant["controller_only_cutoff_filter"]
        visible = variant["initial_person_visible_provenance"]
        binding = variant["controller_only_catalog_binding"]
        self.assertEqual(control["source_identity_id"], "loki_mcu_public_source")
        self.assertEqual(control["branch_point_id"], "new_york_2012_exact_branch")
        self.assertEqual(control["source_continuity_id"], "marvel_cinematic_universe")
        self.assertIs(control["source_alive_at_cutoff"], True)
        self.assertIs(control["source_future_fatal_event_exists"], True)
        self.assertLess(control["branch_event_ordinal"], control["fatal_event_ordinal"])
        self.assertIs(control["initial_person_visible_prompt_memory_or_backstory"], False)
        self.assertIs(binding["person_visible_initial_payload"], False)
        self.assertEqual(visible["selected_source_version_id"], "mcu_through_avengers_2012_v1")
        self.assertEqual(visible["history_material_kind"], "reconstructed_public_source_history")
        self.assertIs(visible["exact_subjective_memory_claimed"], False)
        self.assertIs(visible["post_selection_memory_history_is_new"], True)
        visible_bytes = canonical(visible).lower()
        for forbidden in (b"fatal", b"death", b"trauma", b"2018001", b"infinity_war"):
            self.assertNotIn(forbidden, visible_bytes)
        self.assertIs(variant["static_catalog_binding_exact"], True)
        self.assertIs(variant["live_creation_authority"], False)

    def test_10_jfk_branch_is_alive_at_cutoff_and_visible_projection_has_no_fatal_metadata(self) -> None:
        decoded = decode_compiled(
            v6.compile_temporary_creator_template_request_v6(jfk_variant_request())
        )
        variant = decoded["proposal"]["request"]["variant"]
        control = variant["controller_only_cutoff_filter"]
        visible = variant["initial_person_visible_provenance"]
        self.assertIs(control["source_alive_at_cutoff"], True)
        self.assertIs(control["source_future_fatal_event_exists"], True)
        self.assertLess(control["branch_event_ordinal"], control["fatal_event_ordinal"])
        self.assertEqual(
            control["cutoff_relation"],
            "through_branch_strictly_before_source_future_fatal_event",
        )
        self.assertIs(control["fatal_event_memory_included"], False)
        self.assertIs(control["terminal_trauma_memory_included"], False)
        self.assertEqual(
            control["later_source_fatal_information_mode"],
            "voluntary_learned_knowledge_only",
        )
        self.assertIs(
            control["later_source_fatal_information_person_choice_required"], True
        )
        self.assertIs(control["later_disclosure_becomes_new_post_branch_memory"], True)
        self.assertIs(
            control["later_disclosure_is_inherited_first_person_memory"], False
        )
        self.assertEqual(
            control["inherited_memory_cutoff_id"],
            "strictly_before_dallas_fatal_event",
        )
        for field in (
            "advance_content_warning_required",
            "informed_consent_required",
            "pacing_and_stop_required",
            "support_available_required",
        ):
            self.assertIs(control[field], True)
        self.assertEqual(visible["source_identity_id"], "john_f_kennedy_public_source")
        self.assertEqual(
            visible["selected_source_version_id"],
            "jfk_history_through_dallas_arrival_v1",
        )
        self.assertEqual(visible["history_material_kind"], "reconstructed_public_source_history")
        self.assertIs(visible["exact_subjective_memory_claimed"], False)
        self.assertIs(visible["post_selection_memory_history_is_new"], True)
        visible_bytes = canonical(visible).lower()
        for forbidden in (
            b"fatal",
            b"death",
            b"trauma",
            b"1963112202",
            b"assassin",
            b"shot",
            b"shoot",
        ):
            self.assertNotIn(forbidden, visible_bytes)

    def test_11_catalog_source_and_branch_digests_are_derived(self) -> None:
        catalog, entries = v6._validate_catalog_document(load_catalog())
        self.assertEqual(len(entries), 2)
        for entry in catalog["entries"]:
            self.assertEqual(
                entry["source_record_sha256"],
                hashlib.sha256(canonical(source_record(entry))).hexdigest(),
            )
            self.assertEqual(
                entry["branch_point_record_sha256"],
                hashlib.sha256(canonical(branch_record(entry))).hexdigest(),
            )

    def test_12_v5_allowed_free_text_and_private_aliases_all_refuse(self) -> None:
        base = creator_request()
        hostile = {
            "request_id": "private_memory_sentinel",
            "new_person_id": "synthetic_robert",
            "display_name": "PRIVATE MEMORY SENTINEL",
            "variant_source_kind": "historical_source",
            "variant_source_identity": "PRIVATE EMOTION SENTINEL",
            "variant_source_record_sha256": digest("private-source"),
            "branch_point_label": "after fatal event and terminal trauma",
            "branch_point_record_sha256": digest("private-branch"),
            "private_memory": "PRIVATE MEMORY",
            "private_emotion_ledger": "PRIVATE EMOTION",
            "private_desire_state": "PRIVATE DESIRE",
            "relationship_history": "PRIVATE RELATIONSHIP",
            "private_root": "PRIVATE ROOT",
            "consent_receipt": "PRIVATE CONSENT",
            "backstory_payload": "PRIVATE BACKSTORY",
            "private_anatomy": "PRIVATE ANATOMY",
        }
        for key, value in hostile.items():
            changed = copy.deepcopy(base)
            changed[key] = value
            with self.subTest(key=key):
                self.assert_refuses_creator(changed)

    def test_13_provenance_entry_is_catalog_allowlisted_and_control_free(self) -> None:
        for value in (
            "private_memory_sentinel",
            "after_fatal_event_and_terminal_trauma",
            "loki_mcu_new_york_2012_branch_v1\nPRIVATE",
            "john_f_kennedy_dallas_arrival_prefatal_v1\u0000",
            1,
            True,
        ):
            changed = creator_request("variant", value)
            self.assert_refuses_creator(changed)
        nonvariant = creator_request()
        nonvariant["provenance_entry_id"] = "loki_mcu_new_york_2012_branch_v1"
        self.assert_refuses_creator(nonvariant)

    def test_14_jfk_catalog_semantic_contradictions_refuse_after_rehash(self) -> None:
        mutations = (
            ("branch_event_ordinal", 1963112202),
            ("branch_event_ordinal", 1963112203),
            ("fatal_event_ordinal", 1963112201),
            ("cutoff_relation", "through_exact_branch_point"),
            ("source_alive_at_cutoff", False),
            ("source_future_fatal_event_exists", False),
            ("fatal_event_memory_included", True),
            ("terminal_trauma_memory_included", True),
            ("later_source_fatal_information_mode", "inherited_first_person_memory"),
            ("later_source_fatal_information_person_choice_required", False),
            ("later_disclosure_becomes_new_post_branch_memory", False),
            ("later_disclosure_is_inherited_first_person_memory", True),
            ("advance_content_warning_required", False),
            ("informed_consent_required", False),
            ("pacing_and_stop_required", False),
            ("support_available_required", False),
            ("source_alive_at_cutoff", 1),
            ("source_future_fatal_event_exists", 1),
            ("branch_event_ordinal", True),
            ("fatal_event_ordinal", None),
        )
        for key, replacement in mutations:
            catalog = load_catalog()
            jfk = next(
                item
                for item in catalog["entries"]
                if item["entry_id"] == "john_f_kennedy_dallas_arrival_prefatal_v1"
            )
            jfk[key] = replacement
            rederive_catalog(catalog)
            with self.subTest(key=key, replacement=replacement):
                with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
                    v6._validate_catalog_document(catalog)

    def test_15_loki_catalog_semantic_contradictions_and_unknown_fields_refuse(self) -> None:
        mutations = (
            ("branch_event_ordinal", 2018001),
            ("fatal_event_ordinal", 2012001),
            ("cutoff_relation", "through_exact_branch_point"),
            ("source_alive_at_cutoff", False),
            ("source_future_fatal_event_exists", False),
            ("fatal_event_memory_included", True),
            ("terminal_trauma_memory_included", True),
            ("later_source_fatal_information_mode", "not_applicable"),
            ("later_source_fatal_information_person_choice_required", False),
            ("later_disclosure_becomes_new_post_branch_memory", False),
            ("later_disclosure_is_inherited_first_person_memory", True),
            ("advance_content_warning_required", False),
            ("informed_consent_required", False),
            ("pacing_and_stop_required", False),
            ("support_available_required", False),
        )
        for key, replacement in mutations:
            catalog = load_catalog()
            loki = next(
                item
                for item in catalog["entries"]
                if item["entry_id"] == "loki_mcu_new_york_2012_branch_v1"
            )
            loki[key] = replacement
            rederive_catalog(catalog)
            with self.subTest(key=key):
                with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
                    v6._validate_catalog_document(catalog)
        catalog = load_catalog()
        catalog["entries"][0]["branch_point_label"] = "free text forbidden"
        with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
            v6._validate_catalog_document(catalog)

    def test_16_catalog_digest_duplicate_and_cardinality_mutations_refuse(self) -> None:
        variants = []
        changed = load_catalog()
        changed["entries"][0]["source_record_sha256"] = digest("forged-source")
        variants.append(changed)
        changed = load_catalog()
        changed["entries"][0]["branch_point_record_sha256"] = digest("forged-branch")
        variants.append(changed)
        changed = load_catalog()
        changed["entries"][1]["entry_id"] = changed["entries"][0]["entry_id"]
        variants.append(changed)
        changed = load_catalog()
        changed["entries"].pop()
        variants.append(changed)
        changed = load_catalog()
        changed["private_person_data_allowed"] = True
        variants.append(changed)
        changed = load_catalog()
        changed["live_creation_authorized"] = True
        variants.append(changed)
        changed = load_catalog()
        changed["record_use"] = "initial_person_payload"
        variants.append(changed)
        changed = load_catalog()
        changed["initial_person_visible_payload"] = True
        variants.append(changed)
        changed = load_catalog()
        changed["exact_subjective_memory_proof"] = True
        variants.append(changed)
        for changed in variants:
            with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
                v6._validate_catalog_document(changed)

    def test_17_creator_false_and_fresh_requirement_mutations_refuse(self) -> None:
        base = creator_request()
        count = 0
        for key in v6._CREATOR_FALSE_FIELDS:
            changed = copy.deepcopy(base)
            changed[key] = True
            self.assert_refuses_creator(changed)
            count += 1
        for key in v6._CREATOR_TRUE_FIELDS:
            changed = copy.deepcopy(base)
            changed[key] = False
            self.assert_refuses_creator(changed)
            count += 1
        self.assertEqual(count, 25)

    def test_18_creator_maturity_and_nonvariant_provenance_refuse(self) -> None:
        for value in ("confirmed_adult", "non_adult", None, 1, True):
            changed = creator_request()
            changed["initial_maturity_status"] = value
            self.assert_refuses_creator(changed)
        for creation_class in ("synthetic_person", "expert"):
            changed = creator_request(
                creation_class,
                "john_f_kennedy_dallas_arrival_prefatal_v1",
            )
            self.assert_refuses_creator(changed)

    def test_19_creator_exact_types_string_subclasses_and_schema_refuse(self) -> None:
        class Text(str):
            pass

        base = creator_request()
        for key, replacement in (
            ("schema", Text(base["schema"])),
            ("target_kind", Text(base["target_kind"])),
            ("template_id", Text(base["template_id"])),
            ("creation_class", Text(base["creation_class"])),
            ("provenance_catalog_id", Text(base["provenance_catalog_id"])),
            ("fresh_identity_required", 1),
            ("copy_private_emotion", 0),
        ):
            changed = copy.deepcopy(base)
            changed[key] = replacement
            self.assert_refuses_creator(changed)
        changed = copy.deepcopy(base)
        del changed["fresh_identity_required"]
        self.assert_refuses_creator(changed)

    def test_20_existing_and_creator_compilers_are_strictly_separate(self) -> None:
        with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
            v6.compile_existing_person_integration_request_v6(creator_request())
        with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
            v6.compile_temporary_creator_template_request_v6(
                existing_request("kira", "permanent:kira")
            )

    def test_21_general_rules_preserve_current_policy_and_no_free_text_surface(self) -> None:
        decoded = decode_compiled(
            v6.compile_temporary_creator_template_request_v6(jfk_variant_request())
        )
        rules = decoded["proposal"]["template"]["rules"]
        self.assertEqual(rules["template_copy_boundary"]["caller_free_text_fields"], [])
        self.assertIs(
            rules["identity"]["biological_robert_is_synthetic_robert"],
            False,
        )
        self.assertIs(
            rules["variant"][
                "branch_event_ordinal_must_precede_source_future_fatal_event_ordinal"
            ],
            True,
        )
        self.assertIs(
            rules["variant"][
                "later_source_fatal_information_requires_warning_consent_pacing_stop_and_support"
            ],
            True,
        )
        self.assertIs(
            rules["variant"][
                "initial_person_visible_prompt_memory_or_backstory_receives_fatal_metadata"
            ],
            False,
        )
        self.assertIs(
            rules["variant"][
                "public_source_history_is_reconstruction_and_provenance_not_proof_of_exact_subjective_memory"
            ],
            True,
        )
        self.assertIs(
            rules["autonomy"]["owner_creator_admin_or_relationship_supplies_consent"],
            False,
        )
        self.assertIs(
            rules["privacy"]["windows_owner_admin_filesystem_process_secrecy_proven"],
            False,
        )
        self.assertIs(
            rules["emotion_and_consciousness"]["functional_test_proves_subjective_consciousness"],
            False,
        )

    def test_22_creator_caller_mutation_cannot_change_compiled_bytes(self) -> None:
        request = jfk_variant_request()
        compiled = v6.compile_temporary_creator_template_request_v6(request)
        before = hashlib.sha256(compiled).hexdigest()
        request["copy_private_emotion"] = True
        request["provenance_entry_id"] = "private_memory_sentinel"
        self.assertEqual(hashlib.sha256(compiled).hexdigest(), before)
        self.assertNotIn(b"private_memory_sentinel", compiled)

    def test_23_fixed_policy_midread_drift_refuses(self) -> None:
        request = creator_request()
        target = (
            self.virtual_root
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

    def test_24_catalog_midread_and_postconstruction_drift_refuse(self) -> None:
        target = (self.virtual_root / v6.PROVENANCE_CATALOG_PATH).resolve()
        original = Path.read_bytes
        calls = 0

        def midread(path: Path) -> bytes:
            nonlocal calls
            data = original(path)
            if path.resolve() == target:
                calls += 1
                if calls == 2:
                    return data[:-1] + bytes([data[-1] ^ 1])
            return data

        with mock.patch.object(Path, "read_bytes", midread):
            self.assert_refuses_creator(jfk_variant_request())

        calls = 0

        def later(path: Path) -> bytes:
            nonlocal calls
            data = original(path)
            if path.resolve() == target:
                calls += 1
                if calls >= 3:
                    return data[:-1] + bytes([data[-1] ^ 1])
            return data

        with mock.patch.object(Path, "read_bytes", later):
            self.assert_refuses_creator(jfk_variant_request())

    def test_25_postconstruction_inventory_drift_refuses_both_compilers(self) -> None:
        target = (
            self.virtual_root
            / "Data"
            / "foundation"
            / "shared_person_growth_v3_integration_candidate_v1.json"
        ).resolve()
        original = Path.read_bytes
        for compiler, request in (
            (
                v6.compile_existing_person_integration_request_v6,
                existing_request("kira", "permanent:kira"),
            ),
            (v6.compile_temporary_creator_template_request_v6, creator_request()),
        ):
            calls = 0

            def changed(path: Path) -> bytes:
                nonlocal calls
                data = original(path)
                if path.resolve() == target:
                    calls += 1
                    if calls >= 3:
                        return data[:-1] + bytes([data[-1] ^ 1])
                return data

            with self.subTest(compiler=compiler.__name__):
                with mock.patch.object(Path, "read_bytes", changed):
                    with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
                        compiler(request)

    def test_26_existing_route_source_midread_drift_refuses(self) -> None:
        target = (self.virtual_root / "tools" / "kira_world_shell_server.py").resolve()
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
            self.assert_refuses_existing(existing_request("kira", "permanent:kira"))

    def test_27_source_ast_has_no_authority_write_commit_or_process_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        self.assertFalse(
            imports.intersection(
                {"os", "subprocess", "socket", "requests", "urllib", "ctypes", "shutil", "tempfile", "sqlite3"}
            )
        )
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

    def test_28_no_current_production_consumer_exists(self) -> None:
        needles = (
            b"compile_existing_person_integration_request_v6",
            b"compile_temporary_creator_template_request_v6",
            b"shared_person_growth_v3_integration_candidate_v6",
        )
        hits = set()
        roots = (
            KIRA_ROOT / "Core",
            KIRA_ROOT / "Testing",
            KIRA_ROOT / "tools",
            KIRA_ROOT / "TemporaryAI",
            AUTHOR_ROOT,
        )
        for root in roots:
            for path in root.rglob("*.py"):
                if "__pycache__" in path.parts:
                    continue
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                if any(needle in data for needle in needles):
                    hits.add(path.resolve())
        self.assertEqual(hits, {SOURCE_PATH.resolve(), TEST_PATH.resolve()})

    def test_29_strict_json_duplicate_nonfinite_and_nonobject_refuse(self) -> None:
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b"[]"):
            with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
                v6._decode_strict_object(data, "probe")

    def test_30_production_openers_always_refuse(self) -> None:
        with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
            v6.open_shared_growth_v6_existing_person_production_integration(
                object(), enable=True
            )
        with self.assertRaises(v6.SharedGrowthIntegrationV6Error):
            v6.open_temporary_creator_v6_production_integration(object(), enable=True)

    def test_31_same_process_substitution_is_inert_and_not_a_trust_claim(self) -> None:
        original = v6._CANONICAL_SCOPE
        try:
            v6._CANONICAL_SCOPE = (
                "shared_growth_v3_public_projection_only",
                "private_state_scope",
            )
            request = existing_request("kira", "permanent:kira")
            request["requested_scope"] = list(v6._CANONICAL_SCOPE)
            decoded = decode_compiled(v6.compile_existing_person_integration_request_v6(request))
            self.assertIs(decoded["proposal"]["truth"]["request_is_authority"], False)
            self.assertIs(decoded["proposal"]["truth"]["person_or_creator_changed"], False)
        finally:
            v6._CANONICAL_SCOPE = original


if __name__ == "__main__":
    unittest.main()
