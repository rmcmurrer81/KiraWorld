"""Append-only voice registry with immutable provenance and consent fields."""

from __future__ import annotations

import json
import hashlib
import hmac
import os
import re
import stat
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from .errors import ConflictError, NotFoundError, ValidationError
from .models import AuditionStatus, ConsentBasis, ConsentRecord, SourceBasis, VoiceProfile
from .paths import atomic_write_json_new, contained_path, exclusive_file_lock, safe_component

_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


class VoiceRegistry:
    """Stores each voice as a separate immutable JSON record.

    Updating a voice means registering a new voice_id. This prevents an existing
    friendly name from silently changing identity, source, or permission basis.
    """

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.deactivation_root = contained_path(self.root, "_deactivated")
        self.deactivation_root.mkdir(parents=True, exist_ok=True)
        self.guard_path=contained_path(self.root.parent,".voice_registry.guard")
        self.key_path=contained_path(self.root.parent,".voice_registry_integrity.key")
        self._key=self._load_or_create_key()

    def register(self, profile: VoiceProfile) -> VoiceProfile:
        voice_id = safe_component(profile.voice_id, field="voice_id")
        self._validate(profile)
        record = profile if profile.created_at else replace(profile, created_at=utc_now())
        path = contained_path(self.root, f"{voice_id}.json")
        profile_data = record.to_dict()
        canonical = json.dumps(profile_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = {
            "schema": "kira.local-voice.profile.v2",
            "profile": profile_data,
            "profile_hmac_sha256": hmac.new(self._key,canonical,hashlib.sha256).hexdigest(),
        }
        with self.mutation_guard():
            try: atomic_write_json_new(path, envelope)
            except FileExistsError as exc: raise ConflictError(f"voice_id already exists: {voice_id}") from exc
        return record

    def get(self, voice_id: str) -> VoiceProfile:
        path = contained_path(self.root, f"{safe_component(voice_id, field='voice_id')}.json")
        if not path.exists():
            raise NotFoundError(f"unknown voice_id: {voice_id}")
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError("voice registry record is invalid") from exc
        if not isinstance(envelope,dict) or set(envelope)!={"schema","profile","profile_hmac_sha256"}:
            raise ValidationError("voice registry record schema is invalid")
        if envelope.get("schema") != "kira.local-voice.profile.v2" or not isinstance(envelope.get("profile"), dict):
            raise ValidationError("voice registry record schema is invalid")
        data = envelope["profile"]
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected=hmac.new(self._key,canonical,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(str(envelope.get("profile_hmac_sha256","")),expected):
            raise ValidationError("voice registry record failed tamper verification")
        try:
            consent_data=data["consent"]
            if not isinstance(consent_data,dict): raise TypeError
            consent = ConsentRecord(
                basis=ConsentBasis(consent_data["basis"]),
                subject_id=consent_data["subject_id"],
                authority=consent_data["authority"],
                scope=consent_data["scope"],
                recorded_at=consent_data["recorded_at"],
                evidence_sha256=consent_data.get("evidence_sha256"),
                reference_recording_permitted=consent_data["reference_recording_permitted"],
                generated_audio_permitted=consent_data["generated_audio_permitted"],
                revocable=consent_data.get("revocable", True),
                expires_at=consent_data.get("expires_at"),
            )
            profile = VoiceProfile(
                voice_id=data["voice_id"],
                display_name=data["display_name"],
                source_basis=SourceBasis(data["source_basis"]),
                audition_status=AuditionStatus(data["audition_status"]),
                consent=consent,
                language=data.get("language", "en-US"),
                description=data.get("description", ""),
                reference_hashes=tuple(data.get("reference_hashes", ())),
                created_at=data["created_at"],
            )
        except (KeyError,TypeError,ValueError) as exc:
            raise ValidationError("voice registry record fields are invalid") from exc
        self._validate(profile)
        return profile

    def list(self) -> list[VoiceProfile]:
        return [self.get(path.stem) for path in sorted(self.root.glob("*.json"))]

    def deactivate(self, voice_id: str, *, authority: str, reason: str, at: str | None = None) -> None:
        voice_id = safe_component(voice_id, field="voice_id")
        self.get(voice_id)
        if not isinstance(authority,str) or not isinstance(reason,str) or not authority.strip() or not reason.strip():
            raise ValidationError("deactivation authority and reason are required")
        record = {"voice_id":voice_id,
                   "authority":authority,"reason":reason,"at":at or utc_now()}
        parse_timestamp(record["at"], field="deactivation at")
        canonical=json.dumps(record,sort_keys=True,separators=(",", ":")).encode()
        payload={"schema":"kira.local-voice.deactivation.v2","record":record,
                 "record_hmac_sha256":hmac.new(self._key,canonical,hashlib.sha256).hexdigest()}
        path = contained_path(self.deactivation_root, f"{voice_id}.json")
        with self.mutation_guard():
            try: atomic_write_json_new(path, payload)
            except FileExistsError as exc: raise ConflictError(f"voice is already deactivated: {voice_id}") from exc

    def is_deactivated(self, voice_id: str) -> bool:
        voice_id = safe_component(voice_id, field="voice_id")
        path=contained_path(self.deactivation_root,f"{voice_id}.json")
        if not path.is_file(): return False
        try: envelope=json.loads(path.read_text(encoding="utf-8")); record=envelope["record"]
        except (OSError,json.JSONDecodeError,KeyError,TypeError) as exc: raise ValidationError("deactivation record is invalid") from exc
        canonical=json.dumps(record,sort_keys=True,separators=(",", ":")).encode()
        expected=hmac.new(self._key,canonical,hashlib.sha256).hexdigest()
        if envelope.get("schema")!="kira.local-voice.deactivation.v2" or not hmac.compare_digest(str(envelope.get("record_hmac_sha256","")),expected):
            raise ValidationError("deactivation record failed tamper verification")
        return True

    def mutation_guard(self): return exclusive_file_lock(self.guard_path,timeout=5)

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            if self.key_path.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(self.key_path)):
                raise ValidationError("registry integrity key cannot be a link")
            try:
                info=self.key_path.stat(follow_symlinks=False); key=self.key_path.read_bytes()
            except OSError as exc: raise ValidationError("registry integrity key is unreadable") from exc
            if not stat.S_ISREG(info.st_mode): raise ValidationError("registry integrity key is invalid")
            if len(key)!=32: raise ValidationError("registry integrity key is invalid")
            return key
        key=os.urandom(32)
        try:
            fd=os.open(self.key_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_BINARY",0),0o600)
            with os.fdopen(fd,"wb") as handle: handle.write(key); handle.flush(); os.fsync(handle.fileno())
            return key
        except FileExistsError:
            existing=self.key_path.read_bytes()
            if len(existing)!=32: raise ValidationError("registry integrity key is invalid")
            return existing

    @staticmethod
    def _validate(profile: VoiceProfile) -> None:
        if not isinstance(profile.voice_id,str):
            raise ValidationError("voice_id must be a string")
        safe_component(profile.voice_id,field="voice_id")
        if not isinstance(profile.display_name,str) or not profile.display_name.strip() or len(profile.display_name) > 120:
            raise ValidationError("display_name must be 1-120 visible characters")
        if not isinstance(profile.language,str) or not profile.language or len(profile.language) > 35:
            raise ValidationError("language must be 1-35 characters")
        if not isinstance(profile.description,str) or len(profile.description)>1000:
            raise ValidationError("description must be at most 1000 characters")
        if not isinstance(profile.created_at,str):
            raise ValidationError("created_at must be a string")
        if profile.created_at: parse_timestamp(profile.created_at,field="created_at")
        consent = profile.consent
        required_text = (consent.subject_id, consent.authority, consent.scope, consent.recorded_at)
        if any(not isinstance(value,str) or not value.strip() for value in required_text):
            raise ValidationError("consent subject, authority, scope, and recorded_at are required")
        if any(len(value)>500 for value in required_text):
            raise ValidationError("consent text fields are too long")
        for value in (consent.reference_recording_permitted,consent.generated_audio_permitted,consent.revocable):
            if not isinstance(value,bool): raise ValidationError("consent permission flags must be booleans")
        if not consent.generated_audio_permitted:
            raise ValidationError("consent record does not permit generated audio")
        if consent.evidence_sha256 is not None and (not isinstance(consent.evidence_sha256,str) or not _SHA256.fullmatch(consent.evidence_sha256)):
            raise ValidationError("consent evidence_sha256 must be a lowercase SHA-256 digest")
        recorded_at = parse_timestamp(consent.recorded_at, field="consent recorded_at")
        if recorded_at > datetime.now(UTC):
            raise ValidationError("consent recorded_at cannot be in the future")
        if consent.expires_at is not None:
            expires_at = parse_timestamp(consent.expires_at, field="consent expires_at")
            if expires_at <= recorded_at:
                raise ValidationError("consent expires_at must be after recorded_at")
        if not isinstance(profile.reference_hashes,tuple) or any(not isinstance(item,str) or not _SHA256.fullmatch(item) for item in profile.reference_hashes):
            raise ValidationError("every reference hash must be a lowercase SHA-256 digest")

        if profile.source_basis is SourceBasis.SOURCE_RECORDING_BACKED:
            if consent.basis is not ConsentBasis.SOURCE_SUBJECT_CONSENT:
                raise ValidationError("source-recording-backed voices require source-subject consent")
            if not consent.reference_recording_permitted:
                raise ValidationError("consent does not permit reference-recording use")
            if not consent.evidence_sha256 or not profile.reference_hashes:
                raise ValidationError("source-recording-backed voices require consent evidence and reference hashes")
        elif profile.reference_hashes:
            raise ValidationError("designed and generic fallback voices cannot carry reference hashes")

        if profile.source_basis is SourceBasis.DESIGNED and consent.basis is not ConsentBasis.SYNTHETIC_DESIGN:
            raise ValidationError("designed voices require synthetic-design provenance")
        if (
            profile.source_basis is SourceBasis.GENERIC_FALLBACK
            and consent.basis is not ConsentBasis.GENERIC_NO_IDENTITY
        ):
            raise ValidationError("generic fallback voices require generic-no-identity provenance")
