import numpy as np
from .utils import *


@UTIL.coroutine
def import_libs():
    """Import big packages and do other stuff."""
    
    print('Importing math libraries...')
    time.sleep(0.1)
    
    import sympy as sp
    import pandas as pd
    import plotly.express as px
    
    from sympy import (
        sin, cos, tan, cot, sinh, cosh, tanh,
        exp, ln, sqrt, gamma, binomial, conjugate,
        diff, integrate, limit, simplify, summation, product,
        Rational, Integer, RealField as Real, ComplexField as Complex,
        pi, I, E, oo, nan,
        Eq, Symbol, Expr, Tuple, Dict, Matrix, Function
    )
    ί = I
    ℮ = E
    π = PI = pi
    ℤ = Integer
    ℚ = Rational
    ℝ = Real
    ℂ = Complex

    sp.init_printing()

    @override(sp.Expr, '__call__')
    def _call(self, *args, **kwds):
        if kwds and not args:
            return self.subs(
                (mAKeRXyZ_2345.sym(k), v) for k, v in kwds.items())
        elif len(args) == 1 and not kwds and \
                len(self.free_symbols) == 1:
            x = next(iter(self.free_symbols))
            return self.subs(x, args[0])
        else:
            return self.subs(*args, **kwds)
    
    # @UTIL.deco.override(sp.Expr)
    # def n(self, *args, **kwds):
    #     n = self._overrid_n(*args, **kwds)
    #     if isinstance(n, sp.Number):
    #         n = n.round(10)
    #     return sp.nsimplify(n)
    # del n
    
    def _convert_type(x):
        if isinstance(x, list):
            if not x:
                return None
            elif len(x) == 1:
                return _convert_type(x[0])
            else:
                return Tuple(*map(_convert_type, x))
        elif isinstance(x, dict):
            global ans
            ans = NameSpace()
            def to_eq(pair):
                s, v = pair
                setattr(ans, s.name, v)
                return Eq(s, v)
            if len(x) == 1:
                return to_eq(first(x.items()))
            else:
                return Tuple(*map(to_eq, x.items()))
        else:
            return x

    @override(sp, 'solve')
    def _solve(*args, **kwds):
        sol = sp._overrid_solve(*args, **kwds)
        return _convert_type(sol)
    
    # update shell namespace
    globals().update(
        (k, v) for k, v in locals().items()
        if not k.startswith('_'))
    UTIL._shell.ns_table['user_global'].update(globals())


class Array(np.ndarray):
    def __new__(cls, value, **kwds):
        return np.asarray(value, **kwds).view(cls)
    
    def __init__(self, *_, **__):
        super().__init__()
        self.__mem = {}
        
    def __array_finalize__(self, obj):
        self.__mem = getattr(obj, '__mem', {})
    
    @classmethod
    def random(cls, *shape, distr='uniform', dtype=np.float32, **kwds):
        if isinstance(dtype, int):
            rand = np.random.randint
        else:
            rand = getattr(np.random, distr)
        return cls(rand(size=shape, **kwds))

    @classmethod
    def register_method(cls, name, func):
        def f(*args, **kwargs):
            ret = func(*args, **kwargs)
            if isinstance(ret, np.ndarray): ret = cls(ret)
            return ret
        update_wrapper(f, func)
        setattr(cls, name, f)
        
    @classmethod
    def register_property(cls, name, func):
        def f(self):
            if name in self.__mem:
                return self.__mem[name]
            else:
                ret = func(self)
                self.__mem[name] = ret
                return ret
        cls.register_method(name, f)
        setattr(cls, name, property(getattr(cls, name)))

    def __repr__(self) -> str:
        return str(self)
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.__mem.clear()
        
    class I:
        def __new__(cls, rank):
            return Array(np.eye(rank))

    # @classmethod
    # def defplot(cls, name):
    #     plot = getattr(px, name)
    #     def p(self, *args, **kwargs):
    #         if self.squeeze().ndim == 1:
    #             plot(self, *args, **kwargs)
    #         elif self.ndim == 2:
    #             plot(*self.T, *args, **kwargs)
    #         elif self.ndim == 3:
    #             ax = plt.axes(projection='3d')
    #             getattr(ax, name+'3D')(*self.T, *args, **kwargs)
    #         else:
    #             raise ValueError('Array must be 1D or 2D')
    #         plt.show()
    #     UTIL.update_wrapper(p, plot)
    #     setattr(cls, name, p)


[Array.register_method(name, func) for name, func in [
    ('abs', np.abs),
    ('range', np.arange),
    ('linspace', np.linspace),
    ('logspace', np.logspace),
    ('ones', np.ones),
    ('zeros', np.zeros),
]]
[Array.register_property(name, func) for name, func in [
    ('inv', np.linalg.inv),
    ('det', np.linalg.det),
    ('diag', np.diag),
    ('flat', lambda self: self.reshape(-1)),
    ('rank', np.linalg.matrix_rank),
    ('eig', np.linalg.eig),
    ('svd', np.linalg.svd)
]]

# [Array.defplot(name) for name in ['plot', 'scatter', 'hist']]
