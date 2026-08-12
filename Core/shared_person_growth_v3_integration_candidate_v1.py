"""Default-off integration candidate for accepted-static Shared Growth V3.

This module projects only public, maturity-compatible metadata from one exact
V3 profile.  It never serializes private roots or records, never opens a live
person session, and never changes a production pointer.  Existing routes are
closed by the hash-pinned inventory.  New Temporary Creator profiles use a
separate collision-checked lane and remain inactive.

The migration surface is deliberately explicit: an exact adapter-owned
identity plus a high-entropy secret issues a one-use receipt, an append-only
CAS-like file ledger records issue/commit/rollback, and an exclusive staged
output is exposed only after exact-byte readback and ledger commit.  This is a
static integration candidate, not production enablement.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from Core.shared_person_growth_capabilities_v3 import (
    ControllerIdentityHandle,
    GrowthAuthorityError,
    GrowthCapabilityError,
    GrowthReplayError,
    ProtectedGrowthController,
    validate_capability_profile,
)
from tools.create_temporary_ai_growth_profile_v3 import validate_creator_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = (
    PROJECT_ROOT
    / "Data"
    / "foundation"
    / "shared_person_growth_v3_integration_candidate_v1.json"
)
INVENTORY_SCHEMA = "kira.shared_person_growth_v3_integration_inventory.v1"
PUBLIC_ATTACHMENT_SCHEMA = "kira.shared_person_growth_v3_public_attachment.v1"
LEDGER_RECORD_SCHEMA = "kira.shared_person_growth_v3_integration_ledger_record.v1"
RECEIPT_SCHEMA = "kira.shared_person_growth_v3_integration_receipt.v1"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,127}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_LEDGER_NAME_RE = re.compile(r"^[0-9]{8}\.json$")
_HANDLE_KEY = object()


class GrowthIntegrationError(GrowthCapabilityError):
    """Closed-boundary failure in the static integration candidate."""


class GrowthIntegrationAuthorityError(GrowthAuthorityError):
    """Exact adapter authority is absent or cross-bound."""


class GrowthIntegrationRecoveryRequired(GrowthIntegrationError):
    """A durable ledger tail is ambiguous and the adapter fails closed."""


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_mapping(value: Mapping[str, Any]) -> str:
    return _sha_bytes(_canonical_bytes(value))


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GrowthIntegrationError(f"duplicate JSON key rejected: {key}")
        result[key] = value
    return result


def _exact_keys(value: Any, keys: set[str], field: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise GrowthIntegrationError(f"{field} exact schema mismatch")
    if any(type(key) is not str for key in value):
        raise GrowthIntegrationError(f"{field} contains a non-string key")
    return value


def _identifier(value: Any, field: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise GrowthIntegrationError(f"{field} must be a canonical identifier")
    return value


def _text(value: Any, field: str, maximum: int = 512) -> str:
    if type(value) is not str or not value.strip():
        raise GrowthIntegrationError(f"{field} must be nonempty text")
    result = value.strip()
    if len(result.encode("utf-8")) > maximum:
        raise GrowthIntegrationError(f"{field} exceeds {maximum} UTF-8 bytes")
    return result


def _sha(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or _SHA_RE.fullmatch(value) is None or value == "0" * 64:
        raise GrowthIntegrationError(f"{field} must be nonzero lowercase SHA-256")
    return value


def _relative_path(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    text = _text(value, field, 512).replace("\\", "/")
    path = Path(text)
    if path.is_absolute() or ".." in path.parts or text.startswith("/"):
        raise GrowthIntegrationError(f"{field} must stay project-relative")
    if path.as_posix() != text:
        raise GrowthIntegrationError(f"{field} is not canonical POSIX-relative")
    return text


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(right) is dict:
        return set(left) == set(right) and all(
            _typed_equal(left[key], right[key]) for key in right
        )
    if type(right) is list:
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def inventory_sha256(path: Path = INVENTORY_PATH) -> str:
    return _sha_bytes(path.read_bytes())


_GROWTH_KEYS = {
    "policy_path",
    "policy_sha256",
    "core_path",
    "core_sha256",
    "creator_path",
    "creator_sha256",
    "fresh_audit_checkpoint_path",
    "fresh_audit_checkpoint_sha256",
    "fresh_audit_verdict",
}
_DISCOVERY_KEYS = {"path", "sha256", "purpose"}
_MATURITY_SOURCE_KEYS = {
    "source_id",
    "path",
    "sha256",
    "permitted_status",
    "requires_new_v3_receipt",
}
_PERSON_KEYS = {
    "person_id",
    "candidate_id",
    "display_name",
    "required_maturity",
    "maturity_source_id",
    "person_class",
}
_ROUTE_KEYS = {
    "route_id",
    "route_kind",
    "person_id",
    "candidate_id",
    "source_path",
    "source_sha256",
    "disposition",
}
_CREATOR_KEYS = {
    "route_id",
    "existing_candidate_collision_rejected",
    "default_maturity",
    "classified_creation_requires_exact_v3_maturity_receipt",
    "private_payload_copy_allowed",
    "private_root_copy_allowed",
    "live_activation_allowed",
}
_INTEGRATION_TRUTH = {
    "default_off": True,
    "production_pointer_changed": False,
    "public_projection_only": True,
    "private_state_roots_exposed": False,
    "private_memory_or_emotion_payload_exposed": False,
    "automatic_lived_memory_created": False,
    "automatic_emotion_created": False,
    "automatic_external_action_created": False,
    "bounded_initiative_stage": "DESIGN_ONLY",
    "bounded_initiative_live_enabled": False,
    "different_fresh_audit_required_before_promotion": True,
}


def _verify_bound_file(project_root: Path, path_value: str, sha_value: str) -> None:
    path = (project_root / path_value).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError as exc:
        raise GrowthIntegrationError("bound source escaped the project") from exc
    if not path.is_file() or path.is_symlink():
        raise GrowthIntegrationError(f"bound source is absent or a symlink: {path_value}")
    if _sha_bytes(path.read_bytes()) != sha_value:
        raise GrowthIntegrationError(f"bound source hash drifted: {path_value}")


def load_integration_inventory(
    path: Path = INVENTORY_PATH,
    *,
    project_root: Path = PROJECT_ROOT,
    verify_current_routes: bool = True,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=_strict_object)
    except GrowthIntegrationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GrowthIntegrationError("integration inventory is not strict UTF-8 JSON") from exc
    top = _exact_keys(
        value,
        {
            "schema",
            "status",
            "owner_authorization_date",
            "growth_v3_binding",
            "discovery_sources",
            "maturity_sources",
            "people",
            "routes",
            "creator_lane",
            "integration_truth",
        },
        "integration_inventory",
    )
    if top["schema"] != INVENTORY_SCHEMA:
        raise GrowthIntegrationError("integration inventory schema mismatch")
    if top["status"] != "STATIC_INTEGRATION_CANDIDATE_DEFAULT_OFF_PENDING_DIFFERENT_AUDIT":
        raise GrowthIntegrationError("integration inventory status drifted")
    if top["owner_authorization_date"] != "2026-08-11":
        raise GrowthIntegrationError("integration inventory authorization date drifted")

    growth = _exact_keys(top["growth_v3_binding"], _GROWTH_KEYS, "growth_v3_binding")
    for field in ("policy_path", "core_path", "creator_path", "fresh_audit_checkpoint_path"):
        _relative_path(growth[field], field)
    for field in (
        "policy_sha256",
        "core_sha256",
        "creator_sha256",
        "fresh_audit_checkpoint_sha256",
    ):
        _sha(growth[field], field)
    if growth["fresh_audit_verdict"] != "ACCEPT_STATIC_ONLY":
        raise GrowthIntegrationError("Growth V3 did not retain its static-only verdict")
    for pfield, hfield in (
        ("policy_path", "policy_sha256"),
        ("core_path", "core_sha256"),
        ("creator_path", "creator_sha256"),
        ("fresh_audit_checkpoint_path", "fresh_audit_checkpoint_sha256"),
    ):
        _verify_bound_file(project_root, growth[pfield], growth[hfield])

    if type(top["discovery_sources"]) is not list or not top["discovery_sources"]:
        raise GrowthIntegrationError("discovery_sources must be a nonempty list")
    discovery_paths: set[str] = set()
    for index, item in enumerate(top["discovery_sources"]):
        checked = _exact_keys(item, _DISCOVERY_KEYS, f"discovery_sources[{index}]")
        source_path = _relative_path(checked["path"], "discovery.path")
        source_sha = _sha(checked["sha256"], "discovery.sha256")
        _text(checked["purpose"], "discovery.purpose")
        if source_path in discovery_paths:
            raise GrowthIntegrationError("duplicate discovery source")
        discovery_paths.add(source_path)
        _verify_bound_file(project_root, source_path, source_sha)

    if type(top["maturity_sources"]) is not list or not top["maturity_sources"]:
        raise GrowthIntegrationError("maturity_sources must be a nonempty list")
    maturity_sources: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(top["maturity_sources"]):
        checked = _exact_keys(item, _MATURITY_SOURCE_KEYS, f"maturity_sources[{index}]")
        source_id = _identifier(checked["source_id"], "maturity_source.source_id")
        if source_id in maturity_sources:
            raise GrowthIntegrationError("duplicate maturity source ID")
        if checked["permitted_status"] not in {
            "unresolved",
            "confirmed_adult",
            "non_adult",
            "subject_specific",
        }:
            raise GrowthIntegrationError("unsupported maturity source status")
        if type(checked["requires_new_v3_receipt"]) is not bool:
            raise GrowthIntegrationError("maturity receipt truth must be exact bool")
        source_path = _relative_path(checked["path"], "maturity_source.path", nullable=True)
        source_sha = _sha(checked["sha256"], "maturity_source.sha256", nullable=True)
        if (source_path is None) != (source_sha is None):
            raise GrowthIntegrationError("maturity source path/hash nullability differs")
        if source_path is None:
            if source_id != "no_protected_source" or checked["permitted_status"] != "unresolved":
                raise GrowthIntegrationError("only the unresolved source may omit source bytes")
        else:
            _verify_bound_file(project_root, source_path, source_sha)
        maturity_sources[source_id] = checked

    if type(top["people"]) is not list or not top["people"]:
        raise GrowthIntegrationError("people must be a nonempty list")
    people: dict[str, Mapping[str, Any]] = {}
    candidates: set[str] = set()
    for index, item in enumerate(top["people"]):
        person = _exact_keys(item, _PERSON_KEYS, f"people[{index}]")
        person_id = _identifier(person["person_id"], "person_id")
        candidate_id = _identifier(person["candidate_id"], "candidate_id")
        _text(person["display_name"], "display_name", 256)
        _identifier(person["person_class"], "person_class")
        required = person["required_maturity"]
        if required not in {"confirmed_adult", "non_adult", "unresolved"}:
            raise GrowthIntegrationError("person required maturity is unsupported")
        source_id = _identifier(person["maturity_source_id"], "maturity_source_id")
        if source_id not in maturity_sources:
            raise GrowthIntegrationError("person maturity source is absent")
        source_status = maturity_sources[source_id]["permitted_status"]
        if source_status != "subject_specific" and source_status != required:
            raise GrowthIntegrationError("person maturity and source differ")
        if person_id in people or candidate_id in candidates:
            raise GrowthIntegrationError("person or candidate identity is duplicated")
        if person_id in {"robert", "biological_robert", "human_robert"}:
            raise GrowthIntegrationError("biological Robert is not a synthetic person route")
        people[person_id] = person
        candidates.add(candidate_id)

    if type(top["routes"]) is not list or not top["routes"]:
        raise GrowthIntegrationError("routes must be a nonempty list")
    routes: dict[str, Mapping[str, Any]] = {}
    covered_people: set[str] = set()
    profile_paths: set[str] = set()
    state_paths: set[str] = set()
    for index, item in enumerate(top["routes"]):
        route = _exact_keys(item, _ROUTE_KEYS, f"routes[{index}]")
        route_id = _identifier(route["route_id"], "route_id")
        _identifier(route["route_kind"], "route_kind")
        candidate_id = _identifier(route["candidate_id"], "route.candidate_id")
        source_path = _relative_path(route["source_path"], "route.source_path")
        source_sha = _sha(route["source_sha256"], "route.source_sha256")
        if route_id in routes:
            raise GrowthIntegrationError("duplicate route ID")
        if route["disposition"] == "applicable":
            person_id = _identifier(route["person_id"], "route.person_id")
            if person_id not in people:
                raise GrowthIntegrationError("applicable route person is absent")
            if people[person_id]["candidate_id"] != candidate_id:
                raise GrowthIntegrationError("applicable route is cross-bound")
            covered_people.add(person_id)
        elif route["disposition"] == "deny_alias_no_person_authority":
            if route["person_id"] is not None:
                raise GrowthIntegrationError("denied alias must have no person authority")
            if candidate_id in candidates:
                raise GrowthIntegrationError("denied alias collides with an authoritative candidate")
        else:
            raise GrowthIntegrationError("route disposition is unsupported")
        _verify_bound_file(project_root, source_path, source_sha)
        if route["route_kind"] != "permanent_selector":
            raw = json.loads(
                (project_root / source_path).read_bytes(),
                object_pairs_hook=_strict_object,
            )
            observed_candidate = raw.get("candidate_id")
            if observed_candidate != candidate_id:
                raise GrowthIntegrationError("route source candidate ID drifted")
        if source_path.startswith("TemporaryAI/candidates/"):
            profile_paths.add(source_path)
        if source_path.startswith("Avatar/state/temp_ai/"):
            state_paths.add(source_path)
        routes[route_id] = route
    if covered_people != set(people):
        raise GrowthIntegrationError("one or more current people lack an applicable route")
    if len(people) != 24 or len(routes) != 36 or len(maturity_sources) != 9:
        raise GrowthIntegrationError("closed current-person inventory cardinality drifted")
    permanent_ids = {
        route_id for route_id, route in routes.items() if route["route_kind"] == "permanent_selector"
    }
    if permanent_ids != {"permanent:kira", "permanent:lisa"}:
        raise GrowthIntegrationError("permanent person routes drifted")
    denied_routes = [
        route for route in routes.values() if route["disposition"] == "deny_alias_no_person_authority"
    ]
    if len(denied_routes) != 1 or denied_routes[0]["candidate_id"] != (
        "sarah_bennett_enterainment_pr_agent_expert_20260606_171637"
    ):
        raise GrowthIntegrationError("denied Sarah legacy alias boundary drifted")

    creator = _exact_keys(top["creator_lane"], _CREATOR_KEYS, "creator_lane")
    if creator["route_id"] != "creator:new_person" or creator["default_maturity"] != "unresolved":
        raise GrowthIntegrationError("creator route or default maturity drifted")
    expected_creator_truth = {
        "existing_candidate_collision_rejected": True,
        "classified_creation_requires_exact_v3_maturity_receipt": True,
        "private_payload_copy_allowed": False,
        "private_root_copy_allowed": False,
        "live_activation_allowed": False,
    }
    for field, expected in expected_creator_truth.items():
        if creator[field] is not expected:
            raise GrowthIntegrationError(f"creator boundary drifted: {field}")
    if not _typed_equal(top["integration_truth"], _INTEGRATION_TRUTH):
        raise GrowthIntegrationError("integration truth boundary drifted")

    if verify_current_routes:
        observed_profiles = {
            path.relative_to(project_root).as_posix()
            for path in (project_root / "TemporaryAI" / "candidates").glob(
                "*/temporary_ai_profile.json"
            )
            if path.is_file()
        }
        observed_states = {
            path.relative_to(project_root).as_posix()
            for path in (project_root / "Avatar" / "state" / "temp_ai").glob("*.json")
            if path.is_file()
        }
        if observed_profiles != profile_paths:
            raise GrowthIntegrationError("TemporaryAI profile coverage drifted")
        if observed_states != state_paths:
            raise GrowthIntegrationError("TemporaryAI state-route coverage drifted")
    return deepcopy(dict(top))


def current_route_coverage_inventory(
    *, inventory_path: Path = INVENTORY_PATH, project_root: Path = PROJECT_ROOT
) -> dict[str, Any]:
    inventory = load_integration_inventory(
        inventory_path, project_root=project_root, verify_current_routes=True
    )
    routes = inventory["routes"]
    return {
        "schema": "kira.shared_person_growth_v3_route_coverage.v1",
        "inventory_sha256": inventory_sha256(inventory_path),
        "person_count": len(inventory["people"]),
        "route_count": len(routes),
        "applicable_route_count": sum(r["disposition"] == "applicable" for r in routes),
        "denied_alias_route_count": sum(
            r["disposition"] == "deny_alias_no_person_authority" for r in routes
        ),
        "temporary_profile_route_count": sum(
            r["source_path"].startswith("TemporaryAI/candidates/") for r in routes
        ),
        "temporary_state_route_count": sum(
            r["source_path"].startswith("Avatar/state/temp_ai/") for r in routes
        ),
        "permanent_route_count": sum(r["route_kind"] == "permanent_selector" for r in routes),
        "omitted_person_ids": [],
        "omitted_route_paths": [],
        "cross_bound_route_ids": [],
        "biological_robert_profile_created": False,
    }


class IntegrationIdentityHandle:
    __slots__ = ()

    def __new__(cls, key: object | None = None) -> "IntegrationIdentityHandle":
        if key is not _HANDLE_KEY:
            raise TypeError("integration identity handles are controller-owned")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("integration identity handles cannot be copied")

    def __deepcopy__(self, memo: object) -> None:
        raise TypeError("integration identity handles cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("integration identity handles cannot be serialized")


class IntegrationReceiptHandle:
    __slots__ = ()

    def __new__(cls, key: object | None = None) -> "IntegrationReceiptHandle":
        if key is not _HANDLE_KEY:
            raise TypeError("integration receipts are controller-owned")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("integration receipts cannot be copied")

    def __deepcopy__(self, memo: object) -> None:
        raise TypeError("integration receipts cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("integration receipts cannot be serialized")


_LEDGER_KEYS = {
    "schema",
    "sequence",
    "previous_record_sha256",
    "operation_id",
    "kind",
    "binding",
    "binding_sha256",
    "authenticator_sha256",
    "record_sha256",
}

_LEDGER_BINDING_KEYS = {
    "migration_receipt_issue": {
        "receipt_sha256",
        "attachment_sha256",
        "route_id",
        "profile_fingerprint_sha256",
    },
    "migration_commit_and_receipt_consume": {
        "receipt_sha256",
        "attachment_sha256",
        "person_id",
        "profile_id",
        "output_name",
    },
    "migration_precommit_rollback": {
        "receipt_sha256",
        "attachment_sha256",
        "output_name",
        "output_absent_after_rollback",
    },
    "migration_postcommit_rollback": {
        "attachment_sha256",
        "person_id",
        "profile_id",
        "output_name",
        "output_absent_after_rollback",
        "production_pointer_changed",
    },
}


class _AppendOnlyIntegrationLedger:
    def __init__(self, root: Path, authentication_key: bytes) -> None:
        if not isinstance(root, Path):
            raise GrowthIntegrationError("ledger root must be pathlib.Path")
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise GrowthIntegrationError("ledger root must not be a symlink")
        self._lock = threading.RLock()
        if type(authentication_key) is not bytes or len(authentication_key) != 32:
            raise GrowthIntegrationAuthorityError("ledger authentication key is invalid")
        self.__authentication_key = bytes(authentication_key)
        self._records: list[dict[str, Any]] = []
        self._reload()

    @staticmethod
    def _validate_binding(kind: str, binding: Any) -> dict[str, Any]:
        if kind not in _LEDGER_BINDING_KEYS:
            raise GrowthIntegrationRecoveryRequired("ledger kind is not closed")
        checked = _exact_keys(binding, _LEDGER_BINDING_KEYS[kind], "ledger.binding")
        for field in (
            "receipt_sha256",
            "attachment_sha256",
            "profile_fingerprint_sha256",
        ):
            if field in checked:
                _sha(checked[field], f"ledger.binding.{field}")
        for field in ("route_id", "person_id", "profile_id"):
            if field in checked:
                _identifier(checked[field], f"ledger.binding.{field}")
        if "output_name" in checked:
            output_name = _text(checked["output_name"], "ledger.binding.output_name", 256)
            if Path(output_name).name != output_name or not output_name.endswith(
                ".shared_growth_integration_v1.json"
            ):
                raise GrowthIntegrationRecoveryRequired("ledger output name is not closed")
        for field in ("output_absent_after_rollback", "production_pointer_changed"):
            if field in checked and type(checked[field]) is not bool:
                raise GrowthIntegrationRecoveryRequired("ledger truth value is not exact bool")
        if "output_absent_after_rollback" in checked and checked["output_absent_after_rollback"] is not True:
            raise GrowthIntegrationRecoveryRequired("ledger rollback did not prove output absence")
        if "production_pointer_changed" in checked and checked["production_pointer_changed"] is not False:
            raise GrowthIntegrationRecoveryRequired("ledger claims a production pointer change")
        return deepcopy(dict(checked))

    def _validate_record(
        self, value: Any, *, expected_sequence: int, expected_previous: str
    ) -> dict[str, Any]:
        record = _exact_keys(value, _LEDGER_KEYS, "integration_ledger_record")
        if record["schema"] != LEDGER_RECORD_SCHEMA:
            raise GrowthIntegrationRecoveryRequired("ledger record schema drifted")
        if type(record["sequence"]) is not int or record["sequence"] != expected_sequence:
            raise GrowthIntegrationRecoveryRequired("ledger sequence drifted")
        if record["previous_record_sha256"] != expected_previous:
            raise GrowthIntegrationRecoveryRequired("ledger previous hash drifted")
        _identifier(record["operation_id"], "ledger.operation_id")
        kind = _identifier(record["kind"], "ledger.kind")
        self._validate_binding(kind, record["binding"])
        binding_sha = _sha(record["binding_sha256"], "ledger.binding_sha256")
        if _sha_mapping(record["binding"]) != binding_sha:
            raise GrowthIntegrationRecoveryRequired("ledger binding hash drifted")
        authenticator = _sha(
            record["authenticator_sha256"], "ledger.authenticator_sha256"
        )
        authenticated = deepcopy(dict(record))
        authenticated.pop("record_sha256")
        authenticated.pop("authenticator_sha256")
        expected_authenticator = hmac.new(
            self.__authentication_key,
            b"shared-growth-v3-integration-ledger-v1\x00"
            + _canonical_bytes(authenticated),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(authenticator, expected_authenticator):
            raise GrowthIntegrationRecoveryRequired("ledger authenticator mismatch")
        record_sha = _sha(record["record_sha256"], "ledger.record_sha256")
        unsigned = deepcopy(dict(record))
        unsigned.pop("record_sha256")
        if _sha_mapping(unsigned) != record_sha:
            raise GrowthIntegrationRecoveryRequired("ledger record hash drifted")
        return deepcopy(dict(record))

    def _reload(self) -> None:
        names = sorted(path.name for path in self.root.iterdir() if path.is_file())
        if any(_LEDGER_NAME_RE.fullmatch(name) is None for name in names):
            raise GrowthIntegrationRecoveryRequired("ledger contains an unknown file")
        records: list[dict[str, Any]] = []
        previous = "0" * 64
        operations: set[str] = set()
        for sequence, name in enumerate(names, 1):
            if name != f"{sequence:08d}.json":
                raise GrowthIntegrationRecoveryRequired("ledger has a sequence gap")
            path = self.root / name
            if path.is_symlink():
                raise GrowthIntegrationRecoveryRequired("ledger record is a symlink")
            try:
                raw = path.read_bytes()
                parsed = json.loads(raw, object_pairs_hook=_strict_object)
            except Exception as exc:
                raise GrowthIntegrationRecoveryRequired("ledger record is unreadable") from exc
            record = self._validate_record(
                parsed, expected_sequence=sequence, expected_previous=previous
            )
            if record["operation_id"] in operations:
                raise GrowthIntegrationRecoveryRequired("ledger operation ID replayed")
            operations.add(record["operation_id"])
            previous = record["record_sha256"]
            records.append(record)
        self._records = records

    def append(self, *, operation_id: str, kind: str, binding: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._reload()
            operation_id = _identifier(operation_id, "ledger.operation_id")
            kind = _identifier(kind, "ledger.kind")
            if any(record["operation_id"] == operation_id for record in self._records):
                raise GrowthReplayError("integration ledger operation ID replayed")
            checked_binding = self._validate_binding(kind, binding)
            sequence = len(self._records) + 1
            body: dict[str, Any] = {
                "schema": LEDGER_RECORD_SCHEMA,
                "sequence": sequence,
                "previous_record_sha256": (
                    self._records[-1]["record_sha256"] if self._records else "0" * 64
                ),
                "operation_id": operation_id,
                "kind": kind,
                "binding": checked_binding,
                "binding_sha256": _sha_mapping(checked_binding),
            }
            body["authenticator_sha256"] = hmac.new(
                self.__authentication_key,
                b"shared-growth-v3-integration-ledger-v1\x00"
                + _canonical_bytes(body),
                hashlib.sha256,
            ).hexdigest()
            body["record_sha256"] = _sha_mapping(body)
            data = json.dumps(body, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            encoded = data.encode("utf-8")
            output = self.root / f"{sequence:08d}.json"
            created = False
            try:
                fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                created = True
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                if output.read_bytes() != encoded:
                    raise GrowthIntegrationRecoveryRequired("ledger exact-byte readback failed")
                self._reload()
                if self._records[-1]["record_sha256"] != body["record_sha256"]:
                    raise GrowthIntegrationRecoveryRequired("ledger accepted head differs")
            except FileExistsError as exc:
                self._reload()
                raise GrowthIntegrationRecoveryRequired("concurrent ledger append won CAS") from exc
            except BaseException:
                # A created-but-unverified record is deliberately retained.  Its
                # malformed or uncertain tail makes every later reload fail closed.
                if not created:
                    self._reload()
                raise
            return deepcopy(body)

    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            self._reload()
            return deepcopy(self._records)


_PUBLIC_ATTACHMENT_KEYS = {
    "schema",
    "status",
    "route_binding",
    "profile_binding",
    "maturity_projection",
    "public_capability_projection",
    "source_binding",
    "integration_truth",
    "attachment_sha256",
}
_ROUTE_BINDING_KEYS = {
    "route_id",
    "route_kind",
    "inventory_sha256",
    "existing_person_route",
    "creator_new_person_route",
}
_PROFILE_BINDING_KEYS = {
    "person_id",
    "candidate_id",
    "profile_id",
    "profile_fingerprint_sha256",
    "controller_id",
    "controller_identity_sha256",
    "growth_policy_sha256",
}
_MATURITY_PROJECTION_KEYS = {
    "status",
    "maturity_source_id",
    "classification_receipt_sha256",
    "full_adult_curriculum_eligible",
    "full_adult_curriculum_delivered",
    "adult_anatomy_added",
    "consent_granted",
    "default_body_lane",
}
_CAPABILITY_PROJECTION_KEYS = {
    "catalog_sha256",
    "static_candidate_capability_ids",
    "design_only_capability_ids",
    "live_enabled_capability_ids",
    "bounded_initiative_stage",
    "bounded_initiative_live_enabled",
}
_SOURCE_BINDING_KEYS = {
    "route_source_path",
    "route_source_sha256",
    "creator_bundle_sha256",
}
_PUBLIC_TRUTH = {
    "default_off": True,
    "staged_not_promoted": True,
    "production_pointer_changed": False,
    "private_state_roots_included": False,
    "private_memory_or_emotion_payload_included": False,
    "profile_or_creator_bundle_copied": False,
    "automatic_lived_memory_created": False,
    "automatic_emotion_created": False,
    "automatic_external_action_created": False,
    "person_activated": False,
    "model_or_device_called": False,
}
_RECEIPT_KEYS = {
    "schema",
    "operation_id",
    "attachment_sha256",
    "route_id",
    "person_id",
    "candidate_id",
    "profile_id",
    "profile_fingerprint_sha256",
    "inventory_sha256",
    "single_use",
    "authenticator_sha256",
    "receipt_sha256",
}
_EXPECTED_STATIC_CAPABILITY_IDS = [
    "causal_emotion_continuity",
    "learning_proposals",
    "present_source_grounding",
]
_EXPECTED_DESIGN_ONLY_CAPABILITY_IDS = [
    "body_control",
    "bounded_initiative",
    "external_practical_adapters",
    "resident_media_experience",
    "vision_and_hearing",
]
_EXPECTED_CAPABILITY_CATALOG_SHA256 = (
    "ecb7d97f8918153eeb2b33296a0e25bd6918f6cd86fe1428df404618cc3b08c7"
)


def _public_capability_projection(profile: Mapping[str, Any]) -> dict[str, Any]:
    capabilities = profile["capabilities"]
    static_ids = sorted(
        key for key, value in capabilities.items() if value["stage"] == "STATIC_CANDIDATE"
    )
    design_ids = sorted(
        key for key, value in capabilities.items() if value["stage"] == "DESIGN_ONLY"
    )
    live_ids = sorted(key for key, value in capabilities.items() if value["live_enabled"] is True)
    return {
        "catalog_sha256": _sha_mapping(capabilities),
        "static_candidate_capability_ids": static_ids,
        "design_only_capability_ids": design_ids,
        "live_enabled_capability_ids": live_ids,
        "bounded_initiative_stage": capabilities["bounded_initiative"]["stage"],
        "bounded_initiative_live_enabled": capabilities["bounded_initiative"]["live_enabled"],
    }


def validate_public_attachment(
    value: Mapping[str, Any],
    *,
    inventory: Mapping[str, Any],
    inventory_digest: str,
    authority_controller: ProtectedGrowthController,
) -> dict[str, Any]:
    attachment = _exact_keys(value, _PUBLIC_ATTACHMENT_KEYS, "public_attachment")
    if attachment["schema"] != PUBLIC_ATTACHMENT_SCHEMA:
        raise GrowthIntegrationError("public attachment schema mismatch")
    if attachment["status"] != "DEFAULT_OFF_STAGED_NOT_PROMOTED":
        raise GrowthIntegrationError("public attachment status drifted")
    route = _exact_keys(attachment["route_binding"], _ROUTE_BINDING_KEYS, "route_binding")
    route_id = _identifier(route["route_id"], "route_id")
    _identifier(route["route_kind"], "route_kind")
    if route["inventory_sha256"] != inventory_digest:
        raise GrowthIntegrationError("attachment inventory binding mismatch")
    if type(route["existing_person_route"]) is not bool or type(route["creator_new_person_route"]) is not bool:
        raise GrowthIntegrationError("route truth values must be exact bool")
    if route["existing_person_route"] is route["creator_new_person_route"]:
        raise GrowthIntegrationError("attachment must use exactly one route class")

    profile = _exact_keys(
        attachment["profile_binding"], _PROFILE_BINDING_KEYS, "profile_binding"
    )
    for field in ("person_id", "candidate_id", "profile_id", "controller_id"):
        _identifier(profile[field], f"profile_binding.{field}")
    for field in (
        "profile_fingerprint_sha256",
        "controller_identity_sha256",
        "growth_policy_sha256",
    ):
        _sha(profile[field], f"profile_binding.{field}")
    if profile["controller_id"] != authority_controller.controller_id:
        raise GrowthIntegrationAuthorityError("attachment controller label differs")
    if profile["controller_identity_sha256"] != authority_controller.controller_identity_sha256:
        raise GrowthIntegrationAuthorityError("attachment controller identity differs")
    if profile["growth_policy_sha256"] != inventory["growth_v3_binding"]["policy_sha256"]:
        raise GrowthIntegrationError("attachment Growth V3 policy differs")

    maturity = _exact_keys(
        attachment["maturity_projection"], _MATURITY_PROJECTION_KEYS, "maturity_projection"
    )
    if maturity["status"] not in {"confirmed_adult", "non_adult", "unresolved"}:
        raise GrowthIntegrationError("attachment maturity is unsupported")
    _identifier(maturity["maturity_source_id"], "maturity_source_id")
    _sha(
        maturity["classification_receipt_sha256"],
        "classification_receipt_sha256",
        nullable=maturity["status"] == "unresolved",
    )
    if maturity["status"] == "unresolved" and maturity["classification_receipt_sha256"] is not None:
        raise GrowthIntegrationError("unresolved attachment claims maturity receipt")
    expected_adult = maturity["status"] == "confirmed_adult"
    if maturity["full_adult_curriculum_eligible"] is not expected_adult:
        raise GrowthIntegrationError("adult curriculum eligibility drifted")
    for field in ("full_adult_curriculum_delivered", "adult_anatomy_added", "consent_granted"):
        if maturity[field] is not False:
            raise GrowthIntegrationError(f"attachment inferred {field}")
    expected_lane = (
        "separately_selected_adult_body_pending"
        if expected_adult
        else "doll_safe_non_anatomical"
    )
    if maturity["default_body_lane"] != expected_lane:
        raise GrowthIntegrationError("attachment body lane drifted")

    capability = _exact_keys(
        attachment["public_capability_projection"],
        _CAPABILITY_PROJECTION_KEYS,
        "public_capability_projection",
    )
    _sha(capability["catalog_sha256"], "capability.catalog_sha256")
    for field in (
        "static_candidate_capability_ids",
        "design_only_capability_ids",
        "live_enabled_capability_ids",
    ):
        if type(capability[field]) is not list or any(type(v) is not str for v in capability[field]):
            raise GrowthIntegrationError("capability IDs must be exact string lists")
        if capability[field] != sorted(set(capability[field])):
            raise GrowthIntegrationError("capability IDs must be sorted and unique")
    if capability["catalog_sha256"] != _EXPECTED_CAPABILITY_CATALOG_SHA256:
        raise GrowthIntegrationError("public capability catalog hash drifted")
    if capability["static_candidate_capability_ids"] != _EXPECTED_STATIC_CAPABILITY_IDS:
        raise GrowthIntegrationError("static candidate capability set drifted")
    if capability["design_only_capability_ids"] != _EXPECTED_DESIGN_ONLY_CAPABILITY_IDS:
        raise GrowthIntegrationError("design-only capability set drifted")
    if capability["live_enabled_capability_ids"] != []:
        raise GrowthIntegrationError("static attachment cannot enable a capability")
    if capability["bounded_initiative_stage"] != "DESIGN_ONLY":
        raise GrowthIntegrationError("bounded initiative is not DESIGN_ONLY")
    if capability["bounded_initiative_live_enabled"] is not False:
        raise GrowthIntegrationError("bounded initiative was enabled")

    source = _exact_keys(attachment["source_binding"], _SOURCE_BINDING_KEYS, "source_binding")
    _relative_path(source["route_source_path"], "route_source_path")
    _sha(source["route_source_sha256"], "route_source_sha256")
    _sha(source["creator_bundle_sha256"], "creator_bundle_sha256", nullable=True)
    routes = {item["route_id"]: item for item in inventory["routes"]}
    people = {item["person_id"]: item for item in inventory["people"]}
    if route["existing_person_route"]:
        if route_id not in routes or routes[route_id]["disposition"] != "applicable":
            raise GrowthIntegrationError("attachment existing route is unavailable")
        expected = routes[route_id]
        if route["route_kind"] != expected["route_kind"]:
            raise GrowthIntegrationError("attachment route kind differs")
        if source["route_source_path"] != expected["source_path"] or source["route_source_sha256"] != expected["source_sha256"]:
            raise GrowthIntegrationError("attachment route source differs")
        if source["creator_bundle_sha256"] is not None:
            raise GrowthIntegrationError("existing route claims a Creator bundle")
        if profile["person_id"] != expected["person_id"] or profile["candidate_id"] != expected["candidate_id"]:
            raise GrowthIntegrationError("attachment existing route is cross-bound")
        person = people[profile["person_id"]]
        if maturity["status"] != person["required_maturity"]:
            raise GrowthIntegrationError("attachment maturity is incompatible with person route")
        if maturity["maturity_source_id"] != person["maturity_source_id"]:
            raise GrowthIntegrationError("attachment maturity source is cross-bound")
    else:
        creator = inventory["creator_lane"]
        if route_id != creator["route_id"] or route["route_kind"] != "temporary_creator_new_person":
            raise GrowthIntegrationError("attachment Creator route differs")
        if source["route_source_path"] != inventory["growth_v3_binding"]["creator_path"] or source["route_source_sha256"] != inventory["growth_v3_binding"]["creator_sha256"]:
            raise GrowthIntegrationError("attachment Creator source differs")
        _sha(source["creator_bundle_sha256"], "creator_bundle_sha256")
        if profile["person_id"] in people or profile["candidate_id"] in {
            item["candidate_id"] for item in inventory["people"]
        }:
            raise GrowthIntegrationError("Creator attachment collides with an existing person")
        expected_source = (
            "no_protected_source"
            if maturity["status"] == "unresolved"
            else "creator_protected_v3_receipt"
        )
        if maturity["maturity_source_id"] != expected_source:
            raise GrowthIntegrationError("Creator maturity source truth differs")
    if not _typed_equal(attachment["integration_truth"], _PUBLIC_TRUTH):
        raise GrowthIntegrationError("public attachment truth boundary drifted")
    digest = _sha(attachment["attachment_sha256"], "attachment_sha256")
    unsigned = deepcopy(dict(attachment))
    unsigned.pop("attachment_sha256")
    if _sha_mapping(unsigned) != digest:
        raise GrowthIntegrationError("public attachment hash mismatch")
    forbidden = {
        "private_state_roots",
        "growth_profile",
        "private_records",
        "private_payload",
        "memory_payload",
        "emotion_payload",
        "authority_secret",
    }

    def reject_private(node: Any) -> None:
        if type(node) is dict:
            if set(node) & forbidden:
                raise GrowthIntegrationError("public attachment contains private payload fields")
            for child in node.values():
                reject_private(child)
        elif type(node) is list:
            for child in node:
                reject_private(child)

    reject_private(attachment)
    return deepcopy(dict(attachment))


class SharedGrowthV3IntegrationAdapter:
    """One exact, default-off, public-only V3 integration adapter."""

    def __init__(
        self,
        *,
        authority_controller: ProtectedGrowthController,
        authority_identity: ControllerIdentityHandle,
        integration_secret: bytes,
        ledger_root: Path,
        staging_root: Path,
        inventory_path: Path = INVENTORY_PATH,
        project_root: Path = PROJECT_ROOT,
    ) -> None:
        if type(authority_controller) is not ProtectedGrowthController:
            raise GrowthIntegrationAuthorityError("exact V3 controller is required")
        if authority_identity is not authority_controller.identity:
            raise GrowthIntegrationAuthorityError("exact V3 controller identity is required")
        self._validate_secret(integration_secret)
        self.__authority_controller = authority_controller
        self.__authority_identity = authority_identity
        self.__secret = bytes(integration_secret)
        self.__identity = IntegrationIdentityHandle(_HANDLE_KEY)
        self.__inventory_path = inventory_path.resolve()
        self.__project_root = project_root.resolve()
        self.__inventory = load_integration_inventory(
            self.__inventory_path,
            project_root=self.__project_root,
            verify_current_routes=True,
        )
        self.__inventory_sha = inventory_sha256(self.__inventory_path)
        if not isinstance(staging_root, Path):
            raise GrowthIntegrationError("staging_root must be pathlib.Path")
        self.__staging_root = staging_root.resolve()
        self.__staging_root.mkdir(parents=True, exist_ok=True)
        if self.__staging_root.is_symlink():
            raise GrowthIntegrationError("staging_root must not be a symlink")
        self.__ledger = _AppendOnlyIntegrationLedger(ledger_root, self.__secret)
        self.__receipts: dict[IntegrationReceiptHandle, dict[str, Any]] = {}
        self.__lock = threading.RLock()

    @staticmethod
    def _validate_secret(value: Any) -> None:
        if type(value) is not bytes or len(value) != 32 or 0 in value or len(set(value)) < 16:
            raise GrowthIntegrationAuthorityError(
                "integration_secret must be exact 32 nonzero bytes with at least 16 distinct values"
            )

    @property
    def identity(self) -> IntegrationIdentityHandle:
        return self.__identity

    @property
    def inventory_digest(self) -> str:
        return self.__inventory_sha

    def _authenticate(self, identity: IntegrationIdentityHandle, secret: bytes) -> None:
        if identity is not self.__identity:
            raise GrowthIntegrationAuthorityError("exact integration identity capability mismatch")
        self._validate_secret(secret)
        if not hmac.compare_digest(secret, self.__secret):
            raise GrowthIntegrationAuthorityError("integration secret mismatch")

    def _make_attachment(
        self,
        *,
        profile: Mapping[str, Any],
        route_id: str,
        route_kind: str,
        source_path: str,
        source_sha256: str,
        maturity_source_id: str,
        existing_person: bool,
        creator_bundle_sha256: str | None,
    ) -> dict[str, Any]:
        checked = validate_capability_profile(
            profile,
            authority_controller=self.__authority_controller,
            authority_identity=self.__authority_identity,
        )
        maturity = checked["maturity"]
        attachment: dict[str, Any] = {
            "schema": PUBLIC_ATTACHMENT_SCHEMA,
            "status": "DEFAULT_OFF_STAGED_NOT_PROMOTED",
            "route_binding": {
                "route_id": route_id,
                "route_kind": route_kind,
                "inventory_sha256": self.__inventory_sha,
                "existing_person_route": existing_person,
                "creator_new_person_route": not existing_person,
            },
            "profile_binding": {
                "person_id": checked["person_binding"]["person_id"],
                "candidate_id": checked["person_binding"]["candidate_id"],
                "profile_id": checked["profile_id"],
                "profile_fingerprint_sha256": checked["profile_fingerprint_sha256"],
                "controller_id": checked["authority_binding"]["controller_id"],
                "controller_identity_sha256": checked["authority_binding"]["controller_identity_sha256"],
                "growth_policy_sha256": checked["policy"]["sha256"],
            },
            "maturity_projection": {
                "status": maturity["status"],
                "maturity_source_id": maturity_source_id,
                "classification_receipt_sha256": maturity["classification_receipt_sha256"],
                "full_adult_curriculum_eligible": maturity["full_adult_curriculum_eligible"],
                "full_adult_curriculum_delivered": False,
                "adult_anatomy_added": False,
                "consent_granted": False,
                "default_body_lane": maturity["default_body_lane"],
            },
            "public_capability_projection": _public_capability_projection(checked),
            "source_binding": {
                "route_source_path": source_path,
                "route_source_sha256": source_sha256,
                "creator_bundle_sha256": creator_bundle_sha256,
            },
            "integration_truth": deepcopy(_PUBLIC_TRUTH),
        }
        attachment["attachment_sha256"] = _sha_mapping(attachment)
        return validate_public_attachment(
            attachment,
            inventory=self.__inventory,
            inventory_digest=self.__inventory_sha,
            authority_controller=self.__authority_controller,
        )

    def _validate_receipt_body(
        self, value: Mapping[str, Any], *, attachment: Mapping[str, Any]
    ) -> dict[str, Any]:
        body = _exact_keys(value, _RECEIPT_KEYS, "integration_receipt")
        if body["schema"] != RECEIPT_SCHEMA:
            raise GrowthIntegrationAuthorityError("integration receipt schema mismatch")
        for field in (
            "operation_id",
            "route_id",
            "person_id",
            "candidate_id",
            "profile_id",
        ):
            _identifier(body[field], f"integration_receipt.{field}")
        for field in (
            "attachment_sha256",
            "profile_fingerprint_sha256",
            "inventory_sha256",
            "authenticator_sha256",
            "receipt_sha256",
        ):
            _sha(body[field], f"integration_receipt.{field}")
        if body["single_use"] is not True:
            raise GrowthIntegrationAuthorityError("integration receipt lost single-use truth")
        expected = {
            "attachment_sha256": attachment["attachment_sha256"],
            "route_id": attachment["route_binding"]["route_id"],
            "person_id": attachment["profile_binding"]["person_id"],
            "candidate_id": attachment["profile_binding"]["candidate_id"],
            "profile_id": attachment["profile_binding"]["profile_id"],
            "profile_fingerprint_sha256": attachment["profile_binding"][
                "profile_fingerprint_sha256"
            ],
            "inventory_sha256": self.__inventory_sha,
        }
        if any(body[field] != expected_value for field, expected_value in expected.items()):
            raise GrowthIntegrationAuthorityError("integration receipt exact binding differs")
        authenticated = deepcopy(dict(body))
        authenticated.pop("receipt_sha256")
        authenticator = authenticated.pop("authenticator_sha256")
        expected_authenticator = hmac.new(
            self.__secret,
            b"shared-growth-v3-integration-v1\x00" + _canonical_bytes(authenticated),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(authenticator, expected_authenticator):
            raise GrowthIntegrationAuthorityError("integration receipt authenticator mismatch")
        unsigned = deepcopy(dict(body))
        unsigned.pop("receipt_sha256")
        if _sha_mapping(unsigned) != body["receipt_sha256"]:
            raise GrowthIntegrationAuthorityError("integration receipt hash mismatch")
        return deepcopy(dict(body))

    def _issue(
        self,
        *,
        identity: IntegrationIdentityHandle,
        secret: bytes,
        operation_id: str,
        attachment: Mapping[str, Any],
    ) -> IntegrationReceiptHandle:
        with self.__lock:
            self._authenticate(identity, secret)
            operation_id = _identifier(operation_id, "receipt.operation_id")
            checked = validate_public_attachment(
                attachment,
                inventory=self.__inventory,
                inventory_digest=self.__inventory_sha,
                authority_controller=self.__authority_controller,
            )
            body = {
                "schema": RECEIPT_SCHEMA,
                "operation_id": operation_id,
                "attachment_sha256": checked["attachment_sha256"],
                "route_id": checked["route_binding"]["route_id"],
                "person_id": checked["profile_binding"]["person_id"],
                "candidate_id": checked["profile_binding"]["candidate_id"],
                "profile_id": checked["profile_binding"]["profile_id"],
                "profile_fingerprint_sha256": checked["profile_binding"]["profile_fingerprint_sha256"],
                "inventory_sha256": self.__inventory_sha,
                "single_use": True,
            }
            body["authenticator_sha256"] = hmac.new(
                self.__secret,
                b"shared-growth-v3-integration-v1\x00" + _canonical_bytes(body),
                hashlib.sha256,
            ).hexdigest()
            body["receipt_sha256"] = _sha_mapping(body)
            self._validate_receipt_body(body, attachment=checked)
            self.__ledger.append(
                operation_id=operation_id,
                kind="migration_receipt_issue",
                binding={
                    "receipt_sha256": body["receipt_sha256"],
                    "attachment_sha256": checked["attachment_sha256"],
                    "route_id": body["route_id"],
                    "profile_fingerprint_sha256": body["profile_fingerprint_sha256"],
                },
            )
            handle = IntegrationReceiptHandle(_HANDLE_KEY)
            self.__receipts[handle] = {
                "body": body,
                "attachment": checked,
                "consumed": False,
            }
            return handle

    def issue_existing_person_migration(
        self,
        *,
        identity: IntegrationIdentityHandle,
        secret: bytes,
        operation_id: str,
        route_id: str,
        profile: Mapping[str, Any],
    ) -> IntegrationReceiptHandle:
        self._authenticate(identity, secret)
        route_id = _identifier(route_id, "route_id")
        routes = {item["route_id"]: item for item in self.__inventory["routes"]}
        if route_id not in routes or routes[route_id]["disposition"] != "applicable":
            raise GrowthIntegrationAuthorityError("route is absent, denied, or not applicable")
        route = routes[route_id]
        checked = validate_capability_profile(
            profile,
            authority_controller=self.__authority_controller,
            authority_identity=self.__authority_identity,
        )
        binding = checked["person_binding"]
        if binding["person_id"] != route["person_id"] or binding["candidate_id"] != route["candidate_id"]:
            raise GrowthIntegrationAuthorityError("profile and route exact identity differ")
        person = next(
            item for item in self.__inventory["people"] if item["person_id"] == route["person_id"]
        )
        if checked["maturity"]["status"] != person["required_maturity"]:
            raise GrowthIntegrationAuthorityError("profile maturity is incompatible with exact person")
        attachment = self._make_attachment(
            profile=checked,
            route_id=route_id,
            route_kind=route["route_kind"],
            source_path=route["source_path"],
            source_sha256=route["source_sha256"],
            maturity_source_id=person["maturity_source_id"],
            existing_person=True,
            creator_bundle_sha256=None,
        )
        return self._issue(
            identity=identity,
            secret=secret,
            operation_id=operation_id,
            attachment=attachment,
        )

    def issue_creator_migration(
        self,
        *,
        identity: IntegrationIdentityHandle,
        secret: bytes,
        operation_id: str,
        creator_bundle: Mapping[str, Any],
    ) -> IntegrationReceiptHandle:
        self._authenticate(identity, secret)
        bundle = validate_creator_bundle(
            creator_bundle,
            authority_controller=self.__authority_controller,
            authority_identity=self.__authority_identity,
        )
        profile = bundle["attachment"]["growth_profile"]
        existing_people = {item["person_id"] for item in self.__inventory["people"]}
        existing_candidates = {item["candidate_id"] for item in self.__inventory["people"]}
        binding = profile["person_binding"]
        if binding["person_id"] in existing_people or binding["candidate_id"] in existing_candidates:
            raise GrowthIntegrationAuthorityError("Temporary Creator identity collides with an existing person")
        denied_candidates = {
            item["candidate_id"]
            for item in self.__inventory["routes"]
            if item["disposition"] != "applicable"
        }
        if binding["candidate_id"] in denied_candidates:
            raise GrowthIntegrationAuthorityError("Temporary Creator candidate collides with a denied alias")
        maturity = profile["maturity"]
        source_id = (
            "no_protected_source"
            if maturity["status"] == "unresolved"
            else "creator_protected_v3_receipt"
        )
        attachment = self._make_attachment(
            profile=profile,
            route_id=self.__inventory["creator_lane"]["route_id"],
            route_kind="temporary_creator_new_person",
            source_path=self.__inventory["growth_v3_binding"]["creator_path"],
            source_sha256=self.__inventory["growth_v3_binding"]["creator_sha256"],
            maturity_source_id=source_id,
            existing_person=False,
            creator_bundle_sha256=bundle["bundle_sha256"],
        )
        return self._issue(
            identity=identity,
            secret=secret,
            operation_id=operation_id,
            attachment=attachment,
        )

    def stage_receipt(
        self,
        *,
        identity: IntegrationIdentityHandle,
        secret: bytes,
        receipt: IntegrationReceiptHandle,
        operation_id: str,
    ) -> Path:
        with self.__lock:
            self._authenticate(identity, secret)
            operation_id = _identifier(operation_id, "stage.operation_id")
            if type(receipt) is not IntegrationReceiptHandle or receipt not in self.__receipts:
                raise GrowthIntegrationAuthorityError("migration receipt is not owned by this adapter")
            stored = self.__receipts[receipt]
            if stored["consumed"]:
                raise GrowthReplayError("migration receipt was already consumed")
            attachment = validate_public_attachment(
                stored["attachment"],
                inventory=self.__inventory,
                inventory_digest=self.__inventory_sha,
                authority_controller=self.__authority_controller,
            )
            receipt_body = self._validate_receipt_body(
                stored["body"], attachment=attachment
            )
            profile_id = attachment["profile_binding"]["profile_id"]
            output = self.__staging_root / f"{profile_id}.shared_growth_integration_v1.json"
            if output.parent.resolve() != self.__staging_root or output.is_symlink():
                raise GrowthIntegrationError("staged output escaped its exact root")
            data = json.dumps(attachment, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            encoded = data.encode("utf-8")
            created = False
            try:
                fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                created = True
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                readback = output.read_bytes()
                if readback != encoded:
                    raise GrowthIntegrationError("staged attachment exact-byte readback failed")
                observed = json.loads(readback, object_pairs_hook=_strict_object)
                validate_public_attachment(
                    observed,
                    inventory=self.__inventory,
                    inventory_digest=self.__inventory_sha,
                    authority_controller=self.__authority_controller,
                )
                self.__ledger.append(
                    operation_id=operation_id,
                    kind="migration_commit_and_receipt_consume",
                    binding={
                        "receipt_sha256": receipt_body["receipt_sha256"],
                        "attachment_sha256": attachment["attachment_sha256"],
                        "person_id": attachment["profile_binding"]["person_id"],
                        "profile_id": profile_id,
                        "output_name": output.name,
                    },
                )
                stored["consumed"] = True
                stored["output_name"] = output.name
            except BaseException as exc:
                if not created:
                    # Exclusive-create refusal proves this attempt created
                    # nothing.  Preserve the pre-existing owner bytes and do
                    # not mislabel their continued presence as rollback debt.
                    raise exc
                if created and output.exists() and not output.is_symlink():
                    output.unlink()
                try:
                    self.__ledger.append(
                        operation_id=f"rollback:{operation_id}",
                        kind="migration_precommit_rollback",
                        binding={
                            "receipt_sha256": receipt_body["receipt_sha256"],
                            "attachment_sha256": attachment["attachment_sha256"],
                            "output_name": output.name,
                            "output_absent_after_rollback": not output.exists(),
                        },
                    )
                except BaseException as rollback_exc:
                    raise GrowthIntegrationRecoveryRequired(
                        "staging failed and rollback ledger could not be proven"
                    ) from rollback_exc
                raise exc
            return output

    def rollback_staged_attachment(
        self,
        *,
        identity: IntegrationIdentityHandle,
        secret: bytes,
        output: Path,
        operation_id: str,
    ) -> dict[str, Any]:
        with self.__lock:
            self._authenticate(identity, secret)
            operation_id = _identifier(operation_id, "rollback.operation_id")
            if not isinstance(output, Path):
                raise GrowthIntegrationError("rollback output must be pathlib.Path")
            resolved = output.resolve()
            if resolved.parent != self.__staging_root or resolved.is_symlink():
                raise GrowthIntegrationAuthorityError("rollback output escaped exact staging root")
            if not resolved.is_file():
                raise FileNotFoundError("exact staged attachment does not exist")
            observed = json.loads(resolved.read_bytes(), object_pairs_hook=_strict_object)
            attachment = validate_public_attachment(
                observed,
                inventory=self.__inventory,
                inventory_digest=self.__inventory_sha,
                authority_controller=self.__authority_controller,
            )
            commits = [
                record
                for record in self.__ledger.records()
                if record["kind"] == "migration_commit_and_receipt_consume"
                and record["binding"].get("attachment_sha256") == attachment["attachment_sha256"]
                and record["binding"].get("output_name") == resolved.name
            ]
            prior_rollbacks = [
                record
                for record in self.__ledger.records()
                if record["kind"] == "migration_postcommit_rollback"
                and record["binding"].get("attachment_sha256") == attachment["attachment_sha256"]
                and record["binding"].get("output_name") == resolved.name
            ]
            if len(commits) != 1 or prior_rollbacks:
                raise GrowthIntegrationAuthorityError("staged attachment lacks one live commit")
            resolved.unlink()
            if resolved.exists():
                raise GrowthIntegrationRecoveryRequired("staged attachment deletion was not proven")
            record = self.__ledger.append(
                operation_id=operation_id,
                kind="migration_postcommit_rollback",
                binding={
                    "attachment_sha256": attachment["attachment_sha256"],
                    "person_id": attachment["profile_binding"]["person_id"],
                    "profile_id": attachment["profile_binding"]["profile_id"],
                    "output_name": resolved.name,
                    "output_absent_after_rollback": True,
                    "production_pointer_changed": False,
                },
            )
            return {
                "schema": "kira.shared_person_growth_v3_integration_rollback.v1",
                "attachment_sha256": attachment["attachment_sha256"],
                "output_name": resolved.name,
                "output_absent": True,
                "production_pointer_changed": False,
                "ledger_record_sha256": record["record_sha256"],
            }

    def ledger_public_snapshot(self) -> dict[str, Any]:
        records = self.__ledger.records()
        return {
            "schema": "kira.shared_person_growth_v3_integration_ledger_snapshot.v1",
            "record_count": len(records),
            "head_record_sha256": records[-1]["record_sha256"] if records else "0" * 64,
            "authority_secret_exposed": False,
            "private_payload_exposed": False,
            "production_pointer_changed": False,
        }

    def __copy__(self) -> None:
        raise TypeError("integration adapters cannot be copied")

    def __deepcopy__(self, memo: object) -> None:
        raise TypeError("integration adapters cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("integration adapters cannot be serialized")


__all__ = [
    "INVENTORY_PATH",
    "GrowthIntegrationError",
    "GrowthIntegrationAuthorityError",
    "GrowthIntegrationRecoveryRequired",
    "IntegrationIdentityHandle",
    "IntegrationReceiptHandle",
    "SharedGrowthV3IntegrationAdapter",
    "inventory_sha256",
    "load_integration_inventory",
    "current_route_coverage_inventory",
    "validate_public_attachment",
]
