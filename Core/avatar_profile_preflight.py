"""Read-only canonical identity, version, and maturity preflight for avatars.

The Avatar Builder receives requests from several generations of TemporaryAI
profiles.  Those profiles do not all use the same schema, and an avatar request
may legitimately use a body/variant alias instead of the profile directory ID.
This module resolves only aliases that are explicitly registered, binds the
request to the exact canonical profile, and stops fictional body authoring when
the selected version or maturity lane is blank.

It deliberately does not repair or rewrite a TemporaryAI profile.  In
particular, it never infers adulthood from an actor, performer, filename,
costume, or reference model.  An unresolved candidate receives the doll-safe
safety fallback, but that fallback is not authority to author a body until the
profile has an explicit version and reviewed maturity decision.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


REGISTRY_RELATIVE_PATH = Path(
    "Avatar/avatar_builder/policies/candidate_identity_variant_registry.json"
)
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

ADULT = "adult"
NON_ADULT_DOLL_SAFE = "non_adult_doll_safe"
UNRESOLVED_DOLL_SAFE = "unresolved_doll_safe"
NONHUMAN_EMBODIMENT_UNRESOLVED = "nonhuman_embodiment_unresolved"

CONFIRMED_ADULT_TOPOLOGY = "confirmed_adult_topology"
NON_ADULT_DOLL_SAFE_TOPOLOGY = "non_adult_doll_safe_topology"
BLOCKED_NONHUMAN_EMBODIMENT = "blocked_nonhuman_embodiment"

MATURITY_LANES = frozenset(
    {
        ADULT,
        NON_ADULT_DOLL_SAFE,
        UNRESOLVED_DOLL_SAFE,
        NONHUMAN_EMBODIMENT_UNRESOLVED,
    }
)
FICTIONAL_IDENTITY_CLASSES = frozenset(
    {"fictional_character", "fictional_android", "fictional_nonhuman"}
)
ADULT_REQUEST_CLASSES = frozenset(
    {"adult", "adult_confirmed", "confirmed_adult"}
)
AGE_UP_PRESENTATION_REQUEST_CLASSES = frozenset({"adult_aged_up_variant"})
NON_ADULT_REQUEST_CLASSES = frozenset(
    {
        "non_adult",
        "minor",
        "teen",
        "child",
        "non_adult_doll_safe",
        "unresolved",
        "unresolved_doll_safe",
    }
)


class AvatarProfilePreflightError(ValueError):
    """The registry or canonical profile cannot be evaluated safely."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _text(value).lower()).strip("_")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AvatarProfilePreflightError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise AvatarProfilePreflightError(f"JSON must be an object: {path}")
    return value


def _regular_file_below(root: Path, relative: Path, *, required: bool) -> Path | None:
    if relative.is_absolute() or ".." in relative.parts:
        raise AvatarProfilePreflightError("preflight path must be project-relative")
    unresolved = root / relative
    current = unresolved
    while True:
        if current.is_symlink():
            raise AvatarProfilePreflightError(f"symlinked preflight path: {relative}")
        if current == root or current.parent == current:
            break
        current = current.parent
    if not unresolved.exists():
        if required:
            raise AvatarProfilePreflightError(f"required preflight file is missing: {relative}")
        return None
    resolved = unresolved.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AvatarProfilePreflightError(f"preflight path escapes project: {relative}") from exc
    if not resolved.is_file():
        raise AvatarProfilePreflightError(f"preflight path is not a regular file: {relative}")
    return resolved


def _validated_id(value: Any, field: str) -> str:
    candidate = _text(value)
    if not SAFE_ID_RE.fullmatch(candidate):
        raise AvatarProfilePreflightError(f"{field} is not a safe identifier")
    return candidate


