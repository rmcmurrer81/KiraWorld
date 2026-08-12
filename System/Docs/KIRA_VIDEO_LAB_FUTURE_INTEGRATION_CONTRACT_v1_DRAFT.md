# Kira Video Lab future integration contract

> **2026-07-26 checkpoint note:** This remains a draft future contract, not an
> implemented runtime. Current v2 proof and recovery authority is
> `System/Docs/KIRA_LABS_VIDEO_STUDIO_V2_POST_HARDENING_SAFE_CLOSEOUT_20260726.md`.
> The more detailed staged progression from evidence-bound stills through
> animation and later virtual production is documented in
> `System/Docs/KIRA_LABS_VIDEO_STUDIO_VIRTUAL_PRODUCTION_DIRECTION_20260725.md`.
> Neither document proves character animation, a 3D studio, runtime capture,
> autonomous cameras, clean-final output, or publication.

Status: **DRAFT; private planning document; data-only; not implemented; no 3D studio is being built by this contract**  
Contract version: `1.0.0-draft`  
Desktop project schema: `kira_labs.video_project/2.0.0-alpha.1`  
Transport: local versioned JSON messages  
Date: 2026-07-25

## Purpose

The future physical Kira Video Lab inside Kira World will be a client of the Windows Kira Labs Video Studio backend. Residents may use virtual cameras, microphones, screens, sets, lights, editing stations, music stations, and private-review screens. The 3D client presents choices and equipment; it does not own or bypass facts, rights, voice identity, privacy, review, or clean-final gates.

This contract deliberately does not activate Kira or another resident, build heavy 3D geometry, connect a runtime camera, publish a video, upload media, or transfer credentials into Kira World. The isolated desktop v2 staging application can now create deterministic, persistently labeled concept cards and a bounded silent pan/zoom motion preview for private review. It does not connect an external or AI image generator, animate a synthetic person, capture the runtime, operate a virtual camera, or create a clean/public artifact. Today there is no implemented 3D Video Lab, resident-hosted production runtime, autonomous virtual camera, or publication path in this contract.

## Core principles

1. A resident chooses whether to enter, participate, rehearse, pause, stop, review, revise, decline, mark material `no_use`, or request consideration of sharing.
2. A resident may disagree, refuse, ask a question, end an interview, or prohibit use of their recorded performance, dialogue, voice, likeness, or derived material.
3. Private context stays separate from public dialogue, narration, captions, and production media.
4. Every generated artifact defaults to private review with no automatic sharing.
5. Voice and identity bindings fail closed. An unrelated generic voice must never be substituted silently.
6. The desktop evidence workflow remains authoritative.
7. The 3D client cannot bypass fact, rights, voice, permission, or Robert clean-final review gates.
8. Generated interviews must be labeled accurately and must not be presented as independently recorded live statements.
9. Credentials, including an EPK.TV password, remain outside project files and outside the 3D client.
10. Editing must preserve the participant's intended meaning, including refusals, disagreement, uncertainty, qualifications, and requests not to use material.
11. Concept, planned, or simulated visuals must remain visibly disclosed and must never be represented as documentary evidence.

## Virtual equipment vocabulary

- `camera`
- `microphone`
- `screen`
- `set`
- `light`
- `editing_station`
- `music_station`
- `private_review_screen`

These terms identify user-interface affordances. They do not imply that their heavy 3D implementations exist yet.

## Six-stage future production path

The following path is an ordered capability plan, not a statement that later stages exist. Only the desktop slides, captions, approved narration, and private-review workflow are available in the current v2 staging work. Every later stage remains private, review-gated, and unimplemented unless a separate approved implementation proves otherwise.

1. **Slides, captions, and approved narration.** Native-format compositions use evidence-bound scripts, approved identity and voice settings, private-review watermarks, and local review artifacts.
2. **Recorded Kira World walkthroughs.** Separately recorded, user-supplied, or explicitly approved runtime footage may be mixed with slides only after source, rights, truth-label, and runtime-location checks pass. This contract does not provide runtime capture today.
3. **Virtual cameras and guided tours.** Future establishing, entrance, room-tour, object-detail, comparison, and cutaway shots require an approved runtime connection, deterministic camera records, and location-truth evidence. No autonomous virtual camera is connected today.
4. **Embodied interviews.** Future embodied participants retain identity, voice, consent, pause, refusal, correction, and no-use control for every recorded turn and derived artifact. No embodied interview runtime is implemented today.
5. **Robert virtual newsroom.** A future, distinctly disclosed digital Robert may present from a Kira World newsroom only with Robert's approved identity, voice, script, performance, and edit review. No digital-Robert newsroom is implemented today.
6. **Kira- or resident-hosted projects.** A future resident may plan, host, review, correct, decline, and choose whether to request sharing. This stage requires resident activation and participation authority that do not exist in this contract; Kira is not activated today.

