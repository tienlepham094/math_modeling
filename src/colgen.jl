# =====================================================================
# Column generation (price-and-branch) cho T-ASR, min MLU.
#   - Một chu kỳ (Step 6): cột = một segment path cho một demand.
#   - Hai chu kỳ (Step 9): cột = cặp path (t=0, t=1) cho một demand, có hệ số budget Δ.
# Master LP giải bằng HiGHS C API (thêm cột trực tiếp, warm start).
# Pricing: quy hoạch động Bellman-Ford tối đa maxSeg segment trên đồ thị segment đầy đủ.
# Cận dưới: cận Lagrange, hợp lệ ở mọi vòng lặp.
# Nghiệm nguyên: MILP trên tập path đã sinh (HiGHS), có cận U >= LB.
# =====================================================================
using JuMP, HiGHS, Printf, Statistics, Random
include(joinpath(@__DIR__, "data.jl"))

const HI = HiGHS

# ---------------- r dạng CSR theo cặp nút ----------------
struct RCSR
    n::Int
    ptr::Vector{Int}
    arc::Vector{Int32}
    val::Vector{Float64}
    has::BitVector
end
@inline pidx(n, i, j) = (i - 1) * n + j

function to_csr(inst::Instance, r::SplitCoef)
    n = inst.n
    cnt = zeros(Int, n * n)
    has = falses(n * n)
    for ((i, j), lst) in r
        q = pidx(n, i, j); cnt[q] = length(lst); has[q] = true
    end
    ptr = Vector{Int}(undef, n * n + 1); ptr[1] = 1
    for q in 1:n*n; ptr[q+1] = ptr[q] + cnt[q]; end
    arc = Vector{Int32}(undef, ptr[end] - 1); val = Vector{Float64}(undef, ptr[end] - 1)
    for ((i, j), lst) in r
        k = ptr[pidx(n, i, j)]
        for (a, v) in lst; arc[k] = a; val[k] = v; k += 1; end
    end
    RCSR(n, ptr, arc, val, has)
end

# Wt[v,u] = Σ_a r(u,v,a) w[a]   (Inf nếu không có segment u->v)
function seg_weights!(Wt::Matrix{Float64}, R::RCSR, w::Vector{Float64})
    n = R.n
    Threads.@threads for u in 1:n
        @inbounds for v in 1:n
            q = pidx(n, u, v)
            if !R.has[q]; Wt[v, u] = Inf; continue; end
            s = 0.0
            for e in R.ptr[q]:R.ptr[q+1]-1; s += R.val[e] * w[R.arc[e]]; end
            Wt[v, u] = s
        end
    end
    Wt
end

# Cộng tải của path (hệ số r, chưa nhân volume) vào acc; touched = các cung khác 0
function path_load!(acc::Vector{Float64}, touched::Vector{Int}, R::RCSR, path::Vector{Int})
    @inbounds for k in 1:length(path)-1
        q = pidx(R.n, path[k], path[k+1])
        R.has[q] || error("segment $(path[k])->$(path[k+1]) không có đường đi")
        for e in R.ptr[q]:R.ptr[q+1]-1
            a = Int(R.arc[e])
            acc[a] == 0.0 && push!(touched, a)
            acc[a] += R.val[e]
        end
    end
end

segset(n, p::Vector{Int}) = Set(pidx(n, p[k], p[k+1]) for k in 1:length(p)-1)
valid_path(n, p) = length(segset(n, p)) == length(p) - 1     # không dùng một segment hai lần
delta(n, p, q) = (sp = segset(n, p); sq = segset(n, q); length(setdiff(sp, sq)) + length(setdiff(sq, sp)))

# ---------------- Pricing: DP tối đa K segment ----------------
# dist[v,k] = chi phí nhỏ nhất đi từ s tới v với tối đa k-1 segment
function dp1!(dist, pred, s, K, Wt)
    n = size(Wt, 1)
    fill!(dist, Inf); fill!(pred, Int32(0))
    dist[s, 1] = 0.0
    @inbounds for k in 2:K+1
        for v in 1:n; dist[v, k] = dist[v, k-1]; end
        for u in 1:n
            du = dist[u, k-1]
            isinf(du) && continue
            (k > 2 && !(du < dist[u, k-2])) && continue      # u không được cải thiện ở lớp trước
            for v in 1:n
                c = du + Wt[v, u]
                if c < dist[v, k] * (1 - 1e-10)
                    dist[v, k] = c; pred[v, k] = u
                end
            end
        end
    end
