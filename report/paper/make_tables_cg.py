"""Generate the LaTeX rows of the method-2 tables of report/paper/paper.tex from the raw CSV files.

    python3 report/paper/make_tables_cg.py

Inputs : results/runs/seed*/cg/cg_step{6,9}.csv   (10 runs per instance; last row kept if an instance was re-run)
         results/reference/sprint_best_mlu.csv    (best MLU of the sprint phase of the challenge)
Outputs: report/paper/table_cg.tex (Table VI), report/paper/cg_facts.txt
The comparison with method 1 on the same machine is in the text of the paper (Section VII-F), from Tables III, IV and VI.
"""
import csv, glob, os, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "report", "paper")
best = {r["instance"]: float(r["best_mlu"]) for r in csv.DictReader(open(os.path.join(ROOT, "results/reference/sprint_best_mlu.csv")))}
OPT = 1e-4          # same relative gap as the default mip_rel_gap of HiGHS (method 1)

def cg_runs(step):
    data = {}
    for f in sorted(glob.glob(os.path.join(ROOT, f"results/runs/seed*/cg/cg_step{step}.csv"))):
        last = {}
        for r in csv.DictReader(open(f)):
            last[r["instance"]] = r
        for i, r in last.items():
            data.setdefault(i, []).append(r)
    return data

def summary(rs):
    ub = [float(r["ub"]) for r in rs]
    gap = [float(r["gap"]) for r in rs]
    k = sum(g <= OPT for g in gap)
    status = "Opt." if k == len(rs) else ("Not Opt." if k == 0 else f"Opt. {k}/{len(rs)}")
    # Same convention as Tables III/IV of method 1: Obj = best value over the runs;
    # CPU, Gap and Nodes = averages over the runs, with Gap 0 for an optimal run.
    return dict(obj=min(ub), mean=st.mean(ub), sd=st.stdev(ub) if len(ub) > 1 else 0.0, worst=max(ub),
                lb=max(float(r["lb"]) for r in rs), cpu=st.mean(float(r["cpu_s"]) for r in rs), status=status, k=k, n=len(rs),
                gap=st.mean(0.0 if g <= OPT else g for g in gap), nodes=st.mean(float(r["nodes"]) for r in rs))

def fgap(s):
    if s["k"] == s["n"]:
        return "0"
    g = 100 * s["gap"]
    return (f"{g:.3f}" if g < 0.1 else f"{g:.2f}") + "\\%"

def fcpu(x):
    return f"{x:.1f}" if x < 100 else f"{x:.0f}"

d6, d9 = cg_runs(6), cg_runs(9)
rows, facts = [], []
for inst in sorted(set(d6) | set(d9)):
    a, b = summary(d6[inst]), summary(d9[inst])
    match = sum(abs(float(r["ub"]) - best[inst]) <= 1.5e-6 for r in d9[inst])
    rows.append(" & ".join([inst[5:],
        f"{a['obj']:.4f}", f"{a['lb']:.4f}", fcpu(a["cpu"]), a["status"], fgap(a), f"{a['nodes']:.0f}",
        f"{b['obj']:.4f}", f"{b['lb']:.4f}", fcpu(b["cpu"]), b["status"], fgap(b), f"{b['nodes']:.0f}",
        f"{best[inst]:.4f}"]) + r" \\")
    facts.append(f"{inst} s6 obj {a['obj']:.6f} worst {a['worst']:.6f} sd {a['sd']:.2e} lb {a['lb']:.6f} gap {a['gap']:.5f} {a['status']} cpu {a['cpu']:.1f} | "
                 f"s9 obj {b['obj']:.6f} worst {b['worst']:.6f} sd {b['sd']:.2e} lb {b['lb']:.6f} gap {b['gap']:.5f} {b['status']} cpu {b['cpu']:.1f} "
                 f"| best {best[inst]:.6f} match {match}/{len(d9[inst])}")
open(os.path.join(OUT, "table_cg.tex"), "w").write("\n".join(rows) + "\n")

def agg(d):
    objs = [summary(v)["mean"] for v in d.values()]
    return st.mean(objs), st.median(objs)
facts.append(f"step6 mean/median {agg(d6)}; step9 mean/median {agg(d9)}")
open(os.path.join(OUT, "cg_facts.txt"), "w").write("\n".join(facts) + "\n")
print("\n".join(facts))
