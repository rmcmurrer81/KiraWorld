from __future__ import annotations

import concurrent.futures
import copy
import hashlib
import json
import sys
import types
import unittest
import weakref
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from Core import resident_media_voluntary_gate_v4 as v4
from Core import resident_media_voluntary_gate_v12 as v12
from Core import resident_media_voluntary_gate_v13 as v13
from Core import resident_media_voluntary_gate_v14 as v14
from Core import resident_media_voluntary_gate_v15 as v15
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
    validator = v15._open_disconnected_static_validation_harness_v15(
        person_id=PERSON,
        owner_selected_snapshot_bytes=raw,
        expected_snapshot_sha256=digest,
    )
    return accepted, authority, validator


def envelope(
    validator: Any,
    accepted: v4.StimulusCatalog,
    ordinal: int,
    label: str,
) -> Any:
    session_id, value = item_for(accepted, ordinal=ordinal, label=label)
    return validator.validate_static_evidence_plan(
        value,
        session_id=session_id,
        expected_manifest=accepted.manifest(ordinal),
        consumed_start_permit_sha256=sha(f"permit:{ordinal}"),
    )


def plan(
    validator: Any,
    accepted: v4.StimulusCatalog,
    ordinal: int,
    label: str,
) -> dict[str, Any]:
    return v15.decode_static_plan_envelope_v15(
        envelope(validator, accepted, ordinal, label)
    )


def closure_reachable(root: Any) -> list[Any]:
    """Traverse Python-level closures/containers/slots, never globals."""

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


