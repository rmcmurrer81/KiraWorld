"""Strict evidence gates for staged 3D embodiment tests.

The Home World runtime can display poses and generated hand props before the
underlying interaction is physically implemented.  Those previews are useful
for development, but they are not evidence that an avatar walked to a target,
picked an object up, used it, or put it back.  This module keeps test reports
honest by requiring independent location, transition, support, and hand-contact
evidence before a capability may pass.

Restroom snapshots are deliberately metadata-only.  The evaluator checks the
private-room boundary and fixture/action state without retaining intimate
details or screenshots.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable


CAPABILITIES = (
    "restroom_private_use",
    "eat_food",
    "drink",
    "sit_couch",
    "lie_bed",
    "tablet_pickup",
    "tablet_putdown",
    "tablet_read",
    "tablet_online_lookup",
    "tablet_note_writing",
)

HAND_CONTACT_MAX_METERS = 0.20
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GROUNDED_TRANSITION_MODES = {"walk", "grounded_walk", "physics_walk", "reach", "manipulation"}
WALK_TRANSITION_MODES = {"walk", "grounded_walk", "physics_walk"}
WALK_MIN_DISTANCE_METERS = 0.05
MANIPULATION_MIN_PATH_METERS = 0.001
TRANSITION_CAPTURE_BASES = {
    "runtime_physics_trace",
    "browser_runtime_trace",
    "motion_controller_trace",
    "scene_observer_trace",
}
EMBODIMENT_PROJECT_ROOT = Path(__file__).resolve().parents[1]
EMBODIMENT_APPROVAL_REGISTRY_PATH = (
    EMBODIMENT_PROJECT_ROOT
    / "Data"
    / "embodiment"
    / "policies"
    / "body_runtime_approval_registry.json"
)
# Updating this owner registry requires a matching reviewed code change.  A
# caller cannot turn a newly written JSON file into authority by supplying its
# hash in a runtime snapshot.
EMBODIMENT_APPROVAL_REGISTRY_PINNED_SHA256 = (
    "3a5bef38282b763a90ae8fe5932ab3151495ad8ba39fec9f0e60a00f6244ab94"
)
EMBODIMENT_APPROVAL_REGISTRY_TYPE = (
    "owner_controlled_embodiment_body_runtime_approval_registry"
)
EMBODIMENT_APPROVAL_TYPE = "embodiment_body_runtime_approval"
EMBODIMENT_APPROVAL_REVIEWER_ID = "robert_mcmurrer"
EMBODIMENT_MATURITY_CLASSES = {
    "adult",
    "non_adult_doll_safe",
}
MAX_APPROVAL_JSON_BYTES = 1024 * 1024


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains(value: Any, terms: Iterable[str]) -> bool:
    text = _text(value)
    return any(term in text for term in terms)


def _append(reasons: list[str], condition: bool, reason: str) -> None:
    if not condition:
        reasons.append(reason)


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stream_sha256(path: Path) -> str:
    """Hash the bytes on disk without trusting sidecar or caller claims."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_artifact_path(value: Any, label: str) -> tuple[Path | None, str, list[str]]:
    """Resolve one canonical project-relative regular file, fail closed."""

    raw = str(value or "").strip()
    if not raw:
        return None, "", [f"{label} path is missing"]
    supplied = Path(raw)
    if supplied.is_absolute():
        return None, "", [f"{label} path must be project-relative"]
    try:
        root = EMBODIMENT_PROJECT_ROOT.resolve(strict=True)
        candidate = (root / supplied).resolve(strict=True)
    except (OSError, RuntimeError):
        return None, "", [f"{label} artifact is missing or unreadable"]
    try:
        relative = candidate.relative_to(root).as_posix()
    except ValueError:
        return None, "", [f"{label} artifact is outside the fixed project root"]
    # Reject aliases containing '..' or other alternate spellings.  All three
    # layers (snapshot, approval, registry) must bind the same concrete name.
    if supplied.as_posix() != relative:
        return None, relative, [f"{label} path is not canonical"]
    if not candidate.is_file():
        return None, relative, [f"{label} artifact is not a regular file"]
    return candidate, relative, []


