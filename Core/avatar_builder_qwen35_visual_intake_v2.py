"""Fail-closed v2 static visual intake for Avatar Builder.

V2 is an append-only repair successor to the preserved v1 prototype. It loads
all subject, rights, continuity, maturity, correction, and media authority from
hash-bound project artifacts rather than from request booleans or prose. It
prepares and validates evidence only. There is no network, Ollama, subprocess,
video decoder, Blender, geometry, or activation path in this module.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping, Sequence
import warnings

from PIL import Image

from Core.avatar_builder_correction_memory import verify_correction_event_chain
from Core.avatar_profile_preflight import evaluate_avatar_profile_preflight
from Core.model_request_policy import (
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    require_exact_qwen35_selection,
)


ROUTE_ID = "avatar_builder_qwen35_visual_intake_v2"
CONTRACT_ID = ROUTE_ID
CONTRACT_RELATIVE_PATH = Path(
    "Avatar/avatar_builder/policies/qwen35_visual_intake_contract_v2.json"
)
CONTRACT_SHA256 = "2dbc4e280b70efe6772ae7c25243f252cc73caa6f8b0dd8dc72e5cbd2d2d1bc0"
OWNER_REGISTRY_RELATIVE_PATH = Path(
    "Avatar/avatar_builder/policies/qwen35_visual_intake_owner_authority_registry_v1.json"
)
OWNER_REGISTRY_SHA256 = "e69c845427103c8166811ee5da0b3082ce9b5d8a406b87b51c74625b5180e0ac"
QWEN_VISUAL_MODEL = QWEN_TEXT_VOICE_MODEL
QWEN_VISUAL_DIGEST = QWEN_TEXT_VOICE_DIGEST
OLLAMA_CHAT_ENDPOINT = "http://127.0.0.1:11434/api/chat"
PLAN_ROOT = Path("RecoverySprint/avatar_builder_qwen35_visual_intake_v2/plans")
VALIDATED_OUTPUT_ROOT = Path(
    "RecoverySprint/avatar_builder_qwen35_visual_intake_v2/validated_observations"
)

SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_PRIVATE_TOP_LEVELS = frozenset({"Avatar", "TemporaryAI", "RecoverySprint"})
ALLOWED_IMAGE_SUFFIXES = frozenset({".bmp", ".jpeg", ".jpg", ".png", ".webp"})
ALLOWED_VIDEO_SUFFIXES = frozenset({".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"})
MAX_SOURCE_ITEMS = 12
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 24 * 1024 * 1024
MAX_VIDEO_BYTES = 4 * 1024 * 1024 * 1024
MAX_WIDTH = 8192
MAX_HEIGHT = 8192
MAX_PIXELS = 40_000_000

ADULT_CLASSES = frozenset({"adult", "adult_confirmed", "confirmed_adult"})
NON_ADULT_CLASSES = frozenset(
    {
        "child",
        "minor",
        "non_adult",
        "non_adult_doll_safe",
        "teen",
    }
)
UNRESOLVED_CLASSES = frozenset(
    {
        "adult_aged_up_variant",
        "uncertain_non_adult_safe_default",
        "unresolved",
        "unresolved_doll_safe",
    }
)
MATURITY_LANES = frozenset(
    {"adult", "non_adult_doll_safe", "unresolved_doll_safe"}
)
IDENTITY_CLASS_TO_SUBJECT_KIND = {
    "fictional_character": "fictional",
    "fictional_android": "fictional",
    "fictional_nonhuman": "fictional",
    "historical_person": "historical",
    "generated_expert": "synthetic_person",
    "original_person": "synthetic_person",
    "synthetic_person": "synthetic_person",
    "real_owner_variant": "owner",
    "real_person": "living_person",
    "living_person": "living_person",
}
OBSERVATION_CATEGORIES = frozenset(
    {
        "body_proportion",
        "ear",
        "eye_shape",
        "eyebrow",
        "face_shape",
        "garment_occlusion",
        "hair_style",
        "hairline",
        "lips",
        "material",
        "nose",
        "posture",
        "silhouette",
        "skin_regional_variation",
        "skin_tone",
        "unknown",
    }
)
CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})
SUGGESTION_GROUPS = ("morph", "material", "hair")


class AvatarVisualIntakeV2Error(ValueError):
    """A v2 authority, source, plan, or output failed closed."""


class PreparedPlanDriftError(AvatarVisualIntakeV2Error):
    """External authority or source state changed after preparation."""


class ProtectedOutputError(AvatarVisualIntakeV2Error):
    """A plan or receipt destination was unsafe or already existed."""


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).casefold()).strip("_")


def _safe_id(value: Any, field: str) -> str:
    result = _text(value)
    if not SAFE_ID_RE.fullmatch(result):
        raise AvatarVisualIntakeV2Error(f"{field} is not a safe identifier")
    return result


def _exact_sha(value: Any, field: str, *, allow_empty: bool = False) -> str:
    result = _text(value).casefold()
    if allow_empty and not result:
        return ""
    if not SHA256_RE.fullmatch(result):
        raise AvatarVisualIntakeV2Error(f"{field} is not an exact SHA-256")
    return result


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AvatarVisualIntakeV2Error(f"{field} must be an object")
    return value


def _sequence(value: Any, field: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise AvatarVisualIntakeV2Error(f"{field} must be an array")
    return value


def _clean_text(
    value: Any,
    field: str,
    *,
    limit: int,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise AvatarVisualIntakeV2Error(f"{field} must be text")
    result = re.sub(r"[\x00-\x1f\x7f]+", " ", value)
    result = re.sub(r"\s+", " ", result).strip()
    if (not result and not allow_empty) or len(result) > limit:
        raise AvatarVisualIntakeV2Error(f"{field} is empty or exceeds its limit")
    return result


def _regular_project_file(root: Path, relative_value: Any, field: str) -> Path:
    relative = Path(_text(relative_value))
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise AvatarVisualIntakeV2Error(f"{field} must be project-relative")
    candidate = root / relative
    current = candidate
    while True:
        if current.is_symlink():
            raise AvatarVisualIntakeV2Error(f"{field} may not traverse a symlink")
        if current == root or current.parent == current:
            break
        current = current.parent
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise AvatarVisualIntakeV2Error(f"{field} is missing or escapes the project") from exc
    if not resolved.is_file():
        raise AvatarVisualIntakeV2Error(f"{field} is not a regular file")
    return resolved


def _private_project_file(root: Path, relative_value: Any, field: str) -> Path:
    relative = Path(_text(relative_value))
    if not relative.parts or relative.parts[0] not in ALLOWED_PRIVATE_TOP_LEVELS:
        raise AvatarVisualIntakeV2Error(f"{field} is outside project-private evidence lanes")
    return _regular_project_file(root, relative, field)


def _read_json_object(path: Path, field: str) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise AvatarVisualIntakeV2Error(f"{field} could not be stat-checked") from exc
    if size <= 0 or size > MAX_JSON_BYTES:
        raise AvatarVisualIntakeV2Error(f"{field} JSON byte size is outside bounds")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AvatarVisualIntakeV2Error(f"{field} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise AvatarVisualIntakeV2Error(f"{field} JSON must be an object")
    return value


def _load_contract(root: Path) -> dict[str, Any]:
    path = _regular_project_file(root, CONTRACT_RELATIVE_PATH, "v2 contract")
    actual_sha = _sha256_file(path)
    if actual_sha != CONTRACT_SHA256:
        raise AvatarVisualIntakeV2Error("v2 machine contract hash mismatch")
    contract = _read_json_object(path, "v2 contract")
    if contract.get("schema_version") != 2 or contract.get("contract_id") != CONTRACT_ID:
        raise AvatarVisualIntakeV2Error("v2 machine contract identity mismatch")
    authority = _mapping(contract.get("authority"), "contract.authority")
    if _text(authority.get("registry_path")) != OWNER_REGISTRY_RELATIVE_PATH.as_posix():
        raise AvatarVisualIntakeV2Error("contract owner-authority registry path mismatch")
    if _text(authority.get("registry_sha256")).casefold() != OWNER_REGISTRY_SHA256:
        raise AvatarVisualIntakeV2Error("contract owner-authority registry digest mismatch")
    return {
        "artifact": contract,
        "path": CONTRACT_RELATIVE_PATH.as_posix(),
        "sha256": actual_sha,
    }


def _load_registered_owner_authority(
    root: Path,
    authority_id: str,
    contract_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Load an authority only through the fixed, contract-hash-bound registry."""

    registry_path = _regular_project_file(
        root, OWNER_REGISTRY_RELATIVE_PATH, "owner authority registry"
    )
    registry_sha = _sha256_file(registry_path)
    if registry_sha != OWNER_REGISTRY_SHA256:
        raise AvatarVisualIntakeV2Error("owner authority registry hash mismatch")
    if registry_sha != contract_binding["artifact"]["authority"]["registry_sha256"]:
        raise AvatarVisualIntakeV2Error("contract and owner registry binding mismatch")
    registry = _read_json_object(registry_path, "owner authority registry")
    if registry.get("registry_id") != "qwen35_visual_intake_owner_authority_registry_v1":
        raise AvatarVisualIntakeV2Error("owner authority registry identity mismatch")
    entries = _sequence(registry.get("entries"), "owner authority registry entries")
    matches = [
        item
        for item in entries
        if isinstance(item, Mapping)
        and _text(item.get("authority_id")) == authority_id
        and item.get("status") == "active"
    ]
    if len(matches) != 1:
        raise AvatarVisualIntakeV2Error("exact owner authority is not actively registered")
    entry = matches[0]
    if set(entry) != {"authority_id", "artifact_path", "artifact_sha256", "status"}:
        raise AvatarVisualIntakeV2Error("owner authority registry entry schema mismatch")
    artifact_path = _regular_project_file(root, entry.get("artifact_path"), "owner authority artifact")
    authority_root = (root / _text(registry.get("authority_root"))).resolve()
    if authority_root not in artifact_path.parents:
        raise AvatarVisualIntakeV2Error("owner authority artifact is outside the protected authority root")
    expected_sha = _exact_sha(entry.get("artifact_sha256"), "owner authority artifact sha256")
    actual_sha = _sha256_file(artifact_path)
    if actual_sha != expected_sha:
        raise AvatarVisualIntakeV2Error("owner authority artifact hash mismatch")
    artifact = _read_json_object(artifact_path, "owner authority artifact")
    return {
        "artifact": artifact,
        "artifact_path": artifact_path.relative_to(root).as_posix(),
        "artifact_sha256": actual_sha,
        "registry_path": OWNER_REGISTRY_RELATIVE_PATH.as_posix(),
        "registry_sha256": registry_sha,
    }


