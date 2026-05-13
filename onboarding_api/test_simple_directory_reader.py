import os
from pathlib import Path
import tempfile

import pytest

from llama_index.core import SimpleDirectoryReader


def create_sample_docx(path: Path, text: str):
    import docx

    doc = docx.Document()
    doc.add_paragraph(text)
    doc.save(path)


def create_sample_xlsx(path: Path):
    import pandas as pd

    df = pd.DataFrame({'Name': ['Alice', 'Bob'], 'Value': [10, 20]})
    df.to_excel(path, index=False)


def create_sample_pptx(path: Path, text: str):
    from pptx import Presentation

    prs = Presentation()
    slide_layout = prs.slide_layouts[5] if len(prs.slide_layouts) > 5 else prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    title.text = text
    prs.save(path)


def create_sample_pdf(path: Path, text: str):
    # Creates a minimal text PDF that is readable by most PDF parsers.
    contents = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    parts = []
    parts.append(b"%PDF-1.4\n")
    parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    parts.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    parts.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    parts.append(b"4 0 obj\n<< /Length %d >>\nstream\n" % len(contents))
    parts.append(contents + b"\nendstream\nendobj\n")
    parts.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    xref_offset = sum(len(p) for p in parts)
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    current = 10
    offset = 10
    obj_offsets = []
    running = 0
    for part in parts[:-1]:
        obj_offsets.append(running)
        running += len(part)
    for offset in obj_offsets:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(running).encode("ascii") + b"\n%%EOF\n"

    with open(path, "wb") as f:
        for part in parts:
            f.write(part)
        for line in xref:
            f.write(line)
        f.write(trailer)


def create_sample_png(path: Path, text: str):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (320, 80), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((10, 10), text, fill="black", font=font)
    img.save(path)


def read_text_from_files(path: Path):
    reader = SimpleDirectoryReader(input_files=[str(path)])
    documents = reader.load_data()
    return "\n".join(getattr(doc, "text", "") or "" for doc in documents)


@pytest.mark.parametrize(
    "factory, filename, expected_substring",
    [
        (create_sample_docx, "sample.docx", "Hello Word"),
        (create_sample_xlsx, "sample.xlsx", "Alice"),
    ],
)
def test_simple_directory_reader_docx_xlsx(factory, filename, expected_substring):
    factory_name = factory.__name__
    if factory_name == "create_sample_docx":
        pytest.importorskip("docx")
    if factory_name == "create_sample_xlsx":
        pytest.importorskip("pandas")
        pytest.importorskip("openpyxl")

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / filename
        factory(path, expected_substring)
        extracted = read_text_from_files(path)
        assert expected_substring in extracted


def test_simple_directory_reader_pdf():
    pytest.importorskip("PyPDF2")
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "sample.pdf"
        create_sample_pdf(path, "Hello PDF")
        extracted = read_text_from_files(path)
        assert "Hello PDF" in extracted


def test_simple_directory_reader_pptx():
    pytest.importorskip("pptx")
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "sample.pptx"
        create_sample_pptx(path, "Hello PPT")
        extracted = read_text_from_files(path)
        assert "Hello PPT" in extracted


def test_simple_directory_reader_image():
    pytest.importorskip("PIL")
    pytest.importorskip("pytesseract")
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "sample.png"
        create_sample_png(path, "Hello image")
        extracted = read_text_from_files(path)
        assert "Hello image" in extracted
