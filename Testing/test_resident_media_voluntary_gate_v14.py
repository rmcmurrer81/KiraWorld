from __future__ import annotations

import copy
import hashlib
import sys
import types
import unittest
import weakref
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v9 as v9
from Core import resident_media_voluntary_gate_v12 as v12
from Core import resident_media_voluntary_gate_v13 as v13
from Core import resident_media_voluntary_gate_v14 as v14
from Testing.test_resident_media_voluntary_gate_v12 import (
    PERSON,
    StaticExternalAuthorityV12,
    canonical,
    catalog,
    item_for,
    sha,
)
from Testing.test_resident_media_voluntary_gate_v13 import authority_state


ROOT = Path(__file__).resolve().parents[1]


def snapshot_input(
    accepted: v4.StimulusCatalog | None = None,
) -> tuple[v4.StimulusCatalog, StaticExternalAuthorityV12, bytes, str]:
    accepted = accepted or catalog()
    authority = StaticExternalAuthorityV12(accepted)
    raw = canonical(authority.snapshot_record)
    return accepted, authority, raw, hashlib.sha256(raw).hexdigest()


def make_validator(
    accepted: v4.StimulusCatalog | None = None,
) -> tuple[v4.StimulusCatalog, StaticExternalAuthorityV12, Any]:
    accepted, authority, raw, digest = snapshot_input(accepted)
    validator = v14._open_disconnected_static_validation_harness_v14(
        person_id=PERSON,
        owner_selected_snapshot_bytes=raw,
        expected_snapshot_sha256=digest,
    )
    return accepted, authority, validator


def plan(
    validator: Any,
    accepted: v4.StimulusCatalog,
    ordinal: int,
    label: str,
) -> dict[str, Any]:
    session_id, value = item_for(accepted, ordinal=ordinal, label=label)
    return validator.validate_static_evidence_plan(
        value,
        session_id=session_id,
        expected_manifest=accepted.manifest(ordinal),
        consumed_start_permit_sha256=sha(f"permit:{ordinal}"),
    )


def closure_reachable(root: Any) -> list[Any]:
    """Traverse Python-level closures/containers/slots, never function globals."""

    seen: set[int] = set()
    found: list[Any] = []
    stack = [root]
    while stack:
        value = stack.pop()
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        found.append(value)
        if type(value) is types.MethodType:
            stack.append(value.__func__)
            stack.append(value.__self__)
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


