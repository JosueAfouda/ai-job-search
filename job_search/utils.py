from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path


WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\x00", " ")
    return WHITESPACE_RE.sub(" ", text).strip()


def compact_multiline(value: str) -> str:
    lines = [clean_text(line) for line in (value or "").splitlines()]
    return "\n".join(line for line in lines if line)


def slugify(value: str, max_len: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    slug = re.sub(r"_+", "_", slug)
    return (slug[:max_len].strip("_") or "job")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate(value: str, limit: int) -> str:
    value = value or ""
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0].rstrip() + "..."


def redact_phone_numbers(value: str) -> str:
    # Career-Ops shared rules avoid emitting phone numbers in generated documents.
    return re.sub(r"(?<!\d)(?:\+33|0)\s*[1-9](?:[\s.-]*\d{2}){4}(?!\d)", "[phone redacted]", value)
