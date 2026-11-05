"""Orange T-ASR deck on the HUST template.  usage: build_slides.py template.pptx figdir out.pptx

template.pptx: the HUST template or a previous build (cover, title, outline, ..., thanks).
Results of Method 2 are read from report/table_cg.tex."""
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

# ============ 1-3: cover, title, outline ============
cover.notes_slide.notes_text_frame.text = "Good morning. Our project is the Orange problem of the EURO/ROADEF Challenge 2026."
sh = {s.name: s for s in title_sl.shapes}
set_text(sh["Google Shape;84;p16"], ["Keep The Flow!", "T-Adaptive Segment Routing: MILP and column generation"])
set_text(sh["Google Shape;85;p16"], ["Mathematical Modeling  ·  EURO/ROADEF Challenge 2026"])
set_text(sh["Google Shape;86;p16"], ["Lê Phạm Thuỷ Tiên  20261075M"])
title_sl.notes_slide.notes_text_frame.text = (
    "We model Orange's T-Adaptive Segment Routing problem as a MILP, then as a path model solved by column generation, "
    "and test both with HiGHS on the 20 SetA instances.")
sh = {s.name: s for s in outline_sl.shapes}
for a, b, t1 in [("96", "97", "Problem"), ("100", "101", "Related work"), ("104", "105", "Our approach"),
                 ("108", "109", "Results"), ("112", "113", "Conclusion")]:
    set_text(sh[f"Google Shape;{a};p17"], [t1])
    sh[f"Google Shape;{b};p17"].text_frame.clear()
outline_sl.notes_slide.notes_text_frame.text = "Five parts: the problem, related work, our approach, results, conclusion."

# ============ 4. context ============
s = new_slide("Why traffic engineering?",
    "Orange runs national IP backbones with thousands of routers and tens of thousands of demands. The picture is "
    "setA-20, one of the challenge networks. Traffic follows shortest paths for the operator's link weights. That is "
    "simple, but many flows end up on the same links, and re-tuning the weights is itself a hard problem. Links are also "
    "switched off for maintenance, which changes the shortest paths and moves the congestion.")
text(s, 0.45, 0.85, 5.1, 3.9, [
    "Orange operates national IP/MPLS backbones",
    "- thousands of routers, tens of thousands of demands",
    "Traffic follows **shortest paths** for link weights ω",
    "- simple to run, but flows pile up on a few links",
    "- re-tuning ω is itself NP-hard [1]",
    "Links are switched off for **maintenance**",
    "- shortest paths change, congestion moves",
    "Goal: keep the *most loaded link* as low as possible"], 17, bullets=True, space=12)
image(s, "setA20.png", 6.0, 0.8, h=3.75)
caption(s, 5.9, 4.45, 3.7, "setA-20: 400 routers, 2000 arcs")
footnote(s, "[1] B. Fortz, M. Thorup. Internet traffic engineering by optimizing OSPF weights. INFOCOM 2000.")

# ============ 5. segment routing ============
s = new_slide("Segment Routing: one waypoint is enough",
    "With Segment Routing the source writes a list of waypoints in the packet header. Between two waypoints the packet "
    "follows shortest paths, and ECMP splits the flow equally at each node when there are ties. On the toy instance of "
    "the subject, shortest paths put 0.4375 of capacity on arc v3 to v5. Sending demand v0 to v5 through waypoint v4 "
    "spreads the load and the maximum drops to 0.375, which is optimal.")
text(s, 0.45, 0.78, 9.1, 0.65,
     "The source writes a list of *waypoints* in the packet header. Between two waypoints, packets follow "
     "shortest paths; ties are split equally at each node (ECMP).", 16)
image(s, "toy_default.png", 0.45, 1.55, w=4.35)
image(s, "toy_sr.png", 5.2, 1.55, w=4.35)
caption(s, 0.45, 4.3, 4.35, "(a) shortest paths only — MLU = 0.4375")
caption(s, 5.2, 4.3, 4.35, "(b) demand (v₀, v₅) via waypoint v₄ — MLU = 0.375")
footnote(s, "Toy instance of the subject, t = 0. Arc labels: load / capacity; red = most loaded arcs.")

# ============ 6. problem ============
s = new_slide("The T-ASR problem",
    "Formally, the T-Adaptive Segment Routing problem gives us a directed network with weights and capacities, demands "
    "whose volume changes over the periods, a maintenance schedule, a maximum number of segments, and a budget on how "
    "many segments can change between two periods. We choose a segment path for each demand and period. The subject "
    "uses a lexicographic objective; we minimise its first term, the maximum link utilisation. The problem is NP-hard "
    "and hard to approximate even on simple topologies.")
