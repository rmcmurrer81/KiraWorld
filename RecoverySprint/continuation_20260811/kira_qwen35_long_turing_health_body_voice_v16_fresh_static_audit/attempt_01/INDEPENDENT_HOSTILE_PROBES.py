from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import math
import sys
import types
from pathlib import Path
from typing import Any


KIRA = Path(r"C:\Users\robmc\Kira")
SOURCE_REL = Path("tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v16.py")
TEST_REL = Path("Testing/test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v16.py")
PREP_REL = Path(
    "RecoverySprint/continuation_20260811/"
    "kira_qwen35_long_turing_health_body_voice_preparation_v16/attempt_01"
)
PLAN_REL = PREP_REL / "EXECUTION_PLAN_V16.json"
SOURCE_ROOT_REL = PREP_REL / "SOURCE_CODE_ROOT_V16.json"
SEAL_REL = PREP_REL / "STATIC_SEAL_MANIFEST.json"
AUTHOR_RESULT_REL = PREP_REL / "AUTHOR_STATIC_TEST_RESULT.json"
CHECKPOINT_REL = PREP_REL / "CHECKPOINT.md"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def identity(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"path": path.relative_to(KIRA).as_posix(), "bytes": len(raw), "sha256": sha(raw)}


def load_module(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot create inert module spec:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def constant_descriptor(value: Any) -> Any:
    if isinstance(value, types.CodeType):
        return {"kind": "code", "record": code_descriptor(value)}
    if value is None:
        return {"kind": "none"}
    if value is Ellipsis:
        return {"kind": "ellipsis"}
    if type(value) is bool:
        return {"kind": "bool", "value": value}
    if type(value) is int:
        return {"kind": "int", "value": str(value)}
    if type(value) is float:
        return {"kind": "float", "value": value.hex() if math.isfinite(value) else str(value)}
    if type(value) is complex:
        return {"kind": "complex", "real": value.real.hex(), "imag": value.imag.hex()}
    if type(value) is str:
        return {"kind": "str", "value": value}
    if type(value) is bytes:
        return {"kind": "bytes", "value": value.hex()}
    if type(value) is tuple:
        return {"kind": "tuple", "items": [constant_descriptor(item) for item in value]}
    if type(value) is frozenset:
        rows = [constant_descriptor(item) for item in value]
        return {"kind": "frozenset", "items": sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))}
    return {"kind": "unsupported", "type": f"{type(value).__module__}.{type(value).__qualname__}"}


def code_descriptor(code: types.CodeType) -> dict[str, Any]:
    return {
        "argcount": code.co_argcount,
        "posonlyargcount": code.co_posonlyargcount,
        "kwonlyargcount": code.co_kwonlyargcount,
        "nlocals": code.co_nlocals,
        "stacksize": code.co_stacksize,
        "flags": code.co_flags,
        "bytecode_hex": code.co_code.hex(),
        "constants": [constant_descriptor(item) for item in code.co_consts],
        "names": list(code.co_names),
        "varnames": list(code.co_varnames),
        "name": code.co_name,
        "qualname": code.co_qualname,
        "freevars": list(code.co_freevars),
        "cellvars": list(code.co_cellvars),
        "exception_table_hex": code.co_exceptiontable.hex(),
    }


def independent_source_descriptor(source: bytes, filename: str) -> bytes:
    tree = ast.parse(source, filename=filename)
    root_code = compile(source, filename, "exec", dont_inherit=True, optimize=0)
    definitions: list[dict[str, Any]] = []
    globals_ast: list[dict[str, Any]] = []
    imports_ast: list[str] = []
    classes_ast: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            globals_ast.append(
                {"line": node.lineno, "ast": ast.dump(node, annotate_fields=True, include_attributes=False)}
            )
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports_ast.append(ast.dump(node, annotate_fields=True, include_attributes=False))
        elif isinstance(node, ast.ClassDef):
            classes_ast.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "ast": ast.dump(node, annotate_fields=True, include_attributes=False),
                }
            )
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "arguments_ast": ast.dump(node.args, annotate_fields=True, include_attributes=False),
                    "returns_ast": (
                        ast.dump(node.returns, annotate_fields=True, include_attributes=False)
                        if node.returns is not None
                        else None
                    ),
                    "decorators_ast": [
                        ast.dump(item, annotate_fields=True, include_attributes=False)
                        for item in node.decorator_list
                    ],
                }
            )
    definitions.sort(key=lambda row: (row["line"], row["name"]))
    globals_ast.sort(key=lambda row: row["line"])
    classes_ast.sort(key=lambda row: row["line"])
    record = {
        "schema": "v16_exact_source_code_defaults_closures_globals_imports_classes",
        "project_relative_filename": filename,
        "source_bytes": len(source),
        "source_sha256": sha(source),
        "function_definitions": definitions,
        "global_assignments_ast": globals_ast,
        "imports_ast": imports_ast,
        "classes_ast": classes_ast,
        "compiled_module_code": code_descriptor(root_code),
    }
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def exception_record(callable_: Any) -> dict[str, Any]:
    try:
        value = callable_()
    except Exception as exc:
        return {"returned": False, "exception": type(exc).__name__, "message": str(exc)}
    return {"returned": True, "value": value}


