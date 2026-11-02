"""Generate the method-1 tables of report/paper/paper.tex (Tables III, IV and V) from the raw CSV files of machine B.

    python3 report/paper/make_tables_m1.py [thư mục lượt chạy trong results/, mặc định m1opt]
    python3 report/paper/make_tables_m1.py m1opt      # lượt ngày 29/10, có thời gian của cả lệnh optimize!

Sources (all machine B unless stated):
  results/<RUN>/main/seed*/step{6,9}.csv, checks_step*.csv, memory_step*.csv   one process per run (RUN = m1sync: 2026-10-28;
                                                                                m1opt: 2026-10-29, with column opt_mean)
  results/<RUN>/noloop/seed*/step6.csv                                          no-loop restriction (Table V)
  results/<RUN>/period1/seed0/step9.csv                                         period 1 alone (discussion of Step 9)
CPU column: opt_mean (wall time of the whole optimize! call, the definition of the project) when the CSV has it, otherwise
cpu_mean (HiGHS solve_time). The * mark always uses cpu_mean: HiGHS itself exceeded its time limit.
  results/step9.csv          Step 9 setA-05, run of 2026-10-26 (stopped at 4500 s); fallback only if missing from RUN (not used with m1opt)
  results/m1b/step9.csv      Step 9 setA-06, run of 2026-10-26 (stopped at 5400 s); fallback only if missing from RUN (not used with m1opt)
  results/step6.csv, results/step9.csv   "Too large" rows: MLU without waypoints of the models that are not built
  results/reference/method1_machineA.csv  fallback for Step 9 setA-08/09 only if they are missing from RUN (not used since 2026-11-02)
Outputs: report/paper/table_m1_step6.tex, table_m1_step9.tex, table_noloop.tex, m1_facts.txt
"""
import csv, glob, os, sys, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = lambda *p: os.path.join(ROOT, "results", *p)
OUT = os.path.join(ROOT, "report", "paper")
TL = {6: 1800.0, 9: 3600.0}
RUN = sys.argv[1] if len(sys.argv) > 1 else "m1opt"

def rows(path):
    if not os.path.exists(path):
        return []
    lines = [l for l in open(path) if not l.startswith("#")]
    return list(csv.DictReader(lines))

def runs(sub, step):
    """instance -> list of rows, one per seed directory (one run per process; if an instance was re-run
    in the same directory, the last row counts)"""
    d = {}
    for f in sorted(glob.glob(R(RUN, sub, "seed*", f"step{step}.csv"))):
        last = {r["instance"]: r for r in rows(f)}
        for inst, r in last.items():
            d.setdefault(inst, []).append(r)
    return d

def info():
    """instance -> (n, m, D, nvars per step, MLU0 per step) from any CSV row"""
    inf = {}
    for step in (6, 9):
        srcs = [R("step%d.csv" % step), R("m1b", "step%d.csv" % step)] + \
               sorted(glob.glob(R(RUN, "main", "seed*", f"step{step}.csv")))
        for f in srcs:
            for r in rows(f):
                e = inf.setdefault(r["instance"], {})
                e.update(n=int(r["n"]), m=int(r["m"]), D=int(r["D"]))
                e[f"nvars{step}"] = int(r["nvars"]); e[f"mlu0_{step}"] = float(r["mlu_nowp"])
    return inf

def fcpu(x):
    return f"{x:.1f}" if x < 1000 else f"{x:.0f}"

def tcpu(r):
    """CPU of one run: wall time of the optimize! call when recorded (opt_mean), else HiGHS solve_time (cpu_mean)"""
    return float(r["opt_mean"]) if r.get("opt_mean") else float(r["cpu_mean"])

def summarize(rs, step):
    """Same convention as the authors' report: Obj = best value over the runs; CPU, Gap, Nodes = averages over the runs,
    Gap 0 for an optimal run; a run stopped by the hard stop has Obj = MLU of the starting solution, Gap 1 (trivial bound)."""
    killed = [r for r in rs if r["status"] == "Killed"]
    ok = [r for r in rs if r["status"] in ("Optimal", "Not Optimal")]
    k = sum(r["status"] == "Optimal" for r in rs)
    objs = [float(r["obj"]) for r in rs if r["obj"]]
    gaps = [0.0 if r["status"] == "Optimal" else (float(r["gap"]) if r["status"] == "Not Optimal" else 1.0) for r in rs]
    cpus = [tcpu(r) for r in ok]
    solves = [float(r["cpu_mean"]) for r in ok]
    nodes = [float(r["nodes_mean"]) for r in ok]
    over = any(float(r["cpu_mean"]) > 1.02 * TL[step] for r in ok)
    status = "Optimal" if k == len(rs) else ("Not Opt." if k == 0 else f"Opt. {k}/{len(rs)}")
    if killed and not ok:
        cpu = f"$>${int(float(killed[0]['cpu_mean']))}"
        status += "$^\\dagger$"
    else:
        cpu = fcpu(st.mean(cpus)) + ("$^*$" if over else "") + ("$^\\dagger$" if killed else "")
    gap = st.mean(gaps)
    return dict(obj=min(objs) if objs else float("nan"), cpu=cpu, status=status, gap="0" if gap == 0 else (f"{100*gap:.2f}\\%" if gap < 1 else "100\\%"),
                nodes=f"{st.mean(nodes):.1f}" if nodes else "--", runs=len(rs), k=k, n=len(rs), killed=len(killed),
                cpus=cpus, solves=solves, objs=objs)

