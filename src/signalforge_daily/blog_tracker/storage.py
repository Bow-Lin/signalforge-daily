from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BlogSource:
    id: int
    url: str
    name: str


class Storage:
    def __init__(self, sources_path: str) -> None:
        self.sources_path = Path(sources_path)
        if self.sources_path.parent and not self.sources_path.parent.exists():
            self.sources_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.sources_path.exists():
            self.sources_path.write_text("", encoding="utf-8")

    def list_sources(self) -> list[BlogSource]:
        _, source_lines = self._load_lines()
        sources: list[BlogSource] = []
        for idx, line in enumerate(source_lines, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                name, url = parts[0], parts[1]
            else:
                url = parts[0]
                name = url
            sources.append(BlogSource(id=idx, url=url, name=name))
        return sources

    def get_last_run_at(self) -> str | None:
        meta, _ = self._load_lines()
        return meta

    def upsert_source(self, url: str, name: str) -> None:
        meta, source_lines = self._load_lines()
        sources = self._parse_sources(source_lines)
        lines: list[str] = []
        found = False
        for source in sources:
            if source.url == url:
                lines.append(f"{name}\t{url}")
                found = True
            else:
                lines.append(f"{source.name}\t{source.url}")
        if not found:
            lines.append(f"{name}\t{url}")
        self._write_lines(meta, lines)

    def update_last_run_at(self, last_run_at: str) -> None:
        _, source_lines = self._load_lines()
        self._write_lines(last_run_at, source_lines)

    def _load_lines(self) -> tuple[str | None, list[str]]:
        lines = self.sources_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return None, []
        first = lines[0].strip()
        if first.startswith("last_run_at"):
            parts = first.split("\t", maxsplit=1)
            meta = parts[1] if len(parts) > 1 and parts[1] else None
            if meta == "last_run_at":
                meta = None
            return meta, lines[1:]
        return None, lines

    def _write_lines(self, meta: str | None, source_lines: list[str]) -> None:
        lines: list[str] = []
        if meta:
            lines.append(f"last_run_at\t{meta}")
        lines.extend(source_lines)
        self.sources_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _parse_sources(self, source_lines: list[str]) -> list[BlogSource]:
        sources: list[BlogSource] = []
        for idx, line in enumerate(source_lines, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                name, url = parts[0], parts[1]
            else:
                url = parts[0]
                name = url
            sources.append(BlogSource(id=idx, url=url, name=name))
        return sources
