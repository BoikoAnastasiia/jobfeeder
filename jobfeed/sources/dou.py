import html
import logging
import re
from typing import List
from urllib.parse import urlparse, urlunparse

import feedparser
import requests

from .base import Source, Job

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; job-feed-bot/1.0)"

# Category feed, e.g. .../vacancies/feeds/?category=Front+End&remote
CATEGORY_FEED = "https://jobs.dou.ua/vacancies/feeds/"
# Per-company feed, e.g. .../vacancies/techmagic/feeds/
# Note: the `company=` query param on the category feed is silently ignored by
# DOU (it returns every vacancy), so company filtering has to use this path.
COMPANY_FEED = "https://jobs.dou.ua/vacancies/{company}/feeds/"

DEFAULT_CATEGORIES = ["Front End", "Fullstack", "JavaScript", "Node.js"]

# DOU writes titles as "<role> в <Company>, <salary?>, <locations>" and its
# locations are Ukrainian, so they'd never match the English EU/remote gate in
# filter.py. Translate the two markers that gate cares about, and tag every job
# "ukraine" — DOU is a Ukrainian board, same as what djinni.py does.
LOCATION_WORDS = {
    "віддалено": "remote",
    "за кордоном": "abroad",
}

VACANCY_ID_RE = re.compile(r"/vacancies/(\d+)/")
TAG_RE = re.compile(r"<[^>]+>")
COMPANY_SLUG_RE = re.compile(r"jobs\.dou\.ua/companies/([^/]+)/")
# DOU slots the salary between company and locations, e.g. "$2000–2500", "до $4000".
PAY_RE = re.compile(r"[$€₴]|\bдо\s|\bвід\s")


def _strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", s or ""))).strip()


def _canonical(link: str) -> str:
    """Drop the ?utm_source=jobsrss tracking query so links dedupe cleanly."""
    p = urlparse(link)
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def _split_title(raw: str):
    """"Senior dev в Acme, $2000–2500, віддалено" -> role, company, where, pay."""
    raw = _strip_html(raw)
    role, sep, rest = raw.rpartition(" в ")
    if not sep:
        return raw.strip(), "", "ukraine", ""
    parts = [p.strip() for p in rest.split(",")]
    company = parts[0] if parts else ""
    where, pay = [], []
    for p in parts[1:]:
        if not p:
            continue
        (pay if PAY_RE.search(p) else where).append(LOCATION_WORDS.get(p.lower(), p))
    # "ukraine" is what carries a DOU job past require_remote_or_eu.
    where.append("ukraine")
    return role.strip(), company, ", ".join(where), ", ".join(pay)


class Dou(Source):
    """jobs.dou.ua — the biggest Ukrainian board. Carries roles that never
    reach Djinni, and company feeds catch postings a category feed misses."""

    name = "dou"

    def __init__(
        self,
        categories: List[str] = None,
        companies: List[str] = None,
        remote_only: bool = False,
    ):
        self.categories = categories if categories is not None else DEFAULT_CATEGORIES
        # Company slugs as they appear in the URL, e.g. "techmagic" from
        # https://jobs.dou.ua/companies/techmagic/vacancies/
        self.companies = companies or []
        self.remote_only = remote_only

    def _feeds(self):
        for cat in self.categories:
            params = {"category": cat}
            if self.remote_only:
                # DOU takes `remote` as a valueless flag.
                yield cat, CATEGORY_FEED + "?remote", params
            else:
                yield cat, CATEGORY_FEED, params
        for slug in self.companies:
            yield slug, COMPANY_FEED.format(company=slug), None

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []
        seen_links = set()
        for label, url, params in self._feeds():
            try:
                r = requests.get(
                    url, params=params, headers={"User-Agent": UA}, timeout=20
                )
                r.raise_for_status()
                parsed = feedparser.parse(r.text)
            except Exception as e:
                log.warning("dou feed %s failed: %s", label, e)
                continue

            for entry in parsed.entries:
                link = _canonical(entry.get("link") or "")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                role, company, where, pay = _split_title(entry.get("title") or "")
                if not company:
                    m = COMPANY_SLUG_RE.search(link)
                    company = m.group(1) if m else ""

                m = VACANCY_ID_RE.search(link)
                jobs.append(
                    Job(
                        source=self.name,
                        external_id=m.group(1) if m else link,
                        title=role[:200],
                        company=company[:120],
                        url=link,
                        description=_strip_html(entry.get("summary") or "")[:1500],
                        tags=[label] + ([pay] if pay else []),
                        location=where,
                        posted_at=entry.get("published", ""),
                    )
                )
        log.info("dou: collected %d posts", len(jobs))
        return jobs
