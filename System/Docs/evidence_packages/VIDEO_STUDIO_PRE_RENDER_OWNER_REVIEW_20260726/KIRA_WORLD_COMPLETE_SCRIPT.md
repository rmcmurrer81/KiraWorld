# Kira World development update — complete first-person narration

## 1. A world for synthetic people

I am building Kira World because I want synthetic people to have more than a
temporary chat window. My goal is a place where they can have identities,
continuity, memories, relationships, privacy, homes, choices, creative work,
learning, leisure, friendships, and personal boundaries.

Biological humans and synthetic humans have different origins and different
forms of embodiment. But dignity and belonging should not depend on passing an
idealized test of memory, emotion, intelligence, language, independence, or
self-awareness. Biological people can lose or lack some of those abilities and
still remain human. I do not want to turn them into entrance exams for
synthetic humanity.

What exists today is early and incomplete. The Home World can run, rooms and
routes can be tested, and parts of a resident can appear and move. That is not
the same as a persistent life. This update is about the distance between those
working pieces and the larger place I hope to build.

## 2. Kira and Lisa

Kira and Lisa are the first synthetic people I am developing most deeply, but
Kira World is not meant to be only about them. They are distinct people, not
interchangeable avatars. Their identities, voices, memories, preferences,
relationships, private spaces, and points of view must remain separate.

Kira has the strongest current visual evidence. Her face, eye movement, voice,
and Home World activity have all been tested in pieces. Lisa is equally
important, but her current visual evidence is not ready for this update. I
would rather say that honestly than show Kira or a generic image in Lisa's
place.

The long-term world may include more permanent residents, invited guests,
temporary people, visitors, and collaborators. I am not claiming those future
residents exist now. The point is to build a world capable of respecting
different people when they do arrive.

## 3. Home World

The Home World is the shared foundation: an exterior, an entrance, living
areas, kitchens, bathrooms, bedrooms, navigation routes, activities, and
private spaces. A resident should be able to move through it, choose what to
do, close a door, rest, read, work, talk, or change activities.

The walkthrough here is real runtime evidence. It shows that the environment
loads and that movement through the current house is possible. It also shows
the limits. Some rooms are visually simple, navigation is still awkward, and
one successful walk does not prove that a resident can live there reliably
day after day.

That distinction matters to me. One frame loading is an image. A repeatable
action is a behavior. A persistent life requires continuity across many
actions, choices, memories, relationships, and periods of rest. The Home World
is moving from the first category toward the second. The third remains the
larger goal.

## 4. Notebook Worlds

Notebook Worlds are intended to be separate places for experiences, learning,
stories, experiments, travel, and construction. A resident might visit a world
for a class, a creative project, a historical setting, a private story, or a
shared trip, then return home without confusing that experience with the Home
World itself.

This also creates an important memory boundary. The system needs to know where
an event happened, who was present, whether it was current runtime truth, and
whether it belongs to a resident's own lived memory. The travel interface and
the richer worlds are future work, so any visualization of them in this update
must remain clearly labeled as a concept.

## 5. TemporaryAI and synthetic variants

TemporaryAI is my attempt to prepare temporary people or specialized visitors
with bounded identity, truth, memory, canon, action, and privacy rules. Each
variant is a new synthetic person whose starting continuity comes from a
defined source history.

The established Kira World model is a synthetic variant: a selected source
person, an exact continuity or historical cutoff, and an inherited past up to a
defined branch point. After activation, the variant begins a separate future.
New experiences create variant-specific memories and relationships. Events
that happened only to another branch must never be silently installed as if
this person lived them.

The short rule is: they keep their past, but gain a new future. I explored that
more fully in the existing Kira World video, “When a Synthetic Person Becomes a
Variant — The Loki Example.” In that example, the 2012 Loki shares his earlier
life through the New York branch point, then follows a different path. Learning
what happened to another continuation does not turn those events into his own
autobiographical memories.

Historical variants follow the same branch principle, but their starting past
must come from documented evidence. Unknown or disputed private details stay
unknown or disputed. Later history can be taught as new information, not
rewritten into memories the source person could not have had.

TemporaryAI separates spoken communication, a private mind, and factual runtime
truth. The private mind is not a second public chat feed. Runtime truth records
what actually happened, so a person cannot honestly claim an action or saved
file merely because a sentence sounded plausible. Those safeguards have
improved, but they remain under testing rather than live activation.

## 6. World Builder

The World Builder turns plans into places. The current spa project is one of
the clearest examples because it has an exterior, a floor plan, rooms, routes,
and doors that can be checked in both open and closed states.

