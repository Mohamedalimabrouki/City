import json, sys
d = json.load(open(sys.argv[1])); e = json.load(open(sys.argv[2]))
def fl(fs, n=5):
    s = ", ".join(f"`{f.replace('citygen/', '')}`" for f in fs[:n])
    return s + (f" +{len(fs)-n}" if len(fs) > n else "")
L = ["| branch | based on (main at) | +ahead/-behind | contains | files touched | conflicts with main | conflicts with others (on top of main + that branch) |", "|---|---|---|---|---|---|---|"]
for n in sorted(d):
    r = d[n]
    cm = fl(r["cm"]) if r["cm"] else "clean"
    if not r["code"]: po = "docs only"
    elif r["cm"]: po = "not checked: rebase on main first"
    else:
        # drop partners that are lower parts of a stack already listed through the top branch
        po = "; ".join(f"{o}: {fl(c, 3)}" for o, c in sorted(e["pair"][n].items())) or "none"
    L.append(f"| {n} | {r['base'][:7]} | +{r['ahead']}/-{r['behind']} | {', '.join(e['contains'][n]) or '-'} | {len(r['files'])}: {fl(r['files'])} | {cm} | {po} |")
print("\n".join(L))
