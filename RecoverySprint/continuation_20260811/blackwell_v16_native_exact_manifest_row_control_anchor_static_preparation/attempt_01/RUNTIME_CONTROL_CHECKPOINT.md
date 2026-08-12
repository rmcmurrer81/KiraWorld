# Blackwell voice V16 runtime control checkpoint

Status: `AUTHOR_STATIC_ONLY_PENDING_BUILD_SEAL_AND_DIFFERENT_FRESH_AUDIT`

Execution authority: `NONE`

Candidate invoked: `false`

Python candidate invoked: `false`

V15 is permanently `CONSUMED_FAILURE_DO_NOT_RERUN`. Its exact accepted audit,
one exit-code-4 attempt, and absence of both output files are retained evidence,
not reusable authority.

V16 is an append-only native manifest-row repair. It replaces V15's separate
whitespace-sensitive fragment searches and 512-byte field window with one
complete compact JSON row token per binding. A row is accepted only once and
only with the exact path, positive byte count, and lowercase SHA-256. Missing,
duplicate, whitespace-mutated, split, cross-row, decoy, wrong-size, wrong-hash,
NUL-bearing, or wrong-count seals fail before output.

V16 retains the exact V15 Python source, validator, control config, immutable
origin binding, loader typing, complete namespace/path graph state, and full
V15/V14/V13/V12 slot checks. It adds no model or voice path.

Only a new different-reviewer V16 acceptance can authorize at most one
no-argument bounded disconnected static-control validation. Any invocation,
including failure, consumes that V16 decision. It must stop before model, GPU,
Torch, CUDA, Chatterbox, synthesis, audio, playback, latency, network,
subprocess, person state, production route, body, or Blender.
