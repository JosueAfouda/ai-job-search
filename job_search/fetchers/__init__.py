from __future__ import annotations

from .apec import ApecFetcher
from .base import BaseFetcher
from .france_travail import FranceTravailFetcher
from .free_work import FreeWorkFetcher
from .hellowork import HelloWorkFetcher
from .indeed import IndeedFetcher
from .meteojob import MeteoJobFetcher
from .upwork import UpworkFetcher
from .welcome_to_the_jungle import WelcomeToTheJungleFetcher


FETCHERS: dict[str, type[BaseFetcher]] = {
    "france_travail": FranceTravailFetcher,
    "hellowork": HelloWorkFetcher,
    "apec": ApecFetcher,
    "indeed": IndeedFetcher,
    "free_work": FreeWorkFetcher,
    "meteojob": MeteoJobFetcher,
    "upwork": UpworkFetcher,
    "welcome_to_the_jungle": WelcomeToTheJungleFetcher,
}

DEFAULT_SOURCE_NAMES = tuple(FETCHERS)


def build_fetchers(names: list[str] | None = None) -> list[BaseFetcher]:
    selected = names or list(DEFAULT_SOURCE_NAMES)
    fetchers: list[BaseFetcher] = []
    for name in selected:
        key = name.strip().lower().replace("-", "_")
        if key == "all":
            return [cls() for cls in FETCHERS.values()]
        cls = FETCHERS.get(key)
        if cls is None:
            available = ", ".join(sorted(FETCHERS))
            raise ValueError(f"Unknown source '{name}'. Available: {available}, all")
        fetchers.append(cls())
    return fetchers
