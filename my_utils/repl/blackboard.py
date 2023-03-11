import sys
import os
import re
import msvcrt
import time
from typing import Any

try:
    from .unicode import subst, map_2chars
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from unicode import subst, map_2chars
    

getch = msvcrt.getwch

spaces = ' \t\r\n'        # invokes a substitution if possible
cancel_signal = '\x04'    # cancels the current input, here ^D
redo_signal = '\x1a'      # redo the previous input, here ^Z
exit_signal = '\x03'      # exits the program, here ^C
esc = '\x1b'              # also invokes a substitution

text_style = {
    'default': 0,       'bold': 1,          'no-bold': 22,      
    'red': 31,          'green': 32,        'blue': 34,
    'yellow': 33,       'magenta': 45,      'cyan': 46,
    'bright-blue': 94,      'bright-green': 92
}
for k, v in text_style.items():
    text_style[k] = esc + '[%dm' % v

sub_pre = text_style['green']          # the chars printed when a subst starts
sub_suf = text_style['default']        # the chars printed when a subst ends

arrow_map = dict(zip('HPMK', 'ABCD'))  # moves the cursor
arrow_dir = dict(zip('ABCD', 'UDRL'))  # corresponding directions


buffer = []         # buffer of input chars
record = []         # record of previous insertions and deletions
caret = 0           # position of insertion from the end of buffer
substart = None     # position of the last sub_pos from the end
free_cursor = False


def ins() -> int:
    return len(buffer) - caret


def write(s: str, track: int=0, style: Any=None) -> None:
    if type(s) is not str:
        s = ''.join(s)

    if style and style in text_style:
        style_ctrl_seq = text_style[style]
        sys.stdout.write(style_ctrl_seq)
    else:
        style_ctrl_seq = None
        
    if s == '\n':  # new line
        sys.stdout.write(' ' * caret + '\b' * caret)
        sys.stdout.write(s)
    else:
        sys.stdout.write(s)
        
    if style_ctrl_seq:
        sys.stdout.write(text_style['default'])
    
    bl = 0  # length of backspace
    
    if track:
        if '\b' in s:
            assert all(c == '\b' for c in s)
            op = 'd'  # delete
        else:
            op = 'i'  # insert

        buf = []
        for ch in s:
            if ch == '\b':
                if buffer:
                    buf.append(buffer.pop(-caret-1))
                else:
                    break
                bl += 1
            else:
                buf.append(ch)
                buffer.insert(ins(), ch)
                
        record.append((op, ''.join(buf)))

    # rewrite the tail after the caret
    tail = ''.join(buffer[ins():])
    if bl + len(tail) > 0:
        sys.stdout.write(tail)
        sys.stdout.write(bl * ' ')
        bl += len(tail)
        sys.stdout.write('\b' * bl)  # move back the caret
            
    sys.stdout.flush()
        

def delete(n: int=1, track: int=1) -> None:
    write('\b' * n, track)
    

def redo(n: int=1) -> None:
    for _ in range(n):
        if not record: break
        op, text = record.pop()
        if op == 'i':
            delete(len(text))
        else:
            write(text, 1)


def resetbuffer() -> None:
    global caret, substart
    buffer.clear()
    record.clear()
    caret = 0
    substart = None


def read(end: str='\r\n', indent: int=0) -> str:
    """Reads the input; supports writing LaTeX symbols by typing a tab
    at the end of a string beginning with a sub_pos.
    """
    assert end in spaces
    global substart
    
    resetbuffer()
    read.index = len(read.history)
    read.history.append(buffer)
    
    text = ''
    while True:
        end_ch = _read()
        i, j = substart, ins()
            
        if i is not None:
            # replace the expression with its latex symbol
            s = subst(''.join(buffer[i:j]))
            
            # remove substituted chars from the input
            delete(j - i)
            write(sub_suf)
            
            # if s[0] == 'x':  # a decorator, 'x' is a placeholder
            #     write(s[1:])
            #     move_cursor('K')  # move to the left of the decorator
            # else:
            write(s, 1)

            substart = None
            
        if end_ch in end:
            line = ''.join(buffer)
            next_indent = BracketTracker.next_insertion(' '*indent + line)
            
            if line and line[-1] == '\\':
                delete()
            else:
                indent = next_indent
                
            if indent:  # incomplete line
                write(end_ch, 1)
                write(' ' * indent)
                text += ''.join(buffer[:ins()])
                buffer[:] = buffer[ins():]
            else:
                for _ in range(caret):
                    move_cursor('M')  # move to the end of line
                write(end_ch)
                text += line
                read.history[-1] = text
                return text
        
        elif end_ch in spaces:
            if end_ch == '\t':  # TODO: auto-complete
                pass
            else:
                write(end_ch, 1)

