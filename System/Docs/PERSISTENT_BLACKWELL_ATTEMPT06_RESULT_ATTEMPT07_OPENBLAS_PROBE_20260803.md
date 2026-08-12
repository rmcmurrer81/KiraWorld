# Persistent Blackwell Attempt 06 and Attempt 07 import diagnosis

Date: 2026-08-03 / 2026-08-04 UTC  
Status: `OPENBLAS_HYPOTHESIS_REJECTED_ROOT_CAUSE_UNRESOLVED`  
Candidate: inactive, private, not production  
Full GPU acceptance: not run  
Production voice routing: unchanged  
Packages, virtual environment, model cache, approved voice files: unchanged

## Current result

Attempt 06 remains the exact persistent-worker failure record. Attempt 07's
bounded live import A/B was executed after the body-work boundary and is
preserved append-only at:

`RecoverySprint/continuation_20260803/persistent_blackwell_attempt07_openblas_import_ab_probe/attempt_01/ATTEMPT07_OPENBLAS_IMPORT_AB_REPORT.json`

Its SHA-256 is
`008b04fbc89a606fff6713a2c1e2b858298eeb4da03257d5a082d190f5d4e94d`.
The result is not an acceptance pass:

- control, `OPENBLAS_NUM_THREADS` absent: Torch plus NumPy import passed in
  `1.074988` seconds (`1.391139` seconds child wall time);
- treatment, `OPENBLAS_NUM_THREADS=1`: import passed in `0.964216` seconds
  (`1.216039` seconds child wall time);
- both children exited cleanly and neither timed out;
- exact Torch was `2.11.0+cu130`; exact NumPy was `1.26.4`;
- no CUDA API, model load, audio generation, playback, Ollama call, package
  change, routing change, or candidate promotion occurred in either arm;
- the report's own assessment is
  `BOUNDED_AB_DOES_NOT_SUPPORT_ATTEMPT07_ACCEPTANCE`;
- `openblas_single_thread_hypothesis_supported=false`;
- `root_cause_proven=false`;
- `ready_for_separate_full_attempt07_acceptance=false`.

The empty stderr files prove that neither 180-second bound nor the 30-second
faulthandler threshold was reached. The control and treatment stdout hashes
are respectively
`6be08ae7d73e3e8182692b9c7c93204907f73d9fe057a8f8cce5e688e2064023`
and
`d288788e0766cb6e597eadb7c07642865665c9ac9ad3e04e02d58938461a0223`.
The attempt-start marker hash is
`f15c06811807f6469b912bc12de85389014162a582d204396a7a2041142c5c1a`.

## What Attempt 06 proved

The preserved Attempt 06 report is:

`RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/attempt_06/PERSISTENT_BLACKWELL_ACCEPTANCE.json`

Its SHA-256 is
`49daa08ae6dabe2ad46757737fd01bd8247dc9531b2621e1e7ff017f604d1ab1`.
The phase journal hash is
`e4fd32125cad5518ef0e7267d1a5298a1de8ad38cd10a826700b42905f0af31e`
and the repeated faulthandler log hash is
`de050999589fb6f5bff1a75b27cfb15cf96a3cb920cc1f3a6edf0b97bcd59c75`.

Its exact durable phase sequence was:

- restricted environment: `0.0033065` seconds;
- dependency metadata: `0.0026627` seconds;
- approved identity hashes: `0.006534` seconds;
- Qwen absence: `0.0069022` seconds;
- gap between the Qwen-finished event and Torch-started event: approximately
  `0.0639331` seconds, which includes initial resource-sampler startup;
- `imports.torch`: `901.035163` seconds;
- `imports.torchaudio`: `0.3252021` seconds;
- `imports.transformers_compatibility`: started, then the bounded client
  cleanup occurred.

Seven repeated 120-second stacks place the main thread in native NumPy module
creation reached from `torch.__init__`. They also show the stdin-reader thread
blocked in its buffered pipe read and the resource-sampler thread waiting at
the sampled instants. A Python stack snapshot cannot show the native C/DLL
loader wait and cannot prove OpenBLAS, Defender, disk, scheduler, or another
native component caused it.

The 900-second client timeout occurred before the worker returned. The durable
phase journal proves Torch completed approximately one second later. This
explains the timeout but not the anomalous 901-second import.

## Why the fast Attempt 07 probe does not reproduce the persistent path

The Attempt 07 A/B isolates the OpenBLAS environment value under a useful but
simplified process shape. It rules out both the proposed environment repair
and the claim that merely having two Python threads alive causes the stall. It
does not reproduce these important parts of the real Attempt 06 path:

| Boundary | Attempt 06 persistent worker | Attempt 07 import A/B |
|---|---|---|
| Child stdin | live buffered-reader thread and request queue | `DEVNULL` |
| Parent transport | dedicated stdout and stderr drain threads, response queue | `communicate()` after direct child import |
| Progress telemetry | phase events emitted and flushed during import | one final JSON record |
| Durable telemetry | parent validates and `fsync`s each phase event | no per-phase journal |
| Monitoring | exact `ResourceSampler`; synchronous psutil and one boundary `nvidia-smi`, then active 250 ms psutil sampler | two quiescent `Event.wait()` threads |
| Watchdog | real 120-second repeated load watchdog | separate 30-second probe watchdog |
| Pre-import work | sealed config, restricted environment, runtime metadata, identity hashes, Qwen-absence check | direct import after small environment assertions |
| Model-load opt-in | present for the real load request | deliberately absent |
| Import path | existing worker `_actual_backend_loader` and phase callback | direct `importlib.import_module()` |
| Cold/warm state | first anomalous run in that host state | ran about 31 minutes after Attempt 06 finished |

The real worker calls `ResourceSampler.start()` immediately before its backend
import. The sampler performs a synchronous psutil sample and one boundary
`nvidia-smi` subprocess query, then runs recurring psutil samples. The first
Torch event begins about 64 ms after Qwen-absence finishes, so the boundary
sample returned quickly. However, the active sampler can run between the
120-second stack snapshots; seeing it waiting in each snapshot does not prove
it never overlapped native initialization.

