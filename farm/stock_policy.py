"""Optional conveyor inventory policies; no new transport or simulation clock."""
from .common import GameError, integer

PRESET = {
    'grain': {'version':1, 'reserve':4, 'target':6},
    'flour': {'version':1, 'reserve':0, 'target':3},
    'bread': {'version':1, 'reserve':1, 'target':None},
}
RULES = {'version':1, 'preset':PRESET}


def validate(raw, name):
    from .conveyors import ROUTES
    if name not in ROUTES or not isinstance(raw,dict) or set(raw) != {'version','reserve','target'} or type(raw['version']) is not int or raw['version'] != 1:
        raise GameError('A stock policy needs version 1, reserve and target.')
    reserve=integer(raw['reserve'],0,48 if name=='grain' else 8,'source reserve')
    target=raw['target']
    if name=='bread':
        if target is not None: raise GameError('The depot sells immediately: use None for the bread target.')
    elif target is not None:
        target=integer(target,0,12,'destination target')
    return {'version':1,'reserve':reserve,'target':target}


def committed(state,name,route):
    from .conveyors import ROUTES
    from .factory import ENTITIES
    if name=='bread': return None
    target=ROUTES[name]['target'];machine=state['machines'][target]
    return machine['input']+sum(route['slots'])+(ENTITIES[target]['amount'] if machine['remaining'] else 0)


def intake_status(state,name,route):
    from .conveyors import source
    if not route['feeding']: return 'feed_off'
    policy=route.get('policy')
    if policy and policy['target'] is not None and committed(state,name,route)>=policy['target']:
        return 'target_met'
    bag,key=source(state,name)
    if not bag[key]: return 'waiting_input'
    if policy and bag[key]<=policy['reserve']: return 'reserve_held'
    return 'ready'


def set_policy(state,name,raw):
    from .conveyors import get_route
    route=get_route(state,name)
    if route is None: raise GameError('Build that conveyor before setting its stock policy.')
    policy=validate(raw,name)  # Validate everything before changing any route field.
    route['policy']=policy
    return f"{name.capitalize()} stock policy saved: reserve {policy['reserve']}, target {policy['target']}. Existing stock is kept."


def clear_policy(state,name):
    from .conveyors import get_route
    route=get_route(state,name)
    if route is None: raise GameError('Build that conveyor before clearing its stock policy.')
    route.pop('policy',None)
    return f'{name.capitalize()} stock policy cleared. Its manual feed switch is kept.'


def configure(state,raw):
    from .conveyors import get_route
    if state.get('scenario')!='factory' or 'challenge' in state:
        raise GameError('Stock policies belong to your Breadworks campaign.')
    if state['order']['status']=='active':
        raise GameError('Finish the active order before workshop configuration. Python policy actions remain available.')
    if not isinstance(raw,dict) or len(raw)>3:
        raise GameError('Choose at most three stock policy updates.')
    planned={}
    for name,policy in raw.items():
        if get_route(state,name) is None: raise GameError('Build each conveyor before configuring its stock policy.')
        planned[name]=None if policy is None else validate(policy,name)
    for name,policy in planned.items():
        if policy is None: clear_policy(state,name)
        else: set_policy(state,name,policy)
    return 'Stock policies updated. Queued items and active batches are kept; new limits apply to future pickups.'
