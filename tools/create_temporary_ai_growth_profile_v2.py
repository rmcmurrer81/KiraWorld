"""Write one exact, inert V2 shared-growth bundle for a TemporaryAI candidate.

The ordinary creator path is unresolved-only, exclusive-write, readback
verified, and disconnected.  A classified bundle can be built only when the
caller supplies the exact protected controller and its opaque single-use
maturity authority handle; a status string or digest is never sufficient.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.shared_person_growth_capabilities_v2 import (
    GrowthAuthorityError,
    GrowthCapabilityError,
    MaturityAuthorityHandle,
    ProtectedGrowthController,
    build_temporary_creator_attachment,
    validate_temporary_creator_attachment,
)


BUNDLE_SCHEMA = "kira.temporary_creator_growth_bundle.v2"
_CANDIDATE_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,79}$")
_BUNDLE_KEYS = {
    "schema",
    "candidate_id",
    "attachment",
    "maturity_authority",
    "write_contract",
    "bundle_sha256",
}
_MATURITY_AUTHORITY_KEYS = {
    "status",
    "controller_id",
    "classification_receipt_sha256",
    "classification_inferred_by_creator",
    "unresolved_fails_closed",
    "protected_controller_connected_for_classified_build",
}
_WRITE_CONTRACT = {
    "exclusive_new_file_only": True,
    "atomic_create_no_replace": True,
    "readback_verified": True,
    "existing_candidate_files_modified": False,
    "activation_or_assignment_performed": False,
    "private_person_data_copied": False,
    "unknown_private_payload_allowed": False,
}


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _lower_nonzero_sha(value: Any, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
        or value == "0" * 64
    ):
        raise GrowthCapabilityError(f"{field_name} must be nonzero lowercase SHA-256")
    return value


def _exact_keys(value: Any, expected: set[str], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value.keys()) != expected:
        raise GrowthCapabilityError(f"{field_name} exact schema mismatch")
    if any(not isinstance(key, str) for key in value):
        raise GrowthCapabilityError(f"{field_name} keys must be strings")
    return value


def _typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _typed_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _typed_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def build_fresh_creator_bundle(
    *,
    candidate_id: str,
    display_name: str,
    authority_controller: ProtectedGrowthController,
    maturity_authority: MaturityAuthorityHandle | None = None,
    person_id: str | None = None,
    profile_id: str | None = None,
    root_nonce_sha256: str | None = None,
) -> dict[str, Any]:
    if _CANDIDATE_RE.fullmatch(candidate_id) is None:
        raise GrowthCapabilityError("candidate_id must be one canonical TemporaryAI identifier")
    if not isinstance(authority_controller, ProtectedGrowthController):
        raise GrowthAuthorityError("a protected controller is required")
    person_id = person_id or f"person_{secrets.token_hex(16)}"
    profile_id = profile_id or f"growth_{secrets.token_hex(16)}"
    root_nonce_sha256 = root_nonce_sha256 or _sha(secrets.token_bytes(32))
    attachment = build_temporary_creator_attachment(
        candidate_id=candidate_id,
        display_name=display_name,
        person_id=person_id,
        profile_id=profile_id,
        root_nonce_sha256=root_nonce_sha256,
        authority_controller=authority_controller,
        maturity_authority=maturity_authority,
    )
    maturity = attachment["growth_profile"]["maturity"]
    classified = maturity["status"] != "unresolved"
    bundle: dict[str, Any] = {
        "schema": BUNDLE_SCHEMA,
        "candidate_id": candidate_id,
        "attachment": attachment,
        "maturity_authority": {
            "status": maturity["status"],
            "controller_id": authority_controller.controller_id,
            "classification_receipt_sha256": maturity["classification_receipt_sha256"],
            "classification_inferred_by_creator": False,
            "unresolved_fails_closed": not classified,
            "protected_controller_connected_for_classified_build": classified,
        },
        "write_contract": deepcopy(_WRITE_CONTRACT),
    }
    bundle["bundle_sha256"] = _sha(_canonical_bytes(bundle))
    return validate_creator_bundle(bundle, authority_controller=authority_controller)


def validate_creator_bundle(
    value: Mapping[str, Any],
    *,
    authority_controller: ProtectedGrowthController | None = None,
) -> dict[str, Any]:
    bundle = _exact_keys(value, _BUNDLE_KEYS, "creator_bundle")
    if bundle["schema"] != BUNDLE_SCHEMA:
        raise GrowthCapabilityError("creator growth bundle schema mismatch")
    candidate_id = bundle["candidate_id"]
    if not isinstance(candidate_id, str) or _CANDIDATE_RE.fullmatch(candidate_id) is None:
        raise GrowthCapabilityError("creator growth bundle candidate ID is invalid")
    attachment = validate_temporary_creator_attachment(
        bundle["attachment"],
        authority_controller=authority_controller,
    )
    if attachment["candidate_id"] != candidate_id:
        raise GrowthCapabilityError("creator bundle and attachment candidate differ")
    maturity = _exact_keys(
        bundle["maturity_authority"],
        _MATURITY_AUTHORITY_KEYS,
        "maturity_authority",
    )
    profile_maturity = attachment["growth_profile"]["maturity"]
    if maturity["status"] != profile_maturity["status"]:
        raise GrowthCapabilityError("creator bundle maturity status binding mismatch")
    if maturity["controller_id"] != attachment["growth_profile"]["authority_binding"]["controller_id"]:
        raise GrowthCapabilityError("creator bundle controller binding mismatch")
    if maturity["classification_inferred_by_creator"] is not False:
        raise GrowthCapabilityError("Temporary Creator must not infer maturity")
    if maturity["status"] == "unresolved":
        if maturity["classification_receipt_sha256"] is not None:
            raise GrowthCapabilityError("unresolved creator bundle must not claim a receipt")
        if maturity["unresolved_fails_closed"] is not True:
            raise GrowthCapabilityError("unresolved creator bundle did not fail closed")
        if maturity["protected_controller_connected_for_classified_build"] is not False:
            raise GrowthCapabilityError("unresolved bundle falsely claims classified authority")
    elif maturity["status"] in {"confirmed_adult", "non_adult"}:
        receipt = _lower_nonzero_sha(
            maturity["classification_receipt_sha256"],
            "classification_receipt_sha256",
        )
        if receipt != profile_maturity["classification_receipt_sha256"]:
            raise GrowthCapabilityError("creator maturity receipt binding mismatch")
        if maturity["unresolved_fails_closed"] is not False:
            raise GrowthCapabilityError("classified bundle cannot claim unresolved")
        if maturity["protected_controller_connected_for_classified_build"] is not True:
            raise GrowthCapabilityError("classified bundle lacks protected authority truth")
        if authority_controller is None:
            raise GrowthAuthorityError(
                "classified creator bundle validation fails closed without its controller"
            )
    else:
        raise GrowthCapabilityError("creator bundle maturity status is unsupported")
    contract = _exact_keys(bundle["write_contract"], set(_WRITE_CONTRACT), "write_contract")
    if not _typed_equal(dict(contract), _WRITE_CONTRACT):
        raise GrowthCapabilityError("creator write contract boundary drifted")
    digest = _lower_nonzero_sha(bundle["bundle_sha256"], "bundle_sha256")
    unsigned = deepcopy(dict(bundle))
    unsigned.pop("bundle_sha256")
    if _sha(_canonical_bytes(unsigned)) != digest:
        raise GrowthCapabilityError("creator growth bundle hash mismatch")
    return deepcopy(dict(bundle))


def write_bundle_exclusive(
    bundle: Mapping[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
    authority_controller: ProtectedGrowthController | None = None,
) -> Path:
    checked = validate_creator_bundle(
        bundle,
        authority_controller=authority_controller,
    )
    candidate_id = checked["candidate_id"]
    candidate_root = (project_root / "TemporaryAI" / "candidates" / candidate_id).resolve()
    allowed_root = (project_root / "TemporaryAI" / "candidates").resolve()
    try:
        candidate_root.relative_to(allowed_root)
    except ValueError as exc:
        raise GrowthCapabilityError("candidate output escaped TemporaryAI candidates") from exc
    if not candidate_root.is_dir():
        raise FileNotFoundError("exact TemporaryAI candidate directory does not exist")
    output = candidate_root / "shared_person_growth_capabilities_v2.json"
    data = json.dumps(checked, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    encoded = data.encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(output, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            output.unlink()
        except OSError:
            pass
        raise
    readback_bytes = output.read_bytes()
    if readback_bytes != encoded:
        raise GrowthCapabilityError("creator bundle exact-byte readback mismatch")
    observed = json.loads(readback_bytes)
    if observed != checked:
        raise GrowthCapabilityError("creator bundle semantic readback mismatch")
    validate_creator_bundle(
        observed,
        authority_controller=authority_controller,
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create one unresolved, inactive V2 shared-growth profile for an existing "
            "TemporaryAI candidate. Classified creation is intentionally unavailable in CLI."
        )
    )
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()
    authority_secret = secrets.token_bytes(32)
    controller = ProtectedGrowthController(
        controller_id=f"creator_{secrets.token_hex(12)}",
        authority_secret=authority_secret,
    )
    bundle = build_fresh_creator_bundle(
        candidate_id=args.candidate_id,
        display_name=args.display_name,
        authority_controller=controller,
    )
    output = write_bundle_exclusive(
        bundle,
        authority_controller=controller,
    )
    print(
        json.dumps(
            {
                "status": "STATIC_V2_CANDIDATE_WRITTEN_INACTIVE_UNRESOLVED",
                "output": output.relative_to(PROJECT_ROOT).as_posix(),
                "bundle_sha256": bundle["bundle_sha256"],
                "classified_creation_available_in_cli": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
