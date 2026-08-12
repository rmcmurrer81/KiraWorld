# Avatar Separate Shareable Clothing v1

Avatar clothing is an inventory of persistent physical components, not a body
texture and not geometry baked into a person. Dresses, shirts, trousers, robes,
shoes, coats, and accessories remain independent hash-bound artifacts. A body
can exist without any particular outfit, and removing an outfit must reveal the
same underlying body rather than swap to another body mesh.

## Same-size sharing

Two people may share the same physical garment only after the target wearer has
a reviewed compatibility binding. A familiar label such as `medium` is useful
for browsing but never proves fit. The binding must include:

- target body measurements inside the garment's reviewed measurement envelope;
- the same maturity lane;
- exact target body, rig, garment, adapter, and fit-evidence hashes;
- deformation and penetration review across the garment's intended motions;
- reviewed put-on and take-off transitions for that wearer;
- owner and wearer consent plus a persistent transfer record.

The garment asset hash and item identity remain unchanged. The target binding
is an adapter, not a copied garment. Inventory transfer moves the one item from
its old owner or world location to its new owner or location.

## Physical lifecycle

Every shareable garment must support stored, grasped, put-on, worn, take-off,
released, and person-to-person transfer capabilities. A timer, animation name,
or state label alone is not evidence. Existing detailed robe phases (one arm at
a time, shoulder settling, belt tying, removal, hanging/folding/placing) remain
valid garment-specific evidence and are not weakened by this general contract.

## Gate boundaries

`Core/wearable_component_contract.py` only evaluates whether an exact garment
and exact target may enter private fit review. It does not author cloth,
simulate it, transfer inventory, approve runtime use, or release the Avatar
Builder backlog. The existing positive-proof policy remains unchanged:

`Avatar/avatar_builder/policies/positive_proof_autobuild_gate_v1.json`

Current production status is fail-closed: the contract exists, but no garment
is declared to pass it by this work.
