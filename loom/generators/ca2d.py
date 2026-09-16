"""2D cellular automata grown from the centre.

The grid starts with a few live cells in its centre (`start`) and grows for
`steps` steps on a grid large enough that the pattern never reaches its
edges; the centre h x w piece is kept, so the pattern fills the frame. The
rules treat all directions alike, so a single cell gives 4-fold symmetric,
medallion-like patterns. `steps` must be large enough for the growth to
cover the frame: about max(w, h) / 2 for total9 (square growth) and
(w + h) / 2 for outer5 (diamond growth).
"""
import numpy as np

from . import generator


def _outer5_step(g, table):
    p = np.pad(g, 1)
    n = p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]
    return table[2 * n + g]


def _total9_step(g, table):
    p = np.pad(g, 1)
    h, w = g.shape
    s = sum(p[dy:dy + h, dx:dx + w] for dy in range(3) for dx in range(3))
    return table[s]


def _start_patch(start, rng):
    """cell: one live cell. symmetric: a random 5 x 5 patch with the 4-fold
    mirror symmetry of a single cell. random: a random 4 x 4 patch."""
    if start == "cell":
        return np.ones((1, 1), dtype=np.uint8)
    if start == "symmetric":
        q = rng.integers(0, 2, (3, 3), dtype=np.uint8)
        top = np.hstack([q, q[:, -2::-1]])
        patch = np.vstack([top, top[-2::-1]])
    elif start == "random":
        patch = rng.integers(0, 2, (4, 4), dtype=np.uint8)
    else:
        raise ValueError(f"unknown start {start!r}: cell, symmetric, random")
    patch[patch.shape[0] // 2, patch.shape[1] // 2] = 1
    return patch


def _grow(step, w, h, seed, code, start, steps):
    table = np.array([(code >> i) & 1 for i in range(10)], dtype=np.uint8)
    patch = _start_patch(start, np.random.default_rng(seed))
    size = max(2 * (steps + max(patch.shape)) + 3, max(w, h) + 2)
    g = np.zeros((size, size), dtype=np.uint8)
    y, x = size // 2 - patch.shape[0] // 2, size // 2 - patch.shape[1] // 2
    g[y:y + patch.shape[0], x:x + patch.shape[1]] = patch
    for _ in range(steps):
        g = step(g, table)
    y0, x0 = size // 2 - h // 2, size // 2 - w // 2
    return g[y0:y0 + h, x0:x0 + w]


@generator("outer5")
def outer5(w, h, seed, code, start="cell", steps=144):
    """5-neighbour outer totalistic CA, codes 0-1023: the next state is bit
    (2 n + c) of `code`, n = live cells among the 4 side neighbours, c = the
    cell itself. Grows as a diamond."""
    return _grow(_outer5_step, w, h, seed, code, start, steps)


@generator("total9")
def total9(w, h, seed, code, start="cell", steps=144):
    """9-cell totalistic CA, codes 0-1023: the next state is bit s of
    `code`, s = live cells in the 3 x 3 block. Grows as a square."""
    return _grow(_total9_step, w, h, seed, code, start, steps)
