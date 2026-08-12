"""Cache-free static and mocked-hostile checks for sealed V3r30 Stage 1."""

from __future__ import annotations

import argparse
import ast
import copy
import ctypes
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import types


ROOT = Path(__file__).resolve().parent
KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
CODEX_SCRATCH_ROOT = Path(r"C:\Users\robmc\Documents\Codex")
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
BLENDER_BYTES = 108687824
BLENDER_SHA256 = "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5"
HEX = set("0123456789abcdef")


class Failure(RuntimeError):
    pass


def check(condition: bool, label: str) -> None:
    if not condition:
        raise Failure(label)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read(path: Path) -> bytes:
    return path.read_bytes()


def strict_json(raw: bytes, label: str) -> dict[str, object]:
    check(raw.endswith(b"\n") and b"\r" not in raw and b"\0" not in raw, label + ":encoding")

    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            check(key not in value, label + ":duplicate:" + key)
            value[key] = item
        return value

    def nonfinite(value: str) -> None:
        raise Failure(label + ":nonfinite:" + value)

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=nonfinite)
    check(isinstance(value, dict), label + ":root")
    return value


def parse_upstream() -> tuple[list[list[str]], dict[str, bytes]]:
    raw = read(ROOT / "UPSTREAM_CLOSURE.tsv")
    check(raw.endswith(b"\n") and b"\r" not in raw, "upstream_encoding")
    lines = raw.decode("utf-8").splitlines()
    check(lines[0] == "scope\tpath\tbytes\tsha256\tstatus", "upstream_header")
    rows = [line.split("\t") for line in lines[1:]]
    check(len(rows) == 33 and all(len(row) == 5 for row in rows), "upstream_33")
    check(sum(row[0] == "v3r29_author" for row in rows) == 26, "upstream_author_26")
    check(sum(row[0] == "v3r29_rejection" for row in rows) == 7, "upstream_rejection_7")
    observed: dict[str, bytes] = {}
    for scope, relative, byte_text, sha, status in rows:
        check("\\" not in relative and ".." not in Path(relative).parts, "upstream_path:" + relative)
        check(len(sha) == 64 and set(sha) <= HEX and byte_text.isdecimal(), "upstream_grammar:" + relative)
        expected_status = "DO_NOT_MATERIALIZE_BUILD_RUN_V3R29_PRESERVED" if scope == "v3r29_author" else "REJECTION_PRESERVED"
        check(status == expected_status, "upstream_status:" + relative)
        raw_file = read(KIRA_ROOT.joinpath(*relative.split("/")))
        check(len(raw_file) == int(byte_text) and digest(raw_file) == sha, "upstream_hash:" + relative)
        observed[relative] = raw_file
    check(len(observed) == 33, "upstream_unique")
    nested_raw = next(raw for name, raw in observed.items() if name.endswith("/UPSTREAM_CLOSURE.tsv"))
    nested_lines = nested_raw.decode("utf-8").splitlines()
    check(nested_lines[0] == "scope\tpath\tbytes\tsha256\tstatus", "nested_upstream_header")
    nested_rows = [line.split("\t") for line in nested_lines[1:]]
    check(len(nested_rows) == 28 and all(len(row) == 5 for row in nested_rows), "nested_upstream_28")
    for scope, relative, byte_text, sha, status in nested_rows:
        expected_status = "DO_NOT_MATERIALIZE_BUILD_RUN_V3R28_PRESERVED" if scope == "v3r28_author" else "REJECTION_PRESERVED"
        check(status == expected_status and byte_text.isdecimal() and len(sha) == 64,
              "nested_upstream_grammar:" + relative)
        raw_file = read(KIRA_ROOT.joinpath(*relative.split("/")))
        check(len(raw_file) == int(byte_text) and digest(raw_file) == sha,
              "nested_upstream_hash:" + relative)
        observed[relative] = raw_file
    check(len(observed) == 61, "upstream_transitive_unique_61")
    deep_raw = next(
        raw for name, raw in observed.items()
        if "v3r28" in name and name.endswith("/UPSTREAM_CLOSURE.tsv")
    )
    deep_lines = deep_raw.decode("utf-8").splitlines()
    check(deep_lines[0] == "scope\tpath\tbytes\tsha256\tstatus", "deep_upstream_header")
    deep_rows = [line.split("\t") for line in deep_lines[1:]]
    check(len(deep_rows) == 17 and all(len(row) == 5 for row in deep_rows), "deep_upstream_17")
    for scope, relative, byte_text, sha, status in deep_rows:
        expected_status = "DO_NOT_RUN_V3R27_PRESERVED" if scope == "v3r27_author" else "REJECTION_PRESERVED"
        check(status == expected_status and byte_text.isdecimal() and len(sha) == 64,
              "deep_upstream_grammar:" + relative)
        raw_file = read(KIRA_ROOT.joinpath(*relative.split("/")))
        check(len(raw_file) == int(byte_text) and digest(raw_file) == sha,
              "deep_upstream_hash:" + relative)
        observed[relative] = raw_file
    check(len(observed) == 78, "upstream_transitive_unique_78")
    return rows, observed


