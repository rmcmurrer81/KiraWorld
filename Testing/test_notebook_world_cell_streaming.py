import copy
import unittest
from pathlib import Path

from Core.notebook_world_cell_streaming import (
    CellStreamingContractError,
    load_contract,
    plan_interest,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_courtyard_20260628_210935"
    / "preview"
    / "louvre_cell_streaming_contract.json"
)


class NotebookWorldCellStreamingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract(CONTRACT_PATH)

    def test_only_the_bounded_owner_review_slice_is_runtime_loadable(self) -> None:
        loadable = [cell["id"] for cell in self.contract["cells"] if cell["runtime_loadable"]]
        self.assertEqual(
            loadable,
            [
                "cour_napoleon_exterior",
                "pyramid_entrance_transition",
                "under_pyramid_level_minus_2_circulation",
            ],
        )
        for cell in self.contract["cells"]:
            if cell["id"] not in loadable:
                self.assertIsNone(cell["bounds_m"])
                self.assertIsNone(cell["runtime_binding"])
            self.assertFalse(cell["completion"]["complete"])

    def test_owner_at_arrival_loads_only_exterior(self) -> None:
        plan = plan_interest(self.contract, [(0, 1.68, 62.0)])
        self.assertEqual(plan.desired_cells, ("cour_napoleon_exterior",))
        self.assertEqual(plan.load_cells, ("cour_napoleon_exterior",))
        self.assertEqual(plan.nearby_blocked_cells, ())

    def test_door_approach_loads_exterior_and_entrance_but_not_descent(self) -> None:
        plan = plan_interest(self.contract, [(0, 1.68, 34.0)])
        self.assertEqual(
            plan.desired_cells,
            ("cour_napoleon_exterior", "pyramid_entrance_transition"),
        )
        self.assertNotIn("under_pyramid_level_minus_2_circulation", plan.desired_cells)

    def test_threshold_loads_all_three_bounded_cells(self) -> None:
        without_authorization = plan_interest(
            self.contract,
            [(0, 1.68, 17.0)],
            currently_loaded=("cour_napoleon_exterior", "pyramid_entrance_transition"),
        )
        self.assertNotIn("under_pyramid_level_minus_2_circulation", without_authorization.desired_cells)
        plan = plan_interest(
            self.contract,
            [(0, 1.68, 17.0)],
            currently_loaded=("cour_napoleon_exterior", "pyramid_entrance_transition"),
            authorized_cells=("under_pyramid_level_minus_2_circulation",),
        )
        self.assertEqual(
            set(plan.desired_cells),
            {
                "cour_napoleon_exterior",
                "pyramid_entrance_transition",
                "under_pyramid_level_minus_2_circulation",
            },
        )
        self.assertEqual(plan.load_cells, ("under_pyramid_level_minus_2_circulation",))

    def test_far_presence_unloads_exterior_after_retain_radius(self) -> None:
        plan = plan_interest(
            self.contract,
            [(500, 1.68, 500)],
            currently_loaded=("cour_napoleon_exterior",),
        )
        self.assertEqual(plan.desired_cells, ())
        self.assertEqual(plan.unload_cells, ("cour_napoleon_exterior",))

    def test_hysteresis_retains_an_already_loaded_cell(self) -> None:
        # 17 m beyond the eastern prototype boundary: outside load radius 12,
        # but still inside retain radius 20.
        plan = plan_interest(
            self.contract,
            [(132, 1.68, 0)],
            currently_loaded=("cour_napoleon_exterior",),
        )
        self.assertEqual(plan.desired_cells, ())
        self.assertEqual(plan.retain_cells, ("cour_napoleon_exterior",))
        self.assertEqual(plan.unload_cells, ())

    def test_unbuilt_gallery_cannot_be_made_runtime_loadable(self) -> None:
        changed = copy.deepcopy(self.contract)
        gallery = next(cell for cell in changed["cells"] if cell["id"] == "denon_gallery_zone")
        gallery["runtime_loadable"] = True
        with self.assertRaises(CellStreamingContractError):
            validate_contract(changed)

    def test_bounded_prototype_cannot_be_promoted_complete(self) -> None:
        changed = copy.deepcopy(self.contract)
        entrance = next(cell for cell in changed["cells"] if cell["id"] == "pyramid_entrance_transition")
        entrance["completion"]["complete"] = True
        with self.assertRaises(CellStreamingContractError):
            validate_contract(changed)

    def test_explicit_byte_tri_texture_draw_and_latency_budgets_exist(self) -> None:
        budgets = self.contract["resource_budgets"]
        self.assertGreater(budgets["active_set"]["max_asset_bytes"], 0)
        self.assertGreater(budgets["active_set"]["max_triangles"], 0)
        self.assertGreater(budgets["active_set"]["max_texture_bytes"], 0)
        self.assertGreater(budgets["active_set"]["max_draw_calls"], 0)
        self.assertGreater(budgets["active_set"]["max_transaction_latency_ms"], 0)
        loadable = [cell["id"] for cell in self.contract["cells"] if cell["runtime_loadable"]]
        self.assertEqual(set(loadable), set(budgets["per_cell"]))

    def test_invented_bounds_on_unbuilt_gallery_fail_closed(self) -> None:
        changed = copy.deepcopy(self.contract)
        gallery = next(cell for cell in changed["cells"] if cell["id"] == "denon_gallery_zone")
        gallery["bounds_m"] = {"min": [0, 0, 0], "max": [1, 1, 1]}
        with self.assertRaises(CellStreamingContractError):
            validate_contract(changed)

    def test_promoting_elevator_truth_fails_closed(self) -> None:
        changed = copy.deepcopy(self.contract)
        changed["truth"]["elevators_proven"] = True
        with self.assertRaises(CellStreamingContractError):
            validate_contract(changed)

    def test_unknown_loaded_cell_is_rejected(self) -> None:
        with self.assertRaises(CellStreamingContractError):
            plan_interest(self.contract, [(0, 1.68, 62)], currently_loaded=("invented_gallery",))


if __name__ == "__main__":
    unittest.main()
