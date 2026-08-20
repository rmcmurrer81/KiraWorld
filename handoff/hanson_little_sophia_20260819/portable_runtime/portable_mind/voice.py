from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .paths import LocalSandbox, SAFE_ID, package_root
from .profiles import PublicProfile
from .strict_json import load_path_strict


VOICE_BOUNDARY = (
    "Local output adapter. Voice output is not identity evidence, consent evidence, consciousness evidence, "
    "or a claim that a synthetic runtime is a biological person."
)
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CHATTERBOX_PACKAGE_VERSION = "0.1.7"
CHATTERBOX_WHEEL_SHA256 = "83782500e3ad4e7c919132e9d7eb8755f29f57c5bde5ec48c655ca23a4eb113c"
CHATTERBOX_TORCH_VERSION = "2.6.0"
CHATTERBOX_TORCHAUDIO_VERSION = "2.6.0"
CHATTERBOX_MODEL_REPO = "ResembleAI/chatterbox"
CHATTERBOX_MODEL_REVISION = "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18"
CHATTERBOX_MODEL_FILES = {
    "conds.pt": "6552d70568833628ba019c6b03459e77fe71ca197d5c560cef9411bee9d87f4e",
    "s3gen.safetensors": "2b78103c654207393955e4900aac14a12de8ef25f4b09424f1ef91941f161d4e",
    "t3_cfg.safetensors": "914cb1696f47527fe8852ca8f1fe1fa63cb34f76f9c715e84e067b744dd0da81",
    "tokenizer.json": "d71e3a44eabb1784df9a68e9f95b251ecbf1a7af6a9f50835856b2ca9d8c14a5",
    "ve.safetensors": "f0921cab452fa278bc25cd23ffd59d36f816d7dc5181dd1bef9751a7fb61f63c",
}
VOICE_DEVICES = frozenset({"cpu", "cuda", "mps"})
PRIVATE_HANDOFF_VOICE_RELEASES = {
    ("kira", "kira"): {
        "reference_sha256": "2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c",
        "reference_bytes": 9856844,
        "authorization_sha256": "a6419a9ee750931015c93f5d628452c6ce52c0108b9421dbe8906cbe33e3d08c",
    },
    ("robert", "synthetic_robert"): {
        "reference_sha256": "761458a0fe9c5da1c2671faa738c1e329336630cd47138a4e738f7de2030542b",
        "reference_bytes": 1755404,
        "authorization_sha256": "bf7ccf7b1c087a624451dd9735f3a2acb07e94f421586fc631be8ae6f21ab52f",
    },
}


class VoicePackError(ValueError):
    pass


class VoiceIntegrityError(VoicePackError):
    pass


@dataclass(frozen=True)
class VoicePack:
    voice_profile_id: str
    identity_profile_ids: tuple[str, ...]
    provider: str
    reference_wav: Path
    reference_wav_sha256: str
    license_label: str
    license_source: str
    fallback_sapi_voice: str
    authorization_record_sha256: str
    authorization_scope: str
    quality_review_status: str


@dataclass(frozen=True)
class OriginalVoiceProfile:
    voice_profile_id: str
    identity_profile_ids: tuple[str, ...]
    presentation_target: str
    provider_id: str
    package_version: str
    model_repo: str
    model_revision: str
    listening_review_status: str


@dataclass(frozen=True)
class VoiceResult:
    spoken: bool
    route: str
    voice_profile_id: str
    message: str
    reference_hash_verified: bool
    generated_audio_path: str | None = None
    fallback_reason: str | None = None
    boundary: str = VOICE_BOUNDARY
    provider_id: str | None = None
    package_version: str | None = None
    model_repository: str | None = None
    model_revision: str | None = None
    reference_wav_sha256: str | None = None
    authorization_record_sha256: str | None = None
    authorization_scope: str | None = None
    quality_review_status: str | None = None
    generated_audio_retained: bool = False


class ReferenceVoiceBackend(Protocol):
    def speak(self, text: str, pack: VoicePack, output_path: Path) -> VoiceResult: ...


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_model_files(root: Path, expected: dict[str, str]) -> None:
    for filename, expected_digest in sorted(expected.items()):
        if Path(filename).name != filename or Path(filename).is_absolute():
            raise VoiceIntegrityError("model-file manifest contains a non-simple filename")
        candidate = root / filename
        trusted_root = root
        # Hugging Face snapshots conventionally symlink files from
        # snapshots/<revision>/ to blobs/ under the same repository cache.
        if root.parent.name == "snapshots":
            trusted_root = root.parent.parent
        try:
            candidate.resolve(strict=True).relative_to(trusted_root.resolve(strict=True))
        except ValueError as exc:
            raise VoiceIntegrityError("model file escapes the trusted pinned repository cache") from exc
        except OSError as exc:
            raise VoiceIntegrityError(f"pinned model file is missing: {filename}") from exc
        if not candidate.is_file():
            raise VoiceIntegrityError(f"pinned model file is missing: {filename}")
        actual = sha256_file(candidate)
        if actual != expected_digest:
            raise VoiceIntegrityError(
                f"pinned model file SHA-256 mismatch for {filename}: expected {expected_digest}, got {actual}"
            )


