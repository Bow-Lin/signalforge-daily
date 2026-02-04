from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Optional


_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_TEXT_DATE_RE = re.compile(
    r"\b("
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
    r")\s+(\d{1,2}),\s+(\d{4})\b",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def parse_date_text(text: str) -> Optional[datetime]:
    if not text:
        return None
    text = " ".join(text.split())
    iso_match = _ISO_DATE_RE.search(text)
    if iso_match:
        year, month, day = (int(g) for g in iso_match.groups())
        return datetime(year, month, day, tzinfo=timezone.utc)
    match = _TEXT_DATE_RE.search(text)
    if not match:
        return None
    month_name = match.group(1).lower()
    month = _MONTHS.get(month_name[:3], _MONTHS.get(month_name))
    if not month:
        return None
    day = int(match.group(2))
    year = int(match.group(3))
    return datetime(year, month, day, tzinfo=timezone.utc)
