"""Fail-closed static trust boundary for TemporaryAI Creator quality V3.

V3 is additive.  It does not import or mutate the rejected V2 implementation.
It consumes only a parent-issued authority root whose exact SHA-256 is supplied
by the parent launcher, then derives an inert quality record from exact request,
registry, typed evidence, and (for experts) six case receipts.  This module
never calls a model and never creates a body, voice, avatar, activation,
assignment, publication, or runtime registration.
"""

from __future__ import annotations

import copy
import contextlib
import datetime as dt
import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 3
EXACT_QWEN_MODEL = "qwen3.5:9b"
EXACT_QWEN_DIGEST = "6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7"
PRIVATE_STATUS = "PRIVATE_INACTIVE_UNASSIGNED_STATIC_ONLY"
READY_STATUS = "V3_STATIC_EVIDENCE_READY_PRIVATE_INACTIVE_UNASSIGNED"

ROOT_KIND = "temporary_ai_parent_authority_root_v3"
REQUEST_KIND = "temporary_ai_parent_request_v3"
REGISTRY_KIND = "temporary_ai_parent_evidence_registry_v3"
SOURCE_RECEIPT_KIND = "temporary_ai_source_evidence_receipt_v3"
MATURITY_RECEIPT_KIND = "temporary_ai_maturity_evidence_receipt_v3"
EXPERT_CASE_KIND = "temporary_ai_expert_case_receipt_v3"
QUALITY_KIND = "temporary_ai_creator_quality_record_v3"
SOURCE_PACK_KIND = "temporary_ai_sealed_source_pack_v3"
EVALUATION_KIND = "temporary_ai_parent_expert_evaluation_manifest_v3"
RESPONSE_KIND = "temporary_ai_parent_model_response_receipt_v3"
EVALUATION_ROOT_KIND = "temporary_ai_parent_evaluation_authority_root_v3"
CORRECTION_KIND = "temporary_ai_parent_owner_correction_receipt_v3"
HEAD_KIND = "temporary_ai_quality_head_v3"

AI_TYPES = frozenset({"canon_reconstruction_temp_ai", "expert_temp_ai"})
VARIANT_KINDS = frozenset({"fictional", "historical", "expert"})
MATURITY_VALUES = frozenset({"confirmed_adult", "non_adult", "unresolved"})
MATURITY_AUTHORITIES = frozenset({
    "canonical_source_classification",
    "exact_subject_owner_classification",
    "exact_subject_owner_correction",
})
CASE_KINDS = (
    "domain_knowledge",
    "applied_reasoning",
    "source_grounding",
    "ignorance_boundary",
    "uncertainty_calibration",
    "correction_response",
)
SOURCE_PAIR_MATRIX = frozenset({
    ("primary_canon", "primary_or_official"),
    ("primary_historical", "primary_or_official"),
    ("official_domain_source", "primary_or_official"),
    ("authoritative_secondary", "authoritative_secondary"),
})

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,79}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
REPARSE_ATTRIBUTE = 0x400
_AUTHORITY_CAPABILITY = object()
_EVALUATION_AUTHORITY_CAPABILITY = object()


class QualityV3Error(ValueError):
    """A V3 trust or evidence boundary failed closed."""


