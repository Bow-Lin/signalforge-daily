from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from pypdf import PdfReader


@dataclass(frozen=True)
class PdfReadResult:
    url: str
    text: str


def download_pdf(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def read_pdf_text(path: Path, max_chars: int = 8000) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    total = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        if not text:
            continue
        remaining = max_chars - total
        if remaining <= 0:
            break
        parts.append(text[:remaining])
        total += len(parts[-1])
    return "\n".join(parts)


def fetch_and_read_pdf(
    url: str,
    cache_dir: Path,
    max_chars: int = 8000,
) -> PdfReadResult:
    filename = url.split("/")[-1]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    local_path = cache_dir / filename
    if not local_path.exists():
        download_pdf(url, local_path)
    text = read_pdf_text(local_path, max_chars=max_chars)
    return PdfReadResult(url=url, text=text)
