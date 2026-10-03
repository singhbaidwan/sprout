"""Optional byproduct logistics, conservation, one clock, and save compatibility."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import unittest

from farm import cultivation, recycling, challenges
from farm.common import GameError
from farm.continuous import step_script, validate_checkpoint
from farm.engine import new_state
from farm.factory import Factory, new_factory, validate_factory
from farm.interpreter import run_script
from farm.saves import validate_save
from farm.team import enable_team, step_team

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'
WAIT = 'while True:\n    wait()'


def world():
    state = new_factory()
    recycling.configure(state, True)
    return state


def residue_fixture(amount=2):
    state = world()
    state['recycling']['residue'] = amount
    state['recycling']['stats']['residue_collected'] = amount
    return state


class RecyclingTests(unittest.TestCase):
    def assert_valid(self, state):
        self.assertEqual(validate_factory(state), state)
        self.assertEqual(recycling.material_total(state), 2 * state['recycling']['stats']['residue_collected'])

    def reject_action(self, farm, name, *args):
        before = farm.snapshot()
        with self.assertRaises(GameError): farm.action(name, *args)
        self.assertEqual(farm.snapshot(), before)

    def test_option_keeps_legacy_worlds_and_checkpoint_bindings_unchanged(self):
        for state in (new_factory(), enable_team(new_factory())):
            before = deepcopy(state)
            self.assertEqual(validate_factory(state), before)
            recycling.configure(state, False)
            self.assertEqual(state, before)
            first = step_script(WAIT, state)
            self.assertEqual(validate_checkpoint(WAIT, validate_factory(first['state']), first['checkpoint']), first['checkpoint'])
            recycling.configure(state, True)
            self.assertEqual(state['tick'], before['tick'])
            self.assertEqual(state['care'], before['care'])
            self.assertEqual(state['machines'], before['machines'])
            self.assertEqual(state['coins'], before['coins'])
            self.assertEqual(state['recycling']['stats']['residue_collected'], 0)
            if 'team' in state: self.assertEqual(set(state['team']['cargo']), set(state['cargo']))
            self.assert_valid(state)
        state = enable_team(world())
        self.assertEqual(set(state['team']['cargo']), set(state['cargo']))
        first = step_team([WAIT, WAIT], new_factory())
        second = step_team([WAIT, WAIT], validate_factory(first['state']), first['checkpoint'])
        self.assertIsNone(second['error'])
        self.assertNotIn('recycling', second['state'])

    def test_option_is_strict_and_factory_only(self):
        for value in ('on', 1, 0, None, [], {}):
            state = new_factory(); before = deepcopy(state)
            with self.assertRaises(GameError): recycling.configure(state, value)
            self.assertEqual(state, before)
        with self.assertRaises(GameError): recycling.configure(new_state(), True)
        state = challenges.start('rush', 1)
        with self.assertRaises(GameError): recycling.configure(state, True)
        state['recycling'] = recycling.new_line()
        for bag in (state['cargo'], state['chest']): bag.update(dict.fromkeys(recycling.ITEMS, 0))
        with self.assertRaises(GameError): validate_factory(state)

    def test_harvest_supplies_residue_without_cargo_or_duplicate_compost(self):
        for soil in (False, True):
            state = world(); state['care']['settings']['soil'] = soil
            farm = Factory(state); farm.action('harvest')
            self.assertEqual(farm.state['cargo']['wheat'], 3)
            self.assertEqual(farm.state['cargo']['residue'], 0)
            self.assertEqual(farm.state['recycling']['residue'], 1)
            self.assertEqual(farm.state['care']['compost'], 0)
            self.assertEqual(farm.state['care']['plots'][0]['nutrients'], 80 if soil else 100)
            recycling.configure(farm.state, False)
            farm.action('move', 'east'); farm.action('harvest')
            self.assertEqual(farm.state['recycling']['residue'], 1)
            self.assertEqual(farm.state['care']['compost'], 1 if soil else 0)
            self.assert_valid(farm.state)

    def test_full_hopper_blocks_harvest_atomically_and_loading_frees_it(self):
        farm = Factory(residue_fixture(48)); farm.state['care']['settings']['soil'] = True
        self.reject_action(farm, 'harvest')
        farm.action('load', 'residue', 1)
        farm.action('harvest')
        self.assertEqual(farm.state['recycling']['residue'], 48)
        self.assertEqual(farm.state['cargo']['wheat'], 3)
        self.assert_valid(farm.state)

    def test_shared_cargo_chest_and_machine_input_limits_are_atomic(self):
        farm = Factory(residue_fixture(20))
        farm.action('load', 'residue', 8)
        self.reject_action(farm, 'load', 'residue', 1)
        farm.state['drone'] = {'x': 0, 'y': 6}
        farm.state['chest']['wheat'] = 46
        self.reject_action(farm, 'unload', 'residue', 3)
        farm.action('unload', 'residue', 2)
        self.assertEqual(farm.free_space('chest', 'wheat'), 0)
        self.reject_action(farm, 'unload', 'residue', 1)
        farm.state['drone'] = {'x': 1, 'y': 5}
        farm.state['recycling']['machines']['composter']['input'] = 12
        farm.state['recycling']['residue'] -= 12
        self.reject_action(farm, 'unload', 'residue', 1)
        self.reject_action(farm, 'unload', 'compost', 1)
        self.reject_action(farm, 'load', 'residue', 1)
        self.assert_valid(farm.state)

    def test_two_item_output_reservation_and_transport_resume(self):
        state = world(); line = state['recycling']
        line['stats'].update(residue_collected=10, compost_produced=8)
        line['machines']['composter'].update(input=2, output=7)
        state['cargo']['compost'] = 1
        farm = Factory(state)
        self.assertEqual(farm.machine_status('composter'), 'output_full')
        farm.action('wait')
        self.assertEqual(farm.state['recycling']['machines']['composter']['input'], 2)
        farm.state['drone'] = {'x': 1, 'y': 5}; farm.action('load', 'compost', 1)
        self.assertEqual(farm.state['recycling']['machines']['composter']['remaining'], 5)
        for _ in range(5): farm.action('wait')
        self.assertEqual(farm.state['recycling']['machines']['composter']['output'], 8)
        self.assert_valid(farm.state)

    def test_disable_pauses_exact_batch_but_allows_transfers(self):
        farm = Factory(residue_fixture())
        farm.action('load', 'residue', 2)
        farm.state['drone'] = {'x': 1, 'y': 5}; farm.action('unload', 'residue', 2)
        recycling.configure(farm.state, False)
        line = deepcopy(farm.state['recycling'])
        for _ in range(9): farm.action('wait')
        self.assertEqual(farm.state['recycling'], line)
        self.assertEqual(farm.machine_status('composter'), 'paused')
        recycling.configure(farm.state, True)
        for _ in range(5): farm.action('wait')
        self.assertEqual(farm.state['recycling']['machines']['composter']['output'], 2)
        recycling.configure(farm.state, False)
        farm.action('load', 'compost', 2)
        self.assertEqual(farm.state['cargo']['compost'], 2)
        self.assert_valid(farm.state)

    def test_queries_and_existing_examples_are_bounded_and_conserve_materials(self):
        state = world()
        source = 'print(feature_enabled("recycling"), stored("well", "residue"), free_space("composter", "residue"), machine_status("mixer"))'
        result = run_script(source, state)
        self.assertIsNone(result['error']); self.assertEqual(result['actions'], 0)
        self.assertEqual(result['frames'][0]['message'], 'True 0 12 waiting_input')
        result = run_script('while stored("mixer", "fertilizer") == 0:\n    pass', state)
        self.assertEqual(result['actions'], 0); self.assertIn('20,000', result['error']['message'])
        self.assertFalse(cultivation.query(new_factory(), 'feature_enabled', ['recycling']))
        with self.assertRaises(GameError): cultivation.query(new_state(), 'feature_enabled', ['recycling'])
        result = run_script((EXAMPLES / 'factory_starter.py').read_text(), state)
        self.assertIsNone(result['error'])
        last = next(f['state'] for f in reversed(result['frames']) if 'state' in f)
        self.assertEqual(last['stats']['bread_delivered'], 4)
        self.assert_valid(last)

    def test_demo_runs_all_growing_combinations_and_returns_usable_supplies(self):
        source = (EXAMPLES / 'factory_recycling.py').read_text()
        for values in product((False, True), repeat=3):
            with self.subTest(values=values):
                state = world(); cultivation.configure(state, dict(zip(('fertilizer','irrigation','soil'), values)))
                result = run_script(source, state)
                self.assertIsNone(result['error'], result['error'])
                states = [f['state'] for f in result['frames'] if 'state' in f]
                for state in states: self.assert_valid(state)
                state = states[-1]
                self.assertEqual(state['recycling']['stats']['compost_returned'], 1)
                self.assertEqual(state['recycling']['stats']['fertilizer_returned'], 2)
                self.assertEqual(state['care']['compost'], 1)
                self.assertEqual(state['care']['fertilizer'], 8)
                farm = Factory(state)
                farm.state['drone'] = {'x': 0, 'y': 0}
                self.reject_action(farm, 'load', 'compost', 1)
                self.reject_action(farm, 'load', 'fertilizer', 1)
                farm.state['care']['settings'].update(soil=True, fertilizer=True)
                farm.state['care']['plots'][0]['nutrients'] = 40
                farm.action('compost'); farm.action('plant', 'wheat'); farm.action('fertilize')
                self.assertEqual(farm.state['care']['compost'], 0)
                self.assertEqual(farm.state['care']['fertilizer'], 7)
                self.assert_valid(farm.state)

    def test_well_limits_returns_and_residue_can_be_put_back(self):
        state = residue_fixture(4); state['recycling']['residue'] = 2
        state['cargo'].update(compost=1, fertilizer=2)
        state['recycling']['stats'].update(compost_produced=2, fertilizer_produced=2)
        state['care'].update(compost=1000, fertilizer=100)
        farm = Factory(state)
        self.reject_action(farm, 'unload', 'compost', 1)
        self.reject_action(farm, 'unload', 'fertilizer', 2)
        farm.action('load', 'residue', 2); farm.action('unload', 'residue', 2)
        self.assertEqual(farm.state['recycling']['residue'], 2)
        self.assert_valid(farm.state)

    def test_two_drones_share_one_production_tick_and_contested_stock(self):
        state = residue_fixture(); state['recycling']['residue'] = 0
        state['recycling']['machines']['composter']['input'] = 2
        first = step_team([WAIT, WAIT], state)
        self.assertEqual(first['actions'], 2); self.assertEqual(first['state']['tick'], 1)
        self.assertEqual(first['state']['recycling']['machines']['composter']['remaining'], 5)
        state = first['state']; cp = first['checkpoint']
        for _ in range(5):
            result = step_team([WAIT, WAIT], state, cp); state, cp = result['state'], result['checkpoint']
        self.assertEqual(state['recycling']['machines']['composter']['output'], 2)
        # Advance to odd priority so Drone 2 wins the next contested collection.
        result = step_team([WAIT, WAIT], state, cp); state = result['state']
        state['drone'] = state['team']['drone'] = {'x': 1, 'y': 5}
        codes = ['if stored("composter", "compost") > 0:\n    load("compost", 2)\nwait()'] * 2
        result = step_team(codes, state)
        self.assertIsNone(result['error']); self.assertEqual(result['actions'], 1)
        self.assertEqual(result['state']['cargo']['compost'] + result['state']['team']['cargo']['compost'], 2)
        self.assertEqual(result['state']['team']['cargo']['compost'], 2)
        self.assertEqual(sum(result['state']['team']['blocked']), 1)
        self.assert_valid(result['state'])
        # A parked drone's recycling cargo must survive a solo controller/save.
        result = step_script(WAIT, result['state'])
        self.assert_valid(result['state'])
        game = {'state':result['state'],'code':WAIT,'speed':'8','execution':'continuous','checkpoint':result['checkpoint']}
        restored = validate_save({'format':'sprout-save','version':2,'active':'factory','games':{'factory':game}})
        self.assertEqual(restored['games']['factory']['state']['team']['cargo']['compost'], 2)

    def test_team_fault_cannot_commit_partner_residue_load(self):
        state = residue_fixture()
        result = step_team(['load("residue", 2)', 'import os'], state)
        self.assertIsNotNone(result['error']); self.assertEqual(result['state']['tick'], 0)
        self.assertEqual(result['state']['recycling']['residue'], 2)
        self.assertEqual(result['state']['cargo']['residue'], 0)
        self.assert_valid(result['state'])

    def test_portable_solo_and_team_checkpoints_keep_inflight_batches(self):
        state = residue_fixture(); state['recycling']['residue'] = 0
        state['recycling']['machines']['composter']['input'] = 2
        for execution in ('continuous', 'team'):
            result = step_team([WAIT, WAIT], state) if execution == 'team' else step_script(WAIT, state)
            game = {'state': result['state'], 'code': WAIT, 'speed': '8', 'execution': execution, 'checkpoint': result['checkpoint']}
            if execution == 'team': game['team_code'] = WAIT
            raw = {'format':'sprout-save','version':2,'active':'factory','games':{'factory':game}}
            restored = validate_save(json.loads(json.dumps(raw)))
            self.assertEqual(raw, restored)
            game = restored['games']['factory']
            next_step = step_team([WAIT, WAIT], game['state'], game['checkpoint']) if execution == 'team' else step_script(WAIT, game['state'], game['checkpoint'])
            self.assertIsNone(next_step['error'])
            self.assertEqual(next_step['state']['recycling']['machines']['composter']['remaining'], 4)
            self.assert_valid(next_step['state'])

    def test_malformed_saves_reject_capacity_missing_items_and_lost_materials(self):
        mutations = [lambda s:s['cargo'].pop('residue'), lambda s:s['recycling'].update(version=True),
                     lambda s:s['recycling'].update(enabled='on'), lambda s:s['recycling'].update(residue=49),
                     lambda s:s['recycling']['machines']['composter'].update(output=8,remaining=2),
                     lambda s:s['recycling']['stats'].update(compost_returned=1),
                     lambda s:s['recycling']['stats'].update(compost_produced=1),
                     lambda s:s['cargo'].update(compost=1), lambda s:s['recycling'].update(machines=[])]
        for mutate in mutations:
            state = residue_fixture(); mutate(state); before = deepcopy(state)
            with self.assertRaises(GameError): validate_factory(state)
            self.assertEqual(state, before)

    def test_autopilot_sustains_bakery_and_recycling_all_care_combinations(self):
        source = (EXAMPLES / 'factory_recycling_loop.py').read_text()
        for values in product((False, True), repeat=3):
            with self.subTest(values=values):
                state = world(); cultivation.configure(state, dict(zip(('fertilizer','irrigation','soil'),values)))
                cp = None
                for _ in range(1000):
                    result = step_script(source, state, cp)
                    self.assertIsNone(result['error'], result['error']); self.assertFalse(result['done'])
                    state, cp = result['state'], result['checkpoint']
                    self.assert_valid(state)
                self.assertGreater(state['stats']['bread_delivered'], 12)
                self.assertGreater(state['recycling']['stats']['compost_returned'], 0)
                if values[0]: self.assertGreater(state['recycling']['stats']['fertilizer_returned'], 0)


if __name__ == '__main__': unittest.main()
