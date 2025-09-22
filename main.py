from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from pathlib import Path
import tempfile
import subprocess
import textwrap

app = FastAPI(title="LaTeX Equations to PDF")

class RenderRequest(BaseModel):
    equations_raw: str  # un string con todas las ecuaciones separadas por **
    page_break_between: bool = False
    title: str = "Ecuaciones"

LATEX_PREAMBLE = r"""
\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[a4paper,margin=2.2cm]{geometry}
\usepackage{amsmath, amssymb, amsfonts}
\usepackage{bm}
\usepackage{mathtools}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{relsize}
\usepackage{upgreek}
\usepackage{physics}
\usepackage{xcolor}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=black,urlcolor=blue}
\setlength{\parskip}{0.6em}
\setlength{\parindent}{0pt}
"""

LATEX_BEGIN = r"""
\begin{document}
\begin{center}
{\LARGE \textbf{%(title)s}}
\end{center}
\vspace{1em}
"""

LATEX_END = r"""
\end{document}
"""

def make_equation_block(eq: str, add_pagebreak: bool) -> str:
    rendered = eq

    block = textwrap.dedent(rf"""
    %%%%%% Equation Block Start %%%%%%
    \noindent
    {rendered}

    \vspace{{0.4em}}
    \textbf{{LaTeX literal:}}
    \\begin{{verbatim}}
{eq}
    \\end{{verbatim}}
    \vspace{{0.8em}}
    %%%%%% Equation Block End %%%%%%
    """)

    if add_pagebreak:
        block += "\n\\clearpage\n"

    return block

def build_latex_source(title: str, equations: list[str], page_break_between: bool) -> str:
    body = []
    for i, eq in enumerate(equations, start=1):
        body.append(f"\\textbf{{Ecuación {i}}}\n")
        body.append(make_equation_block(eq, page_break_between))
    body_str = "\n".join(body)

    tex = LATEX_PREAMBLE + LATEX_BEGIN % {"title": title} + body_str + LATEX_END
    return tex

def run_latexmk(tex_path: Path, workdir: Path) -> Path:
    cmd = [
        "latexmk",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex_path.name,
    ]
    proc = subprocess.run(cmd, cwd=str(workdir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"LaTeX compilation failed:\n{proc.stdout}")
    pdf_path = tex_path.with_suffix(".pdf")
    if not pdf_path.exists():
        raise RuntimeError("No se generó el PDF.")
    subprocess.run(["latexmk", "-c"], cwd=str(workdir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pdf_path

@app.post("/render", response_class=Response)
def render_pdf(req: RenderRequest):
    if not req.equations_raw.strip():
        raise HTTPException(status_code=400, detail="El string 'equations_raw' no puede estar vacío.")

    # Separamos por el delimitador **
    equations = [e.strip("* \n") for e in req.equations_raw.split("**") if e.strip()]

    if not equations:
        raise HTTPException(status_code=400, detail="No se encontraron ecuaciones con el delimitador **.")

    tex_source = build_latex_source(title=req.title, equations=equations, page_break_between=req.page_break_between)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tex_path = tmp / "document.tex"
        tex_path.write_text(tex_source, encoding="utf-8")

        try:
            pdf_path = run_latexmk(tex_path, tmp)
            pdf_bytes = pdf_path.read_bytes()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al compilar LaTeX: {e}")

    headers = {
        "Content-Disposition": 'attachment; filename="ecuaciones.pdf"',
        "Content-Type": "application/pdf",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@app.get("/")
def root():
    example = {
        "equations_raw": "*$20 \\mathrm{~m} / \\mathrm{s}$**$9.81 \\mathrm{~m} / \\mathrm{s}^{2}$**\\[ d \\vec{B}=... \\]"
    }
    return {
        "message": "Servicio OK. POST /render con JSON {equations_raw: '...'}",
        "example_payload": example
    }
