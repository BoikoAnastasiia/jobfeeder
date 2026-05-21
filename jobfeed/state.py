import json
import os
from pathlib import Path
from typing import Set


class SeenStore:
    """
    Tracks which job UIDs have already been delivered to Telegram.
    Backed by a JSON file so it can be committed back to the repo from
    GitHub Actions (or kept locally during dev).
    """

    def __init__(self, path: str = "seen.json", max_entries: int = 10000):
        self.path = Path(path)
        self.max_entries = max_entries
        self._seen: list[str] = []
        self._index: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            seen = data.get("seen") if isinstance(data, dict) else data
            if isinstance(seen, list):
                self._seen = [str(x) for x in seen]
                self._index = set(self._seen)
        except Exception:
            # Corrupt state file — start fresh, don't crash the run.
            self._seen = []
            self._index = set()

    def has(self, uid: str) -> bool:
        return uid in self._index

    def add(self, uid: str) -> None:
        if uid in self._index:
            return
        self._seen.append(uid)
        self._index.add(uid)

    def save(self) -> None:
        # Trim oldest entries to keep the file bounded.
        if len(self._seen) > self.max_entries:
            drop = len(self._seen) - self.max_entries
            self._seen = self._seen[drop:]
            self._index = set(self._seen)
        os.makedirs(self.path.parent or ".", exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps({"seen": self._seen}, indent=0))
        tmp.replace(self.path)
