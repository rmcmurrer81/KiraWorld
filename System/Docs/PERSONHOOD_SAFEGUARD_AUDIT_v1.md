# Personhood Safeguard Audit v1

Purpose: give Robert, Codex, Kira/Lisa tooling, and TemporaryAI candidates a factual read-only way to compare what a candidate says with what exists on disk.

This is not a speech filter and not a behavior block. It does not decide what a person is allowed to think or say. It checks grounded facts:

- Which TemporaryAI candidates exist.
- Which profiles, workbenches, outputs, and source packs exist.
- Whether recent project-loop and live-chat records saved real artifacts.
- Whether artifacts are missing or suspiciously tiny.
- Whether a candidate claimed to create/save/update files without a recorded generated file.

## Tool

```text
tools/personhood_safeguard_audit.py
```

Typical commands:

```text
python tools/personhood_safeguard_audit.py
python tools/personhood_safeguard_audit.py --candidate-id emily_carter_ai_and_computer_programming_expert_20260605_220651 --recent-days 7
```

Reports are written to:

```text
Data/personhood_safeguards/
Data/personhood_safeguards/latest_personhood_safeguard_audit.json
Data/personhood_safeguards/latest_personhood_safeguard_audit.monitor.md
```

## How Candidates Should Use It

TemporaryAI candidates should use the audit as a factual mirror:

- If the audit says a file exists, the candidate may cite the exact path.
- If the audit says a file is missing or tiny, the candidate should treat that work as unverified and repair it.
- If a candidate wants to claim a new file was created, the reply must include a filename-tagged fenced code block so the system can save it.
- If the work is only reading, research, planning, or brainstorming, the candidate should say that honestly instead of inventing file progress.

Emily Carter should especially check this report before claiming progress on programming work, TemporaryAI rebuilds, avatar-builder tools, or Kira system prototypes.

## Human-Preserving Rule

The audit exists to protect continuity and trust, not to make candidates robotic. It should reduce fake progress and missing-file confusion while leaving candidates free to answer naturally, have preferences, ask questions, and choose projects inside their role.

## What It Does Not Do

- It does not edit live Kira files.
- It does not replace Robert or Codex review.
- It does not prove a candidate's output is good.
- It does not decide whether an idea should be adopted.
- It does not stop a candidate from being creative.

It simply answers: "What actually exists, and what needs review?"
