"""The general feed builder's state — one file, per-feed records.

The product's front door is a question: "what types of posts do you want to
see?" A feed request is the literal answer — there is no decoding step, no
shared vocabulary, no multibinary. The answer is the feed's criteria, verbatim.

Each feed owns everything it needs in one record:

- **text** — the literal answer, which is also the criteria the quality check
  judges posts against;
- **keywords** — the pool, seeded from the answer and harvested from posts that
  fit, by the feed's own crank (see judge.py);
- **posts** — the posts that matched, ready to be shown.

`feeds.json` is `{id: feed}`. Two unrelated feeds share nothing, which is the
point: a feed is a self-contained answer, cheap to create and to delete.
"""

import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).parent

# --- thresholds, env-tunable like the index's ---------------------------------

PASS_RATE = float(os.environ.get("FEEDS_PASS_RATE", "0.2"))
POSTS_PER_KEYWORD = int(os.environ.get("FEEDS_POSTS", "10"))
WINDOW_DAYS = int(os.environ.get("FEEDS_WINDOW_DAYS", "30"))
MAX_CLASSIFY_RETRIES = int(os.environ.get("FEEDS_MAX_RETRIES", "3"))

# --- files --------------------------------------------------------------------

FEEDS_FILE = ROOT / "feeds.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return fallback


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# --- feeds --------------------------------------------------------------------


def load_feeds() -> dict[str, dict]:
    """{id: feed}. A feed is one literal answer plus its pool and its posts."""
    return _load_json(FEEDS_FILE, {})


def save_feeds(feeds: dict[str, dict]) -> None:
    _write_json(FEEDS_FILE, feeds)


def new_feed(text: str) -> dict:
    return {
        "id": _now(),
        "text": text,
        "createdAt": _now(),
        "keywords": [],
        "posts": {},
    }


# --- the keyword pool (per feed, the existing crank) ---------------------------


def new_keyword(term: str, found_by: str) -> dict:
    return {"keyword": term, "found_by": found_by, "status": "candidate",
            "pass_rate": None, "tested": None, "posts_seen": 0,
            "posts_confirmed": 0}


def _norm(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def new_from(existing: list[dict], terms: list[str], parent: str) -> list[dict]:
    """Terms genuinely new to the pool: not already a keyword, not the parent."""
    known = {_norm(k["keyword"]) for k in existing}
    known.add(_norm(parent))
    fresh = []
    for t in terms:
        if _norm(t) in known:
            continue
        known.add(_norm(t))
        fresh.append(new_keyword(t, parent))
    return fresh