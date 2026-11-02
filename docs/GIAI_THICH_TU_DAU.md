# Giải thích bài toán Orange từ con số 0

Tài liệu này dành cho người **chưa biết gì** về mạng máy tính hay tối ưu hoá. Mỗi khái niệm được giải thích bằng lời trước. Mỗi công thức được **đọc thành câu**, **giải thích ý nghĩa**, rồi **tính thử bằng con số cụ thể**.

Mọi con số trong tài liệu được tính bằng chính code của project (`src/data.jl`) trên ví dụ "toy" của đề. Bạn có thể tự chạy lại để kiểm tra bằng lệnh `scripts/run.sh test` (cài đặt: [CAI_DAT_VA_CHAY.md](CAI_DAT_VA_CHAY.md)).

**Cách đọc:** đọc lần lượt từ Phần 1 đến Phần 12. Mỗi phần dùng kiến thức của các phần trước. Ở mỗi công thức, đọc ba dòng **Đọc là**, **Nghĩa là**, **Ví dụ số** rồi mới đi tiếp.

**Mục lục**

1. [Câu chuyện, chưa có công thức](#phần-1-câu-chuyện-chưa-có-công-thức)
2. [Cách đọc ký hiệu toán học](#phần-2-cách-đọc-ký-hiệu-toán-học)
3. [Ví dụ toy: mạng 7 router](#phần-3-ví-dụ-toy-mạng-7-router)
4. [Đường ngắn nhất, ECMP và hệ số r](#phần-4-đường-ngắn-nhất-ecmp-và-hệ-số-r)
5. [Tải (load) và MLU](#phần-5-tải-load-và-mlu)
6. [Segment Routing: waypoint và segment](#phần-6-segment-routing-waypoint-và-segment)
7. [Hai chu kỳ thời gian, bảo trì và budget](#phần-7-hai-chu-kỳ-thời-gian-bảo-trì-và-budget)
8. [Mô hình toán học, từng dòng một](#phần-8-mô-hình-toán-học-từng-dòng-một)
9. [Solver giải mô hình như thế nào](#phần-9-solver-giải-mô-hình-như-thế-nào)
10. [Vì sao instance lớn không chạy được](#phần-10-vì-sao-instance-lớn-không-chạy-được)
11. [Từ công thức sang code Julia](#phần-11-từ-công-thức-sang-code-julia)
12. [Tự kiểm tra](#phần-12-tự-kiểm-tra)

---

## Phần 1. Câu chuyện, chưa có công thức

### 1.1 Mạng là gì?

Hãy tưởng tượng một **hệ thống đường ống nước** nối nhiều thành phố.

- Mỗi **thành phố** là một **router**: máy chuyển tiếp dữ liệu. Trong toán học gọi là **nút** (node, vertex).
- Mỗi **đường ống một chiều** từ thành phố A sang thành phố B là một **link**. Trong toán học gọi là **cung** (arc). Ống hai chiều được coi là **hai cung riêng**: A→B và B→A.
- Mỗi cung có hai con số:
  - **Trọng số** `ω` (đọc là "ô-mê-ga"): một "độ dài" do kỹ sư mạng tự đặt. Nó **không phải khoảng cách thật**, chỉ là con số dùng để quyết định đường nào được coi là "ngắn". Ví dụ ω = 100.
  - **Dung lượng** `c`: lượng dữ liệu tối đa đi qua được trong một giây, giống như đường kính ống nước. Ví dụ c = 400.

### 1.2 Demand là gì?

**Demand** (nhu cầu) là một yêu cầu gửi dữ liệu: "từ router `s` cần gửi `ν` đơn vị dữ liệu tới router `t`".

- `s` là **nguồn** (source), `t` là **đích** (target).
- `ν` (đọc là "nuy") là **lưu lượng**, tức lượng dữ liệu cần gửi.
- Ví dụ: "từ v0 gửi 50 đơn vị tới v5".

### 1.3 Dữ liệu đi đường nào?

Mặc định, dữ liệu đi theo **đường ngắn nhất**: đường có **tổng trọng số ω nhỏ nhất**. Router tự tính đường này, con người không chọn từng đường.

Nếu có **nhiều đường cùng ngắn nhất** (bằng nhau), dữ liệu được **chia đều tại mỗi ngã rẽ**. Cơ chế này gọi là **ECMP** (Equal-Cost Multi-Path, "nhiều đường cùng chi phí").

### 1.4 Vấn đề: nghẽn

Nhiều demand có thể cùng đi qua một ống, làm ống đó **quá đầy**, trong khi các ống khác lại gần như trống.

- **Tải** (load) của một ống = (lượng dữ liệu đang đi qua) ÷ (dung lượng). Tải 0.5 nghĩa là ống đầy 50%. Tải 1.2 nghĩa là ống quá tải 120%, tức đang nghẽn.
- **MLU** (Maximum Link Utilization) = tải của **ống đầy nhất**. Đây là con số cần làm cho **nhỏ nhất**.

### 1.5 Giải pháp: Segment Routing

Ta không đổi được cách router tìm đường ngắn nhất. Nhưng ta có thể ra lệnh: **"trước hết hãy đi tới router w, rồi mới đi tới đích"**.

- Router `w` đó gọi là **waypoint** (điểm phải đi qua).
- Gói dữ liệu đi đường ngắn nhất từ `s` tới `w`, rồi đi đường ngắn nhất từ `w` tới `t`.
- Chọn waypoint khéo léo thì dữ liệu tránh được các ống đang đầy.
- Kỹ thuật này gọi là **Segment Routing**. Mỗi đoạn "đi ngắn nhất từ điểm này tới điểm kia" gọi là một **segment**.

### 1.6 Bảo trì và budget

- Thời gian được chia thành các **chu kỳ** (ví dụ mỗi chu kỳ là một ngày): `t = 0`, `t = 1`, …
- `t = 0` là ngày bình thường. Từ `t = 1` trở đi, một số ống **bị tắt để bảo trì**. Khi đó đường ngắn nhất thay đổi.
- Giữa hai chu kỳ ta được phép **đổi waypoint**. Nhưng mỗi lần đổi tốn công của kỹ sư, nên tổng số thay đổi bị giới hạn bởi **budget** `κ` (đọc là "kap-pa").

### 1.7 Câu hỏi của bài toán

> Với **mỗi demand** và **mỗi chu kỳ**, chọn danh sách waypoint sao cho **tải của ống đầy nhất (MLU) là nhỏ nhất**, với hai giới hạn:
> - mỗi danh sách không quá dài (tối đa `maxSeg` segment);
> - số thay đổi giữa hai chu kỳ không vượt budget.

Tên của bài toán là **T-ASR** (T-Adaptive Segment Routing).

---

## Phần 2. Cách đọc ký hiệu toán học

Bảng dưới đây là **mọi ký hiệu** sẽ gặp. Khi gặp công thức khó, quay lại đây tra.

| Ký hiệu | Đọc là | Nghĩa | Ví dụ |
|---|---|---|---|
| `V` | "tập V" | tập hợp tất cả các nút (router) | `V = {v0, v1, …, v6}` |
| `A` | "tập A" | tập hợp tất cả các cung (link) | `A = {a0,1 ; a0,2 ; …}` |
| `x ∈ X` | "x thuộc X" | x là một phần tử của tập X | `v3 ∈ V`: v3 là một nút |
| `X ⊆ Y` | "X là tập con của Y" | mọi phần tử của X đều nằm trong Y | |
| `X \ Y` | "X bỏ đi Y" | các phần tử của X mà không nằm trong Y | `{1,2,3} \ {2} = {1,3}` |
| `\|X\|` | "số phần tử của X" | đếm X có bao nhiêu phần tử | `\|V\| = 7` |
| `\|a − b\|` | "trị tuyệt đối của a − b" | khoảng cách giữa a và b, luôn ≥ 0 | `\|0 − 1\| = 1`, `\|1 − 1\| = 0` |
| `∀` | "với mọi" | điều phía sau đúng cho từng phần tử | `∀ i ∈ V`: với mọi nút i |
| `Σ` | "tổng" (xích-ma) | cộng tất cả các số hạng lại | `Σ_{i=1..3} i = 1 + 2 + 3 = 6` |
| `Σ_{j ∈ V \ {i}}` | "tổng theo mọi j thuộc V, trừ i" | cộng qua mọi nút j khác nút i | |
| `{0, 1}` | "tập gồm 0 và 1" | biến chỉ được nhận giá trị 0 hoặc 1 | |
| `min` | "cực tiểu" | làm cho giá trị nhỏ nhất có thể | `min U` |
| `max` | "cực đại" | giá trị lớn nhất | `max{0.1; 0.4; 0.3} = 0.4` |
| `a_{i,j}` | "cung a i j" | cung đi từ nút `v_i` tới nút `v_j` | `a_{0,1}`: cung v0 → v1 |
| `x^{dt}_{ij}` | "x, chỉ số trên d t, chỉ số dưới i j" | biến x ứng với demand `d`, chu kỳ `t` và cặp nút `(i, j)` | `x^{d0,0}_{0,4}` |
| `⟨s, w1, w2, t⟩` | "đường segment s, w1, w2, t" | danh sách các điểm phải đi qua, theo thứ tự | `⟨v0, v4, v5⟩` |
| `ω(a)`, `c(a)` | "ô-mê-ga của a", "c của a" | trọng số và dung lượng của cung a | `ω(a_{0,1}) = 100` |

> **Chỉ số trên và chỉ số dưới không phải là số mũ.** Chúng chỉ là "nhãn" để phân biệt các biến với nhau. `x^{dt}_{ij}` giống như một ô trong một bảng lớn, có địa chỉ là (demand d, chu kỳ t, nút i, nút j).

> **Bẫy của đề:** chữ `t` có **hai nghĩa**: (1) đích của demand, (2) chu kỳ thời gian. Tài liệu này viết **`t_d`** cho đích của demand `d` và **`t`** cho chu kỳ.

---

## Phần 3. Ví dụ toy: mạng 7 router

Đề bài cho một ví dụ nhỏ gọi là **toy**. Mọi phần sau đều dùng ví dụ này.

### 3.1 Các nút và các link

Có 7 nút: `v0, v1, v2, v3, v4, v5, v6`. Có 11 link hai chiều, tức **22 cung**. Mỗi link có cùng trọng số và dung lượng ở cả hai chiều:

| Link | ω (trọng số) | c (dung lượng) |
|---|---|---|
| v0 — v1 | 100 | 400 |
| v0 — v2 | 200 | 300 |
| v1 — v3 | 200 | 200 |
| v1 — v4 | 100 | 200 |
| v2 — v4 | 100 | 400 |
| v2 — v6 | 300 | 200 |
| v3 — v4 | 100 | 200 |
| v3 — v5 | 100 | 200 |
| v4 — v5 | 300 | 200 |
| v4 — v6 | 100 | 200 |
| v5 — v6 | 100 | 200 |

Ví dụ: link "v0 — v1" tương ứng với hai cung: `a_{0,1}` (v0 → v1) và `a_{1,0}` (v1 → v0). Mỗi cung có ω = 100 và c = 400.

### 3.2 Các demand

| Demand | Nguồn → Đích | Lưu lượng tại t = 0 | Lưu lượng tại t = 1 |
|---|---|---|---|
| d0 | v0 → v5 | ν = 50 | ν = 100 |
| d1 | v2 → v5 | ν = 100 | ν = 50 |

- Số segment tối đa: `maxSeg = 4`, tức tối đa 3 waypoint.
- Tại t = 1: hai cung `a_{1,3}` (v1 → v3) và `a_{1,4}` (v1 → v4) bị tắt.
- Budget: `κ(1) = 20`.

Ba file JSON của ví dụ này nằm trong thư mục `toy/`.

---

## Phần 4. Đường ngắn nhất, ECMP và hệ số r

### 4.1 Độ dài một đường

**Độ dài** của một đường = **tổng trọng số ω** của các cung trên đường đó.

**Ví dụ số:** các đường từ v0 tới v5:

| Đường | Tính | Độ dài |
|---|---|---|
| v0 → v1 → v3 → v5 | 100 + 200 + 100 | **400** |
| v0 → v1 → v4 → v3 → v5 | 100 + 100 + 100 + 100 | **400** |
| v0 → v1 → v4 → v6 → v5 | 100 + 100 + 100 + 100 | **400** |
| v0 → v1 → v4 → v5 | 100 + 100 + 300 | 500 |
| v0 → v2 → v4 → v3 → v5 | 200 + 100 + 100 + 100 | 500 |

Độ dài nhỏ nhất là 400, và **có 3 đường cùng đạt 400**. Ba đường đó là "đường ngắn nhất".

### 4.2 Khoảng cách tới đích

Gọi `dist(x)` là **độ dài đường ngắn nhất từ nút x tới v5**. Máy tính dùng **thuật toán Dijkstra** để tính các giá trị này. Kết quả (tính bằng code):

| Nút x | v0 | v1 | v2 | v3 | v4 | v5 | v6 |
|---|---|---|---|---|---|---|---|
| dist(x) tới v5 | 400 | 300 | 300 | 100 | 200 | 0 | 100 |

Đọc bảng: "từ v4, đường ngắn nhất tới v5 dài 200". Đó là v4 → v3 → v5 hoặc v4 → v6 → v5. Còn đường thẳng v4 → v5 dài 300 nên không ngắn nhất.

### 4.3 Quy tắc: cung nào nằm trên đường ngắn nhất?

```
Cung a = (x → y) nằm trên một đường ngắn nhất tới đích  ⟺  dist(x) = ω(a) + dist(y)
```

- **Đọc là:** "cung từ x tới y nằm trên đường ngắn nhất khi và chỉ khi khoảng cách từ x bằng trọng số của cung cộng khoảng cách từ y."
- **Nghĩa là:** đi cung này rồi tiếp tục đi ngắn nhất từ y thì vẫn đạt đúng độ dài ngắn nhất từ x. Tức là đi cung này **không bị đi vòng**.
- **Ví dụ số** (đích v5):
  - Cung v4 → v3: `dist(v4) = 200` và `ω + dist(v3) = 100 + 100 = 200`. Bằng nhau, nên **có**.
  - Cung v4 → v5: `dist(v4) = 200` nhưng `ω + dist(v5) = 300 + 0 = 300`. Khác nhau, nên **không**.
  - Cung v0 → v2: `dist(v0) = 400` nhưng `200 + dist(v2) = 200 + 300 = 500`. Khác nhau, nên **không**.

Tập hợp mọi cung "có" gọi là **forwarding graph**, viết là `FG(v0, v5)`: đồ thị chuyển tiếp từ v0 tới v5.

### 4.4 ECMP: chia đều tại mỗi ngã rẽ (cách của đề bài)

Đặt **1 đơn vị** dữ liệu tại v0 rồi cho nó chảy về v5, chỉ đi trên các cung "có". Mỗi khi tới một nút có nhiều cung "có" đi ra, **chia đều** lượng đang có:

1. Tại **v0**: chỉ có một cung đúng hướng là v0 → v1. Cả 1 đơn vị đi sang v1.
2. Tại **v1** (đang có 1): hai cung đúng hướng là v1 → v3 (200 + 100 = 300 ✓) và v1 → v4 (100 + 200 = 300 ✓). **Chia đôi**: 0.5 đi v3, 0.5 đi v4.
3. Tại **v4** (đang có 0.5): hai cung đúng hướng là v4 → v3 và v4 → v6. Chia đôi: 0.25 đi v3, 0.25 đi v6.
4. Tại **v3** (nhận 0.5 từ v1 và 0.25 từ v4, tổng 0.75): đi v3 → v5 với **0.75**.
5. Tại **v6** (đang có 0.25): đi v6 → v5 với **0.25**.

Tổng về tới v5: 0.75 + 0.25 = 1. Không mất đơn vị dữ liệu nào.

### 4.5 Hệ số chia luồng `r(u, v, a, t)`

```
r(u, v, a, t) = phần của 1 đơn vị dữ liệu, gửi từ u tới v trong mạng ở chu kỳ t, đi qua cung a
```

- **Đọc là:** "r của u, v, a, t".
- **Nghĩa là:** nếu gửi 1 đơn vị từ `u` tới `v` thì cung `a` chở bao nhiêu phần. Luôn nằm trong khoảng từ 0 tới 1. Bằng 0 nếu cung không nằm trên đường ngắn nhất.
- **Ví dụ số** (từ phần 4.4): `r(v0, v5, ·, 0)`, với dấu "·" nghĩa là "mọi cung":

| Cung | a0,1 | a1,3 | a1,4 | a4,3 | a4,6 | a3,5 | a6,5 | các cung khác |
|---|---|---|---|---|---|---|---|---|
| r | 1 | 0.5 | 0.5 | 0.25 | 0.25 | **0.75** | 0.25 | 0 |

Bảng này khớp **Table 2** của đề.

Tương tự, `r(v2, v5, ·, 0)`: a2,4 = 1; a4,3 = a4,6 = 0.5; a3,5 = a6,5 = 0.5.

**Hai điều quan trọng về r:**

1. **r là dữ liệu, không phải biến.** r chỉ phụ thuộc vào mạng (ω và các cung còn sống), không phụ thuộc vào việc ta chọn waypoint nào. Vì vậy ta tính r **một lần trước**, rồi dùng như hằng số.
2. **Phải tính r cho mọi cặp nút (u, v)**, không chỉ cặp (nguồn, đích) của demand. Lý do: cặp nào cũng có thể trở thành một segment (xem Phần 6). Toy có 7 × 6 = 42 cặp, nên tính 42 bảng r.

### 4.6 Hai cách tính r: của đề bài và của `calculating_r.pdf`

**Tóm tắt trước:** project **không tự nghĩ ra cách tính mới**. Có **hai tài liệu**, và mỗi tài liệu mô tả **một cách tính r khác nhau**:

| | **Cách 1: ECMP** | **Cách 2: đếm đường** |
|---|---|---|
| Lấy từ | **Đề bài** `Challenge_Orange_ROADEF_2026_Subject.pdf` (trang 2, đoạn "Forwarding graph & ECMP", và Table 2) | **Tài liệu giảng viên** `calculating_r.pdf` |
| Chia đều dữ liệu cho | từng **ngã rẽ** (tại mỗi nút) | từng **đường** ngắn nhất |
| Mô tả trong file này | mục 4.4 ở trên | mục này |
| Kết quả cho cung a3,5 (toy, v0 → v5) | **0.75**, khớp Table 2 của đề | **0.667** |
| Tên hàm trong code | `r_ecmp` | `r_pathcount` |

**Ví dụ để thấy khác nhau.** Từ v0 tới v5 có 3 đường cùng ngắn nhất (độ dài 400):

```
Đường A:  v0 → v1 → v3 → v5
Đường B:  v0 → v1 → v4 → v3 → v5
Đường C:  v0 → v1 → v4 → v6 → v5
```

**Cách 2, đếm đường** (`calculating_r.pdf`): có 3 đường, nên **mỗi đường nhận 1/3**. Cung a3,5 nằm trên đường A và B, nên r = 1/3 + 1/3 = **2/3 ≈ 0.667**.

Công thức trong `calculating_r.pdf` tính đúng con số này mà không cần liệt kê từng đường:

```
r(i, j, a) = σ(i, u) · σ(v, j) / σ(i, j)      với cung a = (u → v) nằm trên đường ngắn nhất từ i tới j
```

- `σ(i, j)` (đọc là "xích-ma") = **số** đường ngắn nhất từ i tới j.
- `σ(i, u) · σ(v, j)` = số đường ngắn nhất **đi qua cung a**: có σ(i,u) cách đi từ i tới u, đi cung a, rồi có σ(v,j) cách đi tiếp từ v tới j.
- Với cung a3,5: σ(v0, v3) = 2 (đường A và B), σ(v5, v5) = 1, σ(v0, v5) = 3. Vậy r = 2 × 1 / 3 = 0.667.

**Cách 1, ECMP** (đề bài): dữ liệu **chia đôi mỗi khi gặp ngã rẽ**, không quan tâm phía sau còn bao nhiêu đường:

```
Tại v1: hai ngã rẽ (đi v3, đi v4)   → mỗi ngã 1/2
          ngã v3 → chính là đường A                    : 1/2
          ngã v4 → tới v4 lại có hai ngã (đi v3, đi v6) → mỗi ngã 1/2 × 1/2 = 1/4
                     đường B (qua v4 → v3)               : 1/4
                     đường C (qua v4 → v6)               : 1/4
```

Ba đường nhận **1/2, 1/4, 1/4**, không đều nhau. Cung a3,5 nằm trên A và B, nên r = 1/2 + 1/4 = **0.75**.

**Vì sao đề dùng ECMP:** router thật chỉ biết **các ngã rẽ của chính nó** và chia đều cho các ngã đó. Nó không biết phía sau còn bao nhiêu đường. Giống nước chảy trong ống: tới chỗ chia đôi thì chia đôi, không "đếm" trước số lối ra phía sau. Vì vậy ECMP mô tả đúng cách mạng thật hoạt động, và Table 2 của đề cũng được tính theo cách này.

**Khi nào hai cách ra cùng kết quả:**

- Khi chỉ có **một** đường ngắn nhất: không có ngã rẽ nào, nên cả hai cách đều cho r = 1 trên đường đó.
- Khi các ngã rẽ **cân đối**, tức mỗi ngã dẫn tới cùng số đường phía sau.

Trên SetA, đường ngắn nhất hầu như luôn duy nhất. Đã kiểm tra mọi cặp nút: hai cách chỉ khác nhau ở **1 cặp trong setA-18 và 1 cặp trong setA-20**, và hai cặp này không phải cặp nguồn–đích của demand nào. Vì vậy kết quả thí nghiệm gần như không đổi dù dùng cách nào. Chỉ trên ví dụ toy là hai cách khác nhau rõ.

**Project làm gì:**

- Cài **cả hai** cách, để cho thấy đã làm theo hướng dẫn của giảng viên.
- **Mô hình dùng Cách 1 (ECMP)**, vì nó đúng với định nghĩa và Table 2 của đề.
- Lệnh `scripts/run.sh test` in kết quả của cả hai cách cạnh nhau.
- Nên hỏi giảng viên: *"Table 2 của đề chia luồng đều tại mỗi nút, còn calculating_r.pdf chia đều theo số đường. Em dùng cách nào ạ?"*

---

## Phần 5. Tải (load) và MLU

### 5.1 Công thức tải khi không có waypoint

```
                Σ_{d ∈ D}  r(s_d, t_d, a, t) · ν(d, t)
λ(a, t)  =  ──────────────────────────────────────────
                             c(a)
```

- **Đọc là:** "lam-đa của a tại t bằng tổng, theo mọi demand d, của r nhân ν, tất cả chia cho c của a".
- **Nghĩa là:**
  - Với mỗi demand `d`, phần dữ liệu của nó đi qua cung `a` là `r(s_d, t_d, a, t) · ν(d, t)`, tức (tỉ lệ đi qua a) × (lưu lượng).
  - Cộng lại cho mọi demand, được **tổng lượng dữ liệu trên cung a**.
  - Chia cho dung lượng `c(a)` được **tỉ lệ đầy** của cung.
- **Ví dụ số:** cung a3,5 tại t = 0, khi không có waypoint:
  - d0: r(v0,v5,a3,5) · ν = 0.75 × 50 = 37.5
  - d1: r(v2,v5,a3,5) · ν = 0.5 × 100 = 50
  - Tổng = 87.5. Chia c = 200, được **λ = 0.4375**, tức đầy 43.75%.

### 5.2 MLU

```
MLU = max_{a ∈ A}  λ(a, t)
```

- **Đọc là:** "MLU bằng giá trị lớn nhất của λ, xét mọi cung a".
- **Ví dụ số:** tải của tất cả các cung có dữ liệu, tại t = 0, khi không có waypoint (tính bằng code):

| Cung | a0,1 | a1,3 | a1,4 | a2,4 | **a3,5** | a4,3 | a4,6 | a6,5 |
|---|---|---|---|---|---|---|---|---|
| Lưu lượng | 50 | 25 | 25 | 100 | **87.5** | 62.5 | 62.5 | 62.5 |
| Dung lượng | 400 | 200 | 200 | 400 | 200 | 200 | 200 | 200 |
| Tải λ | 0.125 | 0.125 | 0.125 | 0.25 | **0.4375** | 0.3125 | 0.3125 | 0.3125 |

Cung đầy nhất là a3,5, nên **MLU = 0.4375**. Mục tiêu là làm con số này nhỏ hơn.

---

## Phần 6. Segment Routing: waypoint và segment

### 6.1 Segment path

Một **segment path** được viết `⟨s, w1, w2, …, wℓ, t_d⟩`:

- `s` là nguồn, `t_d` là đích, còn `w1, …, wℓ` là các waypoint theo thứ tự.
- `ℓ` (chữ "l" viết tay) là **số waypoint**. ℓ = 0 nghĩa là đi thẳng `⟨s, t_d⟩`, không có waypoint.

### 6.2 Segment

**Segment** là **cặp hai điểm đứng liền nhau** trong segment path.

- **Ví dụ:** `⟨v0, v4, v5⟩` có **2 segment**: `(v0, v4)` và `(v4, v5)`.
- **Ví dụ:** `⟨s, w1, w2, t⟩` có **3 segment**: `(s, w1)`, `(w1, w2)`, `(w2, t)`.
- **Quy tắc:** ℓ waypoint thì có ℓ + 1 segment. Vì vậy `maxSeg = 4` nghĩa là tối đa 3 waypoint.

Trên mỗi segment `(i, j)`, dữ liệu đi theo đường ngắn nhất từ i tới j và chia theo ECMP, với hệ số `r(i, j, ·, t)`.

### 6.3 Ví dụ: thêm waypoint v4 cho d0

Đổi d0 từ `⟨v0, v5⟩` thành **`⟨v0, v4, v5⟩`**:

- Segment `(v0, v4)`: đường ngắn nhất là v0 → v1 → v4, dài 200. Code cho `r(v0,v4,·,0)`: a0,1 = 1 và a1,4 = 1.
- Segment `(v4, v5)`: chia đôi qua v3 và qua v6. Code cho `r(v4,v5,·,0)`: a4,3 = a4,6 = a3,5 = a6,5 = 0.5.

Tải mới tại t = 0 (d1 vẫn đi thẳng):

| Cung | a0,1 | a1,4 | a2,4 | a3,5 | a4,3 | a4,6 | a6,5 |
|---|---|---|---|---|---|---|---|
| Lưu lượng | 50 | 50 | 100 | 75 | 75 | 75 | 75 |
| Tải λ | 0.125 | 0.25 | 0.25 | **0.375** | **0.375** | **0.375** | **0.375** |

Tính chi tiết cho a3,5: d0 góp 0.5 × 50 = 25 (từ segment (v4, v5)), d1 góp 0.5 × 100 = 50. Tổng 75, chia 200 được 0.375.

**MLU giảm từ 0.4375 xuống 0.375.** Lưu lượng giờ được **dàn đều** trên bốn cung, không dồn vào a3,5 nữa. Đây cũng là nghiệm tối ưu mà mô hình tìm ra.

---

## Phần 7. Hai chu kỳ thời gian, bảo trì và budget

### 7.1 Các ký hiệu về thời gian

| Ký hiệu | Nghĩa | Trong toy |
|---|---|---|
| `T = {0, 1, …, h−1}` | tập các chu kỳ, `h` là số chu kỳ | `T = {0, 1}` |
| `T* = T \ {0}` | các chu kỳ trừ chu kỳ 0 (chỉ những chu kỳ này mới có bảo trì và budget) | `T* = {1}` |
| `q(t)` | tập các cung bị tắt tại chu kỳ t | `q(1) = {a1,3 ; a1,4}` |
| `G_t` | mạng tại chu kỳ t, tức mạng gốc bỏ đi các cung trong q(t) | `G_1` không có a1,3 và a1,4 |
| `κ(t)` | budget: số thay đổi tối đa từ chu kỳ t−1 sang chu kỳ t | `κ(1) = 20` |

### 7.2 Khi cung bị tắt, r phải tính lại

Tại t = 1, từ v1 không còn đi được tới v3 hay v4. Đường ngắn nhất từ v0 tới v5 trở thành v0 → v2 → v4 → (v3 hoặc v6) → v5, dài 500. Code cho:

`r(v0, v5, ·, 1)`: a0,2 = 1, a2,4 = 1, a4,3 = a4,6 = a3,5 = a6,5 = 0.5.

Vì vậy mỗi chu kỳ có **bộ r riêng**: `r(·,·,·,0)` tính trên `G_0`, và `r(·,·,·,1)` tính trên `G_1`.

### 7.3 Đếm số thay đổi

```
dist(P, P') = Σ_{d ∈ D} Σ_{i,j ∈ V, i ≠ j} | δ(p_d, ij) − δ(p'_d, ij) |
```

- `P` là routing ở chu kỳ trước, `P'` là routing ở chu kỳ sau.
- `δ(p_d, ij)` (đen-ta) = 1 nếu đường của demand d **có** segment (i, j), = 0 nếu không có.
- **Đọc là:** "khoảng cách giữa P và P' bằng tổng, theo mọi demand và mọi cặp nút khác nhau, của trị tuyệt đối hiệu hai đen-ta".
- **Nghĩa là:** với mỗi segment, nếu nó **có ở một bên mà không có ở bên kia** thì số hạng bằng `|1 − 0| = 1`: một lần thêm hoặc một lần bỏ. Nếu có ở cả hai bên hoặc không có ở cả hai bên thì số hạng bằng 0. Tổng lại là số segment bị thêm cộng số segment bị bỏ.
- **Ví dụ số:** đổi d0 từ `⟨v0, v4, v5⟩` thành `⟨v0, v5⟩`:

| Segment | Có ở trước? | Có ở sau? | Đóng góp |
|---|---|---|---|
| (v0, v4) | 1 | 0 | \|1 − 0\| = 1 (bị bỏ) |
| (v4, v5) | 1 | 0 | 1 (bị bỏ) |
| (v0, v5) | 0 | 1 | 1 (được thêm) |
| mọi segment khác | 0 | 0 | 0 |
| **Tổng** | | | **3** |

Budget bắt buộc: `dist(P^{t−1}, P^t) ≤ κ(t)`. Trong toy, 3 ≤ 20 nên thay đổi này được phép.

---

## Phần 8. Mô hình toán học, từng dòng một

Đây là phần quan trọng nhất của báo cáo. Một **mô hình tối ưu** luôn có 3 thành phần:

1. **Biến**: những gì ta được phép chọn.
2. **Hàm mục tiêu**: thứ ta muốn làm nhỏ nhất (hoặc lớn nhất).
3. **Ràng buộc**: các luật mà lựa chọn phải tuân theo.

Còn **dữ liệu** (tham số) là những con số **đã biết trước**: ω, c, ν, r, maxSeg, κ.

### 8.1 Biến thứ nhất: `x^{dt}_{ij}`

```
x^{dt}_{ij} ∈ {0, 1}
```

- **Đọc là:** "x d t i j thuộc tập không-một".
- **Nghĩa là:** x là một **công tắc bật/tắt**. Nó bằng **1** nếu đường của demand `d` tại chu kỳ `t` **có dùng segment (i, j)**, và bằng **0** nếu không dùng.
- **Mẹo hình dung:** vẽ một **đồ thị tưởng tượng H**, trong đó mọi cặp nút (i, j) đều được nối bằng một "cung ảo". Khi đó chọn segment path chính là **chọn một đường đi từ s tới t_d trên H**. Mỗi biến x trả lời câu hỏi "cung ảo (i, j) có nằm trên đường đó không?".
- **Ví dụ số:** đường `⟨v0, v4, v5⟩` cho d0 tại t = 0 tương ứng với:
  - `x^{d0,0}_{0,4} = 1`
  - `x^{d0,0}_{4,5} = 1`
  - **mọi** `x^{d0,0}_{ij}` còn lại bằng 0, ví dụ `x^{d0,0}_{0,5} = 0` và `x^{d0,0}_{2,3} = 0`.
- **Đếm số biến:** mỗi demand và mỗi chu kỳ có một biến cho mỗi cặp (i, j). Toy có 7 × 6 = 42 cặp, nên với 2 demand và 1 chu kỳ có 2 × 42 = **84 biến x**.

### 8.2 Biến thứ hai: `U`

```
U ≥ 0
```

- **Đọc là:** "U lớn hơn hoặc bằng 0".
- **Nghĩa là:** U là một số thực, đại diện cho **MLU**. Vai trò của nó được giải thích ngay dưới đây.

### 8.3 Hàm mục tiêu: `min U`

Thứ ta muốn là `min ( max_a λ(a) )`: làm cho tải lớn nhất nhỏ nhất. Nhưng solver chỉ hiểu được công thức **tuyến tính** (chỉ có cộng, trừ, và nhân với hằng số), còn hàm `max` không thuộc loại đó.

**Mẹo:** dùng một biến U làm "trần nhà", và bắt mọi tải phải nằm dưới trần:

```
min U        sao cho      λ(a, t) ≤ U   với mọi cung a và mọi chu kỳ t
```

- **Đọc là:** "cực tiểu U, sao cho tải của mọi cung đều không vượt U".
- **Nghĩa là:** U phải ≥ mọi tải, tức U ≥ tải lớn nhất. Khi solver ép U xuống thấp nhất có thể, U sẽ dừng **đúng bằng** tải lớn nhất. Vì vậy cực tiểu U cũng chính là cực tiểu MLU.
- **Ví dụ số:** với nghiệm `⟨v0, v4, v5⟩`, các tải là 0.125, 0.25, 0.25, 0.375, … U phải ≥ mọi số đó, nên U nhỏ nhất là 0.375 = MLU.

> **Về mục tiêu "lex-min" của đề:** đề muốn làm tải lớn nhất nhỏ nhất, **rồi** trong các nghiệm đó làm tải lớn thứ hai nhỏ nhất, và cứ thế tiếp tục. Project chỉ làm **bước đầu tiên** (min MLU). Bước đầu đã là bài toán chính, và các paper cũng giải đúng bước này trước.

### 8.4 Ràng buộc (1): bảo toàn luồng, để x tạo thành một đường đi hợp lệ

```
Σ_{j ∈ V\{i}} x^{dt}_{ij}  −  Σ_{j ∈ V\{i}} x^{dt}_{ji}  =   1    nếu i = s_d       (i là nguồn)
                                                          =  −1    nếu i = t_d       (i là đích)
                                                          =   0    nếu khác
                                           với mọi nút i ∈ V, mọi demand d ∈ D, mọi chu kỳ t ∈ T
```

- **Đọc từng phần:**
  - `Σ_{j ∈ V\{i}} x^{dt}_{ij}` = tổng các x có **i đứng đầu**, tức **số segment đi RA khỏi nút i**.
  - `Σ_{j ∈ V\{i}} x^{dt}_{ji}` = tổng các x có **i đứng sau**, tức **số segment đi VÀO nút i**.
  - Hiệu của chúng = (ra) − (vào).
- **Nghĩa là:**
  - Tại **nguồn**: ra nhiều hơn vào đúng 1. Đường xuất phát từ đây.
  - Tại **đích**: vào nhiều hơn ra đúng 1. Đường kết thúc ở đây.
  - Tại **mọi nút khác**: vào bao nhiêu ra bấy nhiêu. Nếu đường đi qua nút đó (nút đó là waypoint) thì vào 1 ra 1. Nếu không đi qua thì vào 0 ra 0.
- **Ví dụ số:** kiểm tra `⟨v0, v4, v5⟩` cho d0 (x_{0,4} = 1, x_{4,5} = 1):

| Nút | Ra | Vào | Ra − Vào | Phải bằng | Đúng? |
|---|---|---|---|---|---|
| v0 (nguồn) | 1 (là x_{0,4}) | 0 | 1 | 1 | ✓ |
| v4 | 1 (là x_{4,5}) | 1 (là x_{0,4}) | 0 | 0 | ✓ |
| v5 (đích) | 0 | 1 (là x_{4,5}) | −1 | −1 | ✓ |
| v1, v2, v3, v6 | 0 | 0 | 0 | 0 | ✓ |

- **Ví dụ sai:** nếu chỉ bật `x_{0,4} = 1` mà quên `x_{4,5}`, thì tại v4 có Ra − Vào = 0 − 1 = −1, trong khi phải bằng 0. Ràng buộc bị vi phạm, nên solver **không được phép** chọn nghiệm này. Như vậy ràng buộc (1) đảm bảo mỗi demand có **một đường liền mạch từ nguồn tới đích**.

### 8.5 Ràng buộc (2): giới hạn số segment

```
Σ_{i,j ∈ V} x^{dt}_{ij}  ≤  maxSeg            với mọi demand d, mọi chu kỳ t
```

- **Đọc là:** "tổng mọi x của demand d tại chu kỳ t nhỏ hơn hoặc bằng maxSeg".
- **Nghĩa là:** tổng số công tắc đang bật = **số segment của đường**. Router chỉ chứa được một danh sách có độ dài giới hạn trong header của gói tin, nên con số này không được vượt maxSeg.
- **Ví dụ số:** `⟨v0, v4, v5⟩` có 1 + 1 = 2 segment, và 2 ≤ 4 ✓. Đường có 4 waypoint (5 segment) thì 5 > 4, bị cấm.

### 8.6 Ràng buộc (3): tính tải và giữ tải dưới U

```
Σ_{d ∈ D}  Σ_{i,j ∈ V}  r(i, j, a, t) · ν(d, t) · x^{dt}_{ij}   ≤   U · c(a)
                                     với mọi chu kỳ t, mọi cung a còn sống (a ∈ A \ q(t))
```

- **Đọc từng phần:**
  - Mỗi số hạng `r(i,j,a,t) · ν(d,t) · x^{dt}_{ij}` = (phần của segment (i,j) đi qua cung a) × (lưu lượng của demand d) × (demand d có dùng segment (i,j) không: 1 hoặc 0).
  - Nếu x = 0 thì số hạng bằng 0: segment không được dùng nên không góp gì vào tải.
  - Nếu x = 1 thì số hạng bằng `r · ν`: đúng lượng dữ liệu segment đó đẩy qua cung a.
  - Cộng qua mọi demand và mọi segment, được **tổng dữ liệu trên cung a**.
  - Vế phải `U · c(a)`: "tổng dữ liệu ≤ U × dung lượng", tương đương "tải = tổng dữ liệu / c(a) ≤ U".
- **Vì sao gọi là tuyến tính:** r, ν, c đều là **con số đã biết**. Mỗi số hạng chỉ là (một con số) × (một biến), không có hai biến nhân với nhau. Solver xử lý được dạng này.
- **Ví dụ số:** cung a3,5, t = 0, d0 đi `⟨v0, v4, v5⟩`, d1 đi `⟨v2, v5⟩`. Chỉ các số hạng có x = 1 mới khác 0:

| Demand | Segment có x = 1 | r(segment, a3,5, 0) | ν | r · ν · x |
|---|---|---|---|---|
| d0 | (v0, v4) | 0 | 50 | 0 |
| d0 | (v4, v5) | 0.5 | 50 | 25 |
| d1 | (v2, v5) | 0.5 | 100 | 50 |
| | | | **Tổng** | **75** |

Vậy ràng buộc là `75 ≤ U × 200`, tức `U ≥ 0.375`.

- **Vì sao chỉ xét cung còn sống (`a ∈ A \ q(t)`):** cung bị tắt không chở dữ liệu. Thật ra r của nó đã bằng 0 vì r được tính trên `G_t`.

### 8.7 Ràng buộc (4): budget, chỉ dùng khi có từ hai chu kỳ trở lên

```
Σ_{d ∈ D}  Σ_{i ≠ j}  | x^{dt}_{ij} − x^{d,t−1}_{ij} |   ≤   κ(t)            với mọi t ∈ T* (t = 1, 2, …)
```

- **Đọc là:** "tổng, theo mọi demand và mọi segment, của trị tuyệt đối hiệu giữa x ở chu kỳ t và x ở chu kỳ t−1, không vượt κ(t)".
- **Nghĩa là:** đây chính là công thức `dist(P, P')` ở Phần 7.3, viết bằng biến x. Mỗi segment bị bật hoặc tắt giữa hai chu kỳ tính là 1 thay đổi. Tổng số thay đổi ≤ budget.
- **Vấn đề:** `| · |` (trị tuyệt đối) **không tuyến tính**, nên solver không hiểu.
- **Cách sửa (tuyến tính hoá):** thêm một biến phụ `y^{dt}_{ij} ≥ 0` cho mỗi (d, i, j), rồi thay (4) bằng ba dòng:

```
y^{dt}_{ij}  ≥  x^{dt}_{ij} − x^{d,t−1}_{ij}            (4a)
y^{dt}_{ij}  ≥  x^{d,t−1}_{ij} − x^{dt}_{ij}            (4b)
Σ_d Σ_{i≠j} y^{dt}_{ij}  ≤  κ(t)                         (4c)
```

- **Vì sao đúng:** xét cả 4 trường hợp có thể của hai công tắc:

| x cũ | x mới | \|mới − cũ\| (cần đếm) | (4a): y ≥ | (4b): y ≥ | y nhỏ nhất được phép |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | **0** |
| 0 | 1 | 1 | 1 | −1 | **1** |
| 1 | 0 | 1 | −1 | 1 | **1** |
| 1 | 1 | 0 | 0 | 0 | **0** |

  Cột cuối **luôn bằng đúng trị tuyệt đối**. Vậy (4a) và (4b) ép `y ≥ |x mới − x cũ|`. Solver có thể chọn y đúng bằng trị tuyệt đối, và không có lý do gì chọn lớn hơn, vì y lớn hơn chỉ làm (4c) khó thoả hơn. Kết quả là (4c) giới hạn đúng tổng số thay đổi.

- **Ví dụ số:** nếu d0 đổi từ `⟨v0, v4, v5⟩` sang `⟨v0, v5⟩`, thì ba segment (v0,v4), (v4,v5), (v0,v5) có y = 1 và mọi segment khác có y = 0. Tổng = 3 ≤ 20 ✓.

### 8.8 Toàn bộ mô hình

**Mô hình Step 5 (chỉ t = 0):**

```
min  U
với:  (1) bảo toàn luồng       cho mọi nút i, mọi demand d
      (2) số segment ≤ maxSeg   cho mọi demand d
      (3) tải ≤ U · c(a)        cho mọi cung a
      x^{d0}_{ij} ∈ {0, 1},  U ≥ 0
```

**Mô hình Step 8 (t = 0 và t = 1):**

```
min  U
với:  (1), (2), (3) viết riêng cho t = 0 (dùng r và ν của t = 0)
      (1), (2), (3) viết riêng cho t = 1 (dùng r và ν của t = 1, bỏ các cung bị tắt)
      (4a), (4b), (4c) nối hai chu kỳ bằng budget κ(1)
      x ∈ {0, 1},  y ≥ 0,  U ≥ 0
```

Ở Step 8 chỉ có **một U chung**, nên U phải ≥ mọi tải **ở cả hai chu kỳ**.

**Kết quả trên toy** (lệnh `scripts/run.sh test`, code ở `src/test_toy.jl`):

- Step 5 cho U = **0.375**, với d0 đi `⟨v0, v4, v5⟩` và d1 đi thẳng.
- Step 8 cho U = **0.375**. Tại t = 1, kể cả khi không có waypoint, tải lớn nhất đã là 0.375 (cung a2,4: 150/400). Nghiệm giữ nguyên waypoint nên dùng 0 thay đổi.

---

## Phần 9. Solver giải mô hình như thế nào

Bạn không phải tự giải. Phần mềm **HiGHS** (solver) làm việc đó. Nhưng cần hiểu các con số nó báo về, vì đề bắt ghi vào bảng.

### 9.1 LP relaxation: "nới lỏng"

- Bài toán có biến **0/1** rất khó giải, vì số tổ hợp cần thử khổng lồ.
- Solver tạm **cho phép x nhận số lẻ** trong đoạn [0, 1], ví dụ x = 0.5, tức "nửa demand đi đường này". Bài toán nới lỏng này gọi là **LP relaxation** và giải rất nhanh.
- Kết quả của nó **không thể tệ hơn** bài toán thật, vì nó được tự do hơn. Nên giá trị của nó là một **cận dưới** (LB): "MLU thật chắc chắn ≥ LB".

### 9.2 Branch-and-bound: "chia nhánh"

- Nếu nghiệm nới lỏng có biến lẻ (ví dụ x = 0.5), solver **chia đôi bài toán**: một nhánh ép x = 0, một nhánh ép x = 1. Nó giải từng nhánh, rồi lại chia tiếp nếu cần.
- Các nhánh tạo thành một **cây**. Mỗi bài toán con là một **nút của cây** (node). Đề bắt ghi **số nút**, và con số này cho biết bài toán khó tới mức nào.

### 9.3 UB, LB, Gap

- **UB** (cận trên) = MLU của **nghiệm tốt nhất đã tìm thấy**: một lựa chọn waypoint thật, có thể đem đi dùng.
- **LB** (cận dưới) = con số solver **chứng minh** được là không nghiệm nào tốt hơn.
- Giá trị tối ưu thật luôn nằm giữa: **LB ≤ tối ưu ≤ UB**.

```
Gap = 1 − LB / UB
```

- **Đọc là:** "gap bằng một trừ LB chia UB".
- **Nghĩa là:** khoảng cách tương đối giữa nghiệm đang có và cận dưới. Gap = 0 nghĩa là UB = LB: nghiệm đang có đã **được chứng minh là tối ưu**.
- **Ví dụ số:** hết giờ mà UB = 0.60 và LB = 0.55 thì Gap = 1 − 0.55/0.60 = 1 − 0.9167 = **0.0833 (8.33%)**. Nghĩa là: "nghiệm đang có tệ hơn tối ưu nhiều nhất 8.33%".

### 9.4 Trạng thái (Status) và CPU time

| Status | Nghĩa |
|---|---|
| **Optimal** | Đã tìm được nghiệm và chứng minh là tối ưu (Gap = 0) |
| **Not Optimal** | Hết thời gian (time limit), có nghiệm nhưng chưa chứng minh tối ưu, nên phải ghi Gap |
| **Infeasible** | Không có nghiệm nào thoả mọi ràng buộc (không xảy ra ở bài này, vì "không waypoint" luôn hợp lệ) |

**CPU time** là thời gian chạy của **riêng lệnh `optimize!`**, tức lúc solver làm việc. Không tính thời gian đọc file hay tính r.

---

## Phần 10. Vì sao instance lớn không chạy được

Số biến x **cho một chu kỳ** = (số demand) × (số cặp nút) ≈ `|D| × n × (n − 1)`.

| Instance | n (nút) | \|D\| (demand) | Số biến x | Ghi chú |
|---|---|---|---|---|
| toy | 7 | 2 | 2 × 42 = 84 | rất nhỏ |
| setA-01 | 20 | 40 | 40 × 380 = 15 200 | giải trong vài giây |
| setA-09 | 150 | 200 | 200 × 22 350 = 4 470 000 | dựng mô hình đã tốn 3.3 GB RAM; cả lượt chạy (chép vào HiGHS và giải) lên tới 17.7 GB |
| setA-20 | 400 | 6000 | 6000 × 159 600 = 957 600 000 | gần 1 tỉ biến, không máy tính thường nào chứa nổi |

Số cặp nút tăng theo **bình phương** số nút (n × n), rồi còn nhân với số demand. Vì vậy mô hình "phình" rất nhanh.

Đây là **giới hạn của mô hình**, không phải lỗi. Trong báo cáo, ghi rõ instance nào không dựng được và giải thích bằng bảng này.

---

## Phần 11. Từ công thức sang code Julia

Mỗi dòng công thức ở Phần 8 tương ứng với một dòng trong `src/model.jl`:

| Công thức | Code JuMP | Giải thích code |
|---|---|---|
| `U ≥ 0` | `@variable(model, U >= 0)` | tạo biến U, không âm |
| `x^{dt}_{ij} ∈ {0,1}` | `@variable(model, [1:D, 1:P], Bin)` | tạo bảng x: D hàng (demand) × P cột (segment); `Bin` = nhị phân 0/1 |
| (1) Ra − Vào = 1 / −1 / 0 | `@constraint(model, sum(xt[d,p] for p in out_of[i]) - sum(xt[d,p] for p in in_to[i]) == rhs)` | `out_of[i]` = các segment bắt đầu tại i; `in_to[i]` = các segment kết thúc tại i; `rhs` = 1, −1 hoặc 0 |
| (2) Σ x ≤ maxSeg | `@constraint(model, [d in 1:D], sum(xt[d, :]) <= inst.maxSeg)` | `xt[d, :]` = cả hàng d, tức mọi segment của demand d |
| (3) Σ r·ν·x ≤ U·c(a) | `add_to_expression!(load[a], ratio * vol, xt[d, p])` rồi `@constraint(model, load[a] <= U * inst.cap[a])` | cộng dồn từng số hạng r·ν·x vào `load[a]`, rồi so với U·c |
| (4a), (4b) | `@constraint(model, y >= xnow - xprev)` và `@constraint(model, y >= xprev - xnow)` | hai bất đẳng thức của bảng 4 trường hợp |
| (4c) | `@constraint(model, changes <= inst.budget[t])` | `changes` = tổng mọi y |
| `min U` | `@objective(model, Min, U)` | mục tiêu |
| Gọi solver | `optimize!(model)` | HiGHS bắt đầu giải; đây là phần được đo CPU time |

Phần tính r ở Phần 4 nằm trong `src/data.jl`:

- `r_ecmp`: cách của đề, chia đều tại mỗi ngã rẽ.
- `r_pathcount`: cách của `calculating_r.pdf`, đếm số đường.

---

## Phần 12. Tự kiểm tra

Che đáp án lại, tự trả lời, rồi mới xem.

1. Tại sao cung v4 → v5 **không** nằm trên đường ngắn nhất từ v4 tới v5, dù nó nối thẳng hai nút?
   > Vì ω(v4→v5) = 300, trong khi đi vòng v4 → v3 → v5 chỉ dài 200. Kiểm tra theo quy tắc: dist(v4) = 200 ≠ 300 + 0.
2. Nếu ν(d1, 0) tăng từ 100 lên 200 và không có waypoint, tải của a3,5 là bao nhiêu?
   > (0.75 × 50 + 0.5 × 200) / 200 = (37.5 + 100) / 200 = 0.6875.
3. Đường `⟨v0, v1, v4, v5⟩` bật những biến x nào? Có thoả ràng buộc (2) với maxSeg = 4 không?
   > x_{0,1}, x_{1,4}, x_{4,5}. Có 3 segment và 3 ≤ 4, nên thoả.
4. Với đường ở câu 3, kiểm tra ràng buộc (1) tại v1.
   > Ra = 1 (x_{1,4}), vào = 1 (x_{0,1}), nên ra − vào = 0. v1 không phải nguồn hay đích nên phải bằng 0 ✓.
5. Đổi `⟨s, w1, t⟩` thành `⟨s, w2, t⟩` tốn bao nhiêu budget?
   > Bỏ (s,w1) và (w1,t), thêm (s,w2) và (w2,t): tổng 4.
6. Vì sao không viết thẳng `min max λ` mà phải dùng biến U?
   > Vì `max` không tuyến tính. Dùng U làm "trần" (mọi λ ≤ U) rồi cực tiểu U thì cho cùng kết quả.
7. Vì sao r là **dữ liệu** mà không phải **biến**?
   > Vì r chỉ phụ thuộc vào mạng (ω, cung nào còn sống), không phụ thuộc vào waypoint ta chọn. Ta tính r trước bằng Dijkstra và ECMP.
8. UB = 0.80, LB = 0.76. Gap là bao nhiêu? Status là gì?
   > Gap = 1 − 0.76/0.80 = 0.05 = 5%. Status là "Not Optimal" vì gap > 0.

Trả lời đúng được cả 8 câu nghĩa là bạn đã hiểu đủ để viết phần Mô hình toán học của báo cáo. Bước tiếp theo xem trong [HUONG_DAN.md](HUONG_DAN.md).
