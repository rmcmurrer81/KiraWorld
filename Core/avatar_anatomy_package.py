"""Read-only preflight for source-bound adult anatomy authoring packages.

Milestone v1 deliberately stops before Blender.  It validates immutable source,
carrier, contract, normalization, route, privacy, and truth-boundary evidence and
returns either a bounded authoring-ready receipt or an explicit blocker report.
It never creates geometry, edits a carrier, activates an avatar, or grants public
export authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any, Iterable, Mapping, Sequence


REQUEST_SCHEMA = "kira.avatar.anatomy_package_preflight_request.v1"
REPORT_SCHEMA = "kira.avatar.anatomy_package_preflight_report.v1"
SOURCE_INTAKE_VALIDATED_INCOMPLETE = "SOURCE_INTAKE_VALIDATED_INCOMPLETE"
SOURCE_INTAKE_VALIDATED_COMPLETE = "SOURCE_INTAKE_VALIDATED_COMPLETE"
PREFLIGHT_BLOCKED_MISSING_STRUCTURES = "PREFLIGHT_BLOCKED_MISSING_STRUCTURES"
PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED = "PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED"
READY_FOR_PRIVATE_INACTIVE_AUTHORING = "READY_FOR_PRIVATE_INACTIVE_AUTHORING"
AUTHORED_PRIVATE_INACTIVE_PENDING_GEOMETRY_REVIEW = (
    "AUTHORED_PRIVATE_INACTIVE_PENDING_GEOMETRY_REVIEW"
)
GEOMETRY_REVIEW_PASSED_PENDING_OWNER_REVIEW = "GEOMETRY_REVIEW_PASSED_PENDING_OWNER_REVIEW"
OWNER_ACCEPTED_PRIVATE_INACTIVE = "OWNER_ACCEPTED_PRIVATE_INACTIVE"
STATUS_LADDER = (
    SOURCE_INTAKE_VALIDATED_INCOMPLETE,
    PREFLIGHT_BLOCKED_MISSING_STRUCTURES,
    PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED,
    READY_FOR_PRIVATE_INACTIVE_AUTHORING,
    AUTHORED_PRIVATE_INACTIVE_PENDING_GEOMETRY_REVIEW,
    GEOMETRY_REVIEW_PASSED_PENDING_OWNER_REVIEW,
    OWNER_ACCEPTED_PRIVATE_INACTIVE,
)

GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK = 0x4E4F534A
GLB_BIN_CHUNK = 0x004E4942
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
MAX_AUTHORITY_BOUND_ZSTD_CARRIER_BYTES = 16 * 1024 * 1024
MAX_AUTHORITY_BOUND_BLENDER_BYTES = 64 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,127}$")
HTTPS_RE = re.compile(r"^https://[^\s]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

TARGET_UNITS = "meters"
TARGET_AXES = {"up": "+Z", "forward": "-Y", "handedness": "right"}
HRA_SOURCE_AXES = {"up": "+Y", "forward": "+Z", "handedness": "right"}
HRA_TO_BLENDER_TRANSFORM = (
    1.0, 0.0, 0.0, 0.0,
    0.0, 0.0, -1.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
)
ROUTE_SYSTEMS = {
    "urinary": "urinary",
    "reproductive": "reproductive",
    "bowel": "posterior_bowel",
}
MATERIAL_FOR_SYSTEM = {
    "urinary": "clinical_urinary",
    "reproductive": "clinical_reproductive",
    "posterior_bowel": "clinical_bowel",
    "support": "clinical_support",
    "orientation": "clinical_landmark",
}
SUPPORTED_UNITS = frozenset({"millimeters", "centimeters", "meters"})
UNIT_TO_METERS = {"millimeters": 0.001, "centimeters": 0.01, "meters": 1.0}
SUPPORTED_AXES = frozenset({"+X", "-X", "+Y", "-Y", "+Z", "-Z"})
SUPPORTED_LICENSES = frozenset(
    {
        "CC BY 4.0",
        "CC0 1.0",
        "CC0 1.0 Universal",
        "Public Domain",
    }
)
CANONICAL_LICENSE_URLS = {
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC0 1.0 Universal": "https://creativecommons.org/publicdomain/zero/1.0/",
    "Public Domain": "https://creativecommons.org/publicdomain/mark/1.0/",
}
SUPPORTED_CONTRACT_SHA256 = {
    "kira_confirmed_adult_internal_pelvic_anatomy_module_contract_v1": (
        "d219bfc6c7b4ac01c3fa0925d90c0815f2f213344cc6d8e43661fbd649abb46a"
    )
}
SUPPORTED_ANATOMY_PROFILES: dict[str, dict[str, Any]] = {
    "confirmed_adult_female_internal_pelvic_v1": {
        "contract_id": "kira_confirmed_adult_internal_pelvic_anatomy_module_contract_v1",
        "region": "internal_pelvis",
        "whole_body_complete": False,
        "external_anatomy_complete": False,
    }
}
SUPPORTED_SOURCE_PACKAGES: dict[str, dict[str, Any]] = {
    "hra_female_pelvis_cc_by_4_v1_2": {
        "source_manifest_sha256": (
            "d40b7eb6dc260a1fc21d5bdb07286dfdb86545be59fa143bea5652fe2aa634b2"
        ),
        "role_map_sha256": (
            "33a6631ba2fabdb06b2821cb8655647ed1d2a4b7b7d1b78862cd76cacd4e4620"
        ),
        "contract_sha256": (
            "d219bfc6c7b4ac01c3fa0925d90c0815f2f213344cc6d8e43661fbd649abb46a"
        ),
        "allow_direct_semantic_nodes": False,
    }
}
SUPPORTED_CARRIER_AUTHORITIES: dict[str, dict[str, Any]] = {
    "generic_makehuman_adult_female_foundation_v1_20260801": {
        "carrier_sha256": (
            "3911419c44681d25f33892122e61206f1f4651bb78b3e403e377d1ed099cde2f"
        ),
        "carrier_bytes": 789620,
        "storage_format": "zstd_multiframe_blender",
        "decompressed_bytes": 2714373,
        "decompressed_sha256": (
            "995f66562d38c204e3722370c81551c796494ee827d7da722fbbee74561410fd"
        ),
        "qualification_manifest_sha256": (
            "c91c11f649fca7dcdff4530df15a5ed4654d0fe4ca723740cca55660a4b969e0"
        ),
        "owner_acceptance_sha256": None,
        "object_ids": None,
        "armature_id": None,
        "rest_pose_matrix": None,
    }
}
REQUIRED_SOURCE_TRUTH_BOUNDARY = frozenset(
    {
        "REFERENCE_GEOMETRY_ONLY",
        "NO_KIRA_BODY_CREATED_OR_CHANGED",
        "NO_EXTERNAL_ANATOMY_REPLACEMENT",
        "NO_PHYSIOLOGICAL_OR_SUBJECTIVE_FUNCTION_CLAIM",
        "NO_RUNTIME_ACTIVATION_OR_ASSIGNMENT",
        "PRIVATE_CLINICAL_REVIEW_DERIVATIVES_ONLY",
    }
)
ADDITIONAL_TRUTH_NONCLAIMS = frozenset(
    {
        "whole_body_complete",
        "eating_implemented",
        "drinking_implemented",
        "swallowing_implemented",
        "digestion_implemented",
        "nutrient_absorption_implemented",
        "relationship_status_proven",
        "consent_proven",
        "activity_proven",
        "fertility_implemented",
        "conception_implemented",
        "delivery_implemented",
        "postpartum_implemented",
        "family_relationships_proven",
    }
)
HRA_SCHEMA = "kira.avatar.medical_reference.hra_female_pelvis_intake.v1"
HRA_STATUS = "SOURCE_REFERENCE_ONLY_NOT_A_BODY_NOT_FUNCTIONAL"
HRA_COLLECTION_NAME = "Human Reference Atlas 3D Reference Object Library"
HRA_PORTAL = "https://humanatlas.io/3d-reference-library"
HRA_VISIBLE_HUMAN_SOURCE = "https://www.nlm.nih.gov/research/visible/visible_human.html"
HRA_SOURCE_URL_PREFIX = "https://ccf-ontology.hubmapconsortium.org/objects/"
HRA_SOURCE_ROLE_MAP: dict[str, dict[str, tuple[str, ...]]] = {
    "bladder_shell": {
        "VH_F_Urinary_Bladder.glb": (
            "VH_F_fundus_of_urinary_bladder_dome",
            "VH_F_fundus_of_urinary_bladder_base",
        )
    },
    "bladder_neck_trigone_marker": {
        "VH_F_Urinary_Bladder.glb": (
            "VH_F_urinary_bladder_neck_smooth_muscle",
            "VH_F_trigone_of_urinary_bladder",
        )
    },
    "ureter_stub_left": {"VH_F_Ureter_L.glb": ("VH_F_left_ureter",)},
    "ureter_stub_right": {"VH_F_Ureter_R.glb": ("VH_F_right_ureter",)},
    "cervix": {
        "VH_F_Uterus.glb": (
            "VH_F_cervix",
            "VH_F_internal_cervical_os",
            "VH_F_external_cervical_os",
        )
    },
    "uterine_body_fundus": {
        "VH_F_Uterus.glb": ("VH_F_body_of_uterus", "VH_F_fundus_of_uterus")
    },
    "uterine_tube_left": {
        "VH_F_Fallopian_Tube_L.glb": (
            "VH_F_ampulla_of_uterine_tube_L",
            "VH_F_isthmus_of_fallopian_tube_L",
            "VH_F_fibria_of_uterine_tube_L",
            "VH_F_uterine_tube_infundibulum_L",
        )
    },
    "uterine_tube_right": {
        "VH_F_Fallopian_Tube_R.glb": (
            "VH_F_ampulla_of_uterine_tube_R",
            "VH_F_isthmus_of_fallopian_tube_R",
            "VH_F_fibria_of_uterine_tube_R",
            "VH_F_uterine_tube_infundibulum_R",
        )
    },
    "ovary_left": {"VH_F_Ovary_L.glb": ("VH_F_left_ovary",)},
    "ovary_right": {"VH_F_Ovary_R.glb": ("VH_F_right_ovary",)},
    "distal_bowel_stub": {"SBU_F_Intestine_Large.glb": ("VH_F_sigmoid_colon",)},
    "rectum": {"SBU_F_Intestine_Large.glb": ("VH_F_rectum",)},
    "bony_pelvis_proxy": {
        "VH_F_Pelvis.glb": (
            "VH_F_sacrum",
            "VH_F_coccyx",
            "VH_F_pubis_spongy_bone_L",
            "VH_F_pubis_spongy_bone_R",
            "VH_F_pubis_compact_bone_R",
            "VH_F_pubis_compact_bone_L",
            "VH_F_ilium_compact_bone_R",
            "VH_F_ilium_compact_bone_L",
            "VH_F_ilium_spongy_bone_L",
            "VH_F_ilium_spongy_bone_R",
            "VH_F_ischium_compact_bone_R",
            "VH_F_ischium_compact_bone_L",
            "VH_F_ischium_spongy_bone_R",
            "VH_F_ischium_spongy_bone_L",
        )
    },
}


class AvatarAnatomyPackageError(ValueError):
    """Fail-closed schema, path, or immutable-evidence validation error."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with _io_path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AvatarAnatomyPackageError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise AvatarAnatomyPackageError(f"non-finite JSON number: {value}")


