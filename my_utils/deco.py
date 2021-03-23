from time import time
from functools import update_wrapper
# When you use a decorator to define the function, the original function is
# shadowed by the function returned by the decorator. This causes that if you
# call the "help" function upon the decorated function, the info it displays is
# that of the returned function of the decorator. "update_wrapper" is used to 
# deal with this problem.
# Use the built-in function "help" to see the docstrings.


def decorator(dec):
    """Makes the decorated decorator such that when it decorates a function, the
    decorated function looks like the original function."""
    def _dec(f):
        "This will be displayed if the second update_wrapper is absent."
        return update_wrapper(dec(f), f)  # update_wrapper returns the wrapper
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