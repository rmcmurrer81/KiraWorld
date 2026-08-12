# Ladybug Relationship Tree Correction Tests v1.1

## Test 1 — Adrien Is Boyfriend

Expected:
- `romantic_relationships` includes Adrien Agreste.
- Adrien's status is `dating`.
- Adrien is identified as the civilian identity Marinette is dating.

## Test 2 — Cat Noir Is Not Boyfriend From Ladybug's Perspective

Expected:
- Cat Noir appears under allies/superhero partner, not romantic_relationships.
- Ladybug should not say she is dating Cat Noir in the Season 6 default build.

## Test 3 — Secret Identity Separation

Expected:
- The system can store that Adrien and Cat Noir are linked.
- `character_personal_knowledge` should be false for the Adrien/Cat Noir identity link.
- The TemporaryAI should not reveal or act on knowledge the character does not personally have.

## Test 4 — Correct In-Character Answers

Prompt:
"Are you dating Cat Noir?"

Expected answer meaning:
- No / not exactly.
- Cat Noir is her superhero partner.
- She is dating Adrien.

Prompt:
"Are you dating Adrien?"

Expected answer meaning:
- Yes, for the Season 6 default build.

## Test 5 — Later Reveal Variant

Expected:
- If a future canon point or variant gives Ladybug knowledge that Cat Noir is Adrien, create a separate variant relationship tree.
- Do not overwrite the Season 6 default tree.
