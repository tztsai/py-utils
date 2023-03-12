import os
import sys
import inspect
import unittest
import signal
import code
import contextlib
from icecream import ic
from multiprocessing import Pool
from functools import wraps


def interact(msg=None):
    """Start an interactive interpreter session in the current environment.

    On Unix:
      <Control>-D exits the interactive session and returns to normal execution.
    In Windows:
      <Control>-Z <Enter> exits the interactive session and returns to normal
      execution.
    """
    # evaluate commands in current namespace
    frame = inspect.currentframe().f_back
    namespace = frame.f_globals.copy()
    namespace.update(frame.f_locals)

    # exit on interrupt
    def handler(signum, frame):
        print()
        exit(0)
    signal.signal(signal.SIGINT, handler)

    if not msg:
        _, filename, line, _, _, _ = inspect.stack()[1]
        msg = 'Interacting at File "{0}", line {1} \n'.format(filename, line)
        msg += '    Unix:    <Control>-D continues the program; \n'
        msg += '    Windows: <Control>-Z <Enter> continues the program; \n'
        msg += '    exit() or <Control>-C exits the program'

    code.interact(msg, None, namespace)


@contextlib.contextmanager
def binding(**kwds):
    """Bind variables within a context; revert to old values on exit."""
            
    old_binds = {}
    new_binds = {}
    G = globals()

    for k, v in kwds.items():
        if k in G:
            old_binds[k] = G[k]
        else:
            new_binds[k] = v
    try:
        G.update(kwds)
        yield  # stuff within the context gets run here.
    finally:  # restore
        for k in new_binds:
            del G[k]
        G.update(old_binds)
        

# @contextlib.contextmanager
# def jump_if(condition, jump_lines):
#     #! Does it work?
#     def tracer(frame, event, arg):
#         # print(event, frame.f_lineno, arg)
#         ic(event, frame.f_locals, frame.f_lineno, arg)
#         if event == 'line':
#             if condition():
#                 ic()
#                 frame.f_lineno += jump_lines
#                 ic(frame.f_lineno)
#         return tracer
#     sys.settrace(tracer)
#     yield
#     sys.settrace(None)

    
class JumpIf:
    def __init__(self, condition, jump_lines):
        self.condition = condition
        self.jump_lines = jump_lines

    def tracer(self, frame, event, arg):
        if event == 'line':
            try:
                assert eval(self.condition, frame.f_locals)
                ic('meet', self.condition, frame.f_lineno)
                frame.f_lineno += self.jump_lines
                ic('jump', self.jump_lines, 'lines to', frame.f_lineno)
                # return sys.settrace(self._old_tracer)
            except:
                pass
        return self.tracer
    
    def __enter__(self):
        self._old_tracer = sys.gettrace()
        sys.settrace(self.tracer)
        
    def __exit__(self, exc_type, exc_value, traceback):
        sys.settrace(self._old_tracer)
        
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


def all_attrs(obj, _visited=None):
    if _visited is None:
        _visited = set()
    _visited.add(id(obj))
    return dict(
        (a, all_attrs(v, _visited))
        for a in dir(obj)
        if not a.startswith('_')
        for v in [getattr(obj, a)]
        if id(v) not in _visited and not callable(v)
    ) or obj

    
def pmap(f, lst, jobs=None):
    if jobs is None:
        jobs = os.cpu_count()
    l = int(len(lst) / jobs + 1 - 1e-8)
    splits = [lst[i*l:(i+1)*l] for i in range(jobs)]
    with Pool(jobs) as pool:
        pool.map(f, splits)
    

def outer_frame():
    return inspect.currentframe().f_back.f_back.f_locals


class Default:
    """Change to the default value if it is set to None,
       used as a class attribute."""
    placeholder = None

    def __init__(self, default):
        self.default = self.value = default

    def __set__(self, obj, value):
        if value is self.placeholder:
            self.value = self.default
        else:
            self.value = value

    def __get__(self, obj, type=None):
        return self.value


class IsInstance:

    def __init__(self, ns=None):
        if ns is None:
            self.ns = globals()
        else:
            self.ns = ns

    def __getattr__(self, type):
        ns = super().__getattribute__('ns')
        type = eval(type, ns)
        if hasattr(type, '__package__'):
            return IsInstance(type.__dict__)
        else:
            return lambda *args: all(isinstance(arg, type)
                                     for arg in args)

    def __call__(self, *types):
        return lambda *args: all(isinstance(arg, types)
                                 for arg in args)

    
if __name__ == '__main__':

    @JumpIf('x % 2', 2)
    def f(x):
        x *= 2
        x -= 1
        x += 3
        x //= 2
        x -= 2
        return x

    class TestJumpIf(unittest.TestCase):
        def test_jump_to(self):
            ic(f(1))
            ic(f(0))
            ic(f(-1))
    
    unittest.main()
    