# Project Orange: ROADEF/EURO Challenge 2026 "Keep The Flow!"

Cài đặt và thí nghiệm mô hình **MILP** (quy hoạch tuyến tính nguyên) cho bài toán **T-Adaptive Segment Routing (T-ASR)**: chọn waypoint cho các luồng dữ liệu trong mạng Orange, sao cho **link đầy nhất bị đầy ít nhất**, kể cả khi có link bị tắt để bảo trì.

- **Ngôn ngữ và công cụ:** Julia 1.13.2, JuMP, solver HiGHS (miễn phí).
- **Chạy được:** trực tiếp trên Linux, macOS, Windows (qua WSL), hoặc bằng **Docker** (khuyên dùng khi chuyển sang máy khác).
- **Hạn nộp báo cáo:** Chủ nhật 25/10/2026.

---

## 1. Đọc gì trước?

| Bạn muốn… | Đọc file |
|---|---|
| Hiểu bài toán từ con số 0: mọi khái niệm, ký hiệu, công thức, có ví dụ số | [docs/GIAI_THICH_TU_DAU.md](docs/GIAI_THICH_TU_DAU.md) |
| Biết từng Step 1→9 của giảng viên phải làm gì, ra kết quả gì | [docs/HUONG_DAN.md](docs/HUONG_DAN.md) |
| Cài đặt và chạy trên máy khác (có hoặc không có Docker), cấu hình, xử lý lỗi | [docs/CAI_DAT_VA_CHAY.md](docs/CAI_DAT_VA_CHAY.md) |
| Đọc và phân tích kết quả thí nghiệm (số liệu và nhận xét hiện hành) | Báo cáo chính [report/paper/paper.pdf](report/paper/paper.pdf), mục VII. [docs/PHAN_TICH_KET_QUA.md](docs/PHAN_TICH_KET_QUA.md) **đã cũ** (số liệu 22/10, trước khi sửa `r_ecmp`), chỉ còn dùng để hiểu các cột CSV |
| Hiểu phương pháp 2 (column generation), chạy được cả 20 instance, và kết quả của nó | [docs/PHUONG_PHAP_CG.md](docs/PHUONG_PHAP_CG.md) |
| **Đọc báo cáo chính** (tiếng Anh, 10 trang) | [report/paper/paper.pdf](report/paper/paper.pdf) |
| Tái tạo đúng các bảng của báo cáo chính (lệnh, tham số, kiểm tra nghiệm, biên dịch PDF) | [docs/TAI_TAO_KET_QUA.md](docs/TAI_TAO_KET_QUA.md) |
| Biết mỗi file trong `results/` từ đâu ra | [results/README.md](results/README.md) |
| Xem các điểm cần lưu ý trong đề và trong mô hình (review) | [docs/review.md](docs/review.md) |
| Tìm tài liệu tham khảo, paper liên quan | [docs/survey.md](docs/survey.md) |

Tài liệu gốc: đề bài `Challenge_Orange_ROADEF_2026_Subject.pdf`, hướng dẫn tính `r` `calculating_r.pdf`, yêu cầu của giảng viên `readme.txt`.

---

## 2. Chạy nhanh

### Cách A: bằng Docker (không cần cài Julia)

```bash
docker build -t orange-tasr .                 # build lần đầu: 10–20 phút, cần mạng
docker run --rm orange-tasr test              # kiểm tra trên toy, phải in "TẤT CẢ ĐẠT"
docker run --rm -v "$PWD/results:/app/results" orange-tasr step6 1 2 3   # Step 6 cho setA-01..03
```

### Cách B: chạy trực tiếp

```bash
curl -fsSL https://install.julialang.org | sh -s -- --yes   # cài juliaup (một lần)
juliaup add 1.13.2 && juliaup default 1.13.2                # đúng phiên bản dùng trong thí nghiệm
scripts/run.sh setup                                        # cài thư viện theo Manifest.toml (một lần)
scripts/run.sh test                                         # phải in "TẤT CẢ ĐẠT"
scripts/run.sh step6 1 2 3
```

