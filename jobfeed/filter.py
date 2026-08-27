import re
from dataclasses import dataclass
from typing import List

from .sources.base import Job


@dataclass
class FilterConfig:
    include_any: List[str]
    exclude_any: List[str]
    title_include_any: List[str] = None  # if set, title must match at least one
    require_allowed_geo: bool = False
    geo_always_allow_any: List[str] = None
    geo_exclude_any: List[str] = None
    geo_allow_any: List[str] = None
    geo_remote_sources: List[str] = None

    def __post_init__(self):
        if self.title_include_any is None:
            self.title_include_any = []
        if self.geo_always_allow_any is None:
            self.geo_always_allow_any = []
        if self.geo_exclude_any is None:
            self.geo_exclude_any = []
        if self.geo_allow_any is None:
            self.geo_allow_any = []
        if self.geo_remote_sources is None:
            self.geo_remote_sources = []


# --------------------------------------------------------------------------
# Geo rules live in config.yaml under filter.geo. An entry starting with "re:"
# is a regular expression; everything else is a plain phrase (single words match
# on word boundaries, multi-word phrases match as substrings).
#
# Empty lists mean "no opinion": nothing blocked / everything allowed.
# --------------------------------------------------------------------------


def _words(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def _matches_any(haystack: str, needles: List[str]) -> bool:
    if not needles:
        return False
    for n in needles:
        if not n:
            continue
        n = n.lower()
        if n.startswith("re:"):
            if re.search(n[3:], haystack):
                return True
        # word-boundary match for short tokens, substring for multi-word
        elif " " in n:
            if n in haystack:
                return True
        else:
            if re.search(rf"\b{re.escape(n)}\b", haystack):
                return True
    return False


def _passes_geo(
    geo_text: str, full_text: str, cfg: FilterConfig, implicit_remote: bool = False
) -> bool:
    """Three-step geo gate: hard keeps, then blocked countries, then the allow list."""
    if _matches_any(full_text, cfg.geo_always_allow_any):
        return True
    if _matches_any(geo_text, cfg.geo_exclude_any):
        return False
    if not cfg.geo_allow_any:
        return True
    # Boards that only list remote work satisfy the allow step on their own —
    # plenty of their posts never spell the word "remote" out in the body.
    if implicit_remote:
        return True
    return _matches_any(full_text, cfg.geo_allow_any)


def apply_filter(jobs: List[Job], cfg: FilterConfig) -> List[Job]:
    out = []
    for job in jobs:
        title_text = _words(job.title or "")
        # Fields that actually declare where a job is tied to. Pipe-joined so a
        # bare "US" in a location field is still recognisable as a segment.
        geo_text = _words(
            " | ".join([job.title or "", job.location or "", " ".join(job.tags or [])])
        )
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
        implicit_remote = job.source in cfg.geo_remote_sources
        if cfg.require_allowed_geo and not _passes_geo(
            geo_text, full_text, cfg, implicit_remote
        ):
            continue
        out.append(job)
    return out
