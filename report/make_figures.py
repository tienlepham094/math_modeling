"""Figures for the Orange T-ASR deck, drawn from the real instance data."""
import json, heapq, sys, os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import networkx as nx

ROOT, OUT = sys.argv[1], sys.argv[2]
LANG = sys.argv[3] if len(sys.argv) > 3 else "en"  # "vi": Vietnamese chart labels
T = lambda en, vi: vi if LANG == "vi" else en
os.makedirs(OUT, exist_ok=True)
RED, INK, GRAY, LIGHT = "#2B6E8F", "#23272D", "#8A9099", "#CDD1D5"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "mathtext.fontset": "cm"})

def load(name, base):
    net = json.load(open(f"{base}/{name}-net.json"))
    tm = json.load(open(f"{base}/{name}-tm.json"))
    return net, tm

# ---------- ECMP flow ratios ----------
def dijkstra_to(arcs, n, j):
    """distance from every node to j"""
    rev = defaultdict(list)
    for (u, v), w in arcs.items():
        rev[v].append((u, w))
    d = [float("inf")] * n; d[j] = 0; pq = [(0, j)]
    while pq:
        du, u = heapq.heappop(pq)
        if du > d[u]: continue
        for x, w in rev[u]:
            if du + w < d[x]:
                d[x] = du + w; heapq.heappush(pq, (d[x], x))
    return d

def ecmp(arcs, n, i, j):
    d = dijkstra_to(arcs, n, j)
    out = defaultdict(list)
    for (u, v), w in arcs.items():
        if abs(d[u] - (w + d[v])) < 1e-9: out[u].append(v)
    flow = defaultdict(float); flow[i] = 1.0; r = {}
    for u in sorted(range(n), key=lambda x: -d[x]):
        if u == j or flow[u] == 0: continue
        k = len(out[u])
        for v in out[u]:
            r[(u, v)] = r.get((u, v), 0) + flow[u] / k
            flow[v] += flow[u] / k
    return r

def loads(arcs, cap, n, routes):
    """routes: list of (segment path, volume)"""
    L = defaultdict(float)
    for path, vol in routes:
        for a, b in zip(path, path[1:]):
            for arc, x in ecmp(arcs, n, a, b).items():
                L[arc] += x * vol
    return {a: L[a] / cap[a] for a in L}

# ---------- toy instance ----------
net, tm = load("toy", f"{ROOT}/toy")
n = len(net["nodes"])
arcs = {(l["from"], l["to"]): l["metric"] for l in net["links"]}
cap = {(l["from"], l["to"]): l["capacity"] for l in net["links"]}
dem = [(d["s"], d["t"], d["v"][0]) for d in tm["demands"]]
pos = {0: (0, 1), 1: (1, 1.8), 2: (1, 0.2), 4: (2, 1), 3: (2.6, 2.0), 6: (2.6, 0.0), 5: (3.5, 1.0)}
lab = {k: f"$v_{k}$" for k in range(n)}

def draw_toy(ax, util, highlight=True, title=None, waypoint=None, labels=None):
    und = {tuple(sorted(a)) for a in arcs}
    for u, v in und:
        x = [pos[u][0], pos[v][0]]; y = [pos[u][1], pos[v][1]]
        ax.plot(x, y, color=LIGHT, lw=1.2, zorder=1)
    umax = max(util.values()) if util else 0
    for (u, v), val in util.items():
        if val < 1e-9: continue
        hot = highlight and abs(val - umax) < 1e-9
        a = FancyArrowPatch(pos[u], pos[v], arrowstyle="-|>", mutation_scale=14, shrinkA=13, shrinkB=13,
                            color=RED if hot else INK, lw=1.2 + 4 * val, zorder=2)
        ax.add_patch(a)
        mx, my = (pos[u][0] + pos[v][0]) / 2, (pos[u][1] + pos[v][1]) / 2
        txt = labels[(u, v)] if labels else f"{val:.4g}"
        ax.text(mx, my + 0.12, txt, ha="center", fontsize=9.5, color=RED if hot else INK,
                bbox=dict(fc="white", ec="none", pad=0.6), zorder=4)
    for k, (x, y) in pos.items():
        fc = RED if k == waypoint else ("white")
        ax.scatter([x], [y], s=520, c=fc, edgecolors=INK, linewidths=1.2, zorder=3)
        ax.text(x, y, lab[k], ha="center", va="center", fontsize=12, color="white" if k == waypoint else INK, zorder=5)
    ax.set_xlim(-0.35, 3.85); ax.set_ylim(-0.35, 2.35); ax.axis("off")
    if title: ax.set_title(title, fontsize=12.5, color=INK, loc="left")