The real parent also flushes and `fsync`s phase events. Only the Torch-started
event occurs during the 901-second interval, so repeated journal writes are
not themselves a likely direct cause, but the full pipe/thread/protocol shape
has not been reproduced.

`contextlib.redirect_stdout(sys.stderr)` is not active around `imports.torch`.
It begins later, around `model_from_pretrained`. Therefore stdout redirection
cannot explain the 901-second import.

The candidate cache root was `40528` bytes both before and after Attempt 06.
That rules out cache growth as the explanation. It does not measure Windows
file-system cache, DLL-loader cache, Defender scanning, disk contention, or
other transient host state. The fast probe ran roughly 47 minutes after
Attempt 06 started and roughly 31 minutes after it finished, so those states
were not controlled. Attempt 07 records its own restricted environment, but
Attempt 06 did not preserve a byte-for-byte redacted environment snapshot;
exact environment equality across the two runs therefore cannot be claimed.

### Defender event correlation

A narrow read-only query of
`Microsoft-Windows-Windows Defender/Operational` found a strong temporal
correlation:

- the Attempt 06 local window from 19:25:30 through 19:43:30 contained exactly
  53 events, all Event ID 2010, categorized as Defender using cloud protection
  to obtain additional security intelligence;
- those events began at 19:41:44 and ended at 19:42:43;
- the 901.035163-second Torch phase ended at 19:41:44.353 local time, in the
  same second as the first cloud-protection event;
- the comparison Attempt 05 window from 18:19:30 through 18:37:30 contained
  eight Event ID 2010 events, all between 18:20:40 and 18:20:50, and that
  persistent run was later killed at its 900-second bound.

This is strong support for a cold Defender cloud/reputation or native-DLL
inspection hypothesis and helps explain why the later warm imports took about
one second. It is not causal proof: the aggregate Event ID does not identify a
specific Kira process or DLL, and no per-file reputation decision was
captured. The exact aggregate record is:

`RecoverySprint/continuation_20260803/persistent_blackwell_attempt07_openblas_import_ab_diagnosis/attempt_01/DEFENDER_EVENT_CORRELATION.json`

SHA-256:
`b0d6dbdc2f5878dc8a2f7c3e82ed60905536bbeaf4f08ccc8e58ca44ca9037fd`.

At the time this correlation was first recorded, no Defender setting had been
changed. Robert subsequently authorized a Defender intervention. The selected
experiment was deliberately narrowed to one reversible path exclusion for
only:

`C:\Users\robmc\Kira\Voice\sidecars\chatterbox_blackwell_gpu\.venv`

Defender was not disabled or removed. The sole apply helper is
`tools/apply_defender_blackwell_voice_exclusion.ps1`, SHA-256
`87527f0c5973a6e1c3c698b0a21395562ae6db4fb94849b6271cf99591664919`.
The prechange checkpoint records that the exact target was absent and both
real-time and behavior monitoring were enabled. A legitimate UAC run of the
helper later returned exit code zero. By the helper's code contract, zero is
possible only after it re-reads Defender state, sees the exact target present,
and sees real-time and behavior monitoring still enabled.

That in-process exit result is not a substitute for independent post-state
evidence. Two attempts to run the separate elevated read-only capture were
blocked by the Codex escalation-approval usage limit; they were not retried or
bypassed. Therefore current status is:

`EXACT_VENV_EXCLUSION_APPLY_EXIT0_INDEPENDENT_POST_CAPTURE_PENDING`

Do not claim paired pre/post causality or that the exclusion has improved
Torch latency. No import test has run after the change. Do not add another
exclusion, broaden this path, or disable Defender globally.

Current classification:

`PERSISTENT_PROTOCOL_TORCH_NUMPY_NATIVE_IMPORT_STALL_NOT_REPRODUCED_BY_SIMPLIFIED_PROBE`

Exact root cause remains unresolved.

## Candidate truth after the rejected hypothesis

The unsupported `OPENBLAS_NUM_THREADS=1` candidate policy has been removed.
The five changed candidate/harness files were restored to their exact
pre-experiment Attempt 06 hashes:

- `candidate_client.py`:
  `b57e1a57625f8d3c55881795611b440aaf91aeb7466ee2f1231ee7bedbc3e9f1`;
- `candidate_contract.py`:
  `e74ce6ad83b181d5f8ca786764d5e61e2cc5e053aaebf29065063151aed38cbc`;
- `candidate_config.json`:
  `8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57`;
- full acceptance harness:
  `828ce07f899e53f844f98a2ba915286e13e4eeb5a99194da9d79dd681ce8adea`;
- persistent-candidate regression test:
  `c982f5cc27a38c56a383ada28e8e8b2f8ea5533f478dbfd5914c82734a1470e8`.

The worker remained unchanged at
`bbf33447e7b742a3f2c79da6f7a3527b37a069e32bb888ed3d1e833345388085`.
The restricted child does not inherit a parent OpenBLAS value and does not
force one. No unsupported experimental setting is approved for production or
for a full Attempt 07 run.

The preserved reverse patch in the preparation package records exactly the
restoration that has now been applied. Do not apply it again and do not apply
its inverse. If a later edit changes the candidate, restore from the exact
hash-bound pre-experiment versions rather than reintroducing the rejected
setting.

## Smallest next protocol-path-faithful import-only probe

Do not run a full GPU acceptance next. The smallest useful next probe is a
separate diagnostic-only operation that uses the real persistent pipes,
stdin-reader, parent stdout/stderr drain threads, request queue, phase-event
flush and parent `fsync`, 120-second watchdog, restricted environment, and
Torch import path, but returns immediately after `imports.torch`. It must not
import Torchaudio or Chatterbox, call `torch.cuda`, load a model, generate or
play audio, query or load Ollama, or change routing.