rows = [("Given", ["directed network G = (V, A), weights ω(a), capacities c(a)",
                   "demands d = (s_{d}, t_{d}) with volume ν(d, t), periods t = 0, …, h−1",
                   "maintenance: arcs q(t) switched off at period t",
                   "at most maxSeg segments per path, budget κ(t) on changes"]),
        ("Find", ["a segment path ⟨s_{d}, w_{1}, …, t_{d}⟩ for every demand and every period"]),
        ("Minimize", ["MLU = max_{a, t}  load(a, t) / c(a)"])]
y = 0.95
for lab, lines in rows:
    text(s, 0.45, y, 1.3, 0.35, lab, 17, RED, bold=True)
    text(s, 1.8, y, 7.7, 0.35 * len(lines), lines, 16, space=4)
    y += 0.36 * len(lines) + 0.25
hline(s, 0.45, y - 0.05, 9.55, "D5D8DC")
text(s, 0.45, y + 0.05, 9.1, 0.8, [
    "The subject uses a lexicographic objective on all loads; MLU is its first and main term.",
    "NP-hard and hard to approximate, even on very simple topologies [2]."], 14, MUTED, space=4)
footnote(s, "[2] C. Bazgan, M. Chopin, A. Nichterlein, C. Richer. Parameterized complexity of segment routing. INFOCOM 2025.")

# ============ 7a. related work: timeline ============
s = new_slide("Related work: 25 years of traffic engineering",
    "A short history. In 2000 Fortz and Thorup showed that tuning OSPF weights is NP-hard and proposed local search. "
    "Segment Routing changed the question: in 2015 Bhatia et al. showed that two segments, so one waypoint, are almost "
    "enough to balance the load, and Hartert et al. built DEFO, the first centralized SR optimizer. Gay et al. then "
    "re-optimized large ISP networks in under a second with local search. SR was standardized in RFC 8402 in 2018, and "
    "CG4SR brought column generation in 2019. Later work combined weights and segments, and preprocessing removed "
    "dominated paths. In 2025 Bazgan et al. settled the complexity. The time-dependent version with a budget on changes "
    "only appears in 2026, with this challenge.")
ev = [("2000", "Fortz & Thorup", "OSPF weights:\nNP-hard"),
      ("2015", "Bhatia et al.", "2 segments are\nalmost enough"),
      ("2015", "Hartert et al.", "DEFO, first SR\noptimizer"),
      ("2017", "Gay et al.", "sub-second\nlocal search"),
      ("2018", "RFC 8402", "SR\nstandardized"),
      ("2019", "Jadin et al.", "CG4SR: column\ngeneration"),
      ("2021", "Parham et al.", "weights +\nsegments jointly"),
      ("2023", "Callebaut et al.", "remove dominated\npaths"),
      ("2025", "Bazgan et al.", "parameterized\ncomplexity"),
      ("2026", "Benhamiche; Jaumard", "T-ASR: time +\nbudget")]
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
     "Changes over time with a *budget on reconfigurations* only appear in 2026, with this challenge.", 14)

# ============ 7b. related work: static SR-TE ============
s = new_slide("Related work: three families of methods",
    "For the static problem, one period, three families exist. Exact models: MILP or ILP formulations like DEFO, "
    "Schüller et al. and Li and Yeung. They give optimal solutions and bounds, but they have about D times V squared "
    "variables. Column generation, as in CG4SR: a master LP picks segment paths and a pricing problem finds a new path "
    "with negative reduced cost; with at most maxSeg segments, pricing is a shortest path with a bounded number of arcs, "
    "solved by dynamic programming. And heuristics: local search changes few paths and runs in under a second, while "
    "Bhatia et al. and Pereira et al. restrict paths to two or three segments. Our Method 1 is in the first family, "
    "Method 2 in the second.")
fam = [("Exact: MILP / ILP", "DEFO 2015 · Schüller et al. 2018 · Li & Yeung 2020",
        ["Optimal solution and a bound", "≈ |D| · |V|^{2} binaries", "Size limited by memory"]),
       ("Column generation", "CG4SR 2019 · Jaumard et al. 2026",
        ["Master LP picks one path per demand", "Pricing: path with ≤ maxSeg arcs (DP)", "Near optimal, LP bound"]),
       ("Heuristics", "Gay et al. 2017 · Bhatia et al. 2015 · Pereira et al. 2020",
        ["Local search: few changes, sub-second", "Restrict to 2 or 3 segments", "No bound"])]
for k, (h, refs, pts) in enumerate(fam):
    x = 0.45 + k * 3.1
    if k < 2:
        frame(s, x - 0.08, 0.85, 3.0, 3.75, RED, 1.25)
    text(s, x, 0.95, 2.85, 0.35, h, 17, RED, bold=True)
    text(s, x, 1.33, 2.85, 0.55, refs, 11.5, MUTED, italic=True)
    text(s, x, 2.0, 2.85, 2.0, pts, 15, bullets=True, space=10)
    if k < 2:
        text(s, x, 4.05, 2.85, 0.35, ["Our Method 1", "Our Method 2"][k], 13, RED, bold=True)