def _parse_json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8-sig")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except AvatarAnatomyPackageError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AvatarAnatomyPackageError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise AvatarAnatomyPackageError(f"{label} must be a JSON object")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AvatarAnatomyPackageError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AvatarAnatomyPackageError(f"{label} must be a list")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AvatarAnatomyPackageError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_id(value: Any, label: str) -> str:
    result = _text(value, label)
    if not SAFE_ID_RE.fullmatch(result):
        raise AvatarAnatomyPackageError(f"{label} must be a safe identifier")
    return result


def _sha256(value: Any, label: str) -> str:
    result = _text(value, label).lower()
    if not SHA256_RE.fullmatch(result):
        raise AvatarAnatomyPackageError(f"{label} must be a lowercase SHA-256")
    return result


def _bytes_count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AvatarAnatomyPackageError(f"{label} must be a positive integer")
    return value


def _strip_extended_prefix(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


def _lexical_absolute(path: Path | str) -> Path:
    """Return a normalized absolute path without filesystem resolution.

    Containment is lexical because every child component is subsequently checked
    for symlink/reparse indirection.  Avoiding ``Path.resolve(strict=True)`` is
    required for qualified Windows foundation paths longer than MAX_PATH.
    """

    return Path(os.path.abspath(os.path.normpath(_strip_extended_prefix(str(path)))))


def _io_path(path: Path | str) -> Path:
    absolute = str(_lexical_absolute(path))
    if os.name != "nt" or absolute.startswith("\\\\?\\"):
        return Path(absolute)
    if absolute.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + absolute[2:])
    return Path("\\\\?\\" + absolute)


def _file_size(path: Path) -> int:
    return _io_path(path).stat().st_size


def _read_bytes(path: Path) -> bytes:
    return _io_path(path).read_bytes()


def _validate_blender_carrier_container(
    path: Path,
    authority: Mapping[str, Any],
) -> None:
    """Validate a raw Blender file or one exact authority-bound zstd carrier.

    Blender 5 may store a ``.blend`` as concatenated Zstandard frames.  Such a
    container is accepted only when its raw size/hash have already matched the
    registered authority and that same authority pins the bounded decompressed
    size and hash.  The stream is consumed to EOF so truncation, malformed
    frames, trailing garbage, and decompression bombs fail closed.
    """

    try:
        with _io_path(path).open("rb") as stream:
            header = stream.read(7)
    except OSError as exc:
        raise AvatarAnatomyPackageError("cannot inspect carrier container") from exc

    storage_format = authority.get("storage_format")
    if header == b"BLENDER":
        if storage_format not in (None, "raw_blender"):
            raise AvatarAnatomyPackageError(
                "carrier storage format differs from its authority record"
            )
        return
    if header[:4] != ZSTD_MAGIC:
        raise AvatarAnatomyPackageError("carrier does not have a Blender file header")
    if storage_format != "zstd_multiframe_blender":
        raise AvatarAnatomyPackageError(
            "carrier compressed Blender container is not authority-bound"
        )

    expected_carrier_bytes = _bytes_count(
        authority.get("carrier_bytes"),
        "carrier authority carrier_bytes",
    )
    expected_decompressed_bytes = _bytes_count(
        authority.get("decompressed_bytes"),
        "carrier authority decompressed_bytes",
    )
    expected_decompressed_sha256 = _sha256(
        authority.get("decompressed_sha256"),
        "carrier authority decompressed_sha256",
    )
    if expected_carrier_bytes > MAX_AUTHORITY_BOUND_ZSTD_CARRIER_BYTES:
        raise AvatarAnatomyPackageError("carrier compressed byte bound is unsafe")
    if expected_decompressed_bytes > MAX_AUTHORITY_BOUND_BLENDER_BYTES:
        raise AvatarAnatomyPackageError("carrier decompressed byte bound is unsafe")
    if _file_size(path) != expected_carrier_bytes:
        raise AvatarAnatomyPackageError(
            "carrier compressed byte count differs from its authority record"
        )

    try:
        from compression import zstd
    except ImportError as exc:  # pragma: no cover - Python runtime capability
        raise AvatarAnatomyPackageError(
            "authority-bound zstd carrier inspection is unavailable"
        ) from exc

    decompressed_sha256 = hashlib.sha256()
    decompressed_bytes = 0
    decompressed_header = b""
    try:
        with _io_path(path).open("rb") as raw_stream:
            with zstd.ZstdFile(raw_stream, "rb") as blender_stream:
                while True:
                    remaining_with_sentinel = (
                        expected_decompressed_bytes - decompressed_bytes + 1
                    )
                    read_size = min(256 * 1024, max(1, remaining_with_sentinel))
                    chunk = blender_stream.read(read_size)
                    if not chunk:
                        break
                    if len(decompressed_header) < 7:
                        decompressed_header += chunk[: 7 - len(decompressed_header)]
                    decompressed_bytes += len(chunk)
                    if decompressed_bytes > expected_decompressed_bytes:
                        raise AvatarAnatomyPackageError(
                            "carrier decompressed byte count exceeds its authority bound"
                        )
                    decompressed_sha256.update(chunk)
    except AvatarAnatomyPackageError:
        raise
    except (OSError, EOFError, ValueError, zstd.ZstdError) as exc:
        raise AvatarAnatomyPackageError(
            "carrier compressed Blender container is invalid"
        ) from exc

    if decompressed_bytes != expected_decompressed_bytes:
        raise AvatarAnatomyPackageError(
            "carrier decompressed byte count differs from its authority record"
        )
    if decompressed_header != b"BLENDER":
        raise AvatarAnatomyPackageError(
            "carrier decompressed payload does not have a Blender file header"
        )
    if decompressed_sha256.hexdigest() != expected_decompressed_sha256:
        raise AvatarAnatomyPackageError(
            "carrier decompressed SHA-256 differs from its authority record"
        )


def _is_within(path: Path, root: Path) -> bool:
    path_text = os.path.normcase(str(_lexical_absolute(path)))
    root_text = os.path.normcase(str(_lexical_absolute(root)))
    try:
        return os.path.commonpath((path_text, root_text)) == root_text
    except ValueError:
        return False


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = os.lstat(_io_path(path))
    except OSError as exc:
        raise AvatarAnatomyPackageError(
            "cannot inspect path for symlink or reparse point"
        ) from exc
    attributes = getattr(metadata, "st_file_attributes", 0)
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(marker and attributes & marker)


def _safe_relative_file(
    containment_root: Path,
    relative_root: Path,
    raw_value: Any,
    label: str,
) -> Path:
    raw_text = _text(raw_value, label)
    raw = Path(raw_text)
    if (
        raw.is_absolute()
        or raw.anchor
        or ".." in raw.parts
        or not raw.parts
        or any(":" in part for part in raw.parts)
    ):
        raise AvatarAnatomyPackageError(f"{label} must be a safe project-relative path")
    if any(part in {"", "."} for part in raw.parts):
        raise AvatarAnatomyPackageError(f"{label} must be normalized")
    project = _lexical_absolute(containment_root)
    base = _lexical_absolute(relative_root)
    if not _is_within(base, project):
        raise AvatarAnatomyPackageError(f"{label} base escapes the project")
    unresolved = _lexical_absolute(base / raw)
    if not _is_within(unresolved, base):
        raise AvatarAnatomyPackageError(f"{label} escapes its relative root")
    current = unresolved
    while True:
        if _io_path(current).exists() and _is_reparse_point(current):
            raise AvatarAnatomyPackageError(f"{label} contains a symlink or reparse point")
        if current == base or current.parent == current:
            break
        current = current.parent
    if not _io_path(unresolved).exists():
        raise AvatarAnatomyPackageError(f"{label} does not exist")
    if not _is_within(unresolved, project):
        raise AvatarAnatomyPackageError(f"{label} escapes the project")
    if not _io_path(unresolved).is_file() or _is_reparse_point(unresolved):
        raise AvatarAnatomyPackageError(f"{label} is not a regular non-link file")
    if getattr(_io_path(unresolved).stat(), "st_nlink", 1) != 1:
        raise AvatarAnatomyPackageError(f"{label} must not be a multiply-linked file")
    return unresolved


def _project_file(project_root: Path, raw_value: Any, label: str) -> Path:
    return _safe_relative_file(project_root, project_root, raw_value, label)


def _validated_project_root(value: Path | str) -> Path:
    root = _lexical_absolute(value)
    if not _io_path(root).exists() or not _io_path(root).is_dir():
        raise AvatarAnatomyPackageError("project_root must be an existing directory")
    current = root
    while True:
        if _is_reparse_point(current):
            raise AvatarAnatomyPackageError("project_root ancestors must not be symlinks or reparse points")
        if current.parent == current:
            break
        current = current.parent
    return root


def _project_relative(path: Path, project_root: Path) -> str:
    absolute = _lexical_absolute(path)
    root = _lexical_absolute(project_root)
    if not _is_within(absolute, root):
        raise AvatarAnatomyPackageError("artifact escapes the project")
    return Path(os.path.relpath(str(absolute), str(root))).as_posix()


