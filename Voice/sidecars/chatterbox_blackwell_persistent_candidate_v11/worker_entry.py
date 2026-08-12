#!/usr/bin/env python3
"""Default-off v11 worker shim for the typed-memory integration.

Static-fixture mode delegates to the exact sealed v8 worker without importing
the live adapter.  Live mode remains unreachable until this exact package has
its own different-agent audit and a later process-scoped capability.  Only
then does the shim verify the accepted v10 repair, import the exact v8 live
adapter, install the typed Win32 memory probe, and delegate to v8's sealed
worker main.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v11 import (
    candidate_contract as v11_contract,
)


V11_AUDIT_ARGUMENT = "--accepted-v11-audit-sha256"


def _extract_v11_audit_and_strip(argv: list[str]) -> tuple[list[str], str]:
    values = list(argv)
    if V11_AUDIT_ARGUMENT not in values:
        return values, ""
    if values.count(V11_AUDIT_ARGUMENT) != 1:
        raise v11_contract.V11ContractError("v11 audit argument is duplicated")
    index = values.index(V11_AUDIT_ARGUMENT)
    if index + 1 >= len(values):
        raise v11_contract.V11ContractError("v11 audit argument has no value")
    digest = values[index + 1]
    if not v11_contract.is_sha256(digest):
        raise v11_contract.V11ContractError("v11 audit argument is not SHA-256")
    del values[index:index + 2]
    return values, digest


def prepare_live_memory_integration(expected_v11_audit_sha256: str) -> dict[str, Any]:
    """Prepare an exact adapter for a later separately audited live harness.

    This helper is exercised only through static tests in v11. V11's own
    command entry refuses live mode unconditionally; a successor harness must
    add its own fresh audit and one-shot capability before calling this helper.
    """

    config = v11_contract.load_canonical_config()
    v11_contract.verify_preserved_bytes(config)
    v11_contract.verify_v10_static_audit(config)
    v11_contract.verify_future_fresh_audit_authorization(
        config, expected_audit_sha256=expected_v11_audit_sha256
    )
    v11_contract.verify_per_run_live_capability(config)

    from Core.blackwell_v10_windows_memory import (
        install_into_exact_v8_live_adapter,
        windows_memory_mib,
    )
    from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8 import (
        live_adapter as v8_live_adapter,
    )

    evidence = install_into_exact_v8_live_adapter(v8_live_adapter)
    if (
        evidence.get("installed") is not True
        or evidence.get("target_sha256")
        != config["preserved_boundaries"][
            "Voice/sidecars/chatterbox_blackwell_persistent_candidate_v8/live_adapter.py"
        ]
        or v8_live_adapter._windows_memory_mib is not windows_memory_mib
    ):
        raise v11_contract.V11ContractError(
            "typed memory replacement did not bind the exact v8 live adapter"
        )
    return dict(evidence)


def main() -> int:
    delegated, accepted_v11_audit = _extract_v11_audit_and_strip(sys.argv[1:])
    live = "--live" in delegated
    static_fixture = "--static-fixture" in delegated
    if live == static_fixture:
        sys.stderr.write("Blackwell v11 requires exactly one worker mode.\n")
        return 91
    try:
        config = v11_contract.load_canonical_config()
        v11_contract.verify_preserved_bytes(config)
        if live:
            sys.stderr.write(
                "Blackwell v11 is static integration only; a later audited harness is required.\n"
            )
            return 93
        elif accepted_v11_audit:
            raise v11_contract.V11ContractError(
                "static fixture must not receive a v11 live audit argument"
            )
        from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8 import (
            worker_entry as v8_worker_entry,
        )

        sys.argv = [sys.argv[0], *delegated]
        return int(v8_worker_entry.main())
    except Exception as exc:
        sys.stderr.write(f"Blackwell v11 integration refused: {type(exc).__name__}:{exc}\n")
        return 92


if __name__ == "__main__":
    raise SystemExit(main())
