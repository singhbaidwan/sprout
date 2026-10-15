"""Per-tick reserves and soft destination targets, with conserved old queues."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import json
import unittest
from farm import conveyors,stock_policy,cultivation,recycling,challenges,layout
from farm.common import GameError
from farm.factory import Factory,new_factory,validate_factory
from farm.engine import new_state
from farm.interpreter import run_script
from farm.continuous import step_script
from farm.team import step_team,enable_team
from farm.saves import validate_save
from test_conveyors import world,plan,total,WAIT

EXAMPLES=Path(__file__).resolve().parents[1]/'examples'


class StockPolicyTests(unittest.TestCase):
    def test_legacy_routes_and_solo_team_bindings_keep_absent_policies(self):
        for team in (False,True):
            first=step_team([WAIT,WAIT],world()) if team else step_script(WAIT,world())
            before=deepcopy(first['state']);stock_policy.configure(first['state'],{})
            self.assertEqual(first['state'],before);self.assertEqual(validate_factory(before),before)
            self.assertTrue(all('policy' not in r for r in before['conveyors']['routes'].values()))
            result=step_team([WAIT,WAIT],before,first['checkpoint']) if team else step_script(WAIT,before,first['checkpoint'])
            self.assertIsNone(result['error'])

    def test_reserve_holds_during_unrelated_drone_work_without_polling(self):
        state=world();stock_policy.set_policy(state,'grain',{'version':1,'reserve':4,'target':None})
        farm=Factory(state)
        for _ in range(90):
            farm.action('wait');self.assertGreaterEqual(farm.state['chest']['wheat'],4)
            self.assertEqual(total(farm.state),12)
        self.assertEqual(farm.state['chest']['wheat'],4)
        self.assertEqual(farm.state['stats']['bread_delivered'],4)
        self.assertEqual(conveyors.status(farm.state,'grain'),'reserve_held')

    def test_target_counts_input_transit_and_ingredients_in_active_batch(self):
        state=world(('grain',));stock_policy.set_policy(state,'grain',{'version':1,'reserve':0,'target':2})
        farm=Factory(state)
        saw_batch=False
        for _ in range(24):
            farm.action('wait');r=conveyors.get_route(farm.state,'grain')
            self.assertLessEqual(stock_policy.committed(farm.state,'grain',r),2)
            if farm.state['machines']['mill']['remaining']:
                saw_batch=True;self.assertEqual(stock_policy.intake_status(farm.state,'grain',r),'target_met')
            self.assertEqual(total(farm.state),12)
        self.assertTrue(saw_batch)

    def test_target_zero_and_below_recipe_explain_stalls_without_losing_stock(self):
        for goal in (0,1):
            state=world(('grain',));stock_policy.set_policy(state,'grain',{'version':1,'reserve':0,'target':goal})
            farm=Factory(state)
            for _ in range(20):farm.action('wait')
            self.assertEqual(farm.state['machines']['mill']['input'],goal)
            self.assertEqual(farm.state['stats']['flour_milled'],0)
            self.assertEqual(conveyors.status(farm.state,'grain'),'target_met')
            self.assertEqual(total(farm.state),12)

    def test_lowering_policy_keeps_queued_stock_batch_and_all_other_fields(self):
        farm=Factory(world())
        for _ in range(5):farm.action('wait')
        before=farm.snapshot();route_before=deepcopy(before['conveyors']['routes']['grain'])
        stock_policy.configure(farm.state,{'grain':{'version':1,'reserve':48,'target':0}})
        current=deepcopy(farm.state);current['conveyors']['routes']['grain'].pop('policy')
        self.assertEqual(current,before)
        for _ in range(8):farm.action('wait')
        route=conveyors.get_route(farm.state,'grain')
        self.assertEqual(route['picked'],route_before['picked'])
        self.assertEqual(sum(route['slots']),0);self.assertEqual(total(farm.state),12)

    def test_manual_feeds_and_master_pause_override_policies_and_clear_preserves_gate(self):
        state=world();stock_policy.configure(state,stock_policy.PRESET)
        farm=Factory(state);farm.action('set_conveyor_feed','grain',False)
        picked=conveyors.get_route(farm.state,'grain')['picked']
        for _ in range(4):farm.action('wait')
        self.assertEqual(conveyors.get_route(farm.state,'grain')['picked'],picked)
        farm.action('clear_conveyor_policy','grain')
        self.assertFalse(conveyors.get_route(farm.state,'grain')['feeding'])
        self.assertNotIn('policy',conveyors.get_route(farm.state,'grain'))
        config=plan(farm.state);conveyors.configure(farm.state,False,config)
        before=deepcopy(farm.state['conveyors'])
        for _ in range(5):farm.action('wait')
        self.assertEqual(farm.state['conveyors'],before)

    def test_bread_reserve_and_destination_none_use_finished_output_only(self):
        state=world(('bread',));state['machines']['oven']['output']=3
        stock_policy.set_policy(state,'bread',{'version':1,'reserve':1,'target':None})
        farm=Factory(state)
        for _ in range(20):farm.action('wait')
        self.assertEqual(farm.state['machines']['oven']['output'],1)
        self.assertEqual(farm.state['stats']['bread_delivered'],2)
        self.assertIsNone(stock_policy.committed(farm.state,'bread',conveyors.get_route(farm.state,'bread')))

    def test_drone_can_use_reserved_stock_and_belt_observes_post_action_inventory(self):
        state=world(('grain',));state['drone']={'x':0,'y':6}
        stock_policy.set_policy(state,'grain',{'version':1,'reserve':10,'target':None})
        farm=Factory(state);farm.action('load','wheat',4)
        self.assertEqual(farm.state['chest']['wheat'],8)
        self.assertEqual(conveyors.get_route(farm.state,'grain')['picked'],0)
        self.assertEqual(total(farm.state),12)

    def test_policy_preflight_rejects_invalid_batch_atomically(self):
        state=world();before=deepcopy(state)
        bad=[None,True,{}, {'version':True,'reserve':4,'target':6}, {'version':1,'reserve':True,'target':6},
             {'version':1,'reserve':-1,'target':6},{'version':1,'reserve':49,'target':6},
             {'version':1,'reserve':4,'target':True},{'version':1,'reserve':4,'target':13},
             {'version':1,'reserve':4,'target':1.5},{'version':1,'reserve':4,'target':6,'extra':0}]
        for policy in bad:
            with self.assertRaises(GameError):stock_policy.set_policy(state,'grain',policy)
            self.assertEqual(state,before)
        for updates in ({'grain':stock_policy.PRESET['grain'],'flour':{'version':1,'reserve':9,'target':2}},
                        {'bread':{'version':1,'reserve':0,'target':1}}, {'unknown':None}):
            with self.assertRaises(GameError):stock_policy.configure(state,updates)
            self.assertEqual(state,before)
        with self.assertRaises(GameError):stock_policy.configure(new_factory(),{'grain':stock_policy.PRESET['grain']})

    def test_present_malformed_saved_policy_fails_but_explicit_defaults_survive(self):
        state=world();r=conveyors.get_route(state,'grain')
        for raw in (None,{},False,{'version':1,'reserve':4,'target':False}):
            r['policy']=raw
            with self.assertRaises(GameError):validate_factory(state)
        r['policy']={'version':1,'reserve':0,'target':None}
        self.assertEqual(validate_factory(state),state)

    def test_rebuild_toggles_and_empty_reroutes_keep_policy_and_removal_clears_it(self):
        state=world();stock_policy.configure(state,stock_policy.PRESET)
        config=plan(state);conveyors.configure(state,False,config)
        self.assertEqual(conveyors.get_route(state,'grain')['policy'],stock_policy.PRESET['grain'])
        config['grain']['path']=[48,56,57,58,59,51];conveyors.configure(state,True,config)
        self.assertEqual(conveyors.get_route(state,'grain')['policy'],stock_policy.PRESET['grain'])
        config['grain']['policy']=None;conveyors.configure(state,True,config)
        self.assertNotIn('policy',conveyors.get_route(state,'grain'))
        conveyors.configure(state,True,{})
        self.assertEqual(state['conveyors']['routes'],{})

    def test_runtime_actions_are_strict_and_shared_gate_contention_rotates(self):
        for code in ['set_conveyor_policy("grain", True, 6)','set_conveyor_policy("bread", 0, 4)',
                     'set_conveyor_policy("grain", 4)','clear_conveyor_policy("nope")']:
            result=run_script(code,world());self.assertIsNotNone(result['error']);self.assertEqual(result['actions'],0)
        code='set_conveyor_policy("grain",4,6)\nprint(conveyor_reserve("grain"),conveyor_target("grain"))\nclear_conveyor_policy("grain")'
        result=run_script(code,world());self.assertIsNone(result['error']);self.assertEqual(result['actions'],2)
        self.assertTrue(any(f.get('message')=='4 6' for f in result['frames']))
        for tick,first_wins in ((0,True),(1,False)):
            state=enable_team(world());state['tick']=tick;state['team']['drone']={'x':7,'y':7}
            result=step_team(['set_conveyor_policy("grain",4,6)','set_conveyor_feed("grain",False)'],state)
            self.assertEqual(result['actions'],1)
            self.assertEqual('policy' in conveyors.get_route(result['state'],'grain'),first_wins)
        result=step_team(['set_conveyor_policy("grain",4,6)','set_conveyor_policy("flour",0,3)'],world())
        self.assertEqual(result['actions'],2);self.assertEqual(result['state']['tick'],1)

    def test_orders_allow_runtime_actions_but_workshop_and_challenges_stay_fixed(self):
        for state in (new_state(),challenges.start('rush',1)):
            with self.assertRaises(GameError):stock_policy.configure(state,{})
        state=world();state['stats']['bread_delivered']=4;farm=Factory(state);farm.start_order();before=farm.snapshot()
        with self.assertRaises(GameError):stock_policy.configure(farm.state,stock_policy.PRESET)
        self.assertEqual(farm.state,before)
        farm.action('set_conveyor_policy','grain',4,6);self.assertEqual(farm.state['tick'],1)

    def test_portable_solo_team_policy_queues_and_deterministic_retries(self):
        for execution in ('continuous','team'):
            state=world();stock_policy.configure(state,stock_policy.PRESET)
            result=step_team([WAIT,WAIT],state) if execution=='team' else step_script(WAIT,state)
            game={'state':result['state'],'code':WAIT,'execution':execution,'checkpoint':result['checkpoint'],'speed':'8'}
            if execution=='team':game['team_code']=WAIT
            save={'format':'sprout-save','version':2,'active':'factory','games':{'factory':game}}
            self.assertEqual(validate_save(json.loads(json.dumps(save))),save)
            op=lambda:step_team([WAIT,WAIT],game['state'],game['checkpoint']) if execution=='team' else step_script(WAIT,game['state'],game['checkpoint'])
            second=op();self.assertEqual(second,op());self.assertIsNone(second['error'])
            self.assertEqual(total(second['state']),12)

    def test_target_demo_conserves_frames_and_finishes_with_four_reserved_wheat(self):
        code=(EXAMPLES/'factory_target_demo.py').read_text()
        for compact in (False,True):
            state=new_factory()
            if compact:layout.configure(state,{n:layout.COMPACT[n] for n in ('mill','oven')})
            conveyors.configure(state,True,plan(state))
            result=run_script(code,state);self.assertIsNone(result['error'])
            for frame in result['frames']:
                if 'state' in frame:self.assertEqual(total(frame['state']),12);self.assertGreaterEqual(frame['state']['chest']['wheat'],4)
            final=next(f['state'] for f in reversed(result['frames']) if 'state' in f)
            self.assertEqual(final['stats']['bread_delivered'],4);self.assertEqual(final['chest']['wheat'],4)
            self.assertEqual(validate_factory(final),final)

    def test_policy_farmer_sustains_all_care_and_recycling_combinations(self):
        code=(EXAMPLES/'factory_target_farmer.py').read_text()
        for options in product((False,True),repeat=3):
            for recycled in (False,True):
                state=world();cultivation.configure(state,dict(zip(('fertilizer','irrigation','soil'),options)))
                if recycled:recycling.configure(state,True)
                cp=None
                for _ in range(650):
                    result=step_script(code,state,cp);self.assertIsNone(result['error'],(options,recycled,result['error']))
                    state,cp=result['state'],result['checkpoint'];self.assertGreaterEqual(state['chest']['wheat'],4)
                    route=conveyors.get_route(state,'grain')
                    if 'policy' in route:self.assertLessEqual(stock_policy.committed(state,'grain',route),6)
                self.assertGreater(state['stats']['bread_delivered'],8)
                self.assertEqual(validate_factory(state),state)
