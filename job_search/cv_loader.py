from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .utils import compact_multiline


DEFAULT_CV_PDF = Path("Consultant_Data_Josue_Afouda.pdf")


@dataclass(slots=True)
class CandidateProfile:
    text: str
    name: str
    keywords: list[str]


def load_cv(pdf_path: Path = DEFAULT_CV_PDF) -> CandidateProfile:
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
        keywords=extract_keywords(text),
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


def extract_keywords(cv_text: str, limit: int = 40) -> list[str]:
    known_terms = [
        "Python",
        "SQL",
        "Power BI",
        "Machine Learning",
        "Deep Learning",
        "NLP",
        "Data Engineering",
        "ETL",
        "ELT",
        "PySpark",
        "Spark",
        "Azure",
        "Databricks",
        "Azure ML",
        "Docker",
        "CI/CD",
        "FastAPI",
        "SQLAlchemy",
        "PostgreSQL",
        "Oracle",
        "Snowflake",
        "BigQuery",
        "Data Modeling",
        "MLOps",
        "Forecasting",
        "Time Series",
        "Anomaly Detection",
        "R Shiny",
        "Plotly",
        "DAX",
        "Power Query",
        "Data Pipelines",
        "Agents IA",
        "Codex",
        "Consultant Data",
        "Business Intelligence",
    ]

    found: list[str] = []
    haystack = cv_text.casefold()
    for term in known_terms:
        if term.casefold() in haystack and term not in found:
            found.append(term)
    if len(found) >= limit:
        return found[:limit]

    tokens = re.findall(r"\b[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9+#./-]{2,}\b", cv_text)
    stop = {
        "avec",
        "dans",
        "pour",
        "des",
        "les",
        "une",
        "the",
        "and",
        "contexte",
        "stack",
        "réalisations",
    }
    counts: dict[str, int] = {}
    for token in tokens:
        key = token.strip(".,;:()[]").casefold()
        if len(key) < 4 or key in stop:
            continue
        counts[token] = counts.get(token, 0) + 1
    for token, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        if token not in found:
            found.append(token)
        if len(found) >= limit:
            break
    return found[:limit]
