# Kokoro backend attribution and license boundary

The optional worker is an adapter; this source tree does not contain model
weights, voice packs, eSpeak data, or a Python environment.

| Component | Upstream | License stated upstream |
|---|---|---|
| Kokoro Python inference library 0.9.4 | https://github.com/hexgrad/kokoro | Apache-2.0 |
| Kokoro-82M model, `kokoro-v1_0.pth`, configuration and built-in voice packs | https://huggingface.co/hexgrad/Kokoro-82M | Apache-2.0 |
| Misaki G2P 0.9.4 | https://github.com/hexgrad/misaki | Apache-2.0 |
| eSpeak NG used through `EspeakG2P` | https://github.com/espeak-ng/espeak-ng | GPL-3.0-or-later |

The two-voice generic-bootstrap runtime revision is
`f3ff3571791e39611d31c381e3a41a3af07b4987`. Its allowlist contains only
upstream built-ins `af_heart` and `am_fenrir`. The upstream voice table
identifies them as American-English female and male voices respectively. Kira
Labs does not claim either represents a named person, and no Kira reference
recording is used.

The product owner reported a listening review on 2026-08-25 America/New_York
and approved the perceived sound of these two built-ins for hackathon use. That
approval is not identity verification, cloning permission, or approval of any
private reference. The hash-bound catalog audit records ASR WER 0.04 and an
intelligibility pass for each selected voice. No release-bound performance or
GPU-memory claim is made.

A separate nine-voice technical audition catalog records source evidence at the
same revision. Its exact configuration/model hashes and exact source-pack
hashes for `af_heart` and `am_fenrir` are bound to the owner decision by the
starter runtime bridge. That does not make all nine voices routable and does not
satisfy the separate OS-isolation gate. The other seven IDs must be rejected by
this runtime release. The former `fbba...` runtime label is retained only as a
superseded, unbound label in that bridge; it is not current provenance.

Before distributing a bundled runtime, preserve all upstream notices and audit
the resolved transitive dependency lock. In particular, eSpeak NG's official
repository states GPL-3.0-or-later; packaging and source-offer obligations must
be reviewed for the intended distribution model. This file is attribution, not
legal advice.
