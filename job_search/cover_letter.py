from __future__ import annotations

from pathlib import Path

from .llm import CodexClient, CodexError
from .models import Job
from .tailoring import tailored_cv_filename
from .utils import ensure_dir, truncate


COVER_LETTER_PROMPT = """You are writing a short, high-impact markdown cover letter.

This is not a traditional application letter. It must read like an expert operator who understands
the business problem and can deliver results fast.

Constraints:
- Return markdown only
- Maximum 1000 characters total
- Human, direct, confident
- No generic opening
- Do not say "I am applying for"
- Avoid overly formal language
- Focus on business impact, relevance, and execution
- Align closely with the tailored CV and the job description

Tailored CV:
{tailored_cv}

Target job:
Title: {title}
Company: {company}
Location: {location}
URL: {url}
Description:
{description}
"""


def generate_cover_letter(
    job: Job,
    tailored_cv_text: str,
    codex: CodexClient,
    output_dir: Path,
    use_llm: bool = True,
) -> Path:
    ensure_dir(output_dir)
    path = output_dir / tailored_cv_filename(job)

    if use_llm:
        prompt = COVER_LETTER_PROMPT.format(
            tailored_cv=truncate(tailored_cv_text, 16000),
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            description=truncate(job.description, 10000),
        )
        try:
            content = codex.run_text(prompt, timeout_seconds=240).strip()
            if content:
                path.write_text(_fit_length(content), encoding="utf-8")
                return path
        except CodexError:
            pass

    path.write_text(_fallback_cover_letter(job, tailored_cv_text), encoding="utf-8")
    return path


def _fallback_cover_letter(job: Job, tailored_cv_text: str) -> str:
    priorities = ", ".join(_top_terms(job.description, tailored_cv_text))
    letter = (
        f"# {job.title} - {job.company}\n\n"
        f"Your team needs delivery, not theory. I can step in on {job.title} and turn {priorities or 'data, AI, and analytics priorities'} "
        f"into production work: structured pipelines, decision-ready reporting, and solutions that business teams can actually use.\n\n"
        f"My tailored CV for this role focuses on Python, SQL, BI, machine learning, and consulting execution. "
        f"The fit is straightforward: understand the problem fast, align stakeholders, ship usable outputs, and raise impact without adding noise."
    )
    return _fit_length(letter)


def _top_terms(job_description: str, tailored_cv_text: str) -> list[str]:
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
        "Forecasting",
        "BI",
        "Consulting",
    ]
    haystack = f"{job_description}\n{tailored_cv_text}".casefold()
    return [term for term in preferred if term.casefold() in haystack][:5]


def _fit_length(content: str, limit: int = 1000) -> str:
    text = content.strip()
    if len(text) <= limit:
        return text
    return truncate(text, limit).rstrip()
