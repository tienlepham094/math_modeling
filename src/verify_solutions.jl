# =====================================================================
# Kiểm tra độc lập nghiệm của mô hình (Step 6 và Step 9).
#
#   julia --project=. src/verify_solutions.jl 9 1 2 3     # Step 9 cho setA-01, 02, 03
#   julia --project=. src/verify_solutions.jl 6 1 2 3     # Step 6
#
# Giải mô hình với đúng thiết lập của thí nghiệm (seed 0), rồi:
#   1. đọc segment path của mỗi demand bằng đường đi Euler từ nguồn (hàm waypoints);
#   2. báo các chu trình rời (segment có x = 1 nhưng không nằm trên đường đi từ nguồn);
#   3. tính lại tải từ DANH SÁCH SEGMENT (không dùng biến của mô hình) và MLU của từng chu kỳ;
#   4. tính dist(P^0, P^1) theo định nghĩa của đề và so với budget κ(1).
# Nếu không có chu trình rời, MLU tính lại bằng U và dist <= κ thì nghiệm của mô hình
# là một nghiệm hợp lệ của bài toán T-ASR (với mục tiêu MLU).
# =====================================================================
using Printf
include("data.jl")
include("model.jl")

const ROOT = dirname(@__DIR__)

# Danh sách segment (i, j) của đường đi Euler s = w0, w1, ..., t
function segment_path(inst, x, S, d, t)
    w, leftover = waypoints(inst, x, S, d, t)
    nodes = [inst.src[d]; w; inst.dst[d]]
    return [(nodes[k], nodes[k+1]) for k in 1:length(nodes)-1], leftover
end

function main(args)
    step = parse(Int, args[1])
    ids = parse.(Int, args[2:end])
    tlim = step == 6 ? 1800.0 : 3600.0
    for k in ids
        name = @sprintf("setA-%02d", k)
        inst = read_instance(joinpath(ROOT, "setA", name))
        D = length(inst.src)
        rs = step == 6 ? [r_ecmp(inst, 0)] : [r_ecmp(inst, 0), r_ecmp(inst, 1)]
        model, x, S = build_model(inst, rs; time_limit = tlim, seed = 0, heuristic_effort = 0.3, no_loops = false)
        res = solve_and_report(model)
        U = value(model[:U])
        paths = [[segment_path(inst, x, S, d, t) for d in 1:D] for t in 0:length(rs)-1]
        leftover = sum(l for P in paths for (_, l) in P)
        too_long = count(length(p) > inst.maxSeg for P in paths for (p, _) in P)
        ends_ok = all(p[end][2] == inst.dst[d] for P in paths for (d, (p, _)) in enumerate(P))
        # tải tính lại từ danh sách segment
        mlu = Float64[]
        for t in 0:length(rs)-1
            load = zeros(inst.m)
            for d in 1:D, seg in paths[t+1][d][1], (a, ratio) in rs[t+1][seg]
                load[a] += ratio * inst.vol[d, t+1]
            end
            push!(mlu, maximum(load[a] / inst.cap[a] for a in alive_arcs(inst, t)))
        end
        line = @sprintf("%s Step %d: %s, U = %.6f, cpu = %.1f s | MLU tính lại theo chu kỳ = %s | chu trình rời: %d segment | path quá maxSeg: %d | tới đúng đích: %s",
                        name, step, res.status, U, res.cpu, join((@sprintf("%.6f", v) for v in mlu), ", "),
                        leftover, too_long, ends_ok)
        if step == 9
            dist = sum(length(symdiff(Set(paths[2][d][1]), Set(paths[1][d][1]))) for d in 1:D)
            changed = count(Set(paths[2][d][1]) != Set(paths[1][d][1]) for d in 1:D)
            line *= @sprintf(" | dist(P0,P1) = %d (κ = %d), %d demand đổi đường", dist, inst.budget[1], changed)
        end
        println(line); flush(stdout)
    end
end

main(ARGS)
