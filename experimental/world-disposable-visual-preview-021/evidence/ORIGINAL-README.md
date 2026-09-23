# Disposable World019 visual inspection

This is an isolated copy of the existing World Builder bedding viewer using the
exact wide-frame test fixture and World019 physics source. World015 remains
installed. All 56 protected owner frame/study files matched their preservation
inventory during staging; no owner files were edited.

The viewer starts paused. **Run 12 frames** advances actual solver steps, then
pauses. The disposable view has a 120-frame total cap and a 15-second limit per
batch. Angle, Side and Top controls remain available. Paused views only redraw
after UI or resize changes. Recording and saving are disabled.

The read-only server binds only 127.0.0.1, serves the pinned asset allowlist,
rejects POST and closes after 300 seconds. It preserves a consumed-run receipt
and checks owner/input hashes at closure. Root coordinates browser graphics
with Studio model work before launching it. No server or browser was launched
by the preparing agent.

Reviewed static plan SHA256:
`6da223ec878cedd635da770097c17a9259044f3192222b90d87888e28e02337b`

Launch from the local copy with Python:

```text
python -B serve_preview.py --expected-plan-sha256 6da223ec878cedd635da770097c17a9259044f3192222b90d87888e28e02337b
```

Use the printed loopback URL. Do not overwrite a consumed run. The viewer
cannot establish settled 480-frame behavior within its initial 120-frame cap;
it is for early geometry, contact and responsiveness inspection. There is no
visual acceptance until the actual browser output has been inspected.

## Numerical context

019 passed 3,040 key cases, 20 focused domain groups, 33 tiny frames and two
opposite-order 12+12-frame full-size comparisons against017. Every observed
p/prev/v byte, history mask, primitive certificate and counter matched. Runtime
fell 18.5–19.6% in those short comparisons. The 1,110-frame continuous trajectory
belongs to017, not019. Even019 measured only about six wide solver frames per
second in the short CPU pilot; real-time full-world performance is unfinished.

020 removed allocations inside the observation helper and preserved all tested
state, but runtime rose 9.0–10.5% versus019. It remains held and uninstalled.
Its negative result is preserved separately, not silently discarded.

## Remaining installation concerns

The finite-domain helper has a scoped ownership contract: position buffers,
topology and certificate state remain public. Its checks detect selected
unobserved position changes, but arbitrary alias mutation is outside its
claimed contract. A separate ownership review is needed before promotion.

The helper suppresses only certified exterior paths through an existing
upper-surface barrier. It does not implement closed-volume side/underside
response, general continuous collision, cloth self collision, cloth-pillow
coupling or calibrated body/material behavior. Numerical contact counts do not
prove those absent capabilities or visual realism.
