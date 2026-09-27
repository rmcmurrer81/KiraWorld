# Experimental latch authoring086

This original source component replaces the old static latch artwork with one versioned shared-authoring core. It retains the structural hatch, leaf and hinge while replacing21 legacy hardware meshes with28 owned meshes: moving bolts, hollow keeper bars, supports, controls and a variable-depth gasket. Conservative per-part bounds cover all visual poses and the full hinge sweep.

The new contract is `authored_pressure_hatch_latch_geometry_v2`. Existing geometry, architectural cutout and consumer contracts continue to reject it. It has not been merged into the full World Builder, installed, exported to a new GLB package or tested in a saved-world walkthrough. Original artificial test data is included; no owner world, personal asset or private package is included.

The separate084 component previously received a native browser fixture review: the visible bolt moved from a gap through partial extension into a hollow keeper, followed the released open leaf, and showed the inner wheel/gasket. Those observations do not approve this086 assembly, final hatch artwork or pressure containment. NATIVE-FIXTURE-085.json records that limited evidence without local runtime details.

Run the portable CPU checks described in TESTS.md. The component accepts Three.js from its caller; tests use the existing repository vendor and license rather than another dependency copy. INTEGRATION.md identifies the unimplemented producer/controller/exporter/importer work.
