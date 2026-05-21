import logging
import requests
from typing import List

from .base import Source, Job

log = logging.getLogger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"
CATEGORIES = ["software-dev", "design"]


class Remotive(Source):
    name = "remotive"

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []
        seen_ids = set()
        for category in CATEGORIES:
            try:
                r = requests.get(
                    API_URL,
                    params={"category": category, "limit": 100},
                    timeout=20,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                log.warning("remotive category %s failed: %s", category, e)
                continue
            for item in data.get("jobs", []):
                item_id = str(item.get("id") or "")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                tags = item.get("tags") or []
                jobs.append(
                    Job(
                        source=self.name,
                        external_id=item_id,
                        title=(item.get("title") or "")[:200],
                        company=item.get("company_name") or "",
                        url=item.get("url") or "",
                        description=(item.get("description") or "")[:1500],
                        tags=[str(t) for t in tags],
                        location=item.get("candidate_required_location") or "Remote",
                        posted_at=str(item.get("publication_date") or ""),
                    )
                )
        log.info("remotive: collected %d posts", len(jobs))
        return jobs
