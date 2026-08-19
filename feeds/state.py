"""The general feed builder's state — one file, per-feed records.

The product's front door is a question: "what types of posts do you want to
see?" A feed request is the literal answer — there is no decoding step, no
shared vocabulary, no multibinary. The answer is the feed's criteria, verbatim.

Each feed owns everything it needs in one record:

- **text** — the literal answer, which is also the criteria the selector
  judges posts against;
- **keywords** — the seeder pool, planted once from the answer (harvest.py);
   each round the selector may propose fresh terms for the next search;
- **criteria** — the per-post classifier's prompt, refined by each round from
   the reader's literal words (batch.one_shot);
- **posts** — the continuously generated feed: fitting posts per-post judges
   find under the seed pool using the refined criteria (batch.populate);
- **seen** — uris already suggested, so nothing is offered twice;
- **included** / **discarded** — the reader's curation of the suggested batch,
  kept as the feed itself and as negative examples;
- **suggested** — the current batch of picks, waiting for the reader.

Assembly is round-based, not a crawl: one round searches the keyword pool,
loads everything found into one model context, and returns a small diverse set
(batch.one_shot). The reader includes or discards each; a later round carries
that history forward. `feeds.json` is `{id: feed}`. Two unrelated feeds share
nothing, which is the point: a feed is a self-contained answer, cheap to
create and to delete.
"""

import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).parent

# --- thresholds, env-tunable like the index's ---------------------------------

# The seeder pool a new feed starts with, and the cap on a feed's keyword list.
KEYWORDS_PER_FEED = int(os.environ.get("FEEDS_KEYWORDS", "10"))

# Each keyword search takes at most this many fresh posts into the batch.
POSTS_PER_KEYWORD = int(os.environ.get("FEEDS_POSTS", "10"))

# The size of one suggested batch — the selector picks this many diverse posts.
SUGGEST_COUNT = int(os.environ.get("FEEDS_SUGGEST", "8"))

# Hard cap on posts collected into one round's context, whatever the pool size.
MAX_BATCH = int(os.environ.get("FEEDS_BATCH", "100"))

# Search results older than this are filtered out (the post's own createdAt).
WINDOW_DAYS = int(os.environ.get("FEEDS_WINDOW_DAYS", "30"))

# --- the embedding pipeline (pipeline.py) -------------------------------------

# A keyword is indexed by embedding all of its posts from the last
# WINDOW_DAYS. If the supply exceeds this cap the keyword is disqualified —
# it is too common to be a useful retrieval signal ("the" can never be
# indexed). Kept small on purpose; raise it to grow the corpus.
KEYWORD_POST_CAP = int(os.environ.get("FEEDS_KEYWORD_CAP", "1000"))

# How many unjudged posts the judge is seeded with: the top-N by cosine
# similarity between the criteria embedding and the embedded post corpus.
SEED_TOP_N = int(os.environ.get("FEEDS_SEED_N", "20"))

# How many nearest already-indexed keywords the harvest call sees, so it
# builds on what is known instead of re-proposing it.
SIMILAR_KEYWORDS = int(os.environ.get("FEEDS_SIMILAR_KEYWORDS", "10"))

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
        "criteria": None,
        "posts": {},
        "seen": [],
        "included": {},
        "discarded": {},
        "suggested": [],
        "rounds": 0,
        "note": None,
    }


# --- the keyword pool ---------------------------------------------------------


def _norm(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def pool(existing: list[str], new_terms: list[str],
         limit: int = KEYWORDS_PER_FEED) -> list[str]:
    """The next seeder pool: existing terms kept, fresh terms added, deduped
    case-insensitively and capped at `limit`. Order preserves the old pool."""
    known: set[str] = set()
    out: list[str] = []
    for t in list(existing) + list(new_terms):
        n = _norm(t)
        if not n or n in known:
            continue
        known.add(n)
        out.append(t.strip())
        if len(out) >= limit:
            break
    return out