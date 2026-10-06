"""Build the project report (LaTeX for Overleaf + MS Word) from one source file.

Source : report/src/report.md       (restricted Markdown, see "Source syntax" below)
Numbers: report/numbers.json        (written by scripts/export_report_numbers.py)
Refs   : report/src/references.json (written by scripts/check_references.py; only verified entries may be cited)

Output : report/overleaf/main.tex, references.bib, figures/   -> upload to Overleaf (pdfLaTeX + BibTeX)
         report/overleaf_upload.zip                           -> the same folder zipped
         report/figures/figNN_*.png|jpg + CAPTIONS.md          -> numbered figures on their own
         report/Project_Report_Revised.docx                   -> MS Word version

Source syntax
-------------
%% comment                          ignored
# Heading {#sec:label}              numbered heading (#, ##, ###); {-} = unnumbered
![Caption](file.png){#fig:label width=0.9}
Table: Caption {#tab:label cols=LRRR}   followed by a pipe table; {-} = no caption/number
$$ latex $$ || plain-text version   display equation
- item / 1. item                    lists
**bold**  *italic*  `code`  [@key1; @key2]  @key  [[fig:label]]  {{python expression:format}}
<<TOC>> <<MAINMATTER>> <<APPENDIX>> <<REFERENCES>> <<NEWPAGE>>
"""
import json
import re
import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
SRC = REPORT / "src"
OVERLEAF = REPORT / "overleaf"
FIG_OUT = REPORT / "figures"
FIG_SEARCH = [ROOT / "results" / "figures", SRC / "assets"]

META = {
    "university": "KATHMANDU UNIVERSITY",
    "department": "Department of Computer Science and Engineering",
    "place": "Dhulikhel, Kavre",
    "title": "DATASET PREPARATION AND MACHINE LEARNING-BASED CLASSIFICATION OF SPRING STATUS",
    "subtitle": "Mid-Hill Nepal Case Study from the Roshi Khola Watershed",
    "purpose": "(For partial fulfillment of Year II/Semester I in Masters of Computer Engineering)",
    "author": "Suraj Kant Pant",
    "regno": "Registration No.: [038808-24]",
    "supervisor": "Prof. Santosh Khanal",
    "date": "October 2026",
}


