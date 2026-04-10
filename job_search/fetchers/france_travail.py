from __future__ import annotations

import re

from .base import BaseFetcher, urlencode


class FranceTravailFetcher(BaseFetcher):
    source = "France Travail"

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        params = {
            "motsCles": query,
            "lieux": location or "France",
            "offresPartenaires": "true",
        }
        url = "https://candidat.francetravail.fr/offres/recherche?" + urlencode(params)
        return self.jobs_from_search_page(
            url,
            [
                re.compile(r"candidat\.francetravail\.fr/offres/recherche/detail/", re.I),
                re.compile(r"candidat\.francetravail\.fr/offres/emploi/", re.I),
            ],
            limit,
        )
