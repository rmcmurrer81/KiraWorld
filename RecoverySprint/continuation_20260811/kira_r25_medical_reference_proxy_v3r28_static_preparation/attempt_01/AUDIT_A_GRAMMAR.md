# V3r28 Audit A exact grammar

Audit A is a different independent cache-free static/mocked-hostile review. It
cannot authorize Blender. Its only possible acceptance status is:

`ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY`

The audit directory is flat and contains only regular non-reparse files. It
must contain `AUDIT_DECISION.json`, `CHECKPOINT.md`, `INDEPENDENT_AUDIT.tsv`,
and `AUDIT_ARTIFACT_MANIFEST.tsv`; additional evidence files are allowed only
when the manifest binds them. The manifest excludes itself, covers every other
file exactly once in Python ordinal path order, uses LF only, and has:

`path<TAB>bytes<TAB>sha256<LF>`

`CHECKPOINT.md` is therefore content-bound, not presence-only. Root must obtain
the exact manifest SHA-256, Stage-1 package root, and independent auditor ID
outside the replaceable package and pass those three values explicitly to the
sealed materializer.

`INDEPENDENT_AUDIT.tsv` uses LF only and this header:

`row_id<TAB>status<TAB>evidence_sha256<TAB>finding<LF>`

It has exactly these 14 rows, in this order, each with status `PASS`, a
lowercase 64-hex evidence digest, and a nonempty one-line finding:

1. `01_stage1_seal`
2. `02_upstream_17`
3. `03_static_only`
4. `04_two_stage_authority`
5. `05_blender_identity`
6. `06_native_handle_locking`
7. `07_one_shot_ledger`
8. `08_worker_factory_isolation`
9. `09_frame_landmarks`
10. `10_proxy_truth`
11. `11_hostile_geometry`
12. `12_output_revalidation`
13. `13_license_quarantine`
14. `14_claim_boundary`

`AUDIT_DECISION.json` is strict UTF-8/LF JSON with no duplicate keys or
non-finite values and exactly these fields/values (the three bracketed values
are externally fixed):

```json
{
  "schema": "kira.r25.medical_reference_proxy.v3r28.audit_a_decision.v1",
  "status": "ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY",
  "auditor_id": "[independent_auditor_id]",
  "accepted_stage1_package_root": "[exact_stage1_root_sha256]",
  "execution_authority": "MATERIALIZE_STAGE2_ONLY_NO_BLENDER",
  "candidate_executed": false,
  "blender_invoked": false,
  "maximum_materializations": 1,
  "stage2_requires_different_audit_b": true,
  "audit_scope": "CACHE_FREE_STATIC_SYNTAX_MOCKED_HOSTILE_ONLY"
}
```

Even a valid Audit A permits only one scratch Stage-2 source materialization
and native build. A different Audit B must externally pin the exact materialized
executable, and root must hold the rehashed same file object across the one
future process launch. No local Audit A/sidecar pair is launch authority.