class _EvidenceLedger:
    """Binds exact artifacts and proves they stayed unchanged during preflight."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = _lexical_absolute(project_root)
        self._before: dict[str, dict[str, Any]] = {}

    def bind(
        self,
        path: Path,
        *,
        expected_bytes: Any,
        expected_sha256: Any,
        label: str,
    ) -> None:
        byte_count = _bytes_count(expected_bytes, f"{label}.bytes")
        digest = _sha256(expected_sha256, f"{label}.sha256")
        actual_bytes = _file_size(path)
        actual_digest = sha256_file(path)
        if actual_bytes != byte_count:
            raise AvatarAnatomyPackageError(f"{label} byte count mismatch")
        if actual_digest != digest:
            raise AvatarAnatomyPackageError(f"{label} SHA-256 mismatch")
        relative = _project_relative(path, self.project_root)
        record = {"bytes": actual_bytes, "sha256": actual_digest}
        prior = self._before.get(relative)
        if prior is not None and prior != record:
            raise AvatarAnatomyPackageError(f"conflicting evidence binding: {relative}")
        self._before[relative] = record

    def snapshot_before(self) -> dict[str, dict[str, Any]]:
        return {key: dict(value) for key, value in sorted(self._before.items())}

    def verify_unchanged(self) -> tuple[str, str]:
        before = self.snapshot_before()
        after: dict[str, dict[str, Any]] = {}
        for relative in before:
            path = _project_file(self.project_root, relative, "bound artifact")
            after[relative] = {"bytes": _file_size(path), "sha256": sha256_file(path)}
        if after != before:
            raise AvatarAnatomyPackageError("bound source or carrier changed during preflight")
        return canonical_sha256(before), canonical_sha256(after)


def _read_bound_json(
    ledger: _EvidenceLedger,
    path: Path,
    *,
    expected_bytes: Any,
    expected_sha256: Any,
    label: str,
) -> dict[str, Any]:
    ledger.bind(
        path,
        expected_bytes=expected_bytes,
        expected_sha256=expected_sha256,
        label=label,
    )
    try:
        payload = _read_bytes(path)
    except OSError as exc:
        raise AvatarAnatomyPackageError(f"cannot read {label}") from exc
    return _parse_json_object(payload, label)


def read_glb2(path: Path) -> dict[str, Any]:
    """Read one GLB 2 JSON chunk and reject truncated or inconsistent files."""

    try:
        with _io_path(path).open("rb") as stream:
            header = stream.read(12)
            if len(header) != 12:
                raise AvatarAnatomyPackageError(f"truncated GLB: {path.name}")
            magic, version, declared_length = struct.unpack("<4sII", header)
            if magic != GLB_MAGIC or version != 2:
                raise AvatarAnatomyPackageError(f"not a GLB 2 artifact: {path.name}")
            if declared_length < 20 or declared_length % 4 or declared_length != _file_size(path):
                raise AvatarAnatomyPackageError(f"GLB declared length mismatch: {path.name}")
            chunk_header = stream.read(8)
            if len(chunk_header) != 8:
                raise AvatarAnatomyPackageError(f"GLB JSON chunk missing: {path.name}")
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            if (
                chunk_type != GLB_JSON_CHUNK
                or chunk_length % 4
                or chunk_length > declared_length - 20
            ):
                raise AvatarAnatomyPackageError(f"invalid GLB JSON chunk: {path.name}")
            raw_document_payload = stream.read(chunk_length)
            if len(raw_document_payload) != chunk_length:
                raise AvatarAnatomyPackageError(f"truncated GLB JSON chunk: {path.name}")
            remaining = declared_length - 20 - chunk_length
            binary_chunks: list[bytes] = []
            while remaining:
                if remaining < 8:
                    raise AvatarAnatomyPackageError(f"truncated trailing GLB chunk: {path.name}")
                trailing_header = stream.read(8)
                if len(trailing_header) != 8:
                    raise AvatarAnatomyPackageError(f"truncated trailing GLB chunk: {path.name}")
                trailing_length, trailing_type = struct.unpack("<II", trailing_header)
                if trailing_length % 4 or trailing_length > remaining - 8:
                    raise AvatarAnatomyPackageError(f"invalid trailing GLB chunk: {path.name}")
                trailing_payload = stream.read(trailing_length)
                if len(trailing_payload) != trailing_length:
                    raise AvatarAnatomyPackageError(f"truncated trailing GLB chunk: {path.name}")
                if trailing_type == GLB_BIN_CHUNK:
                    binary_chunks.append(trailing_payload)
                remaining -= 8 + trailing_length
            document_payload = raw_document_payload.rstrip(b" \t\r\n\x00")
    except OSError as exc:
        raise AvatarAnatomyPackageError(f"cannot read GLB: {path.name}") from exc
    document = _parse_json_object(document_payload, f"GLB JSON {path.name}")
    asset = document.get("asset")
    meshes = document.get("meshes")
    if not isinstance(asset, Mapping) or asset.get("version") != "2.0":
        raise AvatarAnatomyPackageError(f"unsupported GLB asset document: {path.name}")
    if not isinstance(meshes, list) or not meshes:
        raise AvatarAnatomyPackageError(f"GLB has no meshes: {path.name}")
    buffers = document.get("buffers")
    buffer_views = document.get("bufferViews")
    accessors = document.get("accessors")
    if (
        not isinstance(buffers, list)
        or len(buffers) != 1
        or not isinstance(buffer_views, list)
        or not isinstance(accessors, list)
        or len(binary_chunks) != 1
    ):
        raise AvatarAnatomyPackageError(f"GLB geometry buffers are incomplete: {path.name}")
    buffer = buffers[0]
    if (
        not isinstance(buffer, Mapping)
        or "uri" in buffer
        or not isinstance(buffer.get("byteLength"), int)
        or buffer["byteLength"] <= 0
        or buffer["byteLength"] > len(binary_chunks[0])
    ):
        raise AvatarAnatomyPackageError(f"GLB binary buffer is invalid: {path.name}")
    component_sizes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    for mesh_index, mesh in enumerate(meshes):
        if not isinstance(mesh, Mapping) or not isinstance(mesh.get("primitives"), list) or not mesh["primitives"]:
            raise AvatarAnatomyPackageError(f"GLB mesh has no primitives: {path.name}:{mesh_index}")
        for primitive in mesh["primitives"]:
            attributes = primitive.get("attributes") if isinstance(primitive, Mapping) else None
            position_index = attributes.get("POSITION") if isinstance(attributes, Mapping) else None
            if not isinstance(position_index, int) or not 0 <= position_index < len(accessors):
                raise AvatarAnatomyPackageError(f"GLB mesh has no POSITION accessor: {path.name}:{mesh_index}")
            accessor = accessors[position_index]
            if not isinstance(accessor, Mapping):
                raise AvatarAnatomyPackageError(f"GLB POSITION accessor is invalid: {path.name}:{mesh_index}")
            view_index = accessor.get("bufferView")
            count = accessor.get("count")
            component_size = component_sizes.get(accessor.get("componentType"))
            if (
                accessor.get("type") != "VEC3"
                or not isinstance(count, int)
                or count <= 0
                or component_size is None
                or not isinstance(view_index, int)
                or not 0 <= view_index < len(buffer_views)
            ):
                raise AvatarAnatomyPackageError(f"GLB POSITION accessor is invalid: {path.name}:{mesh_index}")
            view = buffer_views[view_index]
            if not isinstance(view, Mapping) or view.get("buffer") != 0:
                raise AvatarAnatomyPackageError(f"GLB POSITION bufferView is invalid: {path.name}:{mesh_index}")
            view_length = view.get("byteLength")
            view_offset = view.get("byteOffset", 0)
            accessor_offset = accessor.get("byteOffset", 0)
            stride = view.get("byteStride", component_size * 3)
            if (
                not all(isinstance(item, int) and item >= 0 for item in (view_length, view_offset, accessor_offset, stride))
                or stride < component_size * 3
                or view_offset + view_length > buffer["byteLength"]
                or accessor_offset + (count - 1) * stride + component_size * 3 > view_length
            ):
                raise AvatarAnatomyPackageError(f"GLB POSITION range is invalid: {path.name}:{mesh_index}")
    return document


def _mesh_bound_source_names(document: Mapping[str, Any], label: str) -> dict[str, tuple[int, ...]]:
    meshes = document["meshes"]
    result: dict[str, tuple[int, ...]] = {}
    for mesh_index, mesh in enumerate(meshes):
        positions = tuple(
            primitive["attributes"]["POSITION"]
            for primitive in mesh["primitives"]
        )
        names: list[str] = []
        if isinstance(mesh.get("name"), str) and mesh["name"].strip():
            names.append(mesh["name"].strip())
        for node in document.get("nodes", []):
            if (
                isinstance(node, Mapping)
                and node.get("mesh") == mesh_index
                and isinstance(node.get("name"), str)
                and node["name"].strip()
            ):
                names.append(node["name"].strip())
        for name in names:
            prior = result.get(name)
            if prior is not None and prior != positions:
                raise AvatarAnatomyPackageError(f"ambiguous mesh-bound source name: {label}:{name}")
            result[name] = positions
    if not result:
        raise AvatarAnatomyPackageError(f"source GLB has no named mesh or node: {label}")
    return result


def _validate_contract(
    project_root: Path,
    ledger: _EvidenceLedger,
    binding: Mapping[str, Any],
) -> tuple[dict[str, Any], Path, str, dict[str, str]]:
    path = _project_file(project_root, binding.get("path"), "contract.path")
    contract_sha = _sha256(binding.get("sha256"), "contract.sha256")
    contract = _read_bound_json(
        ledger,
        path,
        expected_bytes=binding.get("bytes"),
        expected_sha256=contract_sha,
        label="contract",
    )
    contract_id = _safe_id(contract.get("contract_id"), "contract.contract_id")
    if contract.get("schema_version") != 1:
        raise AvatarAnatomyPackageError("contract.schema_version must equal 1")
    if contract.get("status") != "SOURCE_BACKED_DESIGN_CONTRACT_ONLY_NOT_IMPLEMENTED_NOT_RUNTIME_AUTHORITY":
        raise AvatarAnatomyPackageError("contract is not the bounded design-only contract")
    if SUPPORTED_CONTRACT_SHA256.get(contract_id) != contract_sha:
        raise AvatarAnatomyPackageError("contract is not an exact supported canonical contract")
    scope = _mapping(contract.get("scope"), "contract.scope")
    if scope.get("confirmed_adult_required") is not True:
        raise AvatarAnatomyPackageError("contract must require confirmed-adult routing")
    for key in (
        "external_body_mesh_mutation_authorized",
        "approved_face_mutation_authorized",
        "approved_skin_mutation_authorized",
        "carrier_rig_mutation_authorized",
        "blender_execution_authorized",
        "runtime_activation_authorized",
        "explicit_behavior_scene_authorized",
        "physiology_simulation_implemented",
    ):
        if scope.get(key) is not False:
            raise AvatarAnatomyPackageError(f"contract scope must keep {key} false")
    privacy = _mapping(contract.get("maturity_and_privacy"), "contract.maturity_and_privacy")
    required_privacy = {
        "maturity_status_required": "confirmed_adult",
        "non_adult_or_unresolved_body_representation": "doll_safe_non_anatomical",
        "default_module_visible": False,
        "private_review_lease_required": True,
        "review_lease_is_consent_or_activity_authority": False,
        "public_export_allowed": False,
        "general_gallery_allowed": False,
        "runtime_instantiation_allowed": False,
    }
    for key, expected in required_privacy.items():
        if privacy.get(key) != expected:
            raise AvatarAnatomyPackageError(f"contract privacy invariant failed: {key}")
    relationships = _mapping(contract.get("spatial_relationships"), "contract.spatial_relationships")
    for key in (
        "compartment_merging_allowed",
        "shared_lumen_allowed",
        "shared_external_endpoint_allowed",
    ):
        if relationships.get(key) is not False:
            raise AvatarAnatomyPackageError(f"contract route invariant failed: {key}")
    groups = _mapping(contract.get("required_module_meshes"), "contract.required_module_meshes")
    inventory: dict[str, str] = {}
    for system, raw_ids in groups.items():
        system_id = _safe_id(system, "contract system")
        for raw_id in _list(raw_ids, f"contract.required_module_meshes.{system_id}"):
            anatomy_id = _safe_id(raw_id, "contract anatomy_id")
            if anatomy_id in inventory:
                raise AvatarAnatomyPackageError(f"duplicate contract anatomy_id: {anatomy_id}")
            inventory[anatomy_id] = system_id
    if not inventory:
        raise AvatarAnatomyPackageError("contract required anatomy inventory is empty")
    interface = _mapping(contract.get("attachment_interface"), "contract.attachment_interface")
    if interface.get("source_carrier_hash_must_match_before_and_after") is not True:
        raise AvatarAnatomyPackageError("contract must preserve the source carrier hash")
    if interface.get("module_local_armature_or_deformer_required") is not True:
        raise AvatarAnatomyPackageError("contract must require a module-local deformer")
    if interface.get("carrier_dependency_mode") != "READ_ONLY_TRANSFORM_FOLLOWING_ONLY":
        raise AvatarAnatomyPackageError("contract carrier dependency must be read-only")
    materials = _mapping(contract.get("materials"), "contract.materials")
    if materials.get("fluid_or_activity_animation_allowed") is not False:
        raise AvatarAnatomyPackageError("contract must not claim function or activity animation")
    truth = _mapping(contract.get("truth_limits"), "contract.truth_limits")
    for key in (
        "geometry_proves_biological_function",
        "urination_implemented",
        "defecation_implemented",
        "menstrual_cycle_implemented",
        "pregnancy_implemented",
        "sensation_implemented",
        "health_or_diagnosis_implemented",
        "anatomy_or_body_response_is_consent",
        "anatomy_or_body_response_is_desire_or_preference",
    ):
        if truth.get(key) is not False:
            raise AvatarAnatomyPackageError(f"contract truth invariant failed: {key}")
    return contract, path, contract_sha, inventory


def _validate_source_manifest(
    project_root: Path,
    ledger: _EvidenceLedger,
    binding: Mapping[str, Any],
) -> tuple[dict[str, Any], Path, dict[str, dict[str, Any]]]:
    authority_id = _safe_id(binding.get("authority_id"), "source_package.authority_id")
    authority = SUPPORTED_SOURCE_PACKAGES.get(authority_id)
    if authority is None:
        raise AvatarAnatomyPackageError("source package authority is not registered")
    if binding.get("manifest_sha256") != authority["source_manifest_sha256"]:
        raise AvatarAnatomyPackageError("source manifest is not pinned by its authority record")
    manifest_path = _project_file(
        project_root,
        binding.get("manifest_path"),
        "source_package.manifest_path",
    )
    manifest = _read_bound_json(
        ledger,
        manifest_path,
        expected_bytes=binding.get("manifest_bytes"),
        expected_sha256=binding.get("manifest_sha256"),
        label="source package manifest",
    )
    if manifest.get("schema") != HRA_SCHEMA or manifest.get("status") != HRA_STATUS:
        raise AvatarAnatomyPackageError("source manifest is not the bounded HRA intake schema/status")
    retrieved = _text(manifest.get("retrieved_utc_date"), "source retrieved_utc_date")
    if not DATE_RE.fullmatch(retrieved):
        raise AvatarAnatomyPackageError("source retrieved_utc_date must use YYYY-MM-DD")
    collection = _mapping(manifest.get("source_collection"), "source manifest.source_collection")
    if collection.get("name") != HRA_COLLECTION_NAME or collection.get("portal") != HRA_PORTAL:
        raise AvatarAnatomyPackageError("source collection is not the bounded HRA collection")
    if collection.get("visible_human_source") != HRA_VISIBLE_HUMAN_SOURCE:
        raise AvatarAnatomyPackageError("source Visible Human provenance is missing")
    license_name = _text(collection.get("license"), "source license")
    if license_name not in SUPPORTED_LICENSES:
        raise AvatarAnatomyPackageError(f"unsupported source license: {license_name}")
    license_url = _text(collection.get("license_url"), "source license_url")
    if not HTTPS_RE.fullmatch(license_url):
        raise AvatarAnatomyPackageError("source license_url must be HTTPS")
    if CANONICAL_LICENSE_URLS[license_name] != license_url:
        raise AvatarAnatomyPackageError("source license_url does not match the declared license")
    _text(collection.get("attribution"), "source attribution")
    validation = _mapping(manifest.get("validation"), "source manifest.validation")
    expected_validation = {
        "glb_magic": "glTF",
        "glb_version": 2,
        "declared_length_matches_file": True,
        "json_chunk_decoded": True,
        "all_files_passed": True,
    }
    for key, expected in expected_validation.items():
        if validation.get(key) != expected:
            raise AvatarAnatomyPackageError(f"source validation is not affirmative: {key}")
    boundary = set(_list(manifest.get("truth_boundary"), "source manifest.truth_boundary"))
    if not REQUIRED_SOURCE_TRUTH_BOUNDARY.issubset(boundary):
        missing = sorted(REQUIRED_SOURCE_TRUTH_BOUNDARY - boundary)
        raise AvatarAnatomyPackageError(f"source truth boundary missing: {','.join(missing)}")
    source_files: dict[str, dict[str, Any]] = {}
    for index, raw_record in enumerate(_list(manifest.get("files"), "source manifest.files")):
        record = _mapping(raw_record, f"source manifest.files[{index}]")
        raw_path = _text(record.get("path"), f"source manifest.files[{index}].path")
        if raw_path in source_files:
            raise AvatarAnatomyPackageError(f"duplicate source path: {raw_path}")
        path = _safe_relative_file(
            project_root,
            manifest_path.parent,
            raw_path,
            f"source manifest.files[{index}].path",
        )
        ledger.bind(
            path,
            expected_bytes=record.get("bytes"),
            expected_sha256=record.get("sha256"),
            label=f"source file {raw_path}",
        )
        url = _text(record.get("url"), f"source file {raw_path}.url")
        if not HTTPS_RE.fullmatch(url) or not url.startswith(HRA_SOURCE_URL_PREFIX):
            raise AvatarAnatomyPackageError(f"source file URL must be a bounded HRA URL: {raw_path}")
        mesh_count = _bytes_count(record.get("mesh_count"), f"source file {raw_path}.mesh_count")
        document = read_glb2(path)
        if len(document["meshes"]) != mesh_count:
            raise AvatarAnatomyPackageError(f"source mesh_count mismatch: {raw_path}")
        source_name_geometry = _mesh_bound_source_names(document, raw_path)
        source_files[raw_path] = {
            "path": path,
            "bytes": _file_size(path),
            "sha256": sha256_file(path),
            "url": url,
            "mesh_count": mesh_count,
            "source_name_geometry": source_name_geometry,
        }
    if not source_files:
        raise AvatarAnatomyPackageError("source manifest has no GLB files")
    return manifest, manifest_path, source_files


def _validate_source_role_map(
    project_root: Path,
    ledger: _EvidenceLedger,
    binding: Mapping[str, Any],
    *,
    source_manifest_path: Path,
    source_manifest_sha256: str,
    contract_path: Path,
    contract_sha256: str,
    inventory: Mapping[str, str],
    source_files: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], Path, dict[str, dict[str, Any]], list[str], dict[str, Any]]:
    authority_id = _safe_id(binding.get("authority_id"), "source_package.authority_id")
    authority = SUPPORTED_SOURCE_PACKAGES.get(authority_id)
    if authority is None:
        raise AvatarAnatomyPackageError("source package authority is not registered")
    if (
        binding.get("role_map_sha256") != authority["role_map_sha256"]
        or contract_sha256 != authority["contract_sha256"]
    ):
        raise AvatarAnatomyPackageError("source role map is not pinned by its authority record")
    role_map_path = _project_file(
        project_root,
        binding.get("role_map_path"),
        "source_package.role_map_path",
    )
    role_map = _read_bound_json(
        ledger,
        role_map_path,
        expected_bytes=binding.get("role_map_bytes"),
        expected_sha256=binding.get("role_map_sha256"),
        label="source anatomy role map",
    )
    if role_map.get("schema_version") != 1:
        raise AvatarAnatomyPackageError("source role map schema_version must equal 1")
    _safe_id(role_map.get("role_map_id"), "source role_map_id")
    source_binding = _mapping(role_map.get("source_manifest"), "role map.source_manifest")
    if (
        source_binding.get("path") != _project_relative(source_manifest_path, project_root)
        or source_binding.get("bytes") != _file_size(source_manifest_path)
        or source_binding.get("sha256") != source_manifest_sha256
    ):
        raise AvatarAnatomyPackageError("source role map does not bind the exact source manifest")
    contract_binding = _mapping(role_map.get("anatomy_contract"), "role map.anatomy_contract")
    if (
        contract_binding.get("path") != _project_relative(contract_path, project_root)
        or contract_binding.get("bytes") != _file_size(contract_path)
        or contract_binding.get("sha256") != contract_sha256
    ):
        raise AvatarAnatomyPackageError("source role map does not bind the exact anatomy contract")
    license_record = _mapping(role_map.get("license"), "role map.license")
    if (
        license_record.get("id") != "CC-BY-4.0"
        or license_record.get("url") != CANONICAL_LICENSE_URLS["CC BY 4.0"]
        or not isinstance(license_record.get("attribution"), str)
        or not license_record["attribution"].strip()
        or license_record.get("adaptation_notice_required") is not True
        or license_record.get("private_clinical_review_derivatives_only") is not True
    ):
        raise AvatarAnatomyPackageError("source role map license boundary is invalid")
    normalization = _mapping(role_map.get("normalization"), "role map.normalization")
    if (
        normalization.get("source_format") != "glTF-2.0-binary"
        or normalization.get("source_units") != "meters"
        or normalization.get("source_axes") != "gltf_right_handed_y_up"
        or normalization.get("target_units") != "meters"
        or normalization.get("target_axes") != "blender_right_handed_z_up"
        or normalization.get("per_source_transform") is not None
        or normalization.get("transform_sha256") is not None
        or normalization.get("status") != "REQUIRED_NOT_RUN"
    ):
        raise AvatarAnatomyPackageError("source role map normalization frame is invalid")
    roles: dict[str, dict[str, Any]] = {}
    for index, raw_role in enumerate(_list(role_map.get("source_roles"), "role map.source_roles")):
        role = _mapping(raw_role, f"role map.source_roles[{index}]")
        anatomy_id = _safe_id(role.get("anatomy_id"), "role map anatomy_id")
        if anatomy_id in roles or anatomy_id not in inventory:
            raise AvatarAnatomyPackageError(f"duplicate or unknown source role: {anatomy_id}")
        source_file = _text(role.get("source_file"), f"source role {anatomy_id}.source_file")
        if source_file not in source_files:
            raise AvatarAnatomyPackageError(f"source role file is not manifest-bound: {anatomy_id}")
        system = _safe_id(role.get("system"), f"source role {anatomy_id}.system")
        if system != inventory[anatomy_id]:
            raise AvatarAnatomyPackageError(f"source role system mismatch: {anatomy_id}")
        laterality = _text(role.get("laterality"), f"source role {anatomy_id}.laterality")
        source_nodes = [
            _text(item, f"source role {anatomy_id}.source_nodes")
            for item in _list(role.get("source_nodes"), f"source role {anatomy_id}.source_nodes")
        ]
        if not source_nodes or len(set(source_nodes)) != len(source_nodes):
            raise AvatarAnatomyPackageError(f"source role nodes must be non-empty and unique: {anatomy_id}")
        source_geometry = source_files[source_file]["source_name_geometry"]
        if any(node not in source_geometry for node in source_nodes):
            raise AvatarAnatomyPackageError(f"source role node is not mesh-bound: {anatomy_id}")
        canonical_nodes = HRA_SOURCE_ROLE_MAP.get(anatomy_id, {}).get(source_file)
        directly_named_synthetic_role = (
            authority.get("allow_direct_semantic_nodes") is True
            and source_nodes == [anatomy_id]
        )
        if not directly_named_synthetic_role and (
            canonical_nodes is None or set(source_nodes) != set(canonical_nodes)
        ):
            raise AvatarAnatomyPackageError(f"source role semantics are not recognized: {anatomy_id}")
        if role.get("function_implemented") is not False:
            raise AvatarAnatomyPackageError(f"source role cannot claim function: {anatomy_id}")
        roles[anatomy_id] = {
            "anatomy_id": anatomy_id,
            "system": system,
            "laterality": laterality,
            "source_file": source_file,
            "source_nodes": sorted(source_nodes),
            "function_implemented": False,
        }
    missing = sorted(set(inventory) - set(roles))
    expected_status = (
        "SOURCE_ROLE_MAP_INCOMPLETE_NORMALIZATION_NOT_RUN"
        if missing
        else "SOURCE_ROLE_MAP_COMPLETE_NORMALIZATION_DECLARED"
    )
    if role_map.get("status") != expected_status:
        raise AvatarAnatomyPackageError("source role map completeness status is inconsistent")
    anchor_references = _mapping(
        role_map.get("external_anchor_references"),
        "role map.external_anchor_references",
    )
    truth = _mapping(role_map.get("truth_limits"), "role map.truth_limits")
    for key in (
        "source_role_is_authored_component",
        "normalization_or_carrier_fit_completed",
        "external_anatomy_complete",
        "internal_anatomy_complete",
        "function_implemented",
        "runtime_activation_allowed",
        "public_export_allowed",
    ):
        if truth.get(key) is not False:
            raise AvatarAnatomyPackageError(f"source role map truth boundary failed: {key}")
    return role_map, role_map_path, roles, missing, dict(anchor_references)


def _finite_matrix(value: Any, label: str) -> list[float]:
    entries = _list(value, label)
    if len(entries) != 16:
        raise AvatarAnatomyPackageError(f"{label} must contain 16 values")
    result: list[float] = []
    for entry in entries:
        if isinstance(entry, bool) or not isinstance(entry, (int, float)):
            raise AvatarAnatomyPackageError(f"{label} must be numeric")
        number = float(entry)
        if not math.isfinite(number):
            raise AvatarAnatomyPackageError(f"{label} must be finite")
        result.append(number)
    if result[12:] != [0.0, 0.0, 0.0, 1.0]:
        raise AvatarAnatomyPackageError(f"{label} must be an affine 4x4 row-major matrix")
    determinant = (
        result[0] * (result[5] * result[10] - result[6] * result[9])
        - result[1] * (result[4] * result[10] - result[6] * result[8])
        + result[2] * (result[4] * result[9] - result[5] * result[8])
    )
    if abs(determinant) < 1.0e-12:
        raise AvatarAnatomyPackageError(f"{label} must be invertible")
    return result


def _axes(value: Any, label: str) -> dict[str, str]:
    axes = _mapping(value, label)
    result = {
        "up": _text(axes.get("up"), f"{label}.up"),
        "forward": _text(axes.get("forward"), f"{label}.forward"),
        "handedness": _text(axes.get("handedness"), f"{label}.handedness"),
    }
    if result["up"] not in SUPPORTED_AXES or result["forward"] not in SUPPORTED_AXES:
        raise AvatarAnatomyPackageError(f"{label} has unsupported axes")
    if result["up"][-1] == result["forward"][-1]:
        raise AvatarAnatomyPackageError(f"{label} up and forward axes are parallel")
    if result["handedness"] not in {"left", "right"}:
        raise AvatarAnatomyPackageError(f"{label}.handedness is invalid")
    return result


def _axis_vector(axis: str) -> tuple[float, float, float]:
    sign = 1.0 if axis[0] == "+" else -1.0
    index = {"X": 0, "Y": 1, "Z": 2}[axis[1]]
    values = [0.0, 0.0, 0.0]
    values[index] = sign
    return values[0], values[1], values[2]


def _transform_direction(matrix: Sequence[float], vector: Sequence[float]) -> tuple[float, float, float]:
    return tuple(
        sum(matrix[row * 4 + column] * vector[column] for column in range(3))
        for row in range(3)
    )


def _validate_coordinate_transform(
    matrix: Sequence[float],
    *,
    source_units: str,
    source_axes: Mapping[str, str],
    target_axes: Mapping[str, str],
    label: str,
) -> None:
    scale = UNIT_TO_METERS[source_units] / UNIT_TO_METERS[TARGET_UNITS]
    tolerance = max(1.0e-10, scale * 1.0e-8)
    columns = [tuple(matrix[row * 4 + column] for row in range(3)) for column in range(3)]
    for column in columns:
        norm = math.sqrt(sum(value * value for value in column))
        if not math.isclose(norm, scale, rel_tol=1.0e-8, abs_tol=tolerance):
            raise AvatarAnatomyPackageError(f"{label} does not apply the declared unit scale")
    for first in range(3):
        for second in range(first + 1, 3):
            dot = sum(columns[first][index] * columns[second][index] for index in range(3))
            if not math.isclose(dot, 0.0, rel_tol=0.0, abs_tol=tolerance * scale):
                raise AvatarAnatomyPackageError(f"{label} contains shear")
    for semantic in ("up", "forward"):
        actual = _transform_direction(matrix, _axis_vector(source_axes[semantic]))
        target = tuple(scale * value for value in _axis_vector(target_axes[semantic]))
        if any(
            not math.isclose(actual[index], target[index], rel_tol=1.0e-8, abs_tol=tolerance)
            for index in range(3)
        ):
            raise AvatarAnatomyPackageError(
                f"{label} does not convert the declared {semantic} axis"
            )
    determinant = (
        matrix[0] * (matrix[5] * matrix[10] - matrix[6] * matrix[9])
        - matrix[1] * (matrix[4] * matrix[10] - matrix[6] * matrix[8])
        + matrix[2] * (matrix[4] * matrix[9] - matrix[5] * matrix[8])
    )
    expected_sign = 1.0 if source_axes["handedness"] == target_axes["handedness"] else -1.0
    if not math.isclose(
        determinant,
        expected_sign * scale**3,
        rel_tol=1.0e-7,
        abs_tol=max(1.0e-15, scale**3 * 1.0e-8),
    ):
        raise AvatarAnatomyPackageError(f"{label} does not preserve declared handedness")


def _validate_normalization(
    value: Mapping[str, Any],
    source_files: Mapping[str, Mapping[str, Any]],
    role_map: Mapping[str, Any],
) -> dict[str, Any]:
    source_units = _text(value.get("source_units"), "normalization.source_units")
    target_units = _text(value.get("target_units"), "normalization.target_units")
    if source_units not in SUPPORTED_UNITS:
        raise AvatarAnatomyPackageError("normalization.source_units is unsupported")
    if target_units != TARGET_UNITS:
        raise AvatarAnatomyPackageError("normalization.target_units must be meters")
    source_axes = _axes(value.get("source_axes"), "normalization.source_axes")
    target_axes = _axes(value.get("target_axes"), "normalization.target_axes")
    role_normalization = _mapping(role_map.get("normalization"), "role map.normalization")
    if (
        source_units != role_normalization.get("source_units")
        or target_units != role_normalization.get("target_units")
        or source_axes != HRA_SOURCE_AXES
        or role_normalization.get("source_axes") != "gltf_right_handed_y_up"
        or role_normalization.get("target_axes") != "blender_right_handed_z_up"
    ):
        raise AvatarAnatomyPackageError(
            "normalization frame does not match the pinned source role map"
        )
    if target_axes != TARGET_AXES:
        raise AvatarAnatomyPackageError("normalization.target_axes must be Blender +Z/-Y right-handed")
    raw_transforms = _mapping(
        value.get("per_source_transform"),
        "normalization.per_source_transform",
    )
    if set(raw_transforms) != set(source_files):
        raise AvatarAnatomyPackageError("normalization transforms must exactly cover source files")
    transforms = {
        source_path: _finite_matrix(
            raw_transforms[source_path],
            f"normalization.per_source_transform.{source_path}",
        )
        for source_path in sorted(source_files)
    }
    for source_path, matrix in transforms.items():
        _validate_coordinate_transform(
            matrix,
            source_units=source_units,
            source_axes=source_axes,
            target_axes=target_axes,
            label=f"normalization.per_source_transform.{source_path}",
        )
        if matrix != list(HRA_TO_BLENDER_TRANSFORM):
            raise AvatarAnatomyPackageError(
                f"normalization.per_source_transform.{source_path} is not the "
                "canonical zero-translation HRA-to-Blender transform"
            )
    normalized = {
        "source_units": source_units,
        "target_units": target_units,
        "source_axes": source_axes,
        "target_axes": target_axes,
        "per_source_transform": transforms,
    }
    expected_hash = _sha256(value.get("transform_sha256"), "normalization.transform_sha256")
    if canonical_sha256(normalized) != expected_hash:
        raise AvatarAnatomyPackageError("normalization.transform_sha256 mismatch")
    normalized["transform_sha256"] = expected_hash
    return normalized


def _validate_carrier(
    project_root: Path,
    ledger: _EvidenceLedger,
    value: Mapping[str, Any],
    candidate_id: str,
) -> tuple[dict[str, Any], list[str]]:
    authority_id = _safe_id(value.get("authority_id"), "carrier.authority_id")
    authority = SUPPORTED_CARRIER_AUTHORITIES.get(authority_id)
    if authority is None:
        raise AvatarAnatomyPackageError("carrier authority is not registered")
    blockers: list[str] = []
    carrier_path = _project_file(project_root, value.get("path"), "carrier.path")
    if carrier_path.suffix.lower() != ".blend":
        raise AvatarAnatomyPackageError("carrier must be an exact-hash .blend artifact")
    carrier_sha = _sha256(value.get("sha256"), "carrier.sha256")
    if carrier_sha != authority["carrier_sha256"]:
        raise AvatarAnatomyPackageError("carrier artifact is not pinned by its authority record")
    ledger.bind(
        carrier_path,
        expected_bytes=value.get("bytes"),
        expected_sha256=carrier_sha,
        label="carrier",
    )
    _validate_blender_carrier_container(carrier_path, authority)
    before = _sha256(value.get("source_hash_before"), "carrier.source_hash_before")
    after = _sha256(value.get("source_hash_after"), "carrier.source_hash_after")
    if before != carrier_sha or after != carrier_sha or before != after:
        raise AvatarAnatomyPackageError("carrier source hashes before/after must equal the carrier SHA-256")
    expected_object_ids = authority.get("object_ids")
    if expected_object_ids is None:
        if value.get("object_ids") != []:
            raise AvatarAnatomyPackageError(
                "carrier.object_ids must remain empty until authority-bound extraction"
            )
        object_ids: list[str] = []
        blockers.append("carrier_object_inventory_not_qualified")
    else:
        object_ids = [
            _safe_id(item, "carrier.object_id")
            for item in _list(value.get("object_ids"), "carrier.object_ids")
        ]
        if not object_ids or len(set(object_ids)) != len(object_ids):
            raise AvatarAnatomyPackageError("carrier.object_ids must be non-empty and unique")
        if object_ids != expected_object_ids:
            raise AvatarAnatomyPackageError("carrier.object_ids differ from carrier authority")
    expected_armature_id = authority.get("armature_id")
    raw_armature_id = value.get("armature_id")
    if expected_armature_id is None:
        if raw_armature_id is not None:
            raise AvatarAnatomyPackageError(
                "carrier.armature_id must remain null until authority-bound extraction"
            )
        armature_id = None
    else:
        armature_id = _safe_id(raw_armature_id, "carrier.armature_id")
        if armature_id != expected_armature_id:
            raise AvatarAnatomyPackageError("carrier.armature_id differs from carrier authority")
    expected_rest_pose = authority.get("rest_pose_matrix")
    if expected_rest_pose is None:
        if value.get("rest_pose_matrix") is not None:
            raise AvatarAnatomyPackageError(
                "carrier.rest_pose_matrix must remain null until authority-bound extraction"
            )
        rest_pose = None
        blockers.append("carrier_rest_pose_not_qualified")
    else:
        rest_pose = _finite_matrix(value.get("rest_pose_matrix"), "carrier.rest_pose_matrix")
        if rest_pose != expected_rest_pose:
            raise AvatarAnatomyPackageError(
                "carrier.rest_pose_matrix differs from carrier authority"
            )

    qualification_path = _project_file(
        project_root,
        value.get("qualification_manifest_path"),
        "carrier.qualification_manifest_path",
    )
    qualification = _read_bound_json(
        ledger,
        qualification_path,
        expected_bytes=value.get("qualification_manifest_bytes"),
        expected_sha256=value.get("qualification_manifest_sha256"),
        label="carrier qualification manifest",
    )
    qualification_sha = _sha256(
        value.get("qualification_manifest_sha256"),
        "carrier.qualification_manifest_sha256",
    )
    if qualification_sha != authority["qualification_manifest_sha256"]:
        raise AvatarAnatomyPackageError(
            "carrier qualification is not pinned by its authority record"
        )
    owner_path = _project_file(
        project_root,
        value.get("owner_acceptance_path"),
        "carrier.owner_acceptance_path",
    )
    owner = _read_bound_json(
        ledger,
        owner_path,
        expected_bytes=value.get("owner_acceptance_bytes"),
        expected_sha256=value.get("owner_acceptance_sha256"),
        label="carrier owner acceptance",
    )
    owner_sha = _sha256(
        value.get("owner_acceptance_sha256"),
        "carrier.owner_acceptance_sha256",
    )
    owner_authority_bound = authority.get("owner_acceptance_sha256") == owner_sha
    carrier_relative = _project_relative(carrier_path, project_root)
    foundation_id = _safe_id(value.get("foundation_id"), "carrier.foundation_id")
    qualified_source = (
        qualification.get("source_artifact")
        if isinstance(qualification.get("source_artifact"), Mapping)
        else {}
    )
    qualification_accepted = (
        qualification.get("schema_version") == 1
        and qualification.get("artifact_type") == "adult_foundation_qualification_result"
        and qualification.get("status") == "QUALIFIED_INACTIVE"
        and qualification.get("foundation_id") == foundation_id
        and qualified_source.get("path") == carrier_relative
        and qualified_source.get("sha256") == carrier_sha
        and qualification.get("qualified_for_adult_foundation") is True
        and qualification.get("adult_eligible") is True
        and qualification.get("complete_adult_topology_proven") is True
        and qualification.get("blockers") == []
        and qualification.get("build_performed_by_evaluator") is False
        and qualification.get("render_performed") is False
        and qualification.get("export_performed") is False
        and qualification.get("runtime_mutation_performed") is False
        and qualification.get("runtime_activation_allowed") is False
        and qualification.get("public_export_allowed") is False
        and qualification.get("clothing_applied") is False
        and qualification.get("armature_present") is True
        and qualification.get("pose_space_deformation_audit_passed") is True
    )
    if armature_id is None and qualification.get("armature_present") is not False:
        raise AvatarAnatomyPackageError(
            "carrier.armature_id may be null only when qualification.armature_present is false"
        )
    if not qualification_accepted:
        blockers.append("carrier_qualification_not_accepted")
    if qualification.get("armature_present") is not True:
        blockers.append("carrier_armature_not_qualified")
    if qualification.get("pose_space_deformation_audit_passed") is not True:
        blockers.append("carrier_pose_space_deformation_not_qualified")
    owner_accepted = (
        owner.get("schema_version") == 1
        and owner_authority_bound
        and owner.get("artifact_type") == "private_inactive_carrier_owner_acceptance"
        and owner.get("status") == "OWNER_ACCEPTED_PRIVATE_INACTIVE_CARRIER"
        and owner.get("candidate_id") == candidate_id
        and owner.get("foundation_id") == foundation_id
        and owner.get("carrier_sha256") == carrier_sha
        and owner.get("owner_approved") is True
        and owner.get("runtime_activation_allowed") is False
        and owner.get("public_export_allowed") is False
    )
    if not owner_accepted:
        blockers.append("carrier_owner_acceptance_missing_or_false")
    return (
        {
            "path": carrier_relative,
            "authority_id": authority_id,
            "authority_record_sha256": canonical_sha256(authority),
            "bytes": _file_size(carrier_path),
            "sha256": carrier_sha,
            "qualification_manifest_path": _project_relative(qualification_path, project_root),
            "qualification_manifest_sha256": sha256_file(qualification_path),
            "owner_acceptance_path": _project_relative(owner_path, project_root),
            "owner_acceptance_sha256": sha256_file(owner_path),
            "rest_pose_matrix": rest_pose,
            "object_ids": object_ids,
            "armature_id": armature_id,
            "foundation_id": foundation_id,
            "source_hash_before": before,
            "source_hash_after": after,
            "qualification_accepted": qualification_accepted,
            "owner_accepted": owner_accepted,
        },
        blockers,
    )


def _validate_components(
    raw_components: Any,
    inventory: Mapping[str, str],
    source_roles: Mapping[str, Mapping[str, Any]],
    source_files: Mapping[str, Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    required_metadata = set(
        _list(contract.get("per_mesh_required_metadata"), "contract.per_mesh_required_metadata")
    )
    material_ids = set(
        _list(
            _mapping(contract.get("materials"), "contract.materials").get("required_distinct_material_ids"),
            "contract.materials.required_distinct_material_ids",
        )
    )
    contract_id = _safe_id(contract.get("contract_id"), "contract.contract_id")
    components: list[dict[str, Any]] = []
    seen: set[str] = set()
    used_source_geometry: set[tuple[str, int]] = set()
    blockers: list[str] = []
    for index, raw in enumerate(_list(raw_components, "components")):
        component = _mapping(raw, f"components[{index}]")
        missing_metadata = required_metadata - set(component)
        if missing_metadata:
            raise AvatarAnatomyPackageError(
                f"components[{index}] missing contract metadata: {','.join(sorted(missing_metadata))}"
            )
        allowed_component_fields = required_metadata | {
            "source_file",
            "source_file_sha256",
            "source_nodes",
        }
        if set(component) != allowed_component_fields:
            unexpected = sorted(set(component) - allowed_component_fields)
            missing_fields = sorted(allowed_component_fields - set(component))
            raise AvatarAnatomyPackageError(
                "component fields must exactly match the preflight schema: "
                f"unexpected={unexpected},missing={missing_fields}"
            )
        anatomy_id = _safe_id(component.get("anatomy_id"), f"components[{index}].anatomy_id")
        if anatomy_id in seen:
            raise AvatarAnatomyPackageError(f"duplicate component anatomy_id: {anatomy_id}")
        seen.add(anatomy_id)
        if anatomy_id not in inventory:
            raise AvatarAnatomyPackageError(f"component is outside contract inventory: {anatomy_id}")
        if anatomy_id not in source_roles:
            raise AvatarAnatomyPackageError(f"component has no source role-map authority: {anatomy_id}")
        source_role = source_roles[anatomy_id]
        system = _safe_id(component.get("system"), f"components[{index}].system")
        if system != inventory[anatomy_id]:
            raise AvatarAnatomyPackageError(f"component system mismatch: {anatomy_id}")
        laterality = _text(component.get("laterality"), f"components[{index}].laterality")
        expected_laterality = "left" if anatomy_id.endswith("_left") else "right" if anatomy_id.endswith("_right") else None
        if laterality not in {"none", "midline", "left", "right", "paired", "bilateral"}:
            raise AvatarAnatomyPackageError(f"component laterality is invalid: {anatomy_id}")
        if expected_laterality is not None and laterality != expected_laterality:
            raise AvatarAnatomyPackageError(f"component laterality mismatch: {anatomy_id}")
        if laterality != source_role["laterality"]:
            raise AvatarAnatomyPackageError(f"component laterality differs from source role: {anatomy_id}")
        source_file = _text(component.get("source_file"), f"components[{index}].source_file")
        if source_file not in source_files:
            raise AvatarAnatomyPackageError(f"component source file is not manifest-bound: {anatomy_id}")
        if source_file != source_role["source_file"]:
            raise AvatarAnatomyPackageError(f"component source file differs from source role: {anatomy_id}")
        source_sha = _sha256(
            component.get("source_file_sha256"),
            f"components[{index}].source_file_sha256",
        )
        if source_sha != source_files[source_file]["sha256"]:
            raise AvatarAnatomyPackageError(f"component source SHA-256 mismatch: {anatomy_id}")
        source_nodes = [
            _text(item, f"components[{index}].source_nodes")
            for item in _list(component.get("source_nodes"), f"components[{index}].source_nodes")
        ]
        if not source_nodes or len(set(source_nodes)) != len(source_nodes):
            raise AvatarAnatomyPackageError(f"component source_nodes are empty or duplicate: {anatomy_id}")
        if set(source_nodes) != set(source_role["source_nodes"]):
            raise AvatarAnatomyPackageError(f"component source_nodes differ from source role: {anatomy_id}")
        source_name_geometry = source_files[source_file]["source_name_geometry"]
        component_geometry = {
            (source_file, accessor)
            for source_node in source_nodes
            for accessor in source_name_geometry[source_node]
        }
        if used_source_geometry.intersection(component_geometry):
            raise AvatarAnatomyPackageError(f"component source geometry is reused: {anatomy_id}")
        used_source_geometry.update(component_geometry)
        review_visibility = _text(
            component.get("review_visibility"),
            f"components[{index}].review_visibility",
        )
        if review_visibility != "PRIVATE_INACTIVE_DEFAULT_HIDDEN":
            blockers.append(f"component_not_private_hidden:{anatomy_id}")
        material_id = _safe_id(component.get("material_id"), f"components[{index}].material_id")
        if material_id not in material_ids:
            raise AvatarAnatomyPackageError(f"component material is outside contract: {anatomy_id}")
        if MATERIAL_FOR_SYSTEM.get(system) != material_id:
            raise AvatarAnatomyPackageError(f"component material/system mismatch: {anatomy_id}")
        if component.get("source_contract_id") != contract_id:
            raise AvatarAnatomyPackageError(f"component contract binding mismatch: {anatomy_id}")
        if component.get("function_implemented") is not False:
            blockers.append(f"component_function_claimed:{anatomy_id}")
        components.append(
            {
                "anatomy_id": anatomy_id,
                "system": system,
                "laterality": laterality,
                "source_file": source_file,
                "source_file_sha256": source_sha,
                "source_nodes": sorted(source_nodes),
                "review_visibility": review_visibility,
                "material_id": material_id,
                "source_contract_id": contract_id,
                "function_implemented": component.get("function_implemented"),
            }
        )
    missing = sorted(set(inventory) - seen)
    return sorted(components, key=lambda item: item["anatomy_id"]), missing, blockers


def _validate_anchors_routes(
    raw_anchors: Any,
    raw_routes: Any,
    contract: Mapping[str, Any],
    inventory: Mapping[str, str],
    mapped_ids: set[str],
    source_files: Mapping[str, Mapping[str, Any]],
    normalization: Mapping[str, Any],
    anchor_references: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    interface = _mapping(contract.get("attachment_interface"), "contract.attachment_interface")
    required_anchor_ids = {
        _safe_id(item, "contract anchor")
        for item in _list(interface.get("required_anchor_ids"), "contract required anchors")
    }
    if set(anchor_references) != required_anchor_ids:
        raise AvatarAnatomyPackageError("source role map anchors must exactly match the contract")
    source_name_locations: dict[str, list[str]] = {}
    for source_file, evidence in source_files.items():
        for source_name in evidence["source_name_geometry"]:
            source_name_locations.setdefault(source_name, []).append(source_file)
    expected_anchor_sources: dict[str, tuple[str, str]] = {}
    unavailable_anchor_ids: set[str] = set()
    for anchor_id in sorted(required_anchor_ids):
        reference = anchor_references[anchor_id]
        if reference is None:
            unavailable_anchor_ids.add(anchor_id)
            continue
        source_node = _text(reference, f"role map anchor {anchor_id}")
        locations = source_name_locations.get(source_node, [])
        if len(locations) != 1:
            unavailable_anchor_ids.add(anchor_id)
            continue
        expected_anchor_sources[anchor_id] = (locations[0], source_node)
    anchors: list[dict[str, Any]] = []
    seen_anchors: set[str] = set()
    for index, raw in enumerate(_list(raw_anchors, "anchors")):
        anchor = _mapping(raw, f"anchors[{index}]")
        if set(anchor) != {
            "anchor_id",
            "source_file",
            "source_node",
            "source_bound",
            "authored",
            "transform",
        }:
            raise AvatarAnatomyPackageError("anchor fields must exactly match the preflight schema")
        anchor_id = _safe_id(anchor.get("anchor_id"), f"anchors[{index}].anchor_id")
        if anchor_id in seen_anchors:
            raise AvatarAnatomyPackageError(f"duplicate anchor_id: {anchor_id}")
        if anchor_id not in required_anchor_ids:
            raise AvatarAnatomyPackageError(f"unexpected anchor_id: {anchor_id}")
        if anchor_id not in expected_anchor_sources:
            raise AvatarAnatomyPackageError(
                f"anchor has no exact mesh-bound source role-map reference: {anchor_id}"
            )
        seen_anchors.add(anchor_id)
        expected_source_file, expected_source_node = expected_anchor_sources[anchor_id]
        source_file = _text(anchor.get("source_file"), f"anchors[{index}].source_file")
        source_node = _text(anchor.get("source_node"), f"anchors[{index}].source_node")
        if source_file != expected_source_file or source_node != expected_source_node:
            raise AvatarAnatomyPackageError(f"anchor source binding mismatch: {anchor_id}")
        if anchor.get("source_bound") is not True or anchor.get("authored") is not False:
            raise AvatarAnatomyPackageError(f"anchor must remain source-bound and unauthored: {anchor_id}")
        transform = _finite_matrix(anchor.get("transform"), f"anchors[{index}].transform")
        if transform != normalization["per_source_transform"][source_file]:
            raise AvatarAnatomyPackageError(f"anchor transform is not the exact source normalization: {anchor_id}")
        anchors.append(
            {
                "anchor_id": anchor_id,
                "source_file": source_file,
                "source_node": source_node,
                "source_bound": True,
                "authored": False,
                "transform": transform,
            }
        )
    blockers = [
        f"missing_source_anchor:{item}"
        for item in sorted(unavailable_anchor_ids | (required_anchor_ids - seen_anchors))
    ]
    bindings = _list(contract.get("external_outlet_bindings"), "contract.external_outlet_bindings")
    expected_routes: dict[str, dict[str, Any]] = {}
    for raw in bindings:
        binding = _mapping(raw, "contract outlet binding")
        route_id = _safe_id(binding.get("route"), "contract route")
        expected_routes[route_id] = {
            "external_endpoint_anchor_id": _safe_id(binding.get("anchor"), "contract outlet anchor"),
            "module_terminal": _safe_id(binding.get("module_terminal"), "contract module terminal"),
            "exclusive": binding.get("exclusive") is True,
        }
    routes: list[dict[str, Any]] = []
    seen_routes: set[str] = set()
    seen_endpoints: set[str] = set()
    route_for_anatomy_id: dict[str, str] = {}
    for index, raw in enumerate(_list(raw_routes, "routes")):
        route = _mapping(raw, f"routes[{index}]")
        route_id = _safe_id(route.get("route_id"), f"routes[{index}].route_id")
        if route_id in seen_routes or route_id not in expected_routes:
            raise AvatarAnatomyPackageError(f"unexpected or duplicate route: {route_id}")
        seen_routes.add(route_id)
        endpoint = _safe_id(
            route.get("external_endpoint_anchor_id"),
            f"routes[{index}].external_endpoint_anchor_id",
        )
        if endpoint in seen_endpoints:
            blockers.append(f"shared_external_endpoint:{endpoint}")
        seen_endpoints.add(endpoint)
        ordered = [
            _safe_id(item, f"routes[{index}].ordered_anatomy_ids")
            for item in _list(route.get("ordered_anatomy_ids"), f"routes[{index}].ordered_anatomy_ids")
        ]
        expected = expected_routes[route_id]
        if endpoint != expected["external_endpoint_anchor_id"]:
            blockers.append(f"route_endpoint_mismatch:{route_id}")
        if endpoint not in seen_anchors:
            blockers.append(f"route_endpoint_anchor_missing:{route_id}")
        if route.get("exclusive") is not True or not expected["exclusive"]:
            blockers.append(f"route_not_exclusive:{route_id}")
        if not ordered or len(set(ordered)) != len(ordered):
            blockers.append(f"route_nodes_empty_or_duplicate:{route_id}")
        for anatomy_id in ordered:
            if anatomy_id not in inventory or anatomy_id not in mapped_ids:
                blockers.append(f"route_node_not_mapped:{route_id}:{anatomy_id}")
                continue
            expected_system = ROUTE_SYSTEMS.get(route_id)
            if expected_system is None or inventory[anatomy_id] != expected_system:
                blockers.append(f"route_system_mismatch:{route_id}:{anatomy_id}")
            prior_route = route_for_anatomy_id.get(anatomy_id)
            if prior_route is not None and prior_route != route_id:
                blockers.append(
                    f"shared_route_node:{anatomy_id}:{prior_route}:{route_id}"
                )
            else:
                route_for_anatomy_id[anatomy_id] = route_id
        if expected["module_terminal"] not in ordered:
            blockers.append(f"route_terminal_missing:{route_id}")
        if route_id == "reproductive":
            relationships = _mapping(
                contract.get("spatial_relationships"),
                "contract.spatial_relationships",
            )
            vaginal_route = [
                _safe_id(item, "contract vaginal route")
                for item in _list(relationships.get("vaginal_route"), "contract vaginal_route")
            ]
            expected_order = [
                item for item in vaginal_route if item != expected["external_endpoint_anchor_id"]
            ]
            if ordered != expected_order:
                blockers.append("route_order_mismatch:reproductive")
        routes.append(
            {
                "route_id": route_id,
                "ordered_anatomy_ids": ordered,
                "external_endpoint_anchor_id": endpoint,
                "exclusive": route.get("exclusive"),
            }
        )
    for missing_route in sorted(set(expected_routes) - seen_routes):
        blockers.append(f"missing_route:{missing_route}")
    return (
        sorted(anchors, key=lambda item: item["anchor_id"]),
        sorted(routes, key=lambda item: item["route_id"]),
        blockers,
    )


def _validate_separation_truth(
    separation: Mapping[str, Any],
    truth: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[str]:
    interface = _mapping(contract.get("attachment_interface"), "contract.attachment_interface")
    expected_writes = _list(interface.get("forbidden_carrier_writes"), "contract forbidden writes")
    blockers: list[str] = []
    expected_separation = {
        "separate_artifact": True,
        "default_hidden": True,
        "carrier_dependency_mode": "READ_ONLY_TRANSFORM_FOLLOWING_ONLY",
        "module_local_armature_or_deformer": True,
        "contains_hair": False,
        "contains_clothing": False,
    }
    allowed_separation_fields = set(expected_separation) | {
        "forbidden_carrier_writes",
        "carrier_write_operations",
    }
    if set(separation) != allowed_separation_fields:
        raise AvatarAnatomyPackageError("separation fields must exactly match the preflight schema")
    for key, expected in expected_separation.items():
        actual = separation.get(key)
        if (
            (isinstance(expected, bool) and actual is not expected)
            or (not isinstance(expected, bool) and actual != expected)
        ):
            blockers.append(f"separation_invariant_failed:{key}")
    if separation.get("forbidden_carrier_writes") != expected_writes:
        blockers.append("separation_invariant_failed:forbidden_carrier_writes")
    if separation.get("carrier_write_operations") != []:
        blockers.append("separation_invariant_failed:carrier_write_operations")
    expected_truth = {
        "external_anatomy_complete": False,
        "internal_anatomy_complete": False,
        "function_implemented": False,
        "owner_approved": False,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "geometry_proves_biological_function": False,
    }
    for key in ADDITIONAL_TRUTH_NONCLAIMS:
        expected_truth[key] = False
    contract_truth = _mapping(contract.get("truth_limits"), "contract.truth_limits")
    for key, expected in contract_truth.items():
        if expected is False:
            expected_truth[key] = False
    if set(truth) != set(expected_truth):
        raise AvatarAnatomyPackageError("truth fields must exactly match the preflight schema")
    for key, expected in expected_truth.items():
        if truth.get(key) is not expected:
            blockers.append(f"truth_invariant_failed:{key}")
    return blockers


def evaluate_avatar_anatomy_package_preflight(
    project_root: Path | str,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one immutable anatomy-package request without writing any file."""

    root = _validated_project_root(project_root)
    request = _mapping(request, "request")
    if request.get("schema") != REQUEST_SCHEMA or request.get("schema_version") != 1:
        raise AvatarAnatomyPackageError("unsupported anatomy package request schema")
    required_request_fields = {
        "schema",
        "schema_version",
        "status",
        "package_id",
        "candidate_id",
        "subject_id",
        "maturity_status",
        "anatomy_profile_id",
        "contract",
        "source_package",
        "carrier",
        "normalization",
        "components",
        "anchors",
        "routes",
        "separation",
        "truth",
    }
    if set(request) != required_request_fields:
        raise AvatarAnatomyPackageError("request fields must exactly match the version-1 schema")
    if request.get("status") != "PREFLIGHT_REQUESTED":
        raise AvatarAnatomyPackageError("request.status must be PREFLIGHT_REQUESTED")
    package_id = _safe_id(request.get("package_id"), "package_id")
    candidate_id = _safe_id(request.get("candidate_id"), "candidate_id")
    subject_id = _safe_id(request.get("subject_id"), "subject_id")
    anatomy_profile_id = _safe_id(request.get("anatomy_profile_id"), "anatomy_profile_id")
    if request.get("maturity_status") != "confirmed_adult":
        raise AvatarAnatomyPackageError("maturity_status must be confirmed_adult")

    ledger = _EvidenceLedger(root)
    contract, contract_path, contract_sha, inventory = _validate_contract(
        root,
        ledger,
        _mapping(request.get("contract"), "contract"),
    )
    anatomy_profile = SUPPORTED_ANATOMY_PROFILES.get(anatomy_profile_id)
    if (
        anatomy_profile is None
        or anatomy_profile.get("contract_id") != contract.get("contract_id")
    ):
        raise AvatarAnatomyPackageError(
            "anatomy_profile_id is not bound to the selected canonical contract"
        )
    source_package_binding = _mapping(request.get("source_package"), "source_package")
    source_manifest, source_manifest_path, source_files = _validate_source_manifest(
        root,
        ledger,
        source_package_binding,
    )
    role_map, role_map_path, source_roles, role_missing, anchor_references = (
        _validate_source_role_map(
            root,
            ledger,
            source_package_binding,
            source_manifest_path=source_manifest_path,
            source_manifest_sha256=sha256_file(source_manifest_path),
            contract_path=contract_path,
            contract_sha256=contract_sha,
            inventory=inventory,
            source_files=source_files,
        )
    )
    normalization = _validate_normalization(
        _mapping(request.get("normalization"), "normalization"),
        source_files,
        role_map,
    )
    carrier, carrier_blockers = _validate_carrier(
        root,
        ledger,
        _mapping(request.get("carrier"), "carrier"),
        candidate_id,
    )
    components, missing, component_blockers = _validate_components(
        request.get("components"),
        inventory,
        source_roles,
        source_files,
        contract,
    )
    anchors, routes, route_blockers = _validate_anchors_routes(
        request.get("anchors"),
        request.get("routes"),
        contract,
        inventory,
        {item["anatomy_id"] for item in components},
        source_files,
        normalization,
        anchor_references,
    )
    invariant_blockers = _validate_separation_truth(
        _mapping(request.get("separation"), "separation"),
        _mapping(request.get("truth"), "truth"),
        contract,
    )

    missing = sorted(set(missing) | set(role_missing))
    blockers = sorted(
        set(
            [f"missing_required_structure:{item}" for item in missing]
            + carrier_blockers
            + component_blockers
            + route_blockers
            + invariant_blockers
        )
    )
    noncarrier_blockers = [
        item
        for item in blockers
        if not item.startswith("carrier_")
    ]
    if missing or noncarrier_blockers:
        status = PREFLIGHT_BLOCKED_MISSING_STRUCTURES
    elif carrier_blockers:
        status = PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED
    else:
        status = READY_FOR_PRIVATE_INACTIVE_AUTHORING
    source_intake_status = (
        SOURCE_INTAKE_VALIDATED_COMPLETE if not missing else SOURCE_INTAKE_VALIDATED_INCOMPLETE
    )
    before_snapshot_sha, after_snapshot_sha = ledger.verify_unchanged()

    source_collection = _mapping(source_manifest.get("source_collection"), "source collection")
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "schema_version": 1,
        "package_id": package_id,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "maturity_status": "confirmed_adult",
        "anatomy_profile_id": anatomy_profile_id,
        "scope": {
            "region": anatomy_profile["region"],
            "whole_body_complete": anatomy_profile["whole_body_complete"],
            "external_anatomy_complete": anatomy_profile["external_anatomy_complete"],
        },
        "status": status,
        "source_intake_status": source_intake_status,
        "preflight_performed": True,
        "build_performed": False,
        "blender_invoked": False,
        "contract": {
            "path": _project_relative(contract_path, root),
            "bytes": _file_size(contract_path),
            "sha256": contract_sha,
            "contract_id": contract["contract_id"],
        },
        "source_package": {
            "authority_id": source_package_binding["authority_id"],
            "authority_record_sha256": canonical_sha256(
                SUPPORTED_SOURCE_PACKAGES[source_package_binding["authority_id"]]
            ),
            "manifest_path": _project_relative(source_manifest_path, root),
            "manifest_bytes": _file_size(source_manifest_path),
            "manifest_sha256": sha256_file(source_manifest_path),
            "role_map_path": _project_relative(role_map_path, root),
            "role_map_bytes": _file_size(role_map_path),
            "role_map_sha256": sha256_file(role_map_path),
            "role_map_id": role_map["role_map_id"],
            "mapped_role_count": len(source_roles),
            "contract_role_count": len(inventory),
            "missing_contract_role_count": len(role_missing),
            "null_anchor_reference_count": sum(
                value is None for value in anchor_references.values()
            ),
            "license": source_collection["license"],
            "license_url": source_collection["license_url"],
            "attribution": source_collection["attribution"],
            "files": [
                {
                    "path": key,
                    "bytes": source_files[key]["bytes"],
                    "sha256": source_files[key]["sha256"],
                    "url": source_files[key]["url"],
                    "mesh_count": source_files[key]["mesh_count"],
                }
                for key in sorted(source_files)
            ],
        },
        "normalization": normalization,
        "carrier": carrier,
        "contract_inventory": [
            {
                "anatomy_id": anatomy_id,
                "system": inventory[anatomy_id],
                "mapped": anatomy_id not in missing,
            }
            for anatomy_id in sorted(inventory)
        ],
        "source_roles": [source_roles[key] for key in sorted(source_roles)],
        "components": components,
        "anchors": anchors,
        "routes": routes,
        "required_structure_count": len(inventory),
        "mapped_structure_count": len(components),
        "missing_required_structures": missing,
        "blockers": blockers,
        "read_only_evidence": {
            "source_carrier_hash_before": carrier["source_hash_before"],
            "source_carrier_hash_after": carrier["source_hash_after"],
            "source_carrier_equal": carrier["source_hash_before"] == carrier["source_hash_after"],
            "artifact_snapshot_sha256_before": before_snapshot_sha,
            "artifact_snapshot_sha256_after": after_snapshot_sha,
            "artifacts_unchanged": before_snapshot_sha == after_snapshot_sha,
        },
        "separation": dict(_mapping(request.get("separation"), "separation")),
        "truth": dict(_mapping(request.get("truth"), "truth")),
        "authoring_authority": {
            "readiness_only_not_execution_authority": True,
            "separate_versioned_authorization_required": True,
            "private_inactive_authoring_allowed": False,
            "blender_execution_allowed": False,
            "carrier_mutation_allowed": False,
            "function_claim_allowed": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        },
    }
    report["preflight_receipt_sha256"] = canonical_sha256(report)
    return report


