# Blackwell voice V17 whole-document manifest author checkpoint

Recorded UTC: `2026-08-11T20:46:12.7228794Z`

Status: `AUTHOR_SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT`

Execution authority: `NONE`

## Exact repair

V16 remains preserved and is `REJECTED_UNINVOKED_DO_NOT_RUN`. Its clean build
did not overcome four blocking native-boundary defects: trailing bytes were
accepted, a valid 42nd whitespace-form logical duplicate was accepted,
terminal `.`/`..` segments were accepted, and new-operation provenance still
contained V15 identities.

V17 uses a canonical-only whole-document parser. Whitespace is not part of the
grammar. It consumes every top-level key in exact order and type, parses every
subject as an object with exact `path`, `bytes`, `sha256` field order, counts
55 actual objects, rejects path reuse, and requires each object at ordinal N to
equal exactly Binding N. It then consumes `]}` and requires exact EOF.

Path validation operates by segment and rejects bare, first, interior, and
terminal `.` or `..`, empty segments, slash edges, backslashes, quotes,
control/non-ASCII characters, and colons. The one exception is not generic
drive authority: only the exact locked `C:/Python314/python314.dll` Binding is
recognized. Byte counts begin at 1-9, remain decimal, and use checked uint64
accumulation. Digests are exactly 64 lowercase hexadecimal bytes.

## Exact closure

The 55-row canonical seal contains:

- six V17 runtime rows: source, identity header, executable, config, contract,
  and README;
- every one of the exact 41 V16 author-seal rows;
- the exact V16 author seal; and
- seven V16 rejection artifacts: decision, checkpoint, parser result, review
  probes, audit TSV, audit sidecar, and closure rehash.

Seal: 11,748 bytes, SHA-256
`64fad216711534d8e1e3c014ae616fc651b36f70847c6efc18d55566dc5ab75a`.

## Static evidence

- Exact compiled parser harness: `83/83` checks passed.
- Exact source-predicate mutation gate: `6/6` mutants rejected.
- Strict x64 `/W4 /WX /O2 /MT /guard:cf /std:c17`: pass, zero
  diagnostics.
- Separate `/analyze /W4 /WX`: pass, zero unsuppressed diagnostics.
- PE: x64 PE32+, high-entropy VA, ASLR, NX, CFG/CF-instrumented/FID table,
  Guard CF count `0x32`; imports exactly `bcrypt.dll` and `KERNEL32.dll`.
- PreBuild, PostBuild, and PostSeal static suites: pass.

Core identities:

- source: 83,635 bytes,
  `850cc18c8084c1cf4a0a8c8353289067bcbe8e7a27cc87fa77287f81b26cd1bc`;
- identity header: 6,591 bytes,
  `8fb7df074a1eb658cdefc7c84aa5d441e8397a6863b79fbeee7901b096b67e94`;
- object: 127,137 bytes,
  `17b7dbf117ecba86a6c4e013b8a45fff7722c37a6139fd3cfb7605fda515ad42`;
- executable: 157,696 bytes,
  `52a4376025bdb08902396c033b66d1626c126e56fcb8134bddb79979cb068a4a`;
- hostile harness source: 18,529 bytes,
  `d8bf5e2b65131b09445e72d31efda1a4b784cfca9d76e78c49c2046f3201875b`;
- hostile harness executable: 184,320 bytes,
  `123c874a7d0e3b1c58fdb787c69a8f78e966da99baa8d3b88b2a434e0a6999dc`.

## Boundary and next step

No Kira file was written by this author. V15, V16, V17, Python, model, GPU,
synthesis, audio, playback, latency, network, camera, microphone, speaker,
person state, body, Blender, Sarah, and production routing were not invoked.
No V17 evidence or outcome file exists.

Root may transplant exact bytes only into previously absent append-only paths,
rehash them, run the installed non-candidate PostSeal suite, and obtain a
different fresh audit. Author sealing is not acceptance and grants no run.
