import subprocess, json, sys, itertools
R = sys.argv[3] if len(sys.argv) > 3 else "."
def g(*a, ok=(0,)):
    p = subprocess.run(["git", "-C", R, *a], capture_output=True, text=True)
    if p.returncode not in ok: raise SystemExit(f"git {a}: {p.stderr}")
    return p.returncode, p.stdout
MAIN = "claude/procedural-city-generator-xop72h"
d = json.load(open(sys.argv[1]))
B = lambda s: "origin/wip/" + s
def mtree(a, b):
    rc, out = g("merge-tree", "--write-tree", "--name-only", a, b, ok=(0, 1))
    tree = out.split("\n")[0].strip()
    files = []
    for l in out.split("\n")[1:]:
        if not l.strip(): break
        files.append(l.strip())
    return tree, sorted(set(files))
# containment
names = sorted(d)
contains = {n: [] for n in names}
for a, b in itertools.permutations(names, 2):
    rc, _ = g("merge-base", "--is-ancestor", B(a), B(b), ok=(0, 1))
    if rc == 0: contains[b].append(a)
clean = [n for n in names if d[n]["code"] and not d[n]["cm"]]
mc = {}
for a in clean:
    tree, _ = mtree(MAIN, B(a))
    _, c = g("commit-tree", tree, "-p", MAIN, "-p", B(a), "-m", f"tmp main+{a}")
    mc[a] = c.strip()
pair = {n: {} for n in names}
for a, b in itertools.permutations(clean, 2):
    if a in contains[b] or b in contains[a]: continue
    if not set(d[a]["code"]) & set(d[b]["code"]): continue
    _, c = mtree(mc[a], B(b))
    if c: pair[a][b] = c
json.dump(dict(contains=contains, pair=pair, clean=clean), open(sys.argv[2], "w"), indent=1)
for n in names:
    print(n, "| contains:", ",".join(contains[n]) or "-", "| on main+X conflicts:", "; ".join(f"{o}: {','.join(c)}" for o, c in sorted(pair[n].items())) or "-")
