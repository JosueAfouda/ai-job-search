from __future__ import annotations

import re

from .base import BaseFetcher, urlencode


class WelcomeToTheJungleFetcher(BaseFetcher):
    source = "Welcome to the Jungle"

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        params = {"query": query, "aroundQuery": location or "France"}
        url = "https://www.welcometothejungle.com/fr/jobs?" + urlencode(params)
        return self.jobs_from_search_page(
            url,
            [
                re.compile(r"welcometothejungle\.com/fr/companies/.+/jobs/.+", re.I),
                re.compile(r"welcometothejungle\.com/fr/jobs/.+", re.I),
            ],
            limit,
        )
