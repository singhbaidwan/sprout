"""Validate portable chapters, isolated trials, and legacy save envelopes."""

from .engine import GameError
from .world import validate_game
from .continuous import validate_checkpoint
from .team import validate_team_checkpoint
from . import challenges


def validate_saved_game(game, name, trial=False):
    if not isinstance(game, dict):
        raise GameError('A saved chapter must be an object.')
    code, speed = game.get('code'), game.get('speed')
    if type(code) is not str or len(code) > 16000:
        raise GameError('Saved programs must be text under 16,000 characters.')
    if type(speed) is not str or speed not in ('1', '2', '4', '8'):
        raise GameError('Invalid playback speed in this save.')
    state = validate_game(game.get('state'))
    if state.get('scenario', 'classic') != name or ('challenge' in state) != trial:
        raise GameError('The saved world does not match its chapter or challenge.')
    clean = {'state': state, 'code': code, 'speed': speed}
    execution = game.get('execution', 'finite')
    if type(execution) is not str or execution not in ('finite', 'continuous', 'team'):
        raise GameError('Invalid controller mode in this save.')
    if execution == 'team' and name != 'factory':
        raise GameError('Drone teams belong to the Breadworks chapter.')
    if trial:
        challenges.execution(state, 2 if execution == 'team' else 1)
    team_code = game.get('team_code', 'while True:\n    wait()')
    if type(team_code) is not str or len(team_code) > 16000:
        raise GameError('The second drone program must be under 16,000 characters.')
    if 'team_code' in game:
        clean['team_code'] = team_code
    if 'execution' in game:
        clean['execution'] = execution
    if game.get('checkpoint') is not None:
        if challenges.terminal(state):
            raise GameError('A finished challenge cannot have a controller checkpoint.')
        if execution == 'team':
            clean['checkpoint'] = validate_team_checkpoint([code, team_code], state, game['checkpoint'])
        elif execution != 'continuous':
            raise GameError('A checkpoint requires continuous mode.')
        else:
            clean['checkpoint'] = validate_checkpoint(code, state, game['checkpoint'])
    return clean


def validate_save(raw):
    if not isinstance(raw, dict):
        raise GameError('Expected a Sprout save object.')
    if type(raw.get('version')) is int and raw['version'] == 1:
        raw = {'format': 'sprout-save', 'version': 2, 'active': 'classic', 'games': {'classic': raw}}
    if raw.get('format') != 'sprout-save' or type(raw.get('version')) is not int or raw['version'] != 2:
        raise GameError('This save format or version is not supported.')
    games = raw.get('games')
    if not isinstance(games, dict) or not games or set(games) - {'classic', 'factory'}:
        raise GameError('The save contains an unknown or missing chapter.')
    active = raw.get('active')
    if type(active) is not str or active not in games:
        raise GameError('The active chapter is missing.')
    clean = {'format': 'sprout-save', 'version': 2, 'active': active, 'games': {}}
    for name, game in games.items():
        clean['games'][name] = validate_saved_game(game, name)
    if 'trial' in raw:
        trial = raw['trial']
        if not isinstance(trial, dict) or type(trial.get('active')) is not bool or trial['active'] and active != 'factory':
            raise GameError('Invalid challenge session.')
        if 'factory' not in games:
            raise GameError('A challenge needs its saved Breadworks campaign.')
        if type(trial.get('recorded', False)) is not bool:
            raise GameError('Invalid challenge record marker.')
        game = validate_saved_game(trial.get('game'), 'factory', trial=True)
        if trial.get('recorded', False) and not challenges.terminal(game['state']):
            raise GameError('An active challenge cannot have a recorded result.')
        clean['trial'] = {'active': trial['active'], 'recorded': trial.get('recorded', False), 'game': game}
    if 'challenge_records' in raw:
        clean['challenge_records'] = challenges.validate_records(raw['challenge_records'])
    if clean.get('trial', {}).get('recorded'):
        state = clean['trial']['game']['state']
        key = f"{state['challenge']['id']}:{state['challenge']['drones']}"
        if clean.get('challenge_records', {}).get(key, {}).get('last') != challenges.score(state):
            raise GameError('The recorded challenge result is missing or mismatched.')
    return clean
