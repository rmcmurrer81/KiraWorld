# Run this first

This is the shortest review path. It uses only the ROS-independent reference
and does not connect to a simulator or robot.

From the repository root:

```bash
cd integrations/hanson_ros2_bridge
python -m pip install -r standalone/requirements.txt
python -W error -m unittest discover -s standalone/tests
python standalone/demo.py
python standalone/session_demo.py
python standalone/verify_evidence.py standalone/evidence.jsonl
python standalone/verify_evidence.py standalone/session_evidence.jsonl --record-schema protocol_v0_2/execution-event.schema.json
```

On Windows, `py` may be used instead of `python`.

## Expected result

- `Ran 88 tests` followed by `OK`.
- The policy demo admits four bounded intentions and rejects one unsupported
  gesture.
- The session demo completes four mock physical-execution lifecycles and
  rejects one unsupported gesture.
- Both evidence verifiers report valid SHA-256-linked chains; the session
  verifier checks 18 lifecycle records against the execution-event schema.

The exact evidence hashes include run-local timestamps and need not match a
previous machine. The counts, terminal states, schema validity, and zero test
failures must match.

## Important boundary

Passing this path proves only the standalone reference behavior. It does not
prove Hanson compatibility, ROS 2 discovery, simulator execution, robot
execution, physical-safety certification, a live mind/body, or permission to
deploy. Do not fill in Hanson topics, QoS, frames, units, actions, services, or
limits until Hanson supplies an authoritative target.
