# Đọc và phân tích kết quả thí nghiệm

File này giải thích:

1. Từng cột trong file kết quả nghĩa là gì.
2. Kết quả hiện có nói lên điều gì.
3. Các hiện tượng bất thường và cách giải thích chúng.
4. Nên viết gì vào phần nhận xét của báo cáo.

> Số liệu dưới đây lấy từ `results/step6.csv` và `results/step9.csv` trên máy gốc (Intel Core 7 240H, 16 GB RAM, HiGHS 1.15.1). Mục 0 là cập nhật ngày 24/10/2026; các mục sau được sửa theo đó. Dùng `scripts/run.sh status` để xem số mới nhất.

---

## 0. Cập nhật 24/10/2026 (đọc trước)

### 0.1 Các lỗi đã sửa

| Lỗi | Ảnh hưởng | Cách sửa |
|---|---|---|
| `src/data.jl` so sánh độ dài đường đi bằng `==`. Ở 4 instance có trọng số là số thực (05, 08, 12, 14), cùng một độ dài nhưng cộng theo thứ tự khác nhau, `(a+b)+c` và `a+(b+c)`, lệch nhau ở chữ số cuối. Khi đó ECMP bỏ sót cung của đường ngắn nhất và luồng "biến mất" | setA-08: 12 560/22 350 cặp nút mất luồng (101/200 demand). setA-12, 14 tương tự. **setA-05 không bị**, nên kết quả 01–05 vẫn đúng. MLU không waypoint của setA-12 bị sai: 0.4400 (Step 6) và 0.7201 (Step 9), đúng là 1.0001 | So sánh với sai số tương đối 1e-9. Đã kiểm tra lại cả 20 instance ở cả hai chu kỳ: không cặp nào mất luồng, không cặp nào "gần bằng". Đã ghi lại các dòng Too large của 08, 12, 14 trong CSV |
| `scripts/run.sh`: với `timeout -s KILL`, lệnh `timeout` trả về mã 137 (không phải 124) khi hết giờ | Instance bị chốt chặn cứng dừng sẽ bị ghi nhầm là "Out of memory" | Phân biệt bằng thời gian đã chạy |
| `run_server.sh` gọi `tables` với `RESULTS_DIR=results/server` | Ghi đè bảng của báo cáo bằng số liệu biến thể không đi vòng | Bảng sinh từ `results/server` giờ được ghi vào `results/server/` |

### 0.2 Việc còn lại: Step 6 cho setA-06, 08, 09 trên máy Intel

Ba instance này (4.5–5 triệu biến) dựng được mô hình nên phải có trong bảng. setA-08 **bắt buộc** chạy bằng code mới. 06 và 09 dùng trọng số nguyên, nên nếu `results/step6.csv` trên máy Intel đã có dòng của chúng (từ `results/finish_runs.sh`, mô hình của đề) thì giữ lại.

```bash
# trên máy Intel (WSL), trong thư mục project
grep -E '^setA-0(6|8|9),' results/step6.csv            # xem đã có dòng nào chưa
grep -E '^setA-0(6|9),' results/step6.csv > /tmp/keep_06_09.csv   # giữ 06, 09 (nếu có); KHÔNG giữ 08
git checkout -- results/step6.csv results/step9.csv report/table_step6.tex report/table_step9.tex
git pull
cat /tmp/keep_06_09.csv >> results/step6.csv
scripts/run.sh test                                     # phải in "TẤT CẢ ĐẠT"
HARD_LIMIT=2700 nohup scripts/run.sh step6 9 8 6 > step6_060809.out 2>&1 &   # tối đa ~45 phút/instance
# instance đã có dòng trong CSV sẽ tự được bỏ qua. Khi xong:
scripts/run.sh tables && scripts/run.sh status
```

- Chạy đúng mô hình của đề (không đặt `NO_LOOPS`), để khớp Bảng step6 của báo cáo.
- Nếu một instance bị ghi "Out of memory": WSL2 mặc định chỉ được khoảng một nửa RAM của máy. Tăng `memory=` trong `%UserProfile%\.wslconfig`, chạy `wsl --shutdown`, xoá dòng đó khỏi CSV rồi chạy lại.
- Sau đó sửa chỗ `[TODO]` trong mục 3.3 của `report/report.tex` (có sẵn hai câu mẫu trong comment ngay trên) và biên dịch lại báo cáo.

