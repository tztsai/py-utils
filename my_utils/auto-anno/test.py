# %%
from lib import *

def compose(f, g):
    return lambda x: f(g(x))

sup_types = compose(get_suptypes, get_type)
annotate = compose(get_full_name, get_annotation)

# %%
get_type([1, 0.0])

# %%
get_type((1, 0.0))

# %%
get_type((1, 2, 3, 4, 5))

# %%
sup_types(0.1)

# %%
sup_types((1.0, 'a'))

# %%
sup_types((1.0, 2.0, 3, 4, None))

# %%
sup_types(dict(a='a', b=None))

# %%
annotate([1, 2.0, 3])

# %%
annotate([1, None, 2])

# %%
annotate([dict(a=1, b=2), dict(a=None, b=2.0)])

# %%
annotate([(1, 2), (3, 4), (5, 6.0)])

# %%
annotate([[1, 2], [3, 4], [5, 6.0]])

# %%
annotate([(1, 2, 3, 4, 5), (6, 7, 8, 9, 10)])

# %%
annotate([{(1, 2): ['a', 'b', 'c'],
           (3, 4): ['d', 'e', 'f'],
           (2.0, 3): ['g', 'h', 'i']}])

# %%
import torch
x = torch.tensor([1, 2, 3])
records = [(torch.nn.ReLU(), x), (torch.nn.Tanh(), x)]
annotate(records)

# %%
from torch import Tensor, nn as NN
annotate(records)

# %%
records = [(NN.functional.relu, NN.Linear(3, 4).parameters())]
annotate(records)

# %%
