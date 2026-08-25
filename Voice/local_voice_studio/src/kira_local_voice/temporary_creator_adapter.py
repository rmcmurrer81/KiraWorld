"""Read-only Temporary Creator to voice-design adapter.

The adapter accepts only exact registry identifiers and explicitly authored
voice-shaping fields.  It never edits an avatar profile, infers a locale from
free text, parses prose personality notes, creates audio, or activates a voice.
Missing optional shaping fields are represented as zero-affinity limitations;
missing gender, locale, role, or source attestations yields ``needs_review``.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import types
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .paths import PinnedDirectory, safe_component
from .voice_design import (
    AgeBand,
    AssignmentMode,
    AvatarSourceAttestation,
    BodyPresence,
    EraContext,
    Gender,
    IdentityKind,
    LanguageProvenance,
    VoiceDesignBrief,
)

ADAPTER_SCHEMA = "kira.local-voice.temporary-creator-adapter.v1"
COVERAGE_SCHEMA = "kira.local-voice.temporary-creator-coverage.v1"
REGISTRY_RELATIVE_PATH = Path("Avatar/avatar_builder/policies/candidate_identity_variant_registry.json")
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_COVERAGE_CANDIDATES = 32

GENERATED_EXPERT_CANDIDATES = (
    "emily_carter_ai_and_computer_programming_expert_20260605_220651",
    "jessica_hale_robotics_engineer_20260611_041314",
    "laura_mitchell_new_jersey_criminal_attorney_expert_20260605_195530",
    "ryan_hale_quantum_mechanics_expert_20260608_200749",
    "sarah_bennett_entertainment_pr_agent_expert_20260606_171637",
)

PRESERVED_VOICE_PROFILES: Mapping[str, tuple[str, str]] = {
    "kathryn_merteuil_kathryn_merteuil_20260605_213017": (
        "Voice/profiles/temp_ai/kathryn_merteuil_voice_profile.json",
        "preserve_existing",
    ),
    "ladybug_marinette_expanded_smoke": (
        "Voice/profiles/temp_ai/ladybug_voice_profile.json",
        "preserve_existing",
    ),
    "peter_parker_spider_man_no_way_home_final_suit": (
        "Voice/profiles/temp_ai/peter_parker_voice_profile.json",
        "preserve_existing",
    ),
    "kira": (
        "Voice/profiles/temp_ai/kira_voice_profile.json",
        "rollback_preserved_subject_selection_required",
    ),
}

_BCP47 = __import__("re").compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_SAFE_TRAIT = __import__("re").compile(r"^[a-z][a-z0-9_-]{0,31}$")


def _identity(info: os.stat_result) -> tuple[int, int, int, int]:
    # Windows reports different ctime values for a named-path stat and an open
    # handle to the same file, so use the stable file ID, volume, size, and
    # last-write timestamp for cross-view identity checks.
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _read_bytes_attested(path: Path) -> bytes:
    before = path.lstat()
    if _is_reparse_point(path) or not stat.S_ISREG(before.st_mode):
        raise ValidationError(f"source is not an unlinked regular file: {path.name}")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if _identity(opened) != _identity(before):
            raise ValidationError(f"source identity changed while opening: {path.name}")
        if not 0 < opened.st_size <= MAX_JSON_BYTES:
            raise ValidationError(f"source must contain 1-{MAX_JSON_BYTES} bytes")
        payload = stream.read(MAX_JSON_BYTES + 1)
        after_read = os.fstat(stream.fileno())
    after = path.lstat()
    if (
        len(payload) != opened.st_size
        or len(payload) > MAX_JSON_BYTES
        or _identity(opened) != _identity(after_read)
        or _identity(opened) != _identity(after)
        or _is_reparse_point(path)
    ):
        raise ValidationError(f"source changed while it was being read: {path.name}")
    return payload


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(_read_bytes_attested(path)).hexdigest()


def _is_reparse_point(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse_flag)


def _regular_file_below(root: Path, relative: Path, *, required: bool = True) -> Path | None:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValidationError("source path must be project-relative")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() and _is_reparse_point(cursor):
            raise ValidationError(f"source path contains a link or reparse point: {relative.as_posix()}")
    if not cursor.exists():
        if required:
            raise ValidationError(f"required source file is missing: {relative.as_posix()}")
        return None
    resolved = cursor.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValidationError("source path escapes the project root") from exc
    if not resolved.is_file() or _is_reparse_point(resolved):
        raise ValidationError(f"source is not a regular file: {relative.as_posix()}")
    return resolved


def _decode_json(payload: bytes, *, name: str) -> dict[str, Any]:
    def reject_constant(value: str) -> object:
        raise ValidationError(f"non-finite JSON number is forbidden: {value}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON key is forbidden: {key}")
            result[key] = value
        return result

    try:
        encoding = "utf-8-sig" if payload.startswith(b"\xef\xbb\xbf") else "utf-8"
        value = json.loads(
            payload.decode(encoding),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid UTF-8 JSON source: {name}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON source must be an object: {name}")
    return value


def _read_json_attested(path: Path) -> tuple[dict[str, Any], str]:
    payload = _read_bytes_attested(path)
    return _decode_json(payload, name=path.name), hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return _read_json_attested(path)[0]


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _nested(mapping: Mapping[str, Any], path: tuple[str, ...]) -> object:
    current: object = mapping
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _exact_values(
    profile: Mapping[str, Any],
    registry_record: Mapping[str, Any],
    paths: tuple[tuple[str, ...], ...],
    registry_fields: tuple[str, ...],
) -> list[str]:
    values: list[str] = []
    for path in paths:
        value = _text(_nested(profile, path))
        if value:
            values.append(value)
    for field in registry_fields:
        value = _text(registry_record.get(field))
        if value:
            values.append(value)
    return list(dict.fromkeys(values))


def _load_preflight(source: Path) -> tuple[Callable[..., dict[str, Any]], str]:
    """Execute only the exact attested preflight bytes from the trusted project root."""

    source_bytes = _read_bytes_attested(source)
    module_name = "kira_avatar_profile_preflight_for_voice"
    module = types.ModuleType(module_name)
    module.__file__ = str(source)
    try:
        executable = compile(source_bytes, str(source), "exec", dont_inherit=True)
        exec(executable, module.__dict__)
    except Exception as exc:
        raise ValidationError("trusted avatar preflight module could not be loaded") from exc
    evaluator = getattr(module, "evaluate_avatar_profile_preflight", None)
    if not callable(evaluator):
        raise ValidationError("avatar preflight evaluator is unavailable")
    return evaluator, hashlib.sha256(source_bytes).hexdigest()


class TemporaryCreatorVoiceAdapter:
    """Create a design brief only from exact, source-attested profile fields."""

    def __init__(
        self,
        project_root: Path,
        *,
        preflight_evaluator: Callable[..., dict[str, Any]] | None = None,
    ):
        self.project_root = project_root.expanduser().resolve(strict=True)
        self._root_pin = PinnedDirectory.capture(self.project_root)
        registry_path = _regular_file_below(self.project_root, REGISTRY_RELATIVE_PATH)
        assert registry_path is not None
        self._registry_path = registry_path
        self._registry_pin = PinnedDirectory.capture(registry_path.parent)
        self._registry, self._registry_sha256 = _read_json_attested(registry_path)
        self._records, self._aliases = self._index_registry(self._registry)
        preflight_path = _regular_file_below(self.project_root, Path("Core/avatar_profile_preflight.py"))
        assert preflight_path is not None
        self._preflight_path = preflight_path
        self._preflight_pin = PinnedDirectory.capture(preflight_path.parent)
        if preflight_evaluator is None:
            self._preflight, self._preflight_sha256 = _load_preflight(preflight_path)
        else:
            self._preflight = preflight_evaluator
            self._preflight_sha256 = _sha256_file(preflight_path)

    @staticmethod
    def _index_registry(
        registry: Mapping[str, Any],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        records = registry.get("candidates")
        if not isinstance(records, list) or not records:
            raise ValidationError("avatar registry has no candidate records")
        canonical: dict[str, dict[str, Any]] = {}
        aliases: dict[str, str] = {}
        for item in records:
            if not isinstance(item, dict):
                raise ValidationError("avatar registry candidate record must be an object")
            candidate_id = safe_component(item.get("canonical_candidate_id"), field="canonical_candidate_id")
            if candidate_id in canonical:
                raise ValidationError("avatar registry repeats a canonical candidate ID")
            canonical[candidate_id] = item
            names = [candidate_id]
            profile_directory = item.get("profile_directory")
            if profile_directory:
                names.append(safe_component(profile_directory, field="profile_directory"))
            raw_aliases = item.get("aliases", [])
            if not isinstance(raw_aliases, list):
                raise ValidationError("avatar registry aliases must be a list")
            names.extend(safe_component(value, field="candidate alias") for value in raw_aliases)
            for name in names:
                previous = aliases.get(name)
                if previous is not None and previous != candidate_id:
                    raise ValidationError("avatar registry contains a contradictory exact alias")
                aliases[name] = candidate_id
        return canonical, aliases

    def _assert_sources(self) -> None:
        self._root_pin.assert_unchanged()
        self._registry_pin.assert_unchanged()
        self._preflight_pin.assert_unchanged()
        if _sha256_file(self._registry_path) != self._registry_sha256:
            raise ValidationError("avatar registry changed after adapter initialization")
        if _sha256_file(self._preflight_path) != self._preflight_sha256:
            raise ValidationError("trusted avatar preflight changed after adapter initialization")

    def _resolve_record(self, requested_candidate_id: str) -> tuple[str, dict[str, Any], str | None]:
        requested = safe_component(requested_candidate_id, field="requested_candidate_id")
        canonical_id = self._aliases.get(requested)
        if canonical_id is None:
            raise ValidationError("requested candidate ID is not an exact registry ID or alias")
        alias_used = requested if requested != canonical_id else None
        return canonical_id, self._records[canonical_id], alias_used

    @staticmethod
    def _gender(values: list[str], missing: list[str], conflicts: list[str]) -> Gender | None:
        normalized: list[Gender] = []
        for value in values:
            lowered = value.casefold()
            if lowered == "female":
                normalized.append(Gender.FEMALE)
            elif lowered == "male":
                normalized.append(Gender.MALE)
            else:
                conflicts.append("gender_must_be_explicitly_male_or_female")
        unique = set(normalized)
        if len(unique) > 1:
            conflicts.append("contradictory_explicit_gender_fields")
        if not values:
            missing.append("gender")
        return next(iter(unique)) if len(unique) == 1 and not conflicts else None

    @staticmethod
    def _locale(values: list[str], missing: list[str], conflicts: list[str]) -> str | None:
        if not values:
            missing.append("locale")
            return None
        if len(values) > 1:
            conflicts.append("contradictory_explicit_locale_fields")
            return None
        locale = values[0]
        if not _BCP47.fullmatch(locale):
            conflicts.append("locale_is_not_a_valid_explicit_bcp47_tag")
            return None
        return locale

    @staticmethod
    def _identity_kind(identity_class: str) -> IdentityKind:
        if identity_class == "historical_person":
            return IdentityKind.HISTORICAL
        if identity_class.startswith("fictional"):
            return IdentityKind.FICTIONAL
        return IdentityKind.ORIGINAL

    @staticmethod
    def _age_band(profile: Mapping[str, Any], preflight: Mapping[str, Any], limitations: list[str]) -> AgeBand:
        explicit = _exact_values(
            profile,
            {},
            (("voice_design", "age_band"), ("age_band",)),
            (),
        )
        if len(explicit) == 1:
            try:
                return AgeBand(explicit[0])
            except ValueError as exc:
                raise ValidationError("explicit voice age_band is unsupported") from exc
        if len(explicit) > 1:
            raise ValidationError("explicit voice age_band fields conflict")
        maturity = preflight.get("maturity")
        lane = _text(maturity.get("lane")) if isinstance(maturity, Mapping) else ""
        if lane == "adult":
            return AgeBand.ADULT
        limitations.append("age_not_authored_zero_affinity")
        return AgeBand.UNSPECIFIED

    @staticmethod
    def _body_presence(profile: Mapping[str, Any], registry: Mapping[str, Any], limitations: list[str]) -> BodyPresence:
        explicit = _exact_values(
            profile,
            registry,
            (("voice_design", "body_presence"), ("avatar_identity_selection", "body_presence")),
            ("voice_body_presence",),
        )
        if len(explicit) > 1:
            raise ValidationError("explicit voice body_presence fields conflict")
        if explicit:
            try:
                return BodyPresence(explicit[0])
            except ValueError as exc:
                raise ValidationError("explicit voice body_presence is unsupported") from exc
        limitations.append("body_not_authored_zero_affinity")
        return BodyPresence.NOT_AUTHORED

    @staticmethod
    def _traits(profile: Mapping[str, Any], limitations: list[str]) -> tuple[str, ...]:
        sources = [
            _nested(profile, ("voice_design", "personality_traits")),
            profile.get("personality_traits"),
        ]
        authored = [value for value in sources if value is not None]
        if not authored:
            limitations.append("personality_tags_not_authored_zero_affinity")
            return ()
        if len(authored) > 1 and authored[0] != authored[1]:
            raise ValidationError("explicit personality trait fields conflict")
        value = authored[0]
        if not isinstance(value, list) or len(value) > 12:
            raise ValidationError("personality_traits must be an explicit list with at most 12 items")
        if any(not isinstance(item, str) or not _SAFE_TRAIT.fullmatch(item) for item in value):
            raise ValidationError("personality_traits must contain lowercase safe identifiers")
        if len(set(value)) != len(value):
            raise ValidationError("personality_traits cannot contain duplicates")
        return tuple(value)

    @staticmethod
    def _era(profile: Mapping[str, Any], identity_kind: IdentityKind, limitations: list[str]) -> EraContext:
        explicit = _exact_values(
            profile,
            {},
            (("voice_design", "era"), ("era_context",)),
            (),
        )
        if len(explicit) > 1:
            raise ValidationError("explicit voice era fields conflict")
        if explicit:
            try:
                return EraContext(explicit[0])
            except ValueError as exc:
                raise ValidationError("explicit voice era is unsupported") from exc
        if identity_kind is IdentityKind.HISTORICAL:
            return EraContext.HISTORICAL
        limitations.append("era_not_authored_zero_affinity")
        return EraContext.UNSPECIFIED

    def adapt(
        self,
        requested_candidate_id: str,
        *,
        assignment_mode: AssignmentMode = AssignmentMode.ASSIGN_IF_MISSING,
        existing_voice_id: str | None = None,
        candidate_count: int = 3,
        audition_locale: str | None = None,
    ) -> dict[str, Any]:
        """Return a validated brief or a precise, non-guessing review result."""

        self._assert_sources()
        canonical_id, record, alias_used = self._resolve_record(requested_candidate_id)
        try:
            preflight = self._preflight(self.project_root, requested_candidate_id)
        except Exception as exc:  # exact upstream diagnostic, no partial brief
            return {
                "schema": ADAPTER_SCHEMA,
                "status": "needs_review",
                "binding_status": "needs_review",
                "requested_candidate_id": requested_candidate_id,
                "canonical_candidate_id": canonical_id,
                "storage_id": _text(record.get("profile_directory")) or canonical_id,
                "registry_alias_used": alias_used,
                "missing_required_fields": ["avatar_preflight"],
                "conflicts": [f"avatar_preflight_error:{type(exc).__name__}"],
                "fit_limitations": [],
                "source_hashes": {
                    "registry_sha256": self._registry_sha256,
                    "preflight_sha256": self._preflight_sha256,
                },
                "brief": None,
                "mutation_performed": False,
                "runtime_activation_allowed": False,
            }

        if preflight.get("registry_binding_verified") is not True:
            raise ValidationError("avatar preflight did not verify the exact registry binding")
        if preflight.get("canonical_candidate_id") != canonical_id:
            raise ValidationError("avatar preflight canonical candidate differs from the exact registry result")
        registry_info = preflight.get("registry")
        profile_info = preflight.get("canonical_profile")
        identity_info = preflight.get("identity")
        if not all(isinstance(item, Mapping) for item in (registry_info, profile_info, identity_info)):
            raise ValidationError("avatar preflight omitted required source attestations")
        if registry_info.get("sha256") != self._registry_sha256:
            raise ValidationError("avatar preflight registry digest differs from the pinned adapter registry")

        profile_relative = Path(_text(profile_info.get("path")))
        profile_path = _regular_file_below(self.project_root, profile_relative)
        assert profile_path is not None
        profile, profile_sha = _read_json_attested(profile_path)
        if profile_sha != profile_info.get("sha256"):
            raise ValidationError("canonical profile digest differs from avatar preflight")
        storage_id = safe_component(profile_path.parent.name, field="storage_id")
        if storage_id != (_text(record.get("profile_directory")) or canonical_id):
            raise ValidationError("canonical profile storage directory differs from the registry")

        request_path = _regular_file_below(profile_path.parent, Path("voice_discovery_request.json"))
        assert request_path is not None
        request, request_sha = _read_json_attested(request_path)
        request_candidate = _text(request.get("candidate_id"))
        exact_names = {canonical_id, storage_id, *record.get("aliases", [])}
        if request_candidate not in exact_names:
            raise ValidationError("voice discovery request candidate ID is not an exact registry identifier")

        missing: list[str] = []
        conflicts: list[str] = []
        limitations: list[str] = []
        gender_values = _exact_values(
            profile,
            record,
            (("gender_preference",), ("voice_design", "gender"), ("knowledge_plan", "gender_preference")),
            ("voice_gender",),
        )
        gender = self._gender(gender_values, missing, conflicts)
        locale_values = _exact_values(
            profile,
            record,
            (("locale",), ("language",), ("voice_design", "locale"), ("voice_and_behavior", "locale")),
            ("voice_locale",),
        )
        locale = self._locale(locale_values, missing, conflicts)
        language_provenance = LanguageProvenance.EXPLICIT_SOURCE
        if locale is None and "locale" in missing and not any("locale" in item for item in conflicts):
            if audition_locale is not None:
                if not isinstance(audition_locale, str) or not _BCP47.fullmatch(audition_locale):
                    conflicts.append("application_audition_locale_is_invalid")
                else:
                    locale = audition_locale
                    language_provenance = LanguageProvenance.APPLICATION_AUDITION_DEFAULT
                    limitations.append("locale_confirmation_required_before_binding")
        role = _text(profile.get("role_title"))
        if not role:
            missing.append("role_title")
        subject_id = _text(identity_info.get("subject_id"))
        if not subject_id:
            missing.append("subject_id")
        display_name = _text(profile.get("display_name"))
        if not display_name:
            missing.append("display_name")

        identity_kind = self._identity_kind(_text(identity_info.get("identity_class")))
        try:
            age_band = self._age_band(profile, preflight, limitations)
            body_presence = self._body_presence(profile, record, limitations)
            traits = self._traits(profile, limitations)
            era = self._era(profile, identity_kind, limitations)
        except ValidationError as exc:
            conflicts.append(str(exc))
            age_band = AgeBand.UNSPECIFIED
            body_presence = BodyPresence.NOT_AUTHORED
            traits = ()
            era = EraContext.HISTORICAL if identity_kind is IdentityKind.HISTORICAL else EraContext.UNSPECIFIED

        source_hashes = {
            "registry_sha256": self._registry_sha256,
            "profile_sha256": profile_sha,
            "request_sha256": request_sha,
            "preflight_sha256": self._preflight_sha256,
        }
        only_audition_locale_missing = (
            locale is not None
            and language_provenance is LanguageProvenance.APPLICATION_AUDITION_DEFAULT
            and set(missing) == {"locale"}
            and not conflicts
        )
        result: dict[str, Any] = {
            "schema": ADAPTER_SCHEMA,
            "status": (
                "ready_for_nonbinding_audition"
                if only_audition_locale_missing
                else ("needs_review" if missing or conflicts else "ready_for_design")
            ),
            "binding_status": "needs_review" if missing or conflicts else "source_fields_complete",
            "requested_candidate_id": requested_candidate_id,
            "canonical_candidate_id": canonical_id,
            "storage_id": storage_id,
            "registry_alias_used": alias_used,
            "missing_required_fields": sorted(set(missing)),
            "conflicts": sorted(set(conflicts)),
            "fit_limitations": sorted(set(limitations)),
            "source_hashes": source_hashes,
            "brief": None,
            "mutation_performed": False,
            "runtime_activation_allowed": False,
        }
        if result["status"] == "needs_review":
            return result

        assert gender is not None and locale is not None
        source = AvatarSourceAttestation(
            candidate_id=canonical_id,
            storage_id=storage_id,
            profile_sha256=profile_sha,
            request_sha256=request_sha,
            registry_sha256=self._registry_sha256,
            registry_alias=alias_used,
        )
        brief = VoiceDesignBrief(
            subject_id=subject_id,
            display_name=display_name,
            gender=gender,
            age_band=age_band,
            body_presence=body_presence,
            role=role,
            personality_traits=traits,
            language=locale,
            era=era,
            identity_kind=identity_kind,
            assignment_mode=assignment_mode,
            source_attestation=source,
            existing_voice_id=existing_voice_id,
            candidate_count=candidate_count,
            language_provenance=language_provenance,
        ).validate()
        result["brief"] = brief.to_dict()
        return result

    def live_coverage(
        self,
        *,
        candidate_ids: tuple[str, ...] = GENERATED_EXPERT_CANDIDATES,
        audition_locale: str | None = "en-US",
    ) -> dict[str, Any]:
        """Inspect bounded live generated experts and protected existing voices."""

        if not 1 <= len(candidate_ids) <= MAX_COVERAGE_CANDIDATES or len(set(candidate_ids)) != len(candidate_ids):
            raise ValidationError("coverage candidate list must contain 1-32 unique IDs")
        self._assert_sources()
        generated = []
        for candidate_id in candidate_ids:
            result = self.adapt(candidate_id, audition_locale=audition_locale)
            generated.append(
                {
                    "candidate_id": candidate_id,
                    "status": result["status"],
                    "binding_status": result["binding_status"],
                    "missing_required_fields": result["missing_required_fields"],
                    "conflicts": result["conflicts"],
                    "fit_limitations": result["fit_limitations"],
                    "source_hashes": result["source_hashes"],
                }
            )

        preserved = []
        for candidate_id, (relative_text, policy) in PRESERVED_VOICE_PROFILES.items():
            canonical_id, _record, _alias = self._resolve_record(candidate_id)
            path = _regular_file_below(self.project_root, Path(relative_text))
            assert path is not None
            profile, voice_profile_sha = _read_json_attested(path)
            if _text(profile.get("candidate_id")) not in {"", canonical_id}:
                raise ValidationError("existing voice profile candidate ID contradicts the exact registry")
            voice_id = safe_component(profile.get("voice_id"), field="existing voice_id")
            preserved.append(
                {
                    "candidate_id": canonical_id,
                    "voice_id": voice_id,
                    "status": policy,
                    "voice_profile_path": relative_text,
                    "voice_profile_sha256": voice_profile_sha,
                    "mutation_performed": False,
                }
            )
        return {
            "schema": COVERAGE_SCHEMA,
            "registry_sha256": self._registry_sha256,
            "trusted_preflight_sha256": self._preflight_sha256,
            "generated_experts": generated,
            "preserved_existing_voices": preserved,
            "summary": {
                "generated_expert_count": len(generated),
                "ready_for_design_count": sum(item["status"] == "ready_for_design" for item in generated),
                "ready_for_nonbinding_audition_count": sum(
                    item["status"] == "ready_for_nonbinding_audition" for item in generated
                ),
                "needs_review_count": sum(item["status"] == "needs_review" for item in generated),
                "preserved_voice_count": len(preserved),
            },
            "runtime_activation_allowed": False,
            "mutation_performed": False,
        }
