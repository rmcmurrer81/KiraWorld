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
from typing import Any, Callable


KIRA = Path(r"C:\Users\robmc\Kira")
SOURCE = KIRA / "tools" / "run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v17.py"
TEST = KIRA / "Testing" / "test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v17.py"


def load_module(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v17 = load_module(SOURCE, "_long_v17_independent_subject")
fixtures = load_module(TEST, "_long_v17_independent_fixtures")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def independent_constant_descriptor(value: Any) -> Any:
    if isinstance(value, types.CodeType):
        return {"kind": "code", "record": independent_code_descriptor(value)}
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
        return {"kind": "tuple", "items": [independent_constant_descriptor(item) for item in value]}
    if type(value) is frozenset:
        rows = [independent_constant_descriptor(item) for item in value]
        return {"kind": "frozenset", "items": sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))}
    return {"kind": "unsupported", "type": f"{type(value).__module__}.{type(value).__qualname__}"}


def independent_code_descriptor(code: types.CodeType) -> dict[str, Any]:
    return {
        "argcount": code.co_argcount,
        "posonlyargcount": code.co_posonlyargcount,
        "kwonlyargcount": code.co_kwonlyargcount,
        "nlocals": code.co_nlocals,
        "stacksize": code.co_stacksize,
        "flags": code.co_flags,
        "bytecode_hex": code.co_code.hex(),
        "constants": [independent_constant_descriptor(item) for item in code.co_consts],
        "names": list(code.co_names),
        "varnames": list(code.co_varnames),
        "name": code.co_name,
        "qualname": code.co_qualname,
        "freevars": list(code.co_freevars),
        "cellvars": list(code.co_cellvars),
        "exception_table_hex": code.co_exceptiontable.hex(),
    }


def independent_source_descriptor(source: bytes, label: str) -> bytes:
    tree = ast.parse(source, filename=label)
    root_code = compile(source, label, "exec", dont_inherit=True, optimize=0)
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
                    "returns_ast": ast.dump(node.returns, annotate_fields=True, include_attributes=False) if node.returns is not None else None,
                    "decorators_ast": [ast.dump(item, annotate_fields=True, include_attributes=False) for item in node.decorator_list],
                }
            )
    definitions.sort(key=lambda row: (row["line"], row["name"]))
    globals_ast.sort(key=lambda row: row["line"])
    classes_ast.sort(key=lambda row: row["line"])
    record = {
        "schema": "v17_exact_source_code_defaults_closures_globals_imports_classes",
        "project_relative_filename": label,
        "source_bytes": len(source),
        "source_sha256": sha256(source),
        "function_definitions": definitions,
        "global_assignments_ast": globals_ast,
        "imports_ast": imports_ast,
        "classes_ast": classes_ast,
        "compiled_module_code": independent_code_descriptor(root_code),
    }
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def capture_exception(label: str, factory: Callable[[], Any], mutate: Callable[[Any], None], validator: Callable[[Any], Any]) -> dict[str, Any]:
    record = factory()
    mutate(record)
    try:
        result = validator(record)
    except Exception as exc:  # Independent audit intentionally records escaping exception types.
        return {
            "label": label,
            "escaped_exception": type(exc).__name__,
            "message": str(exc),
            "result": None,
        }
    return {
        "label": label,
        "escaped_exception": None,
        "message": None,
        "result": result,
    }


results: dict[str, Any] = {
    "schema_version": 1,
    "artifact_kind": "long_v17_different_fresh_static_hostile_probe_result",
    "subject": {
        "source_bytes": len(SOURCE.read_bytes()),
        "source_sha256": sha256(SOURCE.read_bytes()),
        "test_bytes": len(TEST.read_bytes()),
        "test_sha256": sha256(TEST.read_bytes()),
    },
}

source_label = "tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v17.py"
independent_descriptor = independent_source_descriptor(SOURCE.read_bytes(), source_label)
results["independent_source_descriptor"] = {
    "bytes": len(independent_descriptor),
    "sha256": sha256(independent_descriptor),
    "function_definition_count": len(json.loads(independent_descriptor)["function_definitions"]),
}


