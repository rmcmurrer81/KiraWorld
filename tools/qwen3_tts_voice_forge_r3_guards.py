"""Append-only R3 guards for the inert TemporaryAI Qwen3-TTS forge.

This module contains only deterministic file/archive/audio checks and small
proxies.  It never imports Torch, Qwen3-TTS, an evaluator, or a model.  R3
exists to close four independently reproduced R2 evidence gaps while leaving
every R2 file byte-for-byte intact.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import math
import os
import re
import struct
import wave
import zipfile
from email.parser import BytesParser
from email.policy import default as email_policy
from pathlib import Path
from typing import Any, Callable


HASH = re.compile(r"[0-9a-f]{64}")
ALLOWED_INSTALLER_REASONS = {
    "INSTALLER_METADATA",
    "DIRECT_URL_METADATA",
    "REQUESTED_METADATA",
    "INSTALLER_GENERATED_BYTECODE",
}


class R3GuardError(RuntimeError):
    """An R3 evidence check failed closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def inside(root: Path, value: str | Path, label: str) -> Path:
    root = root.resolve()
    candidate = Path(str(value))
    if candidate.is_absolute():
        result = candidate.resolve()
    else:
        result = (root / candidate).resolve()
    try:
        result.relative_to(root)
    except ValueError as exc:
        raise R3GuardError(f"{label} escaped its exact root") from exc
    return result


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise R3GuardError(f"cannot read exact JSON: {path}") from exc
    if not isinstance(value, dict):
        raise R3GuardError(f"exact JSON is not an object: {path}")
    return value


def require_hash(value: Any, label: str) -> str:
    text = str(value or "")
    if not HASH.fullmatch(text):
        raise R3GuardError(f"{label} is not an exact SHA-256")
    return text


def verify_file(path: Path, expected_hash: Any, label: str) -> None:
    expected = require_hash(expected_hash, label)
    if not path.is_file() or path.is_symlink():
        raise R3GuardError(f"{label} is missing, not regular, or a symlink")
    if sha256_file(path) != expected:
        raise R3GuardError(f"{label} hash mismatch")


def _decode_record_hash(value: str, label: str) -> str:
    if not value.startswith("sha256="):
        raise R3GuardError(f"{label} is not SHA-256")
    encoded = value.split("=", 1)[1]
    try:
        return base64.urlsafe_b64decode(encoded + "=" * ((4 - len(encoded) % 4) % 4)).hex()
    except (ValueError, TypeError) as exc:
        raise R3GuardError(f"{label} is malformed") from exc


def _read_pcm16(path: Path) -> tuple[list[float], int, int, float]:
    try:
        with wave.open(str(path), "rb") as reader:
            channels = reader.getnchannels()
            width = reader.getsampwidth()
            rate = reader.getframerate()
            frames = reader.getnframes()
            compression = reader.getcomptype()
            payload = reader.readframes(frames)
    except (OSError, EOFError, wave.Error) as exc:
        raise R3GuardError(f"unreadable WAV: {path}") from exc
    if channels != 1 or width != 2 or compression != "NONE" or rate <= 0 or frames <= 0:
        raise R3GuardError("accepted WAV must be nonempty uncompressed mono PCM16")
    if len(payload) != frames * 2:
        raise R3GuardError("accepted WAV payload length is inconsistent")
    integers = struct.unpack(f"<{frames}h", payload)
    samples = [value / 32768.0 for value in integers]
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    if not math.isfinite(rms) or rms <= 1e-5:
        raise R3GuardError("accepted WAV is silent or non-finite")
    return samples, rate, frames, rms


def seal_pcm16_wav(path: Path, attempt_dir: Path) -> dict[str, Any]:
    exact = inside(attempt_dir, path, "final WAV")
    if not exact.is_file() or exact.is_symlink():
        raise R3GuardError("final WAV is missing, not regular, or a symlink")
    _samples, rate, frames, rms = _read_pcm16(exact)
    return {
        "kind": "READABLE_NON_SILENT_MONO_PCM16_WAV",
        "path": relative(exact, attempt_dir),
        "bytes": exact.stat().st_size,
        "sha256": sha256_file(exact),
        "sample_rate_hz": rate,
        "frames": frames,
        "duration_seconds": frames / rate,
        "rms": rms,
    }


