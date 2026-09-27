# Portable CPU tests

From the root of this repository:

```sh
node --test experiments/world-builder/latch-visual-084/tests/test_latch_visual.mjs
```

The tests import the already published Three.js 0.180.0 module from the sibling `package-consumer-083/candidate/vendor/three` directory. They need no new download, browser, server, canvas, WebGL, model or private scene file. If copying only this folder, also preserve that sibling vendor source and license with its relative location.

Every hatch plan in this suite is explicitly artificial and every door observer is a synchronous double. It tests bolt/keeper alignment, four portal orientations, gasket contact, both control poses, pause aggregation, invalid identities/observations/steps, reentrant reset/disposal and resource ownership. It does not prove real package admission, actual walking collision, a visual appearance, native door operation or physical containment.
