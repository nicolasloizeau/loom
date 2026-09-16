"""From resolved settings to an image file, with the settings embedded in
it (JPEG comment / PNG text) so any image can be reproduced."""
import json
import os
import tempfile

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from . import settings as S
from .plain import flat
from .post import add_background, add_grain


def save_plain(s, path):
    """Flat image of the drawdown (no rendering) as PNG."""
    p = s["plain"]
    img = flat(S.drawdown(s), s["colors"]["warp"], s["colors"]["weft"],
               p["scale"], p["fringe"], p["background"])
    info = PngInfo()
    info.add_text("settings", json.dumps(s))
    Image.fromarray(img).save(path, pnginfo=info)


def save_rendered(s, path):
    """Blender render + film grain + background, as JPEG. Blender writes
    to a temporary file; only the finished JPEG is kept."""
    from . import blender  # needs Blender (bpy); the plain image does not
    seed = s["seed"]
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "render.png")
        blender.render(S.drawdown(s), s["colors"]["warp"], s["colors"]["weft"],
                       raw, S.style(s), s["render"]["size"], S.aspect(s), seed)
        img = Image.open(raw).convert("RGB")
    img = add_grain(img, S.grain(s), seed + 4)
    img = add_background(img, S.background(s), seed + 5)
    img.save(path, quality=92, comment=json.dumps(s).encode())
