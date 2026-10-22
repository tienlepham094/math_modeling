# Cài đặt và chạy project trên máy bất kỳ

Tài liệu này hướng dẫn **từ máy trắng** tới lúc có bảng kết quả, theo hai cách:

- **Cách 1: Docker.** Không cần cài Julia. Mọi thứ đóng gói sẵn với đúng phiên bản. **Khuyên dùng khi chuyển sang máy khác.**
- **Cách 2: Chạy trực tiếp.** Cài Julia lên máy. Hợp khi muốn sửa code và chạy thử nhanh.

Cả hai cách đều dùng cùng một lệnh chung `scripts/run.sh` và cho cùng kết quả.

**Mục lục**

1. [Yêu cầu về máy](#1-yêu-cầu-về-máy)
2. [Mang project sang máy khác](#2-mang-project-sang-máy-khác)
3. [Cách 1: Docker](#3-cách-1-docker)
4. [Cách 2: Chạy trực tiếp](#4-cách-2-chạy-trực-tiếp)
5. [Cấu hình bằng biến môi trường](#5-cấu-hình-bằng-biến-môi-trường)
6. [Chạy thí nghiệm dài: chạy nền, chạy tiếp khi bị ngắt](#6-chạy-thí-nghiệm-dài-chạy-nền-chạy-tiếp-khi-bị-ngắt)
7. [Kết quả nằm ở đâu](#7-kết-quả-nằm-ở-đâu)
8. [Biên dịch báo cáo](#8-biên-dịch-báo-cáo)
9. [Đổi solver sang Gurobi](#9-đổi-solver-sang-gurobi)
10. [Xử lý sự cố](#10-xử-lý-sự-cố)
11. [Kiểm tra kết quả có tái lập được không](#11-kiểm-tra-kết-quả-có-tái-lập-được-không)

---

## 1. Yêu cầu về máy

| Thứ | Tối thiểu | Nên có | Ghi chú |
|---|---|---|---|
| Hệ điều hành | Linux, macOS, Windows 10/11 (qua WSL2) | Linux | Trên Windows, chạy mọi lệnh trong WSL2 (Ubuntu) |
| CPU | 2 nhân | 8 nhân trở lên | HiGHS chủ yếu dùng 1 nhân cho mỗi bài toán |
| RAM | 8 GB | 32 GB trở lên | **RAM quyết định instance nào chạy được** (bảng dưới) |
| Ổ đĩa | 5 GB trống | 10 GB | Docker image khoảng 2.2 GB, bản có LaTeX khoảng 3.1 GB |
| Mạng | Cần khi cài hoặc build | | Chạy thí nghiệm thì không cần mạng |
| Thời gian | | | Toàn bộ Step 6 + Step 9: từ vài giờ tới hơn 1 ngày tuỳ máy |

**RAM và instance chạy được** (số đo thật: dựng mô hình 4.47 triệu biến tốn 3.3 GB, HiGHS cần thêm khoảng chừng đó khi giải; quy tắc gần đúng là **1.5 GB RAM cho mỗi triệu biến**):

| RAM trống | `MAX_VARS` nên đặt | Step 6 chạy được | Step 9 chạy được |
|---|---|---|---|
| 4 GB | 2 000 000 | 01–05 | 01–04 |
| 8 GB | 5 000 000 | 01–06, 08, 09 | 01–05 |
| 16 GB | 10 000 000 | 01–09 | 01–05 |
| 32 GB | 20 000 000 | 01–09, 11, 12 | 01–06, 08, 09 |
| 64 GB | 40 000 000 | 01–12, 14, 15 | 01–09 |

Instance 13, 16–20 cần từ 80 triệu tới gần 1 tỉ biến, nên không máy tính thông thường nào chạy được mô hình này (xem [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), Phần 10). Lệnh `scripts/run.sh info` in ra `MAX_VARS` gợi ý dựa trên RAM đang trống của máy.

---

## 2. Mang project sang máy khác

**Cách 1: dùng git** (nếu project đã được push lên GitHub hoặc GitLab):

```bash
git clone <địa chỉ repo> math_modeling
cd math_modeling
```

**Cách 2: chép cả thư mục** (USB, Google Drive, nén zip…). **Bắt buộc phải có:**

- `Project.toml` và **`Manifest.toml`**: hai file này ghi phiên bản **chính xác** của từng thư viện. Thiếu `Manifest.toml` thì máy mới có thể cài phiên bản khác, và kết quả có thể khác đi.
- `src/`, `scripts/`, `setA/`, `toy/`, `report/`, `Dockerfile`, `.dockerignore`.
- `results/` nếu muốn giữ kết quả đã chạy. Script sẽ bỏ qua instance đã có kết quả và chỉ chạy phần còn thiếu.

**Không cần chép:** `.julia/`, `report/build/`, `.remember/`, `.trunk/`.

> **Nếu chép sang Windows rồi mới đưa vào WSL:** chạy `git config --global core.autocrlf input` trước khi clone, hoặc chuyển script về LF bằng `sed -i 's/\r$//' scripts/run.sh`. File `.gitattributes` của project đã ép LF cho mọi script khi dùng git.

---

## 3. Cách 1: Docker

### 3.1 Cài Docker

| Máy | Cách cài |
|---|---|
| Ubuntu / Debian | `curl -fsSL https://get.docker.com \| sh`, rồi `sudo usermod -aG docker $USER` và đăng xuất, đăng nhập lại |
| Windows | Cài **Docker Desktop**, bật "Use the WSL 2 based engine", rồi chạy các lệnh trong terminal WSL |
| macOS (Intel hoặc Apple M1/M2/M3) | Cài **Docker Desktop**. Image Julia có bản cho chip ARM, nên chạy được trên Apple Silicon |

Kiểm tra: `docker run --rm hello-world` phải in "Hello from Docker!".

> **Docker Desktop (Windows/macOS) mặc định chỉ cho container dùng một phần RAM của máy.** Vào **Settings → Resources → Memory** và kéo lên mức cao nhất có thể. Nếu không, các instance lớn sẽ bị dừng vì hết RAM dù máy còn nhiều RAM.

### 3.2 Build image

Trong thư mục project:

```bash
docker build -t orange-tasr .
```

- Lần đầu mất khoảng **10–20 phút**: tải Julia 1.13.2, cài và biên dịch thư viện theo `Manifest.toml`.
- Cuối quá trình build, Docker **tự chạy kiểm tra trên toy**. Nếu kiểm tra không đạt thì build báo lỗi, nên **build thành công nghĩa là chương trình đã chạy đúng**.
- Những lần build sau nhanh hơn nhiều nhờ cache, trừ khi `Manifest.toml` thay đổi.

### 3.3 Các lệnh hay dùng

Cú pháp chung: `docker run --rm [tuỳ chọn] orange-tasr <lệnh> [tham số]`, với `<lệnh>` lấy trong bảng ở [README](../README.md#3-các-lệnh).

```bash
# Kiểm tra (phải in "TẤT CẢ ĐẠT")
docker run --rm orange-tasr test

# Thông tin máy, phần mềm, gợi ý MAX_VARS
docker run --rm orange-tasr info

# Step 6 cho setA-01..05; kết quả ghi ra thư mục results/ của máy thật
docker run --rm -v "$PWD/results:/app/results" --user "$(id -u):$(id -g)" orange-tasr step6 1 2 3 4 5

# Step 9 cho tất cả, đặt MAX_VARS theo RAM của máy
docker run --rm -v "$PWD/results:/app/results" --user "$(id -u):$(id -g)" \
    -e MAX_VARS=10000000 orange-tasr step9 all

# Xem tóm tắt kết quả
docker run --rm -v "$PWD/results:/app/results" orange-tasr status
```

Giải thích các tuỳ chọn:

| Tuỳ chọn | Ý nghĩa |
|---|---|
| `--rm` | Xoá container sau khi chạy xong (image vẫn giữ). |
| `-v "$PWD/results:/app/results"` | **Nối** thư mục `results/` của máy thật vào container. Thiếu tuỳ chọn này thì kết quả **mất** khi container tắt. |
| `--user "$(id -u):$(id -g)"` | File kết quả thuộc về user của bạn, không thuộc root. Trên Docker Desktop có thể bỏ. |
| `-e TÊN=giá_trị` | Truyền biến cấu hình (mục 5). |

### 3.4 Chạy nền (thí nghiệm dài nhiều giờ)

```bash
docker run -d --name orange-step6 -v "$PWD/results:/app/results" --user "$(id -u):$(id -g)" \
    orange-tasr step6 all
docker logs -f orange-step6        # xem tiến độ (Ctrl+C để thôi xem, container vẫn chạy)
docker ps                          # container còn chạy không
docker rm orange-step6             # dọn sau khi xong
```

Có thể tắt cửa sổ terminal. Container vẫn chạy cho tới khi xong hoặc máy tắt.

### 3.5 Mở notebook Pluto của giảng viên (Step 2)

```bash
docker run --rm -p 1234:1234 orange-tasr pluto
```

Mở trình duyệt tại http://localhost:1234, chọn `/app/json_to_graph_pluto_v2.jl` (instance đồ thị đơn) hoặc `/app/json_to_multigraph_pluto.jl` (instance 05, 06, 08, 10, 12, 13, 14, 16, 17, 19).

### 3.6 Image có LaTeX để biên dịch báo cáo

```bash
docker build -t orange-tasr-report --target report .
docker run --rm --user "$(id -u):$(id -g)" \
    -v "$PWD/report:/app/report" -v "$PWD/results:/app/results" orange-tasr-report report
# Kết quả: report/build/report.pdf
```

---

## 4. Cách 2: Chạy trực tiếp

### 4.1 Cài Julia đúng phiên bản 1.13.2

Julia được quản lý bằng **juliaup**, công cụ cài đặt chính thức.

| Máy | Lệnh |
|---|---|
| Linux, macOS, WSL | `curl -fsSL https://install.julialang.org \| sh -s -- --yes` |
| Windows (PowerShell, nếu không dùng WSL) | `winget install --name Julia --id 9NJNWW8PVKMN -e -s msstore` |

Mở terminal **mới** (để PATH được cập nhật), rồi chọn đúng phiên bản dùng trong thí nghiệm:

```bash
juliaup add 1.13.2
juliaup default 1.13.2
julia --version              # phải in: julia version 1.13.2
```

> Phiên bản Julia khác (ví dụ 1.12) có thể vẫn chạy, nhưng `Manifest.toml` được tạo với 1.13.2, nên Julia sẽ cảnh báo và có thể cài phiên bản thư viện khác. Để chắc chắn tái lập, dùng 1.13.2.

### 4.2 Cài thư viện (một lần)

```bash
scripts/run.sh setup
```

Lệnh này đọc `Manifest.toml` rồi tải và biên dịch đúng phiên bản: JuMP 1.32.1, HiGHS.jl 1.26.1 (HiGHS 1.15.1), Graphs 1.15.0, JSON3 1.14.3, Pluto… Mất khoảng 5–15 phút.

Lệnh tương đương nếu không dùng script: `julia --project=. -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'`.

### 4.3 Kiểm tra và chạy

```bash
scripts/run.sh test            # phải in "TẤT CẢ ĐẠT"
scripts/run.sh info            # xem RAM, gợi ý MAX_VARS
scripts/run.sh step6 1 2 3     # thí nghiệm
```

**Trên Windows không có WSL:** `scripts/run.sh` cần bash (có trong Git Bash). Hoặc gọi thẳng Julia:

```powershell
julia --project=. src/test_toy.jl
julia --project=. src/run_experiments.jl 6 1 2 3
julia --project=. src/make_tables.jl
```

Lưu ý: gọi thẳng như vậy thì **không có chốt chặn cứng HARD_LIMIT** (mục 5).

---

## 5. Cấu hình bằng biến môi trường

Mọi cấu hình đều **không bắt buộc**. Mặc định đúng với yêu cầu của đề.

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `MAX_VARS` | `5000000` | Instance có nhiều biến hơn số này thì **không dựng mô hình**, chỉ ghi "Too large". Đặt theo RAM (bảng ở mục 1). |
| `TIME_LIMIT` | 1800 (Step 6), 3600 (Step 9) | Giới hạn thời gian của solver cho mỗi lần chạy (giây). **Đề yêu cầu đúng hai giá trị này.** Chỉ giảm khi muốn chạy thử nhanh. |
| `HARD_LIMIT` | `2 × TIME_LIMIT + 3600` | Chốt chặn cứng (giây). Quá hạn này thì tiến trình bị dừng và ghi "Killed". Cần có vì HiGHS đôi khi không tôn trọng `TIME_LIMIT` với mô hình lớn (đã gặp: 9905 s với giới hạn 3600 s). |
| `FAST` | `300` | Instance giải tối ưu trong dưới `FAST` giây thì được chạy lặp với seed khác. |
| `MAX_RUNS` | `10` | Số lần chạy tối đa mỗi instance (đề yêu cầu trung bình 10 lần). |
| `HEURISTIC` | `0.3` | Tham số `mip_heuristic_effort` của HiGHS (mặc định của HiGHS là 0.05). |
| `RESULTS_DIR` | `results` | Thư mục ghi CSV và log, tính từ thư mục project. |
| `FORCE` | `0` | `1` = chạy lại cả instance đã có kết quả. |
| `JULIA` | tự tìm | Đường dẫn tới chương trình julia, nếu không nằm trong PATH. |

Ví dụ:

```bash
MAX_VARS=10000000 scripts/run.sh step6 all                 # máy 16 GB RAM trống
TIME_LIMIT=60 MAX_RUNS=1 RESULTS_DIR=results/thu scripts/run.sh step6 1 2   # chạy thử nhanh, không đụng kết quả thật
FORCE=1 scripts/run.sh step9 3                              # chạy lại setA-03 cho Step 9
```

---

## 6. Chạy thí nghiệm dài: chạy nền, chạy tiếp khi bị ngắt

### 6.1 Thời gian ước lượng

- Mỗi instance tốn tối đa `HARD_LIMIT` giây (mặc định 2 giờ cho Step 6, 3 giờ cho Step 9), cộng thêm các lần chạy lặp nếu instance giải nhanh.
- Instance "Too large" chỉ tốn vài giây.
- Trên máy 16 GB: Step 6 khoảng 6–10 giờ, Step 9 khoảng 5–10 giờ.

### 6.2 Chạy nền (không Docker)

```bash
nohup scripts/run.sh all > results/logs/all.out 2>&1 &
tail -f results/logs/all.out          # xem tiến độ
```

Trên WSL: **giữ một cửa sổ terminal WSL mở**. Khi không còn cửa sổ nào, Windows có thể tắt WSL và dừng thí nghiệm. Với Docker thì dùng `docker run -d` (mục 3.4).

### 6.3 Chạy tiếp sau khi bị ngắt

Chỉ cần **gọi lại đúng lệnh cũ**:

- Instance nào đã có dòng trong `results/step6.csv` hoặc `results/step9.csv` thì được **bỏ qua**.
- Instance đang chạy dở lúc bị ngắt chưa có dòng nào, nên sẽ được chạy lại từ đầu.

Muốn chạy lại một instance đã có kết quả thì xoá dòng của nó trong CSV, hoặc dùng `FORCE=1`.

### 6.4 Trạng thái trong CSV

| `status` | Nghĩa |
|---|---|
| `Optimal` | Giải xong và chứng minh tối ưu |
| `Not Optimal` | Hết `TIME_LIMIT`, có nghiệm nhưng chưa chứng minh tối ưu; xem `gap` |
| `Too large` | Số biến > `MAX_VARS`, không dựng mô hình |
| `Killed` | Quá `HARD_LIMIT`, bị dừng cưỡng bức; `obj` là MLU của nghiệm "không waypoint" |
| `Out of memory` | Bị hệ điều hành dừng vì hết RAM; giảm `MAX_VARS` |

---

## 7. Kết quả nằm ở đâu

| File | Nội dung |
|---|---|
| `results/step6.csv`, `results/step9.csv` | Mỗi instance một dòng. Cột giải thích ở [PHAN_TICH_KET_QUA.md](PHAN_TICH_KET_QUA.md) |
| `results/logs/step6.log`, `step9.log` | Kết quả từng lần chạy (từng seed) |
| `report/table_step6.tex`, `table_step9.tex` | Bảng LaTeX sinh bởi `scripts/run.sh tables` |

---

## 8. Biên dịch báo cáo

Báo cáo nằm ở `report/report.tex` (tiếng Việt). Có ba cách:

1. **Overleaf (dễ nhất):**
   - Chạy `scripts/run.sh tables`.
   - Trên Overleaf: New Project → Upload Project. Tải lên `report.tex`, `table_step6.tex`, `table_step9.tex`.
   - Menu → Compiler: **pdfLaTeX**, rồi Recompile.
2. **Docker:** mục 3.6.
3. **LaTeX trên máy:** cần TeX Live có các gói `vntex`, `babel-vietnamese`, `booktabs`, `enumitem`, `lm`, `hyperref`. Trên Ubuntu: `sudo apt install texlive-latex-extra texlive-lang-other texlive-fonts-recommended`. Sau đó chạy `scripts/run.sh report`, file ra là `report/build/report.pdf`.

---

## 9. Đổi solver sang Gurobi

Gurobi thường nhanh hơn HiGHS nhiều với mô hình lớn. Gurobi cần **license** (license học thuật miễn phí, đăng ký tại gurobi.com bằng email trường, kích hoạt bằng `grbgetkey` khi đang dùng mạng của trường).

1. Cài Gurobi và kích hoạt license theo hướng dẫn của Gurobi.
2. `julia --project=. -e 'using Pkg; Pkg.add("Gurobi")'`
3. Trong `src/model.jl`:
   - `using JuMP, HiGHS` → `using JuMP, Gurobi`
   - `Model(HiGHS.Optimizer)` → `Model(Gurobi.Optimizer)`
   - `set_attribute(model, "random_seed", seed)` → `set_attribute(model, "Seed", seed)`
   - Xoá dòng `set_attribute(model, "mip_heuristic_effort", ...)`, hoặc thay bằng `set_attribute(model, "Heuristics", heuristic_effort)`.
4. Chạy `scripts/run.sh test`, rồi chạy lại toàn bộ thí nghiệm **vào thư mục kết quả mới** (`RESULTS_DIR=results/gurobi`). Kết quả của hai solver không trộn vào cùng một bảng.

Docker image hiện tại **không** có Gurobi, vì license gắn với máy cụ thể. Dùng Gurobi thì nên chạy trực tiếp.

---

## 10. Xử lý sự cố

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `Không tìm thấy julia` | Julia chưa cài hoặc chưa có trong PATH | Cài theo mục 4.1, mở terminal mới. Hoặc `export JULIA=/đường/dẫn/julia` |
| `bash\r: No such file or directory` hoặc `$'\r': command not found` | Script bị đổi sang xuống dòng kiểu Windows (CRLF) | `sed -i 's/\r$//' scripts/run.sh` |
| `Permission denied: scripts/run.sh` | Mất quyền thực thi khi chép file | `chmod +x scripts/run.sh` |
| `Pkg.instantiate` báo lỗi mạng hoặc SSL | Mạng chặn pkg.julialang.org | Thử mạng khác, hoặc `export JULIA_PKG_SERVER=""` để tải trực tiếp từ GitHub |
| Cảnh báo `Manifest was resolved with a different julia version` | Không dùng Julia 1.13.2 | `juliaup add 1.13.2 && juliaup default 1.13.2` |
| `test` báo `[KHÔNG ĐẠT]` | Code hoặc dữ liệu bị sửa, hoặc thiếu file `toy/` | Kiểm tra `toy/` có đủ 3 file JSON; so sánh `src/` với bản gốc |
| Trạng thái `Out of memory`, hoặc máy treo hay rất chậm khi chạy | Hết RAM | Giảm `MAX_VARS` (mục 1); đóng chương trình khác; với Docker Desktop thì tăng Memory |
| CPU time lớn hơn `TIME_LIMIT` | HiGHS không kiểm tra giới hạn khi đang presolve hoặc giải LP gốc của mô hình lớn | Bình thường với mô hình lớn. `HARD_LIMIT` sẽ chặn. Ghi chú trong báo cáo (bảng có dấu `*`) |
| Docker: `permission denied` khi ghi `results/` | Thư mục thuộc root, hoặc user không khớp | Thêm `--user "$(id -u):$(id -g)"`; hoặc `sudo chown -R $USER results` |
| Docker build dừng ở bước `Pkg.precompile()` với `Killed` hoặc `returned a non-zero code: 137` | Hết RAM khi biên dịch thư viện | Build với ít luồng hơn: `docker build --build-arg PRECOMPILE_TASKS=1 -t orange-tasr .`; với Docker Desktop thì tăng Memory (mục 3.1) |
| Docker: `Cannot connect to the Docker daemon` | Docker chưa chạy | Mở Docker Desktop, hoặc `sudo systemctl start docker` |
| Thí nghiệm dừng giữa chừng khi đóng VS Code hoặc terminal | Tiến trình con bị tắt theo terminal | Dùng `nohup … &` (mục 6.2) hoặc `docker run -d` (mục 3.4). Chạy lại lệnh cũ để làm tiếp phần còn thiếu |
| Pluto không mở được trong Docker | Thiếu `-p 1234:1234` | `docker run --rm -p 1234:1234 orange-tasr pluto` |

---

## 11. Kiểm tra kết quả có tái lập được không

- **Giá trị MLU (`obj`) của các instance `Optimal`** phải **giống hệt** trên mọi máy, vì đó là giá trị tối ưu của bài toán. Đây là cách kiểm tra quan trọng nhất.
- **CPU time và số nút B&B** sẽ **khác** giữa các máy (do CPU khác) và cả giữa các lần chạy (do seed). Đó là bình thường. Báo cáo phải ghi rõ cấu hình máy (`scripts/run.sh info`).
- Với các instance `Not Optimal`, `obj` có thể khác giữa các máy, vì solver dừng ở những điểm khác nhau khi hết giờ.

Giá trị tham chiếu (máy gốc, HiGHS 1.15.1):

| Instance | Step 6: MLU tối ưu | Step 9: MLU tối ưu |
|---|---|---|
| toy | 0.375 | 0.375 |
| setA-01 | 0.929384 | 0.929384 |
| setA-02 | 0.548578 | 0.903075 |
| setA-03 | 0.943543 | 0.943543 |
| setA-05 | 0.115524 | (đang chạy) |
