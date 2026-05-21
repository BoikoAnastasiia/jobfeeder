from .base import Job, Source
from .hackernews import HackerNewsWhoIsHiring
from .remoteok import RemoteOK
from .weworkremotely import WeWorkRemotely
from .justjoinit import JustJoinIt

REGISTRY = {
    "hackernews": HackerNewsWhoIsHiring,
    "remoteok": RemoteOK,
    "weworkremotely": WeWorkRemotely,
    "justjoinit": JustJoinIt,
}

__all__ = [
    "Job",
    "Source",
    "REGISTRY",
    "HackerNewsWhoIsHiring",
    "RemoteOK",
    "WeWorkRemotely",
    "JustJoinIt",
]
