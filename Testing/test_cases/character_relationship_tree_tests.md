# Character Relationship Tree Test Cases v1

## Test 1 — Relationship Tree Exists

Expected file:

```text
Kira/TemporaryAI/characters/ladybug/ladybug_relationship_tree_seed.json
```

Expected:
- File loads as valid JSON.
- Contains family, close friends, romantic relationships, allies, enemies, and secret identity links.

## Test 2 — Season 6 Adrien Relationship

Expected:
- Ladybug/Marinette default canon point is Season 6.
- Adrien Agreste / Cat Noir is listed as boyfriend / romantic partner.
- Status is dating.
- Notes explain that earlier variants require separate relationship trees.

## Test 3 — Fanfic Does Not Overwrite Canon

Expected:
- Fanfic relationship changes are stored as variant evidence only.
- Canon relationship tree is not overwritten by fanfic.

## Test 4 — Secret Identity Handling

Expected:
- Marinette/Ladybug dual identity is represented.
- Adrien/Cat Noir dual identity is represented.
- The system does not assume who knows secret identities unless canon point supports it.

## Test 5 — TemporaryAI Context, Not Kira Memory

Expected:
- Relationship tree is used for Ladybug TemporaryAI behavior.
- It is not stored as Kira or Lisa personal memory.