# ------------------------------------------------------------------ numbers
class D(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as e:
            raise AttributeError(k) from e


def wrap(o):
    if isinstance(o, dict):
        return D({k: wrap(v) for k, v in o.items()})
    if isinstance(o, list):
        return [wrap(v) for v in o]
    return o


FMT_RE = re.compile(r"^,?(\.\d+)?[dfe%]?$")


def fill_numbers(text, ns):
    def sub(m):
        body = m.group(1).strip()
        expr, fmt = body, ""
        if ":" in body:
            head, tail = body.rsplit(":", 1)
            if tail and FMT_RE.match(tail):
                expr, fmt = head, tail
        try:
            val = eval(expr, {"__builtins__": {"max": max, "min": min, "abs": abs, "round": round, "len": len, "sum": sum}}, ns)
        except Exception as e:
            raise ValueError(f"cannot evaluate {{{{{body}}}}}: {e}") from e
        return format(val, fmt) if fmt else str(val)
    return re.sub(r"\{\{(.+?)\}\}", sub, text)


# ------------------------------------------------------------------ references
def surname(a):
    return a.split(",")[0].strip()


def is_org(a):
    return "," not in a


def cite_names(ref):
    au = ref["authors"]
    if len(au) == 1:
        return surname(au[0])
    if len(au) == 2:
        return f"{surname(au[0])} and {surname(au[1])}"
    return f"{surname(au[0])} et al."


def initials(given):
    parts = re.split(r"[\s.]+", given.strip())
    out = []
    for p in parts:
        if not p:
            continue
        out.append("-".join(s[0] + "." for s in p.split("-") if s))
    return " ".join(out)


def apa_author(a):
    if is_org(a):
        return a
    fam, given = [s.strip() for s in a.split(",", 1)]
    return f"{fam}, {initials(given)}" if given else fam


def apa_reference(ref):
    au = [apa_author(a) for a in ref["authors"]]
    if len(au) > 20:
        au = au[:19] + ["..."] + au[-1:]
    authors = au[0] if len(au) == 1 else ", ".join(au[:-1]) + ", & " + au[-1]
    parts = [f"{authors} ({ref['year']}). {ref['title'].rstrip('.')}."]
    t, j = ref.get("type"), ref.get("journal") or ""
    pages = (ref.get("pages") or "").replace("--", "-")
    if t == "journal-article":
        s = f" {j}"
        if ref.get("volume"):
            s += f", {ref['volume']}"
            if ref.get("issue"):
                s += f"({ref['issue']})"
        if pages:
            s += f", {pages}"
        parts.append(s + ".")
    elif t in ("proceedings-article", "inproceedings", "book-chapter"):
        book = j or ref.get("booktitle", "")
        parts.append(f" In {book}" + (f" (pp. {pages})" if pages else "") + ".")
        if ref.get("publisher"):
            parts.append(f" {ref['publisher']}.")
    elif t == "posted-content":
        parts.append(f" Preprint, {ref.get('publisher') or 'posted content'}.")
    else:
        where = j or ref.get("publisher") or ""
        if where:
            parts.append(f" {where}" + (f", {pages}" if pages else "") + ".")
    if ref.get("doi"):
        parts.append(f" https://doi.org/{ref['doi']}")
    elif ref.get("url"):
        parts.append(f" {ref['url']}")
    return "".join(parts)


def bib_escape(s):
    s = s.replace("\\", "").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")
    return latex_unicode(s)


def bib_entry(ref):
    names = " and ".join("{" + a + "}" if is_org(a) else a for a in ref["authors"])
    t = ref.get("type")
    fields = {"author": bib_escape(names), "title": "{" + bib_escape(ref["title"]) + "}", "year": str(ref["year"])}
    pages = (ref.get("pages") or "").replace("--", "-").replace("-", "--")
    if t == "journal-article":
        kind = "article"
        fields["journal"] = bib_escape(ref.get("journal", ""))
        for k, f in (("volume", "volume"), ("issue", "number")):
            if ref.get(k):
                fields[f] = str(ref[k])
        if pages:
            fields["pages"] = pages
    elif t in ("proceedings-article", "inproceedings", "book-chapter"):
        kind = "inproceedings"
        fields["booktitle"] = bib_escape(ref.get("journal") or ref.get("booktitle", ""))
        if pages:
            fields["pages"] = pages
        if ref.get("publisher"):
            fields["publisher"] = bib_escape(ref["publisher"])
    else:
        kind = "misc"
        how = ref.get("journal") or ref.get("publisher") or ""
        if t == "posted-content":
            how = "Preprint" + (f", {ref.get('publisher')}" if ref.get("publisher") else "")
        if how:
            fields["howpublished"] = bib_escape(how)
        if pages:
            fields["pages"] = pages
    if ref.get("doi"):
        fields["url"] = "https://doi.org/" + ref["doi"]
    elif ref.get("url"):
        fields["url"] = ref["url"]
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items())
    return f"@{kind}{{{ref['key']},\n{body}\n}}\n"


# ------------------------------------------------------------------ inline parsing
INLINE_RE = re.compile(
    r"(?P<code>`[^`]+`)"
    r"|(?P<citep>\[@[^\]]+\])"
    r"|(?P<ref>\[\[[a-z]+:[A-Za-z0-9_\-]+\]\])"
    r"|(?P<bold>\*\*.+?\*\*)"
    r"|(?P<ital>(?<![\*\w])\*(?!\s)[^*]+?\*(?![\*\w]))"
    r"|(?P<citet>(?<![\w@.])@[a-z][a-z0-9]+[0-9]{4}[a-z]?)"
)


def tokenize(text, refs):
    toks, pos = [], 0
    for m in INLINE_RE.finditer(text):
        kind = m.lastgroup
        s = m.group(0)
        if kind == "citet" and s[1:] not in refs:
            continue
        if m.start() > pos:
            toks.append(("text", text[pos:m.start()]))
        if kind == "code":
            toks.append(("code", s[1:-1]))
        elif kind == "citep":
            toks.append(("citep", [k.strip().lstrip("@") for k in s[1:-1].split(";")]))
        elif kind == "ref":
            toks.append(("ref", s[2:-2]))
        elif kind == "bold":
            toks.append(("bold", tokenize(s[2:-2], refs)))
        elif kind == "ital":
            toks.append(("ital", tokenize(s[1:-1], refs)))
        elif kind == "citet":
            toks.append(("citet", s[1:]))
        pos = m.end()
    if pos < len(text):
        toks.append(("text", text[pos:]))
    return toks


