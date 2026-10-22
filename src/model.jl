# =====================================================================
# Step 5 và Step 8: mô hình MILP, Step 6 và Step 9: giải và lấy kết quả
# =====================================================================
using JuMP, HiGHS

# rs = [r0]      -> Step 5 (chỉ t = 0, không có ràng buộc budget)
# rs = [r0, r1]  -> Step 8 (t = 0 và t = 1, có ràng buộc budget (4))
function build_model(inst::Instance, rs::Vector{SplitCoef}; time_limit = 1800.0, seed = 0, silent = true,
                     aggregate = false, warm_start = true, heuristic_effort = 0.05)
    D = length(inst.src)
    T = 0:length(rs)-1
    model = Model(HiGHS.Optimizer)
    set_time_limit_sec(model, time_limit)
    set_attribute(model, "random_seed", seed)
    set_attribute(model, "mip_heuristic_effort", heuristic_effort)   # mặc định của HiGHS là 0.05
    silent && set_silent(model)

    @variable(model, U >= 0)                       # MLU cần cực tiểu
    S = [collect(keys(r)) for r in rs]             # S[t+1] = các segment (i,j) có đường đi trong G_t
    # x[t+1][d, p] = 1 nếu đường segment của demand d tại chu kỳ t dùng segment S[t+1][p]
    x = [@variable(model, [1:D, 1:length(S[t+1])], Bin, base_name = "x$t") for t in T]

    for t in T
        St, xt, r = S[t+1], x[t+1], rs[t+1]
        out_of = [Int[] for _ in 1:inst.n]
        in_to  = [Int[] for _ in 1:inst.n]
        for (p, (i, j)) in enumerate(St)
            push!(out_of[i], p); push!(in_to[j], p)
        end

        # (1) bảo toàn luồng trên đồ thị segment
        for d in 1:D, i in 1:inst.n
            rhs = i == inst.src[d] ? 1 : (i == inst.dst[d] ? -1 : 0)
            @constraint(model, sum(xt[d, p] for p in out_of[i]) - sum(xt[d, p] for p in in_to[i]) == rhs)
        end

        # (2) số segment tối đa
        @constraint(model, [d in 1:D], sum(xt[d, :]) <= inst.maxSeg)

        # (3) tải của mỗi cung còn sống <= U * c(a)
        load = [AffExpr(0.0) for _ in 1:inst.m]
        if aggregate
            # Viết tương đương: f[p] = tổng lưu lượng đi trên segment p (mọi demand cộng lại),
            # rồi tải = Σ_p r(p,a) f[p]. Ít hệ số hơn rất nhiều nên LP giải nhanh hơn.
            f = @variable(model, [1:length(St)], lower_bound = 0, base_name = "f$t")
            for p in eachindex(St)
                @constraint(model, f[p] == sum(inst.vol[d, t+1] * xt[d, p] for d in 1:D))
            end
            for (p, seg) in enumerate(St), (a, ratio) in r[seg]
                add_to_expression!(load[a], ratio, f[p])
            end
        else
            for (p, seg) in enumerate(St), (a, ratio) in r[seg], d in 1:D
                add_to_expression!(load[a], ratio * inst.vol[d, t+1], xt[d, p])
            end
        end
        for a in alive_arcs(inst, t)
            @constraint(model, load[a] <= U * inst.cap[a])
        end

        # (4) budget: tổng |x^t - x^{t-1}| <= κ(t), tuyến tính hoá bằng biến y >= 0
        if t >= 1
            idx_prev = Dict(seg => p for (p, seg) in enumerate(S[t]))
            idx_now  = Dict(seg => p for (p, seg) in enumerate(St))
            changes = AffExpr(0.0)
            for seg in union(S[t], St), d in 1:D
                xnow  = haskey(idx_now, seg)  ? xt[d, idx_now[seg]]     : 0.0  # segment không có đường đi => x = 0
                xprev = haskey(idx_prev, seg) ? x[t][d, idx_prev[seg]]  : 0.0
                y = @variable(model, lower_bound = 0)
                @constraint(model, y >= xnow - xprev)
                @constraint(model, y >= xprev - xnow)
                add_to_expression!(changes, y)
            end
            @constraint(model, changes <= inst.budget[t])
        end
    end

    @objective(model, Min, U)
    warm_start && set_no_waypoint_start!(model, inst, rs, x, S)
    return model, x, S
end

# Nghiệm khởi đầu: mọi demand đi thẳng s -> t (không waypoint), ở mọi chu kỳ.
# Nghiệm này luôn khả thi (dùng 0 thay đổi budget), nên solver có ngay một cận trên.
# Nhờ vậy dù hết giờ, instance nào cũng có nghiệm và gap để báo cáo.
function set_no_waypoint_start!(model, inst::Instance, rs, x, S)
    D = length(inst.src)
    mlu = 0.0
    for t in 0:length(rs)-1
        idx = Dict(seg => p for (p, seg) in enumerate(S[t+1]))
        set_start_value.(x[t+1], 0.0)
        load = zeros(inst.m)
        for d in 1:D
            seg = (inst.src[d], inst.dst[d])
            set_start_value(x[t+1][d, idx[seg]], 1.0)
            for (a, ratio) in rs[t+1][seg]
                load[a] += ratio * inst.vol[d, t+1]
            end
        end
        mlu = max(mlu, maximum(load ./ inst.cap))
    end
    set_start_value(model[:U], mlu)
    # các biến phụ (y, f) để solver tự hoàn thiện
    return mlu
end

# Gọi optimize! và thu các thông tin cần ghi vào bảng kết quả
function solve_and_report(model)
    optimize!(model)
    st = termination_status(model)
    feasible = primal_status(model) == FEASIBLE_POINT
    status = st == OPTIMAL ? "Optimal" :
             st in (INFEASIBLE, INFEASIBLE_OR_UNBOUNDED) ? "Infeasible" :
             feasible ? "Not Optimal" : string(st)
    obj = feasible ? objective_value(model) : NaN
    lb  = objective_bound(model)
    gap = status == "Optimal" ? 0.0 : 1.0 - lb / obj         # công thức của đề
    return (status = status, obj = obj, lb = lb, gap = gap,
            cpu = solve_time(model), nodes = node_count(model))
end

# Đọc danh sách waypoint của demand d tại chu kỳ t từ nghiệm.
# Dùng đường đi Euler (Hierholzer) vì đường segment có thể đi qua một nút nhiều lần.
function waypoints(inst::Instance, x, S, d::Int, t::Int)
    succ = Dict{Int,Vector{Int}}()
    for (p, (i, j)) in enumerate(S[t+1])
        value(x[t+1][d, p]) > 0.5 && push!(get!(succ, i, Int[]), j)
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
    reverse!(walk)                                  # walk = s, w1, ..., t
    leftover = sum(length, values(succ); init = 0)  # > 0 nghĩa là có chu trình rời
    return walk[2:end-1], leftover
end
