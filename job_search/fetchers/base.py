from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from ..models import Job
from ..utils import clean_text, truncate


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122 Safari/537.36 career-ops"
)


class FetchError(RuntimeError):
    pass


@dataclass(slots=True)
class Anchor:
    href: str
    text: str


class AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[Anchor] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {key.lower(): value for key, value in attrs if value is not None}
        href = attrs_dict.get("href")
        if href:
            self._href = href
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            text = clean_text(" ".join(self._parts))
            self.anchors.append(Anchor(self._href, text))
            self._href = None
            self._parts = []


class BaseFetcher:
    source = "base"
    timeout = 20

    def search(self, query: str, location: str, limit: int) -> list[Job]:
        raise NotImplementedError

    def fetch_html(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise FetchError(f"{self.source}: failed to fetch {url}: {exc}") from exc
        return raw.decode("utf-8", errors="replace")

    def jobs_from_search_page(
        self,
        search_url: str,
        link_patterns: list[re.Pattern[str]],
        limit: int,
    ) -> list[Job]:
        html = self.fetch_html(search_url)
        jobs = extract_json_ld_jobs(html, search_url, self.source)
        if jobs:
            return jobs[:limit]

        collector = AnchorCollector()
        collector.feed(html)
        detail_urls: list[str] = []
        seen: set[str] = set()
        for anchor in collector.anchors:
            if not anchor.text or len(anchor.text) < 4:
                continue
            absolute = urllib.parse.urljoin(search_url, anchor.href)
            if not any(pattern.search(absolute) for pattern in link_patterns):
                continue
            key = absolute.split("#", 1)[0]
            if key in seen:
                continue
            seen.add(key)
            detail_urls.append(key)
            if len(detail_urls) >= limit:
                break

        detail_jobs: list[Job] = []
        for url in detail_urls:
            try:
                detail_jobs.append(self.job_from_detail_page(url))
            except FetchError:
                continue
        return detail_jobs

    def job_from_detail_page(self, url: str) -> Job:
        html = self.fetch_html(url)
        jobs = extract_json_ld_jobs(html, url, self.source)
        if jobs:
            return jobs[0]

        title = extract_tag_text(html, "title") or "Unknown role"
        company = extract_meta(html, "og:site_name") or self.source
        description = extract_meta(html, "description") or clean_text(html)
        return Job(
            title=title,
            company=company,
            location="France",
            description=truncate(description, 8000),
            url=url,
            source=self.source,
        )


def urlencode(params: dict[str, str]) -> str:
    return urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def extract_json_ld_jobs(html: str, base_url: str, source: str) -> list[Job]:
    scripts = re.findall(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    jobs: list[Job] = []
    for script in scripts:
        text = clean_script_json(script)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        for item in iter_json_ld_items(payload):
            item_type = item.get("@type") or item.get("type") or ""
            if isinstance(item_type, list):
                is_job = any(str(value).casefold() == "jobposting" for value in item_type)
            else:
                is_job = str(item_type).casefold() == "jobposting"
            if not is_job:
                continue
            jobs.append(job_from_json_ld(item, base_url, source))
    return jobs


def clean_script_json(value: str) -> str:
    value = value.strip()
    value = value.replace("&quot;", '"').replace("&amp;", "&")
    return value


def iter_json_ld_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items: list[dict[str, Any]] = []
        if "@graph" in payload:
            items.extend(iter_json_ld_items(payload["@graph"]))
        else:
            items.append(payload)
        return items
    if isinstance(payload, list):
        items = []
        for item in payload:
            items.extend(iter_json_ld_items(item))
        return items
    return []


def job_from_json_ld(item: dict[str, Any], base_url: str, source: str) -> Job:
    org = item.get("hiringOrganization") or {}
    place = item.get("jobLocation") or {}
    if isinstance(place, list):
        place = place[0] if place else {}
    address = place.get("address") if isinstance(place, dict) else {}
    if isinstance(address, str):
        location = address
    elif isinstance(address, dict):
        location = ", ".join(
            clean_text(str(address.get(key, "")))
            for key in ("addressLocality", "addressRegion", "addressCountry")
            if address.get(key)
        )
    else:
        location = "France"

    url = item.get("url") or base_url
    return Job(
        title=clean_text(str(item.get("title") or "Unknown role")),
        company=clean_text(str(org.get("name") if isinstance(org, dict) else org or "Unknown company")),
        location=location or "France",
        description=truncate(clean_text(str(item.get("description") or "")), 12000),
        url=urllib.parse.urljoin(base_url, str(url)),
        source=source,
        raw={"json_ld": item},
    )


def extract_tag_text(html: str, tag: str) -> str:
    match = re.search(fr"<{tag}[^>]*>(.*?)</{tag}>", html, flags=re.IGNORECASE | re.DOTALL)
    return clean_text(match.group(1)) if match else ""


def extract_meta(html: str, name: str) -> str:
    escaped = re.escape(name)
    patterns = [
        fr'<meta[^>]+(?:name|property)=["\']{escaped}["\'][^>]+content=["\']([^"\']+)["\']',
        fr'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\']{escaped}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return clean_text(match.group(1))
    return ""
