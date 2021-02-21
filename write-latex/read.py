import sys
import os
import re
import psutil
import msvcrt
from latex import subst


putch = msvcrt.putwch
getch = msvcrt.getwch


tab_space = 2
exit_signal = '\x03\x04'
ctrl_chars = re.compile(r'^[\x00-\x1f\x7f-\x9f]$')


def write(s: str):
    for c in s: putch(c)


def repl():
    while True:
        try:
            expr = read('>> ')
            try:
                val = eval(expr)
                if val is not None:
                    write(str(val) + '\n')
            except SyntaxError:
                exec(expr)
        except KeyboardInterrupt:
            write('Byebye!\n')
            return exit()


def read(prompt='', end='\n', sub='\t', ccl='\x1a'):
    """Reads the input; supports writing LaTeX symbols by typing a tab
    at the end of a string beginning with a backslash."""
    write(prompt)
    
    s = []
    while True:
        _read(s)

        if s[-1] == sub:  # substitute backslash if it exists
            i = rfind(s, '\\')
            if i is None: continue
            
            n_del = len(s) - i + tab_space - 1
            backspace(n_del)  # remove substituted chars from console
            s, t = s[:i], s[i:-1]
            
            t = subst(''.join(t))
            write(t)
            s.extend(t)
            
        elif s[-1] == ccl:  # cancel input
            raise IOError("input cancelled")

        elif s[-1] == end:
            return ''.join(s[:-1])
        
    
def _read(s=[]):
    c = 1
    while c and not is_ctrl_char(c):
        c = getch()

        if c == '\r':
            c = '\n'

        if c in exit_signal:
            raise KeyboardInterrupt

        if c == '\t':
            write('  ')
        elif c == '\x08':  # backspace
            backspace()
            if s: s.pop()
            continue
        else:
            putch(c)

        s.append(c)

    return s


def rfind(l: list, x):
    i = len(l) - 1
    while i >= 0:
        if l[i] == x:
            return i
        else:
            i -= 1
            

def backspace(n=1):
    write('\b' * n)
    write(' ' * n)
    write('\b' * n)
    

def is_ctrl_char(ch):
    return type(ch) is str and ctrl_chars.match(ch)


if __name__ == '__main__':
    repl()
