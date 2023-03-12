# %%
import numpy as np
import ast
from operator import *
from copy import deepcopy
from inspect import Signature, Parameter
from typing import Union, Any

ID = Union[str, int]


class MakeSome(type):
    """Metaclass for Some class"""

    def __getattribute__(self, __name: str) -> "Some":
        try:
            return super().__getattribute__(__name)
        except:
            return self(__name)


class SomeArgs:
    def __init__(self, pos_args: frozenset["Some"], key_args: frozenset["Some"]):
        self.poses = pos_args
        self.keys = key_args
        self._make_signature()

    def merge(self, other: "SomeArgs") -> "SomeArgs":
        return SomeArgs(self.poses | other.poses, self.keys | other.keys)

    def _make_signature(self):
        n = len(self.poses) and max(int(k[1:] or 0) for k in self.poses) + 1
        self._signature = Signature(
            [Parameter(name=f'_{i}', kind=Parameter.POSITIONAL_ONLY)
             for i in range(n)] +
            [Parameter(name=a[1:], kind=Parameter.KEYWORD_ONLY)
             for a in self.keys])

    def bind(self, *args: Any, **kwds: Any) -> dict:
        binds = self._signature.bind(*args, **kwds).arguments
        for k in list(binds.keys()):
            v = binds.pop(k)
            if k.startswith('_') and k[1:].isdigit():
                k = int(k[1:]) or ''
            binds[f'${k}'] = v
        return binds


class SomeExpr:
    def __init__(self, body: ast.expr, args: SomeArgs):
        self._body = body
        self._args = args
        self._tree = to_dict(body)
        self._repr = ast.unparse(body)

    def __bool__(self) -> bool:
        #! cannot include if-else, and, or, and not?
        return True

    def __getattr__(self, name: str) -> "SomeExpr":
        return SomeExpr(ast.Attribute(self._body, name), self._args)

    def __getitem__(self, key: Any) -> "SomeExpr":
        if isinstance(key, SomeExpr):
            args = self._args.merge(key._args)
            key = key._body
        else:
            args = self._args
            key = ast.Constant(key)
        return SomeExpr(ast.Subscript(self._body, key), args)

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        lsa, lskw = list(args), list(kwds.items())
        
        expr_args = []
        for i, a in enumerate(lsa):
            if isinstance(a, SomeExpr):
                expr_args.append(a)
                lsa[i] = a._body
        for i, (k, a) in enumerate(lskw):
            if isinstance(a, SomeExpr):
                expr_args.append(a)
                lskw[i] = ast.keyword(k, a._body)

        if len(expr_args) > 0 or isinstance(self._body, ast.Attribute):
            args = self._args
            for a in expr_args:
                args = args.merge(a._args)
            for i, a in enumerate(lsa):
                if not isinstance(a, ast.expr):
                    lsa[i] = ast.Constant(a)
            for i, (k, a) in enumerate(lskw):
                if not isinstance(a, ast.expr):
                    lskw[i] = ast.keyword(k, ast.Constant(a))
            body = ast.Call(self._body, lsa, lskw)
            return SomeExpr(body, args)
        
        binds = self._args.bind(*args, **dict(kwds))
        return eval_somebody(self._body, binds)
    
    def __matmul__(self, other: Any) -> "SomeExpr":
        if isinstance(other, SomeExpr):
            other = other,
        if isinstance(other, tuple):
            binds = self._args.bind(*[a._body for a in other])
            body = deepcopy(self._body)
            body = eval_somebody(body, binds, keep_expr=True)
            args = other[0]._args
            for exp in other[1:]:
                args = args.merge(exp._args)
            return SomeExpr(body, args)
        else:
            raise TypeError("unsupported operand type(s) for @: 'SomeExpr' and 'Any'")

    def __repr__(self) -> str:
        return self._repr


class Some(SomeExpr, metaclass=MakeSome):
    def __init__(self, id: ID):
        sym = "$" if id == 0 else f'${id}'
        if type(id) is int:
            self._id = id
            args = SomeArgs(frozenset([sym]), frozenset())
        elif type(id) is str:
            self._id = hash(sym)
            args = SomeArgs(frozenset(), frozenset([sym]))
        else:
            raise TypeError("id must be str or int")
        super().__init__(ast.Name(id=sym), args)

    def __hash__(self) -> int:
        return self._id


# TODO: use ast.NodeVisitor
def eval_somebody(body: ast.expr, args: dict, keep_expr=False) -> Any:
    if isinstance(body, ast.Name):
        try:
            return args[body.id]
        except:
            raise NameError(f"Name {body.id} is not defined")
    elif keep_expr:
        for a, v in vars(body).items():
            if isinstance(v, ast.expr):
                setattr(body, a, eval_somebody(v, args, keep_expr))
        return body
    elif isinstance(body, ast.Constant):
        return body.value
    elif isinstance(body, ast.BinOp):
        left = eval_somebody(body.left, args)
        right = eval_somebody(body.right, args)
        op = OP2FUNC[type(body.op).__name__]
        return op(left, right)
    elif isinstance(body, ast.UnaryOp):
        value = eval_somebody(body.operand, args)
        op = OP2FUNC[type(body.op).__name__]
        return op(value)
    elif isinstance(body, ast.Compare):
        left = eval_somebody(body.left, args)
        right = eval_somebody(body.comparators[0], args)
        op = OP2FUNC[type(body.ops[0]).__name__]
        return op(left, right)
    elif isinstance(body, ast.Attribute):
        obj = eval_somebody(body.value, args)
        return getattr(obj, body.attr)
    elif isinstance(body, ast.Subscript):
        obj = eval_somebody(body.value, args)
        slc = eval_somebody(body.slice, args)
        return obj[slc]
    elif isinstance(body, ast.Call):
        f = eval_somebody(body.func, args)
        args = [eval_somebody(a, args) for a in body.args]
        kwds = {k: eval_somebody(v, args) for k, v in body.keywords}
        return f(*args, **kwds)
    else:
        raise NotImplementedError(
            f"eval_somebody does not support {body}")
        
