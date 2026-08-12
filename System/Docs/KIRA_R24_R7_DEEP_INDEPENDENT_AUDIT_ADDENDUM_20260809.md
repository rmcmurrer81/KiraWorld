# Kira R24 R7 deep independent-audit addendum — 2026-08-09

Status: **R7 REMAINS REJECTED; EXECUTION IS NOT AUTHORIZED.**

This is an append-only supplement to
`System/Docs/KIRA_R24_R7_INDEPENDENT_STATIC_REJECTION_20260809.md`. It records
deeper defects found in the same sealed R7 byte set. It does not modify R7,
grant Blender authority, accept a candidate, or supersede the earlier rejection.

## Exact reviewed byte set

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py` | 45,424 | `391eac6d01782f75524546600067e441809b706dfd5d9bc8ddfad5c7513bc5e6` |
| `tools/kira_r24_r7_fresh_evaluator.py` | 4,905 | `abd171a1eb73089c7906a213db28c6da5dcb2a847f1ff62ee23535607c8fdc74` |
| `tools/kira_r24_r7_semantic_projection.py` | 5,462 | `e50052017866fcca945ae141ac4227e33a3164de8356ae29e5a5a9e41b1b623f` |
| `tools/blender_extract_kira_r24_candidate_read_only_r7.py` | 16,112 | `df25d4aaabcee0da0333633b2498402433a468c816aef77861850565f3a99b87` |
| R7 contract | 8,915 | `c228fc29b3f2028734a47dd74bdc074216d04b62dd10cf8f3399c419343e9992` |
| R7 package manifest | 918 | `78194b2f42dfd6d3bc96bc771ef389ac40bb9b600c82895362825970b22337a9` |
| R7 static results | 1,076 | `066fea226a76c669fb4371d8077b416b3463bec1babd0c184e09768f189e94dd` |
| Earlier R7 rejection | — | `a6878187e19d1c75647c1c0d7eb3d4fef23b183ed28fe754fae210b58bf22c25` |

## Additional execution and receipt blockers

### 1. The cached contract is a mutable authority object

`load_sealed_contract()` is decorated with `@lru_cache(maxsize=1)` and returns
the mutable `merged` dictionary directly
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:98-99,170-189`).
The author controller later trusts the `static_execution_authority` value on
that same cached object
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:883-886`).
An in-process caller can therefore mutate the already-validated cached mapping
without changing the sealed contract file. The false authority bit is not an
unforgeable capability or a fresh file-derived decision.

### 2. The supposedly sealed process launcher accepts an arbitrary command

`_run_sealed_process_tree()` accepts an arbitrary `Sequence[str]` plus a digest
supplied by its caller, verifies only that the digest matches those same
caller-supplied arguments, and launches them
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:684-714`).
The launcher itself does not bind the executable, script, or arguments to the
sealed contract and does not check the static authority bit. Hashing arbitrary
caller-selected bytes does not turn them into an authorized command.

### 3. Job-object signaling is not a valid general quiescence proof

