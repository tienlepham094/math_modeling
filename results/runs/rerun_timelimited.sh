#!/usr/bin/env bash
# Chạy lại các lượt mà vòng cải thiện bị cắt vì hết IMP_TIME cũ (600 s), với mặc định mới
# (IMP_TIME 2400 s cho Step 9, 780 s cho Step 6). Danh sách lấy từ phân tích: gap > 0 và milp_s >= 600.
# Dòng mới được ghi thêm vào CSV của seed đó; src/aggregate_cg.py lấy dòng cuối của mỗi instance.
cd "$(dirname "$0")/../.."
until grep -q "ALL DONE" results/runs/logs/run_10.out; do sleep 30; done
job() {   # $1 = step, $2 = seed, $3 = instance
    docker run --rm --name "cg_re$1_seed$2_$3" --user "$(id -u):$(id -g)" -v "$PWD/results:/app/results" \
        -e RESULTS_DIR="results/runs/seed$2" -e SEED="$2" -e THREADS=2 -e FORCE=1 orange-tasr "cg$1" "$3" \
        >> "results/runs/logs/step$1_seed$2.out" 2>&1
    echo "rerun step$1 seed$2 setA-$3 exit=$? $(date '+%T')"
}
export -f job
{ echo "9 2 19"; echo "9 4 19"; for k in $(seq 0 9); do echo "9 $k 16"; done; for k in $(seq 0 5); do echo "6 $k 16"; done; } \
    | xargs -P 5 -L 1 bash -c 'job $0 $1 $2'
echo "RERUN DONE $(date '+%T')"
