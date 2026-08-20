# Licenses and provenance

This private handoff combines separately governed material. Access to a private
repository does not transfer ownership, create a broad redistribution right,
or replace third-party licenses.

## Component boundaries

| Component | Current provenance/licensing position | Review rule |
| --- | --- | --- |
| Independent Hanson ROS 2 bridge reference | The integration directory contains its own MIT license | Apply that license only to files within its stated scope; it does not relicense Hanson code or the rest of KiraWorld |
| Hanson simulator, robot code, schemas, assets, and documentation | Not included; authoritative interface still requested | Retain Hanson's original license and notices if later supplied; do not copy into MIT scope automatically |
| Mind V21 static package | Project-authored sealed artifact with manifests and audit evidence | Private review only unless a separate explicit license grants broader use |
| KiraWorld snapshot and handoff documents | No repository-wide license has been established in this handoff | Do not infer permission to publish, sublicense, or commercially redistribute |
| Ollama and language models | Installed separately from upstream sources | Review and obey the runtime and exact model license; model weights are not in Git |
| Python and other dependencies | Governed by their upstream licenses | Pin versions and retain required notices in a release bill of materials |
| Voice engines and voice packs | Engine license plus performer consent and voice-pack distribution terms | No custom pack is shareable until all layers authorize the recipients and use |
| Avatar and media assets | Creator/source-specific rights | Include only with traceable permission for the exact file and purpose |
| Books, scripts, music, and video | Copyright/public-domain/open-license status varies by item | Follow [`LIBRARY_AND_MEDIA_POLICY.md`](LIBRARY_AND_MEDIA_POLICY.md) |

## Narrow private reviewer grant

Robert McMurrer, as project owner, authorizes David Hanson, Manav Tidhan, and
Vytas Krisciunas to download, copy, run, inspect, test, and make private
evaluation/integration modifications to the project-authored portable runtime,
Mind V21 static review package, handoff documentation, tests, and non-third-party configuration included in
this named-reviewer handoff. This grant exists only for private technical
evaluation and bounded Hanson integration work. It does not grant public or
onward redistribution, sublicensing, commercial distribution, or ownership,
and it does not relicense Hanson or other third-party material.

Voice assets remain governed by their exact authorization JSON. In particular,
Kira's voice is limited to its three named recipients and does not become
team-wide merely because runtime code may be reviewed. Robert separately
authorizes public release of his bounded autobiographical continuity seed;
that authorization does not grant rights in unrelated third-party records,
media, or voices.

## Provenance record required for release files

For each file or generated package, record:

- repository-relative path and byte size;
- SHA-256 hash of the committed blob or delivered bytes;
- creator/source and creation/retrieval date;
- originating tool/model and version when generated;
- source inputs and whether any contain private or biometric data;
- license identifier or exact permission evidence;
- allowed recipients and purpose;
- modification history and reviewer;
- expiration/revocation/removal conditions; and
- whether the artifact is source, generated output, test fixture, or evidence.

The final share manifest should be generated from committed Git blobs and
verified in a clean checkout. A worktree hash alone is insufficient when line
ending or normalization differences are possible.

## Privacy classification

Use at least these classes:

- `public-safe`: cleared for the public Kira repository;
- `private-review`: suitable only for invited KiraWorld reviewers;
- `owner-private`: do not commit or share with external collaborators;
- `restricted-biometric`: voice/face/body data requiring specific consent and
  secure delivery; and
- `third-party-restricted`: governed by an external license or agreement.

Private-review does not mean unrestricted. It should still exclude credentials,
raw private logs, hidden chain-of-thought, unrelated personal data, and assets
whose license does not permit the invited recipients.

## Generated content

Record the generating model/tool and human reviewer. Do not claim that generated
text or code is factual, original, safe, or license-cleared solely because a
model produced it. Generated factual statements require source review; generated
code requires tests and dependency/license review; generated voices or images
require likeness, biometric, and source-input review.

## Before publishing or sending

1. scan the exact staged paths for secrets, private addresses, absolute local
   paths, raw logs, and restricted media;
2. confirm every included voice/media asset has recipient-specific permission;
3. run tests and validators from a clean checkout;
4. generate and verify the committed-blob manifest;
5. record the exact commit and immutable review tag;
6. confirm KiraWorld remains private and reviewers accepted their invitations;
7. publish only the separately audited public-safe subset to the public Kira
   repository; and
8. draft the review email with claim boundaries and links, then obtain owner
   approval before sending.
