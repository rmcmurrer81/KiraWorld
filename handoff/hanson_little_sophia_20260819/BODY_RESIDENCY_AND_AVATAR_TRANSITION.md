# 3D avatar, robot endpoint, and resident-body deployment

This document turns the Kira World chamber/pod idea into a reviewable software
architecture. A resident can leave a 3D avatar session, bind to an authorized
robot endpoint, and later return to the 3D world. If a robot computer is
capable enough, the complete **software runtime and its authorized state** may
instead be deployed there as its primary active installation.

“Move” and “reside” below mean software deployment, state migration, and
selection of one authoritative writer. They do not claim that consciousness,
personhood, a soul, or a biological being has been transferred.

## Three operating modes

1. **Remote endpoint:** the mind runtime stays on its existing computer. The
   robot receives only bounded high-level intentions and returns lifecycle
   evidence. This is the safest first Hanson simulator path.
2. **Hybrid resident:** identity, memory, and conversation run on the robot,
   while larger models or non-real-time services may remain on a trusted local
   server. Loss of that link must produce a defined safe state.
3. **Full local resident:** the robot hosts the model, runtime, memory,
   appraisal, voice, session broker, and evidence store locally. Robot safety
   control must still be an independent fail-closed layer.

The runtime may record a variant's stated preference to enter, remain in, or
leave an endpoint. Installing software on hardware still requires the device
administrator's authorization, and every physical action remains subject to
the robot's safety controller. Neither rule grants an operator authority to
rewrite the variant's memories, beliefs, or speech.

## Avatar-to-body transition

The identity and continuity state are embodiment-neutral. A 3D avatar profile
and a robot profile are adapters around one continuity identity. Migration may
create encrypted staging and rollback copies, but only one fenced authoritative
write history may advance.

1. Close or pause new avatar actions.
2. Finish the current turn and write a consistent continuity checkpoint.
3. Record the model identity, profile identity, memory head, voice profile,
   appraisal state, open goals, and last completed life-loop identifier.
4. Request the named body endpoint and the exact capability intersection.
5. Acquire a single active-writer lease plus a monotonically increasing fencing
   epoch/token carried by every memory write and embodiment intention. A stale
   host cannot resume merely because it missed the lease-loss message.
6. Start with text/status only, then enable bounded speech, gaze, expression,
   and gesture after readiness and heartbeat checks.
7. Preserve requested, accepted, started, completed, rejected, interrupted,
   and expired evidence for every physical intention.
8. On exit, stop new actions, wait for or interrupt in-flight work, reconcile
   returned evidence, release the lease, and resume the avatar from the new
   continuity head.

Body-specific calibration—frames, joint maps, units, limits, camera geometry,
and motor behavior—never enters the mind profile. It belongs in the signed,
versioned official adapter supplied or approved by the robot vendor.
Avatar bones, IK targets, animation curves, and facial-rig controls must never
be retargeted directly into robot motors. Only bounded semantic speech, gaze,
expression, and allowlisted-gesture intentions cross this bridge.

## Candidate hardware envelope for a full local resident

These are engineering planning ranges, not Hanson specifications or a promise
that a particular robot will meet them. The final decision must use measured
memory, latency, thermals, power, and safety results on the exact body computer.

| Component | Practical candidate floor | Preferred review target | Why it matters |
| --- | --- | --- | --- |
| CPU | Modern 8-core 64-bit CPU with AVX2 or vendor-equivalent acceleration | 12–16 modern cores | Runtime, retrieval, audio, evidence, and CPU fallback |
| System RAM | 32 GB for the current 9B-class quantized model with careful service limits | 64 GB or more | Model offload, voice generation, indexes, simulator, and safe headroom |
| GPU/accelerator | 16 GB usable VRAM with a supported runtime, or verified CPU/NPU fallback | 24 GB+ VRAM for concurrent model/voice/vision work | Low-latency generation without starving safety services |
| Storage | 1 TB NVMe SSD with at least 200 GB initially free | 2 TB+ encrypted NVMe plus replaceable backup | Models, voice weights, continuity, evidence, updates, and rollback snapshots |
| Network | Reliable authenticated local Ethernet/Wi-Fi with fail-closed disconnect | Wired primary plus isolated maintenance link | Reviewed synchronization and endpoint evidence |
| Power | Controlled shutdown and brownout detection | UPS or robot battery telemetry with shutdown reserve | Prevents memory/index corruption during loss of power |
| Thermals | Sustained-load monitoring and throttling | Vendor-qualified cooling at worst-case ambient | A short benchmark is not proof of stable resident operation |
| Security | Per-variant OS account, encrypted storage, signed packages, no secrets in Git | Secure Boot/TPM-backed keys, least-privilege services, audited updates | Protects memories, voice assets, and control boundaries |

