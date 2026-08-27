"""Regression cases for the geo gate in config.yaml.

Run after editing filter.geo lists:  python tests/test_filter.py
"""
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobfeed.filter import FilterConfig, apply_filter  # noqa: E402
from jobfeed.sources.base import Job  # noqa: E402

# (should_be_kept, source, title, location, description)
CASES = [
    # --- blocked: pinned to a country that's out of reach ---
    (False, "hackernews", "Instinct Science | Senior Full-Stack Engineer (Elixir + React) | REMOTE (US)", "", "React, TypeScript, cloud-native EMR."),
    (False, "hackernews", "Detections.ai | Full-Stack Engineer | REMOTE (US & Canada) | Full-time", "", "React, TypeScript, SIEM/EDR."),
    (False, "hackernews", "Apex Dental | Full-Stack Developer | Dallas, TX (Remote US or Hybrid)", "", "React, JavaScript."),
    (False, "hackernews", "Phonely | San Francisco, CA | Onsite (5 days/week) | Senior Full Stack Engineer", "", "TypeScript, Next.js, distributed systems."),
    (False, "hackernews", "Bar Inc | React Engineer | REMOTE - US", "", "TypeScript."),
    (False, "hackernews", "Baz | Frontend Developer | USA", "", "React, remote."),
    (False, "hackernews", "Qux | Senior React Dev | North America", "", "Remote across North America."),
    (False, "hackernews", "Frontend Engineer (Remote, Toronto)", "", "React, TypeScript."),
    (False, "hackernews", "Acme | Senior Frontend Engineer | Berlin, Germany", "", "React, hybrid in our Berlin office."),
    (False, "hackernews", "Frontend Engineer | Sydney, Australia", "", "React, remote within Australia."),
    (False, "hackernews", "Adalat AI | Remote (India) | Go, React, Next.js", "", "React, remote."),
    (False, "remoteok", "Frontend Engineer", "US", "React, remote."),
    (False, "remoteok", "DESARROLLADOR FULL STACK", "", "Consultora especializada en talento tecnologico en LATAM."),
    (False, "arbeitnow", "(Senior) Fullstack Entwickler (m/w/d) Node.js", "Remote", "Softwareloesungen, React, TypeScript."),
    (False, "weworkremotely", "Senior Frontend Engineer", "", "Remote. React. Must be based in the US."),
    # --- kept: remote / Europe-wide / an allowed country ---
    (True, "djinni", "Senior JavaScript Developer", "abroad, remote, ukraine", "Devart. React, TypeScript."),
    (True, "hackernews", "Frontend Engineer (React) | REMOTE (Europe)", "", "TypeScript, React, team across Europe."),
    (True, "hackernews", "React Developer — Remote, Worldwide", "", "Frontend, JavaScript, remote worldwide."),
    (True, "hackernews", "Aqora Quantum | Sr Full-Stack Engineer (Rust + React) | Paris ONSITE or REMOTE (EU)", "", "React, TypeScript."),
    (True, "dou", "Middle Frontend Developer", "Zagreb, Croatia", "React, TypeScript, hybrid office in Zagreb."),
    (True, "justjoinit", "Frontend Developer (React)", "Warsaw, Poland", "JavaScript, TypeScript, B2B contract."),
    (True, "justjoinit", "Senior Frontend Engineer", "Lisbon / remote", "React, TypeScript."),
    (True, "justjoinit", "Frontend Developer", "Vienna, Austria", "React, TypeScript, EU contract."),
    # a remote-only board post that never spells out "remote"
    (True, "weworkremotely", "Senior Fullstack Developer (React.js / Node.js)", "", "Headquarters: Sweden. React.js and Node.js for one of our clients."),
    # always_allow beats a blocked country in the title
    (True, "hackernews", "Widget Co | Frontend Engineer | REMOTE (US)", "", "React. Our team is in Kyiv, Ukraine and we hire Ukrainian contractors."),
    # a worldwide post that merely lists office locations must survive
    (True, "hackernews", "Globex | Senior Frontend Engineer | REMOTE (Worldwide)", "", "React. We have entities in Canada, Germany and Australia but hire contractors anywhere."),
]


def build_config(path="config.yaml"):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = yaml.safe_load(open(os.path.join(root, path)))["filter"]
    geo = cfg.get("geo") or {}
    return FilterConfig(
        title_include_any=cfg.get("title_include_any", []),
        include_any=cfg.get("include_any", []),
        exclude_any=cfg.get("exclude_any", []),
        require_allowed_geo=cfg.get("require_allowed_geo", False),
        geo_always_allow_any=geo.get("always_allow_any", []),
        geo_exclude_any=geo.get("exclude_any", []),
        geo_allow_any=geo.get("allow_any", []),
        geo_remote_sources=geo.get("remote_sources", []),
    )


def main():
    fc = build_config()
    jobs = [
        Job(source=src, external_id=str(i), title=t, company="", url="", description=d, location=loc)
        for i, (_, src, t, loc, d) in enumerate(CASES)
    ]
    kept = {j.external_id for j in apply_filter(jobs, fc)}

    failed = 0
    for i, (expected, src, title, loc, _) in enumerate(CASES):
        got = str(i) in kept
        if got != expected:
            failed += 1
            want = "KEEP" if expected else "DROP"
            print(f"FAIL  expected {want}  [{src}] {title}  |{loc}")

    print(f"{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
