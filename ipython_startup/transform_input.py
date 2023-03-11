import re
import ast
import inspect
from .utils import *
from contextlib import contextmanager
from pprint import pprint, pformat
from IPython.core.latex_symbols import latex_symbols

dbg = debug.dbg


class RangeMaker:
    precedence = '&'
    def __rand__(self, x):
        self.start = x
        return self
    def __and__(self, y):
        self.end = y
        return range(self.start, self.end+1)

class ArrayMaker:
    precedence = '[]'
    def __getitem__(self, x):
        # return Array(x)
        return Matrix(x)
    def __call__(self, *x):
        return Tuple(*x)
        
class DomMaker:
    precedence = '<'
    def __rlshift__(self, x):
        self.x = x
        return self
    def __lt__(self, domain):
        if isinstance(self.x, Symbol):
            if domain == Complex:
                asm = dict(complex=True)
            elif domain == Real:
                asm = dict(real=True)
            elif domain == Rational:
                asm = dict(rational=True)
            elif domain == Integer:
                asm = dict(integer=True)
            else:
                raise ValueError
            mAKeRXyZ_2345.sym._assumptions[self.x.name] = asm
            return Symbol(self.x.name, **asm)
        else:
            return self.x in domain

class SPDIMaker:
    """Maker of Sum, Product, Differentiation, Integration, etc."""
    
    def __init__(self, var=None, args=None, kwds=None):
        self.vars = []
        if var: getattr(self, var)
        
    def apply(self, f, y):
        if isinstance(y, Lambda):
            syms, exp = y.symbolic()
            if self.vars:
                vars = self.vars
            elif len(syms) == 1:
                vars = [syms[0]]
            else:
                raise TypeError('independent variable not specified')
            return Lambda(signature=y.signature, exp=f(exp, *vars))
        else:
            if len(self.vars) == 1 and type(self.vars[0]) is list \
                and self.vars[0][0] is None:
                    assert len(y.free_symbols) == 1
                    var = first(y.free_symbols)
                    self.vars[0][0] = var
            return f(y, *self.vars)
        
    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError
        self.vars.append(mAKeRXyZ_2345.sym(name))
        return self
    
    def __getitem__(self, lim: slice):
        if not self.vars: self.vars.append(None)
        assert type(self.vars[-1]) is not list
        start, end = lim.start, lim.stop
        if start is None: start = -oo
        if end is None: end = oo
        self.vars[-1] = [self.vars[-1], start, end]
        return self

class SumMaker(SPDIMaker):
    precedence = '<<'
    def __lshift__(self, y):
        return self.apply(summation, y)
    
class ProdMaker(SPDIMaker):
    precedence = '<<'
    def __lshift__(self, y):
        return self.apply(product, y)

class IntMaker(SPDIMaker):
    precedence = '<<'
    def __lshift__(self, y):
        return self.apply(integrate, y)
    
class DiffMaker(SPDIMaker):
    precedence = '**'

    def __init__(self, var=None, args=None, kwds=None):
        super().__init__(var)
        self.args, self.kwds = args, kwds

    def __pow__(self, y):
        return self.apply(diff, y)
    
    def __rmul__(self, y):
        dy = self.apply(diff, y)
        if self.args is not None:
            return dy(*self.args, **self.kwds)
        else:
            return dy

    def __call__(self, *args, **kwds):
        assert self.args is None
        self.args, self.kwds = args, kwds
        return self

class SymMaker:
    _assumptions = {}
    _ans = {}
    def __new__(cls, name):
        asm = cls._assumptions.setdefault(name, dict(real=True))
        return Symbol(name, **asm)

class SqrtMaker:
    precedence = '**'
    def __pow__(self, x):
        return sp.sqrt(x)

