#!/usr/bin/env bash
# =====================================================================
# Chạy TOÀN BỘ thí nghiệm (Step 6 + Step 9) trên server, từ đầu tới cuối.
#
# Mặc định chạy BẰNG DOCKER (server chỉ cần có Docker, không cần cài Julia,
# không đụng tới thư viện nào khác trên server).
#
# Cách dùng (trong thư mục project), chạy nền để tắt terminal vẫn không sao:
#
#   nohup scripts/run_server.sh > server_run.out 2>&1 &
#   tail -f server_run.out                    # xem tiến độ
#
# Không dùng Docker (cần Julia 1.13.2 trên server):  USE_DOCKER=0 nohup scripts/run_server.sh ...
#
# Kết quả nằm trong results/server/:
#   step6.csv, step9.csv, logs/, env_info.txt (thông tin máy cho báo cáo)
# và bảng LaTeX report/table_step6.tex, report/table_step9.tex
#
# Chạy lại đúng lệnh này nếu bị ngắt: instance đã xong sẽ được bỏ qua.
# =====================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ---------------- Cấu hình (đổi bằng biến môi trường khi gọi) ----------------
export RESULTS_DIR="${RESULTS_DIR:-results/server}"   # thư mục kết quả riêng cho server
USE_DOCKER="${USE_DOCKER:-1}"                         # 1 = chạy bằng Docker (mặc định), 0 = Julia trên máy
DOCKER="${DOCKER:-docker}"                            # "sudo docker" nếu user chưa thuộc nhóm docker
INSTANCES="${INSTANCES:-all}"                         # ví dụ: INSTANCES="1 2 3 4 5"
# Step 6: thêm ràng buộc "không đi vòng" (không đổi nghiệm tối ưu, nhanh hơn rất nhiều)
NO_LOOPS_STEP6="${NO_LOOPS_STEP6:-1}"
# Step 9: mặc định giữ đúng mô hình của đề (đi vòng có thể cần khi có budget)
NO_LOOPS_STEP9="${NO_LOOPS_STEP9:-0}"
# Chốt chặn cứng = time limit + 15 phút (HiGHS đôi khi không tự dừng đúng giờ với mô hình lớn)
HARD6="${HARD6:-2700}"     # Step 6: 1800 s + 900 s
HARD9="${HARD9:-4500}"     # Step 9: 3600 s + 900 s
# MAX_VARS: nếu không đặt, tự tính theo RAM trống (khoảng 1.5 GB cho mỗi triệu biến, chừa 2 GB)
if [[ -z "${MAX_VARS:-}" ]]; then
    avail_kb=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    MAX_VARS=$(( (avail_kb / 1024 / 1024 - 2) * 1000000 * 2 / 3 ))
    (( MAX_VARS < 1000000 )) && MAX_VARS=1000000
fi
export MAX_VARS

log() { echo "[$(date '+%F %T')] $*"; }

# ---------------- Hàm chạy một lệnh của scripts/run.sh ----------------
mkdir -p "$RESULTS_DIR/logs"
if [[ "$USE_DOCKER" == "1" ]]; then
    command -v docker >/dev/null || { log "LỖI: server chưa có Docker"; exit 1; }
    $DOCKER info >/dev/null 2>&1 || { log "LỖI: không dùng được Docker (permission denied?). Thử: DOCKER=\"sudo docker\" $0, hoặc xem docs/CAI_DAT_VA_CHAY.md mục 10"; exit 1; }
    # Luôn build lại để image khớp code hiện tại (có cache: lần đầu 10-20 phút, các lần sau vài giây)
    log "build Docker image orange-tasr"
    $DOCKER build -t orange-tasr . 2>&1 | tail -3
    run() {   # chạy trong container; truyền mọi biến cấu hình vào; kết quả ghi ra thư mục thật
        $DOCKER run --rm --user "$(id -u):$(id -g)" \
            -v "$ROOT/results:/app/results" -v "$ROOT/report:/app/report" \
            -e RESULTS_DIR -e MAX_VARS -e NO_LOOPS -e HARD_LIMIT -e TIME_LIMIT -e MAX_RUNS -e FAST \
            orange-tasr "$@"
    }
else
    run() { scripts/run.sh "$@"; }
    log "cài thư viện Julia (bỏ qua nếu đã cài)"
    run setup
fi

# ---------------- 0. Kiểm tra và ghi thông tin máy ----------------
log "kiểm tra trên toy"
run test
run info | tee "$RESULTS_DIR/env_info.txt"
log "cấu hình: RESULTS_DIR=$RESULTS_DIR MAX_VARS=$MAX_VARS NO_LOOPS step6=$NO_LOOPS_STEP6 step9=$NO_LOOPS_STEP9 HARD step6=$HARD6 step9=$HARD9"
echo "MAX_VARS=$MAX_VARS NO_LOOPS_STEP6=$NO_LOOPS_STEP6 NO_LOOPS_STEP9=$NO_LOOPS_STEP9 HARD6=$HARD6 HARD9=$HARD9" >> "$RESULTS_DIR/env_info.txt"

# ---------------- 1. Step 6: chỉ t = 0, time limit 1800 s ----------------
log "Step 6 bắt đầu"
NO_LOOPS=$NO_LOOPS_STEP6 HARD_LIMIT=$HARD6 run step6 $INSTANCES
log "Step 6 xong"

# ---------------- 2. Step 9: t = 0 và t = 1, time limit 3600 s ----------------
log "Step 9 bắt đầu"
NO_LOOPS=$NO_LOOPS_STEP9 HARD_LIMIT=$HARD9 run step9 $INSTANCES
log "Step 9 xong"

# ---------------- 3. Bảng cho báo cáo + tóm tắt ----------------
run tables
RESULTS_DIR="$RESULTS_DIR" run status
log "HOÀN TẤT. Kết quả: $RESULTS_DIR/step6.csv, $RESULTS_DIR/step9.csv; bảng: report/table_step*.tex"
