# Tái tạo các con số của báo cáo chính

Báo cáo chính là [report/paper/paper.pdf](../report/paper/paper.pdf). Tài liệu này ghi **đúng các lệnh đã tạo ra mọi bảng** của báo cáo, để người khác chạy lại được. Nguồn gốc từng file kết quả: [results/README.md](../results/README.md).

Cần: Docker, Python 3 (≥ 3.8, chỉ thư viện chuẩn), image `orange-tasr` (`docker build -t orange-tasr .`, xem [CAI_DAT_VA_CHAY.md](CAI_DAT_VA_CHAY.md)). Mọi lệnh chạy từ thư mục gốc của project.

> **Lưu ý về thời gian.** Mọi thời gian trong báo cáo đo trên máy dùng chung (Intel Xeon 2.20 GHz, 16 luồng, 67.4 GB = 62.8 GiB RAM), có nhiều lượt chạy song song. Chạy lại trên máy khác hoặc với tải khác sẽ cho thời gian khác, và các lượt dừng theo time limit có thể cho nghiệm khác (mục 3).

## 1. Phương pháp 1 (MILP compact): Bảng III, IV, V

Quy trình của báo cáo:
- mô hình gốc (`NO_LOOPS=0`), time limit 1800 s (Step 6) và 3600 s (Step 9);
- chốt chặn `HARD_LIMIT` = time limit + 900 s (2700 s Step 6, 4500 s Step 9), riêng Step 9 setA-06 (mô hình lớn nhất được chạy, 1.5·10⁷ biến) là 5400 s; giá trị này do `schedule.py` đặt, khác mặc định của `scripts/run.sh` (xem dưới);
- mỗi lần chạy là **một tiến trình** với một seed (`SEED_START=k`, `MAX_RUNS=1`), ghi vào thư mục riêng `results/<lượt>/<loại>/seed<k>/` (`m1sync` ngày 28/10; `m1opt` đêm 29/10, đêm 30/10 cho Step 9 setA-06, 09 và sáng 02/11 cho Step 9 setA-08);
- mô hình dưới 10⁶ biến chạy 10 seed, lớn hơn chạy 1 seed.

Toàn bộ do một script điều phối. Script chạy từ instance lớn đến bé, chỉ khởi động một lượt khi RAM trống đủ cho ước tính của nó, giới hạn RAM mỗi container, và không khởi động lượt nào không kịp xong trước giờ dừng:

```bash
python3 results/m1sync/schedule.py --dry-run --out results/m1opt   # xem 124 lượt, RAM ước tính, lượt nào đã có
mkdir -p results/m1opt/logs
nohup python3 results/m1sync/schedule.py --out results/m1opt --start "2026-10-29 11:00" --deadline "2026-10-30 01:00" \
      > results/m1opt/logs/schedule.out 2>&1 &        # giờ UTC
```

Đêm 29/10 không kịp chạy 3 lượt Step 9 setA-06, 08, 09 trước giờ dừng. Chúng được chạy tiếp bằng **cùng script** (bỏ qua 121 lượt đã có):

```bash
# đêm 30/10: Step 9 setA-06, 09 (setA-08 lại không kịp trước giờ dừng)
nohup python3 results/m1sync/schedule.py --out results/m1opt --start "2026-10-30 11:00" --deadline "2026-10-31 01:00" \
      >> results/m1opt/logs/schedule_night2.out 2>&1 &
# ngày 02/11: Step 9 setA-08, chạy ngay (không có --start)
nohup python3 results/m1sync/schedule.py --out results/m1opt --deadline "2026-11-03 01:00" \
      >> results/m1opt/logs/schedule_s9_08.out 2>&1 &
```

- Cả ba lượt này đều bị chốt chặn dừng (5400 s với setA-06, 4500 s với 08, 09), không có cận.
- Mỗi lần còn chạy kèm `results/pause_at_8h_vn.sh '<giờ dừng UTC>'` (log `results/m1opt/logs/pause*.out`) để xoá mọi container của project lúc 01:00 UTC, trả RAM cho người dùng khác.
- Lượt đã có trong CSV sẽ được bỏ qua. Muốn chạy lại từ đầu thì dùng một thư mục `--out` mới.
- Lịch sử: lượt ngày 28/10 ghi vào `results/m1sync/`. Lượt chạy lại đêm 29/10 ghi vào `results/m1opt/`; lượt này có thêm cột `opt_mean` = thời gian của cả lệnh `optimize!` (gồm chép mô hình vào HiGHS và giải), đúng định nghĩa CPU time của đề. Mỗi tiến trình giải toy một lần trước (khởi động) để thời gian này không gồm thời gian biên dịch của Julia. Cột `cpu_mean` vẫn là thời gian giải do HiGHS báo (`solve_time`).
- Các loại lượt:

  | Loại | Biến môi trường | Dùng cho |
  |---|---|---|
  | `main` | mô hình gốc | Bảng III, IV |
  | `noloop` | `NO_LOOPS=1` | Bảng V |
  | `period1` | `PERIOD1_ONLY=1`: chỉ chu kỳ 1, không budget | đoạn "period 1 alone" của mục VII-D |

  Mỗi loại phải có `RESULTS_DIR` riêng, vì `PERIOD1_ONLY` ghi vào cùng tên file `step9.csv`.
