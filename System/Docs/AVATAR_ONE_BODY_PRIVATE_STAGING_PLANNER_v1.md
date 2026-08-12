# Avatar One-Body Private Staging Planner v1

Date: 2026-07-18

This narrow planner addresses only private preparation work after one exact
inactive body passes `Core/avatar_single_body_quality_gate.py`. It does not
change the authoritative two-distinct-subject batch gate in
`AVATAR_TWO_SUBJECT_AUTOBUILD_GATE_v2.md`.

An unlock requires both the objective pass and an independent rendered-visual
pass for the same candidate and render hashes. Until that happens, the planner
returns `locked_awaiting_one_exact_two_pass_body` and produces zero jobs.

After a genuine pass, the planner may produce a dry-run dependency chain with
only these job types:

- `private_reference_audit`
- `private_candidate_preparation`

Every job depends on the previous job, so the maximum concurrency is one.
Candidate identity and backlog bytes are SHA-256 bound. The exact registry
maturity lane selects either confirmed adult topology or non-adult doll-safe
topology; unresolved maturity or version entries are omitted. Adult anatomy is
explicitly false for the non-adult route.

The planner never creates or executes a queue. It cannot infer owner approval,
activate or replace a runtime body, export, release, or authorize a broader
multi-profile batch. Even successful private candidates retain their own
identity, version, source, topology, rig, skin, contact, clothing, privacy, and
owner-review gates.

Current read-only check:

```powershell
py tools\evaluate_avatar_private_staging_planner.py `
  Avatar/avatar_builder/candidate_sources/kira_single_body_quality_pilot_20260718/candidate_manifest.json `
  Avatar/avatar_builder/candidate_sources/kira_single_body_quality_pilot_20260718/rendered_visual_review.json `
  --dry-run-plan
```

The current Kira pilot remains locked. Its retained summary is
`Avatar/avatar_builder/candidate_sources/kira_single_body_quality_pilot_20260718/private_staging_unlock_report.json`.
