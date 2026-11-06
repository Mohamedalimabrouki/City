"""City planner: turns one settlement of the world into streets, lots, buildings and trees.

Pipeline (each step is its own module):
  layout     land, city limit, old town outline, neighborhoods and their kinds
  medina     great mosque, gates, souks and alleys, ramparts
  kasbah     the citadel on the old town's high edge (capital and cities; its buildings come last)
  streets    arterials, ring road, boulevard, road links, local street grids, street trees
  station    the railway station across an avenue at the colonial quarter's edge, its tracks out to the
             city limit (its precinct and corridor are cut with the old town's; its buildings come last)
  parcels    blocks between streets, split into building lots
  impasses   dead-end lanes to the lots without a street (old town and neighborhoods)
  landmarks  a cathedral and a theatre on merged colonial lots facing the boulevard (their buildings come last)
  buildings  a building per lot following the district rules, landmarks, parks, cemetery
  massing    rows, cut corners, domes, set-back top floors, stepped slabs, villa L's, roof rooms
             (after households and souks: it never adds, removes or reorders a building)
  greenery   street trees on arterials, courtyard trees, villa fruit trees (last: only appends trees)
  port       quays along the port districts' coast, a breakwater and its lighthouse (after everything:
             it only adds the harbor, its land and the lighthouse's landmark, appended last)
  moorings   boats, cranes and cargo of the harbor
  corniche   the seafront promenade on the corniche's sea side (last: appends its walks and moves only the
             beach-side palms onto it, each keeping its index)
  river      keeps the plan off a river's corridor (prompt 61): read by layout, streets, station and walks
  bridges    where streets cross the river (prompt 62): the riverside walks stop at them; their streets are
             appended last and their heights read from the finished plan's ground
"""
from __future__ import annotations

import math
import time

from shapely.geometry import LineString
from shapely.ops import unary_union

from ..names import NameMaker, fixed_name
from ..rng import stream
from .bridges import off_decks, plan_bridges, raise_decks
from .buildings import cemetery_and_parks, make_buildings, neighborhood_mosques
from .greenery import greenery
from .layout import assign_kinds, city_boundary, lake_water, land_near, main_axis, medina_outline, neighborhoods
from .life import households, souks
from .massing import apply_massing
from .history import histories
from .impasses import cut_impasses
from . import landmarks as boulevard
from .medina import old_town
from .model import CityPlan, District
from .parcels import make_blocks, make_parcels
from .paint import deck_paint, make_paint, street_surfaces
from . import river
from .streets import local_streets, major_streets, road_links, street_trees
from .walks import make_walks
from . import station as railway
from .moorings import plan_props
from .port import lengths as port_lengths, plan_port
from .corniche import lengths as front_lengths, plan_fronts


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
        self.water = self.banks = None   # a river's corridor in this city and what the districts keep off (city/river.py)
        self.lake = None                 # the lakes and salt flats beside it

    def rng(self, *path):
        return stream(self.seed, "city", self.s.key, *path)


