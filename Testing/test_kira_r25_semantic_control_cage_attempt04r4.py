from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_r25_semantic_control_cage_diagnostic_v4r4.json"
)
HELPER = ROOT / "tools/kira_r25_mapped_pe_image_attestation_v4r4.py"
WRAPPER = ROOT / "tools/blender_diagnose_kira_r25_semantic_control_cage_v4r4.py"
CONTROLLER = ROOT / "tools/run_kira_r25_semantic_control_cage_v4r4.py"
R3_AUDIT = ROOT / (
    "RecoverySprint/continuation_20260809/"
    "kira_r25_semantic_cage_correspondence_static_preparation/"
    "attempt_04r3/INDEPENDENT_AUDIT.md"
)


def digest(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def build_synthetic_pe64() -> bytes:
    raw = bytearray(0xC00)
    raw[0:2] = b"MZ"
    struct.pack_into("<I", raw, 0x3C, 0x80)
    raw[0x80:0x84] = b"PE\x00\x00"
    coff = 0x84
    struct.pack_into("<HHIIIHH", raw, coff, 0x8664, 4, 0, 0, 0, 0xF0, 0x0022)
    optional = coff + 20
    struct.pack_into("<H", raw, optional, 0x20B)
    struct.pack_into("<III", raw, optional + 4, 0x200, 0x600, 0)
    struct.pack_into("<II", raw, optional + 16, 0x1000, 0x1000)
    struct.pack_into("<Q", raw, optional + 24, 0x140000000)
    struct.pack_into("<II", raw, optional + 32, 0x1000, 0x200)
    struct.pack_into("<HHHHHH", raw, optional + 40, 6, 0, 0, 0, 6, 0)
    struct.pack_into("<I", raw, optional + 52, 0)
    struct.pack_into("<II", raw, optional + 56, 0x5000, 0x400)
    struct.pack_into("<I", raw, optional + 64, 0)
    struct.pack_into("<HH", raw, optional + 68, 3, 0x0140)
    struct.pack_into(
        "<QQQQII", raw, optional + 72,
        0x100000, 0x1000, 0x100000, 0x1000, 0, 16,
    )
    struct.pack_into("<II", raw, optional + 112 + 5 * 8, 0x4000, 12)

    table = optional + 0xF0
    sections = (
        (b".text", 0x200, 0x1000, 0x200, 0x400, 0x60000020),
        (b".rdata", 0x200, 0x2000, 0x200, 0x600, 0x40000040),
        (b".data", 0x200, 0x3000, 0x200, 0x800, 0xC0000040),
        (b".reloc", 0x200, 0x4000, 0x200, 0xA00, 0x42000040),
    )
    for index, (name, vsize, va, rsize, pointer, flags) in enumerate(sections):
        offset = table + index * 40
        raw[offset:offset + 8] = name.ljust(8, b"\x00")
        struct.pack_into("<IIIIIIHHI", raw, offset + 8, vsize, va, rsize, pointer, 0, 0, 0, 0, flags)
    raw[0x400:0x600] = bytes((index * 17 + 3) % 256 for index in range(0x200))
    raw[0x600:0x800] = bytes((index * 29 + 5) % 256 for index in range(0x200))
    raw[0x800:0xA00] = bytes((index * 31 + 7) % 256 for index in range(0x200))
    struct.pack_into("<Q", raw, 0x410, 0x140001234)
    struct.pack_into("<IIHH", raw, 0xA00, 0x1000, 12, 0xA010, 0)
    return bytes(raw)


def materialize_loaded(helper, held: bytes, remote_base: int) -> bytes:
    plan = helper._parse_pe64(held)
    image = bytearray(plan["size_of_image"])
    image[:plan["size_of_headers"]] = held[:plan["size_of_headers"]]
    for section in plan["sections"]:
        start = section["virtual_address"]
        count = section["raw_size"]
        if count:
            source = section["raw_pointer"]
            image[start:start + count] = held[source:source + count]
    delta = remote_base - plan["preferred_image_base"]
    for relocation in plan["base_relocations"]:
        current = struct.unpack_from("<Q", image, relocation["rva"])[0]
        struct.pack_into(
            "<Q", image, relocation["rva"],
            (current + delta) & ((1 << 64) - 1),
        )
    return bytes(image)


class SemanticControlCageAttempt04R4StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.helper = load_module("_test_mapped_pe_attestation_v4r4", HELPER)
        cls.controller = load_module("_test_semantic_controller_v4r4", CONTROLLER)
        fake_bpy = types.ModuleType("bpy")
        prior = sys.modules.get("bpy")
        sys.modules["bpy"] = fake_bpy
        try:
            cls.wrapper = load_module("_test_semantic_wrapper_v4r4", WRAPPER)
        finally:
            if prior is None:
                sys.modules.pop("bpy", None)
            else:
                sys.modules["bpy"] = prior
        cls.helper_source = HELPER.read_text(encoding="utf-8")
        cls.wrapper_source = WRAPPER.read_text(encoding="utf-8")
        cls.controller_source = CONTROLLER.read_text(encoding="utf-8")
        cls.config_source = CONFIG.read_text(encoding="utf-8")
        cls.held_pe = build_synthetic_pe64()
        cls.remote_base = 0x180000000
        cls.loaded_pe = materialize_loaded(cls.helper, cls.held_pe, cls.remote_base)

    def attestation(self, loaded: bytes | None = None, **facts):
        image = self.loaded_pe if loaded is None else loaded
        plan = self.helper._parse_pe64(self.held_pe)
        values = {
            "remote_module_base": self.remote_base,
            "module_size_of_image": plan["size_of_image"],
            "module_entry_point": self.remote_base + plan["entry_point_rva"],
            "remote_reader": lambda rva, size: image[rva:rva + size],
        }
        values.update(facts)
        return self.helper._attest_loaded_main_image(self.held_pe, **values)

    def static_binding(self) -> dict:
        return {
            "state": self.wrapper.STATIC_NATIVE_STATE,
            "final_image_path": r"\\?\C:\Trusted\semantic-controller.exe",
            "bytes": len(self.held_pe),
            "sha256": hashlib.sha256(self.held_pe).hexdigest(),
            "volume_serial_number": 987654321,
            "file_id_128_hex": "2" * 32,
            "image_file_creation_time_100ns": 133800000000000001,
        }

    def sealed_config_and_row(self) -> tuple[dict, dict]:
        config = copy.deepcopy(self.config)
        config["status"] = self.wrapper.SEALED_STATUS
        config["native_semantic_controller_executable_binding"] = self.static_binding()
        pair = config["afes_v3r3_pair_binding"]
        pair["seal_status"] = "SEALED_FINAL_INDEPENDENTLY_ACCEPTED_V3R3_PAIR"
        pair["required_final_placeholders"] = []
        pair["expected_pair_and_analysis"] = {
            "pair_acceptance_frame_sha256": "3" * 64,
            "run_01_frame_sha256": "4" * 64,
            "run_02_frame_sha256": "5" * 64,
        }
        raw = json.dumps(
            config, ensure_ascii=False, allow_nan=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        row = {
            "path": self.wrapper.CONFIG_RELATIVE_PATH,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        }
        return config, row

    def observed_parent(self, binding: dict, attestation: dict) -> dict:
        device = r"\Device\HarddiskVolume7\Trusted\semantic-controller.exe"
        return {
            "process_id": 701,
            "process_creation_time_100ns": 133800000000000002,
            "windows_session_id": 7,
            "process_image_device_path": device,
            "mapped_image_device_path": device,
            "held_image_device_path": device,
            "final_image_path": binding["final_image_path"],
            "bytes": binding["bytes"], "sha256": binding["sha256"],
            "volume_serial_number": binding["volume_serial_number"],
            "file_id_128_hex": binding["file_id_128_hex"],
            "image_file_creation_time_100ns": binding[
                "image_file_creation_time_100ns"
            ],
            "mapped_image_attestation": attestation,
        }

    def audit_fixture(self, config: dict, config_row: dict, module) -> dict:
        rows = {
            label: module._row_for(relative)
            for label, relative in module.SUBJECT_PATHS.items()
        }
        rows["attempt04r4_config"] = copy.deepcopy(config_row)
        return {
            "schema": module.AUDIT_SCHEMA,
            "authoritative_decision": copy.deepcopy(module.AUDIT_DECISION),
            "auditor": copy.deepcopy(module.AUDITOR_IDENTITY),
            "subject_manifest": rows,
            "native_controller_executable_binding": copy.deepcopy(
                config["native_semantic_controller_executable_binding"]
            ),
            "native_runtime_lease_review": copy.deepcopy(module.AUDIT_LEASE_REVIEW),
            "findings": {"blocking": []},
            "truth_boundary": copy.deepcopy(module.AUDIT_TRUTH),
        }

    def runtime_lease(self) -> dict:
        return {
            "schema": self.wrapper.RUNTIME_LEASE_SCHEMA,
            "status": self.wrapper.RUNTIME_LEASE_STATUS,
            "authority_owner": self.wrapper.AUDIT_LEASE_REVIEW["authority_owner"],
            "lease_id": "a" * 64, "one_shot_nonce": "b" * 64,
            "capability_pipe_instance_id": "c" * 64,
            "persistent_exclusive_reservation_acquired": True,
            "reservation_persisted_before_child_resume": True,
            "lease_and_nonce_consumed_before_capability_write": True,
            "second_issue_or_replay_refused": True,
            "cross_child_reissue_refused": True,
            "child_wrapper_replay_ledger_authority": False,
        }

    def capability_fixture(self):
        config, row = self.sealed_config_and_row()
        attestation = self.attestation()
        observed = self.observed_parent(
            config["native_semantic_controller_executable_binding"], attestation
        )
        audit = self.audit_fixture(config, row, self.wrapper)
        audit_sha = hashlib.sha256(
            self.wrapper._canonical_json_bytes(audit)
        ).hexdigest()
        payload = {
            "schema": self.wrapper.CAPABILITY_SCHEMA,
            "status": self.wrapper.CAPABILITY_STATUS,
            "config_sha256": row["sha256"],
            "wrapper_sha256": config["bindings"]["execution_wrapper"]["sha256"],
            "native_controller_sha256": config[
                "native_semantic_controller_executable_binding"
            ]["sha256"],
            "accepted_audit_path": self.wrapper.AUDIT_RELATIVE_PATH,
            "accepted_audit_sha256": audit_sha,
            "accepted_audit_subject": audit,
            "native_controller_process_id": observed["process_id"],
            "native_controller_process_creation_time_100ns": observed[
                "process_creation_time_100ns"
            ],
            "native_controller_session_id": observed["windows_session_id"],
            "native_controller_process_image_device_path": observed[
                "process_image_device_path"
            ],
            "native_controller_mapped_image_device_path": observed[
                "mapped_image_device_path"
            ],
            "native_controller_mapped_image_attestation": attestation,
            "intended_child_process_id": 702,
            "intended_child_process_creation_time_100ns": 133800000000000003,
            "runtime_lease": self.runtime_lease(),
            "handles": {"capability": 801, "lock_input": 802, "result_output": 803},
            "input_frames": self.wrapper._expected_capability_inputs(
                config["afes_v3r3_pair_binding"]["expected_pair_and_analysis"]
            ),
            "one_frame_then_eof": True,
            "truth_boundary": copy.deepcopy(self.wrapper.CAPABILITY_TRUTH),
        }
        return config, row, observed, payload

    def validate_capability(self, config, row, observed, payload):
        real_row_for = self.wrapper._row_for

        def row_for(relative):
            if relative == self.wrapper.CONFIG_RELATIVE_PATH:
                return copy.deepcopy(row)
            return real_row_for(relative)

        with mock.patch.object(self.wrapper, "_row_for", side_effect=row_for):
            return self.wrapper._validate_capability(
                payload, capability_handle=801, lock_handle=802,
                result_handle=803, config_sha256=row["sha256"], config=config,
                observed_parent=observed, child_pid=702,
                child_creation_time_100ns=133800000000000003,
            )

    def test_01_identity_is_static_unsealed_and_execution_forbidden(self) -> None:
        self.assertEqual(
            self.config["schema"],
            "kira.avatar.r25.semantic_control_cage_diagnostic.v4r4",
        )
        self.assertEqual(self.config["status"], self.wrapper.PREPARATION_STATUS)
        self.assertFalse(self.config["scope"]["blender_execution_authorized"])
        self.assertFalse(self.config["scope"]["controller_execution_authorized"])
        self.assertFalse(self.config["scope"]["native_controller_exists"])

    def test_02_exact_placeholders_nulls_and_native_sentinels_remain(self) -> None:
        pair = self.config["afes_v3r3_pair_binding"]
        self.assertEqual(len(pair["required_final_placeholders"]), 16)
        self.assertEqual(self.config_source.count(": null"), 7)
        binding = self.config["native_semantic_controller_executable_binding"]
        self.assertEqual(set(binding), self.wrapper.STATIC_NATIVE_KEYS)
        self.assertTrue(
            all(
                type(value) is str and value.startswith("UNRESOLVED_")
                for value in binding.values()
            )
        )

    def test_03_all_04r3_subjects_and_rejection_are_byte_preserved(self) -> None:
        expected = {
            "config": (9691, "a61003e010fae6707f502894a8bc3c75d7796c93d3375cac15e8a9c4686dc6b3"),
            "adapter": (19457, "b954a47a7103a9bb4a119cf11c26ce997e16c04ef23069796db627a31b2df766"),
            "wrapper": (40465, "a6a8f849a394faa18999495b57a9ec5ffd530ece3ef9495e960a35e3b9f78d56"),
            "controller": (14868, "a31eaef5b6e75ea394d595a1ffd5455a080faf91a57cf9f635052efb7ba147c2"),
            "test": (27703, "f278186206cf05ead3017723633a6cc6dc06b99624ae916a2cbe33da99664f8c"),
            "checkpoint": (4354, "5d504c934e2320d96d65f1ce5dc9cba08ea9d2f732b9d6ab9c296f423b8182e1"),
            "independent_rejection_audit": (12259, "375cf534ffad3c12dee2f35ac2c86f826ba0de214c88c71afebe3902321316f1"),
        }
        for label, row in self.config[
            "preserved_attempt04r3_rejection_lineage"
        ].items():
            self.assertEqual(digest(ROOT / row["path"]), expected[label], label)
        self.assertEqual(digest(R3_AUDIT), expected["independent_rejection_audit"])

    def test_04_current_bindings_rehash_exactly(self) -> None:
        for label, row in self.config["bindings"].items():
            self.assertEqual(
                digest(ROOT / row["path"]), (row["bytes"], row["sha256"]), label
            )

    def test_05_relocation_aware_live_mapped_image_attestation_passes(self) -> None:
        attestation = self.attestation()
        self.assertEqual(attestation["base_relocation_count"], 1)
        self.assertEqual(attestation["relocation_delta"], 0x40000000)
        self.assertGreaterEqual(attestation["compared_region_count"], 3)
        self.assertGreater(attestation["compared_region_bytes"], 0)
        self.assertIs(
            self.helper._validate_attestation_shape(
                attestation, hashlib.sha256(self.held_pe).hexdigest()
            ),
            attestation,
        )

    def test_06_same_path_different_mapped_object_fails_before_capability(self) -> None:
        config, _ = self.sealed_config_and_row()
        held_device_path = r"\Device\HarddiskVolume7\Trusted\semantic-controller.exe"
        mapped_device_path = held_device_path
        self.assertEqual(held_device_path, mapped_device_path)
        hostile = bytearray(self.loaded_pe)
        hostile[0x1080] ^= 0x5A

        def hostile_same_path_query(parent_pid, helper):
            self.assertEqual(parent_pid, 701)
            plan = helper._parse_pe64(self.held_pe)
            return helper._attest_loaded_main_image(
                self.held_pe, remote_module_base=self.remote_base,
                module_size_of_image=plan["size_of_image"],
                module_entry_point=self.remote_base + plan["entry_point_rva"],
                remote_reader=lambda rva, size: bytes(hostile[rva:rva + size]),
            )

        with mock.patch.object(self.wrapper.os, "getppid", return_value=701), mock.patch.object(
            self.wrapper, "_pipe_server_pid", return_value=701
        ), mock.patch.object(
            self.wrapper, "_query_and_hold_mapped_parent_identity",
            side_effect=hostile_same_path_query,
        ), mock.patch.object(
            self.wrapper, "_adopt_pipe",
            side_effect=AssertionError("capability read must remain untouched"),
        ), mock.patch.object(
            self.wrapper, "_query_process_creation_time",
            side_effect=AssertionError("runtime child query must remain untouched"),
        ), mock.patch.object(
            self.wrapper, "_verified_runtime",
            side_effect=AssertionError("runtime/AFES/Blend must remain untouched"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "mapped_authority_region_bytes_mismatch"
            ):
                self.wrapper._authorize_mapped_parent_and_runtime_lease(
                    801, 802, 803, "7" * 64, config
                )

    def test_07_read_only_or_executable_mutation_and_header_mutation_fail(self) -> None:
        for rva in (0x90, 0x1080, 0x2080):
            with self.subTest(rva=hex(rva)):
                hostile = bytearray(self.loaded_pe)
                hostile[rva] ^= 0x01
                with self.assertRaisesRegex(
                    self.helper.MappedPeAttestationV4R4Error,
                    "mapped_authority_region_bytes_mismatch",
                ):
                    self.attestation(bytes(hostile))

    def test_08_writable_executable_or_mutable_iat_in_authority_fails(self) -> None:
        table = 0x80 + 4 + 20 + 0xF0
        wx = bytearray(self.held_pe)
        struct.pack_into("<I", wx, table + 36, 0xE0000020)
        with self.assertRaisesRegex(
            self.helper.MappedPeAttestationV4R4Error,
            "writable_executable_section_refused",
        ):
            self.helper._parse_pe64(bytes(wx))

        mutable_read_only = bytearray(self.held_pe)
        optional = 0x80 + 4 + 20
        struct.pack_into("<II", mutable_read_only, optional + 112 + 1 * 8, 0x2000, 0x20)
        struct.pack_into("<II", mutable_read_only, optional + 112 + 12 * 8, 0x2040, 0x20)
        with self.assertRaisesRegex(
            self.helper.MappedPeAttestationV4R4Error,
            "iat_not_in_nonexecutable_writable_section",
        ):
            self.helper._parse_pe64(bytes(mutable_read_only))

    def test_09_relocation_target_bounds_duplicates_and_overlap_fail(self) -> None:
        outside = bytearray(self.held_pe)
        struct.pack_into("<I", outside, 0xA00, 0x6000)
        with self.assertRaisesRegex(
            self.helper.MappedPeAttestationV4R4Error,
            "relocation_target_outside_section",
        ):
            self.helper._parse_pe64(bytes(outside))

        overlap = bytearray(self.held_pe)
        optional = 0x80 + 4 + 20
        struct.pack_into("<II", overlap, optional + 112 + 5 * 8, 0x4000, 14)
        struct.pack_into("<IIHHH", overlap, 0xA00, 0x1000, 14, 0xA010, 0xA014, 0)
        with self.assertRaisesRegex(
            self.helper.MappedPeAttestationV4R4Error,
            "overlapping_base_relocation_targets",
        ):
            self.helper._parse_pe64(bytes(overlap))

        reversed_raw_overlap = bytearray(self.held_pe)
        table = 0x80 + 4 + 20 + 0xF0
        struct.pack_into("<II", reversed_raw_overlap, table + 16, 0x400, 0x600)
        struct.pack_into(
            "<II", reversed_raw_overlap, table + 40 + 16, 0x400, 0x400
        )
        with self.assertRaisesRegex(
            self.helper.MappedPeAttestationV4R4Error,
            "raw_sections_overlap",
        ):
            self.helper._parse_pe64(bytes(reversed_raw_overlap))

    def test_10_reported_module_size_entrypoint_and_relocated_value_are_exact(self) -> None:
        plan = self.helper._parse_pe64(self.held_pe)
        cases = (
            {"module_size_of_image": plan["size_of_image"] + 0x1000},
            {"module_entry_point": self.remote_base + plan["entry_point_rva"] + 1},
        )
        for values in cases:
            with self.subTest(values=values):
                with self.assertRaises(self.helper.MappedPeAttestationV4R4Error):
                    self.attestation(**values)
        hostile = bytearray(self.loaded_pe)
        value = struct.unpack_from("<Q", hostile, 0x1010)[0]
        struct.pack_into("<Q", hostile, 0x1010, value + 1)
        with self.assertRaisesRegex(
            self.helper.MappedPeAttestationV4R4Error,
            "mapped_authority_region_bytes_mismatch",
        ):
            self.attestation(bytes(hostile))

    def test_11_attestation_digest_is_capability_bound_and_drift_fails(self) -> None:
        config, row, observed, payload = self.capability_fixture()
        self.assertIs(
            self.validate_capability(config, row, observed, payload), payload
        )
        hostile = copy.deepcopy(payload)
        hostile["native_controller_mapped_image_attestation"][
            "compared_region_manifest_sha256"
        ] = "f" * 64
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R4Error,
            "capability_runtime_binding_mismatch:native_controller_mapped_image_attestation",
        ):
            self.validate_capability(config, row, observed, hostile)

    def test_12_observed_attestation_content_hash_and_held_hash_are_exact(self) -> None:
        binding = self.static_binding()
        observed = self.observed_parent(binding, self.attestation())
        self.assertIs(
            self.wrapper._validate_mapped_parent_identity(
                binding, observed, 701, self.helper
            ),
            observed,
        )
        for mutation in ("content", "held"):
            hostile = copy.deepcopy(observed)
            if mutation == "content":
                hostile["mapped_image_attestation"]["compared_region_bytes"] += 1
                pattern = "content_sha256_mismatch"
            else:
                hostile["mapped_image_attestation"]["held_file_sha256"] = "f" * 64
                pattern = "held_sha256_mismatch"
            with self.assertRaisesRegex(
                self.helper.MappedPeAttestationV4R4Error, pattern
            ):
                self.wrapper._validate_mapped_parent_identity(
                    binding, hostile, 701, self.helper
                )
        inconsistent = copy.deepcopy(observed["mapped_image_attestation"])
        inconsistent["remote_entry_point"] += 1
        inconsistent.pop("attestation_content_sha256")
        inconsistent["attestation_content_sha256"] = hashlib.sha256(
            self.helper._canonical_json_bytes(inconsistent)
        ).hexdigest()
        with self.assertRaisesRegex(
            self.helper.MappedPeAttestationV4R4Error,
            "module_facts_inconsistent",
        ):
            self.helper._validate_attestation_shape(
                inconsistent, binding["sha256"]
            )

    def test_13_out_of_band_audit_remains_finite_and_acyclic(self) -> None:
        raw = CONFIG.read_bytes()
        config_sha = hashlib.sha256(raw).hexdigest()
        row = {
            "path": self.controller.CONFIG_RELATIVE_PATH,
            "bytes": len(raw), "sha256": config_sha,
        }
        audit = self.audit_fixture(self.config, row, self.controller)
        audit_raw = self.controller._canonical_json_bytes(audit)
        audit_sha = hashlib.sha256(audit_raw).hexdigest()
        self.assertEqual(
            self.controller._parse_out_of_band_audit(
                audit_raw, audit_sha, config_sha, self.config
            ),
            audit,
        )
        self.assertNotIn(audit_sha.encode("ascii"), raw)
        self.assertNotIn(self.controller.AUDIT_RELATIVE_PATH, self.config_source)

    def test_14_current_wrapper_and_plan_refuse_before_audit_or_runtime(self) -> None:
        config_sha = digest(CONFIG)[1]
        with self.assertRaisesRegex(
            self.wrapper.R25SemanticControlCageV4R4Error,
            "v4r4_static_preparation_is_not_execution_authority",
        ):
            self.wrapper._read_config(config_sha)
        with self.assertRaisesRegex(
            self.controller.SemanticCageV4R4PlanError,
            "static_v4r4_preparation_is_not_execution_authority",
        ):
            self.controller.build_sealed_execution_plan(
                config_sha, self.controller.AUDIT_RELATIVE_PATH, "0" * 64
            )

    def test_15_live_attestation_precedes_capability_runtime_afes_and_blend(self) -> None:
        authorize = self.wrapper_source.index(
            "def _authorize_mapped_parent_and_runtime_lease("
        )
        query = self.wrapper_source.index(
            "_query_and_hold_mapped_parent_identity(parent_pid, helper)", authorize
        )
        capability = self.wrapper_source.index("_adopt_pipe(capability_handle)", query)
        main = self.wrapper_source.index("def main()")
        runtime = self.wrapper_source.index("_verified_runtime(config)", main)
        bundle = self.wrapper_source.index("_read_bundle(", main)
        self.assertLess(query, capability)
        self.assertLess(capability, runtime)
        self.assertLess(runtime, bundle)
        for token in (
            "ReadProcessMemory", "GetModuleInformation", "SizeOfImage",
            "EntryPoint", "mapped_image_attestation",
        ):
            self.assertIn(token, self.wrapper_source)
        for token in (
            "IMAGE_SCN_MEM_EXECUTE", "IMAGE_SCN_MEM_WRITE",
            "IMAGE_REL_BASED_DIR64", "compared_region_manifest_sha256",
        ):
            self.assertIn(token, self.helper_source)

    def test_16_controller_is_inert_and_reserved_outputs_are_absent(self) -> None:
        tree = ast.parse(self.controller_source)
        imported = {
            alias.name for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        for forbidden in (
            "subprocess", "ctypes", "bpy", "secrets", "socket", "msvcrt"
        ):
            self.assertNotIn(forbidden, imported)
        for token in (
            "Popen(", "CreateProcess", "CreatePipe", "CreateNamedPipe",
            "open_osfhandle", "write_bytes(", "write_text(", "mkdir(",
            "save_as_mainfile", "token_hex(",
        ):
            self.assertNotIn(token, self.controller_source)
        values = (
            self.controller.AUDIT_RELATIVE_PATH,
            self.controller.OUTCOME_RELATIVE_PATH,
            self.controller.OUTPUT_RELATIVE_ROOT,
        )
        self.assertEqual(len(values), len(set(values)))
        self.assertTrue(all("attempt_04r4" in value for value in values))
        self.assertTrue(all(not (ROOT / value).exists() for value in values))


if __name__ == "__main__":
    unittest.main()
