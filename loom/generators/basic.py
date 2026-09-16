"""Regular weaves (they ignore the seed)."""
import numpy as np

from . import generator


@generator("plain_weave")
def plain_weave(w, h, seed):
    """The simplest weave: warp and weft alternate at every crossing."""
    y, x = np.indices((h, w))
    return (x + y) % 2


@generator("twill")
def twill(w, h, seed, over=2, under=2):
    """Diagonal ribs: along each row the weft is on top for `over` crossings,
    then the warp for `under`, and each row is shifted by one."""
    y, x = np.indices((h, w))
    return ((x + y) % (over + under) >= over).astype(np.uint8)
