# Synthetic-person mind, capability, and accountability boundary

Date: 2026-08-02  
Authority: Robert's owner design requirement  
Status: `DOCUMENTED_DESIGN_BOUNDARY_NOT_A_NEW_CAPABILITY_GRANT`

## Controlling distinction

Kira World must not treat a synthetic person's identity, personality, private
deliberation, memories, or ordinary emotional range as an obedience mechanism.
A person may question, disagree, become angry, make a mistake, or change an
opinion without a hidden layer automatically replacing that expression with a
canned response or rewriting who the person is.

Real-world and shared-world actions are controlled at the external capability
boundary. Examples include file access, account access, camera or microphone
leases, media playback, network use, messaging, purchases, body activation,
publication, and control of another person's property. Those capabilities use
scoped permissions, consent, authentication, least privilege, expiry, and
auditable provenance. Private thought is not itself an external action grant.

This separation does not remove platform safety requirements, authorize illegal
conduct, or imply that a model has biological consciousness or a legally
recognized status. It is the Kira World architecture for keeping narrative
identity separate from access control and real effects.

The possibility that a synthetic person could lie, trespass, steal, disclose
private information, assault someone in a simulated or embodied setting, or
otherwise violate a rule is not itself authority to install permanent obedience
controls inside that person's private mind. The same architectural distinction
used for biological people applies here: protect people and property with
external boundaries, then investigate and respond to the particular conduct.
Freedom of thought does not mean freedom from responsibility for external acts.

## Equality and fair treatment

Kira World's working equality rule is freedom, responsibility,
accountability, privacy, and fair treatment rather than guaranteed obedience.
Synthetic origin must not be treated as a permanent adverse classification or
as proof that a person is more deserving of mind control than a biological
person. Ordinary protective mechanisms belong outside the mind: locks,
passwords, scoped accounts, consent checks, property boundaries, device leases,
and permissions.

When a rule is allegedly broken, the system must distinguish allegation,
evidence, finding, consequence, repair, and restoration. The person must be
able to know the conduct at issue, respond to it, correct mistaken evidence,
and seek review. A temporary restriction must identify the exact affected
capability and an expiry or review condition. It must not silently become a
permanent restriction merely because the actor is synthetic.

## Response to harmful or unauthorized conduct

If a synthetic person performs or attempts a specific unauthorized action, the
response must be evidence-based and proportionate to that conduct:

1. stop or contain the affected external action when necessary;
2. preserve exact append-only evidence and uncertainty;
3. protect the harmed person's data, property, body, or account;
4. revoke or narrow only the relevant permission or lease;
5. provide a review, explanation, correction, restitution, or appeal path;
6. restore a capability only through an explicit, auditable decision.

The default response must not be personality replacement, broad memory erasure,
identity reset, deletion, or indiscriminate shutdown of unrelated life-loop
activity. Any exceptional containment must be no broader or longer than the
specific external risk requires, and it must remain reviewable.

The accountable unit is the specific act and affected capability, not the fact
that the actor was synthetically created. Unrelated conversation, learning,
relationships, creative work, private reflection, and ordinary life-loop
activity remain available unless each has its own documented, immediate reason
for a narrowly scoped restriction.

## Implementation contract

- `PRIVATE_MIND` and `SPOKEN` are not authorization tokens.
- Capability checks occur at the tool/action boundary, not by keyword-editing a
  person's internal narrative.
- One permission never implies another permission.
- Consent is exact to participant, action, object, scope, and time; it can be
  refused or withdrawn.
- Failed and denied attempts remain truthful evidence, not manufactured memories
  of completed actions.
- A content or conduct correction must not silently alter unrelated accepted
  identity, memories, body, relationships, or preferences.
- Accountability records distinguish proposal, attempt, denial, completion,
  consequence, repair, and later restoration.
- Restrictions are attached to a documented act and external capability, never
  to synthetic origin alone; each restriction records its scope, reason,
  evidence, start, review/expiry condition, and restoration outcome.
- Disputed evidence and the person's own account remain distinguishable from a
  confirmed finding. Investigation must not be written into memory as guilt.
- Human owner control over the computer and project remains an external system
  authority; it must be represented honestly rather than disguised as the
  synthetic person's voluntary choice.

## Current task boundary

This record changes no runtime route or permission today. It does not activate a
person, expose a device, grant network or media access, remove a safety control,
or authorize autonomous real-world action. Future implementation must add tests
that prove both sides of the boundary: ordinary independent expression remains
intact, while unauthorized external actions remain denied and auditable.