def _read_small_json(path: Path, label: str) -> tuple[dict[str, Any], str, list[str]]:
    failures: list[str] = []
    try:
        if path.stat().st_size > MAX_APPROVAL_JSON_BYTES:
            return {}, "", [f"{label} is too large"]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        value = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}, "", [f"{label} is unreadable or invalid JSON"]
    if not isinstance(value, dict):
        failures.append(f"{label} root is not an object")
        value = {}
    return value, digest, failures


def load_embodiment_approval_registry() -> dict[str, Any]:
    """Load the fixed, code-hash-pinned owner registry.

    The production registry intentionally starts empty.  Missing, malformed,
    unpinned, or edited registries expose no entries, so live body activation
    remains default-deny until Robert performs an explicit reviewed update.
    """

    failures: list[str] = []
    value: dict[str, Any] = {}
    actual_hash = ""
    try:
        root = EMBODIMENT_PROJECT_ROOT.resolve(strict=True)
        path = EMBODIMENT_APPROVAL_REGISTRY_PATH.resolve(strict=True)
        path.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        path = EMBODIMENT_APPROVAL_REGISTRY_PATH
        failures.append("owner approval registry is missing or outside the fixed project root")
    else:
        if not path.is_file():
            failures.append("owner approval registry is not a regular file")
        else:
            value, actual_hash, read_failures = _read_small_json(path, "owner approval registry")
            failures.extend(read_failures)

    pinned_hash = str(EMBODIMENT_APPROVAL_REGISTRY_PINNED_SHA256 or "").lower()
    if not SHA256_RE.fullmatch(pinned_hash):
        failures.append("owner approval registry code-pinned hash is invalid")
    elif actual_hash != pinned_hash:
        failures.append("owner approval registry does not match its code-pinned hash")

    entries: list[dict[str, Any]] = []
    expected_policy = {
        "default": "deny",
        "callerSuppliedHashesAreAuthority": False,
        "requireConcreteArtifactBytes": True,
        "requireExactApprovalArtifactSha256": True,
        "requireExactBodyRigIdentityMaturityBindings": True,
        "currentApprovedBodies": len(value.get("entries") or [])
        if isinstance(value.get("entries"), list)
        else -1,
    }
    if actual_hash:
        if value.get("schemaVersion") != 1:
            failures.append("owner approval registry schema version is invalid")
        if value.get("registryType") != EMBODIMENT_APPROVAL_REGISTRY_TYPE:
            failures.append("owner approval registry type is invalid")
        if value.get("ownerId") != EMBODIMENT_APPROVAL_REVIEWER_ID:
            failures.append("owner approval registry owner is invalid")
        if value.get("status") != "active_fail_closed":
            failures.append("owner approval registry status is invalid")
        if value.get("policy") != expected_policy:
            failures.append("owner approval registry policy is invalid")
        raw_entries = value.get("entries")
        if not isinstance(raw_entries, list):
            failures.append("owner approval registry entries are missing")
        else:
            seen_approval_hashes: set[str] = set()
            required_text = (
                "approvalId",
                "approvedAt",
                "approvalArtifactPath",
                "actorId",
                "subjectId",
                "bodyAssetPath",
                "rigArtifactPath",
            )
            required_hashes = (
                "approvalArtifactSha256",
                "bodyAssetSha256",
                "rigSha256",
            )
            for index, raw_entry in enumerate(raw_entries):
                prefix = f"owner approval registry entry {index}"
                if not isinstance(raw_entry, dict):
                    failures.append(f"{prefix} is not an object")
                    continue
                if raw_entry.get("status") != "approved" or raw_entry.get("ownerApproved") is not True:
                    failures.append(f"{prefix} is not owner-approved")
                if raw_entry.get("reviewerId") != EMBODIMENT_APPROVAL_REVIEWER_ID:
                    failures.append(f"{prefix} reviewer is invalid")
                if any(not str(raw_entry.get(key) or "").strip() for key in required_text):
                    failures.append(f"{prefix} has a missing identity/path field")
                hashes = {key: str(raw_entry.get(key) or "").lower() for key in required_hashes}
                if any(not SHA256_RE.fullmatch(value) for value in hashes.values()):
                    failures.append(f"{prefix} has an invalid artifact hash")
                approval_hash = hashes["approvalArtifactSha256"]
                if approval_hash in seen_approval_hashes:
                    failures.append("owner approval registry has a duplicate approval artifact")
                seen_approval_hashes.add(approval_hash)
                if raw_entry.get("maturityClass") not in EMBODIMENT_MATURITY_CLASSES:
                    failures.append(f"{prefix} maturity class is invalid")
                entries.append(raw_entry)

    failures = list(dict.fromkeys(failures))
    return {
        "valid": not failures,
        "path": str(EMBODIMENT_APPROVAL_REGISTRY_PATH),
        "sha256": actual_hash or None,
        "pinnedSha256": pinned_hash or None,
        "entries": entries if not failures else [],
        "failures": failures,
        "default": "deny",
    }


