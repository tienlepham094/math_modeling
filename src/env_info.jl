# In thông tin máy và phần mềm, dùng cho mục "Môi trường chạy" của báo cáo.
# Chạy:  julia --project=. src/env_info.jl
using JuMP, HiGHS, Graphs, JSON3

println("Thông tin môi trường chạy")
println("  Hệ điều hành : ", Sys.KERNEL, " ", Sys.MACHINE,
        isfile("/.dockerenv") ? " (trong Docker container)" : "")
println("  CPU          : ", Sys.cpu_info()[1].model, " (", Sys.CPU_THREADS, " luồng)")
println("  RAM          : ", round(Sys.total_memory() / 2^30, digits = 1), " GB tổng, ",
        round(Sys.free_memory() / 2^30, digits = 1), " GB đang trống")
println("  Julia        : ", VERSION)
println("  JuMP         : ", pkgversion(JuMP))
println("  HiGHS.jl     : ", pkgversion(HiGHS))
println("  HiGHS solver : ", HiGHS.Highs_version() |> unsafe_string)
println("  Graphs.jl    : ", pkgversion(Graphs))
println("  JSON3.jl     : ", pkgversion(JSON3))
println()
free_gb = Sys.free_memory() / 2^30
# Số đo RAM cao nhất trên máy B (28/10/2026): 3.7–4.0 GB cho mỗi triệu biến (Step 6), 3.4 GB (Step 9), cộng ~1.5 GB cố định.
println("Gợi ý MAX_VARS cho máy này (khoảng 4 GB RAM cho mỗi triệu biến, cộng 1.5 GB cố định): ",
        round(Int, max(free_gb * 2^30 / 1e9 - 1.5, 0) / 4.0 * 1e6))
