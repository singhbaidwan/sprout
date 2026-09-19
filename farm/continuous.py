"""One-action scheduler and portable continuations for bounded farm Python.

Bytecode is always compiled from validated source, never supplied by a save.
Only values, instruction offsets and bounded call/loop stacks cross requests.
"""

import ast
import hashlib
import json
import operator

from .interpreter import (Interpreter, Function, ScriptError, ACTIONS, FACTORY_ACTIONS,
                          RESERVED, MAX_SOURCE, MAX_OPERATIONS)
from .engine import GameError
from .factory import Factory
from . import cultivation

MAX_CHECKPOINT = 48000
MAX_STACK = 2500
MAX_LOOPS = 256
COMPARISONS = {"Eq": operator.eq, "NotEq": operator.ne, "Lt": operator.lt,
               "LtE": operator.le, "Gt": operator.gt, "GtE": operator.ge,
               "In": lambda a, b: a in b, "NotIn": lambda a, b: a not in b,
               "Is": operator.is_, "IsNot": operator.is_not}


class Compiler:
    def __init__(self, tree):
        self.code = []
        self.functions = {}
        self.nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        self.block(tree.body, [])
        self.emit("halt")
        for index, node in enumerate(self.nodes):
            self.functions[index] = len(self.code)
            self.block(node.body, [])
            self.emit("const", None)
            self.emit("return")

    def emit(self, *instruction):
        self.code.append(list(instruction))
        return len(self.code) - 1

    def patch(self, indices, target):
        for index in indices:
            self.code[index][-1] = target

    def block(self, body, loops):
        for node in body:
            self.emit("line", node.lineno)
            if isinstance(node, ast.Expr):
                self.expr(node.value)
                self.emit("pop")
            elif isinstance(node, (ast.Assign, ast.AugAssign)):
                if isinstance(node, ast.Assign):
                    self.expr(node.value)
                    targets = node.targets
                else:
                    self.expr(node.target)
                    self.expr(node.value)
                    self.emit("binary", type(node.op).__name__)
                    targets = [node.target]
                for target in targets:
                    if not isinstance(target, ast.Name) or target.id in RESERVED:
                        raise ScriptError("Assign to a variable name that does not replace a farm function.", node.lineno)
                    self.emit("store", target.id)
                self.emit("pop")
            elif isinstance(node, ast.If):
                self.expr(node.test)
                branch = self.emit("branch", False, None)
                self.block(node.body, loops)
                end = self.emit("jump", None)
                self.patch([branch], len(self.code))
                self.block(node.orelse, loops)
                self.patch([end], len(self.code))
            elif isinstance(node, (ast.For, ast.While)):
                is_for = isinstance(node, ast.For)
                if is_for:
                    if not isinstance(node.target, ast.Name) or node.target.id in RESERVED:
                        raise ScriptError("A for loop needs a variable name that does not replace a farm function.", node.lineno)
                    self.expr(node.iter)
                    self.emit("for_init")
                start = len(self.code)
                self.emit("line", node.lineno)
                if is_for:
                    branch = self.emit("for_next", node.target.id, None)
                else:
                    self.expr(node.test)
                    branch = self.emit("branch", False, None)
                loop = {"start": start, "breaks": [], "for": is_for}
                self.block(node.body, loops + [loop])
                self.emit("jump", start)
                self.patch([branch], len(self.code))
                self.block(node.orelse, loops)
                self.patch(loop["breaks"], len(self.code))
            elif isinstance(node, (ast.Break, ast.Continue)):
                if not loops:
                    raise ScriptError("This control statement is outside its loop.", node.lineno)
                loop = loops[-1]
                if isinstance(node, ast.Continue):
                    self.emit("jump", loop["start"])
                else:
                    if loop["for"]:
                        self.emit("for_pop")
                    loop["breaks"].append(self.emit("jump", None))
            elif isinstance(node, ast.FunctionDef):
                self.emit("define", node.name, self.nodes.index(node))
            elif isinstance(node, ast.Return):
                self.expr(node.value) if node.value else self.emit("const", None)
                self.emit("return")

    def expr(self, node):
        if isinstance(node, ast.Constant):
            self.emit("const", node.value)
        elif isinstance(node, ast.Name):
            self.emit("load", node.id)
        elif isinstance(node, (ast.List, ast.Tuple)):
            for item in node.elts:
                self.expr(item)
            self.emit("build", isinstance(node, ast.Tuple), len(node.elts))
        elif isinstance(node, ast.BinOp):
            self.expr(node.left)
            self.expr(node.right)
            self.emit("binary", type(node.op).__name__)
        elif isinstance(node, ast.UnaryOp):
            self.expr(node.operand)
            self.emit("unary", type(node.op).__name__)
        elif isinstance(node, ast.BoolOp):
            branches = []
            for index, item in enumerate(node.values):
                self.expr(item)
                if index < len(node.values) - 1:
                    self.emit("dup")
                    branches.append(self.emit("branch", isinstance(node.op, ast.Or), None))
                    self.emit("pop")
            self.patch(branches, len(self.code))
        elif isinstance(node, ast.Compare):
            self.expr(node.left)
            branches = []
            for index, (op, item) in enumerate(zip(node.ops, node.comparators)):
                self.expr(item)
                branches.append(self.emit("compare", type(op).__name__, index == len(node.ops) - 1, None))
            self.patch(branches, len(self.code))
        elif isinstance(node, ast.Subscript):
            self.expr(node.value)
            self.expr(node.slice)
            self.emit("subscript")
        elif isinstance(node, ast.Call):
            for arg in node.args:
                self.expr(arg)
            self.emit("line", node.lineno)
            self.emit("call", node.func.id, len(node.args))
        else:
            raise ScriptError("Unsupported expression.", getattr(node, "lineno", 1))


