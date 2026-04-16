from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Job:
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    raw: dict[str, Any] = field(default_factory=dict)

    def key(self) -> tuple[str, str, str]:
        return (
            self.title.strip().casefold(),
            self.company.strip().casefold(),
            self.url.strip().casefold(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScoreResult:
    score: float
    reason: str
    method: str = "codex"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MatchedJob:
    job: Job
    score: ScoreResult
    tailored_cv_path: str | None = None
    cover_letter_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "score": self.score.to_dict(),
            "tailored_cv_path": self.tailored_cv_path,
            "cover_letter_path": self.cover_letter_path,
        }
