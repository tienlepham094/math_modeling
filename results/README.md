# Thư mục kết quả: nguồn gốc từng phần

Báo cáo chính là [report/paper/paper.pdf](../report/paper/paper.pdf). Bảng trong báo cáo được sinh từ các file dưới đây bằng [make_tables_m1.py](../report/paper/make_tables_m1.py) (phương pháp 1) và [make_tables_cg.py](../report/paper/make_tables_cg.py) (phương pháp 2).

| Đường dẫn | Nội dung | Máy |
|---|---|---|
| `m1opt/main/seed*/`, `m1opt/noloop/seed*/`, `m1opt/period1/seed0/` | Phương pháp 1, **chạy lại đêm 29/10** với cùng quy trình như `m1sync`, thêm cột `opt_mean` = thời gian của cả lệnh `optimize!` (CPU time theo định nghĩa của đề, đo sau một lần giải khởi động trên toy). **Đây là nguồn của Bảng III, IV, V trong báo cáo.** Đêm 29/10: 121 lượt (thêm Step 9 setA-05). Đêm 30/10: Step 9 setA-06 và 09 (cả hai bị chốt chặn dừng, RAM cao nhất 47.5 và 42.0 GB); Ngày 02/11: Step 9 setA-08 (bị chốt chặn dừng, RAM cao nhất 43.7 GB). Mọi dòng của Bảng III–V giờ lấy từ `m1opt`. Kiểm tra độc lập 111/111 nghiệm đạt (`m1opt/logs/verify.txt`). Log: `m1opt/logs/schedule.out`, `m1opt/logs/schedule_night2.out`, `m1opt/logs/schedule_s9_08.out` | B |
| `m1sync/main/seed*/`, `m1sync/noloop/seed*/`, `m1sync/period1/seed0/` | Phương pháp 1 chạy 28/10 (bản trước của báo cáo; thay bằng `m1opt`): CSV, `checks_step*.csv` (kiểm tra nghiệm), `memory_step*.csv` (RAM cao nhất), nghiệm `srpaths.json` (110/110 qua kiểm tra độc lập), log điều phối `m1sync/logs/schedule.out` | B |
| `reference/method1_machineA.csv` | Phương pháp 1, chép từ báo cáo cũ của nhóm. Không còn dùng trong các bảng; chỉ dùng để so sánh máy A với máy B ở mục VII-F của báo cáo | A: AMD EPYC 7713, 32 luồng, 128 GB |
| `reference/sprint_best_mlu.csv` | MLU tốt nhất của vòng sprint ROADEF 2026 (53 đội), từ repo của ban tổ chức | |
| `runs/seed0` … `runs/seed9` (`cg/`) | Phương pháp 2 (sinh cột): 20 instance × Step 6, 9, gồm CSV và nghiệm `srpaths.json` (định dạng checker chính thức). Instance được chạy lại có nhiều dòng; bảng lấy **dòng cuối**. Cột `status` của vài dòng setA-19 được ghi với ngưỡng cũ 10⁻⁶; script sinh bảng tính lại với 10⁻⁴ | B: Intel Xeon 2.20 GHz, 16 luồng, 62.8 GiB = 67.4 GB |
| `runs/logs/` | Nhật ký chạy; `verify_all_final.txt`: kiểm tra độc lập 400/400 nghiệm đạt | B |
| `cg/cg_step{6,9}_10runs.csv`, `cg/cg_10runs.md` | Tổng hợp 10 lần chạy của phương pháp 2 | B |
| `m1b/seed*/` | Lượt phương pháp 1 trên máy B ngày 26/10 (chưa có kiểm tra nghiệm); được thay bằng `m1sync/` | B |
| `m1b/step9.csv` | Phương pháp 1, Step 9 setA-06 (bị dừng ở chốt chặn 5400 s), bản cũ ngày 26/10, **không còn dùng** trong báo cáo (đã thay bằng lượt `m1opt` đêm 30/10); RAM lúc chạy (mẫu `docker stats`, 43.14 GiB ≈ 46 GB): `m1b/logs/s9_06_docker_stats.txt` | B |
| `step6.csv`, `step9.csv` | Lượt phương pháp 1 dở dang ngày 26/10 (bị dừng giữa chừng; Step 6 dùng biến thể no-loop). Trong báo cáo chỉ dùng MLU không waypoint của các dòng "Too large" | B |
| `old_2026-10-22/` | Kết quả cũ trên laptop, tính **trước** khi sửa lỗi `r_ecmp`; không dùng | laptop |
| `cg/old_single_run/`, `rerun/` | Các lượt chạy thử phương pháp 2 trước lượt 10 lần chính thức | B |

Chạy lại toàn bộ (lệnh và tham số đúng như đã dùng cho báo cáo, kể cả kiểm tra nghiệm và biên dịch PDF): [docs/TAI_TAO_KET_QUA.md](../docs/TAI_TAO_KET_QUA.md).
