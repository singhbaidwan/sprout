"""Bounded Python-subset interpreter. Player code never reaches exec/eval."""

import ast
import math
import operator
from dataclasses import dataclass

from .engine import Farm, GameError

MAX_SOURCE = 16000
MAX_NODES = 2500
MAX_DEPTH = 60
MAX_OPERATIONS = 20000
MAX_ACTIONS = 400
MAX_VALUE = 10**9
MAX_SEQUENCE = 1000

ACTIONS = {"move", "till", "plant", "water", "harvest", "wait"}
QUERIES = {"can_harvest", "get_crop", "get_water", "get_x", "get_y", "get_size", "get_coins", "is_tilled"}
BUILTINS = {"range", "len", "min", "max", "abs", "int", "str", "print"}
RESERVED = ACTIONS | QUERIES | BUILTINS
ALLOWED = (
    ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.If, ast.For,
    ast.While, ast.FunctionDef, ast.Return, ast.Break, ast.Continue, ast.Pass,
    ast.Name, ast.Load, ast.Store, ast.Constant, ast.List, ast.Tuple,
    ast.Subscript, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call,
    ast.arguments, ast.arg, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
    ast.Mod, ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq,
    ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
)


class ScriptError(Exception):
    def __init__(self, message, line=None):
        super().__init__(message)
        self.line = line


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


@dataclass
class Function:
    node: ast.FunctionDef


