# stdlib
import os
import re
import sys
import ast
import runpy
import shutil
import argparse

# third party
import cloudpickle

# local
from .lib import *


# ** read system arguments and set up global variables **

parser = argparse.ArgumentParser()
parser.add_argument("script", help="the script to run")
parser.add_argument("-n", type=int, default=1, help="number of times to run the script")
parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument(
    "-i", action="store_true", help="prompt before overwriting each script"
)
parser.add_argument(
    "--log", default="type_records.pkl", help="output file for type records"
)
parser.add_argument("--cwd", default=None, help="working directory")
parser.add_argument(
    "--backup", action="store_true", help="backup the scripts before annotating them"
)

ARGS = parser.parse_args()
DIR = os.path.dirname(os.path.abspath(ARGS.script))
CWD = ARGS.cwd or DIR

try:
    TYPE_RECS = cloudpickle.load(open(ARGS.log, "rb"))
    FIRST_RUN = False
except:
    TYPE_RECS = {}  # {filename: {(lineno, funcname): {argname: [type]}}}}
    FIRST_RUN = True

sys.path.extend([DIR, CWD])


# ** run the script n times to collect type records **

def profiler(frame, event, arg):
    if event in ("call", "return"):
        filename = os.path.abspath(frame.f_code.co_filename)
        funcname = frame.f_code.co_name
        
        if filename.endswith(".py") and funcname[0] != "<" and CWD in filename:
            recs = get_record(TYPE_RECS, filename)
            
            if "globals" not in recs:
                recs["globals", None] = {
                    id(v): k for k, v in frame.f_globals.items() if k[0] != "_"
                }
                
            if event == "call":
                # print(filename, funcname, frame.f_lineno, frame.f_locals)
                arg_types = {var: get_type(val) for var, val in frame.f_locals.items()}
                lineno = frame.f_lineno
            else:
                arg_types = {"return": get_type(arg)}
                #! assumes no nested function has the same name as the outer function
                lineno = max(ln for ln, fn in recs 
                             if fn == funcname and ln <= frame.f_lineno)

            rec = get_record(recs, (lineno, funcname))
            for k, v in arg_types.items():
                get_record(rec, k, []).append(v)
                
    return profiler

def get_record(recs, key, default=None):
    if default is None:
        default = {}
    if FIRST_RUN:
        return recs.setdefault(key, default)
    else:
        try:
            return recs[key]
        except KeyError:
            os.remove(ARGS.log)
            raise SystemExit('Files have been modified since the last run.')


sys.setprofile(profiler)

for _ in range(ARGS.n):
    runpy.run_path(sys.argv[1], run_name="__main__")

sys.setprofile(None)

with open(ARGS.log, "wb") as f:
    cloudpickle.dump(TYPE_RECS, f)


# ** write the type annotations to the script **

annotations = get_type_annotations(TYPE_RECS)

for path in annotations:
    s = annotate_script(path, annotations[path], ARGS.verbose)
    if s is None:
        continue
    if ARGS.backup:
        shutil.copy(path, path + ".bak")
    if not ARGS.i or input(f"Overwrite {path}? ").lower() == "y":
        with open(path, "w", encoding="utf8") as f:
            f.write(s)
