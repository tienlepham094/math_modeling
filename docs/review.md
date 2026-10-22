# Review: phân tích bài toán T-ASR

Review ngày 21/10/2026. Đối chiếu bản phân tích ban đầu (README.md cũ, commit `26ed990`) và `survey.md` với đề gốc (`Challenge_Orange_ROADEF_2026_Subject.pdf`), tài liệu của giảng viên (`calculating_r.pdf`, `readme.txt`), dữ liệu SetA và hai paper 2026 về T-ASR.

> **Lưu ý khi đọc:** chữ "README" trong file này là **README cũ**, bản phân tích ban đầu, đã được thay bằng bộ tài liệu hiện tại. Các vấn đề nêu ở đây đã được xử lý trong code. Xem bảng "Trạng thái xử lý" ngay dưới đây.

## Trạng thái xử lý (cập nhật 22/10/2026)

| Vấn đề (mục) | Trạng thái | Ở đâu |
|---|---|---|
| 2.1 `calculating_r.pdf` khác đề | Cài cả hai cách; mô hình dùng ECMP của đề; test tự kiểm tra Table 2 | `src/data.jl` (`r_ecmp`, `r_pathcount`), `src/test_toy.jl` |
| 2.2 Mô hình quá lớn | Bỏ qua instance có hơn `MAX_VARS` biến, ghi "Too large". Đã thử gộp luồng: HiGHS **chậm hơn**, nên không dùng | `src/run_experiments.jl`, `src/model.jl` (`aggregate`) |
| 2.3 Vòng lặp trong segment path | `waypoints()` đọc nghiệm bằng đường đi Euler và báo chu trình rời (`leftover`) | `src/model.jl` |
| 2.4 Min-MLU trên hai chu kỳ | Giữ mục tiêu của đề (min U chung); ghi chú trong báo cáo | `report/report.tex` mục 2.4 |
| 2.5 Budget nhỏ (κ = 1) | Phân tích trong báo cáo; chưa cài ràng buộc `z_d` | `docs/PHAN_TICH_KET_QUA.md` mục 4.5 |
| 2.6 Các điểm nhỏ | Cài Julia bằng juliaup; Step 9 ghi chú lỗi chép; 10 lần chạy với seed khác | `docs/CAI_DAT_VA_CHAY.md` |
| **Mới:** HiGHS chạy quá time limit với mô hình lớn hơn khoảng 1.5 triệu biến | Thêm chốt chặn cứng `HARD_LIMIT`; bảng đánh dấu `*`; ghi trạng thái "Killed" | `scripts/run.sh`, `src/make_tables.jl` |
| **Mới:** chạy trên máy khác | Dockerfile, script lệnh chung, cấu hình bằng biến môi trường, tự chạy tiếp khi bị ngắt | `Dockerfile`, `scripts/run.sh` |

## Tóm tắt

- **Phần lớn README đúng với đề**: khái niệm, ví dụ toy (MLU tối ưu 0.375 ở cả t=0 và t=1, đã kiểm tra lại bằng vét cạn), mô hình (1)–(4), cách tuyến tính hoá budget.
- **4 vấn đề cần xử lý trước khi code**:
  1. `calculating_r.pdf` tính `r` **khác đề** (chia theo số đường ngắn nhất, không phải ECMP chia đều tại từng nút). Trên toy sai Table 2. Trên SetA gần như không ảnh hưởng.
  2. **Mô hình quá lớn** cho phần lớn SetA: instance 10–20 cần từ 15 triệu đến 958 triệu biến nhị phân cho mỗi chu kỳ. README ước lượng thấp hơn thực tế nhiều.
  3. **Vòng lặp trong segment path**: đề cho phép waypoint lặp lại và điều này có thể cần cho nghiệm tối ưu, nhưng hàm `waypoints()` trong README sẽ đọc sai. Ngoài ra mô hình (1)–(4) cho phép chu trình rời, làm đếm budget sai.
  4. **Budget rất nhỏ** ở nhiều instance (κ = 1 ở instance 5, 10, 17). Có thể khai thác để thu nhỏ mô hình.
