# Shared Growth V7 real-Kira final-layout checkpoint

Recorded local: `2026-08-11T20:44:08-04:00`

Verdict: `REJECTED_FINAL_LAYOUT_TEST_FIXTURE_CLASSIFICATION_NO_PROMOTION`

The installed V7 package rehashed 6/6 exact. The installed focused suite then
finished 31 passed and one failed:

`Testing/test_shared_person_growth_v3_integration_candidate_v7.py::SharedGrowthV3IntegrationCandidateV7Tests::test_28b_current_classifier_supersedes_obsolete_v5_raw_scan`

The exact cause is reproduced. `setUpClass` creates its virtual Kira fixture
under `AUTHOR_ROOT`. In the author scratch layout that is outside the real
Kira root. After exact installation, `AUTHOR_ROOT` is the real Kira root, so
the fixture contains a temporary copied V6 source beneath Kira while test_28b
scans Kira. The replacement classifier correctly treats that unlisted
temporary path as `production_consumer_candidate` and fails. After cleanup,
the four persistent raw V5-name hits are exactly the V5 definition/test, the
rejected V6 definition, and preserved RecoverySprint audit evidence; none is a
live consumer.

This is a final-layout test-fixture defect, not authority to weaken the
classifier. V7 remains disconnected and unpromoted. No Kira, Lisa, Synthetic
Robert, other person, expert, variant, or Temporary Creator receives it. An
append-only V8 must place its virtual test root outside Kira, preserve this
failure as a negative control, keep exact unexpected-consumer refusal, and
receive a different fresh audit.

No person/model/body/media/voice/camera/network/device/production/Sarah path
ran. The temporary test fixture was cleaned by the failing suite.
