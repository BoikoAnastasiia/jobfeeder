import logging
import requests
from typing import List

from .base import Source, Job

log = logging.getLogger(__name__)

REMOTEOK_API = "https://remoteok.com/api"
UA = "job-feed-bot (+https://github.com/)"


class RemoteOK(Source):
    name = "remoteok"

    def fetch(self) -> List[Job]:
        try:
            r = requests.get(REMOTEOK_API, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("remoteok fetch failed: %s", e)
            return []

        # First element is a legal/disclaimer object; skip non-job entries.
        jobs: List[Job] = []
        for item in data:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            position = item.get("position") or item.get("title") or ""
            company = item.get("company") or ""
            url = item.get("url") or item.get("apply_url") or ""
            desc = item.get("description") or ""
            tags = item.get("tags") or []
            location = item.get("location") or ""
            posted_at = item.get("date") or ""
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(item["id"]),
                    title=position[:200],
                    company=company,
                    url=url,
                    description=(desc or "")[:1500],
                    tags=[str(t) for t in tags],
                    location=location,
                    posted_at=str(posted_at),
                )
            )
        log.info("remoteok: collected %d posts", len(jobs))
        return jobs
