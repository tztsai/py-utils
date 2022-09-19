import sys
import inspect
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
        if not args or not callable(args[0]):
            return partial(dec, *args, **kwargs)  # return another decorator
        assert len(args) == 1 and not kwargs
        return update_wrapper(dec(args[0]), args[0])
    return update_wrapper(_dec, dec)  # update_wrapper returns the wrapper


@decorator
def main(fn):
    """Call fn with command line arguments.  Used as a decorator.

    The main decorator marks the function that starts a program. For example,

    @main
    def my_run_function():
        # function body

    Use this instead of the typical __name__ == "__main__" predicate.
    """
    if inspect.stack()[1][0].f_locals['__name__'] == '__main__':
        args = sys.argv[1:]  # Discard the script name from command line
        fn(*args)  # Call the main function
    return fn


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

@decorator
class trace_locals:
    """ A decorator to trace the local variables of a function after it returns. """
    
    def __init__(self, func, modifiers: dict = None):
        self.vars = {}
        self.__fn = func
        self.__co = func.__code__
        self._mod = modifiers

    def __call__(self, *args, **kwargs):
        def tracer(frame, event, arg):
            if frame.f_code is not self.__co:
                return
            elif event == 'call':
                self.vars = frame.f_locals
                if self._mod:
                    self.vars.update((k, m(self.vars[k]))
                                     for k, m in self._mod.items())
            # elif event == 'return':
            #     self._locals = frame.f_locals.copy()

        # tracer is activated on next call, return or exception
        sys.setprofile(tracer)
        try:
            # trace the function call
            res = self.__fn(*args, **kwargs)
        finally:
            # disable tracer and replace with old one
            sys.setprofile(None)
        return res

    def __getitem__(self, key):
        return self.vars[key]


# @decorator
# def with_jumps(func):
#     def trace(frame, event, arg):
#         # if event == 'line':
#         #     print(frame.f_code.co_name, frame.f_lineno)
#         print(event, arg, frame.f_code.co_name, frame.f_lineno)
#         if event == 'opcode':
#             print(frame.f_code.co_name, frame.f_lineno)
#         elif event == 'exception':
#             e, v, tb = arg
#             print(e, v, tb)
#             if isinstance(v, str) and v.startswith('jump '):
#                 frame.f_lineno += int(v.split(' ', 1)[1])
#                 print('jumping to', frame.f_lineno)
#         return trace
#     def wrapper(*args, **kwargs):
#         _trace = sys.gettrace()
#         try:
#             sys.settrace(trace)
#             return func(*args, **kwargs)
#         except AssertionError:
#             pass
#         finally:
#             sys.settrace(_trace)
#     return wrapper


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


if __name__ == '__main__':
    import unittest
    
    class TestDecorators(unittest.TestCase):
        # def test_with_jumps(self):
        #     @with_jumps
        #     def abs_(x):
        #         if x < 0:
        #             return -x
        #         else:
        #             return x
        #     self.assertEqual(abs_(1), 1)
        #     self.assertEqual(abs_(-1), 1)
            
        def test_trace_locals(self):
            @trace_locals
            def f(x):
                y = x + 1
                return y
            self.assertEqual(f(1), 2)
            self.assertEqual(f['x'], 1)
            self.assertEqual(f['y'], 2)
            self.assertEqual(f.__name__, 'f')
            
            @trace_locals
            def g(y):
                def h(x):
                    return x + y
                z = h(y)
                return h(z)
            self.assertEqual(g(2), 6)
            self.assertEqual(g['y'], 2)
            self.assertEqual(g['z'], 4)
            self.assertEqual(len(g.vars), 3)
            
            @trace_locals(modifiers={'y': abs})
            def h(x, y):
                @trace_locals
                def g(z):
                    w = x + y + z
                    return w
                z = g(999)
                return g(g['w']) - z
            self.assertEqual(h(-1, 2), 1)
            self.assertEqual(h['x'], -1)
            self.assertEqual(h(1, -5), 6)
            self.assertEqual(h['y'], 5)

    unittest.main()

