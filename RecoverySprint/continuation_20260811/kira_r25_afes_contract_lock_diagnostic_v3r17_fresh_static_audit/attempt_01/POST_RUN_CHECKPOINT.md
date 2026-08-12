# Kira R25 AFES V3r17 consumed-run outcome

Date: 2026-08-11

Outcome: `CONTRACT_LOCK_DIAGNOSTIC_SUCCESS_AUTHORITY_CONSUMED_NO_RETRY`

## Result

The exact one-shot command ran once from `C:\Users\robmc\Kira` with no
arguments, wrapper script, pipe, or redirection:

```powershell
.\tools\native\kira_r25_afes_contract_lock_diagnostic_v3r17.exe
```

Exit code: `0`

Standard output: `V3R17_CONTRACT_LOCK_DIAGNOSTIC_SUCCESS`

Standard error: empty.

The authorization is consumed and V3r17 must never be invoked again.

## Durable evidence

- `RUN_EVIDENCE.jsonl`: 356 bytes, SHA-256
  `e0e4968efa52efc924cc7e9e3841c04047bf25389dde87bbf379cc5ddda2aafa`.
  It contains exactly a sequence-1 reservation and sequence-2 terminal record.
- `CONTRACT_LOCK_DIAGNOSTIC_OUTCOME.receipt.bin`: 992 bytes, SHA-256
  `7a2d0b9f54b3b96a8621528b794afc07458a870b0cf37ea3b7318ad8bae7b385`.
  It contains exactly two 496-byte packed records and no trailing byte.
- The terminal record has state 2, success 1, failure gate 0, Win32 error 0,
  and passed mask 32767 (all fifteen diagnostic gates).
- The expected, snapshot-one, and snapshot-two lengths are each 6,174 bytes.
- Their SHA-256 values are all exactly
  `ad33386d767b516425dcbed073e22dfc9747a963a64dc5d205483d210acac79d`.
- The terminal evidence digest exactly matches `RUN_EVIDENCE.jsonl`.
- The terminal pending-record digest
  `cc2505e3c31ca8b70cb6637b630232d20a1d251166f7ce442cba3051f59055a9`
  exactly matches the first 496-byte receipt record.
- The executable and accepted-audit digests embedded in both records exactly
  match the sealed V3r17 PE and the accepted audit TSV.

## Meaning and boundary

This closes only the V3r15 contract-lock diagnostic layer: the target contract
was opened read-only after durable output reservation, measured twice through
the same handle with stable identity/path/size gates, and durably receipted.

It does **not** validate or execute Python, the controller, the execution
contract, the plan builder, broker, AFES, Blender, a Blend file, mesh, anatomy,
movement, body activation, save, render, export, or production routing.  No
body was created or changed.  The next step must be a new append-only static
successor and a different fresh audit; this success never authorizes a V3r17
retry or an automatic expansion of capability.
