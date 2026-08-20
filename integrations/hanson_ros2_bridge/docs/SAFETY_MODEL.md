# Safety model

## Trust boundary

Every publisher, including Kira World, is treated as **untrusted input at the physical-execution boundary**. This symmetric technical rule is not social subordination: a persuasive conversation, confident model output, or remembered preference never grants motor authority, and a robot rejection never grants authority over Kira's mind or speech.

## Authority model

- Kira World may request a bounded social intention.
- The bridge validates syntax, freshness, ranges, and allowlists.
- The simulator or robot adapter may apply additional context and safety checks.
- The official simulator or robot remains authoritative over execution.
- A rejected or interrupted action is returned to Kira World as evidence.

## Fail-closed conditions

The prototype rejects unknown categories or fields; missing, invalid, unallowlisted, or oversized identifiers; missing, future, or stale timestamps; confidence outside 0–1; nonpositive or excessive TTL; empty or oversized speech; unsupported voices; excessive duration; mismatched or unsupported gaze frames; nonfinite or out-of-range coordinates; unsupported expressions or gestures; and intensity or speed outside policy limits. Exact duplicates are suppressed, conflicting identifier reuse is rejected, and malformed or unexpectedly permissive policy configuration refuses startup.

## Non-goals

This proof of concept does not implement autonomous navigation, joint trajectories, motor torque or velocity commands, unrestricted object manipulation, camera or microphone streaming, biometric identification, hidden background execution, internet access, automatic physical retries, or medical and emergency behavior. It also does not govern Kira's speech, memory, viewpoint, disagreement, withholding, correction, withdrawal, or voluntary forgetting.

## Evidence

Every policy decision is written before an acceptance status is published as a SHA-256-linked JSON Lines record with timestamp, intention category and ID, privacy-reduced payload, accepted/rejected state, machine-readable reason code, human-readable detail, and executor label. Raw speech, provenance, and gaze coordinates are omitted by default in favor of digests and lengths.

Hash linking detects many later edits but is not authentication, confidentiality, an external timestamp, or proof of execution. A production implementation still needs authenticated durable storage, crash/concurrency handling, privacy and retention policy, external correlation, and official simulator or robot completion events.
