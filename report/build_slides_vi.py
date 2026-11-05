"""Bản tiếng Việt của slide Orange T-ASR.  usage: build_slides_vi.py template.pptx figdir out.pptx

template.pptx: template HUST hoặc một bản build trước (cover, title, outline, ..., thanks).
figdir: hình tạo bởi make_figures.py ROOT figdir vi. Kết quả phương pháp 2 đọc từ report/table_cg.tex."""
import copy, os, re, sys
from lxml import etree
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

SRC, FIG, OUT = sys.argv[1:4]
RED, INK, MUTED, RULE = "BC1C2F", "23272D", "6B7178", "8A9099"
FONT = "Calibri"

prs = Presentation(SRC)
slides = list(prs.slides)
cover, title_sl, outline_sl, thanks = slides[0], slides[1], slides[2], slides[-1]
layout = slides[3].slide_layout
sldIdLst = prs.slides._sldIdLst
for s in slides[3:-1]:
    for sid in list(sldIdLst):
        if prs.part.related_part(sid.rId) is s.part:
            prs.part.drop_rel(sid.rId); sldIdLst.remove(sid)

from pptx.opc.packuri import PackURI
thanks.part.partname = PackURI("/ppt/slides/slide9999.xml")  # keep new slide names free

def rgb(h): return RGBColor.from_string(h)

# **bold**, *red*, _{sub}, ^{sup}
TOKEN = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|_\{.+?\}|\^\{.+?\})")
def add_runs(p, txt, size, color=INK, bold=False, italic=False):
    for k, tok in enumerate(TOKEN.split(txt)):
        if not tok: continue
        b, c, base, t = bold, color, 0, tok
        if k % 2 == 0: pass  # plain text between markup tokens
        elif tok.startswith("**"): b, t = True, tok[2:-2]
        elif tok.startswith("*"): b, c, t = True, RED, tok[1:-1]
        elif tok.startswith("_{"): base, t = -25000, tok[2:-1]
        elif tok.startswith("^{"): base, t = 30000, tok[2:-1]
        r = p.add_run(); r.text = t
        f = r.font; f.size, f.bold, f.italic, f.name = Pt(size), b, italic, FONT
        f.color.rgb = rgb(c)
        if base: r._r.get_or_add_rPr().set("baseline", str(base))

def bullet(p, level):
    pPr = p._p.get_or_add_pPr()
    ind = [228600, 457200][level]
    pPr.set("marL", str(ind)); pPr.set("indent", str(-228600 if level == 0 else -200000))
    bc = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(bc, qn("a:srgbClr")).set("val", RED if level == 0 else MUTED)
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
    etree.SubElement(pPr, qn("a:buChar")).set("char", "•" if level == 0 else "–")

