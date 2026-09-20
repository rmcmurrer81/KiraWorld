# Topic-relevant memory context

The ordinary per-person conversation context now selects approved summaries using an explicit subject and audience. It preserves source labels, event dates, uncertainty and forbidden inferences instead of appending unrelated recent records. It does not create memories, verify historical truth, or generate a response.

The matcher uses Unicode word normalization and a small visible set of spelling/word aliases, such as cinema/theater and movie/film. The regression case `cinema?` matches an approved summary containing `movie theater`. This is deterministic matching, not general semantic search. Explicit approved `recall_aliases` can extend an individual record.

## Ownership and audiences

- The current person's approved record remains attributed to that subject. Another person's record is not treated as a lived event of the current speaker.
- `private` permits the selected subject's approved context; `owner_visible` additionally requires the existing shareable-summary policy; `public` requires the record's explicit publication approval. A public-looking request also selects public scope. This lexical safeguard is not a complete export authorization system.
- An explicitly public record about another subject can appear as attributed knowledge, with that subject retained and an instruction not to present it as the current person's lived event.
- Existing explicitly promoted conversation records remain compatible only for their exact owner and never acquire public permission through the legacy schema.
- Private raw detail is not searched or projected. Source paths are labels and are never opened by this selector. Full uncertainty and inference restrictions are kept, or the record is omitted if it exceeds the bounded context limits.

## Corrections

Draft, rejected, inactive, deleted, superseded and duplicate-ID records are withheld. Only explicit same-subject approved correction links withdraw earlier records. A private correction may withdraw an obsolete public statement without exposing its replacement. The selector follows approved/superseded ancestry so an older account does not reappear after a second correction. It does not infer dates or rewrite source records.

The memory store is read again for each ordinary request. Existing temporal filtering remains in the ordinary context builder. The unscoped legacy `MemoryManager` API remains unchanged for compatibility; callers need the explicit scoped API to obtain these controls. The existing Robert autobiographical adapter reuses only the matcher and retains its own per-record permissions and exact role handling.

## Verification and limits

Run from a checkout with Python 3:

```sh
python Testing/test_topic_recall.py
```

The 26 tests use invented temporary records and the real MemoryManager and ordinary context builder. They cover two separate character profiles, attributed public knowledge, three audience scopes, punctuation/word aliases, correction chains, date corrections, full qualifiers, unrelated greetings, next-request reads and source-path non-dereference. The test blocks network/process calls and model imports. No private character records, workstation test receipts, biographies or handoffs are included in this update.

These are context-selection checks, not generated recall, voice quality, activation or an Avatar Creator integration. A future character-builder adapter still needs explicit subject/reference approval and provenance checks before using this contract.
