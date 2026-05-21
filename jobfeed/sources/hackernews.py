import re
import html
import logging
import requests
from typing import List, Optional

from .base import Source, Job

log = logging.getLogger(__name__)

ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
HN_WEB = "https://news.ycombinator.com/item?id={id}"


class HackerNewsWhoIsHiring(Source):
    """
    Pulls top-level comments from the latest 'Ask HN: Who is hiring?' thread.

    You can pin a specific thread ID via config (thread_id), otherwise the latest
    thread is auto-discovered via the HN Algolia search API.
    """

    name = "hackernews"

    def __init__(self, thread_id: Optional[int] = None, max_comments: int = 400):
        self.thread_id = thread_id
        self.max_comments = max_comments

    def _latest_thread_id(self) -> Optional[int]:
        # search_by_date returns hits sorted newest first.
        # whoishiring is a dedicated HN account that posts the monthly thread.
        params = {
            "tags": "story,author_whoishiring",
            "hitsPerPage": 10,
        }
        r = requests.get(ALGOLIA_SEARCH, params=params, timeout=20)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        for hit in hits:
            title = (hit.get("title") or "").lower()
            if "who is hiring" in title:
                return int(hit["objectID"])
        return None

    def _fetch_item(self, item_id: int) -> Optional[dict]:
        try:
            r = requests.get(HN_ITEM.format(id=item_id), timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning("hn item %s failed: %s", item_id, e)
            return None

    @staticmethod
    def _strip_html(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"<p>", "\n\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        return html.unescape(text).strip()

    @staticmethod
    def _guess_title(text: str) -> str:
        first = text.strip().splitlines()[0] if text.strip() else ""
        return first[:140]

    @staticmethod
    def _guess_company(text: str) -> str:
        m = re.match(r"\s*([A-Z][A-Za-z0-9&.\- ]{1,40})\s*[\|\-–—]", text)
        if m:
            return m.group(1).strip()
        return ""

    def fetch(self) -> List[Job]:
        thread_id = self.thread_id or self._latest_thread_id()
        if not thread_id:
            log.warning("could not find a Who is hiring thread")
            return []

        log.info("hn: using thread %s", thread_id)
        thread = self._fetch_item(thread_id)
        if not thread:
            return []
        kids = thread.get("kids") or []
        kids = kids[: self.max_comments]

        jobs: List[Job] = []
        for cid in kids:
            item = self._fetch_item(cid)
            if not item or item.get("deleted") or item.get("dead"):
                continue
            text = self._strip_html(item.get("text", ""))
            if not text:
                continue
            jobs.append(
                Job(
                    source=self.name,
                    external_id=str(cid),
                    title=self._guess_title(text),
                    company=self._guess_company(text),
                    url=HN_WEB.format(id=cid),
                    description=text[:1500],
                    tags=[],
                    posted_at=str(item.get("time", "")),
                )
            )
        log.info("hn: collected %d posts", len(jobs))
        return jobs