- **Hai paper trong survey (Benhamiche 2026, Jaumard 2026) đều có thật** và đã được đọc full text. Bổ sung các tài liệu và điểm mới ở mục 3.

---

## 1. Kiểm tra dữ liệu SetA

Thống kê từ 60 file JSON (script Python, chạy trên máy):

| Inst | n | m | \|D\| | κ(1) | Inst | n | m | \|D\| | κ(1) |
|---|---|---|---|---|---|---|---|---|---|
| 01 | 20 | 80 | 40 | 51 | 11 | 200 | 1000 | 400 | 89 |
| 02 | 30 | 150 | 45 | 63 | 12 | 200 | 898 | 400 | 13 |
| 03 | 50 | 250 | 20 | 53 | 13 | 200 | 1000 | 2000 | 12 |
| 04 | 50 | 250 | 200 | 44 | 14 | 250 | 1108 | 600 | 13 |
| 05 | 100 | 396 | 100 | **1** | 15 | 250 | 1250 | 600 | 54 |
| 06 | 100 | 500 | 500 | 13 | 16 | 250 | 1452 | 4800 | 13 |
| 07 | 100 | 500 | 800 | 90 | 17 | 300 | 1270 | 2000 | **1** |
| 08 | 150 | 654 | 200 | 13 | 18 | 300 | 1500 | 2000 | 89 |
| 09 | 150 | 750 | 200 | 18 | 19 | 300 | 1998 | 6000 | 13 |
| 10 | 150 | 966 | 1000 | **1** | 20 | 400 | 2000 | 6000 | 90 |

Những điểm chung của cả 20 instance:

- `h = 2` (chỉ có t=0 và t=1), `maxSeg = 6`, và **đúng 1 link bị tắt** tại t=1. Vậy Step 8–9 chính là bài toán SetA đầy đủ.
- Mọi metric > 0, nên thứ tự topo theo `dist` giảm dần trong README mục 6.3 là đúng.
- Mỗi cặp `(s,t)` chỉ có một demand.
- **Các instance gắn cờ `"multigraph": true` (05, 06, 08, 10, 12, 13, 14, 16, 17, 19) thực ra không có cung song song nào.** Chỉ cần notebook multigraph vì cờ này, còn về toán thì xử lý như đồ thị đơn.
- **Đường ngắn nhất gần như luôn duy nhất**: ở mọi instance, chưa tới 0.3% cặp `(u,v)` có nhiều hơn một đường ngắn nhất. Vì vậy `r` gần như luôn bằng 0 hoặc 1, và ECMP hầu như không xảy ra trên SetA.

---

## 2. Các vấn đề, xếp theo mức độ quan trọng

### 2.1 [Cao] `calculating_r.pdf` mâu thuẫn với đề

- **Đề (trang 2, Table 2)**: ECMP chia đều luồng **tại từng nút** cho các cung ra trong `FG(u,v)`.
- **`calculating_r.pdf`**: `r_ija = σ_iu · σ_vj / σ_ij`, tức tỉ lệ **số đường ngắn nhất** đi qua cung `a`. Cách này giả định luồng chia đều cho mọi đường.
- Trên toy, demand `(v0, v5)`:

| Cung | Đề (Table 2) | `calculating_r.pdf` |
|---|---|---|
| a1,3 | 0.5 | 0.333 |
| a1,4 | 0.5 | 0.667 |
| a3,5 | **0.75** | **0.667** |
| a4,3 / a4,6 / a6,5 | 0.25 | 0.333 |

  MLU khi không dùng waypoint là 0.4375 theo đề, nhưng 0.4167 theo `calculating_r.pdf`.
- **Trên SetA**: hai cách cho cùng kết quả ở mọi cặp nút, trừ **1 cặp ở instance 18 và 1 cặp ở instance 20** (lệch 0.167), và hai cặp này không phải cặp `(s,t)` của demand nào. Lý do là đường ngắn nhất hầu như luôn duy nhất.
- **Khuyến nghị**:
  - Dùng cách của đề (README mục 6.3 đã làm đúng như vậy). Solution checker của ban tổ chức cũng sẽ tính theo đề.
  - Giữ Table 2 làm unit test. Nếu cài theo `calculating_r.pdf` (dùng `pathcounts` của Graphs.jl) thì test toy sẽ **không qua**.
  - Trong báo cáo, ghi một câu về sự khác biệt này và lý do chọn cách của đề. Có thể nói thêm rằng trên SetA hai cách gần như trùng nhau.
  - Lưu ý ký hiệu: `calculating_r.pdf` dùng `c_a(t)` cho **độ dài** cung, trong khi đề dùng `c(a)` cho **dung lượng**. Đừng nhầm khi viết báo cáo.

