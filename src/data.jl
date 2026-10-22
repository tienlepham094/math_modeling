# =====================================================================
# Step 2, 3, 4, 7: đọc dữ liệu, dựng đồ thị G_t, tính split coefficients r
# =====================================================================
using JSON3, Graphs

# ---------------------------------------------------------------------
# Step 4: cấu trúc chứa toàn bộ dữ liệu của một instance
# ---------------------------------------------------------------------
struct Instance
    name::String
    n::Int                        # số nút |V|
    m::Int                        # số cung |A|
    from::Vector{Int}             # from[a], to[a]: nút đầu/cuối của cung a (chỉ số Julia 1..n)
    to::Vector{Int}
    metric::Vector{Float64}       # ω(a)
    cap::Vector{Float64}          # c(a)
    link_id::Vector{Int}          # ID của cung a trong file JSON
    node_id::Vector{Int}          # ID của nút k trong file JSON
    src::Vector{Int}              # nguồn của demand d
    dst::Vector{Int}              # đích của demand d
    vol::Matrix{Float64}          # vol[d, t+1] = ν(d, t)
    maxSeg::Int
    budget::Dict{Int,Int}         # t => κ(t)
    down::Dict{Int,Vector{Int}}   # t => các cung (chỉ số Julia) bị tắt
end

function read_instance(prefix::AbstractString)
    net = JSON3.read(read(prefix * "-net.json", String))
    tm  = JSON3.read(read(prefix * "-tm.json", String))
    sc  = JSON3.read(read(prefix * "-scenario.json", String))

    # ID trong JSON không nhất thiết là 0,1,2,... theo thứ tự => tạo bảng ánh xạ
    node_id = [Int(nd["id"]) for nd in net["nodes"]]
    vtx = Dict(id => k for (k, id) in enumerate(node_id))          # JSON id -> 1..n
    links = net["links"]
    link_id = [Int(l["id"]) for l in links]
    arc = Dict(id => a for (a, id) in enumerate(link_id))          # JSON id -> 1..m

    dem = tm["demands"]
    h = Int(tm["num_time_slots"])
    vol = [Float64(d["v"][k]) for d in dem, k in 1:h]

    down = Dict{Int,Vector{Int}}()
    for iv in sc["interventions"]
        append!(get!(down, Int(iv["t"]), Int[]), [arc[Int(l)] for l in iv["links"]])
    end
    budget = Dict(Int(b["t"]) => Int(b["value"]) for b in sc["budget"])

    Instance(basename(prefix), length(node_id), length(links),
        [vtx[Int(l["from"])] for l in links], [vtx[Int(l["to"])] for l in links],
        [Float64(l["metric"]) for l in links], [Float64(l["capacity"]) for l in links],
        link_id, node_id,
        [vtx[Int(d["s"])] for d in dem], [vtx[Int(d["t"])] for d in dem], vol,
        Int(sc["max_segments"]), budget, down)
end

# ---------------------------------------------------------------------
# Step 2 / Step 7: đồ thị G_t (bỏ các cung bị tắt) và ma trận trọng số
# ---------------------------------------------------------------------
alive_arcs(inst::Instance, t::Int) = setdiff(1:inst.m, get(inst.down, t, Int[]))

function graph_at(inst::Instance, t::Int)
    g = SimpleDiGraph(inst.n)
    W = fill(Inf, inst.n, inst.n)                  # W[u,v] = ω của cung u->v
    for a in alive_arcs(inst, t)
        add_edge!(g, inst.from[a], inst.to[a])
        W[inst.from[a], inst.to[a]] = inst.metric[a]
    end
    return g, W
end

# Khoảng cách và số đường ngắn nhất giữa mọi cặp nút (calculating_r.pdf, mục 1)
function all_pairs_shortest_data(g, W)
    n = nv(g)
    d = fill(Inf, n, n)
    sigma = zeros(Float64, n, n)
    for i in vertices(g)
        st = dijkstra_shortest_paths(g, i, W; allpaths = true)
        d[i, :] .= st.dists
        sigma[i, :] .= st.pathcounts
    end
    return d, sigma
end

# ---------------------------------------------------------------------
# Step 3: split coefficients.
# Kết quả: r[(i,j)] = danh sách (a, r(i,j,a,t)) với r > 0.
# Cặp (i,j) không có trong r  <=>  từ i không đi được tới j.
# ---------------------------------------------------------------------
const SplitCoef = Dict{Tuple{Int,Int},Vector{Tuple{Int,Float64}}}

# Cách 1 (calculating_r.pdf): tỉ lệ số đường ngắn nhất đi qua cung a
function r_pathcount(inst::Instance, t::Int)
    g, W = graph_at(inst, t)
    d, sigma = all_pairs_shortest_data(g, W)
    A = alive_arcs(inst, t)
    r = SplitCoef()
    for i in 1:inst.n, j in 1:inst.n
        (i == j || isinf(d[i, j])) && continue
        lst = Tuple{Int,Float64}[]
        for a in A
            u, v = inst.from[a], inst.to[a]
            if d[i, u] + inst.metric[a] + d[v, j] == d[i, j]
                push!(lst, (a, sigma[i, u] * sigma[v, j] / sigma[i, j]))
            end
        end
        r[(i, j)] = lst
    end
    return r
end

# Cách 2 (đề bài, Table 2): ECMP chia đều luồng TẠI MỖI NÚT cho các cung ra trong FG(i,j)
function r_ecmp(inst::Instance, t::Int)
    g, W = graph_at(inst, t)
    d, _ = all_pairs_shortest_data(g, W)
    A = alive_arcs(inst, t)
    out = [Int[] for _ in 1:inst.n]
    for a in A
        push!(out[inst.from[a]], a)
    end
    r = SplitCoef()
    flow = zeros(inst.n)
    for j in 1:inst.n
        # nh[u] = các cung ra của u nằm trên một đường ngắn nhất u -> j
        nh = [[a for a in out[u] if d[u, j] == inst.metric[a] + d[inst.to[a], j]] for u in 1:inst.n]
        order = sortperm(d[:, j]; rev = true)      # xa j trước, gần j sau
        for i in 1:inst.n
            (i == j || isinf(d[i, j])) && continue
            fill!(flow, 0.0); flow[i] = 1.0
            ratio = Dict{Int,Float64}()
            for u in order
                (u == j || flow[u] == 0.0) && continue
                share = flow[u] / length(nh[u])
                for a in nh[u]
                    ratio[a] = get(ratio, a, 0.0) + share
                    flow[inst.to[a]] += share
                end
            end
            r[(i, j)] = [(a, v) for (a, v) in ratio]
        end
    end
    return r
end
