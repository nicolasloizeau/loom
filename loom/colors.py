"""Colour helpers and the named palettes of palettes.json."""
import json
import os

PALETTES = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "palettes.json")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def palette(name, path=PALETTES):
    """{"warp": [...], "weft": [...]} of a named palette."""
    with open(path) as f:
        palettes = json.load(f)
    if name not in palettes:
        raise KeyError(f"unknown palette {name!r}; known: "
                       f"{', '.join(palettes)}")
    return palettes[name]
