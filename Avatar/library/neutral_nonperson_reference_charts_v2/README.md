# Neutral non-person reference charts v2

This private package contains ten synthetic design-selector charts and four
licensed NIH/NIDDK medical drawings. It contains no photograph of a real
person and no real-person photograph pixels.

The older external-anatomy SVG is deliberately absent because inspection found
that it embeds a base64 raster image derived from a real photograph. The
manifest records its excluded identity so it cannot be silently reintroduced.

The skin-material chart now has an exact-hash-bound map with six stable selector
IDs. Avatar Builder can apply each one deterministically to a synthetic
non-person material record while proving the body geometry hash is unchanged.
The loader decodes the PNG and verifies all 30 declared sample pixels. This is
a machine selector and material-direction pass, not a render-quality pass.

The other synthetic charts currently provide visual direction only. None of
the charts is yet an accepted replacement for the local photo library. That
requires exact before/after evidence plus visual and structural review.

No local reference photo may be deleted automatically. An exact coverage map,
successful machine-utility evidence, and owner approval are required first.

The medical drawings describe general structure. They do not prove a body,
mesh, biological function, diagnosis, identity, likeness, or runtime ability.
