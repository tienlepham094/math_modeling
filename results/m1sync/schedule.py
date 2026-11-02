#!/usr/bin/env python3
"""Phương pháp 1 (MILP đầy đủ) trên máy B: chạy mọi lượt của Bảng III, IV, V của báo cáo, kèm kiểm tra nghiệm
(checks_step*.csv), nghiệm (srpaths.json), RAM cao nhất (memory_step*.csv) và thời gian của cả lệnh optimize! (cột opt_mean).

    python3 results/m1sync/schedule.py --dry-run                     # xem kế hoạch, không chạy gì
    nohup python3 results/m1sync/schedule.py --out results/m1opt --start "2026-10-29 11:00" --deadline "2026-10-30 01:00" \\
          > results/m1opt/logs/schedule.out 2>&1 &

Lịch sử: ngày 28/10 chạy với --out results/m1sync (code khi đó chưa ghi opt_mean); ngày 29/10 chạy lại với
--out results/m1opt để có thời gian của cả lệnh optimize! như đề yêu cầu.

Quy tắc (theo báo cáo): mô hình gốc; time limit 1800 s (Step 6) / 3600 s (Step 9); chốt chặn TL + 900 s; mỗi lần chạy là một
tiến trình (SEED_START=k, MAX_RUNS=1); instance < 1e6 biến chạy 10 seed, lớn hơn chạy 1 seed.
Điều phối: thứ tự từ instance lớn đến bé (theo số biến); một lượt chỉ được khởi động khi RAM trống đủ cho ước tính của nó
(3.7 GB/triệu biến cho Step 6, 3.4 GB cho Step 9, theo số đo ngày 28/10), nếu không thì tạm bỏ qua và thử lại sau;
mỗi container bị giới hạn RAM (--memory) để không ảnh hưởng người dùng khác; không khởi động lượt nào có thể không xong
trước giờ dừng (deadline, giờ UTC). Lượt đã có kết quả trong CSV được bỏ qua, nên có thể chạy lại script để chạy tiếp.
"""
import argparse, csv, datetime as dt, json, math, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = "results/m1opt"                       # tương đối so với ROOT (= /app trong container); đổi bằng --out
LOGS = os.path.join(ROOT, OUT, "logs")
UID = f"{os.getuid()}:{os.getgid()}"

def size(inst):
    p = os.path.join(ROOT, "setA", inst)
    n = len(json.load(open(p + "-net.json"))["nodes"])
    D = len(json.load(open(p + "-tm.json"))["demands"])
    return n, D

def tasks():
    """(nhãn, lệnh, instance id, seed, env thêm, thư mục kết quả, số biến, GB ước tính, chốt chặn)"""
    T = []
    def add(kind, step, k, seeds, hard9=4500):
        n, D = size(f"setA-{k:02d}")
        pairs = D * n * (n - 1)
        if kind == "period1":
            nvars, gb_per_m, hard, env, sub, cmd = pairs, 3.7, 4500, {"PERIOD1_ONLY": "1", "NO_LOOPS": "0"}, "period1", "step9"
        elif kind == "noloop":
            nvars, gb_per_m, hard, env, sub, cmd = pairs, 3.7, 2700, {"NO_LOOPS": "1"}, "noloop", "step6"
        elif step == 6:
            nvars, gb_per_m, hard, env, sub, cmd = pairs, 3.7, 2700, {"NO_LOOPS": "0"}, "main", "step6"
        else:
            nvars, gb_per_m, hard, env, sub, cmd = 3 * pairs, 3.4, hard9, {"NO_LOOPS": "0"}, "main", "step9"
        for s in seeds:
            T.append(dict(label=f"{kind}-s{step}-{k:02d}-seed{s}", cmd=cmd, k=k, seed=s, env=env,
                          rdir=f"{OUT}/{sub}/seed{s}", nvars=nvars, gb=nvars * gb_per_m / 1e6 + 1.5, hard=hard))
    ten = range(10)
    # lớn (1 seed)
    for k in (9, 8, 5): add("main", 9, k, [0])
    add("main", 9, 6, [0], hard9=5400)       # mô hình lớn nhất được chạy (1.5e7 biến): thêm thời gian dựng và chép mô hình
    for k in (7, 6, 9, 8): add("main", 6, k, [0])
    add("main", 9, 4, [0])
    # nhỏ (10 seed; no-loop: 10 seed cho 01–03, 1 seed cho 04, 05 như bảng V; chu kỳ 1 riêng: seed 0)
    add("main", 6, 5, ten); add("noloop", 6, 5, [0])
    add("main", 6, 4, ten); add("noloop", 6, 4, [0])
    add("main", 9, 3, ten); add("period1", 9, 3, [0])
    add("main", 9, 2, ten); add("period1", 9, 2, [0])
    add("main", 6, 3, ten); add("noloop", 6, 3, ten)
    add("main", 9, 1, ten); add("period1", 9, 1, [0])
    add("main", 6, 2, ten); add("noloop", 6, 2, ten)
    add("main", 6, 1, ten); add("noloop", 6, 1, ten)
    T.sort(key=lambda t: -t["nvars"])          # từ lớn đến bé; Python sort ổn định nên giữ thứ tự seed
    return T