read.index = 0
read.history = []
read.keywords = {}
read.highlight = text_style['bright-blue']


def _read() -> str:
    global substart
    c = -1
    edited = 0
    auto_sub = False  # flag of auto substitution
    
    while c:
        c = getch()

        # convert char here
        if c == '\r': c = '\n'
        elif c == '`': c = '⋅'

        if c in exit_signal:
            raise KeyboardInterrupt
        elif c in cancel_signal:
            raise IOError("input cancelled")
        elif c == esc:
            if substart is None:
                substart = ins()
                write(sub_pre)
            else:
                return esc
        elif c in spaces:
            return c[-1]  # '[-1]' removes '\r' from '\r\n'
        elif c == '\b':  # backspace
            if auto_sub:
                redo(2)
            elif caret < len(buffer):
                delete()
        elif c in '\x00\xe0':
            if (d := getch()) in 'KHMP':  # arrow key
                if edited and d in 'HP':
                    # set the last history to the current buffer
                    read.history[-1] = list(buffer)
                    read.index = len(read.history) - 1
                    edited = 0
                move_cursor(d)
                continue
            else:
                write(c + d, 1)
        else:
            write(c, 1)
        
        if (chs := ''.join(buffer[-2:])) in map_2chars:
            s = map_2chars[chs]
            delete(2)
            write(s, 1)
            auto_sub = True
        else:
            auto_sub = False
            
        edited = 1
    
    raise IOError("failed to read input")


def move_cursor(code: str) -> None:
    global caret, newline
    
    c = arrow_map[code]
    d = arrow_dir[c]
    cs = f'{esc}[{c}'
    
    if free_cursor:
        return write(cs)
    
    if d in 'UD':
        i = read.index + (1 if d == 'D' else -1)
        if 0 <= i < len(read.history):
            read.index = i
            caret = 0
            delete(len(buffer))
            write(read.history[i], 1)
    else:
        if d == 'L' and caret < len(buffer):
            caret += 1
            write(cs)
        elif d == 'R' and caret > 0:
            caret -= 1
            write(cs)
        # buf = list(buffer)
        # buf.insert(ins(), '^')
        # print(buf)

    
def input(prompt: str='', indent: int=0) -> str:
    write(prompt)
    return read(indent=indent)


# def print(*s, sep=' ', end='\n'):
#     s = sep.join(map(str, s)) + end
#     write(s)
    

class BracketTracker:
    parentheses = ')(', '][', '}{', '""'
    close_pars, open_pars = zip(*parentheses)
    par_map = dict(parentheses)
    stack = []

    @classmethod
    def push(cls: type, par: str, pos: int) -> None:
        if par in cls.open_pars:
            cls.stack.append((par, pos))
        else:
            raise SyntaxError('not an open bracket')

    @classmethod
    def pop(cls: type, par: str) -> None:
        if cls.stack and cls.stack[-1][0] == cls.par_map[par]:
            cls.stack.pop()
        else:
            cls.stack.clear()
            raise SyntaxError('bad brackets')

    @classmethod
    def next_insertion(cls: type, text: str) -> int:
        "Track the brackets in the line and return the appropriate pooint of the nest insertion."
        for line in text.splitlines():
            for i, c in enumerate(line):
                try:
                    cls.pop(c)
                except:
                    if c in cls.open_pars: cls.push(c, i)
                    elif c in cls.close_pars: raise
        return cls.stack[-1][1] + 1 if cls.stack else 0


def repl() -> None:
    while True:
        try:
            line = input()
        except KeyboardInterrupt:
            break
        except IOError:
            continue
        if line == 'exit': break
        write(line + '\n')


if __name__ == '__main__':
    repl()