The implementation treats `WaitForSingleObject(job_handle) == WAIT_OBJECT_0`
as a required general process-tree completion signal, combines it with one
`ActiveProcesses` sample, and calls that `job_quiescent`
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:600-610,662-676,719-730`).
However, R7 configures only `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:647-651`),
not an end-of-job time limit. Microsoft's Job
Objects documentation defines the job object's signaled state for the event in
which all processes terminate because an end-of-job time limit was exceeded;
it is not the ordinary zero-active-process completion primitive R7 assumes:
[Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

The job handle is then closed
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:731-733`),
while the detached
dataclass boolean is later reused as continuing receipt truth
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:776,841-857`).
Thus this code can reject a clean tree for the
wrong signal semantics, and its retained receipt is only a past sample, not a
live kernel-owned lease.

### 4. Candidate identity is not continuous through the final decision

The parent hashes the named candidate once after the author-source lease closes
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:919-924`).
The child hashes that path before evaluation
(`tools/kira_r24_r7_fresh_evaluator.py:86-91`), but the parent later validates
only the echoed digest and the path's current byte count
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:850-855`).
It does not re-hash the candidate or retain an
open immutable candidate handle through lines 942-978. A same-size replacement
after evaluation can therefore leave an eligible receipt naming bytes that are
no longer at the candidate path.

### 5. The evaluator and result channel have no startup-to-decision lease

The fresh evaluator imports the R7 worker before checking its own sealed file
identity (`tools/kira_r24_r7_fresh_evaluator.py:19-24,75-84`). Import-time code
and dependencies have already executed when the identity check occurs. The
candidate is also opened only for ordinary path-based hashing, not held by an
immutable file-identity lease (`tools/kira_r24_r7_fresh_evaluator.py:86-99`).

The evaluator creates its JSON with `O_EXCL`, then closes the descriptor before
exit (`tools/kira_r24_r7_fresh_evaluator.py:119-125`). The parent waits for exit
and reopens the ordinary path by name
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:924-942`).
No file handle, file ID, or
non-delete-sharing lease binds that exact result from creation through parsing
and the final eligibility decision.

### 6. The child receipt fields are echoes, not independent attestations

Author PID, command digest, job nonce, quiescence text, controller nonce, and
source digest all arrive at the evaluator as command-line arguments
(`tools/kira_r24_r7_fresh_evaluator.py:43-57`). The evaluator performs syntax
checks (`tools/kira_r24_r7_fresh_evaluator.py:61-73`) and copies them into its
envelope (`tools/kira_r24_r7_fresh_evaluator.py:100-117`); it does not own or query the author process
or Job Object and does not recompute the author's command. The parent then
compares those echoes with its own now-detached `ProcessTreeEvidence`
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:837-857`).
Nonces establish correlation, but these fields do
not constitute an independently measured, kernel-bound author receipt.

### 7. Raw path components and file identities are not leased

The private snapshot directory is accepted directly from `tempfile.mkdtemp`,
and a child pathname is composed beneath it
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:222-225`).
The final snapshot file handle limits sharing, but R7 never rejects raw
reparse-point components, holds no directory identity handle, and records no
volume serial/file ID for the component chain. `Path.resolve()` follows path
redirection; it is not a reparse rejection or a file-identity lease
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:273-280`).

The runtime candidate path is likewise assembled from a contract prefix and
attempt name
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:736-759`),
then created with an ordinary `mkdir`/path workflow
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:908-923`).
The fresh-evaluator result uses another ordinary temporary directory
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:924-942`).
The
child again relies on resolved pathnames for the evaluator, candidate, and
output (`tools/kira_r24_r7_fresh_evaluator.py:75-96`). None of these routes
provides complete raw-component reparse rejection plus stable parent-directory
and final-file identity leases.

## Additional semantic-projection blockers

### 8. META NLA strips are not recursive

Top-level NLA tracks enumerate only their direct strips
(`tools/blender_extract_kira_r24_candidate_read_only_r7.py:73-97`).
`nla_strip_record()` records scalar RNA, custom properties, F-curves, and
modifiers, but never recursively serializes a META strip's child `strips`
collection (`tools/kira_r24_r7_semantic_projection.py:117-143`). A
behavior-changing edit beneath a META strip can therefore remain outside the
protected semantic projection.

### 9. Nested modifier collections are discarded

The inherited `rna_record()` deliberately drops every RNA `COLLECTION`
property
(`tools/blender_extract_kira_r24_candidate_read_only_r5.py:62-73`). R7's
object, F-curve, and NLA-strip modifier records add only flat RNA and custom
properties
(`tools/blender_extract_kira_r24_candidate_read_only_r7.py:55-62,183-196`;
`tools/kira_r24_r7_semantic_projection.py:135-142`). Modifier-owned nested
collections are not recursively projected, so the claim of complete protected
modifier semantics is too broad.

### 10. CurveMapping and custom-property coverage is selected, not complete

