"""Bounded bakery belts: one item per segment, one hop per shared phase."""
from collections import deque
from .common import GameError, integer
from . import stock_policy, bread_routing

BAKERY_ROUTES=('grain','flour','bread')

ROUTES = {
    'grain': {'title': 'Grain feed', 'source': 'chest', 'target': 'mill', 'item': 'wheat'},
    'flour': {'title': 'Flour transfer', 'source': 'mill', 'target': 'oven', 'item': 'flour'},
    'bread': {'title': 'Bread delivery', 'source': 'oven', 'target': 'depot', 'item': 'bread'},
    'bread_store': {'title': 'Bread storage', 'source': 'oven', 'target': 'chest', 'item': 'bread'},
}
RULES = {'version': 1, 'routes': ROUTES, 'bakery_routes':BAKERY_ROUTES, 'max_path': 32, 'capacity': 1, 'stock_policy':stock_policy.RULES, 'bread_routing':bread_routing.RULES}


def stations(state):
    from . import layout
    return layout.entities(state, layout.defaults())


def validate_path(state, name, raw):
    from .factory import walkable, farmland
    if name not in ROUTES or not isinstance(raw, list) or not 2 <= len(raw) <= RULES['max_path']:
        raise GameError('Choose a bakery route with 2–32 connected pads.')
    path = [integer(cell, 0, 63, 'conveyor pad') for cell in raw]
    buildings = stations(state); rule = ROUTES[name]
    index = lambda d: d['y'] * 8 + d['x']
    if path[0] != index(buildings[rule['source']]) or path[-1] != index(buildings[rule['target']]):
        raise GameError(f"Connect {rule['source']} to {rule['target']} for the {name} conveyor.")
    if len(set(path)) != len(path):
        raise GameError('Conveyors cannot loop or repeat a pad.')
    occupied = {index(d) for d in buildings.values()}
    for i, cell in enumerate(path):
        x, y = cell % 8, cell // 8
        if not walkable(x, y) or farmland(x, y) or i not in (0, len(path)-1) and cell in occupied:
            raise GameError('Route belts along lanes, away from crops, rocks and other building pads.')
        if i and abs(x-path[i-1]%8)+abs(y-path[i-1]//8) != 1:
            raise GameError('Conveyor pads must touch north, south, east or west.')
    return path


def auto_path(state, name):
    """Deterministic editor suggestion; no movement or inventory mutation."""
    from .factory import walkable, farmland
    if name not in ROUTES: raise GameError('Choose grain, flour or bread.')
    buildings = stations(state); rule = ROUTES[name]
    index = lambda d: d['y'] * 8 + d['x']
    start, end = (index(buildings[rule[k]]) for k in ('source', 'target'))
    occupied = {index(d) for d in buildings.values()} - {start, end}
    queue = deque([[start]]); seen = {start}
    while queue:
        path = queue.popleft(); cell = path[-1]
        if cell == end: return validate_path(state, name, path)
        if len(path) >= RULES['max_path']: continue
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
            x,y = cell%8+dx, cell//8+dy; point = y*8+x
            if walkable(x,y) and not farmland(x,y) and point not in occupied and point not in seen:
                seen.add(point); queue.append(path+[point])
    raise GameError('No conveyor route fits this layout. Move machines or draw another route.')


def validate(raw, state):
    if not isinstance(raw, dict) or set(raw) not in ({'version','enabled','routes'},{'version','enabled','routes','routing'}) or type(raw['version']) is not int or raw['version'] != 1 or type(raw['enabled']) is not bool:
        raise GameError('Unsupported or malformed conveyors.')
    routes = raw['routes']
    if not isinstance(routes, dict) or len(routes) > 4:
        raise GameError('A bakery supports at most four conveyor routes.')
    clean = {'version':1, 'enabled':raw['enabled'], 'routes':{}}
    for name, route in routes.items():
        if not isinstance(route, dict) or set(route) not in ({'path','feeding','slots','picked','delivered'}, {'path','feeding','slots','picked','delivered','policy'}) or type(route['feeding']) is not bool:
            raise GameError('Malformed conveyor route or feed switch.')
        path = validate_path(state, name, route['path'])
        if not isinstance(route['slots'], list) or len(route['slots']) != len(path)-1:
            raise GameError('Conveyor slots must match its route segments.')
        slots = [integer(value,0,1,'segment inventory') for value in route['slots']]
        picked = integer(route['picked'],0,10**9,'conveyor pickups')
        delivered = integer(route['delivered'],0,picked,'conveyor arrivals')
        if picked-delivered != sum(slots) or name == 'bread' and delivered > state['stats']['bread_delivered']:
            raise GameError('Conveyor pickups, queued items and arrivals must balance.')
        clean['routes'][name] = {'path':path,'feeding':route['feeding'],'slots':slots,'picked':picked,'delivered':delivered}
        if 'policy' in route: clean['routes'][name]['policy']=stock_policy.validate(route['policy'],name)
    if 'bread_store' in routes or 'routing' in raw:
        clean['routing']=bread_routing.validate(raw.get('routing'),routes)
        if 'bread_store' not in routes:raise GameError('A bread dispatcher needs its storage branch.')
    return clean


def configure(state, enabled, routes):
    if state.get('scenario') != 'factory' or 'challenge' in state:
        raise GameError('Conveyors belong to your Breadworks campaign; challenges keep fixed rules.')
    if state['order']['status'] == 'active':
        raise GameError('Finish the active order before rebuilding or configuring conveyors. Python feed switches remain available.')
    if type(enabled) is not bool or not isinstance(routes, dict) or len(routes) > 4:
        raise GameError('Choose a conveyor on/off option and up to four routes.')
    old = state.get('conveyors', {}).get('routes', {}); planned = {}
    for name, route in routes.items():
        if not isinstance(route, dict) or set(route) not in ({'path','feeding'},{'path','feeding','policy'}) or type(route['feeding']) is not bool:
            raise GameError('Each planned route needs path and a boolean feeding switch.')
        path = validate_path(state, name, route['path'])
        previous = old.get(name)
        planned[name] = dict(previous, feeding=route['feeding']) if previous and previous['path'] == path else {
            'path':path,'feeding':route['feeding'],'slots':[0]*(len(path)-1),'picked':0,'delivered':0}
        if previous and 'policy' in previous: planned[name]['policy']=dict(previous['policy'])
        if 'policy' in route:
            if route['policy'] is None: planned[name].pop('policy',None)
            else: planned[name]['policy']=stock_policy.validate(route['policy'],name)
    for name, previous in old.items():
        if sum(previous['slots']) and (name not in planned or planned[name]['path'] != previous['path']):
            raise GameError('Stop feeding and run until queued items drain before removing or rerouting a conveyor.')
    routing=None
    if 'bread_store' in planned:
        routing=bread_routing.validate(state.get('conveyors',{}).get('routing',{'version':1,'mode':'sell','next':'bread'}),planned)
    if 'conveyors' not in state and not enabled and not planned:
        return 'Conveyors remain off.'
    state['conveyors'] = {'version':1,'enabled':enabled,'routes':planned}
    if routing:state['conveyors']['routing']=routing
    return 'Conveyor plan saved. Stock is kept; belts move during farm ticks.' if enabled else 'Conveyors paused. All queued items are kept.'


def source(state, name):
    rule = ROUTES[name]
    return (state['chest'], rule['item']) if name == 'grain' else (state['machines'][rule['source']], 'output')


def accepts(state, name):
    if name == 'bread': return True
    if name == 'bread_store':return sum(state['chest'].values())<48
    target = ROUTES[name]['target']
    return state['machines'][target]['input'] < stations(state)[target]['input_capacity']


def advance(state):
    from .factory import ENTITIES
    line = state.get('conveyors')
    if not line or not line['enabled']: return
    for name in ROUTES:  # Stable order; newly baked products await the next phase.
        route = line['routes'].get(name)
        if not route: continue
        old = route['slots'][:]; slots = old[:]
        if old[-1] and accepts(state, name):
            slots[-1] = 0; route['delivered'] += 1
            if name == 'bread':
                price=ENTITIES['depot']['price']
                state['coins'] += price; state['stats']['earned'] += price; state['stats']['bread_delivered'] += 1
            elif name=='bread_store':
                state['chest']['bread']+=1
            else:
                state['machines'][ROUTES[name]['target']]['input'] += 1
        for i in range(len(slots)-1, 0, -1):
            if old[i-1] and not slots[i]: slots[i] = 1; slots[i-1] = 0
        route['slots']=slots
    def pickup(name):
        route=line['routes'].get(name)
        if not route or route['slots'][0] or stock_policy.intake_status(state,name,route)!='ready':return False
        bag,key=source(state,name)
        bag[key]-=1;route['slots'][0]=1;route['picked']+=1
        return True
    # All old stock moves before any pickups; the oven dispatches only one loaf.
    for name in ('grain','flour'):pickup(name)
    for name in bread_routing.order(state):
        if pickup(name):bread_routing.picked(state,name);break


def get_route(state, name):
    if type(name) is not str or name not in ROUTES: raise GameError('Choose grain, flour, bread or bread_store.')
    return state.get('conveyors', {}).get('routes', {}).get(name)


def status(state, name):
    route = get_route(state, name)
    if not route: return 'not_installed'
    if not state['conveyors']['enabled']: return 'paused'
    if route['slots'][-1] and not accepts(state,name): return 'blocked'
    if sum(route['slots']): return 'moving'
    if not route['feeding']: return 'drained'
    return stock_policy.intake_status(state,name,route)


def set_feed(state, name, value):
    route = get_route(state,name)
    if route is None: raise GameError('Build that conveyor in the Conveyor workshop first.')
    if type(value) is not bool: raise GameError('Use True or False for a conveyor feed switch.')
    route['feeding'] = value
    return f"{name.capitalize()} conveyor feed {'on' if value else 'off; queued items will drain'}"