The first arm must reproduce the exact Attempt 06 monitoring shape, including
`ResourceSampler.start()`. If that control does not reproduce the stall, stop:
the evidence plus the Defender timing favors a transient cold security/file-
loading state and no sampler or OpenBLAS code change is justified. If it does
reproduce, run a bounded paired arm whose only change is deferring the
resource sampler until after Torch import. For stronger causal evidence, run
fresh AB/BA pairs rather than always running the no-sampler arm second,
because Windows file/DLL cache warming can otherwise mimic an improvement.

The diagnostic should record:

- exact command and redacted environment digest;
- exact worker, client, contract, config, and diagnostic-tool hashes;
- active thread names/count immediately before import;
- boundary psutil and `nvidia-smi` start/end timings;
- every protocol emit/flush and parent journal-write/`fsync` timing;
- Torch import start/end and exact version;
- whether NumPy was loaded transitively and its version;
- timeout/owned-child cleanup evidence;
- an explicit OS page-cache/Defender/DLL-cache uncontrolled-state caveat.

This diagnostic is now prepared as:

`tools/run_persistent_blackwell_protocol_import_only_control.py`

SHA-256:
`7fd8e006ba58aede2f34b4289c4fc857a1bc6ae76d6a6a4fcc36a7f3a0466f21`.

It subclasses the real candidate client, uses the real client request/pipe,
stdout/stderr drain, queue, validation, and phase-journal `fsync` behavior,
then launches the real worker `serve` loop with a separately opted-in
diagnostic runtime. The real watchdog and exact `ResourceSampler` remain in
the path. The runtime returns immediately after `imports.torch`; it contains
no Torchaudio or Chatterbox import call, `torch.cuda` call, model load, audio,
playback, or Ollama query.

The separate worker/client/config/contract files were not edited to add this
operation and retain their exact Attempt 06 hashes. The wrapper is separately
operator-hash-bound and cannot become a production route.

Before the diagnostic can run, an independent Defender state record must be
captured by the read-only helper:

`tools/capture_blackwell_defender_exclusion_state.ps1`

SHA-256:
`7644d4a41a7e53d446852d8e349391bd015ea4fa8a809e05f0a505e6e1798b23`.

That helper contains no Defender mutation command. It binds the sole apply
helper and prior attempt evidence, records other exclusions only as hashes,
and explicitly marks that no paired machine-readable pre-state exists. Its
elevated `POST_APPLY_BASELINE` capture remains pending. The import-control
tool refuses to run without a hash-bound state record.

A separate safe prewarm experiment remains reasonable at a future cold-boot
boundary. It must compare clearly recorded Defender states rather than mixing
excluded and non-excluded runs, remain bounded above the already observed
901-second delay, never call CUDA or load a model, and record the narrow
Defender event aggregate. Only repeated cold-boot evidence may justify a
launcher prewarm. One later warm result cannot prove exclusion effectiveness
or approve a production change.

## Verification and handoff

Sixteen focused host-only tests pass across the Attempt 07 rejection suite and
the Defender/protocol-import preparation suite. The protocol tool's own
static self-check also passes. These checks did not start the Blackwell
Python, import Torch, call the GPU, load a model, call Ollama,
synthesize/play audio, start Kira, or start Blender.

Handoff status:

- preserve Attempt 06 and Attempt 07 `attempt_01` byte-for-byte;
- do not run the full GPU Attempt 07;
- do not promote the persistent candidate;
- do not retain `OPENBLAS_NUM_THREADS=1` as a candidate or production policy;
- do not run the protocol import control until independent post-exclusion
  evidence exists and the active body/Blender operation has ended;
- do not represent apply exit zero as measured latency improvement;
- current candidate config SHA-256 is
  `8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57`;
- next allowed voice work is the independent read-only Defender post-state
  capture, followed at a clean body/Blender boundary by the bounded
  protocol-path-faithful import-only control described above.

Detailed append-only checkpoint:

`RecoverySprint/continuation_20260803/persistent_blackwell_attempt07_openblas_import_ab_diagnosis/attempt_01/CHECKPOINT.md`

## Exit-zero-bound pending-state control revision

A second, separately named protocol-import-only wrapper is now statically
prepared for the narrower evidence boundary created by the observed legitimate
UAC helper exit code:

`tools/run_persistent_blackwell_protocol_import_only_control_pending_defender_state.py`

SHA-256:
`cf72d1d5dcb5060b1f7fdf88deefa3d97d72351c459fca0f80736d60da9c4cd9`.

This wrapper does not replace or edit the stricter control. The stricter tool
remains byte-for-byte unchanged at SHA-256
`7fd8e006ba58aede2f34b4289c4fc857a1bc6ae76d6a6a4fcc36a7f3a0466f21`
and still requires independent Defender-state evidence when it is invoked
directly.

The new wrapper binds all of the following before it can start a later bounded
control:

- the sole exact-target apply helper, SHA-256
  `87527f0c5973a6e1c3c698b0a21395562ae6db4fb94849b6271cf99591664919`;
- the append-only apply-result record, SHA-256
  `f4e0a73b43a4bb6a6ade9234da3d4a55a69cac4eee1905d59f6ee9201914a057`;
- the prior preparation checkpoint, SHA-256
  `8b9771580194a9fec66bf57bf3c6a282883ec637ee89ce90c9378d39b7406d7b`;
- the prior preparation manifest, SHA-256
  `8d112384c06144e9405a39233d6564de46db6f508bf01be8db5cc6d49e8c8140`;
- the restored Attempt 06 candidate hashes and an explicit operator-bound
  wrapper hash;
- an explicit no-active-Blender confirmation plus the existing lightweight
  process gate.

The apply-result record reports only what was actually observed: the approved
helper returned exit code zero. The helper's internal contract permits exit
zero only after its own exact-target-present, real-time-monitoring-not-disabled,
and behavior-monitoring-not-disabled checks pass. No execution timestamp,
stdout, stderr, or separate post-run Defender capture was retained. Therefore
the independent current Defender state remains:

