"""Deterministic, append-only voice design and audition orchestration.

This module plans voice candidates; it never synthesizes audio.  It is kept
separate from the neural backend so profile interpretation, provenance checks,
human audition, approval, and rollback remain inspectable and testable without
loading a model.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable

from .errors import ConflictError, NotFoundError, ValidationError
from .models import AuditionStatus, ConsentBasis, SourceBasis, VoiceProfile
from .paths import PinnedDirectory, atomic_write_json_new, safe_component
from .registry import VoiceRegistry, parse_timestamp, utc_now
from .reservations import OutputReservation

BRIEF_SCHEMA = "kira.local-voice.design-brief.v1"
BUNDLE_SCHEMA = "kira.local-voice.audition-bundle.v1"
DECISION_SCHEMA = "kira.local-voice.audition-decision.v1"
BINDING_SCHEMA = "kira.local-voice.binding-event.v1"
ENVELOPE_SCHEMA = "kira.local-voice.immutable-record.v1"

MAX_RECORD_BYTES = 512 * 1024
MAX_TRAITS = 12
MAX_CANDIDATES = 5
MIN_CANDIDATES = 2
MAX_BATCH_BRIEFS = 32
KOKORO_MODEL_REPO = "hexgrad/Kokoro-82M"
KOKORO_MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
KOKORO_MODEL_WEIGHTS_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"
KOKORO_CONFIG_SHA256 = "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
CATALOG_AUDITION_REPORT_SHA256 = "cfbf870e08ec7ad992ebd857d43845ca598313a95c23af8270e3b0f801024ef6"
CATALOG_AUDIT_REPORT_SHA256 = "c0b855b5fe0b2143d93e85558221b6996303b99956009d4c96dc9b324ecaa4f9"
TECHNICAL_REVIEW_STATUS = "technical_pass_human_review_required"
_LANGUAGE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_TRAIT = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_ROLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &'./_-]{0,79}$")


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"


class AgeBand(StrEnum):
    UNSPECIFIED = "unspecified"
    CHILD = "child"
    TEEN = "teen"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    MATURE = "mature"
    SENIOR = "senior"


class BodyPresence(StrEnum):
    NOT_AUTHORED = "not_authored"
    LIGHT = "light"
    BALANCED = "balanced"
    GROUNDED = "grounded"
    BROAD = "broad"
    SYNTHETIC = "synthetic"


class EraContext(StrEnum):
    UNSPECIFIED = "unspecified"
    CONTEMPORARY = "contemporary"
    HISTORICAL = "historical"
    FUTURE = "future"
    TIMELESS = "timeless"


class IdentityKind(StrEnum):
    ORIGINAL = "original"
    FICTIONAL = "fictional"
    HISTORICAL = "historical"


class AssignmentMode(StrEnum):
    ASSIGN_IF_MISSING = "assign_if_missing"
    REPLACE_EXISTING = "replace_existing"
    KEEP_EXISTING = "keep_existing"


class LanguageProvenance(StrEnum):
    """Why a language is present in an audition brief."""

    EXPLICIT_SOURCE = "explicit_source"
    APPLICATION_AUDITION_DEFAULT = "application_audition_default"


@dataclass(frozen=True, slots=True)
class AvatarSourceAttestation:
    """Exact non-content identifiers and digests supplied by the profile adapter."""

    candidate_id: str
    storage_id: str
    profile_sha256: str
    request_sha256: str
    registry_sha256: str
    registry_alias: str | None = None

    def validate(self) -> "AvatarSourceAttestation":
        safe_component(self.candidate_id, field="avatar candidate_id")
        safe_component(self.storage_id, field="avatar storage_id")
        for field_name, digest in (
            ("profile_sha256", self.profile_sha256),
            ("request_sha256", self.request_sha256),
            ("registry_sha256", self.registry_sha256),
        ):
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                raise ValidationError(f"{field_name} must be a lowercase SHA-256 digest")
        if self.registry_alias is not None:
            _plain_text(self.registry_alias, field="registry_alias", maximum=200)
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> "AvatarSourceAttestation":
        data = _strict_keys(
            value,
            required={"candidate_id", "storage_id", "profile_sha256", "request_sha256", "registry_sha256"},
            optional={"registry_alias"}, field="avatar source attestation",
        )
        return cls(
            candidate_id=data["candidate_id"], storage_id=data["storage_id"],
            profile_sha256=data["profile_sha256"], request_sha256=data["request_sha256"],
            registry_sha256=data["registry_sha256"], registry_alias=data.get("registry_alias"),
        ).validate()


def _plain_text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum or any(ord(char) < 32 for char in cleaned):
        raise ValidationError(f"{field} must be 1-{maximum} visible characters")
    return cleaned


def _enum(enum_type: type[StrEnum], value: object, *, field: str) -> StrEnum:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValidationError(f"{field} is not supported") from exc


def _strict_keys(data: object, *, required: set[str], optional: set[str], field: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValidationError(f"{field} must be a JSON object")
    keys = set(data)
    missing = required - keys
    unexpected = keys - required - optional
    if missing:
        raise ValidationError(f"{field} is missing required fields: {', '.join(sorted(missing))}")
    if unexpected:
        raise ValidationError(f"{field} has unexpected fields: {', '.join(sorted(unexpected))}")
    return data


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identity_key(*values: str) -> str:
    return "".join(character.lower() for value in values for character in value if character.isalnum())


@dataclass(frozen=True, slots=True)
class VoiceDesignBrief:
    """Bounded profile information used to choose—not impersonate—a voice."""

    subject_id: str
    display_name: str
    gender: Gender
    age_band: AgeBand
    body_presence: BodyPresence
    role: str
    personality_traits: tuple[str, ...]
    language: str
    era: EraContext
    identity_kind: IdentityKind
    assignment_mode: AssignmentMode
    source_attestation: AvatarSourceAttestation
    existing_voice_id: str | None = None
    candidate_count: int = 3
    language_provenance: LanguageProvenance = LanguageProvenance.EXPLICIT_SOURCE

    def validate(self) -> "VoiceDesignBrief":
        safe_component(self.subject_id, field="subject_id")
        _plain_text(self.display_name, field="display_name", maximum=120)
        if not isinstance(self.gender, Gender):
            raise ValidationError("gender must be explicitly female or male")
        if not isinstance(self.age_band, AgeBand):
            raise ValidationError("age_band is invalid")
        if not isinstance(self.body_presence, BodyPresence):
            raise ValidationError("body_presence is invalid")
        if not isinstance(self.era, EraContext) or not isinstance(self.identity_kind, IdentityKind):
            raise ValidationError("era and identity_kind are required")
        if not isinstance(self.assignment_mode, AssignmentMode):
            raise ValidationError("assignment_mode is invalid")
        if not isinstance(self.source_attestation, AvatarSourceAttestation):
            raise ValidationError("source_attestation is required")
        self.source_attestation.validate()
        if not _ROLE.fullmatch(self.role):
            raise ValidationError("role must be 1-80 short visible characters")
        if not isinstance(self.personality_traits, tuple) or len(self.personality_traits) > MAX_TRAITS:
            raise ValidationError(f"personality_traits must contain 0-{MAX_TRAITS} items")
        if len(set(self.personality_traits)) != len(self.personality_traits):
            raise ValidationError("personality_traits cannot contain duplicates")
        if any(not isinstance(item, str) or not _TRAIT.fullmatch(item) for item in self.personality_traits):
            raise ValidationError("personality traits must be lowercase safe identifiers")
        if not isinstance(self.language, str) or not _LANGUAGE.fullmatch(self.language):
            raise ValidationError("language must be a BCP-47-like tag")
        if not isinstance(self.language_provenance, LanguageProvenance):
            raise ValidationError("language_provenance is invalid")
        if not isinstance(self.candidate_count, int) or isinstance(self.candidate_count, bool):
            raise ValidationError("candidate_count must be an integer")
        if not MIN_CANDIDATES <= self.candidate_count <= MAX_CANDIDATES:
            raise ValidationError(f"candidate_count must be between {MIN_CANDIDATES} and {MAX_CANDIDATES}")
        if self.existing_voice_id is not None:
            safe_component(self.existing_voice_id, field="existing_voice_id")
        if self.assignment_mode is AssignmentMode.ASSIGN_IF_MISSING and self.existing_voice_id is not None:
            raise ValidationError("assign_if_missing cannot name an existing voice")
        if self.assignment_mode in {AssignmentMode.REPLACE_EXISTING, AssignmentMode.KEEP_EXISTING}:
            if self.existing_voice_id is None:
                raise ValidationError(f"{self.assignment_mode.value} requires existing_voice_id")
        if self.identity_kind is IdentityKind.HISTORICAL and self.era is not EraContext.HISTORICAL:
            raise ValidationError("historical identities require historical era context")
        return self

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["schema"] = BRIEF_SCHEMA
        result["personality_traits"] = list(self.personality_traits)
        result["source_attestation"] = self.source_attestation.to_dict()
        result["language_provenance"] = self.language_provenance.value
        return result

    @classmethod
    def from_dict(cls, value: object) -> "VoiceDesignBrief":
        data = _strict_keys(
            value,
            required={
                "schema", "subject_id", "display_name", "gender", "age_band", "body_presence",
                "role", "personality_traits", "language", "era", "identity_kind", "assignment_mode",
                "source_attestation", "language_provenance",
            },
            optional={"existing_voice_id", "candidate_count"},
            field="voice design brief",
        )
        if data["schema"] != BRIEF_SCHEMA:
            raise ValidationError("voice design brief schema is unsupported")
        traits = data["personality_traits"]
        if not isinstance(traits, list):
            raise ValidationError("personality_traits must be a JSON array")
        brief = cls(
            subject_id=data["subject_id"],
            display_name=data["display_name"],
            gender=_enum(Gender, data["gender"], field="gender"),
            age_band=_enum(AgeBand, data["age_band"], field="age_band"),
            body_presence=_enum(BodyPresence, data["body_presence"], field="body_presence"),
            role=data["role"],
            personality_traits=tuple(traits),
            language=data["language"],
            era=_enum(EraContext, data["era"], field="era"),
            identity_kind=_enum(IdentityKind, data["identity_kind"], field="identity_kind"),
            assignment_mode=_enum(AssignmentMode, data["assignment_mode"], field="assignment_mode"),
            source_attestation=AvatarSourceAttestation.from_dict(data["source_attestation"]),
            existing_voice_id=data.get("existing_voice_id"),
            candidate_count=data.get("candidate_count", 3),
            language_provenance=_enum(
                LanguageProvenance, data["language_provenance"], field="language_provenance"
            ),
        )
        return brief.validate()


@dataclass(frozen=True, slots=True)
class CatalogRecipe:
    catalog_id: str
    display_name: str
    backend_voice_id: str
    gender: Gender
    languages: tuple[str, ...]
    base_speed: float
    style: str
    tags: frozenset[str]
    age_affinity: frozenset[AgeBand]
    body_affinity: frozenset[BodyPresence]
    era_affinity: frozenset[EraContext]
    role_keywords: frozenset[str]
    license_id: str = "Apache-2.0"

    def source_attestation(self) -> dict[str, Any]:
        payload = {
            "model_repo": KOKORO_MODEL_REPO,
            "model_revision": KOKORO_MODEL_REVISION,
            "model_weights_sha256": KOKORO_MODEL_WEIGHTS_SHA256,
            "config_sha256": KOKORO_CONFIG_SHA256,
            "runtime_voice_id": self.backend_voice_id,
            "license_id": self.license_id,
            "catalog_audition_report_sha256": CATALOG_AUDITION_REPORT_SHA256,
            "catalog_audit_report_sha256": CATALOG_AUDIT_REPORT_SHA256,
            "technical_status": TECHNICAL_REVIEW_STATUS,
        }
        return {**payload, "source_attestation_sha256": _canonical_digest(payload)}


def safe_builtin_catalog() -> tuple[CatalogRecipe, ...]:
    """Audited generic bases with distinct delivery recipes, not identities."""

    shared = {"languages": ("en-US",), "license_id": "Apache-2.0"}
    return (
        CatalogRecipe(
            "aoede-bright", "Kokoro af_aoede — bright target", "af_aoede", Gender.FEMALE,
            base_speed=1.05, style="bright",
            tags=frozenset({"bright", "expressive", "playful", "energetic", "youthful", "warm"}),
            age_affinity=frozenset({AgeBand.CHILD, AgeBand.TEEN, AgeBand.YOUNG_ADULT}),
            body_affinity=frozenset({BodyPresence.LIGHT, BodyPresence.BALANCED, BodyPresence.SYNTHETIC}),
            era_affinity=frozenset({EraContext.CONTEMPORARY, EraContext.FUTURE}),
            role_keywords=frozenset({"companion", "student", "performer", "hero"}), **shared,
        ),
        CatalogRecipe(
            "bella-clear", "Kokoro af_bella — clear target", "af_bella", Gender.FEMALE,
            base_speed=0.99, style="clear",
            tags=frozenset({"clear", "curious", "direct", "observant", "practical", "warm"}),
            age_affinity=frozenset({AgeBand.TEEN, AgeBand.YOUNG_ADULT, AgeBand.ADULT}),
            body_affinity=frozenset({BodyPresence.BALANCED, BodyPresence.SYNTHETIC}),
            era_affinity=frozenset({EraContext.CONTEMPORARY, EraContext.FUTURE, EraContext.TIMELESS}),
            role_keywords=frozenset({"expert", "engineer", "producer", "assistant", "scientist"}), **shared,
        ),
        CatalogRecipe(
            "heart-grounded", "Kokoro af_heart — grounded target", "af_heart", Gender.FEMALE,
            base_speed=0.93, style="grounded",
            tags=frozenset({"calm", "gentle", "measured", "patient", "reassuring", "warm"}),
            age_affinity=frozenset({AgeBand.ADULT, AgeBand.MATURE, AgeBand.SENIOR}),
            body_affinity=frozenset({BodyPresence.BALANCED, BodyPresence.GROUNDED, BodyPresence.BROAD}),
            era_affinity=frozenset({EraContext.HISTORICAL, EraContext.CONTEMPORARY, EraContext.TIMELESS}),
            role_keywords=frozenset({"companion", "mentor", "counselor", "attorney", "director"}), **shared,
        ),
        CatalogRecipe(
            "kore-formal", "Kokoro af_kore — formal target", "af_kore", Gender.FEMALE,
            base_speed=0.95, style="formal",
            tags=frozenset({"clear", "formal", "measured", "observant", "reserved", "direct"}),
            age_affinity=frozenset({AgeBand.ADULT, AgeBand.MATURE, AgeBand.SENIOR}),
            body_affinity=frozenset({BodyPresence.BALANCED, BodyPresence.GROUNDED, BodyPresence.BROAD}),
            era_affinity=frozenset({EraContext.HISTORICAL, EraContext.CONTEMPORARY, EraContext.TIMELESS}),
            role_keywords=frozenset({"expert", "attorney", "director", "historian", "leader"}), **shared,
        ),
        CatalogRecipe(
            "nicole-reassuring", "Kokoro af_nicole — reassuring target", "af_nicole", Gender.FEMALE,
            base_speed=0.94, style="reassuring",
            tags=frozenset({"calm", "gentle", "patient", "reassuring", "warm", "measured"}),
            age_affinity=frozenset({AgeBand.ADULT, AgeBand.MATURE, AgeBand.SENIOR}),
            body_affinity=frozenset({BodyPresence.BALANCED, BodyPresence.GROUNDED}),
            era_affinity=frozenset({EraContext.CONTEMPORARY, EraContext.TIMELESS}),
            role_keywords=frozenset({"companion", "mentor", "counselor", "teacher", "guide"}), **shared,
        ),
        CatalogRecipe(
            "sarah-curious", "Kokoro af_sarah — curious target", "af_sarah", Gender.FEMALE,
            base_speed=1.01, style="curious",
            tags=frozenset({"clear", "curious", "gentle", "practical", "warm", "expressive"}),
            age_affinity=frozenset({AgeBand.TEEN, AgeBand.YOUNG_ADULT, AgeBand.ADULT}),
            body_affinity=frozenset({BodyPresence.LIGHT, BodyPresence.BALANCED, BodyPresence.SYNTHETIC}),
            era_affinity=frozenset({EraContext.CONTEMPORARY, EraContext.FUTURE, EraContext.TIMELESS}),
            role_keywords=frozenset({"expert", "assistant", "engineer", "scientist", "companion"}), **shared,
        ),
        CatalogRecipe(
            "fenrir-grounded", "Kokoro am_fenrir — grounded target", "am_fenrir", Gender.MALE,
            base_speed=0.92, style="grounded",
            tags=frozenset({"calm", "formal", "measured", "patient", "reassuring", "warm"}),
            age_affinity=frozenset({AgeBand.ADULT, AgeBand.MATURE, AgeBand.SENIOR}),
            body_affinity=frozenset({BodyPresence.BALANCED, BodyPresence.GROUNDED, BodyPresence.BROAD}),
            era_affinity=frozenset({EraContext.HISTORICAL, EraContext.CONTEMPORARY, EraContext.TIMELESS}),
            role_keywords=frozenset({"companion", "mentor", "counselor", "attorney", "director"}), **shared,
        ),
        CatalogRecipe(
            "michael-clear", "Kokoro am_michael — clear target", "am_michael", Gender.MALE,
            base_speed=0.98, style="clear",
            tags=frozenset({"clear", "curious", "direct", "observant", "practical", "warm"}),
            age_affinity=frozenset({AgeBand.TEEN, AgeBand.YOUNG_ADULT, AgeBand.ADULT}),
            body_affinity=frozenset({BodyPresence.BALANCED, BodyPresence.SYNTHETIC}),
            era_affinity=frozenset({EraContext.CONTEMPORARY, EraContext.FUTURE, EraContext.TIMELESS}),
            role_keywords=frozenset({"expert", "engineer", "producer", "assistant", "scientist"}), **shared,
        ),
        CatalogRecipe(
            "puck-bright", "Kokoro am_puck — bright target", "am_puck", Gender.MALE,
            base_speed=1.04, style="bright",
            tags=frozenset({"bright", "expressive", "playful", "energetic", "youthful", "warm"}),
            age_affinity=frozenset({AgeBand.CHILD, AgeBand.TEEN, AgeBand.YOUNG_ADULT}),
            body_affinity=frozenset({BodyPresence.LIGHT, BodyPresence.BALANCED, BodyPresence.SYNTHETIC}),
            era_affinity=frozenset({EraContext.CONTEMPORARY, EraContext.FUTURE}),
            role_keywords=frozenset({"companion", "student", "performer", "hero"}), **shared,
        ),
    )


@dataclass(frozen=True, slots=True)
class AuditionApproval:
    candidate_id: str
    listener: str
    auditioned_at: str
    sample_sha256: str
    heard_full_sample: bool
    clarity: int
    naturalness: int
    character_fit: int
    provenance_reviewed: bool
    distinctness_checked: bool
    distinctness_report_sha256: str
    shared_spec_sha256: str
    notes: str = ""

    def validate(self) -> "AuditionApproval":
        safe_component(self.candidate_id, field="candidate_id")
        _plain_text(self.listener, field="listener", maximum=120)
        parse_timestamp(self.auditioned_at, field="auditioned_at")
        if not _SHA256.fullmatch(self.sample_sha256):
            raise ValidationError("sample_sha256 must be a lowercase SHA-256 digest")
        if self.heard_full_sample is not True:
            raise ValidationError("approval requires listening to the complete audition sample")
        if self.provenance_reviewed is not True:
            raise ValidationError("approval requires provenance review")
        if self.distinctness_checked is not True:
            raise ValidationError("approval requires a distinctness check")
        if not _SHA256.fullmatch(self.distinctness_report_sha256):
            raise ValidationError("distinctness_report_sha256 must be a lowercase SHA-256 digest")
        if not _SHA256.fullmatch(self.shared_spec_sha256):
            raise ValidationError("shared_spec_sha256 must be a lowercase SHA-256 digest")
        if any(not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5
               for score in (self.clarity, self.naturalness, self.character_fit)):
            raise ValidationError("audition ratings must be integers from 1 to 5")
        if not isinstance(self.notes, str) or len(self.notes) > 500 or any(ord(char) < 32 for char in self.notes):
            raise ValidationError("audition notes must be at most 500 visible characters")
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> "AuditionApproval":
        data = _strict_keys(
            value,
            required={
                "candidate_id", "listener", "auditioned_at", "sample_sha256", "heard_full_sample",
                "clarity", "naturalness", "character_fit", "provenance_reviewed", "distinctness_checked",
                "distinctness_report_sha256", "shared_spec_sha256", "notes",
            },
            optional=set(), field="audition approval",
        )
        return cls(**data).validate()


@dataclass(frozen=True, slots=True)
class SubjectVoiceSelection:
    """A subject's explicit choice after comparing eligible candidates."""

    candidate_id: str
    selector_subject_id: str
    selected_at: str
    comparison_complete: bool
    selection_receipt_sha256: str

    def validate(self) -> "SubjectVoiceSelection":
        safe_component(self.candidate_id, field="candidate_id")
        safe_component(self.selector_subject_id, field="selector_subject_id")
        parse_timestamp(self.selected_at, field="selected_at")
        if self.comparison_complete is not True:
            raise ValidationError("selection requires completing the comparative audition")
        if not _SHA256.fullmatch(self.selection_receipt_sha256):
            raise ValidationError("selection_receipt_sha256 must be a lowercase SHA-256 digest")
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> "SubjectVoiceSelection":
        data = _strict_keys(
            value,
            required={
                "candidate_id", "selector_subject_id", "selected_at", "comparison_complete",
                "selection_receipt_sha256",
            },
            optional=set(), field="subject voice selection",
        )
        return cls(**data).validate()


