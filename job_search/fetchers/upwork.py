from __future__ import annotations

import re

from .base import BaseFetcher, urlencode


class UpworkFetcher(BaseFetcher):
    source = "Upwork"

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        params = {"q": query, "location": location or "France", "sort": "recency"}
        url = "https://www.upwork.com/nx/jobs/search/?" + urlencode(params)
        return self.jobs_from_search_page(
            url,
            [
                re.compile(r"upwork\.com/jobs/.+", re.I),
                re.compile(r"upwork\.com/freelance-jobs/apply/.+", re.I),
            ],
            limit,
        )
