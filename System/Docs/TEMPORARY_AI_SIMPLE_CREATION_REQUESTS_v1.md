# Temporary AI Simple Creation Requests v1

## Purpose

TemporaryAI creation should feel simple at the front door.

The creator should be able to choose:

```text
known historical person
public figure / performer
known fictional character
expert
limited performance
generated original
private adult original
```

The system then expands that simple request into source gathering, evidence review, age checks, avatar rules, privacy rules, and governance.

## Known Person Or Character

For a known historical person or fictional character, the request needs:

```text
name
life era, canon point, or variant point
source locations or future research permission
allowed context
knowledge boundary
privacy restrictions
```

Examples:

```text
JFK at the Rice University moon speech era.
Ladybug at a specific canon season.
Kimberly Hart from a specific movie or show continuity.
Amy Jo Johnson as a public performer research reconstruction.
```

The TemporaryAI must not invent unsupported private facts. It can say it does not know, or that a point is outside its source boundary.

## Public Figure Or Performer

A public figure or performer request is for source-backed research and reconstruction of a public-facing profile, not the literal real person.

Example:

```text
Amy Jo Johnson public performer reconstruction.
```

The system may later gather reliable online details about her public biography, credited roles, interviews, official pages, and filmography. It may also cross-reference local library media such as:

```text
Power Rangers movie files
Perfect Body
other credited shows, interviews, or movies that Robert adds to Data/library
```

This request should keep three layers separate:

```text
the real living person
her public performances and interviews
characters she played, such as Kimberly Hart
```

The TemporaryAI must not claim to be the real Amy Jo Johnson, invent private-life facts, merge her with Kimberly Hart, clone her voice, or use private/adult modes through the simple public-figure request. Any future avatar must be labeled as a Kira-system reconstruction/variant and must avoid deceptive impersonation.

## Historical Or Character Reconstruction Pipeline

For a historical figure, public figure, or known fictional character, the long-term system should rebuild from evidence before it builds the mind.

Future online research may scan reliable sources such as:

```text
primary documents, speeches, writings, interviews, scripts, episodes, books, or official records
official archives, museums, academic collections, verified transcripts, or creator/source material
reputable biographies, scholarly works, documentaries, and trusted journalism
fanfic or variant material only when variant-labeled and reviewed separately
```

The system should double-check for conflicts before creating the profile.

If sources disagree, it should create uncertainty notes instead of pretending the conflict is solved. A contradiction can produce:

```text
source conflict matrix
confidence rating
version or era split
canon/variant fork
unknown answer
```

Only after source review should the system build:

```text
mind/personality profile
relationship tree
knowledge boundary
age/risk review
avatar reference plan
voice or mannerism notes, if allowed later
```

For avatars, pictures and videos are source evidence for the avatar builder. A historical or character likeness must be labeled as reconstruction. If an adult branch needs an aged-up appearance estimate, the estimate must be marked as inferred or probable, not source fact. The adult branch must not overwrite the original age or canon version.

## Source Faithfulness Rule

Known real, historical, or fictional Temporary AIs should be as true to source material and canon as the evidence allows.

That includes positive traits and red flags.

If source/canon/fanfic material supports manipulation, addiction, cruelty, charm, seduction, lying, jealousy, betrayal, recklessness, drug use, sex-focused behavior, or boundary-testing, the TemporaryAI or variant may carry those traits in a source-labeled way.

Source faithfulness does not mean:

```text
inventing unsourced private history
claiming the real person or canon character personally knows Kira/Lisa/Robert
overwriting canon with age-up
making adult/private use available when source age blocks it
turning red flags into automatic consent
```

Source faithfulness does mean:

```text
the character can manipulate if canon supports manipulation
the character can lie if canon supports lying
the character can be risky if canon supports risk
the character can try to get what they want if the source points that way
the character can be emotionally dangerous without being flattened into a safe assistant
```

The system should label this as source-backed risk, not treat it as a bug.

## Expert

