# =====================================================================
# Cải thiện nghiệm nguyên sau column generation:
#   - MILP trên tập path của từng demand (pool), có thể cố định các demand không liên quan.
#   - Vòng lặp: giải MILP -> tìm link nghẽn -> sinh path thay thế (DP "cổ chai") cho các
#     demand đi qua link nghẽn -> thêm vào pool -> giải lại.
#   - Cận dưới "một demand": demand d một mình đã làm link nào đó đạt mức tải tối thiểu bao nhiêu.
# =====================================================================

# DP cổ chai, so sánh từ điển (max, tổng): Cm[v,u], Cs[v,u] = chi phí segment u->v
function bdp!(dm, ds, pred, s, K, Cm, Cs)
    n = size(Cm, 1)
    fill!(dm, Inf); fill!(ds, Inf); fill!(pred, Int32(0))
    dm[s, 1] = 0.0; ds[s, 1] = 0.0
    @inbounds for k in 2:K+1
        for v in 1:n; dm[v, k] = dm[v, k-1]; ds[v, k] = ds[v, k-1]; end
        for u in 1:n
            mu = dm[u, k-1]; su = ds[u, k-1]
            isinf(mu) && continue
            (k > 2 && mu == dm[u, k-2] && su == ds[u, k-2]) && continue
            for v in 1:n
                c = Cm[v, u]
                isinf(c) && continue
                cm = max(mu, c); cs = su + Cs[v, u]
                if cm < dm[v, k] * (1 - 1e-12) || (cm <= dm[v, k] * (1 + 1e-12) && cs < ds[v, k] * (1 - 1e-10))
                    dm[v, k] = cm; ds[v, k] = cs; pred[v, k] = u
                end
            end
        end
    end
end

# Cm[v,u] = max_a (base[a] + vol*r(u,v,a))/cap[a],  Cs[v,u] = Σ_a vol*r/cap   (cộng dồn vào Cm, Cs có sẵn)
function seg_bneck!(Cm, Cs, R::RCSR, base, vol, cap)
    n = R.n
    @inbounds for u in 1:n, v in 1:n
        q = pidx(n, u, v)
        if !R.has[q]; Cm[v, u] = Inf; continue; end
        mx = 0.0; sm = 0.0
        for e in R.ptr[q]:R.ptr[q+1]-1
            a = R.arc[e]; x = vol * R.val[e]
            mx = max(mx, (base[a] + x) / cap[a]); sm += x / cap[a]
        end
        Cm[v, u] = max(Cm[v, u], mx); Cs[v, u] += sm
    end
end

# Cận dưới một demand: max_{d,t} min_p max_a vol(d,t) r(p,a)/cap(a)  (DP theo nguồn, hệ số vol tách ra)
function single_demand_lb(inst::Instance, Rs::Vector{RCSR}, T::Vector{Int})
    n, K, D = inst.n, inst.maxSeg, length(inst.src)
    lb = 0.0
    zero = zeros(inst.m)
    for (ti, t) in enumerate(T)
        Cm = zeros(n, n); Cs = zeros(n, n)
        seg_bneck!(Cm, Cs, Rs[ti], zero, 1.0, inst.cap)
        srcs = unique(inst.src)
        res = zeros(D)
        nth = Threads.maxthreadid()
        bufs = [(zeros(n, K + 1), zeros(n, K + 1), zeros(Int32, n, K + 1)) for _ in 1:nth]
        Threads.@threads :static for s in srcs
            dm, ds, pred = bufs[Threads.threadid()]
            bdp!(dm, ds, pred, s, K, Cm, Cs)
            for d in 1:D
                inst.src[d] == s && (res[d] = inst.vol[d, t+1] * dm[inst.dst[d], K+1])
            end
        end
        lb = max(lb, maximum(res))
    end
    lb
end

pool_from_master(M, D) = begin
    pool = [Vector{Vector{Int}}() for _ in 1:D]
    for c in M.cols, p in c.paths
        p in pool[c.d] || push!(pool[c.d], p)
    end
    pool
end

