"""City planner: turns one settlement of the world into streets, lots, buildings and trees.

Pipeline (each step is its own module):
  layout     land, city limit, old town outline, neighborhoods and their kinds
  medina     great mosque, gates, souks and alleys, ramparts
  streets    arterials, ring road, boulevard, road links, local street grids, street trees
  parcels    blocks between streets, split into building lots
  buildings  a building per lot following the district rules, landmarks, parks, cemetery
"""
from __future__ import annotations

import math
import time

from shapely.geometry import LineString

from ..names import NameMaker
from ..rng import stream
from .buildings import cemetery_and_parks, make_buildings, neighborhood_mosques
from .layout import assign_kinds, city_boundary, land_near, main_axis, medina_outline, neighborhoods
from .medina import old_town
from .model import CityPlan, District
from .parcels import make_blocks, make_parcels
from .streets import local_streets, major_streets, road_links, street_trees


class CityContext:
    """What every planning step needs: the world, the settlement, its rules and random streams."""

    def __init__(self, world, settlement):
        self.world = world
        self.s = settlement
        self.seed = world.seed
        self.style = world.style
        self.kc = world.style["settlement"][settlement.kind]
        self.qibla = math.radians(90.0 - float(world.style.get("qibla_bearing", 90.0)))
        self.namer = NameMaker(world.style, self.rng("landmark-names"))
        self.boundary = None

    def rng(self, *path):
        return stream(self.seed, "city", self.s.id, *path)


def plan_city(world, settlement) -> CityPlan:
    t0 = time.perf_counter()
    ctx = CityContext(world, settlement)
    s = settlement
    land = land_near(world.terrain, s.x, s.y, s.radius * 1.35)
    ctx.boundary = boundary = city_boundary(ctx, land)
    roads = [r for r in world.roads if LineString(r.coords).intersects(boundary)]
    axis = main_axis(ctx, roads)
    medina = medina_outline(ctx, boundary)
    districts = neighborhoods(ctx, boundary, medina)
    assign_kinds(ctx, districts, medina, axis, land)
    streets, buildings, landmarks, cut = [], [], [], None
    if medina is not None:
        kind = "village" if medina is boundary else "medina"
        name = s.name if kind == "village" else "Medina of " + s.name
        districts.insert(0, District(0, kind, name, medina, axis))
        for i, d in enumerate(districts):
            d.id = i
        crossings = []
        for r in roads:
            hit = LineString(r.coords).intersection(medina.exterior)
            crossings += [p for p in getattr(hit, "geoms", [hit]) if p.geom_type == "Point"]
        streets, buildings, cut, landmarks, _gates = old_town(ctx, medina, 0, axis, crossings)
    streets += major_streets(ctx, districts, medina, axis, land)
    streets += road_links(ctx, roads, streets)
    streets += local_streets(ctx, districts)
    blocks = make_blocks(ctx, districts, streets, cut)
    parcels = make_parcels(ctx, blocks, districts)
    mosques, mosque_marks, used = neighborhood_mosques(ctx, districts, parcels)
    houses, trees = make_buildings(ctx, parcels, districts, used)
    green_buildings, green_trees = cemetery_and_parks(ctx, districts, blocks)
    buildings += houses + mosques + green_buildings
    trees += green_trees + street_trees(ctx, streets)
    plan = CityPlan(s, boundary, land, medina, districts, streets, blocks, parcels, buildings,
                    trees, landmarks + mosque_marks)
    plan.stats = {"districts": len(districts), "streets": len(streets), "blocks": len(blocks),
                  "parcels": len(parcels), "buildings": len(buildings), "trees": len(trees),
                  "seconds": round(time.perf_counter() - t0, 1)}
    return plan