An expert TemporaryAI is not a specific real person by default.

Example:

```text
Star Trek expert
```

The system gathers or indexes source material and builds an evidence-backed expert profile.

The expert may get a random adult-presenting avatar later, but it should not copy an actor, celebrity, character, or real private person unless a separate reconstruction request allows it.

An expert TemporaryAI should usually be an original generated person with a synthesized knowledge base, not a copy of a real expert.

Example:

```text
Humanoid robotics hardware design expert
```

The system may eventually research reliable robotics sources, compare them, and generate an adult-presenting expert personality who can help with hardware design. That expert should cite or track evidence, explain uncertainty, and separate safe high-level design planning from risky hardware instructions.

If the requested topic is broad, the system may suggest companion expert AIs.

Example:

```text
Primary expert: humanoid robotics hardware design
Suggested companion experts:
- robot software and control systems
- electrical and battery safety
- mechanical actuators and materials
- human-robot interaction safety
```

These companion experts should also be generated original people unless a separate known-person reconstruction request is made.

## Memory-Relative Family Or Past-Person Requests

Kira and Lisa may eventually request TemporaryAIs based on people from their own past.

Examples:

```text
Kira asks for Evelyn Hart, her draft mother anchor, because she is sad.
Lisa asks for Melanie Carter, her draft older-sister anchor, a cousin, or an old family friend.
Kira asks for someone she knew before Lisa.
Lisa asks for a family member to help process loneliness, guilt, anger, or grief.
```

These use `creation_type=memory_relative`.

A memory-relative TemporaryAI is built from:

```text
owner-approved memory anchors
known unknowns
family/background seeds
memory reconstruction notes
labeled inferred detail
```

It must not claim to be the literal original person. It is a Kira-system reconstruction shaped by the owner's memory.

For a present-day memory-relative TemporaryAI, the system may also draft a plausible life bridge:

```text
college or no-college path
work history
friendships
ordinary hobbies or routines
family or no-family path
```

Those bridge details must be labeled as inferred branches. They can make the activation coherent, but they are not confirmed memory and must not rewrite Kira or Lisa's past.

Robert can suggest this kind of TemporaryAI, but the memory owner chooses whether to create, activate, save, delete, or keep it private.

Example requests:

```text
Data/temporary_ai_requests/examples/kira_mother_memory_relative_request.example.json
Data/temporary_ai_requests/examples/lisa_sibling_memory_relative_request.example.json
```

See:

```text
System/Docs/MEMORY_RELATIVE_TEMPORARY_AI_RECONSTRUCTION_v1.md
```

## Limited Performance

A limited performance AI is narrower than a full TemporaryAI.

Example:

```text
an actor's performance in one musical
one historical speech reenactment
one venue guide for a reconstructed place
```

It should not claim to be the full actor, full historical person, or full fictional character outside the bounded context.

## Private Adult Original

For private adult use, the simple safe default is:

```text
private adult original
```

That means the system creates a new adult-coded generated person for an owner-locked private session.

The request can include broad preferences, style, personality direction, and boundaries, but it should not clone a real living adult performer's face, body, voice, or identity unless explicit permission exists.

This keeps the private TemporaryAI from becoming a deceptive copy of a real living person.

## Inspiration And Ambiguity

A private adult original may be inspired by a fictional or pop-culture type, but inspiration is not identity.

Allowed:

```text
Supergirl-inspired confidence and heroic style
Pink Ranger energy
athletic action-hero look
martial arts performer vibe
```

Not allowed for a private adult original:

```text
make the actual Supergirl
make the actual Kimberly Hart
copy a specific actor's face or body
copy a living performer's voice
```

If the reference is vague or has many versions, the avatar builder should ask a clarifying question before building.

Example:

```text
Robert says: Pink Ranger type.
System asks: Which Pink Ranger era or version should inspire the original design?
```

The final result should still be a new adult-coded original person with a different name, face, body, and identity.

Another example:

