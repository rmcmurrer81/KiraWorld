# V3r30 Audit A exact grammar

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
the replaceable package and pass those five Audit-A values explicitly to the sealed
materializer. The seal and all-files roots are mandatory authority anchors;
recomputing the subject root after changing the seal cannot authorize V3r30.

`INDEPENDENT_AUDIT.tsv` uses LF only and this header:

`row_id<TAB>status<TAB>evidence_sha256<TAB>finding<LF>`

It has exactly these 18 rows, in this order, each with status `PASS`, a
lowercase 64-hex evidence digest, and a nonempty one-line finding:

1. `01_stage1_subject_root`
2. `02_stage1_seal_external_sha`
3. `03_stage1_all_files_external_root`
4. `04_upstream_v3r29_and_rejection`
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
  "schema": "kira.r25.medical_reference_proxy.v3r30.audit_a_decision.v1",
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

Audit A must rehash all 33 direct V3r29 bindings (26 exact author files and
seven exact rejection files), all 28 nested V3r28 bindings, and all 17 deep
V3r27 bindings. The V3r29 rejection remains a rejection; V3r30 may pass only
if its append-only repairs independently close the three recorded blockers.

Audit A must also run cache-free `PostSeal` from the installed layout and prove
that the package snapshot is byte-identical before and after. Every hostile
consumption probe must use a test-owned directory below `Documents/Codex`; it
must never try to create a ledger beneath the installed Kira package.

## Separate ProgramData install-authority audit

Audit A acceptance still cannot create the ProgramData ledger directory. A
second separately manifested install-authority review, with an auditor ID
different from both author and Audit A, must be installed at the exact sealed
path before materialization. Its four exact files are
`INSTALL_AUTHORITY_MANIFEST.tsv`, `INSTALL_AUTHORITY_DECISION.json`,
`INSTALL_AUTHORITY_AUDIT.tsv`, and `CHECKPOINT.md`. The manifest binds all
three other files; its SHA-256 plus the auditor ID are external materializer
arguments.

The strict decision binds the accepted Audit-A manifest/auditor, exact
`C:\ProgramData` anchor, exact anchor DACL SDDL, access-denied
`FILE_DELETE_CHILD` result, exact
`C:\ProgramData\KiraV3r30AuthorityLedger` target, exact final read-only
ledger-file and append-only ledger-directory DACLs supplied during atomic
object creation, both exact canonical DACL readbacks, mandatory
`NtCreateFile`/`RootDirectory`-relative directory and file operations, one target-directory
creation, and one materialization. It records that
the reviewer created no ProgramData directory and ran no candidate. Its own
maximum native builds and Blender invocations are both zero. The seven exact
audit rows cover target absence, anchor identity, exact DACL, delete-child
refusal, Owner-Rights atomic-creation policy, handle-relative creation policy,
and zero build/Blender authority. Missing,
unbound, same-auditor, wrong-type, changed-path, or changed-DACL evidence
refuses before the materializer writes anything.

Even a valid Audit A permits only one scratch Stage-2 source materialization
and native build. Before writing any generated output, the separately
authorized materializer proves
that the caller cannot obtain `FILE_DELETE_CHILD` on the fixed
`C:\ProgramData` anchor and that its DACL exactly matches the sealed expected
SDDL; ambiguity, access success, or a changed DACL refuses. It retains that
exact anchor without delete sharing, then uses `NtCreateFile` with the held
anchor as `RootDirectory` to atomically create the one exact top-level
`KiraV3r30AuthorityLedger` directory with its final protected append-only
Owner-Rights DACL.
If the name already exists, a separate handle-relative read/traverse open must
prove its exact identity and canonical final DACL. It uses the held directory
as `RootDirectory` to atomically create the single-link non-reparse consumed
record with its final read-only Owner-Rights DACL, flushes and reads it through
the same held handle, and requires both canonical DACL readbacks: the file is
read-only and the ledger directory allows only read, traverse, and add-file,
with no add-subdirectory, delete, delete-child, or `WRITE_DAC`. Extra child
creation cannot remove, replace, or reset the exact deterministic ledger.
Because neither the protected object nor its
anchor parent authorizes current-user deletion, and the explicit Owner Rights
ACEs suppress the owner's usual implicit `WRITE_DAC`, the fixed path
cannot be reset after handles close. The materializer also revalidates the held identities
through atomic Stage-2 publication. Removing, renaming, junction-swapping, or
recreating the generated package cannot restore the same authority within the
software boundary; administrator take-ownership and disk rollback remain
outside that boundary.

Before Blender, native must pre-reserve and retain seven unique regular
single-link non-reparse worker-staging handles plus all eight final handles.
It must protect all seven staging files and their directory with the exact
Owner-Rights transaction DACL before Blender, so the owner retains worker
read/write but cannot add a hard link. The worker may write only those exact identities. Any substitution, hard-link,
reparse, path, identity, size, or hash mismatch consumes/refuses. A different
Audit B must externally pin the exact materialized executable, and root must
hold the rehashed same file object across the one future process launch. No
local Audit A/sidecar pair is launch authority.