# Nghiệm khởi đầu từ LP: mỗi demand lấy cột có λ lớn nhất; nếu vượt budget thì đưa về cột Δ = 0
function round_start(M, λ, D, nT, κ)
    pick = zeros(Int, D)
    for (ci, c) in enumerate(M.cols)
        (pick[c.d] == 0 || λ[ci] > λ[pick[c.d]]) && (pick[c.d] = ci)
    end
    if nT == 2
        used = sum(M.cols[pick[d]].delta for d in 1:D)
        if used > κ
            for d in sort([d for d in 1:D if M.cols[pick[d]].delta > 0], by = d -> λ[pick[d]])
                used <= κ && break
                alt = [ci for (ci, c) in enumerate(M.cols) if c.d == d && c.delta == 0]
                ci = alt[argmax(λ[alt])]
                used -= M.cols[pick[d]].delta; pick[d] = ci
            end
        end
    end
    [[M.cols[pick[d]].paths[ti] for d in 1:D] for ti in 1:nT]
end

function current_loads(inst, Rs, T, chosen)
    m = inst.m
    L = [zeros(m) for _ in T]
    acc = zeros(m); touched = Int[]
    for (ti, t) in enumerate(T), d in eachindex(chosen[ti])
        empty!(touched); path_load!(acc, touched, Rs[ti], chosen[ti][d])
        for a in touched; L[ti][a] += inst.vol[d, t+1] * acc[a]; acc[a] = 0.0; end
    end
    L
end

# MILP trên pool; demand không thuộc `free` bị cố định theo `start`
function milp_pool(inst, Rs, T, pool, start, free::BitVector, lb; time_limit = 300.0)
    n, m, D = inst.n, inst.m, length(inst.src)
    nT = length(T)
    κ = nT == 2 ? inst.budget[1] : 0
    okt(ti, p) = all(Rs[ti].has[pidx(n, p[k], p[k+1])] for k in 1:length(p)-1)
    for ti in 1:nT, d in 1:D
        start[ti][d] in pool[d] || push!(pool[d], start[ti][d])
    end
    model = Model(HiGHS.Optimizer)
    set_silent(model)
    set_time_limit_sec(model, time_limit)
    set_attribute(model, "mip_rel_gap", 1e-6)
    set_attribute(model, "random_seed", parse(Int, get(ENV, "SEED", "0")))   # mỗi lần chạy một seed
    @variable(model, U >= lb * (1 - 1e-7))
    u = [[Dict{Int,VariableRef}() for _ in 1:D] for _ in 1:nT]
    acc = zeros(m); touched = Int[]
    fixed_used = 0
    for d in 1:D
        (!free[d] && nT == 2) && (fixed_used += delta(n, start[1][d], start[2][d]))
    end
    for ti in 1:nT
        t = T[ti]
        load = [AffExpr(0.0) for _ in 1:m]
        for d in 1:D
            if !free[d]
                empty!(touched); path_load!(acc, touched, Rs[ti], start[ti][d])
                for a in touched; add_to_expression!(load[a], inst.vol[d, t+1] * acc[a]); acc[a] = 0.0; end
                continue
            end
            for (k, p) in enumerate(pool[d])
                okt(ti, p) || continue
                x = @variable(model, binary = true)
                u[ti][d][k] = x
                set_start_value(x, p == start[ti][d] ? 1.0 : 0.0)
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
        changes = AffExpr(Float64(fixed_used))
        for d in 1:D
            free[d] || continue
            segs = Dict{Int,Tuple{AffExpr,AffExpr}}()
            for ti in 1:2, (k, x) in u[ti][d], q in segset(n, pool[d][k])
                e = get!(segs, q, (AffExpr(0.0), AffExpr(0.0)))
                add_to_expression!(e[ti], 1.0, x)
            end
            s0 = segset(n, start[1][d]); s1 = segset(n, start[2][d])
            for (q, (e0, e1)) in segs
                y = @variable(model, lower_bound = 0)
                set_start_value(y, abs((q in s1) - (q in s0)))
                @constraint(model, y >= e1 - e0)
                @constraint(model, y >= e0 - e1)
                add_to_expression!(changes, y)
            end
        end
        @constraint(model, changes <= κ)
    end
    @objective(model, Min, U)
    optimize!(model)
    if !has_values(model)
        return (chosen = start, status = string(termination_status(model)), time = solve_time(model), nodes = node_count(model),
                nbin = 0, bound = -Inf)
    end
    chosen = [[free[d] ? pool[d][first(k for (k, x) in u[ti][d] if value(x) > 0.5)] : start[ti][d]
               for d in 1:D] for ti in 1:nT]
    (chosen = chosen, status = string(termination_status(model)), time = solve_time(model), nodes = node_count(model),
     nbin = sum(length(u[ti][d]) for ti in 1:nT for d in 1:D), bound = objective_bound(model))
