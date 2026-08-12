# Blackwell voice V15 different fresh static review probes

Recorded UTC: `2026-08-11T16:59:34.2596946Z`

Reviewer task: `/root/voice_v15_quality_review`

Decision: `ACCEPT_STATIC_ONLY`

Execution authority exercised during review: `NONE`

The reviewer did not invoke the sealed V15 executable or the V15 Python
candidate. The only candidate-specific suite run was the existing PowerShell
suite with `-Phase PostSeal`. The review did not load Python through the native
controller, load a model or GPU, synthesize or play audio, measure latency, or
write under `C:\Users\robmc\Kira`.

## Probe 1: controlling evidence and exact 21-row seal

The V15 checkpoint and seal, plus the V14 rejection decision and checkpoint,
were read first. Both an opening and closing rehash produced `21/21` exact
subjects, `21/21` unique paths, and zero mismatch. The manifest is 4,557 bytes,
SHA-256
`f3d451041796c2bfbdf5dbe52f3a485b227f67b01af051e9e95c35b40549d932`.

| # | Subject | Bytes | SHA-256 |
|---:|---|---:|---|
| 1 | `Core/persistent_blackwell_voice_integration_v15.py` | 44,606 | `adecc01013fefab8a76f6558b6a91cf33ce82f5ed9e8921a45b77abf5d169e7e` |
| 2 | `tools/native/kira_blackwell_voice_control_anchor_v15_validator.py` | 21,931 | `2bf232b07b0b7b93de8776f5210bd2d89068ad76cb4ee46555b861ad2818d16a` |
| 3 | `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/candidate_config.json` | 3,725 | `e282667bcddf46c83d74b2e1ff56b4eed81c88b12a10177b50fca030a1f5faac` |
| 4 | `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/native_control_contract.json` | 4,393 | `6b5808b14d1c1dbbe23968afb03813ec430ec9e80a1780f454fb6524deafe7f8` |
| 5 | `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v15/README.md` | 1,303 | `45140bc00613c269f7207c86eeb4d3c24eda3bf97127cb4774c90dbd64bc5d99` |
| 6 | `tools/native/kira_blackwell_voice_control_anchor_v15.c` | 70,512 | `5563fb180e3295f2258ea02c89c4a7c54e8a729da73ea0f0c76ab6d3e557c951` |
| 7 | `Testing/test_blackwell_persistent_voice_candidate_v15_native_anchor_static.ps1` | 11,373 | `df8212542c5db05a9337b4c046078eba53b093a721618bd3cb87c8dfd7bd0aa3` |
| 8 | `RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/RUNTIME_CONTROL_CHECKPOINT.md` | 1,234 | `701efab09fd674a7f39e542fb831945575591b92490caafbd952e24967fecc4b` |
| 9 | `RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/AUTHOR_PACKAGE.json` | 2,748 | `7d2af69240bb1111a5dfd9e5207e277d697c86f9a5d8dcd91ee835dde5d29ae8` |
| 10 | `tools/native/kira_blackwell_voice_control_anchor_v15_identity_anchor.h` | 2,388 | `84d6b215c0b0a5d57ef3fdc167c40d8abdcbdf3622da5b3443bb426f35d5b0c4` |
| 11 | `tools/native/kira_blackwell_voice_control_anchor_v15.obj` | 98,765 | `df8e9b21a70aa9cc659c9f4019f5752d06133f803e67d68ab52d4ae507692351` |
| 12 | `tools/native/kira_blackwell_voice_control_anchor_v15.exe` | 175,104 | `7d8b807b54df5c980ecca2758e1d4359b3d385e3382839b8fd3101c16ede0a4f` |
| 13 | `RecoverySprint/continuation_20260811/blackwell_v15_native_exact_control_anchor_static_preparation/attempt_01/BUILD_AND_STATIC_TEST_RESULTS.txt` | 2,629 | `013df9131f87f87d4af1cd73b2675409048f9655efe0f6b3404256d6c3053774` |
| 14 | `Core/persistent_blackwell_voice_integration_v14.py` | 42,108 | `1faeb894bc9ab9e0bd13c06d6af42497c548ee15310ba97c1cc56df902e26d5f` |
| 15 | `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v14/candidate_config.json` | 6,184 | `c517afc9953ceae527f88afb0361b1022bcc45d19fc9c577d6e6e58f8ad96695` |
| 16 | `RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/CHECKPOINT.md` | 4,050 | `e800b28381fa1c2462b0499d3b2e4a03d3e59a0726793c5f74df59394675b3e2` |
| 17 | `RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_static_preparation/attempt_01/STATIC_SEAL_MANIFEST.json` | 6,425 | `f995cf68ba1b82de0f56acb11c1b1bf73667602beae0a1e685c8eebde13cc4e8` |
| 18 | `RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_fresh_static_audit/attempt_01/AUDIT_DECISION.json` | 4,399 | `b555938d847955c2fb2844bc1894570ce06ec8b53e3011c9ec9bb9f865c78ecb` |
| 19 | `RecoverySprint/continuation_20260811/blackwell_v14_native_exact_control_anchor_fresh_static_audit/attempt_01/CHECKPOINT.md` | 3,806 | `9f15de0358f7563861f034d36fca67fcb14aee0026d90242040807c3b8447fb7` |
| 20 | `C:/Python314/python314.dll` | 6,767,440 | `a07f7d09c3121492bb066535c6d0811df5fbc2090cbca7031a97bb47ce1480c9` |
| 21 | `tools/native/runtime/python314_stdlib_v3r4.zip` | 28,997,479 | `7e07541a67b8eba5835c9c371ec90e5732fba6602576ae0a6f22e09b09271846` |

