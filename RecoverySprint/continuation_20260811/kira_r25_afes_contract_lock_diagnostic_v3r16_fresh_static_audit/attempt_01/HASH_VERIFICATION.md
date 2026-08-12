# V3r16 exact-byte closure verification

Date: 2026-08-11

Verdict contribution: `REJECT`

The author checkpoint recorded at `2026-08-11T05:16:00Z` is the outer seal
presented to this auditor. Six checkpoint-sealed subjects differ from that
seal. A later rewrite made the inner `STATIC_SEAL_MANIFEST.json` agree with
the newer files, but the inner manifest itself no longer matches the outer
checkpoint hash and cannot retroactively replace the seal under audit.

| Subject | Checkpoint bytes | Current bytes | Checkpoint SHA-256 | Current SHA-256 | Result |
|---|---:|---:|---|---|---|
| contract JSON | 5276 | 5276 | `b28c8778a10ffae5c163ca9ee49429c532841ecb12e9230ea66564ad3ed704df` | same | MATCH |
| native source | 38271 | 38439 | `c18d6664d586cca85d551e23cb62f9e44733451519f1155615b2660ae97724c4` | `0ab71d6f8e303bb81eb787b4d52e716103d8dc632e5f8cdec426501fbb5bf789` | MISMATCH |
| identity anchor | 1338 | 1338 | `e0a8406850afe633f086e18ca938bed72f5b21ad3119b616c868478563efda23` | `d3f220cfb1745d9979d24160b77df4e20bdc0d03507b60105963880f5ce4c51d` | MISMATCH |
| native object | 48716 | 48732 | `0fce463d11a8e6b372bbf42c6ee55a852187757cb3e284c71af8cce83d2b6390` | `cc78f747ee08445be4b625f4a2affc8d10c179049e3f383d61c683da1fc2493c` | MISMATCH |
| native executable | 164864 | 164864 | `621fbf7fa635e475e6186530b9ae6d6e05e78856d679db0f07f8d555895ac76d` | `98e71cdf1817ca6b693b43a1f8f68fbf8c5c41d8451900cd2a719bcac6ddfc7f` | MISMATCH |
| author static test | 17970 | 17970 | `3227c11a38ab7b5e716b2386a014e40e0ca061bbed2fc7051ff1dce9963b9408` | same | MATCH |
| runtime-control checkpoint | 2345 | 2345 | `44a174e107baa9f119e1b8a391833d2d3fb78cfd2c15d91b7bbff6c4683d1128` | same | MATCH |
| build/static results | 2250 | 2250 | `a362925de68b08738920e258e70079168d4dabb1cc5563f25ff5fea1c2f7ba2a` | `1e6be290edb737a2467741ddecf7364427de8b767b8e19b6a8dd4e2b9d07dff3` | MISMATCH |
| static seal manifest | 5213 | 5213 | `434a2e11bb574e299136188556fafab8e5f709b05025d0a15cba1c25b3820234` | `ae32d720ebdc3cf69f2895be47c26c5040afde9e248488c193c270645c08b4a8` | MISMATCH |

All bound V3r15 predecessor subjects and the exact 6174-byte target contract
continued to match their recorded hashes. Both fixed V3r16 runtime outputs and
both audit files at the candidate's hardcoded 20260810 audit path remained
absent throughout this review.

The checkpoint itself remains 6180 bytes with SHA-256
`ce9dc906c0b41772c402c489fa0dadad43333de083795c98787015fc33f81a33`.
