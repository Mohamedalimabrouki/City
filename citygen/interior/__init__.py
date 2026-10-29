"""Interiors: the inside of one dwelling, made on demand from a build folder (SPEC 6c).

Never stored and never drawn by a normal build: `python -m citygen interior BUILDING` rebuilds the world
and the plan from a build's `summary.json` settings, replays the facade exactly as its tile dresses it
(`outside.py`), lays out the rooms (`layout.py`) and writes a folder the viewer opens (`export.py`).
The build key leaves this package out (`buildkey.NOT_BUILD_CODE`), so interior work never makes a build stale.
"""
from __future__ import annotations


class InteriorError(Exception):
    """Something the interior command cannot do; the message says why in plain words, and what to do."""


LAYOUTS = ("dar", "compact", "small", "koubba", "colonial", "slab", "villa", "maison")   # SPEC 6c "Who gets one"
