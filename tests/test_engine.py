import copy
import unittest

from farm.engine import CROPS, Farm, GameError, new_state, validate_state


class EngineTests(unittest.TestCase):
    def test_initial_state_is_independent_and_valid(self):
        first, second = new_state(), new_state()
        first["tiles"][4]["tilled"] = True
        self.assertFalse(second["tiles"][4]["tilled"])
        self.assertEqual(validate_state(second), second)
        self.assertEqual(sum(tile["crop"] is not None for tile in second["tiles"]), 3)

    def test_crop_requires_soil_water_and_time(self):
        farm = Farm()
        farm.action("move", "south")
        with self.assertRaisesRegex(GameError, "till"):
            farm.action("plant", "wheat")
        farm.action("till")
        farm.action("plant", "wheat")
        for _ in range(10):
            farm.action("wait")
        self.assertEqual(farm.tile["growth"], 0)
        farm.action("water")
        self.assertEqual(farm.tile["water"], 23)
        for _ in range(CROPS["wheat"]["growth"] - 1):
            farm.action("wait")
        self.assertTrue(farm.ready())
        coins = farm.state["coins"]
        farm.action("harvest")
        self.assertEqual(farm.state["coins"], coins + 5)
        self.assertTrue(farm.tile["tilled"])
        self.assertIsNone(farm.tile["crop"])

    def test_mature_crop_does_not_wilt(self):
        farm = Farm()
        for _ in range(50):
            farm.action("wait")
        self.assertTrue(farm.ready())

    def test_edges_wrap_in_all_directions(self):
        farm = Farm()
        for direction, expected in [("west", (5, 0)), ("north", (5, 5)), ("east", (0, 5)), ("south", (0, 0))]:
            farm.action("move", direction)
            self.assertEqual(tuple(farm.state["drone"].values()), expected)

    def test_mission_reward_paid_once(self):
        farm = Farm()
        for _ in range(3):
            farm.action("harvest")
            farm.action("move", "east")
        self.assertEqual(farm.state["coins"], 55)
        self.assertEqual(farm.state["stats"]["earned"], 15)
        self.assertEqual(farm.state["completed"], ["first_harvest"])
        farm.action("wait")
        self.assertEqual(farm.state["coins"], 55)

    def test_invalid_action_does_not_advance_or_mutate(self):
        farm = Farm()
        before = farm.snapshot()
        for name, args in [("move", ["up"]), ("plant", ["wheat"]), ("till", []), ("water", [5])]:
            with self.assertRaises(GameError):
                farm.action(name, *args)
            self.assertEqual(before, farm.state)

    def test_bankruptcy_has_a_recovery_path(self):
        raw = new_state(); raw["coins"] = 0
        farm = Farm(raw)
        farm.action("move", "south"); farm.action("till"); farm.action("plant", "wheat")
        self.assertEqual(farm.state["coins"], 0)
        self.assertEqual(farm.tile["crop"], "wheat")

    def test_crop_unlock_and_insufficient_balance(self):
        farm = Farm()
        with self.assertRaises(GameError):
            farm.unlock("carrot")
        farm.state["coins"] = 100
        farm.unlock("carrot")
        self.assertEqual(farm.state["coins"], 60)
        with self.assertRaises(GameError):
            farm.unlock("carrot")
        farm.action("move", "south"); farm.action("till"); farm.action("plant", "carrot")
        self.assertEqual(farm.state["coins"], 57)

    def test_expansion_preserves_coordinate_mapping(self):
        farm = Farm(); farm.state["coins"] = 150
        farm.state["tiles"][35] = {"tilled": True, "crop": "wheat", "growth": 3, "water": 2}
        farm.state["drone"] = {"x": 5, "y": 5}
        farm.unlock("expansion")
        self.assertEqual(farm.state["size"], 8)
        self.assertEqual(len(farm.state["tiles"]), 64)
        self.assertEqual(farm.state["tiles"][45]["growth"], 3)
        self.assertFalse(farm.state["tiles"][63]["tilled"])
        self.assertEqual(farm.state["drone"], {"x": 5, "y": 5})
        self.assertEqual(validate_state(farm.state), farm.state)

    def test_saved_state_rejects_malformed_data(self):
        variants = [None, [], {}, {**new_state(), "size": 7}, {**new_state(), "coins": True},
                    {**new_state(), "coins": -1}, {**new_state(), "tiles": []},
                    {**new_state(), "unlocked": ["wheat", "potato"]},
                    {**new_state(), "unlocked": [["wheat"]]},
                    {**new_state(), "completed": ["first_harvest"]}]
        bad = new_state(); bad["tiles"][0]["growth"] = 999; variants.append(bad)
        bad = new_state(); bad["tiles"][0]["crop"] = {}; variants.append(bad)
        for value in variants:
            with self.subTest(value=value):
                with self.assertRaises(GameError):
                    validate_state(value)

    def test_validation_discards_unknown_fields_and_copies(self):
        raw = new_state(); raw["extra"] = "ignored"
        restored = validate_state(raw)
        self.assertNotIn("extra", restored)
        restored["tiles"][0]["crop"] = None
        self.assertEqual(raw["tiles"][0]["crop"], "wheat")


if __name__ == "__main__":
    unittest.main()
