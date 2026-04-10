from __future__ import annotations

import re

from .base import BaseFetcher, urlencode


class ApecFetcher(BaseFetcher):
    source = "Apec"

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        params = {"motsCles": query, "lieux": location or "France"}
        url = "https://www.apec.fr/candidat/recherche-emploi.html/emploi?" + urlencode(params)
        return self.jobs_from_search_page(
            url,
            [
                re.compile(r"apec\.fr/candidat/recherche-emploi\.html/emploi/detail-offre/", re.I),
                re.compile(r"apec\.fr/.+/detail-offre/", re.I),
            ],
            limit,
        )
