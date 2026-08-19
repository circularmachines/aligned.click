"""The feeds pipeline's LanceDB stores — embedded keywords and posts.

feeds/.lancedb (gitignored; the repo's one non-stdlib dependency, see
requirements.txt) holds the two stores the pipeline grows:

- **keywords** — every term any feed has harvested, with its green-embedding
  vector and lifecycle status: candidate (added, not yet checked), indexed
  (its last-month posts are embedded), disqualified (over the cap — too
  common to be a retrieval signal, e.g. "the");
- **posts** — every post embedded while indexing a keyword, deduped by at://
  URI. `fit`/`why`/`judged` record the last judgment the per-post classifier
  made (the binary membership decision) and `grade` the general quality score
  (0-10); `replyTo` tells the judge whether the post is a root post or a
  reply, and `media`/engagement counts (like/reply/repost) are kept for later
  sizing and filtering. The store is shared across feeds, so a judged post is
  not re-seeded for any of them.

The criteria is embedded and cosine-searched against both: keywords, to show
the harvest call what is already known (harvest.py), and posts, to seed the
per-post judge (top-N by similarity, pipeline.py).
"""

import sys
import time
from pathlib import Path

import lancedb
import pyarrow as pa

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from embed import EMBED_DIM  # noqa: E402

DB_PATH = ROOT / ".lancedb"
_KEYWORDS = "keywords"
_POSTS = "posts"


def _vector():
    return pa.list_(pa.float32(), EMBED_DIM)


_db = None
_tables: dict[str, object] = {}


def _conn():
    global _db
    if _db is None:
        _db = lancedb.connect(str(DB_PATH))
    return _db


def _table(name: str):
    if name not in _tables:
        _tables[name] = _conn().open_table(name)
    return _tables[name]


def _names() -> set[str]:
    """The existing table names. `list_tables()` returns a response object in
    this lancedb version, so reach into `.tables` rather than `in`-checking it."""
    try:
        resp = _conn().list_tables()
        names = resp.tables if hasattr(resp, "tables") else list(resp)
    except Exception:  # noqa: BLE001 — older/newer lancedb shapes
        names = _conn().table_names()
    return set(names)


def ensure() -> None:
    """Create the two tables on first use. Idempotent afterwards."""
    conn = _conn()
    if _KEYWORDS not in _names():
        t = conn.create_table(_KEYWORDS, schema=pa.schema([
            pa.field("keyword", pa.string()),
            pa.field("embedding", _vector()),
            pa.field("status", pa.string()),
            pa.field("post_count", pa.int64()),
            pa.field("last_indexed", pa.string()),
            pa.field("provenance", pa.string()),
            pa.field("created", pa.string()),
        ]))
        _tables[_KEYWORDS] = t
    if _POSTS not in _names():
        t = conn.create_table(_POSTS, schema=pa.schema([
            pa.field("uri", pa.string()),
            pa.field("handle", pa.string()),
            pa.field("did", pa.string()),
            pa.field("displayName", pa.string()),
            pa.field("text", pa.string()),
            pa.field("embedding", _vector()),
            pa.field("keyword", pa.string()),
            pa.field("createdAt", pa.string()),
            pa.field("replyTo", pa.string()),
            pa.field("media", pa.string()),
            pa.field("likeCount", pa.int64()),
            pa.field("replyCount", pa.int64()),
            pa.field("repostCount", pa.int64()),
            pa.field("fit", pa.bool_()),
            pa.field("grade", pa.int8()),
            pa.field("graded", pa.bool_()),
            pa.field("why", pa.string()),
            pa.field("judged", pa.bool_()),
        ]))
        _tables[_POSTS] = t
    _migrate()


def _migrate() -> None:
    """Add columns the running code expects but older stores lack. Existing
    rows get the default, so nothing is re-embedded."""
    expected = {
        "replyTo": pa.string(),
        "grade": pa.int8(),
        "displayName": pa.string(),
        "media": pa.string(),
        "likeCount": pa.int64(),
        "replyCount": pa.int64(),
        "repostCount": pa.int64(),
        "graded": pa.bool_(),
    }
    try:
        existing = {f.name for f in _table(_POSTS).schema}
        missing = [pa.field(name, typ) for name, typ in expected.items()
                   if name not in existing]
        if missing:
            _table(_POSTS).add_columns(missing)
            _tables.pop(_POSTS, None)
    except Exception:  # noqa: BLE001 — a store that cannot migrate still works
        pass


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- keywords -----------------------------------------------------------------


