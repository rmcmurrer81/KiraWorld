"""Fail-closed preparation for one inactive MakeHuman rigged carrier.

This module is deliberately Blender-free.  It binds the qualified source,
the exact CC0 MakeHuman skeleton and weights, the append-only output paths,
and the command-line safety flags required by the later Blender workers.  It
does not create an authorization record, start Blender, create a body, assign
a person, or grant anatomy/runtime/public authority.
"""

from __future__ import annotations

from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Iterable, Mapping


CONFIG_SCHEMA_VERSION = 1
CONTROLLER_ID = "makehuman_adult_female_rigged_carrier_v1"
ONE_RUN_AUTHORIZATION_SCHEMA = (
    "kira.avatar.makehuman_rigged_carrier.one_run_authorization.v1"
)
ONE_RUN_AUTHORIZATION_STATUS = "AUTHORIZED_ONE_INACTIVE_CARRIER_BUILD_AND_AUDIT"
REQUIRED_BLENDER_FLAGS = ("--background", "--factory-startup", "--disable-autoexec")
CONTROLLER_RELATIVE_PATH = "Core/avatar_makehuman_rigged_carrier.py"
BUILDER_RELATIVE_PATH = (
    "tools/blender_build_makehuman_adult_female_rigged_carrier_inactive.py"
)
AUDITOR_RELATIVE_PATH = "tools/blender_audit_makehuman_adult_female_rigged_carrier.py"
INTERSECTION_AUDITOR_RELATIVE_PATH = "tools/blender_exact_mesh_intersections.py"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
MAX_COMPRESSED_BLEND_BYTES = 16 * 1024 * 1024
MAX_DECOMPRESSED_BLEND_BYTES = 64 * 1024 * 1024

EXPECTED_POSE_IDS = (
    "neutral_standing",
    "seated_contact",
    "supine",
    "left_knee_flexion",
    "right_knee_flexion",
    "bilateral_knee_flexion",
    "bounded_hip_flexion_thigh_separation_diagnostic",
)
EXPECTED_PELVIC_GROUPS = (
    "AFES_LANDMARK__mons_pubis",
    "AFES_LANDMARK__labia_majora",
    "AFES_LANDMARK__labia_minora",
    "AFES_LANDMARK__clitoral_hood",
    "AFES_LANDMARK__clitoris",
    "AFES_LANDMARK__vestibule",
    "AFES_LANDMARK__urethral_opening",
    "AFES_LANDMARK__vaginal_opening",
    "AFES_LANDMARK__fourchette",
    "AFES_LANDMARK__perineal_path",
)

CONFIG_KEYS = {
    "schema_version",
    "controller_id",
    "status",
    "candidate",
    "source",
    "source_build_inputs",
    "skeleton",
    "output",
    "pose_audit",
    "separation",
    "authority",
}
AUTHORIZATION_KEYS = {
    "schema",
    "status",
    "one_run_id",
    "issued_at_utc",
    "config_sha256",
    "source_sha256",
    "candidate_blend_path",
    "build_report_path",
    "audit_report_path",
    "blender_executable_sha256",
    "preflight_receipt_sha256",
    "controller_sha256",
    "builder_sha256",
    "auditor_sha256",
    "intersection_auditor_sha256",
    "build_allowed",
    "audit_allowed",
    "background_required",
    "factory_startup_required",
    "autoexec_disabled_required",
    "overwrite_allowed",
    "source_mutation_allowed",
    "hair_allowed",
    "clothing_allowed",
    "internal_anatomy_allowed",
    "identity_styling_allowed",
    "runtime_activation_allowed",
    "public_export_allowed",
}


class RiggedCarrierError(ValueError):
    """Raised when an exact input or safety boundary fails closed."""


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RiggedCarrierError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path, label: str = "JSON") -> dict[str, Any]:
    try:
        value = json.loads(
            native_filesystem_path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_json_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                RiggedCarrierError(f"{label} contains non-finite number: {token}")
            ),
        )
    except RiggedCarrierError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RiggedCarrierError(f"cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise RiggedCarrierError(f"{label} must be a JSON object")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with native_filesystem_path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise RiggedCarrierError(f"cannot hash artifact: {path}") from exc
    return digest.hexdigest()


def native_filesystem_path(path: Path) -> Path:
    """Return a Windows extended-length spelling without resolving the target."""

    absolute = path.absolute()
    text = str(absolute)
    if os.name != "nt" or text.startswith("\\\\?\\"):
        return absolute
    if text.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + text[2:])
    return Path("\\\\?\\" + text)


def same_filesystem_path(first: Path, second: Path) -> bool:
    """Compare lexical absolute paths while tolerating Windows long-path prefixes."""

    def identity(path: Path) -> str:
        value = str(path.absolute())
        if value.startswith("\\\\?\\UNC\\"):
            value = "\\\\" + value[8:]
        elif value.startswith("\\\\?\\"):
            value = value[4:]
        return os.path.normcase(os.path.normpath(value))

    return identity(first) == identity(second)