# ------------------------------------------------------------------ block parsing
def parse(md):
    lines = md.splitlines()
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip() or line.startswith("%%"):
            i += 1
            continue
        if re.match(r"^<<[A-Z]+>>$", line):
            blocks.append({"t": "marker", "v": line[2:-2]}); i += 1; continue
        m = re.match(r"^(#{1,3}) (.+?)(?:\s*\{([^}]*)\})?$", line)
        if m:
            attrs = m.group(3) or ""
            label = re.search(r"#([\w:\-]+)", attrs)
            blocks.append({"t": "h", "level": len(m.group(1)), "text": m.group(2).strip(),
                           "label": label.group(1) if label else None, "numbered": "-" not in attrs.split()})
            i += 1; continue
        m = re.match(r"^!\[(.+)\]\((.+?)\)\{(.*)\}$", line)
        if m:
            attrs = m.group(3)
            w = re.search(r"width=([\d.]+)", attrs)
            blocks.append({"t": "fig", "caption": m.group(1), "file": m.group(2),
                           "label": re.search(r"#([\w:\-]+)", attrs).group(1), "width": float(w.group(1)) if w else 0.9})
            i += 1; continue
        m = re.match(r"^Table: (.*?)\s*\{(.*)\}$", line)
        if m:
            attrs = m.group(2)
            lab = re.search(r"#([\w:\-]+)", attrs)
            cols = re.search(r"cols=(\S+)", attrs)
            rows, i = [], i + 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                    rows.append(cells)
                i += 1
            size = re.search(r"size=(\w+)", attrs)
            blocks.append({"t": "table", "caption": m.group(1), "label": lab.group(1) if lab else None,
                           "numbered": lab is not None, "cols": cols.group(1) if cols else None, "rows": rows,
                           "size": size.group(1) if size else "small"})
            continue
        m = re.match(r"^\$\$(.+?)\$\$\s*\|\|\s*(.+)$", line)
        if m:
            blocks.append({"t": "eq", "tex": m.group(1).strip(), "text": m.group(2).strip()}); i += 1; continue
        if re.match(r"^(- |\d+\. )", line):
            ordered = bool(re.match(r"^\d+\. ", line))
            items = []
            while i < len(lines) and re.match(r"^(- |\d+\. )", lines[i]):
                item = re.sub(r"^(- |\d+\. )", "", lines[i].rstrip()); i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                    item += " " + lines[i].strip(); i += 1
                items.append(item)
            blocks.append({"t": "list", "ordered": ordered, "items": items}); continue
        para = [line.strip()]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3} |!\[|Table: |\$\$|<<|- |\d+\. |%%)", lines[i]):
            para.append(lines[i].strip()); i += 1
        blocks.append({"t": "p", "text": " ".join(para)})
    return blocks


def number_blocks(blocks):
    """Assign heading/figure/table numbers; return label -> display number."""
    labels, h, fig, tab, appendix = {}, [0, 0, 0], 0, 0, False
    for b in blocks:
        if b["t"] == "marker" and b["v"] == "APPENDIX":
            appendix, h = True, [0, 0, 0]
        if b["t"] == "h" and b["numbered"]:
            lvl = b["level"] - 1
            h[lvl] += 1
            for j in range(lvl + 1, 3):
                h[j] = 0
            first = chr(64 + h[0]) if appendix else str(h[0])
            b["num"] = ".".join([first] + [str(x) for x in h[1:lvl + 1]])
            if b["label"]:
                labels[b["label"]] = b["num"]
        elif b["t"] == "fig":
            fig += 1; b["num"] = fig; labels[b["label"]] = str(fig)
        elif b["t"] == "table" and b["numbered"]:
            tab += 1; b["num"] = tab; labels[b["label"]] = str(tab)
    return labels


