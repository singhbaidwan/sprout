import copy
import itertools
import json
from pathlib import Path
import unittest

from farm.continuous import step_script, validate_checkpoint, MAX_CHECKPOINT
from farm.engine import GameError, new_state
from farm.factory import new_factory
from farm.interpreter import run_script
from farm.saves import validate_save
from farm.world import validate_game

EXAMPLES = Path(__file__).resolve().parent.parent / 'examples'


class ContinuousTests(unittest.TestCase):
    def steps(self, source, state=None, limit=1000):
        state = state or new_state()
        checkpoint, frames = None, []
        for revision in range(1, limit + 1):
            result = step_script(source, state, checkpoint)
            self.assertEqual(result['revision'], revision)
            self.assertLessEqual(result['actions'], 1)
            self.assertEqual(result['state']['tick'] - state['tick'], result['actions'])
            self.assertIsNone(result['error'], result['error'])
            frames.extend(result['frames'])
            state = validate_game(result['state'])
            if result['done']:
                return state, frames, None
            # Every request uses a newly decoded, portable continuation.
            checkpoint = json.loads(json.dumps(result['checkpoint']))
        return state, frames, checkpoint

    def test_continues_beyond_400_and_is_deterministic(self):
        source = 'while True:\n    move("east")\n    wait()'
        state, frames, checkpoint = self.steps(source, limit=450)
        self.assertEqual(state['tick'], 450)
        self.assertEqual(checkpoint['revision'], 450)
        one = step_script(source, state, checkpoint)
        two = step_script(source, state, copy.deepcopy(checkpoint))
        self.assertEqual(one, two)
        self.assertEqual(run_script(source)['actions'], 400)

    def test_nested_calls_loops_returns_and_expressions_match_finite(self):
        source = '''
def sample(value):
    for i in range(3):
        if i == 1:
            continue
        wait()
        if value == 7:
            return value + i
    else:
        print("loop complete", value)
    return value

def outer():
    for j in range(4):
        if j == 3:
            break
        result = [sample(j), (sample(7), range(2, 6, 2))]
        print(result, result[1][1][0])
    else:
        print("should not run")
    return sample(3)

x = outer() + sample(4)
a = b = [1, 2]
alias = sample
while x > 0:
    x -= 1
    if x == 2:
        break
    if x == 4:
        continue
    wait()
else:
    print("should not run")
print(False and sample(8), True or sample(9), 1 < sample(2) < 3, 3 < sample(1) < sample(8))
print(a is b, alias == sample, get_crop() is not None, -x, not x, x % 3)
'''
        finite = run_script(source)
        self.assertIsNone(finite['error'])
        state, frames, checkpoint = self.steps(source)
        self.assertIsNone(checkpoint)
        self.assertEqual(frames, finite['frames'])
        self.assertEqual(state, [frame['state'] for frame in frames if 'state' in frame][-1])

    def test_navigation_yields_each_tile_and_preserves_machine_clock(self):
        source = 'navigate_to("chest")\nload("wheat", 4)\nnavigate_to("mill")\nunload("wheat", 4)\nfor i in range(10):\n    wait()'
        start = new_factory()
        finite = run_script(source, start)
        state, frames, _ = self.steps(source, start)
        self.assertEqual(frames, finite['frames'])
        self.assertEqual(state['stats']['flour_milled'], 2)

    def test_every_finite_example_keeps_world_results(self):
        for path in EXAMPLES.glob('*.py'):
            if 'continuous' in path.stem:
                continue
            start = new_factory() if path.stem.startswith('factory_') else new_state()
            finite = run_script(path.read_text(), start)
            if finite['error']:
                continue  # Some examples require unlocks, options, or order eligibility.
            with self.subTest(example=path.name):
                _, frames, _ = self.steps(path.read_text(), start)
                self.assertEqual(frames, finite['frames'])

    def test_computation_print_recursion_and_language_limits(self):
        for source, part in [
            ('while True:\n    pass', '20,000 operations'),
            ('while True:\n    print("spam")', '100 messages'),
            ('def again():\n    again()\nagain()', 'nested too deeply'),
            ('import os\nwait()', 'Import'),
            ('wait.__class__', 'Attribute'),
            ('x = [0] * 1001\nwait()', 'too many items'),
            ('while True:\n    if True:\n', 'expected an indented block'),
        ]:
            with self.subTest(source=source):
                result = step_script(source, new_state())
                self.assertTrue(result['done'])
                self.assertIn(part, result['error']['message'])
                self.assertEqual(result['state']['tick'], 0)
                self.assertEqual(result['revision'], 1)

    def test_no_action_completion_and_output_reset_between_actions(self):
        result = step_script('print("done")', new_state())
        self.assertTrue(result['done'])
        self.assertEqual(result['actions'], 0)
        state, frames, cp = self.steps('while True:\n    print("tick")\n    wait()', limit=110)
        self.assertEqual(len(frames), 220)
        self.assertEqual(state['tick'], 110)
        self.assertIsNotNone(cp)

    def test_failure_keeps_last_completed_action(self):
        source = 'harvest()\nmove("diagonal")'
        first = step_script(source, new_state())
        result = step_script(source, first['state'], first['checkpoint'])
        self.assertTrue(result['done'])
        self.assertIsNotNone(result['error'])
        self.assertEqual(result['state'], first['state'])
        self.assertEqual(result['revision'], 2)
        self.assertEqual(result['actions'], 0)

    def test_checkpoint_binding_and_malformed_data(self):
        source = 'x = [1, 2]\nwhile True:\n    wait()'
        result = step_script(source, new_state())
        state, cp = result['state'], result['checkpoint']
        self.assertEqual(validate_checkpoint(source, state, cp), cp)
        for key, value in [('version', True), ('pc', -1), ('pc', True), ('line', None),
                           ('revision', -1), ('scopes', []), ('scopes', [{'__host': 1}]),
                           ('values', [{'type': 'ref', 'value': 0}]),
                           ('values', [{'type': 'object', 'value': [0, {'type': 'list', 'value': [{'type': 'ref', 'value': 0}]}]}]),
                           ('loops', [{'sequence': 9, 'index': 0}]), ('calls', [None]),
                           ('navigation', ['teleport']), ('source', 'changed'), ('world', 'changed')]:
            bad = copy.deepcopy(cp); bad[key] = value
            with self.subTest(key=key, value=value), self.assertRaises((GameError, ValueError)):
                validate_checkpoint(source, state, bad)
        with self.assertRaises(GameError):
            validate_checkpoint(source + '\nwait()', state, cp)
        changed = copy.deepcopy(state); changed['coins'] += 1
        with self.assertRaises(GameError):
            validate_checkpoint(source, changed, cp)
        bad = copy.deepcopy(cp); bad['junk'] = 'x' * MAX_CHECKPOINT
        with self.assertRaises(GameError):
            validate_checkpoint(source, state, bad)

    def test_missing_example_helper_has_actionable_error_in_both_modes(self):
        for result in (run_script('store_cargo()', new_factory()), step_script('store_cargo()', new_factory())):
            self.assertIn('helper from Harvest & store', result['error']['message'])
            self.assertIn('def store_cargo():', result['error']['message'])
            self.assertEqual(result['actions'], 0)

    def test_checkpoint_memory_limit_keeps_completed_world(self):
        source = '\n'.join(f'v{i} = str({i}) + "." * 800' for i in range(65)) + '\nwait()'
        result = step_script(source, new_state())
        self.assertTrue(result['done'])
        self.assertIn('48 KB', result['error']['message'])
        self.assertEqual(result['actions'], 1)
        self.assertEqual(result['state']['tick'], 1)
        self.assertIsNone(result['checkpoint'])

    def test_checkpoint_save_round_trip_and_old_saves(self):
        source = 'while True:\n    move("east")'
        first = step_script(source, new_state())
        save = {'format': 'sprout-save', 'version': 2, 'active': 'classic', 'games': {
            'classic': {'state': first['state'], 'code': source, 'speed': '8', 'execution': 'continuous', 'checkpoint': first['checkpoint']}}}
        restored = validate_save(json.loads(json.dumps(save)))
        self.assertEqual(restored, save)
        game = restored['games']['classic']
        resumed = step_script(game['code'], game['state'], game['checkpoint'])
        self.assertEqual(resumed['state']['drone']['x'], 2)
        game['execution'] = 'finite'
        with self.assertRaises(GameError):
            validate_save(restored)
        del game['checkpoint']; del game['execution']
        self.assertEqual(validate_save(restored), restored)

    def test_continuous_examples_sustain_all_growing_option_combinations(self):
        for factory, flags in itertools.product((False, True), itertools.product((False, True), repeat=3)):
            state = new_factory() if factory else new_state()
            state['care']['settings'] = dict(zip(('fertilizer', 'irrigation', 'soil'), flags))
            source = (EXAMPLES / ('factory_continuous.py' if factory else 'continuous.py')).read_text()
            with self.subTest(factory=factory, flags=flags):
                state, _, cp = self.steps(source, state, limit=650)
                self.assertIsNotNone(cp)
                self.assertGreater(state['stats']['harvested'], 6)
                if factory:
                    self.assertGreater(state['stats']['bread_delivered'], 4)