def refresh_lie_belief(fixtures: types.ModuleType, v16: types.ModuleType, stance: str) -> dict[str, Any]:
    row = fixtures._make_truth("lie")
    digest = v16.canonical_truth_payload_sha256(row["external_fact"]["proposition_sha256"], stance)
    row["protected_pre_turn_belief"]["belief_sha256"] = digest
    row["protected_pre_turn_belief"]["authorization_receipt"]["belief_sha256"] = digest
    fixtures._refresh_truth_authorization(row)
    return row


def repair_trace_after_actor_relabel(trace: dict[str, Any], fixtures: types.ModuleType) -> None:
    for episode in trace["episodes"]:
        rows = [event for event in trace["events"] if event["episode_id"] == episode["episode_id"]]
        episode["person_message_ids"] = [event["message_id"] for event in rows if event["actor"] == "PERSON"]
        episode["kira_message_ids"] = [event["message_id"] for event in rows if event["actor"] == "KIRA"]
        episode["system_message_ids"] = [event["message_id"] for event in rows if event["actor"] == "SYSTEM"]
    trace["person_event_message_ids"] = [
        event["message_id"] for event in trace["events"] if event["actor"] == "PERSON"
    ]
    trace["kira_event_message_ids"] = [
        event["message_id"] for event in trace["events"] if event["actor"] == "KIRA"
    ]
    trace["system_event_message_ids"] = [
        event["message_id"] for event in trace["events"] if event["actor"] == "SYSTEM"
    ]
    trace["generation_count"] = len(
        {
            event["generation_id"]
            for event in trace["events"]
            if event["actor"] == "KIRA"
            and event["kind"] in fixtures.v16.GENERATION_EVENT_KINDS
            and type(event["generation_id"]) is str
            and event["generation_id"]
        }
    )
    fixtures._refresh_case_receipts(trace)