# ------------------------------------------------------------------ LaTeX rendering
# Unicode symbols that pdfLaTeX text fonts lack (written as \u escapes so the file stays ASCII-safe)
UNI = {"≥": r"$\geq$", "≤": r"$\leq$", "→": r"$\rightarrow$", "←": r"$\leftarrow$",
       "≈": r"$\approx$", "−": r"$-$", "∂": r"$\partial$", "√": r"$\surd$",
       "ᵢ": r"$_i$", "²": r"\textsuperscript{2}", "°": r"\textdegree{}", "±": r"$\pm$",
       "×": r"$\times$", "µ": r"$\mu$", "‰": r"\textperthousand{}", "…": r"\ldots{}",
       " ": "~"}


def latex_unicode(s):
    for k, v in UNI.items():
        s = s.replace(k, v)
    return s


def tex_escape(s):
    s = (s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("$", r"\$")
         .replace("#", r"\#").replace("_", r"\_").replace("{", r"\{").replace("}", r"\}")
         .replace("~", r"\textasciitilde{}").replace("^", r"\textasciicircum{}"))
    return latex_unicode(s)


REF_WORD = {"fig": "Figure", "tab": "Table", "sec": "Section", "eq": "Equation"}


def tex_inline(toks, refs):
    out = []
    for kind, v in toks:
        if kind == "text":
            out.append(tex_escape(v))
        elif kind == "code":
            out.append(r"\texttt{" + tex_escape(v).replace(r"\_", r"\_\allowbreak{}") + "}")
        elif kind == "bold":
            out.append(r"\textbf{" + tex_inline(v, refs) + "}")
        elif kind == "ital":
            out.append(r"\emph{" + tex_inline(v, refs) + "}")
        elif kind == "citep":
            out.append(r"\citep{" + ",".join(v) + "}")
        elif kind == "citet":
            out.append(r"\citet{" + v + "}")
        elif kind == "ref":
            out.append(REF_WORD[v.split(":")[0]] + r"~\ref{" + v + "}")
    return "".join(out)


