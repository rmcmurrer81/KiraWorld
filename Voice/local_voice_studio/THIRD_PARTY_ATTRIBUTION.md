# Kokoro backend attribution and license boundary

The optional worker is an adapter; this source tree does not contain model
weights, voice packs, eSpeak data, or a Python environment.

| Component | Upstream | License stated upstream |
|---|---|---|
| Kokoro Python inference library 0.9.4 | https://github.com/hexgrad/kokoro | Apache-2.0 |
| Kokoro-82M model, `kokoro-v1_0.pth`, configuration and built-in voice packs | https://huggingface.co/hexgrad/Kokoro-82M | Apache-2.0 |
| Misaki G2P 0.9.4 | https://github.com/hexgrad/misaki | Apache-2.0 |
| eSpeak NG used through `EspeakG2P` | https://github.com/espeak-ng/espeak-ng | GPL-3.0-or-later |

The two-voice runtime policy revision is
`fbba31e67ad83eb66394c926627e99d35abeb087`. Its allowlist contains only
upstream built-ins `af_heart` and `am_fenrir`. The upstream voice table
identifies them as American-English female and male voices respectively. Kira
Labs does not claim either represents a named person, and no Kira reference
recording is used.

The product owner reported a listening review on 2026-08-25 America/New_York
and approved the perceived sound of these two built-ins for hackathon use. That
approval is not identity verification, cloning permission, or approval of any
private reference. The reported proof had ASR WER 0.0 for both samples; measured
real-time factors were 0.2466 for the first female run including its voice-pack
fetch and 0.0777 for the male run, with peak CUDA memory 766,400,512 bytes.
Those measurements describe that proof environment, not a universal quality or
performance guarantee.

A separate nine-voice technical audition catalog records source evidence at
revision `f3ff3571791e39611d31c381e3a41a3af07b4987`. That report is audition and
design provenance only. It does not make all nine voices routable, does not
change the two-voice runtime revision, and does not satisfy the missing OS
isolation gate. The other seven IDs must be rejected by this runtime release.

Before distributing a bundled runtime, preserve all upstream notices and audit
the resolved transitive dependency lock. In particular, eSpeak NG's official
repository states GPL-3.0-or-later; packaging and source-offer obligations must
be reviewed for the intended distribution model. This file is attribution, not
legal advice.
