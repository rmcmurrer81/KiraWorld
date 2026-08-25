"""Fail-closed resolver for the two owner-approved generic starter voices.

The release manifest is an application-facing assignment table, not a resident
voice registry.  It exposes only two original built-in Kokoro voices and their
owner-approved preview files.  Existing character authorities are attested and
preserved, while Kira, Lisa, and H. H. Holmes remain explicitly unassigned.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .backends.kokoro_subprocess import ALLOWLIST, MODEL_REPO, MODEL_REVISION
from .errors import NotFoundError, ValidationError
from .paths import PinnedDirectory, safe_component

RELEASE_SCHEMA = "kira.local-voice.approved-starter-release.v1"
DEFAULT_MANIFEST_RELATIVE_PATH = Path(
    "Voice/local_voice_studio/release/approved_starter_voice_release_v1.json"
)
MAX_JSON_BYTES = 128 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_APPROVAL_RELATIVE_PATH = (
    "Voice/local_voice_studio/auditions/catalog_20260825/"
    "starter-owner-approval.json"
)
_ATTRIBUTION_RELATIVE_PATH = "Voice/local_voice_studio/THIRD_PARTY_ATTRIBUTION.md"
_PROVIDER_RELATIVE_PATH = (
    "Voice/local_voice_studio/src/kira_local_voice/backends/kokoro_subprocess.py"
)
_ROUTES = {
    "starter.calm_female": {
        "voice_id": "af_heart",
        "product_label": "calm female",
        "voice_presentation": "female",
        "preview_relative_path": (
            "Voice/local_voice_studio/auditions/catalog_20260825/"
            "calm_female_approved.wav"
        ),
        "preview_sha256": "c3e3682817476212c990969901028758fbbde1eb4eb8c97153ef878b3939b33a",
    },
    "starter.warm_male": {
        "voice_id": "am_fenrir",
        "product_label": "warm male",
        "voice_presentation": "male",
        "preview_relative_path": (
            "Voice/local_voice_studio/auditions/catalog_20260825/"
            "warm_male_approved.wav"
        ),
        "preview_sha256": "0a8cdb8178bf56a6aa2442cca496dcf87a76b52e8eb0743488dc5f0e8c8a8a8e",
    },
}
_CONSUMER_DEFAULTS = {
    "avatar_builder.nonbinding_preview.female": "starter.calm_female",
    "avatar_builder.nonbinding_preview.male": "starter.warm_male",
    "hackathon.health_companion.voice.female": "starter.calm_female",
    "hackathon.health_companion.voice.male": "starter.warm_male",
    "hackathon.setsignal.voice.female": "starter.calm_female",
    "hackathon.setsignal.voice.male": "starter.warm_male",
    "hackathon.unitday.voice.female": "starter.calm_female",
    "hackathon.unitday.voice.male": "starter.warm_male",
    "hackathon.unitline.voice.female": "starter.calm_female",
    "hackathon.unitline.voice.male": "starter.warm_male",
    "temporary_creator.nonbinding_preview.female": "starter.calm_female",
    "temporary_creator.nonbinding_preview.male": "starter.warm_male",
}
_PRESERVED = {
    "ladybug_marinette_expanded_smoke": {
        "voice_id": "ladybug_voice_canon_v1",
        "profile_relative_path": "Voice/profiles/temp_ai/ladybug_voice_profile.json",
        "profile_sha256": "22abeadcf9821234b35bf48c6338cbdc89738b2285ef2514b423240f4133b998",
    },
    "peter_parker_spider_man_no_way_home_final_suit": {
        "voice_id": "peter_parker_reviewed_reference_v1",
        "profile_relative_path": "Voice/profiles/temp_ai/peter_parker_voice_profile.json",
        "profile_sha256": "04f604b69d13fbfb1ad3b9e27797177bf39e45d1eeb6ed8d0567d9b633b861c1",
    },
}
_BLOCKED_SUBJECTS = {
    "h_h_holmes": "speculative_historical_design_and_separate_approval_required",
    "kira": "subject_comparative_selection_required_current_route_preserved",
    "lisa": "subject_comparative_selection_required_no_owned_profile",
}
_PROTECTED_EVIDENCE = {
    "h_h_holmes": (
        (
            "Voice/profiles/temp_ai/h_h_holmes_voice_profile.json",
            "3c6178fd003d93719591636391c30d18758870d0c825fbdf79c17bc5fc2ddc0d",
        ),
    ),
    "kira": (
        (
            "Voice/profiles/temp_ai/kira_voice_profile.json",
            "102d17f5420a1a16b3a920204ebde0d532c0a9bfd2979dca28048378ecddc116",
        ),
        (
            "Voice/sidecars/kira_approved_voice_routing.json",
            "a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81",
        ),
    ),
    "lisa": (),
}
_TOP_LEVEL_KEYS = {
    "schema",
    "status",
    "owner_approval",
    "provider",
    "routes",
    "consumer_defaults",
    "preserved_existing_authorities",
    "blocked_subject_assignments",
    "protected_authority_evidence",
    "release_boundary",
}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key rejected: {key}")
        result[key] = value
    return result


def _is_reparse(path: Path) -> bool:
    if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & getattr(__import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _relative_regular_file(project_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValidationError("release paths must be nonempty repository-relative POSIX paths")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValidationError("release paths must not be absolute or contain traversal")
    cursor = project_root
    for index, part in enumerate(pure.parts):
        cursor = cursor / part
        if not cursor.exists():
            raise NotFoundError(f"release file is missing: {value}")
        if _is_reparse(cursor):
            raise ValidationError(f"release path contains a link or reparse point: {value}")
        if index < len(pure.parts) - 1 and not cursor.is_dir():
            raise ValidationError(f"release path ancestor is not a directory: {value}")
    if not cursor.is_file():
        raise ValidationError(f"release path is not a regular file: {value}")
    resolved = cursor.resolve(strict=True)
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise ValidationError("release path escapes the repository root") from exc
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValidationError("release JSON exceeds the bounded size limit")
    try:
        # Existing reviewed profile files include both UTF-8 and UTF-8-with-BOM.
        # ``utf-8-sig`` accepts both while preserving the byte-level SHA-256
        # attestation performed before parsing.
        payload = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object)
    except UnicodeDecodeError as exc:
        raise ValidationError("release JSON must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError("release JSON is malformed") from exc
    if not isinstance(payload, dict):
        raise ValidationError("release JSON root must be an object")
    return payload


def _require_hash(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValidationError(f"{field} must be a lowercase SHA-256")
    return value


def _require_exact_keys(payload: dict[str, Any], expected: set[str], *, label: str) -> None:
    if set(payload) != expected:
        raise ValidationError(f"{label} fields differ from the release contract")


@dataclass(frozen=True, slots=True)
class ApprovedStarterRoute:
    consumer_id: str
    route_id: str
    voice_id: str
    product_label: str
    voice_presentation: str
    approved_preview_relative_path: str
    approved_preview_sha256: str
    assignment_class: str

    def to_dict(self) -> dict[str, str]:
        return {
            "consumer_id": self.consumer_id,
            "route_id": self.route_id,
            "voice_id": self.voice_id,
            "product_label": self.product_label,
            "voice_presentation": self.voice_presentation,
            "approved_preview_relative_path": self.approved_preview_relative_path,
            "approved_preview_sha256": self.approved_preview_sha256,
            "assignment_class": self.assignment_class,
        }


class ApprovedStarterVoiceRelease:
    """Validate and resolve the immutable approved-only starter assignment table."""

    def __init__(
        self,
        project_root: Path,
        *,
        manifest_relative_path: Path = DEFAULT_MANIFEST_RELATIVE_PATH,
    ):
        self.project_root = project_root.expanduser().resolve(strict=True)
        self._root_pin = PinnedDirectory.capture(self.project_root)
        manifest_value = manifest_relative_path.as_posix()
        self.manifest_path = _relative_regular_file(self.project_root, manifest_value)
        self.manifest_relative_path = manifest_value
        self._manifest_sha256 = _hash_file(self.manifest_path)
        self.payload = _read_json(self.manifest_path)
        self._validate()

    def _attest(self, relative: object, expected_hash: object, *, label: str) -> Path:
        path = _relative_regular_file(self.project_root, relative)
        digest = _require_hash(expected_hash, field=f"{label} sha256")
        if _hash_file(path) != digest:
            raise ValidationError(f"{label} content digest mismatch")
        return path

    def _validate_approval(self) -> dict[str, dict[str, Any]]:
        approval = self.payload.get("owner_approval")
        if not isinstance(approval, dict):
            raise ValidationError("owner_approval must be an object")
        _require_exact_keys(
            approval,
            {"relative_path", "sha256", "approver_role", "scope", "decision"},
            label="owner_approval",
        )
        if approval != {
            "relative_path": _APPROVAL_RELATIVE_PATH,
            "sha256": "b91de4433382af5e1d9b92ed12773707f59624d85ddd735efdb6e15a2d4df175",
            "approver_role": "product_owner",
            "scope": "starter voices for hackathon projects",
            "decision": "approved",
        }:
            raise ValidationError("owner approval identity or scope differs from the reviewed decision")
        approval_path = self._attest(
            approval["relative_path"], approval["sha256"], label="owner approval"
        )
        decision = _read_json(approval_path)
        if (
            decision.get("schema") != "kira-labs-local-voice-audition-v1"
            or decision.get("approver_role") != "product_owner"
            or decision.get("scope") != "starter voices for hackathon projects"
            or decision.get("decision") != "approved"
        ):
            raise ValidationError("owner decision content no longer grants the exact starter scope")
        voices = decision.get("voices")
        if not isinstance(voices, list) or len(voices) != 2:
            raise ValidationError("owner decision must contain exactly two approved voices")
        by_id: dict[str, dict[str, Any]] = {}
        for item in voices:
            if not isinstance(item, dict) or set(item) != {
                "voice_id", "product_label", "sample_file", "sample_sha256", "decision"
            }:
                raise ValidationError("owner decision voice fields differ from the contract")
            voice_id = safe_component(item.get("voice_id"), field="approved voice_id")
            if voice_id in by_id or item.get("decision") != "approved":
                raise ValidationError("owner decision contains a duplicate or unapproved voice")
            by_id[voice_id] = item
        if set(by_id) != set(ALLOWLIST) or set(by_id) != {"af_heart", "am_fenrir"}:
            raise ValidationError("owner decision differs from the exact two-voice runtime allowlist")
        return by_id

    def _validate_provider(self) -> None:
        provider = self.payload.get("provider")
        if not isinstance(provider, dict):
            raise ValidationError("provider must be an object")
        expected = {
            "provider_id": "kokoro_subprocess_exact_two_voice_v1",
            "source_relative_path": _PROVIDER_RELATIVE_PATH,
            "source_sha256": "a902e6f589b0694997de8557da151d478d33a59679f8d5291216281f95b2d13d",
            "model_repo": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "license_id": "Apache-2.0",
            "runtime_voice_ids": ["af_heart", "am_fenrir"],
            "synthesis_readiness": "fail_closed_pending_reviewed_os_isolation_provider",
            "identity_claim": False,
        }
        if provider != expected:
            raise ValidationError("provider record differs from the exact reviewed source and pins")
        self._attest(provider["source_relative_path"], provider["source_sha256"], label="provider")

    def _validate_routes(self, approved: dict[str, dict[str, Any]]) -> None:
        routes = self.payload.get("routes")
        if not isinstance(routes, list) or len(routes) != 2:
            raise ValidationError("routes must contain exactly two entries")
        found: set[str] = set()
        route_fields = {
            "route_id", "voice_id", "product_label", "voice_presentation",
            "approved_preview_relative_path", "approved_preview_sha256",
            "assignment_class", "resident_assignment_created", "identity_claim",
            "allowed_use",
        }
        for route in routes:
            if not isinstance(route, dict):
                raise ValidationError("each route must be an object")
            _require_exact_keys(route, route_fields, label="route")
            route_id = safe_component(route.get("route_id"), field="route_id")
            expected = _ROUTES.get(route_id)
            if expected is None or route_id in found:
                raise ValidationError("route is unknown or duplicated")
            found.add(route_id)
            voice_id = route.get("voice_id")
            decision = approved.get(str(voice_id))
            if decision is None:
                raise ValidationError("route voice is not in the exact owner decision")
            if route.get("product_label") != expected["product_label"]:
                raise ValidationError("route product label differs from the owner decision")
            if decision.get("product_label") != route.get("product_label"):
                raise ValidationError("route product label is not owner approved")
            if route.get("voice_id") != expected["voice_id"]:
                raise ValidationError("route voice_id differs from the exact assignment")
            if route.get("voice_presentation") != expected["voice_presentation"]:
                raise ValidationError("route presentation differs from the exact assignment")
            if route.get("approved_preview_relative_path") != expected["preview_relative_path"]:
                raise ValidationError("route preview is not an approved release file")
            if route.get("approved_preview_sha256") != expected["preview_sha256"]:
                raise ValidationError("route preview digest differs from the approved release file")
            if decision.get("sample_file") != Path(expected["preview_relative_path"]).name:
                raise ValidationError("route preview filename differs from the owner decision")
            if decision.get("sample_sha256") != expected["preview_sha256"]:
                raise ValidationError("route preview digest differs from the owner decision")
            if route.get("assignment_class") != "generic_product_voice":
                raise ValidationError("starter routes cannot become identity assignments")
            if route.get("resident_assignment_created") is not False:
                raise ValidationError("starter routes cannot assign a KiraWorld resident")
            if route.get("identity_claim") is not False:
                raise ValidationError("starter routes cannot carry a human identity claim")
            if route.get("allowed_use") != [
                "hackathon_app_product_voice",
                "temporary_creator_nonbinding_audition_preview",
                "avatar_builder_nonbinding_audition_preview",
            ]:
                raise ValidationError("route use scope differs from the approved release boundary")
            self._attest(
                route["approved_preview_relative_path"],
                route["approved_preview_sha256"],
                label=f"{route_id} preview",
            )
        if found != set(_ROUTES):
            raise ValidationError("the exact approved starter routes are not present")

    def _validate_consumers(self) -> None:
        consumers = self.payload.get("consumer_defaults")
        if consumers != _CONSUMER_DEFAULTS:
            raise ValidationError("consumer defaults differ from the reviewed nonbinding assignments")

    def _validate_preserved(self) -> None:
        entries = self.payload.get("preserved_existing_authorities")
        if not isinstance(entries, list) or len(entries) != len(_PRESERVED):
            raise ValidationError("preserved voice authorities are incomplete")
        found: set[str] = set()
        fields = {
            "candidate_id", "voice_id", "profile_relative_path", "profile_sha256",
            "policy", "released_audio_in_this_manifest",
        }
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValidationError("preserved voice authority must be an object")
            _require_exact_keys(entry, fields, label="preserved voice authority")
            candidate_id = safe_component(entry.get("candidate_id"), field="preserved candidate_id")
            expected = _PRESERVED.get(candidate_id)
            if expected is None or candidate_id in found:
                raise ValidationError("preserved voice authority is unknown or duplicated")
            found.add(candidate_id)
            if (
                entry.get("voice_id") != expected["voice_id"]
                or entry.get("profile_relative_path") != expected["profile_relative_path"]
                or entry.get("profile_sha256") != expected["profile_sha256"]
                or entry.get("policy") != "preserve_existing_verified_voice_no_export"
                or entry.get("released_audio_in_this_manifest") is not False
            ):
                raise ValidationError("preserved voice authority differs from its exact existing profile")
            path = self._attest(
                entry["profile_relative_path"], entry["profile_sha256"], label=candidate_id
            )
            profile = _read_json(path)
            if (
                profile.get("candidate_id") != candidate_id
                or profile.get("voice_id") != expected["voice_id"]
            ):
                raise ValidationError("preserved profile identity differs from its authority record")
        if found != set(_PRESERVED):
            raise ValidationError("preserved voice authorities are incomplete")

    def _validate_blocked(self) -> None:
        blocked = self.payload.get("blocked_subject_assignments")
        if not isinstance(blocked, list) or len(blocked) != len(_BLOCKED_SUBJECTS):
            raise ValidationError("blocked subject assignments are incomplete")
        actual: dict[str, str] = {}
        for entry in blocked:
            if not isinstance(entry, dict) or set(entry) != {
                "subject_id", "status", "rule", "starter_route_id"
            }:
                raise ValidationError("blocked subject assignment fields differ from the contract")
            subject_id = safe_component(entry.get("subject_id"), field="blocked subject_id")
            if subject_id in actual:
                raise ValidationError("blocked subject assignment is duplicated")
            if entry.get("status") != "not_assigned" or entry.get("starter_route_id") is not None:
                raise ValidationError("protected subject received a starter assignment")
            actual[subject_id] = str(entry.get("rule"))
        if actual != _BLOCKED_SUBJECTS:
            raise ValidationError("protected subject selection rules differ from the contract")

        evidence = self.payload.get("protected_authority_evidence")
        if not isinstance(evidence, dict) or set(evidence) != set(_PROTECTED_EVIDENCE):
            raise ValidationError("protected authority evidence is incomplete")
        for subject_id, expected_files in _PROTECTED_EVIDENCE.items():
            records = evidence.get(subject_id)
            if not isinstance(records, list) or len(records) != len(expected_files):
                raise ValidationError("protected authority evidence file count differs")
            expected_records = [
                {"relative_path": relative, "sha256": digest}
                for relative, digest in expected_files
            ]
            if records != expected_records:
                raise ValidationError("protected authority evidence differs from the exact current files")
            for record in records:
                self._attest(
                    record["relative_path"], record["sha256"], label=f"{subject_id} authority"
                )

    def _validate_release_boundary(self) -> None:
        boundary = self.payload.get("release_boundary")
        expected = {
            "distributable_audio_paths": sorted(
                item["preview_relative_path"] for item in _ROUTES.values()
            ),
            "distributable_metadata_paths": sorted(
                [_APPROVAL_RELATIVE_PATH, _ATTRIBUTION_RELATIVE_PATH]
            ),
            "excluded_categories": [
                "unapproved_auditions",
                "private_or_third_party_reference_audio",
                "model_weights",
                "model_or_package_caches",
                "generated_resident_audio",
            ],
            "raw_or_reference_audio_included": False,
            "unapproved_auditions_included": False,
            "model_weights_or_caches_included": False,
            "resident_audio_included": False,
            "manifest_creates_resident_assignment": False,
        }
        if boundary != expected:
            raise ValidationError("release boundary differs from the approved-only export contract")
        self._attest(
            _ATTRIBUTION_RELATIVE_PATH,
            "366d3d0261663cbc2b90060f047e2b46beef803a8aeb8efa1da806dbeff2b08b",
            label="third-party attribution",
        )

    def _validate(self) -> None:
        self._root_pin.assert_unchanged()
        _require_exact_keys(self.payload, _TOP_LEVEL_KEYS, label="release manifest")
        if self.payload.get("schema") != RELEASE_SCHEMA:
            raise ValidationError("release manifest schema is unsupported")
        if self.payload.get("status") != "approved_starter_routes_only":
            raise ValidationError("release manifest is not approved for starter routing")
        approved = self._validate_approval()
        self._validate_provider()
        self._validate_routes(approved)
        self._validate_consumers()
        self._validate_preserved()
        self._validate_blocked()
        self._validate_release_boundary()

    def _assert_current(self) -> None:
        """Re-attest the manifest and every dependency before each public read."""

        self._root_pin.assert_unchanged()
        current = _relative_regular_file(self.project_root, self.manifest_relative_path)
        if _hash_file(current) != self._manifest_sha256:
            raise ValidationError("release manifest changed after validation")
        self._validate()

    def resolve(self, consumer_id: str) -> ApprovedStarterRoute:
        """Resolve one exact product/preview selector; never accept a subject ID."""

        self._assert_current()
        consumer = safe_component(consumer_id, field="consumer_id")
        route_id = _CONSUMER_DEFAULTS.get(consumer)
        if route_id is None:
            raise NotFoundError("consumer is not an approved starter voice selector")
        route = next(item for item in self.payload["routes"] if item["route_id"] == route_id)
        return ApprovedStarterRoute(
            consumer_id=consumer,
            route_id=route_id,
            voice_id=route["voice_id"],
            product_label=route["product_label"],
            voice_presentation=route["voice_presentation"],
            approved_preview_relative_path=route["approved_preview_relative_path"],
            approved_preview_sha256=route["approved_preview_sha256"],
            assignment_class=route["assignment_class"],
        )

    def release_inventory(self) -> tuple[dict[str, Any], ...]:
        """Return the complete upload allowlist with current content digests."""

        self._assert_current()
        boundary = self.payload["release_boundary"]
        paths = [
            self.manifest_relative_path,
            *boundary["distributable_audio_paths"],
            *boundary["distributable_metadata_paths"],
        ]
        records = []
        for relative in sorted(set(paths)):
            path = _relative_regular_file(self.project_root, relative)
            records.append(
                {
                    "relative_path": relative,
                    "sha256": _hash_file(path),
                    "size_bytes": path.stat().st_size,
                    "kind": (
                        "approved_synthesized_preview"
                        if relative.endswith(".wav")
                        else "release_metadata"
                    ),
                }
            )
        return tuple(records)
