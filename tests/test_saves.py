import copy
import unittest

from farm.engine import GameError, new_state
from farm.saves import validate_save


class SaveTests(unittest.TestCase):
    def legacy(self):
        return {"version": 1, "state": new_state(), "code": "harvest()", "speed": "2"}

    def test_legacy_migration_retains_game_and_code(self):
        old = self.legacy()
        result = validate_save(old)
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["games"]["classic"]["state"], old["state"])
        self.assertEqual(result["games"]["classic"]["code"], "harvest()")
        self.assertEqual(old["version"], 1)

    def test_round_trip_is_independent(self):
        current = validate_save(self.legacy())
        restored = validate_save(current)
        self.assertEqual(current, restored)
        restored["games"]["classic"]["state"]["coins"] = 999
        self.assertEqual(current["games"]["classic"]["state"]["coins"], 20)

    def test_bad_imports_rejected_without_mutating_input(self):
        for field, value in [("code", 4), ("code", "a" * 16001), ("speed", "100"), ("state", {})]:
            raw = self.legacy(); raw[field] = value; before = copy.deepcopy(raw)
            with self.assertRaises(GameError):
                validate_save(raw)
            self.assertEqual(raw, before)
        for raw in [None, [], {}, {"version": True}, {"version": 99},
                    {"format": "sprout-save", "version": 2, "active": "classic", "games": {} }]:
            with self.assertRaises(GameError):
                validate_save(raw)
