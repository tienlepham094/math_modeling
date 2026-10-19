# Project Orange – ROADEF/EURO Challenge 2026 "Keep The Flow!"

Bài toán: **T-Adaptive Segment Routing (T-ASR)**. Ngôn ngữ dùng: **Julia** (JuMP và một solver MILP; notebook dùng Pluto).
Tài liệu gốc: `Challenge_Orange_ROADEF_2026_Subject.pdf`, hướng dẫn của giảng viên: `readme.txt`.

> **Hạn nộp: Chủ nhật 25/10/2026.** (Hạn đăng ký nhóm qua Google Form là thứ Sáu 09/10, đã qua.)

**Mục lục**
1. [Bối cảnh: bài toán đến từ đâu](#1-bối-cảnh-bài-toán-đến-từ-đâu)
2. [Các khái niệm, giải thích từng cái](#2-các-khái-niệm-giải-thích-từng-cái)
3. [Ví dụ toy, tính tay từ đầu đến cuối](#3-ví-dụ-toy-tính-tay-từ-đầu-đến-cuối)
4. [Mô hình toán học](#4-mô-hình-toán-học)
5. [Định dạng dữ liệu](#5-định-dạng-dữ-liệu)
6. [Cài đặt bằng Julia](#6-cài-đặt-bằng-julia)
7. [Những việc cần làm (Step 1 → 9 và báo cáo)](#7-những-việc-cần-làm)

---

## 1. Bối cảnh: bài toán đến từ đâu

Orange quản lý các mạng backbone IP/MPLS có hàng nghìn router và link. Mỗi năm mạng phục vụ hàng chục nghìn **luồng lưu lượng** (demand) giữa các cặp điểm.

**Cách định tuyến truyền thống.** Mỗi link được gán một trọng số `ω` (metric). Gói tin đi theo **đường ngắn nhất** tính theo `ω`. Cách này đơn giản, nhưng nhiều luồng thường dồn vào cùng vài link, làm các link đó **nghẽn** trong khi link khác lại rảnh. Muốn sửa thì phải chỉnh lại toàn bộ trọng số, việc này rất khó.

**Segment Routing (SR).** Tại nút nguồn, ta ghi vào header của gói tin một danh sách **waypoint** (nút bắt buộc phải đi qua). Gói tin đi theo đường ngắn nhất từ nguồn tới waypoint 1, rồi theo đường ngắn nhất từ waypoint 1 tới waypoint 2, v.v., cho tới đích. Chỉ cần chọn waypoint là "lái" được luồng tránh link nghẽn, không phải sửa trọng số.

**Bảo trì.** Theo thời gian, một số link sẽ bị **tắt để bảo trì**. Khi đó đường ngắn nhất thay đổi và có thể gây nghẽn chỗ khác. Ta được phép đổi waypoint giữa các chu kỳ, nhưng mỗi thay đổi tốn công vận hành, nên **số thay đổi bị giới hạn** (budget).

**Câu hỏi của bài toán.** Với mỗi demand và mỗi chu kỳ thời gian, chọn danh sách waypoint sao cho **tải lớn nhất trên các link (MLU) là nhỏ nhất**, đồng thời tôn trọng giới hạn số segment và giới hạn số thay đổi.

---

## 2. Các khái niệm, giải thích từng cái

### 2.1 Mạng `(G = (V, A), ω, c)`
- `V`: tập nút (router), `n = |V|`.
- `A`: tập cung có hướng (link). Link hai chiều được tách thành **2 cung** riêng, mỗi cung có metric và capacity riêng.
- `ω(a)`: trọng số (metric) dùng để tính đường ngắn nhất.
- `c(a)`: dung lượng (bandwidth) của cung.

### 2.2 Forwarding graph `FG(u, v)` và ECMP
- `FG(u, v)` là đồ thị con gồm **tất cả các cung nằm trên ít nhất một đường ngắn nhất** từ `u` đến `v`.
- Nếu có nhiều đường ngắn nhất, cơ chế **ECMP** (Equal-Cost Multi-Path) chia luồng theo quy tắc: **tại mỗi nút, luồng đi vào được chia đều cho các cung đi ra của nút đó trong `FG(u,v)`.**
- Lưu ý: luồng được chia đều **theo từng nút**, không phải đều cho mọi đường. Vì vậy ba đường ngắn nhất có thể nhận các tỉ lệ 1/2, 1/4, 1/4 thay vì 1/3 mỗi đường (xem ví dụ toy).

**Kiểm tra một cung có thuộc `FG(u,v)` không.** Gọi `dist(x)` là độ dài đường ngắn nhất từ `x` đến `v`. Cung `a = (x, y)` thuộc forwarding graph tới `v` khi và chỉ khi `dist(x) = ω(a) + dist(y)`.

### 2.3 Split coefficient `r(u, v, a, t)` (tham số quan trọng nhất)
- `r(u, v, a, t)` là **tỉ lệ** của 1 đơn vị luồng gửi từ `u` đến `v` (theo ECMP, trên đồ thị `G_t`) đi qua cung `a`.
- `r ∈ [0, 1]`, và `r = 0` nếu `a ∉ FG(u,v)`.
- Phải tính `r` cho **mọi cặp** `(u, v)`, không chỉ các cặp nguồn/đích của demand, vì bất kỳ cặp nút nào cũng có thể trở thành một segment.
- `r` **không phải biến** mà là **dữ liệu tính trước**. Nhờ vậy mô hình tối ưu là tuyến tính.

### 2.4 Segment path và segment
- **Segment path** `⟨s, w1, …, wℓ, t⟩`: nguồn `s`, các waypoint `w1…wℓ` theo thứ tự, đích `t`. `ℓ = 0` nghĩa là đi thẳng theo đường ngắn nhất.
- **Segment**: cặp hai nút liên tiếp trong segment path, ví dụ `(s, w1), (w1, w2), …, (wℓ, t)`. Một path có `ℓ` waypoint sẽ có `ℓ + 1` segment.
- Mỗi segment `(i, j)` được định tuyến bằng `FG(i, j)` và ECMP.
- `maxSeg`: số segment tối đa (thường 4 đến 10), tức tối đa `maxSeg − 1` waypoint.

**Góc nhìn quan trọng cho việc mô hình hoá.** Tưởng tượng một **đồ thị đầy đủ `H`** trên cùng tập nút `V`, trong đó mỗi cặp `(i, j)` là một "cung ảo" (một segment). Khi đó **chọn segment path cho demand `(s,t)` chính là chọn một đường đi từ `s` đến `t` trong `H` có tối đa `maxSeg` cung.** Chọn đường đi thì mô hình bằng ràng buộc bảo toàn luồng, đây là kỹ thuật quen thuộc.

### 2.5 Demand và traffic matrix
- Demand `d = (s, t)` có lưu lượng `ν(d, t)` thay đổi theo chu kỳ thời gian `t`.
- Lưu ý: trong đề, chữ `t` vừa chỉ **đích** của demand vừa chỉ **chu kỳ thời gian**. Cần đọc kỹ ngữ cảnh.

### 2.6 Thời gian, intervention, budget
- `T = {0, 1, …, h−1}`. **`t = 0` là trạng thái bình thường**: không có link nào bị tắt và không có budget. `T* = T \ {0}`.
- `q(t)`: tập các cung bị tắt tại chu kỳ `t`. `G_t` là đồ thị `G` sau khi bỏ các cung trong `q(t)`. **Vì đồ thị thay đổi nên đường ngắn nhất thay đổi, và phải tính lại `r(·,·,·,t)` trên `G_t`.**
- `κ(t)`: số thay đổi tối đa giữa chu kỳ `t−1` và `t`.
- **Cách đếm thay đổi**: `dist(P, P′)` = số segment **bị thêm** + số segment **bị bỏ**.

| Trước | Sau | Segment bỏ | Segment thêm | dist |
|---|---|---|---|---|
| ⟨s,w,t⟩ | ⟨s,t⟩ | (s,w), (w,t) | (s,t) | 3 |
| ⟨s,w1,w2,t⟩ | ⟨s,w1,t⟩ | (w1,w2), (w2,t) | (w1,t) | 3 |
| ⟨s,w1,w2,t⟩ | ⟨s,w2,w1,t⟩ | 3 segment | 3 segment | 6 |
| ⟨s,w1,t⟩ | ⟨s,w2,t⟩ | 2 | 2 | 4 |

### 2.7 Tải (load) và MLU
- Tải của cung `a` tại chu kỳ `t` là tổng luồng đi qua cung chia cho dung lượng:

  `λ(a,t) = ( Σ_d Σ_{(i,j) ∈ segment của d} r(i,j,a,t) · ν(d,t) ) / c(a)`

- `λ > 1` nghĩa là link quá tải (nghẽn).
- **MLU** (Maximum Link Utilization) là `max_a λ(a,t)`, tức tải của link nặng nhất.

---

## 3. Ví dụ toy, tính tay từ đầu đến cuối

Mạng có 7 nút `v0…v6` và 22 cung (xem `toy-net.json` ở mục 5). Có hai demand:

| Demand | Nguồn → đích | ν tại t=0 | ν tại t=1 |
|---|---|---|---|
| d0 | v0 → v5 | 50 | 100 |
| d1 | v2 → v5 | 100 | 50 |

`maxSeg = 4`. Tại t=1, link 2 (`v1→v3`) và link 3 (`v1→v4`) bị tắt. Budget `κ(1) = 20`.

### 3.1 Tính `r(v0, v5, ·, 0)`

**Bước 1: Dijkstra ngược từ v5**, tìm khoảng cách ngắn nhất từ mỗi nút đến v5:

| nút | v3 | v6 | v4 | v1 | v2 | v0 |
|---|---|---|---|---|---|---|
| dist→v5 | 100 | 100 | 200 (qua v3 hoặc v6) | 300 (qua v3 hoặc v4) | 300 (qua v4) | 400 (qua v1) |

**Bước 2: Đẩy 1 đơn vị luồng từ v0**, xét các nút theo thứ tự `dist` giảm dần:
- Tại v0: chỉ có cung `v0→v1` thoả `100 + 300 = 400`. Cung `v0→v2` cho `200 + 300 = 500`, không thoả. Vậy `r(a0,1) = 1`.
- Tại v1: cả `v1→v3` (`200 + 100`) và `v1→v4` (`100 + 200`) đều bằng 300. Chia đôi: `r(a1,3) = r(a1,4) = 0.5`.
- Tại v4 (nhận 0.5): `v4→v3` và `v4→v6` thoả, còn `v4→v5` (`300 ≠ 200`) không thoả. Chia đôi: `r(a4,3) = r(a4,6) = 0.25`.
- Tại v3 (nhận 0.5 + 0.25): `r(a3,5) = 0.75`.
- Tại v6 (nhận 0.25): `r(a6,5) = 0.25`.

Kết quả khớp **Table 2** của đề. Tương tự, `r(v2, v5, ·, 0)` = `{a2,4: 1, a4,3: 0.5, a4,6: 0.5, a3,5: 0.5, a6,5: 0.5}`.

### 3.2 Tải khi không dùng waypoint (t=0)

`λ(a3,5) = (0.75·50 + 0.5·100) / 200 = 87.5 / 200 = 0.4375`. Đây là cung nặng nhất, nên **MLU = 0.4375**.
`λ(a4,6) = (0.25·50 + 0.5·100) / 200 = 0.3125`. Đây là ví dụ trong đề.

### 3.3 Thêm waypoint v4 cho d0: ⟨v0, v4, v5⟩

- Segment `(v0, v4)` đi `v0→v1→v4`, với tỉ lệ 1 trên mỗi cung.
- Segment `(v4, v5)` chia đôi qua `v4→v3→v5` và `v4→v6→v5`.
- Kết quả: `λ(a3,5) = (25 + 50) / 200 = 0.375` và `λ(a4,6) = (25 + 50) / 200 = 0.375`. **MLU giảm từ 0.4375 xuống 0.375.** (Waypoint v2 cũng cho 0.375.)
- Đổi lại, một số cung khác lại tăng tải (Figure 4 của đề). Đó là bản chất của bài toán: phải **cân bằng** tải giữa các link.

### 3.4 Tại t=1 (link v1→v3 và v1→v4 bị tắt)

- Từ v1 giờ chỉ còn đi được về v0, nên mọi luồng từ v0 phải đi `v0→v2→v4→{v3, v6}→v5`.
- Phải **tính lại `r` trên `G_1`**.
- Không dùng waypoint thì MLU tại t=1 là 0.375, với `λ(a0,2) = 100/300 ≈ 0.333` và `λ(a2,4) = 150/400 = 0.375`.

---

## 4. Mô hình toán học

### 4.1 Dữ liệu (tham số)

| Ký hiệu | Lấy từ | Ý nghĩa |
|---|---|---|
| `V, A` | net.json | nút, cung |
| `c(a)` | net.json (`capacity`) | dung lượng |
| `ω(a)` | net.json (`metric`) | chỉ dùng để tính `r` |
| `r(i,j,a,t)` | **tự tính** từ `G_t` và `ω` | split coefficient |
| `D, s_d, t_d` | tm.json | các demand |
| `ν(d,t)` | tm.json (`v[t]`) | lưu lượng |
| `maxSeg` | scenario.json | số segment tối đa |
| `q(t), κ(t)` | scenario.json | link bị tắt, budget |

### 4.2 Biến

- `x[d,t,i,j] ∈ {0,1}`: bằng 1 nếu segment path của demand `d` tại chu kỳ `t` **chứa segment `(i,j)`** (với `i ≠ j`). Đây là cung `(i,j)` trong đồ thị đầy đủ `H`.
- `U ≥ 0`: MLU cần cực tiểu.
- (Chỉ dùng khi có budget) `y[d,t,i,j] ≥ 0`: biến phụ để tuyến tính hoá `|x^t − x^{t−1}|`.

### 4.3 Hàm mục tiêu

- Đề gốc dùng **lex-min**: cực tiểu tải lớn nhất, sau đó tải lớn thứ hai, v.v., trên mọi `(a, t)`. Mục tiêu này rất khó cài trực tiếp.
- Trong project này dùng phiên bản chuẩn là **cực tiểu MLU**:

  `min U`  với  `λ(a,t) ≤ U` cho mọi `a, t`.

- Đây là thành phần đầu tiên (quan trọng nhất) của lex-min, nên một nghiệm tối ưu lex-min cũng tối ưu theo MLU.

### 4.4 Ràng buộc

**(1) Bảo toàn luồng.** Mỗi demand `d` tại mỗi chu kỳ `t` phải chọn đúng một đường từ `s_d` đến `t_d` trong `H`:

```
Σ_{j≠i} x[d,t,i,j] − Σ_{j≠i} x[d,t,j,i] =  1   nếu i = s_d
                                         = −1   nếu i = t_d
                                         =  0   nếu khác
        ∀ i ∈ V, ∀ d ∈ D, ∀ t ∈ T
```

Ý nghĩa: tại nguồn có một segment đi ra nhiều hơn đi vào, tại đích có một segment đi vào nhiều hơn đi ra, và tại waypoint thì "vào bao nhiêu, ra bấy nhiêu".

**(2) Số segment.**

```
Σ_{i,j} x[d,t,i,j] ≤ maxSeg      ∀ d, t
```

**(3) Tải** (tuyến tính vì `r` và `ν` là hằng số):

```
Σ_d Σ_{i≠j} r(i,j,a,t) · ν(d,t) · x[d,t,i,j] ≤ U · c(a)      ∀ t ∈ T, ∀ a ∈ A \ q(t)
```

**(4) Budget** (chỉ áp dụng khi `t ≥ 1`):

```
Σ_d Σ_{i≠j} | x[d,t,i,j] − x[d,t−1,i,j] | ≤ κ(t)      ∀ t ∈ T*
```

Trị tuyệt đối không tuyến tính, nên ta **tuyến tính hoá** bằng biến phụ `y`:

```
y[d,t,i,j] ≥ x[d,t,i,j] − x[d,t−1,i,j]
y[d,t,i,j] ≥ x[d,t−1,i,j] − x[d,t,i,j]
Σ_d Σ_{i≠j} y[d,t,i,j] ≤ κ(t)
```

Vì `y ≥ |…|` và tổng `y` bị chặn trên, mọi nghiệm khả thi đều thoả (4).

### 4.5 Những điểm tinh tế khi cài đặt

1. **Segment không có đường đi.** Nếu trong `G_t` từ `i` không đến được `j` thì `FG(i,j)` rỗng, nên segment `(i,j)` **không được dùng**. Cách xử lý: đặt `x[d,t,i,j] = 0`, hoặc đơn giản là không tạo biến đó.
2. **Cung bị tắt.** `r` được tính trên `G_t`, nên cung trong `q(t)` luôn có `r = 0` và không mang tải.
3. **Chu trình.** Ràng buộc (1) có thể cho phép thêm một chu trình rời khỏi đường `s → t`. Vì chu trình chỉ làm tăng tải, solver thường không chọn. Dù vậy, khi đọc nghiệm thành danh sách waypoint thì chỉ đi theo đường từ `s`.
4. **Kích thước mô hình.** Số biến `x` là khoảng `|D| · n · (n−1) · |T|`. Ví dụ với `n = 50` và `|D| = 500` thì có khoảng 1.2 triệu biến cho mỗi chu kỳ. Nên:
   - chỉ tạo biến cho các cặp `(i,j)` có đường đi;
   - lưu `r` dạng **thưa** (chỉ giữ các phần tử khác 0);
   - với mỗi cung `a`, chuẩn bị sẵn danh sách các segment đi qua nó để dựng ràng buộc (3) cho nhanh.
5. **Đánh chỉ số trong Julia.** JSON dùng ID bắt đầu từ 0, còn Julia đánh chỉ số từ 1. Nên tạo bảng ánh xạ `id → index` một lần duy nhất.

---

## 5. Định dạng dữ liệu

Mỗi instance gồm 3 file JSON.

**`*-net.json`** (dạng NetworkX): `nodes` (`id`, `name`) và `links` (`id`, `from`, `to`, `metric`, `capacity`).

```json
{ "directed": true, "multigraph": false,
  "nodes": [ {"name": "A", "id": 0}, ... ],
  "links": [ {"id": 0, "from": 0, "to": 1, "metric": 100, "capacity": 400}, ... ] }
```

**`*-tm.json`**: ID của demand là vị trí của nó trong danh sách, bắt đầu từ 0. `v[k]` là lưu lượng tại chu kỳ `k`.

```json
{ "num_time_slots": 2,
  "demands": [ { "v": [50.0, 100.0], "s": 0, "t": 5 },
               { "v": [100.0, 50.0], "s": 2, "t": 5 } ] }
```

**`*-scenario.json`**: chu kỳ t=0 không xuất hiện trong file vì budget tại đó là vô hạn và không có link nào bị tắt.

```json
{ "max_segments": 4,
  "budget":        [ { "t": 1, "value": 20 } ],
  "interventions": [ { "t": 1, "links": [2, 3] } ] }
```

**Output** `*-srpaths.json` (tuỳ chọn): `{"srpaths": [ {"d": 0, "t": 0, "w": [3]}, ... ]}`. Được phép bỏ qua các entry có danh sách waypoint rỗng.


<details>
<summary>3 file JSON của instance toy (chép từ PDF, dùng để test)</summary>

`toy-net.json`
```json
{
"directed": true, "multigraph": false,
"nodes": [ {"name": "A", "id": 0}, {"name": "B", "id": 1}, {"name": "C", "id": 2},
           {"name": "D", "id": 3}, {"name": "E", "id": 4}, {"name": "F", "id": 5},
           {"name": "G", "id": 6} ],
"links": [
{"id": 0, "from": 0, "to": 1, "metric": 100, "capacity": 400},
{"id": 1, "from": 0, "to": 2, "metric": 200, "capacity": 300},
{"id": 2, "from": 1, "to": 3, "metric": 200, "capacity": 200},
{"id": 3, "from": 1, "to": 4, "metric": 100, "capacity": 200},
{"id": 4, "from": 2, "to": 4, "metric": 100, "capacity": 400},
{"id": 5, "from": 2, "to": 6, "metric": 300, "capacity": 200},
{"id": 6, "from": 3, "to": 5, "metric": 100, "capacity": 200},
{"id": 7, "from": 3, "to": 4, "metric": 100, "capacity": 200},
{"id": 8, "from": 4, "to": 5, "metric": 300, "capacity": 200},
{"id": 9, "from": 4, "to": 6, "metric": 100, "capacity": 200},
{"id": 10, "from": 5, "to": 6, "metric": 100, "capacity": 200},
{"id": 11, "from": 1, "to": 0, "metric": 100, "capacity": 400},
{"id": 12, "from": 2, "to": 0, "metric": 200, "capacity": 300},
{"id": 13, "from": 3, "to": 1, "metric": 200, "capacity": 200},
{"id": 14, "from": 4, "to": 1, "metric": 100, "capacity": 200},
{"id": 15, "from": 4, "to": 2, "metric": 100, "capacity": 400},
{"id": 16, "from": 6, "to": 2, "metric": 300, "capacity": 200},
{"id": 17, "from": 5, "to": 3, "metric": 100, "capacity": 200},
{"id": 18, "from": 4, "to": 3, "metric": 100, "capacity": 200},
{"id": 19, "from": 5, "to": 4, "metric": 300, "capacity": 200},
{"id": 20, "from": 6, "to": 4, "metric": 100, "capacity": 200},
{"id": 21, "from": 6, "to": 5, "metric": 100, "capacity": 200}
]
}
```

`toy-tm.json`
```json
{ "num_time_slots": 2,
  "demands": [ { "v": [50.0, 100.0], "s": 0, "t": 5 },
               { "v": [100.0, 50.0], "s": 2, "t": 5 } ] }
```

`toy-scenario.json`
```json
{ "max_segments": 4,
  "budget": [ { "t": 1, "value": 20 } ],
  "interventions": [ { "t": 1, "links": [2, 3] } ] }
```
</details>

---

## 6. Cài đặt bằng Julia

> Các đoạn code dưới đây là **khung tham khảo**, viết theo đúng mô hình ở mục 4. Chúng **chưa được chạy thử** vì máy hiện chưa cài Julia. Thuật toán tính `r` đã được kiểm chứng bằng một bản Python tương đương trên instance toy. Sau khi cài Julia, nên chạy lại phần kiểm thử ở mục 6.6.

### 6.1 Môi trường

```julia
using Pkg
Pkg.add(["JSON", "JuMP", "HiGHS", "Pluto"])   # HiGHS miễn phí; nếu có license thì thêm "Gurobi"
# Mở notebook: using Pluto; Pluto.run()
```

- **Solver.** Nếu được, nên dùng **Gurobi** hoặc **CPLEX** (có license học thuật miễn phí), vì chúng nhanh hơn HiGHS rất nhiều với MILP lớn. Ba giá trị gap, bound và số nút B&B đều lấy được qua JuMP.
- **Pluto.** Script Pluto mà giảng viên cung cấp là một notebook Julia (file `.jl`). Mở bằng `Pluto.run()`.

### 6.2 Đọc dữ liệu (Step 4)

```julia
using JSON

struct Instance
    n::Int                       # số nút
    m::Int                       # số cung
    from::Vector{Int}            # from[a], to[a]: chỉ số nút 1..n
    to::Vector{Int}
    w::Vector{Float64}           # metric ω(a)
    c::Vector{Float64}           # capacity c(a)
    src::Vector{Int}             # nguồn / đích của demand d
    dst::Vector{Int}
    vol::Matrix{Float64}         # vol[d, t+1] = ν(d, t)
    maxSeg::Int
    budget::Dict{Int,Int}        # t => κ(t)
    down::Dict{Int,Vector{Int}}  # t => chỉ số các cung bị tắt
end

function read_instance(netfile, tmfile, scenariofile)
    net = JSON.parsefile(netfile)
    tm  = JSON.parsefile(tmfile)
    sc  = JSON.parsefile(scenariofile)

    node = Dict(nd["id"] => k for (k, nd) in enumerate(net["nodes"]))   # id JSON -> 1..n
    links = net["links"]
    link = Dict(l["id"] => k for (k, l) in enumerate(links))            # id JSON -> 1..m

    dem = tm["demands"]
    vol = [Float64(d["v"][k]) for d in dem, k in 1:tm["num_time_slots"]]

    down = Dict{Int,Vector{Int}}()
    for iv in sc["interventions"]
        append!(get!(down, iv["t"], Int[]), [link[l] for l in iv["links"]])
    end

    Instance(length(node), length(links),
             [node[l["from"]] for l in links], [node[l["to"]] for l in links],
             [Float64(l["metric"]) for l in links], [Float64(l["capacity"]) for l in links],
             [node[d["s"]] for d in dem], [node[d["t"]] for d in dem], vol,
             sc["max_segments"],
             Dict(b["t"] => b["value"] for b in sc["budget"]),
             down)
end
```

### 6.3 Tính split coefficients `r` (Step 3 và Step 7)

Thuật toán, với mỗi đích `v`:
1. **Dijkstra ngược** từ `v` để có `dist[x]`, độ dài đường ngắn nhất từ `x` đến `v`.
2. Cung `a = (x, y)` thuộc forwarding graph khi `dist[x] == w[a] + dist[y]`.
3. Với mỗi nguồn `u`: đặt `flow[u] = 1`, rồi xét các nút theo thứ tự **`dist` giảm dần**. Đây là một thứ tự topo, vì trên `FG` mỗi bước đi đều làm `dist` giảm khi `ω > 0`. Tại mỗi nút, chia đều `flow` cho các cung ra thuộc `FG`.

Kết quả được lưu dạng thưa: `r[(u,v)]` là một `Dict(a => tỉ lệ)`. Nếu cặp `(u,v)` **không có trong `r`** thì từ `u` không đến được `v`.

```julia
function split_coefficients(inst::Instance, down::Vector{Int} = Int[])
    alive = setdiff(1:inst.m, down)
    outarcs = [Int[] for _ in 1:inst.n]
    inarcs  = [Int[] for _ in 1:inst.n]
    for a in alive
        push!(outarcs[inst.from[a]], a)
        push!(inarcs[inst.to[a]], a)
    end

    r = Dict{Tuple{Int,Int},Dict{Int,Float64}}()
    for v in 1:inst.n
        # 1. Dijkstra ngược (O(n^2), đủ nhanh cho vài trăm nút)
        dist = fill(Inf, inst.n); dist[v] = 0.0
        done = falses(inst.n)
        while true
            u, best = 0, Inf
            for x in 1:inst.n
                if !done[x] && dist[x] < best
                    u, best = x, dist[x]
                end
            end
            u == 0 && break
            done[u] = true
            for a in inarcs[u]
                p = inst.from[a]
                dist[p] = min(dist[p], dist[u] + inst.w[a])
            end
        end

        # 2-3. Đẩy luồng theo ECMP
        order = sortperm(dist; rev = true)
        for u in 1:inst.n
            (u == v || isinf(dist[u])) && continue
            flow = zeros(inst.n); flow[u] = 1.0
            ru = Dict{Int,Float64}()
            for x in order
                (x == v || flow[x] == 0.0) && continue
                nxt = [a for a in outarcs[x] if dist[x] ≈ inst.w[a] + dist[inst.to[a]]]
                share = flow[x] / length(nxt)
                for a in nxt
                    ru[a] = get(ru, a, 0.0) + share
                    flow[inst.to[a]] += share
                end
            end
            r[(u, v)] = ru
        end
    end
    return r
end

# r0 = split_coefficients(inst)                          # t = 0
# r1 = split_coefficients(inst, get(inst.down, 1, Int[])) # t = 1, trên G_1
```

### 6.4 Mô hình JuMP tổng quát cho T = {0, …, h−1} (Step 5 và Step 8)

- Hàm `build_model(inst, rs)` nhận `rs = [r0]` cho Step 5, hoặc `rs = [r0, r1]` cho Step 8.
- Biến `x` chỉ được tạo cho các segment có đường đi, đúng như lưu ý 4.5.1.

```julia
using JuMP, HiGHS

function build_model(inst::Instance, rs::Vector; optimizer = HiGHS.Optimizer, time_limit = 1800.0)
    D = 1:length(inst.src)
    T = 0:length(rs)-1
    model = Model(optimizer)
    set_time_limit_sec(model, time_limit)

    @variable(model, U >= 0)
    x = Dict{Tuple{Int,Int,Tuple{Int,Int}},VariableRef}()   # (d, t, (i,j)) => biến
    for t in T, d in D, s in keys(rs[t+1])
        x[(d, t, s)] = @variable(model, binary = true)
    end
    xv(d, t, s) = get(x, (d, t, s), 0)                    # segment không có đường đi => 0

    for t in T
        r = rs[t+1]
        S = collect(keys(r))
        out_of = [[s for s in S if s[1] == i] for i in 1:inst.n]
        in_to  = [[s for s in S if s[2] == i] for i in 1:inst.n]

        # (1) bảo toàn luồng
        for d in D, i in 1:inst.n
            rhs = i == inst.src[d] ? 1 : (i == inst.dst[d] ? -1 : 0)
            @constraint(model, sum(x[(d, t, s)] for s in out_of[i]) -
                               sum(x[(d, t, s)] for s in in_to[i]) == rhs)
        end

        # (2) số segment
        for d in D
            @constraint(model, sum(x[(d, t, s)] for s in S) <= inst.maxSeg)
        end

        # (3) tải: uses[a] = các segment (i,j) có r(i,j,a,t) > 0
        uses = [Tuple{Tuple{Int,Int},Float64}[] for _ in 1:inst.m]
        for (s, ra) in r, (a, f) in ra
            push!(uses[a], (s, f))
        end
        for a in 1:inst.m
            isempty(uses[a]) && continue
            @constraint(model, sum(f * inst.vol[d, t+1] * x[(d, t, s)]
                                   for d in D for (s, f) in uses[a]) <= U * inst.c[a])
        end

        # (4) budget, tuyến tính hoá |x^t - x^{t-1}| bằng y
        if t >= 1
            allS = union(keys(rs[t]), keys(rs[t+1]))
            ys = VariableRef[]
            for d in D, s in allS
                y = @variable(model, lower_bound = 0)
                @constraint(model, y >= xv(d, t, s) - xv(d, t-1, s))
                @constraint(model, y >= xv(d, t-1, s) - xv(d, t, s))
                push!(ys, y)
            end
            @constraint(model, sum(ys) <= inst.budget[t])
        end
    end

    @objective(model, Min, U)
    return model, x
end
```

### 6.5 Giải, lấy kết quả và đọc waypoint (Step 6 và Step 9)

```julia
function solve_and_report(model)
    optimize!(model)                         # CHỈ đo thời gian của lời gọi này
    st = termination_status(model)
    status = st == MOI.OPTIMAL    ? "Optimal" :
             st == MOI.INFEASIBLE ? "Infeasible" :
             has_values(model)    ? "Not Optimal" : string(st)
    obj = has_values(model) ? objective_value(model) : NaN
    lb  = objective_bound(model)
    gap = status == "Optimal" ? 0.0 : 1.0 - lb / obj    # công thức theo readme.txt
    return (status = status, obj = obj, lb = lb, gap = gap,
            cpu = solve_time(model), nodes = node_count(model))
end

# Lấy danh sách waypoint của demand d tại chu kỳ t: đi theo các segment x = 1 từ nguồn
function waypoints(inst, x, d, t)
    succ = Dict(s[1] => s[2] for ((dd, tt, s), var) in x if dd == d && tt == t && value(var) > 0.5)
    w, i = Int[], inst.src[d]
    while i != inst.dst[d]
        i = succ[i]
        i != inst.dst[d] && push!(w, i)
    end
    return w        # chỉ số Julia; trừ 1 để ra ID trong JSON
end
```

Thông tin cần ghi vào bảng kết quả cho mỗi instance:

| Instance | \|V\| | \|A\| | \|D\| | Obj (MLU) | CPU (s) | Status | Gap | #Nodes B&B |
|---|---|---|---|---|---|---|---|---|

Theo phần Deliverables, mỗi instance chạy **10 lần** và báo cáo **trung bình**. Ghi kết quả ra CSV để dựng bảng cho báo cáo.

### 6.6 Kiểm thử trên toy (bắt buộc làm trước khi chạy SetA)

```julia
inst = read_instance("instances/toy/toy-net.json", "instances/toy/toy-tm.json",
                     "instances/toy/toy-scenario.json")
r0 = split_coefficients(inst)
r0[(1, 6)]        # v0 -> v5 (chỉ số Julia = id JSON + 1)
# Kỳ vọng: Dict(1 => 1.0, 3 => 0.5, 4 => 0.5, 7 => 0.75, 19 => 0.25, 10 => 0.25, 22 => 0.25)
#          tức a0,1 = 1, a1,3 = a1,4 = 0.5, a3,5 = 0.75, a4,3 = a4,6 = a6,5 = 0.25 (khớp Table 2)
model, x = build_model(inst, [r0])
solve_and_report(model)          # kỳ vọng obj = 0.375

r1 = split_coefficients(inst, inst.down[1])
model2, x2 = build_model(inst, [r0, r1]; time_limit = 3600.0)
solve_and_report(model2)         # kỳ vọng obj = 0.375 (MLU trên cả hai chu kỳ)
```

Các giá trị kỳ vọng đã được kiểm tra bằng cách vét cạn mọi danh sách waypoint trên toy.
- t=0: MLU tối ưu là 0.375.
- t=1: MLU tối ưu là 0.375.

---

## 7. Những việc cần làm

### Chuẩn bị
- [ ] Bổ sung các file còn thiếu: **script Pluto**, **`calculating_r.pdf`**, **instances SetA**.
- [ ] Cài Julia (`brew install juliaup && juliaup add release`), JuMP, JSON, solver và Pluto.
- [ ] Tạo thư mục `instances/toy/` và chép 3 file JSON toy ở mục 5 vào đó.
- [ ] Ghi lại cấu hình máy (CPU, RAM, OS, phiên bản Julia/JuMP/solver) để đưa vào báo cáo.

### Step 1: Đọc hiểu đề
- [ ] Đọc mục 1–4 ở trên và tự tính lại ví dụ toy (mục 3).

### Step 2: Đồ thị G tại t = 0
- [ ] Dùng script Pluto để dựng đồ thị từ `*-net.json`.

### Step 3: Tính `r[i,j,a,0]`
- [ ] Đọc `calculating_r.pdf`, rồi so với cách tính ở mục 6.3.
- [ ] Kiểm tra kết quả khớp Table 2 của đề.

### Step 4: Phần Data
- [ ] `read_instance` lấy `c(a)` và topology từ net, `ν(d,0)` từ tm, `maxSeg` từ scenario. Sau đó gọi `split_coefficients`.

### Step 5: Mô hình chỉ có t = 0 (ràng buộc 1–3, không có 4)
- [ ] Gọi `build_model(inst, [r0])`. Trên toy phải ra MLU = 0.375.

### Step 6: Thí nghiệm SetA tại t = 0 (time limit 1800 s)
- [ ] Chạy 10 lần mỗi instance và lập bảng: `|V|, |A|, |D|`, Obj, CPU (chỉ tính `optimize!`), Status, Gap = `1 − LB/UB`, số nút B&B.

### Step 7: Đồ thị và tham số tại t = 1
- [ ] Bỏ các link trong `q(1)`, tính `r1 = split_coefficients(inst, inst.down[1])`, lấy `ν(d,1)` và `κ(1)`.

### Step 8: Mô hình hai chu kỳ (t = 0, 1) có budget
- [ ] Gọi `build_model(inst, [r0, r1])`, trong đó ràng buộc (4) đã được tuyến tính hoá.

### Step 9: Thí nghiệm SetA với t = 0 và t = 1 (time limit 3600 s)
> Trong `readme.txt` ghi "only time period 0", nhiều khả năng là chép nhầm từ Step 6. Nên hỏi lại giảng viên.
- [ ] Lập bảng giống Step 6.

### Báo cáo (tối đa 10 trang), nộp trước Chủ nhật 25/10/2026
- [ ] **Introduction**: bối cảnh, động lực, mô tả bài toán (dùng mục 1–3).
- [ ] **Mathematical model**: dữ liệu, biến, mục tiêu, ràng buộc, giải thích chi tiết kèm phần tuyến tính hoá (mục 4).
- [ ] **Numerical experiments**: mô tả instances, môi trường chạy, các bảng kết quả trung bình 10 lần (CPU time, Gap, số nút B&B).

---

## Gợi ý cấu trúc thư mục

```
math_modeling/
├── README.md
├── readme.txt
├── Challenge_Orange_ROADEF_2026_Subject.pdf
├── calculating_r.pdf          # cần bổ sung
├── instances/
│   ├── toy/                   # toy-net.json, toy-tm.json, toy-scenario.json
│   └── setA/                  # cần bổ sung
├── src/
│   ├── data.jl                # read_instance, split_coefficients
│   ├── model.jl               # build_model, solve_and_report, waypoints
│   └── run_experiments.jl     # Step 6 và Step 9, xuất CSV
├── notebooks/                 # notebook Pluto
├── results/                   # CSV kết quả
└── report/                    # báo cáo
```
