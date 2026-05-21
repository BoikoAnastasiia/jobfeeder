import re
from dataclasses import dataclass
from typing import List

from .sources.base import Job


@dataclass
class FilterConfig:
    include_any: List[str]
    exclude_any: List[str]
    require_remote_or_eu: bool = False


EU_HINTS = [
    "remote",
    "europe",
    "eu",
    "emea",
    "worldwide",
    "anywhere",
    "ukraine",
    "slovakia",
    "poland",
    "czech",
    "germany",
    "spain",
    "portugal",
    "netherlands",
    "uk",
    "ireland",
    "estonia",
    "latvia",
    "lithuania",
    "croatia",
    "romania",
    "hungary",
    "bulgaria",
    "italy",
    "france",
    "sweden",
    "finland",
    "denmark",
    "norway",
    "austria",
    "switzerland",
    "belgium",
    "greece",
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
        text = _words(
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

        if cfg.include_any and not _matches_any(text, cfg.include_any):
            continue
        if cfg.exclude_any and _matches_any(text, cfg.exclude_any):
            continue
        if cfg.require_remote_or_eu and not _matches_any(text, EU_HINTS):
            continue
        out.append(job)
    return out
