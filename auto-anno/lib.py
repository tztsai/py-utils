import io
import re
import ast
import isort
import black
import inspect
from numbers import *
from functools import partial
from importlib import import_module
from itertools import islice, product
from typing import Any, Optional, Union
from collections import defaultdict
from collections.abc import Callable, Iterator


TYPE_MAP = {  # maps of type annotations
    Integral: int,
    Real: float,
    Complex: complex,
    object: Any,
}

REQ_IMPORTS = {Any, Optional, Union, Callable, Iterator}


def get_type(x):
    """
    Examples:
    >>> f = lambda x: print(get_full_name(get_type(x)))
    >>> f(None)
    None
    >>> f([])
    list
    >>> f([1, 2, 3])
    list[Integral]
    >>> f([1, 'a'])
    list
    >>> f(dict(a=0.9, b=0.1))
    dict[str, Real]
    >>> f(dict(a=0.9, b='a'))
    dict[str, object]
    >>> f({1, 2.0, None})
    set[Optional[Real]]
    >>> f(str)
    type
    >>> f(True)
    bool
    >>> f((1, 2.0))
    tuple[Integral, Real]
    >>> f(tuple(range(9)))
    tuple[Integral, ...]
    >>> f(iter(range(9)))
    Iterator[Integral]
    >>> f((i if i % 2 else None for i in range(9)))
    Iterator[Optional[Integral]]
    """

    def dispatch(T, *xs, maxlen=4):
        xs = [list(map(get_type, l)) for l in xs]
        if not xs or min(map(len, xs)) == 0:  # empty collection
            return T
        ts = tuple(map(get_common_suptype, xs))
        if len(ts) == 1:
            t = ts[0]
        elif len(ts) > maxlen:  # use [t, ...] for long tuples
            t = get_common_suptype(ts)
        else:
            t = ts
        if t is object:
            return T
        elif len(ts) > maxlen:
            return T[t, ...]
        else:
            return T[t]

    if x is None:
        return None
    if inspect.isfunction(x) or inspect.ismethod(x):
        return Callable
    for t in (list, set, frozenset):
        if isinstance(x, t):
            return dispatch(t, x)
    if isinstance(x, tuple):
        return dispatch(tuple, *[[a] for a in x])
    if isinstance(x, dict):
        return dispatch(dict, x.keys(), x.values())
    if isinstance(x, io.IOBase):
        return type(x)
    if isinstance(x, Iterator):  #! may be too general
        return dispatch(Iterator, islice(x, 10))
    if isinstance(x, bool):
        return bool
    if isinstance(x, Integral):
        return Integral
    if isinstance(x, Real):
        return Real
    if isinstance(x, Complex):
        return Complex
    return type(x)


def get_suptypes(t, type_map: Optional[dict]=None):
    """ Get all supertypes of a type. """
    
    def suptypes_of_subscripted_type(t):
        T = t.__origin__
        args = t.__args__
        sts = [T[ts] for ts in 
               product(*[get_suptypes(t, type_map) for t in args])
               if not (T is Union and object in ts)
               if not (T is tuple and set(ts) == {object, ...})
               if not all(t is object for t in ts)]
        return sts + get_suptypes(T, type_map)

    if hasattr(t, "__origin__"):
        sts = suptypes_of_subscripted_type(t)
    elif inspect.isclass(t):
        if issubclass(t, type):
            sts = list(t.__mro__)
        else:
            sts = list(t.mro())
    elif t in (Ellipsis, None, Any):
        sts = [t]
    elif t in (Optional, Union):
        sts = [object]
    elif type(t) is str:  # used type name as annotation
        sts = [t, object]
    else:
        raise TypeError(f"unsupported type: {t}")

    if type_map:
        sts = [type_map.get(t, t) for t in sts]
    return sts


def get_common_suptype(ts, type_map=None):
    """ Find the most specific common supertype of a collection of types. """
    
    ts = set(ts)
    assert ts, "empty collection of types"

    optional = any(t is None for t in ts)
    ts.discard(None)

    if not ts:
        return None

    sts = [get_suptypes(t, type_map) for t in ts]
    for t in min(sts, key=len):
        if all(t in ts for ts in sts):
            break
    else:
        return Any

    if optional:
        t = Optional[t]
    return t