def _extract_path(source: Mapping[str, Any], raw_path: Any) -> Any:
    if not isinstance(raw_path, Sequence) or isinstance(raw_path, (str, bytes)):
        raise AvatarProfilePreflightError("registry binding path must be a JSON-key list")
    current: Any = source
    for raw_key in raw_path:
        if isinstance(current, Mapping):
            key = _text(raw_key)
            if not key or key not in current:
                return None
            current = current[key]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            if isinstance(raw_key, bool):
                return None
            try:
                index = int(raw_key)
            except (TypeError, ValueError):
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
        else:
            return None
    return current


def _load_registry(root: Path) -> tuple[dict[str, Any], Path, str, dict[str, dict[str, Any]]]:
    registry_path = _regular_file_below(root, REGISTRY_RELATIVE_PATH, required=True)
    assert registry_path is not None
    registry = _read_json_object(registry_path)
    if registry.get("schema_version") != 1:
        raise AvatarProfilePreflightError("unsupported candidate identity registry schema")
    records = registry.get("candidates")
    if not isinstance(records, list):
        raise AvatarProfilePreflightError("candidate identity registry has no candidate list")

    aliases: dict[str, dict[str, Any]] = {}
    for raw_record in records:
        if not isinstance(raw_record, dict):
            raise AvatarProfilePreflightError("candidate identity registry record is not an object")
        canonical_id = _validated_id(
            raw_record.get("canonical_candidate_id"), "canonical_candidate_id"
        )
        keys = [canonical_id]
        raw_aliases = raw_record.get("aliases", [])
        if not isinstance(raw_aliases, list):
            raise AvatarProfilePreflightError(f"aliases are invalid for {canonical_id}")
        keys.extend(_validated_id(value, "candidate alias") for value in raw_aliases)
        if len(set(keys)) != len(keys):
            raise AvatarProfilePreflightError(f"duplicate aliases within record: {canonical_id}")
        for key in keys:
            if key in aliases:
                raise AvatarProfilePreflightError(f"candidate alias collision: {key}")
            aliases[key] = raw_record
    return registry, registry_path, _sha256_file(registry_path), aliases


def identity_registry_available(project_root: Path) -> bool:
    """Return whether this project has the canonical preflight registry."""

    root = project_root.resolve()
    try:
        return _regular_file_below(root, REGISTRY_RELATIVE_PATH, required=False) is not None
    except AvatarProfilePreflightError:
        return True


def _binding_value(
    binding: Mapping[str, Any],
    *,
    profile: Mapping[str, Any],
    creation_request: Mapping[str, Any],
) -> Any:
    source_name = _normalized(binding.get("source"))
    if source_name == "temporary_ai_profile":
        source = profile
    elif source_name == "avatar_only_variant_profile":
        source = profile
    elif source_name == "creation_request":
        source = creation_request
    else:
        raise AvatarProfilePreflightError("registry binding source is invalid")
    return _extract_path(source, binding.get("path"))


def _binding_matches(binding: Mapping[str, Any], value: Any) -> bool:
    accepted_values = binding.get("accepted_values")
    if isinstance(accepted_values, list):
        return value in accepted_values
    if "expected" in binding:
        return value == binding.get("expected")
    expected_text = binding.get("expected_contains_text")
    if isinstance(expected_text, str) and expected_text:
        return expected_text in _text(value)
    return False


def _validate_avatar_only_source_bindings(
    root: Path, profile: Mapping[str, Any]
) -> tuple[list[dict[str, str]], list[str]]:
    raw_bindings = profile.get("source_bindings")
    failures: list[str] = []
    results: list[dict[str, str]] = []
    if not isinstance(raw_bindings, list) or not raw_bindings:
        return [], ["avatar_only_variant_source_bindings_missing"]
    for index, raw_binding in enumerate(raw_bindings):
        if not isinstance(raw_binding, Mapping):
            failures.append(f"avatar_only_source_binding_{index}_invalid")
            continue
        raw_path = _text(raw_binding.get("path"))
        expected_sha = _text(raw_binding.get("sha256")).lower()
        if not SHA256_RE.fullmatch(expected_sha):
            failures.append(f"avatar_only_source_binding_{index}_sha256_invalid")
            continue
        try:
            source_path = _regular_file_below(root, Path(raw_path), required=True)
        except AvatarProfilePreflightError:
            failures.append(f"avatar_only_source_binding_{index}_path_invalid")
            continue
        assert source_path is not None
        actual_sha = _sha256_file(source_path)
        if actual_sha != expected_sha:
            failures.append(f"avatar_only_source_binding_{index}_sha256_mismatch")
        results.append(
            {
                "path": source_path.relative_to(root).as_posix(),
                "sha256": actual_sha,
            }
        )
    return results, failures


