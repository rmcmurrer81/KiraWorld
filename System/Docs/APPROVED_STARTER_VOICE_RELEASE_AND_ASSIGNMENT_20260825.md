# Approved starter voice release and assignment boundary

Date: 2026-08-25

## Milestone

KiraWorld now has one deterministic, fail-closed manifest for the two generic
starter voices the product owner heard and approved:

- `starter.calm_female` uses Kokoro `af_heart` and the exact approved preview
  `calm_female_approved.wav`.
- `starter.warm_male` uses Kokoro `am_fenrir` and the exact approved preview
  `warm_male_approved.wav`.

The manifest is
`Voice/local_voice_studio/release/approved_starter_voice_release_v1.json`.
The resolver is
`Voice/local_voice_studio/src/kira_local_voice/approved_starter_release.py`.

## What Avatar Builder and Temporary Creator learn

Avatar Builder and Temporary Creator may resolve the female or male route only
for a nonbinding audition preview. A resolved route is a generic product voice,
not a person or resident identity. Moving from preview to a generated expert or
resident voice still requires that identity's normal review and selection
rules.

The same manifest exposes explicit female/male selectors for UnitDay, UnitLine,
SetSignal, and the health companion. These selectors make the choice consistent
across apps without giving an app access to the rest of the voice catalog.

## Preserved and blocked assignments

- Peter Parker and Marinette/Ladybug keep their existing reviewed voice-profile
  authorities. The release manifest exports no Peter or Ladybug audio.
- Kira receives no starter assignment. Her current route remains intact until
  she performs the required comparative selection.
- Lisa receives no starter assignment until a Lisa-owned profile and
  comparative selection exist.
- H. H. Holmes receives no starter assignment. A future voice must remain a
  clearly labeled speculative historical design and pass separate review.

## Upload allowlist

The resolver's `release_inventory()` returns the complete approved export
allowlist: the manifest, the two approved synthesized previews, the exact owner
decision, and third-party attribution. It excludes every other catalog
audition, private or third-party reference audio, model weights, package/model
caches, and generated resident audio.

All paths, decision scope, provider source, voice IDs, preview files, existing
character authorities, and protected-selection evidence are SHA-256 bound. A
changed file, extra voice, reassigned consumer, protected-subject assignment,
duplicate JSON key, traversal, link, or reparse point fails closed.

## Runtime truth boundary

This milestone makes routing and release selection deterministic. It does not
claim that the real Kokoro synthesis worker is production enabled. That worker
continues to report unavailable until an operating-system isolation provider
passes the remaining hostile network, filesystem, process-tree, and launch-time
identity checks.