`node_nested_collections()` recognizes only `node.color_ramp`,
`node.mapping`, and part of `node.color_mapping`
(`tools/kira_r24_r7_semantic_projection.py:100-114`). Its CurveMapping record
uses a fixed scalar list and curve points
(`tools/kira_r24_r7_semantic_projection.py:64-97`),
not a generic inventory of every CurveMapping-bearing pointer or supported
nested RNA collection.

Custom properties are also added only at selected augmentation sites. For
example, inherited node links and interface items are serialized without R7
custom-property augmentation
(`tools/blender_extract_kira_r24_candidate_read_only_r5.py:193-235` compared
with `tools/blender_extract_kira_r24_candidate_read_only_r7.py:160-171`).
Inherited scene view layers and recursive layer collections likewise remain
flat R5 records, while R7 adds custom properties only to the Scene itself
(`tools/blender_extract_kira_r24_candidate_read_only_r5.py:404-445`;
`tools/blender_extract_kira_r24_candidate_read_only_r7.py:259-263`). These are
concrete gaps in the claim
that behavior-affecting protected custom state is complete.

### 11. Camera and light datablocks are absent from the extracted inventory

The R7 state enumerates objects, mesh/armature datablocks, materials, actions,
images, node groups, collections, worlds, scenes, and intersection reports,
but not `bpy.data.cameras` or `bpy.data.lights`
(`tools/blender_extract_kira_r24_candidate_read_only_r7.py:316-334`). The
generic object record retains only `data_name` and explicitly excludes the
object's `data` pointer from its RNA projection
(`tools/blender_extract_kira_r24_candidate_read_only_r5.py:268-310`). Camera or
light datablock settings can therefore change without a complete semantic
record of those datablocks.

## Package-provenance blockers

### 12. The advertised POST-audit state contradicts the sealed manifest

The worker labels exactly the five current files plus
`INDEPENDENT_STATIC_AUDIT.md` as `POST_AUDIT_EXACT`
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:993-1004`).
But the sealed manifest states `PRE_AUDIT_EXACT`, omits that audit from its file
map, and says `independent_static_audit_present: false`
(`RecoverySprint/continuation_20260808/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7/PACKAGE_MANIFEST.json:1-27`).
Adding the audit would therefore make the directory matcher say POST while the
manifest inside the same package still says PRE/no audit. Updating the
manifest would change preserved R7 bytes. The current System/Docs rejection is
external to the R7 package and does not cure this contradiction.

### 13. Two current R6 evidence parents are missing

The exact expected-parent set omits R6's current package manifest and static
test results
(`tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7.py:112-120`).
The R7 contract's complete parent list likewise stops at the R6 proposal and
does not bind either file
(`RecoverySprint/continuation_20260808/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7/INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R7_CONTRACT.json:7-68`).
The unbound current files are:

- R6 `PACKAGE_MANIFEST.json`: 4,088 bytes,
  SHA-256 `dd8e3d32a1a74d06f984cbbb9688a54030e32abd790b452b841a1d5115a58871`.
- R6 `STATIC_TEST_RESULTS.json`: 3,494 bytes,
  SHA-256 `3d1a51e4e6c212d3dd4edc707a5afab25f5dd41dd9e1711389370c3f57dae1c4`.

This contradicts R7 checkpoint language claiming the complete current R6
implementation/package was held and sealed
(`RecoverySprint/continuation_20260808/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r7/CHECKPOINT.md:7`).

## Disposition

R7's `37/37` focused static result remains historical test truth, not execution
authority. The deeper findings are independently sufficient to reject the
gate. Preserve R7 byte-for-byte. Do not launch Blender, create a candidate, or
start a minor R8 that only adds more hashes and path samples. A successor would
need a genuinely different authority boundary, immutable artifact/result
leases with kernel identity, correct process-tree completion evidence, and a
complete Blender semantic inventory—or an explicit owner decision to accept a
narrower threat model.

No tests or Blender process were run while producing this read-only addendum.