class VoiceDesignStore:
    """Bounded immutable record store for bundles, decisions, and bindings."""

    def __init__(self, root: Path):
        requested_root = root.expanduser().absolute()
        requested_root.mkdir(parents=True, exist_ok=True)
        root_pin = PinnedDirectory.capture(requested_root)
        self.root = root_pin.path
        # These are fixed single components. Avoid resolving them before
        # PinnedDirectory inspects the requested directory itself.
        self.bundle_root = self.root / "bundles"
        self.decision_root = self.root / "decisions"
        self.binding_root = self.root / "bindings"
        self.lock_root = self.root / "locks"
        for directory in (self.bundle_root, self.decision_root, self.binding_root, self.lock_root):
            directory.mkdir(parents=True, exist_ok=True)
        self._pinned = (root_pin,) + tuple(PinnedDirectory.capture(path) for path in (
            self.bundle_root, self.decision_root, self.binding_root, self.lock_root,
        ))

    def _assert_roots(self) -> None:
        for root in self._pinned:
            root.assert_unchanged()

    def _record_path(self, root: Path, record_id: str) -> Path:
        # `contained_path` resolves links, which would hide the fact that the
        # requested record name itself is a link. The component is already
        # single-segment validated and every root is pinned, so joining without
        # resolution preserves link detection while remaining contained.
        return root / f"{safe_component(record_id, field='record_id')}.json"

    def _write_new(self, root: Path, record_id: str, schema: str, payload: dict[str, Any]) -> None:
        self._assert_roots()
        envelope = {
            "schema": ENVELOPE_SCHEMA,
            "record_schema": schema,
            "payload": payload,
            "payload_sha256": _canonical_digest(payload),
        }
        try:
            atomic_write_json_new(self._record_path(root, record_id), envelope)
        except FileExistsError as exc:
            raise ConflictError(f"immutable record already exists: {record_id}") from exc

    def _read(self, root: Path, record_id: str, schema: str) -> dict[str, Any]:
        self._assert_roots()
        path = self._record_path(root, record_id)
        if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
            raise ValidationError("voice design record cannot be a link or junction")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError as exc:
            raise NotFoundError(f"unknown immutable record: {record_id}") from exc
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= MAX_RECORD_BYTES:
                raise ValidationError("voice design record size or type is invalid")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                encoded = handle.read(MAX_RECORD_BYTES + 1)
        finally:
            os.close(descriptor)
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("voice design record is not valid UTF-8 JSON") from exc
        _strict_keys(
            envelope,
            required={"schema", "record_schema", "payload", "payload_sha256"},
            optional=set(), field="immutable record envelope",
        )
        if envelope["schema"] != ENVELOPE_SCHEMA or envelope["record_schema"] != schema:
            raise ValidationError("voice design record schema is invalid")
        if not isinstance(envelope["payload"], dict):
            raise ValidationError("voice design record payload is invalid")
        if envelope["payload_sha256"] != _canonical_digest(envelope["payload"]):
            raise ValidationError("voice design record failed tamper verification")
        return envelope["payload"]

    def put_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        bundle_id = bundle.get("bundle_id")
        safe_component(bundle_id, field="bundle_id")
        try:
            self._write_new(self.bundle_root, bundle_id, BUNDLE_SCHEMA, bundle)
            return bundle
        except ConflictError:
            existing = self.get_bundle(bundle_id)
            if existing.get("brief_digest") != bundle.get("brief_digest"):
                raise
            return existing

    def get_bundle(self, bundle_id: str) -> dict[str, Any]:
        payload = self._read(self.bundle_root, bundle_id, BUNDLE_SCHEMA)
        if payload.get("bundle_id") != bundle_id:
            raise ValidationError("audition bundle filename does not match its payload ID")
        return payload

    def list_bundles(self) -> list[dict[str, Any]]:
        self._assert_roots()
        return [self.get_bundle(path.stem) for path in sorted(self.bundle_root.glob("*.json"))]

    def put_decision(self, decision: dict[str, Any]) -> None:
        self._write_new(self.decision_root, decision["decision_id"], DECISION_SCHEMA, decision)

    def list_decisions(self) -> list[dict[str, Any]]:
        self._assert_roots()
        records = []
        for path in sorted(self.decision_root.glob("*.json")):
            payload = self._read(self.decision_root, path.stem, DECISION_SCHEMA)
            if payload.get("decision_id") != path.stem or payload.get("schema") != DECISION_SCHEMA:
                raise ValidationError("audition decision filename or payload schema is invalid")
            records.append(payload)
        return records

    def put_binding(self, binding: dict[str, Any]) -> None:
        self._write_new(self.binding_root, binding["event_id"], BINDING_SCHEMA, binding)

    def list_bindings(self, subject_id: str) -> list[dict[str, Any]]:
        safe_component(subject_id, field="subject_id")
        self._assert_roots()
        records: list[dict[str, Any]] = []
        for path in sorted(self.binding_root.glob(f"{subject_id}--*.json")):
            payload = self._read(self.binding_root, path.stem, BINDING_SCHEMA)
            if (
                payload.get("event_id") != path.stem
                or payload.get("schema") != BINDING_SCHEMA
                or payload.get("subject_id") != subject_id
            ):
                raise ValidationError("binding filename, subject, or payload schema is invalid")
            records.append(payload)
        return records

    def acquire_subject_lock(self, subject_id: str) -> OutputReservation:
        self._assert_roots()
        return OutputReservation.acquire(self.lock_root, f"bind-{safe_component(subject_id, field='subject_id')}")


