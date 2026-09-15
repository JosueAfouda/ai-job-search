from __future__ import annotations

from .models import Job
from .utils import clean_text, infer_work_mode, truncate


def normalize_jobs(jobs: list[Job]) -> list[Job]:
    normalized: list[Job] = []
    seen: set[tuple[str, str, str]] = set()
    seen_urls: set[str] = set()

    for job in jobs:
        title = clean_text(job.title)
        company = clean_text(job.company) or "Unknown company"
        location = clean_text(job.location) or "France"
        description = truncate(clean_text(job.description), 12000)
        url = clean_text(job.url)
        source = clean_text(job.source)

        if not title or not url:
            continue

        clean_job = Job(
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            source=source,
            raw=job.raw,
            work_mode=job.work_mode if job.work_mode != "unknown" else infer_work_mode(f"{title} {location} {description}"),
        )
        key = clean_job.key()
        url_key = url.split("#", 1)[0]
        if key in seen or url_key in seen_urls:
            continue
        seen.add(key)
        seen_urls.add(url_key)
        normalized.append(clean_job)

    return normalized
