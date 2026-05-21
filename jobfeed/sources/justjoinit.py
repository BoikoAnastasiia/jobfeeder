import logging
import requests
from typing import List

from .base import Source, Job

log = logging.getLogger(__name__)

# JustJoin.it is a major EU (PL) tech board with frequent listings hiring
# Ukrainian/EU-based remote engineers. The public v2 offers endpoint returns
# paginated job summaries.
API_URL = "https://api.justjoin.it/v2/user-panel/offers"


class JustJoinIt(Source):
    name = "justjoinit"

    def __init__(self, max_pages: int = 2, per_page: int = 100):
        self.max_pages = max_pages
        self.per_page = per_page

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []
        # JustJoin.it indexes one role under multiple category slugs, so the
        # same job comes back several times with different trailing slugs.
        # Dedupe within a fetch by (company, title) lowercased.
        seen_pairs = set()
        for page in range(1, self.max_pages + 1):
            params = {"page": page, "perPage": self.per_page, "sortBy": "newest"}
            try:
                r = requests.get(
                    API_URL,
                    params=params,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept": "application/json",
                        "Version": "2",
                    },
                    timeout=20,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                log.warning("justjoinit page %s failed: %s", page, e)
                break

            items = data.get("data") or data.get("items") or []
            if not items:
                break

            for item in items:
                slug = item.get("slug") or item.get("id") or ""
                if not slug:
                    continue
                title = item.get("title") or ""
                company = (item.get("companyName") or item.get("company_name") or "")
                pair = (company.lower().strip(), title.lower().strip())
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                city = (item.get("city") or "")
                remote = item.get("remote") or item.get("workplaceType") == "remote"
                tags = []
                for skill in (item.get("requiredSkills") or item.get("skills") or []):
                    if isinstance(skill, dict):
                        tags.append(skill.get("name", ""))
                    else:
                        tags.append(str(skill))
                if remote:
                    tags.append("remote")
                url = f"https://justjoin.it/offers/{slug}"
                location = "Remote" if remote else city
                jobs.append(
                    Job(
                        source=self.name,
                        external_id=str(slug),
                        title=title[:200],
                        company=company,
                        url=url,
                        description="",
                        tags=tags,
                        location=location,
                        posted_at=str(item.get("publishedAt") or ""),
                    )
                )
        log.info("justjoinit: collected %d posts", len(jobs))
        return jobs
