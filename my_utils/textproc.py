import os, re
from cmd import Cmd
from itertools import chain


usage = """Usage:

q/quit: quit the program

l [begin=1] [lines=10]: display lines

d [lines]: delete [lines]
    Syntax:
    lines := <int/range>,<int/range>,... (comma seperated, space not allowed)
    range := [start=<empty>]:[end=<empty>] (inclusive)
    Note that a single : can represent the whole file.

find [exp]: find all occurrences of [exp]
    Syntax:
    [exp] is wrapped by '' or //. If the former, it is a plain text; otherwise, it is a regex.

swp [i] [j]: swap lines [i] and [j]

i [lines] [text]: insert [text] (should be surrounded by '') into [lines]

subs [lines] [target] [sub] [sub] ...: substitute [target]
[target] can be plain text or regex. If [target] is plain text, then there can be only one [sub] and all [target] is replaced by [sub]. Otherwise, there can be the number of [sub] should equal to the number of groups in the [target] regex. Each [sub] can be plain text or a special expression wrapped by ``. This expression has parameters _0 (the matched string), _1, _2, ... (the matched groups); the single _ represents the matched group corresponding to the current [sub]. Its syntax follows the python syntax.
    Examples:
    > subs 1:10 'Shakespeare' '莎士比亚'
    This just replace all 'Shakespeare' in the first 10 lines with '莎士比亚'.
    > subs : /(an? )([a-zA-Z\-]+)/ '' `_+'es' if _[-2:] in ['ch', 'sh'] else _[:-1]+'ies' if _[-1]=='y' else _+'s'`
    This example uses a regex with 2 groups: the first matches 'a ' or 'an ' and the second matches the  the following word. Then, the first [sub] is just an empty string, so as to remove this group; the second is a python expression, which checks the tail of this word - if it is 'ch' or 'sh', then append 'es' to this word; if it is 'y', then remove the 'y' and append 'ies'; otherwise, simply append 's'.

w/w!: write the file (with a '!', there will be no confirmation)
"""


class Text: #(Cmd):
    def __init__(self, file_name):
        super().__init__()
        self.filename = file_name
        file = open(file_name, 'r', encoding='utf8')
        lines = [l[:-1] if l[-1] in '\r\n' else l for l in file.readlines()]
        self.lines = [Line(l) for l in lines]
        self.linenum = len(self.lines)
        file.close()
        os.system(f"cp {file_name} {file_name}.backup")

    def __str__(self):
        return '\n'.join(map(str, self.lines))

    def swap(self, l1, l2):
        "swap lines l1 and l2"
        self.lines[l1], self.lines[l2] = self.lines[l2], self.lines[l1]

    def delete(self, l):
        "delete line l"
        self.lines = self.lines[:l] + self.lines[l+1:]

    def insert(self, l, text):
        "insert a line at line l"
        self.lines.insert(l, Line(text))

    def join(self, l):
        "join line l with line l+1"
        assert l+1 < self.linenum
        self.lines[l].strip(left=False)
        self.lines[l+1].strip(right=False)
        self.lines[l] = self.lines[l].s + ' ' + self.lines[l+1].s
        del self.lines[l+1]

    def maplines(self, op, lns):
        for l in lns: op(self.lines[l])

    def display(self, begin=0, ln_num=10, show_ln_num=True):
        for i in range(begin, self.linenum):
            if i >= begin+ln_num: break
            print((f'{i+1}  |' if show_ln_num else '') + self.lines[i].s)

    def write(self):
        file = open(self.filename, 'w', encoding='utf8')
        file.write(str(self))
        file.close()


class Line:
    def __init__(self, string):
        self.s = string

    def __str__(self):
        return self.s

    def insert(self, text, pos): 
        "insert text at pos"
        self.s = self.s[:pos] + text + self.s[pos:]

    def strip(self, left=True, right=True):
        "strip the space on the left or/and right"
        if left and right:
            self.s = self.s.strip()
        elif left:
            self.s = self.s.lstrip()
        elif right:
            self.s = self.s.rstrip()

    def adjust_space(self, exclude_leading=True):
        "set all space between words to 1 sp"
        def leading_space(s):
            return re.match(r'\s*', s)[0]
        s = self.s
        lsp = leading_space(s)
        self.s = ' '.join(s.split())
        if exclude_leading:
            self.s = lsp + self.s

    def replace(self, pattern, substitutes):
        def repl(m):
            groups = len(m.groups())
            assert groups == len(substitutes)
            s = m[0]
            splits = []
            k = 0
            for g in range(groups):
                i, j = [x - m.start() for x in m.span(g+1)]
                splits.append(s[k:i])
                if callable(substitutes[g]):
                    splits.append(substitutes[g](m[g+1], m))
                else:
                    splits.append(substitutes[g])
                k = j
            splits.append(s[k:])
            return ''.join(splits)
        self.s, count = pattern.subn(repl, self.s)
        return count