class ContinuousInterpreter(Interpreter):
    def __init__(self, source, state=None, checkpoint=None):
        super().__init__(state)
        if type(source) is not str or len(source) > MAX_SOURCE:
            raise ScriptError("Scripts must be text under 16,000 characters.")
        tree = ast.parse(source)
        self.validate(tree)
        self.program = Compiler(tree)
        self.digest = hashlib.sha256(source.encode()).hexdigest()
        self.pc = 0
        self.values = []
        self.calls = []
        self.loops = []
        self.navigation = []
        self.revision = 0
        if checkpoint is not None:
            self.restore(checkpoint)

    def consume(self):
        self.operations += 1
        if self.operations > MAX_OPERATIONS:
            raise ScriptError("Continuous mode reached 20,000 operations without a drone action. Add wait() or another action inside your loop.", self.line)

    def encode(self, value):
        if value is None or type(value) is bool:
            return value
        identity = id(value)
        if identity in self.encoded:
            return {"type": "ref", "value": self.encoded[identity]}
        index = len(self.encoded)
        self.encoded[identity] = index
        return {"type": "object", "value": [index, self.encode_value(value)]}

    def encode_value(self, value):
        if isinstance(value, Function):
            return {"type": "function", "value": self.program.nodes.index(value.node)}
        if isinstance(value, range):
            return {"type": "range", "value": [value.start, value.stop, value.step]}
        if isinstance(value, (tuple, list)):
            return {"type": "tuple" if isinstance(value, tuple) else "list", "value": [self.encode(item) for item in value]}
        return value

    def decode(self, raw, depth=0):
        if depth > 8:
            raise GameError("Checkpoint collections are nested too deeply.")
        if type(raw) in (int, float, str, bool, type(None)):
            return self.checked(raw)
        if not isinstance(raw, dict) or set(raw) != {"type", "value"}:
            raise GameError("Invalid checkpoint value.")
        kind, value = raw["type"], raw["value"]
        if kind == "ref":
            index = self.offset(value, MAX_STACK)
            if index not in self.decoded or self.decoded[index] is self.pending_value:
                raise GameError("Invalid checkpoint value reference.")
            return self.decoded[index]
        if kind == "object":
            if not isinstance(value, list) or len(value) != 2:
                raise GameError("Invalid checkpoint object.")
            index = self.offset(value[0], MAX_STACK)
            if index in self.decoded or isinstance(value[1], dict) and value[1].get("type") in ("ref", "object"):
                raise GameError("Invalid checkpoint object reference.")
            self.decoded[index] = self.pending_value
            result = self.decode(value[1], depth)
            self.decoded[index] = result
            return result
        if kind == "function":
            return Function(self.program.nodes[self.offset(value, len(self.program.nodes))])
        if kind == "range":
            if not isinstance(value, list) or len(value) != 3 or any(type(item) is not int or abs(item) > 10**9 for item in value) or value[2] == 0:
                raise GameError("Invalid checkpoint range.")
            return self.checked(range(*value))
        if kind not in ("tuple", "list") or not isinstance(value, list) or len(value) > 1000:
            raise GameError("Invalid checkpoint collection.")
        result = [self.decode(item, depth + 1) for item in value]
        return self.checked(tuple(result) if kind == "tuple" else result)

    @staticmethod
    def offset(value, limit):
        if type(value) is not int or not 0 <= value < limit:
            raise GameError("Invalid checkpoint offset.")
        return value

    def restore(self, raw):
        try:
            if not isinstance(raw, dict) or len(json.dumps(raw, ensure_ascii=True)) > MAX_CHECKPOINT:
                raise GameError("Checkpoint must be an object under 48 KB.")
            if type(raw.get("version")) is not int or raw["version"] != 1 or raw.get("source") != self.digest:
                raise GameError("Checkpoint version or program does not match. Stop to start a new controller.")
            # Bind execution to the exact saved world, not merely its tick count.
            if raw.get("world") != self.world_digest():
                raise GameError("Checkpoint does not match this farm. Stop to start a new controller.")
            self.pc = self.offset(raw["pc"], len(self.program.code))
            self.line = self.offset(raw["line"], 16002)
            self.revision = self.offset(raw["revision"], 10**9)
            for name, limit in (("values", MAX_STACK), ("scopes", 25), ("calls", 24), ("loops", MAX_LOOPS), ("navigation", 64)):
                if not isinstance(raw[name], list) or len(raw[name]) > limit:
                    raise GameError("Checkpoint stack is too large or malformed.")
            if not raw["scopes"] or len(raw["scopes"]) != len(raw["calls"]) + 1:
                raise GameError("Invalid checkpoint call stack.")
            self.decoded = {}
            self.pending_value = object()
            self.values = [self.decode(value) for value in raw["values"]]
            # Names can only refer to the bounded namespace; no host objects exist.
            self.scopes = []
            for scope in raw["scopes"]:
                if not isinstance(scope, dict) or len(scope) > 2500 or any(not isinstance(name, str) or not name.isidentifier() or name.startswith("__") or name in RESERVED for name in scope):
                    raise GameError("Invalid checkpoint variables.")
                self.scopes.append({name: self.decode(value) for name, value in scope.items()})
            self.globals = self.scopes[0]
            self.calls = []
            for call in raw["calls"]:
                if not isinstance(call, dict) or set(call) != {"pc", "base", "loops"}:
                    raise GameError("Invalid checkpoint call frame.")
                self.calls.append({"pc": self.offset(call["pc"], len(self.program.code)),
                                   "base": self.offset(call["base"], len(self.values) + 1),
                                   "loops": self.offset(call["loops"], len(raw["loops"]) + 1)})
            self.loops = []
            for loop in raw["loops"]:
                if not isinstance(loop, dict) or set(loop) != {"sequence", "index"}:
                    raise GameError("Invalid checkpoint loop.")
                sequence = self.decode(loop["sequence"])
                if not isinstance(sequence, (list, tuple, str, range)):
                    raise GameError("Invalid checkpoint loop sequence.")
                self.loops.append({"sequence": sequence, "index": self.offset(loop["index"], len(sequence) + 1)})
            if any(type(direction) is not str or direction not in ("north", "south", "east", "west") for direction in raw["navigation"]):
                raise GameError("Invalid checkpoint route.")
            self.navigation = list(raw["navigation"])
        except (KeyError, TypeError, IndexError, RecursionError) as exc:
            raise GameError("Malformed controller checkpoint.") from exc

    def world_digest(self):
        return hashlib.sha256(json.dumps(self.farm.state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def checkpoint(self):
        self.encoded = {}
        result = {"version": 1, "source": self.digest, "world": self.world_digest(), "pc": self.pc,
                  "line": self.line, "revision": self.revision,
                  "values": [self.encode(value) for value in self.values],
                  "scopes": [{key: self.encode(value) for key, value in scope.items()} for scope in self.scopes],
                  "calls": self.calls, "loops": [{"sequence": self.encode(loop["sequence"]), "index": loop["index"]} for loop in self.loops],
                  "navigation": self.navigation}
        if len(self.encoded) > MAX_STACK or len(json.dumps(result, ensure_ascii=True)) > MAX_CHECKPOINT:
            raise ScriptError("Controller memory reached 48 KB. Keep fewer or smaller variables.", self.line)
        return result

    def pop_args(self, count):
        if count > len(self.values):
            raise ScriptError("Invalid controller expression stack.", self.line)
        args = self.values[-count:] if count else []
        if count:
            del self.values[-count:]
        return args

    def action(self, name, args):
        message = self.farm.action(name, *args)
        self.actions += 1
        self.frame(message, action=name)

    def invoke(self, name, args):
        if name == "navigate_to":
            if not isinstance(self.farm, Factory):
                raise GameError("navigate_to() belongs to the Breadworks chapter.")
            self.navigation = self.farm.route(*args)
            self.values.append(None)
        elif name in ACTIONS | FACTORY_ACTIONS | cultivation.ACTIONS:
            self.action(name, args)
            self.values.append(None)
        elif name in RESERVED:
            self.values.append(super().call(name, args))
        else:
            function = self.lookup(name)
            if not isinstance(function, Function):
                raise ScriptError(f"'{name}' is not a function.", self.line)
            params = function.node.args.args
            if len(params) != len(args):
                raise ScriptError(f"{name}() expects {len(params)} arguments, got {len(args)}.", self.line)
            if len(self.scopes) >= 25:
                raise ScriptError("Function calls are nested too deeply. Use a loop instead of recursion.", self.line)
            self.calls.append({"pc": self.pc, "base": len(self.values), "loops": len(self.loops)})
            self.scopes.append(dict(zip((param.arg for param in params), args)))
            self.pc = self.program.functions[self.program.nodes.index(function.node)]

    def instruction(self, ins):
        op, *args = ins
        if op == "line":
            self.line = args[0]
        elif op == "const":
            self.values.append(self.checked(args[0]))
        elif op == "load":
            self.values.append(self.lookup(args[0]))
        elif op == "store":
            self.scopes[-1][args[0]] = self.checked(self.values[-1])
        elif op == "pop":
            self.values.pop()
        elif op == "dup":
            self.values.append(self.values[-1])
        elif op == "build":
            values = self.pop_args(args[1])
            self.values.append(self.checked(tuple(values) if args[0] else values))
        elif op == "binary":
            left, right = self.pop_args(2)
            self.values.append(self.binary(getattr(ast, args[0])(), left, right))
        elif op == "unary":
            operation = {"USub": operator.neg, "UAdd": operator.pos, "Not": operator.not_}[args[0]]
            self.values.append(self.checked(operation(self.values.pop())))
        elif op == "branch":
            if bool(self.values.pop()) == args[0]:
                self.pc = args[1]
        elif op == "jump":
            self.pc = args[0]
        elif op == "compare":
            left, right = self.pop_args(2)
            result = COMPARISONS[args[0]](left, right)
            self.values.append(bool(result) if args[1] or not result else right)
            if not result:
                self.pc = args[2]
        elif op == "subscript":
            value, index = self.pop_args(2)
            if not isinstance(value, (list, tuple, str, range)) or type(index) is not int:
                raise ScriptError("Use an integer index with a list, tuple, string, or range.", self.line)
            self.values.append(value[index])
        elif op == "define":
            self.scopes[-1][args[0]] = Function(self.program.nodes[args[1]])
        elif op == "call":
            self.invoke(args[0], self.pop_args(args[1]))
        elif op == "return":
            value = self.values.pop()
            call = self.calls.pop()
            self.scopes.pop()
            del self.values[call["base"]:]
            del self.loops[call["loops"]:]
            self.values.append(value)
            self.pc = call["pc"]
        elif op == "for_init":
            sequence = self.values.pop()
            if not isinstance(sequence, (list, tuple, str, range)):
                raise ScriptError("A for loop needs range(), a list, a tuple, or a string.", self.line)
            self.loops.append({"sequence": sequence, "index": 0})
        elif op == "for_next":
            loop = self.loops[-1]
            if loop["index"] == len(loop["sequence"]):
                self.loops.pop()
                self.pc = args[1]
            else:
                self.scopes[-1][args[0]] = loop["sequence"][loop["index"]]
                loop["index"] += 1
        elif op == "for_pop":
            self.loops.pop()

    def step(self):
        error, checkpoint, done = None, None, False
        self.revision += 1
        try:
            while not self.actions:
                self.consume()
                if len(self.values) > MAX_STACK or len(self.loops) > MAX_LOOPS:
                    raise ScriptError("Controller stack is too large. Use simpler expressions or fewer nested loops.", self.line)
                if self.navigation:
                    self.action("move", [self.navigation.pop(0)])
                    continue
                instruction = self.program.code[self.pc]
                self.pc += 1
                if instruction[0] == "halt":
                    done = True
                    break
                self.instruction(instruction)
            if not done:
                checkpoint = self.checkpoint()
        except (ScriptError, GameError, TypeError, ValueError, ZeroDivisionError, IndexError, OverflowError, RecursionError) as exc:
            error = {"message": str(exc) or "Invalid controller continuation.", "line": getattr(exc, "line", None) or self.line}
            done = True
        return {"frames": self.frames, "state": self.farm.snapshot(), "checkpoint": checkpoint,
                "revision": self.revision, "done": done, "error": error,
                "actions": self.actions, "operations": self.operations}


def step_script(source, state, checkpoint=None):
    try:
        interpreter = ContinuousInterpreter(source, state, checkpoint)
    except (SyntaxError, ScriptError) as exc:
        if checkpoint is not None:
            raise GameError(f"Invalid checkpoint program: {exc}") from exc
        return {"frames": [], "state": state, "checkpoint": None, "revision": 1, "done": True,
                "error": {"message": str(exc), "line": getattr(exc, "lineno", None) or getattr(exc, "line", None) or 1},
                "actions": 0, "operations": 0}
    return interpreter.step()


def validate_checkpoint(source, state, checkpoint):
    try:
        return ContinuousInterpreter(source, state, checkpoint).checkpoint()
    except (SyntaxError, ScriptError) as exc:
        raise GameError(f"Invalid controller checkpoint: {exc}") from exc