text(s, 0.45, 4.72, 9.1, 0.3, "Before 2026 all of them handle one period; T-ASR adds periods, maintenance and a change budget.", 13, MUTED)

# ============ 7c. related work: T-ASR papers ============
s = new_slide("Related work: the two T-ASR papers (2026)",
    "Two papers work on T-ASR itself. Benhamiche et al., the authors of the challenge, give exactly the model we use. "
    "They handle the lexicographic objective with a sequence of MILPs, ALEXA and STELA; STELA wins on 109 of 115 "
    "instances, and the first step of both is min MLU, which is what we solve. They also show that with a budget the best "
    "path may contain a loop, so preprocessing for one period does not carry over. Their tests use small instances, up "
    "to 50 nodes. Jaumard et al. use the MLU and the budget like us, but solve period by period, which makes the budget "
    "linear, and use column generation. They are the only ones with results on all of SetA: the LP–ILP gap is 3.12 "
    "percent on average at t equals 0 but 13.05 percent at t equals 1, so the second period is clearly harder.")
text(s, 0.45, 0.82, 4.4, 0.35, "Benhamiche et al. — the subject's authors", 16, RED, bold=True)
text(s, 0.45, 1.25, 4.4, 3.4, [
    "Same model (1)–(4) as ours",
    "Lexicographic objective by a sequence of MILPs",
    "-ALEXA (permutations, big-M), STELA (thresholds)",
    "-STELA better on 109 / 115 instances",
    "-step 1 of both = min MLU",
    "With a budget, the best path may need a *loop*",
    "Tests: setAP, 10–50 nodes, Gurobi, 20 min"], 14, bullets=True, space=7)
text(s, 5.1, 0.82, 4.45, 0.35, "Jaumard, Tran, Ziazet", 16, RED, bold=True)
text(s, 5.1, 1.25, 4.45, 1.9, [
    "MLU + budget, like us",
    "Period by period: t − 1 fixed → budget is linear",
    "Column generation, then ILP on the columns",
    "Only results on *all of SetA*"], 14, bullets=True, space=7)
for k, (big, lab) in enumerate([("3.12%", "mean LP–ILP gap, t = 0"), ("13.05%", "mean LP–ILP gap, t = 1")]):
    x = 5.25 + k * 2.15
    text(s, x, 3.25, 2.0, 0.55, big, 28, RED if k else INK, bold=True, align="c")
    text(s, x, 3.82, 2.0, 0.3, lab, 11.5, MUTED, align="c")
text(s, 5.1, 4.2, 4.45, 0.3, "→ the budget makes period t = 1 much harder", 13, INK, italic=True)
footnote(s, "Benhamiche et al., On the T-ASR problem, arXiv:2609.32896.   Jaumard et al., SR-TE with time-based reconfiguration constraints, arXiv:2610.04759.")

# ============ 7d. related work: comparison ============
s = new_slide("Where our work stands",
    "This table puts the approaches side by side. The full MILP is exact and gives a gap, handles the budget directly, "
    "but only scales to small instances. Solving period by period gives bounds for each subproblem but no global optimum. "
    "Column generation scales to all of SetA with an LP bound. Local search is very fast but has no bound, and restricting "
    "to two segments gives a smaller model. We do two of these: Method 1 is the full MILP of the subject, to get true "
    "optimal values and see where it stops; Method 2 is a path model with column generation that solves the two periods "
    "together, to reach all of SetA.")
cmp_rows = [["Approach", "Optimal", "Bound", "Budget", "Scale", "Key papers"],
            ["Full MILP", "yes", "yes", "yes, (4)", "small", "Benhamiche 2026"],
            ["Period by period + MILP", "per period", "per period", "yes", "medium", "Benhamiche; Jaumard 2026"],
            ["Column generation", "near", "LP bound", "yes", "large", "CG4SR 2019, Jaumard 2026"],
            ["Local search", "no", "no", "few changes", "very large", "Gay 2017, Hartert 2018"],
            ["2 segments only", "no", "on submodel", "yes", "large", "Bhatia 2015"],
            ["Method 1: full MILP", "yes", "MILP gap", "yes, (4)", "≤ 5·10^{6} vars", "subject's MILP, HiGHS"],
            ["Method 2: path CG", "14 / 20", "Lagrange", "yes, exact", "all 20", "both periods jointly"]]
table(s, 0.45, 0.85, 9.1, cmp_rows, [2.3, 1.05, 1.15, 1.1, 1.35, 2.35], size=13, rowh=0.38, red_rows=(6, 7),
      align="llllll")
text(s, 0.45, 4.05, 9.1, 0.7, [
    "Method 1: *true optimal values and gaps* with an open-source solver — how far does the exact model go?",
    "Method 2: the same problem on *all of SetA*, two periods at once, with a lower bound"], 14, space=3)

