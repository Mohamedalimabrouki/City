"""Golden hour beauty render of the generated city in Blender 3.6+ (Cycles, CPU).

    blender -b --python tools/blender_beauty.py -- OUT_DIR --view aerial|street|souk --png FILE
            [--samples N] [--size 1600x900]

Imports every tile of OUT_DIR (the generator folder), swaps the palette materials for procedural
shaders (facades are driven by the wall UVs, which are meters: u along the wall, v = 1 + height above
the building's highest ground point), adds water tanks, and lights the scene with a Nishita sky, a
matching sun and a thin haze. Parapets and the sea are Blender-only dressing: the generator's tiles
carry their own parapets (the index says "parapets": true) and this script only adds them for older
builds; tiles built without street dressing get painted windows, doors and shutters here instead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_import import expand_instances  # noqa: E402

FOV = 50.0                              # vertical field of view in degrees, as the web viewer
AERIAL = (160.0, 900.0, 650.0)          # viewer preset: bearing, distance, height above the focus
SUN_AZIMUTH, SUN_ELEVATION = 225.0, 14.0
SUN_COLOR, SUN_STRENGTH = (1.0, 0.66, 0.38), 3.5
SKY_STRENGTH, EXPOSURE = 0.6, -1.0
HAZE_DENSITY, HAZE_MAX, HAZE_COLOR = 1.0e-4, 0.7, (0.42, 0.52, 0.66, 1.0)   # 1/m, share, linear color
GRADE_GAIN, GRADE_LIFT = (1.06, 1.0, 0.92), (0.98, 1.0, 1.03)
SEA_LEVEL, SEA_BOTTOM = 0.03, -16.7     # sea plane just above the generator water (no coplanar fight); seabed reaches -16.6
PARAPET_THICK, PARAPET_HEIGHT, TANK_SHARE = 0.25, 0.8, 0.25
SKIRT = 0.7                             # how far the generator buries wall feet below the ground

STYLE_OF = {"lime_white": "old", "warm_white": "old", "sand": "old", "ochre": "old",
            "cream": "colonial", "pale_yellow": "colonial",
            "concrete": "modern", "concrete_dark": "modern", "pastel_blue": "modern", "metal": "metal"}
STYLES = {   # floor height, bay width, window width/height/sill, frame, window odds above/ground, door odds
    "old": dict(floor=3.2, bay=3.4, ww=0.7, wh=1.0, sill=1.05, frame=0.07, up=0.55, ground=0.15, door=0.42),
    "colonial": dict(floor=3.6, bay=3.2, ww=1.1, wh=2.2, sill=0.45, frame=0.08, up=0.93, ground=0.72, door=0.0),
    "modern": dict(floor=3.0, bay=3.0, ww=1.9, wh=1.5, sill=0.9, frame=0.06, up=0.92, ground=0.55, door=0.0),
}
COPY_SUFFIX = re.compile(r"\.\d{3,}$")
DRESSED = False                         # set in main: the tiles carry the generator's street dressing
PARAPETS = False                        # set in main: the tiles carry their own roof parapets


def lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcolor(code: str) -> tuple[float, float, float, float]:
    return (*(lin(int(code[i:i + 2], 16) / 255.0) for i in (1, 3, 5)), 1.0)


BLUE = hexcolor("#1F5FA8")              # old town doors and window frames
SHUTTER_BLUE, DOOR_DARK = hexcolor("#3F7FC0"), hexcolor("#143F70")
SURROUND, GLASS = hexcolor("#E9E2D0"), hexcolor("#101A24")
GREEN, CREAM = hexcolor("#24402C"), hexcolor("#EDE4CF")
SIGNS = [hexcolor(c) for c in ("#7A1E1A", "#1F4A30", "#1B2F58", "#C9BC98")]


def rng(seed: int, *purpose: object) -> np.random.Generator:
    digest = hashlib.sha256("/".join(map(str, (seed, "beauty") + purpose)).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


# --- shader node helpers -------------------------------------------------------------

class Val:
    """A node output socket; Python arithmetic on it adds Math nodes to the graph."""

    def __init__(self, g: "Graph", sock) -> None:
        self.g, self.sock = g, sock

    def _bin(self, op: str, other, swap: bool = False) -> "Val":
        a, b = (other, self) if swap else (self, other)
        return self.g.math(op, a, b)

    def __add__(self, o): return self._bin("ADD", o)
    def __radd__(self, o): return self._bin("ADD", o, True)
    def __sub__(self, o): return self._bin("SUBTRACT", o)
    def __rsub__(self, o): return self._bin("SUBTRACT", o, True)
    def __mul__(self, o): return self._bin("MULTIPLY", o)
    def __rmul__(self, o): return self._bin("MULTIPLY", o, True)
    def __truediv__(self, o): return self._bin("DIVIDE", o)
    def __rtruediv__(self, o): return self._bin("DIVIDE", o, True)
    def __lt__(self, o): return self._bin("LESS_THAN", o)
    def __gt__(self, o): return self._bin("GREATER_THAN", o)
    def __and__(self, o): return self._bin("MULTIPLY", o)
    def __or__(self, o): return self._bin("MAXIMUM", o)
    def __invert__(self): return self._bin("SUBTRACT", 1.0, True)
    def __neg__(self): return self._bin("MULTIPLY", -1.0)
    def __abs__(self): return self.g.math("ABSOLUTE", self)


class Graph:
    """Builds one material's node tree. Masks are 0/1 floats, so `a & b` multiplies and `a | b` takes the max."""

    def __init__(self, mat: bpy.types.Material) -> None:
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self._geo = self._coord = self._cam = None

    def add(self, kind: str, **props):
        node = self.nt.nodes.new(kind)
        for key, value in props.items():
            setattr(node, key, value)
        return node

    def feed(self, sock, value) -> None:
        if isinstance(value, Val):
            value = value.sock
        if isinstance(value, bpy.types.NodeSocket):
            self.nt.links.new(value, sock)
        elif value is not None:
            sock.default_value = value

    def math(self, op: str, a, b=None, c=None) -> Val:
        node = self.add("ShaderNodeMath", operation=op)
        for sock, value in zip(node.inputs, (a, b, c)):
            self.feed(sock, value)
        return Val(self, node.outputs[0])

    def vmax(self, a, b) -> Val: return self.math("MAXIMUM", a, b)
    def vmin(self, a, b) -> Val: return self.math("MINIMUM", a, b)
    def floor(self, a) -> Val: return self.math("FLOOR", a)
    def fract(self, a) -> Val: return self.math("FRACT", a)

    @property
    def pos(self) -> Val:
        if self._geo is None:
            self._geo = self.add("ShaderNodeNewGeometry")
        return Val(self, self._geo.outputs["Position"])

    def geo(self, name: str) -> Val:
        self.pos
        return Val(self, self._geo.outputs[name])

    def obj(self) -> Val:
        if self._coord is None:
            self._coord = self.add("ShaderNodeTexCoord")
        return Val(self, self._coord.outputs["Object"])

    def distance(self) -> Val:
        if self._cam is None:
            self._cam = self.add("ShaderNodeCameraData")
        return Val(self, self._cam.outputs["View Distance"])

    def uv(self, name: str) -> Val:
        return Val(self, self.add("ShaderNodeUVMap", uv_map=name).outputs[0])

    def xyz(self, vec) -> tuple[Val, Val, Val]:
        node = self.add("ShaderNodeSeparateXYZ")
        self.feed(node.inputs[0], vec)
        return tuple(Val(self, o) for o in node.outputs)

    def vec(self, x, y, z) -> Val:
        node = self.add("ShaderNodeCombineXYZ")
        for sock, value in zip(node.inputs, (x, y, z)):
            self.feed(sock, value)
        return Val(self, node.outputs[0])

    def vmul(self, vec, scale: tuple[float, float, float]) -> Val:
        node = self.add("ShaderNodeVectorMath", operation="MULTIPLY")
        self.feed(node.inputs[0], vec)
        node.inputs[1].default_value = scale
        return Val(self, node.outputs[0])

    def noise(self, vec, scale: float, detail: float = 2.0, rough: float = 0.5) -> Val:
        node = self.add("ShaderNodeTexNoise", noise_dimensions="3D")
        self.feed(node.inputs["Vector"], vec)
        node.inputs["Scale"].default_value = scale
        node.inputs["Detail"].default_value = detail
        node.inputs["Roughness"].default_value = rough
        return Val(self, node.outputs["Fac"])

    def noises(self) -> tuple[Val, Val, Val]:
        """Blotches (meters), mid grain (decimeters) and fine grain; the first two use world space, no tile seams."""
        return self.noise(self.pos, 0.3, 3, 0.55), self.noise(self.pos, 3.0, 4, 0.6), self.noise(self.obj(), 45.0, 2, 0.5)

    def rand(self, a, b, c) -> Val:
        node = self.add("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        self.feed(node.inputs[0], self.vec(a, b, c))
        return Val(self, node.outputs["Value"])

    def smooth(self, x, lo, hi) -> Val:
        node = self.add("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True)
        for sock, value in zip(node.inputs, (x, lo, hi)):
            self.feed(sock, value)
        return Val(self, node.outputs[0])

    def lerp(self, t, a, b) -> Val:
        node = self.add("ShaderNodeMix", data_type="FLOAT")
        self.feed(node.inputs[0], t)
        self.feed(node.inputs[2], a)
        self.feed(node.inputs[3], b)
        return Val(self, node.outputs[0])

    def mixc(self, fac, a, b, blend: str = "MIX") -> Val:
        node = self.add("ShaderNodeMixRGB", blend_type=blend)
        for sock, value in zip(node.inputs, (fac, a, b)):
            self.feed(sock, value)
        return Val(self, node.outputs[0])

    def pick(self, r, colors: list) -> Val:
        """One of `colors` chosen by the random value r in 0..1."""
        out = colors[0]
        for k, color in enumerate(colors[1:], 1):
            out = self.mixc(r > k / len(colors), out, color)
        return out if isinstance(out, Val) else self.mixc(0.0, out, out)


class Surface:
    """Running color, roughness, specular and bump height of one material."""

    def __init__(self, g: Graph, color, rough=0.9, spec=0.3, height=0.0) -> None:
        self.g, self.color, self.rough, self.spec, self.height = g, color, rough, spec, height

    def paint(self, mask, color=None, rough=None, spec=None, height=None) -> None:
        g = self.g
        if color is not None:
            self.color = g.mixc(mask, self.color, color)
        if rough is not None:
            self.rough = g.lerp(mask, self.rough, rough)
        if spec is not None:
            self.spec = g.lerp(mask, self.spec, spec)
        if height is not None:
            self.height = self.height + mask * height

    def finish(self, strength: float = 0.5, metal: float = 0.0, shader=None) -> None:
        g = self.g
        bsdf = g.add("ShaderNodeBsdfPrincipled")
        g.feed(bsdf.inputs["Base Color"], self.color)
        g.feed(bsdf.inputs["Roughness"], self.rough)
        g.feed(spec_input(bsdf), self.spec)
        bsdf.inputs["Metallic"].default_value = metal
        if isinstance(self.height, Val):
            bump = g.add("ShaderNodeBump")
            bump.inputs["Strength"].default_value = strength
            g.feed(bump.inputs["Height"], self.height)
            g.nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        out = g.add("ShaderNodeOutputMaterial")
        g.nt.links.new(bsdf.outputs[0], out.inputs[0])


def spec_input(bsdf):
    """Blender 4 renamed the Principled BSDF "Specular" input to "Specular IOR Level"."""
    return bsdf.inputs["Specular"] if "Specular" in bsdf.inputs else bsdf.inputs["Specular IOR Level"]


def arch(g: Graph, dx, hd, half: float, top: float) -> Val:
    """Mask of a door shape: a rectangle with a round top, `dx` across and `hd` up from the ground."""
    rect = (abs(dx) < half) & (hd < top - half)
    dy = hd - (top - half)
    return rect | ((dx * dx + dy * dy) < half * half)


# --- wall shaders --------------------------------------------------------------------

def wall_context(g: Graph, st: dict) -> SimpleNamespace:
    """Bay and floor coordinates of a wall point plus per-cell random numbers (needs the wallA/wallB UV maps)."""
    u, v = g.xyz(g.uv("UVMap"))[:2]
    u0, length = g.xyz(g.uv("wallA"))[:2]
    hb, ht = g.xyz(g.uv("wallB"))[:2]
    x, h = u - u0, v - 1.0                                  # h: meters above the building's highest ground point
    floors = g.vmax(g.math("ROUND", ht / st["floor"]), 1.0)
    fh = ht / floors
    bays = g.vmax(g.math("ROUND", length / st["bay"]), 1.0)
    bw = length / bays
    cell = g.vmin(g.floor(x / bw), bays - 1.0)
    fl = g.vmin(g.floor(h / fh), floors - 1.0)
    seed = u0 * 0.137 + ht * 0.71 + length * 0.29
    return SimpleNamespace(
        x=x, h=h, hb=hb, ht=ht, length=length, bw=bw, fh=fh, fl=fl, floors=floors, wall=length > 0.5,
        cx=x - (cell + 0.5) * bw, fy=h - fl * fh, hd=h - hb - SKIRT * (hb < 1.5), above=fl > -0.5, ground=fl < 0.5,
        ra=g.rand(cell, fl, seed), rb=g.rand(cell + 17.3, fl + 3.1, seed),
        rc=g.rand(cell + 41.7, fl, seed + 9.7), rd=g.rand(cell, fl + 23.9, seed + 5.3),
        tint=g.rand(u0 * 0.31, ht, length * 0.7))


def box(c: SimpleNamespace, w: float, y0: float, hh: float, dx=None) -> Val:
    """Rectangle w wide and hh high in bay coordinates, its sill y0 above the floor, around the bay centre."""
    across = c.cx if dx is None else c.cx - dx
    return (abs(across) < w / 2) & (c.fy > y0) & (c.fy < y0 + hh)


def old_openings(g: Graph, s: Surface, c: SimpleNamespace, st: dict) -> None:
    """Old town: few small windows with blue frames and shutters, blue arched doors on the ground floor."""
    f = st["frame"]
    door_cell = (c.length > 2.6) & (c.rc < st["door"])
    dx = c.cx - (c.rd - 0.5) * 0.9
    door = arch(g, dx, c.hd, 0.58, 2.35) & door_cell
    around = arch(g, dx, c.hd, 0.68, 2.45) & door_cell & ~door
    present = (c.ra < g.lerp(c.ground, st["up"], st["ground"])) & c.above & ~(door_cell & c.ground)
    inner = box(c, st["ww"], st["sill"], st["wh"]) & present
    framed = box(c, st["ww"] + 2 * f, st["sill"] - f, st["wh"] + 2 * f) & present & ~inner
    closed = c.rb < 0.3
    s.paint(framed, BLUE, rough=0.5, height=0.01)
    s.paint(inner & closed, SHUTTER_BLUE, rough=0.6, height=-0.02)
    s.paint(inner & ~closed, GLASS, rough=0.04, spec=0.8, height=-0.05)
    s.paint(around, SURROUND, rough=0.85, height=0.015)
    s.paint(door, BLUE, rough=0.45, height=-0.03)
    planks = (abs(g.fract(dx / 0.13) - 0.5) > 0.45) & door
    s.paint(planks, DOOR_DARK, rough=0.5)


def colonial_openings(g: Graph, s: Surface, c: SimpleNamespace, st: dict) -> None:
    """Colonial: tall windows with green shutters on every floor, shop fronts and signs on the ground floor."""
    f, ww, sill, wh = st["frame"], st["ww"], st["sill"], st["wh"]
    upper = c.above & ~c.ground
    present = (c.ra < st["up"]) & upper
    inner = box(c, ww, sill, wh) & present
    framed = box(c, ww + 2 * f, sill - f, wh + 2 * f) & present & ~inner
    shuttered = c.rc < 0.82
    closed = (c.rb < 0.22) & shuttered
    zone = (abs(c.cx) > ww / 2) & (abs(c.cx) < ww / 2 + 0.5) & (c.fy > sill) & (c.fy < sill + wh)
    s.paint(framed, CREAM, rough=0.6, height=0.01)
    s.paint(inner & ~closed, GLASS, rough=0.04, spec=0.8, height=-0.05)
    s.paint((zone & present & shuttered) | (inner & closed), GREEN, rough=0.55, height=0.015)
    shop = c.ground & c.above & (c.ra < st["ground"])
    sw = c.bw - 1.0
    front = shop & (abs(c.cx) < sw / 2) & (c.fy > 0.35) & (c.fy < 2.65)
    rim = shop & (abs(c.cx) < sw / 2 + 0.08) & (c.fy > 0.27) & (c.fy < 2.73) & ~front
    sign = shop & (abs(c.cx) < sw / 2 + 0.08) & (c.fy > 2.78) & (c.fy < 3.3)
    rolled = front & (c.rb < 0.3)
    s.paint(rim, CREAM, rough=0.6, height=0.012)
    s.paint(front, GLASS, rough=0.05, spec=0.8, height=-0.06)
    s.paint(rolled, hexcolor("#6F6C66"), rough=0.5)
    s.paint(sign, g.pick(c.rd, SIGNS), rough=0.5, height=0.02)
    band = (c.fy < 0.14) & upper | (c.ht - c.h < 0.35)
    s.paint(band, CREAM, rough=0.85, height=0.02)


def modern_openings(g: Graph, s: Surface, c: SimpleNamespace, st: dict) -> None:
    """Modern: a regular window grid with dark frames, some blinds, panel joints, taller ground floor glazing."""
    f = st["frame"]
    present = (c.ra < g.lerp(c.ground, st["up"], st["ground"])) & c.above
    tall = c.ground & (c.rb < 0.5)
    y0, hh = g.lerp(tall, st["sill"], 0.2), g.lerp(tall, st["wh"], 2.3)
    inner = (abs(c.cx) < st["ww"] / 2) & (c.fy > y0) & (c.fy < y0 + hh) & present
    framed = (abs(c.cx) < st["ww"] / 2 + f) & (c.fy > y0 - f) & (c.fy < y0 + hh + f) & present & ~inner
    blind = c.rc < 0.18
    joints = ((abs(c.cx) > c.bw / 2 - 0.012) | (c.fy < 0.012)) & c.above
    s.paint(joints, (0.1, 0.1, 0.1, 1.0), rough=0.9, height=-0.01)
    s.paint(framed, hexcolor("#2C3036"), rough=0.4, height=0.01)
    s.paint(inner & blind, hexcolor("#B8B3A6"), rough=0.8, height=-0.03)
    s.paint(inner & ~blind, g.mixc(c.rd, hexcolor("#142230"), hexcolor("#2A3C4C")), rough=0.03, spec=0.9, height=-0.05)


def shade_facade(mat: bpy.types.Material, kind: str, base: tuple) -> None:
    g = Graph(mat)
    st = STYLES[kind]
    big, mid, fine = g.noises()
    c = wall_context(g, st)
    var = (1.0 + 0.55 * (big - 0.5) + 0.35 * (mid - 0.5) + 0.25 * (fine - 0.5)) * (0.94 + 0.12 * c.tint)
    s = Surface(g, g.mixc(1.0, base, var, "MULTIPLY"), rough=0.92, spec=0.25, height=fine * 0.004)
    hl = c.h - c.hb                                           # meters above the wall's own bottom
    grime = g.smooth(hl, 1.5 + 1.2 * (mid - 0.5), 0.0) * (0.35 + 0.8 * big)
    streaks = g.smooth(g.noise(g.vmul(g.pos, (1.4, 1.4, 0.09)), 1.0, 2, 0.5), 0.5, 0.85)
    s.color = g.mixc(grime * 0.7, s.color, (0.42, 0.38, 0.33, 1.0), "MULTIPLY")
    s.color = g.mixc(streaks * 0.3 * g.smooth(hl, 0.8, 4.0), s.color, (0.6, 0.55, 0.5, 1.0), "MULTIPLY")
    plain = (s.color, s.rough, s.spec, s.height)
    {"old": old_openings, "colonial": colonial_openings, "modern": modern_openings}[kind](g, s, c, st)
    flat = ~c.wall                                            # roofs and floors sharing the material stay plain
    s.color = g.mixc(flat, s.color, plain[0])
    s.rough, s.spec, s.height = g.lerp(flat, s.rough, plain[1]), g.lerp(flat, s.spec, plain[2]), g.lerp(flat, s.height, plain[3])
    s.finish(0.7)


def shade_metal(mat: bpy.types.Material, base: tuple) -> None:
    """Corrugated sheet: ribs along the wall, or along x on roofs; no windows."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    u0, length = g.xyz(g.uv("wallA"))[:2]
    u = g.xyz(g.uv("UVMap"))[0]
    px, py = g.xyz(g.pos)[:2]
    wall = length > 0.5
    along = g.lerp(wall, px * 0.9 + py * 0.4, u)
    rib = abs(g.fract(along / 0.22) - 0.5) * 2.0
    rust = g.smooth(g.noise(g.vmul(g.pos, (2.0, 2.0, 0.12)), 1.0, 3, 0.6), 0.55, 0.9)
    color = g.mixc(1.0, base, 0.82 + 0.15 * rib + 0.2 * (big - 0.5), "MULTIPLY")
    color = g.mixc(rust * 0.5, color, hexcolor("#6B3E26"))
    s = Surface(g, color, rough=0.45, spec=0.5, height=rib * 0.05 + fine * 0.003)
    s.finish(0.8, metal=0.35)


# --- other materials -----------------------------------------------------------------

def shade_plaster(mat: bpy.types.Material, base: tuple, stains: float = 1.0, rough: float = 0.88) -> None:
    """Off-white plaster with water stains and dirt: roofs, parapets, domes."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    zone = g.noise(g.pos, 0.05, 1, 0.5)
    var = 0.92 + 0.14 * (mid - 0.5) + 0.2 * (zone - 0.5)
    color = g.mixc(1.0, base, var, "MULTIPLY")
    stain = g.smooth(big, 0.5, 0.78) * stains
    color = g.mixc(stain * 0.35, color, (0.55, 0.5, 0.42, 1.0), "MULTIPLY")
    speck = g.smooth(fine, 0.62, 0.8) * 0.25
    color = g.mixc(speck, color, (0.5, 0.47, 0.42, 1.0), "MULTIPLY")
    Surface(g, color, rough=rough, spec=0.25, height=fine * 0.004 + stain * 0.002).finish(0.5)


def shade_asphalt(mat: bpy.types.Material, base: tuple) -> None:
    g = Graph(mat)
    big, mid, fine = g.noises()
    grain = g.noise(g.obj(), 160.0, 1, 0.5)
    var = 0.8 + 0.22 * (big - 0.5) + 0.2 * (mid - 0.5) + 0.5 * (grain - 0.5)
    color = g.mixc(1.0, base, var, "MULTIPLY")
    Surface(g, color, rough=g.lerp(g.smooth(mid, 0.55, 0.8), 0.9, 0.6), spec=0.3, height=grain * 0.004).finish(0.6)


def shade_paving(mat: bpy.types.Material, base: tuple) -> None:
    """Worn stone slabs in running bond along the lane (UV meters: u across, v along)."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    brick = g.add("ShaderNodeTexBrick", offset=0.5, offset_frequency=2, squash=1.0, squash_frequency=2)
    g.feed(brick.inputs["Vector"], g.uv("UVMap"))
    for name, value in (("Color1", tuple(x * 1.1 for x in base[:3]) + (1.0,)), ("Color2", tuple(x * 0.85 for x in base[:3]) + (1.0,)),
                        ("Mortar", tuple(x * 0.55 for x in base[:3]) + (1.0,))):
        brick.inputs[name].default_value = value
    for name, value in (("Scale", 1.0), ("Mortar Size", 0.02), ("Mortar Smooth", 0.3), ("Bias", 0.0),
                        ("Brick Width", 0.8), ("Row Height", 0.4)):
        brick.inputs[name].default_value = value
    color = g.mixc(1.0, Val(g, brick.outputs["Color"]), 0.86 + 0.25 * (big - 0.5) + 0.3 * (mid - 0.5), "MULTIPLY")
    s = Surface(g, color, rough=g.lerp(g.smooth(mid, 0.5, 0.8), 0.9, 0.55), spec=0.3,
                height=Val(g, brick.outputs["Fac"]) * 0.02 + fine * 0.004)
    s.finish(0.8)


def shade_dust(mat: bpy.types.Material, base: tuple, tone: float = 1.0) -> None:
    """Dusty ground: urban_ground, grass, steppe."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    var = tone * (0.86 + 0.3 * (big - 0.5) + 0.25 * (mid - 0.5) + 0.2 * (fine - 0.5))
    color = g.mixc(g.smooth(mid, 0.55, 0.75) * 0.4, g.mixc(1.0, base, var, "MULTIPLY"), (0.78, 0.7, 0.55, 1.0), "MULTIPLY")
    Surface(g, color, rough=0.96, spec=0.15, height=fine * 0.01).finish(0.5)


def shade_beach(mat: bpy.types.Material, base: tuple) -> None:
    """Sand with ripples; below sea level it fades to turquoise and deep blue, and a foam line follows z = 0."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    z = g.xyz(g.pos)[2]
    ripple = g.noise(g.vmul(g.pos, (0.6, 3.5, 1.0)), 1.0, 2, 0.5)
    sand = g.mixc(1.0, base, 0.9 + 0.25 * (mid - 0.5) + 0.2 * (fine - 0.5), "MULTIPLY")
    depth = g.vmax(-z, 0.0)
    tint = 1.0 - g.math("POWER", 2.718, depth * -0.55)
    water = g.mixc(g.smooth(depth, 1.0, 7.0), hexcolor("#2FB0A8"), hexcolor("#14607F"))
    wet = g.smooth(z, 0.5, 0.05)
    color = g.mixc(wet * 0.55, sand, (0.55, 0.5, 0.44, 1.0), "MULTIPLY")
    color = g.mixc(tint, color, water)
    foam = g.smooth(z, 0.2, 0.0) * g.smooth(z, -0.35, -0.05) * g.smooth(g.noise(g.pos, 2.0, 2, 0.5), 0.35, 0.65)
    color = g.mixc(foam * 0.85, color, (0.95, 0.97, 1.0, 1.0))
    s = Surface(g, color, rough=g.lerp(wet, 0.95, 0.4), spec=0.2, height=ripple * 0.03)
    s.finish(0.4)


def shade_seabed(mat: bpy.types.Material) -> None:
    g = Graph(mat)
    Surface(g, hexcolor("#0A3A58"), rough=1.0, spec=0.0).finish()


def shade_sea(mat: bpy.types.Material) -> None:
    """Glossy water: swell plus ripples fading with distance, reflective at grazing angles, clear below."""
    g = Graph(mat)
    swell = g.noise(g.vmul(g.pos, (0.05, 0.07, 0.05)), 1.0, 3, 0.5)
    chop = g.noise(g.vmul(g.pos, (0.7, 0.7, 0.7)), 1.0, 2, 0.5)
    height = swell * 0.5 + chop * 0.06 / (1.0 + g.distance() / 120.0)
    bump = g.add("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    g.feed(bump.inputs["Height"], height)
    fres = g.add("ShaderNodeFresnel")
    fres.inputs["IOR"].default_value = 1.33
    gloss = g.add("ShaderNodeBsdfGlossy")
    gloss.inputs["Roughness"].default_value = 0.03
    clear = g.add("ShaderNodeBsdfTransparent")
    mix = g.add("ShaderNodeMixShader")
    for node in (fres, gloss):
        g.nt.links.new(bump.outputs["Normal"], node.inputs["Normal"])
    g.nt.links.new(fres.outputs[0], mix.inputs[0])
    g.nt.links.new(clear.outputs[0], mix.inputs[1])
    g.nt.links.new(gloss.outputs[0], mix.inputs[2])
    out = g.add("ShaderNodeOutputMaterial")
    g.nt.links.new(mix.outputs[0], out.inputs[0])


def shade_hidden(mat: bpy.types.Material) -> None:
    g = Graph(mat)
    out = g.add("ShaderNodeOutputMaterial")
    g.nt.links.new(g.add("ShaderNodeBsdfTransparent").outputs[0], out.inputs[0])


def shade_rampart(mat: bpy.types.Material, base: tuple) -> None:
    """Sandy stone blocks; the block grid follows the wall using the face normal, tops use x and y."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    n = g.geo("True Normal")
    nx, ny, nz = g.xyz(n)
    px, py, pz = g.xyz(g.pos)
    side = abs(nz) < 0.5
    run = (px * -ny + py * nx) / g.vmax(g.math("SQRT", nx * nx + ny * ny), 0.001)
    brick = g.add("ShaderNodeTexBrick", offset=0.5, offset_frequency=2, squash=1.0, squash_frequency=2)
    g.feed(brick.inputs["Vector"], g.vec(g.lerp(side, px, run), g.lerp(side, py, pz), 0.0))
    brick.inputs["Color1"].default_value = tuple(x * 1.1 for x in base[:3]) + (1.0,)
    brick.inputs["Color2"].default_value = tuple(x * 0.8 for x in base[:3]) + (1.0,)
    brick.inputs["Mortar"].default_value = tuple(x * 0.45 for x in base[:3]) + (1.0,)
    for name, value in (("Scale", 1.0), ("Mortar Size", 0.03), ("Mortar Smooth", 0.2), ("Brick Width", 0.9), ("Row Height", 0.45)):
        brick.inputs[name].default_value = value
    color = g.mixc(1.0, Val(g, brick.outputs["Color"]), 0.85 + 0.3 * (big - 0.5) + 0.3 * (mid - 0.5), "MULTIPLY")
    grime = g.smooth(g.noise(g.vmul(g.pos, (1.2, 1.2, 0.1)), 1.0, 2, 0.5), 0.5, 0.85) * 0.3
    color = g.mixc(grime, color, (0.55, 0.5, 0.44, 1.0), "MULTIPLY")
    Surface(g, color, rough=0.9, spec=0.2, height=Val(g, brick.outputs["Fac"]) * 0.03 + fine * 0.01).finish(0.8)


def shade_stone(mat: bpy.types.Material, base: tuple) -> None:
    """Minaret masonry: courses by height with slight tone shifts."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    pz = g.xyz(g.pos)[2]
    course = g.fract(pz / 0.45)
    line = g.smooth(abs(course - 0.5), 0.46, 0.5)
    tone = 0.9 + 0.2 * g.rand(g.floor(pz / 0.45), 0.0, 1.0) + 0.2 * (mid - 0.5)
    color = g.mixc(line * 0.5, g.mixc(1.0, base, tone, "MULTIPLY"), (0.45, 0.4, 0.33, 1.0), "MULTIPLY")
    Surface(g, color, rough=0.9, spec=0.2, height=line * -0.02 + fine * 0.005).finish(0.6)


def shade_glaze(mat: bpy.types.Material, base: tuple) -> None:
    """Glazed green dome tiles."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    color = g.mixc(1.0, base, 0.85 + 0.3 * (mid - 0.5) + 0.2 * (fine - 0.5), "MULTIPLY")
    Surface(g, color, rough=0.28, spec=0.6, height=fine * 0.01).finish(0.4)


def shade_foliage(mat: bpy.types.Material, base: tuple) -> None:
    """Leaves: tone variation in space, a little translucency so sun-lit crowns glow."""
    g = Graph(mat)
    big, mid, fine = g.noises()
    color = g.mixc(1.0, base, 0.7 + 0.6 * big + 0.3 * (mid - 0.5), "MULTIPLY")
    bsdf = g.add("ShaderNodeBsdfPrincipled")
    g.feed(bsdf.inputs["Base Color"], color)
    bsdf.inputs["Roughness"].default_value = 0.65
    spec_input(bsdf).default_value = 0.2
    leaf = g.add("ShaderNodeBsdfTranslucent")
    g.feed(leaf.inputs["Color"], g.mixc(1.0, color, (1.4, 1.3, 0.9, 1.0), "MULTIPLY"))
    mix = g.add("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.35
    g.nt.links.new(bsdf.outputs[0], mix.inputs[1])
    g.nt.links.new(leaf.outputs[0], mix.inputs[2])
    out = g.add("ShaderNodeOutputMaterial")
    g.nt.links.new(mix.outputs[0], out.inputs[0])


def shade_trunk(mat: bpy.types.Material, base: tuple) -> None:
    g = Graph(mat)
    bark = g.noise(g.vmul(g.pos, (6.0, 6.0, 0.7)), 1.0, 3, 0.6)
    color = g.mixc(1.0, base, 0.6 + 0.8 * bark, "MULTIPLY")
    Surface(g, color, rough=0.9, spec=0.15, height=bark * 0.05).finish(0.6)


def shade_tank(mat: bpy.types.Material) -> None:
    g = Graph(mat)
    big = g.noise(g.pos, 0.8, 2, 0.5)
    Surface(g, g.mixc(1.0, (0.85, 0.85, 0.82, 1.0), 0.92 + 0.12 * (big - 0.5), "MULTIPLY"), rough=0.4, spec=0.45).finish()


def build_materials(mats: dict[str, bpy.types.Material]) -> None:
    """Replace every palette material by its procedural shader, keeping the generator's base color."""
    base = {name: tuple(m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value)
            if m.node_tree and "Principled BSDF" in m.node_tree.nodes else (0.6, 0.6, 0.6, 1.0) for name, m in mats.items()}
    for name, mat in mats.items():
        b = base[name]
        kind = STYLE_OF.get(name)
        if kind == "metal":
            shade_metal(mat, b)
        elif kind and DRESSED:
            shade_plaster(mat, b)                          # the kit's doors and windows are on the walls
        elif kind:
            shade_facade(mat, kind, b)
        elif name in ("roof_white", "dome_white", "roof_tile"):
            shade_plaster(mat, b)
        elif name == "asphalt":
            shade_asphalt(mat, b)
        elif name == "paving":
            shade_paving(mat, b)
        elif name in ("urban_ground", "grass", "steppe"):
            shade_dust(mat, b, 1.0 if name == "urban_ground" else 0.9)
        elif name == "beach":
            shade_beach(mat, b)
        elif name == "water":
            shade_hidden(mat)                              # the big sea plane replaces the tile water
        elif name == "rampart":
            shade_rampart(mat, b)
        elif name == "minaret_stone":
            shade_stone(mat, b)
        elif name == "dome_green":
            shade_glaze(mat, b)
        elif name.startswith("leaf"):
            shade_foliage(mat, b)
        elif name == "trunk":
            shade_trunk(mat, b)
        else:
            print(f"beauty: no shader for material {name}, kept as imported")


# --- scene: import, wall data, dressing ----------------------------------------------

def load_index(out_dir: str) -> tuple[Path, dict]:
    folder = Path(out_dir).expanduser()
    if not (folder / "index.json").is_file() and (folder / "tiles" / "index.json").is_file():
        folder = folder / "tiles"
    return folder, json.loads((folder / "index.json").read_text(encoding="utf-8"))


def import_tiles(folder: Path, index: dict) -> tuple[list[bpy.types.Object], dict[str, bpy.types.Material]]:
    """Import every tile; "grass.012" and "grass" share one material, as in tools/blender_import.py.

    Returns the tile meshes (the dressing pieces are placed but not returned) and the materials.
    """
    if not hasattr(bpy.ops.import_scene, "gltf"):
        bpy.ops.preferences.addon_enable(module="io_scene_gltf2")
    mats: dict[str, bpy.types.Material] = {}
    tiles: list[bpy.types.Object] = []
    for tile in index["tiles"]:
        before = {o.name for o in bpy.data.objects}
        bpy.ops.import_scene.gltf(filepath=str(folder / tile["file"]))
        fresh = [o for o in bpy.data.objects if o.name not in before]
        dressing = expand_instances(fresh, folder / tile["file"])
        for ob in fresh:
            if ob.type != "MESH":
                continue
            if ob.name not in dressing:
                tiles.append(ob)
            for slot in ob.material_slots:
                if slot.material is None:
                    continue
                keep = mats.setdefault(COPY_SUFFIX.sub("", slot.material.name), slot.material)
                if keep is not slot.material:
                    old, slot.material = slot.material, keep
                    if old.users == 0:
                        bpy.data.materials.remove(old)
    return tiles, mats


def get(items, name: str, n: int, dtype) -> np.ndarray:
    out = np.empty(n, dtype)
    items.foreach_get(name, out)
    return out


def bake_wall_uvs(ob: bpy.types.Object) -> None:
    """Add UV maps wallA = (wall start u, wall length) and wallB = (foot, top) in meters to every wall triangle.

    Each wall is a rectangle of two triangles, so both triangles see the full extent in u and in height.
    """
    me = ob.data
    n = len(me.polygons)
    layers = [me.uv_layers.new(name="wallA"), me.uv_layers.new(name="wallB")]
    walls = {i for i, s in enumerate(ob.material_slots) if s.material and STYLE_OF.get(s.material.name)}
    start = get(me.polygons, "loop_start", n, np.int32)
    if not walls or not np.all(get(me.polygons, "loop_total", n, np.int32) == 3):
        return
    mat = get(me.polygons, "material_index", n, np.int32)
    nz = get(me.polygons, "normal", n * 3, np.float32).reshape(-1, 3)[:, 2]
    uv = get(me.uv_layers["UVMap"].data, "uv", len(me.loops) * 2, np.float32).reshape(-1, 2)
    loops = start[:, None] + np.arange(3)
    u, h = uv[loops, 0], uv[loops, 1] - 1.0
    sel = np.isin(mat, list(walls)) & (np.abs(nz) < 0.5)
    a = np.where(sel[:, None], np.stack([u.min(1), u.max(1) - u.min(1)], 1), 0.0)
    b = np.where(sel[:, None], np.stack([h.min(1), h.max(1)], 1), 0.0)
    for layer, data in zip(layers, (a, b)):
        flat = np.zeros((len(me.loops), 2), np.float32)
        flat[loops.ravel()] = np.repeat(data, 3, axis=0)
        layer.data.foreach_set("uv", flat.ravel())


def roof_parts(ob: bpy.types.Object, slot: int):
    """Boundary edges (p0, p1, one per row) and per-roof triangle groups of the flat roof_white roofs."""
    me = ob.data
    n = len(me.polygons)
    mat = get(me.polygons, "material_index", n, np.int32)
    nz = get(me.polygons, "normal", n * 3, np.float32).reshape(-1, 3)[:, 2]
    start = get(me.polygons, "loop_start", n, np.int32)
    sel = np.flatnonzero((mat == slot) & (nz > 0.9))
    if not len(sel):
        return None
    vid = get(me.loops, "vertex_index", len(me.loops), np.int32)
    co = get(me.vertices, "co", len(me.vertices) * 3, np.float32).reshape(-1, 3)
    pts = co[vid[start[sel][:, None] + np.arange(3)]]                    # (T, 3, 3)
    _, ids = np.unique(np.round(pts.reshape(-1, 3) * 50).astype(np.int64), axis=0, return_inverse=True)
    ids = np.asarray(ids).reshape(-1, 3)
    a, b = ids.ravel(), ids[:, [1, 2, 0]].ravel()
    count = ids.max() + 1
    key = np.minimum(a, b) * count + np.maximum(a, b)
    _, inverse, counts = np.unique(key, return_inverse=True, return_counts=True)
    border = counts[inverse] == 1
    p0, p1 = pts.reshape(-1, 3)[border], pts[:, [1, 2, 0]].reshape(-1, 3)[border]
    label = np.arange(count)
    for _ in range(80):
        low = label[ids].min(axis=1)
        new = label.copy()
        np.minimum.at(new, ids.ravel(), np.repeat(low, 3))
        if np.array_equal(new, label):
            break
        label = new
    group = label[ids[:, 0]]
    return p0, p1, np.repeat(group, 3)[border], pts, group


def add_parapet(bm: bmesh.types.BMesh, p0, p1) -> None:
    """A low wall along one roof edge, its outer face flush with the facade (outside = right of the edge)."""
    dx, dy = float(p1[0] - p0[0]), float(p1[1] - p0[1])
    length = math.hypot(dx, dy)
    if length < 0.05:
        return
    ix, iy = -dy / length * PARAPET_THICK, dx / length * PARAPET_THICK          # inward = left of the edge
    corners = ((p0[0], p0[1], p0[2]), (p1[0], p1[1], p1[2]), (p1[0] + ix, p1[1] + iy, p1[2]), (p0[0] + ix, p0[1] + iy, p0[2]))
    low = [bm.verts.new(c) for c in corners]
    top = [bm.verts.new((c[0], c[1], c[2] + PARAPET_HEIGHT)) for c in corners]
    for quad in ((low[0], low[1], top[1], top[0]), (low[2], low[3], top[3], top[2]), (top[0], top[1], top[2], top[3])):
        bm.faces.new(quad).material_index = 0


def add_tank(bm: bmesh.types.BMesh, x: float, y: float, z: float, gen: np.random.Generator) -> None:
    """A short white cylinder on four legs."""
    r, h, leg, k = gen.uniform(0.55, 0.75), gen.uniform(0.9, 1.2), 0.45, 12

    def ring(zz: float) -> list:
        return [bm.verts.new((x + r * math.cos(2 * math.pi * i / k), y + r * math.sin(2 * math.pi * i / k), zz)) for i in range(k)]

    low, top, cap = ring(z + leg), ring(z + leg + h), ring(z + leg + h)
    for i in range(k):
        f = bm.faces.new((low[i], low[(i + 1) % k], top[(i + 1) % k], top[i]))
        f.material_index, f.smooth = 1, True
    bm.faces.new(cap).material_index = 1
    bm.faces.new(low[::-1]).material_index = 1
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        lx, ly, s = x + sx * r * 0.6, y + sy * r * 0.6, 0.05
        b = [bm.verts.new((lx + dx, ly + dy, zz)) for zz in (z, z + leg) for dx, dy in ((-s, -s), (s, -s), (s, s), (-s, s))]
        for q in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            bm.faces.new([b[i] for i in q]).material_index = 1


def dress_tile(ob: bpy.types.Object, plaster, tank, seed: int):
    slot = next((i for i, s in enumerate(ob.material_slots) if s.material and s.material.name == "roof_white"), None)
    parts = roof_parts(ob, slot) if slot is not None else None
    if parts is None:
        return None, 0, 0
    p0, p1, edge_group, pts, group = parts
    bm = bmesh.new()
    if not PARAPETS:   # the generator's tiles already carry their parapets (index "parapets")
        for a, b in zip(p0, p1):
            add_parapet(bm, a, b)
    gen = rng(seed, "tanks", ob.name)
    tanks = 0
    area = np.linalg.norm(np.cross(pts[:, 1] - pts[:, 0], pts[:, 2] - pts[:, 0]), axis=1) / 2
    for g_id in np.unique(group):
        if DRESSED or gen.random() >= TANK_SHARE:
            continue
        tris = np.flatnonzero(group == g_id)
        if area[tris].sum() < 30.0:
            continue
        edges = np.flatnonzero(edge_group == g_id)
        for t in tris[np.argsort(-area[tris])][:3]:
            c = pts[t].mean(axis=0)
            q0, q1 = p0[edges][:, :2], p1[edges][:, :2]
            seg = q1 - q0
            t_par = np.clip(((c[:2] - q0) * seg).sum(1) / np.maximum((seg * seg).sum(1), 1e-6), 0, 1)
            dist = np.linalg.norm(q0 + seg * t_par[:, None] - c[:2], axis=1).min()
            if dist > 1.4:
                add_tank(bm, c[0], c[1], c[2], gen)
                tanks += 1
                break
    me = bpy.data.meshes.new(f"{ob.name}_roofs")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(plaster)
    me.materials.append(tank)
    dress = bpy.data.objects.new(me.name, me)
    dress.matrix_world = ob.matrix_world.copy()
    bpy.context.scene.collection.objects.link(dress)
    return dress, 0 if PARAPETS else len(p0), tanks


def flat_quad(name: str, z: float, half: float, mat: bpy.types.Material) -> None:
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-half, -half, z), (half, -half, z), (half, half, z), (-half, half, z)], [], [(0, 1, 2, 3)])
    me.materials.append(mat)
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(name, me))


