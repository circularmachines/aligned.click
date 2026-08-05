"""The channel a tool uses to draw something in the chat.

Until now the UI got its instructions from the assistant's *prose*: it scanned
the reply for `[3]` and swapped in a post card. That works, at the cost of three
rules in AGENTS.md that the model has to remember on every single reply — write
the bracketed index, never the raw at:// URI, never put an index in a table —
each added after a real failure. It asks the weakest part of the system for
prose-formatting discipline.

This inverts it. A tool call is the channel a model is most reliable in, so the
model asks for a card by *calling a tool*, and the tool emits a payload the UI
renders. Nothing about the reply text matters any more.

The payload is one line at the end of the tool's output:

    RENDER {"kind": "posts", ...}

One line, so the regex can't run away; at the end, so the human-readable part
the model reads comes first; `kind` chosen by the tool, so the UI dispatches on
it and a tool whose kind the UI doesn't know yet degrades to its text output
instead of vanishing.

The model sees this line too, which is deliberate — it's the tool's receipt that
the cards were drawn, and it needs to know that so it doesn't describe the posts
all over again in prose.
"""
import json

SENTINEL = "RENDER"


def emit(kind: str, **payload) -> None:
    """Print the render line. Compact separators keep it to one line."""
    print(SENTINEL + " " + json.dumps({"kind": kind, **payload}, separators=(",", ":")))
