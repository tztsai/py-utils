# %%
import pytest
from lib import *

# %%
get_type(2.0)

# %%
get_annotation([1, 2.0, 3])

# %%
get_type((1, 2))

# %%
get_suptypes(get_type((1.0, 2.0, 'a')))

# %%
get_suptypes(get_type((1.0, 2.0, None, None, None)))

# %%
get_annotation([dict(a=1, b=2), dict(a=None, b=2.0)])

# %%
get_annotation([(1, 2), (3, 1), (2.0, 'str')])

# %%
get_annotation([(1, 2, 3, 4, 5), (3, 1, 9, 2.0, 0)])

# %%
get_annotation([1, None, 2])

# %%