import logging
import requests
from typing import List

from .base import Source, Job

log = logging.getLogger(__name__)

API_URL = "https://arbeitnow.com/api/job-board-api"


class Arbeitnow(Source):
    """EU-focused job board with visa sponsorship data. Good for non-EU citizens."""

    name = "arbeitnow"

    def fetch(self) -> List[Job]:
        try:
            r = requests.get(API_URL, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("arbeitnow fetch failed: %s", e)
            return []

        jobs: List[Job] = []
        for item in data.get("data", []):
            slug = item.get("slug") or item.get("url") or ""
            if not slug:
                continue
            title = item.get("title") or ""
            company = item.get("company_name") or ""
            url = item.get("url") or f"https://arbeitnow.com/jobs/{slug}"
            desc = item.get("description") or ""
            tags = item.get("tags") or []
            remote = item.get("remote", False)
            visa = item.get("visa_sponsorship", False)
            location = "Remote" if remote else (item.get("location") or "")
            if visa:
                tags = list(tags) + ["visa sponsorship"]
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(slug),
                    title=title[:200],
                    company=company,
                    url=url,
                    description=desc[:1500],
                    tags=[str(t) for t in tags],
                    location=location,
                    posted_at=str(item.get("created_at") or ""),
                )
            )
        log.info("arbeitnow: collected %d posts", len(jobs))
        return jobs