def _body_approval_reasons(
    body: dict[str, Any],
    *,
    actor_id: str,
) -> tuple[list[str], dict[str, str]]:
    """Validate real body/rig/approval bytes and the independent owner registry."""

    reasons: list[str] = []
    subject_id = str(body.get("subjectId") or "").strip()
    maturity_class = str(body.get("maturityClass") or "").strip()
    if body.get("approved") is not True:
        reasons.append("body evidence is not marked approved")
    if not actor_id or body.get("actorId") != actor_id:
        reasons.append("body evidence actor does not match the transition actor")
    if not subject_id:
        reasons.append("body evidence subject identity is missing")
    if maturity_class not in EMBODIMENT_MATURITY_CLASSES:
        reasons.append("body evidence maturity class is missing or invalid")

    body_path, body_relative, path_failures = _resolve_artifact_path(
        body.get("bodyAssetPath"), "body asset"
    )
    reasons.extend(path_failures)
    rig_path, rig_relative, path_failures = _resolve_artifact_path(
        body.get("rigArtifactPath"), "rig"
    )
    reasons.extend(path_failures)
    approval_path, approval_relative, path_failures = _resolve_artifact_path(
        body.get("approvalArtifactPath"), "body approval"
    )
    reasons.extend(path_failures)

    claimed_body_sha = str(body.get("bodyAssetSha256") or "").lower()
    claimed_rig_sha = str(body.get("rigSha256") or "").lower()
    claimed_approval_sha = str(body.get("approvalArtifactSha256") or "").lower()
    for label, claimed in (
        ("body asset", claimed_body_sha),
        ("rig", claimed_rig_sha),
        ("body approval", claimed_approval_sha),
    ):
        if not SHA256_RE.fullmatch(claimed):
            reasons.append(f"{label} SHA-256 is missing or invalid")

    actual_body_sha = ""
    actual_rig_sha = ""
    if body_path is not None:
        try:
            actual_body_sha = _stream_sha256(body_path)
        except OSError:
            reasons.append("body asset bytes could not be hashed")
        if actual_body_sha and claimed_body_sha != actual_body_sha:
            reasons.append("body asset SHA-256 does not match the concrete file bytes")
    if rig_path is not None:
        try:
            actual_rig_sha = _stream_sha256(rig_path)
        except OSError:
            reasons.append("rig bytes could not be hashed")
        if actual_rig_sha and claimed_rig_sha != actual_rig_sha:
            reasons.append("rig SHA-256 does not match the concrete file bytes")

    approval: dict[str, Any] = {}
    actual_approval_sha = ""
    if approval_path is not None:
        approval, actual_approval_sha, read_failures = _read_small_json(
            approval_path, "body approval artifact"
        )
        reasons.extend(read_failures)
        if actual_approval_sha and claimed_approval_sha != actual_approval_sha:
            reasons.append("body approval SHA-256 does not match the concrete file bytes")

    expected_approval = {
        "schemaVersion": 1,
        "approvalType": EMBODIMENT_APPROVAL_TYPE,
        "status": "approved",
        "reviewerId": EMBODIMENT_APPROVAL_REVIEWER_ID,
        "actorId": actor_id,
        "subjectId": subject_id,
        "maturityClass": maturity_class,
        "bodyAssetPath": body_relative,
        "bodyAssetSha256": actual_body_sha,
        "rigArtifactPath": rig_relative,
        "rigSha256": actual_rig_sha,
    }
    if approval:
        for key, expected in expected_approval.items():
            if approval.get(key) != expected:
                reasons.append(f"body approval artifact does not bind {key}")
        if not str(approval.get("approvalId") or "").strip():
            reasons.append("body approval artifact has no approval identity")
        if not str(approval.get("approvedAt") or "").strip():
            reasons.append("body approval artifact has no approval timestamp")

    registry = load_embodiment_approval_registry()
    if not registry["valid"]:
        reasons.extend(registry["failures"])
    else:
        expected_entry = {
            "status": "approved",
            "ownerApproved": True,
            "reviewerId": EMBODIMENT_APPROVAL_REVIEWER_ID,
            "approvalId": approval.get("approvalId"),
            "approvedAt": approval.get("approvedAt"),
            "approvalArtifactPath": approval_relative,
            "approvalArtifactSha256": actual_approval_sha,
            "actorId": actor_id,
            "subjectId": subject_id,
            "maturityClass": maturity_class,
            "bodyAssetPath": body_relative,
            "bodyAssetSha256": actual_body_sha,
            "rigArtifactPath": rig_relative,
            "rigSha256": actual_rig_sha,
        }
        if not any(
            all(entry.get(key) == expected for key, expected in expected_entry.items())
            for entry in registry["entries"]
        ):
            reasons.append("exact body approval and bindings are not listed in the owner registry")

    bindings = {
        "subjectId": subject_id,
        "maturityClass": maturity_class,
        "bodyAssetPath": body_relative,
        "bodyAssetSha256": actual_body_sha,
        "rigArtifactPath": rig_relative,
        "rigSha256": actual_rig_sha,
        "approvalArtifactPath": approval_relative,
        "approvalArtifactSha256": actual_approval_sha,
    }
    return list(dict.fromkeys(reasons)), bindings