def _requested_maturity_lane(value: Any) -> str:
    normalized = _normalized(value)
    if normalized in ADULT_REQUEST_CLASSES:
        return ADULT
    if normalized in AGE_UP_PRESENTATION_REQUEST_CLASSES:
        return UNRESOLVED_DOLL_SAFE
    if normalized in NON_ADULT_REQUEST_CLASSES:
        return NON_ADULT_DOLL_SAFE
    return ""


def evaluate_avatar_profile_preflight(
    project_root: Path,
    requested_candidate_id: str,
    *,
    requested_subject_id: str = "",
    requested_maturity_class: str = "",
    request_complete_adult_anatomy: bool | None = None,
) -> dict[str, Any]:
    """Evaluate one avatar request without mutating its canonical profile.

    The result is suitable for embedding in an orchestration decision.  A
    blocked result still reports the doll-safe safety fallback for unresolved
    candidates, but ``authoring_allowed`` remains false.
    """

    root = project_root.resolve(strict=True)
    requested_id = _validated_id(requested_candidate_id, "requested_candidate_id")
    registry, registry_path, registry_sha, alias_index = _load_registry(root)
    record = alias_index.get(requested_id)
    failures: list[str] = []
    if record is None:
        return {
            "schema_version": 1,
            "status": "blocked",
            "passed": False,
            "requested_candidate_id": requested_id,
            "canonical_candidate_id": "",
            "candidate_alias_used": False,
            "registry_binding_verified": False,
            "registry": {
                "path": REGISTRY_RELATIVE_PATH.as_posix(),
                "sha256": registry_sha,
            },
            "failures": ["candidate_id_not_registered"],
            "authoring_allowed": False,
            "runtime_activation_allowed": False,
        }

    canonical_id = _validated_id(
        record.get("canonical_candidate_id"), "canonical_candidate_id"
    )
    subject_id = _validated_id(record.get("subject_id"), "subject_id")
    identity_class = _normalized(record.get("identity_class"))
    variant_kind = _normalized(record.get("variant_kind"))
    if not identity_class:
        failures.append("identity_class_missing")
    if not variant_kind:
        failures.append("variant_kind_missing")

    profile_kind = _normalized(record.get("profile_kind")) or "temporary_ai"
    if profile_kind == "temporary_ai":
        profile_directory = _validated_id(
            record.get("profile_directory") or canonical_id, "profile_directory"
        )
        candidate_root = Path("TemporaryAI") / "candidates" / profile_directory
        profile_relative = candidate_root / "temporary_ai_profile.json"
        creation_relative = candidate_root / "creation_request.json"
        profile_path = _regular_file_below(root, profile_relative, required=True)
        creation_path = _regular_file_below(root, creation_relative, required=True)
        assert profile_path is not None and creation_path is not None
    elif profile_kind == "avatar_only_variant":
        raw_profile_path = _text(record.get("profile_path"))
        profile_path = _regular_file_below(root, Path(raw_profile_path), required=True)
        creation_path = None
        profile_directory = ""
        assert profile_path is not None
    else:
        raise AvatarProfilePreflightError(f"profile_kind is invalid for {canonical_id}")
    profile = _read_json_object(profile_path)
    creation_request = _read_json_object(creation_path) if creation_path else {}
    profile_sha = _sha256_file(profile_path)
    creation_sha = _sha256_file(creation_path) if creation_path else ""

    if _text(profile.get("candidate_id")) != canonical_id:
        failures.append("canonical_profile_candidate_id_mismatch")
    if creation_path:
        creation_candidate_id = _text(creation_request.get("candidate_id"))
        if creation_candidate_id and creation_candidate_id != canonical_id:
            failures.append("creation_request_candidate_id_mismatch")
    else:
        if _normalized(profile.get("profile_scope")) != "avatar_only_inactive_variant":
            failures.append("avatar_only_variant_scope_invalid")
        if profile.get("creates_temporary_ai_or_mind") is not False:
            failures.append("avatar_only_variant_mind_creation_not_excluded")
        if profile.get("runtime_activation_allowed") is not False:
            failures.append("avatar_only_variant_runtime_activation_not_false")
    if requested_subject_id and _text(requested_subject_id) != subject_id:
        failures.append("orchestration_subject_id_mismatch")

    version_policy = record.get("version_policy")
    if not isinstance(version_policy, Mapping):
        raise AvatarProfilePreflightError(f"version_policy is invalid for {canonical_id}")
    version_required = version_policy.get("required") is True
    version_value: Any = None
    version_binding = version_policy.get("binding")
    if isinstance(version_binding, Mapping):
        version_value = _binding_value(
            version_binding,
            profile=profile,
            creation_request=creation_request,
        )
        if not _binding_matches(version_binding, version_value):
            failures.append("fictional_version_binding_mismatch")
    elif version_required:
        failures.append("fictional_version_binding_missing")
    selected_version = _text(version_value)
    if version_required and not selected_version:
        failures.append(
            "fictional_version_blank"
            if identity_class in FICTIONAL_IDENTITY_CLASSES
            else "required_version_blank"
        )

    maturity_policy = record.get("maturity_policy")
    if not isinstance(maturity_policy, Mapping):
        raise AvatarProfilePreflightError(f"maturity_policy is invalid for {canonical_id}")
    maturity_lane = _normalized(maturity_policy.get("lane"))
    if maturity_lane not in MATURITY_LANES:
        raise AvatarProfilePreflightError(f"maturity lane is invalid for {canonical_id}")
    maturity_binding = maturity_policy.get("binding")
    maturity_value: Any = None
    if isinstance(maturity_binding, Mapping):
        maturity_value = _binding_value(
            maturity_binding,
            profile=profile,
            creation_request=creation_request,
        )
        if not _binding_matches(maturity_binding, maturity_value):
            failures.append("maturity_profile_binding_mismatch")
    elif maturity_lane not in {
        UNRESOLVED_DOLL_SAFE,
        NONHUMAN_EMBODIMENT_UNRESOLVED,
    }:
        failures.append("resolved_maturity_binding_missing")

    requested_lane = _requested_maturity_lane(requested_maturity_class)
    if requested_maturity_class and not requested_lane:
        failures.append("orchestration_maturity_class_unrecognized")
    if requested_lane:
        if maturity_lane in {
            UNRESOLVED_DOLL_SAFE,
            NONHUMAN_EMBODIMENT_UNRESOLVED,
        }:
            failures.append("orchestration_maturity_conflicts_with_unresolved_profile")
        elif requested_lane != maturity_lane:
            failures.append("orchestration_maturity_lane_mismatch")

    variant_policy = record.get("adult_variant_policy", {})
    if not isinstance(variant_policy, Mapping):
        raise AvatarProfilePreflightError(f"adult_variant_policy is invalid for {canonical_id}")
    separate_adult_variant_required = variant_policy.get("separate_variant_required") is True
    if separate_adult_variant_required and (
        requested_lane == ADULT or request_complete_adult_anatomy is True
    ):
        failures.append("adult_request_requires_separate_profiled_variant")
    if request_complete_adult_anatomy is True and maturity_lane != ADULT:
        failures.append("adult_anatomy_request_not_supported_by_canonical_maturity")
    if request_complete_adult_anatomy is False and maturity_lane == ADULT:
        failures.append("confirmed_adult_cannot_be_silently_routed_to_doll_safe")
    if maturity_lane == UNRESOLVED_DOLL_SAFE:
        failures.append("maturity_unresolved_authoring_blocked")
    if maturity_lane == NONHUMAN_EMBODIMENT_UNRESOLVED:
        failures.append("nonhuman_embodiment_authoring_blocked")

    source_bindings: list[dict[str, str]] = []
    if profile_kind == "avatar_only_variant":
        source_bindings, source_binding_failures = _validate_avatar_only_source_bindings(
            root, profile
        )
        failures.extend(source_binding_failures)

    manual_review_notes = record.get("manual_review_notes", [])
    if not isinstance(manual_review_notes, list) or not all(
        isinstance(note, str) for note in manual_review_notes
    ):
        raise AvatarProfilePreflightError(f"manual_review_notes are invalid for {canonical_id}")

    failures = list(dict.fromkeys(failures))
    topology_lane = (
        CONFIRMED_ADULT_TOPOLOGY
        if maturity_lane == ADULT
        else (
            BLOCKED_NONHUMAN_EMBODIMENT
            if maturity_lane == NONHUMAN_EMBODIMENT_UNRESOLVED
            else NON_ADULT_DOLL_SAFE_TOPOLOGY
        )
    )
    return {
        "schema_version": 1,
        "status": "passed" if not failures else "blocked",
        "passed": not failures,
        "requested_candidate_id": requested_id,
        "canonical_candidate_id": canonical_id,
        "candidate_alias_used": requested_id != canonical_id,
        "registry_binding_verified": True,
        "registry": {
            "path": registry_path.relative_to(root).as_posix(),
            "sha256": registry_sha,
            "schema_version": registry.get("schema_version"),
        },
        "canonical_profile": {
            "path": profile_path.relative_to(root).as_posix(),
            "sha256": profile_sha,
            "candidate_id": _text(profile.get("candidate_id")),
            "display_name": _text(profile.get("display_name")),
            "profile_kind": profile_kind,
            "profile_directory": profile_directory,
            "mutation_performed": False,
        },
        "creation_request": {
            "path": creation_path.relative_to(root).as_posix() if creation_path else "",
            "sha256": creation_sha,
            "mutation_performed": False,
        },
        "source_bindings": source_bindings,
        "identity": {
            "subject_id": subject_id,
            "identity_class": identity_class,
            "variant_kind": variant_kind,
            "selected_version": selected_version,
            "version_required": version_required,
            "version_locked": bool(selected_version) if version_required else True,
        },
        "maturity": {
            "lane": maturity_lane,
            "binding_value": maturity_value,
            "safety_topology_lane": topology_lane,
            "unresolved_falls_back_to_doll_safe": maturity_lane == UNRESOLVED_DOLL_SAFE,
            "unresolved_fallback_is_authoring_authority": False,
        },
        "adult_variant_policy": {
            "separate_variant_required": separate_adult_variant_required,
            "adult_variant_candidate_id": _text(
                variant_policy.get("adult_variant_candidate_id")
            ),
            "in_place_age_up_allowed": False,
        },
        "requested_subject_id": _text(requested_subject_id),
        "requested_maturity_class": _text(requested_maturity_class),
        "request_complete_adult_anatomy": request_complete_adult_anatomy,
        "manual_review_notes": manual_review_notes,
        "failures": failures,
        "authoring_allowed": not failures,
        "runtime_activation_allowed": False,
        "truth_note": (
            "Preflight binds an avatar request to an existing canonical profile and explicit "
            "registry decision only. It does not change the profile, infer age/version, create "
            "a body, approve a voice, or authorize activation."
        ),
    }