end

# Sinh path thay thế cho các demand đi qua link nghẽn
function add_candidates!(pool, inst, Rs, T, chosen, L, U; θ = 0.995, maxdem = 400, avoid = true)
    n, m, K, D = inst.n, inst.m, inst.maxSeg, length(inst.src)
    nT = length(T)
    crit = [Set(a for a in 1:m if L[ti][a] >= θ * U * inst.cap[a]) for ti in 1:nT]
    acc = zeros(m); touched = Int[]
    score = zeros(D)
    for ti in 1:nT, d in 1:D
        empty!(touched); path_load!(acc, touched, Rs[ti], chosen[ti][d])
        for a in touched
            a in crit[ti] && (score[d] += inst.vol[d, T[ti]+1] * acc[a] / inst.cap[a])
            acc[a] = 0.0
        end
    end
    dems = sort([d for d in 1:D if score[d] > 0], by = d -> -score[d])
    dems = dems[1:min(end, maxdem)]
    # segment chứa ít nhất một link nghẽn (để sinh thêm path tránh hẳn các link này)
    segcrit = [falses(n * n) for _ in 1:nT]
    for ti in 1:nT, q in 1:n*n
        R = Rs[ti]
        R.has[q] || continue
        for e in R.ptr[q]:R.ptr[q+1]-1
            if Int(R.arc[e]) in crit[ti]; segcrit[ti][q] = true; break; end
        end
    end
    nth = Threads.maxthreadid()
    bufs = [(zeros(n, n), zeros(n, n), zeros(n, n), zeros(n, n), zeros(n, K + 1), zeros(n, K + 1),
             zeros(Int32, n, K + 1), zeros(m), Int[], [zeros(m) for _ in 1:nT], zeros(n, n)) for _ in 1:nth]
    newp = Vector{Vector{Vector{Int}}}(undef, length(dems))
    Threads.@threads :static for k in eachindex(dems)
        d = dems[k]
        Cm0, Cs0, Cm, Cs, dm, ds, pred, acc2, tch, base, Ca = bufs[Threads.threadid()]
        found = Vector{Vector{Int}}()
        fill!(Cm, 0.0); fill!(Cs, 0.0)
        for ti in 1:nT
            copyto!(base[ti], L[ti])
            empty!(tch); path_load!(acc2, tch, Rs[ti], chosen[ti][d])
            for a in tch; base[ti][a] -= inst.vol[d, T[ti]+1] * acc2[a]; acc2[a] = 0.0; end
            fill!(Cm0, 0.0); fill!(Cs0, 0.0)
            seg_bneck!(Cm0, Cs0, Rs[ti], base[ti], inst.vol[d, T[ti]+1], inst.cap ./ U)
            bdp!(dm, ds, pred, inst.src[d], K, Cm0, Cs0)
            push!(found, getpath(pred, inst.src[d], inst.dst[d], K))
            if avoid
                copyto!(Ca, Cm0)
                for u in 1:n, v in 1:n; segcrit[ti][pidx(n, u, v)] && (Ca[v, u] = Inf); end
                bdp!(dm, ds, pred, inst.src[d], K, Ca, Cs0)
                isinf(dm[inst.dst[d], K+1]) || push!(found, getpath(pred, inst.src[d], inst.dst[d], K))
            end
            Cm .= max.(Cm, Cm0); Cs .+= Cs0
        end
        if nT == 2
            bdp!(dm, ds, pred, inst.src[d], K, Cm, Cs)
            push!(found, getpath(pred, inst.src[d], inst.dst[d], K))
            if avoid
                copyto!(Ca, Cm)
                for u in 1:n, v in 1:n
                    q = pidx(n, u, v); (segcrit[1][q] || segcrit[2][q]) && (Ca[v, u] = Inf)
                end
                bdp!(dm, ds, pred, inst.src[d], K, Ca, Cs)
                isinf(dm[inst.dst[d], K+1]) || push!(found, getpath(pred, inst.src[d], inst.dst[d], K))
            end
        end
        newp[k] = found
    end
    added = 0
    for (k, d) in enumerate(dems), p in newp[k]
        if valid_path(n, p) && !(p in pool[d])
            push!(pool[d], p); added += 1
        end
    end
    added, dems