### 0.3 Kết quả kiểm tra mới (chạy lại trên máy thứ hai, Apple M5, seed 0)

- **Instance toy, vét cạn** mọi segment path có tối đa 4 segment (206 path cho mỗi demand ở mỗi chu kỳ): t = 0 tối ưu 0.375 (không waypoint là 0.4375); t = 1 không waypoint đã là 0.375 và không giảm được. Budget κ = 20 không ràng buộc vì hai demand đổi đường tốn tối đa 16. Vậy MLU tối ưu hai chu kỳ là 0.375. Nghiệm tối ưu không duy nhất: trên máy này, Step 8 trả về ⟨v0,v4,v2,v5⟩ ở t = 0 và bỏ waypoint ở t = 1.
- **`src/verify_solutions.jl`**: giải lại rồi đọc segment path bằng đường đi Euler, tính lại tải từ danh sách segment, tính `dist` thật theo định nghĩa của đề.
  - Step 6, 01–03: MLU tính lại đúng bằng U. Nghiệm của 02 và 03 có chu trình rời (2 segment), vô hại với một chu kỳ.
  - Step 9, 01: U = 0.929384; MLU từng chu kỳ 0.929384 và 0.582881; chu trình rời 6 segment; `dist` thật = 0 ≤ κ = 51.
  - Step 9, 02: U = 0.903075; MLU từng chu kỳ 0.826175 và 0.903075; chu trình rời 24 segment; `dist` thật = 0 ≤ κ = 63.
  - Step 9, 03: U = 0.943543 (trên Mac chưa chứng minh được tối ưu vì máy quá tải, nhưng đúng bằng giá trị tối ưu đã chứng minh trên máy Intel); MLU từng chu kỳ 0.943543 và 0.601896; không có chu trình rời; `dist` thật = 8 ≤ κ = 53 (2 demand đổi đường).
  - Kết luận: sau khi bỏ chu trình rời, nghiệm vẫn hợp lệ, nên giá trị tối ưu ở Step 9 là thật.
- **Giải riêng t = 1** (mạng G₁, lưu lượng ν(d,1), không budget): 01 → 0.346350, 02 → **0.903075**, 03 → 0.402612. Với setA-02, MLU hai chu kỳ đúng bằng tối ưu của riêng t = 1, nên **budget κ = 63 không ràng buộc**: giới hạn nằm ở chính chu kỳ t = 1, tức mạng thiếu một cung với lưu lượng của t = 1 (mục 4.5 cũ giải thích sai điểm này).
- **Biến thể không đi vòng** (`results/server/step6.csv`, cùng máy Intel, chạy trong Docker): nhanh hơn 4–19 lần ở 01–03; setA-04 tìm được 0.4791 (gap 4.18%, cùng cận dưới 0.4591); nhưng setA-05 không có cận dưới sau 6037 s, trong khi mô hình của đề giải tối ưu trong 1706 s. Vì vậy bảng chính của báo cáo dùng mô hình của đề, còn biến thể này nằm ở một bảng so sánh riêng.

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
| 06, 08, 09 | 100–150 | 200–500 | 4.5–5 triệu | 0.61–1.0 | chưa chạy (chạy trên máy Intel bằng code mới, mục 0.2) | | | | | |
| 07, 10–20 | 100–400 | 400–6000 | 7.9 triệu – 958 triệu | 0.63–1.0 | không dựng được (Too large) | | | | | |

## 3. Kết quả Step 9 (t = 0 và t = 1, có budget, giới hạn 3600 s)

