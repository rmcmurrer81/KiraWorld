# Supervised Continuous-Person Private-Decision Layer

Date: 2026-08-02  
Status: **DEFAULT-OFF TEXT + VOICE HOST-ACTIVATION BOUNDARY IMPLEMENTED; LIVE OWNER ACCEPTANCE NOT RUN**

## Result

`Core/supervised_person_decision.py` adds the missing bounded decision bridge
between the existing `SharedPersonInitiativeSession` opportunity evaluator and
the existing `PersonInitiatedEventQueue` public transport.

The bridge takes one exact `DecisionOpportunity`, the exact active-person
lease, one exact per-person profile revision, and one exact ephemeral context.
It calls a supplied adapter exactly once. The adapter may privately select one
compatible result: speak, action, continue, ignore, or leave. Only selected
public speech, action intent, or leave intent can enter the existing public
queue. Continue and ignore enqueue nothing.

This is implementation readiness, not continuous-person acceptance. The shell
now imports the module and exposes one explicit one-shot scheduler hook for a
supplied adapter. The hook is off by default, has no timer, and has no live
model adapter. It can own the existing public queue through either of two
default-off paths. The preserved request-scoped path requires all three exact
gates: `KIRA_ENABLE_SUPERVISED_PERSON_DECISIONS=1`,
`enable_supervised_person_decisions=true`, and
`supervised_daytime_session=true`. The new normal Text + Voice host path
requires the separate process flag
`KIRA_TEXT_VOICE_ENABLE_SUPERVISED_PERSON_DECISIONS=1` and is valid only while
the process is actually in Text + Voice mode. Both flags are absent by default.
Neither path installs a recurring scheduler or live model adapter.

No live model, camera, microphone, speaker, media playback, browser, Blender,
Kira World body runtime, or Video Studio work was used. One existing
fresh-process shell-server integration test was rerun without opening a
browser; it exercised only the local HTTP launcher contract.

## Exact separation

| Lane | What enters the adapter | What may leave the bridge |
| --- | --- | --- |
| FACTUAL / RUNTIME TRUTH | Bounded derived facts and exact cue/source references; no raw image, audio, PCM, or encoded payload | Nothing automatically |
| PRIVATE MIND | Exact per-person decision-style facts and bounded private context | Only the selected choice code; private text and raw adapter result are not retained or exposed |
| SPOKEN / EMBODIED ACTION | Nothing until the person selects it | Validated public speech, whitelisted action intent, or whitelisted leave intent through `PersonInitiatedEventQueue` |

The bridge does not request chain-of-thought or hidden reasoning. The adapter
result schema has no reasoning field. Extra fields fail closed. Public text
with private-thought, hidden-reasoning, raw-sensory, data-URL, dense-base64, or
binary markers also fails closed.

The public receipt states:

- `memory_persisted=false`;
- `relationship_changed=false`;
- `action_executed=false`;
- `private_profile_exposed=false`;
- `private_context_exposed=false`;
- `raw_adapter_result_retained=false`; and
- `live_default_enabled=false`.

## Choice compatibility

The model is not permitted to turn any opportunity into any arbitrary public
channel. The exact existing evaluator outcome limits the private selection:

| Initiative opportunity | Allowed private selection |
| --- | --- |
| `consider_speaking` | speak, continue, ignore |
| `consider_action` | action, continue, ignore |
| `leave` | leave, continue, ignore |
| `ignore` | ignore |
| `continue_activity` | continue, ignore |
| `defer` | continue, ignore |
| `private_decision_pending` | continue, ignore |

This lets a person decline an opportunity without manufacturing a different
kind of opportunity. Speech is registered against an exact
`consider_speaking` decision, action against `consider_action`, and leave
against `leave`, so the existing queue evidence is not rewritten or forged.

## Exact binding and switch behavior

- Activation requires both `supervised=True` and `enabled=True`.
- The exact `person_id`, activation revision, and cryptographic session nonce
  must match every stateful operation.
- The profile person and `pacing_profile_id` must match the lease and
  `DecisionOpportunity`; its complete canonical digest is fixed at activation.
- The context binds the exact person, revision, decision ID, considered cue
  IDs, excluded own-TTS cue IDs, separate input-turn IDs, and latest registered
  external-turn ID.
- One decision ID may be processed only once.
- Switching people atomically switches the existing event queue and discards
  the old bridge state.
