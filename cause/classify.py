"""The CAUSE classifier.

Takes the candidates a keyword search retrieved and decides which are worth a
member's time, applying only the cause's *prompt notes* (the judgment) — not
the keywords. Keywords are recall; notes are precision. This script is the
precision half.

The model is GreenPT v4 flash (deepseek-v4-flash-0731), the same model the
rest of the product runs, called over its OpenAI-compatible endpoint with
stdlib alone — the repo's Python has no HTTP client installed.

    python3 classify.py posts.json --notes "repair, not replace" \
        --keywords "repair cafe, fixit"
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

GREENPT_URL = "https://api.greenpt.ai/v1/chat/completions"
GREENPT_MODEL = os.environ.get("GREENPT_MODEL", "deepseek-v4-flash-0731")
TIMEOUT = 120

ENV_FILE = Path(__file__).parent.parent / ".env"


def api_key() -> str:
    """The provider key, from the environment or .env. Never printed."""
    key = os.environ.get("GREENPT_API_KEY", "").strip()
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("GREENPT_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not key:
        raise ClassifyError(
            "GREENPT_API_KEY is not set. Put `GREENPT_API_KEY=sk-…` in .env "
            "or export it before running."
        )
    return key


class ClassifyError(RuntimeError):
    """A failed classification. The message is safe to print — it never names
    a key or a raw model dump, only the reason a decision could not be made."""


def _format_post(index: int, p: dict) -> str:
    """One candidate as the model reads it. `p` is a post_index.extract() dict."""
    date = (p.get("createdAt") or "").replace("T", " ")[:16] or "?"
    counts = (f" {p['likeCount']}L" if p.get("likeCount") else
              "") + (f" {p['repostCount']}R" if p.get("repostCount") else "")
    text = " ".join((p.get("text") or "").split())[:320]
    return f"[{index}] @{p.get('handle')}  {date}{counts} — {text}"


def _system(notes: str, keywords: list[str]) -> str:
    """The classifier's instruction. The notes are the entire source of
    judgment; the keywords are named only so the model can tell them apart from
    the notes and apply just one."""
    return (
        "You are the classifier for one Bluesky cause. A cause has two parts: "
        "keywords (broad terms used to retrieve candidate posts) and prompt "
        "notes (the cause's judgment on what is worth a member's time).\n"
        "Candidates were retrieved WITH the keywords. Your only job is to apply "
        "the prompt notes and decide which candidates are worth surfacing to "
        "the cause's members.\n"
        "A post is surfaced if the prompt notes say it is worth a member's "
        "time; surfacing something that merely matches a keyword but the notes "
        "do not care about is a miss.\n"
        f"Keywords: {', '.join(keywords) if keywords else '(none)'}\n"
        f"<prompt notes>\n{notes}\n</prompt notes>"
    )


def _user(posts: list[dict]) -> str:
    if not posts:
        return "There are no candidates."
    lines = [_format_post(i, p) for i, p in enumerate(posts)]
    return (
        "The candidate posts to judge:\n"
        + "\n".join(lines)
        + "\n\nReturn ONLY a JSON array of decisions, one object per post you "
        "surface. Each object: {\"i\": <post index>, \"surface\": true, "
        "\"reason\": \"<why, citing which part of the prompt notes it matches>\"}. "
        "A surfaced post's reason must be one short sentence and must quote or "
        "paraphrase the note that matched. If none qualify, return []. No prose "
        "around the JSON."
    )


def _completion(messages: list[dict]) -> str:
    body = json.dumps({
        "model": GREENPT_MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 8000,
    }).encode()
    req = urllib.request.Request(
        GREENPT_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise ClassifyError(f"GreenPT returned HTTP {e.code}: {detail[:300]}") from None
    except OSError as e:
        raise ClassifyError(f"cannot reach GreenPT ({e}). Is the network up?") from None
    except json.JSONDecodeError:
        raise ClassifyError("GreenPT returned an unparseable response") from None

    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise ClassifyError(
            f"GreenPT response had no choices — model {GREENPT_MODEL!r} "
            "possibly unusable right now"
        ) from None


def _find_json_array(text: str) -> str:
    """The model may wrap the array in a code fence or add a stray line; the
    array itself is the only part that matters."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text, flags=re.S)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end < start:
        raise ClassifyError(
            "the classifier did not return a JSON array. Try again."
        )
    return text[start:end + 1]


def classify(posts: list[dict], notes: str, keywords: list[str]) -> list[dict]:
    """Decide, from the notes, which candidate posts are worth surfacing.

    Returns a list of the surfaced posts (each with the original fields plus
    `reason` and `index`), in the order the model surfaced them.
    """
    if not posts:
        return []
    content = _completion([
        {"role": "system", "content": _system(notes, keywords)},
        {"role": "user", "content": _user(posts)},
    ])
    try:
        decisions = json.loads(_find_json_array(content))
    except json.JSONDecodeError as e:
        raise ClassifyError(
            f"the classifier's JSON did not parse ({e}). The run left no "
            "decision; retry."
        ) from None

    if not isinstance(decisions, list):
        raise ClassifyError("the classifier returned a JSON object, not an array")

    shown: set[int] = set()
    surfaced: list[dict] = []
    for d in decisions:
        if not isinstance(d, dict):
            continue
        try:
            idx = int(d.get("i"))
            surface = bool(d.get("surface"))
        except (TypeError, ValueError):
            continue
        if surface and idx not in shown and 0 <= idx < len(posts):
            shown.add(idx)
            item = dict(posts[idx])
            item["index"] = idx
            item["reason"] = str(d.get("reason", ""))[:220]
            surfaced.append(item)
    return surfaced


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("posts", help="JSON file: a list of post_index.extract() dicts")
    parser.add_argument("--notes", required=True, help="the prompt notes to apply")
    parser.add_argument("--keywords", default="",
                        help="comma-separated keywords (named for context only)")
    args = parser.parse_args()

    try:
        posts = json.loads(Path(args.posts).read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read {args.posts}: {e}", file=sys.stderr)
        sys.exit(1)

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    try:
        result = classify(posts, args.notes, keywords)
    except ClassifyError as e:
        print(f"classification failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()