### Cách C: tái tạo các bảng của báo cáo chính

Phương pháp 1 dùng `python3 results/m1sync/schedule.py --out results/m1opt` (mỗi seed một tiến trình, điều phối theo RAM trống; script nằm trong `m1sync/` nhưng kết quả của báo cáo ghi vào `results/m1opt/`). Phương pháp 2 dùng `results/runs/run_10.sh`. Sau đó sinh bảng bằng `report/paper/make_tables_*.py`. Toàn bộ lệnh: [docs/TAI_TAO_KET_QUA.md](docs/TAI_TAO_KET_QUA.md).

`scripts/run_server.sh` là quy trình cũ (26/10). Nó không tái tạo các bảng của báo cáo chính: Step 6 dùng `NO_LOOPS=1`, và script sinh bảng cũ.

Chi tiết, các lựa chọn khác và cách xử lý lỗi: [docs/CAI_DAT_VA_CHAY.md](docs/CAI_DAT_VA_CHAY.md).

---

## 3. Các lệnh

Mọi việc đều qua một script, `scripts/run.sh <lệnh>`. Với Docker, thay `scripts/run.sh` bằng `docker run --rm [-v ...] orange-tasr`.

| Lệnh | Làm gì | Step của giảng viên |
|---|---|---|
| `setup` | Cài thư viện Julia đúng phiên bản (chỉ chạy trực tiếp, Docker đã cài sẵn) | |
| `info` | In thông tin máy, phiên bản phần mềm, gợi ý `MAX_VARS` theo RAM | báo cáo: môi trường |
| `test` | Kiểm tra toàn bộ trên ví dụ toy của đề | 2, 3, 5, 7, 8 |
| `step6 <ids\|all>` | Thí nghiệm chỉ t = 0, giới hạn 1800 s | 6 |
| `step9 <ids\|all>` | Thí nghiệm t = 0 và t = 1 có budget, giới hạn 3600 s | 9 |
| `all` | `step6 all` rồi `step9 all` | 6, 9 |
| `cg6 <ids\|all>` | Phương pháp 2 (column generation) cho Step 6, chạy được cả 20 instance | 6 |
| `cg9 <ids\|all>` | Phương pháp 2 cho Step 9 (hai chu kỳ, có budget) | 9 |
| `status` | Tóm tắt kết quả đã có | |
| `tables` | Sinh bảng LaTeX của **bản nháp cũ** (`report/table_step*.tex`) từ CSV. Bảng của báo cáo chính: `python3 report/paper/make_tables_m1.py m1opt` và `python3 report/paper/make_tables_cg.py` | báo cáo |
| `report` | Biên dịch **bản nháp cũ** `report/report.tex` (cần LaTeX). Báo cáo chính: [docs/TAI_TAO_KET_QUA.md](docs/TAI_TAO_KET_QUA.md), mục 5 | báo cáo |
| `pluto` | Mở notebook Pluto của giảng viên ở http://localhost:1234 | 2 |

---

## 4. Cấu trúc thư mục

