"""Fixed, replayable local scenarios and bounded personal-record metadata."""

from .common import GameError, integer
from . import efficiency

CATALOG = {
    'rush': {'title': 'Bakery Rush', 'description': 'Turn stocked grain into 12 loaves. Keep milling and baking while you travel.',
             'target': 12, 'deadline': 180, 'water_budget': None, 'irrigation': False},
    'waterwise': {'title': 'Waterwise Harvest', 'description': 'Grow your own grain and deliver 12 loaves using at most 24 tank water. Water growing crops, then prioritize production.',
                 'target': 12, 'deadline': 500, 'water_budget': 24, 'irrigation': True},
    'buffers': {'title': 'Full Buffers', 'description': 'The chest and both outputs are full. Clear the bakery bottleneck and deliver 24 loaves.',
                'target': 24, 'deadline': 240, 'water_budget': None, 'irrigation': False},
}


def definition(identifier):
    if type(identifier) is not str or identifier not in CATALOG:
        raise GameError('Choose a known challenge: rush, waterwise, or buffers.')
    return CATALOG[identifier]


def start(identifier, drones):
    from .factory import new_factory
    from .team import enable_team
    rule = definition(identifier)
    integer(drones, 1, 2, 'challenge drone count')
    state = new_factory()
    state['coins'] = 30
    state['chest']['wheat'] = 24 if identifier == 'rush' else 48 if identifier == 'buffers' else 0
    state['care']['settings']['irrigation'] = rule['irrigation']
    state['care']['pump'] = False
    if identifier == 'waterwise':
        for x in range(6):
            state['tiles'][x].update(tilled=True, crop='wheat', growth=0, water=0)
    if identifier == 'buffers':
        state['machines']['mill'].update(input=12, output=8)
        state['machines']['oven'].update(input=12, output=8)
    if drones == 2:
        state = enable_team(state)
    state['efficiency'] = efficiency.new_window(state)
    state['challenge'] = {'version': 1, 'id': identifier, 'drones': drones, 'status': 'active'}
    return state


def outcome(state):
    challenge = state['challenge']; rule = definition(challenge['id'])
    if rule['water_budget'] is not None and state['efficiency']['water_used'] > rule['water_budget']:
        return 'failed'
    if state['stats']['bread_delivered'] >= rule['target']:
        return 'complete'
    return 'failed' if state['tick'] >= rule['deadline'] else 'active'


def advance(state, events):
    if 'challenge' not in state:
        return
    status = outcome(state)
    state['challenge']['status'] = status
    if status == 'complete':
        events.append(f"Challenge complete: {definition(state['challenge']['id'])['title']} in {state['tick']} ticks!")
    elif status == 'failed':
        reason = 'water budget exceeded' if definition(state['challenge']['id'])['water_budget'] is not None and state['efficiency']['water_used'] > definition(state['challenge']['id'])['water_budget'] else 'tick budget reached'
        events.append(f'Challenge ended: {reason}. Retry with an improved program.')


def terminal(state):
    return 'challenge' in state and state['challenge']['status'] != 'active'


def execution(state, drones):
    if 'challenge' in state and state['challenge']['drones'] != drones:
        raise GameError('This challenge has a fixed drone count. Start a new attempt to change it.')


def validate(raw, state):
    try:
        if not isinstance(raw, dict) or type(raw.get('version')) is not int or raw['version'] != 1:
            raise GameError('Unsupported challenge version.')
        rule = definition(raw['id']); drones = integer(raw['drones'], 1, 2, 'challenge drone count')
        if raw['status'] not in ('active', 'complete', 'failed') or ('team' in state) != (drones == 2):
            raise GameError('Invalid challenge team or status.')
        settings = {'fertilizer': False, 'irrigation': rule['irrigation'], 'soil': False}
        if state['care']['settings'] != settings or state['upgrades'] or state['order']['status'] != 'idle':
            raise GameError('Challenge rules and upgrades are fixed for comparable scores.')
        if 'efficiency' not in state or state['efficiency']['start_tick'] != 0 or state['efficiency']['start_delivered'] != 0 or state['tick'] > rule['deadline']:
            raise GameError('Invalid challenge measurement baseline.')
        clean = {'version': 1, 'id': raw['id'], 'drones': drones, 'status': raw['status']}
        if outcome(dict(state, challenge=clean)) != clean['status']:
            raise GameError('Challenge status does not match its progress.')
        return clean
    except (KeyError, TypeError) as exc:
        raise GameError('Malformed challenge progress.') from exc


def score(state):
    return {'status': state['challenge']['status'], 'ticks': state['tick'],
            'delivered': state['stats']['bread_delivered'],
            **{key: state['efficiency'][key] for key in ('water_used', 'empty_moves', 'moves')}}


def validate_records(raw):
    if not isinstance(raw, dict) or len(raw) > 6:
        raise GameError('Invalid challenge records.')
    clean = {}
    for key, entry in raw.items():
        if type(key) is not str or key not in {f'{name}:{drones}' for name in CATALOG for drones in (1, 2)} or not isinstance(entry, dict):
            raise GameError('Unknown challenge record.')
        rule = definition(key.split(':')[0])
        result = {'attempts': integer(entry.get('attempts'), 1, 10**9, 'challenge attempts')}
        for name in ('best', 'last', 'previous'):
            if name == 'previous' and name not in entry:
                continue
            item = entry.get(name)
            if item is None and name in ('best', 'previous'):
                result[name] = None; continue
            if not isinstance(item, dict) or item.get('status') not in ('complete', 'failed'):
                raise GameError('Invalid challenge score.')
            result[name] = {'status': item['status'], 'ticks': integer(item.get('ticks'), 1, rule['deadline'], 'challenge time'),
                            **{field: integer(item.get(field), 0, 10**9, field) for field in ('delivered', 'water_used', 'moves', 'empty_moves')}}
            value = result[name]
            if value['empty_moves'] > value['moves'] or name == 'best' and value['status'] != 'complete':
                raise GameError('Invalid challenge best score.')
            if value['status'] == 'complete' and (value['delivered'] < rule['target'] or rule['water_budget'] is not None and value['water_used'] > rule['water_budget']):
                raise GameError('A completed score must satisfy its contract.')
            if value['status'] == 'failed' and value['ticks'] < rule['deadline'] and (rule['water_budget'] is None or value['water_used'] <= rule['water_budget']):
                raise GameError('A failed score must reach a challenge budget.')
        clean[key] = result
    return clean
