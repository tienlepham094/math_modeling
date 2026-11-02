# =====================================================================
# Sinh bảng LaTeX cho báo cáo từ results/step6.csv và results/step9.csv
#   julia --project=. src/make_tables.jl
# Kết quả: report/table_step6.tex, report/table_step9.tex (được \input trong report.tex)
#
# Quy ước hiển thị:
#   Gap "--"  : solver không có cận dưới (LB = -Inf), thường vì chưa giải xong LP gốc
#   CPU có "*": CPU time vượt time limit (HiGHS không kiểm tra giới hạn trong một số giai đoạn)
#
# Bảng chỉ được ghi vào report/ khi đọc từ results/ (mặc định). Với RESULTS_DIR khác
# (ví dụ results/server), bảng được ghi cạnh file CSV, để không đè lên bảng của báo cáo.
# =====================================================================
using Printf

const ROOT = dirname(@__DIR__)
const LIMIT = Dict(6 => 1800.0, 9 => 3600.0)
const RES = get(ENV, "RESULTS_DIR", "results")
const OUTDIR = rstrip(normpath(RES), '/') == "results" ? joinpath(ROOT, "report") : joinpath(ROOT, RES)

function read_csv(file)
    lines = filter(!isempty, readlines(file))
    head = split(lines[1], ",")
    rows = [Dict(zip(head, split(l, ","))) for l in lines[2:end]]
    sort!(rows, by = r -> r["instance"])
end

num(x) = isempty(x) ? NaN : parse(Float64, x)
fmt(x, d) = isfinite(x) ? @sprintf("%.*f", d, x) : "--"

function table(step)
    file = joinpath(ROOT, RES, "step$(step).csv")
    if !isfile(file)
        println("Chưa có $file, bỏ qua bảng Step $step")
        return
    end
    io = IOBuffer()
    for r in read_csv(file)
        inst = replace(r["instance"], "setA-" => "")
        if r["status"] in ("Too large", "Out of memory")
            why = r["status"] == "Too large" ? "mô hình quá lớn" : "hết RAM khi giải"
            @printf(io, "%s & %s & %s & %s & %s & \\multicolumn{6}{c}{\\textit{%s (%.1f triệu biến)}} \\\\\n",
                inst, r["n"], r["m"], r["D"], fmt(num(r["mlu_nowp"]), 4), why, num(r["nvars"]) / 1e6)
            continue
        end
        st = get(Dict("Optimal" => "Optimal", "Not Optimal" => "Not Opt.", "Infeasible" => "Infeasible",
                      "Killed" => "Bị dừng"), r["status"], r["status"])
        gap = r["status"] == "Optimal" ? "0" :
              isfinite(num(r["gap"])) ? fmt(100 * num(r["gap"]), 2) * "\\%" : "--"
        cpu = num(r["cpu_mean"])
        cpu_s = r["status"] == "Killed" ? "\$>\$" * fmt(cpu, 0) :          # bị dừng bởi HARD_LIMIT
                fmt(cpu, 1) * (cpu > LIMIT[step] + 1 ? "\$^*\$" : "")
        @printf(io, "%s & %s & %s & %s & %s & %s & %s & %s & %s & %s & %s \\\\\n",
            inst, r["n"], r["m"], r["D"], fmt(num(r["mlu_nowp"]), 4), fmt(num(r["obj"]), 4),
            cpu_s, st, gap, fmt(num(r["nodes_mean"]), 0), r["runs"])
    end
    out = joinpath(OUTDIR, "table_step$(step).tex")
    write(out, String(take!(io)))
    println("Đã ghi $out")
end

table(6); table(9)