### 2.2 [Cao] Kích thước mô hình

Mô hình trong README tạo một biến `x[d,t,i,j]` cho mọi demand và mọi cặp nút có đường đi. Ràng buộc tải (3) chứa mọi tổ hợp (demand × segment đi qua cung `a`), nên số hệ số khác 0 bằng `|D| × nnz(r)`.

Số liệu đo trên SetA cho **một chu kỳ** (Step 8–9 thì nhân đôi, cộng thêm biến `y`):

| Inst | Biến nhị phân `x` | Hệ số khác 0 trong (3), README | Hệ số khác 0 nếu gộp luồng (xem dưới) |
|---|---|---|---|
| 01 | 15 200 | 37 400 | 16 135 |
| 04 | 490 000 | 1.46 triệu | 0.50 triệu |
| 07 | 7.9 triệu | 28.5 triệu | 8.0 triệu |
| 10 | 22.4 triệu | 116 triệu | 22.5 triệu |
| 13 | 79.6 triệu | 503 triệu | 79.9 triệu |
| 16 | 299 triệu | 2.07 tỉ | 299 triệu |
| 20 | **958 triệu** | **4.30 tỉ** | 958 triệu |

Đánh giá:

- README mục 4.5.4 ghi "khoảng 1.2 triệu biến mỗi chu kỳ" cho `n=50, |D|=500`. Con số đó đúng, nhưng SetA lớn hơn nhiều: instance 10 trở đi **không thể dựng mô hình** trên laptop (JuMP tốn khoảng 100 byte cho mỗi biến, nên 22 triệu biến đã cần vài GB RAM).
- Instance 01–04 giải được. Instance 05–09 dựng được nhưng khó giải tối ưu trong 1800 s.

Khuyến nghị, theo thứ tự nên làm:

1. **Gộp luồng theo segment** (chính xác, không mất tối ưu). Thêm biến liên tục `f[t,i,j] = Σ_d ν(d,t) · x[d,t,i,j]` rồi viết (3) thành `Σ_{(i,j)} r(i,j,a,t) · f[t,i,j] ≤ U · c(a)`. Số hệ số giảm từ `|D|·nnz(r)` xuống `|D|·#cặp + nnz(r)`, ví dụ từ 503 triệu xuống 80 triệu ở instance 13. Không giảm số biến `x`, nhưng dựng và giải nhanh hơn rõ rệt cho instance 05–09.
2. **Bỏ các biến chắc chắn bằng 0**: `x[d,t,i,s_d]` (segment đi vào nguồn) và `x[d,t,t_d,j]` (segment đi ra từ đích). Riêng ở Step 5–6 (một chu kỳ) còn được thêm "mỗi nút đi vào tối đa một lần" (xem 2.3).
3. **Nghiệm khởi đầu**: "không waypoint" (`x[d,t,s_d,t_d] = 1`) luôn khả thi. Truyền nó làm warm start để instance nào cũng có cận trên (UB) và gap.
4. **Instance lớn (10–20)**: nói thẳng trong báo cáo rằng mô hình đầy đủ không dựng được, rồi chạy một **biến thể thu hẹp** và ghi rõ đó là heuristic. Ví dụ tối đa 2 segment (1 waypoint, theo Bhatia 2015): biến `x[d,w]` chỉ còn `|D|·n` (2.4 triệu ở instance 20). Cận dưới của biến thể này **không** phải cận dưới của bài toán gốc.
5. Hướng đúng cho quy mô lớn là **column generation** (CG4SR, Jaumard 2026). Đồ thị segment `K_t` của Jaumard chính là đồ thị `H` trong README. Với hạn nộp 25/10, chỉ nên nhắc hướng này trong phần thảo luận.

