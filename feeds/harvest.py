"""Keyword harvesting — the one-time process of finding search terms.

This module owns a single job: turning the reader's literal answer into the
search terms a new feed will crawl with. It runs exactly once, when the feed
is created — request.py calls seed_keywords and plants the result as the
feed's starting pool. The continuous crawl never calls it: post judgement
(judge.py) runs on a loop and works the pool it was given, only ever deciding
which posts fit and which existing candidate to judge next. Harvesting and
judging are deliberately different processes with different cadences.

The call talks to GreenPT v4 flash through cause/classify's _completion, the
same transport the product uses everywhere.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "cause"))
from classify import ClassifyError, _completion, _find_json_array  # noqa: E402


def seed_keywords(text: str) -> list[str]:
    """The first search terms for a brand-new feed, from its literal answer.

    The index experiment started from a hand-written seeds.txt; a general feed
    builder cannot — the answer is the seed.
    """
    content = _completion([
        {"role": "system", "content":
            "You give a brand-new Bluesky feed its first search terms. Given "
            "what the reader asked to see, name 1-3 word search terms "
            "(lowercase, no quotes) that would retrieve that kind of post.\n"
            "How a term is matched, exactly: a single word is searched as that "
            "word; a multi-word term is searched as the exact phrase in that "
            "order — it does NOT match posts that only contain some of those "
            "words. There is no OR-ing and no word-by-word matching. So a "
            "term like \"repair cafe\" retrieves posts containing the phrase "
            "\"repair cafe\", and a term like \"mending\" retrieves posts "
            "containing that word. Name phrases that genuinely occur together "
            "in that order; when in doubt, prefer a good single word. "
            "Skip brand names and specific places."},
        {"role": "user", "content":
            f"The request: {text}\n\nReturn ONLY a JSON array of search "
            "terms, 4 to 8 of them. No prose around the JSON."},
    ])
    return _parse_terms(content)


def _parse_terms(content: str) -> list[str]:
    try:
        terms = json.loads(_find_json_array(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(f"terms JSON did not parse ({e})") from None
    if not isinstance(terms, list):
        raise ClassifyError("terms call returned an object, not an array")
    cleaned: list[str] = []
    for t in terms:
        if not isinstance(t, str):
            continue
        t = t.strip().strip('"').lower()
        if 1 < len(t) <= 40 and t not in cleaned:
            cleaned.append(t)
    return cleaned