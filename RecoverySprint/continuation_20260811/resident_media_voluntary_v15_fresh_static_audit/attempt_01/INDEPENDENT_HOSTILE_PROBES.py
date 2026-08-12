from __future__ import annotations

import copy
import hashlib
import json
import sys
import types
import weakref
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v15 as v15
from Testing.test_resident_media_voluntary_gate_v12 import (
    PERSON,
    StaticExternalAuthorityV12,
    item_for,
    sha,
)
from Testing.test_resident_media_voluntary_gate_v13 import authority_state
from Testing.test_resident_media_voluntary_gate_v15 import make_validator


def closure_reachable(root: object) -> list[object]:
    seen: set[int] = set()
    found: list[object] = []
    stack = [root]
    while stack:
        value = stack.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        found.append(value)
        if type(value) is types.MethodType:
            stack.extend((value.__func__, value.__self__))
        elif type(value) is types.FunctionType:
            for cell in value.__closure__ or ():
                try:
                    stack.append(cell.cell_contents)
                except ValueError:
                    pass
        elif isinstance(value, weakref.WeakKeyDictionary):
            for key, item in list(value.items()):
                stack.extend((key, item))
        elif type(value) is dict:
            stack.extend(value.keys())
            stack.extend(value.values())
        elif type(value) in (tuple, list, set, frozenset):
            stack.extend(value)
        else:
            slots = getattr(type(value), "__slots__", ())
            if type(slots) is str:
                slots = (slots,)
            for slot in slots:
                if slot == "__weakref__":
                    continue
                try:
                    stack.append(object.__getattribute__(value, slot))
                except (AttributeError, TypeError):
                    pass
    return found


def expect_refusal(callable_object, label: str) -> str:
    try:
        callable_object()
    except Exception as exc:
        return f"PASS_REFUSED:{type(exc).__name__}:{str(exc)[:160]}"
    raise AssertionError(f"{label} unexpectedly accepted")


def main() -> None:
    accepted, authority, validator = make_validator()
    before = authority_state(authority)
    session_id, value = item_for(accepted, ordinal=0, label="root-v15-audit")
    expected_manifest = copy.deepcopy(accepted.manifest(0))
    permit = sha("permit:0")

    envelope = validator.validate_static_evidence_plan(
        copy.deepcopy(value),
        session_id=session_id,
        expected_manifest=copy.deepcopy(expected_manifest),
        consumed_start_permit_sha256=permit,
    )
    assert type(envelope) is tuple and len(envelope) == 2
    assert type(envelope[0]) is bytes and type(envelope[1]) is str
    assert hashlib.sha256(envelope[0]).hexdigest() == envelope[1]
    decoded = v15.decode_static_plan_envelope_v15(envelope)
    assert decoded["status"] == "VALIDATED_IMMUTABLE_STATIC_PLAN_NOT_AUTHORITY_NOT_COMMITTED"
    assert decoded["commit_attempted"] is False
    assert decoded["durable_record_created"] is False
    assert decoded["live_execution_allowed"] is False

    accepted._manifests[0]["source_relative_path"] = "hostile/changed-after-bind.mp4"
    after_mutation = validator.validate_static_evidence_plan(
        copy.deepcopy(value),
        session_id=session_id,
        expected_manifest=copy.deepcopy(expected_manifest),
        consumed_start_permit_sha256=permit,
    )
    assert after_mutation == envelope

    reachable = closure_reachable(validator.validate_static_evidence_plan)
    forbidden_reachable = [
        type(item).__name__
        for item in reachable
        if isinstance(item, (v4.StimulusCatalog, weakref.WeakKeyDictionary, StaticExternalAuthorityV12))
        or any(token in type(item).__name__.lower() for token in ("ledger", "adapter"))
    ]
    assert forbidden_reachable == []

    record_refusal = expect_refusal(
        lambda: validator.validate_and_record_static_evidence(
            copy.deepcopy(value),
            session_id=session_id,
            expected_manifest=copy.deepcopy(expected_manifest),
            consumed_start_permit_sha256=permit,
        ),
        "record surface",
    )

    incomplete = copy.deepcopy(value)
    incomplete["engineering_output_completed"] = False
    incomplete_refusal = expect_refusal(
        lambda: validator.validate_static_evidence_plan(
            incomplete,
            session_id=session_id,
            expected_manifest=copy.deepcopy(expected_manifest),
            consumed_start_permit_sha256=permit,
        ),
        "incomplete evidence",
    )

    digest_mismatch_refusal = expect_refusal(
        lambda: v15.decode_static_plan_envelope_v15((envelope[0], "0" * 64)),
        "envelope digest mismatch",
    )

    function = validator.validate_static_evidence_plan.__func__
    cell = next(
        cell
        for cell in function.__closure__ or ()
        if cell.cell_contents is v15._preflight_complete_evidence_v15
    )
    original = cell.cell_contents
    cell.cell_contents = lambda *args, **kwargs: ({}, {}, ())
    try:
        closure_rebind_refusal = expect_refusal(
            lambda: validator.validate_static_evidence_plan(
                copy.deepcopy(value),
                session_id=session_id,
                expected_manifest=copy.deepcopy(expected_manifest),
                consumed_start_permit_sha256=permit,
            ),
            "closure rebind",
        )
    finally:
        cell.cell_contents = original

    assert authority_state(authority) == before

    source = (ROOT / "Core/resident_media_voluntary_gate_v15.py").read_text(encoding="utf-8")
    forbidden_source_tokens = {
        "subprocess": "subprocess",
        "socket": "socket",
        "requests": "requests",
        "cv2": "cv2",
        "torch": "torch",
        "bpy": "bpy",
    }
    absent = {name: token not in source for name, token in forbidden_source_tokens.items()}
    assert all(absent.values())

    consumers: list[str] = []
    for base in (ROOT / "Core", ROOT / "Testing"):
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if b"resident_media_voluntary_gate_v15" in raw:
                consumers.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    assert sorted(consumers) == [
        "Core/resident_media_voluntary_gate_v15.py",
        "Testing/test_resident_media_voluntary_gate_v15.py",
    ]

    result = {
        "schema": "kira.resident_media_voluntary_gate_v15.independent_hostile_probe_result.v1",
        "reviewer": "/root",
        "verdict": "PASS_STATIC_NO_COMMIT_BOUNDARY",
        "exact_tuple_envelope_and_digest": True,
        "original_catalog_mutation_changes_emitted_envelope": False,
        "closure_reachable_forbidden_instances": forbidden_reachable,
        "record_surface": record_refusal,
        "incomplete_evidence": incomplete_refusal,
        "digest_mismatch": digest_mismatch_refusal,
        "closure_rebinding": closure_rebind_refusal,
        "external_authority_state_unchanged": True,
        "forbidden_heavy_or_live_source_tokens_absent": absent,
        "source_or_test_references_only": sorted(consumers),
        "live_or_production_authority": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
