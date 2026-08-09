"""Material fayllardan matn ajratish testlari (PDF, DOCX, TXT)."""
from __future__ import annotations

from pathlib import Path

import pytest

from services.materials.chunk import chunk_text
from services.materials.extract import (
    MIME_DOCX,
    MIME_PDF,
    MIME_TXT,
    ExtractError,
    extract_text,
)


def test_extract_txt(tmp_path: Path) -> None:
    f = tmp_path / "sample.txt"
    f.write_text("Salom dunyo\n\nIkkinchi paragraf.", encoding="utf-8")
    result = extract_text(f, MIME_TXT)
    assert "Salom dunyo" in result
    assert "Ikkinchi paragraf" in result


def test_extract_pdf(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    f = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "PDF ichidagi matn")
    doc.save(str(f))
    doc.close()

    result = extract_text(f, MIME_PDF)
    assert "PDF ichidagi matn" in result


def test_extract_docx(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    f = tmp_path / "sample.docx"
    d = docx.Document()
    d.add_paragraph("DOCX matn qatori bir")
    d.add_paragraph("DOCX matn qatori ikki")
    d.save(str(f))

    result = extract_text(f, MIME_DOCX)
    assert "DOCX matn qatori bir" in result
    assert "DOCX matn qatori ikki" in result


def test_extract_unsupported_mime(tmp_path: Path) -> None:
    f = tmp_path / "x.bin"
    f.write_bytes(b"\x00\x01")
    with pytest.raises(ExtractError):
        extract_text(f, "application/octet-stream")


def test_chunk_text_short() -> None:
    assert chunk_text("") == []
    assert chunk_text("Bir paragraf") == ["Bir paragraf"]


def test_chunk_text_paragraph_boundary() -> None:
    p1 = "A" * 500
    p2 = "B" * 500
    p3 = "C" * 500
    text = f"{p1}\n\n{p2}\n\n{p3}"
    chunks = chunk_text(text, max_chars=1100)
    assert len(chunks) == 2
    assert chunks[0].startswith("A") and "B" in chunks[0]
    assert chunks[1].startswith("C")


def test_chunk_text_hard_split() -> None:
    text = "X" * 5000
    chunks = chunk_text(text, max_chars=2000)
    assert len(chunks) == 3
    assert all(len(c) <= 2000 for c in chunks)
