# =====================================================================
# Kiểm tra toàn bộ chương trình trên instance "toy" của đề (7 nút, 2 demand).
# Chạy:  julia --project=. src/test_toy.jl
# In "TẤT CẢ ĐẠT" và thoát với mã 0 nếu mọi kết quả khớp với đề; ngược lại thoát mã 1.
# Nên chạy lệnh này đầu tiên mỗi khi chuyển sang máy mới.
# =====================================================================
include("data.jl")
include("model.jl")

const ROOT = dirname(@__DIR__)
failures = 0
function check(ok::Bool, msg::String)
    global failures
    println(ok ? "  [ĐẠT]      " : "  [KHÔNG ĐẠT] ", msg)
    ok || (failures += 1)
end

inst = read_instance(joinpath(ROOT, "toy", "toy"))
arc(u, v) = findfirst(a -> inst.node_id[inst.from[a]] == u && inst.node_id[inst.to[a]] == v, 1:inst.m)
rval(r, i, j, u, v) = Dict(r[(i + 1, j + 1)])[arc(u, v)]       # i, j, u, v là ID nút trong JSON
name(a) = "a$(inst.node_id[inst.from[a]]),$(inst.node_id[inst.to[a]])"

println("Step 2: đồ thị G tại t = 0")
g, W = graph_at(inst, 0)
check(nv(g) == 7 && ne(g) == 22, "đồ thị có 7 nút và 22 cung (thực tế: $(nv(g)) nút, $(ne(g)) cung)")

println("\nStep 3: hệ số r(v0, v5, a, 0)")
r0 = r_ecmp(inst, 0)
println("  ECMP (cách của đề):         ", join(["$(name(a))=$(round(v, digits = 4))" for (a, v) in sort(r0[(1, 6)])], ", "))
rp = r_pathcount(inst, 0)
println("  đếm đường (calculating_r):  ", join(["$(name(a))=$(round(v, digits = 4))" for (a, v) in sort(rp[(1, 6)])], ", "))
check(rval(r0, 0, 5, 3, 5) ≈ 0.75 && rval(r0, 0, 5, 1, 3) ≈ 0.5 && rval(r0, 0, 5, 6, 5) ≈ 0.25,
      "ECMP khớp Table 2 của đề (a3,5 = 0.75; a1,3 = 0.5; a6,5 = 0.25)")
check(rval(rp, 0, 5, 3, 5) ≈ 2 / 3, "cách đếm đường cho a3,5 = 2/3 (khác Table 2, đúng như phân tích)")
check(length(r0) == 42, "có r cho đủ 7 × 6 = 42 cặp nút (thực tế: $(length(r0)))")

println("\nStep 5: mô hình chỉ t = 0")
model, x, S = build_model(inst, [r0])
res = solve_and_report(model)
println("  ", res)
w0 = Int[inst.node_id[w] for w in waypoints(inst, x, S, 1, 0)[1]]
check(res.status == "Optimal" && isapprox(res.obj, 0.375; atol = 1e-6), "MLU tối ưu = 0.375 (thực tế: $(res.obj))")
println("  waypoint của d0 = $w0, của d1 = $(Int[inst.node_id[w] for w in waypoints(inst, x, S, 2, 0)[1]])")

println("\nStep 7: đồ thị G tại t = 1 (tắt link 2 và 3)")
r1 = r_ecmp(inst, 1)
check(rval(r1, 0, 5, 0, 2) ≈ 1.0 && !haskey(Dict(r1[(1, 6)]), arc(1, 3)),
      "v0 -> v5 phải đi qua a0,2 và không dùng cung bị tắt a1,3")
check(all(a ∉ inst.down[1] for l in values(r1) for (a, _) in l), "không cặp nút nào dùng cung bị tắt")

println("\nStep 8: mô hình t = 0 và t = 1 có budget")
model2, x2, S2 = build_model(inst, [r0, r1]; time_limit = 3600.0)
res2 = solve_and_report(model2)
println("  ", res2)
check(res2.status == "Optimal" && isapprox(res2.obj, 0.375; atol = 1e-6), "MLU tối ưu hai chu kỳ = 0.375 (thực tế: $(res2.obj))")
for t in 0:1, d in 1:2
    println("  t=$t demand $(d-1): waypoint = ", Int[inst.node_id[w] for w in waypoints(inst, x2, S2, d, t)[1]])
end

println()
if failures == 0
    println("TẤT CẢ ĐẠT: chương trình chạy đúng trên máy này.")
else
    println("CÓ $failures KIỂM TRA KHÔNG ĐẠT. Xem các dòng [KHÔNG ĐẠT] ở trên.")
    exit(1)
end
