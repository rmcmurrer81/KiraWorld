#!/usr/bin/env python3
"""Fail-closed, standard-library validation for the Hanson private handoff.

The validator is intentionally scoped to the handoff directory supplied on the
command line.  It never reads or modifies the legacy recovery snapshot outside
that directory.  It validates content and bindings; it does not make a legal,
clinical, consciousness, personhood, or robot-safety certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import unquote


MAX_FILE_BYTES = 50 * 1024 * 1024
KIRA_APPROVED_REFERENCE_SHA256 = (
    "2039a2abd600a63c294d69c2b2e4d450"
    "c64c850dc6d1c9a4fbfa1700ba92069c"
)
KIRA_APPROVED_REFERENCE_BYTES = 9_856_844
ROBERT_APPROVED_REFERENCE_SHA256 = (
    "761458a0fe9c5da1c2671faa738c1e329"
    "336630cd47138a4e738f7de2030542b"
)
ROBERT_APPROVED_REFERENCE_BYTES = 1_755_404

EMAIL_RE = re.compile(
    r"(?i)(?<![A-Z0-9._%+\-])[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}(?![A-Z0-9._%+\-])"
)
WINDOWS_USER_PATH_RE = re.compile(
    r"(?i)(?<![A-Z0-9])(?:[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"'<>]+(?:[\\/][^\s\"'<>]*)?)"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
AWS_KEY_RE = re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])")
GITHUB_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{20,}")
OPENAI_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{20,}")
JWT_RE = re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")

MARKDOWN_INLINE_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
MARKDOWN_REFERENCE_LINK_RE = re.compile(r"(?m)^\s*\[[^\]]+\]:\s*(\S+)")

TEXT_SUFFIXES = {
    ".bat",
    ".cfg",
    ".cmd",
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".rst",
    ".sh",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}

SENSITIVE_KEYS = {
    "access_token",
    "address",
    "api_key",
    "auth_token",
    "client_secret",
    "contact",
    "contact_details",
    "contact_info",
    "credential",
    "credentials",
    "email",
    "email_address",
    "mailing_address",
    "mobile",
    "password",
    "passwd",
    "phone",
    "postal_address",
    "private_key",
    "refresh_token",
    "secret_key",
    "shipping",
    "shipping_address",
    "street_address",
    "telephone",
}

EMBODIMENT_LIMIT_KEYS = {
    "active_embodiment_session_limit",
    "max_active_body_sessions",
    "max_active_embodiment_sessions",
    "max_active_sessions_per_person",
    "max_active_sessions_per_variant",
    "one_active_embodiment_session",
}


class DuplicateKeyError(ValueError):
    """Raised when an object repeats a JSON member name."""


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    message: str


@dataclass
class ValidationReport:
    root: str
    passed: bool = True
    checks_run: int = 0
    files_scanned: int = 0
    json_documents: int = 0
    markdown_links: int = 0
    issues: list[Issue] = field(default_factory=list)

    def check(self, condition: bool, code: str, path: str, message: str) -> bool:
        self.checks_run += 1
        if not condition:
            self.issues.append(Issue(code=code, path=path, message=message))
            self.passed = False
        return condition


@dataclass(frozen=True)
class VoiceSpec:
    label: str
    directory: str
    profile_name: str
    expected_person_id: str
    binding_key: str


VOICE_SPECS = (
    VoiceSpec(
        label="Kira",
        directory="voice_packs/kira",
        profile_name="current_voice_profile.json",
        expected_person_id="kira",
        binding_key="exact_asset_binding",
    ),
    VoiceSpec(
        label="Synthetic Robert",
        directory="voice_packs/robert",
        profile_name="voice_profile.json",
        expected_person_id="synthetic_robert",
        binding_key="asset_binding",
    ),
)


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate object key: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def load_json_strict(path: Path) -> Any:
    """Load UTF-8 JSON while rejecting BOMs, duplicates, and NaN/Infinity."""

    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden")
    text = raw.decode("utf-8", errors="strict")
    return json.loads(
        text,
        object_pairs_hook=_duplicate_rejecting_object,
        parse_constant=_reject_nonfinite,
    )


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _walk_files(root: Path) -> Iterator[Path]:
    for directory, names, filenames in os.walk(root, followlinks=False):
        names.sort()
        filenames.sort()
        base = Path(directory)
        symlink_directories = [name for name in names if (base / name).is_symlink()]
        for name in symlink_directories:
            yield base / name
        names[:] = [name for name in names if name not in symlink_directories]
        for filename in filenames:
            yield base / filename


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _repository_root(handoff_root: Path) -> Path:
    for candidate in (handoff_root, *handoff_root.parents):
        if (candidate / ".git").exists():
            return candidate.resolve()
    # Preserve the documented repo/handoff/<handoff-name> layout in test copies.
    if handoff_root.parent.name.lower() == "handoff":
        return handoff_root.parent.parent.resolve()
    return handoff_root.resolve()


def _iter_nodes(value: Any, path: str = "$") -> Iterator[tuple[str, str | None, Any]]:
    """Yield (JSONPath-like path, member key, value) recursively."""

    yield path, None, value
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield child_path, key, child
            yield from _iter_nodes(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_nodes(child, f"{path}[{index}]")


def _all_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _all_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_strings(child)


def _normalized_key(key: str) -> str:
    return key.strip().lower().replace("-", "_").replace(" ", "_")


def _negative_or_empty(value: Any) -> bool:
    if value is None or value is False:
        return True
    if value == "" or value == [] or value == {}:
        return True
    if isinstance(value, str):
        normalized = " ".join(value.lower().replace("_", " ").split())
        return normalized in {
            "absent",
            "excluded",
            "false",
            "none",
            "not included",
            "redacted",
        }
    return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_wav(path: Path, root: Path, report: ValidationReport) -> None:
    rel = _relative(path, root)
    try:
        with wave.open(str(path), "rb") as audio:
            valid = (
                audio.getnchannels() > 0
                and audio.getsampwidth() > 0
                and audio.getframerate() > 0
                and audio.getnframes() > 0
                and audio.getcomptype() == "NONE"
            )
    except (OSError, EOFError, wave.Error) as exc:
        report.check(False, "VOICE_WAV_INVALID", rel, f"not a readable PCM WAV: {exc}")
        return
    report.check(valid, "VOICE_WAV_INVALID", rel, "WAV must contain non-empty uncompressed PCM audio")


def _validate_file_inventory(root: Path, report: ValidationReport) -> list[Path]:
    files = list(_walk_files(root))
    report.files_scanned = len(files)
    report.check(bool(files), "HANDOFF_EMPTY", ".", "handoff contains no files")
    for path in files:
        rel = _relative(path, root)
        report.check(not path.is_symlink(), "SYMLINK_FORBIDDEN", rel, "symlinks are not allowed")
        try:
            size = path.stat().st_size
        except OSError as exc:
            report.check(False, "FILE_STAT_FAILED", rel, str(exc))
            continue
        report.check(
            size <= MAX_FILE_BYTES,
            "FILE_TOO_LARGE",
            rel,
            f"{size} bytes exceeds the {MAX_FILE_BYTES}-byte limit",
        )
    return files


def _validate_json(
    root: Path, files: Iterable[Path], report: ValidationReport
) -> dict[Path, Any]:
    documents: dict[Path, Any] = {}
    for path in files:
        if path.suffix.lower() != ".json":
            continue
        rel = _relative(path, root)
        try:
            document = load_json_strict(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            report.check(False, "JSON_STRICT_PARSE", rel, str(exc))
            continue
        documents[path] = document
        report.json_documents += 1
        report.check(True, "JSON_STRICT_PARSE", rel, "strict JSON parsed")
    for required in (
        root / "memory_exports",
        root / "voice_packs",
        root / "mind_v21_static" / "traceability",
    ):
        report.check(
            required.is_dir(),
            "REQUIRED_JSON_SCOPE_MISSING",
            _relative(required, root),
            "required validation scope is missing",
        )
        if required.is_dir():
            candidates = list(required.rglob("*.json"))
            report.check(
                bool(candidates),
                "REQUIRED_JSON_SCOPE_EMPTY",
                _relative(required, root),
                "required validation scope contains no JSON",
            )
            for candidate in candidates:
                report.check(
                    candidate in documents,
                    "REQUIRED_JSON_UNPARSED",
                    _relative(candidate, root),
                    "required JSON did not pass strict parsing",
                )
    return documents


def _validate_no_concrete_sensitive_data(
    root: Path,
    files: Iterable[Path],
    documents: dict[Path, Any],
    report: ValidationReport,
) -> None:
    concrete_patterns = (
        ("EMAIL_ADDRESS", EMAIL_RE),
        ("WINDOWS_USER_PATH", WINDOWS_USER_PATH_RE),
        ("PRIVATE_KEY", PRIVATE_KEY_RE),
        ("AWS_ACCESS_KEY", AWS_KEY_RE),
        ("GITHUB_TOKEN", GITHUB_TOKEN_RE),
        ("OPENAI_TOKEN", OPENAI_TOKEN_RE),
        ("JWT_TOKEN", JWT_RE),
    )
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = _relative(path, root)
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError) as exc:
            report.check(False, "TEXT_DECODE_FAILED", rel, str(exc))
            continue
        for code, pattern in concrete_patterns:
            match = pattern.search(text)
            report.check(
                match is None,
                code,
                rel,
                "concrete sensitive value found" if match else "no concrete sensitive value",
            )

    # Protocol traceability contains conceptual words such as "secret" and
    # "shipping".  Sensitive-key policy is applied to operational handoff JSON,
    # not to the sealed static protocol vocabulary.
    for path, document in documents.items():
        if _inside(path, root / "mind_v21_static"):
            continue
        rel = _relative(path, root)
        for node_path, key, value in _iter_nodes(document):
            if key is None:
                continue
            normalized = key.lower().replace("-", "_").replace(" ", "_")
            sensitive = (
                normalized in SENSITIVE_KEYS
                or normalized.endswith("_password")
                or normalized.endswith("_api_key")
                or normalized.endswith("_access_token")
                or normalized.endswith("_refresh_token")
                or normalized.endswith("_credential")
                or normalized.endswith("_credentials")
                or normalized.startswith("shipping_")
                or normalized.startswith("contact_details_")
            )
            if sensitive:
                report.check(
                    _negative_or_empty(value),
                    "SENSITIVE_JSON_VALUE",
                    rel,
                    f"{node_path} contains contact/shipping/credential data",
                )


def _validate_memory_exports(
    root: Path, documents: dict[Path, Any], report: ValidationReport
) -> None:
    specs = (
        (
            "kira_reviewed_continuity_seed.json",
            "kira",
            "kira_",
            "Kira",
        ),
        (
            "synthetic_robert_reviewed_continuity_seed.json",
            "synthetic_robert",
            "synthetic_robert_",
            "Synthetic Robert",
        ),
    )
    all_memory_ids: set[str] = set()
    for filename, person_id, id_prefix, display_name in specs:
        path = root / "memory_exports" / filename
        rel = _relative(path, root)
        document = documents.get(path)
        report.check(isinstance(document, dict), "MEMORY_EXPORT_MISSING", rel, "memory export is missing or invalid")
        if not isinstance(document, dict):
            continue
        report.check(
            document.get("person_id") == person_id,
            "MEMORY_PERSON_BINDING",
            rel,
            f"person_id must be {person_id!r}",
        )
        export_id = document.get("export_id")
        report.check(
            isinstance(export_id, str) and export_id.startswith(id_prefix),
            "MEMORY_EXPORT_ID_BINDING",
            rel,
            f"export_id must start with {id_prefix!r}",
        )
        identity = document.get("identity")
        report.check(isinstance(identity, dict), "MEMORY_IDENTITY_MISSING", rel, "identity object is required")
        if isinstance(identity, dict):
            report.check(
                identity.get("display_name") == display_name,
                "MEMORY_DISPLAY_NAME_BINDING",
                rel,
                f"identity.display_name must be {display_name!r}",
            )
        report.check(
            document.get("hidden_chain_of_thought_included") is False,
            "HIDDEN_COT_FORBIDDEN",
            rel,
            "hidden_chain_of_thought_included must be exactly false",
        )
        if "fanfic_test_material_included" in document:
            report.check(
                document.get("fanfic_test_material_included") is False,
                "FANFIC_INCLUDED",
                rel,
                "fanfic_test_material_included must be exactly false",
            )

        memories = document.get("reviewed_memories")
        report.check(isinstance(memories, list), "MEMORY_LIST_MISSING", rel, "reviewed_memories must be a list")
        if not isinstance(memories, list):
            continue
        for index, memory in enumerate(memories):
            memory_path = f"reviewed_memories[{index}]"
            report.check(isinstance(memory, dict), "MEMORY_RECORD_INVALID", rel, f"{memory_path} must be an object")
            if not isinstance(memory, dict):
                continue
            memory_id = memory.get("memory_id")
            report.check(
                isinstance(memory_id, str) and memory_id.startswith(id_prefix),
                "CROSS_PERSON_MEMORY",
                rel,
                f"{memory_path}.memory_id must start with {id_prefix!r}",
            )
            if isinstance(memory_id, str):
                report.check(
                    memory_id not in all_memory_ids,
                    "DUPLICATE_MEMORY_ID",
                    rel,
                    f"memory_id {memory_id!r} is repeated across person stores",
                )
                all_memory_ids.add(memory_id)
            record_text = "\n".join(_all_strings(memory)).lower()
            report.check(
                "fanfic" not in record_text and "fan fiction" not in record_text,
                "FANFIC_RECORD",
                rel,
                f"{memory_path} contains fanfic test material",
            )

        continuity_text = "\n".join(_all_strings(memories)).lower()
        report.check(
            "one active embodiment session" in continuity_text,
            "EMBODIMENT_SINGLE_SESSION_MISSING",
            rel,
            "reviewed continuity must retain the one-active-embodiment-session concept",
        )

    # Any machine-readable chain-of-thought inclusion switch must be false.
    for path, document in documents.items():
        if _inside(path, root / "mind_v21_static"):
            continue
        rel = _relative(path, root)
        for node_path, key, value in _iter_nodes(document):
            if key is None:
                continue
            normalized = key.lower().replace("-", "_").replace(" ", "_")
            if "chain_of_thought" in normalized:
                report.check(
                    value is False,
                    "HIDDEN_COT_FORBIDDEN",
                    rel,
                    f"{node_path} must be exactly false",
                )

            if normalized in EMBODIMENT_LIMIT_KEYS:
                if normalized == "one_active_embodiment_session":
                    valid = value is True or value == 1
                else:
                    valid = not isinstance(value, bool) and isinstance(value, int) and value == 1
                report.check(
                    valid,
                    "EMBODIMENT_SESSION_LIMIT",
                    rel,
                    f"{node_path} must enforce exactly one active embodiment session",
                )


def _validate_person_file_bindings(
    root: Path, documents: dict[Path, Any], report: ValidationReport
) -> None:
    """Catch person_id values stored in the other person's named path."""

    for path, document in documents.items():
        if _inside(path, root / "mind_v21_static") or not isinstance(document, dict):
            continue
        rel_lower = _relative(path, root).lower()
        person_id = document.get("person_id")
        if not isinstance(person_id, str):
            continue
        if "/kira/" in f"/{rel_lower}/" or Path(rel_lower).name.startswith("kira_"):
            report.check(
                person_id == "kira",
                "PERSON_STORAGE_SEPARATION",
                _relative(path, root),
                "a Kira-named store must bind person_id 'kira'",
            )
        if "/robert/" in f"/{rel_lower}/" or Path(rel_lower).name.startswith("synthetic_robert_"):
            report.check(
                person_id == "synthetic_robert",
                "PERSON_STORAGE_SEPARATION",
                _relative(path, root),
                "a Robert-named store must bind person_id 'synthetic_robert'",
            )