def ast_checks() -> tuple[ast.Module, ast.Module]:
    worker_raw = read(ROOT / "blender_worker_v3r30.py")
    materializer_raw = read(ROOT / "materialize_stage2_v3r30.py")
    worker_tree = ast.parse(worker_raw, filename="blender_worker_v3r30.py")
    materializer_tree = ast.parse(materializer_raw, filename="materialize_stage2_v3r30.py")
    allowed_worker_imports = {"__future__", "argparse", "binascii", "hashlib", "json", "math", "os", "pathlib", "struct", "sys", "zlib", "bpy", "mathutils"}
    imports: set[str] = set()
    for node in ast.walk(worker_tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    check(imports == allowed_worker_imports, "worker_import_allowlist")
    allowed_materializer_imports = {
        "__future__", "argparse", "ctypes", "hashlib", "json", "os", "pathlib", "re", "stat",
    }
    materializer_imports: set[str] = set()
    for node in ast.walk(materializer_tree):
        if isinstance(node, ast.Import):
            materializer_imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            materializer_imports.add(node.module.split(".")[0])
    check(materializer_imports == allowed_materializer_imports, "materializer_static_only_imports")
    worker_text = worker_raw.decode("utf-8")
    materializer_text = materializer_raw.decode("utf-8")
    for forbidden in ("import_scene", "export_scene", "bpy.ops.wm.append", "bpy.ops.wm.link", "Sarah", "requests.", "socket.", "subprocess."):
        check(forbidden not in worker_text, "worker_forbidden_surface:" + forbidden)
    check(all(token not in materializer_text for token in ("subprocess", "os.system", "Popen(", "CreateProcess")), "materializer_no_process_launch")
    check("new_scratch_output_only" in materializer_text and
          "input_changed_during_materialization" in materializer_text and
          "input_changed_before_authority_consumption" in materializer_text,
          "materializer_publish_boundary")
    check("materialization_authority_already_consumed" in materializer_text and
          "MATERIALIZATION_LEDGER_ROOT" in materializer_text and
          "validate_ledger_lease" in materializer_text and
          "LEDGER_FILE_SEALED_SDDL" in materializer_text and
          "LEDGER_DIRECTORY_APPEND_ONLY_SDDL" in materializer_text and
          "require_anchor_parent_without_delete_child" in materializer_text and
          "EXPECTED_PROGRAM_DATA_SDDL" in materializer_text and
          "materialization_anchor_parent_grants_delete_child" in materializer_text,
          "materializer_durable_consumption")
    return worker_tree, materializer_tree


def load_worker() -> types.ModuleType:
    fake_bpy = types.ModuleType("bpy")
    fake_bpy.types = types.SimpleNamespace(Object=object, Material=object)
    fake_mathutils = types.ModuleType("mathutils")
    fake_mathutils.Vector = object
    prior_bpy = sys.modules.get("bpy")
    prior_mathutils = sys.modules.get("mathutils")
    sys.modules["bpy"] = fake_bpy
    sys.modules["mathutils"] = fake_mathutils
    module = types.ModuleType("v3r30_worker_static_mock")
    module.__file__ = str(ROOT / "blender_worker_v3r30.py")
    try:
        exec(compile(read(ROOT / "blender_worker_v3r30.py"), module.__file__, "exec"), module.__dict__)
    finally:
        if prior_bpy is None:
            del sys.modules["bpy"]
        else:
            sys.modules["bpy"] = prior_bpy
        if prior_mathutils is None:
            del sys.modules["mathutils"]
        else:
            sys.modules["mathutils"] = prior_mathutils
    return module


def expect_refusal(callable_value: object, label: str) -> None:
    try:
        callable_value()  # type: ignore[operator]
    except Exception:
        return
    raise Failure("hostile_false_accept:" + label)


def mocked_hostile_checks(spec: dict[str, object], frame: dict[str, object]) -> int:
    worker = load_worker()
    worker.validate_spec_contract(copy.deepcopy(spec))
    worker.validate_frame(copy.deepcopy(frame))
    count = 0

    def reject_spec(label: str, mutate: object) -> None:
        nonlocal count
        hostile = copy.deepcopy(spec)
        mutate(hostile)  # type: ignore[operator]
        expect_refusal(lambda: worker.validate_spec_contract(hostile), label)
        count += 1

    reject_spec("wrong_material", lambda value: value["objects"][1].__setitem__("material", "clinical_reproductive"))
    reject_spec("wrong_attribution", lambda value: value["objects"][1].__setitem__("sources", ["mri_pelvis_cc_by"]))
    reject_spec("wrong_primitive", lambda value: value["objects"][1].__setitem__("primitive", "TORUS"))
    reject_spec("missing_object", lambda value: value["objects"].pop())
    reject_spec("reversed_interval", lambda value: value["objects"][1].__setitem__("dimensions_interval", [[0.3, 0.1], [0.1, 0.2], [0.1, 0.2]]))
    reject_spec("truth_overclaim", lambda value: value["truth_tags"].__setitem__("functional_organ", True))

    def reject_frame(label: str, mutate: object) -> None:
        nonlocal count
        hostile = copy.deepcopy(frame)
        mutate(hostile)  # type: ignore[operator]
        expect_refusal(lambda: worker.validate_frame(hostile), label)
        count += 1

    reject_frame("missing_landmark", lambda value: value["landmarks"].pop("pelvic_floor_anchor"))
    reject_frame("reversed_left_right", lambda value: value["landmarks"].__setitem__("pelvis_left_lateral_anchor", [0.7, 0.0, 0.0]))
    reject_frame("nonfinite", lambda value: value["landmarks"].__setitem__("pelvic_floor_anchor", [0.0, 0.0, math.nan]))
    reject_frame("wrong_anterior_axis", lambda value: value["axis"].__setitem__("positive_y", "anatomical_posterior"))
    reject_frame("front_camera_wrong_side", lambda value: value["cameras"].__setitem__("front_clinical", [0.0, -1.55, 0.1]))
    reject_frame("weakened_gate", lambda value: value["gates"].__setitem__("minimum_pelvis_depth", 0.0))

    correct_bounds: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {}
    for row in spec["objects"]:  # type: ignore[index]
        component = row["id"]
        if "location" in row:
            center = tuple(float(value) for value in row["location"])
            dimensions = tuple((float(value[0]) + float(value[1])) / 2.0 for value in row["dimensions_interval"])
        else:
            center = tuple((float(value[0]) + float(value[1])) / 2.0 for value in row["location_interval"])
            dimensions = tuple((float(value[0]) + float(value[1])) / 2.0 for value in row["dimension_interval"])
        correct_bounds[component] = (
            tuple(center[index] - dimensions[index] / 2.0 for index in range(3)),
            tuple(center[index] + dimensions[index] / 2.0 for index in range(3)),
        )
    worker.validate_spatial_relations(correct_bounds)
    hostile_bounds = copy.deepcopy(correct_bounds)
    hostile_bounds["ovary_left_proxy"] = hostile_bounds["ovary_right_proxy"]
    expect_refusal(lambda: worker.validate_spatial_relations(hostile_bounds), "co_located_bilateral")
    count += 1
    hostile_bounds = copy.deepcopy(correct_bounds)
    hostile_bounds["bladder_proxy"] = hostile_bounds["uterus_proxy"]
    expect_refusal(lambda: worker.validate_spatial_relations(hostile_bounds), "co_located_anterior")
    count += 1
    hostile_bounds = copy.deepcopy(correct_bounds)
    hostile_bounds["rectum_reference_proxy"] = ((-0.01, 0.63, -0.01), (0.01, 0.64, 0.01))
    expect_refusal(lambda: worker.validate_spatial_relations(hostile_bounds), "outer_clearance")
    count += 1

    valid_coordinates = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    valid_edges = [(0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)]
    worker.validate_topology_values(4, valid_edges, [0.5, 0.5, 0.5, 0.5], valid_coordinates, "valid")
    expect_refusal(lambda: worker.validate_topology_values(1, [], [], [(0.0, 0.0, 0.0)], "one_vertex"), "one_vertex")
    count += 1
    expect_refusal(lambda: worker.validate_topology_values(4, valid_edges, [0.0], valid_coordinates, "zero_area"), "zero_area")
    count += 1
    expect_refusal(lambda: worker.validate_topology_values(4, [(0, 1), (2, 3)], [0.5], valid_coordinates, "disconnected"), "disconnected")
    count += 1
    return count


def mocked_staging_identity_checks() -> int:
    worker = load_worker()
    original = (
        worker.OUTPUT_ROOT, worker.BLEND_PATH, worker.RESULT_PATH,
        worker.RECEIPT_PATH, worker.RENDER_PATHS, worker.EXPECTED_STAGING_PATHS,
    )
    count = 0
    with tempfile.TemporaryDirectory(
        prefix="v3r30_worker_identity_", dir=CODEX_SCRATCH_ROOT,
    ) as temporary:
        root = Path(temporary)
        render_paths = {
            "front_clinical": root / "front_clinical.png",
            "right_clinical": root / "right_clinical.png",
            "iso_clinical": root / "iso_clinical.png",
            "iso_xray": root / "iso_xray.png",
        }
        blend = root / "proxy.blend"
        result = root / "WORKER_RESULT.json"
        receipt = root / "WORKER_RECEIPT.tsv"
        paths = (
            blend, render_paths["front_clinical"], render_paths["right_clinical"],
            render_paths["iso_clinical"], render_paths["iso_xray"], result, receipt,
        )
        for path in paths:
            path.touch(exist_ok=False)
        worker.OUTPUT_ROOT = root
        worker.BLEND_PATH = blend
        worker.RESULT_PATH = result
        worker.RECEIPT_PATH = receipt
        worker.RENDER_PATHS = render_paths
        worker.EXPECTED_STAGING_PATHS = paths
        try:
            identities = worker.validate_pre_reserved_outputs()
            check(len(identities) == 7 and len(set(identities.values())) == 7,
                  "worker_seven_unique_reserved_identities")

            replacement = result.with_suffix(".replacement")
            replacement.write_bytes(b"")
            result.unlink()
            replacement.rename(result)
            expect_refusal(
                lambda: worker.validate_reserved_identity(
                    result, identities[result], "substitution_probe",
                ),
                "reserved_path_substitution",
            )
            count += 1

            result.unlink()
            result.touch()
            identities = worker.validate_pre_reserved_outputs()
            alias = root / "alias.tmp"
            alias.touch()
            render_paths["front_clinical"].unlink()
            alias.unlink()
            try:
                import os as _os
                _os.link(blend, render_paths["front_clinical"])
                expect_refusal(worker.validate_pre_reserved_outputs, "reserved_hard_link")
                count += 1
            finally:
                render_paths["front_clinical"].unlink(missing_ok=True)
                render_paths["front_clinical"].touch()

            receipt.write_bytes(b"not-empty\n")
            expect_refusal(worker.validate_pre_reserved_outputs, "reserved_nonempty_initial")
            count += 1
            receipt.write_bytes(b"")

            identities = worker.validate_pre_reserved_outputs()
            probe = b"durable-reserved-write\n"
            worker.durable_reserved_bytes(receipt, probe, identities[receipt])
            check(receipt.read_bytes() == probe, "reserved_write_exact_readback")
            worker.validate_reserved_identity(
                receipt, identities[receipt], "reserved_write_terminal", minimum_bytes=len(probe),
            )
            count += 1
        finally:
            (
                worker.OUTPUT_ROOT, worker.BLEND_PATH, worker.RESULT_PATH,
                worker.RECEIPT_PATH, worker.RENDER_PATHS,
                worker.EXPECTED_STAGING_PATHS,
            ) = original
    return count


def c_checks() -> None:
    source = read(ROOT / "post_audit_native_anchor_template_v3r30.c").decode("utf-8")
    materializer = read(ROOT / "materialize_stage2_v3r30.py").decode("utf-8")
    worker = read(ROOT / "blender_worker_v3r30.py").decode("utf-8")
    header = read(ROOT / "POST_AUDIT_BINDINGS_TEMPLATE_v3r30.h").decode("utf-8")
    materialized_header = read(ROOT / "POST_AUDIT_BINDINGS_MATERIALIZED_ANALYSIS_v3r30.h").decode("utf-8")
    materialized_unit = read(ROOT / "materialized_analysis_translation_unit_v3r30.c").decode("utf-8")
    required = (
        "V3R30_MATERIALIZED 0", "V3R30_UNMATERIALIZED_STATIC_TEMPLATE",
        "V3R30_STAGE1_SEAL_SHA256", "V3R30_STAGE1_ALL_FILES_ROOT",
        "V3R30_MATERIALIZATION_CONSUMPTION_KEY",
        "V3R30_INSTALL_AUTHORITY_MANIFEST_SHA256",
        "V3R30_INSTALL_AUTHORITY_AUDITOR",
        "FILE_FLAG_OPEN_REPARSE_POINT", "GetFinalPathNameByHandleW", "FileIdInfo",
        "FILE_SHARE_READ", "CREATE_NEW", "FILE_FLAG_WRITE_THROUGH",
        "LEDGER_PENDING_CONSUMED", "LEDGER_SUCCESS_CONSUMED", "LEDGER_FAILURE_CONSUMED",
        "--background --factory-startup --disable-autoexec --python-exit-code 91",
        "CREATE_SUSPENDED", "AssignProcessToJobObject", "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE",
        "PROC_THREAD_ATTRIBUTE_HANDLE_LIST", "CREATE_UNICODE_ENVIRONMENT", "PYTHONNOUSERSITE=1",
        "WORKER_RECEIPT.tsv", "file_equals_memory", "FINAL_OUTPUT_MANIFEST.tsv",
        "front_clinical.png", "right_clinical.png", "iso_clinical.png", "iso_xray.png",
        "reserve_final_outputs", "reserve_worker_outputs", "WORKER_OUTPUT_COUNT",
        "worker_staging", "copy_to_reserved", "validate_worker_output",
        "regular_nonreparse_single_link", "revalidate_outputs", "close_outputs",
        "apply_worker_transaction_dacl", "WORKER_TRANSACTION_SDDL",
        "PROTECTED_DACL_SECURITY_INFORMATION",
    )
    for token in required:
        check(token in source or token in header, "native_required:" + token)
    for forbidden in ("ShellExecute", "WinExec", "system(", "URLDownload", "InternetOpen", "WSAStartup"):
        check(forbidden not in source, "native_forbidden:" + forbidden)
    check("isolated_environment, L\"C:\\\\Users\\\\robmc\\\\Kira\"" in source, "native_isolated_environment")
    check("finalize_outputs(capability_sha, worker_outputs, final_outputs," in source,
          "native_strict_finalization")
    reserve_worker = source.index("reserve_worker_outputs(worker_outputs)")
    seal_staging_directory = source.index("apply_worker_transaction_dacl(staging_directory)")
    launch_worker = source.index("launch_worker(capability_path")
    finalization = source.index("finalize_outputs(capability_sha, worker_outputs")
    success_ledger = source.index("ledger_update(ledger, LEDGER_SUCCESS_CONSUMED")
    worker_terminal = source.rindex("revalidate_outputs(worker_outputs, WORKER_OUTPUT_COUNT)")
    final_terminal = source.rindex("revalidate_final_outputs(final_outputs, manifest_sha)")
    worker_close = source.rindex("close_outputs(worker_outputs, WORKER_OUTPUT_COUNT)")
    final_close = source.rindex("close_outputs(final_outputs, FINAL_OUTPUT_COUNT)")
    check(reserve_worker < seal_staging_directory < launch_worker < finalization < success_ledger < worker_terminal,
          "worker_staging_reserved_before_blender_and_held_through_success")
    check(success_ledger < worker_terminal < worker_close and
          success_ledger < final_terminal < final_close,
          "native_handles_through_success_and_terminal_revalidation")
    check("FILE_SHARE_READ, NULL, CREATE_NEW" in source,
          "final_paths_reserved_without_write_or_delete_share")
    check("FILE_SHARE_READ | FILE_SHARE_WRITE" in source and
          '\\"staging_count\\":7,\\"staging_pre_reserved\\":true,\\"staging_single_link\\":true' in source,
          "worker_paths_pre_reserved_no_delete_share_capability_bound")
    for token in (
        "EXPECTED_STAGING_PATHS", "validate_pre_reserved_outputs",
        "validate_reserved_identity", "staging_identity_alias",
        "durable_reserved_bytes", 'path.open("r+b")',
    ):
        check(token in worker, "worker_reserved_identity_surface:" + token)
    check('path.open("xb")' not in worker and "worker_output_preexists" not in worker,
          "worker_consumes_pre_reserved_objects")
    check("apply_worker_transaction_dacl(outputs[index].handle)" in source and
          "apply_worker_transaction_dacl(staging_directory)" in source,
          "worker_files_and_directory_dacl_before_blender")
    for token in (
        "NTDLL.NtCreateFile", "def nt_create_relative(",
        "root_directory", "OBJ_DONT_REPARSE",
        "materialization_ledger_directory_relative_create",
        "materialization_ledger_directory_relative_open",
        "materialization_consumption_ledger_relative_create",
        "LEDGER_FILE_SEALED_CANONICAL_SDDL",
        "LEDGER_DIRECTORY_APPEND_ONLY_CANONICAL_SDDL",
        "materialization_ledger_sealed_dacl_readback",
    ):
        check(token in materializer, "materializer_handle_relative_surface:" + token)
    check("CreateDirectoryW(str(root)" not in materializer and
          "CreateFileW(\n            str(ledger_path)" not in materializer,
          "materializer_no_pathname_root_or_ledger_creation")
    check("V3R30_MATERIALIZED 1" in materialized_header and
          "V3R30_ANALYZER_MATERIALIZED_PATH 1" in materialized_header and
          "V3R30_INSTALL_AUTHORITY_MANIFEST_SHA256" in materialized_header and
          "V3R30_INSTALL_AUTHORITY_AUDITOR" in materialized_header and
          "POST_AUDIT_BINDINGS_MATERIALIZED_ANALYSIS_v3r30.h" in materialized_unit,
          "materialized_analysis_path_exact")
    analyzer = read(ROOT / "materialized_analysis_translation_unit_v3r30.nativecodeanalysis.xml")
    check(b"<DEFECTS></DEFECTS>" in analyzer and b"<DEFECT " not in analyzer,
          "materialized_analyzer_zero_defects")


def audit_grammar_hostile() -> int:
    module = types.ModuleType("v3r30_materializer_static")
    module.__file__ = str(ROOT / "materialize_stage2_v3r30.py")
    exec(compile(read(ROOT / "materialize_stage2_v3r30.py"), module.__file__, "exec"), module.__dict__)
    check(len(module.verify_upstream(read(ROOT / "UPSTREAM_CLOSURE.tsv"))) == 78,
          "materializer_direct_and_transitive_upstream_78")
    stage_root = "1" * 64
    seal_sha = "a" * 64
    all_files_root = "b" * 64
    auditor = "independent_v3r30_auditor_bounded"
    decision = {
        "schema": "kira.r25.medical_reference_proxy.v3r30.audit_a_decision.v1",
        "status": "ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY",
        "auditor_id": auditor,
        "accepted_stage1_package_root": stage_root,
        "accepted_stage1_seal_sha256": seal_sha,
        "accepted_stage1_all_files_root_sha256": all_files_root,
        "execution_authority": "MATERIALIZE_STAGE2_ONLY_NO_BLENDER",
        "candidate_executed": False,
        "blender_invoked": False,
        "maximum_materializations": 1,
        "stage2_requires_different_audit_b": True,
        "audit_scope": "CACHE_FREE_STATIC_SYNTAX_MOCKED_HOSTILE_AND_TRUSTED_BUILD_ANALYZE_ONLY",
        "materialization_consumption_key_sha256": module.materialization_key(
            stage_root, seal_sha, all_files_root, auditor,
        ),
    }
    decision_raw = (json.dumps(decision, sort_keys=True, separators=(",", ":")) + "\n").encode()
    audit_raw = ("row_id\tstatus\tevidence_sha256\tfinding\n" + "".join(
        f"{row_id}\tPASS\t{'2' * 64}\tstatic_pass\n" for row_id in module.AUDIT_ROW_IDS
    )).encode()
    checkpoint = b"# Bound independent checkpoint\n"
    artifacts = {"AUDIT_DECISION.json": decision_raw, "CHECKPOINT.md": checkpoint, "INDEPENDENT_AUDIT.tsv": audit_raw}
    manifest = ("path\tbytes\tsha256\n" + "".join(
        f"{name}\t{len(raw)}\t{digest(raw)}\n" for name, raw in sorted(artifacts.items())
    )).encode()
    snapshot = {"AUDIT_ARTIFACT_MANIFEST.tsv": manifest, **artifacts}
    module.parse_audit(snapshot, digest(manifest), stage_root, seal_sha,
                       all_files_root, auditor)
    count = 0
    changed_checkpoint = dict(snapshot)
    changed_checkpoint["CHECKPOINT.md"] += b"replacement\n"
    expect_refusal(lambda: module.parse_audit(changed_checkpoint, digest(manifest), stage_root,
                                              seal_sha, all_files_root, auditor),
                   "unbound_checkpoint_replacement")
    count += 1
    extra = dict(snapshot)
    extra["UNBOUND.txt"] = b"unbound\n"
    expect_refusal(lambda: module.parse_audit(extra, digest(manifest), stage_root,
                                              seal_sha, all_files_root, auditor),
                   "unbound_audit_file")
    count += 1
    expect_refusal(lambda: module.parse_audit(snapshot, "3" * 64, stage_root,
                                              seal_sha, all_files_root, auditor),
                   "external_audit_anchor")
    count += 1
    def reject_decision(label: str, key: str, value: object) -> None:
        nonlocal count
        changed_decision = copy.deepcopy(decision)
        changed_decision[key] = value
        changed_raw = (json.dumps(changed_decision, sort_keys=True,
                                  separators=(",", ":")) + "\n").encode()
        changed_artifacts = dict(artifacts)
        changed_artifacts["AUDIT_DECISION.json"] = changed_raw
        changed_manifest = ("path\tbytes\tsha256\n" + "".join(
            f"{name}\t{len(raw)}\t{digest(raw)}\n"
            for name, raw in sorted(changed_artifacts.items())
        )).encode()
        changed_snapshot = {"AUDIT_ARTIFACT_MANIFEST.tsv": changed_manifest,
                            **changed_artifacts}
        expect_refusal(lambda: module.parse_audit(
            changed_snapshot, digest(changed_manifest), stage_root,
            seal_sha, all_files_root, auditor,
        ), label)
        count += 1

    reject_decision("audit_cannot_authorize_blender", "execution_authority", "RUN_BLENDER")
    for key in (
        "schema", "status", "auditor_id", "accepted_stage1_package_root",
        "accepted_stage1_seal_sha256", "accepted_stage1_all_files_root_sha256",
        "execution_authority", "audit_scope", "materialization_consumption_key_sha256",
    ):
        reject_decision("string_type_" + key, key, 0)
    for key in ("candidate_executed", "blender_invoked", "stage2_requires_different_audit_b"):
        reject_decision("bool_int_alias_" + key, key, int(bool(decision[key])))
    reject_decision("int_bool_alias_maximum", "maximum_materializations", True)
    reject_decision("int_float_alias_maximum", "maximum_materializations", 1.0)
    reject_decision("int_string_maximum", "maximum_materializations", "1")
    expect_refusal(lambda: module.parse_audit(snapshot, digest(manifest), stage_root,
                                              "c" * 64, all_files_root, auditor),
                   "external_stage1_seal_anchor")
    count += 1
    expect_refusal(lambda: module.parse_audit(snapshot, digest(manifest), stage_root,
                                              seal_sha, "d" * 64, auditor),
                   "external_stage1_all_files_anchor")
    count += 1
    return count


def install_authority_grammar_hostile() -> int:
    module = types.ModuleType("v3r30_install_authority_static")
    module.__file__ = str(ROOT / "materialize_stage2_v3r30.py")
    exec(compile(read(ROOT / "materialize_stage2_v3r30.py"), module.__file__, "exec"),
         module.__dict__)
    audit_sha = "a" * 64
    audit_auditor = "independent_v3r30_audit_a_probe"
    install_auditor = "independent_v3r30_programdata_install_probe"
    decision = {
        "schema": "kira.r25.medical_reference_proxy.v3r30.programdata_install_authority.v1",
        "status": "AUTHORIZE_EXACT_PROGRAMDATA_LEDGER_DIRECTORY_FOR_ONE_MATERIALIZATION_ONLY_NO_BUILD_NO_BLENDER",
        "auditor_id": install_auditor,
        "accepted_audit_a_manifest_sha256": audit_sha,
        "accepted_audit_a_auditor_id": audit_auditor,
        "program_data_anchor": str(module.PROGRAM_DATA_ANCHOR),
        "program_data_anchor_dacl_sddl": module.EXPECTED_PROGRAM_DATA_SDDL,
        "program_data_anchor_delete_child_access": "REFUSED_ACCESS_DENIED",
        "ledger_root": str(module.MATERIALIZATION_LEDGER_ROOT),
        "ledger_file_atomic_creation_dacl_sddl": module.LEDGER_FILE_SEALED_SDDL,
        "ledger_file_canonical_readback_dacl_sddl": module.LEDGER_FILE_SEALED_CANONICAL_SDDL,
        "ledger_directory_atomic_creation_append_only_dacl_sddl": module.LEDGER_DIRECTORY_APPEND_ONLY_SDDL,
        "ledger_directory_canonical_readback_dacl_sddl": module.LEDGER_DIRECTORY_APPEND_ONLY_CANONICAL_SDDL,
        "ntcreatefile_rootdirectory_relative_directory_and_file_required": True,
        "final_owner_rights_dacls_at_atomic_creation_required": True,
        "execution_authority": "INSTALL_ONE_LEDGER_DIRECTORY_FOR_MATERIALIZATION_ONLY_NO_BUILD_NO_BLENDER",
        "program_data_directory_created_by_auditor": False,
        "candidate_executed": False,
        "maximum_program_data_directory_creations": 1,
        "maximum_materializations": 1,
        "maximum_native_builds": 0,
        "maximum_blender_invocations": 0,
        "different_audit_b_still_required": True,
    }
    decision_raw = (json.dumps(
        decision, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ) + "\n").encode()
    checkpoint = b"# Independent ProgramData install-authority checkpoint\n"
    audit_raw = (
        "row_id\tstatus\tevidence_sha256\tfinding\n" + "".join(
            f"{row}\tPASS\t{'9' * 64}\tstatic_pass\n" for row in (
                "01_programdata_target_absent",
                "02_programdata_anchor_exact_identity",
                "03_programdata_anchor_exact_dacl",
                "04_programdata_delete_child_access_refused",
                "05_owner_rights_atomic_final_dacl_policy",
                "06_handle_relative_atomic_creation_policy",
                "07_zero_build_blender_authority",
            )
        )
    ).encode()
    artifacts = {
        "CHECKPOINT.md": checkpoint,
        "INSTALL_AUTHORITY_AUDIT.tsv": audit_raw,
        "INSTALL_AUTHORITY_DECISION.json": decision_raw,
    }

    def snapshot_for(values: dict[str, bytes]) -> tuple[dict[str, bytes], str]:
        manifest = (
            "path\tbytes\tsha256\n" + "".join(
                f"{name}\t{len(raw)}\t{digest(raw)}\n"
                for name, raw in sorted(values.items())
            )
        ).encode()
        return {"INSTALL_AUTHORITY_MANIFEST.tsv": manifest, **values}, digest(manifest)

    snapshot, manifest_sha = snapshot_for(artifacts)
    module.parse_install_authority(
        snapshot, manifest_sha, install_auditor, audit_sha, audit_auditor,
    )
    count = 0
    expect_refusal(
        lambda: module.parse_install_authority(
            snapshot, manifest_sha, audit_auditor, audit_sha, audit_auditor,
        ),
        "install_authority_same_as_audit_a",
    )
    count += 1
    expect_refusal(
        lambda: module.parse_install_authority(
            snapshot, manifest_sha,
            "codex_r25_medical_reference_proxy_v3r29_two_stage_author",
            audit_sha, audit_auditor,
        ),
        "install_authority_same_as_v3r29_author",
    )
    count += 1

    changed = copy.deepcopy(decision)
    changed["program_data_anchor_dacl_sddl"] += "(A;;FA;;;WD)"
    changed_artifacts = dict(artifacts)
    changed_artifacts["INSTALL_AUTHORITY_DECISION.json"] = (
        json.dumps(changed, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    changed_snapshot, changed_sha = snapshot_for(changed_artifacts)
    expect_refusal(
        lambda: module.parse_install_authority(
            changed_snapshot, changed_sha, install_auditor,
            audit_sha, audit_auditor,
        ),
        "install_authority_changed_dacl",
    )
    count += 1

    changed = copy.deepcopy(decision)
    changed["maximum_materializations"] = True
    changed_artifacts = dict(artifacts)
    changed_artifacts["INSTALL_AUTHORITY_DECISION.json"] = (
        json.dumps(changed, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    changed_snapshot, changed_sha = snapshot_for(changed_artifacts)
    expect_refusal(
        lambda: module.parse_install_authority(
            changed_snapshot, changed_sha, install_auditor,
            audit_sha, audit_auditor,
        ),
        "install_authority_bool_int_alias",
    )
    count += 1

    extra = dict(snapshot)
    extra["UNBOUND.txt"] = b"unbound\n"
    expect_refusal(
        lambda: module.parse_install_authority(
            extra, manifest_sha, install_auditor, audit_sha, audit_auditor,
        ),
        "install_authority_unbound_file",
    )
    count += 1
    return count


def materialization_consumption_hostile() -> int:
    module = types.ModuleType("v3r30_materializer_consumption_static")
    module.__file__ = str(ROOT / "materialize_stage2_v3r30.py")
    exec(compile(read(ROOT / "materialize_stage2_v3r30.py"), module.__file__, "exec"),
         module.__dict__)
    stage_root = "1" * 64
    seal_sha = "2" * 64
    all_files_root = "3" * 64
    audit_sha = "4" * 64
    auditor = "independent_v3r30_consumption_probe"
    output = CODEX_SCRATCH_ROOT / "DO_NOT_CREATE_v3r30_stage2_output_probe"
    key, raw = module.materialization_ledger_record(
        stage_root, seal_sha, all_files_root, audit_sha, auditor,
        "5" * 64, "independent_v3r30_install_authority_probe", output,
    )
    ledger_record = module.strict_json(raw, "test_materialization_ledger")
    check(ledger_record["ledger_directory_nt_rootdirectory_relative_open_or_create"] is True and
          ledger_record["ledger_file_nt_rootdirectory_relative_create"] is True and
          ledger_record["final_owner_rights_dacls_supplied_during_atomic_create"] is True,
          "consumption_record_handle_relative_boundary")
    package_before = module.directory_snapshot(ROOT)
    check(module.consume_materialization_authority.__kwdefaults__ is None,
          "production_ledger_has_no_test_or_acl_override")
    check(module.consume_materialization_authority.__code__.co_argcount == 2 and
          module.consume_materialization_authority.__code__.co_varnames[:2] == ("key", "raw"),
          "production_ledger_fixed_root_signature")
    parent_handle = module.require_anchor_parent_without_delete_child(
        module.PROGRAM_DATA_ANCHOR,
    )
    try:
        check(module.handle_dacl_sddl(parent_handle) == module.EXPECTED_PROGRAM_DATA_SDDL,
              "production_anchor_exact_dacl")
    finally:
        module.close_handle(parent_handle)
    with tempfile.TemporaryDirectory(
        prefix="v3r30_atomic_owner_rights_", dir=CODEX_SCRATCH_ROOT,
    ) as atomic_temporary:
        atomic_parent, _ = module.open_directory_handle(
            Path(atomic_temporary), False, True,
        )
        try:
            atomic_directory, directory_information = module.nt_create_relative(
                atomic_parent, "sealed_directory_probe",
                module.FILE_LIST_DIRECTORY | module.FILE_ADD_FILE |
                module.FILE_ADD_SUBDIRECTORY | module.FILE_READ_ATTRIBUTES |
                module.READ_CONTROL | module.WRITE_DAC | module.SYNCHRONIZE,
                module.FILE_SHARE_READ | module.FILE_SHARE_WRITE,
                module.FILE_CREATE,
                module.FILE_DIRECTORY_FILE | module.FILE_SYNCHRONOUS_IO_NONALERT |
                module.FILE_OPEN_REPARSE_POINT_OPTION,
                sddl=module.LEDGER_DIRECTORY_APPEND_ONLY_SDDL,
                label="test_atomic_directory_dacl",
            )
            try:
                check(directory_information == module.FILE_CREATED and
                      module.handle_dacl_sddl(atomic_directory) ==
                      module.LEDGER_DIRECTORY_APPEND_ONLY_CANONICAL_SDDL,
                      "atomic_directory_final_dacl_at_create")
                nested_file, nested_information = module.nt_create_relative(
                    atomic_directory, "nested_creation_probe",
                    module.GENERIC_READ | module.GENERIC_WRITE |
                    module.SYNCHRONIZE,
                    module.FILE_SHARE_READ, module.FILE_CREATE,
                    module.FILE_NON_DIRECTORY_FILE |
                    module.FILE_SYNCHRONOUS_IO_NONALERT |
                    module.FILE_OPEN_REPARSE_POINT_OPTION,
                    sddl="D:P(A;;FA;;;OW)",
                    label="test_atomic_directory_creation_handle_child",
                )
                try:
                    check(nested_information == module.FILE_CREATED,
                          "atomic_directory_creation_handle_add_file")
                finally:
                    module.close_handle(nested_file)
                (Path(atomic_temporary) / "sealed_directory_probe" /
                 "nested_creation_probe").unlink()
            finally:
                module.close_handle(atomic_directory)
            reopened_directory, reopened_directory_information = module.nt_create_relative(
                atomic_parent, "sealed_directory_probe",
                module.FILE_LIST_DIRECTORY | module.FILE_READ_ATTRIBUTES |
                module.READ_CONTROL | module.SYNCHRONIZE,
                module.FILE_SHARE_READ | module.FILE_SHARE_WRITE,
                module.FILE_OPEN,
                module.FILE_DIRECTORY_FILE | module.FILE_SYNCHRONOUS_IO_NONALERT |
                module.FILE_OPEN_REPARSE_POINT_OPTION,
                sddl=None, label="test_reopen_atomic_directory_dacl",
            )
            try:
                check(reopened_directory_information == module.FILE_OPENED and
                      module.handle_dacl_sddl(reopened_directory) ==
                      module.LEDGER_DIRECTORY_APPEND_ONLY_CANONICAL_SDDL,
                      "atomic_directory_readonly_reopen")
            finally:
                module.close_handle(reopened_directory)
            atomic_file, file_information = module.nt_create_relative(
                atomic_parent, "sealed_file_probe",
                module.GENERIC_READ | module.GENERIC_WRITE |
                module.WRITE_DAC | module.SYNCHRONIZE,
                module.FILE_SHARE_READ, module.FILE_CREATE,
                module.FILE_NON_DIRECTORY_FILE |
                module.FILE_SYNCHRONOUS_IO_NONALERT |
                module.FILE_OPEN_REPARSE_POINT_OPTION |
                module.FILE_WRITE_THROUGH_OPTION,
                sddl=module.LEDGER_FILE_SEALED_SDDL,
                label="test_atomic_file_dacl",
            )
            try:
                check(file_information == module.FILE_CREATED and
                      module.handle_dacl_sddl(atomic_file) ==
                      module.LEDGER_FILE_SEALED_CANONICAL_SDDL,
                      "atomic_file_final_dacl_at_create")
                probe_raw = b"atomic-owner-rights-create\n"
                probe_buffer = ctypes.create_string_buffer(probe_raw)
                probe_wrote = module.wintypes.DWORD()
                check(module.KERNEL32.WriteFile(
                    module.wintypes.HANDLE(atomic_file), probe_buffer,
                    len(probe_raw), ctypes.byref(probe_wrote), None,
                ) and probe_wrote.value == len(probe_raw) and
                      module.KERNEL32.FlushFileBuffers(
                          module.wintypes.HANDLE(atomic_file)
                      ), "atomic_file_creation_handle_remains_writable")
            finally:
                module.close_handle(atomic_file)
            atomic_file_path = Path(atomic_temporary) / "sealed_file_probe"
            atomic_alias_path = Path(atomic_temporary) / "sealed_file_alias_probe"
            import os as _atomic_os
            expect_refusal(
                lambda: _atomic_os.link(atomic_file_path, atomic_alias_path),
                "atomic_file_final_dacl_hardlink_refusal",
            )
            check(not atomic_alias_path.exists(),
                  "atomic_file_final_dacl_no_hardlink_alias")
            reopened_file, reopened_file_information = module.nt_create_relative(
                atomic_parent, "sealed_file_probe",
                module.GENERIC_READ | module.SYNCHRONIZE,
                module.FILE_SHARE_READ | module.FILE_SHARE_WRITE |
                module.FILE_SHARE_DELETE, module.FILE_OPEN,
                module.FILE_NON_DIRECTORY_FILE |
                module.FILE_SYNCHRONOUS_IO_NONALERT |
                module.FILE_OPEN_REPARSE_POINT_OPTION,
                sddl=None, label="test_reopen_atomic_file_dacl",
            )
            try:
                check(reopened_file_information == module.FILE_OPENED and
                      module.handle_dacl_sddl(reopened_file) ==
                      module.LEDGER_FILE_SEALED_CANONICAL_SDDL and
                      module.read_ledger_handle(reopened_file, len(probe_raw)) ==
                      probe_raw, "atomic_file_readonly_reopen")
            finally:
                module.close_handle(reopened_file)
        finally:
            module.close_handle(atomic_parent)
    with tempfile.TemporaryDirectory(
        prefix="v3r30_consumption_", dir=CODEX_SCRATCH_ROOT,
    ) as temporary:
        temporary_root = Path(temporary)
        ledger_root = temporary_root / "authority_ledger"
        lease = module.exercise_consumption_handles_test_only(
            ledger_root, key, raw,
        )
        try:
            module.validate_ledger_lease(lease)
            check(lease.path.is_file() and read(lease.path) == raw,
                  "consumption_ledger_durable_readback")

            moved_root = temporary_root / "authority_ledger_moved"
            expect_refusal(lambda: ledger_root.rename(moved_root),
                           "held_ledger_directory_rename")
            check(ledger_root.is_dir() and not moved_root.exists(),
                  "held_ledger_directory_path_retained")

            moved_file = temporary_root / "moved_ledger.json"
            expect_refusal(lambda: lease.path.replace(moved_file),
                           "held_ledger_file_replacement")
            check(lease.path.is_file() and not moved_file.exists(),
                  "held_ledger_file_path_retained")

            alias = temporary_root / "ledger_alias.json"
            import os as _os
            _os.link(lease.path, alias)
            try:
                expect_refusal(lambda: module.validate_ledger_lease(lease),
                               "ledger_hard_link_added")
            finally:
                alias.unlink()
            module.validate_ledger_lease(lease)

            generated = temporary_root / "removable_generated_package"
            generated.mkdir()
            generated.rmdir()
            generated.mkdir()
            generated.rmdir()
            expect_refusal(
                lambda: module.exercise_consumption_handles_test_only(
                    ledger_root, key, raw,
                ),
                "retry_after_generated_directory_delete_recreate",
            )
            module.validate_ledger_lease(lease)
        finally:
            lease.close()
        existing_handles, existing_created = module.ensure_ledger_root(
            ledger_root, temporary_root, False,
        )
        try:
            check(existing_created is False,
                  "sealed_style_existing_root_traverse_open")
        finally:
            for handle in reversed(existing_handles):
                module.close_handle(handle)
    check(module.directory_snapshot(ROOT) == package_before,
          "installed_layout_postseal_read_only")
    return 4


def verify_seal() -> int:
    seal = strict_json(read(ROOT / "STATIC_SEAL_MANIFEST.json"), "seal")
    check(seal["schema"] == "kira.r25.medical_reference_proxy.v3r30.static_seal.v1", "seal_schema")
    check(seal["status"] == "SEALED_STATIC_TWO_STAGE_AUTHOR_CANDIDATE_PENDING_DIFFERENT_AUDIT_A", "seal_status")
    check(seal["execution_authority"] == "NONE" and seal["candidate_executed"] is False, "seal_boundary")
    rows: list[tuple[str, int, str]] = []
    for subject in seal["subjects"]:
        path = subject["path"]
        raw = read(ROOT / path)
        check(len(raw) == subject["bytes"] and digest(raw) == subject["sha256"], "seal_subject:" + path)
        rows.append((path, len(raw), digest(raw)))
    check([row[0] for row in rows] == sorted(row[0] for row in rows), "seal_order")
    canonical = b"".join(f"{path}\t{byte_count}\t{sha}\n".encode() for path, byte_count, sha in rows)
    check(len(rows) == seal["subject_count"] and len(canonical) == seal["canonical_bytes"], "seal_counts")
    check(digest(canonical) == seal["package_root_sha256"], "seal_root")
    module = types.ModuleType("v3r30_materializer_postseal")
    module.__file__ = str(ROOT / "materialize_stage2_v3r30.py")
    exec(compile(read(ROOT / "materialize_stage2_v3r30.py"), module.__file__, "exec"), module.__dict__)
    snapshot = module.directory_snapshot(ROOT)
    seal_sha = digest(snapshot["STATIC_SEAL_MANIFEST.json"])
    all_files_root = digest(module.inventory_canonical(snapshot))
    bound, _ = module.parse_stage1(snapshot, seal["package_root_sha256"],
                                   seal_sha, all_files_root)
    check(len(bound) == seal["subject_count"] and len(snapshot) == seal["subject_count"] + 1, "materializer_stage1_parse")
    auditor = "independent_v3r30_header_generation_probe"
    audit_manifest_sha = "f" * 64
    consumption_key, consumption_raw = module.materialization_ledger_record(
        seal["package_root_sha256"], seal_sha, all_files_root,
        audit_manifest_sha, auditor, "e" * 64,
        "independent_v3r30_install_authority_probe",
        module.EXPECTED_MATERIALIZATION_DIR,
    )
    generated_header = module.build_header(
        seal["package_root_sha256"], seal_sha, all_files_root,
        audit_manifest_sha, auditor, "e" * 64,
        "independent_v3r30_install_authority_probe", consumption_key,
        module.MATERIALIZATION_LEDGER_ROOT /
            ("V3R30_MATERIALIZATION_CONSUMED_" + consumption_key + ".json"),
        consumption_raw, snapshot, bound,
        module.verify_upstream(bound["UPSTREAM_CLOSURE.tsv"]),
        [("AUDIT_ARTIFACT_MANIFEST.tsv", b"static_header_probe\n")],
        [("INSTALL_AUTHORITY_MANIFEST.tsv", b"install_authority_probe\n")],
    )
    check(b"#define V3R30_MATERIALIZED 1" in generated_header and
          seal_sha.encode() in generated_header and
          all_files_root.encode() in generated_header and
          consumption_key.encode() in generated_header,
          "materializer_generated_header_external_anchors")
    hostile_authority = copy.deepcopy(seal)
    hostile_authority["audit_a_maximum_authority"] = "RUN_BLENDER"
    hostile_raw = (json.dumps(hostile_authority, sort_keys=True, indent=2,
                              allow_nan=False) + "\n").encode()
    hostile_snapshot = dict(snapshot)
    hostile_snapshot["STATIC_SEAL_MANIFEST.json"] = hostile_raw
    expect_refusal(lambda: module.parse_stage1(
        hostile_snapshot, seal["package_root_sha256"], seal_sha, all_files_root,
    ), "seal_mutation_under_old_external_anchors")
    hostile_type = copy.deepcopy(seal)
    hostile_type["candidate_executed"] = 0
    hostile_type_raw = (json.dumps(hostile_type, sort_keys=True, indent=2,
                                   allow_nan=False) + "\n").encode()
    hostile_type_snapshot = dict(snapshot)
    hostile_type_snapshot["STATIC_SEAL_MANIFEST.json"] = hostile_type_raw
    expect_refusal(lambda: module.parse_stage1(
        hostile_type_snapshot,
        seal["package_root_sha256"],
        digest(hostile_type_raw),
        digest(module.inventory_canonical(hostile_type_snapshot)),
    ), "seal_bool_int_alias_even_with_reanchored_mutant")
    hostile_count = copy.deepcopy(seal)
    hostile_count["maximum_future_blender_invocations_after_both_acceptances"] = True
    hostile_count_raw = (json.dumps(hostile_count, sort_keys=True, indent=2,
                                    allow_nan=False) + "\n").encode()
    hostile_count_snapshot = dict(snapshot)
    hostile_count_snapshot["STATIC_SEAL_MANIFEST.json"] = hostile_count_raw
    expect_refusal(lambda: module.parse_stage1(
        hostile_count_snapshot,
        seal["package_root_sha256"],
        digest(hostile_count_raw),
        digest(module.inventory_canonical(hostile_count_snapshot)),
    ), "seal_int_bool_alias_even_with_reanchored_mutant")
    return 3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("PreSeal", "PostSeal"))
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    _, upstream = parse_upstream()
    check(BLENDER.is_file() and BLENDER.stat().st_size == BLENDER_BYTES and digest(read(BLENDER)) == BLENDER_SHA256, "blender_identity")
    spec = strict_json(read(ROOT / "PROXY_SPEC.json"), "spec")
    frame = strict_json(read(ROOT / "NORMALIZED_REFERENCE_FRAME.json"), "frame")
    worker_constants = load_worker()
    check(worker_constants.SEALED_SPEC_SHA256 == digest(read(ROOT / "PROXY_SPEC.json")) and
          worker_constants.SEALED_FRAME_SHA256 == digest(read(ROOT / "NORMALIZED_REFERENCE_FRAME.json")),
          "worker_sealed_spec_frame_hashes")
    contract = strict_json(read(ROOT / "CONTRACT.json"), "contract")
    build_plan = strict_json(read(ROOT / "STAGE2_NATIVE_BUILD_PLAN.json"), "build_plan")
    ast_checks()
    hostile_worker = mocked_hostile_checks(spec, frame)
    hostile_worker_staging = mocked_staging_identity_checks()
    hostile_audit = audit_grammar_hostile()
    hostile_install_authority = install_authority_grammar_hostile()
    hostile_consumption = materialization_consumption_hostile()
    c_checks()
    license_raw = next(raw for name, raw in upstream.items() if name.endswith("ATTRIBUTION_LICENSE_MANIFEST.tsv"))
    skeleton_raw = next(raw for name, raw in upstream.items() if name.endswith("SKELETON_136_MAPPING_PLAN.tsv"))
    check(b"QUARANTINE" in license_raw and b"CC BY" in license_raw, "license_quarantines")
    skeleton_lines = skeleton_raw.decode("utf-8").splitlines()
    check(len(skeleton_lines) - 1 == 136 and all("UNMAPPED" in line for line in skeleton_lines[1:]), "skeleton_136_unmapped")
    check(contract["execution_authority"] == "NONE" and contract["stage_a_truth"]["proxy_objects_exact"] == 9, "contract_scope")
    downstream = contract["downstream_owner_requirements_preserved_not_implemented_by_v3r30"]
    check("not one flat color" in downstream["tissue_material_goal"] and "bald" in downstream["runtime_variants"] and "Avatar Builder" in downstream["avatar_builder_handoff"], "downstream_owner_requirements")
    person_spec = downstream["shared_person_spec_identity_era_maturity_policy"]
    check(person_spec["status"] ==
          "DOWNSTREAM_POLICY_ONLY_NOT_IMPLEMENTED_OR_AUTHORIZED_BY_V3R30" and
          person_spec["required_consumers"] ==
          ["Temporary Creator", "Avatar Builder", "voice generator"] and
          person_spec["single_exact_contract"] is True and
          person_spec["uncertainty_behavior"] ==
          "FAIL_UNRESOLVED_AND_REQUEST_CORRECTION_NEVER_SILENTLY_ROUTE_NON_ADULT_OR_DOLL_SAFE" and
          set(person_spec["permitted_correction_submitters"]) ==
          {"Kira", "Biological Robert", "another permanent person"} and
          "No Way Home" in person_spec["peter_parker_example"] and
          person_spec["current_body_or_generator_authority"] == "NONE",
          "downstream_person_spec_identity_era_maturity_policy")
    one_shot = contract["one_shot_materialization"]
    check(one_shot["ledger_directory_open_or_create_relative_to_held_anchor_handle"] is True and
          one_shot["ledger_file_create_or_open_relative_to_held_directory_handle"] is True and
          one_shot["final_owner_rights_dacls_supplied_during_atomic_object_creation"] is True,
          "contract_handle_relative_materialization")
    check(one_shot["protected_owner_rights_ledger_directory_append_only_dacl"] ==
          "D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200ab;;;OW)" and
          one_shot["append_only_directory_owner_rights"] ==
          "READ_TRAVERSE_ADD_FILE_ONLY_NO_ADD_SUBDIRECTORY_DELETE_DELETE_CHILD_OR_WRITE_DAC" and
          one_shot["additional_child_creation_cannot_remove_replace_or_reset_exact_ledger"] is True,
          "contract_append_only_directory_boundary")
    check(build_plan["blender_authority"] == "NONE" and "/Brepro" in build_plan["compile_flags"], "build_plan_boundary")
    consumption_plan = build_plan["materialization_consumption"]
    install_plan = build_plan["separate_program_data_install_authority"]
    check(consumption_plan["directory_open_or_create_nt_rootdirectory_relative"] is True and
          consumption_plan["ledger_create_or_open_nt_rootdirectory_relative"] is True and
          consumption_plan["final_owner_rights_dacls_supplied_at_atomic_creation"] is True and
          consumption_plan["protected_directory_append_only_dacl"] ==
          "D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200ab;;;OW)" and
          install_plan["decision_binds_handle_relative_atomic_creation"] is True,
          "build_plan_handle_relative_materialization")
    hostile_seal = verify_seal() if args.phase == "PostSeal" else 0
    print("phase=" + args.phase)
    print("upstream_exact=33/33_direct_28/28_nested_17/17_deep_78/78_total")
    print("blender_exact=bytes_sha256_path")
    print(f"mocked_hostile_worker_refusals={hostile_worker}/18")
    print(f"mocked_hostile_worker_staging_refusals={hostile_worker_staging}/4")
    print(f"mocked_hostile_audit_refusals={hostile_audit}/21")
    print(f"mocked_hostile_install_authority_refusals={hostile_install_authority}/5")
    print(f"mocked_hostile_materialization_consumption_refusals={hostile_consumption}/4")
    print(f"mocked_hostile_seal_refusals={hostile_seal}/3")
    print("syntax_cache_free=2/2")
    print("native_materialized_compile=/W4_/WX_PASS_NOT_EXECUTED")
    print("native_materialized_analyzer=ZERO_UNSUPPRESSED_DEFECTS_NOT_EXECUTED")
    print("native_static_surface=PASS_PRE_RESERVED_SEVEN_WORKER_AND_EIGHT_FINAL_HANDLES_THROUGH_SUCCESS")
    print("postseal_package_write_attempts=0")
    print("candidate_or_blender_invoked=false")
    print("result=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("result=FAIL:" + type(error).__name__ + ":" + str(error))
        raise