# ============ 8. approach overview ============
s = new_slide("Our approach",
    "Our pipeline has five steps. We read the network, the traffic matrix and the scenario. We precompute the flow ratios "
    "r. Then either Method 1, the full MILP in JuMP, or Method 2, a path model solved by column generation; both use "
    "HiGHS. Finally we read the segment paths back and recompute loads and changes. The key point is that r depends only "
    "on the graph, so the load of an arc is a linear function of the decision variables.")
steps = [("Instance", "net, tm, scenario\n(JSON)"), ("Flow ratios r", "Dijkstra + ECMP,\nall node pairs"),
         ("Model", "M1: full MILP\nM2: path model"), ("Solve", "HiGHS; M2 adds\ncolumn generation"),
         ("Check", "paths, loads,\nbudget")]
for k, (h, sub) in enumerate(steps):
    x = 0.45 + k * 1.86
    frame(s, x, 1.0, 1.5, 0.55, RED if k in (1, 2) else RULE, 1.25 if k in (1, 2) else 0.75)
    text(s, x, 1.0, 1.5, 0.55, h, 15, RED if k in (1, 2) else INK, bold=True, align="c", anchor="m")
    text(s, x - 0.1, 1.62, 1.7, 0.55, sub.split("\n"), 12, MUTED, align="c", space=0)
    if k < 4: arrow(s, x + 1.53, 1.275, x + 1.83, 1.275)
text(s, 0.45, 2.55, 9.1, 2.2, [
    "r(i, j, a, t) depends only on the graph of period t, not on the routing",
    "- computed once, before the solver; the load of every arc becomes *linear* in x",
    "Method 1: exact model of the subject, objective min MLU",
    "- warm start without waypoints (always feasible), so every run has an upper bound",
    "Method 2: same optimum, but only the paths that matter are generated",
    "- ~10^{4} columns instead of up to 9.6·10^{8} binaries"], 16, bullets=True, space=8)

# ============ 9. flow ratios ============
s = new_slide("Flow ratios r(i, j, a, t)",
    "r of i, j, a, t is the share of one unit of flow from i to j that crosses arc a in the graph of period t. Every node "
    "can be a waypoint, so we need it for all pairs. We run Dijkstra from every node, mark the arcs that lie on a shortest "
    "path, and push one unit of flow in topological order, splitting it equally at each node. With real-valued weights the "
    "test needs a tolerance. The picture is demand v0 to v5 of the toy instance: 0.5, 0.5 and 0.75 on arc v3 v5, as in "
    "Table 2 of the subject. The guide's formula that counts shortest paths gives one third, two thirds and two thirds "
    "instead, because it splits per path and not per node.")
text(s, 0.45, 0.8, 4.6, 0.65, "Share of one unit of flow from i to j that crosses arc a in G_{t} = (V, A ∖ q(t)).", 15)
lines = ["Dijkstra from every node → d_{ij}",
         "a = (u, v) is on a shortest i–j path iff d_{iu} + ω(a) + d_{vj} = d_{ij}",
         "Push one unit from i in decreasing d_{·j}; split equally at each node"]
tb = text(s, 0.45, 1.55, 4.6, 2.0, lines, 15, space=10)
for p in tb.text_frame.paragraphs:
    pPr = p._p.get_or_add_pPr(); pPr.set("marL", "285750"); pPr.set("indent", "-285750")
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "+mj-lt")
    etree.SubElement(pPr, qn("a:buAutoNum")).set("type", "arabicPeriod")
text(s, 0.45, 3.45, 4.6, 1.2, [
    "Real-valued weights (setA-05, 08, 12, 14): compare with relative tolerance 10^{−9}.",
    "Counting shortest paths (σ_{iu}σ_{vj}/σ_{ij}) splits per *path*, not per node: 1/3, 2/3, 2/3 here."], 13, MUTED, space=6)
image(s, "toy_ecmp.png", 5.3, 0.95, w=4.25)
caption(s, 5.3, 3.8, 4.25, "r(v₀, v₅, a) on the toy instance — same as Table 2 of the subject")

# ============ 10. model ============
s = new_slide("MILP formulation",
    "We see every node pair i, j as a virtual arc, so a segment path for demand d is a path from its source to its "
    "destination in the complete graph. x says whether demand d uses segment i, j at period t, and U is the maximum "
    "utilisation. Constraint one: one segment path per demand. Two: the header size. Three: the load of each arc, linear "
    "because r and the volumes are data. Four: the budget; the absolute value of the change is linearised with y.")
text(s, 0.45, 0.78, 9.1, 0.4,
     "Node pairs (i, j) are virtual arcs: a segment path is a path from s_{d} to t_{d}.   x^{dt}_{ij} = 1 if demand d uses segment (i, j) at t.", 14)
