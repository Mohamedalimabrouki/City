# questions-ali (3 Nov, about 20:59 UTC): open questions for Ali
Sources: docs/wip/*.md on all 75 origin/wip/* branches (fetched now) and docs/WORKLOG.md on main.
Checked by keyword (question, choice, doubt, Ali); the newest first. Older WORKLOG items may already be settled.

1. Salt basins that drain (wip/fix-59 Q1, wip/review-59; hydro.py:173-178). A dry basin with little inflow drains
   to its spill instead of staying a salt lake. Choices: (a) keep as is; (b) `wet = max(wet, min_cells)` so every
   dry basin over 3 m and 0.5 km2 stays endorheic (changes the world).
2. Salt basin in two pockets (wip/fix-59 Q2; hydro.py:84, 195-203). Choices: (a) keep; (b) keep only the pocket
   holding the basin bottom, let the others drain into it, drop the xfail test mark (changes the world).
3. Salt lakes touching towns (wip/canon-60 rivers-59.md:34; WORKLOG l.33). Sota and Ain Chilel touch salt lakes;
   prompt 60 counts lakes as water. Choices: (a) accept; (b) move the towns or the lakes. Also: min_flow 2.0
   (221 rivers, more hill headwaters) tried, not applied: (a) keep 3.0; (b) take 2.0.
4. Arabic names, feminine agreement (wip/arabic-87 l.50, wip/fix-87 review-87.md:34; WORKLOG l.31). A masculine
   descriptor after a feminine core (name in ة). Choices: (a) keep; (b) make the descriptor feminine. Judge on the
   30-name sample.
5. Arabic names, long a (same sources). How often a long a is written (`vowels_ar`). Choices: (a) keep today's
   share; (b) more; (c) less. Judge on the 30-name sample.
6. Godot (WORKLOG l.32, wip/review-godot). Prompt 72 written, never run: Godot is not installed. Choice: yes/no
   to installing Godot so it can be run.
7. Kit textile (WORKLOG l.50, wip/fix-textile). The textile contact sheet looks worse; the fix makes the cushion
   72 triangles (was 40) and the 8 corners still show. Choices: (a) merge the fix; (b) more work first; (c) drop.
8. Kit hide (wip/fix-hide l.2). Ragged edges make legs and neck read less clearly; the rug dome cannot show (rug
   under 2 cm). Choices: (a) accept; (b) less ragged edge; (c) allow a thicker rug.
9. Kit brass (WORKLOG l.50). The tray rim is too steep for one-sided brass. Choices: (a) lower rim; (b) two-sided.
10. Lore wording (wip/fix-81b l.3, left items 5 and 9): count gates from all gate landmarks; name the top trade plus
   one drawn from the rest (not the same top 3 in every colonial quarter). Both change wording: needs Ali's look.
11. Furniture first values (wip/furn-55 l.15): Ali to judge the first values on the kit sheet.
12. Home kit decisions (WORKLOG l.575-582; defaults already written in SPEC 6d, Ali to confirm): period today or
   heritage (rec. today); density lived-in (rec. yes); prayer mats at 112 degrees (rec. yes); abstract verse (rec.
   yes); butane bottle blue #3B6FB6 (confirm); children and elders on their own stream; low-poly now, Blender later.
13. Flat pass bars 257/270 and 336/353 unreachable (WORKLOG l.683). Choices: (a) flat type from windows and area;
   (b) more windows on court walls and blank street walls (city change); (c) split floors by windows (28 blocks).
14. Courtyards and light wells for deep colonial blocks and maisons (WORKLOG l.1162, 31 Oct). Choices: (a) add a
   design step with courts or courettes; (b) keep street windows only. May be settled by houses-patio: check.
15. Older doubts (WORKLOG l.1622, 1674, 1723): the viewer tab opens on an `interior` spot that faces a wall (No.
   845); light slots of 0.3 m by stair windows; a closed slab persienne is one-sided from inside. Likely settled.
16. Many "Choices for Ali/lead" in WORKLOG l.766-1574 (entry steps, sunken entry, bit el ma upstairs, couloirs,
   split rooms, dark cells): each was taken by the lead and marked "Accepted"; Ali may review, none blocks.

Left: I did not read every note in full (keyword scan only), so a question worded without those words may be missed.