# --- lighting, camera, render --------------------------------------------------------

def setup_world(scene: bpy.types.Scene) -> None:
    world = bpy.data.worlds.new("Beauty Sky")
    world.use_nodes = True
    scene.world = world
    nt = world.node_tree
    nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    types = {item.identifier for item in sky.bl_rna.properties["sky_type"].enum_items}
    sky.sky_type = "NISHITA" if "NISHITA" in types else "MULTIPLE_SCATTERING"   # Blender 5 renamed the physical sky
    sky.sun_disc = False
    sky.sun_elevation, sky.sun_rotation = math.radians(SUN_ELEVATION), math.radians(SUN_AZIMUTH)   # rotation reads as compass azimuth
    sky.air_density, sky.altitude = 1.0, 0.0
    if hasattr(sky, "dust_density"):
        sky.dust_density = 3.0
    else:
        sky.aerosol_density = 3.0   # Blender 5 name for the dust in the air
    bg, out = nt.nodes.new("ShaderNodeBackground"), nt.nodes.new("ShaderNodeOutputWorld")
    bg.inputs["Strength"].default_value = SKY_STRENGTH
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])


def setup_haze(scene: bpy.types.Scene) -> None:
    """Aerial haze in the compositor (a world volume would also extinguish the sun): mix toward a pale
    sky color by 1 - exp(-density * depth); the sky itself (no depth) is left alone."""
    scene.view_layers[0].use_pass_z = True
    if bpy.app.version >= (5, 0, 0):        # Blender 5 moved the compositor into a node group
        setup_haze_group(scene)
        return
    scene.use_nodes = True
    nt = scene.node_tree
    nt.nodes.clear()
    layers, comp, mix = (nt.nodes.new(k) for k in ("CompositorNodeRLayers", "CompositorNodeComposite", "CompositorNodeMixRGB"))

    def math(op: str, a, b):
        node = nt.nodes.new("CompositorNodeMath")
        node.operation = op
        for sock, value in zip(node.inputs, (a, b)):
            if isinstance(value, bpy.types.NodeSocket):
                nt.links.new(value, sock)
            else:
                sock.default_value = value
        return node.outputs[0]

    depth = layers.outputs["Depth"]
    keep = math("SUBTRACT", 1.0, math("POWER", 2.71828, math("MULTIPLY", depth, -HAZE_DENSITY)))
    fac = math("MINIMUM", math("MULTIPLY", keep, math("LESS_THAN", depth, 1e8)), HAZE_MAX)
    nt.links.new(fac, mix.inputs[0])
    nt.links.new(layers.outputs["Image"], mix.inputs[1])
    mix.inputs[2].default_value = HAZE_COLOR
    grade = nt.nodes.new("CompositorNodeColorBalance")          # golden hour grade: warm highlights, cool shadows
    grade.correction_method = "LIFT_GAMMA_GAIN"
    grade.gain, grade.lift = GRADE_GAIN, GRADE_LIFT
    nt.links.new(mix.outputs[0], grade.inputs["Image"])
    nt.links.new(grade.outputs[0], comp.inputs["Image"])