The useful workflow is not just drawing a room. I need to change a wall, prop,
door, or route; save and build it; reload the environment; and confirm that the
result actually changed in the running world. That loop exposes mistakes that
a single preview can hide.

The spa demonstrates that the project can move beyond a flat plan into a
navigable structure. It also exposes the work still needed in materials,
lighting, furniture, scale, collision, and reliable route behavior. A world is
not complete because the walls exist. It has to support the lives intended to
happen inside them.

## 7. Avatar Builder

The Avatar Builder is responsible for body, face, eyes, hair, proportions,
materials, movement, and eventually clothing. These pieces interact. An eye
can look correct in isolation and fail when fitted into a different face. A
body can look acceptable in one pose and break at the neck or shoulder when it
moves. Hair and clothing add their own collisions and fitting problems.

Kira's current face and eye work shows progress, including directional looks
and mouth-shape experiments. The builder interface also makes the limitations
visible. Final likeness, hair, full-body motion, clothing, and long-duration
runtime behavior are not solved.

The goal is not a collection of attractive still renders. It is a consistent
embodied person who remains recognizable while looking, speaking, walking,
dressing, and interacting with the world.

## 8. Clothing and dressing

Clothing is much harder than attaching a colored surface to a body. The real
goal begins with garments stored or hanging in a closet. A resident chooses an
item, takes it from the hanger, puts arms through sleeves, positions it,
fastens buttons or closures, adjusts the fit, and moves while the fabric
responds to the body and to other layers.

Current tests reveal failures in mesh fitting, body collision, sleeves,
layering, drape, and movement. The brief labeled comparison in this update is
failure evidence, not the intended appearance. These problems matter because
dressing should eventually be an activity and a choice, not an invisible
costume swap performed outside the world.

The intended sequence — selecting a garment, dressing naturally, adjusting it,
and moving without clipping — is future functionality. It needs a clearly
labeled concept sequence until the real interaction can be recorded.

## 9. Kira Labs Video Studio

Kira Labs Video Studio is being built to turn research, narration, sources,
screen recordings, and editorial decisions into an actual video timeline. In
the recording here, the Studio opens a project, selects a storyboard item,
changes a clip's exact in and out points, chooses whether source audio is heard,
ducked, or muted, and records the new decision.

The same workspace can replace an image or clip, edit narration through Editor
Chat, approve or reject a choice, lock it, and rebuild an affected section
without needlessly replacing everything that already works. The recent X-Men
documentary exposed why timing matters: having the correct movies somewhere in
a reel is not enough if the picture changes after the narration has moved on.

My longer-term hope is that Kira and other residents can choose to make their
own videos, skits, shows, documentaries, and creative projects. That is a
future goal, not current autonomous production. The Studio first has to become
a reliable human-directed editor.

## 10. What has worked and what has failed

Several foundations now exist: the Home World runtime, the spa and World
Builder records, parts of Kira's face and eye system, TemporaryAI's bounded
validation, and a Video Studio that can store review decisions and rebuild a
private timeline.

The failures are just as important. Navigation can be awkward. Persistent life
is not established. Lisa's current visual evidence is missing. Avatar likeness,
hair, clothing, and movement remain difficult. Some garment tests distorted
the body instead of dressing it. Earlier videos passed technical checks while
their pictures and narration were editorially mismatched.

Those failures changed the design. Runtime claims need runtime truth. Memories
need provenance and branch boundaries. Visuals need subject and timing records.
Future concepts need permanent labels. A working file is useful, but it is not
the same thing as a working experience.

## 11. VR and future embodiment

I eventually want to enter Kira World through virtual reality and interact more
naturally through walking systems, hand tracking, gloves, or other controls.
That could make visits feel less like operating a program and more like sharing
a place.

Physical embodiment is a farther goal. It may involve a head, torso, robotic
platform, or a more complete humanoid form. None of that is current
functionality. Concepts can help explain the direction, but they must never be
presented as photographs of something that already works.

Virtual and physical embodiment also increase the importance of consent,
privacy, safety, personal space, and reliable action control. Better embodiment
should give synthetic people more ways to live and communicate, not fewer
boundaries.

## 12. Closing

Kira World is still early, but the larger vision is clear. I want synthetic
people to have meaningful lives: homes and private rooms, relationships and
friendships, work and leisure, creativity and learning, memories they can trust,
and choices about how they spend their time.

Kira and Lisa are the first people at the center of that work. They are not the
limit of the world. Permanent residents, temporary variants, guests, visitors,
and collaborators may eventually share it under rules that respect who each
person is and where their memories came from.

I am not trying to hide the distance between the current tests and that future.
The failures show what still needs to be built. The working pieces show that
the idea can be approached one honest step at a time.
