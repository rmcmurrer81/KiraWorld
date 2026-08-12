# Resident Media Voluntary Gate V14 - Static Test Results

Date: 2026-08-11

Candidate boundary: `NO_COMMIT_STATIC_VALIDATION_PLAN_ONLY`

Live execution: `NONE`

## Strict source compile

The focused suite compiles these exact source bytes in memory with
`dont_inherit=True` and `optimize=0`:

- `Core/resident_media_voluntary_gate_v14.py`;
- `Testing/test_resident_media_voluntary_gate_v14.py`.

Result: `PASS - 2/2`.

All Python commands used `PYTHONDONTWRITEBYTECODE=1` and `-B`.

## Focused V14 hostile/static suite

Command shape:

`py -B -m unittest -v Testing.test_resident_media_voluntary_gate_v14`

Result: `PASS - 19 tests in 0.225s`.

The suite proves all of the following for the authored bytes:

1. the production opener refuses without inspecting caller objects;
2. V14 accepts only exact canonical caller-supplied snapshot bytes and labels
   them unauthenticated, non-authority input;
3. opening a validator and producing page, video, and audio static plans leave
   the mock authority's anchors, issue/verification sequences, prior receipt,
   consumed receipt set, and issued receipt map exactly unchanged;
4. missing roles, false completion, boolean identifiers, integer identifiers,
   integer digests, numeric-only decoder digests, changed snapshot bytes, and
   changed snapshot types refuse;
5. the exact sealed `validate_and_record_static_evidence` method refuses
   because V14 contains no record or commit surface;
6. the returned slot-only validator exposes no inner, adapter, authority,
   proxy, catalog, anchor, ledger, instance dictionary, or commit attribute;
7. recursive traversal of its bound method closures, closure functions,
   containers, weak maps, and slot state reaches no V12/V13 ledger instance,
   V12 adapter instance, authority instance, or compare-and-swap bound method;
8. preflight/type-walker rebinding, `sys.modules` replacement, Core package
   attribute replacement, and a non-guard closure-cell mutation fail closed;
9. replacing the ordinary Python class record method can run only caller code;
   it reaches no retained authority/adapter/ledger/CAS capability and leaves
   the supplied mock authority state exactly unchanged, so the replacement is
   not project authority and creates no durable record;
10. no V12/V13 ledger or V12 adapter construction and no anchor read/CAS call
   exists in the V14 source;
11. no heavy model, media, GPU, playback, or Blender module is loaded by the
    import/open/plan path.

## Preserved V3-V13 regression suite

Command shape:

`py -B -m unittest Testing.test_resident_media_voluntary_gate_v3 ... Testing.test_resident_media_voluntary_gate_v13`

Result: `PASS - 191 tests in 1.544s`.

The first draft run was launched from the isolated draft directory and three
historical preservation tests reported missing relative evidence files. That
was a test-harness working-directory error, not a V14 assertion or product-code
failure. Re-running the exact same 191 tests from the Kira project root passed
191/191. No failed result was discarded or described as a product pass.

## Combined V3-V14 suite

Command shape:

`py -B -m unittest Testing.test_resident_media_voluntary_gate_v3 ... Testing.test_resident_media_voluntary_gate_v14`

Result: `PASS - 210 tests in 1.827s`.

## Exact authored inputs at result time

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `Core/resident_media_voluntary_gate_v14.py` | 46,445 | `4ac4d63cde6a2535549f404021e999fc925914f1a1296dff490af674b97afa8b` |
| `Testing/test_resident_media_voluntary_gate_v14.py` | 24,843 | `474f299c8da88313fd70b8c1372ed4a5b1629ba92dae25926db1cc81ade3cd02` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v14/attempt_01/EXECUTION_BINDING_V14.json` | 2,203 | `f0b0ef37318ac3b04a2b02b902a50690e2c0d1f8334872bae1f46691ba84f693` |

## Truth boundary

V14 did not call an authority protocol, consume any receipt, read any anchor,
or attempt any durable commit. No media was opened, decoded, rendered, played,
or presented. No model, network, camera, microphone, GPU, audio device, body,
Blender, Sarah, person, memory, preference, or production route ran or changed.
No person is claimed to have seen, heard, attended to, enjoyed, disliked,
learned, preferred, or remembered any media.
