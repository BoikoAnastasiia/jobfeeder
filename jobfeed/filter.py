import re
from dataclasses import dataclass
from typing import List

from .sources.base import Job


@dataclass
class FilterConfig:
    include_any: List[str]
    exclude_any: List[str]
    title_include_any: List[str] = None  # if set, title must match at least one
    require_remote_or_eu: bool = False

    def __post_init__(self):
        if self.title_include_any is None:
            self.title_include_any = []


EU_HINTS = [
    "remote",
    "europe",
    "eu",
    "emea",
    "worldwide",
    "anywhere",
    "ukraine",
    "kyiv",
    "lviv",
    "kharkiv",
    "odesa",
    "slovakia",
    "bratislava",
    "poland",
    "warsaw",
    "krakow",
    "czech",
    "prague",
    "germany",
    "berlin",
    "munich",
    "hamburg",
    "frankfurt",
    "cologne",
    "dusseldorf",
    "nuremberg",
    "spain",
    "madrid",
    "barcelona",
    "portugal",
    "lisbon",
    "netherlands",
    "amsterdam",
    "uk",
    "london",
    "ireland",
    "dublin",
    "estonia",
    "tallinn",
    "latvia",
    "riga",
    "lithuania",
    "vilnius",
    "croatia",
    "zagreb",
    "romania",
    "bucharest",
    "hungary",
    "budapest",
    "bulgaria",
    "sofia",
    "italy",
    "milan",
    "rome",
    "france",
    "paris",
    "sweden",
    "stockholm",
    "finland",
    "helsinki",
    "denmark",
    "copenhagen",
    "norway",
    "oslo",
    "austria",
    "vienna",
    "switzerland",
    "zurich",
    "geneva",
    "belgium",
    "brussels",
    "greece",
    "athens",
]


def _words(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def _matches_any(haystack: str, needles: List[str]) -> bool:
    if not needles:
        return False
    for n in needles:
        if not n:
            continue
        # word-boundary match for short tokens, substring for multi-word
        if " " in n:
            if n.lower() in haystack:
                return True
        else:
            if re.search(rf"\b{re.escape(n.lower())}\b", haystack):
                return True
    return False


def apply_filter(jobs: List[Job], cfg: FilterConfig) -> List[Job]:
    out = []
    for job in jobs:
        title_text = _words(job.title or "")
        full_text = _words(
            " ".join(
                [
                    job.title or "",
                    job.company or "",
                    job.description or "",
                    " ".join(job.tags or []),
                    job.location or "",
                ]
            )
        )

        # Title-level gate: if configured, the job title must match.
        # This prevents jobs where a keyword only appears deep in the description
        # (e.g. a robotics company that mentions "react" once in their stack list).
        if cfg.title_include_any and not _matches_any(title_text, cfg.title_include_any):
            continue
        if cfg.include_any and not _matches_any(full_text, cfg.include_any):
            continue
        if cfg.exclude_any and _matches_any(full_text, cfg.exclude_any):
            continue
        if cfg.require_remote_or_eu and not _matches_any(full_text, EU_HINTS):
            continue
        out.append(job)
    return out
