"""Flat image of a run, without rendering: one square per crossing.

    python plain.py run.json [-o out.png]

Reads the same settings files as render.py and ignores the render and post
settings. Also accepts an image made by loom, to redo it from the settings
it carries. See README.md.
"""
import argparse
import os

from loom.pipeline import save_plain
from loom.settings import load


def default_output(source, ext):
    stem = os.path.splitext(source)[0]
    out = stem + ext
    return stem + "_again" + ext if os.path.abspath(out) == \
        os.path.abspath(source) else out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("settings", help="settings .json, or a loom image")
    parser.add_argument("-o", "--output", help="default: next to the input")
    args = parser.parse_args()

    s = load(args.settings)
    out = args.output or default_output(args.settings, ".png")
    save_plain(s, out)
    print(f"{out}  (seed {s['seed']})")