# for testing only
def get_annotation(values):
    """ Get the type annotation from a list of values. """
    return get_common_suptype(map(get_type, values), type_map=TYPE_MAP)


def get_full_name(x, global_vars: Optional[dict]=None):
    """ Get the full name of a type. `global_vars` is a dict of {object_id: name}.
    
    Examples:
    >>> import numpy as np
    >>> G = lambda: {id(v): k for k, v in globals().items() if k[0] != '_'}
    >>> get_full_name(np.ndarray, G())
    'np.ndarray'
    >>> import scipy as sp
    >>> get_full_name(sp.sparse.csr_matrix, G())
    'sp.sparse.csr_matrix'
    >>> import scipy.sparse as sparse
    >>> get_full_name(sparse.csr_matrix, G())
    'sparse.csr_matrix'
    >>> from typing import Optional
    >>> get_full_name(dict[str, Optional[np.ndarray]], G())
    'dict[str, Optional[np.ndarray]]'
    """

    def get_name(x):
        if x.__module__ == "typing":
            return x._name
        return getattr(x, "__qualname__", x.__name__)

    if x is Ellipsis:
        return "..."
    if x is None:
        return "None"
    if type(x) is str:
        return repr(x)
    if x in REQ_IMPORTS:  # requires importing its module
        return get_name(x)
    
    if global_vars is None:
        gs = inspect.currentframe().f_back.f_globals.items()
        global_vars = {id(v): k for k, v in gs if k[0] != '_'}

    if id(x) in global_vars:
        return global_vars[id(x)]
    
    # handle the subscripted types
    if hasattr(x, "__origin__"):
        T, args = x.__origin__, x.__args__
        if T is Union and len(args) == 2 and args[1] is type(None):
            T, args = Optional, args[:1]
        T = get_full_name(T, global_vars)
        args = ", ".join(get_full_name(a, global_vars) for a in args)
        return f"{T}[{args}]"
    
    # handle the built-in types
    if x.__module__ == "builtins":
        return x.__name__
    
    # find the module names
    names = (f"{x.__module__}.{get_name(x)}").split(".")[::-1]
    mods = [import_module(names[-1])]
    for name in names[-2::-1]:
        mods.append(getattr(mods[-1], name))
    mods = mods[::-1]
    
    # find the first module that is imported
    for i, (name, mod) in enumerate(zip(names, mods)):
        if id(mod) in global_vars:
            names = names[:i] + [global_vars[id(mod)]]
            mods = mods[: i + 1]
            break
        
    # remove unnecessary intermediate modules
    for k in range(1, len(names)):
        if k >= len(names) - 1:
            break
        for i, (name, mod) in enumerate(zip(names, mods)):
            if i + 1 + k >= len(names):
                break
            if hasattr(mods[-k], name):
                names = names[: i + 1] + names[-k:]
                mods = mods[: i + 1] + mods[-k:]
                break

    return ".".join(names[::-1])


def find_defs_in_ast(tree):
    def recurse(node):  # should be in order
        if isinstance(node, ast.FunctionDef):
            yield node
        for child in ast.iter_child_nodes(node):
            yield from recurse(child)
    yield from recurse(tree)


def find_imports_in_ast(tree: ast.Module):
    # only "import from" statements at the global level
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            yield node
        # elif isinstance(node, ast.Import):
        #     yield node


def get_def_lineno(def_node: ast.FunctionDef):
    if def_node.decorator_list:
        return def_node.decorator_list[0].lineno
    return def_node.lineno