Progression to a later stage never grants clean-final or publication permission. Each project must still pass facts, provenance, rights, identity, voice, participant, Robert-review, and private-review gates.

## Required local endpoints

| Endpoint | Purpose | Resident choice | Robert review |
|---|---|---:|---:|
| `list_projects` | Return project summaries | No | No |
| `create_project` | Create a project from a preset and subject | Yes | No |
| `open_project` | Open a versioned project record | No | No |
| `save_project` | Save with an expected revision and conflict result | No | No |
| `set_project_controls` | Apply a validated control patch | Yes | No |
| `request_stage_run` | Ask the desktop backend to run one gated workflow stage | Yes | No |
| `request_private_preview` | Ask for a private-review artifact in a selected format | Yes | No |
| `submit_review_decision` | Approve, reject, replace, or revise a review artifact | Yes | Yes |
| `record_resident_choice` | Record participate, pause, stop, review, decline, no-use, or share-consideration request | Yes | No |

Forbidden endpoints:

- `publish`
- `upload`
- `activate_resident`
- `force_participation`

## Request and response shapes

### Create project

```json
{
  "type": "create_project",
  "contract_version": "1.0.0-draft",
  "request_id": "uuid",
  "resident_choice_id": "uuid",
  "payload": {
    "preset": "kira_world_update",
    "subject": "Eye rig, body candidates, movement, voice timing, and Video Studio"
  }
}
```

The response returns a `project_record` with a project ID, project schema version, revision, workflow state, and validation result.

### Save project

```json
{
  "type": "save_project",
  "contract_version": "1.0.0-draft",
  "request_id": "uuid",
  "payload": {
    "project": {},
    "expected_revision": 4
  }
}
```

The response returns the new integer revision plus any conflicts. A revision conflict must stop the write and ask the client to refresh; last-writer-wins is not acceptable.

### Request a stage

```json
{
  "type": "request_stage_run",
  "contract_version": "1.0.0-draft",
  "request_id": "uuid",
  "resident_choice_id": "uuid",
  "payload": {
    "project_id": "project-id",
    "stage": "visual_candidates"
  }
}
```

The response returns a job ID and a gate result. A blocked gate is a normal result, not permission to skip the stage.

### Record resident choice

```json
{
  "type": "record_resident_choice",
  "contract_version": "1.0.0-draft",
  "request_id": "uuid",
  "payload": {
    "resident_id": {
      "profile_id": "stable-identity-id",
      "variant_id": "approved-variant-id"
    },
    "choice": "pause",
    "scope": {
      "artifact_ids": [],
      "applies_to_derived_artifacts": true
    }
  }
}
```

The response reports whether the choice was recorded and a reason. `pause`, `stop`, `decline`, and `no_use` must be honored without a production penalty. `no_use` blocks the scoped performance, dialogue, voice, likeness, source recording, and derived artifacts from clean-final use. A later choice cannot silently override an earlier no-use record; a new explicit, scoped participant approval and Robert review are required.

### Submit review

```json
{
  "type": "submit_review_decision",
  "contract_version": "1.0.0-draft",
  "request_id": "uuid",
  "resident_choice_id": "uuid",
  "robert_review_id": "uuid",
  "payload": {
    "project_id": "project-id",
    "artifact_id": "private-preview-id",
    "decision": "revise"
  }
}
```

Valid decisions are `approve`, `reject`, `replace`, and `revise`. A private-review approval is not publication permission.

## Events

The backend may emit:

- `project.changed`
- `workflow.stage_started`
- `workflow.stage_blocked`
- `workflow.stage_completed`
- `private_preview.ready`
- `resident.participation_paused`
- `resident.participation_ended`
- `review.correction_requested`