def seal_prompt_file(path: Path, attempt_dir: Path, semantic_sha256: str) -> dict[str, Any]:
    exact = inside(attempt_dir, path, "persisted prompt")
    semantic = require_hash(semantic_sha256, "prompt semantic hash")
    if exact != (attempt_dir / "runtime_clone_prompt.pt").resolve():
        raise R3GuardError("persisted prompt path is not the exact runtime artifact")
    if not exact.is_file() or exact.is_symlink() or exact.stat().st_size <= 0:
        raise R3GuardError("persisted prompt is missing, empty, non-regular, or a symlink")
    return {
        "kind": "PERSISTED_RUNTIME_CLONE_PROMPT",
        "path": relative(exact, attempt_dir),
        "bytes": exact.stat().st_size,
        "sha256": sha256_file(exact),
        "semantic_sha256": semantic,
    }


def verify_artifact_seal(attempt_dir: Path, seal: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(seal, dict):
        raise R3GuardError("artifact seal is not an object")
    path = inside(attempt_dir, str(seal.get("path") or ""), "sealed artifact")
    if path.stat().st_size != seal.get("bytes"):
        raise R3GuardError("sealed artifact byte count changed")
    verify_file(path, seal.get("sha256"), "sealed artifact")
    if seal.get("kind") == "READABLE_NON_SILENT_MONO_PCM16_WAV":
        current = seal_pcm16_wav(path, attempt_dir)
        for key in ("path", "bytes", "sha256", "sample_rate_hz", "frames"):
            if current.get(key) != seal.get(key):
                raise R3GuardError(f"sealed WAV {key} changed")
    elif seal.get("kind") == "PERSISTED_RUNTIME_CLONE_PROMPT":
        require_hash(seal.get("semantic_sha256"), "sealed prompt semantic hash")
    else:
        raise R3GuardError("unknown artifact seal kind")
    return seal


def verify_final_artifact_set(attempt_dir: Path, seals: dict[str, Any]) -> None:
    if set(seals) != {"reference_wav", "clone_test_wav", "runtime_clone_prompt"}:
        raise R3GuardError("final artifact seal set is incomplete")
    for value in seals.values():
        verify_artifact_seal(attempt_dir, value)


def _semantic_feed(digest: Any, value: Any) -> None:
    if value is None:
        digest.update(b"N;")
    elif isinstance(value, bool):
        digest.update(b"B1;" if value else b"B0;")
    elif isinstance(value, int):
        digest.update(f"I{value};".encode("ascii"))
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise R3GuardError("prompt contains a non-finite float")
        digest.update(b"F" + struct.pack("!d", value) + b";")
    elif isinstance(value, str):
        payload = value.encode("utf-8")
        digest.update(f"S{len(payload)}:".encode("ascii") + payload + b";")
    elif isinstance(value, bytes):
        digest.update(f"Y{len(value)}:".encode("ascii") + value + b";")
    elif isinstance(value, dict):
        digest.update(f"D{len(value)}[".encode("ascii"))
        keys = sorted(value, key=lambda item: str(item))
        for key in keys:
            if not isinstance(key, (str, int)):
                raise R3GuardError("prompt dictionary key type is unsupported")
            _semantic_feed(digest, key)
            _semantic_feed(digest, value[key])
        digest.update(b"]")
    elif isinstance(value, (list, tuple)):
        digest.update(("L" if isinstance(value, list) else "T").encode("ascii"))
        digest.update(f"{len(value)}[".encode("ascii"))
        for item in value:
            _semantic_feed(digest, item)
        digest.update(b"]")
    elif all(hasattr(value, name) for name in ("detach", "cpu", "contiguous")):
        tensor = value.detach().cpu().contiguous()
        shape = tuple(int(item) for item in getattr(tensor, "shape", ()))
        digest.update(f"X{getattr(tensor, 'dtype', '')}:{shape}:".encode("utf-8"))
        numpy_value = tensor.numpy()
        payload = numpy_value.tobytes(order="C")
        digest.update(f"{len(payload)}:".encode("ascii") + payload + b";")
    else:
        raise R3GuardError(f"unsupported prompt semantic type: {type(value).__name__}")


def prompt_semantic_sha256(prompt: Any) -> str:
    digest = hashlib.sha256()
    _semantic_feed(digest, prompt)
    return digest.hexdigest()


class PersistedPromptRuntime:
    """Force clone generation to use the exact flushed-and-reloaded prompt."""

    def __init__(self, base: Any, attempt_dir: Path) -> None:
        self._base = base
        self._attempt_dir = attempt_dir.resolve()
        self._serialized_sha256: str | None = None
        self._serialized_bytes: int | None = None
        self._original_semantic_sha256: str | None = None
        self._evidence: dict[str, Any] | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def create_prompt(self, *, reference: tuple[Any, int], reference_text: str) -> Any:
        del reference
        reference_path = self._attempt_dir / "original_design_reference.wav"
        _samples, verified_rate, _frames, _rms = _read_pcm16(reference_path)
        approved_loader = getattr(self._base, "load_reference_prompt_audio", None)
        if callable(approved_loader):
            reloaded, rate = approved_loader(reference_path)
            if int(rate) != verified_rate:
                raise R3GuardError("approved reference reload returned the wrong sample rate")
        else:
            reloaded, rate = _samples, verified_rate
        reference_hash_before = sha256_file(reference_path)
        prompt = self._base.create_prompt(
            reference=(reloaded, rate), reference_text=reference_text
        )
        if sha256_file(reference_path) != reference_hash_before:
            raise R3GuardError("saved reference WAV changed while creating the prompt")
        self._original_semantic_sha256 = prompt_semantic_sha256(prompt)
        self._reference_evidence = {
            "exact_saved_reference_reloaded": True,
            "reference_wav_sha256": reference_hash_before,
            "reference_sample_rate_hz": rate,
        }
        return prompt

    def serialize_prompt(self, prompt: Any) -> bytes:
        semantic = prompt_semantic_sha256(prompt)
        if semantic != self._original_semantic_sha256:
            raise R3GuardError("prompt changed before persistence")
        payload = self._base.serialize_prompt(prompt)
        if not isinstance(payload, bytes) or not payload:
            raise R3GuardError("runtime did not serialize a nonempty prompt")
        self._serialized_sha256 = sha256_bytes(payload)
        self._serialized_bytes = len(payload)
        return payload

    def _deserialize(self, payload: bytes) -> Any:
        loader = getattr(self._base, "deserialize_prompt", None)
        if not callable(loader):
            raise R3GuardError("approved runtime has no prompt reload operation")
        try:
            return loader(payload)
        except BaseException as exc:
            raise R3GuardError("persisted prompt could not be reloaded") from exc

    def generate_clone(self, *, text: str, language: str, prompt: Any) -> tuple[Any, int]:
        provided_semantic = prompt_semantic_sha256(prompt)
        if provided_semantic != self._original_semantic_sha256:
            raise R3GuardError("caller prompt changed before persisted reload")
        prompt_path = self._attempt_dir / "runtime_clone_prompt.pt"
        if not prompt_path.is_file() or prompt_path.is_symlink():
            raise R3GuardError("persisted runtime prompt is unavailable")
        payload = prompt_path.read_bytes()
        if (
            len(payload) != self._serialized_bytes
            or sha256_bytes(payload) != self._serialized_sha256
        ):
            raise R3GuardError("persisted runtime prompt bytes changed before reload")
        reloaded = self._deserialize(payload)
        reloaded_semantic = prompt_semantic_sha256(reloaded)
        if reloaded_semantic != self._original_semantic_sha256:
            raise R3GuardError("reloaded prompt semantics differ from the created prompt")
        result = self._base.generate_clone(text=text, language=language, prompt=reloaded)
        if sha256_file(prompt_path) != self._serialized_sha256:
            raise R3GuardError("persisted runtime prompt changed during clone generation")
        self._evidence = {
            **self._reference_evidence,
            "path": "runtime_clone_prompt.pt",
            "bytes": self._serialized_bytes,
            "sha256": self._serialized_sha256,
            "created_prompt_semantic_sha256": self._original_semantic_sha256,
            "reloaded_prompt_semantic_sha256": reloaded_semantic,
            "persisted_prompt_reload_used_for_generation": True,
            "in_memory_caller_prompt_used_for_generation": False,
        }
        return result

    def prompt_evidence(self) -> dict[str, Any]:
        if self._evidence is None:
            raise R3GuardError("persisted prompt was not proven as generation input")
        seal = seal_prompt_file(
            self._attempt_dir / "runtime_clone_prompt.pt",
            self._attempt_dir,
            self._evidence["reloaded_prompt_semantic_sha256"],
        )
        if seal["sha256"] != self._evidence["sha256"] or seal["bytes"] != self._evidence["bytes"]:
            raise R3GuardError("persisted prompt changed after clone generation")
        return {**self._evidence, "artifact_seal": seal}


class EvaluatorMutationGuard:
    """Recheck both final WAVs before and after every evaluator operation."""

    def __init__(self, base: Any, attempt_dir: Path) -> None:
        self._base = base
        self._attempt_dir = attempt_dir.resolve()
        self._seals = {
            "reference_wav": seal_pcm16_wav(
                self._attempt_dir / "original_design_reference.wav", self._attempt_dir
            ),
            "clone_test_wav": seal_pcm16_wav(
                self._attempt_dir / "runtime_clone_test.wav", self._attempt_dir
            ),
        }
        self._checks: list[str] = []

    def _check(self, stage: str) -> None:
        for seal in self._seals.values():
            verify_artifact_seal(self._attempt_dir, seal)
        self._checks.append(stage)

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._base, name)
        if not callable(attribute) or name.startswith("_"):
            return attribute

        def guarded(*args: Any, **kwargs: Any) -> Any:
            self._check(f"before:{name}")
            result = attribute(*args, **kwargs)
            self._check(f"after:{name}")
            return result

        return guarded

    def final_evidence(self) -> dict[str, Any]:
        self._check("before_worker_acceptance")
        return {
            "artifact_seals": dict(self._seals),
            "checkpoints": list(self._checks),
            "checked_before_and_after_every_evaluator_operation": True,
        }


