"""
The taxonomy store is the shared schema all three pillars (Identify,
Generate, Defend) key off of via `attack_id`. This is what makes the
closed loop mechanically real: when the feedback loop promotes a stub to
"active", it writes here, and the router/specialist registry both read
from here on their next request -- no restart needed.
"""
import json
import threading
from pathlib import Path
from datetime import datetime, timezone

from app.config import settings

_SEED_PATH = Path(settings.data_dir) / "seed_taxonomy.json"
_LIVE_PATH = Path(settings.data_dir) / "live_taxonomy.json"


class TaxonomyStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self):
        with self._lock:
            source = _LIVE_PATH if _LIVE_PATH.exists() else _SEED_PATH
            with open(source) as f:
                entries = json.load(f)

            # Self-heal from a stale cache: if live_taxonomy.json was
            # written by an older version of this app (e.g. before the
            # specialist_status -> specialist_tier migration), its entries
            # won't have the fields the current code expects. Rather than
            # crash on every request that reads a missing field, detect
            # the mismatch here, discard the stale cache, and reload from
            # the bundled seed -- which always matches the current code.
            if source == _LIVE_PATH and not self._matches_current_schema(entries):
                _LIVE_PATH.unlink(missing_ok=True)
                with open(_SEED_PATH) as f:
                    entries = json.load(f)

            self._entries = {e["attack_id"]: e for e in entries}

    @staticmethod
    def _matches_current_schema(entries: list[dict]) -> bool:
        return all(
            "specialist_tier" in e and "specialist_module" in e and "lifecycle_stage" in e
            for e in entries
        )

    def _persist(self):
        _LIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_LIVE_PATH, "w") as f:
            json.dump(list(self._entries.values()), f, indent=2)

    def all(self) -> list[dict]:
        with self._lock:
            return list(self._entries.values())

    def get(self, attack_id: str) -> dict | None:
        with self._lock:
            return self._entries.get(attack_id)

    def active_specialists(self) -> list[dict]:
        """All entries have a working detector now (deep or auto tier) --
        kept as 'active' terminology for backward compat with anything
        reading this list, but functionally this is just `all()`."""
        with self._lock:
            return list(self._entries.values())

    def by_tier(self, tier: str) -> list[dict]:
        with self._lock:
            return [e for e in self._entries.values() if e.get("specialist_tier") == tier]

    def add_entry(self, entry: dict):
        entry.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        with self._lock:
            self._entries[entry["attack_id"]] = entry
            self._persist()

    def reset(self):
        """Reset live taxonomy back to the seed set (used by the demo reset button)."""
        with self._lock:
            if _LIVE_PATH.exists():
                _LIVE_PATH.unlink()
        self._load()


taxonomy_store = TaxonomyStore()
