# Đọc và phân tích kết quả thí nghiệm

File này giải thích:

1. Từng cột trong file kết quả nghĩa là gì.
2. Kết quả hiện có nói lên điều gì.
3. Các hiện tượng bất thường và cách giải thích chúng.
4. Nên viết gì vào phần nhận xét của báo cáo.

> Số liệu dưới đây lấy từ `results/step6.csv` và `results/step9.csv` trên máy gốc (Intel Core 7 240H, 16 GB RAM, HiGHS 1.15.1), tính đến 22/10/2026 tối. Những instance ghi "(đang chạy)" sẽ có số sau. Sau khi chạy xong, dùng `scripts/run.sh status` để xem số mới nhất.

---

## 1. Các cột trong file CSV

Mỗi dòng ứng với một instance. File `step6.csv` là chỉ t = 0; file `step9.csv` là t = 0 và t = 1 có budget.

| Cột | Ý nghĩa | Ví dụ |
|---|---|---|
| `instance` | Tên instance | `setA-02` |
| `n`, `m`, `D` | Số nút \|V\|, số cung \|A\|, số demand \|D\| | 30, 150, 45 |
| `nvars` | Số biến của mô hình (x, và y nếu là Step 9) | 39150 |
| `mlu_nowp` | **MLU khi không dùng waypoint** (mọi demand đi đường ngắn nhất). Đây là **mốc so sánh**. Với Step 9 là max của hai chu kỳ. | 1.000000 |
| `runs` | Số lần chạy, mỗi lần một seed khác | 10 |
| `status` | `Optimal`, `Not Optimal`, `Too large`, `Killed`, `Out of memory` (xem [CAI_DAT_VA_CHAY.md](CAI_DAT_VA_CHAY.md), mục 6.4) | `Optimal` |
| `obj` | MLU tốt nhất tìm được (UB), trung bình qua các lần chạy | 0.548578 |
| `lb` | Cận dưới tốt nhất (LB). `-Inf` nghĩa là solver chưa có cận dưới nào | 0.548578 |
| `gap` | `1 − LB/UB`. Bằng 0 là đã chứng minh tối ưu. `Inf` khi LB = `-Inf` | 0.000000 |
| `cpu_mean`, `cpu_std` | CPU time của `optimize!` (giây): trung bình và độ lệch chuẩn qua các lần chạy | 318.01, 0.00 |
| `nodes_mean` | Số nút trung bình của cây branch-and-bound | 1.0 |
| `build_s` | Thời gian dựng mô hình trong JuMP (giây). **Không** tính vào CPU time theo yêu cầu đề | 0.1 |

**Mức giảm tải nhờ Segment Routing** = `1 − obj / mlu_nowp`. Ví dụ setA-02: `1 − 0.5486 / 1.0 = 45%`.

---

## 2. Kết quả Step 6 (chỉ t = 0, giới hạn 1800 s)

| Inst | n | \|D\| | Số biến | MLU không waypoint | MLU tốt nhất | Giảm | Status | Gap | CPU (s) | Lần chạy |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 20 | 40 | 15 200 | 1.0000 | **0.9294** | 7% | Optimal | 0 | 4.5 ± 8.9 | 10 |
| 02 | 30 | 45 | 39 150 | 1.0000 | **0.5486** | 45% | Optimal | 0 | 318 | 1 |
| 03 | 50 | 20 | 49 000 | 1.0000 | **0.9435** | 6% | Optimal | 0 | 58 ± 93 | 9 |
| 04 | 50 | 200 | 490 000 | 0.6918 | 0.6918 | 0% | Not Optimal | 33.6% | 1800 | 1 |
| 05 | 100 | 100 | 990 000 | 0.3333 | **0.1155** | 65% | Optimal | 0 | 1706 | 1 |
| 06, 08, 09 | 100–150 | 200–500 | 4.5–5 triệu | 1.0000 | (đang chạy) | | | | | |
| 07, 10–20 | 100–400 | 400–6000 | 7.9 triệu – 958 triệu | 0.44–1.0 | không dựng được (Too large) | | | | | |

## 3. Kết quả Step 9 (t = 0 và t = 1, có budget, giới hạn 3600 s)

