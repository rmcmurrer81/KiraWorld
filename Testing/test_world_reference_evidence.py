import copy
import unittest

from Core.world_reference_evidence import (
    WorldReferenceEvidenceError,
    validate_reference_evidence_contract,
)


def _source(source_id, kind, truth_use, *, viewpoint=None, rights="owner_supplied_private_reference"):
    result = {
        "source_id": source_id,
        "kind": kind,
        "rights_mode": rights,
        "truth_use": truth_use,
        "provenance": f"test provenance for {source_id}",
    }
    if viewpoint is not None:
        result["viewpoint_id"] = viewpoint
    return result


def _contract(*, supported=True):
    sources = [
        _source("p1", "photo", "visual_feature_observation", viewpoint="north"),
        _source("p2", "photo", "visual_feature_observation", viewpoint="south"),
        _source("p3", "photo", "visual_feature_observation", viewpoint="overhead"),
        _source("v1", "video", "visual_feature_observation", viewpoint="walkthrough"),
        _source("plan", "floor_plan", "layout_topology"),
        _source("measure", "measurement", "scale_measurement"),
    ]
    if not supported:
        sources = sources[:1]
    return {
        "contract_kind": "world_area_reference_evidence_contract",
        "schema_version": 1,
        "world_id": "test_real_place",
        "status": "reference_review_draft_not_runtime_approval",
        "coverage_policy": {
            "minimum_distinct_photo_viewpoints": 3,
            "minimum_distinct_video_viewpoints": 1,
            "layout_source_required": True,
            "scale_source_required": True,
            "unsupported_destination_portals_locked": True,
            "texture_import_requires_explicit_reuse_terms": True,
            "restricted_map_content_derivation_prohibited": True,
        },
        "areas": [
            {
                "area_id": "lobby",
                "sources": sources,
                "evidence_sufficient_for_draft": supported,
                "runtime_approved": False,
            }
        ],
        "portals": [
            {
                "portal_id": "lobby_door",
                "destination_area_id": "lobby",
                "runtime_state": "closed_locked_solid" if not supported else "closed_review_only",
                "collision_solid": True,
                "opens": False,
            }
        ],
    }


class WorldReferenceEvidenceTests(unittest.TestCase):
    def test_complete_multiview_plan_and_scale_supports_draft_only(self):
        decisions = validate_reference_evidence_contract(_contract())
        self.assertTrue(decisions[0].evidence_sufficient_for_draft)
        self.assertEqual(decisions[0].photo_viewpoints, 3)
        self.assertEqual(decisions[0].video_viewpoints, 1)

    def test_missing_evidence_requires_locked_solid_portal(self):
        decisions = validate_reference_evidence_contract(_contract(supported=False))
        self.assertFalse(decisions[0].evidence_sufficient_for_draft)
        self.assertIn("needs 2 more distinct photo viewpoint(s)", decisions[0].reasons)

    def test_missing_evidence_with_open_door_fails_closed(self):
        data = _contract(supported=False)
        data["portals"][0]["runtime_state"] = "open"
        data["portals"][0]["opens"] = True
        with self.assertRaises(WorldReferenceEvidenceError):
            validate_reference_evidence_contract(data)

    def test_duplicate_camera_angle_does_not_count_twice(self):
        data = _contract()
        data["areas"][0]["sources"][2]["viewpoint_id"] = "north"
        data["areas"][0]["evidence_sufficient_for_draft"] = False
        data["portals"][0]["runtime_state"] = "closed_locked_solid"
        decisions = validate_reference_evidence_contract(data)
        self.assertEqual(decisions[0].photo_viewpoints, 2)
        self.assertFalse(decisions[0].evidence_sufficient_for_draft)

    def test_restricted_map_tiles_cannot_support_geometry(self):
        data = _contract()
        data["areas"][0]["sources"][0]["rights_mode"] = "restricted_service_visualization_only"
        with self.assertRaises(WorldReferenceEvidenceError):
            validate_reference_evidence_contract(data)

    def test_reference_only_photo_cannot_be_imported_as_texture(self):
        data = _contract()
        source = data["areas"][0]["sources"][0]
        source["rights_mode"] = "reference_only_no_asset_reuse"
        source["truth_use"] = "runtime_asset"
        with self.assertRaises(WorldReferenceEvidenceError):
            validate_reference_evidence_contract(data)

    def test_contract_cannot_claim_runtime_approval(self):
        data = copy.deepcopy(_contract())
        data["areas"][0]["runtime_approved"] = True
        with self.assertRaises(WorldReferenceEvidenceError):
            validate_reference_evidence_contract(data)

    def test_reference_coverage_alone_cannot_open_supported_door(self):
        data = _contract()
        data["portals"][0]["opens"] = True
        data["portals"][0]["collision_solid"] = False
        with self.assertRaises(WorldReferenceEvidenceError):
            validate_reference_evidence_contract(data)

    def test_contract_cannot_lower_multiview_minimums(self):
        data = _contract()
        data["coverage_policy"]["minimum_distinct_photo_viewpoints"] = 1
        with self.assertRaises(WorldReferenceEvidenceError):
            validate_reference_evidence_contract(data)


if __name__ == "__main__":
    unittest.main()
