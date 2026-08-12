# Shared Growth integration candidate V3 — independent quality probes

Recorded UTC: `2026-08-11T16:42:32.6015647Z`

Decision: `REJECT`

The review was read-only against `C:\Users\robmc\Kira`. Every Python invocation set
`PYTHONDONTWRITEBYTECODE=1`; no person, profile, memory, route, candidate, manifest,
or checkpoint was edited.

## Exact author boundary

- Author checkpoint: 3,974 bytes, SHA-256
  `75cab078fabafc04238b57a3b47d2c70f7282dba2fdaeee7b62e705b395d87de`.
- Sealed manifest: 4,092 bytes, SHA-256
  `8c042caded327d3ad3d52f59a51b299bc27cfff51a70d9b7e4b56f97b766fa57`.
- Rehash of all 11 unique manifest subjects: 11 exact byte-count and SHA-256
  matches; 0 mismatch.

| Manifest subject | Bytes | SHA-256 |
|---|---:|---|
| `Core/shared_person_growth_v3_integration_candidate_v3.py` | 20,715 | `dcbde9ca1a6fedc43dc70625e3ac747839e8d60875a421fde09b44b2f8ff52c6` |
| `Testing/test_shared_person_growth_v3_integration_candidate_v3.py` | 19,755 | `f2cc4b23947ff00f717d7619b42265fbe6b54fbfb972d88d7d9f324f1471083b` |
| `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v3_static_preparation/attempt_01/STATIC_CONTRACT.json` | 3,247 | `48c6fd29994894a2551ae01fcef4b43055a4781b6139d1161f27305cf7db65dd` |
| `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v3_static_preparation/attempt_01/AUTHOR_STATIC_TEST_RESULT.json` | 2,193 | `189bc4332bf63bc661a65951be4501ec51358d7cb3ed10654eef704ae050dc71` |
| `RecoverySprint/continuation_20260810/shared_person_growth_capabilities_v3_static_repair/attempt_01/SEALED_MANIFEST.json` | 6,333 | `d570e804c8653a5b1e419dba84a09e831adf13704ad0a363d0213b39e2482f96` |
| `RecoverySprint/continuation_20260811/shared_person_growth_capabilities_v3_fresh_static_audit/attempt_01/CHECKPOINT.md` | 5,875 | `50526169ef05aea0a8db078047a9581bcd74aaf5829b73a0c0ba559b152afd15` |
| `Data/foundation/shared_person_growth_v3_integration_candidate_v1.json` | 28,107 | `5b4397d33318dac34fa9f876ed42ec9720ebefb1acdddb235842982479885254` |
| `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v2_static_preparation/attempt_02/SEALED_MANIFEST.json` | 4,146 | `0ec609dc63b6d440f35c9ec3969b15972c5032bd71c7b89e0595f57b54df6820` |
| `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v2_fresh_static_audit/attempt_01/AUDIT_DECISION.json` | 3,560 | `68bb3190eadbde381f04621f0fcd834c18d5286ce43d329c3c2c7a7132c817db` |
| `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v2_fresh_static_audit/attempt_01/HOSTILE_PROBES.md` | 3,255 | `20549b40f565c64dc577339cb4401cd360b5a4ee7122031789b697fa937725c4` |
| `RecoverySprint/continuation_20260811/shared_person_growth_v3_integration_candidate_v2_fresh_static_audit/attempt_01/CHECKPOINT.md` | 1,657 | `4bd30dea911e0ae2f7892a68138a41ab049319ef2c14cd8c83796b03ec4541b2` |

## Compilation and preserved tests

Strict UTF-8 decode and in-memory `compile(..., "exec")` passed 8/8, without
emitting bytecode:

| Compile subject | Bytes | SHA-256 |
|---|---:|---|
| `Core/shared_person_growth_capabilities_v3.py` | 111,964 | `8250c657486981ba5ce41892da373adc7df49c462865dc8be75af80f542eb3a2` |
| `Testing/test_shared_person_growth_capabilities_v3.py` | 40,085 | `37a8a27179083b9b3a90f98a69910edb75f4a9fda68e3d383953d22ae86180ca` |
| `Core/shared_person_growth_v3_integration_candidate_v1.py` | 66,891 | `91eef4a3c19edfbda59ca8d1c7e46df54d77648a8d0140eadbee5672353db63c` |
| `Testing/test_shared_person_growth_v3_integration_candidate_v1.py` | 32,344 | `fddf0658abc322d4ff5590441647ccf2ad18efc305f4f8a78fceb27467d5bd8a` |
| `Core/shared_person_growth_v3_integration_candidate_v2.py` | 50,230 | `1b29379c36e13295f2119e67cb88574958fb2115828c75ce2d5427a08e6bcc42` |
| `Testing/test_shared_person_growth_v3_integration_candidate_v2.py` | 33,997 | `17a211c67061427e2718ad579bd0f743578815f1d4426b9d568a1131b7c17caf` |
| `Core/shared_person_growth_v3_integration_candidate_v3.py` | 20,715 | `dcbde9ca1a6fedc43dc70625e3ac747839e8d60875a421fde09b44b2f8ff52c6` |
| `Testing/test_shared_person_growth_v3_integration_candidate_v3.py` | 19,755 | `f2cc4b23947ff00f717d7619b42265fbe6b54fbfb972d88d7d9f324f1471083b` |