def tex_document(blocks, refs, figmap):
    T = lambda s: tex_inline(tokenize(s, refs), refs)  # noqa: E731
    body = []
    for b in blocks:
        t = b["t"]
        if t == "marker":
            body.append({
                "TOC": "\\clearpage\n\\tableofcontents\n\\clearpage\n\\phantomsection\n\\addcontentsline{toc}{section}{List of Figures}\n"
                       "\\listoffigures\n\\clearpage\n\\phantomsection\n\\addcontentsline{toc}{section}{List of Tables}\n"
                       "\\listoftables\n\\clearpage",
                "MAINMATTER": "\\clearpage\n\\pagenumbering{arabic}",
                "APPENDIX": "\\clearpage\n\\appendix",
                "REFERENCES": "\\clearpage\n\\phantomsection\n\\addcontentsline{toc}{section}{References}\n"
                              "\\bibliographystyle{plainnat}\n\\bibliography{references}",
                "NEWPAGE": "\\clearpage",
            }[b["v"]])
        elif t == "h":
            cmd = ["section", "subsection", "subsubsection"][b["level"] - 1]
            pre = "\\clearpage\n" if b["level"] == 1 else ""
            if b["numbered"]:
                lab = f"\\label{{{b['label']}}}" if b["label"] else ""
                body.append(f"{pre}\\{cmd}{{{T(b['text'])}}}{lab}")
            else:
                body.append(f"{pre}\\{cmd}*{{{T(b['text'])}}}\n\\addcontentsline{{toc}}{{{cmd}}}{{{T(b['text'])}}}")
        elif t == "p":
            body.append(T(b["text"]))
        elif t == "list":
            env = "enumerate" if b["ordered"] else "itemize"
            items = "\n".join(f"  \\item {T(x)}" for x in b["items"])
            body.append(f"\\begin{{{env}}}\n{items}\n\\end{{{env}}}")
        elif t == "eq":
            body.append(f"\\begin{{equation}}\n{b['tex']}\n\\end{{equation}}")
        elif t == "fig":
            name = figmap[b["label"]].stem
            body.append("\\begin{figure}[htbp]\n\\centering\n"
                        f"\\includegraphics[width={b['width']}\\linewidth]{{figures/{name}}}\n"
                        f"\\caption{{{T(b['caption'])}}}\n\\label{{{b['label']}}}\n\\end{{figure}}")
        elif t == "table":
            ncol = len(b["rows"][0])
            spec = b["cols"] or ("L" * ncol)
            head = " & ".join(r"\textbf{" + T(c) + "}" for c in b["rows"][0]) + r" \\"
            rows = "\n".join(" & ".join(T(c) for c in r) + r" \\" for r in b["rows"][1:])
            tab = (f"\\begin{{tabularx}}{{\\linewidth}}{{{spec}}}\n\\toprule\n{head}\n\\midrule\n{rows}\n"
                   "\\bottomrule\n\\end{tabularx}")
            if b["numbered"]:
                body.append(f"\\begin{{table}}[htbp]\n\\centering\n\\{b['size']}\n"
                            f"\\caption{{{T(b['caption'])}}}\n\\label{{{b['label']}}}\n{tab}\n\\end{{table}}")
            else:
                body.append(f"{{\\{b['size']}\n" + tab + "\n}")
    m = META
    preamble = r"""\documentclass[12pt,a4paper]{article}
%% Generated by scripts/build_report.py from report/src/report.md - edit the source, not this file.
%% Compile on Overleaf with pdfLaTeX; BibTeX runs automatically.
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{textcomp}
\usepackage{newtxtext,newtxmath}
\usepackage[a4paper,left=1.25in,right=1in,top=1in,bottom=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs,tabularx,array}
\usepackage{amsmath}
\usepackage{setspace}
\usepackage[font=small,labelfont=bf]{caption}
\usepackage[round,authoryear]{natbib}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage{xurl}
\newcolumntype{L}{>{\raggedright\arraybackslash}X}
\newcolumntype{R}{>{\raggedleft\arraybackslash}X}
\newcolumntype{C}{>{\centering\arraybackslash}X}
\renewcommand{\arraystretch}{1.15}
\onehalfspacing
\setlength{\parskip}{0.5em}
\setlength{\parindent}{0pt}
\setlength{\emergencystretch}{3em}
\begin{document}
"""
    title = rf"""\begin{{titlepage}}
\centering
{{\LARGE\bfseries {m['university']}\par}}
{{\Large\bfseries {m['department']}\par}}
{{\Large\bfseries {m['place']}\par}}
\vspace{{1.2cm}}
\includegraphics[width=0.18\linewidth]{{figures/ku_logo}}\par
\vspace{{1.2cm}}
{{\Large\bfseries\color[HTML]{{2E5A88}} A PROJECT REPORT\par}}
\vspace{{0.6cm}}
{{\large\bfseries\color[HTML]{{2E5A88}} on\par}}
\vspace{{0.6cm}}
{{\Large\bfseries {tex_escape(m['title'])}\par}}
\vspace{{0.4cm}}
{{\large\itshape {tex_escape(m['subtitle'])}\par}}
\vspace{{0.3cm}}
{{\itshape {tex_escape(m['purpose'])}\par}}
\vfill
{{\large\bfseries Submitted by\par}}
{{\bfseries {m['author']}\par}}
{tex_escape(m['regno'])}\par
\vspace{{0.8cm}}
{{\large\bfseries Submitted to\par}}
{{\bfseries {m['supervisor']}\par}}
\vspace{{0.8cm}}
{{\bfseries {m['date']}\par}}
\end{{titlepage}}
\pagenumbering{{roman}}
\setcounter{{page}}{{2}}
\section*{{\centering BONAFIDE CERTIFICATE}}
This is to certify that the project report entitled ``{tex_escape(m['title'])}: A {tex_escape(m['subtitle'])}'' is a bona fide record of the project work carried out by {m['author']} under my supervision and guidance for the project requirement of the {m['department']}, Kathmandu University.

\vspace{{2.5cm}}
\noindent\rule{{6cm}}{{0.4pt}}\\
Supervisor: {m['supervisor']}\\
Project Supervisor\\
{m['department']}
\clearpage
"""
    return preamble + title + "\n\n".join(body) + "\n\\end{document}\n"


