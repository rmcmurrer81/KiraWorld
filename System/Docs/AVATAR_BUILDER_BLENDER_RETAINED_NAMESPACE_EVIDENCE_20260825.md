# Avatar Builder Blender Retained Namespace Evidence

Date: 2026-08-25

Status: static retained-handle evidence shape and hostile fake-provider tests
only; no native provider implementation, native API call, Blender execution,
or body authority.

## Result

`Core/avatar_blender_native_namespace_evidence_contract.py` defines a
separately testable response boundary for the two-stage carrier transaction.
Its interface identity is:

`kira.blender_native_carrier_transaction_namespace_evidence_provider.v1`

The boundary requires a provider response to bind every requested target to a
normalized final DOS path, complete retained ancestor chain, local fixed-volume
identity, 128-bit file ID, single-link state, zero reparse state, and one
strongly retained opaque handle. The validator remains pure and does not
discover or call a provider.

## What this closes at the static interface

The request contract can reject malformed Windows path text, but text alone
cannot resolve a short-name alias, ancestor junction, hard link, mounted
volume, or identity substitution. The response boundary therefore requires
the future provider to report exact results from these sources:

1. `GetFinalPathNameByHandleW(FILE_NAME_NORMALIZED|VOLUME_NAME_DOS)`;
2. `GetFileInformationByHandleEx(FileIdInfo)`;
3. `GetFileInformationByHandleEx(FileStandardInfo)`;
4. `GetFileInformationByHandleEx(FileAttributeTagInfo)`;
5. `GetVolumeInformationByHandleW`; and
6. `GetDriveTypeW(DRIVE_FIXED)`.

For every Blender image, working directory, claim-chain directory, reserved
output, claim, and terminal outcome, the normalized canonical path must equal
the requested canonical path. A normalized long path that differs from a
requested 8.3 spelling is rejected. Every root-to-parent component must be
present in order, non-reparse, retained, and on the same local fixed volume as
the target. Distinct canonical paths may not reuse the same volume-and-file-ID
pair. Every regular file must report exactly one link.

When paths share an ancestor, they must reuse the same in-memory evidence
object and retained handle. Separate evidence objects for one canonical path,
opaque token aliasing, different close providers, or an early close all fail
closed. A module-private closure owns construction snapshots keyed by object
identity and weak references; those snapshots retain the original provider,
kind, opaque token, close provider, captured close callable, and lifecycle
phase outside the provider-writable response graph. Path, target, and response
snapshots likewise retain their construction-time query-source, binding,
authority, and original child-object references outside that graph. Child
identity is compared with `is`, not a recyclable integer object address.
The three provider evidence dataclasses are exact, slotted, and weak-reference
capable, so an instance cannot acquire a forged `safe_record`, validator, or
replacement `__dict__`. Validation and safe-record generation enter canonical
module-level functions that recheck the complete live graph against those
snapshots and recurse directly into every target, ancestor, path, handle,
query-source field, and false authority field without dispatching through an
instance method.

The upstream transaction request is deliberately treated as another untrusted
object graph because its older frozen dataclasses are not slotted. This layer
serializes every declared live field itself, including stage, output, source
closure, transaction phase, environment, path, digest, and authority values.
Before any equality, hashing, membership, mapping lookup, serialization, or
graph reconstruction, it requires the expected exact built-in scalar or
container type. At module import it captures and attests the canonical
`gc.get_referents` built-in. For an immutable mapping proxy, that captured
built-in inspects the proxy without mapping dispatch, requires exactly one
backing object of exact built-in `dict` type, and makes one built-in `dict.copy`
snapshot. It then rebuilds a private clean request graph field by field from
those gated copies before calling the upstream private validator. An
injected request, stage, or output `safe_record` is neither copied nor called;
an `Evil(str)` equality subclass or `EvilHash(str)` key cannot conceal a
changed schema, status, interface, operation, phase, worker role, output role,
custody phase, query source, authority key, or request digest.

The clean request, safe record, and canonical request digest are installed in a
closure-owned weak registry behind an opaque identity-bound capsule. The
capsule exposes only the request digest and contains no pointer to the caller's
request, environment, authority, or backing dictionaries. Response validation
resolves that private clean snapshot. Only the exact-gating public binder can
issue a capsule. No standalone issuer, resolver, registry builder, or
resolved-request validator remains in the module namespace after import. The
public response validator requires a previously bound exact capsule and rejects
a raw request before it touches response evidence. Validation never revisits
caller-owned fields or mappings after binding.