| Inst | κ(1) | Số biến | MLU không waypoint | MLU tốt nhất | So với Step 6 | Status | Gap | CPU (s) | Lần chạy |
|---|---|---|---|---|---|---|---|---|---|
| 01 | 51 | 45 600 | 1.0000 | **0.9294** | bằng | Optimal | 0 | 164 ± 297 | 5 |
| 02 | 63 | 117 450 | **1.0981** | **0.9031** | cao hơn (0.5486) | Optimal | 0 | 172 ± 94 | 4 |
| 03 | 53 | 147 000 | 1.0000 | **0.9435** | bằng | Optimal | 0 | 704 | 1 |
| 04 | 44 | 1 470 000 | 1.0000 | 1.0000 | | Not Optimal | không có LB | **9905\*** | 1 |
| 05 | **1** | 2 970 000 | 1.0000 | (đang chạy) | | | | | |
| 06–20 | | 13 triệu – 2.9 tỉ | 0.72–1.0 | không dựng được (Too large) | | | | | |

\* vượt time limit 3600 s (xem mục 4.4).

---

## 4. Các hiện tượng và cách giải thích

### 4.1 Segment Routing giảm tải rất khác nhau giữa các instance

- **Giảm mạnh:** setA-02 giảm 45% (1.0 → 0.55), setA-05 giảm 65% (0.33 → 0.12). Ở đây link nghẽn có thể được tránh bằng cách lái lưu lượng sang đường khác.
- **Giảm ít:** setA-01 giảm 7%, setA-03 giảm 6%. Lý do có thể là link nặng nhất **không tránh được**. Ví dụ, đó là link duy nhất đi vào một nút đích có lưu lượng lớn, nên đi đường nào cũng phải qua nó.
- **MLU không waypoint ≈ 1.0 ở hầu hết instance.** Có vẻ dữ liệu được sinh ra để routing mặc định vừa chạm ngưỡng nghẽn. Theo paper của nhóm ra đề, traffic matrix được chọn theo một "chỉ số độ khó".

### 4.2 Số nút branch-and-bound gần như luôn là 0 hoặc 1

- Nghĩa là **cận dưới của LP relaxation đã bằng giá trị tối ưu**: bài toán nới lỏng (cho x nhận số lẻ) có cùng MLU với bài toán thật. Solver không cần rẽ nhánh, chỉ cần **tìm được một nghiệm nguyên** đạt cận đó.
- Vì vậy thời gian chủ yếu dồn vào **giải LP rất lớn** và **chạy heuristic tìm nghiệm nguyên**, không phải vào cây branch-and-bound.
- Đây cũng là lý do tăng `mip_heuristic_effort` lên 0.3 có ích.
- **Nút = 0** (ví dụ Step 6 setA-02) nghĩa là solver tìm được nghiệm tối ưu bằng heuristic ngay trong lúc xử lý nút gốc, trước khi nút gốc được tính là đã duyệt.

### 4.3 CPU time dao động mạnh giữa các seed

- Ví dụ Step 6 setA-01: 9 lần chạy mất 1.1–2.7 s, nhưng seed 6 mất 29.7 s. Trung bình 4.5 s, độ lệch chuẩn 8.9 s.
- Ví dụ Step 9 setA-01: 21–41 s, nhưng seed 4 mất 696 s.
- Lý do: seed thay đổi thứ tự thử của heuristic. Có lần tìm thấy nghiệm tối ưu sớm, có lần muộn.
- **Hệ quả cho báo cáo:**
  - Nên ghi cả **độ lệch chuẩn**.
  - Nói rõ quy tắc dừng: gặp lần nào chạy ≥ 300 s thì không lặp tiếp. Vì vậy trung bình đã **bao gồm** lần chạy chậm đó.
  - Giá trị MLU tối ưu thì **giống hệt** ở mọi seed, đúng như mong đợi.

### 4.4 HiGHS chạy quá time limit với mô hình lớn

- Step 9 setA-04 (1.47 triệu biến) chạy **9905 s** dù giới hạn là 3600 s. Solver kết thúc mà **không có cận dưới nào** (LB = −∞) và vẫn giữ nghiệm khởi đầu (MLU = 1.0).
- Giải thích: HiGHS chỉ kiểm tra giới hạn thời gian ở một số thời điểm. Với mô hình rất lớn, nó kẹt ở giai đoạn presolve hoặc giải LP gốc rất lâu mà không kiểm tra.
- Đối chiếu: Step 6 setA-04 (490 nghìn biến) vẫn dừng đúng 1800 s và có LB.
- **Xử lý trong code:** `scripts/run.sh` có `HARD_LIMIT` (mặc định 2 × time limit + 3600 s). Quá hạn này thì tiến trình bị dừng và ghi `Killed`.
- **Trong báo cáo:** ghi đúng con số thật và đánh dấu `*` (bảng LaTeX tự làm). Giải thích ngắn rằng đây là hành vi của solver. Đó là **một kết quả thí nghiệm**, không phải lỗi.

