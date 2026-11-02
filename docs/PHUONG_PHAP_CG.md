# Phương pháp 2: Column generation (sinh cột) cho bài toán T-ASR

Tài liệu này mô tả **phương pháp thứ hai** của project. Phương pháp này giải được **cả 20 instance SetA**, kể cả những instance mà mô hình MILP đầy đủ (`src/model.jl`, phương pháp 1) không dựng nổi.

- **Code:** `src/colgen.jl`, `src/improve.jl`, `src/run_cg.jl`. Lệnh chạy: `scripts/run.sh cg6 all` và `scripts/run.sh cg9 all` (mục 11).
- **Kết quả:** `results/cg/`. Bảng đầy đủ ở mục 10.
- **Nên đọc trước:** [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), Phần 4 đến Phần 8 (r, tải, MLU, segment, budget, mô hình (1)–(4)). Tài liệu này dùng lại ký hiệu ở đó.

**Tóm tắt kết quả** (chi tiết ở mục 10):

| | Phương pháp 1 (MILP đầy đủ) | Phương pháp 2 (sinh cột) | Tốt nhất của challenge (53 đội) |
|---|---|---|---|
| Step 9: MLU trung bình 20 instance | 0.989 | **0.572** | 0.572 |
| Step 9: số instance bằng kết quả tốt nhất (giá trị tốt nhất qua 10 lần) | 3/20 | **20/20** (mọi lần chạy: 19/20; setA-19: 9/10 lần) | |
| Step 6: MLU trung bình 20 instance | 0.839 | **0.481** | (không công bố) |
| Thời gian lâu nhất cho một lần chạy | quá 1800 / 3600 s (bị dừng) | 1225 s (khoảng 20 phút) | |

**Mục lục**