def comp_socket(node, name: str, kind: str):
    """The socket called `name` of type `kind`: the unified 5.x nodes carry one per data type."""
    return next(s for s in node.inputs if s.name == name and s.type == kind)


def setup_haze_group(scene: bpy.types.Scene) -> None:
    """Blender 5: the compositor is a node group with a Group Output instead of a Composite node.

    Same chain as the 3.6 and 4.x path above. The math and mix nodes are the unified shader nodes,
    and the color balance method is a menu socket whose default is already Lift/Gamma/Gain, so it
    is left alone.
    """
    group = bpy.data.node_groups.new("Beauty Haze", "CompositorNodeTree")
    group.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = group
    nt = group
    layers = nt.nodes.new("CompositorNodeRLayers")
    nt.nodes.new("NodeGroupOutput")
    comp = next(n for n in nt.nodes if n.bl_idname == "NodeGroupOutput")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"

    def math(op: str, a, b):
        node = nt.nodes.new("ShaderNodeMath")
        node.operation = op
        for sock, value in zip(node.inputs, (a, b)):
            if isinstance(value, bpy.types.NodeSocket):
                nt.links.new(value, sock)
            else:
                sock.default_value = value
        return node.outputs[0]

    depth = layers.outputs["Depth"]
    keep = math("SUBTRACT", 1.0, math("POWER", 2.71828, math("MULTIPLY", depth, -HAZE_DENSITY)))
    fac = math("MINIMUM", math("MULTIPLY", keep, math("LESS_THAN", depth, 1e8)), HAZE_MAX)
    nt.links.new(fac, comp_socket(mix, "Factor", "VALUE"))
    nt.links.new(layers.outputs["Image"], comp_socket(mix, "A", "RGBA"))
    comp_socket(mix, "B", "RGBA").default_value = HAZE_COLOR
    grade = nt.nodes.new("CompositorNodeColorBalance")          # golden hour grade: warm highlights, cool shadows
    comp_socket(grade, "Gain", "RGBA").default_value = GRADE_GAIN + (1.0,)
    comp_socket(grade, "Lift", "RGBA").default_value = GRADE_LIFT + (1.0,)
    nt.links.new(next(o for o in mix.outputs if o.type == "RGBA"), grade.inputs["Image"])
    nt.links.new(grade.outputs[0], comp.inputs["Image"])