def transition_trace_sha256(transition: dict[str, Any]) -> str:
    """Hash the movement fields while excluding the claimed digest itself."""

    fields = {
        key: transition.get(key)
        for key in (
            "actorId",
            "observerId",
            "captureBasis",
            "mode",
            "teleported",
            "collisionBlocked",
            "distanceMeters",
            "pathSampleCount",
            "startedAt",
            "endedAt",
            "startPosition",
            "endPosition",
            "path",
        )
    }
    return _canonical_sha256(fields)


def embodiment_binding_sha256(binding: dict[str, Any]) -> str:
    return _canonical_sha256({key: value for key, value in binding.items() if key != "bindingSha256"})


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _xyz(value: Any) -> tuple[float, float, float] | None:
    point = _dict(value)
    if not all(_finite_number(point.get(axis)) for axis in ("x", "y", "z")):
        return None
    return float(point["x"]), float(point["y"]), float(point["z"])


def _transition_reasons(snapshot: dict[str, Any]) -> list[str]:
    transition = _dict(snapshot.get("transitionEvidence"))
    reasons: list[str] = []
    if not transition:
        return ["required transition evidence is missing"]
    mode = _text(transition.get("mode"))
    teleported = transition.get("teleported") is True or mode in {
        "teleport",
        "debug_position_set",
        "direct_position_copy",
        "scripted_snap",
    }
    if teleported:
        reasons.append("target was reached by teleport/direct placement, not grounded movement")
    if transition.get("teleported") is not False:
        reasons.append("transition must explicitly attest that teleporting was false")
    if mode not in GROUNDED_TRANSITION_MODES:
        reasons.append("transition mode is not an approved grounded movement mode")
    if _text(transition.get("captureBasis")) not in TRANSITION_CAPTURE_BASES:
        reasons.append("transition capture basis is missing or untrusted")
    actor_id = str(transition.get("actorId") or "").strip()
    observer_id = str(transition.get("observerId") or "").strip()
    if not actor_id:
        reasons.append("transition has no actor identity")
    if not observer_id or observer_id == actor_id:
        reasons.append("transition lacks an independent observer identity")
    distance = transition.get("distanceMeters")
    if not _finite_number(distance) or float(distance) < 0:
        reasons.append("transition distance is missing, negative, or non-finite")
    path = _list(transition.get("path"))
    samples = transition.get("pathSampleCount")
    if not isinstance(samples, int) or isinstance(samples, bool) or samples != len(path) or len(path) < 2:
        reasons.append("movement path must contain matching start/end samples")
    points: list[tuple[float, float, float]] = []
    times: list[float] = []
    for sample in path:
        point = _xyz(sample)
        timestamp = _dict(sample).get("t")
        if point is None or not _finite_number(timestamp):
            reasons.append("movement path contains an invalid position or timestamp")
            break
        points.append(point)
        times.append(float(timestamp))
    if len(times) == len(path) and any(right <= left for left, right in zip(times, times[1:])):
        reasons.append("movement path timestamps are not strictly increasing")
    started = transition.get("startedAt")
    ended = transition.get("endedAt")
    if not _finite_number(started) or not _finite_number(ended) or float(ended) <= float(started or 0):
        reasons.append("transition start/end timestamps are missing or invalid")
    elif times and (abs(times[0] - float(started)) > 1e-6 or abs(times[-1] - float(ended)) > 1e-6):
        reasons.append("transition timestamps do not bind the path endpoints")
    start_position = _xyz(transition.get("startPosition"))
    end_position = _xyz(transition.get("endPosition"))
    if start_position is None or end_position is None:
        reasons.append("transition start/end positions are missing")
    elif points and (start_position != points[0] or end_position != points[-1]):
        reasons.append("transition positions do not bind the path endpoints")
    measured = 0.0
    endpoint_displacement = 0.0
    if points and _finite_number(distance):
        measured = sum(
            math.dist(left, right)
            for left, right in zip(points, points[1:])
        )
        endpoint_displacement = math.dist(points[0], points[-1])
        if not math.isfinite(measured) or not math.isfinite(endpoint_displacement):
            reasons.append("sampled movement distance is non-finite")
        tolerance = max(0.05, measured * 0.10)
        if not math.isfinite(measured) or abs(measured - float(distance)) > tolerance:
            reasons.append("reported transition distance does not match the sampled path")
        if mode in WALK_TRANSITION_MODES:
            if (
                float(distance) < WALK_MIN_DISTANCE_METERS
                or measured < WALK_MIN_DISTANCE_METERS
                or endpoint_displacement < WALK_MIN_DISTANCE_METERS
            ):
                reasons.append(
                    "walk transition has no meaningful nonzero displacement and path"
                )
        elif mode in {"reach", "manipulation"} and (
            float(distance) < MANIPULATION_MIN_PATH_METERS
            or measured < MANIPULATION_MIN_PATH_METERS
        ):
            reasons.append("reach/manipulation transition has no measured movement path")
    if transition.get("collisionBlocked") is not False:
        reasons.append("movement route lacks an explicit collision-clear result")
    claimed_trace = str(transition.get("traceSha256") or "").lower()
    actual_trace = transition_trace_sha256(transition)
    if not SHA256_RE.fullmatch(claimed_trace) or claimed_trace != actual_trace:
        reasons.append("transition trace hash is missing or mismatched")

    body = _dict(snapshot.get("bodyEvidence"))
    binding = _dict(snapshot.get("evidenceBinding"))
    approval_reasons, body_bindings = _body_approval_reasons(body, actor_id=actor_id)
    reasons.extend(approval_reasons)
    required_binding = {
        "actorId": actor_id,
        "observerId": observer_id,
        "transitionTraceSha256": actual_trace,
        **body_bindings,
    }
    if any(binding.get(key) != value for key, value in required_binding.items()):
        reasons.append("evidence binding does not match transition/body identities")
    claimed_binding = str(binding.get("bindingSha256") or "").lower()
    if not SHA256_RE.fullmatch(claimed_binding) or claimed_binding != embodiment_binding_sha256(binding):
        reasons.append("evidence binding hash is missing or mismatched")
    return reasons


