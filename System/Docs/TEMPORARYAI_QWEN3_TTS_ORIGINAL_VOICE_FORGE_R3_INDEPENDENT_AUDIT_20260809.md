# TemporaryAI Qwen3-TTS Original Voice Forge R3 - Independent Hostile Audit

Date: 2026-08-09  
Audit type: fresh independent hostile static audit plus isolated stdlib-only adversarial probes  
Execution boundary: no package installation, download, network access, Torch or speech-model import/load, GPU work, inference, voice generation, playback, or runtime/voice-route change was performed

## Verdict

`REJECT_FOR_BOUNDED_REAL_EXECUTION`

R3 closes the four precise Attempt 02 reproductions in its ordinary mocked
suite, but the end-to-end parent acceptance proof still has two independently
reproduced classes of acceptance-critical defect:

1. the exact-wheel binding accepts an arbitrary extra executable `.pyd` when
   that file is declared with the unrestricted
   `INSTALLER_GENERATED_BYTECODE` reason; and
2. the parent does not bind the post-exit worker/profile JSON to the exact
   hashes returned by the verified child, does not reconcile their candidate
   identity/profile hash to the reserved bundle, and does not require the
   artifact-seal keys to name the three fixed artifacts. This lets altered
   evidence relabel the candidate and replace both final WAV identities while
   the parent reports successful revalidation.

This is a rejection of the current acceptance proof, not a finding about the
quality of Qwen3-TTS, CUDA, Blackwell, or any proposed voice. The manifest must
remain `IMPLEMENTED_REQUIRES_INDEPENDENT_AUDIT` with
`execution_allowed: false`. No real execution is authorized by this report.

## Exact frozen scope

