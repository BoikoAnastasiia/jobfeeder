from dataclasses import dataclass, asdict
from typing import List
import hashlib


@dataclass
class Job:
    source: str
    external_id: str
    title: str
    company: str
    url: str
    description: str = ""
    tags: List[str] = None
    location: str = ""
    posted_at: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    @property
    def uid(self) -> str:
        raw = f"{self.source}:{self.external_id}"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def to_dict(self):
        return asdict(self)


class Source:
    name: str = "base"

    def fetch(self) -> List[Job]:
        raise NotImplementedError
