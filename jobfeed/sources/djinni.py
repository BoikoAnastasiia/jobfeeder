import logging
import feedparser
import requests
from typing import List

from .base import Source, Job

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; job-feed-bot/1.0)"

# Djinni RSS feeds filtered by primary keyword.
# Add or remove keywords to match your stack.
DEFAULT_KEYWORDS = ["JavaScript", "TypeScript", "React", "Frontend"]
BASE_RSS = "https://djinni.co/jobs/rss/"


class Djinni(Source):
    """Ukrainian tech job board — great source for EU/remote roles hiring Ukrainian devs."""

    name = "djinni"

    def __init__(self, keywords: List[str] = None, english_level: str = ""):
        self.keywords = keywords or DEFAULT_KEYWORDS
        # english_level options: "" (any), "no_english", "basic", "pre",
        # "intermediate", "upper", "fluent"
        self.english_level = english_level

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []
        seen_links = set()
        for kw in self.keywords:
            params = {"primary_keyword": kw}
            if self.english_level:
                params["english_level"] = self.english_level
            try:
                r = requests.get(BASE_RSS, params=params, headers={"User-Agent": UA}, timeout=20)
                r.raise_for_status()
                parsed = feedparser.parse(r.text)
            except Exception as e:
                log.warning("djinni keyword %s failed: %s", kw, e)
                continue
            for entry in parsed.entries:
                link = entry.get("link") or ""
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                title = entry.get("title") or ""
                summary = entry.get("summary") or ""
                ext_id = entry.get("id") or link
                jobs.append(
                    Job(
                        source=self.name,
                        external_id=ext_id,
                        title=title[:200],
                        company="",
                        url=link,
                        description=summary[:1500],
                        tags=[kw],
                        location="ukraine",
                        posted_at=entry.get("published", ""),
                    )
                )
        log.info("djinni: collected %d posts", len(jobs))
        return jobs
