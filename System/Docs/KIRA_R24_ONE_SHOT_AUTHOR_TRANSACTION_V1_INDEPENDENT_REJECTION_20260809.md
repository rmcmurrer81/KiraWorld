# Kira R24 one-shot author transaction v1 independent rejection — 2026-08-09

Status: **V1 PRESERVED, INERT, AND REJECTED FOR EXECUTION.**

The v1 static/mocked suite passed `14/14`, but an independent read-only audit
showed that those tests were insufficient to authorize a real Blender child.
No Blender process, source Blend, candidate, or `attempt_01` was created.

Preserved v1 hashes:

| Artifact | SHA-256 |
|---|---|
| Blender worker | `3cad1c2fb5a9fff9f52e8ed2e7051955dfa3ad1953b32362669661b441e9d631` |
| CPU controller | `cb59960f8a48dd82de2dbd65c313c6df05d4c26176989c5c5e82fe92e18157c8` |
| mocked/static tests | `bb4cd25d331880537b81f78c444465518a2da2622f377dcf35550576ddba39fa` |
| preparation checkpoint | `bc118f2be708cd0da30181b59a9427abb2802c746e7ca63fd31448c444554f84` |

Independent blockers:

1. `Popen` could start code before the child was assigned to a Windows Job.
   Job setup/assignment failure did not prove termination and wait of the
   already-running child.
2. The fresh-reopen child lacked an equivalent pre-execution assignment gate.
3. Injected mocked child records were trusted without proving assigned/resumed/
   exited/closed state, PID correlation, distinct author/reopen identities, or
   evidence-derived invocation counts.
4. The candidate path used check-then-save with Blender overwrite behavior,
   leaving a check/use overwrite race; candidate/extraction reparse paths were
   not rejected.
5. The author-exit → Job-close → digest order was correct, but independent
   child-tree quiescence after Job closure was not proved.

The exact R19 source and all 49 manifest entries did rehash correctly, symbolic
dependencies failed before source/Bpy/process use, one author followed one
fresh reopen with no retry in the mocked path, and the required Blender safety
flags were present. Those strengths remain useful but do not cure the process
ownership and append-only defects.

Any correction must be an append-only v2. V1 must not be edited, bound, or run.
V2 must use a suspended/pre-execution ownership gate, terminate and wait on
every assignment/resume failure, derive and validate all child evidence,
prove child-tree quiescence, and exclusively reserve a non-reparse candidate
target before Blender can save.
