"""Two bounded controllers, start-of-tick observations, one shared world tick."""

from copy import deepcopy
import hashlib
import json

from .continuous import ContinuousInterpreter, validate_checkpoint
from .engine import Farm, GameError, integer
from .factory import Factory, inventory, validate_factory
from .interpreter import ScriptError
from . import challenges


def enable_team(state):
    state = validate_factory(state)
    state.setdefault('team', {'version': 1, 'drone': {'x': 0, 'y': 6},
                              'cargo': inventory(), 'actions': [0, 0], 'blocked': [0, 0]})
    return state


def perspective(state, drone):
    result = deepcopy(state)
    if drone:
        swap_drone(result)
    return result


def swap_drone(state):
    for key in ('drone', 'cargo'):
        state[key], state['team'][key] = state['team'][key], state[key]


def binding(codes, state):
    return hashlib.sha256(json.dumps([codes, state], sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def programs(codes):
    if not isinstance(codes, list) or len(codes) != 2 or any(type(code) is not str or len(code) > 16000 for code in codes):
        raise GameError('A drone team needs two Python programs under 16,000 characters each.')


class TickFactory(Factory):
    def advance(self):
        # The scheduler calls Farm.advance once after all transfers and actions.
        pass


class Planner(ContinuousInterpreter):
    def __init__(self, source, state, checkpoint=None):
        super().__init__(source, state, checkpoint)
        self.farm = TickFactory(state)
        self.intent = None

    def action(self, name, args):
        # Validate on an isolated start-of-tick copy. No shared mutation yet.
        message = self.farm.action(name, *args)
        self.intent = (name, args, message)
        self.actions += 1


def validate_team_checkpoint(codes, state, raw):
    programs(codes)
    if 'team' not in state or not isinstance(raw, dict) or len(json.dumps(raw, ensure_ascii=True)) > 100000:
        raise GameError('Invalid drone team checkpoint.')
    if type(raw.get('version')) is not int or raw['version'] != 1 or raw.get('binding') != binding(codes, state):
        raise GameError('Team checkpoint does not match these programs and farm. Stop to restart.')
    revision = integer(raw.get('revision'), 1, 10**9 - 1, 'team revision')
    controllers = raw.get('controllers')
    if not isinstance(controllers, list) or len(controllers) != 2:
        raise GameError('A team checkpoint must contain two controllers.')
    clean = []
    for drone, entry in enumerate(controllers):
        if not isinstance(entry, dict) or type(entry.get('done')) is not bool:
            raise GameError('Invalid team controller status.')
        cp = entry.get('checkpoint')
        if entry['done']:
            if cp is not None:
                raise GameError('A finished drone cannot have a continuation.')
        else:
            if cp is None:
                raise GameError('A working drone needs a continuation.')
            cp = validate_checkpoint(codes[drone], perspective(state, drone), cp)
        clean.append({'done': entry['done'], 'checkpoint': cp})
    if all(entry['done'] for entry in clean):
        raise GameError('A finished team cannot have a checkpoint.')
    return {'version': 1, 'binding': raw['binding'], 'revision': revision, 'controllers': clean}


def step_team(codes, state, checkpoint=None):
    programs(codes)
    challenges.execution(state, 2)
    state = enable_team(state)
    previous = validate_team_checkpoint(codes, state, checkpoint) if checkpoint is not None else None
    revision = (previous['revision'] if previous else 0) + 1
    entries = previous['controllers'] if previous else [{'done': False, 'checkpoint': None} for _ in codes]
    result = {'state': state, 'checkpoint': None, 'revision': revision, 'done': False,
              'error': None, 'frames': [], 'actions': 0, 'operations': 0, 'drones': []}
    planners, before, outcomes = [], [], []
    # Compile and plan both programs before committing either drone's action.
    for drone, (code, entry) in enumerate(zip(codes, entries)):
        if entry['done']:
            planners.append(None); before.append(None); outcomes.append(None)
            continue
        try:
            vm = Planner(code, perspective(state, drone), entry['checkpoint'])
            before.append(vm.checkpoint())
            outcome = vm.step()
        except (SyntaxError, ScriptError) as exc:
            outcome = {'error': {'message': str(exc), 'line': getattr(exc, 'lineno', None) or 1}, 'operations': 0}
        result['operations'] += outcome['operations']
        if outcome['error']:
            result.update(done=True, error={**outcome['error'], 'message': f"Drone {drone + 1}: {outcome['error']['message']}", 'drone': drone})
            return result
        planners.append(vm); outcomes.append(outcome)

    farm = TickFactory(state)
    reserved, messages, committed = set(), [], [False, False]
    statuses = ['finished' if vm is None or outcomes[i]['done'] else 'working' for i, vm in enumerate(planners)]
    # Alternating priority prevents one drone permanently owning a contested pad.
    for drone in (state['tick'] % 2, 1 - state['tick'] % 2):
        vm = planners[drone]
        if vm is None or vm.intent is None:
            continue
        name, args, _ = vm.intent
        position = state['team']['drone'] if drone else state['drone']
        resource = (position['x'], position['y']) if name not in ('move', 'wait') else None
        blocked = resource is not None and resource in reserved
        if drone:
            swap_drone(farm.state)
        try:
            if not blocked:
                message = farm.action(name, *args)
                committed[drone] = True
                if resource is not None:
                    reserved.add(resource)
                messages.append({'line': vm.line, 'message': f'Drone {drone + 1}: {message}', 'kind': 'action', 'action': name, 'drone': drone})
        except GameError:
            # It was valid in the starting world: another action consumed the
            # shared resource. Retry from the pre-step VM with fresh queries.
            blocked = True
        finally:
            if drone:
                swap_drone(farm.state)
        if blocked:
            statuses[drone] = 'waiting for shared resource'
            farm.state['team']['blocked'][drone] += 1
            messages.append({'line': vm.line, 'message': f'Drone {drone + 1}: shared resource busy; retrying next tick.', 'kind': 'info', 'drone': drone})
        else:
            farm.state['team']['actions'][drone] += 1

    result['actions'] = sum(committed)
    active = any(vm and vm.intent for vm in planners)
    farm.events = []
    if active:
        Farm.advance(farm)
        # Lifetime actions count successful commands; tick counts shared rounds.
        farm.state['stats']['actions'] += max(0, result['actions'] - 1)
    result['state'] = farm.snapshot()
    for drone, vm in enumerate(planners):
        if vm and (committed[drone] or vm.intent is None):
            result['frames'].extend(dict(frame, drone=drone, message=f"Drone {drone + 1}: {frame['message']}") for frame in vm.frames)
    result['frames'].extend(messages)
    if active:
        result['frames'].append({'line': None, 'message': f"Team tick {farm.state['tick']} · {result['actions']} actions", 'kind': 'tick', 'events': farm.events})
    result['drones'] = [{'status': status, 'line': vm.line if vm else None} for status, vm in zip(statuses, planners)]
    result['done'] = challenges.terminal(result['state']) or all(status == 'finished' for status in statuses)
    if not result['done']:
        controllers = []
        try:
            for drone, vm in enumerate(planners):
                done = statuses[drone] == 'finished'
                cp = None
                if not done:
                    if not committed[drone]:
                        vm = Planner(codes[drone], perspective(state, drone), before[drone])
                    vm.farm = Factory(perspective(result['state'], drone))
                    cp = vm.checkpoint()
                controllers.append({'done': done, 'checkpoint': cp})
            result['checkpoint'] = {'version': 1, 'binding': binding(codes, result['state']), 'revision': revision, 'controllers': controllers}
        except ScriptError as exc:
            result.update(done=True, error={'message': str(exc), 'line': None}, checkpoint=None)
    return result
