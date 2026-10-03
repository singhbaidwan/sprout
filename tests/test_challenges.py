"""Challenge rules, measurement accuracy, and isolated portable sessions."""
from copy import deepcopy
from pathlib import Path
import unittest

from farm import challenges, efficiency
from farm.engine import GameError, new_state
from farm.factory import Factory, ENTITIES, new_factory, validate_factory
from farm.interpreter import run_script
from farm.continuous import ContinuousInterpreter, step_script
from farm.team import step_team
from farm.saves import validate_save

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'
WAIT = 'while True:\n    wait()'


class EfficiencyTests(unittest.TestCase):
    def test_commands_loaded_travel_and_failed_action(self):
        farm = Factory()
        farm.action('move', 'east'); farm.action('harvest')
        farm.action('move', 'south'); farm.action('wait')
        metrics = farm.state['efficiency']
        self.assertEqual((metrics['ticks'], metrics['commands'], metrics['moves'], metrics['empty_moves'], metrics['waits']), (4, 4, 2, 1, 1))
        before = farm.snapshot()
        with self.assertRaises(GameError): farm.action('load', 'bread', 1)
        self.assertEqual(farm.state, before)
        self.assertEqual(validate_factory(farm.state), farm.state)

    def test_first_delivery_uses_pre_action_baseline(self):
        state = new_factory(); state['stats']['bread_delivered'] = 7
        state['drone'] = {k: ENTITIES['depot'][k] for k in ('x', 'y')}
        state['cargo']['bread'] = 3
        farm = Factory(state); farm.action('unload', 'bread', 3)
        self.assertEqual(farm.state['efficiency']['start_delivered'], 7)
        self.assertEqual(farm.state['efficiency']['transfers'], 1)

    def test_machine_categories_count_each_shared_tick_once(self):
        state = new_factory(); state['machines']['mill']['input'] = 2
        farm = Factory(state)
        for _ in range(4): farm.action('wait')
        farm.action('wait'); farm.state['machines']['mill']['output'] = 8
        farm.action('wait')
        metrics = farm.state['efficiency']
        self.assertEqual(metrics['machines']['mill'], {'working': 4, 'starved': 1, 'output_full': 1})
        self.assertEqual(metrics['machines']['oven'], {'working': 0, 'starved': 6, 'output_full': 0})
        metrics['machines']['mill']['working'] += 1
        with self.assertRaises(GameError): validate_factory(farm.state)

    def test_team_water_and_commands_use_shared_clock(self):
        state = challenges.start('waterwise', 2)
        state['care'].update(pump=True, sprinklers=[0])
        for _ in range(5): state = step_team([WAIT, WAIT], state)['state']
        result = step_team(['water()', 'wait()'], state)
        self.assertIsNone(result['error'])
        m = result['state']['efficiency']
        self.assertEqual((m['ticks'], m['commands'], m['manual_waterings'], m['water_used']), (6, 12, 1, 3))
        self.assertEqual(sum(m['machines']['mill'].values()), 6)

    def test_old_checkpoint_without_metrics_keeps_binding(self):
        state = new_factory(); vm = ContinuousInterpreter(WAIT, state)
        checkpoint = vm.checkpoint()
        self.assertNotIn('efficiency', validate_factory(state))
        result = step_script(WAIT, state, checkpoint)
        self.assertIsNone(result['error'])
        self.assertEqual(result['state']['efficiency']['start_tick'], 0)
        self.assertEqual(result['state']['efficiency']['ticks'], 1)

    def test_reset_baseline_does_not_advance_and_classic_has_no_metrics(self):
        farm = Factory(); farm.action('wait')
        state = farm.snapshot(); state['efficiency'] = efficiency.new_window(state)
        self.assertEqual(state['tick'], 1)
        self.assertEqual(validate_factory(state), state)
        self.assertEqual(state['efficiency']['ticks'], 0)
        result = run_script('wait()', new_state())
        self.assertNotIn('efficiency', result['frames'][0]['state'])