end

function dp2!(dist, pred, s, K, W0t, c0, W1t, c1)
    n = size(W0t, 1)
    fill!(dist, Inf); fill!(pred, Int32(0))
    dist[s, 1] = 0.0
    @inbounds for k in 2:K+1
        for v in 1:n; dist[v, k] = dist[v, k-1]; end
        for u in 1:n
            du = dist[u, k-1]
            isinf(du) && continue
            (k > 2 && !(du < dist[u, k-2])) && continue
            for v in 1:n
                c = du + c0 * W0t[v, u] + c1 * W1t[v, u]
                if c < dist[v, k] * (1 - 1e-10)
                    dist[v, k] = c; pred[v, k] = u
                end
            end
        end
    end
end

function getpath(pred, s, t, K)
    path = [t]; v = t; k = K + 1
    while k > 1
        u = Int(pred[v, k])
        if u != 0; pushfirst!(path, u); v = u; end
        k -= 1
    end
    v == s || error("DP: không dựng lại được path $s -> $t")
    path
end

# ---------------- Master LP (HiGHS C API) ----------------
struct Column
    d::Int
    paths::Vector{Vector{Int}}     # một path cho mỗi chu kỳ trong T
    delta::Int
end

mutable struct Master
    h::Ptr{Cvoid}
    inf::Float64
    D::Int
    nT::Int
    caprow::Vector{Vector{Int}}    # caprow[ti][a] = chỉ số dòng (0-based), -1 nếu cung bị tắt
    budrow::Int
    nrow::Int
    cols::Vector{Column}
    seen::Set{UInt}
end

hint(v) = HI.HighsInt.(v)

function Master(inst::Instance, T::Vector{Int}, κ)
    h = HI.Highs_create()
    HI.Highs_setBoolOptionValue(h, "output_flag", 0)
    inf = HI.Highs_getInfinity(h)
    HI.Highs_addCol(h, 1.0, 0.0, inf, 0, C_NULL, C_NULL)            # cột 0 = U
    D = length(inst.src)
    for d in 1:D
        HI.Highs_addRow(h, 1.0, 1.0, 0, C_NULL, C_NULL)               # Σ λ = 1
    end
    row = D
    caprow = Vector{Vector{Int}}()
    for t in T
        cr = fill(-1, inst.m)
        down = Set(get(inst.down, t, Int[]))
        for a in 1:inst.m
            a in down && continue
            HI.Highs_addRow(h, -inf, 0.0, 1, hint([0]), [-inst.cap[a]])   # tải - cap*U <= 0
            cr[a] = row; row += 1
        end
        push!(caprow, cr)
    end
    budrow = -1
    if length(T) == 2
        HI.Highs_addRow(h, -inf, Float64(κ), 0, C_NULL, C_NULL)
        budrow = row; row += 1
    end
    Master(h, inf, D, length(T), caprow, budrow, row, Column[], Set{UInt}())
end

function add_column!(M::Master, inst, Rs, T, col::Column, acc, touched)
    key = hash((col.d, col.paths))
    key in M.seen && return false
    push!(M.seen, key)
    idx = Int[col.d - 1]; val = Float64[1.0]
    for (ti, t) in enumerate(T)
        empty!(touched)
        path_load!(acc, touched, Rs[ti], col.paths[ti])
        vol = inst.vol[col.d, t+1]
        for a in touched
            r = M.caprow[ti][a]
            r >= 0 || error("path dùng cung bị tắt")
            if vol * acc[a] != 0.0
                push!(idx, r); push!(val, vol * acc[a])
            end
            acc[a] = 0.0
        end
    end
    if M.budrow >= 0 && col.delta > 0
        push!(idx, M.budrow); push!(val, Float64(col.delta))
    end
    HI.Highs_addCol(M.h, 0.0, 0.0, M.inf, length(idx), hint(idx), val)
    push!(M.cols, col)
    true