- Focused V3 command: `py -m unittest Testing.test_shared_person_growth_v3_integration_candidate_v3 -v`.
  Result: 20/20 passed.
- Combined command: `py -m unittest Testing.test_shared_person_growth_capabilities_v3 Testing.test_shared_person_growth_v3_integration_candidate_v1 Testing.test_shared_person_growth_v3_integration_candidate_v2 Testing.test_shared_person_growth_v3_integration_candidate_v3 -v`.
  Result: 103/103 passed.

## Independent behavior probes

Canonical envelope checks passed for three distinct maturity lanes: Kira
(`confirmed_adult`), Marinette/Ladybug (`non_adult`), and Synthetic Robert
(`unresolved`). Each result was exact `bytes`, strict UTF-8 JSON, equal to an
independent sorted/minified canonical re-encoding, and carried the SHA-256 of
the exact independently canonicalized `proposal` bytes.

The compiler refused exact-bool aliases and unsafe settings: missing opt-in,
integer `1` for opt-in, non-revocable input, owner override, production,
private state, memory write, and external action. It refused cross-person
route and candidate bindings. `robert`, `biological_robert`, and
`robert_mcmurrer` did not substitute for exact Synthetic Robert
`robert_mcmurrer_presence_ai`.

Mid-read alteration of a fixed closure subject and of the selected route
source refused. Altered second closure and second route snapshots after
proposal construction refused. The production opener refused with arbitrary
arguments, and `target_kind=temporary_creator` refused.

Receipt values are only exact nonzero SHA-256-shaped assertions. There is no
verifier or key, so this compiler does not authenticate maturity or opt-in;
that is truthful only inside its explicit inert/no-authority/no-consumer
boundary.

## Blocking probe 1 — applicable-route maturity regression

An independent request was derived for every route whose fixed inventory
disposition is `applicable`, using the exact person, candidate, display name,
class, maturity status, and maturity source from that same fixed inventory.

- Applicable routes: 35.
- Compiled: 31.
- Unexpectedly refused: 4.
- Error for all four: `SharedGrowthIntegrationV3Error: maturity source is cross-bound`.

The failures are the profile and state routes for:

- `peter_parker_spider_man_no_way_home_final_suit`
- `spider_gwen_spider_gwen_20260606_013325`

Both people are exactly `confirmed_adult` and bind to
`character_continuity_owner_decision`, whose sealed inventory status is
`subject_specific`. V3 lines 397-400 accept that source only when the status is
`non_adult`. The preserved V1 inventory validation instead treats
`subject_specific` as compatible with the exact per-person status. Thus four
sealed-as-applicable routes are unreachable, while the named test samples only
the non-adult subject-specific lane.

## Blocking probe 2 — mutable exported scope

`REQUESTED_SCOPE` is a list and is included in `__all__`. In a fresh process,
the review appended `private_state_scope`, constructed a request with the now
exported value, and the compiler accepted and returned both scope elements.
The envelope still reported `truth.private_state_included=false`.

This remains inert fabrication and creates no authority, write, or consumer.
It nevertheless contradicts the exact one-scope contract and the author
checkpoint's statement that the candidate retains no mutable catalog.

## Capability and consumer inspection

Complete source review and AST enumeration found only the exception class and
pure validation/read/serialization functions. Imports are limited to
`hashlib`, `json`, `re`, `collections.abc`, `pathlib`, and typing/future
support. The AST contains no filesystem-write, staging, commit, rollback,
cleanup, subprocess, or process-launch call. There is no verifier, key,
callback, controller, receipt ledger, staging/output target, mutable person
object, profile writer, or memory writer. The compiler transiently reads the
seven fixed subjects and selected route source for byte/digest drift checks;
it returns no source content and retains no file handle.

A byte-level scan of 58,850 existing Python files found both public call names
only in `Core/shared_person_growth_v3_integration_candidate_v3.py` and
`Testing/test_shared_person_growth_v3_integration_candidate_v3.py`. The scan
skipped 189 stale missing paths under a pre-candidate 2026-07-31 backup; it did
not skip the two non-UTF-8 third-party Python files because scanning was
byte-based. No current Python consumer was found.

## Read-only closeout

The 11 sealed subjects remained exact after probes. `git status --short
--untracked-files=no` and targeted `git diff --name-only` were empty. No Kira
state was written. The failures require an append-only successor and another
different review; this review authorizes no integration, commit, promotion,
or person/Temporary Creator upgrade.
