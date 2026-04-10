from __future__ import annotations

import re

from .base import BaseFetcher, urlencode


class HelloWorkFetcher(BaseFetcher):
    source = "HelloWork"

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        params = {"k": query, "l": location or "France"}
        url = "https://www.hellowork.com/fr-fr/emploi/recherche.html?" + urlencode(params)
        return self.jobs_from_search_page(
            url,
            [
                re.compile(r"hellowork\.com/fr-fr/emplois/\d+", re.I),
                re.compile(r"hellowork\.com/fr-fr/emploi/.+\.html", re.I),
            ],
            limit,
        )