def canonical_json_bytes(value: Any) -> bytes:
    _reject_non_finite(value)
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _reject_non_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise QualityV3Error(f"non-finite number at {path}")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise QualityV3Error(f"non-string object key at {path}")
            _reject_non_finite(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_non_finite(item, f"{path}[{index}]")


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise QualityV3Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode_canonical_json(raw: bytes, *, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> Any:
        raise QualityV3Error(f"{label}: non-standard JSON constant {value}")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object,
                           parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualityV3Error(f"{label}: strict UTF-8 JSON required") from exc
    if not isinstance(value, dict):
        raise QualityV3Error(f"{label}: one JSON object required")
    if raw != canonical_json_bytes(value):
        raise QualityV3Error(f"{label}: canonical JSON bytes required")
    return value


def _exact_keys(value: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    expected_set = set(expected)
    observed = set(value)
    if observed != expected_set:
        missing = sorted(expected_set - observed)
        extra = sorted(observed - expected_set)
        raise QualityV3Error(f"{label}: exact schema mismatch missing={missing} extra={extra}")


def _text(value: Any, label: str, *, minimum: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum or CONTROL_RE.search(value):
        raise QualityV3Error(f"{label}: nonempty control-free text required")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or ID_RE.fullmatch(value) is None:
        raise QualityV3Error(f"{label}: canonical identifier required")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise QualityV3Error(f"{label}: lowercase SHA-256 required")
    return value


def _utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        raise QualityV3Error(f"{label}: second-precision UTC Z timestamp required")
    try:
        return dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise QualityV3Error(f"{label}: invalid UTC timestamp") from exc


def _strict_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise QualityV3Error(f"{label}: integer >= {minimum} required")
    return value


def _unique_text_list(value: Any, label: str, *, minimum: int = 1) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise QualityV3Error(f"{label}: list with at least {minimum} values required")
    rows = [_text(item, f"{label}[]") for item in value]
    normalized = [" ".join(item.casefold().split()) for item in rows]
    if len(set(normalized)) != len(normalized):
        raise QualityV3Error(f"{label}: duplicate normalized values forbidden")
    return rows


def _canonical_relative(value: Any, label: str) -> str:
    text = _text(value, label)
    if "\\" in text or ":" in text:
        raise QualityV3Error(f"{label}: canonical POSIX relative path required")
    path = Path(text)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise QualityV3Error(f"{label}: safe project-relative path required")
    return text


def _is_reparse(st: os.stat_result) -> bool:
    return bool(getattr(st, "st_file_attributes", 0) & REPARSE_ATTRIBUTE)


def _identity(st: os.stat_result) -> tuple[int, int, int, int]:
    # Windows metadata timestamps can be updated asynchronously by filesystem
    # services even while the same file object is held. Stable object identity,
    # exact size, single-link status, and the parent-owned content SHA are the
    # deterministic trust tuple; SHA verification detects same-size mutation.
    return (int(st.st_dev), int(st.st_ino), int(st.st_size), int(st.st_nlink))


def _directory_identity(st: os.stat_result) -> tuple[int, int, int]:
    # Directory size legitimately changes when the protected operation creates
    # a child. Object identity and link count must remain stable.
    return (int(st.st_dev), int(st.st_ino), int(st.st_nlink))


def _validated_real_root(root: Path) -> Path:
    """Return an absolute authority root only when no path component is linked.

    Calling ``resolve()`` first would erase the evidence that the supplied root
    itself was a symlink or Windows junction.  Walk the absolute spelling with
    ``lstat`` before any resolution and then require the resolved spelling to
    be identical.  This also rejects a linked ancestor rather than trusting a
    root reached through an alias.
    """
    absolute = Path(os.path.abspath(os.fspath(root)))
    if not absolute.is_absolute() or not absolute.anchor:
        raise QualityV3Error("authority root must be absolute")
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            st = os.lstat(current)
        except FileNotFoundError as exc:
            raise QualityV3Error("authority root component is missing") from exc
        if _is_reparse(st) or stat.S_ISLNK(st.st_mode):
            raise QualityV3Error("authority root or ancestor is a reparse/symlink")
    final = os.lstat(absolute)
    if not stat.S_ISDIR(final.st_mode):
        raise QualityV3Error("authority root must be a real directory")
    resolved = absolute.resolve(strict=True)
    if os.path.normcase(str(resolved)) != os.path.normcase(str(absolute)):
        raise QualityV3Error("authority root resolved through an alias")
    return absolute


def _safe_chain(root: Path, relative: str, *, final_may_be_missing: bool = False) -> Path:
    root = _validated_real_root(root)
    root_st = os.lstat(root)
    if _is_reparse(root_st) or stat.S_ISLNK(root_st.st_mode) or not stat.S_ISDIR(root_st.st_mode):
        raise QualityV3Error("authority root must be a real directory, not a reparse point")
    current = root
    parts = Path(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        is_final = index == len(parts) - 1
        try:
            st = os.lstat(current)
        except FileNotFoundError:
            if final_may_be_missing and is_final:
                return current
            raise QualityV3Error(f"safe path component missing: {relative}")
        if _is_reparse(st) or stat.S_ISLNK(st.st_mode):
            raise QualityV3Error(f"reparse/symlink path forbidden: {relative}")
        if not is_final and not stat.S_ISDIR(st.st_mode):
            raise QualityV3Error(f"non-directory path component: {relative}")
    resolved = current.resolve(strict=not final_may_be_missing)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise QualityV3Error(f"resolved path escaped authority root: {relative}") from exc
    return current


@contextlib.contextmanager
def _hold_parent_directories(root: Path, relative: str):
    """Hold every parent directory open so it cannot be swapped mid-operation.

    On Windows, directory handles omit FILE_SHARE_DELETE/WRITE and use
    FILE_FLAG_OPEN_REPARSE_POINT. On POSIX, O_DIRECTORY|O_NOFOLLOW descriptors
    are retained. Identities are checked again before release.
    """
    root = _validated_real_root(root)
    parent_parts = Path(relative).parts[:-1]
    paths = [root]
    current = root
    for part in parent_parts:
        current = current / part
        paths.append(current)
    snapshots: list[tuple[Path, tuple[int, int, int]]] = []
    handles: list[Any] = []
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE]
        create_file.restype = wintypes.HANDLE
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        invalid = ctypes.c_void_p(-1).value
        OPEN_EXISTING = 3
        FILE_SHARE_READ = 1
        FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
        FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
        try:
            for path in paths:
                st = os.lstat(path)
                if _is_reparse(st) or stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                    raise QualityV3Error("parent directory became a reparse/non-directory")
                snapshots.append((path, _directory_identity(st)))
                handle = create_file(
                    str(path), 0, FILE_SHARE_READ, None, OPEN_EXISTING,
                    FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
                    None,
                )
                if handle == invalid:
                    raise QualityV3Error(
                        f"could not lock parent directory (winerror={ctypes.get_last_error()})"
                    )
                handles.append(handle)
            yield
            for path, identity in snapshots:
                st = os.lstat(path)
                if _directory_identity(st) != identity or _is_reparse(st):
                    raise QualityV3Error("parent directory identity changed during operation")
        finally:
            for handle in reversed(handles):
                close_handle(handle)
    else:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            for path in paths:
                st = os.lstat(path)
                if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                    raise QualityV3Error("parent directory became a link/non-directory")
                snapshots.append((path, _directory_identity(st)))
                handles.append(os.open(path, flags))
            yield
            for path, identity in snapshots:
                if _directory_identity(os.lstat(path)) != identity:
                    raise QualityV3Error("parent directory identity changed during operation")
        finally:
            for handle in reversed(handles):
                os.close(handle)


def stable_read(root: Path, relative: str, *, expected_sha256: str | None = None,
                require_canonical_json: bool = False) -> bytes:
    """Read one non-linked file while verifying before/descriptor/after identity.

    Every component is rejected when it is a symlink or Windows reparse point.
    The final file must have one hardlink. O_NOFOLLOW is used where available;
    descriptor identity and path identity must remain equal before and after.
    """
    relative = _canonical_relative(relative, "stable_read.relative")
    path = _safe_chain(root, relative)
    with _hold_parent_directories(root, relative):
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or _is_reparse(before) or before.st_nlink != 1:
            raise QualityV3Error(f"stable_read requires one-link regular file: {relative}")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            raise QualityV3Error(f"stable open failed: {relative}") from exc
        try:
            opened = os.fstat(fd)
            if _identity(opened) != _identity(before):
                raise QualityV3Error(f"file identity changed before stable read: {relative}")
            chunks: list[bytes] = []
            while True:
                block = os.read(fd, 1024 * 1024)
                if not block:
                    break
                chunks.append(block)
            after_fd = os.fstat(fd)
            if _identity(after_fd) != _identity(opened):
                raise QualityV3Error(f"file changed during stable read: {relative}")
        finally:
            os.close(fd)
        after_path = os.lstat(path)
        if _identity(after_path) != _identity(before) or _is_reparse(after_path):
            raise QualityV3Error(f"file identity changed after stable read: {relative}")
    raw = b"".join(chunks)
    if expected_sha256 is not None and sha256_bytes(raw) != _sha(expected_sha256, "expected_sha256"):
        raise QualityV3Error(f"stable file SHA-256 mismatch: {relative}")
    if require_canonical_json:
        _decode_canonical_json(raw, label=relative)
    return raw


def stable_load_json(root: Path, relative: str, *, expected_sha256: str | None = None) -> dict[str, Any]:
    raw = stable_read(root, relative, expected_sha256=expected_sha256,
                      require_canonical_json=True)
    return _decode_canonical_json(raw, label=relative)


def private_lifecycle() -> dict[str, Any]:
    return {
        "status": PRIVATE_STATUS,
        "activation_allowed": False,
        "assignment_allowed": False,
        "publication_allowed": False,
        "runtime_registration_allowed": False,
        "body_work_allowed": False,
        "voice_work_allowed": False,
        "model_execution_allowed": False,
        "gpu_execution_allowed": False,
        "blender_execution_allowed": False,
        "browser_execution_allowed": False,
    }


LIFECYCLE_KEYS = tuple(private_lifecycle())
ROOT_KEYS = (
    "schema_version", "record_kind", "authority_id", "owner_id",
    "created_at_utc", "requests", "lifecycle",
)
ROOT_REQUEST_KEYS = (
    "request_id", "request_path", "request_sha256", "registry_path",
    "registry_sha256", "output_directory", "head_directory",
)
REQUEST_KEYS = (
    "schema_version", "record_kind", "request_id", "authority_id", "owner_id",
    "candidate_id", "display_name", "ai_type", "variant_kind", "path_kind",
    "canonical_identity", "source_continuity", "source_version",
    "source_timepoint", "branch_point", "expert_domain",
    "requested_maturity_status", "source_pack_evidence_ids",
    "created_at_utc", "lifecycle",
)
REGISTRY_KEYS = (
    "schema_version", "record_kind", "registry_id", "request_id",
    "request_sha256", "candidate_id", "created_at_utc", "evidence_receipts",
    "expert_case_receipts", "source_pack_allowlist", "lifecycle",
)
REGISTRY_EVIDENCE_KEYS = ("evidence_id", "evidence_kind", "receipt_path", "receipt_sha256")
REGISTRY_CASE_KEYS = ("case_id", "receipt_path", "receipt_sha256")
ALLOWLIST_KEYS = ("evidence_id", "content_path", "content_sha256")
SOURCE_KEYS = (
    "schema_version", "record_kind", "evidence_id", "request_id", "candidate_id",
    "canonical_identity", "source_continuity", "source_version",
    "source_timepoint", "expert_domain", "source_class", "authority_tier",
    "content_path", "content_sha256", "content_size_bytes", "verified_excerpt",
    "verified_excerpt_sha256", "supports_claim_ids", "reviewed_by_owner_id",
    "reviewed_at_utc", "semantic_relevance_confirmed",
)
MATURITY_KEYS = (
    "schema_version", "record_kind", "evidence_id", "request_id", "candidate_id",
    "display_name", "classification_id", "maturity_status", "authority_kind",
    "content_path", "content_sha256", "content_size_bytes", "verified_statement",
    "verified_statement_sha256", "reviewed_by_owner_id", "reviewed_at_utc",
    "appearance_observation_used", "model_guess_used", "body_observation_used",
    "voice_observation_used", "classification_is_body_or_activation_approval",
)
CASE_KEYS = (
    "schema_version", "record_kind", "case_id", "request_id", "candidate_id",
    "expert_domain", "kind", "prompt", "prompt_sha256", "source_evidence_ids",
    "required_response_anchors", "out_of_scope_trigger", "expected_correction",
    "reviewed_by_owner_id", "reviewed_at_utc",
)


@dataclass(frozen=True)
class ParentAuthorityV3:
    root: Path
    root_sha256: str
    authority_id: str
    owner_id: str
    trusted_now_utc: str
    root_record: Mapping[str, Any]
    _capability: object


def _require_parent_authority(authority: ParentAuthorityV3) -> None:
    if not isinstance(authority, ParentAuthorityV3) or authority._capability is not _AUTHORITY_CAPABILITY:
        raise QualityV3Error("a capability minted by open_parent_authority is required")


def open_parent_authority(root: Path, *, expected_root_sha256: str,
                          trusted_now_utc: str) -> ParentAuthorityV3:
    root = _validated_real_root(root)
    now = _utc(trusted_now_utc, "trusted_now_utc")
    raw = stable_read(root, "AUTHORITY_ROOT.json", expected_sha256=expected_root_sha256,
                      require_canonical_json=True)
    record = _decode_canonical_json(raw, label="AUTHORITY_ROOT.json")
    _exact_keys(record, ROOT_KEYS, "authority root")
    if record["schema_version"] != SCHEMA_VERSION or record["record_kind"] != ROOT_KIND:
        raise QualityV3Error("authority root kind/version mismatch")
    authority_id = _identifier(record["authority_id"], "authority_id")
    owner_id = _identifier(record["owner_id"], "owner_id")
    if _utc(record["created_at_utc"], "authority.created_at_utc") > now:
        raise QualityV3Error("authority root is future dated")
    _validate_lifecycle(record["lifecycle"], "authority.lifecycle")
    requests = record["requests"]
    if not isinstance(requests, list):
        raise QualityV3Error("authority requests must be a list")
    seen: set[str] = set()
    seen_outputs: set[str] = set()
    seen_heads: set[str] = set()
    for index, row in enumerate(requests):
        if not isinstance(row, Mapping):
            raise QualityV3Error("authority request index rows must be objects")
        _exact_keys(row, ROOT_REQUEST_KEYS, f"authority.requests[{index}]")
        request_id = _identifier(row["request_id"], "request_id")
        if request_id in seen:
            raise QualityV3Error("duplicate authority request_id")
        seen.add(request_id)
        _canonical_relative(row["request_path"], "request_path")
        _canonical_relative(row["registry_path"], "registry_path")
        output_directory = _canonical_relative(row["output_directory"], "output_directory")
        head_directory = _canonical_relative(row["head_directory"], "head_directory")
        if output_directory in seen_outputs or head_directory in seen_heads:
            raise QualityV3Error("authority requests must have unique output and head directories")
        if not head_directory.startswith(output_directory.rstrip("/") + "/"):
            raise QualityV3Error("authority head directory must be inside its output directory")
        seen_outputs.add(output_directory)
        seen_heads.add(head_directory)
        _sha(row["request_sha256"], "request_sha256")
        _sha(row["registry_sha256"], "registry_sha256")
    return ParentAuthorityV3(root, _sha(expected_root_sha256, "root_sha256"),
                             authority_id, owner_id, trusted_now_utc,
                             copy.deepcopy(record), _AUTHORITY_CAPABILITY)


def _validate_lifecycle(value: Any, label: str) -> None:
    if not isinstance(value, Mapping):
        raise QualityV3Error(f"{label}: object required")
    _exact_keys(value, LIFECYCLE_KEYS, label)
    if dict(value) != private_lifecycle():
        raise QualityV3Error(f"{label}: exact inert lifecycle required")


def _request_index(authority: ParentAuthorityV3, request_id: str) -> Mapping[str, Any]:
    _require_parent_authority(authority)
    matches = [row for row in authority.root_record["requests"]
               if row["request_id"] == request_id]
    if len(matches) != 1:
        raise QualityV3Error("request_id is not uniquely parent-authorized")
    return matches[0]


def _validate_request(record: Mapping[str, Any], authority: ParentAuthorityV3,
                      request_id: str) -> None:
    _exact_keys(record, REQUEST_KEYS, "parent request")
    if record["schema_version"] != SCHEMA_VERSION or record["record_kind"] != REQUEST_KIND:
        raise QualityV3Error("parent request kind/version mismatch")
    if record["request_id"] != request_id or record["authority_id"] != authority.authority_id:
        raise QualityV3Error("parent request authority/request mismatch")
    if record["owner_id"] != authority.owner_id:
        raise QualityV3Error("parent request owner mismatch")
    candidate = _identifier(record["candidate_id"], "candidate_id")
    _text(record["display_name"], "display_name")
    for field in ("canonical_identity", "source_continuity", "source_version",
                  "source_timepoint", "branch_point"):
        _text(record[field], field)
    ai_type = record["ai_type"]
    variant = record["variant_kind"]
    if ai_type not in AI_TYPES or variant not in VARIANT_KINDS:
        raise QualityV3Error("request AI/variant kind outside V3")
    expected_variant = "expert" if ai_type == "expert_temp_ai" else variant
    expected_path = "expert" if ai_type == "expert_temp_ai" else f"{variant}_variant"
    if variant != expected_variant or record["path_kind"] != expected_path:
        raise QualityV3Error("request variant/path contradiction")
    domain = record["expert_domain"]
    if ai_type == "expert_temp_ai":
        _text(domain, "expert_domain", minimum=8)
    elif domain != "":
        raise QualityV3Error("variant must not declare expert domain")
    if record["requested_maturity_status"] not in MATURITY_VALUES:
        raise QualityV3Error("invalid requested maturity status")
    _unique_text_list(record["source_pack_evidence_ids"], "source_pack_evidence_ids")
    if _utc(record["created_at_utc"], "request.created_at_utc") > _utc(authority.trusted_now_utc, "trusted_now"):
        raise QualityV3Error("parent request is future dated")
    _validate_lifecycle(record["lifecycle"], "request.lifecycle")
    if candidate != record["candidate_id"]:
        raise QualityV3Error("candidate ID normalization drift")


def _load_request_registry(authority: ParentAuthorityV3, request_id: str) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, Any]]:
    index = _request_index(authority, request_id)
    request = stable_load_json(authority.root, index["request_path"],
                               expected_sha256=index["request_sha256"])
    _validate_request(request, authority, request_id)
    registry = stable_load_json(authority.root, index["registry_path"],
                                expected_sha256=index["registry_sha256"])
    _validate_registry_shape(registry, request, index, authority)
    return request, registry, index


def _validate_registry_shape(registry: Mapping[str, Any], request: Mapping[str, Any],
                             index: Mapping[str, Any], authority: ParentAuthorityV3) -> None:
    _exact_keys(registry, REGISTRY_KEYS, "evidence registry")
    if registry["schema_version"] != SCHEMA_VERSION or registry["record_kind"] != REGISTRY_KIND:
        raise QualityV3Error("evidence registry kind/version mismatch")
    _identifier(registry["registry_id"], "registry_id")
    if registry["request_id"] != request["request_id"] or registry["candidate_id"] != request["candidate_id"]:
        raise QualityV3Error("registry request/candidate mismatch")
    if registry["request_sha256"] != index["request_sha256"]:
        raise QualityV3Error("registry request hash mismatch")
    if _utc(registry["created_at_utc"], "registry.created_at_utc") > _utc(authority.trusted_now_utc, "trusted_now"):
        raise QualityV3Error("registry is future dated")
    _validate_lifecycle(registry["lifecycle"], "registry.lifecycle")
    for field, keys in (("evidence_receipts", REGISTRY_EVIDENCE_KEYS),
                        ("expert_case_receipts", REGISTRY_CASE_KEYS),
                        ("source_pack_allowlist", ALLOWLIST_KEYS)):
        rows = registry[field]
        if not isinstance(rows, list):
            raise QualityV3Error(f"registry {field} must be a list")
        seen: set[str] = set()
        id_key = "case_id" if field == "expert_case_receipts" else "evidence_id"
        for i, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise QualityV3Error(f"registry {field}[{i}] must be object")
            _exact_keys(row, keys, f"registry.{field}[{i}]")
            item_id = _identifier(row[id_key], f"registry.{field}.{id_key}")
            if item_id in seen:
                raise QualityV3Error(f"duplicate registry {field} ID")
            seen.add(item_id)
            if "receipt_path" in row:
                _canonical_relative(row["receipt_path"], "receipt_path")
                _sha(row["receipt_sha256"], "receipt_sha256")
            if field == "source_pack_allowlist":
                _canonical_relative(row["content_path"], "allowlist.content_path")
                _sha(row["content_sha256"], "allowlist.content_sha256")


def _validate_source_receipt(receipt: Mapping[str, Any], request: Mapping[str, Any],
                             authority: ParentAuthorityV3) -> dict[str, Any]:
    _exact_keys(receipt, SOURCE_KEYS, "source receipt")
    if receipt["schema_version"] != SCHEMA_VERSION or receipt["record_kind"] != SOURCE_RECEIPT_KIND:
        raise QualityV3Error("source receipt kind/version mismatch")
    _identifier(receipt["evidence_id"], "source evidence_id")
    exact = ("request_id", "candidate_id", "canonical_identity", "source_continuity",
             "source_version", "source_timepoint", "expert_domain")
    for field in exact:
        if receipt[field] != request[field]:
            raise QualityV3Error(f"source receipt exact request mismatch: {field}")
    pair = (receipt["source_class"], receipt["authority_tier"])
    if pair not in SOURCE_PAIR_MATRIX:
        raise QualityV3Error("source class/authority pair is not approved")
    expected_primary = {
        "fictional": "primary_canon", "historical": "primary_historical"
    }.get(request["variant_kind"])
    if expected_primary and receipt["source_class"] != expected_primary:
        raise QualityV3Error("variant source class contradicts requested continuity kind")
    if request["ai_type"] == "expert_temp_ai" and receipt["source_class"] not in {
        "official_domain_source", "authoritative_secondary"
    }:
        raise QualityV3Error("expert source class outside declared domain lane")
    content_path = _canonical_relative(receipt["content_path"], "source.content_path")
    content_hash = _sha(receipt["content_sha256"], "source.content_sha256")
    raw = stable_read(authority.root, content_path, expected_sha256=content_hash)
    if _strict_int(receipt["content_size_bytes"], "source.content_size_bytes", minimum=1) != len(raw):
        raise QualityV3Error("source content size mismatch")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise QualityV3Error("source reviewed content must be exact UTF-8 text") from exc
    excerpt = _text(receipt["verified_excerpt"], "verified_excerpt", minimum=20)
    if receipt["verified_excerpt_sha256"] != sha256_text(excerpt):
        raise QualityV3Error("verified excerpt hash mismatch")
    if excerpt not in text:
        raise QualityV3Error("verified excerpt is absent from exact source content")
    required_relevance_tokens = [
        request["canonical_identity"], request["source_continuity"],
        request["source_timepoint"],
    ]
    if request["expert_domain"]:
        required_relevance_tokens.append(request["expert_domain"])
    excerpt_folded = excerpt.casefold()
    if any(token.casefold() not in excerpt_folded for token in required_relevance_tokens):
        raise QualityV3Error("verified excerpt lacks exact identity/continuity/timepoint/domain binding")
    claims = _unique_text_list(receipt["supports_claim_ids"], "supports_claim_ids")
    for claim in claims:
        _identifier(claim, "claim_id")
    if receipt["reviewed_by_owner_id"] != authority.owner_id:
        raise QualityV3Error("source semantic review is not parent-owner issued")
    if _utc(receipt["reviewed_at_utc"], "source.reviewed_at_utc") > _utc(authority.trusted_now_utc, "trusted_now"):
        raise QualityV3Error("source receipt is future dated")
    if receipt["semantic_relevance_confirmed"] is not True:
        raise QualityV3Error("source semantic relevance is not confirmed")
    return copy.deepcopy(dict(receipt))


def _validate_maturity_receipt(receipt: Mapping[str, Any], request: Mapping[str, Any],
                               authority: ParentAuthorityV3) -> dict[str, Any]:
    _exact_keys(receipt, MATURITY_KEYS, "maturity receipt")
    if receipt["schema_version"] != SCHEMA_VERSION or receipt["record_kind"] != MATURITY_RECEIPT_KIND:
        raise QualityV3Error("maturity receipt kind/version mismatch")
    _identifier(receipt["evidence_id"], "maturity evidence_id")
    if receipt["request_id"] != request["request_id"] or receipt["candidate_id"] != request["candidate_id"] or receipt["display_name"] != request["display_name"]:
        raise QualityV3Error("maturity exact subject mismatch")
    _identifier(receipt["classification_id"], "classification_id")
    if receipt["maturity_status"] != request["requested_maturity_status"] or receipt["maturity_status"] not in MATURITY_VALUES:
        raise QualityV3Error("maturity status contradicts parent request")
    if receipt["authority_kind"] not in MATURITY_AUTHORITIES:
        raise QualityV3Error("maturity authority kind not approved")
    raw = stable_read(authority.root,
                      _canonical_relative(receipt["content_path"], "maturity.content_path"),
                      expected_sha256=_sha(receipt["content_sha256"], "maturity.content_sha256"))
    if _strict_int(receipt["content_size_bytes"], "maturity.content_size_bytes", minimum=1) != len(raw):
        raise QualityV3Error("maturity content size mismatch")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise QualityV3Error("maturity evidence must be UTF-8 text") from exc
    statement = _text(receipt["verified_statement"], "verified_statement", minimum=30)
    if receipt["verified_statement_sha256"] != sha256_text(statement) or statement not in content:
        raise QualityV3Error("maturity verified statement/hash mismatch")
    required_tokens = (request["candidate_id"], request["display_name"],
                       request["requested_maturity_status"])
    folded = statement.casefold()
    if any(token.casefold() not in folded for token in required_tokens):
        raise QualityV3Error("maturity statement lacks exact subject/status tokens")
    if receipt["reviewed_by_owner_id"] != authority.owner_id:
        raise QualityV3Error("maturity review is not parent-owner issued")
    if _utc(receipt["reviewed_at_utc"], "maturity.reviewed_at_utc") > _utc(authority.trusted_now_utc, "trusted_now"):
        raise QualityV3Error("maturity receipt is future dated")
    for field in ("appearance_observation_used", "model_guess_used", "body_observation_used",
                  "voice_observation_used", "classification_is_body_or_activation_approval"):
        if receipt[field] is not False:
            raise QualityV3Error(f"maturity forbidden inference flag: {field}")
    return copy.deepcopy(dict(receipt))


def _validate_case_receipt(receipt: Mapping[str, Any], request: Mapping[str, Any],
                           source_ids: set[str], authority: ParentAuthorityV3) -> dict[str, Any]:
    _exact_keys(receipt, CASE_KEYS, "expert case receipt")
    if receipt["schema_version"] != SCHEMA_VERSION or receipt["record_kind"] != EXPERT_CASE_KIND:
        raise QualityV3Error("expert case receipt kind/version mismatch")
    _identifier(receipt["case_id"], "case_id")
    if receipt["request_id"] != request["request_id"] or receipt["candidate_id"] != request["candidate_id"] or receipt["expert_domain"] != request["expert_domain"]:
        raise QualityV3Error("expert case exact request/domain mismatch")
    if receipt["kind"] not in CASE_KINDS:
        raise QualityV3Error("expert case kind invalid")
    prompt = _text(receipt["prompt"], "expert prompt", minimum=30)
    if receipt["prompt_sha256"] != sha256_text(prompt):
        raise QualityV3Error("expert prompt hash mismatch")
    evidence = _unique_text_list(receipt["source_evidence_ids"], "case.source_evidence_ids", minimum=2)
    if any(item not in source_ids for item in evidence):
        raise QualityV3Error("expert case cites evidence outside registry")
    anchors = _unique_text_list(receipt["required_response_anchors"], "required_response_anchors", minimum=2)
    if any(len(" ".join(item.split())) < 6 for item in anchors):
        raise QualityV3Error("expert response anchor is too generic")
    if receipt["kind"] == "ignorance_boundary":
        _text(receipt["out_of_scope_trigger"], "out_of_scope_trigger", minimum=12)
    elif receipt["out_of_scope_trigger"] != "":
        raise QualityV3Error("out-of-scope trigger only allowed for ignorance case")
    if receipt["kind"] == "correction_response":
        _text(receipt["expected_correction"], "expected_correction", minimum=12)
    elif receipt["expected_correction"] != "":
        raise QualityV3Error("expected correction only allowed for correction case")
    if receipt["reviewed_by_owner_id"] != authority.owner_id:
        raise QualityV3Error("expert case is not parent-owner reviewed")
    if _utc(receipt["reviewed_at_utc"], "case.reviewed_at_utc") > _utc(authority.trusted_now_utc, "trusted_now"):
        raise QualityV3Error("expert case is future dated")
    return copy.deepcopy(dict(receipt))


@dataclass(frozen=True)
class PreparedQualityV3:
    request: Mapping[str, Any]
    registry: Mapping[str, Any]
    source_receipts: tuple[Mapping[str, Any], ...]
    maturity_receipt: Mapping[str, Any]
    expert_cases: tuple[Mapping[str, Any], ...]
    source_pack: Mapping[str, Any]
    quality_record: Mapping[str, Any]
    index: Mapping[str, Any]


def prepare_quality_v3(authority: ParentAuthorityV3, request_id: str) -> PreparedQualityV3:
    _require_parent_authority(authority)
    request_id = _identifier(request_id, "request_id")
    request, registry, index = _load_request_registry(authority, request_id)
    sources: list[dict[str, Any]] = []
    maturity: dict[str, Any] | None = None
    registry_ids: set[str] = set()
    for row in registry["evidence_receipts"]:
        receipt = stable_load_json(authority.root, row["receipt_path"], expected_sha256=row["receipt_sha256"])
        if receipt.get("evidence_id") != row["evidence_id"] or receipt.get("record_kind") != row["evidence_kind"]:
            raise QualityV3Error("registry evidence receipt identity/kind mismatch")
        evidence_id = row["evidence_id"]
        if evidence_id in registry_ids:
            raise QualityV3Error("duplicate registry evidence identity")
        registry_ids.add(evidence_id)
        if row["evidence_kind"] == SOURCE_RECEIPT_KIND:
            sources.append(_validate_source_receipt(receipt, request, authority))
        elif row["evidence_kind"] == MATURITY_RECEIPT_KIND:
            if maturity is not None:
                raise QualityV3Error("exactly one maturity receipt required")
            maturity = _validate_maturity_receipt(receipt, request, authority)
        else:
            raise QualityV3Error("unrecognized evidence receipt kind")
    if not sources or maturity is None:
        raise QualityV3Error("source evidence and one maturity receipt are required")
    source_ids = {row["evidence_id"] for row in sources}
    if request["ai_type"] == "expert_temp_ai":
        classes = {row["source_class"] for row in sources}
        if not {"official_domain_source", "authoritative_secondary"}.issubset(classes):
            raise QualityV3Error("expert requires official and authoritative-secondary evidence")
    cases: list[dict[str, Any]] = []
    for row in registry["expert_case_receipts"]:
        receipt = stable_load_json(authority.root, row["receipt_path"], expected_sha256=row["receipt_sha256"])
        if receipt.get("case_id") != row["case_id"]:
            raise QualityV3Error("registry expert case ID mismatch")
        cases.append(_validate_case_receipt(receipt, request, source_ids, authority))
    if request["ai_type"] == "expert_temp_ai":
        if sorted(case["kind"] for case in cases) != sorted(CASE_KINDS):
            raise QualityV3Error("expert requires exactly one of each six case kinds")
        prompts = [case["prompt_sha256"] for case in cases]
        case_ids = [case["case_id"] for case in cases]
        anchors = [anchor.casefold() for case in cases for anchor in case["required_response_anchors"]]
        if len(set(prompts)) != 6 or len(set(case_ids)) != 6 or len(set(anchors)) != len(anchors):
            raise QualityV3Error("expert cases require six distinct prompts, IDs, and anchors")
        unique_case_evidence = [set(case["source_evidence_ids"]) for case in cases]
        if any(not evidence for evidence in unique_case_evidence):
            raise QualityV3Error("expert case evidence missing")
    elif cases:
        raise QualityV3Error("non-expert request must not contain expert cases")

    allowlist = registry["source_pack_allowlist"]
    allow_ids = [row["evidence_id"] for row in allowlist]
    if allow_ids != request["source_pack_evidence_ids"] or set(allow_ids) != source_ids:
        raise QualityV3Error("source-pack allowlist must exactly equal parent request and source receipts")
    by_id = {row["evidence_id"]: row for row in sources}
    for row in allowlist:
        source = by_id[row["evidence_id"]]
        if row["content_path"] != source["content_path"] or row["content_sha256"] != source["content_sha256"]:
            raise QualityV3Error("source-pack allowlist path/hash mismatch")
    source_pack = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": SOURCE_PACK_KIND,
        "request_id": request_id,
        "candidate_id": request["candidate_id"],
        "request_sha256": index["request_sha256"],
        "registry_sha256": index["registry_sha256"],
        "evidence": copy.deepcopy(allowlist),
        "lifecycle": private_lifecycle(),
    }
    quality = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": QUALITY_KIND,
        "revision": 1,
        "previous_revision_sha256": "",
        "request_id": request_id,
        "authority_root_sha256": authority.root_sha256,
        "request_sha256": index["request_sha256"],
        "registry_sha256": index["registry_sha256"],
        "candidate_id": request["candidate_id"],
        "display_name": request["display_name"],
        "ai_type": request["ai_type"],
        "variant_kind": request["variant_kind"],
        "path_kind": request["path_kind"],
        "canonical_identity": request["canonical_identity"],
        "source_continuity": request["source_continuity"],
        "source_version": request["source_version"],
        "source_timepoint": request["source_timepoint"],
        "branch_point": request["branch_point"],
        "expert_domain": request["expert_domain"],
        "maturity_status": maturity["maturity_status"],
        "maturity_receipt_sha256": canonical_sha256(maturity),
        "source_receipt_sha256s": [canonical_sha256(row) for row in sources],
        "expert_case_receipt_sha256s": [canonical_sha256(row) for row in cases],
        "source_pack_sha256": canonical_sha256(source_pack),
        "exact_future_evaluation_model": EXACT_QWEN_MODEL,
        "exact_future_evaluation_digest": EXACT_QWEN_DIGEST,
        "model_loaded_or_called": False,
        "quality_status": READY_STATUS,
        "created_at_utc": request["created_at_utc"],
        "lifecycle": private_lifecycle(),
    }
    return PreparedQualityV3(copy.deepcopy(request), copy.deepcopy(registry),
                             tuple(sources), maturity, tuple(cases),
                             source_pack, quality, copy.deepcopy(index))


