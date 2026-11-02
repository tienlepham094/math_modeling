# Hướng dẫn làm project Orange từng step

File này đi qua **từng step** trong `readme.txt` của giảng viên. Với mỗi step, file ghi rõ năm điều: **mục tiêu**, **cần hiểu gì**, **lệnh cần chạy**, **kết quả phải ra**, và **viết gì vào báo cáo**.

- **Chưa hiểu bài toán?** Đọc [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md) trước. File đó giải thích từng khái niệm, ký hiệu và công thức bằng ví dụ số.
- **Chưa cài gì?** Làm theo [CAI_DAT_VA_CHAY.md](CAI_DAT_VA_CHAY.md). Trong file này, mọi lệnh đều có dạng `scripts/run.sh …`. Nếu dùng Docker thì thay bằng `docker run --rm -v "$PWD/results:/app/results" orange-tasr …`.

**Mục lục**

0. [Tổng quan: phải nộp gì](#0-tổng-quan-phải-nộp-gì)
1. [Step 1: đọc hiểu đề](#step-1-đọc-hiểu-đề)
2. [Step 2: dựng đồ thị G tại t = 0](#step-2-dựng-đồ-thị-g-tại-t--0)
3. [Step 3: tính r(i,j,a,0)](#step-3-tính-rija0)
4. [Step 4: phần Data](#step-4-phần-data)
5. [Step 5: mô hình chỉ cho t = 0](#step-5-mô-hình-chỉ-cho-t--0)
6. [Step 6: thí nghiệm t = 0, giới hạn 1800 s](#step-6-thí-nghiệm-t--0-giới-hạn-1800-s)
7. [Step 7: đồ thị và tham số tại t = 1](#step-7-đồ-thị-và-tham-số-tại-t--1)
8. [Step 8: mô hình hai chu kỳ có budget](#step-8-mô-hình-hai-chu-kỳ-có-budget)
9. [Step 9: thí nghiệm hai chu kỳ, giới hạn 3600 s](#step-9-thí-nghiệm-hai-chu-kỳ-giới-hạn-3600-s)
10. [Kiểm tra nghiệm](#10-kiểm-tra-nghiệm)
11. [Viết báo cáo](#11-viết-báo-cáo)
12. [Checklist](#12-checklist)

---

## 0. Tổng quan: phải nộp gì

**Một báo cáo tối đa 10 trang**, gồm ba phần:

1. **Introduction**: bối cảnh, động lực, mô tả bài toán.
2. **Mathematical model**: dữ liệu, biến, mục tiêu, ràng buộc, giải thích chi tiết.
3. **Numerical experiments**:
   - mô tả instance và môi trường chạy;
   - bảng kết quả gồm CPU time, Gap, số nút branch-and-bound;
   - mỗi con số là trung bình trên 10 lần chạy.

Các step dẫn tới từng phần của báo cáo như sau:

| Step | Làm gì | File code | Phục vụ phần nào của báo cáo |
|---|---|---|---|
| 1 | Đọc hiểu đề | | Introduction |
| 2 | Dựng đồ thị G | `src/data.jl` (`graph_at`), notebook Pluto | Model: Data |
| 3 | Tính r | `src/data.jl` (`r_ecmp`, `r_pathcount`) | Model: Data |
| 4 | Đọc tham số từ JSON | `src/data.jl` (`read_instance`) | Model: Data |
| 5 | Mô hình t = 0 | `src/model.jl` (`build_model` với `[r0]`) | Model |
| 6 | Chạy SetA t = 0 | `src/run_experiments.jl 6` | Experiments, bảng 1 |
| 7 | Đồ thị và r tại t = 1 | `src/data.jl` (`graph_at(inst, 1)`, `r_ecmp(inst, 1)`) | Model: Data |
| 8 | Mô hình hai chu kỳ có budget | `src/model.jl` (`build_model` với `[r0, r1]`) | Model |
| 9 | Chạy SetA t = 0, 1 | `src/run_experiments.jl 9` | Experiments, bảng 2 |

Một lệnh kiểm tra Step 2, 3, 5, 7, 8 cùng lúc trên ví dụ toy của đề:

```bash
scripts/run.sh test        # phải in "TẤT CẢ ĐẠT"
```

---

## Step 1: đọc hiểu đề

**Mục tiêu.** Hiểu bài toán đủ rõ để tự giải thích lại cho người khác.

**Cần làm.**

1. Đọc [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), từ Phần 1 đến Phần 8.
2. Đọc đề gốc `Challenge_Orange_ROADEF_2026_Subject.pdf`, mục 2–4 (khoảng 6 trang).
3. Tự tính lại ví dụ toy bằng tay: MLU = 0.4375 khi không có waypoint, và 0.375 với waypoint v4.

**Tự kiểm tra:** trả lời được 8 câu ở Phần 12 của [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md).

**Viết vào báo cáo:** phần Introduction (bản nháp đã có ở `report/report.tex`, mục 1).

---

## Step 2: dựng đồ thị G tại t = 0

**Mục tiêu.** Đọc file `*-net.json` và có đồ thị `G` trong Julia.

**Cần hiểu.**

- File net gồm `nodes` (id, name) và `links` (id, from, to, metric, capacity). Mỗi link là **một cung có hướng**.
- **Bẫy 1: ID trong JSON không nhất thiết là 0, 1, 2, … theo thứ tự.** Ví dụ `setA-14` liệt kê nút theo thứ tự 249, 248, …, 0. Julia lại đánh số từ 1. Vì vậy code tạo **bảng ánh xạ** `id JSON → số thứ tự Julia` (`read_instance` trong `src/data.jl`).
- **Bẫy 2:** 10 instance có cờ `"multigraph": true` (05, 06, 08, 10, 12, 13, 14, 16, 17, 19).
  - Notebook `json_to_graph_pluto_v2.jl` **báo lỗi** với các file này, nên phải mở bằng `json_to_multigraph_pluto.jl`.
  - Đã kiểm tra: **không instance nào thật sự có cung song song**. Vì vậy code của project dựng `SimpleDiGraph` cho mọi instance.

**Lệnh.**

```bash
scripts/run.sh pluto          # mở http://localhost:1234, chọn notebook, sửa biến json_file rồi chạy
```

Trong code của project: `g, W = graph_at(inst, 0)` trả về đồ thị `g` (Graphs.jl) và ma trận trọng số `W`.

**Kết quả phải ra:**

| Instance | Số nút | Số cung |
|---|---|---|
| toy | 7 | 22 |
| setA-01 | 20 | 80 |
| setA-09 | 150 | 750 |
| setA-20 | 400 | 2000 |

Bảng đầy đủ 20 instance có trong `report/report.tex` (Bảng 2).

---

## Step 3: tính r(i,j,a,0)

**Mục tiêu.** Với **mọi cặp nút** `(i, j)` và **mọi cung** `a`, tính `r(i,j,a,0)`: tỉ lệ của 1 đơn vị luồng gửi từ i tới j (đi đường ngắn nhất) chạy qua cung a. Giải thích chi tiết kèm ví dụ số ở [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), Phần 4.

**Cách của `calculating_r.pdf`** (hàm `r_pathcount`):

1. Chạy Dijkstra từ mọi nút. Hàm `dijkstra_shortest_paths(g, i, W; allpaths = true)` cho cả `dists` (độ dài ngắn nhất `d`) và `pathcounts` (số đường ngắn nhất `σ`).
2. Cung `a = (u,v)` nằm trên đường ngắn nhất từ i tới j khi và chỉ khi `d[i,u] + ω(a) + d[v,j] = d[i,j]`.
3. Khi đó `r = σ[i,u] · σ[v,j] / σ[i,j]`.

**Cách của đề, ECMP** (hàm `r_ecmp`). Với mỗi đích j:

1. Đặt 1 đơn vị luồng tại i.
2. Duyệt các nút từ xa j tới gần j.
3. Tại mỗi nút, **chia đều** lượng luồng đang có cho các cung đi đúng hướng ngắn nhất.

**⚠ Hai cách cho kết quả KHÁC nhau** khi các đường ngắn nhất tách ra rồi nhập lại. Trên toy, với demand (v0, v5):

```
calculating_r.pdf (đếm đường):  a1,3 = 0.333  a1,4 = 0.667  a3,5 = 0.667
ECMP của đề:                    a1,3 = 0.5    a1,4 = 0.5    a3,5 = 0.75   ← khớp Table 2 của đề
```

**Quyết định của project:**

- Cài **cả hai** cách, để cho thấy đã làm theo hướng dẫn của giảng viên.
- **Dùng ECMP cho mô hình**, vì nó khớp với định nghĩa và Table 2 của đề.
- Trên SetA, hai cách cho cùng giá trị ở mọi cặp nút, trừ 1 cặp ở setA-18 và 1 cặp ở setA-20, vì trong SetA hầu như không có hai đường cùng ngắn nhất. Vì vậy **kết quả thí nghiệm gần như không phụ thuộc vào cách chọn**.
- Nên hỏi giảng viên một câu cho chắc.

**Cách lưu.** Chỉ lưu phần khác 0: `r[(i,j)]` là danh sách các cặp `(cung, giá trị)`. Cặp `(i,j)` không có trong `r` nghĩa là từ i không đi được tới j.

**Kiểm tra:** `scripts/run.sh test` in ra cả hai bảng r và kiểm tra ECMP khớp Table 2.

**Viết vào báo cáo:** cách tính r, và 2–3 câu về sự khác biệt giữa hai cách (đã có trong `report.tex`, mục 2.2).

---

## Step 4: phần Data

**Mục tiêu.** Đọc 3 file JSON thành mọi tham số mô hình cần.

| Tham số | Ký hiệu | File | Trường JSON |
|---|---|---|---|
| Đồ thị, trọng số | `G`, `ω(a)` | `*-net.json` | `nodes`, `links[].metric` |
| Dung lượng | `c(a)` | `*-net.json` | `links[].capacity` |
| Split coefficient | `r(i,j,a,0)` | **tính** (Step 3) | |
| Demand | `s_d`, `t_d` | `*-tm.json` | `demands[].s`, `demands[].t` |
| Lưu lượng | `ν(d,0)` | `*-tm.json` | `demands[].v[0]` (phần tử đầu là t = 0) |
| Số segment tối đa | `maxSeg` | `*-scenario.json` | `max_segments` |
| Cung bị tắt, budget | `q(1)`, `κ(1)` | `*-scenario.json` | `interventions`, `budget` (dùng ở Step 7–8) |

**Định dạng 3 file** (ví dụ toy, có trong thư mục `toy/`):

`toy-net.json`:

```json
{ "directed": true, "multigraph": false,
  "nodes": [ {"name": "A", "id": 0}, {"name": "B", "id": 1}, ... ],
  "links": [ {"id": 0, "from": 0, "to": 1, "metric": 100, "capacity": 400}, ... ] }
```

`toy-tm.json`: ID của demand là **vị trí của nó trong danh sách**, bắt đầu từ 0.

```json
{ "num_time_slots": 2,
  "demands": [ { "v": [50.0, 100.0], "s": 0, "t": 5 },
               { "v": [100.0, 50.0], "s": 2, "t": 5 } ] }
```

`toy-scenario.json`: t = 0 **không xuất hiện** trong file, vì tại t = 0 không có cung nào bị tắt và budget là vô hạn.

```json
{ "max_segments": 4,
  "budget":        [ { "t": 1, "value": 20 } ],
  "interventions": [ { "t": 1, "links": [2, 3] } ] }
```

**Code:** `inst = read_instance("setA/setA-01")` trả về `struct Instance`, với các trường `n`, `m`, `from`, `to`, `metric`, `cap`, `src`, `dst`, `vol[d, t+1]`, `maxSeg`, `budget`, `down`.

**Lưu ý chỉ số:** Julia đánh số từ 1, nên `vol[d, 1]` là ν(d, 0) và `vol[d, 2]` là ν(d, 1).

**Viết vào báo cáo:** bảng tham số ở trên (đã có trong `report.tex`, Bảng 1).

---

## Step 5: mô hình chỉ cho t = 0

**Mục tiêu.** Viết MILP gồm ràng buộc (1), (2), (3) của đề, mục tiêu là cực tiểu MLU. Mỗi công thức được giải thích từng dòng ở [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), Phần 8.

**Tóm tắt mô hình:**

```
Biến:      x[d,i,j] ∈ {0,1}   (demand d có dùng segment (i,j) không)
           U ≥ 0              (MLU)
Mục tiêu:  min U
(1)  với mọi d, i:  (số segment ra khỏi i) − (số segment vào i) = 1 nếu i = s_d, −1 nếu i = t_d, 0 nếu khác
(2)  với mọi d:     Σ_{i,j} x[d,i,j] ≤ maxSeg
(3)  với mọi cung a: Σ_d Σ_{i,j} r(i,j,a,0) · ν(d,0) · x[d,i,j] ≤ U · c(a)
```

**Code:** `model, x, S = build_model(inst, [r0])` trong `src/model.jl`. Mỗi ràng buộc trong code có chú thích (1), (2), (3) tương ứng. Bảng đối chiếu từng dòng code với công thức ở [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), Phần 11.

**Hai chi tiết cài đặt:**

- Chỉ tạo biến cho segment `(i,j)` có đường đi từ i tới j. Segment không có đường đi thì không dùng được, nên coi như x = 0.
- Solver được cho **nghiệm khởi đầu "không waypoint"** (mọi demand đi thẳng s → t). Nghiệm này luôn hợp lệ, nên kể cả khi hết giờ solver vẫn có nghiệm và gap để báo cáo.

**Kết quả trên toy** (lệnh `scripts/run.sh test`): `status = Optimal`, `obj = 0.375`, waypoint của d0 là `[4]`, đúng với Figure 4 của đề.

---

## Step 6: thí nghiệm t = 0, giới hạn 1800 s

**Mục tiêu.** Chạy mô hình Step 5 trên 20 instance SetA và lập bảng.

**Lệnh:**

```bash
scripts/run.sh step6 all           # hoặc vài instance: scripts/run.sh step6 1 2 3
scripts/run.sh status              # xem tóm tắt
scripts/run.sh tables              # sinh bảng LaTeX cho báo cáo
```

**Các cột của bảng và nơi lấy:**

| Cột | Ý nghĩa | Lệnh JuMP |
|---|---|---|
| \|V\|, \|A\|, \|D\| | Số nút, số cung, số demand | từ dữ liệu |
| Obj | MLU tốt nhất tìm được (UB) | `objective_value(model)` |
| CPU time | Thời gian của **riêng** `optimize!` | `solve_time(model)` |
| Status | Optimal / Not Optimal / Infeasible | `termination_status(model)` |
| Gap | `1 − LB/UB` khi chưa tối ưu | `objective_bound(model)` cho LB |
| Số nút B&B | Kích thước cây branch-and-bound | `node_count(model)` |

**Các thiết lập (cần ghi vào báo cáo, mục "Môi trường và thiết lập"):**

- **Thời gian:** `set_time_limit_sec(model, 1800)`.
- **Nghiệm khởi đầu:** "không waypoint", luôn khả thi.
- **`mip_heuristic_effort = 0.3`** (mặc định của HiGHS là 0.05).
  - Lý do: log solver cho thấy cận dưới LP gần như luôn bằng giá trị tối ưu ngay từ đầu, còn phần chậm là *tìm nghiệm nguyên tốt*.
  - Trên setA-02: với mức mặc định, solver chưa xong sau 600 s; với 0.3, solver chứng minh tối ưu sau 395 s.
- **Số lần chạy:**
  - HiGHS là *deterministic*, nên mỗi lần chạy dùng một `random_seed` khác (0, 1, …, 9).
  - Instance giải tối ưu dưới 300 s: chạy tối đa 10 lần và lấy trung bình. Gặp lần nào chạy ≥ 300 s thì dừng lặp.
  - Instance chạm time limit: chạy 1 lần, vì 10 × 1800 s là quá lâu.
- **Giới hạn kích thước:** instance có hơn `MAX_VARS` biến (mặc định 5 triệu) không được dựng, ghi "Too large".
- **Chốt chặn cứng:** quá `HARD_LIMIT` (mặc định 2 × 1800 + 3600 = 7200 s) thì tiến trình bị dừng, ghi "Killed".

**Thử nghiệm không thành công (cũng nên ghi):** viết lại ràng buộc tải bằng biến gộp `f[p] = Σ_d ν_d x[d,p]` cho ít hệ số hơn, nhưng HiGHS lại giải **chậm hơn**. Vì vậy code giữ dạng gốc của đề (`aggregate = false`).

**Instance nào chạy được** (chi tiết ở [CAI_DAT_VA_CHAY.md](CAI_DAT_VA_CHAY.md), mục 1):

| Instance | Biến nhị phân (t = 0) | Máy 16 GB |
|---|---|---|
| 01 – 05 | 15 nghìn – 990 nghìn | chạy được |
| 06, 08, 09 | 4.5 – 5 triệu | chạy được, nhưng cần khoảng 7 GB RAM |
| 07, 10 – 20 | 7.9 triệu – 958 triệu | **không** |

Đây không phải lỗi của bạn. Đây là bản chất của mô hình: số biến tăng theo `|D| × n²`. Paper của nhóm ra đề cũng chỉ thử mô hình này trên mạng tối đa 50 nút.

**Kết quả và cách phân tích:** [PHAN_TICH_KET_QUA.md](PHAN_TICH_KET_QUA.md).

---

## Step 7: đồ thị và tham số tại t = 1

**Mục tiêu.** Tại t = 1 có cung bị tắt (`interventions`). Cần dựng `G_1` và tính lại `r(·,·,·,1)`.

**Cần hiểu.**

- `G_1` = `G` bỏ đi các cung trong `q(1)`. Trong SetA, mỗi instance tắt **đúng 1 cung**. Trong toy, tắt 2 cung là a1,3 và a1,4.
- Đường ngắn nhất thay đổi, nên **phải tính lại r cho mọi cặp nút**.
- Lưu lượng `ν(d,1)` lấy từ phần tử thứ hai của `v`. Lưu lượng cũng **thay đổi** giữa hai chu kỳ.

**Code:** `r1 = r_ecmp(inst, 1)`. Hàm `graph_at(inst, 1)` tự bỏ các cung bị tắt.

**Kết quả phải ra** (lệnh `scripts/run.sh test` có kiểm tra):

- Trên toy, demand v0 → v5 tại t = 1 phải đi qua a0,2.
- Không cặp nút nào dùng cung bị tắt.

---

## Step 8: mô hình hai chu kỳ có budget

**Mục tiêu.** Một mô hình cho cả t = 0 và t = 1:

- Mỗi chu kỳ có bộ biến x riêng và ràng buộc (1)–(3) riêng, dùng r và ν của chu kỳ đó.
- **Một U chung**, nên U phải ≥ tải của mọi cung ở cả hai chu kỳ.
- Thêm ràng buộc (4): số thay đổi segment giữa t = 0 và t = 1 không vượt κ(1).

**Ràng buộc (4) và cách tuyến tính hoá** (giải thích đủ 4 trường hợp ở [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), mục 8.7):

```
Σ_d Σ_{i≠j} |x1[d,i,j] − x0[d,i,j]| ≤ κ(1)
   ⇓  thêm biến y ≥ 0
y[d,i,j] ≥ x1[d,i,j] − x0[d,i,j]
y[d,i,j] ≥ x0[d,i,j] − x1[d,i,j]
Σ y ≤ κ(1)
```

Segment có đường đi ở chu kỳ này mà không có ở chu kỳ kia thì coi x = 0 ở chu kỳ không có đường đi.

**Code:** `build_model(inst, [r0, r1])`.

**Kết quả trên toy:** MLU = 0.375, giữ nguyên waypoint nên dùng 0 thay đổi.

**Nhận xét về budget của SetA** (nên đưa vào báo cáo):

- Mỗi demand đổi đường tốn **ít nhất 2 đơn vị budget**.
- Instance 05, 10, 17 có κ = 1, tức **không demand nào được đổi đường**: routing tại t = 1 phải giống hệt t = 0.
- κ = 12–13 nghĩa là tối đa khoảng 6 demand được đổi.

---

## Step 9: thí nghiệm hai chu kỳ, giới hạn 3600 s

- `readme.txt` ghi "only time period 0". Đây gần như chắc chắn là **chép nhầm** từ Step 6, vì Step 9 phải chạy mô hình Step 8 (t = 0 và t = 1). Nên hỏi lại giảng viên.
- Bảng có cùng các cột như Step 6. Obj là MLU **trên cả hai chu kỳ**.
- Mô hình có khoảng **gấp 3 lần** số biến của Step 6 (x0, x1, y), nên chỉ 01–05 chạy được trên máy 16 GB.

```bash
scripts/run.sh step9 all
```

**Hiện tượng cần biết:** với mô hình lớn hơn khoảng 1.5 triệu biến (đã gặp ở Step 9 của setA-04), HiGHS **không trả về được cận dưới nào** và **chạy quá time limit**: 9905 s dù giới hạn 3600 s. Lý do là nó kẹt ở giai đoạn presolve hoặc giải LP gốc, nơi không kiểm tra giới hạn thời gian. Script ghi đúng con số này, và bảng LaTeX đánh dấu `*`. Phân tích ở [PHAN_TICH_KET_QUA.md](PHAN_TICH_KET_QUA.md).

---

## 10. Kiểm tra nghiệm

- Hàm `waypoints(inst, x, S, d, t)` trong `src/model.jl` đọc danh sách waypoint từ nghiệm. Nó đi theo các segment có x = 1, từ nguồn tới đích.
- Một đường segment **được phép đi qua một nút hai lần** (ví dụ `⟨s, a, b, a, t⟩`). Vì vậy hàm dùng thuật toán **đường đi Euler** thay vì chỉ "tìm nút kế tiếp".
- Giá trị trả về thứ hai (`leftover`) > 0 nghĩa là nghiệm có một chu trình rời. Chu trình rời không phải segment path hợp lệ. Chi tiết ở [review.md](review.md), mục 2.3.

---

## 11. Viết báo cáo

**Bản nháp có sẵn:** `report/report.tex` (tiếng Việt, LaTeX). Phần Giới thiệu và Mô hình đã viết đầy đủ. Bảng kết quả được sinh tự động.

**Bạn cần làm:**

1. Điền tên vào `\author{...}`.
2. Khi thí nghiệm xong, chạy `scripts/run.sh tables` để cập nhật bảng.
3. Viết nhận xét ở các chỗ `% TODO`. Gợi ý nội dung ở [PHAN_TICH_KET_QUA.md](PHAN_TICH_KET_QUA.md), mục 5.
4. Biên dịch ra PDF: dùng Overleaf, Docker hoặc LaTeX trên máy (xem [CAI_DAT_VA_CHAY.md](CAI_DAT_VA_CHAY.md), mục 8).
5. **Đọc lại toàn bộ và sửa theo cách hiểu của bạn**, vì giảng viên có thể hỏi về bất kỳ chỗ nào.

**Phân bổ 10 trang gợi ý:**

| Phần | Số trang | Nội dung |
|---|---|---|
| 1. Giới thiệu | 1.5 | Orange và mạng IP/MPLS, nghẽn, Segment Routing, bảo trì và budget, bài toán T-ASR |
| 2. Mô hình | 3 | Dữ liệu (bảng tham số và cách tính r), biến, mục tiêu (min MLU và lex-min), ràng buộc (1)–(4) kèm tuyến tính hoá, ví dụ toy, kích thước mô hình |
| 3. Thí nghiệm | 4 | Bảng instance, môi trường (`scripts/run.sh info`), thiết lập, bảng Step 6, bảng Step 9, nhận xét |
| 4. Kết luận | 0.5 | Điểm mạnh, giới hạn, hướng mở rộng (column generation, tiền xử lý) |
| Tài liệu tham khảo | 0.5 | Xem [survey.md](survey.md) |

---

## 12. Checklist

- [ ] Cài đặt xong, `scripts/run.sh test` in "TẤT CẢ ĐẠT"
- [ ] Step 1: trả lời được 8 câu ở Phần 12 của GIAI_THICH_TU_DAU.md
- [ ] Step 2: mở được notebook Pluto, biết số nút và số cung của vài instance
- [ ] Step 3: hiểu vì sao ECMP cho 0.75 còn cách đếm đường cho 0.667
- [ ] Step 4: hiểu bảng tham số và định dạng 3 file JSON
- [ ] Step 5: hiểu từng ràng buộc; toy cho MLU = 0.375
- [ ] Step 6: có `results/step6.csv`, đủ 20 dòng. setA-06, 08, 09 chạy trên máy Intel bằng code ngày 24/10 (xem PHAN_TICH_KET_QUA.md mục 0.2)
- [ ] Step 7–8: hiểu ràng buộc budget và cách tuyến tính hoá
- [ ] Step 9: có `results/step9.csv`
- [ ] Hỏi giảng viên: cách tính r (Table 2 hay calculating_r.pdf), và lỗi chép ở Step 9
- [ ] Báo cáo: điền tên, cập nhật bảng (`scripts/run.sh tables`), sửa chỗ `[TODO]` về setA-06, 08, 09, ≤ 10 trang (hiện 9), biên dịch ra PDF
