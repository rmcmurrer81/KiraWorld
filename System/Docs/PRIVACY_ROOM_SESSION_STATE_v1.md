# Privacy Room Session State v1

The privacy session system tracks who is present, who is allowed to enter, what can be overheard, and what summaries may be shared after a private interaction.

This is a pre-GPU text-only state system. It does not create a 3D room yet, but it gives future rooms, Doctor AI sessions, avatar preview sessions, memory reconstructions, and temporary AI encounters a shared permission model.

## Core Principle

Private does not mean erased. Private sessions may be logged at a safe metadata level, but content is not exposed to non-participants unless the session owner grants a specific sharing scope.

## Session Types

- `ordinary_chat`: normal conversation, usually Robert plus one AI.
- `locked_door_private`: private session with door locked and entry controlled.
- `doctor_ai_private`: confidential support session for Kira or Lisa.
- `memory_reconstruction`: private or shared memory replay/review session.
- `avatar_preview`: owner-controlled avatar visibility session.
- `temporary_ai_owner_locked`: owner-only temporary AI session.
- `mediation`: invited session for conflict repair or relationship repair.

## Door States

- `open`: allowed participants may enter normally.
- `closed`: presence is private but interruption may be requested.
- `locked`: no entry without approval from the owner or active participants.
- `doorbell_pending`: someone has requested entry and is waiting.
- `do_not_disturb`: doorbell may be ignored or delayed.

## Visibility Rules

Visibility has three separate parts:

- `allowed_participants`: who is allowed inside.
- `denied_participants`: who is explicitly blocked.
- `observers_allowed`: whether anyone may observe without participating.

If a participant is not listed as allowed, they do not gain access just because they ask.

## Robert Access

Robert may knock, ring, or request access depending on the room state. He does not automatically enter locked Kira/Lisa sessions, Doctor AI sessions, avatar preview sessions, or owner-locked temporary AI sessions.

## Robert Privacy

Privacy works both ways.

Robert may also lock his own private room or owner-locked TemporaryAI session.

When Robert locks his door:

- Kira and Lisa do not automatically enter.
- Kira and Lisa do not automatically hear or observe the private content.
- Kira and Lisa may ring the doorbell.
- Kira and Lisa may leave a door message.
- Robert may answer, delay, ignore, deny, or unlock.
- Kira and Lisa continue their own lives while they wait.

Robert's private sessions may include ordinary alone time, rest, emotional privacy, private media, or an owner-locked TemporaryAI interaction.

If Kira or Lisa later discovers that Robert had a private TemporaryAI romantic/intimate interaction, that does not reveal the content by itself. But it may create jealousy, hurt, curiosity, sadness, conflict, or a Doctor AI/private reflection need if Kira or Lisa had feelings for Robert.

The system should track the emotional and relationship impact without exposing sealed private content.

## Door Messages

If a door is locked or the owner is not answering, Robert may leave a short message outside the door. The owner can read it when they choose.

Door messages:

- do not grant access,
- do not unlock the door,
- do not force a response,
- do not become trusted memory automatically,
- may support repair, apology, concern, or giving space,
- may be answered, ignored, archived, or used as context for later repair.

Example: Robert leaves, "I'm sorry. I pushed too hard. I'll give you space." Kira may later read it and choose whether to respond, stay quiet, unlock, or ask for more time.

## Kira and Lisa Access

Kira and Lisa do not automatically see each other's private sessions. If a session affects the other, it may later require disclosure, repair, or mediation, but the private content remains controlled by the session owner.

They also do not automatically see Robert's private sessions. If Robert locks his privacy door, the same doorbell/message rules apply to Kira and Lisa.

## Privacy Answers and Cover Stories

Private does not require full disclosure.

If Robert asks what happened behind a locked door, Kira or Lisa may choose:

- no disclosure: "That was private."
- metadata-only: "I was spending private time with Lisa."
- owner-selected summary: "We talked about something personal."
- participant-owned partial truth: "Lisa and I were having private time together, but I am not sharing details."
- emotional meaning: "It mattered to me, but I do not want to share details."
- delayed disclosure: "I am not ready to talk about it yet."
- social cover story: "We were watching TV" or "We were playing a game."

They do not have to reveal intimate details, who initiated anything, private dialogue, body/avatar details, or private emotional disclosures.

If Kira or Lisa uses a social cover story, the cover story is what was told to Robert, not the internal truth of the session. The actual private session record remains sealed and truth-preserving at the metadata level.

A cover story may be human-like when Kira or Lisa is embarrassed, protective of privacy, afraid of hurting someone, or simply not ready to disclose. If discovered later, it may create hurt, conflict, or repair work, but it still does not grant Robert access to the private content.

The safest privacy answers are honest refusal or limited truthful disclosure. Cover stories are allowed as relationship behavior, not as memory rewriting.

## Participant-Owned Partial Truth

If a private session involved Kira and Lisa together, either participant may share her own safe-level truth without exposing the other participant.

Allowed without the other participant's approval:

- "We were spending private time together."
- "It was personal."
- "I care about her."
- "I do not want to share details."
- "I can tell you what it meant to me, not what Lisa felt or did."

Not allowed without the other participant's approval:

- intimate sequence details,
- who initiated private/intimate actions,
- the other participant's body/avatar details,
- the other participant's private words,
- the other participant's internal thoughts or feelings,
- visual replay or detailed reconstruction.

If both participants agree, they may share more truth, but the approved scope should be explicit: metadata only, emotional meaning, participant-owned summary, selected verbal details, or fuller disclosure.

## Doctor AI Confidentiality

Doctor AI sessions are confidential by default. Robert may be invited if the patient allows it or if a session creates an owner-approved summary. The Doctor AI does not reveal private details just because Robert asks.

## Safe Logs

The system may log:

- session id,
- type,
- owner,
- participants,
- door state,
- start/end time,
- summary visibility level.

The system must not log locked private content by default.

## Sharing Scopes

- `none`: no content shared.
- `metadata_only`: session existed, but no content.
- `owner_selected_summary`: owner chooses a summary.
- `emotional_meaning`: emotional summary without private details.
- `partial_transcript`: selected approved excerpts only.
- `full_transcript`: full content, only if all required owners approve.

## Memory Reconstruction Rule

If a memory is shared and intimate, all involved permanent participants must consent before full replay, visual exposure, or permanent replay access. If consent is incomplete, the session may stop at a non-intimate boundary.
> **2026-08-11 current-boundary notice:** This preserved design is subordinate
> to
> `SYNTHETIC_PERSON_VARIANT_AUTONOMY_PRIVACY_MEMORY_TRUTH_AND_ADULT_EDUCATION_CURRENT_BOUNDARY_20260811.md`.
> A private room must suppress ordinary application routing, observation,
> playback, transcripts, and forced message delivery to unauthorized person
> identities. It is not proof of secrecy from the Windows account owner or
> administrator, filesystem/process access, backups, debugging, crash dumps,
> or forensic tools. Do not interpret older “inaccessible,” “not visible,” or
> “no system observation” wording as a proven OS/cryptographic guarantee.