class EqMaker:
    precedence = '='
    marker = '__EQ__'
    
    @classmethod
    def convert(cls, re_match: re.Match):
        trans = mAKeRXyZ_2345.trans
        gs = re_match.groupdict()
        s, l, q, r = gs['s'], gs['l'], gs['q'], gs['r']
        l, r = trans(l.strip()), trans(r.strip())
        try:
            ast.parse(l + q + r)
            return re_match[0]
        except: pass
        try:
            m1 = re.match(r'\s*(?!\d)((?:\w+\.)*(\w+))\s*\((.*)\)', l)
            ast.parse(f'lambda {m1[3]}: 0')  # validate args
        except:
            m1 = None
        if m1:
            name, args = m1[1], m1[3]
            exp = f'{s}{name}=Lambda.get("{name}");'
            if q == ':=': exp += f'{name}.clear_dispatches();'
            exp += f'{name}<<=lambda {args}: {r}'
            return exp
        ast.parse(l); ast.parse(r)
        return f"{s}mAKeRXyZ_2345.eq(eval('''{l}'''),eval('''{r}'''),{q==':='})"

    def __new__(cls, lhs, rhs, lazy=False):
        import sympy as sp
        if isinstance(lhs, (list, tuple)):
            assert len(lhs) == len(rhs)
            eq = sp.Tuple(*[sp.Eq(l, r) for l, r in zip(lhs, rhs)])
        else:
            eq = sp.Eq(lhs, rhs)
        if not lazy:
            sol = sp.solve(eq, dict=True)
            return display(sol)
        return eq

class Lambda:
    def __init__(self, func=None, exp='...', signature=None, owner=None):
        self._dispatches = []
        if signature is not None:
            if isinstance(signature, inspect.Signature):
                signature = str(signature)[1:-1]
            func = eval(f'lambda {signature}: {exp}')
        if func is not None:
            if isinstance(func, str):
                node = ast.parse(func, mode='eval').body
                exp = ast.unparse(node.body)
                func = eval(func)
            # if inspect.isclass(owner):
            #     _f = f
            #     def f(*args, **kwds):
            #         return _f(*args, **kwds)
            sig = inspect.signature(func)
            self._dispatches.append(dict(
                f=func, body=exp, sig=sig))
            
    @property
    def signature(self):
        s = [d['sig'] for d in self._dispatches]
        if len(s) == 1: return s[0]
        return s
        
    @classmethod
    def get(cls, name):
        env = UTIL.outer_frame()
        try:
            f = eval(name, env)
            assert isinstance(f, cls)
            return f
        except:
            return cls()
        
    def parameters(self, symbolic=False):
        def pars(sig):
            ps = sig.parameters
            if symbolic:
                return {p: mAKeRXyZ_2345.sym(p) for p in ps}
            else:
                return ps
        if type(self.signature) is list:
            return list(map(pars, self.signature))
        else:
            return pars(self.signature)
    
    def symbolic(self):
        assert type(self.signature) is not list
        pars = self.parameters()
        assert len(pars) > 0 and not any(
            p.kind in [0, 2] for p in pars.values())
        syms = self.parameters(symbolic=True)
        return list(syms.values()), self(**syms)
        
    def __ilshift__(self, lam):
        if not isinstance(lam, type(self)):
            raise TypeError(f'{lam} is not a Lambda')
        my_sigs = [d['sig'] for d in self._dispatches]
        for dispatch in lam._dispatches:
            sig = dispatch['sig']
            if sig in my_sigs:
                i = my_sigs.index(sig)
                self._dispatches.pop(i)
            self._dispatches.append(dispatch)
        return self
    
    def clear_dispatches(self):
        self._dispatches.clear()

    def __call__(self, *args, **kwargs):
        breakpoint()
        for d in self._dispatches:
            try: return d['f'](*args, **kwargs)
            except TypeError: pass
        raise TypeError(f'No method found for {self}')
    
    def __repr__(self) -> str:
        reps = [f"{d['sig']} -> {d['body']}" for d in self._dispatches]
        rep = ', '.join(reps)
        if len(rep) > 80:
            rep = (',\n'+' '*len('MultiDispatch[')).join(reps)
        while True:
            dbg(rep)
            newrep = rep
            for s, p in mAKeRXyZ_2345.rev_trans_maps.items():
                newrep = re.sub(s, p, newrep)
            if newrep == rep:
                break
            else:
                rep = newrep
        if len(self._dispatches) == 1:
            return rep
        else:
            return f'MultiDispatch[{rep}]'