Close state moves monotonically through open, closing, closed, or failed. A
successful close cannot be reset, and an exception or non-exact close result is
terminal and cannot be retried. Coherently rewriting both visible lifetime
fields, every visible token and close provider, or a fabricated in-object seal
cannot rewrite the closure-owned truth. Raw final paths and opaque handles do
not enter the safe review record.

## Bounded Python threat model

This repair covers post-construction mutation of the retained-handle, path,
target, response, and supplied transaction-request object graphs through
ordinary assignment or `object.__setattr__`, including a coherent rewrite of
all visible mirrors before validation or safe-record generation. It rejects
instance serializer/validator shadowing structurally on evidence objects,
ignores such shadowing on the supplied request graph, and rejects scalar or
container subclasses before they can control equality, hashing, membership,
mapping lookup, canonical serialization, or reconstruction. A mapping proxy
around a custom `Mapping` is rejected by inspecting its sole backing referent
before any `items`, iteration, indexing, length, equality, or hashing method can
run. An accepted built-in mapping is copied once; later caller mutation or
concurrent flipping of its original backing has no effect on capsule validation
or the receipt. Direct capsule construction, a cloned capsule using the real
seal, and post-bind seal substitution fail the registry identity check. The
ordinary module namespace exposes neither a capsule installation factory nor a
resolver or resolved-state validator. The handle boundary also uses the
captured construction token and close callable rather than a later visible
replacement.

This is not an in-process Python sandbox. The mapping inspection depends on the
attested CPython GC built-in and exact built-in container behavior. It does not
claim resistance to code that reflects into module-private closure cells,
monkeypatches this module's captured globals or classes, controls a debugger,
or writes interpreter memory. The upstream
transaction contract remains responsible for its request, and a future native
provider still requires an independently reviewed isolation model and hostile
real-machine tests. The closure snapshots prove construction-to-use stability
inside this bounded interface; they do not prove that provider data or an
opaque token is genuine operating-system evidence.

## Exact target coverage

The validator derives the required target order from the private clean
transaction request held by the bound capsule:

- held Blender image;
- working directory;
- every directory in the claim-root chain;
- `one_run_authorization`;
- `candidate_blend`;
- `build_report`;
- `audit_report`;
- create-new claim; and
- create-new terminal outcome.

The Blender image additionally binds the byte count and content digest already
held by the transaction closure. Every created file must be positive-length,
must have been observed absent before create-new, and must remain unpublished
before terminalization.

## Hostile fake-provider coverage

`Testing/test_avatar_blender_native_namespace_evidence_contract.py` exercises
the boundary without native APIs or file creation. Its 43 focused tests reject:

- normalized long-path drift from an 8.3 request;
- reparse flags or nonzero reparse tags;
- hard-link counts other than one;
- a volume change inside one ancestry;
- one volume-and-file identity reused by distinct paths;
- missing, reordered, or duplicated ancestors;
- separate evidence objects for one canonical path;
- aliased opaque tokens;
- mixed handle-close providers;
- an early handle close;
- handle-kind drift after evidence construction;
- handle-provider drift after evidence construction;
- substitution of a different unique opaque token;
- resetting a closed handle to appear open;
- coherent substitution of every handle-close provider;
- coherent substitution of every token and close provider plus a fabricated
  replacement seal;
- coherent reset of both visible close fields followed by a duplicate-close
  attempt;
- coherent substitution of path-evidence and handle kind;
- coherent provider substitution across the request, response, target, path,
  and handle mirrors;
- post-construction query-source substitution;
- post-construction body-authority substitution;
- retry after an exception or non-exact close result;
- a same-valued cloned child substituted for the original retained child;
- equality-spoofing objects substituted for exact strings or digests;
- explicit handle reinitialization attempting to overwrite trusted identity;
- a concurrent second close while the first close is in progress;
- substituted native query sources; and
- any reviewed-provider, operating-system-proof, or body-created flag changed
  to true.

The newest exact regressions additionally prove that:

- path, target, and response objects have no instance `__dict__` and reject an
  injected `safe_record` that claims a forged query source or body creation;
- namespace validation never dispatches an injected request `safe_record`,
  even when that method raises if called; and
- replacing request authority with an immutable mapping that enables provider
  invocation still fails when a shadowed request `safe_record` returns the
  original all-false record;