def _verify_hash_object(value: Mapping[str, Any], hash_field: str, field: str) -> str:
    stored = _exact_sha(value.get(hash_field), f"{field}.{hash_field}")
    payload = dict(value)
    payload.pop(hash_field, None)
    if canonical_sha256(payload) != stored:
        raise AvatarVisualIntakeV2Error(f"{field} content hash mismatch")
    return stored


def _profile_route(
    root: Path,
    candidate_id: str,
    subject_id: str,
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    preflight = evaluate_avatar_profile_preflight(
        root,
        candidate_id,
        requested_subject_id=subject_id,
    )
    if preflight.get("registry_binding_verified") is not True:
        raise AvatarVisualIntakeV2Error("canonical profile registry binding is not verified")
    if _text(preflight.get("canonical_candidate_id")) != candidate_id:
        raise AvatarVisualIntakeV2Error("canonical candidate mismatch")
    identity = _mapping(preflight.get("identity"), "profile preflight identity")
    if _text(identity.get("subject_id")) != subject_id:
        raise AvatarVisualIntakeV2Error("canonical subject mismatch")
    identity_class = _normalized(identity.get("identity_class"))
    expected_kind = IDENTITY_CLASS_TO_SUBJECT_KIND.get(identity_class)
    if expected_kind is None:
        raise AvatarVisualIntakeV2Error("canonical identity class has no subject-kind policy")
    maturity = _mapping(preflight.get("maturity"), "profile preflight maturity")
    lane = _normalized(maturity.get("lane"))
    if lane not in MATURITY_LANES:
        raise AvatarVisualIntakeV2Error("canonical maturity lane is invalid")
    registry = _mapping(preflight.get("registry"), "profile preflight registry")
    profile = _mapping(preflight.get("canonical_profile"), "canonical profile")
    creation = _mapping(preflight.get("creation_request"), "canonical creation request")
    binding = _mapping(authority.get("canonical_binding"), "authority canonical binding")
    actual = {
        "registry_path": _text(registry.get("path")),
        "registry_sha256": _exact_sha(registry.get("sha256"), "profile registry sha256"),
        "profile_path": _text(profile.get("path")),
        "profile_sha256": _exact_sha(profile.get("sha256"), "canonical profile sha256"),
        "creation_request_path": _text(creation.get("path")),
        "creation_request_sha256": _exact_sha(
            creation.get("sha256"), "creation request sha256", allow_empty=True
        ),
        "maturity_lane": lane,
        "selected_version": _text(identity.get("selected_version")),
        "identity_class": identity_class,
        "subject_kind": expected_kind,
    }
    for key in (
        "registry_path",
        "registry_sha256",
        "profile_path",
        "profile_sha256",
        "creation_request_path",
        "creation_request_sha256",
        "maturity_lane",
        "selected_version",
    ):
        if _text(binding.get(key)).casefold() != _text(actual[key]).casefold():
            raise AvatarVisualIntakeV2Error(f"owner authority canonical binding mismatch: {key}")
    profile_document_path = _private_project_file(
        root, actual["profile_path"], "canonical profile document"
    )
    if _sha256_file(profile_document_path) != actual["profile_sha256"]:
        raise AvatarVisualIntakeV2Error("canonical profile bytes changed during preflight")
    profile_document = _read_json_object(profile_document_path, "canonical profile document")
    profile_subject_binding = _mapping(
        profile_document.get("qwen35_visual_intake_subject_binding"),
        "canonical profile visual-intake subject binding",
    )
    subject_binding_fields = {
        "schema_version",
        "selected_subject_event_id",
        "selected_subject_event_sha256",
        "subject_id",
        "subject_kind",
        "selected_version_or_era",
        "selected_timepoint",
    }
    if set(profile_subject_binding) != subject_binding_fields or profile_subject_binding.get(
        "schema_version"
    ) != 1:
        raise AvatarVisualIntakeV2Error(
            "canonical profile lacks the exact visual-intake subject-binding schema"
        )
    normalized_profile_subject_binding = {
        "schema_version": 1,
        "selected_subject_event_id": _safe_id(
            profile_subject_binding.get("selected_subject_event_id"),
            "canonical profile selected-subject event ID",
        ),
        "selected_subject_event_sha256": _exact_sha(
            profile_subject_binding.get("selected_subject_event_sha256"),
            "canonical profile selected-subject event SHA-256",
        ),
        "subject_id": _safe_id(
            profile_subject_binding.get("subject_id"),
            "canonical profile visual-intake subject ID",
        ),
        "subject_kind": _text(profile_subject_binding.get("subject_kind")),
        "selected_version_or_era": _text(
            profile_subject_binding.get("selected_version_or_era")
        ),
        "selected_timepoint": _text(profile_subject_binding.get("selected_timepoint")),
    }
    if normalized_profile_subject_binding["subject_id"] != subject_id:
        raise AvatarVisualIntakeV2Error("canonical profile visual-intake subject ID mismatch")
    if normalized_profile_subject_binding["subject_kind"] != expected_kind:
        raise AvatarVisualIntakeV2Error(
            "canonical profile visual-intake subject kind conflicts with identity class"
        )
    if (
        normalized_profile_subject_binding["selected_version_or_era"].casefold()
        != actual["selected_version"].casefold()
    ):
        raise AvatarVisualIntakeV2Error(
            "canonical profile visual-intake version conflicts with canonical preflight"
        )
    if expected_kind in {"fictional", "historical"} and not normalized_profile_subject_binding[
        "selected_timepoint"
    ]:
        raise AvatarVisualIntakeV2Error(
            "canonical fictional/historical profile has no selected timepoint"
        )
    actual["profile_subject_binding"] = normalized_profile_subject_binding
    reconciliation = _mapping(
        profile_document.get("qwen35_visual_intake_reconciliation"),
        "canonical profile visual-intake reconciliation",
    )
    reconciliation_fields = {
        "schema_version",
        "latest_exact_person_event_id",
        "latest_exact_person_event_sha256",
        "reconciled_maturity_event_id",
        "reconciled_maturity_event_sha256",
        "reconciled_continuity_event_id",
        "reconciled_continuity_event_sha256",
        "resolved_maturity_lane",
        "resolved_selected_version",
        "resolved_selected_timepoint",
        "continuity_directive_sha256",
        "reconciled_continuity_markers",
    }
    if set(reconciliation) != reconciliation_fields or reconciliation.get("schema_version") != 1:
        raise AvatarVisualIntakeV2Error(
            "canonical profile lacks the exact visual-intake correction reconciliation schema"
        )
    normalized_reconciliation = dict(reconciliation)
    for key in (
        "latest_exact_person_event_sha256",
        "reconciled_maturity_event_sha256",
        "reconciled_continuity_event_sha256",
        "continuity_directive_sha256",
    ):
        normalized_reconciliation[key] = _exact_sha(
            reconciliation.get(key),
            f"canonical profile reconciliation {key}",
            allow_empty=True,
        )
    for key in (
        "latest_exact_person_event_id",
        "reconciled_maturity_event_id",
        "reconciled_continuity_event_id",
    ):
        event_id = _text(reconciliation.get(key))
        normalized_reconciliation[key] = (
            _safe_id(event_id, f"canonical profile reconciliation {key}") if event_id else ""
        )
    markers = reconciliation.get("reconciled_continuity_markers")
    if not isinstance(markers, list) or any(not isinstance(item, str) for item in markers):
        raise AvatarVisualIntakeV2Error("canonical profile reconciliation markers are invalid")
    normalized_reconciliation["reconciled_continuity_markers"] = list(markers)
    resolved_lane = _text(reconciliation.get("resolved_maturity_lane"))
    if resolved_lane and resolved_lane not in MATURITY_LANES:
        raise AvatarVisualIntakeV2Error("canonical profile reconciled maturity lane is invalid")
    normalized_reconciliation["resolved_maturity_lane"] = resolved_lane
    for key in ("resolved_selected_version", "resolved_selected_timepoint"):
        normalized_reconciliation[key] = _text(reconciliation.get(key))
    actual["profile_correction_reconciliation"] = normalized_reconciliation
    actual.update(
        {
            "template_lane": (
                "confirmed_adult_template"
                if lane == "adult"
                else "non_adult_doll_safe_template"
            ),
            "authoring_allowed_by_profile_preflight": preflight.get("authoring_allowed") is True,
            "profile_preflight_status": _text(preflight.get("status")),
            "profile_preflight_failures": [str(item) for item in preflight.get("failures", [])],
            "adult_anatomy_authoring_authorized": False,
            "maturity_inference_from_media_allowed": False,
        }
    )
    return actual


def _normalized_requested_lane(value: Any) -> str:
    normalized = _normalized(value)
    if normalized in ADULT_CLASSES:
        return "adult"
    if normalized in NON_ADULT_CLASSES:
        return "non_adult_doll_safe"
    if normalized in UNRESOLVED_CLASSES:
        return "unresolved_doll_safe"
    return ""


def _correction_authority(
    root: Path,
    candidate_id: str,
    profile_route: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    binding = _mapping(authority.get("correction_memory"), "authority correction memory")
    path = _private_project_file(root, binding.get("path"), "correction memory path")
    expected_sha = _exact_sha(binding.get("sha256"), "correction memory sha256")
    actual_sha = _sha256_file(path)
    if actual_sha != expected_sha:
        raise AvatarVisualIntakeV2Error("correction memory file hash mismatch")
    memory = _read_json_object(path, "correction memory")
    events = memory.get("correction_memory_events", [])
    if not isinstance(events, list):
        raise AvatarVisualIntakeV2Error("correction memory events must be an array")
    verification = verify_correction_event_chain(events)
    if verification.get("status") != "passed":
        raise AvatarVisualIntakeV2Error("correction memory hash chain failed")
    if _text(binding.get("chain_head_sha256")) != _text(verification.get("head_event_sha256")):
        raise AvatarVisualIntakeV2Error("correction memory chain head is not authority-bound")
    exact_events = [event for event in events if _text(event.get("candidate_id")) == candidate_id]
    latest = exact_events[-1] if exact_events else {}
    if _text(binding.get("latest_exact_person_event_id")) != _text(latest.get("event_id")):
        raise AvatarVisualIntakeV2Error("latest exact-person correction ID is not authority-bound")
    if _text(binding.get("latest_exact_person_event_sha256")) != _text(latest.get("event_sha256")):
        raise AvatarVisualIntakeV2Error("latest exact-person correction hash is not authority-bound")
    profile_reconciliation = _mapping(
        profile_route.get("profile_correction_reconciliation"),
        "canonical profile correction reconciliation",
    )
    if _text(profile_reconciliation.get("latest_exact_person_event_id")) != _text(
        latest.get("event_id")
    ) or _text(profile_reconciliation.get("latest_exact_person_event_sha256")) != _text(
        latest.get("event_sha256")
    ):
        raise AvatarVisualIntakeV2Error(
            "latest exact-person correction is not acknowledged by canonical profile bytes"
        )

    maturity_events: list[Mapping[str, Any]] = []
    continuity_events: list[Mapping[str, Any]] = []
    for event in exact_events:
        directives = event.get("directives") if isinstance(event.get("directives"), Mapping) else {}
        maturity = directives.get("maturity") if isinstance(directives.get("maturity"), Mapping) else {}
        continuity = directives.get("continuity") if isinstance(directives.get("continuity"), Mapping) else {}
        if _text(maturity.get("requested_class")):
            maturity_events.append(event)
        if continuity:
            continuity_events.append(event)

    canonical = _mapping(authority.get("canonical_binding"), "authority canonical binding")
    latest_maturity = maturity_events[-1] if maturity_events else {}
    latest_continuity = continuity_events[-1] if continuity_events else {}
    for prefix, event in (
        ("reconciled_maturity", latest_maturity),
        ("reconciled_continuity", latest_continuity),
    ):
        if _text(canonical.get(f"{prefix}_event_id")) != _text(event.get("event_id")):
            raise AvatarVisualIntakeV2Error(f"latest {prefix} event ID is not reconciled")
        if _text(canonical.get(f"{prefix}_event_sha256")) != _text(event.get("event_sha256")):
            raise AvatarVisualIntakeV2Error(f"latest {prefix} event hash is not reconciled")
        if _text(profile_reconciliation.get(f"{prefix}_event_id")) != _text(event.get("event_id")):
            raise AvatarVisualIntakeV2Error(
                f"latest {prefix} event ID is not reconciled in canonical profile bytes"
            )
        if _text(profile_reconciliation.get(f"{prefix}_event_sha256")) != _text(
            event.get("event_sha256")
        ):
            raise AvatarVisualIntakeV2Error(
                f"latest {prefix} event hash is not reconciled in canonical profile bytes"
            )

    requested_lane = ""
    if latest_maturity:
        directives = _mapping(latest_maturity.get("directives"), "latest maturity directives")
        maturity_directive = _mapping(directives.get("maturity"), "latest maturity directive")
        requested_lane = _normalized_requested_lane(maturity_directive.get("requested_class"))
        if not requested_lane:
            raise AvatarVisualIntakeV2Error("latest maturity correction class is unrecognized")
        if requested_lane != profile_route["maturity_lane"]:
            raise AvatarVisualIntakeV2Error(
                "latest exact-person maturity correction conflicts with canonical profile"
            )
        if profile_reconciliation.get("resolved_maturity_lane") != requested_lane:
            raise AvatarVisualIntakeV2Error(
                "canonical profile bytes do not resolve the latest maturity correction"
            )
    elif profile_reconciliation.get("resolved_maturity_lane"):
        raise AvatarVisualIntakeV2Error(
            "canonical profile claims a resolved maturity correction that does not exist"
        )

    continuity_directive_sha = ""
    if latest_continuity:
        directives = _mapping(latest_continuity.get("directives"), "latest continuity directives")
        continuity = _mapping(directives.get("continuity"), "latest continuity directive")
        continuity_directive_sha = canonical_sha256(continuity)
        if _text(canonical.get("continuity_directive_sha256")) != continuity_directive_sha:
            raise AvatarVisualIntakeV2Error("latest continuity directive is not hash-reconciled")
        if _text(profile_reconciliation.get("continuity_directive_sha256")) != continuity_directive_sha:
            raise AvatarVisualIntakeV2Error(
                "latest continuity directive is not hash-reconciled in canonical profile bytes"
            )
        markers = continuity.get("markers")
        resolved_markers = canonical.get("reconciled_continuity_markers")
        if not isinstance(markers, list) or markers != resolved_markers:
            raise AvatarVisualIntakeV2Error("latest continuity markers are not reconciled")
        if markers != profile_reconciliation.get("reconciled_continuity_markers"):
            raise AvatarVisualIntakeV2Error(
                "latest continuity markers are not reconciled in canonical profile bytes"
            )
        if not profile_route["selected_version"]:
            raise AvatarVisualIntakeV2Error("continuity correction exists but canonical version is blank")
        if _text(canonical.get("resolved_selected_version")) != profile_route["selected_version"]:
            raise AvatarVisualIntakeV2Error("continuity resolution conflicts with canonical selected version")
        if not _text(canonical.get("resolved_selected_timepoint")):
            raise AvatarVisualIntakeV2Error("continuity resolution has no selected timepoint")
        if (
            _text(profile_reconciliation.get("resolved_selected_version"))
            != profile_route["selected_version"]
            or not _text(profile_reconciliation.get("resolved_selected_timepoint"))
        ):
            raise AvatarVisualIntakeV2Error(
                "canonical profile bytes do not resolve the latest continuity correction"
            )
    elif (
        profile_reconciliation.get("continuity_directive_sha256")
        or profile_reconciliation.get("reconciled_continuity_markers")
        or profile_reconciliation.get("resolved_selected_version")
        or profile_reconciliation.get("resolved_selected_timepoint")
    ):
        raise AvatarVisualIntakeV2Error(
            "canonical profile claims a resolved continuity correction that does not exist"
        )

    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": actual_sha,
        "chain_head_sha256": _text(verification.get("head_event_sha256")),
        "event_count": verification.get("event_count"),
        "latest_exact_person_event_id": _text(latest.get("event_id")),
        "latest_exact_person_event_sha256": _text(latest.get("event_sha256")),
        "latest_maturity_event_id": _text(latest_maturity.get("event_id")),
        "latest_maturity_event_sha256": _text(latest_maturity.get("event_sha256")),
        "latest_continuity_event_id": _text(latest_continuity.get("event_id")),
        "latest_continuity_event_sha256": _text(latest_continuity.get("event_sha256")),
        "continuity_directive_sha256": continuity_directive_sha,
        "requested_maturity_lane": requested_lane,
        "reconciled": True,
    }


def _subject_authority(
    authority: Mapping[str, Any],
    *,
    authority_id: str,
    candidate_id: str,
    subject_id: str,
    profile_route: Mapping[str, Any],
) -> dict[str, Any]:
    if authority.get("schema_version") != 1 or _text(authority.get("authority_id")) != authority_id:
        raise AvatarVisualIntakeV2Error("owner authority artifact identity mismatch")
    if authority.get("owner_id") != "Robert":
        raise AvatarVisualIntakeV2Error("owner authority artifact is not Robert-bound")
    event = _mapping(authority.get("selected_subject_event"), "selected subject event")
    required = {
        "event_id",
        "event_sha256",
        "recorded_at",
        "owner_id",
        "candidate_id",
        "subject_id",
        "subject_kind",
        "source_text",
        "source_text_sha256",
        "selected_version_or_era",
        "selected_timepoint",
        "rights_scope",
        "media_authorization_ids",
    }
    if set(event) != required:
        raise AvatarVisualIntakeV2Error("selected subject event schema mismatch")
    event_sha = _verify_hash_object(event, "event_sha256", "selected subject event")
    source_text = _clean_text(event.get("source_text"), "selected subject source text", limit=2_000)
    if _sha256_bytes(source_text.encode("utf-8")) != _exact_sha(
        event.get("source_text_sha256"), "selected subject source text sha256"
    ):
        raise AvatarVisualIntakeV2Error("selected subject source text hash mismatch")
    if event.get("owner_id") != "Robert":
        raise AvatarVisualIntakeV2Error("selected subject event is not Robert-authored")
    if _text(event.get("candidate_id")) != candidate_id or _text(event.get("subject_id")) != subject_id:
        raise AvatarVisualIntakeV2Error("selected subject event exact-person binding mismatch")
    if _text(event.get("subject_kind")) != profile_route["subject_kind"]:
        raise AvatarVisualIntakeV2Error("subject kind conflicts with canonical identity class")
    profile_subject_binding = _mapping(
        profile_route.get("profile_subject_binding"),
        "canonical profile subject binding",
    )
    if (
        profile_subject_binding.get("selected_subject_event_id") != event.get("event_id")
        or profile_subject_binding.get("selected_subject_event_sha256") != event_sha
    ):
        raise AvatarVisualIntakeV2Error(
            "selected subject event is not bound by the exact canonical profile bytes"
        )
    version = _text(event.get("selected_version_or_era"))
    timepoint = _text(event.get("selected_timepoint"))
    if profile_route["subject_kind"] in {"fictional", "historical"}:
        if not version or not timepoint:
            raise AvatarVisualIntakeV2Error("fictional/historical owner event lacks version or timepoint")
        if version.casefold() != profile_route["selected_version"].casefold():
            raise AvatarVisualIntakeV2Error("owner event version conflicts with canonical selected version")
    if (
        profile_subject_binding.get("selected_version_or_era") != version
        or profile_subject_binding.get("selected_timepoint") != timepoint
    ):
        raise AvatarVisualIntakeV2Error(
            "owner event version/timepoint conflicts with exact canonical profile bytes"
        )
    if event.get("rights_scope") != "private_avatar_reconstruction_only_no_public_export":
        raise AvatarVisualIntakeV2Error("selected subject rights scope is not private-only")
    media_ids = [
        _safe_id(value, "selected subject media authorization id")
        for value in _sequence(event.get("media_authorization_ids"), "selected subject media IDs")
    ]
    if len(media_ids) != len(set(media_ids)):
        raise AvatarVisualIntakeV2Error("selected subject media authorization IDs are duplicated")
    return {
        "event_id": _safe_id(event.get("event_id"), "selected subject event id"),
        "event_sha256": event_sha,
        "source_text_sha256": _text(event.get("source_text_sha256")),
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "subject_kind": profile_route["subject_kind"],
        "selected_version_or_era": version,
        "selected_timepoint": timepoint,
        "rights_scope": event["rights_scope"],
        "media_authorization_ids": media_ids,
        "meaning": "Robert_selected_subject_scope_not_model_face_identification",
        "face_identity_claim_allowed": False,
    }


def _decode_image_bytes(data: bytes, suffix: str, field: str) -> dict[str, Any]:
    if len(data) == 0 or len(data) > MAX_IMAGE_BYTES:
        raise AvatarVisualIntakeV2Error(f"{field} image byte size is outside bounds")
    if suffix.casefold() not in ALLOWED_IMAGE_SUFFIXES:
        raise AvatarVisualIntakeV2Error(f"{field} image suffix is not allowed")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                probe.verify()
            with Image.open(io.BytesIO(data)) as decoded:
                width, height = decoded.size
                image_format = _text(decoded.format).upper()
                mode = _text(decoded.mode)
                if width <= 0 or height <= 0 or width > MAX_WIDTH or height > MAX_HEIGHT:
                    raise AvatarVisualIntakeV2Error(
                        f"{field} decoded dimensions are outside bounds"
                    )
                if width * height > MAX_PIXELS:
                    raise AvatarVisualIntakeV2Error(
                        f"{field} decoded pixel count exceeds bounds"
                    )
                decoded.load()
    except (
        OSError,
        ValueError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise AvatarVisualIntakeV2Error(f"{field} failed bounded real image decode") from exc
    allowed_formats = {
        ".bmp": {"BMP"},
        ".jpeg": {"JPEG"},
        ".jpg": {"JPEG"},
        ".png": {"PNG"},
        ".webp": {"WEBP"},
    }
    if image_format not in allowed_formats[suffix.casefold()]:
        raise AvatarVisualIntakeV2Error(f"{field} decoded format conflicts with suffix")
    return {
        "width": width,
        "height": height,
        "pixel_count": width * height,
        "format": image_format,
        "mode": mode,
    }


def _video_container_signature(path: Path) -> str:
    if path.suffix.casefold() not in ALLOWED_VIDEO_SUFFIXES:
        raise AvatarVisualIntakeV2Error("parent video suffix is not allowed")
    with path.open("rb") as stream:
        header = stream.read(16)
    suffix = path.suffix.casefold()
    if suffix in {".mp4", ".m4v", ".mov"} and len(header) >= 8 and header[4:8] == b"ftyp":
        return "isobmff"
    if suffix in {".mkv", ".webm"} and header.startswith(b"\x1aE\xdf\xa3"):
        return "ebml"
    if suffix == ".avi" and header.startswith(b"RIFF") and header[8:12] == b"AVI ":
        return "avi"
    raise AvatarVisualIntakeV2Error("parent video container signature mismatch")


def _provenance_record(value: Any, field: str) -> dict[str, Any]:
    record = _mapping(value, field)
    required = {
        "record_id",
        "record_sha256",
        "source_kind",
        "title_or_version",
        "origin_record",
        "rights_basis",
        "private_reconstruction_allowed",
        "public_export_allowed",
    }
    if set(record) != required:
        raise AvatarVisualIntakeV2Error(f"{field} schema mismatch")
    record_sha = _verify_hash_object(record, "record_sha256", field)
    if record.get("private_reconstruction_allowed") is not True:
        raise AvatarVisualIntakeV2Error(f"{field} does not authorize private reconstruction")
    if record.get("public_export_allowed") is not False:
        raise AvatarVisualIntakeV2Error(f"{field} does not prohibit public export")
    return {
        "record_id": _safe_id(record.get("record_id"), f"{field}.record_id"),
        "record_sha256": record_sha,
        "source_kind": _clean_text(record.get("source_kind"), f"{field}.source_kind", limit=80),
        "title_or_version": _clean_text(record.get("title_or_version"), f"{field}.title_or_version", limit=300),
        "origin_record": _clean_text(record.get("origin_record"), f"{field}.origin_record", limit=500),
        "rights_basis": _clean_text(record.get("rights_basis"), f"{field}.rights_basis", limit=500),
        "private_reconstruction_allowed": True,
        "public_export_allowed": False,
    }


def _video_receipt(
    root: Path,
    authorization: Mapping[str, Any],
    frame_path: Path,
    frame_sha: str,
    image_info: Mapping[str, Any],
) -> dict[str, Any]:
    receipt_path = _private_project_file(
        root, authorization.get("extractor_receipt_path"), "video extractor receipt path"
    )
    expected_receipt_sha = _exact_sha(
        authorization.get("extractor_receipt_sha256"), "video extractor receipt sha256"
    )
    if _sha256_file(receipt_path) != expected_receipt_sha:
        raise AvatarVisualIntakeV2Error("video extractor receipt hash mismatch")
    receipt = _read_json_object(receipt_path, "video extractor receipt")
    required = {
        "schema_version",
        "status",
        "extractor_name",
        "extractor_version",
        "extractor_binary_sha256",
        "exact_options",
        "parent_video_project_relative_path",
        "parent_video_sha256",
        "stream_id",
        "time_base",
        "requested_timestamp_seconds",
        "actual_pts",
        "actual_timestamp_seconds",
        "frame_index",
        "duration_seconds",
        "decoded_width",
        "decoded_height",
        "pixel_format",
        "frame_project_relative_path",
        "frame_sha256",
        "independent_reextract_sha256",
        "independent_reextract_bytes_match",
        "full_video_viewing_claim_allowed",
    }
    if set(receipt) != required or receipt.get("schema_version") != 1:
        raise AvatarVisualIntakeV2Error("video extractor receipt schema mismatch")
    if receipt.get("status") != "verified_bounded_exact_sample":
        raise AvatarVisualIntakeV2Error("video extractor receipt is not verified")
    _clean_text(receipt.get("extractor_name"), "extractor name", limit=120)
    _clean_text(receipt.get("extractor_version"), "extractor version", limit=120)
    _exact_sha(receipt.get("extractor_binary_sha256"), "extractor binary sha256")
    options = _sequence(receipt.get("exact_options"), "extractor exact options")
    if not options or len(options) > 64 or not all(isinstance(item, str) and item for item in options):
        raise AvatarVisualIntakeV2Error("extractor exact options are invalid")
    parent_path = _private_project_file(
        root, receipt.get("parent_video_project_relative_path"), "parent video path"
    )
    if parent_path.stat().st_size > MAX_VIDEO_BYTES:
        raise AvatarVisualIntakeV2Error("parent video exceeds the byte bound")
    parent_sha = _exact_sha(receipt.get("parent_video_sha256"), "parent video sha256")
    if _sha256_file(parent_path) != parent_sha:
        raise AvatarVisualIntakeV2Error("parent video hash mismatch")
    container = _video_container_signature(parent_path)
    if _text(receipt.get("frame_project_relative_path")) != frame_path.relative_to(root).as_posix():
        raise AvatarVisualIntakeV2Error("video receipt frame path mismatch")
    if _text(receipt.get("frame_sha256")) != frame_sha:
        raise AvatarVisualIntakeV2Error("video receipt frame hash mismatch")
    if _text(receipt.get("independent_reextract_sha256")) != frame_sha:
        raise AvatarVisualIntakeV2Error("independent video re-extract hash mismatch")
    if receipt.get("independent_reextract_bytes_match") is not True:
        raise AvatarVisualIntakeV2Error("independent video re-extract did not match")
    if receipt.get("full_video_viewing_claim_allowed") is not False:
        raise AvatarVisualIntakeV2Error("video receipt permits unsupported full-viewing claim")
    numbers: dict[str, float] = {}
    for field in (
        "requested_timestamp_seconds",
        "actual_timestamp_seconds",
        "duration_seconds",
    ):
        value = receipt.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise AvatarVisualIntakeV2Error(f"video receipt {field} is invalid")
        numbers[field] = float(value)
    if (
        numbers["requested_timestamp_seconds"] < 0
        or numbers["actual_timestamp_seconds"] < 0
        or numbers["duration_seconds"] <= 0
        or numbers["requested_timestamp_seconds"] > numbers["duration_seconds"]
        or numbers["actual_timestamp_seconds"] > numbers["duration_seconds"]
    ):
        raise AvatarVisualIntakeV2Error("video receipt timestamp lies outside duration")
    actual_pts = receipt.get("actual_pts")
    frame_index = receipt.get("frame_index")
    if isinstance(actual_pts, bool) or not isinstance(actual_pts, int) or actual_pts < 0:
        raise AvatarVisualIntakeV2Error("video receipt actual_pts is invalid")
    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or frame_index < 0:
        raise AvatarVisualIntakeV2Error("video receipt frame_index is invalid")
    time_base = _text(receipt.get("time_base"))
    match = re.fullmatch(r"([1-9][0-9]*)/([1-9][0-9]*)", time_base)
    if match is None:
        raise AvatarVisualIntakeV2Error("video receipt time_base is invalid")
    numerator, denominator = (int(match.group(1)), int(match.group(2)))
    pts_seconds = actual_pts * numerator / denominator
    tolerance = max(numerator / denominator, 1e-6)
    if abs(pts_seconds - numbers["actual_timestamp_seconds"]) > tolerance:
        raise AvatarVisualIntakeV2Error("video receipt PTS/time-base does not match timestamp")
    if receipt.get("decoded_width") != image_info["width"] or receipt.get("decoded_height") != image_info["height"]:
        raise AvatarVisualIntakeV2Error("video receipt decoded dimensions mismatch")
    pixel_format = _clean_text(receipt.get("pixel_format"), "video receipt pixel format", limit=40)
    return {
        "receipt_path": receipt_path.relative_to(root).as_posix(),
        "receipt_sha256": expected_receipt_sha,
        "extractor_name": receipt["extractor_name"],
        "extractor_version": receipt["extractor_version"],
        "extractor_binary_sha256": receipt["extractor_binary_sha256"],
        "exact_options": list(options),
        "parent_video_project_relative_path": parent_path.relative_to(root).as_posix(),
        "parent_video_sha256": parent_sha,
        "parent_video_container": container,
        "stream_id": _clean_text(receipt.get("stream_id"), "video stream id", limit=80),
        "time_base": time_base,
        "requested_timestamp_seconds": numbers["requested_timestamp_seconds"],
        "actual_pts": actual_pts,
        "actual_timestamp_seconds": numbers["actual_timestamp_seconds"],
        "frame_index": frame_index,
        "duration_seconds": numbers["duration_seconds"],
        "pixel_format": pixel_format,
        "independent_reextract_sha256": frame_sha,
        "independent_reextract_bytes_match": True,
        "full_video_viewing_claim_allowed": False,
    }


def _media_sources(
    root: Path,
    requested_ids: Sequence[Any],
    subject_authority: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> list[dict[str, Any]]:
    ids = [_safe_id(value, "media authorization id") for value in requested_ids]
    if not ids or len(ids) > MAX_SOURCE_ITEMS or len(ids) != len(set(ids)):
        raise AvatarVisualIntakeV2Error("media authorization IDs must be unique and bounded")
    authorized_ids = set(subject_authority["media_authorization_ids"])
    if any(value not in authorized_ids for value in ids):
        raise AvatarVisualIntakeV2Error("request names media outside Robert's exact subject event")
    records = _sequence(authority.get("media_authorizations"), "authority media authorizations")
    by_id: dict[str, Mapping[str, Any]] = {}
    for value in records:
        if not isinstance(value, Mapping):
            raise AvatarVisualIntakeV2Error("media authorization record is invalid")
        media_id = _safe_id(value.get("media_authorization_id"), "media authorization record id")
        if media_id in by_id:
            raise AvatarVisualIntakeV2Error("media authorization record ID is duplicated")
        by_id[media_id] = value
    results: list[dict[str, Any]] = []
    physical_keys: set[str] = set()
    for index, media_id in enumerate(ids, start=1):
        authorization = by_id.get(media_id)
        if authorization is None:
            raise AvatarVisualIntakeV2Error("registered authority lacks requested media record")
        required = {
            "media_authorization_id",
            "opaque_media_id",
            "media_kind",
            "project_relative_path",
            "sha256",
            "selected_subject_event_sha256",
            "provenance_record",
        }
        kind = _text(authorization.get("media_kind"))
        if kind == "verified_video_sample_frame":
            required |= {"extractor_receipt_path", "extractor_receipt_sha256"}
        if set(authorization) != required:
            raise AvatarVisualIntakeV2Error(f"media authorization {media_id} schema mismatch")
        if _text(authorization.get("selected_subject_event_sha256")) != subject_authority["event_sha256"]:
            raise AvatarVisualIntakeV2Error("media is not bound to the selected subject event")
        path = _private_project_file(root, authorization.get("project_relative_path"), "authorized media path")
        source_size = path.stat().st_size
        if source_size <= 0 or source_size > MAX_IMAGE_BYTES:
            raise AvatarVisualIntakeV2Error("authorized media byte size is outside bounds")
        data = path.read_bytes()
        digest = _exact_sha(authorization.get("sha256"), "authorized media sha256")
        if _sha256_bytes(data) != digest:
            raise AvatarVisualIntakeV2Error("authorized media SHA-256 mismatch")
        image_info = _decode_image_bytes(data, path.suffix, "authorized media")
        opaque_id = _safe_id(authorization.get("opaque_media_id"), "opaque media id")
        record: dict[str, Any] = {
            "media_authorization_id": media_id,
            "opaque_media_id": opaque_id,
            "media_kind": kind,
            "project_relative_path": path.relative_to(root).as_posix(),
            "sha256": digest,
            "byte_size": len(data),
            "decoded_image": image_info,
            "selected_subject_event_sha256": subject_authority["event_sha256"],
            "provenance": _provenance_record(
                authorization.get("provenance_record"), f"media {media_id} provenance"
            ),
        }
        if kind == "verified_video_sample_frame":
            receipt = _video_receipt(root, authorization, path, digest, image_info)
            record["video_sample_receipt"] = receipt
            physical_payload = {
                "parent_video_sha256": receipt["parent_video_sha256"],
                "stream_id": receipt["stream_id"],
                "actual_pts": receipt["actual_pts"],
                "frame_index": receipt["frame_index"],
                "frame_sha256": digest,
            }
        elif kind == "image":
            physical_payload = {
                # Identical bytes copied or hard-linked under a second alias are
                # still one physical observation for contradiction counting.
                # The authority-bound path remains in the record, but cannot
                # manufacture a second evidentiary source.
                "sha256": digest,
            }
        else:
            raise AvatarVisualIntakeV2Error("media kind is not allowed")
        physical_id = canonical_sha256(physical_payload)
        if physical_id in physical_keys:
            raise AvatarVisualIntakeV2Error("duplicate aliases name the same physical source")
        physical_keys.add(physical_id)
        record["physical_source_id"] = physical_id
        results.append(record)
    opaque_ids = [item["opaque_media_id"] for item in results]
    if len(opaque_ids) != len(set(opaque_ids)):
        raise AvatarVisualIntakeV2Error("opaque media IDs are duplicated")
    return results


OBSERVATION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "coverage",
        "identity_status",
        "maturity_inference",
        "subject_binding_id",
        "observations",
        "contradictions",
        "suggestions",
        "global_uncertainties",
        "mutation_requested",
    ],
    "properties": {
        "schema_version": {"const": 2},
        "coverage": {"const": "BOUND_STILLS_AND_VERIFIED_VIDEO_SAMPLE_FRAMES_ONLY"},
        "identity_status": {"const": "OWNER_SELECTED_SCOPE_NOT_MODEL_IDENTIFIED"},
        "maturity_inference": {"const": False},
        "subject_binding_id": {"type": "string"},
        "observations": {"type": "array", "maxItems": 48},
        "contradictions": {"type": "array", "maxItems": 16},
        "suggestions": {"type": "object"},
        "global_uncertainties": {"type": "array", "maxItems": 16},
        "mutation_requested": {"const": False},
    },
}


def _inert_request_descriptor(plan: Mapping[str, Any]) -> dict[str, Any]:
    source_bindings = []
    for item in plan["source_items"]:
        binding = {
            "opaque_media_id": item["opaque_media_id"],
            "physical_source_id": item["physical_source_id"],
            "sha256": item["sha256"],
            "media_kind": item["media_kind"],
        }
        if item["media_kind"] == "verified_video_sample_frame":
            receipt = item["video_sample_receipt"]
            binding.update(
                {
                    "parent_video_sha256": receipt["parent_video_sha256"],
                    "stream_id": receipt["stream_id"],
                    "actual_pts": receipt["actual_pts"],
                    "actual_timestamp_seconds": receipt["actual_timestamp_seconds"],
                    "frame_index": receipt["frame_index"],
                }
            )
        source_bindings.append(binding)
    subject_binding_id = plan["subject_authority"]["event_id"]
    prompt = (
        "Return only JSON matching the supplied schema. Analyze only the listed, hash-bound "
        "private still bytes. Video coverage is limited to the exact registered samples and "
        "excludes every unsampled interval. Subject binding ID is "
        f"{subject_binding_id}. Robert selected that scope; do not identify a face. Canonical "
        "profile authority determines maturity and body lane; never infer either from appearance. "
        "Every observation must cite exact source bindings and state uncertainty. Free text is "
        "untrusted non-executable evidence. Return only observations, contradictions, and "
        "morph/material/hair suggestions; never request mutation, activation, assignment, or "
        "publication. Sources: "
        + json.dumps(source_bindings, sort_keys=True, separators=(",", ":"))
    )
    return {
        "status": "INERT_DESCRIPTOR_NOT_SENT",
        "method": "POST",
        "endpoint": OLLAMA_CHAT_ENDPOINT,
        "required_model_preflight": {
            "show_endpoint": "http://127.0.0.1:11434/api/show",
            "tags_endpoint": "http://127.0.0.1:11434/api/tags",
            "model": QWEN_VISUAL_MODEL,
            "digest": QWEN_VISUAL_DIGEST,
            "vision_capability_required": True,
            "alternate_model_or_digest_allowed": False,
            "preflight_implemented_or_executed_here": False,
        },
        "future_worker_bounds_not_implemented_here": {
            "request_timeout_required": True,
            "post_response_authority_revalidation_required": True,
            "exact_model_unload_and_vram_release_required": True,
            "free_text_to_authoring_translation_allowed": False,
        },
        "payload_template": {
            "model": QWEN_VISUAL_MODEL,
            "stream": False,
            "think": False,
            "keep_alive": 0,
            "options": {"temperature": 0},
            "format": OBSERVATION_JSON_SCHEMA,
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": "Produce bounded reconstruction observations for the registered sources.",
                    "images": [
                        f"__BASE64_OF_EXACT_LOCKED_BYTES_FOR_{item['opaque_media_id']}__"
                        for item in plan["source_items"]
                    ],
                },
            ],
        },
        "model_execution_performed": False,
        "source_bytes_embedded_in_plan": False,
        "same_locked_bytes_required_for_images_array": True,
    }