class ChallengeTests(unittest.TestCase):
    def test_fixed_snapshots_and_rules(self):
        for name in challenges.CATALOG:
            for count in (1, 2):
                state = challenges.start(name, count)
                self.assertEqual(state, challenges.start(name, count))
                self.assertEqual(state, validate_factory(state))
                self.assertEqual('team' in state, count == 2)
                farm = Factory(state)
                with self.assertRaises(GameError): farm.unlock('cargo')
                with self.assertRaises(GameError): farm.start_order()
                state['care']['settings']['soil'] = True
                with self.assertRaises(GameError): validate_factory(state)
        for name, count in [('bad', 1), ('rush', True), ('rush', 3)]:
            with self.assertRaises(GameError): challenges.start(name, count)

    def test_all_six_starters_complete_with_valid_measurements(self):
        for name in challenges.CATALOG:
            for count in (1, 2):
                with self.subTest(challenge=name, drones=count):
                    state = challenges.start(name, count); checkpoint = None
                    roles = ('farmer', 'courier') if count == 2 else ('solo',)
                    codes = [(EXAMPLES / f'challenge_{role}.py').read_text() for role in roles]
                    for _ in range(challenges.CATALOG[name]['deadline'] + 1):
                        result = step_team(codes, state, checkpoint) if count == 2 else step_script(codes[0], state, checkpoint)
                        self.assertIsNone(result['error'], result['error'])
                        state, checkpoint = result['state'], result['checkpoint']
                        self.assertEqual(validate_factory(state), state)
                        if result['done']: break
                    self.assertEqual(state['challenge']['status'], 'complete')
                    self.assertIsNone(checkpoint)
                    self.assertLessEqual(state['tick'], challenges.CATALOG[name]['deadline'])
                    self.assertLessEqual(state['efficiency']['water_used'], 24)

    def test_bounded_and_continuous_stop_on_deadline_without_error(self):
        bounded = run_script(WAIT, challenges.start('rush', 1))
        self.assertIsNone(bounded['error'])
        self.assertEqual(bounded['actions'], 180)
        state = challenges.start('rush', 1); checkpoint = None
        for _ in range(180):
            result = step_script(WAIT, state, checkpoint)
            state, checkpoint = result['state'], result['checkpoint']
        self.assertTrue(result['done']); self.assertIsNone(result['error'])
        self.assertIsNone(checkpoint); self.assertEqual(state['challenge']['status'], 'failed')
        self.assertEqual(bounded['frames'][-1]['state'], state)
        before = deepcopy(state)
        with self.assertRaises(GameError): Factory(state).action('wait')
        self.assertEqual(state, before)

    def test_last_tick_delivery_wins_but_water_limit_wins_over_delivery(self):
        farm = Factory(challenges.start('rush', 1))
        for _ in range(179): farm.action('wait')
        farm.state['stats']['bread_delivered'] = 11
        farm.state['cargo']['bread'] = 1
        farm.state['drone'] = {k: ENTITIES['depot'][k] for k in ('x', 'y')}
        farm.action('unload', 'bread', 1)
        self.assertEqual((farm.state['tick'], farm.state['challenge']['status']), (180, 'complete'))
        state = challenges.start('waterwise', 1)
        state['stats']['bread_delivered'] = 12; state['efficiency']['water_used'] = 25
        self.assertEqual(challenges.outcome(state), 'failed')

    def test_refill_does_not_erase_water_consumption(self):
        farm = Factory(challenges.start('waterwise', 1))
        for _ in range(12): farm.action('water')
        self.assertEqual(farm.state['challenge']['status'], 'active')
        farm.action('refill_tank'); farm.action('water')
        self.assertEqual(farm.state['efficiency']['water_used'], 26)
        self.assertEqual(farm.state['challenge']['status'], 'failed')
        self.assertEqual(validate_factory(farm.state), farm.state)

    def test_drone_count_is_fixed_in_every_execution_mode(self):
        for operation in (lambda: run_script('wait()', challenges.start('rush', 2)),
                          lambda: step_script('wait()', challenges.start('rush', 2)),
                          lambda: step_team(['wait()', 'wait()'], challenges.start('rush', 1))):
            with self.assertRaises(GameError): operation()

    def test_team_deadline_stops_and_terminal_record_roundtrips(self):
        state = challenges.start('rush', 2); checkpoint = None
        for _ in range(180):
            result = step_team([WAIT, WAIT], state, checkpoint)
            state, checkpoint = result['state'], result['checkpoint']
        self.assertTrue(result['done']); self.assertIsNone(result['error'])
        self.assertIsNone(checkpoint)
        self.assertEqual((state['tick'], state['efficiency']['commands']), (180, 360))
        score = challenges.score(state)
        envelope = {'format': 'sprout-save', 'version': 2, 'active': 'factory',
                    'games': {'factory': {'state': new_factory(), 'code': 'wait()', 'speed': '2'}},
                    'trial': {'active': True, 'recorded': True, 'game': {'state': state, 'code': WAIT, 'team_code': WAIT, 'execution': 'team', 'speed': '8'}},
                    'challenge_records': {'rush:2': {'attempts': 1, 'best': None, 'last': score, 'previous': None}}}
        self.assertEqual(validate_save(envelope), envelope)
        envelope['challenge_records'] = {}
        with self.assertRaises(GameError): validate_save(envelope)

    def test_trial_save_preserves_campaigns_and_paused_controller(self):
        result = step_script(WAIT, challenges.start('rush', 1))
        game = {'state': result['state'], 'code': WAIT, 'speed': '8', 'execution': 'continuous', 'checkpoint': result['checkpoint']}
        envelope = {'format': 'sprout-save', 'version': 2, 'active': 'factory', 'games': {
            'classic': {'state': new_state(), 'code': 'harvest()', 'speed': '2'},
            'factory': {'state': new_factory(), 'code': 'wait()', 'speed': '4'}},
            'trial': {'active': True, 'recorded': False, 'game': game}, 'challenge_records': {}}
        self.assertEqual(validate_save(envelope), envelope)
        restored = validate_save(envelope)
        next_result = step_script(WAIT, restored['trial']['game']['state'], restored['trial']['game']['checkpoint'])
        self.assertEqual(next_result['state']['tick'], 2)
        self.assertEqual(restored['games'], envelope['games'])
        for mutate in (lambda x: x['trial'].update(recorded=True),
                       lambda x: x['games']['factory'].update(state=game['state']),
                       lambda x: x.update(active='classic')):
            raw = deepcopy(envelope); mutate(raw)
            with self.assertRaises(GameError): validate_save(raw)

    def test_personal_records_are_bounded_and_require_completed_best(self):
        score = {'status': 'complete', 'ticks': 143, 'delivered': 12, 'water_used': 0, 'moves': 118, 'empty_moves': 84}
        records = {'rush:1': {'attempts': 1, 'best': score, 'last': score}}
        self.assertEqual(challenges.validate_records(records), records)
        for field, value in [('ticks', 181), ('ticks', True), ('delivered', 11), ('empty_moves', 119), ('status', 'failed')]:
            raw = deepcopy(records); raw['rush:1']['best'][field] = value
            with self.assertRaises(GameError): challenges.validate_records(raw)
        records['waterwise:1'] = {'attempts': 1, 'best': dict(score, water_used=25), 'last': score}
        with self.assertRaises(GameError): challenges.validate_records(records)
