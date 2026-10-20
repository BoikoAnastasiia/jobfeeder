import html
import logging
import re
import time
import requests
from typing import List

from .base import Source, Job

log = logging.getLogger(__name__)

# profesia.sk — the biggest Slovak job board. No API or RSS; the search results
# are server-rendered HTML. The results page has no language info, so each
# offer's detail page is fetched to read its "Language skills" section and the
# language the post itself is written in.
BASE_URL = "https://www.profesia.sk"
SEARCH_URL = BASE_URL + "/praca/"

# The detail page's fixed section headings come out in the language the
# employer wrote the post in. A post written in Slovak/Czech effectively
# requires that language, whatever its "Language skills" section says.
_POST_LANGUAGE_BY_HEADING = {
    "Requirements for the employee": "English",
    "Požiadavky na zamestnanca": "Slovak",
    "Požadavky na zaměstnance": "Czech",
    "Anforderungen an den Arbeitnehmer": "German",
    "Követelmények a munkavállalóval szemben": "Hungarian",
}

# "Language skills" entries on Slovak/Czech posts: "Anglický jazyk - Pokročilý (C1)".
_SK_LANGUAGE_NAMES = {
    "anglick": "English",
    "slovensk": "Slovak",
    "česk": "Czech",
    "nemeck": "German",
    "německ": "German",
    "maďarsk": "Hungarian",
    "poľsk": "Polish",
    "polsk": "Polish",
    "ukrajinsk": "Ukrainian",
    "rusk": "Russian",
    "francúzsk": "French",
    "francouzsk": "French",
    "taliansk": "Italian",
    "španielsk": "Spanish",
}

_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en,sk;q=0.8"}


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def _language_name(entry: str) -> str:
    # "English - Upper intermediate (B2)" -> "English"
    name = entry.split(" - ")[0].strip()
    low = name.lower()
    for stem, english in _SK_LANGUAGE_NAMES.items():
        if low.startswith(stem):
            return english
    return name


def _guess_language(text: str) -> str:
    """English, Slovak or Czech, judged by how many letters carry SK/CZ diacritics.

    English posts still contain the odd Slovak street or person name, so a
    small share of accented letters is tolerated.
    """
    letters = [c for c in text.lower() if c.isalpha()]
    if not letters:
        return "English"
    accented = sum(c in "áäčďéíĺľňóôŕšťúýžěřů" for c in letters)
    if accented / len(letters) < 0.02:
        return "English"
    czech_only = sum(c in "ěřů" for c in letters)
    return "Czech" if czech_only > accented * 0.15 else "Slovak"


class Profesia(Source):
    name = "profesia"

    def __init__(
        self,
        keywords: List[str] = None,
        max_pages: int = 2,
        title_keywords: List[str] = None,
        delay: float = 0.5,
    ):
        self.keywords = keywords or ["frontend"]
        self.max_pages = max_pages
        # Only offers whose title matches one of these get their detail page
        # fetched — the search is full-text, so most hits are irrelevant.
        self.title_keywords = title_keywords or []
        self.delay = delay

    def fetch(self) -> List[Job]:
        offers = {}  # offer id -> (path, title, company, location)
        # Employers post one role once per city; keep the first.
        seen_pairs = set()
        for kw in self.keywords:
            for page in range(1, self.max_pages + 1):
                params = {"search_anywhere": kw}
                if page > 1:
                    params["page_num"] = page
                try:
                    r = requests.get(SEARCH_URL, params=params, headers=_HEADERS, timeout=20)
                    r.raise_for_status()
                except Exception as e:
                    log.warning("profesia search %r page %s failed: %s", kw, page, e)
                    break
                rows = r.text.split('class="list-row"')[1:]
                if not rows:
                    break
                for row in rows:
                    m = re.search(r'id="offer(\d+)" href="([^"]+)"', row)
                    if not m or m.group(1) in offers:
                        continue
                    title = re.search(r"<span class='title'>(.*?)</span>", row, re.S)
                    company = re.search(r"<span class='employer'>(.*?)</span>", row, re.S)
                    location = re.search(r"class='job-location'>(.*?)</span>", row, re.S)
                    path = html.unescape(m.group(2)).split("?")[0]
                    title = _text(title.group(1)) if title else ""
                    company = _text(company.group(1)) if company else ""
                    pair = (company.lower(), title.lower())
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    offers[m.group(1)] = (
                        path,
                        title,
                        company,
                        _text(location.group(1)) if location else "",
                    )
                if "page_num=%d" % (page + 1) not in r.text:
                    break

        # Imported here: jobfeed.filter imports this package, so a top-level
        # import would be circular.
        from ..filter import _matches_any, _words

        jobs: List[Job] = []
        for offer_id, (path, title, company, location) in offers.items():
            if self.title_keywords and not _matches_any(_words(title), self.title_keywords):
                continue
            time.sleep(self.delay)
            job = self._fetch_detail(offer_id, path, title, company, location)
            if job:
                jobs.append(job)
        log.info("profesia: %d search hits, collected %d posts", len(offers), len(jobs))
        return jobs

    def _fetch_detail(self, offer_id, path, title, company, location):
        url = BASE_URL + path
        try:
            r = requests.get(url, headers=_HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            log.warning("profesia offer %s failed: %s", offer_id, e)
            return None
        page = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", r.text, flags=re.S)

        # The posting itself: from the job title up to the employer blurb (or
        # the page footer, on employers' custom-branded layouts).
        start = max(page.find("<h1"), 0)
        ends = [
            page.find(marker, start)
            for marker in (
                "<h3>Advertiser</h3>",
                "<h3>Inzerujúca spoločnosť</h3>",
                "<h3>Inzerující společnost</h3>",
                "<footer",
                "ID: " + offer_id,
            )
        ]
        end = min([e for e in ends if e > 0] or [len(page)])
        description = _text(page[start:end])

        languages = []
        headings = [_text(h) for h in re.findall(r"<h3>(.*?)</h3>", page, re.S)]
        post_language = next(
            (_POST_LANGUAGE_BY_HEADING[h] for h in headings if h in _POST_LANGUAGE_BY_HEADING),
            None,
        )
        if post_language is None:
            # Custom-branded layout without the standard headings.
            post_language = _guess_language(description)
        if post_language != "English":
            languages.append(post_language)

        skills = re.search(
            r"<h4>(?:Language skills|Jazykové znalosti)</h4>\s*"
            r"<div class=\"details-desc\">(.*?)</div>",
            page,
            re.S,
        )
        if skills:
            for entry in re.split(r"<br\s*/?>", skills.group(1)):
                entry = _text(entry)
                if entry:
                    languages.append(_language_name(entry))

        posted = re.search(r"(\d{4}-\d{2}-\d{2})", page[page.find("ID: " + offer_id):])

        return Job(
            source=self.name,
            external_id=offer_id,
            title=title[:200],
            company=company,
            url=url,
            description=description[:3000],
            tags=[],
            location=location,
            posted_at=posted.group(1) if posted else "",
            languages=languages,
        )
