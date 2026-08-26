"""
Where the reply rules and the activity log live.

Two backends:

  "file"       rules.json on disk. Perfect locally. Does NOT persist on
               Cloud Run — a container's filesystem is wiped on every
               restart and redeploy, so edits made in the admin UI would
               silently disappear.

  "firestore"  Google Cloud Firestore. Free tier covers this easily
               (1 GiB stored, 50k reads/day, 20k writes/day) and it lives
               in the same GCP project as your Cloud Run service.

Pick with the RULES_BACKEND env var. Default is "file".
"""
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).parent / "rules.json"
MAX_EVENTS = 200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class FileStore:
    """Reads and writes rules.json. Used for local development."""

    def __init__(self, path: Path = RULES_PATH):
        self.path = path
        self._lock = threading.Lock()
        self._events = []

    def load_rules(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_rules(self, rules: dict) -> None:
        with self._lock:
            # Write to a temp file then move, so a crash mid-write can't
            # leave you with a truncated rules.json and a dead bot.
            tmp = self.path.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2, ensure_ascii=False)
            tmp.replace(self.path)

    def log_event(self, event: dict) -> None:
        event["at"] = _now()
        with self._lock:
            self._events.insert(0, event)
            del self._events[MAX_EVENTS:]

    def recent_events(self, limit: int = 50) -> list:
        return self._events[:limit]


class FirestoreStore:
    """Keeps rules and the activity log in Firestore, so they survive
    container restarts and redeploys on Cloud Run."""

    def __init__(self, collection: str = "igbot"):
        from google.cloud import firestore  # imported lazily

        self._db = firestore.Client()
        self._rules_doc = self._db.collection(collection).document("rules")
        self._events_doc = self._db.collection(collection).document("events")
        self._lock = threading.Lock()

    def load_rules(self) -> dict:
        snap = self._rules_doc.get()
        if snap.exists:
            return snap.to_dict().get("data", {})
        # First run: seed Firestore from the bundled rules.json.
        seed = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        self.save_rules(seed)
        logger.info("Seeded Firestore rules from rules.json")
        return seed

    def save_rules(self, rules: dict) -> None:
        self._rules_doc.set({"data": rules, "updated_at": _now()})

    def log_event(self, event: dict) -> None:
        event["at"] = _now()
        with self._lock:
            snap = self._events_doc.get()
            events = snap.to_dict().get("items", []) if snap.exists else []
            events.insert(0, event)
            del events[MAX_EVENTS:]
            self._events_doc.set({"items": events})

    def recent_events(self, limit: int = 50) -> list:
        snap = self._events_doc.get()
        if not snap.exists:
            return []
        return snap.to_dict().get("items", [])[:limit]


def get_store(backend: str = "file", collection: str = "igbot"):
    backend = (backend or "file").lower()
    if backend == "firestore":
        logger.info("Using Firestore rules backend (collection=%s)", collection)
        return FirestoreStore(collection)
    logger.info("Using file rules backend (%s)", RULES_PATH.name)
    return FileStore()
