from .base import Job, Source
from .hackernews import HackerNewsWhoIsHiring
from .remoteok import RemoteOK
from .weworkremotely import WeWorkRemotely
from .justjoinit import JustJoinIt
from .arbeitnow import Arbeitnow
from .remotive import Remotive
from .djinni import Djinni
from .dou import Dou
from .profesia import Profesia
from .titans import Titans

REGISTRY = {
    "hackernews": HackerNewsWhoIsHiring,
    "remoteok": RemoteOK,
    "weworkremotely": WeWorkRemotely,
    "justjoinit": JustJoinIt,
    "arbeitnow": Arbeitnow,
    "remotive": Remotive,
    "djinni": Djinni,
    "dou": Dou,
    "profesia": Profesia,
    "titans": Titans,
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
    "Dou",
    "Profesia",
    "Titans",
]