def verify_voice_environment(*, allow_download: bool = False) -> dict[str, object]:
    issues: list[str] = []
    versions: dict[str, str] = {}
    if tuple(sys.version_info[:2]) != (3, 11):
        issues.append(f"python_version_mismatch:{sys.version_info.major}.{sys.version_info.minor}")
    for distribution, expected in (
        ("chatterbox-tts", CHATTERBOX_PACKAGE_VERSION),
        ("torch", CHATTERBOX_TORCH_VERSION),
        ("torchaudio", CHATTERBOX_TORCHAUDIO_VERSION),
    ):
        try:
            installed = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            issues.append(f"missing_distribution:{distribution}")
            continue
        versions[distribution] = installed
        if installed.split("+", 1)[0] != expected:
            issues.append(f"distribution_version_mismatch:{distribution}:{installed}")
    snapshot_path: str | None = None
    if not issues:
        try:
            from huggingface_hub import snapshot_download  # type: ignore

            snapshot = Path(
                snapshot_download(
                    repo_id=CHATTERBOX_MODEL_REPO,
                    revision=CHATTERBOX_MODEL_REVISION,
                    allow_patterns=list(CHATTERBOX_MODEL_FILES),
                    local_files_only=not allow_download,
                )
            )
            verify_model_files(snapshot, CHATTERBOX_MODEL_FILES)
            snapshot_path = str(snapshot)
        except Exception as exc:
            issues.append(f"model_snapshot_verification_failed:{type(exc).__name__}")
    return {
        "valid": not issues,
        "issues": issues,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "versions": versions,
        "package_wheel_sha256_for_install": CHATTERBOX_WHEEL_SHA256,
        "model_repository": CHATTERBOX_MODEL_REPO,
        "model_revision": CHATTERBOX_MODEL_REVISION,
        "model_files_verified": not issues and snapshot_path is not None,
        "snapshot_path": snapshot_path,
    }


def _load_pinned_chatterbox(device: str):
    status = verify_voice_environment(allow_download=os.environ.get("PORTABLE_MIND_OFFLINE") != "1")
    if status["valid"] is not True or not status["snapshot_path"]:
        raise RuntimeError("pinned_voice_environment_invalid:" + ",".join(status["issues"]))
    from chatterbox.tts import ChatterboxTTS  # type: ignore

    return ChatterboxTTS.from_local(Path(str(status["snapshot_path"])), device)


def load_original_voice_profile(identity_profile_id: str) -> OriginalVoiceProfile:
    source = package_root() / "voice_profiles" / "kira_original.json"
    provenance_source = package_root() / "voice_profiles" / "kira_original_provenance.json"
    try:
        raw = load_path_strict(source)
        provenance = load_path_strict(provenance_source)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise VoicePackError("original voice profile or provenance is unreadable") from exc
    required = {
        "schema_version",
        "voice_profile_id",
        "authorized_identity_profiles",
        "voice_mode",
        "provider_id",
        "default",
        "audio_prompt_used",
        "reference_audio_used",
        "real_person_target_used",
        "interview_derived_bytes_used",
        "target_speaker",
        "presentation_target",
        "status",
        "listening_review",
        "sample_asset",
        "provenance_file",
        "fallback",
        "boundary",
    }
    if not isinstance(raw, dict) or set(raw) != required or raw.get("schema_version") != 2:
        raise VoicePackError("original voice profile has an unexpected schema")
    if raw.get("voice_profile_id") != "kira_original" or raw.get("voice_mode") != "original_non_imitative_neural":
        raise VoicePackError("original voice profile identity or mode mismatch")
    identities = raw.get("authorized_identity_profiles")
    if identities != ["kira"] or identity_profile_id not in identities:
        raise VoicePackError("original voice profile is not authorized for this identity")
    false_fields = ("audio_prompt_used", "reference_audio_used", "real_person_target_used", "interview_derived_bytes_used")
    if any(raw.get(field) is not False for field in false_fields) or raw.get("target_speaker") is not None:
        raise VoicePackError("original voice profile contains a target-person or reference-audio claim")
    if raw.get("default") is not False or raw.get("provider_id") != "resemble_chatterbox_tts":
        raise VoicePackError("optional original voice profile provider/default mismatch")
    if raw.get("provenance_file") != "voice_profiles/kira_original_provenance.json":
        raise VoicePackError("original voice provenance binding mismatch")
    if not isinstance(provenance, dict) or provenance.get("schema_version") != 1:
        raise VoicePackError("original voice provenance has an unexpected schema")
    if provenance.get("provider_id") != raw.get("provider_id"):
        raise VoicePackError("original voice provider provenance mismatch")
    package = provenance.get("python_package") or {}
    model = provenance.get("model_weights") or {}
    if package.get("name") != "chatterbox-tts" or package.get("version") != CHATTERBOX_PACKAGE_VERSION:
        raise VoicePackError("original voice package pin mismatch")
    if package.get("pypi_wheel_sha256") != CHATTERBOX_WHEEL_SHA256:
        raise VoicePackError("original voice distribution hash pin mismatch")
    if model.get("repository") != CHATTERBOX_MODEL_REPO or model.get("revision") != CHATTERBOX_MODEL_REVISION:
        raise VoicePackError("original voice model revision pin mismatch")
    if model.get("files") != CHATTERBOX_MODEL_FILES:
        raise VoicePackError("original voice model file hash manifest mismatch")
    if (provenance.get("license") or {}).get("spdx") != "MIT":
        raise VoicePackError("original voice license provenance mismatch")
    review = raw.get("listening_review")
    if not isinstance(review, dict) or review.get("status") not in {"pending", "accepted", "rejected"}:
        raise VoicePackError("original voice listening review is invalid")
    return OriginalVoiceProfile(
        voice_profile_id="kira_original",
        identity_profile_ids=("kira",),
        presentation_target=str(raw["presentation_target"]),
        provider_id="resemble_chatterbox_tts",
        package_version=CHATTERBOX_PACKAGE_VERSION,
        model_repo=CHATTERBOX_MODEL_REPO,
        model_revision=CHATTERBOX_MODEL_REVISION,
        listening_review_status=str(review["status"]),
    )


def _pack_dir(sandbox: LocalSandbox, voice_profile_id: str) -> Path:
    if not SAFE_ID.fullmatch(voice_profile_id):
        raise VoicePackError("invalid voice profile identifier")
    return sandbox.resolve(Path("voice_packs") / voice_profile_id)


