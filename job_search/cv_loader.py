from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .profile import SearchProfile, has_term, load_search_profile
from .utils import compact_multiline


@dataclass(slots=True)
class CandidateProfile:
    text: str
    name: str
    keywords: list[str]
    search_profile: SearchProfile | None = None


def resolve_cv_path(pdf_path: Path | None = None, directory: Path | None = None) -> Path:
    if pdf_path is not None:
        return pdf_path
    candidates = sorted(path for path in (directory or Path.cwd()).iterdir()
                        if path.is_file() and path.suffix.casefold() == ".pdf")
    if len(candidates) != 1:
        raise ValueError(
            "Placez un seul CV PDF à la racine ou indiquez --cv chemin/vers/cv.pdf "
            f"({len(candidates)} PDF trouvés)."
        )
    return candidates[0]


def load_cv(pdf_path: Path | None = None, search_profile: SearchProfile | None = None) -> CandidateProfile:
    pdf_path = resolve_cv_path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"CV PDF not found: {pdf_path}")

    text = extract_pdf_text(pdf_path)
    if len(text) < 500:
        raise RuntimeError(
            "Could not extract enough CV text. Install poppler `pdftotext` or a Python PDF library."
        )

    return CandidateProfile(
        text=text,
        name=extract_name(text),
        keywords=extract_keywords(text, terms=search_profile.vocabulary() if search_profile else None),
        search_profile=search_profile,
    )


def extract_pdf_text(pdf_path: Path) -> str:
    text = _extract_with_pdftotext(pdf_path)
    if text:
        return text

    text = _extract_with_python_libs(pdf_path)
    if text:
        return text

    return ""


def _extract_with_pdftotext(pdf_path: Path) -> str:
    try:
        proc = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""

    if proc.returncode != 0:
        return ""
    return compact_multiline(proc.stdout)


def _extract_with_python_libs(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return ""

    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    return compact_multiline("\n".join(parts))


def extract_name(cv_text: str) -> str:
    for line in cv_text.splitlines():
        line = line.strip()
        if line and len(line) <= 80:
            return line
    return "Candidate"


def extract_keywords(cv_text: str, limit: int = 80, terms: list[str] | None = None) -> list[str]:
    vocabulary = terms if terms is not None else load_search_profile().vocabulary()
    return [term for term in dict.fromkeys(vocabulary) if has_term(cv_text, term)][:limit]
