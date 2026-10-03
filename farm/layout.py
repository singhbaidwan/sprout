"""Free, atomic workshop planning between programs; no simulation actions."""
from .common import GameError, integer

MOVABLE = ('mill', 'oven', 'composter', 'mixer')
COMPACT = {'mill': {'x': 1, 'y': 6}, 'oven': {'x': 2, 'y': 6},
           'composter': {'x': 0, 'y': 4}, 'mixer': {'x': 1, 'y': 4}}
RULES = {'version': 1, 'movable': MOVABLE, 'compact': COMPACT}


def defaults():
    # Imports stay local so the catalog can include layout rules without a cycle.
    from .factory import ENTITIES
    from .recycling import ENTITIES as RECYCLING
    return dict(ENTITIES, **RECYCLING)


def entities(state, definitions):
    positions = state.get('layout', {}).get('positions', {})
    return {name: dict(rule, **positions.get(name, {})) for name, rule in definitions.items()}


def validate_positions(raw, state):
    from .factory import farmland, walkable
    if not isinstance(raw, dict) or len(raw) > len(MOVABLE):
        raise GameError('A layout needs a bounded map of machine positions.')
    positions = {}
    for name, point in raw.items():
        if name not in MOVABLE or name in ('composter', 'mixer') and 'recycling' not in state:
            raise GameError('Move the mill, oven, or installed recycling machines. Supply stations stay fixed.')
        if not isinstance(point, dict) or set(point) != {'x', 'y'}:
            raise GameError('Each machine position needs x and y coordinates.')
        x, y = (integer(point[axis], 0, 7, 'machine coordinate') for axis in ('x', 'y'))
        if not walkable(x, y) or farmland(x, y):
            raise GameError('Place machines on a factory lane, away from crops, rocks and edges.')
        positions[name] = {'x': x, 'y': y}
    # Reserve uninstalled recycling pads too: later enablement must never overlap.
    occupied = {}
    for name, rule in defaults().items():
        point = positions.get(name, rule)
        cell = (point['x'], point['y'])
        if cell in occupied:
            raise GameError(f'That layout overlaps {occupied[cell]} and {name}. Recycling pads stay reserved until installed.')
        occupied[cell] = name
    return positions


def validate(raw, state):
    if not isinstance(raw, dict) or set(raw) != {'version', 'positions'} or type(raw['version']) is not int or raw['version'] != 1:
        raise GameError('Unsupported or malformed factory layout.')
    return {'version': 1, 'positions': validate_positions(raw['positions'], state)}


def configure(state, raw):
    if state.get('scenario') != 'factory' or 'challenge' in state:
        raise GameError('Plan layouts in your Breadworks campaign; challenge maps stay fixed.')
    if state['order']['status'] == 'active':
        raise GameError('Finish the active delivery order before changing its factory layout.')
    positions = validate_positions(raw, state)
    definitions = defaults()
    positions = {name: point for name, point in positions.items()
                 if any(point[axis] != definitions[name][axis] for axis in ('x', 'y'))}
    if positions:
        state['layout'] = {'version': 1, 'positions': positions}
    else:
        state.pop('layout', None)
    return 'Workshop layout saved. Named routes follow the new pads; stock and batches are kept.' if positions else 'Default factory layout restored. Stock and batches are kept.'