```
math_modeling/
├── README.md                     ← file này
├── Dockerfile, .dockerignore     ← đóng gói Docker
├── Project.toml, Manifest.toml   ← danh sách thư viện Julia và phiên bản CHÍNH XÁC (đừng xoá)
├── scripts/run.sh                ← lệnh chung (mục 3)
├── scripts/run_server.sh         ← quy trình cũ (26/10), không tái tạo báo cáo chính
├── src/
│   ├── data.jl                   ← Step 2, 3, 4, 7: đọc JSON, dựng đồ thị G_t, tính r
│   ├── model.jl                  ← Step 5, 8: mô hình MILP; giải; đọc waypoint
│   ├── test_toy.jl               ← kiểm tra trên toy (lệnh test)
│   ├── run_experiments.jl        ← Step 6, 9: chạy SetA, ghi CSV
│   ├── make_tables.jl            ← CSV → bảng LaTeX
│   ├── env_info.jl               ← thông tin máy và phần mềm
│   ├── colgen.jl, improve.jl     ← phương pháp 2: column generation, MILP trên tập cột, vòng cải thiện
│   ├── run_cg.jl                 ← phương pháp 2: chạy SetA (lệnh cg6, cg9), ghi results/cg/
│   ├── aggregate_cg.py           ← tổng hợp 10 lần chạy của phương pháp 2
│   └── verify_srpaths.py         ← kiểm tra độc lập file nghiệm srpaths.json (Python thuần)
├── setA/                         ← 20 instance của giảng viên (3 file JSON mỗi instance)
├── toy/                          ← instance ví dụ của đề (7 nút, 2 demand)
├── results/                      ← mọi kết quả; nguồn gốc từng thư mục: results/README.md
│   ├── m1opt/                    ← phương pháp 1 dùng trong báo cáo (Bảng III–V)
│   ├── m1sync/                   ← lượt cũ 28/10 của phương pháp 1 (không dùng) + schedule.py
│   └── runs/seed0..9/cg/         ← phương pháp 2 dùng trong báo cáo (Bảng VI) + run_10.sh
├── report/paper/                 ← BÁO CÁO CHÍNH: paper.tex, paper.pdf, make_tables_m1.py, make_tables_cg.py
├── report/report.tex             ← bản nháp tiếng Việt cũ (không dùng; bảng report/table_*.tex cũng cũ)
├── docs/                         ← tài liệu (mục 1)
├── json_to_graph_pluto_v2.jl     ← notebook Pluto của giảng viên (đồ thị đơn)
├── json_to_multigraph_pluto.jl   ← notebook Pluto của giảng viên (multigraph)
└── *.pdf, readme.txt             ← đề bài và hướng dẫn gốc
```

---

## 5. Tình trạng hiện tại (02/11/2026)

- **Báo cáo chính:** [report/paper/paper.pdf](report/paper/paper.pdf), 10 trang, tiếng Anh. Mọi bảng được sinh từ dữ liệu thô bằng `report/paper/make_tables_m1.py` và `make_tables_cg.py`.
- **Phương pháp 1 (MILP compact):**
  - chạy trên máy B đêm 29/10 (`results/m1opt/`), mỗi seed một tiến trình, kèm kiểm tra nghiệm và đo RAM; cột CPU là thời gian của cả lệnh `optimize!` như đề yêu cầu;
  - chứng minh tối ưu ở Step 6: 01, 02, 03, 05; Step 9: 01, 02, 03;
  - Step 6 setA-10–20 và Step 9 setA-07, 10–20 không dựng được mô hình vì thiếu RAM;
  - Step 9 setA-06, 08, 09 chạy thêm đêm 30/10 và ngày 02/11 (bị dừng ở chốt chặn, không có cận); mọi bảng của phương pháp 1 giờ cùng một máy, cùng một quy trình.
- **Phương pháp 2 (sinh cột):**
  - 20 instance × 2 bước × 10 seed, mọi nghiệm qua kiểm tra độc lập;
  - ở Step 9, giá trị tốt nhất bằng kết quả tốt nhất của vòng sprint challenge ở 20/20 instance (mọi lần chạy: 19/20).
- **Đã sửa lỗi** trong `r_ecmp` (`src/data.jl`, 26/10): so sánh số thực bằng `==` làm mất luồng ở setA-08, 12, 14. Kết quả tính trước khi sửa nằm ở `results/old_2026-10-22/` và không được dùng.
- **Image Docker `orange-tasr`** được build lại ngày 29/10. Code mới đo thêm thời gian của **cả lệnh `optimize!`** (cột `opt_mean`, đúng định nghĩa CPU time của đề). Lượt chạy lại phương pháp 1 đêm 29/10 dùng image này, ghi vào `results/m1opt/`; lượt ngày 28/10 nằm ở `results/m1sync/`.
