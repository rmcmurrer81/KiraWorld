#!/usr/bin/env python3
"""Default-off worker shim for Blackwell V12 canonical memory binding."""

from __future__ import annotations

import sys
from typing import Any

from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12 import (
    candidate_contract as v12_contract,
)


V12_AUDIT_ARGUMENT = "--accepted-v12-audit-sha256"


def _extract_v12_audit_and_strip(argv: list[str]) -> tuple[list[str], str]:
    values = list(argv)
    if V12_AUDIT_ARGUMENT not in values:
        return values, ""
    if values.count(V12_AUDIT_ARGUMENT) != 1:
        raise v12_contract.V12ContractError("v12 audit argument is duplicated")
    index = values.index(V12_AUDIT_ARGUMENT)
    if index + 1 >= len(values):
        raise v12_contract.V12ContractError("v12 audit argument has no value")
    digest = values[index + 1]
    if not v12_contract.is_sha256(digest):
        raise v12_contract.V12ContractError("v12 audit argument is not SHA-256")
    del values[index:index + 2]
    return values, digest


def prepare_future_harness_memory_binding(
    expected_v12_audit_sha256: str,
) -> tuple[Any, dict[str, Any]]:
    """Static-testable preparation for a later separately authorized harness.

    V12 itself never calls this from its command entry. A future successor must
    add a new one-shot process/session capability before calling it.
    """

    config = v12_contract.load_canonical_config()
    v12_contract.verify_preserved_bytes(config)
    v12_contract.verify_v10_static_audit(config)
    v12_contract.verify_v11_rejection(config)
    v12_contract.verify_future_fresh_audit_authorization(
        config, expected_audit_sha256=expected_v12_audit_sha256
    )
    v12_contract.verify_outer_preparation_opt_in(config)
    from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v12 import (
        canonical_typed_memory_binding as canonical,
    )

    binding = canonical.create_canonical_typed_memory_binding()
    evidence = canonical.install_exact_typed_memory_probe(binding)
    readback = canonical.revalidate_exact_typed_memory_probe(binding)
    if evidence["binding_sha256"] != readback["binding_sha256"] or readback != {
        key: evidence[key] for key in readback
    }:
        raise v12_contract.V12ContractError("v12 canonical binding readback drifted")

    # Close the preparation window as well as each binding authority use.  A
    # future harness must not receive a binding when any sealed dependency,
    # predecessor decision, audit capability, or outer opt-in changed while
    # the private modules were being prepared.
    post_config = v12_contract.load_canonical_config()
    if post_config != config:
        raise v12_contract.V12ContractError(
            "v12 canonical configuration changed during preparation"
        )
    v12_contract.verify_preserved_bytes(post_config)
    v12_contract.verify_v10_static_audit(post_config)
    v12_contract.verify_v11_rejection(post_config)
    v12_contract.verify_future_fresh_audit_authorization(
        post_config, expected_audit_sha256=expected_v12_audit_sha256
    )
    v12_contract.verify_outer_preparation_opt_in(post_config)
    final_readback = canonical.revalidate_exact_typed_memory_probe(binding)
    if final_readback != readback:
        raise v12_contract.V12ContractError(
            "v12 canonical binding changed during final preparation validation"
        )
    return binding, dict(evidence)


def main() -> int:
    try:
        delegated, accepted_v12_audit = _extract_v12_audit_and_strip(sys.argv[1:])
        live = "--live" in delegated
        static_fixture = "--static-fixture" in delegated
        if live == static_fixture:
            sys.stderr.write("Blackwell v12 requires exactly one worker mode.\n")
            return 94
        config = v12_contract.load_canonical_config()
        v12_contract.verify_preserved_bytes(config)
        v12_contract.verify_v11_rejection(config)
        if live:
            sys.stderr.write(
                "Blackwell v12 is static repair only; a later audited harness is required.\n"
            )
            return 96
        if accepted_v12_audit:
            raise v12_contract.V12ContractError(
                "static fixture must not receive a v12 audit argument"
            )
        from Voice.sidecars.chatterbox_blackwell_persistent_candidate_v8 import (
            worker_entry as v8_worker_entry,
        )

        sys.argv = [sys.argv[0], *delegated]
        return int(v8_worker_entry.main())
    except Exception as exc:
        sys.stderr.write(f"Blackwell v12 integration refused: {type(exc).__name__}:{exc}\n")
        return 95


if __name__ == "__main__":
    raise SystemExit(main())
