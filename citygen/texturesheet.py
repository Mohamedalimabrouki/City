"""The texture sheet: every generated texture tiled 2 x 2, tinted by its palette colors.

`python -m citygen texture-sheet` writes `output/checks/texture-sheet.png`. The sheet is the
visual check for prompt 18 (and later for any reworked surface): judge each image as a game
artist would for a low-poly city, not as a close-up photograph.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .mesh.textures import spec_for, texture, texture_names

TILE = 256          # pixels of one repeat on the sheet (each texture is shown 2 x 2)
PAD = 18
MARGIN = 24
TITLE = 64
LABEL = 34
SWATCH = 30

BACKGROUND = "#f1f0ec"
BORDER = "#c9c7c0"
TEXT = "#242423"
MUTED = "#6b6a66"


def _rgb(text: str) -> tuple[int, int, int]:
    text = text.lstrip("#")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def _tinted(image: Image.Image, color: str) -> Image.Image:
    """`image` multiplied by a palette color, the way glTF renders color x texture."""
    a = np.asarray(image, dtype=np.float64) / 255.0
    c = np.array(_rgb(color), dtype=np.float64) / 255.0
    rgb = np.clip(a * c[None, None, :], 0.0, 1.0)
    return Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8), "RGB")


def _tints(style: dict, name: str) -> list[str]:
    """Palette colors that name this texture; the style's sample tint before prompt 19."""
    palette = style.get("palette", {})
    used = [spec["color"] for spec in palette.values() if spec.get("texture") == name]
    if used:
        return used
    sample = style.get("textures", {}).get(name, {}).get("tint")
    if sample in palette:
        return [palette[sample]["color"]]
    return ["#ffffff"]


def _repeat(style: dict, name: str) -> str:
    """The repeat written by the palette entry that uses the texture, if any."""
    for spec in style.get("palette", {}).values():
        if spec.get("texture") == name and spec.get("texture_size"):
            w, h = spec["texture_size"]
            return f"{w:g} x {h:g} m"
    return "not mapped"


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                       # very old Pillow: one small bitmap font
        return ImageFont.load_default()


def texture_sheet(out, style: dict, seed: int, columns: int = 4) -> Path:
    """Write the sheet to `out` and return that path."""
    names = texture_names(style)
    if not names:
        raise ValueError("the style declares no textures")
    rows = (len(names) + columns - 1) // columns
    cell_w = 2 * TILE
    cell_h = cell_w + LABEL + SWATCH
    width = 2 * MARGIN + columns * cell_w + (columns - 1) * PAD
    height = TITLE + MARGIN + rows * cell_h + (rows - 1) * PAD + MARGIN
    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title, small, label = _font(26), _font(17), _font(19)
    draw.text((MARGIN, 12), "Generated textures", fill=TEXT, font=title)
    draw.text((MARGIN + 300, 20), "grey detail x palette color, tiled 2 x 2", fill=MUTED, font=small)
    draw.text((width - MARGIN - 150, 20), f"seed {seed}", fill=MUTED, font=small)

    for k, name in enumerate(names):
        cx = MARGIN + (k % columns) * (cell_w + PAD)
        cy = TITLE + MARGIN + (k // columns) * (cell_h + PAD)
        spec = spec_for(style, name)
        image = texture(name, seed, spec)
        tints = _tints(style, name)
        tile = image.resize((TILE, TILE), Image.LANCZOS)
        pick = _tinted(tile, tints[0])
        for i in range(2):
            for j in range(2):
                sheet.paste(pick, (cx + i * TILE, cy + j * TILE))
        draw.rectangle([cx, cy, cx + cell_w - 1, cy + cell_w - 1], outline=BORDER)
        draw.text((cx + 2, cy + cell_w + 6),
                  f"{name}   {spec['pixels']} px   {_repeat(style, name)}", fill=TEXT, font=label)
        used = f"{len(tints)} tint" + ("s" if len(tints) != 1 else "")
        draw.text((cx + cell_w - 86, cy + cell_w + 9), used, fill=MUTED, font=small)
        for i, color in enumerate(tints[:8]):
            swatch = _tinted(image.crop((8, 8, 64, 32)), color)
            sx = cx + i * 60
            sheet.paste(swatch, (sx, cy + cell_w + LABEL))
            draw.rectangle([sx, cy + cell_w + LABEL, sx + 55, cy + cell_w + LABEL + 23],
                           outline=BORDER)
        if len(tints) > 8:
            draw.text((cx + 8 * 60 + 4, cy + cell_w + LABEL + 4), f"+{len(tints) - 8}",
                      fill=MUTED, font=small)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, format="PNG")
    return out
