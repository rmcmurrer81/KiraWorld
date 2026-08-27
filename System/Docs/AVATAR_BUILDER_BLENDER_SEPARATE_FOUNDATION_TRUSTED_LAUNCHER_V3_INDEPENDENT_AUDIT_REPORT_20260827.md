# Separate-foundation trusted launcher V3 — independent static audit

## Verdict

**PASS (static trust boundary only).** The V2 rejection findings F-001 and F-002 are closed in the sealed V3 source. This verdict does not authorize execution, does not say Blender ran, and does not accept either body.

No external one-use authority was created or accepted. Blender and the frozen worker were not invoked. No authority, consumption, worker claim, runtime namespace, stage, output, activation, publication, or GitHub sync was created. Both source GLBs retained their exact size, SHA-256, and nanosecond modification timestamp.

## V2 finding F-001: directory and executable namespace substitution

Closed by the following combined boundary:

- Every existing ancestor directory in the runtime/static/source closure is opened with delete sharing disabled.
- Each held ancestor records a stable volume serial plus 128-bit file ID, rejects reparse points at the handle, and is reopened by path to prove the path still names the held identity.
- That directory identity chain is revalidated immediately before `CreateProcessW` and again while the new process is suspended.
- The Blender executable itself remains open deny-write/delete and is represented by size, SHA-256, and stable volume/file identity.
- V3 does not use `QueryFullProcessImageNameW`. It reads the suspended process PEB, obtains the actual mapped image base, resolves the file mapping with `GetMappedFileNameW`, and compares its NT device path to the locked Blender executable's device path.
- Under the still-locked directory namespace, V3 reopens Blender and requires stable volume/file identity, size, and SHA-256 to equal the original locked executable.
- Only after all of those checks and the full locked-row revalidation can `ResumeThread` run. Any unavailable or inconsistent Windows identity API throws and fails closed.

The final stage-to-candidate transition is handle-bound through `SetFileInformationByHandle(FileRenameInfo)` with replace disabled. V3 then proves that the final path names the originally created stage volume/file identity and that all four output paths name their already locked file identities.

## V2 finding F-002: unsafe failure cleanup

Closed by removing recursive directory cleanup from the failure path. V3 preserves residue instead of deleting it. If residue is present, reporting first requires:

- the exact expected parent and leaf name;
- the originally held parent/ancestor volume-file identity closure;
- no reparse point in the complete ancestry or at either directory handle;
- the original live stage/final handle's stable identity; and
- a fresh path-opened directory handle with the same stable identity.

If any proof differs, residue is still preserved and the verification failure is recorded. The failure receipt truthfully states `cleanup_performed=false` and `residue_preserved=true`.

## Adversarial coverage

The V3 suite ran **21/21 passing tests**. Independent in-memory corruptions were rejected for:

1. delete-sharing namespace swap;
2. ancestor identity revalidation removal;
3. mapped-process-image proof removal;
4. locked executable stable-identity comparison removal;
5. handle-bound final commit replacement;
6. recursive cleanup injection;
7. cleanup parent/file-ID/reparse proof removal.

The suite also rejected duplicate and case-colliding JSON keys and loose scalar types, checked one-use/replay TTL and no-replace claim markers, checked the exact four-file closure, compiled the embedded C# without calling native methods, parsed the PowerShell and Python sources, verified no alternate data streams, and verified `-Execute` omission fails before native initialization.

## Exact commands and results

```text
$env:PYTHONDONTWRITEBYTECODE='1'; py -m unittest -v Testing.test_avatar_blender_separate_foundation_trusted_launcher_v3
Result: exit 0; Ran 21 tests; OK

$env:PYTHONDONTWRITEBYTECODE='1'; py audit\avatar_separate_foundation_launcher_v3_independent_static_audit.py
Result: exit 0; status PASS; failures []

powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\Users\robmc\Kira\tools\run_avatar_builder_blender_5_1_separate_foundation_trusted_launcher_v3.ps1
Result: exit 1 with "Execution was not requested" before native initialization; runtime namespace remained absent

PowerShell Language.Parser.ParseFile plus Add-Type compile of the embedded C# here-string
Result: PASS; no native method was called
```

## Sealed artifact identities

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| V3 launcher | 76,692 | `81f5f1d57986f882c74447a4dd7d947b3e2c65e5dfe085e03f51fc88ec7ff053` |
| V3 policy and byte-identical worker compatibility mirror (each) | 669 | `891e8cb2dc2e7697a81643b980fdee000b6cb6223785e3e7566e4e6b02ae2a59` |
| V3 minimal audit and byte-identical worker compatibility mirror (each) | 756 | `35b0156ef9a449d16dce6d69b374a72b4635bbe0c8a1036baa197ac4a45fbc4c` |
| Python evaluator | 25,758 | `4e358a9e111f4b849e853803477f3f866b515cf1ef01129207f2e67e424c6f38` |
| Adversarial tests | 11,689 | `45034d6f370fc2d8763a224ebd680e51acc73a3ee41e8ff925a40a298fdd1c81` |
| Static evaluation receipt | 3,693 | `9b38a2ab8bd82f56b5b1a52ce4f82610f5c38da6bc676bbe65db096fb7b4056f` |
| Independent workspace harness | 19,191 | `3a8efebac80d87b28a39efddc61a75a8884a7c93afbe4bc6bcb76fa049dd5b71` |

Frozen dependency hashes remained:

- runtime identity: `44fcf953db0422bab2c9ffe0c885550031f918b0b63538024da47124535749a5`
- worker: `9685e7c2babd966cb4605ec82a585c19546e9ba1665125d769b95924f70b5890`
- worker configuration: `70a72c6f628fab4a85ac4c5e6dc6d3da45ef2e4ef98be4a2162a562d42bebc20`
- output contract: `11a564fa1bc9f5a4b21a59dfb4eecce622c11418be8a9c14babb4a2f78274c71`

## Source preservation

- Kira GLB: 5,105,808 bytes; `ccd3b7467452f0fc9b084511e1aa3e4dd234a9ad90ba0b96f13d78ecd6207c77`; mtime ns `1784407032475394300`.
- Synthetic Robert GLB: 8,645,492 bytes; `bfcdf8ec2a1d8444cfef5f7d1382884cb5f6aff685f04c6e4d000b4de0332370`; mtime ns `1785296385810827200`.

Neither source was modified. No alternate data streams were found on the audited closure.

## Remaining gate

Static V3 is audit-passed, but execution remains intentionally unauthorized. A separately authenticated, current, one-use authority would still be required for a future run. This audit grants no such authority.
