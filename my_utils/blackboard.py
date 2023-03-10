import sys
import os
import re
import msvcrt
import time
from IPython.core.completer import IPCompleter


getch = msvcrt.getwch

spaces = ' \t\r\n'        # invokes a substitution if possible
cancel_signal = '\x1a'    # cancels the current input, here ^Z
exit_signal = '\x03\x04'  # exits the program, here ^C or ^D

arrow_map = dict(zip('HPMK', 'ABCD'))  # moves the cursor
arrow_dir = dict(zip('ABCD', 'UDRL'))  # corresponding directions


buffer = []
caret = 0           # position of insertion from the end of buffer
backslash = None    # position of the last backslash from the end
newline = False


def ins():  # insertion position from the beginning
    return len(buffer) - caret


def write(s, track=False):
    sys.stdout.write(s)
    sys.stdout.flush()

    if track:
        global newline
        newline = False
        for ch in s:
            buffer.insert(ins(), ch)
        if tail := ''.join(buffer[ins():]):
            sys.stdout.write(tail)
            sys.stdout.write('\b' * caret)  # move back the caret
            sys.stdout.flush()


def delete(n=1):
    write('\b' * n)
    write(' ' * n)
    write('\b' * n)
    for _ in range(n):
        buffer.pop(-caret-1)


def resetbuffer():
    global caret
    caret = 0
    buffer.clear()


def read(end='\r\n'):
    """ Reads the input; supports writing LaTeX symbols by typing a tab
    at the end of a string beginning with a backslash. """
    assert end in spaces
    global backslash

    resetbuffer()

    while True:
        end_ch = _read()

        i, j = backslash, ins()

        if i is not None:
            # the part to be replaced
            t = buffer[i:j]

            # remove substituted chars from the input
            delete(j - i)

            # substitute the expression into its latex symbol
            t = subst(''.join(t))

            write(t, True)
            backslash = None

        if end_ch == ' ':  # still print the last char
            write(end_ch, True)
        elif end_ch in '\r\n':
            write(end_ch)

        if end_ch in end:
            return ''.join(buffer)


def _read():
    global backslash
    c = -1

    while c:
        c = getch()

        if c == '\r':
            c += '\n'
        elif c == '\\':
            backslash = ins()

        if c in exit_signal:
            raise KeyboardInterrupt
        elif c in cancel_signal:
            raise IOError("input cancelled")
        elif c in spaces:
            return c
        elif c == '\b':  # backspace
            if caret < len(buffer):
                delete()
        elif c in '\x00\xe0':  # arrow key
            if (d := getch()) in 'KHMP':
                move_cursor(d)
            else:
                write(c + d, True)
        else:
            write(c, True)

    raise IOError("failed to read input")


def move_cursor(code):
    global caret, newline

    c = arrow_map[code]
    d = arrow_dir[c]
    cs = '\x1b[' + c

    write(cs)
    if d in 'UD':  # up or down; TODO
        newline = True
    elif not newline:
        if d == 'L' and caret < len(buffer):
            caret += 1
            # write(cs, False)
        elif d == 'R' and caret > 0:
            caret -= 1
            # write(cs, False)


def input(prompt=''):
    write(prompt)
    return read()


class BracketTracker:

    parentheses = ')(', '][', '}{'
    close_pars, open_pars = zip(*parentheses)
    par_map = dict(parentheses)

    def __init__(self):
        self.stk = []

    def push(self, par, pos):
        self.stk.append((par, pos))

    def pop(self, par):
        if self.stk and self.stk[-1][0] == self.par_map[par]:
            self.stk.pop()
        else:
            self.stk.clear()
            raise SyntaxError('bad parentheses')

    def next_insertion(self, line):
        "Track the brackets in the line and return the appropriate pooint of the nest insertion."
        for i, c in enumerate(line):
            if c in self.open_pars:
                self.push(c, i)
            elif c in self.close_pars:
                self.pop(c)
        return self.stk[-1][1] + 1 if self.stk else 0


extra_mappings = {
    '\\sum': '\\Sigma',
    '\\prod': '\\Pi',
    '\\/\\': '\\land',
    '\\\\/': '\\lor',
    '\\->': '\\rightarrow',
    '\\<-': '\\leftarrow',
    '\\=>': '\\Rightarrow',
    '\\<=': '\\Leftarrow',
    '\\*': '\\times',
    '\\i': 'ⅈ',
    '\\e': 'ℯ',
    '\\inf': '\\infty',
    '\\ga': '\\alpha',
    '\\gb': '\\beta',
    '\\gd': '\\delta',
    '\\ge': '\\epsilon',
    '\\gg': '\\gamma',
    '\\gi': '\\iota',
    '\\gk': '\\kappa',
    '\\gl': '\\lambda',
    '\\go': '\\omega',
    '\\gs': '\\sigma',
    '\\gu': '\\upsilon',
    '\\deg': '°',
    '\\ang': '∠',
    '\\dee': '∂',
    '\\E': '\\exists',
    '\\A': '\\forall',
    '\\grin': '😁',
    '\\haha': '😂',
    '\\smile': '🙂',
    '\\lol': '🤣',
    '\\fire': '🔥',
    '\\cow': '🐮',
    '\\monkey': '🐒',
    '\\horse': '🐴',
    '\\tree': '🌲',
    '\\cake': '🍰',
    '\\red': '🟥',
    '\\green': '🟩',
    '\\blue': '🟦',
}


def subst(s):
    """Substitute escaped characters."""
    s = extra_mappings.get(s, s)
    # return symbols.get(s, s)
    _, matches = IPCompleter.latex_matches(None, s)
    return matches[0] if len(matches) == 1 else s


while True:
    try:
        line = input('>>> ')
    except KeyboardInterrupt:
        write('\n')
        break
    except IOError as e:
        write(str(e) + '\n')
        continue
    if line:
        write(line + '\n')
    if line == 'exit':
        break