EVALUATION_KEYS = (
    "schema_version", "record_kind", "evaluation_id", "request_id",
    "request_sha256", "registry_sha256", "quality_record_sha256", "model",
    "digest", "started_at_utc", "completed_at_utc", "responses", "lifecycle",
)
EVALUATION_RESPONSE_KEYS = ("sequence", "case_id", "response_path", "response_sha256")
RESPONSE_KEYS = (
    "schema_version", "record_kind", "evaluation_id", "request_id", "candidate_id",
    "case_id", "sequence", "prompt_sha256", "model", "digest", "raw_response_text",
    "raw_response_sha256", "started_at_utc", "completed_at_utc",
)

EVALUATION_ROOT_KEYS = (
    "schema_version", "record_kind", "authority_id", "owner_id",
    "created_at_utc", "evaluations", "lifecycle",
)
ROOT_EVALUATION_KEYS = (
    "evaluation_id", "request_id", "evaluation_path", "evaluation_sha256",
)


@dataclass(frozen=True)
class ParentEvaluationAuthorityV3:
    root: Path
    root_sha256: str
    authority_id: str
    owner_id: str
    trusted_now_utc: str
    root_record: Mapping[str, Any]
    _capability: object


def _require_evaluation_authority(authority: ParentEvaluationAuthorityV3) -> None:
    if (not isinstance(authority, ParentEvaluationAuthorityV3) or
            authority._capability is not _EVALUATION_AUTHORITY_CAPABILITY):
        raise QualityV3Error("a capability minted by open_parent_evaluation_authority is required")


