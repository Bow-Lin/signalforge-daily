from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class ListedPost:
    url: str
    title: str
    published_at: datetime


class BlogSourceClient(Protocol):
    def list_posts(self, since: datetime) -> list[ListedPost]:
        ...

    def fetch_html(self, url: str) -> str:
        ...