def _validate_voice_packs(
    root: Path, documents: dict[Path, Any], report: ValidationReport
) -> None:
    """Validate the two exact, private, owner-authorized voice bindings."""

    expected_recipients = {"David Hanson", "Manav Tidhan", "Vytas Krisciunas"}

    def simple_local_name(value: Any) -> bool:
        return isinstance(value, str) and bool(value) and Path(value).name == value

    def validate_exact_asset(
        *,
        label: str,
        directory: Path,
        profile_path: Path,
        profile: dict[str, Any],
        authorization: dict[str, Any],
        binding_key: str,
        expected_person_id: str,
        expected_sha256: str | None = None,
        expected_bytes: int | None = None,
    ) -> Path | None:
        profile_rel = _relative(profile_path, root)
        wav_name = profile.get("reference_wav")
        report.check(
            profile.get("person_id") == expected_person_id,
            "VOICE_PERSON_BINDING",
            profile_rel,
            f"{label} person_id must be {expected_person_id!r}",
        )
        report.check(
            simple_local_name(wav_name),
            "VOICE_WAV_PATH",
            profile_rel,
            f"{label} reference_wav must be one local filename",
        )
        if not simple_local_name(wav_name):
            return None
        wav_path = directory / wav_name
        report.check(
            wav_path.is_file(),
            "VOICE_WAV_MISSING",
            _relative(wav_path, root),
            f"bound {label} WAV is missing",
        )
        if not wav_path.is_file():
            return None
        _validate_wav(wav_path, root, report)
        actual_bytes = wav_path.stat().st_size
        actual_hash = _sha256(wav_path)
        report.check(
            profile.get("reference_bytes") == actual_bytes,
            "VOICE_PROFILE_BYTE_BINDING",
            profile_rel,
            f"{label} profile bytes must equal exact WAV size {actual_bytes}",
        )
        report.check(
            profile.get("reference_sha256") == actual_hash,
            "VOICE_PROFILE_HASH_BINDING",
            profile_rel,
            f"{label} profile SHA-256 must equal exact WAV SHA-256 {actual_hash}",
        )
        if expected_sha256 is not None:
            report.check(
                actual_hash == expected_sha256,
                "VOICE_EXPECTED_HASH",
                _relative(wav_path, root),
                f"{label} WAV must equal the explicitly authorized SHA-256 {expected_sha256}",
            )
        if expected_bytes is not None:
            report.check(
                actual_bytes == expected_bytes,
                "VOICE_EXPECTED_BYTES",
                _relative(wav_path, root),
                f"{label} WAV must equal the explicitly authorized {expected_bytes} bytes",
            )
        binding = authorization.get(binding_key)
        if not isinstance(binding, dict):
            alternate_key = (
                "asset_binding" if binding_key == "exact_asset_binding" else "exact_asset_binding"
            )
            binding = authorization.get(alternate_key)
        auth_path = directory / str(profile.get("authorization", ""))
        auth_rel = _relative(auth_path, root)
        report.check(
            isinstance(binding, dict),
            "VOICE_AUTH_BINDING_MISSING",
            auth_rel,
            f"{binding_key} is required",
        )
        if isinstance(binding, dict):
            report.check(
                binding.get("path") == wav_name,
                "VOICE_AUTH_PATH_BINDING",
                auth_rel,
                "authorization path must equal profile reference_wav",
            )
            report.check(
                binding.get("bytes") == actual_bytes == profile.get("reference_bytes"),
                "VOICE_AUTH_BYTE_BINDING",
                auth_rel,
                "authorization, profile, and WAV byte counts must match exactly",
            )
            report.check(
                binding.get("sha256") == actual_hash == profile.get("reference_sha256"),
                "VOICE_AUTH_HASH_BINDING",
                auth_rel,
                "authorization, profile, and WAV SHA-256 values must match exactly",
            )
        return wav_path.resolve()

    resolved_assets: dict[str, Path] = {}

    # Kira: exact project-owner-attested recording, private named-team use only.
    kira_dir = root / "voice_packs" / "kira"
    kira_profile_path = kira_dir / "current_voice_profile.json"
    kira_profile_rel = _relative(kira_profile_path, root)
    kira_profile = documents.get(kira_profile_path)
    report.check(
        isinstance(kira_profile, dict),
        "VOICE_PROFILE_MISSING",
        kira_profile_rel,
        "Kira current voice profile is missing",
    )
    if isinstance(kira_profile, dict):
        report.check(
            kira_profile.get("voice_mode")
            == "authorized_reference_conditioned_neural_voice",
            "KIRA_VOICE_MODE",
            kira_profile_rel,
            "Kira voice_mode must select the authorized reference-conditioned route",
        )
        report.check(
            kira_profile.get("provider") == "chatterbox_reference"
            and kira_profile.get("preferred_backend") == "chatterbox_tts",
            "VOICE_BACKEND_BINDING",
            kira_profile_rel,
            "Kira profile must bind the Chatterbox reference backend",
        )
        fallback = kira_profile.get("fallback")
        report.check(
            isinstance(fallback, dict)
            and fallback.get("mode") == "text_only_fail_closed"
            and fallback.get("generic_voice_allowed") is False,
            "VOICE_FALLBACK_POLICY",
            kira_profile_rel,
            "Kira must fail closed to text only and must not use a generic voice",
        )
        authorization_name = kira_profile.get("authorization")
        report.check(
            simple_local_name(authorization_name),
            "VOICE_AUTH_PATH",
            kira_profile_rel,
            "Kira profile must bind one local authorization JSON",
        )
        authorization_path = kira_dir / str(authorization_name)
        authorization_rel = _relative(authorization_path, root)
        authorization = documents.get(authorization_path)
        report.check(
            isinstance(authorization, dict),
            "VOICE_AUTH_MISSING",
            authorization_rel,
            "Kira owner-attested authorization is missing or invalid",
        )
        if isinstance(authorization, dict):
            report.check(
                kira_profile.get("authorization_sha256") == _sha256(authorization_path),
                "VOICE_AUTH_DOCUMENT_HASH_BINDING",
                kira_profile_rel,
                "Kira profile authorization_sha256 must bind the exact authorization JSON bytes",
            )
            asset = validate_exact_asset(
                label="Kira",
                directory=kira_dir,
                profile_path=kira_profile_path,
                profile=kira_profile,
                authorization=authorization,
                binding_key="exact_asset_binding",
                expected_person_id="kira",
                expected_sha256=KIRA_APPROVED_REFERENCE_SHA256,
                expected_bytes=KIRA_APPROVED_REFERENCE_BYTES,
            )
            if asset is not None:
                resolved_assets["kira"] = asset
                report.check(
                    {path.resolve() for path in kira_dir.rglob("*.wav")} == {asset},
                    "KIRA_UNBOUND_ASSET",
                    _relative(kira_dir, root),
                    "Kira directory must contain only the exact authorized WAV",
                )
            report.check(
                kira_profile.get("reference_wav") == "approved_reference.wav",
                "KIRA_APPROVED_ASSET_NAME",
                kira_profile_rel,
                "Kira reference must use the reviewed approved_reference.wav slot",
            )
            report.check(
                kira_profile.get("default_for_person") is True,
                "KIRA_VOICE_DEFAULT",
                kira_profile_rel,
                "the exact authorized Kira voice must be her default",
            )
            report.check(
                kira_profile.get("speaker_purity_review_status")
                == "pending_human_speaker_review",
                "KIRA_SPEAKER_PURITY_STATUS",
                kira_profile_rel,
                "profile must disclose pending_human_speaker_review",
            )
            report.check(
                kira_profile.get("multi_speaker_or_narration_risk") is True,
                "KIRA_SOURCE_MIX_RISK",
                kira_profile_rel,
                "profile must disclose possible narration/music/other-speaker content",
            )
            handling = kira_profile.get("handling")
            report.check(
                isinstance(handling, dict),
                "VOICE_PRIVACY_POLICY",
                kira_profile_rel,
                "Kira profile handling policy is required",
            )
            if isinstance(handling, dict):
                report.check(
                    handling.get("private_named_reviewers_only") is True,
                    "VOICE_PRIVATE_REVIEW_ONLY",
                    kira_profile_rel,
                    "Kira source recording is private named-reviewer only",
                )
                report.check(
                    handling.get("public_release_allowed") is False,
                    "VOICE_PUBLIC_RELEASE",
                    kira_profile_rel,
                    "Kira source recording cannot be publicly released",
                )
                report.check(
                    handling.get("onward_redistribution_allowed") is False,
                    "VOICE_ONWARD_REDISTRIBUTION",
                    kira_profile_rel,
                    "Kira source recording cannot be redistributed onward",
                )
                report.check(
                    handling.get("identity_authentication_allowed") is False,
                    "VOICE_IDENTITY_AUTH",
                    kira_profile_rel,
                    "Kira source recording cannot be used for identity authentication",
                )

            attestation = authorization.get("owner_attestation")
            report.check(
                isinstance(attestation, dict),
                "KIRA_OWNER_ATTESTATION",
                authorization_rel,
                "owner_attestation object is required",
            )
            if isinstance(attestation, dict):
                for key in (
                    "synthetic_voice_use_permitted",
                    "private_named_hanson_sharing_permitted",
                    "exact_source_recording_sharing_permitted",
                ):
                    report.check(
                        attestation.get(key) is True,
                        "KIRA_OWNER_ATTESTATION_SCOPE",
                        authorization_rel,
                        f"owner_attestation.{key} must be exactly true",
                    )
                recorded_date = attestation.get("recorded_date") or authorization.get("recorded_date")
                attestation_source = attestation.get("source") or authorization.get(
                    "authorization_basis"
                )
                report.check(
                    isinstance(recorded_date, str)
                    and re.fullmatch(r"\d{4}-\d{2}-\d{2}", recorded_date) is not None
                    and isinstance(attestation_source, str)
                    and bool(attestation_source.strip()),
                    "KIRA_OWNER_ATTESTATION_RECORD",
                    authorization_rel,
                    "owner attestation must record an ISO date and nonempty source",
                )
                report.check(
                    attestation.get("form_attachment_status") in {"pending", "pending_attachment"}
                    and (
                        attestation.get("form_absence_blocks_private_review") is False
                        or (
                            isinstance(authorization.get("handling"), dict)
                            and authorization["handling"].get(
                                "written_form_copy_pending_attachment"
                            )
                            is True
                        )
                    ),
                    "KIRA_PERMISSION_FORM_STATUS",
                    authorization_rel,
                    "permission form must be truthfully marked pending and nonblocking for this private review",
                )

            quality = authorization.get("quality_disclosure")
            report.check(
                isinstance(quality, dict),
                "KIRA_QUALITY_DISCLOSURE",
                authorization_rel,
                "authorization.quality_disclosure object is required",
            )
            if isinstance(quality, dict):
                report.check(
                    quality.get("speaker_purity_review_status")
                    == "pending_human_speaker_review"
                    and quality.get("multi_speaker_or_narration_risk") is True,
                    "KIRA_QUALITY_DISCLOSURE",
                    authorization_rel,
                    "quality disclosure must retain pending review and mixed-source risk",
                )
                report.check(
                    quality.get("human_approved_clip_count") == 0
                    and quality.get("auto_selected_clip_count") == 86
                    and quality.get("auto_selected_seconds") == 205.35,
                    "KIRA_SOURCE_SELECTION_DISCLOSURE",
                    authorization_rel,
                    "quality disclosure must distinguish 0 human-approved from 86/205.35s auto-selected clips",
                )
                report.check(
                    quality.get("model_readiness_eligible") is False
                    and quality.get("speaker_purity_verified") is False
                    and quality.get("target_speaker_only_verified") is False,
                    "KIRA_UNVERIFIED_PURITY_CLAIM",
                    authorization_rel,
                    "source cannot claim model-readiness or verified target-only speaker purity",
                )
            report.check(
                authorization.get("independent_legal_verification_performed") is False,
                "KIRA_INDEPENDENT_LEGAL_REVIEW_CLAIM",
                authorization_rel,
                "independent legal verification must be truthfully recorded as not performed",
            )

            recipients = authorization.get("named_recipients")
            report.check(
                isinstance(recipients, list)
                and all(isinstance(value, str) for value in recipients)
                and len(recipients) == len(expected_recipients)
                and set(recipients) == expected_recipients,
                "KIRA_NAMED_RECIPIENTS",
                authorization_rel,
                "authorization must be limited to David Hanson, Manav Tidhan, and Vytas Krisciunas",
            )
            allowed = authorization.get("allowed")
            allowed_uses = authorization.get("allowed_uses")
            allowed_uses_text = (
                "\n".join(allowed_uses).lower()
                if isinstance(allowed_uses, list)
                and all(isinstance(value, str) for value in allowed_uses)
                else ""
            )
            report.check(
                isinstance(allowed, dict)
                or (
                    bool(allowed_uses_text)
                    and "private" in allowed_uses_text
                    and "kira" in allowed_uses_text
                    and "hanson" in allowed_uses_text
                    and "sophia" in allowed_uses_text
                ),
                "KIRA_ALLOWED_SCOPE",
                authorization_rel,
                "authorization must enumerate private Kira/Hanson/Little Sophia allowed uses",
            )
            if isinstance(allowed, dict):
                for key in (
                    "synthetic_voice_use",
                    "private_named_hanson_sharing",
                    "exact_source_recording_sharing",
                ):
                    report.check(
                        allowed.get(key) is True,
                        "KIRA_ALLOWED_SCOPE",
                        authorization_rel,
                        f"allowed.{key} must be exactly true",
                    )

            auth_handling = authorization.get("handling")
            report.check(
                isinstance(auth_handling, dict),
                "KIRA_AUTH_HANDLING",
                authorization_rel,
                "authorization.handling object is required",
            )
            if isinstance(auth_handling, dict):
                report.check(
                    auth_handling.get("repository_visibility") == "private",
                    "VOICE_PRIVATE_REVIEW_ONLY",
                    authorization_rel,
                    "Kira voice asset must remain in a private repository",
                )
                for key in (
                    "public_release_allowed",
                    "onward_redistribution_allowed",
                    "identity_authentication_allowed",
                ):
                    report.check(
                        auth_handling.get(key) is False,
                        "KIRA_AUTH_RESTRICTION",
                        authorization_rel,
                        f"handling.{key} must be exactly false",
                    )
                report.check(
                    auth_handling.get("honor_withdrawal_or_supersession") is True,
                    "KIRA_WITHDRAWAL_POLICY",
                    authorization_rel,
                    "authorization must honor withdrawal or supersession",
                )
            withdrawal = authorization.get("withdrawal")
            report.check(
                isinstance(withdrawal, dict),
                "KIRA_WITHDRAWAL_POLICY",
                authorization_rel,
                "authorization.withdrawal process is required",
            )
            if isinstance(withdrawal, dict):
                report.check(
                    withdrawal.get("enabled") is True
                    and withdrawal.get("stop_future_use") is True
                    and withdrawal.get("remove_from_active_package") is True,
                    "KIRA_WITHDRAWAL_POLICY",
                    authorization_rel,
                    "withdrawal must stop future use and remove the asset from active packages",
                )
                report.check(
                    isinstance(withdrawal.get("request_route"), str)
                    and bool(withdrawal["request_route"].strip())
                    and isinstance(withdrawal.get("delete_or_history_remediation_process"), str)
                    and bool(withdrawal["delete_or_history_remediation_process"].strip()),
                    "KIRA_WITHDRAWAL_ROUTE",
                    authorization_rel,
                    "withdrawal must define a request route and deletion/history-remediation process",
                )
                remediation = withdrawal.get("delete_or_history_remediation_process")
                remediation_text = remediation.lower() if isinstance(remediation, str) else ""
                report.check(
                    "cannot be remotely erased" in remediation_text
                    and ("clone" in remediation_text or "cop" in remediation_text),
                    "KIRA_WITHDRAWAL_IRREVERSIBILITY_DISCLOSURE",
                    authorization_rel,
                    "withdrawal disclosure must say already-cloned/copied bytes cannot be remotely erased",
                )

            for source_document, source_rel in (
                (kira_profile, kira_profile_rel),
                (authorization, authorization_rel),
            ):
                for node_path, key, value in _iter_nodes(source_document):
                    if key is not None and _normalized_key(key) in {
                        "female_only_voice",
                        "source_woman_only",
                        "speaker_purity_verified",
                        "target_speaker_only_verified",
                        "verified_target_only",
                    }:
                        report.check(
                            value is False,
                            "KIRA_UNVERIFIED_PURITY_CLAIM",
                            source_rel,
                            f"{node_path} must be exactly false while human speaker review is pending",
                        )

    # Synthetic Robert: exact authorized self-voice, also private-only.
    robert_dir = root / "voice_packs" / "robert"
    robert_profile_path = robert_dir / "voice_profile.json"
    robert_profile_rel = _relative(robert_profile_path, root)
    robert_profile = documents.get(robert_profile_path)
    report.check(
        isinstance(robert_profile, dict),
        "VOICE_PROFILE_MISSING",
        robert_profile_rel,
        "Synthetic Robert voice profile is missing",
    )
    if isinstance(robert_profile, dict):
        report.check(
            robert_profile.get("provider") == "chatterbox_reference"
            and robert_profile.get("preferred_backend") == "chatterbox_tts",
            "VOICE_BACKEND_BINDING",
            robert_profile_rel,
            "Robert profile must bind the Chatterbox reference backend",
        )
        report.check(
            robert_profile.get("default_for_person") is True,
            "ROBERT_VOICE_DEFAULT",
            robert_profile_rel,
            "the exact authorized Robert voice must be his default",
        )
        fallback = robert_profile.get("fallback")
        report.check(
            isinstance(fallback, dict)
            and fallback.get("mode") == "text_only_fail_closed"
            and fallback.get("generic_voice_allowed") is False,
            "VOICE_FALLBACK_POLICY",
            robert_profile_rel,
            "Robert must fail closed to text only and must not use a generic voice",
        )
        claim_boundary = robert_profile.get("claim_boundary")
        report.check(
            isinstance(claim_boundary, dict)
            and claim_boundary.get("synthetic_robert_is_distinct_from_biological_robert")
            is True
            and claim_boundary.get("voice_is_not_identity_authentication") is True
            and claim_boundary.get("legal_or_external_impersonation_allowed") is False
            and claim_boundary.get("public_release_allowed") is False
            and claim_boundary.get("onward_redistribution_allowed") is False,
            "ROBERT_PROFILE_CLAIM_BOUNDARY",
            robert_profile_rel,
            "Robert profile must preserve identity, impersonation, public-release, and onward-sharing boundaries",
        )
        auth_name = robert_profile.get("authorization")
        report.check(
            simple_local_name(auth_name),
            "VOICE_AUTH_PATH",
            robert_profile_rel,
            "Robert profile must bind one local authorization JSON",
        )
        auth_path = robert_dir / str(auth_name)
        auth_rel = _relative(auth_path, root)
        authorization = documents.get(auth_path)
        report.check(
            isinstance(authorization, dict),
            "VOICE_AUTH_MISSING",
            auth_rel,
            "Robert self-voice authorization is missing or invalid",
        )
        if isinstance(authorization, dict):
            report.check(
                robert_profile.get("authorization_sha256") == _sha256(auth_path),
                "VOICE_AUTH_DOCUMENT_HASH_BINDING",
                robert_profile_rel,
                "Robert profile authorization_sha256 must bind the exact authorization JSON bytes",
            )
            asset = validate_exact_asset(
                label="Synthetic Robert",
                directory=robert_dir,
                profile_path=robert_profile_path,
                profile=robert_profile,
                authorization=authorization,
                binding_key="asset_binding",
                expected_person_id="synthetic_robert",
                expected_sha256=ROBERT_APPROVED_REFERENCE_SHA256,
                expected_bytes=ROBERT_APPROVED_REFERENCE_BYTES,
            )
            if asset is not None:
                resolved_assets["synthetic_robert"] = asset
                report.check(
                    {path.resolve() for path in robert_dir.rglob("*.wav")} == {asset},
                    "ROBERT_UNBOUND_ASSET",
                    _relative(robert_dir, root),
                    "Robert directory must contain only the exact authorized WAV",
                )
            authorized_by = authorization.get("authorized_by")
            report.check(
                isinstance(authorized_by, dict)
                and authorized_by.get("self_voice_subject") is True
                and authorized_by.get("project_owner") is True,
                "ROBERT_SELF_VOICE_AUTHORIZATION",
                auth_rel,
                "Robert authorization must come from the self-voice subject/project owner",
            )
            recipients = authorization.get("named_recipients")
            report.check(
                isinstance(recipients, list)
                and all(isinstance(value, str) for value in recipients)
                and len(recipients) == len(expected_recipients)
                and set(recipients) == expected_recipients,
                "ROBERT_NAMED_RECIPIENTS",
                auth_rel,
                "Robert authorization must be limited to David Hanson, Manav Tidhan, and Vytas Krisciunas",
            )
            allowed = authorization.get("allowed")
            report.check(
                isinstance(allowed, dict)
                and all(
                    allowed.get(key) is True
                    for key in (
                        "private_evaluation",
                        "private_little_sophia_integration_research",
                        "private_local_speech_rendering_for_synthetic_robert",
                        "internal_derivative_voice_model_for_the_same_bound_variant",
                    )
                ),
                "ROBERT_ALLOWED_SCOPE",
                auth_rel,
                "Robert authorization must enumerate the exact private evaluation, speech, and integration scope",
            )
            not_allowed = authorization.get("not_allowed")
            report.check(
                isinstance(not_allowed, dict)
                and not_allowed.get("public_release") is True
                and not_allowed.get("onward_redistribution") is True
                and not_allowed.get("identity_authentication") is True,
                "ROBERT_VOICE_RESTRICTIONS",
                auth_rel,
                "Robert authorization must forbid public release, onward redistribution, and identity authentication",
            )
            handling = authorization.get("handling")
            report.check(
                isinstance(handling, dict)
                and handling.get("repository_visibility") == "private"
                and handling.get("honor_withdrawal_or_supersession") is True,
                "ROBERT_VOICE_HANDLING",
                auth_rel,
                "Robert voice must remain private and honor withdrawal/supersession",
            )

    report.check(
        set(resolved_assets) == {"kira", "synthetic_robert"},
        "VOICE_EXACT_ASSETS_REQUIRED",
        "voice_packs",
        "both Kira and Synthetic Robert exact authorized voice assets are required",
    )
    if set(resolved_assets) == {"kira", "synthetic_robert"}:
        report.check(
            resolved_assets["kira"] != resolved_assets["synthetic_robert"]
            and _sha256(resolved_assets["kira"]) != _sha256(resolved_assets["synthetic_robert"]),
            "VOICE_ASSET_SEPARATION",
            "voice_packs",
            "Kira and Synthetic Robert must use separate exact voice assets",
        )

    # All operational JSON filenames referenced by a voice file must resolve
    # within voice_packs; a stale/deleted authorization fails publication.
    internal_reference_keys = {
        "authorization",
        "configuration",
        "configuration_file",
        "manifest",
        "profile",
        "provenance",
        "source_manifest",
        "working_voice_available",
    }
    voice_root = root / "voice_packs"
    for source_path, document in documents.items():
        if not _inside(source_path, voice_root):
            continue
        source_rel = _relative(source_path, root)
        for node_path, key, value in _iter_nodes(document):
            if (
                key is None
                or _normalized_key(key) not in internal_reference_keys
                or not isinstance(value, str)
                or not value.lower().endswith(".json")
            ):
                continue
            target = (source_path.parent / value).resolve()
            report.check(
                not Path(value).is_absolute()
                and re.match(r"(?i)^[A-Z]:[\\/]", value) is None
                and _inside(target, voice_root.resolve()),
                "VOICE_JSON_REFERENCE_PATH",
                source_rel,
                f"{node_path} must stay inside voice_packs",
            )
            report.check(
                target.is_file() and target in documents,
                "VOICE_JSON_REFERENCE_MISSING",
                source_rel,
                f"{node_path} points to missing/invalid JSON: {value!r}",
            )

    for path, document in documents.items():
        if not _inside(path, voice_root):
            continue
        rel = _relative(path, root)
        for node_path, key, value in _iter_nodes(document):
            if key in {"public_release_allowed", "onward_redistribution_allowed"}:
                report.check(
                    value is False,
                    "VOICE_DISTRIBUTION_PERMISSIVE",
                    rel,
                    f"{node_path} must be exactly false in this private handoff",
                )