`UNKNOWN_PENDING_INDEPENDENT_CAPTURE`

The wrapper verifies the strict dependency hash before executing that module,
explicitly validates the helper's exact target and all three exit-zero contract
entries, and gates a later pass on clean owned-child exit plus unchanged final
candidate hashes. It never queries or changes Defender. It does not convert the helper
exit into an independent exclusion-state or monitoring-state claim, and it
makes no latency-improvement, Defender-causality, or production-acceptance
claim. Its eventual child remains the same real protocol path used by the
stricter control and stops after `imports.torch`; it cannot call CUDA, load a
model, synthesize or play audio, invoke Ollama, promote the candidate, or
change production routing.

The wrapper and apply-result record have not been live-run as a protocol
control. Twenty-six focused host-only tests and its static self-check pass.
Those checks did not query or change Defender, launch the Blackwell runtime,
import Torch, call CUDA, load a model, generate or play audio, invoke Ollama,
start Kira, start Blender, promote a candidate, or change routing.

At a later clean body/Blender boundary, this revision can run only with all
four exact operator bindings:

```text
py -B tools/run_persistent_blackwell_protocol_import_only_control_pending_defender_state.py --run-control --confirm-no-active-blender --expected-candidate-config-sha256 8fffb5b641486963341ba2a4c10ff13f067eaf1d085c26488f9996ac4cd1af57 --expected-base-tool-sha256 7fd8e006ba58aede2f34b4289c4fc857a1bc6ae76d6a6a4fcc36a7f3a0466f21 --expected-wrapper-tool-sha256 cf72d1d5dcb5060b1f7fdf88deefa3d97d72351c459fca0f80736d60da9c4cd9 --expected-apply-result-sha256 f4e0a73b43a4bb6a6ade9234da3d4a55a69cac4eee1905d59f6ee9201914a057 --timeout-seconds 1100
```

This is permission for one bounded Torch-import-only measurement, not for a
full GPU/model/audio run and not for promotion. The result must retain the
unknown independent Defender-state label whether it passes or fails.

## Pending-state protocol control attempt 01 result

The exit-zero-bound wrapper was later run once at a clean boundary. Preserve
that attempt byte-for-byte:

`RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/import_only_protocol_control_pending_defender_state/attempt_01`

The parent report is
`PROTOCOL_IMPORT_ONLY_PENDING_DEFENDER_STATE.json`, SHA-256
`9bf47ced167c1d6733277516207426d1f5a4dc699caa900cbfd4228730349884`.
The append-only phase journal is SHA-256
`812a007bfecfb6296d3ea75f59f9bf78efb73737d46acc124fb8b10736c28dc0`,
the faulthandler record is SHA-256
`2ae85fd00688dce004c68b62d438d75aa37e8085b796a9b34b96b42d6f45baed`,
and the later read-only process check is SHA-256
`c87cc5a66a05c274dec280505c3f474459b1cf64df2672cd0958661f06bada7a`.

The acceptance result is failed and remains failed. The parent request timed
out at 1100 seconds. The phase journal nevertheless proves that the worker's
Torch import returned and marked its phase passed after 1100.9460583 seconds,
0.9460583 seconds after the client deadline. That late phase event is not a
validated load response and cannot convert the failed parent acceptance into
a pass.

Nine repeated 120-second faulthandler snapshots show the same boundary:

- the main thread remained in `torch.__init__`, `from torch._C import *`,
  through transitive NumPy initialization and native module creation at
  `numpy/core/overrides.py`;
- the real ResourceSampler thread was waiting between its 250 ms host samples;
- the real stdin-reader thread was blocked in inherited-stdin `readline`.

This localizes the delay but does not prove its native, operating-system,
Defender, DLL-loader, page-cache, sampler, stdin, pipe, or disk-fsync cause.
The independent current Defender state remains
`UNKNOWN_PENDING_INDEPENDENT_CAPTURE`; no exclusion-state, monitoring-state,
latency-improvement, or Defender-causality claim is available.

`cleanup_clean=false` in the preserved report means that
`candidate_client.close()` returned no validated shutdown-response dictionary
after the timed-out load. It does not prove that an owned process remained.
The later process check found no Python, PythonW, or Blender process, but it
cannot retroactively prove the exact child exit time or clean protocol
shutdown. Similarly, `prohibited_outcomes_absent=false` means the timed-out
request never supplied the complete child result required by exact `is False`
gates. No prohibited true value was observed, and candidate hashes remained
unchanged; missing evidence must not be rewritten as proof of absence.

Full machine-readable analysis:

`RecoverySprint/continuation_20260803/persistent_blackwell_import_component_isolation_preparation/attempt_01/FAILURE_ANALYSIS.json`

SHA-256:
`273155c325775640c8f36c0a63899009c4df6c1a9d93b241872ecb9c78ae3581`.

## Host-isolated next probe

A new append-only one-arm-at-a-time probe is statically prepared:

`tools/run_blackwell_import_component_isolation_probe.py`

SHA-256:
`a275123607567db7e9663036829808c51c24e792e3c44445d625a45697ee5153`.

It offers seven separately selected arms; it never automatically runs the
matrix:

1. `minimal_direct` — restricted-environment standalone baseline;
2. `worker_context_only` — adds only exact `persistent_worker` module context;
3. `nvidia_boundary_only` — adds one exact boundary `nvidia-smi` query;
4. `resource_sampler_host_only` — adds the real ResourceSampler host thread
   while stubbing only its external GPU subprocess;
5. `stdin_reader_only` — adds the real blocked inherited-stdin reader;
6. `pipe_drains_fsync_only` — adds live parent stdout/stderr drains and the
   append-only phase-journal `fsync`;
7. `combined_real_shape` — combines the real sampler boundary query, stdin
   reader, pipe drains/fsync, and worker context only after individual arms.

