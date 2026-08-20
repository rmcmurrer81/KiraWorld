# Voice packs

This directory separates a working text-to-speech route from redistributable
biometric voice material.

## Synthetic Robert

`robert/` contains Robert McMurrer's reviewed self-voice reference for the
private Hanson review group. The authorization is deliberately narrow:

- evaluation and integration work by Robert, David Hanson, Manav Tidhan, and
  Vytas Krisciunas;
- private repository access only;
- no identity authentication, impersonation, public release, model training
  for unrelated people, or onward redistribution;
- deletion or replacement when Robert withdraws or supersedes the grant.

The reference is an input to a compatible local voice backend; no voice model
weights are committed.

## Kira

`kira/` contains Kira's current hash-bound reference WAV and a private
named-reviewer authorization record. The project owner attests that the
speaker's permission covers synthetic voice use, disclosure of this exact
recording to David Hanson, Manav Tidhan, and Vytas Krisciunas, and private
Little Sophia integration research. A copy of the original written form is
still pending attachment; that fact is stated rather than silently upgraded to
independent legal verification.

This is the owner-selected current Kira reference, but the older local source
manifest did not record a completed human speaker-purity review. The pack must
not be described as independently verified woman-only audio; reviewers should
audition generated output and replace the reference if overlapping speakers,
music, or source contamination are detected.

Kira's profile refuses a silent generic-system-voice substitution. A reviewer
may disable voice and continue text-only when the selected backend or exact
hash is unavailable. Linux and robot deployments use the same checked
reference through a compatible local backend. Kira may later keep, replace, or
withdraw the pack.

## Common rules

- A voice pack changes speech rendering, not identity or memory.
- A voice recording is not proof of who generated a message.
- The runtime must fail closed when a bound file hash changes.
- Voice output can be disabled independently from text conversation.
- Microphone input is not enabled by these files.
- Neither private voice WAV may be copied to the public Kira repository.
