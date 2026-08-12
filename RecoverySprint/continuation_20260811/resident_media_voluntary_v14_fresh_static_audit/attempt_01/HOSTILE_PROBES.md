# Resident-media V14 independent hostile probe

Recorded UTC: `2026-08-11T13:44:02.6823182Z`

Verdict: `REJECT`

## Exact preservation and positive checks

- The different reviewer rehashed all 9 V14 sealed records with zero drift.
- V14 seal: 2,894 bytes, SHA-256
  `7699ff183c24bcbf2fb580b5d9fcb119c19dd36e71503c22bd5b3720ef723736`.
- V14 core: 46,445 bytes, SHA-256
  `4ac4d63cde6a2535549f404021e999fc925914f1a1296dff490af674b97afa8b`.
- V14 test: 24,843 bytes, SHA-256
  `474f299c8da88313fd70b8c1372ed4a5b1629ba92dae25926db1cc81ade3cd02`.
- Focused V14 suite: 19/19 pass.
- Preserved V3-V14 suite: 210/210 pass.
- The no-commit architecture is real: no authority protocol, receipt,
  V12/V13 ledger or adapter, CAS, durable commit, production route, live media,
  model, device, audio, video, person state, memory, body, Blender, or Sarah
  operation was used.

## Blocking probe — mutable catalog with a stale reported digest

`Core/resident_media_voluntary_gate_v14.py` stores a mutable
`StimulusCatalog` plus a digest computed once. Its state verification compares
the catalog object's mutable `sha256` attribute to the cached state digest; it
does not freshly canonicalize and hash the current manifests.

Ordinary Python method-closure introspection followed
`validate_static_evidence_plan -> state_for -> states` to the closure-held
`WeakKeyDictionary`, the bound snapshot state, and then
`state.catalog._manifests`. The reviewer changed one manifest's
`source_relative_path` using only a mock catalog. `state.verify()` still
passed. The validator then emitted
`VALIDATED_STATIC_PLAN_NOT_AUTHORITY_NOT_COMMITTED`; the plan retained the old
catalog digest while a freshly recomputed digest of its current manifest
contents differed.

The stale digest is placed into the returned plan by the V14 plan-construction
path. Thus V14 can describe altered catalog contents under a digest that no
longer binds those contents. Passing the authored suites does not cure this
independent integrity failure.

## Scope and next step

The probe was static and mock-only. No media was opened or played and no
synthetic person's state changed. Preserve all V14 bytes and this rejection.
V15 must be append-only, use immutable canonical catalog data or freshly
recompute and compare the exact current contents before every emitted plan,
close ordinary closure/state mutation routes, retain no commit capability, and
receive a different fresh independent audit.
