"""Post-processing of rendered images: film grain and background.

Defaults are the chosen look: soft film grain on the cloth (none in pure
black), then the black background lifted to charcoal with its own grain.
"""
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


@dataclass
class Grain:
    amount: float = 0.07   # strength: std of the grain, image values 0..1
    size: float = 1.5      # grain size in pixels (0: single-pixel grain)
    colour: float = 0.0    # 0: monochrome grain, 1: independent per channel
    midtones: float = 1.0  # 0: even everywhere; 1: strongest in midtones,
                           # none in pure black


@dataclass
class Background:
    level: float = 26.0             # background grey, 0..255 (0: black)
    tint: tuple = (1.0, 1.0, 1.0)   # colour of the lift, e.g. warm
    grain: float = 0.025            # grain on the background and shadows
    grain_size: float = 1.5         # background grain size in pixels


def _noise(rng, shape, size):
    """Gaussian noise blurred to `size` pixels, with unit std."""
    n = rng.standard_normal(shape).astype(np.float32)
    if size > 0:
        n = gaussian_filter(n, (size / 2, size / 2) + (0,) * (len(shape) - 2))
        n /= n.std()
    return n


def add_grain(img, g, seed=None):
    """`img` (PIL RGB) with film grain `g`."""
    rng = np.random.default_rng(seed)
    x = np.asarray(img, dtype=np.float32) / 255
    h, w, _ = x.shape
    noise = _noise(rng, (h, w), g.size)[:, :, None]
    if g.colour > 0:
        noise = (1 - g.colour) * noise + g.colour * _noise(rng, (h, w, 3),
                                                           g.size)
    lum = x @ LUMA
    weight = (1 - g.midtones) + g.midtones * 4 * lum * (1 - lum)
    return _to_image(x + g.amount * noise * weight[:, :, None])


def add_background(img, b, seed=None):
    """Lift pure black to a dark grey and add grain to the dark areas.

    The lift fades out quickly with brightness ((1 - x)^3): the background
    becomes `level`, shadows lift a little, colours stay. The mapping is
    smooth, so anti-aliased edges blend in without a dark rim.
    """
    rng = np.random.default_rng(seed)
    x = np.asarray(img, dtype=np.float32) / 255
    x = x + b.level / 255 * np.array(b.tint, dtype=np.float32) * (1 - x) ** 3
    if b.grain > 0:
        dark = (1 - x @ LUMA) ** 4
        x = x + b.grain * (_noise(rng, x.shape[:2], b.grain_size)
                           * dark)[:, :, None]
    return _to_image(x)


def _to_image(x):
    return Image.fromarray((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8))