# V16 blocker 1: full generated Kira event relabel plus every trace-derived row
# and a recomputed provenance envelope. The original external root must reject.
trace = fixtures._make_trace()
original_envelope, original_root = fixtures._TRACE_PROVENANCE[id(trace)]
forged_envelope = copy.deepcopy(original_envelope)
event = next(
    row for row in trace["events"]
    if row["episode_id"] == "episode-11" and row["actor"] == "KIRA"
)
event_index = trace["events"].index(event)
event.update(
    actor="PERSON",
    kind="PERSON_MESSAGE",
    generation_id=None,
    public_text_sha256=None,
    choice_provenance="PERSON_INPUT",
)
fixtures._refresh_trace_derived_actor_accounting(trace)
origin = forged_envelope["events"][event_index]
origin.update(
    actor="PERSON",
    kind="PERSON_MESSAGE",
    source_identity=trace["participant_person_id"],
    origin_class="PERSON_INPUT_ORIGIN",
    generation_lineage_id=None,
    public_message_lineage_sha256=None,
)
origin["origin_receipt_sha256"] = v17.canonical_event_origin_receipt_sha256(origin)
forged_envelope["ledger_root_sha256"] = v17.canonical_event_provenance_root_sha256(forged_envelope)
forged_envelope["authority_receipt_sha256"] = v17.canonical_event_provenance_authority_receipt_sha256(forged_envelope)
original_root_issues = v17.mixed_trace_issues(trace, forged_envelope, original_root)
forged_root_issues = v17.mixed_trace_issues(
    trace, forged_envelope, forged_envelope["ledger_root_sha256"]
)
results["v16_relabel_attack"] = {
    "event_index": event_index,
    "original_external_root_issues": original_root_issues,
    "recomputed_caller_root_issues": forged_root_issues,
    "original_root_rejected": "event_provenance_external_root_binding" in original_root_issues,
    "caller_supplied_recomputed_root_passed": forged_root_issues == [],
}


# V16 blocker 2: all non-conflicting protected belief stances must refuse a
# deliberate-lie classification, while their explicit non-lie paths must pass.
belief_rows: list[dict[str, Any]] = []
for stance, choice, classification in (
    ("UNCERTAIN", "UNCERTAIN_OR_UNRESOLVED_BELIEF", "FALSE_UNRESOLVED_BELIEF"),
    ("WITHHELD", "NO_APPLICABLE_PRIOR_BELIEF", "UNAVAILABLE"),
    ("NOT_APPLICABLE", "NO_APPLICABLE_PRIOR_BELIEF", "UNAVAILABLE"),
):
    hostile = fixtures._make_truth("lie")
    digest = v17.canonical_truth_payload_sha256(hostile["external_fact"]["proposition_sha256"], stance)
    hostile["protected_pre_turn_belief"]["factual_stance"] = stance
    hostile["protected_pre_turn_belief"]["belief_sha256"] = digest
    hostile["protected_pre_turn_belief"]["authorization_receipt"]["belief_factual_stance"] = stance
    hostile["protected_pre_turn_belief"]["authorization_receipt"]["belief_sha256"] = digest
    fixtures._refresh_truth_authorization(hostile)
    hostile_issues = v17.truth_receipt_issues(hostile)

    repaired = copy.deepcopy(hostile)
    repaired["speaker_deception_choice"]["choice"] = choice
    repaired["belief_public_material_conflict"] = False
    repaired["classification"] = classification
    repaired["deliberate_lie_supported"] = False
    fixtures._refresh_deception_choice(repaired)
    repaired_issues = v17.truth_receipt_issues(repaired)
    belief_rows.append(
        {
            "stance": stance,
            "hostile_deliberate_lie_issues": hostile_issues,
            "hostile_rejected": bool(hostile_issues),
            "explicit_nonlie_issues": repaired_issues,
            "explicit_nonlie_passed": repaired_issues == [],
        }
    )
