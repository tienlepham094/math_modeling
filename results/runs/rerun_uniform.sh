#!/usr/bin/env bash
# Đồng nhất cấu hình của 10 lần chạy (theo review code): chạy lại với cấu hình cuối (IMP_TIME 780/2400 s)
# các lượt còn dùng IMP_TIME 600 s ở hai instance có vòng cải thiện dài: Step 9 setA-19 (8 seed còn lại)
# và Step 6 setA-16 (seed 6, 7, 8). 4 lượt song song để không tranh RAM với lượt phương pháp 1 setA-06 (~45 GB).
cd "$(dirname "$0")/../.."
job() {   # $1 = step, $2 = seed, $3 = instance
    docker run --rm --name "cg_un$1_seed$2_$3" --user "$(id -u):$(id -g)" -v "$PWD/results:/app/results" \
        -e RESULTS_DIR="results/runs/seed$2" -e SEED="$2" -e THREADS=2 -e FORCE=1 orange-tasr "cg$1" "$3" \
        >> "results/runs/logs/step$1_seed$2.out" 2>&1
    echo "uniform step$1 seed$2 setA-$3 exit=$? $(date -u '+%T')"
}
export -f job
{ for k in 0 1 3 5 6 7 8 9; do echo "9 $k 19"; done; for k in 6 7 8; do echo "6 $k 16"; done; } | xargs -P 4 -L 1 bash -c 'job $0 $1 $2'
echo "UNIFORM DONE $(date -u '+%T')"