class VoiceDesignEngine:
    """Turns a validated avatar brief into candidates and human-gated bindings."""

    _PROTECTED_EXISTING = frozenset({
        "peterparker", "peterparkernwh", "marinettedupaincheng", "marinette", "ladybug",
        "kathrynmerteuil", "kathrynmerteuiladultcontinuation",
    })
    _KIRA_KEYS = frozenset({"kira"})
    _LISA_KEYS = frozenset({"lisa"})
    _HOLMES_KEYS = frozenset({"hhholmes", "hermanwebstermudgett"})
    _HISTORICAL_DISCLOSURE = (
        "Speculative historical reconstruction; not an authentic recording, verified voice match, or identity clone."
    )

    def __init__(
        self,
        store: VoiceDesignStore,
        voice_registry: VoiceRegistry,
        catalog: Iterable[CatalogRecipe] | None = None,
    ):
        self.store = store
        self.voice_registry = voice_registry
        self.catalog = tuple(catalog or safe_builtin_catalog())
        self._validate_catalog()

    def _validate_catalog(self) -> None:
        if len(self.catalog) < 4:
            raise ValidationError("voice catalog must provide multiple male and female recipes")
        seen: set[str] = set()
        counts = {Gender.FEMALE: 0, Gender.MALE: 0}
        for recipe in self.catalog:
            safe_component(recipe.catalog_id, field="catalog_id")
            safe_component(recipe.backend_voice_id, field="backend_voice_id")
            if recipe.catalog_id in seen:
                raise ValidationError("voice catalog IDs must be unique")
            seen.add(recipe.catalog_id)
            counts[recipe.gender] += 1
            if not 0.5 <= recipe.base_speed <= 2.0 or not recipe.languages:
                raise ValidationError("voice catalog recipe has invalid synthesis bounds")
            female_allowlist = {"af_heart", "af_bella", "af_nicole", "af_aoede", "af_kore", "af_sarah"}
            male_allowlist = {"am_fenrir", "am_michael", "am_puck"}
            if recipe.backend_voice_id not in female_allowlist | male_allowlist:
                raise ValidationError("voice catalog recipe uses a base outside the audited allowlist")
            if recipe.gender is Gender.FEMALE and recipe.backend_voice_id not in female_allowlist:
                raise ValidationError("female recipe cannot route to a male base voice")
            if recipe.gender is Gender.MALE and recipe.backend_voice_id not in male_allowlist:
                raise ValidationError("male recipe cannot route to a female base voice")
        if any(count < MIN_CANDIDATES for count in counts.values()):
            raise ValidationError("voice catalog must contain multiple recipes for each gender")

    @staticmethod
    def _keys(brief: VoiceDesignBrief) -> frozenset[str]:
        return frozenset({_identity_key(brief.subject_id), _identity_key(brief.display_name)})

    def _resolve_existing(self, brief: VoiceDesignBrief) -> VoiceProfile | None:
        if brief.existing_voice_id is None:
            return None
        profile = self.voice_registry.get(brief.existing_voice_id)
        if self.voice_registry.is_deactivated(profile.voice_id):
            raise ValidationError("existing voice is deactivated and cannot remain bound")
        consent = profile.consent
        if not consent.generated_audio_permitted:
            raise ValidationError("existing voice provenance does not permit generated audio")
        if consent.expires_at is not None and parse_timestamp(consent.expires_at, field="consent expires_at") <= datetime.now(UTC):
            raise ValidationError("existing voice provenance has expired")
        if profile.source_basis is SourceBasis.SOURCE_RECORDING_BACKED:
            if (
                consent.basis is not ConsentBasis.SOURCE_SUBJECT_CONSENT
                or not consent.reference_recording_permitted
                or not consent.evidence_sha256
                or not profile.reference_hashes
            ):
                raise ValidationError("source-recording-backed existing voice lacks complete provenance")
        if profile.source_basis is SourceBasis.DESIGNED and consent.basis is not ConsentBasis.SYNTHETIC_DESIGN:
            raise ValidationError("designed existing voice lacks synthetic-design provenance")
        if profile.source_basis is SourceBasis.GENERIC_FALLBACK and consent.basis is not ConsentBasis.GENERIC_NO_IDENTITY:
            raise ValidationError("generic existing voice lacks generic-no-identity provenance")
        return profile

    def _enforce_identity_policy(self, brief: VoiceDesignBrief) -> tuple[VoiceProfile | None, str | None]:
        keys = self._keys(brief)
        existing = self._resolve_existing(brief)
        if keys & self._PROTECTED_EXISTING and brief.assignment_mode is not AssignmentMode.KEEP_EXISTING:
            raise ValidationError("this established fictional character voice is locked to keep_existing")
        if keys & self._KIRA_KEYS:
            if brief.assignment_mode is not AssignmentMode.REPLACE_EXISTING or existing is None:
                raise ValidationError("Kira replacement requires a reusable existing voice for rollback")
        if keys & self._HOLMES_KEYS:
            if brief.identity_kind is not IdentityKind.HISTORICAL or brief.era is not EraContext.HISTORICAL:
                raise ValidationError("H. H. Holmes must use historical reconstruction context")
            return existing, self._HISTORICAL_DISCLOSURE
        if brief.identity_kind is IdentityKind.HISTORICAL:
            return existing, self._HISTORICAL_DISCLOSURE
        return existing, None

    def _subject_selection_required(self, brief: VoiceDesignBrief) -> bool:
        return bool(self._keys(brief) & (self._KIRA_KEYS | self._LISA_KEYS))

    @staticmethod
    def _adjusted_speed(recipe: CatalogRecipe, brief: VoiceDesignBrief) -> float:
        adjustment = 0.0
        if brief.age_band in {AgeBand.CHILD, AgeBand.TEEN}:
            adjustment += 0.03
        elif brief.age_band is AgeBand.SENIOR:
            adjustment -= 0.04
        if brief.body_presence is BodyPresence.LIGHT:
            adjustment += 0.02
        elif brief.body_presence in {BodyPresence.GROUNDED, BodyPresence.BROAD}:
            adjustment -= 0.02
        if brief.era is EraContext.HISTORICAL:
            adjustment -= 0.02
        return round(min(1.20, max(0.80, recipe.base_speed + adjustment)), 2)

    @staticmethod
    def _score(recipe: CatalogRecipe, brief: VoiceDesignBrief) -> tuple[int, list[str]]:
        matched_traits = sorted(set(brief.personality_traits) & recipe.tags)
        score = len(matched_traits) * 7
        reasons: list[str] = []
        if matched_traits:
            reasons.append("personality:" + ",".join(matched_traits))
        if brief.age_band in recipe.age_affinity:
            score += 5
            reasons.append(f"age:{brief.age_band.value}")
        if brief.body_presence in recipe.body_affinity:
            score += 4
            reasons.append(f"body:{brief.body_presence.value}")
        if brief.era in recipe.era_affinity:
            score += 3
            reasons.append(f"era:{brief.era.value}")
        role_words = {word.lower() for word in re.findall(r"[A-Za-z]+", brief.role)}
        matched_roles = sorted(role_words & recipe.role_keywords)
        if matched_roles:
            score += 4
            reasons.append("role:" + ",".join(matched_roles))
        return score, reasons or ["safe gender-and-language baseline"]

    def _build_candidates(
        self,
        brief: VoiceDesignBrief,
        brief_digest: str,
        disclosure: str | None,
    ) -> list[dict[str, Any]]:
        eligible = [
            recipe for recipe in self.catalog
            if recipe.gender is brief.gender and brief.language in recipe.languages
        ]
        if len(eligible) < brief.candidate_count:
            raise ValidationError("the safe local catalog has too few candidates for this gender and language")
        scored = []
        for recipe in eligible:
            score, reasons = self._score(recipe, brief)
            scored.append((score, recipe.catalog_id, recipe, reasons))
        scored.sort(key=lambda item: (-item[0], item[1]))

        candidates: list[dict[str, Any]] = []
        for rank, (score, _catalog_id, recipe, reasons) in enumerate(scored[:brief.candidate_count], start=1):
            speed = self._adjusted_speed(recipe, brief)
            seed = {"brief_digest": brief_digest, "catalog_id": recipe.catalog_id, "speed": speed}
            candidate_id = f"vc-{_canonical_digest(seed)[:28]}"
            candidate = {
                "candidate_id": candidate_id,
                "rank": rank,
                "catalog_id": recipe.catalog_id,
                "catalog_display_name": recipe.display_name,
                "backend_voice_id": recipe.backend_voice_id,
                "gender": recipe.gender.value,
                "language": brief.language,
                "language_provenance": brief.language_provenance.value,
                "source_basis": SourceBasis.GENERIC_FALLBACK.value,
                "identity_claim": "none",
                "license_id": recipe.license_id,
                "technical_status": TECHNICAL_REVIEW_STATUS,
                "source_attestation": recipe.source_attestation(),
                "runtime_adapter_requirement": "exact_voice_id_and_source_attestation",
                "delivery": {"speed": speed, "style": recipe.style},
                "fit_score": score,
                "fit_reasons": reasons,
                "target_traits": sorted(recipe.tags),
                "disclosure": disclosure,
                "automated_checks": {
                    "gender_match": "passed",
                    "language_supported": "passed",
                    "audited_base_allowlist": "passed",
                    "non_identity_provenance": "passed",
                    "asr_wer_range_0_04_to_0_08": "passed",
                    "automated_mfcc_collision_threshold_0_9995": "passed",
                    "human_audition": "pending",
                },
                "sample_output_name": f"{brief.subject_id}-{candidate_id}-audition",
            }
            shared_spec = {
                "subject_id": brief.subject_id,
                "candidate_id": candidate_id,
                "catalog_id": recipe.catalog_id,
                "backend_voice_id": recipe.backend_voice_id,
                "gender": recipe.gender.value,
                "language": brief.language,
                "language_provenance": brief.language_provenance.value,
                "delivery": candidate["delivery"],
                "source_basis": candidate["source_basis"],
                "source_attestation_sha256": candidate["source_attestation"]["source_attestation_sha256"],
                "runtime_adapter_requirement": candidate["runtime_adapter_requirement"],
                "disclosure": disclosure,
            }
            candidate["shared_spec_sha256"] = _canonical_digest(shared_spec)
            candidates.append(candidate)
        return candidates

    def _assert_no_contradictory_source(self, brief_payload: dict[str, Any]) -> None:
        source = brief_payload["source_attestation"]
        source_key = (
            source["candidate_id"], source["storage_id"], source["registry_sha256"], source["request_sha256"],
        )
        shaping_fields = (
            "subject_id", "display_name", "gender", "age_band", "body_presence", "role",
            "personality_traits", "language", "era", "identity_kind",
        )
        for stored in self.store.list_bundles():
            other = stored.get("brief")
            if not isinstance(other, dict) or not isinstance(other.get("source_attestation"), dict):
                raise ValidationError("stored audition bundle has an invalid source attestation")
            other_source = other["source_attestation"]
            other_key = (
                other_source.get("candidate_id"), other_source.get("storage_id"),
                other_source.get("registry_sha256"), other_source.get("request_sha256"),
            )
            same_profile_digest = other_source.get("profile_sha256") == source["profile_sha256"]
            shaping_changed = any(other.get(field) != brief_payload.get(field) for field in shaping_fields)
            if source_key == other_key and other != brief_payload:
                raise ValidationError("the same avatar registry request produced contradictory voice briefs")
            if same_profile_digest and shaping_changed:
                raise ValidationError("the same source profile digest produced contradictory voice-shaping fields")

    @staticmethod
    def _batch_sources_contradict(first: VoiceDesignBrief, second: VoiceDesignBrief) -> bool:
        left = first.to_dict()
        right = second.to_dict()
        left_source = left["source_attestation"]
        right_source = right["source_attestation"]
        same_request = all(
            left_source[field] == right_source[field]
            for field in ("candidate_id", "storage_id", "registry_sha256", "request_sha256")
        )
        shaping_fields = (
            "subject_id", "display_name", "gender", "age_band", "body_presence", "role",
            "personality_traits", "language", "era", "identity_kind",
        )
        same_profile = left_source["profile_sha256"] == right_source["profile_sha256"]
        shaping_changed = any(left[field] != right[field] for field in shaping_fields)
        return (same_request and left != right) or (same_profile and shaping_changed)

    def create_batch(self, briefs: Iterable[VoiceDesignBrief | dict[str, Any]]) -> tuple[dict[str, Any], ...]:
        """Preflight and create a bounded batch without choosing any candidate."""

        if isinstance(briefs, (str, bytes, dict)):
            raise ValidationError("voice design batch must be an iterable of brief objects")
        items = list(briefs)
        if not 1 <= len(items) <= MAX_BATCH_BRIEFS:
            raise ValidationError(f"voice design batch must contain 1-{MAX_BATCH_BRIEFS} briefs")
        parsed = [VoiceDesignBrief.from_dict(item) if isinstance(item, dict) else item.validate() for item in items]
        subject_ids = [item.subject_id for item in parsed]
        if len(set(subject_ids)) != len(subject_ids):
            raise ValidationError("voice design batch cannot repeat a subject_id")
        for index, first in enumerate(parsed):
            self._assert_no_contradictory_source(first.to_dict())
            existing, disclosure = self._enforce_identity_policy(first)
            del existing
            if first.assignment_mode is not AssignmentMode.KEEP_EXISTING:
                self._build_candidates(first, _canonical_digest(first.to_dict()), disclosure)
            for second in parsed[index + 1:]:
                if self._batch_sources_contradict(first, second):
                    raise ValidationError("voice design batch contains contradictory source attestations")
        return tuple(self.create_bundle(item) for item in parsed)

    def create_bundle(self, brief: VoiceDesignBrief | dict[str, Any]) -> dict[str, Any]:
        brief = VoiceDesignBrief.from_dict(brief) if isinstance(brief, dict) else brief.validate()
        existing, disclosure = self._enforce_identity_policy(brief)
        brief_payload = brief.to_dict()
        self._assert_no_contradictory_source(brief_payload)
        brief_digest = _canonical_digest(brief_payload)
        bundle_id = f"vb-{brief_digest[:32]}"

        if brief.assignment_mode is AssignmentMode.KEEP_EXISTING:
            bundle = {
                "schema": BUNDLE_SCHEMA,
                "bundle_id": bundle_id,
                "brief_digest": brief_digest,
                "brief": brief_payload,
                "created_at": utc_now(),
                "status": "existing_voice_preserved",
                "existing_voice": self._existing_summary(existing),
                "candidates": [],
                "audition_cases": [],
                "profile_fit_limitations": self._profile_fit_limitations(brief),
                "human_approval_required": False,
                "subject_comparative_selection_required": False,
                "disclosure": disclosure,
            }
            return self.store.put_bundle(bundle)

        candidates = self._build_candidates(brief, brief_digest, disclosure)

        bundle = {
            "schema": BUNDLE_SCHEMA,
            "bundle_id": bundle_id,
            "brief_digest": brief_digest,
            "brief": brief_payload,
            "created_at": utc_now(),
            "status": "awaiting_audio_and_human_audition",
            "existing_voice": self._existing_summary(existing),
            "candidates": candidates,
            "audition_cases": self._audition_cases(brief),
            "profile_fit_limitations": self._profile_fit_limitations(brief),
            "human_approval_required": True,
            "subject_comparative_selection_required": self._subject_selection_required(brief),
            "disclosure": disclosure,
        }
        return self.store.put_bundle(bundle)

    @staticmethod
    def _profile_fit_limitations(brief: VoiceDesignBrief) -> list[str]:
        limitations = []
        if brief.age_band is AgeBand.UNSPECIFIED:
            limitations.append("age_unspecified_zero_affinity")
        if brief.body_presence is BodyPresence.NOT_AUTHORED:
            limitations.append("body_not_authored_zero_affinity")
        if not brief.personality_traits:
            limitations.append("personality_tags_missing_zero_affinity")
        if brief.era is EraContext.UNSPECIFIED:
            limitations.append("era_unspecified_zero_affinity")
        if brief.language_provenance is LanguageProvenance.APPLICATION_AUDITION_DEFAULT:
            limitations.append("locale_confirmation_required_before_binding")
        return limitations

    @staticmethod
    def _existing_summary(profile: VoiceProfile | None) -> dict[str, Any] | None:
        if profile is None:
            return None
        return {
            "voice_id": profile.voice_id,
            "source_basis": profile.source_basis.value,
            "audition_status": profile.audition_status.value,
            "provenance_permits_reuse": True,
        }

    @staticmethod
    def _audition_cases(brief: VoiceDesignBrief) -> list[dict[str, Any]]:
        role = brief.role.lower()
        return [
            {
                "case_id": "neutral-introduction",
                "text": f"Hello. I am ready to help as your {role}, and we can take this one step at a time.",
                "evaluate": ["clarity", "natural pacing", "character fit"],
            },
            {
                "case_id": "warm-support",
                "text": "I hear you. Let us slow down, look at what matters most, and choose a practical next step together.",
                "evaluate": ["warmth", "emotional range", "listening fatigue"],
            },
            {
                "case_id": "high-information",
                "text": "First, I will summarize the evidence. Then I will explain the tradeoffs and mark anything that still needs review.",
                "evaluate": ["precision", "sentence boundaries", "sustained intelligibility"],
            },
        ]

    def _validated_bundle(self, bundle_id: str) -> dict[str, Any]:
        bundle = self.store.get_bundle(bundle_id)
        _strict_keys(
            bundle,
            required={
                "schema", "bundle_id", "brief_digest", "brief", "created_at", "status",
                "existing_voice", "candidates", "audition_cases", "human_approval_required",
                "subject_comparative_selection_required", "profile_fit_limitations", "disclosure",
            },
            optional=set(), field="audition bundle",
        )
        if bundle.get("schema") != BUNDLE_SCHEMA:
            raise ValidationError("audition bundle payload schema is invalid")
        parse_timestamp(bundle.get("created_at"), field="audition bundle created_at")
        brief = VoiceDesignBrief.from_dict(bundle.get("brief"))
        brief_digest = _canonical_digest(brief.to_dict())
        if bundle.get("brief_digest") != brief_digest or bundle_id != f"vb-{brief_digest[:32]}":
            raise ValidationError("audition bundle brief digest is invalid")
        existing, disclosure = self._enforce_identity_policy(brief)
        if bundle.get("existing_voice") != self._existing_summary(existing):
            raise ValidationError("audition bundle existing-voice provenance is stale or invalid")
        if bundle.get("disclosure") != disclosure:
            raise ValidationError("audition bundle disclosure is invalid")
        if brief.assignment_mode is AssignmentMode.KEEP_EXISTING:
            expected = {
                "status": "existing_voice_preserved",
                "candidates": [],
                "audition_cases": [],
                "profile_fit_limitations": self._profile_fit_limitations(brief),
                "human_approval_required": False,
                "subject_comparative_selection_required": False,
            }
            if any(bundle.get(key) != value for key, value in expected.items()):
                raise ValidationError("existing-voice preservation bundle is invalid")
        else:
            if bundle.get("status") != "awaiting_audio_and_human_audition":
                raise ValidationError("audition bundle status is invalid")
            if bundle.get("candidates") != self._build_candidates(brief, brief_digest, disclosure):
                raise ValidationError("audition candidates do not match the deterministic safe catalog plan")
            if bundle.get("audition_cases") != self._audition_cases(brief):
                raise ValidationError("audition cases do not match the validated profile")
            if bundle.get("profile_fit_limitations") != self._profile_fit_limitations(brief):
                raise ValidationError("audition bundle profile-fit limitations are invalid")
            if bundle.get("human_approval_required") is not True:
                raise ValidationError("audition bundle cannot bypass human approval")
            if bundle.get("subject_comparative_selection_required") is not self._subject_selection_required(brief):
                raise ValidationError("audition bundle subject-selection policy is invalid")
        return bundle

    def _eligibility_decisions(
        self,
        bundle: dict[str, Any],
        candidate: dict[str, Any],
    ) -> list[dict[str, Any]]:
        brief = VoiceDesignBrief.from_dict(bundle["brief"])
        if brief.language_provenance is not LanguageProvenance.EXPLICIT_SOURCE:
            raise ValidationError("application audition locale must be confirmed in the source profile before binding")
        matches = []
        for item in self.store.list_decisions():
            if item.get("bundle_id") != bundle["bundle_id"] or item.get("candidate_id") != candidate["candidate_id"]:
                continue
            _strict_keys(
                item,
                required={
                    "schema", "decision_id", "decision", "bundle_id", "subject_id",
                    "candidate_id", "authority", "audition",
                },
                optional=set(), field="audition eligibility decision",
            )
            if (
                item["schema"] != DECISION_SCHEMA
                or item["decision"] != "eligible_pending_subject_selection"
                or item["subject_id"] != brief.subject_id
            ):
                raise ValidationError("audition eligibility decision policy is invalid")
            _plain_text(item["authority"], field="eligibility authority", maximum=120)
            audition = AuditionApproval.from_dict(item["audition"])
            if (
                audition.candidate_id != candidate["candidate_id"]
                or audition.shared_spec_sha256 != candidate["shared_spec_sha256"]
            ):
                raise ValidationError("audition eligibility decision does not match its candidate")
            matches.append(item)
        return matches

    def current_binding(self, subject_id: str) -> dict[str, Any] | None:
        records = self.store.list_bindings(subject_id)
        if not records:
            return None
        for record in records:
            self._validate_binding_record(record, subject_id)
        by_id = {record.get("event_id"): record for record in records}
        if len(by_id) != len(records):
            raise ValidationError("duplicate binding event ID")
        roots = [record for record in records if record.get("parent_event_id") is None]
        children: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            parent = record.get("parent_event_id")
            if parent is not None:
                if parent not in by_id:
                    raise ValidationError("binding history has a missing parent")
                children.setdefault(parent, []).append(record)
        if len(roots) != 1 or any(len(items) != 1 for items in children.values()):
            raise ValidationError("binding history is forked or ambiguous")
        current = roots[0]
        visited = {current["event_id"]}
        while current["event_id"] in children:
            current = children[current["event_id"]][0]
            if current["event_id"] in visited:
                raise ValidationError("binding history contains a cycle")
            visited.add(current["event_id"])
        if len(visited) != len(records):
            raise ValidationError("binding history contains disconnected events")
        return current

    def _validate_binding_target(self, target: object) -> None:
        if not isinstance(target, dict):
            raise ValidationError("binding target must be an object")
        kind = target.get("target_kind")
        if kind == "existing_voice":
            _strict_keys(
                target,
                required={"target_kind", "voice_id", "source_basis", "audition_status"},
                optional=set(), field="existing voice binding target",
            )
            profile = self.voice_registry.get(target["voice_id"])
            if self.voice_registry.is_deactivated(profile.voice_id):
                raise ValidationError("binding target points to a deactivated existing voice")
            if (
                target["source_basis"] != profile.source_basis.value
                or target["audition_status"] != profile.audition_status.value
            ):
                raise ValidationError("existing voice binding target disagrees with registry provenance")
            return
        if kind == "catalog_design":
            _strict_keys(
                target,
                required={
                    "target_kind", "bundle_id", "candidate_id", "catalog_id", "backend_voice_id",
                    "runtime_voice_id", "runtime_resolution_status", "gender", "language", "delivery", "source_basis",
                    "language_provenance", "source_attestation_sha256", "shared_spec_sha256", "disclosure",
                },
                optional=set(), field="catalog voice binding target",
            )
            bundle = self._validated_bundle(target["bundle_id"])
            candidate = next(
                (item for item in bundle["candidates"] if item.get("candidate_id") == target["candidate_id"]),
                None,
            )
            if candidate is None or target != self._candidate_target(candidate, bundle["bundle_id"]):
                raise ValidationError("catalog binding target does not match its immutable audition bundle")
            return
        raise ValidationError("binding target kind is unsupported")

    def _validate_binding_record(self, record: dict[str, Any], subject_id: str) -> None:
        action = record.get("action")
        base = {
            "schema", "event_id", "action", "subject_id", "display_name", "parent_event_id",
            "bundle_id", "decision_id", "effective_at", "authority", "active_target", "rollback_target",
        }
        action_fields = {
            "activate_auditioned_candidate": {"audition_approval"},
            "activate_subject_selected_candidate": {"subject_selection"},
            "rollback": {"reason"},
        }
        if action not in action_fields:
            raise ValidationError("binding action is unsupported")
        _strict_keys(record, required=base | action_fields[action], optional=set(), field="binding event")
        if record["schema"] != BINDING_SCHEMA or record["subject_id"] != subject_id:
            raise ValidationError("binding event schema or subject is invalid")
        safe_component(record["event_id"], field="event_id")
        if record["parent_event_id"] is not None:
            safe_component(record["parent_event_id"], field="parent_event_id")
        parse_timestamp(record["effective_at"], field="binding effective_at")
        _plain_text(record["authority"], field="binding authority", maximum=120)
        _plain_text(record["display_name"], field="binding display_name", maximum=120)
        self._validate_binding_target(record["active_target"])
        if record["rollback_target"] is not None:
            self._validate_binding_target(record["rollback_target"])
        if action == "activate_auditioned_candidate":
            decision = record["audition_approval"]
            if not isinstance(decision, dict) or decision.get("decision") != "approved_for_binding":
                raise ValidationError("binding event lacks an approved audition")
            AuditionApproval.from_dict(decision.get("audition"))
        elif action == "activate_subject_selected_candidate":
            selection = SubjectVoiceSelection.from_dict(record["subject_selection"])
            if selection.selector_subject_id != subject_id:
                raise ValidationError("binding subject-selection receipt is invalid")
        else:
            _plain_text(record["reason"], field="rollback reason", maximum=500)

    def approve_bundle(
        self,
        bundle_id: str,
        approval: AuditionApproval,
        *,
        authority: str,
    ) -> dict[str, Any]:
        approval.validate()
        authority = _plain_text(authority, field="authority", maximum=120)
        bundle = self._validated_bundle(bundle_id)
        if bundle.get("status") != "awaiting_audio_and_human_audition":
            raise ValidationError("this bundle cannot activate a new voice")
        candidate = next((item for item in bundle["candidates"] if item.get("candidate_id") == approval.candidate_id), None)
        if candidate is None:
            raise ValidationError("approved candidate is not in the audition bundle")
        brief = VoiceDesignBrief.from_dict(bundle["brief"])
        if brief.language_provenance is not LanguageProvenance.EXPLICIT_SOURCE:
            raise ValidationError("application audition locale must be confirmed in the source profile before binding")
        if candidate.get("gender") != brief.gender.value or candidate.get("language") != brief.language:
            raise ValidationError("candidate no longer matches the approved avatar brief")
        if approval.shared_spec_sha256 != candidate.get("shared_spec_sha256"):
            raise ValidationError("audition approval does not match the shared candidate specification")
        lock = self.store.acquire_subject_lock(brief.subject_id)
        try:
            current = self.current_binding(brief.subject_id)
            if current is None:
                previous_target = self._initial_existing_target(bundle.get("existing_voice"))
                parent_id = None
            else:
                previous_target = current["active_target"]
                parent_id = current["event_id"]
            if brief.assignment_mode is AssignmentMode.REPLACE_EXISTING and previous_target is None:
                raise ValidationError("replacement approval requires a rollback target")
            active_target = self._candidate_target(candidate, bundle_id)
            seed = {
                "subject_id": brief.subject_id,
                "bundle_id": bundle_id,
                "candidate_id": approval.candidate_id,
                "auditioned_at": approval.auditioned_at,
                "sample_sha256": approval.sample_sha256,
                "parent_event_id": parent_id,
            }
            event_id = f"{brief.subject_id}--be-{_canonical_digest(seed)[:24]}"
            decision = {
                "schema": DECISION_SCHEMA,
                "decision_id": f"ad-{_canonical_digest({**seed, 'authority': authority})[:28]}",
                "decision": (
                    "eligible_pending_subject_selection"
                    if bundle.get("subject_comparative_selection_required") is True
                    else "approved_for_binding"
                ),
                "bundle_id": bundle_id,
                "subject_id": brief.subject_id,
                "candidate_id": approval.candidate_id,
                "authority": authority,
                "audition": approval.to_dict(),
            }
            if bundle.get("subject_comparative_selection_required") is True:
                existing_eligibility = self._eligibility_decisions(bundle, candidate)
                if existing_eligibility:
                    raise ConflictError("candidate already has an eligibility decision")
                self.store.put_decision(decision)
                return decision
            event = {
                "schema": BINDING_SCHEMA,
                "event_id": event_id,
                "action": "activate_auditioned_candidate",
                "subject_id": brief.subject_id,
                "display_name": brief.display_name,
                "parent_event_id": parent_id,
                "bundle_id": bundle_id,
                "decision_id": None,
                "effective_at": approval.auditioned_at,
                "authority": authority,
                "audition_approval": decision,
                "active_target": active_target,
                "rollback_target": previous_target,
            }
            existing_events = [
                item for item in self.store.list_bindings(brief.subject_id)
                if item.get("bundle_id") == bundle_id
                and item.get("active_target", {}).get("candidate_id") == approval.candidate_id
                and item.get("action") == "activate_auditioned_candidate"
            ]
            if existing_events:
                raise ConflictError("candidate is already active from this audition bundle")
            self.store.put_binding(event)
            return event
        finally:
            lock.release()

    @staticmethod
    def _candidate_target(candidate: dict[str, Any], bundle_id: str) -> dict[str, Any]:
        return {
            "target_kind": "catalog_design",
            "bundle_id": bundle_id,
            "candidate_id": candidate["candidate_id"],
            "catalog_id": candidate["catalog_id"],
            "backend_voice_id": candidate["backend_voice_id"],
            "runtime_voice_id": candidate["backend_voice_id"],
            "runtime_resolution_status": "requires_exact_runtime_resolver",
            "gender": candidate["gender"],
            "language": candidate["language"],
            "language_provenance": candidate["language_provenance"],
            "delivery": candidate["delivery"],
            "source_basis": candidate["source_basis"],
            "source_attestation_sha256": candidate["source_attestation"]["source_attestation_sha256"],
            "shared_spec_sha256": candidate["shared_spec_sha256"],
            "disclosure": candidate["disclosure"],
        }

    def select_eligible_candidate(
        self,
        bundle_id: str,
        selection: SubjectVoiceSelection,
        *,
        authority: str,
    ) -> dict[str, Any]:
        """Bind Kira/Lisa only after their own comparative selection receipt."""

        selection.validate()
        authority = _plain_text(authority, field="authority", maximum=120)
        bundle = self._validated_bundle(bundle_id)
        brief = VoiceDesignBrief.from_dict(bundle["brief"])
        if brief.language_provenance is not LanguageProvenance.EXPLICIT_SOURCE:
            raise ValidationError("application audition locale must be confirmed in the source profile before selection")
        if bundle.get("subject_comparative_selection_required") is not True:
            raise ValidationError("this subject does not use the comparative selection gate")
        if selection.selector_subject_id != brief.subject_id:
            raise ValidationError("selector_subject_id must match the voice subject")
        candidate = next((item for item in bundle["candidates"] if item.get("candidate_id") == selection.candidate_id), None)
        if candidate is None:
            raise ValidationError("selected candidate is not in the audition bundle")
        eligible = self._eligibility_decisions(bundle, candidate)
        if len(eligible) != 1:
            raise ValidationError("candidate requires exactly one completed owner-audition eligibility record")

        lock = self.store.acquire_subject_lock(brief.subject_id)
        try:
            current = self.current_binding(brief.subject_id)
            if current is None:
                previous_target = self._initial_existing_target(bundle.get("existing_voice"))
                parent_id = None
            else:
                previous_target = current["active_target"]
                parent_id = current["event_id"]
            if previous_target is None and self._keys(brief) & self._KIRA_KEYS:
                raise ValidationError("comparative selection requires a current or rollback voice target")
            seed = {
                "subject_id": brief.subject_id,
                "bundle_id": bundle_id,
                "candidate_id": selection.candidate_id,
                "selected_at": selection.selected_at,
                "selection_receipt_sha256": selection.selection_receipt_sha256,
                "parent_event_id": parent_id,
            }
            event_id = f"{brief.subject_id}--be-{_canonical_digest(seed)[:24]}"
            event = {
                "schema": BINDING_SCHEMA,
                "event_id": event_id,
                "action": "activate_subject_selected_candidate",
                "subject_id": brief.subject_id,
                "display_name": brief.display_name,
                "parent_event_id": parent_id,
                "bundle_id": bundle_id,
                "decision_id": eligible[0]["decision_id"],
                "effective_at": selection.selected_at,
                "authority": authority,
                "subject_selection": selection.to_dict(),
                "active_target": self._candidate_target(candidate, bundle_id),
                "rollback_target": previous_target,
            }
            existing_events = [
                item for item in self.store.list_bindings(brief.subject_id)
                if item.get("bundle_id") == bundle_id
                and item.get("active_target", {}).get("candidate_id") == selection.candidate_id
                and item.get("action") == "activate_subject_selected_candidate"
            ]
            if existing_events:
                raise ConflictError("subject already selected this candidate from the bundle")
            self.store.put_binding(event)
            return event
        finally:
            lock.release()

    @staticmethod
    def _initial_existing_target(summary: dict[str, Any] | None) -> dict[str, Any] | None:
        if summary is None:
            return None
        if summary.get("provenance_permits_reuse") is not True:
            raise ValidationError("existing voice provenance does not permit rollback")
        return {
            "target_kind": "existing_voice",
            "voice_id": summary["voice_id"],
            "source_basis": summary["source_basis"],
            "audition_status": summary["audition_status"],
        }

    def rollback(self, subject_id: str, *, authority: str, reason: str, effective_at: str | None = None) -> dict[str, Any]:
        safe_component(subject_id, field="subject_id")
        authority = _plain_text(authority, field="authority", maximum=120)
        reason = _plain_text(reason, field="reason", maximum=500)
        effective_at = effective_at or utc_now()
        parse_timestamp(effective_at, field="effective_at")
        lock = self.store.acquire_subject_lock(subject_id)
        try:
            current = self.current_binding(subject_id)
            if current is None or current.get("rollback_target") is None:
                raise ValidationError("current binding has no rollback target")
            seed = {
                "subject_id": subject_id,
                "parent_event_id": current["event_id"],
                "effective_at": effective_at,
                "reason": reason,
            }
            event = {
                "schema": BINDING_SCHEMA,
                "event_id": f"{subject_id}--be-{_canonical_digest(seed)[:24]}",
                "action": "rollback",
                "subject_id": subject_id,
                "display_name": current["display_name"],
                "parent_event_id": current["event_id"],
                "bundle_id": current.get("bundle_id"),
                "decision_id": None,
                "effective_at": effective_at,
                "authority": authority,
                "reason": reason,
                "active_target": current["rollback_target"],
                "rollback_target": current["active_target"],
            }
            self.store.put_binding(event)
            return event
        finally:
            lock.release()


__all__ = [
    "AgeBand", "AssignmentMode", "AuditionApproval", "AvatarSourceAttestation", "BodyPresence",
    "EraContext", "Gender",
    "IdentityKind", "SubjectVoiceSelection", "VoiceDesignBrief", "VoiceDesignEngine", "VoiceDesignStore",
    "safe_builtin_catalog",
]
