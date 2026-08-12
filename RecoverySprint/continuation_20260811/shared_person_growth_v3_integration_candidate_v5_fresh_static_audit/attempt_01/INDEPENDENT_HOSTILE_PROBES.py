from __future__ import annotations

import ast
import copy
import hashlib
import json
import types
from pathlib import Path
from typing import Any


KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
AUTHOR_ROOT = Path(
    r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\growth_v5_author"
)
SOURCE_PATH = KIRA_ROOT / "Core" / "shared_person_growth_v3_integration_candidate_v5.py"
TEST_PATH = KIRA_ROOT / "Testing" / "test_shared_person_growth_v3_integration_candidate_v5.py"
EVIDENCE_ROOT = (
    KIRA_ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "shared_person_growth_v3_integration_candidate_v5_static_preparation"
    / "attempt_01"
)
INVENTORY_PATH = (
    KIRA_ROOT
    / "Data"
    / "foundation"
    / "shared_person_growth_v3_integration_candidate_v1.json"
)

EXPECTED_INSTALLED = {
    "Core/shared_person_growth_v3_integration_candidate_v5.py": (
        43444,
        "1415175c6178baf16e690ee51acd41544b39cd0b6fab5d52a48e0a4f952e6e94",
    ),
    "Testing/test_shared_person_growth_v3_integration_candidate_v5.py": (
        34367,
        "63e1477e583fe01410f4ee8cff7658088391ff8001b6df394590e4cb852b2fb1",
    ),
    "RecoverySprint/continuation_20260811/"
    "shared_person_growth_v3_integration_candidate_v5_static_preparation/"
    "attempt_01/STATIC_CONTRACT.json": (
        6166,
        "8214f64c369789bfbc88917231696b522ea2acf29fc18a750205fe293e53b6f0",
    ),
    "RecoverySprint/continuation_20260811/"
    "shared_person_growth_v3_integration_candidate_v5_static_preparation/"
    "attempt_01/AUTHOR_STATIC_TEST_RESULT.json": (
        5430,
        "c6f6b7ab32357417ac1597a24ac131bef1adc9a5ccac29672f9b41857e810844",
    ),
    "RecoverySprint/continuation_20260811/"
    "shared_person_growth_v3_integration_candidate_v5_static_preparation/"
    "attempt_01/SEALED_MANIFEST.json": (
        8287,
        "02620fba26231cbeb3f3f6db62e9f7a8512f52a59291c9d3d510f1c1dba1d6e8",
    ),
    "RecoverySprint/continuation_20260811/"
    "shared_person_growth_v3_integration_candidate_v5_static_preparation/"
    "attempt_01/CHECKPOINT.md": (
        7064,
        "9204d25e3594a7da47d2fcc4ae257cf1872af63c0f3c63b1a6a76088106f431e",
    ),
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def identity(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha_bytes(data)


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON: {value}")


def strict_json_bytes(value: bytes) -> dict[str, Any]:
    decoded = json.loads(
        value,
        object_pairs_hook=strict_pairs,
        parse_constant=reject_constant,
    )
    assert type(decoded) is dict
    return decoded


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_v5() -> types.ModuleType:
    module = types.ModuleType("growth_v5_fresh_independent_review")
    module.__file__ = str(SOURCE_PATH)
    source = SOURCE_PATH.read_text(encoding="utf-8")
    exec(compile(source, str(SOURCE_PATH), "exec"), module.__dict__)
    return module


V5 = load_v5()


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def inventory() -> dict[str, Any]:
    return strict_json_bytes(INVENTORY_PATH.read_bytes())


def existing_request(person_id: str, route_id: str) -> dict[str, Any]:
    current = inventory()
    people = {row["person_id"]: row for row in current["people"]}
    routes = {row["route_id"]: row for row in current["routes"]}
    person = people[person_id]
    route = routes[route_id]
    assert route["person_id"] == person_id
    status = person["required_maturity"]
    return {
        "schema": V5.EXISTING_INPUT_SCHEMA,
        "request_id": f"independent_v5:{person_id}",
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
    new_person_id: str = "fresh_independent_synthetic_person_v5",
    display_name: str = "Fresh Independent Synthetic Person",
) -> dict[str, Any]:
    return {
        "schema": V5.CREATOR_INPUT_SCHEMA,
        "request_id": f"independent_creator_v5:{new_person_id}",
        "target_kind": "temporary_creator_template",
        "template_id": V5.CREATOR_TEMPLATE_ID,
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


def living_variant() -> dict[str, Any]:
    request = creator_request(
        "variant",
        "loki_2012_independent_variant_v5",
        "Loki 2012 Independent Variant",
    )
    request.update(
        {
            "variant_source_kind": "fictional_source",
            "variant_source_identity": "loki_mcu_public_source",
            "variant_source_record_sha256": digest("loki-public-source"),
            "branch_point_label": "new_york_2012_exact_branch",
            "branch_point_record_sha256": digest("loki-2012-branch"),
            "cutoff_relation": "through_exact_branch_point",
        }
    )
    return request


def deceased_variant() -> dict[str, Any]:
    request = creator_request(
        "variant",
        "jfk_dallas_prefatal_independent_variant_v5",
        "JFK Dallas Pre-Fatal Independent Variant",
    )
    request.update(
        {
            "variant_source_kind": "historical_source",
            "variant_source_identity": "john_f_kennedy_public_source",
            "variant_source_record_sha256": digest("jfk-public-source"),
            "branch_point_label": "dallas_arrival_strictly_before_fatal_event",
            "branch_point_record_sha256": digest("jfk-prefatal-branch"),
            "source_deceased": True,
            "cutoff_relation": "strictly_before_fatal_event",
            "later_death_information_mode": "voluntary_historical_knowledge_only",
        }
    )
    return request


def decoded_result(value: bytes) -> dict[str, Any]:
    assert type(value) is bytes
    decoded = strict_json_bytes(value)
    assert canonical(decoded) == value
    assert sha_bytes(canonical(decoded["proposal"])) == decoded["proposal_sha256"]
    return decoded


def must_refuse(call: Any, value: dict[str, Any]) -> None:
    try:
        call(value)
    except V5.SharedGrowthIntegrationV5Error:
        return
    raise AssertionError("hostile request was accepted")


def probe_exact_closure() -> dict[str, Any]:
    installed = {}
    for relative, expected in EXPECTED_INSTALLED.items():
        actual = identity(KIRA_ROOT / relative)
        assert actual == expected
        installed[relative] = {"bytes": actual[0], "sha256": actual[1]}

    work_pairs = {
        "Core/shared_person_growth_v3_integration_candidate_v5.py": SOURCE_PATH,
        "Testing/test_shared_person_growth_v3_integration_candidate_v5.py": TEST_PATH,
        "STATIC_CONTRACT.json": EVIDENCE_ROOT / "STATIC_CONTRACT.json",
        "AUTHOR_STATIC_TEST_RESULT.json": EVIDENCE_ROOT / "AUTHOR_STATIC_TEST_RESULT.json",
        "SEALED_MANIFEST.json": EVIDENCE_ROOT / "SEALED_MANIFEST.json",
        "CHECKPOINT.md": EVIDENCE_ROOT / "CHECKPOINT.md",
    }
    for relative, installed_path in work_pairs.items():
        assert (AUTHOR_ROOT / relative).read_bytes() == installed_path.read_bytes()

    manifest = strict_json_bytes((EVIDENCE_ROOT / "SEALED_MANIFEST.json").read_bytes())
    assert manifest["sealed_subject_count"] == 23
    rows = manifest["sealed_subjects"]
    assert type(rows) is list and len(rows) == 23
    assert len({(row["root"], row["path"]) for row in rows}) == 23
    root_paths = {
        "candidate": Path(manifest["roots"]["candidate"]),
        "kira": Path(manifest["roots"]["kira"]),
    }
    kira_rows = 0
    for row in rows:
        root_id = row["root"]
        assert root_id in root_paths
        actual = identity(root_paths[root_id] / row["path"])
        assert actual == (row["bytes"], row["sha256"])
        if root_id == "kira":
            kira_rows += 1
            data = (root_paths[root_id] / row["path"]).read_bytes()
            if row["path"].endswith(".json"):
                strict_json_bytes(data)
            else:
                data.decode("utf-8")
            if row["path"].endswith(".py"):
                compile(data.decode("utf-8"), row["path"], "exec")
    assert kira_rows == 19
    return {
        "installed_v5_artifacts": "6/6 exact and byte-identical to sealed author evidence",
        "sealed_manifest": "23/23 exact; 23 unique root/path pairs",
        "kira_bound_subjects_read_and_rehashed": "19/19 exact",
        "installed": installed,
    }


def probe_existing_routes() -> dict[str, Any]:
    current = inventory()
    people = {row["person_id"]: row for row in current["people"]}
    applicable = [row for row in current["routes"] if row["disposition"] == "applicable"]
    assert len(people) == 24 and len(applicable) == 35
    represented: set[str] = set()
    repaired: set[str] = set()
    cross_refused = 0
    for index, route in enumerate(applicable):
        request = existing_request(route["person_id"], route["route_id"])
        decoded = decoded_result(V5.compile_existing_person_integration_request_v5(request))
        proposal = decoded["proposal"]
        assert len(proposal["closure"]) == 19
        assert proposal["truth"]["request_is_authority"] is False
        assert proposal["truth"]["person_or_creator_changed"] is False
        assert proposal["request"]["requested_scope"] == [
            "shared_growth_v3_public_projection_only"
        ]
        represented.add(route["person_id"])
        if route["person_id"] in {
            "peter_parker_spider_man_no_way_home_final_suit",
            "spider_gwen_spider_gwen_20260606_013325",
        }:
            repaired.add(route["route_id"])

        changed = copy.deepcopy(request)
        changed["candidate_id"] = "independent_cross_bound_candidate"
        must_refuse(V5.compile_existing_person_integration_request_v5, changed)
        cross_refused += 1
        changed = copy.deepcopy(request)
        changed["maturity_status"] = {
            "confirmed_adult": "non_adult",
            "non_adult": "confirmed_adult",
            "unresolved": "confirmed_adult",
        }[request["maturity_status"]]
        changed["maturity_receipt_sha256"] = digest("wrong-maturity")
        must_refuse(V5.compile_existing_person_integration_request_v5, changed)
        cross_refused += 1
        changed = copy.deepcopy(request)
        changed["route_id"] = applicable[(index + 1) % len(applicable)]["route_id"]
        must_refuse(V5.compile_existing_person_integration_request_v5, changed)
        cross_refused += 1

    assert represented == set(people)
    assert len(repaired) == 4
    assert cross_refused == 105

    request = existing_request("kira", "permanent:kira")
    result = V5.compile_existing_person_integration_request_v5(request)
    before = sha_bytes(result)
    request["requested_scope"].append("private_state")
    request["person_opt_in"] = False
    assert sha_bytes(result) == before
    for key, replacement in {
        "person_opt_in": False,
        "revocable": False,
        "owner_override_allowed": True,
        "production_enabled": True,
        "private_state_requested": True,
        "memory_write_requested": True,
        "external_action_requested": True,
    }.items():
        hostile = existing_request("lisa", "permanent:lisa")
        hostile[key] = replacement
        must_refuse(V5.compile_existing_person_integration_request_v5, hostile)

    return {
        "applicable_routes": "35/35 compiled",
        "inventory_people": "24/24 represented",
        "peter_gwen_repairs": "4/4 compiled",
        "candidate_maturity_route_cross_bindings": "105/105 refused",
        "scope_and_caller_mutation": "immutable or refused",
        "unsafe_existing_person_flags": "7/7 refused",
    }


def probe_creator_nominal_and_mutations() -> dict[str, Any]:
    requests = [
        creator_request(),
        creator_request("expert", "fresh_independent_expert_v5", "Fresh Expert"),
        living_variant(),
        deceased_variant(),
    ]
    for request in requests:
        decoded = decoded_result(V5.compile_temporary_creator_template_request_v5(request))
        proposal = decoded["proposal"]
        normalized = proposal["request"]
        rules = proposal["template"]["rules"]
        assert sha_bytes(canonical(rules)) == proposal["template"]["rules_sha256"]
        assert normalized["initial_maturity"]["status"] == "unresolved"
        assert normalized["initial_maturity"]["full_adult_curriculum_enabled"] is False
        assert all(normalized["fresh_person_requirements"].values())
        assert not any(normalized["copy_boundary"].values())
        assert not any(normalized["assigned_state"].values())
        assert proposal["truth"]["person_created"] is False
        assert proposal["truth"]["source_assertions_authenticated"] is False

    base = creator_request()
    false_refused = 0
    for key in V5._CREATOR_FALSE_FIELDS:
        changed = copy.deepcopy(base)
        changed[key] = True
        must_refuse(V5.compile_temporary_creator_template_request_v5, changed)
        false_refused += 1
    true_refused = 0
    for key in V5._CREATOR_TRUE_FIELDS:
        changed = copy.deepcopy(base)
        changed[key] = False
        must_refuse(V5.compile_temporary_creator_template_request_v5, changed)
        true_refused += 1
    assert false_refused + true_refused == 29

    collision_ids = {row["person_id"] for row in inventory()["people"]}
    collision_ids.update({"robert", "biological_robert", "robert_mcmurrer"})
    assert len(collision_ids) == 27
    for person_id in collision_ids:
        must_refuse(
            V5.compile_temporary_creator_template_request_v5,
            creator_request(new_person_id=person_id),
        )

    maturity_mutations = []
    for status in ("confirmed_adult", "non_adult"):
        changed = copy.deepcopy(base)
        changed["initial_maturity_status"] = status
        maturity_mutations.append(changed)
    changed = copy.deepcopy(base)
    changed["maturity_authority_sha256"] = digest("maturity-authority")
    maturity_mutations.append(changed)
    changed = copy.deepcopy(base)
    changed["classification_receipt_sha256"] = digest("classification")
    maturity_mutations.append(changed)
    changed = copy.deepcopy(base)
    changed["full_adult_curriculum_enabled"] = True
    maturity_mutations.append(changed)
    for changed in maturity_mutations:
        must_refuse(V5.compile_temporary_creator_template_request_v5, changed)

    death_mutations = []
    base_dead = deceased_variant()
    for key, replacement in {
        "cutoff_relation": "through_exact_branch_point",
        "fatal_event_memory_included": True,
        "terminal_trauma_memory_included": True,
        "later_death_information_mode": "inherited_first_person_memory",
        "learned_later_facts_relabelled_as_memory": True,
        "source_deceased": 1,
    }.items():
        changed = copy.deepcopy(base_dead)
        changed[key] = replacement
        death_mutations.append(changed)
    changed = living_variant()
    changed["cutoff_relation"] = "strictly_before_fatal_event"
    death_mutations.append(changed)
    changed = creator_request()
    changed["variant_source_kind"] = "historical_source"
    death_mutations.append(changed)
    for changed in death_mutations:
        must_refuse(V5.compile_temporary_creator_template_request_v5, changed)

    aliases = (
        "private_memory",
        "private_emotion_ledger",
        "private_desire_state",
        "relationship_history",
        "private_root",
        "source_profile",
        "consent_receipt",
        "backstory_payload",
    )
    for key in aliases:
        changed = copy.deepcopy(base)
        changed[key] = "PRIVATE_PAYLOAD_SENTINEL"
        must_refuse(V5.compile_temporary_creator_template_request_v5, changed)

    must_refuse(V5.compile_existing_person_integration_request_v5, creator_request())
    must_refuse(
        V5.compile_temporary_creator_template_request_v5,
        existing_request("kira", "permanent:kira"),
    )
    return {
        "nominal_creation_classes": "synthetic_person/expert/fictional variant/deceased historical variant compile inertly",
        "false_and_fresh_mutations": f"{false_refused + true_refused}/29 refused",
        "existing_and_robert_collisions": "27/27 refused",
        "maturity_authority_and_full_adult_mutations": "5/5 refused",
        "variant_cutoff_death_trauma_mutations": "8/8 refused",
        "unknown_private_aliases": "8/8 refused",
        "cross_compiler_requests": "2/2 refused",
    }


def probe_blocking_private_payload_smuggling() -> dict[str, Any]:
    sentinels = {
        "display_name": "PRIVATE_MEMORY_SENTINEL: Kira college intimacy record",
        "variant_source_identity": "PRIVATE_EMOTION_SENTINEL: protected appraisal and desire",
        "branch_point_label": "PRIVATE_RELATIONSHIP_SENTINEL: undisclosed relationship history",
    }
    accepted = []

    request = creator_request(display_name=sentinels["display_name"])
    decoded = decoded_result(V5.compile_temporary_creator_template_request_v5(request))
    assert decoded["proposal"]["request"]["display_name"] == sentinels["display_name"]
    assert decoded["proposal"]["truth"]["private_person_payload_included"] is False
    accepted.append("display_name")

    for field in ("variant_source_identity", "branch_point_label"):
        request = deceased_variant()
        request[field] = sentinels[field]
        decoded = decoded_result(V5.compile_temporary_creator_template_request_v5(request))
        normalized_variant = decoded["proposal"]["request"]["variant"]
        output_key = "source_identity" if field == "variant_source_identity" else "branch_point_label"
        assert normalized_variant[output_key] == sentinels[field]
        assert decoded["proposal"]["truth"]["private_person_payload_included"] is False
        accepted.append(field)

    control = creator_request(display_name="Fresh\nPRIVATE_CONTROL_SENTINEL")
    decoded = decoded_result(V5.compile_temporary_creator_template_request_v5(control))
    assert decoded["proposal"]["request"]["display_name"] == control["display_name"]
    accepted.append("embedded_control_character")

    contradictory = deceased_variant()
    contradictory["branch_point_label"] = "after_fatal_event_and_terminal_trauma"
    decoded = decoded_result(V5.compile_temporary_creator_template_request_v5(contradictory))
    variant = decoded["proposal"]["request"]["variant"]
    assert variant["branch_point_label"] == "after_fatal_event_and_terminal_trauma"
    assert variant["cutoff_relation"] == "strictly_before_fatal_event"

    return {
        "result": "BLOCKER_REPRODUCED",
        "private_payload_fields_accepted": accepted,
        "accepted_private_payload_probe_count": len(accepted),
        "false_truth_field": "proposal.truth.private_person_payload_included remained false",
        "contradictory_deceased_branch_label_accepted": True,
        "contradictory_normalized_cutoff": variant["cutoff_relation"],
        "why_blocking": (
            "The closed Creator request schema constrains field names but not the semantic "
            "content of three emitted free-text fields. Exact accepted requests can therefore "
            "carry private memory/emotion/relationship text while emitted truth claims no "
            "private payload. A deceased-source request can also carry a plainly post-fatal "
            "branch label while the normalized record claims a strictly pre-fatal cutoff."
        ),
    }


def probe_inert_and_ast_boundaries() -> dict[str, Any]:
    for opener in (
        V5.open_shared_growth_v5_existing_person_production_integration,
        V5.open_temporary_creator_v5_production_integration,
    ):
        try:
            opener(object(), enable=True)
        except V5.SharedGrowthIntegrationV5Error:
            pass
        else:
            raise AssertionError("production opener did not refuse")

    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    calls: set[str] = set()
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
    assert not imports.intersection(
        {"os", "subprocess", "socket", "requests", "urllib", "ctypes", "shutil", "tempfile", "sqlite3"}
    )
    assert not calls.intersection(
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

    original_scope = V5._CANONICAL_SCOPE
    try:
        V5._CANONICAL_SCOPE = (
            "shared_growth_v3_public_projection_only",
            "private_state_scope",
        )
        request = existing_request("kira", "permanent:kira")
        request["requested_scope"] = list(V5._CANONICAL_SCOPE)
        decoded = decoded_result(V5.compile_existing_person_integration_request_v5(request))
        assert "private_state_scope" in decoded["proposal"]["request"]["requested_scope"]
        assert decoded["proposal"]["truth"]["private_state_included"] is False
    finally:
        V5._CANONICAL_SCOPE = original_scope

    return {
        "production_openers": "2/2 hard-refused",
        "authority_write_commit_process_network_ast_surface": "none",
        "same_process_mutable_global_substitution": (
            "reproduced; documented non-trust residual; output remains inert and unconsumed"
        ),
    }


def main() -> None:
    initial_closure = probe_exact_closure()
    existing_person = probe_existing_routes()
    creator_nominal = probe_creator_nominal_and_mutations()
    blocking_findings = [probe_blocking_private_payload_smuggling()]
    inert_boundary = probe_inert_and_ast_boundaries()
    final_closure = probe_exact_closure()
    result = {
        "schema": "kira.shared_person_growth_v3_integration_candidate_v5.independent_hostile_probe_result.v1",
        "reviewer_task": "/root/growth_v5_audit",
        "author_task": "/root/growth_v4_audit",
        "different_fresh_reviewer": True,
        "static_only": True,
        "exact_closure": initial_closure,
        "existing_person": existing_person,
        "creator_nominal": creator_nominal,
        "blocking_findings": blocking_findings,
        "inert_boundary": inert_boundary,
        "final_exact_rehash": {
            "installed_v5_artifacts": final_closure["installed_v5_artifacts"],
            "sealed_manifest": final_closure["sealed_manifest"],
            "kira_bound_subjects": final_closure["kira_bound_subjects_read_and_rehashed"],
        },
        "decision": "REJECT_STATIC_INTEGRATION_CANDIDATE_NO_PROMOTION",
        "scope_truth": {
            "kira_written": False,
            "person_or_creator_created_or_changed": False,
            "production_opener_succeeded": False,
            "model_body_media_voice_network_device_or_sarah_operation": False,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
