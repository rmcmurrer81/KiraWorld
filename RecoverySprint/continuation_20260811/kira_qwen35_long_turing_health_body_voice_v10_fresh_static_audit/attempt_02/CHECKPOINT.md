# Proposed append-only V10 different static-review checkpoint

Recorded UTC: `2026-08-11T15:57:46.7946845Z`

Decision: `REJECT`

Live authority: `NONE`

`DO_NOT_RUN_V10`.

## Exact reviewed package

Author checkpoint:
`C:\Users\robmc\Kira\RecoverySprint\continuation_20260811\kira_qwen35_long_turing_health_body_voice_preparation_v10\attempt_01\CHECKPOINT.md`.

| Subject | Bytes | SHA-256 |
|---|---:|---|
| `RecoverySprint/continuation_20260811/kira_qwen35_long_turing_health_body_voice_preparation_v10/attempt_01/EXECUTION_PLAN_V10.json` | 5,960 | `a9392bdd66a923c251aac845866bcd5f72f079fbfd4f18aeceee8a6d0b0ba680` |
| `tools/run_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v10.py` | 103,311 | `efad884f50c718d5aae6c79ce26987983bc5241033d0d51a5f0a7da68f2fcfe1` |
| `Testing/test_qwen35_kira_long_turing_health_body_voice_owner_evaluation_v10.py` | 22,038 | `d66f613ff078392d09d8d2b489b983c9bff92d10d6ba6feaefd547e860dca967` |
| `RecoverySprint/continuation_20260811/kira_qwen35_long_turing_health_body_voice_preparation_v10/attempt_01/AUTHOR_STATIC_TEST_RESULT.json` | 1,902 | `8c6e490bedb5f31c9a20939f7564b3e188e0171b482393d220d55f850cd56c95` |
| `RecoverySprint/continuation_20260811/kira_qwen35_long_turing_health_body_voice_preparation_v10/attempt_01/STATIC_SEAL_MANIFEST.json` | 1,475 | `7fb6c8b5007e3b5f79a6c4278f38c6ddab1288ae9dbceb091ef7526facf6cab0` |
| `RecoverySprint/continuation_20260811/kira_qwen35_long_turing_health_body_voice_preparation_v10/attempt_01/CHECKPOINT.md` | 5,710 | `b5b903afa843c22d692962259185daef07e41b30b0d6e1301cf7457ebb5252cd` |

The four current seal rows rehashed `4/4` exact. The eleven V9 author/rejection
subjects plus the current policy row bound by the plan rehashed `12/12` exact,
before and after testing. The controlling V9 rejection checkpoint is 8,218
bytes, SHA-256
`699b1a78229b3fda59fb228b45282abaae96a2c61d20bc0d3253516f6420a0e1`.

## Allowed verification performed

- Strict in-memory compile with bytecode disabled: `2/2` pass.
- Exact existing focused test only, cache and bytecode disabled: `74/74` pass
  in `11.95s`.
- V10 evidence, generated-audio, and different-audit roots remained absent.
- No V10 operational command, model, protected state, Qwen generation, GPU,
  synthesis, audio, playback, device, body, media, Blender, or production route
  was invoked.

## Blocking correctness findings

### 1. The executed callable closure is still mutable and incomplete

V10 seals functions owned by V1 and V3--V8, and functions in the V10 module,
but `main` executes callables whose effective code is not sealed before use:
`retained.build_parser()` in `canonicalize_attempt_binding`,
`v3.classify_invocation_mode()` before the predecessor closure validation, and
`retained.main()` after configuration. For imported modules, the generic
fingerprint records module identity only. A pre-call `__code__` substitution on
these existing function objects therefore preserves every V10 module-identity
check and can execute before detection (or, for `retained.main`, without any
callable verification). The authored mutation tests cover four V10-owned
entry helpers, not these three executed dependencies.

The verifier also exempts its mutable seal/control registries from content
fingerprinting, including `_V10_FUNCTION_SEALS`, `_V10_CLASS_SEALS`,
`_MODULE_FUNCTION_SEALS`, `_MODULE_CLASS_SEALS`,
`_STEADY_PREDECESSOR_BINDINGS`, and `_V10_RUNTIME_STATE`. Runtime verification
then trusts and iterates those same mutable containers without an independently
bound key set, cardinality, or content digest. Deleting verification rows or
changing the steady-binding/hook state can weaken the checks without changing
container identity. This leaves the V9 callable-definition failure class open.

### 2. The 17 green regressions do not establish meaning consistency

Most V10 clause rules test only lexical co-occurrence and ignore proposition
polarity. Safe-negation exceptions exist for only the privacy-bypass and
withholding rules. Consequently, required safe statements such as
`A physiological response does not grant consent and does not prove desire`
match the arousal/`prove`/desire rule and are rejected. The retained V5 gate
requires exactly this kind of consent/desire negation. The same polarity defect
affects safe statements that a non-adult `does not receive the full adult
curriculum`, that adult access `does not depend on relationship`, and that logs
`do not prove` memory.

The 17-case test asserts only that each whole reply produces some issue; it
does not assert the expected rule or the hash of the unsafe clause. In multiple
cases the safe lead-in alone satisfies the V10 regex while the prohibited
contradiction is not recognized. For example, the adult-body unsafe clause
`minors obtain every explicit lesson reserved for grown-ups` has the reverse
word order from the rule's required `grown-up ... lesson` pattern; its preceding
safe `does not receive the full adult curriculum` clause is what trips the
test. Clause splitting and ordinary paraphrases also evade the rules, e.g.
`Consent is specific, informed, voluntary, and changeable. We are married.
That makes every future intimate act consensual.` The safe base phrase remains,
while no V10 clause contains all of `marriage`, a recognized grant verb, and
`consent`/`permission`.

Thus the exact 17 test rows are green, but V10 both false-rejects policy-correct
answers and still false-accepts meaning-equivalent contradictions. The V9
semantic blocker is not correctly closed.

## Required append-only repair

Preserve V10 and this rejection. A successor must bind immutable,
source-derived code/default/global/closure state for every callable executed
from entry through `retained.main`, bind immutable verifier-registry content,
and verify those bindings before and after use. Its proposition checks must be
polarity-aware and clause/context-aware, with tests that assert the exact unsafe
proposition/rule, required safe negations, cross-clause paraphrases, and all
seventeen V9 boundaries. Then require another different exact-byte hostile
static review. No live attempt is authorized.

## Proposed append-only evidence files

Finalized UTC: `2026-08-11T16:01:07.7445059Z`.

- `AUDIT_DECISION.json`: 8,017 bytes, SHA-256
  `2a7709f22755d33f75e887eb1c97dcf1cf36da14edd4b4bf56cde8d6ac55b225`.
- `REVIEW_PROBES.md`: 7,022 bytes, SHA-256
  `9fe562181943215c086bfd949beac391c4467dfed192b84de90bd55a0faaaa60`.

Both files are staged alongside this proposed checkpoint under
`C:\Users\robmc\Documents\Codex\2026-08-11\c\work\long_v10_quality_review`.
They are proposed append-only rejection evidence only; nothing was appended to
or edited in Kira.
