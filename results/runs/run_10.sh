#!/usr/bin/env bash
# Chạy phương pháp 2 mười lần (seed 0..9) cho Step 9 và Step 6: 8 lượt song song, mỗi lượt 2 luồng.
# Trong mỗi lượt, instance chạy từ lớn đến bé (theo số biến |D|·n² của mô hình MILP đầy đủ).
# Instance đã có trong CSV của seed đó được bỏ qua, nên chạy lại script này sẽ chạy tiếp phần còn thiếu.
cd "$(dirname "$0")/../.."
ORDER="20 19 16 18 17 13 15 14 10 12 11 7 6 9 8 5 4 3 2 1"
job() {   # $1 = step (6|9), $2 = seed
    docker run --rm --name "cg_s$1_seed$2" --user "$(id -u):$(id -g)" -v "$PWD/results:/app/results" \
        -e RESULTS_DIR="results/runs/seed$2" -e SEED="$2" -e THREADS=2 orange-tasr "cg$1" $ORDER \
        >> "results/runs/logs/step$1_seed$2.out" 2>&1
    echo "step$1 seed$2 exit=$? $(date '+%T')"
}
export -f job; export ORDER
# Thứ tự hàng đợi: việc dài nhất trước (Step 9 seed 8, 9 chưa chạy gì), rồi Step 9 seed 0-7 (còn 5 instance), rồi Step 6
{ echo "9 8"; echo "9 9"; for k in $(seq 0 7); do echo "9 $k"; done; for k in $(seq 0 9); do echo "6 $k"; done; } \
    | xargs -P 8 -L 1 bash -c 'job $0 $1'
echo "ALL DONE $(date '+%T')"