image(s, "model.png", 1.55, 1.3, h=2.95)
text(s, 0.45, 4.35, 9.1, 0.5,
     "(1) one segment path per demand   (2) header size   (3) arc load — linear, r and ν are data   (4) budget, |x^{t} − x^{t−1}| linearized",
     12, MUTED)
footnote(s, "One period (t = 0): (1)–(3).   Two periods with budget: (1)–(4).")

# ============ 11. validation ============
s = new_slide("Is the model right?",
    "We first checked the model on the toy instance. Without waypoints the MLU at period zero is 0.4375; the model finds "
    "0.375, the solution shown in Figure 4 of the subject, and 0.375 at period one as well. Enumerating all 206 segment paths "
    "per demand gives the same optima. Three details caught us during the implementation: floating-point distances, "
    "disjoint cycles that constraint one does not forbid, and the fact that min MLU only cares about the worst period.")
text(s, 0.45, 0.82, 4.3, 0.4, "Toy instance", 17, RED, bold=True)
text(s, 0.45, 1.25, 4.3, 3.0, [
    "t = 0: 0.4375 → **0.375** (Figure 4 of the subject)",
    "t = 1: **0.375**, budget κ(1) = 20 not binding",
    "Brute force over all 206 segment paths per demand: same optima"], 15, bullets=True, space=10)
text(s, 5.1, 0.82, 4.45, 0.4, "Three things that bit us", 17, RED, bold=True)
text(s, 5.1, 1.25, 4.45, 3.3, [
    "**Floating-point distances**",
    "- with ==, more than half of the node pairs lose flow on setA-08, 12, 14",
    "**Disjoint cycles**",
    "- (1) allows x_{ij} = x_{ji} = 1; we read paths with an Euler walk and recompute loads and budget",
    "**min MLU looks at one period only**",
    "- the other period can stay high"], 15, bullets=True, space=10)

# ============ 11b. method 2 ============
s = new_slide("Method 2: path model and column generation",
    "The full MILP has about D times n squared binaries, so we rewrite it on paths. A column is a whole segment path p "
    "of a demand, with load L of p on each arc, the sum of r over its segments; choosing a path is the same as setting x "
    "on its segments, so the optimum is the same. The restricted master is the LP over the paths generated so far, "
    "starting from the direct path. Pricing: with the duals w on the load constraints, the cost of a path adds up over "
    "its segments, so finding a negative reduced cost path is a shortest path with at most maxSeg arcs on the complete "
    "graph, solved by a Bellman-Ford style dynamic program. Any w gives a Lagrangian lower bound. For two periods a "
    "column is a pair of paths, and its budget cost is the number of segments in exactly one of them, so the budget "
    "becomes an exact linear constraint, with no y variables. Finally a MILP on the generated columns, plus a repair "
    "loop around the most loaded arcs, gives the integer solution.")
text(s, 0.45, 0.78, 9.1, 0.4,
     "Column = a whole segment path p of demand d.   L_{t}(p, a) = Σ_{(i,j) ∈ p} r(i, j, a, t)   — same optimum as the MILP.", 14)
loop = [("Master LP", "paths generated so far\nstart: direct path ⟨s_{d}, t_{d}⟩"),
        ("Pricing", "shortest path with ≤ maxSeg arcs\nW(i, j) = Σ_{a} r(i, j, a) w_{a}  (DP)"),
        ("Integer", "MILP on the columns\n+ repair of the hottest arcs")]
for k, (h, sub) in enumerate(loop):
    x = 0.45 + k * 3.15
    frame(s, x, 1.35, 2.75, 0.5, RED if k < 2 else RULE, 1.25 if k < 2 else 0.75)
    text(s, x, 1.35, 2.75, 0.5, h, 15, RED if k < 2 else INK, bold=True, align="c", anchor="m")
    text(s, x - 0.1, 1.92, 2.95, 0.6, sub.split("\n"), 11.5, MUTED, align="c", space=0)
    if k < 2: arrow(s, x + 2.78, 1.6, x + 3.12, 1.6)
text(s, 3.2, 2.55, 3.0, 0.3, "duals w_{a} → new path if reduced cost < 0", 11, MUTED, italic=True, align="c")
text(s, 0.45, 2.95, 9.1, 1.8, [
    "**Lower bound** at every round: Lagrangian bound LB(w) and the “single demand” bound",
    "**Two periods**: column = pair (p_{0}, p_{1}); budget cost Δ = |S(p_{0}) △ S(p_{1})| segments",
    "- (4) becomes the exact linear constraint Σ Δ λ ≤ κ — no y, both periods optimised together",
    "Gap = 1 − LB / UB, “optimal” = gap ≤ 10^{−4} (HiGHS default mip_rel_gap)"], 14, bullets=True, space=6)
footnote(s, "Pricing as in CG4SR: M. Jadin, F. Aubry, P. Schaus, O. Bonaventure, INFOCOM 2019.")

