#!/usr/bin/env bash
# =====================================================================
# Lệnh chung của project. Dùng được trực tiếp trên máy và bên trong Docker.
#
#   scripts/run.sh help            # xem danh sách lệnh
#   scripts/run.sh test            # kiểm tra trên instance toy (chạy đầu tiên!)
#   scripts/run.sh step6 1 2 3     # Step 6 cho setA-01, 02, 03 (hoặc: step6 all)
#   scripts/run.sh step9 all       # Step 9 cho cả 20 instance
#
# Biến môi trường dùng chung: JULIA (đường dẫn julia), MAX_VARS, FAST, MAX_RUNS,
# HEURISTIC, TIME_LIMIT, RESULTS_DIR, FORCE  (xem docs/CAI_DAT_VA_CHAY.md)
# =====================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Tìm julia: biến JULIA > lệnh julia trong PATH > ~/.juliaup/bin/julia
if [[ -z "${JULIA:-}" ]]; then
    if command -v julia >/dev/null 2>&1; then JULIA=julia
    elif [[ -x "$HOME/.juliaup/bin/julia" ]]; then JULIA="$HOME/.juliaup/bin/julia"
    else echo "Không tìm thấy julia. Cài theo docs/CAI_DAT_VA_CHAY.md mục 3, hoặc dùng Docker." >&2; exit 1
    fi
fi
J=("$JULIA" "--project=$ROOT")

usage() {
    cat <<'EOF'
Cách dùng: scripts/run.sh <lệnh> [tham số]

  setup              Cài các thư viện Julia đúng phiên bản trong Manifest.toml (chỉ cần một lần)
  info               In thông tin máy, phiên bản phần mềm, gợi ý MAX_VARS
  test               Kiểm tra toàn bộ trên instance toy. Phải in "TẤT CẢ ĐẠT"
  step6 <ids|all>    Step 6: chỉ t = 0, giới hạn 1800 s/lần. Ví dụ: step6 1 2 3
  step9 <ids|all>    Step 9: t = 0 và 1 có budget, giới hạn 3600 s/lần. Ví dụ: step9 all
  all                Chạy step6 all rồi step9 all (rất lâu, nên chạy nền)
  cg6 <ids|all>      Phương pháp 2 (column generation) cho Step 6, chạy được cả 20 instance
  cg9 <ids|all>      Phương pháp 2 cho Step 9 (t = 0 và 1, có budget). Kết quả ở results/cg/
  status             Xem tóm tắt kết quả đã có trong results/
  tables             Sinh bảng LaTeX report/table_step6.tex và table_step9.tex từ CSV
  report             Biên dịch report/report.tex ra report/build/report.pdf (cần pdflatex)
  pluto              Mở Pluto để xem notebook của giảng viên (cổng 1234)
  help               In hướng dẫn này
EOF
}

