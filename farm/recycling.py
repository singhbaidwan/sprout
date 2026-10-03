"""Optional, conserved crop byproducts; transport uses the existing factory API."""
from .common import GameError, integer

ITEMS = ('residue', 'compost', 'fertilizer')
ENTITIES = {
    'well': {'title': 'Supply well', 'x': 0, 'y': 0},
    'composter': {'title': 'Composter', 'x': 1, 'y': 5, 'ingredient': 'residue', 'amount': 2,
                  'product': 'compost', 'output_amount': 2, 'ticks': 6, 'input_capacity': 12, 'output_capacity': 8},
    'mixer': {'title': 'Fertilizer mixer', 'x': 5, 'y': 5, 'ingredient': 'compost', 'amount': 1,
              'product': 'fertilizer', 'output_amount': 2, 'ticks': 4, 'input_capacity': 12, 'output_capacity': 8},
}
STATS = ('residue_collected', 'compost_produced', 'fertilizer_produced', 'compost_returned', 'fertilizer_returned')
RULES = {'entities': ENTITIES, 'hopper_capacity': 48, 'items': ITEMS}


def enabled(state):
    return state.get('recycling', {}).get('enabled', False)


def new_line():
    return {'version': 1, 'enabled': True, 'residue': 0,
            'machines': {name: {'input': 0, 'output': 0, 'remaining': 0} for name in ('composter', 'mixer')},
            'stats': dict.fromkeys(STATS, 0)}


def configure(state, value):
    if state.get('scenario') != 'factory' or 'challenge' in state:
        raise GameError('Recycling is available in your Breadworks campaign; challenge rules stay fixed.')
    if type(value) is not bool:
        raise GameError('Choose on or off for recycling.')
    if value and 'recycling' not in state:
        state['recycling'] = new_line()
        for bag in (state['cargo'], state['chest'], *([state['team']['cargo']] if 'team' in state else [])):
            bag.update(dict.fromkeys(ITEMS, 0))
    if 'recycling' in state:
        state['recycling']['enabled'] = value
    return 'Recycling enabled. Harvest residue feeds your new production line.' if value else 'Recycling paused. Existing materials and batches are kept.'


def check_harvest(state):
    if enabled(state) and state['recycling']['residue'] >= RULES['hopper_capacity']:
        raise GameError('The residue hopper is full. Load residue at the supply well and feed the composter before harvesting.')


def harvested(state):
    if enabled(state):
        state['recycling']['residue'] += 1
        state['recycling']['stats']['residue_collected'] += 1


def advance(state, events):
    if not enabled(state):
        return
    line = state['recycling']
    for name, machine in line['machines'].items():
        rule = ENTITIES[name]
        if not machine['remaining'] and machine['input'] >= rule['amount'] and machine['output'] + rule['output_amount'] <= rule['output_capacity']:
            machine['input'] -= rule['amount']; machine['remaining'] = rule['ticks']
        if machine['remaining']:
            machine['remaining'] -= 1
            if not machine['remaining']:
                machine['output'] += rule['output_amount']
                line['stats'][rule['product'] + '_produced'] += rule['output_amount']
                events.append(f"{rule['title']} finished {rule['output_amount']} {rule['product']}.")


def material_total(state):
    """Half-residue units: residue/compost=2, fertilizer=1, including batches/export."""
    line = state['recycling']; weights = {'residue': 2, 'compost': 2, 'fertilizer': 1}
    bags = [state['cargo'], state['chest']]
    if 'team' in state: bags.append(state['team']['cargo'])
    total = line['residue'] * 2 + sum(bag[item] * weights[item] for bag in bags for item in ITEMS)
    for name, machine in line['machines'].items():
        rule = ENTITIES[name]
        total += machine['input'] * weights[rule['ingredient']] + machine['output'] * weights[rule['product']]
        if machine['remaining']: total += rule['amount'] * weights[rule['ingredient']]
    return total + line['stats']['compost_returned'] * 2 + line['stats']['fertilizer_returned']


def validate(raw, state):
    try:
        if not isinstance(raw, dict) or type(raw.get('version')) is not int or raw['version'] != 1 or type(raw['enabled']) is not bool:
            raise GameError('Unsupported or invalid recycling state.')
        clean = new_line(); clean['enabled'] = raw['enabled']
        clean['residue'] = integer(raw['residue'], 0, RULES['hopper_capacity'], 'residue hopper')
        for name, rule in ENTITIES.items():
            if name == 'well': continue
            m = raw['machines'][name]
            clean['machines'][name] = {key: integer(m[key], 0, limit, f'{name} {key}') for key, limit in (
                ('input', rule['input_capacity']), ('output', rule['output_capacity']), ('remaining', rule['ticks'] - 1))}
            if m['remaining'] and m['output'] + rule['output_amount'] > rule['output_capacity']:
                raise GameError('A recycling batch must have room for its reserved output.')
        clean['stats'] = {key: integer(raw['stats'][key], 0, 10**9, key) for key in STATS}
        for item in ('compost', 'fertilizer'):
            if clean['stats'][item + '_returned'] > clean['stats'][item + '_produced'] or clean['stats'][item + '_produced'] % 2:
                raise GameError('Recycling production and return totals do not match.')
        if material_total(dict(state, recycling=clean)) != clean['stats']['residue_collected'] * 2:
            raise GameError('Saved recycling materials must match harvested residue, including active batches and returned supplies.')
        return clean
    except (KeyError, TypeError, IndexError) as exc:
        raise GameError('This recycling save is incomplete or malformed.') from exc