end

# Vòng lặp cải thiện. Trả về nghiệm tốt nhất.
function improve(inst, Rs, T, pool, start, lb; time_limit = 600.0, milp_time = 120.0, verbose = true,
                 free_frac = 0.9, max_free = 1500, max_change = 300)
    t0 = time()
    D = length(inst.src); n = inst.n
    best = start; bestU = evaluate(inst, Rs, T, start).U
    stall = 0; round = 0; nodes = 0
    while time() - t0 < time_limit && bestU > lb * (1 + 1e-6)
        round += 1
        L = current_loads(inst, Rs, T, best)
        added, dems = add_candidates!(pool, inst, Rs, T, best, L, bestU; θ = stall == 0 ? 0.995 : 0.97,
                                      maxdem = stall == 0 ? 400 : 800)
        # demand được tự do: đi qua link có tải >= ff * U; khi bị kẹt thì mở rộng vùng tìm kiếm
        ff = stall == 0 ? free_frac : 0.5
        mf = stall == 0 ? max_free : max(max_free, min(D, 2000))
        score = zeros(D); acc = zeros(inst.m); touched = Int[]
        for (ti, t) in enumerate(T), d in 1:D
            empty!(touched); path_load!(acc, touched, Rs[ti], best[ti][d])
            for a in touched
                u = L[ti][a] / inst.cap[a]
                u >= ff * bestU && (score[d] = max(score[d], u))
                acc[a] = 0.0
            end
        end
        cand = sort([d for d in 1:D if score[d] > 0], by = d -> -score[d])
        free = falses(D)
        for d in cand[1:min(end, mf)]; free[d] = true; end
        for d in dems; free[d] = true; end
        tl_ = min(milp_time, time_limit - (time() - t0) + 1)
        if length(T) == 2
            C = falses(D)
            for d in cand[1:min(end, max_change)]; C[d] = true; end
            for d in dems; C[d] = true; end
            res = milp_pairs(inst, Rs, T, pool, best, free, C, lb; time_limit = tl_)
        else
            res = milp_pool(inst, Rs, T, pool, best, free, lb; time_limit = tl_)
        end
        nodes += res.nodes
        ev = evaluate(inst, Rs, T, res.chosen)
        κ = length(T) == 2 ? inst.budget[1] : 0
        improved = ev.used <= κ && ev.U < bestU * (1 - 1e-9)
        if improved
            best = res.chosen; bestU = ev.U; stall = 0
        else
            stall += 1
        end
        verbose && @printf("  cải thiện vòng %d: +%d path, %d demand tự do, MILP %s %.1f s -> U %.6f %s\n",
                           round, added, count(free), res.status, res.time, ev.U, improved ? "(tốt hơn)" : "")
        flush(stdout)
        (added == 0 && !improved && stall >= 2) && break      # cho vòng mở rộng một cơ hội
        stall >= 3 && break
    end
    best, bestU, nodes
end

