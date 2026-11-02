"""An optional shared oven dispatcher; queued destinations never change."""
from .common import GameError

BRANCHES=('bread','bread_store')
MODES=('sell','store','balanced')
RULES={'version':1,'modes':MODES,'branches':BRANCHES}


def validate(raw,routes):
    if not all(name in routes for name in BRANCHES):
        raise GameError('Build both bread delivery and bread storage routes before dispatching.')
    if not isinstance(raw,dict) or set(raw)!={'version','mode','next'} or type(raw['version']) is not int or raw['version']!=1 or raw['mode'] not in MODES or raw['next'] not in BRANCHES:
        raise GameError('Malformed bread dispatcher: choose sell, store or balanced.')
    return {'version':1,'mode':raw['mode'],'next':raw['next']}


def get_mode(state):
    return state.get('conveyors',{}).get('routing',{}).get('mode','not_installed')


def allowed(state,name):
    routing=state.get('conveyors',{}).get('routing')
    if not routing or name not in BRANCHES:return True
    return routing['mode']=='balanced' or name==('bread' if routing['mode']=='sell' else 'bread_store')


def order(state):
    routing=state.get('conveyors',{}).get('routing')
    if not routing:return ['bread']
    if routing['mode']=='sell':return ['bread']
    if routing['mode']=='store':return ['bread_store']
    return [routing['next'],BRANCHES[1] if routing['next']==BRANCHES[0] else BRANCHES[0]]


def picked(state,name):
    routing=state.get('conveyors',{}).get('routing')
    if routing and routing['mode']=='balanced':
        routing['next']='bread_store' if name=='bread' else 'bread'


def set_mode(state,mode):
    routing=state.get('conveyors',{}).get('routing')
    if not routing:raise GameError('Build both bread routes in Conveyor workshop first.')
    if type(mode) is not str or mode not in MODES:raise GameError('Use sell, store or balanced for bread routing.')
    routing['mode']=mode
    return f'Bread routing: {mode}. Queued loaves keep their destinations.'


def configure(state,mode):
    if state.get('scenario')!='factory' or 'challenge' in state:
        raise GameError('Bread routing belongs to your Breadworks campaign.')
    if state['order']['status']=='active':
        raise GameError('Finish the active order before workshop changes. Python routing actions remain available.')
    return set_mode(state,mode)