- Mỗi lượt ghi thêm:
  - `checks_step*.csv`: kiểm tra nghiệm (đường Euler, MLU từ path, dist thật);
  - `memory_step*.csv`: RAM cao nhất của container (cgroup `memory.peak`);
  - nghiệm `setA-XX-step*-srpaths.json`, theo định dạng checker chính thức.
- Một lượt lẻ với cùng quy trình (tương đương một dòng của script):
  ```bash
  docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/results:/app/results" \
      -e RESULTS_DIR=results/m1opt/main/seed3 -e SEED_START=3 -e MAX_RUNS=1 -e MAX_VARS=20000000 \
      -e HARD_LIMIT=2700 -e NO_LOOPS=0 orange-tasr step6 2
  ```
  Mặc định của `scripts/run.sh` **khác** quy trình này:
  - `HARD_LIMIT` = 2·TL + 3600;
  - `MAX_RUNS=10` trong cùng một tiến trình, dừng sớm theo `FAST`;
  - `MAX_VARS=5000000`.

  Vì vậy luôn đặt đủ các biến như trên.

Các dòng không do script này tạo:
- **MLU không waypoint của các mô hình không dựng (dấu §):** lấy từ các dòng "Too large" của `results/step6.csv` và `results/step9.csv`.

## 2. Phương pháp 2 (sinh cột): Bảng VI

```bash
results/runs/run_10.sh            # seed 0..9 × Step 6 và Step 9; 8 container song song, mỗi container 2 luồng
```

- Mỗi container giải 20 instance theo thứ tự từ lớn đến bé và ghi vào `results/runs/seed<k>/cg/`.
- Lịch sử thực tế: lượt đầu (`run_10.sh`) dùng ngân sách vòng cải thiện 600 s. Sau đó mặc định đổi thành 780 s (Step 6) và 2400 s (Step 9), và hai script chạy lại các lượt mà ngân sách có thể ảnh hưởng (setA-16 cả hai bước, setA-19 Step 9):
  - `results/runs/rerun_timelimited.sh`;
  - `results/runs/rerun_uniform.sh`.
- Mỗi lần chạy lại ghi thêm một dòng vào CSV, và bảng **lấy dòng cuối** của mỗi instance. Ở các lượt còn lại, vòng cải thiện dừng trước 600 s, nên ngân sách không ràng buộc.
- Chạy lại `run_10.sh` bây giờ sẽ dùng thẳng mặc định cuối.
- Cột `status` trong CSV thô của một số dòng setA-19 được ghi với ngưỡng cũ (10⁻⁶). Script sinh bảng tính lại status với ngưỡng 10⁻⁴.

## 3. Tính lặp lại

- **Phương pháp 1:** HiGHS tất định với cùng seed, nhưng lượt dừng theo time limit thì dừng ở điểm phụ thuộc tốc độ máy và tải.
- **Phương pháp 2:**
  - Phần sinh cột tất định.
  - Các MILP dừng theo giới hạn thời gian thực (300 s, 120 s), nên cùng seed có thể cho kết quả khác. Ví dụ ở setA-19 Step 9: seed 2 và 4 không đạt tối ưu ở lượt đầu nhưng đạt khi chạy lại; seed 6 ngược lại. Báo cáo nói rõ điều này (mục VII-B và VII-F).

## 4. Kiểm tra nghiệm độc lập

```bash
python3 src/verify_srpaths.py 9 results/runs/seed0/cg results/reference/sprint_best_mlu.csv   # phương pháp 2, so với sprint
python3 src/verify_srpaths.py 6 results/m1opt/main/seed0                                      # phương pháp 1
```

- Script viết lại Dijkstra và ECMP bằng Python thuần, rồi kiểm tra từng nghiệm:
  - đúng nguồn và đích, ≤ maxSeg segment, không lặp segment;
  - không có tải trên link bị tắt, budget ≤ κ;
  - luồng tới đích đủ 1 đơn vị.
- Script thoát với mã khác 0 nếu có lỗi hoặc không tìm thấy file nghiệm.
- Kết quả đã chạy: 400/400 nghiệm của phương pháp 2 (`results/runs/logs/verify_all_final.txt`) và 111/111 nghiệm của phương pháp 1 trong lượt `m1opt` (`results/m1opt/logs/verify.txt`) đều đạt.

## 5. Bảng LaTeX và PDF

```bash
python3 report/paper/make_tables_m1.py m1opt   # Bảng III, IV, V và m1_facts.txt (các con số dùng trong văn bản)
python3 report/paper/make_tables_cg.py    # Bảng VI và cg_facts.txt
docker build -t orange-tasr-report --target report .    # TeX Live
docker build -t orange-tasr-paper -f Dockerfile.paper .  # thêm IEEEtran (texlive-publishers)
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/report/paper:/work" -w /work \
    --entrypoint bash orange-tasr-paper -c "pdflatex paper.tex && pdflatex paper.tex"
```

- `scripts/run.sh report` và target `report` biên dịch **bản nháp cũ** `report/report.tex`, không phải báo cáo chính.
- `scripts/run_server.sh` là quy trình cũ (26/10): Step 6 dùng `NO_LOOPS=1`, `MAX_VARS` 5 triệu và sinh bảng cũ `report/table_step*.tex`. Script này không tái tạo các bảng của báo cáo chính.