def setup_sun(scene: bpy.types.Scene) -> None:
    az, el = math.radians(SUN_AZIMUTH), math.radians(SUN_ELEVATION)
    to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    light = bpy.data.lights.new("Beauty Sun", "SUN")
    light.energy, light.color, light.angle = SUN_STRENGTH, SUN_COLOR, math.radians(0.6)
    sun = bpy.data.objects.new("Beauty Sun", light)
    sun.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)


def camera_pose(index: dict, view: str) -> tuple[Vector, Vector]:
    if view == "aerial":
        f = index["focus"]
        focus = Vector((f["x"], f["y"], f.get("z", 0.0)))
        b = math.radians(AERIAL[0])
        return focus + Vector((math.sin(b) * AERIAL[1], math.cos(b) * AERIAL[1], AERIAL[2])), focus
    spot = index["views"][view]
    return Vector(spot["cam"]), Vector(spot["look"])


def setup_camera(scene: bpy.types.Scene, index: dict, view: str) -> None:
    pos, look = camera_pose(index, view)
    data = bpy.data.cameras.new("Beauty Camera")
    data.sensor_fit, data.angle_y = "VERTICAL", math.radians(FOV)
    data.clip_start, data.clip_end = 0.1, 500000.0
    cam = bpy.data.objects.new("Beauty Camera", data)
    cam.location = pos
    cam.rotation_euler = (look - pos).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam


def setup_render(scene: bpy.types.Scene, size: tuple[int, int], samples: int, png: str) -> None:
    scene.render.engine = "CYCLES"
    cy = scene.cycles
    cy.device, cy.samples = "CPU", samples
    cy.use_adaptive_sampling, cy.adaptive_threshold = True, 0.02
    cy.use_denoising, cy.denoiser, cy.denoising_input_passes = True, "OPENIMAGEDENOISE", "RGB_ALBEDO_NORMAL"
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 6, 3, 3
    cy.transmission_bounces, cy.transparent_max_bounces, cy.volume_bounces = 2, 8, 0
    cy.sample_clamp_indirect = 6.0
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = size[0], size[1], 100
    scene.render.image_settings.file_format, scene.render.image_settings.color_depth = "PNG", "8"
    scene.render.filepath = png
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = EXPOSURE
    for look in ("Medium High Contrast", "Filmic - Medium High Contrast"):
        try:
            scene.view_settings.look = look
            print(f"beauty: view transform Filmic, look {look}")
            break
        except TypeError:
            continue


# --- main ----------------------------------------------------------------------------

def read_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="blender -b --python blender_beauty.py --", description=__doc__.splitlines()[0])
    ap.add_argument("out_dir", help="generator output folder, or its tiles folder")
    ap.add_argument("--view", choices=("aerial", "street", "souk"), default="aerial")
    ap.add_argument("--png", required=True, help="output image")
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--size", default="1600x900", help="WIDTHxHEIGHT")
    ap.add_argument("--setup-only", action="store_true", help="build the scene and stop before rendering")
    return ap.parse_args(argv)