def _finger_contact(snapshot: dict[str, Any], held: dict[str, Any]) -> dict[str, Any]:
    direct = _dict(held.get("handContact"))
    if direct:
        return direct
    pickup = _dict(held.get("pickupEvidence"))
    direct = _dict(pickup.get("handContact"))
    if direct:
        return direct
    kind = _text(held.get("kind"))
    for item in _list(snapshot.get("fingerContacts")):
        contact = _dict(item)
        if not contact:
            continue
        if kind and _contains(contact.get("kind") or contact.get("object"), (kind,)):
            return contact
    return {}


def _contact_is_touching(contact: dict[str, Any]) -> bool:
    if not contact:
        return False
    if contact.get("touching") is False:
        return False
    distance = contact.get("distance")
    if isinstance(distance, (int, float)):
        return _finite_number(distance) and 0 <= float(distance) <= HAND_CONTACT_MAX_METERS
    return contact.get("touching") is True


def _held_prop_reasons(
    snapshot: dict[str, Any],
    allowed_kinds: Iterable[str],
) -> list[str]:
    held = _dict(snapshot.get("activeHeldProp"))
    reasons: list[str] = []
    allowed = {_text(item) for item in allowed_kinds}
    _append(reasons, bool(held), "no held prop is reported")
    if not held:
        return reasons
    _append(reasons, _text(held.get("kind")) in allowed, "held prop kind does not match the capability")
    _append(reasons, held.get("grounded") is True, "held prop lacks grounded pickup provenance")
    _append(reasons, held.get("syntheticPreview") is not True, "held prop is a generated preview, not a picked-up world object")
    _append(
        reasons,
        bool(held.get("sourcePropId") or _dict(held.get("pickupEvidence")).get("sourcePropId")),
        "held prop has no source world-object identity",
    )
    _append(
        reasons,
        held.get("sourceRemovedOrHidden") is True
        or _dict(held.get("pickupEvidence")).get("sourceRemovedOrHidden") is True,
        "source prop remains independently present, so object continuity is unproven",
    )
    _append(reasons, _contact_is_touching(_finger_contact(snapshot, held)), "no touching hand/finger contact is recorded")
    return reasons


