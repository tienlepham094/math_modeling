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
#   HARD_LIMIT   (Inf)     do scripts/run.sh truyền vào; không chạy thêm seed nếu có thể vượt giới hạn này
#   SEED_START   (0)       seed của lần chạy đầu tiên (các lần sau tăng dần)
#   PERIOD1_ONLY (0)       1 = (với lệnh 9) chỉ giải chu kỳ 1: mạng G_1, lưu lượng ν(d,1), không budget
#
# Thời gian trong CSV:
#   opt_mean = thời gian thực của cả lệnh optimize! (CPU time theo định nghĩa của đề: gồm chép mô hình vào HiGHS và giải),
#              đo sau một lần giải "khởi động" trên toy trong cùng tiến trình, nên không gồm thời gian biên dịch của Julia;
#   cpu_mean = thời gian giải do HiGHS báo (solve_time), không gồm phần chép mô hình;
#   build_s  = thời gian dựng mô hình JuMP (trước optimize!).
#
# Sau mỗi lần chạy có nghiệm, nghiệm được kiểm tra (xem check_solution) và ghi vào checks_step<6|9>.csv;
# nghiệm được lưu ở <instance>-step<6|9>-srpaths.json (định dạng checker chính thức, d = thứ tự demand).
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
const HARD      = env("HARD_LIMIT", Inf)    # chốt chặn cứng của scripts/run.sh cho CẢ instance (mọi seed)
const SEED0     = env("SEED_START", 0)      # seed đầu tiên; SEED_START=k MAX_RUNS=1 = chỉ chạy seed k (mỗi seed một tiến trình)
const PERIOD1   = env("PERIOD1_ONLY", 0) == 1  # chỉ với Step 9: giải riêng chu kỳ 1 (G_1, ν(d,1), không budget)

# MLU khi mọi demand đi thẳng s -> t (không waypoint): mốc để so sánh
function mlu_no_waypoint(inst::Instance, r::SplitCoef, t::Int)
    load = zeros(inst.m)
    for d in eachindex(inst.src), (a, ratio) in r[(inst.src[d], inst.dst[d])]
        load[a] += ratio * inst.vol[d, t+1]
    end
    return maximum(load ./ inst.cap)
end

# Instance chỉ gồm chu kỳ 1: mạng G_1 (bỏ cung bị tắt tại t = 1) và lưu lượng ν(d,1), xem như "chu kỳ 0" của mô hình một chu kỳ
function period1_instance(inst::Instance)
    Instance(inst.name, inst.n, inst.m, inst.from, inst.to, inst.metric, inst.cap, inst.link_id, inst.node_id,
             inst.src, inst.dst, inst.vol[:, 2:2], inst.maxSeg, inst.budget, Dict(0 => get(inst.down, 1, Int[])))
end

# Đọc path của mọi demand tại chu kỳ t từ giá trị x (ma trận D × |S_t|) bằng đường đi Euler (Hierholzer) từ nguồn.
# Segment còn lại sau khi đi hết đường từ nguồn thuộc các chu trình rời; trả về tổng số segment đó.
function recover_paths(inst::Instance, xv::AbstractMatrix, S, t::Int)
    D = length(inst.src)
    paths = Vector{Vector{Int}}(undef, D)
    left = 0
    for d in 1:D
        succ = Dict{Int,Vector{Int}}()
        for (p, (i, j)) in enumerate(S[t+1])
            xv[d, p] > 0.5 && push!(get!(succ, i, Int[]), j)
        end
        stack, walk = [inst.src[d]], Int[]
        while !isempty(stack)
            u = stack[end]
            if !isempty(get(succ, u, Int[]))
                push!(stack, pop!(succ[u]))
            else
                push!(walk, pop!(stack))
            end
        end
        paths[d] = reverse!(walk)
        left += sum(length, values(succ); init = 0)
    end
    return paths, left
end