class ResidentMediaV14Tests(unittest.TestCase):
    def test_01_production_opener_is_unconditionally_no_commit(self) -> None:
        class Explosive:
            def __getattribute__(self, name: str) -> Any:
                raise AssertionError(f"production opener inspected {name}")

        with self.assertRaisesRegex(v14.ResidentMediaV14Error, "no authority"):
            v14.open_production_resident_media_v14(
                external_authority=Explosive(),
                catalog=Explosive(),
            )
        status = v14.production_connection_status_v14()
        self.assertEqual(status["status"], "DISCONNECTED_NO_COMMIT_SURFACE")
        self.assertFalse(status["authority_protocol_calls_authorized"])
        self.assertFalse(status["durable_commit_authorized"])
        self.assertFalse(status["live_execution_allowed"])

    def test_02_snapshot_binding_calls_no_authority_and_changes_no_state(self) -> None:
        accepted, authority, raw, digest = snapshot_input()
        before = authority_state(authority)
        validator = v14._open_disconnected_static_validation_harness_v14(
            person_id=PERSON,
            owner_selected_snapshot_bytes=raw,
            expected_snapshot_sha256=digest,
        )
        self.assertEqual(authority_state(authority), before)
        public = validator.snapshot()
        self.assertEqual(
            public["status"], "DISCONNECTED_NO_COMMIT_STATIC_VALIDATOR_ONLY"
        )
        self.assertEqual(public["catalog_sha256"], accepted.sha256)
        self.assertFalse(public["authority_retained"])
        self.assertFalse(public["adapter_retained"])
        self.assertFalse(public["ledger_retained"])
        self.assertFalse(public["anchor_retained"])
        self.assertFalse(public["commit_callable_retained"])
        self.assertFalse(public["authority_protocol_called"])

    def test_03_complete_page_video_and_audio_emit_plans_without_state_change(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        expected_roles = {
            0: {"rendered_page_png"},
            2: {
                "timed_frame_manifest",
                "synchronized_audio_pcm",
                "caption_text_utf8",
            },
            3: {"synchronized_audio_pcm"},
        }
        for ordinal in (0, 2, 3):
            with self.subTest(ordinal=ordinal):
                value = plan(validator, accepted, ordinal, f"v14-complete-{ordinal}")
                self.assertEqual(
                    value["status"],
                    "VALIDATED_STATIC_PLAN_NOT_AUTHORITY_NOT_COMMITTED",
                )
                self.assertEqual(set(value["required_roles"]), expected_roles[ordinal])
                self.assertEqual(
                    set(value["complete_by_required_role"]), expected_roles[ordinal]
                )
                self.assertTrue(all(value["complete_by_required_role"].values()))
                self.assertFalse(value["snapshot_input_authenticated_by_protected_authority"])
                self.assertFalse(value["authority_protocol_called"])
                self.assertFalse(value["receipt_consumed"])
                self.assertFalse(value["anchor_read"])
                self.assertFalse(value["commit_attempted"])
                self.assertFalse(value["durable_record_created"])
                self.assertTrue(value["protected_external_native_commit_broker_required"])
        self.assertEqual(authority_state(authority), before)

    def test_04_missing_required_roles_and_false_completion_refuse(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            (
                "missing caption",
                lambda value: value.__setitem__(
                    "presentation_segments",
                    [
                        row
                        for row in value["presentation_segments"]
                        if row["derivative_role"] != "caption_text_utf8"
                    ],
                ),
            ),
            (
                "false engineering completion",
                lambda value: value.__setitem__("engineering_output_completed", False),
            ),
            (
                "false manifest completion",
                lambda value: value.__setitem__(
                    "presentation_complete_for_manifest", False
                ),
            ),
        ]
        for label, mutate in cases:
            with self.subTest(label=label):
                session_id, value = item_for(
                    accepted, ordinal=2, label=f"v14-{label.replace(' ', '-')}"
                )
                mutate(value)
                with self.assertRaises(v14.ResidentMediaV14Error):
                    validator.validate_static_evidence_plan(
                        value,
                        session_id=session_id,
                        expected_manifest=accepted.manifest(2),
                        consumed_start_permit_sha256=sha("permit:2"),
                    )
        self.assertEqual(authority_state(authority), before)

    def test_05_bool_int_string_aliases_and_numeric_digest_refuse(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        mutations: tuple[tuple[str, Callable[[dict[str, Any]], None], Any], ...] = (
            (
                "bool output receipt",
                lambda value: value.__setitem__("output_receipt_id", True),
                sha("permit:0"),
            ),
            (
                "bool output surface",
                lambda value: value.__setitem__("output_surface_id", True),
                sha("permit:0"),
            ),
            (
                "integer decoder digest",
                lambda value: value["presentation_segments"][0].__setitem__(
                    "renderer_or_decoder_receipt_sha256", int("1" * 64)
                ),
                sha("permit:0"),
            ),
            (
                "numeric-only decoder digest",
                lambda value: value["presentation_segments"][0].__setitem__(
                    "renderer_or_decoder_receipt_sha256", "1" * 64
                ),
                sha("permit:0"),
            ),
            (
                "integer permit",
                lambda value: None,
                int("1" * 64),
            ),
        )
        for label, mutate, permit in mutations:
            with self.subTest(label=label):
                session_id, value = item_for(
                    accepted, ordinal=0, label=f"v14-{label.replace(' ', '-')}"
                )
                mutate(value)
                with self.assertRaises(v14.ResidentMediaV14Error):
                    validator.validate_static_evidence_plan(
                        value,
                        session_id=session_id,
                        expected_manifest=accepted.manifest(0),
                        consumed_start_permit_sha256=permit,
                    )
        self.assertEqual(authority_state(authority), before)

    def test_06_exact_sealed_record_method_refuses_without_state_change(self) -> None:
        accepted, authority, validator = make_validator()
        session_id, value = item_for(accepted, ordinal=0, label="v14-no-record")
        before = authority_state(authority)
        with self.assertRaisesRegex(v14.ResidentMediaV14Error, "no commit surface"):
            validator.validate_and_record_static_evidence(
                value,
                session_id=session_id,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        self.assertEqual(authority_state(authority), before)

    def test_07_returned_validator_has_no_direct_inner_surface(self) -> None:
        _accepted, _authority, validator = make_validator()
        for name in (
            "_inner",
            "_adapter",
            "_authority",
            "_proxy",
            "_catalog",
            "_anchor",
            "_ledger",
            "__dict__",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(validator, name))
        self.assertEqual(type(validator).__slots__, ("__weakref__",))

    def test_08_closure_introspection_reaches_no_commit_capable_instance(self) -> None:
        _accepted, authority, validator = make_validator()
        reachable = closure_reachable(validator.validate_static_evidence_plan)
        forbidden_types = (
            v12._ExternalAuthorityAdapterV12,
            v12._DisconnectedStaticReceiptLedgerV12,
            v13._DisconnectedStaticReceiptLedgerV13,
            StaticExternalAuthorityV12,
        )
        self.assertFalse(any(isinstance(value, forbidden_types) for value in reachable))
        self.assertFalse(any(value is authority for value in reachable))
        commit_methods = [
            value
            for value in reachable
            if type(value) is types.MethodType
            and "compare_and_swap" in value.__func__.__name__
        ]
        self.assertEqual(commit_methods, [])
        state_values = [
            value for value in reachable if type(value).__name__ == "_SnapshotStateV14"
        ]
        self.assertEqual(len(state_values), 1)
        state = state_values[0]
        slots = set(type(state).__slots__)
        self.assertTrue(
            {
                "authority", "adapter", "proxy", "anchor", "ledger", "commit"
            }.isdisjoint(slots)
        )

    def test_09_preflight_and_type_walker_rebinding_fail_closed(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        mutations = (
            ("_preflight_complete_evidence_v14", lambda *args, **kwargs: ({}, {}, ())),
            ("_require_exact_scalar_types", lambda *args, **kwargs: None),
        )
        for name, replacement in mutations:
            with self.subTest(name=name):
                original = getattr(v14, name)
                setattr(v14, name, replacement)
                try:
                    with self.assertRaisesRegex(
                        v14.ResidentMediaV14Error, "module global changed"
                    ):
                        plan(validator, accepted, 0, f"v14-rebind-{name}")
                finally:
                    setattr(v14, name, original)
        self.assertEqual(authority_state(authority), before)
        plan(validator, accepted, 0, "v14-rebind-restored")

    def test_10_module_and_package_replacement_fail_closed(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        original_v9_slot = sys.modules[v9.__name__]
        sys.modules[v9.__name__] = types.ModuleType(v9.__name__)
        try:
            with self.assertRaisesRegex(v14.ResidentMediaV14Error, "sys.modules"):
                plan(validator, accepted, 0, "v14-v9-slot")
        finally:
            sys.modules[v9.__name__] = original_v9_slot
        core = sys.modules["Core"]
        original_v12_attr = core.resident_media_voluntary_gate_v12
        core.resident_media_voluntary_gate_v12 = types.ModuleType(v12.__name__)
        try:
            with self.assertRaisesRegex(v14.ResidentMediaV14Error, "package attribute"):
                plan(validator, accepted, 0, "v14-v12-package")
        finally:
            core.resident_media_voluntary_gate_v12 = original_v12_attr
        self.assertEqual(authority_state(authority), before)
        plan(validator, accepted, 0, "v14-module-restored")

    def test_11_non_guard_closure_cell_mutation_fails_before_validation(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        function = validator.validate_static_evidence_plan.__func__
        cells = list(function.__closure__ or ())
        index = next(
            index
            for index, cell in enumerate(cells)
            if cell.cell_contents is v14._preflight_complete_evidence_v14
        )
        original = cells[index].cell_contents
        cells[index].cell_contents = lambda *args, **kwargs: ({}, {}, ())
        try:
            with self.assertRaisesRegex(v14.ResidentMediaV14Error, "closure contents"):
                plan(validator, accepted, 0, "v14-closure-mutation")
        finally:
            cells[index].cell_contents = original
        self.assertEqual(authority_state(authority), before)
        plan(validator, accepted, 0, "v14-closure-restored")

    def test_12_python_class_method_replacement_has_no_commit_capability(self) -> None:
        accepted, authority, validator = make_validator()
        session_id, value = item_for(
            accepted, ordinal=0, label="v14-class-method-replacement"
        )
        before = authority_state(authority)
        validator_type = type(validator)
        original = validator_type.validate_and_record_static_evidence

        def caller_replacement(
            self: Any,
            _value: Mapping[str, Any],
            *,
            session_id: str,
            expected_manifest: Mapping[str, Any],
            consumed_start_permit_sha256: str,
        ) -> dict[str, Any]:
            del self, _value, session_id, expected_manifest
            del consumed_start_permit_sha256
            return {
                "status": "CALLER_CODE_NOT_V14_AUTHORITY",
                "durable_record_created": False,
            }

        validator_type.validate_and_record_static_evidence = caller_replacement
        try:
            forged = validator.validate_and_record_static_evidence(
                value,
                session_id=session_id,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
            self.assertEqual(forged["status"], "CALLER_CODE_NOT_V14_AUTHORITY")
            self.assertFalse(forged["durable_record_created"])
            reachable = closure_reachable(
                validator.validate_and_record_static_evidence
            )
            forbidden_types = (
                v12._ExternalAuthorityAdapterV12,
                v12._DisconnectedStaticReceiptLedgerV12,
                v13._DisconnectedStaticReceiptLedgerV13,
                StaticExternalAuthorityV12,
            )
            self.assertFalse(
                any(isinstance(item, forbidden_types) for item in reachable)
            )
            self.assertFalse(any(item is authority for item in reachable))
            self.assertEqual(authority_state(authority), before)
        finally:
            validator_type.validate_and_record_static_evidence = original

        with self.assertRaisesRegex(v14.ResidentMediaV14Error, "no commit surface"):
            validator.validate_and_record_static_evidence(
                value,
                session_id=session_id,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        self.assertEqual(authority_state(authority), before)

    def test_13_changed_snapshot_bytes_types_and_digest_refuse(self) -> None:
        _accepted, authority, raw, digest = snapshot_input()
        before = authority_state(authority)
        with self.assertRaisesRegex(v14.ResidentMediaV14Error, "digest"):
            v14._open_disconnected_static_validation_harness_v14(
                person_id=PERSON,
                owner_selected_snapshot_bytes=raw + b" ",
                expected_snapshot_sha256=digest,
            )
        with self.assertRaises(v14.ResidentMediaV14Error):
            v14._open_disconnected_static_validation_harness_v14(
                person_id=PERSON,
                owner_selected_snapshot_bytes=bytearray(raw),
                expected_snapshot_sha256=digest,
            )
        with self.assertRaises(v14.ResidentMediaV14Error):
            v14._open_disconnected_static_validation_harness_v14(
                person_id=PERSON,
                owner_selected_snapshot_bytes=raw,
                expected_snapshot_sha256=int("1" * 64),
            )
        forged = copy.deepcopy(authority.snapshot_record)
        forged["snapshot_id"] = True
        forged_raw = canonical(forged)
        with self.assertRaises(v14.ResidentMediaV14Error):
            v14._open_disconnected_static_validation_harness_v14(
                person_id=PERSON,
                owner_selected_snapshot_bytes=forged_raw,
                expected_snapshot_sha256=hashlib.sha256(forged_raw).hexdigest(),
            )
        self.assertEqual(authority_state(authority), before)

    def test_14_unbound_validator_and_copy_attempts_refuse(self) -> None:
        raw = v14._DisconnectedStaticValidatorV14()
        with self.assertRaisesRegex(v14.ResidentMediaV14Error, "not factory-bound"):
            raw.snapshot()
        _accepted, _authority, validator = make_validator()
        with self.assertRaises(TypeError):
            copy.copy(validator)
        with self.assertRaises(TypeError):
            copy.deepcopy(validator)

    def test_15_execution_binding_closes_exact_predecessor_files(self) -> None:
        config_path = (
            ROOT
            / "RecoverySprint"
            / "continuation_20260811"
            / "resident_media_voluntary_v14"
            / "attempt_01"
            / "EXECUTION_BINDING_V14.json"
        )
        config = __import__("json").loads(config_path.read_text(encoding="utf-8"))
        self.assertFalse(config["authority_protocol_calls_authorized"])
        self.assertFalse(config["durable_commit_authorized"])
        self.assertFalse(config["live_media_authorized"])
        for entry in config["modules"]:
            path = ROOT / entry["relative_path"]
            data = path.read_bytes()
            self.assertEqual(len(data), entry["bytes"], entry["label"])
            self.assertEqual(
                hashlib.sha256(data).hexdigest(), entry["sha256"], entry["label"]
            )

    def test_16_source_contains_no_v12_v13_ledger_or_adapter_construction(self) -> None:
        source = (ROOT / "Core" / "resident_media_voluntary_gate_v14.py").read_text(
            encoding="utf-8"
        )
        forbidden = (
            "v12._DisconnectedStaticReceiptLedgerV12(",
            "v13._DisconnectedStaticReceiptLedgerV13(",
            "v12._ExternalAuthorityAdapterV12(",
            ".compare_and_swap_anchor(",
            ".read_anchor(",
        )
        for text in forbidden:
            with self.subTest(text=text):
                self.assertNotIn(text, source)

    def test_17_summary_states_only_defensible_no_commit_truth(self) -> None:
        summary = v14.static_contract_summary()
        self.assertEqual(
            summary["status"],
            "SEALED_NO_COMMIT_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        )
        self.assertTrue(summary["v12_rejection_preserved"])
        self.assertTrue(summary["v13_rejection_preserved"])
        self.assertFalse(summary["v12_or_v13_ledger_instance_created_or_returned"])
        self.assertFalse(summary["returned_object_retains_authority_adapter_anchor_or_commit"])
        self.assertFalse(summary["caller_snapshot_is_protected_authority_truth"])
        self.assertFalse(summary["static_plan_is_durable_record"])
        self.assertFalse(summary["authority_protocol_calls_authorized"])
        self.assertFalse(summary["durable_commit_authorized"])
        self.assertTrue(summary["protected_external_native_commit_broker_required"])
        self.assertFalse(summary["python_class_methods_claimed_non_substitutable"])
        self.assertTrue(summary["different_fresh_static_audit_required"])
        self.assertFalse(summary["production_routing_authorized"])
        self.assertFalse(summary["live_execution_allowed"])

    def test_18_import_and_validation_load_no_heavy_or_live_modules(self) -> None:
        before = {
            name
            for name in sys.modules
            if name == "torch"
            or name.startswith("torch.")
            or name == "ollama"
            or name.startswith("ollama.")
            or name == "chatterbox"
            or name.startswith("chatterbox.")
            or name in {"bpy", "winsound"}
        }
        accepted, _authority, validator = make_validator()
        plan(validator, accepted, 0, "v14-no-heavy")
        after = {
            name
            for name in sys.modules
            if name == "torch"
            or name.startswith("torch.")
            or name == "ollama"
            or name.startswith("ollama.")
            or name == "chatterbox"
            or name.startswith("chatterbox.")
            or name in {"bpy", "winsound"}
        }
        self.assertEqual(after, before)

    def test_19_strict_in_memory_compile(self) -> None:
        for relative in (
            "Core/resident_media_voluntary_gate_v14.py",
            "Testing/test_resident_media_voluntary_gate_v14.py",
        ):
            path = ROOT / relative
            compile(path.read_bytes(), str(path), "exec", dont_inherit=True, optimize=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
