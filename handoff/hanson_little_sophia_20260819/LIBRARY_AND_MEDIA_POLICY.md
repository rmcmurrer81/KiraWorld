# Library and media policy

The Kira World library is intended to give residents reading, listening, and
viewing choices during life loops. This handoff does not distribute the owner's
private media library. A private GitHub repository is not a substitute for
copyright permission or a licensed streaming service.

## Material that may be shared

- user-authored material when the user owns the rights and approves the named
  recipients and purpose;
- public-domain works after their status is verified for the relevant
  jurisdiction;
- openly licensed books, articles, scripts, audio, and video when attribution,
  share-alike, noncommercial, and redistribution terms are satisfied;
- third-party material accompanied by a license that permits repository-based
  distribution to the review group; and
- metadata/catalog entries and lawful links to material hosted by its rights
  holder.

Every shared item should have title, creator, source URL or provenance,
license/public-domain basis, retrieval date, file hash, and any attribution or
use restriction.

## Material excluded from the library/media area

- commercial movie and television scripts without redistribution permission;
- copyrighted books, magazines, music, movies, episodes, clips, subtitles, or
  scans without an applicable license;
- files copied from Hulu, Netflix, or another subscription/streaming service;
- DRM-circumvention output;
- private voice-reference clips or biometric recordings, except a separately
  authorized and hash-bound voice pack governed by the voice-pack policy;
- media containing private conversations or unrelated personal data; and
- the fan-fiction book the owner identified as a test and explicitly excluded.

The fact that a resident may later access a title through an authorized user
account does not permit copying that title into Git or training data.

## Recommended repository structure

Store only rights-cleared small artifacts or metadata in the review repository:

```text
library/
  catalog.json
  licenses/
  public_domain/
  open_license/
  user_authored/
```

Large licensed assets should use an access-controlled media store rather than
normal Git history. The catalog can point to that store and record access
requirements without embedding credentials.

## Resident use and memory

- Present title, creator, and license/source to the resident.
- Treat fictional content as fiction; do not promote story details to factual
  truth records.
- Keep notes, reactions, and quotations within applicable copyright and privacy
  limits.
- Record progress and personal reflections in the resident's private continuity
  store, not in a shared public catalog.
- Do not use library access to bypass normal content, privacy, or embodiment
  policy.
- Allow a resident or owner to stop playback and remove a title from future
  suggestions.

## Streaming roadmap

Future co-viewing can integrate a licensed service through its supported
application/API and the user's authorized account, subject to service terms,
device limits, regional availability, and privacy controls. This handoff does
not claim an existing Hulu or Netflix integration, does not store service
credentials, and does not redistribute streams.

## Intake checklist

Before adding an item, confirm:

1. the exact edition/file and its hash;
2. the rights holder and license evidence;
3. the allowed recipients, uses, and redistribution channel;
4. required attribution and notices;
5. whether derivatives, model training, quotation, or public performance are
   permitted;
6. whether personal data, biometric data, or secrets are present;
7. malware/file-format scanning; and
8. a removal/expiry process.
