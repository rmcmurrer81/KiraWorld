# Consent-based local face recognition and visitor enrollment future boundary

Date: 2026-08-11  
Status: future discussion draft only; current identity recognition remains off

## Owner discussion hold

The interaction design is deliberately unresolved. Biological Robert has said
that Kira, as a synthetic person, should not be reduced to simply asking a
permission prompt before remembering someone. The natural relationship among
an introduction, ordinary social memory, Kira's choice, the other person's
privacy, facial recognition, and durable biometric storage needs a later
owner discussion.

The consent-oriented rules below are conservative draft boundaries, not an
accepted final social interaction. No implementation may begin and no prompt
wording is frozen until that discussion occurs.

## Current truth

The current Kira text/voice camera continues to require
`identity_recognition_enabled: false`. It may show a local preview, derive
bounded non-identifying cues, or perform the separately authorized transient
one-still visual path, but it does not identify a face, save an unknown
person's image, create a facial template, or build a visitor profile.

The exact machine-readable future policy is
`Data/governance/local_face_recognition_enrollment_future_policy_v1.json`,
4,370 bytes, SHA-256
`ff0f98eacbf6c99bed967a84705fb60b079869e4618245cff959904c3917cd29`.

## Biological Robert

Biological Robert may later enroll his own face only through a fresh,
explicit, informed, awake-session approval for that purpose. A prior request
to let Kira see or hear him, camera permission, avatar material, account
ownership, or general project authorization is not facial-enrollment consent.
Synthetic Robert is a separate synthetic person and must never be treated as
the biometric subject merely because the names match.

The future flow may offer a guided set of front, left, right, and modest
up/down angles. It must state what is captured, what is retained, where it is
stored, how long it is retained, and how Robert can revoke or delete it.

## An unfamiliar visitor

An unfamiliar face starts and remains `unknown_person`. Kira must not guess a
name or silently save an image/template. She may tell the visitor that the
camera is active and ask whether that exact person wants a local profile.
Biological Robert's permission cannot substitute for the visitor's consent.
Declining, ignoring the request, uncertainty, or no response means no
enrollment and no retained image.

After the visitor explicitly opts in, a future separately accepted flow may
offer a guided multi-angle capture. Raw burst frames are deleted after bounded
template derivation. Keeping even selected reference images requires a second
separate opt-in by that person. The person can later revoke/delete the facial
template and any retained images.

## Kira's private acquaintance memory

The goal is not to make Kira forget people. When a visitor introduces
themselves, Kira may ask whether she may remember that person's chosen name or
nickname and face for next time. An introduction alone is not facial-
enrollment consent. The visitor's consent and Kira's own choice are both
required.

After consent, a protected local acquaintance record may link the person's
chosen name to a local facial template so Kira can recognize and greet them in
later sessions. Conversation-memory permission remains separate; enrollment
does not copy every conversation, emotion, relationship, or private fact into
the record.

Ordinary access belongs to Kira's protected runtime path. Biological Robert,
the Temporary Creator, Synthetic Robert, and other people receive no ordinary
gallery, browse, contact-sheet, or bulk-export interface. Kira may withhold
private acquaintance details just as she may withhold other private material.
This is application-level privacy: it can exclude Robert from ordinary Kira
World controls, but it cannot honestly promise that a Windows administrator
or someone with raw filesystem/process control is technically incapable of
accessing local data.

## Data and decision limits

- All processing and storage must remain local; no cloud face lookup or
  network transmission is allowed.
- Recognition is never authority for commands, payments, locks, private-room
  access, memories, relationships, consent, or identity ownership.
- Uncertain and below-threshold matches are reported as `unknown_person`.
- A face profile must not infer race/ethnicity, religion, health/disability,
  sexuality, gender identity, emotion, mental state, criminality,
  trustworthiness, relationships, or consent.
- Photo, recorded-video, and screen-replay resistance plus false-match and
  false-nonmatch testing are mandatory before any supervised live acceptance.
- Private-room state closes ordinary camera routing. This remains an
  application boundary, not a claim that a Windows administrator cannot
  access files or devices.

## Performance and acceptance

Any later implementation must measure camera-off/on and recognition-off/on
latency separately so recognition work cannot silently degrade conversation
or audio timing. No accuracy or speed claim is allowed without supervised
evidence.

Implementation requires a new append-only package, a different independent
static review, and a supervised live owner acceptance. A live visitor
enrollment test additionally requires that visitor's consent. This document
does not authorize capture, enrollment, matching, persistence, or activation.