end

function solve_master!(M::Master)
    HI.Highs_run(M.h)
    st = HI.Highs_getModelStatus(M.h)
    ncol = HI.Highs_getNumCol(M.h); nrow = HI.Highs_getNumRow(M.h)
    colv = zeros(ncol); cold = zeros(ncol); rowv = zeros(nrow); rowd = zeros(nrow)
    HI.Highs_getSolution(M.h, colv, cold, rowv, rowd)
    (status = st, obj = HI.Highs_getObjectiveValue(M.h), colv = colv, rowd = rowd)
end

# ---------------- Vòng lặp column generation ----------------
# T = [0] (Step 6) hoặc [0, 1] (Step 9). Trả về master, LP, LB, thống kê.
function colgen(inst::Instance, Rs::Vector{RCSR}, T::Vector{Int}; time_limit = 600.0, verbose = true,
                max_iter = 10_000, tol = 1e-6)
    t0 = time()
    n, m, D, K = inst.n, inst.m, length(inst.src), inst.maxSeg
    κ = length(T) == 2 ? inst.budget[1] : 0
    M = Master(inst, T, κ)
    acc = zeros(m); touched = Int[]
    for d in 1:D                                     # cột ban đầu: không waypoint
        p = [inst.src[d], inst.dst[d]]
        add_column!(M, inst, Rs, T, Column(d, [p for _ in T], 0), acc, touched)
    end
    nT = length(T)
    Wt = [zeros(n, n) for _ in 1:nT]
    srcs = unique(inst.src)
    bysrc = Dict(s => [d for d in 1:D if inst.src[d] == s] for s in srcs)
    nth = Threads.maxthreadid()
    bufs = [(zeros(n, K + 1), zeros(Int32, n, K + 1)) for _ in 1:nth]
    best_lb = 0.0; lp = Inf; it = 0
    hist = Tuple{Int,Float64,Float64,Int}[]
    while it < max_iter
        it += 1
        sol = solve_master!(M)
        sol.status == 7 || error("master LP status $(sol.status)")
        lp = sol.obj
        y = sol.rowd
        μ = y[1:D]
        w = [zeros(m) for _ in 1:nT]
        for ti in 1:nT, a in 1:m
            r = M.caprow[ti][a]
            r >= 0 && (w[ti][a] = max(0.0, -y[r+1]))
        end
        ρ = M.budrow >= 0 ? max(0.0, -y[M.budrow+1]) : 0.0
        S = sum(sum(inst.cap .* w[ti]) for ti in 1:nT)
        for ti in 1:nT; seg_weights!(Wt[ti], Rs[ti], w[ti]); end

        # pricing
        best = Vector{Any}(undef, D)                 # các cột ứng viên của d
        lowest = zeros(D)
        # (a) path tốt nhất riêng cho từng chu kỳ: DP theo nguồn
        sep_cost = zeros(D, nT); sep_path = Matrix{Vector{Int}}(undef, D, nT)
        tasks = [(s, ti) for s in srcs for ti in 1:nT]
        Threads.@threads :static for k in eachindex(tasks)
            s, ti = tasks[k]
            dist, pred = bufs[Threads.threadid()]
            dp1!(dist, pred, s, K, Wt[ti])
            for d in bysrc[s]
                sep_cost[d, ti] = dist[inst.dst[d], K+1]
                sep_path[d, ti] = getpath(pred, s, inst.dst[d], K)
            end
        end
        if nT == 1
            for d in 1:D
                c = inst.vol[d, T[1]+1] * sep_cost[d, 1]
                lowest[d] = c
                best[d] = c - μ[d] < -tol * max(lp, 1e-9) ? [Column(d, [sep_path[d, 1]], 0)] : Column[]
            end
        else
            # (b) path chung cho cả hai chu kỳ: DP theo từng demand
            sh_cost = zeros(D); sh_path = Vector{Vector{Int}}(undef, D)
            Threads.@threads :static for d in 1:D
                dist, pred = bufs[Threads.threadid()]
                dp2!(dist, pred, inst.src[d], K, Wt[1], inst.vol[d, T[1]+1], Wt[2], inst.vol[d, T[2]+1])
                sh_cost[d] = dist[inst.dst[d], K+1]
                sh_path[d] = getpath(pred, inst.src[d], inst.dst[d], K)
            end
            for d in 1:D
                v0 = inst.vol[d, T[1]+1]; v1 = inst.vol[d, T[2]+1]
                sep = v0 * sep_cost[d, 1] + v1 * sep_cost[d, 2]
                lowest[d] = min(sh_cost[d], sep + 2ρ)
                cand = Column[]
                if sh_cost[d] - μ[d] < -tol * max(lp, 1e-9)
                    push!(cand, Column(d, [sh_path[d], sh_path[d]], 0))
                end
                p0, p1 = sep_path[d, 1], sep_path[d, 2]
                Δ = delta(n, p0, p1)
                if Δ > 0 && sep + ρ * Δ - μ[d] < -tol * max(lp, 1e-9)
                    push!(cand, Column(d, [p0, p1], Δ))
                end
                best[d] = cand
            end
        end
        lb = S > 0 ? (sum(lowest) - ρ * κ) / S : 0.0
        best_lb = max(best_lb, lb)
        added = 0
        for d in 1:D, col in best[d]
            all(p -> valid_path(n, p), col.paths) || continue
            added += add_column!(M, inst, Rs, T, col, acc, touched)
        end
        push!(hist, (it, lp, best_lb, added))
        if verbose && (it <= 3 || it % 10 == 0)
            @printf("  it %4d  LP %.6f  LB %.6f  gap %.4f%%  +%d cột (tổng %d)  %.1f s\n",
                    it, lp, best_lb, 100 * (1 - best_lb / lp), added, length(M.cols), time() - t0)
            flush(stdout)
        end
        (added == 0 || (lp - best_lb) <= 1e-6 * lp || time() - t0 > time_limit) && break
    end
    sol = solve_master!(M)
    lp = sol.obj
    (M = M, lp = lp, lb = min(best_lb, lp), iters = it, time = time() - t0, hist = hist, λ = sol.colv[2:end])