def enumerate_dist_info(site_packages: Path) -> dict[str, dict[str, Any]]:
    """Enumerate every installed metadata root from the exact filesystem."""

    site_packages = site_packages.resolve()
    if not site_packages.is_dir():
        raise R3GuardError("exact site-packages directory is missing")
    egg_info = sorted(
        path for path in site_packages.rglob("*")
        if path.name.lower().endswith(".egg-info")
    )
    if egg_info:
        raise R3GuardError("legacy egg-info cannot satisfy exact RECORD provenance")
    roots = sorted(
        path for path in site_packages.rglob("*")
        if path.is_dir() and path.name.lower().endswith(".dist-info")
    )
    discovered: dict[str, dict[str, Any]] = {}
    for root in roots:
        if root.parent.resolve() != site_packages:
            raise R3GuardError("nested dist-info metadata root is not an installed distribution root")
        metadata_path = root / "METADATA"
        record_path = root / "RECORD"
        if not metadata_path.is_file() or not record_path.is_file():
            raise R3GuardError("installed dist-info lacks METADATA or RECORD")
        metadata = BytesParser(policy=email_policy).parsebytes(metadata_path.read_bytes())
        name = str(metadata.get("Name") or "")
        version = str(metadata.get("Version") or "")
        canonical = canonical_distribution_name(name)
        if not canonical or not version or canonical in discovered:
            raise R3GuardError("installed dist-info identity is empty or duplicated")
        discovered[canonical] = {
            "name": name,
            "canonical_name": canonical,
            "version": version,
            "metadata_root": relative(root, site_packages),
            "metadata_path": relative(metadata_path, site_packages),
            "record_path": relative(record_path, site_packages),
            "record_sha256": sha256_file(record_path),
        }
    if not discovered:
        raise R3GuardError("no installed dist-info distributions were enumerated")
    return discovered