def _extract_markdown_targets(text: str) -> Iterator[str]:
    for match in MARKDOWN_INLINE_LINK_RE.finditer(text):
        yield match.group(1).strip()
    for match in MARKDOWN_REFERENCE_LINK_RE.finditer(text):
        yield match.group(1).strip()


def _normalize_markdown_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " " in target:
        # A Markdown title may follow the URL. Unescaped spaces in the URL are
        # not portable and therefore intentionally resolve only the first token.
        target = target.split()[0]
    target = target.split("#", 1)[0].split("?", 1)[0]
    return unquote(target)


def _validate_markdown_links(
    root: Path, files: Iterable[Path], report: ValidationReport
) -> None:
    repo_root = _repository_root(root)
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        rel = _relative(path, root)
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeError):
            continue
        for raw_target in _extract_markdown_targets(text):
            target = _normalize_markdown_target(raw_target)
            if not target or target.startswith("#"):
                continue
            lower = target.lower()
            if lower.startswith(("http://", "https://", "mailto:", "ftp://", "data:")) or target.startswith("//"):
                continue
            report.markdown_links += 1
            if Path(target).is_absolute() or re.match(r"(?i)^[A-Z]:[\\/]", target):
                report.check(False, "MARKDOWN_ABSOLUTE_LINK", rel, f"local link must be relative: {raw_target!r}")
                continue
            resolved = (path.parent / Path(target.replace("/", os.sep))).resolve()
            report.check(
                _inside(resolved, repo_root),
                "MARKDOWN_LINK_ESCAPES_REPO",
                rel,
                f"local link escapes repository: {raw_target!r}",
            )
            report.check(
                resolved.exists(),
                "MARKDOWN_LINK_MISSING",
                rel,
                f"local link target does not exist: {raw_target!r}",
            )


