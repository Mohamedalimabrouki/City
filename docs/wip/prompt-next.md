# prompt-next: prompts ready to start now (3 November, 20:57 UTC)

Source: docs/ROADMAP.md (ticked: 1 to 53, with 20.1 and 20.2) and the "Needs" line of each
prompt in docs/prompts/*.md. Ready = unticked, every prompt in "Needs" ticked.

## Ready now (13)
| Prompt | Size | Risk (one line) |
|---|---|---|
| 54 H2c Furnishing rules (52, 53) | L, in progress | Low: built; open 4.2% rooms miss a piece (target 2%), tied to the 47.2 planner, may need a lead decision to tick |
| 59 B1a Rivers (1) | M | Medium: changes the terrain, so many tiles change in the fingerprint; a rivers-59 branch already exists |
| 66 B4 Oasis towns (1) | M | Medium: new settlements; append them at the end so households do not shift |
| 67 B5 Hilltop ksar villages (12) | M | Medium: rebuilds village houses on steep ground (tiles change) |
| 70 C4a Street graph for games (12) | M | Low: an export only, no look change |
| 72 C3a Godot: stream the city (40) | M | Low for the generator, but Look is "Ali": needs Godot on the Mac to check |
| 75 C5 Unreal 5 import (39) | M | Low for the generator; written without the engine (Epic account), so untested here |
| 80 D6 Residents (none) | M | Low-medium: new data per household; own streams, determinism test |
| 81 D1a District histories (1) | S | Low: text only |
| 87 D5a Arabic place names (1) | M | Low-medium: Ali must check the Arabic sample |
| 92 E2 Faster terrain (1) | M | Medium: must keep the ground identical (fingerprint unchanged) or say why |
| 94 F4 Styles per region (1) | M, Opus | Medium: changes how style packs are chosen; touches every city's look |
| 101 K1 Asset review tool (2, 38) | M | Low: a tool, no city change |

Fix tasks open without a "Needs" line: 47.1, 48.1, 47.2 (planner rounds, in progress).

## Not ready, but already started on a branch (per the WORKLOG commits)
- 55 H2d (needs 54, unticked) and 60 B1b (needs 59, unticked): fine as work in progress, but
  do not tick them before 54 and 59.

## Suggested order (most later prompts unlocked first)
1. Finish 54 (unlocks 55, then 56, 57, 58).
2. 59 (unlocks 60 to 65, 68, then 89 and 97).
3. 70 (unlocks 71 and 76, then 79, 88, 90, 102).
4. 80 (unlocks 82, 102, 105).
5. 81 (unlocks 83, 84, 85, 86), then 92 (unlocks 93), then 101 (unlocks 103 and the K prompts).
6. 87, 66, 67, 94 (each unlocks little now; 94 unlocks 95, 96, 98).
7. 72 and 75 last: they need Ali's own machine (Godot, Unreal) to look.

Left: nothing; sizes are from the prompt headers, risks are my one-line reading, not a code check.
