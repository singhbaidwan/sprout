"""Shared-source routing, stock conservation and portable branch decisions."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import json
import unittest
from farm import conveyors,bread_routing,stock_policy,cultivation,recycling,challenges,layout
from farm.common import GameError
from farm.factory import Factory,new_factory,validate_factory
from farm.engine import new_state
from farm.interpreter import run_script
from farm.continuous import step_script
from farm.team import step_team,enable_team
from farm.saves import validate_save
from test_conveyors import plan,world,total,WAIT

EXAMPLES=Path(__file__).resolve().parents[1]/'examples'


def branches(names=tuple(conveyors.ROUTES)):
    state=new_factory();conveyors.configure(state,True,plan(state,names));return state


class BreadRoutingTests(unittest.TestCase):
    def test_legacy_three_routes_and_checkpoints_do_not_gain_dispatch_state(self):
        for team in (False,True):
            state=world();self.assertNotIn('routing',state['conveyors'])
            first=step_team([WAIT,WAIT],state) if team else step_script(WAIT,state)
            restored=validate_factory(first['state']);self.assertEqual(restored,first['state'])
            result=step_team([WAIT,WAIT],restored,first['checkpoint']) if team else step_script(WAIT,restored,first['checkpoint'])
            self.assertIsNone(result['error']);self.assertNotIn('routing',result['state']['conveyors'])
        result=run_script('print(bread_routing())',world())
        self.assertEqual(result['frames'][-1]['message'],'not_installed')

    def test_install_defaults_sell_and_remove_empty_branch_restores_legacy_state(self):
        state=world();before=deepcopy(state)
        conveyors.configure(state,True,plan(state,tuple(conveyors.ROUTES)))
        self.assertEqual(bread_routing.get_mode(state),'sell')
        self.assertEqual(validate_factory(state),state)
        conveyors.configure(state,True,plan(state))
        self.assertEqual(state,before)

    def test_storage_requires_sale_branch_and_bad_schemas_reject_atomically(self):
        state=world();before=deepcopy(state)
        with self.assertRaises(GameError):conveyors.configure(state,True,plan(state,('bread_store',)))
        self.assertEqual(state,before)
        for raw in (None,{},False,{'version':True,'mode':'sell','next':'bread'},
                    {'version':1,'mode':'wrong','next':'bread'},{'version':1,'mode':'sell','next':'grain'},
                    {'version':1,'mode':'sell','next':'bread','extra':0}):
            state=branches();state['conveyors']['routing']=raw
            with self.assertRaises(GameError):validate_factory(state)
        state=branches();state['conveyors'].pop('routing')
        with self.assertRaises(GameError):validate_factory(state)

    def test_balanced_picks_only_one_oven_item_per_tick_and_alternates(self):
        state=branches(('bread','bread_store'));state['machines']['oven']['output']=8
        bread_routing.set_mode(state,'balanced');farm=Factory(state);initial=total(state)
        for tick in range(8):
            farm.action('wait');routes=farm.state['conveyors']['routes']
            self.assertEqual(routes['bread']['picked']+routes['bread_store']['picked'],tick+1)
            self.assertLessEqual(abs(routes['bread']['picked']-routes['bread_store']['picked']),1)
            self.assertEqual(total(farm.state),initial)
            self.assertEqual(validate_factory(farm.state),farm.state)
        self.assertEqual([farm.state['conveyors']['routes'][n]['picked'] for n in bread_routing.BRANCHES],[4,4])

    def test_balanced_fallback_for_full_branch_and_held_target(self):
        state=branches(('bread','bread_store'));state['machines']['oven']['output']=4
        state['chest']['wheat']=48
        store=state['conveyors']['routes']['bread_store'];store['slots']=[1]*len(store['slots']);store['picked']=len(store['slots'])
        state['conveyors']['routing'].update(mode='balanced',next='bread_store')
        farm=Factory(state);initial=total(state);farm.action('wait')
        self.assertEqual(farm.state['conveyors']['routes']['bread']['picked'],1)
        self.assertEqual(farm.state['conveyors']['routes']['bread_store']['delivered'],0)
        self.assertEqual(conveyors.status(farm.state,'bread_store'),'blocked')
        self.assertEqual(total(farm.state),initial)
        state=branches(('bread','bread_store'));state['machines']['oven']['output']=3
        state['conveyors']['routing'].update(mode='balanced',next='bread_store')
        stock_policy.set_policy(state,'bread_store',{'version':1,'reserve':0,'target':0})
        farm=Factory(state);farm.action('wait')
        self.assertEqual(farm.state['conveyors']['routes']['bread']['picked'],1)
        self.assertEqual(farm.state['conveyors']['routes']['bread_store']['picked'],0)

    def test_forced_destination_does_not_fall_back_and_switch_keeps_inflight_destinations(self):
        state=branches(('bread','bread_store'));state['machines']['oven']['output']=4
        farm=Factory(state);farm.action('wait') # One sale-bound loaf.
        farm.action('set_bread_routing','store')
        for _ in range(15):farm.action('wait')
        self.assertEqual(farm.state['stats']['bread_delivered'],1)
        self.assertEqual(farm.state['chest']['bread'],3)
        self.assertEqual(total(farm.state),20) # 12 wheat and 4 bread.
        self.assertEqual(conveyors.status(farm.state,'bread'),'routing_hold')
        farm.state['machines']['oven']['output']=1
        stock_policy.set_policy(farm.state,'bread_store',{'version':1,'reserve':0,'target':3})
        for _ in range(3):farm.action('wait')
        self.assertEqual(farm.state['machines']['oven']['output'],1)
        self.assertEqual(farm.state['stats']['bread_delivered'],1)

    def test_storage_counts_bread_and_transit_respects_shared_capacity_and_does_not_pay(self):
        state=branches(('bread','bread_store'));state['machines']['oven']['output']=8
        bread_routing.set_mode(state,'store');stock_policy.set_policy(state,'bread_store',{'version':1,'reserve':1,'target':4})
        farm=Factory(state);coins=state['coins'];initial=total(state)
        for _ in range(25):
            farm.action('wait');r=farm.state['conveyors']['routes']['bread_store']
            self.assertLessEqual(stock_policy.committed(farm.state,'bread_store',r),4)
            self.assertEqual(total(farm.state),initial)
        self.assertEqual(farm.state['chest']['bread'],4)
        self.assertEqual(farm.state['machines']['oven']['output'],4)
        self.assertEqual(farm.state['stats']['bread_delivered'],0)
        self.assertEqual(farm.state['coins'],coins)
        self.assertEqual(conveyors.status(farm.state,'bread_store'),'target_met')
        farm.state['drone']={'x':0,'y':6};farm.action('load','bread',2)
        self.assertEqual(farm.state['cargo']['bread'],2)
        for _ in range(12):farm.action('wait')
        self.assertEqual(farm.state['chest']['bread'],4)

    def test_pause_feed_rebuild_and_live_removal_preserve_routing_and_items(self):
        farm=Factory(branches());farm.state['machines']['oven']['output']=2
        farm.action('set_bread_routing','balanced');before=farm.snapshot()
        conveyors.configure(farm.state,False,plan(farm.state,tuple(conveyors.ROUTES)))
        routing=deepcopy(farm.state['conveyors']['routing']);routes=deepcopy(farm.state['conveyors']['routes'])
        for _ in range(3):farm.action('wait')
        self.assertEqual(farm.state['conveyors']['routing'],routing)
        self.assertEqual(farm.state['conveyors']['routes'],routes)
        conveyors.configure(farm.state,True,plan(farm.state,tuple(conveyors.ROUTES)))
        farm.action('wait');current=farm.snapshot()
        with self.assertRaises(GameError):conveyors.configure(farm.state,True,plan(farm.state))
        self.assertEqual(farm.state,current)
        self.assertEqual(total(farm.state),total(before))

    def test_policy_and_layout_bounds_extend_storage_without_changing_old_limits(self):
        state=branches();stock_policy.set_policy(state,'bread_store',{'version':1,'reserve':8,'target':48})
        self.assertEqual(validate_factory(state),state)
        for raw in ({'version':1,'reserve':9,'target':4},{'version':1,'reserve':0,'target':49},{'version':1,'reserve':0,'target':True}):
            with self.assertRaises(GameError):stock_policy.set_policy(state,'bread_store',raw)
        before=deepcopy(state)
        with self.assertRaises(GameError):layout.configure(state,{n:layout.COMPACT[n] for n in ('mill','oven')})
        self.assertEqual(state,before)

    def test_team_dispatch_command_conflicts_rotate_and_belts_tick_once(self):
        for tick,expected in ((0,'store'),(1,'balanced')):
            state=enable_team(branches());state['tick']=tick;state['machines']['oven']['output']=4
            state['team']['drone']={'x':7,'y':7}
            result=step_team(['set_bread_routing("store")','set_bread_routing("balanced")'],state)
            self.assertIsNone(result['error']);self.assertEqual(result['actions'],1)
            self.assertEqual(bread_routing.get_mode(result['state']),expected)
            self.assertEqual(sum(result['state']['conveyors']['routes'][n]['picked'] for n in bread_routing.BRANCHES),1)
        result=step_team(['set_bread_routing("balanced")','set_conveyor_feed("bread_store",False)'],branches())
        self.assertEqual(result['actions'],2);self.assertEqual(result['state']['tick'],1)

    def test_solo_team_portable_checkpoint_preserves_next_turn_paths_and_queues(self):
        for execution in ('continuous','team'):
            state=branches();state['machines']['oven']['output']=4;bread_routing.set_mode(state,'balanced')
            first=step_team([WAIT,WAIT],state) if execution=='team' else step_script(WAIT,state)
            game={'state':first['state'],'code':WAIT,'execution':execution,'checkpoint':first['checkpoint'],'speed':'8'}
            if execution=='team':game['team_code']=WAIT
            save={'format':'sprout-save','version':2,'active':'factory','games':{'factory':game}}
            self.assertEqual(validate_save(json.loads(json.dumps(save))),save)
            op=lambda:step_team([WAIT,WAIT],game['state'],game['checkpoint']) if execution=='team' else step_script(WAIT,game['state'],game['checkpoint'])
            second=op();self.assertEqual(second,op());self.assertIsNone(second['error'])
            self.assertEqual(second['state']['conveyors']['routes']['bread_store']['picked'],1)

    def test_runtime_errors_are_atomic_orders_allow_actions_and_trials_stay_fixed(self):
        for code in ['set_bread_routing(True)','set_bread_routing("bad")','set_bread_routing()']:
            r=run_script(code,branches());self.assertIsNotNone(r['error']);self.assertEqual(r['actions'],0)
        self.assertIsNotNone(run_script('set_bread_routing("store")',world())['error'])
        for state in (new_state(),challenges.start('rush',1)):
            with self.assertRaises(GameError):bread_routing.configure(state,'sell')
        state=branches();state['stats']['bread_delivered']=4;farm=Factory(state);farm.start_order();before=farm.snapshot()
        with self.assertRaises(GameError):bread_routing.configure(farm.state,'store')
        self.assertEqual(farm.state,before)
        farm.action('set_bread_routing','sell');self.assertEqual(farm.state['tick'],1)

    def test_branch_demo_conserves_every_frame_on_default_and_compact_layouts(self):
        code=(EXAMPLES/'factory_branch_demo.py').read_text()
        for compact in (False,True):
            state=new_factory()
            if compact:layout.configure(state,{n:layout.COMPACT[n] for n in ('mill','oven')})
            conveyors.configure(state,True,plan(state,tuple(conveyors.ROUTES)))
            result=run_script(code,state);self.assertIsNone(result['error'],result['error'])
            for f in result['frames']:
                if 'state' in f:self.assertEqual(total(f['state']),12);self.assertEqual(validate_factory(f['state']),f['state'])
            final=next(f['state'] for f in reversed(result['frames']) if 'state'in f)
            self.assertEqual(final['chest']['bread'],4);self.assertEqual(final['stats']['bread_delivered'],2)

    def test_balanced_farmer_sustains_all_care_and_recycling_combinations(self):
        code=(EXAMPLES/'factory_branch_farmer.py').read_text()
        for options in product((False,True),repeat=3):
            for recycled in (False,True):
                state=branches();cultivation.configure(state,dict(zip(('fertilizer','irrigation','soil'),options)))
                if recycled:recycling.configure(state,True)
                cp=None
                for _ in range(650):
                    result=step_script(code,state,cp);self.assertIsNone(result['error'],(options,recycled,result['error']))
                    state,cp=result['state'],result['checkpoint'];self.assertGreaterEqual(state['chest']['wheat'],4)
                    self.assertLessEqual(state['chest']['bread']+sum(state['conveyors']['routes']['bread_store']['slots']),4)
                self.assertGreater(state['stats']['bread_delivered'],8);self.assertEqual(state['chest']['bread'],4)
                self.assertEqual(validate_factory(state),state)