### 2.3 [Trung bình] Vòng lặp và chu trình

README mục 4.5.3 viết "chu trình chỉ làm tăng tải nên solver thường không chọn". Điều đó đúng một phần, nhưng thiếu ba điểm sau.

**(a) Segment path có vòng lặp là hợp lệ, và có thể bắt buộc.** Benhamiche et al. (2026, Fig. 1) đưa ví dụ mà nghiệm tối ưu **duy nhất** tại t=1 là `⟨s, b1, b2, b3, b1, t⟩`, với `b1` lặp lại. Lý do: budget chỉ cho phép thêm một waypoint. Khi đó trong `x`, nút `b1` có 2 cung ra.

- **Lỗi trong code README** (`waypoints()`, mục 6.5): `succ = Dict(s[1] => s[2] ...)` chỉ giữ **một** successor cho mỗi nút. Nếu có vòng lặp thì successor bị ghi đè, có thể đọc sai đường hoặc lặp vô hạn.
- **Cách sửa**: đọc nghiệm bằng **đường đi Euler** từ `s` tới `t` (thuật toán Hierholzer) trên các segment có `x = 1`.

**(b) Chu trình rời (không chạm đường s→t) không phải segment path, nhưng (1)–(4) vẫn cho phép.** Chu trình rời cộng thêm tải nên thường không có lợi, **nhưng nó có thể "lách" budget**. Ví dụ, tại t−1 dùng `⟨s,a,b,c,t⟩`. Tại t, mô hình chọn `{(s,t)} ∪ {(a,b),(b,c),(c,a)}`:

- Mô hình đếm 4 thay đổi.
- Đường thật đọc ra là `⟨s,t⟩`, có `dist` = 5. Nếu `κ = 4` thì nghiệm này vi phạm budget mà solver không biết.

Cách xử lý:

- Sau khi giải, kiểm tra xem mọi segment có `x = 1` có nằm trên đường Euler từ `s` không.
- Nếu có chu trình rời, thêm ràng buộc cắt (lazy callback) hoặc ghi rõ trong báo cáo.
- Kiểm tra lại `dist` thật giữa hai chu kỳ bằng code riêng hoặc bằng checker của ban tổ chức.

**(c) Ở Step 5–6 (chỉ t=0), vòng lặp luôn bị trội.** Bỏ vòng lặp thì tải không tăng (Callebaut, De Boeck, Fortz 2023). Vì vậy được phép thêm `Σ_j x[d,j,i] ≤ 1` cho mọi nút `i`, cấm đi vào `s_d` và cấm đi ra từ `t_d`. Mô hình nhỏ hơn và LP relaxation chặt hơn. **Không** dùng các ràng buộc này cho Step 8–9.

### 2.4 [Trung bình] Mục tiêu min-MLU trên cả hai chu kỳ

- `min U` với `λ(a,t) ≤ U` cho mọi `(a,t)` chỉ quan tâm chu kỳ nặng nhất. Thường t=1 nặng hơn (vì thiếu link), nên **routing tại t=0 có thể kém tuỳ ý** mà vẫn là nghiệm "tối ưu".
- Đề dùng lex-min, nên một nghiệm tốt cũng phải tốt ở các tải lớn thứ 2, thứ 3, v.v.
- **Khuyến nghị**:
  - Báo cáo MLU riêng của từng chu kỳ.
  - Có thể thêm pha 2: cố định `U = U*`, rồi cực tiểu `U_0 + U_1` với `U_t = max_a λ(a,t)`. Cách này gần với lex-min hơn.
  - Một lựa chọn khác là giải tuần tự như Jaumard 2026: tối ưu t=0, cố định nghiệm, rồi tối ưu t=1. Khi đó budget tuyến tính mà **không cần biến `y`**: `Σ x̄ + Σ (1 − 2x̄) · x^t ≤ κ`. Đây là heuristic cho bài toán hai chu kỳ, nên chỉ dùng làm warm start hoặc để so sánh.

### 2.5 [Trung bình] Khai thác budget nhỏ