def verify_authoritative_distribution_inventory(
    *,
    project_root: Path,
    isolated_venv_rel: Path,
    spec: dict[str, Any],
    distribution_evidence: dict[str, dict[str, Any]],
    base_verifier: Callable[..., dict[str, Any]],
    base_verifier_style: str,
) -> dict[str, Any]:
    site_packages = (project_root / isolated_venv_rel / "Lib/site-packages").resolve()
    discovered = enumerate_dist_info(site_packages)
    inventory_spec = spec.get("site_packages_inventory") or {}
    manifest_path = inside(project_root, str(inventory_spec.get("manifest_path") or ""), "inventory manifest")
    verify_file(manifest_path, inventory_spec.get("manifest_sha256"), "inventory manifest")
    manifest = read_json(manifest_path)
    distribution_rows = manifest.get("distributions")
    file_rows = manifest.get("files")
    if not isinstance(distribution_rows, list) or not isinstance(file_rows, list):
        raise R3GuardError("inventory distributions/files are not exact lists")
    declared: dict[str, dict[str, Any]] = {}
    for row in distribution_rows:
        if not isinstance(row, dict):
            raise R3GuardError("declared distribution row is invalid")
        canonical = canonical_distribution_name(str(row.get("name") or ""))
        if not canonical or canonical in declared:
            raise R3GuardError("declared distribution identity is empty or duplicated")
        declared[canonical] = row
    evidence = {
        canonical_distribution_name(name): row
        for name, row in distribution_evidence.items()
    }
    if set(discovered) != set(declared) or set(discovered) != set(evidence):
        raise R3GuardError("filesystem dist-info enumeration does not equal every declared distribution")
    indexed_files = {
        str(row.get("path") or ""): row
        for row in file_rows if isinstance(row, dict)
    }
    if len(indexed_files) != len(file_rows) or "" in indexed_files:
        raise R3GuardError("inventory file rows are invalid or duplicated")
    for canonical, actual in discovered.items():
        declared_row = declared[canonical]
        evidence_row = evidence[canonical]
        expected_project_record = relative(site_packages / actual["record_path"], project_root)
        if (
            declared_row.get("version") != actual["version"]
            or evidence_row.get("version") != actual["version"]
            or declared_row.get("record_path") != expected_project_record
            or evidence_row.get("record_path") != expected_project_record
            or declared_row.get("record_sha256") != actual["record_sha256"]
            or evidence_row.get("record_sha256") != actual["record_sha256"]
        ):
            raise R3GuardError(f"{canonical} dist-info identity/RECORD reconciliation failed")
        root_prefix = actual["metadata_root"] + "/"
        metadata_rows = [
            row for path, row in indexed_files.items()
            if path == actual["metadata_root"] or path.startswith(root_prefix)
        ]
        if not metadata_rows:
            raise R3GuardError(f"{canonical} dist-info is absent from exact file inventory")
        for row in metadata_rows:
            owners = {
                canonical_distribution_name(str(owner))
                for owner in row.get("owner_distributions", [])
            }
            if canonical not in owners or row.get("loose_unowned_file") is not False:
                raise R3GuardError("dist-info metadata was relabeled as loose/unowned")
    if base_verifier_style == "worker":
        result = base_verifier(
            project_root=project_root,
            spec=spec,
            distribution_evidence=distribution_evidence,
        )
    elif base_verifier_style == "runner":
        result = base_verifier(spec, distribution_evidence)
    else:
        raise R3GuardError("unknown base inventory verifier style")
    return {
        **result,
        "authoritative_filesystem_dist_info_enumeration": True,
        "enumerated_distribution_count": len(discovered),
        "enumerated_distributions": sorted(discovered),
        "no_dist_info_relabeled_loose": True,
        "claimed_transitive_distribution_completeness_proven": True,
    }


