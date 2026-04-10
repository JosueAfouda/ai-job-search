from __future__ import annotations

import re

from .base import BaseFetcher, urlencode


class MeteoJobFetcher(BaseFetcher):
    source = "MeteoJob"

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        params = {"what": query, "where": location or "France"}
        url = "https://www.meteojob.com/jobs?" + urlencode(params)
        return self.jobs_from_search_page(
            url,
            [
                re.compile(r"meteojob\.com/candidat/offres/offre-d-emploi-.+", re.I),
                re.compile(r"meteojob\.com/jobs/.+", re.I),
                re.compile(r"meteojob\.com/.+/emploi-.+", re.I),
            ],
            limit,
        )