def evaluate_orchestration_identity_preflight(
    project_root: Path, request: Mapping[str, Any]
) -> dict[str, Any]:
    """Evaluate the identity fields declared by an orchestration request."""

    maturity_policy = request.get("maturity_policy")
    if not isinstance(maturity_policy, Mapping):
        maturity_policy = {}
    return evaluate_avatar_profile_preflight(
        project_root,
        _text(request.get("candidate_id")),
        requested_subject_id=_text(request.get("subject_id")),
        requested_maturity_class=_text(maturity_policy.get("maturity_class")),
        request_complete_adult_anatomy=(
            request.get("request_complete_adult_anatomy")
            if isinstance(request.get("request_complete_adult_anatomy"), bool)
            else None
        ),
    )


def evaluate_current_avatar_profile_batch(
    project_root: Path, *, max_candidates: int = 32
) -> dict[str, Any]:
    """Evaluate every registered current TemporaryAI profile in one bounded pass."""

    if not isinstance(max_candidates, int) or not 1 <= max_candidates <= 64:
        raise AvatarProfilePreflightError("max_candidates must be between 1 and 64")
    root = project_root.resolve(strict=True)
    registry, _, registry_sha, _ = _load_registry(root)
    records = [
        record
        for record in registry.get("candidates", [])
        if isinstance(record, Mapping)
        and _normalized(record.get("inventory_scope")) == "current_temporary_ai_profile"
    ]
    if len(records) > max_candidates:
        raise AvatarProfilePreflightError(
            f"registered current profile count {len(records)} exceeds bound {max_candidates}"
        )
    results: list[dict[str, Any]] = []
    registered_directories: set[str] = set()
    for record in records:
        canonical_id = _validated_id(
            record.get("canonical_candidate_id"), "canonical_candidate_id"
        )
        registered_directories.add(
            _validated_id(record.get("profile_directory") or canonical_id, "profile_directory")
        )
        result = evaluate_avatar_profile_preflight(root, canonical_id)
        identity = result.get("identity", {})
        maturity = result.get("maturity", {})
        profile = result.get("canonical_profile", {})
        results.append(
            {
                "canonical_candidate_id": canonical_id,
                "profile_directory": _text(profile.get("profile_directory")),
                "display_name": _text(profile.get("display_name")),
                "identity_class": _text(identity.get("identity_class")),
                "version_status": (
                    "locked"
                    if identity.get("version_locked") is True
                    else "blank_or_unresolved"
                ),
                "selected_version": _text(identity.get("selected_version")),
                "maturity_lane": _text(maturity.get("lane")),
                "topology_lane": _text(maturity.get("safety_topology_lane")),
                "authoring_allowed": result.get("authoring_allowed") is True,
                "blockers": list(result.get("failures", [])),
            }
        )

    discovered_directories = {
        path.parent.name
        for path in (root / "TemporaryAI" / "candidates").glob(
            "*/temporary_ai_profile.json"
        )
        if path.is_file() and not path.is_symlink()
    }
    excluded = {
        _validated_id(value, "excluded candidate directory")
        for value in registry.get("excluded_candidate_directories", [])
    }
    unexpected = sorted(discovered_directories - registered_directories - excluded)
    missing = sorted(registered_directories - discovered_directories)
    coverage_passed = not unexpected and not missing and len(results) == 22
    return {
        "schema_version": 1,
        "status": "complete" if coverage_passed else "coverage_blocked",
        "registry_sha256": registry_sha,
        "expected_current_profile_count": 22,
        "evaluated_profile_count": len(results),
        "coverage_passed": coverage_passed,
        "unexpected_profile_directories": unexpected,
        "missing_profile_directories": missing,
        "excluded_empty_smoke_directories": sorted(excluded),
        "profiles": results,
        "runtime_activation_allowed": False,
        "profile_mutation_performed": False,
    }
