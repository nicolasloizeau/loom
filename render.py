"""Rendered image of a run: woven threads rendered with Blender, then film
grain and background, saved as JPEG.

    python render.py run.json [-o out.jpg]

Also accepts an image made by loom, to redo it from the settings it carries
(same seed: the same image). See README.md.
"""
import argparse
import time

from loom.pipeline import save_rendered
from loom.settings import load
from plain import default_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("settings", help="settings .json, or a loom image")
    parser.add_argument("-o", "--output", help="default: next to the input")
    args = parser.parse_args()

    s = load(args.settings)
    out = args.output or default_output(args.settings, ".jpg")
    t0 = time.time()
    save_rendered(s, out)
    print(f"{out}  (seed {s['seed']}, {time.time() - t0:.0f}s)")