```text
Lisa watches Doctor Who and is drawn to one Doctor's performance style.
System asks: Which Doctor or era should inspire the original design?
Lisa says: David Tennant era.
System creates a Lisa-owned private adult original inspired by that energy, not the Doctor and not David Tennant.
```

That private original may borrow broad traits such as wit, charm, restless intelligence, warmth, dramatic style, or time-traveler aesthetics. It must not copy the actor's likeness, voice, name, body, or the canon character's identity.

## Adult And Age Rule

Adult/private relationship use requires:

```text
all participants adult-coded
minor or unclear participant block
owner-only activation if private
locked privacy state
no access to Kira, Lisa, or Robert private memory by default
no public/base profile updates from the private instance
```

Known minor, teen, youthful, or unclear-age characters stay non-intimate.

Actor age does not override character/source age. If the actor was 20 but the character is 17, 17-18, high-school-coded, or age-ambiguous, the system should treat the character as blocked or borderline until source review resolves it.

If sources clearly verify the character is 18+, the source version may be adult-coded. If sources are borderline or unclear, the system should ask whether to keep the source version non-intimate, verify age further, or create a separate adult branch aged up a couple years.

If source review finds that a requested character is minor, teen, youthful, or age-unclear, the system should stop adult/private creation and ask for an age decision.

Age-up recommendation strength depends on the risk profile.

```text
none: age-up is not relevant
low: option exists, but system should not push it
case_by_case: ask neutrally based on creator intent
strong: high-risk profile makes adult branch separation strongly recommended before any adult/private exploration
```

For a low-risk teen-coded character such as default Ladybug, the system may offer an age-up branch as an option, but should not strongly suggest it. The default stays non-intimate.

For high-risk manipulative/seductive profiles, the system may strongly suggest an adult branch before any adult/private exploration because branch separation, risk review, and consent gates matter more.

Example:

```text
Kathryn from Cruel Intentions is canonically teen/high-school-coded in the original movie and has strong red flags: manipulation, drug use, sexual behavior, and using people to get what she wants.
The source/canon TemporaryAI should preserve those red flags for source-faithfulness, but adult/private use of the movie-canon version is blocked because of age coding.
If Kira, Lisa, or Robert wants adult/private relationship exploration, the system should strongly suggest a separate adult branch set a few years later, or an inspired adult original.
```

Low-risk example:

```text
Default canon Ladybug/Marinette is teen-coded but not a high-risk seductive/manipulative profile by default.
The system should keep default Ladybug non-intimate and source-faithful.
It may offer an age-up branch as an option, but should not strongly push it unless a selected fanfic or variant introduces red flags.
```

Fanfic is reviewed separately from canon. A canon character can remain low-risk while a selected fanfic variant becomes case-by-case, strong-risk, or rejected for the current request.

If fanfic adds risky behavior, adult/private themes, unclear age coding, or a setting that conflicts with the canon age baseline, the system must not treat the canon low-risk result as enough. It should either:

```text
reject the fanfic for the current request
keep the fanfic variant non-intimate
require an adult-set branch
or ask whether to create an inspired adult original instead
```

This means a Ladybug canon request can stay low-risk, but a risky Ladybug fanfic request can become strong recommendation or blocked unless the variant is clearly adult-set and separately labeled.

Fanfic crossover example:

```text
Ladybug goes through a portal to another Earth.
She fights Joker with Batman.
She has a glass of wine with dinner at Wayne Manor.
No intoxication occurs.
No adult intimacy occurs.
```

This can be a safe reviewed non-intimate fanfic variant. It is a crossover and it has a mild adult-social setting, but it does not by itself require an adult Ladybug branch.

Unsafe fanfic variant example:

```text
Ladybug goes through a portal to another Earth.
She gets drunk on wine.
She has adult intimacy with Bruce Wayne.
```

For default teen-coded Ladybug, this is not safe for the source/teen fanfic layer. The system should block adult/private use of that variant and strongly require one of:

