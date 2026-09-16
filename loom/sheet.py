"""Contact sheets: thumbnails of several images with their names."""
import os

from PIL import Image, ImageDraw


def contact_sheet(paths, out, cols=5, tile=600, pad=16, label_h=28):
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tile + pad) + pad,
                              rows * (tile + pad + label_h) + pad), "#111111")
    draw = ImageDraw.Draw(sheet)
    for n, path in enumerate(paths):
        r, c = divmod(n, cols)
        x, y = pad + c * (tile + pad), pad + r * (tile + pad + label_h)
        im = Image.open(path).convert("RGB")
        im.thumbnail((tile, tile), Image.LANCZOS)
        sheet.paste(im, (x, y + label_h))
        draw.text((x, y + 8), os.path.splitext(os.path.basename(path))[0],
                  fill="#dddddd")
    sheet.save(out, quality=90)