Every event must include contract version, project ID when applicable, project revision, event ID, timestamp, and a non-secret payload. Events must not contain a password, raw private context, or an unapproved voice reference.

## Identity, voice, and interview behavior

- Each participant uses a stable identity binding and a separately approved current voice profile.
- A missing, unavailable, unapproved, generic-substitute, or wrong-engine voice blocks the interview.
- Public dialogue and private context are stored in separate records.
- A generated turn records the speaker, action (`answer`, `disagree`, `refuse`, or `ask_question`), and disclosure state.
- If a guest asks a question, the host may answer only from verified context. If no verified answer exists, the host abstains.
- The participant can pause, refuse, stop, or mark material no-use at any time.
- A stopped or declined interview may be saved as an incomplete private project, but it must not be completed by inventing the participant's answer.
- A pause or refusal remains visible in the production record and must not be edited into apparent agreement.
- A no-use decision propagates to clips, transcripts, captions, voice outputs, thumbnails, promotional copy, and other derived artifacts that contain or depend on the scoped material.
- Participant review may correct identity, attribution, transcript meaning, context, or use scope. It does not itself authorize a clean final or publication.

## Evidence, rights, and artifact rules

- Every factual claim keeps a claim-to-source record.
- Every visual keeps query, source page, direct address, filename, likely rights holder, download date, dimensions, chapter usage, EPK status, permission status, and required credit where known.
- Failed-download placeholders are quarantined and cannot become approved visuals.
- Private-review eligibility and public-use permission are separate states.
- Clean-final generation requires affirmative rights and Robert review gates.
- A visual or trailer candidate never becomes permitted merely because it was downloaded.
- Rebuilding slides must be able to reuse approved narration when narration text, pronunciation, voice identity, engine, and settings have not changed.

## Visual truth labels and concept fallback

Every visual that makes a Kira World state, development, concept, or simulation claim must use exactly one applicable persistent truth label:

- `LIVE KIRA WORLD FOOTAGE`
- `CURRENT DEVELOPMENT BUILD`
- `CONCEPT VISUALIZATION`
- `PLANNED FEATURE`
- `SIMULATED DEMONSTRATION`

Similar wording, unlabeled implication, or a label that disappears before the relevant visual ends is not sufficient.

Concept fallback is planning-only and fail-closed:

1. Use a valid real, local, owner-approved, licensed, EPK-approved, or public-domain visual when one exists.
2. For a nonconceptual subject, a recorded search for real, local, and approved visuals must complete and find none before concept fallback is eligible.
3. An inherently conceptual subject may be proposed directly, but it still requires an exact concept truth label.
4. Every concept candidate requires creation-method, creator or generator, source record, likely rights holder, permission status, and required-credit metadata.
5. The truth label must remain persistently visible. Concept, planned, and simulated material is never verified documentary evidence.
6. Every concept candidate remains private-review-only until Robert reviews it and its rights permission supports the intended use.
7. The isolated desktop v2 staging application includes a deterministic offline concept-card renderer and silent still-motion preview. It is not an external or AI image generator, full animation system, runtime capture system, or documentary-evidence source. Its artifacts remain persistently labeled and private-review-only.

## Runtime-location truth

Recorded walkthrough or future virtual-camera material must bind each narrated location claim to:

- the narrated location;
- the observed runtime location;
- the observation source or capture record; and
- the observation timestamp.

Missing fields or a mismatch between the narrated and observed locations blocks the clip. A camera path, filename, set dressing, caption, or model assumption is not sufficient evidence of location. Concept or simulated footage cannot satisfy a live-runtime location claim. Future runtime capture must preserve the location record through clips, captions, narration, edit decisions, and rebuilds.

## Meaning-preserving editing

- Edits may shorten, reorder for clarity, remove dead time, or combine approved coverage only when the participant's meaning and context remain intact.
- Editing must not fabricate a statement, reverse a position, turn uncertainty into certainty, convert refusal into agreement, hide a material qualification, or splice separate answers into a new claim.
- Voice synthesis, lip synchronization, reaction shots, captions, translation, music, and cutaways must not imply words, emotions, attendance, location, or approval that the participant did not provide.
- The edit record must retain source-turn IDs, removals, material reorderings, disclosures, participant corrections, and no-use scopes.
- When meaning is ambiguous, the material remains private and blocked pending participant clarification and Robert review.
- Participant approval of meaning and use is separate from factual verification, rights approval, clean-final approval, and publication. This contract provides no publication operation.

