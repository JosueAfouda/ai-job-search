from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_PROFILE_PATH = Path(__file__).resolve().parent.parent / "search_profile.json"


def normalized_text(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def has_term(text: str, term: str) -> bool:
    """Match whole terms, ignoring accents, case and whitespace variations."""
    pattern = r"\s+".join(re.escape(part) for part in normalized_text(term).split())
    return bool(pattern and re.search(r"(?<!\w)" + pattern + r"(?!\w)", normalized_text(text)))


@dataclass(slots=True)
class SearchProfile:
    headline: str
    queries: list[str]
    target_roles: list[str]
    required_skills: list[str]
    priority_skills: dict[str, list[str]]
    supporting_skills: list[str]
    excluded_titles: list[str]
    seniority: str = "senior"
    remote_policy: str = "any"
    location: str = "France"
    max_job_age_days: int = 14
    min_yearly_salary_eur: int = 40000

    def vocabulary(self) -> list[str]:
        return list(dict.fromkeys([
            *self.required_skills,
            *(term for terms in self.priority_skills.values() for term in terms),
            *self.supporting_skills,
        ]))

    def prompt_context(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def load_search_profile(path: Path = DEFAULT_PROFILE_PATH) -> SearchProfile:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Le profil doit être un objet JSON.")
    try:
        profile = SearchProfile(**payload)
    except TypeError as exc:
        raise ValueError(f"Profil invalide : {exc}") from exc
    for name in ("headline", "location"):
        value = getattr(profile, name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} doit être un texte non vide.")
    for name in ("queries", "target_roles", "required_skills", "supporting_skills", "excluded_titles"):
        _validate_terms(getattr(profile, name), name, required=name in {"queries", "target_roles"})
    if not isinstance(profile.priority_skills, dict) or not profile.priority_skills:
        raise ValueError("priority_skills doit contenir au moins un groupe de compétences.")
    for name, terms in profile.priority_skills.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Chaque groupe de compétences doit avoir un nom.")
        _validate_terms(terms, name, required=True)
    if profile.seniority not in ("senior", "any"):
        raise ValueError("seniority : valeurs autorisées = senior, any.")
    if profile.remote_policy not in ("prefer", "required", "any"):
        raise ValueError("remote_policy : valeurs autorisées = prefer, required, any.")
    for name in ("max_job_age_days", "min_yearly_salary_eur"):
        value = getattr(profile, name)
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} doit être un entier positif ou nul.")
    return profile


def _validate_terms(value: object, name: str, required: bool = False) -> None:
    if not isinstance(value, list) or (required and not value):
        raise ValueError(f"{name} doit être une liste de textes{' non vide' if required else ''}.")
    if any(not isinstance(term, str) or not term.strip() for term in value):
        raise ValueError(f"{name} contient un terme vide ou invalide.")
