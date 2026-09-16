"""1D cellular automata: each row of the drawdown is the next time step.

The automaton starts from random rows (drawn from `seed`) on a line wide
enough that the influence of its two ends never reaches the w columns that
are kept, and its first `burn_in` steps (the transient) are dropped.
"""
import numpy as np

from . import generator


def _run(step, radius, n_rows, w, h, seed, burn_in):
    """Run `step` (taking the last n_rows rows, oldest first) and keep an
    h x w window. Edge effects spread `radius` cells per step, so the line
    is padded by that much per step and only its middle is kept."""
    rng = np.random.default_rng(seed)
    steps = burn_in + h
    pad = radius * steps
    rows = [rng.integers(0, 2, w + 2 * pad, dtype=np.uint8)
            for _ in range(n_rows)]
    kept = []
    for t in range(steps):
        if t >= burn_in:
            kept.append(rows[-1][pad:pad + w])
        rows = rows[1:] + [step(*rows)]
    return np.array(kept)


def _elementary_step(row, rule):
    table = np.array([(rule >> i) & 1 for i in range(8)], dtype=np.uint8)
    p = np.pad(row, 1)
    return table[(p[:-2] << 2) | (p[1:-1] << 1) | p[2:]]


@generator("elementary")
def elementary(w, h, seed, rule, burn_in=50):
    """Elementary CA, Wolfram rules 0-255: a cell's next state depends on
    itself and its two neighbours."""
    return _run(lambda row: _elementary_step(row, rule), 1, 1, w, h, seed,
                burn_in)


@generator("totalistic")
def totalistic(w, h, seed, rule, burn_in=50):
    """Radius-2 totalistic CA, rules 0-63 (the "T" rules): the next state is
    bit k of `rule`, k = number of live cells among the 5 around."""
    def step(row):
        p = np.pad(row, 2)
        ones = p[:-4] + p[1:-3] + p[2:-2] + p[3:-1] + p[4:]
        return ((rule >> ones) & 1).astype(np.uint8)
    return _run(step, 2, 1, w, h, seed, burn_in)


@generator("second_order")
def second_order(w, h, seed, rule, burn_in=50):
    """Second-order (reversible) CA, rules 0-255 (the "R" rules): elementary
    `rule` on the current row, XOR the previous row. Never dies out."""
    return _run(lambda prev, row: _elementary_step(row, rule) ^ prev, 1, 2,
                w, h, seed, burn_in)
