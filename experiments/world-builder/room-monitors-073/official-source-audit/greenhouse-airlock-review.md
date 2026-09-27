# Greenhouse and airlock official-source audit

Checked September 26, 2026 (local date). Scope: frozen experimental World073 source and its existing metadata contract. This is a factual/design review, not engineering certification, headset validation or an installation change. Preserve the frozen source and owner worlds.

## Greenhouse

[NASA's 2017 greenhouse research](https://www.nasa.gov/science-research/lunar-martian-greenhouses-designed-to-mimic-those-on-earth/) describes experimental recirculating nutrient water and plant-based life-support concepts. It discusses protective burial and artificial or conveyed sunlight. It does not validate this preview's exposed transparent roof, dimensions, crop yields or shielding. The article's publication date is April 24, 2017; a later website update is not a new experiment.

[NASA's plant hardware overview](https://science.nasa.gov/biological-physical/focus-areas/plant-biology/hardware/) supports monitoring air, temperature, humidity, water, carbon dioxide and light as relevant plant-research variables. It does not supply the preview's numerical settings or species-specific care instructions.

The exact greenhouse scenario uses 21.2 C, 58% relative humidity, 1,000 ppm CO2, 74% water inventory and a 16-hour photoperiod. The light display is the authored expression `round(180 + 320 * (1 - shade / 100))`, in illustrative micromoles per square metre per second. Bed species, planting days and stages are authored story data. They must retain their visible scenario label and must not be described as measured Mars values, NASA recommendations, a crop-growth forecast or a thermal/solar simulation.

The source already declares no live sensors, no agronomy recommendation, no growth/fluid simulation, and no validated radiation protection. Louver movement and numeric display updates are implemented; physically measured daylight attenuation is not. Clarify the earlier research phrase about varying incoming daylight accordingly. No numeric correction is warranted for values explicitly presented as fictional scenario data.

## Airlock

[NASA's spacecraft architecture guidance, section 8.4](https://www.nasa.gov/reference/8-0-architecture-vol-2/) distinguishes hatch closure from latching. It addresses operation from both sides, separate unlatching actions, manual equalization, opposite-side visibility, differential-pressure indication and unobstructed passage.

World073 has authored gasket-seat and latch-part geometry, opening motion, collisions and paired-door restrictions. Its latch parts are static and retracted; it has no pressure calculation, equalization control, functional latching, hatch inspection window or differential gauge. These are implementation gaps. Do not call the assembly sealed, pressure-safe, NASA-compliant or an operational pressure-cycle simulation. A geometric closed state alone proves none of those properties. Future interactive sequences should expose the missing states and mechanisms while retaining explicit fictional-simulation provenance.

[NASA's Quest description](https://www.nasa.gov/international-space-station/quest-airlock/) separates equipment servicing from crew egress. That supports the preview's functional separation, not a claim to reproduce Quest or an approved Mars layout.

[NASA's 2023 EVA-access study](https://ntrs.nasa.gov/citations/20230002484) compares different lunar access arrangements and pressure-cycling approaches. Its design cases are not universal Mars-base requirements. Do not import a study pressure as an established Mars habitat operating standard.

The older World072 research note mentions an illustrative pressure reading; the inspected current workboard instead reports pressure unavailable. The implementation is the authority for its present behavior. Keep the historical note intact, with this correction attached.

## Evidence and continuation rule

Inspected `candidate/tools/world_builder_engine/greenhouse.mjs`, `pressure_hatch.mjs` and the mirrored export source in frozen World073. `SOURCE-INVENTORY.json` identifies the exact reviewed source bytes; the unfinished greenhouse claim ledger is deliberately excluded from this snapshot. The separate planet/weather ledger checks the already-created portable package as well as the source.

For future Mars facts, record an official primary URL, units, definition, observation date/location/instrument where relevant, and a last-checked date. Keep planet reference values, dated observations, authored base scenarios and inferred future engineering visibly distinct. Film/TV references may guide art direction but must not establish scientific facts. No invented live telemetry or NASA endorsement.
