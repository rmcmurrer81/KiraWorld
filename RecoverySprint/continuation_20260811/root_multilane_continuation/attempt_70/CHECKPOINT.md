# Root multilane continuation attempt 70

Date: 2026-08-11

## V3r29 exact installation

The append-only V3r29 Stage-1 author package was copied from the frozen
Documents/Codex author directory to
`RecoverySprint/continuation_20260811/kira_r25_medical_reference_proxy_v3r29_static_preparation/attempt_01`.

- transplant inventory rows: `26`
- source/destination byte and SHA-256 mismatches: `0`
- inventory: `5,556` bytes, SHA-256
  `af36d03d48328aa19d8320bd379ca5c4e8386d750110b2917691debeabdc2796`
- author-declared subject root:
  `ee704f4b125efd1ae378fb3789e9df952788afb165c9b1d12334da9399834b99`
- installed seal: `5,395` bytes, SHA-256
  `b4187e13fcb57204fd26ff6020044d0e5fd80ace5068514ba42da3f228e3f7ba`
- author-declared all-files root:
  `80e9ab2fff1614c5024d95008868b78990086b4e117536c5fd14920ac1e62bc9`

No product executable, materializer main, Blender, worker, body, save, reload,
render, model, camera, voice, live, or Sarah path was invoked.

## Installed-layout test result

The exact installed cache-free PostSeal command was run:

`py -B .../test_v3r29_static.py PostSeal`

It failed before a PASS result with:

`Refuse:materialization_ledger_root_scope`

The exact cause is a final-layout fixture defect. The hostile consumption test
creates its temporary directory under the installed test `ROOT`, which is now
inside `C:\Users\robmc\Kira`. The exact materializer correctly permits durable
consumption ledgers only under `C:\Users\robmc\Documents\Codex`; therefore the
test's own installed temporary path is refused before the intended retry probe.

This result does not prove the materializer repair unsafe, but it invalidates
an installed PostSeal PASS claim. V3r29 remains static-only and requires a
DIFFERENT Audit A to decide whether this is an isolated test-fixture defect or
whether the candidate has another blocker. No Stage-2 materialization/build
authority and no Blender authority exists.
