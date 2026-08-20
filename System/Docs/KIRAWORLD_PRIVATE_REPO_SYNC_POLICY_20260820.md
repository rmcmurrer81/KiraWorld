# KiraWorld private repository sync policy

Robert authorized the private KiraWorld repository to receive updated copies of
the approved KiraWorld files as work continues. When a mirrored file changes on
the resident Kira workspace, replace the corresponding file in
`private_delivery/source_tree/` and regenerate its inventory and checksum.

The approved scope is defined by
`tools/sync_private_kiraworld_allowlist_20260820.ps1`. Do not broaden it merely
because another file is nearby.

Always exclude:

- Codex handoffs, Codex reports, and session-transfer notes;
- unrequested non-expert person packages;
- caches, logs, temporary files, virtual environments, and dependency trees;
- resident secrets and raw private logs;
- new copyrighted or likeness/voice source media unless Robert explicitly adds
  it to the private-review scope and its status is documented.

The repository is private at the time of this authorization. A visibility or
collaborator change requires a fresh content/rights review first.
