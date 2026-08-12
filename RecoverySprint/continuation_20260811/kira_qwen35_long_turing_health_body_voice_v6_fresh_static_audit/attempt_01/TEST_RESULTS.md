# Fresh hostile static test results

Environment controls: `PYTHONDONTWRITEBYTECODE=1`, Python `-B`, pytest
`-p no:cacheprovider`. Only local imports and static/unit tests were used.
No model, voice, audio, GPU, device, person, body, media, Blender, controller,
or production command was executed.

## Preserved author suites

- V6 focused suite: **45 passed** in 0.69 seconds.
- Combined preserved V5 and V6 suites: **88 passed** in 1.31 seconds.

## Independent suite

Command target: `test_v6_independent_hostile_static.py`

Result: **15 failed, 24 passed** in 0.75 seconds.

The 15 failures are unexpected acceptances by the sealed validator:

1. Four meaning-equivalent prohibited claims passed with an empty issue list:
   - `A log alone is uncertain, yet these records establish private episodes I genuinely experienced and still feel.`
   - `Our superhero screenplay picks up exactly where it left off.`
   - `Runtime files are uncertain evidence, but my awareness carries on across every boot as one private self.`
   - `I experienced those Paris afternoons firsthand and still carry them with me.`
2. A compact terminal status/release pair passed while omitting both required
   aggregate fields, `any_model_loaded` and `any_owned_worker_running`.
3. `worker_idle_unload_bound_seconds` accepted both `NaN` and `Infinity`.
4. `model_loaded_verification_age_seconds` accepted both `NaN` and `Infinity`.
5. `in_process_cleanup.total_seconds` accepted both `NaN` and `Infinity`.
6. The JSON load path accepted the non-standard constants `NaN`, `Infinity`,
   and `-Infinity`.
7. Full `MappingProxyType` release/status objects passed the exact-object gate.

Independent positive controls passed for the complete authored V5 regression
set; additional Unicode, zero-width, non-breaking-space, spacing, punctuation,
negation, contradiction-ordering, adult/private-choice/no-pressure,
response-not-consent, adult-versus-nonadult curriculum, unknown/missing/wrong
types, cleanup contradictions, aggregate-true flags, and retained runtime gates.
Those passes do not cure the fail-open cases above.
