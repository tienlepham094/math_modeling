# =====================================================================
# Phương pháp 2: column generation + MILP trên tập cột + vòng cải thiện (src/colgen.jl, src/improve.jl).
# Chạy được cả 20 instance SetA, kể cả các instance mà MILP đầy đủ (src/model.jl) không dựng nổi.
#
# Cách gọi:
#   julia -t 8 --project=. src/run_cg.jl 6 all        # Step 6: chỉ t = 0
#   julia -t 8 --project=. src/run_cg.jl 9 1 2 3      # Step 9: t = 0 và t = 1 có budget
#
# Biến môi trường (mặc định trong ngoặc):
#   CG_TIME   (600)  giới hạn thời gian column generation (giây)
#   MILP_TIME (300)  giới hạn cho MILP trên tập cột
#   IMP_TIME  (780 cho Step 6, 2400 cho Step 9)  giới hạn cho vòng cải thiện, chọn để tổng
#                    CG_TIME + MILP_TIME + IMP_TIME nằm dưới time limit của đề (1800 s / 3600 s)
#   RESULTS_DIR (results) -> kết quả ghi vào <RESULTS_DIR>/cg/
#   FORCE     (0)    1 = chạy lại instance đã có trong CSV
#   SEED      (0)    random seed của HiGHS cho các MILP (để chạy 10 lần với seed khác nhau)
#
# Kết quả: cg_step6.csv / cg_step9.csv và nghiệm <instance>-step<6|9>-srpaths.json
# (đúng định dạng của checker chính thức ROADEF 2026, d = thứ tự demand trong file tm).
#
# Cột gap = 1 - LB/UB, với LB là cận dưới đã chứng minh:
#   max(cận Lagrange từ column generation, cận "một demand").
# =====================================================================
include(joinpath(@__DIR__, "colgen.jl"))
include(joinpath(@__DIR__, "improve.jl"))

const ROOT = dirname(@__DIR__)
envf(k, d) = haskey(ENV, k) ? parse(Float64, ENV[k]) : d

no_wp(inst, Rs, T) = evaluate(inst, Rs, T, [[[inst.src[d], inst.dst[d]] for d in eachindex(inst.src)] for _ in T])

