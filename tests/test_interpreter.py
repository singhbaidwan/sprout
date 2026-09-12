from pathlib import Path
import time
import unittest

from farm.engine import Farm, new_state, validate_state
from farm.interpreter import MAX_ACTIONS, run_script

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class InterpreterTests(unittest.TestCase):
    def test_starter_harvests_and_replants_row(self):
        result = run_script((EXAMPLES / "starter.py").read_text())
        self.assertIsNone(result["error"])
        state = [frame["state"] for frame in result["frames"] if "state" in frame][-1]
        self.assertEqual(state["stats"]["harvested"], 3)
        self.assertEqual(state["stats"]["planted"], 6)
        self.assertEqual(state["coins"], 49)
        self.assertEqual(state["drone"], {"x": 0, "y": 0})
        self.assertEqual(result["frames"][-1]["kind"], "output")

    def test_examples_can_finish_campaign_and_buy_all_unlocks(self):
        state = new_state()
        for name in ["starter", "full_field", "smart_farmer"]:
            result = run_script((EXAMPLES / (name + ".py")).read_text(), state)
            self.assertIsNone(result["error"], result["error"])
            state = [frame["state"] for frame in result["frames"] if "state" in frame][-1]
        farm = Farm(state); farm.unlock("carrot")
        result = run_script((EXAMPLES / "carrots.py").read_text(), farm.state)
        self.assertIsNone(result["error"])
        state = [frame["state"] for frame in result["frames"] if "state" in frame][-1]
        self.assertEqual(len(state["completed"]), 4)
        farm = Farm(state); farm.unlock("sunflower"); farm.unlock("expansion")
        self.assertEqual(farm.state["unlocked"], ["wheat", "carrot", "sunflower"])
        result = run_script((EXAMPLES / "smart_farmer.py").read_text(), farm.state)
        self.assertIsNone(result["error"])
        self.assertLessEqual(result["actions"], MAX_ACTIONS)
        final = [frame["state"] for frame in result["frames"] if "state" in frame][-1]
        self.assertEqual(validate_state(final), final)

    def test_functions_loops_math_and_short_circuit(self):
        code = '''
def twice(value):
    return value * 2
total = 0
for i in range(8):
    if i == 2:
        continue
    if i == 5:
        break
    total += twice(i)
while total > 10:
    total -= 1
if total == 10 and (True or unknown_name):
    print(total, [1, 2, 3][1], min(3, 4), max([1, 5]), len(range(4)))
'''
        result = run_script(code)
        self.assertIsNone(result["error"])
        self.assertEqual(result["frames"][0]["message"], "10 2 3 5 4")

    def test_queries_do_not_advance_time(self):
        result = run_script('print(can_harvest(), get_x(), get_y(), get_size(), get_crop(), is_tilled(), get_coins(), get_water())')
        self.assertEqual(result["actions"], 0)
        self.assertIsNone(result["error"])
        self.assertEqual(result["frames"][0]["message"], "True 0 0 6 wheat True 20 0")

    def test_partial_progress_and_error_line(self):
        raw = new_state()
        result = run_script('harvest()\nmove("south")\nplant("wheat")', raw)
        self.assertEqual(result["error"]["line"], 3)
        self.assertIn("till", result["error"]["message"])
        self.assertEqual(result["actions"], 2)
        self.assertEqual(raw, new_state())
        self.assertEqual(result["frames"][0]["state"]["drone"]["y"], 0)
        self.assertEqual(result["frames"][1]["state"]["drone"]["y"], 1)

    def test_unsupported_syntax_rejected_before_any_action(self):
        for code in ['import os', 'x = (1).__class__', 'open("secret")', 'eval("1")', 'x = [i for i in range(10)]',
                     'x = 2 ** 99999999', 'move(direction="east")', 'class Foo: pass', 'x = lambda: 1']:
            with self.subTest(code=code):
                result = run_script(code)
                self.assertIsNotNone(result["error"])
                self.assertEqual(result["actions"], 0)
        result = run_script('harvest()\nimport os')
        self.assertEqual(result["actions"], 0)

    def test_infinite_loop_and_recursion_are_bounded(self):
        start = time.monotonic()
        result = run_script('while True:\n    pass')
        self.assertIn("operations", result["error"]["message"])
        result = run_script('def forever():\n    forever()\nforever()')
        self.assertIn("deeply", result["error"]["message"])
        self.assertLess(time.monotonic() - start, 2)

    def test_action_budget_preserves_exactly_400_frames(self):
        result = run_script('while True:\n    move("east")')
        self.assertEqual(result["actions"], MAX_ACTIONS)
        self.assertEqual(len(result["frames"]), MAX_ACTIONS)
        self.assertIn("400", result["error"]["message"])

    def test_values_output_and_collections_are_bounded(self):
        for code in ['x = "a" * 999999999', 'x = range(99999999)', 'x = 999999999 + 999999999',
                     'x = "%999999999s" % "a"', 'x = 1e309',
                     'x = [1] * 100\nfor i in range(5):\n    x = [x] * 100',
                     'for i in range(101):\n    print(i)']:
            with self.subTest(code=code):
                self.assertIsNotNone(run_script(code)["error"])

    def test_syntax_and_invalid_control_flow_report_errors(self):
        for code in ['for i in range(2)\n    wait()', 'break', 'return 2', 'continue',
                     'for x in []:\n    pass\nelse:\n    break',
                     'x = 1 / 0', 'move()', 'move(["east"])', 'get_x(1)', 'print = 1']:
            with self.subTest(code=code):
                self.assertIsNotNone(run_script(code)["error"])


if __name__ == "__main__":
    unittest.main()
