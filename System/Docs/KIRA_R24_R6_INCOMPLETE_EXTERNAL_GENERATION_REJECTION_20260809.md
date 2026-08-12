# Kira R24 R6 incomplete external-generation rejection — 2026-08-09

Status: **R6 STABLE BUT INTERNALLY INCOHERENT; NO STATIC PASS OR EXECUTION AUTHORITY.**

A second Codex session produced several useful R6 implementation pieces, but
the final byte set combines incompatible generations. A read-only monitor
waited for more than 90 seconds of stability before auditing it. No Blender
process ran and no file was edited by the audit.

Current implementation hashes:

| Artifact | SHA-256 |
|---|---|
| worker | `84529d1290b28668c4fa95bd80a208dbc1e442053671b28639fde06fdd8959a6` |
| extractor | `fc2aab4efe54926f94e9089a56a87d96667697222ca1dd094349197b9cb50a56` |
| semantic helper | `581da4fd1239e9516e51a8037c661fb135240a8f47a1ac3245e7a702e17e4bae` |
| sealed author stub | `28ca2ba1a0f0682f0565c9b0e5d6f896ece11266bcbb34b68522a8561ec06472` |
| fresh evaluator | `25d72292d536fc5b5a049734cd65c9ca881cce176f80cd22b23a7f909bd960ee` |
| focused test | `10fee31cfa703ead256ef2600010ac5ccc7ae3750be10fcefa757c1bd038d2c3` |
| stale contract | `d65325b9ea52d84dbcf923833ac59f473ec417f77ad62a38f0989bf4897e399c` |
| stale checkpoint | `3cc9acdd4a696b86ee3aad05d5bd6f0642ca8dd296186dfb3aed031e12c779b0` |
| stale proposal | `a669d144e499907d25154b0b6b17c6033387e6a6a0ac3fef5175965121822131` |

Reasons R6 cannot load or run:

- worker seal constants are zero and its contract identity check fails;
- the contract semantic seal is wrong and its parent/implementation/amendment
  inventories do not match the worker generation;
- contract extractor/test hashes point to older files;
- helper, author stub, and fresh evaluator are unbound;
- `PACKAGE_MANIFEST.json` and `STATIC_TEST_RESULTS.json` are absent;
- exact Blender `5.1.0`, inherited outside-E* world non-regression, and a
  receipt-bound job nonce/command hash remain incomplete.

The two Blender safety flags and several requested semantic projections are
present in current code, and R4/R5 preservation plus false authority state are
intact. Because the package cannot pass its mandatory load gate, the stale
test suite was not run and no pass is claimed.

Any continuation must be append-only R7, adopt only reviewed R6 strengths,
reconcile all seals/inventories, close the remaining deep-audit boundaries,
and undergo a new independent audit. Do not patch R6 in place or launch it.
