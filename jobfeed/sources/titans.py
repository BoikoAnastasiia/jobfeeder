import html
import logging
import re
import requests
from typing import List

from .base import Source, Job

log = logging.getLogger(__name__)

# join.titans.eu — Slovak/Czech IT contracting agency. No API; the job list is
# server-rendered HTML. Open positions are listed first, filled ones (marked
# "occupied") after, so we page until the first filled card. robots.txt only
# allows plain /en/?pagenum=N, not the onlyOpen/type filter params.
LIST_URL = "https://join.titans.eu/en/"

_CARD_SPLIT = re.compile(r"<a\s+onclick=\"sendGtmEvent\('position_list_apply_click'")


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


class Titans(Source):
    name = "titans"

    def __init__(self, max_pages: int = 5):
        self.max_pages = max_pages

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []
        for page in range(1, self.max_pages + 1):
            try:
                r = requests.get(
                    LIST_URL,
                    params={"pagenum": page} if page > 1 else None,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=20,
                )
                r.raise_for_status()
            except Exception as e:
                log.warning("titans page %s failed: %s", page, e)
                break

            cards = _CARD_SPLIT.split(r.text)[1:]
            if not cards:
                break
            reached_filled = False
            for card in cards:
                cls = re.search(r'class="(it-project[^"]*)"', card)
                if cls and "occupied" in cls.group(1):
                    reached_filled = True
                    break
                job = self._parse_card(card)
                if job:
                    jobs.append(job)
            if reached_filled:
                break
        log.info("titans: collected %d open posts", len(jobs))
        return jobs

    def _parse_card(self, card: str):
        url = re.search(r'href="(https://join\.titans\.eu/[^"]+)"', card)
        title = re.search(r'data-position_name="([^"]*)"', card)
        card_id = re.search(r'\bid="(\d+)"', card)
        if not (url and title and card_id):
            return None

        location = re.search(r'project-location-value">.*?<span>(.*?)</span>', card, re.S)
        salary = re.search(r'project-salary-value">(.*?)<span', card, re.S)
        # Tech buttons carry data-cy="project-language-<Tech>-value"; the
        # spoken-language buttons are the ones with an empty name.
        tech = re.findall(r'data-cy="project-language-[^"]+-value"\s*>(.*?)</div>', card, re.S)
        languages = re.findall(r'data-cy="project-language--value"\s*>(.*?)</div>', card, re.S)
        labels = re.findall(r'<div class="(?:tag[^"]*|button inverted)"[^>]*>(.*?)</div>', card, re.S)

        tags = [_text(t) for t in tech + labels]
        return Job(
            source=self.name,
            external_id=card_id.group(1),
            title=_text(title.group(1))[:200],
            company="Titans (contract)",
            url=url.group(1),
            description=_text(salary.group(1)) if salary else "",
            tags=[t for t in tags if t],
            location=_text(location.group(1)) if location else "",
            languages=[_text(lang) for lang in languages],
        )
