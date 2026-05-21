import logging
import time
import requests
from typing import List

from .sources.base import Job

log = logging.getLogger(__name__)

TG_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LEN = 4000  # Telegram limit is 4096; leave headroom


def _escape_html(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_job(job: Job) -> str:
    title = _escape_html(job.title or "(no title)")
    url = _escape_html(job.url or "")
    company = _escape_html(job.company or "")
    location = _escape_html(job.location or "")
    tags = ", ".join(_escape_html(t) for t in (job.tags or [])[:8])
    source_label = {
        "hackernews": "HN Who is hiring",
        "remoteok": "RemoteOK",
        "weworkremotely": "WeWorkRemotely",
        "justjoinit": "JustJoin.it",
    }.get(job.source, job.source)

    lines = [f"<b>{title}</b>"]
    meta = []
    if company:
        meta.append(company)
    if location:
        meta.append(location)
    if meta:
        lines.append(" · ".join(meta))
    if tags:
        lines.append(f"<i>{tags}</i>")
    if url:
        lines.append(f'<a href="{url}">Open</a>  ·  <i>{source_label}</i>')
    else:
        lines.append(f"<i>{source_label}</i>")

    # Optionally include a short snippet from description
    desc = (job.description or "").strip()
    if desc:
        snippet = desc[:400].replace("\n", " ")
        if len(desc) > 400:
            snippet += "…"
        lines.append("")
        lines.append(_escape_html(snippet))

    msg = "\n".join(lines)
    return msg[:MAX_LEN]


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, throttle_sec: float = 1.1):
        self.token = token
        self.chat_id = chat_id
        self.throttle_sec = throttle_sec

    def send(self, text: str) -> bool:
        url = TG_API.format(token=self.token)
        try:
            r = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            if r.status_code == 429:
                retry = int(r.json().get("parameters", {}).get("retry_after", 5))
                log.warning("telegram 429, sleeping %ss", retry)
                time.sleep(retry)
                return self.send(text)
            r.raise_for_status()
            return True
        except Exception as e:
            log.error("telegram send failed: %s", e)
            return False

    def send_jobs(self, jobs: List[Job]) -> int:
        sent = 0
        for job in jobs:
            ok = self.send(format_job(job))
            if ok:
                sent += 1
                time.sleep(self.throttle_sec)
        return sent