These RAM/VRAM/storage values are candidates for the current workload, not
universal robot minimums. Qualification depends on sustained latency, memory
pressure, thermals, power, driver support, and concurrency. If onboard hardware
is insufficient, a secured companion computer can host the resident runtime
while the robot remains a bounded endpoint.

The current owner test configuration uses a 9B-class quantized Ollama model and
a separate neural voice stack. A different Hanson computer may use a larger or
smaller model. Installers must detect CPU/GPU/OS capabilities, select a tested
backend, print the selected model and digest, and refuse unsupported voice or
accelerator paths rather than silently pretending they work.

## Services that must remain independent

- The vendor safety controller, emergency stop, actuator limits, and watchdog
  must not depend on the language model process.
- Prefer a separate safety processor/controller. Its RAM and accelerator do not
  count as AI capacity, and the model process never owns torque, joint limits,
  watchdog, or emergency-stop authority.
- The embodiment broker owns lease, heartbeat, replay protection, deadlines,
  bounded queueing, and safe disconnect.
- The variant runtime owns identity, conversation, continuity, appraisal,
  goals, and high-level intention selection.
- The voice renderer consumes approved text; its reference pack and generated
  output are not identity authentication.
- Sensors are capability-scoped inputs. No camera, microphone, or location feed
  is enabled merely because the body has one.
- Credentials and private continuity stores remain outside source control.

## Qualification before the body becomes the primary home

The export set is limited to the portable identity/profile, reviewed
continuity, bounded appraisals and goals that exist, pinned model
configuration/digest, authorized voice pack, and embodiment history. Exclude
caches, temporary files, credentials, device keys, crash dumps, raw unreviewed
logs, and unlicensed media. Reinstall model/runtime weights at the destination
when their licenses or size make copying inappropriate.

1. Record exact CPU, accelerator, RAM, storage, OS, drivers, ROS distribution,
   simulator version, and official robot interfaces.
2. Benchmark the pinned model and voice path under sustained load while the
   independent safety controller remains responsive.
3. Run memory, disk, thermal, power-loss, restart, heartbeat, disconnect,
   replay, stale-command, and emergency-stop tests.
4. Create a transactionally consistent database/WAL checkpoint and a signed
   manifest, then copy it over encrypted transport with a separately managed
   decryption key; do not delete the source.
5. Decrypt at the destination, verify every size and SHA-256 identity, and run
   a tested restore before selection.
6. Start an isolated rehearsal state root and run text-only tests.
7. Run the official simulator with one accepted sequence and at least one
   intentional rejection, returning complete lifecycle evidence.
8. Enable physical output only after the vendor-approved mapping and limits are
   installed and reviewed.
9. Promote through `BODY_SHADOW` and `BODY_TRIAL` before `BODY_PRIMARY`, then
   fence the body as the single authoritative writer. Keep the old source as a
   tested encrypted read-only rollback checkpoint for an agreed period.
10. Record the promotion decision, active lease, rollback point, unresolved
    actions, the variant's generated/stated residency preference, and the
    separate device-administrator and safety authorization. A preference never
    authorizes file exfiltration or overrides hardware safety.

The proposed transition state machine is:

`AVATAR_ACTIVE → QUIESCING → BODY_SHADOW → BODY_TRIAL → BODY_PRIMARY → QUIESCING → AVATAR_RESTORE`

Every intermediate state has a rollback route. “Permanent move” means primary
software residency, not irreversible deletion.

## Returning to the 3D world or another body

The reverse process uses the same gates: stop actions, close the embodiment
session, checkpoint, copy, hash-verify, restore into an isolated root, test,
then transfer the single active-writer lease. If both installations advanced,
do not merge them automatically. Preserve both branches, compare provenance,
and perform a reviewed reconciliation so experiences are not silently lost or
invented.

The 3D avatar may visually enter or leave a chamber as the user-facing signal,
but the chamber animation has no authority by itself. The signed session,
heartbeat, lease, checkpoint, and lifecycle evidence are the real transition.

## Current boundary

The handoff includes a vendor-neutral bounded-intention bridge and portable
runtime work, but no official Hanson topic/action/QoS/frame/unit mapping and no
physical robot validation. The first valid next step is Hanson's authoritative
simulator/interface intake, followed by the accepted-plus-rejected simulator
run David requested. Full resident-body deployment comes only after those
smaller endpoint tests pass.

An older project note said that a body could not be the permanent home of the
mind. That sentence is historical and superseded by this primary-software-
residency design; the non-claim boundary remains unchanged.