def read(text: Text, exp):

    def read_linenums(exp):
        "syntax: b1[:e1],b2[:e2],..."
        def eval_nums(subexp):
            indices = subexp.split(':')
            colon = subexp.find(':')
            if colon < 0: return [int(subexp)]
            first, second = subexp[:colon], subexp[colon+1:]
            begin = int(first) if first else 1
            end = int(second) if second else len(text.lines)
            return range(begin-1, end)
        exps = exp.split(',')
        return chain(*map(eval_nums, exps))

    def parse_subs(exp):
        def eval_repl(repl):
            if repl[0] == "'":
                return repl[1:-1]
            else:
                body = re.sub('_([0-9]+)', lambda m: f'__[{m[1]}]', repl[1:-1])
                return eval('lambda _, __: ' + body)
        quotes = "'`"
        subs = []
        i = 0
        while i < len(exp):
            while i < len(exp) and exp[i] not in quotes: i += 1
            if i >= len(exp): break
            j = i + 1
            while j < len(exp) and exp[j] != exp[i]: j += 1
            if j >= len(exp): raise SyntaxError('unpaired quotes!')
            subs.append(eval_repl(exp[i:j+1]))
            i = j + 1
        return subs

    cmd = exp.split(None, 1)
    op = cmd[0]
    line_ops = {}
    
    if op in ('q', 'quit'):
        raise KeyboardInterrupt
    elif op == 'l':
        text.display(*([] if len(cmd) == 1 else map(int, cmd[1].split())))
    elif op == 'w':
        confirm = input('Are you sure? [y/N]: ')
        if confirm == 'y': text.write()
    elif op == 'w!':
        text.write()
    elif op == 'rev':
        os.system(f'cp {text.filename}.backup {text.filename}')
    elif op == '1sp':
        for ln in text.lines: ln.adjust_space()
    elif op in ('h', 'help'):
        print(usage)
    else:
        if len(cmd) < 2:
            raise SyntaxError("Not enough arguments!")

        if op == 'swp':
            try:
                l1, l2 = map(int, cmd[1].split())
            except:
                raise SyntaxError("swp command only accept 2 integers!")
            text.swap(l1, l2)
            return

        if op == 'find':
            positions = []
            if cmd[1][0] == cmd[1][-1] == '/':
                pattern = re.compile(cmd[1][1:-1])
                for l, line in enumerate(text.lines):
                    for m in pattern.finditer(line.s):
                        positions.append((l, m.start()))
            else:
                target = cmd[1]
                for l, line in enumerate(text.lines):
                    try:
                        positions.append((l, line.s.index(target)))
                    except ValueError:
                        pass
            for pos in positions:
                print(f'Ln {pos[0]}, Col {pos[1]}')
            return

        # multiline operations
        lines_exp, rest = cmd[1].split(None, 1)
        ln_nums = read_linenums(lines_exp)
        if op == 'd':
            for ln in ln_nums: text.delete(ln)
        elif op == 'i':
            text = rest.split("'")[1]
            for ln in ln_nums: text.insert(ln, text)
        elif op == 'subs':
            if rest[0] == '/':
                regex, rest = rest.split('/', 2)[1:]
                pattern = re.compile(regex)
            elif rest[0] == "'":
                target, rest = rest.split("'", 2)[1:]
                pattern = re.compile(f'({target})')
            else:
                raise SyntaxError("invalid subs syntax!")
            for ln in ln_nums: 
                text.lines[ln].replace(pattern, parse_subs(rest.strip()))
        else:
            exec(exp)


def repl(filename):
    text = Text(filename)
    while True:
        try:
            read(text, input('> '))
        except KeyboardInterrupt:
            return
        except Exception as err:
            print("Error: ", err)


if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    repl(filename)
