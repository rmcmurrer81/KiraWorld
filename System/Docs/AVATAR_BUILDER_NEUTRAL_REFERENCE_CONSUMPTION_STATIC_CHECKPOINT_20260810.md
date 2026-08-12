# Avatar Builder neutral-reference consumption static checkpoint — 2026-08-10

Status: `STATIC_ROLE_BINDING_ONLY_NO_BODY_AUTHORING_OR_DELETION_AUTHORITY`

The neutral generated/open-medical library now has an explicit Avatar Builder
role contract rather than only a folder and manifest. It maps each of the 15
stored assets exactly once to a bounded role: regional skin/material, face
features, detachable hair, chest silhouette, hands/feet/nails, adult-female
and adult-male head/body proportions, pose/contact review, and female/male
medical-structure reference lanes.

The contract does not choose maturity. It requires an external durable person
profile to select an adult-female, adult-male, or doll-safe lane. Generated
charts remain selectors rather than medical or identity evidence; medical
diagrams remain general structure rather than identity or function evidence.
Hair remains detachable and disabled for current 32 GB runtime instantiation.

No Blender execution, mesh/material mutation, body acceptance, activation,
assignment, publication, or old-photo deletion is authorized. Downstream use
still requires exact selected hashes, actual candidate change evidence,
required renders and movement/contact tests, and Robert's visual decision.

Verification command:

`py -m unittest Testing.test_avatar_builder_neutral_reference_consumption_contract_v1 -v`

Result: `5/5 PASS`.

Exact implementation inventory:

- role contract: 3,906 bytes, SHA-256
  `46cc7f09048183ab811282698b8f552e3f0f3e615991cd8e0ec876bfc8abab31`;
- focused test: 4,486 bytes, SHA-256
  `a23d3a6f64a59c41d935f14768aec5fbeaa37331c269fd2e946be702801a2a01`;
- bound neutral-reference manifest: 13,710 bytes, SHA-256
  `61a9912eade5d26766509318258640f532c98c9a370543f022bbb8f97f215ad2`.