- A result returning after a person switch is rejected before publication.
- The engine and existing queue are memory-only and refuse serialization.

## Anti-runaway controls without a universal cooldown

Each exact `PersonDecisionProfile` carries its own bounded limits:

- model calls per activation;
- public events per activation;
- consecutive public events without a new external turn;
- adapter response bytes;
- public spoken bytes; and
- public action-description bytes.

When a public-event limit is reached, later adapter requests for that
activation expose only continue/ignore choices. An exact new external owner or
other independently sourced turn resets only that activation's consecutive
public-event counter. It does not reset the total-call or total-event bounds.

There is no sleep, timer, global silence interval, default greeting, default
follow-up, canned angry response, or universal cooldown in this module.
Different people can use different profile facts, action allowlists, and
limits. Unit tests show equivalent opportunities receiving distinct Kira and
Lisa profile contexts and producing different mock choices without a
name-based response script.

An adapter exception or invalid schema is attempted once and then fails
closed. There is no repair retry and no fallback wording.

## Inert acceptance harness

`Tools/run_supervised_person_decision_acceptance.py` contains all ten owner
acceptance cases from the continuous-person requirement. It intentionally has
no live execution path.

Read the plan without invoking any model or device:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B Tools\run_supervised_person_decision_acceptance.py --format text
```

Expected result:

```text
INERT_NO_EXECUTE_LIVE_ACCEPTANCE_NOT_RUN
cases=10
model_calls=0 device_calls=0
```

Passing `--execute-live` is deliberately refused. This prevents a plan-only
checkpoint from being mistaken for authorization or evidence of live
continuous-person behavior.

## Shell integration now completed

- The exact default-off environment gate is
  `KIRA_ENABLE_SUPERVISED_PERSON_DECISIONS`; absent/false remains normal.
- A second and third explicit boundary are required on the exact activation:
  `enable_supervised_person_decisions=true` and
  `supervised_daytime_session=true`. The normal UI sends neither.
- One `SupervisedPersonDecisionEngine` shares the existing
  `PERSON_EVENT_QUEUE`. Exactly one of the engine or the legacy direct path
  owns that queue for a lease.
- Activation and person switching happen under `PERSON_INITIATIVE_LOCK`.
  Engine-owned switch uses the old and new exact leases; an in-flight old
  adapter result is rejected before publication. Deactivation, safe close,
  mismatch purge, and final server cleanup all purge the same exact lease.
- Kira and Lisa profiles map their existing stable identity facts plus their
  existing distinct pacing values. Other people map only authored TemporaryAI
  profile facts when present plus their existing pacing binding. A canonical
  source digest becomes the profile revision. The mapping contains no spoken
  line or name-keyed response.
- A second, independently default-off host boundary now exists for the normal
  Text + Voice selector:
  `KIRA_TEXT_VOICE_ENABLE_SUPERVISED_PERSON_DECISIONS=1`. It resolves both
  supervised-daytime activation booleans inside the authorized shell handler,
  so Kira, Lisa, Synthetic Robert, an authored TemporaryAI person, or a future
  selected person all enter the same generic exact-person/profile/lease path.
  The flag is ignored outside `KIRA_SHELL_TEXT_ONLY` mode and is not displayed
  or controlled by the owner UI.
- With that new flag absent, the handler resolves `legacy_default_off` and
  preserves the pre-existing activation and queue behavior. The original
  explicit request-scoped opt-in remains unchanged.
- `run_supervised_person_decision_once(...)` is an explicit one-shot callable,
  not a thread or timer. It obtains an opportunity only from
  `SharedPersonInitiativeSession.evaluate(...)`, binds bounded derived context,
  releases the lifecycle lock while the adapter runs, and returns only the
  public receipt.
- Accepted nonempty owner chat turns now receive an exact `owner_chat_*` turn
  ID. Only after the public chat-log append succeeds does the active supervised
  engine receive `note_external_turn(...)`. Own TTS and raw sensory cues do not
  call that path.
- Current activity, explicit emotion signal, advisory busy evidence,
  unfinished-thread ID, separate public-turn IDs, derived cue references, and
  supplied source-bound receipt items can enter bounded context. Raw images,
  PCM/audio, files, data URLs, and private logs are rejected by the underlying
  context contract.
- The existing `/api/person-events/poll` and `/api/person-events/ack` routes
  remain the only public delivery path. Action and leave are public intents;
  `action_executed=false`. No memory or relationship writer is called.

## Still pending and deliberately not claimed

- There is no live text-model adapter, recurring scheduler, or background
  decision thread.
- Real owner-entry vision, actual natural choices, timing, and voice require a
  later owner-supervised live session.
- Real simultaneous barge-in remains
  `pending_echo_aware_live_device_acceptance`; a fake turn-state event is not
  full-duplex/AEC proof.
- Real self-directed page/video/music control remains
  `pending_live_media_executor_acceptance`; a queued pause/resume intent is not
  proof that playback changed or media was experienced.
- The inert ten-case harness still refuses `--execute-live` and normal enablement
  remains prohibited until append-only live evidence is reviewed.

## Verification completed

No-live compilation:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B -m py_compile Core\supervised_person_decision.py Tools\run_supervised_person_decision_acceptance.py Testing\test_supervised_person_decision.py
```