def to_dict(n):
    if isinstance(n, (list, tuple)):
        return type(n)([to_dict(x) for x in n])
    if hasattr(n, '__dict__'):
        return {k: to_dict(v) for k, v in vars(n).items()}
    return n


# %%
OP2FUNC = {
    'Add': add,
    'Sub': sub,
    'Mult': mul,
    'Div': truediv,
    'FloorDiv': floordiv,
    'Mod': mod,
    'Pow': pow,
    # 'MatMult': matmul,
    'LShift': lshift,
    'RShift': rshift,
    'BitOr': or_,
    'BitXor': xor,
    'BitAnd': and_,
    'Invert': invert,
    'UAdd': pos,
    'USub': neg,
    'Eq': eq,
    'NotEq': ne,
    'Lt': lt,
    'LtE': le,
    'Gt': gt,
    'GtE': ge,
}

METHOD2OP = {
    '__add__': ('BinOp', 'Add'),
    '__sub__': ('BinOp', 'Sub'),
    '__mul__': ('BinOp', 'Mult'),
    '__truediv__': ('BinOp', 'Div'),
    '__floordiv__': ('BinOp', 'FloorDiv'),
    '__mod__': ('BinOp', 'Mod'),
    '__pow__': ('BinOp', 'Pow'),
    # '__matmul__': ('BinOp', 'MatMult'),
    '__lshift__': ('BinOp', 'LShift'),
    '__rshift__': ('BinOp', 'RShift'),
    '__or__': ('BinOp', 'BitOr'),
    '__xor__': ('BinOp', 'BitXor'),
    '__and__': ('BinOp', 'BitAnd'),
    '__invert__': ('UnaryOp', 'Invert'),
    '__neg__': ('UnaryOp', 'USub'),
    '__pos__': ('UnaryOp', 'UAdd'),
    '__eq__': ('Compare', 'Eq'),
    '__ne__': ('Compare', 'NotEq'),
    '__lt__': ('Compare', 'Lt'),
    '__le__': ('Compare', 'LtE'),
    '__gt__': ('Compare', 'Gt'),
    '__ge__': ('Compare', 'GtE'),
}

def register(cls, method: str, optype: str, op: str):
    op = getattr(ast, op)()

    if optype == 'BinOp':
        def call(self, other: Any, r=False) -> "SomeExpr":
            left = self._body
            if isinstance(other, SomeExpr):
                args = self._args.merge(other._args)
                right = other._body
            else:
                args = self._args
                right = ast.Constant(other)
            if r:  # reverse order
                left, right = right, left
            body = ast.BinOp(left, op, right)
            return SomeExpr(body, args)

        rmethod = '__r' + method[2:]
        def rcall(self, other): return call(self, other, r=True)
        setattr(cls, rmethod, rcall)

    elif optype == 'UnaryOp':
        def call(self) -> "SomeExpr":
            body = ast.UnaryOp(op, self._body)
            return SomeExpr(body, self._args)

    elif optype == 'Compare':
        def call(self, other: Any) -> "SomeExpr":
            if isinstance(other, SomeExpr):
                args = self._args.merge(other._args)
                other = other._body
            else:
                args = self._args
                other = ast.Constant(other)
            body = ast.Compare(self._body, [op], [other])
            return SomeExpr(body, args)
        
    else:
        raise ValueError(
            f"optype must be 'BinOp', 'UnaryOp', or 'Compare', not {optype}")

    setattr(cls, method, call)

for method, (optype, op) in METHOD2OP.items():
    register(SomeExpr, method, optype, op)

# %%
some = Some(0)
some1 = Some(1)
some2 = Some(2)
some3 = Some(3)
some_x = Some.x
some_y = Some.y
some_z = Some.z

# %%
f = some * 2 + 1
f

# %%
f(3)

# %%
(some1 + some2)(1, 2, 3)

# %%
{some_x, Some('x')}

# %%
list(map(some + some1, [1, 2, 3], [4, 5, 6]))

# %%
list(filter(some % 2, [1, 2, 3, 4, 5]))

# %%
g = some1 * f + some_x
g

# %%
g(1, 2, x=4)

# %%
h = some.reshape(3, 2)[:2] + some1.T[[1, 2]]
h(np.array([[1, 2, 3], [4, 5, 6]]),
  np.array([[1, 2, 3], [4, 5, 6]]))

# %%
print(f)
g = some ** 2
print(g)
h = f @ g
print(h)
print(h @ f)
h(3)

# %%
