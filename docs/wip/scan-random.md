# scan-random: randomness and order risks on every wip branch (3 Nov, 20:57 UTC)

What I scanned: `git diff main...origin/wip/<b>` (added lines in *.py, *.toml, *.md) on all 60
origin/wip/* branches, for `import random`, numpy random without a seed, `hash(`, time or date,
`os.listdir` / `os.walk` / `glob` / `iterdir` order, and loops over a set.

Result: no finding of any severity. No branch adds `import random`, numpy random, time or date,
or a file-system listing. Every new set is used only to ask "is it in there", never looped over.

| Branch | Line in added diff | What | Severity | Fix |
|---|---|---|---|---|
| 47.1-48.1 | +337, +362, +367 | `gone = set()` of `id(o)`, only `not in gone` to filter a list (list keeps its own order) | none | - |
| 47.2-round-c | +41, +50, +53, +65 | `alt_lost` set on the job, only `near not in lost` and `lost.add` | none | - |
| canon-60, rivers-59, rivers-60, fix-59, review-59 | +705 / +498 / +649 / +571 / +543 | `seen` set, only `not in seen` in an assert | none | - |
| fix-81, fix-81b, lore-81, review-81 | +64 to +172 | `self.lights` set, only `d.id in facts.lights` | none | - |
| fix-94, review-94, styles-94 | +6 | `_style_hash(name)`: an old function in citygen/buildkey.py:37, sha256 of sorted JSON, stable | none | - |
| all other 46 branches | - | no hit | none | - |

Left: I did not read diffs of other file types (json, glsl, sh); the grep patterns can miss a loop
over a set returned by a function (for example `for x in some_func()` that returns a set).