cmd="${1:-help}"; shift || true
case "$cmd" in
    setup)
        "${J[@]}" -e 'using Pkg; Pkg.instantiate(); Pkg.precompile(); println("Cài đặt xong.")' ;;
    info)
        "${J[@]}" src/env_info.jl ;;
    test)
        "${J[@]}" src/test_toy.jl ;;
    step6|step9)
        [[ $# -ge 1 ]] || { echo "Thiếu danh sách instance. Ví dụ: scripts/run.sh $cmd 1 2 3  hoặc  $cmd all" >&2; exit 1; }
        step="${cmd#step}"
        ids=("$@"); [[ "$1" == "all" ]] && ids=($(seq 1 20))
        outdir="$ROOT/${RESULTS_DIR:-results}"
        mkdir -p "$outdir/logs"
        # Chốt chặn cứng: HiGHS đôi khi không kiểm tra time limit khi đang presolve hoặc giải LP gốc
        # của mô hình lớn (đã gặp: chạy 9905 s dù giới hạn 3600 s). Mỗi instance chạy trong một
        # tiến trình riêng; quá HARD_LIMIT giây thì bị dừng và được ghi là "Killed".
        tl="${TIME_LIMIT:-$([[ $step == 6 ]] && echo 1800 || echo 3600)}"
        hard="${HARD_LIMIT:-$(( ${tl%.*} * 2 + 3600 ))}"
        for id in "${ids[@]}"; do
            nm="$(printf 'setA-%02d' "$((10#$id))")"
            pending="$outdir/step${step}-${nm}.pending"     # mỗi instance một file, chạy song song không đè nhau
            t0=$SECONDS
            set +e
            HARD_LIMIT="$hard" timeout -s KILL "$hard" "${J[@]}" src/run_experiments.jl "$step" "$id" 2>&1 | tee -a "$outdir/logs/${cmd}.log"
            code=${PIPESTATUS[0]}
            set -e
            el=$(( SECONDS - t0 ))
            # Mức RAM cao nhất của container (cgroup memory.peak), ghi cả khi julia bị dừng.
            # Chỉ có ý nghĩa khi chạy trong Docker với một instance mỗi container (memory.peak tính từ lúc container khởi động).
            if [[ -f /.dockerenv && -r /sys/fs/cgroup/memory.peak ]]; then
                memcsv="$outdir/memory_step${step}.csv"
                [[ -f "$memcsv" ]] || echo "instance,seed,exit_code,elapsed_s,peak_bytes" > "$memcsv"
                echo "$nm,${SEED_START:-0},$code,$el,$(cat /sys/fs/cgroup/memory.peak)" >> "$memcsv"
            fi
            # cột CSV: instance,n,m,D,nvars,mlu_nowp,runs,status,obj,lb,gap,cpu_mean,cpu_std,nodes_mean,build_s,opt_mean
            # Lưu ý: "timeout -s KILL" trả về 137 (không phải 124) khi dừng julia, giống hệt khi hệ điều hành
            # dừng julia vì hết RAM. Vì vậy phân biệt hai trường hợp bằng thời gian đã chạy.
            if [[ ( $code -eq 124 || $code -eq 137 ) && $el -ge $(( hard - 5 )) && -f "$pending" ]]; then
                # Quá HARD_LIMIT. obj = MLU không waypoint: nghiệm khởi đầu luôn khả thi, nên là nghiệm tốt nhất chắc chắn có.
                nowp="$(cut -d, -f6 "$pending")"
                echo "$(cat "$pending"),1,Killed,$nowp,,,$hard,0,,," >> "$outdir/step${step}.csv"
                rm -f "$pending"
                echo ">>> $nm: vượt HARD_LIMIT = $hard s, đã dừng và ghi 'Killed' vào CSV" | tee -a "$outdir/logs/${cmd}.log"
            elif [[ $code -eq 137 && -f "$pending" ]]; then
                # Bị hệ điều hành dừng (SIGKILL) trước HARD_LIMIT: gần như chắc chắn là HẾT RAM
                echo "$(cat "$pending"),0,Out of memory,,,,,,,," >> "$outdir/step${step}.csv"
                rm -f "$pending"
                echo ">>> $nm: bị hệ điều hành dừng sau $el s (hết RAM). Giảm MAX_VARS hoặc dùng máy nhiều RAM hơn." | tee -a "$outdir/logs/${cmd}.log"
            elif [[ $code -ne 0 ]]; then
                echo ">>> $nm: julia kết thúc với mã lỗi $code (xem log). Chuyển sang instance tiếp theo." | tee -a "$outdir/logs/${cmd}.log"
            fi
        done ;;
    all)
        "$0" step6 all && "$0" step9 all ;;
    cg6|cg9)
        [[ $# -ge 1 ]] || { echo "Thiếu danh sách instance. Ví dụ: scripts/run.sh $cmd 1 2 3  hoặc  $cmd all" >&2; exit 1; }
        mkdir -p "$ROOT/${RESULTS_DIR:-results}/cg"
        "${J[@]}" -t "${THREADS:-8}" src/run_cg.jl "${cmd#cg}" "$@" 2>&1 | tee -a "$ROOT/${RESULTS_DIR:-results}/cg/${cmd}.log" ;;
    status)
        for f in "${RESULTS_DIR:-results}/step6.csv" "${RESULTS_DIR:-results}/step9.csv"; do
            [[ -f "$f" ]] || { echo "($f chưa có)"; continue; }
            echo "== $f"
            column -s, -t < <(cut -d, -f1,2,4,6,7,8,9,11,12,14 "$f") 2>/dev/null || cat "$f"
        done ;;
    tables)
        "${J[@]}" src/make_tables.jl ;;
    report)
        "${J[@]}" src/make_tables.jl
        command -v pdflatex >/dev/null || { echo "Không có pdflatex. Dùng Overleaf hoặc image Docker bản report (xem README)." >&2; exit 1; }
        mkdir -p report/build
        (cd report && for i in 1 2; do pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build report.tex >/dev/null; done)
        echo "Đã tạo report/build/report.pdf" ;;
    pluto)
        echo "Mở trình duyệt tại http://localhost:1234 rồi chọn file json_to_graph_pluto_v2.jl hoặc json_to_multigraph_pluto.jl"
        "${J[@]}" -e 'using Pluto; Pluto.run(host="0.0.0.0", port=1234, launch_browser=false, require_secret_for_access=false)' ;;
    help|-h|--help)
        usage ;;
    *)
        echo "Lệnh không hợp lệ: $cmd" >&2; usage; exit 1 ;;
esac
