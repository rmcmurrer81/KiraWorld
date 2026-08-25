"""Read-only Avatar/Temporary Creator voice-audition integration seam.

This module consumes the real Avatar identity registry and TemporaryAI source
records.  It inventories current identities, preserves established voice
authorities, and emits nonbinding, source-attested audition briefs for exact
profiles that still lack an accepted voice.  It never edits source profiles,
creates a binding, activates a person, or changes a runtime route.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .paths import PinnedDirectory, safe_component
from .temporary_creator_adapter import (
    TemporaryCreatorVoiceAdapter,
    _is_reparse_point,
    _read_json_attested,
    _regular_file_below,
    _text,
)
from .voice_design import AssignmentMode, VoiceDesignBrief

INTEGRATION_SCHEMA = "kira.local-voice.avatar-temporary-creator-audition-plan.v1"
INVENTORY_SCOPE = "current_temporary_ai_profile"
MAX_VOICE_PROFILES = 64
_BCP47 = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")

KIRA_CANDIDATE_ID = "kira"
ROBERT_CANDIDATE_ID = "robert_mcmurrer_presence_ai"
HOLMES_CANDIDATE_ID = "h_h_holmes_h_h_holmes_20260605_221432"
KIRA_PROFILE_PATH = Path("Voice/profiles/temp_ai/kira_voice_profile.json")
KIRA_ROUTE_PATH = Path("Voice/sidecars/kira_approved_voice_routing.json")
ROBERT_PROFILE_PATH = Path("Voice/profiles/temp_ai/robert_mcmurrer_voice_profile.json")
HOLMES_PROFILE_PATH = Path("Voice/profiles/temp_ai/h_h_holmes_voice_profile.json")
LEGACY_FILENAME_AUTHORITIES = {
    HOLMES_PROFILE_PATH.name: HOLMES_CANDIDATE_ID,
    KIRA_PROFILE_PATH.name: KIRA_CANDIDATE_ID,
    ROBERT_PROFILE_PATH.name: ROBERT_CANDIDATE_ID,
}

HISTORICAL_DISCLOSURE = (
    "Speculative historical reconstruction; not an authentic recording, "
    "verified voice match, or identity clone."
)


def _exact_candidate_names(item: Mapping[str, Any]) -> set[str]:
    return {
        item["canonical_candidate_id"],
        item["storage_id"],
        *item["aliases"],
    }


def _status_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("readiness_label", "approval_state", "status"):
            text = _text(value.get(key))
            if text:
                return text
    return "unlabeled"


class AvatarTemporaryCreatorVoiceIntegration:
    """Build a bounded source-derived audition plan without side effects."""

    def __init__(
        self,
        project_root: Path,
        *,
        adapter: TemporaryCreatorVoiceAdapter | None = None,
    ):
        self.project_root = project_root.expanduser().resolve(strict=True)
        self._root_pin = PinnedDirectory.capture(self.project_root)
        self.adapter = adapter or TemporaryCreatorVoiceAdapter(self.project_root)
        if self.adapter.project_root != self.project_root:
            raise ValidationError("voice adapter and integration project roots differ")

    def _assert_root(self) -> None:
        self._root_pin.assert_unchanged()

    def _voice_profile_directory(self) -> Path:
        relative = Path("Voice/profiles/temp_ai")
        cursor = self.project_root
        for part in relative.parts:
            cursor = cursor / part
            if not cursor.exists():
                raise ValidationError("TemporaryAI voice profile directory is missing")
            if _is_reparse_point(cursor):
                raise ValidationError("TemporaryAI voice profile directory contains a link or reparse point")
        resolved = cursor.resolve(strict=True)
        try:
            resolved.relative_to(self.project_root)
        except ValueError as exc:
            raise ValidationError("TemporaryAI voice profile directory escapes the project root") from exc
        if not resolved.is_dir():
            raise ValidationError("TemporaryAI voice profile location is not a directory")
        return resolved

    def _exact_voice_profiles(
        self,
        inventory: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        aliases: dict[str, str] = {}
        for item in inventory:
            canonical = item["canonical_candidate_id"]
            for name in _exact_candidate_names(item):
                previous = aliases.get(name)
                if previous is not None and previous != canonical:
                    raise ValidationError("registry inventory contains a contradictory alias")
                aliases[name] = canonical

        directory = self._voice_profile_directory()
        files = sorted(directory.iterdir(), key=lambda path: path.name)
        if len(files) > MAX_VOICE_PROFILES:
            raise ValidationError("TemporaryAI voice profile inventory cannot exceed 64 files")
        exact: dict[str, dict[str, Any]] = {}
        unbound: list[dict[str, Any]] = []
        for listed in files:
            if listed.suffix.casefold() != ".json":
                raise ValidationError("TemporaryAI voice profile directory contains a non-JSON file")
            relative = listed.relative_to(self.project_root)
            path = _regular_file_below(self.project_root, relative)
            assert path is not None
            profile, digest = _read_json_attested(path)
            voice_id = safe_component(profile.get("voice_id"), field="existing voice_id")
            declared = _text(profile.get("candidate_id"))
            entry = {
                "voice_id": voice_id,
                "voice_profile_relative_path": relative.as_posix(),
                "voice_profile_sha256": digest,
                "voice_status": _status_text(profile.get("status")),
            }
            if not declared:
                explicit_authority = LEGACY_FILENAME_AUTHORITIES.get(listed.name)
                unbound.append(
                    {
                        "filename": listed.name,
                        "explicit_candidate_id_absent": True,
                        "resolution": (
                            "preserved_by_explicit_legacy_authority"
                            if explicit_authority is not None
                            else "needs_review_unmapped"
                        ),
                        "explicit_authority_candidate_id": explicit_authority,
                        **entry,
                    }
                )
                continue
            canonical = aliases.get(declared)
            if canonical is None:
                raise ValidationError("voice profile candidate_id is not an exact current registry identifier")
            if canonical in exact:
                raise ValidationError("multiple voice profiles claim the same current candidate")
            exact[canonical] = entry
        return exact, unbound

    def _read_explicit_profile(self, relative: Path) -> tuple[dict[str, Any], str]:
        path = _regular_file_below(self.project_root, relative)
        assert path is not None
        return _read_json_attested(path)

    def _kira_authority(self) -> dict[str, Any]:
        profile, profile_sha = self._read_explicit_profile(KIRA_PROFILE_PATH)
        route, route_sha = self._read_explicit_profile(KIRA_ROUTE_PATH)
        voice_id = safe_component(profile.get("voice_id"), field="Kira current voice_id")
        if route.get("approved_profile") != KIRA_PROFILE_PATH.as_posix():
            raise ValidationError("Kira route does not name the exact current voice profile")
        if route.get("approved_profile_sha256") != profile_sha:
            raise ValidationError("Kira route voice-profile digest is stale")
        policy = route.get("policy")
        if not isinstance(policy, Mapping):
            raise ValidationError("Kira route policy is missing")
        if (
            policy.get("generic_voice_fallback_allowed") is not False
            or policy.get("sapi_fallback_allowed") is not False
            or policy.get("unsealed_in_process_fallback_allowed") is not False
        ):
            raise ValidationError("Kira route no longer preserves its fail-closed fallback policy")
        return {
            "voice_id": voice_id,
            "voice_profile_relative_path": KIRA_PROFILE_PATH.as_posix(),
            "voice_profile_sha256": profile_sha,
            "route_relative_path": KIRA_ROUTE_PATH.as_posix(),
            "route_sha256": route_sha,
            "preferred_route": _text(policy.get("preferred_route")),
            "automatic_fallback_routes": list(policy.get("automatic_fallback_routes", [])),
            "policy": "current_route_and_rollback_preserved_subject_selection_required",
        }

    def _robert_authority(self) -> dict[str, Any]:
        profile, digest = self._read_explicit_profile(ROBERT_PROFILE_PATH)
        if profile.get("target_type") != "synthetic_robert_persistent_runtime":
            raise ValidationError("Robert voice profile target authority is not exact")
        return {
            "voice_id": safe_component(profile.get("voice_id"), field="Robert current voice_id"),
            "voice_profile_relative_path": ROBERT_PROFILE_PATH.as_posix(),
            "voice_profile_sha256": digest,
            "voice_status": _status_text(profile.get("status")),
            "policy": "authorized_self_voice_preserved",
        }

    def _holmes_baseline(self) -> dict[str, Any]:
        profile, digest = self._read_explicit_profile(HOLMES_PROFILE_PATH)
        authenticity = profile.get("authenticity")
        if (
            profile.get("status") != "estimated_reconstruction_only"
            or not isinstance(authenticity, Mapping)
            or authenticity.get("authentic_voice_claim_allowed") is not False
        ):
            raise ValidationError("H. H. Holmes baseline lost its speculative-only boundary")
        return {
            "voice_id": safe_component(profile.get("voice_id"), field="Holmes baseline voice_id"),
            "voice_profile_relative_path": HOLMES_PROFILE_PATH.as_posix(),
            "voice_profile_sha256": digest,
            "voice_status": "estimated_reconstruction_only",
            "policy": "legacy_generic_baseline_preserved_not_an_authentic_voice",
        }

    def _creator_attestation(
        self,
        item: Mapping[str, Any],
        adapted: Mapping[str, Any],
    ) -> dict[str, Any]:
        names = _exact_candidate_names(item)
        creation_relative = Path(item["creation_request_relative_path"])
        creation_path = _regular_file_below(self.project_root, creation_relative)
        assert creation_path is not None
        creation, creation_sha = _read_json_attested(creation_path)
        if _text(creation.get("candidate_id")) not in names:
            raise ValidationError("creation request candidate_id is not an exact registry identifier")

        request_relative = Path(item["voice_discovery_request_relative_path"])
        request_path = _regular_file_below(self.project_root, request_relative)
        assert request_path is not None
        request, request_sha = _read_json_attested(request_path)
        if request_sha != adapted["source_hashes"]["request_sha256"]:
            raise ValidationError("voice discovery request changed after profile adaptation")
        if _text(request.get("candidate_id")) not in names:
            raise ValidationError("voice discovery request candidate_id is not an exact registry identifier")

        static_statuses = {
            _text(creation.get("status")),
            _text(request.get("status")),
            _text((creation.get("voice_plan") or {}).get("status"))
            if isinstance(creation.get("voice_plan"), Mapping)
            else "",
        }
        if any("NO_VOICE_WORK_AUTHORIZED" in value or "STATIC_QUALITY_V2" in value for value in static_statuses):
            raise ValidationError("creator source explicitly forbids voice audition work")

        activation_relative = creation_relative.parent / "activation_plan.json"
        activation_path = _regular_file_below(self.project_root, activation_relative, required=False)
        activation: dict[str, Any] | None = None
        activation_sha: str | None = None
        if activation_path is not None:
            activation, activation_sha = _read_json_attested(activation_path)
            if _text(activation.get("candidate_id")) not in names:
                raise ValidationError("activation plan candidate_id is not an exact registry identifier")

        return {
            "creation_request_relative_path": creation_relative.as_posix(),
            "creation_request_sha256": creation_sha,
            "creation_status": _text(creation.get("status")) or "unlabeled",
            "voice_discovery_request_relative_path": request_relative.as_posix(),
            "voice_discovery_request_sha256": request_sha,
            "voice_discovery_status": _text(request.get("status")) or "unlabeled",
            "activation_plan_relative_path": activation_relative.as_posix() if activation_path else None,
            "activation_plan_sha256": activation_sha,
            "activation_status": _text(activation.get("status")) if activation else "not_present",
        }

    @staticmethod
    def _base_item(item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "canonical_candidate_id": item["canonical_candidate_id"],
            "storage_id": item["storage_id"],
            "subject_id": item["subject_id"],
            "identity_class": item["identity_class"],
            "source_presence": {
                "profile": item["profile_present"],
                "voice_discovery_request": item["voice_discovery_request_present"],
                "creation_request": item["creation_request_present"],
            },
            "mutation_performed": False,
            "voice_binding_created": False,
            "temporary_ai_activation_allowed": False,
        }

    @staticmethod
    def _preserved_item(item: Mapping[str, Any], authority: Mapping[str, Any], *, action: str) -> dict[str, Any]:
        result = AvatarTemporaryCreatorVoiceIntegration._base_item(item)
        result.update(
            {
                "action": action,
                "existing_voice": dict(authority),
                "audition_brief": None,
                "review_gates": {
                    "human_audition_required": False,
                    "owner_approval_can_activate": False,
                    "subject_comparative_selection_required": action == "preserve_current_kira_route",
                },
                "review_blockers": [],
            }
        )
        return result

    def build_plan(
        self,
        *,
        audition_locale: str = "en-US",
        candidate_count: int = 3,
    ) -> dict[str, Any]:
        """Enumerate exact live candidates and create audition briefs only."""

        if not isinstance(audition_locale, str) or not _BCP47.fullmatch(audition_locale):
            raise ValidationError("audition_locale must be an explicit BCP-47-like tag")
        if not isinstance(candidate_count, int) or isinstance(candidate_count, bool) or not 2 <= candidate_count <= 5:
            raise ValidationError("candidate_count must be an integer between 2 and 5")
        self._assert_root()
        inventory = self.adapter.registered_candidates(inventory_scope=INVENTORY_SCOPE)
        source_authority = self.adapter.source_authority()
        exact_profiles, unbound_profiles = self._exact_voice_profiles(inventory)
        inventory_ids = {item["canonical_candidate_id"] for item in inventory}
        kira_authority = self._kira_authority() if KIRA_CANDIDATE_ID in inventory_ids else None
        robert_authority = self._robert_authority() if ROBERT_CANDIDATE_ID in inventory_ids else None
        holmes_baseline = self._holmes_baseline() if HOLMES_CANDIDATE_ID in inventory_ids else None

        candidates: list[dict[str, Any]] = []
        for item in inventory:
            candidate_id = item["canonical_candidate_id"]
            if candidate_id == KIRA_CANDIDATE_ID:
                assert kira_authority is not None
                candidates.append(
                    self._preserved_item(item, kira_authority, action="preserve_current_kira_route")
                )
                continue
            if candidate_id == ROBERT_CANDIDATE_ID:
                assert robert_authority is not None
                candidates.append(
                    self._preserved_item(item, robert_authority, action="preserve_authorized_self_voice")
                )
                continue
            if candidate_id in exact_profiles:
                candidates.append(
                    self._preserved_item(
                        item,
                        exact_profiles[candidate_id],
                        action="preserve_existing_voice_profile",
                    )
                )
                continue

            missing = [
                label
                for label, present in (
                    ("temporary_ai_profile", item["profile_present"]),
                    ("voice_discovery_request", item["voice_discovery_request_present"]),
                    ("creation_request", item["creation_request_present"]),
                )
                if not present
            ]
            if missing:
                result = self._base_item(item)
                result.update(
                    {
                        "action": "needs_review_source_records_missing",
                        "existing_voice": None,
                        "audition_brief": None,
                        "review_gates": {
                            "human_audition_required": False,
                            "owner_approval_can_activate": False,
                            "subject_comparative_selection_required": False,
                        },
                        "review_blockers": missing,
                    }
                )
                candidates.append(result)
                continue

            adapted = self.adapter.adapt(
                candidate_id,
                assignment_mode=AssignmentMode.ASSIGN_IF_MISSING,
                candidate_count=candidate_count,
                audition_locale=audition_locale,
            )
            result = self._base_item(item)
            if adapted["brief"] is None:
                result.update(
                    {
                        "action": "needs_review_voice_profile_fields",
                        "existing_voice": holmes_baseline if candidate_id == HOLMES_CANDIDATE_ID else None,
                        "audition_brief": None,
                        "review_gates": {
                            "human_audition_required": False,
                            "owner_approval_can_activate": False,
                            "subject_comparative_selection_required": False,
                        },
                        "review_blockers": sorted(
                            set(adapted["missing_required_fields"] + adapted["conflicts"])
                        ),
                        "adapter_status": adapted["status"],
                    }
                )
                candidates.append(result)
                continue

            brief = VoiceDesignBrief.from_dict(adapted["brief"])
            creator_attestation = self._creator_attestation(item, adapted)
            is_holmes = candidate_id == HOLMES_CANDIDATE_ID
            if is_holmes and holmes_baseline is None:
                raise ValidationError("H. H. Holmes exact legacy baseline authority is missing")
            result.update(
                {
                    "action": (
                        "prepare_nonbinding_speculative_historical_audition_brief"
                        if is_holmes
                        else "prepare_nonbinding_audition_brief"
                    ),
                    "existing_voice": holmes_baseline if is_holmes else None,
                    "audition_brief": brief.to_dict(),
                    "creator_source_attestation": creator_attestation,
                    "adapter_status": adapted["status"],
                    "binding_status": adapted["binding_status"],
                    "fit_limitations": adapted["fit_limitations"],
                    "required_disclosure": HISTORICAL_DISCLOSURE if is_holmes else None,
                    "review_gates": {
                        "human_audition_required": True,
                        "provenance_review_required": True,
                        "distinctness_review_required": True,
                        "exact_candidate_shared_spec_hash_required": True,
                        "source_locale_confirmation_required_before_binding": (
                            brief.language_provenance.value == "application_audition_default"
                        ),
                        "owner_approval_can_activate": False,
                        "subject_comparative_selection_required": False,
                    },
                    "review_blockers": adapted["missing_required_fields"],
                }
            )
            candidates.append(result)

        audition_actions = {
            "prepare_nonbinding_audition_brief",
            "prepare_nonbinding_speculative_historical_audition_brief",
        }
        preserved_actions = {
            "preserve_current_kira_route",
            "preserve_authorized_self_voice",
            "preserve_existing_voice_profile",
        }
        plan = {
            "schema": INTEGRATION_SCHEMA,
            "inventory_scope": INVENTORY_SCOPE,
            "source_authority": source_authority,
            "audition_locale": {
                "value": audition_locale,
                "provenance": "application_audition_default",
                "written_to_source_profiles": False,
                "sufficient_for_binding": False,
            },
            "candidates": candidates,
            "unbound_legacy_voice_profiles": unbound_profiles,
            "summary": {
                "registered_candidate_count": len(candidates),
                "source_profile_present_count": sum(
                    item["source_presence"]["profile"] for item in candidates
                ),
                "preserved_voice_or_route_count": sum(
                    item["action"] in preserved_actions for item in candidates
                ),
                "nonbinding_audition_brief_count": sum(
                    item["action"] in audition_actions for item in candidates
                ),
                "needs_review_count": sum(item["action"].startswith("needs_review") for item in candidates),
                "binding_ready_count": 0,
                "activation_allowed_count": 0,
            },
            "selection_policy": {
                "generated_or_historical_candidate_human_audition_required": True,
                "kira_and_lisa_owner_approval_only_makes_candidates_eligible": True,
                "kira_and_lisa_subject_comparative_selection_required": True,
                "kira_current_route_remains_rollback_until_kira_selects": True,
                "peter_and_marinette_existing_voices_remain_unchanged": True,
            },
            "integration_boundary": {
                "source_profiles_modified": False,
                "voice_profiles_overwritten": False,
                "audition_audio_generated": False,
                "voice_binding_created": False,
                "runtime_route_changed": False,
                "temporary_ai_activated": False,
                "shared_person_spec_promotion_claimed": False,
                "next_stage": "immutable audition bundles and audio only after runtime evidence and human review",
            },
        }
        if any(item["mutation_performed"] for item in candidates):
            raise ValidationError("integration plan unexpectedly reports a source mutation")
        if plan["summary"]["registered_candidate_count"] > 32:
            raise ValidationError("integration plan exceeded its 32-candidate bound")
        return plan


def build_live_avatar_voice_plan(
    project_root: Path,
    *,
    audition_locale: str = "en-US",
    candidate_count: int = 3,
) -> dict[str, Any]:
    """Convenience entrypoint for the current KiraWorld project tree."""

    return AvatarTemporaryCreatorVoiceIntegration(project_root).build_plan(
        audition_locale=audition_locale,
        candidate_count=candidate_count,
    )
