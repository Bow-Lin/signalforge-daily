from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path

from .arxiv import ArxivEntry


def _load_existing_ids(storage_dir: Path) -> set[str]:
    index_path = storage_dir / "index.jsonl"
    if not index_path.exists():
        return set()
    existing = set()
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            entry_id = obj.get("id")
            if entry_id:
                existing.add(entry_id)
    return existing


def _append_index(storage_dir: Path, entry_ids: list[str]) -> None:
    if not entry_ids:
        return
    index_path = storage_dir / "index.jsonl"
    with index_path.open("a", encoding="utf-8") as f:
        for entry_id in entry_ids:
            f.write(json.dumps({"id": entry_id}) + "\n")


def store_papers(entries: list[ArxivEntry], storage_dir: Path) -> list[ArxivEntry]:
    storage_dir.mkdir(parents=True, exist_ok=True)

    existing_ids = _load_existing_ids(storage_dir)
    new_entries = [e for e in entries if e.arxiv_id not in existing_ids]

    if not new_entries:
        return []

    out_path = storage_dir / "papers_latest.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for entry in new_entries:
            payload = asdict(entry)
            payload["published"] = entry.published.isoformat() if entry.published else None
            payload["updated"] = entry.updated.isoformat() if entry.updated else None
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    _append_index(storage_dir, [e.arxiv_id for e in new_entries])
    return new_entries
