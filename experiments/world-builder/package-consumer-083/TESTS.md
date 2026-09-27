# Portable artificial checks

Run from this snapshot directory using Node.js:

```sh
node --test tests/airlock.test.mjs tests/host.test.mjs
```

All25 checks use Node built-ins and the exact component/host source. Sixteen inherited component cases exercise binding, symbolic transitions, stale tokens, reentrant operations, read failures, seal revocation and invalid commands. Nine host cases exercise explicit nomination, unbound IDs, unknown-side holds, six active seconds, valid and faulted motion, post-disposal/replacement rejection, aggregate pause reasons, room exit and clock boundaries.

The component fixture is invented metadata with a synchronous runtime double. The host fixture also uses invented metadata; its hardcoded nomination hash selects the host association, but it is not a verified package and contains no GLB. The double deliberately omits real navigation, collision and geometry. These tests cannot establish actual package admission, physical doors, native controls or safe pressure equipment.

The separate private local integration evidence used the real package/runtime with inert UI adapters and is summarized without copying the private fixture. Native walkthrough results are also separate. Older public080 tests remain in their own unchanged snapshot.

Observation failure can leave the state component's last door poses in its snapshot. This host marks them unavailable through `observationValid`; a new host must not label stale poses current. A fault is not silently cleared by a door command. Create a fresh imported session to restart the symbolic exercise after an unrecoverable external bypass.