# Kiểm tra nghiệm của một lần chạy (độc lập với giá trị mục tiêu solver trả về):
# path đi từ nguồn tới đích, ≤ maxSeg segment, mọi segment có đường đi ở chu kỳ đó, không tải trên cung bị tắt,
# MLU tính lại từ path (đã bỏ chu trình rời), và dist thật giữa hai chu kỳ (hiệu đối xứng tập segment) ≤ κ.
# Ghi một dòng vào checks_step<step>.csv và, trừ khi PERIOD1_ONLY, lưu nghiệm theo định dạng checker chính thức.
function check_solution(inst::Instance, rs, model, x, S, outdir, step, name, seed, res)
    T = 0:length(rs)-1
    D = length(inst.src)
    paths = Vector{Vector{Vector{Int}}}()
    cycles = 0
    for t in T
        xv = reshape(MOI.get(backend(model), MOI.VariablePrimal(), index.(vec(x[t+1]))), size(x[t+1]))
        P, left = recover_paths(inst, xv, S, t)
        push!(paths, P)
        cycles += left
    end
    ok = true
    maxseg = 0
    mlus = Float64[]
    for t in T
        load = zeros(inst.m)
        for d in 1:D
            p = paths[t+1][d]
            ok &= first(p) == inst.src[d] && last(p) == inst.dst[d]
            maxseg = max(maxseg, length(p) - 1)
            for k in 1:length(p)-1
                seg = (p[k], p[k+1])
                if !haskey(rs[t+1], seg)
                    ok = false
                    continue
                end
                for (a, ratio) in rs[t+1][seg]
                    load[a] += ratio * inst.vol[d, t+1]
                end
            end
        end
        down = get(inst.down, t, Int[])
        ok &= all(load[a] == 0 for a in down)
        push!(mlus, maximum(load[a] / inst.cap[a] for a in alive_arcs(inst, t)))
    end
    ok &= maxseg <= inst.maxSeg
    dist, kappa = -1, -1
    if length(T) == 2
        segs(p) = Set(zip(p[1:end-1], p[2:end]))
        dist = sum(length(symdiff(segs(paths[1][d]), segs(paths[2][d]))) for d in 1:D)
        kappa = inst.budget[1]
        ok &= dist <= kappa
    end
    mlu = maximum(mlus)
    csv = joinpath(outdir, "checks_step$(step).csv")
    isfile(csv) || write(csv, "instance,seed,status,obj,mlu_paths,mlu_t0,mlu_t1,cycle_segments,max_segments,dist,kappa,valid\n")
    open(csv, "a") do io
        @printf(io, "%s,%d,%s,%.6f,%.6f,%.6f,%s,%d,%d,%d,%d,%s\n", name, seed, res.status, res.obj, mlu, mlus[1],
                length(mlus) == 2 ? @sprintf("%.6f", mlus[2]) : "", cycles, maxseg, dist, kappa, ok)
    end
    if !PERIOD1
        open(joinpath(outdir, "$(name)-step$(step)-srpaths.json"), "w") do io
            items = String[]
            for t in T, d in 1:D
                w = inst.node_id[paths[t+1][d][2:end-1]]
                push!(items, "{\"d\":$(d-1),\"t\":$t,\"w\":[$(join(w, ","))]}")
            end
            print(io, "{\"srpaths\":[\n", join(items, ",\n"), "\n]}\n")
        end
    end
    return (mlu = mlu, cycles = cycles, dist = dist, kappa = kappa, maxseg = maxseg, ok = ok)
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
    isfile(csv) || write(csv, "instance,n,m,D,nvars,mlu_nowp,runs,status,obj,lb,gap,cpu_mean,cpu_std,nodes_mean,build_s,opt_mean\n")
    done = Set(first(split(l, ",")) for l in readlines(csv)[2:end] if !isempty(l))

    println("Step $step | time limit $(tlim) s | MAX_VARS $(MAX_VARS) | FAST $(FAST) s | MAX_RUNS $(MAX_RUNS) | NO_LOOPS $(NO_LOOPS) | ghi vào $csv")

    # Khởi động (warm-up): dựng và giải toy một lần trong cùng tiến trình, cùng loại mô hình (một hay hai chu kỳ,
    # cùng NO_LOOPS), để Julia biên dịch sẵn các hàm dựng, chép và giải mô hình. Nhờ vậy thời gian optimize! đo ở dưới
    # chỉ gồm việc chép mô hình vào HiGHS và giải, không gồm thời gian biên dịch (vài giây tới vài chục giây).
    tw = @elapsed let toy = read_instance(joinpath(ROOT, "toy", "toy"))
        rw = (step == 6 || PERIOD1) ? [r_ecmp(toy, 0)] : [r_ecmp(toy, 0), r_ecmp(toy, 1)]
        mw, _, _ = build_model(toy, rw; time_limit = 60.0, seed = 0, heuristic_effort = HEURISTIC, no_loops = NO_LOOPS)
        solve_and_report(mw)
    end
    println("khởi động trên toy: $(round(tw, digits = 1)) s")
    for k in ids
        name = @sprintf("setA-%02d", k)
        if name in done && !FORCE
            println("$name: đã có trong $csv => bỏ qua (đặt FORCE=1 để chạy lại)")
            continue
        end
        inst = read_instance(joinpath(ROOT, "setA", name))
        PERIOD1 && step == 9 && (inst = period1_instance(inst))
        D = length(inst.src)
        rs = (step == 6 || PERIOD1) ? [r_ecmp(inst, 0)] : [r_ecmp(inst, 0), r_ecmp(inst, 1)]
        nowp = maximum(mlu_no_waypoint(inst, rs[t+1], t) for t in 0:length(rs)-1)
        # số biến: x cho mỗi chu kỳ, cộng biến y của budget (Step 9 hai chu kỳ)
        nvars = D * sum(length, rs) + (length(rs) == 2 ? D * length(union(keys(rs[1]), keys(rs[2]))) : 0)
        if nvars > MAX_VARS
            println("$name: $nvars biến > MAX_VARS => không dựng mô hình. MLU không waypoint = $nowp")
            open(csv, "a") do io
                @printf(io, "%s,%d,%d,%d,%d,%.6f,0,Too large,,,,,,,,\n", name, inst.n, inst.m, D, nvars, nowp)
            end
            continue
        end
        # Ghi trước thông tin instance vào file .pending. Nếu tiến trình bị dừng cưỡng bức
        # (scripts/run.sh dùng lệnh timeout), script sẽ dùng file này để ghi dòng "Killed" vào CSV.
        pending = joinpath(outdir, "step$(step)-$(name).pending")
        write(pending, @sprintf("%s,%d,%d,%d,%d,%.6f", name, inst.n, inst.m, D, nvars, nowp))
        results = []
        build_s = 0.0
        t_inst = time()
        for seed in SEED0:SEED0+MAX_RUNS-1
            GC.gc()
            tb = @elapsed (model, x, S) = build_model(inst, rs; time_limit = tlim, seed = seed,
                                                       heuristic_effort = HEURISTIC, no_loops = NO_LOOPS)
            build_s = tb
            res = solve_and_report(model)
            push!(results, res)
            println("$name seed=$seed: ", res, "  (dựng mô hình $(round(tb, digits = 1)) s)")
            if !isnan(res.obj)
                tc = @elapsed chk = check_solution(inst, rs, model, x, S, outdir, step, name, seed, res)
                @printf("%s seed=%d: kiểm tra nghiệm: MLU từ path %.6f (solver %.6f), segment trong chu trình rời %d, tối đa %d segment, dist %d/%d, hợp lệ %s (%.1f s)\n",
                        name, seed, chk.mlu, res.obj, chk.cycles, chk.maxseg, chk.dist, chk.kappa, chk.ok, tc)
            end
            flush(stdout)
            model = nothing; x = nothing; GC.gc()
            (res.status == "Optimal" && res.cpu < FAST) || break
            # Không chạy seed tiếp nếu lần chạy sau (tối đa tlim giây) có thể vượt HARD_LIMIT:
            # nếu không, tiến trình bị dừng và mất luôn các lần chạy đã xong.
            if time() - t_inst + tlim + 300 > HARD
                println("$name: dừng lặp sau $(length(results)) lần chạy vì không đủ thời gian cho một lần nữa trước HARD_LIMIT = $(HARD) s")
                break
            end
        end
        cpus = [r.cpu for r in results]
        open(csv, "a") do io
            @printf(io, "%s,%d,%d,%d,%d,%.6f,%d,%s,%.6f,%.6f,%.6f,%.2f,%.2f,%.1f,%.1f,%.2f\n",
                name, inst.n, inst.m, D, nvars, nowp, length(results), results[1].status,
                mean(r.obj for r in results), mean(r.lb for r in results), mean(r.gap for r in results),
                mean(cpus), length(cpus) > 1 ? std(cpus) : 0.0,
                mean(r.nodes for r in results), build_s, mean(r.opt for r in results))
        end
        rm(pending; force = true)
    end
end

main(ARGS)