Each arm uses a fresh exact owned child, the exact restricted environment and
candidate hashes, imports only Torch, observes transitively loaded NumPy, and
is hard-capped at 180 seconds. A timeout preserves its evidence and stops only
that owned child. No arm calls `torch.cuda`, imports Torchaudio or Chatterbox,
loads a model, generates or plays audio, invokes Ollama or Kira, changes
Defender, elevates, starts Blender, promotes the candidate, or changes routing.

Run only one arm per authorized clean boundary. Start with `minimal_direct`,
then `worker_context_only`; choose the appropriate single-component arm from
their result. Use the combined arm only after individual isolation. OS cache,
DLL-loader, disk, and security-reputation state remain uncontrolled, so one
fast or timed-out arm is evidence, not causal proof. No isolation arm has been
live-run from this preparation.

## Finalization truth revision

The failed-run wrapper remains byte-for-byte unchanged at SHA-256
`cf72d1d5dcb5060b1f7fdf88deefa3d97d72351c459fca0f80736d60da9c4cd9`.
A separate v2 finalization wrapper is prepared at:

`tools/run_persistent_blackwell_protocol_import_only_control_pending_defender_state_v2.py`

SHA-256:
`424869e7a3d90d30dd20381a3adbcf00cd91521ec5cd57c40d0e6f0d8e5eb7c0`.

The v2 wrapper maps a missing validated shutdown response to unknown, not
false. It records the exact owned PID and observed exit code, captures phase
events both before and after cleanup, and reports clean cleanup only from a
validated shutdown response, exit code zero, and no forced termination. It
also distinguishes a prohibited true value from incomplete child evidence:
only a complete child response with every required field false proves absence.
All pass gates remain fail-closed and require both truths to be proven true.

The v2 wrapper has not been live-run. Forty focused host-only tests pass across
the new isolation/finalization tests and the three predecessor suites. Static
self-checks did not start Blackwell Python, import Torch, query or call CUDA,
load a model, generate or play audio, invoke Ollama or Kira, query or change
Defender, elevate, start Blender, promote a candidate, or change routing.

## Superseding static-review and Windows-lineage correction

This section supersedes the operational status in the preceding **Host-isolated
next probe** and **Finalization truth revision** sections. Their artifacts and
hashes remain historical evidence, but independent review rejected both of
these files before any live run:

- `tools/run_blackwell_import_component_isolation_probe.py`, SHA-256
  `a275123607567db7e9663036829808c51c24e792e3c44445d625a45697ee5153`;
- `tools/run_persistent_blackwell_protocol_import_only_control_pending_defender_state_v2.py`,
  SHA-256
  `424869e7a3d90d30dd20381a3adbcf00cd91521ec5cd57c40d0e6f0d8e5eb7c0`.

Do not run either rejected file. The independently reviewed replacements are:

- sealed component probe v2:
  `tools/run_blackwell_import_component_isolation_probe_v2.py`, SHA-256
  `95d6a37c141b4ec7c425bc22a023e089ea91c0f041173d7940de2450d3750a0a`;
- strict finalizer v3:
  `tools/run_persistent_blackwell_protocol_import_only_control_pending_defender_state_v3.py`,
  SHA-256
  `53f31d72c09560bc71507f7374764100f52a04de3db901124141f1930a3f92f1`;
- hardened regression:
  `Testing/test_blackwell_import_component_isolation_hardened_revision.py`,
  SHA-256
  `08b53d8a2df5a068b86935a729ac51b52497517aaf1b225e0e05078b80d252c9`.

The sealed v2 probe was subsequently run once as `minimal_direct`. Preserve the
append-only attempt byte-for-byte:

`RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/import_component_isolation_v2/attempt_01`

It failed in 0.4339544 seconds before dependency loading or Torch import. The
child authorization map had every condition true except
`live_parent_pid=false`; the child exited with code 1, the run did not time
out, and no child result or ready marker existed. Candidate hashes remained
unchanged. Exact attempt hashes are:

- `ATTEMPT_STARTED.json`:
  `ef4cc76a76214adcb50f274c1a3fb3d7a98e12699c15140fba39395723e7843b`;
- `CHILD_STDERR.log`:
  `ab90b715b96ffe1b2f519b6e02fe6a5142d8df6ea1f83e8f6ac34d31aa7f11c6`;
- `COMPONENT_ISOLATION_V2_REPORT.json`:
  `48a04f20ff55df89fafdb3373b19b091591884fb4f5fff3ea432008b07d49774`.

A read-only standard-library microdiagnostic then verified the Windows venv
process shape as controller -> venv redirector -> executing base Python. Its
record is:

`RecoverySprint/continuation_20260803/persistent_blackwell_import_component_isolation_attempt01_analysis/WINDOWS_VENV_REDIRECTOR_MICRODIAGNOSTIC.json`

SHA-256:
`3606e8e42776db2a229569baee9169643f57e4cc4ac8af40098a44d6f43c7593`.

The smallest repair is a new append-only v3 probe; v2 and `attempt_01` remain
unchanged:

`tools/run_blackwell_import_component_isolation_probe_v3.py`

SHA-256:
`89571ac3b0b2bd45d227310bca4b95daa19ee13cf13bb8c662624f6110ea64f6`.

The repair retains the nonce, hash, freshness, same-attempt, result, parent and
child Blender, semantic-ready, candidate-integrity, owned-process, drain, and
whole-run timeout gates. It binds the controller and exact `Popen` launch
process by PID, Windows creation time, and normalized executable path in a
nonce-HMAC-signed append-only launch record. The child accepts only a direct
Popen child or exactly one venv redirector, re-queries both process identities
live, and rejects unrelated, deeper, PID-reused, and executable-spoofed chains.

The focused regression is
`Testing/test_blackwell_import_component_isolation_windows_lineage_revision.py`,
SHA-256
`51b6ce36eabc1ac4394e56aeb725f0aa313289765e257e014412c62d634dbfed`.
The static self-check, 11 focused tests, and 63 combined host-only tests pass.
Independent review returned `PASS_TO_SEAL`. No v3 live arm was run while
preparing or reviewing this repair.

