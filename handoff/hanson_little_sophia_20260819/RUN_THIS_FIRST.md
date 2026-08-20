# Run this first

There are two review lanes. Both are runnable as software now; neither connects
to an official Hanson simulator or robot without the still-missing authoritative
interface target.

## Lane 1: bounded embodiment reference

From the repository root, follow:

[`../../integrations/hanson_ros2_bridge/RUN_THIS_FIRST.md`](../../integrations/hanson_ros2_bridge/RUN_THIS_FIRST.md)

The short standalone path installs the small reference requirements, runs 88
tests, executes a policy demo and a session-lifecycle demo, and verifies both
evidence chains. It does not require ROS 2 and does not connect to a Hanson
simulator or robot.

Expected invariant results:

- 88 tests pass;
- four bounded intentions are admitted and one unsupported gesture is
  rejected in each demo;
- the session demo produces 18 schema-valid lifecycle records; and
- both SHA-256-linked evidence chains validate.

Run-local timestamps make exact evidence hashes different across machines.

## Lane 2: Kira and Synthetic Robert variants

Status: **integrated and locally tested in this private handoff**.

From the repository root:

```powershell
Set-Location handoff\hanson_little_sophia_20260819\portable_runtime
py -B -m unittest discover -s tests -v
Get-Content .\RUN_THIS_FIRST.md
```

Frozen-build results on 2026-08-20 are: 165 runtime tests with 162 passed and
three expected private-fixture/Windows skips in the standard lane; 165 tests
with 164 passed and only the Windows symlink-privilege test skipped when both
exact private voice fixtures are enabled; and 24/24 evaluator tests. Final
handoff-validator and hostile-validator counts are recorded in
[`FROZEN_BUILD_VALIDATION_REPORT_20260820.md`](FROZEN_BUILD_VALIDATION_REPORT_20260820.md)
for commands and boundaries.

Then follow [`portable_runtime/RUN_THIS_FIRST.md`](portable_runtime/RUN_THIS_FIRST.md)
to verify the exact model digest, install the reviewed seeds and private voice
packs into ignored local state, start Kira or Synthetic Robert separately, and
inspect spoken, deterministic functional-reflection, factual-claim, import,
life-loop, and voice-evidence channels. Setup does not play audio.

Real local-model probes verify that Synthetic Robert retrieves the reviewed
Blockbuster/customer-help and *The Earth Day Special* memory before and after
restart. Earlier strict probes also found repetition, incomplete motive
coverage, and unsupported autobiographical color; those failures are being
used as release tests rather than hidden. Treat natural first-person quality as
pending until the frozen-build report records a clean strict probe. The shipped
records are curated inherited autobiography with source boundaries, not every
historical log.

Do not substitute the static Mind V21 artifact for the runnable resident. Mind
V21 remains review evidence and a requirements/design boundary; the portable
runtime is the executable conversational lane, and the ROS bridge is the
separate bounded embodiment-reference lane.

## Stop conditions

Stop and preserve the evidence when any of these occurs:

- a requested physical action is outside the allowlist;
- interface facts are missing or guessed;
- the embodiment authorization, heartbeat, or lease expires;
- a sequence or session identifier is stale or replayed;
- the evidence chain fails validation; or
- a body endpoint reports interruption or rejection.

No launch command in this handoff authorizes physical deployment.