def load_preflight_request(project_root: Path | str, request_path: str) -> dict[str, Any]:
    """Load a strict, safe project-relative request without changing any artifact."""

    root = _validated_project_root(project_root)
    path = _project_file(root, request_path, "request_path")
    return _parse_json_object(_read_bytes(path), "preflight request")


__all__ = [
    "AUTHORED_PRIVATE_INACTIVE_PENDING_GEOMETRY_REVIEW",
    "AvatarAnatomyPackageError",
    "GEOMETRY_REVIEW_PASSED_PENDING_OWNER_REVIEW",
    "HRA_SOURCE_ROLE_MAP",
    "OWNER_ACCEPTED_PRIVATE_INACTIVE",
    "PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED",
    "PREFLIGHT_BLOCKED_MISSING_STRUCTURES",
    "READY_FOR_PRIVATE_INACTIVE_AUTHORING",
    "REPORT_SCHEMA",
    "REQUEST_SCHEMA",
    "SOURCE_INTAKE_VALIDATED_COMPLETE",
    "SOURCE_INTAKE_VALIDATED_INCOMPLETE",
    "STATUS_LADDER",
    "SUPPORTED_ANATOMY_PROFILES",
    "SUPPORTED_CARRIER_AUTHORITIES",
    "SUPPORTED_SOURCE_PACKAGES",
    "canonical_json_bytes",
    "canonical_sha256",
    "evaluate_avatar_anatomy_package_preflight",
    "load_preflight_request",
    "read_glb2",
    "sha256_file",
]