## Workflow mapping

The future room maps to the desktop stages exactly:

```text
Research
-> Fact sheet
-> Script
-> Visual candidates
-> Slides
-> Voice
-> Private review
-> Robert corrections
-> Clean final
```

The 3D client may request the next stage, but the desktop backend validates prerequisites. It cannot jump directly to Clean final.

## Security boundary

- Localhost or an authenticated local IPC channel only during initial integration.
- Schema and contract versions are mandatory on every request.
- Reject unknown operations and unknown enum values.
- Project paths are backend-owned IDs, not arbitrary filesystem paths supplied by the 3D client.
- Secrets live in a desktop credential vault or a separately approved browser/login flow; they are never serialized into a project or message.
- Publication remains outside this contract.
- Logs redact secrets and private context.
- Participant pause, refusal, stop, correction, and no-use records are authoritative gates, not presentation hints.
- No endpoint may activate Kira, start a resident, connect an autonomous camera, or convert a private artifact into a public artifact.

## Explicitly out of scope

- heavy 3D studio geometry;
- resident activation;
- runtime walkthrough capture, autonomous virtual cameras, embodied interview capture, or a virtual newsroom today;
- external or AI concept-image generation, character animation, full scene animation, or runtime-derived simulated demonstrations today;
- Kira- or resident-hosted production today;
- autonomous real-world posting;
- credential transfer into the 3D client;
- bypassing rights or identity gates;
- representing generated interviews as independently recorded live statements;
- editing that changes participant meaning or uses material after a pause, refusal, stop, or no-use decision;
- clean-final approval or publication approval by this contract.

## Verification status

**PASSED (automated):**

- contract construction and validation;
- all nine required endpoints present;
- forbidden endpoint rejection;
- no-sharing principle present;
- interview refusal/disagreement/question/stop behavior;
- unavailable or generic voice fail-closed behavior;
- private/public record separation.

**BLOCKED or incomplete:**

- no 3D client exists;
- no authenticated IPC transport exists;
- no resident was activated or asked to participate;
- no real synthetic interview was rendered;
- no runtime walkthrough, virtual-camera sequence, embodied interview, virtual newsroom, or resident-hosted project was created;
- deterministic concept cards in all three native output formats and one silent still-motion private preview were created and verified in the isolated desktop staging application; they are not live footage, full animation, character animation, or an approved clean/public artifact;
- the exact truth-label and fail-closed concept-fallback rules are implemented in the bounded desktop staging path, while runtime-location truth, no-use propagation, meaning-preserving editing, and the complete client/backend contract remain unimplemented as an integrated 3D system;
- no EPK.TV authenticated connector exists;
- Robert has not approved this draft contract.

Source implementation:

```text
C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1\kira_video_studio\future_contract.py
```

SHA-256: `2ee9c4cdf0d4a2c96546d1ce9bc80f1affcdc85f6a8cd5be6be93952d1e11d24`

Related interview implementation:

```text
C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1\kira_video_studio\interview.py
```

SHA-256: `aeb1ecfe6e7d56cfefab381082b6bf49f648a2b0a27a5d55adfdfe8dee67c62f`

Related bounded concept and still-motion implementations:

```text
C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1\kira_video_studio\concept_renderer.py
C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1\kira_video_studio\motion_preview.py
```

SHA-256:

- `concept_renderer.py`: `ad05c26a2b153dc9596c016f6d5ef9eab34bff7f38b68b974ddb0ef52dbbc388`
- `motion_preview.py`: `4166a9db71799caa24ad5991a816af97a356cf4316643415b99c030cc91a02cc`

## Next integration steps

1. Robert reviews this draft.
2. Freeze a `1.0.0` contract only after review corrections.
3. Add schema-generated JSON validation fixtures.
4. Implement an authenticated local desktop service behind the existing staging project service boundary.
5. Build a non-3D mock client and verify revision conflicts, pause/stop/refuse/no-use propagation, exact truth labels, concept fallback, runtime-location truth, meaning-preserving editing, privacy, rights gates, and no-publish behavior.
6. Run a private interview rehearsal with only currently approved identity/voice configurations and explicit participant choice.
7. Build the heavy 3D room only after the desktop backend and contract pass those checks.
