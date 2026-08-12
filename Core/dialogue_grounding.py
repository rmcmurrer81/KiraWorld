"""Role-scoped grounding for Kira/Robert meetings.

Kira may see her own approved memories.  The Robert variant may see Robert's
private source pack.  Neither role receives the other role's private source.
Only separately reviewed, public dialogue-continuity summaries are shared.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from Core.dialogue_privacy import (
    DialoguePrivacyError,
    canonical_json_sha256,
    contains_private_marker,
    parse_structured_response,
    prepare_dialogue_speech_turns,
)


CONTINUITY_APPROVAL_REGISTRY_RELATIVE_PATH = Path(
    "Data/dialogues/kira_robert_intro/policies/continuity_approval_registry.json"
)
CONTINUITY_APPROVAL_REGISTRY_SHA256 = (
    "0cbdd0050b2a9c6018d756a9aff8c678b66810b8fca271285511317537691a3d"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_continuity_approval_registry(project_root: Path) -> dict[str, Any]:
    """Load the independently pinned owner registry; any ambiguity denies all."""

    path = project_root / CONTINUITY_APPROVAL_REGISTRY_RELATIVE_PATH
    failures: list[str] = []
    data: Any = None
    digest: str | None = None
    try:
        if not path.is_file():
            failures.append("registry_missing")
        elif path.stat().st_size > 1024 * 1024:
            failures.append("registry_too_large")
        else:
            digest = _sha(path)
            if digest != CONTINUITY_APPROVAL_REGISTRY_SHA256:
                failures.append("registry_code_pinned_hash_mismatch")
            data = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError):
        failures.append("registry_unreadable_or_invalid_json")

    entries: list[dict[str, str]] = []
    if not isinstance(data, dict):
        if data is not None:
            failures.append("registry_root_is_not_object")
    else:
        expected_policy = {
            "default": "deny",
            "require_exact_approval_artifact_sha256": True,
            "require_continuity_source_summary_bindings": True,
        }
        if data.get("schema_version") != 1:
            failures.append("registry_schema_version_invalid")
        if data.get("registry_type") != "owner_controlled_dialogue_continuity_approval_registry":
            failures.append("registry_type_invalid")
        if data.get("owner_id") != "robert_mcmurrer":
            failures.append("registry_owner_invalid")
        if data.get("status") != "active":
            failures.append("registry_status_invalid")
        if data.get("policy") != expected_policy:
            failures.append("registry_policy_invalid")
        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list):
            failures.append("registry_entries_missing")
        else:
            seen_approvals: set[str] = set()
            required_hashes = (
                "approval_artifact_sha256",
                "continuity_file_sha256",
                "source_dialogue_sha256",
                "public_summary_sha256",
            )
            for index, raw_entry in enumerate(raw_entries):
                if not isinstance(raw_entry, dict) or raw_entry.get("status") != "approved":
                    failures.append(f"registry_entry_{index}_invalid")
                    continue
                entry = {name: str(raw_entry.get(name) or "").lower() for name in required_hashes}
                if any(not _SHA256_RE.fullmatch(entry[name]) for name in required_hashes):
                    failures.append(f"registry_entry_{index}_hash_invalid")
                    continue
                if entry["approval_artifact_sha256"] in seen_approvals:
                    failures.append("registry_duplicate_approval_artifact")
                    continue
                seen_approvals.add(entry["approval_artifact_sha256"])
                entries.append({"status": "approved", **entry})
    return {
        "valid": not failures,
        "path": str(CONTINUITY_APPROVAL_REGISTRY_RELATIVE_PATH),
        "sha256": digest,
        "pinned_sha256": CONTINUITY_APPROVAL_REGISTRY_SHA256,
        "default": "deny",
        "entries": entries if not failures else [],
        "failures": failures,
    }


def _importance_score(item: dict[str, Any]) -> float:
    importance = item.get("importance")
    if isinstance(importance, dict):
        try:
            return float(importance.get("score") or 0)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def load_kira_private_grounding(project_root: Path, limit: int = 8) -> tuple[str, dict[str, Any]]:
    path = project_root / "Data" / "memories_kira.json"
    values = _read_json(path) if path.exists() else []
    approved = [
        item
        for item in values
        if isinstance(item, dict)
        and str(item.get("owner") or "").lower() == "kira"
        and str(item.get("status") or "").lower() == "approved"
    ]
    approved.sort(key=_importance_score, reverse=True)
    selected = approved[: max(0, limit)]
    lines = [
        "These are Kira's own approved memory records. They are visible only in Kira's role prompt.",
        "Recall them with their stored qualifications; do not convert generated or reading history into physical lived events.",
    ]
    for item in selected:
        summary = str(item.get("summary") or item.get("details", {}).get("safe_recall") or "").strip()
        if summary:
            lines.append(f"- {summary}")
        forbidden = item.get("forbidden_inferences") or []
        if forbidden:
            lines.append(f"  Guard: {str(forbidden[0]).strip()}")
    audit = {
        "path": str(path.relative_to(project_root)),
        "sha256": _sha(path) if path.exists() else None,
        "approved_count": len(approved),
        "selected_count": len(selected),
        "visibility": "kira_only",
    }
    return "\n".join(lines), audit


def load_robert_private_grounding(project_root: Path) -> tuple[str, dict[str, Any]]:
    path = project_root / "Data" / "identity" / "robert_mcmurrer" / "robert_source_memory_20260715.json"
    data = _read_json(path) if path.exists() else {}
    identity = data.get("canonical_identity") or {}
    firewall = data.get("hard_false_memory_firewall") or []
    lines = [
        "This is private Robert-source grounding visible only in the Robert role prompt.",
        "Inherited human-Robert facts are source material, not the synthetic Robert's own lived history.",
    ]
    for key, value in identity.items():
        lines.append(f"- {key}: {value}")
    for rule in firewall:
        lines.append(f"- Firewall: {rule}")
    for era in (data.get("timeline") or []):
        anchors = era.get("anchors") or []
        if anchors:
            lines.append(f"- Human-Robert source era {era.get('era')}: {anchors[0]}")
    audit = {
        "path": str(path.relative_to(project_root)),
        "sha256": _sha(path) if path.exists() else None,
        "visibility": "robert_variant_only",
        "loaded": bool(data),
    }
    return "\n".join(lines), audit


def load_recent_role_private_dialogue(
    project_root: Path,
    owner: str,
    *,
    max_entries: int = 4,
    approved_public_exports: tuple[str, ...] = (),
) -> tuple[str, dict[str, Any]]:
    """Load a validated tail of one role's own private dialogue sidecar.

    These notes are subjective, unpromoted continuity rather than durable
    memory or runtime truth.  Only PRIVATE_MIND/TRUTH_FLAGS are returned; raw
    responses never enter the next prompt.
    """

    normalized_owner = str(owner or "").strip().lower()
    if normalized_owner not in {"kira", "robert"}:
        raise ValueError("owner must be kira or robert")
    folder = project_root / "Data" / "dialogues" / "kira_robert_intro" / "private" / normalized_owner
    candidates = (
        sorted(folder.glob("*.private.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if folder.exists()
        else []
    )
    rejected: list[dict[str, str]] = []
    for path in candidates:
        try:
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("sidecar_too_large")
            data = _read_json(path)
            entries = data.get("entries") if isinstance(data, dict) else None
            if (
                data.get("schema_version") != 1
                or data.get("owner_scope") != normalized_owner
                or data.get("other_dialogue_role_access_allowed") is not False
                or data.get("tts_allowed") is not False
                or data.get("public_export_allowed") is not False
                or not isinstance(entries, list)
                or data.get("private_payload_sha256") != canonical_json_sha256(entries)
            ):
                raise ValueError("sidecar_policy_or_payload_binding_invalid")
            validated: list[dict[str, str]] = []
            for entry in entries:
                if not isinstance(entry, dict) or str(entry.get("speaker") or "").lower() != normalized_owner:
                    raise ValueError("cross_role_or_invalid_private_entry")
                private_mind = str(entry.get("private_mind") or "")
                truth_flags = str(entry.get("truth_flags") or "")
                raw = str(entry.get("raw") or "")
                if (
                    entry.get("private_mind_sha256")
                    != hashlib.sha256(private_mind.encode("utf-8")).hexdigest()
                    or entry.get("truth_flags_sha256")
                    != hashlib.sha256(truth_flags.encode("utf-8")).hexdigest()
                    or entry.get("raw_sha256")
                    != hashlib.sha256(raw.encode("utf-8")).hexdigest()
                ):
                    raise ValueError("private_entry_field_hash_mismatch")
                without_record_hash = dict(entry)
                record_hash = without_record_hash.pop("private_record_sha256", None)
                if record_hash != canonical_json_sha256(without_record_hash):
                    raise ValueError("private_entry_record_hash_mismatch")
                validated.append(
                    {
                        "private_mind": private_mind,
                        "truth_flags": truth_flags,
                    }
                )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            rejected.append({"path": str(path.relative_to(project_root)), "reason": str(exc)})
            continue

        selected = validated[-max(0, max_entries):] if max_entries > 0 else []
        lines = [
            "Recent owner-only dialogue notes follow. They are subjective, unpromoted context—not durable memory or runtime/world truth.",
        ]
        for item in selected:
            lines.append(f"- PRIVATE_MIND: {item['private_mind']}")
            lines.append(f"  TRUTH_FLAGS: {item['truth_flags']}")
        return "\n".join(lines), {
            "visibility": f"{normalized_owner}_only",
            "path": str(path.relative_to(project_root)),
            "sha256": _sha(path),
            "validated_entry_count": len(validated),
            "selected_entry_count": len(selected),
            "raw_loaded_into_prompt": False,
            "tts_allowed": False,
            "rejected_records": rejected,
        }
    # Legacy meetings stored both role-private fields in the source dialogue.
    # Recover only this owner's tail when an approved, privacy-checked public
    # export cryptographically points back to that exact immutable source.
    root_resolved = project_root.resolve()
    for export_value in approved_public_exports:
        try:
            export_path = (project_root / export_value).resolve()
            if not export_path.is_relative_to(root_resolved) or not export_path.is_file():
                raise ValueError("approved_public_export_missing_or_out_of_root")
            export = _read_json(export_path)
            if (
                export.get("status") != "prepared_privacy_safe_spoken_only"
                or export.get("private_channels_included") is not False
            ):
                raise ValueError("approved_public_export_policy_invalid")
            prepare_dialogue_speech_turns(export)
            source_value = str(export.get("source_dialogue") or "").strip()
            source_path = Path(source_value)
            if not source_path.is_absolute():
                source_path = project_root / source_path
            source_path = source_path.resolve()
            if not source_path.is_relative_to(root_resolved) or not source_path.is_file():
                raise ValueError("legacy_private_source_missing_or_out_of_root")
            if export.get("source_dialogue_sha256") != _sha(source_path):
                raise ValueError("legacy_private_source_hash_mismatch")
            source = _read_json(source_path)
            recovered: list[dict[str, str]] = []
            for item in source.get("transcript") or []:
                if not isinstance(item, dict) or str(item.get("speaker") or "").lower() != normalized_owner:
                    continue
                parsed = parse_structured_response(str(item.get("raw") or ""))
                private_mind = str(parsed.get("private_mind") or item.get("private_mind") or "").strip()
                truth_flags = str(parsed.get("truth_flags") or item.get("truth_flags") or "").strip()
                if private_mind or truth_flags:
                    recovered.append(
                        {"private_mind": private_mind, "truth_flags": truth_flags}
                    )
            selected = recovered[-max(0, max_entries):] if max_entries > 0 else []
            if not selected:
                raise ValueError("no_owner_private_entries_recovered")
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            DialoguePrivacyError,
            ValueError,
        ) as exc:
            rejected.append({"path": str(export_value), "reason": str(exc)})
            continue
        lines = [
            "Recent owner-only dialogue notes recovered from an approved public-export source follow. They are subjective, unpromoted context—not durable memory or runtime/world truth.",
        ]
        for item in selected:
            lines.append(f"- PRIVATE_MIND: {item['private_mind']}")
            lines.append(f"  TRUTH_FLAGS: {item['truth_flags']}")
        return "\n".join(lines), {
            "visibility": f"{normalized_owner}_only",
            "path": str(source_path.relative_to(project_root)),
            "sha256": _sha(source_path),
            "approved_public_export": str(export_path.relative_to(project_root)),
            "approved_public_export_sha256": _sha(export_path),
            "validated_entry_count": len(recovered),
            "selected_entry_count": len(selected),
            "raw_loaded_into_prompt": False,
            "tts_allowed": False,
            "storage_mode": "legacy_source_recovery_through_approved_spoken_only_export_binding",
            "rejected_records": rejected,
        }

    return "", {
        "visibility": f"{normalized_owner}_only",
        "path": None,
        "validated_entry_count": 0,
        "selected_entry_count": 0,
        "raw_loaded_into_prompt": False,
        "tts_allowed": False,
        "rejected_records": rejected,
    }


def load_approved_shared_continuity(project_root: Path, limit: int = 3) -> tuple[str, dict[str, Any]]:
    folder = project_root / "Data" / "dialogues" / "kira_robert_intro" / "continuity"
    paths = sorted(folder.glob("*.approved.json"), key=lambda path: path.stat().st_mtime, reverse=True) if folder.exists() else []
    lines: list[str] = []
    records: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    accepted: list[tuple[Path, dict[str, Any], Path]] = []
    root_resolved = project_root.resolve()
    approval_registry = load_continuity_approval_registry(project_root)
    for path in paths:
        if len(accepted) >= max(0, limit):
            break
        try:
            data = _read_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            rejected.append({"path": str(path), "reason": f"invalid_json:{exc}"})
            continue
        if data.get("status") != "approved_shared_continuity":
            rejected.append({"path": str(path.relative_to(project_root)), "reason": "wrong_status"})
            continue
        summary = str(data.get("public_summary") or "").strip()
        summary_sha = hashlib.sha256(summary.encode("utf-8")).hexdigest()
        if not summary or contains_private_marker(summary):
            rejected.append({"path": str(path.relative_to(project_root)), "reason": "empty_or_private_marker_in_summary"})
            continue
        if data.get("public_summary_sha256") != summary_sha:
            rejected.append({"path": str(path.relative_to(project_root)), "reason": "public_summary_hash_mismatch"})
            continue

        source_value = str(data.get("source_dialogue") or "").strip()
        approval_value = str(data.get("approval_artifact") or "").strip()
        source_path = (project_root / source_value).resolve() if source_value else None
        approval_path = (project_root / approval_value).resolve() if approval_value else None
        if (
            source_path is None
            or approval_path is None
            or not source_path.is_relative_to(root_resolved)
            or not approval_path.is_relative_to(root_resolved)
            or not source_path.is_file()
            or not approval_path.is_file()
        ):
            rejected.append({"path": str(path.relative_to(project_root)), "reason": "missing_or_out_of_root_source_or_approval_artifact"})
            continue
        source_sha = _sha(source_path)
        if data.get("source_dialogue_sha256") != source_sha:
            rejected.append({"path": str(path.relative_to(project_root)), "reason": "source_dialogue_hash_mismatch"})
            continue
        try:
            approval = _read_json(approval_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            rejected.append({"path": str(path.relative_to(project_root)), "reason": f"invalid_approval_artifact:{exc}"})
            continue
        approval_ok = (
            approval.get("status") == "approved"
            and approval.get("reviewer_id") == "robert_mcmurrer"
            and approval.get("continuity_file_sha256") == _sha(path)
            and approval.get("public_summary_sha256") == summary_sha
            and approval.get("source_dialogue_sha256") == source_sha
        )
        if not approval_ok:
            rejected.append({"path": str(path.relative_to(project_root)), "reason": "approval_artifact_binding_failed"})
            continue
        approval_sha = _sha(approval_path)
        registry_match = any(
            entry.get("approval_artifact_sha256") == approval_sha
            and entry.get("continuity_file_sha256") == _sha(path)
            and entry.get("public_summary_sha256") == summary_sha
            and entry.get("source_dialogue_sha256") == source_sha
            for entry in approval_registry["entries"]
        ) if approval_registry["valid"] else False
        if not registry_match:
            reason = (
                "owner_approval_registry_invalid"
                if not approval_registry["valid"]
                else "approval_not_listed_in_owner_registry"
            )
            rejected.append({"path": str(path.relative_to(project_root)), "reason": reason})
            continue
        accepted.append((path, data, approval_path))

    for path, data, approval_path in reversed(accepted):
        summary = str(data["public_summary"]).strip()
        lines.append(f"- {summary}")
        records.append(
            {
                "path": str(path.relative_to(project_root)),
                "sha256": _sha(path),
                "approval_artifact": str(approval_path.relative_to(project_root)),
                "approval_artifact_sha256": _sha(approval_path),
                "source_dialogue": str(source_path.relative_to(project_root)),
                "source_dialogue_sha256": _sha(source_path),
            }
        )
    if not lines:
        lines = [
            "No reviewed shared Kira/Robert continuity is available. Do not claim either person remembers a prior meeting."
        ]
    return "\n".join(lines), {
        "visibility": "shared_public_summary_only",
        "approved_records": records,
        "approved_count": len(records),
        "rejected_records": rejected,
        "rejected_count": len(rejected),
        "owner_approval_registry": {
            key: approval_registry[key]
            for key in ("valid", "path", "sha256", "pinned_sha256", "default", "failures")
        },
        "approval_rule": "separate approval artifact must bind continuity, public summary, and source dialogue hashes and its exact hash must be listed in the code-pinned owner registry",
    }


def load_dialogue_grounding(project_root: Path) -> dict[str, Any]:
    kira_text, kira_audit = load_kira_private_grounding(project_root)
    robert_text, robert_audit = load_robert_private_grounding(project_root)
    shared_text, shared_audit = load_approved_shared_continuity(project_root)
    approved_public_exports = tuple(
        str(item.get("source_dialogue") or "")
        for item in shared_audit.get("approved_records") or []
        if item.get("source_dialogue")
    )
    kira_dialogue_text, kira_dialogue_audit = load_recent_role_private_dialogue(
        project_root, "kira", approved_public_exports=approved_public_exports
    )
    robert_dialogue_text, robert_dialogue_audit = load_recent_role_private_dialogue(
        project_root, "robert", approved_public_exports=approved_public_exports
    )
    return {
        "role_text": {
            "Kira": "\n\n".join(value for value in (kira_text, kira_dialogue_text) if value),
            "Robert": "\n\n".join(value for value in (robert_text, robert_dialogue_text) if value),
        },
        "shared_text": shared_text,
        "audit": {
            "kira_private": kira_audit,
            "robert_private": robert_audit,
            "kira_private_dialogue_continuity": kira_dialogue_audit,
            "robert_private_dialogue_continuity": robert_dialogue_audit,
            "shared_continuity": shared_audit,
            "cross_role_private_sharing": False,
        },
    }
