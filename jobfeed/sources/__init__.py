from .base import Job, Source
from .hackernews import HackerNewsWhoIsHiring
from .remoteok import RemoteOK
from .weworkremotely import WeWorkRemotely
from .justjoinit import JustJoinIt
from .arbeitnow import Arbeitnow
from .remotive import Remotive
from .djinni import Djinni

REGISTRY = {
    "hackernews": HackerNewsWhoIsHiring,
    "remoteok": RemoteOK,
    "weworkremotely": WeWorkRemotely,
    "justjoinit": JustJoinIt,
    "arbeitnow": Arbeitnow,
    "remotive": Remotive,
    "djinni": Djinni,
}

__all__ = [
    "Job",
    "Source",
    "REGISTRY",
    "HackerNewsWhoIsHiring",
    "RemoteOK",
    "WeWorkRemotely",
    "JustJoinIt",
    "Arbeitnow",
    "Remotive",
    "Djinni",
]
