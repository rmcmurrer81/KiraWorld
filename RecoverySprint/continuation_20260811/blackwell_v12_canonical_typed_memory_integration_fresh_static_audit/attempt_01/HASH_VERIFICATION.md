# Blackwell V12 exact-byte closure verification

Decision contribution: `REJECT`

The rejection is a correctness finding, not an integrity failure. Rehashing
before and after cache-free tests found the V12 seal, author checkpoint, all
seven sealed subjects, and all 28 predecessor/routing/audit boundaries exact.
No V12, V11, V10, predecessor, or earlier audit byte was edited.

## Outer metadata

| Subject | Bytes | SHA-256 | Result |
|---|---:|---|---|
| V12 seal manifest | 1744 | `50cef220de1ccb30c3f86adc05d9b1561c87f137c69c0be21aaa7074d0c2db15` | MATCH |
| V12 author checkpoint | 7013 | `c9725313ac1730e3e6346211dd94b09c5ea0dbf46f7ec8bf3f530b4b93033d54` | MATCH |
| V12 author result | 2007 | `bae410c7b37618ce9b8ca662509e75a47b721f618354bb68a001e13a57fad107` | MATCH |

## Seven sealed subjects

| Subject | Result |
|---|---|
| `Core/persistent_blackwell_voice_integration_v12.py` | MATCH |
| `Testing/test_blackwell_persistent_voice_candidate_v12_hostile_static.py` | MATCH |
| V12 `README.md` | MATCH |
| V12 `candidate_config.json` | MATCH |
| V12 `candidate_contract.py` | MATCH |
| V12 `canonical_typed_memory_binding.py` | MATCH |
| V12 `worker_entry.py` | MATCH |

## Twenty-eight preserved boundaries

All paths and SHA-256 values in `candidate_config.json` under
`preserved_boundaries` matched, including V8/V9/V10/V11 sources and seals,
accepted V10 static audit, the complete V11 rejection audit, and the approved
production routing file. The routing file remains SHA-256
`a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81`.

The candidate-required `AUDIT_AUTHORIZATION.json` remains absent. No candidate
live/generated output root was created.
