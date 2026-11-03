# fix-textile (WIP, 3 November): sheet `fix-textile.png` (mattresses and cushions, kit as now)

Better: the ticking mattress's top shows its stripes again (the swept cover has its own UVs: u along the bench, v down the profile, equal to y on the top as on the old flat pad), and the cushion is one smooth domed cover over the seam with a thin round gold cord (red on the gold one, about 1 cm, its own normals) instead of the wide flat frame; `pytest -q -k "kit or home or furn"` passes (14).
Doubt: the cushion now costs 72 triangles (was 40; TABLE budget raised, the cord is 32 of them) and its outline still shows the 8 corners of its superellipse; the rounded mattress front still reads like the old box from the kit view; not yet seen in a room render.
