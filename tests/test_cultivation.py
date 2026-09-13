from copy import deepcopy
from itertools import product
from pathlib import Path
import unittest

from farm.engine import Farm, GameError, new_state, validate_state
from farm.factory import Factory, new_factory, validate_factory
from farm.cultivation import configure, new_care, RULES
from farm.interpreter import run_script
from farm.saves import validate_save

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class CultivationTests(unittest.TestCase):
    def enabled(self, cls=Farm, **settings):
        farm = cls()
        configure(farm.state, dict({'fertilizer': False, 'irrigation': False, 'soil': False}, **settings))
        return farm

    def crop(self, farm, growth=0, water=24):
        farm.tile.update(tilled=True, crop='wheat', growth=growth, water=water)

    def rejects(self, farm, action, *args):
        before = farm.snapshot()
        with self.assertRaises(GameError): farm.action(action, *args)
        self.assertEqual(farm.state, before)

    def test_old_worlds_migrate_to_disabled_care_without_losing_progress(self):
        for state, validate in [(new_state(), validate_state), (new_factory(), validate_factory)]:
            state.pop('care'); state['coins'] = 123; state['tick'] = 8
            restored = validate(state)
            self.assertEqual(restored['coins'], 123)
            self.assertEqual(restored['tick'], 8)
            self.assertEqual(restored['care'], new_care(state['size']))
            self.assertNotIn('care', state)

    def test_configuration_is_strict_atomic_and_does_not_tick(self):
        farm = Farm(); before = farm.snapshot()
        for bad in [None, {}, {'fertilizer': 1, 'irrigation': False, 'soil': False}, {'fertilizer': True, 'irrigation': False, 'soil': False, 'unknown': True}]:
            with self.assertRaises(GameError): configure(farm.state, bad)
            self.assertEqual(farm.state, before)
        configure(farm.state, {'fertilizer': True, 'irrigation': False, 'soil': True})
        self.assertEqual(farm.state['tick'], 0)
        self.assertEqual(farm.state['coins'], 20)

    def test_disabled_actions_do_not_mutate(self):
        farm = Farm()
        for name, args in [('fertilize', []), ('compost', []), ('install_sprinkler', []), ('refill_tank', []), ('set_irrigation', [True]), ('buy_fertilizer', [2])]:
            self.rejects(farm, name, *args)

    def test_fertilizer_consumption_boost_and_classic_sale_bonus(self):
        farm = self.enabled(fertilizer=True); self.crop(farm)
        farm.action('fertilize')
        self.assertEqual(farm.tile['growth'], 2)
        self.assertEqual(farm.state['care']['fertilizer'], 5)
        self.rejects(farm, 'fertilize')
        farm.action('wait'); farm.action('wait')
        self.assertTrue(farm.ready())
        self.rejects(farm, 'fertilize')
        coins = farm.state['coins']; farm.action('harvest')
        self.assertEqual(farm.state['coins'] - coins, 7)
        self.assertEqual(farm.state['care']['stats']['bonus'], 1)
        self.assertFalse(farm.state['care']['plots'][0]['fertilized'])

    def test_fertilizer_factory_bonus_requires_four_cargo_slots(self):
        farm = self.enabled(Factory, fertilizer=True); self.crop(farm)
        farm.action('fertilize'); farm.action('wait'); farm.action('wait')
        farm.state['cargo']['wheat'] = 5
        self.rejects(farm, 'harvest')
        farm.state['cargo']['wheat'] = 4
        farm.action('harvest')
        self.assertEqual(farm.state['cargo']['wheat'], 8)
        self.assertEqual(farm.state['stats']['earned'], 0)

    def test_boost_pauses_when_disabled_and_clears_on_harvest(self):
        farm = self.enabled(fertilizer=True); self.crop(farm, water=0)
        farm.action('fertilize'); boost = farm.state['care']['plots'][0]['boost']
        configure(farm.state, {'fertilizer': False, 'irrigation': False, 'soil': False})
        farm.action('wait')
        self.assertEqual(farm.state['care']['plots'][0]['boost'], boost)
        farm.action('water'); farm.action('wait'); farm.action('wait'); farm.action('wait'); farm.action('wait'); farm.action('wait')
        farm.action('harvest')
        self.assertEqual(farm.state['stats']['earned'], 5)
        self.assertFalse(farm.state['care']['plots'][0]['fertilized'])

    def test_buying_fertilizer_uses_well_price_and_capacity(self):
        farm = self.enabled(fertilizer=True)
        for value in (0, -2, True, 1.5, '4', 101): self.rejects(farm, 'buy_fertilizer', value)
        self.rejects(farm, 'buy_fertilizer', 20)
        farm.action('buy_fertilizer', 4)
        self.assertEqual((farm.state['coins'], farm.state['care']['fertilizer']), (12, 10))
        farm.action('move', 'east'); self.rejects(farm, 'buy_fertilizer', 1)
        farm.action('move', 'west'); farm.state['care']['fertilizer'] = 100
        self.rejects(farm, 'buy_fertilizer', 1)

    def test_soil_depletes_compost_recovers_and_poor_soil_slows_growth(self):
        farm = self.enabled(soil=True)
        farm.action('harvest')
        self.assertEqual(farm.state['care']['plots'][0]['nutrients'], 80)
        self.assertEqual(farm.state['care']['compost'], 1)
        farm.action('compost')
        self.assertEqual(farm.state['care']['plots'][0]['nutrients'], 100)
        self.assertEqual(farm.state['care']['compost'], 0)
        self.rejects(farm, 'compost')
        self.crop(farm); farm.state['care']['plots'][0]['nutrients'] = 20
        farm.action('wait'); self.assertEqual(farm.tile['growth'], 0)  # tick 3
        farm.action('wait'); self.assertEqual(farm.tile['growth'], 1)
        configure(farm.state, {'fertilizer': False, 'irrigation': False, 'soil': False})
        farm.action('wait'); self.assertEqual(farm.tile['growth'], 2)
        self.assertEqual(farm.state['care']['plots'][0]['nutrients'], 20)

    def test_fertilizer_restores_some_nutrients_and_compost_caps_at_100(self):
        farm = self.enabled(fertilizer=True, soil=True); self.crop(farm)
        farm.state['care']['plots'][0]['nutrients'] = 30
        farm.action('fertilize')
        self.assertEqual(farm.state['care']['plots'][0]['nutrients'], 40)
        farm.state['care']['compost'] = 2
        farm.action('compost'); farm.action('compost')
        self.assertEqual(farm.state['care']['plots'][0]['nutrients'], 100)

    def test_irrigation_pulses_before_growth_and_uses_shared_tank(self):
        farm = self.enabled(irrigation=True); self.crop(farm, water=0)
        farm.action('install_sprinkler')
        self.assertEqual(farm.state['coins'], 12)
        self.rejects(farm, 'install_sprinkler')
        for _ in range(4): farm.action('wait')
        self.assertEqual(farm.tile['growth'], 0)
        farm.action('wait')
        self.assertEqual(farm.tile['growth'], 1)
        self.assertEqual(farm.tile['water'], 11)
        self.assertEqual(farm.state['care']['tank'], 59)
        self.assertEqual(farm.state['care']['stats']['irrigated'], 4)  # clipped corner coverage
        farm.state['care']['tank'] = 0; farm.tile['water'] = 0
        for _ in range(6): farm.action('wait')
        self.assertEqual(farm.tile['growth'], 1)

    def test_overlapping_sprinklers_only_water_plots_below_threshold(self):
        farm = self.enabled(irrigation=True)
        farm.state['care']['sprinklers'] = [0, 1]
        farm.state['tick'] = 5
        farm.action('wait')
        self.assertEqual(farm.state['care']['tank'], 58)
        self.assertEqual(farm.state['care']['stats']['irrigated'], 6)
        for i in [0,1,2,6,7,8]: self.assertEqual(farm.state['tiles'][i]['water'], 11)

    def test_manual_water_supply_pump_control_and_refill_location(self):
        farm = self.enabled(irrigation=True); farm.state['care']['tank'] = 1
        self.rejects(farm, 'water')
        farm.action('refill_tank'); farm.action('water')
        self.assertEqual(farm.state['care']['tank'], 58)
        farm.action('move', 'east'); self.rejects(farm, 'refill_tank')
        self.rejects(farm, 'set_irrigation', 1)
        farm.action('set_irrigation', False)
        self.assertFalse(farm.state['care']['pump'])
        configure(farm.state, {'fertilizer': False, 'irrigation': False, 'soil': False})
        tank = farm.state['care']['tank']; farm.action('water')
        self.assertEqual(farm.state['care']['tank'], tank)
        configure(farm.state, {'fertilizer': False, 'irrigation': True, 'soil': False})
        self.assertFalse(farm.state['care']['pump'])

    def test_factory_care_avoids_buildings_and_irrigates_during_processing(self):
        farm = self.enabled(Factory, irrigation=True)
        farm.state['drone'] = {'x': 3, 'y': 6}
        self.rejects(farm, 'install_sprinkler')
        farm.state['care']['sprinklers'] = [0]
        farm.state['tick'] = 5; farm.state['machines']['mill']['input'] = 2
        farm.action('wait')
        self.assertEqual(farm.state['care']['tank'], 59)
        self.assertEqual(farm.state['machines']['mill']['remaining'], 3)
        self.assertEqual(farm.state['tiles'][0]['water'], 11)

    def test_expansion_remaps_soil_and_sprinklers(self):
        farm = self.enabled(irrigation=True, soil=True)
        farm.state['care']['sprinklers'] = [7, 35]
        farm.state['care']['plots'][35]['nutrients'] = 12
        farm.state['coins'] = 200; farm.unlock('expansion')
        self.assertEqual(farm.state['care']['sprinklers'], [9,45])
        self.assertEqual(farm.state['care']['plots'][45]['nutrients'], 12)
        self.assertEqual(len(farm.state['care']['plots']), 64)
        self.assertEqual(validate_state(farm.state), farm.state)

    def test_save_preserves_disabled_equipment_and_rejects_bad_care(self):
        farm = self.enabled(irrigation=True); farm.action('install_sprinkler')
        configure(farm.state, {'fertilizer': False, 'irrigation': False, 'soil': False})
        restored = Farm(farm.snapshot())
        self.assertEqual(restored.state, farm.state)
        for key, value in [('version', True), ('tank', -1), ('sprinklers', [0,0]), ('plots', []), ('pump', 1), ('settings', {})]:
            state = farm.snapshot(); state['care'][key] = value
            with self.assertRaises(GameError): validate_state(state)
        state = farm.snapshot(); state['care']['plots'][5]['fertilized'] = True
        with self.assertRaises(GameError): validate_state(state)
        state = new_factory(); state['care']['sprinklers'] = [63]
        with self.assertRaises(GameError): validate_factory(state)

    def test_queries_and_invalid_calls_are_bounded(self):
        result = run_script('print(feature_enabled("soil"), get_nutrients(), get_supply("fertilizer"), has_sprinkler(), is_fertilized(), get_yield(), get_scenario())', new_state())
        self.assertEqual(result['actions'], 0)
        self.assertEqual(result['frames'][0]['message'], 'False 100 6 False False 1 classic')
        for code in ['get_supply("unknown")', 'feature_enabled([])', 'get_nutrients(1)']:
            self.assertIsNotNone(run_script(code, new_state())['error'])

    def test_examples_work_with_all_eight_option_combinations(self):
        for cls in (Farm, Factory):
            for fertilizer, irrigation, soil in product((False, True), repeat=3):
                farm = self.enabled(cls, fertilizer=fertilizer, irrigation=irrigation, soil=soil)
                for filename in ('crop_care', 'irrigation'):
                    result = run_script((EXAMPLES / f'{filename}.py').read_text(), farm.state)
                    self.assertIsNone(result['error'], (cls.__name__, filename, result['error']))
                    for frame in result['frames']:
                        if 'state' in frame: self.assertEqual(cls(frame['state']).state, frame['state'])
                    for frame in reversed(result['frames']):
                        if 'state' in frame: farm = cls(frame['state']); break

    def test_growing_goals_pay_once_and_chapter_settings_remain_independent(self):
        farm = self.enabled(irrigation=True)
        farm.state['care']['stats']['irrigated'] = 36
        farm.action('wait'); coins = farm.state['coins']; farm.action('wait')
        self.assertEqual(farm.state['coins'], coins)
        self.assertIn('water_network', farm.state['care']['completed'])
        save = {'format':'sprout-save','version':2,'active':'classic','games':{
            'classic':{'state':farm.state,'code':'wait()','speed':'2'},
            'factory':{'state':new_factory(),'code':'wait()','speed':'2'}}}
        restored = validate_save(save)
        self.assertTrue(restored['games']['classic']['state']['care']['settings']['irrigation'])
        self.assertFalse(restored['games']['factory']['state']['care']['settings']['irrigation'])


if __name__ == '__main__':
    unittest.main()
