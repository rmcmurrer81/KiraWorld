from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
from typing import BinaryIO, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import kira_r24_intrinsic_curved_annulus_structured_retopology_static_r2 as r2


DEFAULT_CONTRACT = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r3/"
    "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R3_CONTRACT.json"
)
PACKAGE = DEFAULT_CONTRACT.parent
SEALED_CONTRACT_SEMANTIC_SHA256 = "8a08adcc8c07b87bca73d063ff381505af09d051bd35924792fa3e318c666abb"
SEALED_CONTRACT_FILE_SHA256 = "c4538333ab830e03e9540ac335bbd488e7405952e915ef58e8d6e8ad4b9b89ae"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SEAL_RE = re.compile(
    rb'(SEALED_CONTRACT_(?:SEMANTIC|FILE)_SHA256 = ")[0-9a-f]{64}("\r?\n)'
)
ZERO_SHA256 = "0" * 64


class R3PackageError(ValueError):
    """The immutable static package or an exact bound source changed."""


class BlendArtifactError(ValueError):
    """The candidate is not a structurally parseable Blender artifact."""


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_lower_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def is_strict_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def vector_close(first: Sequence[object], second: Sequence[object], tolerance: float = 1e-9) -> bool:
    return len(first) == len(second) and all(
        is_finite_number(a)
        and is_finite_number(b)
        and math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tolerance)
        for a, b in zip(first, second, strict=True)
    )


def _contract_semantic_projection(contract: Mapping[str, object]) -> dict[str, object]:
    value = copy.deepcopy(dict(contract))
    value["semantic_seal_sha256"] = ""
    return value


def normalized_worker_sha256(path: Path = Path(__file__)) -> str:
    data = path.read_bytes()
    normalized, count = SEAL_RE.subn(lambda match: match.group(1) + b"0" * 64 + match.group(2), data)
    if count != 2:
        raise R3PackageError("R3 evaluator seal field inventory changed")
    return hashlib.sha256(normalized).hexdigest()


def resolve_project_path(root: Path, raw: object) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        raise ValueError("path is not a nonempty project-relative path")
    resolved = (root / raw).resolve()
    resolved.relative_to(root.resolve())
    return resolved


def validate_exact_file(root: Path, record: Mapping[str, object]) -> Path:
    path = resolve_project_path(root, record.get("path"))
    if not path.is_file():
        raise ValueError("bound path is not a file")
    if not is_strict_int(record.get("bytes")) or record["bytes"] < 0:
        raise ValueError("bound byte count is invalid")
    if path.stat().st_size != record["bytes"]:
        raise ValueError("bound byte count changed")
    if not is_lower_sha256(record.get("sha256")) or sha256_file(path) != record["sha256"]:
        raise ValueError("bound SHA-256 changed")
    return path


def contract_bound_failures(contract: Mapping[str, object], prefix: str = "contract") -> set[str]:
    failures: set[str] = set()
    bounds = contract.get("metric_bounds")
    if not isinstance(bounds, Mapping):
        return {f"{prefix}:metric_bounds"}
    for name in ("minimum_render_triangle_angle_degrees", "minimum_render_triangle_area_m2"):
        value = bounds.get(name)
        if not is_finite_number(value) or float(value) <= 0.0:
            failures.add(f"{prefix}:{name}")
    maximum = bounds.get("maximum_new_interior_vertices")
    if not is_strict_int(maximum) or maximum < 0:
        failures.add(f"{prefix}:maximum_new_interior_vertices")
    return failures


def validate_parent_bindings(contract: Mapping[str, object], root: Path = ROOT) -> dict[str, Path]:
    expected_names = {
        "r2_contract",
        "r2_proposal",
        "r2_checkpoint",
        "r2_manifest",
        "r2_independent_audit",
        "r2_evaluator",
        "r2_test",
    }
    bindings = contract.get("parent_bindings")
    if not isinstance(bindings, Mapping) or set(bindings) != expected_names:
        raise R3PackageError("R3 parent binding inventory is not exact")
    resolved: dict[str, Path] = {}
    for name, record in bindings.items():
        if not isinstance(record, Mapping):
            raise R3PackageError(f"R3 parent binding {name!r} is malformed")
        try:
            resolved[str(name)] = validate_exact_file(root, record)
        except (OSError, TypeError, ValueError) as exc:
            raise R3PackageError(f"R3 parent binding {name!r} changed: {exc}") from exc
    return resolved


