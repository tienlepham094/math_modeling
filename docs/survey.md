# Survey: các hướng giải quyết bài toán T-ASR và Segment Routing Traffic Engineering

Tài liệu này tổng hợp các hướng tiếp cận đã có trong tài liệu khoa học cho bài toán **T-Adaptive Segment Routing (T-ASR)** của ROADEF/EURO Challenge 2026 và bài toán gốc **Segment Routing Traffic Engineering (SR-TE)**. Mỗi mục ghi rõ ý tưởng chính, liên hệ với project này và link tới paper.

> Hai paper chính về T-ASR (mục 2) **đã được đọc bản đầy đủ** ngày 21/10/2026. Các paper khác được mô tả dựa trên abstract và trang công bố; chi tiết đánh dấu *(chưa đọc full text)* cần kiểm tra lại trong bản PDF trước khi trích dẫn.

**Mục lục**

1. [Bài toán T-ASR và challenge](#1-bài-toán-t-asr-và-challenge)
2. [Paper trực tiếp về T-ASR (2026)](#2-paper-trực-tiếp-về-t-asr-2026)
3. [Mô hình chính xác: MILP / ILP](#3-mô-hình-chính-xác-milp--ilp)
4. [Column generation](#4-column-generation)
5. [Heuristic và local search](#5-heuristic-và-local-search)
6. [Giới hạn số segment, thuật toán xấp xỉ và online](#6-giới-hạn-số-segment-thuật-toán-xấp-xỉ-và-online)
7. [Kết hợp tối ưu trọng số IGP và segment](#7-kết-hợp-tối-ưu-trọng-số-igp-và-segment)
8. [Nền tảng: tối ưu trọng số OSPF/IS-IS và ECMP](#8-nền-tảng-tối-ưu-trọng-số-ospfis-is-và-ecmp)
9. [Survey và luận án tổng quan](#9-survey-và-luận-án-tổng-quan)
10. [Bảng so sánh nhanh](#10-bảng-so-sánh-nhanh)
11. [Gợi ý áp dụng cho project](#11-gợi-ý-áp-dụng-cho-project)

---

## 1. Bài toán T-ASR và challenge

- **ROADEF/EURO Challenge 2026 "Keep the Flow!"**, đề bài do Orange Research đề xuất. Ban tổ chức cung cấp đề bài, dataset Set A (sprint), sau đó Set B (qualification), một **solution checker C++20** và thư viện **Networktools** (header-only C++20 cho tối ưu mạng).
  - Trang chính: <https://roadef.org/challenge/>
  - Luật nộp bài sprint: <https://roadef.org/challenge/2026/en/sprint.php>
  - Thông báo trên EURO: <https://www.euro-online.org/bb/topic/34833>
  - Trang EURO về challenge: <https://euro-online.org/web/pages/1707/roadefeuro-challenge>

- **Liên hệ project.** Đề trong `Challenge_Orange_ROADEF_2026_Subject.pdf` dùng mục tiêu lex-min trên vector tải. Project này chỉ dùng thành phần đầu tiên là MLU (báo cáo mục 2.4). Checker và Networktools có thể dùng để kiểm tra nghiệm của mô hình Julia.

## 2. Paper trực tiếp về T-ASR (2026)

Đây là hai nguồn gần nhất với project và nên đọc đầu tiên.

### 2.1 Benhamiche et al., *On the T-Adaptive Segment Routing Problem* (arXiv 2609.32896, 09/2026), đã đọc bản đầy đủ

- **Tác giả:** A. Benhamiche, K. Bouaachra, Y. Carlinet, M. Chopin, E. Gourdin, N. Perrot (nhóm ra đề challenge).
- **Link:** <https://arxiv.org/abs/2609.32896>
- **Nội dung chính:**
  - Mô hình (1)–(4) trong paper **trùng hoàn toàn** với đề, và với mô hình của project.
  - **Độ phức tạp:** T-ASR tổng quát hoá MIN SEGMENT ROUTING, nên NP-khó và khó xấp xỉ, ngay cả trên topology đơn giản (dẫn Bazgan et al., INFOCOM 2025).
  - **Mục tiêu lexicographic** được giải bằng chuỗi MILP, mỗi MILP tối ưu một hạng của vector tải:
    - **ALEXA**: ma trận hoán vị kèm big-M.
    - **STELA**: ràng buộc "vượt ngưỡng", λ↓_k = min{z : số tải vượt z ≤ k−1}. STELA tốt hơn ALEXA ở 109/115 instance.
    - Bước đầu tiên của cả hai chính là **min MLU**, đúng như project.
  - **Vòng lặp trong segment path có thể bắt buộc** khi có budget (Fig. 1 của paper). Vì vậy tiền xử lý loại path bị trội của Callebaut et al. 2023 không áp dụng được cho bài toán nhiều chu kỳ.
  - **Thí nghiệm:** tập setAP (10–50 nút, 10–50 demand), Gurobi 13, giới hạn 20 phút. Quy mô này nhỏ hơn SetA nhiều.
- **Tài nguyên công khai:**
  - Instance: <https://doi.org/10.5281/zenodo.19219524>
  - Code STELA/ALEXA (Python + Gurobi): <https://github.com/kaoutarbouaachra/T-ASR-STELA-ALEXA-DRCN>
  - Thư viện networktools: <https://gitlab.com/Orange-OpenSource/network-optimization-tools/networktools>
- **Liên hệ project:** nguồn chính thức cho mô hình (báo cáo mục 2) và cho lập luận "min MLU là bước đầu của lex-min".

### 2.2 Jaumard, Tran, Ziazet, *Segment Routing Traffic Engineering with Time-Based Reconfiguration Constraints* (arXiv 2610.04759, 10/2026), đã đọc bản đầy đủ

- **Link:** <https://arxiv.org/abs/2610.04759>
- **Nội dung chính:**
  - Mục tiêu **MLU** và budget thay đổi giữa hai chu kỳ, đúng như project.
  - **Giải tuần tự theo chu kỳ:** tối ưu chu kỳ t, coi routing tại t−1 là cố định. Nhờ vậy budget thành một ràng buộc tuyến tính mà không cần biến y.
  - **Column generation:**
    - Master chọn một cấu hình (segment path) cho mỗi demand.
    - Pricing tìm đường đi có tối đa maxSeg cung trên đồ thị segment `K_t` (chính là đồ thị `H` trong [GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), mục 8.1).
    - Sau đó giải ILP trên tập cột cuối (price-and-branch).
  - **Chạy trên chính SetA** (và một phần SetB). Kết quả trên SetA, đo bằng gap LP–ILP:
    - t = 0: 85% trường hợp có gap ≤ 1%, gap trung bình 3.12%.
    - t = 1: 45% trường hợp có gap ≤ 1%, gap trung bình 13.05%.
    - Số cột sinh ra: 6.9 nghìn – 2.4 triệu.
- **Liên hệ project:** cho thấy **t = 1 khó hơn t = 0** vì budget, và là hướng mở rộng chính cho các instance mà MILP đầy đủ không dựng được. Lưu ý gap của họ là gap LP–ILP trên tập cột, không phải gap MILP.

## 3. Mô hình chính xác: MILP / ILP

- **Ý tưởng chung:**
  - Biến nhị phân chọn segment path (hoặc chọn cung trong đồ thị segment `H`).
  - Hệ số `r(i,j,a)` tính trước từ ECMP nên tải là hàm tuyến tính của biến.
  - Cực tiểu `U` với `λ(a,t) ≤ U`.
- **Ưu điểm:** cho nghiệm tối ưu và bound, lấy được gap và số nút B&B như yêu cầu báo cáo.
- **Nhược điểm:** số biến khoảng `|D| × |V|²` (mỗi demand × mỗi segment), và mỗi ràng buộc tải có tới `|D| × |V|²` hệ số. Với SetA-20 (400 nút, 6000 demand) mô hình rất lớn.
- **Tài liệu:**
  - Hartert et al., *A Declarative and Expressive Approach to Control Forwarding Paths in Carrier-Grade Networks* (DEFO), SIGCOMM 2015. Một trong các paper đầu tiên về tối ưu SR, đề xuất bộ tối ưu tập trung DEFO, tối ưu mạng ISP lớn trong vài giây. PDF: <https://inl.info.ucl.ac.be/system/files/DEFO_sigcomm15_final.pdf>
  - Schüller, Aschenbruck, Chimani, Horneffer, Schnitter, *Traffic Engineering Using Segment Routing and Considering Requirements of a Carrier IP Network*, IEEE/ACM ToN 26(4), 2018. Mô hình LP/ILP cho SR với yêu cầu của mạng ISP tier-1 *(chưa đọc full text)*. DBLP: <https://dblp.org/pid/209/2400.html>
  - Benhamiche et al. (mục 2.1): hai MILP ALEXA và STELA.

## 4. Column generation

- **Ý tưởng:**
  - Master problem là LP chọn tổ hợp segment path cho mỗi demand.
  - Pricing problem tìm segment path có reduced cost âm. Với giới hạn `maxSeg` segment, pricing là bài toán đường đi ngắn nhất có giới hạn số cung trên `H`, giải bằng quy hoạch động (kiểu Bellman–Ford `maxSeg` bước).
  - Lower bound từ LP master chặt hơn relaxation multi-commodity flow.
- **Tài liệu:**
  - Jadin, Aubry, Schaus, Bonaventure, *CG4SR: Near Optimal Traffic Engineering for Segment Routing with Column Generation*, IEEE INFOCOM 2019. PDF: <https://inl.info.ucl.ac.be/system/files/cg4sr.pdf> — trang: <https://research.dial.uclouvain.be/handle/2078.5/256488>
  - Jaumard et al. 2026 (mục 2.2): mở rộng column generation cho nhiều chu kỳ có budget.
- **Liên hệ project:** pricing DP chính là bài toán "chọn đường trong `H` với tối đa `maxSeg` cung" ([GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), mục 8.1). Có thể dùng để sinh tập path ứng viên rồi giải MILP trên tập đó (price-and-branch) nếu MILP đầy đủ quá lớn.

## 5. Heuristic và local search

- **Ý tưởng:** xuất phát từ routing ECMP mặc định (không waypoint). Lặp lại: tìm link có tải cao nhất, chọn demand đi qua link đó, thử đổi waypoint để giảm tải. Chỉ thay đổi ít demand nên hợp với budget `κ(t)`.
- **Tài liệu:**
  - Gay, Hartert, Vissicchio, *Expect the Unexpected: Sub-Second Optimization for Segment Routing*, IEEE INFOCOM 2017. Local search tối ưu lại SR trong dưới 1 giây trên mạng ISP lớn, chỉ thay đổi ít path. Trang: <https://research.google/pubs/pub47610/>
  - Hartert, *Fast and Scalable Optimization for Segment Routing*, luận án UCLouvain 2018 (MIP, local search, constraint programming). Trang: <https://inl.info.ucl.ac.be/publications/historical/2018-fast-optimization-sr.html>
  - Code Go của thuật toán Link-Guided Local Search (SRTE-LS): <https://beta.pkg.go.dev/github.com/rhartert/srte-ls>
- **Liên hệ project:** dùng để tạo **nghiệm khởi đầu (warm start)** cho MILP, giúp solver có UB tốt sớm trên instance lớn trong giới hạn 1800 s / 3600 s.

## 6. Giới hạn số segment, thuật toán xấp xỉ và online

- Bhatia, Hao, Kodialam, Lakshman, *Optimized Network Traffic Engineering using Segment Routing*, IEEE INFOCOM 2015, tr. 657–665.
  - Thuật toán offline không phụ thuộc traffic matrix và thuật toán online có tỉ số cạnh tranh.
  - Kết luận chính: **path 2 segment (1 waypoint) gần như đủ** để cân bằng tải.
  - Trang: <https://www.nokia.com/bell-labs/publications-and-media/publications/optimized-network-traffic-engineering-using-segment-routing>
- Zhang, *Q-SR: An Extensible Optimization Framework for Segment Routing*, arXiv 2020. FPTAS cho bài toán offline và thuật toán primal-dual cho online. <https://arxiv.org/abs/2012.13171>
- **Liên hệ project:** thử giới hạn tạm `maxSeg = 2` để có mô hình nhỏ hơn nhiều, dùng làm nghiệm khởi đầu hoặc để so sánh chất lượng với `maxSeg` đầy đủ trong báo cáo.

## 7. Kết hợp tối ưu trọng số IGP và segment

- Parham, Fenz, Süss, Foerster, Schmid, *Traffic Engineering with Joint Link Weight and Segment Optimization*, ACM CoNEXT 2021, tr. 313–327. Phân tích lợi ích khi tối ưu đồng thời trọng số link và waypoint. DOI: <https://doi.org/10.1145/3485983.3494846> — bản mở: <https://eprints.cs.univie.ac.at/7099>
- **Liên hệ project:** trong T-ASR trọng số `ω` cố định, nên đây chỉ là tài liệu tham khảo cho phần bối cảnh.

## 8. Nền tảng: tối ưu trọng số OSPF/IS-IS và ECMP

- Fortz, Thorup, *Internet Traffic Engineering by Optimizing OSPF Weights*, IEEE INFOCOM 2000, tr. 519–528. Paper kinh điển về TE bằng shortest path + ECMP, chứng minh NP-khó và đề xuất local search.
- Fortz, Rexford, Thorup, *Traffic Engineering with Traditional IP Routing Protocols*, IEEE Communications Magazine 2002. PDF: <https://www.cs.princeton.edu/~jrex/papers/ieeecomm02.pdf>
- **Liên hệ project:** nguồn trích dẫn cho cách chia luồng ECMP và cách tính `r` ([GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md)), dùng trong phần Introduction của báo cáo.

## 9. Survey và luận án tổng quan

- Ventre et al., *Segment Routing: A Comprehensive Survey of Research Activities, Standardization Efforts and Implementation Results*, IEEE Communications Surveys & Tutorials 23(1), 2021. <https://arxiv.org/abs/1904.03471>
- Kushwaha, Sharma, Gumaste, *A Survey on Segment Routing with Emphasis on Use Cases in Large Provider Networks*, arXiv 2020. <https://arxiv.org/abs/2012.14687>
- Wu, Cui, *A comprehensive survey on Segment Routing Traffic Engineering*, Digital Communications and Networks, 2023 (survey riêng về SR-TE). <https://doaj.org/article/ac1b6652123b47c9b627b252f2fb16ec>
- Aubry, *Models and Algorithms for Network Optimization with Segment Routing*, luận án UCLouvain 2020. Hình thức hoá toán học SR và các bài toán TE. PDF: <https://inl.info.ucl.ac.be/system/files/thesis-aubry.pdf>

## 10. Bảng so sánh nhanh

| Hướng | Tối ưu? | Có bound/gap? | Đa chu kỳ + budget? | Quy mô | Paper tiêu biểu |
| --- | --- | --- | --- | --- | --- |
| MILP trực tiếp | Có (nếu kịp thời gian) | Có | Có (ràng buộc 4) | Nhỏ – vừa | Benhamiche 2026, Schüller 2018 |
| Phân rã theo chu kỳ + MILP | Không toàn cục | Có cho từng bài toán con | Có | Vừa | Benhamiche 2026 (ALEXA, STELA) |
| Column generation | Gần tối ưu | Có (LP bound) | Có | Lớn | CG4SR 2019, Jaumard 2026 |
| Local search | Không | Không | Phù hợp (ít thay đổi) | Rất lớn, nhanh | Gay 2017, Hartert 2018 |
| Giới hạn 2 segment | Không | Có trên mô hình con | Có | Lớn | Bhatia 2015 |

## 11. Gợi ý áp dụng cho project

Đề yêu cầu cài **mô hình MILP** và báo cáo CPU time, gap, số nút B&B (Step 5–9). Vì vậy hướng chính vẫn là MILP ([GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md), Phần 8). Các hướng khác dùng để hỗ trợ:

1. **Bắt buộc:** MILP trên đồ thị segment `H` ([GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md)). So sánh công thức với ALEXA/STELA của Benhamiche et al. để viết phần Mathematical model.
2. **Giảm kích thước mô hình:**
   - Chỉ tạo biến cho segment có đường đi ([GIAI_THICH_TU_DAU.md](GIAI_THICH_TU_DAU.md)).
   - Bỏ hệ số `r` bằng 0 khi xây ràng buộc tải.
   - Thử giới hạn `maxSeg = 2` (Bhatia 2015) như một biến thể, để so sánh trong báo cáo.
3. **Warm start:** dùng nghiệm ECMP mặc định (không waypoint) hoặc một local search đơn giản (Gay 2017) làm nghiệm khởi đầu cho solver.
4. **Nếu instance lớn không giải được trong 1800/3600 s:** ghi gap theo yêu cầu đề. Nhắc column generation (CG4SR, Jaumard 2026) trong phần thảo luận như hướng mở rộng.
5. **Trích dẫn trong Introduction:** Fortz & Thorup 2000 (ECMP/OSPF), Ventre 2021 (SR), Benhamiche 2026 (T-ASR), trang ROADEF challenge.

## 12. Tài liệu bổ sung (tìm thấy khi đọc hai paper 2026)

| Tài liệu | Vì sao cần |
|---|---|
| Callebaut, De Boeck, Fortz, *Preprocessing for segment routing optimization*, Networks 82(4):459–478, 2023 | Loại segment path bị trội, thu nhỏ MILP **một chu kỳ** (Step 5–6). Không áp dụng được cho nhiều chu kỳ (Benhamiche 2026). |
| Bazgan, Chopin, Nichterlein, Richer, *Parameterized complexity of segment routing*, IEEE INFOCOM 2025 | Kết quả về độ khó, dùng trong Introduction |
| Schüller, Aschenbruck, Chimani, Horneffer, *Failure resiliency with only a few tunnels: enabling segment routing for traffic engineering*, IEEE/ACM ToN 29(1):262–274, 2021 | MILP min-MLU có tính đến hỏng link, gần với t = 1 |
| Li, Yeung, *Traffic engineering in segment routing networks using MILP*, IEEE TNSM 17(3):1941–1953, 2020 | Một công thức MILP cho SR-TE để so sánh |
| Pereira, Rocha, Sousa, *Traffic engineering with three-segments routing*, IEEE TNSM 17(3):1896–1909, 2020 | Heuristic cho path 3 segment, có xử lý hỏng link |
| Filsfils et al., *Segment Routing Architecture*, RFC 8402, 2018 | Định nghĩa chuẩn của Segment Routing (đề trích dẫn) |
