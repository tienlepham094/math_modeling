#!/usr/bin/env bash
# Dừng mọi job của project lúc 01:00 UTC (= 8:00 sáng giờ Việt Nam) để trả RAM cho người dùng khác.
# Cách dùng: results/pause_at_8h_vn.sh '2026-10-29 01:00:00'   (giờ UTC; mặc định: 01:00 UTC kế tiếp)
# Thứ tự: dừng các script điều phối và xargs (để không mở container mới), rồi xoá container (docker pause không trả RAM).
# Các script đều bỏ qua instance/seed đã xong, nên có thể chạy tiếp sau.
target=$(date -u -d "${1:-$( [[ $(date -u +%H) -lt 1 ]] && date -u +%F || date -u -d tomorrow +%F ) 01:00:00}" +%s)
echo "[$(date -u '+%F %T') UTC] sẽ dừng lúc $(date -u -d @$target '+%F %T') UTC"
while (( $(date -u +%s) < target )); do sleep 30; done
echo "[$(date -u '+%F %T') UTC] dừng các job của project"
for i in 1 2 3; do
    for p in $(ps -eo pid=,args= | awk '(($0 ~ /bash results\/.*\.sh$/ || $0 ~ /python3 (-I )?results\/.*schedule\.py/) && $0 !~ /pause_at_8h_vn/) || $0 ~ /xargs -P [0-9]+ -L 1 bash -c job/ {print $1}'); do
        kill "$p" 2>/dev/null
    done
    docker ps --format '{{.Names}}' | grep -E '^(cg_|m1)' | xargs -r docker rm -f > /dev/null
    sleep 5
done
echo "[$(date -u '+%F %T') UTC] xong; container còn: $(docker ps --format '{{.Names}}' | grep -cE '^(cg_|m1)'); RAM trống: $(free -g | awk '/Mem/ {print $7}') GB"
