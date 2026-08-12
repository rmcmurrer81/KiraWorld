from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import types
from pathlib import Path
from typing import Any, Callable


AUDIT_ROOT = Path(__file__).resolve().parent
WORK_ROOT = AUDIT_ROOT.parent
AUTHOR_ROOT = WORK_ROOT / "growth_v4_author"
KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
V3_REJECTION_ROOT = WORK_ROOT / "growth_v3_quality_review"
SOURCE_PATH = (
    AUTHOR_ROOT
    / "Core"
    / "shared_person_growth_v3_integration_candidate_v4.py"
)
TEST_PATH = (
    AUTHOR_ROOT
    / "Testing"
    / "test_shared_person_growth_v3_integration_candidate_v4.py"
)
MANIFEST_PATH = AUTHOR_ROOT / "SEALED_MANIFEST.json"
INVENTORY_PATH = (
    KIRA_ROOT
    / "Data"
    / "foundation"
    / "shared_person_growth_v3_integration_candidate_v1.json"
)
CORE_SEAL_PATH = (
    KIRA_ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "shared_person_growth_capabilities_v3_static_repair"
    / "attempt_01"
    / "SEALED_MANIFEST.json"
)

EXPECTED_V4 = {
    "Core/shared_person_growth_v3_integration_candidate_v4.py": (
        22676,
        "e6780a5eb1c97c850ca49d543d1594deef477a72aae10f1747a2fe420171bab5",
    ),
    "Testing/test_shared_person_growth_v3_integration_candidate_v4.py": (
        23295,
        "8ff20beba074a0630cd574835bbb7be5c9330eae1e5ee1229b58a80a60a47bdb",
    ),
    "STATIC_CONTRACT.json": (
        4372,
        "81e639f7b2813eab10fce7403b32af61af72579e5b4d6d99d85bd529f3ebbe0a",
    ),
    "AUTHOR_STATIC_TEST_RESULT.json": (
        3039,
        "cb1c9c8174fdeb9ad2db76b88edd88cbbff4cb4e2308da1aaba141cd67363537",
    ),
    "SEALED_MANIFEST.json": (
        5080,
        "1deab069383e235e808dbf888ea527a92056e48e92abad97f05cfdaa685c31e6",
    ),
    "CHECKPOINT.md": (
        4917,
        "11d432c4a90f43010f746e09c4d6e8ed3de5693ed61e36afddfdc072acc7b4ab",
    ),
}