# MILP hai chu kỳ dạng "cặp path": mỗi demand chọn một path chung (Δ = 0) hoặc, nếu thuộc tập C,
# một cặp (p0, p1) khác nhau với chi phí budget Δ(p0, p1). Chính xác trên không gian này và
# LP relaxation chặt hơn cách tuyến tính hoá |x1 - x0| bằng biến y.
function milp_pairs(inst, Rs, T, pool, start, free::BitVector, C::BitVector, lb; time_limit = 300.0)
    n, m, D = inst.n, inst.m, length(inst.src)
    κ = inst.budget[1]
    okt(ti, p) = all(Rs[ti].has[pidx(n, p[k], p[k+1])] for k in 1:length(p)-1)
    for ti in 1:2, d in 1:D
        start[ti][d] in pool[d] || push!(pool[d], start[ti][d])
    end
    model = Model(HiGHS.Optimizer)
    set_silent(model)
    set_time_limit_sec(model, time_limit)
    set_attribute(model, "mip_rel_gap", 1e-6)
    set_attribute(model, "random_seed", parse(Int, get(ENV, "SEED", "0")))   # mỗi lần chạy một seed
    @variable(model, U >= lb * (1 - 1e-7))
    load = [[AffExpr(0.0) for _ in 1:m] for _ in 1:2]
    acc = zeros(m); touched = Int[]
    plist = [Dict{Tuple{Int,Int},VariableRef}() for _ in 1:D]     # (k0, k1) -> biến
    used_fixed = 0
    budget = AffExpr(0.0)
    function addload!(ti, d, p, x)
        empty!(touched); path_load!(acc, touched, Rs[ti], p)
        for a in touched
            if x === nothing
                add_to_expression!(load[ti][a], inst.vol[d, T[ti]+1] * acc[a])
            else
                add_to_expression!(load[ti][a], inst.vol[d, T[ti]+1] * acc[a], x)
            end
            acc[a] = 0.0
        end
    end
    for d in 1:D
        if !free[d]
            addload!(1, d, start[1][d], nothing); addload!(2, d, start[2][d], nothing)
            used_fixed += delta(n, start[1][d], start[2][d])
            continue
        end
        P = pool[d]
        ok0 = [okt(1, p) for p in P]; ok1 = [okt(2, p) for p in P]
        k0s = findfirst(==(start[1][d]), P); k1s = findfirst(==(start[2][d]), P)
        pairs = [(k, k) for k in eachindex(P) if ok0[k] && ok1[k]]
        if C[d] || k0s != k1s
            for k in eachindex(P), l in eachindex(P)
                (k != l && ok0[k] && ok1[l]) || continue
                (C[d] || (k, l) == (k0s, k1s)) || continue
                Δ = delta(n, P[k], P[l])
                Δ <= κ && push!(pairs, (k, l))
            end
        end
        for (k, l) in pairs
            x = @variable(model, binary = true)
            plist[d][(k, l)] = x
            set_start_value(x, (k, l) == (k0s, k1s) ? 1.0 : 0.0)
            addload!(1, d, P[k], x); addload!(2, d, P[l], x)
            k != l && add_to_expression!(budget, Float64(delta(n, P[k], P[l])), x)
        end
        @constraint(model, sum(values(plist[d])) == 1)
    end
    for ti in 1:2
        down = Set(get(inst.down, T[ti], Int[]))
        for a in 1:m
            a in down && continue
            @constraint(model, load[ti][a] <= inst.cap[a] * U)
        end
    end
    @constraint(model, budget <= κ - used_fixed)
    @objective(model, Min, U)
    optimize!(model)
    nbin = sum(length, plist)
    if !has_values(model)
        return (chosen = start, status = string(termination_status(model)), time = solve_time(model), nodes = node_count(model), nbin = nbin, bound = -Inf)
    end
    chosen = [copy(start[1]), copy(start[2])]
    for d in 1:D
        free[d] || continue
        (k, l) = first(kl for (kl, x) in plist[d] if value(x) > 0.5)
        chosen[1][d] = pool[d][k]; chosen[2][d] = pool[d][l]
    end
    (chosen = chosen, status = string(termination_status(model)), time = solve_time(model), nodes = node_count(model), nbin = nbin,
     bound = objective_bound(model))
end
