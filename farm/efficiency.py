"""Bounded, optional measurement windows for factory optimization."""

from .common import GameError, integer

COUNTERS = ('ticks', 'commands', 'moves', 'empty_moves', 'waits', 'transfers', 'manual_waterings', 'water_used')
BUCKETS = ('working', 'starved', 'output_full')


def context(state):
    return {'tick': state['tick'], 'delivered': state['stats']['bread_delivered'],
            'tank': state['care']['tank'], 'cargo': sum(state['cargo'].values())}


def new_window(state, before=None):
    before = before or context(state)
    return {'version': 1, 'start_tick': before['tick'], 'start_delivered': before['delivered'],
            **dict.fromkeys(COUNTERS, 0), 'machines': {name: dict.fromkeys(BUCKETS, 0) for name in ('mill', 'oven')}}


def ensure(state, before=None):
    if 'efficiency' not in state:
        state['efficiency'] = new_window(state, before)
    return state['efficiency']


def record_action(state, name, before):
    metrics = ensure(state, before)
    metrics['commands'] += 1
    if name == 'move':
        metrics['moves'] += 1
        metrics['empty_moves'] += int(before['cargo'] == 0)
    elif name == 'wait':
        metrics['waits'] += 1
    elif name in ('load', 'unload'):
        metrics['transfers'] += 1
    elif name == 'water':
        metrics['manual_waterings'] += 1
        metrics['water_used'] += max(0, before['tank'] - state['care']['tank'])


def validate(raw, state):
    try:
        if not isinstance(raw, dict) or type(raw.get('version')) is not int or raw['version'] != 1:
            raise GameError('Invalid efficiency measurement version.')
        clean = {'version': 1, 'start_tick': integer(raw['start_tick'], 0, state['tick'], 'measurement start'),
                 'start_delivered': integer(raw['start_delivered'], 0, state['stats']['bread_delivered'], 'delivery baseline')}
        clean.update({key: integer(raw[key], 0, 10**9, key) for key in COUNTERS})
        if clean['start_tick'] + clean['ticks'] != state['tick'] or clean['empty_moves'] > clean['moves']:
            raise GameError('Efficiency measurements do not match this farm clock.')
        if sum(clean[key] for key in ('moves', 'waits', 'transfers', 'manual_waterings')) > clean['commands']:
            raise GameError('Invalid measured drone actions.')
        clean['machines'] = {}
        for name in ('mill', 'oven'):
            clean['machines'][name] = {key: integer(raw['machines'][name][key], 0, clean['ticks'], 'machine ticks') for key in BUCKETS}
            if sum(clean['machines'][name].values()) != clean['ticks']:
                raise GameError('Machine measurements must count each world tick once.')
        return clean
    except (KeyError, TypeError) as exc:
        raise GameError('Incomplete efficiency measurements.') from exc
