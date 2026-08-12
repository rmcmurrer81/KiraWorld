"""Create one inert, fresh shared-growth profile for a TemporaryAI candidate.

This append-only successor does not alter the historical Temporary Creator.
It writes one new, exclusive capability document after an exact candidate is
created.  It never activates the candidate, calls a model, copies another
person's state, or grants maturity.  Any maturity status other than unresolved
requires an externally produced exact classification receipt digest.
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

from Core.shared_person_growth_capabilities_v1 import (
    MATURITY_STATUSES,
    GrowthCapabilityError,
    build_temporary_creator_attachment,
    validate_temporary_creator_attachment,
)


BUNDLE_SCHEMA = "kira.temporary_creator_growth_bundle.v1"
_CANDIDATE_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,79}$")


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


def _lower_sha(value: Any, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise GrowthCapabilityError(f"{field_name} must be lowercase SHA-256")
    return value


def build_fresh_creator_bundle(
    *,
    candidate_id: str,
    display_name: str,
    maturity_status: str = "unresolved",
    maturity_classification_receipt_sha256: str = "",
    person_id: str | None = None,
    profile_id: str | None = None,
    root_nonce_sha256: str | None = None,
) -> dict[str, Any]:
    if _CANDIDATE_RE.fullmatch(candidate_id) is None:
        raise GrowthCapabilityError("candidate_id must be one canonical TemporaryAI identifier")
    if maturity_status not in MATURITY_STATUSES:
        raise GrowthCapabilityError("maturity_status is unsupported")
    if maturity_status == "unresolved":
        if maturity_classification_receipt_sha256:
            raise GrowthCapabilityError("unresolved maturity must not claim a classification receipt")
    else:
        maturity_classification_receipt_sha256 = _lower_sha(
            maturity_classification_receipt_sha256,
            "maturity_classification_receipt_sha256",
        )
    person_id = person_id or f"person_{secrets.token_hex(16)}"
    profile_id = profile_id or f"growth_{secrets.token_hex(16)}"
    root_nonce_sha256 = root_nonce_sha256 or _sha(secrets.token_bytes(32))
    attachment = build_temporary_creator_attachment(
        candidate_id=candidate_id,
        display_name=display_name,
        person_id=person_id,
        profile_id=profile_id,
        root_nonce_sha256=root_nonce_sha256,
        maturity_status=maturity_status,
    )
    bundle: dict[str, Any] = {
        "schema": BUNDLE_SCHEMA,
        "candidate_id": candidate_id,
        "attachment": attachment,
        "maturity_authority": {
            "status": maturity_status,
            "classification_inferred_by_creator": False,
            "classification_receipt_sha256": (
                maturity_classification_receipt_sha256 or None
            ),
            "unresolved_fails_closed": maturity_status == "unresolved",
        },
        "write_contract": {
            "exclusive_new_file_only": True,
            "existing_candidate_files_modified": False,
            "activation_or_assignment_performed": False,
            "private_person_data_copied": False,
        },
    }
    bundle["bundle_sha256"] = _sha(_canonical_bytes(bundle))
    validate_creator_bundle(bundle)
    return bundle


def validate_creator_bundle(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema") != BUNDLE_SCHEMA:
        raise GrowthCapabilityError("creator growth bundle schema mismatch")
    candidate_id = value.get("candidate_id")
    if not isinstance(candidate_id, str) or _CANDIDATE_RE.fullmatch(candidate_id) is None:
        raise GrowthCapabilityError("creator growth bundle candidate ID is invalid")
    attachment = validate_temporary_creator_attachment(value.get("attachment"))
    if attachment["candidate_id"] != candidate_id:
        raise GrowthCapabilityError("creator bundle and attachment candidate differ")
    maturity = value.get("maturity_authority")
    if not isinstance(maturity, Mapping):
        raise GrowthCapabilityError("creator bundle maturity authority is missing")
    status = maturity.get("status")
    if status != attachment["growth_profile"]["maturity"]["status"]:
        raise GrowthCapabilityError("creator bundle maturity binding mismatch")
    receipt = maturity.get("classification_receipt_sha256")
    if status == "unresolved":
        if receipt is not None or maturity.get("unresolved_fails_closed") is not True:
            raise GrowthCapabilityError("unresolved maturity did not fail closed")
    elif status in {"confirmed_adult", "non_adult"}:
        _lower_sha(receipt, "classification_receipt_sha256")
    else:
        raise GrowthCapabilityError("creator bundle maturity status is unsupported")
    contract = value.get("write_contract")
    if not isinstance(contract, Mapping):
        raise GrowthCapabilityError("creator bundle write contract is missing")
    if contract.get("exclusive_new_file_only") is not True:
        raise GrowthCapabilityError("creator bundle is not exclusive-write only")
    for field in (
        "existing_candidate_files_modified",
        "activation_or_assignment_performed",
        "private_person_data_copied",
    ):
        if contract.get(field) is not False:
            raise GrowthCapabilityError("creator bundle crossed a forbidden write boundary")
    digest = _lower_sha(value.get("bundle_sha256"), "bundle_sha256")
    unsigned = deepcopy(dict(value))
    unsigned.pop("bundle_sha256", None)
    if _sha(_canonical_bytes(unsigned)) != digest:
        raise GrowthCapabilityError("creator growth bundle hash mismatch")
    return deepcopy(dict(value))


def write_bundle_exclusive(
    bundle: Mapping[str, Any], *, project_root: Path = PROJECT_ROOT
) -> Path:
    checked = validate_creator_bundle(bundle)
    candidate_id = checked["candidate_id"]
    candidate_root = (project_root / "TemporaryAI" / "candidates" / candidate_id).resolve()
    allowed_root = (project_root / "TemporaryAI" / "candidates").resolve()
    try:
        candidate_root.relative_to(allowed_root)
    except ValueError as exc:
        raise GrowthCapabilityError("candidate output escaped TemporaryAI candidates") from exc
    if not candidate_root.is_dir():
        raise FileNotFoundError("exact TemporaryAI candidate directory does not exist")
    output = candidate_root / "shared_person_growth_capabilities_v1.json"
    data = json.dumps(checked, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
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
    observed = json.loads(output.read_text(encoding="utf-8"))
    validate_creator_bundle(observed)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one inactive shared-growth profile for an existing TemporaryAI candidate."
    )
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument(
        "--maturity-status",
        choices=sorted(MATURITY_STATUSES),
        default="unresolved",
    )
    parser.add_argument("--maturity-classification-receipt-sha256", default="")
    args = parser.parse_args()
    bundle = build_fresh_creator_bundle(
        candidate_id=args.candidate_id,
        display_name=args.display_name,
        maturity_status=args.maturity_status,
        maturity_classification_receipt_sha256=(
            args.maturity_classification_receipt_sha256
        ),
    )
    output = write_bundle_exclusive(bundle)
    print(
        json.dumps(
            {
                "status": "STATIC_CANDIDATE_WRITTEN_INACTIVE",
                "output": output.relative_to(PROJECT_ROOT).as_posix(),
                "bundle_sha256": bundle["bundle_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