class Interpreter:
    def __init__(self, state=None):
        self.farm = Farm(state)
        self.frames = []
        self.globals = {}
        self.scopes = [self.globals]
        self.operations = 0
        self.actions = 0
        self.line = 1
        self.output_count = 0

    def consume(self):
        self.operations += 1
        if self.operations > MAX_OPERATIONS:
            raise ScriptError("Script reached 20,000 operations. Use a smaller loop or add an exit condition.", self.line)

    def checked(self, value):
        if type(value) in (int, float):
            if not math.isfinite(value) or abs(value) > MAX_VALUE:
                raise ScriptError("Numbers must stay between −1 billion and 1 billion.", self.line)
        elif isinstance(value, (str, list, tuple, range)):
            if len(value) > MAX_SEQUENCE:
                raise ScriptError("Strings, lists, and ranges are limited to 1,000 items.", self.line)
            if isinstance(value, (list, tuple)):
                pending, weight = [(value, 0)], 0
                while pending:
                    item, depth = pending.pop()
                    weight += 1
                    if weight > MAX_SEQUENCE or depth > 8:
                        raise ScriptError("Nested collections are limited to 1,000 total items and 8 levels.", self.line)
                    if isinstance(item, (list, tuple)):
                        pending.extend((child, depth + 1) for child in item)
        return value

    def validate(self, tree):
        count = 0
        pending = [(tree, 0, 0, 0)]
        while pending:
            node, depth, functions, loops = pending.pop()
            count += 1
            line = getattr(node, "lineno", 1)
            if count > MAX_NODES or depth > MAX_DEPTH:
                raise ScriptError("This script is too complex. Split it into smaller programs.", line)
            if not isinstance(node, ALLOWED):
                raise ScriptError(f"{type(node).__name__} is not supported in farm Python. See the API guide.", line)
            if isinstance(node, ast.Constant) and type(node.value) not in (int, float, str, bool, type(None)):
                raise ScriptError("Only numbers, strings, booleans, and None are supported.", line)
            if isinstance(node, (ast.Name, ast.arg)) and (getattr(node, "id", None) or getattr(node, "arg", "")).startswith("__"):
                raise ScriptError("Private Python names are not available.", line)
            if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.keywords):
                raise ScriptError("Call a named function with positional arguments.", line)
            if isinstance(node, (ast.Break, ast.Continue)) and not loops:
                raise ScriptError("break and continue belong inside a loop.", line)
            if isinstance(node, ast.Return) and not functions:
                raise ScriptError("return belongs inside a function.", line)
            if isinstance(node, ast.FunctionDef):
                if functions or node.decorator_list or node.returns or node.type_comment or getattr(node, "type_params", []):
                    raise ScriptError("Use a top-level function without decorators or annotations.", line)
                args = node.args
                if args.vararg or args.kwarg or args.defaults or args.kwonlyargs or args.posonlyargs or any(arg.annotation for arg in args.args):
                    raise ScriptError("Functions support simple positional parameters only.", line)
                if len({arg.arg for arg in args.args}) != len(args.args):
                    raise ScriptError("Function parameter names must be unique.", line)
                if node.name.startswith("__") or node.name in RESERVED or any(arg.arg in RESERVED for arg in args.args):
                    raise ScriptError("Choose names that do not replace drone API functions.", line)
                functions, loops = functions + 1, 0
            elif isinstance(node, (ast.For, ast.While)):
                loops += 1
            pending.extend((child, depth + 1, functions, loops) for child in ast.iter_child_nodes(node))

    def assign(self, target, value):
        if not isinstance(target, ast.Name):
            raise ScriptError("Assign to one variable name; list mutation and unpacking are not supported.", self.line)
        if target.id in RESERVED:
            raise ScriptError(f"'{target.id}' is a built-in farm function. Choose another variable name.", self.line)
        self.scopes[-1][target.id] = self.checked(value)

    def lookup(self, name):
        if name in self.scopes[-1]:
            return self.scopes[-1][name]
        if name in self.globals:
            return self.globals[name]
        raise ScriptError(f"Unknown name '{name}'. Check its spelling or define it first.", self.line)

    def block(self, body):
        for node in body:
            self.statement(node)

    def statement(self, node):
        self.consume()
        self.line = node.lineno
        if isinstance(node, ast.Expr):
            self.expression(node.value)
        elif isinstance(node, ast.Assign):
            value = self.expression(node.value)
            for target in node.targets:
                self.assign(target, value)
        elif isinstance(node, ast.AugAssign):
            self.assign(node.target, self.binary(node.op, self.expression(node.target), self.expression(node.value)))
        elif isinstance(node, ast.If):
            self.block(node.body if self.expression(node.test) else node.orelse)
        elif isinstance(node, (ast.For, ast.While)):
            broken = False
            if isinstance(node, ast.For):
                sequence = self.expression(node.iter)
                if not isinstance(sequence, (list, tuple, str, range)):
                    raise ScriptError("A for loop needs range(), a list, a tuple, or a string.", self.line)
                iterator = iter(sequence)
            while True:
                self.consume()
                if isinstance(node, ast.For):
                    try:
                        self.assign(node.target, next(iterator))
                    except StopIteration:
                        break
                elif not self.expression(node.test):
                    break
                try:
                    self.block(node.body)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    broken = True
                    break
            if not broken:
                self.block(node.orelse)
        elif isinstance(node, ast.FunctionDef):
            self.scopes[-1][node.name] = Function(node)
        elif isinstance(node, ast.Return):
            raise ReturnSignal(self.expression(node.value) if node.value else None)
        elif isinstance(node, ast.Break):
            raise BreakSignal()
        elif isinstance(node, ast.Continue):
            raise ContinueSignal()
        elif isinstance(node, ast.Pass):
            pass

    def binary(self, op, left, right):
        if isinstance(op, ast.Mult):
            for sequence, number in ((left, right), (right, left)):
                if isinstance(sequence, (str, list, tuple)) and isinstance(number, int) and len(sequence) * max(number, 0) > MAX_SEQUENCE:
                    raise ScriptError("That multiplication would create too many items.", self.line)
        if isinstance(op, ast.Add) and isinstance(left, (str, list, tuple)) and isinstance(right, type(left)) and len(left) + len(right) > MAX_SEQUENCE:
            raise ScriptError("That addition would create too many items.", self.line)
        operation = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                     ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}[type(op)]
        if isinstance(op, ast.Mod) and isinstance(left, str):
            raise ScriptError('Use print("message", value) to display values.', self.line)
        return self.checked(operation(left, right))

    def expression(self, node):
        self.consume()
        if isinstance(node, ast.Constant):
            return self.checked(node.value)
        if isinstance(node, ast.Name):
            return self.lookup(node.id)
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [self.expression(item) for item in node.elts]
            return self.checked(values if isinstance(node, ast.List) else tuple(values))
        if isinstance(node, ast.BinOp):
            return self.binary(node.op, self.expression(node.left), self.expression(node.right))
        if isinstance(node, ast.UnaryOp):
            operation = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}[type(node.op)]
            return self.checked(operation(self.expression(node.operand)))
        if isinstance(node, ast.BoolOp):
            result = None
            for item in node.values:
                result = self.expression(item)
                if isinstance(node.op, ast.And) and not result or isinstance(node.op, ast.Or) and result:
                    break
            return result
        if isinstance(node, ast.Compare):
            left = self.expression(node.left)
            operations = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
                          ast.Gt: operator.gt, ast.GtE: operator.ge, ast.In: lambda a, b: a in b,
                          ast.NotIn: lambda a, b: a not in b, ast.Is: operator.is_, ast.IsNot: operator.is_not}
            for op, right_node in zip(node.ops, node.comparators):
                right = self.expression(right_node)
                if not operations[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Subscript):
            value, index = self.expression(node.value), self.expression(node.slice)
            if not isinstance(value, (list, tuple, str, range)) or type(index) is not int:
                raise ScriptError("Use an integer index with a list, tuple, string, or range.", self.line)
            return value[index]
        if isinstance(node, ast.Call):
            args = [self.expression(arg) for arg in node.args]
            self.line = node.lineno
            return self.call(node.func.id, args)
        raise ScriptError("Unsupported expression.", self.line)

    def frame(self, message, kind="action", action=None, include_state=True):
        frame = {"line": self.line, "message": message, "kind": kind, "action": action}
        if include_state:
            frame["state"] = self.farm.snapshot()
            frame["events"] = list(self.farm.events)
        self.frames.append(frame)

    def call(self, name, args):
        self.consume()
        if name in ACTIONS:
            if self.actions >= MAX_ACTIONS:
                raise ScriptError("Run reached 400 drone actions. Run again to continue, or use a smaller loop.", self.line)
            message = self.farm.action(name, *args)
            self.actions += 1
            self.frame(message, action=name)
            return None
        if name in QUERIES:
            if args:
                raise ScriptError(f"{name}() takes no arguments.", self.line)
            s, tile = self.farm.state, self.farm.tile
            return {"can_harvest": self.farm.ready(), "get_crop": tile["crop"], "get_water": tile["water"],
                    "get_x": s["drone"]["x"], "get_y": s["drone"]["y"], "get_size": s["size"],
                    "get_coins": s["coins"], "is_tilled": tile["tilled"]}[name]
        if name == "print":
            if self.output_count >= 100:
                raise ScriptError("Output reached 100 messages. Print less often inside loops.", self.line)
            # Bounded formatting also avoids expanding shared nested lists recursively.
            message = " ".join(self.display(value) for value in args)
            if len(message) > 2000:
                raise ScriptError("Print messages are limited to 2,000 characters.", self.line)
            self.output_count += 1
            self.frame(message, "output", include_state=False)
            return None
        if name in BUILTINS:
            if name == "range":
                if not 1 <= len(args) <= 3 or any(type(arg) is not int for arg in args):
                    raise ScriptError("range() needs one to three integer arguments.", self.line)
                return self.checked(range(*args))
            if name in ("min", "max"):
                values = args[0] if len(args) == 1 and isinstance(args[0], (list, tuple, range)) else args
                if not values or any(type(value) not in (int, float, bool) for value in values):
                    raise ScriptError(f"{name}() needs numeric values.", self.line)
                return (min if name == "min" else max)(values)
            if len(args) != 1:
                raise ScriptError(f"{name}() takes one argument.", self.line)
            if name == "str":
                return self.checked(self.display(args[0]))
            operation = {"len": len, "int": int, "abs": abs}[name]
            return self.checked(operation(args[0]))
        function = self.lookup(name)
        if not isinstance(function, Function):
            raise ScriptError(f"'{name}' is not a function.", self.line)
        params = function.node.args.args
        if len(params) != len(args):
            raise ScriptError(f"{name}() expects {len(params)} arguments, got {len(args)}.", self.line)
        if len(self.scopes) >= 25:
            raise ScriptError("Function calls are nested too deeply. Use a loop instead of recursion.", self.line)
        self.scopes.append(dict(zip((param.arg for param in params), args)))
        try:
            self.block(function.node.body)
        except ReturnSignal as result:
            return result.value
        finally:
            self.scopes.pop()
        return None

    def display(self, value, depth=0):
        self.consume()
        if depth > 5:
            return "…"
        if isinstance(value, (list, tuple)):
            parts = [self.display(item, depth + 1) for item in value[:20]]
            return "[" + ", ".join(parts)[:1500] + (", …" if len(value) > 20 else "") + "]"
        if isinstance(value, Function):
            return f"<function {value.node.name}>"
        return str(value)[:2000]

    def run(self, source):
        error = None
        try:
            if type(source) is not str or len(source) > MAX_SOURCE:
                raise ScriptError("Scripts must be text under 16,000 characters.")
            tree = ast.parse(source)
            self.validate(tree)
            self.block(tree.body)
        except SyntaxError as exc:
            error = {"message": exc.msg, "line": exc.lineno}
        except (ScriptError, GameError) as exc:
            error = {"message": str(exc), "line": getattr(exc, "line", None) or self.line}
        except (TypeError, ValueError, ZeroDivisionError, IndexError, OverflowError) as exc:
            error = {"message": f"Check this expression: {exc}", "line": self.line}
        except RecursionError:
            error = {"message": "This expression is nested too deeply.", "line": self.line}
        except (BreakSignal, ContinueSignal, ReturnSignal):
            error = {"message": "This control statement is outside its loop or function.", "line": self.line}
        return {"frames": self.frames, "error": error, "actions": self.actions, "operations": self.operations}


def run_script(source, state=None):
    return Interpreter(state).run(source)