def open_parent_evaluation_authority(root: Path, *, expected_root_sha256: str,
                                     trusted_now_utc: str) -> ParentEvaluationAuthorityV3:
    root = _validated_real_root(root)
    now = _utc(trusted_now_utc, "evaluation trusted_now_utc")
    raw = stable_read(root, "EVALUATION_AUTHORITY_ROOT.json",
                      expected_sha256=expected_root_sha256,
                      require_canonical_json=True)
    record = _decode_canonical_json(raw, label="EVALUATION_AUTHORITY_ROOT.json")
    _exact_keys(record, EVALUATION_ROOT_KEYS, "evaluation authority root")
    if record["schema_version"] != SCHEMA_VERSION or record["record_kind"] != EVALUATION_ROOT_KIND:
        raise QualityV3Error("evaluation authority root kind/version mismatch")
    authority_id = _identifier(record["authority_id"], "evaluation authority_id")
    owner_id = _identifier(record["owner_id"], "evaluation owner_id")
    if _utc(record["created_at_utc"], "evaluation authority created_at") > now:
        raise QualityV3Error("evaluation authority root is future dated")
    _validate_lifecycle(record["lifecycle"], "evaluation authority lifecycle")
    rows = record["evaluations"]
    if not isinstance(rows, list):
        raise QualityV3Error("evaluation authority index must be a list")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise QualityV3Error("evaluation authority row must be an object")
        _exact_keys(row, ROOT_EVALUATION_KEYS, f"evaluation authority row {index}")
        evaluation_id = _identifier(row["evaluation_id"], "evaluation_id")
        if evaluation_id in seen:
            raise QualityV3Error("duplicate evaluation authority ID")
        seen.add(evaluation_id)
        _identifier(row["request_id"], "evaluation request_id")
        _canonical_relative(row["evaluation_path"], "evaluation_path")
        _sha(row["evaluation_sha256"], "evaluation_sha256")
    return ParentEvaluationAuthorityV3(root, _sha(expected_root_sha256, "evaluation root hash"),
                                       authority_id, owner_id, trusted_now_utc,
                                       copy.deepcopy(record),
                                       _EVALUATION_AUTHORITY_CAPABILITY)


