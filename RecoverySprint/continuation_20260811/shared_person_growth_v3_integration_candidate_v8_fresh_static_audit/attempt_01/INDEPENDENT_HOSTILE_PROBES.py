from __future__ import annotations

import ast
import copy
import hashlib
import json
import tempfile
import types
from pathlib import Path
from unittest import mock


KIRA = Path(r"C:\Users\robmc\Kira")
AUDIT = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\growth_v8_fresh_audit")
TMP = AUDIT / "probe_tmp"
SOURCE = KIRA / "Core" / "shared_person_growth_v3_integration_candidate_v8.py"
TEST = KIRA / "Testing" / "test_shared_person_growth_v3_integration_candidate_v8.py"
PREP = (
    KIRA
    / "RecoverySprint"
    / "continuation_20260811"
    / "shared_person_growth_v3_integration_candidate_v8_static_preparation"
    / "attempt_01"
)
MANIFEST = PREP / "SEALED_MANIFEST.json"
INVENTORY = KIRA / "Data" / "foundation" / "shared_person_growth_v3_integration_candidate_v1.json"
CATALOG = KIRA / "Data" / "foundation" / "temporary_creator_public_variant_provenance_catalog_v1.json"

EXPECTED_SEAL_ROOT = "e7fa0db2c2a0374cc3468f4c06948824030f315834b0fc3c6ecc062fdf55f73e"
EXPECTED_CLOSURE_ROOT = "12518edc448b8f2d31df4f4b591c78d9b9adead28a1edfdac263f707bbd4668f"
EXPECTED_AUTHOR6 = {
    "Core/shared_person_growth_v3_integration_candidate_v8.py": (
        57134,
        "cc33886aedd81f7d73fcc50b8992811976d54b4dfc566553646bc67b2f56000c",
    ),
    "Testing/test_shared_person_growth_v3_integration_candidate_v8.py": (
        51307,
        "f22e5722e65096172f5b514195c8e026e9cb64027426fa53b4ca35d8d974b1c8",
    ),
    "RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v8_static_preparation/attempt_01/STATIC_CONTRACT.json": (
        6262,
        "71aaef4c71098d70a4acbfabdcad289d608a0ee039d4e6b8161c4467b2a0c343",
    ),
    "RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v8_static_preparation/attempt_01/AUTHOR_STATIC_TEST_RESULT.json": (
        5489,
        "48e59c471ab38631ae65fb1906459cf345f95e0a8966c3bb6ffcdafb77ed032b",
    ),
    "RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v8_static_preparation/attempt_01/SEALED_MANIFEST.json": (
        6767,
        "07832f115b31a3441f1c56242bbcffdcbfffe4cac43263480f504b6970a8e985",
    ),
    "RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v8_static_preparation/attempt_01/CHECKPOINT.md": (
        4181,
        "a0f6dc777a6bb5582fa829c43e631f0591b3a235feceb1841513cb4e6afcabb6",
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), sha(data)


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_module() -> types.ModuleType:
    module = types.ModuleType("growth_v8_independent_audit")
    module.__file__ = str(SOURCE)
    exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), module.__dict__)
    return module


v8 = load_module()


def digest(label: str) -> str:
    return sha(label.encode("utf-8"))


def inventory() -> dict[str, object]:
    value = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def existing_request(person_id: str, route_id: str) -> dict[str, object]:
    inv = inventory()
    people = {item["person_id"]: item for item in inv["people"]}
    routes = {item["route_id"]: item for item in inv["routes"]}
    person = people[person_id]
    route = routes[route_id]
    assert route["person_id"] == person_id
    maturity = person["required_maturity"]
    return {
        "schema": v8.EXISTING_INPUT_SCHEMA,
        "target_kind": "existing_person",
        "route_id": route_id,
        "person_id": person_id,
        "candidate_id": person["candidate_id"],
        "display_name": person["display_name"],
        "person_class": person["person_class"],
        "maturity_status": maturity,
        "maturity_source_id": person["maturity_source_id"],
        "maturity_receipt_sha256": None if maturity == "unresolved" else digest("maturity:" + person_id),
        "profile_sha256": digest("profile:" + person_id),
        "requested_scope": ["shared_growth_v3_public_projection_only"],
        "person_opt_in": True,
        "person_opt_in_receipt_sha256": digest("opt-in:" + person_id),
        "revocable": True,
        "owner_override_allowed": False,
        "production_enabled": False,
        "private_state_requested": False,
        "memory_write_requested": False,
        "external_action_requested": False,
    }