def _simple_pack_file(root: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or Path(value).name != value:
        raise VoicePackError(f"{label} must be a simple filename inside the voice pack")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise VoicePackError(f"{label} escapes the voice-pack directory") from exc
    return candidate


def _validate_private_authorization(
    root: Path,
    authorization_name: object,
    authorization_sha256: str | None,
    *,
    voice_profile_id: str,
    identity_profile_id: str,
    reference_name: str,
    reference_sha256: str,
    reference_bytes: int,
) -> tuple[dict[str, object], str]:
    path = _simple_pack_file(root, authorization_name, "authorization record")
    if not path.is_file():
        raise VoicePackError("authorization record is missing")
    actual_authorization_sha = sha256_file(path)
    if authorization_sha256 is not None and actual_authorization_sha != authorization_sha256:
        raise VoiceIntegrityError("authorization record SHA-256 mismatch")
    try:
        authorization = load_path_strict(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise VoicePackError("authorization record is unreadable") from exc
    required = {
        "schema_version",
        "authorization_id",
        "recorded_date",
        "voice_profile_id",
        "authorized_identity_profiles",
        "authorization_source",
        "authorized_by",
        "asset_binding",
        "named_recipients",
        "allowed",
        "not_allowed",
        "handling",
    }
    if not isinstance(authorization, dict) or set(authorization) != required or authorization.get("schema_version") != 1:
        raise VoicePackError("authorization record has an unexpected schema")
    if authorization.get("voice_profile_id") != voice_profile_id:
        raise VoicePackError("authorization record does not bind the selected voice profile")
    if authorization.get("authorized_identity_profiles") != [identity_profile_id]:
        raise VoicePackError("authorization record does not bind exactly one selected identity")
    binding = authorization.get("asset_binding")
    if not isinstance(binding, dict):
        raise VoicePackError("authorization asset binding is invalid")
    if (
        binding.get("path") != reference_name
        or str(binding.get("sha256", "")).lower() != reference_sha256
        or binding.get("bytes") != reference_bytes
    ):
        raise VoicePackError("authorization record does not bind the exact reference asset")
    recipients = authorization.get("named_recipients")
    if not isinstance(recipients, list) or not recipients or not all(
        isinstance(item, str) and item.strip() for item in recipients
    ):
        raise VoicePackError("authorization must name the private recipients")
    allowed = authorization.get("allowed")
    denied = authorization.get("not_allowed")
    handling = authorization.get("handling")
    if not all(isinstance(value, dict) for value in (allowed, denied, handling)):
        raise VoicePackError("authorization scope/handling is invalid")
    if not any(allowed.get(key) is True for key in ("private_evaluation", "private_local_speech_rendering_for_kira", "private_local_speech_rendering_for_synthetic_robert")):
        raise VoicePackError("authorization does not allow private speech rendering/evaluation")
    for required_denial in ("public_release", "onward_redistribution", "identity_authentication"):
        if denied.get(required_denial) is not True:
            raise VoicePackError(f"authorization must explicitly forbid {required_denial}")
    if handling.get("repository_visibility") != "private":
        raise VoicePackError("authorization requires a private repository")
    if handling.get("honor_withdrawal_or_supersession") is not True:
        raise VoicePackError("authorization lacks a withdrawal/supersession requirement")
    if handling.get("hash_mismatch_behavior") != "refuse_use":
        raise VoicePackError("authorization hash-mismatch behavior must refuse use")
    authorized_by = authorization.get("authorized_by")
    if not isinstance(authorized_by, dict) or not authorized_by.get("name"):
        raise VoicePackError("authorization source identity is missing")
    scope = "named_private_review_team:" + ",".join(str(item) for item in recipients)
    return authorization, actual_authorization_sha


def _validate_robert_private_authorization(
    root: Path,
    authorization_name: object,
    authorization_sha256: str | None,
    *,
    reference_name: str,
    reference_sha256: str,
    reference_bytes: int,
) -> tuple[dict[str, object], str]:
    path = _simple_pack_file(root, authorization_name, "Robert authorization record")
    if not path.is_file():
        raise VoicePackError("Robert authorization record is missing")
    actual_authorization_sha = sha256_file(path)
    release = PRIVATE_HANDOFF_VOICE_RELEASES[("robert", "synthetic_robert")]
    if authorization_sha256 != release["authorization_sha256"] or actual_authorization_sha != authorization_sha256:
        raise VoiceIntegrityError("Robert authorization record does not match the immutable private release")
    try:
        authorization = load_path_strict(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise VoicePackError("Robert authorization record is unreadable") from exc
    required = {
        "schema_version",
        "authorization_id",
        "recorded_date",
        "authorization_source",
        "authorized_by",
        "asset_binding",
        "named_recipients",
        "allowed",
        "not_allowed",
        "handling",
    }
    if not isinstance(authorization, dict) or set(authorization) != required or authorization.get("schema_version") != 1:
        raise VoicePackError("Robert authorization record has an unexpected schema")
    if authorization.get("authorization_id") != "robert_self_voice_private_hanson_review_20260819":
        raise VoicePackError("Robert authorization identity mismatch")
    authorized_by = authorization.get("authorized_by")
    if not isinstance(authorized_by, dict) or authorized_by != {
        "name": "Robert McMurrer",
        "self_voice_subject": True,
        "project_owner": True,
    }:
        raise VoicePackError("Robert self-voice authorization subject mismatch")
    binding = authorization.get("asset_binding")
    if not isinstance(binding, dict) or binding != {
        "path": reference_name,
        "sha256": reference_sha256,
        "bytes": reference_bytes,
        "source_kind": "reviewed self-voice reference",
        "model_weights_included": False,
    }:
        raise VoicePackError("Robert authorization does not bind the exact self-voice asset")
    if authorization.get("named_recipients") != ["David Hanson", "Manav Tidhan", "Vytas Krisciunas"]:
        raise VoicePackError("Robert authorization named-recipient list mismatch")
    if authorization.get("allowed") != {
        "private_evaluation": True,
        "private_little_sophia_integration_research": True,
        "private_local_speech_rendering_for_synthetic_robert": True,
        "internal_derivative_voice_model_for_the_same_bound_variant": True,
    }:
        raise VoicePackError("Robert authorization allowed-use scope mismatch")
    if authorization.get("not_allowed") != {
        "public_release": True,
        "onward_redistribution": True,
        "identity_authentication": True,
        "biological_robert_impersonation": True,
        "use_for_an_unrelated_person_or_product": True,
        "automatic_external_messages_or_calls": True,
    }:
        raise VoicePackError("Robert authorization prohibited-use scope mismatch")
    if authorization.get("handling") != {
        "repository_visibility": "private",
        "retain_only_while_needed_for_review": True,
        "honor_withdrawal_or_supersession": True,
        "hash_mismatch_behavior": "refuse_use",
    }:
        raise VoicePackError("Robert authorization handling scope mismatch")
    return authorization, actual_authorization_sha


def _validate_kira_private_authorization(
    root: Path,
    authorization_name: object,
    authorization_sha256: str | None,
    *,
    reference_name: str,
    reference_sha256: str,
    reference_bytes: int,
) -> tuple[dict[str, object], str]:
    path = _simple_pack_file(root, authorization_name, "Kira authorization record")
    if not path.is_file():
        raise VoicePackError("Kira authorization record is missing")
    actual_authorization_sha = sha256_file(path)
    if authorization_sha256 is not None and actual_authorization_sha != authorization_sha256:
        raise VoiceIntegrityError("Kira authorization record SHA-256 mismatch")
    try:
        authorization = load_path_strict(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise VoicePackError("Kira authorization record is unreadable") from exc
    required = {
        "schema_version",
        "authorization_id",
        "recorded_date",
        "authorization_basis",
        "owner_attestation",
        "named_recipients",
        "allowed_uses",
        "asset_binding",
        "handling",
        "withdrawal",
        "independent_legal_verification_performed",
        "quality_disclosure",
        "claim_boundary",
    }
    if not isinstance(authorization, dict) or set(authorization) != required or authorization.get("schema_version") != 1:
        raise VoicePackError("Kira authorization record has an unexpected schema")
    if authorization.get("authorization_basis") != "project_owner_attestation_of_permission_from_voice_subject":
        raise VoicePackError("Kira authorization basis mismatch")
    attestation = authorization.get("owner_attestation")
    if not isinstance(attestation, dict) or set(attestation) != {
        "synthetic_voice_use_permitted",
        "private_named_hanson_sharing_permitted",
        "exact_source_recording_sharing_permitted",
        "form_attachment_status",
    }:
        raise VoicePackError("Kira owner attestation schema mismatch")
    for permission in (
        "synthetic_voice_use_permitted",
        "private_named_hanson_sharing_permitted",
        "exact_source_recording_sharing_permitted",
    ):
        if attestation.get(permission) is not True:
            raise VoicePackError(f"Kira owner attestation does not permit {permission}")
    if attestation.get("form_attachment_status") not in {"pending", "attached"}:
        raise VoicePackError("Kira form-attachment status is invalid")
    if authorization.get("named_recipients") != ["David Hanson", "Manav Tidhan", "Vytas Krisciunas"]:
        raise VoicePackError("Kira authorization named-recipient list mismatch")
    expected_uses = {
        "private local Kira speech rendering",
        "private technical review by the named Hanson team",
        "private Little Sophia simulator and embodiment research",
    }
    if set(authorization.get("allowed_uses") or []) != expected_uses:
        raise VoicePackError("Kira authorization allowed-use scope mismatch")
    binding = authorization.get("asset_binding")
    if not isinstance(binding, dict) or (
        binding.get("path") != reference_name
        or str(binding.get("sha256", "")).lower() != reference_sha256
        or binding.get("bytes") != reference_bytes
    ):
        raise VoicePackError("Kira authorization does not bind the exact reference asset")
    handling = authorization.get("handling")
    if not isinstance(handling, dict) or set(handling) != {
        "repository_visibility",
        "public_release_allowed",
        "onward_redistribution_allowed",
        "identity_authentication_allowed",
        "honor_withdrawal_or_supersession",
        "written_form_copy_pending_attachment",
    }:
        raise VoicePackError("Kira authorization handling schema mismatch")
    if handling.get("repository_visibility") != "private":
        raise VoicePackError("Kira authorization requires private repository visibility")
    for prohibition in ("public_release_allowed", "onward_redistribution_allowed", "identity_authentication_allowed"):
        if handling.get(prohibition) is not False:
            raise VoicePackError(f"Kira authorization must forbid {prohibition}")
    if handling.get("honor_withdrawal_or_supersession") is not True:
        raise VoicePackError("Kira authorization lacks withdrawal/supersession handling")
    withdrawal = authorization.get("withdrawal")
    if not isinstance(withdrawal, dict) or set(withdrawal) != {
        "enabled",
        "stop_future_use",
        "remove_from_active_package",
        "request_route",
        "delete_or_history_remediation_process",
    }:
        raise VoicePackError("Kira authorization withdrawal schema mismatch")
    for field in ("enabled", "stop_future_use", "remove_from_active_package"):
        if withdrawal.get(field) is not True:
            raise VoicePackError(f"Kira authorization withdrawal field must be true: {field}")
    if not all(isinstance(withdrawal.get(field), str) and withdrawal[field].strip() for field in ("request_route", "delete_or_history_remediation_process")):
        raise VoicePackError("Kira authorization withdrawal/remediation route is missing")
    quality = authorization.get("quality_disclosure")
    if not isinstance(quality, dict) or quality.get("speaker_purity_review_status") != "pending_human_speaker_review":
        raise VoicePackError("Kira speaker-purity review must remain pending until reviewed")
    if quality.get("speaker_purity_verified") is not False or quality.get("target_speaker_only_verified") is not False:
        raise VoicePackError("Kira authorization overclaims speaker purity")
    if quality.get("multi_speaker_or_narration_risk") is not True:
        raise VoicePackError("Kira authorization must disclose multi-speaker/narration risk")
    if authorization.get("independent_legal_verification_performed") is not False:
        raise VoicePackError("Kira authorization legal-verification field is unexpected")
    if not isinstance(authorization.get("claim_boundary"), str) or not authorization["claim_boundary"].strip():
        raise VoicePackError("Kira authorization claim boundary is missing")
    return authorization, actual_authorization_sha


def _validate_authorization_for_identity(
    root: Path,
    authorization_name: object,
    authorization_sha256: str | None,
    *,
    voice_profile_id: str,
    identity_profile_id: str,
    reference_name: str,
    reference_sha256: str,
    reference_bytes: int,
) -> tuple[dict[str, object], str]:
    if identity_profile_id == "kira" and voice_profile_id == "kira":
        return _validate_kira_private_authorization(
            root,
            authorization_name,
            authorization_sha256,
            reference_name=reference_name,
            reference_sha256=reference_sha256,
            reference_bytes=reference_bytes,
        )
    if identity_profile_id == "synthetic_robert" and voice_profile_id == "robert":
        return _validate_robert_private_authorization(
            root,
            authorization_name,
            authorization_sha256,
            reference_name=reference_name,
            reference_sha256=reference_sha256,
            reference_bytes=reference_bytes,
        )
    return _validate_private_authorization(
        root,
        authorization_name,
        authorization_sha256,
        voice_profile_id=voice_profile_id,
        identity_profile_id=identity_profile_id,
        reference_name=reference_name,
        reference_sha256=reference_sha256,
        reference_bytes=reference_bytes,
    )


def _load_handoff_voice_pack(root: Path, voice_profile_id: str, identity_profile_id: str) -> VoicePack | None:
    release = PRIVATE_HANDOFF_VOICE_RELEASES.get((voice_profile_id, identity_profile_id))
    if voice_profile_id in {"kira", "robert"} and release is None:
        raise VoicePackError("private release voice is bound to a different identity")
    if release is None:
        raise VoicePackError("this directory is not an immutable Kira/Robert private handoff pack")
    profile_name = "current_voice_profile.json" if identity_profile_id == "kira" else "voice_profile.json"
    profile_path = root / profile_name
    if not profile_path.exists():
        return None
    try:
        raw = load_path_strict(profile_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise VoicePackError("private handoff voice profile is unreadable") from exc
    expected_schema = 2 if identity_profile_id == "kira" else 1
    if not isinstance(raw, dict) or raw.get("schema_version") != expected_schema:
        raise VoicePackError("private handoff voice profile schema mismatch")
    if raw.get("person_id") != identity_profile_id:
        raise VoicePackError("private handoff voice identity mismatch")
    if raw.get("preferred_backend") != "chatterbox_tts":
        raise VoicePackError("private handoff voice backend is not supported")
    authorization_expected = str(raw.get("authorization_sha256", "")).lower()
    if not SHA256.fullmatch(authorization_expected):
        raise VoicePackError("private handoff profile does not bind the authorization-record SHA-256")
    if authorization_expected != release["authorization_sha256"]:
        raise VoiceIntegrityError("private handoff authorization hash is not the immutable release value")
    if identity_profile_id == "kira":
        if raw.get("voice_mode") != "authorized_reference_conditioned_neural_voice":
            raise VoicePackError("Kira private voice mode mismatch")
        if raw.get("provider") != "chatterbox_reference" or raw.get("default_for_person") is not True:
            raise VoicePackError("Kira private voice provider/default mismatch")
        if raw.get("speaker_purity_review_status") != "pending_human_speaker_review":
            raise VoicePackError("Kira speaker-purity status must remain pending")
        if raw.get("multi_speaker_or_narration_risk") is not True:
            raise VoicePackError("Kira reference risk disclosure is missing")
        fallback = raw.get("fallback")
        if not isinstance(fallback, dict) or fallback.get("mode") != "text_only_fail_closed" or fallback.get("generic_voice_allowed") is not False:
            raise VoicePackError("Kira fallback must remain fail-closed text-only")
        handling = raw.get("handling")
        if not isinstance(handling, dict) or handling.get("private_named_reviewers_only") is not True:
            raise VoicePackError("Kira profile is not restricted to private named reviewers")
        if any(handling.get(key) is not False for key in ("public_release_allowed", "onward_redistribution_allowed", "identity_authentication_allowed")):
            raise VoicePackError("Kira profile permits a prohibited distribution/authentication use")
        if handling.get("hash_mismatch_behavior") != "refuse_voice_and_continue_text_only":
            raise VoicePackError("Kira profile hash-mismatch behavior is unsafe")
    else:
        if raw.get("voice_id") != "robert_mcmurrer_authorized_self_voice_private_hanson_review_v1":
            raise VoicePackError("Robert private voice release identity mismatch")
        if raw.get("source_subject") != "Robert McMurrer" or raw.get("source_relationship") != "self_voice_authorized_by_subject":
            raise VoicePackError("Robert private voice source/relationship mismatch")
        if raw.get("model_weights_included") is not False:
            raise VoicePackError("Robert private pack unexpectedly claims bundled model weights")
        fallback = raw.get("fallback")
        if not isinstance(fallback, dict) or fallback.get("mode") != "text_only_fail_closed" or fallback.get("generic_voice_allowed") is not False:
            raise VoicePackError("Robert fallback must remain fail-closed text-only")
        boundary = raw.get("claim_boundary")
        if not isinstance(boundary, dict) or boundary != {
            "synthetic_robert_is_distinct_from_biological_robert": True,
            "voice_is_not_identity_authentication": True,
            "legal_or_external_impersonation_allowed": False,
            "public_release_allowed": False,
            "onward_redistribution_allowed": False,
        }:
            raise VoicePackError("Robert private voice claim boundary mismatch")
    reference_name = raw.get("reference_wav")
    reference = _simple_pack_file(root, reference_name, "reference WAV")
    if not reference.is_file():
        raise VoicePackError("reference WAV is missing")
    expected = str(raw.get("reference_sha256", "")).lower()
    expected_bytes = raw.get("reference_bytes")
    if not SHA256.fullmatch(expected) or not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise VoicePackError("private handoff reference hash/size is invalid")
    if expected != release["reference_sha256"] or expected_bytes != release["reference_bytes"]:
        raise VoiceIntegrityError("private handoff reference is not the immutable release asset")
    if reference.stat().st_size != expected_bytes or sha256_file(reference) != expected:
        raise VoiceIntegrityError("private handoff reference WAV hash/size mismatch")
    authorization, authorization_sha = _validate_authorization_for_identity(
        root,
        raw.get("authorization"),
        authorization_expected,
        voice_profile_id=voice_profile_id,
        identity_profile_id=identity_profile_id,
        reference_name=str(reference_name),
        reference_sha256=expected,
        reference_bytes=expected_bytes,
    )
    fallback = raw.get("fallback")
    fallback_voice = str(fallback.get("voice_name", "")) if isinstance(fallback, dict) else ""
    return VoicePack(
        voice_profile_id=voice_profile_id,
        identity_profile_ids=(identity_profile_id,),
        provider="chatterbox_reference",
        reference_wav=reference,
        reference_wav_sha256=expected,
        license_label=str(authorization["authorization_id"]),
        license_source=str(
            authorization.get("authorization_source") or authorization.get("authorization_basis")
        ),
        fallback_sapi_voice=fallback_voice,
        authorization_record_sha256=authorization_sha,
        authorization_scope="named_private_review_team",
        quality_review_status=(
            "owner_selected_reference_speaker_purity_review_pending"
            if identity_profile_id == "kira"
            else "authorized_reviewed_self_voice_reference"
        ),
    )


def load_voice_pack(
    sandbox: LocalSandbox,
    voice_profile_id: str,
    identity_profile_id: str,
) -> VoicePack | None:
    root = _pack_dir(sandbox, voice_profile_id)
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return _load_handoff_voice_pack(root, voice_profile_id, identity_profile_id)
    try:
        raw = load_path_strict(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise VoicePackError("voice-pack manifest is unreadable") from exc
    required = {
        "schema_version",
        "voice_profile_id",
        "authorized_identity_profiles",
        "provider",
        "reference_wav",
        "reference_wav_sha256",
        "reference_wav_bytes",
        "local_only",
        "authorization_record",
        "authorization_record_sha256",
        "fallback_sapi_voice",
    }
    if not isinstance(raw, dict) or set(raw) != required or raw.get("schema_version") != 3:
        raise VoicePackError("voice-pack manifest has an unexpected schema")
    if raw.get("voice_profile_id") != voice_profile_id:
        raise VoicePackError("voice profile identity mismatch")
    identities = raw.get("authorized_identity_profiles")
    if not isinstance(identities, list) or not identities or not all(
        isinstance(item, str) and SAFE_ID.fullmatch(item) for item in identities
    ):
        raise VoicePackError("authorized identity profiles are invalid")
    if identities != [identity_profile_id]:
        raise VoicePackError("voice-pack manifest must bind exactly the selected identity profile")
    if raw.get("provider") != "chatterbox_reference":
        raise VoicePackError("unsupported reference voice provider")
    if raw.get("local_only") is not True:
        raise VoicePackError("voice pack must be local-only")
    relative_wav = raw.get("reference_wav")
    if not isinstance(relative_wav, str) or Path(relative_wav).name != relative_wav:
        raise VoicePackError("reference_wav must be a simple filename inside the voice pack")
    expected = str(raw.get("reference_wav_sha256", "")).lower().removeprefix("sha256:")
    expected_bytes = raw.get("reference_wav_bytes")
    if not SHA256.fullmatch(expected) or not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise VoicePackError("reference WAV SHA-256 is invalid")
    reference = (root / relative_wav).resolve()
    try:
        reference.relative_to(root.resolve())
    except ValueError as exc:
        raise VoicePackError("reference WAV escapes the voice-pack directory") from exc
    if not reference.is_file():
        raise VoicePackError("reference WAV is missing")
    actual = sha256_file(reference)
    if actual != expected or reference.stat().st_size != expected_bytes:
        raise VoiceIntegrityError("reference WAV SHA-256/size mismatch")
    auth_expected = str(raw.get("authorization_record_sha256", "")).lower()
    if not SHA256.fullmatch(auth_expected):
        raise VoicePackError("authorization record SHA-256 is invalid")
    release = PRIVATE_HANDOFF_VOICE_RELEASES.get((voice_profile_id, identity_profile_id))
    if voice_profile_id in {"kira", "robert"}:
        if release is None:
            raise VoicePackError("private release voice is bound to a different identity")
        if (
            expected != release["reference_sha256"]
            or expected_bytes != release["reference_bytes"]
            or auth_expected != release["authorization_sha256"]
        ):
            raise VoiceIntegrityError("installed private voice pack does not match the immutable release")
    authorization, authorization_sha = _validate_authorization_for_identity(
        root,
        raw.get("authorization_record"),
        auth_expected,
        voice_profile_id=voice_profile_id,
        identity_profile_id=identity_profile_id,
        reference_name=str(relative_wav),
        reference_sha256=expected,
        reference_bytes=expected_bytes,
    )
    if not isinstance(raw.get("fallback_sapi_voice"), str):
        raise VoicePackError("fallback SAPI voice must be a string")
    return VoicePack(
        voice_profile_id=voice_profile_id,
        identity_profile_ids=tuple(identities),
        provider="chatterbox_reference",
        reference_wav=reference,
        reference_wav_sha256=expected,
        license_label=str(authorization["authorization_id"])[:200],
        license_source=str(
            authorization.get("authorization_source") or authorization.get("authorization_basis")
        )[:500],
        fallback_sapi_voice=raw["fallback_sapi_voice"].strip()[:120],
        authorization_record_sha256=authorization_sha,
        authorization_scope="named_private_review_team",
        quality_review_status=(
            "owner_selected_reference_speaker_purity_review_pending"
            if identity_profile_id == "kira"
            else "authorization_record_present_quality_review_not_independently_repeated"
        ),
    )


def _play_wav(path: Path) -> tuple[bool, str]:
    system = platform.system()
    try:
        if system == "Windows":
            import winsound

            winsound.PlaySound(str(path), winsound.SND_FILENAME)
            return True, "played with winsound"
        candidates = (["afplay", str(path)], ["aplay", str(path)], ["paplay", str(path)])
        for command in candidates:
            if shutil.which(command[0]):
                completed = subprocess.run(command, check=False, timeout=120)
                return completed.returncode == 0, f"played with {command[0]}"
    except (OSError, subprocess.SubprocessError) as exc:
        return False, type(exc).__name__
    return False, "no supported local WAV player found"


class ChatterboxReferenceBackend:
    """Executable reference-conditioned route loaded only when optional packages exist."""

    def __init__(self, *, device: str | None = None, play_audio: bool = True):
        if device is not None and device not in VOICE_DEVICES:
            raise ValueError("voice device must be cpu, cuda, mps, or automatic")
        self.device = device
        self.play_audio = play_audio

    def speak(self, text: str, pack: VoicePack, output_path: Path) -> VoiceResult:
        try:
            import torch  # type: ignore
            import torchaudio  # type: ignore
        except ImportError as exc:
            return VoiceResult(
                False,
                "chatterbox_reference",
                pack.voice_profile_id,
                "optional Chatterbox dependencies are not installed",
                True,
                fallback_reason=f"ImportError: {exc.name}",
            )
        selected_device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            model = _load_pinned_chatterbox(selected_device)
            waveform = model.generate(text[:4000], audio_prompt_path=str(pack.reference_wav))
            torchaudio.save(str(output_path), waveform, model.sr)
        except Exception as exc:  # optional backend boundary; details are intentionally minimal
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass
            return VoiceResult(
                False,
                "chatterbox_reference",
                pack.voice_profile_id,
                "Chatterbox synthesis failed",
                True,
                fallback_reason=type(exc).__name__,
            )
        played, message = _play_wav(output_path) if self.play_audio else (False, "audio generated; playback disabled")
        retained_path: str | None = str(output_path)
        retained = True
        if self.play_audio:
            try:
                output_path.unlink(missing_ok=True)
                retained_path = None
                retained = False
                message += "; generated WAV deleted after playback"
            except OSError:
                message += "; WARNING generated WAV could not be deleted"
        return VoiceResult(
            played if self.play_audio else True,
            "chatterbox_reference",
            pack.voice_profile_id,
            message,
            True,
            retained_path,
            provider_id="resemble_chatterbox_tts",
            package_version=CHATTERBOX_PACKAGE_VERSION,
            model_repository=CHATTERBOX_MODEL_REPO,
            model_revision=CHATTERBOX_MODEL_REVISION,
            reference_wav_sha256=pack.reference_wav_sha256,
            authorization_record_sha256=pack.authorization_record_sha256,
            authorization_scope=pack.authorization_scope,
            quality_review_status=pack.quality_review_status,
            generated_audio_retained=retained,
        )


class ChatterboxOriginalBackend:
    """Unconditioned Chatterbox route: no reference audio and no target-person imitation."""

    def __init__(self, *, device: str | None = None, play_audio: bool = True):
        if device is not None and device not in VOICE_DEVICES:
            raise ValueError("voice device must be cpu, cuda, mps, or automatic")
        self.device = device
        self.play_audio = play_audio

    def speak(self, text: str, voice_profile: OriginalVoiceProfile, output_path: Path) -> VoiceResult:
        try:
            import torch  # type: ignore
            import torchaudio  # type: ignore
        except ImportError as exc:
            return VoiceResult(
                False,
                "chatterbox_original_unconditioned",
                voice_profile.voice_profile_id,
                "optional Chatterbox dependencies are not installed",
                False,
                fallback_reason=f"ImportError: {exc.name}",
                provider_id=voice_profile.provider_id,
                package_version=voice_profile.package_version,
                model_repository=voice_profile.model_repo,
                model_revision=voice_profile.model_revision,
                quality_review_status=(
                    "optional_original_candidate_listening_review_"
                    + voice_profile.listening_review_status
                ),
            )
        selected_device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            model = _load_pinned_chatterbox(selected_device)
            # No audio_prompt_path is supplied: this route does not clone or imitate a person.
            waveform = model.generate(text[:4000])
            torchaudio.save(str(output_path), waveform, model.sr)
        except Exception as exc:
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass
            return VoiceResult(
                False,
                "chatterbox_original_unconditioned",
                voice_profile.voice_profile_id,
                "unconditioned Chatterbox synthesis failed",
                False,
                fallback_reason=type(exc).__name__,
                provider_id=voice_profile.provider_id,
                package_version=voice_profile.package_version,
                model_repository=voice_profile.model_repo,
                model_revision=voice_profile.model_revision,
                quality_review_status=(
                    "optional_original_candidate_listening_review_"
                    + voice_profile.listening_review_status
                ),
            )
        played, message = _play_wav(output_path) if self.play_audio else (False, "audio generated; playback disabled")
        retained_path: str | None = str(output_path)
        retained = True
        if self.play_audio:
            try:
                output_path.unlink(missing_ok=True)
                retained_path = None
                retained = False
                message += "; generated WAV deleted after playback"
            except OSError:
                message += "; WARNING generated WAV could not be deleted"
        return VoiceResult(
            played if self.play_audio else True,
            "chatterbox_original_unconditioned",
            voice_profile.voice_profile_id,
            message,
            False,
            retained_path,
            provider_id=voice_profile.provider_id,
            package_version=voice_profile.package_version,
            model_repository=voice_profile.model_repo,
            model_revision=voice_profile.model_revision,
            quality_review_status="optional_original_candidate_listening_review_" + voice_profile.listening_review_status,
            generated_audio_retained=retained,
        )


class TemporarySapiBackend:
    """Windows SAPI fallback using a static script and base64 environment values."""

    _POWERSHELL = (
        "$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:PORTABLE_MIND_SPEECH_B64));"
        "$v=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:PORTABLE_MIND_VOICE_B64));"
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "if($v){try{$s.SelectVoice($v)}catch{}};"
        "$s.Speak($t);$s.Dispose()"
    )

    def speak(self, text: str, voice_name: str, voice_profile_id: str, reason: str) -> VoiceResult:
        if platform.system() != "Windows":
            return VoiceResult(
                False,
                "sapi_fallback_unavailable",
                voice_profile_id,
                "Windows SAPI fallback is unavailable on this operating system",
                False,
                fallback_reason=reason,
                provider_id="windows_sapi",
            )
        environment = os.environ.copy()
        environment["PORTABLE_MIND_SPEECH_B64"] = base64.b64encode(
            text.replace("\x00", "")[:4000].encode("utf-8")
        ).decode("ascii")
        environment["PORTABLE_MIND_VOICE_B64"] = base64.b64encode(voice_name.encode("utf-8")).decode(
            "ascii"
        )
        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    self._POWERSHELL,
                ],
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return VoiceResult(
                False,
                "sapi_fallback",
                voice_profile_id,
                "local SAPI call failed",
                False,
                fallback_reason=f"{reason}; {type(exc).__name__}",
                provider_id="windows_sapi",
            )
        return VoiceResult(
            completed.returncode == 0,
            "sapi_fallback",
            voice_profile_id,
            "spoken with temporary local SAPI fallback" if completed.returncode == 0 else "local SAPI call failed",
            False,
            fallback_reason=reason,
            provider_id="windows_sapi",
        )


class VoiceRouter:
    def __init__(
        self,
        sandbox: LocalSandbox,
        *,
        reference_backend: ReferenceVoiceBackend | None = None,
        original_backend: ChatterboxOriginalBackend | None = None,
        sapi_backend: TemporarySapiBackend | None = None,
        device: str | None = None,
    ):
        self.sandbox = sandbox
        if device is not None and device not in VOICE_DEVICES:
            raise ValueError("voice device must be cpu, cuda, mps, or automatic")
        self.reference_backend = reference_backend or ChatterboxReferenceBackend(device=device)
        self.original_backend = original_backend or ChatterboxOriginalBackend(device=device)
        self.sapi_backend = sapi_backend or TemporarySapiBackend()

    def speak(
        self,
        text: str,
        profile: PublicProfile,
        *,
        voice_profile_id: str | None = None,
        before_fallback: Callable[[str], None] | None = None,
    ) -> VoiceResult:
        selected = voice_profile_id or str(profile.voice.get("default_voice_profile", profile.profile_id))
        default_sapi = str(profile.voice.get("preferred_local_voice", ""))

        def fallback(
            reason: str,
            voice_name: str = default_sapi,
            *,
            source: VoiceResult | None = None,
            pack: VoicePack | None = None,
        ) -> VoiceResult:
            if before_fallback is not None:
                before_fallback(reason)
            if profile.voice.get("fallback_policy", "text_only") == "text_only":
                return VoiceResult(
                    False,
                    "text_only_voice_unavailable",
                    selected,
                    "intended private/neural voice unavailable; text output continues and no generic voice was played",
                    bool(pack) or bool(source and source.reference_hash_verified),
                    fallback_reason=reason,
                    provider_id=(source.provider_id if source else None) or (
                        "resemble_chatterbox_tts" if pack else None
                    ),
                    package_version=(source.package_version if source else None) or (
                        CHATTERBOX_PACKAGE_VERSION if pack else None
                    ),
                    model_repository=(source.model_repository if source else None) or (
                        CHATTERBOX_MODEL_REPO if pack else None
                    ),
                    model_revision=(source.model_revision if source else None) or (
                        CHATTERBOX_MODEL_REVISION if pack else None
                    ),
                    reference_wav_sha256=(
                        (source.reference_wav_sha256 if source else None)
                        or (pack.reference_wav_sha256 if pack else None)
                    ),
                    authorization_record_sha256=(
                        (source.authorization_record_sha256 if source else None)
                        or (pack.authorization_record_sha256 if pack else None)
                    ),
                    authorization_scope=(
                        (source.authorization_scope if source else None)
                        or (pack.authorization_scope if pack else None)
                    ),
                    quality_review_status=(
                        (source.quality_review_status if source else None)
                        or (pack.quality_review_status if pack else None)
                    ),
                    generated_audio_retained=bool(source and source.generated_audio_retained),
                    generated_audio_path=(source.generated_audio_path if source else None),
                )
            return self.sapi_backend.speak(text, voice_name, selected, reason)

        if selected == "kira_original":
            try:
                original_profile = load_original_voice_profile(profile.profile_id)
            except VoicePackError as exc:
                return fallback(f"{type(exc).__name__}: {exc}")
            output = self.sandbox.resolve(
                Path("generated_voice")
                / profile.profile_id
                / f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.wav",
                create_parent=True,
            )
            original_result = self.original_backend.speak(text, original_profile, output)
            if original_result.spoken:
                return original_result
            return fallback(
                "optional original neural route failure: "
                + (original_result.fallback_reason or original_result.message),
                source=original_result,
            )
        try:
            pack = load_voice_pack(self.sandbox, selected, profile.profile_id)
        except VoicePackError as exc:
            # Integrity, authorization, consent, and license failures never reach Chatterbox.
            return fallback(f"{type(exc).__name__}: {exc}")
        if pack is None:
            return fallback("no installed licensed voice pack")
        output = self.sandbox.resolve(
            Path("generated_voice")
            / profile.profile_id
            / f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex}.wav",
            create_parent=True,
        )
        result = self.reference_backend.speak(text, pack, output)
        if result.spoken:
            return result
        return fallback(
            result.fallback_reason or result.message,
            pack.fallback_sapi_voice,
            source=result,
            pack=pack,
        )