# ------------------------------------------------------------------ DOCX rendering
def set_cell_shading(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def add_field(paragraph, instr, placeholder=""):
    run = paragraph.add_run()
    for tag, attr in (("w:fldChar", "begin"), ("w:instrText", None), ("w:fldChar", "separate")):
        el = OxmlElement(tag)
        if attr:
            el.set(qn("w:fldCharType"), attr)
        else:
            el.set(qn("xml:space"), "preserve"); el.text = instr
        run._r.append(el)
    paragraph.add_run(placeholder)
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
    paragraph.add_run()._r.append(end)


def set_page_numbering(section, fmt, start=None):
    sectPr = section._sectPr
    pg = sectPr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType"); sectPr.append(pg)
    pg.set(qn("w:fmt"), fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(p, "PAGE", "1")


def docx_inline(par, toks, refs, labels, bold=False, ital=False):
    for kind, v in toks:
        if kind == "text":
            r = par.add_run(v); r.bold, r.italic = bold or None, ital or None
        elif kind == "code":
            r = par.add_run(v); r.font.name = "Consolas"; r.font.size = Pt(10.5)
        elif kind == "bold":
            docx_inline(par, v, refs, labels, True, ital)
        elif kind == "ital":
            docx_inline(par, v, refs, labels, bold, True)
        elif kind == "citep":
            par.add_run("(" + "; ".join(f"{cite_names(refs[k])}, {refs[k]['year']}" for k in v) + ")")
        elif kind == "citet":
            par.add_run(f"{cite_names(refs[v])} ({refs[v]['year']})")
        elif kind == "ref":
            par.add_run(f"{REF_WORD[v.split(':')[0]]} {labels[v]}")


def build_docx(blocks, refs, labels, figmap, cited, out):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"; st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.space_after = Pt(6)
    for name, size in (("Heading 1", 16), ("Heading 2", 13.5), ("Heading 3", 12)):
        hs = doc.styles[name]
        hs.font.name = "Times New Roman"; hs.font.size = Pt(size); hs.font.bold = True
        hs.font.color.rgb = RGBColor(0x1F, 0x3B, 0x5C)
    sec = doc.sections[0]
    sec.left_margin, sec.right_margin = Inches(1.25), Inches(1)
    sec.top_margin = sec.bottom_margin = Inches(1)
    m = META

    def centered(text, size=12, bold=False, italic=False, color=None, space=6):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text); r.font.size = Pt(size); r.bold = bold; r.italic = italic
        if color:
            r.font.color.rgb = RGBColor.from_string(color)
        p.paragraph_format.space_after = Pt(space)
        return p

    centered(m["university"], 20, True, space=0)
    centered(m["department"], 16, True, space=0)
    centered(m["place"], 16, True, space=18)
    logo = SRC / "assets" / "ku_logo.png"
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(logo), width=Inches(1.4))
    centered("A PROJECT REPORT", 16, True, color="2E5A88", space=4)
    centered("on", 13, True, color="2E5A88", space=8)
    centered(m["title"], 15, True, space=6)
    centered(m["subtitle"], 12, italic=True, space=2)
    centered(m["purpose"], 11, italic=True, space=40)
    centered("Submitted by", 13, True, space=0)
    centered(m["author"], 12, True, space=0)
    centered(m["regno"], 11, space=18)
    centered("Submitted to", 13, True, space=0)
    centered(m["supervisor"], 12, True, space=18)
    centered(m["date"], 12, True)
    doc.add_page_break()
    centered("BONAFIDE CERTIFICATE", 16, True, color="2E5A88", space=12)
    p = doc.add_paragraph(f"This is to certify that the project report entitled \u201c{m['title']}: A {m['subtitle']}\u201d "
                          f"is a bona fide record of the project work carried out by {m['author']} under my supervision "
                          f"and guidance for the project requirement of the {m['department']}, Kathmandu University.")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for _ in range(3):
        doc.add_paragraph()
    doc.add_paragraph("______________________________\nSupervisor: " + m["supervisor"] + "\nProject Supervisor\n" + m["department"])
    set_page_numbering(sec, "lowerRoman", 1)

    figs = [b for b in blocks if b["t"] == "fig"]
    tabs = [b for b in blocks if b["t"] == "table" and b["numbered"]]
    first_h1 = True
    for b in blocks:
        t = b["t"]
        if t == "marker":
            v = b["v"]
            if v == "TOC":
                doc.add_page_break()
                doc.add_heading("Table of Contents", 1)
                p = doc.add_paragraph()
                add_field(p, 'TOC \\o "1-3" \\h \\z \\u', "Right-click here and choose Update Field to build the table of contents.")
                doc.add_page_break()
                doc.add_heading("List of Figures", 1)
                for f in figs:
                    doc.add_paragraph(f"Figure {f['num']}: " + plain(f["caption"], refs, labels)).paragraph_format.space_after = Pt(2)
                doc.add_heading("List of Tables", 1)
                for tb in tabs:
                    doc.add_paragraph(f"Table {tb['num']}: " + plain(tb["caption"], refs, labels)).paragraph_format.space_after = Pt(2)
            elif v == "MAINMATTER":
                new = doc.add_section(WD_SECTION.NEW_PAGE)
                set_page_numbering(new, "decimal", 1)
                first_h1 = True
            elif v in ("NEWPAGE", "APPENDIX"):
                doc.add_page_break(); first_h1 = True
            elif v == "REFERENCES":
                doc.add_page_break()
                doc.add_heading("References", 1)
                for key in sorted(cited, key=lambda k: (surname(refs[k]["authors"][0]).lower(), refs[k]["year"])):
                    p = doc.add_paragraph(apa_reference(refs[key]))
                    p.paragraph_format.left_indent = Inches(0.5)
                    p.paragraph_format.first_line_indent = Inches(-0.5)
                    p.paragraph_format.line_spacing = 1.15
                first_h1 = True
        elif t == "h":
            if b["level"] == 1 and not first_h1:
                doc.add_page_break()
            first_h1 = False
            text = (b["num"] + " " if b.get("num") else "") + plain(b["text"], refs, labels)
            if b.get("num") and b["num"][0].isalpha() and b["level"] == 1:
                text = "Appendix " + text
            doc.add_heading(text, b["level"])
        elif t == "p":
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            docx_inline(p, tokenize(b["text"], refs), refs, labels)
        elif t == "list":
            for item in b["items"]:
                p = doc.add_paragraph(style="List Number" if b["ordered"] else "List Bullet")
                docx_inline(p, tokenize(item, refs), refs, labels)
        elif t == "eq":
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(b["text"]); r.italic = True
        elif t == "fig":
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(figmap[b["label"]]), width=Inches(6.0 * min(b["width"], 1.0)))
            c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = c.add_run(f"Figure {b['num']}: "); r.bold = True; r.font.size = Pt(10.5)
            before = len(c.runs)
            docx_inline(c, tokenize(b["caption"], refs), refs, labels, ital=True)
            for r in c.runs[before:]:
                r.font.size = Pt(10.5)
        elif t == "table":
            if b["numbered"]:
                c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = c.add_run(f"Table {b['num']}: "); r.bold = True; r.font.size = Pt(10.5)
                before = len(c.runs)
                docx_inline(c, tokenize(b["caption"], refs), refs, labels, ital=True)
                for r in c.runs[before:]:
                    r.font.size = Pt(10.5)
            rows = b["rows"]
            table = doc.add_table(rows=len(rows), cols=len(rows[0]))
            table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.CENTER
            for i, row in enumerate(rows):
                for j, cell_text in enumerate(row):
                    cell = table.cell(i, j)
                    cp = cell.paragraphs[0]
                    cp.paragraph_format.line_spacing = 1.0; cp.paragraph_format.space_after = Pt(0)
                    docx_inline(cp, tokenize(cell_text, refs), refs, labels, bold=(i == 0))
                    for r in cp.runs:
                        r.font.size = Pt(9.5)
                    if i == 0:
                        set_cell_shading(cell, "D9E2F3")
            doc.add_paragraph()
    doc.save(out)


