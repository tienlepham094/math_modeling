"""Kiểm tra độc lập các nghiệm srpaths.json (chỉ dùng Python chuẩn, không dùng code Julia):
tự tính lại ECMP từ file JSON, rồi kiểm tra maxSeg, link bị tắt, budget và in MLU.

    python3 src/verify_srpaths.py 9                                # kiểm tra results/runs/seed0/cg/setA-XX-step9-srpaths.json
    python3 src/verify_srpaths.py 6 results/runs/seed3/cg          # phương pháp 2, Step 6, seed 3
    python3 src/verify_srpaths.py 9 results/m1sync/main/seed0      # phương pháp 1, Step 9, seed 0
    python3 src/verify_srpaths.py 9 results/runs/seed0/cg results/reference/sprint_best_mlu.csv   # in kèm MLU tốt nhất của sprint

Một cặp (d, t) không có trong file được hiểu là đi thẳng không waypoint (quy ước của định dạng srpaths).
Thoát với mã khác 0 nếu một nghiệm sai, hoặc nếu thư mục không có file nghiệm nào.
"""
import json, heapq, sys, os, collections
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
step = int(sys.argv[1])
sol_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "results", "runs", "seed0", "cg")
best = {}
if len(sys.argv) > 3:
    for line in open(sys.argv[3]).read().splitlines()[1:]:
        p = line.split(","); best[p[0]] = float(p[2])
def check(name):
    net = json.load(open(f"{root}/setA/{name}-net.json")); tm = json.load(open(f"{root}/setA/{name}-tm.json"))
    sc = json.load(open(f"{root}/setA/{name}-scenario.json"))
    sol = json.load(open(f"{sol_dir}/{name}-step{step}-srpaths.json"))["srpaths"]
    links = net["links"]; dem = tm["demands"]; K = sc["max_segments"]
    down = collections.defaultdict(set)
    for iv in sc["interventions"]: down[iv["t"]] |= set(iv["links"])
    T = [0] if step == 6 else [0, 1]
    paths = {}
    for it in sol:
        assert (it["d"], it["t"]) not in paths, f"cặp (d={it['d']}, t={it['t']}) xuất hiện hai lần"
        p = [dem[it["d"]]["s"]] + it["w"] + [dem[it["d"]]["t"]]
        assert len(set(zip(p, p[1:]))) == len(p) - 1, f"d={it['d']} t={it['t']}: một segment bị dùng hai lần"
        paths[(it["d"], it["t"])] = p
    mlu = []
    for t in T:
        alive = [l for l in links if l["id"] not in down[t]]
        rin = collections.defaultdict(list); out = collections.defaultdict(list)
        for l in alive: rin[l["to"]].append(l); out[l["from"]].append(l)
        distcache = {}
        def dist_to(j):
            if j in distcache: return distcache[j]
            d = {j: 0.0}; pq = [(0.0, j)]
            while pq:
                du, u = heapq.heappop(pq)
                if du > d.get(u, 1e300): continue
                for l in rin[u]:
                    nd = du + l["metric"]
                    if nd < d.get(l["from"], 1e300): d[l["from"]] = nd; heapq.heappush(pq, (nd, l["from"]))
            distcache[j] = d; return d
        load = collections.defaultdict(float)
        segc = {}
        def seg(u, v):
            if (u, v) in segc: return segc[(u, v)]
            d = dist_to(v); assert u in d, f"không có đường {u}->{v}"
            flow = collections.defaultdict(float); flow[u] = 1.0; ratio = collections.defaultdict(float)
            for x in sorted(d, key=lambda x: -d[x]):
                if x == v or flow[x] == 0: continue
                nh = [l for l in out[x] if l["to"] in d and abs(d[x] - (l["metric"] + d[l["to"]])) <= 1e-9 * max(1.0, d[x])]
                assert nh, f"nút {x} không có cung ra trên đường ngắn nhất tới {v}"
                for l in nh:
                    ratio[l["id"]] += flow[x] / len(nh); flow[l["to"]] += flow[x] / len(nh)
            # bảo toàn luồng: đúng 1 đơn vị tới đích (bắt được lỗi so sánh số thực bằng == trước đây)
            assert abs(flow[v] - 1.0) <= 1e-9, f"segment {u}->{v}: chỉ {flow[v]} đơn vị tới đích"
            segc[(u, v)] = ratio; return ratio
        for di, dd in enumerate(dem):
            p = paths.get((di, t), [dd["s"], dd["t"]])
            assert len(p) - 1 <= K, "quá maxSeg"
            for a, b in zip(p, p[1:]):
                for lid, r in seg(a, b).items(): load[lid] += r * dd["v"][t]
        cap = {l["id"]: l["capacity"] for l in alive}
        assert all(lid in cap for lid in load), "tải trên link bị tắt"
        mlu.append(max(load[lid] / cap[lid] for lid in cap))
    used = 0
    if step == 9:
        for di, dd in enumerate(dem):
            p0 = paths.get((di, 0), [dd["s"], dd["t"]]); p1 = paths.get((di, 1), [dd["s"], dd["t"]])
            s0 = set(zip(p0, p0[1:])); s1 = set(zip(p1, p1[1:]))
            used += len(s0 ^ s1)
        assert used <= sc["budget"][0]["value"], f"vượt budget {used}"
    U = max(mlu)
    b = best.get(name) if step == 9 else None
    print(f"{name} step{step}: MLU {U:.6f} {'(best ' + format(b, '.6f') + ')' if b else ''} budget {used}/{sc['budget'][0]['value'] if step == 9 else 0} OK")
checked = 0
for k in range(1, 21):
    name = f"setA-{k:02d}"
    if os.path.exists(f"{sol_dir}/{name}-step{step}-srpaths.json"):
        check(name); checked += 1
if checked == 0:
    sys.exit(f"Không tìm thấy file setA-XX-step{step}-srpaths.json nào trong {sol_dir}")
print(f"{checked} nghiệm đạt")