end

# ---------------- MILP trên tập path đã sinh ----------------
function restricted_milp(inst::Instance, Rs::Vector{RCSR}, T::Vector{Int}, M::Master, λ, lb;
                         time_limit = 600.0, verbose = false)
    n, m, D = inst.n, inst.m, length(inst.src)
    nT = length(T)
    κ = nT == 2 ? inst.budget[1] : 0
    # tập path của mỗi demand (dùng được ở mọi chu kỳ nếu segment còn đường đi)
    pool = [Vector{Vector{Int}}() for _ in 1:D]
    seenp = [Set{Vector{Int}}() for _ in 1:D]
    for c in M.cols, p in c.paths
        p in seenp[c.d] || (push!(seenp[c.d], p); push!(pool[c.d], p))
    end
    okt(ti, p) = all(Rs[ti].has[pidx(n, p[k], p[k+1])] for k in 1:length(p)-1)

    model = Model(HiGHS.Optimizer)
    set_silent(model) ; verbose && unset_silent(model)
    set_time_limit_sec(model, time_limit)
    set_attribute(model, "mip_rel_gap", 1e-6)
    @variable(model, U >= lb * (1 - 1e-7))                       # cận dưới hợp lệ giúp dừng sớm
    u = [[Dict{Int,VariableRef}() for _ in 1:D] for _ in 1:nT]
    acc = zeros(m); touched = Int[]
    for ti in 1:nT
        t = T[ti]
        load = [AffExpr(0.0) for _ in 1:m]
        for d in 1:D
            for (k, p) in enumerate(pool[d])
                okt(ti, p) || continue
                x = @variable(model, binary = true)
                u[ti][d][k] = x
                empty!(touched); path_load!(acc, touched, Rs[ti], p)
                for a in touched
                    add_to_expression!(load[a], inst.vol[d, t+1] * acc[a], x); acc[a] = 0.0
                end
            end
            @constraint(model, sum(values(u[ti][d])) == 1)
        end
        down = Set(get(inst.down, t, Int[]))
        for a in 1:m
            a in down && continue
            @constraint(model, load[a] <= inst.cap[a] * U)
        end
    end
    if nT == 2
        changes = AffExpr(0.0)
        for d in 1:D
            segs = Dict{Int,Tuple{AffExpr,AffExpr}}()
            for ti in 1:2, (k, x) in u[ti][d]
                p = pool[d][k]
                for q in segset(n, p)
                    e = get!(segs, q, (AffExpr(0.0), AffExpr(0.0)))
                    add_to_expression!(e[ti], 1.0, x)
                end
            end
            for (q, (e0, e1)) in segs
                y = @variable(model, lower_bound = 0)
                @constraint(model, y >= e1 - e0)
                @constraint(model, y >= e0 - e1)
                add_to_expression!(changes, y)
            end
        end
        @constraint(model, changes <= κ)
    end
    @objective(model, Min, U)

    # Nghiệm khởi đầu: mỗi demand lấy cột có λ lớn nhất; nếu vượt budget thì đưa về cột Δ = 0
    pick = Dict{Int,Int}()        # d -> chỉ số cột
    for (ci, c) in enumerate(M.cols)
        (!haskey(pick, c.d) || λ[ci] > λ[pick[c.d]]) && (pick[c.d] = ci)
    end
    if nT == 2
        used = sum(M.cols[pick[d]].delta for d in 1:D)
        if used > κ
            order = sort([d for d in 1:D if M.cols[pick[d]].delta > 0], by = d -> λ[pick[d]])
            for d in order
                used <= κ && break
                alt = [ci for (ci, c) in enumerate(M.cols) if c.d == d && c.delta == 0]
                ci = alt[argmax(λ[alt])]
                used -= M.cols[pick[d]].delta; pick[d] = ci
            end
        end
    end
    for ti in 1:nT, d in 1:D
        p = M.cols[pick[d]].paths[ti]
        k = findfirst(==(p), pool[d])
        for (kk, x) in u[ti][d]; set_start_value(x, kk == k ? 1.0 : 0.0); end
    end
    optimize!(model)
    has_values(model) || error("MILP không có nghiệm")
    chosen =[[begin
                   ks = [k for (k, x) in u[ti][d] if value(x) > 0.5]
                   pool[d][ks[1]]
               end for d in 1:D] for ti in 1:nT]
    (chosen = chosen, obj = objective_value(model), bound = objective_bound(model),
     status = string(termination_status(model)), time = solve_time(model),
     nbin = sum(length(u[ti][d]) for ti in 1:nT for d in 1:D))
