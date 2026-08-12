"""Consume one parent-signed inert TemporaryAI quality-V4 authorization.

The owner-facing launcher supplies only an authorization identifier.  The
envelope path is fixed, and its exact SHA-256 plus trusted UTC value must be
inherited from the separately controlled parent process.  The signed envelope
selects creation versus static evaluation and every identity, authority root,
output namespace, nonce, and expiry.  This CLI has no model, body, voice,
avatar, Blender, activation, assignment, or publication route.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temporary_ai_creator_quality_v4 import (
    ENVELOPE_NAMESPACE,
    consume_signed_envelope_v4,
)


AUTHORIZATION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,79}$")
ENVELOPE_HASH_ENV = "KIRA_TEMP_AI_V4_EXPECTED_ENVELOPE_SHA256"
TRUSTED_NOW_ENV = "KIRA_TEMP_AI_V4_TRUSTED_NOW_UTC"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consume one parent-signed inert TemporaryAI quality-V4 authorization."
    )
    parser.add_argument("--authorization-id", required=True)
    args = parser.parse_args()
    if AUTHORIZATION_ID_RE.fullmatch(args.authorization_id) is None:
        raise SystemExit("authorization ID must be one canonical identifier")
    expected_hash = os.environ.get(ENVELOPE_HASH_ENV, "")
    trusted_now = os.environ.get(TRUSTED_NOW_ENV, "")
    if not expected_hash or not trusted_now:
        raise SystemExit(
            f"parent launcher must set {ENVELOPE_HASH_ENV} and {TRUSTED_NOW_ENV}"
        )
    envelope_relative = (
        f"{ENVELOPE_NAMESPACE}/{args.authorization_id}.json"
    )
    result = consume_signed_envelope_v4(
        PROJECT_ROOT,
        envelope_relative=envelope_relative,
        expected_envelope_sha256=expected_hash,
        trusted_now_utc=trusted_now,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