### 4.5 Step 9 so với Step 6

- **setA-01, 03:** MLU hai chu kỳ **bằng** MLU chỉ t = 0. Nghĩa là t = 0 là chu kỳ khó hơn, và tại t = 1 (dù có link bị tắt) budget đủ để giữ tải không vượt mức đó.
- **setA-02:** MLU tăng từ 0.5486 (chỉ t = 0) lên 0.9031. Tại t = 1, nếu không có waypoint thì link nặng nhất **quá tải 109.8%**. Với budget κ = 63, mô hình kéo được xuống 90.3% nhưng không thấp hơn được. Đây là ví dụ rõ về **tác động của bảo trì và giới hạn budget**.
- **Instance có κ = 1** (05, 10, 17): không demand nào được đổi đường, nên mô hình phải tìm **một routing dùng chung cho cả hai chu kỳ**.

### 4.6 Kích thước, không phải độ khó, là giới hạn chính

- Thời gian **không tăng đều** theo số biến:
  - setA-03 (49 nghìn biến) mất 58 s;
  - setA-02 (39 nghìn biến) mất 318 s;
  - setA-05 (990 nghìn biến, 100 demand) giải tối ưu trong 1706 s;
  - setA-04 (490 nghìn biến, 200 demand) hết giờ với gap 33.6%.
- Như vậy **cấu trúc instance** (số demand, mức độ nghẽn) ảnh hưởng nhiều hơn kích thước thuần.
- Nhưng có một **giới hạn cứng về bộ nhớ**: 12/20 instance ở Step 6 (7.9 triệu tới 958 triệu biến) và 15/20 instance ở Step 9 (13 triệu tới 2.9 tỉ biến) không dựng được trên máy 16 GB.

### 4.7 So sánh với tài liệu

- Jaumard, Tran, Ziazet (2026) giải **toàn bộ SetA** bằng column generation, với gap trung bình 3.12% tại t = 0 và 13.05% tại t = 1. Hướng của họ là chỉ sinh các segment path "có ích" thay vì tạo biến cho mọi cặp nút.
- Đây là hướng mở rộng tự nhiên cho phần kết luận.
- Họ không công bố MLU từng instance, nên không so sánh trực tiếp con số được.

---

## 5. Gợi ý viết nhận xét trong báo cáo

Các đoạn dưới đây là **bản nháp**. Hãy cập nhật số khi thí nghiệm xong và viết lại bằng lời của bạn.

**Sau bảng Step 6:**

> Mô hình giải tối ưu bốn instance nhỏ (01, 02, 03, 05). Segment Routing giảm MLU từ 6% (setA-03) tới 65% (setA-05) so với định tuyến theo đường ngắn nhất. Ở hầu hết các lần chạy, cây branch-and-bound chỉ có 0 hoặc 1 nút: cận dưới của LP relaxation đã bằng giá trị tối ưu, và thời gian chủ yếu dành cho giải LP và tìm nghiệm nguyên. CPU time dao động mạnh theo seed (ví dụ setA-01: 1.1–29.7 s). Với setA-04 (200 demand), solver không cải thiện được nghiệm khởi đầu trong 1800 s và kết thúc với gap 33.6%. Mười hai instance (07, 10–20) có từ 7.9 triệu tới 958 triệu biến nhị phân nên không dựng được mô hình trên máy thí nghiệm.

**Sau bảng Step 9:**

> Khi xét cả hai chu kỳ, MLU của setA-01 và setA-03 không đổi so với chỉ xét t = 0: budget đủ để xử lý việc mất một liên kết. Với setA-02, định tuyến mặc định tại t = 1 làm một liên kết quá tải 109.8%. Mô hình đưa tải xuống 90.3% trong giới hạn budget κ = 63, nhưng không đạt được mức 54.9% của chu kỳ 0. Mô hình hai chu kỳ có khoảng gấp ba số biến, nên chỉ năm instance dựng được. Với setA-04 (1.47 triệu biến), HiGHS không giải xong LP gốc và chạy quá giới hạn thời gian (9905 s), cho thấy giới hạn thực tế của cách mô hình hoá này.

**Kết luận:**

> Mô hình MILP trên đồ thị segment cho nghiệm tối ưu và cận dưới chặt trên các instance nhỏ, nhưng số biến tăng theo |D|·n² khiến nó không áp dụng được cho mạng lớn. Các hướng mở rộng: tiền xử lý loại segment bị trội (Callebaut et al., 2023), sinh cột với bài toán con là đường đi có tối đa maxSeg cung (Jaumard et al., 2026), và dùng solver thương mại như Gurobi.
