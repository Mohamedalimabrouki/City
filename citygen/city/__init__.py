"""City planner: turns one settlement of the world into streets, lots, buildings and trees.

Pipeline (each step is its own module):
  layout     land, city limit, old town outline, neighborhoods and their kinds
  medina     great mosque, gates, souks and alleys, ramparts
  kasbah     the citadel on the old town's high edge (capital and cities; its buildings come last)
  streets    arterials, ring road, boulevard, road links, local street grids, street trees
  parcels    blocks between streets, split into building lots
  impasses   dead-end lanes to the lots without a street (old town and neighborhoods)
  landmarks  a cathedral and a theatre on merged colonial lots facing the boulevard (their buildings come last)
  buildings  a building per lot following the district rules, landmarks, parks, cemetery
  massing    rows, cut corners, domes, set-back top floors, stepped slabs, villa L's, roof rooms
             (after households and souks: it never adds, removes or reorders a building)
  greenery   street trees on arterials, courtyard trees, villa fruit trees (last: only appends trees)
"""
from __future__ import annotations

import math
import time

from shapely.geometry import LineString

from ..names import NameMaker
from ..rng import stream
from .buildings import cemetery_and_parks, make_buildings, neighborhood_mosques
from .greenery import greenery
from .layout import assign_kinds, city_boundary, land_near, main_axis, medina_outline, neighborhoods
from .life import households, souks
from .massing import apply_massing
from .impasses import cut_impasses
from . import landmarks as boulevard
from .medina import old_town
from .model import CityPlan, District
from .parcels import make_blocks, make_parcels
from .paint import make_paint, street_surfaces
from .streets import local_streets, major_streets, road_links, street_trees
from .walks import make_walks


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
    streets, buildings, landmarks, cut, kasbah = [], [], [], None, None
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
        streets, buildings, cut, landmarks, _gates, kasbah = old_town(ctx, medina, 0, axis, crossings)
    streets += major_streets(ctx, districts, medina, axis, land)
    streets += road_links(ctx, roads, streets)
    streets += local_streets(ctx, districts)
    street_surfaces(districts, streets, world.style)
    blocks = make_blocks(ctx, districts, streets, cut)
    walks = make_walks(ctx, districts, streets, blocks)
    parcels = make_parcels(ctx, blocks, districts)
    mosques, mosque_marks, used = neighborhood_mosques(ctx, districts, parcels)
    parcels, used, lanes = cut_impasses(ctx, blocks, districts, parcels, streets, used)
    streets += lanes   # appended last: every earlier street keeps its index (walks, souks, paint)
    sites = boulevard.sites(ctx, parcels, districts, streets, used)
    parcels, used = boulevard.merge(parcels, used, sites)   # merged lots at the end, nothing built on them
    houses, trees = make_buildings(ctx, parcels, districts, used | {s.parcel for s in sites})
    green_buildings, green_trees = cemetery_and_parks(ctx, districts, blocks)
    buildings += houses + mosques + green_buildings
    marks = landmarks + mosque_marks
    if kasbah is not None:   # appended last: every earlier building and landmark keeps its index
        buildings += kasbah.buildings
        marks.append(kasbah.landmark)
    civic, civic_marks = boulevard.buildings(ctx, sites)   # after the kasbah, for the same reason
    buildings += civic
    marks += civic_marks
    tree_clear = float(ctx.style.get("landmarks", {}).get("tree_clear", 0.0))
    trees += green_trees + boulevard.clear_fronts(street_trees(ctx, streets), sites, tree_clear)
    plan = CityPlan(s, boundary, land, medina, districts, streets, blocks, parcels, buildings,
                    trees, marks, walks)
    plan.households = households(ctx, buildings, districts)
    plan.souks = souks(ctx, streets)
    apply_massing(ctx, plan)
    plan.paint = make_paint(world.style, streets, walks, districts)
    green = greenery(ctx, plan)
    trees += green   # appended last: every older tree keeps its index, so its kit variant and turn
    plan.stats = {"districts": len(districts), "streets": len(streets), "impasses": len(lanes),
                  "blocks": len(blocks),
                  "parcels": len(parcels), "buildings": len(buildings), "trees": len(trees),
                  "greenery": len(green),
                  "households": len(plan.households), "souks": len(plan.souks),
                  "seconds": round(time.perf_counter() - t0, 1)}
    return plan