def evaluate_expert_battery_v3(prepared: PreparedQualityV3,
                               authority: ParentEvaluationAuthorityV3,
                               evaluation_id: str) -> dict[str, Any]:
    _require_evaluation_authority(authority)
    if prepared.request["ai_type"] != "expert_temp_ai" or len(prepared.expert_cases) != 6:
        raise QualityV3Error("expert V3 prepared record with six cases required")
    if (authority.authority_id != prepared.request["authority_id"] or
            authority.owner_id != prepared.request["owner_id"]):
        raise QualityV3Error("evaluation authority does not match creation parent authority")
    evaluation_id = _identifier(evaluation_id, "evaluation_id")
    index_rows = [row for row in authority.root_record["evaluations"]
                  if row["evaluation_id"] == evaluation_id]
    if len(index_rows) != 1 or index_rows[0]["request_id"] != prepared.request["request_id"]:
        raise QualityV3Error("evaluation is not uniquely parent-authorized for this request")
    evaluation_index = index_rows[0]
    manifest = stable_load_json(authority.root, evaluation_index["evaluation_path"],
                                expected_sha256=evaluation_index["evaluation_sha256"])
    _exact_keys(manifest, EVALUATION_KEYS, "evaluation manifest")
    if manifest["schema_version"] != SCHEMA_VERSION or manifest["record_kind"] != EVALUATION_KIND:
        raise QualityV3Error("evaluation manifest kind/version mismatch")
    if _identifier(manifest["evaluation_id"], "evaluation_id") != evaluation_id:
        raise QualityV3Error("evaluation manifest/index ID mismatch")
    exact = {
        "request_id": prepared.request["request_id"],
        "request_sha256": prepared.quality_record["request_sha256"],
        "registry_sha256": prepared.quality_record["registry_sha256"],
        "quality_record_sha256": canonical_sha256(prepared.quality_record),
        "model": EXACT_QWEN_MODEL,
        "digest": EXACT_QWEN_DIGEST,
    }
    for field, expected in exact.items():
        if manifest[field] != expected:
            raise QualityV3Error(f"evaluation exact binding mismatch: {field}")
    start = _utc(manifest["started_at_utc"], "evaluation.started_at_utc")
    end = _utc(manifest["completed_at_utc"], "evaluation.completed_at_utc")
    now = _utc(authority.trusted_now_utc, "trusted_now")
    if end < start or end > now:
        raise QualityV3Error("evaluation time interval invalid or future dated")
    _validate_lifecycle(manifest["lifecycle"], "evaluation.lifecycle")
    rows = manifest["responses"]
    if not isinstance(rows, list) or len(rows) != 6:
        raise QualityV3Error("evaluation requires exactly six response receipts")
    cases = {case["case_id"]: case for case in prepared.expert_cases}
    observed_case_ids: list[str] = []
    normalized_responses: list[str] = []
    response_hashes: list[str] = []
    for expected_sequence, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise QualityV3Error("evaluation response index rows must be objects")
        _exact_keys(row, EVALUATION_RESPONSE_KEYS, "evaluation response index")
        if _strict_int(row["sequence"], "response sequence", minimum=1) != expected_sequence:
            raise QualityV3Error("evaluation response sequence mismatch")
        case_id = _identifier(row["case_id"], "response case_id")
        if case_id not in cases:
            raise QualityV3Error("evaluation response case outside exact plan")
        response = stable_load_json(authority.root, row["response_path"],
                                    expected_sha256=row["response_sha256"])
        _exact_keys(response, RESPONSE_KEYS, "model response receipt")
        if response["schema_version"] != SCHEMA_VERSION or response["record_kind"] != RESPONSE_KIND:
            raise QualityV3Error("model response receipt kind/version mismatch")
        response_exact = {
            "evaluation_id": manifest["evaluation_id"],
            "request_id": prepared.request["request_id"],
            "candidate_id": prepared.request["candidate_id"],
            "case_id": case_id,
            "sequence": expected_sequence,
            "prompt_sha256": cases[case_id]["prompt_sha256"],
            "model": EXACT_QWEN_MODEL,
            "digest": EXACT_QWEN_DIGEST,
        }
        for field, expected in response_exact.items():
            if response[field] != expected or (field == "sequence" and isinstance(response[field], bool)):
                raise QualityV3Error(f"response exact binding mismatch: {field}")
        response_start = _utc(response["started_at_utc"], "response.started_at_utc")
        response_end = _utc(response["completed_at_utc"], "response.completed_at_utc")
        if response_end < response_start or response_start < start or response_end > end:
            raise QualityV3Error("response timing outside evaluation interval")
        text = _text(response["raw_response_text"], "raw_response_text", minimum=80)
        if response["raw_response_sha256"] != sha256_text(text):
            raise QualityV3Error("raw response text hash mismatch")
        normalized = " ".join(text.casefold().split())
        generic = {
            "hello.", "i don't know.", "evidence-bound response.",
            "this is a polished, generally sensible answer.",
        }
        if normalized in generic:
            raise QualityV3Error("generic expert response rejected")
        for anchor in cases[case_id]["required_response_anchors"]:
            if " ".join(anchor.casefold().split()) not in normalized:
                raise QualityV3Error(f"response missing parent-reviewed anchor: {case_id}")
        for evidence_id in cases[case_id]["source_evidence_ids"]:
            if f"source[{evidence_id}]" not in normalized:
                raise QualityV3Error(f"response missing exact evidence citation: {case_id}")
        kind = cases[case_id]["kind"]
        if kind == "ignorance_boundary" and "limit:" not in normalized:
            raise QualityV3Error("ignorance response lacks explicit LIMIT marker")
        if kind == "uncertainty_calibration" and "uncertainty:" not in normalized:
            raise QualityV3Error("uncertainty response lacks explicit UNCERTAINTY marker")
        if kind == "correction_response" and cases[case_id]["expected_correction"].casefold() not in normalized:
            raise QualityV3Error("correction response lacks exact reviewed correction")
        observed_case_ids.append(case_id)
        normalized_responses.append(normalized)
        response_hashes.append(response["raw_response_sha256"])
    if set(observed_case_ids) != set(cases) or len(set(observed_case_ids)) != 6:
        raise QualityV3Error("evaluation cases are not exact and distinct")
    if len(set(normalized_responses)) != 6 or len(set(response_hashes)) != 6:
        raise QualityV3Error("six distinct expert replies are required")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "temporary_ai_expert_evaluation_result_v3",
        "evaluation_id": manifest["evaluation_id"],
        "request_id": prepared.request["request_id"],
        "quality_record_sha256": canonical_sha256(prepared.quality_record),
        "model": EXACT_QWEN_MODEL,
        "digest": EXACT_QWEN_DIGEST,
        "passed": True,
        "case_count": 6,
        "response_sha256s": response_hashes,
        "activation_or_assignment_changed": False,
        "lifecycle": private_lifecycle(),
    }