# before / after at t = 0
u0 = loads(arcs, cap, n, [([s, t], v) for s, t, v in dem])
u1 = loads(arcs, cap, n, [([0, 4, 5], dem[0][2]), ([2, 5], dem[1][2])])
print("toy MLU default", max(u0.values()), "with v4", max(u1.values()))
for nm, util, wp, ttl in [("toy_default", u0, None, "Shortest paths only"),
                          ("toy_sr", u1, 4, "Segment path $\\langle v_0, v_4, v_5\\rangle$")]:
    fig, ax = plt.subplots(figsize=(4.6, 3.0), dpi=220)
    draw_toy(ax, util, waypoint=wp)
    fig.tight_layout(pad=0.2); fig.savefig(f"{OUT}/{nm}.png", transparent=False, facecolor="white"); plt.close(fig)

# ECMP splitting for demand (v0, v5)
r = ecmp(arcs, n, 0, 5)
fig, ax = plt.subplots(figsize=(4.6, 3.0), dpi=220)
from fractions import Fraction
draw_toy(ax, {a: x for a, x in r.items()}, highlight=False, labels={a: f"{x:g}" for a, x in r.items()})
fig.tight_layout(pad=0.2); fig.savefig(f"{OUT}/toy_ecmp.png", facecolor="white"); plt.close(fig)
print("r(v0,v5)", r)

# ---------- a real SetA network ----------
net20, _ = load("setA-20", f"{ROOT}/setA")
G = nx.Graph()
G.add_edges_from((l["from"], l["to"]) for l in net20["links"])
p = nx.kamada_kawai_layout(G)
fig, ax = plt.subplots(figsize=(4.4, 4.0), dpi=200)
nx.draw_networkx_edges(G, p, ax=ax, edge_color=LIGHT, width=0.5)
nx.draw_networkx_nodes(G, p, ax=ax, node_size=7, node_color=RED, linewidths=0)
ax.axis("off"); fig.tight_layout(pad=0.1); fig.savefig(f"{OUT}/setA20.png", facecolor="white"); plt.close(fig)
print("setA-20", G.number_of_nodes(), G.number_of_edges())

# ---------- MILP model, LaTeX style ----------
eqs = [
    (r"$\min\quad U$", ""),
    (r"$\Sigma_{j} x^{dt}_{ij}\;-\;\Sigma_{j} x^{dt}_{ji}\;=\;[\,i=s_d\,]-[\,i=t_d\,]$", r"$\forall i,d,t$     (1)"),
    (r"$\Sigma_{i,j} x^{dt}_{ij}\;\leq\; maxSeg$", r"$\forall d,t$     (2)"),
    (r"$\Sigma_{d}\Sigma_{i,j} r(i,j,a,t)\,\nu(d,t)\,x^{dt}_{ij}\;\leq\;U\,c(a)$", r"$\forall t,\ a\notin q(t)$     (3)"),
    (r"$\Sigma_{d}\Sigma_{i\neq j} y^{dt}_{ij}\leq\kappa(t),\quad y^{dt}_{ij}\geq \pm\,(x^{dt}_{ij}-x^{d,t-1}_{ij})$", r"$\forall t\geq 1$     (4)"),
    (r"$x^{dt}_{ij}\in\{0,1\},\quad y^{dt}_{ij}\geq 0,\quad U\geq 0$", ""),
]
fig = plt.figure(figsize=(7.6, 3.4), dpi=220)
for k, (e, tag) in enumerate(eqs):
    y = 1 - (k + 0.5) / len(eqs)
    fig.text(0.02, y, e, fontsize=17, va="center", color=INK)
    fig.text(0.98, y, tag, fontsize=14, va="center", ha="right", color=GRAY)