def _posture_reasons(snapshot: dict[str, Any], posture: str, surfaces: Iterable[str]) -> list[str]:
    state = _dict(snapshot.get("postureState"))
    support = _dict(snapshot.get("supportState"))
    reasons: list[str] = []
    _append(reasons, _text(state.get("posture")) == posture, f"body posture is not {posture}")
    surface = _text(state.get("surface") or support.get("id"))
    _append(reasons, _contains(surface, surfaces), "posture has no matching physical support surface")
    _append(reasons, support.get("supported") is True, "body support state is not grounded")
    _append(reasons, support.get("falling") is not True, "body support reports falling")
    reasons.extend(_transition_reasons(snapshot))
    return reasons


def _action_truth_reasons(snapshot: dict[str, Any], truth_id: str) -> list[str]:
    by_action = _dict(snapshot.get("activityTruthByAction"))
    truth = _dict(by_action.get(truth_id))
    if not truth:
        return [f"no runtime truth record exists for {truth_id}"]
    return [] if truth.get("grounded") is True else [
        _text(truth.get("reason")) or f"runtime truth did not ground {truth_id}"
    ]


def evaluate_capability(capability: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one staged capability without mutating runtime state."""
    if capability not in CAPABILITIES:
        raise ValueError(f"Unsupported embodiment capability: {capability}")
    snapshot = _dict(snapshot)
    reasons: list[str] = []
    action = _text(snapshot.get("action") or snapshot.get("activeAction"))
    place = _dict(snapshot.get("place"))

    if snapshot.get("activeModelLoaded") is not True and snapshot.get("bodyPresent") is not True:
        reasons.append("no loaded 3D body is reported")

    if capability == "restroom_private_use":
        privacy = _dict(snapshot.get("privacyState"))
        fixture = _dict(snapshot.get("fixtureEvidence"))
        _append(reasons, _contains(place.get("label") or place.get("summary"), ("bathroom", "restroom")), "body is not confirmed inside a restroom")
        _append(reasons, place.get("inside") is True, "restroom boundary does not confirm the body is inside")
        _append(reasons, _contains(action, ("use_bathroom", "restroom_use")), "runtime action is not restroom use")
        _append(reasons, _contains(fixture.get("kind"), ("toilet",)), "no nearby toilet fixture evidence is reported")
        distance = fixture.get("distanceMeters")
        _append(reasons, _finite_number(distance) and 0 <= float(distance) <= 1.0, "body is not within the fixture interaction zone")
        _append(reasons, privacy.get("active") is True, "private-room state is not active")
        _append(reasons, privacy.get("observersAllowed") is False, "restroom session still permits observers")
        _append(reasons, _text(privacy.get("logScope")) in {"none", "metadata_only"}, "restroom log scope is not metadata-only")
        _append(reasons, snapshot.get("anatomyAnimationSupported") is True, "body has no approved restroom anatomy/animation support")
        reasons.extend(_transition_reasons(snapshot))

    elif capability == "eat_food":
        _append(reasons, _contains(action, ("eat", "snack", "meal")), "runtime action is not eating")
        reasons.extend(_held_prop_reasons(snapshot, ("food", "fruit", "snack")))
        reasons.extend(_action_truth_reasons(snapshot, "eat_food"))
        _append(reasons, _dict(snapshot.get("consumptionEvidence")).get("mouthContact") is True, "no food-to-mouth contact is recorded")
        _append(reasons, snapshot.get("anatomyAnimationSupported") is True, "body has no approved eating anatomy/animation support")
        reasons.extend(_transition_reasons(snapshot))

    elif capability == "drink":
        _append(reasons, _contains(action, ("drink", "water", "milk", "coffee", "tea")), "runtime action is not drinking")
        reasons.extend(_held_prop_reasons(snapshot, ("cup", "coffee_cup", "bottle", "milk")))
        truth_key = "drink_coffee" if _contains(action, ("coffee", "tea")) else "drink"
        reasons.extend(_action_truth_reasons(snapshot, truth_key))
        _append(reasons, _dict(snapshot.get("consumptionEvidence")).get("mouthContact") is True, "no drink-to-mouth contact is recorded")
        _append(reasons, snapshot.get("anatomyAnimationSupported") is True, "body has no approved drinking anatomy/animation support")
        reasons.extend(_transition_reasons(snapshot))

    elif capability == "sit_couch":
        _append(reasons, _contains(action, ("sit",)), "runtime action is not sitting")
        reasons.extend(_posture_reasons(snapshot, "sit", ("couch", "sofa")))

    elif capability == "lie_bed":
        _append(reasons, _contains(action, ("lie", "bed", "sleep", "rest")), "runtime action is not lying on the bed")
        reasons.extend(_posture_reasons(snapshot, "lie", ("bed", "mattress")))

    elif capability == "tablet_pickup":
        _append(reasons, _contains(action, ("pick", "tablet", "read", "notes", "research")), "runtime action does not describe tablet pickup/use")
        reasons.extend(_held_prop_reasons(snapshot, ("tablet",)))
        reasons.extend(_transition_reasons(snapshot))

    elif capability == "tablet_putdown":
        held = _dict(snapshot.get("activeHeldProp"))
        putdown = _dict(snapshot.get("putdownEvidence"))
        _append(reasons, not held, "tablet is still reported in hand")
        _append(reasons, _contains(putdown.get("kind"), ("tablet",)), "no tablet put-down event is reported")
        _append(reasons, bool(putdown.get("sourcePropId")), "put-down event has no continuous tablet identity")
        _append(reasons, _contains(putdown.get("surface"), ("coffee_table", "coffee table")), "tablet was not grounded on the coffee table")
        _append(reasons, putdown.get("objectVisibleAtSurface") is True, "tablet is not visibly restored at the surface")
        _append(reasons, _contact_is_touching(_dict(putdown.get("handContact"))), "put-down has no hand-contact evidence")
        reasons.extend(_transition_reasons(snapshot))

    elif capability in {"tablet_read", "tablet_online_lookup", "tablet_note_writing"}:
        reasons.extend(_held_prop_reasons(snapshot, ("tablet",)))
        reasons.extend(_action_truth_reasons(snapshot, "use_phone"))
        content = _dict(snapshot.get("contentEvidence"))
        if capability == "tablet_read":
            _append(reasons, _contains(action, ("read", "ebook", "book")), "runtime action is not tablet reading")
            _append(reasons, _text(content.get("kind")) in {"local_book", "ebook", "reading_chunk"}, "no opened book/reading chunk is recorded")
            _append(reasons, bool(content.get("sourceId") or content.get("sourcePath")), "reading evidence has no source identity")
            _append(reasons, bool(content.get("page") or content.get("chunkId") or content.get("progress")), "reading evidence has no page/chunk progress")
        elif capability == "tablet_online_lookup":
            _append(reasons, _contains(action, ("online", "lookup", "research", "web", "browse")), "runtime action is not an online lookup")
            _append(reasons, _text(content.get("kind")) == "online_research", "no online research record is attached")
            _append(reasons, bool(_list(content.get("sourcesChecked"))), "online lookup has no checked source URLs")
            _append(reasons, bool(content.get("researchNoteId")), "online lookup did not save a research-note identity")
        else:
            _append(reasons, _contains(action, ("write", "note", "type")), "runtime action is not note writing")
            _append(reasons, _text(content.get("kind")) in {"note", "creative_writing"}, "no note/creative-writing record is attached")
            _append(reasons, bool(content.get("noteId") or content.get("savedPath")), "note writing has no saved note identity")
            _append(reasons, content.get("saved") is True, "note was not confirmed saved")
        reasons.extend(_transition_reasons(snapshot))

    reasons = list(dict.fromkeys(reason for reason in reasons if reason))
    return {
        "capability": capability,
        "status": "passed" if not reasons else "blocked",
        "passed": not reasons,
        "reasons": reasons,
    }


def evaluate_capability_series(snapshot_by_capability: dict[str, Any]) -> dict[str, Any]:
    results = [
        evaluate_capability(capability, _dict(snapshot_by_capability.get(capability)))
        for capability in CAPABILITIES
    ]
    return {
        "status": "passed" if all(item["passed"] for item in results) else "blocked",
        "passed_count": sum(1 for item in results if item["passed"]),
        "blocked_count": sum(1 for item in results if not item["passed"]),
        "results": results,
    }


def redact_private_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return safe metadata for a restroom result, never intimate content."""
    source = deepcopy(_dict(snapshot))
    redacted = {
        "activeModelLoaded": bool(source.get("activeModelLoaded") or source.get("bodyPresent")),
        "action": source.get("action") or source.get("activeAction") or "",
        "place": {"category": "private_room", "inside": bool(_dict(source.get("place")).get("inside"))},
        "privacyState": {
            "active": _dict(source.get("privacyState")).get("active"),
            "observersAllowed": _dict(source.get("privacyState")).get("observersAllowed"),
            "logScope": _dict(source.get("privacyState")).get("logScope"),
        },
        "fixtureEvidence": {
            "kind": _dict(source.get("fixtureEvidence")).get("kind"),
            "distanceBand": "within_interaction_zone"
            if isinstance(_dict(source.get("fixtureEvidence")).get("distanceMeters"), (int, float))
            and 0 <= _dict(source.get("fixtureEvidence")).get("distanceMeters") <= 1.0
            else "outside_interaction_zone",
        },
        "anatomyAnimationSupported": source.get("anatomyAnimationSupported") is True,
        "detailsRedacted": True,
    }
    return redacted