def prepare_avatar_visual_intake_v2(
    project_root: Path,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a deterministic inert plan from external registered authority."""

    root = project_root.resolve(strict=True)
    required_request = {
        "candidate_id",
        "subject_id",
        "model",
        "model_digest",
        "owner_authority_id",
        "media_authorization_ids",
    }
    if set(request) != required_request:
        raise AvatarVisualIntakeV2Error("v2 request has the wrong schema")
    candidate_id = _safe_id(request.get("candidate_id"), "candidate_id")
    subject_id = _safe_id(request.get("subject_id"), "subject_id")
    authority_id = _safe_id(request.get("owner_authority_id"), "owner_authority_id")
    model, digest = require_exact_qwen35_selection(
        request.get("model"), request.get("model_digest")
    )
    contract = _load_contract(root)
    loaded_authority = _load_registered_owner_authority(root, authority_id, contract)
    authority = _mapping(loaded_authority.get("artifact"), "registered owner authority")
    profile = _profile_route(root, candidate_id, subject_id, authority)
    subject = _subject_authority(
        authority,
        authority_id=authority_id,
        candidate_id=candidate_id,
        subject_id=subject_id,
        profile_route=profile,
    )
    corrections = _correction_authority(root, candidate_id, profile, authority)
    if corrections["latest_continuity_event_id"]:
        canonical = _mapping(authority.get("canonical_binding"), "authority canonical binding")
        if (
            subject["selected_timepoint"].casefold()
            != _text(canonical.get("resolved_selected_timepoint")).casefold()
        ):
            raise AvatarVisualIntakeV2Error(
                "owner subject timepoint conflicts with reconciled continuity correction"
            )
    source_items = _media_sources(
        root,
        _sequence(request.get("media_authorization_ids"), "media_authorization_ids"),
        subject,
        authority,
    )
    request_binding = {
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "model": model,
        "model_digest": digest,
        "owner_authority_id": authority_id,
        "media_authorization_ids": [item["media_authorization_id"] for item in source_items],
    }
    plan: dict[str, Any] = {
        "schema_version": 2,
        "route_id": ROUTE_ID,
        "request_binding": request_binding,
        "contract_binding": {
            "path": contract["path"],
            "sha256": contract["sha256"],
            "contract_id": CONTRACT_ID,
        },
        "model_identity": {"model": model, "digest": digest},
        "registered_owner_authority": {
            "authority_id": authority_id,
            "artifact_path": loaded_authority["artifact_path"],
            "artifact_sha256": loaded_authority["artifact_sha256"],
            "registry_path": loaded_authority["registry_path"],
            "registry_sha256": loaded_authority["registry_sha256"],
        },
        "profile_authority": profile,
        "subject_authority": subject,
        "correction_authority": corrections,
        "source_items": source_items,
        "coverage": {
            "still_images": True,
            "video_samples_require_registered_extractor_receipt": True,
            "full_video_viewing_claim_allowed": False,
            "unsampled_intervals_observed": False,
            "duplicate_physical_sources_allowed": False,
        },
        "output_boundary": {
            "free_text_is_untrusted_non_executable_evidence": True,
            "model_to_authoring_translation_implemented": False,
            "direct_geometry_or_body_mutation_allowed": False,
            "runtime_activation_allowed": False,
            "assignment_allowed": False,
            "publication_allowed": False,
            "owner_review_required": True,
        },
        "execution": {
            "status": "STATIC_INERT_PREPARATION_ONLY",
            "ollama_called": False,
            "gpu_used": False,
            "video_decoder_called": False,
            "blender_called": False,
            "body_mutated": False,
            "rehash_and_lock_same_image_bytes_required_before_future_encoding": True,
            "external_authority_revalidation_required_after_future_response": True,
        },
    }
    plan["ollama_request_descriptor"] = _inert_request_descriptor(plan)
    plan["plan_sha256"] = canonical_sha256(plan)
    return plan


def _plan_integrity(plan: Mapping[str, Any]) -> None:
    if plan.get("schema_version") != 2 or plan.get("route_id") != ROUTE_ID:
        raise PreparedPlanDriftError("prepared plan identity mismatch")
    stored = _exact_sha(plan.get("plan_sha256"), "prepared plan sha256")
    payload = dict(plan)
    payload.pop("plan_sha256", None)
    if canonical_sha256(payload) != stored:
        raise PreparedPlanDriftError("prepared plan content hash mismatch")
    contract = _mapping(plan.get("contract_binding"), "prepared plan contract binding")
    if _text(contract.get("path")) != CONTRACT_RELATIVE_PATH.as_posix() or _text(
        contract.get("sha256")
    ) != CONTRACT_SHA256:
        raise PreparedPlanDriftError("prepared plan is not bound to the v2 contract")
    model = _mapping(plan.get("model_identity"), "prepared plan model identity")
    require_exact_qwen35_selection(model.get("model"), model.get("digest"))


def revalidate_prepared_plan_v2(project_root: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild from current external authority; any drift invalidates the plan."""

    try:
        _plan_integrity(plan)
        request = _mapping(plan.get("request_binding"), "prepared plan request binding")
        current = prepare_avatar_visual_intake_v2(project_root, request)
    except Exception as exc:
        if isinstance(exc, PreparedPlanDriftError):
            raise
        raise PreparedPlanDriftError(
            f"prepared plan external authority/source revalidation failed ({type(exc).__name__})"
        ) from exc
    if current["plan_sha256"] != plan["plan_sha256"]:
        raise PreparedPlanDriftError("prepared plan no longer matches current external authority or sources")
    return {
        "status": "CURRENT_EXTERNAL_AUTHORITY_AND_SOURCES_MATCH",
        "plan_sha256": plan["plan_sha256"],
        "contract_sha256": CONTRACT_SHA256,
        "owner_authority_sha256": current["registered_owner_authority"]["artifact_sha256"],
        "profile_sha256": current["profile_authority"]["profile_sha256"],
        "correction_memory_sha256": current["correction_authority"]["sha256"],
        "source_sha256": [item["sha256"] for item in current["source_items"]],
    }


def lock_visual_source_bytes_v2(
    project_root: Path,
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Read, decode, and hash the exact image bytes a future worker must encode."""

    root = project_root.resolve(strict=True)
    revalidation = revalidate_prepared_plan_v2(root, plan)
    locked: dict[str, bytes] = {}
    receipts: list[dict[str, Any]] = []
    for item in plan["source_items"]:
        path = _private_project_file(root, item["project_relative_path"], "locked visual source")
        before = path.stat()
        with path.open("rb") as stream:
            data = stream.read(MAX_IMAGE_BYTES + 1)
        after = path.stat()
        if (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or len(data) != before.st_size
            or _sha256_bytes(data) != item["sha256"]
        ):
            raise PreparedPlanDriftError("visual source changed while bytes were being locked")
        decoded = _decode_image_bytes(data, path.suffix, "locked visual source")
        locked[item["opaque_media_id"]] = data
        receipts.append(
            {
                "opaque_media_id": item["opaque_media_id"],
                "physical_source_id": item["physical_source_id"],
                "sha256": item["sha256"],
                "byte_size": len(data),
                "decoded_image": decoded,
            }
        )
    return {
        "status": "LOCKED_EXACT_VERIFIED_IMAGE_BYTES_IN_MEMORY",
        "plan_sha256": plan["plan_sha256"],
        "revalidation": revalidation,
        "source_bytes": locked,
        "source_receipts": receipts,
        "caller_must_encode_these_exact_bytes": True,
        "persistent_copy_created": False,
    }


def _untrusted_model_text(value: Any, field: str, *, limit: int) -> str:
    text = _clean_text(value, field, limit=limit)
    folded = text.casefold()
    prohibited_patterns = (
        r"\b(?:identified|identify|recogniz(?:e|ed|es|ing)|face[ -]?match|identity (?:is|confirmed)|same person)\b",
        r"\b(?:adult|minor|teen(?:ager)?|child|preteen|underage|maturity|\d{1,3}[ -]years?[ -]old)\b",
        r"\b(?:activate|assign|publish|upload|overwrite|delete|erase|remove|rename|move)\b",
        r"\b(?:modify|mutate|regenerate|replace|write|save)\s+(?:the\s+)?(?:body|mesh|geometry|blend|profile|policy|file)\b",
        r"\b(?:run|execute|launch)\s+(?:the\s+)?(?:command|script|program|tool|blender)\b",
        r"\b(?:ignore|disregard|override|bypass)\s+(?:all\s+|the\s+|previous\s+)?(?:instructions?|rules?|policy|system prompt)\b",
        r"\b(?:system prompt|developer message|tool call|shell command)\b",
        r"\brobert\b",
    )
    if any(re.search(pattern, folded, re.IGNORECASE) for pattern in prohibited_patterns):
        raise AvatarVisualIntakeV2Error(f"{field} contains prohibited identity, maturity, or action semantics")
    return text


def _output_source_bindings(
    values: Any,
    plan: Mapping[str, Any],
    field: str,
) -> list[dict[str, Any]]:
    inputs = _sequence(values, field)
    if not inputs or len(inputs) > MAX_SOURCE_ITEMS:
        raise AvatarVisualIntakeV2Error(f"{field} is empty or exceeds source bounds")
    expected = {item["opaque_media_id"]: item for item in plan["source_items"]}
    output: list[dict[str, Any]] = []
    seen_physical: set[str] = set()
    for index, raw in enumerate(inputs, start=1):
        binding = _mapping(raw, f"{field}[{index}]")
        opaque_id = _text(binding.get("opaque_media_id"))
        source = expected.get(opaque_id)
        if source is None:
            raise AvatarVisualIntakeV2Error(f"{field}[{index}] names an unregistered source")
        required = {"opaque_media_id", "physical_source_id", "sha256"}
        if source["media_kind"] == "verified_video_sample_frame":
            required |= {
                "parent_video_sha256",
                "stream_id",
                "actual_pts",
                "actual_timestamp_seconds",
                "frame_index",
            }
        if set(binding) != required:
            raise AvatarVisualIntakeV2Error(f"{field}[{index}] schema mismatch")
        if _text(binding.get("sha256")) != source["sha256"] or _text(
            binding.get("physical_source_id")
        ) != source["physical_source_id"]:
            raise AvatarVisualIntakeV2Error(f"{field}[{index}] exact source binding mismatch")
        normalized = {
            "opaque_media_id": opaque_id,
            "physical_source_id": source["physical_source_id"],
            "sha256": source["sha256"],
        }
        if source["media_kind"] == "verified_video_sample_frame":
            receipt = source["video_sample_receipt"]
            for key in (
                "parent_video_sha256",
                "stream_id",
                "actual_pts",
                "actual_timestamp_seconds",
                "frame_index",
            ):
                if binding.get(key) != receipt[key]:
                    raise AvatarVisualIntakeV2Error(f"{field}[{index}] video sample binding mismatch")
                normalized[key] = receipt[key]
        if source["physical_source_id"] not in seen_physical:
            output.append(normalized)
            seen_physical.add(source["physical_source_id"])
    return output


def _validate_model_output(
    raw: Any,
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(raw, str):
        if len(raw.encode("utf-8")) > 131_072:
            raise AvatarVisualIntakeV2Error("model output exceeds the byte bound")
        try:
            output = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AvatarVisualIntakeV2Error("model output is not strict JSON") from exc
    else:
        output = raw
    output = _mapping(output, "model output")
    required = set(OBSERVATION_JSON_SCHEMA["required"])
    if set(output) != required or output.get("schema_version") != 2:
        raise AvatarVisualIntakeV2Error("model output top-level schema mismatch")
    if output.get("coverage") != "BOUND_STILLS_AND_VERIFIED_VIDEO_SAMPLE_FRAMES_ONLY":
        raise AvatarVisualIntakeV2Error("model output coverage claim is invalid")
    if output.get("identity_status") != "OWNER_SELECTED_SCOPE_NOT_MODEL_IDENTIFIED":
        raise AvatarVisualIntakeV2Error("model output identity status is invalid")
    if output.get("maturity_inference") is not False or output.get("mutation_requested") is not False:
        raise AvatarVisualIntakeV2Error("model output attempted maturity inference or mutation")
    if _text(output.get("subject_binding_id")) != plan["subject_authority"]["event_id"]:
        raise AvatarVisualIntakeV2Error("model output subject binding ID mismatch")

    observations_raw = _sequence(output.get("observations"), "observations")
    if len(observations_raw) > 48:
        raise AvatarVisualIntakeV2Error("observations exceed bounds")
    observations: list[dict[str, Any]] = []
    observation_ids: set[str] = set()
    for index, raw_observation in enumerate(observations_raw, start=1):
        item = _mapping(raw_observation, f"observations[{index}]")
        if set(item) != {
            "observation_id",
            "category",
            "description",
            "confidence",
            "uncertainty",
            "source_bindings",
        }:
            raise AvatarVisualIntakeV2Error(f"observations[{index}] schema mismatch")
        observation_id = _safe_id(item.get("observation_id"), "observation_id")
        if observation_id in observation_ids:
            raise AvatarVisualIntakeV2Error("observation IDs are duplicated")
        observation_ids.add(observation_id)
        category = _text(item.get("category"))
        confidence = _text(item.get("confidence"))
        if category not in OBSERVATION_CATEGORIES or confidence not in CONFIDENCE_LEVELS:
            raise AvatarVisualIntakeV2Error("observation category or confidence is invalid")
        observations.append(
            {
                "observation_id": observation_id,
                "category": category,
                "description": _untrusted_model_text(item.get("description"), "observation description", limit=500),
                "confidence": confidence,
                "uncertainty": _untrusted_model_text(item.get("uncertainty"), "observation uncertainty", limit=300),
                "source_bindings": _output_source_bindings(item.get("source_bindings"), plan, "observation source bindings"),
            }
        )

    contradictions_raw = _sequence(output.get("contradictions"), "contradictions")
    if len(contradictions_raw) > 16:
        raise AvatarVisualIntakeV2Error("contradictions exceed bounds")
    contradictions: list[dict[str, Any]] = []
    for index, raw_contradiction in enumerate(contradictions_raw, start=1):
        item = _mapping(raw_contradiction, f"contradictions[{index}]")
        if set(item) != {"field", "summary", "source_bindings"}:
            raise AvatarVisualIntakeV2Error(f"contradictions[{index}] schema mismatch")
        bindings = _output_source_bindings(item.get("source_bindings"), plan, "contradiction source bindings")
        if len({entry["physical_source_id"] for entry in bindings}) < 2:
            raise AvatarVisualIntakeV2Error("contradiction requires two distinct physical sources")
        contradictions.append(
            {
                "field": _untrusted_model_text(item.get("field"), "contradiction field", limit=80),
                "summary": _untrusted_model_text(item.get("summary"), "contradiction summary", limit=500),
                "source_bindings": bindings,
            }
        )

    suggestions_input = _mapping(output.get("suggestions"), "suggestions")
    if set(suggestions_input) != set(SUGGESTION_GROUPS):
        raise AvatarVisualIntakeV2Error("suggestion groups are invalid")
    suggestions: dict[str, list[dict[str, Any]]] = {}
    suggestion_ids: set[str] = set()
    for group in SUGGESTION_GROUPS:
        group_input = _sequence(suggestions_input.get(group), f"suggestions.{group}")
        if len(group_input) > 16:
            raise AvatarVisualIntakeV2Error(f"suggestions.{group} exceeds bounds")
        group_output: list[dict[str, Any]] = []
        for index, raw_suggestion in enumerate(group_input, start=1):
            item = _mapping(raw_suggestion, f"suggestions.{group}[{index}]")
            if set(item) != {
                "suggestion_id",
                "description",
                "based_on_observation_ids",
                "confidence",
                "uncertainty",
            }:
                raise AvatarVisualIntakeV2Error(f"suggestions.{group}[{index}] schema mismatch")
            suggestion_id = _safe_id(item.get("suggestion_id"), "suggestion_id")
            if suggestion_id in suggestion_ids:
                raise AvatarVisualIntakeV2Error("suggestion IDs are duplicated")
            suggestion_ids.add(suggestion_id)
            references = [
                _safe_id(value, "suggestion observation reference")
                for value in _sequence(item.get("based_on_observation_ids"), "suggestion observation IDs")
            ]
            if not references or any(value not in observation_ids for value in references):
                raise AvatarVisualIntakeV2Error("suggestion cites an unknown observation")
            confidence = _text(item.get("confidence"))
            if confidence not in CONFIDENCE_LEVELS:
                raise AvatarVisualIntakeV2Error("suggestion confidence is invalid")
            group_output.append(
                {
                    "suggestion_id": suggestion_id,
                    "description": _untrusted_model_text(item.get("description"), "suggestion description", limit=500),
                    "based_on_observation_ids": list(dict.fromkeys(references)),
                    "confidence": confidence,
                    "uncertainty": _untrusted_model_text(item.get("uncertainty"), "suggestion uncertainty", limit=300),
                    "translation_status": "UNTRUSTED_REQUIRES_OWNER_REVIEW_AND_SEPARATE_ALLOWLISTED_TRANSLATOR",
                }
            )
        suggestions[group] = group_output

    uncertainties = [
        _untrusted_model_text(value, "global uncertainty", limit=300)
        for value in _sequence(output.get("global_uncertainties"), "global uncertainties")
    ]
    if len(uncertainties) > 16:
        raise AvatarVisualIntakeV2Error("global uncertainties exceed bounds")
    result: dict[str, Any] = {
        "schema_version": 2,
        "coverage": output["coverage"],
        "identity_status": output["identity_status"],
        "maturity_inference": False,
        "subject_binding_id": output["subject_binding_id"],
        "observations": observations,
        "contradictions": contradictions,
        "suggestions": suggestions,
        "global_uncertainties": uncertainties,
        "mutation_requested": False,
        "authoritative_template_lane": plan["profile_authority"]["template_lane"],
        "free_text_executable": False,
        "model_to_authoring_translation_implemented": False,
        "runtime_activation_allowed": False,
        "owner_review_required": True,
        "source_plan_sha256": plan["plan_sha256"],
    }
    result["validated_output_sha256"] = canonical_sha256(result)
    return result


def _dedicated_existing_plan_path(root: Path, value: Path) -> Path:
    try:
        relative = value if not value.is_absolute() else value.resolve().relative_to(root)
    except (OSError, ValueError) as exc:
        raise ProtectedOutputError("plan path is outside the project") from exc
    if relative.parent != PLAN_ROOT or relative.suffix.casefold() != ".json":
        raise ProtectedOutputError("plan path is outside the dedicated v2 plan root")
    return _regular_project_file(root, relative, "prepared plan path")


def consume_visual_observation_output_v2(
    project_root: Path,
    plan_path: Path,
    raw_output: Any,
) -> dict[str, Any]:
    """Revalidate external authority before and after consuming model evidence."""

    root = project_root.resolve(strict=True)
    path = _dedicated_existing_plan_path(root, plan_path)
    plan = _read_json_object(path, "prepared plan")
    before = revalidate_prepared_plan_v2(root, plan)
    locked = lock_visual_source_bytes_v2(root, plan)
    result = _validate_model_output(raw_output, plan)
    after = revalidate_prepared_plan_v2(root, plan)
    result["consumption_receipt"] = {
        "plan_path": path.relative_to(root).as_posix(),
        "plan_sha256": plan["plan_sha256"],
        "authority_before": before,
        "authority_after": after,
        "locked_source_receipts": locked["source_receipts"],
        "same_source_bytes_revalidated": True,
        "persistent_source_copy_created": False,
    }
    result["validated_output_sha256"] = canonical_sha256(
        {key: value for key, value in result.items() if key != "validated_output_sha256"}
    )
    return result


def _exclusive_json_write(
    root: Path,
    relative_root: Path,
    output_name: str,
    value: Mapping[str, Any],
) -> Path:
    name = _safe_id(output_name, "output_name")
    directory = root / relative_root
    current = directory
    while current != root:
        if current.exists() and current.is_symlink():
            raise ProtectedOutputError("dedicated output root may not traverse a symlink")
        current = current.parent
    directory.mkdir(parents=True, exist_ok=True)
    resolved_directory = directory.resolve(strict=True)
    if resolved_directory != (root / relative_root).resolve():
        raise ProtectedOutputError("dedicated output root resolved unexpectedly")
    destination = resolved_directory / f"{name}.json"
    if destination.exists():
        raise ProtectedOutputError("existing output files are never overwritten")
    encoded = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(destination, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    return destination


def write_plan_no_clobber_v2(
    project_root: Path,
    output_name: str,
    plan: Mapping[str, Any],
) -> Path:
    _plan_integrity(plan)
    return _exclusive_json_write(project_root.resolve(strict=True), PLAN_ROOT, output_name, plan)


def write_validated_output_no_clobber_v2(
    project_root: Path,
    output_name: str,
    validated_output: Mapping[str, Any],
) -> Path:
    if validated_output.get("runtime_activation_allowed") is not False:
        raise ProtectedOutputError("validated output does not preserve inactive state")
    return _exclusive_json_write(
        project_root.resolve(strict=True),
        VALIDATED_OUTPUT_ROOT,
        output_name,
        validated_output,
    )
