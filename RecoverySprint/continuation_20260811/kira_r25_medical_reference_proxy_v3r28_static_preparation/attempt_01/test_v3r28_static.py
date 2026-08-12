"""Cache-free static and mocked-hostile checks for sealed V3r28 Stage 1."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parent
KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
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
    check(len(rows) == 17 and all(len(row) == 5 for row in rows), "upstream_17")
    check(sum(row[0] == "v3r27_author" for row in rows) == 11, "upstream_author_11")
    check(sum(row[0] == "v3r27_rejection" for row in rows) == 6, "upstream_rejection_6")
    observed: dict[str, bytes] = {}
    for scope, relative, byte_text, sha, status in rows:
        check("\\" not in relative and ".." not in Path(relative).parts, "upstream_path:" + relative)
        check(len(sha) == 64 and set(sha) <= HEX and byte_text.isdecimal(), "upstream_grammar:" + relative)
        expected_status = "DO_NOT_RUN_V3R27_PRESERVED" if scope == "v3r27_author" else "REJECTION_PRESERVED"
        check(status == expected_status, "upstream_status:" + relative)
        raw_file = read(KIRA_ROOT.joinpath(*relative.split("/")))
        check(len(raw_file) == int(byte_text) and digest(raw_file) == sha, "upstream_hash:" + relative)
        observed[relative] = raw_file
    check(len(observed) == 17, "upstream_unique")
    return rows, observed


def ast_checks() -> tuple[ast.Module, ast.Module]:
    worker_raw = read(ROOT / "blender_worker_v3r28.py")
    materializer_raw = read(ROOT / "materialize_stage2_v3r28.py")
    worker_tree = ast.parse(worker_raw, filename="blender_worker_v3r28.py")
    materializer_tree = ast.parse(materializer_raw, filename="materialize_stage2_v3r28.py")
    allowed_worker_imports = {"__future__", "argparse", "binascii", "hashlib", "json", "math", "os", "pathlib", "struct", "sys", "zlib", "bpy", "mathutils"}
    imports: set[str] = set()
    for node in ast.walk(worker_tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    check(imports == allowed_worker_imports, "worker_import_allowlist")
    forbidden_materializer = {"subprocess", "bpy", "socket", "requests", "urllib", "http", "ftplib"}
    materializer_imports: set[str] = set()
    for node in ast.walk(materializer_tree):
        if isinstance(node, ast.Import):
            materializer_imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            materializer_imports.add(node.module.split(".")[0])
    check(not materializer_imports & forbidden_materializer, "materializer_static_only_imports")
    worker_text = worker_raw.decode("utf-8")
    materializer_text = materializer_raw.decode("utf-8")
    for forbidden in ("import_scene", "export_scene", "bpy.ops.wm.append", "bpy.ops.wm.link", "Sarah", "requests.", "socket.", "subprocess."):
        check(forbidden not in worker_text, "worker_forbidden_surface:" + forbidden)
    check(all(token not in materializer_text for token in ("subprocess", "os.system", "Popen(", "CreateProcess")), "materializer_no_process_launch")
    check("new_scratch_output_only" in materializer_text and "input_changed_during_materialization" in materializer_text, "materializer_publish_boundary")
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
    module = types.ModuleType("v3r28_worker_static_mock")
    module.__file__ = str(ROOT / "blender_worker_v3r28.py")
    try:
        exec(compile(read(ROOT / "blender_worker_v3r28.py"), module.__file__, "exec"), module.__dict__)
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


def c_checks() -> None:
    source = read(ROOT / "post_audit_native_anchor_template_v3r28.c").decode("utf-8")
    header = read(ROOT / "POST_AUDIT_BINDINGS_TEMPLATE_v3r28.h").decode("utf-8")
    required = (
        "V3R28_MATERIALIZED 0", "V3R28_UNMATERIALIZED_STATIC_TEMPLATE",
        "FILE_FLAG_OPEN_REPARSE_POINT", "GetFinalPathNameByHandleW", "FileIdInfo",
        "FILE_SHARE_READ", "CREATE_NEW", "FILE_FLAG_WRITE_THROUGH",
        "LEDGER_PENDING_CONSUMED", "LEDGER_SUCCESS_CONSUMED", "LEDGER_FAILURE_CONSUMED",
        "--background --factory-startup --disable-autoexec --python-exit-code 91",
        "CREATE_SUSPENDED", "AssignProcessToJobObject", "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE",
        "PROC_THREAD_ATTRIBUTE_HANDLE_LIST", "CREATE_UNICODE_ENVIRONMENT", "PYTHONNOUSERSITE=1",
        "WORKER_RECEIPT.tsv", "file_equals_memory", "FINAL_OUTPUT_MANIFEST.tsv",
        "front_clinical.png", "right_clinical.png", "iso_clinical.png", "iso_xray.png",
    )
    for token in required:
        check(token in source or token in header, "native_required:" + token)
    for forbidden in ("ShellExecute", "WinExec", "system(", "URLDownload", "InternetOpen", "WSAStartup"):
        check(forbidden not in source, "native_forbidden:" + forbidden)
    check("isolated_environment, L\"C:\\\\Users\\\\robmc\\\\Kira\"" in source, "native_isolated_environment")
    check("finalize_outputs(capability_sha, manifest_sha)" in source, "native_strict_finalization")


def audit_grammar_hostile() -> int:
    module = types.ModuleType("v3r28_materializer_static")
    module.__file__ = str(ROOT / "materialize_stage2_v3r28.py")
    exec(compile(read(ROOT / "materialize_stage2_v3r28.py"), module.__file__, "exec"), module.__dict__)
    stage_root = "1" * 64
    auditor = "independent_v3r28_auditor_bounded"
    decision = {
        "schema": "kira.r25.medical_reference_proxy.v3r28.audit_a_decision.v1",
        "status": "ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY",
        "auditor_id": auditor,
        "accepted_stage1_package_root": stage_root,
        "execution_authority": "MATERIALIZE_STAGE2_ONLY_NO_BLENDER",
        "candidate_executed": False,
        "blender_invoked": False,
        "maximum_materializations": 1,
        "stage2_requires_different_audit_b": True,
        "audit_scope": "CACHE_FREE_STATIC_SYNTAX_MOCKED_HOSTILE_ONLY",
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
    module.parse_audit(snapshot, digest(manifest), stage_root, auditor)
    count = 0
    changed_checkpoint = dict(snapshot)
    changed_checkpoint["CHECKPOINT.md"] += b"replacement\n"
    expect_refusal(lambda: module.parse_audit(changed_checkpoint, digest(manifest), stage_root, auditor), "unbound_checkpoint_replacement")
    count += 1
    extra = dict(snapshot)
    extra["UNBOUND.txt"] = b"unbound\n"
    expect_refusal(lambda: module.parse_audit(extra, digest(manifest), stage_root, auditor), "unbound_audit_file")
    count += 1
    expect_refusal(lambda: module.parse_audit(snapshot, "3" * 64, stage_root, auditor), "external_audit_anchor")
    count += 1
    changed_decision = copy.deepcopy(decision)
    changed_decision["execution_authority"] = "RUN_BLENDER"
    changed_raw = (json.dumps(changed_decision, sort_keys=True, separators=(",", ":")) + "\n").encode()
    changed_artifacts = dict(artifacts)
    changed_artifacts["AUDIT_DECISION.json"] = changed_raw
    changed_manifest = ("path\tbytes\tsha256\n" + "".join(
        f"{name}\t{len(raw)}\t{digest(raw)}\n" for name, raw in sorted(changed_artifacts.items())
    )).encode()
    changed_snapshot = {"AUDIT_ARTIFACT_MANIFEST.tsv": changed_manifest, **changed_artifacts}
    expect_refusal(lambda: module.parse_audit(changed_snapshot, digest(changed_manifest), stage_root, auditor), "audit_cannot_authorize_blender")
    count += 1
    return count


def verify_seal() -> None:
    seal = strict_json(read(ROOT / "STATIC_SEAL_MANIFEST.json"), "seal")
    check(seal["schema"] == "kira.r25.medical_reference_proxy.v3r28.static_seal.v1", "seal_schema")
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
    module = types.ModuleType("v3r28_materializer_postseal")
    module.__file__ = str(ROOT / "materialize_stage2_v3r28.py")
    exec(compile(read(ROOT / "materialize_stage2_v3r28.py"), module.__file__, "exec"), module.__dict__)
    snapshot = module.directory_snapshot(ROOT)
    bound, _ = module.parse_stage1(snapshot, seal["package_root_sha256"])
    check(len(bound) == seal["subject_count"] and len(snapshot) == seal["subject_count"] + 1, "materializer_stage1_parse")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("PreSeal", "PostSeal"))
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    _, upstream = parse_upstream()
    check(BLENDER.is_file() and BLENDER.stat().st_size == BLENDER_BYTES and digest(read(BLENDER)) == BLENDER_SHA256, "blender_identity")
    spec = strict_json(read(ROOT / "PROXY_SPEC.json"), "spec")
    frame = strict_json(read(ROOT / "NORMALIZED_REFERENCE_FRAME.json"), "frame")
    contract = strict_json(read(ROOT / "CONTRACT.json"), "contract")
    build_plan = strict_json(read(ROOT / "STAGE2_NATIVE_BUILD_PLAN.json"), "build_plan")
    ast_checks()
    hostile_worker = mocked_hostile_checks(spec, frame)
    hostile_audit = audit_grammar_hostile()
    c_checks()
    license_raw = next(raw for name, raw in upstream.items() if name.endswith("ATTRIBUTION_LICENSE_MANIFEST.tsv"))
    skeleton_raw = next(raw for name, raw in upstream.items() if name.endswith("SKELETON_136_MAPPING_PLAN.tsv"))
    check(b"QUARANTINE" in license_raw and b"CC BY" in license_raw, "license_quarantines")
    skeleton_lines = skeleton_raw.decode("utf-8").splitlines()
    check(len(skeleton_lines) - 1 == 136 and all("UNMAPPED" in line for line in skeleton_lines[1:]), "skeleton_136_unmapped")
    check(contract["execution_authority"] == "NONE" and contract["stage_a_truth"]["proxy_objects_exact"] == 9, "contract_scope")
    downstream = contract["downstream_owner_requirements_preserved_not_implemented_by_v3r28"]
    check("not one flat color" in downstream["tissue_material_goal"] and "bald" in downstream["runtime_variants"] and "Avatar Builder" in downstream["avatar_builder_handoff"], "downstream_owner_requirements")
    check(build_plan["blender_authority"] == "NONE" and "/Brepro" in build_plan["compile_flags"], "build_plan_boundary")
    if args.phase == "PostSeal":
        verify_seal()
    print("phase=" + args.phase)
    print("upstream_exact=17/17")
    print("blender_exact=bytes_sha256_path")
    print(f"mocked_hostile_worker_refusals={hostile_worker}/18")
    print(f"mocked_hostile_audit_refusals={hostile_audit}/4")
    print("syntax_cache_free=2/2")
    print("native_static_surface=PASS")
    print("candidate_or_blender_invoked=false")
    print("result=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("result=FAIL:" + type(error).__name__ + ":" + str(error))
        raise
