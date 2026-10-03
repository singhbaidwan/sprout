"""Layout conservation, route binding, fixed trials and portable controllers."""
from copy import deepcopy
from pathlib import Path
import json
import unittest

from farm import layout, recycling, challenges, cultivation
from farm.common import GameError
from farm.continuous import step_script
from farm.engine import new_state
from farm.factory import Factory, new_factory, validate_factory
from farm.interpreter import run_script
from farm.saves import validate_save
from farm.team import enable_team, step_team

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'
WAIT = 'while True:\n    wait()'
COMPACT = {name: deepcopy(layout.COMPACT[name]) for name in ('mill', 'oven')}


def compact(recycle=False):
    state = new_factory()
    if recycle: recycling.configure(state, True)
    layout.configure(state, layout.COMPACT if recycle else COMPACT)
    return state


class LayoutTests(unittest.TestCase):
    def test_legacy_world_and_solo_team_checkpoints_stay_unchanged(self):
        state = new_factory()
        self.assertEqual(validate_factory(state), state)
        self.assertNotIn('layout', Factory(state).snapshot())
        for team in (False, True):
            first = step_team([WAIT, WAIT], state) if team else step_script(WAIT, state)
            before = deepcopy(first['state'])
            layout.configure(first['state'], {})
            self.assertEqual(first['state'], before)
            second = step_team([WAIT, WAIT], validate_factory(before), first['checkpoint']) if team else step_script(WAIT, validate_factory(before), first['checkpoint'])
            self.assertIsNone(second['error'])
            self.assertEqual(second['state']['tick'], 2)

    def test_move_keeps_entire_world_stock_batches_and_parked_cargo(self):
        state = enable_team(new_factory())
        recycling.configure(state, True)
        state['team']['cargo']['wheat'] = 3
        state['recycling']['stats']['residue_collected'] = 2
        state['recycling']['machines']['composter'].update(remaining=5)
        state['machines']['mill'].update(input=2, output=1, remaining=3)
        state['machines']['oven'].update(input=1, output=2, remaining=4)
        before = deepcopy(state)
        layout.configure(state, layout.COMPACT)
        self.assertEqual(validate_factory(state), state)
        self.assertEqual(recycling.material_total(state), recycling.material_total(before))
        self.assertEqual(dict((k,v) for k,v in state.items() if k != 'layout'), before)
        layout.configure(state, {})
        self.assertEqual(state, before)

    def test_batch_swap_and_default_overrides_are_atomic(self):
        state = new_factory()
        layout.configure(state, {'mill':{'x':6,'y':6}, 'oven':{'x':3,'y':6}})
        self.assertEqual(Factory(state).entities()['mill']['x'], 6)
        self.assertEqual(Factory(state).entities()['oven']['x'], 3)
        layout.configure(state, {'mill':{'x':3,'y':6}, 'oven':{'x':6,'y':6}})
        self.assertNotIn('layout', state)

    def test_bad_positions_leave_world_unchanged(self):
        cases = [None, [], True, {'chest':{'x':1,'y':6}}, {'wat':{'x':1,'y':6}},
                 {'composter':{'x':0,'y':4}}, {'mill':None}, {'mill':{'x':1}},
                 {'mill':{'x':1,'y':6,'z':0}}, {'mill':{'x':True,'y':6}},
                 {'mill':{'x':-1,'y':6}}, {'mill':{'x':8,'y':6}}, {'mill':{'x':1.5,'y':6}},
                 {'mill':{'x':0,'y':0}}, {'mill':{'x':3,'y':4}},
                 {'mill':{'x':0,'y':6}}, {'mill':{'x':6,'y':6}},
                 {'mill':{'x':1,'y':5}}, {'mill':{'x':5,'y':5}},
                 {'mill':{'x':1,'y':6},'oven':{'x':1,'y':6}}]
        for positions in cases:
            with self.subTest(positions=positions):
                state = new_factory(); before = deepcopy(state)
                with self.assertRaises(GameError): layout.configure(state, positions)
                self.assertEqual(state, before)

    def test_malformed_present_extensions_fail_and_empty_survives_validation(self):
        for raw in (None, [], {}, {'version':True,'positions':{}}, {'version':2,'positions':{}},
                    {'version':1,'positions':{},'extra':True}, {'version':1,'positions':{'mill':{'x':0,'y':0}}}):
            state = new_factory(); state['layout'] = raw
            with self.subTest(raw=raw), self.assertRaises(GameError): validate_factory(state)
        state = new_factory(); state['layout'] = {'version':1,'positions':{}}
        self.assertEqual(validate_factory(state), state)

    def test_recycling_install_and_pause_preserve_legal_layouts(self):
        state = compact(); recycling.configure(state, True)
        self.assertEqual(validate_factory(state), state)
        recycling.configure(state, False)
        layout.configure(state, layout.COMPACT)
        farm = Factory(state)
        self.assertEqual(farm.entities()['composter']['y'], 4)
        self.assertEqual(farm.machine_status('composter'), 'paused')
        recycling.configure(state, True)
        self.assertEqual(validate_factory(state), state)
        self.assertEqual(Factory(state).entities()['mixer']['x'], 1)

    def test_named_routes_and_transfers_use_moved_machine_only(self):
        farm = Factory(compact()); farm.state['cargo']['wheat'] = 2
        farm.state['drone'] = {'x':3,'y':6}
        before = farm.snapshot()
        with self.assertRaises(GameError): farm.action('unload','wheat',2)
        self.assertEqual(farm.snapshot(), before)
        self.assertEqual(len(farm.route('mill')), 2)
        for direction in farm.route('mill'): farm.action('move',direction)
        self.assertEqual(farm.entity_here(), 'mill')
        farm.action('unload','wheat',2)
        self.assertEqual(farm.state['cargo']['wheat'], 0)
        self.assertEqual(farm.machine_status('mill'), 'working')
        for direction in farm.route('oven'): farm.action('move',direction)
        self.assertEqual(farm.entity_here(), 'oven')

    def test_layout_changes_invalidate_an_existing_route_checkpoint(self):
        code = 'navigate_to("mill")\nunload("wheat", 2)'
        state = new_factory(); state['cargo']['wheat'] = 2
        first = step_script(code,state)
        layout.configure(first['state'],COMPACT)
        with self.assertRaises(GameError): step_script(code,first['state'],first['checkpoint'])
        restarted = step_script(code,first['state'])
        self.assertIsNone(restarted['error'])

    def test_portable_solo_team_checkpoints_keep_layout_and_inflight_route(self):
        code = 'navigate_to("mill")\nwhile True:\n    wait()'
        for execution in ('continuous','team'):
            state = compact(True)
            state['recycling']['stats']['residue_collected'] = 2
            state['recycling']['machines']['composter']['input'] = 2
            result = step_team([code,WAIT],state) if execution == 'team' else step_script(code,state)
            game = {'state':result['state'],'code':code,'speed':'8','execution':execution,'checkpoint':result['checkpoint']}
            if execution == 'team': game['team_code'] = WAIT
            raw = {'format':'sprout-save','version':2,'active':'factory','games':{'factory':game}}
            restored = validate_save(json.loads(json.dumps(raw)))
            self.assertEqual(restored, raw)
            game = restored['games']['factory']
            for _ in range(10):
                result = step_team([code,WAIT],game['state'],game['checkpoint']) if execution == 'team' else step_script(code,game['state'],game['checkpoint'])
                self.assertIsNone(result['error'])
                game.update(state=result['state'],checkpoint=result['checkpoint'])
            self.assertEqual(game['state']['drone'],COMPACT['mill'])
            self.assertEqual(game['state']['recycling']['machines']['composter']['output'],2)
            self.assertEqual(validate_factory(game['state']),game['state'])

    def test_team_contention_at_new_pad_and_production_share_one_clock(self):
        state = enable_team(compact())
        state['drone'] = state['team']['drone'] = deepcopy(COMPACT['mill'])
        state['machines']['mill'].update(output=1, input=2)
        result = step_team(['load("flour",1)','load("flour",1)'],state)
        self.assertIsNone(result['error'])
        self.assertEqual(result['state']['tick'],1)
        self.assertEqual(result['state']['cargo']['flour']+result['state']['team']['cargo']['flour'],1)
        self.assertEqual(result['state']['machines']['mill']['remaining'],3)
        self.assertEqual(sum(result['state']['team']['blocked']),1)
        self.assertEqual(validate_factory(result['state']),result['state'])

    def test_campaign_only_and_active_order_guards(self):
        states = [new_state(),challenges.start('rush',1)]
        state = new_factory(); state['stats']['bread_delivered'] = 4
        farm = Factory(state); farm.start_order(); states.append(farm.snapshot())
        for state in states:
            before = deepcopy(state)
            with self.assertRaises(GameError): layout.configure(state,COMPACT)
            self.assertEqual(state,before)
        state = challenges.start('rush',1); state['layout'] = {'version':1,'positions':{}}
        with self.assertRaises(GameError): validate_factory(state)

    def test_delivery_lab_finishes_both_layouts_and_refuses_full_machines(self):
        source = (EXAMPLES / 'factory_layout_lab.py').read_text()
        ticks = []
        for state in (new_factory(),compact()):
            result = run_script(source,state)
            self.assertIsNone(result['error'],result['error'])
            final = next(frame['state'] for frame in reversed(result['frames']) if 'state' in frame)
            self.assertEqual(final['stats']['bread_delivered'],4)
            self.assertEqual(final['chest']['wheat'],4)
            self.assertEqual(validate_factory(final),final)
            ticks.append(final['tick'])
        self.assertLess(ticks[1],ticks[0])
        state = compact(); state['machines']['mill']['output'] = 1
        result = run_script(source,state)
        self.assertIsNone(result['error'])
        self.assertFalse(any('state' in frame for frame in result['frames']))

    def test_existing_solo_recycler_and_team_examples_sustain_custom_layout(self):
        cases = [('recycling_loop',True),('continuous',False),('team',False)]
        for name,recycle in cases:
            state = compact(recycle)
            cultivation.configure(state,{'soil':True,'fertilizer':True,'irrigation':True})
            codes = [(EXAMPLES / f'factory_{role}.py').read_text() for role in ('team_farmer','team_courier')] if name == 'team' else None
            code = (EXAMPLES / f'factory_{name}.py').read_text() if codes is None else None
            cp = None
            for _ in range(700):
                result = step_team(codes,state,cp) if codes else step_script(code,state,cp)
                self.assertIsNone(result['error'],result['error'])
                state,cp = result['state'],result['checkpoint']
            self.assertGreater(state['stats']['bread_delivered'],4)
            self.assertEqual(validate_factory(state),state)
            if recycle:
                self.assertGreater(state['recycling']['stats']['fertilizer_returned'],0)
                self.assertEqual(recycling.material_total(state),2*state['recycling']['stats']['residue_collected'])
