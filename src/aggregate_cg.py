"""Tổng hợp 10 lần chạy của phương pháp 2 (results/runs/seed*/cg/cg_step{6,9}.csv) theo đúng
yêu cầu của đề (readme.txt): mỗi instance báo cáo n, m, |D|, giá trị tốt nhất, CPU time, status,
gap, số nút branch-and-bound, lấy trung bình qua các lần chạy.

    python3 src/aggregate_cg.py                      # đọc results/runs, ghi results/cg/ và report/
    python3 src/aggregate_cg.py results/runs best.csv   # thêm cột so với MLU tốt nhất của challenge (Step 9)

Kết quả:
    results/cg/cg_step{6,9}_10runs.csv     bảng trung bình
    results/cg/cg_10runs.md                bảng Markdown
    report/table_cg_step{6,9}.tex          bảng LaTeX để \\input trong report.tex (cùng cột với bảng phương pháp 1)
    report/table_cg.tex                    bảng LaTeX gộp Step 6 và Step 9 (gọn, dùng trong report.tex)
"""
import csv, glob, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
runs_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "runs")
best = {}
if len(sys.argv) > 2:
    with open(sys.argv[2]) as f:
        rd = csv.reader(f); next(rd)
        for r in rd:
            best[r[0]] = float(r[2])

mean = statistics.mean
sd = lambda xs: statistics.stdev(xs) if len(xs) > 1 else 0.0
md = ["# Phương pháp 2: trung bình nhiều lần chạy\n"]
allrows = {}

for step in (6, 9):
    data = {}
    for f in sorted(glob.glob(os.path.join(runs_dir, "seed*", "cg", f"cg_step{step}.csv"))):
        with open(f) as fh:
            last = {}
            for r in csv.DictReader(fh):      # nếu một instance được chạy lại (FORCE=1), lấy dòng cuối
                last[r["instance"]] = r
        for inst, r in last.items():
            data.setdefault(inst, []).append(r)
    if not data:
        print(f"Step {step}: chưa có kết quả trong {runs_dir}")
        continue
    rows = []
    for inst in sorted(data):
        rs = data[inst]
        ub = [float(r["ub"]) for r in rs]; lb = [float(r["lb"]) for r in rs]
        gap = [float(r["gap"]) for r in rs]; cpu = [float(r["cpu_s"]) for r in rs]
        nodes = [float(r["nodes"]) for r in rs]
        # Status tính lại từ gap, ngưỡng 1e-4 như mip_rel_gap mặc định của HiGHS (phương pháp 1)
        n_opt = sum(float(r["gap"]) <= 1e-4 for r in rs)
        rows.append(dict(
            instance=inst, n=rs[0]["n"], m=rs[0]["m"], D=rs[0]["D"], kappa=rs[0]["kappa"], runs=len(rs),
            status="Optimal" if n_opt == len(rs) else ("Not Optimal" if n_opt == 0 else f"Optimal {n_opt}/{len(rs)}"),
            mlu_nowp=float(rs[0]["mlu_nowp"]), obj_mean=mean(ub), obj_best=min(ub), obj_sd=sd(ub),
            lb=max(lb), gap_mean=mean(gap), cpu_mean=mean(cpu), cpu_sd=sd(cpu), nodes_mean=mean(nodes),
            budget_used=rs[0]["budget_used"], best_known=best.get(inst, "") if step == 9 else ""))
    allrows[step] = {r["instance"]: r for r in rows}
    out = os.path.join(ROOT, "results", "cg", f"cg_step{step}_10runs.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # Markdown
    limit = 1800 if step == 6 else 3600
    md.append(f"## Step {step} (time limit {limit} s, {rows[0]['runs']} lần chạy mỗi instance)\n")
    cols = ["Inst", "n", "m", "\\|D\\|"] + (["κ"] if step == 9 else []) + \
           ["Giá trị tốt nhất (TB)", "Status", "Gap TB", "CPU TB ± độ lệch (s)", "Nút B&B TB"] + \
           (["Tốt nhất challenge"] if best and step == 9 else [])
    md.append("| " + " | ".join(cols) + " |"); md.append("|" + "---|" * len(cols))
    for r in rows:
        line = f"| {r['instance'][5:]} | {r['n']} | {r['m']} | {r['D']} |" + (f" {r['kappa']} |" if step == 9 else "")
        line += f" {r['obj_mean']:.6f} | {r['status']} | {100*r['gap_mean']:.2f}% | {r['cpu_mean']:.1f} ± {r['cpu_sd']:.1f} | {r['nodes_mean']:.1f} |"
        if best and step == 9:
            line += f" {r['best_known']:.6f} |"
        md.append(line)
    objs = [r["obj_mean"] for r in rows]
    md.append(f"\nMLU trung bình {mean(objs):.4f}, trung vị {statistics.median(objs):.4f}; "
              f"Optimal (gap ≤ 0.01%, đã chứng minh tối ưu) ở {sum(r['status'] == 'Optimal' for r in rows)}/{len(rows)} instance; "
              f"CPU lớn nhất {max(r['cpu_mean'] for r in rows):.0f} s (giới hạn {limit} s).\n")

    # LaTeX (cùng kiểu bảng với report/table_step*.tex: chỉ các dòng dữ liệu)
    tex = []
    for r in rows:
        st = {"Optimal": "Optimal", "Not Optimal": "Not Opt."}.get(r["status"], r["status"])
        gap = "0" if r["status"] == "Optimal" else f"{100*r['gap_mean']:.2f}\\%"
        tex.append(f"{r['instance'][5:]} & {r['n']} & {r['m']} & {r['D']} & {r['mlu_nowp']:.4f} & {r['obj_mean']:.4f} & "
                   f"{r['cpu_mean']:.1f} & {st} & {gap} & {r['nodes_mean']:.0f} & {r['runs']} \\\\")
    with open(os.path.join(ROOT, "report", f"table_cg_step{step}.tex"), "w") as fh:
        fh.write("\n".join(tex) + "\n")
    print(f"Step {step}: {len(rows)} instance -> {out}, report/table_cg_step{step}.tex")

# Bảng gộp: Inst | Step 6: Obj, CPU, Status, Gap, nút | Step 9: Obj, CPU, Status, Gap, nút, tốt nhất challenge
if 6 in allrows and 9 in allrows:
    def cells(r):
        st = "Opt." if r["status"] == "Optimal" else ("N.Opt." if r["status"] == "Not Optimal" else r["status"])
        gap = "0" if r["status"] == "Optimal" else f"{100*r['gap_mean']:.2f}\\%"
        return [f"{r['obj_mean']:.4f}", f"{r['cpu_mean']:.1f}", st, gap, f"{r['nodes_mean']:.0f}"]
    tex = []
    for inst in sorted(set(allrows[6]) | set(allrows[9])):
        a = cells(allrows[6][inst]) if inst in allrows[6] else ["--"] * 5
        b = cells(allrows[9][inst]) if inst in allrows[9] else ["--"] * 5
        bk = best.get(inst)
        tex.append(" & ".join([inst[5:]] + a + b + [f"{bk:.4f}" if bk is not None else "--"]) + " \\\\")
    with open(os.path.join(ROOT, "report", "table_cg.tex"), "w") as fh:
        fh.write("\n".join(tex) + "\n")
    print("Bảng gộp LaTeX: report/table_cg.tex")

with open(os.path.join(ROOT, "results", "cg", "cg_10runs.md"), "w") as fh:
    fh.write("\n".join(md) + "\n")
print("Bảng Markdown: results/cg/cg_10runs.md")
