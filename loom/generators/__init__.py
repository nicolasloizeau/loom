"""Drawdown generators.

A drawdown is the h x w grid of 0/1 that tells, at each crossing of a warp
(vertical) thread and a weft (horizontal) thread, which one is on top:
1 = warp, 0 = weft. Row 0 is the top row.

A generator is a function D(w, h, seed, **params) that returns a drawdown,
registered under a name with the @generator("name") decorator. The settings
file picks it by that name ("pattern": {"generator": ..., "params": ...}).
To add one, write it in any module of this package and import that module at
the bottom of this file.
"""
import numpy as np

GENERATORS = {}


def generator(name):
    """Register a drawdown generator D(w, h, seed, **params) as `name`."""
    def register(f):
        if name in GENERATORS:
            raise ValueError(f"generator {name!r} is registered twice")
        GENERATORS[name] = f
        return f
    return register


def drawdown(name, w, h, seed, **params):
    """Run the generator `name` and check that it returned a drawdown."""
    if name not in GENERATORS:
        raise KeyError(f"unknown generator {name!r}; known: "
                       f"{', '.join(sorted(GENERATORS))}")
    d = np.asarray(GENERATORS[name](w, h, seed, **params))
    if d.shape != (h, w) or not np.isin(d, (0, 1)).all():
        raise ValueError(f"generator {name!r} must return a {h} x {w} array "
                         f"of 0 / 1, got shape {d.shape}")
    return d.astype(np.uint8)


# Importing the modules registers their generators.
from . import basic, ca1d, ca2d  # noqa: E402,F401