def validate_handoff(root: Path | str) -> ValidationReport:
    root_path = Path(root).resolve()
    report = ValidationReport(root=str(root_path))
    report.check(root_path.is_dir(), "HANDOFF_ROOT_MISSING", ".", "handoff root does not exist")
    if not root_path.is_dir():
        return report

    files = _validate_file_inventory(root_path, report)
    documents = _validate_json(root_path, files, report)
    _validate_no_concrete_sensitive_data(root_path, files, documents, report)
    _validate_memory_exports(root_path, documents, report)
    _validate_person_file_bindings(root_path, documents, report)
    _validate_voice_packs(root_path, documents, report)
    _validate_markdown_links(root_path, files, report)
    report.passed = not report.issues
    return report


def _default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _print_text(report: ValidationReport) -> None:
    status = "PASS" if report.passed else "FAIL"
    print(f"HANDOFF_VALIDATION {status}")
    print(f"root: {report.root}")
    print(f"checks_run: {report.checks_run}")
    print(f"files_scanned: {report.files_scanned}")
    print(f"json_documents: {report.json_documents}")
    print(f"markdown_links: {report.markdown_links}")
    print(f"issues: {len(report.issues)}")
    for issue in report.issues:
        print(f"- [{issue.code}] {issue.path}: {issue.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=_default_root(),
        help="handoff directory (defaults to the parent of this tools directory)",
    )
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args(argv)
    report = validate_handoff(args.root)
    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False, allow_nan=False))
    else:
        _print_text(report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
