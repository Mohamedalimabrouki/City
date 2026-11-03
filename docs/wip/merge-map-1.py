import subprocess, sys, itertools
R = sys.argv[3] if len(sys.argv) > 3 else "."
def g(*a, ok=(0,)):
    p = subprocess.run(["git", "-C", R, *a], capture_output=True, text=True)
    if p.returncode not in ok: raise SystemExit(f"git {a}: {p.stderr}")
    return p.returncode, p.stdout
MAIN = "claude/procedural-city-generator-xop72h"
_, mt = g("rev-parse", MAIN); mt = mt.strip()
_, refs = g("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/wip/")
brs = [r for r in refs.split() if r.startswith("origin/wip/")]
def mtree(a, b):
    rc, out = g("merge-tree", "--write-tree", "--name-only", a, b, ok=(0, 1))
    if rc == 0: return []
    lines = out.split("\n")[1:]
    files = []
    for l in lines:
        if not l.strip(): break
        files.append(l.strip())
    return sorted(set(files))
rows = {}
for b in brs:
    _, base = g("merge-base", MAIN, b); base = base.strip()
    _, sub = g("log", "-1", "--format=%h %s", base)
    _, ahead = g("rev-list", "--count", f"{MAIN}..{b}")
    _, behind = g("rev-list", "--count", f"{b}..{MAIN}")
    _, files = g("diff", "--name-only", base, b)
    files = files.split()
    code = [f for f in files if not f.startswith("docs/")]
    rows[b] = dict(base=sub.strip(), ahead=ahead.strip(), behind=behind.strip(), files=files, code=code, cm=mtree(MAIN, b))
codebr = [b for b in brs if rows[b]["code"]]
pair = {b: {} for b in brs}
for a, b in itertools.combinations(codebr, 2):
    if not set(rows[a]["code"]) & set(rows[b]["code"]):
        continue
    c = mtree(a, b)
    if c:
        pair[a][b] = c; pair[b][a] = c
def short(b): return b.replace("origin/wip/", "")
def flist(fs, n=6):
    s = ", ".join(f"`{f}`" for f in fs[:n])
    return s + (f" +{len(fs)-n} more" if len(fs) > n else "")
out = []
out.append(f"| branch | based on (main at) | +ahead/-behind main | files touched | conflicts with main | conflicts with others |")
out.append("|---|---|---|---|---|---|")
for b in brs:
    r = rows[b]
    cm = flist(r["cm"]) if r["cm"] else "clean"
    po = "; ".join(f"{short(o)}: {flist(c, 3)}" for o, c in sorted(pair[b].items())) or "none"
    if not r["code"]: po = "docs only (not checked)"
    out.append(f"| {short(b)} | {r['base']} | +{r['ahead']}/-{r['behind']} | {len(r['files'])}: {flist(r['files'])} | {cm} | {po} |")
print("\n".join(out))
import json
json.dump({short(b): dict(rows[b], pair={short(o): c for o, c in pair[b].items()}) for b in brs}, open(sys.argv[1], "w"), indent=1)
