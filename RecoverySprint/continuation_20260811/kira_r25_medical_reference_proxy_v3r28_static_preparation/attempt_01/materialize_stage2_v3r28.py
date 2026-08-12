"""Deterministic V3r28 Stage-2 source materializer; never invokes Blender or a compiler.

This program is not execution authority.  It accepts only a fixed installed
Stage-1 path and fixed Audit-A path, verifies caller-supplied external anchors,
then writes a new scratch-only Stage-2 source directory.  Audit B must inspect
and externally pin the resulting native executable before any launch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat


KIRA_ROOT = Path(r"C:\Users\robmc\Kira")
CODEX_SCRATCH_ROOT = Path(r"C:\Users\robmc\Documents\Codex")
EXPECTED_MATERIALIZATION_DIR = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\body_v3r28_stage2_materialized_attempt_01")
EXPECTED_STAGE1_DIR = KIRA_ROOT / r"RecoverySprint\continuation_20260811\kira_r25_medical_reference_proxy_v3r28_static_preparation\attempt_01"
EXPECTED_AUDIT_A_DIR = KIRA_ROOT / r"RecoverySprint\continuation_20260811\kira_r25_medical_reference_proxy_v3r28_fresh_static_audit\attempt_01"
INSTALLED_STAGE2_ROOT = KIRA_ROOT / r"RecoverySprint\continuation_20260811\kira_r25_medical_reference_proxy_v3r28_stage2\attempt_01"
INSTALLED_ANCHOR_PATH = KIRA_ROOT / r"tools\native\kira_v3r28_stage2_anchor.exe"
BLENDER_PATH = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
BLENDER_BYTES = 108687824
BLENDER_SHA256 = "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
AUDITOR = re.compile(r"independent_[a-z0-9_]{8,96}\Z")
AUDIT_ROW_IDS = (
    "01_stage1_seal",
    "02_upstream_17",
    "03_static_only",
    "04_two_stage_authority",
    "05_blender_identity",
    "06_native_handle_locking",
    "07_one_shot_ledger",
    "08_worker_factory_isolation",
    "09_frame_landmarks",
    "10_proxy_truth",
    "11_hostile_geometry",
    "12_output_revalidation",
    "13_license_quarantine",
    "14_claim_boundary",
)
COPY_TO_STAGE2 = (
    "CONTRACT.json",
    "NORMALIZED_REFERENCE_FRAME.json",
    "PROXY_SPEC.json",
    "STAGE2_NATIVE_BUILD_PLAN.json",
    "STAGE2_PROTOCOL.md",
    "blender_worker_v3r28.py",
    "post_audit_native_anchor_template_v3r28.c",
)


class Refuse(RuntimeError):
    pass


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def reject_constant(value: str) -> None:
    raise Refuse("nonfinite_json:" + value)


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise Refuse("duplicate_json_key:" + key)
        result[key] = value
    return result


def strict_json(raw: bytes, label: str) -> dict[str, object]:
    if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise Refuse(label + ":encoding")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise Refuse(label + ":root")
    return value


def identity(path: Path) -> tuple[int, int, int, int, int]:
    observed = path.lstat()
    attributes = int(getattr(observed, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if stat.S_ISLNK(observed.st_mode) or attributes & reparse or not stat.S_ISREG(observed.st_mode):
        raise Refuse("not_regular_nonreparse:" + str(path))
    return observed.st_dev, observed.st_ino, observed.st_size, observed.st_mtime_ns, attributes


def read_stable(path: Path) -> bytes:
    before = identity(path)
    with path.open("rb") as stream:
        raw = stream.read()
    after = identity(path)
    if before != after or len(raw) != before[2]:
        raise Refuse("changed_while_reading:" + str(path))
    return raw


def exact_path(observed: Path, expected: Path, label: str) -> None:
    if os.path.normcase(os.path.abspath(observed)) != os.path.normcase(os.path.abspath(expected)):
        raise Refuse(label + ":fixed_path")


def safe_relative(value: str) -> PurePosixPath:
    if "\\" in value or "\0" in value:
        raise Refuse("relative_path_grammar:" + value)
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise Refuse("relative_path_grammar:" + value)
    return path


def directory_snapshot(root: Path) -> dict[str, bytes]:
    root_stat = root.lstat()
    attributes = int(getattr(root_stat, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISDIR(root_stat.st_mode) or attributes & reparse:
        raise Refuse("directory_nonreparse:" + str(root))
    result: dict[str, bytes] = {}
    for child in sorted(root.iterdir(), key=lambda value: value.name):
        if not child.is_file() or child.name in result:
            raise Refuse("flat_regular_inventory:" + str(child))
        result[child.name] = read_stable(child)
    return result


def parse_stage1(snapshot: dict[str, bytes], expected_root: str) -> tuple[dict[str, bytes], dict[str, object]]:
    if "STATIC_SEAL_MANIFEST.json" not in snapshot:
        raise Refuse("stage1_seal_missing")
    seal = strict_json(snapshot["STATIC_SEAL_MANIFEST.json"], "stage1_seal")
    if seal.get("schema") != "kira.r25.medical_reference_proxy.v3r28.static_seal.v1":
        raise Refuse("stage1_seal_schema")
    if seal.get("status") != "SEALED_STATIC_TWO_STAGE_AUTHOR_CANDIDATE_PENDING_DIFFERENT_AUDIT_A":
        raise Refuse("stage1_seal_status")
    if seal.get("execution_authority") != "NONE" or seal.get("candidate_executed") is not False:
        raise Refuse("stage1_execution_boundary")
    subjects = seal.get("subjects")
    if not isinstance(subjects, list) or seal.get("subject_count") != len(subjects) or not subjects:
        raise Refuse("stage1_subject_count")
    rows: list[tuple[str, int, str]] = []
    bound: dict[str, bytes] = {}
    for subject in subjects:
        if not isinstance(subject, dict) or set(subject) != {"path", "bytes", "sha256"}:
            raise Refuse("stage1_subject_shape")
        path = str(subject["path"])
        safe_relative(path)
        byte_count = int(subject["bytes"])
        digest = str(subject["sha256"])
        if path not in snapshot or path == "STATIC_SEAL_MANIFEST.json" or not HEX64.fullmatch(digest):
            raise Refuse("stage1_subject_binding:" + path)
        raw = snapshot[path]
        if len(raw) != byte_count or sha256(raw) != digest:
            raise Refuse("stage1_subject_mismatch:" + path)
        rows.append((path, byte_count, digest))
        bound[path] = raw
    if [row[0] for row in rows] != sorted(row[0] for row in rows) or len(bound) != len(rows):
        raise Refuse("stage1_subject_order_unique")
    canonical = b"".join(f"{path}\t{byte_count}\t{digest}\n".encode("utf-8") for path, byte_count, digest in rows)
    root = sha256(canonical)
    if seal.get("canonical_grammar") != "UTF8_LF_PYTHON_ORDINAL_SORTED_PATH_TAB_BYTES_TAB_LOWER_SHA256_LF":
        raise Refuse("stage1_canonical_grammar")
    if seal.get("canonical_bytes") != len(canonical) or seal.get("package_root_sha256") != root or root != expected_root:
        raise Refuse("stage1_external_root")
    if set(snapshot) != set(bound) | {"STATIC_SEAL_MANIFEST.json"}:
        raise Refuse("stage1_unsealed_file")
    return bound, seal


def parse_tsv(raw: bytes, header: str, columns: int, label: str) -> list[list[str]]:
    if not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise Refuse(label + ":encoding")
    lines = raw.decode("utf-8").splitlines()
    if not lines or lines[0] != header:
        raise Refuse(label + ":header")
    rows = [line.split("\t") for line in lines[1:]]
    if any(len(row) != columns or any(field == "" for field in row) for row in rows):
        raise Refuse(label + ":columns")
    return rows


def verify_upstream(raw: bytes) -> list[tuple[Path, int, str, str]]:
    rows = parse_tsv(raw, "scope\tpath\tbytes\tsha256\tstatus", 5, "upstream")
    if len(rows) != 17:
        raise Refuse("upstream_count")
    bindings: list[tuple[Path, int, str, str]] = []
    seen: set[str] = set()
    for scope, path_text, byte_text, digest, status in rows:
        relative = safe_relative(path_text)
        if path_text in seen or scope not in {"v3r27_author", "v3r27_rejection"}:
            raise Refuse("upstream_unique_scope")
        expected_status = "DO_NOT_RUN_V3R27_PRESERVED" if scope == "v3r27_author" else "REJECTION_PRESERVED"
        if status != expected_status or not byte_text.isdecimal() or not HEX64.fullmatch(digest):
            raise Refuse("upstream_grammar:" + path_text)
        absolute = KIRA_ROOT.joinpath(*relative.parts)
        raw_file = read_stable(absolute)
        if len(raw_file) != int(byte_text) or sha256(raw_file) != digest:
            raise Refuse("upstream_mismatch:" + path_text)
        seen.add(path_text)
        bindings.append((absolute, int(byte_text), digest, scope))
    return bindings


def parse_audit(snapshot: dict[str, bytes], expected_manifest_sha: str,
                expected_stage1_root: str, expected_auditor: str) -> tuple[list[tuple[str, bytes]], dict[str, object]]:
    required = {"AUDIT_ARTIFACT_MANIFEST.tsv", "AUDIT_DECISION.json", "CHECKPOINT.md", "INDEPENDENT_AUDIT.tsv"}
    if not required.issubset(snapshot):
        raise Refuse("audit_required_files")
    manifest_raw = snapshot["AUDIT_ARTIFACT_MANIFEST.tsv"]
    if sha256(manifest_raw) != expected_manifest_sha:
        raise Refuse("audit_external_manifest_digest")
    rows = parse_tsv(manifest_raw, "path\tbytes\tsha256", 3, "audit_manifest")
    if [row[0] for row in rows] != sorted(row[0] for row in rows):
        raise Refuse("audit_manifest_order")
    covered: list[tuple[str, bytes]] = []
    for path, byte_text, digest in rows:
        safe_relative(path)
        if "/" in path or path == "AUDIT_ARTIFACT_MANIFEST.tsv" or not byte_text.isdecimal() or not HEX64.fullmatch(digest):
            raise Refuse("audit_manifest_row:" + path)
        if path not in snapshot or any(prior[0] == path for prior in covered):
            raise Refuse("audit_manifest_unique:" + path)
        raw = snapshot[path]
        if len(raw) != int(byte_text) or sha256(raw) != digest:
            raise Refuse("audit_artifact_mismatch:" + path)
        covered.append((path, raw))
    if set(snapshot) != {"AUDIT_ARTIFACT_MANIFEST.tsv"} | {path for path, _ in covered}:
        raise Refuse("audit_unbound_artifact")
    decision = strict_json(snapshot["AUDIT_DECISION.json"], "audit_decision")
    expected_keys = {
        "schema", "status", "auditor_id", "accepted_stage1_package_root",
        "execution_authority", "candidate_executed", "blender_invoked",
        "maximum_materializations", "stage2_requires_different_audit_b", "audit_scope",
    }
    if set(decision) != expected_keys:
        raise Refuse("audit_decision_keys")
    if decision != {
        "schema": "kira.r25.medical_reference_proxy.v3r28.audit_a_decision.v1",
        "status": "ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY",
        "auditor_id": expected_auditor,
        "accepted_stage1_package_root": expected_stage1_root,
        "execution_authority": "MATERIALIZE_STAGE2_ONLY_NO_BLENDER",
        "candidate_executed": False,
        "blender_invoked": False,
        "maximum_materializations": 1,
        "stage2_requires_different_audit_b": True,
        "audit_scope": "CACHE_FREE_STATIC_SYNTAX_MOCKED_HOSTILE_ONLY",
    }:
        raise Refuse("audit_decision_exact")
    audit_rows = parse_tsv(
        snapshot["INDEPENDENT_AUDIT.tsv"],
        "row_id\tstatus\tevidence_sha256\tfinding",
        4,
        "independent_audit",
    )
    if tuple(row[0] for row in audit_rows) != AUDIT_ROW_IDS or any(row[1] != "PASS" or not HEX64.fullmatch(row[2]) for row in audit_rows):
        raise Refuse("independent_audit_14_pass")
    return [("AUDIT_ARTIFACT_MANIFEST.tsv", manifest_raw), *covered], decision


def c_wide(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace('"', '\\"')


def c_ascii(value: str) -> str:
    if not value.isascii() or any(ord(char) < 32 for char in value):
        raise Refuse("c_ascii")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_header(stage1_root: str, audit_manifest_sha: str, auditor: str,
                 stage1_snapshot: dict[str, bytes], stage1_subjects: dict[str, bytes],
                 upstream: list[tuple[Path, int, str, str]],
                 audit: list[tuple[str, bytes]]) -> bytes:
    worker = stage1_subjects["blender_worker_v3r28.py"]
    spec = stage1_subjects["PROXY_SPEC.json"]
    frame = stage1_subjects["NORMALIZED_REFERENCE_FRAME.json"]
    bindings: list[tuple[Path, int, str, str]] = []
    for name, raw in sorted(stage1_snapshot.items()):
        bindings.append((EXPECTED_STAGE1_DIR / name, len(raw), sha256(raw), "stage1:" + name))
    bindings.extend(upstream)
    for name, raw in audit:
        bindings.append((EXPECTED_AUDIT_A_DIR / name, len(raw), sha256(raw), "audit_a:" + name))
    bindings.extend((
        (INSTALLED_STAGE2_ROOT / "blender_worker_v3r28.py", len(worker), sha256(worker), "stage2:worker"),
        (INSTALLED_STAGE2_ROOT / "PROXY_SPEC.json", len(spec), sha256(spec), "stage2:spec"),
        (INSTALLED_STAGE2_ROOT / "NORMALIZED_REFERENCE_FRAME.json", len(frame), sha256(frame), "stage2:frame"),
        (BLENDER_PATH, BLENDER_BYTES, BLENDER_SHA256, "runtime:blender_5_1_2"),
    ))
    normalized = sorted(
        (os.path.normcase(str(path)), path, byte_count, digest, label)
        for path, byte_count, digest, label in bindings
    )
    if len(normalized) > 128 or len({row[0] for row in normalized}) != len(normalized):
        raise Refuse("native_binding_count_or_duplicate")
    lines = [
        "#ifndef KIRA_V3R28_POST_AUDIT_BINDINGS_H",
        "#define KIRA_V3R28_POST_AUDIT_BINDINGS_H",
        "",
        "#define V3R28_MATERIALIZED 1",
        f'#define V3R28_STAGE1_PACKAGE_ROOT "{stage1_root}"',
        f'#define V3R28_AUDIT_A_SHA256 "{audit_manifest_sha}"',
        f'#define V3R28_AUDITOR "{c_ascii(auditor)}"',
        f'#define V3R28_FRAME_SHA256 "{sha256(frame)}"',
        f'#define V3R28_SPEC_SHA256 "{sha256(spec)}"',
        f'#define V3R28_WORKER_SHA256 "{sha256(worker)}"',
        f'#define V3R28_EXPECTED_SELF_PATH L"{c_wide(INSTALLED_ANCHOR_PATH)}"',
        f'#define V3R28_WORKER_PATH L"{c_wide(INSTALLED_STAGE2_ROOT / "blender_worker_v3r28.py")}"',
        f'#define V3R28_OUTPUT_PARENT L"{c_wide(INSTALLED_STAGE2_ROOT)}"',
        f'#define V3R28_BLENDER_PATH L"{c_wide(BLENDER_PATH)}"',
        f"#define V3R28_BLENDER_BYTES {BLENDER_BYTES}ULL",
        f'#define V3R28_BLENDER_SHA256 "{BLENDER_SHA256}"',
        f"#define V3R28_BINDING_COUNT {len(bindings)}U",
        "",
        f"static const V3R28Binding V3R28_BINDINGS[{len(bindings)}] = {{",
    ]
    for _, path, byte_count, digest, label in normalized:
        lines.append(f'    {{ L"{c_wide(path)}", {byte_count}ULL, "{digest}", "{c_ascii(label)}" }},')
    lines.extend(("};", "", "#endif", ""))
    return "\n".join(lines).encode("utf-8")


def exclusive_write(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--stage1-dir", required=True)
    parser.add_argument("--audit-a-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-stage1-root", required=True)
    parser.add_argument("--expected-audit-manifest-sha256", required=True)
    parser.add_argument("--expected-auditor-id", required=True)
    values = parser.parse_args()
    if not HEX64.fullmatch(values.expected_stage1_root) or not HEX64.fullmatch(values.expected_audit_manifest_sha256):
        raise Refuse("external_digest_grammar")
    if not AUDITOR.fullmatch(values.expected_auditor_id):
        raise Refuse("external_auditor_grammar")
    return values


def main() -> int:
    args = parse_args()
    stage1_dir = Path(args.stage1_dir)
    audit_dir = Path(args.audit_a_dir)
    output_dir = Path(args.output_dir)
    exact_path(stage1_dir, EXPECTED_STAGE1_DIR, "stage1")
    exact_path(audit_dir, EXPECTED_AUDIT_A_DIR, "audit_a")
    output_absolute = Path(os.path.abspath(output_dir))
    exact_path(output_absolute, EXPECTED_MATERIALIZATION_DIR, "output")
    staging = output_absolute.with_name(output_absolute.name + ".partial." + str(os.getpid()))
    if (not output_absolute.is_relative_to(CODEX_SCRATCH_ROOT) or output_absolute.exists()
            or staging.exists()):
        raise Refuse("new_scratch_output_only")
    stage1_snapshot = directory_snapshot(stage1_dir)
    stage1_subjects, seal = parse_stage1(stage1_snapshot, args.expected_stage1_root)
    if seal.get("author") == args.expected_auditor_id:
        raise Refuse("auditor_must_differ_from_author")
    upstream = verify_upstream(stage1_subjects["UPSTREAM_CLOSURE.tsv"])
    audit_snapshot = directory_snapshot(audit_dir)
    audit, _ = parse_audit(
        audit_snapshot,
        args.expected_audit_manifest_sha256,
        args.expected_stage1_root,
        args.expected_auditor_id,
    )
    header = build_header(
        args.expected_stage1_root,
        args.expected_audit_manifest_sha256,
        args.expected_auditor_id,
        stage1_snapshot,
        stage1_subjects,
        upstream,
        audit,
    )
    staging.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        created: list[tuple[str, bytes]] = []
        for name in COPY_TO_STAGE2:
            raw = stage1_subjects[name]
            exclusive_write(staging / name, raw)
            created.append((name, raw))
        exclusive_write(staging / "POST_AUDIT_BINDINGS_TEMPLATE_v3r28.h", header)
        created.append(("POST_AUDIT_BINDINGS_TEMPLATE_v3r28.h", header))
        boundary = (json.dumps({
            "schema": "kira.r25.medical_reference_proxy.v3r28.stage2_authority_boundary.v1",
            "status": "MATERIALIZED_SOURCE_ONLY_PENDING_DIFFERENT_AUDIT_B",
            "stage1_package_root_sha256": args.expected_stage1_root,
            "audit_a_manifest_sha256": args.expected_audit_manifest_sha256,
            "audit_a_auditor_id": args.expected_auditor_id,
            "installed_stage2_root": str(INSTALLED_STAGE2_ROOT),
            "installed_anchor_path": str(INSTALLED_ANCHOR_PATH),
            "blender_authority": "NONE",
            "maximum_future_invocations_after_audit_b_acceptance": 1,
            "audit_b_external_native_exe_sha256_required": True,
        }, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
        exclusive_write(staging / "STAGE2_AUTHORITY_BOUNDARY.json", boundary)
        created.append(("STAGE2_AUTHORITY_BOUNDARY.json", boundary))
        manifest_lines = ["path\tbytes\tsha256"]
        for name, raw in sorted(created):
            manifest_lines.append(f"{name}\t{len(raw)}\t{sha256(raw)}")
        manifest = ("\n".join(manifest_lines) + "\n").encode("utf-8")
        exclusive_write(staging / "STAGE2_MATERIALIZATION_MANIFEST.tsv", manifest)
        # Re-read fixed inputs before atomically publishing the scratch package.
        if directory_snapshot(stage1_dir) != stage1_snapshot or directory_snapshot(audit_dir) != audit_snapshot:
            raise Refuse("input_changed_during_materialization")
        staging.rename(output_absolute)
    except BaseException:
        if staging.exists():
            for child in staging.iterdir():
                if not child.is_file() or child.is_symlink():
                    raise Refuse("unexpected_staging_entry:" + str(child))
                child.unlink()
            staging.rmdir()
        raise
    print("V3R28_STAGE2_SOURCE_MATERIALIZED_NO_EXECUTION_AUTHORITY:" + sha256(manifest))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, Refuse) as error:
        print("V3R28_MATERIALIZATION_REFUSED:" + type(error).__name__ + ":" + str(error))
        raise SystemExit(73)