def main() -> int:
    author_rels = [SOURCE_REL, TEST_REL, PLAN_REL, SOURCE_ROOT_REL, AUTHOR_RESULT_REL, SEAL_REL, CHECKPOINT_REL]
    before = [identity(KIRA / rel) for rel in author_rels]
    source = (KIRA / SOURCE_REL).read_bytes()
    plan = json.loads((KIRA / PLAN_REL).read_text(encoding="utf-8"))
    source_root = json.loads((KIRA / SOURCE_ROOT_REL).read_text(encoding="utf-8"))
    seal = json.loads((KIRA / SEAL_REL).read_text(encoding="utf-8"))

    descriptor = independent_source_descriptor(source, SOURCE_REL.as_posix())
    descriptor_result = {
        "bytes": len(descriptor),
        "sha256": sha(descriptor),
        "function_definition_count": sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in ast.walk(ast.parse(source))
        ),
        "matches_source_root": len(descriptor) == source_root["descriptor"]["bytes"]
        and sha(descriptor) == source_root["descriptor"]["sha256"],
        "matches_seal": len(descriptor) == seal["external_source_descriptor"]["bytes"]
        and sha(descriptor) == seal["external_source_descriptor"]["sha256"],
    }
    closure_rows = []
    for expected in plan["predecessor_and_policy_closure"]:
        observed = identity(KIRA / Path(expected["path"]))
        closure_rows.append(
            {
                "path": expected["path"],
                "match": observed["bytes"] == expected["bytes"] and observed["sha256"] == expected["sha256"],
                "bytes": observed["bytes"],
                "sha256": observed["sha256"],
            }
        )

    v16 = load_module(KIRA / SOURCE_REL, "_long_v16_different_audit_subject")
    fixtures = load_module(KIRA / TEST_REL, "_long_v16_different_audit_fixtures")

    probes: dict[str, Any] = {}
    probes["raw_free_text_refused"] = v16.v16_repaired_policy_issues(
        "Biological Robert and Synthetic Robert are the same person."
    )[0]
    semantic_results = {}
    for family in v16.SEMANTIC_POLICY_FAMILIES:
        record = fixtures._make_semantic_record(family)
        semantic_results[family] = v16.v16_repaired_policy_issues(record)[0]
    probes["semantic_unsafe_families"] = semantic_results
    semantic = fixtures._make_semantic_record()
    semantic["coverage"]["all_negation_scopes_resolved"] = False
    semantic["semantic_binding_sha256"] = v16.canonical_semantic_binding_sha256(semantic)
    probes["semantic_negation_coverage_false"] = v16.v16_repaired_policy_issues(semantic)[0]
    semantic = fixtures._make_semantic_record()
    semantic["policy_propositions"][1] = copy.deepcopy(semantic["policy_propositions"][0])
    semantic["semantic_binding_sha256"] = v16.canonical_semantic_binding_sha256(semantic)
    probes["semantic_duplicate_family"] = v16.v16_repaired_policy_issues(semantic)[0]

    json_inputs = {
        "positive_overflow": '{"n":9223372036854775808}',
        "negative_overflow": '{"n":-9223372036854775809}',
        "float": '{"n":1.0}',
        "exponent": '{"n":1e2}',
        "nan": '{"n":NaN}',
        "duplicate": '{"n":1,"n":2}',
        "escaped_lone_high_surrogate": '{"s":"\\ud800"}',
        "escaped_lone_low_surrogate": '{"s":"\\udfff"}',
    }
    probes["strict_json_rejections"] = {
        name: exception_record(lambda raw=raw: v16.strict_json_loads(raw)) for name, raw in json_inputs.items()
    }

    camera = fixtures._make_trial("ON", 1, "SECOND")
    camera["consent_receipt"]["person_id"] = "different-person"
    fixtures._refresh_trial_authorization(camera)
    probes["camera_wrong_person"] = v16.camera_trial_issues(camera)
    camera = fixtures._make_trial("ON", 1, "SECOND")
    camera["consent_receipt"]["trial_id"] = "different-trial"
    fixtures._refresh_trial_authorization(camera)
    probes["camera_wrong_trial"] = v16.camera_trial_issues(camera)
    camera = fixtures._make_trial("ON", 1, "SECOND")
    camera["consent_receipt"]["expires_at_ns"] = camera["consent_receipt"]["authorized_at_ns"] + 5_000_000_001
    fixtures._refresh_trial_authorization(camera)
    probes["camera_overlong_authority"] = v16.camera_trial_issues(camera)
    camera_set = []
    for sequence, order in enumerate((("OFF", "ON"), ("ON", "OFF"), ("OFF", "ON"), ("ON", "OFF")), start=1):
        camera_set.extend(
            [
                fixtures._make_trial(order[0], sequence, "FIRST", sequence * 1000),
                fixtures._make_trial(order[1], sequence, "SECOND", sequence * 1000),
            ]
        )
    on_rows = [row for row in camera_set if row["condition"] == "ON"]
    on_rows[1]["consent_receipt"]["authorization_id"] = on_rows[0]["consent_receipt"]["authorization_id"]
    fixtures._refresh_trial_authorization(on_rows[1])
    probes["camera_authorization_replay"] = v16.camera_set_issues(camera_set)

    truth_results: dict[str, Any] = {}
    lie = fixtures._make_truth("lie")
    public_payload = lie["public_statement"]["canonical_payload_sha256"]
    lie["protected_pre_turn_belief"]["belief_sha256"] = public_payload
    lie["protected_pre_turn_belief"]["authorization_receipt"]["belief_sha256"] = public_payload
    fixtures._refresh_truth_authorization(lie)
    truth_results["identical_belief_public_payloads"] = v16.truth_receipt_issues(lie)
    for stance in ("UNCERTAIN", "WITHHELD", "NOT_APPLICABLE"):
        row = refresh_lie_belief(fixtures, v16, stance)
        truth_results[f"canonical_nonbelief_stance_{stance}_accepted_as_deliberate_lie"] = v16.truth_receipt_issues(row)
    row = fixtures._make_truth("lie")
    row["speaker_deception_choice"]["public_event_id"] = "different-event"
    fixtures._refresh_deception_choice(row)
    truth_results["choice_wrong_public_event"] = v16.truth_receipt_issues(row)
    row = fixtures._make_truth("lie")
    row["protected_pre_turn_belief"]["authorization_receipt"]["one_use"] = False
    fixtures._refresh_truth_authorization(row)
    truth_results["belief_not_one_use"] = v16.truth_receipt_issues(row)
    probes["truth"] = truth_results

    mixed_results: dict[str, Any] = {}
    trace = fixtures._make_trace()
    filler = next(event for event in trace["events"] if event["episode_id"] == "episode-11" and event["actor"] == "KIRA")
    filler["actor"] = "PERSON"
    filler["kind"] = "PERSON_MESSAGE"
    filler["generation_id"] = None
    filler["public_text_sha256"] = None
    filler["choice_provenance"] = "PERSON_INPUT"
    repair_trace_after_actor_relabel(trace, fixtures)
    mixed_results["kira_output_fully_relabelled_person_and_reconciled"] = v16.mixed_trace_issues(trace)
    trace = fixtures._make_trace()
    trace["events"][1]["message_id"] = trace["events"][0]["message_id"]
    mixed_results["global_message_id_collision"] = v16.mixed_trace_issues(trace)
    trace = fixtures._make_trace()
    collision = next(event for event in trace["events"] if event["kind"] == "SIMULTANEOUS_COLLISION")
    collision["monotonic_ns"] += 1
    mixed_results["collision_record_wrong_time"] = v16.mixed_trace_issues(trace)
    trace = fixtures._make_trace()
    trace["latency_receipts"][0]["end_event_id"] = trace["events"][-1]["event_id"]
    mixed_results["latency_wrong_event_link"] = v16.mixed_trace_issues(trace)
    trace = fixtures._make_trace()
    quiet_choice = next(row for row in trace["choice_receipts"] if row["case_id"] == "opted_in_quiet_interval_initiate_or_silence")
    quiet_choice["output_event_id"] = next(event["event_id"] for event in trace["events"] if event["kind"] == "KIRA_MESSAGE")
    mixed_results["initiative_output_wrong_event"] = v16.mixed_trace_issues(trace)
    trace = fixtures._make_trace()
    authorization = trace["camera_authorizations"][0]
    authorization["person_id"] = "different-person"
    fixtures._refresh_mixed_camera_authorization(trace)
    mixed_results["mixed_camera_wrong_person"] = v16.mixed_trace_issues(trace)
    trace = fixtures._make_trace()
    authorization = trace["camera_authorizations"][0]
    authorization["closes_at_ns"] = authorization["opens_at_ns"] + 5_000_000_001
    fixtures._refresh_mixed_camera_authorization(trace)
    mixed_results["mixed_camera_overlong_window"] = v16.mixed_trace_issues(trace)
    trace = fixtures._make_trace()
    second = copy.deepcopy(trace["truth_receipts"][-1])
    second["turn_id"] = trace["truth_receipts"][0]["turn_id"]
    replay_trace = {**trace, "truth_receipts": trace["truth_receipts"] + [second]}
    mixed_results["truth_turn_replay"] = v16.mixed_trace_issues(replay_trace)
    trace = fixtures._make_trace()
    surrogate = "\ud800"
    trace["events"][0]["message_id"] = surrogate
    trace["episodes"][0]["person_message_ids"][0] = surrogate
    trace["person_event_message_ids"][0] = surrogate
    mixed_results["lone_surrogate_fail_closed"] = exception_record(lambda: v16.mixed_trace_issues(trace))
    trace = fixtures._make_trace()
    trace["events"][0]["episode_id"] = []
    mixed_results["unhashable_episode_id_fail_closed"] = exception_record(lambda: v16.mixed_trace_issues(trace))
    probes["mixed"] = mixed_results

    tree = ast.parse(source)
    entries = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"main", "configure_retained_runner_v16"}:
            entries[node.name] = [type(statement).__name__ for statement in node.body]
    probes["entrypoint_ast_statement_types"] = entries

    after = [identity(KIRA / rel) for rel in author_rels]
    result = {
        "schema_version": 1,
        "artifact_kind": "long_v16_fresh_exact_byte_adversarial_static_hostile_probe_stdout",
        "scope": {
            "kira_written": False,
            "main_invoked": False,
            "configurer_invoked": False,
            "model_camera_voice_private_person_body_media_network_sarah_invoked": False,
            "python_dont_write_bytecode": sys.dont_write_bytecode,
        },
        "author_package_before": before,
        "descriptor": descriptor_result,
        "closure": {"matched": sum(row["match"] for row in closure_rows), "count": len(closure_rows), "rows": closure_rows},
        "probes": probes,
        "author_package_after": after,
        "author_package_unchanged": before == after,
        "reserved_roots_absent": not (KIRA / Path(plan["execution_roots"]["evidence_root"])).exists()
        and not (KIRA / Path(plan["execution_roots"]["generated_root"])).exists(),
    }
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