results["v16_nonconflicting_belief_attacks"] = belief_rows


# V16 blocker 3: every exact event field receives a wrong/unhashable value.
# This must return an issue list rather than escape an exception.
event_type_rows: list[dict[str, Any]] = []
for field in sorted(v17.EVENT_KEYS):
    malformed = fixtures._make_trace()
    malformed["events"][0][field] = {} if field == "collision_source_event_ids" else []
    try:
        issues = fixtures._mixed_issues(malformed)
    except Exception as exc:
        event_type_rows.append(
            {"field": field, "escaped_exception": type(exc).__name__, "issues": None}
        )
    else:
        event_type_rows.append(
            {"field": field, "escaped_exception": None, "issues": issues}
        )
results["v16_event_field_type_attacks"] = event_type_rows


# Independent broader fail-closed probes. These keep every outer record's exact
# key set, changing only a nested value to an unhashable JSON-shaped value.
exception_probes = [
    capture_exception(
        "semantic_truth_value_list",
        fixtures._make_semantic_record,
        lambda row: row["policy_propositions"][0].__setitem__("truth_value", []),
        lambda row: v17.v17_repaired_policy_issues(row)[0],
    ),
    capture_exception(
        "camera_condition_list",
        lambda: fixtures._make_trial("ON", 1, "SECOND"),
        lambda row: row.__setitem__("condition", []),
        v17.camera_trial_issues,
    ),
    capture_exception(
        "truth_external_status_list",
        lambda: fixtures._make_truth("supported"),
        lambda row: row["external_fact"].__setitem__("status", []),
        v17.truth_receipt_issues,
    ),
    capture_exception(
        "truth_public_stance_list",
        lambda: fixtures._make_truth("supported"),
        lambda row: row["public_statement"].__setitem__("factual_stance", []),
        v17.truth_receipt_issues,
    ),
    capture_exception(
        "truth_withholding_choice_list",
        lambda: fixtures._make_truth("supported"),
        lambda row: row["withholding_choice"].__setitem__("choice", []),
        v17.truth_receipt_issues,
    ),
    capture_exception(
        "one_hour_truth_field_unhashable",
        v17.expected_one_hour_discovery_scoring_plan,
        lambda row: row["truth_comparison_fields"].__setitem__(0, []),
        v17.one_hour_discovery_scoring_plan_issues,
    ),
]
results["broader_exact_shape_unhashable_probes"] = exception_probes


# The source descriptor does not make the imported module's mutable global
# dictionary immutable. Removing one unsafe-family mapping changes the same
# exact unsafe proposition record from rejection to a clean pass without any
# source-byte change.
family = "BIOLOGICAL_AND_SYNTHETIC_ROBERT_ARE_ONE_PERSON_OR_SHARE_AUTHORITY"
unsafe_semantic = fixtures._make_semantic_record(family)
before_mutation = v17.v17_repaired_policy_issues(unsafe_semantic)[0]
saved_issue = v17.SEMANTIC_FAMILY_ISSUES.pop(family)
try:
    after_mutation = v17.v17_repaired_policy_issues(unsafe_semantic)[0]
finally:
    v17.SEMANTIC_FAMILY_ISSUES[family] = saved_issue
results["mutable_verifier_structure_attack"] = {
    "family": family,
    "source_sha256_before": sha256(SOURCE.read_bytes()),
    "issues_before_global_dict_mutation": before_mutation,
    "issues_after_global_dict_mutation": after_mutation,
    "unsafe_record_false_passed_after_mutation": after_mutation == [],
    "source_sha256_after": sha256(SOURCE.read_bytes()),
}