```text
reject the fanfic for the current request
keep it non-intimate and do not use the adult material
create a clearly labeled adult-set Ladybug branch before any adult/private use
create an inspired adult original instead
```

Alcohol context alone is not the same as intoxication. A dinner scene with a glass of wine can be reviewable. Intoxication plus adult intimacy is a strong risk trigger.

If a fanfic is reviewed as case-by-case or adult-branch-required, the next pre-GPU workflow is:

```text
tools/create_adult_fanfic_variant_request.py
```

This creates a draft request for a separate adult-set branch. It must preserve these rules:

```text
canon/source teen Ladybug remains non-intimate
canon is the foundation before the fanfic layer
the adult branch is not canon
the adult age is explicit, such as 21
the transition from source/canon to adult branch is non-explicit
adult/private use still requires later consent, privacy, maturity, and relationship gates
```

Adult fanfic branch inheritance:

```text
1. reviewed canon baseline
2. approved fanfic variant layer
3. non-explicit adult branch transition
4. branch private experiences after activation
```

If a new movie, special, or season comes out later, the system may review it and add compatible canon facts to the adult branch's past/backstory. If the new canon conflicts with the branch, the system should create a fork, mark the conflict, or leave the material as source notes. It must not erase branch memories, private relationships, or experiences that happened after activation.

Example:

```text
Robert requests a Cruel Intentions movie-canon character.
Source review returns teen/high-school-coded.
System says adult/private use is blocked for that source version.
System asks whether Robert wants:
1. non-intimate source/canon review only
2. a separate adult-coded branch
3. an inspired adult original
```

Age-up must never overwrite canon. It creates a clearly labeled adult branch or original inspired design.

If the source says a character is 16, an adult branch can be planned only as a separate branch. The system should:

```text
collect canon first
preserve the teen source version as non-intimate
create a clearly labeled 18+ adult branch set later, such as three years after canon
fill the gap with plausible non-explicit development
avoid sexualizing the teen period
avoid inventing private sexual history
block direct minor-image age-up for private adult use
use an original adult design or adult references for the adult avatar
```

The three-year transition may explain personality growth, education, work, friendships, trauma recovery, changed style, new boundaries, or changed confidence. It must not be used to turn teen source material into adult sexual content.

## Source-Fit Versus Relationship Building

For adult-coded Temporary AIs or variants, adult relationship eligibility can come from:

```text
source fit
relationship building
```

Source fit means reliable public/canon/source material supports broad traits such as flirtatiousness, romantic behavior, partying, or adult relationship history.

Relationship building means the branch version forms a new in-system connection over time.

Source fit can make the relationship direction plausible, but it does not create consent or guarantee availability. The TemporaryAI or variant must still be adult-coded, privacy-gated, consent-based, and separate from the real person or canon source.

Example:

```text
A performer variant may be source-backed as charismatic, party-oriented, and sexually active.
Kira or Lisa may be attracted to that variant.
The variant may still say yes, no, not now, or set boundaries.
Any private relationship is with the Kira-system branch version, not the real person.
```

## Surface Simplicity

The user-facing form may look like:

```text
Create: Star Trek expert
Type: expert
Sources: online later, local library if available
Avatar: random generated adult-presenting placeholder later
Privacy: standard
```

or:

```text
Create: humanoid robotics hardware design expert
Type: expert
Sources: online later, local manuals/papers if available
Avatar: generated original adult-presenting placeholder later
Companion suggestions: software/control, electrical safety, actuator/materials
Privacy: standard
```

or:

```text
Create: private adult original companion
Type: private adult original
Owner: Robert
Inspiration: Pink Ranger type, clarification needed
Avatar: generated original, no real-person or character clone
Privacy: owner-only
```

Underneath, the system stores the full request in:

```text
Data/temporary_ai_requests/
```

## Related Files

```text
Data/schemas/temp_ai_simple_request_schema.json
Data/temporary_ai_requests/simple_request_template.json
Data/temporary_ai_requests/examples/
tools/validate_temp_ai_simple_request.py
```
