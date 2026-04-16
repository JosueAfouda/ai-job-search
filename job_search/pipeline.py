from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .cover_letter import generate_cover_letter
from .cv_loader import CandidateProfile, load_cv
from .fetchers import build_fetchers
from .fetchers.base import FetchError
from .llm import CodexClient
from .models import Job, MatchedJob
from .normalizer import normalize_jobs
from .scoring import score_job
from .tailoring import generate_tailored_cv
from .utils import clean_text, ensure_dir


DEFAULT_QUERY = "Data Python"
MAX_JOB_AGE_DAYS = 14
MIN_YEARLY_SALARY_EUR = 40_000


@dataclass(slots=True)
class PipelineOptions:
    cv_path: Path = Path("Consultant_Data_Josue_Afouda.pdf")
    query: str = DEFAULT_QUERY
    location: str = "France"
    sources: list[str] | None = None
    max_per_source: int = 5
    threshold: float = 4.0
    output_json: Path = Path("matched_jobs.json")
    tailored_dir: Path = Path("tailored_cvs")
    cover_letter_dir: Path = Path("cover_letters")
    report_path: Path = Path("job_search_results.md")
    use_llm: bool = True
    sample: bool = False


@dataclass(slots=True)
class PipelineRun:
    candidate: CandidateProfile
    fetched_jobs: list[Job]
    matched_jobs: list[MatchedJob]
    errors: list[str]


def run_pipeline(options: PipelineOptions, cwd: Path | None = None) -> PipelineRun:
    project_dir = cwd or Path.cwd()
    candidate = load_cv(options.cv_path)
    jobs, errors = fetch_jobs(options)
    jobs = normalize_jobs(jobs)
    jobs = filter_jobs(jobs)

    codex = CodexClient(project_dir, enabled=options.use_llm)
    matched: list[MatchedJob] = []

    for job in jobs:
        score = score_job(job, candidate, codex, use_llm=options.use_llm)
        if score.score < options.threshold:
            continue
        tailored_path = generate_tailored_cv(
            job,
            candidate,
            codex,
            options.tailored_dir,
            use_llm=options.use_llm,
        )
        cover_letter_path = generate_cover_letter(
            job,
            tailored_path.read_text(encoding="utf-8"),
            codex,
            options.cover_letter_dir,
            use_llm=options.use_llm,
        )
        matched.append(
            MatchedJob(
                job=job,
                score=score,
                tailored_cv_path=str(tailored_path),
                cover_letter_path=str(cover_letter_path),
            )
        )

    save_matches(options.output_json, matched)
    save_markdown_report(options.report_path, jobs, matched)
    return PipelineRun(candidate=candidate, fetched_jobs=jobs, matched_jobs=matched, errors=errors)


def fetch_jobs(options: PipelineOptions) -> tuple[list[Job], list[str]]:
    if options.sample:
        return sample_jobs(), []

    jobs: list[Job] = []
    errors: list[str] = []
    for fetcher in build_fetchers(options.sources):
        try:
            jobs.extend(fetcher.search(options.query, options.location, options.max_per_source))
        except (FetchError, ValueError) as exc:
            errors.append(str(exc))
    return jobs, errors


def save_matches(path: Path, matches: list[MatchedJob]) -> None:
    if path.parent != Path("."):
        ensure_dir(path.parent)
    payload = [match.to_dict() for match in matches]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_markdown_report(path: Path, jobs: list[Job], matches: list[MatchedJob]) -> None:
    if path.parent != Path("."):
        ensure_dir(path.parent)

    lines = [
        "# Agentic Job Search Results",
        "",
        "## Summary",
        f"- Fetched jobs: {len(jobs)}",
        f"- Matched jobs: {len(matches)}",
        "",
        "## Matched Jobs",
        "",
    ]

    if not matches:
        lines.append("No matched jobs.")
    else:
        for match in matches:
            job = match.job
            lines.extend(
                [
                    f"### {job.title} - {job.company}",
                    f"- Score: {match.score.score:.1f}",
                    f"- Reason: {match.score.reason}",
                    f"- Link: {job.url}",
                    f"- Tailored CV: {match.tailored_cv_path or 'N/A'}",
                    f"- Cover Letter: {match.cover_letter_path or 'N/A'}",
                    "",
                ]
            )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def filter_jobs(jobs: list[Job], today: date | None = None) -> list[Job]:
    current_date = today or datetime.now().date()
    return [job for job in jobs if _is_recent_enough(job, current_date) and _is_salary_acceptable(job)]


def _is_recent_enough(job: Job, today: date) -> bool:
    published_date = _extract_job_date(job)
    if published_date is None:
        return True
    return published_date >= today - timedelta(days=MAX_JOB_AGE_DAYS)


def _extract_job_date(job: Job) -> date | None:
    json_ld = _job_json_ld(job)
    if isinstance(json_ld, dict):
        for key in ("datePosted", "dateCreated"):
            parsed = _parse_date_value(json_ld.get(key))
            if parsed is not None:
                return parsed
    for key in ("date_posted", "published_at", "date"):
        parsed = _parse_date_value(job.raw.get(key))
        if parsed is not None:
            return parsed
    return None