end

# ---------------- Đánh giá độc lập một nghiệm ----------------
function evaluate(inst::Instance, Rs::Vector{RCSR}, T::Vector{Int}, chosen)
    n, m = inst.n, inst.m
    mlu = Float64[]
    for (ti, t) in enumerate(T)
        load = zeros(m); acc = zeros(m); touched = Int[]
        for (d, p) in enumerate(chosen[ti])
            p[1] == inst.src[d] && p[end] == inst.dst[d] || error("path sai nguồn/đích")
            length(p) - 1 <= inst.maxSeg || error("quá maxSeg")
            valid_path(n, p) || error("segment lặp lại")
            empty!(touched); path_load!(acc, touched, Rs[ti], p)
            for a in touched; load[a] += inst.vol[d, t+1] * acc[a]; acc[a] = 0.0; end
        end
        down = Set(get(inst.down, t, Int[]))
        any(load[a] > 0 for a in down) && error("có tải trên cung bị tắt")
        push!(mlu, maximum(load[a] / inst.cap[a] for a in 1:m if !(a in down)))
    end
    used = length(T) == 2 ? sum(delta(n, chosen[1][d], chosen[2][d]) for d in eachindex(chosen[1])) : 0
    (mlu = mlu, U = maximum(mlu), used = used)
end
