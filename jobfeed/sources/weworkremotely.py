import logging
import feedparser
import requests
from typing import List

from .base import Source, Job

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; job-feed-bot/1.0)"

DEFAULT_FEEDS = [
    "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
]


class WeWorkRemotely(Source):
    name = "weworkremotely"

    def __init__(self, feeds: List[str] = None):
        self.feeds = feeds or DEFAULT_FEEDS

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []
        seen_links = set()
        for url in self.feeds:
            try:
                # feedparser doesn't send a User-Agent by default and WWR's
                # CDN blocks blank UAs — fetch via requests first.
                r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
                r.raise_for_status()
                parsed = feedparser.parse(r.text)
            except Exception as e:
                log.warning("wwr feed %s failed: %s", url, e)
                continue
            for entry in parsed.entries:
                link = entry.get("link", "")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                title = entry.get("title", "")
                # WWR titles look like "Company: Job Title"
                company = ""
                job_title = title
                if ":" in title:
                    company, _, job_title = title.partition(":")
                    company = company.strip()
                    job_title = job_title.strip()
                summary = entry.get("summary", "")
                ext_id = entry.get("id") or link
                jobs.append(
                    Job(
                        source=self.name,
                        external_id=ext_id,
                        title=job_title[:200],
                        company=company,
                        url=link,
                        description=summary[:1500],
                        tags=[],
                        posted_at=entry.get("published", ""),
                    )
                )
        log.info("wwr: collected %d posts", len(jobs))
        return jobs
