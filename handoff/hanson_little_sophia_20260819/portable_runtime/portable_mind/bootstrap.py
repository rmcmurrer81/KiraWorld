from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .runtime import ConversationRuntime
from .strict_json import load_path_strict
from .transfer import import_hanson_review_seed
from .voice import VoicePackError, _load_handoff_voice_pack, load_voice_pack


class BootstrapError(ValueError):
    pass


@dataclass(frozen=True)
class BootstrapResult:
    profile_id: str
    seed_filename: str
    seed_items_imported: int
    voice_profile_id: str
    voice_installed_now: bool
    reference_wav_sha256: str
    authorization_record_sha256: str
    destination_scope: str = "ignored_local_data_private_runtime_only"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = load_path_strict(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise BootstrapError(f"cannot read required private handoff JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise BootstrapError(f"required private handoff JSON is not an object: {path.name}")
    return value


def install_authorized_voice_pack(
    runtime: ConversationRuntime,
    handoff_root: Path,
) -> tuple[bool, str, str]:
    if runtime.profile_id not in {"kira", "synthetic_robert"}:
        raise BootstrapError("the named private handoff contains packs only for Kira and Synthetic Robert")
    voice_profile_id = "kira" if runtime.profile_id == "kira" else "robert"
    source_root = (handoff_root / "voice_packs" / voice_profile_id).resolve()
    if not source_root.is_dir():
        raise BootstrapError(f"private handoff voice pack is missing: {voice_profile_id}")
    source_pack = _load_handoff_voice_pack(source_root, voice_profile_id, runtime.profile_id)
    if source_pack is None:
        raise BootstrapError("private handoff voice profile is missing")
    profile_name = "current_voice_profile.json" if runtime.profile_id == "kira" else "voice_profile.json"
    source_profile = _read_json(source_root / profile_name)
    authorization_name = source_profile.get("authorization")
    if not isinstance(authorization_name, str) or Path(authorization_name).name != authorization_name:
        raise BootstrapError("private handoff authorization filename is unsafe")
    destination = runtime.sandbox.resolve(Path("voice_packs") / voice_profile_id)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "manifest.json"
    if manifest_path.exists():
        installed = load_voice_pack(runtime.sandbox, voice_profile_id, runtime.profile_id)
        if installed is None:
            raise BootstrapError("existing local voice pack cannot be validated")
        if (
            installed.reference_wav_sha256 != source_pack.reference_wav_sha256
            or installed.authorization_record_sha256 != source_pack.authorization_record_sha256
        ):
            raise BootstrapError("existing local voice pack differs from the authorized handoff; refusing overwrite")
        return False, installed.reference_wav_sha256, installed.authorization_record_sha256
    if any(destination.iterdir()):
        raise BootstrapError("local voice-pack directory is non-empty but has no validated manifest")
    reference_name = source_pack.reference_wav.name
    authorization_source = source_root / authorization_name
    reference_destination = destination / reference_name
    authorization_destination = destination / authorization_name
    shutil.copyfile(source_pack.reference_wav, reference_destination)
    shutil.copyfile(authorization_source, authorization_destination)
    manifest = {
        "schema_version": 3,
        "voice_profile_id": voice_profile_id,
        "authorized_identity_profiles": [runtime.profile_id],
        "provider": "chatterbox_reference",
        "reference_wav": reference_name,
        "reference_wav_sha256": source_pack.reference_wav_sha256,
        "reference_wav_bytes": reference_destination.stat().st_size,
        "local_only": True,
        "authorization_record": authorization_name,
        "authorization_record_sha256": source_pack.authorization_record_sha256,
        "fallback_sapi_voice": source_pack.fallback_sapi_voice,
    }
    temporary = destination / f"manifest.{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, manifest_path)
    installed = load_voice_pack(runtime.sandbox, voice_profile_id, runtime.profile_id)
    if installed is None:
        raise BootstrapError("installed local voice pack did not validate")
    return True, installed.reference_wav_sha256, installed.authorization_record_sha256


def _prevalidate_private_handoff(
    runtime: ConversationRuntime,
    root: Path,
    seed_source: Path,
    seed_filename: str,
) -> None:
    """Validate both source artifacts and destination conflicts before any install write."""

    voice_profile_id = "kira" if runtime.profile_id == "kira" else "robert"
    source_root = (root / "voice_packs" / voice_profile_id).resolve()
    source_pack = _load_handoff_voice_pack(source_root, voice_profile_id, runtime.profile_id)
    if source_pack is None:
        raise BootstrapError("private handoff voice profile is missing")

    destination = runtime.sandbox.resolve(Path("voice_packs") / voice_profile_id)
    if destination.exists():
        manifest_path = destination / "manifest.json"
        if manifest_path.exists():
            installed = load_voice_pack(runtime.sandbox, voice_profile_id, runtime.profile_id)
            if installed is None or (
                installed.reference_wav_sha256 != source_pack.reference_wav_sha256
                or installed.authorization_record_sha256 != source_pack.authorization_record_sha256
            ):
                raise BootstrapError("existing local voice pack differs from the authorized handoff")
        elif any(destination.iterdir()):
            raise BootstrapError("local voice-pack directory is non-empty but has no validated manifest")

    seed_destination = runtime.sandbox.import_path(seed_filename)
    if seed_destination.exists() and seed_destination.read_bytes() != seed_source.read_bytes():
        raise BootstrapError("existing local seed differs from the reviewed handoff")

    # Run the exact converter against an isolated temporary runtime. This catches
    # seed schema/privacy failures before local voice or continuity installation.
    with tempfile.TemporaryDirectory(prefix="portable-mind-bootstrap-preflight-") as temporary:
        validation_runtime = ConversationRuntime(runtime.profile_id, data_root=Path(temporary))
        validation_seed = validation_runtime.sandbox.import_path(seed_filename)
        shutil.copyfile(seed_source, validation_seed)
        import_hanson_review_seed(
            validation_runtime,
            filename=seed_filename,
            approve_import=True,
        )


def bootstrap_private_handoff(
    runtime: ConversationRuntime,
    *,
    handoff_root: str | Path,
    approve_private_bootstrap: bool,
) -> BootstrapResult:
    if not approve_private_bootstrap:
        raise BootstrapError("explicit --approve-private-bootstrap is required")
    if runtime.profile_id not in {"kira", "synthetic_robert"}:
        raise BootstrapError("the named private handoff supports only Kira and Synthetic Robert")
    root = Path(handoff_root).expanduser().resolve()
    if not root.is_dir():
        raise BootstrapError("handoff root does not exist")
    seed_filename = (
        "kira_reviewed_continuity_seed.json"
        if runtime.profile_id == "kira"
        else "synthetic_robert_reviewed_continuity_seed.json"
    )
    seed_source = root / "memory_exports" / seed_filename
    if not seed_source.is_file():
        raise BootstrapError(f"reviewed continuity seed is missing: {seed_filename}")
    _prevalidate_private_handoff(runtime, root, seed_source, seed_filename)
    seed_destination = runtime.sandbox.import_path(seed_filename)
    if seed_destination.exists():
        if seed_destination.read_bytes() != seed_source.read_bytes():
            raise BootstrapError("existing local seed differs from the reviewed handoff; refusing overwrite")
    else:
        shutil.copyfile(seed_source, seed_destination)
    installed, reference_sha, authorization_sha = install_authorized_voice_pack(runtime, root)
    seed_items = import_hanson_review_seed(
        runtime,
        filename=seed_filename,
        approve_import=True,
    )
    return BootstrapResult(
        profile_id=runtime.profile_id,
        seed_filename=seed_filename,
        seed_items_imported=seed_items,
        voice_profile_id="kira" if runtime.profile_id == "kira" else "robert",
        voice_installed_now=installed,
        reference_wav_sha256=reference_sha,
        authorization_record_sha256=authorization_sha,
    )