fig.savefig(f"{OUT}/model.png", facecolor="white"); plt.close(fig)

# ---------- results charts ----------
def style(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRAY); ax.spines["bottom"].set_color(GRAY)
    ax.tick_params(colors=INK, labelsize=10.5)
    ax.yaxis.grid(True, color="#E6E8EB", lw=0.8); ax.set_axisbelow(True)

inst = ["01", "02", "03", "04", "05"]
mlu0 = [1.0, 1.0, 1.0, 0.6918, 0.3333]
obj = [0.9294, 0.5486, 0.9435, 0.6918, 0.1155]
fig, ax = plt.subplots(figsize=(5.4, 3.3), dpi=220)
xs = range(len(inst)); w = 0.38
ax.bar([x - w / 2 for x in xs], mlu0, w, color=LIGHT, label=T("shortest paths (no waypoint)", "đường ngắn nhất (không waypoint)"))
b = ax.bar([x + w / 2 for x in xs], obj, w, color=RED, label="MILP")
for x, v, o in zip(xs, mlu0, obj):
    ax.text(x + w / 2, o + 0.02, f"{o:.2f}", ha="center", fontsize=9.5, color=INK)
ax.text(3 + w / 2, 0.6918 + 0.07, T("not\noptimal", "chưa\ntối ưu"), ha="center", fontsize=8.5, color=GRAY)
ax.set_xticks(list(xs)); ax.set_xticklabels([f"setA-{i}" for i in inst])
ax.set_ylabel(T("MLU at t = 0", "MLU tại t = 0")); ax.set_ylim(0, 1.18)
ax.legend(frameon=False, fontsize=9.5, loc="upper right", ncol=2, bbox_to_anchor=(1, 1.08))
style(ax); fig.tight_layout(); fig.savefig(f"{OUT}/step6.png", facecolor="white"); plt.close(fig)

nv = [1.5e4, 3.9e4, 4.9e4, 4.9e5, 9.9e5, 4.95e6, 7.9e6, 4.5e6, 4.5e6, 2.2e7, 1.6e7, 1.6e7, 8.0e7, 3.7e7,
      3.7e7, 3.0e8, 1.8e8, 1.8e8, 5.4e8, 9.6e8]
col = [RED if i in (0, 1, 2, 4) else ("#9CC3D5" if i == 3 else (GRAY if i in (5, 7, 8) else LIGHT)) for i in range(20)]
fig, ax = plt.subplots(figsize=(6.4, 3.3), dpi=220)
ax.bar(range(20), nv, color=col, width=0.72)
ax.set_yscale("log"); ax.set_ylim(1e4, 2e9)
ax.axhline(5e6, color=INK, lw=1, ls="--")
ax.text(19.4, 6.2e6, T("cap: 5·10⁶ variables", "giới hạn: 5·10⁶ biến"), ha="right", va="bottom", fontsize=9.5, color=INK)
ax.set_xticks(range(20)); ax.set_xticklabels([f"{i:02d}" for i in range(1, 21)], fontsize=9)
ax.set_ylabel(T("binary variables (t = 0)", "số biến nhị phân (t = 0)")); ax.set_xlabel(T("SetA instance", "Instance SetA"))
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=RED, label=T("solved to optimality", "giải tối ưu")), Patch(color="#9CC3D5", label=T("built, not solved", "dựng được, chưa giải xong")),
                   Patch(color=GRAY, label=T("at the limit, no result", "sát giới hạn, chưa có kết quả")), Patch(color=LIGHT, label=T("too large to build", "quá lớn, không dựng"))],
          frameon=False, fontsize=9, loc="upper left")
style(ax); fig.tight_layout(); fig.savefig(f"{OUT}/scale.png", facecolor="white"); plt.close(fig)
print("figures done")
