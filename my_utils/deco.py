import sys
from time import time
from functools import update_wrapper, wraps, partial
from collections import defaultdict

# When you use a decorator to define the function, the original function is
# replaced by the function returned by the decorator. This causes that if you
# call the "help" function upon the decorated function, the info it displays is
# that of the returned function of the decorator. "update_wrapper" is used to 
# deal with this problem.
# Use the built-in function "help" to see the docstrings.
def decorator(dec):
    """ Makes the decorated decorator such that when it decorates a function, the
    decorated function looks like the original function.
    Additionally, the decorated decorator can be partially initialized with provided
    arguments, when the first of them is non-callable. """
    def _dec(*args, **kwargs):
        "This will be displayed if the second update_wrapper is absent."
        assert args, "no arguments provided to the decorator"
        if not callable(args[0]):
            return partial(dec, *args, **kwargs)  # return another decorator
        assert len(args) == 1 and not kwargs, "too many arguments provided to the decorator"
        return update_wrapper(dec(args[0]), args[0])  # update_wrapper returns the wrapper
    return update_wrapper(_dec, dec)


@decorator
def n_ary(bin_f):  # a decorator to improve expressiveness
    "Turns a binary function into a function with arbitrary non-zero arity."
    def f(a, *rest):
        "This will be displayed if @decorator is absent."
        return a if not rest else bin_f(a, f(*rest))
    return f


@decorator
def memo(f):  # a decorator to improve performance
    "Use a table to store computed results of a function."
    table = {}
    def mf(*args):
        # print(table)
        try:
            return table[args]
        except KeyError:
            result = f(*args)
            table[args] = result
            return result
        except TypeError:
            return f(*args)
    return mf


@decorator
def disabled(f):
    "Assign a decorator to disabled to disable it."
    return f


@decorator
def timer(f):
    "Show the elapsed time of calling the function."
    def _f(*args, **kwargs):
        start = time()
        result = f(*args, **kwargs)
        end = time()
        print("time elapsed:", end - start)
        return result
    return _f


def override(cls, name=None):
    @decorator
    def deco(method):
        nonlocal name
        if name is None:
            name = method.__name__
        setattr(cls, '_overrid_'+name, getattr(cls, name))
        setattr(cls, name, method)
        return method
    return deco


class TraceLocals:
    """ A decorator to trace the local variables of a function after it returns. """
    
    def __init__(self, func):
        self._locals = {}
        self.func = func

    def __call__(self, *args, **kwargs):
        def tracer(frame, event, arg):
            if event == 'return':
                self._locals = frame.f_locals.copy()

        # tracer is activated on next call, return or exception
        sys.setprofile(tracer)
        try:
            # trace the function call
            res = self.func(*args, **kwargs)
        finally:
            # disable tracer and replace with old one
            sys.setprofile(None)
        return res

    def clear_locals(self):
        self._locals = {}

    @property
    def locals(self):
        return self._locals


class Profile:
    debug_counts, debug_times = defaultdict(int), defaultdict(float)

    @classmethod
    def print_debug_exit(cls):
        print('\n{}  COUNT --- TIME COST'.format('-' * 47))
        for name, _ in sorted(cls.debug_times.items(), key=lambda x: -x[1]):
            print(f"{name:<45} : {cls.debug_counts[name]:>6} {cls.debug_times[name]:>10.2f} ms")

    def __init__(self, name=''):
        self.name = name

    def __enter__(self):
        self.st = time.time()

    def __exit__(self, *_):
        et = (time.time() - self.st) * 1000.
        self.debug_counts[self.name] += 1
        self.debug_times[self.name] += et
        # debug(f"{self.name:>20} : {et:>7.2f} ms")

@decorator
def timed(fn, name=None):
    if name is None:
        name = fn.__qualname__
    def wrapper(*args, **kwds):
        with Profile(name):
            return fn(*args, **kwds)
    return wrapper