@lru_cache(maxsize=1)
def load_sealed_contract() -> dict[str, object]:
    try:
        file_hash = sha256_file(DEFAULT_CONTRACT)
        contract = json.loads(DEFAULT_CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise R3PackageError(f"R3 contract cannot be loaded: {exc}") from exc
    if file_hash != SEALED_CONTRACT_FILE_SHA256:
        raise R3PackageError("R3 on-disk contract file SHA-256 is not sealed identity")
    if contract.get("schema") != "kira.avatar.r24.intrinsic_curved_annulus_structured_retopology_gate.v3":
        raise R3PackageError("unexpected R3 contract schema")
    semantic = canonical_sha256(_contract_semantic_projection(contract))
    if semantic != SEALED_CONTRACT_SEMANTIC_SHA256 or contract.get("semantic_seal_sha256") != semantic:
        raise R3PackageError("R3 contract semantic seal changed")
    worker_semantic = contract.get("authorized_implementation", {}).get("worker_semantic_sha256")
    if worker_semantic != normalized_worker_sha256():
        raise R3PackageError("R3 evaluator semantic identity changed")
    failures = contract_bound_failures(contract)
    if failures:
        raise R3PackageError("invalid sealed R3 metric bounds: " + ",".join(sorted(failures)))
    validate_parent_bindings(contract)
    source_bindings = contract.get("exact_source_bindings")
    if not isinstance(source_bindings, Mapping) or set(source_bindings) != {
        "build_evidence",
        "inherited_intersection_report",
        "r23_freeze_preflight",
    }:
        raise R3PackageError("R3 exact source binding inventory is not exact")
    for name, record in source_bindings.items():
        if not isinstance(record, Mapping):
            raise R3PackageError(f"R3 source binding {name!r} is malformed")
        try:
            validate_exact_file(ROOT, record)
        except (OSError, TypeError, ValueError) as exc:
            raise R3PackageError(f"R3 source binding {name!r} changed: {exc}") from exc
    return contract


def _validate_sdna(payload: bytes, endian: str) -> dict[str, int]:
    offset = 0

    def take(size: int) -> bytes:
        nonlocal offset
        value = payload[offset : offset + size]
        if len(value) != size:
            raise BlendArtifactError("truncated DNA1 payload")
        offset += size
        return value

    def tag(expected: bytes) -> None:
        if take(4) != expected:
            raise BlendArtifactError(f"DNA1 lacks {expected.decode('ascii')} section")

    def u32() -> int:
        return struct.unpack(endian + "I", take(4))[0]

    def u16() -> int:
        return struct.unpack(endian + "H", take(2))[0]

    def strings(count: int) -> list[str]:
        nonlocal offset
        values: list[str] = []
        for _ in range(count):
            end = payload.find(b"\x00", offset)
            if end < 0:
                raise BlendArtifactError("unterminated DNA1 string")
            values.append(payload[offset:end].decode("utf-8", "strict"))
            offset = end + 1
        offset = (offset + 3) & ~3
        if offset > len(payload):
            raise BlendArtifactError("DNA1 string padding overrun")
        return values

    tag(b"SDNA")
    tag(b"NAME")
    name_count = u32()
    if name_count <= 0 or name_count > 1_000_000:
        raise BlendArtifactError("invalid DNA1 name count")
    names = strings(name_count)
    tag(b"TYPE")
    type_count = u32()
    if type_count <= 0 or type_count > 1_000_000:
        raise BlendArtifactError("invalid DNA1 type count")
    types = strings(type_count)
    tag(b"TLEN")
    lengths = [u16() for _ in range(type_count)]
    offset = (offset + 3) & ~3
    tag(b"STRC")
    struct_count = u32()
    if struct_count <= 0 or struct_count > 1_000_000:
        raise BlendArtifactError("invalid DNA1 structure count")
    for _ in range(struct_count):
        type_index = u16()
        field_count = u16()
        # Blender 5.x may serialize opaque zero-length/zero-field runtime types.
        # Their indices must still be valid; a zero TLEN is not itself corruption.
        if type_index >= len(types) or field_count > 65535:
            raise BlendArtifactError("invalid DNA1 structure header")
        for _ in range(field_count):
            field_type = u16()
            field_name = u16()
            if field_type >= len(types) or field_name >= len(names):
                raise BlendArtifactError("invalid DNA1 field index")
    if any(payload[offset:]):
        raise BlendArtifactError("unexpected nonzero DNA1 trailing data")
    return {"name_count": name_count, "type_count": type_count, "structure_count": struct_count}


def _open_blend_stream(path: Path) -> tuple[BinaryIO, bool]:
    raw = path.open("rb")
    magic = raw.read(4)
    raw.seek(0)
    if magic != b"\x28\xb5\x2f\xfd":
        return raw, False
    raw.close()
    try:
        from compression import zstd
    except ImportError as exc:
        raise BlendArtifactError("zstd-compressed Blend cannot be inspected") from exc
    return zstd.open(path, "rb"), True


def _semantic_id_name(code: str, payload: bytes) -> str | None:
    prefix = code.encode("ascii")
    for match in re.finditer(rb"[ -~]{4,}\x00", payload):
        value = match.group(0)[:-1]
        if value.startswith(prefix) and len(value) > len(prefix):
            try:
                return value[len(prefix) :].decode("utf-8", "strict")
            except UnicodeDecodeError:
                return None
    return None


@lru_cache(maxsize=8)
def _parse_blend_cached(path_text: str, size: int, mtime_ns: int) -> dict[str, object]:
    del size, mtime_ns
    path = Path(path_text)
    stream, compressed = _open_blend_stream(path)
    with stream:
        header = stream.read(17)
        if header.startswith(b"BLENDER17-"):
            if len(header) != 17 or re.fullmatch(rb"BLENDER17-[0-9]{2}[vV][0-9]{4}", header) is None:
                raise BlendArtifactError("invalid extended Blender header")
            endian = "<" if header[12:13] == b"v" else ">"
            version = header[13:17].decode("ascii")
            header_size = 17

            def read_block_header() -> tuple[bytes, int, int, int, int] | None:
                raw = stream.read(32)
                if not raw:
                    return None
                if len(raw) != 32:
                    raise BlendArtifactError("truncated extended Blender block header")
                code, sdna, old_address, length, count = struct.unpack(endian + "4sIQQQ", raw)
                return code, length, old_address, sdna, count

        else:
            header = header[:12]
            if re.fullmatch(rb"BLENDER[-_][vV][0-9]{3}", header) is None:
                raise BlendArtifactError("missing Blender file magic")
            endian = "<" if header[8:9] == b"v" else ">"
            pointer_size = 8 if header[7:8] == b"-" else 4
            version = header[9:12].decode("ascii")
            header_size = 12
            stream.seek(12)
            fmt = endian + ("4sIQII" if pointer_size == 8 else "4sIIII")
            block_header_size = struct.calcsize(fmt)

            def read_block_header() -> tuple[bytes, int, int, int, int] | None:
                raw = stream.read(block_header_size)
                if not raw:
                    return None
                if len(raw) != block_header_size:
                    raise BlendArtifactError("truncated Blender block header")
                code, length, old_address, sdna, count = struct.unpack(fmt, raw)
                return code, length, old_address, sdna, count

        counts: dict[str, int] = {}
        semantic: dict[str, list[dict[str, str]]] = {code: [] for code in ("OB", "ME", "AR", "AC", "MA")}
        dna_payload: bytes | None = None
        ended = False
        block_count = 0
        while True:
            parsed = read_block_header()
            if parsed is None:
                break
            code_raw, length, old_address, sdna, count = parsed
            del old_address, sdna
            try:
                code = code_raw.rstrip(b"\x00").decode("ascii")
            except UnicodeDecodeError as exc:
                raise BlendArtifactError("non-ASCII Blender block code") from exc
            if not code or length > 2**40 or count > 2**40:
                raise BlendArtifactError("invalid Blender block dimensions")
            payload = stream.read(length)
            if len(payload) != length:
                raise BlendArtifactError("truncated Blender block payload")
            block_count += 1
            if block_count > 2_000_000:
                raise BlendArtifactError("unreasonable Blender block count")
            counts[code] = counts.get(code, 0) + 1
            if code == "DNA1":
                if dna_payload is not None:
                    raise BlendArtifactError("duplicate DNA1 block")
                dna_payload = payload
            if code in semantic:
                name = _semantic_id_name(code, payload)
                if name is None:
                    raise BlendArtifactError(f"{code} datablock lacks parseable semantic ID")
                semantic[code].append({"name": name, "direct_block_sha256": hashlib.sha256(payload).hexdigest()})
            if code == "ENDB":
                if length != 0 or count != 0:
                    raise BlendArtifactError("malformed ENDB block")
                ended = True
                break
        if not ended or stream.read(1):
            raise BlendArtifactError("Blend does not terminate exactly at ENDB")
        if dna_payload is None:
            raise BlendArtifactError("Blend lacks DNA1")
        dna = _validate_sdna(dna_payload, endian)
        for required_code in ("OB", "ME", "AR", "AC", "MA", "DNA1", "ENDB"):
            if counts.get(required_code, 0) <= 0:
                raise BlendArtifactError(f"Blend lacks required {required_code} block")
        for records in semantic.values():
            records.sort(key=lambda row: row["name"])
        return {
            "schema": "kira.avatar.r24.blend_structure.v1",
            "compressed_zstd": compressed,
            "header": header.decode("ascii"),
            "header_size": header_size,
            "version": version,
            "block_count": block_count,
            "block_counts": {name: counts[name] for name in sorted(counts)},
            "dna": dna,
            "semantic_ids": semantic,
        }


def parse_blend_artifact(path: Path) -> dict[str, object]:
    stat = path.stat()
    return copy.deepcopy(_parse_blend_cached(str(path.resolve()), stat.st_size, stat.st_mtime_ns))


def _semantic_names(summary: Mapping[str, object], code: str) -> set[str]:
    semantic = summary.get("semantic_ids")
    if not isinstance(semantic, Mapping) or not isinstance(semantic.get(code), list):
        return set()
    return {
        str(row.get("name"))
        for row in semantic[code]
        if isinstance(row, Mapping) and isinstance(row.get("name"), str)
    }


def _source_glb_document(contract: Mapping[str, object]) -> tuple[dict[str, object], bytes]:
    source = contract["exact_source"]
    path = validate_exact_file(
        ROOT,
        {
            "path": source["licensed_source_glb_path"],
            "bytes": source["licensed_source_glb_bytes"],
            "sha256": source["licensed_source_glb_sha256"],
        },
    )
    return r2._parse_glb(path)


@lru_cache(maxsize=1)
def exact_context() -> dict[str, object]:
    contract = load_sealed_contract()
    context = dict(r2.static_context())
    context["contract"] = contract
    document, binary = _source_glb_document(contract)
    source = context["source_mesh"]
    source_nodes = [node for node in document["nodes"] if node.get("name") == contract["exact_source"]["source_object"]]
    if len(source_nodes) != 1 or not is_strict_int(source_nodes[0].get("skin")):
        raise R3PackageError("exact source object does not bind one source skin")
    skin = document["skins"][source_nodes[0]["skin"]]
    bone_names = [document["nodes"][index].get("name") for index in skin["joints"]]
    if any(not isinstance(name, str) or not name for name in bone_names):
        raise R3PackageError("source skin contains unnamed joint")
    exact = contract["exact_source_derived"]
    if len(bone_names) != exact["bone_count"] or canonical_sha256(bone_names) != exact["bone_name_inventory_sha256"]:
        raise R3PackageError("source bone inventory no longer matches R3 seal")
    meshes = [mesh for mesh in document["meshes"] if mesh.get("name") == contract["exact_source"]["source_mesh"]]
    if len(meshes) != 1 or len(meshes[0].get("primitives", [])) != 1:
        raise R3PackageError("source mesh semantic identity changed")
    primitive = meshes[0]["primitives"][0]
    material = document["materials"][primitive["material"]]
    if canonical_sha256(material) != exact["source_glb_material_record_sha256"]:
        raise R3PackageError("source GLB material record changed")
    morph_records = primitive.get("targets", [])
    if len(morph_records) != exact["morph_target_count"] or canonical_sha256(morph_records) != exact["morph_inventory_sha256"]:
        raise R3PackageError("source morph inventory changed")
    interface_records = [
        {"vertex_index": index, "coordinate_m": list(source["positions"][index])}
        for index in contract["intersection_and_interface_requirements"]["global_interface_vertex_indices"]
    ]
    if canonical_sha256(interface_records) != exact["interface_local_coordinate_records_sha256"]:
        raise R3PackageError("source interface coordinate records changed")
    report_path = validate_exact_file(ROOT, contract["exact_source_bindings"]["inherited_intersection_report"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    pair_source = report.get("pairs")
    if not isinstance(pair_source, list) or len(pair_source) != exact["inherited_pair_count"]:
        raise R3PackageError("inherited intersection pair source changed")
    pair_records = [
        {
            "face_indices": row.get("face_indices"),
            "measurement_sha256": canonical_sha256(row),
        }
        for row in pair_source
        if isinstance(row, Mapping)
    ]
    if len(pair_records) != len(pair_source) or canonical_sha256(pair_records) != exact["inherited_pair_records_sha256"]:
        raise R3PackageError("inherited intersection measurement records changed")
    build_path = validate_exact_file(ROOT, contract["exact_source_bindings"]["build_evidence"])
    build = json.loads(build_path.read_text(encoding="utf-8"))
    immutable = build.get("immutable_component_verification", {})
    required_rest = contract["rig_and_action_requirements"]["required_armature_rest_structure_sha256"]
    if (
        immutable.get("native_rig_rest_structure_sha256_before") != required_rest
        or immutable.get("native_rig_rest_structure_sha256_after") != required_rest
    ):
        raise R3PackageError("bound native armature rest evidence changed")
    freeze_path = validate_exact_file(ROOT, contract["exact_source_bindings"]["r23_freeze_preflight"])
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    freeze_ledger = freeze.get("fresh_freeze_ledger", {})
    action_ledger = freeze.get("blender51_action_freeze_ledger", {})
    if (
        freeze_ledger.get("actions_sha256") != exact["source_action_serializer_sha256"]
        or action_ledger.get("serialized_rows_sha256") != exact["source_action_serializer_sha256"]
        or not action_ledger.get("complete_keyframe_handles_and_types_hashed")
    ):
        raise R3PackageError("bound complete action serializer evidence changed")
    materials = freeze_ledger.get("body_materials", {}).get("records", [])
    material_record = exact["preserved_material_record"]
    if not any(
        isinstance(row, Mapping)
        and row.get("name") == material_record["name"]
        and row.get("sha256") == material_record["preserved_material_state_sha256"]
        for row in materials
    ):
        raise R3PackageError("bound complete material state evidence changed")
    preserved_path = validate_exact_file(
        ROOT,
        {
            "path": contract["exact_source"]["preserved_target_blend_path"],
            "bytes": contract["exact_source"]["preserved_target_blend_bytes"],
            "sha256": contract["exact_source"]["preserved_target_blend_sha256"],
        },
    )
    preserved_summary = parse_blend_artifact(preserved_path)
    action_blocks = {
        row["name"]: row["direct_block_sha256"]
        for row in preserved_summary["semantic_ids"]["AC"]
    }
    if any(
        action_blocks.get(row["name"]) != row["direct_blend_block_sha256"]
        for row in exact["required_action_records"]
    ):
        raise R3PackageError("preserved action direct-block evidence changed")
    material_blocks = {
        row["name"]: row["direct_block_sha256"]
        for row in preserved_summary["semantic_ids"]["MA"]
    }
    if material_blocks.get(material_record["name"]) != material_record["preserved_blend_direct_material_block_sha256"]:
        raise R3PackageError("preserved material direct-block evidence changed")
    return {
        **context,
        "source_document": document,
        "source_binary": binary,
        "bone_names": bone_names,
        "interface_records": interface_records,
        "inherited_pair_records": pair_records,
    }


def _native_weight_records(context: Mapping[str, object], vertex_index: int) -> list[dict[str, object]]:
    source = context["source_mesh"]
    bones = context["bone_names"]
    records = []
    for joint, weight in zip(source["joints"][vertex_index], source["weights"][vertex_index], strict=True):
        if float(weight) > 0.0:
            records.append(
                {
                    "joint_index": int(joint),
                    "bone_name": bones[int(joint)],
                    "weight": float(weight),
                }
            )
    return records


def expected_weighted_points(context: Mapping[str, object] | None = None) -> dict[str, list[dict[str, object]]]:
    context = exact_context() if context is None else context
    expected: dict[str, list[dict[str, object]]] = {}
    for scope_name, records in {
        "outside_estar": r2.expected_outside_records(context)["POINT"],
        "outer_boundary": r2.expected_outer_boundary_records(context)["POINT"],
    }.items():
        expected[scope_name] = [
            {
                **copy.deepcopy(record),
                "native_weights": _native_weight_records(context, record["vertex_index"]),
            }
            for record in records
        ]
    return expected


def ledger(records: list[object]) -> dict[str, object]:
    return {"record_count": len(records), "records": records, "sha256": canonical_sha256(records)}


def paired_ledger(records: list[object]) -> dict[str, object]:
    return {"source": ledger(copy.deepcopy(records)), "candidate": ledger(copy.deepcopy(records))}


def _records(raw: object, failures: set[str], name: str) -> list[object]:
    if not isinstance(raw, Mapping):
        failures.add(f"{name}:missing")
        return []
    records = raw.get("records")
    valid = (
        isinstance(records, list)
        and is_strict_int(raw.get("record_count"))
        and raw.get("record_count") == len(records)
        and is_lower_sha256(raw.get("sha256"))
        and raw.get("sha256") == canonical_sha256(records)
    )
    if not valid:
        failures.add(f"{name}:ledger")
        return records if isinstance(records, list) else []
    return records


def _paired_exact(raw: object, expected: list[object], failures: set[str], name: str) -> None:
    if not isinstance(raw, Mapping) or set(raw) != {"source", "candidate"}:
        failures.add(f"{name}:paired_ledger")
        return
    source = _records(raw.get("source"), failures, f"{name}:source")
    candidate = _records(raw.get("candidate"), failures, f"{name}:candidate")
    if source != expected:
        failures.add(f"{name}:source_exact")
    if candidate != expected:
        failures.add(f"{name}:candidate_exact")


def expected_exact_bindings(context: Mapping[str, object] | None = None) -> dict[str, list[object]]:
    context = exact_context() if context is None else context
    contract = context["contract"]
    exact = contract["exact_source_derived"]
    armature = [{
        "name": contract["rig_and_action_requirements"]["required_armature_name"],
        "bone_count": exact["bone_count"],
        "bone_names": list(context["bone_names"]),
        "bone_names_sha256": exact["bone_name_inventory_sha256"],
        "rest_structure_sha256": contract["rig_and_action_requirements"]["required_armature_rest_structure_sha256"],
    }]
    morph = [{
        "morph_target_count": exact["morph_target_count"],
        "morph_inventory_sha256": exact["morph_inventory_sha256"],
    }]
    return {
        "material_inventory": [copy.deepcopy(exact["preserved_material_record"])],
        "armature_inventory": armature,
        "action_inventory": copy.deepcopy(exact["required_action_records"]),
        "morph_inventory": morph,
        "interface_local_coordinates": copy.deepcopy(context["interface_records"]),
        "inherited_intersection_measurements": copy.deepcopy(context["inherited_pair_records"]),
    }


def expected_uv_corner_records(evidence: Mapping[str, object], context: Mapping[str, object] | None = None) -> list[object]:
    context = exact_context() if context is None else context
    source = context["source_mesh"]
    topology = evidence.get("topology")
    provenance = evidence.get("provenance")
    if not isinstance(topology, Mapping) or not isinstance(provenance, Mapping):
        return []
    faces = _records(topology.get("face_ledger"), set(), "unused")
    provenance_rows = _records(provenance.get("new_vertex_ledger"), set(), "unused")
    uv_by_vertex: dict[int, list[float]] = {}
    cycle = set(context["contract"]["exact_topology"]["outer_boundary_cycle"])
    for vertex_index in cycle:
        uv_by_vertex[vertex_index] = list(source["texcoords"][vertex_index])
    for row in provenance_rows:
        if not isinstance(row, Mapping):
            continue
        vertex = row.get("vertex_index")
        triangle = row.get("source_triangle")
        barycentric = row.get("barycentric")
        if not is_strict_int(vertex) or not isinstance(triangle, list) or not isinstance(barycentric, list):
            continue
        if len(triangle) != 3 or len(barycentric) != 3:
            continue
        try:
            uv_by_vertex[vertex] = [
                sum(float(barycentric[i]) * float(source["texcoords"][triangle[i]][axis]) for i in range(3))
                for axis in range(2)
            ]
        except (IndexError, TypeError, ValueError):
            continue
    records: list[object] = []
    for face in faces:
        if not isinstance(face, Mapping) or not isinstance(face.get("vertices"), list):
            continue
        for corner, vertex in enumerate(face["vertices"]):
            if vertex not in uv_by_vertex:
                continue
            records.append({
                "face_id": face.get("face_id"),
                "corner_index": corner,
                "vertex_index": vertex,
                "layer": "TEXCOORD_0",
                "uv": uv_by_vertex[vertex],
            })
    return records


def _validate_artifact_r3(
    evidence: Mapping[str, object],
    contract: Mapping[str, object],
    failures: set[str],
    artifact_root: Path,
) -> None:
    artifact = evidence.get("artifact")
    if not isinstance(artifact, Mapping):
        failures.add("artifact_r3:missing")
        return
    try:
        path = resolve_project_path(artifact_root, artifact.get("path"))
        summary = parse_blend_artifact(path)
    except (OSError, TypeError, ValueError, BlendArtifactError) as exc:
        failures.add("artifact_r3:parseable_blend")
        failures.add("artifact_r3:semantic_identity")
        return
    if artifact.get("blend_structure") != summary:
        failures.add("artifact_r3:structure_binding")
    required = contract["artifact_semantic_identity"]
    semantic_ok = True
    for code, names in required["required_id_names"].items():
        if not set(names).issubset(_semantic_names(summary, code)):
            semantic_ok = False
    exact = contract["exact_source_derived"]
    action_blocks = {
        row["name"]: row["direct_block_sha256"]
        for row in summary["semantic_ids"]["AC"]
    }
    if any(
        action_blocks.get(row["name"]) != row["direct_blend_block_sha256"]
        for row in exact["required_action_records"]
    ):
        semantic_ok = False
    material_blocks = {
        row["name"]: row["direct_block_sha256"]
        for row in summary["semantic_ids"]["MA"]
    }
    material = exact["preserved_material_record"]
    if material_blocks.get(material["name"]) != material["preserved_blend_direct_material_block_sha256"]:
        semantic_ok = False
    if not semantic_ok:
        failures.add("artifact_r3:semantic_identity")


def _validate_boundary_coordinates(
    evidence: Mapping[str, object], context: Mapping[str, object], failures: set[str]
) -> None:
    topology = evidence.get("topology")
    protected = evidence.get("protected_records")
    if not isinstance(topology, Mapping):
        failures.add("topology_r3:missing")
        return
    coordinate_rows = _records(topology.get("vertex_coordinate_ledger"), failures, "topology_r3:coordinates")
    coordinate_map = {
        row.get("vertex_index"): row.get("coordinate_m")
        for row in coordinate_rows
        if isinstance(row, Mapping)
    }
    expected_points = r2.expected_outer_boundary_records(context)["POINT"]
    expected_map = {row["vertex_index"]: row["coordinate_m"] for row in expected_points}
    if set(expected_map) - set(coordinate_map) or any(
        not isinstance(coordinate_map.get(index), list)
        or not vector_close(coordinate_map[index], coordinate)
        for index, coordinate in expected_map.items()
    ):
        failures.add("topology_r3:boundary_coordinates_equal_source")
    try:
        candidate_rows = protected["outer_boundary"]["POINT"]["candidate"]["records"]
        protected_map = {row["vertex_index"]: row["coordinate_m"] for row in candidate_rows}
    except (KeyError, TypeError):
        protected_map = {}
    if protected_map != expected_map or any(coordinate_map.get(index) != coordinate for index, coordinate in protected_map.items()):
        failures.add("topology_r3:boundary_coordinates_equal_protected_point_ledger")


def _validate_uvs(evidence: Mapping[str, object], context: Mapping[str, object], failures: set[str]) -> None:
    provenance = evidence.get("provenance")
    topology = evidence.get("topology")
    if not isinstance(provenance, Mapping) or not isinstance(topology, Mapping):
        failures.add("uv_r3:missing")
        return
    rows = _records(provenance.get("new_vertex_ledger"), failures, "uv_r3:provenance")
    source = context["source_mesh"]
    for row in rows:
        if not isinstance(row, Mapping):
            failures.add("uv_r3:source_derived_provenance")
            continue
        triangle = row.get("source_triangle")
        barycentric = row.get("barycentric")
        uv_records = row.get("uv_records")
        try:
            expected = [
                sum(float(barycentric[i]) * float(source["texcoords"][triangle[i]][axis]) for i in range(3))
                for axis in range(2)
            ]
            actual = uv_records[0]["uv"]
            valid = (
                len(uv_records) == 1
                and uv_records[0].get("layer") == "TEXCOORD_0"
                and isinstance(actual, list)
                and vector_close(actual, expected)
            )
        except (IndexError, KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            failures.add("uv_r3:source_derived_provenance")
    expected_corners = expected_uv_corner_records(evidence, context)
    actual_corners = _records(topology.get("uv_corner_ledger"), failures, "uv_r3:corner_ledger")
    if actual_corners != expected_corners or len(expected_corners) != sum(
        len(row.get("vertices", [])) for row in _records(topology.get("face_ledger"), set(), "unused") if isinstance(row, Mapping)
    ):
        failures.add("uv_r3:complete_exact_corner_topology")


def _validate_exact_bindings(evidence: Mapping[str, object], context: Mapping[str, object], failures: set[str]) -> None:
    raw = evidence.get("exact_bindings_r3")
    if not isinstance(raw, Mapping):
        failures.add("exact_bindings_r3:missing")
        return
    expected = expected_exact_bindings(context)
    if set(raw) != set(expected):
        failures.add("exact_bindings_r3:inventory")
    for name, records in expected.items():
        _paired_exact(raw.get(name), records, failures, f"exact_bindings_r3:{name}")
    protected = evidence.get("protected_attributes_r3")
    weighted = expected_weighted_points(context)
    if not isinstance(protected, Mapping) or set(protected) != set(weighted):
        failures.add("protected_attributes_r3:inventory")
        return
    for name, records in weighted.items():
        _paired_exact(protected.get(name), records, failures, f"protected_attributes_r3:{name}:weighted_points")


def _caller_contract_failures(caller: Mapping[str, object] | None, sealed: Mapping[str, object]) -> set[str]:
    if caller is None:
        return set()
    failures = contract_bound_failures(caller, "contract:caller")
    try:
        same = canonical_json(caller) == canonical_json(sealed)
    except (TypeError, ValueError):
        same = False
    if not same:
        failures.add("contract:caller_mapping_identity")
    return failures


def evaluate_measured_candidate_evidence(
    evidence: Mapping[str, object] | None,
    contract: Mapping[str, object] | None = None,
    *,
    binding_root: Path = ROOT,
    artifact_root: Path = ROOT,
) -> dict[str, object]:
    sealed = load_sealed_contract()
    schema = sealed["authorized_implementation"]["required_gate_schema"]
    caller_failures = _caller_contract_failures(contract, sealed)
    if not isinstance(evidence, Mapping):
        return {
            "schema": schema,
            "eligible": False,
            "failure_names": sorted(caller_failures | {"measured_candidate_evidence_absent"}),
        }
    parent_result = r2.evaluate_measured_candidate_evidence(
        evidence,
        sealed,
        binding_root=binding_root,
        artifact_root=artifact_root,
    )
    failures = set(parent_result.get("failure_names", [])) | caller_failures
    context = exact_context()
    _validate_artifact_r3(evidence, sealed, failures, artifact_root)
    _validate_boundary_coordinates(evidence, context, failures)
    _validate_uvs(evidence, context, failures)
    _validate_exact_bindings(evidence, context, failures)
    return {
        "schema": schema,
        "eligible": not failures,
        "failure_names": sorted(failures),
        "derived": {
            **parent_result.get("derived", {}),
            "actual_blend_parse_required": True,
            "sealed_caller_contract_required": True,
            "exact_source_derived_r3_bindings_required": True,
        },
    }


def package_inventory_status(package: Path = PACKAGE) -> dict[str, object]:
    pre = {
        "CHECKPOINT.md",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R3_CONTRACT.json",
        "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R3_PROPOSAL.md",
        "PACKAGE_MANIFEST.json",
    }
    post = pre | {"INDEPENDENT_STATIC_AUDIT.md"}
    actual = {path.name for path in package.iterdir() if path.is_file()}
    if actual == pre:
        state = "PRE_AUDIT_EXACT"
    elif actual == post:
        state = "POST_AUDIT_EXACT"
    else:
        state = "INVALID"
    return {
        "state": state,
        "actual": sorted(actual),
        "pre_audit": sorted(pre),
        "post_audit": sorted(post),
        "exact_allowlist_passed": state != "INVALID",
    }


def static_evaluation() -> dict[str, object]:
    contract = load_sealed_contract()
    context = exact_context()
    return {
        "schema": "kira.avatar.r24.intrinsic_curved_annulus_structured_retopology_r3_static_evaluation.v1",
        "status": "STATIC_R3_FAIL_CLOSED_GATE_IMPLEMENTED_FRESH_INDEPENDENT_AUDIT_REQUIRED",
        "parent_binding_count": len(validate_parent_bindings(contract)),
        "source_domain": {
            "estar_face_count": len(context["domains"]["estar"]),
            "outside_face_count": len(context["domains"]["outside"]),
            "bone_count": len(context["bone_names"]),
            "inherited_pair_count": len(context["inherited_pair_records"]),
            "interface_vertex_count": len(context["interface_records"]),
        },
        "future_measured_candidate": evaluate_measured_candidate_evidence(None, contract),
        "package_inventory": package_inventory_status(),
        "blender_used": False,
        "mesh_mutated": False,
        "candidate_created": False,
        "body_repair_claimed": False,
        "execution_authority_granted": False,
        "fresh_independent_static_audit_required": True,
    }


def main() -> int:
    print(json.dumps(static_evaluation(), sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
