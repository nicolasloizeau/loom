"""Many runs at once: random combinations of the favourite patterns
(favourites.json), widths and palettes (palettes.json), each with a new
seed; the palette's warp and weft colours are swapped half of the time.

    python batch.py [--n 100] [--out out/batch] [--base base.json]
                    [--widths 24 36 48] [--palettes palette_2 palette_3]
                    [--plain]

--base gives settings shared by every run (e.g. render tweaks). With
--plain, flat images are made instead of renders (fast previews).
Combinations already in the output folder's runs.jsonl are not drawn again,
images are numbered after the existing ones, and there is a contact sheet
for every 20 images. runs.jsonl keeps each image's full settings.
"""
import argparse
import json
import os
import re
import time

import numpy as np

from loom.colors import PALETTES
from loom.pipeline import save_plain, save_rendered
from loom.settings import resolve
from loom.sheet import contact_sheet

HERE = os.path.dirname(os.path.abspath(__file__))
PER_SHEET = 20


def combo_key(favourite, width, palette):
    return json.dumps([favourite, width, palette], sort_keys=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--out", default="out/batch")
    parser.add_argument("--base", help="settings .json shared by all runs")
    parser.add_argument("--widths", type=int, nargs="+", default=[24, 36, 48])
    parser.add_argument("--palettes", nargs="+",
                        help="palette names (default: all but 'original')")
    parser.add_argument("--plain", action="store_true",
                        help="flat images instead of renders")
    args = parser.parse_args()

    with open(os.path.join(HERE, "favourites.json")) as f:
        favourites = json.load(f)
    with open(PALETTES) as f:
        palettes = json.load(f)
    names = args.palettes or [p for p in palettes if p != "original"]
    base = {}
    if args.base:
        with open(args.base) as f:
            base = json.load(f)

    os.makedirs(args.out, exist_ok=True)
    log = os.path.join(args.out, "runs.jsonl")
    done, numbers = set(), [0]
    if os.path.exists(log):
        with open(log) as f:
            for line in f:
                run = json.loads(line)
                done.add(combo_key(*run["combo"]))
                numbers.append(int(run["image"][:3]))
    combos = [(fav, w, p) for fav in favourites for w in args.widths
              for p in names if combo_key(fav, w, p) not in done]
    rng = np.random.default_rng()
    picks = rng.choice(len(combos), size=min(args.n, len(combos)),
                       replace=False)
    ext = ".png" if args.plain else ".jpg"

    for k, c in enumerate(picks):
        fav, width, pal = combos[c]
        colors = dict(palettes[pal])
        swapped = bool(rng.random() < 0.5)
        if swapped:
            colors = {"warp": colors["weft"], "weft": colors["warp"]}
        s = resolve(base, {"seed": None, "colors": colors,
                           "pattern": {**fav, "width": width,
                                       "height": None}})
        tag = "_".join(str(v) for v in fav.get("params", {}).values())
        name = (f"{max(numbers) + 1 + k:03d}_{fav['generator']}_{tag}"
                f"_w{width}_{pal}{'_swap' if swapped else ''}{ext}")
        t0 = time.time()
        (save_plain if args.plain else save_rendered)(
            s, os.path.join(args.out, name))
        with open(log, "a") as f:
            f.write(json.dumps({"image": name,
                                "combo": [fav, width, pal],
                                "swapped": swapped, "settings": s}) + "\n")
        print(f"{name}: {time.time() - t0:.0f}s", flush=True)

    images = sorted(f for f in os.listdir(args.out)
                    if re.match(r"\d{3}_.*\.(jpg|png)$", f))
    for k in range(0, len(images), PER_SHEET):
        contact_sheet([os.path.join(args.out, f)
                       for f in images[k:k + PER_SHEET]],
                      os.path.join(args.out,
                                   f"sheet_{k // PER_SHEET + 1:02d}.jpg"))