def add_keyword(keyword: str, embedding: list[float], provenance: str,
                status: str = "candidate", post_count: int = 0,
                last_indexed: str = "") -> None:
    """Insert the keyword, or update it in place (one entry per keyword, ever)."""
    ensure()
    _table(_KEYWORDS).merge_insert("keyword") \
        .when_matched_update_all() \
        .when_not_matched_insert_all() \
        .execute([{
            "keyword": keyword, "embedding": embedding, "status": status,
            "post_count": post_count, "last_indexed": last_indexed,
            "provenance": provenance, "created": _now(),
        }])


def update_keyword(keyword: str, status: str | None = None,
                   post_count: int | None = None,
                   last_indexed: str | None = None) -> None:
    """Touch selected fields of one keyword. No-op when it does not exist."""
    ensure()
    rows = _table(_KEYWORDS).search() \
        .where(f"keyword = '{keyword}'").limit(1).to_arrow().to_pylist()
    if not rows:
        return
    row = dict(rows[0])
    if status is not None:
        row["status"] = status
    if post_count is not None:
        row["post_count"] = post_count
    if last_indexed is not None:
        row["last_indexed"] = last_indexed
    _table(_KEYWORDS).merge_insert("keyword").when_matched_update_all().execute([row])


def get_keyword(keyword: str) -> dict | None:
    ensure()
    rows = _table(_KEYWORDS).search() \
        .where(f"keyword = '{keyword}'").limit(1).to_arrow().to_pylist()
    return rows[0] if rows else None


def similar_keywords(vec: list[float], k: int = 10) -> list[dict]:
    """The k nearest harvested keywords to a criteria embedding, with status so
    the harvest call can see what is already known — including what was
    disqualified and why it must not be re-proposed."""
    ensure()
    rows = _table(_KEYWORDS).search(vec).metric("cosine").limit(k) \
        .to_arrow().to_pylist()
    out = []
    for r in rows:
        out.append({
            "keyword": r["keyword"], "status": r["status"],
            "post_count": r["post_count"], "last_indexed": r["last_indexed"],
            "provenance": r["provenance"], "_distance": r.get("_distance"),
        })
    return out


def keyword_counts() -> dict[str, int]:
    ensure()
    counts: dict[str, int] = {}
    for r in _table(_KEYWORDS).to_arrow().to_pylist():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


# --- posts --------------------------------------------------------------------


def add_posts(rows: list[dict]) -> None:
    """Insert or update posts, deduped by at:// URI. `rows` are extract() dicts
    plus `embedding`, `keyword`, `fit`, `why`, `judged`."""
    if not rows:
        return
    ensure()
    _table(_POSTS).merge_insert("uri") \
        .when_matched_update_all() \
        .when_not_matched_insert_all() \
        .execute(rows)


def similar_posts(vec: list[float], k: int = 20,
                  exclude_uris: set[str] | None = None) -> list[dict]:
    """The k nearest embedded posts to a criteria embedding.

    `exclude_uris` is a set of at:// URIs to skip — a feed's own seen set, so
    a post the feed has already judged (fit or not) is not re-seeded for it.
    The grade is a property of the post and stays on every returned row, so
    already-graded posts are reused without another quality call."""
    ensure()
    rows = _table(_POSTS).search(vec).metric("cosine").limit(max(k * 3, 60)) \
        .to_arrow().to_pylist()
    if not exclude_uris:
        return rows[:k]
    fresh = [r for r in rows if r["uri"] not in exclude_uris]
    return fresh[:k]


def mark_graded(grades: list[tuple]) -> None:
    """Store the general-quality grade on posts that were not graded yet.
    `grades` is a list of (uri, grade, why); unknown uris are ignored. This
    is the one reusable pass: once graded, every feed reads the same grade."""
    if not grades:
        return
    ensure()
    table = _table(_POSTS)
    for uri, grade, why in grades:
        rows = table.search().where(f"uri = '{uri}'").limit(1).to_arrow().to_pylist()
        if not rows:
            continue
        row = dict(rows[0])
        try:
            row["grade"] = int(grade)
        except (TypeError, ValueError):
            row["grade"] = 0
        row["graded"] = True
        row["why"] = str(why or "")[:200]
        table.merge_insert("uri").when_matched_update_all().execute([row])


def post_counts() -> dict:
    ensure()
    rows = _table(_POSTS).to_arrow().to_pylist()
    total = len(rows)
    graded = sum(1 for r in rows if r.get("graded"))
    return {"total": total, "graded": graded}