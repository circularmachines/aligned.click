"""The CAUSE classifier.

Takes the candidates a keyword search already retrieved and decides which are
worth a member's time, applying **only** the cause's prompt notes. Keywords did
their job at that point — they set the ceiling on what the classifier can ever
see — and play no part here.

The cause's notes are discrete items: each is its own statement, and one day its
own atproto record with its own author. So the classifier cites *which notes*
made it surface a post, by number — that pointer is how a surfaced post's label
attributes the decision, which is the whole transparency story.

The model is GreenPT v4 flash (deepseek-v4-flash-0731), the same model the
rest of the product runs, called over its OpenAI-compatible endpoint with
stdlib alone — the repo's Python has no HTTP client installed.

    python3 classify.py posts.json --notes-file notes.txt
    python3 classify.py posts.json --notes "repair, not replace"  # one note per line
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


def _system() -> str:
    """The classifier's instruction. Keywords never reach it — they were spent
    at retrieval; a wrong call must always land on the prompt notes."""
    return (
        "You are the classifier for one Bluesky cause. The candidate posts you "
        "are given were already retrieved by the cause's keywords — the "
        "keywords did their job at that point and play no part now. Your only "
        "job is to apply the cause's prompt notes: the discrete statements of "
        "what is worth a member's time.\n"
        "A post is surfaced if the prompt notes say it is worth a member's "
        "time; a post that sits in the retrieval set but matches no note is a "
        "miss.\n"
        "The notes are numbered. When a decision rests on a note, name it by "
        "its number — that pointer is how the cause attributes the decision."
    )


def _user(posts: list[dict], notes: list[str]) -> str:
    if not posts:
        return "There are no candidates."
    note_lines = "\n".join(f"{i}. {n}" for i, n in enumerate(notes, 1))
    lines = "\n".join(_format_post(i, p) for i, p in enumerate(posts))
    return (
        "<prompt notes>\n" + note_lines + "\n</prompt notes>\n"
        "The candidate posts to judge:\n" + lines + "\n\n"
        "Return ONLY a JSON array of decision objects, one per post you "
        "surface. Each object: {\"i\": <post index>, \"surface\": true, "
        "\"reason\": \"<why, one short sentence quoting or paraphrasing the "
        "note that matched>\", \"notes\": [<the note numbers that made this a "
        "surface>]}. If none qualify, return []. No prose around the JSON."
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


def _note_numbers(value, n_notes: int) -> list[int]:
    """The `notes` field of a decision, coerced to 1-based note numbers that
    exist. Bad values are dropped rather than failing the whole run."""
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for v in value:
        try:
            num = int(v)
        except (TypeError, ValueError):
            continue
        if 1 <= num <= n_notes and num not in result:
            result.append(num)
    return result


def classify(posts: list[dict], notes: list[str]) -> list[dict]:
    """Decide, from the notes, which candidate posts are worth surfacing.

    `notes` is a list of discrete note statements (one per item). A surfaced
    post returns with the original fields plus `reason` and `note_inds` (the
    matched note numbers, 1-based) so the caller can attribute the decision to
    the items it came from.
    """
    notes = [n.strip() for n in notes if n.strip()]
    if not posts:
        return []
    content = _completion([
        {"role": "system", "content": _system()},
        {"role": "user", "content": _user(posts, notes)},
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
            item["note_inds"] = _note_numbers(d.get("notes"), len(notes))
            surfaced.append(item)
    return surfaced


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("posts", help="JSON file: a list of post_index.extract() dicts")
    notes = parser.add_mutually_exclusive_group(required=True)
    notes.add_argument("--notes", help="the prompt notes, one note per line")
    notes.add_argument("--notes-file", help="a file of prompt notes, one per line")
    args = parser.parse_args()

    try:
        posts = json.loads(Path(args.posts).read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read {args.posts}: {e}", file=sys.stderr)
        sys.exit(1)

    if args.notes_file:
        note_text = Path(args.notes_file).read_text()
    else:
        note_text = args.notes
    note_items = [n.strip() for n in note_text.splitlines() if n.strip()]

    try:
        result = classify(posts, note_items)
    except ClassifyError as e:
        print(f"classification failed: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()