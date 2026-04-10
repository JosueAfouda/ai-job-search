from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .cv_loader import CandidateProfile, load_cv
from .fetchers import build_fetchers
from .fetchers.base import FetchError
from .llm import CodexClient
from .models import Job, MatchedJob
from .normalizer import normalize_jobs
from .scoring import score_job
from .tailoring import generate_tailored_cv
from .utils import ensure_dir


DEFAULT_QUERY = "Data Python"


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
        matched.append(
            MatchedJob(
                job=job,
                score=score,
                tailored_cv_path=str(tailored_path),
            )
        )

    save_matches(options.output_json, matched)
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
