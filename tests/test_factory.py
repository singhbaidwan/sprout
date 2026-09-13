"""Gameplay regressions: conservation, shared ticks, logistics, and progression."""

from copy import deepcopy
from pathlib import Path
import unittest

from farm.engine import GameError, new_state
from farm.factory import Factory, ENTITIES, MISSIONS, ORDER, new_factory, validate_factory, walkable
from farm.interpreter import run_script
from farm.saves import validate_save

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


def grain_total(state):
    total = sum(bag['wheat'] + 2 * bag['flour'] + 2 * bag['bread'] for bag in (state['cargo'], state['chest']))
    mill, oven = state['machines']['mill'], state['machines']['oven']
    return total + mill['input'] + 2 * (mill['output'] + bool(mill['remaining']) + oven['input'] + oven['output'] + bool(oven['remaining']) + state['stats']['bread_delivered'])


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.farm = Factory()

    def run_example(self, name):
        result = run_script((EXAMPLES / f'factory_{name}.py').read_text(), self.farm.state)
        self.assertIsNone(result['error'], result['error'])
        for frame in result['frames']:
            if 'state' in frame:
                state = frame['state']
                self.assertEqual(grain_total(state), 12 + 3 * state['stats']['harvested'])
                self.assertEqual(validate_factory(state), state)
        for frame in reversed(result['frames']):
            if 'state' in frame:
                self.farm = Factory(frame['state']); break
        return result

    def go(self, entity):
        for direction in self.farm.route(entity):
            self.farm.action('move', direction)

    def rejects_without_mutation(self, name, *args):
        before = self.farm.snapshot()
        with self.assertRaises(GameError):
            self.farm.action(name, *args)
        self.assertEqual(before, self.farm.state)

    def test_harvest_yields_items_not_sales_and_requires_space(self):
        self.farm.action('harvest')
        self.assertEqual(self.farm.state['cargo']['wheat'], 3)
        self.assertEqual(self.farm.state['coins'], 30)
        self.assertEqual(self.farm.state['stats']['earned'], 0)
        self.farm.action('move', 'east'); self.farm.action('harvest')
        self.farm.action('move', 'east')
        self.rejects_without_mutation('harvest')
        self.assertTrue(self.farm.ready())

    def test_transfer_capacity_location_and_type_checks_are_atomic(self):
        self.rejects_without_mutation('load', 'wheat', 1)
        self.go('chest')
        for amount in (0, -1, True, 1.5, '2', 9):
            self.rejects_without_mutation('load', 'wheat', amount)
        self.rejects_without_mutation('load', 'unknown', 1)
        self.farm.action('load', 'wheat', 8)
        self.rejects_without_mutation('load', 'wheat', 1)
        self.rejects_without_mutation('unload', 'flour', 1)
        self.go('oven'); self.rejects_without_mutation('unload', 'wheat', 1)
        self.go('depot'); self.rejects_without_mutation('unload', 'wheat', 1)
        self.go('mill'); self.farm.action('unload', 'wheat', 8)
        self.rejects_without_mutation('load', 'wheat', 1)
        self.rejects_without_mutation('load', 'flour', 8)

    def test_shared_chest_capacity_and_machine_input_capacity(self):
        self.go('chest')
        self.farm.state['chest'].update(wheat=46, flour=1, bread=1)
        self.farm.state['cargo']['wheat'] = 1
        self.assertEqual(self.farm.free_space('chest', 'bread'), 0)
        self.rejects_without_mutation('unload', 'wheat', 1)
        self.go('mill')
        self.farm.state['machines']['mill'].update(input=12)
        self.rejects_without_mutation('unload', 'wheat', 1)

    def test_one_action_advances_crops_and_both_machines_once(self):
        s = self.farm.state
        s['machines']['mill']['input'] = 2; s['machines']['oven']['input'] = 1
        s['tiles'][0].update(growth=0, water=8)
        self.farm.action('wait')
        self.assertEqual((s['tick'], s['tiles'][0]['growth'], s['tiles'][0]['water']), (1, 1, 7))
        self.assertEqual(s['machines']['mill'], {'input': 0, 'output': 0, 'remaining': 3})
        self.assertEqual(s['machines']['oven'], {'input': 0, 'output': 0, 'remaining': 5})
        for _ in range(3): self.farm.action('wait')
        self.assertEqual((s['machines']['mill']['output'], s['machines']['oven']['remaining']), (1, 2))
        for _ in range(2): self.farm.action('wait')
        self.assertEqual((s['stats']['flour_milled'], s['stats']['bread_baked']), (1, 1))

    def test_output_full_blocks_batch_without_consuming_ingredients(self):
        machine = self.farm.state['machines']['mill']
        machine.update(input=4, output=8)
        self.farm.action('wait')
        self.assertEqual(machine, {'input': 4, 'output': 8, 'remaining': 0})
        self.assertEqual(self.farm.machine_status('mill'), 'output_full')
        self.go('mill'); self.farm.action('load', 'flour', 1)
        self.assertEqual(machine, {'input': 2, 'output': 7, 'remaining': 3})

    def test_active_batches_survive_save_and_upgrade(self):
        self.farm.state['machines']['oven']['input'] = 2
        self.farm.state['coins'] = 100
        self.farm.action('wait')
        self.farm.unlock('oven')
        self.assertEqual(self.farm.state['machines']['oven']['remaining'], 5)
        restored = Factory(self.farm.snapshot())
        for _ in range(8):
            self.farm.action('wait'); restored.action('wait')
        self.assertEqual(restored.state, self.farm.state)
        self.assertEqual(restored.state['machines']['oven']['output'], 2)

    def test_factory_edges_rocks_and_growing_area(self):
        self.rejects_without_mutation('move', 'north')
        with self.assertRaises(GameError): self.farm.route(6, 2)
        self.go('depot')
        for command, args in [('till', []), ('plant', ['wheat']), ('water', []), ('harvest', [])]:
            self.rejects_without_mutation(command, *args)
        self.rejects_without_mutation('move', 'east')
        self.rejects_without_mutation('move', 'west')

    def test_navigation_uses_visible_steps_and_budget(self):
        result = run_script('navigate_to("depot")', new_factory())
        self.assertIsNone(result['error'])
        self.assertEqual(result['actions'], 10)
        for frame in result['frames']:
            self.assertEqual(frame['action'], 'move')
            self.assertEqual(frame['line'], 1)
            self.assertTrue(walkable(**frame['state']['drone']))
        self.assertEqual(result['frames'][-1]['state']['drone'], {'x': 7, 'y': 3})
        result = run_script('for i in range(100):\n    navigate_to("depot")\n    navigate_to("chest")', new_factory())
        self.assertEqual(result['actions'], 400)
        self.assertIn('400', result['error']['message'])
        self.assertEqual(result['frames'][-1]['state']['tick'], 400)

    def test_queries_do_not_advance_and_busy_wait_is_bounded(self):
        result = run_script('print(cargo("wheat"), cargo_space(), stored("chest", "wheat"), free_space("mill", "wheat"), machine_status("oven"), get_tick(), get_delivered())', new_factory())
        self.assertEqual(result['actions'], 0)
        self.assertEqual(result['frames'][0]['message'], '0 8 12 12 waiting_input 0 0')
        result = run_script('while stored("oven", "bread") == 0:\n    pass', new_factory())
        self.assertIn('20,000', result['error']['message'])
        self.assertEqual(result['actions'], 0)
        result = run_script('load("wheat", 1)', new_state())
        self.assertIn('Breadworks', result['error']['message'])

    def test_full_campaign_with_examples_and_conservation(self):
        self.run_example('starter')
        self.assertEqual(self.farm.state['coins'], 127)
        self.assertEqual(len(self.farm.state['completed']), 3)
        self.run_example('harvest')
        for _ in range(5): self.run_example('bakery')
        self.assertEqual(self.farm.state['completed'], [m['id'] for m in MISSIONS])
        for upgrade in ('cargo', 'mill', 'oven'): self.farm.unlock(upgrade)
        self.assertEqual(self.farm.cargo_space(), 16)
        self.run_example('bakery')

    def test_bakery_also_runs_from_new_game(self):
        self.run_example('bakery')
        self.assertGreater(self.farm.state['stats']['bread_delivered'], 0)

    def test_order_is_optional_unlocks_and_cannot_restart_active(self):
        with self.assertRaises(GameError): self.farm.start_order()
        self.run_example('starter')
        tick = self.farm.state['tick']
        self.farm.start_order()
        self.assertEqual(self.farm.state['tick'], tick)
        with self.assertRaises(GameError): self.farm.start_order()

    def test_order_deadline_final_tick_and_one_reward(self):
        s = self.farm.state
        s['stats']['bread_delivered'] = 4
        s['upgrades'] = ['cargo']; s['cargo']['bread'] = 12
        s['drone'] = {'x': 7, 'y': 3}
        self.farm.start_order()
        for _ in range(179): self.farm.action('wait')
        before = s['coins']
        self.farm.action('unload', 'bread', 12)
        self.assertEqual(s['order']['status'], 'complete')
        self.assertEqual(s['order']['best'], 180)
        self.assertEqual(s['coins'] - before, 12 * 8 + ORDER['reward'])
        self.farm.action('wait')
        self.assertEqual(s['order']['completed'], 1)

    def test_order_expiry_preserves_items_and_allows_retry(self):
        s = self.farm.state; s['stats']['bread_delivered'] = 4
        self.farm.start_order()
        for _ in range(180): self.farm.action('wait')
        self.assertEqual(s['order']['status'], 'failed')
        self.assertEqual(s['chest']['wheat'], 12)
        self.farm.start_order()
        self.assertEqual(s['order']['start_tick'], 180)

    def test_order_runner_can_complete_stocked_challenge(self):
        self.run_example('starter')
        self.run_example('harvest')
        self.run_example('harvest')
        self.farm.unlock('cargo')
        self.farm.start_order()
        self.run_example('orders')
        self.assertEqual(self.farm.state['order']['status'], 'complete')
        self.assertLessEqual(self.farm.state['order']['best'], 180)

    def test_two_chapter_save_retains_state_and_rejects_mismatches(self):
        self.run_example('starter')
        self.farm.start_order()
        raw = {'format': 'sprout-save', 'version': 2, 'active': 'factory', 'games': {
            'classic': {'state': new_state(), 'code': 'harvest()', 'speed': '2'},
            'factory': {'state': self.farm.state, 'code': 'wait()', 'speed': '8'}}}
        self.assertEqual(validate_save(raw), raw)
        bad = deepcopy(raw); bad['games']['classic']['state'] = new_factory()
        with self.assertRaises(GameError): validate_save(bad)
        bad = deepcopy(raw); bad['games']['factory']['state'] = new_state()
        with self.assertRaises(GameError): validate_save(bad)

    def test_factory_save_rejects_bad_capacities_positions_and_progress(self):
        bad_states = []
        for key, value in [('cargo', {'wheat': 8, 'flour': 1, 'bread': 0}), ('upgrades', ['cargo', 'cargo']), ('version', True), ('completed', ['first_flour']), ('order', {})]:
            s = new_factory(); s[key] = value; bad_states.append(s)
        s = new_factory(); s['drone'] = {'x': 6, 'y': 2}; bad_states.append(s)
        s = new_factory(); s['tiles'][63]['tilled'] = True; bad_states.append(s)
        s = new_factory(); s['machines']['mill'].update(remaining=2, output=8); bad_states.append(s)
        s = new_factory(); s['order'].update(status='active', start_tick=1); bad_states.append(s)
        for raw in bad_states:
            before = deepcopy(raw)
            with self.assertRaises(GameError): validate_factory(raw)
            self.assertEqual(raw, before)


if __name__ == '__main__':
    unittest.main()
