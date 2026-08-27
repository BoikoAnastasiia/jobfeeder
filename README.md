# job-feed-bot

A small Python bot that aggregates job posts from multiple sources, filters
them by your keywords, dedupes, and pushes the results to a Telegram chat.

Built originally for a frontend dev based in the EU. Runs on a cron via
GitHub Actions, so you don't need a server.

## Sources

| Source | How it's pulled |
|---|---|
| Hacker News — "Ask HN: Who is hiring?" | Firebase + Algolia APIs (latest monthly thread auto-detected) |
| RemoteOK | Public JSON API |
| WeWorkRemotely | Public RSS feeds |
| JustJoin.it | Public v2 offers API (EU/PL, frequently hires Ukrainian engineers) |
| DOU.ua | Public RSS feeds — per category, plus per-company feeds |

> **DOU company feeds.** Some companies post roles that never surface in a
> category feed. Follow them directly by adding the company slug (the bit
> after `/companies/` in the URL) to `sources.dou.companies` in
> `config.yaml` — e.g. `https://jobs.dou.ua/companies/techmagic/vacancies/`
> → `techmagic`.

> **LinkedIn?** There's no legal/stable public API for job search. The
> recommended workaround is to subscribe to LinkedIn's email job alerts and
> have them auto-forwarded into the same Telegram chat — or use a paid
> service like `rss.app` to wrap a saved search as RSS, then add it as a new
> source.

Adding more sources is one file under `jobfeed/sources/` plus an entry in
`jobfeed/sources/__init__.py:REGISTRY` and in `config.yaml`.

## Quick start (local)

```bash
git clone <this repo>
cd job-feed-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# Preview what would be sent, without contacting Telegram:
python main.py --dry-run

# Send for real:
python main.py
```

### Getting a Telegram bot

1. Open Telegram, message **@BotFather**, `/newbot`, follow prompts.
2. Save the token it gives you → `TELEGRAM_BOT_TOKEN`.
3. **Message your new bot once** (otherwise it can't DM you).
4. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and find the
   numeric `chat.id` of your own user → `TELEGRAM_CHAT_ID`.

## Configuration

Edit `config.yaml` to change keyword filters, which sources to poll, etc.

- `filter.include_any` — a job must mention at least one of these (case
  insensitive) to pass.
- `filter.exclude_any` — drop jobs that mention any of these (e.g. `senior`,
  `staff`, technologies you don't want, etc.).
- `filter.require_allowed_geo` — turns on the geo gate below.
- `filter.geo` — where you can realistically work, in three steps:
  1. `always_allow_any` — matched against the **whole post**. A hit keeps the
     job no matter what else it says, on the theory that a post asking for
     Ukrainian (or naming Ukraine/Croatia/Slovakia) can hire from there
     wherever the company itself sits.
  2. `exclude_any` — countries that are out of reach. Matched **only against
     the title, location and tags**, i.e. the fields that actually declare
     where a job is tied to. Deliberately not the description, so a post that
     merely lists offices ("we have entities in Canada and Germany") doesn't
     get dropped.
  3. `allow_any` — the post must mention one of these somewhere, or it's
     dropped. `remote` / `europe` / `worldwide` keep the feed full; the named
     countries are the ones where a local or B2B contract is realistic. Leave
     the list empty to accept anything that survived step 2.

  `remote_sources` lists boards that only ever carry remote work (RemoteOK,
  WeWorkRemotely, Remotive); their posts skip step 3, since many never spell
  the word "remote" out in the body. Step 2 still applies to them.

  Entries starting with `re:` are regular expressions — that's how
  `REMOTE (US)` and `REMOTE (US & Canada)` get caught without a bare `us`
  matching the English word. Everything else is a plain phrase: single words
  match on word boundaries, multi-word phrases match as substrings.
After changing the geo lists, run `python tests/test_filter.py` — it checks a
set of real postings still land on the right side of the gate.

- `max_per_run` — caps the number of messages sent per run, so the first
  run doesn't flood the chat with hundreds of historical posts. Sources are
  polled in the order they appear in `config.yaml` and the cap is applied to
  the combined list, so a source near the bottom only gets through once the
  ones above it run dry.

The dedupe state is kept in `seen.json` and committed back to the repo by
the GitHub Actions workflow.

## Running on GitHub Actions

1. Push this repo to GitHub.
2. In **Settings → Secrets and variables → Actions**, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. **Settings → Actions → General → Workflow permissions**: set to
   *"Read and write permissions"* (so the workflow can commit `seen.json`).
4. Open the **Actions** tab → enable workflows → run `job-feed-bot`
   manually once via *Run workflow* to confirm it works.

It will then run every 4 hours on its own (`.github/workflows/run.yml`).

## Project layout

```
job-feed-bot/
├── main.py                       # entry point
├── config.yaml                   # filters + which sources to poll
├── requirements.txt
├── .env.example
├── jobfeed/
│   ├── filter.py                 # keyword/region filtering
│   ├── notifier.py               # Telegram bot output
│   ├── state.py                  # JSON-backed dedupe store
│   └── sources/
│       ├── base.py               # Job + Source classes
│       ├── hackernews.py
│       ├── remoteok.py
│       ├── weworkremotely.py
│       └── justjoinit.py
└── .github/workflows/run.yml     # cron-based runner
```

## Adding a new source

1. Create `jobfeed/sources/yoursite.py`:
   ```python
   from .base import Source, Job

   class YourSite(Source):
       name = "yoursite"

       def fetch(self):
           # return a list of Job(...)
           ...
   ```
2. Register it in `jobfeed/sources/__init__.py:REGISTRY`.
3. Add `- name: yoursite` to `config.yaml` under `sources:`.

## License

MIT.
