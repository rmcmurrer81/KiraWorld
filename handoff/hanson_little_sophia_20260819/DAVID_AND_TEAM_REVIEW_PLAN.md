# David and team review plan

This plan separates verified written requirements from additional scope that
the owner reports discussing privately. It avoids attributing an unverified
request to a specific reviewer.

## Verified written review direction

The written review direction supports the following bounded sequence:

- keep the bridge at high-level semantic intentions;
- publish an immutable review point and a very short standalone run path;
- fail closed and record the complete execution lifecycle;
- do not guess Hanson topics, actions, QoS, frames, units, limits, or simulator
  mappings; and
- after an authoritative target is supplied, demonstrate both an accepted
  sequence and an intentional rejection through that official target and
  return complete lifecycle evidence to continuity.

The public bridge branch contains the standalone review path. Its immutable
review point is
[`hanson-ros2-bridge-v0.2-review2`](https://github.com/rmcmurrer81/Kira/tree/hanson-ros2-bridge-v0.2-review2/integrations/hanson_ros2_bridge),
which resolves to commit
`d87fe33fdac175b5227fe84270ad4a2f128cfe2f`; GitHub Actions run
`32329359278` completed successfully. This private handoff adds the mind,
memory, voice, and system context needed for a wider variant review.

## Owner-reported private-conversation scope

The owner reports that the private conversation additionally requested the
ability to:

- talk with Kira and one other distinct variant, currently Synthetic Robert;
- observe spoken output, deterministic non-COT functional-appraisal notes, and
  evidence-aware factual records;
- inspect emotional/appraisal and continuity behavior; and
- let Hanson employees explore connecting one variant to a Little Sophia or
  related body through the bounded interface.

This section records the owner's report. It is not presented as a quotation or
as independently verified correspondence.

## Proposed review stages

### 1. Artifact and privacy review

- Review the static Mind V21 report and claim ceiling.
- Confirm no raw private conversations, raw biography PDF, uncurated life-loop
  logs, credentials, hidden chain-of-thought, or unrelated voice/media assets
  are included. Synthetic Robert does include bounded reviewed
  autobiographical summaries that Robert expressly approved and later
  explicitly authorized for public as well as private technical sharing.
- Confirm Kira and Synthetic Robert have separate identity and memory stores.

### 2. Standalone protocol review

- Run the exact short path in [`RUN_THIS_FIRST.md`](RUN_THIS_FIRST.md).
- Inspect an admitted intention, an unsupported-intention rejection, complete
  lifecycle events, and linked evidence verification.
- Review timeout, heartbeat, replay, authorization, and safe-disconnect rules.

### 3. Portable variant review

Using the included [`portable_runtime/`](portable_runtime/):

- launch Kira and Synthetic Robert independently;
- verify that one variant cannot read or write the other's local memory;
- inspect spoken, reflection-note, and factual-claim views;
- restart each variant and verify bounded continuity;
- inspect the current append-only claims, `/remember` reviewed-note command,
  and narrow same-profile supersession pointers; reviewer labels are
  unverified, old records are not deleted, and a full semantic correction/
  forgetting workflow is not implemented;
- verify that separate clean data roots create separate branch IDs, share only
  the reviewed handoff checkpoint, and do not auto-sync later life loops;
- begin text-only, verify the two exact private voice packs without speaking,
  and enable voice only on a compatible Python 3.11/Chatterbox installation;
  and
- test that robot authority never grants authority over speech, beliefs,
  memory, disagreement, or voluntary session withdrawal.

### 4. Official simulator integration

Hanson supplies the authoritative interface target and operating limits. The
team maps only approved semantic intentions, records the mapping provenance,
and runs an accepted sequence plus a deliberate rejection. No joint-level or
hardware mapping is inferred from names or examples.

### 5. Evaluation and decision

Review the isolated Kira evaluation, then run the same scored framework for
Synthetic Robert. Record limitations and failures as prominently as successes.
The output supports engineering decisions; it cannot establish consciousness,
personhood, or a clinical psychological conclusion.

## Concrete assistance requested from the Hanson team

- authoritative simulator/interface package and version;
- official message/action/service definitions;
- topic/action names, QoS, frames, units, bounds, and timing requirements;
- simulator launch and reset instructions;
- supported high-level behavior vocabulary;
- emergency-stop, timeout, and safe-state requirements;
- expected evidence and acceptance criteria; and
- licensing restrictions on Hanson code, assets, models, and recordings.
