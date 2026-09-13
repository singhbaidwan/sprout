"""Optional crop care. Disabling a system suspends its rules, retaining equipment."""

from .common import GameError, integer

FEATURES = {
    'fertilizer': {'title': 'Fertilizer', 'description': 'Feed growing crops for faster growth and a richer harvest.'},
    'irrigation': {'title': 'Irrigation', 'description': 'Build sprinklers and automate a shared water tank.'},
    'soil': {'title': 'Soil health', 'description': 'Harvests use nutrients. Turn crop residue into compost.'},
}
GOALS = [
    {'id': 'feed_six', 'title': 'Feed the field', 'stat': 'fertilized', 'target': 6, 'reward': 20},
    {'id': 'water_network', 'title': 'Water without footsteps', 'stat': 'irrigated', 'target': 36, 'reward': 25},
    {'id': 'close_cycle', 'title': 'Give back to the soil', 'stat': 'composted', 'target': 6, 'reward': 30},
]
RULES = {'features': FEATURES, 'goals': GOALS, 'tank_capacity': 60, 'manual_water_cost': 2,
         'sprinkler_cost': 8, 'sprinkler_limit': 9, 'sprinkler_interval': 6, 'sprinkler_moisture': 12,
         'fertilizer_cost': 2, 'fertilizer_limit': 100, 'boost_ticks': 6,
         'poor_soil': 30, 'compost_restore': 40}
ACTIONS = {'fertilize', 'compost', 'buy_fertilizer', 'install_sprinkler', 'refill_tank', 'set_irrigation'}
QUERIES = {'feature_enabled', 'get_nutrients', 'get_supply', 'has_sprinkler', 'is_fertilized', 'get_yield', 'get_scenario'}


def new_plot():
    return {'nutrients': 100, 'boost': 0, 'fertilized': False}


def new_care(size):
    return {'version': 1, 'settings': dict.fromkeys(FEATURES, False), 'plots': [new_plot() for _ in range(size * size)],
            'fertilizer': 6, 'compost': 0, 'tank': 60, 'pump': True, 'sprinklers': [],
            'stats': dict.fromkeys(('fertilized', 'irrigated', 'composted', 'bonus'), 0), 'completed': []}


def growing(state, x, y):
    return 0 <= x < (6 if state.get('scenario') == 'factory' else state['size']) and 0 <= y < (4 if state.get('scenario') == 'factory' else state['size'])


def position(state):
    return state['drone']['y'] * state['size'] + state['drone']['x']


