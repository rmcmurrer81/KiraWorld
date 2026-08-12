# V3r16 fresh hostile static test results

Date: 2026-08-11

## Author suite

Command:

`powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File Testing/test_kira_r25_foundation_afes_contract_lock_diagnostic_v3r16_static.ps1`

Result: `V3R16_STATIC_TESTS run=114 failed=0`.

This pass is insufficient because the author suite validates current source
against the current identity anchor and does not bind the current closure back
to the earlier outer checkpoint seal.

## Independent suite

Command:

`powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File RecoverySprint/continuation_20260811/kira_r25_afes_contract_lock_diagnostic_v3r16_fresh_static_audit/attempt_01/INDEPENDENT_HOSTILE_STATIC_TEST.ps1`

Result: `V3R16_INDEPENDENT_STATIC run=112 failed=9`.

Failures:

- eight exact byte/hash expectations across six outer-checkpoint subjects;
- one audit binding failure because the PE expects the 20260810
  `kira_r25_afes_v3r16_fresh_static_audit` path, not the required 20260811
  `kira_r25_afes_contract_lock_diagnostic_v3r16_fresh_static_audit` path.

Static positive checks passed for exact `CREATE_NEW` write-through reservation,
reservation before diagnosis, one target handle, broad diagnostic share mode,
all granular gates, two complete snapshots, repeated path/file-ID/size checks,
expected digest equality, terminal evidence and two-record receipt durability,
flush/readback/trailing-byte checks, partial-write refusal, reparse/path/error
fail-closed handling, and absence of Python/controller/AFES/Blender/process
source or image names.

The candidate and rebuilt audit copy were never executed.
