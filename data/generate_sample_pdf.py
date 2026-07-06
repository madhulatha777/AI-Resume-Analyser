"""Generate a sample resume PDF from ``data/sample_resume.txt``.

Useful for manually exercising the Streamlit upload flow without a real resume.

Usage::

    python data/generate_sample_pdf.py
    # -> writes data/sample_resume.pdf
"""

from __future__ import annotations

import pathlib

from fpdf import FPDF
from fpdf.enums import XPos, YPos

HERE = pathlib.Path(__file__).resolve().parent


def main() -> None:
    text = (HERE / "sample_resume.txt").read_text(encoding="utf-8")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.split("\n"):
        safe = line.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 6, safe or " ", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    out = HERE / "sample_resume.pdf"
    pdf.output(str(out))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