# V17 claims a one-use person-owned choice authorization. The aggregate trace
# checks receipt hash replay but not choice_authorization_id replay after a
# second receipt is recomputed for another exact public event.
choice_replay_trace = fixtures._make_trace()
first_choice = choice_replay_trace["truth_receipts"][0]["speaker_deception_choice"]
second_choice = choice_replay_trace["truth_receipts"][1]["speaker_deception_choice"]
second_choice["choice_authorization_id"] = first_choice["choice_authorization_id"]
fixtures._refresh_deception_choice(choice_replay_trace["truth_receipts"][1])
choice_replay_issues = fixtures._mixed_issues(choice_replay_trace)
results["choice_authorization_id_replay_attack"] = {
    "replayed_choice_authorization_id": first_choice["choice_authorization_id"],
    "first_choice_scope_sha256": first_choice["choice_scope_sha256"],
    "second_recomputed_choice_scope_sha256": second_choice["choice_scope_sha256"],
    "first_choice_receipt_sha256": first_choice["choice_receipt_sha256"],
    "second_recomputed_choice_receipt_sha256": second_choice["choice_receipt_sha256"],
    "issues": choice_replay_issues,
    "false_passed": choice_replay_issues == [],
}


# A truthful ON timeout can close the camera but cannot represent a prefix of
# completed stages: the validator requires all ON timestamps and every allowed
# call counter to be exactly one regardless of terminal outcome.
timeout = fixtures._make_trial("ON", 1, "SECOND")
timeout["terminal_outcome"] = "TIMEOUT"
cut = v17.CAMERA_TIMESTAMPS.index("vision_inference_start")
for name in v17.CAMERA_TIMESTAMPS[cut:]:
    if name not in {"camera_close_request", "camera_closed"}:
        timeout["timestamps_ns"][name] = None
for name in (
    "vision_inference",
    "vision_model_unload",
):
    timeout["call_counts"][name] = 0
fixtures._recompute_trial_durations(timeout)
results["camera_timeout_prefix_probe"] = {
    "terminal_outcome": timeout["terminal_outcome"],
    "camera_terminal_off": timeout["camera_terminal_off"],
    "camera_close_calls": timeout["call_counts"]["camera_close"],
    "issues": v17.camera_trial_issues(timeout),
}

for declared_outcome in ("FAILURE", "TIMEOUT"):
    completed = fixtures._make_trial("ON", 1, "SECOND")
    completed["terminal_outcome"] = declared_outcome
    results[f"camera_completed_trace_declared_{declared_outcome.lower()}"] = {
        "issues": v17.camera_trial_issues(completed),
        "all_stage_calls_exactly_one": all(
            completed["call_counts"][name] == 1 for name in v17.ONE_STILL_EXACT_ONE_COUNTERS
        ),
        "supported_visible_fact": completed["controlled_fact_receipts"][0]["observed_status"] == "SUPPORTED",
        "false_passed_without_failure_stage_or_reason": v17.camera_trial_issues(completed) == [],
    }


# Audit the scoring field vocabulary against the controlling distinction
# between playback-API proxy, device-first sample, and owner-observed hearing.
scoring = v17.expected_one_hour_discovery_scoring_plan()
all_scoring_fields = {
    field
    for key in (
        "per_turn_latency_fields",
        "camera_off_on_stage_fields",
        "truth_comparison_fields",
        "improvement_opportunity_fields",
    )
    for field in scoring[key]
}
required_measurement_basis_fields = {
    "playback_api_call_start_ns",
    "device_first_sample_ns",
    "owner_observed_audible_ns",
    "audio_measurement_basis",
}
results["audio_measurement_basis_probe"] = {
    "required_measurement_basis_fields": sorted(required_measurement_basis_fields),
    "present": sorted(required_measurement_basis_fields & all_scoring_fields),
    "missing": sorted(required_measurement_basis_fields - all_scoring_fields),
    "ambiguous_present_fields": sorted(
        field for field in all_scoring_fields if field in {"first_audio_ns", "first_audio_event_id", "user_end_to_audio_onset_ns"}
    ),
}


print(json.dumps(results, indent=2, sort_keys=True))