# ============ 12. setup ============
s = new_slide("Experimental setup",
    "SetA has 20 instances, from 20 to 400 nodes and from 20 to 6000 demands. All have two periods, at most six segments "
    "and one arc down at period one. All runs are on an 8-core Xeon server with 63 GB of RAM, inside Docker, with Julia, "
    "JuMP and HiGHS, a time limit of 1800 seconds for one period and 3600 for two. Method 1 uses a higher heuristic effort "
    "and a warm start, ten seeds when it solves in under 300 seconds, one otherwise; models above five million variables "
    "are not built. Method 2 splits its time between column generation, the MILP on the columns and the repair loop, and "
    "always runs ten seeds.")
text(s, 0.45, 0.82, 4.4, 0.4, "Instances: SetA (20)", 17, RED, bold=True)
text(s, 0.45, 1.25, 4.4, 3.4, [
    "20–400 nodes, 80–2000 arcs",
    "20–6000 demands",
    "h = 2 periods, maxSeg = 6",
    "one arc switched off at t = 1",
    "budget κ(1) between 1 and 90",
    "binary variables: 1.5·10^{4} to 9.6·10^{8} per period"], 15, bullets=True, space=8)
text(s, 5.1, 0.82, 4.45, 0.4, "Runs", 17, RED, bold=True)
text(s, 5.1, 1.25, 4.45, 3.5, [
    "Xeon 2.2 GHz, 8 cores / 16 threads, 62.8 GB, Docker",
    "Julia 1.13.2, JuMP 1.32.1, HiGHS 1.15.1",
    "Limit 1800 s (t = 0), 3600 s (two periods)",
    "**M1**: heuristic effort 0.3, warm start",
    "- 10 seeds if solved < 300 s, else 1; > 5·10^{6} vars not built",
    "**M2**: CG 600 s + MILP 300 s + repair",
    "- 10 seeds (0–9), 8 runs × 2 threads in parallel"], 14, bullets=True, space=5)

# ============ 13. step 6 ============
s = new_slide("One period (t = 0): up to 65% lower MLU",
    "With one period, the model proves optimality on 01, 02, 03 and 05. The MLU drops by 7.1, 45.1, 5.6 and 65.3 percent "
    "compared with shortest paths. All seeds give the same optimum but the time varies a lot. The tree has zero or one "
    "node: the root bound is already tight, and the time goes into the root LP and into finding a matching integer "
    "solution. On 04 the solver does not improve the warm start in 1800 seconds.")
image(s, "step6.png", 0.35, 0.85, w=5.6)
text(s, 6.15, 0.95, 3.4, 3.8, [
    "Optimal on 01, 02, 03, 05",
    "- MLU −7.1%, −45.1%, −5.6%, −65.3%",
    "0–1 branch-and-bound nodes",
    "- root bound already tight; time goes to the root LP and to finding a matching solution",
    "Time depends on the seed",
    "- setA-01: 4.5 ± 8.9 s",
    "04: no improvement in 1800 s (gap 33.6%)"], 15, bullets=True, space=9)

# ============ 14. no loops ============
s = new_slide("Forbidding loops: faster, but not always",
    "With one period we can also forbid a segment path from visiting a node twice; this keeps the optimum because "
    "removing a loop never increases a load. It makes 01 to 03 four to nineteen times faster and finds 0.4791 on 04 "
    "instead of 0.6918, so the optimum of 04 is between 0.4591 and 0.4791; Method 2 later finds 0.4591, so that is "
    "the optimum up to 0.01 percent. But on 05 HiGHS does not finish the root LP. "
    "Since the effect is mixed, the main results use the subject's model. With a budget the variant is not valid.")
rows = [["", "Obj", "CPU (s)", "Gap", "Obj", "CPU (s)", "Gap"],
        ["setA-01", "0.9294", "4.5", "0", "0.9294", "0.6", "0"],
        ["setA-02", "0.5486", "318.0", "0", "0.5486", "16.4", "0"],
        ["setA-03", "0.9435", "58.2", "0", "0.9435", "13.6", "0"],
        ["setA-04", "0.6918", "1800", "33.6%", "0.4791", "1800", "4.2%"],
        ["setA-05", "0.1155", "1706", "0", "0.3333", "6037", "–"]]
text(s, 1.75, 0.85, 3.6, 0.3, "Subject's model (1)–(3)", 13, MUTED, align="c")
text(s, 5.55, 0.85, 3.6, 0.3, "+ each node at most once", 13, MUTED, align="c")
hline(s, 1.85, 1.17, 5.25, MUTED); hline(s, 5.65, 1.17, 9.05, MUTED)
table(s, 0.45, 1.22, 8.7, rows, [1.3, 1.2, 1.2, 1.2, 1.2, 1.2, 1.2], size=14, rowh=0.36,
      bold_cells={(1, 5), (2, 5), (3, 5), (4, 4), (5, 1)})
