#!/usr/bin/env bash
# Chạy một lần (26/10/2026): chờ lượt 10 lần của phương pháp 2 (results/runs/run_10.sh) xong, rồi
#   1. chạy lại phương pháp 1 (MILP đầy đủ) cho Step 6 và Step 9 song song, từ instance 20 xuống 1,
#      cấu hình như scripts/run_server.sh: Step 6 NO_LOOPS=1, HARD_LIMIT 2700 s; Step 9 HARD_LIMIT 4500 s; MAX_VARS 5 triệu;
#   2. sinh bảng LaTeX của phương pháp 1 (report/table_step6.tex, table_step9.tex);
#   3. tổng hợp 10 lần chạy của phương pháp 2 (results/cg/*_10runs.*, report/table_cg_step*.tex).
# Chạy nối tiếp để hai phương pháp không tranh CPU (thời gian đo được chính xác hơn).
cd "$(dirname "$0")/.."
ORDER="$(seq -s ' ' 20 -1 1)"      # từ instance 20 xuống 1
U="$(id -u):$(id -g)"
until grep -q "ALL DONE" results/runs/logs/run_10.out; do sleep 30; done
echo "[$(date '+%F %T')] phương pháp 2 (10 lần) xong; bắt đầu phương pháp 1"
docker run --rm --name m1_step6 --user "$U" -v "$PWD/results:/app/results" -e NO_LOOPS=1 -e HARD_LIMIT=2700 \
    orange-tasr step6 $ORDER > results/logs/m1_step6.out 2>&1 &
docker run --rm --name m1_step9 --user "$U" -v "$PWD/results:/app/results" -e NO_LOOPS=0 -e HARD_LIMIT=4500 \
    orange-tasr step9 $ORDER > results/logs/m1_step9.out 2>&1 &
wait
echo "[$(date '+%F %T')] phương pháp 1 xong"
docker run --rm --user "$U" -v "$PWD/results:/app/results" -v "$PWD/report:/app/report" orange-tasr tables
docker run --rm --user "$U" -v "$PWD/results:/app/results" orange-tasr status
python3 src/aggregate_cg.py results/runs results/reference/sprint_best_mlu.csv
echo "[$(date '+%F %T')] HOÀN TẤT"
