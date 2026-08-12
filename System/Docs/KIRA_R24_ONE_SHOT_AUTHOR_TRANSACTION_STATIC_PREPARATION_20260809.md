# Kira R24 one-shot author transaction static preparation — 2026-08-09

Status: **INERT STATIC PREPARATION PASSED; EXECUTION NOT AUTHORIZED.**

This package separates body authoring from evaluation. It does not treat an
evaluator as a mesh-authoring function and does not claim that any R24
candidate exists.

Files:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/blender_author_kira_r24_one_shot_candidate.py` | 20166 | `3cad1c2fb5a9fff9f52e8ed2e7051955dfa3ad1953b32362669661b441e9d631` |
| `tools/run_kira_r24_one_shot_author_transaction.py` | 27897 | `cb59960f8a48dd82de2dbd65c313c6df05d4c26176989c5c5e82fe92e18157c8` |
| `Testing/test_kira_r24_one_shot_author_transaction.py` | 15282 | `bb4cd25d331880537b81f78c444465518a2da2622f377dcf35550576ddba39fa` |

The controller and Blender-side worker remain fail-closed on symbolic R5 and
author-operation bindings. They cannot execute against the rejected R4.

Static/mocked verification passed `14/14` and proves:

- full rehash of all 49 files in the exact R19 attempt-06 package manifest;
- `load_ui=False` for the exact hash-locked R19 source;
- exactly one candidate save in the Blender author worker;
- exactly one author child followed by exactly one read-only fresh-reopen
  child, with no automatic retry;
- `--background`, `--factory-startup`, `--disable-autoexec`, and
  `--python-exit-code 1` on both Blender invocations;
- a controller-owned Windows Job/PID kill-on-close boundary;
- clean author-process exit and Job closure before the candidate digest is
  established; and
- no attempt directory, source open, Blender process, or candidate creation
  during static verification.

Current blockers:

1. A corrected R5 evaluator must be sealed and independently accepted.
2. The separate external-surface author operation must pass its own geometry
   quality gates and be hash-bound.
3. The symbolic dependency slots must be replaced with exact reviewed hashes.
4. A new independent audit must approve the combined transaction before the
   controller may reserve `attempt_01` or launch Blender.

No body, review images, movement evidence, Avatar Builder gallery entry,
internal module, activation, assignment, export, or publication is produced by
this preparation.