def _parse_date_value(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    text = clean_text(str(value))
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1))
        except ValueError:
            return None

    fr_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text)
    if fr_match:
        day, month, year = (int(part) for part in fr_match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _is_salary_acceptable(job: Job) -> bool:
    floor = _extract_salary_floor(job)
    return floor is None or floor >= MIN_YEARLY_SALARY_EUR


def _extract_salary_floor(job: Job) -> float | None:
    json_ld = _job_json_ld(job)
    if isinstance(json_ld, dict):
        structured = _salary_from_payload(json_ld.get("baseSalary"))
        if structured is not None:
            return structured
        estimated = _salary_from_payload(json_ld.get("estimatedSalary"))
        if estimated is not None:
            return estimated

    for value in (job.raw.get("salary"), job.raw.get("salary_text"), job.description):
        parsed = _salary_from_text(value)
        if parsed is not None:
            return parsed
    return None


def _salary_from_payload(payload: object) -> float | None:
    if payload is None:
        return None
    if isinstance(payload, (int, float)):
        return float(payload) if payload >= 10_000 else None
    if isinstance(payload, str):
        return _salary_from_text(payload)
    if not isinstance(payload, dict):
        return None

    raw_value = payload.get("value", payload)
    unit = _salary_unit(payload, raw_value)
    currency = _salary_currency(payload, raw_value)
    if currency and currency != "EUR":
        return None

    if isinstance(raw_value, (int, float)):
        return _annualize_salary(float(raw_value), unit)
    if isinstance(raw_value, dict):
        for key in ("minValue", "value", "maxValue"):
            candidate = raw_value.get(key)
            if isinstance(candidate, (int, float)):
                return _annualize_salary(float(candidate), unit)
        return _salary_from_text(json.dumps(raw_value, ensure_ascii=False))
    return None


def _salary_currency(payload: dict[str, object], raw_value: object) -> str:
    if isinstance(raw_value, dict):
        candidate = raw_value.get("currency")
        if isinstance(candidate, str):
            return candidate.strip().upper()
    candidate = payload.get("currency")
    if isinstance(candidate, str):
        return candidate.strip().upper()
    return ""


def _salary_unit(payload: dict[str, object], raw_value: object) -> str:
    if isinstance(raw_value, dict):
        for key in ("unitText", "unitCode"):
            candidate = raw_value.get(key)
            if isinstance(candidate, str):
                return candidate
    for key in ("unitText", "unitCode"):
        candidate = payload.get(key)
        if isinstance(candidate, str):
            return candidate
    return ""


def _salary_from_text(value: object) -> float | None:
    if value is None:
        return None

    text = clean_text(str(value))
    lower = text.casefold()
    if not re.search(r"(?:€|eur|euros?)", lower):
        return None

    amounts: list[float] = []
    for amount_text, kilo_suffix in re.findall(r"(\d[\d\s.,]*)\s*(k)?\s*(?:€|eur|euros?)", lower):
        amount = _parse_amount(amount_text, kilo_suffix)
        if amount is not None:
            amounts.append(amount)
    for amount_text, kilo_suffix in re.findall(r"(?:€|eur|euros?)\s*(\d[\d\s.,]*)\s*(k)?", lower):
        amount = _parse_amount(amount_text, kilo_suffix)
        if amount is not None:
            amounts.append(amount)
    if not amounts:
        return None

    amount = min(amounts)
    if "mois" in lower or "mensuel" in lower or "monthly" in lower or "month" in lower:
        return amount * 12
    if any(token in lower for token in ("an", "annuel", "annuelle", "annual", "year", "yr")):
        return amount
    if amount >= 10_000:
        return amount
    return None


def _parse_amount(value: str, kilo_suffix: str) -> float | None:
    compact = value.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    if not compact:
        return None
    if "," in compact and "." in compact:
        compact = compact.replace(".", "").replace(",", ".")
    elif compact.count(".") >= 1 and len(compact.rsplit(".", 1)[-1]) == 3:
        compact = compact.replace(".", "")
    elif compact.count(",") >= 1 and len(compact.rsplit(",", 1)[-1]) == 3:
        compact = compact.replace(",", "")
    else:
        compact = compact.replace(",", ".")

    try:
        amount = float(compact)
    except ValueError:
        return None
    if kilo_suffix:
        amount *= 1000
    return amount


def _annualize_salary(amount: float, unit: str) -> float | None:
    normalized = clean_text(unit).casefold()
    if normalized in {"", "year", "ann", "annually", "annual", "an", "annee", "annees", "annuel", "annuelle"}:
        return amount if amount >= 10_000 else None
    if normalized in {"month", "mon", "monthly", "mois", "mensuel", "mensuelle"}:
        return amount * 12
    return None


def _job_json_ld(job: Job) -> dict[str, object]:
    payload = job.raw.get("json_ld")
    return payload if isinstance(payload, dict) else {}


def sample_jobs() -> list[Job]:
    return [
        Job(
            title="Consultant Data & IA - Python SQL Power BI",
            company="Example Analytics",
            location="Paris, France",
            description=(
                "Nous recherchons un consultant data senior avec Python, SQL, Power BI, "
                "Machine Learning, Azure Databricks, ETL, forecasting et capacité à accompagner "
                "les métiers dans la mise en production de data products."
            ),
            url="https://example.com/jobs/consultant-data-ia",
            source="sample",
        ),
        Job(
            title="Développeur Mobile Android Junior",
            company="Example Mobile",
            location="Lyon, France",
            description="Stage ou alternance Android Kotlin pour application mobile grand public.",
            url="https://example.com/jobs/android-junior",
            source="sample",
        ),
    ]