def validate_care(raw, state):
    try:
        if not isinstance(raw, dict) or type(raw.get('version')) is not int or raw['version'] != 1:
            raise GameError('Unsupported crop-care save version.')
        care = new_care(state['size'])
        for name in FEATURES:
            if type(raw['settings'][name]) is not bool:
                raise GameError('Growing options must be on or off.')
            care['settings'][name] = raw['settings'][name]
        if not isinstance(raw['plots'], list) or len(raw['plots']) != state['size'] ** 2:
            raise GameError('Invalid soil map.')
        care['plots'] = []
        for index, plot in enumerate(raw['plots']):
            if type(plot['fertilized']) is not bool:
                raise GameError('Invalid fertilizer flag.')
            item = {'nutrients': integer(plot['nutrients'], 0, 100, 'soil nutrients'),
                    'boost': integer(plot['boost'], 0, RULES['boost_ticks'], 'fertilizer boost'), 'fertilized': plot['fertilized']}
            if (item['boost'] and not item['fertilized']) or (item['fertilized'] and not state['tiles'][index]['crop']):
                raise GameError('Saved fertilizer must belong to a crop.')
            if not growing(state, index % state['size'], index // state['size']) and item != new_plot():
                raise GameError('Soil care must stay inside the growing field.')
            care['plots'].append(item)
        for name, limit in [('fertilizer', 100), ('compost', 1000), ('tank', RULES['tank_capacity'])]:
            care[name] = integer(raw[name], 0, limit, name)
        if type(raw['pump']) is not bool:
            raise GameError('Invalid irrigation pump state.')
        care['pump'] = raw['pump']
        if not isinstance(raw['sprinklers'], list) or len(raw['sprinklers']) > RULES['sprinkler_limit']:
            raise GameError('Too many sprinklers.')
        care['sprinklers'] = [integer(index, 0, state['size'] ** 2 - 1, 'sprinkler position') for index in raw['sprinklers']]
        if len(set(care['sprinklers'])) != len(care['sprinklers']) or any(not growing(state, i % state['size'], i // state['size']) for i in care['sprinklers']):
            raise GameError('Sprinklers need distinct growing plots.')
        care['stats'] = {key: integer(raw['stats'][key], 0, 10**9, key) for key in care['stats']}
        completed = raw['completed']
        if not isinstance(completed, list) or len(completed) > len(GOALS) or any(type(name) is not str or name not in [g['id'] for g in GOALS] for name in completed) or len(set(completed)) != len(completed):
            raise GameError('Invalid growing goal progress.')
        if any(care['stats'][g['stat']] < g['target'] for g in GOALS if g['id'] in completed):
            raise GameError('Growing goals do not match statistics.')
        care['completed'] = list(completed)
        return care
    except (KeyError, TypeError, IndexError) as exc:
        raise GameError('This crop-care save is incomplete or malformed.') from exc


def configure(state, settings):
    if not isinstance(settings, dict) or set(settings) != set(FEATURES) or any(type(value) is not bool for value in settings.values()):
        raise GameError('Choose on/off values for fertilizer, irrigation, and soil health.')
    state['care']['settings'] = dict(settings)
    return 'Growing options updated. Existing equipment, supplies, and soil are kept.'


def irrigate(state):
    care = state['care']
    if not care['settings']['irrigation'] or not care['pump'] or state['tick'] % RULES['sprinkler_interval']:
        return
    for index in care['sprinklers']:
        x, y = index % state['size'], index // state['size']
        targets = [ny * state['size'] + nx for ny in range(y - 1, y + 2) for nx in range(x - 1, x + 2)
                   if growing(state, nx, ny) and state['tiles'][ny * state['size'] + nx]['water'] < RULES['sprinkler_moisture']]
        if targets and care['tank']:
            care['tank'] -= 1
            for target in targets:
                state['tiles'][target]['water'] = RULES['sprinkler_moisture']
            care['stats']['irrigated'] += len(targets)


def growth_amount(state, index):
    care, plot = state['care'], state['care']['plots'][index]
    if care['settings']['soil'] and plot['nutrients'] < RULES['poor_soil'] and state['tick'] % 2:
        return 0
    return 1 + int(care['settings']['fertilizer'] and plot['boost'] > 0)


def after_growth(state):
    care = state['care']
    if care['settings']['fertilizer']:
        for plot in care['plots']:
            plot['boost'] = max(0, plot['boost'] - 1)


def quality(state):
    return state['care']['settings']['fertilizer'] and state['care']['plots'][position(state)]['fertilized']


def harvest_yield(state):
    return 3 + int(quality(state)) if state.get('scenario') == 'factory' else 1


def harvested(state, crop):
    care, plot = state['care'], state['care']['plots'][position(state)]
    if quality(state):
        care['stats']['bonus'] += 1
    if care['settings']['soil']:
        plot['nutrients'] = max(0, plot['nutrients'] - {'wheat': 20, 'carrot': 30, 'sunflower': 15}[crop])
        care['compost'] = min(1000, care['compost'] + 1)
    plot.update(boost=0, fertilized=False)


def goals(state, events):
    care = state['care']
    for goal in GOALS:
        if goal['id'] not in care['completed'] and care['stats'][goal['stat']] >= goal['target']:
            care['completed'].append(goal['id']); state['coins'] += goal['reward']
            events.append(f"Growing goal: {goal['title']}! +{goal['reward']} coins")


def action(farm, name, args):
    state, care = farm.state, farm.state['care']
    index = position(state); plot = care['plots'][index]
    feature = 'fertilizer' if name in ('fertilize', 'buy_fertilizer') else 'soil' if name == 'compost' else 'irrigation'
    if not care['settings'][feature]:
        raise GameError(f"Enable {FEATURES[feature]['title']} in Growing options to use {name}().")
    if name in ('buy_fertilizer', 'set_irrigation'):
        if len(args) != 1:
            raise GameError(f'{name}() expects one argument.')
    elif args:
        raise GameError(f'{name}() takes no arguments.')
    if name in ('fertilize', 'compost', 'install_sprinkler') and not growing(state, **state['drone']):
        raise GameError('This action needs a growing plot.')
    if name in ('buy_fertilizer', 'refill_tank') and state['drone'] != {'x': 0, 'y': 0}:
        raise GameError('Visit the supply well at (0, 0) first.')
    if name == 'fertilize':
        if not farm.tile['crop'] or farm.ready():
            raise GameError('Fertilize a growing crop before it is ripe.')
        if plot['fertilized']:
            raise GameError('This crop is already fertilized.')
        if care['fertilizer'] < 1:
            raise GameError('No fertilizer left. Use buy_fertilizer(amount) at (0, 0).')
        care['fertilizer'] -= 1; care['stats']['fertilized'] += 1
        plot.update(boost=RULES['boost_ticks'], fertilized=True, nutrients=min(100, plot['nutrients'] + 10))
        return 'Fed crop · faster growth and a richer harvest'
    if name == 'compost':
        if not care['compost']:
            raise GameError('No compost yet. Harvest crops with Soil health on to collect residue.')
        if plot['nutrients'] == 100:
            raise GameError('This soil already has full nutrients.')
        care['compost'] -= 1; care['stats']['composted'] += 1
        plot['nutrients'] = min(100, plot['nutrients'] + RULES['compost_restore'])
        return 'Composted soil · restored up to 40 nutrients'
    if name == 'buy_fertilizer':
        amount = integer(args[0], 1, 100, 'fertilizer amount'); price = amount * RULES['fertilizer_cost']
        if care['fertilizer'] + amount > RULES['fertilizer_limit']:
            raise GameError('The supply shed can hold 100 fertilizer.')
        if state['coins'] < price:
            raise GameError(f'You need {price} coins for that fertilizer.')
        state['coins'] -= price; care['fertilizer'] += amount
        return f'Bought {amount} fertilizer for {price} coins'
    if name == 'install_sprinkler':
        if index in care['sprinklers']:
            raise GameError('A sprinkler is already installed here.')
        if len(care['sprinklers']) >= RULES['sprinkler_limit']:
            raise GameError('This field supports at most 9 sprinklers.')
        if state['coins'] < RULES['sprinkler_cost']:
            raise GameError('A sprinkler costs 8 coins.')
        state['coins'] -= RULES['sprinkler_cost']; care['sprinklers'].append(index)
        return 'Installed sprinkler · covers this plot and its eight neighbors'
    if name == 'refill_tank':
        care['tank'] = RULES['tank_capacity']
        return 'Refilled shared irrigation tank to 60 water'
    if type(args[0]) is not bool:
        raise GameError('Use set_irrigation(True) or set_irrigation(False).')
    care['pump'] = args[0]
    return 'Irrigation pump ' + ('on' if args[0] else 'off')


def query(state, name, args):
    arity = 1 if name in ('feature_enabled', 'get_supply') else 0
    if len(args) != arity:
        raise GameError(f'{name}() expects {arity} arguments.')
    care, plot = state['care'], state['care']['plots'][position(state)]
    if name == 'feature_enabled':
        if type(args[0]) is not str or args[0] not in FEATURES:
            raise GameError('Choose fertilizer, irrigation, or soil.')
        return care['settings'][args[0]]
    if name == 'get_supply':
        if type(args[0]) is not str or args[0] not in ('fertilizer', 'compost', 'water'):
            raise GameError('Choose fertilizer, compost, or water.')
        return care['tank' if args[0] == 'water' else args[0]]
    return {'get_nutrients': plot['nutrients'], 'has_sprinkler': position(state) in care['sprinklers'],
            'is_fertilized': plot['fertilized'], 'get_yield': harvest_yield(state),
            'get_scenario': state.get('scenario', 'classic')}[name]


def expand(state, old_size):
    care = state['care']; old = care['plots']; size = state['size']
    care['plots'] = [old[y * old_size + x] if x < old_size and y < old_size else new_plot() for y in range(size) for x in range(size)]
    care['sprinklers'] = [(i // old_size) * size + i % old_size for i in care['sprinklers']]