def promote_file_no_replace(staging_path: Path, destination_path: Path) -> dict[str, Any]:
    """Promote one regular file on the same volume without replacing a name."""

    native_staging = native_filesystem_path(staging_path)
    native_destination = native_filesystem_path(destination_path)
    try:
        staging_device = native_filesystem_path(staging_path.parent).stat().st_dev
        destination_device = native_filesystem_path(destination_path.parent).stat().st_dev
    except OSError as exc:
        raise RiggedCarrierError("cannot inspect promotion directories") from exc
    if staging_device != destination_device:
        raise RiggedCarrierError("staging and destination must share one volume")
    try:
        staging_metadata = os.lstat(native_staging)
    except OSError as exc:
        raise RiggedCarrierError("staging file is absent") from exc
    attributes = int(getattr(staging_metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISREG(staging_metadata.st_mode) or attributes & reparse_flag:
        raise RiggedCarrierError("staging path must be a regular non-reparse file")
    if int(getattr(staging_metadata, "st_nlink", 1)) != 1:
        raise RiggedCarrierError("staging file must have exactly one link")
    if native_destination.exists() or native_destination.is_symlink():
        raise RiggedCarrierError("destination already exists; replacement is forbidden")
    staged_bytes = staging_metadata.st_size
    staged_sha = sha256_file(staging_path)
    try:
        os.link(native_staging, native_destination, follow_symlinks=False)
    except FileExistsError as exc:
        raise RiggedCarrierError("destination appeared; replacement is forbidden") from exc
    except OSError as exc:
        raise RiggedCarrierError("same-volume no-replace promotion failed") from exc
    try:
        os.unlink(native_staging)
    except OSError as exc:
        try:
            os.unlink(native_destination)
        except OSError:
            pass
        raise RiggedCarrierError("could not retire private staging name") from exc
    try:
        final_metadata = os.lstat(native_destination)
    except OSError as exc:
        raise RiggedCarrierError("promoted destination is absent") from exc
    final_attributes = int(getattr(final_metadata, "st_file_attributes", 0))
    if (
        not stat.S_ISREG(final_metadata.st_mode)
        or final_attributes & reparse_flag
        or int(getattr(final_metadata, "st_nlink", 1)) != 1
        or final_metadata.st_size != staged_bytes
        or sha256_file(destination_path) != staged_sha
    ):
        raise RiggedCarrierError("promoted destination differs from staged file")
    return {
        "bytes": staged_bytes,
        "sha256": staged_sha,
        "promotion": "same_volume_hardlink_create_no_replace_then_unlink_private_name",
    }


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RiggedCarrierError(f"{label} must be an object")
    return dict(value)


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise RiggedCarrierError(f"{label} must be a list")
    return value


def _exact_keys(value: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    actual = set(value)
    expected_set = set(expected)
    if actual != expected_set:
        missing = sorted(expected_set - actual)
        extra = sorted(actual - expected_set)
        raise RiggedCarrierError(
            f"{label} fields differ; missing={missing!r}, extra={extra!r}"
        )


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RiggedCarrierError(f"{label} must be a non-empty string")
    return value.strip()


def _sha(value: Any, label: str) -> str:
    digest = _text(value, label).lower()
    if not SHA256_RE.fullmatch(digest):
        raise RiggedCarrierError(f"{label} must be lowercase SHA-256")
    return digest


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RiggedCarrierError(f"{label} must be a positive integer")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RiggedCarrierError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise RiggedCarrierError(f"{label} must be finite")
    return result


def _require_bool(value: Any, expected: bool, label: str) -> None:
    if value is not expected:
        raise RiggedCarrierError(f"{label} must be {expected}")


def evaluate_pose_gate(
    pose_id: str,
    metrics: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, bool]:
    """Evaluate the pure pass/fail portion of one pose audit."""

    expected_metrics = {
        "exact_intersection_pairs",
        "pelvic_minimum_edge_ratio",
        "pelvic_maximum_edge_ratio",
        "pelvic_minimum_triangle_area_ratio",
        "global_minimum_edge_ratio",
        "global_maximum_edge_ratio",
        "global_minimum_triangle_area_ratio",
        "global_maximum_triangle_area_ratio",
        "orientation_reversal_triangle_count",
        "signed_volume_ratio",
        "rotation_application_passed",
        "requested_rotation_count",
        "moved_vertex_count",
        "maximum_displacement_m",
        "rotated_bone_group_response_passed",
    }
    _exact_keys(metrics, expected_metrics, "pose metrics")
    for key in (
        "exact_intersection_pairs",
        "orientation_reversal_triangle_count",
        "requested_rotation_count",
        "moved_vertex_count",
    ):
        value = metrics[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RiggedCarrierError(f"pose metric {key} must be a nonnegative integer")
    for key in ("rotation_application_passed", "rotated_bone_group_response_passed"):
        if type(metrics[key]) is not bool:
            raise RiggedCarrierError(f"pose metric {key} must be Boolean")
    numeric = {
        key: _finite(metrics[key], f"pose metric {key}")
        for key in expected_metrics
        if key
        not in {
            "exact_intersection_pairs",
            "orientation_reversal_triangle_count",
            "requested_rotation_count",
            "moved_vertex_count",
            "rotation_application_passed",
            "rotated_bone_group_response_passed",
        }
    }
    neutral = pose_id == "neutral_standing"
    movement = bool(
        (
            metrics["requested_rotation_count"] == 0
            and numeric["maximum_displacement_m"]
            <= float(thresholds["maximum_rest_pose_surface_displacement_m"])
        )
        if neutral
        else (
            metrics["requested_rotation_count"] > 0
            and metrics["moved_vertex_count"]
            >= int(thresholds["minimum_nonneutral_pose_moved_vertex_count"])
            and numeric["maximum_displacement_m"]
            >= float(thresholds["minimum_nonneutral_pose_maximum_displacement_m"])
            and metrics["rotated_bone_group_response_passed"] is True
        )
    )
    intersection = bool(
        metrics["exact_intersection_pairs"]
        <= int(thresholds["maximum_exact_nonadjacent_self_intersection_pairs_per_pose"])
    )
    pelvic = bool(
        numeric["pelvic_minimum_edge_ratio"]
        >= float(thresholds["minimum_pelvic_patch_edge_ratio"])
        and numeric["pelvic_maximum_edge_ratio"]
        <= float(thresholds["maximum_pelvic_patch_edge_ratio"])
        and numeric["pelvic_minimum_triangle_area_ratio"]
        >= float(thresholds["minimum_pelvic_patch_triangle_area_ratio"])
    )
    global_deformation = bool(
        numeric["global_minimum_edge_ratio"]
        >= float(thresholds["minimum_global_edge_ratio"])
        and numeric["global_maximum_edge_ratio"]
        <= float(thresholds["maximum_global_edge_ratio"])
        and numeric["global_minimum_triangle_area_ratio"]
        >= float(thresholds["minimum_global_triangle_area_ratio"])
        and numeric["global_maximum_triangle_area_ratio"]
        <= float(thresholds["maximum_global_triangle_area_ratio"])
        and metrics["orientation_reversal_triangle_count"]
        <= int(thresholds["maximum_global_orientation_reversal_triangle_count"])
        and numeric["signed_volume_ratio"]
        >= float(thresholds["minimum_signed_volume_ratio"])
    )
    rotation = metrics["rotation_application_passed"] is True
    return {
        "intersection": intersection,
        "pelvic": pelvic,
        "global_deformation": global_deformation,
        "rotation_application": rotation,
        "movement": movement,
        "passed": bool(
            intersection and pelvic and global_deformation and rotation and movement
        ),
    }


def _is_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(native_filesystem_path(path))
    except OSError as exc:
        raise RiggedCarrierError(f"cannot inspect path: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def _relative_parts(raw: Any, label: str) -> tuple[str, ...]:
    text = _text(raw, label)
    if "\\" in text or "\x00" in text:
        raise RiggedCarrierError(f"{label} must use a safe project-relative POSIX path")
    pure = PurePosixPath(text)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise RiggedCarrierError(f"{label} must be a safe project-relative path")
    if ":" in pure.parts[0]:
        raise RiggedCarrierError(f"{label} must not contain a drive prefix")
    return tuple(pure.parts)


def project_path(
    project_root: Path,
    raw: Any,
    label: str,
    *,
    must_exist: bool,
    reject_hardlinks: bool = True,
) -> Path:
    root = project_root.resolve(strict=True)
    parts = _relative_parts(raw, label)
    candidate = root.joinpath(*parts)
    try:
        common = os.path.commonpath(
            (os.path.normcase(str(root)), os.path.normcase(str(candidate.absolute())))
        )
    except ValueError as exc:
        raise RiggedCarrierError(f"{label} escapes project root") from exc
    if common != os.path.normcase(str(root)):
        raise RiggedCarrierError(f"{label} escapes project root")

    current = root
    if _is_reparse(current):
        raise RiggedCarrierError(f"{label} traverses a reparse point")
    for part in parts:
        current = current / part
        native_current = native_filesystem_path(current)
        if native_current.exists() or native_current.is_symlink():
            if _is_reparse(current):
                raise RiggedCarrierError(f"{label} traverses a reparse point")
    if must_exist:
        native_candidate = native_filesystem_path(candidate)
        if not native_candidate.is_file():
            raise RiggedCarrierError(f"{label} does not exist: {candidate}")
        try:
            metadata = native_candidate.stat()
        except OSError as exc:
            raise RiggedCarrierError(f"cannot inspect {label}") from exc
        if reject_hardlinks and int(getattr(metadata, "st_nlink", 1)) != 1:
            raise RiggedCarrierError(f"{label} must not be multiply linked")
    return candidate


def _bind_file(
    project_root: Path,
    binding: Mapping[str, Any],
    label: str,
) -> tuple[Path, dict[str, Any]]:
    _exact_keys(binding, {"path", "bytes", "sha256"}, label)
    path = project_path(project_root, binding.get("path"), f"{label}.path", must_exist=True)
    expected_bytes = _positive_int(binding.get("bytes"), f"{label}.bytes")
    expected_sha = _sha(binding.get("sha256"), f"{label}.sha256")
    try:
        actual_bytes = native_filesystem_path(path).stat().st_size
    except OSError as exc:
        raise RiggedCarrierError(f"cannot inspect {label}") from exc
    actual_sha = sha256_file(path)
    if actual_bytes != expected_bytes:
        raise RiggedCarrierError(f"{label} byte count mismatch")
    if actual_sha != expected_sha:
        raise RiggedCarrierError(f"{label} SHA-256 mismatch")
    return path, {"path": str(binding["path"]), "bytes": actual_bytes, "sha256": actual_sha}


def _validate_compressed_blend(
    path: Path,
    source: Mapping[str, Any],
    *,
    verify_decompressed: bool,
) -> None:
    expected_raw = _positive_int(source.get("bytes"), "source.bytes")
    expected_size = _positive_int(
        source.get("decompressed_bytes"), "source.decompressed_bytes"
    )
    expected_sha = _sha(
        source.get("decompressed_sha256"), "source.decompressed_sha256"
    )
    if expected_raw > MAX_COMPRESSED_BLEND_BYTES or expected_size > MAX_DECOMPRESSED_BLEND_BYTES:
        raise RiggedCarrierError("source Blender container exceeds its bounded size")
    try:
        with native_filesystem_path(path).open("rb") as stream:
            header = stream.read(7)
    except OSError as exc:
        raise RiggedCarrierError("cannot inspect source Blender container") from exc
    if header == b"BLENDER":
        if expected_raw != expected_size or sha256_file(path) != expected_sha:
            raise RiggedCarrierError("raw Blender source decompression binding is inconsistent")
        return
    if header[:4] != ZSTD_MAGIC:
        raise RiggedCarrierError("source does not contain a Blender file")
    if not verify_decompressed:
        return
    try:
        from compression import zstd
    except ImportError as exc:  # pragma: no cover - runtime capability
        raise RiggedCarrierError("zstd Blender inspection is unavailable") from exc

    digest = hashlib.sha256()
    total = 0
    blender_header = b""
    try:
        with native_filesystem_path(path).open("rb") as raw_stream:
            with zstd.ZstdFile(raw_stream, "rb") as stream:
                while True:
                    read_size = min(256 * 1024, max(1, expected_size - total + 1))
                    block = stream.read(read_size)
                    if not block:
                        break
                    if len(blender_header) < 7:
                        blender_header += block[: 7 - len(blender_header)]
                    total += len(block)
                    if total > expected_size:
                        raise RiggedCarrierError("source decompressed size exceeds bound")
                    digest.update(block)
    except RiggedCarrierError:
        raise
    except (OSError, EOFError, ValueError, zstd.ZstdError) as exc:
        raise RiggedCarrierError("source Blender container is malformed") from exc
    if total != expected_size or blender_header != b"BLENDER":
        raise RiggedCarrierError("source decompressed Blender binding differs")
    if digest.hexdigest() != expected_sha:
        raise RiggedCarrierError("source decompressed SHA-256 mismatch")


def _base_vertex_count(path: Path) -> int:
    count = 0
    try:
        with native_filesystem_path(path).open("r", encoding="utf-8") as stream:
            for raw in stream:
                if raw.startswith("v "):
                    fields = raw.split()
                    if len(fields) < 4:
                        raise RiggedCarrierError("base OBJ has malformed vertex row")
                    for token in fields[1:4]:
                        if not math.isfinite(float(token)):
                            raise RiggedCarrierError("base OBJ has non-finite vertex")
                    count += 1
    except (OSError, UnicodeError, ValueError) as exc:
        raise RiggedCarrierError("cannot validate base OBJ") from exc
    if count <= 0:
        raise RiggedCarrierError("base OBJ contains no vertices")
    return count


def load_transformed_makehuman_vertices(
    base_path: Path,
    targets: Iterable[tuple[Path, float]],
    target_height_m: float,
) -> tuple[list[tuple[float, float, float]], dict[str, float]]:
    """Recreate MakeHuman's exact macro frame without importing MakeHuman."""

    vertices: list[list[float]] = []
    used_body_vertices: set[int] = set()
    current_group = ""
    try:
        with native_filesystem_path(base_path).open("r", encoding="utf-8") as stream:
            for raw in stream:
                line = raw.strip()
                if line.startswith("v "):
                    fields = line.split()
                    if len(fields) < 4:
                        raise RiggedCarrierError("base OBJ has malformed vertex row")
                    point = [float(token) for token in fields[1:4]]
                    if not all(math.isfinite(value) for value in point):
                        raise RiggedCarrierError("base OBJ has non-finite vertex")
                    vertices.append(point)
                elif line.startswith("g "):
                    current_group = line[2:].strip()
                elif current_group == "body" and line.startswith("f "):
                    for token in line.split()[1:]:
                        raw_index = int(token.split("/", 1)[0])
                        index = raw_index - 1 if raw_index > 0 else len(vertices) + raw_index
                        if not 0 <= index < len(vertices):
                            raise RiggedCarrierError("base OBJ body face index is invalid")
                        used_body_vertices.add(index)
    except RiggedCarrierError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise RiggedCarrierError("cannot parse MakeHuman base OBJ") from exc
    if not vertices or not used_body_vertices:
        raise RiggedCarrierError("MakeHuman base OBJ body is empty")

    for path, raw_weight in targets:
        weight = _finite(raw_weight, "macro target weight")
        try:
            with native_filesystem_path(path).open("r", encoding="utf-8") as stream:
                for raw in stream:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    fields = line.split()
                    if len(fields) != 4:
                        raise RiggedCarrierError("macro target has malformed row")
                    index = int(fields[0])
                    if not 0 <= index < len(vertices):
                        raise RiggedCarrierError("macro target index is invalid")
                    delta = [float(token) for token in fields[1:4]]
                    if not all(math.isfinite(value) for value in delta):
                        raise RiggedCarrierError("macro target has non-finite displacement")
                    for axis in range(3):
                        vertices[index][axis] += delta[axis] * weight
        except RiggedCarrierError:
            raise
        except (OSError, UnicodeError, ValueError) as exc:
            raise RiggedCarrierError("cannot apply MakeHuman macro target") from exc

    low_y = min(vertices[index][1] for index in used_body_vertices)
    high_y = max(vertices[index][1] for index in used_body_vertices)
    source_height = high_y - low_y
    height = _finite(target_height_m, "target_height_m")
    if source_height <= 1.0e-8 or height <= 0.0:
        raise RiggedCarrierError("MakeHuman source or target height is invalid")
    scale = height / source_height
    transformed = [
        (point[0] * scale, -point[2] * scale, (point[1] - low_y) * scale)
        for point in vertices
    ]
    return transformed, {
        "source_vertex_count": len(vertices),
        "source_body_vertex_count": len(used_body_vertices),
        "source_floor_y": float(low_y),
        "source_height_units": float(source_height),
        "target_height_m": float(height),
        "uniform_scale": float(scale),
    }


def resolve_makehuman_skeleton_geometry(
    skeleton_payload: Mapping[str, Any],
    transformed_vertices: list[tuple[float, float, float]],
) -> dict[str, Any]:
    """Resolve joint positions, bone endpoints and roll-plane normals."""

    joints = _mapping(skeleton_payload.get("joints"), "skeleton.joints")
    bones = _mapping(skeleton_payload.get("bones"), "skeleton.bones")
    planes = _mapping(skeleton_payload.get("planes"), "skeleton.planes")
    joint_positions: dict[str, tuple[float, float, float]] = {}
    for name, raw in joints.items():
        indices = _joint_indices(raw, f"joint {name}", len(transformed_vertices))
        joint_positions[name] = tuple(
            sum(transformed_vertices[index][axis] for index in indices) / len(indices)
            for axis in range(3)
        )

    def subtract(first: tuple[float, ...], second: tuple[float, ...]) -> tuple[float, float, float]:
        return tuple(first[axis] - second[axis] for axis in range(3))  # type: ignore[return-value]

    def cross(first: tuple[float, ...], second: tuple[float, ...]) -> tuple[float, float, float]:
        return (
            first[1] * second[2] - first[2] * second[1],
            first[2] * second[0] - first[0] * second[2],
            first[0] * second[1] - first[1] * second[0],
        )

    def normalize(value: tuple[float, ...], label: str) -> tuple[float, float, float]:
        length = math.sqrt(sum(component * component for component in value))
        if length <= 1.0e-10:
            raise RiggedCarrierError(f"{label} is degenerate")
        return tuple(component / length for component in value)  # type: ignore[return-value]

    plane_normals: dict[str, tuple[float, float, float]] = {}
    for name, raw in planes.items():
        joint_names = _list(raw, f"plane {name}")
        if len(joint_names) != 3 or any(value not in joint_positions for value in joint_names):
            raise RiggedCarrierError(f"plane {name} is unresolved")
        first, second, third = (joint_positions[value] for value in joint_names)
        pvec = normalize(subtract(second, first), f"plane {name} first edge")
        yvec = normalize(subtract(third, second), f"plane {name} second edge")
        plane_normals[name] = normalize(cross(yvec, pvec), f"plane {name} normal")

    bone_records: dict[str, dict[str, Any]] = {}
    minimum_length = math.inf
    maximum_length = 0.0
    for name in _topological_bones(bones):
        record = _mapping(bones[name], f"bone {name}")
        head = joint_positions[str(record["head"])]
        tail = joint_positions[str(record["tail"])]
        length = math.sqrt(sum((tail[axis] - head[axis]) ** 2 for axis in range(3)))
        if not math.isfinite(length) or length <= 1.0e-7:
            raise RiggedCarrierError(f"bone {name} has zero or invalid length")
        plane_name = str(record["rotation_plane"])
        normal = plane_normals[plane_name]
        minimum_length = min(minimum_length, length)
        maximum_length = max(maximum_length, length)
        bone_records[name] = {
            "head": list(head),
            "tail": list(tail),
            "parent": record.get("parent"),
            "roll_plane": plane_name,
            "roll_normal": list(normal),
            "length_m": length,
        }
    return {
        "joint_positions": {name: list(value) for name, value in joint_positions.items()},
        "bones": bone_records,
        "bone_order": _topological_bones(bones),
        "minimum_bone_length_m": minimum_length,
        "maximum_bone_length_m": maximum_length,
    }


def _validate_target(path: Path, vertex_count: int, label: str) -> int:
    changed: set[int] = set()
    try:
        with native_filesystem_path(path).open("r", encoding="utf-8") as stream:
            for raw in stream:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                fields = line.split()
                if len(fields) != 4:
                    raise RiggedCarrierError(f"{label} has malformed target row")
                index = int(fields[0])
                if not 0 <= index < vertex_count:
                    raise RiggedCarrierError(f"{label} references vertex outside base OBJ")
                if not all(math.isfinite(float(token)) for token in fields[1:]):
                    raise RiggedCarrierError(f"{label} has non-finite displacement")
                changed.add(index)
    except RiggedCarrierError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise RiggedCarrierError(f"cannot validate {label}") from exc
    return len(changed)


def _joint_indices(value: Any, label: str, vertex_count: int) -> tuple[int, ...]:
    raw_values = value if isinstance(value, list) else [value]
    if not raw_values:
        raise RiggedCarrierError(f"{label} must reference at least one vertex")
    indices: list[int] = []
    for raw in raw_values:
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise RiggedCarrierError(f"{label} contains a non-integer vertex")
        if not 0 <= raw < vertex_count:
            raise RiggedCarrierError(f"{label} references vertex outside base OBJ")
        indices.append(raw)
    if len(indices) != len(set(indices)):
        raise RiggedCarrierError(f"{label} repeats a vertex index")
    return tuple(indices)


def _topological_bones(bones: Mapping[str, Any]) -> list[str]:
    parents: dict[str, str | None] = {}
    children: dict[str, list[str]] = {name: [] for name in bones}
    roots: list[str] = []
    for name, raw in bones.items():
        record = _mapping(raw, f"skeleton bone {name}")
        parent = record.get("parent")
        if parent is not None and (not isinstance(parent, str) or parent not in bones):
            raise RiggedCarrierError(f"skeleton bone {name} has invalid parent")
        parents[name] = parent
        if parent is None:
            roots.append(name)
        else:
            children[parent].append(name)
    if roots != ["root"]:
        raise RiggedCarrierError("skeleton must have exactly the root bone as root")
    order: list[str] = []
    queue: deque[str] = deque(roots)
    while queue:
        name = queue.popleft()
        order.append(name)
        queue.extend(children[name])
    if len(order) != len(bones):
        raise RiggedCarrierError("skeleton hierarchy is cyclic or disconnected")
    return order


def validate_source_definition(
    skeleton_payload: Mapping[str, Any],
    weights_payload: Mapping[str, Any],
    *,
    vertex_count: int,
    expected_bones: int,
    expected_weight_groups: int,
) -> dict[str, Any]:
    if skeleton_payload.get("name") != "MakeHuman default skeleton":
        raise RiggedCarrierError("unexpected MakeHuman skeleton name")
    if skeleton_payload.get("license") != "CC0":
        raise RiggedCarrierError("MakeHuman skeleton is not marked CC0")
    if skeleton_payload.get("weights_file") != "default_weights.mhw":
        raise RiggedCarrierError("MakeHuman skeleton weights_file differs")
    bones = _mapping(skeleton_payload.get("bones"), "skeleton.bones")
    joints = _mapping(skeleton_payload.get("joints"), "skeleton.joints")
    planes = _mapping(skeleton_payload.get("planes"), "skeleton.planes")
    if len(bones) != expected_bones:
        raise RiggedCarrierError("MakeHuman bone count differs")
    joint_map = {
        name: _joint_indices(value, f"joint {name}", vertex_count)
        for name, value in joints.items()
    }
    order = _topological_bones(bones)
    for name, raw in bones.items():
        record = _mapping(raw, f"skeleton bone {name}")
        _exact_keys(
            record,
            {"head", "parent", "reference", "rotation_plane", "tail"},
            f"skeleton bone {name}",
        )
        if record.get("head") not in joint_map or record.get("tail") not in joint_map:
            raise RiggedCarrierError(f"skeleton bone {name} has an unresolved endpoint")
        plane_name = record.get("rotation_plane")
        if not isinstance(plane_name, str) or plane_name not in planes:
            raise RiggedCarrierError(f"skeleton bone {name} has an unresolved roll plane")
    for name, raw in planes.items():
        values = _list(raw, f"plane {name}")
        if len(values) != 3 or any(value not in joint_map for value in values):
            raise RiggedCarrierError(f"plane {name} must bind exactly three known joints")

    if weights_payload.get("license") != "CC0":
        raise RiggedCarrierError("MakeHuman weights are not marked CC0")
    weight_groups = _mapping(weights_payload.get("weights"), "weights.weights")
    if len(weight_groups) != expected_weight_groups:
        raise RiggedCarrierError("MakeHuman weight-group count differs")
    missing_bones = sorted(set(weight_groups) - set(bones))
    if missing_bones:
        raise RiggedCarrierError(f"weighted groups lack bones: {missing_bones!r}")
    assignment_count = 0
    weighted_vertices: set[int] = set()
    for name, raw in weight_groups.items():
        assignments = _list(raw, f"weight group {name}")
        if not assignments:
            raise RiggedCarrierError(f"weight group {name} is empty")
        for row in assignments:
            if not isinstance(row, list) or len(row) != 2:
                raise RiggedCarrierError(f"weight group {name} has malformed assignment")
            index, raw_weight = row
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < vertex_count:
                raise RiggedCarrierError(f"weight group {name} references an invalid vertex")
            weight = _finite(raw_weight, f"weight group {name} weight")
            if not 0.0 < weight <= 1.0:
                raise RiggedCarrierError(f"weight group {name} has weight outside (0, 1]")
            weighted_vertices.add(index)
            assignment_count += 1
    return {
        "bone_count": len(bones),
        "joint_count": len(joints),
        "plane_count": len(planes),
        "weight_group_count": len(weight_groups),
        "weight_assignment_count": assignment_count,
        "weighted_source_vertex_count": len(weighted_vertices),
        "weighted_groups_missing_bones": missing_bones,
        "bones_without_weight_groups": sorted(set(bones) - set(weight_groups)),
        "breadth_first_bone_order": order,
    }


def _validate_config_shape(config: Mapping[str, Any]) -> None:
    _exact_keys(config, CONFIG_KEYS, "config")
    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise RiggedCarrierError("unsupported config schema_version")
    if config.get("controller_id") != CONTROLLER_ID:
        raise RiggedCarrierError("unsupported controller_id")
    if config.get("status") != "PREPARED_NO_BLENDER_AUTHORITY":
        raise RiggedCarrierError("config status must remain non-authorizing")

    candidate = _mapping(config.get("candidate"), "candidate")
    _exact_keys(
        candidate,
        {
            "candidate_id",
            "foundation_id",
            "body_class",
            "maturity_status",
            "identity_scope",
            "armature_id",
        },
        "candidate",
    )
    for key in candidate:
        _text(candidate[key], f"candidate.{key}")
    if candidate["body_class"] != "adult_female" or candidate["maturity_status"] != "confirmed_adult":
        raise RiggedCarrierError("candidate must remain in the confirmed-adult female lane")
    if candidate["identity_scope"] != "generic_identity_neutral":
        raise RiggedCarrierError("candidate may not contain identity styling")

    source = _mapping(config.get("source"), "source")
    _exact_keys(
        source,
        {
            "path",
            "bytes",
            "sha256",
            "decompressed_bytes",
            "decompressed_sha256",
            "primary_object_id",
            "expected_vertex_count",
            "expected_face_count",
            "qualification",
        },
        "source",
    )
    _positive_int(source.get("expected_vertex_count"), "source.expected_vertex_count")
    _positive_int(source.get("expected_face_count"), "source.expected_face_count")

    build_inputs = _mapping(config.get("source_build_inputs"), "source_build_inputs")
    _exact_keys(
        build_inputs,
        {"base_obj", "female_macro_targets", "target_height_m", "license"},
        "source_build_inputs",
    )
    target_height = _finite(build_inputs.get("target_height_m"), "target_height_m")
    if not 1.4 <= target_height <= 2.1:
        raise RiggedCarrierError("target_height_m is outside the bounded adult range")
    license_record = _mapping(build_inputs.get("license"), "source_build_inputs.license")
    _exact_keys(license_record, {"id", "path", "bytes", "sha256"}, "license")
    if license_record.get("id") != "CC0-1.0":
        raise RiggedCarrierError("foundation asset license must remain CC0-1.0")

    skeleton = _mapping(config.get("skeleton"), "skeleton")
    _exact_keys(
        skeleton,
        {
            "definition",
            "weights",
            "license_id",
            "expected_bone_count",
            "expected_weight_group_count",
            "expected_root_bone",
            "coordinate_conversion",
        },
        "skeleton",
    )
    if skeleton.get("license_id") != "CC0" or skeleton.get("expected_root_bone") != "root":
        raise RiggedCarrierError("skeleton license or root differs")
    if skeleton.get("coordinate_conversion") != (
        "makehuman_y_up_positive_z_forward_to_blender_z_up_negative_y_forward"
    ):
        raise RiggedCarrierError("skeleton coordinate conversion differs")

    output = _mapping(config.get("output"), "output")
    _exact_keys(
        output,
        {
            "allowed_root",
            "candidate_blend",
            "build_report",
            "audit_report",
            "one_run_authorization",
        },
        "output",
    )
    if len(set(output.values())) != len(output):
        raise RiggedCarrierError("output paths must be distinct")

    pose_audit = _mapping(config.get("pose_audit"), "pose_audit")
    _exact_keys(
        pose_audit,
        {
            "required_pose_ids",
            "pelvic_landmark_groups",
            "poses",
            "maximum_exact_nonadjacent_self_intersection_pairs_per_pose",
            "maximum_rest_pose_surface_displacement_m",
            "movement_epsilon_m",
            "minimum_nonneutral_pose_moved_vertex_count",
            "minimum_nonneutral_pose_maximum_displacement_m",
            "minimum_rotated_bone_group_maximum_displacement_m",
            "minimum_global_edge_ratio",
            "maximum_global_edge_ratio",
            "minimum_global_triangle_area_ratio",
            "maximum_global_triangle_area_ratio",
            "maximum_global_orientation_reversal_triangle_count",
            "minimum_signed_volume_ratio",
            "minimum_pelvic_patch_edge_ratio",
            "maximum_pelvic_patch_edge_ratio",
            "minimum_pelvic_patch_triangle_area_ratio",
        },
        "pose_audit",
    )
    if tuple(pose_audit.get("required_pose_ids", ())) != EXPECTED_POSE_IDS:
        raise RiggedCarrierError("required pose IDs differ")
    if tuple(pose_audit.get("pelvic_landmark_groups", ())) != EXPECTED_PELVIC_GROUPS:
        raise RiggedCarrierError("pelvic landmark groups differ")
    poses = _list(pose_audit.get("poses"), "pose_audit.poses")
    pose_ids: list[str] = []
    for index, raw in enumerate(poses):
        pose = _mapping(raw, f"pose {index}")
        _exact_keys(pose, {"pose_id", "rotations_degrees_xyz"}, f"pose {index}")
        pose_id = _text(pose.get("pose_id"), f"pose {index}.pose_id")
        pose_ids.append(pose_id)
        rotations = _mapping(pose.get("rotations_degrees_xyz"), f"pose {pose_id}.rotations")
        for bone, values in rotations.items():
            _text(bone, f"pose {pose_id} bone")
            vector = _list(values, f"pose {pose_id} rotation {bone}")
            if len(vector) != 3:
                raise RiggedCarrierError(f"pose {pose_id} rotation must have three values")
            if any(abs(_finite(value, f"pose {pose_id} rotation")) > 180.0 for value in vector):
                raise RiggedCarrierError(f"pose {pose_id} rotation exceeds bounded range")
    if tuple(pose_ids) != EXPECTED_POSE_IDS or len(set(pose_ids)) != len(pose_ids):
        raise RiggedCarrierError("pose definitions do not exactly cover required poses")
    maximum_pairs = pose_audit.get("maximum_exact_nonadjacent_self_intersection_pairs_per_pose")
    if isinstance(maximum_pairs, bool) or maximum_pairs != 0:
        raise RiggedCarrierError("self-intersection maximum must remain zero")
    maximum_rest_displacement = _finite(
        pose_audit.get("maximum_rest_pose_surface_displacement_m"),
        "maximum rest displacement",
    )
    movement_epsilon = _finite(
        pose_audit.get("movement_epsilon_m"), "movement epsilon"
    )
    minimum_moved = pose_audit.get("minimum_nonneutral_pose_moved_vertex_count")
    if isinstance(minimum_moved, bool) or not isinstance(minimum_moved, int):
        raise RiggedCarrierError("minimum moved-vertex count must be an integer")
    minimum_pose_displacement = _finite(
        pose_audit.get("minimum_nonneutral_pose_maximum_displacement_m"),
        "minimum nonneutral pose displacement",
    )
    minimum_bone_displacement = _finite(
        pose_audit.get("minimum_rotated_bone_group_maximum_displacement_m"),
        "minimum rotated-bone group displacement",
    )
    global_minimum_edge = _finite(
        pose_audit.get("minimum_global_edge_ratio"), "minimum global edge ratio"
    )
    global_maximum_edge = _finite(
        pose_audit.get("maximum_global_edge_ratio"), "maximum global edge ratio"
    )
    global_minimum_area = _finite(
        pose_audit.get("minimum_global_triangle_area_ratio"),
        "minimum global triangle area ratio",
    )
    global_maximum_area = _finite(
        pose_audit.get("maximum_global_triangle_area_ratio"),
        "maximum global triangle area ratio",
    )
    maximum_reversals = pose_audit.get(
        "maximum_global_orientation_reversal_triangle_count"
    )
    if isinstance(maximum_reversals, bool) or maximum_reversals != 0:
        raise RiggedCarrierError("orientation-reversal maximum must remain zero")
    minimum_volume_ratio = _finite(
        pose_audit.get("minimum_signed_volume_ratio"), "minimum signed volume ratio"
    )
    if not (
        0.0 <= maximum_rest_displacement <= movement_epsilon
        and movement_epsilon > maximum_rest_displacement
        and minimum_moved > 0
        and minimum_pose_displacement > movement_epsilon
        and minimum_bone_displacement > movement_epsilon
        and 0.0 < global_minimum_edge <= 1.0 <= global_maximum_edge
        and 0.0 < global_minimum_area <= 1.0 <= global_maximum_area
        and 0.0 < minimum_volume_ratio <= 1.0
    ):
        raise RiggedCarrierError("global pose-response thresholds are invalid")
    minimum_edge = _finite(
        pose_audit.get("minimum_pelvic_patch_edge_ratio"), "minimum edge ratio"
    )
    maximum_edge = _finite(
        pose_audit.get("maximum_pelvic_patch_edge_ratio"), "maximum edge ratio"
    )
    minimum_area = _finite(
        pose_audit.get("minimum_pelvic_patch_triangle_area_ratio"), "minimum area ratio"
    )
    if not 0.0 < minimum_edge <= 1.0 <= maximum_edge or not 0.0 < minimum_area <= 1.0:
        raise RiggedCarrierError("pose deformation thresholds are invalid")

    separation = _mapping(config.get("separation"), "separation")
    _exact_keys(
        separation,
        {
            "bald",
            "contains_hair",
            "contains_clothing",
            "contains_internal_anatomy",
            "contains_identity_styling",
            "contains_actions",
            "runtime_activation_allowed",
            "public_export_allowed",
            "carrier_dependency_mode_for_future_modules",
            "forbidden_body_changes",
        },
        "separation",
    )
    _require_bool(separation.get("bald"), True, "separation.bald")
    for key in (
        "contains_hair",
        "contains_clothing",
        "contains_internal_anatomy",
        "contains_identity_styling",
        "contains_actions",
        "runtime_activation_allowed",
        "public_export_allowed",
    ):
        _require_bool(separation.get(key), False, f"separation.{key}")
    if separation.get("carrier_dependency_mode_for_future_modules") != "READ_ONLY_TRANSFORM_FOLLOWING_ONLY":
        raise RiggedCarrierError("future module dependency mode differs")
    expected_changes = [
        "vertices",
        "faces",
        "uvs",
        "materials",
        "shape_keys",
        "existing_vertex_groups",
        "existing_weight_assignments",
    ]
    if separation.get("forbidden_body_changes") != expected_changes:
        raise RiggedCarrierError("forbidden body-change list differs")

    authority = _mapping(config.get("authority"), "authority")
    _exact_keys(
        authority,
        {
            "blender_execution_authorized",
            "candidate_assignment_authorized",
            "owner_approved",
            "anatomy_authoring_authorized",
            "runtime_activation_authorized",
            "public_export_authorized",
            "required_one_run_authorization_schema",
        },
        "authority",
    )
    for key in authority:
        if key != "required_one_run_authorization_schema":
            _require_bool(authority.get(key), False, f"authority.{key}")
    if authority.get("required_one_run_authorization_schema") != ONE_RUN_AUTHORIZATION_SCHEMA:
        raise RiggedCarrierError("one-run authorization schema differs")


def _validate_qualification(
    qualification: Mapping[str, Any],
    source: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> None:
    source_artifact = _mapping(qualification.get("source_artifact"), "qualification.source_artifact")
    accepted = (
        qualification.get("schema_version") == 1
        and qualification.get("artifact_type") == "adult_foundation_qualification_result"
        and qualification.get("status") == "QUALIFIED_INACTIVE"
        and qualification.get("foundation_id") == candidate.get("foundation_id")
        and qualification.get("qualified_for_adult_foundation") is True
        and qualification.get("adult_eligible") is True
        and qualification.get("complete_adult_topology_proven") is True
        and qualification.get("blockers") == []
        and source_artifact.get("path") == source.get("path")
        and source_artifact.get("sha256") == source.get("sha256")
        and qualification.get("armature_present") is False
        and qualification.get("runtime_activation_allowed") is False
        and qualification.get("public_export_allowed") is False
        and qualification.get("clothing_applied") is False
    )
    if not accepted:
        raise RiggedCarrierError("source qualification does not match the exact inactive foundation")


def _output_paths(project_root: Path, output: Mapping[str, Any]) -> dict[str, Path]:
    allowed_parts = _relative_parts(output.get("allowed_root"), "output.allowed_root")
    root = project_root.resolve(strict=True)
    allowed_root = root.joinpath(*allowed_parts)
    paths: dict[str, Path] = {}
    for key in ("candidate_blend", "build_report", "audit_report", "one_run_authorization"):
        path = project_path(root, output.get(key), f"output.{key}", must_exist=False)
        try:
            common = os.path.commonpath(
                (os.path.normcase(str(allowed_root)), os.path.normcase(str(path.absolute())))
            )
        except ValueError as exc:
            raise RiggedCarrierError(f"output.{key} escapes allowed root") from exc
        if common != os.path.normcase(str(allowed_root)):
            raise RiggedCarrierError(f"output.{key} escapes allowed root")
        paths[key] = path
    parents = {path.parent for path in paths.values()}
    if len(parents) != 1:
        raise RiggedCarrierError("all carrier outputs must share one append-only directory")
    return paths


def _input_snapshot(paths: Mapping[str, Path]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for label, path in sorted(paths.items()):
        result[label] = {
            "bytes": native_filesystem_path(path).stat().st_size,
            "sha256": sha256_file(path),
        }
    return result


def _code_bindings(project_root: Path) -> dict[str, dict[str, Any]]:
    relative_paths = {
        "controller": CONTROLLER_RELATIVE_PATH,
        "builder": BUILDER_RELATIVE_PATH,
        "auditor": AUDITOR_RELATIVE_PATH,
        "intersection_auditor": INTERSECTION_AUDITOR_RELATIVE_PATH,
    }
    result: dict[str, dict[str, Any]] = {}
    for label, relative in relative_paths.items():
        path = project_path(project_root, relative, label, must_exist=True)
        result[label] = {
            "path": relative,
            "bytes": native_filesystem_path(path).stat().st_size,
            "sha256": sha256_file(path),
        }
    return result


def preflight_binding_receipt(
    project_root: Path,
    config_path: Path,
) -> tuple[str, dict[str, dict[str, Any]]]:
    """Bind the immutable plan without importing Blender or decompressing it."""

    root = project_root.resolve(strict=True)
    config_absolute = config_path.resolve(strict=True)
    config = read_json(config_absolute, "rigged-carrier config")
    _validate_config_shape(config)
    code = _code_bindings(root)
    receipt_payload = {
        "schema_version": 1,
        "controller_id": CONTROLLER_ID,
        "config_sha256": sha256_file(config_absolute),
        "source_sha256": config["source"]["sha256"],
        "source_decompressed_sha256": config["source"]["decompressed_sha256"],
        "candidate_id": config["candidate"]["candidate_id"],
        "output": dict(config["output"]),
        "required_blender_flags": list(REQUIRED_BLENDER_FLAGS),
        "separation": dict(config["separation"]),
        "code": code,
    }
    return canonical_sha256(receipt_payload), code


def prepare_preflight(
    project_root: Path,
    config_path: Path,
    *,
    blender_executable: Path | None = None,
    authorization_path: Path | None = None,
    verify_decompressed_container: bool = True,
) -> dict[str, Any]:
    """Validate exact inputs and return a non-executing immutable run plan."""

    root = project_root.resolve(strict=True)
    config_absolute = config_path.resolve(strict=True)
    try:
        config_relative = config_absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise RiggedCarrierError("config escapes project root") from exc
    config = read_json(config_absolute, "rigged-carrier config")
    _validate_config_shape(config)

    source = _mapping(config["source"], "source")
    candidate = _mapping(config["candidate"], "candidate")
    build_inputs = _mapping(config["source_build_inputs"], "source_build_inputs")
    skeleton = _mapping(config["skeleton"], "skeleton")

    input_paths: dict[str, Path] = {}
    source_binding = {
        "path": source["path"],
        "bytes": source["bytes"],
        "sha256": source["sha256"],
    }
    source_path, _ = _bind_file(root, source_binding, "source Blend")
    input_paths["source_blend"] = source_path
    _validate_compressed_blend(
        source_path,
        source,
        verify_decompressed=verify_decompressed_container,
    )

    qualification_path, _ = _bind_file(
        root,
        _mapping(source.get("qualification"), "source.qualification"),
        "source qualification",
    )
    input_paths["source_qualification"] = qualification_path
    qualification = read_json(qualification_path, "source qualification")
    _validate_qualification(qualification, source, candidate)

    base_path, _ = _bind_file(
        root,
        _mapping(build_inputs.get("base_obj"), "source_build_inputs.base_obj"),
        "MakeHuman base OBJ",
    )
    input_paths["base_obj"] = base_path
    vertex_count = _base_vertex_count(base_path)

    target_records: list[dict[str, Any]] = []
    target_bindings: list[tuple[Path, float]] = []
    raw_targets = _list(build_inputs.get("female_macro_targets"), "female_macro_targets")
    if len(raw_targets) != 2:
        raise RiggedCarrierError("exactly two female macro targets are required")
    for index, raw in enumerate(raw_targets):
        target = _mapping(raw, f"female macro target {index}")
        _exact_keys(target, {"path", "bytes", "sha256", "weight"}, f"female macro target {index}")
        weight = _finite(target.get("weight"), f"female macro target {index}.weight")
        if weight != 1.0:
            raise RiggedCarrierError("female macro target weight must remain exactly 1.0")
        binding = {key: target[key] for key in ("path", "bytes", "sha256")}
        path, record = _bind_file(root, binding, f"female macro target {index}")
        input_paths[f"female_macro_target_{index}"] = path
        record["weight"] = weight
        record["changed_vertex_count"] = _validate_target(
            path, vertex_count, f"female macro target {index}"
        )
        target_records.append(record)
        target_bindings.append((path, weight))
    if sum(int(record["changed_vertex_count"]) for record in target_records) <= 0:
        raise RiggedCarrierError("the exact macro-target set changes no vertices")

    license_record = _mapping(build_inputs.get("license"), "source_build_inputs.license")
    license_path, _ = _bind_file(
        root,
        {key: license_record[key] for key in ("path", "bytes", "sha256")},
        "MakeHuman asset license",
    )
    input_paths["asset_license"] = license_path

    skeleton_path, _ = _bind_file(
        root,
        _mapping(skeleton.get("definition"), "skeleton.definition"),
        "MakeHuman skeleton definition",
    )
    weights_path, _ = _bind_file(
        root,
        _mapping(skeleton.get("weights"), "skeleton.weights"),
        "MakeHuman default weights",
    )
    input_paths["skeleton_definition"] = skeleton_path
    input_paths["skeleton_weights"] = weights_path
    skeleton_payload = read_json(skeleton_path, "MakeHuman skeleton definition")
    weights_payload = read_json(weights_path, "MakeHuman default weights")
    source_definition = validate_source_definition(
        skeleton_payload,
        weights_payload,
        vertex_count=vertex_count,
        expected_bones=_positive_int(skeleton.get("expected_bone_count"), "expected_bone_count"),
        expected_weight_groups=_positive_int(
            skeleton.get("expected_weight_group_count"), "expected_weight_group_count"
        ),
    )
    pose_bones = {
        bone
        for pose in config["pose_audit"]["poses"]
        for bone in pose["rotations_degrees_xyz"]
    }
    missing_pose_bones = sorted(pose_bones - set(skeleton_payload["bones"]))
    if missing_pose_bones:
        raise RiggedCarrierError(f"poses reference absent bones: {missing_pose_bones!r}")
    source_definition["pose_bones"] = sorted(pose_bones)
    transformed_vertices, transform = load_transformed_makehuman_vertices(
        base_path,
        target_bindings,
        _finite(build_inputs.get("target_height_m"), "target_height_m"),
    )
    skeleton_geometry = resolve_makehuman_skeleton_geometry(
        skeleton_payload,
        transformed_vertices,
    )
    source_definition["resolved_skeleton_geometry"] = {
        "bone_geometry_count": len(skeleton_geometry["bones"]),
        "joint_position_count": len(skeleton_geometry["joint_positions"]),
        "minimum_bone_length_m": skeleton_geometry["minimum_bone_length_m"],
        "maximum_bone_length_m": skeleton_geometry["maximum_bone_length_m"],
        "bone_geometry_sha256": canonical_sha256(skeleton_geometry["bones"]),
        "transform": transform,
    }

    output = _mapping(config["output"], "output")
    outputs = _output_paths(root, output)
    existing_outputs = {
        key: (
            native_filesystem_path(path).exists()
            or native_filesystem_path(path).is_symlink()
        )
        for key, path in outputs.items()
    }
    allowed_existing = {"one_run_authorization"} if authorization_path is not None else set()
    blockers = [
        f"output_exists:{key}"
        for key, exists in existing_outputs.items()
        if exists and key not in allowed_existing
    ]
    if blockers:
        raise RiggedCarrierError("append-only output is not empty: " + ", ".join(blockers))
    if authorization_path is None and existing_outputs["one_run_authorization"]:
        raise RiggedCarrierError("unexpected one-run authorization exists")
    if authorization_path is not None:
        expected_authorization = outputs["one_run_authorization"].absolute()
        supplied_authorization = authorization_path.absolute()
        if os.path.normcase(str(expected_authorization)) != os.path.normcase(
            str(supplied_authorization)
        ):
            raise RiggedCarrierError("authorization path differs from config")
        if not existing_outputs["one_run_authorization"]:
            raise RiggedCarrierError("one-run authorization is absent")

    blender_record: dict[str, Any] | None = None
    if blender_executable is not None:
        blender_path = blender_executable.resolve(strict=True)
        if not blender_path.is_file():
            raise RiggedCarrierError("Blender executable is not a file")
        blender_record = {
            "path": str(blender_path),
            "bytes": blender_path.stat().st_size,
            "sha256": sha256_file(blender_path),
        }

    builder = BUILDER_RELATIVE_PATH
    auditor = AUDITOR_RELATIVE_PATH
    code_bindings = _code_bindings(root)
    for label, record in code_bindings.items():
        relative = str(record["path"])
        path = project_path(root, relative, label, must_exist=True)
        input_paths[label] = path

    before = _input_snapshot(input_paths)
    after = _input_snapshot(input_paths)
    if before != after:
        raise RiggedCarrierError("bound inputs changed during preflight")

    authorization: dict[str, Any] | None = None
    if authorization_path is not None:
        if blender_executable is None:
            raise RiggedCarrierError("Blender executable is required to bind authorization")
        authorization = validate_one_run_authorization(
            root,
            config_absolute,
            authorization_path,
            blender_executable,
            operation="build",
        )

    command_prefix: list[str] = [
        str(blender_record["path"] if blender_record else "<BLENDER_EXECUTABLE>"),
        *REQUIRED_BLENDER_FLAGS,
    ]
    authorization_relative = str(output["one_run_authorization"])
    build_command = [
        *command_prefix,
        "--python",
        builder,
        "--",
        "--config",
        config_relative,
        "--authorization",
        authorization_relative,
    ]
    audit_command = [
        *command_prefix,
        "--python",
        auditor,
        "--",
        "--config",
        config_relative,
        "--authorization",
        authorization_relative,
    ]
    binding_receipt, receipt_code_bindings = preflight_binding_receipt(
        root,
        config_absolute,
    )
    if receipt_code_bindings != code_bindings:
        raise RiggedCarrierError("code bindings changed during preflight")
    report = {
        "schema_version": 1,
        "artifact_type": "makehuman_adult_female_rigged_carrier_preflight",
        "status": (
            "PREFLIGHT_AUTHORIZED_EXACT_INACTIVE_RUN_READY"
            if authorization is not None
            else "PREFLIGHT_READY_AWAITING_EXACT_ONE_RUN_AUTHORIZATION"
        ),
        "controller_id": CONTROLLER_ID,
        "config": {
            "path": config_relative,
            "bytes": config_absolute.stat().st_size,
            "sha256": sha256_file(config_absolute),
        },
        "candidate_id": candidate["candidate_id"],
        "source": {
            "path": source["path"],
            "bytes": native_filesystem_path(source_path).stat().st_size,
            "sha256_before": before["source_blend"]["sha256"],
            "sha256_after": after["source_blend"]["sha256"],
            "unchanged": before["source_blend"] == after["source_blend"],
            "decompressed_container_verified": verify_decompressed_container,
        },
        "source_definition": source_definition,
        "macro_targets": target_records,
        "outputs_absent": not any(
            exists
            for key, exists in existing_outputs.items()
            if key != "one_run_authorization"
        ),
        "output_paths": {key: str(output[key]) for key in outputs},
        "blender_executable": blender_record,
        "required_blender_flags": list(REQUIRED_BLENDER_FLAGS),
        "bound_code": code_bindings,
        "preflight_receipt_sha256": binding_receipt,
        "build_command": build_command,
        "audit_command": audit_command,
        "one_run_authorization": {
            "schema": ONE_RUN_AUTHORIZATION_SCHEMA,
            "path": authorization_relative,
            "present": authorization is not None,
            "required_before_blender": True,
            "sha256": (
                sha256_file(authorization_path.resolve(strict=True))
                if authorization_path is not None
                else None
            ),
            "one_run_id": authorization.get("one_run_id") if authorization else None,
        },
        "separation": dict(_mapping(config["separation"], "separation")),
        "authority": {
            "blender_execution_authorized": False,
            "candidate_assignment_authorized": False,
            "owner_approved": False,
            "anatomy_authoring_authorized": False,
            "runtime_activation_authorized": False,
            "public_export_authorized": False,
        },
        "input_snapshot_root_before": canonical_sha256(before),
        "input_snapshot_root_after": canonical_sha256(after),
    }
    report["preflight_report_receipt_sha256"] = canonical_sha256(report)
    return report


def validate_one_run_authorization(
    project_root: Path,
    config_path: Path,
    authorization_path: Path,
    blender_executable: Path,
    *,
    operation: str,
) -> dict[str, Any]:
    """Validate the exact external authorization used by a Blender worker."""

    if operation not in {"build", "audit"}:
        raise RiggedCarrierError("operation must be build or audit")
    root = project_root.resolve(strict=True)
    config_absolute = config_path.resolve(strict=True)
    config = read_json(config_absolute, "rigged-carrier config")
    _validate_config_shape(config)
    output = _mapping(config["output"], "output")
    output_paths = _output_paths(root, output)
    expected_authorization = output_paths["one_run_authorization"]
    if not same_filesystem_path(authorization_path, expected_authorization):
        raise RiggedCarrierError("authorization path differs from config")
    authorization_absolute = project_path(
        root,
        output["one_run_authorization"],
        "one-run authorization",
        must_exist=True,
    )
    authorization = read_json(authorization_absolute, "one-run authorization")
    _exact_keys(authorization, AUTHORIZATION_KEYS, "one-run authorization")
    if authorization.get("schema") != ONE_RUN_AUTHORIZATION_SCHEMA:
        raise RiggedCarrierError("one-run authorization schema differs")
    if authorization.get("status") != ONE_RUN_AUTHORIZATION_STATUS:
        raise RiggedCarrierError("one-run authorization status differs")
    _text(authorization.get("one_run_id"), "one_run_id")
    issued = _text(authorization.get("issued_at_utc"), "issued_at_utc")
    if not RFC3339_UTC_RE.fullmatch(issued):
        raise RiggedCarrierError("issued_at_utc must be RFC3339 UTC")

    binding_receipt, code_bindings = preflight_binding_receipt(
        root,
        config_absolute,
    )
    blender_path = blender_executable.resolve(strict=True)
    if not blender_path.is_file() or _is_reparse(blender_path):
        raise RiggedCarrierError("Blender executable is not a regular unlinked file")
    if int(getattr(blender_path.stat(), "st_nlink", 1)) != 1:
        raise RiggedCarrierError("Blender executable must not be multiply linked")
    expected = {
        "config_sha256": sha256_file(config_absolute),
        "source_sha256": config["source"]["sha256"],
        "candidate_blend_path": output["candidate_blend"],
        "build_report_path": output["build_report"],
        "audit_report_path": output["audit_report"],
        "blender_executable_sha256": sha256_file(blender_path),
        "preflight_receipt_sha256": binding_receipt,
        "controller_sha256": code_bindings["controller"]["sha256"],
        "builder_sha256": code_bindings["builder"]["sha256"],
        "auditor_sha256": code_bindings["auditor"]["sha256"],
        "intersection_auditor_sha256": code_bindings["intersection_auditor"]["sha256"],
    }
    for key, value in expected.items():
        if authorization.get(key) != value:
            raise RiggedCarrierError(f"one-run authorization {key} differs")
    for key in (
        "build_allowed",
        "audit_allowed",
        "background_required",
        "factory_startup_required",
        "autoexec_disabled_required",
    ):
        _require_bool(authorization.get(key), True, f"authorization.{key}")
    for key in (
        "overwrite_allowed",
        "source_mutation_allowed",
        "hair_allowed",
        "clothing_allowed",
        "internal_anatomy_allowed",
        "identity_styling_allowed",
        "runtime_activation_allowed",
        "public_export_allowed",
    ):
        _require_bool(authorization.get(key), False, f"authorization.{key}")
    if authorization.get(f"{operation}_allowed") is not True:
        raise RiggedCarrierError(f"authorization does not allow {operation}")
    return authorization


__all__ = [
    "CONFIG_SCHEMA_VERSION",
    "CONTROLLER_ID",
    "EXPECTED_PELVIC_GROUPS",
    "EXPECTED_POSE_IDS",
    "ONE_RUN_AUTHORIZATION_SCHEMA",
    "ONE_RUN_AUTHORIZATION_STATUS",
    "REQUIRED_BLENDER_FLAGS",
    "RiggedCarrierError",
    "canonical_sha256",
    "evaluate_pose_gate",
    "load_transformed_makehuman_vertices",
    "native_filesystem_path",
    "preflight_binding_receipt",
    "prepare_preflight",
    "promote_file_no_replace",
    "project_path",
    "read_json",
    "resolve_makehuman_skeleton_geometry",
    "same_filesystem_path",
    "sha256_file",
    "validate_one_run_authorization",
    "validate_source_definition",
]