inf = info()
facts = []
for step in (6, 9):
    main = runs("main", step)
    extra = {}
    if step == 9:
        for r in rows(R("step9.csv")):
            if r["instance"] == "setA-05" and r["status"] == "Killed":
                extra["setA-05"] = [r]
        for r in rows(R("m1b", "step9.csv")):
            if r["instance"] == "setA-06":
                extra["setA-06"] = [r]
    A = {r["instance"]: r for r in rows(R("reference", "method1_machineA.csv")) if r["step"] == str(step)}
    gbm = 3.7 if step == 6 else 3.2          # replaced in the text by the values measured on machine B
    tex = []
    for k in range(1, 21):
        inst = f"setA-{k:02d}"
        e = inf[inst]
        mlu0 = e.get(f"mlu0_{step}")
        from_extra = inst not in main and inst in extra
        rs = main.get(inst) or extra.get(inst)
        head = f"{k:02d} & {e['n']} & {e['m']} & {e['D']} & {mlu0:.4f}"
        if rs:
            s = summarize(rs, step)
            mark = "$^\\flat$" if from_extra else ""
            tex.append(f"{head} & {s['obj']:.4f} & {s['cpu']}{mark} & {s['status']} & {s['gap']} & {s['nodes']} & {s['runs']} \\\\")
            facts.append(f"step{step} {inst}: {s['status']} obj {s['obj']:.6f} objs {sorted(set(round(o,6) for o in s['objs']))} "
                         f"cpu {[round(c,1) for c in s['cpus']]} solve {[round(c,1) for c in s['solves']]} "
                         f"opt-solve {[round(c - d, 1) for c, d in zip(s['cpus'], s['solves'])]} killed {s['killed']} "
                         f"src {'extra' if from_extra else RUN}")
        elif step == 9 and inst in ("setA-08", "setA-09"):
            a = A[inst]
            tex.append(f"{head} & {float(a['obj']):.4f} & $>$4500$^A$ & Not Opt.$^\\dagger$ & 100\\% & -- & 1 \\\\")
            facts.append(f"step{step} {inst}: machine A (not run on B)")
        else:
            nv = e.get(f"nvars{step}")
            tex.append(f"{head} & {mlu0:.4f} & -- & Not Opt.$^\\S$ & 100\\% & -- & 0 \\\\")
            facts.append(f"step{step} {inst}: not built, nvars {nv:,}")
    open(os.path.join(OUT, f"table_m1_step{step}.tex"), "w").write("\n".join(tex) + "\n")

# Table V: no-loop restriction versus the original model (Step 6, 01-05)
main6, nl = runs("main", 6), runs("noloop", 6)
tex = []
for k in range(1, 6):
    inst = f"setA-{k:02d}"
    a, b = summarize(main6[inst], 6), summarize(nl[inst], 6)
    tex.append(f"{k:02d} & {a['obj']:.4f} & {a['cpu']} & {a['gap']} & {a['runs']} & {b['obj']:.4f} & {b['cpu']} & {b['gap']} & {b['runs']} \\\\")
    facts.append(f"noloop {inst}: orig {a['status']} obj {a['obj']:.6f} cpu mean {st.mean(a['cpus']) if a['cpus'] else 0:.1f} median {st.median(a['cpus']) if a['cpus'] else 0:.1f} | "
                 f"noloop {b['status']} obj {b['obj']:.6f} cpu mean {st.mean(b['cpus']) if b['cpus'] else 0:.1f} median {st.median(b['cpus']) if b['cpus'] else 0:.1f}")
open(os.path.join(OUT, "table_noloop.tex"), "w").write("\n".join(tex) + "\n")

# Period 1 alone
for r in rows(R(RUN, "period1", "seed0", "step9.csv")):
    facts.append(f"period1 {r['instance']}: {r['status']} obj {float(r['obj']):.6f} cpu {r['cpu_mean']}")

# Solution checks and memory
for step in (6, 9):
    ch = [r for f in sorted(glob.glob(R(RUN, "*", "seed*", f"checks_step{step}.csv"))) for r in rows(f)]
    mainch = [r for f in sorted(glob.glob(R(RUN, "main", "seed*", f"checks_step{step}.csv"))) for r in rows(f)]
    if ch:
        bad = [r for r in ch if r["valid"] != "true"]
        diff = max(abs(float(r["mlu_paths"]) - float(r["obj"])) for r in ch)
        facts.append(f"checks step{step}: {len(ch)} solutions (main {len(mainch)}), invalid {len(bad)}, max |mlu_paths-obj| {diff:.2e}, "
                     f"max cycle segments (main) {max(int(r['cycle_segments']) for r in mainch)}, "
                     f"with cycles (main) {sum(int(r['cycle_segments'])>0 for r in mainch)}/{len(mainch)}")
        if step == 9:
            for inst in sorted(set(r["instance"] for r in mainch)):
                ds = [int(r["dist"]) for r in mainch if r["instance"] == inst]
                facts.append(f"  dist {inst}: max {max(ds)} min {min(ds)} kappa {[r['kappa'] for r in mainch if r['instance']==inst][0]}")
    mem = [r for f in sorted(glob.glob(R(RUN, "main", "seed*", f"memory_step{step}.csv"))) for r in rows(f)]
    peak = {}
    for r in mem:
        peak[r["instance"]] = max(peak.get(r["instance"], 0), int(r["peak_bytes"]))
    for inst in sorted(peak, key=lambda i: -inf[i][f"nvars{step}"])[:4]:
        nv = inf[inst][f"nvars{step}"]
        facts.append(f"memory step{step} {inst}: peak {peak[inst]/1e9:.1f} GB, nvars {nv:,}, {peak[inst]/1e9/(nv/1e6):.2f} GB per million variables")

open(os.path.join(OUT, "m1_facts.txt"), "w").write("\n".join(facts) + "\n")
print("\n".join(facts))
