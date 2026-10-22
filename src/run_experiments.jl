# =====================================================================
# Step 6 và Step 9: chạy thí nghiệm trên SetA và ghi kết quả ra CSV.
#
# Cách gọi (chạy từ bất kỳ thư mục nào):
#   julia --project=<thư mục project> src/run_experiments.jl 6 1 2 3   # Step 6 cho setA-01, 02, 03
#   julia --project=<thư mục project> src/run_experiments.jl 9 all     # Step 9 cho cả 20 instance
#
# Step 6: chỉ t = 0, time limit 1800 s.   Step 9: t = 0 và t = 1, time limit 3600 s.
#
# Quy tắc số lần chạy: mỗi instance chạy 1 lần. Nếu giải tối ưu nhanh (< FAST giây)
# thì chạy thêm, mỗi lần một random seed khác, tối đa MAX_RUNS lần, rồi lấy trung bình.
#
# Cấu hình bằng biến môi trường (không bắt buộc, mặc định trong ngoặc):
#   MAX_VARS     (5000000) quá số biến này thì không dựng mô hình (tránh hết RAM)
#   FAST         (300)     ngưỡng "giải nhanh" (giây) để chạy lặp nhiều seed
#   MAX_RUNS     (10)      số lần chạy tối đa cho một instance
#   HEURISTIC    (0.3)     tham số mip_heuristic_effort của HiGHS
#   TIME_LIMIT   (1800 cho Step 6, 3600 cho Step 9) giới hạn thời gian mỗi lần chạy
#   RESULTS_DIR  (results) thư mục ghi CSV, tính từ thư mục project
#   FORCE        (0)       1 = chạy lại cả instance đã có trong CSV
#   NO_LOOPS     (0)       1 = thêm ràng buộc "mỗi đường đi qua mỗi nút tối đa một lần".
#                          Step 6: không làm đổi nghiệm tối ưu, nhanh hơn rất nhiều (setA-02: 364 s -> 5 s).
#                          Step 9: là phiên bản hạn chế (có thể mất nghiệm tối ưu), xem src/model.jl.
#
# Instance đã có dòng trong CSV sẽ được bỏ qua (trừ khi FORCE=1), nên nếu máy bị
# tắt giữa chừng thì chỉ cần gọi lại đúng lệnh cũ để chạy tiếp.
# =====================================================================
using Statistics, Printf
include("data.jl")
include("model.jl")

const ROOT = dirname(@__DIR__)                       # thư mục project (chứa src/, setA/)
env(name, default) = haskey(ENV, name) ? parse(typeof(default), ENV[name]) : default

const MAX_VARS  = env("MAX_VARS", 5_000_000)
const FAST      = env("FAST", 300.0)
const MAX_RUNS  = env("MAX_RUNS", 10)
const HEURISTIC = env("HEURISTIC", 0.3)
const FORCE     = env("FORCE", 0) == 1
const NO_LOOPS  = env("NO_LOOPS", 0) == 1

# MLU khi mọi demand đi thẳng s -> t (không waypoint): mốc để so sánh
function mlu_no_waypoint(inst::Instance, r::SplitCoef, t::Int)
    load = zeros(inst.m)
    for d in eachindex(inst.src), (a, ratio) in r[(inst.src[d], inst.dst[d])]
        load[a] += ratio * inst.vol[d, t+1]
    end
    return maximum(load ./ inst.cap)
end

function main(args)
    if length(args) < 2 || !(args[1] in ("6", "9"))
        println("Cách dùng: julia --project=. src/run_experiments.jl <6|9> <danh sách instance | all>")
        exit(1)
    end
    step = parse(Int, args[1])
    ids = args[2] == "all" ? collect(1:20) : parse.(Int, args[2:end])
    tlim = env("TIME_LIMIT", step == 6 ? 1800.0 : 3600.0)

    outdir = joinpath(ROOT, get(ENV, "RESULTS_DIR", "results"))
    mkpath(outdir)
    csv = joinpath(outdir, "step$(step).csv")
    isfile(csv) || write(csv, "instance,n,m,D,nvars,mlu_nowp,runs,status,obj,lb,gap,cpu_mean,cpu_std,nodes_mean,build_s\n")
    done = Set(first(split(l, ",")) for l in readlines(csv)[2:end] if !isempty(l))

    println("Step $step | time limit $(tlim) s | MAX_VARS $(MAX_VARS) | FAST $(FAST) s | MAX_RUNS $(MAX_RUNS) | NO_LOOPS $(NO_LOOPS) | ghi vào $csv")
    for k in ids
        name = @sprintf("setA-%02d", k)
        if name in done && !FORCE
            println("$name: đã có trong $csv => bỏ qua (đặt FORCE=1 để chạy lại)")
            continue
        end
        inst = read_instance(joinpath(ROOT, "setA", name))
        D = length(inst.src)
        rs = step == 6 ? [r_ecmp(inst, 0)] : [r_ecmp(inst, 0), r_ecmp(inst, 1)]
        nowp = maximum(mlu_no_waypoint(inst, rs[t+1], t) for t in 0:length(rs)-1)
        # số biến: x cho mỗi chu kỳ, cộng biến y của budget (Step 9)
        nvars = D * sum(length, rs) + (step == 9 ? D * length(union(keys(rs[1]), keys(rs[2]))) : 0)
        if nvars > MAX_VARS
            println("$name: $nvars biến > MAX_VARS => không dựng mô hình. MLU không waypoint = $nowp")
            open(csv, "a") do io
                @printf(io, "%s,%d,%d,%d,%d,%.6f,0,Too large,,,,,,,\n", name, inst.n, inst.m, D, nvars, nowp)
            end
            continue
        end
        # Ghi trước thông tin instance vào file .pending. Nếu tiến trình bị dừng cưỡng bức
        # (scripts/run.sh dùng lệnh timeout), script sẽ dùng file này để ghi dòng "Killed" vào CSV.
        pending = joinpath(outdir, "step$(step).pending")
        write(pending, @sprintf("%s,%d,%d,%d,%d,%.6f", name, inst.n, inst.m, D, nvars, nowp))
        results = []
        build_s = 0.0
        for seed in 0:MAX_RUNS-1
            GC.gc()
            tb = @elapsed (model, x, S) = build_model(inst, rs; time_limit = tlim, seed = seed,
                                                       heuristic_effort = HEURISTIC, no_loops = NO_LOOPS)
            build_s = tb
            res = solve_and_report(model)
            push!(results, res)
            println("$name seed=$seed: ", res, "  (dựng mô hình $(round(tb, digits = 1)) s)")
            flush(stdout)
            model = nothing; x = nothing; GC.gc()
            (res.status == "Optimal" && res.cpu < FAST) || break
        end
        cpus = [r.cpu for r in results]
        open(csv, "a") do io
            @printf(io, "%s,%d,%d,%d,%d,%.6f,%d,%s,%.6f,%.6f,%.6f,%.2f,%.2f,%.1f,%.1f\n",
                name, inst.n, inst.m, D, nvars, nowp, length(results), results[1].status,
                mean(r.obj for r in results), mean(r.lb for r in results), mean(r.gap for r in results),
                mean(cpus), length(cpus) > 1 ? std(cpus) : 0.0,
                mean(r.nodes for r in results), build_s)
        end
        rm(pending; force = true)
    end
end

main(ARGS)