The R3 harness manifest is 5,033 bytes with SHA-256
`3116650bf4937c77af9937fede8ee187f16165ab3a3d21ee3c2e08e6579bcada`.
All 14 listed paths were independently reopened after testing; every byte count
and SHA-256 matched exactly.

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `TemporaryAI/config/temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2.json` | 6,884 | `8ae41050fcb5cef73d6dfc65a60a97302b0e8d7278f1dd40cc1cc9908233bab1` |
| `Voice/sidecars/qwen3_tts_voice_forge_v2/environment_spec_v2.json` | 3,633 | `8cc507aaa6737a8d61920242f3c6e9cd3b0ac4670aa90cbc3a728f3cac88c69f` |
| `Data/voice/policies/temporaryai_qwen3_tts_voice_forge_bundle_registry_v2.json` | 154 | `089a88f4ddcf96a2c557d3d3200d095f6dfe9198add90997736963389dff940a` |
| `Data/voice/policies/qwen3_tts_voice_forge_evaluation_corpus_v2.json` | 433 | `6348031cbbc8205d03d44dbdbef1fdf3d2ae984e8a7027347d4fdee11a5a1853` |
| `tools/qwen3_tts_original_voice_forge_worker_v2.py` | 163,093 | `b22d735abdc649760ff65134bbdb157bd039ec71abdd04ad081b33f5d99f222c` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v2.py` | 48,980 | `88c4d3856d2854e91ee5266802dc87f9af3ea1bd2b2304eac1d8ed44e602ec45` |
| `TemporaryAI/config/qwen3_tts_voice_forge_harness_manifest_v2.json` | 5,557 | `682d95880d93fffa68a7c9bbf6005ca52e59f1ab241be827c3f0c1d2938844a4` |
| `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_ACCEPTANCE_HARNESS_R2_CHECKPOINT_20260809.md` | 10,672 | `c48444632f3af96d064ef01bfacb21cbdbd644415e66fae7e5ce1c399e056310` |
| `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R2_INDEPENDENT_AUDIT_20260809.md` | 17,870 | `cc77ae5f8b2d068b4133e259a7141bc9d3c5485ec1bc546a32f6ce44ef3b0639` |
| `System/Docs/TEMPORARYAI_QWEN3_TTS_ORIGINAL_VOICE_FORGE_R2_REPAIRED_INDEPENDENT_AUDIT_ATTEMPT_02_20260809.md` | 14,481 | `304f28d06cd37e45693dd88206a7979cde5c8e7cf729c33cf9dc36e2e59bad00` |
| `tools/qwen3_tts_voice_forge_r3_guards.py` | 33,123 | `869ee27a048d2c40b8f1433b1fb17abf94c538f32bf3e74ec68417a2f9b4045c` |
| `tools/qwen3_tts_original_voice_forge_worker_v3.py` | 17,134 | `dcf9803afe4c519f19ff2eb6fc677454eb5b33d0e0d62861cfefe689ac90b020` |
| `tools/run_temporary_ai_qwen3_tts_voice_forge_acceptance_v3.py` | 17,858 | `f2aa4dca82bed34a88f46a4e8529829072f1aba0f56e61d12d1be522957eb53d` |
| `Testing/test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v3.py` | 27,123 | `7bb2b518d11a2ab1e19213369fa07cb01815445dff284b2e5c2831203c07d7a8` |

The rejected Attempt 02 audit and frozen R2 manifest, worker, runner, and test
remain unchanged. This report is append-only and is not inserted into or used
to mutate the rejected R3 seal.

## Verification performed

The sealed R3 suite was run with bytecode writes disabled:

`py -B -m unittest Testing.test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v3 -v`

Result: `22/22 PASS`.

The combined frozen R2 and R3 focused suites were then run:

`py -B -m unittest Testing.test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v2 Testing.test_temporary_ai_qwen3_tts_original_voice_forge_acceptance_v3 -q`

Result: `82/82 PASS` in 2.775 seconds.

Those suites were treated as non-conclusive evidence. A separate stdlib-only
hostile probe used synthetic temporary WAV, JSON, distribution, RECORD, and
wheel fixtures. The probe source was 36,017 bytes with SHA-256
`e9fc2a209dcb422ea7279fc4fc787204fb59698a06298b4085f0d02b55c84b13`.
It completed with exit code 0 and the verdict
`REJECT_FOR_BOUNDED_REAL_EXECUTION`.

## Control 1 - persisted reusable prompt: passed the bounded static probe

`PersistedPromptRuntime` reopens the saved reference WAV, serializes the
created prompt, reads the exact persisted prompt bytes back from
`runtime_clone_prompt.pt`, deserializes them, compares deterministic semantic
hashes, and passes only the reloaded object to `generate_clone`.

The hostile runtime asserted object identity, not merely value equality: the
object supplied to generation was the deserialized object and was not the
original caller object. Corrupt bytes and a parseable byte substitution both
failed before generation. The exact clean fixture prompt SHA-256 was
`9eb86f5cb32fa4eacc02e965306d30639ec3357cdba3a0f305009bf8148fbc0e`.

This control is correct inside the sealed worker path. The parent-evidence
binding defect below still means the parent can be shown altered prompt-use
claims after the verified worker exits unless it anchors the exact child-returned
manifest/profile hashes.

## Control 2 - evaluator and direct WAV mutation detection: locally passed

With the original worker-produced seals unchanged, both of these hostile cases
failed closed with `R3GuardError: sealed artifact hash mismatch`:

- an evaluator changed the reference WAV before returning; and
- the clone WAV changed after worker evidence and before parent validation.

The evaluator proxy checks both WAVs before and after each public evaluator
operation, again before worker acceptance, after profile/manifest writes, and
in the parent after clean exit. Silent or structurally invalid replacement WAVs
also fail.

This local control does not cure the broader parent evidence substitution in
Blocker 2, because the parent accepts newly supplied seals whose key-to-path
mapping was never constrained to the required filenames.

## Control 3 - installed distribution enumeration: passed

The R3 guard independently enumerates actual direct `.dist-info` roots and
reconciles them one-to-one with the declared inventory and distribution
evidence. The hostile fixtures confirmed:

- an omitted `.dist-info` distribution relabeled as loose was rejected;
- a declared distribution whose metadata rows were relabeled loose was
  rejected; and
- the complete one-to-one two-distribution fixture was accepted.

This closes the exact Attempt 02 installed-metadata omission/relabeling exploit.

## Blocker 1 - arbitrary executable installed extras can evade wheel binding

`bind_wheel_to_installed_distribution` binds every non-RECORD wheel member to
an installed member by exact bytes and SHA-256. It then treats every installed
path absent from the wheel as acceptable when the environment row supplies the
same path/bytes/hash and one of four reason strings. The reason check does not
constrain the path, extension, metadata root, bytecode layout, or corresponding
wheel source member.

The hostile fixture first proved that a metadata-only Torch wheel fails and
that different installed `torch/__init__.py` bytes fail. It then added the
unbound executable path:

`torch/injected.pyd`

The installed RECORD and declared difference were updated with its real bytes
and hash, but the file was absent from the exact wheel. Labeling it
`INSTALLER_GENERATED_BYTECODE` was accepted. The returned evidence listed
`torch/injected.pyd` under `installer_generated_differences` and set
`exact_wheel_to_installed_record_and_files_bound: true`.

That boolean is false for this accepted fixture: arbitrary executable code was
not supplied by the exact wheel.

Required repair: restrict each installer-difference reason to an exact bounded
path/type policy. In particular, bytecode must be a valid `__pycache__/*.pyc`
derived from a corresponding exact wheel `.py` member; it must never authorize
`.pyd`, `.dll`, `.exe`, source, or arbitrary package payload. Installer,
`direct_url.json`, and REQUESTED metadata must be limited to their exact
distribution metadata paths. Add hostile tests for executable/source extras
under every allowed reason.

## Blocker 2 - parent acceptance is not bound to exact child outputs, identity, or artifact names

The verified R3 worker prints an in-memory result containing exact
`manifest_sha256` and `profile_sha256`. The parent captures stdout but only
writes it to `worker_stdout_v3.log`; it does not parse those returned hashes or
use them as the post-exit trust anchor.

`validate_parent_artifacts` checks only:

- worker-manifest schema and status;
- equality of the two supplied `artifact_seals` objects;
- current files matching those supplied seals; and
- supplied prompt booleans/hash/semantic-hash consistency.

It does not require:

- worker-manifest `bundle_id`, `candidate_id`, and `opaque_voice_id` to equal
  the reserved/parent-verified bundle;
- profile identity and owner/queue authorization hashes to match the worker
  manifest and reservation;
- worker-manifest `profile_sha256` to equal the exact profile bytes;
- the parent-read manifest/profile hashes to equal the exact hashes returned
  through the verified child's stdout pipe; or
- `reference_wav`, `clone_test_wav`, and `runtime_clone_prompt` seals to map
  uniquely to `original_design_reference.wav`, `runtime_clone_test.wav`, and
  `runtime_clone_prompt.pt`.

Two isolated hostile probes were accepted:

1. the worker manifest identified `candidate-a`, while the profile identified
   `candidate-b`, carried unrelated authorization/queue hashes, and did not
   match the manifest's claimed profile SHA-256; and
2. both required WAV seal keys pointed to the same `substitute.wav` while
   `original_design_reference.wav` and `runtime_clone_test.wav` were absent.

The second probe returned all of the following simultaneously:

```json
{"accepted":true,"accepted_path":"substitute.wav","both_required_wavs_absent":true,"both_seal_keys_same_path":true,"parent_claim":true}
```

Here `parent_claim: true` is the guard's
`parent_reopened_and_revalidated_every_final_artifact` result. The result is
therefore not derived from reopening every required final artifact.

The frozen R2 core still correctly rejects named-person/imitation text, changes
the queue binding when candidate/job/nonce changes, rejects an owner candidate
mismatch, consumes the exact nonce append-only, and constructs the honest R3
profile/manifest from the trusted bundle. The defect is the unanchored
post-process parent acceptance layer: altered JSON can relabel otherwise honest
execution after the worker exits.

Required repair: parse one exact child result from captured stdout; require its
fixed paths and hashes before reading either JSON; compare the manifest's
profile hash to both the child-returned hash and current profile bytes; reconcile
all bundle/candidate/voice/authorization/queue fields to the reservation and
profile; require the exact unique artifact filenames for each seal key; and
repeat hash/seal checks immediately before the append-only parent acceptance.
Add hostile regressions for candidate/profile/hash mismatch, duplicate or
swapped artifact paths, arbitrary substitute paths, and a forged prompt-use
claim in post-exit JSON.

## Other controls retained

Static and synthetic probes also confirmed the existing fail-closed behavior
for original-trait-only job identity, named-person/imitation defense in depth,
exact queue-binding changes, owner/candidate mismatch, nonce reuse, real-ASR
mode labels, transcript fidelity, separate speech probability, pure-tone
rejection, generic/resident collision, normalized speaker-embedding sample
rate, bounded RSS sampling, early parent failure evidence, and the deliberately
narrow offline-flags/network-nonuse claim.

These passing controls do not outweigh either blocker.

## Re-audit boundary

Do not authorize a bounded real voice-forge execution on this R3 verdict. Keep
the R3 manifest inert and preserve every R1/R2/R3 source, checkpoint, test, and
prior audit. A subsequent append-only repair should change only the minimum
implementation/tests/checkpoint/manifest needed to close both blocker classes,
then rerun all four Attempt 02 exploits, the new executable-extra probe, the
candidate/profile/hash probe, the exact-artifact-path probe, and the complete
prior focused suites under another fresh independent audit.