function main(args)
    if length(args) < 2 || !(args[1] in ("6", "9"))
        println("Cách dùng: julia -t 8 --project=. src/run_cg.jl <6|9> <danh sách instance | all>")
        exit(1)
    end
    step = parse(Int, args[1])
    ids = args[2] == "all" ? collect(1:20) : parse.(Int, args[2:end])
    T = step == 6 ? [0] : [0, 1]
    out = joinpath(ROOT, get(ENV, "RESULTS_DIR", "results"), "cg"); mkpath(out)
    csv = joinpath(out, "cg_step$(step).csv")
    isfile(csv) || write(csv, "instance,n,m,D,kappa,seed,status,mlu_nowp,lp,lb,ub,gap,mlu_t0,mlu_t1,budget_used,cg_iters,cols,nodes,cpu_s,cg_s,milp_s,total_s\n")
    done = Set(first(split(l, ",")) for l in readlines(csv)[2:end] if !isempty(l))
    cgt = envf("CG_TIME", 600.0); mt = envf("MILP_TIME", 300.0); imt = envf("IMP_TIME", step == 6 ? 780.0 : 2400.0)
    println("Step $step | $(Threads.nthreads()) luồng | CG_TIME $cgt | MILP_TIME $mt | IMP_TIME $imt | ghi vào $csv")
    for k in ids
        name = @sprintf("setA-%02d", k)
        if name in done && get(ENV, "FORCE", "0") != "1"
            println("$name: đã có trong $csv => bỏ qua (đặt FORCE=1 để chạy lại)")
            continue
        end
        t_start = time()
        inst = read_instance(joinpath(ROOT, "setA", name))
        D = length(inst.src)
        Rs = [to_csr(inst, r_ecmp(inst, t)) for t in T]
        nw = no_wp(inst, Rs, T)
        κ = step == 9 ? inst.budget[1] : 0
        println("== $name n=$(inst.n) m=$(inst.m) D=$D κ=$κ | MLU không waypoint $(round(nw.U, digits = 6))")
        flush(stdout)

        # 1. Column generation: LP và cận dưới Lagrange.
        # cpu_s = thời gian giải (từ đây tới hết vòng cải thiện), không tính đọc dữ liệu và tính r.
        t_solve = time()
        cg = colgen(inst, Rs, T; time_limit = cgt)
        lb = max(cg.lb, single_demand_lb(inst, Rs, T))
        @printf("  CG: %d vòng, %d cột, LP %.6f, cận dưới %.6f, %.1f s\n", cg.iters, length(cg.M.cols), cg.lp, lb, cg.time)
        flush(stdout)

        # 2. MILP trên tập cột đã sinh, xuất phát từ nghiệm làm tròn LP
        t_milp = time()
        pool = pool_from_master(cg.M, D)
        start = round_start(cg.M, cg.λ, D, length(T), κ)
        if length(T) == 2
            C0 = falses(D)                       # demand mà LP dùng cột có thay đổi (Δ > 0)
            for (ci, c) in enumerate(cg.M.cols); (c.delta > 0 && cg.λ[ci] > 1e-6) && (C0[c.d] = true); end
            mi = milp_pairs(inst, Rs, T, pool, start, trues(D), C0, lb; time_limit = mt)
        else
            mi = milp_pool(inst, Rs, T, pool, start, trues(D), lb; time_limit = mt)
        end
        @printf("  MILP trên tập cột: %s, U %.6f (%.1f s)\n", mi.status, evaluate(inst, Rs, T, mi.chosen).U, mi.time)
        flush(stdout)

        # 3. Vòng cải thiện quanh các link nghẽn
        best, _, imp_nodes = improve(inst, Rs, T, pool, mi.chosen, lb; time_limit = imt, milp_time = min(mt, 120.0))
        milp_s = time() - t_milp
        cpu_s = time() - t_solve
        nodes = mi.nodes + imp_nodes
        HI.Highs_destroy(cg.M.h)

        # 4. Kiểm tra độc lập và ghi kết quả
        ev = evaluate(inst, Rs, T, best)
        ev.used <= κ || error("vượt budget: $(ev.used) > $κ")
        gap = max(0.0, 1 - lb / ev.U)
        # Optimal = đã chứng minh bằng cận dưới, với cùng ngưỡng như phương pháp 1 (mip_rel_gap mặc định của HiGHS = 1e-4)
        status = gap <= 1e-4 ? "Optimal" : "Not Optimal"
        total = time() - t_start
        @printf("  KẾT QUẢ: %s MLU %.6f (t0 %.6f%s) | cận dưới %.6f | gap %.3f%% | budget %d/%d | nút B&B %d | CPU %.1f s (tổng %.1f s)\n",
                status, ev.U, ev.mlu[1], length(T) == 2 ? @sprintf(", t1 %.6f", ev.mlu[2]) : "", lb, 100gap, ev.used, κ, nodes, cpu_s, total)
        flush(stdout)
        open(csv, "a") do io
            @printf(io, "%s,%d,%d,%d,%d,%s,%s,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%s,%d,%d,%d,%d,%.1f,%.1f,%.1f,%.1f\n",
                    name, inst.n, inst.m, D, κ, get(ENV, "SEED", "0"), status, nw.U, cg.lp, lb, ev.U, gap, ev.mlu[1],
                    length(T) == 2 ? @sprintf("%.6f", ev.mlu[2]) : "", ev.used, cg.iters, length(cg.M.cols),
                    nodes, cpu_s, cg.time, milp_s, total)
        end
        open(joinpath(out, "$(name)-step$(step)-srpaths.json"), "w") do io
            items = String[]
            for (ti, t) in enumerate(T), d in 1:D
                w = inst.node_id[best[ti][d][2:end-1]]
                push!(items, "{\"d\":$(d-1),\"t\":$t,\"w\":[$(join(w, ","))]}")
            end
            print(io, "{\"srpaths\":[\n", join(items, ",\n"), "\n]}\n")
        end
        GC.gc()
    end
end

main(ARGS)