- Mỗi demand đổi đường tốn **ít nhất 2 thay đổi**. Ví dụ `⟨s,i,t⟩ → ⟨s,i,j,i,t⟩` chỉ thêm `(i,j)` và `(j,i)`. Nếu không có vòng lặp thì tốn ít nhất 3. (Chứng minh: `x^t − x^{t−1}` là một luồng vòng khác 0 trên đồ thị không có khuyên, nên có ít nhất 2 phần tử khác 0.)
- **κ = 1 (instance 05, 10, 17)**: không demand nào được đổi đường. Khi đó dùng **một biến `x` chung cho cả hai chu kỳ**, kèm ràng buộc tải của cả t=0 và t=1. Số biến giảm một nửa và không cần `y`.
  - Cần kiểm tra mọi segment được chọn vẫn có đường đi trong `G_1`. Vì chỉ tắt 1 link nên điều này gần như luôn đúng.
- **κ = 12–13**: tối đa 6 demand đổi đường. Có thể thêm biến `z_d ∈ {0,1}` với `x^t_dij − x^{t−1}_dij ≤ z_d`, `x^{t−1}_dij − x^t_dij ≤ z_d` và `Σ_d 2·z_d ≤ κ`. Đây là ràng buộc hợp lệ (đúng với mọi nghiệm khả thi), giúp siết LP relaxation đáng kể.

### 2.6 [Thấp] Các điểm nhỏ khác

- **`readme.txt`**:
  - "Report average on ten runs": Gurobi và HiGHS là deterministic, nên 10 lần chạy giống nhau chỉ khác thời gian. Nên đổi random seed (`Seed` trong Gurobi, `random_seed` trong HiGHS) và ghi rõ điều này trong báo cáo.
  - Step 9 ghi "only time period 0", gần như chắc chắn là chép nhầm. README đã ghi chú điểm này.
- **Notebook multigraph**: gộp các cung song song thành `min metric` và `tổng capacity`. Nếu các cung song song có metric khác nhau thì cách này sai, vì cung metric lớn không mang luồng nhưng capacity vẫn bị cộng vào. SetA không có cung song song nên không ảnh hưởng. Code README tính theo từng cung nên vẫn đúng.
- **README mục 6.1 và 7** hướng dẫn cài Julia bằng `brew`, nhưng máy đang dùng WSL Linux. Nên dùng `curl -fsSL https://install.julialang.org | sh` (juliaup). Julia hiện **chưa được cài**.
- **README mục 6.4**: hàm `build_model` tính `out_of` / `in_to` bằng vòng lặp O(n·|S|) = O(n³) cho mỗi chu kỳ. Với n=400 thì khoảng 64 triệu phép so sánh, vẫn chấp nhận được, nhưng nên dựng một lần bằng cách duyệt `S`.
- **File output mẫu trong đề** (`toy-srpaths.json`, d0 → [3], d1 → [6]) chỉ minh hoạ định dạng. Tính ra nó cho MLU = 0.5, **tệ hơn** không dùng waypoint (0.4375), nên đừng dùng làm kết quả kỳ vọng.

---

## 3. Nghiên cứu: các tài liệu đã đọc và bổ sung cho survey

### 3.1 Benhamiche et al. 2026, *On the T-Adaptive Segment Routing Problem* (arXiv 2609.32896), đã đọc full text

- Nhóm ra đề challenge. Mô hình (1)–(4) trong paper **trùng hoàn toàn** với đề.
- **Độ phức tạp**: T-ASR tổng quát hoá MIN SEGMENT ROUTING, nên NP-khó, khó xấp xỉ và khó theo tham số, ngay cả trên topology rất hạn chế (Bazgan, Chopin, Nichterlein, Richer, INFOCOM 2025). Có thể trích dẫn trong phần Introduction.
- **Mục tiêu lex-min** được giải bằng chuỗi MILP, mỗi MILP tối ưu một hạng của vector tải:
  - **ALEXA** dùng ma trận hoán vị và big-M, với `M = max_a maxSeg · max_ij r(i,j,a,t) · Σ_d ν(d,t) / c(a)`.
  - **STELA** dùng ngưỡng vượt: `λ↓_k = min{z : số tải vượt z ≤ k−1}`. STELA tốt hơn ALEXA ở 109/115 instance.
  - Vì thế bước đầu tiên của cả hai đều chính là `min U` của project này.