| Inst | κ(1) | Số biến | MLU không waypoint | MLU tốt nhất | So với Step 6 | Status | Gap | CPU (s) | Lần chạy |
|---|---|---|---|---|---|---|---|---|---|
| 01 | 51 | 45 600 | 1.0000 | **0.9294** | bằng | Optimal | 0 | 164 ± 297 | 5 |
| 02 | 63 | 117 450 | **1.0981** | **0.9031** | cao hơn (0.5486) | Optimal | 0 | 172 ± 94 | 4 |
| 03 | 53 | 147 000 | 1.0000 | **0.9435** | bằng | Optimal | 0 | 704 | 1 |
| 04 | 44 | 1 470 000 | 1.0000 | 1.0000 | | Not Optimal | không có LB | **9905\*** | 1 |
| 05 | **1** | 2 970 000 | 1.0000 | 1.0000 (nghiệm khởi đầu) | | Bị dừng | | > 10800 | 1 |
| 06–20 | | 13 triệu – 2.9 tỉ | ≈ 1.0 | không dựng được (Too large) | | | | | |

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
- **setA-02:** MLU tăng từ 0.5486 (chỉ t = 0) lên 0.9031. Tại t = 1, nếu không có waypoint thì link nặng nhất **quá tải 109.8%**. Mô hình kéo xuống 90.3%, đúng bằng MLU tối ưu khi giải riêng t = 1 mà không có budget (mục 0.3). Vậy **giới hạn nằm ở chính chu kỳ t = 1 (thiếu một link, lưu lượng của t = 1), không phải ở budget κ = 63**. Ngoài ra, vì mục tiêu min U chỉ quan tâm chu kỳ nặng nhất, nghiệm tìm được có MLU tại t = 0 là 0.826, cao hơn hẳn 0.5486.
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

- Jaumard, Tran, Ziazet (2026) áp dụng column generation cho **toàn bộ SetA** (giải tuần tự từng chu kỳ), với gap LP–ILP trung bình 3.12% tại t = 0 và 13.05% tại t = 1. Hướng của họ là chỉ sinh các segment path "có ích" thay vì tạo biến cho mọi cặp nút.
- Đây là hướng mở rộng tự nhiên cho phần kết luận.
- Họ không công bố MLU từng instance, nên không so sánh trực tiếp con số được.

---

## 5. Gợi ý viết nhận xét trong báo cáo

> **Đã thay thế (24/10/2026):** nhận xét chính thức nằm trong `report/report.tex`, mục 3.3–3.4 và Kết luận. Các đoạn nháp dưới đây giữ lại để tham khảo; đoạn về setA-02 trong bản nháp Step 9 đã sai (budget không ràng buộc, xem mục 0.3).

**Sau bảng Step 6:**

> Mô hình giải tối ưu bốn instance nhỏ (01, 02, 03, 05). Segment Routing giảm MLU từ 6% (setA-03) tới 65% (setA-05) so với định tuyến theo đường ngắn nhất. Ở hầu hết các lần chạy, cây branch-and-bound chỉ có 0 hoặc 1 nút: cận dưới của LP relaxation đã bằng giá trị tối ưu, và thời gian chủ yếu dành cho giải LP và tìm nghiệm nguyên. CPU time dao động mạnh theo seed (ví dụ setA-01: 1.1–29.7 s). Với setA-04 (200 demand), solver không cải thiện được nghiệm khởi đầu trong 1800 s và kết thúc với gap 33.6%. Mười hai instance (07, 10–20) có từ 7.9 triệu tới 958 triệu biến nhị phân nên không dựng được mô hình trên máy thí nghiệm.

**Sau bảng Step 9:**

> Khi xét cả hai chu kỳ, MLU của setA-01 và setA-03 không đổi so với chỉ xét t = 0: budget đủ để xử lý việc mất một liên kết. Với setA-02, định tuyến mặc định tại t = 1 làm một liên kết quá tải 109.8%. Mô hình đưa tải xuống 90.3% trong giới hạn budget κ = 63, nhưng không đạt được mức 54.9% của chu kỳ 0. Mô hình hai chu kỳ có khoảng gấp ba số biến, nên chỉ năm instance dựng được. Với setA-04 (1.47 triệu biến), HiGHS không giải xong LP gốc và chạy quá giới hạn thời gian (9905 s), cho thấy giới hạn thực tế của cách mô hình hoá này.

**Kết luận:**

> Mô hình MILP trên đồ thị segment cho nghiệm tối ưu và cận dưới chặt trên các instance nhỏ, nhưng số biến tăng theo |D|·n² khiến nó không áp dụng được cho mạng lớn. Các hướng mở rộng: tiền xử lý loại segment bị trội (Callebaut et al., 2023), sinh cột với bài toán con là đường đi có tối đa maxSeg cung (Jaumard et al., 2026), và dùng solver thương mại như Gurobi.
