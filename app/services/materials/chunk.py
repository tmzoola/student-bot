"""Matnni paragraf chegarasida bo'laklarga bo'lish."""
from __future__ import annotations


def chunk_text(text: str, max_chars: int = 2000) -> list[str]:
    if not text:
        return []
    text = text.replace("\r\n", "\n").strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if buf:
            chunks.append("\n\n".join(buf))
            buf = []
            buf_len = 0

    for para in paragraphs:
        # Uzun paragraf: qattiq bo'l max_chars bo'yicha.
        if len(para) > max_chars:
            flush()
            for i in range(0, len(para), max_chars):
                chunks.append(para[i : i + max_chars])
            continue
        add_len = len(para) + (2 if buf else 0)
        if buf_len + add_len > max_chars:
            flush()
        buf.append(para)
        buf_len += add_len

    flush()
    return chunks
