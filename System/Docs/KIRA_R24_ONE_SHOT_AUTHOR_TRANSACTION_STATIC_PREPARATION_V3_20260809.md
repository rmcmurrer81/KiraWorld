# Kira R24 one-shot author transaction — static preparation v3

Date: 2026-08-09  
Status: `STATIC_ONLY_INERT_R7_BINDINGS_UNSEALED_EXECUTION_AUTHORITY_FALSE`  
Candidate accepted: **no**  
Blender started: **no**  
R24 attempt created: **no**

## Append-only files

| File | Bytes | SHA-256 |
|---|---:|---|
| `tools/blender_author_kira_r24_one_shot_candidate_v3.py` | 19,463 | `df50a0b4729aae33aaa4abd571b053062d0af194606d7ec3b4b8544e018e674c` |
| `tools/run_kira_r24_one_shot_author_transaction_v3.py` | 52,757 | `6c5f01bd73a50dddd4372385265ce198191a7659aa09dcf114af0402b939bd8f` |
| `Testing/test_kira_r24_one_shot_author_transaction_v3.py` | 19,191 | `2e6c0e025257ca959ea35cd12f7630400ed2b8446fae95ed28001cdd466a6f03` |

V1 and v2 workers, controllers, tests, and static checkpoints were not edited. The v3 suite rehashes all eight preserved files against their accepted identities.

## V2 rejection closure

1. **Post-`CreateProcessW` ownership:** the v3 native adapter creates its cleanup context before opening streams and records process handle, thread handle, and PID immediately after successful `CreateProcessW`. Every later failure inside `create_suspended` performs local termination, bounded wait, stream/handle closure, and error propagation before returning control.
2. **Cleanup truth:** complete cleanup raises an observed-owned-failure containing its cleanup report. Incomplete cleanup or a cleanup exception raises `R24OneShotCleanupV3Error` with the cleanup error recorded. No cleanup exception is suppressed.
3. **Private save and publication:** Blender's only possible save target is a nonce-private file and uses `check_existing=True`. Blender never receives the sealed-staging or final public candidate as its save target. The worker uses Win32 `MoveFileExW(..., flags=0)` to publish private bytes to a reservation-derived sealed-staging name without replacement. Only after the author process and Job tree are proved exited does the controller use a second no-replace move from sealed staging to the final candidate.
4. **Raw/reparse boundary:** each raw lexical path component is inspected before any resolving operation and re-inspected at open, save, move, hash, and extraction boundaries. A real Windows junction alias is rejected by the suite.
5. **Real process and reservation evidence:** the suite launches harmless Python probes with the production Win32 path: `CREATE_SUSPENDED`, configured kill-on-close Job, assignment before resume, exact resume count, direct wait, Job-tree quiescence, handle closure, and independent post-close `OpenProcess`/zero-time-wait verification. Production child execution exposes no injectable native or evidence callback.

The exclusive reservation file is created with `CREATE_NEW` and a live handle that shares read access only. An integration test holds it across two real child lifetimes; both children are unable to overwrite or delete it. Write access succeeds only after the controller closes the reservation handle.

## Verification

Command:

```text
py -B -m unittest Testing.test_kira_r24_one_shot_author_transaction Testing.test_kira_r24_one_shot_author_transaction_v2 Testing.test_kira_r24_one_shot_author_transaction_v3 -v
```

Result: **61 passed, 0 failed, 0 skipped** (`1.330s`). V3 contributes 20 passing tests.

The v3-specific real Windows tests prove:

- harmless suspended-process/Job lifecycle and direct evidence;
- injected post-create failure terminates, waits, closes all owned resources, and leaves no active PID;
- an injected cleanup exception is recorded and propagated after the underlying process cleanup;
- actual junction/reparse alias rejection before resolution;
- real no-replace private-to-sealed and sealed-to-final publication behavior using temporary files;
- reservation lifetime across both actual child roles;
- strict rejection of altered/injectable child evidence.

All integration artifacts were confined to repository `tmp` temporary directories and removed by the tests. They did not call Blender, mutate a Blend, create `attempt_01`, render, activate, assign, publish, or accept a body.

## Remaining authorization boundary

`EXECUTION_AUTHORITY_GRANTED` remains `False` in both v3 files. The accepted R7 contract and R7 author-operation byte/hash bindings remain symbolic (`None`). The controller fails on authority before package scans, dependency verification, process inventory, reservation, or child launch. This static preparation is not production acceptance and cannot execute the Blender transaction.

## Rollback

No rollback of v1, v2, R19, or any candidate is needed because none was changed. To withdraw v3, archive or remove only the three v3 implementation/test files and this v3 checkpoint. Do not modify the preserved v1/v2 files or their checkpoints. No runtime attempt directory or Blender artifact exists to recover.
