# syntax=docker/dockerfile:1
# =====================================================================
# Image Docker cho project Orange T-ASR: Julia + JuMP + HiGHS + dữ liệu SetA.
#
#   docker build -t orange-tasr .                      # image chạy thí nghiệm (mặc định)
#   docker build -t orange-tasr-report --target report .   # thêm LaTeX để biên dịch báo cáo
#
#   docker run --rm orange-tasr test                   # kiểm tra trên toy
#   docker run --rm -v "$PWD/results:/app/results" orange-tasr step6 1 2 3
#
# Chi tiết: docs/CAI_DAT_VA_CHAY.md
# =====================================================================
ARG JULIA_VERSION=1.13.2

# ---------- Giai đoạn chung: Julia + thư viện + code + dữ liệu ----------
FROM julia:${JULIA_VERSION} AS base

# Thư viện Julia được cài vào /opt/julia-depot ngay lúc build (không cần mạng khi chạy).
# JULIA_NUM_PRECOMPILE_TASKS: số thư viện biên dịch song song. Để mặc định (= số nhân CPU)
# thì bước build có thể cần trên 3 GB RAM và bị dừng trên máy ít RAM; 2 là đủ an toàn.
ARG PRECOMPILE_TASKS=2
ENV JULIA_DEPOT_PATH=/opt/julia-depot \
    JULIA_NUM_PRECOMPILE_TASKS=${PRECOMPILE_TASKS} \
    JULIA_PKG_SERVER_REGISTRY_PREFERENCE=eager
WORKDIR /app

# Chép Project.toml + Manifest.toml trước để Docker cache bước cài thư viện
COPY Project.toml Manifest.toml ./
RUN julia --project=/app -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()' \
 && chmod -R a+rX /opt/julia-depot

# Code, script, dữ liệu, báo cáo, notebook của giảng viên
COPY src ./src
COPY scripts ./scripts
COPY setA ./setA
COPY toy ./toy
COPY report ./report
COPY json_to_graph_pluto_v2.jl json_to_multigraph_pluto.jl ./

# Khi chạy: thư mục ghi được nằm đầu (/tmp), thư viện đã cài nằm sau (chỉ đọc).
# Nhờ vậy container chạy được cả với --user $(id -u):$(id -g).
ENV JULIA_DEPOT_PATH=/tmp/julia-depot:/opt/julia-depot
RUN chmod +x scripts/run.sh \
 && mkdir -p results report/build \
 && chmod a+rwx results report report/build

EXPOSE 1234
ENTRYPOINT ["/app/scripts/run.sh"]
CMD ["help"]

# ---------- Bản có LaTeX (tuỳ chọn): docker build --target report ----------
FROM base AS report
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra \
      texlive-fonts-recommended texlive-lang-other lmodern \
 && rm -rf /var/lib/apt/lists/*

# ---------- Bản mặc định (không có LaTeX, nhẹ hơn) ----------
FROM base AS app
# Kiểm tra ngay lúc build: nếu toy không đạt thì build thất bại.
# Xoá depot tạm do lần test tạo ra (thuộc root), để user khác tự tạo khi chạy.
RUN scripts/run.sh test && rm -rf /tmp/julia-depot