def main() -> None:
    args = read_args()
    width, height = (int(v) for v in args.size.lower().split("x"))
    clock = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    folder, index = load_index(args.out_dir)
    global DRESSED, PARAPETS
    DRESSED = any(t.get("pieces", 0) for t in index["tiles"])
    PARAPETS = bool(index.get("parapets"))
    tiles, mats = import_tiles(folder, index)
    print(f"beauty: imported {len(tiles)} tiles in {time.time() - clock:.1f} s", flush=True)

    build_materials(mats)
    plaster = mats.get("roof_white") or next(iter(mats.values()))
    tank = bpy.data.materials.new("tank_white")
    shade_tank(tank)
    sea, bottom = bpy.data.materials.new("sea"), bpy.data.materials.new("seabed")
    shade_sea(sea)
    shade_seabed(bottom)
    seed = int(index.get("seed", 0))
    edges = tanks = 0
    for ob in tiles:
        bake_wall_uvs(ob)
        dress, n_edges, n_tanks = dress_tile(ob, plaster, tank, seed)
        edges, tanks = edges + n_edges, tanks + n_tanks
    flat_quad("Sea", SEA_LEVEL, 250000.0, sea)
    flat_quad("Seabed", SEA_BOTTOM, 250000.0, mats.get("beach") or bottom)
    print(f"beauty: {edges} parapet edges, {tanks} tanks, scene ready at {time.time() - clock:.1f} s", flush=True)

    setup_world(scene)
    setup_haze(scene)
    setup_sun(scene)
    setup_camera(scene, index, args.view)
    setup_render(scene, (width, height), args.samples, args.png)
    if args.setup_only:
        return
    start = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"beauty: rendered {args.view} {width}x{height} at {args.samples} samples in {time.time() - start:.1f} s -> {args.png}")


if __name__ == "__main__":
    main()
