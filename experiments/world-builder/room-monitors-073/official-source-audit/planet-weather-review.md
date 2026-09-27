# Mars planet and weather review — exact World 073

Checked September 26, 2026, against direct NASA, NASA/JPL and ESA pages. **No numeric correction is required in the inspected 073 planet/reference and archived-weather data.** The real exported GLB preserves the same data and separates it from the fictional habitat workboards. This finding is limited to frozen 073 and its completed export; it does not certify installed 056, new consumers, physical simulations or visual quality.

## Planet references

| Existing value | Verdict |
| --- | --- |
| Mean surface gravity 3.73 m/s² | Matches the cited NASA sheet's mean-gravity quantity. |
| Solar day 24.6597 Earth hours | Correct solar-day value; about 24 h 39 m 35 s. |
| Year approximately 687 Earth days | Correct rounded value; these are Earth days, not sols. |
| Atmosphere approximately 95.1% CO₂ by volume | Matches the cited NASA reference. |
| Pressure 636 Pa at mean radius | Correct conversion of 6.36 mbar; a reference, not a local sensor. |

The first four rows appear on the planet screen; pressure remains in the reference dataset. NASA distinguishes mean gravity from effective acceleration and solar-day length from sidereal rotation. Keep those labels. The pressure note correctly allows seasonal and elevation differences. [NASA Mars Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html), [NASA parameter definitions](https://nssdc.gsfc.nasa.gov/planetary/factsheet/fact_notes.html), [NASA Mars Facts](https://science.nasa.gov/mars/facts/).

ESA's quick-look page lists 3.711 m/s², 95.32% CO₂, 6.35 mbar and a rounded 24 h 37 min day. These are not an instruction to replace or average the explicitly sourced NASA quantities. In particular, that rounded day must not be silently substituted for the labelled solar-day value. NASA itself notes that research reference values are not one universally agreed set. “NASA reference” is appropriate; “NASA certified habitat” would not be. [ESA Mars facts](https://www.esa.int/content/view/full/200994), [NASA reference notes](https://nssdc.gsfc.nasa.gov/planetary/factsheet/fact_notes.html).

## Archived weather

The weather screen correctly identifies **Jezero, Perseverance/MEDA, April 3–4, 2021, sols 43–44**, with −22°C high, −83°C low and approximately 10 m/s gusts. Its NOT LIVE label and footer are appropriate. The same JPL article separately reports 718 Pa from the first MEDA activation on February 19, 2021. Source metadata keeps that pressure separate rather than attaching it to the April temperature report. The article was published April 6; that is not the observation date. No exact UTC timestamp, sustained-wind value, sensor height or fictional-base forecast should be inferred. [NASA/JPL first Jezero weather report](https://www.jpl.nasa.gov/news/nasas-first-weather-report-from-jezero-crater-on-mars/).

## Maps, scenery and room status

`room_dressing_render.mjs` draws the operations map from the generated room dimensions and labels it as a room plan, not a terrain survey. Its operations console does not construct a scientific globe or georeferenced Martian map. The exterior is original procedural regolith, rocks, ridges and sky. Its GLB nodes preserve `measured_terrain:false` and `live_weather:false`; the greenhouse sky also states `physical_sky:false`.

NASA supports broadly dusty, rocky surfaces with varied brown, gold and tan colors; it does not validate this invented site or the chosen shader colors. Sky color also varies with dust and viewing conditions, including characteristic blue sunset light. A warm artistic horizon is not a measured sky or a physical lighting simulation. [NASA Mars surface description](https://science.nasa.gov/mars/facts/), [NASA Mastcam-Z sunset explanation](https://science.nasa.gov/resource/mastcam-zs-first-martian-sunset/).

The EVA, habitat and laboratory boards retain a visible STATIC HABITAT SCENARIO badge. Their equipment IDs, percentages, water inventory, comfort targets and sample queues are original examples. Scene and material metadata explicitly mark them as unmeasured, non-NASA, non-operational and without sensor updates. No scientific source is invented for these authored values. Greenhouse and airlock science concepts are being reviewed separately by root.

The exported airlock panel is an initial CLOSED snapshot with pressure/leak testing unavailable. A future interactive consumer must update the panel from its own door controller or identify it as frozen. An exported texture must not become a false live-pressure or safety indicator.

## Exact package evidence and remaining limits

The existing `scene.glb` SHA is `06244f334b253010833631993c3009620d957a9caed5b6dc6e2c794d4f12b59f`. The audit parsed its JSON chunk directly, without a renderer. Its full Mars reference object equals the current pure-data module. Five source-generated planet/weather/scenario records equal the corresponding scene extras, and all six monitor records equal their material extras. The package manifest's file digests were checked; files remained unchanged.

No obsolete fictional-weather values or misleading current-weather record were found in the inspected helpers, current preview metadata and actual package metadata. The legacy contract name `fictional_mars_display_snapshot_v1` remains, but its content is explicitly REFERENCE / ARCHIVE. That identifier alone does not turn the documented observations into invented weather. Old historical artifacts were not changed or reapproved.

The sanitized `claim-ledger.json` contains 17 claims, repository-relative source references, GLB JSON pointers, artifact hashes, six official URLs, dates and confidence limits. The referenced GLB and private source fixtures are not included. Local inspection and source-import receipts remain private; public hash metadata is evidence of their exact identity, not a self-contained reproduction of the checks. No frozen source, package, owner world or canonical file was changed. No render, export, server, model or Git operation was performed. Embedded texture readability, headset presentation and scientific simulation behavior remain untested here.
