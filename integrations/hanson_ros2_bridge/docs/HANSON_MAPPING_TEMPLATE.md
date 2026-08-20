# Hanson Robotics mapping template

This document intentionally leaves the Hanson side blank until official simulator and developer interfaces are available.

Use the closed [official-interface intake template](../hanson_interface_intake/official-hanson-interface-intake.template.json) and its [Draft 2020-12 JSON Schema](../hanson_interface_intake/official-hanson-interface-intake.schema.json) as the machine-readable record. The JSON template begins entirely unresolved and must be populated only from public or explicitly authorized official sources. Validate a working copy with:

```bash
python standalone/validate_hanson_intake.py path/to/completed-intake.json --require-official
```

The Markdown table below remains a compact human review view; the validated JSON intake is the source-aware handoff record.

`--require-official` can test a candidate final-status working copy before it is published: set that copy's `intake_status` to `hanson_reviewed` (or, only with matching pass evidence, `simulator_validated_for_named_versions`) and run the flag. The validator does not promote the file or change its status. Either final status activates the same strict gate automatically. Simulator validation and named-version pass evidence must agree in both directions. The validator checks structure and declared source/reference consistency; it cannot independently authenticate a source or prove an external simulator run.

| Kira bounded input | Prototype topic | Official Hanson interface | Conversion notes | Completion signal |
|---|---|---|---|---|
| Speech | `<namespace>/kira/intents/speech` | TBD | Map text, voice, and duration without exposing credentials or arbitrary resources. | TBD |
| Gaze | `<namespace>/kira/intents/gaze` | TBD | Convert allowed target frame and point into official gaze target representation. | TBD |
| Expression | `<namespace>/kira/intents/expression` | TBD | Map allowlisted semantic name and intensity to supported expression vocabulary. | TBD |
| Gesture | `<namespace>/kira/intents/gesture` | TBD | Map allowlisted semantic gesture to robot-side safe routine. | TBD |
| Status | `<namespace>/kira/execution_status` | TBD | Preserve policy admission separately from requested/accepted/started/completed/rejected/failed/cancelled/interrupted/expired execution states. | N/A |

## Mapping rules

1. Do not bypass Hanson robot-side safety or low-level control.
2. Reject an intention when no safe official mapping exists.
3. Preserve the original `intent_id` through the complete lifecycle.
4. Record the official request identifier when one is returned.
5. Keep units, coordinate frames, and time bases explicit.
6. Never infer an unsupported gesture or expression by approximating joint commands.
7. Treat emergency stop, degraded mode, and safety interruption as authoritative robot states.
8. Do not silently retry physical actions; require policy and product decisions for retry behavior.

## Information needed from Hanson Robotics

- Target ROS 2 distribution
- Official message/action/service definitions
- Topic/action names and namespaces
- Required QoS profiles
- Coordinate frames and units
- Supported expression and gesture vocabulary
- Rate and duration limits
- Cancellation and preemption semantics
- Safety-state and emergency-stop interfaces
- Simulator launch instructions and test fixtures

After those values are confirmed, follow the [official-simulator acceptance runbook](SIMULATOR_ACCEPTANCE_RUNBOOK.md). For an event demonstration, use the [simulator hackathon checklist](HACKATHON_DEMO_CHECKLIST.md).