def transform(code):
    pattern = r'"(?:\\.|[^\\"])*"|\'(?:\\.|[^\\\'])*\'|(?:#.*)|%s'
        
    if hasattr(UTIL, 'task_thread'):
        UTIL.task_thread.join()

    def sub(m):
        gs = m.groups()
        if all(g is None for g in gs): return m[0]
        dbg('{}\n{}\n{}\n'.format(m.string, m.re, gs))
        if callable(t): return t(m)
        return t.format(*gs)

    while True:
        dbg(code)
        newcode = code
        for s, t in mAKeRXyZ_2345.trans_maps.items():
            try:
                newcode = re.sub(pattern % s, sub, newcode)
            except SyntaxError:
                continue
        if newcode == code:
            break
        else:
            code = newcode
 
    def to_dict(t: ast.AST):
        if isinstance(t, list): return list(map(to_dict, t))
        if type(t).__name__ not in ast.__dict__: return t
        if isinstance(t, ast.Module) and len(t.body) == 1: t = t.body[0]
        dic = {name: to_dict(val) for name, val in ast.iter_fields(t) if val is not None}
        return {'': type(t).__name__, **dic}

    def make_lambda(node):
        # dbg(pformat(to_dict(node)))
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='mAKeRXyZ_2345'),
                attr='lam',
                ctx=ast.Load()),
            args=[node, ast.Constant(ast.unparse(node.body))],
            keywords=[])

    def transform_ast(code):
        try:
            t = ast.parse(code)
        except SyntaxError:
            return code
        # dbg(pformat(to_dict(t)))
        t1 = Transformer().visit(t)
        # dbg(pformat(to_dict(t1)))
        return ast.unparse(t1)
    
    class Transformer(ast.NodeTransformer):
        # def visit_Name(self, node):
        #     if node.id.startswith(arg_prefix):
        #         name = node.id[len(arg_prefix):]
        #         if not name or name.isdigit():
        #             name = arg_prefix + name
        #         node.id = name
        #         node.vars = {name}
        #     return node

        def visit_Lambda(self, node):
            node = self.generic_visit(node)
            return make_lambda(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                eq = mAKeRXyZ_2345.eq
                if node.func.id == eq.marker:
                    new_code = eq.convert(arg.value for arg in node.args)
                    return ast.Name(id=transform_ast(new_code))
            return self.generic_visit(node)
            
    code = transform_ast(code)
    dbg(code)
    return code


class MainMaker:
    ran = RangeMaker()
    arr = ArrayMaker()
    sqrt = SqrtMaker()
    dom = DomMaker()
    sym = SymMaker
    lam = Lambda
    eq = EqMaker
    sum = SumMaker
    prod = ProdMaker
    diff = DiffMaker
    int = IntMaker
    ns = NameSpace
    trans = classmethod(transform)
    
    trans_maps = {
    # x^2 ==> x**2
    r'(\^)': '**',
    
    # 1..3 ==> range(1, 4)
    r'([.][.])': '&mAKeRXyZ_2345.ran&',

    # a.0 ==> a[0]
    r'([^\s\d])\.(-?\d+)': '{}[{}]',

    # √2 ==> sp.sqrt(2)
    r'(√)': 'mAKeRXyZ_2345.sqrt**',

    # x -> x+1 ==> lambda x: x+1
    r'(\([^()]*\)|(^|(?<=\W))(?!\d)\w+)\s*->':
        lambda m: f"lambda {m[1].strip('(').strip(')')}:",
    
    # y′ ==> diff(y)
    r'(′)': '*mAKeRXyZ_2345.diff()',
    
    # ∂x x?^2 ==> sp.diff(x?**2, x?)
    r'∂((?!\d)\w+)': 'mAKeRXyZ_2345.diff("{}")**',
    
    # a? ==> Symbol('a')
    r'(?:^|(?<=\W))(?!\d)(\w+)\?': 'mAKeRXyZ_2345.sym("{}")',
    
    # x? ∈ Real ==> Symbol('x', real=True)  # modify its domain
    r'(∈)': '<<mAKeRXyZ_2345.dom<',
   
    # (a=1;c=a+1;c-a) ==> (lambda:[a=1,c=a+1,c-a])()[-1]
    r'(\(.*;.*\)): ': ...,

    # $[1,2,3] ==> Matrix([1,2,3])
    r'(\$\[)': 'mAKeRXyZ_2345.arr[',
    
    # $(1,2,3) ==> Tuple(1,2,3)
    r'(\$\()': 'mAKeRXyZ_2345.arr(',

    # [1,2;3,4] ==> [[1,2],[3,4]]
    r'\[(.+?(;.+?)+?)\]':
        lambda m: '[%s]' % ', '.join('[%s]' % s for s in m[1].split(';')),

    # {a=1, b=2} ==> SimpleNamespace(a=1, b=2)
    r'\{(\s*\w+=.+?)\}': 'mAKeRXyZ_2345.ns({})',

    # 2 * $x = 4 ==> solve(Eq(2 * $x, 4))
    # 2 * $x := 4 ==> Eq(2 * $x, 4)
    # f(x) = x + 1 ==> if f not in dir(): f = Lambda(); f <<= lambda x: x + 1
    # f(x) := x + 1 ==> f = lambda x: x + 1
    (r'(?P<s>(^|\n)\s*)'  # space at the beginning of the line
     r'(?P<l>.*)'  # left hand side
     r'(?<![:<>!&|+\-*/%])(?P<q>:?=)(?!=|[^()]*\))'  # equal sign (ensure balanced parens)
     r'(?P<r>[^\n]+)'):  # right hand side
        EqMaker.convert
    }

    # ∫ x?^2 ==> integrate(x?**2)
    # ∫[0:1] x?^2 => integrate(x?**2, (x?,0,1))
    # ∫x.y 1/(x?^2+y?) ==> integrate(1/(x?**2+y?), x?, y?)
    # ∫x[0:] 1/(x?^2+y?) => integrate(1/(x?**2+y?), (x?,0,inf))
    # ∫x[0:].y[-1:1] 1/(x?^2+y?) => integrate(1/(x?**2+y?), (x?,0,inf), (y?,-1,1))
    spi_maps = {
    'sum': 'Σ',
    'prod': 'Π',
    'int': '∫',
    }

    rev_trans_maps = {
    r' \| mAKeRXyZ_2345\.ran \| ': '..',
    r'(?<!\w)mAKeRXyZ_2345\.sqrt \*\* ': '√',
    r'\*\*mAKeRXyZ_2345.diff': '′',
    r'(?<!\w)mAKeRXyZ_2345\.sym\.(\w+)': r'\1?',
    r'(?<!\w)mAKeRXyZ_2345\.arr\[': '$[',
    r"(?<!\w)mAKeRXyZ_2345.lam\((?:lambda (?P<a>.*?):|\((?P<b>.*?)\) ->) (.*), ([\'\"])\3\4\)":
        lambda m: f"({m['a'] or m['b']}) -> {m[3]}"
    }
    
    for _s, _c in spi_maps.items():
        trans_maps[
            r'%s((?!\d)\w+(?!\?))?((\[.+?\]|\.\w+)*)' % _c
        ] = lambda m,s=_s:f'mAKeRXyZ_2345.%s('%s+(f'"{m[1]}"'if m[1] else'')+f'){m[2]}<<'
        

mAKeRXyZ_2345 = MainMaker()

UTIL._my_transform_cell = transform


class UnicodeSymbols:
    all_symbols = latex_symbols
    extra_symbols = {
        '\\sum': '\\Sigma',
        '\\prod': '\\Pi',
        '\\i': 'ί',
        '\\e': '℮',
        '\\sqrt': '√',
        "\\'": '′',
        '\\d': '∂',
        '\\int': '∫',
        '\\ga': '\\alpha',
        '\\gb': '\\beta',
        '\\gd': '\\delta',
        '\\ge': '\\epsilon',
        '\\gg': '\\gamma',
        '\\gG': '\\Gamma',
        '\\gi': '\\iota',
        '\\gk': '\\kappa',
        '\\gl': '\\lambda',
        '\\gr': '\\rho',
        '\\gs': '\\sigma',
        '\\go': '\\omega',
        '\\gO': '\\Omega',
        '\\gu': '\\upsilon',
        '\\in': '∈',
        '\\R': 'ℝ',
        '\\C': 'ℂ',
        '\\Q': 'ℚ',
        '\\Z': 'ℤ',
        '\\deg': '°',
        '\\ang': '∠',
        '\\grin': '😁',
        '\\haha': '😂',
        '\\smile': '🙂',
        '\\lol': '🤣',
        '\\fire': '🔥',
        '\\cow': '🐮',
        '\\monkey': '🐒',
        '\\horse': '🐴',
        '\\tree': '🌲',
        '\\cake': '🍰',
        '\\red': '🟥',
        '\\green': '🟩',
        '\\blue': '🟦',
    }
    for code, sym in extra_symbols.items():
        if sym[0] == '\\':
            extra_symbols[code] = all_symbols[sym]
    all_symbols.update(extra_symbols)