def plain(s, refs, labels):
    out = []
    for kind, v in tokenize(s, refs):
        if kind in ("text", "code"):
            out.append(v)
        elif kind in ("bold", "ital"):
            out.append(plain_tokens(v, refs, labels))
        elif kind == "citep":
            out.append("(" + "; ".join(f"{cite_names(refs[k])}, {refs[k]['year']}" for k in v) + ")")
        elif kind == "citet":
            out.append(f"{cite_names(refs[v])} ({refs[v]['year']})")
        elif kind == "ref":
            out.append(f"{REF_WORD[v.split(':')[0]]} {labels[v]}")
    return "".join(out)


def plain_tokens(toks, refs, labels):
    return "".join(v if k in ("text", "code") else "" for k, v in toks)


# ------------------------------------------------------------------ main
def collect_citations(blocks, refs):
    keys = []
    def scan(toks):
        for kind, v in toks:
            if kind == "citep":
                keys.extend(v)
            elif kind == "citet":
                keys.append(v)
            elif kind in ("bold", "ital"):
                scan(v)
    for b in blocks:
        for field in ("text", "caption"):
            if field in b and isinstance(b[field], str):
                scan(tokenize(b[field], refs))
        for item in b.get("items", []):
            scan(tokenize(item, refs))
        for row in b.get("rows", []):
            for c in row:
                scan(tokenize(c, refs))
    return list(dict.fromkeys(keys))