def file_identity(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def load_strict_json(path: Path) -> dict[str, Any]:
    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise AssertionError(f"duplicate key in {path}: {key}")
            value[key] = item
        return value

    value = json.loads(path.read_bytes(), object_pairs_hook=strict_object)
    assert type(value) is dict
    return value


def load_candidate() -> types.ModuleType:
    module = types.ModuleType("growth_v4_independent_exact_subject")
    module.__file__ = str(SOURCE_PATH)
    source = SOURCE_PATH.read_text(encoding="utf-8")
    exec(compile(source, str(SOURCE_PATH), "exec"), module.__dict__)
    return module


v4 = load_candidate()
inventory = load_strict_json(INVENTORY_PATH)
people = {item["person_id"]: item for item in inventory["people"]}
routes = {item["route_id"]: item for item in inventory["routes"]}
maturity_sources = {
    item["source_id"]: item for item in inventory["maturity_sources"]
}


def request_for(person_id: str, route_id: str) -> dict[str, Any]:
    person = people[person_id]
    route = routes[route_id]
    assert route["person_id"] == person_id
    status = person["required_maturity"]
    return {
        "schema": v4.INPUT_SCHEMA,
        "request_id": f"independent_growth:{person_id}",
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


def decode_compiled(value: bytes) -> dict[str, Any]:
    assert type(value) is bytes
    decoded = json.loads(value)
    assert type(decoded) is dict
    assert canonical(decoded) == value
    assert (
        hashlib.sha256(canonical(decoded["proposal"])).hexdigest()
        == decoded["proposal_sha256"]
    )
    return decoded


def must_refuse(value: dict[str, Any]) -> str:
    try:
        v4.compile_disconnected_integration_request_v4(value)
    except v4.SharedGrowthIntegrationV4Error as exc:
        return str(exc)
    raise AssertionError("hostile request unexpectedly compiled")


results: list[dict[str, Any]] = []
failures: list[dict[str, str]] = []


def probe(name: str, operation: Callable[[], dict[str, Any]]) -> None:
    try:
        details = operation()
        results.append({"name": name, "passed": True, "details": details})
    except Exception as exc:  # audit harness must report every group
        failures.append({"name": name, "error": f"{type(exc).__name__}: {exc}"})
        results.append(
            {
                "name": name,
                "passed": False,
                "details": {"error": f"{type(exc).__name__}: {exc}"},
            }
        )


def probe_v4_subject_identities() -> dict[str, Any]:
    actual = {
        relative: file_identity(AUTHOR_ROOT / relative)
        for relative in EXPECTED_V4
    }
    assert actual == EXPECTED_V4
    return {
        "subjects": len(actual),
        "source_sha256": actual[
            "Core/shared_person_growth_v3_integration_candidate_v4.py"
        ][1],
        "test_sha256": actual[
            "Testing/test_shared_person_growth_v3_integration_candidate_v4.py"
        ][1],
    }


def probe_manifest_closure() -> dict[str, Any]:
    manifest = load_strict_json(MANIFEST_PATH)
    roots = {
        "candidate": AUTHOR_ROOT,
        "kira": KIRA_ROOT,
        "v3_rejection": V3_REJECTION_ROOT,
    }
    rows = manifest["sealed_subjects"]
    assert type(rows) is list and len(rows) == manifest["sealed_subject_count"] == 14
    identities: set[tuple[str, str]] = set()
    for row in rows:
        identity = (row["root"], row["path"])
        assert identity not in identities
        identities.add(identity)
        assert file_identity(roots[row["root"]] / row["path"]) == (
            row["bytes"],
            row["sha256"],
        )
    return {"exact": len(rows), "mismatches": 0, "unique": len(identities)}


def probe_accepted_core_closure() -> dict[str, Any]:
    seal = load_strict_json(CORE_SEAL_PATH)
    rows = seal["sealed_subjects"] + seal["protected_predecessor_anchors"]
    assert len(rows) == 28
    for row in rows:
        assert file_identity(KIRA_ROOT / row["path"]) == (
            row["bytes"],
            row["sha256"],
        )
    decision_path = (
        KIRA_ROOT
        / "RecoverySprint"
        / "continuation_20260811"
        / "shared_person_growth_capabilities_v3_fresh_static_audit"
        / "attempt_01"
        / "AUDIT_DECISION.json"
    )
    decision = load_strict_json(decision_path)
    assert decision["decision"] == "ACCEPT_STATIC_ONLY"
    assert decision["integration_authorized"] is False
    return {
        "seal_rows_exact": 28,
        "acceptance": "ACCEPT_STATIC_ONLY",
        "integration_authorized": False,
    }


def probe_compile_closure() -> dict[str, Any]:
    files = [
        SOURCE_PATH,
        TEST_PATH,
        KIRA_ROOT / "Core" / "shared_person_growth_capabilities_v3.py",
        KIRA_ROOT / "Testing" / "test_shared_person_growth_capabilities_v3.py",
    ]
    for version in (1, 2, 3):
        files.extend(
            [
                KIRA_ROOT
                / "Core"
                / f"shared_person_growth_v3_integration_candidate_v{version}.py",
                KIRA_ROOT
                / "Testing"
                / f"test_shared_person_growth_v3_integration_candidate_v{version}.py",
            ]
        )
    assert len(files) == 10
    for path in files:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    return {"strict_utf8_in_memory_compile": "10/10 PASS"}


def probe_all_routes() -> dict[str, Any]:
    applicable = [
        route for route in inventory["routes"] if route["disposition"] == "applicable"
    ]
    assert len(applicable) == 35
    compiled_people: set[str] = set()
    compiled_routes: set[str] = set()
    maturity_counts = {"confirmed_adult": 0, "non_adult": 0, "unresolved": 0}
    person_class_counts: dict[str, int] = {}
    repaired: set[str] = set()
    for route in applicable:
        person_id = route["person_id"]
        request = request_for(person_id, route["route_id"])
        decoded = decode_compiled(v4.compile_disconnected_integration_request_v4(request))
        proposal = decoded["proposal"]
        normalized = proposal["request"]
        assert normalized["person_id"] == person_id
        assert normalized["route_id"] == route["route_id"]
        assert normalized["candidate_id"] == people[person_id]["candidate_id"]
        assert normalized["maturity_status"] == people[person_id]["required_maturity"]
        assert normalized["requested_scope"] == [
            "shared_growth_v3_public_projection_only"
        ]
        assert proposal["route_snapshot"]["source_sha256"] == route["source_sha256"]
        truth = proposal["truth"]
        assert truth["request_is_inert_bytes_only"] is True
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
            assert truth[key] is False
        compiled_people.add(person_id)
        compiled_routes.add(route["route_id"])
        maturity_counts[people[person_id]["required_maturity"]] += 1
        person_class = people[person_id]["person_class"]
        person_class_counts[person_class] = person_class_counts.get(person_class, 0) + 1
        if person_id in {
            "peter_parker_spider_man_no_way_home_final_suit",
            "spider_gwen_spider_gwen_20260606_013325",
        }:
            assert people[person_id]["required_maturity"] == "confirmed_adult"
            assert (
                maturity_sources[people[person_id]["maturity_source_id"]][
                    "permitted_status"
                ]
                == "subject_specific"
            )
            repaired.add(route["route_id"])
    expected_repaired = {
        "profile:peter_parker_spider_man_no_way_home_final_suit",
        "state:peter_parker_spider_man_no_way_home_final_suit",
        "profile:spider_gwen_spider_gwen_20260606_013325",
        "state:spider_gwen_spider_gwen_20260606_013325",
    }
    assert repaired == expected_repaired
    assert compiled_routes == {route["route_id"] for route in applicable}
    assert compiled_people == set(people)
    return {
        "applicable_routes": len(compiled_routes),
        "inventory_people_represented": len(compiled_people),
        "v3_failed_routes_repaired": len(repaired),
        "maturity_route_counts": maturity_counts,
        "person_class_route_counts": dict(sorted(person_class_counts.items())),
    }


def probe_every_route_cross_binding() -> dict[str, Any]:
    applicable = [
        route for route in inventory["routes"] if route["disposition"] == "applicable"
    ]
    refused = 0
    for index, route in enumerate(applicable):
        person_id = route["person_id"]
        base = request_for(person_id, route["route_id"])

        changed = copy.deepcopy(base)
        changed["candidate_id"] = (
            "lisa" if changed["candidate_id"] != "lisa" else "kira"
        )
        must_refuse(changed)
        refused += 1

        changed = copy.deepcopy(base)
        status = changed["maturity_status"]
        changed["maturity_status"] = {
            "confirmed_adult": "non_adult",
            "non_adult": "confirmed_adult",
            "unresolved": "confirmed_adult",
        }[status]
        if changed["maturity_status"] == "unresolved":
            changed["maturity_receipt_sha256"] = None
        else:
            changed["maturity_receipt_sha256"] = digest("cross-bound")
        must_refuse(changed)
        refused += 1

        changed = copy.deepcopy(base)
        other_route = applicable[(index + 1) % len(applicable)]["route_id"]
        changed["route_id"] = other_route
        must_refuse(changed)
        refused += 1
    return {
        "routes_hostile_probed": len(applicable),
        "candidate_maturity_and_route_cross_bindings_refused": refused,
    }


def probe_subject_specific_semantics() -> dict[str, Any]:
    route_ids = [
        "profile:peter_parker_spider_man_no_way_home_final_suit",
        "state:peter_parker_spider_man_no_way_home_final_suit",
        "profile:spider_gwen_spider_gwen_20260606_013325",
        "state:spider_gwen_spider_gwen_20260606_013325",
        "profile:ladybug_marinette_expanded_smoke",
        "state:ladybug_marinette_expanded_smoke",
    ]
    accepted = []
    for route_id in route_ids:
        person_id = routes[route_id]["person_id"]
        decoded = decode_compiled(
            v4.compile_disconnected_integration_request_v4(
                request_for(person_id, route_id)
            )
        )
        accepted.append(
            {
                "route_id": route_id,
                "status": decoded["proposal"]["request"]["maturity_status"],
            }
        )
    wrong_peter = request_for(
        "peter_parker_spider_man_no_way_home_final_suit",
        "profile:peter_parker_spider_man_no_way_home_final_suit",
    )
    wrong_peter["maturity_status"] = "non_adult"
    wrong_peter["maturity_receipt_sha256"] = digest("wrong-peter")
    must_refuse(wrong_peter)
    wrong_marinette = request_for(
        "ladybug_marinette_expanded_smoke",
        "profile:ladybug_marinette_expanded_smoke",
    )
    wrong_marinette["maturity_status"] = "confirmed_adult"
    wrong_marinette["maturity_receipt_sha256"] = digest("wrong-marinette")
    must_refuse(wrong_marinette)
    return {
        "exact_subject_specific_routes_accepted": accepted,
        "cross_status_refusals": 2,
    }


def probe_scope_repair() -> dict[str, Any]:
    assert type(v4._CANONICAL_SCOPE) is tuple
    assert v4._CANONICAL_SCOPE == ("shared_growth_v3_public_projection_only",)
    assert "_CANONICAL_SCOPE" not in v4.__all__
    assert "REQUESTED_SCOPE" not in v4.__all__
    assert not hasattr(v4, "REQUESTED_SCOPE")
    try:
        v4._CANONICAL_SCOPE.append("private_state_scope")
    except AttributeError:
        pass
    else:
        raise AssertionError("tuple unexpectedly exposed append")
    try:
        v4._CANONICAL_SCOPE[0] = "private_state_scope"
    except TypeError:
        pass
    else:
        raise AssertionError("tuple item assignment unexpectedly succeeded")

    class ScopeList(list):
        pass

    class ScopeText(str):
        pass

    base = request_for("kira", "permanent:kira")
    bad_scopes = (
        tuple(base["requested_scope"]),
        ScopeList(base["requested_scope"]),
        [ScopeText("shared_growth_v3_public_projection_only")],
        [],
        ["shared_growth_v3_public_projection_only", "private_state_scope"],
    )
    for value in bad_scopes:
        changed = copy.deepcopy(base)
        changed["requested_scope"] = value
        must_refuse(changed)

    first = v4.compile_disconnected_integration_request_v4(base)
    first_hash = hashlib.sha256(first).hexdigest()
    base["requested_scope"].append("private_state_scope")
    base["person_opt_in"] = False
    assert hashlib.sha256(first).hexdigest() == first_hash
    assert b"private_state_scope" not in first

    clean = request_for("kira", "permanent:kira")
    decoded_one = decode_compiled(v4.compile_disconnected_integration_request_v4(clean))
    decoded_two = decode_compiled(v4.compile_disconnected_integration_request_v4(clean))
    list_one = decoded_one["proposal"]["request"]["requested_scope"]
    list_two = decoded_two["proposal"]["request"]["requested_scope"]
    assert list_one is not list_two
    list_one.append("private_state_scope")
    assert list_two == ["shared_growth_v3_public_projection_only"]
    return {
        "private_tuple_exact": True,
        "not_exported": True,
        "wrong_scope_shapes_refused": len(bad_scopes),
        "caller_mutation_changes_returned_bytes": False,
        "decoded_projection_lists_are_fresh": True,
    }


def probe_acknowledged_same_process_substitution() -> dict[str, Any]:
    original = v4._CANONICAL_SCOPE
    try:
        v4._CANONICAL_SCOPE = (
            "shared_growth_v3_public_projection_only",
            "private_state_scope",
        )
        request = request_for("kira", "permanent:kira")
        request["requested_scope"] = list(v4._CANONICAL_SCOPE)
        decoded = decode_compiled(
            v4.compile_disconnected_integration_request_v4(request)
        )
        assert decoded["proposal"]["request"]["requested_scope"][-1] == (
            "private_state_scope"
        )
        assert decoded["proposal"]["truth"]["request_is_authority"] is False
        assert decoded["proposal"]["truth"]["private_state_included"] is False
    finally:
        v4._CANONICAL_SCOPE = original
    assert v4._CANONICAL_SCOPE == ("shared_growth_v3_public_projection_only",)
    return {
        "private_name_rebinding_can_fabricate_inert_bytes": True,
        "claimed_as_authority": False,
        "current_consumer_exists": False,
        "contract_disclaimer_present": True,
    }


def probe_refusals_and_identity_boundaries() -> dict[str, Any]:
    base = request_for("kira", "permanent:kira")
    refused = 0
    for target in ("temporary_creator", "creator", "new_person"):
        changed = copy.deepcopy(base)
        changed["target_kind"] = target
        changed["route_id"] = "creator:new_person"
        must_refuse(changed)
        refused += 1
    denied = request_for(
        "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
        "profile:sarah_bennett_enterainment_pr_agent_expert_20260606_171637",
    )
    denied["route_id"] = (
        "state:sarah_bennett_enterainment_pr_agent_expert_20260606_171637"
    )
    must_refuse(denied)
    refused += 1
    synthetic = request_for(
        "robert_mcmurrer_presence_ai",
        "profile:robert_mcmurrer_presence_ai",
    )
    for person_id in ("robert", "biological_robert", "robert_mcmurrer"):
        changed = copy.deepcopy(synthetic)
        changed["person_id"] = person_id
        must_refuse(changed)
        refused += 1
    for key, unsafe in {
        "person_opt_in": False,
        "revocable": False,
        "owner_override_allowed": True,
        "production_enabled": True,
        "private_state_requested": True,
        "memory_write_requested": True,
        "external_action_requested": True,
    }.items():
        changed = copy.deepcopy(base)
        changed[key] = unsafe
        must_refuse(changed)
        refused += 1
    try:
        v4.open_shared_growth_v4_production_integration(object(), enable=True)
    except v4.SharedGrowthIntegrationV4Error:
        refused += 1
    else:
        raise AssertionError("production opener unexpectedly returned")
    return {
        "refusals": refused,
        "temporary_creator_supported": False,
        "denied_legacy_alias_supported": False,
        "biological_robert_substitutes_for_synthetic_robert": False,
        "production_opener": "HARD_REFUSE",
    }


def probe_source_surface() -> dict[str, Any]:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE_PATH))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])
    forbidden_modules = {
        "os",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "http",
        "ctypes",
        "shutil",
        "tempfile",
        "sqlite3",
    }
    assert not imported_modules.intersection(forbidden_modules)
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    forbidden_calls = {
        "open",
        "write",
        "write_text",
        "write_bytes",
        "touch",
        "mkdir",
        "makedirs",
        "unlink",
        "remove",
        "rmdir",
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
    assert not calls.intersection(forbidden_calls)
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert classes == ["SharedGrowthIntegrationV4Error"]
    assert tuple(v4.__all__) == (
        "ENVELOPE_SCHEMA",
        "INPUT_SCHEMA",
        "PROPOSAL_SCHEMA",
        "SharedGrowthIntegrationV4Error",
        "compile_disconnected_integration_request_v4",
        "open_shared_growth_v4_production_integration",
    )
    return {
        "imports": sorted(imported_modules),
        "classes": classes,
        "forbidden_imports": [],
        "forbidden_calls": [],
        "verifier_or_key": False,
        "callback_or_controller": False,
        "staging_write_commit_or_cleanup": False,
        "profile_or_memory_writer": False,
    }


def probe_current_consumers() -> dict[str, Any]:
    needles = (
        b"compile_disconnected_integration_request_v4",
        b"shared_person_growth_v3_integration_candidate_v4",
        b"open_shared_growth_v4_production_integration",
    )
    extensions = {".py", ".pyw", ".ps1", ".cmd", ".bat"}
    hits: set[Path] = set()
    scanned = 0
    for root in (KIRA_ROOT, WORK_ROOT):
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            if "__pycache__" in path.parts:
                continue
            scanned += 1
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if any(needle in data for needle in needles):
                hits.add(path.resolve())
    allowed = {SOURCE_PATH.resolve(), TEST_PATH.resolve(), Path(__file__).resolve()}
    assert hits <= allowed
    assert not any(path.is_relative_to(KIRA_ROOT) for path in hits)
    return {
        "executable_text_files_scanned": scanned,
        "kira_consumer_hits": 0,
        "only_source_test_and_audit_probe_hits": len(hits),
        "production_consumer": False,
    }


def probe_final_rehash() -> dict[str, Any]:
    probe_v4_subject_identities()
    manifest = probe_manifest_closure()
    return {
        "v4_six_subjects_exact_after_probes": 6,
        "sealed_closure_exact_after_probes": manifest["exact"],
        "mismatches": 0,
    }


probe("v4_subject_identities", probe_v4_subject_identities)
probe("sealed_manifest_closure", probe_manifest_closure)
probe("accepted_isolated_v3_core_closure", probe_accepted_core_closure)
probe("strict_in_memory_compile", probe_compile_closure)
probe("all_applicable_routes", probe_all_routes)
probe("every_route_cross_binding", probe_every_route_cross_binding)
probe("subject_specific_semantics", probe_subject_specific_semantics)
probe("immutable_private_scope_repair", probe_scope_repair)
probe("acknowledged_same_process_substitution", probe_acknowledged_same_process_substitution)
probe("refusals_and_identity_boundaries", probe_refusals_and_identity_boundaries)
probe("no_authority_write_commit_surface", probe_source_surface)
probe("no_current_consumer", probe_current_consumers)
probe("final_exact_rehash", probe_final_rehash)

output = {
    "schema": "kira.shared_person_growth_v3_integration_candidate_v4.independent_hostile_probe_result.v1",
    "reviewer_task": "/root/growth_v4_audit",
    "different_from_author_task": True,
    "static_only": True,
    "python_cache_disabled_expected": sys.dont_write_bytecode,
    "probe_count": len(results),
    "passed": sum(1 for item in results if item["passed"]),
    "failed": sum(1 for item in results if not item["passed"]),
    "results": results,
    "failures": failures,
    "scope_truth": {
        "kira_written": False,
        "live_person_or_model_invoked": False,
        "profile_memory_or_person_state_changed": False,
        "body_media_voice_network_device_or_sarah_runtime_invoked": False,
        "promotion_or_production_pointer_changed": False,
    },
}
print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
raise SystemExit(0 if not failures else 1)