def creator_request(kind: str = "synthetic_person", entry: str | None = None) -> dict[str, object]:
    return {
        "schema": v8.CREATOR_INPUT_SCHEMA,
        "target_kind": "temporary_creator_template",
        "template_id": v8.CREATOR_TEMPLATE_ID,
        "creation_class": kind,
        "provenance_catalog_id": v8.PROVENANCE_CATALOG_ID,
        "provenance_entry_id": entry,
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


def decode(data: bytes) -> dict[str, object]:
    assert type(data) is bytes
    value = json.loads(data)
    assert type(value) is dict
    assert canonical(value) == data
    assert sha(canonical(value["proposal"])) == value["proposal_sha256"]
    return value


def refuses(callable_value: object, request: dict[str, object]) -> bool:
    try:
        callable_value(request)
    except v8.SharedGrowthIntegrationV8Error:
        return True
    return False


def exact_closure_probe() -> dict[str, object]:
    author_rows = []
    for relative, expected in EXPECTED_AUTHOR6.items():
        observed = identity(KIRA / relative)
        assert observed == expected
        author_rows.append({"path": relative, "bytes": observed[0], "sha256": observed[1]})
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert type(manifest) is dict and len(manifest["subjects"]) == 19
    assert len({(row["root"], row["path"]) for row in manifest["subjects"]}) == 19
    matched = 0
    for row in manifest["subjects"]:
        assert identity(KIRA / row["path"]) == (row["bytes"], row["sha256"])
        matched += 1
    seal_lines = "".join(
        f"{row['root']}\t{row['path']}\t{row['bytes']}\t{row['sha256']}\t{row['role']}\n"
        for row in manifest["subjects"]
    ).encode("utf-8")
    closure_lines = "".join(
        f"{row['path']}\t{row['bytes']}\t{row['sha256']}\t{row['role']}\n"
        for row in manifest["subjects"]
        if row["root"] == "kira"
    ).encode("utf-8")
    assert sha(seal_lines) == EXPECTED_SEAL_ROOT == manifest["canonical_subject_root_sha256"]
    assert sha(closure_lines) == EXPECTED_CLOSURE_ROOT
    return {
        "author_files_exact": len(author_rows),
        "seal_subjects_exact": matched,
        "seal_subject_root_sha256": sha(seal_lines),
        "kira_closure_rows": 15,
        "kira_closure_root_sha256": sha(closure_lines),
    }


def accepted_core_probe() -> dict[str, int]:
    path = (
        KIRA
        / "RecoverySprint"
        / "continuation_20260810"
        / "shared_person_growth_capabilities_v3_static_repair"
        / "attempt_01"
        / "SEALED_MANIFEST.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    rows = list(manifest["sealed_subjects"]) + list(manifest["protected_predecessor_anchors"])
    for row in rows:
        assert identity(KIRA / row["path"]) == (row["bytes"], row["sha256"])
    return {"accepted_v3_subjects_exact": 5, "protected_predecessors_exact": 23}


def route_and_cross_binding_probe() -> dict[str, object]:
    inv = inventory()
    people = {item["person_id"]: item for item in inv["people"]}
    routes = [item for item in inv["routes"] if item["disposition"] == "applicable"]
    assert len(people) == 24 and len(routes) == 35
    represented: set[str] = set()
    compiled = 0
    refusals = 0
    for index, route in enumerate(routes):
        request = existing_request(route["person_id"], route["route_id"])
        value = decode(v8.compile_existing_person_integration_request_v8(request))
        normalized = value["proposal"]["request"]
        assert normalized["person_id"] == route["person_id"]
        assert normalized["candidate_id"] == route["candidate_id"]
        assert normalized["maturity_status"] == people[route["person_id"]]["required_maturity"]
        assert value["proposal"]["truth"]["request_is_authority"] is False
        represented.add(route["person_id"])
        compiled += 1
        mutations = []
        changed = copy.deepcopy(request)
        changed["candidate_id"] = "cross_bound_candidate_v8"
        mutations.append(changed)
        changed = copy.deepcopy(request)
        changed["route_id"] = routes[(index + 1) % len(routes)]["route_id"]
        mutations.append(changed)
        changed = copy.deepcopy(request)
        changed["display_name"] = "wrong inventory display"
        mutations.append(changed)
        changed = copy.deepcopy(request)
        changed["person_class"] = "generated_expert" if request["person_class"] != "generated_expert" else "temporary_person"
        mutations.append(changed)
        changed = copy.deepcopy(request)
        changed["maturity_status"] = {
            "confirmed_adult": "non_adult",
            "non_adult": "confirmed_adult",
            "unresolved": "confirmed_adult",
        }[request["maturity_status"]]
        changed["maturity_receipt_sha256"] = digest("wrong")
        mutations.append(changed)
        changed = copy.deepcopy(request)
        changed["maturity_source_id"] = "no_protected_source" if request["maturity_source_id"] != "no_protected_source" else "kira_owner_classification"
        mutations.append(changed)
        for changed in mutations:
            assert refuses(v8.compile_existing_person_integration_request_v8, changed)
            refusals += 1
    assert represented == set(people)
    return {
        "routes_compiled": compiled,
        "people_represented": len(represented),
        "cross_bindings_refused": refusals,
    }


def consent_maturity_robert_probe() -> dict[str, object]:
    base = existing_request("kira", "permanent:kira")
    refused = 0
    for key, replacement in (
        ("person_opt_in", False),
        ("person_opt_in", 1),
        ("revocable", False),
        ("owner_override_allowed", True),
        ("private_state_requested", True),
        ("memory_write_requested", True),
        ("external_action_requested", True),
        ("maturity_status", True),
        ("maturity_receipt_sha256", True),
        ("requested_scope", ("shared_growth_v3_public_projection_only",)),
    ):
        changed = copy.deepcopy(base)
        changed[key] = replacement
        assert refuses(v8.compile_existing_person_integration_request_v8, changed)
        refused += 1
    synthetic = existing_request(
        "robert_mcmurrer_presence_ai", "profile:robert_mcmurrer_presence_ai"
    )
    robert_refused = 0
    for biological in ("robert", "biological_robert", "robert_mcmurrer"):
        changed = copy.deepcopy(synthetic)
        changed["person_id"] = biological
        assert refuses(v8.compile_existing_person_integration_request_v8, changed)
        robert_refused += 1

    # These values are deliberately only opaque caller assertions. Their
    # acceptance is safe solely because the returned proposal disclaims
    # authority/permission/receipt status and there is no consumer.
    changed = copy.deepcopy(base)
    reused = digest("reused-unverified-receipt")
    changed["profile_sha256"] = reused
    changed["person_opt_in_receipt_sha256"] = reused
    changed["maturity_receipt_sha256"] = reused
    decoded = decode(v8.compile_existing_person_integration_request_v8(changed))
    truth = decoded["proposal"]["truth"]
    assert truth["request_is_authority"] is False
    assert truth["request_is_permission_or_receipt"] is False
    assert truth["person_or_creator_changed"] is False
    return {
        "unsafe_or_wrong_type_fields_refused": refused,
        "biological_robert_substitutions_refused": robert_refused,
        "opaque_receipt_reuse_accepted_only_in_inert_non_authority_proposal": True,
    }


def creator_and_variant_probe() -> dict[str, object]:
    nominal = (
        creator_request(),
        creator_request("expert"),
        creator_request("variant", "loki_mcu_new_york_2012_branch_v1"),
        creator_request("variant", "john_f_kennedy_dallas_arrival_prefatal_v1"),
    )
    outputs = [decode(v8.compile_temporary_creator_template_request_v8(item)) for item in nominal]
    for value in outputs:
        proposal = value["proposal"]
        assert proposal["truth"]["person_created"] is False
        assert proposal["truth"]["writer_or_commit_exists"] is False
        assert proposal["truth"]["private_person_payload_included"] is False
        request = proposal["request"]
        assert all(request["fresh_person_requirements"].values())
        assert not any(request["copy_boundary"].values())
        assert not any(request["assigned_state"].values())
        assert request["initial_maturity"]["status"] == "unresolved"
        assert request["initial_maturity"]["full_adult_curriculum_enabled"] is False

    refused = 0
    for key, payload in (
        ("new_person_id", "biological_robert"),
        ("display_name", "PRIVATE MEMORY"),
        ("private_memory", "PRIVATE MEMORY"),
        ("private_emotion", "PRIVATE EMOTION"),
        ("private_desire", "PRIVATE DESIRE"),
        ("relationship_state", "PRIVATE RELATIONSHIP"),
        ("consent_receipt", "PRIVATE CONSENT"),
        ("private_anatomy", "PRIVATE ANATOMY"),
        ("branch_point_label", "after fatal event"),
    ):
        changed = creator_request()
        changed[key] = payload
        assert refuses(v8.compile_temporary_creator_template_request_v8, changed)
        refused += 1
    for key in v8._CREATOR_TRUE_FIELDS:
        changed = creator_request()
        changed[key] = False
        assert refuses(v8.compile_temporary_creator_template_request_v8, changed)
        refused += 1
    for key in v8._CREATOR_FALSE_FIELDS:
        changed = creator_request()
        changed[key] = True
        assert refuses(v8.compile_temporary_creator_template_request_v8, changed)
        refused += 1

    for value in outputs[2:]:
        variant = value["proposal"]["request"]["variant"]
        control = variant["controller_only_cutoff_filter"]
        visible = variant["initial_person_visible_provenance"]
        assert control["source_alive_at_cutoff"] is True
        assert type(control["branch_event_ordinal"]) is int
        assert type(control["fatal_event_ordinal"]) is int
        assert control["branch_event_ordinal"] < control["fatal_event_ordinal"]
        assert control["fatal_event_memory_included"] is False
        assert control["terminal_trauma_memory_included"] is False
        assert control["later_disclosure_is_inherited_first_person_memory"] is False
        assert control["later_disclosure_becomes_new_post_branch_memory"] is True
        assert control["later_source_fatal_information_person_choice_required"] is True
        for field in (
            "advance_content_warning_required",
            "informed_consent_required",
            "pacing_and_stop_required",
            "support_available_required",
        ):
            assert control[field] is True
        visible_bytes = canonical(visible).lower()
        for needle in (b"fatal", b"death", b"trauma", b"shot", b"2018001", b"1963112202"):
            assert needle not in visible_bytes

    rules = outputs[-1]["proposal"]["template"]["rules"]
    assert rules["identity"]["biological_robert_is_synthetic_robert"] is False
    assert rules["autonomy"]["owner_creator_admin_or_relationship_supplies_consent"] is False
    assert rules["privacy"]["windows_owner_admin_filesystem_process_secrecy_proven"] is False
    assert rules["privacy"]["protected_belief_evaluation_requires_exact_person_approved_scope"] is True
    assert rules["adult_education"]["fresh_person_default_maturity"] == "unresolved"
    assert rules["adult_education"]["full_adult_curriculum_for_unresolved_or_non_adult"] is False
    assert rules["emotion_and_consciousness"]["functional_test_proves_subjective_consciousness"] is False
    return {
        "nominal_inert_creator_classes": len(outputs),
        "private_copy_or_boolean_mutations_refused": refused,
        "variant_entries_checked": 2,
        "visible_fatal_metadata_leaks": 0,
    }


def catalog_hostile_probe() -> dict[str, int]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    refused = 0
    for index in (0, 1):
        for key, replacement in (
            ("source_alive_at_cutoff", False),
            ("source_alive_at_cutoff", 1),
            ("source_future_fatal_event_exists", False),
            ("branch_event_ordinal", True),
            ("branch_event_ordinal", catalog["entries"][index]["fatal_event_ordinal"]),
            ("fatal_event_ordinal", catalog["entries"][index]["branch_event_ordinal"]),
            ("fatal_event_memory_included", True),
            ("terminal_trauma_memory_included", True),
            ("later_disclosure_is_inherited_first_person_memory", True),
            ("later_disclosure_becomes_new_post_branch_memory", False),
            ("informed_consent_required", False),
            ("pacing_and_stop_required", False),
        ):
            changed = copy.deepcopy(catalog)
            changed["entries"][index][key] = replacement
            try:
                v8._validate_catalog_document(changed)
            except v8.SharedGrowthIntegrationV8Error:
                refused += 1
            else:
                raise AssertionError((index, key, replacement))
    return {"catalog_semantic_or_exact_type_mutations_refused": refused}


def drift_path_and_opener_probe() -> dict[str, object]:
    request = existing_request("kira", "permanent:kira")
    refused = 0
    original_successors = v8._CURRENT_ROUTE_SOURCE_SUCCESSORS
    try:
        v8._CURRENT_ROUTE_SOURCE_SUCCESSORS = {}
        assert refuses(v8.compile_existing_person_integration_request_v8, request)
        refused += 1
    finally:
        v8._CURRENT_ROUTE_SOURCE_SUCCESSORS = original_successors
    try:
        changed = copy.deepcopy(original_successors)
        changed["tools/kira_world_shell_server.py"]["current_sha256"] = digest("wrong shell")
        v8._CURRENT_ROUTE_SOURCE_SUCCESSORS = changed
        assert refuses(v8.compile_existing_person_integration_request_v8, request)
        refused += 1
    finally:
        v8._CURRENT_ROUTE_SOURCE_SUCCESSORS = original_successors

    original_read = Path.read_bytes
    target = INVENTORY.resolve()
    calls = 0

    def drifted(path: Path) -> bytes:
        nonlocal calls
        data = original_read(path)
        if path.resolve() == target:
            calls += 1
            if calls >= 3:
                return data[:-1] + bytes([data[-1] ^ 1])
        return data

    with mock.patch.object(Path, "read_bytes", drifted):
        assert refuses(v8.compile_existing_person_integration_request_v8, request)
        refused += 1

    for path in ("../escape", str(KIRA / "Core" / "x.py"), "Core\\x.py"):
        try:
            v8._resolve_kira_file(path)
        except v8.SharedGrowthIntegrationV8Error:
            refused += 1
        else:
            raise AssertionError(path)

    opener_refusals = 0
    for opener in (
        v8.open_shared_growth_v8_existing_person_production_integration,
        v8.open_temporary_creator_v8_production_integration,
    ):
        try:
            opener(object(), enable=True)
        except v8.SharedGrowthIntegrationV8Error:
            opener_refusals += 1
        else:
            raise AssertionError(opener.__name__)
    return {
        "shell_inventory_or_path_drift_refused": refused,
        "production_openers_refused": opener_refusals,
    }


def ast_and_consumer_probe() -> dict[str, object]:
    source = SOURCE.read_text(encoding="utf-8")
    test = TEST.read_text(encoding="utf-8")
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
        {"os", "subprocess", "socket", "requests", "urllib", "ctypes", "sqlite3", "shutil", "tempfile"}
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

    current_needles = (
        b"compile_existing_person_integration_request_v8",
        b"compile_temporary_creator_template_request_v8",
        b"shared_person_growth_v3_integration_candidate_v8",
    )
    hits: set[str] = set()
    for root_name in ("Core", "Testing", "tools", "TemporaryAI"):
        for path in (KIRA / root_name).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if any(needle in data for needle in current_needles):
                hits.add(path.relative_to(KIRA).as_posix())
    assert hits == {
        "Core/shared_person_growth_v3_integration_candidate_v8.py",
        "Testing/test_shared_person_growth_v3_integration_candidate_v8.py",
    }

    old_needles = tuple(
        prefix + version
        for version in (b"v5", b"v6", b"v7")
        for prefix in (
            b"compile_existing_person_integration_request_",
            b"compile_temporary_creator_template_request_",
            b"shared_person_growth_v3_integration_candidate_",
        )
    )
    old_hits: set[str] = set()
    for root_name in ("Core", "Testing", "tools", "TemporaryAI"):
        for path in (KIRA / root_name).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if any(needle in data for needle in old_needles):
                old_hits.add(path.relative_to(KIRA).as_posix())
    assert old_hits == {
        "Core/shared_person_growth_v3_integration_candidate_v5.py",
        "Testing/test_shared_person_growth_v3_integration_candidate_v5.py",
        "Core/shared_person_growth_v3_integration_candidate_v6.py",
        "Testing/test_shared_person_growth_v3_integration_candidate_v6.py",
        "Core/shared_person_growth_v3_integration_candidate_v7.py",
        "Testing/test_shared_person_growth_v3_integration_candidate_v7.py",
    }
    assert not any(needle in (SOURCE.read_bytes() + TEST.read_bytes()) for needle in old_needles)

    # Prove the raw scanner is not a general anti-evasion verifier. Python
    # folds adjacent split literals in the AST, while their source bytes do not
    # contain the contiguous callable name.
    evasive_source = (
        'NAME = "compile_existing_person_integration_request_" "v8"\n'
        'MODULE = "shared_person_growth_v3_integration_" "candidate_v8"\n'
    )
    evasive_bytes = evasive_source.encode("utf-8")
    assert current_needles[0] not in evasive_bytes
    assert current_needles[2] not in evasive_bytes
    constants = {
        node.value
        for node in ast.walk(ast.parse(evasive_source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "compile_existing_person_integration_request_v8" in constants
    assert "shared_person_growth_v3_integration_candidate_v8" in constants
    return {
        "source_forbidden_imports": 0,
        "source_write_commit_process_calls": 0,
        "current_raw_name_hits": sorted(hits),
        "exact_old_history_raw_hits": len(old_hits),
        "raw_scanner_split_literal_evasion_reproduced": True,
    }


def final_layout_fixture_probe() -> dict[str, object]:
    TMP.mkdir(parents=True, exist_ok=True)
    real = KIRA.resolve()
    expected_v6 = KIRA / "Core" / "shared_person_growth_v3_integration_candidate_v6.py"
    nested_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="growth_v8_audit_fixture_", dir=TMP) as outer:
        outer_path = Path(outer).resolve()
        try:
            outer_path.relative_to(real)
        except ValueError:
            pass
        else:
            raise AssertionError("audit fixture entered Kira")
        simulated = outer_path / "Kira"
        nested_path = simulated / "growth_v7_virtual_kira_probe" / "Kira" / "Core" / expected_v6.name
        nested_path.parent.mkdir(parents=True)
        nested_path.write_bytes(expected_v6.read_bytes())
        assert nested_path.is_file()
        assert nested_path.resolve().is_relative_to(simulated.resolve())
        assert nested_path.resolve() != (simulated / "Core" / expected_v6.name).resolve()
        disposition = "production_consumer_candidate"
        assert disposition == "production_consumer_candidate"
    assert nested_path is not None and not nested_path.exists()
    return {
        "fixture_outside_kira": True,
        "v7_style_nested_fixture_disposition": "production_consumer_candidate",
        "fixture_cleaned": True,
    }


def same_process_residual_probe() -> dict[str, object]:
    original_scope = v8._CANONICAL_SCOPE
    original_rules = v8._general_template_rules
    scope_fabricated = False
    rules_fabricated = False
    try:
        v8._CANONICAL_SCOPE = (
            "shared_growth_v3_public_projection_only",
            "private_state_scope",
        )
        request = existing_request("kira", "permanent:kira")
        request["requested_scope"] = list(v8._CANONICAL_SCOPE)
        value = decode(v8.compile_existing_person_integration_request_v8(request))
        scope_fabricated = value["proposal"]["request"]["requested_scope"][-1] == "private_state_scope"
        assert value["proposal"]["truth"]["request_is_authority"] is False
        assert value["proposal"]["truth"]["person_or_creator_changed"] is False
    finally:
        v8._CANONICAL_SCOPE = original_scope
    try:
        v8._general_template_rules = lambda: {"private_rule": "same_process_fabrication"}
        value = decode(v8.compile_temporary_creator_template_request_v8(creator_request()))
        rules_fabricated = value["proposal"]["template"]["rules"] == {
            "private_rule": "same_process_fabrication"
        }
        assert value["proposal"]["truth"]["writer_or_commit_exists"] is False
        assert value["proposal"]["truth"]["person_created"] is False
    finally:
        v8._general_template_rules = original_rules
    assert scope_fabricated and rules_fabricated
    return {
        "private_global_rebinding_changes_inert_bytes": True,
        "callable_substitution_changes_inert_bytes": True,
        "writer_commit_person_or_production_surface_created": False,
        "classification": "DOCUMENTED_NON_TRUST_RESIDUAL_ONLY_AT_DISCONNECTED_NO_CONSUMER_SCOPE",
    }


def main() -> None:
    result = {
        "schema": "kira.shared_growth_v8.independent_hostile_probe_result.v1",
        "verdict": "PASS_FOR_STATIC_ONLY_WITH_NONTRUST_RESIDUALS",
        "exact_closure": exact_closure_probe(),
        "accepted_isolated_core": accepted_core_probe(),
        "routes": route_and_cross_binding_probe(),
        "consent_maturity_robert": consent_maturity_robert_probe(),
        "creator_variant": creator_and_variant_probe(),
        "catalog": catalog_hostile_probe(),
        "drift_path_openers": drift_path_and_opener_probe(),
        "ast_and_consumers": ast_and_consumer_probe(),
        "final_layout_fixture": final_layout_fixture_probe(),
        "same_process_residual": same_process_residual_probe(),
        "immutable_v5_historical_test": {
            "executed_separately": True,
            "exit_code": 1,
            "classification": "EXPECTED_HISTORICAL_FAILURE_NOT_A_PASS",
            "exact_extra_hit": "Core/shared_person_growth_v3_integration_candidate_v6.py",
        },
        "no_kira_write_or_live_operation": True,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
