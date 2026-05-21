import argparse
import logging
import os
import sys
from typing import List

import yaml
from dotenv import load_dotenv

from jobfeed.filter import FilterConfig, apply_filter
from jobfeed.notifier import TelegramNotifier, format_job
from jobfeed.sources import REGISTRY, Job
from jobfeed.state import SeenStore

log = logging.getLogger("jobfeed")


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_sources(cfg: dict):
    sources = []
    for entry in cfg.get("sources", []):
        name = entry.get("name")
        klass = REGISTRY.get(name)
        if not klass:
            log.warning("unknown source: %s", name)
            continue
        kwargs = {k: v for k, v in entry.items() if k != "name" and v is not None}
        try:
            sources.append(klass(**kwargs))
        except TypeError:
            sources.append(klass())
    return sources


def collect_jobs(sources) -> List[Job]:
    all_jobs: List[Job] = []
    for src in sources:
        try:
            all_jobs.extend(src.fetch())
        except Exception as e:
            log.exception("source %s crashed: %s", src.name, e)
    return all_jobs


def main():
    parser = argparse.ArgumentParser(description="Aggregate job posts to Telegram")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Don't send to Telegram")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    load_dotenv()
    cfg = load_config(args.config)

    fcfg = FilterConfig(
        title_include_any=cfg["filter"].get("title_include_any", []),
        include_any=cfg["filter"].get("include_any", []),
        exclude_any=cfg["filter"].get("exclude_any", []),
        require_remote_or_eu=cfg["filter"].get("require_remote_or_eu", False),
    )

    state_path = cfg.get("state_path", "seen.json")
    store = SeenStore(state_path)

    sources = build_sources(cfg)
    log.info("polling %d sources", len(sources))

    raw = collect_jobs(sources)
    log.info("fetched %d total jobs", len(raw))

    filtered = apply_filter(raw, fcfg)
    log.info("after filter: %d jobs", len(filtered))

    fresh = [j for j in filtered if not store.has(j.uid)]
    log.info("new (not yet sent): %d jobs", len(fresh))

    cap = int(cfg.get("max_per_run", 30))
    to_send = fresh[:cap]
    if len(fresh) > cap:
        log.info("capping send batch at %d (dropping %d)", cap, len(fresh) - cap)

    if args.dry_run:
        for j in to_send:
            print("---")
            print(format_job(j))
        # Don't update state in dry-run mode so a real run still sees them.
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.error("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID env vars missing")
        return 2

    notifier = TelegramNotifier(token=token, chat_id=chat_id)
    sent = notifier.send_jobs(to_send)
    log.info("sent %d/%d jobs to telegram", sent, len(to_send))

    # Mark every job we tried to send (including failures) as seen, so a
    # transient Telegram error doesn't flood the channel on the next run.
    # If you'd rather retry failed sends, change this to only mark successes.
    for j in to_send:
        store.add(j.uid)
    # Also mark all filtered (but skipped due to cap) as seen on a first run?
    # No — keep them queued so they trickle out across runs.
    store.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
