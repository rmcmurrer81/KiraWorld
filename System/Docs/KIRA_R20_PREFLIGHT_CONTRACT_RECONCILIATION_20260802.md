# Kira R20 preflight-contract reconciliation

Date: 2026-08-02  
Status: `ATTEMPT03_FAILED_CLOSED_WHOLE_READ_ONLY_DIAGNOSTIC_PREPARED_NOT_RUN`

R20 `preflight_attempt_03` preserved the source and stopped before mutation or
Blend save with an apparent 0.12830215951281168 m licensed-interface mismatch.
The mismatch is an ordering defect in historical evidence, not yet evidence of a
displaced seam.

The exact interface probe's `boundary_loops()` function collects each connected
boundary component using breadth-first traversal. It does not walk adjacent edges
around the cycle. The resulting BFS visit list was nevertheless written under the
field name `ordered_boundary_cycles_world_m`. R20 canonicalized that list as if it
were a real edge cycle and compared it index-by-index with the actual sealed R19
topological cycle.

The interface evidence remains valid as an exact coordinate-set source:

- 34 boundary coordinates;
- 34 full-precision adult-to-base correspondence records;
- exactly zero recorded adult/base distance for every record;
- the rounded BFS rows and full-precision correspondence rows describe the same
  coordinate set within `1e-8 m`.

The principled correction, if the live read-only diagnostic confirms it, is to:

1. derive the seam cycle from the exact selected/unselected edges in sealed R19;
2. transform R19 local coordinates through the exact `body.matrix_world` into
   world meters;
3. retain the existing deterministic start/direction rule on that real cycle;
4. require a bijective one-to-one match with the 34 full-precision licensed
   `base_world` coordinates within `1e-8 m`;
5. never use the source record order as cycle adjacency.

The historical plan and interface evidence remain unchanged. Attempt04 is not yet
prepared.

One bounded read-only Blender diagnostic is prepared at:

`tools/blender_diagnose_kira_r20_preflight_contract.py`

It contains no Blend-save or body-mutation operation. In one source opening it
collects the coordinate frame, unit settings, set pairing, all mask and bounds
checks, preserved-primary hashes/counts/attributes, every exterior-ring and
normal record, every seam UV sample and crossing, every seam weight and
normalization result, the pure patch contract, and all frozen global digests. It
also preserves the historical sequential failure as an expected diagnostic item.

The exact parent-review command and rollback are in:

`RecoverySprint/continuation_20260802/kira_r20_preflight_contract_reconciliation_prepared`

No body authoring, pose suite, render, activation, assignment, export,
publication, upload, or GPU work is authorized by this diagnostic preparation.