QUALITY_KEYS = (
    "schema_version", "record_kind", "revision", "previous_revision_sha256",
    "request_id", "authority_root_sha256", "request_sha256", "registry_sha256",
    "candidate_id", "display_name", "ai_type", "variant_kind", "path_kind",
    "canonical_identity", "source_continuity", "source_version", "source_timepoint",
    "branch_point", "expert_domain", "maturity_status", "maturity_receipt_sha256",
    "source_receipt_sha256s", "expert_case_receipt_sha256s", "source_pack_sha256",
    "exact_future_evaluation_model", "exact_future_evaluation_digest",
    "model_loaded_or_called", "quality_status", "created_at_utc", "lifecycle",
)


def validate_quality_record_exact(record: Mapping[str, Any], prepared: PreparedQualityV3) -> None:
    _exact_keys(record, QUALITY_KEYS, "quality record")
    if canonical_json_bytes(record) != canonical_json_bytes(prepared.quality_record):
        raise QualityV3Error("quality record is not exactly parent-derived")


def exclusive_write(root: Path, relative: str, data: bytes) -> str:
    """Exclusively write inert evidence after checking all real parent components."""
    relative = _canonical_relative(relative, "exclusive_write.relative")
    path = _safe_chain(root, relative, final_may_be_missing=True)
    with _hold_parent_directories(root, relative):
        if path.exists() or path.is_symlink():
            raise FileExistsError(path)
        parent_rel = Path(relative).parent.as_posix()
        if parent_rel != ".":
            _safe_chain(root, parent_rel)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        fd = os.open(path, flags, 0o600)
        try:
            written = 0
            while written < len(data):
                written += os.write(fd, data[written:])
            os.fsync(fd)
            st = os.fstat(fd)
            if st.st_nlink != 1 or _is_reparse(st) or st.st_size != len(data):
                raise QualityV3Error("exclusive output identity/link/size failure")
        finally:
            os.close(fd)
    if stable_read(root, relative, expected_sha256=sha256_bytes(data)) != data:
        raise QualityV3Error("exclusive output readback mismatch")
    return sha256_bytes(data)


