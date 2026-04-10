from __future__ import annotations

import re

from .base import BaseFetcher, urlencode


class FreeWorkFetcher(BaseFetcher):
    source = "Free-Work"

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        params = {"query": query, "locations": location or "France"}
        url = "https://www.free-work.com/fr/tech-it/jobs?" + urlencode(params)
        return self.jobs_from_search_page(
            url,
            [
                re.compile(r"free-work\.com/fr/tech-it/.+/job-mission/", re.I),
                re.compile(r"free-work\.com/fr/tech-it/jobs/.+", re.I),
                re.compile(r"free-work\.com/fr/tech-it/freelance-missions/.+", re.I),
            ],
            limit,
        )
