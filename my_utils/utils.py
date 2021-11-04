import os
import sys
import inspect
import signal
import code
import contextlib
from multiprocessing import Pool


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
    "Bind global variables within a context; revert to old values on exit."
    old_binds = {}
    new_binds = {}
    G = globals()

    for k, v in kwds.items():
        G = globals()
        if k in G:
            old_binds[k] = G[k]
        else:
            new_binds[k] = v
    try:
        G.update(kwds)
        yield  # Stuff within the context gets run here.
    finally:
        [G.pop(k) for k in new_binds]
        G.update(old_binds)


def pmap(f, lst, jobs=None):
    if jobs is None:
        jobs = os.cpu_count()
    l = int(len(lst) / jobs + 1 - 1e-8)
    splits = [lst[i*l:(i+1)*l] for i in range(jobs)]
    with Pool(jobs) as pool:
        pool.map(f, splits)
    

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