def attest_wheel_archive(
    *, project_root: Path, wheel_root_rel: Path, package: str, row: dict[str, Any]
) -> dict[str, Any]:
    wheel_root = (project_root / wheel_root_rel).resolve()
    wheel_path = inside(project_root, str(row.get("wheel_evidence_path") or ""), f"{package} wheel")
    try:
        wheel_path.relative_to(wheel_root)
    except ValueError as exc:
        raise R3GuardError(f"{package} wheel escaped its fixed evidence root") from exc
    if wheel_path.name != row.get("wheel_filename") or wheel_path.suffix.lower() != ".whl":
        raise R3GuardError(f"{package} wheel filename/path mismatch")
    verify_file(wheel_path, row.get("wheel_sha256"), f"{package} exact wheel")
    parts = wheel_path.stem.split("-")
    if len(parts) < 5:
        raise R3GuardError(f"{package} wheel filename is malformed")
    distribution, version = parts[0], parts[1]
    py_tag, abi_tag, platform_tag = parts[-3:]
    if (
        canonical_distribution_name(distribution) != canonical_distribution_name(package)
        or version != row.get("version")
        or py_tag != "cp311"
        or abi_tag != "cp311"
        or platform_tag != "win_amd64"
    ):
        raise R3GuardError(f"{package} wheel identity or cp311 Windows tag mismatch")
    try:
        with zipfile.ZipFile(wheel_path, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or any(name.startswith("/") or ".." in Path(name).parts for name in names):
                raise R3GuardError(f"{package} wheel member paths are unsafe/duplicated")
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            wheel_names = [name for name in names if name.endswith(".dist-info/WHEEL")]
            record_names = [name for name in names if name.endswith(".dist-info/RECORD")]
            if len(metadata_names) != 1 or len(wheel_names) != 1 or len(record_names) != 1:
                raise R3GuardError(f"{package} wheel lacks unique METADATA/WHEEL/RECORD")
            metadata = BytesParser(policy=email_policy).parsebytes(archive.read(metadata_names[0]))
            if (
                canonical_distribution_name(str(metadata.get("Name") or ""))
                != canonical_distribution_name(package)
                or str(metadata.get("Version") or "") != row.get("version")
            ):
                raise R3GuardError(f"{package} wheel METADATA mismatch")
            wheel_text = archive.read(wheel_names[0]).decode("utf-8")
            if "Tag: cp311-cp311-win_amd64" not in wheel_text or "root-is-purelib: false" not in wheel_text.lower():
                raise R3GuardError(f"{package} wheel WHEEL tags/purity mismatch")
            record_rows = list(csv.reader(io.StringIO(archive.read(record_names[0]).decode("utf-8"))))
            members: dict[str, dict[str, Any]] = {}
            for record_row in record_rows:
                if len(record_row) != 3:
                    raise R3GuardError(f"{package} wheel RECORD row is malformed")
                name, encoded_hash, declared_size = record_row
                if not name or name in members or name not in names:
                    raise R3GuardError(f"{package} wheel RECORD inventory is invalid")
                if name == record_names[0]:
                    if encoded_hash or declared_size:
                        raise R3GuardError(f"{package} wheel RECORD self-row must be unhashed")
                    members[name] = {"bytes": len(archive.read(name)), "sha256": sha256_bytes(archive.read(name)), "record_self": True}
                    continue
                if not declared_size.isdigit():
                    raise R3GuardError(f"{package} wheel member size is absent")
                expected = _decode_record_hash(encoded_hash, f"{package} wheel RECORD hash")
                payload = archive.read(name)
                if len(payload) != int(declared_size) or sha256_bytes(payload) != expected:
                    raise R3GuardError(f"{package} wheel member differs from RECORD: {name}")
                members[name] = {"bytes": len(payload), "sha256": expected, "record_self": False}
            if set(names) != set(members):
                raise R3GuardError(f"{package} wheel RECORD is not a complete archive inventory")
    except (OSError, zipfile.BadZipFile, UnicodeError, csv.Error, ValueError) as exc:
        if isinstance(exc, R3GuardError):
            raise
        raise R3GuardError(f"{package} wheel is invalid: {exc}") from exc
    root = package.replace("-", "_")
    required_init = f"{root}/__init__.py"
    compiled = [name for name in members if name.startswith(root + "/") and name.lower().endswith(".pyd")]
    if required_init not in members or not compiled:
        raise R3GuardError(f"{package} wheel lacks real importable package/compiled payload")
    return {
        "package": package,
        "version": row["version"],
        "path": relative(wheel_path, project_root),
        "filename": wheel_path.name,
        "sha256": row["wheel_sha256"],
        "tag": "cp311-cp311-win_amd64",
        "record_path": record_names[0],
        "members": members,
        "archive_members_verified": len(members) - 1,
        "metadata_name": package,
        "metadata_version": row["version"],
        "real_package_root": root,
        "required_init_member": required_init,
        "compiled_payload_members": sorted(compiled),
        "real_importable_payload_proven": True,
    }


def bind_wheel_to_installed_distribution(
    *,
    project_root: Path,
    isolated_venv_rel: Path,
    package: str,
    row: dict[str, Any],
    installed_evidence: dict[str, Any],
    wheel_evidence: dict[str, Any],
) -> dict[str, Any]:
    site_packages = (project_root / isolated_venv_rel / "Lib/site-packages").resolve()
    source_rows = installed_evidence.get("installed_files")
    if source_rows is None:
        source_rows = installed_evidence.get("files")
    if not isinstance(source_rows, list) or not source_rows:
        raise R3GuardError(f"{package} installed RECORD evidence has no files")
    installed: dict[str, dict[str, Any]] = {}
    for source in source_rows:
        path = inside(project_root, str(source.get("path") or ""), f"{package} installed RECORD member")
        try:
            rel = relative(path, site_packages)
        except ValueError as exc:
            raise R3GuardError(f"{package} installed RECORD member escaped site-packages") from exc
        if rel in installed:
            raise R3GuardError(f"{package} installed RECORD member is duplicated")
        verify_file(path, source.get("sha256"), f"{package} installed RECORD member")
        if path.stat().st_size != source.get("bytes"):
            raise R3GuardError(f"{package} installed RECORD member size changed")
        installed[rel] = source
    wheel_members = wheel_evidence["members"]
    wheel_record = wheel_evidence["record_path"]
    matched = 0
    for rel, member in wheel_members.items():
        if rel == wheel_record:
            continue
        source = installed.get(rel)
        if source is None or source.get("bytes") != member["bytes"] or source.get("sha256") != member["sha256"]:
            raise R3GuardError(f"{package} installed file is not from the exact wheel member: {rel}")
        matched += 1
    if matched <= 0:
        raise R3GuardError(f"{package} exact wheel bound no installed payload")
    extras = set(installed) - set(wheel_members)
    declared_extras = row.get("installer_generated_files")
    if not isinstance(declared_extras, list):
        raise R3GuardError(f"{package} installer-generated differences are not explicitly declared")
    indexed_extras: dict[str, dict[str, Any]] = {}
    for extra in declared_extras:
        if not isinstance(extra, dict):
            raise R3GuardError(f"{package} installer-generated row is invalid")
        rel = str(extra.get("path") or "")
        if rel in indexed_extras or extra.get("reason") not in ALLOWED_INSTALLER_REASONS:
            raise R3GuardError(f"{package} installer-generated row is duplicated/unjustified")
        require_hash(extra.get("sha256"), f"{package} installer-generated hash")
        indexed_extras[rel] = extra
    if extras != set(indexed_extras):
        raise R3GuardError(f"{package} installed/wheel differences are not exactly declared")
    for rel, extra in indexed_extras.items():
        source = installed[rel]
        if source.get("bytes") != extra.get("bytes") or source.get("sha256") != extra.get("sha256"):
            raise R3GuardError(f"{package} installer-generated difference evidence mismatch")
    installed_record_rel = relative(
        inside(project_root, installed_evidence["record_path"], f"{package} installed RECORD"),
        site_packages,
    )
    if installed_record_rel != wheel_record or installed_record_rel not in installed:
        raise R3GuardError(f"{package} installed RECORD is not the exact wheel RECORD path")
    root = wheel_evidence["real_package_root"] + "/"
    installed_payload = [name for name in installed if name.startswith(root)]
    if not installed_payload:
        raise R3GuardError(f"{package} installed RECORD contains no real package payload")
    return {
        "exact_wheel_sha256": wheel_evidence["sha256"],
        "installed_record_sha256": installed_evidence["record_sha256"],
        "wheel_members_bound_to_installed_files": matched,
        "installer_generated_differences": sorted(extras),
        "installed_real_package_payload_count": len(installed_payload),
        "exact_wheel_to_installed_record_and_files_bound": True,
    }


def validate_parent_artifacts(
    *, attempt_dir: Path, worker_manifest: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    if worker_manifest.get("schema") != "qwen3_tts_original_voice_forge_worker_manifest_v3":
        raise R3GuardError("parent received the wrong worker manifest schema")
    if worker_manifest.get("status") != "ENGINEERING_ACCEPTANCE_PASSED_OWNER_HEARING_PENDING_INDEPENDENT_AUDIT":
        raise R3GuardError("worker did not pass every R3 engineering gate")
    seals = worker_manifest.get("artifact_seals")
    if not isinstance(seals, dict):
        raise R3GuardError("worker manifest has no final artifact seals")
    verify_final_artifact_set(attempt_dir, seals)
    if profile.get("artifact_seals") != seals:
        raise R3GuardError("profile/worker final artifact seals differ")
    prompt = worker_manifest.get("persisted_prompt_evidence") or {}
    if (
        prompt.get("persisted_prompt_reload_used_for_generation") is not True
        or prompt.get("in_memory_caller_prompt_used_for_generation") is not False
        or prompt.get("sha256") != seals["runtime_clone_prompt"]["sha256"]
        or prompt.get("reloaded_prompt_semantic_sha256")
        != seals["runtime_clone_prompt"]["semantic_sha256"]
    ):
        raise R3GuardError("persisted prompt use/hash/semantics are not parent-verifiable")
    return {
        "parent_reopened_and_revalidated_every_final_artifact": True,
        "artifact_seals": seals,
    }
