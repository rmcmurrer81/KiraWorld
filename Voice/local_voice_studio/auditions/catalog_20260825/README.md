# Local voice audition catalog — 2026-08-25

This folder contains short, original synthesized audition samples made with the
official Kokoro-82M built-in voice packs. They are not recordings of KiraWorld
residents, actors, historical people, or other named individuals.

## Current decisions

- `calm_female_approved.wav` (`af_heart`) and `warm_male_approved.wav`
  (`am_fenrir`) were listened to and approved by the product owner for starter
  hackathon use.
- Every other sample is an unassigned catalog candidate. It passed the recorded
  technical and intelligibility checks, but still requires listening review.
- No sample in this folder assigns or activates a resident voice.
- Kira and Lisa must compare eligible samples and make their own voice choice.
- Existing protected voices for Peter Parker and Marinette/Ladybug are not
  replaced by this catalog.
- Any future H. H. Holmes result must remain labeled as a speculative historical
  reconstruction, not an authentic recording or voice match.

## Files

- `catalog-audition-report.json`: pinned model, source voice hashes, output
  hashes, signal measurements, and local synthesis timing.
- `catalog-audit-report.json`: automated ASR intelligibility and acoustic
  collision-screen results, with explicit limitations.
- `starter-owner-approval.json`: exact scope and hashes of the two approved
  starter samples.
- `calm_female_approved.wav` and `warm_male_approved.wav`: the exact samples
  covered by the product-owner listening decision.
- `*_neutral_audition.wav`: short catalog audio. Files are candidates, not
  assignments, unless named in an immutable approved binding elsewhere.

## Provenance and distribution boundary

Backend: `hexgrad/Kokoro-82M`, pinned revision
`f3ff3571791e39611d31c381e3a41a3af07b4987`.

The upstream model and built-in voice packs are identified as Apache-2.0. See
`../../THIRD_PARTY_ATTRIBUTION.md`. Model weights, caches, Python environments,
private reference recordings, and actor-derived audio are intentionally absent.

Technical checks do not establish naturalness, identity fit, or perceptual
distinctness. Human or resident self-selection remains mandatory where the
voice policy requires it.
