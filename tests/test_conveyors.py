"""Conserved queued transport, fair phases, safe rebuilding and controllers."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import json
import unittest
from farm import conveyors, recycling, layout, challenges, cultivation
from farm.common import GameError
from farm.factory import Factory, new_factory, validate_factory
from farm.engine import new_state
from farm.interpreter import run_script
from farm.continuous import step_script
from farm.team import step_team, enable_team
from farm.saves import validate_save
from test_factory import grain_total

WAIT='while True:\n    wait()'
EXAMPLES=Path(__file__).resolve().parents[1]/'examples'


def plan(state, names=tuple(conveyors.ROUTES)):
    return {name:{'path':conveyors.auto_path(state,name),'feeding':True} for name in names}


def world(names=tuple(conveyors.ROUTES)):
    state=new_factory();conveyors.configure(state,True,plan(state,names));return state


def total(state):
    value=grain_total(state)
    if 'team' in state:
        bag=state['team']['cargo'];value+=bag['wheat']+2*bag['flour']+2*bag['bread']
    return value+sum(sum(r['slots'])*(1 if name=='grain' else 2) for name,r in state.get('conveyors',{}).get('routes',{}).items())


class ConveyorTests(unittest.TestCase):
    def test_untouched_solo_team_checkpoints_keep_legacy_schema(self):
        for team in (False,True):
            state=new_factory();first=step_team([WAIT,WAIT],state) if team else step_script(WAIT,state)
            before=deepcopy(first['state']);conveyors.configure(first['state'],False,{})
            self.assertEqual(first['state'],before);self.assertNotIn('conveyors',before)
            next_=step_team([WAIT,WAIT],validate_factory(before),first['checkpoint']) if team else step_script(WAIT,validate_factory(before),first['checkpoint'])
            self.assertIsNone(next_['error']);self.assertEqual(next_['state']['tick'],2)

    def test_build_pause_and_noop_keep_world_without_ticking(self):
        state=enable_team(new_factory());recycling.configure(state,True)
        state['team']['cargo']['wheat']=2;state['machines']['oven']['remaining']=4
        before=deepcopy(state);conveyors.configure(state,True,plan(state))
        self.assertEqual({k:v for k,v in state.items() if k!='conveyors'},before)
        self.assertEqual(validate_factory(state),state)
        line=deepcopy(state['conveyors']);conveyors.configure(state,False,plan(state))
        line['enabled']=False;self.assertEqual(state['conveyors'],line)
        self.assertEqual(state['tick'],0)

    def test_one_hop_and_one_pickup_per_phase_and_expected_latency(self):
        farm=Factory(world(('grain',)));expected=[[1,0,0],[1,1,0],[1,1,1],[1,1,1]]
        for i,slots in enumerate(expected):
            farm.action('wait');self.assertEqual(farm.state['conveyors']['routes']['grain']['slots'],slots)
            self.assertEqual(farm.state['conveyors']['routes']['grain']['delivered'],max(0,i-2))
            self.assertEqual(total(farm.state),12)
            self.assertEqual(validate_factory(farm.state),farm.state)
        self.assertEqual(farm.state['machines']['mill']['input'],1)

    def test_machine_output_created_in_phase_is_picked_next_tick(self):
        state=world(('flour',));state['machines']['mill']['remaining']=1
        farm=Factory(state);farm.action('wait')
        self.assertEqual(farm.state['machines']['mill']['output'],1)
        self.assertEqual(conveyors.get_route(farm.state,'flour')['picked'],0)
        farm.action('wait');self.assertEqual(conveyors.get_route(farm.state,'flour')['slots'],[1,0,0])

    def test_full_input_backs_up_queue_without_loss_then_resumes(self):
        state=world(('grain',));state['machines']['mill'].update(input=12,output=8)
        farm=Factory(state);initial=total(state)
        for _ in range(20):farm.action('wait');self.assertEqual(total(farm.state),initial)
        route=conveyors.get_route(farm.state,'grain')
        self.assertEqual((route['picked'],route['delivered'],route['slots']),(3,0,[1,1,1]))
        self.assertEqual(conveyors.status(farm.state,'grain'),'blocked')
        farm.state['drone']={'x':3,'y':6};farm.action('load','flour',1)
        self.assertEqual(farm.state['machines']['mill']['input'],10)
        farm.action('wait');self.assertEqual(route['delivered'],1)
        self.assertEqual(total(farm.state),initial)

    def test_paused_queue_and_stock_survive_world_ticks_then_feed_off_drains(self):
        farm=Factory(world(('grain',)));farm.action('wait')
        config=plan(farm.state,('grain',));conveyors.configure(farm.state,False,config)
        line=deepcopy(farm.state['conveyors'])
        for _ in range(6):farm.action('wait')
        self.assertEqual(farm.state['conveyors'],line)
        config['grain']['feeding']=False;conveyors.configure(farm.state,True,config)
        for _ in range(4):farm.action('wait')
        route=conveyors.get_route(farm.state,'grain')
        self.assertEqual((route['picked'],route['delivered']),(1,1))
        self.assertEqual(conveyors.status(farm.state,'grain'),'drained')

    def test_live_removal_and_reroute_reject_atomically_unchanged_path_keeps_ledger(self):
        farm=Factory(world(('grain',)));farm.action('wait');state=farm.state;before=deepcopy(state)
        for routes in ({},{'grain':{'path':[48,56,57,58,59,51],'feeding':True}}):
            with self.assertRaises(GameError):conveyors.configure(state,True,routes)
            self.assertEqual(state,before)
        config=plan(state,('grain',));config['grain']['feeding']=False
        conveyors.configure(state,True,config)
        self.assertEqual(state['conveyors']['routes']['grain']['slots'],[1,0,0])
        self.assertEqual(state['conveyors']['routes']['grain']['picked'],1)
        for _ in range(4):farm.action('wait')
        conveyors.configure(state,True,{})
        self.assertEqual(state['conveyors']['routes'],{})
        self.assertEqual(total(state),12)

    def test_invalid_paths_and_config_leave_world_unchanged(self):
        cases=[[],[48],[48,51],[48,49,48,49,50,51],[48,49,50,True],
               [48,49,50,52],[48,40,41,42,34,35,43,51],
               [48,40,41,42,43,44,45,46,47,55,54,53,52,51],
               [48,40,41,42,43,51], [48]*33]
        for path in cases:
            state=new_factory();before=deepcopy(state)
            with self.subTest(path=path),self.assertRaises(GameError):
                conveyors.configure(state,True,{'grain':{'path':path,'feeding':True}})
            self.assertEqual(state,before)
        for enabled,routes in [('on',{}),(True,None),(True,{'wrong':{'path':[48,49,50,51],'feeding':True}}),
                               (True,{'grain':{'path':[48,49,50,51],'feeding':1}})]:
            state=new_factory();before=deepcopy(state)
            with self.assertRaises(GameError):conveyors.configure(state,enabled,routes)
            self.assertEqual(state,before)

    def test_bad_saved_queues_versions_counters_and_routes_fail(self):
        state=world();mutations=[lambda s:s['conveyors'].update(version=True),lambda s:s['conveyors'].update(enabled=1),
            lambda s:s['conveyors'].update(extra=0),lambda s:s['conveyors']['routes']['grain'].update(slots=[True,0,0]),
            lambda s:s['conveyors']['routes']['grain'].update(slots=[1,0,0]),lambda s:s['conveyors']['routes']['grain'].update(picked=1),
            lambda s:s['conveyors']['routes']['grain'].update(path=[48,51]),lambda s:s['conveyors']['routes']['grain'].update(delivered=-1),
            lambda s:s['conveyors']['routes']['grain'].update(feeding='on')]
        for mutate in mutations:
            bad=deepcopy(state);mutate(bad)
            with self.assertRaises(GameError):validate_factory(bad)

    def test_layout_requires_removing_connected_empty_tracks(self):
        state=world();before=deepcopy(state)
        with self.assertRaises(GameError):layout.configure(state,{n:layout.COMPACT[n] for n in ('mill','oven')})
        self.assertEqual(state,before)
        conveyors.configure(state,False,{})
        layout.configure(state,{n:layout.COMPACT[n] for n in ('mill','oven')})
        conveyors.configure(state,True,plan(state))
        self.assertEqual(validate_factory(state),state)
        recycling.configure(state,True);self.assertEqual(validate_factory(state),state)

    def test_classic_trials_and_order_builds_reject_but_order_feed_actions_work(self):
        for state in (new_state(),challenges.start('rush',1)):
            with self.assertRaises(GameError):conveyors.configure(state,True,{})
        state=challenges.start('rush',1);state['conveyors']={'version':1,'enabled':False,'routes':{}}
        with self.assertRaises(GameError):validate_factory(state)
        state=world();state['stats']['bread_delivered']=4;farm=Factory(state);farm.start_order();before=farm.snapshot()
        with self.assertRaises(GameError):conveyors.configure(farm.state,False,plan(farm.state))
        self.assertEqual(farm.state,before)
        farm.action('set_conveyor_feed','grain',False)
        self.assertEqual(farm.state['tick'],1)

    def test_sales_and_order_final_tick_and_missions_resolve_once(self):
        state=world(('bread',));state['stats']['bread_delivered']=4
        farm=Factory(state);farm.start_order()
        farm.state['tick']=179;farm.state['stats']['bread_delivered']=15
        route=conveyors.get_route(farm.state,'bread');route.update(slots=[0,0,0,1],picked=1)
        farm.action('wait')
        self.assertEqual(farm.state['order']['status'],'complete')
        self.assertEqual(farm.state['order']['best'],180)
        self.assertEqual(farm.state['stats']['bread_delivered'],16)
        coins=farm.state['coins'];farm.action('wait');self.assertEqual(farm.state['coins'],coins)

    def test_feed_and_query_api_is_bounded_strict_and_atomic(self):
        state=world();result=run_script('set_conveyor_feed("grain", False)\nprint(conveyor_status("grain"), conveyor_items("grain"))',state)
        self.assertIsNone(result['error']);self.assertEqual(result['actions'],1)
        self.assertEqual(result['frames'][-1]['message'],'drained 0')
        for code in ['set_conveyor_feed("grain", 1)','set_conveyor_feed("unknown", True)','set_conveyor_feed("grain")','conveyor_items("wrong")']:
            result=run_script(code,state);self.assertIsNotNone(result['error']);self.assertEqual(result['actions'],0)
        self.assertIsNotNone(run_script('set_conveyor_feed("grain", True)',new_factory())['error'])
        self.assertIsNotNone(run_script('conveyor_items("grain")',new_state())['error'])
        result=run_script('print(conveyor_status("grain"), conveyor_items("grain"))',new_factory())
        self.assertEqual(result['frames'][-1]['message'],'not_installed 0')

    def test_team_belts_advance_once_and_remote_gate_conflicts_alternate(self):
        result=step_team([WAIT,WAIT],world(('grain',)))
        route=conveyors.get_route(result['state'],'grain')
        self.assertEqual(result['state']['tick'],1);self.assertEqual(route['picked'],1)
        for tick,expected in ((0,False),(1,True)):
            state=enable_team(world(('grain',)));state['tick']=tick
            state['team']['drone']={'x':7,'y':7}
            result=step_team(['set_conveyor_feed("grain",False)','set_conveyor_feed("grain",True)'],state)
            self.assertIsNone(result['error']);self.assertEqual(result['actions'],1)
            self.assertEqual(conveyors.get_route(result['state'],'grain')['feeding'],expected)
            self.assertEqual(sum(result['state']['team']['blocked']),1)
        result=step_team(['set_conveyor_feed("grain",False)','set_conveyor_feed("flour",False)'],world())
        self.assertEqual(result['actions'],2)

    def test_solo_team_portable_queue_checkpoints_and_retry_match(self):
        for execution in ('continuous','team'):
            state=world();result=step_team([WAIT,WAIT],state) if execution=='team' else step_script(WAIT,state)
            game={'state':result['state'],'code':WAIT,'speed':'8','execution':execution,'checkpoint':result['checkpoint']}
            if execution=='team':game['team_code']=WAIT
            save={'format':'sprout-save','version':2,'active':'factory','games':{'factory':game}}
            self.assertEqual(validate_save(json.loads(json.dumps(save))),save)
            operation=lambda:step_team([WAIT,WAIT],game['state'],game['checkpoint']) if execution=='team' else step_script(WAIT,game['state'],game['checkpoint'])
            second=operation();self.assertEqual(second,operation());self.assertIsNone(second['error'])
            self.assertEqual(conveyors.get_route(second['state'],'grain')['slots'],[1,1,0])
            self.assertEqual(total(second['state']),12)

    def test_invalid_team_command_does_not_advance_or_mutate_queued_stock(self):
        first=step_team([WAIT,WAIT],world())
        state=first['state'];before=deepcopy(state)
        result=step_team([WAIT,'set_conveyor_feed("grain", 1)'],state)
        self.assertIsNotNone(result['error']);self.assertEqual(result['state'],before)
        self.assertEqual(state,before)

    def test_bakery_demo_and_long_detour_preserve_every_frame(self):
        code=(EXAMPLES/'factory_conveyors.py').read_text()
        for compact in (False,True):
            state=new_factory()
            if compact:layout.configure(state,{n:layout.COMPACT[n] for n in ('mill','oven')})
            config=plan(state)
            if not compact:config['grain']['path']=[48,56,57,58,59,51]
            conveyors.configure(state,True,config);result=run_script(code,state)
            self.assertIsNone(result['error'])
            for frame in result['frames']:
                if 'state' in frame:self.assertEqual(total(frame['state']),12);self.assertEqual(validate_factory(frame['state']),frame['state'])
            final=next(f['state'] for f in reversed(result['frames']) if 'state' in f)
            self.assertGreaterEqual(final['stats']['bread_delivered'],4)

    def test_farmer_sustains_all_care_options_with_and_without_recycling(self):
        code=(EXAMPLES/'factory_conveyor_loop.py').read_text()
        for options in product((False,True),repeat=3):
            for recycled in (False,True):
                state=world();cultivation.configure(state,dict(zip(('fertilizer','irrigation','soil'),options)))
                if recycled:recycling.configure(state,True)
                cp=None
                for _ in range(650):
                    result=step_script(code,state,cp);self.assertIsNone(result['error'],(options,recycled,result['error']))
                    state,cp=result['state'],result['checkpoint']
                    self.assertGreaterEqual(state['chest']['wheat'],4)
                self.assertGreater(state['stats']['bread_delivered'],8)
                self.assertEqual(validate_factory(state),state)
                if recycled:self.assertEqual(recycling.material_total(state),2*state['recycling']['stats']['residue_collected'])
