"""Settings files: read the JSON of a run, fill in the defaults, resolve.

A settings file only lists what differs from DEFAULTS (the look of the last
random run). Unknown keys are an error, except keys starting with "_", which
are ignored and can hold notes. See README.md for every key.
"""
import copy
import json
from dataclasses import asdict

import numpy as np
from PIL import Image

from .colors import palette
from .generators import drawdown as generate
from .post import Background, Grain
from .style import Style

# Black margin per side as a share of the image width, as in the 48-wide
# frame the look was tuned on.
MARGIN_SHARE = 2.5 / 58.2

# Through JSON, so that defaults have the same types (lists, not tuples) as
# settings read back from a file.
DEFAULTS = json.loads(json.dumps({
    "seed": None,
    "pattern": {"generator": "second_order", "params": {"rule": 90},
                "width": 48, "height": None},
    "colors": "original",
    "plain": {"scale": 10, "fringe": 3, "background": "#1a1a1a"},
    "render": {"size": 1350, "aspect": "1:1", "style": asdict(Style())},
    "post": {"grain": asdict(Grain()), "background": asdict(Background())},
}))

REPLACED = ("colors", "pattern.params")  # given as a whole, never merged


def _merge(base, over, path=""):
    out = copy.deepcopy(base)
    for key, value in over.items():
        if key.startswith("_"):
            continue
        where = path + key
        if key not in base:
            raise KeyError(f"unknown setting {where!r}")
        if where in REPLACED or not isinstance(base[key], dict):
            out[key] = copy.deepcopy(value)
        elif isinstance(value, dict):
            out[key] = _merge(base[key], value, where + ".")
        else:
            raise TypeError(f"setting {where!r} must be an object")
    return out


def resolve(*overrides):
    """Full settings: DEFAULTS updated by each override dict in turn, with
    the seed, colours, pattern height and margin filled in."""
    s = DEFAULTS
    for over in overrides:
        s = _merge(s, over)
        if "generator" in over.get("pattern", {}) and \
                "params" not in over["pattern"]:
            s["pattern"]["params"] = {}  # a new generator: no default params
    if s["seed"] is None:
        s["seed"] = int(np.random.SeedSequence().entropy % 2 ** 32)
    if isinstance(s["colors"], str):
        s["colors"] = palette(s["colors"])

    # Frame: the margin keeps the same share of the image at any width, and
    # the height fills the aspect ratio.
    style, pattern = s["render"]["style"], s["pattern"]
    aw, ah = (float(x) for x in s["render"]["aspect"].split(":"))
    pad = style["fringe"] + 2 * sum(amp for _, amp in style["distort"])
    ext_x = (pattern["width"] - 1 + 2 * pad) / (1 - 2 * MARGIN_SHARE)
    if style["margin"] is None:
        style["margin"] = MARGIN_SHARE * ext_x
    else:
        ext_x = pattern["width"] - 1 + 2 * (pad + style["margin"])
    if pattern["height"] is None:
        pattern["height"] = int(ext_x * ah / aw
                                - 2 * (pad + style["margin"])) + 1
    return s


def load(path):
    """Resolved settings from a JSON file, or from an image made by loom
    (which carries its settings)."""
    if path.lower().endswith((".jpg", ".jpeg", ".png")):
        info = Image.open(path).info
        text = info.get("comment") or info.get("settings")
        if not text:
            raise ValueError(f"{path} carries no loom settings")
        return resolve(json.loads(text))
    with open(path) as f:
        return resolve(json.load(f))


def drawdown(s):
    p = s["pattern"]
    return generate(p["generator"], p["width"], p["height"], s["seed"],
                    **p["params"])


def aspect(s):
    aw, ah = (float(x) for x in s["render"]["aspect"].split(":"))
    return aw / ah


def style(s):
    return Style(**s["render"]["style"])


def grain(s):
    return Grain(**s["post"]["grain"])


def background(s):
    return Background(**s["post"]["background"])