def plan_city(world, settlement) -> CityPlan:
    t0 = time.perf_counter()
    ctx = CityContext(world, settlement)
    s = settlement
    sea_land = land = land_near(world.terrain, s.x, s.y, s.radius * 1.35)
    ctx.lake = None if world.carve is None else lake_water(world.terrain, land, world.carve.shores)
    if ctx.lake is not None:      # a city ends on a shore, with room for its quay
        land = land.difference(ctx.lake.buffer(0.5 * float(ctx.kc["arterial_width"]) + 2.0, quad_segs=3)).simplify(1.0)
    water = river.corridor(world, s)
    if water is not None and ctx.kc["medina_radius"] >= 1.0:   # a village: on the bank its center lies on
        land = land.difference(water)
    ctx.boundary = boundary = city_boundary(ctx, land)
    if water is not None and water.intersects(boundary) and ctx.kc["medina_radius"] < 1.0:
        ctx.water = water
        ctx.banks = river.banks(ctx)
    roads = [r for r in world.roads if LineString(r.coords).intersects(boundary)]
    axis = main_axis(ctx, roads)
    medina = medina_outline(ctx, boundary)
    districts = neighborhoods(ctx, boundary, medina)
    assign_kinds(ctx, districts, medina, axis, sea_land)
    streets, buildings, landmarks, cut, kasbah = [], [], [], None, None
    if medina is not None:
        kind = "village" if medina is boundary else "medina"
        name = s.label if kind == "village" else fixed_name(world.style, "medina", s=s.label)
        districts.insert(0, District(0, kind, name, medina, axis))
        for i, d in enumerate(districts):
            d.id = i
        crossings = []
        for r in roads:
            hit = LineString(r.coords).intersection(medina.exterior)
            crossings += [p for p in getattr(hit, "geoms", [hit]) if p.geom_type == "Point"]
        streets, buildings, cut, landmarks, _gates, kasbah = old_town(ctx, medina, 0, axis, crossings)
    links = []
    if ctx.water is not None:     # the kinds and names were dealt as if no river ran here: only its banks change
        links = river.split_districts(ctx, districts)
    streets += major_streets(ctx, districts, medina, axis, sea_land)
    streets += road_links(ctx, roads, streets)
    streets += local_streets(ctx, districts)
    if ctx.water is not None:     # nothing crosses it but the bridges
        streets, cuts = river.cut_streets(streets, ctx.water)
        links += cuts
    station = railway.place(ctx, districts, streets, medina, cut, land if ctx.water is None else land.difference(ctx.water))
    if station is not None:   # local streets cut back from the precinct and from along the tracks
        streets = railway.clip_streets(ctx.style["station"], streets, station, 0)
        cut = railway.cut(station) if cut is None else unary_union([cut, railway.cut(station)])
    street_surfaces(districts, streets, world.style)
    blocks = make_blocks(ctx, districts, streets, cut)
    walks = railway.clip_walks(make_walks(ctx, districts, streets, blocks), station)
    parcels = make_parcels(ctx, blocks, districts)
    mosques, mosque_marks, used = neighborhood_mosques(ctx, districts, parcels)
    parcels, used, lanes = cut_impasses(ctx, blocks, districts, parcels, streets, used)
    through = streets[:]
    streets += lanes   # appended last: every earlier street keeps its index (walks, souks, paint)
    decks, bridges = [], []
    if ctx.water is not None:
        links = river.link_banks(ctx, streets, links)
        solid = [p for p, _d in blocks] + [b.footprint for b in buildings] + ([cut] if cut is not None else [])
        links, decks, bridges = plan_bridges(ctx, streets, links, solid)
    shore_walks = [] if ctx.water is None else river.riverside_walks(ctx, through + decks, medina)
    walks += shore_walks          # appended last: every other walk keeps its index
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
    rail_buildings, rail_marks = railway.buildings(ctx, station)   # after the boulevard's, for the same reason
    buildings += rail_buildings
    marks += rail_marks
    tree_clear = float(ctx.style.get("landmarks", {}).get("tree_clear", 0.0))
    trees += green_trees + off_decks(railway.clear(boulevard.clear_fronts(street_trees(ctx, streets), sites, tree_clear),
                                                   station), bridges) + river.riverside_trees(ctx, shore_walks)
    plan = CityPlan(s, boundary, land, medina, districts, streets, blocks, parcels, buildings,
                    trees, marks, walks)
    plan.station = station
    plan.households = households(ctx, buildings, districts)
    plan.souks = souks(ctx, streets)
    apply_massing(ctx, plan)
    plan.paint = make_paint(world.style, streets + decks, walks, districts)
    green = off_decks(railway.clear(greenery(ctx, plan), station), bridges)
    trees += green   # appended last: every older tree keeps its index, so its kit variant and turn
    plan.crossings = links
    plan.port, lights, plan.land = plan_port(ctx, districts, sea_land)   # reads districts and land only
    marks += lights   # appended last: every earlier landmark keeps its index
    plan.props = plan_props(ctx, plan)   # boats, cranes and cargo (prompt 35): planned last, moves nothing
    plan.fronts = plan_fronts(ctx, plan)  # the seafront promenade (prompt 36): appends walks, moves sea palms
    histories(ctx, plan)   # district histories (prompt 81): text only, read from the finished plan
    streets += decks       # last: no step above sees a bridge, and every earlier street keeps its index
    plan.bridges = raise_decks(ctx, plan, links, bridges)
    plan.deck_paint = deck_paint(world.style, plan.streets, plan.bridges)
    plan.stats = {"districts": len(districts), "streets": len(streets) - len(decks), "impasses": len(lanes),
                  "blocks": len(blocks),
                  "parcels": len(parcels), "buildings": len(buildings), "trees": len(trees),
                  "greenery": len(green),
                  "households": len(plan.households), "souks": len(plan.souks),
                  **({"quay_m": port_lengths(plan.port)["quays"], "breakwater_m": port_lengths(plan.port)["breakwaters"]}
                     if plan.port is not None else {}),
                  **(front_lengths(plan.fronts) if plan.fronts else {}),
                  **({"bridges": len(bridges), **ctx.bridge_notes} if bridges else {}),
                  "seconds": round(time.perf_counter() - t0, 1)}
    return plan
