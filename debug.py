"""The UCB module contains functions specific to 61A projects at UC Berkeley."""

import functools
import inspect
import re


_PREFIX = ''
def trace(fn):
    """A decorator that prints a function's name, its arguments, and its return
    values each time the function is called. For example,

    @trace
    def compute_something(x, y):
        # function body
    """
    @functools.wraps(fn)
    def wrapped(*args, **kwds):
        global _PREFIX
        reprs = [repr(e) for e in args]
        reprs += [repr(k) + '=' + repr(v) for k, v in kwds.items()]
        log('{0}({1})'.format(fn.__name__, ', '.join(reprs)) + ':')
        _PREFIX += '    '
        try:
            result = fn(*args, **kwds)
            _PREFIX = _PREFIX[:-4]
        except Exception as e:
            log(fn.__name__ + ' exited via exception')
            _PREFIX = _PREFIX[:-4]
            raise
        # Here, print out the return value.
        log('{0}({1}) -> {2}'.format(fn.__name__, ', '.join(reprs), result))
        return result
    return wrapped


def log(message):
    """Print an indented message (used with trace)."""
    line = _PREFIX + re.sub('\n', '\n' + _PREFIX, str(message))
    if log.out == 'stdout': print(line)
    else: log.out.write(line + '\n')

log.out = 'stdout'


def log_current_line():
    """Print information about the current line of code."""
    frame = inspect.stack()[1]
    log('Current line: File "{f[1]}", line {f[2]}, in {f[3]}'.format(f=frame))