- **Vòng lặp có thể bắt buộc** khi có budget (Fig. 1), nên tiền xử lý loại path bị trội của Callebaut 2023 **không áp dụng được** cho đa chu kỳ.
- **Thực nghiệm**: setAP (10–50 nút, 10–50 demand), Gurobi 13, giới hạn 20 phút. Đây là quy mô nhỏ hơn hẳn SetA, nên MILP đầy đủ không giải được SetA lớn là điều bình thường.
- **Tài nguyên**:
  - Instance: <https://doi.org/10.5281/zenodo.19219524>
  - Code STELA/ALEXA (Python + Gurobi): <https://github.com/kaoutarbouaachra/T-ASR-STELA-ALEXA-DRCN>
  - Thư viện networktools: <https://gitlab.com/Orange-OpenSource/network-optimization-tools/networktools>

### 3.2 Jaumard, Tran, Ziazet 2026, *SR-TE with Time-Based Reconfiguration Constraints* (arXiv 2610.04759), đã đọc full text

- **Mục tiêu MLU**, **giải tuần tự theo chu kỳ**: tối ưu t, coi routing tại t−1 là cố định.
- Đồ thị segment `K_t` (giống `H` trong README). Column generation: master chọn một cấu hình cho mỗi demand, pricing là đường đi ≤ maxSeg cung trên `K_t`. Sau đó giải ILP trên tập cột cuối (price-and-branch).
- **Chạy trên chính SetA** (và một phần SetB). Bảng đặc tính dữ liệu của họ khớp với thống kê ở mục 1.
- **Kết quả trên SetA**, đo bằng gap LP–ILP:
  - t=0: 85% trường hợp có gap ≤ 1%, gap trung bình 3.12%.
  - t=1: chỉ 45% có gap ≤ 1%, gap trung bình 13.05%.
  - Số cột sinh ra từ 6.9 nghìn đến 2.4 triệu.
- **Liên hệ project**: kết quả này cho thấy **t=1 khó hơn t=0 rõ rệt** vì budget. Có thể dùng làm mốc so sánh trong báo cáo. Lưu ý gap của họ là gap LP–ILP trên tập cột, không phải gap MILP đầy đủ.

### 3.3 Tài liệu nên bổ sung vào `survey.md`

| Tài liệu | Vì sao cần |
|---|---|
| Callebaut, De Boeck, Fortz, *Preprocessing for segment routing optimization*, Networks 82(4), 2023 | Loại segment path bị trội, giảm mạnh kích thước MILP **một chu kỳ** (Step 5–6) |
| Bazgan, Chopin, Nichterlein, Richer, *Parameterized complexity of segment routing*, INFOCOM 2025 | Kết quả độ khó, dùng cho Introduction |
| Schüller, Aschenbruck, Chimani, Horneffer, *Failure resiliency with only a few tunnels*, IEEE/ACM ToN 29(1), 2021 | MILP min-MLU có tính đến hỏng link, gần với t=1 |
| Li, Yeung, *Traffic engineering in segment routing networks using MILP*, IEEE TNSM 17(3), 2020 | Một công thức MILP cho SR-TE để so sánh |
| Pereira, Rocha, Sousa, *Traffic engineering with three-segments routing*, IEEE TNSM 17(3), 2020 | Heuristic cho path 3 segment, có xử lý hỏng link |
| Zenodo instance, code STELA/ALEXA, networktools | Để kiểm tra nghiệm và so sánh |

Kiểm tra survey hiện tại: hai paper 2026 có thật, đúng tác giả, đúng nội dung tóm tắt. Các mục "*(chưa đọc full text)*" của hai paper này giờ có thể bỏ, và nên thêm các chi tiết ở 3.1–3.2.

---

## 4. Kế hoạch

Kế hoạch ban đầu đã được thực hiện. Việc còn lại và tình trạng hiện tại xem ở:

- [HUONG_DAN.md](HUONG_DAN.md), mục 12: checklist từng step.
- [PHAN_TICH_KET_QUA.md](PHAN_TICH_KET_QUA.md): kết quả thí nghiệm và phân tích.