## Probe 2: approved authored PostSeal suite

Command:

`powershell.exe -NoProfile -ExecutionPolicy Bypass -File Testing/test_blackwell_persistent_voice_candidate_v15_native_anchor_static.ps1 -Phase PostSeal`

Result: exit `0`, marker
`V15_IMMUTABLE_ORIGIN_BOUND_HOSTILE_STATIC_TESTS_PASS`.

The suite performed compile-only Python checks and canonical JSON/source-text
checks. It did not import or invoke the V15 candidate.

## Probe 3: independent exact-source MSVC build and analysis

The exact sealed C source was compiled directly from its Kira path with MSVC
x64 `19.50.35730` into separate reviewer scratch paths. Strict compilation used
`/W4 /WX /O2 /MT /guard:cf /DUNICODE /D_UNICODE /std:c17` and linker
`/guard:cf /WX bcrypt.lib`; exit `0`, zero diagnostics. A separate
`/W4 /WX /analyze /c /DUNICODE /D_UNICODE /std:c17` pass exited `0` with zero
diagnostics. Its 59-byte analyzer XML contains an empty `DEFECTS` element.

| Independent artifact | Bytes | SHA-256 |
|---|---:|---|
| `build/kira_blackwell_voice_control_anchor_v15_review.obj` | 98,765 | `244e762256aa0133e5f6af7bd74a3916f3f4e0be24613f99c78806f7a39a2df5` |
| `build/kira_blackwell_voice_control_anchor_v15_review.exe` | 175,104 | `cc17b2aba316619fb7e4ac40e1c77bdf22d706979c25feb7e764afc52f4ea932` |
| `analyze/kira_blackwell_voice_control_anchor_v15_review_analyze.obj` | 61,240 | `172804a841219ac8e6183db2afc8911aa3dc4b56966a2951ff861f72ed87600c` |
| `analyze/kira_blackwell_voice_control_anchor_v15_review_analyze.nativecodeanalysis.xml` | 59 | `ba052e3b011b8f8a3e59a7b5c3120d3c9496a6c3e2fd73c55013bde5e2642bc5` |

## Probe 4: static PE inspection

Both the sealed and independently rebuilt images report:

- machine `8664` / x64;
- optional-header magic `20B` / PE32+;
- High Entropy VA, Dynamic Base/ASLR, NX Compatible, and Control Flow Guard;
- Guard flags `0x10017500`, explicitly decoded as CF instrumented and FID table
  present, with Guard CF function count `0x33`;
- exact imported DLL set `bcrypt.dll`, `KERNEL32.dll`;
- no static Python DLL, process, or shell import.

## Probe 5: closure of the four V14 blockers

1. Immutable origin-bound result: V15 source lines 939-976 return an exact
   13-element built-in tuple and recursively reject mutable/non-built-in state.
   Validator lines 423-442 require exact tuple shape and exact immutable tree,
   plus `state[4] is attestations` and `state[5] is expected_v14_graph` together
   with exact value equality. No `BlackwellV15StaticControlSnapshot` exists.
2. Exact loader types: validator lines 435-439 require an exact five-element
   tuple, exact-string tag, exact value
   `("private_globals_only", None, None, None, False)`, and exact `False`
   Booleans for all six authority slots. The subsequent recursive exact-type
   walk prevents equality-spoof objects.
3. Complete mutable graph state: source lines 399-413 and validator lines
   80-93 serialize `_StaticPath._text` and every `_StaticImportNamespace` slot
   (`__name__`, `machinery`, `Path`, `Any`). Unsupported opaque instances fail
   closed. The source and validator cross-compile signatures match field for
   field; same-graph signatures additionally retain identity.
4. Complete module/package slots: validator lines 243-265 cover the V15, V14,
   V13, private V14 graph, private V12, and normal V12 module slots; the V15,
   V14, and V13 `Core` attributes; and the normal V12 parent-package attribute.
   `_slots_clean` runs before, between, and after private graph executions, the
   stored factory call, revalidation, and destruction (lines 330, 354, 356,
   376, 397, 399, 412, 447, and 460).

## Probe 6: canonical config and default-off boundary

The 3,725-byte V15 config passed the existing suite's duplicate-rejecting parse
and exact byte comparison against sorted-key, minimal-separator UTF-8 JSON plus
one LF. V15's private parser independently rejects duplicate keys at lines
230-258 and byte-compares canonical encoding at lines 304-309. Exact config
keys, six predecessor rows, predecessor sizes/digests, and exact Boolean types
are enforced at lines 713-819.

Every config and source authority value remains default-off. The two Python
route functions only raise `V15StaticControlError`, and source inspection found
no module-level call of the factory or either route. The native controller has
a future no-argument entrypoint, but it fails closed before any output or
Python load unless the exact independent audit TSV and digest sidecar exist.
Those two Kira audit inputs and both candidate output paths were absent at the
opening and close of review. The native source contains no model, GPU, voice,
synthesis, playback, latency, network, subprocess, person, body, Blender, or
production route.

## Probe conclusion

No blocking defect was found in the requested V15 static scope. This is an
`ACCEPT_STATIC_ONLY` decision: it proves only the sealed disconnected control
anchor and may at most support one separately transcribed, no-argument bounded
static-control validation. It grants no voice, model, GPU, synthesis, audio,
playback, latency, retry, production, or other live authority.