text(s, 0.45, 3.55, 9.1, 1.3, [
    "**4–19× faster** on 01–03; setA-04: 0.6918 → 0.4791, bound 0.4591 — Method 2 reaches *0.4591*",
    "setA-05: no root LP after 6037 s — so the main tables keep the subject's model",
    "Not valid with a budget: the best path may need a loop"], 14, bullets=True, space=6)

# ============ 15. step 9 ============
s = new_slide("Two periods with a budget",
    "With two periods and a budget, the model is about three times larger; only 01 to 05 can be built and 01 to 03 are "
    "solved. On 01 and 03 the result equals the period-zero optimum: period zero is the bottleneck. On 02 the default "
    "routing overloads a link at 109.8 percent in period one, and the model brings it to 0.9031, the optimum of period one "
    "alone. So in no case is the budget the limit. We rechecked the solutions: all paths valid, MLU equal to U, and 0, 0 "
    "and 8 changes, within the budget.")
rows = [["", "κ(1)", "MLU₀", "Obj", "CPU (s)", "Status"],
        ["setA-01", "51", "1.0000", "0.9294", "163.9", "optimal"],
        ["setA-02", "63", "1.0981", "0.9031", "172.4", "optimal"],
        ["setA-03", "53", "1.0000", "0.9435", "704.2", "optimal"],
        ["setA-04", "44", "1.0000", "1.0000", "9905*", "no LP bound"],
        ["setA-05", "1", "1.0000", "1.0000", "> 10800", "stopped"]]
table(s, 0.45, 0.95, 5.2, rows, [1.2, 0.7, 1.0, 1.0, 1.0, 1.3], size=14, rowh=0.38,
      bold_cells={(1, 3), (2, 3), (3, 3)})
text(s, 0.45, 3.32, 5.2, 0.6, ["MLU₀: no waypoint; Obj: max MLU over both periods.",
                               "* HiGHS overran the 3600 s limit inside the root LP."], 11, MUTED, space=2)
text(s, 5.95, 0.95, 3.6, 3.8, [
    "01, 03: same as t = 0 alone",
    "- period 0 is the bottleneck",
    "02: overload 109.8% at t = 1 → **90.3%**",
    "- = optimum of t = 1 alone",
    "The budget never binds",
    "Solutions rechecked: paths valid, 0 / 0 / 8 changes ≤ κ(1)"], 15, bullets=True, space=9)

# ============ 16. scalability ============
s = new_slide("How far does the exact model go?",
    "This is the number of binary variables of the one-period model, on a log scale. It grows like the number of demands "
    "times n squared. Building a model of four and a half million variables already takes 3.3 GB in JuMP, and HiGHS "
    "needs a second copy, so we stop at five million. Four instances are solved, 04 is built but not solved, 06, 08 and 09 "
    "sit at the limit with no result, and the other twelve are not built. With the budget the model is three times larger. "
    "This is why we need Method 2.")
image(s, "scale.png", 0.35, 0.85, w=6.2)
text(s, 6.75, 0.95, 2.8, 3.8, [
    "Size ≈ |D| · n² binaries per period",
    "4.5·10^{6} vars = 3.3 GB in JuMP, + a copy in HiGHS → cap at 5·10^{6}",
    "Optimal: **4 / 20** at t = 0, **3 / 20** with budget",
    "The bottleneck is memory and the root LP, not branching",
    "→ *Method 2*"], 15, bullets=True, space=9)

# ============ 16b. method 2 results ============
cg = []
for ln in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "table_cg.tex")):
    c = [x.strip() for x in ln.replace("\\\\", "").replace("\\%", "%").split("&")]
    if len(c) == 12: cg.append(c)
assert len(cg) == 20, len(cg)
st = lambda x: x.replace("Optimal", "Opt.")
s = new_slide("Method 2: all 20 instances, best known MLU on all",
    "Method 2 solves all twenty instances within the time limits; the longest run takes 840 seconds for one period and "
    "1139 for two, with 1.3 to 2 GB of memory. With two periods, the MLU equals the best result of the 53 teams of the "
    "challenge sprint round on all twenty instances and in all ten runs. The mean MLU over SetA drops from 0.989 to 0.572. "
    "Optimality is proven on 12 instances for one period and 14 for two.")
rows = [["Inst", "Obj t=0", "Status", "Obj t∈{0,1}", "CPU (s)", "Status", "Gap", "Best"]]
for c in cg:
    rows.append([c[0], c[1], st(c[3]), c[6], c[7], st(c[8]), c[9], c[11]])
text(s, 1.0, 0.68, 1.6, 0.22, "1800 s", 9, MUTED, align="c")
text(s, 2.6, 0.68, 3.0, 0.22, "two periods + budget, 3600 s", 9, MUTED, align="c")
table(s, 0.45, 0.88, 5.95, rows, [0.5, 0.75, 0.7, 0.85, 0.7, 0.85, 0.65, 0.75], size=8.5, rowh=0.178,
      align="lrlrrlrr", bold_cells={(i, 7) for i in range(1, 21)})