- every declared request string, including source-closure identities, private
  paths, and digests, rejects an equality-spoofing `str` subclass before use;
- stage schema, stage ID, worker role, command items, ordinal, digests, and
  timeout accept only exact built-in types before stage lookup or hashing;
- output schema, role, custody phase, private path, and digests reject equality
  and hash-spoofing subclasses before output-role lookup;
- transaction-phase, directory, stage, and output containers must be exact
  tuples whose scalar members have exact built-in types; and
- environment and authority mappings reject forged subclass keys or values
  before set membership, dictionary construction, or upstream validation; and
- mapping proxies around hostile custom mappings are rejected from their
  GC-visible backing type without calling `items`, iteration, indexing, length,
  equality, or hashing on the hostile object;
- monkeypatching the mutable public `gc.get_referents` module attribute after
  import cannot intercept binding because only the captured, attested built-in
  is called;
- mutations made to caller-owned request fields and mapping backings after
  capsule binding, including concurrent false/true authority flips, do not
  alter repeated validation receipts; and
- direct capsule construction, an attacker-closure-issued clone carrying a
  genuine seal, digest lookup on that clone, and replacing a real capsule's
  seal all fail closed against the closure-owned identity;
- the module exposes no standalone capsule issuer, resolver, registry builder,
  validator wrapper, or resolved-request validation bypass after import; and
- the capsule-only public validator rejects a raw request before reading even a
  deliberately explosive response object.

The focused suite passes all 43 tests. The focused suite plus the adjacent
native-provider, transaction-provider, and carrier-closure suites passes all
76 tests.

The positive fake response proves only that the structures and relationships
are internally consistent. Its receipt explicitly retains false values for
provider review, provider invocation, operating-system verification, Blender
execution, body creation, runtime activation, and public export.

## Avatar Builder curriculum candidate

The bounded lesson candidate is:

`Avatar/avatar_builder/body_systems/avatar_builder_blender_native_namespace_evidence_candidate_v1.json`

It binds the contract and hostile test bytes and teaches one blocking rule:
path text is never enough; require normalized held-handle ancestry and stable
volume/file identity, keep construction snapshots outside the writable response
graph, state the bounded Python threat model, and start no process when any
native link is unproven. The candidate does not add an executable method or
alter a controller allowlist.

Bound source identities at creation:

- contract: 84,019 bytes,
  `17a82e052ec66c5ba65ccad103fb7a3ca812cfbed88c168a36230732c3d4ea60`;
- tests: 66,487 bytes,
  `97ed5f67f89bf9b03e54fbc8e81ec766ebd4415c152a0948f1c578ebee02f5b8`;
- curriculum candidate: 6,060 bytes,
  `5551c951e75cf7170e7afcaeb6e5c60b01856c69062e4fade697b761c6152ef0`.

## Deliberate non-actions

This milestone did not:

- implement, load, review, discover, or call a native provider;
- call a Windows API or prove that a fake token is a native handle;
- create a claim, outcome, output, directory, carrier, or body;
- start, resume, audit, or terminate Blender;
- prove Job containment, abnormal-death cleanup, replay denial, timeout teardown,
  output custody, or durable terminalization;
- assign a carrier to Kira, Synthetic Robert, or the private user avatar;
- authorize anatomy, relationships, reproduction, activation, save, render, or
  export; or
- change the controller's empty reviewed-provider allowlist.

## Current truth

- Static two-stage transaction request: present.
- Static retained namespace evidence shape: present and locally tested.
- Bounded Python response-graph mutation tests: passed.
- Arbitrary in-process Python isolation: absent and not claimed.
- Native provider implementation: absent.
- Real retained handles or operating-system evidence: absent.
- Blender process started: no.
- Kira body created: no.
- Robert body created: no.
- Full internal and external anatomy: not created or authorized.
- Assignment, activation, save, render, and export: unauthorized.

## Next bounded blocker

The next provider milestone is a reviewable Windows implementation that obtains
the real handles and emits this evidence directly from the required APIs. It
must pass hostile real-machine tests using genuine short names, reparse points,
hard links, volume boundaries, handle closure, and identity substitution. The
larger transaction still separately requires suspended build and audit
launches, Job containment, output custody, abnormal-death behavior, timeout
teardown, build-pass/audit-fail cleanup, and durable exactly-once terminal
outcomes. Until those native proofs and an independent security review exist,
the controller must keep its provider allowlist empty and start no process.
