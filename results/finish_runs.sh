#!/bin/bash
# Script một lần cho máy hiện tại (22/10/2026): hoàn tất phần thí nghiệm còn lại,
# rồi build và kiểm tra Docker image. Log ghi vào results/logs/finish_runs.log.
cd "$(dirname "$0")/.."
log=results/logs/finish_runs.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$log"; }

# 1. Dừng chuỗi chạy cũ (run_rest.sh), nhưng để tiến trình Step 9 setA-05 đang chạy tiếp
kill 67851 2>/dev/null && say "đã huỷ run_rest.sh (không chạy step6 9 8 6 kiểu cũ)"

# 2. Step 9 setA-05: bắt đầu khoảng 18:29:37, áp HARD_LIMIT = 10800 s như scripts/run.sh
deadline=$(date -d '2026-10-22 21:29:37' +%s)
while kill -0 67854 2>/dev/null; do
    if (( $(date +%s) > deadline )); then
        kill -9 67854
        echo "setA-05,100,396,100,2970000,0.999986,1,Killed,0.999986,,,10800,0,," >> results/step9.csv
        say "Step 9 setA-05 vượt 10800 s => dừng, ghi Killed"
        break
    fi
    sleep 30
done
say "Step 9 xong"

# 3. Step 6 cho 3 instance nặng, có chốt chặn cứng (2 x 1800 + 3600 = 7200 s mỗi instance)
say "bắt đầu Step 6 cho setA-09, 08, 06"
scripts/run.sh step6 9 8 6 >> "$log" 2>&1
scripts/run.sh tables >> "$log" 2>&1
say "thí nghiệm xong"

# 4. Build và kiểm tra Docker image (để sau cùng vì cần nhiều RAM)
say "docker build orange-tasr"
docker build -t orange-tasr . > results/logs/docker_build.log 2>&1 && say "build OK" || say "build LỖI (xem docker_build.log)"
docker run --rm orange-tasr test > results/logs/docker_test.log 2>&1 && say "docker test OK" || say "docker test LỖI"
docker run --rm --user "$(id -u):$(id -g)" orange-tasr info >> results/logs/docker_test.log 2>&1 && say "chạy với --user OK" || say "chạy với --user LỖI"

say "docker build orange-tasr-report"
docker build -t orange-tasr-report --target report . >> results/logs/docker_build.log 2>&1 && say "build report OK" || say "build report LỖI"
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/report:/app/report" -v "$PWD/results:/app/results" \
    orange-tasr-report report >> results/logs/docker_test.log 2>&1 && say "biên dịch báo cáo OK: report/build/report.pdf" || say "biên dịch báo cáo LỖI"
say "HOÀN TẤT"