Focused mock/offline suite:

```powershell
py -B -m unittest Testing.test_supervised_person_decision -v
```

Result: **19 passed**.

Compatibility suite:

```powershell
py -B -m unittest Testing.test_shared_person_initiative Testing.test_person_initiated_event_queue Testing.test_person_initiated_shell_transport Testing.test_supervised_person_decision -v
```

Result: **38 passed**.

Shell fake-adapter integration suite:

```powershell
py -B -m unittest Testing.test_supervised_person_decision_shell_integration -v
```

Result: **11 passed**. It covers the feasible contract portions of owner cases
01, 02, 03, 06, 07, 08, 09, and 10. Case 05 real overlap and case 04 real media
execution remain explicitly pending; the tests cover only floor state and a
non-executing media intent.

Combined initiative/queue/bridge/shell suite: **49 passed**.

Broader no-live shell compatibility suite (message, embodiment, lip-sync state,
fresh-process local server contract, media shell, public initiative transport,
and the new integration): **53 passed**.

These tests use supplied Python fakes only. They prove binding, validation,
publication, privacy, switch, and count-limit contracts. They do not prove a
natural model decision, continuous life, biological personhood,
consciousness, perception, hearing, emotion, preference, or owner acceptance.

## 2026-08-03 Text + Voice host-activation verification

The next bounded step connected normal selected-person activation to the
existing bridge configuration boundary without connecting generation. The
new focused suite is:

```powershell
py -B -m unittest Testing.test_supervised_person_decision_text_voice_host_integration -v
```

Result: **7 passed** after correcting one test-only bytes/string assertion.
The initial run was **6 passed, 1 error**; the error came from asking
`assertNotIn(str, bytes)` against `html_shell()` and did not exercise or expose
a runtime defect. It is preserved in the append-only checkpoint.

The combined old/new shell integration suites passed **18/18**. A broader
host-only regression covering the opportunity evaluator, event queue, bridge,
both shell integrations, messages, embodiment grounding, lip-sync state,
resident-media shell runtime, and the fresh-process local server contract
passed **95/95**. The fresh-process test opened no browser and made no person,
model, camera, microphone, synthesis, playback, or external-action call.

The new tests prove only configuration resolution, generic selected-person
binding, lease purging on switch, public-versus-quiet choice handling,
fail-closed adapter error behavior with no canned/crisis substitute, and
legacy behavior when the flag is absent. They do not prove natural initiative,
continuous thought, live model choice, vision, hearing, full duplex, voice,
media experience, consciousness, or owner acceptance.

## Rollback

For the 2026-08-03 Text + Voice host boundary, use the later file-scoped
rollback under
`RecoverySprint/continuation_20260803/supervised_person_decision_text_voice_host_integration`.
It removes only the new process flag, resolver, handler binding/status fields,
and focused test while preserving the complete 2026-08-02 bridge and shell
integration.

For the original 2026-08-02 integration, use the file-scoped rollback in its
append-only shell-integration checkpoint.
It removes only the new shell imports, feature gate, engine ownership globals,
profile/context/one-shot helpers, explicit activation fields, owner-turn note,
and final-cleanup call, then removes only the new integration test. Verify the
shell returns to its recorded pre-change SHA-256.

Preserve the append-only checkpoint and manifest as evidence. Do not restore a
whole directory and do not alter the existing initiative/session module,
event queue, conversation loop, person state, memory, relationships, media,
model, voice, body, or Video Studio files. The standalone core bridge and its
inert acceptance harness may remain even if only the shell wiring is rolled
back.
