# %%
import ast
from operator import *
from inspect import Signature, Parameter
from typing import Union, Any

ID = Union[str, int]

class MakeSome(type):
    """Metaclass for Some class"""
    # def __getattribute__(self, __name: str) -> "Some":
    #     print(self)
    #     return self(__name)

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
        print(self._signature, args)
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
        self._repr = ast.unparse(body)

    @classmethod
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
            rcall = lambda self, other: call(self, other, r=True)
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
            raise ValueError(f"optype must be 'BinOp', 'UnaryOp', or 'Compare', not {optype}")
        
        setattr(cls, method, call)
    
    def __bool__(self) -> bool:
        #! no way to include if-else, and, or, and not?
        return True
    
    def __getattr__(self, name: str) -> "SomeExpr":
        return SomeExpr(ast.Attribute(self._body, name), self._args)
    
    def __getitem__(self, key: Any) -> "SomeExpr":
        return SomeExpr(ast.Subscript(self._body, ast.Constant(key)), self._args)
    
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        binds = self._args.bind(*args, **kwds)
        return eval_somebody(self._body, binds)
        
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
    
def eval_somebody(body: ast.expr, args: dict) -> Any:
    if isinstance(body, ast.Constant):
        return body.value
    elif isinstance(body, ast.Name):
        try:
            return args[body.id]
        except:
            raise NameError(f"Name {body.id} is not defined")
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
    else:
        print(body)
        raise NotImplementedError(f"eval_somebody does not support {type(body)}")

# %%
OP2FUNC = {
    'Add': add,
    'Sub': sub,
    'Mult': mul,
    'Div': truediv,
    'FloorDiv': floordiv,
    'Mod': mod,
    'Pow': pow,
    'MatMult': matmul,
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
    '__matmul__': ('BinOp', 'MatMult'),
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

for method, (optype, op) in METHOD2OP.items():
    SomeExpr.register(method, optype, op)

# %%
some = Some(0)
some1 = Some(1)
some2 = Some(2)
some3 = Some(3)
some_x = Some('x')
some_y = Some('y')
some_z = Some('z')

# %%
f = some1 + some2
f

# %%
f(1, 2, 3)

# %%
g = some * f + some_x
g(1, 2, 3, x=4)

# %%
import numpy as np
h = some[:, 0] + some1.T @ some2.reshape(2, 2)
h(np.array([[1, 2, 3], [4, 5, 6]]),
  np.array([[1, 2, 3], [4, 5, 6]]),
  np.array([1, 2, 3, 4]))

# %%
