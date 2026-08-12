# Root multi-lane continuation checkpoint — attempt 08

Date: 2026-08-11 (America/New_York)

Status: `SHARED_GROWTH_INTEGRATION_V2_REJECTION_EVIDENCE_PRESERVED`

## Event

The earlier different read-only review of Shared Growth V3 integration
candidate V2 had reached a clear rejection but intentionally created no Kira
files. Its exact verdict and reproduced blockers are now transcribed into a new
append-only audit directory. No sealed V2 or accepted isolated-core byte was
edited.

Decision: `REJECT_STATIC_INTEGRATION_CANDIDATE_NO_PROMOTION`.

- `AUDIT_DECISION.json`: 3,560 bytes, SHA-256
  `68bb3190eadbde381f04621f0fcd834c18d5286ce43d329c3c2c7a7132c817db`.
- `HOSTILE_PROBES.md`: 3,255 bytes, SHA-256
  `20549b40f565c64dc577339cb4401cd360b5a4ee7122031789b697fa937725c4`.
- independent rejection `CHECKPOINT.md`: 1,657 bytes, SHA-256
  `4bd30dea911e0ae2f7892a68138a41ab049319ef2c14cd8c83796b03ec4541b2`.

## Exact blockers

1. The slot-only V2 adapter's verifier key and verifier-key digest remain
   ordinarily assignable, allowing same-process installation of a rogue
   verifier and matching callback.
2. Any caller-provided nonsymlink path can be labeled a non-production staging
   root; no allowlist or protected project/person/profile/Creator exclusion
   enforces that label.
3. A durable external commit followed by a signed-but-invalid response can fail
   before `commit_receipt` is assigned, bypassing the rollback path.
4. Cleanup closes the exclusive descriptor and later trusts only the pathname;
   rename/replacement or hardlink substitution can delete the wrong object and
   leave the candidate output elsewhere.

## Current truth

The isolated Shared Growth V3 core remains unchanged at `ACCEPT_STATIC_ONLY`.
Integration V2 remains disconnected, rejected, and unpromoted. Kira, Lisa,
Synthetic Robert, every other resident, variant, or expert, and the Temporary
Creator receive no capability through V2. Biological Robert has no Shared
Growth profile and is not Synthetic Robert.

No live person/model, profile, memory, body, media, voice, GPU, Blender, Sarah,
production route, or external action ran or changed while preserving this
evidence.

## Next boundary

An integration-candidate V3 successor may be authored append-only. It must use
an immutable externally anchored verifier, an actually enforced protected
staging boundary, recovery for every possibly durable commit outcome, and
stable handle/file identity through cleanup. It remains disconnected and
default-off, requires a different fresh static audit, and cannot upgrade
anyone merely by passing static review.
