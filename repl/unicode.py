
from IPython.core.completer import IPCompleter


extra_mappings = {
    'sum': 'Sigma',
    'prod': 'Pi',
    '/\\': 'land',
    '\\/': 'lor',
    '->': 'rightarrow',
    '<-': 'leftarrow',
    '=>': 'Rightarrow',
    '<=': 'Leftarrow',
    '^T': 'ᵀ',
    '*': 'times',
    'i': 'ⅈ',
    'e': 'ℯ',
    'Z': 'mathbb{Z}',
    'Q': 'mathbb{Q}',
    'R': 'mathbb{R}',
    'C': 'mathbb{C}',
    'inf': 'infty',
    'ga': 'alpha',
    'gb': 'beta',
    'gd': 'delta',
    'ge': 'epsilon',
    'gg': 'gamma',
    'gi': 'iota',
    'gk': 'kappa',
    'gl': 'lambda',
    'go': 'omega',
    'gs': 'sigma',
    'gu': 'upsilon',
    'deg': '°',
    'ang': '∠',
    'd': '∂',
    'E': 'exists',
    'A': 'forall',
    'grin': '😁',
    'haha': '😂',
    'smile': '🙂',
    'lol': '🤣',
    'fire': '🔥',
    'cow': '🐮',
    'monkey': '🐒',
    'horse': '🐴',
    'tree': '🌲',
    'cake': '🍰',
    'red': '🟥',
    'green': '🟩',
    'blue': '🟦',
    # 'white': '⬜',
    # 'black': '⬛'
}

map_2chars = {
    '/\\': '∧', '\\/': '∨', '/_': '∠', '+-': '±',
    '<<': '⟨', '>>': '⟩', '->': '→', '<-': '←'
}

def subst(s: str) -> str:
    """Substitute escaped characters."""
    s = extra_mappings.get(s, s)
    _, matches = IPCompleter.latex_matches(None, s)
    return matches[0] if len(matches) == 1 else s