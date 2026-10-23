"""Texture images for the 3D materials.

A palette entry may name a texture (`texture = "plaster"`) and the size in meters one repeat
covers (`texture_size = [3.0, 3.0]`). The .glb writer turns that into a base-color texture with
`KHR_texture_transform`, so the meter UVs of every mesh keep working unchanged.

Images are neutral detail around white: the palette color multiplies the texture (glTF
`baseColorFactor` x `baseColorTexture`), so one grey image serves every wall color. The real
surfaces (plaster, stone, roof tiles, paving, ground) come in prompt 18; this module ships the
provider and one test image until then.

Every image owns its random stream (`stream(seed, "texture", name)`), so adding one texture
never changes another.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image

from ..rng import stream

TEST_SIZE = 128   # pixels; prompt 18 uses 256 or 512 for the real surfaces


def texture(name: str, seed: int) -> Image.Image:
    """The image for texture `name`: same pixels for the same seed and name.

    Prompt 17: a neutral checker with fine grain, useful to see repeats and alignment.
    Prompt 18 replaces this body with the generated plaster, stone, tiles and ground.
    """
    rng = stream(seed, "texture", name)
    y, x = np.mgrid[0:TEST_SIZE, 0:TEST_SIZE]
    cell = TEST_SIZE // 4                      # four squares across: seamless, the checker closes
    checker = ((x // cell + y // cell) % 2).astype(np.float64)
    phase = rng.uniform(0.0, 2.0 * np.pi, 2)
    grain = np.sin(2.0 * np.pi * (3.0 * x + 2.0 * y) / TEST_SIZE + phase[0]) * \
        np.sin(2.0 * np.pi * (2.0 * x - 3.0 * y) / TEST_SIZE + phase[1])
    value = np.clip(228.0 + 22.0 * checker + 5.0 * grain, 0.0, 255.0).astype(np.uint8)
    return Image.fromarray(np.repeat(value[:, :, None], 3, axis=2), "RGB")


def png_bytes(image: Image.Image) -> bytes:
    """PNG file content, exactly the same bytes for the same pixels."""
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def image_names(style: dict) -> list[str]:
    """Every texture name the palette asks for, sorted."""
    return sorted({spec["texture"] for spec in style.get("palette", {}).values() if spec.get("texture")})


def write_shared_textures(style: dict, seed: int, folder) -> list[str]:
    """Write each image once into `folder/textures/` before any tile; returns the file names.

    Tiles reference them with a relative URI, so parallel workers never write the same image.
    """
    from pathlib import Path

    out = Path(folder) / "textures"
    names = image_names(style)
    if names:
        out.mkdir(parents=True, exist_ok=True)
    for name in names:
        (out / f"{name}.png").write_bytes(png_bytes(texture(name, seed)))
    return [f"{name}.png" for name in names]


def images_for(style: dict, seed: int, mode: str) -> dict:
    """The writer's image table: {texture name: {"uri": path} or {"bytes": png}}.

    "shared": one file per image under the tiles folder, written by the parent process.
    "embedded": the PNG bytes go inside every .glb (single-file exports such as hero scenes).
    "off": no texture at all, flat palette colors.
    """
    names = image_names(style)
    if mode == "shared":
        return {name: {"uri": f"textures/{name}.png"} for name in names}
    if mode == "embedded":
        return {name: {"bytes": png_bytes(texture(name, seed))} for name in names}
    return {}