1. [Vì sao cần phương pháp khác](#1-vì-sao-cần-phương-pháp-khác)
2. [Ý tưởng bằng lời](#2-ý-tưởng-bằng-lời)
3. [Mô hình theo đường đi](#3-mô-hình-theo-đường-đi)
4. [Vòng lặp sinh cột](#4-vòng-lặp-sinh-cột)
5. [Cận dưới và gap](#5-cận-dưới-và-gap)
6. [Step 9: hai chu kỳ và budget](#6-step-9-hai-chu-kỳ-và-budget)
7. [Từ nghiệm LP ra nghiệm nguyên](#7-từ-nghiệm-lp-ra-nghiệm-nguyên)
8. [Vòng cải thiện quanh link nghẽn](#8-vòng-cải-thiện-quanh-link-nghẽn)
9. [Kiểm tra nghiệm](#9-kiểm-tra-nghiệm)
10. [Kết quả trên SetA](#10-kết-quả-trên-seta)
11. [Cách chạy và tham số](#11-cách-chạy-và-tham-số)
12. [Giới hạn và lưu ý khi viết báo cáo](#12-giới-hạn-và-lưu-ý-khi-viết-báo-cáo)
13. [Từ công thức sang code](#13-từ-công-thức-sang-code)
14. [Tài liệu tham khảo](#14-tài-liệu-tham-khảo)

---

## 1. Vì sao cần phương pháp khác

Mô hình (1)–(4) có một biến nhị phân `x^{dt}_{ij}` cho **mỗi demand × mỗi cặp nút**, nên số biến là khoảng `|D| × n × (n − 1)` cho mỗi chu kỳ:

| Instance | n | \|D\| | Số biến x (một chu kỳ) |
|---|---|---|---|
| setA-01 | 20 | 40 | 15 200 |
| setA-05 | 100 | 100 | 990 000 |
| setA-10 | 150 | 1 000 | 22 350 000 |
| setA-20 | 400 | 6 000 | **957 600 000** |

Hậu quả trong thí nghiệm của phương pháp 1:

- Chỉ chứng minh được tối ưu ở setA-01, 02, 03, 05 (Step 6) và 01–03 (Step 9). Step 6 setA-10–20 và Step 9 setA-07, 10–20 không dựng được mô hình vì thiếu RAM; các instance còn lại hết giờ hoặc bị chốt chặn dừng.
- Với phần lớn các instance đó, nghiệm duy nhất có được là "mọi demand đi thẳng, không waypoint", mà nghiệm này cho MLU ≈ 1.0. Vì vậy **MLU của cả bảng cao**: trung bình 0.839 (Step 6) và 0.989 (Step 9), trung vị 0.984 và 1.0. MLU cao là do mô hình không chạy được, không phải do mạng không cải thiện được.

Điểm mấu chốt để làm khác đi: **trong nghiệm tối ưu, gần như mọi demand chỉ dùng 1 đến 3 đường đi khác nhau đáng cân nhắc.** Phần lớn hàng trăm triệu biến kia chắc chắn bằng 0. Nếu biết trước những đường "có ích", mô hình sẽ nhỏ đi hàng nghìn lần.

## 2. Ý tưởng bằng lời

Hãy hình dung một **người điều phối giao thông** và một **người tư vấn đường đi**:

1. Người điều phối bắt đầu với một danh sách đường rất ngắn: mỗi demand chỉ có một đường, là đi thẳng. Ông chia luồng sao cho link đầy nhất ít đầy nhất có thể, **trong phạm vi danh sách hiện có**.
2. Sau khi chia, ông biết **link nào đang là "nút cổ chai"** và gán cho mỗi link một **"giá"**. Link càng gây nghẽn thì giá càng cao, còn link thừa chỗ thì giá bằng 0.
3. Người tư vấn nhận bảng giá và, với từng demand, tìm **đường rẻ nhất** (tối đa maxSeg segment) theo bảng giá đó. Nếu đường này rẻ hơn mức mà demand đang "trả", nó được **thêm vào danh sách** (đây là "sinh cột").
4. Lặp lại bước 1–3 cho đến khi người tư vấn không tìm thêm được đường nào có lợi.

Khi dừng, ta có:

- một **nghiệm LP** (cho phép chia một demand ra nhiều đường), tốt nhất có thể trên **toàn bộ** không gian đường đi, dù chỉ liệt kê một phần nhỏ;
- một **cận dưới có chứng minh** cho MLU (mục 5);
- một **tập đường ứng viên** nhỏ. Sau đó ta giải MILP chỉ trên tập này để có nghiệm thật, tức mỗi demand đúng một đường (mục 7), rồi cải thiện thêm (mục 8).

Đây là kỹ thuật kinh điển trong tối ưu, gọi là **column generation** (sinh cột; mỗi đường đi là một "cột" của ma trận ràng buộc). Với Segment Routing, nó được dùng trong CG4SR (Jadin et al., 2019), và Jaumard et al. (2026) đã chạy nó trên chính SetA.

## 3. Mô hình theo đường đi

### 3.1 Ký hiệu mới

| Ký hiệu | Nghĩa | Ví dụ (toy) |
|---|---|---|
| `p` | một **segment path** của demand d: dãy nút `⟨s_d, w1, …, t_d⟩`, tối đa maxSeg segment, không dùng một segment hai lần | `⟨v0, v2, v5⟩` |
| `P_d` | tập **mọi** segment path hợp lệ của demand d | rất lớn (khoảng n^5) |
| `L_t(p, a)` | phần lưu lượng (tính trên 1 đơn vị) mà path p đặt lên cung a ở chu kỳ t | |
| `λ_{dp}` | biến chọn: = 1 nếu demand d đi theo path p | |

Tải của một path là tổng tải của các segment của nó:

```
L_t(p, a) = Σ_{(i,j) ∈ p} r(i, j, a, t)
```

- **Đọc là:** "L t của p tại a bằng tổng, theo mọi segment (i, j) của p, của r(i, j, a, t)".
- **Nghĩa là:** gửi 1 đơn vị theo path p thì cung a nhận đúng chừng đó, do mỗi segment đi theo ECMP với hệ số r.
- **Ví dụ số:** ở toy, t = 0, path `⟨v0, v5⟩` có `L(⟨v0,v5⟩, a3,5) = r(v0, v5, a3,5) = 0.75` (Table 2 của đề).

### 3.2 Mô hình chính (master problem), Step 6

```
min  U
s.t. Σ_{p ∈ P_d} λ_{dp} = 1                                   với mọi demand d        (M1)
     Σ_d Σ_{p ∈ P_d} ν(d, 0) · L_0(p, a) · λ_{dp} ≤ U · c(a)   với mọi cung a          (M2)
     λ_{dp} ∈ {0, 1}
```

- **(M1)** mỗi demand chọn đúng một path. Nó thay cho ràng buộc bảo toàn luồng (1) và giới hạn segment (2) của mô hình gốc: hai điều kiện đó đã nằm sẵn trong định nghĩa "p là segment path hợp lệ".
- **(M2)** chính là ràng buộc tải (3) của mô hình gốc, viết theo path.
- **Tương đương với mô hình gốc:** chọn `λ_{dp} = 1` giống hệt việc đặt `x^{d0}_{ij} = 1` cho các segment (i, j) của p. Hai mô hình có cùng nghiệm tối ưu.
- **Bản LP (nới lỏng):** thay `λ ∈ {0,1}` bằng `λ ≥ 0`, tức cho phép chia một demand ra nhiều path. Giá trị LP là một cận dưới của bài toán thật.

Mô hình này có **ít ràng buộc** (`|D| + m`) nhưng **rất nhiều cột** (một cột cho mỗi path). Vì vậy ta không liệt kê hết cột, mà sinh dần.

## 4. Vòng lặp sinh cột

### 4.1 Bài toán chính thu hẹp (RMP)

Ta giải bản LP của (M1)–(M2) nhưng chỉ với **tập path hiện có**. Ban đầu, mỗi demand chỉ có path đi thẳng `⟨s_d, t_d⟩`. Bài toán này gọi là **restricted master problem** (RMP), giải bằng HiGHS (simplex). Mỗi lần thêm cột, HiGHS giải tiếp từ nghiệm cũ (warm start) nên rất nhanh.

### 4.2 Giá đối ngẫu: "giá link" và "mức trả của demand"

Khi giải LP, solver trả về kèm **biến đối ngẫu** (dual) cho mỗi ràng buộc:

- `w_a ≥ 0` cho ràng buộc tải (M2) của cung a: đây là **"giá" của link a**. `w_a > 0` nghĩa là link a đang là nút cổ chai; `w_a = 0` nghĩa là link a còn thừa chỗ.
- `μ_d` cho ràng buộc (M1) của demand d: đây là **"mức trả" hiện tại của demand d**.
- Luôn có `Σ_a c(a) · w_a = 1` (đối ngẫu của biến U).

### 4.3 Bài toán con (pricing): tìm path rẻ nhất

Một path p mới của demand d **có lợi** nếu **reduced cost** của nó âm:

```
rc(d, p) = ν(d) · Σ_a L(p, a) · w_a − μ_d < 0
```

- **Đọc là:** "chi phí của path p theo bảng giá w, trừ mức trả hiện tại của d".
- **Nghĩa là:** nếu đi theo p rẻ hơn mức d đang trả, thì thêm p vào RMP sẽ làm U giảm (hoặc ít nhất không tăng).

Vì `L(p, a)` là tổng theo segment, chi phí của path cũng là **tổng theo segment**:

```
W(i, j) = Σ_a r(i, j, a) · w_a          (giá của segment i → j)
chi phí(p) = Σ_{(i,j) ∈ p} W(i, j)
```

Vậy tìm path rẻ nhất chính là **tìm đường ngắn nhất từ s_d tới t_d trên đồ thị segment H** (đồ thị đầy đủ, cung (i, j) có độ dài W(i, j)), **với tối đa maxSeg cung**. Ta giải bằng quy hoạch động kiểu Bellman–Ford:

```
f_0(s) = 0,   f_0(v) = +∞ với v ≠ s
f_k(v) = min( f_{k−1}(v),  min_u [ f_{k−1}(u) + W(u, v) ] )     k = 1, …, maxSeg
```

- `f_k(v)` là chi phí nhỏ nhất để đi từ s tới v với **tối đa k segment**. Kết quả cần tìm là `f_{maxSeg}(t_d)`.
- **Độ phức tạp:** `O(maxSeg × n²)` cho mỗi nguồn s. Một lần DP từ s cho đường rẻ nhất tới **mọi** đích, nên chỉ cần chạy một lần cho mỗi nguồn khác nhau. Hệ số ν(d) chỉ nhân chi phí lên, không đổi đường rẻ nhất.
- Với setA-20 (n = 400), một vòng pricing mất dưới 1 giây khi chạy song song 8 luồng.
- Khi hai path có cùng chi phí, DP giữ path **ít segment hơn**. Path nào dùng lại một segment hai lần (mô hình gốc không cho phép, vì x là 0/1) thì bị bỏ.

### 4.4 Điều kiện dừng

Mỗi vòng, với mọi demand có `rc < −10⁻⁶ × LP`, path rẻ nhất được thêm vào RMP. Vòng lặp dừng khi:

- không demand nào có path với reduced cost âm (LP đã tối ưu trên **toàn bộ** không gian path); hoặc
- LP − cận dưới ≤ 10⁻⁶ × LP (mục 5); hoặc
- hết `CG_TIME` giây (mặc định 600).

Trên SetA, vòng lặp luôn dừng vì hai điều kiện đầu, sau 1 đến 67 vòng, và sinh 25 đến khoảng 23 000 cột. Con số này rất nhỏ so với hàng trăm triệu biến của phương pháp 1.

### 4.5 Ví dụ số trên toy (Step 6)

Toy có 2 demand: d0 từ v0 tới v5 (ν = 50) và d1 từ v2 tới v5 (ν = 100). In ra bằng `src/colgen.jl`:

**Vòng 1.** RMP chỉ có hai path đi thẳng `⟨v0, v5⟩` và `⟨v2, v5⟩`.

- LP: U = 0.4375. Link a3,5 nhận `r(v0,v5,a3,5) × 50 + r(v2,v5,a3,5) × 100 = 0.75 × 50 + 0.5 × 100 = 87.5` trên dung lượng 200, nên U = 87.5/200 = 0.4375.
- Giá link: chỉ `w(a3,5) = 0.005` khác 0 (đúng link nghẽn), `c(a3,5) · w = 200 × 0.005 = 1`. Mức trả: `μ = (0.1875, 0.25)`.
- Pricing: với bảng giá này, mọi path tránh a3,5 đều có chi phí 0, ví dụ `⟨v0, v6, v5⟩` và `⟨v2, v6, v5⟩`. Reduced cost là 0 − 0.1875 < 0 và 0 − 0.25 < 0, nên **thêm 2 cột**.

**Vòng 2.**

- LP: U = **0.375**, với λ(⟨v2, v5⟩) = 0.75 và λ(⟨v2, v6, v5⟩) = 0.25. Ở đây d1 được chia ra hai path, tức là nghiệm phân số.
- Giá link: `w(a3,5) = w(a4,6) = 0.0025`.
- Pricing: path rẻ nhất của mỗi demand đúng bằng mức trả, reduced cost = 0, nên **không thêm cột nào**. Dừng.
- Cận dưới Lagrange (mục 5.1) = 0.375 = LP, nên **MLU tối ưu không thể nhỏ hơn 0.375**.

Nghiệm nguyên tối ưu của toy cũng là 0.375 (khớp `scripts/run.sh test`), nhưng để có nó cần thêm mục 7 và mục 8.

## 5. Cận dưới và gap

Đề yêu cầu báo cáo `gap = 1 − LB / UB`. UB là MLU của nghiệm tìm được. LB phải là một con số **đã chứng minh** rằng không nghiệm nào tốt hơn. Phương pháp 2 dùng hai cận dưới và lấy cái lớn hơn.

### 5.1 Cận Lagrange (từ giá link)

Với **bất kỳ** bảng giá `w ≥ 0` nào:

```
LB(w) = Σ_d ν(d) · chi_phí_rẻ_nhất_d(w)  /  Σ_a c(a) · w_a
```

- **Vì sao đúng:** xét một nghiệm bất kỳ có MLU bằng U. Tải mỗi cung ≤ U · c(a), nên `Σ_a w_a · tải_a ≤ U · Σ_a c(a) · w_a`. Vế trái bằng tổng chi phí các path đang dùng, mà mỗi path tốn ít nhất bằng path rẻ nhất. Chia hai vế cho `Σ c·w` là ra công thức.
- **Ưu điểm:** pricing đã tính sẵn `chi_phí_rẻ_nhất_d`, nên **mỗi vòng có ngay một cận dưới hợp lệ**, kể cả khi chưa hội tụ. Khi hội tụ, cận này bằng đúng giá trị LP.
- Ở vòng 1 của toy, chi phí rẻ nhất bằng 0 nên LB = 0. Ở vòng 2, LB = 0.375.

### 5.2 Cận "một demand"

Một demand lớn, dù đi đường nào, cũng phải đặt một lượng tải nhất định lên một link nào đó:

```
LB_1 = max_d  min_{p ∈ P_d}  max_a  ν(d) · L(p, a) / c(a)
```

- **Nghĩa là:** "dù các demand khác biến mất, riêng demand d đã làm MLU ít nhất bằng chừng này".
- Tính bằng một DP "cổ chai": giống mục 4.3 nhưng thay phép cộng bằng phép lấy max. DP lấy max theo từng segment, nên nếu hai segment của path cùng đi qua một link thì tải bị tính thiếu. Vì vậy giá trị DP nhỏ hơn hoặc bằng biểu thức trên, và vẫn là cận dưới hợp lệ.
- **Vì sao cần:** cận LP yếu khi có **ít demand nhưng demand lớn**. LP được chia một demand lớn ra nhiều path, còn nghiệm thật thì không. Ví dụ ở Step 9 setA-02: LP = 0.624 nhưng LB_1 = **0.903075** = MLU tìm được, nên chứng minh được nghiệm là tối ưu (gap 0).

### 5.3 Khi nào cận dưới vẫn yếu

setA-03 (20 demand) có LB = 0.634 trong khi MLU tối ưu là 0.943543. MLU này đã được phương pháp 1 chứng minh tối ưu, vì MILP đầy đủ của setA-03 nhỏ. Gap 32.8% ở đây là do **cận dưới yếu**, không phải do nghiệm kém. Khi viết báo cáo nên ghi rõ điều này.

## 6. Step 9: hai chu kỳ và budget

### 6.1 Cột = một cặp path

Ở Step 9, mỗi demand cần một path cho t = 0 và một path cho t = 1. Một **cột** bây giờ là một **cặp** `(p0, p1)`, với chi phí budget:

```
Δ(p0, p1) = | S(p0) △ S(p1) |
```

- `S(p)` là tập segment của p, `△` là hiệu đối xứng (có ở bên này mà không có ở bên kia).
- Đây đúng là `dist` của đề cho một demand ([GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), mục 7.3). Ví dụ `⟨v0, v4, v5⟩ → ⟨v0, v5⟩` có Δ = 3.

Master thêm ràng buộc tải cho **cả hai chu kỳ** (cung bị tắt ở t = 1 thì không có ràng buộc) và một dòng budget:

```
Σ_d Σ_{(p0,p1)} Δ(p0, p1) · λ_{d,(p0,p1)} ≤ κ          (đối ngẫu ρ ≥ 0)
```

Với λ nguyên, dòng này **chính xác** bằng ràng buộc budget (4) của đề, không cần biến phụ y.

### 6.2 Pricing cho cặp path

Reduced cost của cặp `(p0, p1)`:

```
rc = ν(d,0) · chi_phí_0(p0) + ν(d,1) · chi_phí_1(p1) + ρ · Δ(p0, p1) − μ_d
```

Mỗi vòng, với mỗi demand, ta tạo hai ứng viên:

1. **Path chung** `(p, p)`, Δ = 0: DP như mục 4.3 với giá segment `ν(d,0)·W_0(i,j) + ν(d,1)·W_1(i,j)`. Vì hai hệ số ν khác nhau theo demand, DP chạy cho từng demand.
2. **Hai path riêng** `(p0*, p1*)`: path rẻ nhất cho từng chu kỳ (DP theo nguồn), rồi tính Δ thật của cặp.

Cận Lagrange vẫn hợp lệ nhờ hai nhận xét. (i) **Hai path có tập segment khác nhau thì khác nhau ít nhất 2 segment**, tức Δ ≥ 2: hiệu hai luồng s → t là một luồng vòng khác 0, mà luồng vòng trên đồ thị không có khuyên có ít nhất 2 cung. (ii) Hai path có **cùng** tập segment (chỉ khác thứ tự) thì Δ = 0 và đặt lên mạng đúng cùng một tải, nên chi phí của chúng không nhỏ hơn chi phí của path chung tốt nhất. Vậy chi phí của mọi cặp ≥ `min(chi_phí_chung, chi_phí_riêng + 2ρ)`, và:

```
LB = ( Σ_d min(chung_d, riêng_d + 2ρ) − ρ·κ )  /  Σ_{t,a} c(a) · w_{t,a}
```

### 6.3 Tối ưu đồng thời, không tuần tự

Jaumard et al. (2026) giải t = 0 trước, cố định nghiệm, rồi mới giải t = 1. Theo hình kết quả của họ, MLU ở t = 1 đôi khi vượt 1. Phương pháp 2 tối ưu **cả hai chu kỳ cùng lúc** (min của max hai chu kỳ), giống ý tưởng "trajectory column generation" của Bouaachra (2026). Nhờ vậy nó tránh được nghiệm tốt ở t = 0 nhưng xấu ở t = 1.

### 6.4 Trường hợp κ = 1 (setA-05, 10, 17)

Mọi thay đổi tốn ít nhất 2, nên với κ = 1 **không demand nào được đổi đường**: mỗi demand dùng một path chung cho cả hai chu kỳ. Phương pháp tự xử lý trường hợp này, vì chỉ cột Δ = 0 mới vừa budget trong MILP.

## 7. Từ nghiệm LP ra nghiệm nguyên

Nghiệm LP có thể chia một demand ra nhiều path, nên cần nghiệm nguyên: mỗi demand **đúng một** path ở mỗi chu kỳ.

### 7.1 Làm tròn

Mỗi demand lấy cột có λ lớn nhất. Ở Step 9, nếu tổng Δ vượt κ thì lần lượt đưa các demand có λ nhỏ nhất về cột Δ = 0 tốt nhất của chúng. Nghiệm này dùng làm **điểm xuất phát** (MIP start) cho bước sau.

### 7.2 MILP trên tập cột

Với mỗi demand, gom mọi path đã sinh thành một **tập ứng viên** (pool), thường chỉ 1 đến 5 path. Sau đó giải bằng HiGHS:

- **Step 6:** biến nhị phân cho mỗi (demand, path trong pool), cùng ràng buộc (M1), (M2).
- **Step 9 ("MILP cặp"):** mỗi demand chọn **một path chung** (Δ = 0) **hoặc**, nếu thuộc tập C, **một cặp path khác nhau** với hệ số Δ trong dòng budget. Tập C gồm các demand mà nghiệm LP có dùng cột thay đổi. Cách viết này chặt hơn nhiều so với tuyến tính hoá `|x¹ − x⁰|` bằng biến y. Ví dụ ở setA-10, MILP giải xong trong 10 s thay vì quá 300 s.
- Thêm ràng buộc `U ≥ LB`, để solver dừng ngay khi chạm cận dưới.
- Giới hạn `MILP_TIME` giây (mặc định 300).

### 7.3 Vì sao chưa đủ

Tập cột sinh ra để **giải tốt LP**, chưa chắc chứa những path cần cho **nghiệm nguyên tốt nhất**. Ở toy, pool chỉ có `⟨v0,v5⟩, ⟨v0,v6,v5⟩` cho d0 và `⟨v2,v5⟩, ⟨v2,v6,v5⟩` cho d1. MILP trên pool chỉ đạt **0.4375**, trong khi tối ưu là 0.375. Kỹ thuật "sinh cột rồi giải MILP trên tập cột" (price-and-branch) luôn có khoảng hở này, nên cần mục 8.

## 8. Vòng cải thiện quanh link nghẽn

Lặp lại các bước sau cho đến khi chạm cận dưới, hoặc hết `IMP_TIME` giây (mặc định 780 s cho Step 6 và 2400 s cho Step 9, mục 11), hoặc 3 vòng liền không cải thiện (2 vòng nếu không sinh thêm được path nào):

1. **Tìm link nghẽn:** các link có tải ≥ 99.5% MLU hiện tại (ở cả hai chu kỳ nếu là Step 9).
2. **Chọn demand:** tối đa 400 demand đi qua các link nghẽn, ưu tiên demand đóng góp nhiều tải nhất.
3. **Sinh path mới cho mỗi demand đó** bằng DP "cổ chai". Giữ nguyên tải của mọi demand khác, gọi là `L'`, rồi tìm path làm **link đầy nhất trên đường đi ít đầy nhất**:
   ```
   giá_segment(i, j) = max_a ( L'_a + ν(d) · r(i, j, a) ) / c(a)
   ```
   Hai path có cùng giá trị max thì so tiếp tổng tải. Mỗi demand nhận tối đa 2 path mới (Step 6) hoặc 6 path mới (Step 9):
   - path tốt nhất cho từng chu kỳ;
   - path tốt nhất **tránh hẳn** mọi segment đi qua link nghẽn;
   - (Step 9) path chung tốt nhất cho cả hai chu kỳ, và bản tránh link nghẽn của nó.
4. **Giải lại MILP trên pool đã mở rộng** (tối đa 120 s). Để MILP nhỏ, chỉ được đổi path: các demand vừa được sinh path mới, cộng tối đa 1500 demand tải nặng nhất đi qua link có tải ≥ 90% MLU; các demand còn lại giữ nguyên. Ở Step 9, chỉ các demand vừa được sinh path mới và 300 demand tải nặng nhất được dùng cặp path khác nhau.
5. **Mở rộng khi bị kẹt:** nếu một vòng không cải thiện, vòng sau dùng ngưỡng rộng hơn: link nghẽn ≥ 97% MLU, sinh path mới cho tối đa 800 demand, và tối đa 2000 demand tải nặng nhất đi qua link ≥ 50% MLU được đổi path.

**Ví dụ toy (Step 6):**

- Link nghẽn là a3,5. Bước 3 thêm cho d0 hai path mới `⟨v0, v2, v5⟩` và `⟨v0, v2, v6, v5⟩`.
- MILP chọn d0 = `⟨v0, v2, v5⟩`, d1 = `⟨v2, v5⟩`, cho **U = 0.375 = cận dưới**. Gap 0, tối ưu.
- Step 9 trên toy cũng cho 0.375 ở cả hai chu kỳ.

**Trên SetA**, vòng cải thiện là bước quyết định ở các instance lớn. Ví dụ ở một lần chạy setA-19 Step 9: MILP trên tập cột cho 0.0548; sau vài vòng cải thiện còn 0.0468, bằng cận dưới và bằng kết quả tốt nhất của challenge.

## 9. Kiểm tra nghiệm

Ba lớp kiểm tra độc lập:

1. **Trong Julia** (`evaluate` trong `src/colgen.jl`): sau khi giải, tính lại tải từ các path đã chọn, **không dùng** giá trị của MILP. Kiểm tra: đúng nguồn và đích, ≤ maxSeg segment, không dùng lại segment, không có tải trên cung bị tắt, và budget ≤ κ.
2. **Bằng Python thuần** (`src/verify_srpaths.py`): đọc thẳng file JSON của đề và file nghiệm `srpaths.json`, **tự viết lại** Dijkstra và ECMP, rồi tính MLU và budget. Lệnh: `python3 src/verify_srpaths.py 9 results/runs/seed0/cg`. Cả 400 nghiệm (20 instance × 2 step × 10 seed) đều đạt (`results/runs/logs/verify_all_final.txt`).
3. **So với kết quả công bố:** ở Step 9, giá trị tốt nhất qua 10 lần của cả 20 instance, làm tròn xuống 6 chữ số như checker chính thức in ra, bằng đúng MLU tốt nhất của vòng sprint ROADEF 2026 (53 đội). Ở 19/20 instance, cả 10 lần chạy đều đạt giá trị đó; ở setA-19, 9/10 lần đạt và 1 lần dừng ở 0.048712 (mục 12). Vì các giá trị tham chiếu do checker chính thức tính, sự trùng khớp này là bằng chứng mạnh rằng cách tính r và tải của chúng ta khớp với của ban tổ chức.

File nghiệm `results/runs/seed<k>/cg/setA-XX-step{6,9}-srpaths.json` có đúng định dạng của **checker chính thức** (`{"srpaths":[{"d":…,"t":…,"w":[…]}]}`, với d là thứ tự demand trong file tm). Bạn có thể tự chạy checker của ban tổ chức để xác nhận lần nữa.

> **Lỗi đã sửa trong `src/data.jl`.** Hàm `r_ecmp` từng so sánh khoảng cách số thực bằng `==`. Với metric thập phân (ví dụ 0.0037), sai số làm tròn làm phép so sánh sai, nên luồng bị "mất": hơn một nửa số cặp nút của setA-08, 12 và 14 bị mất một phần luồng (ở t = 0: 12 560/22 350, 25 144/39 800 và 41 280/62 250 cặp; đã kiểm chứng bằng cách so bản cũ với bản sửa). Ở setA-05, cũng có metric thập phân, không cặp nào bị ảnh hưởng. Code hiện dùng so sánh có sai số (`isapprox`, rtol = 10⁻⁹). Kết quả cũ tính trước khi sửa nằm ở `results/old_2026-10-22/` và sai ở ba instance này: ví dụ MLU không waypoint của setA-12 ghi 0.44, thực ra là 1.0001. Các file `results/step6.csv`, `results/step9.csv` hiện tại được tính sau khi sửa (26/10).

## 10. Kết quả trên SetA

> **Cập nhật 02/11/2026.** Báo cáo chính ([report/paper/paper.pdf](../report/paper/paper.pdf)) dùng số liệu phương pháp 1 **chạy lại trên máy B đêm 29/10** (`results/m1opt/`, CPU = thời gian cả lệnh `optimize!`, kèm kiểm tra nghiệm và đo RAM). Mọi bảng giờ cùng một máy; kể cả Step 9 setA-06, 08, 09 (chạy thêm đêm 30/10 và ngày 02/11). Cột phương pháp 1 của các bảng 10.1–10.2 dưới đây lấy theo lượt này (Bảng III, IV của báo cáo). Máy A (`results/reference/method1_machineA.csv`) chỉ còn dùng để so sánh ở mục VII-F của báo cáo: giá trị tốt nhất trùng ở mọi instance; trạng thái khác ở Step 6 setA-02 (Opt. 9/10), setA-05 (Opt. 2/10, 5 lượt bị chốt chặn dừng) và setA-09 (trả về trong giới hạn, có cận dưới 0.5054).

Phương pháp 2 chạy trên **máy B** (Intel Xeon 2.20 GHz, 8 nhân / 16 luồng, 62.8 GiB = 67.4 GB RAM, Docker), 10 lần cho mỗi instance và mỗi bước (`random_seed` 0..9 của HiGHS), 8 lượt song song, mỗi lượt 2 luồng. Cột "Phương pháp 1" lấy từ Bảng III, IV của báo cáo chính (`results/m1opt/`, cũng trên máy B). Quy ước giống bảng của báo cáo: MLU là giá trị tốt nhất qua các lần chạy; CPU, gap và số nút là trung bình (gap = 0 với lần tối ưu). Dữ liệu gốc: `results/runs/seed*/cg/`, tổng hợp: `results/cg/cg_10runs.md`. Toàn bộ 400 nghiệm đã được kiểm tra độc lập bằng `src/verify_srpaths.py`.

### 10.1 Step 6 (chỉ t = 0, time limit 1800 s)

| Inst | n | \|D\| | Không waypoint | Phương pháp 1 | Cận dưới | **MLU (tốt nhất 10 lần)** | Status | Gap TB | CPU TB ± độ lệch (s) | Nút B&B TB |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 20 | 40 | 1.0000 | 0.9294 (Opt.) | 0.929384 | **0.929384** | Optimal | 0.00% | 0.0 ± 0.0 | 0 |
| 02 | 30 | 45 | 1.0000 | 0.5486 (Optimal 9/10) | 0.548578 | **0.548578** | Optimal | 0.00% | 0.1 ± 0.0 | 3 |
| 03 | 50 | 20 | 1.0000 | 0.9435 (Opt.) | 0.633661 | **0.943543** | Not Optimal | 32.84% | 0.1 ± 0.0 | 4 |
| 04 | 50 | 200 | 0.6918 | 0.5467 (N.Opt.) | 0.459068 | **0.459119** | Not Optimal | 0.01% | 0.5 ± 0.1 | 265 |
| 05 | 100 | 100 | 0.3333 | 0.1155 (Optimal 2/10) | 0.115524 | **0.115524** | Optimal | 0.00% | 0.0 ± 0.0 | 0 |
| 06 | 100 | 500 | 1.0000 | 1.0000 (N.Opt.) | 0.098592 | **0.098592** | Optimal | 0.00% | 0.6 ± 0.2 | 17 |
| 07 | 100 | 800 | 0.9080 | 0.9080 (N.Opt.) | 0.907989 | **0.907989** | Optimal | 0.00% | 0.1 ± 0.0 | 0 |
| 08 | 150 | 200 | 1.0000 | 0.5832 (N.Opt.) | 0.318904 | **0.318904** | Optimal | 0.00% | 0.1 ± 0.0 | 2 |
| 09 | 150 | 200 | 0.6111 | 0.6111 (N.Opt., gap 17.30%, cận 0.5054) | 0.505384 | **0.505384** | Optimal | 0.00% | 0.1 ± 0.0 | 1 |
| 10 | 150 | 1000 | 1.0000 | quá lớn (không dựng) | 0.068323 | **0.069565** | Not Optimal | 1.79% | 7.8 ± 7.1 | 393 |
| 11 | 200 | 400 | 1.0000 | quá lớn (không dựng) | 0.613133 | **0.644600** | Not Optimal | 4.88% | 0.5 ± 0.1 | 10 |
| 12 | 200 | 400 | 1.0001 | quá lớn (không dựng) | 0.578947 | **0.640075** | Not Optimal | 9.55% | 0.2 ± 0.1 | 3 |
| 13 | 200 | 2000 | 1.0000 | quá lớn (không dựng) | 0.038850 | **0.038889** | Not Optimal | 0.10% | 28.2 ± 7.8 | 8917 |
| 14 | 250 | 600 | 1.0000 | quá lớn (không dựng) | 0.423910 | **0.434209** | Not Optimal | 2.37% | 0.4 ± 0.1 | 4 |
| 15 | 250 | 600 | 1.0000 | quá lớn (không dựng) | 0.825206 | **0.825206** | Optimal | 0.00% | 0.2 ± 0.0 | 0 |
| 16 | 250 | 4800 | 0.9672 | quá lớn (không dựng) | 0.038593 | **0.038934** | Not Optimal | 0.88% | 841.4 ± 194.5 | 64662 |
| 17 | 300 | 2000 | 1.0001 | quá lớn (không dựng) | 0.424192 | **0.424192** | Optimal | 0.00% | 0.5 ± 0.1 | 0 |
| 18 | 300 | 2000 | 0.6334 | quá lớn (không dựng) | 0.633365 | **0.633365** | Optimal | 0.00% | 0.4 ± 0.1 | 0 |
| 19 | 300 | 6000 | 1.0000 | quá lớn (không dựng) | 0.046838 | **0.046838** | Optimal | 0.00% | 409.0 ± 56.3 | 4921 |
| 20 | 400 | 6000 | 1.0000 | quá lớn (không dựng) | 0.991312 | **0.991312** | Optimal | 0.00% | 4.3 ± 0.5 | 0 |

| Tổng hợp 20 instance | Không waypoint | Phương pháp 1 (*) | **Phương pháp 2** |
|---|---|---|---|
| MLU trung bình | 0.9073 | 0.8393 | **0.4807** |
| MLU trung vị | 1.0000 | 0.9836 | **0.4823** |

Mỗi instance chạy 10 lần. **Optimal** (gap ≤ 0.01%, đã chứng minh) ở **12/20** instance; gap TB ≤ 1% ở 15/20; gap TB lớn nhất 32.84%. Lần chạy lâu nhất mất 1097 s, dưới time limit 1800 s.

### 10.2 Step 9 (t = 0 và t = 1, có budget, time limit 3600 s)

| Inst | n | \|D\| | κ | Không waypoint | Phương pháp 1 | Cận dưới | **MLU (tốt nhất 10 lần)** | Status | Gap TB | CPU TB ± độ lệch (s) | Nút B&B TB | Tốt nhất challenge | Số lần bằng |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 20 | 40 | 51 | 1.0000 | 0.9294 (Opt.) | 0.929384 | **0.929384** | Optimal | 0.00% | 2.3 ± 1.2 | 0 | 0.929383 | 10/10 |
| 02 | 30 | 45 | 63 | 1.0981 | 0.9031 (Opt.) | 0.903075 | **0.903075** | Optimal | 0.00% | 0.0 ± 0.0 | 1 | 0.903074 | 10/10 |
| 03 | 50 | 20 | 53 | 1.0000 | 0.9435 (Optimal 7/10) | 0.633661 | **0.943543** | Not Optimal | 32.84% | 1.1 ± 0.5 | 4 | 0.943543 | 10/10 |
| 04 | 50 | 200 | 44 | 1.0000 | bị dừng (chốt chặn) | 0.581144 | **0.581237** | Not Optimal | 0.02% | 4.8 ± 0.7 | 9102 | 0.581237 | 10/10 |
| 05 | 100 | 100 | 1 | 1.0000 | bị dừng (chốt chặn) | 0.204986 | **0.204986** | Optimal | 0.00% | 0.0 ± 0.0 | 0 | 0.204985 | 10/10 |
| 06 | 100 | 500 | 13 | 1.0000 | bị dừng (chốt chặn 5400 s) | 0.098592 | **0.098592** | Optimal | 0.00% | 3.1 ± 0.9 | 7 | 0.098591 | 10/10 |
| 07 | 100 | 800 | 90 | 1.0000 | quá lớn (không dựng) | 0.907989 | **0.907989** | Optimal | 0.00% | 0.1 ± 0.0 | 0 | 0.907989 | 10/10 |
| 08 | 150 | 200 | 13 | 1.0000 | bị dừng (chốt chặn) | 0.318904 | **0.318904** | Optimal | 0.00% | 0.3 ± 0.0 | 3 | 0.318903 | 10/10 |
| 09 | 150 | 200 | 18 | 1.0000 | bị dừng (chốt chặn) | 0.849650 | **0.849650** | Optimal | 0.00% | 0.1 ± 0.0 | 0 | 0.849650 | 10/10 |
| 10 | 150 | 1000 | 1 | 1.0000 | quá lớn (không dựng) | 0.068323 | **0.071739** | Not Optimal | 4.76% | 22.6 ± 9.6 | 488 | 0.071739 | 10/10 |
| 11 | 200 | 400 | 89 | 1.0000 | quá lớn (không dựng) | 0.785789 | **0.785789** | Optimal | 0.00% | 0.2 ± 0.0 | 0 | 0.785788 | 10/10 |
| 12 | 200 | 400 | 13 | 1.0001 | quá lớn (không dựng) | 0.879873 | **0.879873** | Optimal | 0.00% | 0.2 ± 0.0 | 0 | 0.879872 | 10/10 |
| 13 | 200 | 2000 | 12 | 1.0000 | quá lớn (không dựng) | 0.040793 | **0.041026** | Not Optimal | 0.57% | 366.6 ± 49.8 | 11782 | 0.041025 | 10/10 |
| 14 | 250 | 600 | 13 | 1.0000 | quá lớn (không dựng) | 0.507448 | **0.517621** | Not Optimal | 1.97% | 1.0 ± 0.1 | 22 | 0.517621 | 10/10 |
| 15 | 250 | 600 | 54 | 1.0000 | quá lớn (không dựng) | 0.898696 | **0.898696** | Optimal | 0.00% | 0.4 ± 0.0 | 0 | 0.898695 | 10/10 |
| 16 | 250 | 4800 | 13 | 1.0000 | quá lớn (không dựng) | 0.044057 | **0.044262** | Not Optimal | 0.46% | 1139.5 ± 75.8 | 9755 | 0.044262 | 10/10 |
| 17 | 300 | 2000 | 1 | 1.0001 | quá lớn (không dựng) | 0.424192 | **0.424192** | Optimal | 0.00% | 0.9 ± 0.1 | 0 | 0.424192 | 10/10 |
| 18 | 300 | 2000 | 89 | 1.0000 | quá lớn (không dựng) | 0.999999 | **0.999999** | Optimal | 0.00% | 0.8 ± 0.1 | 0 | 0.999998 | 10/10 |
| 19 | 300 | 6000 | 13 | 1.0000 | quá lớn (không dựng) | 0.046838 | **0.046838** | Optimal 9/10 | 0.38% | 860.6 ± 179.3 | 4004 | 0.046838 | 9/10 |
| 20 | 400 | 6000 | 90 | 1.0000 | quá lớn (không dựng) | 0.991312 | **0.991312** | Optimal | 0.00% | 6.2 ± 0.3 | 0 | 0.991312 | 10/10 |

| Tổng hợp 20 instance | Không waypoint | Phương pháp 1 (*) | **Phương pháp 2** | Tốt nhất challenge |
|---|---|---|---|---|
| MLU trung bình | 1.0049 | 0.9888 | **0.5719** | 0.5719 |
| MLU trung vị | 1.0000 | 1.0000 | **0.6835** | 0.6835 |

Mỗi instance chạy 10 lần. **Optimal** (gap ≤ 0.01%, đã chứng minh) ở **13/20** instance; gap TB ≤ 1% ở 17/20; gap TB lớn nhất 32.84%. Lần chạy lâu nhất mất 1225 s, dưới time limit 3600 s. Ở **19/20** instance, cả 10 lần chạy đều cho đúng MLU tốt nhất của challenge (sai khác ≤ 0.000001 do làm tròn).

(*) Phương pháp 1: Bảng III, IV của báo cáo chính (`results/m1opt/`, máy B). Với instance "quá lớn" hoặc "bị dừng", phương pháp 1 không có nghiệm nào tốt hơn đi thẳng, nên khi tính trung bình ta dùng MLU không waypoint.


### 10.3 So sánh hai phương pháp trên cùng máy B

Số liệu lấy đúng như trong báo cáo chính (Bảng III, IV, VI). Phương pháp 1 dùng `results/m1opt/` (đêm 29/10, CPU = thời gian cả lệnh `optimize!`): mỗi seed một tiến trình, mô hình gốc, chốt chặn TL + 900 s, tối đa 7 lượt song song. Phương pháp 2 dùng `results/runs/`. Quy ước: Obj là tốt nhất 10 lần; CPU và Gap là trung bình (Gap 0 cho lần tối ưu).

| Step | Inst | PP1: Obj | PP1: CPU (s) | PP1: Status | PP1: Gap | PP2: Obj | PP2: CPU (s) | PP2: Status |
|---|---|---|---|---|---|---|---|---|
| 6 | 01 | 0.9294 | 9.0 | Optimal | 0 | 0.9294 | 0.0 | Opt. |
| 6 | 02 | 0.5486 | 545.6 | Opt. 9/10 | 4.51% | 0.5486 | 0.1 | Opt. |
| 6 | 03 | 0.9435 | 91.7 | Optimal | 0 | 0.9435 | 0.1 | Not Opt. (32.84%) |
| 6 | 04 | 0.5467 | 1847 * | Not Opt. | 31.88% | 0.4591 | 0.5 | Not Opt. (0.011%) |
| 6 | 05 | 0.1155 | 1736 * † | Opt. 2/10 | 59.15% | 0.1155 | 0.0 | Opt. |
| 9 | 01 | 0.9294 | 148.1 | Optimal | 0 | 0.9294 | 2.3 | Opt. |
| 9 | 02 | 0.9031 | 236.5 | Optimal | 0 | 0.9031 | 0.0 | Opt. |
| 9 | 03 | 0.9435 | 2034 | Opt. 7/10 | 8.69% | 0.9435 | 1.1 | Not Opt. (32.84%) |

Ký hiệu:
- `*`: HiGHS tự chạy quá time limit hơn 2% ở ít nhất một lần.
- `†`: có lượt bị chốt chặn dừng ở 2700 s. Các lượt này được tính với Gap 100% và không tính vào CPU.

Nhận xét:

- Phương pháp 1 trên máy B **tái lập giá trị tốt nhất của máy A** ở mọi instance chạy trên cả hai máy. Trạng thái chỉ khác ở những chỗ phụ thuộc tải máy:
  - Step 6 setA-02: tối ưu 9/10 lần trên máy B, 10/10 trên máy A;
  - Step 6 setA-05: tối ưu 2/10 lần trên máy B, 6/10 trên máy A;
  - Step 6 setA-09: trả về có cận dưới 0.5054 trên máy B, bị chốt chặn dừng trên máy A.
- Trên cùng máy, phương pháp 2 cần tối đa 2.3 s trung bình (phần lớn là biên dịch Julia ở setA-01), so với 9.0–2034 s của phương pháp 1, và cho cùng giá trị. Riêng setA-04 Step 6, phương pháp 2 tìm được 0.4591 thay vì 0.5467.
- CPU của phương pháp 1 là thời gian thực của **cả lệnh `optimize!`** (chép mô hình vào HiGHS + giải; không tính dựng mô hình JuMP, tối đa 8.4 s ở 01–05), đo sau một lần giải khởi động trên toy. Riêng phần chép mô hình tốn 1–8 s ở 01–03, 30–78 s ở 04, 05 và 372–563 s ở 06–09. CPU của phương pháp 2 gồm cả việc dựng các MILP, nên phép so sánh không thiên vị phương pháp 2.
- Status chỉ khác ở setA-03: phương pháp 1 chứng minh được tối ưu, còn cận dưới của phương pháp 2 yếu (mục 5.3).

## 11. Cách chạy và tham số

**Trực tiếp** (cần Julia, xem [CAI_DAT_VA_CHAY.md](CAI_DAT_VA_CHAY.md)):

```bash
scripts/run.sh cg6 all          # Step 6 cho cả 20 instance
scripts/run.sh cg9 1 2 3        # Step 9 cho setA-01, 02, 03
THREADS=8 scripts/run.sh cg9 all
```

**Bằng Docker** (build lại image sau khi đổi code; bước cài thư viện có cache nên nhanh):

```bash
docker build -t orange-tasr .
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/results:/app/results" -e THREADS=8 orange-tasr cg9 all
```

**Kết quả** nằm trong `results/cg/`:

- `cg_step6.csv`, `cg_step9.csv`: một dòng cho mỗi instance. Cột: `instance,n,m,D,kappa,seed,status,mlu_nowp,lp,lb,ub,gap,mlu_t0,mlu_t1,budget_used,cg_iters,cols,nodes,cpu_s,cg_s,milp_s,total_s`.
  - `status`: `Optimal` nếu gap ≤ 10⁻⁴ (0.01%), tức đã chứng minh tối ưu bằng cận dưới, sai khác chỉ do làm tròn số thực. Đây cũng là ngưỡng `mip_rel_gap` mặc định của HiGHS mà phương pháp 1 dùng để báo "Optimal". Ngược lại là `Not Optimal`.
  - `nodes`: tổng số nút branch-and-bound của mọi MILP mà HiGHS giải (MILP trên tập cột và các MILP trong vòng cải thiện).
  - `cpu_s`: thời gian giải, tính từ lúc bắt đầu sinh cột tới hết vòng cải thiện. Không tính đọc JSON và tính r, tương tự "chỉ tính lệnh optimize!" của đề.
  - `total_s`: tổng thời gian của instance, gồm cả đọc dữ liệu.
- `setA-XX-step{6,9}-srpaths.json`: nghiệm.
- `cg6.log`, `cg9.log`: nhật ký từng vòng.

Instance đã có trong CSV sẽ được bỏ qua. Đặt `FORCE=1` để chạy lại. Có thể chỉ định thứ tự instance, ví dụ `scripts/run.sh cg9 20 19 16 13`.

**Chạy 10 lần (yêu cầu "average on ten runs" của đề):**

```bash
results/runs/run_10.sh                                   # seed 0..9 cho Step 9 và Step 6, 8 lượt song song
python3 src/aggregate_cg.py results/runs                 # tổng hợp: trung bình qua 10 lần chạy
```

- Mỗi lần chạy dùng một `SEED` khác, truyền vào `random_seed` của HiGHS cho các MILP. Kết quả của seed k nằm ở `results/runs/seed<k>/cg/`.
- Trong mỗi lượt, instance chạy **từ lớn đến bé** (theo số biến của mô hình MILP đầy đủ): 20, 19, 16, 18, 17, 13, 15, 14, 10, 12, 11, 7, 6, 9, 8, 5, 4, 3, 2, 1.
- Script tổng hợp ghi `results/cg/cg_step{6,9}_10runs.csv`, `results/cg/cg_10runs.md` và bảng LaTeX `report/table_cg_step{6,9}.tex` (cho bản nháp cũ). Bảng VI của báo cáo chính do `report/paper/make_tables_cg.py` sinh.
- Toàn bộ quy trình đã dùng cho báo cáo (kể cả các script chạy lại): [TAI_TAO_KET_QUA.md](TAI_TAO_KET_QUA.md), mục 2.

**Tham số** (biến môi trường):

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `THREADS` | 8 | Số luồng cho DP pricing (chạy song song theo nguồn hoặc demand) |
| `CG_TIME` | 600 | Giới hạn thời gian sinh cột (giây) |
| `MILP_TIME` | 300 | Giới hạn MILP trên tập cột. Mỗi vòng cải thiện dùng tối đa min(MILP_TIME, 120) |
| `IMP_TIME` | 780 (Step 6), 2400 (Step 9) | Giới hạn cho cả vòng cải thiện |
| `RESULTS_DIR` | results | Kết quả ghi vào `<RESULTS_DIR>/cg/` |
| `FORCE` | 0 | 1 = chạy lại instance đã có |

Tổng ba giới hạn là 600 + 300 + 780 = 1680 s cho Step 6 và 600 + 300 + 2400 = 3300 s cho Step 9, nằm dưới time limit 1800 s và 3600 s của đề. Ban đầu `IMP_TIME` là 600 s cho cả hai bước. Khi chạy 10 lần song song, vòng cải thiện của setA-19 (Step 9) ở 2/10 seed bị cắt lúc vẫn đang cải thiện, nên giới hạn được nâng lên để dùng hết thời gian đề cho phép. Các lượt bị cắt (setA-16 ở cả hai bước, setA-19 seed 2 và 4) đã được chạy lại với giới hạn mới bằng `results/runs/rerun_timelimited.sh`. Các lượt còn lại của setA-19 (Step 9) và setA-16 (Step 6, seed 6–8) được chạy lại bằng `results/runs/rerun_uniform.sh`, để mọi lượt của hai instance này dùng cùng cấu hình. Các lượt khác dừng trước 600 s, vì đạt cận dưới hoặc không cải thiện được nữa, nên giới hạn không ràng buộc chúng.

**Tính lặp lại:** phần sinh cột tất định. Các MILP dừng theo giới hạn thời gian thực, nên cùng seed có thể cho kết quả khác giữa hai lần chạy, tuỳ tải máy. Ví dụ ở setA-19 Step 9: seed 2 và 4 không đạt tối ưu ở lượt đầu nhưng đạt khi chạy lại; seed 6 ngược lại.

## 12. Giới hạn và lưu ý khi viết báo cáo

- **Số nút branch-and-bound** ở phương pháp 2 là tổng số nút của các MILP trên tập cột, không phải của một cây B&B trên mô hình đầy đủ. Ở đa số instance, số này bằng 0 hoặc vài chục, vì MILP trên tập cột nhỏ và cận `U ≥ LB` giúp dừng sớm. Ở các instance khó (04, 10, 13, 16, 19), số nút lên tới vài nghìn, vì các MILP trong vòng cải thiện phải rẽ nhánh. Khi viết báo cáo, nên trình bày phương pháp 2 như **phương pháp bổ sung** bên cạnh MILP đầy đủ.
- **Gap dùng cận dưới đã chứng minh** (mục 5), nên hợp lệ theo công thức của đề. Gap lớn ở setA-03 là do cận yếu, không phải do nghiệm kém (mục 5.3).
- **Không chứng minh tối ưu ở mọi instance:** khi gap > 0 thì chỉ biết nghiệm cách tối ưu không quá gap đó. Ở Step 9, giá trị tốt nhất qua 10 lần của cả 20 instance bằng kết quả tốt nhất mà các đội của challenge tìm được.
- **Vòng cải thiện có thể dừng sớm:** ở setA-19 (Step 9, seed 6), MILP của 3 vòng cuối đều chạm giới hạn 120 s mà không cải thiện, nên vòng lặp dừng ở 0.048712 dù còn khoảng 1 600 s trong ngân sách 2 400 s; 9 seed còn lại (cùng cấu hình) đạt 0.046838, và chính seed 6 cũng đạt 0.046838 ở lượt chạy đầu. Vòng có MILP chạm giới hạn thời gian nên được coi là "chưa kết luận" thay vì "không cải thiện"; đó là hướng cải tiến tự nhiên. Kết quả được báo cáo trung thực, không chạy lại để chọn số đẹp.
- **Chỉ sinh path không đi vòng:** phương pháp 2 chỉ sinh path không qua nút nào hai lần. Khi có budget, nghiệm tối ưu có thể cần một path đi vòng (Benhamiche et al. 2026; báo cáo mục IV-D), nên khi đó phương pháp 2 có thể bỏ lỡ tối ưu. Cận dưới vẫn hợp lệ, vì nó tính trên mọi path.
- **"Trung bình 10 lần chạy":** đã chạy 10 lần với seed 0..9 (mục 10). Phần sinh cột cho cùng kết quả mỗi lần, nên khác biệt giữa các lần chủ yếu đến từ các MILP chạm giới hạn thời gian (setA-13, 16, 19).
- **CPU time** (`cpu_s`) là thời gian thực (wall clock) của phần giải. 10 lần chạy được chạy 8 lượt song song, mỗi lượt 2 luồng, trên máy 16 luồng (8 nhân). Vì vậy thời gian có thể dài hơn một chút so với khi chạy riêng một lượt. Đã kiểm tra trên setA-13 (Step 9): 271–425 s khi chạy song song, so với 413 s khi chạy riêng.
- **Mục tiêu là MLU** (thành phần đầu của vector tải), đúng như đề của môn học. Challenge thật xếp hạng theo **toàn bộ vector tải** (lex-min), nên phương pháp này chưa tối ưu phần "đuôi" của vector.
- **Sai số so sánh khoảng cách 10⁻⁹ (tương đối):** trên cả 20 instance và hai chu kỳ, hai độ dài thật sự bằng nhau chỉ lệch tương đối tối đa 4.7·10⁻¹⁶ (setA-14), còn hai độ dài khác nhau lệch tương đối ít nhất 2.7·10⁻⁶ (setA-19). Ngưỡng 10⁻⁹ nằm xa cả hai phía, nên an toàn. Đã kiểm lại ngày 29/10 bằng chính hàm tính khoảng cách của code.

## 13. Từ công thức sang code

| Thành phần | Hàm | File |
|---|---|---|
| r dạng thưa theo cặp nút | `to_csr` | `src/colgen.jl` |
| Giá segment W(i, j) | `seg_weights!` | `src/colgen.jl` |
| DP Bellman–Ford ≤ maxSeg (mục 4.3) | `dp1!` (một chu kỳ), `dp2!` (path chung hai chu kỳ), `getpath` | `src/colgen.jl` |
| Master LP qua HiGHS C API (mục 3.2, 6.1) | `Master`, `add_column!`, `solve_master!` | `src/colgen.jl` |
| Vòng sinh cột và cận Lagrange (mục 4, 5.1, 6.2) | `colgen` | `src/colgen.jl` |
| Kiểm tra độc lập (mục 9) | `evaluate` | `src/colgen.jl` |
| Cận một demand (mục 5.2) | `single_demand_lb`, `bdp!`, `seg_bneck!` | `src/improve.jl` |
| Làm tròn LP (mục 7.1) | `round_start` | `src/improve.jl` |
| MILP trên tập cột (mục 7.2) | `milp_pool` (Step 6), `milp_pairs` (Step 9) | `src/improve.jl` |
| Sinh path quanh link nghẽn (mục 8) | `add_candidates!` | `src/improve.jl` |
| Vòng cải thiện (mục 8) | `improve` | `src/improve.jl` |
| Chạy toàn bộ, ghi CSV và nghiệm | `main` | `src/run_cg.jl` |
| Kiểm tra bằng Python | | `src/verify_srpaths.py` |

## 14. Tài liệu tham khảo

- Jadin, Aubry, Schaus, Bonaventure, *CG4SR: Near Optimal Traffic Engineering for Segment Routing with Column Generation*, IEEE INFOCOM 2019. Pricing bằng DP theo số segment; gap thường dưới 1% trên các mạng ISP thật.
- Jaumard, Tran, Ziazet, *Segment Routing Traffic Engineering with Time-Based Reconfiguration Constraints*, arXiv 2610.04759, 2026. Column generation trên chính SetA, giải tuần tự t = 0 rồi t = 1.
- Bouaachra, *Lexicographic Minimax Load Balancing for T-Adaptive Segment Routing*, arXiv 2609.36338, 2026. Branch-and-price (mục tiêu lex) trên cột "quỹ đạo": một cột là bộ path theo từng chu kỳ (t = 0, t = 1) với chi phí thay đổi là hằng số, nên budget thành một dòng tuyến tính chính xác.
- Benhamiche et al., *On the T-Adaptive Segment Routing Problem*, arXiv 2609.32896, 2026. Mô hình (1)–(4) của đề.
- Kết quả vòng sprint và checker chính thức: <https://gitlab.com/Orange-OpenSource/network-optimization-tools/challenge-roadef-2026> (thư mục `sprint_results/` và `checker/`).
- Danh sách đầy đủ hơn: [survey.md](survey.md).
