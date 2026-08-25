# Avatar Builder Blender Native Transaction Provider Contract

Date: 2026-08-25

Status: static request-side interface and hostile-mutation tests only; no native
provider implementation or execution authority.

## Result

`Core/avatar_blender_native_transaction_provider_contract.py` now defines an
inert private-payload request for one future provider-owned carrier
transaction. It closes the interface mismatch recorded by the carrier closure:
the old `kira.blender_native_launch_provider.v2` surface describes one launch,
while the carrier requires an inseparable build followed by audit.

The new interface identity is:

`kira.blender_native_carrier_transaction_provider.v1`

This identity names a contract, not an installed, reviewed, or callable
provider.

## Exact request boundary

One frozen request binds all of the following before any provider could be
invoked:

1. the validated static carrier closure and its complete input/output digests;
2. the exact private build and audit command payloads, in that order;
3. a bounded private environment and working directory;
4. the held Blender image identity expected by the closure;
5. all four create-new output paths:
   `one_run_authorization`, `candidate_blend`, `build_report`, and
   `audit_report`;
6. a contiguous retained directory chain ending at one private claim root;
7. distinct create-new claim and terminal-outcome paths;
8. the seven transaction phases already fixed by the reviewed closure; and
9. separate bounded build and audit timeouts.

Raw commands, paths, and environment values remain private fields of the
request. The safe review record exposes only digests and bounded metadata.
Every request construction or reconstruction revalidates the raw canonical
directory ancestry, exact final-directory/claim-root equality, and both the
claim and outcome parent relationships; recomputing digests cannot bypass
those relations.

The lexical Windows grammar requires an ASCII letter drive designator
(`[A-Za-z]:`) after an optional exact `\\?\` prefix. It rejects every Win32
forbidden component character (`<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, `*` as
applicable after separators are parsed), every U+0000-U+001F control,
trailing-dot or trailing-space components, alternate data
stream/extra-colon components, and DOS device basenames. The device set
includes `CON`, `CONIN$`, `CONOUT$`, `CLOCK$`, `PRN`, `AUX`, `NUL`,
`COM1`-`COM9`, `LPT1`-`LPT9`, and the `COM`/`LPT` aliases using superscript
digits `¹`, `²`, or `³`, case-insensitively and even with an extension. This
is not handle-derived identity evidence: 8.3 short-name aliases, reparse
targets, and hard-link identity remain unresolved until a reviewed native
provider proves them through retained handles, volume identity, and file IDs.

## Required two-stage behavior

Both stages require a suspended launch, Job assignment before image checking,
image identity queried from the retained process handle, no PID-based identity,
exactly one resume, and completion before the next transaction phase. The audit
stage additionally requires custody of the candidate created by the build
stage before audit launch.

Every reserved output must be created new, validated through a retained handle,
held until terminalization, and not published before the terminal outcome. The
claim and outcome must also be create-new durable records with payload and
parent-directory flush requirements. Exactly one terminal outcome is required.

## Hostile cases rejected statically

`Testing/test_avatar_blender_native_transaction_provider_contract.py` rejects,
without invoking a provider:

- one-stage requests and reordered build/audit requests;
- build/audit command substitution or aliasing;
- audit launch without prior candidate custody;
- PID identity or early path publication;
- output path substitution and output aliases;
- claim/outcome aliasing;
- UNC, duplicate, canonically aliased (including `C:\` versus `\\?\C:\`),
  drive-prefix-truncated, skipped, or non-contiguous claim directory chains;
- non-ASCII/nonletter drive designators (with or without the native prefix),
  Win32-forbidden/control characters, trailing-dot/space aliases, alternate
  data streams, extra-colon components, and reserved DOS device basenames;
- phase reordering;
- the legacy single-launch interface masquerading as the transaction
  interface;
- unknown success fields; and
- any body or execution authority changed to true.

The tests also bind the current 18-input machine closure read-only and verify
that the safe record contains no private command, path, environment, person,
or body-owner value.

## Deliberate non-actions

This milestone did not:

- discover, load, call, or review a provider;
- call Windows native APIs;
- create a claim, authorization, outcome, output directory, body, or file;
- start or resume Blender;
- build, audit, save, render, assign, activate, or export a body;
- add a reviewed provider ID or change the controller trust boundary;
- create or teach a new Avatar Builder lesson; or
- merge the Kira, Synthetic Robert, and private Biological Robert/user-avatar
  boundaries.

The request remains generic to the inactive carrier candidate. It does not
name a person, assign a carrier, infer maturity, add anatomy, or authorize use
for Kira, Synthetic Robert, or the private Robert/user avatar.

## Current truth

- Static two-stage provider request contract: present and locally tested.
- Native two-stage provider implementation: absent.
- Provider response/evidence contract: absent.
- Independent provider/security review: absent.
- Controller integration: absent and unauthorized.
- Native claim root selection: absent.
- Authorization and outputs: absent.
- Blender process started: no.
- Kira body created: no.
- Robert body created: no.
- Anatomy, assignment, activation, save, render, and export: unauthorized.

## Next bounded blocker

The next provider milestone is a native implementation plus a separately
reviewable response/evidence contract. It must prove real retained handles,
abnormal-death and replay behavior, Job containment for both launches, image
identity from created-process handles, build-pass/audit-fail cleanup, output
custody, durable exactly-once terminalization, and timeout teardown. Static
shape validity from this module cannot satisfy any of those proofs.