def done(t):
    f = os.path.join(ROOT, t["rdir"], "step6.csv" if t["cmd"] == "step6" else "step9.csv")
    if not os.path.exists(f):
        return False
    return any(r["instance"] == f"setA-{t['k']:02d}" for r in csv.DictReader(open(f)))

def mem_available_gb():
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024**2
    return 0.0

def container_usage_gb():
    out = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}} {{.MemUsage}}"],
                         capture_output=True, text=True).stdout
    use = {}
    for line in out.splitlines():
        m = re.match(r"(\S+) ([\d.]+)([KMG]i?B)", line)
        if m:
            v = float(m.group(2)); u = m.group(3)[0]
            use[m.group(1)] = v / 1024**2 if u == "K" else v / 1024 if u == "M" else v
    return use

def name_of(t):
    return "m1o_" + t["label"].replace("-", "_")

def launch(t):
    os.makedirs(os.path.join(ROOT, t["rdir"]), exist_ok=True)
    limit = math.ceil(t["gb"] * 1.2 + 2)
    env = {"RESULTS_DIR": t["rdir"], "SEED_START": str(t["seed"]), "MAX_RUNS": "1", "MAX_VARS": "20000000",
           "HARD_LIMIT": str(t["hard"]), **t["env"]}
    cmd = ["docker", "run", "--rm", "--name", name_of(t), "--user", UID, f"--memory={limit}g",
           "-v", f"{ROOT}/results:/app/results"]
    for k, v in env.items():
        cmd += ["-e", f"{k}={v}"]
    cmd += ["orange-tasr", t["cmd"], str(t["k"])]
    log = open(os.path.join(LOGS, t["label"] + ".out"), "a")
    return subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)

def say(msg):
    print(f"[{dt.datetime.now(dt.timezone.utc):%F %T} UTC] {msg}", flush=True)

def main():
    global OUT, LOGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=None, help="giờ bắt đầu (UTC), vd. '2026-10-28 11:00'")
    ap.add_argument("--deadline", default=None, help="giờ dừng (UTC), vd. '2026-10-29 01:00'")
    ap.add_argument("--max-parallel", type=int, default=7)
    ap.add_argument("--margin-gb", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=OUT, help="thư mục kết quả, tương đối so với thư mục project (mặc định results/m1opt)")
    a = ap.parse_args()
    OUT = a.out.rstrip("/")
    LOGS = os.path.join(ROOT, OUT, "logs")
    T = tasks()
    if a.dry_run:
        tot = 0
        for t in T:
            print(f"{t['label']:28s} {t['cmd']} nvars={t['nvars']:>11,} RAM≈{t['gb']:5.1f} GB (giới hạn {math.ceil(t['gb']*1.2+2)} GB) "
                  f"chốt chặn {t['hard']} s {'(đã xong)' if done(t) else ''}")
            tot += 1
        print(f"Tổng {tot} lượt; RAM trống hiện tại {mem_available_gb():.1f} GB")
        return
    os.makedirs(LOGS, exist_ok=True)
    parse = lambda s: dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
    if a.start:
        st = parse(a.start)
        say(f"chờ tới {st:%F %H:%M} UTC")
        while dt.datetime.now(dt.timezone.utc) < st:
            time.sleep(30)
    deadline = parse(a.deadline) if a.deadline else None
    pending = [t for t in T if not done(t)]
    say(f"bắt đầu: {len(pending)} lượt cần chạy, {len(T) - len(pending)} lượt đã có")
    running = {}                                  # tên container -> (task, Popen)
    while pending or running:
        for nm, (t, p) in list(running.items()):
            if p.poll() is not None:
                say(f"xong {t['label']} (mã {p.returncode})")
                del running[nm]
        now = dt.datetime.now(dt.timezone.utc)
        if deadline and now >= deadline:
            say("tới giờ dừng; không khởi động thêm lượt nào")
            break
        use = container_usage_gb() if running else {}
        reserve = sum(max(0.0, t["gb"] - use.get(nm, 0.0)) for nm, (t, _) in running.items())
        free = mem_available_gb() - reserve - a.margin_gb
        started = False
        for t in list(pending):
            if len(running) >= a.max_parallel:
                break
            if deadline and now + dt.timedelta(seconds=t["hard"] + 120) > deadline:
                continue                          # có thể không xong trước giờ dừng
            if t["gb"] <= free:
                p = launch(t)
                running[name_of(t)] = (t, p)
                pending.remove(t)
                free -= t["gb"]
                say(f"chạy {t['label']} (RAM ước tính {t['gb']:.1f} GB; trống còn {free:.1f} GB; đang chạy {len(running)})")
                started = True
                time.sleep(5)
        if not started and not running and pending:
            if deadline and all(now + dt.timedelta(seconds=t["hard"] + 120) > deadline for t in pending):
                say(f"không còn lượt nào kịp xong trước giờ dừng; bỏ {len(pending)} lượt: " + ", ".join(t["label"] for t in pending))
                break
        time.sleep(20)
    say(f"kết thúc; còn {len(pending)} lượt chưa chạy: " + ", ".join(t["label"] for t in pending))

if __name__ == "__main__":
    main()
