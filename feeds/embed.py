"""GreenPT embeddings — the pipeline's one way to turn text into vectors.

Uses the product's own provider and key (the same GREENPT_API_KEY that powers
cause/classify.py) but the /embeddings endpoint with the `green-embedding`
model (Qwen3-Embedding-4B, 2560-dim multilingual). urllib only, like the rest
of the repo.

    from embed import embed
    vecs = embed(["repair cafe", "community garden"])  # list[list[float]]

The endpoint takes an array in `input` and returns one vector per element, so
`embed` batches (EMBED_BATCH per call) and reassembles in input order.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "cause"))
from classify import api_key  # noqa: E402

EMBED_URL = "https://api.greenpt.ai/v1/embeddings"
EMBED_MODEL = os.environ.get("FEEDS_EMBED_MODEL", "green-embedding")
EMBED_DIM = 2560
EMBED_BATCH = 64
TIMEOUT = 120


class EmbedError(RuntimeError):
    """A failed embedding. The message is safe to print — it never names a key."""


def _call(texts: list[str]) -> list[list[float]]:
    body = json.dumps({"model": EMBED_MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        EMBED_URL, data=body,
        headers={"Authorization": f"Bearer {api_key()}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise EmbedError(
            f"GreenPT embeddings returned HTTP {e.code}: {detail[:300]}") from None
    except OSError as e:
        raise EmbedError(
            f"cannot reach GreenPT embeddings ({e}). Is the network up?") from None
    except json.JSONDecodeError:
        raise EmbedError("GreenPT embeddings returned an unparseable response") from None

    data = payload.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise EmbedError(
            f"GreenPT embeddings returned {len(data) if isinstance(data, list) else 'no'} "
            f"vectors for {len(texts)} inputs")
    if all(isinstance(d.get("index"), int) for d in data):
        data = sorted(data, key=lambda d: d["index"])
    out: list[list[float]] = []
    for d in data:
        vec = d.get("embedding")
        if not isinstance(vec, list) or len(vec) != EMBED_DIM:
            raise EmbedError(
                f"GreenPT embeddings returned a vector of size "
                f"{len(vec) if isinstance(vec, list) else '?'}, expected {EMBED_DIM}")
        out.append([float(x) for x in vec])
    return out


def embed(texts: list[str]) -> list[list[float]]:
    """Embed texts with green-embedding, in input order. Empty input -> []."""
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        out.extend(_call(texts[i:i + EMBED_BATCH]))
    return out