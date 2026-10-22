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
| Đọc và phân tích kết quả thí nghiệm, viết phần nhận xét trong báo cáo | [docs/PHAN_TICH_KET_QUA.md](docs/PHAN_TICH_KET_QUA.md) |
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
| `status` | Tóm tắt kết quả đã có | |
| `tables` | Sinh bảng LaTeX cho báo cáo từ CSV | báo cáo |
| `report` | Biên dịch báo cáo ra PDF (cần LaTeX) | báo cáo |
| `pluto` | Mở notebook Pluto của giảng viên ở http://localhost:1234 | 2 |

---

## 4. Cấu trúc thư mục

```
math_modeling/
├── README.md                     ← file này
├── Dockerfile, .dockerignore     ← đóng gói Docker
├── Project.toml, Manifest.toml   ← danh sách thư viện Julia và phiên bản CHÍNH XÁC (đừng xoá)
├── scripts/run.sh                ← lệnh chung (mục 3)
├── src/
│   ├── data.jl                   ← Step 2, 3, 4, 7: đọc JSON, dựng đồ thị G_t, tính r
│   ├── model.jl                  ← Step 5, 8: mô hình MILP; giải; đọc waypoint
│   ├── test_toy.jl               ← kiểm tra trên toy (lệnh test)
│   ├── run_experiments.jl        ← Step 6, 9: chạy SetA, ghi CSV
│   ├── make_tables.jl            ← CSV → bảng LaTeX
│   └── env_info.jl               ← thông tin máy và phần mềm
├── setA/                         ← 20 instance của giảng viên (3 file JSON mỗi instance)
├── toy/                          ← instance ví dụ của đề (7 nút, 2 demand)
├── results/                      ← kết quả: step6.csv, step9.csv, logs/
├── report/                       ← báo cáo LaTeX: report.tex, table_step6.tex, table_step9.tex
├── docs/                         ← tài liệu (mục 1)
├── json_to_graph_pluto_v2.jl     ← notebook Pluto của giảng viên (đồ thị đơn)
├── json_to_multigraph_pluto.jl   ← notebook Pluto của giảng viên (multigraph)
└── *.pdf, readme.txt             ← đề bài và hướng dẫn gốc
```

---

## 5. Tình trạng hiện tại (22/10/2026)

- **Code:** đủ cho Step 1–9. Đã kiểm tra trên toy: khớp Table 2 của đề, MLU tối ưu 0.375.
- **Thí nghiệm:** đang chạy trên máy gốc (Intel Core 7 240H, 16 GB RAM). Xem kết quả bằng `scripts/run.sh status`, phân tích trong [docs/PHAN_TICH_KET_QUA.md](docs/PHAN_TICH_KET_QUA.md).
- **Giới hạn đã biết:**
  - Mô hình có khoảng `|D| × n²` biến, nên chỉ instance nhỏ dựng được: Step 6 được 8/20, Step 9 được 5/20 trên máy 16 GB.
  - HiGHS đôi khi chạy quá time limit với mô hình lớn hơn khoảng 1.5 triệu biến. Script có chốt chặn cứng để không treo máy.
- **Báo cáo:** bản nháp tiếng Việt ở `report/report.tex`. Còn phải điền tên và viết nhận xét ở các chỗ `% TODO`.