big = [("20 / 20", "two-period MLU = challenge best\n(53 teams, sprint round), all 10 seeds"),
       ("0.989 → 0.572", "mean MLU over SetA vs Method 1\n(mostly no-waypoint routing)"),
       ("12 + 14", "proven optimal: t = 0 / two periods"),
       ("≤ 2 GB", "≤ 23 000 columns, longest run 1139 s")]
for k, (b, lab) in enumerate(big):
    y = 0.85 + k * 0.98
    text(s, 6.7, y, 2.9, 0.45, b, 22 if k else 26, RED if k == 0 else INK, bold=True)
    text(s, 6.7, y + 0.43, 2.9, 0.45, lab.split("\n"), 10.5, MUTED, space=0)
footnote(s, "Mean of 10 runs. Opt.: gap ≤ 10^{−4}. Best: best MLU of the ROADEF/EURO 2026 sprint round (Orange GitLab).")

s = new_slide("Method 1 vs Method 2",
    "The two methods complement each other. Method 1 is the subject's model and proves optimality on the small "
    "instances. Method 2 reaches the large ones and gives a bound to judge the solution. Where Method 2 does not close "
    "the gap, it is the bound that is weak, not the solution. On setA-03 the gap is 32.8 percent, but Method 1 proves "
    "that 0.943543 is optimal: there are only 20 demands, some of them large, and the LP relaxation can split a demand "
    "over several paths, so its bound is much lower.")
rows = [["", "Method 1: full MILP", "Method 2: path CG"],
        ["Instances with a solution", "5 / 20", "20 / 20"],
        ["Proven optimal, t = 0", "4", "12"],
        ["Proven optimal, two periods", "3", "14"],
        ["Mean MLU, two periods", "0.989", "0.572"],
        ["Memory", "> 3 GB at 4.5·10^{6} vars", "1.3–2 GB"],
        ["Bound", "MILP (tight at root)", "Lagrangian / single demand"]]
table(s, 0.45, 0.9, 9.1, rows, [2.6, 2.6, 2.6], size=14, rowh=0.38, align="lll", bold_cells={(i, 2) for i in range(1, 5)})
text(s, 0.45, 3.75, 9.1, 1.0, [
    "Remaining gaps of Method 2 come from a *weak bound*, not a bad solution",
    "- setA-03: gap 32.8%, yet Method 1 proves 0.943543 optimal — 20 demands, some large; the LP splits them",
    "Method 1 certifies small instances, Method 2 scales and bounds the rest"], 14, bullets=True, space=5)

# ============ 17. conclusion ============
s = new_slide("Conclusion",
    "To sum up: we implemented the subject's MILP with ECMP flow ratios and a linearised budget, and it is exact on the toy "
    "instance. On SetA it solves four instances with one period, with up to 65 percent lower MLU, and three with two "
    "periods; the limit is size. Column generation on the path model solves all twenty, matches the best MLU of the "
    "challenge sprint on all of them, and proves optimality on fourteen. Next: a tighter bound with branch-and-price, "
    "removing dominated paths, and the full lexicographic objective.")
text(s, 0.45, 0.82, 4.4, 0.4, "What we did", 17, RED, bold=True)
text(s, 0.45, 1.25, 4.4, 3.5, [
    "Exact MILP of T-ASR in Julia / JuMP / HiGHS",
    "ECMP flow ratios, linearized budget, solution checker",
    "Exact on the toy instance (brute force)",
    "M1 on SetA: 4 optimal at t = 0 (MLU up to −65%), 3 with budget; limit |D| · n²",
    "M2 (column generation): *all 20* solved, = challenge best on all 20, 14 proven optimal"], 15, bullets=True, space=8)
text(s, 5.1, 0.82, 4.45, 0.4, "Next steps", 17, RED, bold=True)
text(s, 5.1, 1.25, 4.45, 3.5, [
    "Tighter bound with few large demands: branch-and-price instead of a MILP on fixed columns",
    "Remove dominated segment paths [Callebaut et al. 2023]",
    "Full lexicographic objective: STELA, ALEXA [Benhamiche et al. 2026], on the generated columns"], 15, bullets=True, space=8)

thanks.notes_slide.notes_text_frame.text = "Thank you. We are happy to take questions."
for sid in list(sldIdLst):
    if prs.part.related_part(sid.rId) is thanks.part:
        sldIdLst.remove(sid); sldIdLst.append(sid)
for k, sl in enumerate(prs.slides, 1):
    sl.part.partname = PackURI(f"/ppt/slides/slide{k}.xml")
prs.save(OUT)
print("saved", OUT, len(prs.slides))
