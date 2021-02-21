import functools
import inspect
import re
import logging
from logging import DEBUG, INFO, WARN, ERROR


_PREFIX = ''
def trace(fn):
    """A decorator that prints a function's name, its arguments, and its return
    values each time the function is called. For example,

    @trace
    def compute_something(x, y):
        # function body
    """
    def log(message):
        dbg(_PREFIX + re.sub('\n', '\n' + _PREFIX, str(message)))
        
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


class LogFormatter(logging.Formatter):

    formats = {
        DEBUG: ("%(module)s.%(funcName)s, L%(lineno)s:\n  %(msg)s"),
        INFO:  "%(msg)s",
        WARN:  "WARNING: %(msg)s",
        ERROR: "ERROR: %(msg)s"
    }

    def format(self, record):
        dct = record.__dict__
        fmt = LogFormatter.formats.get(record.levelno, self._fmt)
        return fmt % dct


logLevel = logging.DEBUG
logFormat = LogFormatter()

logger = logging.getLogger(__name__)
logger.setLevel(logLevel)

logHandler = logging.StreamHandler()
logHandler.setLevel(logging.DEBUG)
logHandler.setFormatter(logFormat)

logger.addHandler(logHandler)

dbg = logger.debug
info = logger.info
warn = logger.warning


def setloglevel(level):
    logger.setLevel(level)
