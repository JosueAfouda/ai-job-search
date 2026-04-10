from __future__ import annotations

from pathlib import Path

from .cv_loader import CandidateProfile
from .llm import CodexClient, CodexError
from .models import Job
from .utils import ensure_dir, redact_phone_numbers, slugify, truncate


TAILOR_PROMPT = """You are tailoring a CV for a specific job.

Return markdown only. Keep the CV professional, concise, ATS-friendly, and truthful.
Keep the same broad structure as the original CV. You may reorder skills and rephrase existing
experience to match the job, but you must not invent employers, dates, tools, metrics, degrees, or
responsibilities. Do not include a phone number.

Candidate CV:
{cv_text}

Target job:
Title: {title}
Company: {company}
Location: {location}
URL: {url}
Description:
{description}
"""


def tailored_cv_filename(job: Job) -> str:
    return f"{slugify(job.company, 45)}_{slugify(job.title, 55)}.md"


def generate_tailored_cv(
    job: Job,
    candidate: CandidateProfile,
    codex: CodexClient,
    output_dir: Path,
    use_llm: bool = True,
) -> Path:
    ensure_dir(output_dir)
    path = output_dir / tailored_cv_filename(job)

    if use_llm:
        prompt = TAILOR_PROMPT.format(
            cv_text=truncate(redact_phone_numbers(candidate.text), 18000),
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            description=truncate(job.description, 10000),
        )
        try:
            content = codex.run_text(prompt, timeout_seconds=240).strip()
            if content:
                path.write_text(content + "\n", encoding="utf-8")
                return path
        except CodexError:
            pass

    path.write_text(_fallback_tailored_cv(job, candidate), encoding="utf-8")
    return path


def _fallback_tailored_cv(job: Job, candidate: CandidateProfile) -> str:
    safe_cv = redact_phone_numbers(candidate.text)
    job_terms = ", ".join(_top_job_terms(job.description))
    return f"""# {candidate.name}

## Target Role

{job.title} - {job.company}

## Professional Summary

Consultant Data & IA with 10+ years of experience across Python, SQL, BI, data pipelines,
machine learning, forecasting, and Azure-oriented delivery. This version emphasizes alignment
with {job.title}: {job_terms or "data, AI, analytics, and delivery"}.

## Core Alignment

- Target company: {job.company}
- Target location: {job.location}
- Job link: {job.url}
- Relevant keywords to preserve in the CV: {job_terms or "Python, SQL, BI, Machine Learning"}

## Original CV Content For Review

{safe_cv}
"""


def _top_job_terms(description: str) -> list[str]:
    preferred = [
        "Python",
        "SQL",
        "Power BI",
        "Machine Learning",
        "Data Engineering",
        "ETL",
        "PySpark",
        "Spark",
        "Azure",
        "Databricks",
        "MLOps",
        "NLP",
        "Forecasting",
        "BI",
        "Consulting",
    ]
    haystack = description.casefold()
    return [term for term in preferred if term.casefold() in haystack][:10]
