#!/usr/bin/env bash
# Phương pháp 1 (mô hình MILP gốc) trên máy B (Xeon, 62 GB), 10 seed, theo đúng quy trình của báo cáo:
# mỗi lần chạy là một tiến trình riêng (SEED_START=k, MAX_RUNS=1), mô hình gốc (NO_LOOPS=0, cả Step 6),
# mip_heuristic_effort 0.3, time limit 1800/3600 s, chốt chặn TL + 900 s. Các instance có < 1e6 biến:
# Step 6: 01-05, Step 9: 01-03. Thứ tự: instance lớn trước (theo số biến), 8 lượt song song.
# Bắt đầu sau khi lượt Step 9 setA-06 (cần ~48 GB RAM, chạy một mình) kết thúc.
cd "$(dirname "$0")/../.."
while docker ps --format '{{.Names}}' | grep -q '^m1b_s9_06$'; do sleep 30; done
job() {   # $1 = step, $2 = instance, $3 = seed
    local hard=$([[ $1 == 6 ]] && echo 2700 || echo 4500)
    docker run --rm --name "m1b_s$1_$2_seed$3" --user "$(id -u):$(id -g)" -v "$PWD/results:/app/results" \
        -e RESULTS_DIR="results/m1b/seed$3" -e SEED_START="$3" -e MAX_RUNS=1 -e NO_LOOPS=0 -e HARD_LIMIT="$hard" \
        orange-tasr "step$1" "$2" >> "results/m1b/logs/step$1_seed$3.out" 2>&1
    echo "step$1 setA-$2 seed$3 exit=$? $(date -u '+%T')"
}
export -f job
# số biến: S6-05 9.9e5, S6-04 4.9e5, S9-03 1.5e5, S9-02 1.2e5, S6-03 4.9e4, S9-01 4.6e4, S6-02 3.9e4, S6-01 1.5e4
{ for t in "6 5" "6 4" "9 3" "9 2" "6 3" "9 1" "6 2" "6 1"; do for k in $(seq 0 9); do echo "$t $k"; done; done; } \
    | xargs -P 8 -L 1 bash -c 'job $0 $1 $2'
echo "SMALL DONE $(date -u '+%T')"