def text(slide, x, y, w, h, lines, size=16, color=INK, bold=False, align="l", anchor="t",
         italic=False, space=6, bullets=False):
    """lines: str or list. With bullets=True, a line starting with '-' is a sub-bullet."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.03); tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE}[anchor]
    for i, ln in enumerate([lines] if isinstance(lines, str) else lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        sz, c = size, color
        if bullets and ln.startswith("-"):
            ln = ln[1:].strip(); bullet(p, 1); sz, c = size - 2, MUTED
            p.space_before = Pt(2)
        elif bullets:
            bullet(p, 0); p.space_before = Pt(space if i else 0)
        elif i:
            p.space_before = Pt(space)
        if ln == "":
            ln = " "
        add_runs(p, ln, sz, c, bold, italic)
    return tb

def image(slide, name, x, y, w=None, h=None):
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return slide.shapes.add_picture(f"{FIG}/{name}", Inches(x), Inches(y), **kw)

def caption(slide, x, y, w, txt, align="c"):
    return text(slide, x, y, w, 0.3, txt, 11, MUTED, italic=True, align=align)

def footnote(slide, txt):
    return text(slide, 0.45, 4.74, 8.3, 0.25, txt, 9, MUTED)

def hline(slide, x1, y, x2, color=RULE, w=0.75):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y), Inches(x2), Inches(y))
    c.line.color.rgb = rgb(color); c.line.width = Pt(w)
    return c

def arrow(slide, x1, y1, x2, y2):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(RULE); c.line.width = Pt(1.25)
    t = etree.SubElement(c.line._get_or_add_ln(), qn("a:tailEnd")); t.set("type", "triangle")

def frame(slide, x, y, w, h, color=RULE, lw=0.75):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.background(); s.line.color.rgb = rgb(color); s.line.width = Pt(lw)
    return s

def _border(tcPr, tag, w_pt, color):
    ln = etree.SubElement(tcPr, qn(tag))
    if w_pt:
        ln.set("w", str(int(w_pt * 12700)))
        sf = etree.SubElement(ln, qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", color)
    else:
        ln.set("w", "0"); etree.SubElement(ln, qn("a:noFill"))
    return ln

def table(slide, x, y, w, rows, colw, size=13, rowh=0.32, bold_cells=(), red_rows=(), mid_after=0, align=None):
    """Booktabs style: thick top/bottom rule, thin rule under the header, no fills."""
    nr, nc = len(rows), len(rows[0])
    tbl = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(rowh * nr)).table
    tblPr = tbl._tbl.tblPr
    for ch in list(tblPr): tblPr.remove(ch)
    tblPr.attrib.clear()
    tot = sum(colw)
    for j, cw in enumerate(colw): tbl.columns[j].width = Inches(w * cw / tot)
    for i in range(nr):
        tbl.rows[i].height = Inches(rowh)
        for j in range(nc):
            c = tbl.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.06); c.margin_top = c.margin_bottom = Inches(0.01)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            tcPr = c._tc.get_or_add_tcPr()
            for ch in list(tcPr): tcPr.remove(ch)
            _border(tcPr, "a:lnL", 0, None); _border(tcPr, "a:lnR", 0, None)
            top = 1.5 if i == 0 else 0
            bot = 1.5 if i == nr - 1 else (0.75 if i == mid_after else 0)
            _border(tcPr, "a:lnT", top, INK); _border(tcPr, "a:lnB", bot, INK)
            etree.SubElement(tcPr, qn("a:noFill"))
            p = c.text_frame.paragraphs[0]
            a = align[j] if align else ("l" if j == 0 else "r")
            p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[a]
            col = RED if i in red_rows else INK
            add_runs(p, str(rows[i][j]), size, col, bold=(i == 0) or ((i, j) in bold_cells) or (i in red_rows))
    return tbl

page = [3]
def new_slide(title, notes):
    s = prs.slides.add_slide(layout)
    for ph in list(s.placeholders): ph._element.getparent().remove(ph._element)
    text(s, 0.36, 0.06, 9.15, 0.4, title, 22, "FFFFFF", bold=True, anchor="m")
    page[0] += 1
    text(s, 8.8, 5.28, 0.75, 0.26, str(page[0]), 8.5, MUTED, align="r")
    s.notes_slide.notes_text_frame.text = notes
    return s

def set_text(shape, lines):
    tf = shape.text_frame
    p0 = tf.paragraphs[0]._p
    rPr, pPr = p0.find(".//" + qn("a:rPr")), p0.find(qn("a:pPr"))
    for p in list(tf._txBody.findall(qn("a:p"))): tf._txBody.remove(p)
    for ln in lines:
        p = etree.SubElement(tf._txBody, qn("a:p"))
        if pPr is not None: p.append(copy.deepcopy(pPr))
        r = etree.SubElement(p, qn("a:r")); r.append(copy.deepcopy(rPr))
        etree.SubElement(r, qn("a:t")).text = ln


def retext(slide, old, new):
    """Thay chữ có sẵn trong template (giữ định dạng run)."""
    for shp in slide.shapes:
        if not shp.has_text_frame: continue
        for p in shp.text_frame.paragraphs:
            for r in p.runs:
                if old.lower() in r.text.lower():
                    r.text = re.sub(re.escape(old), new, r.text, flags=re.I)

# ============ 1-3: bìa, tiêu đề, nội dung ============
cover.notes_slide.notes_text_frame.text = "Xin chào thầy cô và các bạn. Đề tài của em là bài toán của Orange trong EURO/ROADEF Challenge 2026."
sh = {s.name: s for s in title_sl.shapes}
set_text(sh["Google Shape;84;p16"], ["Keep The Flow!", "T-Adaptive Segment Routing: MILP và sinh cột"])
set_text(sh["Google Shape;85;p16"], ["Mô hình hoá toán học  ·  EURO/ROADEF Challenge 2026"])
set_text(sh["Google Shape;86;p16"], ["Lê Phạm Thuỷ Tiên  20261075M"])
title_sl.notes_slide.notes_text_frame.text = (
    "Em mô hình bài toán T-Adaptive Segment Routing của Orange bằng MILP, sau đó bằng mô hình theo đường đi giải bằng "
    "sinh cột, và thử cả hai với HiGHS trên 20 instance SetA.")
sh = {s.name: s for s in outline_sl.shapes}
for a, b, t1 in [("96", "97", "Bài toán"), ("100", "101", "Các nghiên cứu liên quan"), ("104", "105", "Phương pháp"),
                 ("108", "109", "Kết quả"), ("112", "113", "Kết luận")]:
    set_text(sh[f"Google Shape;{a};p17"], [t1])
    sh[f"Google Shape;{b};p17"].text_frame.clear()
retext(outline_sl, "Outline", "Nội dung")
outline_sl.notes_slide.notes_text_frame.text = "Bài trình bày gồm năm phần: bài toán, các nghiên cứu liên quan, phương pháp, kết quả và kết luận."

# ============ 4. bối cảnh ============
s = new_slide("Vì sao cần kỹ thuật lưu lượng?",
    "Orange vận hành các mạng backbone IP quy mô quốc gia với hàng nghìn router và hàng chục nghìn demand. Hình bên là "
    "setA-20, một mạng của challenge. Lưu lượng đi theo đường ngắn nhất theo trọng số do nhà vận hành gán. Cách này đơn "
    "giản, nhưng nhiều luồng dồn vào cùng vài liên kết, và tìm lại trọng số cũng là một bài toán khó. Ngoài ra liên kết "
    "có thể bị tắt để bảo trì, làm đường ngắn nhất thay đổi và chỗ nghẽn dịch chuyển.")
text(s, 0.45, 0.85, 5.1, 3.9, [
    "Orange vận hành các mạng backbone IP/MPLS quốc gia",
    "- hàng nghìn router, hàng chục nghìn demand",
    "Lưu lượng đi theo **đường ngắn nhất** theo trọng số ω",
    "- dễ vận hành, nhưng luồng dồn vào vài liên kết",
    "- chỉnh lại ω cũng là bài toán NP-khó [1]",
    "Liên kết bị tắt để **bảo trì**",
    "- đường ngắn nhất đổi, chỗ nghẽn dịch chuyển",
    "Mục tiêu: giữ *liên kết tải nặng nhất* thấp nhất có thể"], 16, bullets=True, space=11)
image(s, "setA20.png", 6.0, 0.8, h=3.75)
caption(s, 5.9, 4.45, 3.7, "setA-20: 400 router, 2000 cung")
footnote(s, "[1] B. Fortz, M. Thorup. Internet traffic engineering by optimizing OSPF weights. INFOCOM 2000.")

# ============ 5. segment routing ============
s = new_slide("Segment Routing: một waypoint là đủ",
    "Với Segment Routing, nút nguồn ghi một danh sách waypoint vào header của gói tin. Giữa hai waypoint, gói tin đi theo "
    "đường ngắn nhất, và khi có nhiều đường ngắn nhất thì ECMP chia đều luồng tại mỗi nút. Trên instance toy của đề, "
    "định tuyến theo đường ngắn nhất làm cung v3 v5 tải 0.4375. Cho demand v0 đến v5 đi qua waypoint v4 thì tải được dàn "
    "đều, giá trị lớn nhất giảm còn 0.375, là tối ưu.")
text(s, 0.45, 0.78, 9.1, 0.65,
     "Nút nguồn ghi danh sách *waypoint* vào header gói tin. Giữa hai waypoint, gói tin đi theo đường ngắn nhất; "
     "khi có nhiều đường thì chia đều tại mỗi nút (ECMP).", 15)
image(s, "toy_default.png", 0.45, 1.55, w=4.35)
image(s, "toy_sr.png", 5.2, 1.55, w=4.35)
caption(s, 0.45, 4.3, 4.35, "(a) chỉ dùng đường ngắn nhất, MLU = 0.4375")
caption(s, 5.2, 4.3, 4.35, "(b) demand (v₀, v₅) qua waypoint v₄, MLU = 0.375")
footnote(s, "Instance toy của đề, t = 0. Nhãn cung: tải / dung lượng; màu đỏ = cung tải nặng nhất.")

# ============ 6. bài toán ============
s = new_slide("Bài toán T-ASR",
    "Bài toán T-Adaptive Segment Routing cho một mạng có hướng với trọng số và dung lượng, các demand có lưu lượng thay "
    "đổi theo chu kỳ, một lịch bảo trì, số segment tối đa, và một budget giới hạn số segment được thay đổi giữa hai chu kỳ "
    "liên tiếp. Ta chọn một segment path cho mỗi demand và mỗi chu kỳ. Đề dùng mục tiêu lexicographic; em cực tiểu thành "
    "phần đầu tiên của nó là MLU, tải lớn nhất trên các liên kết. Bài toán là NP-khó và khó xấp xỉ, kể cả trên topology đơn giản.")
rows = [("Cho", ["mạng có hướng G = (V, A), trọng số ω(a), dung lượng c(a)",
                 "demand d = (s_{d}, t_{d}), lưu lượng ν(d, t), chu kỳ t = 0, …, h−1",
                 "bảo trì: tập cung q(t) bị tắt tại chu kỳ t",
                 "tối đa maxSeg segment mỗi đường, budget κ(t) cho thay đổi"]),
        ("Tìm", ["một segment path ⟨s_{d}, w_{1}, …, t_{d}⟩ cho mỗi demand và mỗi chu kỳ"]),
        ("Cực tiểu", ["MLU = max_{a, t}  tải(a, t) / c(a)"])]
y = 0.95
for lab, lines in rows:
    text(s, 0.45, y, 1.3, 0.35, lab, 17, RED, bold=True)
    text(s, 1.8, y, 7.7, 0.35 * len(lines), lines, 16, space=4)
    y += 0.36 * len(lines) + 0.25
hline(s, 0.45, y - 0.05, 9.55, "D5D8DC")
text(s, 0.45, y + 0.05, 9.1, 0.8, [
    "Đề dùng mục tiêu lexicographic trên toàn bộ vector tải; MLU là thành phần đầu tiên và quan trọng nhất.",
    "NP-khó và khó xấp xỉ, kể cả trên topology rất đơn giản [2]."], 14, MUTED, space=4)
footnote(s, "[2] C. Bazgan, M. Chopin, A. Nichterlein, C. Richer. Parameterized complexity of segment routing. INFOCOM 2025.")

# ============ 7a. timeline ============
s = new_slide("Nghiên cứu liên quan: 25 năm kỹ thuật lưu lượng",
    "Tóm tắt lịch sử. Năm 2000 Fortz và Thorup chứng minh chỉnh trọng số OSPF là NP-khó và đề xuất tìm kiếm cục bộ. "
    "Segment Routing thay đổi câu hỏi: năm 2015 Bhatia và cộng sự cho thấy hai segment, tức một waypoint, gần như đủ để "
    "cân bằng tải, và Hartert và cộng sự xây dựng DEFO, bộ tối ưu SR tập trung đầu tiên. Gay và cộng sự sau đó tối ưu lại "
    "các mạng ISP lớn trong dưới một giây bằng tìm kiếm cục bộ. SR được chuẩn hoá trong RFC 8402 năm 2018, và CG4SR đưa "
    "sinh cột vào năm 2019. Các công trình sau kết hợp trọng số với segment, và tiền xử lý loại các đường bị trội. Năm "
    "2025 Bazgan và cộng sự làm rõ độ phức tạp. Phiên bản theo thời gian, có budget cho thay đổi, chỉ xuất hiện năm 2026 "
    "cùng challenge này.")
ev = [("2000", "Fortz & Thorup", "trọng số OSPF:\nNP-khó"),
      ("2015", "Bhatia et al.", "2 segment gần\nnhư là đủ"),
      ("2015", "Hartert et al.", "DEFO, bộ tối\nưu SR đầu tiên"),
      ("2017", "Gay et al.", "tìm kiếm cục\nbộ < 1 giây"),
      ("2018", "RFC 8402", "chuẩn hoá\nSR"),
      ("2019", "Jadin et al.", "CG4SR:\nsinh cột"),
      ("2021", "Parham et al.", "trọng số +\nsegment cùng lúc"),
      ("2023", "Callebaut et al.", "loại đường\nbị trội"),
      ("2025", "Bazgan et al.", "độ phức tạp\ntham số hoá"),
      ("2026", "Benhamiche; Jaumard", "T-ASR: thời\ngian + budget")]
y0 = 2.75
hline(s, 0.55, y0, 9.45, RULE, 1.25)
for k, (yr, who, what) in enumerate(ev):
    x = 0.95 + k * 0.9
    last = k == len(ev) - 1
    d = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x - 0.08), Inches(y0 - 0.08), Inches(0.16), Inches(0.16))
    d.fill.solid(); d.fill.fore_color.rgb = rgb(RED if last else "FFFFFF")
    d.line.color.rgb = rgb(RED if last else INK); d.line.width = Pt(1.25)
    up = k % 2 == 0
    tick_y = (y0 - 0.45, y0 - 0.1) if up else (y0 + 0.1, y0 + 0.45)
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(tick_y[0]), Inches(x), Inches(tick_y[1]))
    c.line.color.rgb = rgb("C4C8CC"); c.line.width = Pt(0.75)
    col = RED if last else INK
    if up:
        text(s, x - 0.85, y0 - 1.55, 1.7, 0.3, yr, 15, col, bold=True, align="c")
        text(s, x - 0.85, y0 - 1.25, 1.7, 0.3, who, 12, col, bold=True, align="c")
        text(s, x - 0.85, y0 - 1.0, 1.7, 0.5, what.split("\n"), 11, MUTED, align="c", space=0)
    else:
        text(s, x - 0.85, y0 + 0.5, 1.7, 0.3, yr, 15, col, bold=True, align="c")
        text(s, x - 0.85, y0 + 0.8, 1.7, 0.3, who, 12, col, bold=True, align="c")
        text(s, x - 0.85, y0 + 1.05, 1.7, 0.5, what.split("\n"), 11, MUTED, align="c", space=0)
text(s, 0.45, 4.45, 9.1, 0.3,
     "Bài toán thay đổi theo thời gian với *budget cho việc cấu hình lại* chỉ xuất hiện năm 2026, cùng challenge này.", 14)

# ============ 7b. ba nhóm phương pháp ============
s = new_slide("Nghiên cứu liên quan: ba nhóm phương pháp",
    "Với bài toán tĩnh, một chu kỳ, có ba nhóm phương pháp. Mô hình chính xác: các công thức MILP hoặc ILP như DEFO, "
    "Schüller và cộng sự, Li và Yeung. Chúng cho nghiệm tối ưu và cận, nhưng có khoảng D nhân V bình phương biến. Sinh "
    "cột, như CG4SR: bài toán chính LP chọn segment path, bài toán con tìm đường mới có reduced cost âm; với tối đa maxSeg "
    "segment, bài toán con là đường ngắn nhất có số cung bị chặn, giải bằng quy hoạch động. Và heuristic: tìm kiếm cục bộ "
    "đổi ít đường và chạy dưới một giây, còn Bhatia và Pereira giới hạn đường ở hai hoặc ba segment. Phương pháp 1 của em "
    "thuộc nhóm thứ nhất, phương pháp 2 thuộc nhóm thứ hai.")
fam = [("Chính xác: MILP / ILP", "DEFO 2015 · Schüller et al. 2018 · Li & Yeung 2020",
        ["Nghiệm tối ưu và cận", "≈ |D| · |V|^{2} biến nhị phân", "Kích thước bị giới hạn bởi bộ nhớ"]),
       ("Sinh cột", "CG4SR 2019 · Jaumard et al. 2026",
        ["LP chính chọn một đường cho mỗi demand", "Bài toán con: đường ≤ maxSeg cung (QHĐ)", "Gần tối ưu, có cận LP"]),
       ("Heuristic", "Gay et al. 2017 · Bhatia et al. 2015 · Pereira et al. 2020",
        ["Tìm kiếm cục bộ: ít thay đổi, < 1 giây", "Giới hạn 2 hoặc 3 segment", "Không có cận"])]
for k, (h, refs, pts) in enumerate(fam):
    x = 0.45 + k * 3.1
    if k < 2:
        frame(s, x - 0.08, 0.85, 3.0, 3.75, RED, 1.25)
    text(s, x, 0.95, 2.85, 0.35, h, 17, RED, bold=True)
    text(s, x, 1.33, 2.85, 0.55, refs, 11.5, MUTED, italic=True)
    text(s, x, 2.0, 2.85, 2.0, pts, 14, bullets=True, space=10)
    if k < 2:
        text(s, x, 4.05, 2.85, 0.35, ["Phương pháp 1 của em", "Phương pháp 2 của em"][k], 13, RED, bold=True)
text(s, 0.45, 4.72, 9.1, 0.3, "Trước 2026 đều chỉ xét một chu kỳ; T-ASR thêm nhiều chu kỳ, bảo trì và budget thay đổi.", 13, MUTED)

# ============ 7c. hai bài báo T-ASR ============
s = new_slide("Nghiên cứu liên quan: hai bài báo về T-ASR (2026)",
    "Có hai bài báo nghiên cứu trực tiếp T-ASR. Benhamiche và cộng sự, tác giả của challenge, đưa ra đúng mô hình em dùng. "
    "Họ xử lý mục tiêu lexicographic bằng chuỗi MILP, ALEXA và STELA; STELA tốt hơn ở 109 trên 115 instance, và bước đầu "
    "của cả hai là min MLU, chính là bài toán em giải. Họ cũng chỉ ra rằng khi có budget, đường tốt nhất có thể chứa vòng "
    "lặp, nên tiền xử lý cho một chu kỳ không dùng lại được. Thí nghiệm của họ trên instance nhỏ, tối đa 50 nút. Jaumard và "
    "cộng sự dùng MLU và budget như em, nhưng giải từng chu kỳ một, nhờ đó budget tuyến tính, và dùng sinh cột. Họ là nhóm "
    "duy nhất có kết quả trên toàn bộ SetA: gap LP–ILP trung bình 3.12 phần trăm tại t bằng 0 nhưng 13.05 phần trăm tại t "
    "bằng 1, nên chu kỳ thứ hai khó hơn rõ rệt.")
text(s, 0.45, 0.82, 4.4, 0.35, "Benhamiche et al., tác giả của đề", 16, RED, bold=True)
text(s, 0.45, 1.25, 4.4, 3.4, [
    "Cùng mô hình (1)–(4) như em",
    "Mục tiêu lexicographic bằng chuỗi MILP",
    "-ALEXA (hoán vị, big-M), STELA (ngưỡng)",
    "-STELA tốt hơn ở 109 / 115 instance",
    "-bước 1 của cả hai = min MLU",
    "Khi có budget, đường tốt nhất có thể cần *vòng lặp*",
    "Thí nghiệm: setAP, 10–50 nút, Gurobi, 20 phút"], 14, bullets=True, space=7)
text(s, 5.1, 0.82, 4.45, 0.35, "Jaumard, Tran, Ziazet", 16, RED, bold=True)
text(s, 5.1, 1.25, 4.45, 1.9, [
    "MLU + budget, giống em",
    "Từng chu kỳ: cố định t − 1 → budget tuyến tính",
    "Sinh cột, rồi ILP trên tập cột",
    "Duy nhất có kết quả trên *toàn bộ SetA*"], 14, bullets=True, space=7)
for k, (big, lab) in enumerate([("3.12%", "gap LP–ILP trung bình, t = 0"), ("13.05%", "gap LP–ILP trung bình, t = 1")]):
    x = 5.25 + k * 2.15
    text(s, x, 3.25, 2.0, 0.55, big, 28, RED if k else INK, bold=True, align="c")
    text(s, x, 3.82, 2.0, 0.3, lab, 11.5, MUTED, align="c")
text(s, 5.1, 4.2, 4.45, 0.3, "→ budget làm chu kỳ t = 1 khó hơn nhiều", 13, INK, italic=True)
footnote(s, "Benhamiche et al., On the T-ASR problem, arXiv:2609.32896.   Jaumard et al., SR-TE with time-based reconfiguration constraints, arXiv:2610.04759.")

# ============ 7d. so sánh ============
s = new_slide("Vị trí của đề tài",
    "Bảng này đặt các cách tiếp cận cạnh nhau. MILP đầy đủ là chính xác, cho gap, xử lý trực tiếp budget, nhưng chỉ chạy "
    "được trên instance nhỏ. Giải từng chu kỳ cho cận của từng bài toán con nhưng không cho tối ưu toàn cục. Sinh cột mở "
    "rộng được tới toàn bộ SetA với cận LP. Tìm kiếm cục bộ rất nhanh nhưng không có cận, còn giới hạn hai segment cho mô "
    "hình nhỏ hơn. Em làm hai trong số đó: phương pháp 1 là MILP đầy đủ của đề, để có giá trị tối ưu thật và xem nó dừng "
    "ở đâu; phương pháp 2 là mô hình theo đường đi với sinh cột, giải đồng thời hai chu kỳ, để giải được toàn bộ SetA.")
cmp_rows = [["Cách tiếp cận", "Tối ưu", "Cận", "Budget", "Quy mô", "Bài báo chính"],
            ["MILP đầy đủ", "có", "có", "có, (4)", "nhỏ", "Benhamiche 2026"],
            ["Từng chu kỳ + MILP", "từng chu kỳ", "từng chu kỳ", "có", "vừa", "Benhamiche; Jaumard 2026"],
            ["Sinh cột", "gần", "cận LP", "có", "lớn", "CG4SR 2019, Jaumard 2026"],
            ["Tìm kiếm cục bộ", "không", "không", "ít thay đổi", "rất lớn", "Gay 2017, Hartert 2018"],
            ["Chỉ 2 segment", "không", "mô hình con", "có", "lớn", "Bhatia 2015"],
            ["PP1: MILP đầy đủ", "có", "gap MILP", "có, (4)", "≤ 5·10^{6} biến", "MILP của đề, HiGHS"],
            ["PP2: sinh cột", "13 / 20", "Lagrange", "có, chính xác", "cả 20", "hai chu kỳ đồng thời"]]
table(s, 0.45, 0.85, 9.1, cmp_rows, [2.2, 1.15, 1.2, 1.2, 1.35, 2.3], size=12.5, rowh=0.38, red_rows=(6, 7),
      align="llllll")
text(s, 0.45, 4.05, 9.1, 0.7, [
    "PP1: *giá trị tối ưu thật và gap* với solver mã nguồn mở: mô hình chính xác đi được bao xa?",
    "PP2: cùng bài toán trên *toàn bộ SetA*, hai chu kỳ cùng lúc, có cận dưới"], 14, space=3)

# ============ 8. tổng quan phương pháp ============
s = new_slide("Phương pháp",
    "Quy trình gồm năm bước. Đọc mạng, ma trận lưu lượng và kịch bản. Tính trước hệ số chia luồng r. Sau đó dùng phương "
    "pháp 1, MILP đầy đủ trong JuMP, hoặc phương pháp 2, mô hình theo đường đi giải bằng sinh cột; cả hai dùng HiGHS. Cuối "
    "cùng đọc lại các segment path, tính lại tải và số thay đổi. Điểm mấu chốt là r chỉ phụ thuộc vào đồ thị, nên tải "
    "của một cung là hàm tuyến tính của biến quyết định.")
steps = [("Instance", "net, tm, scenario\n(JSON)"), ("Hệ số r", "Dijkstra + ECMP,\nmọi cặp nút"),
         ("Mô hình", "PP1: MILP đầy đủ\nPP2: theo đường đi"), ("Giải", "HiGHS; PP2 thêm\nsinh cột"),
         ("Kiểm tra", "đường, tải,\nbudget")]
for k, (h, sub) in enumerate(steps):
    x = 0.45 + k * 1.86
    frame(s, x, 1.0, 1.5, 0.55, RED if k in (1, 2) else RULE, 1.25 if k in (1, 2) else 0.75)
    text(s, x, 1.0, 1.5, 0.55, h, 15, RED if k in (1, 2) else INK, bold=True, align="c", anchor="m")
    text(s, x - 0.1, 1.62, 1.7, 0.55, sub.split("\n"), 12, MUTED, align="c", space=0)
    if k < 4: arrow(s, x + 1.53, 1.275, x + 1.83, 1.275)
text(s, 0.45, 2.55, 9.1, 2.2, [
    "r(i, j, a, t) chỉ phụ thuộc vào đồ thị của chu kỳ t, không phụ thuộc vào định tuyến",
    "- tính một lần trước khi giải; tải của mọi cung trở thành hàm *tuyến tính* theo x",
    "PP1: mô hình chính xác của đề, mục tiêu min MLU",
    "- nghiệm khởi đầu không waypoint (luôn khả thi), nên lần chạy nào cũng có cận trên",
    "PP2: cùng giá trị tối ưu, nhưng chỉ sinh những đường cần thiết",
    "- ~10^{4} cột thay vì tới 9.6·10^{8} biến nhị phân"], 15, bullets=True, space=8)

# ============ 9. hệ số chia luồng ============
s = new_slide("Hệ số chia luồng r(i, j, a, t)",
    "r của i, j, a, t là phần của một đơn vị luồng từ i đến j đi qua cung a trong đồ thị của chu kỳ t. Nút nào cũng có thể "
    "là waypoint, nên cần tính cho mọi cặp. Chạy Dijkstra từ mọi nút, đánh dấu các cung nằm trên đường ngắn nhất, rồi đẩy "
    "một đơn vị luồng theo thứ tự topo, chia đều tại mỗi nút. Với trọng số số thực thì phép so sánh cần sai số. Hình bên là "
    "demand v0 đến v5 của instance toy: 0.5, 0.5 và 0.75 trên cung v3 v5, đúng như Table 2 của đề. Công thức đếm số đường "
    "ngắn nhất trong tài liệu hướng dẫn cho một phần ba, hai phần ba và hai phần ba, vì nó chia theo đường chứ không theo nút.")
text(s, 0.45, 0.8, 4.6, 0.65, "Phần của một đơn vị luồng từ i đến j đi qua cung a trong G_{t} = (V, A ∖ q(t)).", 15)
lines = ["Dijkstra từ mọi nút → d_{ij}",
         "a = (u, v) nằm trên đường ngắn nhất i–j ⇔ d_{iu} + ω(a) + d_{vj} = d_{ij}",
         "Đẩy một đơn vị từ i theo d_{·j} giảm dần; chia đều tại mỗi nút"]
tb = text(s, 0.45, 1.55, 4.6, 2.0, lines, 15, space=10)
for p in tb.text_frame.paragraphs:
    pPr = p._p.get_or_add_pPr(); pPr.set("marL", "285750"); pPr.set("indent", "-285750")
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "+mj-lt")
    etree.SubElement(pPr, qn("a:buAutoNum")).set("type", "arabicPeriod")
text(s, 0.45, 3.45, 4.6, 1.2, [
    "Trọng số thực (setA-05, 08, 12, 14): so sánh với sai số tương đối 10^{−9}.",
    "Đếm đường ngắn nhất (σ_{iu}σ_{vj}/σ_{ij}) chia theo *đường*, không theo nút: ở đây ra 1/3, 2/3, 2/3."], 13, MUTED, space=6)
image(s, "toy_ecmp.png", 5.3, 0.95, w=4.25)
caption(s, 5.3, 3.8, 4.25, "r(v₀, v₅, a) trên instance toy, khớp Table 2 của đề")

# ============ 10. mô hình ============
s = new_slide("Mô hình MILP",
    "Coi mỗi cặp nút i, j là một cung ảo, khi đó segment path của demand d là một đường đi từ nguồn tới đích trong đồ thị "
    "đầy đủ. x cho biết demand d có dùng segment i, j tại chu kỳ t hay không, và U là MLU. Ràng buộc một: mỗi demand đúng "
    "một segment path. Hai: độ dài header. Ba: tải của mỗi cung, tuyến tính vì r và lưu lượng là dữ liệu. Bốn: budget; trị "
    "tuyệt đối của thay đổi được tuyến tính hoá bằng biến y.")
text(s, 0.45, 0.78, 9.1, 0.4,
     "Cặp nút (i, j) là cung ảo: segment path là đường đi từ s_{d} đến t_{d}.   x^{dt}_{ij} = 1 nếu demand d dùng segment (i, j) tại t.", 13.5)
image(s, "model.png", 1.55, 1.3, h=2.95)
text(s, 0.45, 4.35, 9.1, 0.5,
     "(1) mỗi demand một segment path   (2) độ dài header   (3) tải cung — tuyến tính, r và ν là dữ liệu   (4) budget, tuyến tính hoá |x^{t} − x^{t−1}|",
     12, MUTED)
footnote(s, "Một chu kỳ (t = 0): (1)–(3).   Hai chu kỳ có budget: (1)–(4).")

# ============ 11. kiểm tra ============
s = new_slide("Mô hình có đúng không?",
    "Trước hết em kiểm tra mô hình trên instance toy. Không có waypoint thì MLU tại chu kỳ 0 là 0.4375; mô hình tìm được "
    "0.375, đúng nghiệm ở Figure 4 của đề, và tại chu kỳ 1 cũng là 0.375. Vét cạn toàn bộ 206 segment path cho mỗi demand "
    "cho cùng giá trị tối ưu. Có ba chi tiết gây khó khi cài đặt: khoảng cách số thực, các chu trình rời mà ràng buộc một "
    "không cấm, và việc min MLU chỉ quan tâm tới chu kỳ tệ nhất.")
text(s, 0.45, 0.82, 4.3, 0.4, "Instance toy", 17, RED, bold=True)
text(s, 0.45, 1.25, 4.3, 3.0, [
    "t = 0: 0.4375 → **0.375** (Figure 4 của đề)",
    "t = 1: **0.375**, budget κ(1) = 20 không chặt",
    "Vét cạn 206 segment path mỗi demand: cùng giá trị tối ưu"], 15, bullets=True, space=10)
text(s, 5.1, 0.82, 4.45, 0.4, "Ba điểm dễ sai", 17, RED, bold=True)
text(s, 5.1, 1.25, 4.45, 3.3, [
    "**Khoảng cách số thực**",
    "- dùng ==, hơn nửa số cặp nút mất luồng ở setA-08, 12, 14",
    "**Chu trình rời**",
    "- (1) cho phép x_{ij} = x_{ji} = 1; đọc đường bằng chu trình Euler rồi tính lại tải và budget",
    "**min MLU chỉ nhìn một chu kỳ**",
    "- chu kỳ còn lại có thể vẫn cao"], 15, bullets=True, space=10)

# ============ 11b. phương pháp 2 ============
s = new_slide("Phương pháp 2: mô hình theo đường đi và sinh cột",
    "MILP đầy đủ có khoảng D nhân n bình phương biến nhị phân, nên em viết lại theo đường đi. Mỗi cột là một segment path p "
    "của một demand, với tải L của p trên mỗi cung bằng tổng r trên các segment của nó; chọn một đường tương đương với đặt "
    "x cho các segment của nó, nên giá trị tối ưu không đổi. Bài toán chính thu hẹp là LP trên các đường đã sinh, bắt đầu "
    "từ đường đi thẳng. Bài toán con: với đối ngẫu w của ràng buộc tải, chi phí của đường cộng được theo segment, nên tìm "
    "đường có reduced cost âm là bài toán đường ngắn nhất có tối đa maxSeg cung trên đồ thị đầy đủ, giải bằng quy hoạch "
    "động kiểu Bellman-Ford. Mọi w đều cho một cận dưới Lagrange. Với hai chu kỳ, mỗi cột là một cặp đường, và chi phí "
    "budget là số segment chỉ có ở một trong hai đường, nên budget là ràng buộc tuyến tính chính xác, không cần biến y. "
    "Cuối cùng giải MILP trên tập cột, cộng một vòng sửa quanh các cung tải nặng nhất, để có nghiệm nguyên.")
text(s, 0.45, 0.78, 9.1, 0.4,
     "Cột = một segment path p của demand d.   L_{t}(p, a) = Σ_{(i,j) ∈ p} r(i, j, a, t)   (cùng tối ưu với MILP)", 14)
loop = [("LP chính", "các đường đã sinh\nban đầu: đường thẳng ⟨s_{d}, t_{d}⟩"),
        ("Bài toán con", "đường ngắn nhất ≤ maxSeg cung\nW(i, j) = Σ_{a} r(i, j, a) w_{a}  (QHĐ)"),
        ("Nghiệm nguyên", "MILP trên tập cột\n+ sửa các cung tải nặng nhất")]
for k, (h, sub) in enumerate(loop):
    x = 0.45 + k * 3.15
    frame(s, x, 1.35, 2.75, 0.5, RED if k < 2 else RULE, 1.25 if k < 2 else 0.75)
    text(s, x, 1.35, 2.75, 0.5, h, 15, RED if k < 2 else INK, bold=True, align="c", anchor="m")
    text(s, x - 0.1, 1.92, 2.95, 0.6, sub.split("\n"), 11.5, MUTED, align="c", space=0)
    if k < 2: arrow(s, x + 2.78, 1.6, x + 3.12, 1.6)
text(s, 3.2, 2.55, 3.0, 0.3, "đối ngẫu w_{a} → thêm đường nếu reduced cost < 0", 11, MUTED, italic=True, align="c")
text(s, 0.45, 2.95, 9.1, 1.8, [
    "**Cận dưới** ở mọi vòng: cận Lagrange LB(w) và cận “một demand”",
    "**Hai chu kỳ**: cột = cặp (p_{0}, p_{1}); chi phí budget Δ = |S(p_{0}) △ S(p_{1})| segment",
    "- (4) thành ràng buộc tuyến tính chính xác Σ Δ λ ≤ κ, không cần y; tối ưu hai chu kỳ cùng lúc",
    "Gap = 1 − LB / UB, “tối ưu” = gap ≤ 10^{−4} (mip_rel_gap mặc định của HiGHS)"], 14, bullets=True, space=6)
footnote(s, "Bài toán con theo CG4SR: M. Jadin, F. Aubry, P. Schaus, O. Bonaventure, INFOCOM 2019.")

# ============ 11b. điểm mới so với mô hình gốc ============
s = new_slide("Điểm mới so với mô hình gốc của đề",
    "Phương pháp 2 khác mô hình một đến bốn của đề ở năm điểm. Một: biến là cả đường đi chứ không phải từng cặp nút, nên "
    "không còn khoảng D nhân n bình phương biến, chỉ sinh từ hai mươi lăm đến khoảng hai mươi ba nghìn cột. Hai: cận dưới "
    "chứng minh được có ngay ở mọi vòng, gồm cận Lagrange và cận một demand; cận một demand giúp chứng minh setA-02 hai chu "
    "kỳ là tối ưu. Ba: với hai chu kỳ, cột là cặp đường, budget là ràng buộc chính xác không cần biến y, và hai chu kỳ được "
    "tối ưu đồng thời thay vì giải t bằng không trước rồi cố định như bài của Jaumard. Bốn: MILP cặp chặt hơn nhiều so với "
    "tuyến tính hoá bằng y, ở setA-10 giải trong mười giây thay vì hơn ba trăm giây. Năm: vòng cải thiện quanh cung nghẽn "
    "bù khoảng hở của việc giải MILP trên tập cột; ở toy, MILP trên tập cột chỉ đạt 0.4375 còn tối ưu là 0.375. Ý tưởng "
    "sinh cột cho Segment Routing đã có trong CG4SR và Jaumard; phần riêng là các điểm hai đến năm và bộ kiểm tra độc lập.")
rows = [["", "Mô hình gốc (PP1)", "Phương pháp 2 (sinh cột)"],
        ["Biến", "x_{ij}^{dt} cho mỗi demand × cặp nút\n≈ |D| · n(n−1), tới 9.6·10^{8}", "λ_{dp}: demand d chọn path p\n25 – 23 000 cột sinh dần"],
        ["Cận dưới", "chỉ có khi MILP giải được", "Lagrange + “một demand”\ncó ở mọi vòng"],
        ["Budget (Step 9)", "tuyến tính hoá |x^{t} − x^{t−1}| bằng biến y", "cột = cặp (p_{0}, p_{1}), Δ = |S(p_{0}) △ S(p_{1})|\nchính xác, không cần y"],
        ["Hai chu kỳ", "đồng thời", "đồng thời (min của max); [Jaumard 2026]: tuần tự"],
        ["Nghiệm nguyên", "branch-and-bound trên mọi x", "LP → MILP trên tập path → vòng cải thiện\nquanh cung nghẽn"],
        ["Kiểm tra nghiệm", "giá trị của solver", "tính lại tải + script Python độc lập\n(định dạng checker chính thức)"]]
table(s, 0.45, 0.75, 9.1, rows, [1.5, 3.3, 4.3], size=11, rowh=0.52, align="lll", bold_cells={(i, 0) for i in range(1, 7)})
footnote(s, "Sinh cột cho SR đã có ở CG4SR [Jadin 2019] và [Jaumard 2026]; phần riêng: cột cặp path với budget chính xác, cận “một demand”, MILP cặp, vòng cải thiện.")

# ============ 12. thiết lập ============
s = new_slide("Thiết lập thí nghiệm",
    "SetA gồm 20 instance, từ 20 đến 400 nút và từ 20 đến 6000 demand. Tất cả có hai chu kỳ, tối đa sáu segment và một cung "
    "bị tắt tại chu kỳ 1. Mọi lần chạy đều trên máy chủ Xeon 8 nhân, 63 GB RAM, trong Docker, với Julia, JuMP và HiGHS, giới "
    "hạn 1800 giây cho một chu kỳ và 3600 giây cho hai chu kỳ. Phương pháp 1 tăng mức heuristic và dùng nghiệm khởi đầu, "
    "chạy mười seed nếu giải xong dưới 300 giây, ngược lại một lần; mô hình trên năm triệu biến không được dựng. Phương "
    "pháp 2 chia thời gian cho sinh cột, MILP trên tập cột và vòng sửa, và luôn chạy mười seed.")
text(s, 0.45, 0.82, 4.4, 0.4, "Instance: SetA (20)", 17, RED, bold=True)
text(s, 0.45, 1.25, 4.4, 3.4, [
    "20–400 nút, 80–2000 cung",
    "20–6000 demand",
    "h = 2 chu kỳ, maxSeg = 6",
    "một cung bị tắt tại t = 1",
    "budget κ(1) từ 1 đến 90",
    "biến nhị phân: 1.5·10^{4} đến 9.6·10^{8} mỗi chu kỳ"], 15, bullets=True, space=8)
text(s, 5.1, 0.82, 4.45, 0.4, "Cấu hình chạy", 17, RED, bold=True)
text(s, 5.1, 1.25, 4.45, 3.5, [
    "Xeon 2.2 GHz, 8 nhân / 16 luồng, 62.8 GB, Docker",
    "Julia 1.13.2, JuMP 1.32.1, HiGHS 1.15.1",
    "Giới hạn 1800 s (t = 0), 3600 s (hai chu kỳ)",
    "**PP1**: mip_heuristic_effort 0.3, nghiệm khởi đầu",
    "- 10 seed nếu giải < 300 s, ngược lại 1; > 5·10^{6} biến không dựng",
    "**PP2**: sinh cột 600 s + MILP 300 s + vòng sửa",
    "- 10 seed (0–9), 8 lượt × 2 luồng song song"], 14, bullets=True, space=5)

# ============ 13. step 6 ============
s = new_slide("Một chu kỳ (t = 0): MLU giảm tới 65%",
    "Với một chu kỳ, mô hình chứng minh tối ưu ở 01, 02, 03 và 05. MLU giảm 7.1, 45.1, 5.6 và 65.3 phần trăm so với đường "
    "ngắn nhất. Mọi seed cho cùng giá trị tối ưu nhưng thời gian dao động nhiều. Cây nhánh cận chỉ có 0 hoặc 1 nút: cận ở "
    "gốc đã chặt, thời gian chủ yếu dành cho LP gốc và cho việc tìm nghiệm nguyên khớp với cận. Ở 04 solver không cải "
    "thiện được nghiệm khởi đầu trong 1800 giây.")
image(s, "step6.png", 0.35, 0.85, w=5.6)
text(s, 6.15, 0.95, 3.4, 3.8, [
    "Tối ưu ở 01, 02, 03, 05",
    "- MLU −7.1%, −45.1%, −5.6%, −65.3%",
    "0–1 nút nhánh cận",
    "- cận gốc đã chặt; thời gian dành cho LP gốc và tìm nghiệm khớp cận",
    "Thời gian phụ thuộc seed",
    "- setA-01: 4.5 ± 8.9 s",
    "04: không cải thiện trong 1800 s (gap 33.6%)"], 14, bullets=True, space=9)

# ============ 14. cấm vòng lặp ============
s = new_slide("Cấm vòng lặp: nhanh hơn, nhưng không luôn như vậy",
    "Với một chu kỳ, ta có thể cấm segment path đi qua một nút hai lần; giá trị tối ưu không đổi vì bỏ một vòng lặp không "
    "bao giờ làm tải tăng. Ràng buộc này làm 01 đến 03 nhanh hơn từ bốn đến mười chín lần và tìm được 0.4791 ở 04 thay vì "
    "0.6918, nên tối ưu của 04 nằm giữa 0.4591 và 0.4791; sau đó phương pháp 2 tìm được 0.4591, tức là tối ưu với sai số "
    "0.01 phần trăm. Nhưng ở 05 HiGHS không giải xong LP gốc. Vì hiệu quả không đồng đều, bảng kết quả chính dùng mô hình "
    "của đề. Khi có budget thì biến thể này không hợp lệ.")
rows = [["", "Obj", "CPU (s)", "Gap", "Obj", "CPU (s)", "Gap"],
        ["setA-01", "0.9294", "4.5", "0", "0.9294", "0.6", "0"],
        ["setA-02", "0.5486", "318.0", "0", "0.5486", "16.4", "0"],
        ["setA-03", "0.9435", "58.2", "0", "0.9435", "13.6", "0"],
        ["setA-04", "0.6918", "1800", "33.6%", "0.4791", "1800", "4.2%"],
        ["setA-05", "0.1155", "1706", "0", "0.3333", "6037", "–"]]
text(s, 1.75, 0.85, 3.6, 0.3, "Mô hình của đề (1)–(3)", 13, MUTED, align="c")
text(s, 5.55, 0.85, 3.6, 0.3, "+ mỗi nút tối đa một lần", 13, MUTED, align="c")
hline(s, 1.85, 1.17, 5.25, MUTED); hline(s, 5.65, 1.17, 9.05, MUTED)
table(s, 0.45, 1.22, 8.7, rows, [1.3, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2], size=14, rowh=0.36,
      bold_cells={(1, 5), (2, 5), (3, 5), (4, 4), (5, 1)})
text(s, 0.45, 3.55, 9.1, 1.3, [
    "**Nhanh hơn 4–19×** ở 01–03; setA-04: 0.6918 → 0.4791, cận 0.4591; PP2 đạt *0.4591*",
    "setA-05: chưa có LP gốc sau 6037 s, nên bảng chính giữ mô hình của đề",
    "Không hợp lệ khi có budget: đường tốt nhất có thể cần vòng lặp"], 14, bullets=True, space=6)

# ============ 15. step 9 ============
s = new_slide("Hai chu kỳ có budget",
    "Với hai chu kỳ và budget, mô hình lớn gấp khoảng ba lần; chỉ dựng được 01 đến 05 và giải xong 01 đến 03. Ở 01 và 03 "
    "kết quả bằng tối ưu của chu kỳ 0: chu kỳ 0 là nút thắt. Ở 02, định tuyến mặc định làm một liên kết quá tải 109.8 phần "
    "trăm tại chu kỳ 1, và mô hình đưa về 0.9031, bằng tối ưu của riêng chu kỳ 1. Vậy không trường hợp nào budget là giới "
    "hạn. Em đã kiểm tra lại nghiệm: mọi đường hợp lệ, MLU bằng U, và số thay đổi là 0, 0 và 8, trong budget.")
rows = [["", "κ(1)", "MLU₀", "Obj", "CPU (s)", "Trạng thái"],
        ["setA-01", "51", "1.0000", "0.9294", "163.9", "tối ưu"],
        ["setA-02", "63", "1.0981", "0.9031", "172.4", "tối ưu"],
        ["setA-03", "53", "1.0000", "0.9435", "704.2", "tối ưu"],
        ["setA-04", "44", "1.0000", "1.0000", "9905*", "chưa có cận LP"],
        ["setA-05", "1", "1.0000", "1.0000", "> 10800", "bị dừng"]]
table(s, 0.45, 0.95, 5.3, rows, [1.2, 0.7, 1.0, 1.0, 1.0, 1.5], size=14, rowh=0.38,
      bold_cells={(1, 3), (2, 3), (3, 3)})
text(s, 0.45, 3.32, 5.3, 0.6, ["MLU₀: không waypoint; Obj: MLU lớn nhất trên hai chu kỳ.",
                               "* HiGHS vượt giới hạn 3600 s trong lúc giải LP gốc."], 11, MUTED, space=2)
text(s, 6.0, 0.95, 3.55, 3.8, [
    "01, 03: bằng kết quả chỉ t = 0",
    "- chu kỳ 0 là nút thắt",
    "02: quá tải 109.8% tại t = 1 → **90.3%**",
    "- = tối ưu của riêng t = 1",
    "Budget không bao giờ chặt",
    "Đã kiểm tra lại: đường hợp lệ, 0 / 0 / 8 thay đổi ≤ κ(1)"], 14, bullets=True, space=9)

# ============ 16. quy mô ============
s = new_slide("Mô hình chính xác đi được bao xa?",
    "Đây là số biến nhị phân của mô hình một chu kỳ, thang log. Nó tăng theo số demand nhân n bình phương. Dựng mô hình "
    "bốn triệu rưỡi biến đã tốn 3.3 GB trong JuMP, và HiGHS cần thêm một bản sao, nên em dừng ở năm triệu. Bốn instance "
    "giải tối ưu, 04 dựng được nhưng chưa giải xong, 06, 08 và 09 sát giới hạn và chưa có kết quả, mười hai instance còn "
    "lại không dựng được. Có budget thì mô hình lớn gấp ba. Đó là lý do cần phương pháp 2.")
image(s, "scale.png", 0.35, 0.85, w=6.2)
text(s, 6.75, 0.95, 2.8, 3.8, [
    "Kích thước ≈ |D| · n² biến nhị phân mỗi chu kỳ",
    "4.5·10^{6} biến = 3.3 GB trong JuMP, + bản sao trong HiGHS → giới hạn 5·10^{6}",
    "Tối ưu: **4 / 20** tại t = 0, **3 / 20** có budget",
    "Nút thắt là bộ nhớ và LP gốc, không phải phân nhánh",
    "→ *Phương pháp 2*"], 14, bullets=True, space=9)

# ============ 16b. kết quả phương pháp 2 ============
cg = []
for ln in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "table_cg.tex")):
    c = [x.strip() for x in ln.replace("\\\\", "").replace("\\%", "%").split("&")]
    if len(c) == 12: cg.append(c)
assert len(cg) == 20, len(cg)
st = lambda x: x.replace("Optimal", "Opt.").replace("N.Opt.", "Chưa").replace("Opt.", "Tối ưu")
s = new_slide("Phương pháp 2: cả 20 instance, MLU tốt nhất đã biết",
    "Phương pháp 2 giải được cả hai mươi instance trong giới hạn thời gian; lần chạy lâu nhất mất 1097 giây cho một chu kỳ "
    "và 1225 giây cho hai chu kỳ, dùng 1.3 đến 2 GB bộ nhớ. Với hai chu kỳ, MLU bằng kết quả tốt nhất của 53 đội ở vòng "
    "sprint của challenge trên cả hai mươi instance. MLU trung bình trên SetA giảm từ 0.989 xuống "
    "0.572. Tối ưu được chứng minh ở 12 instance với một chu kỳ và 13 instance với hai chu kỳ.")
rows = [["Inst", "Obj t=0", "Trạng thái", "Obj t∈{0,1}", "CPU (s)", "Trạng thái", "Gap", "Tốt nhất"]]
for c in cg:
    rows.append([c[0], c[1], st(c[3]), c[6], c[7], st(c[8]), c[9], c[11]])
text(s, 1.0, 0.68, 1.6, 0.22, "1800 s", 9, MUTED, align="c")
text(s, 2.6, 0.68, 3.0, 0.22, "hai chu kỳ + budget, 3600 s", 9, MUTED, align="c")
table(s, 0.45, 0.88, 6.05, rows, [0.45, 0.72, 0.78, 0.85, 0.65, 0.95, 0.62, 0.75], size=8.5, rowh=0.178,
      align="lrlrrlrr", bold_cells={(i, 7) for i in range(1, 21)})
big = [("20 / 20", "MLU hai chu kỳ = tốt nhất challenge\n(53 đội, vòng sprint), cả 10 seed"),
       ("0.989 → 0.572", "MLU trung bình trên SetA so với PP1\n(phần lớn là nghiệm không waypoint)"),
       ("12 + 13", "chứng minh tối ưu: t = 0 / hai chu kỳ"),
       ("≤ 2 GB", "≤ 23 000 cột, lần chạy lâu nhất 1225 s")]
for k, (b, lab) in enumerate(big):
    y = 0.85 + k * 0.98
    text(s, 6.75, y, 2.85, 0.45, b, 22 if k else 26, RED if k == 0 else INK, bold=True)
    text(s, 6.75, y + 0.43, 2.85, 0.45, lab.split("\n"), 10, MUTED, space=0)
footnote(s, "Trung bình 10 lần chạy. Tối ưu: gap ≤ 10^{−4}. Tốt nhất: MLU tốt nhất vòng sprint ROADEF/EURO 2026 (GitLab của Orange).")

s = new_slide("Phương pháp 1 và phương pháp 2",
    "Hai phương pháp bổ sung cho nhau. Phương pháp 1 là mô hình của đề và chứng minh được tối ưu ở instance nhỏ. Phương "
    "pháp 2 giải được instance lớn và cho cận để đánh giá nghiệm. Khi phương pháp 2 chưa đóng được gap, nguyên nhân là cận "
    "yếu chứ không phải nghiệm kém. Ở setA-03 gap là 32.8 phần trăm, nhưng phương pháp 1 đã chứng minh 0.943543 là tối ưu: "
    "instance chỉ có 20 demand, trong đó có demand lớn, và nới lỏng LP cho phép chia một demand ra nhiều đường, nên cận "
    "thấp hơn nhiều.")
rows = [["", "PP1: MILP đầy đủ", "PP2: sinh cột"],
        ["Số instance có nghiệm", "5 / 20", "20 / 20"],
        ["Chứng minh tối ưu, t = 0", "4", "12"],
        ["Chứng minh tối ưu, hai chu kỳ", "3", "13"],
        ["MLU trung bình, hai chu kỳ", "0.989", "0.572"],
        ["Bộ nhớ", "> 3 GB với 4.5·10^{6} biến", "1.3–2 GB"],
        ["Cận dưới", "MILP (chặt ngay ở gốc)", "Lagrange / một demand"]]
table(s, 0.45, 0.9, 9.1, rows, [2.8, 2.5, 2.5], size=14, rowh=0.38, align="lll", bold_cells={(i, 2) for i in range(1, 5)})
text(s, 0.45, 3.75, 9.1, 1.0, [
    "Gap còn lại của PP2 do *cận yếu*, không phải nghiệm kém",
    "- setA-03: gap 32.8%, nhưng PP1 chứng minh 0.943543 tối ưu (20 demand, có demand lớn mà LP chia nhỏ được)",
    "PP1 xác nhận tối ưu ở instance nhỏ, PP2 mở rộng và cho cận cho phần còn lại"], 14, bullets=True, space=5)

# ============ 17. kết luận ============
s = new_slide("Kết luận",
    "Tóm lại: em đã cài đặt MILP của đề với hệ số chia luồng ECMP và budget tuyến tính hoá, cho kết quả đúng trên instance "
    "toy. Trên SetA, mô hình giải tối ưu bốn instance với một chu kỳ, MLU giảm tới 65 phần trăm, và ba instance với hai chu "
    "kỳ; giới hạn là kích thước. Sinh cột trên mô hình theo đường đi giải được cả hai mươi instance, bằng MLU tốt nhất "
    "của vòng sprint trên tất cả, và chứng minh tối ưu ở mười ba instance. Hướng tiếp theo: làm chặt cận bằng "
    "branch-and-price, loại các đường bị trội, và xử lý mục tiêu lexicographic đầy đủ.")
text(s, 0.45, 0.82, 4.4, 0.4, "Đã làm được", 17, RED, bold=True)
text(s, 0.45, 1.25, 4.4, 3.5, [
    "MILP chính xác của T-ASR bằng Julia / JuMP / HiGHS",
    "Hệ số chia luồng ECMP, budget tuyến tính hoá, bộ kiểm tra nghiệm",
    "Đúng trên instance toy (vét cạn)",
    "PP1 trên SetA: 4 tối ưu tại t = 0 (MLU giảm tới 65%), 3 có budget; giới hạn |D| · n²",
    "PP2 (sinh cột): giải *cả 20*, = tốt nhất challenge ở cả 20, 13 chứng minh tối ưu"], 14, bullets=True, space=8)
text(s, 5.1, 0.82, 4.45, 0.4, "Hướng phát triển", 17, RED, bold=True)
text(s, 5.1, 1.25, 4.45, 3.5, [
    "Làm chặt cận khi có ít demand lớn: branch-and-price thay cho MILP trên tập cột cố định",
    "Loại các segment path bị trội [Callebaut et al. 2023]",
    "Mục tiêu lexicographic đầy đủ: STELA, ALEXA [Benhamiche et al. 2026], trên tập cột đã sinh"], 14, bullets=True, space=8)

retext(thanks, "THANK YOU!", "CẢM ƠN!")
retext(thanks, "THANK YOU", "CẢM ƠN")
retext(thanks, "Questions and discussion", "Hỏi đáp và thảo luận")
thanks.notes_slide.notes_text_frame.text = "Em xin cảm ơn thầy cô và các bạn đã lắng nghe. Em sẵn sàng trả lời câu hỏi."
for sid in list(sldIdLst):
    if prs.part.related_part(sid.rId) is thanks.part:
        sldIdLst.remove(sid); sldIdLst.append(sid)

# bỏ mọi đổ bóng: effectRef của style hình/đường và effectLst có sẵn trong template
def strip_shadows(slide):
    root = slide._element
    for e in root.iter(qn("a:effectRef")): e.set("idx", "0")
    for lst in root.iter(qn("a:effectLst")):
        for ch in list(lst): lst.remove(ch)
for sl in prs.slides: strip_shadows(sl)
for k, sl in enumerate(prs.slides, 1):
    sl.part.partname = PackURI(f"/ppt/slides/slide{k}.xml")
prs.save(OUT)
print("saved", OUT, len(prs.slides))