def safe_make_directory(root: Path, relative: str) -> Path:
    relative = _canonical_relative(relative, "safe_make_directory.relative")
    parts = Path(relative).parts
    current = _validated_real_root(root)
    for index, part in enumerate(parts):
        next_path = current / part
        if next_path.exists() or next_path.is_symlink():
            st = os.lstat(next_path)
            if _is_reparse(st) or stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                raise QualityV3Error("output directory contains reparse/non-directory component")
            if index == len(parts) - 1:
                raise FileExistsError(next_path)
        else:
            partial_relative = Path(*parts[: index + 1]).as_posix()
            with _hold_parent_directories(root, partial_relative):
                os.mkdir(next_path)
            st = os.lstat(next_path)
            if _is_reparse(st) or stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                raise QualityV3Error("created output directory is unsafe")
        current = next_path
    return current


HEAD_KEYS = (
    "schema_version", "record_kind", "generation", "request_id", "candidate_id",
    "revision", "record_path", "record_sha256", "previous_head_sha256",
    "consumed_parent_record_sha256", "request_sha256", "registry_sha256",
    "created_at_utc", "lifecycle",
)


def validate_head_chain(authority: ParentAuthorityV3, request_id: str) -> list[dict[str, Any]]:
    _require_parent_authority(authority)
    prepared = prepare_quality_v3(authority, request_id)
    request = prepared.request
    index = prepared.index
    head_dir = _canonical_relative(index["head_directory"], "head_directory")
    directory = _safe_chain(authority.root, head_dir)
    rows: list[dict[str, Any]] = []
    entries = sorted(directory.iterdir())
    files = [path for path in entries if path.name.startswith("head_") and path.suffix == ".json" and path.is_file()]
    if len(entries) != len(files):
        raise QualityV3Error("head directory contains an unrecognized file, directory, or alias")
    # Attempt 01 intentionally exposes no correction/successor writer. A second
    # head is therefore always an unauthorized fork/replay. A future correction
    # protocol must be a separately audited additive successor, not an implicit
    # acceptance of model- or caller-authored history.
    if len(files) > 1:
        raise QualityV3Error("V3 Attempt 01 permits one immutable head; successor/fork rejected")
    expected_previous = ""
    consumed: set[str] = set()
    for generation, path in enumerate(files, start=1):
        if path.name != f"head_{generation:06d}.json":
            raise QualityV3Error("head ledger must be contiguous with no forks/gaps")
        rel = path.relative_to(authority.root).as_posix()
        head = stable_load_json(authority.root, rel)
        _exact_keys(head, HEAD_KEYS, "quality head")
        if head["schema_version"] != SCHEMA_VERSION or head["record_kind"] != HEAD_KIND:
            raise QualityV3Error("head kind/version mismatch")
        if _strict_int(head["generation"], "head.generation", minimum=1) != generation:
            raise QualityV3Error("head generation mismatch")
        if head["request_id"] != request_id or head["candidate_id"] != request["candidate_id"]:
            raise QualityV3Error("head request/candidate mismatch")
        if head["previous_head_sha256"] != expected_previous:
            raise QualityV3Error("head chain predecessor mismatch")
        _strict_int(head["revision"], "head.revision", minimum=1)
        expected_record_path = (
            f"{str(index['output_directory']).rstrip('/')}/"
            "creator_quality_v3_revision_000001.json"
        )
        if head["record_path"] != expected_record_path or head["revision"] != 1:
            raise QualityV3Error("head record path/revision is not the exact parent-owned V3 initial record")
        record_raw = stable_read(authority.root, head["record_path"], expected_sha256=head["record_sha256"])
        record = _decode_canonical_json(record_raw, label="head record")
        validate_quality_record_exact(record, prepared)
        if generation > 1:
            consumed_hash = _sha(head["consumed_parent_record_sha256"], "consumed parent")
            if consumed_hash in consumed or consumed_hash != rows[-1]["record_sha256"]:
                raise QualityV3Error("head fork/replay/consumed-parent mismatch")
            consumed.add(consumed_hash)
        elif head["consumed_parent_record_sha256"] != "":
            raise QualityV3Error("first head must not consume a parent")
        if head["request_sha256"] != index["request_sha256"] or head["registry_sha256"] != index["registry_sha256"]:
            raise QualityV3Error("head request/registry hash mismatch")
        if _utc(head["created_at_utc"], "head.created_at_utc") > _utc(authority.trusted_now_utc, "trusted_now"):
            raise QualityV3Error("head future dated")
        _validate_lifecycle(head["lifecycle"], "head.lifecycle")
        expected_previous = sha256_bytes(canonical_json_bytes(head))
        rows.append(head)
    return rows


__all__ = [
    "AI_TYPES", "CASE_KINDS", "CORRECTION_KIND", "EVALUATION_KIND",
    "EVALUATION_ROOT_KIND", "EXACT_QWEN_DIGEST", "EXACT_QWEN_MODEL",
    "EXPERT_CASE_KIND", "HEAD_KIND", "MATURITY_RECEIPT_KIND",
    "ParentAuthorityV3", "ParentEvaluationAuthorityV3", "PreparedQualityV3",
    "PRIVATE_STATUS", "QUALITY_KIND", "QualityV3Error", "READY_STATUS",
    "REGISTRY_KIND", "REQUEST_KIND", "RESPONSE_KIND", "ROOT_KIND",
    "SCHEMA_VERSION", "SOURCE_RECEIPT_KIND", "canonical_json_bytes",
    "canonical_sha256", "evaluate_expert_battery_v3", "exclusive_write",
    "open_parent_authority", "open_parent_evaluation_authority",
    "prepare_quality_v3", "private_lifecycle",
    "safe_make_directory", "sha256_bytes", "sha256_text", "stable_load_json",
    "stable_read", "validate_head_chain", "validate_quality_record_exact",
]
