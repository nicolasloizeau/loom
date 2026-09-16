"""Flat image of a drawdown: one square per crossing, no rendering."""
import numpy as np

from .colors import hex_to_rgb


def flat(drawdown, warp, weft, scale=10, fringe=3, background="#1a1a1a"):
    """RGB uint8 image of a drawdown (1 = warp on top, 0 = weft on top).

    The warp colours repeat across the columns, the weft colours down the
    rows. Each crossing is scale x scale pixels. `fringe` crossings of
    loose thread stick out on each side (weft left and right, warp top and
    bottom); the corners are `background`.
    """
    d = np.asarray(drawdown)
    h, w = d.shape
    weft_rows = np.array([hex_to_rgb(weft[i % len(weft)]) for i in range(h)],
                         dtype=np.uint8)
    warp_cols = np.array([hex_to_rgb(warp[j % len(warp)]) for j in range(w)],
                         dtype=np.uint8)
    f = fringe
    img = np.empty((h + 2 * f, w + 2 * f, 3), dtype=np.uint8)
    img[:] = hex_to_rgb(background)
    img[f:f + h, f:f + w] = np.where(d[:, :, None] == 1, warp_cols[None],
                                     weft_rows[:, None])
    img[f:f + h, :f] = img[f:f + h, f + w:] = weft_rows[:, None]
    img[:f, f:f + w] = img[f + h:, f:f + w] = warp_cols[None]
    return img.repeat(scale, axis=0).repeat(scale, axis=1)