def annotate_def(def_node: ast.FunctionDef, type_records) -> bool:
    """ Change the annotations of a ast.FunctionDef node in-place.
    Return True if the node is changed. """

    key = (get_def_lineno(def_node), def_node.name)
    
    if key not in type_records:
        return False  # no type records for this function
    
    records = type_records[key]
    global_vars = type_records["globals", None]
    
    A = def_node.args
    all_args = A.posonlyargs + A.args + A.kwonlyargs
    defaults = dict(zip(reversed([a.arg for a in A.args + A.kwonlyargs]),
                        reversed(A.defaults + A.kw_defaults)))
    all_args.extend(filter(None, [A.vararg, A.kwarg]))
    
    union = partial(get_common_suptype, type_map=TYPE_MAP)
    
    changed = False
    for a in all_args:
        if a.annotation or a.arg == "self":
            continue
        t = union(records[a.arg])
        if a == A.vararg:
            if t is tuple:
                t = Any
            else:
                assert t.__origin__ is tuple
                if (  # tuple[t] or tuple[t, ...]
                    len(t.__args__) == 1
                    or len(t.__args__) == 2
                    and t.__args__[1] is Ellipsis
                ):
                    t = t.__args__[0]
                else:
                    t = union(t.__args__)
        elif a == A.kwarg:
            if t is dict:
                t = Any
            else:
                assert t.__origin__ is dict
                t = t.__args__[1]
        if t is None:
            t = Any
        default = defaults.get(a.arg, ...)
        if isinstance(default, ast.NameConstant):
            t = union([t, get_type(default.value)])
        anno = get_full_name(t, global_vars)
        a.annotation = ast.Name(anno)
        changed = True

    if def_node.returns is None:
        t = union(records["return"])
        anno = get_full_name(t, global_vars)
        def_node.returns = ast.Name(anno)
        def_node.returns.lineno = (max(a.lineno for a in all_args)
                                   if all_args else def_node.lineno)
        # default to the same line as the last arg
        changed = True
        
    return changed


def annotate_script(filepath, type_records, verbose=False) -> str:
    """ Output the annotated version of the script at `filepath`. """
    
    s = open(filepath, encoding="utf8").read()
    lines = s.splitlines()
    tree = ast.parse(s)
    
    # annotate function definitions in-place and find the changed ones
    defs = [d for d in find_defs_in_ast(tree)
            if annotate_def(d, type_records)]
    
    if not defs:
        return None
    
    # find all imports in the script
    imps = list(find_imports_in_ast(tree))
    
    # find all required imports
    required_imports = defaultdict(list)
    for t in REQ_IMPORTS:
        mod = t.__module__
        name = getattr(t, "__name__", getattr(t, "_name", None))
        required_imports[mod].append(name)
    
    # # append missing names in imported modules
    # for imp in imps:
    #     if imp.module in required_imports:
    #         imp_names = set(a.name for a in imp.names)
    #         for name in required_imports.pop(imp.module):
    #             if name not in imp_names:
    #                 imp.names.append(ast.alias(name))
    #         lines[imp.lineno-1:imp.end_lineno] = '\n'
    #         lines[imp.lineno-1] = ast.unparse(imp)
    
    if verbose:
        print("Adding annotations to", filepath, "\n")
        
    starts, ends, sigs = [], [], []
    for node in defs:
        ln0, ln1 = get_def_lineno(node), node.body[0].lineno
        starts.append(ln0 - 1)
        ends.append(ln1 - 1)
        node.body = []  # only keep signature
        indent = re.match(r"\s*", lines[ln0 - 1])[0]
        line = indent + ast.unparse(node).replace("\n", "\n" + indent)
        sigs.append(line)
        if verbose:
            print("Old:", *lines[ln0 - 1 : ln1 - 1], sep="\n")
            print(">" * 80)
            print("New:", sigs[-1], sep="\n")
            print("-" * 80)
    
    # insert the new signatures
    new_lines = []
    for s, e, sig in zip([None] + ends, starts + [None], sigs + [None]):
        new_lines.extend(lines[s:e])
        if sig is not None:
            new_lines.append(sig)

    # insert missing imports
    for mod, names in required_imports.items():
        new_lines.insert(0, f"from {mod} import {', '.join(names)}")

    # reformat new script
    new_script = "\n".join(new_lines)
    new_script = isort.code(new_script)
    new_script = black.format_str(new_script, mode=black.Mode())
    return new_script


if __name__ == "__main__":
    import doctest
    doctest.testmod()
