from __future__ import annotations

import re
from pathlib import Path

from .cv_loader import CandidateProfile
from .llm import CodexClient, CodexError
from .models import Job, ScoreResult
from .utils import redact_phone_numbers, truncate


SCORE_SCHEMA = Path(__file__).with_name("schemas") / "score.schema.json"


SCORING_PROMPT = """You are scoring a job against a candidate CV for a France-focused job search.

Return STRICT JSON only:
{{
  "score": float,
  "reason": "short explanation"
}}

Scoring scale:
- 5.0: excellent match; apply immediately
- 4.0-4.9: good match; keep
- 3.0-3.9: partial match
- 1.0-2.9: weak match

Evaluate:
- Skills match
- Experience relevance
- Seniority alignment
- Domain relevance

Do not invent candidate experience. Do not mention phone numbers.

Candidate CV:
{cv_text}

Job:
Title: {title}
Company: {company}
Location: {location}
Source: {source}
URL: {url}
Description:
{description}
"""


def score_job(
    job: Job,
    candidate: CandidateProfile,
    codex: CodexClient,
    use_llm: bool = True,
) -> ScoreResult:
    if use_llm:
        prompt = SCORING_PROMPT.format(
            cv_text=truncate(redact_phone_numbers(candidate.text), 14000),
            title=job.title,
            company=job.company,
            location=job.location,
            source=job.source,
            url=job.url,
            description=truncate(job.description, 9000),
        )
        try:
            payload = codex.run_json(prompt, SCORE_SCHEMA)
            return ScoreResult(
                score=_bound_score(float(payload["score"])),
                reason=str(payload["reason"]).strip(),
                method="codex",
            )
        except (CodexError, KeyError, TypeError, ValueError):
            pass

    return heuristic_score(job, candidate)


def heuristic_score(job: Job, candidate: CandidateProfile) -> ScoreResult:
    haystack = f"{job.title}\n{job.description}".casefold()
    keywords = [keyword for keyword in candidate.keywords if keyword.casefold() in haystack]

    core_terms = {
        "python",
        "sql",
        "power bi",
        "machine learning",
        "data engineering",
        "etl",
        "pyspark",
        "spark",
        "azure",
        "databricks",
        "mlops",
        "forecasting",
        "nlp",
    }
    core_hits = sorted(term for term in core_terms if term in haystack)

    score = 1.6
    score += min(len(core_hits) * 0.28, 1.7)
    score += min(len(keywords) * 0.08, 0.9)

    if re.search(r"\b(data|bi|business intelligence|analytics|ia|ai|machine learning|ml|consultant)\b", haystack):
        score += 0.5
    if re.search(r"\b(senior|confirm[eé]|lead|consultant|expert)\b", haystack):
        score += 0.25
    if re.search(r"\b(alternance|stage|intern|junior)\b", haystack):
        score -= 0.9
    if re.search(r"\b(java|php|ios|android|mainframe|cobol)\b", haystack):
        score -= 0.5

    bounded = _bound_score(score)
    reason = (
        f"Heuristic match: {', '.join(core_hits[:8]) or 'few direct core skills'}; "
        f"{len(keywords)} CV keywords detected."
    )
    return ScoreResult(score=bounded, reason=reason, method="heuristic")


def _bound_score(score: float) -> float:
    return round(max(1.0, min(5.0, score)), 1)