class ResidentMediaV15Tests(unittest.TestCase):
    def test_01_v14_stale_catalog_digest_rejection_is_reproducible(self) -> None:
        accepted, _authority, raw, digest = snapshot_input()
        validator = v14._open_disconnected_static_validation_harness_v14(
            person_id=PERSON,
            owner_selected_snapshot_bytes=raw,
            expected_snapshot_sha256=digest,
        )
        reachable = closure_reachable(validator.validate_static_evidence_plan)
        state = next(
            item for item in reachable if type(item).__name__ == "_SnapshotStateV14"
        )
        old_digest = state.catalog.sha256
        changed = copy.deepcopy(state.catalog._manifests)
        changed[0]["source_relative_path"] = "Media/changed-after-v14-bind.png"
        state.catalog._manifests = tuple(changed)
        session_id, value = item_for(
            state.catalog, ordinal=0, label="v14-stale-digest-proof"
        )
        emitted = validator.validate_static_evidence_plan(
            value,
            session_id=session_id,
            expected_manifest=state.catalog.manifest(0),
            consumed_start_permit_sha256=sha("permit:0"),
        )
        current_bytes = canonical(
            {
                "schema": "kira.resident_media_source_catalog.v4",
                "manifests": list(state.catalog._manifests),
            }
        )
        self.assertEqual(emitted["catalog_sha256"], old_digest)
        self.assertNotEqual(hashlib.sha256(current_bytes).hexdigest(), old_digest)
        self.assertIsNot(state.catalog, accepted)

    def test_02_production_opener_is_unconditionally_disconnected(self) -> None:
        class Explosive:
            def __getattribute__(self, name: str) -> Any:
                raise AssertionError(f"production opener inspected {name}")

        with self.assertRaisesRegex(v15.ResidentMediaV15Error, "no authority"):
            v15.open_production_resident_media_v15(
                external_authority=Explosive(), catalog=Explosive()
            )
        status = v15.production_connection_status_v15()
        self.assertEqual(status["status"], "DISCONNECTED_IMMUTABLE_NO_COMMIT_SURFACE")
        self.assertFalse(status["authority_protocol_calls_authorized"])
        self.assertFalse(status["durable_commit_authorized"])
        self.assertFalse(status["live_execution_allowed"])

    def test_03_snapshot_binding_calls_no_authority_and_retains_no_catalog(self) -> None:
        accepted, authority, raw, digest = snapshot_input()
        before = authority_state(authority)
        validator = v15._open_disconnected_static_validation_harness_v15(
            person_id=PERSON,
            owner_selected_snapshot_bytes=raw,
            expected_snapshot_sha256=digest,
        )
        self.assertEqual(authority_state(authority), before)
        public = validator.snapshot()
        self.assertEqual(
            public["status"],
            "DISCONNECTED_IMMUTABLE_NO_COMMIT_STATIC_VALIDATOR_ONLY",
        )
        self.assertEqual(public["catalog_sha256"], accepted.sha256)
        self.assertTrue(public["immutable_tuple_state_only"])
        self.assertFalse(public["mutable_catalog_retained"])
        self.assertFalse(public["mutable_mapping_or_weak_registry_retained"])
        self.assertFalse(public["authority_protocol_called"])

    def test_04_complete_roles_emit_exact_immutable_plan_envelopes(self) -> None:
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
                result = envelope(
                    validator, accepted, ordinal, f"v15-complete-{ordinal}"
                )
                self.assertIs(type(result), tuple)
                self.assertEqual(len(result), 2)
                self.assertEqual(
                    result[1],
                    hashlib.sha256(result[0]).hexdigest(),
                )
                value = v15.decode_static_plan_envelope_v15(result)
                self.assertEqual(
                    value["status"],
                    "VALIDATED_IMMUTABLE_STATIC_PLAN_NOT_AUTHORITY_NOT_COMMITTED",
                )
                self.assertEqual(set(value["required_roles"]), expected_roles[ordinal])
                self.assertEqual(
                    set(value["complete_by_required_role"]), expected_roles[ordinal]
                )
                self.assertTrue(all(value["complete_by_required_role"].values()))
                self.assertTrue(
                    value["plan_digest_is_derived_from_exact_envelope_bytes"]
                )
                self.assertFalse(value["durable_record_created"])
        self.assertEqual(authority_state(authority), before)

    def test_05_envelope_copy_mutation_and_digest_mismatch_paths_close(self) -> None:
        accepted, _authority, validator = make_validator()
        result = envelope(validator, accepted, 0, "v15-envelope")
        original_bytes = result[0]
        original_digest = result[1]
        record = v15.decode_static_plan_envelope_v15(result)
        record["catalog_sha256"] = "0" * 64
        self.assertEqual(result[0], original_bytes)
        self.assertEqual(result[1], original_digest)
        self.assertNotEqual(
            v15.decode_static_plan_envelope_v15(result)["catalog_sha256"],
            "0" * 64,
        )
        with self.assertRaises(TypeError):
            result[0] = b"{}"
        with self.assertRaises(TypeError):
            setattr(tuple, "reported_sha256", property(lambda self: "0" * 64))
        with self.assertRaises((AttributeError, TypeError)):
            object.__setattr__(result, "reported_sha256", "0" * 64)
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        forged = (b"{}", hashlib.sha256(b"{}").hexdigest())
        self.assertEqual(v15.decode_static_plan_envelope_v15(forged), {})
        malformed = (b"{}", "0" * 64)
        with self.assertRaises(v15.ResidentMediaV15Error):
            v15.decode_static_plan_envelope_v15(malformed)

        original_decoder = v15.decode_static_plan_envelope_v15
        v15.decode_static_plan_envelope_v15 = lambda _value: {
            "status": "CALLER_REPLACEMENT_NOT_ENVELOPE_STATE"
        }
        try:
            self.assertEqual(result[0], original_bytes)
            self.assertEqual(result[1], hashlib.sha256(result[0]).hexdigest())
        finally:
            v15.decode_static_plan_envelope_v15 = original_decoder
        self.assertEqual(
            v15.decode_static_plan_envelope_v15(result)["status"],
            "VALIDATED_IMMUTABLE_STATIC_PLAN_NOT_AUTHORITY_NOT_COMMITTED",
        )

    def test_06_caller_catalog_mutation_cannot_change_retained_snapshot(self) -> None:
        accepted, _authority, validator = make_validator()
        session_id, value = item_for(
            accepted, ordinal=0, label="v15-caller-catalog-mutated"
        )
        expected = accepted.manifest(0)
        original_catalog_sha = accepted.sha256
        changed = copy.deepcopy(accepted._manifests)
        changed[0]["source_relative_path"] = "Media/caller-mutated.png"
        accepted._manifests = tuple(changed)
        result = validator.validate_static_evidence_plan(
            value,
            session_id=session_id,
            expected_manifest=expected,
            consumed_start_permit_sha256=sha("permit:0"),
        )
        self.assertEqual(
            v15.decode_static_plan_envelope_v15(result)["catalog_sha256"],
            original_catalog_sha,
        )
        with self.assertRaises(v15.ResidentMediaV15Error):
            validator.validate_static_evidence_plan(
                value,
                session_id=session_id,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )

    def test_07_closure_reaches_no_mutable_catalog_state_or_commit_capability(self) -> None:
        _accepted, authority, validator = make_validator()
        reachable = closure_reachable(validator.validate_static_evidence_plan)
        forbidden_types = (
            v4.StimulusCatalog,
            weakref.WeakKeyDictionary,
            v12._ExternalAuthorityAdapterV12,
            v12._DisconnectedStaticReceiptLedgerV12,
            v13._DisconnectedStaticReceiptLedgerV13,
            StaticExternalAuthorityV12,
        )
        self.assertFalse(any(isinstance(value, forbidden_types) for value in reachable))
        self.assertFalse(any(value is authority for value in reachable))
        self.assertFalse(
            any(type(value).__name__ == "_SnapshotStateV14" for value in reachable)
        )
        self.assertEqual(type(validator).__slots__, ())
        self.assertEqual(len(validator), 4)
        self.assertIs(type(validator[1]), str)
        self.assertIs(type(validator[2]), bytes)
        self.assertRegex(validator[3], r"^[0-9a-f]{64}$")
        self.assertFalse(hasattr(validator, "__dict__"))

    def test_08_validator_tuple_is_immutable_and_wrong_seal_fails(self) -> None:
        _accepted, _authority, validator = make_validator()
        with self.assertRaises(TypeError):
            validator[2] = b"{}"
        with self.assertRaises((AttributeError, TypeError)):
            object.__setattr__(validator, "snapshot_bytes", b"{}")
        with self.assertRaises(TypeError):
            type(validator)()
        forged = tuple.__new__(
            type(validator), (object(), validator[1], validator[2], validator[3])
        )
        with self.assertRaisesRegex(v15.ResidentMediaV15Error, "seal"):
            forged.snapshot()
        with self.assertRaises(TypeError):
            copy.copy(validator)
        with self.assertRaises(TypeError):
            copy.deepcopy(validator)

    def test_09_fresh_catalog_digest_matches_immutable_snapshot_contents(self) -> None:
        accepted, _authority, validator = make_validator()
        result = envelope(validator, accepted, 0, "v15-fresh-digest")
        value = v15.decode_static_plan_envelope_v15(result)
        snapshot = json.loads(validator[2].decode("utf-8"))
        catalog_bytes = canonical(snapshot["catalog_record"])
        derived = hashlib.sha256(catalog_bytes).hexdigest()
        self.assertEqual(value["catalog_sha256"], derived)
        self.assertEqual(snapshot["catalog_sha256"], derived)
        self.assertEqual(
            value["source_manifest_sha256"],
            v12._record_sha(snapshot["catalog_record"]["manifests"][0]),
        )

    def test_10_missing_roles_and_false_completion_refuse(self) -> None:
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
                    accepted, ordinal=2, label=f"v15-{label.replace(' ', '-')}"
                )
                mutate(value)
                with self.assertRaises(v15.ResidentMediaV15Error):
                    validator.validate_static_evidence_plan(
                        value,
                        session_id=session_id,
                        expected_manifest=accepted.manifest(2),
                        consumed_start_permit_sha256=sha("permit:2"),
                    )
        self.assertEqual(authority_state(authority), before)

    def test_11_exact_scalar_aliases_refuse(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        mutations: tuple[tuple[str, Callable[[dict[str, Any]], None], Any], ...] = (
            (
                "bool output receipt",
                lambda value: value.__setitem__("output_receipt_id", True),
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
            ("integer permit", lambda value: None, int("1" * 64)),
        )
        for label, mutate, permit in mutations:
            with self.subTest(label=label):
                session_id, value = item_for(
                    accepted, ordinal=0, label=f"v15-{label.replace(' ', '-')}"
                )
                mutate(value)
                with self.assertRaises(v15.ResidentMediaV15Error):
                    validator.validate_static_evidence_plan(
                        value,
                        session_id=session_id,
                        expected_manifest=accepted.manifest(0),
                        consumed_start_permit_sha256=permit,
                    )
        self.assertEqual(authority_state(authority), before)

    def test_12_exact_record_method_refuses_without_state_change(self) -> None:
        accepted, authority, validator = make_validator()
        session_id, value = item_for(accepted, ordinal=0, label="v15-no-record")
        before = authority_state(authority)
        with self.assertRaisesRegex(v15.ResidentMediaV15Error, "no commit surface"):
            validator.validate_and_record_static_evidence(
                value,
                session_id=session_id,
                expected_manifest=accepted.manifest(0),
                consumed_start_permit_sha256=sha("permit:0"),
            )
        self.assertEqual(authority_state(authority), before)

    def test_13_module_global_and_closure_rebinding_fail_closed(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        original_global = v15._canonical_copy
        v15._canonical_copy = lambda *args, **kwargs: {}
        try:
            with self.assertRaisesRegex(v15.ResidentMediaV15Error, "execution seal"):
                plan(validator, accepted, 0, "v15-global-rebind")
        finally:
            v15._canonical_copy = original_global
        plan(validator, accepted, 0, "v15-global-restored")

        function = validator.validate_static_evidence_plan.__func__
        cells = list(function.__closure__ or ())
        index = next(
            index
            for index, cell in enumerate(cells)
            if cell.cell_contents is v15._preflight_complete_evidence_v15
        )
        original_cell = cells[index].cell_contents
        cells[index].cell_contents = lambda *args, **kwargs: ({}, {}, ())
        try:
            with self.assertRaisesRegex(v15.ResidentMediaV15Error, "execution seal"):
                plan(validator, accepted, 0, "v15-closure-rebind")
        finally:
            cells[index].cell_contents = original_cell
        plan(validator, accepted, 0, "v15-closure-restored")
        self.assertEqual(authority_state(authority), before)

    def test_14_predecessor_module_and_package_replacement_fail_closed(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)
        original_slot = sys.modules[v14.__name__]
        sys.modules[v14.__name__] = types.ModuleType(v14.__name__)
        try:
            with self.assertRaises(v15.ResidentMediaV15Error):
                plan(validator, accepted, 0, "v15-v14-slot")
        finally:
            sys.modules[v14.__name__] = original_slot
        core = sys.modules["Core"]
        original_attr = core.resident_media_voluntary_gate_v12
        core.resident_media_voluntary_gate_v12 = types.ModuleType(v12.__name__)
        try:
            with self.assertRaises(v15.ResidentMediaV15Error):
                plan(validator, accepted, 0, "v15-v12-package")
        finally:
            core.resident_media_voluntary_gate_v12 = original_attr
        plan(validator, accepted, 0, "v15-module-restored")
        self.assertEqual(authority_state(authority), before)

    def test_15_changed_snapshot_bytes_types_and_digest_refuse(self) -> None:
        _accepted, authority, raw, digest = snapshot_input()
        before = authority_state(authority)
        with self.assertRaises(v15.ResidentMediaV15Error):
            v15._open_disconnected_static_validation_harness_v15(
                person_id=PERSON,
                owner_selected_snapshot_bytes=raw + b" ",
                expected_snapshot_sha256=digest,
            )
        with self.assertRaises(v15.ResidentMediaV15Error):
            v15._open_disconnected_static_validation_harness_v15(
                person_id=PERSON,
                owner_selected_snapshot_bytes=bytearray(raw),
                expected_snapshot_sha256=digest,
            )
        with self.assertRaises(v15.ResidentMediaV15Error):
            v15._open_disconnected_static_validation_harness_v15(
                person_id=PERSON,
                owner_selected_snapshot_bytes=raw,
                expected_snapshot_sha256=int("1" * 64),
            )
        forged = copy.deepcopy(authority.snapshot_record)
        forged["catalog_sha256"] = "0" * 64
        forged_raw = canonical(forged)
        with self.assertRaises(v15.ResidentMediaV15Error):
            v15._open_disconnected_static_validation_harness_v15(
                person_id=PERSON,
                owner_selected_snapshot_bytes=forged_raw,
                expected_snapshot_sha256=hashlib.sha256(forged_raw).hexdigest(),
            )
        self.assertEqual(authority_state(authority), before)

    def test_16_parallel_static_validation_is_deterministic_and_no_commit(self) -> None:
        accepted, authority, validator = make_validator()
        before = authority_state(authority)

        def run(index: int) -> tuple[str, str]:
            result = envelope(
                validator, accepted, index % 4, f"v15-parallel-{index}"
            )
            return result[1], v15.decode_static_plan_envelope_v15(result)["status"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(run, range(24)))
        self.assertEqual(len(results), 24)
        self.assertTrue(
            all(
                status
                == "VALIDATED_IMMUTABLE_STATIC_PLAN_NOT_AUTHORITY_NOT_COMMITTED"
                for _digest, status in results
            )
        )
        self.assertEqual(authority_state(authority), before)

    def test_17_execution_binding_closes_v15_and_v14_chain(self) -> None:
        config_path = (
            ROOT
            / "RecoverySprint"
            / "continuation_20260811"
            / "resident_media_voluntary_v15"
            / "attempt_01"
            / "EXECUTION_BINDING_V15.json"
        )
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertTrue(config["v12_v13_and_v14_rejected"])
        self.assertTrue(config["immutable_byte_state_only"])
        self.assertTrue(config["v14_bootstrap_chain_required"])
        self.assertFalse(config["durable_commit_authorized"])
        self.assertFalse(config["live_media_authorized"])
        for entry in config["modules"]:
            path = ROOT / entry["relative_path"]
            data = path.read_bytes()
            self.assertEqual(len(data), entry["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
        v14._BOOTSTRAP_V14.verify()

    def test_18_summary_states_only_defensible_static_truth(self) -> None:
        summary = v15.static_contract_summary()
        self.assertEqual(
            summary["status"],
            "SEALED_NO_COMMIT_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT",
        )
        self.assertTrue(summary["v12_rejection_preserved"])
        self.assertTrue(summary["v13_rejection_preserved"])
        self.assertTrue(summary["v14_rejection_preserved"])
        self.assertTrue(summary["v14_mutable_catalog_stale_digest_path_removed"])
        self.assertTrue(summary["validator_retains_only_exact_immutable_tuple_scalars"])
        self.assertTrue(summary["plan_envelope_is_exact_builtin_tuple_pair"])
        self.assertTrue(
            summary[
                "plan_envelope_retains_only_canonical_bytes_and_derived_sha256"
            ]
        )
        self.assertTrue(
            summary["plan_digest_derived_from_envelope_bytes_before_emission"]
        )
        self.assertFalse(summary["caller_snapshot_is_protected_authority_truth"])
        self.assertFalse(summary["static_plan_is_durable_record"])
        self.assertFalse(summary["authority_protocol_calls_authorized"])
        self.assertFalse(summary["durable_commit_authorized"])
        self.assertTrue(summary["different_fresh_static_audit_required"])
        self.assertFalse(summary["production_routing_authorized"])
        self.assertFalse(summary["live_execution_allowed"])

    def test_19_import_and_validation_load_no_heavy_or_live_modules(self) -> None:
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
        plan(validator, accepted, 0, "v15-no-heavy")
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

    def test_20_strict_in_memory_compile(self) -> None:
        for relative in (
            "Core/resident_media_voluntary_gate_v15.py",
            "Testing/test_resident_media_voluntary_gate_v15.py",
        ):
            path = ROOT / relative
            compile(path.read_bytes(), str(path), "exec", dont_inherit=True, optimize=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
