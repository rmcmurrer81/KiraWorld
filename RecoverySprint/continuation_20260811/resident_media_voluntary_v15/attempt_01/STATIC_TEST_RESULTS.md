# Resident-media voluntary gate V15 author static results

Date: 2026-08-11

Status: `AUTHOR_STATIC_PASS_PENDING_DIFFERENT_FRESH_INDEPENDENT_AUDIT`

## Exact rejected predecessor defect reproduced

The focused V15 suite first constructs a separate preserved V14 validator and
uses the exact ordinary method-closure traversal identified by the independent
V14 audit. It reaches `_SnapshotStateV14`, changes the retained
`StimulusCatalog._manifests` tuple without changing that catalog object's cached
`sha256`, and obtains a V14 static plan whose reported `catalog_sha256` differs
from the digest freshly derived from the manifest contents used by the plan.

This reproduction changes only a disposable in-memory V14 test instance. No
sealed predecessor byte is changed.

## V15 repair checked

- A V15 validator is an exact immutable tuple subclass containing only an
  identity marker, exact person identifier, canonical snapshot `bytes`, and
  their exact SHA-256 string.
- It retains no `StimulusCatalog`, manifest mapping/list, weak-key registry,
  lock, authority, adapter, ledger, anchor, receipt history, or commit callable.
- Every operation revalidates the immutable snapshot bytes and creates only a
  fresh local catalog long enough to derive canonical catalog bytes and their
  SHA-256.
- Caller mutation of the catalog used to construct the test snapshot cannot
  alter the bound V15 bytes or emitted catalog digest.
- Direct closure/container/slot traversal from
  `validate_static_evidence_plan` reaches no `StimulusCatalog`,
  `WeakKeyDictionary`, V14 snapshot state, authority double, V12 adapter, or
  V12/V13 ledger.
- A returned plan envelope is an exact built-in tuple containing canonical JSON
  `bytes` and their derived SHA-256. Its two immutable items are verified before
  emission and by `decode_static_plan_envelope_v15()`, which returns a fresh
  decoded copy. A caller cannot add or replace a member on the exact built-in
  tuple class. A consistent fabricated pair decodes only as its own bytes; a
  mismatched pair refuses.
- Required-role completeness, exact scalar types, snapshot/catalog/manifests,
  module/package/function/class/member/code/default/global/closure bindings,
  and the exact refusing record method remain exercised.
- Twenty-four concurrent static validations returned only non-authoritative,
  non-committed plan envelopes and changed no authority-double state.

## Accepted final commands

Strict in-memory compile:

```text
STRICT_IN_MEMORY_COMPILE_PASS=2
```

Focused V15 suite:

```text
Ran 20 tests in 0.674s
OK
```

Combined preserved V3 through V15 suite, run from the Kira root with the V15
author overlay first on `PYTHONPATH`:

```text
Ran 230 tests in 2.426s
OK
```

The combined count is 210 preserved V3-V14 tests plus 20 V15 tests.

## Preserved author-iteration results

Before the accepted final suite, two test-authoring iterations failed and were
retained in this account rather than described as passes:

1. `Ran 20 tests in 0.655s` — `FAILED (failures=1, errors=4)`. Three malformed
   evidence cases and one malformed permit correctly raised the V14 base error
   rather than V15's error subtype, and the closure assertion counted V14's
   predecessor bootstrap registry. The repair added V15 error translation and
   changed the predecessor guard to retain only the original unbound verifier,
   exact predecessor type and identity integer, not the predecessor bootstrap
   object.
2. `Ran 20 tests in 0.632s` — `FAILED (errors=1)`. The hostile test still looked
   for the predecessor preflight function after the V15 translation wrapper was
   introduced. The test was corrected to mutate the V15 wrapper closure; the
   production code did not change in that iteration.

After the first all-pass draft was sealed locally but before transplant or
independent audit, a bounded hardening pass replaced the plan-envelope tuple
subclass with an exact built-in tuple pair `(canonical_bytes, sha256)`. The
hostile test now proves that post-return tuple class/member replacement refuses,
module decoder replacement cannot change the two returned tuple items, and the
byte/digest invariant survives. The accepted final focused and combined runs
above are the post-hardening runs.

A first command attempted the 230-test combined suite from the author workspace
instead of the Kira root. It ran all 230 tests but three historical V4-V6 tests
reported `FileNotFoundError` for their intentionally cwd-relative predecessor
paths. Re-running the identical suite from `C:\Users\robmc\Kira`, which is the
historical suite's required working directory, passed all 230 tests.

## Negative execution evidence

- no production opener was connected;
- no authority protocol was called;
- no receipt was consumed;
- no anchor was read;
- no compare-and-swap or durable commit was attempted;
- no resident-media route or pointer was changed;
- no media was opened, decoded, rendered, played, or presented;
- no model, network, camera, microphone, GPU, audio device, body, or Blender
  workflow was used;
- no person, memory, preference, relationship, or Sarah state was changed;
- no seeing, hearing, attendance, enjoyment, learning, preference, memory,
  emotion, or consciousness result is claimed.

V15 remains disconnected, default-off, static/no-commit, and pending a
**different fresh independent audit**. These author tests do not accept it.