def find_figure(name):
    for d in FIG_SEARCH:
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(f"figure {name} not found in {FIG_SEARCH}")


def main():
    numbers = wrap(json.loads((REPORT / "numbers.json").read_text(encoding="utf-8-sig")))
    refs_all = {r["key"]: r for r in json.loads((SRC / "references.json").read_text(encoding="utf-8-sig"))}
    refs = {k: r for k, r in refs_all.items() if r.get("verified")}
    md = (SRC / "report.md").read_text(encoding="utf-8-sig")
    md = fill_numbers(md, dict(numbers))
    blocks = parse(md)
    labels = number_blocks(blocks)

    cited = collect_citations(blocks, refs_all)
    bad = [k for k in cited if k not in refs]
    if bad:
        raise SystemExit(f"citations not verified or unknown: {bad}")
    missing_refs = set(re.findall(r"\[\[([a-z]+:[\w\-]+)\]\]", md)) - set(labels)
    if missing_refs:
        raise SystemExit(f"cross-references to unknown labels: {sorted(missing_refs)}")

    # figures: number them in order of appearance
    # clear old outputs file by file (OneDrive can lock the folders themselves)
    for d in (OVERLEAF, FIG_OUT):
        if d.exists():
            for f in d.rglob("*"):
                if f.is_file():
                    f.unlink()
    (OVERLEAF / "figures").mkdir(parents=True, exist_ok=True)
    FIG_OUT.mkdir(parents=True, exist_ok=True)
    figmap, captions = {}, ["# Figures for the report\n", "Upload `report/overleaf_upload.zip` to Overleaf, or these files into a `figures/` folder.\n"]
    for b in blocks:
        if b["t"] == "fig":
            src = find_figure(b["file"])
            dst_name = f"fig{b['num']:02d}_{src.stem}{src.suffix}"
            shutil.copy2(src, OVERLEAF / "figures" / dst_name)
            shutil.copy2(src, FIG_OUT / dst_name)
            figmap[b["label"]] = OVERLEAF / "figures" / dst_name
            captions.append(f"- **Figure {b['num']}** (`{dst_name}`, source `{src.relative_to(ROOT).as_posix()}`): {plain(b['caption'], refs, labels)}")
    shutil.copy2(SRC / "assets" / "ku_logo.png", OVERLEAF / "figures" / "ku_logo.png")
    (FIG_OUT / "CAPTIONS.md").write_text("\n".join(captions) + "\n", encoding="utf-8")

    tex = tex_document(blocks, refs, figmap)
    (OVERLEAF / "main.tex").write_text(tex, encoding="utf-8")
    (OVERLEAF / "references.bib").write_text("".join(bib_entry(refs[k]) for k in sorted(cited)), encoding="utf-8")
    zpath = REPORT / "overleaf_upload.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in OVERLEAF.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(OVERLEAF).as_posix())

    build_docx(blocks, refs, labels, figmap, cited, REPORT / "Project_Report_Revised.docx")
    nf = sum(1 for b in blocks if b["t"] == "fig"); nt = sum(1 for b in blocks if b["t"] == "table" and b["numbered"])
    print(f"built: {nf} figures, {nt} tables, {len(cited)} references")
    print("  ", OVERLEAF / "main.tex"); print("  ", zpath); print("  ", REPORT / "Project_Report_Revised.docx")


if __name__ == "__main__":
    main()