The next allowed action is one append-only v3 `minimal_direct` arm at a clean
boundary, expected to allocate `attempt_02`. It remains import-only and bounded
to 180 seconds overall and 120 seconds around the import measurement. It does
not authorize CUDA, model loading, audio, playback, Defender change, production
promotion, routing change, or an automatic arm matrix.

Static package:

`RecoverySprint/continuation_20260803/persistent_blackwell_import_component_isolation_preparation/attempt_02`

- `CHECKPOINT.md` SHA-256
  `f3ac6e78c136133329ca6e952692f996bcd48ff028a005886ee5750ae542b2de`;
- `PREPARATION.json` SHA-256
  `eb9f8738a3ae22ed068aacad80f3a81585aedd29b12f8395f7ead039a715484d`;
- `INDEPENDENT_STATIC_REVIEW.json` SHA-256
  `09236562b9a22f50959645b2f18bb1c49a0910d03d95daec2b1f6170f1b6ec60`;
- `MANIFEST.json` SHA-256
  `7853b8e1b332b6876b525bc2cd1b33458b654ceb3a98b5c41547ccd3324af10d`.

## OpenBLAS source clue remains a hypothesis

The preserved local A/B report
`ATTEMPT07_OPENBLAS_IMPORT_AB_REPORT.json`, SHA-256
`008b04fbc89a606fff6713a2c1e2b858298eeb4da03257d5a082d190f5d4e94d`,
binds NumPy 1.26.4 to an OpenBLAS 0.3.23 development build with
`MAX_THREADS=2` and DLL SHA-256
`57b87772bf676b5c2d718c79dddc9f039d79ec3319fee1398cc305adff7b69e5`.
The official [OpenBLAS README](https://github.com/OpenMathLib/OpenBLAS#considerations-for-using-the-library-from-java)
documents one Windows startup deadlock involving a MinGW-gfortran OpenBLAS
build and pipes, but specifically in a Java/SBT/Play setting. That source is a
useful reason to keep pipe/process context as a bounded hypothesis. It is not
evidence that this Python/Torch delay has the same cause. Only the append-only
component arms can support or reject that local hypothesis.

## 2026-08-04 live isolation result and inactive v2 request-gate repair

The sealed v3 component series was run one arm at a time. It did not invoke
CUDA, Torchaudio, Chatterbox, a model, audio, playback, Ollama, candidate
promotion, or production routing:

- `attempt_02` / `minimal_direct` passed in `3.6727555 s`; Torch import was
  `2.7010621 s`. Report SHA-256:
  `455a5b905656e105eaea2df54044b26e8caebb129ebc108ddaae4a688b385854`.
- `attempt_03` / `worker_context_only` passed in `1.8551449 s`; Torch import
  was `1.0063127 s`. Report SHA-256:
  `4a33a51444a22bfb1ace1cb13efa03829a22dbce8bf4d3c886077975d2f15bbc`.
- `attempt_04` / `nvidia_boundary_only` passed in `1.8530083 s`; Torch import
  was `1.0058179 s`, and the single real `nvidia-smi` boundary query took
  `0.0526409 s`. Report SHA-256:
  `cb01a47b55452b1534ad302c7d961502c68933cd353c2c28f82da5ce036c8e62`.
- `attempt_05` / `resource_sampler_host_only` passed in `1.7463437 s`; Torch
  import was `0.9733047 s`. The real host sampler produced five samples and
  two deliberately stubbed external-GPU polls without errors. Report SHA-256:
  `ccfec3f4ea4728822e67d1e646cf554d8161d469c2237a41844bcbb34b7c29e5`.
- `attempt_06` / `stdin_reader_only` reproduced the fault. It reached its
  `120.0 s` import bound and was terminated at `120.2362762 s`. No committed
  child result existed, so CUDA/model/audio/routing outcomes remain unknown,
  not false. Report SHA-256:
  `87e2fc7df4aefdb40dd4f27ee7b5896c7f41f203be19c240972f8fc1d6dcca2b`;
  stderr SHA-256:
  `b5b52fadfd207ad25226d4ea37ae324c0ede35b363767d81bd6e9548c14fb818`.

The `attempt_06` repeated stacks match the earlier `1100.9460583 s` failure:
the background reader is blocked in inherited
`sys.stdin.buffer.readline()` while the main thread remains in NumPy
`core.multiarray` native creation reached from `torch.__init__`. Because every
preceding arm, including a live host-sampler thread, imported Torch in about
one to three seconds, the evidence supports this bounded local conclusion:
the concurrent blocking inherited-pipe read is sufficient to reproduce the
stall on this host. It does not claim a universal Windows or OpenBLAS cause.

The v1 candidate and Attempts 01-06 remain unchanged. The repair is a separate
inactive sibling:

`Voice/sidecars/chatterbox_blackwell_persistent_candidate_v2`

Its reader queues one request and then parks on a semaphore until the main
thread has written and flushed that request's final response. Terminal paths
set a stop event before releasing the parked reader. This preserves lazy
Torch/CUDA/model loading and the existing single-request client contract; it
does not pre-import NumPy, alter packages, rebuild the environment, or change
production routing.

Sealed v2 hashes:

- config: `805c1d2836c618970a81f5f44d31f81f67e204173bd919857452daa8dbedc8bb`;
- contract: `863c6ece050b12af157565c60df6fd82b207dae5476e693cc08e34b392c8f910`;
- client: `9f33ef0d9fd969da05ce48eb148163efc77306bfd3bc215efcb482e68e7261a8`;
- worker: `b6f2dcc816537552db02d00c5a1932057f2d99b5d206a578344d4a92523b3cad`.

The focused v2 gate suite passes `11/11`. The separate hardened import-only
harness passes `10/10` static tests and is sealed at SHA-256
`40eaa812edd2ae88c82854909684a4ea1f821ac199627aaf11e3738159aaab10`.

Its one live inherited-pipe proof passed append-only as:

`RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/import_only_v2_request_gate/attempt_01/FINAL_REPORT.json`

Final report SHA-256:
`38a566bf29cf72b5532514a0b7876eb2003e648745a6a36d1581bbf42ef04726`.
Torch `2.11.0+cu130` imported in `2.32634 s`; total wall time was
`3.0099338 s`. The persisted stack proves the sole stdin reader was parked at
`request_complete.acquire()` and had no active `readline` frame. The child
result and ready marker were hash/size bound, the exact worker exited `0`
without terminate or kill, drains finalized before diagnostic hashes, and the
production routing hash remained
`a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81`.
Trusted evidence records CUDA, Torchaudio, Chatterbox, model, audio, playback,
Ollama, generic/SAPI/fallback, promotion, and routing change all exactly
false.

This is a real repair of the persistent candidate's Torch-import stall. It is
not yet a GPU-model, WAV, conversational-latency, or owner-hearing acceptance.
The v2 candidate remains inactive. The next bounded gate is a no-playback v2
GPU load, two approved WAV generations (cold then warm), explicit unload,
VRAM-return proof, protected-file verification, and no promotion.

## 2026-08-04 v2 full-GPU engineering acceptance

Full-GPU `attempt_01` is preserved as a harness-validation failure, not a CUDA
failure. Its eager matrix passed, but the first harness incorrectly required
`nvidia-smi` total/free/used accounting to close within `8 MiB`. The actual
before/after snapshots each had a `260 MiB` unreported/reserved gap. NVIDIA's
official `nvidia-smi` documentation states that the driver may reserve memory
for internal use and that operating-system-managed FB memory can produce
reporting discrepancies in its
[FB Memory Usage documentation](https://docs.nvidia.com/deploy/nvidia-smi/index.html#fb-memory-usage).
Attempt 01 stopped before the voice worker/model.

- original harness SHA-256:
  `db55950b59c3f0ffa3a2f1831c1cba1b9a1b399d846cdea0ee48ab5e95df6223`;
- Attempt 01 final report SHA-256:
  `091fe7dc39ed19bfdb6db89e10cec7751546b9149216fac3a35a732d539964f7`;
- Attempt 01 eager-readiness SHA-256:
  `a352f59cc3830e558df6a23e9500ca951fd0fc2eec4a9aafb8a27de537701c31`.

Revision 01 preserved the original harness and changed only that validator.
It requires exact GPU identity, driver text, nonnegative integer values,
free/used no greater than total, their sum no greater than total, and an
explicitly recorded unreported/reserved gap no larger than the greater of
`1024 MiB` or `10%` of total. The gap is not attributed to a process or
reported as measured VRAM use. Focused tests pass `6/6`; related v2 tests pass
`39/39`.

- revision-01 harness SHA-256:
  `bd7a720ea831dd679e19a3eb4ad0c2efdc3067b9c3005c33d165a38b76a62c81`;
- revision-01 test SHA-256:
  `09859062921ea1dd5232b3bb3fc48a1eb94d851a87f72ba256ee74157be3fef5`.

Append-only `full_gpu_v2/attempt_02` then passed as
`engineering_pass_pending_owner_heard_acceptance`. Final report:

`RecoverySprint/continuation_20260802/persistent_blackwell_voice_candidate_acceptance/full_gpu_v2/attempt_02/FINAL_REPORT.json`

SHA-256:
`40771bb8961a09a9e627e2c8b3a0d80da18dbb3199aea900912c56ceefc7d339`.

Measured results:

- fresh eager-CUDA matrix preflight: `1.5983728 s`; RTX 5060 Ti, capability
  `12.0`, `sm_120`, exact `[4096,4096] @ [4096,64]` result, measurable
  allocation/release, no unsupported-architecture/no-kernel warning;
- fresh worker start: `0.1057114 s`;
- cold model load plus approved-reference conditioning: `25.243665 s`;
- first GPU synthesis: `2.164824 s` generation / `2.165326 s` operation;
- second warm GPU synthesis: `1.82563 s` generation / `1.826145 s`
  operation;
- explicit unload: `0.148987 s`;
- total including eager preflight: `33.4002128 s`.

The approved sentence was exactly:
`I don't see anything and I don't hear anything.` Its SHA-256 was
`0956e983e4287fb61142377cfe09fe3277c6c33747da9bec9da312b316dcfaf7`.
Both generations bound the exact approved profile and reference hashes.

- first WAV: `2.16 s`, 24 kHz mono, readable/non-silent, SHA-256
  `7be55c8abc1831e44e07c6587f7abb9b44c4904daf8b95b24a1f2db78862497d`;
- second warm WAV: `2.84 s`, 24 kHz mono, readable/non-silent, SHA-256
  `d6c4b0d577207e7e01055776c391d769f3d4e3bf2c0e364bcfb070d2e62c4632`.

Authoritative Torch allocator peaks were `3,656,216,576` allocated bytes and
`3,814,719,488` reserved bytes. Peak worker RSS was `4,944.3 MiB`; peak system
RAM used was `21,070.3 MiB`. Boundary-only total GPU snapshots reached
`4,994 MiB`; that is not a continuous total-VRAM peak. Explicit unload
returned `3,536,158,208` allocated bytes and `3,787,456,512` reserved bytes,
leaving the model unloaded. Qwen absence was proven before eager preflight,
load, both syntheses, and after unload. The exact worker exited zero; both
drain threads ended; protected files and production routing remained exact.

No audio was played. `owner_heard_acceptance` remains false. The v2 candidate
was not promoted and is not a normal-launch default. These measurements prove
the persistent GPU path removes repeated model startup and reduces the tested
warm generation portion from the prior `20.637 s` to approximately
`1.83-2.16 s`; they do not yet prove complete live Text + Voice turn latency,
playback timing, or owner-perceived quality.

## 2026-08-04 default-off application-route v2 acceptance

The real no-playback application-route series is append-only:

- `application_route_v2/attempt_01` failed before GPU work because direct
  script execution could not import `Core`; it is preserved unchanged.
- `application_route_v2/attempt_02` proved cold load and one GPU WAV but
  failed overall. The host incorrectly demanded cold-only identity/runtime
  telemetry from the sealed worker's compact `already_loaded` response,
  closed the valid worker, and restarted it.
- The host now validates sparse reuse as a separate same-owned-worker
  contract. It still requires current Qwen absence, all six retained GPU/load
  proof flags, loaded lifecycle state, positive model-load/conditioning
  counts, the exact approved conditioned-reference hash, and prior cold-load
  proof on the same client. It cannot accept sparse reuse from a new client.

Append-only `application_route_v2/attempt_03` passed all 17 gates:

`RecoverySprint/continuation_20260803/persistent_blackwell_voice_candidate_acceptance/application_route_v2/attempt_03/FINAL_REPORT.json`

SHA-256:
`407a34c458af5810583d74d98c623be6761dd482aec46d925c62fab5b1f335f6`.

Measured application-route results:

- cold worker/model/reference prewarm: `11.182215 s` external;
- first retained-worker turn: `3.182024 s` external / `3.054409 s`
  generation;
- second retained-worker turn: `4.011697 s` external / `3.884747 s`
  generation;
- release: `1.958062 s` external / `0.139071 s` worker unload;
- total: `20.685393 s`.

Both turns used the same persistent CUDA worker and exact approved Kira
identity, with actual GPU execution and Qwen absence. WAV SHA-256 values are
`92f933b9a22cc26f429bcc6c28819b41b9a71138cd5d8920cd538ebdf29d2e88`
and
`d187a00d693b74d7f8c5ab120cc7fe4319ddf9c18d438fc10cde871aaf49d5fd`.
Both are readable, non-silent, 24 kHz mono files.

GPU boundary use was `1,288 MiB` before, `4,909 MiB` loaded, and `1,282 MiB`
after release. The exact worker exited zero without forced termination;
protected files were unchanged. No playback, text-model call, CPU/generic/SAPI
fallback, promotion, or production-route change occurred.

Peak worker RSS was `5,000.7 MiB`; peak system RAM used was `21,902.3 MiB`;
the boundary-only GPU delta was `3,621 MiB`. Runtime versions remained Torch
`2.11.0+cu130`, Torchaudio `2.11.0+cu130`, and Chatterbox TTS `0.1.7`.

Host checkpoint:

`RecoverySprint/continuation_20260803/persistent_blackwell_voice_candidate_acceptance/host_integration_v2/attempt_02/CHECKPOINT.md`

Checkpoint SHA-256:
`a71ba154b2c983f388bb3b51f7ecf7bdbe743a9978b3165fec6b07efd09a1565`.

The v2 feature remains default off. Owner-heard, complete live-turn, and
playback-latency acceptance remain pending and require Robert to be present.

## 2026-08-04 current-host application-route Attempt 04

After the owner-hearing harness added explicit v2 route/GPU/nonpromotion
evidence, the previous Attempt 03 host binding correctly became stale. The
host was also made fail-closed: selected v2 can never fall through to one-shot
Blackwell, missing cleanup evidence never proves closure, and the sealed CPU
route is available only after exact cleanup proof.

The fresh no-playback current-host run passed every gate:

`RecoverySprint/continuation_20260803/persistent_blackwell_voice_candidate_acceptance/application_route_v2/attempt_04/FINAL_REPORT.json`

SHA-256:
`659ab7886c4571b3deb0bf759cc7ba84c3ff24a47a1f0ec7c7f3b3216171d9ab`.

- cold prewarm: `11.522588 s` external;
- retained-worker turns: `2.280725 s` and `2.600909 s` external;
- generation: `2.186476 s` and `2.473000 s`;
- release: `1.990612 s` external / `0.142730 s` unload;
- total: `18.775542 s`.

No audio, text-model call, Blender operation, CPU/generic/SAPI fallback,
promotion, or default change occurred. Exact checkpoint SHA-256:
`124575e17427dfb17e3932df9b37ac69e8a3ad347b4999ffd36663b7c983be42`.

## 2026-08-04 two-turn Text + Voice engineering result

The audible series remains append-only:

- Attempt 01 failed because the harness required stale `chat_received` while
  the real server emitted documented `chat_request_received`. One real v2 GPU
  reply played, but no turn record was accepted. Report SHA-256:
  `ebcf9281ce6579ebb0c6463a2c00b40711095e0d75405e6d4950cfba9cd29855`.
- Attempt 02 fixed the event name and proved exact failure cleanup, but the
  privacy recorder omitted new safe v2 scalar evidence. One real v2 GPU reply
  played; the strict route classifier correctly failed closed. Report SHA-256:
  `d4a5d066c48ec26c5bef9cefe0350b1c79b726c9c814635ab2f41f18dddc96e0`.
- Attempt 03 passed all engineering, privacy, routing, CUDA, WAV, playback-
  proxy, protected-file, exact cleanup, Ollama-unload, and VRAM-return gates.

Attempt 03 report:

`RecoverySprint/continuation_20260802/kira_text_voice_two_turn_latency_acceptance/persistent_voice_v2_llama_keep_alive_buffered/attempt_03/TWO_TURN_LATENCY_ACCEPTANCE.json`

SHA-256:
`00f69921a3db7776147d1a23a9312e7d4eb5cf5234cc629536d0a636e0dade34`.

Turn 1 reached text at `6.321 s`, began playback at `8.732 s`, and completed
at `11.530 s`. Turn 2 reached text at `3.776 s`, began playback at `7.700 s`,
and completed at `13.888 s`. Both used the exact retained v2 CUDA route with
no fallback or continuation gap. The 1.5-second first-audible target was not
met, so latency remains rejected/pending diagnosis. Machine playback is not
human-heard acceptance; `owner_heard_latency_acceptance` remains false until
Robert separately confirms both turns. The candidate remains default-off and
unpromoted.

Attempt 03 checkpoint SHA-256:
`b993b4ab6587a8f36d6b1eabcd8f252d6048500e0140527101fe8cca05a40054`.
