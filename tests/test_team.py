import copy
import itertools
import json
from pathlib import Path
import unittest

from farm.continuous import step_script
from farm.engine import GameError, new_state
from farm.factory import new_factory, validate_factory
from farm.saves import validate_save
from farm.team import enable_team, step_team, validate_team_checkpoint

WAIT = 'while True:\n    wait()'
EXAMPLES = Path(__file__).resolve().parent.parent / 'examples'


class TeamTests(unittest.TestCase):
    def test_two_actions_share_one_growth_machine_and_order_tick(self):
        state = new_factory()
        state['tiles'][0].update(growth=0, water=10)
        state['machines']['mill']['input'] = 4
        result = step_team([WAIT, WAIT], state)
        self.assertIsNone(result['error'])
        self.assertEqual(result['actions'], 2)
        self.assertEqual(result['state']['tick'], 1)
        self.assertEqual(result['state']['stats']['actions'], 2)
        self.assertEqual(result['state']['tiles'][0]['growth'], 1)
        self.assertEqual(result['state']['tiles'][0]['water'], 9)
        self.assertEqual(result['state']['machines']['mill']['remaining'], 3)
        self.assertEqual(result['state']['team']['actions'], [1, 1])
        self.assertNotIn('team', state)

    def test_harvest_conflict_retries_queries_without_duplicate_crop(self):
        state = enable_team(new_factory()); state['team']['drone'] = dict(state['drone'])
        code = 'if can_harvest():\n    harvest()\nwait()'
        first = step_team([code, code], state)
        self.assertEqual(first['actions'], 1)
        self.assertEqual(first['state']['stats']['harvested'], 1)
        self.assertEqual(first['state']['cargo']['wheat'], 3)
        self.assertEqual(first['state']['team']['cargo']['wheat'], 0)
        self.assertEqual(first['state']['team']['blocked'], [0, 1])
        second = step_team([code, code], first['state'], first['checkpoint'])
        self.assertIsNone(second['error'])
        self.assertEqual(second['state']['stats']['harvested'], 1)
        self.assertEqual(second['actions'], 2)

    def test_pad_priority_rotates_and_conserves_shared_stock(self):
        state = enable_team(new_factory()); state['drone'] = {'x': 0, 'y': 6}
        code = 'while True:\n    if stored("chest", "wheat") > 0 and cargo_space() > 0:\n        load("wheat", 1)\n    else:\n        wait()'
        cp = None
        for _ in range(12):
            result = step_team([code, code], state, cp)
            self.assertIsNone(result['error'])
            state, cp = result['state'], result['checkpoint']
        self.assertEqual(state['cargo']['wheat'], 6)
        self.assertEqual(state['team']['cargo']['wheat'], 6)
        self.assertEqual(state['chest']['wheat'], 0)
        self.assertEqual(state['team']['blocked'], [6, 6])

    def test_shared_supply_conflict_on_distinct_tiles_is_atomic(self):
        state = enable_team(new_factory()); state['care']['settings']['irrigation'] = True
        state['care']['tank'] = 2; state['team']['drone'] = {'x': 1, 'y': 0}
        result = step_team(['water()', 'water()'], state)
        self.assertIsNone(result['error'])
        self.assertEqual(result['state']['care']['tank'], 0)
        self.assertEqual(result['state']['tiles'][1]['water'], 0)
        self.assertEqual(result['actions'], 1)

    def test_last_tick_delivery_order_and_mission_rewards_resolve_once(self):
        state = enable_team(new_factory())
        state['tick'] = 178
        state['stats']['bread_delivered'] = 4
        state['order'].update(status='active', start_tick=0, start_delivered=4)
        state['drone'] = state['team']['drone'] = {'x': 7, 'y': 3}
        state['cargo']['bread'] = 8; state['team']['cargo']['bread'] = 4
        codes = ['if cargo("bread") > 0:\n    unload("bread", cargo("bread"))\nwait()'] * 2
        first = step_team(codes, state)
        self.assertEqual(first['state']['order']['status'], 'active')
        second = step_team(codes, first['state'], first['checkpoint'])
        self.assertIsNone(second['error'])
        self.assertEqual(second['state']['tick'], 180)
        self.assertEqual(second['state']['order']['status'], 'complete')
        self.assertEqual(second['state']['order']['completed'], 1)
        self.assertEqual(second['state']['order']['best'], 180)
        self.assertEqual(second['state']['coins'], 30 + 12 * 8 + 40)

    def test_navigation_uses_independent_positions_and_air_lanes(self):
        result = step_team(['navigate_to(1, 0)', 'navigate_to(1, 6)'], new_factory())
        self.assertEqual(result['state']['drone'], {'x': 1, 'y': 0})
        self.assertEqual(result['state']['team']['drone'], {'x': 1, 'y': 6})
        self.assertEqual(result['state']['tick'], 1)
        state = enable_team(new_factory()); state['team']['drone'] = {'x': 1, 'y': 0}
        result = step_team(['move("east")', 'move("west")'], state)
        self.assertEqual(result['state']['drone']['x'], 1)
        self.assertEqual(result['state']['team']['drone']['x'], 0)

    def test_failure_in_either_program_commits_neither_action(self):
        for bad in ('store_cargo()', 'while True: pass', 'import os', 'move("southwest")'):
            with self.subTest(bad=bad):
                result = step_team(['harvest()', bad], new_factory())
                self.assertTrue(result['done'])
                self.assertIn('Drone 2', result['error']['message'])
                self.assertEqual(result['state']['tick'], 0)
                self.assertEqual(result['state']['stats']['harvested'], 0)

    def test_finished_drone_parks_without_stopping_partner(self):
        codes = ['print("done")', WAIT]
        first = step_team(codes, new_factory())
        self.assertEqual(first['actions'], 1)
        self.assertTrue(first['checkpoint']['controllers'][0]['done'])
        second = step_team(codes, first['state'], first['checkpoint'])
        self.assertIsNone(second['error'])
        self.assertEqual(second['state']['tick'], 2)
        self.assertFalse(any('done' in frame['message'] for frame in second['frames']))
        self.assertTrue(step_team(['pass', 'pass'], new_factory())['done'])

    def test_save_roundtrip_binds_both_programs_and_world(self):
        codes = [WAIT, 'while True:\n    navigate_to("oven")\n    navigate_to("chest")']
        first = step_team(codes, new_factory())
        save = {'format': 'sprout-save', 'version': 2, 'active': 'factory', 'games': {'factory': {
            'state': first['state'], 'code': codes[0], 'team_code': codes[1], 'execution': 'team', 'speed': '4', 'checkpoint': first['checkpoint']}}}
        restored = validate_save(json.loads(json.dumps(save)))
        self.assertEqual(restored, save)
        game = restored['games']['factory']
        self.assertEqual(step_team(codes, game['state'], game['checkpoint']), step_team(codes, first['state'], first['checkpoint']))
        for changed in ([WAIT, WAIT], list(reversed(codes))):
            with self.assertRaises(GameError):
                validate_team_checkpoint(changed, first['state'], first['checkpoint'])
        changed = copy.deepcopy(first['state']); changed['team']['cargo']['wheat'] = 1
        with self.assertRaises(GameError):
            validate_team_checkpoint(codes, changed, first['checkpoint'])
        for key, value in [('version', True), ('revision', -1), ('controllers', []), ('controllers', [None, None])]:
            bad = copy.deepcopy(first['checkpoint']); bad[key] = value
            with self.subTest(key=key), self.assertRaises(GameError):
                validate_team_checkpoint(codes, first['state'], bad)

    def test_old_save_compatibility_and_parked_cargo_survives_single_mode(self):
        old = new_factory()
        self.assertEqual(old, validate_factory(old))
        first = step_script(WAIT, old)
        second = step_script(WAIT, first['state'], first['checkpoint'])
        self.assertEqual(second['state']['tick'], 2)
        state = enable_team(old); state['team']['cargo']['wheat'] = 4
        result = step_script(WAIT, state)
        self.assertEqual(result['state']['team'], state['team'])
        with self.assertRaises(GameError):
            step_team([WAIT, WAIT], new_state())
        for key, value in [('drone', {'x': 6, 'y': 2}), ('cargo', {'wheat': 9, 'flour': 0, 'bread': 0}), ('actions', [0])]:
            state = enable_team(old); state['team'][key] = value
            with self.subTest(key=key), self.assertRaises(GameError):
                validate_factory(state)

    def test_team_starter_sustains_every_growing_option_combination(self):
        codes = [(EXAMPLES / f'factory_team_{role}.py').read_text() for role in ('farmer', 'courier')]
        for flags in itertools.product((False, True), repeat=3):
            state = new_factory(); cp = None
            state['care']['settings'] = dict(zip(('fertilizer', 'irrigation', 'soil'), flags))
            with self.subTest(flags=flags):
                for _ in range(500):
                    result = step_team(codes, state, cp)
                    self.assertIsNone(result['error'], result['error'])
                    self.assertFalse(result['done'])
                    state = validate_factory(result['state'])
                    cp = json.loads(json.dumps(result['checkpoint']))
                    stock = sum(inv['wheat'] + 2 * inv['flour'] + 2 * inv['bread'] for inv in (state['cargo'], state['team']['cargo'], state['chest']))
                    for name, machine in state['machines'].items():
                        stock += machine['input'] * (1 if name == 'mill' else 2) + 2 * machine['output'] + 2 * bool(machine['remaining'])
                    stock += 2 * state['stats']['bread_delivered']
                    self.assertEqual(stock, 12 + 3 * state['stats']['harvested'] + state['care']['stats']['bonus'])
                self.assertGreater(state['stats']['harvested'], 12)
                self.assertGreater(state['stats']['bread_delivered'], 12)
