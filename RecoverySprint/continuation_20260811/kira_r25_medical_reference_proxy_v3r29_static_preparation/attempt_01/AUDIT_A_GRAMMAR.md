# V3r29 Audit A exact grammar

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
the exact manifest SHA-256, Stage-1 subject root, Stage-1 seal SHA-256,
complete Stage-1 all-files inventory root, and independent auditor ID outside
the replaceable package and pass all five values explicitly to the sealed
materializer. The seal and all-files roots are mandatory authority anchors;
recomputing the subject root after changing the seal cannot authorize V3r29.

`INDEPENDENT_AUDIT.tsv` uses LF only and this header:

`row_id<TAB>status<TAB>evidence_sha256<TAB>finding<LF>`

It has exactly these 18 rows, in this order, each with status `PASS`, a
lowercase 64-hex evidence digest, and a nonempty one-line finding:

1. `01_stage1_subject_root`
2. `02_stage1_seal_external_sha`
3. `03_stage1_all_files_external_root`
4. `04_upstream_v3r28_and_rejection`
5. `05_static_only`
6. `06_two_stage_authority`
7. `07_blender_identity`
8. `08_materialized_native_analyzer`
9. `09_exact_audit_json_types`
10. `10_durable_materialization_consumption`
11. `11_native_pre_reserved_outputs`
12. `12_handles_through_terminal_success`
13. `13_worker_factory_isolation`
14. `14_frame_landmarks`
15. `15_proxy_truth`
16. `16_hostile_geometry`
17. `17_license_quarantine`
18. `18_claim_boundary`

`AUDIT_DECISION.json` is strict UTF-8/LF JSON with no duplicate keys or
non-finite values and exactly these fields/values (the three bracketed values
are externally fixed):

```json
{
  "schema": "kira.r25.medical_reference_proxy.v3r29.audit_a_decision.v1",
  "status": "ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY",
  "auditor_id": "[independent_auditor_id]",
  "accepted_stage1_package_root": "[exact_stage1_root_sha256]",
  "accepted_stage1_seal_sha256": "[exact_stage1_seal_sha256]",
  "accepted_stage1_all_files_root_sha256": "[exact_stage1_all_files_root_sha256]",
  "execution_authority": "MATERIALIZE_STAGE2_ONLY_NO_BLENDER",
  "candidate_executed": false,
  "blender_invoked": false,
  "maximum_materializations": 1,
  "stage2_requires_different_audit_b": true,
  "audit_scope": "CACHE_FREE_STATIC_SYNTAX_MOCKED_HOSTILE_AND_TRUSTED_BUILD_ANALYZE_ONLY",
  "materialization_consumption_key_sha256": "[deterministic_key_from_subject_root_seal_all_files_root_and_auditor]"
}
```

Every field has an exact JSON type. String fields are strings, the three
Boolean fields are Boolean singletons, and `maximum_materializations` is the
exact integer `1`; Python Boolean/integer equality aliases, floats, numeric
strings, duplicate keys, non-finite numbers, extra keys, and coercions are all
refused.

Even a valid Audit A permits only one scratch Stage-2 source materialization
and native build. Before writing any generated output the materializer creates
and flushes an exclusive consumed-authority record under the fixed external
`Documents/Codex/kira_authority_ledgers/body_v3r29` directory. Removing or
recreating the generated package does not remove that record or restore the
same authority. A different Audit B must externally pin the exact materialized
executable, and root must hold the rehashed same file object across the one
future process launch. No local Audit A/sidecar pair is launch authority.
