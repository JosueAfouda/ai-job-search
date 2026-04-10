from __future__ import annotations

import re

from .base import BaseFetcher, urlencode


class IndeedFetcher(BaseFetcher):
    source = "Indeed"

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        params = {"q": query, "l": location or "France"}
        url = "https://fr.indeed.com/jobs?" + urlencode(params)
        return self.jobs_from_search_page(
            url,
            [
                re.compile(r"indeed\.com/viewjob", re.I),
                re.compile(r"fr\.indeed\.com/viewjob", re.I),
                re.compile(r"fr\.indeed\.com/rc/clk", re.I),
                re.compile(r"fr\.indeed\.com/pagead/clk", re.I),
                re.compile(r"fr\.indeed\.com/m/jobs", re.I),
            ],
            limit,
        )
